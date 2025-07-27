#!/usr/bin/env python3
# examples/weather_calculations_stdio_client.py
"""
STDIO client for the Weather Calculations MCP Server.

This demonstrates pure weather calculation functions via MCP.
"""

import asyncio
import json
import subprocess
import sys
from typing import Dict, Any, Optional
from pathlib import Path

class WeatherCalculationsMCPClient:
    """Client for communicating with the Weather Calculations MCP Server via stdio."""
    
    def __init__(self, server_command: list = None):
        # Find the weather calculations server script
        current_dir = Path(__file__).parent
        possible_paths = [
            current_dir / "weather_calculations_server.py",
            Path("weather_calculations_server.py"),
            Path("examples/weather_calculations_server.py")
        ]
        
        server_path = None
        for path in possible_paths:
            if path.exists():
                server_path = path
                break
        
        if server_path:
            self.server_command = server_command or ["python", str(server_path)]
        else:
            self.server_command = server_command or ["python", "weather_calculations_server.py"]
        
        self.process = None
        self.message_id = 0
        print(f"🧮 Using weather calculations server command: {' '.join(self.server_command)}")
        
        # Check if server file exists
        if server_path and server_path.exists():
            print(f"✅ Found server at: {server_path}")
        else:
            print(f"⚠️ Warning: Server file not confirmed to exist")
            print("   Will attempt to run anyway...")
    
    async def start(self):
        """Start the weather calculations server process."""
        try:
            print("🚀 Starting weather calculations server process...")
            self.process = await asyncio.create_subprocess_exec(
                *self.server_command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Wait for server to start
            await asyncio.sleep(2.0)
            
            # Check if process started successfully
            if self.process.returncode is not None:
                stderr_data = await self.process.stderr.read()
                stdout_data = await self.process.stdout.read()
                error_msg = stderr_data.decode() if stderr_data else "No stderr"
                output_msg = stdout_data.decode() if stdout_data else "No stdout"
                print(f"❌ Process stdout: {output_msg}")
                print(f"❌ Process stderr: {error_msg}")
                raise RuntimeError(f"Weather calculations server failed to start. Return code: {self.process.returncode}")
            
            print("✅ Weather calculations server process started successfully")
            
        except FileNotFoundError:
            print(f"❌ Could not start server with command: {' '.join(self.server_command)}")
            print("💡 Possible solutions:")
            print("   1. Make sure weather_calculations_server.py is in the current directory")
            print("   2. Check that Python can find the server script")
            print("   3. Try running the server manually first:")
            print(f"      {' '.join(self.server_command)}")
            raise RuntimeError("Weather calculations server not found.")
        except Exception as e:
            print(f"❌ Failed to start weather calculations server: {e}")
            raise
    
    async def stop(self):
        """Stop the weather calculations server process gracefully."""
        if self.process:
            try:
                print("🛑 Stopping weather calculations server...")
                self.process.terminate()
                try:
                    await asyncio.wait_for(self.process.wait(), timeout=5.0)
                    print("✅ Weather calculations server stopped gracefully")
                except asyncio.TimeoutError:
                    print("⏰ Timeout waiting for graceful shutdown, force killing...")
                    self.process.kill()
                    await self.process.wait()
                    print("✅ Weather calculations server force stopped")
            except Exception as e:
                print(f"⚠️ Error stopping weather calculations server: {e}")
    
    def _next_id(self) -> int:
        """Get next message ID."""
        self.message_id += 1
        return self.message_id
    
    async def send_message(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send a message to the server and return the response."""
        if not self.process:
            raise RuntimeError("Weather calculations server not started")
        
        message = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": method
        }
        
        if params:
            message["params"] = params
        
        # Send message
        message_json = json.dumps(message) + "\n"
        print(f"📤 Sending: {method}")
        self.process.stdin.write(message_json.encode())
        await self.process.stdin.drain()
        
        # Read response with timeout
        try:
            response_line = await asyncio.wait_for(
                self.process.stdout.readline(), 
                timeout=15.0
            )
        except asyncio.TimeoutError:
            print("⏰ Server response timeout - checking if process is alive...")
            if self.process.returncode is not None:
                stderr_data = await self.process.stderr.read()
                error_msg = stderr_data.decode() if stderr_data else "Process terminated"
                raise RuntimeError(f"Weather calculations server died: {error_msg}")
            else:
                raise RuntimeError("Weather calculations server response timeout")
        
        if not response_line:
            # Check if process died
            if self.process.returncode is not None:
                stderr_data = await self.process.stderr.read()
                error_msg = stderr_data.decode() if stderr_data else "Process terminated"
                raise RuntimeError(f"Weather calculations server died: {error_msg}")
            else:
                raise RuntimeError("No response from weather calculations server")
        
        try:
            response_text = response_line.decode().strip()
            print(f"📥 Received response for {method}")
            response = json.loads(response_text)
            return response
        except json.JSONDecodeError as e:
            print(f"❌ Raw response: {response_line.decode()}")
            raise RuntimeError(f"Invalid JSON response: {e}")
    
    async def initialize(self):
        """Initialize the connection."""
        print("🔗 Initializing connection...")
        response = await self.send_message("initialize", {
            "protocolVersion": "2025-03-26",
            "clientInfo": {
                "name": "weather-calculations-client",
                "version": "1.0.0"
            }
        })
        
        if response.get("error") is not None:
            raise RuntimeError(f"Initialization failed: {response['error']}")
        
        # Send initialized notification
        init_msg = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }
        init_json = json.dumps(init_msg) + "\n"
        self.process.stdin.write(init_json.encode())
        await self.process.stdin.drain()
        
        print("✅ Initialized weather calculations connection")
        return response["result"]
    
    async def list_tools(self) -> list:
        """List available weather calculation tools."""
        response = await self.send_message("tools/list")
        if response.get("error") is not None:
            raise RuntimeError(f"Failed to list tools: {response['error']}")
        
        return response["result"]["tools"]
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Call a weather calculation tool."""
        response = await self.send_message("tools/call", {
            "name": name,
            "arguments": arguments
        })
        
        if response.get("error") is not None:
            raise RuntimeError(f"Tool call failed: {response['error']}")
        
        return response["result"]

def extract_result_content(result):
    """Extract content from MCP response."""
    if isinstance(result, dict) and "content" in result:
        content = result["content"][0]["text"]
        try:
            # Try to parse as JSON for pretty printing
            parsed = json.loads(content)
            return json.dumps(parsed, indent=2)
        except json.JSONDecodeError:
            return content
    else:
        return str(result)

async def test_basic_connectivity():
    """Test basic weather calculations server connectivity."""
    print("\n🔍 Testing Basic Weather Calculations Server Connectivity")
    print("=" * 60)
    
    client = WeatherCalculationsMCPClient()
    
    try:
        await client.start()
        
        print("🔗 Testing initialization...")
        init_result = await client.initialize()
        
        print("✅ Weather calculations server connected successfully!")
        server_info = init_result.get('serverInfo', {})
        print(f"📋 Server: {server_info.get('name', 'unknown')} v{server_info.get('version', 'unknown')}")
        
        # Test tool listing
        print("\n📋 Testing tool listing...")
        tools = await client.list_tools()
        print(f"🛠️ Available tools: {len(tools)}")
        for tool in tools:
            print(f"   • {tool['name']}: {tool.get('description', 'No description')}")
        
        # Test a simple operation
        print("\n🧪 Testing simple operation...")
        try:
            result = await client.call_tool("celsius_to_fahrenheit", {"celsius": 25})
            print("✅ celsius_to_fahrenheit(25) successful")
            content = extract_result_content(result)
            print("🧮 Temperature conversion result:")
            print(content)
        except Exception as e:
            print(f"❌ Tool execution failed: {e}")
            return False
        
        print("\n✅ Basic connectivity test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Basic connectivity test failed: {e}")
        return False
    finally:
        await client.stop()

async def demonstrate_temperature_conversions():
    """Demonstrate temperature conversion functions."""
    print("\n🌡️ Temperature Conversion Demonstrations")
    print("=" * 50)
    
    client = WeatherCalculationsMCPClient()
    
    try:
        await client.start()
        await client.initialize()
        
        # Temperature conversions
        conversions = [
            ("celsius_to_fahrenheit", {"celsius": 0}),
            ("celsius_to_fahrenheit", {"celsius": 25}),
            ("celsius_to_fahrenheit", {"celsius": -10}),
            ("fahrenheit_to_celsius", {"fahrenheit": 32}),
            ("fahrenheit_to_celsius", {"fahrenheit": 77}),
            ("fahrenheit_to_celsius", {"fahrenheit": 100}),
        ]
        
        for func_name, args in conversions:
            try:
                print(f"\n🔍 Computing {func_name}({args})...")
                result = await client.call_tool(func_name, args)
                content = extract_result_content(result)
                print(f"✅ Result:")
                print(content)
            except Exception as e:
                print(f"❌ Failed {func_name}({args}): {e}")
        
    except Exception as e:
        print(f"❌ Temperature conversion demonstration failed: {e}")
    finally:
        await client.stop()

async def demonstrate_weather_indices():
    """Demonstrate weather index calculations."""
    print("\n🌤️ Weather Index Calculations")
    print("=" * 50)
    
    client = WeatherCalculationsMCPClient()
    
    try:
        await client.start()
        await client.initialize()
        
        # Heat index calculations
        print("\n🔥 Heat Index Calculations:")
        heat_index_tests = [
            {"temperature_f": 85, "humidity": 70},
            {"temperature_f": 95, "humidity": 50},
            {"temperature_f": 100, "humidity": 80},
        ]
        
        for args in heat_index_tests:
            try:
                print(f"\n🔍 Computing heat_index({args})...")
                result = await client.call_tool("calculate_heat_index", args)
                content = extract_result_content(result)
                print(f"✅ Result:")
                print(content)
            except Exception as e:
                print(f"❌ Failed heat_index({args}): {e}")
        
        # Wind chill calculations
        print("\n❄️ Wind Chill Calculations:")
        wind_chill_tests = [
            {"temperature_f": 30, "wind_speed_mph": 15},
            {"temperature_f": 10, "wind_speed_mph": 25},
            {"temperature_f": -5, "wind_speed_mph": 30},
        ]
        
        for args in wind_chill_tests:
            try:
                print(f"\n🔍 Computing wind_chill({args})...")
                result = await client.call_tool("calculate_wind_chill", args)
                content = extract_result_content(result)
                print(f"✅ Result:")
                print(content)
            except Exception as e:
                print(f"❌ Failed wind_chill({args}): {e}")
        
        # Dew point calculations
        print("\n💧 Dew Point Calculations:")
        dew_point_tests = [
            {"temperature_c": 20, "humidity": 60},
            {"temperature_c": 30, "humidity": 85},
            {"temperature_c": 5, "humidity": 40},
        ]
        
        for args in dew_point_tests:
            try:
                print(f"\n🔍 Computing dew_point({args})...")
                result = await client.call_tool("calculate_dew_point", args)
                content = extract_result_content(result)
                print(f"✅ Result:")
                print(content)
            except Exception as e:
                print(f"❌ Failed dew_point({args}): {e}")
        
    except Exception as e:
        print(f"❌ Weather index demonstration failed: {e}")
    finally:
        await client.stop()

async def demonstrate_advanced_calculations():
    """Demonstrate advanced weather calculations."""
    print("\n🔬 Advanced Weather Calculations")
    print("=" * 50)
    
    client = WeatherCalculationsMCPClient()
    
    try:
        await client.start()
        await client.initialize()
        
        # Feels like temperature
        print("\n🌡️ Feels Like Temperature:")
        feels_like_tests = [
            {"temperature_c": 30, "humidity": 70, "wind_speed_kmh": 15},
            {"temperature_c": 5, "humidity": 60, "wind_speed_kmh": 25},
            {"temperature_c": 20, "humidity": 50, "wind_speed_kmh": 10},
        ]
        
        for args in feels_like_tests:
            try:
                print(f"\n🔍 Computing feels_like({args})...")
                result = await client.call_tool("calculate_feels_like", args)
                content = extract_result_content(result)
                print(f"✅ Result:")
                print(content)
            except Exception as e:
                print(f"❌ Failed feels_like({args}): {e}")
        
        # Sunrise/sunset calculations
        print("\n🌅 Sunrise/Sunset Calculations:")
        sun_tests = [
            {"latitude": 40.7128, "longitude": -74.0060, "day_of_year": 172},  # NYC, summer solstice
            {"latitude": 51.5074, "longitude": -0.1278, "day_of_year": 355},   # London, winter solstice
            {"latitude": -33.8688, "longitude": 151.2093, "day_of_year": 80},  # Sydney, spring equinox
        ]
        
        for args in sun_tests:
            try:
                print(f"\n🔍 Computing sunrise_sunset({args})...")
                result = await client.call_tool("sunrise_sunset_times", args)
                content = extract_result_content(result)
                print(f"✅ Result:")
                print(content)
            except Exception as e:
                print(f"❌ Failed sunrise_sunset({args}): {e}")
        
        # UV index calculations
        print("\n☀️ UV Index Calculations:")
        uv_tests = [
            {"solar_elevation_degrees": 90, "ozone_thickness": 300, "cloud_cover": 0},
            {"solar_elevation_degrees": 45, "ozone_thickness": 250, "cloud_cover": 50},
            {"solar_elevation_degrees": 15, "ozone_thickness": 350, "cloud_cover": 20},
        ]
        
        for args in uv_tests:
            try:
                print(f"\n🔍 Computing uv_index({args})...")
                result = await client.call_tool("uv_index_from_solar_elevation", args)
                content = extract_result_content(result)
                print(f"✅ Result:")
                print(content)
            except Exception as e:
                print(f"❌ Failed uv_index({args}): {e}")
        
        # Pressure calculations
        print("\n📊 Pressure Calculations:")
        pressure_tests = [
            {"pressure_hpa": 1000, "altitude_m": 500, "temperature_c": 15},
            {"pressure_hpa": 950, "altitude_m": 1500, "temperature_c": 5},
        ]
        
        for args in pressure_tests:
            try:
                print(f"\n🔍 Computing pressure_altitude_to_sea_level({args})...")
                result = await client.call_tool("pressure_altitude_to_sea_level", args)
                content = extract_result_content(result)
                print(f"✅ Result:")
                print(content)
            except Exception as e:
                print(f"❌ Failed pressure calculation({args}): {e}")
        
        # Saturation vapor pressure
        print("\n💨 Saturation Vapor Pressure:")
        vapor_tests = [
            {"temperature_c": 20},
            {"temperature_c": 0},
            {"temperature_c": -10},
        ]
        
        for args in vapor_tests:
            try:
                print(f"\n🔍 Computing saturation_vapor_pressure({args})...")
                result = await client.call_tool("saturation_vapor_pressure", args)
                content = extract_result_content(result)
                print(f"✅ Result:")
                print(content)
            except Exception as e:
                print(f"❌ Failed vapor pressure({args}): {e}")
        
    except Exception as e:
        print(f"❌ Advanced calculations demonstration failed: {e}")
    finally:
        await client.stop()

async def main():
    """Main demonstration function."""
    print("🧮 Weather Calculations MCP Server - Pure Functions Demo")
    print("=" * 70)
    
    # First test basic connectivity
    server_works = await test_basic_connectivity()
    
    if server_works:
        print("\n🎯 Running weather calculation demonstrations...")
        await demonstrate_temperature_conversions()
        await demonstrate_weather_indices()
        await demonstrate_advanced_calculations()
        print("\n✅ All weather calculation demonstrations completed successfully!")
    else:
        print("\n❌ Weather calculations server connectivity failed")
        print("\n💡 Troubleshooting steps:")
        print("   1. Make sure weather_calculations_server.py exists")
        print("   2. Try running the server manually:")
        print("      python weather_calculations_server.py")
        print("   3. Check for any error messages in the server output")
        print("   4. Ensure all dependencies are installed")

if __name__ == "__main__":
    asyncio.run(main())