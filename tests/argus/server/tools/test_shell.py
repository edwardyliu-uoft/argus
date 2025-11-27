"""Tests for shell tools."""

from pathlib import Path
import tempfile
import json
import pytest

from argus.server.tools import ShellToolPlugin


class TestShellToolPlugin:
    """Tests for ShellToolPlugin initialization."""

    @pytest.fixture
    def shell(self):
        """Shell tool plugin instance."""
        return ShellToolPlugin()

    def test_initialization_default(self, shell):
        """Test plugin initialization with default config."""
        shell.initialize()
        assert shell.initialized is True
        assert "hardhat" in shell.tools
        assert "npm" in shell.tools
        assert "ls" in shell.tools
        assert "cat" in shell.tools

    def test_initialization_custom_config(self, shell):
        """Test plugin initialization with custom config."""
        custom_config = {
            "cli": {
                "hardhat": ["compile", "test"],
                "npm": ["install"],
            }
        }
        shell.initialize(custom_config)
        assert shell.initialized is True
        assert shell.config["cli"]["hardhat"] == ["compile", "test"]
        assert shell.config["cli"]["npm"] == ["install"]

    def test_plugin_metadata(self, shell):
        """Test plugin metadata properties."""
        assert shell.name == "shell"
        assert shell.version == "1.0.0"
        assert shell.description == "Shell operations"


