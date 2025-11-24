"""Argus MCP Server: Model Context Protocol server for Argus security tool.

This module exposes a thread-runnable `MCPServer` class. For CLI usage the
`run()` function preserves the previous blocking behavior.
"""

from typing import Optional
from multiprocessing import Process
import logging
import importlib
import time

from mcp.server.fastmcp import FastMCP

from argus.core import conf


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
            self.register_prompts(self.app)
            self.register_resources(self.app)
            self.register_tools(self.app)
            self.app.run(transport="streamable-http")

        # pylint: disable=broad-except
        except Exception as e:
            _logger.error("Server error: %s", e)
            raise

    def register_prompts(self, app: FastMCP) -> None:
        """Register MCP prompts with the server."""
        if app is None:
            raise RuntimeError("Argus MCP Server is not initialized.")

        # Register prompts from conf
        for promptname in conf.get("server.prompts", {}).keys():
            promptmodule = importlib.import_module(f"argus.server.prompts.{promptname}")
            for funcname in conf.get(
                f"server.prompts.{promptname}.functions",
                [promptname],
            ):
                promptfunc = getattr(promptmodule, funcname, None)
                if callable(promptfunc):
                    app.prompt()(promptfunc)
                else:
                    _logger.warning(
                        "MCP server prompt '%s'.'%s' not found in argus.server.prompts",
                        promptname,
                        funcname,
                    )

    def register_resources(self, app: FastMCP) -> None:
        """Register MCP resources with the server."""
        if app is None:
            raise RuntimeError("Argus MCP Server is not initialized.")

        # Register resources from conf
        for resname in conf.get("server.resources", {}).keys():
            resmodule = importlib.import_module(f"argus.server.resources.{resname}")
            for funcname in conf.get(
                f"server.resources.{resname}.functions",
                [resname],
            ):
                resfunc = getattr(resmodule, funcname, None)
                if callable(resfunc):
                    # Generate URI from function name
                    uri = f"resource:///{resname}/{funcname}"
                    app.resource(uri)(resfunc)
                else:
                    _logger.warning(
                        "MCP server resource '%s'.'%s' not found in argus.server.resources",
                        resname,
                        funcname,
                    )

    def register_tools(self, app: FastMCP) -> None:
        """Register MCP tools with the server."""
        if app is None:
            raise RuntimeError("Argus MCP Server is not initialized.")

        # Register tools from conf
        for toolname in conf.get("server.tools", {}).keys():
            toolmodule = importlib.import_module(f"argus.server.tools.{toolname}")
            for funcname in conf.get(
                f"server.tools.{toolname}.functions",
                [toolname],
            ):
                toolfunc = getattr(toolmodule, funcname, None)
                if callable(toolfunc):
                    app.tool()(toolfunc)
                else:
                    _logger.warning(
                        "MCP server tool '%s'.'%s' not found in argus.server.tools",
                        toolname,
                        funcname,
                    )

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
