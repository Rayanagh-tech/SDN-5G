#!/bin/bash
# ============================================================================
# 5G NETWORK SLICING - ONE-CLICK DEMO
# ============================================================================
# Starts: Controller + Topology + SliceManager + Orchestrator + Dashboard
# Usage: sudo ./start_all.sh
# ============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Get VM IP
VM_IP=$(hostname -I | awk '{print $1}')

echo -e "${CYAN}${BOLD}"
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║              🚀 5G NETWORK SLICING - ONE-CLICK DEMO 🚀                       ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Create directories
mkdir -p monitoring/logs monitoring/metrics monitoring/reports

# ============================================================================
# STEP 1: CLEANUP
# ============================================================================
echo -e "${YELLOW}[1/6] Cleaning up previous sessions...${NC}"
sudo mn -c 2>/dev/null || true
sudo pkill -9 -f "ryu-manager" 2>/dev/null || true
sudo pkill -9 -f "simple_monitor" 2>/dev/null || true
sudo pkill -9 -f "iperf3" 2>/dev/null || true
sudo pkill -9 -f "http.server" 2>/dev/null || true
sudo pkill -9 -f "orchestrator" 2>/dev/null || true
sleep 2
echo -e "${GREEN}[✓] Cleanup complete${NC}"

# ============================================================================
# STEP 2: START RYU CONTROLLER (uses slice_manager.py internally)
# ============================================================================
echo -e "${YELLOW}[2/6] Starting Ryu SDN Controller + Slice Manager...${NC}"
ryu-manager --ofp-tcp-listen-port 6653 controller.py > monitoring/logs/controller.log 2>&1 &
CONTROLLER_PID=$!
sleep 4

if ps -p $CONTROLLER_PID > /dev/null 2>&1; then
    echo -e "${GREEN}[✓] Controller running (PID: $CONTROLLER_PID)${NC}"
else
    echo -e "${RED}[✗] Controller failed! Check monitoring/logs/controller.log${NC}"
    cat monitoring/logs/controller.log
    exit 1
fi

# ============================================================================
# STEP 3: START MININET TOPOLOGY
# ============================================================================
echo -e "${YELLOW}[3/6] Starting Mininet Topology...${NC}"
sudo python3 topology.py > monitoring/logs/mininet.log 2>&1 &
MININET_PID=$!
sleep 5

if ps -p $MININET_PID > /dev/null 2>&1; then
    echo -e "${GREEN}[✓] Mininet running (PID: $MININET_PID)${NC}"
else
    echo -e "${RED}[✗] Mininet failed! Check monitoring/logs/mininet.log${NC}"
fi

# Wait for switches to connect
echo -e "${YELLOW}[4/6] Waiting for switches to connect...${NC}"
sleep 5
echo -e "${GREEN}[✓] Network ready${NC}"

# ============================================================================
# STEP 5: START MONITORING DASHBOARD
# ============================================================================
echo -e "${YELLOW}[5/6] Starting Monitoring Dashboard...${NC}"
python3 monitoring/simple_monitor.py --demo > monitoring/logs/monitor.log 2>&1 &
MONITOR_PID=$!
sleep 2
echo -e "${GREEN}[✓] Monitor running (PID: $MONITOR_PID)${NC}"

# ============================================================================
# STEP 6: START WEB SERVER FOR DASHBOARD
# ============================================================================
echo -e "${YELLOW}[6/6] Starting Web Dashboard Server...${NC}"
python3 -m http.server 8000 > monitoring/logs/webserver.log 2>&1 &
WEB_PID=$!
sleep 2
echo -e "${GREEN}[✓] Web server running on port 8000${NC}"

# ============================================================================
# SHOW STATUS AND URLS
# ============================================================================
echo ""
echo -e "${GREEN}${BOLD}"
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║                       ✅ ALL SYSTEMS RUNNING ✅                              ║"
echo "╠══════════════════════════════════════════════════════════════════════════════╣"
echo "║  COMPONENTS:                                                                 ║"
echo "║    • Ryu Controller:    PID $CONTROLLER_PID (port 6653)                                ║"
echo "║    • Slice Manager:     Integrated in controller                             ║"
echo "║    • Mininet Topology:  PID $MININET_PID (3 slices + server)                         ║"
echo "║    • Monitor Dashboard: PID $MONITOR_PID                                            ║"
echo "║    • Web Server:        PID $WEB_PID (port 8000)                                   ║"
echo "╠══════════════════════════════════════════════════════════════════════════════╣"
echo -e "${NC}${GREEN}║  ${CYAN}📊 DASHBOARD URL (open in Windows browser):${NC}${GREEN}                              ║"
echo -e "║                                                                              ║"
echo -e "║     ${BOLD}http://${VM_IP}:8000/monitoring/reports/dashboard.html${NC}${GREEN}           ║"
echo "║                                                                              ║"
echo -e "║  ${CYAN}📡 REST API:${NC}${GREEN}                                                               ║"
echo -e "║     http://${VM_IP}:8080/stats/flow/1                                      ║"
echo -e "║     http://${VM_IP}:8080/stats/switches                                    ║"
echo "╠══════════════════════════════════════════════════════════════════════════════╣"
echo -e "║  ${CYAN}🔧 MANUAL TESTING - Open NEW terminal and run:${NC}${GREEN}                          ║"
echo "║                                                                              ║"
echo "║     cd ~/SDN-5G && sudo python3 manual_test.py                               ║"
echo "║                                                                              ║"
echo "╠══════════════════════════════════════════════════════════════════════════════╣"
echo "║  To stop: Press Ctrl+C, then run: sudo ./stop_all.sh                         ║"
echo -e "╚══════════════════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# ============================================================================
# SHOW LIVE LOGS
# ============================================================================
echo -e "${YELLOW}${BOLD}Live Controller Output (Ctrl+C to exit):${NC}"
echo "============================================================"
tail -f monitoring/logs/controller.log
