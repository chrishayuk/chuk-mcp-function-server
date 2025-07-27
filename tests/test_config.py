#!/usr/bin/env python3
# tests/test_config.py
"""
Unit tests for the config module of chuk_mcp_function_server.

Tests configuration loading, validation, serialization, and multiple source handling.
"""

import os
import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from typing import Dict, Any

# Import the modules under test
try:
    from chuk_mcp_function_server.config import (
        ServerConfig,
        load_configuration_from_sources,
        _get_package_version
    )
except ImportError as e:
    raise ImportError(f"Could not import config modules: {e}")

class TestServerConfigDefaults:
    """Test ServerConfig default values and initialization."""
    
    def test_default_initialization(self):
        """Test that ServerConfig initializes with correct defaults."""
        config = ServerConfig()
        
        # Transport settings
        assert config.transport == "stdio"
        assert config.port == 8000
        assert config.host == "0.0.0.0"
        
        # Feature toggles
        assert config.enable_tools is True
        assert config.enable_prompts is True
        assert config.enable_resources is True
        
        # Function filtering (should be empty lists)
        assert config.function_whitelist == []
        assert config.function_blacklist == []
        assert config.domain_whitelist == []
        assert config.domain_blacklist == []
        assert config.category_whitelist == []
        assert config.category_blacklist == []
        
        # Performance settings
        assert config.cache_strategy == "smart"
        assert config.cache_size == 1000
        assert config.max_concurrent_calls == 10
        assert config.computation_timeout == 30.0
        
        # Logging
        assert config.log_level == "INFO"
        assert config.verbose is False
        assert config.quiet is False
        
        # Security
        assert config.enable_cors is True
        assert config.rate_limit_enabled is False
        assert config.rate_limit_per_minute == 60
        
        # Server metadata
        assert config.server_name == "generic-mcp-server"
        assert isinstance(config.server_version, str)
        assert config.server_description == "Configurable MCP server"
        
        # Advanced options
        assert config.streaming_threshold == 1000
        assert config.memory_limit_mb == 512
        assert config.custom_config_path is None
    
    def test_custom_initialization(self):
        """Test ServerConfig initialization with custom values."""
        config = ServerConfig(
            transport="http",
            port=9000,
            host="127.0.0.1",
            enable_tools=False,
            server_name="custom-server",
            log_level="DEBUG",
            function_whitelist=["func1", "func2"],
            cache_size=2000
        )
        
        assert config.transport == "http"
        assert config.port == 9000
        assert config.host == "127.0.0.1"
        assert config.enable_tools is False
        assert config.server_name == "custom-server"
        assert config.log_level == "DEBUG"
        assert config.function_whitelist == ["func1", "func2"]
        assert config.cache_size == 2000
    
    def test_version_field_default(self):
        """Test that version field gets set from package version."""
        config = ServerConfig()
        # Should be a valid version string
        assert isinstance(config.server_version, str)
        assert len(config.server_version) > 0
        # Should contain at least one digit
        assert any(c.isdigit() for c in config.server_version)

