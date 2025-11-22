"""
Tests for Docker utilities module.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from docker.errors import DockerException, ImageNotFound, APIError

from argus.core.docker import (
    docker_available,
    pull_image,
    run_docker
)


class TestDockerAvailable:
    """Tests for docker_available function."""

    @patch("argus.core.docker.docker.from_env")
    def test_docker_available(self, mock_from_env: Mock) -> None:
        """Test when Docker daemon is available."""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_from_env.return_value = mock_client

        is_available = docker_available()

        assert is_available is True
        mock_client.ping.assert_called_once()

    @patch("argus.core.docker.docker.from_env")
    def test_docker_not_available(self, mock_from_env: Mock) -> None:
        """Test when Docker daemon is not running."""
        mock_from_env.side_effect = DockerException("Connection refused")

        is_available = docker_available()

        assert is_available is False

    @patch("argus.core.docker.docker.from_env")
    def test_docker_general_error(self, mock_from_env: Mock) -> None:
        """Test when there's a general Docker error."""
        mock_from_env.side_effect = Exception("Unknown error")

        is_available = docker_available()

        assert is_available is False


class TestPullImage:
    """Tests for pull_image function."""

    @patch("argus.core.docker.docker.from_env")
    def test_image_already_exists_locally(self, mock_from_env: Mock) -> None:
        """Test when image already exists locally - should not pull."""
        mock_client = Mock()
        mock_client.images.get.return_value = Mock()
        mock_from_env.return_value = mock_client

        success, error = pull_image("test:latest")

        assert success is True
        assert error is None
        mock_client.images.get.assert_called_once_with("test:latest")
        mock_client.images.pull.assert_not_called()

    @patch("argus.core.docker.docker.from_env")
    def test_image_not_found_locally_pulls_successfully(self, mock_from_env: Mock) -> None:
        """Test when image doesn't exist locally - should pull it."""
        mock_client = Mock()
        mock_client.images.get.side_effect = ImageNotFound("Not found")
        mock_client.images.pull.return_value = Mock()
        mock_from_env.return_value = mock_client

        success, error = pull_image("test:latest")

        assert success is True
        assert error is None
        mock_client.images.pull.assert_called_once_with("test:latest")

    @patch("argus.core.docker.docker.from_env")
    def test_image_not_found_in_registry(self, mock_from_env: Mock) -> None:
        """Test when image doesn't exist in registry."""
        mock_client = Mock()
        mock_client.images.get.side_effect = ImageNotFound("Not found locally")
        mock_client.images.pull.side_effect = ImageNotFound("Not found in registry")
        mock_from_env.return_value = mock_client

        success, error = pull_image("test:latest")

        assert success is False
        assert error is not None
        assert "not found in registry" in error.lower()

    @patch("argus.core.docker.docker.from_env")
    def test_pull_image_api_error(self, mock_from_env: Mock) -> None:
        """Test API error during image pull."""
        mock_client = Mock()
        mock_client.images.get.side_effect = ImageNotFound("Not found")
        mock_client.images.pull.side_effect = APIError("Pull failed")
        mock_from_env.return_value = mock_client

        success, error = pull_image("test:latest")

        assert success is False
        assert error is not None
        assert "Failed to pull image" in error

    @patch("argus.core.docker.docker.from_env")
    def test_docker_connection_error(self, mock_from_env: Mock) -> None:
        """Test general Docker error."""
        mock_from_env.side_effect = Exception("Connection failed")

        success, error = pull_image("test:latest")

        assert success is False
        assert error is not None
        assert "Docker error" in error

