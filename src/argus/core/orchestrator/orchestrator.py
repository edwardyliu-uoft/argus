"""Argus Orchestrator: Coordinates multi-phase security analysis workflow.

Phase 1: Initialization & Discovery
Phase 2: File-level Semantic Analysis
Phase 3: Project-level Semantic Analysis
Phase 4: Static Analysis (Slither/Mythril)
Phase 5: Endpoint Extraction
Phase 6: Test Generation & Execution
Phase 7: Report Generation
"""

import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

from argus import utils, server as mcp_server, llm
from argus.core import conf
from argus.core.orchestrator import prompts

_logger = logging.getLogger("argus.console")


class OrchestrationState:
    """Maintains state across orchestration phases."""

    def __init__(self):
        self.start_time = datetime.now()
        self.current_phase = "initialization"

        # Phase 1: Discovery
        self.contracts: List[Path] = []
        self.documentation: Dict[str, str] = {}

        # Phase 2: File-level semantic analysis
        self.file_semantic_findings: Dict[str, List[Dict]] = {}

        # Phase 2: Contract classification metadata
        self.contracts_metadata: Dict[str, Dict] = {}
        self.contracts_to_analyze: List[Path] = []
        self.contracts_skipped: List[Path] = []

        # Phase 3: Project-level semantic analysis
        self.project_semantic_findings: List[Dict] = []
        self.cross_contract_findings: List[Dict] = []

        # Phase 4: Static analysis
        self.static_analysis_results: Dict[str, Dict] = {}
        self.static_analysis_summary: str = ""  # Overall summary across all contracts
        self.tool_decisions: Dict[str, List[str]] = {}  # contract -> [tools_to_run]

        # Phase 5: Endpoints
        self.endpoints: Dict[str, List[Dict]] = {}

        # Phase 6: Tests
        self.generated_tests: List[Path] = []
        self.test_results: Dict[str, Any] = {}

        # Phase 7: Report
        self.report_path: Optional[Path] = None

        # Errors
        self.errors: List[str] = []


