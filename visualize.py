#!/usr/bin/env python3
"""
Visualize System Metrics from CSV
Usage: python3 visualize.py system_metrics.csv
"""

import sys
import csv
import matplotlib.pyplot as plt
from datetime import datetime
import argparse

def load_data(csv_file):
    """Load metrics from CSV file"""
    data = {
        'timestamps': [],
        'cpu_usage_pct': [],
        'mem_usage_pct': [],
        'mem_used_mb': [],
        'buffers_mb': [],
        'cached_mb': [],
        'disk_read_mb_s': [],
        'disk_write_mb_s': [],
        'disk_usage_pct': [],
        'net_rx_mb_s': [],
        'net_tx_mb_s': [],
        'total_connections': [],
        'established': [],
        'syn_recv': [],
        'time_wait': [],
        'close_wait': []
    }
    
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                data['timestamps'].append(datetime.strptime(row['timestamp'], '%Y-%m-%d %H:%M:%S'))
                
                for key in data.keys():
                    if key != 'timestamps' and key in row:
                        data[key].append(float(row[key]))
            except Exception as e:
                print(f"Warning: Skipping row due to error: {e}")
                continue
    
    return data

def plot_metrics(data, output_prefix='metrics'):
    """Create comprehensive plots"""
    
    # Set style
    plt.style.use('seaborn-v0_8-darkgrid')
    
    # Figure 1: CPU and Memory
    fig1, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
    fig1.suptitle('CPU and Memory Usage', fontsize=16, fontweight='bold')
    
    # CPU
    ax1.plot(data['timestamps'], data['cpu_usage_pct'], 
             label='CPU Usage', color='#e74c3c', linewidth=2)
    ax1.set_ylabel('CPU Usage (%)', fontsize=12)
    ax1.set_xlabel('Time', fontsize=12)
    ax1.legend(loc='upper right')
    ax1.grid(True, alpha=0.3)
    ax1.set_ylim([0, 105])
    
    # Memory
    ax2.plot(data['timestamps'], data['mem_usage_pct'], 
             label='Memory Usage', color='#3498db', linewidth=2)
    ax2.plot(data['timestamps'], data['buffers_mb'], 
             label='Buffers (MB)', color='#2ecc71', linewidth=1.5, alpha=0.7)
    ax2.plot(data['timestamps'], data['cached_mb'], 
             label='Cached (MB)', color='#f39c12', linewidth=1.5, alpha=0.7)
    ax2.set_ylabel('Memory / Buffers (MB)', fontsize=12)
    ax2.set_xlabel('Time', fontsize=12)
    ax2.legend(loc='upper right')
    ax2.grid(True, alpha=0.3)
    
    ax2_twin = ax2.twinx()
    ax2_twin.plot(data['timestamps'], data['mem_usage_pct'], 
                  color='#3498db', linewidth=2, alpha=0)
    ax2_twin.set_ylabel('Memory Usage (%)', fontsize=12)
    ax2_twin.set_ylim([0, 105])
    
    plt.tight_layout()
    plt.savefig(f'{output_prefix}_cpu_memory.png', dpi=300, bbox_inches='tight')
    print(f"[+] Saved: {output_prefix}_cpu_memory.png")
    
    # Figure 2: Disk I/O
    fig2, (ax3, ax4) = plt.subplots(2, 1, figsize=(14, 10))
    fig2.suptitle('Disk Activity', fontsize=16, fontweight='bold')
    
    # Disk I/O
    ax3.plot(data['timestamps'], data['disk_read_mb_s'], 
             label='Read (MB/s)', color='#9b59b6', linewidth=2)
    ax3.plot(data['timestamps'], data['disk_write_mb_s'], 
             label='Write (MB/s)', color='#e67e22', linewidth=2)
    ax3.set_ylabel('Disk I/O (MB/s)', fontsize=12)
    ax3.set_xlabel('Time', fontsize=12)
    ax3.legend(loc='upper right')
    ax3.grid(True, alpha=0.3)
    
    # Disk Usage
    ax4.plot(data['timestamps'], data['disk_usage_pct'], 
             label='Disk Usage', color='#34495e', linewidth=2)
    ax4.set_ylabel('Disk Usage (%)', fontsize=12)
    ax4.set_xlabel('Time', fontsize=12)
    ax4.legend(loc='upper right')
    ax4.grid(True, alpha=0.3)
    ax4.set_ylim([0, 105])
    
    plt.tight_layout()
    plt.savefig(f'{output_prefix}_disk.png', dpi=300, bbox_inches='tight')
    print(f"[+] Saved: {output_prefix}_disk.png")
    
    # Figure 3: Network
    fig3, ax5 = plt.subplots(figsize=(14, 6))
    fig3.suptitle('Network Traffic', fontsize=16, fontweight='bold')
    
    ax5.plot(data['timestamps'], data['net_rx_mb_s'], 
             label='RX (MB/s)', color='#16a085', linewidth=2)
    ax5.plot(data['timestamps'], data['net_tx_mb_s'], 
             label='TX (MB/s)', color='#c0392b', linewidth=2)
    ax5.set_ylabel('Network Traffic (MB/s)', fontsize=12)
    ax5.set_xlabel('Time', fontsize=12)
    ax5.legend(loc='upper right')
    ax5.grid(True, alpha=0.3)
    ax5.fill_between(data['timestamps'], data['net_rx_mb_s'], alpha=0.3, color='#16a085')
    ax5.fill_between(data['timestamps'], data['net_tx_mb_s'], alpha=0.3, color='#c0392b')
    
    plt.tight_layout()
    plt.savefig(f'{output_prefix}_network.png', dpi=300, bbox_inches='tight')
    print(f"[+] Saved: {output_prefix}_network.png")
    
    # Figure 4: Connections (CRITICAL for DDoS detection)
    fig4, (ax6, ax7) = plt.subplots(2, 1, figsize=(14, 10))
    fig4.suptitle('Network Connections - DDoS Indicators', fontsize=16, fontweight='bold')
    
    # Total connections
    ax6.plot(data['timestamps'], data['total_connections'], 
             label='Total Connections', color='#e74c3c', linewidth=2.5)
    ax6.set_ylabel('Total Connections', fontsize=12)
    ax6.set_xlabel('Time', fontsize=12)
    ax6.legend(loc='upper right')
    ax6.grid(True, alpha=0.3)
    ax6.fill_between(data['timestamps'], data['total_connections'], alpha=0.2, color='#e74c3c')
    
    # Connection states
    ax7.plot(data['timestamps'], data['established'], 
             label='ESTABLISHED', color='#2ecc71', linewidth=2)
    ax7.plot(data['timestamps'], data['syn_recv'], 
             label='SYN_RECV (SYN Flood)', color='#e74c3c', linewidth=2)
    ax7.plot(data['timestamps'], data['time_wait'], 
             label='TIME_WAIT', color='#f39c12', linewidth=2)
    ax7.plot(data['timestamps'], data['close_wait'], 
             label='CLOSE_WAIT', color='#9b59b6', linewidth=2)
    ax7.set_ylabel('Connection Count', fontsize=12)
    ax7.set_xlabel('Time', fontsize=12)
    ax7.legend(loc='upper right')
    ax7.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(f'{output_prefix}_connections.png', dpi=300, bbox_inches='tight')
    print(f"[+] Saved: {output_prefix}_connections.png")
    
    # Figure 5: All-in-One Dashboard
    fig5 = plt.figure(figsize=(18, 12))
    fig5.suptitle('System Monitoring Dashboard - DDoS Detection', 
                  fontsize=18, fontweight='bold')
    
    # Create grid
    gs = fig5.add_gridspec(3, 2, hspace=0.3, wspace=0.3)
    
    # CPU
    ax_cpu = fig5.add_subplot(gs[0, 0])
    ax_cpu.plot(data['timestamps'], data['cpu_usage_pct'], color='#e74c3c', linewidth=2)
    ax_cpu.set_title('CPU Usage', fontweight='bold')
    ax_cpu.set_ylabel('Usage (%)')
    ax_cpu.grid(True, alpha=0.3)
    ax_cpu.set_ylim([0, 105])
    
    # Memory
    ax_mem = fig5.add_subplot(gs[0, 1])
    ax_mem.plot(data['timestamps'], data['mem_usage_pct'], color='#3498db', linewidth=2)
    ax_mem.set_title('Memory Usage', fontweight='bold')
    ax_mem.set_ylabel('Usage (%)')
    ax_mem.grid(True, alpha=0.3)
    ax_mem.set_ylim([0, 105])
    
    # Network
    ax_net = fig5.add_subplot(gs[1, 0])
    ax_net.plot(data['timestamps'], data['net_rx_mb_s'], label='RX', color='#16a085', linewidth=2)
    ax_net.plot(data['timestamps'], data['net_tx_mb_s'], label='TX', color='#c0392b', linewidth=2)
    ax_net.set_title('Network Traffic', fontweight='bold')
    ax_net.set_ylabel('Traffic (MB/s)')
    ax_net.legend()
    ax_net.grid(True, alpha=0.3)
    
    # Disk I/O
    ax_disk = fig5.add_subplot(gs[1, 1])
    ax_disk.plot(data['timestamps'], data['disk_read_mb_s'], label='Read', color='#9b59b6', linewidth=2)
    ax_disk.plot(data['timestamps'], data['disk_write_mb_s'], label='Write', color='#e67e22', linewidth=2)
    ax_disk.set_title('Disk I/O', fontweight='bold')
    ax_disk.set_ylabel('I/O (MB/s)')
    ax_disk.legend()
    ax_disk.grid(True, alpha=0.3)
    
    # Total Connections
    ax_conn = fig5.add_subplot(gs[2, 0])
    ax_conn.plot(data['timestamps'], data['total_connections'], color='#e74c3c', linewidth=2.5)
    ax_conn.set_title('Total Connections (DDoS Indicator)', fontweight='bold')
    ax_conn.set_ylabel('Connections')
    ax_conn.grid(True, alpha=0.3)
    ax_conn.fill_between(data['timestamps'], data['total_connections'], alpha=0.2, color='#e74c3c')
    
    # Connection States
    ax_states = fig5.add_subplot(gs[2, 1])
    ax_states.plot(data['timestamps'], data['syn_recv'], label='SYN_RECV', color='#e74c3c', linewidth=2)
    ax_states.plot(data['timestamps'], data['established'], label='ESTABLISHED', color='#2ecc71', linewidth=2)
    ax_states.set_title('Connection States', fontweight='bold')
    ax_states.set_ylabel('Count')
    ax_states.legend()
    ax_states.grid(True, alpha=0.3)
    
    plt.savefig(f'{output_prefix}_dashboard.png', dpi=300, bbox_inches='tight')
    print(f"[+] Saved: {output_prefix}_dashboard.png")
    
    plt.close('all')

