#!/bin/bash
# ============================================================================
# ONE-CLICK 5G NETWORK SLICING DEMO
# ============================================================================
# This script starts the complete 5G Network Slicing demo automatically.
# No Docker, no Terraform, no ELK - just pure Python + Mininet!
#
# Usage: sudo ./start_all.sh
# ============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║              🚀 5G NETWORK SLICING - ONE-CLICK DEMO 🚀                       ║"
echo "╠══════════════════════════════════════════════════════════════════════════════╣"
echo "║  Starting: Ryu Controller + Mininet + Traffic Generation + Monitoring       ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Create directories
mkdir -p monitoring/logs
mkdir -p monitoring/metrics
mkdir -p monitoring/reports

# Cleanup function
cleanup() {
    echo -e "\n${YELLOW}[*] Cleaning up...${NC}"
    sudo mn -c 2>/dev/null || true
    sudo pkill -f "ryu-manager" 2>/dev/null || true
    sudo pkill -f "simple_monitor" 2>/dev/null || true
    sudo pkill -f "iperf3" 2>/dev/null || true
    echo -e "${GREEN}[✓] Cleanup complete${NC}"
}

# Set trap for cleanup on exit
trap cleanup EXIT

# Step 1: Cleanup previous runs
echo -e "${YELLOW}[1/5] Cleaning up previous sessions...${NC}"
cleanup
sleep 2

# Step 2: Start Ryu Controller
echo -e "${YELLOW}[2/5] Starting Ryu SDN Controller...${NC}"
ryu-manager --ofp-tcp-listen-port 6653 controller.py > monitoring/logs/controller.log 2>&1 &
CONTROLLER_PID=$!
sleep 3

if ps -p $CONTROLLER_PID > /dev/null; then
    echo -e "${GREEN}[✓] Controller started (PID: $CONTROLLER_PID)${NC}"
else
    echo -e "${RED}[✗] Controller failed to start. Check monitoring/logs/controller.log${NC}"
    exit 1
fi

# Step 3: Start Mininet in background with auto-traffic
echo -e "${YELLOW}[3/5] Starting Mininet topology with auto-traffic...${NC}"

# Create a Python script that runs Mininet and generates traffic
cat > /tmp/run_mininet.py << 'MININET_SCRIPT'
#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')
from mininet.net import Mininet
from mininet.node import RemoteController, OVSKernelSwitch
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.log import setLogLevel
import time
import threading

def create_topology():
    net = Mininet(controller=RemoteController, switch=OVSKernelSwitch, link=TCLink)
    
    # Add controller
    c0 = net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6653)
    
    # Add switches
    s1 = net.addSwitch('s1', protocols='OpenFlow13')
    s2 = net.addSwitch('s2', protocols='OpenFlow13')
    s3 = net.addSwitch('s3', protocols='OpenFlow13')
    
    # Add hosts
    urllc_h1 = net.addHost('urllc_h1', ip='10.0.0.1/24')
    embb_h1 = net.addHost('embb_h1', ip='10.0.0.2/24')
    mmtc_h1 = net.addHost('mmtc_h1', ip='10.0.0.3/24')
    server = net.addHost('server', ip='10.0.0.100/24')
    
    # Add links
    net.addLink(urllc_h1, s1, bw=100)
    net.addLink(embb_h1, s2, bw=100)
    net.addLink(mmtc_h1, s3, bw=100)
    net.addLink(s1, s2, bw=1000)
    net.addLink(s2, s3, bw=1000)
    net.addLink(s3, server, bw=1000)
    
    return net

def generate_traffic(net):
    """Generate traffic automatically after network starts."""
    time.sleep(5)  # Wait for network to stabilize
    
    server = net.get('server')
    urllc = net.get('urllc_h1')
    embb = net.get('embb_h1')
    mmtc = net.get('mmtc_h1')
    
    print("\n[*] Starting iperf3 servers...")
    server.cmd('killall iperf3 2>/dev/null')
    time.sleep(1)
    server.cmd('iperf3 -s -p 5001 -D')
    server.cmd('iperf3 -s -p 5002 -D')
    server.cmd('iperf3 -s -p 5003 -D')
    time.sleep(2)
    
    print("[*] Generating slice traffic...")
    # URLLC: Low latency, moderate bandwidth
    urllc.cmd('iperf3 -c 10.0.0.100 -p 5001 -t 300 -b 50M &')
    # eMBB: High bandwidth
    embb.cmd('iperf3 -c 10.0.0.100 -p 5002 -t 300 -b 100M &')
    # mMTC: Low bandwidth, many packets
    mmtc.cmd('iperf3 -c 10.0.0.100 -p 5003 -t 300 -b 5M &')
    
    print("[✓] Traffic generation started (5 minutes)")

if __name__ == '__main__':
    setLogLevel('info')
    net = create_topology()
    net.start()
    
    # Start traffic in background thread
    traffic_thread = threading.Thread(target=generate_traffic, args=(net,))
    traffic_thread.daemon = True
    traffic_thread.start()
    
    print("\n" + "="*60)
    print("Network is running. Traffic will start automatically.")
    print("Type 'exit' or press Ctrl+D to stop.")
    print("="*60 + "\n")
    
    CLI(net)
    net.stop()
MININET_SCRIPT

sudo python3 /tmp/run_mininet.py > monitoring/logs/mininet.log 2>&1 &
MININET_PID=$!
sleep 5

echo -e "${GREEN}[✓] Mininet started (PID: $MININET_PID)${NC}"

# Step 4: Start monitoring dashboard
echo -e "${YELLOW}[4/5] Starting monitoring dashboard...${NC}"
python3 monitoring/simple_monitor.py --demo > monitoring/logs/monitor.log 2>&1 &
MONITOR_PID=$!
sleep 2
echo -e "${GREEN}[✓] Monitor started (PID: $MONITOR_PID)${NC}"

# Step 5: Generate HTML report
echo -e "${YELLOW}[5/5] Generating HTML dashboard...${NC}"
sleep 3

echo -e "${GREEN}"
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║                    ✅ ALL SYSTEMS RUNNING ✅                                 ║"
echo "╠══════════════════════════════════════════════════════════════════════════════╣"
echo "║  Ryu Controller:  Running on port 6653                                       ║"
echo "║  REST API:        http://localhost:8080                                      ║"
echo "║  Mininet:         3 slice hosts + 1 server + 3 switches                      ║"
echo "║  Traffic:         Auto-generating on ports 5001, 5002, 5003                  ║"
echo "║  Monitoring:      Real-time stats collection                                 ║"
echo "╠══════════════════════════════════════════════════════════════════════════════╣"
echo "║  📊 View Dashboard: firefox monitoring/reports/dashboard.html                ║"
echo "║  📋 View Logs:      tail -f monitoring/logs/controller.log                   ║"
echo "╠══════════════════════════════════════════════════════════════════════════════╣"
echo "║  Press Ctrl+C to stop all services                                           ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Show live controller output
echo -e "${CYAN}[*] Live Controller Output:${NC}"
echo "-----------------------------------------------------------"
tail -f monitoring/logs/controller.log
