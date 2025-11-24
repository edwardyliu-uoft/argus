"""Filesystem resources for MCP server.

Provides resource URIs for accessing files and directories in the workspace.
Resources provide read-only access to file contents via URI schemes.
"""

from pathlib import Path
import logging

from argus.core import conf

_logger = logging.getLogger("argus.console")


async def get_workspace() -> str:
    """
    List all files in the workspace as an MCP resource.

    Returns a formatted list of all files in the workspace directory tree,
    useful for understanding project structure and available files.

    Returns:
        str: Formatted text containing:
            - Workspace root path
            - Tree-like listing of all files and directories
            - File count

    Example output:
        Workspace: /home/user/my-project

        Files:
        ├── contracts/
        │   ├── Token.sol
        │   └── NFT.sol
        ├── test/
        │   └── Token.test.js
        └── README.md

        Total: 4 files
    """
    try:
        work_dir = Path(conf.get("workdir", Path.cwd().as_posix()))
        if not work_dir.exists():
            return f"Error: Workspace directory does not exist: {work_dir}"

        # Collect all files and directories recursively
        files = []
        dirs = set()
        for item in sorted(work_dir.rglob("*")):
            if item.is_file():
                rpath = item.relative_to(work_dir)
                files.append(rpath)
                # Collect all parent directories
                for parent in rpath.parents:
                    if parent != Path("."):
                        dirs.add(parent)

        # Format the output with a proper tree structure
        outstack = [f"Workspace: {work_dir}\n"]
        outstack.append("Files:")

        if not files:
            outstack.append("\t(empty workspace)")
        else:
            # Combine directories and files, then sort
            items = []
            for d in dirs:
                items.append((d, True))  # (path, is_dir)
            for f in files:
                items.append((f, False))  # (path, is_file)

            # Sort by path
            items.sort(key=lambda x: str(x[0]))

            # Display tree structure
            for path, is_dir in items:
                depth = len(path.parts) - 1
                indent = "\t" * (depth + 1)
                if is_dir:
                    outstack.append(f"{indent}{path.as_posix()}/")
                else:
                    outstack.append(f"{indent}{path.name}")

        outstack.append(f"\nTotal: {len(files)} files")

        output = "\n".join(outstack)
        _logger.info("Listed workspace files: %d files", len(files))

        return output

    # pylint: disable=broad-except
    except Exception as e:
        _logger.error("Error listing workspace files: %s", e)
        return f"Error listing workspace files: {str(e)}"


