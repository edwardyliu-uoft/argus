"""Argus MCP Server: Model Context Protocol server for Argus security tool.

This module exposes a thread-runnable `MCPServer` class. For CLI usage the
`run()` function preserves the previous blocking behavior.
"""

from typing import Optional
from multiprocessing import Process
import logging
import time

from mcp.server.fastmcp import FastMCP

from argus.core.config import conf as config

logger = logging.getLogger("argus.console")


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
            config.get("services.mcp.name", "Argus MCP Server"),
        )
        self.json_response = kwargs.get(
            "json_response",
            config.get("services.mcp.json_response", True),
        )
        self.host = kwargs.get("host", config.get("services.mcp.host", "127.0.0.1"))
        self.port = kwargs.get("port", config.get("services.mcp.port", 8000))
        self.mount_path = kwargs.get(
            "mount_path",
            config.get("services.mcp.mount_path", "/mcp"),
        )

    def run(self) -> None:
        """Construct FastMCP in the child process and run it (blocking)."""
        try:
            logger.info(
                f"Starting Argus MCP Server on {self.host}:{self.port} "
                f"at mount_path={self.mount_path}"
            )
            logger.info("Available transports: streamable-http")

            self.app = FastMCP(
                self.name,
                json_response=self.json_response,
                host=self.host,
                port=self.port,
                mount_path=self.mount_path,
            )
            self.register_tools(self.app)
            self.app.run(transport="streamable-http")
        except Exception as e:
            logger.error(f"Server error: {e}")
            raise

    def register_tools(self, app: FastMCP) -> None:
        """Register MCP tools with the server."""
        from argus.services.mcp import tools

        if app is None:
            raise RuntimeError("Argus MCP Server is not initialized.")

        # Register tools
        # TODO: make configurable and dynamically-added
        # for config.get("tools", ["mythril", "slither"]):
        #     app.tool()(<tool>)
        app.tool()(tools.get_weather)
        app.tool()(tools.get_time)

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
                logger.warning("Forcefully killing server process")
                self.kill()
                self.join(timeout=1.0)
        except Exception as e:
            logger.error(f"Error stopping server: {e}")
        finally:
            self.app = None


server: Optional[ArgusMCPServer] = None


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
    global server
    server = create_server(**kwargs)
    server.start()

    # Give server a moment to start
    time.sleep(0.5)

    try:
        pid = server.pid
    except Exception:
        pid = None
    logger.info(f"Started Argus MCP server process (pid={pid})")
    return server


def stop() -> None:
    """Stop the Argus MCP server if it is running."""
    global server
    if server is not None:
        server.stop()
        server = None
