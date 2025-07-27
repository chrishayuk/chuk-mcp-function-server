#!/usr/bin/env python3
# examples/debug_setup.py
"""
Debug script to check the setup and help diagnose issues.
"""

import sys
from pathlib import Path

def check_file_structure():
    """Check if the required files exist."""
    print("🔍 Checking File Structure")
    print("=" * 40)
    
    current_dir = Path.cwd()
    print(f"📁 Current directory: {current_dir}")
    
    # Check for source files
    required_files = [
        "src/chuk_mcp_function_server/__init__.py",
        "src/chuk_mcp_function_server/base_server.py",
        "src/chuk_mcp_function_server/config.py",
        "src/chuk_mcp_function_server/function_filter.py",
        "src/chuk_mcp_function_server/cli.py",
        "src/chuk_mcp_function_server/_version.py"
    ]
    
    print("\n📋 Required source files:")
    all_exist = True
    for file_path in required_files:
        path = Path(file_path)
        exists = path.exists()
        status = "✅" if exists else "❌"
        print(f"   {status} {file_path}")
        if not exists:
            all_exist = False
    
    # Check for example files
    required_example_files = [
        "examples/weather_calculations_server.py"
    ]
    
    optional_example_files = [
        "examples/weather_calculations_stdio_client.py",
        "examples/weather_calculations_http_client.py"
    ]
    
    print("\n📋 Required example files:")
    for file_path in required_example_files:
        path = Path(file_path)
        exists = path.exists()
        status = "✅" if exists else "❌"
        print(f"   {status} {file_path}")
    
    print("\n📋 Optional example files:")
    for file_path in optional_example_files:
        path = Path(file_path)
        exists = path.exists()
        status = "✅" if exists else "⚠️"
        print(f"   {status} {file_path}")
    
    return all_exist

def check_python_imports():
    """Check if the modules can be imported."""
    print("\n🐍 Checking Python Imports")
    print("=" * 40)
    
    # Add src to path
    src_path = Path.cwd() / "src"
    if src_path.exists():
        sys.path.insert(0, str(src_path))
        print(f"✅ Added {src_path} to Python path")
    else:
        print(f"❌ Source directory not found: {src_path}")
        return False
    
    # Try importing modules
    modules_to_test = [
        "chuk_mcp_function_server",
        "chuk_mcp_function_server.base_server",
        "chuk_mcp_function_server.config",
        "chuk_mcp_function_server.function_filter",
        "chuk_mcp_function_server.cli"
    ]
    
    all_imported = True
    for module_name in modules_to_test:
        try:
            __import__(module_name)
            print(f"✅ {module_name}")
        except ImportError as e:
            print(f"❌ {module_name}: {e}")
            all_imported = False
    
    return all_imported

def check_dependencies():
    """Check for required dependencies."""
    print("\n📦 Checking Dependencies")
    print("=" * 40)
    
    dependencies = [
        ("yaml", "PyYAML"),
        ("asyncio", "asyncio (built-in)"),
        ("json", "json (built-in)"),
        ("logging", "logging (built-in)"),
        ("dataclasses", "dataclasses (built-in)"),
        ("pathlib", "pathlib (built-in)")
    ]
    
    optional_deps = [
        ("httpx", "httpx (for HTTP client)"),
        ("fastapi", "FastAPI (for HTTP server)"),
        ("uvicorn", "uvicorn (for HTTP server)")
    ]
    
    print("Required dependencies:")
    for module, desc in dependencies:
        try:
            __import__(module)
            print(f"   ✅ {desc}")
        except ImportError:
            print(f"   ❌ {desc}")
    
    print("\nOptional dependencies:")
    for module, desc in optional_deps:
        try:
            __import__(module)
            print(f"   ✅ {desc}")
        except ImportError:
            print(f"   ⚠️ {desc} (not available)")

