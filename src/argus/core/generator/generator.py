"""Test generator for creating security test cases from vulnerability findings.

Uses LLM with tool access to generate and write Hardhat test cases that demonstrate
vulnerabilities found during static analysis and semantic analysis phases.
"""

from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import logging
import subprocess

from argus.core import conf
from argus import utils
from argus.llm import get_llm_provider
from argus.core.generator import prompts as gen_prompts

_logger = logging.getLogger("argus.console")


class TestGenerator:
    """Generates and executes security tests for smart contracts."""

    def __init__(
        self,
        contracts: List[Path],
        file_semantic_findings: Dict[str, List[Dict]],
        project_semantic_findings: List[Dict],
        cross_contract_findings: List[Dict],
        static_analysis_results: Dict[str, Dict],
        endpoints: Dict[str, List[Dict]],
        output_dir: Path,
        project_path: Path,
    ):
        """Initialize test generator with analysis results.

        Args:
            contracts: List of contract file paths
            file_semantic_findings: Semantic findings per file from Phase 2
            project_semantic_findings: Project-level semantic findings from Phase 3
            cross_contract_findings: Cross-contract findings from Phase 3
            static_analysis_results: Vulnerability findings from Phase 4
            endpoints: Extracted function endpoints from Phase 5
            output_dir: Directory for test output
            project_path: Project root directory
        """
        self.contracts = contracts
        self.file_semantic_findings = file_semantic_findings
        self.project_semantic_findings = project_semantic_findings
        self.cross_contract_findings = cross_contract_findings
        self.static_analysis_results = static_analysis_results
        self.endpoints = endpoints
        self.output_dir = output_dir
        self.project_path = project_path

        # Create fresh LLM client for test generation
        llm_provider_name = conf.get("generator.llm", "gemini")
        self.llm = get_llm_provider(llm_provider_name)
        self.llm.initialize_client()

        _logger.info("Initialized TestGenerator with %s LLM", llm_provider_name)

    async def generate_tests(self) -> Tuple[List[Path], Dict[str, Any]]:
        """Generate tests for all contracts with vulnerabilities.

        Returns:
            Tuple of (generated_test_paths, test_results)
        """
        generated_tests = []
        test_results = {
            "tests_generated": 0,
            "tests_executed": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "compilation_succeeded": 0,
            "compilation_failed": 0,
            "results": [],
        }

        try:
            # Generate tests for each contract
            for contract in self.contracts:
                contract_name = contract.name

                # Collect all findings for this contract
                contract_findings = self._collect_contract_findings(contract_name)

                if not contract_findings:
                    _logger.debug("Skipping %s: no contract-specific findings", contract_name)
                    continue

                # Generate test file for this contract
                _logger.info(
                    "Generating tests for %s (%d contract-specific findings)",
                    contract_name,
                    len(contract_findings)
                )

                test_path = await self._generate_contract_tests(
                    contract=contract,
                    contract_name=contract_name,
                    contract_findings=contract_findings,
                )

                if test_path:
                    generated_tests.append(test_path)
                    test_results["tests_generated"] += 1

                    # Optionally execute tests
                    # Note: Test execution requires proper Hardhat setup
                    # For now, we just generate the tests
                    # execution_result = await self._execute_tests(test_path)
                    # test_results["results"].append(execution_result)

            return generated_tests, test_results

        finally:
            # Cleanup: close MCP client session for test generation LLM
            _logger.debug("Cleaning up test generator MCP session...")
            await self.llm.cleanup_mcp_session()

    def _collect_contract_findings(self, contract_name: str) -> List[Dict]:
        """Collect contract-specific findings (not including project-level).

        Args:
            contract_name: Name of the contract (e.g., "SimpleBank.sol")

        Returns:
            List of contract-specific findings
        """
        contract_findings = []

        # Phase 2: File-level semantic findings
        if contract_name in self.file_semantic_findings:
            semantic_findings = self.file_semantic_findings[contract_name]
            for finding in semantic_findings:
                # Tag with source phase
                finding_with_source = {**finding, "source_phase": "semantic_analysis_file"}
                contract_findings.append(finding_with_source)

        # Phase 3: Cross-contract findings involving this contract
        for finding in self.cross_contract_findings:
            finding_with_source = {**finding, "source_phase": "semantic_analysis_cross_contract"}
            # Include if involves this contract
            if "contracts" in finding and contract_name in finding.get("contracts", []):
                contract_findings.append(finding_with_source)
            elif "contract" in finding and finding["contract"] == contract_name:
                contract_findings.append(finding_with_source)

        # Phase 4: Static analysis findings
        if contract_name in self.static_analysis_results:
            static_findings = self.static_analysis_results[contract_name].get("findings", [])
            for finding in static_findings:
                finding_with_source = {**finding, "source_phase": "static_analysis"}
                contract_findings.append(finding_with_source)

        return contract_findings

    async def _generate_contract_tests(
        self,
        contract: Path,
        contract_name: str,
        contract_findings: List[Dict],
    ) -> Optional[Path]:
        """Generate test file for a single contract using LLM with tool access.

        Args:
            contract: Path to contract file
            contract_name: Name of the contract
            contract_findings: Contract-specific findings

        Returns:
            Path to generated test file, or None if generation failed
        """
        try:
            # Read contract source code
            contract_code = utils.read_file(str(contract))

            # Get endpoints for this contract
            contract_endpoints = self.endpoints.get(contract_name, [])

            if not contract_endpoints:
                _logger.warning("No endpoints found for %s, skipping test generation", contract_name)
                return None

            # Extract contract name without .sol extension
            base_name = contract_name.replace(".sol", "")

            # Create test directory in PROJECT (not output dir) so Hardhat can find tests
            test_dir = self.project_path / "test"
            test_dir.mkdir(parents=True, exist_ok=True)

            # Create helper contracts directory in PROJECT (not output dir)
            helper_dir = self.project_path / "contracts" / "test-helpers"
            helper_dir.mkdir(parents=True, exist_ok=True)

            # Expected test file path in project directory with Argus prefix
            test_filename = f"Argus.{base_name}.test.js"
            test_path = test_dir / test_filename

            # Build comprehensive context prompt
            prompt = gen_prompts.test_generation_prompt(
                contract_name=base_name,
                contract_code=contract_code,
                contract_endpoints=contract_endpoints,
                contract_findings=contract_findings,
                project_semantic_findings=self.project_semantic_findings,
                output_path=test_path,
                project_root=self.project_path,
            )

            _logger.debug("Generating tests for %s using LLM with tool access...", contract_name)

            # Call LLM with tool access to write, compile, and test files
            # The LLM will iteratively fix compilation and runtime errors
            response = await self.llm.call_with_tools(
                prompt=prompt,
                tools=self._get_filesystem_tools(),
                max_iterations=15,  # Increased to allow for compile-fix-test cycles
            )

            _logger.info("=" * 80)
            _logger.info("LLM RESPONSE (Test Generation - %s):", contract_name)
            _logger.info("=" * 80)
            _logger.info(response)
            _logger.info("=" * 80)

            # Check if LLM created the test file
            if test_path.exists():
                _logger.info("✓ Generated test file: %s", test_path)
                _logger.info("  LLM completed test generation successfully")
                return test_path
            else:
                _logger.warning("✗ LLM did not create expected test file: %s", test_path)
                return None

        except Exception as e:
            _logger.error("Failed to generate tests for %s: %s", contract_name, e, exc_info=True)
            return None

    def _get_filesystem_tools(self) -> List[Dict]:
        """Get tool definitions for LLM (filesystem + command execution).

        Returns:
            List of tool definitions
        """
        return [
            {
                "name": "write_file",
                "description": "Write content to a file, creating it if it doesn't exist or overwriting if it does.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the file to write (can be absolute or relative to workdir)",
                        },
                        "content": {
                            "type": "string",
                            "description": "Content to write to the file as a string",
                        },
                    },
                    "required": ["file_path", "content"],
                },
            },
            {
                "name": "read_file",
                "description": "Read contents of a file for inspection or error analysis.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the file to read",
                        },
                    },
                    "required": ["file_path"],
                },
            },
            {
                "name": "run_command",
                "description": "Execute Hardhat commands for compilation, testing, and cache cleaning. Only whitelisted commands allowed: npx hardhat compile/test/clean.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "Command to execute (must be 'npx')",
                        },
                        "args": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Command arguments. Examples: ['hardhat', 'compile'], ['hardhat', 'test', 'test/Contract.test.js'], ['hardhat', 'clean']",
                        },
                        "cwd": {
                            "type": "string",
                            "description": "Working directory (optional, defaults to project root)",
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Timeout in seconds (default: 180, max: 240). First compilation may take longer.",
                        },
                    },
                    "required": ["command", "args"],
                },
            },
        ]

    async def _execute_tests(self, test_path: Path) -> Dict[str, Any]:
        """Execute generated tests using Hardhat.

        Args:
            test_path: Path to test file

        Returns:
            Dict with execution results
        """
        try:
            _logger.info("Executing tests: %s", test_path)

            # Run Hardhat test
            result = subprocess.run(
                ["npx", "hardhat", "test", str(test_path)],
                cwd=str(self.project_path),
                capture_output=True,
                text=True,
                timeout=120,
            )

            passed = result.returncode == 0

            execution_result = {
                "test_file": str(test_path),
                "status": "passed" if passed else "failed",
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }

            if passed:
                _logger.info("Tests passed: %s", test_path.name)
            else:
                _logger.warning("Tests failed: %s", test_path.name)
                _logger.debug("Test output:\n%s", result.stdout)
                _logger.debug("Test errors:\n%s", result.stderr)

            return execution_result

        except subprocess.TimeoutExpired:
            _logger.error("Test execution timed out: %s", test_path)
            return {
                "test_file": str(test_path),
                "status": "timeout",
                "exit_code": -1,
                "stdout": "",
                "stderr": "Test execution timed out after 120 seconds",
            }

        except Exception as e:
            _logger.error("Failed to execute tests %s: %s", test_path, e)
            return {
                "test_file": str(test_path),
                "status": "error",
                "exit_code": -1,
                "stdout": "",
                "stderr": str(e),
            }
