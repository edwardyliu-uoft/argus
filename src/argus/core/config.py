"""Configuration loading and validation."""

import json
from pathlib import Path
from typing import Dict, Any


class ArgusConfig:
    """Manages Argus configuration."""

    def __init__(self, config_path: str = None):
        """
        Load configuration from file or use defaults.

        Args:
            config_path: Path to config JSON file
        """
        if config_path and Path(config_path).exists():
            with open(config_path) as f:
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
                    "host": "127.0.0.1",
                    "port": 8000,
                    "mount_path": "/mcp",
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


def initialize() -> ArgusConfig:
    """Initialize and return the Argus configuration."""

    project_dir = Path.cwd()
    selected_config = None
    for fname in ("argus.json", "argus.config.json"):
        candidate = project_dir / fname
        if candidate.exists():
            selected_config = str(candidate)
            break

    return ArgusConfig(config_path=selected_config)


config = initialize()
