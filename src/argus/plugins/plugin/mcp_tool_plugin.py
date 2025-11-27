"""MCP tool plugin interface for Argus plugins."""

from typing import Callable, Dict

from .plugin import BasePlugin


class MCPToolPlugin(BasePlugin):
    """
    Base class for MCP tool plugins.

    Tools are async functions that can be called by the LLM to perform
    actions or retrieve information.
    """

    # Dict mapping tool names to async callable functions.
    #   Each function should accept standard MCP tool parameters
    #   and return a Dict[str, Any] with results.
    # Example:
    #     {
    #         "my_tool": my_tool_function,
    #         "another_tool": another_tool_function
    #     }
    tools: Dict[str, Callable]
