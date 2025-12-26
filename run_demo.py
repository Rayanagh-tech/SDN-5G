#!/usr/bin/env python3
"""
Quick Start Script for 5G Network Slicing Demo
===============================================
Runs the complete demo without Docker/ELK.
"""

import subprocess
import sys
import os
import time
import signal

def print_banner():
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    5G NETWORK SLICING DEMONSTRATION                          ║
║                         Lightweight Version                                   ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  This demo runs without Docker/ELK to save disk space.                       ║
║  Monitoring is done via Python-based terminal dashboard.                      ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)

def check_requirements():
    """Check if required tools are available."""
    print("[*] Checking requirements...")
    
    requirements = {
        'python3': 'Python 3',
        'ryu-manager': 'Ryu SDN Controller',
        'mn': 'Mininet',
        'iperf3': 'iperf3'
    }
    
    missing = []
    for cmd, name in requirements.items():
        try:
            subprocess.run([cmd, '--version'], capture_output=True, timeout=5)
            print(f"    ✓ {name}")
        except:
            print(f"    ✗ {name} - MISSING")
            missing.append(name)
    
    if missing:
        print(f"\n[!] Missing requirements: {', '.join(missing)}")
        print("    Install with: sudo apt-get install mininet iperf3")
        print("    And: pip3 install ryu")
        return False
    
    return True

def cleanup():
    """Clean up any running processes."""
    print("\n[*] Cleaning up previous sessions...")
    os.system("sudo mn -c 2>/dev/null")
    os.system("sudo pkill -f 'ryu-manager' 2>/dev/null")
    os.system("sudo pkill -f 'iperf3' 2>/dev/null")
    time.sleep(2)

def start_controller():
    """Start Ryu controller in background."""
    print("[*] Starting Ryu SDN Controller...")
    
    controller_cmd = [
        'ryu-manager',
        '--ofp-tcp-listen-port', '6653',
        '--wsapi-port', '8080',
        'controller.py'
    ]
    
    log_file = open('monitoring/logs/controller.log', 'w')
    proc = subprocess.Popen(
        controller_cmd,
        stdout=log_file,
        stderr=subprocess.STDOUT
    )
    
    time.sleep(3)
    
    if proc.poll() is None:
        print(f"    ✓ Controller started (PID: {proc.pid})")
        return proc
    else:
        print("    ✗ Controller failed to start")
        return None

def main():
    print_banner()
    
    if not check_requirements():
        sys.exit(1)
    
    cleanup()
    
    # Create log directory
    os.makedirs('monitoring/logs', exist_ok=True)
    os.makedirs('monitoring/metrics', exist_ok=True)
    
    controller = start_controller()
    if not controller:
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("NEXT STEPS:")
    print("=" * 60)
    print("""
1. In a NEW terminal, start the Mininet topology:
   sudo python3 topology.py

2. In ANOTHER terminal, start the monitoring dashboard:
   python3 monitoring/simple_monitor.py --demo

3. (Optional) Open the HTML dashboard in a browser:
   firefox monitoring/reports/dashboard.html

4. To stop everything:
   - Press Ctrl+C in each terminal
   - Run: sudo mn -c
   - Run: sudo pkill ryu-manager
""")
    print("=" * 60)
    
    print("\n[*] Controller is running. Press Ctrl+C to stop.")
    
    try:
        controller.wait()
    except KeyboardInterrupt:
        print("\n[*] Stopping controller...")
        controller.terminate()
        cleanup()
        print("[*] Done!")

if __name__ == "__main__":
    main()
