#!/usr/bin/env python3
# examples/weather_calculations_http_client.py
"""
HTTP client for the Weather Calculations MCP Server.

This demonstrates pure weather calculation functions via HTTP transport.
"""

import asyncio
import json
import subprocess
import sys
import time
from typing import Dict, Any, Optional
from pathlib import Path

# HTTP client requirements
try:
    import httpx
    _http_available = True
except ImportError:
    _http_available = False
    print("❌ HTTP client requires httpx: pip install httpx")

class WeatherCalculationsHTTPClient:
    """Client for communicating with the Weather Calculations MCP Server via HTTP transport."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session_id = None
        self.message_id = 0
        self.session = None
        
        if not _http_available:
            raise RuntimeError("httpx required for HTTP client: pip install httpx")
        
        print(f"🌐 HTTP Weather Calculations Client connecting to: {base_url}")
    
    async def start(self):
        """Start the HTTP session."""
        self.session = httpx.AsyncClient(timeout=30.0)
        print("🚀 Started HTTP session")
    
    async def stop(self):
        """Stop the HTTP session."""
        if self.session:
            await self.session.aclose()
            print("🛑 Stopped HTTP session")
    
    def _next_id(self) -> int:
        """Get next message ID."""
        self.message_id += 1
        return self.message_id
    
    async def send_message(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send a message to the server and return the response."""
        if not self.session:
            raise RuntimeError("Session not started - call start() first")
        
        message = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": method
        }
        
        if params:
            message["params"] = params
        
        headers = {"Content-Type": "application/json"}
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        
        try:
            response = await self.session.post(
                f"{self.base_url}/mcp",
                json=message,
                headers=headers
            )
            
            # Check for session ID in response
            if "mcp-session-id" in response.headers:
                self.session_id = response.headers["mcp-session-id"]
            
            response_data = response.json()
            return response_data
                
        except httpx.RequestError as e:
            raise RuntimeError(f"HTTP request failed: {e}")
        except httpx.TimeoutException:
            raise RuntimeError("HTTP request timeout")
    
    async def initialize(self):
        """Initialize the connection."""
        response = await self.send_message("initialize", {
            "protocolVersion": "2025-03-26",
            "clientInfo": {
                "name": "weather-calculations-http-client",
                "version": "1.0.0"
            }
        })
        
        if response.get("error") is not None:
            raise RuntimeError(f"Initialization failed: {response['error']}")
        
        print("✅ Initialized HTTP connection")
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
    
    async def get_server_info(self) -> Dict[str, Any]:
        """Get server information from the root endpoint."""
        try:
            response = await self.session.get(f"{self.base_url}/")
            return response.json()
        except Exception as e:
            raise RuntimeError(f"Failed to get server info: {e}")
    
    async def get_health(self) -> Dict[str, Any]:
        """Get server health information."""
        try:
            response = await self.session.get(f"{self.base_url}/health")
            return response.json()
        except Exception as e:
            raise RuntimeError(f"Failed to get health info: {e}")

