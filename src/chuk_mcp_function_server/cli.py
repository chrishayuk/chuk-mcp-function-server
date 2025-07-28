#!/usr/bin/env python3
# src/chuk_mcp_function_server/cli.py
"""
Generic command line interface for MCP servers.
This provides a base CLI that can be extended by domain-specific servers.
"""

import argparse
import asyncio
import json
import logging
import sys
from typing import Dict, Any, Optional, Type, List

from .config import ServerConfig, load_configuration_from_sources
from .base_server import BaseMCPServer

# Check library availability
try:
    from chuk_mcp.server import MCPServer
    _chuk_mcp_available = True
except ImportError:
    _chuk_mcp_available = False

logger = logging.getLogger(__name__)

def create_argument_parser(prog_name: str = "mcp-server") -> argparse.ArgumentParser:
    """Create the base command line argument parser that can be extended."""
    parser = argparse.ArgumentParser(
        prog=prog_name,
        description="Generic Configurable MCP Server Infrastructure",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                           # Run with STDIO transport
  %(prog)s --transport http          # Run with HTTP transport
  %(prog)s --port 9000               # Custom port for HTTP
  %(prog)s --config server.yaml      # Load configuration from file
  %(prog)s --functions add multiply  # Only expose specific functions
  %(prog)s --verbose                 # Enable debug logging
  %(prog)s --version                 # Show version information
  %(prog)s --check-deps              # Check dependency status

Configuration precedence (highest to lowest):
  1. Command line arguments
  2. Environment variables (MCP_SERVER_*)
  3. Configuration file (--config)
  4. Default values
        """
    )
    
    # Transport settings
    transport_group = parser.add_argument_group('Transport Settings')
    transport_group.add_argument(
        "--transport", "-t",
        choices=["stdio", "http"],
        default="stdio",
        help="Transport method to use (default: %(default)s)"
    )
    transport_group.add_argument(
        "--port", "-p",
        type=int,
        default=8000,
        help="Port for HTTP transport (default: %(default)s)"
    )
    transport_group.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host for HTTP transport (default: %(default)s)"
    )
    
    # Feature toggles
    feature_group = parser.add_argument_group('Feature Control')
    feature_group.add_argument(
        "--disable-tools",
        action="store_true",
        help="Disable tool registration"
    )
    feature_group.add_argument(
        "--disable-prompts",
        action="store_true",
        help="Disable prompt registration"
    )
    feature_group.add_argument(
        "--disable-resources",
        action="store_true",
        help="Disable resource registration"
    )
    feature_group.add_argument(
        "--enable-cors",
        action="store_true",
        help="Enable CORS for HTTP transport (default: enabled)"
    )
    
    # Function filtering (generic)
    filter_group = parser.add_argument_group('Function Filtering')
    filter_group.add_argument(
        "--functions",
        nargs="+",
        metavar="FUNC",
        help="Whitelist specific functions (space-separated)"
    )
    filter_group.add_argument(
        "--exclude-functions",
        nargs="+",
        metavar="FUNC",
        help="Blacklist specific functions (space-separated)"
    )
    filter_group.add_argument(
        "--domains",
        nargs="+",
        metavar="DOMAIN",
        help="Whitelist function domains (space-separated)"
    )
    filter_group.add_argument(
        "--exclude-domains",
        nargs="+",
        metavar="DOMAIN",
        help="Blacklist function domains (space-separated)"
    )
    filter_group.add_argument(
        "--categories",
        nargs="+",
        metavar="CAT",
        help="Whitelist function categories (space-separated)"
    )
    filter_group.add_argument(
        "--exclude-categories",
        nargs="+",
        metavar="CAT",
        help="Blacklist function categories (space-separated)"
    )
    
    # Performance settings
    perf_group = parser.add_argument_group('Performance Settings')
    perf_group.add_argument(
        "--cache-strategy",
        choices=["none", "memory", "smart"],
        default="smart",
        help="Caching strategy (default: %(default)s)"
    )
    perf_group.add_argument(
        "--cache-size",
        type=int,
        default=1000,
        help="Cache size for functions (default: %(default)s)"
    )
    perf_group.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        metavar="SECONDS",
        help="Computation timeout in seconds (default: %(default)s)"
    )
    perf_group.add_argument(
        "--max-concurrent",
        type=int,
        default=10,
        help="Maximum concurrent operations (default: %(default)s)"
    )
    
    # Logging and debugging
    log_group = parser.add_argument_group('Logging')
    log_group.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose debug logging"
    )
    log_group.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Minimize logging output (WARNING level and above)"
    )
    log_group.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Set specific log level (overrides --verbose/--quiet)"
    )
    
    # Configuration file
    config_group = parser.add_argument_group('Configuration')
    config_group.add_argument(
        "--config", "-c",
        metavar="FILE",
        help="Load configuration from file (YAML or JSON)"
    )
    config_group.add_argument(
        "--save-config",
        metavar="FILE",
        help="Save current configuration to file and exit"
    )
    config_group.add_argument(
        "--show-config",
        action="store_true",
        help="Show current configuration and exit"
    )
    config_group.add_argument(
        "--config-format",
        choices=["yaml", "json"],
        default="yaml",
        help="Format for saved configuration files (default: %(default)s)"
    )
    
    # Server information
    info_group = parser.add_argument_group('Information')
    info_group.add_argument(
        "--version",
        action="store_true",
        help="Show version information and exit"
    )
    info_group.add_argument(
        "--check-deps",
        action="store_true",
        help="Check dependency status and exit"
    )
    info_group.add_argument(
        "--list-functions",
        action="store_true",
        help="List available functions and exit"
    )
    info_group.add_argument(
        "--server-info",
        action="store_true",
        help="Show server information and exit"
    )
    
    return parser

def args_to_config_overrides(args) -> Dict[str, Any]:
    """Convert command line arguments to configuration overrides."""
    cli_overrides = {
        'transport': args.transport,
        'port': args.port,
        'host': args.host,
        'enable_tools': not args.disable_tools,
        'enable_prompts': not args.disable_prompts,
        'enable_resources': not args.disable_resources,
        'cache_strategy': args.cache_strategy,
        'cache_size': args.cache_size,
        'computation_timeout': args.timeout,
    }
    
    # Handle max concurrent if provided
    if hasattr(args, 'max_concurrent'):
        cli_overrides['max_concurrent_calls'] = args.max_concurrent
    
    # Handle CORS setting
    if hasattr(args, 'enable_cors') and args.enable_cors:
        cli_overrides['enable_cors'] = True
    
    # Handle list arguments
    list_overrides = {}
    if hasattr(args, 'functions') and args.functions:
        list_overrides['function_allowlist'] = args.functions
    if hasattr(args, 'exclude_functions') and args.exclude_functions:
        list_overrides['function_denylist'] = args.exclude_functions
    if hasattr(args, 'domains') and args.domains:
        list_overrides['domain_allowlist'] = args.domains
    if hasattr(args, 'exclude_domains') and args.exclude_domains:
        list_overrides['domain_denylist'] = args.exclude_domains
    if hasattr(args, 'categories') and args.categories:
        list_overrides['category_allowlist'] = args.categories
    if hasattr(args, 'exclude_categories') and args.exclude_categories:
        list_overrides['category_denylist'] = args.exclude_categories
    
    # Handle log level with precedence
    if hasattr(args, 'log_level') and args.log_level:
        cli_overrides['log_level'] = args.log_level
    elif hasattr(args, 'verbose') and args.verbose:
        cli_overrides['log_level'] = "DEBUG"
    elif hasattr(args, 'quiet') and args.quiet:
        cli_overrides['log_level'] = "WARNING"
    
    # Set verbose/quiet flags
    if hasattr(args, 'verbose'):
        cli_overrides['verbose'] = args.verbose
    if hasattr(args, 'quiet'):
        cli_overrides['quiet'] = args.quiet
    
    # Merge with list overrides
    cli_overrides.update(list_overrides)
    
    # Filter out None values
    return {k: v for k, v in cli_overrides.items() if v is not None}

def check_dependencies() -> bool:
    """Check and report on required dependencies."""
    missing_deps = []
    
    if not _chuk_mcp_available:
        missing_deps.append("chuk-mcp")
    
    # Check for optional dependencies based on usage
    try:
        import yaml
    except ImportError:
        missing_deps.append("pyyaml")
    
    if missing_deps:
        logger.error(f"❌ Missing required dependencies: {', '.join(missing_deps)}")
        logger.error("💡 Install with: pip install " + " ".join(missing_deps))
        return False
    
    logger.debug("✅ All required dependencies available")
    return True

def check_optional_dependencies() -> Dict[str, bool]:
    """Check availability of optional dependencies."""
    optional_deps = {}
    
    # HTTP transport dependencies
    try:
        import fastapi
        import uvicorn
        import httpx
        optional_deps['http'] = True
    except ImportError:
        optional_deps['http'] = False
    
    # Development dependencies
    try:
        import pytest
        optional_deps['dev'] = True
    except ImportError:
        optional_deps['dev'] = False
    
    return optional_deps

async def run_server(
    config: ServerConfig, 
    server_class: Type[BaseMCPServer] = BaseMCPServer
):
    """Run the server with the given configuration and server class."""
    try:
        # Create and run server
        server = server_class(config)
        
        logger.info("✨ Generic MCP Server starting...")
        logger.info(f"🎯 Transport: {config.transport}")
        if config.transport == "http":
            logger.info(f"🌐 Host: {config.host}:{config.port}")
        
        await server.run()
        
    except KeyboardInterrupt:
        logger.info("🛑 Server interrupted by user")
    except Exception as e:
        logger.error(f"💥 Server failed: {e}")
        logger.debug("Full error details:", exc_info=True)
        raise

def show_server_info(server_class: Type[BaseMCPServer], config: ServerConfig):
    """Display server information."""
    print(f"🖥️ Server Information")
    print("=" * 50)
    print(f"Server Class: {server_class.__name__}")
    print(f"Server Name: {config.server_name}")
    print(f"Server Version: {config.server_version}")
    print(f"Server Description: {config.server_description}")
    print(f"Transport: {config.transport}")
    
    if config.transport == "http":
        print(f"HTTP Host: {config.host}")
        print(f"HTTP Port: {config.port}")
        print(f"CORS Enabled: {config.enable_cors}")
    
    print(f"\nFeatures:")
    print(f"  Tools: {'✅' if config.enable_tools else '❌'}")
    print(f"  Resources: {'✅' if config.enable_resources else '❌'}")
    print(f"  Prompts: {'✅' if config.enable_prompts else '❌'}")
    
    print(f"\nPerformance:")
    print(f"  Cache Strategy: {config.cache_strategy}")
    print(f"  Cache Size: {config.cache_size}")
    print(f"  Timeout: {config.computation_timeout}s")
    print(f"  Max Concurrent: {config.max_concurrent_calls}")
    
    # Show filtering if active
    filters_active = any([
        config.function_allowlist,
        config.function_denylist,
        config.domain_allowlist,
        config.domain_denylist,
        config.category_allowlist,
        config.category_denylist
    ])
    
    if filters_active:
        print(f"\n🔍 Active Filters:")
        if config.function_allowlist:
            print(f"  Function Allowlist: {', '.join(config.function_allowlist)}")
        if config.function_denylist:
            print(f"  Function Denylist: {', '.join(config.function_denylist)}")
        if config.domain_allowlist:
            print(f"  Domain Allowlist: {', '.join(config.domain_allowlist)}")
        if config.domain_denylist:
            print(f"  Domain Denylist: {', '.join(config.domain_denylist)}")
        if config.category_allowlist:
            print(f"  Category Allowlist: {', '.join(config.category_allowlist)}")
        if config.category_denylist:
            print(f"  Category Denylist: {', '.join(config.category_denylist)}")

def list_available_functions(server_class: Type[BaseMCPServer], config: ServerConfig):
    """List available functions from the server."""
    print(f"📋 Available Functions")
    print("=" * 50)
    
    try:
        # Create a temporary server instance to get function info
        server = server_class(config)
        
        # This would require extending the base server to expose function information
        # For now, just show that the feature is available
        print("Function listing would be available here.")
        print("Note: This requires server-specific implementation.")
        
    except Exception as e:
        print(f"❌ Could not list functions: {e}")

def validate_configuration(config: ServerConfig) -> List[str]:
    """Validate configuration and return list of warnings/errors."""
    warnings = []
    
    # Transport-specific validation
    if config.transport == "http":
        optional_deps = check_optional_dependencies()
        if not optional_deps.get('http', False):
            warnings.append("HTTP transport requires FastAPI and uvicorn: pip install chuk-mcp-function-server[http]")
    
    # Performance validation
    if config.computation_timeout <= 0:
        warnings.append("Computation timeout disabled (0 or negative value)")
    
    if config.cache_size < 0:
        warnings.append("Invalid cache size (negative value)")
    
    if config.max_concurrent_calls <= 0:
        warnings.append("Invalid max concurrent calls (must be positive)")
    
    # Port validation for HTTP
    if config.transport == "http":
        if not (1 <= config.port <= 65535):
            warnings.append(f"Invalid port number: {config.port}")
    
    return warnings

def main(
    server_class: Type[BaseMCPServer] = BaseMCPServer,
    config_class: Type[ServerConfig] = ServerConfig,
    prog_name: str = "mcp-server"
):
    """Main entry point for the CLI that can be customized by domain-specific servers."""
    parser = create_argument_parser(prog_name)
    args = parser.parse_args()
    
    # Handle version and dependency checks first
    if hasattr(args, 'version') and args.version:
        try:
            from ._version import print_version_info
            print_version_info()
        except ImportError:
            print("Version information not available")
        return
    
    if hasattr(args, 'check_deps') and args.check_deps:
        try:
            from . import print_dependency_status
            print_dependency_status()
        except ImportError:
            # Fallback dependency check - FIXED: Actually call check_optional_dependencies
            required_ok = check_dependencies()
            optional_deps = check_optional_dependencies()  # This was missing!
            
            print("📦 Dependency Status")
            print("=" * 30)
            print(f"Required: {'✅' if required_ok else '❌'}")
            for dep, available in optional_deps.items():
                print(f"Optional ({dep}): {'✅' if available else '❌'}")
        return
    
    # Check dependencies before proceeding
    if not check_dependencies():
        sys.exit(1)
    
    try:
        # Load configuration
        cli_overrides = args_to_config_overrides(args)
        config = load_configuration_from_sources(
            config_file=args.config if hasattr(args, 'config') else None,
            cli_overrides=cli_overrides
        )
        
        # Convert to specific config class if provided
        if config_class != ServerConfig:
            config_dict = config.to_dict()
            config = config_class(**config_dict)
        
        # Validate configuration
        config_warnings = validate_configuration(config)
        if config_warnings:
            logger.warning("Configuration warnings:")
            for warning in config_warnings:
                logger.warning(f"  ⚠️ {warning}")
        
        # Handle special options that don't start the server
        if hasattr(args, 'save_config') and args.save_config:
            try:
                format_type = getattr(args, 'config_format', 'yaml')
                config.save_to_file(args.save_config, format=format_type)
                print(f"✅ Configuration saved to {args.save_config} ({format_type} format)")
                return
            except Exception as e:
                print(f"❌ Failed to save configuration: {e}")
                sys.exit(1)
        
        if hasattr(args, 'show_config') and args.show_config:
            print("📊 Current Configuration:")
            print(json.dumps(config.to_dict(), indent=2))
            return
        
        if hasattr(args, 'server_info') and args.server_info:
            show_server_info(server_class, config)
            return
        
        if hasattr(args, 'list_functions') and args.list_functions:
            list_available_functions(server_class, config)
            return
        
        # Run the server
        asyncio.run(run_server(config, server_class))
        
    except Exception as e:
        logger.error(f"💥 CLI failed: {e}")
        logger.debug("Full error details:", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()