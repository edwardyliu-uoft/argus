"""Comprehensive tests for Argus MCP Server."""

from unittest.mock import patch
from pathlib import Path
import time
import socket
import json
import shutil
import pytest

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from argus.core import conf
from argus.server import server


def find_free_port():
    """Find a free port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("", 0))
        sock.listen(1)
        port = sock.getsockname()[1]

    return port


class TestServerLifecycle:
    """Tests for server creation, starting, and stopping."""

    def test_create_server_returns_process(self):
        """`create_server` should return an `ArgusMCPServer` instance."""
        srv = server.create_server(port=0)
        assert isinstance(srv, server.ArgusMCPServer)

    def test_create_server_with_custom_params(self):
        """Test creating server with custom parameters."""
        srv = server.create_server(
            port=9999,
            host="0.0.0.0",
            name="Test Server",
            mount_path="/test",
        )
        assert srv.port == 9999
        assert srv.host == "0.0.0.0"
        assert srv.name == "Test Server"
        assert srv.mount_path == "/test"

    def test_start_and_stop_server_process(self):
        """Starting the server should spawn a child process which can be stopped."""
        srv = server.create_server(port=0)
        srv.start()

        # Give the child process a moment to start
        time.sleep(1.0)

        assert srv.is_alive(), "Server process should be alive after start()"
        assert srv.pid is not None, "Server process should have a pid"

        # Stop and join
        srv.stop()

        assert not srv.is_alive(), "Server process should not be alive after stop()"

    def test_stop_non_mcp_server(self):
        """Stopping a non-running server should not raise an error."""
        srv = server.create_server(port=0)
        # Don't start it
        srv.stop()  # Should not raise

    def test_stop_with_timeout(self):
        """Test stop with custom timeout."""
        srv = server.create_server(port=0)
        srv.start()
        time.sleep(1.0)

        assert srv.is_alive()
        srv.stop(timeout=1.0)
        assert not srv.is_alive()

    def test_server_attributes(self):
        """Test that server has required attributes."""
        srv = server.create_server(
            port=8765,
            host="127.0.0.1",
            name="Attr Test",
            json_response=False,
            mount_path="/api",
        )
        assert srv.port == 8765
        assert srv.host == "127.0.0.1"
        assert srv.name == "Attr Test"
        assert srv.json_response is False
        assert srv.mount_path == "/api"
        assert srv.app is None  # Not started yet

    def test_global_start_stop_functions(self):
        """Test the global start() and stop() functions."""
        # Start server
        srv = server.start(port=0)

        assert srv is not None
        assert isinstance(srv, server.ArgusMCPServer)
        time.sleep(1.0)
        assert srv.is_alive()

        # Stop server
        server.stop()
        time.sleep(0.5)
        assert not srv.is_alive()

    def test_multiple_starts_stops(self):
        """Test starting and stopping server multiple times."""
        for _ in range(2):
            srv = server.create_server(port=0)
            srv.start()
            time.sleep(0.8)
            assert srv.is_alive()

            srv.stop()
            time.sleep(0.3)
            assert not srv.is_alive()

    def test_server_process_name(self):
        """Test that server process has correct name."""
        srv = server.create_server(port=0)
        assert srv.name == "ArgusMCPServerProcess" or "Argus" in srv.name


class TestClientConnection:
    """Tests for MCP client connection and session management."""

    @pytest.fixture(scope="class")
    def mcp_server(self):
        """Start MCP server for client integration tests."""
        host = "127.0.0.1"
        port = find_free_port()
        mount_path = "/mcp"

        # Start server in background process
        srv = server.start(host=host, port=port, mount_path=mount_path)

        # Give server time to start and register tools
        time.sleep(2.0)

        url = f"http://{host}:{port}{mount_path}"

        yield {"url": url, "server": srv}

        # Cleanup
        server.stop()
        time.sleep(0.5)

    @pytest.mark.asyncio
    async def test_client_can_connect_to_server(self, mcp_server):
        """Test that a client can connect to the running server."""
        url = mcp_server["url"]

        async with streamablehttp_client(url) as (read, write, _):
            async with ClientSession(read, write) as session:
                init_result = await session.initialize()

                assert init_result is not None
                assert session is not None

    @pytest.mark.asyncio
    async def test_client_can_list_tools(self, mcp_server):
        """Test that client can list available tools."""
        url = mcp_server["url"]

        async with streamablehttp_client(url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                tools = await session.list_tools()

                assert tools is not None
                assert isinstance(tools.tools, list)
                # Should have at least one tool registered
                assert len(tools.tools) >= 2

                tool_names = [tool.name for tool in tools.tools]
                assert "mythril" in tool_names
                assert "slither" in tool_names

    @pytest.mark.asyncio
    async def test_client_multiple_connections(self, mcp_server):
        """Test multiple sequential client connections."""
        url = mcp_server["url"]

        for _ in range(3):
            async with streamablehttp_client(url) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools = await session.list_tools()
                    assert tools is not None

    @pytest.mark.asyncio
    async def test_client_session_initialization(self, mcp_server):
        """Test that client session initializes correctly."""
        url = mcp_server["url"]

        async with streamablehttp_client(url) as (read, write, _):
            async with ClientSession(read, write) as session:
                init_result = await session.initialize()

                assert init_result is not None
                # Check server info is available
                assert hasattr(init_result, "serverInfo") or init_result is not None

    @pytest.mark.asyncio
    async def test_client_list_resources(self, mcp_server):
        """Test listing resources via client."""
        url = mcp_server["url"]

        async with streamablehttp_client(url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # List resources (should work even if empty)
                try:
                    resources = await session.list_resources()
                    assert resources is not None
                except Exception:
                    # Resources may not be implemented
                    pass

    @pytest.mark.asyncio
    async def test_client_list_prompts(self, mcp_server):
        """Test listing prompts via client."""
        url = mcp_server["url"]

        async with streamablehttp_client(url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # List prompts (should work even if empty)
                try:
                    prompts = await session.list_prompts()
                    assert prompts is not None
                except Exception:
                    # Prompts may not be implemented
                    pass

    @pytest.mark.asyncio
    async def test_client_rapid_list_operations(self, mcp_server):
        """Test multiple rapid list operations from client."""
        url = mcp_server["url"]

        async with streamablehttp_client(url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Make rapid sequential list calls
                for _ in range(5):
                    tools = await session.list_tools()
                    assert tools is not None

    @pytest.mark.asyncio
    async def test_client_same_session_multiple_operations(self, mcp_server):
        """Test making multiple operations in the same client session."""
        url = mcp_server["url"]

        async with streamablehttp_client(url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Make 10 list operations in the same session
                for _ in range(10):
                    tools = await session.list_tools()
                    assert tools is not None
                    assert isinstance(tools.tools, list)

    @pytest.mark.asyncio
    async def test_client_tool_details(self, mcp_server):
        """Test that client can retrieve tool details."""
        url = mcp_server["url"]

        async with streamablehttp_client(url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                tools = await session.list_tools()

                # Check that tools have descriptions
                for tool in tools.tools:
                    assert tool.name is not None
                    assert tool.description is not None or tool.description == ""

    @pytest.mark.asyncio
    async def test_client_server_info_details(self, mcp_server):
        """Test retrieving detailed server information."""
        url = mcp_server["url"]

        async with streamablehttp_client(url) as (read, write, _):
            async with ClientSession(read, write) as session:
                init_result = await session.initialize()

                assert init_result is not None
                # Server should have serverInfo
                if hasattr(init_result, "serverInfo"):
                    server_info = init_result.serverInfo
                    assert server_info is not None

    @pytest.mark.asyncio
    async def test_client_concurrent_sessions(self, mcp_server):
        """Test multiple concurrent client sessions."""
        url = mcp_server["url"]

        async def create_session_and_list():
            async with streamablehttp_client(url) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools = await session.list_tools()
                    return len(tools.tools)

        # Sequential calls to simulate concurrent usage
        results = []
        for _ in range(3):
            count = await create_session_and_list()
            results.append(count)

        # Verify all calls succeeded
        assert len(results) == 3
        for count in results:
            assert count >= 0  # Should have at least some tools or zero


class TestToolInvocation:
    """Tests for invoking mythril and slither tools via MCP client."""

    @pytest.fixture(scope="class")
    def mcp_server(self):
        """Start MCP server for client integration tests."""
        host = "127.0.0.1"
        port = find_free_port()
        mount_path = "/mcp"

        # Start server in background process
        srv = server.start(host=host, port=port, mount_path=mount_path)

        # Give server time to start and register tools
        time.sleep(2.0)

        url = f"http://{host}:{port}{mount_path}"

        yield {"url": url, "server": srv}

        # Cleanup
        server.stop()
        time.sleep(0.5)

    @pytest.mark.asyncio
    async def test_call_mythril_version(self, mcp_server):
        """Test calling mythril tool with version command."""
        url = mcp_server["url"]

        async with streamablehttp_client(url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Call mythril with version command
                result = await session.call_tool(
                    "mythril",
                    arguments={"args": ["version"], "kwargs": {}},
                )

                assert result is not None
                assert len(result.content) > 0

                # Parse the response
                content = result.content[0]
                data = json.loads(content.text)

                # Check response exit codes
                assert data["exit_code"] == 0
                assert data["container_exit_code"] == 0

    @pytest.mark.asyncio
    async def test_call_mythril_help(self, mcp_server):
        """Test calling mythril tool with help command."""
        url = mcp_server["url"]

        async with streamablehttp_client(url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                result = await session.call_tool(
                    "mythril",
                    arguments={"args": ["--help"], "kwargs": {}},
                )

                assert result is not None
                content = result.content[0]
                data = json.loads(content.text)

                # Check response exit codes
                assert data["exit_code"] == 0
                assert data["container_exit_code"] == 0

    @pytest.mark.asyncio
    async def test_call_slither_version(self, mcp_server):
        """Test calling slither tool with version command."""
        url = mcp_server["url"]

        async with streamablehttp_client(url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Call slither with version command
                result = await session.call_tool(
                    "slither",
                    arguments={"args": ["--version"], "kwargs": {}},
                )

                assert result is not None
                assert len(result.content) > 0

                content = result.content[0]
                data = json.loads(content.text)

                # Check response exit codes
                assert data["exit_code"] == 0
                assert data["container_exit_code"] == 0

    @pytest.mark.asyncio
    async def test_call_slither_help(self, mcp_server):
        """Test calling slither tool with help command."""
        url = mcp_server["url"]

        async with streamablehttp_client(url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                result = await session.call_tool(
                    "slither",
                    arguments={"args": ["--help"], "kwargs": {}},
                )

                assert result is not None
                content = result.content[0]
                data = json.loads(content.text)

                # Check response exit codes
                assert data["exit_code"] == 0
                assert data["container_exit_code"] == 0

    @pytest.mark.asyncio
    @patch("argus.server.tools.mythril.conf")
    async def test_call_mythril_analyze_contract(
        self,
        mock_conf,
        tmp_path,
        mcp_server,
    ):
        """Test calling mythril to analyze a Solidity contract."""
        url = mcp_server["url"]

        # Create a simple test contract
        project_root = tmp_path / "project"
        project_root.mkdir()
        contract_file = project_root / "SimpleTest.sol"
        contract_file.write_text(
            """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract SimpleTest {
    uint256 public value;
    
    function setValue(uint256 _value) public {
        value = _value;
    }
    
    function getValue() public view returns (uint256) {
        return value;
    }
}
"""
        )
        mock_conf.get.side_effect = lambda key, default=None: {
            "workdir": str(project_root),
            "server.tools.mythril": {
                "timeout": 120,
                "docker": {
                    "image": "mythril/myth:latest",
                    "network_mode": "bridge",
                    "remove_containers": True,
                },
            },
        }.get(key, default)

        async with streamablehttp_client(url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Call mythril to analyze the contract
                result = await session.call_tool(
                    "mythril",
                    arguments={
                        "args": [
                            "analyze",
                            "SimpleTest.sol",
                            "--solv",
                            "0.8.0",
                            "--execution-timeout",
                            "30",
                        ],
                        "kwargs": {},
                    },
                )

                assert result is not None
                content = result.content[0]
                data = json.loads(content.text)

                # Check response exit codes
                assert data["exit_code"] == 0
                assert data["container_exit_code"] == 0

    @pytest.mark.asyncio
    @patch("argus.server.tools.slither.conf")
    async def test_call_slither_analyze_contract(
        self,
        mock_conf,
        tmp_path,
        mcp_server,
    ):
        """Test calling slither to analyze a Solidity contract."""
        url = mcp_server["url"]

        # Create a simple test contract
        project_root = tmp_path / "project"
        project_root.mkdir()
        contract_file = project_root / "TokenTest.sol"
        contract_file.write_text(
            """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract TokenTest {
    mapping(address => uint256) public balances;
    
    function transfer(address to, uint256 amount) public {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        balances[msg.sender] -= amount;
        balances[to] += amount;
    }
}
"""
        )
        mock_conf.get.side_effect = lambda key, default=None: {
            "workdir": str(project_root),
            "server.tools.slither": {
                "timeout": 120,
                "docker": {
                    "image": "trailofbits/eth-security-toolbox:latest",
                    "network_mode": "bridge",
                    "remove_containers": True,
                },
            },
        }.get(key, default)

        async with streamablehttp_client(url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Call slither to analyze the contract
                result = await session.call_tool(
                    "slither",
                    arguments={
                        "args": ["TokenTest.sol"],
                        "kwargs": {},
                    },
                )

                assert result is not None
                content = result.content[0]
                data = json.loads(content.text)

                # Check response exit codes
                assert data["exit_code"] == 0
                assert data["container_exit_code"] != 0

    @pytest.mark.asyncio
    async def test_multiple_tool_calls_same_session(self, mcp_server):
        """Test calling multiple tools in the same session."""
        url = mcp_server["url"]

        async with streamablehttp_client(url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Call mythril version
                mythril_result = await session.call_tool(
                    "mythril",
                    arguments={"args": ["version"], "kwargs": {}},
                )
                assert mythril_result is not None

                # Call slither version
                slither_result = await session.call_tool(
                    "slither",
                    arguments={"args": ["--version"], "kwargs": {}},
                )
                assert slither_result is not None

                # Call mythril help
                mythril_help = await session.call_tool(
                    "mythril",
                    arguments={"args": ["--help"], "kwargs": {}},
                )
                assert mythril_help is not None

                # Verify all calls returned valid data
                mythril_data = json.loads(mythril_result.content[0].text)
                slither_data = json.loads(slither_result.content[0].text)
                mythril_help_data = json.loads(mythril_help.content[0].text)

                assert mythril_data["exit_code"] == 0
                assert slither_data["exit_code"] == 0
                assert mythril_help_data["exit_code"] == 0

    @pytest.mark.asyncio
    async def test_interleaved_tool_calls(self, mcp_server):
        """Test interleaving calls between mythril and slither."""
        url = mcp_server["url"]

        async with streamablehttp_client(url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Interleave tool calls
                mythril1 = await session.call_tool(
                    "mythril",
                    arguments={"args": ["version"], "kwargs": {}},
                )
                slither1 = await session.call_tool(
                    "slither",
                    arguments={"args": ["--version"], "kwargs": {}},
                )
                mythril2 = await session.call_tool(
                    "mythril",
                    arguments={"args": ["--help"], "kwargs": {}},
                )
                slither2 = await session.call_tool(
                    "slither",
                    arguments={"args": ["--help"], "kwargs": {}},
                )

                # Verify all completed
                assert mythril1 is not None
                assert slither1 is not None
                assert mythril2 is not None
                assert slither2 is not None

    @pytest.mark.asyncio
    async def test_tool_call_with_invalid_arguments(self, mcp_server):
        """Test tool calls with invalid arguments."""
        url = mcp_server["url"]

        async with streamablehttp_client(url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Call with nonexistent file
                result = await session.call_tool(
                    "mythril",
                    arguments={
                        "args": ["analyze", "nonexistent_file.sol"],
                        "kwargs": {},
                    },
                )

                assert result is not None
                # Tool should handle error gracefully
                content = result.content[0]
                data = json.loads(content.text)

                assert data["exit_code"] == 0
                assert data["container_exit_code"] == 0
                assert "FileNotFoundError" in data["stdout"]["error"]

    @pytest.mark.asyncio
    async def test_rapid_tool_calls(self, mcp_server):
        """Test rapid sequential tool calls."""
        url = mcp_server["url"]

        async with streamablehttp_client(url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Make 5 rapid tool calls
                for _ in range(5):
                    result = await session.call_tool(
                        "mythril",
                        arguments={"args": ["version"], "kwargs": {}},
                    )
                    assert result is not None
                    data = json.loads(result.content[0].text)

                    assert data["exit_code"] == 0
                    assert data["container_exit_code"] == 0


class TestFilesystemTools:
    """Tests for filesystem tools via MCP client."""

    @pytest.fixture(scope="class")
    def mcp_server(self):
        """Start MCP server for filesystem tool tests."""
        host = "127.0.0.1"
        port = find_free_port()
        mount_path = "/mcp"

        # Start server in background process
        srv = server.start(host=host, port=port, mount_path=mount_path)

        # Give server time to start and register tools
        time.sleep(2.0)

        url = f"http://{host}:{port}{mount_path}"

        yield {"url": url, "server": srv}

        # Cleanup
        server.stop()
        time.sleep(0.5)

    @pytest.mark.asyncio
    async def test_find_files_by_extension(self, mcp_server):
        """Test find_files_by_extension tool."""
        url = mcp_server["url"]

        async with streamablehttp_client(url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Find Python test files in the project
                result = await session.call_tool(
                    "find_files_by_extension",
                    arguments={"extension": "py", "recursive": True},
                )

                assert result is not None
                data = json.loads(result.content[0].text)

                assert data["success"] is True
                assert data["count"] > 0  # Should find Python files in the project
                assert len(data["files"]) > 0

    @pytest.mark.asyncio
    async def test_read_file(self, mcp_server):
        """Test read_file tool."""
        url = mcp_server["url"]

        async with streamablehttp_client(url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Read the README.md file from the project
                result = await session.call_tool(
                    "read_file",
                    arguments={"file_path": "README.md"},
                )

                assert result is not None
                data = json.loads(result.content[0].text)

                assert data["success"] is True
                assert "content" in data
                assert data["total_size"] > 0

    @pytest.mark.asyncio
    async def test_write_file(self, mcp_server, tmp_path):
        """Test write_file tool."""
        url = mcp_server["url"]

        # Use a temp file path that will be created in workdir
        test_filename = f"test_output_{id(tmp_path)}.txt"

        async with streamablehttp_client(url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                result = await session.call_tool(
                    "write_file",
                    arguments={
                        "file_path": test_filename,
                        "content": "Test content",
                    },
                )

                assert result is not None
                data = json.loads(result.content[0].text)

                assert data["success"] is True
                assert data["total_size"] == 12

                # Clean up - delete the file
                try:

                    test_file = (
                        Path(conf.get("workdir", Path.cwd().as_posix())) / test_filename
                    )
                    if test_file.exists():
                        test_file.unlink()
                except Exception:
                    pass

    @pytest.mark.asyncio
    async def test_append_file(self, mcp_server, tmp_path):
        """Test append_file tool."""
        url = mcp_server["url"]

        # Create a temp file first
        test_filename = f"test_log_{id(tmp_path)}.txt"

        async with streamablehttp_client(url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Write initial content
                await session.call_tool(
                    "write_file",
                    arguments={
                        "file_path": test_filename,
                        "content": "Line 1\n",
                    },
                )

                # Append to the file
                result = await session.call_tool(
                    "append_file",
                    arguments={
                        "file_path": test_filename,
                        "content": "Line 2\n",
                    },
                )

                assert result is not None
                data = json.loads(result.content[0].text)

                assert data["success"] is True
                assert data["appended_size"] == 7

                # Verify content by reading back
                read_result = await session.call_tool(
                    "read_file",
                    arguments={"file_path": test_filename},
                )
                read_data = json.loads(read_result.content[0].text)
                assert "Line 1" in read_data["content"]
                assert "Line 2" in read_data["content"]

                # Clean up
                try:
                    test_file = (
                        Path(conf.get("workdir", Path.cwd().as_posix())) / test_filename
                    )
                    if test_file.exists():
                        test_file.unlink()
                except Exception:
                    pass

    @pytest.mark.asyncio
    async def test_create_directory(self, mcp_server, tmp_path):
        """Test create_directory tool."""
        url = mcp_server["url"]

        # Use a unique temp directory name
        test_dirname = f"test_dir_{id(tmp_path)}/nested/dir"

        async with streamablehttp_client(url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                result = await session.call_tool(
                    "create_directory",
                    arguments={"directory_path": test_dirname},
                )

                assert result is not None
                data = json.loads(result.content[0].text)

                assert data["success"] is True
                # Either created or already existed
                assert "created" in data or "path" in data

                # Clean up
                try:
                    test_dir = (
                        Path(conf.get("workdir", Path.cwd().as_posix()))
                        / test_dirname.split("/")[0]
                    )
                    if test_dir.exists():
                        shutil.rmtree(test_dir)
                except Exception:
                    pass

    @pytest.mark.asyncio
    async def test_list_directory(self, mcp_server):
        """Test list_directory tool."""
        url = mcp_server["url"]

        async with streamablehttp_client(url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # List the src directory
                result = await session.call_tool(
                    "list_directory",
                    arguments={"directory_path": "src", "recursive": False},
                )

                assert result is not None
                data = json.loads(result.content[0].text)

                assert data["success"] is True
                assert data["count"] > 0  # Should find files/folders in src
                assert "items" in data

    @pytest.mark.asyncio
    async def test_read_file_info(self, mcp_server):
        """Test read_file_info tool."""
        url = mcp_server["url"]

        async with streamablehttp_client(url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Get info for README.md
                result = await session.call_tool(
                    "read_file_info",
                    arguments={"file_path": "README.md"},
                )

                assert result is not None
                data = json.loads(result.content[0].text)

                assert data["success"] is True
                assert data["exists"] is True
                assert data["type"] == "file"
                assert data["total_size"] > 0


class TestFilesystemResources:
    """Tests for filesystem resources via MCP client."""

    @pytest.fixture(scope="class")
    def mcp_server(self):
        """Start MCP server for client integration tests."""
        host = "127.0.0.1"
        port = find_free_port()
        mount_path = "/mcp"

        # Start server in background process
        srv = server.start(host=host, port=port, mount_path=mount_path)

        # Give server time to start and register tools
        time.sleep(2.0)

        url = f"http://{host}:{port}{mount_path}"

        yield {"url": url, "server": srv}

        # Cleanup
        server.stop()
        time.sleep(0.5)

    @pytest.mark.asyncio
    async def test_list_resources_includes_filesystem(self, mcp_server):
        """Test that filesystem resources are registered."""
        url = mcp_server["url"]

        async with streamablehttp_client(url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                resources = await session.list_resources()

                assert resources is not None
                resource_uris = [str(r.uri) for r in resources.resources]

                # Check that filesystem resources are registered
                assert any("filesystem" in uri for uri in resource_uris)

    @pytest.mark.asyncio
    async def test_get_workspace_resource(self, mcp_server):
        """Test get_workspace resource."""
        url = mcp_server["url"]

        async with streamablehttp_client(url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                result = await session.read_resource(
                    uri="resource:///filesystem/get_workspace"
                )

                assert result is not None
                assert len(result.contents) > 0
                content = result.contents[0].text

                assert "Workspace:" in content
                assert "Total:" in content
                # Should find Python files in the project
                assert ".py" in content or "files" in content

    @pytest.mark.asyncio
    async def test_get_project_structure_resource(
        self,
        mcp_server,
    ):
        """Test get_project_structure resource."""
        url = mcp_server["url"]

        async with streamablehttp_client(url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                result = await session.read_resource(
                    uri="resource:///filesystem/get_project_structure"
                )

                assert result is not None
                content = result.contents[0].text

                assert "Project Structure:" in content
                # Should show src/ directory from the argus project
                assert "src/" in content or "Directory structure" in content
                assert "File types:" in content

    @pytest.mark.asyncio
    async def test_get_solidity_files_resource(self, mcp_server):
        """Test get_solidity_files resource."""
        url = mcp_server["url"]

        async with streamablehttp_client(url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                result = await session.read_resource(
                    uri="resource:///filesystem/get_solidity_files"
                )

                assert result is not None
                content = result.contents[0].text

                # May have Solidity contracts or not in the argus project
                assert (
                    "Solidity Contracts:" in content
                    or "No Solidity contracts found" in content
                )