async def start_weather_calculations_http_server(port: int = 8000) -> subprocess.Popen:
    """Start the weather calculations HTTP server and wait for it to be ready."""
    # Find weather calculations server path
    current_dir = Path(__file__).parent
    server_path = current_dir / "weather_calculations_server.py"
    
    if server_path.exists():
        server_cmd = ["python", str(server_path), "--transport", "http", "--port", str(port)]
    else:
        # Fallback
        server_cmd = ["python", "weather_calculations_server.py", "--transport", "http", "--port", str(port)]
    
    print(f"🚀 Starting weather calculations HTTP server on port {port}...")
    print(f"📍 Command: {' '.join(server_cmd)}")
    
    # Start server process
    process = subprocess.Popen(
        server_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for server to be ready
    base_url = f"http://localhost:{port}"
    max_attempts = 30
    
    for attempt in range(max_attempts):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{base_url}/health", timeout=2.0)
                if response.status_code == 200:
                    print(f"✅ Weather calculations HTTP server ready at {base_url}")
                    return process
        except:
            pass
        
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            print(f"❌ Weather calculations server failed to start:")
            print(f"  stdout: {stdout.decode()}")
            print(f"  stderr: {stderr.decode()}")
            raise RuntimeError("Weather calculations server process terminated")
        
        await asyncio.sleep(1)
    
    process.terminate()
    raise RuntimeError(f"Weather calculations server not ready after {max_attempts} seconds")

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

async def demonstrate_http_temperature_conversions():
    """Demonstrate temperature conversions via HTTP."""
    print("\n🌡️ HTTP Temperature Conversions")
    print("=" * 50)
    
    client = WeatherCalculationsHTTPClient()
    
    try:
        await client.start()
        await client.initialize()
        
        # Test server info
        try:
            server_info = await client.get_server_info()
            print(f"🌐 Server: {server_info.get('server', 'unknown')} v{server_info.get('version', 'unknown')}")
            print(f"📍 Transport: {server_info.get('transport', 'unknown')}")
        except Exception as e:
            print(f"⚠️ Could not get server info: {e}")
        
        # List tools
        try:
            tools = await client.list_tools()
            print(f"📋 Available tools: {len(tools)} found")
            
            # Show sample tools
            for tool in tools[:5]:
                print(f"   • {tool['name']}: {tool.get('description', 'No description')[:60]}...")
            if len(tools) > 5:
                print(f"   ... and {len(tools) - 5} more tools")
        
        except Exception as e:
            print(f"❌ Failed to list tools: {e}")
            return
        
        # Temperature conversions via HTTP
        print("\n🌡️ Temperature Conversions (HTTP):")
        conversions = [
            ("celsius_to_fahrenheit", {"celsius": 0}),
            ("celsius_to_fahrenheit", {"celsius": 25}),
            ("fahrenheit_to_celsius", {"fahrenheit": 32}),
            ("fahrenheit_to_celsius", {"fahrenheit": 77}),
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
        print(f"❌ HTTP temperature conversion demonstration failed: {e}")
    finally:
        await client.stop()

async def demonstrate_http_weather_indices():
    """Demonstrate weather index calculations via HTTP."""
    print("\n🌤️ HTTP Weather Index Calculations")
    print("=" * 50)
    
    client = WeatherCalculationsHTTPClient()
    
    try:
        await client.start()
        await client.initialize()
        
        # Get health info
        try:
            health = await client.get_health()
            print(f"💓 Server health: {health.get('status', 'unknown')}")
            print(f"⏰ Timestamp: {health.get('timestamp', 'unknown')}")
        except Exception as e:
            print(f"⚠️ Could not get health info: {e}")
        
        # Heat index calculations via HTTP
        print("\n🔥 Heat Index Calculations (HTTP):")
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
        
        # Wind chill calculations via HTTP
        print("\n❄️ Wind Chill Calculations (HTTP):")
        wind_chill_tests = [
            {"temperature_f": 30, "wind_speed_mph": 15},
            {"temperature_f": 10, "wind_speed_mph": 25},
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
        
        # Dew point calculations via HTTP
        print("\n💧 Dew Point Calculations (HTTP):")
        dew_point_tests = [
            {"temperature_c": 20, "humidity": 60},
            {"temperature_c": 30, "humidity": 85},
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
        print(f"❌ HTTP weather index demonstration failed: {e}")
    finally:
        await client.stop()

async def demonstrate_http_advanced_calculations():
    """Demonstrate advanced weather calculations via HTTP."""
    print("\n🔬 HTTP Advanced Weather Calculations")
    print("=" * 50)
    
    client = WeatherCalculationsHTTPClient()
    
    try:
        await client.start()
        await client.initialize()
        
        # Feels like temperature via HTTP
        print("\n🌡️ Feels Like Temperature (HTTP):")
        feels_like_tests = [
            {"temperature_c": 30, "humidity": 70, "wind_speed_kmh": 15},
            {"temperature_c": 5, "humidity": 60, "wind_speed_kmh": 25},
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
        
        # Sunrise/sunset calculations via HTTP
        print("\n🌅 Sunrise/Sunset Calculations (HTTP):")
        sun_tests = [
            {"latitude": 40.7128, "longitude": -74.0060, "day_of_year": 172},  # NYC, summer solstice
            {"latitude": 51.5074, "longitude": -0.1278, "day_of_year": 355},   # London, winter solstice
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
        
        # UV index calculations via HTTP
        print("\n☀️ UV Index Calculations (HTTP):")
        uv_tests = [
            {"solar_elevation_degrees": 90, "ozone_thickness": 300, "cloud_cover": 0},
            {"solar_elevation_degrees": 45, "ozone_thickness": 250, "cloud_cover": 50},
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
        
        # Pressure calculations via HTTP
        print("\n📊 Pressure Calculations (HTTP):")
        pressure_tests = [
            {"pressure_hpa": 1000, "altitude_m": 500, "temperature_c": 15},
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
        
        # Saturation vapor pressure via HTTP
        print("\n💨 Saturation Vapor Pressure (HTTP):")
        vapor_tests = [
            {"temperature_c": 20},
            {"temperature_c": 0},
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
        print(f"❌ HTTP advanced calculations demonstration failed: {e}")
    finally:
        await client.stop()

async def test_weather_calculations_http_server_connectivity(port: int = 8000):
    """Test basic HTTP weather calculations server connectivity."""
    print(f"\n🌐 Testing Weather Calculations HTTP Server Connectivity (port {port})")
    print("=" * 70)
    
    client = WeatherCalculationsHTTPClient(f"http://localhost:{port}")
    
    try:
        await client.start()
        
        print("🔗 Testing server endpoints...")
        
        # Test root endpoint
        try:
            server_info = await client.get_server_info()
            print(f"✅ Root endpoint: {server_info.get('server', 'unknown')}")
        except Exception as e:
            print(f"❌ Root endpoint failed: {e}")
            return False
        
        # Test health endpoint
        try:
            health = await client.get_health()
            print(f"✅ Health endpoint: {health.get('status', 'unknown')}")
        except Exception as e:
            print(f"❌ Health endpoint failed: {e}")
        
        # Test MCP initialization
        try:
            init_result = await client.initialize()
            print("✅ MCP initialization successful")
            print(f"📋 Server: {init_result.get('serverInfo', {}).get('name', 'unknown')}")
        except Exception as e:
            print(f"❌ MCP initialization failed: {e}")
            return False
        
        # Test tool listing
        try:
            tools = await client.list_tools()
            print(f"✅ Tool listing: {len(tools)} tools available")
        except Exception as e:
            print(f"❌ Tool listing failed: {e}")
            return False
        
        # Test simple calculation
        try:
            result = await client.call_tool("celsius_to_fahrenheit", {"celsius": 25})
            print("✅ Simple calculation successful")
            print("🧮 celsius_to_fahrenheit(25) completed")
        except Exception as e:
            print(f"❌ Simple calculation failed: {e}")
            return False
        
        print("✅ Weather calculations HTTP server is fully functional!")
        return True
        
    except Exception as e:
        print(f"❌ HTTP connectivity test failed: {e}")
        return False
    finally:
        await client.stop()

async def main():
    """Main HTTP demonstration function."""
    print("🧮 Weather Calculations MCP Server - HTTP Client Examples")
    print("=" * 70)
    
    if not _http_available:
        print("❌ HTTP client requires httpx: pip install httpx")
        return
    
    port = 8000
    server_process = None
    
    try:
        # Start HTTP server
        server_process = await start_weather_calculations_http_server(port)
        
        # Test connectivity
        server_works = await test_weather_calculations_http_server_connectivity(port)
        
        if server_works:
            print("\n🎯 Running full HTTP weather calculations demonstrations...")
            await demonstrate_http_temperature_conversions()
            await demonstrate_http_weather_indices()
            await demonstrate_http_advanced_calculations()
            print("\n✅ All HTTP weather calculations demonstrations completed!")
        else:
            print("\n❌ Weather calculations HTTP server connectivity failed")
            
    except Exception as e:
        print(f"❌ HTTP weather calculations demonstration failed: {e}")
    finally:
        # Clean up server
        if server_process:
            print("\n🛑 Stopping weather calculations HTTP server...")
            server_process.terminate()
            try:
                server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server_process.kill()
                server_process.wait()
            print("✅ Weather calculations HTTP server stopped")

if __name__ == "__main__":
    asyncio.run(main())