async def get_project_structure() -> str:
    """
    Get project structure overview.

    Returns a hierarchical view of directories and key files, helping understand
    project organization. Excludes common build artifacts and dependencies.

    Returns:
        str: Formatted text containing:
            - Directory tree structure
            - File type summary
            - Key configuration files

    Example output:
        Project Structure:

        .
        ├── contracts/
        │   ├── tokens/
        │   └── governance/
        ├── test/
        ├── scripts/
        └── docs/

        File types:
        - Solidity (.sol): 12 files
        - JavaScript (.js): 8 files
        - Markdown (.md): 3 files

        Configuration:
        - hardhat.config.js
        - package.json
    """
    try:
        work_dir = Path(conf.get("workdir", Path.cwd().as_posix()))
        if not work_dir.exists():
            return f"Error: Workspace directory does not exist: {work_dir}"

        # Directories to skip
        skip_dirs = {
            "node_modules",
            ".git",
            "__pycache__",
            ".venv",
            "venv",
            "build",
            "dist",
            ".pytest_cache",
            ".mypy_cache",
            "artifacts",
            "cache",
        }
        config_targets = {
            "package.json",
            "hardhat.config.js",
            "hardhat.config.ts",
            "truffle-config.js",
            "foundry.toml",
            ".solhint.json",
            "slither.config.json",
        }

        # Collect directory structure
        dirs = set()
        files_by_ext = {}
        config_files = []
        for item in work_dir.rglob("*"):
            # Skip excluded directories
            if any(part in skip_dirs for part in item.parts):
                continue

            if item.is_dir():
                rpath = item.relative_to(work_dir)
                if rpath != Path("."):
                    dirs.add(rpath.as_posix())
            elif item.is_file():
                # Track file extensions
                ext = item.suffix.lower()
                if ext:
                    files_by_ext[ext] = files_by_ext.get(ext, 0) + 1

                # Track config files
                if item.name in config_targets:
                    config_files.append(item.name)

        # Format output
        outstack = ["Project Structure:\n"]

        # Directory tree - show full hierarchy with proper nesting
        if dirs:
            outstack.append(".")
            # Sort directories by path to ensure proper ordering
            dir_paths = sorted([Path(d) for d in dirs])
            for dir_path in dir_paths:
                # Calculate proper indentation based on depth
                depth = len(dir_path.parts)
                indent = "\t" * depth
                # Show just the directory name at each level
                outstack.append(f"{indent}├── {dir_path.name}/")
        else:
            outstack.append("\t(no sub-directories)")

        # File types summary
        outstack.append("\nFile types:")
        if files_by_ext:
            for ext, count in sorted(
                files_by_ext.items(),
                key=lambda x: x[1],
                reverse=True,
            )[:10]:
                outstack.append(f"\t- {ext}: {count} files")
        else:
            outstack.append("\t(no files)")

        # Configuration files
        if config_files:
            outstack.append("\nConfiguration:")
            for cf in sorted(config_files):
                outstack.append(f"\t- {cf}")

        result = "\n".join(outstack)
        _logger.info("Generated project structure overview")

        return result

    # pylint: disable=broad-except
    except Exception as e:
        _logger.error("Error getting project structure: %s", e)
        return f"Error getting project structure: {str(e)}"


async def get_solidity_files() -> str:
    """
    List all Solidity contract files in the workspace.

    Specifically finds and lists .sol files, which are the primary files for
    ETH-based smart contracts i.e. our target for security analysis.

    Returns:
        str: Formatted text containing:
            - List of all .sol files with paths
            - Contract count
            - Organization by directory

    Example output:
        Solidity Contracts:

        contracts/tokens/:
          - Token.sol
          - ERC20.sol

        contracts/governance/:
          - Governor.sol

        Total: 3 contracts
    """
    try:
        work_dir = Path(conf.get("workdir", Path.cwd().as_posix()))
        if not work_dir.exists():
            return f"Error: Workspace directory does not exist: {work_dir}"

        # Find all .sol files
        sol_files = sorted(work_dir.rglob("*.sol"))
        if not sol_files:
            return "No Solidity contracts found in the workspace."

        # Group by directory
        by_dir = {}
        for sol_file in sol_files:
            rpath = sol_file.relative_to(work_dir)
            dir_path = rpath.parent
            if dir_path not in by_dir:
                by_dir[dir_path] = []
            by_dir[dir_path].append(rpath.name)

        # Format output with full directory paths
        outstack = ["Solidity Contracts:\n"]
        for dir_path in sorted(by_dir.keys()):
            if dir_path == Path("."):
                outstack.append("(root):")
            else:
                # Show full nested directory path
                outstack.append(f"{dir_path.as_posix()}/:")

            # Indent files based on directory depth
            depth = len(dir_path.parts) if dir_path != Path(".") else 0
            indent = "\t" * (depth + 1)
            for filename in sorted(by_dir[dir_path]):
                outstack.append(f"{indent}- {filename}")
            outstack.append("")
        outstack.append(f"Total: {len(sol_files)} contracts")

        result = "\n".join(outstack)
        _logger.info("Found %d Solidity contracts", len(sol_files))

        return result

    # pylint: disable=broad-except
    except Exception as e:
        _logger.error("Error listing Solidity contracts: %s", e)
        return f"Error listing Solidity contracts: {str(e)}"
