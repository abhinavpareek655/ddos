# Advanced Stress Testing Tool - User Guide

## Overview

A Python-based HTTP stress testing tool with features beyond Apache Bench (ab), including:

- ✅ **Async I/O**: Uses `asyncio` and `aiohttp` for high concurrency
- ✅ **Cooldown periods**: Pause between request batches
- ✅ **Batch processing**: Send requests in waves
- ✅ **Detailed metrics**: Response times, status codes, errors
- ✅ **Multiple output formats**: Console, CSV, JSON
- ✅ **Real-time progress**: Live progress bar with RPS
- ✅ **Comprehensive visualization**: 6 different graph types

---

## Installation

```bash
# Install required packages
pip3 install aiohttp requests matplotlib numpy
```

**requirements.txt:**
```
aiohttp>=3.9.0
requests>=2.31.0
matplotlib>=3.8.0
numpy>=1.24.0
```

---

## Basic Usage

### Simple Test (Like Apache Bench)

```bash
# 10,000 requests with 100 concurrent connections
python3 stress_test.py http://localhost:5000/matmul -n 10000 -c 100
```

### With Data Collection

```bash
# Save detailed results and summary
python3 stress_test.py http://localhost:5000/matmul \
    -n 10000 -c 100 \
    --csv results.csv \
    --json summary.json
```

### Generate Visualizations

```bash
# Create graphs from results
python3 visualize_stress_test.py results.csv --output my_test
```

---

## Advanced Features

### 1. Cooldown Between Batches

Useful for testing server recovery or preventing resource exhaustion:

```bash
# Send 1000 requests, pause 2 seconds, repeat
python3 stress_test.py http://localhost:5000/matmul \
    -n 10000 -c 100 \
    --batch-size 1000 \
    --cooldown 2
```

**Use cases:**
- Test server recovery after load spikes
- Prevent overwhelming monitoring systems
- Simulate realistic traffic patterns
- Allow garbage collection between batches

### 2. High Concurrency Testing

Test extreme concurrency levels:

```bash
# 100,000 requests with 5,000 concurrent connections
python3 stress_test.py http://localhost:5000/matmul \
    -n 100000 -c 5000 \
    --timeout 60
```

### 3. POST Requests with Body

```bash
# POST with JSON body
python3 stress_test.py http://localhost:5000/api \
    -n 1000 -c 50 \
    -X POST \
    --body '{"key":"value"}' \
    -H "Content-Type: application/json"
```

### 4. Custom Headers

```bash
# Add authentication and custom headers
python3 stress_test.py http://localhost:5000/api \
    -n 5000 -c 100 \
    -H "Authorization: Bearer token123" \
    -H "X-Custom-Header: value"
```

### 5. Disable Keep-Alive

Test connection establishment overhead:

```bash
# New connection for each request
python3 stress_test.py http://localhost:5000/matmul \
    -n 1000 -c 50 \
    --no-keep-alive
```

### 6. HTTPS without SSL Verification

For testing with self-signed certificates:

```bash
python3 stress_test.py https://localhost:5000/matmul \
    -n 1000 -c 50 \
    --no-verify-ssl
```

---

## Complete Workflow Example

### Step 1: Start System Monitoring

```bash
# Terminal 1: Monitor system resources
python3 monitor.py --interval 1 --output system_during_test.csv
```

### Step 2: Run Stress Test

```bash
# Terminal 2: Run stress test
python3 stress_test.py http://localhost:5000/matmul \
    -n 50000 -c 500 \
    --batch-size 5000 \
    --cooldown 1 \
    --csv stress_results.csv \
    --json stress_summary.json
```

### Step 3: Stop Monitoring

Press `Ctrl+C` in Terminal 1 to stop monitoring.

### Step 4: Generate Visualizations

```bash
# Visualize stress test results
python3 visualize_stress_test.py stress_results.csv --output stress_graphs

# Visualize system monitoring data
python3 visualize.py system_during_test.csv --output system_graphs
```

### Step 5: Analyze Results

You now have:
- `stress_graphs_*.png` - 6 graphs of stress test metrics
- `system_graphs_*.png` - 5 graphs of system performance
- `stress_summary.json` - Statistical summary
- Combined view of application and system behavior

---

## Understanding the Output

### Console Output During Test

```
======================================================================
STRESS TEST CONFIGURATION
======================================================================
Target URL:          http://localhost:5000/matmul
Total Requests:      10,000
Concurrency:         100
Method:              GET
Timeout:             30s
Keep-Alive:          True
Batch Size:          10,000
======================================================================

[████████████████████████████████████████████████] 100.0% | 10000/10000 | 845 RPS
```

### Final Report

