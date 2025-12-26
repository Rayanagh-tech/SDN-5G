#!/usr/bin/env python3
"""
Manual Testing Script for 5G Network Slicing
=============================================
Connects to the running Mininet network and provides easy testing commands.

Usage: sudo python3 manual_test.py
"""

import subprocess
import sys
import time
import os

# Colors
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
CYAN = '\033[0;36m'
BOLD = '\033[1m'
NC = '\033[0m'

def print_banner():
    print(f"""{CYAN}{BOLD}
╔══════════════════════════════════════════════════════════════════════════════╗
║              🔧 5G NETWORK SLICING - MANUAL TESTING 🔧                       ║
╚══════════════════════════════════════════════════════════════════════════════╝
{NC}""")

def print_menu():
    print(f"""
{YELLOW}Available Commands:{NC}
  {GREEN}1{NC} - Test connectivity (pingall)
  {GREEN}2{NC} - Start iperf3 servers on server host
  {GREEN}3{NC} - Generate URLLC traffic from CSV (port 5001)
  {GREEN}4{NC} - Generate eMBB traffic from Video (port 5002)
  {GREEN}5{NC} - Generate mMTC traffic from CSV (port 5003)
  {GREEN}6{NC} - Generate ALL slice traffic (from data files)
  {GREEN}7{NC} - Show switch flows
  {GREEN}8{NC} - Show network status
  {GREEN}9{NC} - Stop all traffic
  {GREEN}0{NC} - Exit
""")

def run_mn_cmd(host, cmd):
    """Run command on Mininet host."""
    full_cmd = f"sudo mnexec -a $(pgrep -f 'python3 topology.py') {host} {cmd}"
    # Alternative using ip netns
    ns_cmd = f"sudo ip netns exec mn_{host} {cmd}"
    try:
        result = subprocess.run(ns_cmd, shell=True, capture_output=True, text=True, timeout=30)
        return result.stdout + result.stderr
    except:
        return "Command failed or timed out"

def test_connectivity():
    """Test connectivity between all hosts."""
    print(f"{YELLOW}Testing connectivity...{NC}")
    
    hosts = [
        ("urllc_h1", "10.0.0.1"),
        ("embb_h1", "10.0.0.2"),
        ("mmtc_h1", "10.0.0.3"),
        ("server", "10.0.0.100")
    ]
    
    for src_name, src_ip in hosts:
        for dst_name, dst_ip in hosts:
            if src_name != dst_name:
                cmd = f"ping -c 1 -W 1 {dst_ip}"
                result = subprocess.run(
                    f"sudo ip netns exec mn_{src_name} {cmd}",
                    shell=True, capture_output=True, text=True
                )
                if "1 received" in result.stdout:
                    print(f"  {GREEN}✓{NC} {src_name} -> {dst_name}")
                else:
                    print(f"  {RED}✗{NC} {src_name} -> {dst_name}")

def start_iperf_servers():
    """Start iperf3 servers on the server host."""
    print(f"{YELLOW}Starting iperf3 servers on ports 5001, 5002, 5003...{NC}")
    
    subprocess.run("sudo ip netns exec mn_server killall iperf3 2>/dev/null", shell=True)
    time.sleep(1)
    
    subprocess.run("sudo ip netns exec mn_server iperf3 -s -p 5001 -D", shell=True)
    subprocess.run("sudo ip netns exec mn_server iperf3 -s -p 5002 -D", shell=True)
    subprocess.run("sudo ip netns exec mn_server iperf3 -s -p 5003 -D", shell=True)
    
    time.sleep(1)
    result = subprocess.run("sudo ip netns exec mn_server pgrep iperf3", shell=True, capture_output=True, text=True)
    if result.stdout.strip():
        print(f"{GREEN}✓ iperf3 servers running{NC}")
    else:
        print(f"{RED}✗ Failed to start iperf3 servers{NC}")

