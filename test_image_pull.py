#!/usr/bin/env python3
"""
Test script to verify docker.py can pull Slither and Mythril images.
Tests the specific images used by Argus for security analysis.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

print("=" * 80)
print("TESTING DOCKER IMAGE PULL FOR ARGUS SECURITY TOOLS")
print("=" * 80)
print()

# Configuration from argus
SLITHER_IMAGE = "trailofbits/eth-security-toolbox:latest"
MYTHRIL_IMAGE = "mythril/myth:latest"

# Step 1: Check if docker module is available
print("Step 1: Checking Python docker module...")
try:
    import docker
    print("✅ Docker module is installed")
except ImportError:
    print("❌ Docker module not installed")
    print()
    print("Please install it:")
    print("  pip3 install docker")
    print()
    sys.exit(1)

# Step 2: Import our functions
print()
print("Step 2: Importing docker.py functions...")
try:
    from argus.core.docker import (
        check_docker_available,
        pull_image_if_needed,
    )
    print("✅ Successfully imported docker.py functions")
except ImportError as e:
    print(f"❌ Failed to import: {e}")
    sys.exit(1)

# Step 3: Check Docker daemon
print()
print("Step 3: Checking Docker daemon availability...")
is_available, error = check_docker_available()

if not is_available:
    print(f"❌ Docker is not available: {error}")
    print()
    print("Please ensure:")
    print("  1. Docker Desktop is installed")
    print("  2. Docker daemon is running")
    print("  3. You have permissions to access Docker")
    print()
    sys.exit(1)

print("✅ Docker daemon is running and accessible")

# Step 4: Test pulling Slither image
print()
print("=" * 80)
print("Step 4: Testing Slither image pull")
print("=" * 80)
print(f"Image: {SLITHER_IMAGE}")
print("Policy: if-not-present")
print()

success, error = pull_image_if_needed(SLITHER_IMAGE, "if-not-present")

if success:
    print(f"✅ SUCCESS: Slither image is ready")
    print(f"   Image: {SLITHER_IMAGE}")
else:
    print(f"❌ FAILED: Could not get Slither image")
    print(f"   Error: {error}")
    sys.exit(1)

# Step 5: Test pulling Mythril image
print()
print("=" * 80)
print("Step 5: Testing Mythril image pull")
print("=" * 80)
print(f"Image: {MYTHRIL_IMAGE}")
print("Policy: if-not-present")
print()

success, error = pull_image_if_needed(MYTHRIL_IMAGE, "if-not-present")

if success:
    print(f"✅ SUCCESS: Mythril image is ready")
    print(f"   Image: {MYTHRIL_IMAGE}")
else:
    print(f"❌ FAILED: Could not get Mythril image")
    print(f"   Error: {error}")
    sys.exit(1)

# Step 6: Verify images with Docker directly
print()
print("=" * 80)
print("Step 6: Verifying images with Docker client")
print("=" * 80)
print()

try:
    client = docker.from_env()

    # Check Slither image
    try:
        slither_img = client.images.get(SLITHER_IMAGE)
        print(f"✅ Slither image verified")
        print(f"   ID: {slither_img.id[:12]}")
        print(f"   Tags: {slither_img.tags}")
        print(f"   Size: {slither_img.attrs['Size'] / 1024 / 1024:.1f} MB")
    except docker.errors.ImageNotFound:
        print(f"❌ Slither image not found in local Docker")

    print()

    # Check Mythril image
    try:
        mythril_img = client.images.get(MYTHRIL_IMAGE)
        print(f"✅ Mythril image verified")
        print(f"   ID: {mythril_img.id[:12]}")
        print(f"   Tags: {mythril_img.tags}")
        print(f"   Size: {mythril_img.attrs['Size'] / 1024 / 1024:.1f} MB")
    except docker.errors.ImageNotFound:
        print(f"❌ Mythril image not found in local Docker")

except Exception as e:
    print(f"⚠️  Could not verify images: {e}")

# Success!
print()
print("=" * 80)
print("ALL TESTS PASSED!")
print("=" * 80)
print()
print("Summary:")
print(f"  ✅ Docker daemon is running")
print(f"  ✅ Slither image ready: {SLITHER_IMAGE}")
print(f"  ✅ Mythril image ready: {MYTHRIL_IMAGE}")
print()
print("docker.py is ready to run security analysis tools!")
print()
