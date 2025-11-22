#!/usr/bin/env python3
"""
Example usage of the Docker utilities module.

This script demonstrates how to use the docker.py module to run
security analysis tools (Slither, Mythril) in Docker containers.
"""

import logging
import sys
from pathlib import Path

# Add src to path for local development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from argus.core.docker import (
    check_docker_available,
    pull_image_if_needed,
    get_project_root,
    run_docker_command,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Main example function."""

    print("=" * 70)
    print("Docker Utilities Example")
    print("=" * 70)
    print()

    # Step 1: Check if Docker is available
    print("Step 1: Checking Docker availability...")
    is_available, error = check_docker_available()

    if not is_available:
        print(f"❌ Docker is not available: {error}")
        print("\nPlease ensure:")
        print("  1. Docker Desktop is installed")
        print("  2. Docker daemon is running")
        print("  3. You have proper permissions to access Docker")
        return

    print("✅ Docker is available and running")
    print()

    # Step 2: Pull a test image
    print("Step 2: Testing image pull (using alpine:latest as example)...")
    image = "alpine:latest"

    # Test different pull policies
    policies = ["if-not-present", "never", "always"]

    for policy in policies:
        print(f"\n  Testing pull policy: '{policy}'")
        success, error = pull_image_if_needed(image, policy)

        if success:
            print(f"  ✅ Image '{image}' ready (policy: {policy})")
        else:
            print(f"  ❌ Failed: {error}")

    print()

    # Step 3: Demonstrate project root detection
    print("Step 3: Testing project root detection...")

    # Create a temporary test structure
    import tempfile
    import os

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a mock Hardhat project structure
        project_root = Path(tmpdir) / "my-project"
        contracts_dir = project_root / "contracts"
        contracts_dir.mkdir(parents=True)

        # Create hardhat.config.js
        (project_root / "hardhat.config.js").write_text("module.exports = {};")

        # Create a contract file
        contract_file = contracts_dir / "MyToken.sol"
        contract_file.write_text("""
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract MyToken {
    string public name = "MyToken";
}
""")

        detected_root = get_project_root(str(contract_file))
        print(f"  Contract file: {contract_file}")
        print(f"  Detected root: {detected_root}")
        print(f"  ✅ Correct: {detected_root == project_root}")
        print()

        # Step 4: Run a simple Docker command
        print("Step 4: Testing Docker command execution...")
        print("  Running simple 'echo' command in alpine container...")

        result = run_docker_command(
            image="alpine:latest",
            command=["echo", "Hello from Docker!"],
            project_root=project_root,
            file_path=str(contract_file),
            timeout=30,
        )

        if result["success"]:
            print(f"  ✅ Command executed successfully")
            print(f"  Output: {result['output'].strip()}")
            print(f"  Exit code: {result['exit_code']}")
        else:
            print(f"  ❌ Command failed")
            print(f"  Error: {result['stderr']}")
        print()

        # Step 5: Demonstrate listing files in mounted volume
        print("Step 5: Testing volume mounting...")
        print("  Listing files in mounted project directory...")

        result = run_docker_command(
            image="alpine:latest",
            command=["ls", "-la", "/project"],
            project_root=project_root,
            file_path=str(contract_file),
            timeout=30,
        )

        if result["success"]:
            print(f"  ✅ Volume mounted successfully")
            print(f"  Contents of /project:")
            for line in result["output"].strip().split("\n"):
                print(f"    {line}")
        else:
            print(f"  ❌ Failed to list files")
            print(f"  Error: {result['stderr']}")
        print()

    # Step 6: Demonstrate security analysis tools (if available)
    print("Step 6: Security analysis tools demonstration")
    print("  Note: This would normally run Slither or Mythril")
    print("  Example command for Slither:")
    print("    run_docker_command(")
    print("        image='trailofbits/eth-security-toolbox:latest',")
    print("        command=['slither', '/project/contracts/MyToken.sol', '--json', '-'],")
    print("        project_root=project_root,")
    print("        file_path=str(contract_file),")
    print("        timeout=300,")
    print("    )")
    print()

    print("  Example command for Mythril:")
    print("    run_docker_command(")
    print("        image='mythril/myth:latest',")
    print("        command=['myth', 'analyze', '/project/contracts/MyToken.sol', '--solv', '0.8.0'],")
    print("        project_root=project_root,")
    print("        file_path=str(contract_file),")
    print("        timeout=300,")
    print("    )")
    print()

    print("=" * 70)
    print("Example completed successfully!")
    print("=" * 70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.exception("Error running example")
        print(f"\n❌ Error: {e}")
        sys.exit(1)
