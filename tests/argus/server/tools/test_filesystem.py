"""Tests for filesystem tools."""

from pathlib import Path
import tempfile
import pytest

from argus.server.tools import FilesystemToolPlugin


class TestFindFilesByExtension:
    """Tests for find_files_by_extension tool."""

    @pytest.fixture(scope="class")
    def filesystem(self):
        """Filesystem tool plugin instance."""
        return FilesystemToolPlugin()

    @pytest.mark.asyncio
    async def test_find_sol_files(self, filesystem):
        """Test finding Solidity files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            (Path(tmpdir) / "Token.sol").touch()
            (Path(tmpdir) / "NFT.sol").touch()
            (Path(tmpdir) / "test.js").touch()
            (Path(tmpdir) / "sub").mkdir()
            (Path(tmpdir) / "sub" / "Lib.sol").touch()

            filesystem.initialize({"workdir": tmpdir})
            res = await filesystem.find_files_by_extension(
                extension="sol",
                recursive=True,
            )
            assert res["success"] is True
            assert res["count"] == 3
            assert len(res["files"]) == 3
            assert all("sol" in f for f in res["files"])

    @pytest.mark.asyncio
    async def test_find_with_dot_extension(self, filesystem):
        """Test finding files with dot prefix in extension."""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "README.md").touch()

            filesystem.initialize({"workdir": tmpdir})
            res = await filesystem.find_files_by_extension(extension=".md")
            assert res["success"] is True
            assert res["count"] == 1

    @pytest.mark.asyncio
    async def test_find_non_recursive(self, filesystem):
        """Test non-recursive file search."""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "root.txt").touch()
            (Path(tmpdir) / "sub").mkdir()
            (Path(tmpdir) / "sub" / "nested.txt").touch()

            filesystem.initialize({"workdir": tmpdir})
            res = await filesystem.find_files_by_extension(
                extension="txt",
                recursive=False,
            )
            assert res["success"] is True
            assert res["count"] == 1

    @pytest.mark.asyncio
    async def test_find_nonexistent_directory(self, filesystem):
        """Test finding files in non-existent directory."""
        filesystem.initialize()
        res = await filesystem.find_files_by_extension(
            extension="sol", directory="/nonexistent/path"
        )
        assert res["success"] is False
        assert "does not exist" in res["error"]


class TestReadFile:
    """Tests for read_file tool."""

    @pytest.fixture(scope="class")
    def filesystem(self):
        """Filesystem tool plugin instance."""
        return FilesystemToolPlugin()

    @pytest.mark.asyncio
    async def test_read_existing_file(self, filesystem):
        """Test reading an existing file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("test content")
            filepath = f.name

        try:
            filesystem.initialize({"workdir": str(Path(filepath).parent)})
            res = await filesystem.read_file(Path(filepath).name)

            assert res["success"] is True
            assert res["content"] == "test content"
            assert res["total_size"] == 12
        finally:
            Path(filepath).unlink()

    @pytest.mark.asyncio
    async def test_read_nonexistent_file(self, filesystem):
        """Test reading a non-existent file."""
        filesystem.initialize()
        res = await filesystem.read_file("/nonexistent/file.txt")

        assert res["success"] is False
        assert "does not exist" in res["error"]


class TestWriteFile:
    """Tests for write_file tool."""

    @pytest.fixture(scope="class")
    def filesystem(self):
        """Filesystem tool plugin instance."""
        return FilesystemToolPlugin()

    @pytest.mark.asyncio
    async def test_write_new_file(self, filesystem):
        """Test writing a new file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filesystem.initialize({"workdir": tmpdir})
            res = await filesystem.write_file(
                file_path="test.txt", content="hello world"
            )

            assert res["success"] is True
            assert res["total_size"] == 11
            assert Path(res["path"]).exists()
            assert Path(res["path"]).read_text(encoding="utf-8") == "hello world"

    @pytest.mark.asyncio
    async def test_write_creates_directory(self, filesystem):
        """Test that write_file creates parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filesystem.initialize({"workdir": tmpdir})
            res = await filesystem.write_file(
                file_path="sub/dir/test.txt", content="nested"
            )

            assert res["success"] is True
            assert Path(res["path"]).exists()


