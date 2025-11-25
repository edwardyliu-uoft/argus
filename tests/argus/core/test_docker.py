"""Tests for Argus Docker management toolkit."""

from unittest.mock import Mock, patch
import pytest
from docker.errors import DockerException, ImageNotFound, APIError, ContainerError

from argus.core.docker import docker_available, pull_image, run_docker


class TestDockerAvailable:
    """Tests for docker_available function."""

    @patch("argus.core.docker.docker.from_env")
    def test_docker_available_success(self, mock_from_env):
        """Test when Docker daemon is available."""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_from_env.return_value = mock_client

        assert docker_available() is True
        mock_client.ping.assert_called_once()

    @patch("argus.core.docker.docker.from_env")
    def test_docker_not_available_docker_exception(self, mock_from_env):
        """Test when Docker daemon is not running."""
        mock_from_env.side_effect = DockerException("Docker not running")

        assert docker_available() is False

    @patch("argus.core.docker.docker.from_env")
    def test_docker_not_available_generic_exception(self, mock_from_env):
        """Test when unexpected error occurs."""
        mock_from_env.side_effect = Exception("Unexpected error")

        assert docker_available() is False


class TestPullImage:
    """Tests for pull_image function."""

    @patch("argus.core.docker.docker.from_env")
    def test_pull_policy_never_image_exists(self, mock_from_env):
        """Test 'never' policy when image exists locally."""
        mock_client = Mock()
        mock_client.images.get.return_value = Mock()
        mock_from_env.return_value = mock_client

        success, error = pull_image("test:latest", pull_policy="never")

        assert success is True
        assert error is None
        mock_client.images.get.assert_called_once_with("test:latest")
        mock_client.images.pull.assert_not_called()

    @patch("argus.core.docker.docker.from_env")
    def test_pull_policy_never_image_not_found(self, mock_from_env):
        """Test 'never' policy when image doesn't exist locally."""
        mock_client = Mock()
        mock_client.images.get.side_effect = ImageNotFound("Not found")
        mock_from_env.return_value = mock_client

        success, error = pull_image("test:latest", pull_policy="never")

        assert success is False
        assert "not found" in error.lower()
        mock_client.images.pull.assert_not_called()

    @patch("argus.core.docker.docker.from_env")
    def test_pull_policy_if_not_present_exists(self, mock_from_env):
        """Test 'if-not-present' policy when image exists."""
        mock_client = Mock()
        mock_client.images.get.return_value = Mock()
        mock_from_env.return_value = mock_client

        success, error = pull_image("test:latest", pull_policy="if-not-present")

        assert success is True
        assert error is None
        mock_client.images.pull.assert_not_called()

    @patch("argus.core.docker.docker.from_env")
    def test_pull_policy_if_not_present_not_exists(self, mock_from_env):
        """Test 'if-not-present' policy when image doesn't exist."""
        mock_client = Mock()
        mock_client.images.get.side_effect = ImageNotFound("Not found")
        mock_client.images.pull.return_value = Mock()
        mock_from_env.return_value = mock_client

        success, error = pull_image("test:latest", pull_policy="if-not-present")

        assert success is True
        assert error is None
        # Check that pull was called with image and platform parameter
        mock_client.images.pull.assert_called_once()
        call_args = mock_client.images.pull.call_args
        assert call_args[0][0] == "test:latest"
        assert "platform" in call_args[1]

    @patch("argus.core.docker.docker.from_env")
    def test_pull_policy_always(self, mock_from_env):
        """Test 'always' policy pulls image regardless."""
        mock_client = Mock()
        mock_client.images.pull.return_value = Mock()
        mock_from_env.return_value = mock_client

        success, error = pull_image("test:latest", pull_policy="always")

        assert success is True
        assert error is None
        # Check that pull was called with image and platform parameter
        mock_client.images.pull.assert_called_once()
        call_args = mock_client.images.pull.call_args
        assert call_args[0][0] == "test:latest"
        assert "platform" in call_args[1]

    @patch("argus.core.docker.docker.from_env")
    def test_pull_policy_invalid(self, mock_from_env):
        """Test invalid pull policy."""
        mock_client = Mock()
        mock_from_env.return_value = mock_client

        success, error = pull_image("test:latest", pull_policy="invalid")

        assert success is False
        assert "Unrecognized pull_policy" in error

    @patch("argus.core.docker.docker.from_env")
    def test_pull_image_not_found_in_registry(self, mock_from_env):
        """Test pulling non-existent image from registry."""
        mock_client = Mock()
        mock_client.images.get.side_effect = ImageNotFound("Not found")
        mock_client.images.pull.side_effect = ImageNotFound("Not in registry")
        mock_from_env.return_value = mock_client

        success, error = pull_image("nonexistent:latest", pull_policy="if-not-present")

        assert success is False
        assert "not found in registry" in error.lower()

    @patch("argus.core.docker.docker.from_env")
    def test_pull_api_error(self, mock_from_env):
        """Test API error during pull."""
        mock_client = Mock()
        mock_client.images.get.side_effect = ImageNotFound("Not found")
        mock_client.images.pull.side_effect = APIError("API error")
        mock_from_env.return_value = mock_client

        success, error = pull_image("test:latest", pull_policy="if-not-present")

        assert success is False
        assert "Failed to pull image" in error