class ArgusOrchestrator:
    """Orchestrates multi-phase smart contract security analysis."""

    def __init__(self, project_path: str):
        """Initialize orchestrator.

        Args:
            project_path: Path to Hardhat project root
        """
        self.project_path = Path(project_path).resolve()
        self.config = conf
        self.state = OrchestrationState()

        # Initialize LLM provider
        llm_provider_name = self.config.get("orchestrator.llm", "anthropic")
        self.llm = llm.get_llm_provider(llm_provider_name)
        self.llm.initialize_client()

        # Set up output directory
        output_dir_name = self.config.get("output.directory", "argus")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = self.project_path / output_dir_name / timestamp
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Set up file logging
        self._setup_file_logging()

        # Start MCP server for LLM tool access
        mcp_host = self.config.get("server.host", "127.0.0.1")
        mcp_port = self.config.get("server.port", 8000)
        log_file = self.output_dir / "argus-analysis.log"
        self.mcp_server = mcp_server.start(
            host=mcp_host,
            port=mcp_port,
            log_file=str(log_file),
            output_dir=str(self.output_dir),
        )
        _logger.info("Started MCP server at http://%s:%d/mcp", mcp_host, mcp_port)
        _logger.info("Initialized Argus Orchestrator for %s", self.project_path)
        _logger.info("Output directory: %s", self.output_dir)

    def _setup_file_logging(self) -> None:
        """Set up file logging to capture all logs to a file in the output directory."""
        log_file = self.output_dir / "argus-analysis.log"

        # Create file handler
        file_handler = logging.FileHandler(log_file, mode="w", encoding="utf-8")

        # Set format (same as console but with timestamp)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(formatter)

        # Always use DEBUG level for file logging to capture all details
        file_handler.setLevel(logging.DEBUG)

        # Add handler to root logger to capture all argus.* loggers
        root_logger = logging.getLogger("argus")
        root_logger.setLevel(logging.DEBUG)  # Set logger level to DEBUG too
        root_logger.addHandler(file_handler)

        _logger.info("Logging to file: %s", log_file)

    async def run(self) -> Dict[str, Any]:
        """Execute all 7 phases of analysis.

        Returns:
            Dictionary with results summary
        """
        _logger.info("=" * 80)
        _logger.info("ARGUS SECURITY ANALYSIS")
        _logger.info("=" * 80)

        try:
            # Phase 1: Initialization & Discovery
            await self.phase1_initialization()

            # Phase 2: File-level Semantic Analysis
            await self.phase2_file_semantic_analysis()

            # Phase 3: Project-level Semantic Analysis
            await self.phase3_project_semantic_analysis()

            # Phase 4: Static Analysis
            await self.phase4_static_analysis()

            # FOR DEBUGGING
            # Phase 5: Endpoint Extraction
            await self.phase5_endpoint_extraction()

            # Phase 6: Test Generation & Execution
            await self.phase6_test_generation()

            # Phase 7: Report Generation
            await self.phase7_report_generation()

            # Summary
            duration = (datetime.now() - self.state.start_time).total_seconds()
            _logger.info("=" * 80)
            _logger.info("Analysis complete in %.1fs", duration)
            _logger.info("Report: %s", self.state.report_path)
            _logger.info("=" * 80)

            return {
                "success": True,
                "duration": duration,
                "report_path": str(self.state.report_path),
                "contracts_analyzed": len(self.state.contracts),
                "tests_generated": len(self.state.generated_tests),
                "errors": self.state.errors,
            }

        # pylint: disable=broad-except
        except Exception as e:
            _logger.error("Orchestration failed: %s", e, exc_info=True)
            self.state.errors.append(str(e))
            return {
                "success": False,
                "error": str(e),
                "errors": self.state.errors,
            }
        finally:
            # Cleanup: stop MCP server
            if self.mcp_server:
                _logger.info("Stopping MCP server...")
                mcp_server.stop()
                self.mcp_server = None
                _logger.info("MCP server stopped")

    # =========================================================================
    # PHASE 1: INITIALIZATION & DISCOVERY
    # =========================================================================

    async def phase1_initialization(self) -> None:
        """Phase 1: Initialize project and discover contracts.

        Discovers all Solidity contracts in the project, reads documentation,
        creates output directories, and generates an initial analysis summary.
        """
        _logger.info("=" * 80)
        _logger.info("PHASE 1: INITIALIZATION & DISCOVERY")
        _logger.info("=" * 80)

        self.state.current_phase = "initialization"

        try:
            # Create output directory structure
            utils.create_directory(self.output_dir)
            utils.create_directory(self.output_dir / "contracts")
            utils.create_directory(self.output_dir / "tests")
            utils.create_directory(self.output_dir / "reports")
            _logger.info("Created output directory: %s", self.output_dir)

            # look for .sol files
            # Get excluded directories from config, or use defaults
            exclude_dirs = self.config.get(
                "orchestrator.exclude_dirs",
                [
                    "node_modules",
                    "test",
                    "tests",
                    "build",
                    "artifacts",
                    "cache",
                ]
            )
            self.state.contracts = utils.find_files_with_extension(
                str(self.project_path),
                "sol",
                exclude_dirs,
            )

            if not self.state.contracts:
                _logger.warning("No Solidity contracts found in project")
            else:
                _logger.info("Discovered %d contracts", len(self.state.contracts))

            # Read documentation files
            readme_path = self.project_path / "README.md"
            if readme_path.exists():
                self.state.documentation["README"] = utils.read_file(str(readme_path))
                _logger.info("Found README.md")

            # NOTE: this assumes that other docs are in docs/ dir, might change in the future
            # Look for other documentation
            docs_dir = self.project_path / "docs"
            if docs_dir.exists():
                doc_files = utils.find_files_with_extension(str(docs_dir), "md")
                for doc_file in doc_files:
                    doc_name = doc_file.stem
                    self.state.documentation[doc_name] = utils.read_file(str(doc_file))
                _logger.info("Found %d documentation files", len(doc_files))

            # NOTE: not sure if we need this initial summary
            # Generate initial analysis summary using LLM
            # if self.state.contracts:
            #     contract_list = [
            #         str(c.relative_to(self.project_path)) for c in self.state.contracts
            #     ]
            #     doc_list = list(self.state.documentation.keys())

            #     prompt = prompts.initialization_summary_prompt(
            #         contracts=contract_list, docs=doc_list
            #     )

            #     response = await self.llm.generate_text(prompt)
            #     summary = parse_json_llm(response)
            #     # Write summary to output directory
            #     # write_file(self.output_dir / "initialization_summary.json", json.dumps(summary, indent=2))

            _logger.info("Initial discovery complete")

            # Save list of discovered contracts for write protection
            # The MCP server filesystem plugin will use this to prevent
            # modification of existing source contracts
            if self.state.contracts:
                protected_files = [str(c.resolve()) for c in self.state.contracts]
                protected_files_path = self.output_dir / "write-protected-files.json"
                import json
                with open(protected_files_path, "w", encoding="utf-8") as f:
                    json.dump(protected_files, f, indent=2)
                _logger.info(
                    "Saved %d write-protected contract paths to %s",
                    len(protected_files),
                    protected_files_path,
                )

        except Exception as e:
            _logger.error("Phase 1 failed: %s", e, exc_info=True)
            self.state.errors.append(f"Phase 1: {str(e)}")
            raise

    # =========================================================================
    # PHASE 2: FILE-LEVEL SEMANTIC ANALYSIS
    # =========================================================================

    async def phase2_file_semantic_analysis(self) -> None:
        """Phase 2: Analyze each contract file for semantic issues.

        Examines individual contracts for misalignment between documentation
        and implementation, checking for semantic vulnerabilities at the
        file level.
        """
        _logger.info("=" * 80)
        _logger.info("PHASE 2: FILE-LEVEL SEMANTIC ANALYSIS")
        _logger.info("=" * 80)

        self.state.current_phase = "file_semantic_analysis"

        if not self.state.contracts:
            _logger.warning("No contracts to analyze, skipping Phase 2")
            return

        try:
            _logger.info("Analyzing %d contracts", len(self.state.contracts))

            # Analyze contracts concurrently for better performance
            tasks = [
                self._analyze_single_contract(contract)
                for contract in self.state.contracts
            ]
            await asyncio.gather(*tasks)

            # Count total findings
            total_findings = sum(
                len(findings) for findings in self.state.file_semantic_findings.values()
            )
            _logger.info(
                "Phase 2 semantic analysis complete: %d findings across %d contracts",
                total_findings,
                len(self.state.contracts),
            )

            # Apply filtering based on classification
            _logger.info("")
            self._apply_contract_filter()

        except Exception as e:
            _logger.error("Phase 2 failed: %s", e, exc_info=True)
            self.state.errors.append(f"Phase 2: {str(e)}")
            raise

    async def _analyze_single_contract(self, contract_path: Path) -> None:
        """Analyze a single contract file for semantic issues.

        Args:
            contract_path: Path to the contract file
        """
        try:
            contract_name = contract_path.name
            _logger.info("Analyzing %s...", contract_name)

            # Read contract code
            code = utils.read_file(str(contract_path))

            # Generate prompt for semantic analysis
            prompt = prompts.file_semantic_analysis_prompt(
                file_path=str(contract_path.relative_to(self.project_path)), code=code
            )

            # Log the prompt being sent (for debugging)
            _logger.debug("=" * 80)
            _logger.debug("PROMPT SENT TO LLM (Phase 2 - %s):", contract_name)
            _logger.debug("=" * 80)
            _logger.debug(prompt[:500] + "..." if len(prompt) > 500 else prompt)
            _logger.debug("=" * 80)

            # Call LLM for semantic analysis
            response = await self.llm.call_simple(prompt)

            # Log the raw LLM response for debugging
            _logger.info("=" * 80)
            _logger.info("LLM RESPONSE (Phase 2 - %s):", contract_name)
            _logger.info("=" * 80)
            _logger.info(response)
            _logger.info("=" * 80)

            # Parse findings and classification from response
            try:
                findings_data = utils.parse_json_llm(response)

                # Extract findings
                self.state.file_semantic_findings[contract_name] = findings_data.get(
                    "findings", []
                )

                # Extract classification metadata
                classification = findings_data.get("contract_classification", {})

                # Provide safe defaults if classification is missing or incomplete
                if not classification:
                    _logger.warning(
                        "No classification provided for %s, defaulting to analyze",
                        contract_name,
                    )
                    classification = {
                        "is_standard_library": False,
                        "library_type": None,
                        "is_test_contract": False,
                        "is_mock_contract": False,
                        "complexity": "unknown",
                        "should_analyze_further": True,  # Safe default: analyze when unsure
                        "skip_reason": None,
                        "confidence": 5,
                    }

                # Ensure should_analyze_further is present with safe default
                if "should_analyze_further" not in classification:
                    classification["should_analyze_further"] = True
                    classification["confidence"] = classification.get("confidence", 5)

                # Store classification in state
                self.state.contracts_metadata[contract_name] = classification

                # Log classification decision for transparency
                should_analyze = classification.get("should_analyze_further", True)
                skip_reason = classification.get("skip_reason", "N/A")
                confidence = classification.get("confidence", 0)
                complexity = classification.get("complexity", "unknown")

                if should_analyze:
                    _logger.info(
                        "✓ %s marked FOR ANALYSIS (complexity: %s, confidence: %d/10)",
                        contract_name,
                        complexity,
                        confidence,
                    )
                else:
                    _logger.info(
                        "⊘ %s marked TO SKIP - reason: %s (confidence: %d/10)",
                        contract_name,
                        skip_reason,
                        confidence,
                    )

                _logger.info(
                    "Successfully parsed %d findings for %s",
                    len(self.state.file_semantic_findings[contract_name]),
                    contract_name,
                )

            # pylint: disable=broad-except
            except Exception as e:
                _logger.warning(
                    "Failed to parse LLM response as JSON for %s: %s",
                    contract_name,
                    e,
                )
                # Fallback: empty findings + safe default classification
                self.state.file_semantic_findings[contract_name] = []
                self.state.contracts_metadata[contract_name] = {
                    "should_analyze_further": True,  # Conservative: analyze if parsing fails
                    "skip_reason": None,
                    "confidence": 0,
                }

            _logger.info(
                "Completed analysis of %s: %d findings",
                contract_name,
                len(self.state.file_semantic_findings[contract_name]),
            )

        # pylint: disable=broad-except
        except Exception as e:
            _logger.error("Failed to analyze %s: %s", contract_path.name, e)
            self.state.errors.append(f"Phase 2 ({contract_path.name}): {str(e)}")

    def _apply_contract_filter(self) -> None:
        """Apply filtering based on Phase 2 classification metadata.

        Creates contracts_to_analyze and contracts_skipped lists based on
        the should_analyze_further flag in contracts_metadata.

        Respects configuration settings:
        - orchestrator.enable_contract_filtering
        - orchestrator.filter_low_confidence_threshold

        Edge case handling:
        - If all contracts filtered out → fallback to analyze all
        - If low confidence → analyze anyway (conservative)
        """
        _logger.info("=" * 80)
        _logger.info("APPLYING CONTRACT FILTER")
        _logger.info("=" * 80)

        # Check if filtering is enabled in config
        enable_filtering = self.config.get("orchestrator.enable_contract_filtering", True)

        if not enable_filtering:
            _logger.info("Contract filtering DISABLED in config - analyzing all contracts")
            self.state.contracts_to_analyze = self.state.contracts.copy()
            self.state.contracts_skipped = []
            _logger.info("All %d contracts will be analyzed", len(self.state.contracts))
            return

        # Get confidence threshold from config
        min_confidence = self.config.get("orchestrator.filter_low_confidence_threshold", 7)

        # Separate contracts based on classification
        contracts_to_analyze = []
        contracts_skipped = []

        for contract in self.state.contracts:
            contract_name = contract.name
            metadata = self.state.contracts_metadata.get(contract_name, {})

            should_analyze = metadata.get("should_analyze_further", True)
            confidence = metadata.get("confidence", 0)
            skip_reason = metadata.get("skip_reason", "unspecified")

            # Safety check: if classification confidence is low, be conservative and analyze
            if not should_analyze and confidence < min_confidence:
                _logger.warning(
                    "  Low confidence (%d < %d) for skipping %s - analyzing anyway for safety",
                    confidence,
                    min_confidence,
                    contract_name,
                )
                should_analyze = True

            if should_analyze:
                contracts_to_analyze.append(contract)
            else:
                contracts_skipped.append(contract)
                _logger.info(
                    "  Skipping %s: %s (confidence: %d)",
                    contract_name,
                    skip_reason,
                    confidence,
                )

        # EDGE CASE: All contracts filtered out - fallback to analyze all
        if not contracts_to_analyze and self.state.contracts:
            _logger.warning("=" * 80)
            _logger.warning("WARNING: All contracts were filtered out!")
            _logger.warning("This may indicate:")
            _logger.warning("  1. All contracts are standard libraries (no custom code)")
            _logger.warning("  2. LLM classification was too aggressive")
            _logger.warning("  3. Configuration settings are too strict")
            _logger.warning("Falling back to analyzing all contracts to ensure coverage.")
            _logger.warning("=" * 80)

            contracts_to_analyze = self.state.contracts.copy()
            contracts_skipped = []

        # Update state
        self.state.contracts_to_analyze = contracts_to_analyze
        self.state.contracts_skipped = contracts_skipped

        # Log comprehensive summary
        total = len(self.state.contracts)
        analyze_count = len(contracts_to_analyze)
        skip_count = len(contracts_skipped)

        _logger.info("=" * 80)
        _logger.info("FILTER RESULTS:")
        _logger.info("  Total contracts discovered: %d", total)
        _logger.info(
            "  Contracts to analyze in-depth: %d (%.1f%%)",
            analyze_count,
            100 * analyze_count / total if total > 0 else 0,
        )
        _logger.info(
            "  Contracts skipped: %d (%.1f%%)",
            skip_count,
            100 * skip_count / total if total > 0 else 0,
        )

        # Breakdown by skip reason
        if contracts_skipped:
            _logger.info("")
            _logger.info("Skipped contracts by reason:")
            skip_reasons = {}
            for contract in contracts_skipped:
                metadata = self.state.contracts_metadata.get(contract.name, {})
                reason = metadata.get("skip_reason", "unspecified")
                skip_reasons[reason] = skip_reasons.get(reason, 0) + 1

            for reason, count in sorted(skip_reasons.items()):
                _logger.info("  - %s: %d contracts", reason, count)

        _logger.info("=" * 80)

    # =========================================================================
    # PHASE 3: PROJECT-LEVEL SEMANTIC ANALYSIS
    # =========================================================================

    async def phase3_project_semantic_analysis(self) -> None:
        """Phase 3: Analyze project-level semantic alignment.

        Examines the entire project for alignment with high-level design
        (from README, docs, comments, or docstrings) and performs
        cross-contract analysis.
        """
        _logger.info("=" * 80)
        _logger.info("PHASE 3: PROJECT-LEVEL SEMANTIC ANALYSIS")
        _logger.info("=" * 80)

        self.state.current_phase = "project_semantic_analysis"

        if not self.state.contracts_to_analyze:
            _logger.warning("No contracts to analyze, skipping Phase 3")
            return

        # Check if project is too large for project-level semantic analysis
        skip_if_large = self.config.get("orchestrator.skip_project_semantic_if_large", True)
        max_contracts = self.config.get("orchestrator.project_semantic_max_contracts", 10)

        if skip_if_large and len(self.state.contracts_to_analyze) > max_contracts:
            _logger.warning("=" * 80)
            _logger.warning(
                "Skipping Phase 3: Project has %d contracts (threshold: %d)",
                len(self.state.contracts_to_analyze),
                max_contracts,
            )
            _logger.warning(
                "Project-level semantic analysis disabled for large projects to prevent context overflow."
            )
            _logger.warning(
                "To enable, set orchestrator.skip_project_semantic_if_large=false or increase "
                "orchestrator.project_semantic_max_contracts in config."
            )
            _logger.warning("=" * 80)
            return

        try:
            # Perform project-level analysis if project size is manageable
            _logger.info("Performing project-level semantic analysis")
            _logger.info(
                "Analyzing %d contracts (threshold: %d)",
                len(self.state.contracts_to_analyze),
                max_contracts,
            )

            # Combine all documentation (may be empty)
            readme = self.state.documentation.get("README", "No README found")
            other_docs = (
                "\n\n".join(
                    [
                        f"## {name}\n{content}"
                        for name, content in self.state.documentation.items()
                        if name != "README"
                    ]
                )
                or "No additional documentation found"
            )

            # Read contract code for project-level analysis
            contracts_data = {}
            for contract in self.state.contracts_to_analyze:
                code = utils.read_file(str(contract))
                contracts_data[contract.name] = code

            # Generate project-level analysis prompt
            prompt = prompts.project_semantic_analysis_prompt(
                readme=readme, all_docs=other_docs, contracts=contracts_data
            )

            # Log the prompt being sent (for debugging)
            _logger.debug("=" * 80)
            _logger.debug("PROMPT SENT TO LLM (Phase 3 - Project-level):")
            _logger.debug("=" * 80)
            _logger.debug(prompt[:500] + "..." if len(prompt) > 500 else prompt)
            _logger.debug("=" * 80)

            # Call LLM for project-level analysis
            response = await self.llm.call_simple(prompt)

            # Log the raw LLM response for debugging
            _logger.info("=" * 80)
            _logger.info("LLM RESPONSE (Phase 3 - Project-level):")
            _logger.info("=" * 80)
            _logger.info(response)
            _logger.info("=" * 80)

            # Parse findings from response
            try:
                findings_data = utils.parse_json_llm(response)
                self.state.project_semantic_findings = findings_data.get("findings", [])
                _logger.info(
                    "Successfully parsed %d project-level findings",
                    len(self.state.project_semantic_findings),
                )

            # pylint: disable=broad-except
            except Exception as e:
                _logger.warning(
                    "Failed to parse LLM response as JSON for project-level analysis: %s",
                    e,
                )
                self.state.project_semantic_findings = []

            _logger.info(
                "Project-level analysis complete: %d findings",
                len(self.state.project_semantic_findings),
            )

            # Perform cross-contract analysis if multiple contracts exist
            if len(self.state.contracts_to_analyze) > 1:
                _logger.info("Performing cross-contract analysis")

                # Read contract code for cross-contract analysis
                # Limit to avoid context overflow
                max_contracts = 5
                contracts_to_analyze = self.state.contracts_to_analyze[:max_contracts]

                contracts_data = {}
                for contract in contracts_to_analyze:
                    code = utils.read_file(str(contract))
                    contracts_data[contract.name] = code

                if len(self.state.contracts_to_analyze) > max_contracts:
                    _logger.info(
                        "Analyzing %d of %d filtered contracts to avoid context overflow",
                        max_contracts,
                        len(self.state.contracts_to_analyze),
                    )

                # Generate cross-contract analysis prompt
                prompt = prompts.cross_contract_analysis_prompt(contracts_data)

                # Log the prompt being sent (for debugging)
                _logger.debug("=" * 80)
                _logger.debug("PROMPT SENT TO LLM (Phase 3 - Cross-contract):")
                _logger.debug("=" * 80)
                _logger.debug(prompt[:500] + "..." if len(prompt) > 500 else prompt)
                _logger.debug("=" * 80)

                # Call LLM for cross-contract analysis
                response = await self.llm.call_simple(prompt)

                # Log the raw LLM response for debugging
                _logger.info("=" * 80)
                _logger.info("LLM RESPONSE (Phase 3 - Cross-contract):")
                _logger.info("=" * 80)
                _logger.info(response)
                _logger.info("=" * 80)

                # Parse findings from response
                try:
                    findings_data = utils.parse_json_llm(response)
                    self.state.cross_contract_findings = findings_data.get(
                        "findings", []
                    )
                    _logger.info(
                        "Successfully parsed %d cross-contract findings",
                        len(self.state.cross_contract_findings),
                    )

                # pylint: disable=broad-except
                except Exception as e:
                    _logger.warning(
                        "Failed to parse LLM response as JSON for cross-contract analysis: %s",
                        e,
                    )
                    self.state.cross_contract_findings = []

                _logger.info(
                    "Cross-contract analysis complete: %d findings",
                    len(self.state.cross_contract_findings),
                )
            else:
                _logger.info(
                    "Only one contract in filtered set, skipping cross-contract analysis"
                )

            total_findings = len(self.state.project_semantic_findings) + len(
                self.state.cross_contract_findings
            )
            _logger.info("Phase 3 complete: %d project-level findings", total_findings)

        # pylint: disable=broad-except
        except Exception as e:
            _logger.error("Phase 3 failed: %s", e, exc_info=True)
            self.state.errors.append(f"Phase 3: {str(e)}")
            raise

    # =========================================================================
    # PHASE 4: STATIC ANALYSIS (SINGLE-STAGE LLM-DRIVEN)
    # =========================================================================

    async def phase4_static_analysis(self) -> None:
        """Phase 4: Run static analysis with LLM-driven tool selection.

        The LLM is given access to static analysis tools (Slither/Mythril)
        and autonomously decides which tools to run on which contracts based
        on semantic findings. This is done in a single LLM call with native
        tool use.
        """
        _logger.info("=" * 80)
        _logger.info("PHASE 4: STATIC ANALYSIS")
        _logger.info("=" * 80)

        self.state.current_phase = "static_analysis"

        if not self.state.contracts_to_analyze:
            _logger.warning("No contracts to analyze, skipping Phase 4")
            return

        try:
            # Ensure dependencies are installed before running static analysis tools
            # This is critical for tools like Slither and Mythril to resolve imports
            await self._ensure_hardhat_installed()

            _logger.info("Preparing context for LLM-driven static analysis")

            # Prepare contract data
            contract_data = {}
            for contract in self.state.contracts_to_analyze:
                code = utils.read_file(str(contract))
                contract_data[contract.name] = {
                    "code": code,
                    "path": str(contract),  # Absolute path for tool calls
                    "relative_path": str(contract.relative_to(self.project_path)),
                }

            # Combine all semantic findings for context
            # Only include file-level findings from contracts being analyzed
            all_semantic_findings = []
            for contract in self.state.contracts_to_analyze:
                contract_name = contract.name
                if contract_name in self.state.file_semantic_findings:
                    all_semantic_findings.extend(
                        self.state.file_semantic_findings[contract_name]
                    )
            # Project-level and cross-contract findings are already filtered by Phase 3
            all_semantic_findings.extend(self.state.project_semantic_findings)
            all_semantic_findings.extend(self.state.cross_contract_findings)

            # Generate comprehensive prompt for LLM
            prompt = prompts.tool_selection_prompt(
                contract_data=contract_data, semantic_findings=all_semantic_findings
            )

            _logger.info(
                "Invoking LLM with tool access for %d filtered contracts (%d skipped)",
                len(self.state.contracts_to_analyze),
                len(self.state.contracts_skipped),
            )

            # Log the prompt being sent (for debugging)
            _logger.debug("=" * 80)
            _logger.debug("PROMPT SENT TO LLM:")
            _logger.debug("=" * 80)
            _logger.debug(prompt[:500] + "..." if len(prompt) > 500 else prompt)
            _logger.debug("=" * 80)

            # Call LLM with native tool use via MCP
            # The LLM will:
            # 1. Analyze the semantic findings and contract data
            # 2. Decide which tools to run on which contracts
            # 3. Call the tools directly via MCP server
            # 4. Interpret and consolidate the results
            # 5. Return comprehensive analysis
            response = await self.llm.call_with_tools(
                prompt=prompt,
                tools=prompts.tools_info_prompt(),  # Slither and Mythril tool definitions
                max_iterations=20,  # Allow LLM to run multiple tools
            )

            # Log the raw LLM response for debugging
            _logger.info("=" * 80)
            _logger.info("LLM RESPONSE (Phase 4 - Static Analysis):")
            _logger.info("=" * 80)
            _logger.info(response)
            _logger.info("=" * 80)

            # Parse the LLM's final response
            # Expected structure: {"vulnerabilities": [...], "summary": "..."}
            # (Also accepts: {"findings": [...], "summary": "..."} or {"tool_executions": [...], "findings": [...], "summary": "..."})
            try:
                analysis_results = utils.parse_json_llm(response)
                _logger.info("Successfully parsed LLM response as JSON")

            # pylint: disable=broad-except
            except Exception as e:
                _logger.warning("Failed to parse LLM response as JSON: %s", e)
                # Fallback to raw text response
                analysis_results = {
                    "tool_executions": [],
                    "findings": [],
                    "summary": response,
                }

            # Extract and store results from LLM response
            self._process_static_analysis_results(analysis_results)

            # Log what the LLM decided and executed
            _logger.info("LLM completed static analysis")

            # Log based on response format
            tool_executions = analysis_results.get("tool_executions", [])
            vulnerabilities = analysis_results.get("vulnerabilities", [])
            findings = analysis_results.get("findings", [])

            if tool_executions:
                _logger.info("Tool executions: %d", len(tool_executions))
                for i, execution in enumerate(tool_executions, 1):
                    _logger.info(
                        "\t%d. Tool: %s, Contract: %s, Findings: %d",
                        i,
                        execution.get("tool", "unknown"),
                        execution.get("contract", "unknown"),
                        len(execution.get("findings", [])),
                    )
            elif vulnerabilities:
                _logger.info("Vulnerabilities found: %d", len(vulnerabilities))
            elif findings:
                _logger.info("Findings: %d", len(findings))

            total_findings = sum(
                len(results.get("findings", []))
                for results in self.state.static_analysis_results.values()
            )
            _logger.info(
                "Phase 4 complete: %d static analysis findings", total_findings
            )

            # Log findings per contract
            for contract_name, results in self.state.static_analysis_results.items():
                _logger.info(
                    "\t%s: %d findings (tools: %s)",
                    contract_name,
                    len(results.get("findings", [])),
                    ", ".join(results.get("tools_used", [])),
                )

        # pylint: disable=broad-except
        except Exception as e:
            error_str = str(e).lower()

            # Check if this is a server connection error
            is_server_error = any(
                keyword in error_str
                for keyword in [
                    "disconnected",
                    "connection",
                    "server",
                    "remote protocol",
                ]
            )

            if is_server_error:
                _logger.error(
                    "Phase 4 failed due to MCP server connection issue: %s", e
                )
                _logger.warning(
                    "Static analysis could not complete. Continuing with semantic findings only..."
                )

                # Store error but don't raise - allow orchestration to continue
                self.state.errors.append(
                    f"Phase 4: MCP server connection failed - {str(e)}"
                )
                self.state.static_analysis_summary = (
                    "Static analysis tools (Slither/Mythril) could not be executed "
                    "due to MCP server connection issues. Analysis continues with "
                    "semantic findings only."
                )

                # Log that we're continuing despite the error
                _logger.info(
                    "Phase 4 skipped: %d static analysis findings (graceful degradation)",
                    0,
                )
            else:
                # Non-server error - still fail
                _logger.error("Phase 4 failed: %s", e, exc_info=True)
                self.state.errors.append(f"Phase 4: {str(e)}")
                raise
        finally:
            # Cleanup: close MCP client session
            _logger.info("Cleaning up MCP client session...")
            try:
                await self.llm.cleanup_mcp_session()
                _logger.info("MCP client session closed")
            # pylint: disable=broad-except
            except Exception as cleanup_error:
                _logger.warning(
                    "Session termination failed: %s", str(cleanup_error)
                )
                # MCP server process will be terminated in main finally block,
                # which will clean up all resources including Docker containers

    # =========================================================================
    # PHASE 5: ENDPOINT EXTRACTION
    # =========================================================================

    async def phase5_endpoint_extraction(self) -> None:
        """Phase 5: Extract public/external endpoints from contracts.

        Analyzes each contract to identify all public and external functions,
        events, and state-changing operations. This information is used for
        test generation in Phase 6.
        """
        _logger.info("=" * 80)
        _logger.info("PHASE 5: ENDPOINT EXTRACTION")
        _logger.info("=" * 80)

        self.state.current_phase = "endpoint_extraction"

        if not self.state.contracts_to_analyze:
            _logger.warning("No contracts to analyze, skipping Phase 5")
            return

        try:
            _logger.info(
                "Extracting endpoints from %d filtered contracts",
                len(self.state.contracts_to_analyze),
            )

            # Extract endpoints concurrently for better performance
            tasks = [
                self._extract_contract_endpoints(contract)
                for contract in self.state.contracts_to_analyze
            ]
            await asyncio.gather(*tasks)

            # Count total endpoints
            total_endpoints = sum(
                len(endpoints) for endpoints in self.state.endpoints.values()
            )
            _logger.info("Phase 5 complete: %d endpoints extracted", total_endpoints)

        except Exception as e:
            _logger.error("Phase 5 failed: %s", e, exc_info=True)
            self.state.errors.append(f"Phase 5: {str(e)}")
            raise

    async def _extract_contract_endpoints(self, contract_path: Path) -> None:
        """Extract endpoints from a single contract.

        Args:
            contract_path: Path to the contract file
        """
        try:
            contract_name = contract_path.name
            _logger.info("Extracting endpoints from %s...", contract_name)

            # Read contract code
            code = utils.read_file(str(contract_path))

            # Generate endpoint extraction prompt
            prompt = prompts.endpoint_extraction_prompt(
                file_path=str(contract_path.relative_to(self.project_path)), code=code
            )

            # Call LLM for endpoint extraction
            response = await self.llm.call_simple(prompt)

            # Log the raw LLM response for debugging
            _logger.info("=" * 80)
            _logger.info("LLM RESPONSE (Phase 5 - %s):", contract_name)
            _logger.info("=" * 80)
            _logger.info(response)
            _logger.info("=" * 80)

            # Parse the LLM response
            # Expected format: JSON array directly or {"endpoints": [...]}
            try:
                endpoints_data = utils.parse_json_llm(response)

                # Handle different response formats
                if isinstance(endpoints_data, list):
                    # Direct array of endpoints
                    self.state.endpoints[contract_name] = endpoints_data
                elif isinstance(endpoints_data, dict):
                    # Wrapped in object with "endpoints" key
                    self.state.endpoints[contract_name] = endpoints_data.get(
                        "endpoints", []
                    )
                else:
                    _logger.warning(
                        "Unexpected endpoint extraction response format for %s",
                        contract_name,
                    )
                    self.state.endpoints[contract_name] = []

                _logger.info(
                    "Successfully parsed %d endpoints from %s",
                    len(self.state.endpoints[contract_name]),
                    contract_name,
                )

            # pylint: disable=broad-except
            except Exception as e:
                _logger.warning(
                    "Failed to parse endpoint extraction response for %s: %s",
                    contract_name,
                    e,
                )
                self.state.endpoints[contract_name] = []

            _logger.info(
                "Extracted %d endpoints from %s",
                len(self.state.endpoints[contract_name]),
                contract_name,
            )

        # pylint: disable=broad-except
        except Exception as e:
            _logger.error(
                "Failed to extract endpoints from %s: %s", contract_path.name, e
            )
            self.state.errors.append(f"Phase 5 ({contract_path.name}): {str(e)}")

    # =========================================================================
    # PHASE 6: TEST GENERATION & EXECUTION
    # =========================================================================

    async def phase6_test_generation(self) -> None:
        """Phase 6: Test Generation & Execution.

        Generates security tests based on vulnerabilities found in previous phases
        and optionally executes them to confirm exploitability.
        """
        _logger.info("=" * 80)
        _logger.info("PHASE 6: TEST GENERATION & EXECUTION")
        _logger.info("=" * 80)

        self.state.current_phase = "test_generation"

        if not self.state.contracts:
            _logger.warning("No contracts to generate tests for, skipping Phase 6")
            return

        try:
            # Ensure Hardhat is installed before test generation begins
            # (may already be installed from Phase 4 static analysis)
            # This prevents npx prompts during the iterative test generation process
            await self._ensure_hardhat_installed()
            # Import generator
            from argus.core.generator import TestGenerator

            # Create generator instance with all analysis results
            generator = TestGenerator(
                contracts=self.state.contracts_to_analyze,
                file_semantic_findings=self.state.file_semantic_findings,
                project_semantic_findings=self.state.project_semantic_findings,
                cross_contract_findings=self.state.cross_contract_findings,
                static_analysis_results=self.state.static_analysis_results,
                endpoints=self.state.endpoints,
                output_dir=self.output_dir,
                project_path=self.project_path,
            )

            # Generate tests
            _logger.info("Generating security tests...")
            test_paths, test_results = await generator.generate_tests()

            # Update state
            self.state.generated_tests = test_paths
            self.state.test_results = test_results

            _logger.info(
                "Phase 6 complete: %d tests generated",
                test_results.get("tests_generated", 0),
            )

            # Log summary of generated tests
            for test_path in test_paths:
                _logger.info("\tGenerated: %s", test_path.name)

        except Exception as e:
            _logger.error("Phase 6 failed: %s", e, exc_info=True)
            self.state.errors.append(f"Phase 6: {str(e)}")
            raise

    # =========================================================================
    # PHASE 7: REPORT GENERATION
    # =========================================================================

    async def phase7_report_generation(self) -> None:
        """Phase 7: Report Generation.

        Generates a comprehensive final report consolidating all analysis phases.
        """
        _logger.info("=" * 80)
        _logger.info("PHASE 7: REPORT GENERATION")
        _logger.info("=" * 80)

        self.state.current_phase = "report_generation"

        try:
            # Calculate analysis duration
            duration = (datetime.now() - self.state.start_time).total_seconds()
            timestamp = self.state.start_time.strftime("%Y-%m-%d %H:%M:%S")

            # Save raw analysis data to JSON file for reference
            import json

            raw_data = {
                "timestamp": timestamp,
                "duration": duration,
                "contracts_discovered": [
                    str(c.relative_to(self.project_path)) for c in self.state.contracts
                ],
                "contracts_analyzed": [
                    str(c.relative_to(self.project_path))
                    for c in self.state.contracts_to_analyze
                ],
                "contracts_skipped": [
                    str(c.relative_to(self.project_path))
                    for c in self.state.contracts_skipped
                ],
                "contracts_metadata": self.state.contracts_metadata,
                "file_semantic_findings": self.state.file_semantic_findings,
                "project_semantic_findings": self.state.project_semantic_findings,
                "cross_contract_findings": self.state.cross_contract_findings,
                "static_analysis_results": self.state.static_analysis_results,
                "endpoints": self.state.endpoints,
                "test_results": self.state.test_results,
            }
            raw_data_path = self.output_dir / "raw-analysis-data.json"
            utils.write_file(str(raw_data_path), json.dumps(raw_data, indent=2))
            _logger.info("Saved raw analysis data to %s", raw_data_path.name)

            # Build comprehensive prompt with all phase results
            prompt = prompts.report_generation_prompt(
                timestamp=timestamp,
                duration=duration,
                file_semantic_findings=self.state.file_semantic_findings,
                project_semantic_findings=self.state.project_semantic_findings,
                cross_contract_findings=self.state.cross_contract_findings,
                static_analysis_results=self.state.static_analysis_results,
                endpoints=self.state.endpoints,
                test_results=self.state.test_results,
                contracts=self.state.contracts_to_analyze,
                contracts_skipped=self.state.contracts_skipped,
                contracts_metadata=self.state.contracts_metadata,
            )

            # Measure prompt size
            prompt_size_chars = len(prompt)
            prompt_size_kb = prompt_size_chars / 1024
            # Rough token estimate (1 token ≈ 4 characters for English)
            estimated_tokens = prompt_size_chars // 4

            _logger.info("Generating comprehensive final report...")
            _logger.info("Report prompt size: %d chars (%.1f KB, ~%d tokens estimated)",
                        prompt_size_chars, prompt_size_kb, estimated_tokens)

            # Call LLM to generate the report
            report_content = await self.llm.call_simple(prompt)

            # Log the raw LLM response for debugging
            _logger.debug("=" * 80)
            _logger.debug("LLM RESPONSE (Phase 7 - Report Generation):")
            _logger.debug("=" * 80)
            _logger.debug(
                report_content[:1000] + "..."
                if len(report_content) > 1000
                else report_content
            )
            _logger.debug("=" * 80)

            # Write report to file
            report_filename = "argus-security-report.md"
            report_path = self.output_dir / report_filename
            utils.write_file(str(report_path), report_content)

            # Update state
            self.state.report_path = report_path

            _logger.info("Phase 7 complete: Report generated at %s", report_path)

        except Exception as e:
            _logger.error("Phase 7 failed: %s", e, exc_info=True)
            self.state.errors.append(f"Phase 7: {str(e)}")
            raise

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    async def _ensure_hardhat_installed(self) -> None:
        """Ensure Hardhat dependencies are installed to prevent interactive prompts.

        Runs `npm install` to install dependencies from package.json if node_modules
        doesn't exist or is incomplete. This is called at the start of Phase 4
        (static analysis) and Phase 6 (test generation) to ensure:
        - Static analysis tools can resolve imports (OpenZeppelin, etc.)
        - Hardhat is available for compile/test cycles

        Safe to call multiple times - checks if already installed first.
        """
        try:
            _logger.info("Checking Hardhat installation...")

            # Check if package.json exists
            package_json = self.project_path / "package.json"
            if not package_json.exists():
                _logger.warning("No package.json found - Hardhat may not be configured")
                return

            # Check if node_modules exists and has hardhat
            node_modules = self.project_path / "node_modules"
            hardhat_installed = (node_modules / "hardhat").exists()

            if hardhat_installed:
                _logger.info("✓ Hardhat is already installed")
                return

            # Install dependencies
            _logger.info("Installing Hardhat dependencies (this may take a minute)...")
            process = await asyncio.create_subprocess_exec(
                "npm",
                "install",
                cwd=str(self.project_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            _, stderr = await asyncio.wait_for(
                process.communicate(), timeout=180  # 3 minutes for npm install
            )

            if process.returncode == 0:
                _logger.info("✓ Hardhat dependencies installed successfully")
            else:
                _logger.warning(
                    "npm install returned non-zero exit code: %d", process.returncode
                )
                stderr_str = stderr.decode("utf-8", errors="replace")
                if stderr_str:
                    _logger.debug("STDERR: %s", stderr_str[:500])
                # Log but don't fail - LLM might still be able to work with it

        except asyncio.TimeoutError:
            _logger.warning("npm install timed out - dependencies may be incomplete")
        except FileNotFoundError:
            _logger.warning("npm not found - Node.js may not be installed")
        except Exception as e:
            _logger.warning("Failed to install Hardhat dependencies: %s", e)
            # Don't raise - this is just a setup step

    def _process_static_analysis_results(
        self,
        analysis_results: Dict[str, Any],
    ) -> None:
        """Process LLM tool execution results and populate state.

        Accepts multiple response formats:

        Format 1 (Gemini preferred):
        {
            "vulnerabilities": [
                {
                    "contract": "MyContract.sol",
                    "tool": "slither",
                    "severity": "High",
                    "name": "reentrancy",
                    "description": "...",
                    "sourceMap": "MyContract.sol#51-64"
                }
            ],
            "summary": "Overall analysis summary"
        }

        Format 2 (Alternative):
        {
            "tool_executions": [...],
            "findings": [...],
            "summary": "..."
        }

        Args:
            analysis_results: Parsed LLM response with tool execution results
        """
        # Initialize results storage for all contracts
        for contract in self.state.contracts:
            contract_name = contract.name
            self.state.static_analysis_results[contract_name] = {
                "tools_used": [],
                "findings": [],
                "analysis": "",
            }

        # Process tool executions (if provided)
        tool_executions = analysis_results.get("tool_executions", [])
        for execution in tool_executions:
            tool_name = execution.get("tool", "unknown")
            contract_name = execution.get("contract", "unknown")

            # Find matching contract in state
            if contract_name in self.state.static_analysis_results:
                # Track which tools were used
                if (
                    tool_name
                    not in self.state.static_analysis_results[contract_name][
                        "tools_used"
                    ]
                ):
                    self.state.static_analysis_results[contract_name][
                        "tools_used"
                    ].append(tool_name)

                # Store tool-specific findings
                tool_findings = execution.get("findings", [])
                self.state.static_analysis_results[contract_name]["findings"].extend(
                    tool_findings
                )

        # Process consolidated findings from LLM
        # Accept either "findings" or "vulnerabilities" key
        all_findings = analysis_results.get("findings", analysis_results.get("vulnerabilities", []))
        _logger.info("Processing %d findings/vulnerabilities", len(all_findings))

        for finding in all_findings:
            contract_name = finding.get("contract", "unknown")
            tool_name = finding.get("tool", "unknown")

            _logger.debug(
                "Processing finding: contract=%s, tool=%s, severity=%s, name=%s",
                contract_name,
                tool_name,
                finding.get("severity", "?"),
                finding.get("name", "?")
            )

            # Normalize contract name - try both with and without .sol extension
            # LLM might return "Treasury" or "Treasury.sol"
            matched_contract = None
            if contract_name in self.state.static_analysis_results:
                matched_contract = contract_name
                _logger.debug("Found exact match for contract: %s", contract_name)
            elif f"{contract_name}.sol" in self.state.static_analysis_results:
                matched_contract = f"{contract_name}.sol"
                _logger.debug("Found match with .sol extension: %s", matched_contract)
            elif contract_name.endswith(".sol") and contract_name[:-4] in self.state.static_analysis_results:
                matched_contract = contract_name[:-4]
                _logger.debug("Found match without .sol extension: %s", matched_contract)

            if matched_contract:
                # Track which tool found this (if not already tracked from tool_executions)
                if (
                    tool_name != "unknown"
                    and tool_name not in self.state.static_analysis_results[matched_contract]["tools_used"]
                ):
                    self.state.static_analysis_results[matched_contract]["tools_used"].append(tool_name)
                    _logger.debug("Added tool %s to %s", tool_name, matched_contract)

                # Avoid duplicates
                if (
                    finding
                    not in self.state.static_analysis_results[matched_contract]["findings"]
                ):
                    self.state.static_analysis_results[matched_contract][
                        "findings"
                    ].append(finding)
                    _logger.debug("Added finding to %s", matched_contract)
            else:
                _logger.warning(
                    "Contract '%s' not found in static_analysis_results. Available: %s",
                    contract_name,
                    list(self.state.static_analysis_results.keys())
                )

        # Store overall summary at the phase level
        self.state.static_analysis_summary = analysis_results.get("summary", "")

        # Generate per-contract analysis summaries based on their findings
        for contract_name, results in self.state.static_analysis_results.items():
            findings = results.get("findings", [])
            tools_used = results.get("tools_used", [])

            if findings:
                # Create a summary for this specific contract
                high_severity = [f for f in findings if f.get("severity") == "high"]
                medium_severity = [f for f in findings if f.get("severity") == "medium"]
                low_severity = [f for f in findings if f.get("severity") == "low"]

                summary_parts = [
                    f"Analysis of {contract_name} using {', '.join(tools_used)}:",
                    f"- {len(high_severity)} high severity issues",
                    f"- {len(medium_severity)} medium severity issues",
                    f"- {len(low_severity)} low severity issues",
                ]
                results["analysis"] = "\n".join(summary_parts)
            else:
                results["analysis"] = (
                    f"No security issues found in {contract_name} using {', '.join(tools_used) if tools_used else 'no tools'}"
                )
