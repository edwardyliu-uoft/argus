"""LLM Provider Factory

This module provides a factory function to create the appropriate
LLM provider based on configuration. Uses the plugin system to
discover and load providers (built-in and external).
"""

import logging

from argus.core import conf
from argus.plugins import PluginRegistry, LLMProviderPlugin, get_plugin_registry

from .provider import BaseLLMProvider


_logger = logging.getLogger("argus.console")


def __register_providers() -> PluginRegistry:
    """Register built-in providers as plugins.
    Called lazily when get_llm_provider is first used.
    """

    registry = get_plugin_registry()
    if not registry.initialized("argus.llm.providers"):
        _logger.debug("Registering LLM provider plugins")
        registry.discover_plugins("argus.llm.providers")

    return registry


def get_llm_provider(provider_name: str) -> BaseLLMProvider:
    """
    Factory function to create LLM provider based on configuration.

    This function uses the plugin system to discover and load providers.
    Built-in providers (anthropic, gemini) are automatically registered.
    External providers can be added via entry points in the 'argus.llm.providers' group.

    Args:
        provider_name: Name of the provider to load (e.g. 'anthropic', 'gemini')

    Returns:
        Instance of BaseLLMProvider

    Raises:
        ValueError: If provider is not found or not properly registered

    Example:
        >>> provider = get_llm_provider("anthropic")
        >>> provider.initialize_client()
        >>> response = provider.call_simple("Hello!")
    """

    # Ensure providers are registered
    registry = __register_providers()
    plugin = registry.get_plugin(provider_name, "argus.llm.providers")
    if plugin is None:
        _logger.error("LLM provider plugin '%s' not found", provider_name)
        raise ValueError(f"LLM provider '{provider_name}' not found.")
    if not isinstance(plugin, LLMProviderPlugin):
        raise ValueError(
            f"LLM provider '{provider_name}' is not of a valid plugin type."
        )
    if not plugin.initialized:
        registry.initialize_plugin(
            provider_name,
            "argus.llm.providers",
            conf.get(f"llm.{provider_name}"),
        )

    return plugin.provider
