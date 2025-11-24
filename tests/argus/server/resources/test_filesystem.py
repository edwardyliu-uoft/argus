"""Tests for filesystem resources."""

from unittest.mock import patch
from pathlib import Path
import tempfile
import pytest

from argus.server.resources import filesystem


class TestListWorkspaceFiles:
    """Tests for list_workspace_files resource."""

    @pytest.mark.asyncio
    async def test_get_workspace(self):
        """Test listing workspace files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            (Path(tmpdir) / "file1.txt").touch()
            (Path(tmpdir) / "file2.sol").touch()
            (Path(tmpdir) / "sub").mkdir()
            (Path(tmpdir) / "sub" / "file3.md").touch()

            with patch("argus.server.resources.filesystem.conf") as mock_conf:
                mock_conf.get.return_value = tmpdir
                result = await filesystem.get_workspace()

                assert "Workspace:" in result
                assert tmpdir in result
                assert "file1.txt" in result
                assert "file2.sol" in result
                assert "file3.md" in result
                assert "Total: 3 files" in result

    @pytest.mark.asyncio
    async def test_get_empty_workspace(self):
        """Test listing an empty workspace."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("argus.server.resources.filesystem.conf") as mock_conf:
                mock_conf.get.return_value = tmpdir
                result = await filesystem.get_workspace()

                assert "Workspace:" in result
                assert "Total: 0 files" in result

    @pytest.mark.asyncio
    async def test_get_nonexistent_workspace(self):
        """Test listing a non-existent workspace."""
        with patch("argus.server.resources.filesystem.conf") as mock_conf:
            mock_conf.get.return_value = "/nonexistent/path"
            result = await filesystem.get_workspace()

            assert "Error:" in result
            assert "does not exist" in result


class TestGetProjectStructure:
    """Tests for get_project_structure resource."""

    @pytest.mark.asyncio
    async def test_get_project_structure(self):
        """Test getting project structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test structure
            (Path(tmpdir) / "contracts").mkdir()
            (Path(tmpdir) / "contracts" / "Token.sol").touch()
            (Path(tmpdir) / "test").mkdir()
            (Path(tmpdir) / "test" / "Token.test.js").touch()
            (Path(tmpdir) / "package.json").touch()
            (Path(tmpdir) / "README.md").touch()

            with patch("argus.server.resources.filesystem.conf") as mock_conf:
                mock_conf.get.return_value = tmpdir
                result = await filesystem.get_project_structure()

                assert "Project Structure:" in result
                assert "contracts/" in result
                assert "test/" in result
                assert "File types:" in result
                assert ".sol:" in result
                assert ".js:" in result
                assert "Configuration:" in result
                assert "package.json" in result

    @pytest.mark.asyncio
    async def test_project_structure_excludes_node_modules(self):
        """Test that project structure excludes node_modules."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create structure with excluded dirs
            (Path(tmpdir) / "node_modules").mkdir()
            (Path(tmpdir) / "node_modules" / "package").mkdir()
            (Path(tmpdir) / "node_modules" / "package" / "index.js").touch()
            (Path(tmpdir) / "src").mkdir()
            (Path(tmpdir) / "src" / "app.js").touch()

            with patch("argus.server.resources.filesystem.conf") as mock_conf:
                mock_conf.get.return_value = tmpdir
                result = await filesystem.get_project_structure()

                assert "src/" in result
                assert "node_modules" not in result


class TestGetSolidityContracts:
    """Tests for get_solidity_contracts resource."""

    @pytest.mark.asyncio
    async def test_get_solidity_files(self):
        """Test getting Solidity contracts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test contracts
            (Path(tmpdir) / "contracts").mkdir()
            (Path(tmpdir) / "contracts" / "Token.sol").touch()
            (Path(tmpdir) / "contracts" / "NFT.sol").touch()
            (Path(tmpdir) / "contracts" / "lib").mkdir()
            (Path(tmpdir) / "contracts" / "lib" / "SafeMath.sol").touch()

            with patch("argus.server.resources.filesystem.conf") as mock_conf:
                mock_conf.get.return_value = tmpdir
                result = await filesystem.get_solidity_files()

                assert "Solidity Contracts:" in result
                assert "Token.sol" in result
                assert "NFT.sol" in result
                assert "SafeMath.sol" in result
                assert "Total: 3 contracts" in result

    @pytest.mark.asyncio
    async def test_get_solidity_files_empty_workspace(self):
        """Test getting contracts when none exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("argus.server.resources.filesystem.conf") as mock_conf:
                mock_conf.get.return_value = tmpdir
                result = await filesystem.get_solidity_files()

                assert "No Solidity contracts found" in result

    @pytest.mark.asyncio
    async def test_get_solidity_files_groups_by_directory(self):
        """Test that contracts are grouped by directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create contracts in different directories
            (Path(tmpdir) / "Token.sol").touch()
            (Path(tmpdir) / "tokens").mkdir()
            (Path(tmpdir) / "tokens" / "ERC20.sol").touch()
            (Path(tmpdir) / "governance").mkdir()
            (Path(tmpdir) / "governance" / "Governor.sol").touch()

            with patch("argus.server.resources.filesystem.conf") as mock_conf:
                mock_conf.get.return_value = tmpdir
                result = await filesystem.get_solidity_files()

                assert "(root):" in result
                assert "tokens/:" in result
                assert "governance/:" in result
