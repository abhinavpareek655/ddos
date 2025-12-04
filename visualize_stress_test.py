#!/usr/bin/env python3
"""
Visualize Stress Test Results
Creates comprehensive graphs from stress test CSV data

Usage:
    python3 visualize_stress_test.py results.csv
    python3 visualize_stress_test.py results.csv --output test_graphs
"""

import sys
import csv
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
from collections import Counter
import argparse

def load_results(csv_file):
    """Load stress test results from CSV"""
    data = {
        'request_ids': [],
        'success': [],
        'status_codes': [],
        'response_times': [],
        'timestamps': [],
        'response_sizes': [],
        'errors': []
    }
    
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                data['request_ids'].append(int(row['Request_ID']))
                data['success'].append(row['Success'] == 'True')
                data['status_codes'].append(int(row['Status_Code']))
                data['response_times'].append(float(row['Response_Time_ms']))
                data['timestamps'].append(float(row['Timestamp']))
                data['response_sizes'].append(int(row['Response_Size_bytes']))
                data['errors'].append(row['Error'])
            except Exception as e:
                print(f"Warning: Skipping row due to error: {e}")
                continue
    
    return data

def plot_response_times_over_time(data, output_prefix):
    """Plot response times over the test duration"""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 10))
    fig.suptitle('Response Time Analysis', fontsize=16, fontweight='bold')
    
    # Calculate relative time from start
    start_time = min(data['timestamps'])
    relative_times = [(t - start_time) for t in data['timestamps']]
    
    # Plot 1: Response times scatter
    successful = [i for i, s in enumerate(data['success']) if s]
    failed = [i for i, s in enumerate(data['success']) if not s]
    
    if successful:
        ax1.scatter([relative_times[i] for i in successful],
                   [data['response_times'][i] for i in successful],
                   c='#2ecc71', alpha=0.3, s=1, label='Successful')
    
    if failed:
        ax1.scatter([relative_times[i] for i in failed],
                   [data['response_times'][i] for i in failed],
                   c='#e74c3c', alpha=0.6, s=5, label='Failed')
    
    ax1.set_xlabel('Time (seconds)', fontsize=12)
    ax1.set_ylabel('Response Time (ms)', fontsize=12)
    ax1.set_title('Response Time Distribution Over Test Duration', fontweight='bold')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: Moving average (smoothed)
    window_size = max(len(data['response_times']) // 100, 10)
    moving_avg = np.convolve(data['response_times'], 
                            np.ones(window_size)/window_size, 
                            mode='valid')
    moving_avg_times = relative_times[window_size-1:]
    
    ax2.plot(moving_avg_times, moving_avg, color='#3498db', linewidth=2, 
            label=f'Moving Average (window={window_size})')
    ax2.fill_between(moving_avg_times, moving_avg, alpha=0.3, color='#3498db')
    ax2.set_xlabel('Time (seconds)', fontsize=12)
    ax2.set_ylabel('Response Time (ms)', fontsize=12)
    ax2.set_title('Response Time Trend (Smoothed)', fontweight='bold')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(f'{output_prefix}_response_times.png', dpi=300, bbox_inches='tight')
    print(f"[+] Saved: {output_prefix}_response_times.png")
    plt.close()

def plot_throughput(data, output_prefix):
    """Plot requests per second over time"""
    fig, ax = plt.subplots(figsize=(16, 6))
    fig.suptitle('Throughput Analysis', fontsize=16, fontweight='bold')
    
    # Calculate RPS in time buckets
    start_time = min(data['timestamps'])
    duration = max(data['timestamps']) - start_time
    num_buckets = max(int(duration), 10)
    bucket_size = duration / num_buckets
    
    buckets = [[] for _ in range(num_buckets)]
    for i, ts in enumerate(data['timestamps']):
        bucket_idx = min(int((ts - start_time) / bucket_size), num_buckets - 1)
        buckets[bucket_idx].append(i)
    
    bucket_times = [(i * bucket_size) + (bucket_size / 2) for i in range(num_buckets)]
    rps_values = [len(bucket) / bucket_size if bucket_size > 0 else 0 for bucket in buckets]
    success_rps = []
    
    for bucket in buckets:
        successful = sum(1 for idx in bucket if data['success'][idx])
        success_rps.append(successful / bucket_size if bucket_size > 0 else 0)
    
    # Plot
    ax.plot(bucket_times, rps_values, color='#3498db', linewidth=2, 
           label='Total RPS', marker='o', markersize=4)
    ax.plot(bucket_times, success_rps, color='#2ecc71', linewidth=2, 
           label='Successful RPS', marker='s', markersize=4)
    ax.fill_between(bucket_times, success_rps, alpha=0.3, color='#2ecc71')
    
    ax.set_xlabel('Time (seconds)', fontsize=12)
    ax.set_ylabel('Requests per Second', fontsize=12)
    ax.set_title('Throughput Over Time', fontweight='bold')
    ax.legend(loc='best', fontsize=10)
    ax.grid(True, alpha=0.3)
    
    # Add average line
    avg_rps = np.mean(success_rps)
    ax.axhline(y=avg_rps, color='#e74c3c', linestyle='--', linewidth=2, 
              label=f'Average: {avg_rps:.1f} RPS')
    ax.legend(loc='best', fontsize=10)
    
    plt.tight_layout()
    plt.savefig(f'{output_prefix}_throughput.png', dpi=300, bbox_inches='tight')
    print(f"[+] Saved: {output_prefix}_throughput.png")
    plt.close()

def plot_latency_distribution(data, output_prefix):
    """Plot latency histogram and percentiles"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    fig.suptitle('Latency Distribution', fontsize=16, fontweight='bold')
    
    successful_times = [data['response_times'][i] for i in range(len(data['response_times'])) 
                       if data['success'][i]]
    
    if not successful_times:
        print("[!] No successful requests to plot")
        return
    
    # Histogram
    ax1.hist(successful_times, bins=50, color='#3498db', alpha=0.7, edgecolor='black')
    ax1.set_xlabel('Response Time (ms)', fontsize=12)
    ax1.set_ylabel('Frequency', fontsize=12)
    ax1.set_title('Response Time Histogram', fontweight='bold')
    ax1.grid(True, alpha=0.3, axis='y')
    
    # Add percentile lines
    percentiles = [50, 95, 99]
    colors = ['#2ecc71', '#f39c12', '#e74c3c']
    
    for p, color in zip(percentiles, colors):
        value = np.percentile(successful_times, p)
        ax1.axvline(x=value, color=color, linestyle='--', linewidth=2, 
                   label=f'p{p}: {value:.1f}ms')
    ax1.legend()
    
    # Box plot
    bp = ax2.boxplot(successful_times, vert=True, patch_artist=True,
                     showmeans=True, meanline=True)
    bp['boxes'][0].set_facecolor('#3498db')
    bp['boxes'][0].set_alpha(0.7)
    bp['medians'][0].set_color('#e74c3c')
    bp['medians'][0].set_linewidth(2)
    bp['means'][0].set_color('#2ecc71')
    bp['means'][0].set_linewidth(2)
    
    ax2.set_ylabel('Response Time (ms)', fontsize=12)
    ax2.set_title('Response Time Box Plot', fontweight='bold')
    ax2.grid(True, alpha=0.3, axis='y')
    
    # Add statistics text
    stats_text = f"Mean: {np.mean(successful_times):.1f}ms\n"
    stats_text += f"Median: {np.median(successful_times):.1f}ms\n"
    stats_text += f"Std Dev: {np.std(successful_times):.1f}ms"
    ax2.text(1.3, np.median(successful_times), stats_text,
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5),
            fontsize=10)
    
    plt.tight_layout()
    plt.savefig(f'{output_prefix}_latency_distribution.png', dpi=300, bbox_inches='tight')
    print(f"[+] Saved: {output_prefix}_latency_distribution.png")
    plt.close()

def plot_status_codes(data, output_prefix):
    """Plot status code distribution"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    fig.suptitle('Status Code Analysis', fontsize=16, fontweight='bold')
    
    # Count status codes
    status_counter = Counter(data['status_codes'])
    codes = sorted(status_counter.keys())
    counts = [status_counter[code] for code in codes]
    
    # Color mapping
    colors_map = {
        0: '#95a5a6',    # Connection failed
        200: '#2ecc71',  # Success
        500: '#e74c3c',  # Server error
        502: '#e67e22',  # Bad gateway
        503: '#e74c3c',  # Service unavailable
        504: '#c0392b',  # Gateway timeout
    }
    colors = [colors_map.get(code, '#3498db') for code in codes]
    
    # Bar chart
    bars = ax1.bar(range(len(codes)), counts, color=colors, alpha=0.7, edgecolor='black')
    ax1.set_xticks(range(len(codes)))
    ax1.set_xticklabels([str(c) for c in codes], rotation=45)
    ax1.set_xlabel('Status Code', fontsize=12)
    ax1.set_ylabel('Count', fontsize=12)
    ax1.set_title('Status Code Distribution', fontweight='bold')
    ax1.grid(True, alpha=0.3, axis='y')
    
    # Add percentage labels on bars
    total = sum(counts)
    for bar, count in zip(bars, counts):
        height = bar.get_height()
        percentage = (count / total) * 100
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{percentage:.1f}%',
                ha='center', va='bottom', fontsize=9)
    
    # Pie chart
    success_count = sum(1 for s in data['success'] if s)
    failed_count = len(data['success']) - success_count
    
    sizes = [success_count, failed_count]
    labels = ['Successful', 'Failed']
    colors_pie = ['#2ecc71', '#e74c3c']
    explode = (0.05, 0.05)
    
    ax2.pie(sizes, explode=explode, labels=labels, colors=colors_pie,
           autopct='%1.1f%%', shadow=True, startangle=90)
    ax2.set_title('Success vs Failed Requests', fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(f'{output_prefix}_status_codes.png', dpi=300, bbox_inches='tight')
    print(f"[+] Saved: {output_prefix}_status_codes.png")
    plt.close()

def plot_errors(data, output_prefix):
    """Plot error distribution if any errors exist"""
    errors = [e for e in data['errors'] if e]
    
    if not errors:
        print("[*] No errors to plot")
        return
    
    fig, ax = plt.subplots(figsize=(14, 8))
    fig.suptitle('Error Analysis', fontsize=16, fontweight='bold')
    
    error_counter = Counter(errors)
    error_types = list(error_counter.keys())
    error_counts = list(error_counter.values())
    
    # Sort by count
    sorted_pairs = sorted(zip(error_types, error_counts), key=lambda x: x[1], reverse=True)
    error_types, error_counts = zip(*sorted_pairs) if sorted_pairs else ([], [])
    
    # Horizontal bar chart
    y_pos = range(len(error_types))
    bars = ax.barh(y_pos, error_counts, color='#e74c3c', alpha=0.7, edgecolor='black')
    
    ax.set_yticks(y_pos)
    ax.set_yticklabels(error_types, fontsize=9)
    ax.set_xlabel('Count', fontsize=12)
    ax.set_title('Error Distribution', fontweight='bold')
    ax.grid(True, alpha=0.3, axis='x')
    
    # Add count labels
    for i, (bar, count) in enumerate(zip(bars, error_counts)):
        width = bar.get_width()
        ax.text(width, bar.get_y() + bar.get_height()/2.,
               f' {count}',
               ha='left', va='center', fontsize=9)
    
    plt.tight_layout()
    plt.savefig(f'{output_prefix}_errors.png', dpi=300, bbox_inches='tight')
    print(f"[+] Saved: {output_prefix}_errors.png")
    plt.close()

def plot_dashboard(data, output_prefix):
    """Create all-in-one dashboard"""
    fig = plt.figure(figsize=(20, 12))
    fig.suptitle('Stress Test Dashboard', fontsize=18, fontweight='bold')
    
    gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)
    
    # Calculate stats
    successful_times = [data['response_times'][i] for i in range(len(data['response_times'])) 
                       if data['success'][i]]
    
    start_time = min(data['timestamps'])
    relative_times = [(t - start_time) for t in data['timestamps']]
    
    # 1. Response times over time
    ax1 = fig.add_subplot(gs[0, :])
    successful_idx = [i for i, s in enumerate(data['success']) if s]
    if successful_idx:
        ax1.scatter([relative_times[i] for i in successful_idx],
                   [data['response_times'][i] for i in successful_idx],
                   c='#2ecc71', alpha=0.2, s=1)
    ax1.set_ylabel('Response Time (ms)')
    ax1.set_xlabel('Time (s)')
    ax1.set_title('Response Times Over Test Duration')
    ax1.grid(True, alpha=0.3)
    
    # 2. Latency histogram
    ax2 = fig.add_subplot(gs[1, 0])
    if successful_times:
        ax2.hist(successful_times, bins=30, color='#3498db', alpha=0.7, edgecolor='black')
    ax2.set_xlabel('Response Time (ms)')
    ax2.set_ylabel('Frequency')
    ax2.set_title('Latency Distribution')
    ax2.grid(True, alpha=0.3, axis='y')
    
    # 3. Status codes
    ax3 = fig.add_subplot(gs[1, 1])
    status_counter = Counter(data['status_codes'])
    codes = list(status_counter.keys())
    counts = list(status_counter.values())
    ax3.bar(range(len(codes)), counts, color='#2ecc71', alpha=0.7)
    ax3.set_xticks(range(len(codes)))
    ax3.set_xticklabels([str(c) for c in codes])
    ax3.set_ylabel('Count')
    ax3.set_title('Status Codes')
    ax3.grid(True, alpha=0.3, axis='y')
    
    # 4. Success vs Failure
    ax4 = fig.add_subplot(gs[1, 2])
    success_count = sum(data['success'])
    failed_count = len(data['success']) - success_count
    ax4.pie([success_count, failed_count], labels=['Success', 'Failed'],
           colors=['#2ecc71', '#e74c3c'], autopct='%1.1f%%', startangle=90)
    ax4.set_title('Success Rate')
    
    # 5. Stats summary text
    ax5 = fig.add_subplot(gs[2, :])
    ax5.axis('off')
    
    if successful_times:
        stats_text = f"""
    SUMMARY STATISTICS
    {'='*60}
    Total Requests:        {len(data['response_times']):,}
    Successful:            {success_count:,} ({success_count/len(data['response_times'])*100:.1f}%)
    Failed:                {failed_count:,} ({failed_count/len(data['response_times'])*100:.1f}%)
    
    Response Time (ms):
        Average:           {np.mean(successful_times):.2f}
        Median:            {np.median(successful_times):.2f}
        Min:               {np.min(successful_times):.2f}
        Max:               {np.max(successful_times):.2f}
        95th Percentile:   {np.percentile(successful_times, 95):.2f}
        99th Percentile:   {np.percentile(successful_times, 99):.2f}
    
    Test Duration:         {max(relative_times):.2f} seconds
    Requests per Second:   {len(data['response_times']) / max(relative_times):.2f}
        """
    else:
        stats_text = "No successful requests to analyze"
    
    ax5.text(0.1, 0.5, stats_text, fontsize=11, family='monospace',
            verticalalignment='center')
    
    plt.savefig(f'{output_prefix}_dashboard.png', dpi=300, bbox_inches='tight')
    print(f"[+] Saved: {output_prefix}_dashboard.png")
    plt.close()