```
======================================================================
TEST RESULTS
======================================================================

📊 SUMMARY
----------------------------------------------------------------------
Total Requests:        10,000
Successful:            9,987 (99.9%)
Failed:                13 (0.1%)
Total Time:            11.83s
Requests per Second:   845.39
Data Transferred:      1.23 GB

⏱️  RESPONSE TIMES (milliseconds)
----------------------------------------------------------------------
Average:               118.45 ms
Median:                115.23 ms
Min:                   45.12 ms
Max:                   1234.56 ms
95th Percentile:       145.67 ms
99th Percentile:       189.34 ms

📡 STATUS CODES
----------------------------------------------------------------------
200 OK                 9,987 (99.9%)
500 Internal Server    13 (0.1%)

📈 LATENCY DISTRIBUTION
----------------------------------------------------------------------
<10ms        ░░░░░                                           142 (  1.4%)
10-50ms      ████░░░░░░░░░░░░░░░░░░░░░░░                   1,234 ( 12.3%)
50-100ms     ████████████████████████████████████          3,456 ( 34.6%)
100-200ms    ██████████████████████████████████████████    4,123 ( 41.2%)
200-500ms    ████████░░░░░░░░░░░░░░░░░░░                     987 (  9.9%)
500ms-1s     ██░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░           45 (  0.5%)
1-2s         ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░           13 (  0.1%)
```

---

## Performance Comparison: Apache Bench vs This Tool

| Feature | Apache Bench (ab) | stress_test.py |
|---------|------------------|----------------|
| Concurrency | Up to ~1,000 | **Up to 50,000+** |
| Progress bar | No | **Yes, with RPS** |
| Detailed metrics | Basic | **Comprehensive** |
| CSV export | No | **Yes** |
| JSON export | No | **Yes** |
| Cooldown periods | No | **Yes** |
| Batch processing | No | **Yes** |
| Error categorization | Basic | **Detailed** |
| Percentiles | p50, p99 | **p50, p95, p99** |
| Keep-alive control | Limited | **Full control** |
| Custom headers | Limited | **Unlimited** |
| Visualization | None | **6 graph types** |

---

## Generated Graphs

### 1. Response Times Over Time
- Scatter plot of all requests
- Moving average trend line
- Identifies performance degradation patterns

### 2. Throughput Analysis
- Requests per second over time
- Shows server capacity under sustained load
- Identifies bottlenecks

### 3. Latency Distribution
- Histogram of response times
- Box plot with quartiles
- Percentile markers (p50, p95, p99)

### 4. Status Code Analysis
- Bar chart of status codes
- Pie chart of success vs failures
- Percentage breakdown

### 5. Error Analysis
- Distribution of error types
- Helps identify failure patterns
- Shows most common errors

### 6. Dashboard
- All-in-one view
- Summary statistics
- Quick overview of test results

---

## Tips for Effective Testing

### 1. Start Small, Scale Up

```bash
# Step 1: Baseline (low load)
python3 stress_test.py http://localhost:5000/matmul -n 100 -c 10

# Step 2: Medium load
python3 stress_test.py http://localhost:5000/matmul -n 1000 -c 100

# Step 3: High load
python3 stress_test.py http://localhost:5000/matmul -n 10000 -c 500

# Step 4: Extreme load
python3 stress_test.py http://localhost:5000/matmul -n 100000 -c 5000
```

### 2. Monitor System Resources

Always run system monitoring during stress tests:

```bash
# Terminal 1
python3 monitor.py --interval 1 --output load_test.csv

# Terminal 2
python3 stress_test.py ...

# Terminal 3 (optional - real-time view)
watch -n 1 'ss -s; free -h'
```

### 3. Use Cooldown for Realistic Testing

Real traffic comes in waves, not constant streams:

```bash
# Simulate burst traffic patterns
python3 stress_test.py http://localhost:5000/matmul \
    -n 10000 -c 200 \
    --batch-size 500 \
    --cooldown 0.5
```

### 4. Test Different Endpoints

Create a test script to test multiple endpoints:

```bash
#!/bin/bash
# test_all_endpoints.sh

ENDPOINTS=(
    "http://localhost:5000/ping"
    "http://localhost:5000/health"
    "http://localhost:5000/matmul"
)

for endpoint in "${ENDPOINTS[@]}"; do
    echo "Testing: $endpoint"
    python3 stress_test.py "$endpoint" -n 5000 -c 100 \
        --csv "results_$(basename $endpoint).csv"
done
```

### 5. Identify Bottlenecks

Compare stress test results with system monitoring:

- **High CPU, normal latency** → CPU-bound (expected for matrix multiplication)
- **Normal CPU, high latency** → I/O bottleneck or network issues
- **Increasing latency over time** → Memory leak or resource exhaustion
- **Spike in SYN_RECV connections** → SYN flood or connection handling issues
- **High TIME_WAIT connections** → Connection recycling problems

