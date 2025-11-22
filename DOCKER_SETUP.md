# Docker Module Setup and Testing

This guide explains how to set up and test the `docker.py` module.

## Prerequisites

1. **Python 3.12+** (project requirement)
   - Your system has Python 3.9.6, you may need to upgrade or use pyenv

2. **Docker Desktop** (for actual Docker execution)
   - Download from: https://www.docker.com/products/docker-desktop
   - Ensure Docker daemon is running

## Installation

### Option 1: Full Development Setup (Recommended)

```bash
# Navigate to the project root
cd /Users/jonathanweenon/Documents/UofToronto/2025Fall/CSC2125/argus

# Install the package in development mode with dependencies
pip install -e ".[dev]"
```

This will install all dependencies from `pyproject.toml`:
- `docker>=7.0.0` - Python Docker client
- `anthropic>=0.18.0` - Anthropic API
- `google-genai>=1.0.0` - Google Gemini API
- `mcp>=1.22.0` - Model Context Protocol
- `click>=8.0.0` - CLI framework
- Development tools: `pytest`, `black`, `ruff`, `mypy`

### Option 2: Install Only Required Dependencies

```bash
# Install just what's needed for docker.py
pip install docker>=7.0.0

# For testing
pip install pytest pytest-cov
```

### Option 3: Using a Virtual Environment (Recommended)

```bash
# Create a virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate  # On Windows

# Install dependencies
pip install -e ".[dev]"
```

## Running Tests

### Unit Tests (with pytest)

```bash
# Run all docker tests
pytest tests/argus/core/test_docker.py -v

# Run with coverage
pytest tests/argus/core/test_docker.py -v --cov=argus.core.docker --cov-report=term-missing

# Run all tests
pytest tests/ -v
```

### Standalone Test Script

If you don't have pytest installed, use the standalone test:

```bash
python3 test_docker_standalone.py
```

This script:
- ✅ Tests module imports
- ✅ Validates function signatures
- ✅ Tests project root detection
- ✅ Checks Docker availability (if installed)
- ✅ Tests image pulling (if Docker is running)
- ✅ Executes simple commands (if Docker is running)

### Example Usage Script

```bash
# Run the comprehensive example
python3 examples/docker_example.py
```

This demonstrates:
- Docker availability checking
- Image pull policies
- Project root detection
- Docker command execution
- Volume mounting
- Security tool integration patterns

## Code Quality Checks

```bash
# Type checking with mypy
mypy src/argus/core/docker.py

# Linting with ruff
ruff check src/argus/core/docker.py

# Format with black
black src/argus/core/docker.py
```

## Testing Without Docker

The unit tests use mocking and don't require Docker to be installed. They test:
- Function logic
- Error handling
- Path translation
- Volume mounting configuration
- Network isolation settings

To run tests without Docker:
```bash
pytest tests/argus/core/test_docker.py -v
```

## Testing With Docker

To test actual Docker integration:

1. **Install Docker Desktop** and ensure it's running
2. **Run the standalone test**:
   ```bash
   python3 test_docker_standalone.py
   ```
3. **Run the example script**:
   ```bash
   python3 examples/docker_example.py
   ```

## Key Improvements Made

The `docker.py` module has been debugged and enhanced with:

1. ✅ **Proper type hints** - All functions use `List[str]` instead of `list`
2. ✅ **Comprehensive logging** - Using Python's logging module
3. ✅ **Better error handling** - Improved timeout and exception handling
4. ✅ **Robust timeout handling** - Graceful handling of container timeouts
5. ✅ **Security features** - Read-only mounts, no network access
6. ✅ **Comprehensive tests** - 15+ test cases covering all scenarios
7. ✅ **Example usage** - Practical demonstration script

## Module Functions

### `check_docker_available() -> Tuple[bool, Optional[str]]`
Checks if Docker daemon is running.

### `pull_image_if_needed(image: str, pull_policy: str) -> Tuple[bool, Optional[str]]`
Pulls Docker images based on policy:
- `"always"` - Always pull latest
- `"if-not-present"` - Only pull if missing
- `"never"` - Use only local images

### `get_project_root(file_path: str) -> Path`
Intelligently finds project root by looking for:
- `hardhat.config.js/ts`
- `package.json`
- `foundry.toml`
- `truffle-config.js`
- `contracts` directory

### `run_docker_command(...) -> Dict[str, Any]`
Executes commands in isolated Docker containers with:
- Read-only volume mounting
- No network access
- Timeout protection
- Automatic cleanup

## Security Features

The module provides secure execution of third-party tools:

1. **Read-only volumes** - Prevents tools from modifying code
2. **Network isolation** - `network_mode="none"` prevents data exfiltration
3. **Timeout protection** - Prevents resource exhaustion
4. **Automatic cleanup** - Removes containers after execution
5. **Path isolation** - Proper path translation for container execution

## Common Issues

### "No module named 'docker'"
```bash
pip install docker
```

### "Docker daemon not running"
Start Docker Desktop and wait for it to fully initialize.

### "Permission denied" on Docker
On Linux, add your user to the docker group:
```bash
sudo usermod -aG docker $USER
# Then log out and back in
```

### Python version mismatch
The project requires Python 3.12+. Check your version:
```bash
python3 --version
```

Consider using `pyenv` to manage Python versions:
```bash
# Install pyenv, then:
pyenv install 3.12
pyenv local 3.12
```

## Next Steps

1. Install dependencies using one of the options above
2. Run the standalone test to verify installation
3. Run the example script to see practical usage
4. Check out the comprehensive unit tests in `tests/argus/core/test_docker.py`
5. Integrate with security tools (Slither, Mythril) as shown in examples

## Questions or Issues?

- Check the [main README](README.md) for project overview
- Review the [pyproject.toml](pyproject.toml) for full dependency list
- Examine the test files for usage examples
