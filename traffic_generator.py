#!/usr/bin/env python3
"""
Traffic Generator from Real Data
=================================
Generates 5G slice traffic using real data files:
- URLLC: urllc_traffic.csv (low latency traffic)
- eMBB: Demo.mp4 (video streaming traffic)
- mMTC: mmtc_traffic.csv (IoT sensor traffic)

Usage: sudo python3 traffic_generator.py [--slice urllc|embb|mmtc|all]
"""

import csv
import time
import subprocess
import argparse
import os
import sys
import random
from datetime import datetime

# Colors for terminal output
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
CYAN = '\033[0;36m'
BOLD = '\033[1m'
NC = '\033[0m'

# Slice configurations
SLICE_CONFIG = {
    'urllc': {
        'file': 'data-input/urllc_traffic.csv',
        'host': 'urllc_h1',
        'port': 5001,
        'server_ip': '10.0.0.100',
        'color': CYAN,
        'description': 'Low-latency critical traffic'
    },
    'embb': {
        'file': 'data-input/Demo.mp4',
        'host': 'embb_h1',
        'port': 5002,
        'server_ip': '10.0.0.100',
        'color': YELLOW,
        'description': 'Video streaming traffic'
    },
    'mmtc': {
        'file': 'data-input/mmtc_traffic.csv',
        'host': 'mmtc_h1',
        'port': 5003,
        'server_ip': '10.0.0.100',
        'color': GREEN,
        'description': 'IoT sensor traffic'
    }
}