def test_weather_server_import():
    """Test importing the weather server."""
    print("\n🌤️ Testing Weather Server Import")
    print("=" * 40)
    
    weather_server_path = Path("examples/weather_server.py")
    if not weather_server_path.exists():
        print(f"❌ Weather server not found: {weather_server_path}")
        return False
    
    # Add current directory to path for examples
    sys.path.insert(0, str(Path.cwd()))
    
    try:
        # Method 1: Try adding examples to path and importing
        examples_path = Path("examples")
        if examples_path.exists():
            sys.path.insert(0, str(examples_path.absolute()))
        
        import weather_server
        print("✅ Weather server imported successfully")
        
        # Try to create the server class
        from weather_server import WeatherMCPServer, WeatherServerConfig
        config = WeatherServerConfig(transport="stdio")
        print("✅ WeatherServerConfig created successfully")
        
        # Note: Don't actually create the server as it might start listening
        print("✅ Weather server classes are working")
        return True
        
    except Exception as e:
        print(f"❌ Weather server import failed (method 1): {e}")
        print(f"   Error details: {type(e).__name__}: {str(e)}")
        
        # Method 2: Try importing directly as a file
        try:
            print("🔄 Trying alternative import method...")
            import importlib.util
            spec = importlib.util.spec_from_file_location("weather_server", "examples/weather_server.py")
            weather_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(weather_module)
            print("✅ Weather server imported via file path!")
            
            # Check if classes exist
            if hasattr(weather_module, 'WeatherMCPServer') and hasattr(weather_module, 'WeatherServerConfig'):
                print("✅ Weather server classes found!")
                return True
            else:
                print("❌ Weather server classes not found in module")
                return False
                
        except Exception as alt_e:
            print(f"❌ Alternative import also failed: {alt_e}")
            print(f"   Error details: {type(alt_e).__name__}: {str(alt_e)}")
            return False

def suggest_fixes():
    """Suggest fixes for common issues."""
    print("\n💡 Suggested Fixes")
    print("=" * 30)
    
    print("If you're missing source files:")
    print("   1. Make sure you have the src/chuk_mcp_function_server/ directory")
    print("   2. Copy all the source files from the documents into src/chuk_mcp_function_server/")
    print("   3. Make sure __init__.py exists in the package directory")
    
    print("\nIf imports are failing:")
    print("   1. Check that all files are in the correct locations")
    print("   2. Ensure there are no syntax errors in the source files")
    print("   3. Try running: python -c 'import sys; print(sys.path)'")
    
    print("\nIf dependencies are missing:")
    print("   1. Install PyYAML: pip install PyYAML")
    print("   2. For HTTP support: pip install fastapi uvicorn httpx")
    
    print("\nTo test manually:")
    print("   1. Try: python examples/weather_calculations_server.py --help")
    print("   2. Try: python -c 'from examples.weather_calculations_server import WeatherCalculationsMCPServer'")
    print("   3. Try: python examples/weather_calculations_stdio_client.py")

def main():
    """Main debug function."""
    print("🔧 Chuk MCP Function Server - Debug Setup")
    print("=" * 50)
    
    files_ok = check_file_structure()
    imports_ok = check_python_imports() if files_ok else False
    check_dependencies()
    
    if files_ok and imports_ok:
        # Simple test of weather calculations server
        weather_calc_ok = True
        try:
            examples_path = Path("examples")
            if examples_path.exists():
                sys.path.insert(0, str(examples_path.absolute()))
            
            import weather_calculations_server
            from weather_calculations_server import WeatherCalculationsMCPServer, WeatherCalculationsServerConfig
            config = WeatherCalculationsServerConfig(transport="stdio")
            print("\n🧮 Weather Calculations Server Test:")
            print("✅ Weather calculations server imported successfully")
            print("✅ WeatherCalculationsServerConfig created successfully")
            print("✅ Weather calculations server classes are working")
        except Exception as e:
            print(f"\n❌ Weather calculations server test failed: {e}")
            weather_calc_ok = False
        
        if weather_calc_ok:
            print("\n🎉 Setup looks good!")
            print("✅ All files found")
            print("✅ All imports working")
            print("✅ Weather calculations server can be imported")
            print("\nYou should be able to run:")
            print("   python examples/weather_calculations_server.py")
            print("   python examples/weather_calculations_stdio_client.py")
            print("   python examples/weather_calculations_http_client.py")
        else:
            suggest_fixes()
    else:
        suggest_fixes()

if __name__ == "__main__":
    main()