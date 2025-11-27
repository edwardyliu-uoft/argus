"""LLM provider plugin interface for Argus plugins."""

from typing import Optional, TYPE_CHECKING

from .plugin import BasePlugin

if TYPE_CHECKING:
    from argus.llm.provider import BaseLLMProvider


class LLMProviderPlugin(BasePlugin):
    """
    Base class for LLM provider plugins.

    LLM provider plugins must return a provider class that implements
    the BaseLLMProvider interface from argus.llm.provider.
    """

    provider: Optional["BaseLLMProvider"] = None
