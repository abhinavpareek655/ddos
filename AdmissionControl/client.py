import subprocess
import time
import csv
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

# === Configuration ===
URL = "http://172.18.0.2:5000/matmul"
TOTAL_REQUESTS = 25
CONCURRENCY = 5
COOLDOWN = 2
TIMEOUT = 120

# Find what network your server is using
# Replace 'bridge' with your server's network name if different
SERVER_NETWORK = "server_default"  # Common options: bridge, host, or custom network name

def make_request_docker(req_id):
    """Run a single request in a Docker container and capture container IP."""
    container_name = f"bench_req_{req_id}_{int(time.time() * 1000)}"
    
    docker_cmd = [
        "docker", "run", "--rm",
        "--name", container_name,
        "--network", SERVER_NETWORK,
        "curlimages/curl:latest",
        "-s", "-w", '{"status":%{http_code},"time":%{time_total},"size":%{size_download}}',
        "-o", "/dev/null",
        "--max-time", str(TIMEOUT),
        "-H", "Accept-Encoding: gzip,default",
        URL
    ]

    start = time.perf_counter()
    try:
        result = subprocess.run(docker_cmd, capture_output=True, text=True,
                                timeout=TIMEOUT + 5, check=False)
        elapsed = time.perf_counter() - start

        # --- NEW: Get IP using docker inspect ---
        try:
            inspect = subprocess.run(
                ["docker", "inspect", container_name],
                capture_output=True, text=True
            )
            inspect_json = json.loads(inspect.stdout)[0]
            container_ip = list(inspect_json["NetworkSettings"]["Networks"].values())[0]["IPAddress"]
        except:
            container_ip = "unknown"

        # Parse curl output
        if result.returncode == 0 and result.stdout:
            try:
                data = json.loads(result.stdout)
                return {
                    "id": req_id,
                    "status": data["status"],
                    "time": data["time"],
                    "size": int(data["size"]),
                    "container_ip": container_ip,
                    "error": None
                }
            except json.JSONDecodeError:
                return {
                    "id": req_id,
                    "status": "error",
                    "time": elapsed,
                    "size": 0,
                    "container_ip": container_ip,
                    "error": f"Invalid response: {result.stdout}"
                }
        else:
            error_msg = result.stderr.strip() if result.stderr else "Container failed"
            return {
                "id": req_id,
                "status": "error",
                "time": elapsed,
                "size": 0,
                "container_ip": container_ip,
                "error": error_msg
            }
    except subprocess.TimeoutExpired:
        return {
            "id": req_id,
            "status": "timeout",
            "time": TIMEOUT,
            "size": 0,
            "container_ip": "unknown",
            "error": "Request timeout"
        }

# === Main Execution ===
print("=" * 60)
print("Docker-based Benchmark with Different Source IPs")
print("=" * 60)

# Check if Docker is available
try:
    result = subprocess.run(["docker", "--version"], capture_output=True, check=True, text=True)
    print(f"✓ Docker found: {result.stdout.strip()}")
except:
    print("❌ Docker not found. Please install Docker first.")
    exit(1)

# Check if curl image is available
print("Checking for curl image...")
try:
    subprocess.run(["docker", "pull", "curlimages/curl:latest"], 
                  capture_output=True, check=True)
    print("✓ Curl image ready")
except:
    print("⚠️  Warning: Could not pull curl image, will try to use cached version")

# Test network connectivity
print(f"\nTesting connection to {URL}...")
test_result = make_request_docker(0)
if test_result["status"] == 200:
    print(f"✓ Server reachable (response time: {test_result['time']:.3f}s)\n")
elif "error" in test_result and test_result["error"]:
    print(f"⚠️  Connection test failed: {test_result['error']}")
    print(f"   Make sure:")
    print(f"   1. Your server container is running")
    print(f"   2. SERVER_NETWORK is set correctly (current: '{SERVER_NETWORK}')")
    print(f"   3. URL is correct (current: '{URL}')\n")
    response = input("Continue anyway? (y/n): ")
    if response.lower() != 'y':
        exit(1)

# Initialize CSV
with open("results.csv", "w", newline="") as f:
    csv.writer(f).writerow(["RequestID", "Status", "ResponseTime(s)", 
                       "Size(bytes)", "ContainerIP", "Timestamp"])

print(f"Starting benchmark: {TOTAL_REQUESTS} requests, {CONCURRENCY} concurrent")
print(f"Using network: {SERVER_NETWORK}\n")

batches = (TOTAL_REQUESTS + CONCURRENCY - 1) // CONCURRENCY
all_results = []
request_counter = 0

for batch_num in range(batches):
    batch_start = request_counter
    batch_size = min(CONCURRENCY, TOTAL_REQUESTS - request_counter)
    
    print(f"Batch {batch_num + 1}/{batches}: running {batch_size} requests...")
    
    # Run batch with thread pool
    with ThreadPoolExecutor(max_workers=batch_size) as executor:
        futures = []
        for i in range(batch_size):
            req_id = request_counter + i + 1
            futures.append(executor.submit(make_request_docker, req_id))
        
        batch_results = [f.result() for f in as_completed(futures)]
    
    # Save to CSV
    with open("results.csv", "a", newline="") as f:
        writer = csv.writer(f)
        for r in batch_results:
            writer.writerow([
                r["id"], r["status"],
                f"{r['time']:.4f}" if r["time"] else "N/A",
                r["size"],
                r.get("container_ip", "unknown"),
                time.strftime("%Y-%m-%d %H:%M:%S")
            ])
    
    all_results.extend(batch_results)
    request_counter += batch_size
    
    # Stats
    successes = [r for r in batch_results if r["status"] == 200]
    rate_limited = [r for r in batch_results if r["status"] == 429]
    errors = [r for r in batch_results if r["status"] == "error"]
    
    if rate_limited:
        print(f"  ⚠️  {len(rate_limited)} requests rate-limited (429)")
    if errors:
        print(f"  ❌ {len(errors)} requests failed")
        for err in errors[:2]:  # Show first 2 errors
            print(f"     Error: {err.get('error', 'Unknown')}")
    if successes:
        avg = sum(float(r["time"]) for r in successes) / len(successes)
        print(f"  ✓ {len(successes)}/{batch_size} successful, avg {avg:.3f}s")
    
    print()
    
    if batch_num < batches - 1:
        time.sleep(COOLDOWN)

# === Final Summary ===
successes = [r for r in all_results if r["status"] == 200]
rate_limited = [r for r in all_results if r["status"] == 429]
errors = [r for r in all_results if r["status"] == "error"]

print("\n" + "=" * 60)
if successes:
    times = [float(r["time"]) for r in successes]
    print(f"✅ Complete! {len(successes)}/{TOTAL_REQUESTS} successful")
    print(f"Min: {min(times):.3f}s | Max: {max(times):.3f}s | Avg: {sum(times)/len(times):.3f}s")
    if rate_limited:
        print(f"⚠️  {len(rate_limited)} requests were rate-limited")
    if errors:
        print(f"❌ {len(errors)} requests failed")
else:
    print("❌ No successful requests")
    if errors:
        print("\nCommon errors:")
        for err in errors[:5]:
            if err.get('error'):
                print(f"  - {err['error']}")

print(f"\nResults saved to results.csv")
print("=" * 60)