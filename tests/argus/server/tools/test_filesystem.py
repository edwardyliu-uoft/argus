"""Tests for filesystem tools."""

from unittest.mock import patch
from pathlib import Path
import tempfile
import pytest

from argus.server.tools import filesystem


class TestFindFilesByExtension:
    """Tests for find_files_by_extension tool."""

    @pytest.mark.asyncio
    async def test_find_sol_files(self):
        """Test finding Solidity files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            (Path(tmpdir) / "Token.sol").touch()
            (Path(tmpdir) / "NFT.sol").touch()
            (Path(tmpdir) / "test.js").touch()
            (Path(tmpdir) / "sub").mkdir()
            (Path(tmpdir) / "sub" / "Lib.sol").touch()

            with patch("argus.server.tools.filesystem.conf") as mock_conf:
                mock_conf.get.return_value = tmpdir

                result = await filesystem.find_files_by_extension(
                    extension="sol", recursive=True
                )

                assert result["success"] is True
                assert result["count"] == 3
                assert len(result["files"]) == 3
                assert all("sol" in f for f in result["files"])

    @pytest.mark.asyncio
    async def test_find_with_dot_extension(self):
        """Test finding files with dot prefix in extension."""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "README.md").touch()

            with patch("argus.server.tools.filesystem.conf") as mock_conf:
                mock_conf.get.return_value = tmpdir

                result = await filesystem.find_files_by_extension(extension=".md")

                assert result["success"] is True
                assert result["count"] == 1

    @pytest.mark.asyncio
    async def test_find_non_recursive(self):
        """Test non-recursive file search."""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "root.txt").touch()
            (Path(tmpdir) / "sub").mkdir()
            (Path(tmpdir) / "sub" / "nested.txt").touch()

            with patch("argus.server.tools.filesystem.conf") as mock_conf:
                mock_conf.get.return_value = tmpdir

                result = await filesystem.find_files_by_extension(
                    extension="txt", recursive=False
                )

                assert result["success"] is True
                assert result["count"] == 1

    @pytest.mark.asyncio
    async def test_find_nonexistent_directory(self):
        """Test finding files in non-existent directory."""
        result = await filesystem.find_files_by_extension(
            extension="sol", directory="/nonexistent/path"
        )

        assert result["success"] is False
        assert "does not exist" in result["error"]


class TestReadFile:
    """Tests for read_file tool."""

    @pytest.mark.asyncio
    async def test_read_existing_file(self):
        """Test reading an existing file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("test content")
            filepath = f.name

        try:
            with patch("argus.server.tools.filesystem.conf") as mock_conf:
                mock_conf.get.return_value = Path(filepath).parent

                result = await filesystem.read_file(Path(filepath).name)

                assert result["success"] is True
                assert result["content"] == "test content"
                assert result["total_size"] == 12
        finally:
            Path(filepath).unlink()

    @pytest.mark.asyncio
    async def test_read_nonexistent_file(self):
        """Test reading a non-existent file."""
        result = await filesystem.read_file("/nonexistent/file.txt")

        assert result["success"] is False
        assert "does not exist" in result["error"]


class TestWriteFile:
    """Tests for write_file tool."""

    @pytest.mark.asyncio
    async def test_write_new_file(self):
        """Test writing a new file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("argus.server.tools.filesystem.conf") as mock_conf:
                mock_conf.get.return_value = tmpdir

                result = await filesystem.write_file(
                    file_path="test.txt", content="hello world"
                )

                assert result["success"] is True
                assert result["total_size"] == 11
                assert Path(result["path"]).exists()
                assert Path(result["path"]).read_text(encoding="utf-8") == "hello world"

    @pytest.mark.asyncio
    async def test_write_creates_directory(self):
        """Test that write_file creates parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("argus.server.tools.filesystem.conf") as mock_conf:
                mock_conf.get.return_value = tmpdir

                result = await filesystem.write_file(
                    file_path="sub/dir/test.txt", content="nested"
                )

                assert result["success"] is True
                assert Path(result["path"]).exists()


