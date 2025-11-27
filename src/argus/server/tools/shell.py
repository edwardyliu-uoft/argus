"""Shell execution tool for executing whitelisted commands.

Allows the LLM to compile and test contracts iteratively while maintaining security
through strict command whitelisting and validation.
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import logging
import json
import asyncio


from argus import utils
from argus.plugins import MCPToolPlugin


_logger = logging.getLogger("argus.console")

BLACKLIST_CHARS = [";", "&", "|", "`", "$", "(", ")", "<", ">", "\n", "\r"]


class ShellToolPlugin(MCPToolPlugin):
    """Plugin wrapper for shell tools."""

    config: Dict[str, Any]

    @property
    def name(self) -> str:
        return "shell"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Shell operations"

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the filesystem tool plugin."""
        self.config = config or {}
        if "cli" not in self.config:
            self.config["cli"] = {
                "hardhat": ["compile", "test", "clean"],
                "npm": ["install", "uninstall", "audit", "ls"],
                "ls": None,
                "cat": None,
            }
        self.tools = {
            command: getattr(self, command)
            for command in utils.conf_get(self.config, "cli").keys()
        }
        self.initialized = True

    def __validate_cwd(
        self,
        cwd: Optional[str] = None,
        flags: Optional[Dict[str, bool]] = None,
    ) -> None:
        if cwd:
            flags = flags or {
                "dir": True,
                "file": False,
            }

            wd = Path(
                utils.conf_get(
                    self.config,
                    "workdir",
                    Path.cwd().as_posix(),
                )
            ).resolve()
            cwdr = Path(cwd).resolve()
            if not cwdr.exists():
                raise ValueError(f"Current work directory does not exist: {cwd}")
            if flags["dir"] and not cwdr.is_dir():
                raise ValueError(f"Current work directory is not a directory: {cwd}")
            if flags["file"] and not cwdr.is_file():
                raise ValueError(f"Current work directory is not a file: {cwd}")
            if wd not in cwdr.parents and wd != cwdr:
                raise ValueError(
                    f"Current work directory '{cwd}' is outside of project root '{wd}'"
                )

    def __validate_args(self, args: Optional[List[str]] = None) -> None:
        for arg in args if args else []:
            if any(char in arg for char in BLACKLIST_CHARS):
                raise ValueError(f"Argument contains a blacklisted character: '{arg}'")

    async def __exec_command(
        self,
        command: List[str],
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd: Optional[str] = None,
        timeout: int = 180,
    ) -> List[Dict[str, Any]]:

        command_str = " ".join(command)

        _logger.info("Executing command: %s", command_str)
        if cwd:
            _logger.info("\tWork directory: %s", cwd)
        _logger.info("\tTimeout: %d seconds", timeout)

        try:
            subprocess = await asyncio.create_subprocess_exec(
                *command,
                stdout=stdout,
                stderr=stderr,
                cwd=cwd,
            )
            _logger.info("\tProcess started (PID: %s)", subprocess.pid)

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    subprocess.communicate(),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                _logger.warning("Command timed out, terminating process...")
                try:
                    subprocess.kill()
                    await subprocess.wait()

                # pylint: disable=broad-except
                except Exception as kill_error:
                    _logger.error("Failed to kill process: %s", kill_error)
                raise

            stdout = stdout_bytes.decode("utf-8", errors="replace")
            stderr = stderr_bytes.decode("utf-8", errors="replace")
            exit_code = subprocess.returncode
            success = exit_code == 0

            if success:
                _logger.debug("Command succeeded with exit code 0")
            else:
                _logger.warning("Command failed with exit code %d", exit_code)
                if stderr:
                    _logger.error("stderr: %s", stderr[:500])

            json_res = {
                "success": success,
                "exit_code": exit_code,
                "stdout": stdout,
                "stderr": stderr,
                "command": command_str,
            }
            return [{"type": "text", "text": json.dumps(json_res, indent=2)}]

        except asyncio.TimeoutError:
            error_message = f"Command timed out after {timeout} seconds"
            _logger.error(error_message)
            json_res = {
                "success": False,
                "exit_code": -1,
                "stdout": "",
                "stderr": error_message,
                "command": command_str,
            }
            return [{"type": "text", "text": json.dumps(json_res, indent=2)}]

        # pylint: disable=broad-except
        except Exception as e:
            error_message = f"Command execution failed: {str(e)}"
            _logger.error(error_message, exc_info=True)
            json_res = {
                "success": False,
                "exit_code": -1,
                "stdout": "",
                "stderr": error_message,
                "command": command_str,
            }
            return [{"type": "text", "text": json.dumps(json_res, indent=2)}]

    async def hardhat(
        self,
        command: str,
        args: Optional[List[str]] = None,
        cwd: Optional[str] = None,
        timeout: int = 180,
    ) -> List[Dict[str, Any]]:
        """Execute a hardhat command.

        Args:
            command: Hardhat command to execute
                (e.g. compile, test, run, node, clean, deploy, status, verify)
            args: Command arguments
            cwd: Optional current work directory (Validated against project root)
            timeout: Timeout in seconds (default: 180)
        """
        # Validate command against whitelist
        whitelist = utils.conf_get(
            self.config,
            "cli.hardhat",
            ["compile", "test", "clean"],
        )
        if whitelist and command not in whitelist:
            raise ValueError(
                f"Hardhat command '{command}' is not allowed. Use: {whitelist}"
            )

        # Validate cwd
        self.__validate_cwd(cwd)

        # Sanitize arguments
        self.__validate_args(args)

        # Build full command
        cmd = ["npx", "hardhat", command] + (args if args else [])
        return await self.__exec_command(cmd, cwd=cwd, timeout=timeout)

    async def npm(
        self,
        command: str,
        args: Optional[List[str]] = None,
        cwd: Optional[str] = None,
        timeout: int = 180,
    ) -> List[Dict[str, Any]]:
        """Execute a npm command.

        Args:
            command: Npm command to execute
                (e.g. init, install, update, uninstall, run, audit, ls)
            args: Command arguments
            cwd: Optional current work directory (Validated against project root)
            timeout: Timeout in seconds (default: 180)
        """
        # Validate command against whitelist
        whitelist = utils.conf_get(
            self.config,
            "cli.npm",
            ["install", "uninstall", "audit", "ls"],
        )
        if whitelist and command not in whitelist:
            raise ValueError(
                f"Npm command '{command}' is not allowed. Use: {whitelist}"
            )

        # Validate cwd
        self.__validate_cwd(cwd)

        # Sanitize arguments
        self.__validate_args(args)

        # Build full command
        cmd = ["npm", command] + (args if args else [])
        return await self.__exec_command(cmd, cwd=cwd, timeout=timeout)

    async def ls(
        self,
        directory: str,
        args: Optional[List[str]] = None,
        cwd: Optional[str] = None,
        timeout: int = 60,
    ) -> List[Dict[str, Any]]:
        """Execute the 'ls' (i.e. list) command.

        Args:
            directory: Directory to list (Validated against project root)
            args: Command arguments
            cwd: Optional current work directory (Validated against project root)
            timeout: Timeout in seconds (default: 60)
        """
        # Validate dir
        self.__validate_cwd(directory)

        # Validate cwd
        self.__validate_cwd(cwd)

        # Sanitize arguments
        self.__validate_args(args)

        # Build full command
        cmd = ["ls", directory] + (args if args else [])
        return await self.__exec_command(cmd, cwd=cwd, timeout=timeout)

    async def cat(
        self,
        file: str,
        args: Optional[List[str]] = None,
        cwd: Optional[str] = None,
        timeout: int = 60,
    ) -> List[Dict[str, Any]]:
        """Execute the 'cat' command.

        Args:
            file: Path to file (Validated against project root)
            args: Command arguments
            cwd: Optional current work directory (Validated against project root)
            timeout: Timeout in seconds (default: 60)
        """
        # Validate file
        self.__validate_cwd(
            file,
            flags={
                "dir": False,
                "file": True,
            },
        )

        # Validate cwd
        self.__validate_cwd(cwd)

        # Sanitize arguments
        self.__validate_args(args)

        # Build full command
        cmd = ["cat", file] + (args if args else [])
        return await self.__exec_command(cmd, cwd=cwd, timeout=timeout)
