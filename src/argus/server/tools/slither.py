"""Controller for Slither tool execution within Argus framework."""

from typing import Any, Dict, Optional
from pathlib import Path
import logging
import asyncio

from argus.core import conf, docker as argus_docker
from argus import utils

_logger = logging.getLogger("argus.console")


async def slither(
    command: Optional[str] = None,
    args: Optional[list] = None,
    kwargs: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Execute the Slither tool detector.

    Args:
        command: Slither command to execute (e.g., "slither")
        args: List of arguments for the slither command (e.g., ["file.sol"])
        kwargs: Additional keyword arguments (currently unused)
    Returns:
        Result of the tool execution as a dictionary.
    """
    if command is None:
        command = "slither"
    if args is None:
        args = []
    if kwargs is None:
        kwargs = {}

    try:
        # Check Docker availability
        if not argus_docker.docker_available():
            return {
                "exit_code": -1,
                "container_exit_code": None,
                "stdout": "",
                "stderr": "Docker daemon is not available.",
            }

        # Prepare arguments
        project_root = Path(conf.get("workdir", Path.cwd().as_posix()))
        slither_conf = conf.get("server.tools.slither", {})
        image = utils.conf_get(
            slither_conf,
            "docker.image",
            "trailofbits/eth-security-toolbox:latest",
        )
        network_mode = utils.conf_get(slither_conf, "docker.network_mode", "bridge")
        remove_container = utils.conf_get(
            slither_conf,
            "docker.remove_containers",
            True,
        )
        timeout = utils.conf_get(slither_conf, "timeout", 300)

        # Create full command
        fullcmd = [command] + args
        _logger.info("Slither command: %s", " ".join(fullcmd))

        # Pull image, default behavior is to only pull if-not-present
        pull_success, pull_error = argus_docker.pull_image(image)
        if not pull_success:
            return {
                "exit_code": -1,
                "container_exit_code": None,
                "stdout": "Failed to pull Docker image",
                "stderr": pull_error,
            }

        # Run Docker executor
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(
            None,
            argus_docker.run_docker,
            image,
            fullcmd,
            project_root,
            timeout,
            network_mode,
            remove_container,
        )

        stdout = utils.str2dict(res["stdout"]) if res["stdout"] else {}
        stderr = utils.str2dict(res["stderr"]) if res["stderr"] else {}
        return {
            "exit_code": res["exit_code"],
            "container_exit_code": res["container_exit_code"],
            "stdout": stdout,
            "stderr": stderr,
        }

    # pylint: disable=broad-except
    except Exception as e:
        return {
            "exit_code": -1,
            "container_exit_code": None,
            "stdout": "",
            "stderr": f"Unexpected error during Docker execution: {str(e)}",
        }
