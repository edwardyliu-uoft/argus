"""
Tests for Mythril controller.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from argus.tools.mythril.controller import MythrilController


class TestMythrilController:
    """Tests for MythrilController class."""

    @pytest.fixture
    def controller(self) -> MythrilController:
        """Create a MythrilController instance for testing."""
        return MythrilController()

    @pytest.mark.asyncio
    @patch("argus.tools.mythril.controller.argus_docker.docker_available")
    async def test_docker_unavailable(
        self,
        mock_check_docker: Mock,
        controller: MythrilController
    ) -> None:
        """Test execution when Docker is not available."""
        mock_check_docker.return_value = False

        result = await controller.execute(command="myth", args=["test.sol"])

        assert result["success"] is False
        assert result["error"]["type"] == "docker_unavailable"
        assert "Docker daemon not running" in result["error"]["raw_output"]

    @pytest.mark.asyncio
    @patch("argus.tools.mythril.controller.argus_docker.run_docker")
    @patch("argus.tools.mythril.controller.argus_docker.pull_image")
    @patch("argus.tools.mythril.controller.argus_docker.docker_available")
    @patch("argus.tools.mythril.controller.conf")
    async def test_image_pull_failure(
        self,
        mock_config: Mock,
        mock_check_docker: Mock,
        mock_pull_image: Mock,
        mock_run_docker: Mock,
        controller: MythrilController
    ) -> None:
        """Test execution when Docker image pull fails."""
        mock_check_docker.return_value = True
        mock_pull_image.return_value = (False, "Image not found in registry")
        mock_config.get.side_effect = lambda key, default: {
            "tools.mythril.docker.image": "mythril/myth:latest",
            "tools.mythril.docker.network_mode": "none",
            "tools.mythril.docker.remove_containers": True,
            "tools.mythril.timeout": 300,
            "tools.mythril.format": "json",
            "workdir": "/test/project"
        }.get(key, default)

        result = await controller.execute(command="myth", args=["test.sol"])

        assert result["success"] is False
        assert result["error"]["type"] == "docker_image_not_found"
        assert "Image not found in registry" in result["error"]["raw_output"]

    @pytest.mark.asyncio
    @patch("argus.tools.mythril.controller.argus_docker.run_docker")
    @patch("argus.tools.mythril.controller.argus_docker.pull_image")
    @patch("argus.tools.mythril.controller.argus_docker.docker_available")
    @patch("argus.tools.mythril.controller.conf")
    async def test_successful_execution_with_json_output(
        self,
        mock_config: Mock,
        mock_check_docker: Mock,
        mock_pull_image: Mock,
        mock_run_docker: Mock,
        controller: MythrilController,
        tmp_path: Path
    ) -> None:
        """Test successful Mythril execution with JSON output."""
        # Setup mocks
        mock_check_docker.return_value = True
        mock_pull_image.return_value = (True, None)

        project_root = str(tmp_path)
        mock_config.get.side_effect = lambda key, default: {
            "tools.mythril.docker.image": "mythril/myth:latest",
            "tools.mythril.docker.network_mode": "none",
            "tools.mythril.docker.remove_containers": True,
            "tools.mythril.timeout": 300,
            "tools.mythril.format": "json",
            "workdir": project_root
        }.get(key, default)

        # Mock successful Docker execution
        mock_run_docker.return_value = {
            "success": True,
            "stdout": '{"success": true, "issues": []}',
            "stderr": "",
            "exit_code": 0
        }

        result = await controller.execute(command="myth", args=["test.sol"])

        assert result["success"] is True
        assert result["error"] is None
        assert '{"success": true, "issues": []}' in result["output"]

        # Verify run_docker_command was called with correct arguments
        mock_run_docker.assert_called_once()
        call_args = mock_run_docker.call_args[0]
        assert call_args[0] == "mythril/myth:latest"  # image
        assert isinstance(call_args[1], list)  # command as list
        assert "myth" in call_args[1]
        assert isinstance(call_args[2], Path)  # project_root as Path
        assert call_args[4] == 300  # timeout
        assert call_args[5] == "none"  # network_mode
        assert call_args[6] is True  # remove_container

    @pytest.mark.asyncio
    @patch("argus.tools.mythril.controller.argus_docker.run_docker")
    @patch("argus.tools.mythril.controller.argus_docker.pull_image")
    @patch("argus.tools.mythril.controller.argus_docker.docker_available")
    @patch("argus.tools.mythril.controller.conf")
    async def test_execution_timeout(
        self,
        mock_config: Mock,
        mock_check_docker: Mock,
        mock_pull_image: Mock,
        mock_run_docker: Mock,
        controller: MythrilController,
        tmp_path: Path
    ) -> None:
        """Test Mythril execution timeout handling."""
        mock_check_docker.return_value = True
        mock_pull_image.return_value = (True, None)

        project_root = str(tmp_path)
        mock_config.get.side_effect = lambda key, default: {
            "tools.mythril.docker.image": "mythril/myth:latest",
            "tools.mythril.docker.network_mode": "none",
            "tools.mythril.docker.remove_containers": True,
            "tools.mythril.timeout": 300,
            "tools.mythril.format": "json",
            "workdir": project_root
        }.get(key, default)

        # Mock timeout error
        mock_run_docker.return_value = {
            "success": False,
            "stdout": "",
            "stderr": "Container timeout after 300s",
            "exit_code": -1
        }

        result = await controller.execute(command="myth", args=["test.sol"])

        assert result["success"] is False
        assert result["error"]["type"] == "timeout"
        assert "timed out after 300 seconds" in result["error"]["raw_output"]

    @pytest.mark.asyncio
    @patch("argus.tools.mythril.controller.argus_docker.run_docker")
    @patch("argus.tools.mythril.controller.argus_docker.pull_image")
    @patch("argus.tools.mythril.controller.argus_docker.docker_available")
    @patch("argus.tools.mythril.controller.conf")
    async def test_compilation_error(
        self,
        mock_config: Mock,
        mock_check_docker: Mock,
        mock_pull_image: Mock,
        mock_run_docker: Mock,
        controller: MythrilController,
        tmp_path: Path
    ) -> None:
        """Test Mythril execution with compilation error."""
        mock_check_docker.return_value = True
        mock_pull_image.return_value = (True, None)

        project_root = str(tmp_path)
        mock_config.get.side_effect = lambda key, default: {
            "tools.mythril.docker.image": "mythril/myth:latest",
            "tools.mythril.docker.network_mode": "none",
            "tools.mythril.docker.remove_containers": True,
            "tools.mythril.timeout": 300,
            "tools.mythril.format": "json",
            "workdir": project_root
        }.get(key, default)

        # Mock compilation error
        mock_run_docker.return_value = {
            "success": False,
            "stdout": "",
            "stderr": "Compilation failed: Syntax error in contract",
            "exit_code": 1
        }

        result = await controller.execute(command="myth", args=["test.sol"])

        assert result["success"] is False
        assert result["error"]["type"] == "compilation_error"
        assert "Compilation failed" in result["error"]["raw_output"]

    @pytest.mark.asyncio
    @patch("argus.tools.mythril.controller.argus_docker.run_docker")
    @patch("argus.tools.mythril.controller.argus_docker.pull_image")
    @patch("argus.tools.mythril.controller.argus_docker.docker_available")
    @patch("argus.tools.mythril.controller.conf")
    async def test_docker_container_error(
        self,
        mock_config: Mock,
        mock_check_docker: Mock,
        mock_pull_image: Mock,
        mock_run_docker: Mock,
        controller: MythrilController,
        tmp_path: Path
    ) -> None:
        """Test Mythril execution with Docker container error."""
        mock_check_docker.return_value = True
        mock_pull_image.return_value = (True, None)

        project_root = str(tmp_path)
        mock_config.get.side_effect = lambda key, default: {
            "tools.mythril.docker.image": "mythril/myth:latest",
            "tools.mythril.docker.network_mode": "none",
            "tools.mythril.docker.remove_containers": True,
            "tools.mythril.timeout": 300,
            "tools.mythril.format": "json",
            "workdir": project_root
        }.get(key, default)

        # Mock Docker container error
        mock_run_docker.return_value = {
            "success": False,
            "stdout": "",
            "stderr": "Container failed to start",
            "exit_code": 125
        }

        result = await controller.execute(command="myth", args=["test.sol"])

        assert result["success"] is False
        assert result["error"]["type"] == "docker_container_error"
        assert "Container failed to start" in result["error"]["raw_output"]

    @pytest.mark.asyncio
    @patch("argus.tools.mythril.controller.argus_docker.run_docker")
    @patch("argus.tools.mythril.controller.argus_docker.pull_image")
    @patch("argus.tools.mythril.controller.argus_docker.docker_available")
    @patch("argus.tools.mythril.controller.conf")
    async def test_default_target_to_project_root(
        self,
        mock_config: Mock,
        mock_check_docker: Mock,
        mock_pull_image: Mock,
        mock_run_docker: Mock,
        controller: MythrilController,
        tmp_path: Path
    ) -> None:
        """Test that target defaults to project root when no args provided."""
        mock_check_docker.return_value = True
        mock_pull_image.return_value = (True, None)

        project_root = str(tmp_path)
        mock_config.get.side_effect = lambda key, default: {
            "tools.mythril.docker.image": "mythril/myth:latest",
            "tools.mythril.docker.network_mode": "none",
            "tools.mythril.docker.remove_containers": True,
            "tools.mythril.timeout": 300,
            "tools.mythril.format": "json",
            "workdir": project_root
        }.get(key, default)

        mock_run_docker.return_value = {
            "success": True,
            "stdout": "{}",
            "stderr": "",
            "exit_code": 0
        }

        result = await controller.execute(command="myth", args=[])

        assert result["success"] is True

        # Verify the command was called (project root is passed as file_path, not in command)
        mock_run_docker.assert_called_once()

    @pytest.mark.asyncio
    @patch("argus.tools.mythril.controller.argus_docker.run_docker")
    @patch("argus.tools.mythril.controller.argus_docker.pull_image")
    @patch("argus.tools.mythril.controller.argus_docker.docker_available")
    @patch("argus.tools.mythril.controller.conf")
    async def test_json_format_flag_added(
        self,
        mock_config: Mock,
        mock_check_docker: Mock,
        mock_pull_image: Mock,
        mock_run_docker: Mock,
        controller: MythrilController,
        tmp_path: Path
    ) -> None:
        """Test that --json flag is added when format is json."""
        mock_check_docker.return_value = True
        mock_pull_image.return_value = (True, None)

        project_root = str(tmp_path)
        mock_config.get.side_effect = lambda key, default: {
            "tools.mythril.docker.image": "mythril/myth:latest",
            "tools.mythril.docker.network_mode": "none",
            "tools.mythril.docker.remove_containers": True,
            "tools.mythril.timeout": 300,
            "tools.mythril.format": "json",
            "workdir": project_root
        }.get(key, default)

        mock_run_docker.return_value = {
            "success": True,
            "stdout": "{}",
            "stderr": "",
            "exit_code": 0
        }

        result = await controller.execute(command="myth", args=["test.sol"])

        # Verify -o json flag is in the command (Mythril uses -o instead of --json)
        call_args = mock_run_docker.call_args[0]
        command_list = call_args[1]
        assert "-o" in command_list and "json" in command_list

    @pytest.mark.asyncio
    @patch("argus.tools.mythril.controller.argus_docker.run_docker")
    @patch("argus.tools.mythril.controller.argus_docker.pull_image")
    @patch("argus.tools.mythril.controller.argus_docker.docker_available")
    @patch("argus.tools.mythril.controller.conf")
    async def test_invalid_json_output(
        self,
        mock_config: Mock,
        mock_check_docker: Mock,
        mock_pull_image: Mock,
        mock_run_docker: Mock,
        controller: MythrilController,
        tmp_path: Path
    ) -> None:
        """Test handling of invalid JSON output."""
        mock_check_docker.return_value = True
        mock_pull_image.return_value = (True, None)

        project_root = str(tmp_path)
        mock_config.get.side_effect = lambda key, default: {
            "tools.mythril.docker.image": "mythril/myth:latest",
            "tools.mythril.docker.network_mode": "none",
            "tools.mythril.docker.remove_containers": True,
            "tools.mythril.timeout": 300,
            "tools.mythril.format": "json",
            "workdir": project_root
        }.get(key, default)

        # Mock output with invalid JSON
        mock_run_docker.return_value = {
            "success": True,
            "stdout": "Not valid JSON output",
            "stderr": "",
            "exit_code": 0
        }

        result = await controller.execute(command="myth", args=["test.sol"])

        # Should still succeed but return the raw output
        assert result["success"] is True
        assert "Not valid JSON output" in result["output"]

    @pytest.mark.asyncio
    @patch("argus.tools.mythril.controller.argus_docker.run_docker")
    @patch("argus.tools.mythril.controller.argus_docker.pull_image")
    @patch("argus.tools.mythril.controller.argus_docker.docker_available")
    @patch("argus.tools.mythril.controller.conf")
    async def test_exception_handling(
        self,
        mock_config: Mock,
        mock_check_docker: Mock,
        mock_pull_image: Mock,
        mock_run_docker: Mock,
        controller: MythrilController
    ) -> None:
        """Test exception handling during execution."""
        mock_check_docker.return_value = True
        mock_pull_image.return_value = (True, None)
        mock_config.get.side_effect = Exception("Unexpected error")

        result = await controller.execute(command="myth", args=["test.sol"])

        assert result["success"] is False
        assert result["error"]["type"] == "crash"
        assert "Unexpected error" in result["error"]["raw_output"]

    @pytest.mark.asyncio
    @patch("argus.tools.mythril.controller.argus_docker.run_docker")
    @patch("argus.tools.mythril.controller.argus_docker.pull_image")
    @patch("argus.tools.mythril.controller.argus_docker.docker_available")
    @patch("argus.tools.mythril.controller.conf")
    async def test_additional_args_passed_correctly(
        self,
        mock_config: Mock,
        mock_check_docker: Mock,
        mock_pull_image: Mock,
        mock_run_docker: Mock,
        controller: MythrilController,
        tmp_path: Path
    ) -> None:
        """Test that additional arguments are passed correctly to Docker command."""
        mock_check_docker.return_value = True
        mock_pull_image.return_value = (True, None)

        project_root = str(tmp_path)
        mock_config.get.side_effect = lambda key, default: {
            "tools.mythril.docker.image": "mythril/myth:latest",
            "tools.mythril.docker.network_mode": "none",
            "tools.mythril.docker.remove_containers": True,
            "tools.mythril.timeout": 300,
            "tools.mythril.format": "json",
            "workdir": project_root
        }.get(key, default)

        mock_run_docker.return_value = {
            "success": True,
            "stdout": "{}",
            "stderr": "",
            "exit_code": 0
        }

        # Pass additional arguments
        result = await controller.execute(
            command="myth",
            args=["test.sol", "--max-depth", "10", "--solver-timeout", "30000"]
        )

        assert result["success"] is True

        # Verify additional args are in the command
        call_args = mock_run_docker.call_args[0]
        command_list = call_args[1]
        assert "--max-depth" in command_list
        assert "10" in command_list
        assert "--solver-timeout" in command_list
        assert "30000" in command_list