class TestRunDocker:
    """Tests for run_docker function."""

    @patch("argus.core.docker.docker.from_env")
    def test_run_docker_success_string_command(self, mock_from_env, tmp_path):
        """Test successful execution with string command."""
        # Setup
        project_root = tmp_path / "project"
        project_root.mkdir()
        test_file = project_root / "test.py"
        test_file.write_text("print('hello')")

        mock_container = Mock()
        mock_container.wait.return_value = {"StatusCode": 0}
        mock_container.logs.side_effect = [
            b"output",  # stdout
            b"",  # stderr
        ]

        mock_client = Mock()
        mock_client.containers.run.return_value = mock_container
        mock_from_env.return_value = mock_client

        # Execute - command uses relative path
        result = run_docker(
            image="python:3.9",
            command="python test.py",
            project_root=project_root,
            timeout=30,
        )

        # Assert
        assert result["exit_code"] == 0
        assert result["container_exit_code"] == 0
        assert "output" in result["stdout"]
        mock_container.remove.assert_called_once()

    @patch("argus.core.docker.docker.from_env")
    def test_run_docker_with_arguments_list_command(self, mock_from_env, tmp_path):
        """Test execution with list command and arguments."""
        # Setup
        project_root = tmp_path / "project"
        project_root.mkdir()
        test_file = project_root / "script.sh"
        test_file.write_text("#!/bin/bash\necho $1")

        mock_container = Mock()
        mock_container.wait.return_value = {"StatusCode": 0}
        mock_container.logs.side_effect = [b"arg_value", b""]

        mock_client = Mock()
        mock_client.containers.run.return_value = mock_container
        mock_from_env.return_value = mock_client

        # Execute with relative path in command
        result = run_docker(
            image="bash:latest",
            command=["bash", "script.sh", "--arg", "value"],
            project_root=project_root,
            timeout=30,
        )

        # Assert
        assert result["exit_code"] == 0
        assert result["container_exit_code"] == 0
        call_args = mock_client.containers.run.call_args
        command_arg = call_args[1]["command"]
        assert "script.sh" in command_arg
        assert "--arg" in command_arg
        assert "value" in command_arg

    @patch("argus.core.docker.docker.from_env")
    def test_run_docker_with_subdirectory_path(self, mock_from_env, tmp_path):
        """Test that relative paths work correctly with subdirectories."""
        # Setup
        project_root = tmp_path / "project"
        project_root.mkdir()
        subdir = project_root / "subdir"
        subdir.mkdir()
        test_file = subdir / "test.py"
        test_file.write_text("test")

        mock_container = Mock()
        mock_container.wait.return_value = {"StatusCode": 0}
        mock_container.logs.side_effect = [b"", b""]

        mock_client = Mock()
        mock_client.containers.run.return_value = mock_container
        mock_from_env.return_value = mock_client

        # Execute with relative path
        run_docker(
            image="python:3.9",
            command=["python", "subdir/test.py"],
            project_root=project_root,
            timeout=30,
        )

        # Assert command contains relative path
        call_args = mock_client.containers.run.call_args
        command_arg = call_args[1]["command"]
        assert "python" in command_arg
        assert "subdir/test.py" in command_arg

    @patch("argus.core.docker.docker.from_env")
    def test_run_docker_volume_mount(self, mock_from_env, tmp_path):
        """Test that volume mounting is configured correctly."""
        # Setup
        project_root = tmp_path / "project"
        project_root.mkdir()

        mock_container = Mock()
        mock_container.wait.return_value = {"StatusCode": 0}
        mock_container.logs.side_effect = [b"", b""]

        mock_client = Mock()
        mock_client.containers.run.return_value = mock_container
        mock_from_env.return_value = mock_client

        # Execute
        run_docker(
            image="python:3.9",
            command="python test.py",
            project_root=project_root,
            timeout=30,
        )

        # Assert volume mount configuration
        call_args = mock_client.containers.run.call_args
        volumes = call_args[1]["volumes"]
        assert str(project_root.resolve()) in volumes
        assert volumes[str(project_root.resolve())]["bind"] == "/project"
        assert volumes[str(project_root.resolve())]["mode"] == "rw"

    @patch("argus.core.docker.docker.from_env")
    def test_run_docker_non_zero_exit_code(self, mock_from_env, tmp_path):
        """Test handling of non-zero exit codes."""
        project_root = tmp_path / "project"
        project_root.mkdir()

        mock_container = Mock()
        mock_container.wait.return_value = {"StatusCode": 1}
        mock_container.logs.side_effect = [b"", b"error occurred"]

        mock_client = Mock()
        mock_client.containers.run.return_value = mock_container
        mock_from_env.return_value = mock_client

        result = run_docker(
            image="python:3.9",
            command="python test.py",
            project_root=project_root,
            timeout=30,
        )

        assert result["exit_code"] == 0  # Execution succeeded
        assert result["container_exit_code"] == 1  # But container had error
        assert "error occurred" in result["stderr"]

    @patch("argus.core.docker.docker.from_env")
    def test_run_docker_timeout(self, mock_from_env, tmp_path):
        """Test timeout handling."""
        project_root = tmp_path / "project"
        project_root.mkdir()

        mock_container = Mock()
        mock_container.wait.side_effect = Exception("Timeout")
        mock_container.logs.side_effect = [b"partial output", b""]

        mock_client = Mock()
        mock_client.containers.run.return_value = mock_container
        mock_from_env.return_value = mock_client

        result = run_docker(
            image="python:3.9",
            command="python test.py",
            project_root=project_root,
            timeout=1,
        )

        assert result["exit_code"] == -1
        assert result["container_exit_code"] is None
        assert "partial output" in result["stdout"]

    @patch("argus.core.docker.docker.from_env")
    def test_run_docker_container_error(self, mock_from_env, tmp_path):
        """Test ContainerError handling."""
        project_root = tmp_path / "project"
        project_root.mkdir()

        mock_client = Mock()
        container_error = ContainerError(
            container=Mock(),
            exit_status=126,
            command="python",
            image="python:3.9",
            stderr=b"Permission denied",
        )
        mock_client.containers.run.side_effect = container_error
        mock_from_env.return_value = mock_client

        result = run_docker(
            image="python:3.9",
            command="python test.py",
            project_root=project_root,
            timeout=30,
        )

        assert result["exit_code"] == -1
        assert result["container_exit_code"] == 126

    @patch("argus.core.docker.docker.from_env")
    def test_run_docker_api_error(self, mock_from_env, tmp_path):
        """Test Docker API error handling."""
        project_root = tmp_path / "project"
        project_root.mkdir()

        mock_client = Mock()
        mock_client.containers.run.side_effect = APIError("API error")
        mock_from_env.return_value = mock_client

        result = run_docker(
            image="python:3.9",
            command="python test.py",
            project_root=project_root,
            timeout=30,
        )

        assert result["exit_code"] == -1
        assert "Docker API error" in result["stderr"]

    @patch("argus.core.docker.docker.from_env")
    def test_run_docker_with_network_mode(self, mock_from_env, tmp_path):
        """Test custom network mode."""
        project_root = tmp_path / "project"
        project_root.mkdir()

        mock_container = Mock()
        mock_container.wait.return_value = {"StatusCode": 0}
        mock_container.logs.side_effect = [b"", b""]

        mock_client = Mock()
        mock_client.containers.run.return_value = mock_container
        mock_from_env.return_value = mock_client

        run_docker(
            image="python:3.9",
            command="python test.py",
            project_root=project_root,
            timeout=30,
            network_mode="bridge",
        )

        call_args = mock_client.containers.run.call_args
        assert call_args[1]["network_mode"] == "bridge"

    @patch("argus.core.docker.docker.from_env")
    def test_run_docker_remove_container_false(self, mock_from_env, tmp_path):
        """Test with remove_container=False."""
        project_root = tmp_path / "project"
        project_root.mkdir()

        mock_container = Mock()
        mock_container.wait.return_value = {"StatusCode": 0}
        mock_container.logs.side_effect = [b"", b""]

        mock_client = Mock()
        mock_client.containers.run.return_value = mock_container
        mock_from_env.return_value = mock_client

        run_docker(
            image="python:3.9",
            command="python test.py",
            project_root=project_root,
            timeout=30,
            remove_container=False,
        )

        mock_container.remove.assert_not_called()

    @patch("argus.core.docker.docker.from_env")
    def test_run_docker_with_complex_arguments(self, mock_from_env, tmp_path):
        """Test with complex command arguments (e.g., static analysis tools)."""
        project_root = tmp_path / "project"
        project_root.mkdir()
        test_file = project_root / "contract.sol"
        test_file.write_text("pragma solidity ^0.8.0;")

        mock_container = Mock()
        mock_container.wait.return_value = {"StatusCode": 0}
        mock_container.logs.side_effect = [b"analysis output", b""]

        mock_client = Mock()
        mock_client.containers.run.return_value = mock_container
        mock_from_env.return_value = mock_client

        # Simulate a tool like slither with multiple arguments
        result = run_docker(
            image="trailofbits/eth-security-toolbox:latest",
            command=[
                "slither",
                "contract.sol",
                "--json",
                "-",
                "--solc-args",
                "--optimize",
            ],
            project_root=project_root,
            timeout=60,
        )

        assert result["exit_code"] == 0
        call_args = mock_client.containers.run.call_args
        command_arg = call_args[1]["command"]
        # Verify relative path is used
        assert "contract.sol" in command_arg
        # Verify other arguments preserved
        assert "--json" in command_arg
        assert "--solc-args" in command_arg
        assert "--optimize" in command_arg


