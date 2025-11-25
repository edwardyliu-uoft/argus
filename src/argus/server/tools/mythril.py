"""Controller for Mythril tool execution within Argus framework.

Mythril is a security analysis tool for EVM bytecode. It detects security vulnerabilities
in smart contracts built for Ethereum, Hedera, Quorum, Vechain, Roostock, Tron and other
EVM-compatible blockchains. It uses symbolic execution, SMT solving and taint analysis to
detect a variety of security vulnerabilities.

Documentation: https://mythril-classic.readthedocs.io/en/master/index.html
"""

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
    Execute Mythril symbolic analysis on Ethereum smart contracts.

    Mythril performs deep security analysis using symbolic execution and constraint solving
    to detect vulnerabilities in EVM bytecode. It can analyze Solidity source code, bytecode,
    or contracts deployed on-chain. Mythril is particularly effective at finding complex
    vulnerabilities that require reasoning about program state and execution paths.

    COMMON USAGE PATTERNS:
    ----------------------
    1. Analyze a Solidity contract:
       mythril(args=["analyze", "contract.sol"])

    2. Analyze deployed contract by address (requires RPC connection):
       mythril(args=["analyze", "-a", "0x1234..."])

    3. Analyze bytecode directly:
       mythril(args=["analyze", "-c", "0x6060604052..."])

    4. Quick analysis with timeout:
       mythril(args=["analyze", "contract.sol", "--execution-timeout", "300"])

    5. Analyze specific functions:
       mythril(args=["analyze", "contract.sol", "--transaction-count", "2"])

    SUBCOMMANDS:
    ------------
    analyze: Perform security analysis (most common)
    disassemble: Disassemble bytecode to opcodes
    read-storage: Read storage slots from deployed contracts
    function-to-hash: Generate function signature hashes
    hash-to-address: Convert hashes to addresses

    KEY VULNERABILITY DETECTORS:
    ----------------------------
    Mythril automatically checks for:
    - Integer overflows and underflows
    - Reentrancy vulnerabilities
    - Unprotected selfdestruct instructions
    - Unprotected Ether withdrawal
    - Delegatecall to untrusted callee
    - State access after external call
    - Dependence on predictable variables (block.timestamp, block.number)
    - Transaction order dependence
    - Assert violations
    - Use of deprecated functions
    - Unchecked return values

    USEFUL FLAGS FOR 'analyze' SUBCOMMAND:
    --------------------------------------
    -a, --address ADDRESS: Analyze contract at given on-chain address
    -c, --code BYTECODE: Analyze raw bytecode string
    --max-depth N: Maximum recursion depth (default: 22)
    --execution-timeout SECS: Timeout for symbolic execution (default: 86400)
    --transaction-count N: Maximum transactions to analyze (default: 2)
    --modules MODULES: Comma-separated list of modules to run (e.g., "ether_thief,suicide")
    --solc-args ARGS: Pass arguments to solc compiler
    --solv VERSION: Specify Solidity compiler version
    -o, --outform FORMAT: Output format (text, json, jsonv2, markdown) - default: json

    OUTPUT FORMATS:
    ---------------
    - json: Original JSON format with issues array
    - jsonv2: Enhanced JSON with more detailed execution trace
    - text: Human-readable text output
    - markdown: Formatted markdown for documentation

    Args:
        command: The Mythril command to execute. Defaults to "myth" if not specified.
                 This is the base command; actual operations are specified in args.
                 Should typically remain as "myth" for standard usage.

        args: List of command-line arguments to pass to Mythril.
              - First argument should be the subcommand (e.g., "analyze", "disassemble")
              - For "analyze": follow with target (file path, -a for address, -c for bytecode)
              - Additional flags control analysis behavior, depth, timeout, output format
              - Example: ["analyze", "contract.sol", "--max-depth", "12"]
              - Example: ["analyze", "-a", "0x1234...", "-o", "json"]
              - Example: ["disassemble", "-c", "0x6060..."]

        kwargs: Additional keyword arguments. Currently unused but reserved for future
                extensibility (e.g., custom RPC endpoints, environment variables).

    Returns:
        Dict[str, Any]: A dictionary containing the execution results with the following keys:
            - exit_code (int): Overall execution status code (-1 for errors, 0+ for tool results)
            - container_exit_code (int|None): Docker container's exit code (None if container didn't start)
            - stdout (dict|str): Parsed JSON output from Mythril containing vulnerability findings,
                                or string if parsing failed or empty if no output
            - stderr (dict|str): Parsed JSON error output or string containing error messages

        Mythril's JSON output typically contains:
            - success (bool): Whether analysis completed without critical errors
            - error (str|None): Error message if analysis failed
            - issues (list): List of detected vulnerabilities, each with:
                - title (str): Short title of the issue
                - swcID (str): Smart Contract Weakness Classification ID
                - swcTitle (str): Human-readable weakness name
                - description (str): Detailed description of the vulnerability
                - severity (str): High, Medium, or Low
                - address (int): EVM bytecode instruction address
                - sourceMap (str): Mapping to source code location
                - code (str): Relevant code snippet
                - tx_sequence (dict): Transaction trace showing how to trigger the issue

        Note: The function automatically adds "-o json" to the command if no output
              format is specified, ensuring machine-readable output by default.

    Execution Flow:
        1. Validates Docker daemon availability
        2. Loads configuration for Docker image and execution parameters
        3. Ensures JSON output format for parseable results (unless explicitly overridden)
        4. Pulls the Mythril Docker image (mythril/myth) if needed
        5. Runs Mythril in Docker container with project mounted as volume
        6. Parses and returns JSON-formatted results

    Error Handling:
        - Returns exit_code -1 with descriptive stderr for Docker/system errors
        - Mythril's own errors (compilation issues, solver timeouts) are in stdout/stderr
        - Symbolic execution timeouts may result in partial results with timeout warnings
        - Network or Docker errors are caught and returned as stderr messages

    Performance Considerations:
        - Symbolic execution can be time-intensive; default timeout is 300s (configurable)
        - --max-depth and --transaction-count greatly affect analysis time
        - Complex contracts may require increased timeout values
        - Consider using --quick-timeout for faster but less thorough analysis
    """
    # Set default values for optional parameters
    if command is None:
        command = "myth"  # Default to standard Mythril command
    if args is None:
        args = []  # Empty args will prompt Mythril to show help
    if kwargs is None:
        kwargs = {}  # Reserved for future use (e.g., RPC endpoints, env vars)

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
        myth_conf = conf.get("server.tools.mythril", {})

        # Docker image containing Mythril symbolic execution engine
        image = utils.conf_get(myth_conf, "docker.image", "mythril/myth:latest")
        platform = utils.conf_get(myth_conf, "docker.platform", None)
        pull_policy = utils.conf_get(myth_conf, "docker.pull_policy", "if-not-present")
        # Network mode: 'bridge' for isolated, 'host' to access blockchain RPC endpoints
        network_mode = utils.conf_get(myth_conf, "docker.network_mode", "bridge")
        # Whether to remove container after execution (cleanup)
        remove_container = utils.conf_get(
            myth_conf,
            "docker.remove_containers",
            True,
        )
        # Maximum seconds to wait for analysis to complete (default 5 minutes)
        # Note: Symbolic execution can be slow; increase for complex contracts
        timeout = utils.conf_get(myth_conf, "timeout", 300)
        # Default output format (json for machine-readable results)
        outform = utils.conf_get(myth_conf, "outform", "json")

        # STEP 3: Build the full command to execute inside container
        fullcmd = [command] + args
        # Automatically add JSON output flag if not already specified by user
        # This ensures parseable results for programmatic consumption
        if ("-o" not in fullcmd) and ("--outform" not in fullcmd):
            fullcmd += ["-o", outform]
        _logger.info("Mythril command: %s", " ".join(fullcmd))

        # STEP 4: Ensure Docker image is available locally (pulls if missing)
        # Uses 'if-not-present' policy: only downloads if not in local cache
        pull_success, pull_error = argus_docker.pull_image(image, platform, pull_policy)
        if not pull_success:
            return {
                "exit_code": -1,
                "container_exit_code": None,
                "stdout": "Failed to pull Docker image",
                "stderr": pull_error,
            }

        # STEP 5: Execute Mythril in Docker container
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

        # STEP 6: Parse JSON output from Mythril (if valid JSON)
        # Mythril JSON output includes 'success', 'error', and 'issues' array
        stdout = utils.str2dict(res["stdout"]) if res["stdout"] else {}
        stderr = utils.str2dict(res["stderr"]) if res["stderr"] else {}

        return {
            "exit_code": res[
                "exit_code"
            ],  # 0 = success, >0 = issues found or execution errors
            "container_exit_code": res["container_exit_code"],
            "stdout": stdout,  # Primary vulnerability findings
            "stderr": stderr,  # Errors, solver timeouts, or diagnostic messages
        }

    # pylint: disable=broad-except
    except Exception as e:
        # Catch-all for unexpected errors (network issues, Docker daemon crashes, solver failures, etc.)
        return {
            "exit_code": -1,
            "container_exit_code": None,
            "stdout": "",
            "stderr": f"Unexpected error during Docker execution: {str(e)}",
        }
