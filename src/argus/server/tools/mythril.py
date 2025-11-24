"""Controller for Mythril tool execution within Argus framework."""

from typing import Any, Dict, Optional
from pathlib import Path
import logging
import asyncio

from argus.core import conf, docker as argus_docker
from argus import utils

_logger = logging.getLogger("argus.console")


async def mythril(
    command: Optional[str] = None,
    args: Optional[list] = None,
    kwargs: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Execute the Mythril tool detector.

    Args:
        command: Mythril command to execute (e.g., "myth")
        args: List of arguments for the mythril command (e.g., ["analyze", "file.sol"])
        kwargs: Additional keyword arguments
    Returns:
        Result of the tool execution as a dictionary.
    """
    if command is None:
        command = "myth"
    if args is None:
        args = []
    if kwargs is None:
        kwargs = {}

    try:
        # Check for Docker availability
        if not argus_docker.docker_available():
            return {
                "exit_code": -1,
                "container_exit_code": None,
                "stdout": "",
                "stderr": "Docker daemon is not available.",
            }

        # Prepare arguments
        project_root = Path(conf.get("workdir", Path.cwd().as_posix()))
        myth_conf = conf.get("server.tools.mythril", {})
        image = utils.conf_get(myth_conf, "docker.image", "mythril/myth:latest")
        network_mode = utils.conf_get(myth_conf, "docker.network_mode", "bridge")
        remove_container = utils.conf_get(
            myth_conf,
            "docker.remove_containers",
            True,
        )
        timeout = utils.conf_get(myth_conf, "timeout", 300)
        outform = utils.conf_get(myth_conf, "outform", "json")

        # Create full command
        fullcmd = [command] + args
        if ("-o" not in fullcmd) and ("--outform" not in fullcmd):
            fullcmd += ["-o", outform]
        _logger.info("Mythril command: %s", " ".join(fullcmd))

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
