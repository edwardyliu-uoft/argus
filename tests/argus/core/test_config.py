"""Unit tests for configuration loading and validation."""

import json
import pytest
from pathlib import Path
from argus.core.config import ArgusConfig, initialize


class TestArgusConfig:
    """Test suite for ArgusConfig class."""

    def test_default_config_structure(self):
        """Test that default config has all required keys."""
        config = ArgusConfig.get_default_config()

        assert "llm" in config
        assert "tools" in config
        assert "services" in config
        assert "output" in config
        assert "workdir" in config
        assert "mode" in config

        # Verify LLM config structure (nested by provider)
        assert "anthropic" in config["llm"]
        assert "gemini" in config["llm"]
        assert "provider" in config["llm"]["anthropic"]
        assert "model" in config["llm"]["anthropic"]
        assert "api_key" in config["llm"]["anthropic"]
        assert "max_retries" in config["llm"]["anthropic"]
        assert "timeout" in config["llm"]["anthropic"]

        # Verify tools config structure
        assert "mythril" in config["tools"]
        assert "slither" in config["tools"]

        # Verify services config structure
        assert "mcp" in config["services"]
        assert "langchain" in config["services"]
        assert "generator" in config["services"]

        # Verify output config structure
        assert "directory" in config["output"]
        assert "level" in config["output"]

    def test_default_config_values(self):
        """Test that default config has expected values."""
        config = ArgusConfig.get_default_config()

        # Test anthropic LLM config
        assert config["llm"]["anthropic"]["provider"] == "anthropic"
        assert config["llm"]["anthropic"]["model"] == "claude-sonnet-4-5-20250929"
        assert config["llm"]["anthropic"]["api_key"] == "ANTHROPIC_API_KEY"
        assert config["llm"]["anthropic"]["max_retries"] == 3
        assert config["llm"]["anthropic"]["timeout"] == 300

        # Test gemini LLM config
        assert config["llm"]["gemini"]["provider"] == "gemini"
        assert config["llm"]["gemini"]["model"] == "gemini-2.5-flash"
        assert config["llm"]["gemini"]["api_key"] == "GEMINI_API_KEY"

        # Test tools config
        assert config["tools"]["mythril"]["timeout"] == 300
        assert config["tools"]["mythril"]["format"] == "json"
        assert config["tools"]["slither"]["timeout"] == 300
        assert config["tools"]["slither"]["format"] == "json"

        # Test services config
        assert config["services"]["mcp"]["host"] == "127.0.0.1"
        assert config["services"]["mcp"]["port"] == 8000
        assert config["services"]["generator"]["llm"] == "gemini"
        assert config["services"]["generator"]["framework"] == "hardhat"

        # Test output config
        assert config["output"]["directory"] == "argus"
        assert config["output"]["level"] == "debug"
        assert config["workdir"] == "."
        assert config["mode"] == "generator"

    def test_init_with_no_config_path(self):
        """Test initialization with no config path uses defaults."""
        config = ArgusConfig()

        assert config.config == ArgusConfig.get_default_config()

    def test_init_with_none_config_path(self):
        """Test initialization with None explicitly uses defaults."""
        config = ArgusConfig(config_path=None)

        assert config.config == ArgusConfig.get_default_config()

    def test_init_with_nonexistent_file(self):
        """Test initialization with non-existent file uses defaults."""
        config = ArgusConfig(config_path="/path/to/nonexistent/file.json")

        assert config.config == ArgusConfig.get_default_config()

    def test_init_with_valid_config_file(self, tmp_path):
        """Test initialization with valid config file loads correctly."""
        # Create a temporary config file
        config_file = tmp_path / "config.json"
        test_config = {
            "llm": {
                "anthropic": {
                    "provider": "anthropic",
                    "model": "claude-3-opus",
                    "api_key": "TEST_KEY",
                    "max_retries": 5,
                    "timeout": 600,
                },
                "gemini": {
                    "provider": "gemini",
                    "model": "gemini-pro",
                    "api_key": "TEST_KEY_2",
                    "max_retries": 5,
                    "timeout": 600,
                },
            },
            "tools": {
                "mythril": {"timeout": 400, "format": "text"},
                "slither": {"timeout": 500, "format": "text"},
            },
            "services": {
                "mcp": {"host": "localhost", "port": 9000},
            },
            "output": {"directory": "custom_output", "level": "info"},
            "workdir": "/custom/path",
            "mode": "orchestrator",
        }

        config_file.write_text(json.dumps(test_config))

        config = ArgusConfig(config_path=str(config_file))

        assert config.config == test_config
        assert config.config["llm"]["anthropic"]["provider"] == "anthropic"
        assert config.config["llm"]["gemini"]["model"] == "gemini-pro"
        assert config.config["output"]["directory"] == "custom_output"
        assert config.config["mode"] == "orchestrator"

    def test_get_simple_key(self):
        """Test getting a simple top-level key."""
        config = ArgusConfig()

        assert config.get("workdir") == "."

    def test_get_nested_key_single_level(self):
        """Test getting a nested key with dot notation (one level)."""
        config = ArgusConfig()

        llm_config = config.get("llm")
        assert "anthropic" in llm_config
        assert "gemini" in llm_config
        assert llm_config["anthropic"]["provider"] == "anthropic"
        assert llm_config["anthropic"]["model"] == "claude-sonnet-4-5-20250929"

    def test_get_nested_key_multiple_levels(self):
        """Test getting a nested key with dot notation (multiple levels)."""
        config = ArgusConfig()

        assert config.get("llm.anthropic.provider") == "anthropic"
        assert config.get("llm.anthropic.model") == "claude-sonnet-4-5-20250929"
        assert config.get("llm.anthropic.max_retries") == 3
        assert config.get("llm.gemini.provider") == "gemini"
        assert config.get("tools.mythril.timeout") == 300
        assert config.get("tools.slither.format") == "json"
        assert config.get("output.directory") == "argus"
        assert config.get("services.mcp.host") == "127.0.0.1"
        assert config.get("services.generator.llm") == "gemini"

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
        test_config = {"custom": {"nested": {"value": "test_value"}}}
        config_file.write_text(json.dumps(test_config))

        config = ArgusConfig(config_path=str(config_file))

        assert config.get("custom.nested.value") == "test_value"
        assert config.get("custom.nested") == {"value": "test_value"}
        assert config.get("custom") == {"nested": {"value": "test_value"}}

    def test_config_immutability_through_get(self):
        """Test that modifying returned values doesn't affect config."""
        config = ArgusConfig()

        llm_config = config.get("llm")

        # Modify the returned dict
        llm_config["anthropic"]["provider"] = "modified"

        # Original config should be modified (Python dict behavior)
        # This test documents current behavior
        assert config.get("llm.anthropic.provider") == "modified"

        # Note: If immutability is desired, the get method should return deep copies

    def test_invalid_json_file(self, tmp_path):
        """Test initialization with invalid JSON file."""
        config_file = tmp_path / "invalid.json"
        config_file.write_text("{ invalid json }")

        with pytest.raises(json.JSONDecodeError):
            ArgusConfig(config_path=str(config_file))

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
        test_config = {
            "llm": {"gemini": {"provider": "gemini", "model": "custom-model"}}
        }
        config_file.write_text(json.dumps(test_config))

        config2 = ArgusConfig(config_path=str(config_file))

        assert config1.get("llm.anthropic.provider") == "anthropic"
        assert config2.get("llm.gemini.provider") == "gemini"

        # Verify they are independent instances
        assert config1.config != config2.config


