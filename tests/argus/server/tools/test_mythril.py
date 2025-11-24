"""Tests for Mythril tool controller."""

from unittest.mock import patch
import pytest

from argus.core import docker as argus_docker
from argus.server import tools


@pytest.mark.skipif(not argus_docker.docker_available(), reason="Docker not available")
class TestMythrilIntegration:
    """Integration tests that run actual Mythril container."""

    @pytest.mark.asyncio
    @patch("argus.server.tools.mythril.conf")
    async def test_mythril_help_command(self, mock_conf, tmp_path):
        """Test running mythril with --help command."""
        project_root = tmp_path / "project"
        project_root.mkdir()
        mock_conf.get.side_effect = lambda key, default=None: {
            "workdir": str(project_root),
            "server.tools.mythril": {
                "timeout": 60,
                "docker": {
                    "image": "mythril/myth:latest",
                    "network_mode": "none",
                    "remove_containers": True,
                },
            },
        }.get(key, default)

        result = await tools.mythril.mythril(command="myth", args=["--help"])

        assert result["exit_code"] == 0
        assert result["container_exit_code"] == 0

    @pytest.mark.asyncio
    @patch("argus.server.tools.mythril.conf")
    async def test_mythril_version_command(self, mock_conf, tmp_path):
        """Test running mythril with --version command."""
        project_root = tmp_path / "project"
        project_root.mkdir()
        mock_conf.get.side_effect = lambda key, default=None: {
            "workdir": str(project_root),
            "server.tools.mythril": {
                "timeout": 60,
                "docker": {
                    "image": "mythril/myth:latest",
                    "network_mode": "none",
                    "remove_containers": True,
                },
            },
        }.get(key, default)

        result = await tools.mythril.mythril(command="myth", args=["version"])

        assert result["exit_code"] == 0
        assert result["container_exit_code"] == 0

    @pytest.mark.asyncio
    @patch("argus.server.tools.mythril.conf")
    async def test_mythril_analyze_simple_contract(self, mock_conf, tmp_path):
        """Test running mythril analysis on a simple Solidity contract."""
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Create a simple Solidity contract
        contract_file = project_root / "SimpleStorage.sol"
        contract_file.write_text(
            """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract SimpleStorage {
    uint256 private storedValue;

    function setValue(uint256 _value) public {
        storedValue = _value;
    }

    function getValue() public view returns (uint256) {
        return storedValue;
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

        result = await tools.mythril.mythril(
            command="myth",
            args=[
                "analyze",
                "SimpleStorage.sol",
                "--solv",
                "0.8.0",
            ],
        )

        assert result["exit_code"] == 0
        assert result["container_exit_code"] == 0

    @pytest.mark.asyncio
    @patch("argus.server.tools.mythril.conf")
    async def test_mythril_analyze_contract_with_vulnerability(
        self,
        mock_conf,
        tmp_path,
    ):
        """Test running mythril on a contract with a known vulnerability."""
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Create a contract with potential reentrancy issue
        contract_file = project_root / "Vulnerable.sol"
        contract_file.write_text(
            """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Vulnerable {
    mapping(address => uint256) public balances;

    function deposit() public payable {
        balances[msg.sender] += msg.value;
    }

    function withdraw(uint256 amount) public {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        
        // Vulnerable: external call before state update
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "Transfer failed");
        
        balances[msg.sender] -= amount;
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

        result = await tools.mythril.mythril(
            command="myth",
            args=[
                "analyze",
                "Vulnerable.sol",
                "--solv",
                "0.8.0",
            ],
        )

        assert result["exit_code"] == 0
        assert result["container_exit_code"] != 0

    @pytest.mark.asyncio
    @patch("argus.server.tools.mythril.conf")
    async def test_mythril_analyze_with_json_output(self, mock_conf, tmp_path):
        """Test running mythril with JSON output format."""
        project_root = tmp_path / "project"
        project_root.mkdir()

        contract_file = project_root / "Token.sol"
        contract_file.write_text(
            """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Token {
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
            "server.tools.mythril": {
                "timeout": 120,
                "docker": {
                    "image": "mythril/myth:latest",
                    "network_mode": "bridge",
                    "remove_containers": True,
                },
            },
        }.get(key, default)

        result = await tools.mythril.mythril(
            command="myth",
            args=[
                "analyze",
                "Token.sol",
                "--solv",
                "0.8.0",
                "-o",
                "json",
            ],
        )

        assert result["exit_code"] == 0
        assert result["container_exit_code"] == 0

    @pytest.mark.asyncio
    @patch("argus.server.tools.mythril.conf")
    async def test_mythril_analyze_with_execution_timeout(self, mock_conf, tmp_path):
        """Test running mythril with execution timeout argument."""
        project_root = tmp_path / "project"
        project_root.mkdir()

        contract_file = project_root / "Simple.sol"
        contract_file.write_text(
            """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Simple {
    uint256 public value;
    
    function set(uint256 _value) public {
        value = _value;
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

        result = await tools.mythril.mythril(
            command="myth",
            args=[
                "analyze",
                "Simple.sol",
                "--solv",
                "0.8.0",
                "--execution-timeout",
                "30",
            ],
        )

        assert result["exit_code"] == 0
        assert result["container_exit_code"] == 0

    @pytest.mark.asyncio
    @patch("argus.server.tools.mythril.conf")
    async def test_mythril_with_invalid_contract(self, mock_conf, tmp_path):
        """Test running mythril on invalid Solidity code."""
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Create invalid contract
        contract_file = project_root / "Invalid.sol"
        contract_file.write_text(
            """
pragma solidity ^0.8.0;

contract Invalid {
    this is not valid solidity code
    function broken() {
        // missing return type and body
    }
}
"""
        )
        mock_conf.get.side_effect = lambda key, default=None: {
            "workdir": str(project_root),
            "server.tools.mythril": {
                "timeout": 60,
                "docker": {
                    "image": "mythril/myth:latest",
                    "network_mode": "bridge",
                    "remove_containers": True,
                },
            },
        }.get(key, default)

        result = await tools.mythril.mythril(
            command="myth",
            args=[
                "analyze",
                "Invalid.sol",
                "--solv",
                "0.8.0",
            ],
        )

        assert result["exit_code"] == 0
        assert result["container_exit_code"] == 0
        assert "ParserError" in result["stdout"]["error"]

    @pytest.mark.asyncio
    @patch("argus.server.tools.mythril.conf")
    async def test_mythril_with_nonexistent_file(self, mock_conf, tmp_path):
        """Test running mythril on a file that doesn't exist."""
        project_root = tmp_path / "project"
        project_root.mkdir()

        mock_conf.get.side_effect = lambda key, default=None: {
            "workdir": str(project_root),
            "server.tools.mythril": {
                "timeout": 60,
                "docker": {
                    "image": "mythril/myth:latest",
                    "network_mode": "none",
                    "remove_containers": True,
                },
            },
        }.get(key, default)

        result = await tools.mythril.mythril(
            command="myth",
            args=[
                "analyze",
                "NonExistent.sol",
            ],
        )

        assert result["exit_code"] == 0
        assert result["container_exit_code"] == 0
        assert "FileNotFoundError" in result["stdout"]["error"]

    @pytest.mark.asyncio
    @patch("argus.server.tools.mythril.conf")
    async def test_mythril_with_multiple_contracts_in_project(
        self,
        mock_conf,
        tmp_path,
    ):
        """Test running mythril in a project with multiple contract files."""
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Create multiple contracts
        contract1 = project_root / "ContractA.sol"
        contract1.write_text(
            """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract ContractA {
    uint256 public valueA;
    
    function setA(uint256 _value) public {
        valueA = _value;
    }
}
"""
        )

        contract2 = project_root / "ContractB.sol"
        contract2.write_text(
            """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract ContractB {
    uint256 public valueB;
    
    function setB(uint256 _value) public {
        valueB = _value;
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

        result = await tools.mythril.mythril(
            command="myth",
            args=[
                "analyze",
                "ContractA.sol",
                "--solv",
                "0.8.0",
            ],
        )

        assert result["exit_code"] == 0
        assert result["container_exit_code"] == 0

    @pytest.mark.asyncio
    @patch("argus.server.tools.mythril.conf")
    async def test_mythril_with_subdirectory_contract(self, mock_conf, tmp_path):
        """Test running mythril on a contract in a subdirectory."""
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Create contracts subdirectory
        contracts_dir = project_root / "contracts"
        contracts_dir.mkdir()

        contract_file = contracts_dir / "Storage.sol"
        contract_file.write_text(
            """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Storage {
    uint256 private data;
    
    function set(uint256 _data) public {
        data = _data;
    }
    
    function get() public view returns (uint256) {
        return data;
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

        result = await tools.mythril.mythril(
            command="myth",
            args=[
                "analyze",
                "contracts/Storage.sol",
                "--solv",
                "0.8.0",
            ],
        )

        assert result["exit_code"] == 0
        assert result["container_exit_code"] == 0
