#!/usr/bin/env python3
# tests/conftest.py
"""
Pytest configuration for chuk_mcp_function_server tests.

This file sets up the test environment, configures paths, and provides
common fixtures for testing the MCP function server infrastructure.
"""

import os
import sys
import pytest
import asyncio
from pathlib import Path
from typing import Dict, Any
from unittest.mock import MagicMock, patch

# ==================== PATH SETUP ====================

def setup_python_path():
    """Ensure the src directory is in the Python path."""
    test_dir = Path(__file__).parent
    project_root = test_dir.parent
    src_dir = project_root / "src"
    
    # Add src to path if not already there
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))
    
    # Also add the project root to be safe
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    return src_dir, project_root

# Set up paths immediately
SRC_DIR, PROJECT_ROOT = setup_python_path()

# Set testing environment variable
os.environ["TESTING"] = "1"

# ==================== PYTEST CONFIGURATION ====================

def pytest_configure(config):
    """Configure pytest with custom settings."""
    # Add custom markers
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "mock: mark test as using extensive mocking"
    )

def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on file patterns."""
    for item in items:
        # Add unit marker to unit test files
        if "unit" in item.fspath.basename:
            item.add_marker(pytest.mark.unit)
        
        # Add integration marker to integration test files
        if "integration" in item.fspath.basename:
            item.add_marker(pytest.mark.integration)
        
        # Add slow marker to tests that contain "slow" in name
        if "slow" in item.name.lower():
            item.add_marker(pytest.mark.slow)

# ==================== IMPORT VALIDATION ====================

def validate_imports():
    """Validate that required modules can be imported."""
    import_errors = []
    
    try:
        import chuk_mcp_function_server
        print(f"✅ Successfully imported chuk_mcp_function_server")
    except ImportError as e:
        import_errors.append(f"chuk_mcp_function_server: {e}")
    
    try:
        from chuk_mcp_function_server import _version
        print(f"✅ Successfully imported _version module")
    except ImportError as e:
        import_errors.append(f"_version: {e}")
    
    try:
        from chuk_mcp_function_server import config
        print(f"✅ Successfully imported config module")
    except ImportError as e:
        import_errors.append(f"config: {e}")
    
    if import_errors:
        print("❌ Import validation failed:")
        for error in import_errors:
            print(f"   {error}")
        print(f"📁 Source directory: {SRC_DIR}")
        if SRC_DIR.exists():
            print(f"📂 Contents: {list(SRC_DIR.iterdir())}")
    else:
        print("✅ All import validations passed")

# Run import validation
validate_imports()

# ==================== FIXTURES ====================

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def mock_config():
    """Provide a mock ServerConfig for testing."""
    try:
        from chuk_mcp_function_server.config import ServerConfig
        return ServerConfig(
            server_name="test-server",
            server_version="0.1.0-test",
            transport="stdio",
            enable_tools=True,
            enable_resources=True,
            enable_prompts=True,
            log_level="DEBUG"
        )
    except ImportError:
        # Fallback mock if config can't be imported
        mock = MagicMock()
        mock.server_name = "test-server"
        mock.server_version = "0.1.0-test"
        mock.transport = "stdio"
        mock.enable_tools = True
        mock.enable_resources = True
        mock.enable_prompts = True
        mock.log_level = "DEBUG"
        mock.function_allowlist = []
        mock.function_denylist = []
        mock.domain_allowlist = []
        mock.domain_denylist = []
        mock.category_allowlist = []
        mock.category_denylist = []
        mock.cache_strategy = "smart"
        mock.cache_size = 1000
        mock.computation_timeout = 30.0
        return mock

@pytest.fixture
def sample_functions():
    """Provide sample functions for testing."""
    def add(x: int, y: int) -> int:
        """Add two numbers."""
        return x + y
    
    def multiply(x: float, y: float) -> float:
        """Multiply two numbers."""
        return x * y
    
    def greet(name: str, greeting: str = "Hello") -> str:
        """Greet someone."""
        return f"{greeting}, {name}!"
    
    async def async_task(duration: float = 1.0) -> str:
        """An async task."""
        await asyncio.sleep(duration)
        return "Task completed"
    
    return {
        "add": add,
        "multiply": multiply,
        "greet": greet,
        "async_task": async_task
    }

@pytest.fixture
def mock_function_spec():
    """Provide a mock FunctionSpec for testing."""
    try:
        from chuk_mcp_function_server.function_filter import GenericFunctionSpec
        
        def sample_func(x: int) -> int:
            return x * 2
        
        return GenericFunctionSpec(
            name="sample_func",
            namespace="test_domain",
            category="test_category",
            func=sample_func,
            description="A sample function for testing"
        )
    except ImportError:
        # Fallback mock
        mock = MagicMock()
        mock.function_name = "sample_func"
        mock.namespace = "test_domain"
        mock.category = "test_category"
        mock.description = "A sample function for testing"
        mock.is_async_native = False
        mock.cache_strategy = "none"
        mock.parameters = {"x": {"type": "integer", "required": True}}
        return mock

@pytest.fixture
def mock_function_provider():
    """Provide a mock FunctionProvider for testing."""
    try:
        from chuk_mcp_function_server.function_filter import GenericFunctionProvider
        
        provider = GenericFunctionProvider("test_provider")
        
        # Add some sample functions
        def func1(): pass
        def func2(): pass
        
        from chuk_mcp_function_server.function_filter import GenericFunctionSpec
        
        spec1 = GenericFunctionSpec("func1", "domain1", "category1", func1)
        spec2 = GenericFunctionSpec("func2", "domain2", "category2", func2)
        
        provider.register_function("domain1::func1", spec1)
        provider.register_function("domain2::func2", spec2)
        
        return provider
    except ImportError:
        # Fallback mock
        mock = MagicMock()
        mock.get_provider_name.return_value = "test_provider"
        mock.get_functions.return_value = {
            "domain1::func1": MagicMock(function_name="func1", namespace="domain1", category="category1"),
            "domain2::func2": MagicMock(function_name="func2", namespace="domain2", category="category2"),
        }
        return mock

@pytest.fixture
def temp_config_file(tmp_path):
    """Create a temporary configuration file for testing."""
    config_content = """
