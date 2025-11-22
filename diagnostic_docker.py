#!/usr/bin/env python3
"""Deep diagnostic for Docker connection"""

import sys

print("Testing urllib3 and requests...")
try:
    import urllib3
    print(f"urllib3 version: {urllib3.__version__}")
    
    import requests
    print(f"requests version: {requests.__version__}")
    
    # Check if docker can import properly
    import docker
    print(f"docker version: {docker.__version__}")
    
    # Check what adapter docker is trying to use
    from docker.transport import SSLHTTPAdapter
    print(f"SSLHTTPAdapter available: {SSLHTTPAdapter}")
    
    # Try to see what URL docker is constructing
    from docker.api.client import APIClient
    
    print("\nTrying to create APIClient...")
    api_client = APIClient()
    print(f"Base URL constructed: {api_client.base_url}")
    
except Exception as e:
    print(f"Error during import/setup: {e}")
    import traceback
    traceback.print_exc()

print("\nChecking Docker socket...")
import os
socket_path = "/var/run/docker.sock"
if os.path.exists(socket_path):
    print(f"✅ {socket_path} exists")
    import stat
    st = os.stat(socket_path)
    print(f"   Mode: {oct(st.st_mode)}")
    print(f"   Readable: {os.access(socket_path, os.R_OK)}")
    print(f"   Writable: {os.access(socket_path, os.W_OK)}")
else:
    print(f"❌ {socket_path} does not exist")

print("\nChecking alternative socket locations...")
alt_paths = [
    "/var/run/docker.sock",
    f"{os.path.expanduser('~')}/.docker/run/docker.sock",
    f"{os.path.expanduser('~')}/.colima/docker.sock",
]
for path in alt_paths:
    if os.path.exists(path):
        print(f"✅ Found: {path}")