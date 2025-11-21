"""Configuration loading and validation."""

import json
from pathlib import Path
from typing import Dict, Any


class ArgusConfig:
    """Manages Argus configuration."""

    def __init__(self, configpath: str = None):
        """
        Load configuration from file or use defaults.

        Args:
            config_path: Path to config JSON file
        """
        if configpath and Path(configpath).exists():
            with open(configpath) as f:
                self.config = json.load(f)
        else:
            self.config = self.get_default_config()

    @staticmethod
    def get_default_config() -> Dict[str, Any]:
        """Return default configuration."""
        return {
            "llm": {
                "provider": "anthropic",  # "anthropic" or "gemini"
                "model": "claude-sonnet-4-5-20250929",
                "api_key": "ANTHROPIC_API_KEY",  # Environment variable for API key
                "max_retries": 3,
                "timeout": 300
            },
            "tools" : { 
                "mythril": {
                    "timeout": 300,
                    "format": "json"
                },
                "slither": {
                    "timeout": 300,
                    "format": "json"
                }
            },
           
            "output": {
                "directory": "argus",
                "mode": "debug"
            },
            "workdir": "."
        }

    def get(self, key_path: str, default=None):
        """
        Get configuration value using dot notation.

        Example: config.get('llm.model')
        """
        keys = key_path.split('.')
        value = self.config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value
