import subprocess
import time
import csv
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

# === Configuration ===
URL = "http://10.50.2.92:5000/matmul"
TOTAL_REQUESTS = 25
CONCURRENCY = 5
COOLDOWN = 2
TIMEOUT = 120

# Docker network configuration
DOCKER_NETWORK = "bench_network"
SUBNET = "172.20.0.0/16"
IP_RANGE = "172.20.0.0/24"

def setup_docker_network():
    """Create a Docker network with custom subnet."""
    print("Setting up Docker network...")
    try:
        # Remove existing network if it exists
        subprocess.run(["docker", "network", "rm", DOCKER_NETWORK], 
                      capture_output=True, check=False)
        
        # Create new network
        subprocess.run([
            "docker", "network", "create",
            "--subnet", SUBNET,
            "--ip-range", IP_RANGE,
            DOCKER_NETWORK
        ], check=True, capture_output=True)
        print(f"✓ Docker network '{DOCKER_NETWORK}' created\n")
    except subprocess.CalledProcessError as e:
        print(f"Error creating network: {e}")
        exit(1)

def cleanup_docker_network():
    """Remove the Docker network."""
    print("\nCleaning up Docker network...")
    subprocess.run(["docker", "network", "rm", DOCKER_NETWORK], 
                  capture_output=True, check=False)
    print("✓ Cleanup complete")

def make_request_docker(req_id, ip_address):
    """Run a single request in a Docker container with specific IP."""
    container_name = f"bench_req_{req_id}"
    
    # Docker command to run curl in alpine container
    docker_cmd = [
        "docker", "run", "--rm",
        "--name", container_name,
        "--network", DOCKER_NETWORK,
        "--ip", ip_address,
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
        
        # Parse curl output
        if result.returncode == 0 and result.stdout:
            data = json.loads(result.stdout)
            return {
                "id": req_id,
                "ip": ip_address,
                "status": data["status"],
                "time": data["time"],
                "size": int(data["size"]),
                "error": None
            }
        else:
            return {
                "id": req_id,
                "ip": ip_address,
                "status": "error",
                "time": elapsed,
                "size": 0,
                "error": result.stderr or "Container failed"
            }
    except Exception as e:
        return {
            "id": req_id,
            "ip": ip_address,
            "status": "error",
            "time": None,
            "size": 0,
            "error": str(e)
        }

def generate_ips(count):
    """Generate unique IPs in the Docker subnet."""
    ips = []
    for i in range(count):
        # Start from 172.20.0.10 to avoid conflicts
        octet4 = 10 + i
        octet3 = (10 + i) // 246  # Overflow to next subnet if needed
        ip = f"172.20.{octet3}.{octet4 % 246 + 10}"
        ips.append(ip)
    return ips

# === Main Execution ===
print("=" * 60)
print("Docker-based Benchmark with Different Source IPs")
print("=" * 60)

# Check if Docker is available
try:
    subprocess.run(["docker", "--version"], capture_output=True, check=True)
except:
    print("❌ Docker not found. Please install Docker first.")
    exit(1)

# Setup
setup_docker_network()
ip_pool = generate_ips(TOTAL_REQUESTS)

# Initialize CSV
with open("results.csv", "w", newline="") as f:
    csv.writer(f).writerow(["RequestID", "SourceIP", "Status", "ResponseTime(s)", 
                           "Size(bytes)", "Timestamp"])

print(f"Starting benchmark: {TOTAL_REQUESTS} requests, {CONCURRENCY} concurrent")
print(f"Each request from unique IP: {ip_pool[0]} - {ip_pool[-1]}\n")

batches = (TOTAL_REQUESTS + CONCURRENCY - 1) // CONCURRENCY
all_results = []
request_counter = 0

try:
    for batch_num in range(batches):
        batch_start = request_counter
        batch_size = min(CONCURRENCY, TOTAL_REQUESTS - request_counter)
        
        print(f"Batch {batch_num + 1}/{batches}: running {batch_size} requests...")
        
        # Run batch with thread pool
        with ThreadPoolExecutor(max_workers=batch_size) as executor:
            futures = []
            for i in range(batch_size):
                req_id = request_counter + i + 1
                ip = ip_pool[request_counter + i]
                futures.append(executor.submit(make_request_docker, req_id, ip))
            
            batch_results = [f.result() for f in as_completed(futures)]
        
        # Save to CSV
        with open("results.csv", "a", newline="") as f:
            writer = csv.writer(f)
            for r in batch_results:
                writer.writerow([
                    r["id"], r["ip"], r["status"],
                    f"{r['time']:.4f}" if r["time"] else "N/A",
                    r["size"], time.strftime("%Y-%m-%d %H:%M:%S")
                ])
        
        all_results.extend(batch_results)
        request_counter += batch_size
        
        # Stats
        successes = [r for r in batch_results if r["status"] == 200]
        rate_limited = [r for r in batch_results if r["status"] == 429]
        
        if rate_limited:
            print(f"  ⚠️  {len(rate_limited)} requests rate-limited (429)")
        if successes:
            avg = sum(float(r["time"]) for r in successes) / len(successes)
            print(f"  ✓ {len(successes)}/{batch_size} successful, avg {avg:.3f}s")
        
        print()
        
        if batch_num < batches - 1:
            time.sleep(COOLDOWN)

finally:
    # Always cleanup
    cleanup_docker_network()

# === Final Summary ===
successes = [r for r in all_results if r["status"] == 200]
rate_limited = [r for r in all_results if r["status"] == 429]

print("\n" + "=" * 60)
if successes:
    times = [float(r["time"]) for r in successes]
    print(f"✅ Complete! {len(successes)}/{TOTAL_REQUESTS} successful")
    print(f"Min: {min(times):.3f}s | Max: {max(times):.3f}s | Avg: {sum(times)/len(times):.3f}s")
    if rate_limited:
        print(f"⚠️  {len(rate_limited)} requests were rate-limited")
else:
    print("❌ No successful requests")

print(f"\nResults saved to results.csv")
print("=" * 60)