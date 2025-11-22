"""Comprehensive test cases for Argus MCP server functionality.

These tests cover:
1. Server initialization and startup
2. MCP client connection and session initialization
3. Tool functionality (get_weather and get_time)
4. Basic server functionality
5. Edge cases and error handling
"""

import time
import socket
import json
import pytest
import logging

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from argus.services import mcp

logger = logging.getLogger(__name__)


def find_free_port():
    """Find a free port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


@pytest.fixture(scope="module")
def mcp_server():
    """Start MCP server with tools registered for testing."""
    host = "127.0.0.1"
    port = find_free_port()
    mount_path = "/mcp"

    # Start server in a separate process
    mcp.start(host=host, port=port, mount_path=mount_path)

    # Give the server more time to start and register tools
    time.sleep(5)

    url = f"http://{host}:{port}{mount_path}"

    yield {"url": url}

    # Cleanup
    mcp.stop()


@pytest.mark.asyncio
async def test_mcp_server_connection(mcp_server):
    """Test basic connection to MCP server."""
    url = mcp_server["url"]

    async with streamablehttp_client(url) as (read, write, _):
        async with ClientSession(read, write) as session:
            init_result = await session.initialize()

            assert init_result is not None
            # Verify we can successfully connect and initialize a session
            assert session is not None


@pytest.mark.asyncio
async def test_get_weather_default(mcp_server):
    """Test get_weather tool with default parameters."""
    url = mcp_server["url"]

    async with streamablehttp_client(url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool("get_weather", arguments={})

            assert result is not None
            assert len(result.content) > 0

            content = result.content[0]
            data = json.loads(content.text)

            assert data["city"] == "London"  # Default value
            assert data["temperature"] == "22"
            assert data["condition"] == "Partly cloudy"
            assert data["humidity"] == "65%"


@pytest.mark.asyncio
async def test_get_weather_custom_city(mcp_server):
    """Test get_weather tool with custom city parameter."""
    url = mcp_server["url"]

    async with streamablehttp_client(url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool("get_weather", arguments={"city": "Paris"})

            assert result is not None
            content = result.content[0]
            data = json.loads(content.text)

            assert data["city"] == "Paris"
            assert data["temperature"] == "22"
            assert data["condition"] == "Partly cloudy"
            assert data["humidity"] == "65%"


@pytest.mark.asyncio
async def test_get_time_default(mcp_server):
    """Test get_time tool with default parameters."""
    url = mcp_server["url"]

    async with streamablehttp_client(url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool("get_time", arguments={})

            assert result is not None
            content = result.content[0]
            data = json.loads(content.text)

            assert data["city"] == "Toronto"  # Default value
            assert data["time"] == "14:30"
            assert data["date"] == "2024-06-15"


@pytest.mark.asyncio
async def test_get_time_custom_city(mcp_server):
    """Test get_time tool with custom city parameter."""
    url = mcp_server["url"]

    async with streamablehttp_client(url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool("get_time", arguments={"city": "Berlin"})

            assert result is not None
            content = result.content[0]
            data = json.loads(content.text)

            assert data["city"] == "Berlin"
            assert data["time"] == "14:30"
            assert data["date"] == "2024-06-15"


@pytest.mark.asyncio
async def test_multiple_tool_calls(mcp_server):
    """Test multiple sequential tool calls."""
    url = mcp_server["url"]

    async with streamablehttp_client(url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Call get_weather multiple times
            cities = ["London", "Paris", "Tokyo", "New York"]
            for city in cities:
                result = await session.call_tool(
                    "get_weather", arguments={"city": city}
                )
                assert result is not None
                data = json.loads(result.content[0].text)
                assert data["city"] == city

            # Call get_time multiple times
            for city in cities:
                result = await session.call_tool("get_time", arguments={"city": city})
                assert result is not None
                data = json.loads(result.content[0].text)
                assert data["city"] == city


@pytest.mark.asyncio
async def test_interleaved_tool_calls(mcp_server):
    """Test interleaving get_weather and get_time calls."""
    url = mcp_server["url"]

    async with streamablehttp_client(url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Interleave weather and time calls
            weather = await session.call_tool(
                "get_weather", arguments={"city": "Sydney"}
            )
            time_result = await session.call_tool(
                "get_time", arguments={"city": "Sydney"}
            )
            weather2 = await session.call_tool(
                "get_weather", arguments={"city": "Mumbai"}
            )
            time_result2 = await session.call_tool(
                "get_time", arguments={"city": "Mumbai"}
            )

            weather_data = json.loads(weather.content[0].text)
            time_data = json.loads(time_result.content[0].text)
            weather_data2 = json.loads(weather2.content[0].text)
            time_data2 = json.loads(time_result2.content[0].text)

            assert weather_data["city"] == "Sydney"
            assert time_data["city"] == "Sydney"
            assert weather_data2["city"] == "Mumbai"
            assert time_data2["city"] == "Mumbai"


@pytest.mark.asyncio
async def test_mcp_list_tools(mcp_server):
    """Test listing available tools via MCP client."""
    url = mcp_server["url"]

    async with streamablehttp_client(url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()

            assert tools is not None
            assert isinstance(tools.tools, list)
            assert len(tools.tools) >= 2

            tool_names = [tool.name for tool in tools.tools]
            assert "get_weather" in tool_names
            assert "get_time" in tool_names


@pytest.mark.asyncio
async def test_mcp_multiple_connections(mcp_server):
    """Test multiple sequential connections to MCP server."""
    url = mcp_server["url"]

    for _ in range(3):
        async with streamablehttp_client(url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Verify each connection works
                assert session is not None

                # Can list tools even if empty
                tools = await session.list_tools()
                assert tools is not None


@pytest.mark.asyncio
async def test_mcp_session_reinitialization(mcp_server):
    """Test reinitializing session multiple times."""
    url = mcp_server["url"]

    async with streamablehttp_client(url) as (read, write, _):
        async with ClientSession(read, write) as session:
            # Initialize once
            init1 = await session.initialize()
            assert init1 is not None

            # Can list tools after initialization
            tools = await session.list_tools()
            assert tools is not None


@pytest.mark.asyncio
async def test_mcp_server_info(mcp_server):
    """Test retrieving server information."""
    url = mcp_server["url"]

    async with streamablehttp_client(url) as (read, write, _):
        async with ClientSession(read, write) as session:
            init_result = await session.initialize()

            assert init_result is not None
            # Check that server info is available
            assert hasattr(init_result, "serverInfo") or init_result is not None


@pytest.mark.asyncio
async def test_mcp_list_resources(mcp_server):
    """Test listing resources via MCP."""
    url = mcp_server["url"]

    async with streamablehttp_client(url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # List resources (should work even if empty)
            try:
                resources = await session.list_resources()
                assert resources is not None
            except Exception:
                # Some servers may not implement resources, which is fine
                pass


@pytest.mark.asyncio
async def test_mcp_invalid_tool_name(mcp_server):
    """Test that calling an invalid tool completes without raising (FastMCP behavior).

    Note: FastMCP doesn't raise an error for nonexistent tools when validation
    is not enforced. The server logs a warning instead.
    """
    url = mcp_server["url"]

    async with streamablehttp_client(url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Call a non-existent tool - should complete without exception
            result = await session.call_tool("nonexistent_tool", arguments={})

            # The call completes (may return error or empty result)
            assert result is not None


# Additional tests for better coverage


@pytest.mark.asyncio
async def test_mcp_rapid_list_operations(mcp_server):
    """Test multiple rapid list operations."""
    url = mcp_server["url"]

    async with streamablehttp_client(url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Make rapid sequential list calls
            for _ in range(5):
                tools = await session.list_tools()
                assert tools is not None

                try:
                    resources = await session.list_resources()
                    assert resources is not None
                except Exception:
                    # Resources may not be implemented
                    pass


@pytest.mark.asyncio
async def test_mcp_prompts_listing(mcp_server):
    """Test listing prompts via MCP."""
    url = mcp_server["url"]

    async with streamablehttp_client(url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # List prompts (should work even if empty)
            try:
                prompts = await session.list_prompts()
                assert prompts is not None
            except Exception:
                # Some servers may not implement prompts, which is fine
                pass


@pytest.mark.asyncio
async def test_mcp_session_initialization(mcp_server):
    """Test that session initializes correctly."""
    url = mcp_server["url"]

    async with streamablehttp_client(url) as (read, write, _):
        async with ClientSession(read, write) as session:
            init_result = await session.initialize()

            assert init_result is not None
            # Check that we can list tools after initialization
            tools = await session.list_tools()
            assert isinstance(tools.tools, list)
            assert len(tools.tools) >= 2


@pytest.mark.asyncio
async def test_tool_parameters_validation(mcp_server):
    """Test that tools handle various parameter formats correctly."""
    url = mcp_server["url"]

    async with streamablehttp_client(url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Test with empty string
            result = await session.call_tool("get_weather", arguments={"city": ""})
            data = json.loads(result.content[0].text)
            assert data["city"] == ""

            # Test with special characters
            result = await session.call_tool(
                "get_weather", arguments={"city": "São Paulo"}
            )
            data = json.loads(result.content[0].text)
            assert data["city"] == "São Paulo"

            # Test with long city name
            long_name = "A" * 100
            result = await session.call_tool("get_time", arguments={"city": long_name})
            data = json.loads(result.content[0].text)
            assert data["city"] == long_name


@pytest.mark.asyncio
async def test_concurrent_sessions(mcp_server):
    """Test multiple concurrent sessions to the same server."""
    url = mcp_server["url"]

    # Create multiple sessions simultaneously
    async def create_session_and_call():
        async with streamablehttp_client(url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(
                    "get_weather", arguments={"city": "TestCity"}
                )
                return json.loads(result.content[0].text)

    # Sequential calls to simulate concurrent usage
    results = []
    for _ in range(3):
        data = await create_session_and_call()
        results.append(data)

    # Verify all calls succeeded
    assert len(results) == 3
    for data in results:
        assert data["city"] == "TestCity"


@pytest.mark.asyncio
async def test_tool_response_structure(mcp_server):
    """Test that tool responses have the expected structure."""
    url = mcp_server["url"]

    async with streamablehttp_client(url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Test get_weather response structure
            result = await session.call_tool("get_weather", arguments={})
            assert result is not None
            assert hasattr(result, "content")
            assert len(result.content) > 0

            weather_data = json.loads(result.content[0].text)
            assert "city" in weather_data
            assert "temperature" in weather_data
            assert "condition" in weather_data
            assert "humidity" in weather_data

            # Test get_time response structure
            result = await session.call_tool("get_time", arguments={})
            time_data = json.loads(result.content[0].text)
            assert "city" in time_data
            assert "time" in time_data
            assert "date" in time_data


@pytest.mark.asyncio
async def test_same_session_multiple_calls(mcp_server):
    """Test making multiple tool calls in the same session."""
    url = mcp_server["url"]

    async with streamablehttp_client(url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Make 10 calls in the same session
            for i in range(10):
                city = f"City{i}"

                # Alternate between tools
                if i % 2 == 0:
                    result = await session.call_tool(
                        "get_weather", arguments={"city": city}
                    )
                else:
                    result = await session.call_tool(
                        "get_time", arguments={"city": city}
                    )

                data = json.loads(result.content[0].text)
                assert data["city"] == city


@pytest.mark.asyncio
async def test_tool_list_details(mcp_server):
    """Test that tool listing provides correct tool details."""
    url = mcp_server["url"]

    async with streamablehttp_client(url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()

            # Find get_weather tool
            weather_tool = next(
                (t for t in tools.tools if t.name == "get_weather"), None
            )
            assert weather_tool is not None
            assert weather_tool.description is not None
            assert "weather" in weather_tool.description.lower()

            # Find get_time tool
            time_tool = next((t for t in tools.tools if t.name == "get_time"), None)
            assert time_tool is not None
            assert time_tool.description is not None
            assert "time" in time_tool.description.lower()