class TestAppendFile:
    """Tests for append_file tool."""

    @pytest.mark.asyncio
    async def test_append_to_existing_file(self):
        """Test appending to an existing file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("initial")

            with patch("argus.server.tools.filesystem.conf") as mock_conf:
                mock_conf.get.return_value = tmpdir

                result = await filesystem.append_file(
                    file_path="test.txt",
                    content=" appended",
                )

                assert result["success"] is True
                assert result["appended_size"] == 9
                assert test_file.read_text() == "initial appended"

    @pytest.mark.asyncio
    async def test_append_creates_file(self):
        """Test that append_file creates file if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("argus.server.tools.filesystem.conf") as mock_conf:
                mock_conf.get.return_value = tmpdir

                result = await filesystem.append_file(
                    file_path="new.txt", content="content"
                )

                assert result["success"] is True
                assert Path(result["path"]).exists()


class TestCreateDirectory:
    """Tests for create_directory tool."""

    @pytest.mark.asyncio
    async def test_create_new_directory(self):
        """Test creating a new directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("argus.server.tools.filesystem.conf") as mock_conf:
                mock_conf.get.return_value = tmpdir

                result = await filesystem.create_directory("newdir")

                assert result["success"] is True
                assert result["created"] is True
                assert Path(result["path"]).is_dir()

    @pytest.mark.asyncio
    async def test_create_nested_directory(self):
        """Test creating nested directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("argus.server.tools.filesystem.conf") as mock_conf:
                mock_conf.get.return_value = tmpdir

                result = await filesystem.create_directory("sub/nested/deep")

                assert result["success"] is True
                assert result["created"] is True
                assert Path(result["path"]).is_dir()

    @pytest.mark.asyncio
    async def test_create_existing_directory(self):
        """Test creating an already existing directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            existing = Path(tmpdir) / "existing"
            existing.mkdir()

            with patch("argus.server.tools.filesystem.conf") as mock_conf:
                mock_conf.get.return_value = tmpdir

                result = await filesystem.create_directory("existing")

                assert result["success"] is True
                assert result["created"] is False


class TestListDirectory:
    """Tests for list_directory tool."""

    @pytest.mark.asyncio
    async def test_list_directory_contents(self):
        """Test listing directory contents."""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "file1.txt").touch()
            (Path(tmpdir) / "file2.txt").touch()
            (Path(tmpdir) / "subdir").mkdir()

            with patch("argus.server.tools.filesystem.conf") as mock_conf:
                mock_conf.get.return_value = tmpdir

                result = await filesystem.list_directory()

                assert result["success"] is True
                assert result["count"] == 3
                assert len(result["items"]) == 3

    @pytest.mark.asyncio
    async def test_list_files_only(self):
        """Test listing only files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "file.txt").touch()
            (Path(tmpdir) / "dir").mkdir()

            with patch("argus.server.tools.filesystem.conf") as mock_conf:
                mock_conf.get.return_value = tmpdir

                result = await filesystem.list_directory(include_dirs=False)

                assert result["success"] is True
                assert result["count"] == 1
                assert result["items"][0]["type"] == "file"

    @pytest.mark.asyncio
    async def test_list_recursive(self):
        """Test recursive directory listing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "root.txt").touch()
            (Path(tmpdir) / "sub").mkdir()
            (Path(tmpdir) / "sub" / "nested.txt").touch()

            with patch("argus.server.tools.filesystem.conf") as mock_conf:
                mock_conf.get.return_value = tmpdir

                result = await filesystem.list_directory(recursive=True)

                assert result["success"] is True
                assert result["count"] >= 2


class TestReadFileInfo:
    """Tests for read_file_info tool."""

    @pytest.mark.asyncio
    async def test_get_file_info_existing(self):
        """Test getting info for existing file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("test")
            filepath = f.name

        try:
            with patch("argus.server.tools.filesystem.conf") as mock_conf:
                mock_conf.get.return_value = Path(filepath).parent

                result = await filesystem.read_file_info(Path(filepath).name)

                assert result["success"] is True
                assert result["exists"] is True
                assert result["type"] == "file"
                assert result["total_size"] > 0
        finally:
            Path(filepath).unlink()

    @pytest.mark.asyncio
    async def test_get_file_info_nonexistent(self):
        """Test getting info for non-existent file."""
        result = await filesystem.read_file_info("/nonexistent/file.txt")

        assert result["success"] is True
        assert result["exists"] is False
        assert result["type"] is None

    @pytest.mark.asyncio
    async def test_get_directory_info(self):
        """Test getting info for directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("argus.server.tools.filesystem.conf") as mock_conf:
                mock_conf.get.return_value = Path(tmpdir).parent

                result = await filesystem.read_file_info(Path(tmpdir).name)

                assert result["success"] is True
                assert result["exists"] is True
                assert result["type"] == "directory"