class TestConfigInitialize:
    """Test suite for config file discovery and initialization."""

    def test_initialize_without_config_file(self, tmp_path, monkeypatch):
        """Test initialize() when no config file exists."""
        # Change to a directory with no config files
        monkeypatch.chdir(tmp_path)

        config = initialize()

        # Should return default config
        assert config.config == ArgusConfig.get_default_config()

    def test_initialize_with_argus_json(self, tmp_path, monkeypatch):
        """Test initialize() discovers argus.json."""
        monkeypatch.chdir(tmp_path)

        # Create argus.json
        config_file = tmp_path / "argus.json"
        test_config = {
            "llm": {
                "anthropic": {
                    "provider": "anthropic",
                    "model": "test-model",
                }
            },
            "mode": "test_mode",
        }
        config_file.write_text(json.dumps(test_config))

        config = initialize()

        assert config.config == test_config
        assert config.get("mode") == "test_mode"
        assert config.get("llm.anthropic.model") == "test-model"

    def test_initialize_with_argus_config_json(self, tmp_path, monkeypatch):
        """Test initialize() discovers argus.config.json."""
        monkeypatch.chdir(tmp_path)

        # Create argus.config.json
        config_file = tmp_path / "argus.config.json"
        test_config = {
            "llm": {
                "gemini": {
                    "provider": "gemini",
                    "model": "config-test-model",
                }
            },
            "mode": "config_test_mode",
        }
        config_file.write_text(json.dumps(test_config))

        config = initialize()

        assert config.config == test_config
        assert config.get("mode") == "config_test_mode"
        assert config.get("llm.gemini.model") == "config-test-model"

    def test_initialize_prefers_argus_json_over_argus_config_json(
        self,
        tmp_path,
        monkeypatch,
    ):
        """Test initialize() prefers argus.json when both files exist."""
        monkeypatch.chdir(tmp_path)

        # Create both config files
        argus_json = tmp_path / "argus.json"
        argus_json_config = {
            "mode": "from_argus_json",
            "llm": {"anthropic": {"model": "json-model"}},
        }
        argus_json.write_text(json.dumps(argus_json_config))

        argus_config_json = tmp_path / "argus.config.json"
        argus_config_json_config = {
            "mode": "from_argus_config_json",
            "llm": {"anthropic": {"model": "config-json-model"}},
        }
        argus_config_json.write_text(json.dumps(argus_config_json_config))

        config = initialize()

        # Should use argus.json
        assert config.get("mode") == "from_argus_json"
        assert config.get("llm.anthropic.model") == "json-model"

    def test_initialize_with_invalid_json_in_argus_json(self, tmp_path, monkeypatch):
        """Test initialize() handles invalid JSON in argus.json."""
        monkeypatch.chdir(tmp_path)

        # Create invalid argus.json
        config_file = tmp_path / "argus.json"
        config_file.write_text("{ invalid json }")

        with pytest.raises(json.JSONDecodeError):
            initialize()

    def test_initialize_with_valid_argus_config_json_and_invalid_argus_json(
        self,
        tmp_path,
        monkeypatch,
    ):
        """Test initialize() behavior when argus.json is invalid but argus.config.json is valid."""
        monkeypatch.chdir(tmp_path)

        # Create invalid argus.json (will be tried first)
        argus_json = tmp_path / "argus.json"
        argus_json.write_text("{ invalid }")

        # Create valid argus.config.json
        argus_config_json = tmp_path / "argus.config.json"
        valid_config = {"mode": "backup_config"}
        argus_config_json.write_text(json.dumps(valid_config))

        # Should raise error when trying to parse argus.json
        # (current implementation doesn't fall back to argus.config.json on error)
        with pytest.raises(json.JSONDecodeError):
            initialize()

    def test_initialize_in_subdirectory(self, tmp_path, monkeypatch):
        """Test initialize() looks in current working directory."""
        # Create a subdirectory
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        monkeypatch.chdir(subdir)

        # Create config in parent directory (should not be found)
        parent_config = tmp_path / "argus.json"
        parent_config.write_text(json.dumps({"mode": "parent"}))

        # Create config in current directory
        subdir_config = subdir / "argus.json"
        subdir_config.write_text(json.dumps({"mode": "subdir"}))

        config = initialize()

        # Should find the config in current directory
        assert config.get("mode") == "subdir"

    def test_initialize_returns_argus_config_instance(self, tmp_path, monkeypatch):
        """Test initialize() returns an ArgusConfig instance."""
        monkeypatch.chdir(tmp_path)

        config = initialize()

        assert isinstance(config, ArgusConfig)
        assert hasattr(config, "config")
        assert hasattr(config, "get")