---

## Troubleshooting

### "Too many open files" Error

```bash
# Increase file descriptor limit
ulimit -n 100000

# Then re-run test
python3 stress_test.py ...
```

### "Connection refused" Errors

Server might be overloaded. Try:
1. Reduce concurrency: `-c 50` instead of `-c 500`
2. Add cooldown: `--cooldown 1 --batch-size 1000`
3. Increase server workers

### Low RPS Despite High Concurrency

Possible causes:
1. Server bottleneck (CPU/memory)
2. Network bandwidth limit
3. Client machine limitations
4. Keep-alive disabled (try removing `--no-keep-alive`)

### Script Crashes with High Concurrency

```bash
# Python might hit resource limits
# Reduce concurrency or increase system limits

# Check current limits
ulimit -a

# Increase (as needed)
ulimit -n 100000
ulimit -u unlimited
```

### Timeouts with Matrix Multiplication

Matrix multiplication is CPU-intensive:

```bash
# Increase timeout for slow operations
python3 stress_test.py http://localhost:5000/matmul \
    -n 1000 -c 50 \
    --timeout 120
```

---

## Interpreting Results for DDoS Testing

### Normal Operation Indicators

- ✅ Success rate > 99%
- ✅ P95 latency < 2x average
- ✅ Stable RPS throughout test
- ✅ Low connection states (SYN_RECV < 100)

### Server Under Stress

- ⚠️ Success rate 95-99%
- ⚠️ P95 latency 2-5x average
- ⚠️ Decreasing RPS over time
- ⚠️ Moderate connection states (SYN_RECV 100-1000)

### Server Failing (DDoS-like Conditions)

- ❌ Success rate < 95%
- ❌ P95 latency > 5x average
- ❌ RPS drops significantly
- ❌ High connection states (SYN_RECV > 1000)
- ❌ Many 5xx errors or timeouts

---

## Example Test Scenarios

### Scenario 1: Finding Maximum Capacity

```bash
# Binary search for max RPS
for c in 50 100 200 500 1000 2000 5000; do
    echo "Testing concurrency: $c"
    python3 stress_test.py http://localhost:5000/matmul \
        -n 10000 -c $c \
        --csv "capacity_test_c${c}.csv" \
        --json "capacity_test_c${c}.json"
    sleep 5
done
```

### Scenario 2: Endurance Testing

```bash
# Long-running test to check for memory leaks
python3 stress_test.py http://localhost:5000/matmul \
    -n 100000 -c 100 \
    --batch-size 1000 \
    --cooldown 0.1 \
    --csv endurance_test.csv
```

### Scenario 3: Burst Traffic

```bash
# Simulate sudden traffic spikes
python3 stress_test.py http://localhost:5000/matmul \
    -n 50000 -c 1000 \
    --batch-size 5000 \
    --cooldown 5 \
    --csv burst_test.csv
```

### Scenario 4: Sustained Load

```bash
# Constant moderate load
python3 stress_test.py http://localhost:5000/matmul \
    -n 100000 -c 200 \
    --csv sustained_test.csv
```

---

## Integration with CI/CD

### Performance Regression Testing

```bash
#!/bin/bash
# performance_test.sh

# Run stress test
python3 stress_test.py http://localhost:5000/matmul \
    -n 5000 -c 100 \
    --json performance_results.json

# Extract RPS from JSON
RPS=$(jq '.stats.requests_per_second' performance_results.json)
THRESHOLD=500

# Check against threshold
if (( $(echo "$RPS < $THRESHOLD" | bc -l) )); then
    echo "FAIL: RPS $RPS is below threshold $THRESHOLD"
    exit 1
else
    echo "PASS: RPS $RPS meets threshold"
    exit 0
fi
```

---

## Comparison with Other Tools

| Tool | Best For | Limitation |
|------|----------|-----------|
| **stress_test.py** | High concurrency, detailed analysis | Requires Python |
| **Apache Bench** | Quick tests, simplicity | Low max concurrency |
| **wrk** | High performance, Lua scripting | Harder to use |
| **Locust** | Distributed testing, web UI | More complex setup |
| **JMeter** | Enterprise, GUI | Heavy, Java-based |

---

## Summary

This stress testing tool provides:

1. **Easy-to-use** CLI interface like Apache Bench
2. **Advanced features** beyond basic load testing
3. **Detailed metrics** for thorough analysis
4. **Beautiful visualizations** for presentations
5. **Flexible configuration** for various test scenarios
6. **Python-based** for easy modification and integration

Perfect for testing your high-performance Flask server! 🚀