#!/usr/bin/env python3
"""
Production-grade launcher with Gunicorn + Gevent
Maximum performance configuration

Usage:
    python3 run_server.py [--workers auto] [--port 5000]
"""

import os
import sys
import multiprocessing
import subprocess
import argparse

def get_optimal_workers():
    """Calculate optimal number of workers"""
    cpu_count = multiprocessing.cpu_count()
    # Formula: (2 x CPU cores) + 1 for CPU-bound tasks
    # Use more for I/O bound: 4-8 x CPU cores
    return (cpu_count * 4) + 1

def main():
    parser = argparse.ArgumentParser(description='Launch high-performance Flask server')
    parser.add_argument('--workers', type=str, default='auto',
                       help='Number of workers (default: auto = 4*CPU+1)')
    parser.add_argument('--port', type=int, default=5000,
                       help='Port to listen on (default: 5000)')
    parser.add_argument('--host', type=str, default='0.0.0.0',
                       help='Host to bind to (default: 0.0.0.0)')
    parser.add_argument('--threads', type=int, default=1000,
                       help='Threads per worker (default: 1000)')
    parser.add_argument('--mode', type=str, default='gevent',
                       choices=['gevent', 'sync', 'gthread'],
                       help='Worker mode: gevent (best), sync, or gthread')
    parser.add_argument('--backlog', type=int, default=65535,
                       help='Maximum pending connections (default: 65535)')
    
    args = parser.parse_args()
    
    # Calculate workers
    if args.workers == 'auto':
        workers = get_optimal_workers()
    else:
        workers = int(args.workers)
    
    print("=" * 60)
    print("HIGH-PERFORMANCE FLASK SERVER")
    print("=" * 60)
    print(f"Workers:          {workers}")
    print(f"Threads/Worker:   {args.threads}")
    print(f"Worker Mode:      {args.mode}")
    print(f"Listen:           {args.host}:{args.port}")
    print(f"Backlog:          {args.backlog}")
    print(f"CPU Cores:        {multiprocessing.cpu_count()}")
    print("=" * 60)
    print()
    
    # Build gunicorn command
    cmd = [
        'gunicorn',
        'server:app',
        '--workers', str(workers),
        '--worker-class', args.mode,
        '--worker-connections', str(args.threads),
        '--bind', f'{args.host}:{args.port}',
        '--backlog', str(args.backlog),
        '--timeout', '300',
        '--keep-alive', '5',
        '--max-requests', '0',  # Never restart workers
        '--max-requests-jitter', '0',
        '--preload',  # Preload app for faster worker spawning
        '--log-level', 'warning',
        '--access-logfile', '-',
        '--error-logfile', '-',
        '--enable-stdio-inheritance',
    ]
    
    # Additional optimizations for gevent
    if args.mode == 'gevent':
        cmd.extend([
            '--worker-tmp-dir', '/dev/shm',  # Use RAM for worker tmp
        ])
    
    print(f"[+] Starting Gunicorn...")
    print(f"[+] Command: {' '.join(cmd)}")
    print()
    print("[*] Server is running. Press Ctrl+C to stop.")
    print()
    
    try:
        # Run gunicorn
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n[!] Shutting down...")
        sys.exit(0)
    except subprocess.CalledProcessError as e:
        print(f"\n[!] Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()