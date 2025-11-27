"""
Base plugin interface for Argus plugins.

All plugins must inherit from BasePlugin and implement the required methods.
Specific plugin types (LLM providers, tools, resources, prompts) have their
own abstract base classes.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from jsonschema import validate, ValidationError


class BasePlugin(ABC):
    """
    Base class for all Argus plugins.

    All plugins must provide a name and version, and implement
    the initialize method for any setup logic.
    """

    initialized: bool = False

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for the plugin (e.g. 'anthropic', 'mythril')"""

    @property
    @abstractmethod
    def version(self) -> str:
        """Plugin version (semantic versioning recommended)"""

    @property
    def description(self) -> Optional[str]:
        """Human-readable description of the plugin"""
        return None

    @property
    def config_schema(self) -> Optional[Dict[str, Any]]:
        """
        JSON schema for configuring the plugin.
        Return None if no configuration is required or schema is not enforced.

        Example:
            {
                "type": "object",
                "properties": {
                    "api_key": {"type": "string"},
                    "timeout": {"type": "integer", "minimum": 0}
                },
                "required": ["api_key"]
            }
        """
        return None

    def config_validate(self, config: Dict[str, Any]) -> bool:
        """
        Validate the provided configuration against the config_schema.

        Args:
            config: Configuration dictionary to validate

        Returns:
            True if valid, False otherwise
        """
        if self.config_schema is None:
            return True  # No schema to validate against

        try:
            validate(instance=config, schema=self.config_schema)
            return True
        except ValidationError:
            return False

    @abstractmethod
    def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize plugin given the configuration.

        Args:
            config: Configuration from 'argus.json' or 'argus.config.json'

        Raises:
            ValueError: If configuration is invalid
        """
