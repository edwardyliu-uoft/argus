"""
Docker Runner for Static Analysis Tools

Provides utilities for running Slither and Mythril in Docker containers.
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
import docker
from docker.errors import DockerException, ImageNotFound, APIError

# Set up logging
logger = logging.getLogger(__name__)


def check_docker_available() -> Tuple[bool, Optional[str]]:
    """
    Check if Docker daemon is available.

    Returns:
        Tuple of (is_available, error_message)
    """
    try:
        client = docker.from_env()
        client.ping()
        logger.debug("Docker daemon is available and responding")
        return True, None
    except DockerException as e:
        error_msg = f"Docker daemon not running: {str(e)}"
        logger.error(error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"Docker error: {str(e)}"
        logger.error(error_msg)
        return False, error_msg


def pull_image_if_needed(image: str, pull_policy: str) -> Tuple[bool, Optional[str]]:
    """
    Pull Docker image based on pull policy.

    Args:
        image: Docker image name (e.g., "trailofbits/eth-security-toolbox:latest")
        pull_policy: "always", "if-not-present", or "never"

    Returns:
        Tuple of (success, error_message)
    """
    try:
        client = docker.from_env()

        if pull_policy == "never":
            # Check if image exists locally
            try:
                client.images.get(image)
                logger.debug(f"Image '{image}' found locally")
                return True, None
            except ImageNotFound:
                error_msg = f"Image '{image}' not found and pull_policy is 'never'"
                logger.error(error_msg)
                return False, error_msg

        elif pull_policy == "if-not-present":
            # Only pull if not present
            try:
                client.images.get(image)
                logger.debug(f"Image '{image}' already present locally")
                return True, None  # Image exists, no need to pull
            except ImageNotFound:
                logger.info(f"Pulling Docker image: {image}...")
                client.images.pull(image)
                logger.info(f"Image '{image}' pulled successfully")
                return True, None

        elif pull_policy == "always":
            # Always pull latest
            logger.info(f"Pulling Docker image: {image}...")
            client.images.pull(image)
            logger.info(f"Image '{image}' pulled successfully")
            return True, None

        else:
            error_msg = f"Invalid pull_policy: {pull_policy}"
            logger.error(error_msg)
            return False, error_msg

    except ImageNotFound:
        error_msg = f"Image '{image}' not found in registry"
        logger.error(error_msg)
        return False, error_msg
    except APIError as e:
        error_msg = f"Failed to pull image: {str(e)}"
        logger.error(error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"Docker error: {str(e)}"
        logger.error(error_msg)
        return False, error_msg


def get_project_root(file_path: str) -> Path:
    """
    Find the project root directory for a contract file.

    Looks for common project indicators (package.json, hardhat.config.js, etc.)
    going up from the file's directory.

    Args:
        file_path: Absolute path to contract file

    Returns:
        Path to project root directory
    """
    current = Path(file_path).parent

    # Common project root indicators
    indicators = [
        "hardhat.config.js",
        "hardhat.config.ts",
        "package.json",
        "foundry.toml",
        "truffle-config.js",
        "contracts"  # Directory name
    ]

    # Walk up the directory tree
    max_depth = 10  # Prevent infinite loop
    for _ in range(max_depth):
        # Check for indicators
        for indicator in indicators:
            if (current / indicator).exists():
                return current

        # Move up one level
        parent = current.parent
        if parent == current:  # Reached root
            break
        current = parent

    # If no project root found, use the contracts directory parent
    return Path(file_path).parent


def run_docker_command(
    image: str,
    command: List[str],
    project_root: Path,
    file_path: str,
    timeout: int,
    network_mode: str = "none",
    remove_container: bool = True
) -> Dict[str, Any]:
    """
    Run a command in a Docker container.

    Args:
        image: Docker image name
        command: Command to run (list of strings)
        project_root: Project root directory to mount
        file_path: Absolute path to target file (for relative path calculation)
        timeout: Execution timeout in seconds
        network_mode: Docker network mode (default: "none" for security)
        remove_container: Whether to remove container after execution

    Returns:
        Dict with:
            - success (bool): Whether execution succeeded
            - output (str): stdout from container
            - stderr (str): stderr from container
            - exit_code (int): Container exit code
    """
    try:
        client = docker.from_env()

        # Calculate relative path from project root to file
        file_path_obj = Path(file_path)
        try:
            relative_path = file_path_obj.relative_to(project_root)
        except ValueError:
            # File is not under project root, use parent directory
            project_root = file_path_obj.parent
            relative_path = file_path_obj.name

        # Container path
        container_path = f"/project/{relative_path}"

        # Replace the file path in command with container path
        # Assumes the file path is the last argument or first non-flag argument
        updated_command = []
        for arg in command:
            # Check if this arg is a file path (not a flag like '--json' or '-')
            try:
                if Path(arg).exists() and Path(arg).resolve() == file_path_obj.resolve():
                    updated_command.append(container_path)
                else:
                    updated_command.append(arg)
            except (OSError, ValueError):
                # Not a valid path, keep as-is (likely a flag)
                updated_command.append(arg)

        # Mount project root as /project (read-only)
        volumes = {
            str(project_root.resolve()): {
                'bind': '/project',
                'mode': 'ro'  # Read-only for security
            }
        }

        # Run container
        container = client.containers.run(
            image,
            command=updated_command,
            volumes=volumes,
            working_dir='/project',
            network_mode=network_mode,
            detach=True,
            remove=False  # We'll remove manually after getting logs
        )

        try:
            # Wait for container to finish with timeout
            logger.debug(f"Waiting for container to finish (timeout: {timeout}s)")
            result = container.wait(timeout=timeout)

            # Get logs
            stdout = container.logs(stdout=True, stderr=False).decode('utf-8', errors='ignore')
            stderr = container.logs(stdout=False, stderr=True).decode('utf-8', errors='ignore')

            exit_code = result.get('StatusCode', -1)

            logger.debug(f"Container exited with code: {exit_code}")

            return {
                "success": exit_code == 0,
                "output": stdout,
                "stderr": stderr,
                "exit_code": exit_code
            }

        except Exception as timeout_error:
            # Handle timeout or other errors during container execution
            logger.error(f"Container execution error: {str(timeout_error)}")
            # Try to get partial logs
            try:
                stdout = container.logs(stdout=True, stderr=False).decode('utf-8', errors='ignore')
                stderr = container.logs(stdout=False, stderr=True).decode('utf-8', errors='ignore')
            except Exception:
                stdout = ""
                stderr = f"Container timeout after {timeout}s: {str(timeout_error)}"

            return {
                "success": False,
                "output": stdout,
                "stderr": stderr,
                "exit_code": -1
            }

        finally:
            # Clean up container
            if remove_container:
                try:
                    container.remove(force=True)
                    logger.debug("Container removed successfully")
                except Exception as cleanup_error:
                    logger.warning(f"Failed to remove container: {str(cleanup_error)}")

    except docker.errors.ContainerError as e:
        logger.error(f"Container error: {str(e)}")
        return {
            "success": False,
            "output": "",
            "stderr": str(e),
            "exit_code": e.exit_status
        }

    except APIError as e:
        logger.error(f"Docker API error: {str(e)}")
        return {
            "success": False,
            "output": "",
            "stderr": f"Docker API error: {str(e)}",
            "exit_code": -1
        }

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return {
            "success": False,
            "output": "",
            "stderr": f"Unexpected error: {str(e)}",
            "exit_code": -1
        }