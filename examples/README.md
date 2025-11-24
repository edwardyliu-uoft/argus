# Argus Examples

This directory contains example projects for testing Argus.

## test-project

A minimal Hardhat project with a SimpleBank contract for testing orchestrator phases 1-4.

**Known vulnerabilities** (for testing detection):
1. **Reentrancy**: `withdraw()` updates balance after external call
2. **Missing Access Control**: `emergencyWithdraw()` has no access restrictions

### Running Argus on test-project

From the argus root directory:

```bash
# Make sure MCP server tools are configured
# Then run orchestrator
python -m argus.cli analyze examples/test-project
```

### Expected Behavior

- **Phase 1**: Discover SimpleBank.sol in contracts/
- **Phase 2**: File-level semantic analysis identifies critical functions
- **Phase 3**: Project-level analysis identifies fund handling patterns
- **Phase 4**: LLM intelligently selects and runs Slither/Mythril to detect vulnerabilities