# Integration tests that actually run Docker i.e. skip if Docker not available
@pytest.mark.skipif(not docker_available(), reason="Docker not available")
class TestDockerIntegration:
    """Integration tests that run actual Docker containers."""

    def test_pull_mythril_image(self):
        """Test pulling mythril/myth:latest image."""
        success, error = pull_image("mythril/myth:latest", pull_policy="if-not-present")

        assert success is True
        assert error is None

    def test_pull_eth_security_toolbox_image(self):
        """Test pulling trailofbits/eth-security-toolbox:latest image."""
        success, error = pull_image(
            "trailofbits/eth-security-toolbox:latest",
            pull_policy="if-not-present",
        )

        assert success is True
        assert error is None

    def test_run_mythril_help(self, tmp_path):
        """Test running mythril with --help command."""
        project_root = tmp_path / "project"
        project_root.mkdir()

        result = run_docker(
            image="mythril/myth:latest",
            command=["myth", "--help"],
            project_root=project_root,
            timeout=30,
        )
        print(result)
        assert result["exit_code"] == 0
        assert result["container_exit_code"] == 0
        assert "usage" in result["stdout"].lower() or "myth" in result["stdout"].lower()

    def test_run_mythril_analyze_simple_contract(self, tmp_path):
        """Test running mythril analysis on a simple Solidity contract."""
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Create a simple Solidity contract
        contract_file = project_root / "SimpleContract.sol"
        contract_file.write_text(
            """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract SimpleContract {
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

        result = run_docker(
            image="mythril/myth:latest",
            command=[
                "myth",
                "analyze",
                "SimpleContract.sol",
                "--solv",
                "0.8.0",
            ],
            project_root=project_root,
            timeout=60,
            network_mode="bridge",  # Allow network access for downloads
        )
        assert result["exit_code"] == 0  # Execution succeeded
        assert result["container_exit_code"] == 0

    def test_run_slither_help(self, tmp_path):
        """Test running slither from eth-security-toolbox with --help."""
        project_root = tmp_path / "project"
        project_root.mkdir()

        result = run_docker(
            image="trailofbits/eth-security-toolbox:latest",
            command=["slither", "--help"],
            project_root=project_root,
            timeout=30,
        )

        assert result["exit_code"] == 0
        assert result["container_exit_code"] == 0
        assert (
            "usage" in result["stdout"].lower() or "slither" in result["stdout"].lower()
        )

    def test_run_slither_analyze_contract(self, tmp_path):
        """Test running slither analysis on a contract with vulnerability."""
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Create a contract with a known issue (reentrancy-like pattern)
        contract_file = project_root / "VulnerableContract.sol"
        contract_file.write_text(
            """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract VulnerableContract {
    mapping(address => uint256) public balances;

    function deposit() public payable {
        balances[msg.sender] += msg.value;
    }

    function withdraw(uint256 amount) public {
        require(balances[msg.sender] >= amount, "Insufficient balance");

        // Vulnerable: state updated after external call
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "Transfer failed");

        balances[msg.sender] -= amount;
    }

    function getBalance() public view returns (uint256) {
        return balances[msg.sender];
    }
}
"""
        )

        result = run_docker(
            image="trailofbits/eth-security-toolbox:latest",
            command=[
                "slither",
                "VulnerableContract.sol",
            ],
            project_root=project_root,
            timeout=60,
            network_mode="bridge",  # Allow network access for downloads
        )
        assert result["exit_code"] == 0
        assert result["container_exit_code"] != 0  # Should find issues

    def test_run_mythril_with_solc_version_argument(self, tmp_path):
        """Test mythril with specific Solidity compiler version."""
        project_root = tmp_path / "project"
        project_root.mkdir()

        contract_file = project_root / "VersionSpecific.sol"
        contract_file.write_text(
            """
