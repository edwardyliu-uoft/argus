"""Tests for filesystem resources."""

from pathlib import Path
import tempfile
import pytest

from argus.server.resources import FilesystemResourcePlugin


class TestListWorkspaceFiles:
    """Tests for list_workspace_files resource."""

    @pytest.fixture(scope="class")
    def filesystem(self):
        """Fixture for FilesystemResourcePlugin instance."""
        return FilesystemResourcePlugin()

    @pytest.mark.asyncio
    async def test_get_workspace(self, filesystem):
        """Test listing workspace files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            (Path(tmpdir) / "file1.txt").touch()
            (Path(tmpdir) / "file2.sol").touch()
            (Path(tmpdir) / "sub").mkdir()
            (Path(tmpdir) / "sub" / "file3.md").touch()

            filesystem.initialize({"workdir": tmpdir})
            res = await filesystem.get_workspace()
            assert "Workspace:" in res
            assert tmpdir in res
            assert "file1.txt" in res
            assert "file2.sol" in res
            assert "file3.md" in res
            assert "Total: 3 files" in res

    @pytest.mark.asyncio
    async def test_get_empty_workspace(self, filesystem):
        """Test listing an empty workspace."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filesystem.initialize({"workdir": tmpdir})
            res = await filesystem.get_workspace()
            assert "Workspace:" in res
            assert "Total: 0 files" in res

    @pytest.mark.asyncio
    async def test_get_nonexistent_workspace(self, filesystem):
        """Test listing a non-existent workspace."""
        filesystem.initialize({"workdir": "/nonexistent/path"})
        res = await filesystem.get_workspace()
        assert "Error:" in res
        assert "does not exist" in res


class TestGetProjectStructure:
    """Tests for get_project_structure resource."""

    @pytest.fixture(scope="class")
    def filesystem(self):
        """Fixture for FilesystemResourcePlugin instance."""
        return FilesystemResourcePlugin()

    @pytest.mark.asyncio
    async def test_get_project_structure(self, filesystem):
        """Test getting project structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test structure
            (Path(tmpdir) / "contracts").mkdir()
            (Path(tmpdir) / "contracts" / "Token.sol").touch()
            (Path(tmpdir) / "test").mkdir()
            (Path(tmpdir) / "test" / "Token.test.js").touch()
            (Path(tmpdir) / "package.json").touch()
            (Path(tmpdir) / "README.md").touch()

            filesystem.initialize({"workdir": tmpdir})
            res = await filesystem.get_project_structure()
            assert "Project Structure:" in res
            assert "contracts/" in res
            assert "test/" in res
            assert "File types:" in res
            assert ".sol:" in res
            assert ".js:" in res
            assert "Configuration:" in res
            assert "package.json" in res

    @pytest.mark.asyncio
    async def test_project_structure_excludes_node_modules(self, filesystem):
        """Test that project structure excludes node_modules."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create structure with excluded dirs
            (Path(tmpdir) / "node_modules").mkdir()
            (Path(tmpdir) / "node_modules" / "package").mkdir()
            (Path(tmpdir) / "node_modules" / "package" / "index.js").touch()
            (Path(tmpdir) / "src").mkdir()
            (Path(tmpdir) / "src" / "app.js").touch()

            filesystem.initialize({"workdir": tmpdir})
            res = await filesystem.get_project_structure()
            assert "src/" in res
            assert "node_modules" not in res


class TestGetSolidityContracts:
    """Tests for get_solidity_contracts resource."""

    @pytest.fixture(scope="class")
    def filesystem(self):
        """Fixture for FilesystemResourcePlugin instance."""
        return FilesystemResourcePlugin()

    @pytest.mark.asyncio
    async def test_get_solidity_files(self, filesystem):
        """Test getting Solidity contracts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test contracts
            (Path(tmpdir) / "contracts").mkdir()
            (Path(tmpdir) / "contracts" / "Token.sol").touch()
            (Path(tmpdir) / "contracts" / "NFT.sol").touch()
            (Path(tmpdir) / "contracts" / "lib").mkdir()
            (Path(tmpdir) / "contracts" / "lib" / "SafeMath.sol").touch()

            filesystem.initialize({"workdir": tmpdir})
            res = await filesystem.get_solidity_files()
            assert "Solidity Contracts:" in res
            assert "Token.sol" in res
            assert "NFT.sol" in res
            assert "SafeMath.sol" in res
            assert "Total: 3 contracts" in res

    @pytest.mark.asyncio
    async def test_get_solidity_files_empty_workspace(self, filesystem):
        """Test getting contracts when none exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filesystem.initialize({"workdir": tmpdir})
            res = await filesystem.get_solidity_files()
            assert "No Solidity contracts found" in res

    @pytest.mark.asyncio
    async def test_get_solidity_files_groups_by_directory(self, filesystem):
        """Test that contracts are grouped by directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create contracts in different directories
            (Path(tmpdir) / "Token.sol").touch()
            (Path(tmpdir) / "tokens").mkdir()
            (Path(tmpdir) / "tokens" / "ERC20.sol").touch()
            (Path(tmpdir) / "governance").mkdir()
            (Path(tmpdir) / "governance" / "Governor.sol").touch()

            filesystem.initialize({"workdir": tmpdir})
            res = await filesystem.get_solidity_files()
            assert "(root):" in res
            assert "tokens/:" in res
            assert "governance/:" in res
