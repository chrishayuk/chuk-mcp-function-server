#!/usr/bin/env python3
# examples/weather_calculations_benchmark.py
"""
Performance benchmark script for the Weather Calculations MCP Server.

This tests both STDIO and HTTP transports with various workloads to measure:
- Throughput (operations per second)
- Latency (response times)
- Scalability (concurrent operations)
- Memory usage
- Server startup/shutdown times
"""

import asyncio
import json
import subprocess
import sys
import time
import statistics
import psutil
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

# HTTP client requirements
try:
    import httpx
    _http_available = True
except ImportError:
    _http_available = False
    print("❌ HTTP benchmarks require httpx: pip install httpx")

@dataclass
class BenchmarkResult:
    """Results from a benchmark test."""
    test_name: str
    transport: str
    operations: int
    duration: float
    operations_per_second: float
    avg_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    memory_usage_mb: float
    cpu_usage_percent: float
    errors: int
    success_rate: float

class WeatherCalculationsBenchmark:
    """Performance benchmark for weather calculations server."""
    
    def __init__(self):
        self.server_process = None
        self.server_port = 8001  # Use different port to avoid conflicts
        self.base_url = f"http://localhost:{self.server_port}"
        
        # Find server script
        current_dir = Path(__file__).parent
        server_path = current_dir / "weather_calculations_server.py"
        
        if server_path.exists():
            self.server_command = ["python", str(server_path)]
        else:
            self.server_command = ["python", "weather_calculations_server.py"]
        
        print(f"🧮 Weather Calculations Benchmark")
        print(f"📍 Server command: {' '.join(self.server_command)}")
        print(f"🌐 HTTP endpoint: {self.base_url}")
    
    async def start_http_server(self) -> bool:
        """Start HTTP server for benchmarking."""
        try:
            cmd = self.server_command + ["--transport", "http", "--port", str(self.server_port)]
            self.server_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Wait for server to be ready
            for attempt in range(30):
                try:
                    async with httpx.AsyncClient() as client:
                        response = await client.get(f"{self.base_url}/health", timeout=2.0)
                        if response.status_code == 200:
                            print(f"✅ HTTP server ready")
                            return True
                except:
                    pass
                
                if self.server_process.poll() is not None:
                    stdout, stderr = self.server_process.communicate()
                    print(f"❌ Server failed: {stderr.decode()}")
                    return False
                
                await asyncio.sleep(1)
            
            print("❌ Server startup timeout")
            return False
            
        except Exception as e:
            print(f"❌ Failed to start HTTP server: {e}")
            return False
    
    async def stop_http_server(self):
        """Stop HTTP server."""
        if self.server_process:
            self.server_process.terminate()
            try:
                await asyncio.wait_for(
                    asyncio.create_task(asyncio.to_thread(self.server_process.wait)),
                    timeout=5.0
                )
            except asyncio.TimeoutError:
                self.server_process.kill()
                await asyncio.create_task(asyncio.to_thread(self.server_process.wait))
            print("🛑 HTTP server stopped")
    
    async def benchmark_stdio_single_threaded(self, operations: int = 100) -> BenchmarkResult:
        """Benchmark STDIO transport with single-threaded operations."""
        print(f"\n🔍 STDIO Single-Threaded Benchmark ({operations} operations)")
        
        # Start server
        server_process = await asyncio.create_subprocess_exec(
            *self.server_command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        await asyncio.sleep(2)  # Let server start
        
        if server_process.returncode is not None:
            raise RuntimeError("Server failed to start")
        
        # Initialize connection
        await self._send_message(server_process, "initialize", {
            "protocolVersion": "2025-03-26",
            "clientInfo": {"name": "benchmark", "version": "1.0.0"}
        })
        
        # Send initialized notification
        init_msg = {"jsonrpc": "2.0", "method": "notifications/initialized"}
        server_process.stdin.write((json.dumps(init_msg) + "\n").encode())
        await server_process.stdin.drain()
        
        # Benchmark operations
        start_time = time.time()
        latencies = []
        errors = 0
        
        # Monitor process
        process = psutil.Process(server_process.pid)
        
        for i in range(operations):
            op_start = time.time()
            
            try:
                await self._send_message(server_process, "tools/call", {
                    "name": "celsius_to_fahrenheit",
                    "arguments": {"celsius": 20 + (i % 50)}  # Vary input
                })
                latency = (time.time() - op_start) * 1000
                latencies.append(latency)
            except Exception as e:
                errors += 1
                print(f"❌ Operation {i} failed: {e}")
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Get final resource usage
        memory_mb = process.memory_info().rss / 1024 / 1024
        cpu_percent = process.cpu_percent()
        
        # Cleanup
        server_process.terminate()
        await server_process.wait()
        
        return BenchmarkResult(
            test_name="STDIO Single-Threaded",
            transport="stdio",
            operations=operations,
            duration=duration,
            operations_per_second=operations / duration,
            avg_latency_ms=statistics.mean(latencies) if latencies else 0,
            min_latency_ms=min(latencies) if latencies else 0,
            max_latency_ms=max(latencies) if latencies else 0,
            p95_latency_ms=statistics.quantiles(latencies, n=20)[18] if latencies else 0,
            p99_latency_ms=statistics.quantiles(latencies, n=100)[98] if latencies else 0,
            memory_usage_mb=memory_mb,
            cpu_usage_percent=cpu_percent,
            errors=errors,
            success_rate=(operations - errors) / operations * 100
        )
    
    async def benchmark_http_single_threaded(self, operations: int = 100) -> BenchmarkResult:
        """Benchmark HTTP transport with single-threaded operations."""
        print(f"\n🌐 HTTP Single-Threaded Benchmark ({operations} operations)")
        
        if not await self.start_http_server():
            raise RuntimeError("Failed to start HTTP server")
        
        try:
            async with httpx.AsyncClient() as client:
                # Initialize connection
                await client.post(f"{self.base_url}/mcp", json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-03-26",
                        "clientInfo": {"name": "benchmark", "version": "1.0.0"}
                    }
                })
                
                # Benchmark operations
                start_time = time.time()
                latencies = []
                errors = 0
                
                # Monitor process
                process = psutil.Process(self.server_process.pid)
                
                for i in range(operations):
                    op_start = time.time()
                    
                    try:
                        response = await client.post(f"{self.base_url}/mcp", json={
                            "jsonrpc": "2.0",
                            "id": i + 2,
                            "method": "tools/call",
                            "params": {
                                "name": "celsius_to_fahrenheit",
                                "arguments": {"celsius": 20 + (i % 50)}
                            }
                        })
                        
                        if response.status_code == 200:
                            latency = (time.time() - op_start) * 1000
                            latencies.append(latency)
                        else:
                            errors += 1
                    except Exception as e:
                        errors += 1
                        print(f"❌ Operation {i} failed: {e}")
                
                end_time = time.time()
                duration = end_time - start_time
                
                # Get final resource usage
                memory_mb = process.memory_info().rss / 1024 / 1024
                cpu_percent = process.cpu_percent()
                
                return BenchmarkResult(
                    test_name="HTTP Single-Threaded",
                    transport="http",
                    operations=operations,
                    duration=duration,
                    operations_per_second=operations / duration,
                    avg_latency_ms=statistics.mean(latencies) if latencies else 0,
                    min_latency_ms=min(latencies) if latencies else 0,
                    max_latency_ms=max(latencies) if latencies else 0,
                    p95_latency_ms=statistics.quantiles(latencies, n=20)[18] if latencies else 0,
                    p99_latency_ms=statistics.quantiles(latencies, n=100)[98] if latencies else 0,
                    memory_usage_mb=memory_mb,
                    cpu_usage_percent=cpu_percent,
                    errors=errors,
                    success_rate=(operations - errors) / operations * 100
                )
        
        finally:
            await self.stop_http_server()
    
    async def benchmark_http_concurrent(self, total_operations: int = 100, concurrency: int = 10) -> BenchmarkResult:
        """Benchmark HTTP transport with concurrent operations."""
        print(f"\n⚡ HTTP Concurrent Benchmark ({total_operations} ops, {concurrency} concurrent)")
        
        if not await self.start_http_server():
            raise RuntimeError("Failed to start HTTP server")
        
        try:
            # Track all latencies and errors
            all_latencies = []
            total_errors = 0
            
            async def worker(worker_id: int, operations_per_worker: int):
                nonlocal all_latencies, total_errors
                worker_latencies = []
                worker_errors = 0
                
                async with httpx.AsyncClient() as client:
                    # Initialize connection
                    await client.post(f"{self.base_url}/mcp", json={
                        "jsonrpc": "2.0",
                        "id": worker_id * 1000,
                        "method": "initialize",
                        "params": {
                            "protocolVersion": "2025-03-26",
                            "clientInfo": {"name": f"benchmark-{worker_id}", "version": "1.0.0"}
                        }
                    })
                    
                    for i in range(operations_per_worker):
                        op_start = time.time()
                        
                        try:
                            response = await client.post(f"{self.base_url}/mcp", json={
                                "jsonrpc": "2.0",
                                "id": worker_id * 1000 + i + 1,
                                "method": "tools/call",
                                "params": {
                                    "name": "calculate_heat_index",  # More complex operation
                                    "arguments": {
                                        "temperature_f": 80 + (i % 20),
                                        "humidity": 50 + (i % 40)
                                    }
                                }
                            })
                            
                            if response.status_code == 200:
                                latency = (time.time() - op_start) * 1000
                                worker_latencies.append(latency)
                            else:
                                worker_errors += 1
                        except Exception:
                            worker_errors += 1
                
                # Thread-safe updates
                all_latencies.extend(worker_latencies)
                total_errors += worker_errors
            
            # Monitor process
            process = psutil.Process(self.server_process.pid)
            
            # Run concurrent workers
            operations_per_worker = total_operations // concurrency
            start_time = time.time()
            
            tasks = [
                worker(i, operations_per_worker)
                for i in range(concurrency)
            ]
            
            await asyncio.gather(*tasks)
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Get final resource usage
            memory_mb = process.memory_info().rss / 1024 / 1024
            cpu_percent = process.cpu_percent()
            
            actual_operations = len(all_latencies) + total_errors
            
            return BenchmarkResult(
                test_name=f"HTTP Concurrent (x{concurrency})",
                transport="http",
                operations=actual_operations,
                duration=duration,
                operations_per_second=actual_operations / duration,
                avg_latency_ms=statistics.mean(all_latencies) if all_latencies else 0,
                min_latency_ms=min(all_latencies) if all_latencies else 0,
                max_latency_ms=max(all_latencies) if all_latencies else 0,
                p95_latency_ms=statistics.quantiles(all_latencies, n=20)[18] if all_latencies else 0,
                p99_latency_ms=statistics.quantiles(all_latencies, n=100)[98] if all_latencies else 0,
                memory_usage_mb=memory_mb,
                cpu_usage_percent=cpu_percent,
                errors=total_errors,
                success_rate=(actual_operations - total_errors) / actual_operations * 100 if actual_operations > 0 else 0
            )
        
        finally:
            await self.stop_http_server()
    
    async def benchmark_mixed_operations(self, operations: int = 100) -> BenchmarkResult:
        """Benchmark HTTP transport with mixed operation types."""
        print(f"\n🎯 HTTP Mixed Operations Benchmark ({operations} operations)")
        
        if not await self.start_http_server():
            raise RuntimeError("Failed to start HTTP server")
        
        # Define different operation types with varying complexity
        operation_types = [
            ("celsius_to_fahrenheit", {"celsius": 25}),  # Simple
            ("calculate_heat_index", {"temperature_f": 85, "humidity": 70}),  # Medium
            ("calculate_dew_point", {"temperature_c": 20, "humidity": 60}),  # Medium
            ("sunrise_sunset_times", {"latitude": 40.7, "longitude": -74.0, "day_of_year": 172}),  # Complex
            ("uv_index_from_solar_elevation", {"solar_elevation_degrees": 45, "ozone_thickness": 300, "cloud_cover": 20}),  # Complex
        ]
        
        try:
            async with httpx.AsyncClient() as client:
                # Initialize connection
                await client.post(f"{self.base_url}/mcp", json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-03-26",
                        "clientInfo": {"name": "mixed-benchmark", "version": "1.0.0"}
                    }
                })
                
                # Benchmark operations
                start_time = time.time()
                latencies = []
                errors = 0
                
                # Monitor process
                process = psutil.Process(self.server_process.pid)
                
                for i in range(operations):
                    op_start = time.time()
                    
                    # Select operation type cyclically
                    op_name, op_args = operation_types[i % len(operation_types)]
                    
                    try:
                        response = await client.post(f"{self.base_url}/mcp", json={
                            "jsonrpc": "2.0",
                            "id": i + 2,
                            "method": "tools/call",
                            "params": {
                                "name": op_name,
                                "arguments": op_args
                            }
                        })
                        
                        if response.status_code == 200:
                            latency = (time.time() - op_start) * 1000
                            latencies.append(latency)
                        else:
                            errors += 1
                    except Exception:
                        errors += 1
                
                end_time = time.time()
                duration = end_time - start_time
                
                # Get final resource usage
                memory_mb = process.memory_info().rss / 1024 / 1024
                cpu_percent = process.cpu_percent()
                
                return BenchmarkResult(
                    test_name="HTTP Mixed Operations",
                    transport="http",
                    operations=operations,
                    duration=duration,
                    operations_per_second=operations / duration,
                    avg_latency_ms=statistics.mean(latencies) if latencies else 0,
                    min_latency_ms=min(latencies) if latencies else 0,
                    max_latency_ms=max(latencies) if latencies else 0,
                    p95_latency_ms=statistics.quantiles(latencies, n=20)[18] if latencies else 0,
                    p99_latency_ms=statistics.quantiles(latencies, n=100)[98] if latencies else 0,
                    memory_usage_mb=memory_mb,
                    cpu_usage_percent=cpu_percent,
                    errors=errors,
                    success_rate=(operations - errors) / operations * 100
                )
        
        finally:
            await self.stop_http_server()
    
    async def _send_message(self, process, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send message to STDIO server and get response."""
        message = {
            "jsonrpc": "2.0",
            "id": int(time.time() * 1000000),  # Unique ID
            "method": method
        }
        
        if params:
            message["params"] = params
        
        # Send message
        message_json = json.dumps(message) + "\n"
        process.stdin.write(message_json.encode())
        await process.stdin.drain()
        
        # Read response
        response_line = await asyncio.wait_for(process.stdout.readline(), timeout=10.0)
        if not response_line:
            raise RuntimeError("No response from server")
        
        return json.loads(response_line.decode().strip())
    
    def print_results(self, results: List[BenchmarkResult]):
        """Print formatted benchmark results."""
        print(f"\n🏆 BENCHMARK RESULTS")
        print("=" * 80)
        
        # Summary table
        print(f"{'Test Name':<25} {'Transport':<10} {'Ops/sec':<10} {'Avg (ms)':<10} {'P95 (ms)':<10} {'Memory (MB)':<12} {'Success %':<10}")
        print("-" * 80)
        
        for result in results:
            print(f"{result.test_name:<25} {result.transport:<10} {result.operations_per_second:<10.1f} "
                  f"{result.avg_latency_ms:<10.1f} {result.p95_latency_ms:<10.1f} "
                  f"{result.memory_usage_mb:<12.1f} {result.success_rate:<10.1f}")
        
        print("\n📊 DETAILED METRICS")
        print("=" * 80)
        
        for result in results:
            print(f"\n🔍 {result.test_name} ({result.transport.upper()})")
            print(f"   Operations: {result.operations:,}")
            print(f"   Duration: {result.duration:.2f}s")
            print(f"   Throughput: {result.operations_per_second:.1f} ops/sec")
            print(f"   Latency (avg): {result.avg_latency_ms:.1f}ms")
            print(f"   Latency (min/max): {result.min_latency_ms:.1f}ms / {result.max_latency_ms:.1f}ms")
            print(f"   Latency (P95/P99): {result.p95_latency_ms:.1f}ms / {result.p99_latency_ms:.1f}ms")
            print(f"   Memory usage: {result.memory_usage_mb:.1f} MB")
            print(f"   CPU usage: {result.cpu_usage_percent:.1f}%")
            print(f"   Errors: {result.errors}")
            print(f"   Success rate: {result.success_rate:.1f}%")
        
        # Performance comparison
        if len(results) > 1:
            print(f"\n⚡ PERFORMANCE COMPARISON")
            print("=" * 50)
            
            # Find fastest throughput
            fastest = max(results, key=lambda r: r.operations_per_second)
            print(f"🥇 Fastest throughput: {fastest.test_name} ({fastest.operations_per_second:.1f} ops/sec)")
            
            # Find lowest latency
            lowest_latency = min(results, key=lambda r: r.avg_latency_ms)
            print(f"🚀 Lowest latency: {lowest_latency.test_name} ({lowest_latency.avg_latency_ms:.1f}ms avg)")
            
            # Find most memory efficient
            lowest_memory = min(results, key=lambda r: r.memory_usage_mb)
            print(f"💾 Lowest memory: {lowest_memory.test_name} ({lowest_memory.memory_usage_mb:.1f} MB)")
            
            # Transport comparison
            stdio_results = [r for r in results if r.transport == "stdio"]
            http_results = [r for r in results if r.transport == "http"]
            
            if stdio_results and http_results:
                stdio_avg = statistics.mean([r.operations_per_second for r in stdio_results])
                http_avg = statistics.mean([r.operations_per_second for r in http_results])
                
                print(f"\n🔄 Transport Comparison:")
                print(f"   STDIO average: {stdio_avg:.1f} ops/sec")
                print(f"   HTTP average: {http_avg:.1f} ops/sec")
                
                if stdio_avg > http_avg:
                    ratio = stdio_avg / http_avg
                    print(f"   STDIO is {ratio:.1f}x faster than HTTP")
                else:
                    ratio = http_avg / stdio_avg
                    print(f"   HTTP is {ratio:.1f}x faster than STDIO")

async def main():
    """Main benchmark runner."""
    print("🏁 Weather Calculations MCP Server - Performance Benchmark")
    print("=" * 70)
    
    if not _http_available:
        print("⚠️ HTTP benchmarks disabled (httpx not available)")
    
    benchmark = WeatherCalculationsBenchmark()
    results = []
    
    try:
        # Quick benchmarks for development
        print("🚀 Running performance benchmarks...")
        
        # STDIO single-threaded
        result = await benchmark.benchmark_stdio_single_threaded(50)
        results.append(result)
        
        if _http_available:
            # HTTP single-threaded
            result = await benchmark.benchmark_http_single_threaded(50)
            results.append(result)
            
            # HTTP concurrent
            result = await benchmark.benchmark_http_concurrent(50, 5)
            results.append(result)
            
            # HTTP mixed operations
            result = await benchmark.benchmark_mixed_operations(50)
            results.append(result)
        
        # Print all results
        benchmark.print_results(results)
        
        print(f"\n✅ Benchmark completed! ({len(results)} tests)")
        
    except Exception as e:
        print(f"❌ Benchmark failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        if benchmark.server_process:
            await benchmark.stop_http_server()

if __name__ == "__main__":
    asyncio.run(main())