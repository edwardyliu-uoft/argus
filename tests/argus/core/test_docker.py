"""
Tests for Docker utilities module.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from docker.errors import DockerException, ImageNotFound, APIError

from argus.core.docker import (
    check_docker_available,
    pull_image,
    get_project_root,
    run_docker_command,
)


class TestCheckDockerAvailable:
    """Tests for check_docker_available function."""

    @patch("argus.core.docker.docker.from_env")
    def test_docker_available(self, mock_from_env: Mock) -> None:
        """Test when Docker daemon is available."""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_from_env.return_value = mock_client

        is_available, error = check_docker_available()

        assert is_available is True
        assert error is None
        mock_client.ping.assert_called_once()

    @patch("argus.core.docker.docker.from_env")
    def test_docker_not_available(self, mock_from_env: Mock) -> None:
        """Test when Docker daemon is not running."""
        mock_from_env.side_effect = DockerException("Connection refused")

        is_available, error = check_docker_available()

        assert is_available is False
        assert error is not None
        assert "Docker daemon not running" in error

    @patch("argus.core.docker.docker.from_env")
    def test_docker_general_error(self, mock_from_env: Mock) -> None:
        """Test when there's a general Docker error."""
        mock_from_env.side_effect = Exception("Unknown error")

        is_available, error = check_docker_available()

        assert is_available is False
        assert error is not None
        assert "Docker error" in error


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


class TestGetProjectRoot:
    """Tests for get_project_root function."""

    def test_finds_hardhat_config_js(self, tmp_path: Path) -> None:
        """Test finding project root with hardhat.config.js."""
        # Create directory structure
        project_root = tmp_path / "project"
        contracts_dir = project_root / "contracts"
        contracts_dir.mkdir(parents=True)

        # Create hardhat config
        (project_root / "hardhat.config.js").touch()

        # Create contract file
        contract_file = contracts_dir / "MyContract.sol"
        contract_file.touch()

        result = get_project_root(str(contract_file))

        assert result == project_root

    def test_finds_hardhat_config_ts(self, tmp_path: Path) -> None:
        """Test finding project root with hardhat.config.ts."""
        project_root = tmp_path / "project"
        contracts_dir = project_root / "contracts"
        contracts_dir.mkdir(parents=True)

        (project_root / "hardhat.config.ts").touch()
        contract_file = contracts_dir / "MyContract.sol"
        contract_file.touch()

        result = get_project_root(str(contract_file))

        assert result == project_root

    def test_finds_package_json(self, tmp_path: Path) -> None:
        """Test finding project root with package.json."""
        project_root = tmp_path / "project"
        contracts_dir = project_root / "contracts"
        contracts_dir.mkdir(parents=True)

        (project_root / "package.json").touch()
        contract_file = contracts_dir / "MyContract.sol"
        contract_file.touch()

        result = get_project_root(str(contract_file))

        assert result == project_root

    def test_finds_foundry_toml(self, tmp_path: Path) -> None:
        """Test finding project root with foundry.toml."""
        project_root = tmp_path / "project"
        contracts_dir = project_root / "src"
        contracts_dir.mkdir(parents=True)

        (project_root / "foundry.toml").touch()
        contract_file = contracts_dir / "MyContract.sol"
        contract_file.touch()

        result = get_project_root(str(contract_file))

        assert result == project_root

    def test_finds_contracts_directory(self, tmp_path: Path) -> None:
        """Test finding project root by contracts directory."""
        project_root = tmp_path / "project"
        contracts_dir = project_root / "contracts"
        contracts_dir.mkdir(parents=True)

        contract_file = contracts_dir / "MyContract.sol"
        contract_file.touch()

        result = get_project_root(str(contract_file))

        assert result == project_root

    def test_no_indicators_returns_parent(self, tmp_path: Path) -> None:
        """Test returns file parent when no project indicators found."""
        contracts_dir = tmp_path / "random" / "path"
        contracts_dir.mkdir(parents=True)

        contract_file = contracts_dir / "MyContract.sol"
        contract_file.touch()

        result = get_project_root(str(contract_file))

        assert result == contracts_dir


class TestRunDockerCommand:
    """Tests for run_docker_command function."""

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

        result = run_docker_command(
            image="test:latest",
            command=["analyze", str(test_file)],
            project_root=project_root,
            file_path=str(test_file),
            timeout=60,
        )

        assert result["success"] is True
        assert result["exit_code"] == 0
        assert "Success output" in result["output"]
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

        result = run_docker_command(
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

        result = run_docker_command(
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

        run_docker_command(
            image="test:latest",
            command=["analyze", str(test_file)],
            project_root=project_root,
            file_path=str(test_file),
            timeout=60,
        )

        # Verify the command passed to container.run
        call_args = mock_client.containers.run.call_args
        command_arg = call_args[1]["command"]

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

        run_docker_command(
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

        run_docker_command(
            image="test:latest",
            command=["analyze", str(test_file)],
            project_root=project_root,
            file_path=str(test_file),
            timeout=60,
        )

        call_args = mock_client.containers.run.call_args
        volumes = call_args[1]["volumes"]

        # Verify volume is mounted as read-only
        assert any(vol["mode"] == "ro" for vol in volumes.values())
