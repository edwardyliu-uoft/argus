"""Prompts for test generation phase."""

import json
from typing import List, Dict
from pathlib import Path


def test_generation_prompt(
    contract_name: str,
    contract_code: str,
    contract_endpoints: List[Dict],
    contract_findings: List[Dict],
    project_semantic_findings: List[Dict],
    output_path: Path,
) -> str:
    """Build comprehensive prompt for test generation.

    Includes:
    - Full project-level semantic analysis (always included for context)
    - Contract code and endpoints
    - Contract-specific findings
    - Instructions for writing tests with filesystem tools

    Args:
        contract_name: Name of the contract (without .sol)
        contract_code: Contract source code
        contract_endpoints: Extracted function endpoints
        contract_findings: Contract-specific findings
        project_semantic_findings: Project-level semantic findings
        output_path: Path where test file should be written

    Returns:
        Complete prompt string
    """
    # Build context sections
    sections = []

    # Section 1: Project-level semantic analysis (ALWAYS included)
    sections.append("## Project-Level Semantic Analysis\n")
    sections.append("**Important**: The following findings apply to the entire project and provide important context.\n")

    if project_semantic_findings:
        sections.append("**Project Findings**:")
        sections.append(json.dumps(project_semantic_findings, indent=2))
    else:
        sections.append("No project-level semantic findings.")

    # Section 2: Contract details
    sections.append(f"\n## Contract: {contract_name}\n")
    sections.append("**Source Code**:")
    sections.append(f"```solidity\n{contract_code}\n```\n")

    sections.append("**Endpoints**:")
    sections.append(json.dumps(contract_endpoints, indent=2))

    # Section 3: Contract-specific findings
    sections.append("\n## Contract-Specific Vulnerabilities\n")
    if contract_findings:
        sections.append(json.dumps(contract_findings, indent=2))
    else:
        sections.append("No contract-specific findings.")

    # Section 4: Instructions
    sections.append("\n## Your Task\n")
    sections.append(f"""
Generate comprehensive Hardhat test cases for the {contract_name} contract that:

1. **Demonstrate all vulnerabilities** found in the analysis (both contract-specific and relevant project-level issues)
2. **Use the filesystem tools** to write the test file directly
3. **Follow Hardhat/Ethers.js syntax** exactly

**Test File Requirements**:
- File path: `{output_path}`
- Use describe/it blocks
- Include setup in beforeEach
- Each test should demonstrate a specific vulnerability
- Include comments explaining what each test demonstrates
- Tests should either PASS (exploit works) or FAIL (invariant broken) - document which

**Test Structure Template**:
```javascript
const {{ expect }} = require("chai");
const {{ ethers }} = require("hardhat");

describe("{contract_name} Security Tests", function() {{
  let contract;
  let owner, attacker, user;

  beforeEach(async function() {{
    [owner, attacker, user] = await ethers.getSigners();
    const Contract = await ethers.getContractFactory("{contract_name}");
    contract = await Contract.deploy();
  }});

  it("Should demonstrate [vulnerability name]", async function() {{
    // Setup: Prepare the exploit scenario

    // Exploit: Execute the attack

    // Assert: Verify the exploit worked (test should PASS if vulnerability exists)
  }});
}});
```

**IMPORTANT**:
- Use the `write_file` tool to create the test file at the path specified above
- Make sure to write valid JavaScript/Hardhat test code
- Focus on the most critical vulnerabilities first
- Each test should be clear and well-commented
""")

    return "\n".join(sections)