server_name: "test-server"
server_version: "1.0.0-test"
transport: "stdio"
enable_tools: true
enable_resources: true
enable_prompts: true
log_level: "INFO"
function_allowlist: []
function_denylist: []
domain_allowlist: []
domain_denylist: []
cache_strategy: "smart"
cache_size: 500
computation_timeout: 15.0
"""
    
    config_file = tmp_path / "test_config.yaml"
    config_file.write_text(config_content)
    return str(config_file)

@pytest.fixture
def clean_environment():
    """Provide a clean environment for testing."""
    # Save original environment
    original_env = os.environ.copy()
    
    # Clean test-related environment variables
    test_vars = [key for key in os.environ.keys() if key.startswith("MCP_SERVER_")]
    for var in test_vars:
        if var in os.environ:
            del os.environ[var]
    
    yield
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)

@pytest.fixture
def mock_mcp_server():
    """Provide a mock MCP server for testing."""
    mock_server = MagicMock()
    mock_server.register_tool = MagicMock()
    mock_server.register_resource = MagicMock()
    mock_server.register_prompt = MagicMock()
    
    # Mock protocol handler
    mock_handler = MagicMock()
    mock_handler.handle_message = MagicMock()
    mock_server.protocol_handler = mock_handler
    
    return mock_server

# ==================== UTILITY FIXTURES ====================

@pytest.fixture
def capture_logs(caplog):
    """Enhanced log capturing with better formatting."""
    with caplog.at_level("DEBUG"):
        yield caplog

@pytest.fixture
async def async_mock():
    """Provide utilities for async mocking."""
    class AsyncMock:
        def __init__(self, return_value=None):
            self.return_value = return_value
            self.call_count = 0
            self.call_args_list = []
        
        async def __call__(self, *args, **kwargs):
            self.call_count += 1
            self.call_args_list.append((args, kwargs))
            return self.return_value
    
    return AsyncMock

# ==================== PYTEST HOOKS ====================

def pytest_runtest_setup(item):
    """Setup for each test."""
    # You can add test-specific setup here
    pass

def pytest_runtest_teardown(item, nextitem):
    """Teardown for each test."""
    # Clean up any test artifacts
    pass

def pytest_sessionstart(session):
    """Called after the Session object has been created."""
    print("\n🧪 Starting chuk-mcp-function-server test session")
    print(f"📁 Project root: {PROJECT_ROOT}")
    print(f"📁 Source directory: {SRC_DIR}")

def pytest_sessionfinish(session, exitstatus):
    """Called after whole test run finished."""
    if exitstatus == 0:
        print("\n✅ All tests completed successfully!")
    else:
        print(f"\n❌ Test session finished with exit status: {exitstatus}")

# ==================== PYTEST PLUGINS ====================

pytest_plugins = [
    # Add any pytest plugins here if needed
]