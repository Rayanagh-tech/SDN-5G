#!/bin/bash
# ============================================================================
# 5G Network Slicing - Quick Start Script
# ============================================================================
# This script automates the setup and execution of the network slicing
# experiment. Run with sudo for Mininet operations.
#
# Usage:
#   chmod +x run_experiment.sh
#   sudo ./run_experiment.sh
# ============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
EXPERIMENT_DURATION=${1:-60}
CONTROLLER_PORT=6653
REST_API_PORT=8080

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}  5G Network Slicing Experiment${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# Function to check if a command exists
check_command() {
    if ! command -v $1 &> /dev/null; then
        echo -e "${RED}Error: $1 is not installed${NC}"
        exit 1
    fi
}

# Function to check if a port is available
check_port() {
    if nc -z localhost $1 2>/dev/null; then
        echo -e "${YELLOW}Warning: Port $1 is already in use${NC}"
        return 1
    fi
    return 0
}

# Function to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}Cleaning up...${NC}"
    
    # Stop iperf3 servers
    pkill -f iperf3 2>/dev/null || true
    
    # Stop Ryu controller
    pkill -f ryu-manager 2>/dev/null || true
    
    # Clean Mininet
    mn -c 2>/dev/null || true
    
    echo -e "${GREEN}Cleanup complete${NC}"
}

# Set trap for cleanup
trap cleanup EXIT

echo -e "${BLUE}Step 1: Checking prerequisites...${NC}"
check_command python3
check_command ryu-manager
check_command iperf3
check_command mn
check_command docker
echo -e "${GREEN}All prerequisites installed${NC}"
echo ""

echo -e "${BLUE}Step 2: Creating required directories...${NC}"
mkdir -p monitoring/metrics monitoring/logs
echo -e "${GREEN}Directories created${NC}"
echo ""

echo -e "${BLUE}Step 3: Starting ELK stack...${NC}"
if docker-compose ps | grep -q "Up"; then
    echo -e "${YELLOW}ELK stack already running${NC}"
else
    docker-compose up -d
    echo "Waiting for Elasticsearch to be ready..."
    for i in {1..30}; do
        if curl -s http://localhost:9200 > /dev/null 2>&1; then
            echo -e "${GREEN}Elasticsearch ready${NC}"
            break
        fi
        sleep 5
        echo "  Waiting... ($i/30)"
    done
fi
echo ""

echo -e "${BLUE}Step 4: Starting Ryu SDN Controller...${NC}"
if check_port $CONTROLLER_PORT; then
    ryu-manager --ofp-tcp-listen-port $CONTROLLER_PORT \
                --wsapi-port $REST_API_PORT \
                controller.py &
    CONTROLLER_PID=$!
    sleep 3
    echo -e "${GREEN}Controller started (PID: $CONTROLLER_PID)${NC}"
else
    echo -e "${YELLOW}Controller may already be running${NC}"
fi
echo ""

echo -e "${BLUE}Step 5: Starting Mininet topology...${NC}"
echo "This will open the Mininet CLI."
echo "Run the following commands in Mininet:"
echo ""
echo -e "${YELLOW}  # Start iperf3 servers on server host${NC}"
echo "  server iperf3 -s -p 5001 -D"
echo "  server iperf3 -s -p 5002 -D"
echo "  server iperf3 -s -p 5003 -D"
echo ""
echo -e "${YELLOW}  # Generate traffic from slice hosts${NC}"
echo "  urllc_h1 iperf3 -c 10.0.0.100 -u -p 5001 -b 5M -l 128 -t $EXPERIMENT_DURATION &"
echo "  embb_h1 iperf3 -c 10.0.0.100 -u -p 5002 -b 50M -l 1400 -t $EXPERIMENT_DURATION &"
echo "  mmtc_h1 iperf3 -c 10.0.0.100 -u -p 5003 -b 1M -l 256 -t $EXPERIMENT_DURATION &"
echo ""
echo -e "${YELLOW}  # Wait for completion and exit${NC}"
echo "  exit"
echo ""
echo -e "${BLUE}Press Enter to start Mininet...${NC}"
read

python3 topology.py

echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}  Experiment Complete!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo "Results available at:"
echo "  - Kibana: http://localhost:5601"
echo "  - Metrics: monitoring/metrics/"
echo "  - Logs: monitoring/logs/"
echo ""
