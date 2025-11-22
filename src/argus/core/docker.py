"""Argus Docker management toolkit.

Provides utilities for operating Docker containers.
"""

from typing import Dict, Any, Optional, Tuple, List, Union
from pathlib import Path
import logging

import docker
from docker.errors import DockerException, ImageNotFound, APIError


logger = logging.getLogger("argus.console")


def docker_available() -> bool:
    """
    If Docker daemon is available.

    Returns:
        bool: True if Docker is available, False otherwise
    """
    try:
        client = docker.from_env()
        client.ping()
        logger.debug("Docker daemon is available and responding.")
        return True

    except DockerException as e:
        logger.error("Docker daemon not running: %s", e)
        return False

    # pylint: disable=broad-except
    except Exception as e:
        logger.error("Docker error: %s", e)
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
                    logger.debug("Image '%s' present locally", image)
                    return True, None
                except ImageNotFound:
                    error_msg = "Image '%s' not found; pull_policy is 'never'."
                    logger.error(error_msg, image)
                    return False, error_msg
            case "if-not-present":
                # Only pull if not present
                try:
                    client.images.get(image)
                    logger.debug("Image '%s' present locally", image)
                    return True, None  # Image exists, no need to pull
                except ImageNotFound:
                    logger.info("Pulling Docker image: %s", image)
                    client.images.pull(image)
                    logger.info("Image '%s' pulled successfully", image)
                    return True, None
            case "always":
                # Always pull latest
                logger.info("Pulling Docker image: %s", image)
                client.images.pull(image)
                logger.info("Image '%s' pulled successfully", image)
                return True, None

            case _:
                error_msg = f"Unrecognized pull_policy: {pull_policy}"
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

    # pylint: disable=broad-except
    except Exception as e:
        error_msg = f"Docker error: {str(e)}"
        logger.error(error_msg)
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
        project_root: Project root directory to mount
        timeout: Execution timeout in seconds
        network_mode: Docker network mode (default: "none" for security)
        remove_container: Whether to remove container after execution

    Returns:
        Dict with:
            - success (bool): Whether execution succeeded
            - stdout (str): stdout from container
            - stderr (str): stderr from container
            - exit_code (int): Container exit code
    """
    try:
        client = docker.from_env()

        # Mount project root as /project (read-only)
        volumes = {
            str(project_root.resolve()): {
                "bind": "/project",
                "mode": "ro",  # Read-only for security
            }
        }

        # Run container with command as-is
        container = client.containers.run(
            image,
            command=command,
            volumes=volumes,
            working_dir="/project",
            network_mode=network_mode,
            platform='linux/amd64',  # Force x86_64 platform for compatibility
            detach=True,
            remove=False,  # will remove manually after getting logs
        )

        try:
            # Wait for container to finish with timeout
            logger.debug("Waiting for container to finish (timeout: %s)", timeout)
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
            logger.debug("Container exited with code: %s", exit_code)

            return {
                "success": exit_code == 0,
                "stdout": stdout,
                "stderr": stderr,
                "exit_code": exit_code,
            }

        # pylint: disable=broad-except
        except Exception as e:
            # Handle timeout or other errors during container execution
            logger.error("Container execution error: %s", e)
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
                "success": False,
                "stdout": stdout,
                "stderr": stderr,
                "exit_code": -1,
            }

        finally:
            # Clean up container
            if remove_container:
                try:
                    container.remove(force=True)
                    logger.debug("Container removed successfully.")
                except Exception as e:
                    logger.warning("Failed to remove container: %s", e)

    except docker.errors.ContainerError as e:
        logger.error("Container error: %s", e)
        return {
            "success": False,
            "stdout": "",
            "stderr": str(e),
            "exit_code": e.exit_status,
        }

    except APIError as e:
        logger.error("Docker API error: %s", e)
        return {
            "success": False,
            "stdout": "",
            "stderr": f"Docker API error: {str(e)}",
            "exit_code": -1,
        }

    # pylint: disable=broad-except
    except Exception as e:
        logger.error("Unexpected error: %s", e)
        return {
            "success": False,
            "stdout": "",
            "stderr": f"Unexpected error: {str(e)}",
            "exit_code": -1,
        }
