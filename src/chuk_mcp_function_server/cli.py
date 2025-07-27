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
from typing import Dict, Any, Optional, Type

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
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Transport settings
    transport_group = parser.add_argument_group('Transport Settings')
    transport_group.add_argument(
        "--transport", "-t",
        choices=["stdio", "http"],
        default="stdio",
        help="Transport method to use (default: stdio)"
    )
    transport_group.add_argument(
        "--port", "-p",
        type=int,
        default=8000,
        help="Port for HTTP transport (default: 8000)"
    )
    transport_group.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host for HTTP transport (default: 0.0.0.0)"
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
    
    # Function filtering (generic)
    filter_group = parser.add_argument_group('Function Filtering')
    filter_group.add_argument(
        "--functions",
        nargs="+",
        help="Whitelist specific functions"
    )
    filter_group.add_argument(
        "--exclude-functions",
        nargs="+",
        help="Blacklist specific functions"
    )
    filter_group.add_argument(
        "--domains",
        nargs="+",
        help="Whitelist function domains"
    )
    filter_group.add_argument(
        "--exclude-domains",
        nargs="+",
        help="Blacklist function domains"
    )
    filter_group.add_argument(
        "--categories",
        nargs="+",
        help="Whitelist function categories"
    )
    filter_group.add_argument(
        "--exclude-categories",
        nargs="+",
        help="Blacklist function categories"
    )
    
    # Performance settings
    perf_group = parser.add_argument_group('Performance Settings')
    perf_group.add_argument(
        "--cache-strategy",
        choices=["none", "memory", "smart"],
        default="smart",
        help="Caching strategy (default: smart)"
    )
    perf_group.add_argument(
        "--cache-size",
        type=int,
        default=1000,
        help="Cache size for functions (default: 1000)"
    )
    perf_group.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Computation timeout in seconds (default: 30.0)"
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
        help="Minimize logging output"
    )
    
    # Configuration file
    config_group = parser.add_argument_group('Configuration')
    config_group.add_argument(
        "--config", "-c",
        help="Load configuration from file (YAML or JSON)"
    )
    config_group.add_argument(
        "--save-config",
        help="Save current configuration to file and exit"
    )
    config_group.add_argument(
        "--show-config",
        action="store_true",
        help="Show current configuration and exit"
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
        'verbose': args.verbose,
        'quiet': args.quiet,
        'cache_strategy': args.cache_strategy,
        'cache_size': args.cache_size,
        'computation_timeout': args.timeout,
    }
    
    # Handle list arguments
    list_overrides = {}
    if hasattr(args, 'functions') and args.functions:
        list_overrides['function_whitelist'] = args.functions
    if hasattr(args, 'exclude_functions') and args.exclude_functions:
        list_overrides['function_blacklist'] = args.exclude_functions
    if hasattr(args, 'domains') and args.domains:
        list_overrides['domain_whitelist'] = args.domains
    if hasattr(args, 'exclude_domains') and args.exclude_domains:
        list_overrides['domain_blacklist'] = args.exclude_domains
    if hasattr(args, 'categories') and args.categories:
        list_overrides['category_whitelist'] = args.categories
    if hasattr(args, 'exclude_categories') and args.exclude_categories:
        list_overrides['category_blacklist'] = args.exclude_categories
    
    # Handle log level
    if args.verbose:
        cli_overrides['log_level'] = "DEBUG"
    elif args.quiet:
        cli_overrides['log_level'] = "WARNING"
    
    # Merge with list overrides
    cli_overrides.update(list_overrides)
    
    # Filter out None values
    return {k: v for k, v in cli_overrides.items() if v is not None}

def check_dependencies():
    """Check and report on required dependencies."""
    missing_deps = []
    
    if not _chuk_mcp_available:
        missing_deps.append("chuk-mcp")
    
    if missing_deps:
        logger.error(f"❌ Missing required dependencies: {', '.join(missing_deps)}")
        logger.error("💡 Install with: pip install " + " ".join(missing_deps))
        return False
    
    return True

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
        raise

def main(
    server_class: Type[BaseMCPServer] = BaseMCPServer,
    config_class: Type[ServerConfig] = ServerConfig,
    prog_name: str = "mcp-server"
):
    """Main entry point for the CLI that can be customized by domain-specific servers."""
    parser = create_argument_parser(prog_name)
    args = parser.parse_args()
    
    # Handle version and dependency checks
    if hasattr(args, 'version') and args.version:
        from ._version import print_version_info
        print_version_info()
        return
    
    if hasattr(args, 'check_deps') and args.check_deps:
        from . import print_dependency_status
        print_dependency_status()
        return
    
    # Check dependencies first
    if not check_dependencies():
        sys.exit(1)
    
    try:
        # Load configuration
        cli_overrides = args_to_config_overrides(args)
        config = load_configuration_from_sources(
            config_file=args.config,
            cli_overrides=cli_overrides
        )
        
        # Convert to specific config class if provided
        if config_class != ServerConfig:
            config_dict = config.to_dict()
            config = config_class(**config_dict)
        
        # Handle special options
        if args.save_config:
            try:
                config.save_to_file(args.save_config)
                print(f"✅ Configuration saved to {args.save_config}")
                return
            except Exception as e:
                print(f"❌ Failed to save configuration: {e}")
                sys.exit(1)
        
        if args.show_config:
            print("📊 Current Configuration:")
            print(json.dumps(config.to_dict(), indent=2))
            return
        
        # Run the server
        asyncio.run(run_server(config, server_class))
        
    except Exception as e:
        logger.error(f"💥 CLI failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()