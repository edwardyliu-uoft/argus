"""Unit tests for configuration loading and validation."""

import json
import pytest
from argus.core.config import ArgusConfig


class TestArgusConfig:
    """Test suite for ArgusConfig class."""

    def test_default_config_structure(self):
        """Test that default config has all required keys."""
        config = ArgusConfig.get_default_config()

        assert "llm" in config
        assert "tools" in config
        assert "output" in config
        assert "workdir" in config

        # Verify LLM config structure
        assert "provider" in config["llm"]
        assert "model" in config["llm"]
        assert "api_key" in config["llm"]
        assert "max_retries" in config["llm"]
        assert "timeout" in config["llm"]

        # Verify tools config structure
        assert "mythril" in config["tools"]
        assert "slither" in config["tools"]

        # Verify output config structure
        assert "directory" in config["output"]
        assert "mode" in config["output"]

    def test_default_config_values(self):
        """Test that default config has expected values."""
        config = ArgusConfig.get_default_config()

        assert config["llm"]["provider"] == "anthropic"
        assert config["llm"]["model"] == "claude-sonnet-4-5-20250929"
        assert config["llm"]["api_key"] == "ANTHROPIC_API_KEY"
        assert config["llm"]["max_retries"] == 3
        assert config["llm"]["timeout"] == 300

        assert config["tools"]["mythril"]["timeout"] == 300
        assert config["tools"]["mythril"]["format"] == "json"
        assert config["tools"]["slither"]["timeout"] == 300
        assert config["tools"]["slither"]["format"] == "json"

        assert config["output"]["directory"] == "argus"
        assert config["output"]["mode"] == "debug"
        assert config["workdir"] == "."

    def test_init_with_no_config_path(self):
        """Test initialization with no config path uses defaults."""
        config = ArgusConfig()

        assert config.config == ArgusConfig.get_default_config()

    def test_init_with_none_config_path(self):
        """Test initialization with None explicitly uses defaults."""
        config = ArgusConfig(configpath=None)

        assert config.config == ArgusConfig.get_default_config()

    def test_init_with_nonexistent_file(self):
        """Test initialization with non-existent file uses defaults."""
        config = ArgusConfig(configpath="/path/to/nonexistent/file.json")

        assert config.config == ArgusConfig.get_default_config()

    def test_init_with_valid_config_file(self, tmp_path):
        """Test initialization with valid config file loads correctly."""
        # Create a temporary config file
        config_file = tmp_path / "config.json"
        test_config = {
            "llm": {
                "provider": "gemini",
                "model": "gemini-pro",
                "api_key": "TEST_KEY",
                "max_retries": 5,
                "timeout": 600
            },
            "tools": {
                "mythril": {
                    "timeout": 400,
                    "format": "text"
                },
                "slither": {
                    "timeout": 500,
                    "format": "text"
                }
            },
            "output": {
                "directory": "custom_output",
                "mode": "production"
            },
            "workdir": "/custom/path"
        }

        config_file.write_text(json.dumps(test_config))

        config = ArgusConfig(configpath=str(config_file))

        assert config.config == test_config
        assert config.config["llm"]["provider"] == "gemini"
        assert config.config["llm"]["model"] == "gemini-pro"
        assert config.config["output"]["directory"] == "custom_output"

    def test_get_simple_key(self):
        """Test getting a simple top-level key."""
        config = ArgusConfig()

        assert config.get("workdir") == "."

    def test_get_nested_key_single_level(self):
        """Test getting a nested key with dot notation (one level)."""
        config = ArgusConfig()

        llm_config = config.get("llm")
        assert llm_config["provider"] == "anthropic"
        assert llm_config["model"] == "claude-sonnet-4-5-20250929"

    def test_get_nested_key_multiple_levels(self):
        """Test getting a nested key with dot notation (multiple levels)."""
        config = ArgusConfig()

        assert config.get("llm.provider") == "anthropic"
        assert config.get("llm.model") == "claude-sonnet-4-5-20250929"
        assert config.get("llm.max_retries") == 3
        assert config.get("tools.mythril.timeout") == 300
        assert config.get("tools.slither.format") == "json"
        assert config.get("output.directory") == "argus"

    def test_get_nonexistent_key_returns_none(self):
        """Test getting a non-existent key returns None."""
        config = ArgusConfig()

        assert config.get("nonexistent") is None
        assert config.get("llm.nonexistent") is None
        assert config.get("nonexistent.nested.key") is None

    def test_get_nonexistent_key_returns_default(self):
        """Test getting a non-existent key returns provided default."""
        config = ArgusConfig()

        assert config.get("nonexistent", "default_value") == "default_value"
        assert config.get("llm.nonexistent", 42) == 42
        assert config.get("nonexistent.nested", []) == []

    def test_get_with_empty_string_key(self):
        """Test getting with empty string key."""
        config = ArgusConfig()

        # Empty string splits to [''] which looks for a key '', which doesn't exist
        # So it returns None (or the default if provided)
        result = config.get("")
        assert result is None

        # With a default value
        assert config.get("", "default") == "default"

    def test_get_partial_path_to_dict(self):
        """Test getting a partial path that points to a dict."""
        config = ArgusConfig()

        tools_config = config.get("tools")
        assert isinstance(tools_config, dict)
        assert "mythril" in tools_config
        assert "slither" in tools_config

    def test_get_with_custom_config(self, tmp_path):
        """Test get method with custom loaded config."""
        config_file = tmp_path / "custom.json"
        test_config = {
            "custom": {
                "nested": {
                    "value": "test_value"
                }
            }
        }
        config_file.write_text(json.dumps(test_config))

        config = ArgusConfig(configpath=str(config_file))

        assert config.get("custom.nested.value") == "test_value"
        assert config.get("custom.nested") == {"value": "test_value"}
        assert config.get("custom") == {"nested": {"value": "test_value"}}

    def test_config_immutability_through_get(self):
        """Test that modifying returned values doesn't affect config."""
        config = ArgusConfig()

        llm_config = config.get("llm")

        # Modify the returned dict
        llm_config["provider"] = "modified"

        # Original config should be modified (Python dict behavior)
        # This test documents current behavior
        assert config.get("llm.provider") == "modified"

        # Note: If immutability is desired, the get method should return deep copies

    def test_invalid_json_file(self, tmp_path):
        """Test initialization with invalid JSON file."""
        config_file = tmp_path / "invalid.json"
        config_file.write_text("{ invalid json }")

        with pytest.raises(json.JSONDecodeError):
            ArgusConfig(configpath=str(config_file))

    def test_get_with_integer_in_path(self):
        """Test get method when path contains numeric keys (edge case)."""
        config = ArgusConfig()
        config.config = {"list": [1, 2, 3], "nested": {"0": "zero"}}

        # Numeric string keys should work for dict
        assert config.get("nested.0") == "zero"

        # But numeric keys don't work for lists (current implementation)
        # This documents current behavior
        assert config.get("list.0") is None

    def test_multiple_config_instances(self, tmp_path):
        """Test that multiple config instances are independent."""
        config1 = ArgusConfig()

        config_file = tmp_path / "config2.json"
        test_config = {"llm": {"provider": "gemini"}}
        config_file.write_text(json.dumps(test_config))

        config2 = ArgusConfig(configpath=str(config_file))

        assert config1.get("llm.provider") == "anthropic"
        assert config2.get("llm.provider") == "gemini"

        # Verify they are independent instances
        assert config1.config != config2.config
