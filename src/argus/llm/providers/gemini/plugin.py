"""Google Gemini LLM provider plugin."""

from typing import Dict, Any, Optional

from argus.plugins import LLMProviderPlugin

from .provider import GeminiProvider


class GeminiProviderPlugin(LLMProviderPlugin):
    """Plugin wrapper for Google Gemini provider"""

    @property
    def name(self) -> str:
        return "gemini"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Google Gemini LLM provider"

    @property
    def config_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "provider": {"type": "string", "const": "gemini"},
                "model": {"type": "string"},
                "api_key": {"type": "string"},
                "max_retries": {"type": "integer", "minimum": 0},
                "timeout": {"type": "integer", "minimum": 0},
                "max_tool_result_length": {"type": "integer", "minimum": 0},
            },
            "required": ["provider", "model", "api_key"],
        }

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the Anthropic LLM provider using the given config."""

        self.provider = GeminiProvider(config)
        self.initialized = True
