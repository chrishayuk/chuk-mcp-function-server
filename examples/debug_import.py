#!/usr/bin/env python3
# examples/debug_import.py
"""
Simple test to check what's actually in the weather_server.py file
"""

import sys
from pathlib import Path

# Add the src directory to the path
src_path = Path(__file__).parent.parent / "src"
if src_path.exists():
    sys.path.insert(0, str(src_path))

print("🔍 Testing direct import of weather server components...")
print("=" * 60)

# Test the basic imports that should work
try:
    from chuk_mcp_function_server import BaseMCPServer, ServerConfig, main
    print("✅ Basic imports work: BaseMCPServer, ServerConfig, main")
except ImportError as e:
    print(f"❌ Basic imports failed: {e}")
    sys.exit(1)

# Check what's actually in the weather_calculations_server.py file
weather_calc_server_path = Path("examples/weather_calculations_server.py")
if weather_calc_server_path.exists():
    print(f"\n📄 Reading weather_calculations_server.py to check imports...")
    with open(weather_calc_server_path, 'r') as f:
        content = f.read()
    
    # Look for the import statement
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if 'from chuk_mcp_function_server import' in line:
            print(f"Line {i+1}: {line}")
            # Show next few lines too
            for j in range(i+1, min(i+5, len(lines))):
                if lines[j].strip():
                    print(f"Line {j+1}: {lines[j]}")
                else:
                    break
            break
    
    # Check if GenericFunctionProvider is mentioned anywhere
    if "GenericFunctionProvider" in content:
        print("\n❌ Found GenericFunctionProvider in the file!")
        print("   This needs to be removed")
    else:
        print("\n✅ GenericFunctionProvider not found in file")
        
else:
    print("❌ weather_calculations_server.py not found")

# Try importing the weather server
print(f"\n🌤️ Testing weather server import...")
try:
    # Clear any cached modules first
    modules_to_clear = [name for name in sys.modules.keys() if 'weather_server' in name]
    for module in modules_to_clear:
        del sys.modules[module]
        print(f"   Cleared cached module: {module}")
    
    # Add examples directory to path temporarily
    examples_path = Path("examples")
    if examples_path.exists():
        sys.path.insert(0, str(examples_path.absolute()))
    
    # Now try importing
    import weather_server
    print("✅ Weather server imported successfully!")
    
    # Try importing the classes
    from weather_server import WeatherMCPServer, WeatherServerConfig
    print("✅ Weather server classes imported successfully!")
    
except Exception as e:
    print(f"❌ Weather server import failed: {e}")
    print(f"   Error type: {type(e).__name__}")
    
    # If it's still an import error about GenericFunctionProvider, there might be a cached file
    if "GenericFunctionProvider" in str(e):
        print("\n💡 Trying to clear Python cache files...")
        
        # Look for .pyc files
        for pyc_file in Path('.').rglob('*.pyc'):
            if 'weather_server' in str(pyc_file):
                print(f"   Found cache file: {pyc_file}")
                try:
                    pyc_file.unlink()
                    print(f"   ✅ Deleted: {pyc_file}")
                except Exception as del_e:
                    print(f"   ❌ Could not delete {pyc_file}: {del_e}")
        
        # Look for __pycache__ directories
        for pycache_dir in Path('.').rglob('__pycache__'):
            if any('weather_server' in str(f) for f in pycache_dir.iterdir()):
                print(f"   Found cache directory: {pycache_dir}")
                try:
                    import shutil
                    shutil.rmtree(pycache_dir)
                    print(f"   ✅ Deleted: {pycache_dir}")
                except Exception as del_e:
                    print(f"   ❌ Could not delete {pycache_dir}: {del_e}")
    
    # Try a different approach - import directly as a file
    print("\n🔄 Trying alternative import method...")
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("weather_server", "examples/weather_server.py")
        weather_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(weather_module)
        print("✅ Weather server imported via file path!")
        
        # Check if classes exist
        if hasattr(weather_module, 'WeatherMCPServer'):
            print("✅ WeatherMCPServer class found!")
        else:
            print("❌ WeatherMCPServer class not found")
            
        if hasattr(weather_module, 'WeatherServerConfig'):
            print("✅ WeatherServerConfig class found!")
        else:
            print("❌ WeatherServerConfig class not found")
            
    except Exception as alt_e:
        print(f"❌ Alternative import also failed: {alt_e}")
        print(f"   Error type: {type(alt_e).__name__}")
        
        # Print more detailed error info
        import traceback
        print("   Full traceback:")
        traceback.print_exc()

print(f"\n🏁 Test complete!")