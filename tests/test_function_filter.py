#!/usr/bin/env python3
# tests/test_function_filter.py
"""
Unit tests for the generic function_filter module of chuk_mcp_function_server.
"""

import inspect
import pytest
from unittest.mock import patch, MagicMock
from typing import Union

# Import the modules under test
try:
    from chuk_mcp_function_server.function_filter import (
        FunctionFilter,
        GenericFunctionSpec,
        GenericFunctionProvider,
        FunctionSpec,
        FunctionProvider
    )
    from chuk_mcp_function_server.config import ServerConfig
except ImportError as e:
    raise ImportError(f"Could not import function_filter modules: {e}")

class TestGenericFunctionSpec:
    """Test the GenericFunctionSpec class."""
    
    def test_basic_properties(self):
        """Test basic properties of GenericFunctionSpec."""
        def sample_func(x: int, y: str) -> float:
            return float(x)
        
        spec = GenericFunctionSpec("test_func", "test_domain", "test_category", sample_func)
        
        assert spec.function_name == "test_func"
        assert spec.namespace == "test_domain"
        assert spec.category == "test_category"
        assert spec.description == "test_func function from test_domain"
        assert spec.function_ref == sample_func
        assert spec.is_async_native is True
        assert spec.cache_strategy == "none"
    
    def test_custom_description(self):
        """Test custom description in GenericFunctionSpec."""
        def sample_func():
            pass
        
        spec = GenericFunctionSpec(
            "test_func", "domain", "category", sample_func, 
            description="Custom description"
        )
        
        assert spec.description == "Custom description"
    
    def test_parameter_extraction_with_annotations(self):
        """Test parameter extraction from function with type annotations."""
        def annotated_func(x: int, y: str, z: float, flag: bool) -> None:
            pass
        
        spec = GenericFunctionSpec("annotated", "domain", "category", annotated_func)
        
        assert "x" in spec.parameters
        assert spec.parameters["x"]["type"] == "integer"
        assert spec.parameters["x"]["required"] is True
        assert spec.parameters["y"]["type"] == "string"
        assert spec.parameters["z"]["type"] == "number"
        assert spec.parameters["flag"]["type"] == "boolean"
    
    def test_parameter_extraction_with_defaults(self):
        """Test parameter extraction with default values."""
        def func_with_defaults(x: int, y: str = "default", z: bool = True) -> None:
            pass
        
        spec = GenericFunctionSpec("defaults", "domain", "category", func_with_defaults)
        
        assert spec.parameters["x"]["required"] is True
        assert spec.parameters["y"]["required"] is False
        assert spec.parameters["y"]["default"] == "default"
        assert spec.parameters["z"]["required"] is False
        assert spec.parameters["z"]["default"] is True
    
    def test_parameter_extraction_union_types(self):
        """Test parameter extraction with Union types."""
        def union_func(value: Union[int, float]) -> None:
            pass
        
        spec = GenericFunctionSpec("union", "domain", "category", union_func)
        
        assert "value" in spec.parameters
        assert spec.parameters["value"]["type"] == "number"
    
    def test_parameter_extraction_no_annotations(self):
        """Test parameter extraction from function without annotations."""
        def no_annotations_func(x, y, z):
            pass
        
        spec = GenericFunctionSpec("no_annotations", "domain", "category", no_annotations_func)
        
        assert "x" in spec.parameters
        assert spec.parameters["x"]["type"] == "any"
        assert spec.parameters["y"]["type"] == "any"
        assert spec.parameters["z"]["type"] == "any"
    
    def test_normalize_type_annotation(self):
        """Test type annotation normalization."""
        def dummy_func():
            pass
        
        spec = GenericFunctionSpec("dummy", "domain", "category", dummy_func)
        
        # Test various type mappings
        assert spec._normalize_type_annotation(int) == "integer"
        assert spec._normalize_type_annotation(float) == "number"
        assert spec._normalize_type_annotation(str) == "string"
        assert spec._normalize_type_annotation(bool) == "boolean"
        assert spec._normalize_type_annotation(list) == "array"
        assert spec._normalize_type_annotation(dict) == "object"
    
    def test_parameter_extraction_error_handling(self):
        """Test parameter extraction handles errors gracefully."""
        # Create a mock function that will cause inspect.signature to fail
        mock_func = MagicMock()
        mock_func.__name__ = "error_func"
        
        with patch('inspect.signature', side_effect=Exception("Signature error")):
            spec = GenericFunctionSpec("error", "domain", "category", mock_func)
            assert spec.parameters == {}

