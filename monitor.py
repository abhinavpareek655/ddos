#!/usr/bin/env python3
"""
Lightweight System Monitor for DDoS Detection
Collects: CPU, Memory, Disk, Network, Connections, Buffers
Usage: python3 monitor.py --interval 1 --output system_metrics.csv
       Press Ctrl+C to stop
"""

import time
import csv
import argparse
import signal
import sys
from datetime import datetime
from pathlib import Path

class SystemMonitor:
    def __init__(self, interval=1):
        self.interval = interval
        self.running = True
        self.prev_net = None
        self.prev_disk = None
        self.prev_cpu = None
        
        # Register signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, sig, frame):
        print("\n[!] Stopping monitor gracefully...")
        self.running = False
    
    def read_file(self, path):
        """Read file content safely"""
        try:
            with open(path, 'r') as f:
                return f.read()
        except:
            return ""
    
    def get_cpu_stats(self):
        """Get CPU usage percentage"""
        cpu_line = self.read_file('/proc/stat').split('\n')[0]
        fields = cpu_line.split()[1:]
        current = [int(x) for x in fields[:8]]
        
        if self.prev_cpu:
            # Calculate delta
            deltas = [current[i] - self.prev_cpu[i] for i in range(len(current))]
            total = sum(deltas)
            idle = deltas[3]  # idle time
            usage = 100.0 * (total - idle) / total if total > 0 else 0.0
        else:
            usage = 0.0
        
        self.prev_cpu = current
        return round(usage, 2)
    
    def get_memory_stats(self):
        """Get memory and buffer/cache stats"""
        mem_info = {}
        for line in self.read_file('/proc/meminfo').split('\n'):
            if line:
                parts = line.split(':')
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = int(parts[1].strip().split()[0])  # KB
                    mem_info[key] = value
        
        total = mem_info.get('MemTotal', 0)
        available = mem_info.get('MemAvailable', 0)
        buffers = mem_info.get('Buffers', 0)
        cached = mem_info.get('Cached', 0)
        
        used = total - available
        mem_usage_pct = 100.0 * used / total if total > 0 else 0.0
        
        # Convert to MB
        return {
            'mem_used_mb': round(used / 1024, 2),
            'mem_total_mb': round(total / 1024, 2),
            'mem_usage_pct': round(mem_usage_pct, 2),
            'buffers_mb': round(buffers / 1024, 2),
            'cached_mb': round(cached / 1024, 2)
        }
    
    def get_disk_stats(self):
        """Get disk I/O statistics"""
        disk_stats = {}
        
        # Read from /proc/diskstats
        for line in self.read_file('/proc/diskstats').split('\n'):
            if not line:
                continue
            parts = line.split()
            if len(parts) < 14:
                continue
            
            device = parts[2]
            # Focus on main disks (sda, nvme0n1, etc.), skip partitions
            if device.startswith(('sd', 'nvme', 'vd', 'hd')) and not any(c.isdigit() for c in device[-1]):
                reads = int(parts[5])  # sectors read
                writes = int(parts[9])  # sectors written
                disk_stats[device] = {'reads': reads, 'writes': writes}
        
        if not disk_stats:
            return {'disk_read_mb_s': 0.0, 'disk_write_mb_s': 0.0}
        
        # Calculate total I/O rate
        total_reads = sum(d['reads'] for d in disk_stats.values())
        total_writes = sum(d['writes'] for d in disk_stats.values())
        
        if self.prev_disk:
            # Sector size is typically 512 bytes
            read_mb = (total_reads - self.prev_disk['reads']) * 512 / 1024 / 1024 / self.interval
            write_mb = (total_writes - self.prev_disk['writes']) * 512 / 1024 / 1024 / self.interval
        else:
            read_mb = 0.0
            write_mb = 0.0
        
        self.prev_disk = {'reads': total_reads, 'writes': total_writes}
        
        return {
            'disk_read_mb_s': round(read_mb, 2),
            'disk_write_mb_s': round(write_mb, 2)
        }
    
    def get_disk_usage(self):
        """Get disk space usage for root partition"""
        try:
            stat = Path('/').stat()
            # This is simplified; for more accurate use statvfs
            import os
            st = os.statvfs('/')
            total = st.f_blocks * st.f_frsize / 1024 / 1024 / 1024  # GB
            free = st.f_bfree * st.f_frsize / 1024 / 1024 / 1024
            used = total - free
            usage_pct = 100.0 * used / total if total > 0 else 0.0
            
            return {
                'disk_used_gb': round(used, 2),
                'disk_total_gb': round(total, 2),
                'disk_usage_pct': round(usage_pct, 2)
            }
        except:
            return {'disk_used_gb': 0, 'disk_total_gb': 0, 'disk_usage_pct': 0}
    
    def get_network_stats(self):
        """Get network traffic statistics"""
        net_stats = {}
        
        for line in self.read_file('/proc/net/dev').split('\n')[2:]:
            if not line or ':' not in line:
                continue
            
            parts = line.split(':')
            interface = parts[0].strip()
            
            # Skip loopback
            if interface == 'lo':
                continue
            
            stats = parts[1].split()
            if len(stats) < 16:
                continue
            
            rx_bytes = int(stats[0])
            tx_bytes = int(stats[8])
            
            net_stats[interface] = {'rx': rx_bytes, 'tx': tx_bytes}
        
        if not net_stats:
            return {'net_rx_mb_s': 0.0, 'net_tx_mb_s': 0.0}
        
        # Calculate total network rate
        total_rx = sum(d['rx'] for d in net_stats.values())
        total_tx = sum(d['tx'] for d in net_stats.values())
        
        if self.prev_net:
            rx_mb = (total_rx - self.prev_net['rx']) / 1024 / 1024 / self.interval
            tx_mb = (total_tx - self.prev_net['tx']) / 1024 / 1024 / self.interval
        else:
            rx_mb = 0.0
            tx_mb = 0.0
        
        self.prev_net = {'rx': total_rx, 'tx': total_tx}
        
        return {
            'net_rx_mb_s': round(rx_mb, 2),
            'net_tx_mb_s': round(tx_mb, 2)
        }
    
    def get_connection_stats(self):
        """Get TCP connection statistics - important for DDoS detection"""
        states = {
            'ESTABLISHED': 0,
            'SYN_SENT': 0,
            'SYN_RECV': 0,
            'FIN_WAIT1': 0,
            'FIN_WAIT2': 0,
            'TIME_WAIT': 0,
            'CLOSE': 0,
            'CLOSE_WAIT': 0,
            'LAST_ACK': 0,
            'LISTEN': 0,
            'CLOSING': 0
        }
        
        # State codes from /proc/net/tcp
        state_map = {
            '01': 'ESTABLISHED',
            '02': 'SYN_SENT',
            '03': 'SYN_RECV',
            '04': 'FIN_WAIT1',
            '05': 'FIN_WAIT2',
            '06': 'TIME_WAIT',
            '07': 'CLOSE',
            '08': 'CLOSE_WAIT',
            '09': 'LAST_ACK',
            '0A': 'LISTEN',
            '0B': 'CLOSING'
        }
        
        # Read TCP connections
        for line in self.read_file('/proc/net/tcp').split('\n')[1:]:
            if not line:
                continue
            parts = line.split()
            if len(parts) < 4:
                continue
            
            state_hex = parts[3]
            state = state_map.get(state_hex, 'UNKNOWN')
            if state in states:
                states[state] += 1
        
        # Also check IPv6
        for line in self.read_file('/proc/net/tcp6').split('\n')[1:]:
            if not line:
                continue
            parts = line.split()
            if len(parts) < 4:
                continue
            
            state_hex = parts[3]
            state = state_map.get(state_hex, 'UNKNOWN')
            if state in states:
                states[state] += 1
        
        total_connections = sum(states.values())
        
        return {
            'total_connections': total_connections,
            'established': states['ESTABLISHED'],
            'syn_recv': states['SYN_RECV'],
            'time_wait': states['TIME_WAIT'],
            'close_wait': states['CLOSE_WAIT']
        }
    
    def collect_metrics(self):
        """Collect all metrics"""
        metrics = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Collect all stats
        metrics['cpu_usage_pct'] = self.get_cpu_stats()
        metrics.update(self.get_memory_stats())
        metrics.update(self.get_disk_stats())
        metrics.update(self.get_disk_usage())
        metrics.update(self.get_network_stats())
        metrics.update(self.get_connection_stats())
        
        return metrics
    
    def run(self, output_file):
        """Main monitoring loop"""
        print(f"[+] Starting system monitor (interval: {self.interval}s)")
        print(f"[+] Output file: {output_file}")
        print("[+] Press Ctrl+C to stop\n")
        
        # Initialize - first collection for baseline
        self.collect_metrics()
        time.sleep(self.interval)
        
        # Get fieldnames from first real collection
        first_metrics = self.collect_metrics()
        fieldnames = list(first_metrics.keys())
        
        with open(output_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerow(first_metrics)
            f.flush()
            
            count = 1
            print(f"[{count}] {first_metrics['timestamp']} | CPU: {first_metrics['cpu_usage_pct']}% | "
                  f"Mem: {first_metrics['mem_usage_pct']}% | "
                  f"Connections: {first_metrics['total_connections']}")
            
            while self.running:
                time.sleep(self.interval)
                
                metrics = self.collect_metrics()
                writer.writerow(metrics)
                f.flush()  # Ensure data is written immediately
                
                count += 1
                print(f"[{count}] {metrics['timestamp']} | CPU: {metrics['cpu_usage_pct']}% | "
                      f"Mem: {metrics['mem_usage_pct']}% | "
                      f"Connections: {metrics['total_connections']}")
        
        print(f"\n[+] Monitoring stopped. Collected {count} samples.")
        print(f"[+] Data saved to: {output_file}")

def main():
    parser = argparse.ArgumentParser(
        description='Lightweight system monitor for DDoS detection'
    )
    parser.add_argument(
        '--interval', '-i',
        type=float,
        default=1.0,
        help='Monitoring interval in seconds (default: 1.0)'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='system_metrics.csv',
        help='Output CSV file (default: system_metrics.csv)'
    )
    
    args = parser.parse_args()
    
    if args.interval < 0.1:
        print("[!] Warning: Interval too small, setting to 0.1s")
        args.interval = 0.1
    
    monitor = SystemMonitor(interval=args.interval)
    monitor.run(args.output)

if __name__ == '__main__':
    main()