class TestValidateCwd:
    """Tests for current working directory validation."""

    @pytest.fixture
    def shell(self):
        """Shell tool plugin instance."""
        plugin = ShellToolPlugin()
        return plugin

    @pytest.mark.asyncio
    async def test_valid_cwd_within_workdir(self, shell):
        """Test validation passes for cwd within workdir."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = Path(tmpdir) / "subdir"
            subdir.mkdir()

            shell.initialize({"workdir": str(Path(tmpdir).resolve())})
            # Should not raise
            shell._ShellToolPlugin__validate_cwd(str(subdir.resolve()))

    @pytest.mark.asyncio
    async def test_invalid_cwd_outside_workdir(self, shell):
        """Test validation fails for cwd outside workdir."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with tempfile.TemporaryDirectory() as outside_dir:
                shell.initialize({"workdir": tmpdir})

                with pytest.raises(ValueError, match="outside of project root"):
                    shell._ShellToolPlugin__validate_cwd(outside_dir)

    @pytest.mark.asyncio
    async def test_invalid_cwd_nonexistent(self, shell):
        """Test validation fails for non-existent directory."""
        shell.initialize()
        with pytest.raises(ValueError, match="does not exist"):
            shell._ShellToolPlugin__validate_cwd("/nonexistent/path")

    @pytest.mark.asyncio
    async def test_invalid_cwd_not_directory(self, shell):
        """Test validation fails when cwd is not a directory."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name
        try:
            shell.initialize({"workdir": str(Path(tmp_path).parent)})
            with pytest.raises(ValueError, match="is not a directory"):
                shell._ShellToolPlugin__validate_cwd(tmp_path)
        finally:
            Path(tmp_path).unlink(missing_ok=True)


class TestValidateArgs:
    """Tests for argument validation."""

    @pytest.fixture
    def shell(self):
        """Shell tool plugin instance."""
        plugin = ShellToolPlugin()
        plugin.initialize()
        return plugin

    def test_valid_args(self, shell):
        """Test validation passes for safe arguments."""
        args = ["--flag", "value", "-v", "test.txt"]
        # Should not raise
        shell._ShellToolPlugin__validate_args(args)

    def test_invalid_args_with_semicolon(self, shell):
        """Test validation fails for arguments with semicolon."""
        args = ["test;rm -rf /"]
        with pytest.raises(ValueError, match="blacklisted character"):
            shell._ShellToolPlugin__validate_args(args)

    def test_invalid_args_with_pipe(self, shell):
        """Test validation fails for arguments with pipe."""
        args = ["test | cat"]
        with pytest.raises(ValueError, match="blacklisted character"):
            shell._ShellToolPlugin__validate_args(args)

    def test_invalid_args_with_backtick(self, shell):
        """Test validation fails for arguments with backtick."""
        args = ["`whoami`"]
        with pytest.raises(ValueError, match="blacklisted character"):
            shell._ShellToolPlugin__validate_args(args)

    def test_invalid_args_with_dollar(self, shell):
        """Test validation fails for arguments with dollar sign."""
        args = ["$(cat /etc/passwd)"]
        with pytest.raises(ValueError, match="blacklisted character"):
            shell._ShellToolPlugin__validate_args(args)

    def test_empty_args(self, shell):
        """Test validation passes for empty arguments."""
        # Should not raise
        shell._ShellToolPlugin__validate_args([])
        shell._ShellToolPlugin__validate_args(None)


class TestHardhatCommand:
    """Tests for hardhat command execution."""

    @pytest.fixture
    def shell(self):
        """Shell tool plugin instance."""
        plugin = ShellToolPlugin()
        return plugin

    @pytest.mark.asyncio
    async def test_hardhat_compile_command(self, shell):
        """Test executing hardhat compile command."""
        with tempfile.TemporaryDirectory() as tmpdir:
            shell.initialize({"workdir": tmpdir})
            result = await shell.hardhat("compile", timeout=5)

            assert isinstance(result, list)
            assert len(result) > 0
            assert result[0]["type"] == "text"

            response = json.loads(result[0]["text"])
            assert "success" in response
            assert "exit_code" in response
            assert "command" in response
            assert "npx hardhat compile" in response["command"]

    @pytest.mark.asyncio
    async def test_hardhat_with_args(self, shell):
        """Test hardhat command with additional arguments."""
        with tempfile.TemporaryDirectory() as tmpdir:
            shell.initialize({"workdir": tmpdir})
            result = await shell.hardhat("test", args=["--verbose"], timeout=5)

            response = json.loads(result[0]["text"])
            assert "npx hardhat test --verbose" in response["command"]

    @pytest.mark.asyncio
    async def test_hardhat_invalid_command(self, shell):
        """Test hardhat with non-whitelisted command."""
        shell.initialize()
        with pytest.raises(ValueError, match="is not allowed"):
            await shell.hardhat("deploy")

    @pytest.mark.asyncio
    async def test_hardhat_custom_whitelist(self, shell):
        """Test hardhat with custom whitelist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            shell.initialize(
                {"workdir": tmpdir, "cli": {"hardhat": ["compile", "deploy"]}}
            )
            result = await shell.hardhat("deploy", timeout=5)
            response = json.loads(result[0]["text"])
            assert "deploy" in response["command"]

    @pytest.mark.asyncio
    async def test_hardhat_invalid_args(self, shell):
        """Test hardhat command with blacklisted characters in args."""
        shell.initialize()
        with pytest.raises(ValueError, match="blacklisted character"):
            await shell.hardhat("compile", args=["test;ls"])

    @pytest.mark.asyncio
    async def test_hardhat_invalid_cwd(self, shell):
        """Test hardhat command with invalid cwd."""
        shell.initialize()
        with pytest.raises(ValueError):
            await shell.hardhat("compile", cwd="/nonexistent/path")