def main():
    parser = argparse.ArgumentParser(description='Visualize stress test results')
    parser.add_argument('csv_file', help='Input CSV file from stress_test.py')
    parser.add_argument('--output', '-o', default='stress_test',
                       help='Output prefix for graph files (default: stress_test)')
    
    args = parser.parse_args()
    
    print(f"[+] Loading data from: {args.csv_file}")
    data = load_results(args.csv_file)
    
    if not data['request_ids']:
        print("[!] Error: No valid data found in CSV file")
        return
    
    print(f"[+] Loaded {len(data['request_ids'])} requests")
    print(f"[+] Generating visualizations...")
    print()
    
    # Generate all plots
    plot_response_times_over_time(data, args.output)
    plot_throughput(data, args.output)
    plot_latency_distribution(data, args.output)
    plot_status_codes(data, args.output)
    plot_errors(data, args.output)
    plot_dashboard(data, args.output)
    
    print()
    print("[+] Done! Generated visualizations:")
    print(f"    1. {args.output}_response_times.png")
    print(f"    2. {args.output}_throughput.png")
    print(f"    3. {args.output}_latency_distribution.png")
    print(f"    4. {args.output}_status_codes.png")
    print(f"    5. {args.output}_errors.png (if errors exist)")
    print(f"    6. {args.output}_dashboard.png")

if __name__ == '__main__':
    main()