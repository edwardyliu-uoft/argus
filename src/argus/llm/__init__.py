"""
LLM Provider Factory

This module provides a factory function to create the appropriate
LLM provider based on configuration.
"""

from .base import BaseLLMProvider


def get_llm_provider(config) -> BaseLLMProvider:
    """
    Factory function to create LLM provider based on configuration.

    Args:
        config: ArgusConfig instance

    Returns:
        Instance of BaseLLMProvider (AnthropicProvider or GeminiProvider)

    Raises:
        ValueError: If provider is not supported

    Example:
        >>> config = ArgusConfig()
        >>> provider = get_llm_provider(config)
        >>> provider.initialize_client()
        >>> response = provider.call_simple("Hello!")
    """
    provider_name = config.get("llm.provider", "anthropic").lower()

    if provider_name == "anthropic":
        from .providers.anthropic import AnthropicProvider

        return AnthropicProvider(config)

    elif provider_name == "gemini":
        from .providers.gemini import GeminiProvider

        return GeminiProvider(config)

    else:
        raise ValueError(
            f"Unsupported LLM provider: {provider_name}. "
            f"Supported providers: anthropic, gemini"
        )


# Export for convenient imports
__all__ = ["get_llm_provider", "BaseLLMProvider"]
