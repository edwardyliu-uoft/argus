# How to Test Docker Image Pull for Slither and Mythril

## Quick Start (3 Commands)

```bash
# 1. Install the docker Python package
pip3 install docker

# 2. Make sure Docker Desktop is running

# 3. Run the test
python3 test_image_pull.py
```

---

## What This Test Does

Tests that `docker.py` can pull the two security analysis tool images:

1. **Slither**: `trailofbits/eth-security-toolbox:latest`
2. **Mythril**: `mythril/myth:latest`

---

## Prerequisites

### 1. Docker Desktop Installed & Running

- **Download**: https://www.docker.com/products/docker-desktop
- **Verify running**: Look for Docker icon in menu bar (Mac) or system tray (Windows)
- **Command line check**:
  ```bash
  docker --version
  # Should show: Docker version XX.X.X
  ```

### 2. Python Docker Package

```bash
pip3 install docker
```

---

## Running the Test

```bash
cd /Users/jonathanweenon/Documents/UofToronto/2025Fall/CSC2125/argus
python3 test_image_pull.py
```

---

## Expected Output (Success)

```
================================================================================
TESTING DOCKER IMAGE PULL FOR ARGUS SECURITY TOOLS
================================================================================

Step 1: Checking Python docker module...
✅ Docker module is installed

Step 2: Importing docker.py functions...
✅ Successfully imported docker.py functions

Step 3: Checking Docker daemon availability...
✅ Docker daemon is running and accessible

================================================================================
Step 4: Testing Slither image pull
================================================================================
Image: trailofbits/eth-security-toolbox:latest
Policy: if-not-present

✅ SUCCESS: Slither image is ready
   Image: trailofbits/eth-security-toolbox:latest

================================================================================
Step 5: Testing Mythril image pull
================================================================================
Image: mythril/myth:latest
Policy: if-not-present

✅ SUCCESS: Mythril image is ready
   Image: mythril/myth:latest

================================================================================
Step 6: Verifying images with Docker client
================================================================================

✅ Slither image verified
   ID: abc123def456
   Tags: ['trailofbits/eth-security-toolbox:latest']
   Size: 1234.5 MB

✅ Mythril image verified
   ID: def456abc123
   Tags: ['mythril/myth:latest']
   Size: 567.8 MB

================================================================================
ALL TESTS PASSED!
================================================================================

Summary:
  ✅ Docker daemon is running
  ✅ Slither image ready: trailofbits/eth-security-toolbox:latest
  ✅ Mythril image ready: mythril/myth:latest

docker.py is ready to run security analysis tools!
```

---

## What Happens During the Test

1. **Checks Python docker module** - Verifies you have the package
2. **Imports docker.py functions** - Tests your code is importable
3. **Checks Docker daemon** - Calls `check_docker_available()`
4. **Pulls Slither image** - Calls `pull_image_if_needed(slither, "if-not-present")`
5. **Pulls Mythril image** - Calls `pull_image_if_needed(mythril, "if-not-present")`
6. **Verifies images** - Checks images are actually in Docker

---

## Image Details

### Slither Image
- **Name**: `trailofbits/eth-security-toolbox:latest`
- **Purpose**: Solidity static analysis
- **Size**: ~1-2 GB
- **Contains**: Slither, Echidna, and other security tools
- **Pull time**: 2-5 minutes (first time)

### Mythril Image
- **Name**: `mythril/myth:latest`
- **Purpose**: EVM bytecode security analysis
- **Size**: ~500-700 MB
- **Contains**: Mythril Classic security analyzer
- **Pull time**: 1-3 minutes (first time)

---

## Troubleshooting

### "Docker module not installed"
```bash
pip3 install docker
```

### "Docker daemon not running"
- Start Docker Desktop application
- Wait for it to fully initialize (icon turns solid)
- Try test again

### "Permission denied" accessing Docker
**On Mac/Linux:**
```bash
sudo usermod -aG docker $USER
# Then log out and back in
```

**On Mac with Docker Desktop:** Usually not needed, Docker Desktop handles permissions

### Images take too long to download
- **First time pull**: These are large images, can take 5-10 minutes on slower connections
- **Subsequent runs**: Images are cached, test completes in seconds
- **Check progress**: Test will show "Pulling Docker image..." message

### Test hangs or times out
- Check Docker Desktop is fully started
- Check internet connection
- Try pulling manually:
  ```bash
  docker pull trailofbits/eth-security-toolbox:latest
  docker pull mythril/myth:latest
  ```

---

## What Success Means

When this test passes, it confirms:

✅ Your `docker.py` module is working correctly
✅ Docker daemon is accessible
✅ The `pull_image_if_needed()` function works
✅ Both security tool images are available
✅ Argus can run Slither and Mythril analyses

---

## Next Steps After Test Passes

1. **Run a real analysis** - Test docker.py with an actual smart contract
2. **Integrate with orchestrator** - Use docker.py in the main Argus pipeline
3. **Add more tools** - Extend to support other security analyzers

---

## Alternative: Manual Verification

If you prefer to verify manually:

```bash
# Check Docker is running
docker ps

# Pull images manually
docker pull trailofbits/eth-security-toolbox:latest
docker pull mythril/myth:latest

# Verify images are present
docker images | grep -E "(slither|mythril)"

# Should show:
# trailofbits/eth-security-toolbox   latest   abc123   2 weeks ago   1.5GB
# mythril/myth                       latest   def456   1 week ago    600MB
```

---

## Summary

**To test image pulling:**

```bash
# Install dependency
pip3 install docker

# Run test (make sure Docker Desktop is running!)
python3 test_image_pull.py
```

**Test validates:**
- docker.py can check Docker availability ✅
- docker.py can pull Slither image ✅
- docker.py can pull Mythril image ✅
- Images are correctly stored in Docker ✅

This confirms docker.py is ready for production use!