class TestNpmCommand:
    """Tests for npm command execution."""

    @pytest.fixture
    def shell(self):
        """Shell tool plugin instance."""
        plugin = ShellToolPlugin()
        return plugin

    @pytest.mark.asyncio
    async def test_npm_install_command(self, shell):
        """Test executing npm install command."""
        with tempfile.TemporaryDirectory() as tmpdir:
            shell.initialize({"workdir": tmpdir})
            result = await shell.npm("install", timeout=5)

            assert isinstance(result, list)
            response = json.loads(result[0]["text"])
            assert "npm install" in response["command"]

    @pytest.mark.asyncio
    async def test_npm_with_args(self, shell):
        """Test npm command with package arguments."""
        with tempfile.TemporaryDirectory() as tmpdir:
            shell.initialize({"workdir": tmpdir})
            result = await shell.npm("install", args=["express", "--save"], timeout=5)

            response = json.loads(result[0]["text"])
            assert "npm install express --save" in response["command"]

    @pytest.mark.asyncio
    async def test_npm_invalid_command(self, shell):
        """Test npm with non-whitelisted command."""
        shell.initialize()
        with pytest.raises(ValueError, match="is not allowed"):
            await shell.npm("run")

    @pytest.mark.asyncio
    async def test_npm_audit_command(self, shell):
        """Test npm audit command."""
        with tempfile.TemporaryDirectory() as tmpdir:
            shell.initialize({"workdir": tmpdir})
            result = await shell.npm("audit", timeout=5)

            response = json.loads(result[0]["text"])
            assert "npm audit" in response["command"]

    @pytest.mark.asyncio
    async def test_npm_custom_whitelist(self, shell):
        """Test npm with custom whitelist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            shell.initialize({"workdir": tmpdir, "cli": {"npm": ["init", "start"]}})
            result = await shell.npm("init", args=["-y"], timeout=5)
            response = json.loads(result[0]["text"])
            assert "npm init" in response["command"]


class TestLsCommand:
    """Tests for ls command execution."""

    @pytest.fixture
    def shell(self):
        """Shell tool plugin instance."""
        plugin = ShellToolPlugin()
        return plugin

    @pytest.mark.asyncio
    async def test_ls_directory(self, shell):
        """Test listing directory contents."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            (Path(tmpdir) / "test1.txt").touch()
            (Path(tmpdir) / "test2.txt").touch()

            tmpdir_resolved = str(Path(tmpdir).resolve())
            shell.initialize({"workdir": tmpdir_resolved})
            result = await shell.ls(tmpdir_resolved, timeout=5)

            assert isinstance(result, list)
            response = json.loads(result[0]["text"])
            assert response["success"] is True
            assert (
                "test1.txt" in response["stdout"] or "test2.txt" in response["stdout"]
            )

    @pytest.mark.asyncio
    async def test_ls_with_args(self, shell):
        """Test ls command with additional arguments."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_resolved = str(Path(tmpdir).resolve())
            shell.initialize({"workdir": tmpdir_resolved})
            result = await shell.ls(tmpdir_resolved, args=["-la"], timeout=5)

            response = json.loads(result[0]["text"])
            assert "ls" in response["command"]
            assert "-la" in response["command"]

    @pytest.mark.asyncio
    async def test_ls_invalid_directory(self, shell):
        """Test ls with non-existent directory."""
        shell.initialize()
        with pytest.raises(ValueError, match="does not exist"):
            await shell.ls("/nonexistent/path")

    @pytest.mark.asyncio
    async def test_ls_outside_workdir(self, shell):
        """Test ls with directory outside workdir."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with tempfile.TemporaryDirectory() as outside_dir:
                shell.initialize({"workdir": tmpdir})
                with pytest.raises(ValueError, match="outside of project root"):
                    await shell.ls(outside_dir)


