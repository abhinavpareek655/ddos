#!/usr/bin/env python3
"""
Advanced HTTP Stress Testing Tool
Like Apache Bench but with more features and better data collection

Usage:
    python3 stress_test.py http://localhost:5000/matmul -n 10000 -c 100
    python3 stress_test.py http://localhost:5000/matmul -n 10000 -c 100 --cooldown 1 --batch-size 1000

Requirements:
    pip3 install requests aiohttp
"""

import asyncio
import aiohttp
import time
import argparse
import sys
import statistics
import json
from datetime import datetime
from collections import defaultdict
import signal
from dataclasses import dataclass, asdict
from typing import List, Dict
import csv

@dataclass
class RequestResult:
    """Single request result"""
    success: bool
    status_code: int
    response_time: float
    timestamp: float
    error: str = ""
    response_size: int = 0

@dataclass
class TestStats:
    """Aggregated test statistics"""
    total_requests: int
    successful_requests: int
    failed_requests: int
    total_time: float
    requests_per_second: float
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    median_response_time: float
    p95_response_time: float
    p99_response_time: float
    total_data_transferred: int
    status_codes: Dict[int, int]
    errors: Dict[str, int]

class StressTester:
    def __init__(self, url: str, total_requests: int, concurrency: int,
                 timeout: int = 30, method: str = "GET", headers: dict = None,
                 body: str = None, cooldown: float = 0, batch_size: int = None,
                 keep_alive: bool = True, verify_ssl: bool = True):
        self.url = url
        self.total_requests = total_requests
        self.concurrency = concurrency
        self.timeout = timeout
        self.method = method.upper()
        self.headers = headers or {}
        self.body = body
        self.cooldown = cooldown
        self.batch_size = batch_size or total_requests
        self.keep_alive = keep_alive
        self.verify_ssl = verify_ssl
        
        self.results: List[RequestResult] = []
        self.start_time = 0
        self.end_time = 0
        self.running = True
        
        # Setup signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
    
    def signal_handler(self, sig, frame):
        """Handle Ctrl+C gracefully"""
        print("\n\n[!] Interrupted! Generating report with collected data...\n")
        self.running = False
    
    async def make_request(self, session: aiohttp.ClientSession, request_id: int) -> RequestResult:
        """Make a single HTTP request"""
        start = time.time()
        
        try:
            kwargs = {
                'timeout': aiohttp.ClientTimeout(total=self.timeout),
                'headers': self.headers,
                'ssl': self.verify_ssl
            }
            
            if self.body:
                kwargs['data'] = self.body
            
            async with session.request(self.method, self.url, **kwargs) as response:
                # Read response to measure transfer time
                content = await response.read()
                response_time = time.time() - start
                
                return RequestResult(
                    success=True,
                    status_code=response.status,
                    response_time=response_time,
                    timestamp=start,
                    response_size=len(content)
                )
        
        except asyncio.TimeoutError:
            return RequestResult(
                success=False,
                status_code=0,
                response_time=time.time() - start,
                timestamp=start,
                error="Timeout"
            )
        except aiohttp.ClientError as e:
            return RequestResult(
                success=False,
                status_code=0,
                response_time=time.time() - start,
                timestamp=start,
                error=f"ClientError: {str(e)}"
            )
        except Exception as e:
            return RequestResult(
                success=False,
                status_code=0,
                response_time=time.time() - start,
                timestamp=start,
                error=f"Exception: {str(e)}"
            )
    
    async def worker(self, session: aiohttp.ClientSession, queue: asyncio.Queue, 
                    worker_id: int, progress_callback):
        """Worker coroutine that processes requests from queue"""
        while self.running:
            try:
                request_id = await asyncio.wait_for(queue.get(), timeout=0.1)
                
                result = await self.make_request(session, request_id)
                self.results.append(result)
                
                # Progress update
                if progress_callback:
                    progress_callback(len(self.results))
                
                queue.task_done()
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"[Worker {worker_id}] Error: {e}")
                break
    
    async def run_batch(self, start_idx: int, end_idx: int, progress_callback):
        """Run a batch of requests"""
        batch_size = end_idx - start_idx
        
        # Configure connection pooling
        connector = aiohttp.TCPConnector(
            limit=self.concurrency * 2,  # Max connections
            limit_per_host=self.concurrency * 2,
            ttl_dns_cache=300,
            force_close=not self.keep_alive
        )
        
        # Create session with keep-alive
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        async with aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers=self.headers
        ) as session:
            
            # Create queue and add requests
            queue = asyncio.Queue()
            for i in range(start_idx, end_idx):
                await queue.put(i)
            
            # Create workers
            workers = [
                asyncio.create_task(
                    self.worker(session, queue, i, progress_callback)
                )
                for i in range(self.concurrency)
            ]
            
            # Wait for queue to be processed
            await queue.join()
            
            # Cancel workers
            for w in workers:
                w.cancel()
            
            await asyncio.gather(*workers, return_exceptions=True)
    
    def print_progress(self, completed: int):
        """Print progress bar"""
        progress = (completed / self.total_requests) * 100
        bar_length = 50
        filled = int(bar_length * completed / self.total_requests)
        bar = '█' * filled + '░' * (bar_length - filled)
        
        # Calculate current RPS
        elapsed = time.time() - self.start_time
        current_rps = completed / elapsed if elapsed > 0 else 0
        
        sys.stdout.write(f'\r[{bar}] {progress:.1f}% | {completed}/{self.total_requests} | {current_rps:.0f} RPS')
        sys.stdout.flush()
    
    async def run(self):
        """Run the stress test"""
        print("=" * 70)
        print("STRESS TEST CONFIGURATION")
        print("=" * 70)
        print(f"Target URL:          {self.url}")
        print(f"Total Requests:      {self.total_requests:,}")
        print(f"Concurrency:         {self.concurrency}")
        print(f"Method:              {self.method}")
        print(f"Timeout:             {self.timeout}s")
        print(f"Keep-Alive:          {self.keep_alive}")
        print(f"Batch Size:          {self.batch_size:,}")
        if self.cooldown > 0:
            print(f"Cooldown:            {self.cooldown}s between batches")
        print("=" * 70)
        print()
        
        self.start_time = time.time()
        
        # Process in batches if specified
        num_batches = (self.total_requests + self.batch_size - 1) // self.batch_size
        
        for batch_num in range(num_batches):
            if not self.running:
                break
            
            start_idx = batch_num * self.batch_size
            end_idx = min((batch_num + 1) * self.batch_size, self.total_requests)
            
            if num_batches > 1:
                print(f"\n[Batch {batch_num + 1}/{num_batches}] Requests {start_idx}-{end_idx}")
            
            await self.run_batch(start_idx, end_idx, self.print_progress)
            
            # Cooldown between batches
            if self.cooldown > 0 and batch_num < num_batches - 1 and self.running:
                print(f"\n[Cooldown] Waiting {self.cooldown}s before next batch...")
                await asyncio.sleep(self.cooldown)
        
        self.end_time = time.time()
        print("\n")
    
    def calculate_stats(self) -> TestStats:
        """Calculate statistics from results"""
        if not self.results:
            return None
        
        successful = [r for r in self.results if r.success]
        failed = [r for r in self.results if not r.success]
        
        response_times = [r.response_time * 1000 for r in self.results]  # Convert to ms
        response_times.sort()
        
        # Status code distribution
        status_codes = defaultdict(int)
        for r in self.results:
            status_codes[r.status_code] += 1
        
        # Error distribution
        errors = defaultdict(int)
        for r in failed:
            errors[r.error] += 1
        
        # Calculate percentiles
        def percentile(data, p):
            if not data:
                return 0
            k = (len(data) - 1) * p
            f = int(k)
            c = f + 1
            if c >= len(data):
                return data[-1]
            return data[f] + (k - f) * (data[c] - data[f])
        
        total_time = self.end_time - self.start_time
        
        return TestStats(
            total_requests=len(self.results),
            successful_requests=len(successful),
            failed_requests=len(failed),
            total_time=total_time,
            requests_per_second=len(self.results) / total_time if total_time > 0 else 0,
            avg_response_time=statistics.mean(response_times) if response_times else 0,
            min_response_time=min(response_times) if response_times else 0,
            max_response_time=max(response_times) if response_times else 0,
            median_response_time=statistics.median(response_times) if response_times else 0,
            p95_response_time=percentile(response_times, 0.95),
            p99_response_time=percentile(response_times, 0.99),
            total_data_transferred=sum(r.response_size for r in successful),
            status_codes=dict(status_codes),
            errors=dict(errors)
        )
    
    def print_report(self, stats: TestStats):
        """Print detailed test report"""
        print("=" * 70)
        print("TEST RESULTS")
        print("=" * 70)
        print()
        
        print("📊 SUMMARY")
        print("-" * 70)
        print(f"Total Requests:        {stats.total_requests:,}")
        print(f"Successful:            {stats.successful_requests:,} ({stats.successful_requests/stats.total_requests*100:.1f}%)")
        print(f"Failed:                {stats.failed_requests:,} ({stats.failed_requests/stats.total_requests*100:.1f}%)")
        print(f"Total Time:            {stats.total_time:.2f}s")
        print(f"Requests per Second:   {stats.requests_per_second:.2f}")
        print(f"Data Transferred:      {self.format_bytes(stats.total_data_transferred)}")
        print()
        
        print("⏱️  RESPONSE TIMES (milliseconds)")
        print("-" * 70)
        print(f"Average:               {stats.avg_response_time:.2f} ms")
        print(f"Median:                {stats.median_response_time:.2f} ms")
        print(f"Min:                   {stats.min_response_time:.2f} ms")
        print(f"Max:                   {stats.max_response_time:.2f} ms")
        print(f"95th Percentile:       {stats.p95_response_time:.2f} ms")
        print(f"99th Percentile:       {stats.p99_response_time:.2f} ms")
        print()
        
        print("📡 STATUS CODES")
        print("-" * 70)
        for code, count in sorted(stats.status_codes.items()):
            percentage = (count / stats.total_requests) * 100
            code_desc = self.get_status_description(code)
            print(f"{code} {code_desc:20s} {count:,} ({percentage:.1f}%)")
        print()
        
        if stats.errors:
            print("❌ ERRORS")
            print("-" * 70)
            for error, count in sorted(stats.errors.items(), key=lambda x: x[1], reverse=True):
                percentage = (count / stats.failed_requests) * 100 if stats.failed_requests > 0 else 0
                print(f"{error:40s} {count:,} ({percentage:.1f}%)")
            print()
        
        print("=" * 70)
    
    def get_status_description(self, code: int) -> str:
        """Get HTTP status code description"""
        descriptions = {
            0: "Connection Failed",
            200: "OK",
            201: "Created",
            204: "No Content",
            301: "Moved Permanently",
            302: "Found",
            304: "Not Modified",
            400: "Bad Request",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            500: "Internal Server Error",
            502: "Bad Gateway",
            503: "Service Unavailable",
            504: "Gateway Timeout"
        }
        return descriptions.get(code, "")
    
    def format_bytes(self, bytes_val: int) -> str:
        """Format bytes to human readable"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_val < 1024.0:
                return f"{bytes_val:.2f} {unit}"
            bytes_val /= 1024.0
        return f"{bytes_val:.2f} TB"
    
    def save_results_csv(self, filename: str):
        """Save detailed results to CSV"""
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Request_ID', 'Success', 'Status_Code', 'Response_Time_ms', 
                           'Timestamp', 'Response_Size_bytes', 'Error'])
            
            for i, r in enumerate(self.results):
                writer.writerow([
                    i + 1,
                    r.success,
                    r.status_code,
                    round(r.response_time * 1000, 2),
                    r.timestamp,
                    r.response_size,
                    r.error
                ])
        
        print(f"[+] Detailed results saved to: {filename}")
    
    def save_summary_json(self, stats: TestStats, filename: str):
        """Save summary statistics to JSON"""
        data = {
            'test_config': {
                'url': self.url,
                'total_requests': self.total_requests,
                'concurrency': self.concurrency,
                'method': self.method,
                'timeout': self.timeout,
                'cooldown': self.cooldown,
                'batch_size': self.batch_size
            },
            'stats': asdict(stats),
            'timestamp': datetime.now().isoformat()
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"[+] Summary statistics saved to: {filename}")
    
    def generate_latency_distribution(self) -> Dict[str, int]:
        """Generate latency distribution histogram"""
        buckets = {
            '<10ms': 0,
            '10-50ms': 0,
            '50-100ms': 0,
            '100-200ms': 0,
            '200-500ms': 0,
            '500ms-1s': 0,
            '1-2s': 0,
            '2-5s': 0,
            '>5s': 0
        }
        
        for r in self.results:
            ms = r.response_time * 1000
            if ms < 10:
                buckets['<10ms'] += 1
            elif ms < 50:
                buckets['10-50ms'] += 1
            elif ms < 100:
                buckets['50-100ms'] += 1
            elif ms < 200:
                buckets['100-200ms'] += 1
            elif ms < 500:
                buckets['200-500ms'] += 1
            elif ms < 1000:
                buckets['500ms-1s'] += 1
            elif ms < 2000:
                buckets['1-2s'] += 1
            elif ms < 5000:
                buckets['2-5s'] += 1
            else:
                buckets['>5s'] += 1
        
        return buckets
    
    def print_latency_distribution(self):
        """Print latency distribution histogram"""
        buckets = self.generate_latency_distribution()
        total = sum(buckets.values())
        
        print("📈 LATENCY DISTRIBUTION")
        print("-" * 70)
        
        max_bar_width = 50
        max_count = max(buckets.values()) if buckets.values() else 1
        
        for range_name, count in buckets.items():
            percentage = (count / total * 100) if total > 0 else 0
            bar_width = int((count / max_count) * max_bar_width)
            bar = '█' * bar_width
            
            print(f"{range_name:12s} {bar:50s} {count:6,} ({percentage:5.1f}%)")
        print()

async def main():
    parser = argparse.ArgumentParser(
        description='Advanced HTTP Stress Testing Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic test: 10,000 requests with 100 concurrent connections
  python3 stress_test.py http://localhost:5000/matmul -n 10000 -c 100
  
  # With cooldown: 1 second pause every 1000 requests
  python3 stress_test.py http://localhost:5000/matmul -n 10000 -c 100 --cooldown 1 --batch-size 1000
  
  # POST request with JSON body
  python3 stress_test.py http://localhost:5000/api -n 1000 -c 50 -X POST --body '{"key":"value"}'
  
  # Save results to files
  python3 stress_test.py http://localhost:5000/matmul -n 5000 -c 100 --csv results.csv --json summary.json
  
  # High concurrency test
  python3 stress_test.py http://localhost:5000/matmul -n 100000 -c 5000 --timeout 60
        """
    )
    
    parser.add_argument('url', help='Target URL')
    parser.add_argument('-n', '--requests', type=int, default=1000,
                       help='Total number of requests (default: 1000)')
    parser.add_argument('-c', '--concurrency', type=int, default=10,
                       help='Number of concurrent connections (default: 10)')
    parser.add_argument('-t', '--timeout', type=int, default=30,
                       help='Request timeout in seconds (default: 30)')
    parser.add_argument('-X', '--method', type=str, default='GET',
                       help='HTTP method (default: GET)')
    parser.add_argument('-H', '--header', action='append', dest='headers',
                       help='Custom header (e.g., -H "Content-Type: application/json")')
    parser.add_argument('--body', type=str,
                       help='Request body for POST/PUT requests')
    parser.add_argument('--cooldown', type=float, default=0,
                       help='Cooldown period in seconds between batches (default: 0)')
    parser.add_argument('--batch-size', type=int,
                       help='Number of requests per batch (default: all requests in one batch)')
    parser.add_argument('--no-keep-alive', action='store_true',
                       help='Disable HTTP keep-alive')
    parser.add_argument('--no-verify-ssl', action='store_true',
                       help='Disable SSL certificate verification')
    parser.add_argument('--csv', type=str,
                       help='Save detailed results to CSV file')
    parser.add_argument('--json', type=str,
                       help='Save summary statistics to JSON file')
    
    args = parser.parse_args()
    
    # Parse headers
    headers = {}
    if args.headers:
        for header in args.headers:
            key, value = header.split(':', 1)
            headers[key.strip()] = value.strip()
    
    # Create tester
    tester = StressTester(
        url=args.url,
        total_requests=args.requests,
        concurrency=args.concurrency,
        timeout=args.timeout,
        method=args.method,
        headers=headers,
        body=args.body,
        cooldown=args.cooldown,
        batch_size=args.batch_size,
        keep_alive=not args.no_keep_alive,
        verify_ssl=not args.no_verify_ssl
    )
    
    # Run test
    await tester.run()
    
    # Calculate and display results
    stats = tester.calculate_stats()
    
    if stats:
        tester.print_report(stats)
        tester.print_latency_distribution()
        
        # Save results if requested
        if args.csv:
            tester.save_results_csv(args.csv)
        
        if args.json:
            tester.save_summary_json(stats, args.json)
    else:
        print("[!] No results collected")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[!] Test interrupted by user")
        sys.exit(0)