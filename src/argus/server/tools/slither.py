"""Controller for Slither tool execution within Argus framework.

Slither is a Solidity static analysis framework written in Python 3. It runs a suite of
vulnerability detectors, prints visual information about contract details, and provides
an API to easily write custom analyses. Slither enables developers to find vulnerabilities,
enhance their code comprehension, and quickly prototype custom analyses.

Documentation: https://crytic.github.io/slither/slither.html
"""

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
    Execute Slither static analysis on Solidity smart contracts.

    Slither is a comprehensive Solidity static analyzer that detects vulnerabilities and
    provides detailed contract information. It can analyze individual contracts, entire
    projects, and supports various output formats.

    COMMON USAGE PATTERNS:
    ----------------------
    1. Basic analysis of a single file:
       slither(args=["contract.sol"])

    2. Analyze with specific detectors:
       slither(args=["contract.sol", "--detect", "reentrancy-eth,controlled-delegatecall"])

    3. Exclude certain detectors:
       slither(args=["contract.sol", "--exclude", "naming-convention,solc-version"])

    4. Generate detailed reports:
       slither(args=[".", "--print", "human-summary"])

    5. Filter by severity:
       slither(args=["contract.sol", "--filter-paths", "test/"])

    KEY DETECTORS (use with --detect flag):
    ---------------------------------------
    - reentrancy-eth: Reentrancy vulnerabilities (theft of ethers)
    - reentrancy-no-eth: Reentrancy vulnerabilities (no theft of ethers)
    - controlled-delegatecall: Controlled delegatecall destination
    - suicidal: Functions allowing anyone to destruct the contract
    - uninitialized-state: Uninitialized state variables
    - arbitrary-send: Functions that send ether to arbitrary destinations
    - tx-origin: Dangerous usage of tx.origin
    - timestamp: Dangerous comparisons with block.timestamp
    - locked-ether: Contracts that lock ether

    USEFUL FLAGS:
    -------------
    --json FILE: Export results as JSON to specified file
    --exclude DETECTORS: Comma-separated list of detectors to exclude
    --filter-paths REGEX: Exclude paths matching the regex from analysis
    --solc-remaps REMAPS: Add Solidity remappings (e.g., "@openzeppelin=node_modules/@openzeppelin")
    --solc-args ARGS: Additional arguments for solc compiler
    --print PRINTERS: Print contract information (e.g., human-summary, inheritance-graph)

    Args:
        command: The Slither command to execute. Defaults to "slither" if not specified.
                 Generally should remain as "slither" for standard analysis.

        args: List of command-line arguments to pass to Slither.
              - First argument is typically the target (file path, directory, or ".")
              - Followed by optional flags like --detect, --exclude, --json, etc.
              - Example: ["contract.sol", "--detect", "reentrancy-eth", "--json", "output.json"]
              - Example: [".", "--exclude", "naming-convention"]

        kwargs: Additional keyword arguments. Currently unused but reserved for future
                extensibility (e.g., environment variables, custom configurations).

    Returns:
        Dict[str, Any]: A dictionary containing the execution results with the following keys:
            - exit_code (int): Overall execution status code (-1 for errors, 0+ for tool results)
            - container_exit_code (int|None): Docker container's exit code (None if container didn't start)
            - stdout (dict|str): Parsed JSON output from Slither containing findings and analysis results,
                                or string if parsing failed or empty if no output
            - stderr (dict|str): Parsed JSON error output or string containing error messages

        Slither's stdout typically contains:
            - success (bool): Whether analysis completed successfully
            - error (str|None): Error message if analysis failed
            - results (dict): Detection results organized by severity and detector type
                - detectors (list): List of vulnerability findings, each with:
                    - check (str): Name of the detector that found the issue
                    - impact (str): Severity level (High, Medium, Low, Informational)
                    - confidence (str): Confidence level (High, Medium, Low)
                    - description (str): Human-readable description of the issue
                    - elements (list): Source code elements involved in the issue

    Execution Flow:
        1. Validates Docker daemon availability
        2. Loads configuration for Docker image and execution parameters
        3. Pulls the Slither Docker image (trailofbits/eth-security-toolbox) if needed
        4. Runs Slither in Docker container with project mounted as volume
        5. Parses and returns JSON-formatted results

    Error Handling:
        - Returns exit_code -1 with descriptive stderr for Docker/system errors
        - Slither's own errors (compilation issues, invalid files) are in stdout/stderr
        - Network or timeout errors are caught and returned as stderr messages
    """
    # Set default values for optional parameters
    if command is None:
        command = "slither"  # Default to standard Slither command
    if args is None:
        args = []  # Empty args will prompt Slither to show help
    if kwargs is None:
        kwargs = {}  # Reserved for future use

    try:
        # STEP 1: Verify Docker is running and accessible
        if not argus_docker.docker_available():
            return {
                "exit_code": -1,
                "container_exit_code": None,
                "stdout": "",
                "stderr": "Docker daemon is not available.",
            }

        # STEP 2: Load configuration from Argus config file or use defaults
        # Project root is where contract files are located (mounted as volume in container)
        project_root = Path(conf.get("workdir", Path.cwd().as_posix()))
        slither_conf = conf.get("server.tools.slither", {})

        # Docker image containing Slither and Solidity compiler tools
        image = utils.conf_get(
            slither_conf,
            "docker.image",
            "trailofbits/eth-security-toolbox:latest",
        )
        # Network mode: 'bridge' for isolated, 'host' for network access
        network_mode = utils.conf_get(slither_conf, "docker.network_mode", "bridge")
        # Whether to remove container after execution (cleanup)
        remove_container = utils.conf_get(
            slither_conf,
            "docker.remove_containers",
            True,
        )
        # Maximum seconds to wait for analysis to complete (default 5 minutes)
        timeout = utils.conf_get(slither_conf, "timeout", 300)

        # STEP 3: Build the full command to execute inside container
        fullcmd = [command] + args
        _logger.info("Slither command: %s", " ".join(fullcmd))

        # STEP 4: Ensure Docker image is available locally (pulls if missing)
        # Uses 'if-not-present' policy: only downloads if not in local cache
        pull_success, pull_error = argus_docker.pull_image(image)
        if not pull_success:
            return {
                "exit_code": -1,
                "container_exit_code": None,
                "stdout": "Failed to pull Docker image",
                "stderr": pull_error,
            }

        # STEP 5: Execute Slither in Docker container
        # Runs in executor to avoid blocking the async event loop
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(
            None,  # Use default executor (thread pool)
            argus_docker.run_docker,
            image,
            fullcmd,
            project_root,  # Mounted as /workspace in container
            timeout,
            network_mode,
            remove_container,
        )

        # STEP 6: Parse JSON output from Slither (if valid JSON)
        # Slither typically outputs JSON with 'success', 'error', and 'results' keys
        stdout = utils.str2dict(res["stdout"]) if res["stdout"] else {}
        stderr = utils.str2dict(res["stderr"]) if res["stderr"] else {}

        return {
            "exit_code": res[
                "exit_code"
            ],  # 0 = success, >0 = errors found or execution issues
            "container_exit_code": res["container_exit_code"],
            "stdout": stdout,  # Primary analysis results
            "stderr": stderr,  # Errors, warnings, or diagnostic messages
        }

    # pylint: disable=broad-except
    except Exception as e:
        # Catch-all for unexpected errors (network issues, Docker daemon crashes, etc.)
        return {
            "exit_code": -1,
            "container_exit_code": None,
            "stdout": "",
            "stderr": f"Unexpected error during Docker execution: {str(e)}",
        }
