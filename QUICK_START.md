# Docker Module - Quick Start Guide

## How to Run Tests - Step by Step

### Option 1: Run Unit Tests (No Docker Required - Uses Mocking)

This is the **easiest way** to test - doesn't require Docker to be installed!

```bash
# 1. Navigate to project directory
cd /Users/jonathanweenon/Documents/UofToronto/2025Fall/CSC2125/argus

# 2. Install dependencies (if not already installed)
pip3 install pytest docker

# 3. Run the tests
python3 -m pytest tests/argus/core/test_docker.py -v

# Expected output:
# tests/argus/core/test_docker.py::TestCheckDockerAvailable::test_docker_available PASSED
# tests/argus/core/test_docker.py::TestCheckDockerAvailable::test_docker_not_available PASSED
# ... (15+ tests should pass)
# ======================== 15 passed in 0.5s ========================
```

**Input:** None (uses mocked Docker client)
**Output:** All tests should PASS ✅

---

### Option 2: Run Standalone Test (Tests Real Docker if Available)

This test works **with or without Docker** installed:

```bash
# 1. Navigate to project directory
cd /Users/jonathanweenon/Documents/UofToronto/2025Fall/CSC2125/argus

# 2. Install docker module (if not already installed)
pip3 install docker

# 3. Run the standalone test
python3 test_docker_standalone.py

# Expected output (without Docker):
# ======================================================================
# Testing docker.py module
# ======================================================================
#
# [Test 1] Module imports
# ✅ All functions imported successfully
#
# [Test 2] Function signatures
#   check_docker_available()
#   pull_image_if_needed(image: str, pull_policy: str)
#   get_project_root(file_path: str)
#   run_docker_command(image: str, command: List[str], ...)
# ✅ All function signatures valid
#
# [Test 3] get_project_root function
#   ✅ Correctly detected project root
#
# [Test 4] Docker availability check
#   ⚠️  Docker not available: Docker daemon not running: ...
#       This is OK if Docker is not installed
#       Skipping Docker-dependent tests
#
# ======================================================================
# Testing complete!
# ======================================================================
```

**Input:** None (automatically detects if Docker is available)
**Output:** Tests 1-3 should PASS, Test 4-6 skip if Docker not installed

---

### Option 3: Run Example Script (Demonstrates Real Usage)

```bash
# 1. Navigate to project directory
cd /Users/jonathanweenon/Documents/UofToronto/2025Fall/CSC2125/argus

# 2. Install docker module
pip3 install docker

# 3. Run the example
python3 examples/docker_example.py

# Expected output (without Docker):
# ======================================================================
# Docker Utilities Example
# ======================================================================
#
# Step 1: Checking Docker availability...
# ❌ Docker is not available: Docker daemon not running: ...
#
# Please ensure:
#   1. Docker Desktop is installed
#   2. Docker daemon is running
#   3. You have proper permissions to access Docker
```

**Input:** None
**Output:** Demonstrates each function with clear feedback

---

## What Each Function Does (Input/Output)

### 1. `check_docker_available()`

**Input:** None

**Output:** `Tuple[bool, Optional[str]]`
- `(True, None)` - Docker is available
- `(False, "error message")` - Docker not available with reason

**Example:**
```python
from argus.core.docker import check_docker_available

is_available, error = check_docker_available()
if is_available:
    print("✅ Docker is ready!")
else:
    print(f"❌ Docker problem: {error}")
```

---

### 2. `pull_image_if_needed(image, pull_policy)`

**Input:**
- `image: str` - Docker image name (e.g., `"alpine:latest"`)
- `pull_policy: str` - One of: `"always"`, `"if-not-present"`, `"never"`

**Output:** `Tuple[bool, Optional[str]]`
- `(True, None)` - Image ready to use
- `(False, "error message")` - Failed to get image

**Example:**
```python
from argus.core.docker import pull_image_if_needed

# Try to pull image only if not present locally
success, error = pull_image_if_needed("alpine:latest", "if-not-present")
if success:
    print("✅ Image is ready")
else:
    print(f"❌ Failed: {error}")
```

---

### 3. `get_project_root(file_path)`

**Input:**
- `file_path: str` - Absolute path to a contract file

**Output:** `Path` - Project root directory

