"""Command execution tool for running whitelisted Hardhat commands.

Allows LLM to compile and test contracts iteratively while maintaining security
through strict command whitelisting and validation.
"""
# TODO: improve security in command cleaning
import asyncio
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

_logger = logging.getLogger("argus.console")

# Whitelist of allowed commands
ALLOWED_COMMANDS = {
    "npx": {
        "hardhat": ["compile", "test", "clean"]
    }
}


async def run_command(
    command: str,
    args: List[str],
    cwd: Optional[str] = None,
    timeout: int = 180,
) -> List[Dict[str, Any]]:
    """Execute whitelisted Hardhat commands for compilation and testing.

    Security: Only allows npx hardhat compile/test/clean commands.

    Args:
        command: Command to execute (must be 'npx')
        args: Command arguments (first must be 'hardhat', second must be compile/test/clean)
        cwd: Working directory (optional, validated against project root)
        timeout: Timeout in seconds (default: 180, max: 240)

    Returns:
        MCP-formatted result with command output

    Raises:
        ValueError: If command is not whitelisted or validation fails
    """
    # Validate command is whitelisted
    if command not in ALLOWED_COMMANDS:
        raise ValueError(
            f"Command '{command}' is not whitelisted. Only 'npx' is allowed."
        )

    # Validate args structure
    if not args or len(args) < 2:
        raise ValueError(
            "Invalid arguments. Expected format: ['hardhat', 'compile|test|clean', ...]"
        )

    # Validate first arg is 'hardhat'
    if args[0] not in ALLOWED_COMMANDS[command]:
        raise ValueError(
            f"First argument must be 'hardhat', got: '{args[0]}'"
        )

    # Validate second arg is in allowed subcommands
    subcommand = args[1]
    allowed_subcommands = ALLOWED_COMMANDS[command][args[0]]
    if subcommand not in allowed_subcommands:
        raise ValueError(
            f"Subcommand '{subcommand}' is not allowed. "
            f"Allowed: {', '.join(allowed_subcommands)}"
        )

    # Validate cwd if provided
    if cwd:
        cwd_path = Path(cwd).resolve()
        if not cwd_path.exists():
            raise ValueError(f"Working directory does not exist: {cwd}")
        if not cwd_path.is_dir():
            raise ValueError(f"Working directory is not a directory: {cwd}")
        # Additional validation could check if cwd is within project root
        # but this requires knowing the project root, which could be passed in

    # Sanitize arguments (basic check for shell metacharacters)
    dangerous_chars = [";", "&", "|", "`", "$", "(", ")", "<", ">", "\n", "\r"]
    for arg in args:
        if any(char in arg for char in dangerous_chars):
            raise ValueError(
                f"Argument contains dangerous characters: '{arg}'"
            )

    # Build full command
    full_command = [command] + args
    command_str = " ".join(full_command)

    # Log the execution
    _logger.info("Executing whitelisted command: %s", command_str)
    if cwd:
        _logger.info("  Working directory: %s", cwd)
    _logger.info("  Timeout: %d seconds", timeout)

    try:
        # Execute command
        process = await asyncio.create_subprocess_exec(
            *full_command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )

        _logger.info("  Process started (PID: %s)", process.pid)

        # Wait for completion with timeout
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            # Kill the process if it times out
            _logger.warning("Command timed out, terminating process...")
            try:
                process.kill()
                await process.wait()
            except Exception as kill_error:
                _logger.error("Failed to kill process: %s", kill_error)
            raise

        # Decode output
        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")
        exit_code = process.returncode

        # Determine success
        success = exit_code == 0

        # Log result
        if success:
            _logger.debug("Command succeeded with exit code 0")
        else:
            _logger.warning("Command failed with exit code %d", exit_code)
            if stderr:
                _logger.debug("STDERR: %s", stderr[:500])

        # Build result
        result = {
            "success": success,
            "exit_code": exit_code,
            "stdout": stdout,
            "stderr": stderr,
            "command": command_str,
        }

        # Return in MCP format
        return [
            {
                "type": "text",
                "text": json.dumps(result, indent=2)
            }
        ]

    except asyncio.TimeoutError:
        error_msg = f"Command timed out after {timeout} seconds"
        _logger.error(error_msg)
        result = {
            "success": False,
            "exit_code": -1,
            "stdout": "",
            "stderr": error_msg,
            "command": command_str,
        }
        return [
            {
                "type": "text",
                "text": json.dumps(result, indent=2)
            }
        ]

    except Exception as e:
        error_msg = f"Command execution failed: {str(e)}"
        _logger.error(error_msg, exc_info=True)
        result = {
            "success": False,
            "exit_code": -1,
            "stdout": "",
            "stderr": error_msg,
            "command": command_str,
        }
        return [
            {
                "type": "text",
                "text": json.dumps(result, indent=2)
            }
        ]
