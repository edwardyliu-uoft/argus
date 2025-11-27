"""Filesystem tools for MCP server.

Provides tools for file and directory operations including:
- File search by extension (find .sol, .md files, etc.)
- File operations (read, write, append)
- Directory operations (create, list)
- Path operations (get info, check existence)
"""

from typing import Dict, Any, Optional
from pathlib import Path
import logging
from datetime import datetime

from argus import utils
from argus.plugins import MCPToolPlugin


_logger = logging.getLogger("argus.console")


class FilesystemToolPlugin(MCPToolPlugin):
    """Plugin wrapper for filesystem tools"""

    config: Dict[str, Any]

    @property
    def name(self) -> str:
        return "filesystem"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Filesystem operations"

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the filesystem tool plugin."""
        self.config = config or {}
        self.tools = {
            "list_directory": self.list_directory,
            "find_files_by_extension": self.find_files_by_extension,
            "read_file_info": self.read_file_info,
            "read_file": self.read_file,
            "write_file": self.write_file,
            "append_file": self.append_file,
            "create_directory": self.create_directory,
        }
        self.initialized = True

    async def list_directory(
        self,
        directory_path: Optional[str] = None,
        include_files: bool = True,
        include_dirs: bool = True,
        recursive: bool = False,
    ) -> Dict[str, Any]:
        """
        List contents of a directory.

        Returns information about files and subdirectories in the specified directory.
        Can be used recursively to explore the entire directory tree.

        Args:
            directory_path: Path to the directory to list. Defaults to workdir if None.
            include_files: If True, include files in the results. Default True.
            include_dirs: If True, include subdirectories in the results. Default True.
            recursive: If True, list contents recursively. Default False.

        Returns:
            Dict[str, Any]: Dictionary containing:
                - success (bool): Whether the operation succeeded
                - path (str): Absolute path of the listed directory
                - items (list): List of dictionaries, each containing:
                    - name (str): Item name
                    - path (str): Full path to item
                    - type (str): 'file' or 'directory'
                    - total_size (int): Size in bytes (files only, 0 for directories)
                - count (int): Total number of items
                - error (str|None): Error message if operation failed

        Examples:
            # List current directory
            list_directory()

            # List contracts folder
            list_directory(directory_path="contracts")

            # List all files recursively
            list_directory(directory_path="src", recursive=True)
        """
        try:
            # Resolve path
            if directory_path is None:
                path = Path(
                    utils.conf_get(
                        self.config,
                        "workdir",
                        Path.cwd().as_posix(),
                    )
                )
            else:
                path = Path(directory_path)
                if not path.is_absolute():
                    work_dir = Path(
                        utils.conf_get(
                            self.config,
                            "workdir",
                            Path.cwd().as_posix(),
                        )
                    )
                    path = work_dir / path

            # Validate directory exists
            if not path.exists():
                return {
                    "success": False,
                    "path": "",
                    "items": [],
                    "count": 0,
                    "error": f"Directory does not exist: {path}",
                }

            if not path.is_dir():
                return {
                    "success": False,
                    "path": "",
                    "items": [],
                    "count": 0,
                    "error": f"Path is not a directory: {path}",
                }

            # List contents
            items = []
            pattern = "**/*" if recursive else "*"

            for item in sorted(path.glob(pattern)):
                # Skip if filtering
                if item.is_file() and not include_files:
                    continue
                if item.is_dir() and not include_dirs:
                    continue

                items.append(
                    {
                        "name": item.name,
                        "path": item.resolve().as_posix(),
                        "type": "file" if item.is_file() else "directory",
                        "total_size": item.stat().st_size if item.is_file() else 0,
                    }
                )
            _logger.info("Listed directory: %s (%d items)", path, len(items))
            return {
                "success": True,
                "path": path.as_posix(),
                "items": items,
                "count": len(items),
                "error": None,
            }

        # pylint: disable=broad-except
        except Exception as e:
            _logger.error("Error listing directory: %s", e)
            return {
                "success": False,
                "path": "",
                "items": [],
                "count": 0,
                "error": str(e),
            }

    async def find_files_by_extension(
        self,
        extension: str,
        directory: Optional[str] = None,
        recursive: bool = True,
    ) -> Dict[str, Any]:
        """
        Find all files with a specific extension in a directory.

        Useful for discovering project files like Solidity contracts (.sol),
        documentation (.md), configuration files (.json), tests, etc.

        Args:
            extension: File extension to search for (e.g. 'sol', 'md', 'json').
                    Can include or omit the leading dot (both 'sol' and '.sol' work).
            directory: Directory path to search in. Defaults to current working directory.
                    Can be absolute or relative path.
            recursive: If True, searches subdirectories recursively. If False, only
                    searches the immediate directory. Default is True.

        Returns:
            Dict[str, Any]: Dictionary containing:
                - success (bool): Whether the operation succeeded
                - files (list): List of file paths (strings) matching the extension
                - count (int): Number of files found
                - error (str|None): Error message if operation failed

        Examples:
            # Find all Solidity contracts
            find_files_by_extension(extension="sol")

            # Find markdown files in docs folder only
            find_files_by_extension(extension=".md", directory="docs", recursive=False)

            # Find all JSON config files
            find_files_by_extension(extension="json")
        """
        try:
            # Normalize extension (ensure it has a dot)
            if not extension.startswith("."):
                extension = f".{extension}"

            # Determine search directory
            if directory is None:
                search_dir = Path(
                    utils.conf_get(
                        self.config,
                        "workdir",
                        Path.cwd().as_posix(),
                    )
                )
            else:
                search_dir = Path(directory)
                if not search_dir.is_absolute():
                    work_dir = Path(
                        utils.conf_get(
                            self.config,
                            "workdir",
                            Path.cwd().as_posix(),
                        )
                    )
                    search_dir = work_dir / search_dir

            # Validate directory exists
            if not search_dir.exists():
                return {
                    "success": False,
                    "files": [],
                    "count": 0,
                    "error": f"Directory does not exist: {search_dir}",
                }

            if not search_dir.is_dir():
                return {
                    "success": False,
                    "files": [],
                    "count": 0,
                    "error": f"Path is not a directory: {search_dir}",
                }

            # Search for files
            pattern = f"**/*{extension}" if recursive else f"*{extension}"
            files = list(search_dir.glob(pattern))

            # Convert to strings and sort
            file_paths = sorted([f.resolve().as_posix() for f in files if f.is_file()])
            _logger.info(
                "Found %d files with extension '%s' in %s",
                len(file_paths),
                extension,
                search_dir,
            )
            return {
                "success": True,
                "files": file_paths,
                "count": len(file_paths),
                "error": None,
            }

        # pylint: disable=broad-except
        except Exception as e:
            _logger.error("Error finding files: %s", e)
            return {
                "success": False,
                "files": [],
                "count": 0,
                "error": str(e),
            }

    async def read_file_info(self, file_path: str) -> Dict[str, Any]:
        """
        Get detailed information about a file or directory.

        Provides metadata including size, modification time, type, and existence status.

        Args:
            file_path: Path to the file or directory. Can be absolute or relative.

        Returns:
            Dict[str, Any]: Dictionary containing:
                - success (bool): Whether the operation succeeded
                - exists (bool): Whether the path exists
                - path (str): Absolute path
                - type (str|None): 'file', 'directory', or None if unknown or not applicable
                - total_size (int): Size in bytes (0 for directories)
                - modified (str): Last modified timestamp (ISO format)
                - error (str|None): Error message if operation failed

        Examples:
            # Check if a contract exists and get its size
            read_file_info(file_path="contracts/Token.sol")

            # Get info about a directory
            read_file_info(file_path="test")
        """
        try:
            # Resolve path
            path = Path(file_path)
            if not path.is_absolute():
                work_dir = Path(
                    utils.conf_get(
                        self.config,
                        "workdir",
                        Path.cwd().as_posix(),
                    )
                )
                path = work_dir / path

            # Check existence
            if not path.exists():
                return {
                    "success": True,
                    "exists": False,
                    "path": path.as_posix(),
                    "type": None,
                    "total_size": 0,
                    "modified": "",
                    "error": None,
                }

            # Get stats
            stat = path.stat()
            file_type = "file" if path.is_file() else "directory"
            modified = datetime.fromtimestamp(stat.st_mtime).isoformat()
            _logger.info(
                "Got info for: %s (type=%s, total_size=%d)",
                path,
                file_type,
                stat.st_size,
            )
            return {
                "success": True,
                "exists": True,
                "path": path.as_posix(),
                "type": file_type,
                "total_size": stat.st_size,
                "modified": modified,
                "error": None,
            }

        # pylint: disable=broad-except
        except Exception as e:
            _logger.error("Error getting file info: %s", e)
            return {
                "success": False,
                "exists": False,
                "path": "",
                "type": None,
                "total_size": 0,
                "modified": "",
                "error": str(e),
            }

    async def read_file(self, file_path: str) -> Dict[str, Any]:
        """
        Read the contents of a file.

        Reads text or binary files and returns their contents. Useful for examining
        smart contracts, configuration files, documentation, or any project files.

        Args:
            file_path: Path to the file to read. Can be absolute or relative to workdir.

        Returns:
            Dict[str, Any]: Dictionary containing:
                - success (bool): Whether the read operation succeeded
                - content (str): File contents as string
                - total_size (int): File size in bytes
                - error (str|None): Error message if operation failed

        Examples:
            # Read a Solidity contract
            read_file(file_path="contracts/Token.sol")

            # Read configuration file
            read_file(file_path="hardhat.config.js")
        """
        try:
            # Resolve path
            path = Path(file_path)
            if not path.is_absolute():
                work_dir = Path(
                    utils.conf_get(
                        self.config,
                        "workdir",
                        Path.cwd().as_posix(),
                    )
                )
                path = work_dir / path

            # Validate file exists
            if not path.exists():
                return {
                    "success": False,
                    "content": "",
                    "total_size": 0,
                    "error": f"File does not exist: {path}",
                }

            if not path.is_file():
                return {
                    "success": False,
                    "content": "",
                    "total_size": 0,
                    "error": f"Path is not a file: {path}",
                }

            # Read file
            content = path.read_text(encoding="utf-8")
            total_size = path.stat().st_size
            _logger.info("Read file: %s (%d bytes)", path, total_size)
            return {
                "success": True,
                "content": content,
                "total_size": total_size,
                "error": None,
            }

        except UnicodeDecodeError as e:
            _logger.error("Error reading file (encoding issue): %s", e)
            return {
                "success": False,
                "content": "",
                "total_size": 0,
                "error": f"File encoding error: {str(e)}",
            }
        # pylint: disable=broad-except
        except Exception as e:
            _logger.error("Error reading file: %s", e)
            return {
                "success": False,
                "content": "",
                "total_size": 0,
                "error": str(e),
            }

    async def write_file(self, file_path: str, content: str) -> Dict[str, Any]:
        """
        Write content to a file, creating it if it doesn't exist or overwriting if it does.

        Use this to create new files or replace existing file contents. The parent
        directory will be created automatically if it doesn't exist.

        Args:
            file_path: Path to the file to write. Can be absolute or relative to workdir.
            content: Content to write to the file as a string.

        Returns:
            Dict[str, Any]: Dictionary containing:
                - success (bool): Whether the write operation succeeded
                - path (str): Absolute path to the written file
                - total_size (int): Number of bytes written
                - error (str|None): Error message if operation failed

        Examples:
            # Create a new Solidity contract
            write_file(
                file_path="contracts/MyToken.sol",
                content="pragma solidity ^0.8.0;\n\ncontract MyToken {...}"
            )

            # Create a README
            write_file(file_path="README.md", content="# My Project\n\n...")
        """
        try:
            # Resolve path
            path = Path(file_path)
            if not path.is_absolute():
                work_dir = Path(
                    utils.conf_get(
                        self.config,
                        "workdir",
                        Path.cwd().as_posix(),
                    )
                )
                path = work_dir / path

            # Create parent directories if needed
            path.parent.mkdir(parents=True, exist_ok=True)

            # Write file
            path.write_text(content, encoding="utf-8")
            total_size = len(content.encode("utf-8"))
            _logger.info("Wrote file: %s (%d bytes)", path, total_size)
            return {
                "success": True,
                "path": path.as_posix(),
                "total_size": total_size,
                "error": None,
            }

        # pylint: disable=broad-except
        except Exception as e:
            _logger.error("Error writing file: %s", e)
            return {
                "success": False,
                "path": "",
                "total_size": 0,
                "error": str(e),
            }

    async def append_file(self, file_path: str, content: str) -> Dict[str, Any]:
        """
        Append content to the end of a file, creating it if it does not exist.

        Useful for adding to log files, updating documentation, or incrementally
        building files without replacing existing content.

        Args:
            file_path: Path to the file to append to. Can be absolute or relative to workdir.
            content: Content to append to the file as a string.

        Returns:
            Dict[str, Any]: Dictionary containing:
                - success (bool): Whether the append operation succeeded
                - path (str): Absolute path to the file
                - appended_size (int): Number of bytes appended
                - total_size (int): Total file size after append
                - error (str|None): Error message if operation failed

        Examples:
            # Add to a log file
            append_file(file_path="audit.log", content="\n[2024-01-01] Analysis completed")

            # Add documentation
            append_file(file_path="CHANGELOG.md", content="\n## v1.0.1\n- Bug fixes")
        """
        try:
            # Resolve path
            path = Path(file_path)
            if not path.is_absolute():
                work_dir = Path(
                    utils.conf_get(
                        self.config,
                        "workdir",
                        Path.cwd().as_posix(),
                    )
                )
                path = work_dir / path

            # Create parent directories if needed
            path.parent.mkdir(parents=True, exist_ok=True)

            # Append to file
            with open(path, "a", encoding="utf-8") as f:
                f.write(content)

            appended_size = len(content.encode("utf-8"))
            total_size = path.stat().st_size
            _logger.info(
                "Appended to file: %s (%d bytes appended, %d total)",
                path,
                appended_size,
                total_size,
            )
            return {
                "success": True,
                "path": path.as_posix(),
                "appended_size": appended_size,
                "total_size": total_size,
                "error": None,
            }

        # pylint: disable=broad-except
        except Exception as e:
            _logger.error("Error appending to file: %s", e)
            return {
                "success": False,
                "path": "",
                "appended_size": 0,
                "total_size": 0,
                "error": str(e),
            }

    async def create_directory(self, directory_path: str) -> Dict[str, Any]:
        """
        Create a directory and all necessary parent directories.

        Similar to 'mkdir -p' on Unix systems. Safe to call on existing directories.

        Args:
            directory_path: Path to the directory to create. Can be absolute or relative.

        Returns:
            Dict[str, Any]: Dictionary containing:
                - success (bool): Whether the operation succeeded
                - path (str): Absolute path to the created directory
                - created (bool): True if directory was created, False if already existed
                - error (str|None): Error message if operation failed

        Examples:
            # Create contracts directory
            create_directory(directory_path="contracts/tokens")

            # Create test output directory
            create_directory(directory_path="test/output")
        """
        try:
            # Resolve path
            path = Path(directory_path)
            if not path.is_absolute():
                work_dir = Path(
                    utils.conf_get(
                        self.config,
                        "workdir",
                        Path.cwd().as_posix(),
                    )
                )
                path = work_dir / path

            # Check if already exists
            existed = path.exists()

            # Create directory
            path.mkdir(parents=True, exist_ok=True)
            _logger.info(
                "Directory %s: %s",
                "already existed" if existed else "created",
                path,
            )
            return {
                "success": True,
                "path": path.as_posix(),
                "created": not existed,
                "error": None,
            }

        # pylint: disable=broad-except
        except Exception as e:
            _logger.error("Error creating directory: %s", e)
            return {
                "success": False,
                "path": "",
                "created": False,
                "error": str(e),
            }
