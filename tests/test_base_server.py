#!/usr/bin/env python3
# tests/test_base_server.py
"""
Unit tests for the base_server module of chuk_mcp_function_server.

Tests the BaseMCPServer class, tool registration, transport handling,
and server operations.
"""

import asyncio
import json
import pytest
import sys
from io import StringIO
from unittest.mock import (
    MagicMock, AsyncMock, patch, mock_open, call
)
from typing import Dict, Any

# Import the modules under test
try:
    from chuk_mcp_function_server.base_server import (
        BaseMCPServer,
        ToolHandler
    )
    from chuk_mcp_function_server.config import ServerConfig
except ImportError as e:
    raise ImportError(f"Could not import base_server modules: {e}")

class TestBaseMCPServerInitialization:
    """Test BaseMCPServer initialization and basic properties."""
    
    def test_initialization_with_default_config(self):
        """Test server initialization with default configuration."""
        config = ServerConfig()
        
        # Create a concrete implementation for testing
        class TestServer(BaseMCPServer):
            def _register_tools(self):
                pass
        
        server = TestServer(config)
        
        assert server.config == config
        assert server.mcp_server is not None
    
    def test_initialization_with_custom_config(self):
        """Test server initialization with custom configuration."""
        config = ServerConfig(
            server_name="custom-test-server",
            server_version="2.0.0",
            enable_tools=False,
            enable_resources=False,
            enable_prompts=True,
            log_level="DEBUG"
        )
        
        class TestServer(BaseMCPServer):
            def _register_tools(self):
                pass
        
        server = TestServer(config)
        
        assert server.config.server_name == "custom-test-server"
        assert server.config.server_version == "2.0.0"
        assert server.config.enable_tools is False
        assert server.config.enable_resources is False
        assert server.config.enable_prompts is True
    
    @patch('chuk_mcp_function_server.base_server.logging.getLogger')
    def test_logging_configuration(self, mock_get_logger):
        """Test that logging is configured correctly."""
        config = ServerConfig(log_level="DEBUG")
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        class TestServer(BaseMCPServer):
            def _register_tools(self):
                pass
        
        TestServer(config)
        
        # Verify logger was configured
        mock_logger.setLevel.assert_called()

class TestBaseMCPServerToolRegistration:
    """Test tool registration functionality."""
    
    def test_register_tool_basic(self):
        """Test basic tool registration functionality."""
        config = ServerConfig()
        
        class TestServer(BaseMCPServer):
            def _register_tools(self):
                pass
        
        server = TestServer(config)
        
        # Mock the register_tool method to test the call
        server.mcp_server.register_tool = MagicMock()
        
        # Test tool registration
        async def test_tool(param1: str) -> str:
            return f"Result: {param1}"
        
        server.register_tool(
            name="test_tool",
            handler=test_tool,
            schema={
                "type": "object",
                "properties": {"param1": {"type": "string"}},
                "required": ["param1"]
            },
            description="A test tool"
        )
        
        # Verify the tool was registered
        server.mcp_server.register_tool.assert_called_once()
        call_args = server.mcp_server.register_tool.call_args
        assert call_args[1]['name'] == "test_tool"
        assert call_args[1]['description'] == "A test tool"
    
    @patch('chuk_mcp_function_server.base_server.logger')
    def test_register_tool_without_mcp_server(self, mock_logger):
        """Test tool registration when MCP server is not available."""
        config = ServerConfig()
        
        class TestServer(BaseMCPServer):
            def _register_tools(self):
                pass
        
        server = TestServer(config)
        server.mcp_server = None  # Simulate no MCP server
        
        async def test_tool():
            return "test"
        
        server.register_tool(
            name="test_tool",
            handler=test_tool,
            schema={},
            description="Test tool"
        )
        
        # Should log warning about unavailable MCP server
        mock_logger.warning.assert_called()
    
    @patch('chuk_mcp_function_server.base_server.logger')
    def test_register_tool_with_error(self, mock_logger):
        """Test tool registration error handling."""
        config = ServerConfig()
        
        class TestServer(BaseMCPServer):
            def _register_tools(self):
                pass
        
        server = TestServer(config)
        server.mcp_server.register_tool = MagicMock(side_effect=Exception("Registration failed"))
        
        async def test_tool():
            return "test"
        
        server.register_tool(
            name="test_tool",
            handler=test_tool,
            schema={},
            description="Test tool"
        )
        
        # Should log error
        mock_logger.error.assert_called()
    
    @pytest.mark.asyncio
    async def test_wrapped_handler_timeout(self):
        """Test that wrapped handlers respect timeout settings."""
        config = ServerConfig(computation_timeout=0.1)  # Very short timeout
        
        async def slow_handler():
            await asyncio.sleep(0.2)  # Longer than timeout
            return "Should not reach here"
        
        class TestServer(BaseMCPServer):
            def _register_tools(self):
                pass
        
        server = TestServer(config)
        wrapped = server._create_wrapped_handler(slow_handler)
        
        result = await wrapped()
        assert "timed out" in result.lower()
    
    @pytest.mark.asyncio
    async def test_wrapped_handler_error_handling(self):
        """Test that wrapped handlers handle errors properly."""
        async def error_handler():
            raise ValueError("Test error")
        
        class TestServer(BaseMCPServer):
            def _register_tools(self):
                pass
        
        server = TestServer(ServerConfig())
        wrapped = server._create_wrapped_handler(error_handler)
        
        result = await wrapped()
        assert "Error: Test error" == result
    
    @pytest.mark.asyncio
    async def test_wrapped_handler_no_timeout(self):
        """Test wrapped handler with timeout disabled."""
        config = ServerConfig(computation_timeout=0)  # Timeout disabled
        
        async def normal_handler():
            return "success"
        
        class TestServer(BaseMCPServer):
            def _register_tools(self):
                pass
        
        server = TestServer(config)
        wrapped = server._create_wrapped_handler(normal_handler)
        
        result = await wrapped()
        assert result == "success"

