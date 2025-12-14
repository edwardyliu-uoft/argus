# NOTE: THIS COULD ALSO BECOME ITS OWN MODULE
"""
Prompt templates for LLM API calls.
All prompts should be clear, structured, and return parseable output.

Prompts are organized by the orchestration phase in which they are used:
- Phase 1: Initialization & Discovery
- Phase 2: File-level Semantic Analysis
- Phase 3: Project-level Semantic Analysis
- Phase 4: Static Analysis (Slither/Mythril)
- Phase 5: Endpoint Extraction
- Phase 6: Test Generation & Execution
- Phase 7: Report Generation
"""

import json


# =============================================================================
# PHASE 1: INITIALIZATION & DISCOVERY
# =============================================================================


def tools_info_prompt() -> str:
    """Return MCP tool schemas for Slither, Mythril, and query_slither_results.

    These schemas match the actual tool function signatures in:
    - argus.server.tools.slither.slither()
    - argus.server.tools.slither.query_slither_results()
    - argus.server.tools.mythril.mythril()
    """
    return [
        {
            "name": "slither",
            "description": "Run Slither static analysis on Solidity files. Returns a SUMMARY with total findings count and a results_file path. Use query_slither_results to retrieve actual findings.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Slither command to execute (default: 'slither')",
                        "default": "slither",
                    },
                    "args": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": """Array of command-line arguments for slither.

REQUIRED FORMAT - args must be an array with at least 3 elements:
  args = [<target_file>, "--json", "-"]

Examples:
  ✓ CORRECT: args=["contracts/Token.sol", "--json", "-"]
  ✓ CORRECT: args=["contracts/Treasury.sol", "--json", "-", "--detect", "reentrancy-eth"]
  ✗ WRONG: args=["contracts/Token.sol"] (missing --json -)
  ✗ WRONG: args=["contracts/Token.sol", "--json"] (missing trailing -)
  ✗ WRONG: args=["contracts/Token.sol", "--json", "output.json"] (must use - for stdout)

Explanation:
  - Element [0]: Target file path, relative to project root (e.g., "contracts/Token.sol")
  - Elements [1-2]: MUST be "--json" and "-" to output JSON to stdout
  - Elements [3+]: Optional detector flags like "--detect", "--exclude", etc.

The "--json -" flags are REQUIRED for the tool to return parseable results.""",
                    },
                    "kwargs": {
                        "type": "object",
                        "description": "Reserved for future extensibility",
                    },
                },
                "required": ["args"],
            },
        },
        {
            "name": "mythril",
            "description": "Run Mythril symbolic execution on Ethereum files. Returns JSON with security issues found.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Mythril command to execute (default: 'myth')",
                        "default": "myth",
                    },
                    "args": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": """Array of command-line arguments for mythril.

REQUIRED FORMAT - args must be an array with at least 4 elements:
  args = ["analyze", <target_file>, "-o", "json"]

Examples:
  ✓ CORRECT: args=["analyze", "contracts/Token.sol", "-o", "json"]
  ✓ CORRECT: args=["analyze", "contracts/Treasury.sol", "-o", "json", "--execution-timeout", "300"]
  ✗ WRONG: args=["analyze", "contracts/Token.sol"] (missing -o json)
  ✗ WRONG: args=["contracts/Token.sol", "-o", "json"] (missing 'analyze' subcommand)
  ✗ WRONG: args=["analyze", "contracts/Token.sol", "--json"] (use -o json, not --json)

Explanation:
  - Element [0]: MUST be "analyze" (mythril subcommand)
  - Element [1]: Target file path, relative to project root (e.g., "contracts/Token.sol")
  - Elements [2-3]: MUST be "-o" and "json" to output JSON format
  - Elements [4+]: Optional flags like "--execution-timeout", "--max-depth", etc.

The "analyze" subcommand and "-o json" flags are REQUIRED for the tool to return parseable results.""",
                    },
                    "kwargs": {
                        "type": "object",
                        "description": "Reserved for future extensibility",
                    },
                },
                "required": ["args"],
            },
        },
        {
            "name": "query_slither_results",
            "description": "Query Slither results with server-side filtering. Use this to retrieve findings from a saved Slither results file in chunks, filtered by severity, detector type, or contract.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "results_file": {
                        "type": "string",
                        "description": "Path to the slither-full-results.json file (obtained from slither tool's results_file field)",
                    },
                    "severity": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": 'Filter by severity levels. Valid values: ["High", "Medium", "Low", "Informational", "Optimization"]. Example: ["High", "Medium"]',
                    },
                    "detector_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": 'Filter by detector names. Example: ["reentrancy-eth", "arbitrary-send", "controlled-delegatecall"]',
                    },
                    "contracts": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": 'Filter by contract names. Example: ["Visor", "Hypervisor"]',
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of findings to return (default: 50). Use smaller limits to avoid context overflow.",
                        "default": 50,
                    },
                },
                "required": ["results_file"],
            },
        },
    ]


def initialization_summary_prompt(contracts: list, docs: list) -> str:
    """Generate prompt for initial project discovery summary."""
    return f"""
Analyze the discovered smart contract project structure and suggest analysis priorities.

**Discovered Contracts**:
{json.dumps(contracts, indent=2)}

**Discovered Documentation Files**:
{json.dumps(docs, indent=2)}

**Analysis Requirements**:
1. Categorize contracts by complexity (simple/medium/complex)
2. Identify core vs peripheral contracts
3. Suggest analysis priority order
4. Estimate potential risk areas based on file names and count

**Output Format** (return as JSON):
```json
{{
  "contracts": [
    {{
      "path": "contracts/Token.sol",
      "complexity": "simple|medium|complex",
      "category": "core|peripheral|test",
      "priority": <1-10>,
      "risk_indicators": ["handles_funds", "upgradeable", "complex_logic"]
    }}
  ],
  "overall_priority": "critical|high|medium|low",
  "suggested_order": ["Contract1.sol", "Contract2.sol"],
  "observations": "Brief overview of project structure"
}}
```

Return ONLY valid JSON, no additional text.
"""


# =============================================================================
# PHASE 2: FILE-LEVEL SEMANTIC ANALYSIS
# =============================================================================


def file_semantic_analysis_prompt(file_path: str, code: str) -> str:
    """Generate prompt for file-level semantic analysis."""
    return f"""
You have two tasks for this Solidity contract:
1. **Classify** the contract to determine if it needs further in-depth analysis in subsequent phases
2. **Analyze** it for semantic misalignment between documentation and implementation

**File**: {file_path}

**Code**:
```solidity
{code}
```

**TASK 1: Classification Requirements**:
Classify this contract to determine if it warrants further in-depth analysis (static analysis, test generation, etc.):

1. **Standard Library Detection**:
   - Check for standard library imports (@openzeppelin/contracts, @solmate, @chainlink)
   - Identify if contract inherits from well-known base contracts:
     * ERC20, ERC721, ERC1155, ERC4626 (token standards)
     * Ownable, AccessControl, Pausable (access patterns)
     * ReentrancyGuard, SafeMath (security utilities)
   - If contract ONLY inherits standard patterns WITHOUT custom logic → mark as standard_library
   - If contract extends standard libraries WITH custom business logic → analyze further

2. **Test/Mock Contract Detection**:
   - Check for test-related naming patterns: "Mock", "Test", "Fake", "Stub", "Attacker", "Helper"
   - Check if file path contains "test", "mock", or "test-helpers" directories
   - Mark as test_contract or mock_contract accordingly

3. **Interface-Only Detection**:
   - Check if contract is an interface (interface keyword)
   - Interfaces have no implementation, only function signatures
   - Should skip further analysis (no exploitable logic)

4. **Complexity Assessment**:
   - **simple**: < 100 lines, basic CRUD operations, minimal state management, no fund handling
   - **medium**: 100-300 lines, moderate logic, state management, some external calls
   - **complex**: > 300 lines, complex state machines, heavy cross-contract interaction, fund management

5. **Further Analysis Decision - should_analyze_further**:

   **ANALYZE (true) if**:
   - Contract has custom business logic beyond standard patterns
   - Handles funds (deposits, withdrawals, transfers, payments)
   - Has custom access control beyond standard Ownable
   - Implements novel mechanisms or algorithms
   - Has any concerning patterns identified in initial review
   - Extends standard library with meaningful additions
   - Is a core protocol contract

   **SKIP (false) if**:
   - Pure standard library implementation with no modifications
   - Test helper or mock contract
   - Simple getter/setter contract with no security implications
   - Interface-only contract (no implementation)
   - Unmodified OpenZeppelin/Solmate/Chainlink import

   **Confidence Score**:
   - Rate your confidence in this classification from 1-10
   - 10 = certain (e.g., exact OpenZeppelin ERC20 with no changes)
   - 5 = uncertain (e.g., complex inheritance, unclear if custom logic exists)
   - 1 = very uncertain (e.g., insufficient context, ambiguous code)
   - Only skip contracts with confidence >= 7

**TASK 2: Semantic Analysis Requirements**:
1. Compare inline comments and docstrings with actual implementation
2. Check if access controls match documented intent
3. Verify business logic aligns with described behavior
4. Identify missing security checks mentioned in comments and docstrings

**Output Format** (return as JSON with BOTH classification and findings):
```json
{{
  "contract_classification": {{
    "is_standard_library": <boolean>,
    "library_type": null | "openzeppelin" | "solmate" | "chainlink" | "other",
    "is_test_contract": <boolean>,
    "is_mock_contract": <boolean>,
    "complexity": "simple" | "medium" | "complex",
    "should_analyze_further": <boolean>,
    "skip_reason": null | "standard_library" | "test_helper" | "minimal_logic" | "interface_only",
    "confidence": <1-10>
  }},
  "findings": [
    {{
      "type": "semantic_misalignment",
      "location": "function_name or line_number",
      "description": "detailed explanation of the misalignment",
      "confidence": <1-10>,
      "severity": "critical|high|medium|low",
      "evidence": {{
        "documented": "what the documentation says",
        "actual": "what the code does"
      }}
    }}
  ]
}}
```

Return ONLY valid JSON, no additional text.
"""


# =============================================================================
# PHASE 3: PROJECT-LEVEL SEMANTIC ANALYSIS
# =============================================================================


def project_semantic_analysis_prompt(
    readme: str, all_docs: str, contracts: dict
) -> str:
    """Generate prompt for project-level semantic analysis.

    Args:
        readme: README.md content
        all_docs: Additional documentation
        contracts: Dict mapping contract names to their source code
    """
    # Format contracts for the prompt
    contracts_text = "\n\n".join(
        [f"**{name}**:\n```solidity\n{code}\n```" for name, code in contracts.items()]
    )

    return f"""
Analyze the entire smart contract project for alignment with high-level design.

**README.md**:
{readme}

**Additional Documentation**:
{all_docs}

**Contracts**:
{contracts_text}

**Analysis Requirements**:
1. Check if overall architecture matches README description
2. Analyze cross-contract interaction patterns if feasible
3. Identify missing components mentioned in documentation
4. Verify consistent behavior across contracts

If cross-contract analysis is too complex, analyze each contract individually against the README.

**Output Format** (return as JSON):
```json
{{
  "findings": [
    {{
      "type": "semantic_misalignment|architecture_mismatch|missing_component",
      "scope": "project|contract_name",
      "description": "detailed explanation",
      "confidence": <1-10>,
      "severity": "critical|high|medium|low"
    }}
  ]
}}
```

Return ONLY valid JSON, no additional text.
"""


def cross_contract_analysis_prompt(contracts_data: dict) -> str:
    """Generate prompt for analyzing interactions between multiple contracts."""
    contracts_list = "\n\n".join(
        [
            f"**{name}**:\n```solidity\n{code}\n```"
            for name, code in contracts_data.items()
        ]
    )

    return f"""
Analyze interactions and dependencies between multiple smart contracts in this project.

**Contracts**:
{contracts_list}

**Analysis Requirements**:
1. Identify all cross-contract calls and interactions
2. Check for privilege escalation vulnerabilities across contracts
3. Verify consistent state assumptions between contracts
4. Find reentrancy vulnerabilities in multi-contract call chains
5. Detect circular dependencies or deadlock potential
6. Analyze access control across contract boundaries

**Output Format** (return as JSON):
```json
{{
  "interaction_graph": {{
    "nodes": ["Contract1", "Contract2"],
    "edges": [
      {{
        "from": "Contract1",
        "to": "Contract2",
        "method": "function_name",
        "type": "call|delegatecall|staticcall"
      }}
    ]
  }},
  "findings": [
    {{
      "type": "privilege_escalation|reentrancy|state_inconsistency|circular_dependency",
      "contracts_involved": ["Contract1", "Contract2"],
      "description": "Detailed explanation of the vulnerability",
      "attack_scenario": "Step-by-step exploit path",
      "severity": "critical|high|medium|low",
      "confidence": <1-10>,
      "remediation": "Suggested fix"
    }}
  ],
  "dependencies": [
    {{"contract": "Contract1", "depends_on": ["Contract2", "Contract3"]}}
  ],
  "summary": "Overall assessment of cross-contract security"
}}
```

Return ONLY valid JSON, no additional text.
"""


# =============================================================================
# PHASE 4: STATIC ANALYSIS (SLITHER/MYTHRIL)
# =============================================================================


def tool_selection_prompt(contract_data: dict, semantic_findings: list) -> str:
    """Generate prompt for LLM to decide which static analysis tools to run."""
    # Get contract file paths for tool calling (use relative paths for Docker compatibility)
    contract_paths = "\n".join(
        [
            f"- {name}: {data.get('relative_path', data.get('path', 'unknown'))}"
            for name, data in contract_data.items()
        ]
    )

    return f"""
You are a smart contract security analyzer with access to static analysis tools. Analyze the contracts and USE the tools to find vulnerabilities.

**Contracts to Analyze**:
{contract_paths}

**Semantic Analysis Findings**:
```json
{json.dumps(semantic_findings, indent=2)}
```

**Your Task**:
1. **RUN the slither and mythril tools** on the contracts (use tool calling)
2. Analyze the tool outputs to identify vulnerabilities
3. **CRITICAL**: After running all tools, return your final response as valid JSON

**IMPORTANT RESTRICTIONS**:
- DO NOT modify, write to, or edit any contract files (.sol files)
- DO NOT create, modify, or delete any files in the project
- ONLY use read operations (read_file, list_directory) and security tools (slither, mythril)
- Your role is to ANALYZE existing code, not to modify it

**Analysis Guidelines**:
- **CRITICAL**: Run Slither ONCE on the entire project with path filtering
  - Slither needs full project context (all imports, cross-contract interactions)
  - Use: slither(args=[".", "--include-paths", "path1|path2|path3", "--json", "-"])
  - The "." analyzes full project with all dependencies resolved
  - --include-paths uses regex to limit results to specific contracts (use | as separator)
  - Example: slither(args=[".", "--include-paths", "contracts/Visor.sol|contracts/Mainframe.sol", "--json", "-"])
  - **IMPORTANT**: Slither will return a SUMMARY (not full findings) with:
    - total_findings: Total number of vulnerabilities found
    - by_severity: Count of findings by severity level
    - by_detector: Count of findings by detector type
    - results_file: Path to the full results JSON file

- **Query Slither results iteratively** using query_slither_results tool:
  - After running slither, use query_slither_results to retrieve findings in chunks
  - Start with high-severity: query_slither_results(results_file="path/from/summary", severity=["High"])
  - Then medium: query_slither_results(results_file="...", severity=["Medium"], limit=20)
  - Query specific detectors if needed: query_slither_results(results_file="...", detector_types=["reentrancy-eth"])
  - This prevents hitting size limits and lets you prioritize critical findings
  - The tool returns: findings (array), total_found, total_available, truncated (bool)

- Run mythril selectively on 2-3 highest-risk contracts (if time permits)
  - Mythril is much slower, so only target contracts with critical vulnerabilities
  - Use: mythril(args=["contracts/path/to/Contract.sol"])

- Focus on high/medium severity issues from tools

**CRITICAL - Final Response Format**:
After running all tools, return ONLY a JSON object. DO NOT wrap in markdown code blocks.
Your response must start with {{ and end with }}.

Return ONLY a JSON object of the following structure:

```json
{{
  "vulnerabilities": [
    {{
      "contract": "ContractName.sol",
      "tool": "slither|mythril",
      "severity": "High|Medium|Low",
      "name": "vulnerability-name",
      "description": "detailed description of the issue",
      "sourceMap": "ContractName.sol#line-numbers"
    }}
  ],
  "summary": "Overall analysis summary describing what was found"
}}
```

MANDATORY RULES:
1. Top-level keys: "vulnerabilities" (array) and "summary" (string)
2. Each vulnerability MUST include: contract, tool, severity, name, description
3. severity should be "High", "Medium", or "Low" (capitalize first letter)
4. tool should be "slither" or "mythril" (the tool that found it)
5. Use actual contract names from the contracts list above
6. Include sourceMap with file path and line numbers when available

Run the tools now. You are restricted to ONLY return the JSON with no additional text.
"""


def additional_tool_recommendation_prompt(
    initial_findings: dict, contracts_analyzed: list
) -> str:
    """Generate prompt for recommending additional tools after initial analysis."""
    return f"""
Review the initial static analysis results and recommend additional analysis if needed.

**Initial Analysis Results**:
```json
{json.dumps(initial_findings, indent=2)}
```

**Contracts Analyzed**: {", ".join(contracts_analyzed)}

**Recommendation Criteria**:
1. **Incomplete Coverage**: Initial tools missed certain vulnerability types
2. **High Complexity**: Findings suggest deeper analysis needed
3. **Timeout Issues**: Tool timed out, needs different approach or parameters
4. **Contradictory Results**: Different tools disagree, need clarification

**Available Actions**:
- Run Mythril with extended timeout/depth on specific contracts
- Run Slither with different detectors enabled
- Rerun with modified parameters

**Output Format** (return as JSON):
```json
{{
  "needs_additional_analysis": true,
  "additional_tools": [
    {{
      "contract": "DEX.sol",
      "tool": "mythril",
      "additional_args": ["--max-depth", "20", "--solver-timeout", "60000"],
      "reasoning": "Initial analysis timed out on complex swap logic",
      "priority": "high"
    }}
  ],
  "sufficient_analysis": [
    {{
      "contract": "Token.sol",
      "reasoning": "Both tools agree, comprehensive coverage achieved"
    }}
  ]
}}
```

Return ONLY valid JSON, no additional text.
"""


def static_analysis_interpretation_prompt(
    tool_name: str, raw_results: str, contract_code: str
) -> str:
    """Generate prompt for interpreting static analysis tool output."""
    return f"""
Interpret the output from {tool_name} static analysis tool in the context of the contract code.

**Tool**: {tool_name}

**Raw Tool Output**:
```json
{raw_results}
```

**Contract Code**:
```solidity
{contract_code}
```

**Analysis Requirements**:
1. Explain each finding in plain language
2. Identify potential false positives (with reasoning)
3. Assess actual exploitability of each finding
4. Prioritize findings by real-world impact
5. Suggest remediation approaches

**Output Format** (return as JSON):
```json
{{
  "interpreted_findings": [
    {{
      "original_id": "tool-specific-id",
      "title": "Clear vulnerability title",
      "description": "Plain language explanation",
      "is_false_positive": false,
      "false_positive_reasoning": "Why this might be FP (if applicable)",
      "exploitability": "high|medium|low|none",
      "real_world_impact": "Detailed impact assessment",
      "confidence": <1-10>,
      "severity": "critical|high|medium|low",
      "remediation": "Suggested fix approach"
    }}
  ],
  "summary": "Overall assessment of tool findings",
  "priority_order": ["finding_id_1", "finding_id_2"]
}}
```

Return ONLY valid JSON, no additional text.
"""


def vulnerability_correlation_prompt(
    semantic_findings: list, static_findings: list
) -> str:
    """Generate prompt for identifying overlaps between analysis methods without deduplication."""
    return f"""
Analyze vulnerability findings from semantic analysis and static analysis tools to identify overlaps.

**IMPORTANT**: Do NOT deduplicate or merge findings. Keep all findings separate. Only identify which findings refer to the same underlying issue.

**Semantic Analysis Findings**:
```json
{json.dumps(semantic_findings, indent=2)}
```

**Static Analysis Findings** (from Slither/Mythril):
```json
{json.dumps(static_findings, indent=2)}
```

**Analysis Requirements**:
1. Identify which findings from different tools refer to the same vulnerability
2. Note agreement/disagreement between tools on severity
3. Preserve all findings separately (do not merge or deduplicate)
4. Suggest overall priority based on tool consensus

**Output Format** (return as JSON):
```json
{{
  "overlapping_findings": [
    {{
      "semantic_finding_id": "id from semantic analysis",
      "static_finding_ids": ["id from slither", "id from mythril"],
      "agreement_level": "full|partial|conflicting",
      "severity_consensus": "critical|high|medium|low|mixed",
      "notes": "How the findings relate to each other"
    }}
  ],
  "all_findings_preserved": true,
  "suggested_review_order": [
    {{
      "finding_id": "...",
      "source": "semantic|slither|mythril",
      "priority": <1-10>,
      "reasoning": "Why this should be reviewed in this order"
    }}
  ],
  "summary": "Overall analysis of finding coverage"
}}
```

Return ONLY valid JSON, no additional text.
"""


# =============================================================================
# PHASE 5: ENDPOINT EXTRACTION
# =============================================================================


def endpoint_extraction_prompt(file_path: str, code: str) -> str:
    """Generate prompt for extracting contract endpoints."""
    return f"""
Extract all public/external endpoints from this Solidity contract.

**File**: {file_path}

**Code**:
```solidity
{code}
```

**Include**:
- External and public functions
- Event emissions
- Fallback and receive functions

**Output Format** (return as JSON array):
```json
[
  {{
    "name": "function_name",
    "params": [
      {{"name": "param_name", "type": "address"}},
      {{"name": "amount", "type": "uint256"}}
    ],
    "modifiers": ["onlyOwner", "nonReentrant"],
    "visibility": "external",
    "mutability": "nonpayable|payable|view|pure"
  }}
]
```

Return ONLY valid JSON, no additional text.
"""


# =============================================================================
# PHASE 6: TEST GENERATION & EXECUTION
# =============================================================================


def test_generation_prompt(
    contract_name: str, endpoints: list, vulnerabilities: list
) -> str:
    """Generate prompt for creating test cases."""
    return f"""
Generate Hardhat test cases for the {contract_name} contract to demonstrate vulnerabilities.

**Endpoints**:
```json
{json.dumps(endpoints, indent=2)}
```

**Vulnerabilities to Test**:
```json
{json.dumps(vulnerabilities, indent=2)}
```

**Requirements**:
1. Create test cases that demonstrate each vulnerability
2. Use Hardhat/Ethers.js syntax
3. Include setup, exploit, and assertion
4. Tests should either PASS (exploit works) or FAIL (invariant broken) - document which is used

**Example Test Structure**:
```javascript
const {{ expect }} = require("chai");
const {{ ethers }} = require("hardhat");

describe("{contract_name} Security Tests", function() {{
  let contract;
  let owner, attacker;

  beforeEach(async function() {{
    [owner, attacker] = await ethers.getSigners();
    const Contract = await ethers.getContractFactory("{contract_name}");
    contract = await Contract.deploy();
  }});

  it("Should demonstrate [vulnerability]", async function() {{
    // Setup
    // Exploit
    // Assert
  }});
}});
```

**Output**: Return complete JavaScript test file code.
"""


def test_failure_analysis_prompt(
    test_code: str, failure_output: str, contract_code: str
) -> str:
    """Generate prompt for analyzing why a generated test failed."""
    return f"""
Analyze why a generated security test failed and determine the root cause.

**Test Code**:
```javascript
{test_code}
```

**Failure Output**:
```
{failure_output}
```

**Contract Code**:
```solidity
{contract_code}
```

**Analysis Requirements**:
1. Determine the root cause of test failure
2. Classify failure type:
   - Bug in test code (test needs fixing)
   - Vulnerability doesn't actually exist (false positive)
   - Test environment/setup issue
   - Contract behavior different than expected
3. Suggest specific fixes if test code is wrong
4. Update vulnerability assessment if it's a false positive

**Output Format** (return as JSON):
```json
{{
  "diagnosis": "detailed explanation of what went wrong",
  "failure_type": "test_bug|false_positive|environment|unexpected_behavior",
  "root_cause": "Specific reason for failure",
  "vulnerability_exists": true,
  "vulnerability_assessment": "Updated assessment of the vulnerability",
  "suggested_fix": {{
    "type": "test_code|contract_code|environment",
    "code": "Corrected code (if applicable)",
    "explanation": "Why this fix works"
  }},
  "confidence": <1-10>
}}
```

Return ONLY valid JSON, no additional text.
"""


# =============================================================================
# PHASE 7: REPORT GENERATION
# =============================================================================


def report_generation_prompt(
    timestamp: str,
    duration: float,
    file_semantic_findings: dict,
    project_semantic_findings: list,
    cross_contract_findings: list,
    static_analysis_results: dict,
    endpoints: dict,
    test_results: dict,
    contracts: list,
    contracts_skipped: list,
    contracts_metadata: dict,
) -> str:
    """Generate prompt for final comprehensive report creation.

    Args:
        timestamp: Analysis start timestamp
        duration: Analysis duration in seconds
        file_semantic_findings: Phase 2 file-level semantic findings
        project_semantic_findings: Phase 3 project-level semantic findings
        cross_contract_findings: Phase 3 cross-contract findings
        static_analysis_results: Phase 4 static analysis results
        endpoints: Phase 5 extracted endpoints
        test_results: Phase 6 test execution results
        contracts: List of analyzed contracts
        contracts_skipped: List of contracts skipped during filtering
        contracts_metadata: Classification metadata for all contracts
    """
    return f"""
Generate a comprehensive security analysis report based on the multi-phase analysis results.

**Analysis Metadata**:
- **Timestamp**: {timestamp}
- **Duration**: {duration:.1f} seconds
- **Contracts Analyzed**: {', '.join([c.name for c in contracts])}
- **Contracts Skipped**: {len(contracts_skipped)}

**Contracts Metadata** (Classification Info):
```json
{json.dumps(contracts_metadata, indent=2)}
```

**Contracts Skipped** ({len(contracts_skipped)} total):
{', '.join([c.name for c in contracts_skipped]) if contracts_skipped else 'None'}

**Phase 2 - File-Level Semantic Findings**:
```json
{json.dumps(file_semantic_findings, indent=2)}
```

**Phase 3 - Project-Level Semantic Findings**:
```json
{json.dumps(project_semantic_findings, indent=2)}
```

**Phase 3 - Cross-Contract Findings**:
```json
{json.dumps(cross_contract_findings, indent=2)}
```

**Phase 4 - Static Analysis Results**:
```json
{json.dumps(static_analysis_results, indent=2)}
```

**Phase 5 - Extracted Endpoints**:
```json
{json.dumps(endpoints, indent=2)}
```

**Phase 6 - Test Results**:
```json
{json.dumps(test_results, indent=2)}
```

---

**Your Task**: Generate a comprehensive markdown report following this structure:

# Argus Security Analysis Report
**Generated**: {timestamp}
**Analysis Duration**: {duration:.1f}s

---

## Executive Summary

**Total Vulnerabilities**: X
**Severity Breakdown**:
- 🔴 Critical: X
- 🟠 High: X
- 🟡 Medium: X
- 🟢 Low: X

**Key Findings**:
1. [Most critical finding]
2. [Second most critical]
3. ...

---

## Contract Analysis Scope

**Total Contracts Discovered**: {len(contracts) + len(contracts_skipped)}
**Contracts Analyzed In-Depth**: {len(contracts)}
**Contracts Skipped**: {len(contracts_skipped)}

### Analyzed Contracts
{chr(10).join([f"- **{c.name}** - Complexity: {contracts_metadata.get(c.name, {}).get('complexity', 'unknown') if c.name in contracts_metadata else 'unknown'}" for c in contracts])}

### Skipped Contracts
{chr(10).join([f"- **{c.name}** - Reason: {contracts_metadata.get(c.name, {}).get('skip_reason', 'N/A') if c.name in contracts_metadata else 'N/A'} (Confidence: {contracts_metadata.get(c.name, {}).get('confidence', 0) if c.name in contracts_metadata else 0}/10)" for c in contracts_skipped]) if contracts_skipped else 'None'}

**Note**: Skipped contracts were excluded from in-depth static analysis and test generation based on automated classification. They may still appear in project-level semantic analysis if they interact with analyzed contracts.

---

## Detailed Findings

### Semantic Misalignment

[For each semantic finding, include:]

#### 🔴 [SEVERITY] [Title]
- **Confidence**: X/10
- **Location**: File.sol - function() (line X)
- **Description**: [Detailed explanation]
- **Source**: Semantic Analysis (File-level / Project-level / Cross-contract)
- **Also Detected By**: [If multiple tools found it]
- **Test Generated**: test_name [✓ CONFIRMED | ✗ NOT CONFIRMED | ⊘ NOT TESTED]
- **Remediation**:
  ```solidity
  // Suggested fix with code
  ```
- **References**: [Links if available]

---

### Slither Findings

[Same format as above for each Slither finding]

---

### Mythril Findings

[Same format as above for each Mythril finding]

---

## Test Results Summary

**Tests Generated**: X
**Tests Passed**: X (vulnerabilities confirmed)
**Tests Failed**: X (expected behavior)

| Test File | Test Case | Status | Vulnerability Confirmed |
|-----------|-----------|--------|------------------------|
| ... | ... | ... | ... |

---

## Appendix: Contract Endpoints

[List all extracted endpoints by contract]

---

**CRITICAL REQUIREMENTS**:
- **DO NOT deduplicate findings** - If the same vulnerability was found by multiple tools, include ALL assessments separately
- Use markdown tables for structured data
- Include severity emojis: 🔴 Critical, 🟠 High, 🟡 Medium, 🟢 Low
- Add code snippets for remediation where possible
- Make findings actionable with clear next steps
- Cross-reference findings with test results where applicable
- Focus on actionable insights, not raw data dumps

**Output**: Return the complete markdown report as a single string.
"""