def load_csv_data(filepath):
    """Load traffic data from CSV file."""
    data = []
    try:
        with open(filepath, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                data.append({
                    'device_id': row.get('device_id', 'unknown'),
                    'app': row.get('app', 'unknown'),
                    'packet_size': int(row.get('packet_size_bytes', 100)),
                    'throughput_kbps': float(row.get('throughput_kbps', 100)),
                    'latency_ms': float(row.get('latency_ms', 10)),
                    'jitter_ms': float(row.get('jitter_ms', 1)),
                    'loss_percent': float(row.get('loss_percent', 0))
                })
        print(f"{GREEN}[✓] Loaded {len(data)} records from {filepath}{NC}")
    except FileNotFoundError:
        print(f"{RED}[✗] File not found: {filepath}{NC}")
    except Exception as e:
        print(f"{RED}[✗] Error loading {filepath}: {e}{NC}")
    return data


def run_mininet_cmd(host, cmd):
    """Run command on Mininet host using ip netns."""
    full_cmd = f"sudo ip netns exec mn_{host} {cmd}"
    try:
        subprocess.run(full_cmd, shell=True, capture_output=True, timeout=5)
        return True
    except:
        return False


def start_iperf_server(port):
    """Start iperf3 server on the server host."""
    cmd = f"sudo ip netns exec mn_server iperf3 -s -p {port} -D"
    subprocess.run(cmd, shell=True, capture_output=True)


def generate_traffic_burst(host, server_ip, port, bandwidth_kbps, duration=1):
    """Generate a single traffic burst using iperf3."""
    bandwidth = f"{int(bandwidth_kbps)}K"
    cmd = f"sudo ip netns exec mn_{host} iperf3 -c {server_ip} -p {port} -u -b {bandwidth} -t {duration} --connect-timeout 1000"
    try:
        subprocess.run(cmd, shell=True, capture_output=True, timeout=duration + 5)
        return True
    except:
        return False


def generate_slice_traffic(slice_type, duration=60):
    """Generate traffic for a specific slice based on CSV data."""
    config = SLICE_CONFIG.get(slice_type)
    if not config:
        print(f"{RED}[✗] Unknown slice type: {slice_type}{NC}")
        return
    
    # Load CSV data
    data = load_csv_data(config['file'])
    if not data:
        print(f"{YELLOW}[!] No data for {slice_type}, using default traffic{NC}")
        # Generate default traffic
        bandwidth = "5M" if slice_type == 'urllc' else "1M"
        cmd = f"sudo ip netns exec mn_{config['host']} iperf3 -c {config['server_ip']} -p {config['port']} -u -b {bandwidth} -t {duration}"
        subprocess.run(cmd, shell=True)
        return
    
    print(f"\n{config['color']}{BOLD}=== Generating {slice_type.upper()} Traffic ==={NC}")
    print(f"  Host: {config['host']} → Server: {config['server_ip']}:{config['port']}")
    print(f"  Data records: {len(data)}")
    print(f"  Duration: {duration}s")
    
    # Start iperf server
    start_iperf_server(config['port'])
    time.sleep(1)
    
    start_time = time.time()
    record_idx = 0
    
    while time.time() - start_time < duration:
        # Get next record (cycle through data)
        record = data[record_idx % len(data)]
        record_idx += 1
        
        # Calculate bandwidth from throughput
        bandwidth_kbps = record['throughput_kbps']
        
        # Generate traffic burst
        print(f"  {config['color']}[{slice_type.upper()}]{NC} Device: {record['device_id']}, "
              f"App: {record['app']}, BW: {bandwidth_kbps:.1f} kbps")
        
        generate_traffic_burst(
            config['host'],
            config['server_ip'],
            config['port'],
            bandwidth_kbps,
            duration=1
        )
        
        # Small delay between bursts
        time.sleep(0.5)
    
    print(f"{GREEN}[✓] {slice_type.upper()} traffic generation complete{NC}")


def generate_embb_traffic(duration=60):
    """Generate eMBB traffic by streaming the Demo.mp4 video file."""
    config = SLICE_CONFIG['embb']
    video_file = config['file']
    
    print(f"\n{YELLOW}{BOLD}=== Generating eMBB Traffic (Video Streaming) ==={NC}")
    print(f"  Host: {config['host']} → Server: {config['server_ip']}:{config['port']}")
    print(f"  Source: {video_file}")
    print(f"  Type: High bandwidth video streaming")
    
    # Check if video file exists
    if not os.path.exists(video_file):
        print(f"{RED}[✗] Video file not found: {video_file}{NC}")
        print(f"{YELLOW}[!] Using default high-bandwidth traffic instead{NC}")
        start_iperf_server(config['port'])
        time.sleep(1)
        cmd = f"sudo ip netns exec mn_{config['host']} iperf3 -c {config['server_ip']} -p {config['port']} -u -b 50M -t {duration}"
        subprocess.run(cmd, shell=True)
        return
    
    # Get video file size
    video_size = os.path.getsize(video_file)
    video_size_mb = video_size / (1024 * 1024)
    print(f"  Video size: {video_size_mb:.2f} MB")
    
    # Calculate bandwidth needed to stream video in given duration
    # bandwidth = file_size / duration
    bandwidth_mbps = (video_size * 8) / (duration * 1000000)
    bandwidth_mbps = max(bandwidth_mbps, 10)  # Minimum 10 Mbps
    bandwidth_mbps = min(bandwidth_mbps, 100)  # Maximum 100 Mbps
    
    print(f"  Streaming bandwidth: {bandwidth_mbps:.1f} Mbps")
    
    # Start iperf server
    start_iperf_server(config['port'])
    time.sleep(1)
    
    # Stream the video file using netcat + iperf3 for realistic traffic
    # We'll use iperf3 with bandwidth matching video bitrate
    
    # First, calculate chunks based on video
    chunk_duration = 5  # 5-second chunks like real video streaming
    num_chunks = duration // chunk_duration
    
    print(f"  Streaming in {num_chunks} chunks of {chunk_duration}s each...")
    
    for i in range(num_chunks):
        # Vary bandwidth slightly to simulate adaptive bitrate
        current_bw = bandwidth_mbps * random.uniform(0.8, 1.2)
        print(f"  {YELLOW}[eMBB]{NC} Chunk {i+1}/{num_chunks}: {current_bw:.1f} Mbps")
        
        cmd = f"sudo ip netns exec mn_{config['host']} iperf3 -c {config['server_ip']} -p {config['port']} -u -b {current_bw:.0f}M -t {chunk_duration} 2>/dev/null"
        subprocess.run(cmd, shell=True, capture_output=True)
    
    print(f"{GREEN}[✓] eMBB video streaming complete{NC}")


def main():
    parser = argparse.ArgumentParser(description='5G Slice Traffic Generator from CSV Data')
    parser.add_argument('--slice', choices=['urllc', 'embb', 'mmtc', 'all'], 
                        default='all', help='Which slice to generate traffic for')
    parser.add_argument('--duration', type=int, default=60, 
                        help='Duration in seconds (default: 60)')
    parser.add_argument('--list', action='store_true', 
                        help='List available data files')
    args = parser.parse_args()
    
    print(f"{CYAN}{BOLD}")
    print("╔══════════════════════════════════════════════════════════════════════════════╗")
    print("║              📊 5G TRAFFIC GENERATOR FROM CSV DATA 📊                       ║")
    print("╚══════════════════════════════════════════════════════════════════════════════╝")
    print(f"{NC}")
    
    if args.list:
        print(f"{YELLOW}Available data files:{NC}")
        for slice_type, config in SLICE_CONFIG.items():
            filepath = config['file']
            if os.path.exists(filepath):
                data = load_csv_data(filepath)
                print(f"  {GREEN}✓{NC} {slice_type.upper()}: {filepath} ({len(data)} records)")
            else:
                print(f"  {RED}✗{NC} {slice_type.upper()}: {filepath} (not found)")
        return
    
    # Check if running as root
    if os.geteuid() != 0:
        print(f"{RED}[✗] This script must be run as root (sudo){NC}")
        sys.exit(1)
    
    # Kill any existing iperf3 processes
    print(f"{YELLOW}[*] Cleaning up existing traffic...{NC}")
    subprocess.run("sudo pkill -9 iperf3 2>/dev/null", shell=True)
    time.sleep(1)
    
    # Generate traffic based on slice selection
    if args.slice == 'all':
        print(f"{YELLOW}[*] Generating traffic for ALL slices...{NC}")
        # Run all in parallel using background processes
        import threading
        
        threads = []
        t1 = threading.Thread(target=generate_slice_traffic, args=('urllc', args.duration))
        t2 = threading.Thread(target=generate_embb_traffic, args=(args.duration,))
        t3 = threading.Thread(target=generate_slice_traffic, args=('mmtc', args.duration))
        
        threads = [t1, t2, t3]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
    elif args.slice == 'embb':
        generate_embb_traffic(args.duration)
    else:
        generate_slice_traffic(args.slice, args.duration)
    
    print(f"\n{GREEN}{BOLD}╔══════════════════════════════════════════════════════════════════════════════╗")
    print("║                    ✅ TRAFFIC GENERATION COMPLETE ✅                        ║")
    print(f"╚══════════════════════════════════════════════════════════════════════════════╝{NC}")


if __name__ == "__main__":
    main()
