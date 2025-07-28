# Chuk MCP Function Server

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP Protocol](https://img.shields.io/badge/MCP-Protocol-green.svg)](https://modelcontextprotocol.io/)

**A high-performance, configurable MCP (Model Context Protocol) server infrastructure for building domain-specific function servers with pure functions.**

Perfect for exposing mathematical calculations, data transformations, and stateless operations as MCP tools with both STDIO and HTTP transport support.

## 🚀 Features

### 🏗️ **Infrastructure**
- **Dual Transport**: STDIO and HTTP support out of the box
- **Configuration Management**: YAML, JSON, environment variables, and CLI args
- **Function Filtering**: Flexible allowlist/denylist system
- **Error Handling**: Robust error handling with timeouts and recovery
- **Performance**: Sub-millisecond latency for pure functions (2,700+ ops/sec)

### 🔧 **Developer Experience**
- **Pure Function Focus**: Optimized for stateless, deterministic functions
- **Easy Extension**: Simple base classes for domain-specific servers
- **Rich CLI**: Comprehensive command-line interface with help
- **Debugging Tools**: Built-in debug and testing utilities
- **Type Safety**: Full type hints and validation

### 📊 **Production Ready**
- **Health Monitoring**: Built-in health checks and metrics
- **Resource Management**: Memory and CPU monitoring
- **Concurrent Support**: Handle multiple simultaneous requests
- **CORS Support**: Ready for web applications
- **Logging**: Structured logging with configurable levels

## 📦 Installation

```bash
pip install chuk-mcp-function-server
```

### Optional Dependencies

```bash
# For HTTP transport
pip install chuk-mcp-function-server[http]

# For development tools
pip install chuk-mcp-function-server[dev]

# Install everything
pip install chuk-mcp-function-server[full]
```

## 🏃 Quick Start

### 1. Create Your Server

```python
#!/usr/bin/env python3
from chuk_mcp_function_server import BaseMCPServer, ServerConfig, main

class MyCalculatorServer(BaseMCPServer):
    def __init__(self, config: ServerConfig):
        config.server_name = "my-calculator-server"
        config.server_description = "Mathematical calculations MCP server"
        super().__init__(config)
    
    def _register_tools(self):
        """Register your pure functions as MCP tools."""
        self.register_tool(
            name="add",
            handler=self._add,
            schema={
                "type": "object",
                "properties": {
                    "a": {"type": "number", "description": "First number"},
                    "b": {"type": "number", "description": "Second number"}
                },
                "required": ["a", "b"]
            },
            description="Add two numbers"
        )
    
    async def _add(self, a: float, b: float) -> str:
        """Pure function: add two numbers."""
        result = a + b
        return f"Result: {a} + {b} = {result}"

if __name__ == "__main__":
    main(server_class=MyCalculatorServer)
```

### 2. Run Your Server

```bash
# STDIO mode (default)
python my_server.py

# HTTP mode
python my_server.py --transport http --port 8000

# With configuration file
python my_server.py --config server-config.yaml
```

### 3. Test Your Server

```python
# Create a simple client
import asyncio
import json

async def test_calculator():
    # Start your server process and send JSON-RPC messages
    # See examples/ directory for complete client implementations
    pass
```

## 📚 Examples

We provide a complete **Weather Calculations Server** example that demonstrates:

- ✅ **10 Pure Weather Functions**: Temperature conversions, heat index, wind chill, dew point, sunrise/sunset times, UV calculations, and more
- ✅ **Real Scientific Formulas**: NWS heat index, Magnus formula, Tetens formula, barometric corrections
- ✅ **Both Transports**: STDIO and HTTP clients with full demonstrations
- ✅ **Performance Benchmarks**: Achieving 2,700+ operations/second

### Run the Example

```bash
# Clone the repository to get examples
git clone https://github.com/your-org/chuk-mcp-function-server.git
cd chuk-mcp-function-server

# Test STDIO transport
uv run examples/weather_calculations_stdio_client.py

# Test HTTP transport  
uv run examples/weather_calculations_http_client.py

# Run performance benchmarks
uv run examples/weather_calculations_benchmark.py
```

## 🔧 Configuration

### Command Line Options

```bash
python my_server.py \
  --transport http \
  --port 8000 \
  --host 0.0.0.0 \
  --verbose \
  --functions add multiply \
  --timeout 30
```

### Configuration File (YAML)

```yaml
# server-config.yaml
transport: http
port: 8000
host: "0.0.0.0"
enable_tools: true
enable_resources: true
enable_prompts: false
log_level: "INFO"

# Function filtering
function_allowlist:
  - add
  - multiply
  - divide

# Performance settings
cache_strategy: smart
computation_timeout: 30.0
max_concurrent_calls: 10
```

### Environment Variables

```bash
export MCP_SERVER_TRANSPORT=http
export MCP_SERVER_PORT=8000
export MCP_SERVER_LOG_LEVEL=DEBUG
export MCP_SERVER_FUNCTION_allowlist=add,multiply
```

## 🏛️ Architecture

```
┌─────────────────────────────────────┐
│           Your Server               │
│  (extends BaseMCPServer)            │
├─────────────────────────────────────┤
│      Chuk MCP Function Server       │
│  ┌─────────────┬─────────────────┐  │
│  │   Config    │   Function      │  │
│  │ Management  │   Filtering     │  │
│  └─────────────┴─────────────────┘  │
│  ┌─────────────┬─────────────────┐  │
│  │    STDIO    │      HTTP       │  │
│  │  Transport  │   Transport     │  │
│  └─────────────┴─────────────────┘  │
├─────────────────────────────────────┤
│         MCP Protocol Layer          │
└─────────────────────────────────────┘
```

### Key Components

- **BaseMCPServer**: Your server extends this class
- **ServerConfig**: Comprehensive configuration management
- **FunctionFilter**: Control which functions are exposed
- **Transport Layer**: STDIO and HTTP support
- **CLI**: Command-line interface and argument parsing

## 🎯 Core Concepts

### Pure Functions

This framework is optimized for **pure functions** - functions that:
- ✅ **Deterministic**: Same inputs always produce same outputs
- ✅ **No Side Effects**: No database calls, file I/O, or network requests
- ✅ **Stateless**: Each function call is independent
- ✅ **Fast**: No I/O bottlenecks mean sub-millisecond performance

```python
# ✅ Perfect for this framework
async def celsius_to_fahrenheit(self, celsius: float) -> str:
    fahrenheit = (celsius * 9/5) + 32
    return json.dumps({"celsius": celsius, "fahrenheit": fahrenheit})

# ❌ Not ideal (has side effects)
async def get_weather_from_api(self, city: str) -> str:
    response = await httpx.get(f"http://api.weather.com/{city}")
    return response.text
```

### Tool Registration

Register your functions as MCP tools with JSON schemas:

```python
def _register_tools(self):
    tools = [
        {
            "name": "calculate_bmi",
            "handler": self._calculate_bmi,
            "description": "Calculate Body Mass Index",
            "schema": {
                "type": "object",
                "properties": {
                    "weight_kg": {"type": "number", "description": "Weight in kilograms"},
                    "height_m": {"type": "number", "description": "Height in meters"}
                },
                "required": ["weight_kg", "height_m"]
            }
        }
    ]
    
    for tool in tools:
        self.register_tool(**tool)
```

### Function Filtering

Control which functions are exposed:

```python
# Configuration
function_allowlist = ["add", "multiply"]  # Only these functions
function_denylist = ["dangerous_function"]  # Exclude these
domain_allowlist = ["math", "conversion"]  # Only these domains
category_allowlist = ["safe"]  # Only these categories
```

## 📊 Performance

Benchmark results from the weather calculations example:

```
🏆 BENCHMARK RESULTS
================================================================================
Test Name                 Transport  Ops/sec    Avg (ms)   P95 (ms)   Memory (MB)
--------------------------------------------------------------------------------
STDIO Single-Threaded     stdio      2702.7     0.4        0.8        40.6      
HTTP Single-Threaded      http       1499.5     0.7        0.8        50.3      
HTTP Concurrent (x5)      http       539.3      1.4        1.7        49.6      
HTTP Mixed Operations     http       1541.9     0.6        0.8        49.7      
```

**Perfect for high-performance applications requiring fast mathematical computations.**

## 🛠️ Development

### Project Structure

```
chuk-mcp-function-server/
├── src/chuk_mcp_function_server/
│   ├── __init__.py          # Main exports
│   ├── base_server.py       # BaseMCPServer class
│   ├── config.py            # Configuration management
│   ├── function_filter.py   # Function filtering system
│   ├── cli.py               # Command-line interface
│   └── _version.py          # Version management
├── examples/
│   ├── weather_calculations_server.py     # Complete example server
│   ├── weather_calculations_stdio_client.py   # STDIO client
│   ├── weather_calculations_http_client.py    # HTTP client
│   └── weather_calculations_benchmark.py      # Performance tests
├── tests/                   # Test suite
└── docs/                    # Documentation
```

### Running Tests

```bash
# Install development dependencies
pip install chuk-mcp-function-server[dev]

# Run tests
pytest

# Run with coverage
pytest --cov=chuk_mcp_function_server

# Run type checking
mypy src/

# Format code
black src/ examples/
isort src/ examples/
```

### Debug Tools

```bash
# Check setup and dependencies
python examples/debug_setup.py

# Test imports and file structure
python examples/test_import.py

# Check server functionality
python examples/weather_calculations_server.py --help
```

## 🌐 HTTP API

When running in HTTP mode, the server provides additional REST endpoints:

### Endpoints

- `GET /` - Server information
- `GET /health` - Health check  
- `POST /mcp` - MCP protocol endpoint

### Server Info Response

```json
{
  "server": "my-calculator-server",
  "version": "1.0.0",
  "description": "Mathematical calculations MCP server",
  "transport": "http"
}
```

### Health Check Response

```json
{
  "status": "healthy",
  "timestamp": 1706356800.123,
  "server": "my-calculator-server"
}
```

### MCP Protocol

Send JSON-RPC messages to `/mcp`:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "add",
    "arguments": {"a": 5, "b": 3}
  }
}
```

## 🔒 Security Considerations

- **Function Filtering**: Use allowlist/denylist to control exposed functions
- **Input Validation**: All tool schemas are validated
- **Timeout Protection**: Configurable computation timeouts prevent hanging
- **Resource Limits**: Memory and CPU monitoring with limits
- **CORS Configuration**: Configurable for web applications
- **No Arbitrary Code**: Only registered functions can be called

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Areas for Contribution

- 🧮 **More Examples**: Domain-specific server examples
- 🔧 **Tools**: Additional CLI utilities and debugging tools
- 📊 **Performance**: Optimization and benchmarking improvements
- 📚 **Documentation**: Tutorials and guides
- 🧪 **Testing**: Test coverage and integration tests

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **MCP Protocol**: Built on the Model Context Protocol specification
- **FastAPI**: HTTP transport powered by FastAPI
- **Pydantic**: Configuration and validation using Pydantic models
- **Weather Science**: Example uses real meteorological formulas from NOAA/NWS

## 📞 Support

- 📖 **Documentation**: [Full documentation](https://docs.chuk-mcp-function-server.com)
- 🐛 **Issues**: [GitHub Issues](https://github.com/your-org/chuk-mcp-function-server/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/your-org/chuk-mcp-function-server/discussions)
- 📧 **Email**: support@chuk-mcp-function-server.com

---

**Built with ❤️ for the MCP community**

*Making it easy to expose pure functions as high-performance MCP tools.*