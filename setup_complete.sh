#!/bin/bash
# ============================================================================
# 5G Network Slicing - Complete Setup Script for Mininet VM
# ============================================================================
# This script sets up the entire 5G Network Slicing project in a Mininet VM.
# 
# Prerequisites:
# - Mininet VM (Ubuntu-based)
# - Internet connection
#
# Usage:
#   chmod +x setup_complete.sh
#   sudo ./setup_complete.sh
# ============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║       5G Network Slicing - Complete Setup Script             ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root (sudo ./setup_complete.sh)${NC}"
    exit 1
fi

# Get the actual user (not root)
ACTUAL_USER=${SUDO_USER:-$USER}
PROJECT_DIR="/home/$ACTUAL_USER/SDN-5G"

echo -e "${BLUE}[1/7] Updating system packages...${NC}"
apt-get update
apt-get upgrade -y

echo -e "${BLUE}[2/7] Installing dependencies...${NC}"
apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    iperf3 \
    curl \
    wget \
    git \
    net-tools \
    openvswitch-switch \
    openvswitch-common

# Start OVS
systemctl start openvswitch-switch
systemctl enable openvswitch-switch

echo -e "${BLUE}[3/7] Installing Python packages...${NC}"
pip3 install --upgrade pip
pip3 install ryu eventlet requests

echo -e "${BLUE}[4/7] Installing Docker...${NC}"
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sh
    usermod -aG docker $ACTUAL_USER
    systemctl start docker
    systemctl enable docker
    echo -e "${GREEN}Docker installed successfully${NC}"
else
    echo -e "${YELLOW}Docker already installed${NC}"
fi

echo -e "${BLUE}[5/7] Installing Docker Compose...${NC}"
if ! command -v docker-compose &> /dev/null; then
    apt-get install -y docker-compose
    echo -e "${GREEN}Docker Compose installed successfully${NC}"
else
    echo -e "${YELLOW}Docker Compose already installed${NC}"
fi

echo -e "${BLUE}[6/7] Creating project directory...${NC}"
mkdir -p $PROJECT_DIR
mkdir -p $PROJECT_DIR/data-input
mkdir -p $PROJECT_DIR/traffic
mkdir -p $PROJECT_DIR/monitoring/metrics
mkdir -p $PROJECT_DIR/monitoring/logs
mkdir -p $PROJECT_DIR/terraform

chown -R $ACTUAL_USER:$ACTUAL_USER $PROJECT_DIR

echo -e "${BLUE}[7/7] Setup complete!${NC}"
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    SETUP COMPLETE!                           ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "Project directory: ${YELLOW}$PROJECT_DIR${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "1. Copy the project files to $PROJECT_DIR"
echo "2. cd $PROJECT_DIR"
echo "3. docker-compose up -d    # Start ELK stack"
echo "4. ryu-manager controller.py &"
echo "5. sudo python3 topology.py"
echo ""
echo -e "${YELLOW}NOTE: Log out and log back in for Docker group permissions to take effect${NC}"