def generate_traffic(slice_type):
    """Generate traffic for a specific slice using data files."""
    print(f"{YELLOW}Generating {slice_type.upper()} traffic from data files...{NC}")
    
    # Use the traffic_generator.py script
    cmd = f"python3 traffic_generator.py --slice {slice_type} --duration 30 &"
    subprocess.run(cmd, shell=True)
    print(f"{GREEN}✓ {slice_type.upper()} traffic started (30 seconds){NC}")

def generate_all_traffic():
    """Generate traffic on all slices using data files."""
    print(f"{YELLOW}Starting all slice traffic from data files...{NC}")
    print(f"  - URLLC: urllc_traffic.csv")
    print(f"  - eMBB: Demo.mp4 (video streaming)")
    print(f"  - mMTC: mmtc_traffic.csv")
    
    start_iperf_servers()
    time.sleep(2)
    
    # Use the traffic_generator.py script
    cmd = "python3 traffic_generator.py --slice all --duration 60 &"
    subprocess.run(cmd, shell=True)
    print(f"{GREEN}✓ All traffic started (60 seconds){NC}")

def show_flows():
    """Show OpenFlow flows on switches."""
    print(f"{YELLOW}Switch Flows:{NC}")
    for i in [1, 2, 3]:
        print(f"\n{CYAN}=== Switch s{i} ==={NC}")
        result = subprocess.run(
            f"sudo ovs-ofctl dump-flows s{i} -O OpenFlow13 2>/dev/null | head -20",
            shell=True, capture_output=True, text=True
        )
        print(result.stdout if result.stdout else "No flows or switch not found")

def show_status():
    """Show network status."""
    print(f"{YELLOW}Network Status:{NC}")
    
    # Check controller
    result = subprocess.run("pgrep -f ryu-manager", shell=True, capture_output=True)
    if result.returncode == 0:
        print(f"  {GREEN}✓{NC} Ryu Controller running")
    else:
        print(f"  {RED}✗{NC} Ryu Controller not running")
    
    # Check Mininet
    result = subprocess.run("pgrep -f 'python3 topology.py'", shell=True, capture_output=True)
    if result.returncode == 0:
        print(f"  {GREEN}✓{NC} Mininet running")
    else:
        print(f"  {RED}✗{NC} Mininet not running")
    
    # Check switches
    result = subprocess.run("sudo ovs-vsctl show 2>/dev/null | grep Bridge", shell=True, capture_output=True, text=True)
    switches = result.stdout.count("Bridge")
    print(f"  {GREEN}✓{NC} {switches} OVS switches found")
    
    # Check iperf3 servers
    result = subprocess.run("sudo ip netns exec mn_server pgrep iperf3 2>/dev/null", shell=True, capture_output=True, text=True)
    servers = len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0
    print(f"  {GREEN}✓{NC} {servers} iperf3 servers running")

def stop_traffic():
    """Stop all iperf3 traffic."""
    print(f"{YELLOW}Stopping all traffic...{NC}")
    subprocess.run("sudo pkill -9 iperf3 2>/dev/null", shell=True)
    print(f"{GREEN}✓ Traffic stopped{NC}")

def main():
    print_banner()
    
    # Check if running as root
    if os.geteuid() != 0:
        print(f"{RED}Error: This script must be run as root (sudo){NC}")
        sys.exit(1)
    
    while True:
        print_menu()
        try:
            choice = input(f"{CYAN}Enter choice (0-9): {NC}").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{YELLOW}Exiting...{NC}")
            break
        
        if choice == "1":
            test_connectivity()
        elif choice == "2":
            start_iperf_servers()
        elif choice == "3":
            generate_traffic("urllc")
        elif choice == "4":
            generate_traffic("embb")
        elif choice == "5":
            generate_traffic("mmtc")
        elif choice == "6":
            generate_all_traffic()
        elif choice == "7":
            show_flows()
        elif choice == "8":
            show_status()
        elif choice == "9":
            stop_traffic()
        elif choice == "0":
            print(f"{YELLOW}Exiting...{NC}")
            break
        else:
            print(f"{RED}Invalid choice{NC}")

if __name__ == "__main__":
    main()
