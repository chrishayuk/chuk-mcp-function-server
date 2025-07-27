#!/usr/bin/env python3
# tests/conftest.py
"""
Simple pytest configuration for chuk_mcp_function_server tests.
"""

import os
import sys
from pathlib import Path

# Ensure the src directory is in the Python path
test_dir = Path(__file__).parent
project_root = test_dir.parent
src_dir = project_root / "src"

# Add src to path if not already there
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

# Also add the project root to be safe
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Set testing environment variable
os.environ["TESTING"] = "1"

# Debug: Print the paths being added
print(f"Debug: Added {src_dir} to Python path")
print(f"Debug: Python path: {sys.path[:3]}...")

# Try to import and see what happens
try:
    import chuk_mcp_function_server
    print(f"Debug: Successfully imported chuk_mcp_function_server from {chuk_mcp_function_server.__file__ if hasattr(chuk_mcp_function_server, '__file__') else 'unknown location'}")
except ImportError as e:
    print(f"Debug: Failed to import chuk_mcp_function_server: {e}")
    # List what's actually in the src directory
    if src_dir.exists():
        print(f"Debug: Contents of {src_dir}: {list(src_dir.iterdir())}")
    else:
        print(f"Debug: {src_dir} does not exist!")

try:
    from chuk_mcp_function_server import _version
    print(f"Debug: Successfully imported _version module")
except ImportError as e:
    print(f"Debug: Failed to import _version: {e}")