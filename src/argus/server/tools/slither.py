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
import json

from argus import utils
from argus.core import docker as argus_docker
from argus.plugins import MCPToolPlugin


_logger = logging.getLogger("argus.console")


class SlitherToolPlugin(MCPToolPlugin):
    """Plugin wrapper for Slither static analysis tool"""

    config: Dict[str, Any]

    @property
    def name(self) -> str:
        return "slither"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Slither static analysis tool for smart contract security"

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the slither tool plugin."""
        self.config = config or {}
        self.tools = {
            "slither": self.slither,
            "query_slither_results": self.query_slither_results,
        }
        self.initialized = True

    async def slither(
        self,
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
        --solc-remaps REMAPS: Add Solidity remappings (e.g. "@openzeppelin=node_modules/@openzeppelin")
        --solc-args ARGS: Additional arguments for solc compiler
        --print PRINTERS: Print contract information (e.g. human-summary, inheritance-graph)

        Args:
            command: The Slither command to execute. Defaults to "slither" if not specified.
                    Generally should remain as "slither" for standard analysis.

            args: List of command-line arguments to pass to Slither.
                - First argument is typically the target (file path, directory, or ".")
                - Followed by optional flags like --detect, --exclude, --json, etc.
                - Example: ["contract.sol", "--detect", "reentrancy-eth", "--json", "output.json"]
                - Example: [".", "--exclude", "naming-convention"]

            kwargs: Additional keyword arguments. Currently unused but reserved for future
                    extensibility (e.g. environment variables, custom configurations).

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
            project_root = Path(
                utils.conf_get(
                    self.config,
                    "workdir",
                    Path.cwd().as_posix(),
                )
            )

            # Docker image containing Slither and Solidity compiler tools
            image = utils.conf_get(
                self.config,
                "docker.image",
                "trailofbits/eth-security-toolbox:latest",
            )
            platform = utils.conf_get(self.config, "docker.platform", None)
            pull_policy = utils.conf_get(
                self.config, "docker.pull_policy", "if-not-present"
            )
            # Network mode: 'bridge' for isolated, 'host' for network access
            network_mode = utils.conf_get(self.config, "docker.network_mode", "bridge")
            # Whether to remove container after execution (cleanup)
            remove_container = utils.conf_get(
                self.config,
                "docker.remove_containers",
                True,
            )
            # Maximum seconds to wait for analysis to complete (default 5 minutes)
            timeout = utils.conf_get(self.config, "timeout", 300)

            # STEP 3: Build the full command to execute inside container
            fullcmd = [command] + args
            _logger.info("Slither command: %s", " ".join(fullcmd))

            # STEP 4: Ensure Docker image is available locally (pulls if missing)
            # Uses 'if-not-present' policy: only downloads if not in local cache
            pull_success, pull_error = argus_docker.pull_image(
                image, platform, pull_policy
            )
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

            # Log stderr and stdout if container failed
            if res["container_exit_code"] != 0:
                _logger.warning(
                    "Slither container exited with code %d. stderr: %s, stdout: %s",
                    res["container_exit_code"],
                    stderr if stderr else res.get("stderr", ""),
                    res.get("stdout", "")[:500] if res.get("stdout") else "",
                )

            # STEP 7: Save full results and return summary
            if isinstance(stdout, dict) and "results" in stdout:
                _logger.info("Slither returned results dict with %d detectors",
                           len(stdout.get("results", {}).get("detectors", [])))
                results_file = self._save_full_results(stdout)
                if results_file:
                    _logger.info("Replacing full results with summary for results_file: %s", results_file)
                    stdout = self._create_summary(stdout, results_file)
                    _logger.info("Summary created: %d total findings", stdout.get("total_findings", 0))
                else:
                    _logger.warning("Failed to save results file, returning full results")

            return {
                "exit_code": res[
                    "exit_code"
                ],  # 0 = success, >0 = errors found or execution issues
                "container_exit_code": res["container_exit_code"],
                "stdout": stdout,  # Primary analysis results (now summary if results saved)
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

    def _save_full_results(self, results: dict) -> Optional[str]:
        """Save full Slither results to file and return file path."""
        try:
            # Get output directory from config (orchestrator sets this)
            output_dir = self.config.get("output_dir")
            if not output_dir:
                _logger.warning("No output_dir in config, cannot save Slither results")
                return None

            output_path = Path(output_dir) / "slither-full-results.json"
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2)

            _logger.info("Saved full Slither results to: %s", output_path)
            return str(output_path)
        except Exception as e:
            _logger.error("Failed to save Slither results: %s", e)
            return None

    def _create_summary(self, results: dict, results_file: str) -> dict:
        """Create summary of Slither results."""
        if not isinstance(results, dict) or "results" not in results:
            return {"error": "Invalid results format"}

        detectors = results.get("results", {}).get("detectors", [])

        # Count by severity
        by_severity = {}
        by_detector = {}
        by_contract = {}

        for finding in detectors:
            impact = finding.get("impact", "Unknown")
            detector = finding.get("check", "unknown")

            # Count by severity
            by_severity[impact] = by_severity.get(impact, 0) + 1
            by_detector[detector] = by_detector.get(detector, 0) + 1

            # Extract contracts from elements
            for element in finding.get("elements", []):
                if element.get("type") == "contract":
                    contract_name = element.get("name", "Unknown")
                    by_contract[contract_name] = by_contract.get(contract_name, 0) + 1

        return {
            "success": results.get("success", False),
            "results_file": results_file,
            "total_findings": len(detectors),
            "by_severity": by_severity,
            "by_detector": by_detector,
            "by_contract": by_contract,
            "message": f"Full results saved to {results_file}. Use query_slither_results to retrieve filtered findings.",
        }

    async def query_slither_results(
        self,
        results_file: str,
        severity: Optional[list] = None,
        detector_types: Optional[list] = None,
        contracts: Optional[list] = None,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """
        Query Slither results with server-side filtering.

        Allows retrieving specific findings from saved Slither results without
        loading the entire file into LLM context.

        Args:
            results_file: Path to slither-full-results.json file
            severity: Filter by severity levels (e.g. ["High", "Medium"])
            detector_types: Filter by detector names (e.g. ["reentrancy-eth"])
            contracts: Filter by contract names (e.g. ["Visor.sol"])
            limit: Maximum number of findings to return (default 50)

        Returns:
            Dict with filtered findings and metadata

        Examples:
            # Get all high-severity findings
            query_slither_results(
                results_file="argus/20251210/slither-full-results.json",
                severity=["High"]
            )

            # Get reentrancy findings
            query_slither_results(
                results_file="argus/20251210/slither-full-results.json",
                detector_types=["reentrancy-eth", "reentrancy-no-eth"]
            )
        """
        _logger.info("Query Slither results: file=%s, severity=%s, detector_types=%s, contracts=%s, limit=%d",
                    results_file, severity, detector_types, contracts, limit)
        try:
            # Load full results
            with open(results_file, "r", encoding="utf-8") as f:
                full_results = json.load(f)

            detectors = full_results.get("results", {}).get("detectors", [])

            # Apply filters
            filtered = []
            for finding in detectors:
                # Filter by severity
                if severity and finding.get("impact") not in severity:
                    continue

                # Filter by detector type
                if detector_types and finding.get("check") not in detector_types:
                    continue

                # Filter by contract (check if any element matches)
                if contracts:
                    contract_match = False
                    for element in finding.get("elements", []):
                        if (
                            element.get("type") == "contract"
                            and element.get("name") in contracts
                        ):
                            contract_match = True
                            break
                    if not contract_match:
                        continue

                # Simplify finding (remove verbose fields to save space)
                simplified = {
                    "check": finding.get("check"),
                    "impact": finding.get("impact"),
                    "confidence": finding.get("confidence"),
                    "description": finding.get("description"),
                    "first_markdown_element": finding.get("first_markdown_element"),
                }

                filtered.append(simplified)

                # Respect limit
                if len(filtered) >= limit:
                    break

            result = {
                "success": True,
                "findings": filtered,
                "total_found": len(filtered),
                "total_available": len(detectors),
                "truncated": len(filtered) >= limit,
            }
            _logger.info("Query returned %d findings (out of %d total, truncated=%s)",
                        len(filtered), len(detectors), len(filtered) >= limit)
            return result

        except FileNotFoundError:
            return {
                "success": False,
                "error": f"Results file not found: {results_file}",
                "findings": [],
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to query results: {str(e)}",
                "findings": [],
            }