class TestGenericFunctionProvider:
    """Test the GenericFunctionProvider class."""
    
    def test_initialization(self):
        """Test provider initialization."""
        provider = GenericFunctionProvider("test_provider")
        
        assert provider.get_provider_name() == "test_provider"
        assert provider.get_functions() == {}
    
    def test_register_function(self):
        """Test manual function registration."""
        provider = GenericFunctionProvider("test_provider")
        
        def test_func():
            pass
        
        spec = GenericFunctionSpec("test", "domain", "category", test_func)
        provider.register_function("domain::test", spec)
        
        functions = provider.get_functions()
        assert "domain::test" in functions
        assert functions["domain::test"] == spec
    
    def test_register_from_module(self):
        """Test registering functions from a module."""
        provider = GenericFunctionProvider("module_provider")
        
        def public_func():
            pass
        
        def _private_func():
            pass
        
        def excluded_func():
            pass
        
        # Create a simple mock module class that avoids recursion
        class MockModule:
            def __init__(self):
                self.public_func = public_func
                self._private_func = _private_func
                self.excluded_func = excluded_func
        
        mock_module = MockModule()
        
        # Mock only dir() to return our specific function names
        with patch('builtins.dir') as mock_dir:
            mock_dir.return_value = ['public_func', '_private_func', 'excluded_func']
            
            provider.register_from_module(
                mock_module, 
                "test_namespace", 
                "test_category",
                exclude_names=["excluded_func"]
            )
        
        functions = provider.get_functions()
        
        # Should only include public_func (not private or excluded)
        assert len(functions) == 1
        assert "test_namespace::public_func" in functions
        assert "test_namespace::_private_func" not in functions
        assert "test_namespace::excluded_func" not in functions
    
    def test_register_from_module_include_private(self):
        """Test registering functions including private ones."""
        provider = GenericFunctionProvider("module_provider")
        
        def public_func():
            pass
        
        def _private_func():
            pass
        
        # Create a simple mock module class that avoids recursion
        class MockModule:
            def __init__(self):
                self.public_func = public_func
                self._private_func = _private_func
        
        mock_module = MockModule()
        
        # Mock only dir() to return our specific function names  
        with patch('builtins.dir') as mock_dir:
            mock_dir.return_value = ['public_func', '_private_func']
            
            provider.register_from_module(
                mock_module, 
                "test_namespace", 
                "test_category",
                include_private=True
            )
        
        functions = provider.get_functions()
        
        # Should include both public and private functions
        assert len(functions) == 2
        assert "test_namespace::public_func" in functions
        assert "test_namespace::_private_func" in functions

class TestFunctionFilter:
    """Test the generic FunctionFilter class."""
    
    def test_initialization_empty(self):
        """Test FunctionFilter initialization with no providers."""
        config = ServerConfig()
        filter_obj = FunctionFilter(config)
        
        assert filter_obj.config == config
        assert filter_obj.providers == []
        assert filter_obj._all_functions is None
        assert filter_obj._filtered_functions is None
    
    def test_initialization_with_providers(self):
        """Test FunctionFilter initialization with providers."""
        config = ServerConfig()
        provider1 = GenericFunctionProvider("provider1")
        provider2 = GenericFunctionProvider("provider2")
        
        filter_obj = FunctionFilter(config, [provider1, provider2])
        
        assert len(filter_obj.providers) == 2
        assert provider1 in filter_obj.providers
        assert provider2 in filter_obj.providers
    
    def test_add_provider(self):
        """Test adding a provider to the filter."""
        config = ServerConfig()
        filter_obj = FunctionFilter(config)
        provider = GenericFunctionProvider("test_provider")
        
        filter_obj.add_provider(provider)
        
        assert provider in filter_obj.providers
        assert filter_obj._all_functions is None  # Cache should be reset
    
    def test_remove_provider(self):
        """Test removing a provider from the filter."""
        config = ServerConfig()
        provider1 = GenericFunctionProvider("provider1")
        provider2 = GenericFunctionProvider("provider2")
        filter_obj = FunctionFilter(config, [provider1, provider2])
        
        filter_obj.remove_provider("provider1")
        
        assert len(filter_obj.providers) == 1
        assert provider2 in filter_obj.providers
        assert provider1 not in filter_obj.providers
    
    def test_get_all_functions_with_providers(self):
        """Test getting all functions from multiple providers."""
        config = ServerConfig()
        
        # Create providers with functions
        provider1 = GenericFunctionProvider("math")
        provider2 = GenericFunctionProvider("text")
        
        def add_func():
            pass
        def upper_func():
            pass
        
        spec1 = GenericFunctionSpec("add", "math", "arithmetic", add_func)
        spec2 = GenericFunctionSpec("upper", "text", "string", upper_func)
        
        provider1.register_function("math::add", spec1)
        provider2.register_function("text::upper", spec2)
        
        filter_obj = FunctionFilter(config, [provider1, provider2])
        
        all_functions = filter_obj.get_all_functions()
        
        assert len(all_functions) == 2
        assert "math::add" in all_functions
        assert "text::upper" in all_functions
    
    def test_get_all_functions_caching(self):
        """Test that get_all_functions caches results."""
        config = ServerConfig()
        provider = GenericFunctionProvider("test")
        filter_obj = FunctionFilter(config, [provider])
        
        def test_func():
            pass
        
        spec = GenericFunctionSpec("test", "domain", "category", test_func)
        provider.register_function("domain::test", spec)
        
        # First call
        result1 = filter_obj.get_all_functions()
        assert len(result1) == 1
        
        # Add another function to provider
        spec2 = GenericFunctionSpec("test2", "domain", "category", test_func)
        provider.register_function("domain::test2", spec2)
        
        # Second call should return cached result
        result2 = filter_obj.get_all_functions()
        assert len(result2) == 1  # Should still be cached result
        assert result2 == result1
    
    @patch('chuk_mcp_function_server.function_filter.logger')
    def test_get_all_functions_error_handling(self, mock_logger):
        """Test error handling when provider fails."""
        config = ServerConfig()
        
        # Create a mock provider that raises an error
        mock_provider = MagicMock()
        mock_provider.get_provider_name.return_value = "error_provider"
        mock_provider.get_functions.side_effect = Exception("Provider error")
        
        filter_obj = FunctionFilter(config, [mock_provider])
        
        result = filter_obj.get_all_functions()
        
        assert result == {}
        mock_logger.error.assert_called()

