"""Argus MCP Server: Model Context Protocol server for Argus security tool.

This module exposes a thread-runnable `MCPServer` class. For CLI usage the
`run()` function preserves the previous blocking behavior.
"""

from typing import Optional
from multiprocessing import Process
import logging
import time

from mcp.server.fastmcp import FastMCP

from argus.core import conf
from argus.plugins import (
    PluginRegistry,
    MCPPromptPlugin,
    MCPResourcePlugin,
    MCPToolPlugin,
    get_plugin_registry,
)


_logger = logging.getLogger("argus.console")


class ArgusMCPServer(Process):
    """A process-wrapping MCP server.

    This uses `multiprocessing.Process` so the server can be forcibly
    terminated via `terminate()` since there is no graceful shutdown API.

    Usage:
      server = MCPServer()
      server.start()    # runs in a background process
      ...
      server.stop()     # forcibly terminate the server process
    """

    def __init__(self, **kwargs) -> None:
        """Initialize the MCP server process.

        Args:
            name: Server name
            json_response: Enable JSON responses
            host: Server host address
            port: Server port
            mount_path: API mount path
        """
        super().__init__(target=self.run, name="ArgusMCPServerProcess")
        self.app: Optional[FastMCP] = None
        self.name = kwargs.get(
            "name",
            conf.get("server.name", "Argus MCP Server"),
        )
        self.json_response = kwargs.get(
            "json_response",
            conf.get("server.json_response", True),
        )
        self.host = kwargs.get("host", conf.get("server.host", "127.0.0.1"))
        self.port = kwargs.get("port", conf.get("server.port", 8000))
        self.mount_path = kwargs.get(
            "mount_path",
            conf.get("server.mount_path", "/mcp"),
        )

    def run(self) -> None:
        """Construct FastMCP in the child process and run it (blocking)."""
        try:
            _logger.info(
                "Starting Argus MCP Server on %s:%s at mount_path=%s",
                self.host,
                self.port,
                self.mount_path,
            )
            _logger.info("Available transports: streamable-http")

            self.app = FastMCP(
                self.name,
                json_response=self.json_response,
                host=self.host,
                port=self.port,
                mount_path=self.mount_path,
            )
            self.register(self.app, "prompts")
            self.register(self.app, "resources")
            self.register(self.app, "tools")
            self.app.run(transport="streamable-http")

        # pylint: disable=broad-except
        except Exception as e:
            _logger.error("Server error: %s", e)
            raise

    def __register_mcp_plugins(self, group: str) -> PluginRegistry:
        """Register built-in MCP server plugins.
        Called lazily when MCP server is started.

        Args:
            group: Plugin group to discover and register ('argus.mcp.tools', etc.)

        Returns:
            The PluginRegistry instance
        """

        registry = get_plugin_registry()
        if not registry.initialized(group):
            _logger.debug("Registering MCP plugins for group: '%s'", group)
            registry.discover_plugins(group)

        return registry

    def register(self, app: FastMCP, what: str) -> None:
        """Register MCP components with the server.

        Args:
            app: FastMCP server instance
            what: Component type to register ('prompts', 'resources', 'tools')
        """
        if app is None:
            raise RuntimeError("Argus MCP Server is not initialized.")

        # Ensure components are registered
        group = f"argus.mcp.{what}"
        registry = self.__register_mcp_plugins(group)

        plugins = registry.get_plugins_by_group(group)
        for plugin_name, plugin in plugins.items():

            if not isinstance(
                plugin,
                {
                    "prompts": MCPPromptPlugin,
                    "resources": MCPResourcePlugin,
                    "tools": MCPToolPlugin,
                }[what],
            ):
                _logger.warning(
                    "MCP %s plugin '%s' is not of a valid type, skipping.",
                    what,
                    plugin_name,
                )
                continue

            if not plugin.initialized:
                registry.initialize_plugin(
                    plugin_name,
                    group,
                    {
                        "workdir": conf.get("workdir"),
                        **conf.get(f"server.{what}.{plugin_name}", {}),
                    },
                )

            components = {
                "prompts": getattr(plugin, "prompts", {}),
                "resources": getattr(plugin, "resources", {}),
                "tools": getattr(plugin, "tools", {}),
            }[what]
            for component_name, component_callable in components.items():
                if callable(component_callable):
                    if what == "prompts":
                        app.prompt()(component_callable)
                    elif what == "resources":
                        uri = f"resource:///{plugin_name}/{component_name}"
                        app.resource(uri)(component_callable)
                    elif what == "tools":
                        app.tool()(component_callable)
                    _logger.debug("Loaded %s: %s", what[:-1], component_name)
                else:
                    _logger.warning(
                        "MCP server %s '%s' from plugin '%s' is not callable, skipping.",
                        what[:-1],
                        component_name,
                        plugin_name,
                    )
            _logger.info("Finished loading %s from plugin: %s", what, plugin_name)

    def stop(self, timeout: float = 5.0) -> None:
        """Stop the server process.

        Attempts graceful shutdown first, then forceful termination if needed.

        Args:
            timeout: Seconds to wait for graceful shutdown before forcing
        """
        if not self.is_alive():
            return

        try:
            # Try termination
            self.terminate()
            self.join(timeout=timeout)

            # Force kill if still alive
            if self.is_alive():
                _logger.warning("Forcefully killing server process")
                self.kill()
                self.join(timeout=1.0)

        # pylint: disable=broad-except
        except Exception as e:
            _logger.error("Error stopping server: %s", e)
        finally:
            self.app = None


_server: Optional[ArgusMCPServer] = None


def create_server(**kwargs) -> ArgusMCPServer:
    """Create an `ArgusMCPServer` instance with any overrides.

    Example: `create_server(port=9000).start()`
    """

    return ArgusMCPServer(**kwargs)


def start(**kwargs) -> ArgusMCPServer:
    """Start the Argus MCP server in a background process (non-blocking).

    Args:
        **kwargs: Arguments passed to create_server()

    Returns:
        The `ArgusMCPServer` process instance so callers can manage it.
    """
    # pylint: disable=global-statement
    global _server
    _server = create_server(**kwargs)
    _server.start()

    # Give server a moment to start
    time.sleep(0.5)

    try:
        pid = _server.pid

    # pylint: disable=broad-except
    except Exception:
        pid = None
    _logger.info("Started Argus MCP server process (pid=%s)", pid)
    return _server


def stop() -> None:
    """Stop the Argus MCP server if it is running."""
    # pylint: disable=global-statement
    global _server
    if _server is not None:
        _server.stop()
        _server = None
