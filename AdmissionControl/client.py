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
SERVER_NETWORK = "calico_net"

def make_request_docker(req_id):
    container_name = f"bench_req_{req_id}_{int(time.time() * 1000)}"

    try:
        # Create and start container
        subprocess.run([
            "docker", "run", "-d",
            "--name", container_name,
            "--network", SERVER_NETWORK,
            "curlimages/curl:latest",
            "sleep", "120"
        ], check=True, capture_output=True)

        # Wait briefly for network setup
        time.sleep(0.2)

        # Get container IP after it's running
        inspect = subprocess.run(
            ["docker", "inspect", container_name],
            capture_output=True, text=True, check=True
        )
        inspect_json = json.loads(inspect.stdout)[0]
        networks = inspect_json["NetworkSettings"]["Networks"]
        container_ip = list(networks.values())[0].get("IPAddress", "not_assigned")

        # Execute curl
        curl_cmd = [
            "docker", "exec", container_name,
            "curl",
            "-s", "-w", '{"status":%{http_code},"time":%{time_total},"size":%{size_download}}',
            "-o", "/dev/null",
            "--max-time", str(TIMEOUT),
            "-H", "Accept-Encoding: gzip,default",
            URL
        ]

        start = time.perf_counter()
        result = subprocess.run(curl_cmd, capture_output=True, text=True)
        elapsed = time.perf_counter() - start

        # Cleanup
        subprocess.run(["docker", "rm", "-f", container_name], 
                      check=False, capture_output=True)

        # Parse result
        if result.returncode == 0:
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
            except:
                return {
                    "id": req_id,
                    "status": "error",
                    "time": elapsed,
                    "size": 0,
                    "container_ip": container_ip,
                    "error": "Invalid JSON response"
                }

        return {
            "id": req_id,
            "status": "error",
            "time": elapsed,
            "size": 0,
            "container_ip": container_ip,
            "error": result.stderr or "Request failed"
        }

    except Exception as e:
        subprocess.run(["docker", "rm", "-f", container_name], 
                      check=False, capture_output=True)
        return {
            "id": req_id,
            "status": "error",
            "time": None,
            "size": 0,
            "container_ip": "unknown",
            "error": str(e)
        }

# === Main Execution ===
print("Docker Benchmark - Different Source IPs")
print("-" * 60)

# Check Docker
try:
    result = subprocess.run(["docker", "--version"], 
                          capture_output=True, check=True, text=True)
    print(f"Docker: {result.stdout.strip()}")
except:
    print("ERROR: Docker not found")
    exit(1)

# Pull curl image
print("Pulling curl image...")
subprocess.run(["docker", "pull", "curlimages/curl:latest"], 
              capture_output=True, check=True)

# Test connection
print(f"Testing connection to {URL}...")
test_result = make_request_docker(0)
if test_result["status"] == 200:
    print(f"Connection OK (IP: {test_result['container_ip']}, Time: {test_result['time']:.3f}s)")
else:
    print(f"WARNING: Connection test failed")
    print(f"Error: {test_result.get('error', 'Unknown')}")
    print(f"Check: SERVER_NETWORK='{SERVER_NETWORK}', URL='{URL}'")
    response = input("Continue? (y/n): ")
    if response.lower() != 'y':
        exit(1)

print()

# Initialize CSV
with open("results.csv", "w", newline="") as f:
    csv.writer(f).writerow(["RequestID", "Status", "ResponseTime(s)", 
                           "Size(bytes)", "ContainerIP", "Timestamp"])

print(f"Running {TOTAL_REQUESTS} requests, {CONCURRENCY} concurrent")
print(f"Network: {SERVER_NETWORK}\n")

batches = (TOTAL_REQUESTS + CONCURRENCY - 1) // CONCURRENCY
all_results = []
request_counter = 0

for batch_num in range(batches):
    batch_size = min(CONCURRENCY, TOTAL_REQUESTS - request_counter)
    
    print(f"Batch {batch_num + 1}/{batches} ({batch_size} requests)...", end=" ", flush=True)
    
    # Run batch
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
    
    status_parts = []
    if successes:
        avg = sum(float(r["time"]) for r in successes) / len(successes)
        status_parts.append(f"{len(successes)} OK (avg {avg:.2f}s)")
    if rate_limited:
        status_parts.append(f"{len(rate_limited)} rate-limited")
    if errors:
        status_parts.append(f"{len(errors)} failed")
    
    print(", ".join(status_parts))
    
    if batch_num < batches - 1:
        time.sleep(COOLDOWN)

# === Final Summary ===
successes = [r for r in all_results if r["status"] == 200]
rate_limited = [r for r in all_results if r["status"] == 429]
errors = [r for r in all_results if r["status"] == "error"]

print("\n" + "-" * 60)
if successes:
    times = [float(r["time"]) for r in successes]
    print(f"Complete: {len(successes)}/{TOTAL_REQUESTS} successful")
    print(f"Time - Min: {min(times):.3f}s, Max: {max(times):.3f}s, Avg: {sum(times)/len(times):.3f}s")
    if rate_limited:
        print(f"Rate-limited: {len(rate_limited)}")
    if errors:
        print(f"Failed: {len(errors)}")
        if errors:
            print("\nFirst error samples:")
            for err in errors[:3]:
                if err.get('error'):
                    print(f"  Req {err['id']}: {err['error']}")
else:
    print("FAILED: No successful requests")
    if errors:
        print("\nErrors:")
        for err in errors[:5]:
            if err.get('error'):
                print(f"  Req {err['id']}: {err['error']}")

print(f"\nResults: results.csv")
print("-" * 60)