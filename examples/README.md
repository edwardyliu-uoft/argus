# Argus Examples

This directory contains example projects demonstrating Argus capabilities and usage patterns.

## Overview

- **[simple-project](#simple-project)**: Minimal example with intentional vulnerabilities
- **[demo-project](#demo-project)**: Complete example with analysis results
- **[example-plugin](#example-plugin)**: Plugin development guide

---

## simple-project

A minimal Hardhat project with a SimpleBank contract for testing Argus analysis.

### Features

- Single contract (`SimpleBank.sol`)
- Basic configuration (`argus.config.json`)
- Intentional vulnerabilities for testing detection

### Known Vulnerabilities

1. **Reentrancy**: `withdraw()` updates balance after external call
2. **Missing Access Control**: `emergencyWithdraw()` has no access restrictions

### Running Argus

From the project directory:

```bash
cd examples/simple-project
argus analyze .
```

Or from the argus root:

```bash
argus analyze examples/simple-project
```

### Expected Behavior

- **Phase 1**: Discovers `SimpleBank.sol` in contracts/
- **Phase 2**: File-level semantic analysis identifies critical functions
- **Phase 3**: Project-level analysis examines fund handling patterns
- **Phase 4**: Static analysis tools (Slither/Mythril) detect vulnerabilities
- **Phase 5**: Extracts public/external function endpoints
- **Phase 6**: Generates test files demonstrating vulnerabilities
- **Phase 7**: Creates comprehensive security report

### Output Structure

```
simple-project/
├── argus/
│   └── YYYYMMDD_HHMMSS/
│       ├── argus-security-report.md
│       └── raw-analysis-data.json
└── test/
    └── Argus.SimpleBank.test.js
```

---

## demo-project

A complete example demonstrating Argus on a multi-contract system with real analysis results.

### Features

- Multiple smart contracts (Claimer, RewardToken, Treasury)
- Complex interactions between contracts
- Comprehensive configuration
- Pre-generated analysis results
- Generated test files

### Contracts

- **RewardToken.sol**: ERC20 token with owner-controlled minting
- **Treasury.sol**: ETH deposit/withdrawal with reward distribution
- **Claimer.sol**: Batch operations for fund claiming

### Configuration Highlights

```json
{
  "orchestrator": {
    "llm": "gemini",
    "cross_contract": {"max_contracts": 10},
    "parallel_test_generation": true
  },
  "generator": {
    "test_generation": {
      "priority_only_threshold": 20,
      "priority_severities": ["critical", "high"]
    }
  }
}
```

### Running Argus

```bash
cd examples/demo-project
argus analyze .
```

### Exploring Results

The demo-project includes pre-generated analysis results:

```bash
# View the security report
cat argus/20251129_221148/argus-security-report.md

# Examine raw analysis data
cat argus/20251129_221148/raw-analysis-data.json

# Check generated tests
ls test/Argus.*.test.js
```

### Generated Tests

- `test/Argus.Claimer.test.js`
- `test/Argus.RewardToken.test.js`
- `test/Argus.Treasury.test.js`

### Running Generated Tests

```bash
npm install
npx hardhat test test/Argus.*.test.js
```

---

## example-plugin

A complete example demonstrating how to create custom Argus plugins.

### Features

- Example MCP tool plugin
- Plugin structure and organization
- Entry point registration
- Configuration handling
- Unit tests for plugins

### Plugin Structure

```
example-plugin/
├── pyproject.toml              # Package metadata and entry points
├── README.md                   # Plugin documentation
├── argus_example_plugin/
│   ├── __init__.py
│   └── plugin.py              # Plugin implementation
└── tests/
    ├── __init__.py
    └── test_plugin.py         # Plugin tests
```

### Installing the Example Plugin

```bash
cd examples/example-plugin
pip install -e .
```

### Using the Plugin

After installation, the plugin is automatically discovered by Argus:

```bash
# The plugin tools are now available during analysis
argus analyze /path/to/project
```

### Creating Your Own Plugin

1. **Copy the example plugin structure**:
   ```bash
   cp -r examples/example-plugin my-argus-plugin
   cd my-argus-plugin
   ```

2. **Update `pyproject.toml`**:
   - Change package name
   - Update entry points
   - Add dependencies

3. **Implement your plugin** in `my_argus_plugin/plugin.py`:
   ```python
   from argus.plugins import MCPToolPlugin
   
   class MyPlugin(MCPToolPlugin):
       @property
       def name(self):
           return "myplugin"
       
       def initialize(self, config=None):
           # Setup your plugin
           self.tools = {"mytool": self.my_tool_function}
           self.initialized = True
   ```

4. **Write tests** in `tests/`

5. **Install and test**:
   ```bash
   pip install -e .
   pytest
   ```

### Plugin Types

The example can be adapted for different plugin types:

- **LLM Provider Plugins** (`argus.llm.providers`): Add new LLM providers
- **MCP Tool Plugins** (`argus.mcp.tools`): Add analysis tools
- **MCP Resource Plugins** (`argus.mcp.resources`): Provide project resources
- **MCP Prompt Plugins** (`argus.mcp.prompts`): Built-in prompt templates

See the main [README.md](../README.md#plugin-system) for detailed plugin documentation.

---

## Testing Examples Locally

### Prerequisites

```bash
# Install Argus
cd /path/to/argus
pip install -e .

# Set up API keys
export ANTHROPIC_API_KEY="your-key"
export GEMINI_API_KEY="your-key"

# Ensure Docker is running
docker ps
```

### Run All Examples

```bash
# Simple project
cd examples/simple-project
argus analyze .

# Demo project
cd ../demo-project
argus analyze .

# Test generated tests
npm install
npx hardhat test
```

### Clean Up Results

```bash
# Remove generated analysis results
rm -rf examples/*/argus/YYYYMMDD_HHMMSS/

# Remove generated tests (be careful!)
rm -f examples/*/test/Argus.*.test.js
```

---

## Need Help?

- **Documentation**: See main [README.md](../README.md)
- **Issues**: https://github.com/calebchin/argus/issues
- **Configuration**: Check `argus.config.json` in each example
- **Verbose Logging**: Run with `argus analyze . --verbose`