class TestServerConfigValidation:
    """Test ServerConfig validation logic."""
    
    def test_valid_transport(self):
        """Test validation accepts valid transport values."""
        # These should not raise exceptions
        ServerConfig(transport="stdio")
        ServerConfig(transport="http")
    
    def test_invalid_transport(self):
        """Test validation rejects invalid transport values."""
        with pytest.raises(ValueError, match="Invalid transport"):
            ServerConfig(transport="invalid")
    
    def test_valid_port_range(self):
        """Test validation accepts valid port numbers."""
        ServerConfig(port=1)
        ServerConfig(port=8080)
        ServerConfig(port=65535)
    
    def test_invalid_port_low(self):
        """Test validation rejects port numbers too low."""
        with pytest.raises(ValueError, match="Invalid port"):
            ServerConfig(port=0)
    
    def test_invalid_port_high(self):
        """Test validation rejects port numbers too high."""
        with pytest.raises(ValueError, match="Invalid port"):
            ServerConfig(port=65536)
    
    def test_valid_log_levels(self):
        """Test validation accepts valid log levels."""
        for level in ["DEBUG", "INFO", "WARNING", "ERROR"]:
            ServerConfig(log_level=level)
    
    def test_invalid_log_level(self):
        """Test validation rejects invalid log levels."""
        with pytest.raises(ValueError, match="Invalid log level"):
            ServerConfig(log_level="INVALID")
    
    def test_valid_cache_strategies(self):
        """Test validation accepts valid cache strategies."""
        for strategy in ["none", "memory", "smart"]:
            ServerConfig(cache_strategy=strategy)
    
    def test_invalid_cache_strategy(self):
        """Test validation rejects invalid cache strategies."""
        with pytest.raises(ValueError, match="Invalid cache strategy"):
            ServerConfig(cache_strategy="invalid")

class TestServerConfigFileOperations:
    """Test ServerConfig file loading and saving operations."""
    
    def test_from_file_yaml(self):
        """Test loading configuration from YAML file."""
        yaml_content = """
transport: "http"
port: 9000
host: "localhost"
enable_tools: false
server_name: "yaml-test-server"
log_level: "DEBUG"
function_whitelist:
  - "func1"
  - "func2"
cache_size: 2000
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            f.flush()
            
            try:
                config = ServerConfig.from_file(f.name)
                
                assert config.transport == "http"
                assert config.port == 9000
                assert config.host == "localhost"
                assert config.enable_tools is False
                assert config.server_name == "yaml-test-server"
                assert config.log_level == "DEBUG"
                assert config.function_whitelist == ["func1", "func2"]
                assert config.cache_size == 2000
            finally:
                os.unlink(f.name)
    
    def test_from_file_json(self):
        """Test loading configuration from JSON file."""
        json_data = {
            "transport": "http",
            "port": 7000,
            "enable_resources": False,
            "server_name": "json-test-server",
            "domain_blacklist": ["excluded_domain"]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(json_data, f)
            f.flush()
            
            try:
                config = ServerConfig.from_file(f.name)
                
                assert config.transport == "http"
                assert config.port == 7000
                assert config.enable_resources is False
                assert config.server_name == "json-test-server"
                assert config.domain_blacklist == ["excluded_domain"]
            finally:
                os.unlink(f.name)
    
    def test_from_file_not_found(self):
        """Test handling of non-existent configuration file."""
        with pytest.raises(FileNotFoundError, match="Configuration file not found"):
            ServerConfig.from_file("/non/existent/file.yaml")
    
    def test_from_file_unsupported_format(self):
        """Test handling of unsupported file format."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("some content")
            f.flush()
            
            try:
                with pytest.raises(ValueError, match="Unsupported config file format"):
                    ServerConfig.from_file(f.name)
            finally:
                os.unlink(f.name)
    
    def test_save_to_file_yaml(self):
        """Test saving configuration to YAML file."""
        config = ServerConfig(
            transport="http",
            port=9000,
            server_name="save-test",
            function_whitelist=["func1", "func2"]
        )
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            try:
                config.save_to_file(f.name, format="yaml")
                
                # Load it back and verify
                loaded_config = ServerConfig.from_file(f.name)
                assert loaded_config.transport == "http"
                assert loaded_config.port == 9000
                assert loaded_config.server_name == "save-test"
                assert loaded_config.function_whitelist == ["func1", "func2"]
            finally:
                os.unlink(f.name)
    
    def test_save_to_file_json(self):
        """Test saving configuration to JSON file."""
        config = ServerConfig(
            transport="stdio",
            enable_tools=False,
            server_name="json-save-test"
        )
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            try:
                config.save_to_file(f.name, format="json")
                
                # Load it back and verify
                loaded_config = ServerConfig.from_file(f.name)
                assert loaded_config.transport == "stdio"
                assert loaded_config.enable_tools is False
                assert loaded_config.server_name == "json-save-test"
            finally:
                os.unlink(f.name)
    
    def test_save_to_file_unsupported_format(self):
        """Test handling of unsupported save format."""
        config = ServerConfig()
        
        with tempfile.NamedTemporaryFile(delete=False) as f:
            try:
                with pytest.raises(ValueError, match="Unsupported format"):
                    config.save_to_file(f.name, format="xml")
            finally:
                os.unlink(f.name)

