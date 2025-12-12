# Argus

**Argus** is an LLM-powered smart contract security tool that performs automated security analysis and test generation for Ethereum smart contracts. It combines semantic analysis with traditional static analysis tools (Slither, Mythril) to identify vulnerabilities and automatically generates Hardhat test cases that demonstrate potential exploits.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)

## Features

- 🔍 **Semantic Analysis**: Uses LLMs to detect misalignment between documentation and implementation
- 🛠️ **Static Analysis Integration**: Runs Slither and Mythril via Docker containers
- 🧪 **Automated Test Generation**: Creates Hardhat tests that prove vulnerabilities
- 📊 **Multi-phase Analysis**: 7-phase orchestrated workflow for comprehensive security review
- 🔌 **Plugin System**: Extensible architecture for LLM providers and analysis tools
- 🌐 **MCP Server**: Model Context Protocol server for tool communication
- 📝 **Detailed Reports**: Generates markdown reports with findings and proof-of-concept tests

## Table of Contents

- [How It Works](#how-it-works)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Usage](#usage)
- [Plugin System](#plugin-system)
- [Development](#development)
- [Testing](#testing)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## How It Works

Argus performs a 7-phase analysis workflow:

### Phase 1: Initialization & Discovery
- Discovers Solidity contracts in the project
- Reads README and documentation files
- Creates output directory structure

### Phase 2: File-Level Semantic Analysis
- Analyzes each contract individually
- Compares inline comments/docstrings with implementation
- Identifies semantic misalignments

### Phase 3: Project-Level Semantic Analysis
- Examines entire project against high-level design docs
- Performs cross-contract interaction analysis
- Identifies architectural vulnerabilities

### Phase 4: Static Analysis (LLM-Driven)
- LLM autonomously selects which tools to run (Slither/Mythril)
- Executes tools via MCP server
- Consolidates results

### Phase 5: Endpoint Extraction
- Identifies all public/external functions
- Extracts function signatures and parameters
- Prepares data for test generation

### Phase 6: Test Generation & Execution
- Generates Hardhat test files using LLM with tool access
- LLM iteratively compiles and fixes tests
- Creates helper contracts as needed (e.g., reentrancy attackers)

### Phase 7: Report Generation
- Consolidates all findings
- Generates comprehensive markdown report
- Saves raw JSON data for further analysis

## Installation

### Prerequisites

- **Python 3.12+**
- **Docker** (for running Slither and Mythril)
- **Node.js and npm** (for Hardhat project testing)
- **API Keys** for LLM providers:
  - Anthropic API key (for Claude models)
  - Google API key (for Gemini models)

### Install from Source

```bash
# Clone the repository
git clone https://github.com/calebchin/argus.git
cd argus

# Install in editable mode
pip install -e .

# Or install with development dependencies
pip install -e ".[dev]"
```

### Verify Installation

```bash
argus --version
```

## Quick Start

### 1. Set Up API Keys

Export your LLM provider API keys as environment variables:

```bash
export ANTHROPIC_API_KEY="your-anthropic-api-key"
export GEMINI_API_KEY="your-google-api-key"
```

### 2. Ensure Docker is Running

Argus uses Docker to run Slither and Mythril. Make sure Docker is installed and running:

```bash
docker ps
```

### 3. Navigate to Your Hardhat Project

```bash
cd /path/to/your/hardhat/project
```

### 4. Run Analysis

```bash
argus analyze .
```

Or specify a project path:

```bash
argus analyze /path/to/hardhat/project
```

### 5. View Results

Analysis results are saved in the `argus/` directory with a timestamp:

```
your-project/
├── argus/
│   └── YYYYMMDD_HHMMSS/
│       ├── argus-security-report.md    # Main security report
│       ├── raw-analysis-data.json      # Raw findings data
│       ├── contracts/                  # Contract analysis data
│       ├── tests/                      # Test generation data
│       └── reports/                    # Additional reports
└── test/
    └── Argus.*.test.js                 # Generated Hardhat tests
```

## Configuration

Argus looks for configuration files in the project root:
- `argus.config.json` (preferred)
- `argus.json` (alternative)

If no configuration file is found, Argus uses default settings.

### Configuration File Structure

Create an `argus.config.json` in your project root:

```json
{
  "orchestrator": {
    "llm": "gemini",
    "cross_contract": {
      "max_contracts": 10
    },
    "parallel_test_generation": true
  },
  "llm": {
    "anthropic": {
      "provider": "anthropic",
      "model": "claude-sonnet-4-5-20250929",
      "api_key": "ANTHROPIC_API_KEY",
      "max_retries": 3,
      "timeout": 600,
      "max_tool_result_length": 500000
    },
    "gemini": {
      "provider": "gemini",
      "model": "gemini-2.5-flash",
      "api_key": "GEMINI_API_KEY",
      "max_retries": 3,
      "timeout": 600,
      "max_tool_result_length": 500000
    }
  },
  "server": {
    "host": "127.0.0.1",
    "port": 8000,
    "mount_path": "/mcp",
    "tools": {
      "mythril": {
        "timeout": 600,
        "outform": "json",
        "enabled": true,
        "max_contracts": 5,
        "skip_for_large_projects": false,
        "large_project_threshold": 20,
        "docker": {
          "image": "mythril/myth:latest",
          "network_mode": "bridge",
          "remove_containers": true
        }
      },
      "slither": {
        "timeout": 600,
        "docker": {
          "image": "trailofbits/eth-security-toolbox:latest",
          "network_mode": "bridge",
          "remove_containers": true
        }
      }
    }
  },
  "generator": {
    "llm": "gemini",
    "framework": "hardhat",
    "test_generation": {
      "priority_only_threshold": 20,
      "priority_severities": ["critical", "high"],
      "test_file_prefix": "Argus."
    }
  },
  "output": {
    "directory": "argus",
    "level": "info"
  },
  "workdir": "."
}
```

### Configuration Options

#### Orchestrator Settings

- `orchestrator.llm`: LLM provider to use (`"anthropic"` or `"gemini"`)
- `orchestrator.cross_contract.max_contracts`: Maximum number of contracts for cross-contract analysis (default: 10)
- `orchestrator.parallel_test_generation`: Generate tests in parallel (default: `true`)

#### LLM Provider Settings

Configure each LLM provider with:
- `model`: Model name to use
- `api_key`: Environment variable name containing API key
- `max_retries`: Maximum retry attempts for API calls
- `timeout`: Request timeout in seconds
- `max_tool_result_length`: Maximum characters for tool results

**Available Models:**
- **Anthropic**: `claude-sonnet-4-5-20250929`, `claude-3-5-sonnet-20241022`
- **Gemini**: `gemini-2.5-pro`, `gemini-2.5-flash` (faster, more cost-effective)

#### Analysis Tool Settings

- `mythril.enabled`: Enable/disable Mythril analysis
- `mythril.max_contracts`: Maximum contracts to analyze with Mythril
- `mythril.skip_for_large_projects`: Skip Mythril for large projects
- `mythril.large_project_threshold`: Number of contracts to consider "large"
- Tool timeouts and Docker configurations

#### Generator Settings

- `generator.llm`: LLM provider for test generation
- `generator.framework`: Test framework (`"hardhat"`)
- `generator.test_generation.priority_only_threshold`: Only generate tests for high-priority findings if total findings exceed this threshold
- `generator.test_generation.priority_severities`: Severity levels considered high-priority
- `generator.test_generation.test_file_prefix`: Prefix for generated test files (default: `"Argus."`)

#### Output Settings

- `output.directory`: Output directory name (default: `"argus"`)
- `output.level`: Logging level (`"debug"`, `"info"`, `"warning"`, `"error"`)

### View Current Configuration

```bash
argus config
```

View a specific configuration value:

```bash
argus config --key llm.gemini.model
```

## Usage

### Analyze a Project

Run security analysis on a Hardhat project:

```bash
argus analyze /path/to/project
```

With verbose logging:

```bash
argus analyze /path/to/project --verbose
```

### View Configuration

Display current configuration:

```bash
argus config
```

Query specific configuration values:

```bash
argus config --key orchestrator.llm
argus config --key llm.gemini.model
```

### Additional Commands

The following commands are currently under development:

- `argus tool <name> [args...]`: Execute an MCP tool directly
- `argus resource <name>`: Access an MCP resource
- `argus generate [options] <report>`: Generate tests from an existing analysis report

## Plugin System

Argus uses a plugin-based architecture that allows extending functionality through Python entry points.

### Plugin Types

#### 1. LLM Provider Plugins

Add support for new LLM providers.

**Entry point group**: `argus.llm.providers`

**Example Plugin**:

```python
from argus.plugins import LLMProviderPlugin
from argus.llm import BaseLLMProvider

class MyLLMProvider(BaseLLMProvider):
    async def call_with_tools(self, prompt, tools, max_iterations=10):
        # Implementation
        pass
    
    async def call_simple(self, prompt):
        # Implementation
        pass

class MyLLMProviderPlugin(LLMProviderPlugin):
    @property
    def name(self):
        return "myllm"
    
    @property
    def version(self):
        return "1.0.0"
    
    def initialize(self, config=None):
        self.provider = MyLLMProvider(config)
        self.initialized = True
    
    def get_provider(self):
        return self.provider
```

**Register in `pyproject.toml`**:

```toml
[project.entry-points."argus.llm.providers"]
myllm = "my_plugin:MyLLMProviderPlugin"
```

#### 2. MCP Tool Plugins

Add new analysis tools accessible via the MCP server.

**Entry point group**: `argus.mcp.tools`

**Example Plugin**:

```python
from argus.plugins import MCPToolPlugin

class MyToolPlugin(MCPToolPlugin):
    @property
    def name(self):
        return "mytool"
    
    @property
    def version(self):
        return "1.0.0"
    
    def initialize(self, config=None):
        self.config = config or {}
        self.tools = {
            "mytool_analyze": self.analyze,
            "mytool_report": self.report
        }
        self.initialized = True
    
    async def analyze(self, file_path: str):
        """Analyze a file."""
        # Implementation
        return {"status": "success", "findings": []}
    
    async def report(self, analysis_id: str):
        """Generate report."""
        # Implementation
        return {"report": "..."}
```

**Register in `pyproject.toml`**:

```toml
[project.entry-points."argus.mcp.tools"]
mytool = "my_plugin:MyToolPlugin"
```

#### 3. MCP Resource Plugins

Provide access to project resources.

**Entry point group**: `argus.mcp.resources`

#### 4. MCP Prompt Plugins

Reserved for future built-in prompt plugins.

**Entry point group**: `argus.mcp.prompts`

### Creating a Plugin

See the [example plugin](examples/example-plugin/) for a complete working example.

1. **Create plugin package structure**:
   ```
   my_argus_plugin/
   ├── pyproject.toml
   ├── README.md
   └── my_argus_plugin/
       ├── __init__.py
       └── plugin.py
   ```

2. **Implement plugin class** in `plugin.py`

3. **Register entry point** in `pyproject.toml`:
   ```toml
   [project.entry-points."argus.mcp.tools"]
   myplugin = "my_argus_plugin.plugin:MyPlugin"
   ```

4. **Install plugin**:
   ```bash
   pip install -e .
   ```

5. **Configure in `argus.config.json`** (if needed):
   ```json
   {
     "server": {
       "tools": {
         "myplugin": {
           "enabled": true,
           "custom_setting": "value"
         }
       }
     }
   }
   ```

## Development

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/calebchin/argus.git
cd argus

# Install with dev dependencies
pip install -e ".[dev]"
```

### Code Style

Argus follows these code style guidelines:

- **Formatter**: Black (line length: 88)
- **Linter**: Pylint, Ruff
- **Type Checking**: mypy (with `disallow_untyped_defs`)

Format code:
```bash
black src/ tests/
```

Run linters:
```bash
pylint src/
ruff check src/
```

Type checking:
```bash
mypy src/
```

### Project Structure

```
argus/
├── src/argus/              # Main package
│   ├── core/              # Core functionality
│   │   ├── orchestrator/  # 7-phase workflow
│   │   ├── generator/     # Test generation
│   │   ├── api.py         # Programmatic API (planned)
│   │   ├── cli.py         # Command-line interface
│   │   ├── config.py      # Configuration management
│   │   └── docker.py      # Docker integration
│   ├── llm/               # LLM provider abstraction
│   │   ├── factory.py     # Provider factory
│   │   ├── provider.py    # Base provider class
│   │   └── providers/     # Built-in providers
│   ├── plugins/           # Plugin system
│   │   ├── registry.py    # Plugin discovery
│   │   └── plugin/        # Base plugin classes
│   ├── server/            # MCP server
│   │   ├── server.py      # Server implementation
│   │   ├── tools/         # Built-in tools
│   │   └── resources/     # Built-in resources
│   └── utils/             # Utilities
├── tests/                 # Test suite
├── examples/              # Example projects
│   ├── demo-project/      # Full demo with analysis results
│   ├── simple-project/    # Minimal example
│   └── example-plugin/    # Plugin development example
└── pyproject.toml         # Project metadata and dependencies
```

### Adding New Features

1. Create feature branch: `git checkout -b feature/my-feature`
2. Implement changes with tests
3. Ensure code style compliance: `black src/ tests/`
4. Run tests: `pytest`
5. Run type checking: `mypy src/`
6. Commit changes: `git commit -am "Add my feature"`
7. Push and create pull request

## Testing

### Run Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=argus --cov-report=html

# Run specific test file
pytest tests/argus/core/test_config.py

# Run with verbose output
pytest -v

# Run tests matching pattern
pytest -k "test_config"
```

### Test Structure

Tests are organized by component:

- `tests/argus/core/`: Core functionality tests
  - `test_config.py`: Configuration loading and parsing
  - `test_docker.py`: Docker container management
- `tests/argus/server/`: MCP server tests
  - `test_server.py`: Server functionality

### Writing Tests

```python
import pytest
from argus.core.config import ArgusConfig

class TestArgusConfig:
    def test_default_config(self):
        """Test default configuration structure."""
        config = ArgusConfig.get_default_config()
        assert "llm" in config
        assert "orchestrator" in config
        assert "server" in config
    
    def test_get_nested_value(self):
        """Test getting nested configuration values."""
        config = ArgusConfig()
        model = config.get("llm.gemini.model")
        assert model is not None
```

### Coverage Goals

- Maintain >80% code coverage
- All new features must include tests
- Critical paths (orchestrator, generator) should have >90% coverage

## Examples

### Demo Project

The [demo-project](examples/demo-project/) contains a complete example with:
- Multiple smart contracts (Claimer, RewardToken, Treasury)
- Configuration file (`argus.config.json`)
- Sample analysis results in `argus/` directory
- Generated tests demonstrating vulnerabilities

Run analysis on demo project:

```bash
cd examples/demo-project
argus analyze .
```

### Simple Project

The [simple-project](examples/simple-project/) contains a minimal example:
- Single contract (SimpleBank)
- Basic configuration
- Suitable for testing and learning

### Plugin Example

The [example-plugin](examples/example-plugin/) demonstrates:
- Creating a custom MCP tool plugin
- Plugin structure and registration
- Testing plugins

## Troubleshooting

### Docker Issues

**Problem**: "Cannot connect to Docker daemon"

**Solution**: Ensure Docker is running:
```bash
docker ps
```

On Windows, make sure Docker Desktop is started.

**Problem**: Docker timeout errors

**Solution**: Increase timeout in configuration:
```json
{
  "server": {
    "tools": {
      "mythril": {
        "timeout": 1200
      },
      "slither": {
        "timeout": 1200
      }
    }
  }
}
```

### API Key Issues

**Problem**: "API key not found" errors

**Solution**: Verify environment variables are set:
```bash
echo $ANTHROPIC_API_KEY
echo $GEMINI_API_KEY
```

Make sure to export them in your current shell session.

### Large Projects

**Problem**: Analysis takes too long or runs out of memory

**Solution**: Adjust configuration for large projects:
```json
{
  "orchestrator": {
    "cross_contract": {
      "max_contracts": 5
    },
    "parallel_test_generation": false
  },
  "server": {
    "tools": {
      "mythril": {
        "skip_for_large_projects": true,
        "large_project_threshold": 10
      }
    }
  },
  "generator": {
    "test_generation": {
      "priority_only_threshold": 10,
      "priority_severities": ["critical"]
    }
  }
}
```

### Test Generation Failures

**Problem**: Generated tests fail to compile

**Solution**: The LLM iteratively fixes compilation errors, but if it fails:
1. Check Hardhat configuration is correct
2. Ensure all dependencies are installed: `npm install`
3. Review generated tests in `test/Argus.*.test.js`
4. Report issues with verbose logging: `argus analyze . --verbose`

### Memory Issues

**Problem**: Out of memory errors with large codebases

**Solution**: Reduce `max_tool_result_length` in LLM configuration:
```json
{
  "llm": {
    "gemini": {
      "max_tool_result_length": 100000
    }
  }
}
```

## Contributing

We welcome contributions! Please follow these guidelines:

1. **Fork the repository** and create a feature branch
2. **Write tests** for new functionality
3. **Follow code style** guidelines (Black, Pylint, mypy)
4. **Update documentation** as needed
5. **Submit a pull request** with a clear description

### Development Setup

```bash
git clone https://github.com/calebchin/argus.git
cd argus
pip install -e ".[dev]"
```

### Before Submitting

```bash
# Format code
black src/ tests/

# Run linters
pylint src/
ruff check src/

# Type checking
mypy src/

# Run tests
pytest --cov=argus
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Authors

- **Caleb Chin** - cchin@cs.toronto.edu
- **Edward Liu** - edwardy.liu@mail.utoronto.ca
- **Jonathan Wen** - jon.wen@mail.utoronto.ca

## Acknowledgments

- Built with [Anthropic Claude](https://www.anthropic.com/) and [Google Gemini](https://deepmind.google/technologies/gemini/)
- Uses [Slither](https://github.com/crytic/slither) and [Mythril](https://github.com/ConsenSys/mythril) for static analysis
- Model Context Protocol (MCP) for tool integration
- [Hardhat](https://hardhat.org/) for test framework integration

## Links

- **Repository**: https://github.com/calebchin/argus
- **Issues**: https://github.com/calebchin/argus/issues
- **Documentation**: This README

---

**Note**: Argus is under active development. Some features (programmatic API, additional CLI commands) are planned for future releases.