class TestGenericFunctionFiltering:
    """Test generic function filtering logic."""
    
    def create_test_filter_with_functions(self, config: ServerConfig = None):
        """Create a filter with test functions for filtering tests."""
        if config is None:
            config = ServerConfig()
        
        provider = GenericFunctionProvider("test_provider")
        
        def func1(): pass
        def func2(): pass
        def func3(): pass
        def func4(): pass
        
        # Create diverse function specifications
        specs = [
            GenericFunctionSpec("add", "math", "arithmetic", func1),
            GenericFunctionSpec("subtract", "math", "arithmetic", func2),
            GenericFunctionSpec("upper", "text", "string", func3),
            GenericFunctionSpec("complex", "advanced", "special", func4),
        ]
        
        for spec in specs:
            provider.register_function(f"{spec.namespace}::{spec.function_name}", spec)
        
        filter_obj = FunctionFilter(config, [provider])
        return filter_obj
    
    def test_no_filtering(self):
        """Test that when no filters are applied, all functions are returned."""
        filter_obj = self.create_test_filter_with_functions()
        
        all_functions = filter_obj.get_all_functions()
        filtered = filter_obj.get_filtered_functions()
        
        assert len(filtered) == len(all_functions)
        assert filtered == all_functions
    
    def test_function_whitelist_filtering(self):
        """Test filtering with function whitelist."""
        config = ServerConfig(function_whitelist=["add", "upper"])
        filter_obj = self.create_test_filter_with_functions(config)
        
        filtered = filter_obj.get_filtered_functions()
        
        assert len(filtered) == 2
        function_names = [spec.function_name for spec in filtered.values()]
        assert "add" in function_names
        assert "upper" in function_names
        assert "subtract" not in function_names
        assert "complex" not in function_names
    
    def test_function_blacklist_filtering(self):
        """Test filtering with function blacklist."""
        config = ServerConfig(function_blacklist=["subtract", "complex"])
        filter_obj = self.create_test_filter_with_functions(config)
        
        filtered = filter_obj.get_filtered_functions()
        
        assert len(filtered) == 2
        function_names = [spec.function_name for spec in filtered.values()]
        assert "add" in function_names
        assert "upper" in function_names
        assert "subtract" not in function_names
        assert "complex" not in function_names
    
    def test_domain_whitelist_filtering(self):
        """Test filtering with domain whitelist."""
        config = ServerConfig(domain_whitelist=["math"])
        filter_obj = self.create_test_filter_with_functions(config)
        
        filtered = filter_obj.get_filtered_functions()
        
        assert len(filtered) == 2
        domains = [spec.namespace for spec in filtered.values()]
        assert all(domain == "math" for domain in domains)
    
    def test_domain_blacklist_filtering(self):
        """Test filtering with domain blacklist."""
        config = ServerConfig(domain_blacklist=["advanced"])
        filter_obj = self.create_test_filter_with_functions(config)
        
        filtered = filter_obj.get_filtered_functions()
        
        assert len(filtered) == 3
        domains = [spec.namespace for spec in filtered.values()]
        assert "advanced" not in domains
    
    def test_category_filtering(self):
        """Test filtering with category whitelist."""
        config = ServerConfig(category_whitelist=["arithmetic"])
        filter_obj = self.create_test_filter_with_functions(config)
        
        filtered = filter_obj.get_filtered_functions()
        
        assert len(filtered) == 2
        categories = [spec.category for spec in filtered.values()]
        assert all(category == "arithmetic" for category in categories)
    
    def test_combined_filtering(self):
        """Test filtering with multiple filter types combined."""
        config = ServerConfig(
            domain_whitelist=["math", "text"],
            function_blacklist=["subtract"]
        )
        filter_obj = self.create_test_filter_with_functions(config)
        
        filtered = filter_obj.get_filtered_functions()
        
        assert len(filtered) == 2
        function_names = [spec.function_name for spec in filtered.values()]
        assert "add" in function_names
        assert "upper" in function_names
        assert "subtract" not in function_names  # Blacklisted
        assert "complex" not in function_names   # Not in domain whitelist

