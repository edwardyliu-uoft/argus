"""Anthropic LLM provider plugin."""

from typing import Dict, Any, Optional

from argus.plugins import LLMProviderPlugin

from .provider import AnthropicProvider


class AnthropicProviderPlugin(LLMProviderPlugin):
    """Plugin wrapper for Anthropic Claude provider"""

    def __init__(self) -> None:
        self.provider: Optional[AnthropicProvider] = None

    @property
    def name(self) -> str:
        return "anthropic"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Anthropic Claude LLM provider"

    @property
    def config_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "provider": {"type": "string", "const": "anthropic"},
                "model": {"type": "string"},
                "api_key": {"type": "string"},
                "max_tokens": {"type": "integer", "minimum": 1},
                "max_retries": {"type": "integer", "minimum": 0},
                "timeout": {"type": "integer", "minimum": 0},
                "max_tool_result_length": {"type": "integer", "minimum": 0},
            },
            "required": ["provider", "model", "api_key"],
        }

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the Anthropic LLM provider using the given config."""

        self.provider = AnthropicProvider(config)
        self.initialized = True