class TestAppendFile:
    """Tests for append_file tool."""

    @pytest.fixture(scope="class")
    def filesystem(self):
        """Filesystem tool plugin instance."""
        return FilesystemToolPlugin()

    @pytest.mark.asyncio
    async def test_append_to_existing_file(self, filesystem):
        """Test appending to an existing file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("initial")

            filesystem.initialize({"workdir": tmpdir})
            res = await filesystem.append_file(
                file_path="test.txt",
                content=" appended",
            )

            assert res["success"] is True
            assert res["appended_size"] == 9
            assert test_file.read_text() == "initial appended"

    @pytest.mark.asyncio
    async def test_append_creates_file(self, filesystem):
        """Test that append_file creates file if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filesystem.initialize({"workdir": tmpdir})
            res = await filesystem.append_file(file_path="new.txt", content="content")

            assert res["success"] is True
            assert Path(res["path"]).exists()


class TestCreateDirectory:
    """Tests for create_directory tool."""

    @pytest.fixture(scope="class")
    def filesystem(self):
        """Filesystem tool plugin instance."""
        return FilesystemToolPlugin()

    @pytest.mark.asyncio
    async def test_create_new_directory(self, filesystem):
        """Test creating a new directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filesystem.initialize({"workdir": tmpdir})
            res = await filesystem.create_directory("newdir")

            assert res["success"] is True
            assert res["created"] is True
            assert Path(res["path"]).is_dir()

    @pytest.mark.asyncio
    async def test_create_nested_directory(self, filesystem):
        """Test creating nested directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filesystem.initialize({"workdir": tmpdir})
            res = await filesystem.create_directory("sub/nested/deep")

            assert res["success"] is True
            assert res["created"] is True
            assert Path(res["path"]).is_dir()

    @pytest.mark.asyncio
    async def test_create_existing_directory(self, filesystem):
        """Test creating an already existing directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            existing = Path(tmpdir) / "existing"
            existing.mkdir()

            filesystem.initialize({"workdir": tmpdir})
            res = await filesystem.create_directory("existing")

            assert res["success"] is True
            assert res["created"] is False


class TestListDirectory:
    """Tests for list_directory tool."""

    @pytest.fixture(scope="class")
    def filesystem(self):
        """Filesystem tool plugin instance."""
        return FilesystemToolPlugin()

    @pytest.mark.asyncio
    async def test_list_directory_contents(self, filesystem):
        """Test listing directory contents."""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "file1.txt").touch()
            (Path(tmpdir) / "file2.txt").touch()
            (Path(tmpdir) / "subdir").mkdir()

            filesystem.initialize({"workdir": tmpdir})
            res = await filesystem.list_directory()

            assert res["success"] is True
            assert res["count"] == 3
            assert len(res["items"]) == 3

    @pytest.mark.asyncio
    async def test_list_files_only(self, filesystem):
        """Test listing only files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "file.txt").touch()
            (Path(tmpdir) / "dir").mkdir()

            filesystem.initialize({"workdir": tmpdir})
            res = await filesystem.list_directory(include_dirs=False)

            assert res["success"] is True
            assert res["count"] == 1
            assert res["items"][0]["type"] == "file"

    @pytest.mark.asyncio
    async def test_list_recursive(self, filesystem):
        """Test recursive directory listing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "root.txt").touch()
            (Path(tmpdir) / "sub").mkdir()
            (Path(tmpdir) / "sub" / "nested.txt").touch()

            filesystem.initialize({"workdir": tmpdir})
            res = await filesystem.list_directory(recursive=True)

            assert res["success"] is True
            assert res["count"] >= 2


class TestReadFileInfo:
    """Tests for read_file_info tool."""

    @pytest.fixture(scope="class")
    def filesystem(self):
        """Filesystem tool plugin instance."""
        return FilesystemToolPlugin()

    @pytest.mark.asyncio
    async def test_get_file_info_existing(self, filesystem):
        """Test getting info for existing file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("test")
            filepath = f.name

        try:
            filesystem.initialize({"workdir": str(Path(filepath).parent)})
            res = await filesystem.read_file_info(Path(filepath).name)

            assert res["success"] is True
            assert res["exists"] is True
            assert res["type"] == "file"
            assert res["total_size"] > 0
        finally:
            Path(filepath).unlink()

    @pytest.mark.asyncio
    async def test_get_file_info_nonexistent(self, filesystem):
        """Test getting info for non-existent file."""
        filesystem.initialize()
        res = await filesystem.read_file_info("/nonexistent/file.txt")

        assert res["success"] is True
        assert res["exists"] is False
        assert res["type"] is None

    @pytest.mark.asyncio
    async def test_get_directory_info(self, filesystem):
        """Test getting info for directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filesystem.initialize({"workdir": str(Path(tmpdir).parent)})
            res = await filesystem.read_file_info(Path(tmpdir).name)

            assert res["success"] is True
            assert res["exists"] is True
            assert res["type"] == "directory"
