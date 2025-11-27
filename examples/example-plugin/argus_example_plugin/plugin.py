"""Example Plugin Implementation

This plugin provides a simple greeting tool that demonstrates the basic
structure of an Argus MCP tool plugin.
"""

from typing import Any, Dict, Optional
import logging

from argus.plugins import MCPToolPlugin


_logger = logging.getLogger("argus.console.example-plugin")


class ExamplePlugin(MCPToolPlugin):
    """
    A simple example plugin that provides a greeting tool.

    This plugin demonstrates:
    - Basic plugin structure and inheritance
    - Tool registration and implementation
    - Configuration handling
    - Async tool execution
    """

    config: Dict[str, Any]

    @property
    def name(self) -> str:
        """Unique identifier for the plugin."""
        return "example"

    @property
    def version(self) -> str:
        """Plugin version."""
        return "0.1.0"

    @property
    def description(self) -> str:
        """Human-readable description of the plugin."""
        return "A simple greeting tool that says hello in multiple languages"

    @property
    def config_schema(self) -> Optional[Dict[str, Any]]:
        """
        JSON schema for plugin configuration.

        This plugin accepts an optional default_language configuration.
        """
        return {
            "type": "object",
            "properties": {
                "default_language": {
                    "type": "string",
                    "enum": ["en", "es", "fr", "de", "ja", "cn"],
                    "description": "Default language for greetings",
                },
                "include_emoji": {
                    "type": "boolean",
                    "description": "Whether to include emoji in greetings",
                },
            },
        }

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize the plugin with configuration.

        Args:
            config: Configuration dictionary, may include:
                - default_language: Default greeting language (default: "en")
                - include_emoji: Whether to include emoji (default: True)
        """
        self.config = config or {}

        # Register all tools provided by this plugin
        self.tools = {
            "greet": self.greet,
            "greet_multiple": self.greet_multiple,
        }
        self.initialized = True

    async def greet(
        self,
        name: Optional[str] = None,
        language: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate a greeting message.

        This is the main tool function that will be called when the LLM
        invokes the "greet" tool.

        Args:
            name: Name to greet (default: "Edward Liu")
            language: Language code for greeting (default: from config or "en")
                Supported: en, es, fr, de, ja, cn

        Returns:
            Dictionary containing:
                - success: Whether the operation succeeded
                - greeting: The greeting message
                - language: Language used
                - name: Name that was greeted

        Example:
            >>> result = await plugin.greet(name="Alice", language="es")
            >>> print(result)
            {
                "success": True,
                "greeting": "¡Hola, Alice!",
                "language": "es",
                "name": "Alice"
            }
        """
        # Get parameters with defaults
        name = name or "Edward Liu"
        language = language or self.config.get("default_language", "en")
        include_emoji = self.config.get("include_emoji", True)

        # Define greetings in different languages
        greetings = {
            "en": "Hello",
            "es": "Hola",
            "fr": "Bonjour",
            "de": "Guten Tag",
            "ja": "こんにちは",
            "cn": "你好",
        }
        emojis = {
            "en": "👋",
            "es": "🎉",
            "fr": "🥖",
            "de": "🍺",
            "ja": "🎌",
            "cn": "🐉",
        }

        # Validate language
        if language not in greetings:
            return {
                "success": False,
                "error": f"Unsupported language: {language}",
                "supported_languages": list(greetings.keys()),
            }

        # Build greeting message
        greeting_word = greetings[language]

        # Spanish uses inverted exclamation at start
        if language == "es":
            message = f"¡{greeting_word}, {name}"
        else:
            message = f"{greeting_word}, {name}!"

        # Add emoji if enabled
        if include_emoji and language in emojis:
            message = f"{emojis[language]} {message}"

        _logger.debug("Generated greeting: %s", message)

        return {
            "success": True,
            "greeting": message,
            "language": language,
            "name": name,
        }

    async def greet_multiple(
        self,
        names: Optional[list] = None,
        language: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate greetings for multiple people.

        Args:
            names: List of names to greet (default: ["Edward Liu"])
            language: Language code for greeting (default: from config or "en")

        Returns:
            Dictionary containing:
                - success: Whether the operation succeeded
                - greetings: List of greeting messages
                - count: Number of people greeted
                - language: Language used

        Example:
            >>> result = await plugin.greet_multiple(
            ...     names=["Alice", "Bob", "Charlie"],
            ...     language="fr"
            ... )
            >>> print(result)
            {
                "success": True,
                "greetings": ["Bonjour, Alice!", "Bonjour, Bob!", "Bonjour, Charlie!"],
                "count": 3,
                "language": "fr"
            }
        """
        names = names or ["Edward Liu"]
        language = language or self.config.get("default_language", "en")

        # Generate greeting for each name
        greetings = []
        for name in names:
            result = await self.greet(name=name, language=language)
            if result["success"]:
                greetings.append(result["greeting"])
            else:
                return result  # Return error if any greeting fails

        return {
            "success": True,
            "greetings": greetings,
            "count": len(greetings),
            "language": language,
        }