// SPDX-License-Identifier: MIT
pragma solidity 0.8.19;

contract VersionSpecific {
    uint256 private data;

    function setData(uint256 _data) external {
        data = _data;
    }
}
"""
        )

        result = run_docker(
            image="mythril/myth:latest",
            command=[
                "myth",
                "analyze",
                "VersionSpecific.sol",
                "--solv",
                "0.8.19",
                "--execution-timeout",
                "30",
            ],
            project_root=project_root,
            timeout=60,
            network_mode="bridge",  # Allow network access for downloads
        )

        # Should execute (may or may not find issues)
        assert result["exit_code"] == 0
        assert result["container_exit_code"] == 0

    def test_run_slither_with_multiple_detectors(self, tmp_path):
        """Test slither with specific detector arguments."""
        project_root = tmp_path / "project"
        project_root.mkdir()

        contract_file = project_root / "DetectorTest.sol"
        contract_file.write_text(
            """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract DetectorTest {
    uint256 public value;

    function dangerousFunction(address target) public {
        // Unprotected call
        target.call("");
    }
}
"""
        )

        result = run_docker(
            image="trailofbits/eth-security-toolbox:latest",
            command=[
                "slither",
                "DetectorTest.sol",
                "--detect",
                "reentrancy-eth",
            ],
            project_root=project_root,
            timeout=60,
            network_mode="bridge",  # Allow network access for solc download
        )

        # Should execute - verify the command ran
        assert result is not None
        assert "exit_code" in result
        assert "container_exit_code" in result
        # Check that container executed (any exit code is acceptable here)
        assert result["exit_code"] == 0
        assert result["container_exit_code"] == 0

    def test_run_slither_on_multiple_contracts_with_dot(self, tmp_path):
        """Test running slither on all contracts in directory using '.' command."""
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Create multiple contract files
        contract1 = project_root / "Token.sol"
        contract1.write_text(
            """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Token {
    mapping(address => uint256) public balances;
    
    function transfer(address to, uint256 amount) public {
        balances[msg.sender] -= amount;
        balances[to] += amount;
    }
}
"""
        )

        contract2 = project_root / "Vault.sol"
        contract2.write_text(
            """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Vault {
    mapping(address => uint256) public deposits;
    
    function deposit() public payable {
        deposits[msg.sender] += msg.value;
    }
    
    function withdraw(uint256 amount) public {
        require(deposits[msg.sender] >= amount, "Insufficient balance");
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "Transfer failed");
        deposits[msg.sender] -= amount;
    }
}
"""
        )

        # Run slither on entire directory
        result = run_docker(
            image="trailofbits/eth-security-toolbox:latest",
            command=["slither", "."],
            project_root=project_root,
            timeout=90,
            network_mode="bridge",
        )

        assert result["exit_code"] == 0
        assert result["container_exit_code"] != 0  # Should find issues

    def test_run_slither_on_contracts_subdirectory(self, tmp_path):
        """Test running slither on contracts in a subdirectory."""
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Create contracts subdirectory
        contracts_dir = project_root / "contracts"
        contracts_dir.mkdir()

        # Create contract files in subdirectory
        contract1 = contracts_dir / "Storage.sol"
        contract1.write_text(
            """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Storage {
    uint256 private data;
    
    function setData(uint256 _data) external {
        data = _data;
    }
    
    function getData() external view returns (uint256) {
        return data;
    }
}
"""
        )

        contract2 = contracts_dir / "Calculator.sol"
        contract2.write_text(
            """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Calculator {
    function add(uint256 a, uint256 b) public pure returns (uint256) {
        return a + b;
    }
    
    function multiply(uint256 a, uint256 b) public pure returns (uint256) {
        return a * b;
    }
}
"""
        )

        # Run slither on contracts subdirectory
        result = run_docker(
            image="trailofbits/eth-security-toolbox:latest",
            command=["slither", "contracts"],
            project_root=project_root,
            timeout=90,
            network_mode="bridge",
        )

        assert result["exit_code"] == 0
        assert result["container_exit_code"] != 0  # Should find issues

    def test_run_slither_multiple_contracts_with_json_output(self, tmp_path):
        """Test running slither on multiple contracts with JSON output."""
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Create multiple contracts with different severity issues
        contract1 = project_root / "SafeContract.sol"
        contract1.write_text(
            """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract SafeContract {
    uint256 public counter;
    
    function increment() public {
        counter += 1;
    }
}
"""
        )

        contract2 = project_root / "UnsafeContract.sol"
        contract2.write_text(
            """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract UnsafeContract {
    function unsafeCall(address target) public {
        target.call("");
    }
}
"""
        )

        # Run slither with JSON output on all contracts
        result = run_docker(
            image="trailofbits/eth-security-toolbox:latest",
            command=["slither", ".", "--json", "-"],
            project_root=project_root,
            timeout=90,
            network_mode="bridge",
        )

        assert result["exit_code"] == 0
        assert result["container_exit_code"] != 0  # Should find issues

    def test_run_slither_exclude_specific_contracts(self, tmp_path):
        """Test running slither while excluding specific contracts."""
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Create multiple contracts
        contract1 = project_root / "Include.sol"
        contract1.write_text(
            """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Include {
    uint256 public value;
}
"""
        )

        contract2 = project_root / "Exclude.sol"
        contract2.write_text(
            """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Exclude {
    uint256 public value;
}
"""
        )

        # Run slither excluding Exclude.sol
        result = run_docker(
            image="trailofbits/eth-security-toolbox:latest",
            command=["slither", ".", "--filter-paths", "Exclude.sol"],
            project_root=project_root,
            timeout=90,
            network_mode="bridge",
        )
        assert result["exit_code"] == 0
        assert result["container_exit_code"] != 0
        assert (
            "Exclude.sol#" not in result["stdout"]
            or "Exclude.sol#" not in result["stderr"]
        )

    def test_run_slither_on_empty_directory(self, tmp_path):
        """Test running slither on directory with no contracts."""
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Run slither on empty directory
        result = run_docker(
            image="trailofbits/eth-security-toolbox:latest",
            command=["slither", "."],
            project_root=project_root,
            timeout=60,
            network_mode="bridge",
        )

        # Should handle empty directory gracefully
        assert result["exit_code"] == 0
        assert result["container_exit_code"] == 0
