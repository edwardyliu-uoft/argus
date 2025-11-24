"""Argus Docker management toolkit.

Provides utilities for operating Docker containers.
"""

from typing import Dict, Any, Optional, Tuple, List, Union
from pathlib import Path
import logging

import docker
from docker.errors import DockerException, ImageNotFound, APIError


_logger = logging.getLogger("argus.console")


def docker_available() -> bool:
    """
    If Docker daemon is available.

    Returns:
        bool: True if Docker is available, False otherwise
    """
    try:
        client = docker.from_env()
        client.ping()
        _logger.debug("Docker daemon is available and responding.")
        return True

    except DockerException as e:
        _logger.error("Docker daemon not running: %s", e)
        return False

    # pylint: disable=broad-except
    except Exception as e:
        _logger.error("Docker error: %s", e)
        return False


def pull_image(
    image: str,
    pull_policy: str = "if-not-present",
) -> Tuple[bool, Optional[str]]:
    """Pull Docker image according to the pull policy.

    Args:
        image: Docker image name (e.g. "trailofbits/eth-security-toolbox:latest")
        pull_policy: "always", "if-not-present", or "never"

    Returns:
        Tuple of (success, error_message)
    """
    try:
        client = docker.from_env()
        match pull_policy:
            case "never":
                # Check if image exists locally
                try:
                    client.images.get(image)
                    _logger.debug("Image '%s' present locally", image)
                    return True, None
                except ImageNotFound:
                    error_msg = "Image '%s' not found; pull_policy is 'never'."
                    _logger.error(error_msg, image)
                    return False, error_msg
            case "if-not-present":
                # Only pull if not present
                try:
                    client.images.get(image)
                    _logger.debug("Image '%s' present locally", image)
                    return True, None  # Image exists, no need to pull
                except ImageNotFound:
                    _logger.info("Pulling Docker image: %s", image)
                    client.images.pull(image)
                    _logger.info("Image '%s' pulled successfully", image)
                    return True, None
            case "always":
                # Always pull latest
                _logger.info("Pulling Docker image: %s", image)
                client.images.pull(image)
                _logger.info("Image '%s' pulled successfully", image)
                return True, None

            case _:
                error_msg = f"Unrecognized pull_policy: {pull_policy}"
                _logger.error(error_msg)
                return False, error_msg

    except ImageNotFound:
        error_msg = f"Image '{image}' not found in registry"
        _logger.error(error_msg)
        return False, error_msg

    except APIError as e:
        error_msg = f"Failed to pull image: {str(e)}"
        _logger.error(error_msg)
        return False, error_msg

    # pylint: disable=broad-except
    except Exception as e:
        error_msg = f"Docker error: {str(e)}"
        _logger.error(error_msg)
        return False, error_msg


def run_docker(
    image: str,
    command: Optional[Union[str, List[str]]],
    project_root: Path,
    timeout: int,
    network_mode: str = "none",
    remove_container: bool = True,
) -> Dict[str, Any]:
    """
    Run a command in a Docker container.

    Args:
        image: Docker image name
        command: Command to run i.e. str, list of strings, None
                 Paths in command should be relative to project_root
        project_root: Project root directory to mount at /project
        timeout: Execution timeout in seconds
        network_mode: Docker network mode (default: "none" for security)
        remove_container: Whether to remove container after execution

    Returns:
        Dict with:
            - exit_code (int): 0 for success, -1 for errors
            - container_exit_code (int): Container exit code
            - stdout (str): stdout from container
            - stderr (str): stderr from container
    """
    try:
        client = docker.from_env()

        # Mount project root as /project (read-write to allow tools to create temp files)
        volumes = {
            str(project_root.resolve()): {
                "bind": "/project",
                "mode": "rw",  # Read-write to allow tools to create temp files
            }
        }

        # Run container with command containing relative paths
        container = client.containers.run(
            image,
            command=command,
            volumes=volumes,
            working_dir="/project",
            network_mode=network_mode,
            platform="linux/amd64",  # Force x86_64 platform for compatibility
            detach=True,
            remove=False,  # will remove manually after getting logs
        )

        try:
            # Wait for container to finish with timeout
            _logger.debug("Waiting for container to finish (timeout: %s)", timeout)
            res = container.wait(timeout=timeout)

            # Fetch logs
            stdout = container.logs(stdout=True, stderr=False).decode(
                "utf-8",
                errors="ignore",
            )
            stderr = container.logs(stdout=False, stderr=True).decode(
                "utf-8",
                errors="ignore",
            )

            exit_code = res.get("StatusCode", -1)
            _logger.debug("Container exited with code: %s", exit_code)

            return {
                "exit_code": 0,
                "container_exit_code": exit_code,
                "stdout": stdout,
                "stderr": stderr,
            }

        # pylint: disable=broad-except
        except Exception as e:
            # Handle timeout or other errors during container execution
            _logger.error("Container execution error: %s", e)
            # Try to get partial logs
            try:
                stdout = container.logs(stdout=True, stderr=False).decode(
                    "utf-8",
                    errors="ignore",
                )
                stderr = container.logs(stdout=False, stderr=True).decode(
                    "utf-8",
                    errors="ignore",
                )
            except Exception:
                stdout = ""
                stderr = f"Container timeout after {timeout} seconds."

            return {
                "exit_code": -1,
                "container_exit_code": None,
                "stdout": stdout,
                "stderr": stderr,
            }

        finally:
            # Clean up container
            if remove_container:
                try:
                    container.remove(force=True)
                    _logger.debug("Container removed successfully.")
                except Exception as e:
                    _logger.warning("Failed to remove container: %s", e)

    except docker.errors.ContainerError as e:
        _logger.error("Container error: %s", e)
        return {
            "exit_code": -1,
            "container_exit_code": e.exit_status,
            "stdout": "",
            "stderr": f"Docker Container error: {str(e)}",
        }

    except APIError as e:
        _logger.error("Docker API error: %s", e)
        return {
            "exit_code": -1,
            "container_exit_code": None,
            "stdout": "",
            "stderr": f"Docker API error: {str(e)}",
        }

    # pylint: disable=broad-except
    except Exception as e:
        _logger.error("Unexpected error: %s", e)
        return {
            "exit_code": -1,
            "container_exit_code": None,
            "stdout": "",
            "stderr": f"Unexpected error: {str(e)}",
        }
