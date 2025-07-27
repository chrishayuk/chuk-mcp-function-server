#!/usr/bin/env python3
# src/chuk_mcp_function_server/function_filter.py
"""
Generic function filtering system for controlling which functions are exposed.
This module is domain-agnostic and can be used with any function provider.
"""

import logging
import inspect
from typing import Dict, Any, Optional, Protocol, Callable, List
from .config import ServerConfig

logger = logging.getLogger(__name__)

class FunctionSpec(Protocol):
    """Protocol for function specifications."""
    function_name: str
    namespace: str
    category: str
    description: str
    function_ref: Any
    is_async_native: bool
    cache_strategy: str
    parameters: Dict[str, Any]

class GenericFunctionSpec:
    """Generic function specification for any domain."""
    
    def __init__(self, name: str, namespace: str, category: str, func: Callable, 
                 description: Optional[str] = None, is_async: bool = True, 
                 cache_strategy: str = "none"):
        self.function_name = name
        self.namespace = namespace
        self.category = category
        self.description = description or f"{name} function from {namespace}"
        self.function_ref = func
        self.is_async_native = is_async
        self.cache_strategy = cache_strategy
        
        # Extract parameters from function signature
        self.parameters = self._extract_parameters(func)
    
    def _extract_parameters(self, func: Callable) -> Dict[str, Any]:
        """Extract parameters from function signature."""
        try:
            sig = inspect.signature(func)
            parameters = {}
            
            for param_name, param in sig.parameters.items():
                param_info = {"type": "any"}  # Default type
                
                if param.annotation != inspect.Parameter.empty:
                    param_type = self._normalize_type_annotation(param.annotation)
                    param_info["type"] = param_type
                
                # Check if parameter has a default value
                if param.default != inspect.Parameter.empty:
                    param_info["default"] = param.default
                    param_info["required"] = False
                else:
                    param_info["required"] = True
                
                parameters[param_name] = param_info
            
            return parameters
        except Exception as e:
            logger.debug(f"Could not extract parameters from {func}: {e}")
            return {}
    
    def _normalize_type_annotation(self, annotation) -> str:
        """Normalize type annotations to standard string representations."""
        type_str = str(annotation).replace('<class \'', '').replace('\'>', '')
        
        # Handle Union types
        if 'Union' in type_str or '|' in type_str:
            if any(t in type_str.lower() for t in ['int', 'float']):
                return "number"
            return "any"
        
        # Map common types
        type_mapping = {
            'int': 'integer',
            'float': 'number', 
            'bool': 'boolean',
            'str': 'string',
            'list': 'array',
            'dict': 'object'
        }
        
        for python_type, json_type in type_mapping.items():
            if python_type in type_str.lower():
                return json_type
        
        return "any"

class FunctionProvider(Protocol):
    """Protocol for function providers that can supply functions to the filter."""
    
    def get_functions(self) -> Dict[str, FunctionSpec]:
        """Get all available functions from this provider."""
        ...
    
    def get_provider_name(self) -> str:
        """Get the name of this function provider."""
        ...

class GenericFunctionProvider:
    """Generic function provider that can load functions from modules or registries."""
    
    def __init__(self, name: str):
        self.name = name
        self._functions: Dict[str, FunctionSpec] = {}
    
    def register_function(self, qualified_name: str, spec: FunctionSpec):
        """Register a function with this provider."""
        self._functions[qualified_name] = spec
    
    def register_from_module(self, module, namespace: str, category: str = "general",
                           include_private: bool = False, exclude_names: Optional[List[str]] = None):
        """Register functions from a Python module."""
        exclude_names = exclude_names or []
        
        for attr_name in dir(module):
            if self._should_include_attribute(attr_name, include_private, exclude_names):
                attr = getattr(module, attr_name)
                if callable(attr) and hasattr(attr, '__name__'):
                    qualified_name = f"{namespace}::{attr_name}"
                    spec = GenericFunctionSpec(
                        name=attr_name,
                        namespace=namespace,
                        category=category,
                        func=attr
                    )
                    self.register_function(qualified_name, spec)
    
    def _should_include_attribute(self, attr_name: str, include_private: bool, 
                                exclude_names: List[str]) -> bool:
        """Check if an attribute should be included."""
        if attr_name in exclude_names:
            return False
        
        if not include_private and attr_name.startswith('_'):
            return False
        
        return True
    
    def get_functions(self) -> Dict[str, FunctionSpec]:
        """Get all functions from this provider."""
        return self._functions.copy()
    
    def get_provider_name(self) -> str:
        """Get the name of this provider."""
        return self.name