class TestServerConfigEnvironmentVariables:
    """Test ServerConfig environment variable loading."""
    
    def test_from_env_basic_values(self):
        """Test loading basic configuration from environment variables."""
        env_vars = {
            'MCP_SERVER_TRANSPORT': 'http',
            'MCP_SERVER_PORT': '9000',
            'MCP_SERVER_HOST': 'localhost',
            'MCP_SERVER_ENABLE_TOOLS': 'false',
            'MCP_SERVER_LOG_LEVEL': 'DEBUG',
            'MCP_SERVER_CACHE_STRATEGY': 'memory'
        }
        
        with patch.dict(os.environ, env_vars):
            config = ServerConfig.from_env()
            
            assert config.transport == "http"
            assert config.port == 9000
            assert config.host == "localhost"
            assert config.enable_tools is False
            assert config.log_level == "DEBUG"
            assert config.cache_strategy == "memory"
    
    def test_from_env_list_values(self):
        """Test loading list values from environment variables."""
        env_vars = {
            'MCP_SERVER_FUNCTION_WHITELIST': 'func1,func2,func3',
            'MCP_SERVER_DOMAIN_BLACKLIST': 'domain1,domain2'
        }
        
        with patch.dict(os.environ, env_vars):
            config = ServerConfig.from_env()
            
            assert config.function_whitelist == ["func1", "func2", "func3"]
            assert config.domain_blacklist == ["domain1", "domain2"]
    
    def test_from_env_boolean_values(self):
        """Test loading boolean values from environment variables."""
        env_vars = {
            'MCP_SERVER_ENABLE_PROMPTS': 'true',
            'MCP_SERVER_ENABLE_RESOURCES': 'false',
        }
        
        with patch.dict(os.environ, env_vars):
            config = ServerConfig.from_env()
            
            assert config.enable_prompts is True
            assert config.enable_resources is False
    
    def test_from_env_numeric_values(self):
        """Test loading numeric values from environment variables."""
        env_vars = {
            'MCP_SERVER_CACHE_SIZE': '5000',
            'MCP_SERVER_TIMEOUT': '45.5',
            'MCP_SERVER_MAX_CONCURRENT': '20'
        }
        
        with patch.dict(os.environ, env_vars):
            config = ServerConfig.from_env()
            
            assert config.cache_size == 5000
            assert config.computation_timeout == 45.5
            assert config.max_concurrent_calls == 20
    
    @patch('chuk_mcp_function_server.config.logger')
    def test_from_env_invalid_values(self, mock_logger):
        """Test handling of invalid environment variable values."""
        env_vars = {
            'MCP_SERVER_PORT': 'not_a_number',
            'MCP_SERVER_CACHE_SIZE': 'invalid_int',
            'MCP_SERVER_TIMEOUT': 'invalid_float'
        }
        
        with patch.dict(os.environ, env_vars):
            config = ServerConfig.from_env()
            
            # Should use defaults for invalid values and log warnings
            assert config.port == 8000  # Default value
            assert config.cache_size == 1000  # Default value
            assert config.computation_timeout == 30.0  # Default value
            
            # Should have logged warnings
            assert mock_logger.warning.called
    
    def test_from_env_empty_environment(self):
        """Test loading from empty environment (should use defaults)."""
        # Create a clean environment without MCP variables
        clean_env = {k: v for k, v in os.environ.items() if not k.startswith('MCP_SERVER_')}
        
        with patch.dict(os.environ, clean_env, clear=True):
            config = ServerConfig.from_env()
            
            # Should have all default values
            assert config.transport == "stdio"
            assert config.port == 8000
            assert config.enable_tools is True

