"""Helper functions for file operations and data processing."""

from pathlib import Path
from typing import List, Dict
import json


def find_solidity_files(contracts_dir: str) -> List[Path]:
    """
    Find all .sol files in contracts directory.

    Args:
        contracts_dir: Path to contracts directory

    Returns:
        List of Path objects to .sol files
    """
    contracts_path = Path(contracts_dir)
    if not contracts_path.exists():
        raise FileNotFoundError(f"Contracts directory not found: {contracts_dir}")

    return list(contracts_path.rglob("*.sol"))


def find_documentation_files(project_root: str) -> List[Path]:
    """
    Recursively find all .md files in project.

    Args:
        project_root: Path to project root

    Returns:
        List of Path objects to .md files
    """
    root = Path(project_root)
    md_files = []

    # Exclude common directories
    exclude_dirs = {'node_modules', 'test', 'artifacts', 'cache', '.git'}

    for md_file in root.rglob("*.md"):
        if not any(excluded in md_file.parts for excluded in exclude_dirs):
            md_files.append(md_file)

    return md_files


def read_file_safe(file_path: Path) -> str:
    """
    Safely read file content with error handling.

    Args:
        file_path: Path to file

    Returns:
        File content as string, or empty string if error
    """
    try:
        return file_path.read_text(encoding='utf-8')
    except Exception as e:
        print(f"Warning: Could not read {file_path}: {e}")
        return ""


def create_output_directory(output_dir: str):
    """
    Create output directory structure.

    Args:
        output_dir: Path to output directory
    """
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    (output_path / "tests").mkdir(exist_ok=True)


def append_to_file(file_path: str, content: str):
    """
    Append content to file, creating if doesn't exist.

    Args:
        file_path: Path to file
        content: Content to append
    """
    with open(file_path, 'a', encoding='utf-8') as f:
        f.write(content)
        f.write("\n\n")


def write_file(file_path: str, content: str):
    """
    Write content to file, overwriting if exists.

    Args:
        file_path: Path to file
        content: Content to write
    """
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)


def parse_json_response(response: str) -> Dict:
    """
    Parse JSON from LLM response, handling markdown code blocks.

    Args:
        response: LLM response text

    Returns:
        Parsed JSON as dict
    """
    # Remove markdown code blocks if present
    response = response.strip()
    if response.startswith("```json"):
        response = response[7:]
    if response.startswith("```"):
        response = response[3:]
    if response.endswith("```"):
        response = response[:-3]

    response = response.strip()

    try:
        return json.loads(response)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        print(f"Response was: {response[:200]}...")
        return {}


def validate_hardhat_project(project_path: str) -> bool:
    """
    Validate that project is a valid Hardhat project.

    Args:
        project_path: Path to project root

    Returns:
        True if valid Hardhat project, False otherwise
    """
    root = Path(project_path)

    required_files = [
        root / "hardhat.config.js",
        root / "contracts"
    ]

    for required in required_files:
        if not required.exists():
            print(f"Missing required file/directory: {required}")
            return False

    return True


def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to human-readable string.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted string like "5m 32s"
    """
    minutes = int(seconds // 60)
    secs = int(seconds % 60)

    if minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"