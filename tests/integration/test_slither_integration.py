#!/usr/bin/env python3
"""
Integration test for Slither Docker image.

This script verifies that the Slither Docker image can be pulled and run successfully.
Unlike unit tests, this actually executes Docker commands using the SlitherController.

Usage:
    python tests/integration/test_slither_integration.py

    Or with pytest:
    pytest tests/integration/test_slither_integration.py -v
"""

import sys
import asyncio
import tempfile
import logging
from pathlib import Path
import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from argus.tools.slither.controller import SlitherController
from argus.core.docker import docker_available

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)


def create_test_contract(tmp_dir: Path) -> Path:
    """Create a simple test Solidity contract."""
    contract_file = tmp_dir / "TestContract.sol"
    contract_file.write_text("""
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract TestContract {
    uint256 public value;

    function setValue(uint256 _value) public {
        value = _value;
    }

    function getValue() public view returns (uint256) {
        return value;
    }
}
""")
    return contract_file


@pytest.mark.integration
async def test_slither_docker():
    """Test that Slither Docker image can be pulled and run."""
    logger.info("=" * 60)
    logger.info("Slither Integration Test")
    logger.info("=" * 60)

    # Step 1: Check Docker availability
    logger.info("\n1. Checking Docker availability...")
    if not docker_available():
        logger.error("❌ FAILED: Docker is not available")
        pytest.fail("Docker is not available")
    logger.info("✅ Docker is available")

    # Step 2: Create test contract
    logger.info("\n2. Creating test Solidity contract...")
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        contract_file = create_test_contract(tmp_path)
        logger.info(f"   Contract: {contract_file}")
        logger.info("✅ Test contract created")

        # Step 3: Run Slither using the controller
        logger.info("\n3. Running Slither analysis via SlitherController...")
        controller = SlitherController()

        # Override config for this test
        from argus.core.config import conf
        conf.config["workdir"] = str(tmp_path)
    
        result = await controller.execute(
            command="slither",
            args=[str(contract_file.name)]
        )

        logger.info(f"   Success: {result.get('success', False)}")

        # Check for errors
        if result.get("error"):
            error_info = result["error"]
            error_type = error_info.get('type', 'unknown')
            logger.error(f"   Error type: {error_type}")
            logger.error(f"   Error output: {error_info.get('raw_output', '')[:200]}")
            logger.error(f"❌ FAILED: Slither execution failed with {error_type}")
            pytest.fail(f"Slither execution failed with {error_type}: {error_info.get('raw_output', '')[:200]}")

        # Verify we got output
        if not result.get('output'):
            logger.error("❌ FAILED: No output from Slither")
            pytest.fail("No output from Slither")

        # Try to validate JSON output if format is JSON
        output_len = len(result['output'])
        logger.info(f"   Output length: {output_len} characters")

        try:
            import json
            output_json = json.loads(result['output'])
            logger.info("   Valid JSON output: Yes")

            # Check if Slither itself reported success
            if 'success' in output_json:
                logger.info(f"   Slither success: {output_json['success']}")
        except json.JSONDecodeError as e:
            logger.warning(f"   Output is not valid JSON: {e}")
            logger.debug(f"   Output preview: {result['output'][:200]}...")
            # JSON parse failure might be acceptable if Slither still ran
            # (e.g., plain text output or warnings)

        # Success criteria: result.success is True and we have output
        if not result.get('success'):
            logger.error("❌ FAILED: Slither reported failure")
            pytest.fail("Slither reported failure")

        logger.info("✅ Slither ran successfully")

    logger.info("\n" + "=" * 60)
    logger.info("✅ INTEGRATION TEST PASSED")
    logger.info("=" * 60)


if __name__ == "__main__":
    try:
        success = asyncio.run(test_slither_docker())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
