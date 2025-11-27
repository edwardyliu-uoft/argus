"""Package for Argus plugins system.

This module provides the plugin infrastructure to extend Argus:
- LLM providers
- MCP server tools
- MCP server resources
- MCP server prompts

Plugins are discovered via setuptools entry points and managed through
a central registry.
"""

from .plugin import (
    BasePlugin,
    LLMProviderPlugin,
    MCPToolPlugin,
    MCPResourcePlugin,
    MCPPromptPlugin,
)
from .registry import PluginRegistry, get_plugin_registry, reset_plugin_registry

__all__ = [
    "BasePlugin",
    "LLMProviderPlugin",
    "MCPToolPlugin",
    "MCPResourcePlugin",
    "MCPPromptPlugin",
    "PluginRegistry",
    "get_plugin_registry",
    "reset_plugin_registry",
]
