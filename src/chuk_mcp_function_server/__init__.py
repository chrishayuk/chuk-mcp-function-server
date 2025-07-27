#!/usr/bin/env python3
# src/chuk_mcp_function_server/__init__.py
"""
Chuk MCP Server - Generic Infrastructure

A configurable MCP server infrastructure that can be extended for any domain.
Provides transport abstraction (stdio/HTTP), configuration management, 
function filtering, and extensible server base classes.
"""

# Import version dynamically
from ._version import get_version, __version__

__author__ = "Chuk MCP Team"
__description__ = "Generic configurable MCP server infrastructure"

# Core exports
from .config import ServerConfig, load_configuration_from_sources
from .function_filter import (
    FunctionFilter, 
    FunctionSpec, 
    GenericFunctionSpec
)
from .base_server import BaseMCPServer, ToolHandler
from .cli import main, create_argument_parser

# Version utilities
from ._version import get_version, get_version_info, print_version_info

__all__ = [
    # Core classes
    "BaseMCPServer",
    "ServerConfig", 
    "FunctionFilter",
    "FunctionSpec",
    "GenericFunctionSpec",
    "ToolHandler",
    
    # Configuration
    "load_configuration_from_sources",
    
    # CLI utilities
    "main",
    "create_argument_parser",
    
    # Version utilities
    "get_version",
    "get_version_info", 
    "print_version_info",
    "__version__",
    "__author__",
    "__description__"
]

# Package metadata
PACKAGE_INFO = {
    "name": "chuk-mcp-function-server",
    "version": __version__,
    "description": __description__,
    "author": __author__,
    "supports_stdio": True,
    "supports_http": True,
    "supported_transports": ["stdio", "http"],
    "default_transport": "stdio",
    "required_dependencies": [
        "chuk-mcp",
        "pyyaml"
    ],
    "optional_dependencies": {
        "http": ["fastapi", "uvicorn", "httpx"],
        "dev": ["pytest", "pytest-asyncio", "black", "isort", "flake8", "mypy", "pre-commit"]
    }
}

def get_package_info():
    """Get package information."""
    info = PACKAGE_INFO.copy()
    info["version"] = __version__  # Use dynamic version
    return info

def check_dependencies():
    """Check which optional dependencies are available."""
    dependencies = {
        "required": {},
        "optional": {}
    }
    
    # Check required dependencies
    try:
        import chuk_mcp
        dependencies["required"]["chuk_mcp"] = True
    except ImportError:
        dependencies["required"]["chuk_mcp"] = False
    
    try:
        import yaml
        dependencies["required"]["pyyaml"] = True
    except ImportError:
        dependencies["required"]["pyyaml"] = False
    
    # Check optional dependencies
    try:
        import fastapi
        import uvicorn
        import httpx
        dependencies["optional"]["http"] = True
    except ImportError:
        dependencies["optional"]["http"] = False
    
    try:
        import pytest
        dependencies["optional"]["dev"] = True
    except ImportError:
        dependencies["optional"]["dev"] = False
    
    return dependencies

def print_dependency_status():
    """Print current dependency status."""
    deps = check_dependencies()
    
    print(f"📦 {PACKAGE_INFO['name']} v{__version__}")
    print("=" * 50)
    
    print("\n✅ Required Dependencies:")
    for dep, available in deps["required"].items():
        status = "✅" if available else "❌"
        print(f"  {status} {dep}")
    
    print("\n🔧 Optional Dependencies:")
    for dep, available in deps["optional"].items():
        status = "✅" if available else "❌"
        feature = {
            "http": "HTTP transport support",
            "dev": "Development tools"
        }.get(dep, dep)
        print(f"  {status} {dep} ({feature})")
    
    # Installation suggestions
    missing_optional = [dep for dep, available in deps["optional"].items() if not available]
    if missing_optional:
        print("\n💡 To install missing optional dependencies:")
        if "http" in missing_optional:
            print("   pip install chuk-mcp-function-server[http]  # For HTTP transport")
        if "dev" in missing_optional:
            print("   pip install chuk-mcp-function-server[dev]   # For development")
        print("   pip install chuk-mcp-function-server[full]  # Install all optional deps")

# Convenience functions for quick server creation
def create_server(server_class=None, config_file=None, **kwargs):
    """Create a configured server instance.
    
    Args:
        server_class: Server class to instantiate (defaults to BaseMCPServer)
        config_file: Optional path to configuration file
        **kwargs: Additional configuration options
    
    Returns:
        Server instance
    """
    if server_class is None:
        server_class = BaseMCPServer
    
    if config_file:
        config = ServerConfig.from_file(config_file)
        # Apply any overrides
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
    else:
        config = ServerConfig(**kwargs)
    
    return server_class(config)

def run_server_stdio(server_class=None, **kwargs):
    """Quick stdio server startup."""
    import asyncio
    server = create_server(server_class=server_class, transport="stdio", **kwargs)
    asyncio.run(server.run())

def run_server_http(server_class=None, port=8000, host="0.0.0.0", **kwargs):
    """Quick HTTP server startup.""" 
    import asyncio
    server = create_server(server_class=server_class, transport="http", port=port, host=host, **kwargs)
    asyncio.run(server.run())