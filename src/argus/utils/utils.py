"""Helper functions for file operations and data processing."""

from typing import List, Dict, Optional, Union
from pathlib import Path
import logging
import json


_logger = logging.getLogger("argus.console")


def find_project_root(filepath: str) -> Path:
    """
    Find the project root directory for a contract file.

    Looks for common project indicators (package.json, hardhat.config.js, etc.)
    going up from the file's directory.

    Args:
        filepath: Absolute path to contract file

    Returns:
        Path to project root directory
    """
    current = Path(filepath).parent

    # Common project root indicators
    indicators = [
        "hardhat.config.js",
        "hardhat.config.ts",
        "package.json",
        "tsconfig.json",
        "foundry.toml",
        "truffle-config.js",
        "LICENSE",
    ]

    # Walk up the directory tree
    max_depth = 10  # to prevent infinite loop
    for _ in range(max_depth):
        # Check for indicators
        for indicator in indicators:
            if (current / indicator).exists():
                return current

        # Move up one level
        parent = current.parent
        if parent == current:  # reached root
            break
        current = parent

    # If no project root found, use the contracts directory parent
    return Path(filepath).parent


def find_files_with_extension(
    project_root: str,
    extension: str,
    exclude_dirs: Optional[List[str]] = None,
) -> List[Path]:
    """Find all files with a given extension in project root directory,
    excluding specified directories.

    Args:
        project_root: Path to project root
        extension: File extension to search for (e.g. "sol", "md")
        exclude_dirs: Optional list of directory names to exclude from search
    """
    project_path = Path(project_root)
    matched_files = []

    for filepath in project_path.rglob(f"*.{extension}"):
        if exclude_dirs is None or not any(
            excluded in filepath.parts for excluded in exclude_dirs
        ):
            matched_files.append(filepath)

    return matched_files


def read_file(file: str) -> str:
    """Read file content with error handling.

    Args:
        file: Path to file

    Returns:
        File content as string, or empty string if error
    """
    try:
        filepath = Path(file)
        return filepath.read_text(encoding="utf-8")

    # pylint: disable=broad-except
    except Exception as e:
        _logger.warning("Warning: Could not read %s: %s", file, e)
        return ""


def create_directory(directory: str):
    """Create directory.

    Args:
        directory: Path to directory
    """
    dirpath = Path(directory)
    dirpath.mkdir(parents=True, exist_ok=True)


def append_file(file: str, content: str):
    """Append content to file, creating it if doesn't exist.

    Args:
        file: Path to file
        content: Content to append
    """
    with open(file, "a", encoding="utf-8") as f:
        f.write(content)
        f.write("\n\n")


def write_file(file: str, content: str):
    """Write content to file, overwriting it if it exists.

    Args:
        file: Path to file
        content: Content to write
    """
    with open(file, "w", encoding="utf-8") as f:
        f.write(content)


def parse_json_llm(message: str) -> Dict:
    """Parse JSON from LLM response, handling markdown code blocks and malformed responses.

    Args:
        message: LLM message string

    Returns:
        Parsed JSON as dict

    Raises:
        json.JSONDecodeError: If JSON parsing fails after all cleanup attempts
    """
    import re

    # Remove markdown code blocks if present
    message = message.strip()
    if message.startswith("```json"):
        message = message[7:]
    if message.startswith("```"):
        message = message[3:]
    if message.endswith("```"):
        message = message[:-3]

    message = message.strip()

    # Try parsing as-is first
    try:
        return json.loads(message)
    except json.JSONDecodeError as e:
        _logger.warning("Initial JSON parse failed: %s", e)

        # Strategy 1: Extract JSON from text using regex
        # Look for first { to last } (handles text before/after JSON)
        json_match = re.search(r'\{.*\}', message, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                _logger.debug("Regex extraction failed")

        # Strategy 2: Clean up common LLM artifacts
        # Remove common invalid characters between JSON elements
        cleaned = re.sub(r'\}\s*[a-zA-Z]\s*\{', '},{', message)  # Fix: }e{ -> },{
        cleaned = re.sub(r'\]\s*[a-zA-Z]\s*\[', '],[', cleaned)  # Fix: ]e[ -> ],[

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            _logger.debug("Cleaned JSON parse failed")

        # Strategy 3: Try to fix truncated JSON by finding last complete object
        if message.strip().endswith(','):
            # Remove trailing comma
            try:
                return json.loads(message.rstrip(','))
            except json.JSONDecodeError:
                _logger.debug("Trailing comma removal failed")

        # All strategies failed - log full error and raise
        _logger.error("Error parsing JSON from LLM: %s", e)
        _logger.error("Message was: %s", message[:500])
        _logger.error("Full message length: %d characters", len(message))

        # Re-raise the original exception instead of silently returning {}
        raise


def project_is_hardhat(project_root: str) -> bool:
    """Validate if project is a Hardhat project.

    Args:
        project_root: Path to project root

    Returns:
        True if valid Hardhat project, False otherwise
    """
    project_path = Path(project_root)
    possible_files = [
        project_path / "hardhat.config.js",
        project_path / "hardhat.config.ts",
    ]

    for possible_file in possible_files:
        if possible_file.exists():
            return True

    _logger.info("Missing proof of hardhat project: %s", possible_files)
    return False


def format_duration(seconds: float) -> str:
    """Format duration in seconds to a human-readable string.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted string like "5m 32s"
    """
    minutes = int(seconds // 60)
    secs = int(seconds % 60)

    if minutes > 0:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def conf_get(config: dict, key_path: str, default=None):
    """Get configuration value using dot notation.

    Args:
        config: Configuration dictionary
        key_path: Dot notation key path
        default: Default value if key not found

    Returns:
        Configuration value or default

    Example: config.get('llm.model')
    """
    keys = key_path.split(".")
    value = config
    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return default
    return value


def str2dict(candidate: str) -> Union[Dict[str, any], str]:
    """
    Convert input string to dictionary.

    Args:
        candidate: string
    Returns:
        Parsed as dictionary if applicable.
    """
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return candidate
