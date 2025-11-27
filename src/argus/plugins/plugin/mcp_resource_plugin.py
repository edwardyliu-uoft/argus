"""MCP resource plugin interface for Argus plugins."""

from typing import Callable, Dict

from .plugin import BasePlugin


class MCPResourcePlugin(BasePlugin):
    """
    Base class for MCP resource plugins.

    Resources provide read-only access to data or information.
    """

    # Dict mapping resource names to async callable functions.
    #   Each function should return resource data (typically strings).
    # Example:
    #     {
    #         "get_workspace": get_workspace_function,
    #         "get_info": get_info_function
    #     }
    resources: Dict[str, Callable]
