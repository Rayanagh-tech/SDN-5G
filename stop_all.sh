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

echo -e "${YELLOW}Stopping all 5G Network Slicing services...${NC}"
echo ""

echo -e "${YELLOW}[1/5] Stopping Mininet...${NC}"
sudo mn -c 2>/dev/null
echo -e "${GREEN}[✓] Mininet stopped${NC}"

echo -e "${YELLOW}[2/5] Stopping Ryu Controller...${NC}"
sudo pkill -9 -f "ryu-manager" 2>/dev/null || true
echo -e "${GREEN}[✓] Controller stopped${NC}"

echo -e "${YELLOW}[3/5] Stopping Monitor...${NC}"
sudo pkill -9 -f "simple_monitor" 2>/dev/null || true
echo -e "${GREEN}[✓] Monitor stopped${NC}"

echo -e "${YELLOW}[4/5] Stopping iperf3...${NC}"
sudo pkill -9 -f "iperf3" 2>/dev/null || true
echo -e "${GREEN}[✓] iperf3 stopped${NC}"

echo -e "${YELLOW}[5/5] Stopping Web Server...${NC}"
sudo pkill -9 -f "http.server" 2>/dev/null || true
echo -e "${GREEN}[✓] Web server stopped${NC}"

echo ""
echo -e "${GREEN}"
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║                    ✅ ALL SERVICES STOPPED ✅                                ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"