class FunctionFilter:
    """Generic function filter that works with any function provider."""
    
    def __init__(self, config: ServerConfig, providers: Optional[List[FunctionProvider]] = None):
        self.config = config
        self.providers = providers or []
        self._all_functions: Optional[Dict[str, FunctionSpec]] = None
        self._filtered_functions: Optional[Dict[str, FunctionSpec]] = None
    
    def add_provider(self, provider: FunctionProvider):
        """Add a function provider to this filter."""
        self.providers.append(provider)
        self.reset_cache()
    
    def remove_provider(self, provider_name: str):
        """Remove a function provider by name."""
        self.providers = [p for p in self.providers if p.get_provider_name() != provider_name]
        self.reset_cache()
    
    def get_all_functions(self) -> Dict[str, FunctionSpec]:
        """Get all available functions from all providers."""
        if self._all_functions is None:
            self._all_functions = {}
            
            for provider in self.providers:
                try:
                    provider_functions = provider.get_functions()
                    self._all_functions.update(provider_functions)
                    logger.debug(f"Loaded {len(provider_functions)} functions from {provider.get_provider_name()}")
                except Exception as e:
                    logger.error(f"Error loading functions from {provider.get_provider_name()}: {e}")
            
            logger.info(f"Loaded total of {len(self._all_functions)} functions from {len(self.providers)} providers")
        
        return self._all_functions
    
    def get_filtered_functions(self) -> Dict[str, FunctionSpec]:
        """Get functions filtered according to configuration."""
        if self._filtered_functions is None:
            self._filtered_functions = self._apply_filters()
        return self._filtered_functions
    
    def _apply_filters(self) -> Dict[str, FunctionSpec]:
        """Apply all configured filters to the function list."""
        all_functions = self.get_all_functions()
        filtered = {}
        
        for qualified_name, func_spec in all_functions.items():
            if self._should_include_function(func_spec):
                filtered[qualified_name] = func_spec
        
        logger.info(f"Filtered {len(all_functions)} functions down to {len(filtered)}")
        return filtered
    
    def _should_include_function(self, func_spec: FunctionSpec) -> bool:
        """Determine if a function should be included based on filters."""
        
        # Check function whitelist (if specified, only these are allowed)
        if self.config.function_whitelist:
            if func_spec.function_name not in self.config.function_whitelist:
                return False
        
        # Check function blacklist
        if func_spec.function_name in self.config.function_blacklist:
            return False
        
        # Check domain whitelist (if specified, only these domains are allowed)
        if self.config.domain_whitelist:
            if func_spec.namespace not in self.config.domain_whitelist:
                return False
        
        # Check domain blacklist
        if func_spec.namespace in self.config.domain_blacklist:
            return False
        
        # Check category whitelist (if specified, only these categories are allowed)
        if self.config.category_whitelist:
            if func_spec.category not in self.config.category_whitelist:
                return False
        
        # Check category blacklist
        if func_spec.category in self.config.category_blacklist:
            return False
        
        return True
    
    def get_function_stats(self) -> Dict[str, Any]:
        """Get statistics about function filtering."""
        all_functions = self.get_all_functions()
        filtered_functions = self.get_filtered_functions()
        
        # Count by domain
        all_domains = {}
        filtered_domains = {}
        all_categories = {}
        filtered_categories = {}
        
        for func_spec in all_functions.values():
            domain = func_spec.namespace
            category = func_spec.category
            all_domains[domain] = all_domains.get(domain, 0) + 1
            all_categories[category] = all_categories.get(category, 0) + 1
        
        for func_spec in filtered_functions.values():
            domain = func_spec.namespace
            category = func_spec.category
            filtered_domains[domain] = filtered_domains.get(domain, 0) + 1
            filtered_categories[category] = filtered_categories.get(category, 0) + 1
        
        # Calculate ratios
        total_available = len(all_functions)
        total_filtered = len(filtered_functions)
        filter_ratio = total_filtered / total_available if total_available > 0 else 0
        
        return {
            "total_available": total_available,
            "total_filtered": total_filtered,
            "filter_ratio": filter_ratio,
            "domains_available": all_domains,
            "domains_filtered": filtered_domains,
            "categories_available": all_categories,
            "categories_filtered": filtered_categories,
            "providers": [p.get_provider_name() for p in self.providers],
            "filtering_active": bool(
                self.config.function_whitelist or 
                self.config.function_blacklist or
                self.config.domain_whitelist or 
                self.config.domain_blacklist or
                self.config.category_whitelist or 
                self.config.category_blacklist
            )
        }
    
    def get_functions_by_domain(self) -> Dict[str, List[str]]:
        """Get functions organized by domain."""
        filtered_functions = self.get_filtered_functions()
        by_domain = {}
        
        for qualified_name, func_spec in filtered_functions.items():
            domain = func_spec.namespace
            if domain not in by_domain:
                by_domain[domain] = []
            by_domain[domain].append(func_spec.function_name)
        
        return by_domain
    
    def get_functions_by_category(self) -> Dict[str, List[str]]:
        """Get functions organized by category."""
        filtered_functions = self.get_filtered_functions()
        by_category = {}
        
        for qualified_name, func_spec in filtered_functions.items():
            category = func_spec.category
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(func_spec.function_name)
        
        return by_category
    
    def find_function(self, name: str) -> Optional[FunctionSpec]:
        """Find a function by name in the filtered functions."""
        filtered_functions = self.get_filtered_functions()
        
        for func_spec in filtered_functions.values():
            if func_spec.function_name == name:
                return func_spec
        
        return None
    
    def reset_cache(self):
        """Reset the function cache to force reloading."""
        self._all_functions = None
        self._filtered_functions = None