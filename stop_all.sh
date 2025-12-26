#!/bin/bash
# ============================================================================
# STOP ALL 5G NETWORK SLICING SERVICES
# ============================================================================
# Usage: sudo ./stop_all.sh
# ============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}[*] Stopping all services...${NC}"

# Stop Mininet
echo -e "${YELLOW}[1/4] Stopping Mininet...${NC}"
sudo mn -c 2>/dev/null
echo -e "${GREEN}[✓] Mininet stopped${NC}"

# Stop Ryu Controller
echo -e "${YELLOW}[2/4] Stopping Ryu Controller...${NC}"
sudo pkill -f "ryu-manager" 2>/dev/null || true
echo -e "${GREEN}[✓] Controller stopped${NC}"

# Stop Monitor
echo -e "${YELLOW}[3/4] Stopping Monitor...${NC}"
sudo pkill -f "simple_monitor" 2>/dev/null || true
echo -e "${GREEN}[✓] Monitor stopped${NC}"

# Stop iperf3
echo -e "${YELLOW}[4/4] Stopping iperf3...${NC}"
sudo pkill -f "iperf3" 2>/dev/null || true
echo -e "${GREEN}[✓] iperf3 stopped${NC}"

echo -e "${GREEN}"
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║                    ✅ ALL SERVICES STOPPED ✅                                ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"
