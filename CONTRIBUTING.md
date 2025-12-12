# Contributing to Argus

Thank you for your interest in contributing to Argus! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Development Workflow](#development-workflow)
- [Code Style](#code-style)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)
- [Areas for Contribution](#areas-for-contribution)

## Code of Conduct

This project adheres to a code of conduct that all contributors are expected to follow:

- Be respectful and inclusive
- Welcome newcomers and help them get started
- Focus on constructive feedback
- Respect differing viewpoints and experiences

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/argus.git
   cd argus
   ```
3. **Add upstream remote**:
   ```bash
   git remote add upstream https://github.com/calebchin/argus.git
   ```

## Development Setup

### Prerequisites

- Python 3.12 or higher
- Docker (for running analysis tools)
- Node.js and npm (for testing with Hardhat)
- Git

### Installation

```bash
# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Verify installation
argus --version
pytest --version
```

### Environment Setup

Set up your API keys for testing:

```bash
export ANTHROPIC_API_KEY="your-anthropic-key"
export GEMINI_API_KEY="your-google-key"
```

Consider adding these to your shell profile (`.bashrc`, `.zshrc`, etc.).

## Development Workflow

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
```

Use descriptive branch names:
- `feature/add-openai-provider` - For new features
- `fix/docker-timeout-issue` - For bug fixes
- `docs/improve-plugin-guide` - For documentation
- `refactor/llm-provider-interface` - For refactoring

### 2. Make Your Changes

- Write clear, concise code
- Add docstrings to functions and classes
- Include type hints
- Update documentation as needed
- Add tests for new functionality

### 3. Test Your Changes

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=argus --cov-report=html

# Check specific areas
pytest tests/argus/core/
pytest tests/argus/server/
```

### 4. Check Code Style

```bash
# Format code
black src/ tests/

# Check linting
pylint src/argus
ruff check src/

# Type checking
mypy src/
```

### 5. Commit Your Changes

Write clear, descriptive commit messages:

```bash
git add .
git commit -m "Add OpenAI LLM provider plugin

- Implement OpenAI provider class
- Add configuration schema
- Include unit tests
- Update documentation"
```

### 6. Keep Your Branch Updated

```bash
git fetch upstream
git rebase upstream/main
```

### 7. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a pull request on GitHub.

## Code Style

### Python Style Guide

Argus follows these style guidelines:

#### Formatting

- **Line Length**: 88 characters (Black default)
- **Indentation**: 4 spaces
- **Quotes**: Double quotes for strings
- **Imports**: Organized in three groups (stdlib, third-party, local)

#### Naming Conventions

```python
# Classes: PascalCase
class LLMProvider:
    pass

# Functions and variables: snake_case
def analyze_contract(contract_path):
    result_data = {}
    
# Constants: UPPER_SNAKE_CASE
MAX_RETRIES = 3
DEFAULT_TIMEOUT = 300

# Private members: leading underscore
def _internal_helper():
    pass
```

#### Documentation

Use Google-style docstrings:

```python
def analyze_project(project_path: str, config: Dict[str, Any]) -> AnalysisResult:
    """Analyze a Hardhat project for security vulnerabilities.
    
    Args:
        project_path: Absolute path to the project directory
        config: Configuration dictionary for analysis
        
    Returns:
        AnalysisResult object containing findings and metadata
        
    Raises:
        ValueError: If project_path doesn't exist
        RuntimeError: If analysis fails
        
    Example:
        >>> result = analyze_project("/path/to/project", config)
        >>> print(f"Found {len(result.findings)} issues")
    """
    pass
```

#### Type Hints

All functions should have type hints:

```python
from typing import Dict, List, Optional, Any
from pathlib import Path

def load_config(path: Optional[Path] = None) -> Dict[str, Any]:
    """Load configuration from file."""
    pass

async def run_analysis(
    contracts: List[str],
    llm: BaseLLMProvider,
    timeout: int = 300
) -> Dict[str, Any]:
    """Run async analysis."""
    pass
```

### Tools

```bash
# Auto-format with Black
black src/ tests/

# Lint with Pylint (target: 9.0+)
pylint src/argus

# Fast linting with Ruff
ruff check src/ --fix

# Type checking with mypy
mypy src/
```

## Testing

### Writing Tests

Tests should be clear, focused, and independent:

```python
import pytest
from argus.core.config import ArgusConfig

class TestArgusConfig:
    """Tests for ArgusConfig class."""
    
    def test_default_config_has_required_keys(self):
        """Verify default config contains all required keys."""
        config = ArgusConfig.get_default_config()
        
        assert "orchestrator" in config
        assert "llm" in config
        assert "server" in config
        assert "generator" in config
    
    def test_get_nested_value_with_dot_notation(self):
        """Test retrieving nested config values."""
        config = ArgusConfig()
        
        model = config.get("llm.gemini.model")
        assert model == "gemini-2.5-flash"
    
    def test_get_missing_key_returns_default(self):
        """Test that missing keys return default value."""
        config = ArgusConfig()
        
        value = config.get("nonexistent.key", "default")
        assert value == "default"
    
    @pytest.mark.asyncio
    async def test_async_functionality(self):
        """Test async functions."""
        result = await some_async_function()
        assert result is not None
```

### Test Organization

- Group related tests in classes
- Use descriptive test names
- One assertion per test when possible
- Use fixtures for common setup

```python
@pytest.fixture
def sample_config():
    """Provide sample configuration for tests."""
    return {
        "orchestrator": {"llm": "gemini"},
        "llm": {"gemini": {"model": "gemini-2.5-flash"}}
    }

def test_with_fixture(sample_config):
    """Test using fixture."""
    config = ArgusConfig()
    # ... test code ...
```

### Running Tests

```bash
# All tests
pytest

# Specific file
pytest tests/argus/core/test_config.py

# Specific test
pytest tests/argus/core/test_config.py::TestArgusConfig::test_default_config

# With coverage
pytest --cov=argus --cov-report=html
open htmlcov/index.html  # View coverage report

# Verbose output
pytest -v

# Stop on first failure
pytest -x

# Run only failed tests from last run
pytest --lf
```

## Pull Request Process

### Before Submitting

- [ ] All tests pass (`pytest`)
- [ ] Code is formatted (`black src/ tests/`)
- [ ] Linting passes (`pylint src/`, `ruff check src/`)
- [ ] Type checking passes (`mypy src/`)
- [ ] Documentation is updated
- [ ] CHANGELOG.md is updated (if applicable)

### PR Description Template

```markdown
## Description
Brief description of the changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Changes Made
- Change 1
- Change 2
- Change 3

## Testing
Describe how you tested these changes

## Checklist
- [ ] Tests pass
- [ ] Code formatted with Black
- [ ] Linting passes
- [ ] Type checking passes
- [ ] Documentation updated
```

### Review Process

1. Automated checks run on your PR
2. Maintainers review your code
3. Address any feedback
4. Once approved, your PR will be merged

## Areas for Contribution

### High Priority

1. **Programmatic API** (`src/argus/core/api.py`)
   - Implement functions for library usage
   - Add incremental analysis support
   - Create result processing utilities

2. **CLI Commands** (`src/argus/core/cli.py`)
   - Implement `tool` command
   - Implement `resource` command
   - Implement `generate` command

3. **Configuration Validation**
   - Add JSON schema for `argus.config.json`
   - Validate config at load time
   - Provide helpful error messages

4. **Additional LLM Providers**
   - OpenAI/GPT-4 provider
   - Open-source model providers (Ollama, etc.)
   - Provider comparison benchmarks

### Medium Priority

5. **Enhanced Logging**
   - File-based logging option
   - Per-component log levels
   - Structured logging (JSON format)

6. **Report Formats**
   - HTML report generation
   - JSON/CSV export options
   - Integration with CI/CD platforms

7. **Performance Optimizations**
   - Caching of LLM responses
   - Parallel contract analysis
   - Incremental re-analysis

8. **Documentation**
   - Video tutorials
   - Architecture diagrams
   - Plugin development guide expansion

### Low Priority / Nice to Have

9. **Web Interface**
   - Dashboard for viewing results
   - Real-time analysis progress
   - Interactive report exploration

10. **Additional Analysis Tools**
    - Echidna integration
    - Manticore integration
    - Custom static analysis rules

11. **IDE Integration**
    - VS Code extension
    - Real-time vulnerability detection
    - Inline security suggestions

## Questions?

- **Documentation**: See [README.md](README.md)
- **Issues**: https://github.com/calebchin/argus/issues
- **Discussions**: https://github.com/calebchin/argus/discussions

## License

By contributing to Argus, you agree that your contributions will be licensed under the MIT License.