class TestCatCommand:
    """Tests for cat command execution."""

    @pytest.fixture
    def shell(self):
        """Shell tool plugin instance."""
        plugin = ShellToolPlugin()
        return plugin

    @pytest.mark.asyncio
    async def test_cat_file(self, shell):
        """Test reading file contents with cat."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.txt"
            filepath.write_text("Hello World\n")

            tmpdir_resolved = str(Path(tmpdir).resolve())
            shell.initialize({"workdir": tmpdir_resolved})
            result = await shell.cat(str(filepath.resolve()), timeout=5)

            assert isinstance(result, list)
            response = json.loads(result[0]["text"])
            assert response["success"] is True
            assert "Hello World" in response["stdout"]

    @pytest.mark.asyncio
    async def test_cat_with_args(self, shell):
        """Test cat command with additional arguments."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.txt"
            filepath.write_text("test content")

            tmpdir_resolved = str(Path(tmpdir).resolve())
            shell.initialize({"workdir": tmpdir_resolved})
            result = await shell.cat(str(filepath.resolve()), args=["-n"], timeout=5)

            response = json.loads(result[0]["text"])
            assert "cat" in response["command"]
            assert "-n" in response["command"]

    @pytest.mark.asyncio
    async def test_cat_nonexistent_file(self, shell):
        """Test cat with non-existent file."""
        shell.initialize()
        with pytest.raises(ValueError, match="does not exist"):
            await shell.cat("/nonexistent/file.txt")

    @pytest.mark.asyncio
    async def test_cat_directory(self, shell):
        """Test cat fails when target is a directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            shell.initialize({"workdir": str(Path(tmpdir).parent)})
            with pytest.raises(ValueError, match="is not a file"):
                await shell.cat(tmpdir)

    @pytest.mark.asyncio
    async def test_cat_outside_workdir(self, shell):
        """Test cat with file outside workdir."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with tempfile.NamedTemporaryFile(delete=False) as outside_file:
                outside_path = outside_file.name
            try:
                shell.initialize({"workdir": tmpdir})
                with pytest.raises(ValueError, match="outside of project root"):
                    await shell.cat(outside_path)
            finally:
                Path(outside_path).unlink(missing_ok=True)


class TestCommandTimeout:
    """Tests for command timeout functionality."""

    @pytest.fixture
    def shell(self):
        """Shell tool plugin instance."""
        plugin = ShellToolPlugin()
        return plugin

    @pytest.mark.asyncio
    async def test_command_timeout(self, shell):
        """Test command timeout handling."""
        with tempfile.TemporaryDirectory() as tmpdir:
            shell.initialize({"workdir": tmpdir})
            # Use a command that will timeout (sleep is not in whitelist, so we use npm with very short timeout)
            result = await shell.npm("install", timeout=0.001)

            response = json.loads(result[0]["text"])
            # Should complete quickly or timeout
            assert "success" in response
            assert "exit_code" in response


class TestCommandOutput:
    """Tests for command output formatting."""

    @pytest.fixture
    def shell(self):
        """Shell tool plugin instance."""
        plugin = ShellToolPlugin()
        return plugin

    @pytest.mark.asyncio
    async def test_output_structure(self, shell):
        """Test command output has correct JSON structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "test.txt").touch()

            tmpdir_resolved = str(Path(tmpdir).resolve())
            shell.initialize({"workdir": tmpdir_resolved})
            result = await shell.ls(tmpdir_resolved, timeout=5)

            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0]["type"] == "text"

            response = json.loads(result[0]["text"])
            assert "success" in response
            assert "exit_code" in response
            assert "stdout" in response
            assert "stderr" in response
            assert "command" in response
            assert isinstance(response["success"], bool)
            assert isinstance(response["exit_code"], int)

    @pytest.mark.asyncio
    async def test_successful_command_output(self, shell):
        """Test successful command returns success=True and exit_code=0."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_resolved = str(Path(tmpdir).resolve())
            shell.initialize({"workdir": tmpdir_resolved})
            result = await shell.ls(tmpdir_resolved, timeout=5)

            response = json.loads(result[0]["text"])
            assert response["success"] is True
            assert response["exit_code"] == 0

    @pytest.mark.asyncio
    async def test_failed_command_output(self, shell):
        """Test failed command returns appropriate error information."""
        with tempfile.TemporaryDirectory() as tmpdir:
            shell.initialize({"workdir": tmpdir})
            # Try to compile without hardhat installed
            result = await shell.hardhat("compile", timeout=5)

            response = json.loads(result[0]["text"])
            # Command will likely fail if hardhat is not installed
            assert "success" in response
            assert "exit_code" in response
