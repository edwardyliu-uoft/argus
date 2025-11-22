import asyncio
import json
import os
from pathlib import Path

# internal imports
from ..controller import BaseController
from argus.core import docker as argus_docker
# global config object
from argus.core.config import conf

class SlitherController(BaseController):
    """Controller for the Slither tool."""

    def __init__(self):
        """Initialize the SlitherController with ArgusConfig config."""
        super().__init__()


    async def execute(self, command: str = "slither", args: list = []) -> str:
        """
        Execute the Slither tool's detector.

        Args:
            command: slither command to execute. Default is "slither"
            args: List of arguments for the command with the first argument being the target file or directory. 
                If the target is not provided, it defaults to the project root.
        Returns:
            Result of the tool execution as a string
        """
        try:
        # Check Docker availability
            if not argus_docker.docker_available():
                return {
                    "success": False,
                    "output": "",
                    "error": {
                        "type": "docker_unavailable",
                        "raw_output": "Docker daemon not running. Start Docker daemon."
                    }
                }
            image = conf.get("tools.slither.docker.image", "trailofbits/eth-security-toolbox:latest")
            # Slither needs network access to download Solidity compiler
            network_mode = conf.get("tools.slither.docker.network_mode", "bridge")
            remove_container = conf.get("tools.slither.docker.remove_containers", True)
            timeout = conf.get("tools.slither.timeout", 300)
            output_format = conf.get("tools.slither.format", "json")
            project_root = conf.get("workdir", ".")

            # Extract and prepare target file path
            target_file_arg = args[0] if args else project_root

            # Convert to absolute path
            if not os.path.isabs(target_file_arg):
                target_file = os.path.abspath(os.path.join(project_root, target_file_arg))
            else:
                target_file = target_file_arg

            # Build command as list - use absolute path so run_docker can detect and replace it
            full_command = [command, target_file]
            if len(args) > 1:
                full_command.extend(args[1:])

            # Add output format if not already present
            if output_format == "json" and "--json" not in full_command:
                full_command.extend(["--json", "-"])
            
            # pull_image, default behavior is only to pull if not present
            pull_success, pull_error = argus_docker.pull_image(image)

            if not pull_success:
                return {
                    "success": False,
                    "output": "",
                    "error": {
                        "type": "docker_image_not_found",
                        "raw_output": f"{pull_error}\nTry: docker pull {image}"
                    }
                }
            loop = asyncio.get_event_loop()
            
            result = await loop.run_in_executor(
                None,
                argus_docker.run_docker,
                image,
                full_command,
                Path(project_root),
                target_file,
                timeout,
                network_mode,
                remove_container
            )

            # Slither may return non-zero exit codes even with valid results
            # Check for valid JSON output first
            if output_format == "json" and result["stdout"].strip():
                try:
                    json.loads(result["stdout"])
                    # Valid JSON output means success regardless of exit code
                    return {
                        "success": True,
                        "output": result["stdout"],
                        "error": None
                    }
                except json.JSONDecodeError:
                    # Invalid JSON, check if there was an error
                    pass

            # If no valid JSON and exit code != 0, check for errors
            if not result["success"]:
                # Check for timeout
                if "timeout" in result["stderr"].lower():
                    return {
                        "success": False,
                        "output": result["stdout"],
                        "error": {
                            "type": "timeout",
                            "raw_output": f"Slither execution timed out after {timeout} seconds"
                        }
                    }

                # Check for compilation errors
                stderr_lower = result["stderr"].lower()
                if "compilation" in stderr_lower:
                    error_type = "compilation_error"
                else:
                    error_type = "docker_container_error"

                return {
                    "success": False,
                    "output": result["stdout"],
                    "error": {
                        "type": error_type,
                        "raw_output": result["stderr"]
                    }
                }

            # Exit code 0 with no JSON
            return {
                "success": True,
                "output": result["stdout"],
                "error": None
            }

        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": {
                    "type": "crash",
                    "raw_output": f"Unexpected error in Docker execution: {str(e)}"
                }
            }
