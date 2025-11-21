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
                "anthropic": {  # "anthropic"
                    "provider": "anthropic",
                    "model": "claude-sonnet-4-5-20250929",
                    "api_key": "ANTHROPIC_API_KEY",  # Environment variable for API key
                    "max_retries": 3,
                    "timeout": 300,
                },
                "gemini": {
                    "provider": "gemini",
                    "model": "gemini-2.5-flash",
                    "api_key": "GEMINI_API_KEY",  # Environment variable for API key
                    "max_retries": 3,
                    "timeout": 300,
                },
            },
            "tools": {
                "mythril": {
                    "timeout": 300,
                    "format": "json",
                    "docker": {"image": "mythril/myth:latest"},
                },
                "slither": {
                    "timeout": 300,
                    "format": "json",
                    "docker": {"image": "trailofbits/eth-security-toolbox:latest"},
                },
            },
            "services": {
                "mcp": {
                    "host": "localhost",
                    "port": 8000,
                },
                "langchain": {
                    "llms": ["anthropic", "gemini"],
                    "framework": "hardhat",
                },
                "generator": {
                    "llm": "gemini",
                    "framework": "hardhat",
                },
            },
            "output": {
                "directory": "argus",
                "level": "debug",
            },
            "workdir": ".",
            "mode": "generator",
        }

    def get(self, key_path: str, default=None):
        """
        Get configuration value using dot notation.

        Example: config.get('llm.model')
        """
        keys = key_path.split(".")
        value = self.config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value
