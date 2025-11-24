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
    """Return MCP tool schemas for Slither and Mythril.

    These schemas match the actual tool function signatures in:
    - argus.server.tools.slither.slither()
    - argus.server.tools.mythril.mythril()
    """
    return [
        {
            "name": "slither",
            "description": "Run Slither static analysis on Solidity files. Returns JSON with vulnerabilities found.",
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
                        "description": "Command-line arguments. First arg is target file path (relative to project root), followed by optional flags like --detect, --exclude, --json, etc.",
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
                        "description": "Command-line arguments. First arg should be subcommand ('analyze'), followed by target file (relative to project root), then optional flags like --max-depth, --execution-timeout, etc.",
                    },
                    "kwargs": {
                        "type": "object",
                        "description": "Reserved for future extensibility",
                    },
                },
                "required": ["args"],
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
Analyze this Solidity contract for semantic misalignment between documentation and implementation.

**File**: {file_path}

**Code**:
```solidity
{code}
```

**Analysis Requirements**:
1. Compare inline comments and docstrings with actual implementation
2. Check if access controls match documented intent
3. Verify business logic aligns with described behavior
4. Identify missing security checks mentioned in comments and docstrings

**Output Format** (return as JSON):
```json
{{
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
    readme: str, all_docs: str, contracts: list
) -> str:
    """Generate prompt for project-level semantic analysis."""
    return f"""
Analyze the entire smart contract project for alignment with high-level design.

**README.md**:
{readme}

**Additional Documentation**:
{all_docs}

**Contracts To Analyzed**: {", ".join(contracts)}

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
3. Provide a consolidated summary

**Analysis Guidelines**:
- Contract paths are relative to the project root - use them as-is in tool calls
- Run slither on all contracts (fast, comprehensive)
- Run mythril on contracts with complex logic, fund handling, or access control
- Focus on high/medium severity issues

**After running the tools, return JSON**:
```json
{{
  "tool_executions": [
    {{
      "tool": "slither|mythril",
      "contract": "ContractName.sol",
      "findings": [/* parsed findings */]
    }}
  ],
  "findings": [
    {{
      "contract": "ContractName.sol",
      "severity": "high|medium|low",
      "category": "category name",
      "issue": "description",
      "location": "location",
      "tool": "slither|mythril"
    }}
  ],
  "summary": "Overall analysis summary"
}}
```

Start by running the tools on the contracts.
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
    analysis_md: str, endpoints_md: str, test_results: dict
) -> str:
    """Generate prompt for final report creation."""
    return f"""
Generate a comprehensive security analysis report.

**Input Data**:

1. **Analysis Findings**:
{analysis_md}

2. **Extracted Endpoints**:
{endpoints_md}

3. **Test Results**:
```json
{json.dumps(test_results, indent=2)}
```

**Report Structure**:

# Argus Security Analysis Report
**Generated**: [timestamp]
**Analysis Duration**: [duration]

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

## Detailed Findings

### Semantic Misalignment

[For each semantic finding, include:]

#### 🔴 [SEVERITY] [Title]
- **Confidence**: X/10
- **Location**: File.sol - function() (line X)
- **Description**: [Detailed explanation]
- **Source**: Semantic Analysis
- **Also Detected By**: [If multiple tools found it]
- **Test Generated**: test_name [✓ CONFIRMED | ✗ NOT CONFIRMED]
- **Remediation**:
  ```solidity
  // Suggested fix with code only if confident in solution
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

## Appendix: Raw Analysis Data

[Include full argus-analysis.md content]

---

**Important**:
- DO NOT deduplicate findings. If same vulnerability found by multiple tools, include all assessments
- Use markdown tables for structured data
- Include severity emojis: 🔴 Critical, 🟠 High, 🟡 Medium, 🟢 Low
- Add code snippets for remediation where possible
- Make findings actionable with clear next steps
"""
