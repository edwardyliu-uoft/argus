"""Argus configuration."""

from typing import Dict, Any
from pathlib import Path
import json


class ArgusConfig:
    """Manages Argus configuration."""

    def __init__(self, config_path: str = None):
        """
        Load configuration from file or use defaults.

        Args:
            config_path: Path to config JSON file
        """
        if config_path and Path(config_path).exists():
            with open(config_path, encoding="utf-8") as f:
                self.config = json.load(f)
        else:
            self.config = self.get_default_config()

        # Ensure workdir is an absolute path
        if self.config.get("workdir", None):
            self.config["workdir"] = Path(self.config["workdir"]).resolve().as_posix()
        else:
            self.config["workdir"] = Path.cwd().as_posix()

    @staticmethod
    def get_default_config() -> Dict[str, Any]:
        """Return default configuration."""
        return {
            "orchestrator": {
                "llm": "gemini",
            },
            "llm": {
                "anthropic": {
                    "provider": "anthropic",
                    "model": "claude-sonnet-4-5-20250929",
                    "api_key": "ANTHROPIC_API_KEY",  # Environment variable for API key
                    "max_retries": 3,
                    "timeout": 300,
                    "max_tool_result_length": 50000,  # Max characters for tool results
                },
                "gemini": {
                    "provider": "gemini",
                    "model": "gemini-2.5-flash",
                    "api_key": "GEMINI_API_KEY",  # Environment variable for API key
                    "max_retries": 3,
                    "timeout": 300,
                    "max_tool_result_length": 50000,  # Max characters for tool results
                },
            },
            "server": {
                "host": "127.0.0.1",
                "port": 8000,
                "mount_path": "/mcp",
                "tools": {
                    "mythril": {
                        "timeout": 300,
                        "outform": "json",
                        "docker": {
                            "image": "mythril/myth:latest",
                            "network_mode": "bridge",
                            "remove_containers": True,
                        },
                    },
                    "slither": {
                        "timeout": 300,
                        "docker": {
                            "image": "trailofbits/eth-security-toolbox:latest",
                            "network_mode": "bridge",
                            "remove_containers": True,
                        },
                    },
                    "filesystem": {
                        "functions": [
                            "list_directory",
                            "find_files_by_extension",
                            "read_file_info",
                            "read_file",
                            "write_file",
                            "append_file",
                            "create_directory",
                        ],
                    },
                },
                "resources": {
                    "filesystem": {
                        "functions": [
                            "get_workspace",
                            "get_project_structure",
                            "get_solidity_files",
                        ],
                    },
                },
            },
            "generator": {
                "llm": "gemini",
                "framework": "hardhat",
            },
            "output": {
                "directory": "argus",
                "level": "debug",
            },
            "workdir": Path.cwd().as_posix(),
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


conf = initialize()
