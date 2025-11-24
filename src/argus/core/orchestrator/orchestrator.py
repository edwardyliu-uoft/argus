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

from argus.core.config import conf
from argus.llm import get_llm_provider
from argus.utils.utils import (
    find_project_root,
    find_files_with_extension,
    read_file,
    create_directory,
    write_file,
    parse_json_llm,
)
from argus.core.orchestrator import prompts

logger = logging.getLogger("argus.console")


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

        # Phase 3: Project-level semantic analysis
        self.project_semantic_findings: List[Dict] = []
        self.cross_contract_findings: List[Dict] = []

        # Phase 4: Static analysis
        self.static_analysis_results: Dict[str, Dict] = {}
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
        llm_provider_name = self.config.get("services.orchestrator.llm", "anthropic")
        self.llm = get_llm_provider(llm_provider_name)
        self.llm.initialize_client()

        # Set up output directory
        output_dir_name = self.config.get("output.directory", "argus")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = self.project_path / output_dir_name / timestamp

        logger.info(f"Initialized Argus Orchestrator for {self.project_path}")
        logger.info(f"Output directory: {self.output_dir}")

    async def run(self) -> Dict[str, Any]:
        """Execute all 7 phases of analysis.

        Returns:
            Dictionary with results summary
        """
        logger.info("=" * 80)
        logger.info("ARGUS SECURITY ANALYSIS")
        logger.info("=" * 80)

        try:
            # Phase 1: Initialization & Discovery
            await self.phase1_initialization()

            # Phase 2: File-level Semantic Analysis
            await self.phase2_file_semantic_analysis()

            # Phase 3: Project-level Semantic Analysis
            await self.phase3_project_semantic_analysis()

            # Phase 4: Static Analysis
            await self.phase4_static_analysis()

            # Phase 5: Endpoint Extraction
            await self.phase5_endpoint_extraction()

            # Phase 6: Test Generation & Execution
            await self.phase6_test_generation()

            # Phase 7: Report Generation
            await self.phase7_report_generation()

            # Summary
            duration = (datetime.now() - self.state.start_time).total_seconds()
            logger.info("=" * 80)
            logger.info(f"Analysis complete in {duration:.1f}s")
            logger.info(f"Report: {self.state.report_path}")
            logger.info("=" * 80)

            return {
                "success": True,
                "duration": duration,
                "report_path": str(self.state.report_path),
                "contracts_analyzed": len(self.state.contracts),
                "vulnerabilities_found": self._count_vulnerabilities(),
                "tests_generated": len(self.state.generated_tests),
                "errors": self.state.errors,
            }

        except Exception as e:
            logger.error(f"Orchestration failed: {e}", exc_info=True)
            self.state.errors.append(str(e))
            return {
                "success": False,
                "error": str(e),
                "errors": self.state.errors,
            }

    # =========================================================================
    # PHASE 1: INITIALIZATION & DISCOVERY
    # =========================================================================

    async def phase1_initialization(self) -> None:
        """Phase 1: Initialize project and discover contracts.

        Discovers all Solidity contracts in the project, reads documentation,
        creates output directories, and generates an initial analysis summary.
        """
        logger.info("=" * 80)
        logger.info("PHASE 1: INITIALIZATION & DISCOVERY")
        logger.info("=" * 80)

        self.state.current_phase = "initialization"

        try:
            # Create output directory structure
            create_directory(self.output_dir)
            create_directory(self.output_dir / "contracts")
            create_directory(self.output_dir / "tests")
            create_directory(self.output_dir / "reports")
            logger.info(f"Created output directory: {self.output_dir}")

            # look for .sol files
            # TODO: should we specify this in config instead?
            exclude_dirs = ["node_modules", "test", "tests", "build", "artifacts", "cache"]
            self.state.contracts = find_files_with_extension(
                str(self.project_path), "sol", exclude_dirs
            )

            if not self.state.contracts:
                logger.warning("No Solidity contracts found in project")
            else:
                logger.info(f"Discovered {len(self.state.contracts)} contracts")

            # Read documentation files
            readme_path = self.project_path / "README.md"
            if readme_path.exists():
                self.state.documentation["README"] = read_file(str(readme_path))
                logger.info("Found README.md")
            
            # NOTE: this assumes that other docs are in docs/ dir, might change in the future
            # Look for other documentation
            docs_dir = self.project_path / "docs"
            if docs_dir.exists():
                doc_files = find_files_with_extension(str(docs_dir), ".md")
                for doc_file in doc_files:
                    doc_name = doc_file.stem
                    self.state.documentation[doc_name] = read_file(str(doc_file))
                logger.info(f"Found {len(doc_files)} documentation files")

            # Generate initial analysis summary using LLM
            if self.state.contracts:
                contract_list = [str(c.relative_to(self.project_path)) for c in self.state.contracts]
                doc_list = list(self.state.documentation.keys())

                prompt = prompts.initialization_summary_prompt(
                    contracts=contract_list,
                    docs=doc_list
                )

                # TODO: Call LLM to generate initial summary
                # response = await self.llm.generate_text(prompt)
                # summary = parse_json_llm(response)
                # Write summary to output directory
                # write_file(self.output_dir / "initialization_summary.json", json.dumps(summary, indent=2))

                logger.info("Initial discovery complete")

        except Exception as e:
            logger.error(f"Phase 1 failed: {e}", exc_info=True)
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
        logger.info("=" * 80)
        logger.info("PHASE 2: FILE-LEVEL SEMANTIC ANALYSIS")
        logger.info("=" * 80)

        self.state.current_phase = "file_semantic_analysis"

        if not self.state.contracts:
            logger.warning("No contracts to analyze, skipping Phase 2")
            return

        try:
            logger.info(f"Analyzing {len(self.state.contracts)} contracts")

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
            logger.info(f"Phase 2 complete: {total_findings} findings across {len(self.state.contracts)} contracts")

        except Exception as e:
            logger.error(f"Phase 2 failed: {e}", exc_info=True)
            self.state.errors.append(f"Phase 2: {str(e)}")
            raise

    async def _analyze_single_contract(self, contract_path: Path) -> None:
        """Analyze a single contract file for semantic issues.

        Args:
            contract_path: Path to the contract file
        """
        try:
            contract_name = contract_path.name
            logger.info(f"Analyzing {contract_name}...")

            # Read contract code
            code = read_file(str(contract_path))

            # Generate prompt for semantic analysis
            prompt = prompts.file_semantic_analysis_prompt(
                file_path=str(contract_path.relative_to(self.project_path)),
                code=code
            )

            # TODO: Call LLM for semantic analysis
            # response = await self.llm.generate_text(prompt)
            # findings = parse_json_llm(response)
            # self.state.file_semantic_findings[contract_name] = findings.get("findings", [])

            # For now, initialize empty findings
            # TODO: REMOVE THIS WHEN LLM IS INTEGRATED
            self.state.file_semantic_findings[contract_name] = []

            logger.info(f"Completed analysis of {contract_name}")

        except Exception as e:
            logger.error(f"Failed to analyze {contract_path.name}: {e}")
            self.state.errors.append(f"Phase 2 ({contract_path.name}): {str(e)}")

    # =========================================================================
    # PHASE 3: PROJECT-LEVEL SEMANTIC ANALYSIS
    # =========================================================================

    async def phase3_project_semantic_analysis(self) -> None:
        """Phase 3: Analyze project-level semantic alignment.

        Examines the entire project for alignment with high-level design
        (from README, docs, comments, or docstrings) and performs
        cross-contract analysis.
        """
        logger.info("=" * 80)
        logger.info("PHASE 3: PROJECT-LEVEL SEMANTIC ANALYSIS")
        logger.info("=" * 80)

        self.state.current_phase = "project_semantic_analysis"

        if not self.state.contracts:
            logger.warning("No contracts to analyze, skipping Phase 3")
            return

        try:
            # Always perform project-level analysis
            # Even without explicit docs, contracts may have comments/docstrings
            logger.info("Performing project-level semantic analysis")

            # Combine all documentation (may be empty)
            readme = self.state.documentation.get("README", "No README found")
            other_docs = "\n\n".join([
                f"## {name}\n{content}"
                for name, content in self.state.documentation.items()
                if name != "README"
            ]) or "No additional documentation found"

            contract_names = [c.name for c in self.state.contracts]

            # Generate project-level analysis prompt
            prompt = prompts.project_semantic_analysis_prompt(
                readme=readme,
                all_docs=other_docs,
                contracts=contract_names
            )

            # TODO: Call LLM for project-level analysis
            # response = await self.llm.generate_text(prompt)
            # findings = parse_json_llm(response)
            # self.state.project_semantic_findings = findings.get("findings", [])

            # For now, initialize empty findings
            # TODO: REMOVE THIS WHEN LLM IS INTEGRATED
            self.state.project_semantic_findings = []

            logger.info("Project-level analysis complete")

            # Perform cross-contract analysis if multiple contracts exist
            if len(self.state.contracts) > 1:
                logger.info("Performing cross-contract analysis")

                # Read contract code for cross-contract analysis
                # Limit to avoid context overflow
                max_contracts = 5
                contracts_to_analyze = self.state.contracts[:max_contracts]

                contracts_data = {}
                for contract in contracts_to_analyze:
                    code = read_file(str(contract))
                    contracts_data[contract.name] = code

                if len(self.state.contracts) > max_contracts:
                    logger.info(f"Analyzing {max_contracts} of {len(self.state.contracts)} contracts to avoid context overflow")

                # Generate cross-contract analysis prompt
                prompt = prompts.cross_contract_analysis_prompt(contracts_data)

                # TODO: Call LLM for cross-contract analysis
                # response = await self.llm.generate_text(prompt)
                # findings = parse_json_llm(response)
                # self.state.cross_contract_findings = findings.get("findings", [])

                # For now, initialize empty findings
                # TODO: REMOVE THIS WHEN LLM IS INTEGRATED
                self.state.cross_contract_findings = []

                logger.info("Cross-contract analysis complete")
            else:
                logger.info("Only one contract found, skipping cross-contract analysis")

            total_findings = len(self.state.project_semantic_findings) + len(self.state.cross_contract_findings)
            logger.info(f"Phase 3 complete: {total_findings} project-level findings")

        except Exception as e:
            logger.error(f"Phase 3 failed: {e}", exc_info=True)
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
        logger.info("=" * 80)
        logger.info("PHASE 4: STATIC ANALYSIS")
        logger.info("=" * 80)

        self.state.current_phase = "static_analysis"

        if not self.state.contracts:
            logger.warning("No contracts to analyze, skipping Phase 4")
            return

        try:
            logger.info("Preparing context for LLM-driven static analysis")

            # Prepare contract data
            contract_data = {}
            for contract in self.state.contracts:
                code = read_file(str(contract))
                contract_data[contract.name] = {
                    "code": code,
                    "path": str(contract),  # Absolute path for tool calls
                    "relative_path": str(contract.relative_to(self.project_path))
                }

            # Combine all semantic findings for context
            all_semantic_findings = []
            for contract_name, findings in self.state.file_semantic_findings.items():
                all_semantic_findings.extend(findings)
            all_semantic_findings.extend(self.state.project_semantic_findings)
            all_semantic_findings.extend(self.state.cross_contract_findings)

            # Generate comprehensive prompt for LLM
            prompt = prompts.tool_selection_prompt(
                contract_data=contract_data,
                semantic_findings=all_semantic_findings
            )

            logger.info(f"Invoking LLM with tool access for {len(self.state.contracts)} contracts")

            # TODO: Call LLM with native tool use
            # The LLM will:
            # 1. Analyze the semantic findings and contract data
            # 2. Decide which tools to run on which contracts
            # 3. Call the tools directly via MCP
            # 4. Interpret and consolidate the results
            # 5. Return comprehensive analysis
            #
            # response = await self.llm.generate_with_tools(
            #     prompt=prompt,
            #     tools=prompts.tools_info_prompt()  # Slither and Mythril tool definitions
            # )
            # analysis_results = parse_json_llm(response.content)

            # For now, create placeholder structure
            # TODO: REMOVE THIS WHEN LLM IS INTEGRATED
            analysis_results = {
                "tool_executions": [],
                "findings": [],
                "summary": "Placeholder: LLM will provide analysis summary"
            }

            # Extract and store results from LLM response
            # The LLM's response will include which tools it ran and their results
            for contract in self.state.contracts:
                contract_name = contract.name

                # Initialize results storage
                self.state.static_analysis_results[contract_name] = {
                    "tools_used": [],  # e.g., ["slither", "mythril"]
                    "findings": [],
                    "analysis": "Placeholder"
                }

            # Log what the LLM decided and executed
            logger.info(f"LLM completed static analysis")
            logger.info(f"Tool executions: {len(analysis_results.get('tool_executions', []))}")

            total_findings = len(analysis_results.get("findings", []))
            logger.info(f"Phase 4 complete: {total_findings} static analysis findings")

        except Exception as e:
            logger.error(f"Phase 4 failed: {e}", exc_info=True)
            self.state.errors.append(f"Phase 4: {str(e)}")
            raise

    # =========================================================================
    # PHASE 5: ENDPOINT EXTRACTION
    # =========================================================================

    async def phase5_endpoint_extraction(self) -> None:
        """Phase 5: Extract public/external endpoints from contracts.

        Analyzes each contract to identify all public and external functions,
        events, and state-changing operations. This information is used for
        test generation in Phase 6.
        """
        logger.info("=" * 80)
        logger.info("PHASE 5: ENDPOINT EXTRACTION")
        logger.info("=" * 80)

        self.state.current_phase = "endpoint_extraction"

        if not self.state.contracts:
            logger.warning("No contracts to analyze, skipping Phase 5")
            return

        try:
            logger.info(f"Extracting endpoints from {len(self.state.contracts)} contracts")

            # Extract endpoints concurrently for better performance
            tasks = [
                self._extract_contract_endpoints(contract)
                for contract in self.state.contracts
            ]
            await asyncio.gather(*tasks)

            # Count total endpoints
            total_endpoints = sum(
                len(endpoints) for endpoints in self.state.endpoints.values()
            )
            logger.info(f"Phase 5 complete: {total_endpoints} endpoints extracted")

        except Exception as e:
            logger.error(f"Phase 5 failed: {e}", exc_info=True)
            self.state.errors.append(f"Phase 5: {str(e)}")
            raise

    async def _extract_contract_endpoints(self, contract_path: Path) -> None:
        """Extract endpoints from a single contract.

        Args:
            contract_path: Path to the contract file
        """
        try:
            contract_name = contract_path.name
            logger.info(f"Extracting endpoints from {contract_name}...")

            # Read contract code
            code = read_file(str(contract_path))

            # Generate endpoint extraction prompt
            prompt = prompts.endpoint_extraction_prompt(
                file_path=str(contract_path.relative_to(self.project_path)),
                code=code
            )

            # TODO: Call LLM for endpoint extraction
            # response = await self.llm.generate_text(prompt)
            # endpoints_data = parse_json_llm(response)
            # self.state.endpoints[contract_name] = endpoints_data.get("endpoints", [])

            # For now, initialize empty endpoints
            # TODO: REMOVE THIS WHEN LLM IS INTEGRATED
            self.state.endpoints[contract_name] = []

            logger.info(f"Extracted {len(self.state.endpoints[contract_name])} endpoints from {contract_name}")

        except Exception as e:
            logger.error(f"Failed to extract endpoints from {contract_path.name}: {e}")
            self.state.errors.append(f"Phase 5 ({contract_path.name}): {str(e)}")