**Example:**
```python
from argus.core.docker import get_project_root

# Finds project root by looking for hardhat.config.js, package.json, etc.
project_root = get_project_root("/path/to/project/contracts/MyToken.sol")
# Returns: /path/to/project
```

---

### 4. `run_docker_command(image, command, project_root, file_path, timeout)`

**Input:**
- `image: str` - Docker image to use
- `command: List[str]` - Command and arguments to run
- `project_root: Path` - Project directory to mount
- `file_path: str` - File to analyze (for path translation)
- `timeout: int` - Timeout in seconds

**Output:** `Dict[str, Any]` with keys:
- `"success": bool` - True if exit code was 0
- `"output": str` - Standard output from command
- `"stderr": str` - Standard error from command
- `"exit_code": int` - Process exit code

**Example:**
```python
from argus.core.docker import run_docker_command
from pathlib import Path

result = run_docker_command(
    image="alpine:latest",
    command=["echo", "Hello Docker!"],
    project_root=Path("/path/to/project"),
    file_path="/path/to/project/test.txt",
    timeout=30
)

if result["success"]:
    print(f"✅ Output: {result['output']}")
else:
    print(f"❌ Error: {result['stderr']}")
```

---

## Real-World Usage Example

Here's how you'd actually use this in practice to run Mythril on a contract:

```python
from argus.core.docker import (
    check_docker_available,
    pull_image_if_needed,
    get_project_root,
    run_docker_command,
)
from pathlib import Path

# Step 1: Check Docker
is_available, error = check_docker_available()
if not is_available:
    print(f"Error: {error}")
    exit(1)

# Step 2: Prepare image
contract_path = "/path/to/MyToken.sol"
pull_image_if_needed("mythril/myth:latest", "if-not-present")

# Step 3: Find project root
project_root = get_project_root(contract_path)

# Step 4: Run analysis
result = run_docker_command(
    image="mythril/myth:latest",
    command=["myth", "analyze", "/project/contracts/MyToken.sol", "--solv", "0.8.0"],
    project_root=project_root,
    file_path=contract_path,
    timeout=300  # 5 minutes
)

# Step 5: Process results
if result["success"]:
    print("Analysis complete!")
    print(result["output"])
else:
    print(f"Analysis failed: {result['stderr']}")
```

---

## Installation Quick Reference

```bash
# Minimum installation (just to run unit tests)
pip3 install pytest docker

# Full installation (recommended)
cd /Users/jonathanweenon/Documents/UofToronto/2025Fall/CSC2125/argus
pip3 install -e ".[dev]"
```

---

## Troubleshooting

### "No module named 'docker'"
```bash
pip3 install docker
```

### "No module named 'pytest'"
```bash
pip3 install pytest
```

### "No module named 'argus'"
```bash
# Make sure you're in the project directory
cd /Users/jonathanweenon/Documents/UofToronto/2025Fall/CSC2125/argus

# Install in development mode
pip3 install -e .
```

### Tests fail with import errors
The tests use absolute imports. Make sure to either:
1. Install the package: `pip3 install -e .`
2. Or run from project root with: `PYTHONPATH=src python3 -m pytest tests/...`

---

## Quick Command Cheatsheet

```bash
# Test without Docker (unit tests with mocking)
python3 -m pytest tests/argus/core/test_docker.py -v

# Test with Docker detection (standalone)
python3 test_docker_standalone.py

# Run full example
python3 examples/docker_example.py

# Run specific test
python3 -m pytest tests/argus/core/test_docker.py::TestCheckDockerAvailable::test_docker_available -v

# Run with coverage
python3 -m pytest tests/argus/core/test_docker.py --cov=argus.core.docker --cov-report=term-missing
```

---

## Expected Results Summary

| Test Method | Docker Required? | Expected Result |
|-------------|------------------|-----------------|
| Unit tests (`pytest`) | ❌ No | All 15+ tests pass |
| Standalone test | ⚠️ Optional | Tests 1-3 pass, 4-6 skip without Docker |
| Example script | ⚠️ Optional | Shows Docker unavailable message |
| Real integration | ✅ Yes | Full Docker execution |

The module is **fully runnable** - you can test it right now without Docker using the unit tests!
