# Argus Test Suite

This directory contains tests for the Argus smart contract security scanner.

## Test Types

### Unit Tests
Unit tests verify individual components in isolation without external dependencies like Docker.

**Location**: `tests/unit/`

**Run unit tests**:
```bash
pytest tests/unit/ -v
```

### Integration Tests
Integration tests verify that Docker images can be pulled and run successfully with real containers.

**Location**: `tests/integration/`

**Prerequisites**:
- Docker daemon must be running
- Network access required (for pulling images and Slither's solc download)

**Run integration tests**:
```bash
pytest tests/integration/ -v -m integration
```

**Run a specific integration test**:
```bash
# Test Mythril only
pytest tests/integration/test_mythril_integration.py -v

# Test Slither only
pytest tests/integration/test_slither_integration.py -v
```

## Running All Tests

Run all tests (unit + integration):
```bash
pytest tests/ -v
```

## Test Options

**Verbose output**:
```bash
pytest tests/ -v
```

**Show print statements**:
```bash
pytest tests/ -v -s
```

**Control log level**:
```bash
pytest tests/ -v --log-cli-level=INFO
```

**Run tests matching a pattern**:
```bash
pytest tests/ -v -k "slither"
```

## Troubleshooting

**Docker not available**: Integration tests will fail if Docker is not running. Start the Docker daemon first.

**Network issues**: Slither requires network access to download the Solidity compiler. Ensure `network_mode: "bridge"` is set in the configuration.

**Image pull failures**: If Docker images fail to pull, try manually pulling them first:
```bash
docker pull mythril/myth:latest
docker pull trailofbits/eth-security-toolbox:latest
```