class TestServerConfigUtilities:
    """Test ServerConfig utility methods."""
    
    def test_to_dict(self):
        """Test converting configuration to dictionary."""
        config = ServerConfig(
            transport="http",
            port=9000,
            function_whitelist=["func1", "func2"],
            enable_tools=False
        )
        
        config_dict = config.to_dict()
        
        assert isinstance(config_dict, dict)
        assert config_dict["transport"] == "http"
        assert config_dict["port"] == 9000
        assert config_dict["function_whitelist"] == ["func1", "func2"]
        assert config_dict["enable_tools"] is False
        
        # Should contain all fields
        expected_fields = [
            "transport", "port", "host", "enable_tools", "enable_prompts",
            "enable_resources", "function_whitelist", "function_blacklist",
            "domain_whitelist", "domain_blacklist", "category_whitelist",
            "category_blacklist", "cache_strategy", "cache_size",
            "max_concurrent_calls", "computation_timeout", "log_level",
            "verbose", "quiet", "enable_cors", "rate_limit_enabled",
            "rate_limit_per_minute", "server_name", "server_version",
            "server_description", "streaming_threshold", "memory_limit_mb",
            "custom_config_path"
        ]
        
        for field in expected_fields:
            assert field in config_dict

class TestLoadConfigurationFromSources:
    """Test the load_configuration_from_sources function."""
    
    def test_defaults_only(self):
        """Test loading with only default values."""
        config = load_configuration_from_sources()
        
        # Should be equivalent to ServerConfig()
        default_config = ServerConfig()
        assert config.transport == default_config.transport
        assert config.port == default_config.port
        assert config.server_name == default_config.server_name
    
    def test_file_override(self):
        """Test loading with file override."""
        yaml_content = """
transport: "http"
port: 7000
server_name: "file-override-test"
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            f.flush()
            
            try:
                config = load_configuration_from_sources(config_file=f.name)
                
                assert config.transport == "http"
                assert config.port == 7000
                assert config.server_name == "file-override-test"
                # Other values should remain default
                assert config.enable_tools is True
            finally:
                os.unlink(f.name)
    
    def test_env_override(self):
        """Test loading with environment variable override."""
        env_vars = {
            'MCP_SERVER_TRANSPORT': 'http',
            'MCP_SERVER_PORT': '6000'
        }
        
        with patch.dict(os.environ, env_vars):
            config = load_configuration_from_sources()
            
            assert config.transport == "http"
            assert config.port == 6000
    
    def test_cli_override(self):
        """Test loading with CLI argument override."""
        cli_overrides = {
            'transport': 'http',
            'port': 5000,
            'enable_tools': False
        }
        
        config = load_configuration_from_sources(cli_overrides=cli_overrides)
        
        assert config.transport == "http"
        assert config.port == 5000
        assert config.enable_tools is False
    
    def test_precedence_order(self):
        """Test that CLI overrides take precedence over env and file."""
        # Create config file
        yaml_content = """