class TestFunctionFilterUtilities:
    """Test utility methods of FunctionFilter."""
    
    def test_get_function_stats(self):
        """Test function statistics generation."""
        config = ServerConfig(domain_whitelist=["math"])
        filter_obj = TestGenericFunctionFiltering().create_test_filter_with_functions(config)
        
        stats = filter_obj.get_function_stats()
        
        assert isinstance(stats, dict)
        assert "total_available" in stats
        assert "total_filtered" in stats
        assert "filter_ratio" in stats
        assert "domains_available" in stats
        assert "domains_filtered" in stats
        assert "categories_available" in stats
        assert "categories_filtered" in stats
        assert "providers" in stats
        assert "filtering_active" in stats
        
        assert stats["filtering_active"] is True
        assert stats["total_available"] == 4
        assert stats["total_filtered"] == 2
        assert stats["filter_ratio"] == 0.5
    
    def test_get_functions_by_domain(self):
        """Test organizing functions by domain."""
        filter_obj = TestGenericFunctionFiltering().create_test_filter_with_functions()
        
        by_domain = filter_obj.get_functions_by_domain()
        
        assert isinstance(by_domain, dict)
        assert "math" in by_domain
        assert "text" in by_domain
        assert "advanced" in by_domain
        assert len(by_domain["math"]) == 2
        assert "add" in by_domain["math"]
        assert "subtract" in by_domain["math"]
    
    def test_get_functions_by_category(self):
        """Test organizing functions by category."""
        filter_obj = TestGenericFunctionFiltering().create_test_filter_with_functions()
        
        by_category = filter_obj.get_functions_by_category()
        
        assert isinstance(by_category, dict)
        assert "arithmetic" in by_category
        assert "string" in by_category
        assert "special" in by_category
        assert len(by_category["arithmetic"]) == 2
    
    def test_find_function(self):
        """Test finding a function by name."""
        filter_obj = TestGenericFunctionFiltering().create_test_filter_with_functions()
        
        # Find existing function
        found = filter_obj.find_function("add")
        assert found is not None
        assert found.function_name == "add"
        assert found.namespace == "math"
        
        # Try to find non-existent function
        not_found = filter_obj.find_function("nonexistent")
        assert not_found is None
    
    def test_reset_cache(self):
        """Test cache reset functionality."""
        filter_obj = TestGenericFunctionFiltering().create_test_filter_with_functions()
        
        # Prime the cache
        filter_obj.get_all_functions()
        filter_obj.get_filtered_functions()
        
        assert filter_obj._all_functions is not None
        assert filter_obj._filtered_functions is not None
        
        # Reset cache
        filter_obj.reset_cache()
        
        assert filter_obj._all_functions is None
        assert filter_obj._filtered_functions is None

class TestFilterCaching:
    """Test function filter caching behavior."""
    
    def test_filtered_functions_caching(self):
        """Test that filtered functions are cached properly."""
        filter_obj = TestGenericFunctionFiltering().create_test_filter_with_functions()
        
        # First call
        filtered1 = filter_obj.get_filtered_functions()
        assert len(filtered1) == 4
        
        # Second call should return cached result
        filtered2 = filter_obj.get_filtered_functions()
        
        assert filtered1 == filtered2
        assert filtered1 is filtered2  # Should be the same object (cached)

if __name__ == "__main__":
    pytest.main([__file__])