import requests
import time
import csv
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

# === Configuration ===
URL = "http://10.50.2.92:5000/matmul"
TOTAL_REQUESTS = 25
CONCURRENCY = 5
COOLDOWN = 2  # seconds between batches
TIMEOUT = 120
USE_UNIQUE_IPS = True  # Set False to disable unique IP per request

# === Generate unique IPs upfront ===
def generate_unique_ips(count):
    """Generate sequential unique IP addresses, avoiding reserved ranges."""
    ips = []
    # Start from 10.0.0.1 (private range, safe for testing)
    base = 10 * 256**3  # 10.0.0.0
    
    for i in range(count):
        ip_num = base + i + 1  # Start from 10.0.0.1
        
        octet1 = (ip_num >> 24) & 0xFF
        octet2 = (ip_num >> 16) & 0xFF
        octet3 = (ip_num >> 8) & 0xFF
        octet4 = ip_num & 0xFF
        
        # Skip invalid IPs (broadcast addresses ending in .0 or .255)
        if octet4 == 0 or octet4 == 255:
            ip_num += 1
            octet4 = ip_num & 0xFF
        
        ips.append(f"{octet1}.{octet2}.{octet3}.{octet4}")
    
    return ips

IP_POOL = generate_unique_ips(TOTAL_REQUESTS) if USE_UNIQUE_IPS else []

# === Helper Functions ===
def make_request(req_id):
    """Perform a single HTTP request."""
    headers = {"Accept-Encoding": "gzip,default"}
    if USE_UNIQUE_IPS:
        headers["X-Forwarded-For"] = IP_POOL[req_id - 1]  # req_id starts at 1
    
    start = time.perf_counter()
    try:
        resp = requests.get(URL, headers=headers, timeout=TIMEOUT)
        elapsed = time.perf_counter() - start
        return {"id": req_id, "status": resp.status_code, "time": elapsed, "size": len(resp.content)}
    except Exception as e:
        return {"id": req_id, "status": "error", "time": None, "size": 0, "error": str(e)}

# === Initialize CSV ===
with open("results.csv", "w", newline="") as f:
    csv.writer(f).writerow(["RequestID", "Status", "ResponseTime(s)", "Size(bytes)", "Timestamp"])

# === Run Benchmark ===
print(f"Starting benchmark: {TOTAL_REQUESTS} requests, {CONCURRENCY} concurrent")
print(f"Unique IPs: {'Enabled (' + str(len(IP_POOL)) + ' IPs generated)' if USE_UNIQUE_IPS else 'Disabled'}\n")

batches = (TOTAL_REQUESTS + CONCURRENCY - 1) // CONCURRENCY
all_results = []

for batch_num in range(batches):
    batch_start = batch_num * CONCURRENCY + 1
    batch_size = min(CONCURRENCY, TOTAL_REQUESTS - batch_num * CONCURRENCY)
    
    print(f"Batch {batch_num + 1}/{batches}: running {batch_size} requests...")
    
    with ThreadPoolExecutor(max_workers=batch_size) as executor:
        futures = [executor.submit(make_request, batch_start + i) for i in range(batch_size)]
        batch_results = [f.result() for f in as_completed(futures)]
    
    # Save to CSV
    with open("results.csv", "a", newline="") as f:
        writer = csv.writer(f)
        for r in batch_results:
            writer.writerow([r["id"], r["status"], f"{r['time']:.4f}" if r["time"] else "N/A", 
                           r["size"], time.strftime("%Y-%m-%d %H:%M:%S")])
    
    all_results.extend(batch_results)
    
    # Stats
    successes = [r for r in batch_results if r["status"] == 200]
    avg = sum(r["time"] for r in successes) / len(successes) if successes else 0
    print(f"  ✓ {len(successes)}/{batch_size} successful, avg {avg:.3f}s\n")
    
    if batch_num < batches - 1:
        time.sleep(COOLDOWN)

# === Final Summary ===
successes = [r for r in all_results if r["status"] == 200]
if successes:
    times = [r["time"] for r in successes]
    print(f"✅ Complete! {len(successes)}/{TOTAL_REQUESTS} successful")
    print(f"Min: {min(times):.3f}s | Max: {max(times):.3f}s | Avg: {sum(times)/len(times):.3f}s")
else:
    print("❌ No successful requests")

print(f"\nResults saved to results.csv")