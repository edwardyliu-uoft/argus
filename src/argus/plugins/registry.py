"""The plugin registry for discovering and managing Argus plugins.

Responsible for:
- Discovering plugins via setuptools entry points
- Registering and storing plugin instances
- Providing access to plugins by name or type
- Validating plugin configurations
"""

from typing import Dict, List, Optional, Any
from importlib.metadata import entry_points

import logging

from . import constants as const
from .plugin import (
    BasePlugin,
    LLMProviderPlugin,
    MCPToolPlugin,
    MCPResourcePlugin,
    MCPPromptPlugin,
)


_logger = logging.getLogger("argus.console")


class PluginRegistry:
    """Argus plugin registry.

    Plugins are discovered through setuptools entry points:
    - argus.llm.providers: LLM provider plugins
    - argus.mcp.tools: MCP tool plugins
    - argus.mcp.resources: MCP resource plugins
    - argus.mcp.prompts: MCP prompt plugins
    """

    def __init__(self):
        self.__plugins: Dict[str, Dict[str, BasePlugin]] = {}
        self.__initialized: Dict[str, bool] = {}
        for entry_point in const.ARGUS_ENTRY_POINTS:
            self.__plugins[entry_point] = {}
            self.__initialized[entry_point] = False

    def initialized(self, group: str) -> bool:
        """Verify if plugin discovery has been executed.

        Args:
            group: Plugin group name to check initialization status

        Returns:
            True if initialized, False otherwise
        """
        return self.__initialized[group]

    def discover_plugins(self, group: Optional[str] = None) -> None:
        """Discover and load plugins from entry points.

        Args:
            group: Specific plugin group to discover (e.g. 'argus.llm.providers').
                If None, discovers all plugin groups.
        """
        groups = [group] if group else const.ARGUS_ENTRY_POINTS

        for group in groups:
            _logger.debug("Discovering plugins in group: %s", group)

            eps = entry_points(group=group)
            for ep in eps:
                try:
                    plugin_cls = ep.load()
                    plugin_ins = plugin_cls()

                    # Validate plugin type
                    if not isinstance(plugin_ins, BasePlugin):
                        _logger.warning(
                            "Plugin '%s' does not inherit from BasePlugin, skipping.",
                            ep.name,
                        )
                        continue

                    # Validate plugin type matches group
                    if not self.__validate_plugin_type(
                        plugin_ins,
                        group,
                    ):
                        _logger.warning(
                            "Plugin '%s' type mismatched for group '%s', skipping.",
                            ep.name,
                            group,
                        )
                        continue

                    # Register plugin
                    self.register_plugin(plugin_ins, group)

                # pylint: disable=broad-except
                except Exception as e:
                    _logger.error(
                        "Failed to load plugin '%s', error: %s",
                        ep.name,
                        e,
                        exc_info=True,
                    )
            self.__initialized[group] = True

    def __validate_plugin_type(self, plugin_ins: BasePlugin, group: str) -> bool:
        """
        Validate plugin type matches the expected type for the group.

        Args:
            plugin_ins: Plugin instance
            group: Plugin group name

        Returns:
            True if valid, False otherwise
        """
        expected_plugin_types = {
            "argus.llm.providers": LLMProviderPlugin,
            "argus.mcp.tools": MCPToolPlugin,
            "argus.mcp.resources": MCPResourcePlugin,
            "argus.mcp.prompts": MCPPromptPlugin,
        }
        return isinstance(plugin_ins, expected_plugin_types[group])

    def register_plugin(self, plugin_ins: BasePlugin, group: str) -> None:
        """Register a plugin instance.

        Args:
            plugin_ins: Plugin instance to register
            group: Plugin group (e.g. 'argus.llm.providers')

        Raises:
            ValueError: If group is invalid or plugin name conflicts
        """
        if group not in self.__plugins:
            raise ValueError(f"Invalid plugin group: {group}")

        if plugin_ins.name in self.__plugins[group]:
            _logger.warning(
                "Plugin '%s' already registered in group '%s', overwriting",
                plugin_ins.name,
                group,
            )

        self.__plugins[group][plugin_ins.name] = plugin_ins
        _logger.info("Registered plugin: '%s' in group '%s'", plugin_ins.name, group)

    def get_plugin(self, name: str, group: str) -> Optional[BasePlugin]:
        """Get a plugin by name and group.

        Args:
            name: Plugin name
            group: Plugin group

        Returns:
            Plugin instance or None if not found
        """
        return self.__plugins.get(group, {}).get(name)

    def get_plugins_by_group(self, group: str) -> Dict[str, BasePlugin]:
        """Get all plugins in a specific group.

        Args:
            group: Plugin group

        Returns:
            Dictionary of plugin name to plugin instance
        """
        return self.__plugins.get(group, {}).copy()

    def get_all_plugins(self) -> Dict[str, Dict[str, BasePlugin]]:
        """Get all registered plugins organized by group.

        Returns:
            Dictionary of group -> (plugin name -> plugin instance)
        """
        return {group: plugins.copy() for group, plugins in self.__plugins.items()}

    def initialize_plugin(
        self,
        name: str,
        group: str,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize a plugin.

        Args:
            name: Plugin name
            group: Plugin group
            config: Plugin-specific configuration

        Raises:
            ValueError: If plugin not found
        """

        plugin = self.get_plugin(name, group)
        if plugin is None:
            raise ValueError(f"Plugin '{name}' not found in group '{group}'.")

        # Validate configuration
        if not plugin.config_validate(config):
            raise ValueError(f"Invalid configuration for plugin '{name}'.")

        # Initialize plugin
        plugin.initialize(config)
        _logger.info("Initialized plugin: '%s' from group '%s'.", name, group)

    def list_plugins(self, group: Optional[str] = None) -> List[Dict[str, str]]:
        """List all available plugins.

        Args:
            group: Specific group to list, or None for all groups

        Returns:
            List of plugin info dictionaries with name, version, description, group
        """
        metadata_plugins = []
        groups = [group] if group else const.ARGUS_ENTRY_POINTS

        for group in groups:
            for name, plugin in self.__plugins[group].items():
                metadata_plugins.append(
                    {
                        "name": name,
                        "version": plugin.version,
                        "description": plugin.description,
                        "group": group,
                    }
                )

        return metadata_plugins


# Global plugin registry instance
__plugin_registry: Optional[PluginRegistry] = None


def get_plugin_registry() -> PluginRegistry:
    """Get the global plugin registry instance.

    Returns:
        Global PluginRegistry instance
    """
    # pylint: disable=global-statement
    global __plugin_registry
    if __plugin_registry is None:
        __plugin_registry = PluginRegistry()

    return __plugin_registry


def reset_plugin_registry() -> None:
    """Reset the global plugin registry."""
    # pylint: disable=global-statement
    global __plugin_registry
    __plugin_registry = None
