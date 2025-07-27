#!/usr/bin/env python3
# tests/test_version.py
"""
Unit tests for the version module of chuk_mcp_function_server.
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# Debug information
print(f"Debug: Python path in test: {sys.path[:3]}...")
print(f"Debug: Current working directory: {os.getcwd()}")

# Import the module under test
try:
    from chuk_mcp_function_server._version import (
        get_version,
        get_version_info,
        _get_version_from_metadata,
        _get_version_from_pyproject,
        _get_version_from_env,
        VERSION,
        __version__
    )
    print("Debug: Successfully imported all version functions")
except ImportError as e:
    print(f"Debug: Import error details: {e}")
    print(f"Debug: Available modules in sys.modules: {[m for m in sys.modules.keys() if 'chuk' in m]}")
    # Don't skip, let the test fail with a clear error
    raise ImportError(f"Could not import chuk_mcp_function_server._version: {e}. Check that the package is properly installed or the src directory is in the Python path.")

class TestVersionConstants:
    """Test basic version constants and functions."""
    
    def test_module_constants_exist(self):
        """Test that module constants are properly set."""
        assert VERSION is not None
        assert __version__ is not None
        assert isinstance(VERSION, str)
        assert isinstance(__version__, str)
    
    def test_version_consistency(self):
        """Test that all version functions return consistent results."""
        assert VERSION == __version__
    
    def test_get_version_returns_string(self):
        """Test that get_version always returns a string."""
        version = get_version()
        assert isinstance(version, str)
        assert len(version) > 0
    
    def test_version_format(self):
        """Test that version follows a reasonable format."""
        version = get_version()
        # Should contain at least one digit and one dot
        assert any(c.isdigit() for c in version)
        assert '.' in version

class TestEnvironmentVersionDetection:
    """Test version detection from environment variables."""
    
    def test_env_variable_present(self):
        """Test reading version from environment variable."""
        test_version = "4.5.6-test"
        
        with patch.dict(os.environ, {'chuk_mcp_function_server_VERSION': test_version}):
            version = _get_version_from_env()
            assert version == test_version
    
    def test_env_variable_absent(self):
        """Test behavior when environment variable is not set."""
        # Create a clean environment without our test variable
        clean_env = {k: v for k, v in os.environ.items() if k != 'chuk_mcp_function_server_VERSION'}
        with patch.dict(os.environ, clean_env, clear=True):
            version = _get_version_from_env()
            assert version is None
    
    def test_env_variable_empty(self):
        """Test behavior when environment variable is empty."""
        with patch.dict(os.environ, {'chuk_mcp_function_server_VERSION': ''}):
            version = _get_version_from_env()
            assert version == ''

class TestMetadataVersionDetection:
    """Test version detection from package metadata."""
    
    @patch('importlib.metadata.version')
    def test_metadata_success(self, mock_version):
        """Test successful metadata detection."""
        mock_version.return_value = "2.5.1"
        
        version = _get_version_from_metadata()
        assert version == "2.5.1"
        mock_version.assert_called_once_with("chuk-mcp-function-server")
    
    @patch('importlib.metadata.version')
    def test_metadata_package_not_found(self, mock_version):
        """Test handling when package is not found in metadata."""
        # Mock the PackageNotFoundError
        from importlib.metadata import PackageNotFoundError
        mock_version.side_effect = PackageNotFoundError("chuk-mcp-function-server")
        
        version = _get_version_from_metadata()
        assert version is None
    
    @patch('importlib.metadata.version')
    def test_metadata_import_error(self, mock_version):
        """Test handling when importlib.metadata is not available."""
        mock_version.side_effect = ImportError("No module named 'importlib.metadata'")
        
        version = _get_version_from_metadata()
        assert version is None

class TestVersionInfo:
    """Test version info functionality."""
    
    def test_get_version_info_structure(self):
        """Test that get_version_info returns expected structure."""
        info = get_version_info()
        
        assert isinstance(info, dict)
        assert 'version' in info
        assert 'python_version' in info
        assert 'detection_method' in info
        assert 'available_methods' in info
        
        assert isinstance(info['version'], str)
        assert isinstance(info['python_version'], str)
        assert isinstance(info['available_methods'], list)
    
    def test_get_version_info_python_version(self):
        """Test that python_version is correctly captured."""
        info = get_version_info()
        assert info['python_version'] == sys.version

class TestVersionPriority:
    """Test version detection priority order."""
    
    @patch('chuk_mcp_function_server._version._get_version_from_metadata')
    @patch('chuk_mcp_function_server._version._get_version_from_pyproject')
    @patch('chuk_mcp_function_server._version._get_version_from_env')
    def test_priority_metadata_wins(self, mock_env, mock_pyproject, mock_metadata):
        """Test that metadata has highest priority."""
        mock_metadata.return_value = "1.0.0-metadata"
        mock_pyproject.return_value = "1.0.0-pyproject"
        mock_env.return_value = "1.0.0-env"
        
        version = get_version()
        assert version == "1.0.0-metadata"
    
    @patch('chuk_mcp_function_server._version._get_version_from_metadata')
    @patch('chuk_mcp_function_server._version._get_version_from_pyproject')
    @patch('chuk_mcp_function_server._version._get_version_from_env')
    def test_priority_pyproject_second(self, mock_env, mock_pyproject, mock_metadata):
        """Test that pyproject has second priority."""
        mock_metadata.return_value = None
        mock_pyproject.return_value = "1.0.0-pyproject"
        mock_env.return_value = "1.0.0-env"
        
        version = get_version()
        assert version == "1.0.0-pyproject"
    
    @patch('chuk_mcp_function_server._version._get_version_from_metadata')
    @patch('chuk_mcp_function_server._version._get_version_from_pyproject')
    @patch('chuk_mcp_function_server._version._get_version_from_env')
    def test_priority_env_third(self, mock_env, mock_pyproject, mock_metadata):
        """Test that environment has third priority."""
        mock_metadata.return_value = None
        mock_pyproject.return_value = None
        mock_env.return_value = "1.0.0-env"
        
        version = get_version()
        assert version == "1.0.0-env"
    
    @patch('chuk_mcp_function_server._version._get_version_from_metadata')
    @patch('chuk_mcp_function_server._version._get_version_from_pyproject')
    @patch('chuk_mcp_function_server._version._get_version_from_env')
    def test_fallback_version(self, mock_env, mock_pyproject, mock_metadata):
        """Test fallback version when all methods fail."""
        mock_metadata.return_value = None
        mock_pyproject.return_value = None
        mock_env.return_value = None
        
        version = get_version()
        assert version == "0.1.0"

if __name__ == "__main__":
    pytest.main([__file__])