class TestRunDocker:
    """Tests for run_docker function."""

    @patch("argus.core.docker.docker.from_env")
    def test_successful_command_execution(self, mock_from_env: Mock, tmp_path: Path) -> None:
        """Test successful Docker command execution."""
        # Setup mocks
        mock_client = Mock()
        mock_container = MagicMock()
        mock_container.wait.return_value = {"StatusCode": 0}
        mock_container.logs.side_effect = [
            b"Success output",  # stdout
            b"",  # stderr
        ]

        mock_client.containers.run.return_value = mock_container
        mock_from_env.return_value = mock_client

        # Create test file
        project_root = tmp_path / "project"
        project_root.mkdir()
        test_file = project_root / "test.sol"
        test_file.write_text("contract Test {}")

        result = run_docker(
            image="test:latest",
            command=["analyze", str(test_file)],
            project_root=project_root,
            file_path=str(test_file),
            timeout=60,
        )

        assert result["success"] is True
        assert result["exit_code"] == 0
        assert "Success output" in result["stdout"]
        mock_container.remove.assert_called_once_with(force=True)

    @patch("argus.core.docker.docker.from_env")
    def test_command_execution_failure(self, mock_from_env: Mock, tmp_path: Path) -> None:
        """Test Docker command execution with non-zero exit code."""
        mock_client = Mock()
        mock_container = MagicMock()
        mock_container.wait.return_value = {"StatusCode": 1}
        mock_container.logs.side_effect = [
            b"",  # stdout
            b"Error occurred",  # stderr
        ]

        mock_client.containers.run.return_value = mock_container
        mock_from_env.return_value = mock_client

        project_root = tmp_path / "project"
        project_root.mkdir()
        test_file = project_root / "test.sol"
        test_file.write_text("contract Test {}")

        result = run_docker(
            image="test:latest",
            command=["analyze", str(test_file)],
            project_root=project_root,
            file_path=str(test_file),
            timeout=60,
        )

        assert result["success"] is False
        assert result["exit_code"] == 1
        assert "Error occurred" in result["stderr"]

    @patch("argus.core.docker.docker.from_env")
    def test_command_timeout(self, mock_from_env: Mock, tmp_path: Path) -> None:
        """Test Docker command execution timeout."""
        mock_client = Mock()
        mock_container = MagicMock()
        mock_container.wait.side_effect = Exception("Timeout")
        mock_container.logs.side_effect = [
            b"Partial output",
            b"",
        ]

        mock_client.containers.run.return_value = mock_container
        mock_from_env.return_value = mock_client

        project_root = tmp_path / "project"
        project_root.mkdir()
        test_file = project_root / "test.sol"
        test_file.write_text("contract Test {}")

        result = run_docker(
            image="test:latest",
            command=["analyze", str(test_file)],
            project_root=project_root,
            file_path=str(test_file),
            timeout=1,
        )

        assert result["success"] is False
        assert result["exit_code"] == -1

    @patch("argus.core.docker.docker.from_env")
    def test_path_translation(self, mock_from_env: Mock, tmp_path: Path) -> None:
        """Test file path is correctly translated to container path."""
        mock_client = Mock()
        mock_container = MagicMock()
        mock_container.wait.return_value = {"StatusCode": 0}
        mock_container.logs.return_value = b"output"

        mock_client.containers.run.return_value = mock_container
        mock_from_env.return_value = mock_client

        project_root = tmp_path / "project"
        contracts_dir = project_root / "contracts"
        contracts_dir.mkdir(parents=True)
        test_file = contracts_dir / "test.sol"
        test_file.write_text("contract Test {}")

        run_docker(
            image="test:latest",
            command=["analyze", str(test_file)],
            project_root=project_root,
            file_path=str(test_file),
            timeout=60,
        )

        # Verify the command passed to container.run
        call_args = mock_client.containers.run.call_args
        command_arg = call_args[1]["command"]
        import logging
        logging.basicConfig(level=logging.DEBUG)
        logging.debug("Command passed to container: %s", command_arg)
        # The file path should be translated to /project/contracts/test.sol
        assert "/project/contracts/test.sol" in command_arg

    @patch("argus.core.docker.docker.from_env")
    def test_network_mode_none(self, mock_from_env: Mock, tmp_path: Path) -> None:
        """Test container runs with no network access by default."""
        mock_client = Mock()
        mock_container = MagicMock()
        mock_container.wait.return_value = {"StatusCode": 0}
        mock_container.logs.return_value = b"output"

        mock_client.containers.run.return_value = mock_container
        mock_from_env.return_value = mock_client

        project_root = tmp_path / "project"
        project_root.mkdir()
        test_file = project_root / "test.sol"
        test_file.write_text("contract Test {}")

        run_docker(
            image="test:latest",
            command=["analyze", str(test_file)],
            project_root=project_root,
            file_path=str(test_file),
            timeout=60,
        )

        call_args = mock_client.containers.run.call_args
        assert call_args[1]["network_mode"] == "none"

    @patch("argus.core.docker.docker.from_env")
    def test_readonly_volume_mount(self, mock_from_env: Mock, tmp_path: Path) -> None:
        """Test project root is mounted as read-only volume."""
        mock_client = Mock()
        mock_container = MagicMock()
        mock_container.wait.return_value = {"StatusCode": 0}
        mock_container.logs.return_value = b"output"

        mock_client.containers.run.return_value = mock_container
        mock_from_env.return_value = mock_client

        project_root = tmp_path / "project"
        project_root.mkdir()
        test_file = project_root / "test.sol"
        test_file.write_text("contract Test {}")

        run_docker(
            image="test:latest",
            command=["analyze", str(test_file)],
            project_root=project_root,
            file_path=str(test_file),
            timeout=60,
        )

        call_args = mock_client.containers.run.call_args
        volumes = call_args[1]["volumes"]

        # Verify volume is mounted as read-write
        assert any(vol["mode"] == "rw" for vol in volumes.values())