def print_statistics(data):
    """Print summary statistics"""
    print("\n" + "="*60)
    print("SYSTEM MONITORING STATISTICS")
    print("="*60)
    
    if not data['timestamps']:
        print("No data available")
        return
    
    duration = (data['timestamps'][-1] - data['timestamps'][0]).total_seconds()
    samples = len(data['timestamps'])
    
    print(f"\nMonitoring Period:")
    print(f"  Start: {data['timestamps'][0]}")
    print(f"  End:   {data['timestamps'][-1]}")
    print(f"  Duration: {duration:.1f} seconds ({samples} samples)")
    
    print(f"\nCPU Usage:")
    print(f"  Average: {sum(data['cpu_usage_pct'])/len(data['cpu_usage_pct']):.2f}%")
    print(f"  Peak:    {max(data['cpu_usage_pct']):.2f}%")
    
    print(f"\nMemory Usage:")
    print(f"  Average: {sum(data['mem_usage_pct'])/len(data['mem_usage_pct']):.2f}%")
    print(f"  Peak:    {max(data['mem_usage_pct']):.2f}%")
    
    print(f"\nNetwork Traffic:")
    print(f"  Avg RX: {sum(data['net_rx_mb_s'])/len(data['net_rx_mb_s']):.2f} MB/s")
    print(f"  Avg TX: {sum(data['net_tx_mb_s'])/len(data['net_tx_mb_s']):.2f} MB/s")
    print(f"  Peak RX: {max(data['net_rx_mb_s']):.2f} MB/s")
    print(f"  Peak TX: {max(data['net_tx_mb_s']):.2f} MB/s")
    
    print(f"\nConnections (DDoS Indicators):")
    print(f"  Avg Total:    {sum(data['total_connections'])/len(data['total_connections']):.0f}")
    print(f"  Peak Total:   {max(data['total_connections'])}")
    print(f"  Peak SYN_RECV: {max(data['syn_recv'])} (High = possible SYN flood)")
    print(f"  Avg SYN_RECV:  {sum(data['syn_recv'])/len(data['syn_recv']):.1f}")
    
    print("\n" + "="*60)

def main():
    parser = argparse.ArgumentParser(
        description='Visualize system metrics from CSV'
    )
    parser.add_argument(
        'csv_file',
        help='Input CSV file from monitor.py'
    )
    parser.add_argument(
        '--output', '-o',
        default='metrics',
        help='Output prefix for graph files (default: metrics)'
    )
    parser.add_argument(
        '--no-stats',
        action='store_true',
        help='Skip printing statistics'
    )
    
    args = parser.parse_args()
    
    print(f"[+] Loading data from: {args.csv_file}")
    data = load_data(args.csv_file)
    
    if not data['timestamps']:
        print("[!] Error: No valid data found in CSV file")
        return
    
    print(f"[+] Loaded {len(data['timestamps'])} samples")
    
    if not args.no_stats:
        print_statistics(data)
    
    print(f"\n[+] Generating graphs...")
    plot_metrics(data, args.output)
    
    print(f"\n[+] Done! Generated 5 visualizations:")
    print(f"    1. {args.output}_cpu_memory.png")
    print(f"    2. {args.output}_disk.png")
    print(f"    3. {args.output}_network.png")
    print(f"    4. {args.output}_connections.png")
    print(f"    5. {args.output}_dashboard.png (All-in-one)")

if __name__ == '__main__':
    main()