"""
Tests for the Hello World Plugin
"""

import pytest
from argus_example_plugin import ExamplePlugin


class TestExamplePlugin:
    """Test cases for ExamplePlugin"""

    @pytest.fixture
    def plugin(self):
        """Create a plugin instance for testing"""
        plugin = ExamplePlugin()
        plugin.initialize()
        return plugin

    @pytest.fixture
    def plugin_with_config(self):
        """Create a plugin instance with custom configuration"""
        plugin = ExamplePlugin()
        plugin.initialize({"default_language": "cn", "include_emoji": False})
        return plugin

    def test_plugin_properties(self, plugin):
        """Test that plugin has required properties"""
        assert plugin.name == "example"
        assert plugin.version == "0.1.0"
        assert plugin.description is not None
        assert plugin.initialized is True

    def test_plugin_tools_registered(self, plugin):
        """Test that tools are properly registered"""
        assert "greet" in plugin.tools
        assert "greet_multiple" in plugin.tools
        assert callable(plugin.tools["greet"])
        assert callable(plugin.tools["greet_multiple"])

    @pytest.mark.asyncio
    async def test_greet_default(self, plugin):
        """Test greeting with default parameters"""
        result = await plugin.greet()
        assert result["success"] is True
        assert result["name"] == "Edward Liu"
        assert result["language"] == "en"
        assert "Hello" in result["greeting"]

    @pytest.mark.asyncio
    async def test_greet_with_name(self, plugin):
        """Test greeting with custom name"""
        result = await plugin.greet(name="Alice")
        assert result["success"] is True
        assert result["name"] == "Alice"
        assert "Alice" in result["greeting"]

    @pytest.mark.asyncio
    async def test_greet_spanish(self, plugin):
        """Test Spanish greeting"""
        result = await plugin.greet(name="Carlos", language="es")
        assert result["success"] is True
        assert result["language"] == "es"
        assert "¡Hola" in result["greeting"]
        assert "Carlos" in result["greeting"]

    @pytest.mark.asyncio
    async def test_greet_french(self, plugin):
        """Test French greeting"""
        result = await plugin.greet(name="Marie", language="fr")
        assert result["success"] is True
        assert result["language"] == "fr"
        assert "Bonjour" in result["greeting"]

    @pytest.mark.asyncio
    async def test_greet_japanese(self, plugin):
        """Test Japanese greeting"""
        result = await plugin.greet(name="Yuki", language="ja")
        assert result["success"] is True
        assert result["language"] == "ja"
        assert "こんにちは" in result["greeting"]

    @pytest.mark.asyncio
    async def test_greet_invalid_language(self, plugin):
        """Test greeting with unsupported language"""
        result = await plugin.greet(language="invalid")
        assert result["success"] is False
        assert "error" in result
        assert "supported_languages" in result

    @pytest.mark.asyncio
    async def test_greet_with_config(self, plugin_with_config):
        """Test greeting uses configuration defaults"""
        result = await plugin_with_config.greet(name="Test")
        assert result["success"] is True
        assert result["language"] == "cn"  # From config

    @pytest.mark.asyncio
    async def test_greet_multiple_default(self, plugin):
        """Test greeting multiple people with defaults"""
        result = await plugin.greet_multiple()
        assert result["success"] is True
        assert result["count"] == 1
        assert len(result["greetings"]) == 1

    @pytest.mark.asyncio
    async def test_greet_multiple_names(self, plugin):
        """Test greeting multiple people"""
        names = ["Alice", "Bob", "Charlie"]
        result = await plugin.greet_multiple(names=names, language="en")

        assert result["success"] is True
        assert result["count"] == 3
        assert len(result["greetings"]) == 3

        for name, greeting in zip(names, result["greetings"]):
            assert name in greeting

    @pytest.mark.asyncio
    async def test_greet_multiple_spanish(self, plugin):
        """Test greeting multiple people in Spanish"""
        names = ["Ana", "Luis"]
        result = await plugin.greet_multiple(names=names, language="es")
        assert result["success"] is True
        assert result["language"] == "es"
        assert result["count"] == 2
        for greeting in result["greetings"]:
            assert "¡Hola" in greeting

    @pytest.mark.asyncio
    async def test_greet_multiple_invalid_language(self, plugin):
        """Test greeting multiple with invalid language"""
        result = await plugin.greet_multiple(names=["Test"], language="invalid")
        assert result["success"] is False
        assert "error" in result

    def test_config_schema(self, plugin):
        """Test that config schema is defined"""
        schema = plugin.config_schema
        assert schema is not None
        assert "properties" in schema
        assert "default_language" in schema["properties"]
        assert "include_emoji" in schema["properties"]

    def test_config_validation(self, plugin):
        """Test config validation"""
        # Valid config
        valid_config = {"default_language": "en", "include_emoji": True}
        assert plugin.config_validate(valid_config) is True

        # Invalid config (wrong language)
        invalid_config = {"default_language": "invalid_lang"}
        assert plugin.config_validate(invalid_config) is False