class TestBaseMCPServerResourceRegistration:
    """Test resource registration functionality."""
    
    def test_register_resources_enabled(self):
        """Test resource registration when enabled."""
        config = ServerConfig(enable_resources=True)
        
        class TestServer(BaseMCPServer):
            def _register_tools(self):
                pass
        
        server = TestServer(config)
        assert server.config.enable_resources is True
    
    def test_register_resources_disabled(self):
        """Test that resource registration is disabled when configured."""
        config = ServerConfig(enable_resources=False)
        
        class TestServer(BaseMCPServer):
            def _register_tools(self):
                pass
        
        server = TestServer(config)
        assert server.config.enable_resources is False

class TestBaseMCPServerSchemaConversion:
    """Test JSON schema conversion functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        class TestServer(BaseMCPServer):
            def _register_tools(self):
                pass
        
        self.server = TestServer(ServerConfig())
    
    def test_convert_empty_parameters(self):
        """Test conversion of empty parameters."""
        result = self.server.convert_to_json_schema({})
        expected = {"type": "object", "properties": {}}
        assert result == expected
    
    def test_convert_none_parameters(self):
        """Test conversion of None parameters."""
        result = self.server.convert_to_json_schema(None)
        expected = {"type": "object", "properties": {}}
        assert result == expected
    
    def test_convert_basic_types(self):
        """Test conversion of basic parameter types."""
        parameters = {
            "str_param": {"type": "string", "description": "A string parameter"},
            "int_param": {"type": "integer", "required": True},
            "float_param": {"type": "number"},
            "bool_param": {"type": "boolean"},
            "array_param": {"type": "array"}
        }
        
        result = self.server.convert_to_json_schema(parameters)
        
        assert result["type"] == "object"
        assert "properties" in result
        
        # Check string parameter
        assert result["properties"]["str_param"]["type"] == "string"
        assert result["properties"]["str_param"]["description"] == "A string parameter"
        
        # Check integer parameter
        assert result["properties"]["int_param"]["type"] == "integer"
        
        # Check required fields
        assert "required" in result
        assert "int_param" in result["required"]
        assert "str_param" not in result["required"]
    
    def test_convert_type_aliases(self):
        """Test conversion of type aliases."""
        parameters = {
            "int_alias": {"type": "int"},
            "float_alias": {"type": "float"}
        }
        
        result = self.server.convert_to_json_schema(parameters)
        
        assert result["properties"]["int_alias"]["type"] == "integer"
        assert result["properties"]["float_alias"]["type"] == "number"
    
    def test_convert_unknown_types(self):
        """Test conversion of unknown types defaults to string."""
        parameters = {
            "unknown_param": {"type": "unknown_type"}
        }
        
        result = self.server.convert_to_json_schema(parameters)
        
        assert result["properties"]["unknown_param"]["type"] == "string"
    
    def test_convert_non_dict_parameters(self):
        """Test conversion when parameter spec is not a dict."""
        parameters = {
            "simple_param": "not_a_dict"
        }
        
        result = self.server.convert_to_json_schema(parameters)
        
        assert result["properties"]["simple_param"]["type"] == "string"
        assert "Parameter: simple_param" in result["properties"]["simple_param"]["description"]

class TestBaseMCPServerStdioTransport:
    """Test stdio transport functionality."""
    
    @pytest.mark.asyncio
    async def test_run_stdio_with_mcp_server(self):
        """Test stdio transport with MCP server available."""
        config = ServerConfig()
        
        class TestServer(BaseMCPServer):
            def _register_tools(self):
                pass
        
        server = TestServer(config)
        
        # Mock stdin to return empty immediately (EOF)
        with patch('sys.stdin', StringIO('')), \
             patch('asyncio.get_event_loop') as mock_loop:
            
            mock_loop_instance = MagicMock()
            mock_loop.return_value = mock_loop_instance
            future = asyncio.Future()
            future.set_result('')  # EOF
            mock_loop_instance.run_in_executor.return_value = future
            
            # This should complete without error
            await server.run_stdio()
    
    @pytest.mark.asyncio
    async def test_run_stdio_invalid_json(self):
        """Test stdio handling of invalid JSON."""
        config = ServerConfig()
        
        class TestServer(BaseMCPServer):
            def _register_tools(self):
                pass
        
        server = TestServer(config)
        
        # Mock stdin with invalid JSON then EOF
        with patch('builtins.print') as mock_print, \
             patch('asyncio.get_event_loop') as mock_loop:
            
            mock_loop_instance = MagicMock()
            mock_loop.return_value = mock_loop_instance
            
            def side_effect(*args, **kwargs):
                future = asyncio.Future()
                if not hasattr(side_effect, 'called'):
                    side_effect.called = True
                    future.set_result('invalid json\n')
                else:
                    future.set_result('')  # EOF
                return future
            
            mock_loop_instance.run_in_executor.side_effect = side_effect
            
            await server.run_stdio()
            
            # Should have printed error response
            mock_print.assert_called()

class TestBaseMCPServerHttpTransport:
    """Test HTTP transport functionality."""
    
    @pytest.mark.asyncio
    async def test_run_http_missing_dependencies(self):
        """Test HTTP transport when FastAPI dependencies are missing."""
        config = ServerConfig(transport="http")
        
        with patch('builtins.__import__', side_effect=ImportError("No module named 'fastapi'")), \
             patch('chuk_mcp_function_server.base_server.logger') as mock_logger:
            
            class TestServer(BaseMCPServer):
                def _register_tools(self):
                    pass
            
            server = TestServer(config)
            await server.run_http()
            
            # Should log error about missing dependencies
            mock_logger.error.assert_called()

class TestBaseMCPServerMainRun:
    """Test the main run method and transport selection."""
    
    @pytest.mark.asyncio
    async def test_run_stdio_transport(self):
        """Test run method with stdio transport."""
        config = ServerConfig(transport="stdio")
        
        class TestServer(BaseMCPServer):
            def _register_tools(self):
                pass
            
            async def run_stdio(self):
                self.stdio_called = True
        
        server = TestServer(config)
        await server.run()
        
        assert hasattr(server, 'stdio_called')
        assert server.stdio_called
    
    @pytest.mark.asyncio
    async def test_run_http_transport(self):
        """Test run method with HTTP transport."""
        config = ServerConfig(transport="http")
        
        class TestServer(BaseMCPServer):
            def _register_tools(self):
                pass
            
            async def run_http(self):
                self.http_called = True
        
        server = TestServer(config)
        await server.run()
        
        assert hasattr(server, 'http_called')
        assert server.http_called
    
    @pytest.mark.asyncio
    async def test_run_unknown_transport(self):
        """Test run method with unknown transport."""
        config = ServerConfig(transport="stdio")  # Start with valid
        
        with patch('chuk_mcp_function_server.base_server.logger') as mock_logger:
            class TestServer(BaseMCPServer):
                def _register_tools(self):
                    pass
            
            server = TestServer(config)
            server.config.transport = "unknown"  # Change after validation
            await server.run()
            
            # Should log error about unknown transport
            mock_logger.error.assert_called()

class TestBaseMCPServerAbstractMethods:
    """Test abstract method requirements."""
    
    def test_abstract_register_tools_method(self):
        """Test that _register_tools must be implemented."""
        config = ServerConfig()
        
        # This should raise TypeError because _register_tools is not implemented
        with pytest.raises(TypeError):
            BaseMCPServer(config)
    
    def test_concrete_implementation_works(self):
        """Test that concrete implementation with _register_tools works."""
        config = ServerConfig()
        
        class ConcreteServer(BaseMCPServer):
            def _register_tools(self):
                # Concrete implementation
                pass
        
        # Should not raise any errors
        server = ConcreteServer(config)
        assert server is not None

class TestBaseMCPServerIntegration:
    """Integration tests for BaseMCPServer functionality."""
    
    def test_full_server_lifecycle(self):
        """Test complete server initialization and basic operations."""
        config = ServerConfig(
            server_name="integration-test-server",
            enable_tools=True,
            enable_resources=True,
            log_level="DEBUG"
        )
        
        class IntegrationTestServer(BaseMCPServer):
            def _register_tools(self):
                async def test_integration_tool(message: str) -> str:
                    return f"Processed: {message}"
                
                # Test the schema conversion
                schema = self.convert_to_json_schema({
                    "message": {"type": "string", "required": True}
                })
                
                # Verify schema is correct
                assert schema["type"] == "object"
                assert "message" in schema["properties"]
                assert schema["properties"]["message"]["type"] == "string"
        
        server = IntegrationTestServer(config)
        
        # Verify server was properly initialized
        assert server.config.server_name == "integration-test-server"
        assert server.mcp_server is not None
        
        # Test schema conversion
        schema = server.convert_to_json_schema({
            "param1": {"type": "string", "required": True},
            "param2": {"type": "integer", "default": 42}
        })
        
        assert schema["type"] == "object"
        assert "param1" in schema["properties"]
        assert "param2" in schema["properties"]
        assert "param1" in schema["required"]
        assert "param2" not in schema.get("required", [])

if __name__ == "__main__":
    pytest.main([__file__])