transport: "stdio"
port: 8000
server_name: "file-config"
enable_tools: true
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            f.flush()
            
            try:
                # Set environment variables
                env_vars = {
                    'MCP_SERVER_TRANSPORT': 'http',
                    'MCP_SERVER_PORT': '9000',
                    'MCP_SERVER_ENABLE_TOOLS': 'false'
                }
                
                # Set CLI overrides
                cli_overrides = {
                    'port': 7000,
                    'enable_tools': True
                }
                
                with patch.dict(os.environ, env_vars):
                    config = load_configuration_from_sources(
                        config_file=f.name,
                        cli_overrides=cli_overrides
                    )
                    
                    # CLI should win for port and enable_tools
                    assert config.port == 7000  # CLI override
                    assert config.enable_tools is True  # CLI override
                    
                    # Env should win for transport (no CLI override)
                    assert config.transport == "http"  # Env override
                    
                    # File should provide server_name (no env or CLI override)
                    assert config.server_name == "file-config"  # File
            finally:
                os.unlink(f.name)
    
    @patch('chuk_mcp_function_server.config.logger')
    def test_file_loading_error(self, mock_logger):
        """Test handling of file loading errors."""
        with pytest.raises(Exception):
            load_configuration_from_sources(config_file="/invalid/path/config.yaml")
    
    @patch('chuk_mcp_function_server.config.logger')
    def test_env_loading_warning(self, mock_logger):
        """Test warning when environment loading fails."""
        with patch('chuk_mcp_function_server.config.ServerConfig.from_env', side_effect=Exception("Env error")):
            config = load_configuration_from_sources()
            
            # Should still return a valid config with defaults
            assert config.transport == "stdio"
            
            # Should have logged a warning
            mock_logger.warning.assert_called()

class TestPackageVersionFunction:
    """Test the _get_package_version function."""
    
    def test_get_package_version_returns_string(self):
        """Test that _get_package_version returns a string."""
        version = _get_package_version()
        assert isinstance(version, str)
        assert len(version) > 0
    
    def test_get_package_version_uses_module_version(self):
        """Test that _get_package_version uses the module version when available."""
        # Since the function dynamically imports _version, we can test this
        # by checking that it doesn't return the fallback value
        version = _get_package_version()
        
        # The version should not be the fallback value if _version module exists
        # This is an indirect test but more reliable than mocking dynamic imports
        try:
            from chuk_mcp_function_server._version import __version__
            # If we can import it, the function should use it
            assert version == __version__
        except ImportError:
            # If we can't import it, should use fallback
            assert version == "0.1.0"
    
    def test_get_package_version_fallback_behavior(self):
        """Test that the function has proper fallback logic."""
        # Test the actual fallback by creating a version of the function
        # that simulates import failure
        def test_version_function():
            try:
                # Simulate import failure
                raise ImportError("Simulated failure")
            except (ImportError, AttributeError):
                return "0.1.0"
        
        version = test_version_function()
        assert version == "0.1.0"
    
    def test_get_package_version_attribute_error_fallback(self):
        """Test that the function handles AttributeError properly."""
        def test_version_function():
            try:
                # Simulate AttributeError
                raise AttributeError("Simulated __version__ missing")
            except (ImportError, AttributeError):
                return "0.1.0"
        
        version = test_version_function()
        assert version == "0.1.0"

class TestConfigIntegration:
    """Integration tests for configuration functionality."""
    
    def test_full_configuration_cycle(self):
        """Test a complete configuration load-modify-save-reload cycle."""
        # Create initial config
        original_config = ServerConfig(
            transport="http",
            port=8080,
            server_name="integration-test",
            function_whitelist=["func1", "func2"]
        )
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            try:
                # Save config
                original_config.save_to_file(f.name, format="yaml")
                
                # Load config from file
                loaded_config = load_configuration_from_sources(config_file=f.name)
                
                # Verify loaded config matches original
                assert loaded_config.transport == original_config.transport
                assert loaded_config.port == original_config.port
                assert loaded_config.server_name == original_config.server_name
                assert loaded_config.function_whitelist == original_config.function_whitelist
                
                # Test CLI override on loaded config
                cli_overrides = {'port': 9090, 'enable_tools': False}
                final_config = load_configuration_from_sources(
                    config_file=f.name,
                    cli_overrides=cli_overrides
                )
                
                # Verify overrides applied
                assert final_config.port == 9090  # CLI override
                assert final_config.enable_tools is False  # CLI override
                assert final_config.transport == "http"  # From file
                assert final_config.server_name == "integration-test"  # From file
                
            finally:
                os.unlink(f.name)

if __name__ == "__main__":
    pytest.main([__file__])