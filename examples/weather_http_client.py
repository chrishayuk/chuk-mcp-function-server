#!/usr/bin/env python3
# examples/weather_http_client.py
"""
HTTP client example for the Weather MCP Server.

This demonstrates HTTP transport communication with the weather server,
including real-time endpoints and MCP protocol over HTTP.
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

class WeatherMCPHTTPClient:
    """Client for communicating with the Weather MCP Server via HTTP transport."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session_id = None
        self.message_id = 0
        self.session = None
        
        if not _http_available:
            raise RuntimeError("httpx required for HTTP client: pip install httpx")
        
        print(f"🌐 HTTP Weather Client connecting to: {base_url}")
    
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
                "name": "weather-http-client",
                "version": "1.0.0"
            }
        })
        
        if response.get("error") is not None:
            raise RuntimeError(f"Initialization failed: {response['error']}")
        
        print("✅ Initialized HTTP connection")
        return response["result"]
    
    async def list_tools(self) -> list:
        """List available weather tools."""
        response = await self.send_message("tools/list")
        if response.get("error") is not None:
            raise RuntimeError(f"Failed to list tools: {response['error']}")
        
        return response["result"]["tools"]
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Call a weather tool."""
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

async def start_weather_http_server(port: int = 8000) -> subprocess.Popen:
    """Start the weather HTTP server and wait for it to be ready."""
    # Find weather server path
    current_dir = Path(__file__).parent
    server_path = current_dir / "weather_server.py"
    
    if server_path.exists():
        server_cmd = ["python", str(server_path), "--transport", "http", "--port", str(port)]
    else:
        # Fallback
        server_cmd = ["python", "weather_server.py", "--transport", "http", "--port", str(port)]
    
    print(f"🚀 Starting weather HTTP server on port {port}...")
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
                    print(f"✅ Weather HTTP server ready at {base_url}")
                    return process
        except:
            pass
        
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            print(f"❌ Weather server failed to start:")
            print(f"  stdout: {stdout.decode()}")
            print(f"  stderr: {stderr.decode()}")
            raise RuntimeError("Weather server process terminated")
        
        await asyncio.sleep(1)
    
    process.terminate()
    raise RuntimeError(f"Weather server not ready after {max_attempts} seconds")

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

async def demonstrate_http_weather_info():
    """Demonstrate weather information via HTTP."""
    print("\n🌤️ HTTP Weather Information")
    print("=" * 50)
    
    client = WeatherMCPHTTPClient()
    
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
        
        # Get current weather for multiple cities
        print("\n🌡️ Current Weather (HTTP):")
        cities = ["London", "New York", "Tokyo"]
        
        for city in cities:
            try:
                print(f"\n🔍 Getting weather for {city}...")
                result = await client.call_tool("get_current_weather", {"location": city})
                content = extract_result_content(result)
                print(f"✅ Weather in {city}:")
                print(content)
            except Exception as e:
                print(f"❌ Failed to get weather for {city}: {e}")
        
        # Get weather comparison
        print("\n⚖️ Weather Comparison (HTTP):")
        try:
            result = await client.call_tool("compare_weather", {
                "location1": "London",
                "location2": "Tokyo"
            })
            content = extract_result_content(result)
            print("✅ London vs Tokyo:")
            print(content)
        except Exception as e:
            print(f"❌ Failed to compare weather: {e}")
        
    except Exception as e:
        print(f"❌ HTTP weather demonstration failed: {e}")
    finally:
        await client.stop()

async def demonstrate_http_weather_forecast():
    """Demonstrate weather forecasting via HTTP."""
    print("\n📅 HTTP Weather Forecasting")
    print("=" * 50)
    
    client = WeatherMCPHTTPClient()
    
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
        
        # Get forecasts for different cities and durations
        forecasts = [
            ("Paris", 3),
            ("Sydney", 5),
            ("Mumbai", 7)
        ]
        
        for city, days in forecasts:
            try:
                print(f"\n🔍 Getting {days}-day forecast for {city}...")
                result = await client.call_tool("get_forecast", {
                    "location": city,
                    "days": days
                })
                content = extract_result_content(result)
                print(f"✅ {days}-day forecast for {city}:")
                print(content)
            except Exception as e:
                print(f"❌ Failed to get forecast for {city}: {e}")
        
        # Get weather alerts
        print("\n🚨 Weather Alerts (HTTP):")
        cities = ["New York", "Berlin"]
        
        for city in cities:
            try:
                result = await client.call_tool("get_weather_alerts", {"location": city})
                content = extract_result_content(result)
                print(f"\n⚠️ Alerts for {city}:")
                print(content)
            except Exception as e:
                print(f"❌ Failed to get alerts for {city}: {e}")
        
    except Exception as e:
        print(f"❌ HTTP weather forecast demonstration failed: {e}")
    finally:
        await client.stop()

async def demonstrate_http_weather_utilities():
    """Demonstrate weather utility functions via HTTP."""
    print("\n🔧 HTTP Weather Utilities")
    print("=" * 50)
    
    client = WeatherMCPHTTPClient()
    
    try:
        await client.start()
        await client.initialize()
        
        # Temperature conversions
        print("\n🌡️ Temperature Conversions (HTTP):")
        conversions = [
            (20, "celsius", "fahrenheit"),
            (68, "fahrenheit", "celsius")
        ]
        
        for temp, from_unit, to_unit in conversions:
            try:
                result = await client.call_tool("convert_temperature", {
                    "temperature": temp,
                    "from_unit": from_unit,
                    "to_unit": to_unit
                })
                content = extract_result_content(result)
                print(f"\n🔍 Convert {temp}° {from_unit} to {to_unit}:")
                print(content)
            except Exception as e:
                print(f"❌ Failed temperature conversion: {e}")
        
        # Air quality information
        print("\n🌬️ Air Quality (HTTP):")
        cities = ["London", "Paris"]
        
        for city in cities:
            try:
                result = await client.call_tool("get_air_quality", {"location": city})
                content = extract_result_content(result)
                print(f"\n🔍 Air quality in {city}:")
                print(content)
            except Exception as e:
                print(f"❌ Failed to get air quality for {city}: {e}")
        
        # UV Index
        print("\n☀️ UV Index (HTTP):")
        try:
            result = await client.call_tool("get_uv_index", {"location": "Sydney"})
            content = extract_result_content(result)
            print("🔍 UV index in Sydney:")
            print(content)
        except Exception as e:
            print(f"❌ Failed to get UV index: {e}")
        
        # Climate statistics
        print("\n📊 Climate Statistics (HTTP):")
        try:
            result = await client.call_tool("get_climate_stats", {"location": "Barcelona"})
            content = extract_result_content(result)
            print("🔍 Climate stats for Barcelona:")
            print(content)
        except Exception as e:
            print(f"❌ Failed to get climate stats: {e}")
        
    except Exception as e:
        print(f"❌ HTTP weather utilities demonstration failed: {e}")
    finally:
        await client.stop()

async def test_weather_http_server_connectivity(port: int = 8000):
    """Test basic HTTP weather server connectivity."""
    print(f"\n🌐 Testing Weather HTTP Server Connectivity (port {port})")
    print("=" * 50)
    
    client = WeatherMCPHTTPClient(f"http://localhost:{port}")
    
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
        
        # Test simple weather call
        try:
            result = await client.call_tool("list_locations", {})
            print("✅ Simple weather operation successful")
            print("🌍 Location listing completed")
        except Exception as e:
            print(f"❌ Simple weather operation failed: {e}")
            return False
        
        print("✅ Weather HTTP server is fully functional!")
        return True
        
    except Exception as e:
        print(f"❌ HTTP connectivity test failed: {e}")
        return False
    finally:
        await client.stop()

async def main():
    """Main HTTP demonstration function."""
    print("🌤️ Weather MCP Server - HTTP Client Examples")
    print("=" * 60)
    
    if not _http_available:
        print("❌ HTTP client requires httpx: pip install httpx")
        return
    
    port = 8000
    server_process = None
    
    try:
        # Start HTTP server
        server_process = await start_weather_http_server(port)
        
        # Test connectivity
        server_works = await test_weather_http_server_connectivity(port)
        
        if server_works:
            print("\n🎯 Running full HTTP weather demonstrations...")
            await demonstrate_http_weather_info()
            await demonstrate_http_weather_forecast()
            await demonstrate_http_weather_utilities()
            print("\n✅ All HTTP weather demonstrations completed!")
        else:
            print("\n❌ Weather HTTP server connectivity failed")
            
    except Exception as e:
        print(f"❌ HTTP weather demonstration failed: {e}")
    finally:
        # Clean up server
        if server_process:
            print("\n🛑 Stopping weather HTTP server...")
            server_process.terminate()
            try:
                server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server_process.kill()
                server_process.wait()
            print("✅ Weather HTTP server stopped")

if __name__ == "__main__":
    asyncio.run(main())