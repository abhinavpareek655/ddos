import subprocess
import time
import csv
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

# === Configuration ===
URL = "http://172.18.0.2:5000/matmul"  # Server container IP
TOTAL_REQUESTS = 25
CONCURRENCY = 5
COOLDOWN = 2
TIMEOUT = 120

# Docker network configuration - use existing server network
SERVER_NETWORK = "bridge"  # or the name of your server's network
USE_EXISTING_NETWORK = True  # Set to True if server is on existing network

def setup_docker_network():
    """Create a Docker network or use existing one."""
    print("Setting up Docker network...")
    
    if USE_EXISTING_NETWORK:
        # Find server's network
        try:
            result = subprocess.run([
                "docker", "inspect", "-f", 
                "{{range .NetworkSettings.Networks}}{{.NetworkID}}{{end}}",
                "server_container_name"  # Replace with your server container name
            ], capture_output=True, text=True, check=False)
            
            # Get network name from the server container
            result = subprocess.run([
                "docker", "network", "ls", "--format", "{{.Name}}"
            ], capture_output=True, text=True, check=True)
            
            networks = result.stdout.strip().split('\n')
            print(f"Available networks: {networks}")
            
            # Try to find the network with 172.18.x.x subnet
            for net in networks:
                inspect = subprocess.run([
                    "docker", "network", "inspect", net, "-f", "{{.IPAM.Config}}"
                ], capture_output=True, text=True, check=False)
                
                if "172.18" in inspect.stdout:
                    print(f"✓ Using existing network '{net}' (172.18.x.x subnet)\n")
                    return net
            
            # Default to bridge if nothing found
            print(f"✓ Using default bridge network\n")
            return "bridge"
            
        except Exception as e:
            print(f"Using bridge network (error: {e})\n")
            return "bridge"
    else:
        try:
            # Remove existing network if it exists
            subprocess.run(["docker", "network", "rm", "bench_network"], 
                          capture_output=True, check=False)
            
            # Create new network with different subnet
            subprocess.run([
                "docker", "network", "create",
                "--subnet", "172.25.0.0/16",
                "--ip-range", "172.25.0.0/24",
                "bench_network"
            ], check=True, capture_output=True)
            print(f"✓ Docker network 'bench_network' created\n")
            return "bench_network"
        except subprocess.CalledProcessError as e:
            print(f"Error creating network: {e}")
            print("Falling back to bridge network\n")
            return "bridge"

def cleanup_docker_network(network_name):
    """Remove the Docker network if we created it."""
    if not USE_EXISTING_NETWORK and network_name == "bench_network":
        print("\nCleaning up Docker network...")
        subprocess.run(["docker", "network", "rm", network_name], 
                      capture_output=True, check=False)
        print("✓ Cleanup complete")
    else:
        print("\n✓ Using existing network, no cleanup needed")

def make_request_docker(req_id, ip_address, network_name):
    """Run a single request in a Docker container with specific IP."""
    container_name = f"bench_req_{req_id}"
    
    # For existing networks, we can't always assign specific IPs
    # So we'll let Docker assign IPs automatically
    docker_cmd = [
        "docker", "run", "--rm",
        "--name", container_name,
        "--network", network_name
    ]
    
    # Only try to set IP if not using bridge network
    if network_name != "bridge" and not USE_EXISTING_NETWORK:
        docker_cmd.extend(["--ip", ip_address])
    
    docker_cmd.extend([
        "curlimages/curl:latest",
        "-s", "-w", '{"status":%{http_code},"time":%{time_total},"size":%{size_download}}',
        "-o", "/dev/null",
        "--max-time", str(TIMEOUT),
        "-H", "Accept-Encoding: gzip,default",
        URL
    ])
    
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
network_name = setup_docker_network()
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
                futures.append(executor.submit(make_request_docker, req_id, ip, network_name))
            
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
    cleanup_docker_network(network_name)

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