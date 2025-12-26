# 5G Network Slicing with SDN

A complete, academically defensible implementation of 5G Network Slicing using Software-Defined Networking (SDN). This project demonstrates real traffic differentiation, QoS enforcement, and SLA monitoring using industry-standard tools.

## 🎯 Project Overview

This project implements a simplified but realistic 5G Network Slicing system that:

- **Classifies traffic** into three 5G slice types (URLLC, eMBB, mMTC)
- **Enforces QoS** using DSCP marking and OpenFlow meters
- **Generates real traffic** using iperf3
- **Monitors performance** with real-time metrics collection
- **Visualizes results** using the ELK stack (Elasticsearch, Logstash, Kibana)
- **Automates deployment** using Terraform and Docker

---

## 📁 Project Structure

```
SDN-5G/
│
├── controller.py           # Ryu SDN slicing controller (OpenFlow 1.3)
├── topology.py             # Mininet network topology
├── slice_manager.py        # Slice definitions & SLA logic
├── orchestrator.py         # High-level experiment control
│
├── data-input/
│   ├── video.json          # eMBB traffic profile (high bandwidth)
│   ├── latency.json        # URLLC traffic profile (low latency)
│   └── mmtc.json           # mMTC traffic profile (IoT)
│
├── traffic/
│   ├── __init__.py
│   └── traffic_generator.py    # iperf3 traffic launcher
│
├── monitoring/
│   ├── logstash.conf       # Logstash pipeline configuration
│   └── metrics_collector.py    # Metrics collection module
│
├── terraform/
│   ├── main.tf             # Infrastructure as code
│   ├── variables.tf        # Configuration variables
│   └── outputs.tf          # Deployment outputs
│
├── docker-compose.yml      # ELK stack deployment
└── README.md               # This file
```

---

## 🏗️ Architecture

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           5G NETWORK SLICING SYSTEM                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        CONTROL PLANE                                  │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐  │   │
│  │  │   Ryu SDN       │  │  Slice Manager  │  │    Orchestrator     │  │   │
│  │  │   Controller    │◄─┤  (SLA Logic)    │◄─┤  (Experiment Ctrl)  │  │   │
│  │  │   (OF 1.3)      │  │                 │  │                     │  │   │
│  │  └────────┬────────┘  └─────────────────┘  └─────────────────────┘  │   │
│  └───────────┼──────────────────────────────────────────────────────────┘   │
│              │ OpenFlow                                                      │
│  ┌───────────▼──────────────────────────────────────────────────────────┐   │
│  │                         DATA PLANE (Mininet)                          │   │
│  │                                                                        │   │
│  │   ┌────────────┐      ┌────────┐      ┌────────┐      ┌──────────┐   │   │
│  │   │ urllc_h1   │──────│   S1   │──────│   S2   │──────│  server  │   │   │
│  │   │ (Port 5001)│      │(Access)│      │ (Core) │      │ (iperf3) │   │   │
│  │   └────────────┘      │        │      │        │      └──────────┘   │   │
│  │   ┌────────────┐      │        │      │        │                     │   │
│  │   │ embb_h1    │──────┤        │      │        │                     │   │
│  │   │ (Port 5002)│      │        ├──────┤   S3   │                     │   │
│  │   └────────────┘      │        │      │ (Edge) │                     │   │
│  │   ┌────────────┐      │        │      │        │                     │   │
│  │   │ mmtc_h1    │──────┤        │      │        │                     │   │
│  │   │ (Port 5003)│      └────────┘      └────────┘                     │   │
│  │   └────────────┘                                                      │   │
│  └───────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐   │
│  │                         MONITORING PLANE                               │   │
│  │  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐              │   │
│  │  │ Elasticsearch │◄──│   Logstash   │◄──│   Metrics    │              │   │
│  │  │  (Storage)    │   │ (Ingestion)  │   │  Collector   │              │   │
│  │  └──────┬───────┘   └──────────────┘   └──────────────┘              │   │
│  │         │                                                              │   │
│  │  ┌──────▼───────┐                                                     │   │
│  │  │    Kibana    │  ← Dashboards & Visualization                       │   │
│  │  └──────────────┘                                                     │   │
│  └───────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Traffic Flow

```
Client Hosts                    Switches                    Server
┌──────────┐                  ┌────────┐                 ┌──────────┐
│ urllc_h1 │──UDP:5001───────▶│   S1   │────────────────▶│  server  │
│          │   DSCP=46 (EF)   │        │                 │          │
└──────────┘   Meter ID: 1    │        │                 │  iperf3  │
                               │        │                 │  servers │
┌──────────┐                  │        │                 │          │
│ embb_h1  │──UDP:5002───────▶│        │──────S2────────▶│ :5001    │
│          │   DSCP=34 (AF41) │        │                 │ :5002    │
└──────────┘   Meter ID: 2    │        │                 │ :5003    │
                               │        │                 │          │
┌──────────┐                  │        │                 └──────────┘
│ mmtc_h1  │──UDP:5003───────▶│        │
│          │   DSCP=10 (AF11) └────────┘
└──────────┘   Meter ID: 3
```

---

## 📊 Slice Definitions & SLA

### Three 5G Slice Types

| Slice | Use Case | UDP Port | DSCP | Priority |
|-------|----------|----------|------|----------|
| **URLLC** | Ultra-Reliable Low-Latency | 5001 | 46 (EF) | 100 |
| **eMBB** | Enhanced Mobile Broadband | 5002 | 34 (AF41) | 50 |
| **mMTC** | Massive Machine Type Comm. | 5003 | 10 (AF11) | 10 |

### SLA Requirements

| Metric | URLLC | eMBB | mMTC |
|--------|-------|------|------|
| **Min Bandwidth** | 5 Mbps | 50 Mbps | 1 Mbps |
| **Max Latency** | 5 ms | 20 ms | 100 ms |
| **Max Jitter** | 1 ms | 5 ms | 20 ms |
| **Max Packet Loss** | 0.001% | 1% | 1% |

---

## 🔧 QoS Enforcement Mechanism

### How Traffic is Classified

1. **Packet Arrival**: UDP packet arrives at OVS switch
2. **Match Rules**: OpenFlow matches on `eth_type=0x0800, ip_proto=17, udp_dst`
3. **Action**: Apply DSCP marking and meter

### DSCP Marking

```python
# DSCP values for differentiated services
URLLC: DSCP = 46  # Expedited Forwarding (EF) - highest priority
eMBB:  DSCP = 34  # Assured Forwarding AF41 - high throughput
mMTC:  DSCP = 10  # Assured Forwarding AF11 - best effort
```

### OpenFlow Meters

Meters enforce bandwidth limits by dropping excess traffic:

```
Meter 1 (URLLC): Rate = 10,000 kbps
Meter 2 (eMBB):  Rate = 100,000 kbps  
Meter 3 (mMTC):  Rate = 5,000 kbps
```

---

## 🚀 Installation & Setup

### Prerequisites

- **Ubuntu 20.04/22.04** (or WSL2 on Windows)
- **Python 3.8+**
- **Mininet** (with Open vSwitch)
- **Ryu SDN Framework**
- **Docker & Docker Compose**
- **iperf3**
- **Terraform** (optional, for automation)

### Step 1: Install Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Mininet
sudo apt install mininet -y

# Install Open vSwitch
sudo apt install openvswitch-switch -y

# Install iperf3
sudo apt install iperf3 -y

# Install Python dependencies
pip3 install ryu eventlet requests

# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt install docker-compose -y
```

### Step 2: Clone the Project

```bash
cd ~/Desktop
git clone <repository-url> SDN-5G
cd SDN-5G
```

### Step 3: Create Required Directories

```bash
mkdir -p monitoring/metrics monitoring/logs
```

---

## ▶️ Running the Experiment

### Quick Start (5 Steps)

```bash
# Terminal 1: Start ELK Stack
docker-compose up -d

# Terminal 2: Start Ryu Controller
ryu-manager --ofp-tcp-listen-port 6653 --wsapi-port 8080 controller.py

# Terminal 3: Start Mininet Topology (requires sudo)
sudo python3 topology.py

# Terminal 4: Run Traffic Generation (inside Mininet or from host)
# Option A: From Mininet CLI
mininet> urllc_h1 iperf3 -c 10.0.0.100 -u -p 5001 -b 5M -t 60 &
mininet> embb_h1 iperf3 -c 10.0.0.100 -u -p 5002 -b 50M -t 60 &
mininet> mmtc_h1 iperf3 -c 10.0.0.100 -u -p 5003 -b 1M -t 60 &

# Terminal 5: Collect Metrics
python3 monitoring/metrics_collector.py --duration 120
```

### Detailed Execution

#### 1. Start ELK Stack

```bash
# Start all ELK services
docker-compose up -d

# Verify services are running
docker-compose ps

# Wait for Kibana to be ready (about 2 minutes)
curl -s http://localhost:5601/api/status | grep -q "available" && echo "Kibana ready!"
```

#### 2. Start Ryu Controller

```bash
# Basic start
ryu-manager controller.py

# With REST API enabled
ryu-manager --ofp-tcp-listen-port 6653 --wsapi-port 8080 controller.py

# Verbose output
ryu-manager --verbose controller.py
```

#### 3. Start Mininet Topology

```bash
# Start with default settings
sudo python3 topology.py

# With custom controller address
sudo python3 topology.py 192.168.1.100 6653
```

In the Mininet CLI:
```
mininet> nodes          # List all nodes
mininet> links          # Show link information
mininet> pingall        # Test connectivity
mininet> xterm server   # Open terminal on server
```

#### 4. Start iperf3 Servers (on server host)

From the Mininet CLI:
```bash
mininet> server iperf3 -s -p 5001 -D  # URLLC
mininet> server iperf3 -s -p 5002 -D  # eMBB
mininet> server iperf3 -s -p 5003 -D  # mMTC
```

#### 5. Generate Traffic

Using the traffic generator script:
```bash
python3 -m traffic.traffic_generator --server 10.0.0.100 --duration 60
```

Or manually from Mininet:
```bash
# URLLC traffic (small packets, low latency)
mininet> urllc_h1 iperf3 -c 10.0.0.100 -u -p 5001 -b 5M -l 128 -t 60 --json > /tmp/urllc.json &

# eMBB traffic (high bandwidth)
mininet> embb_h1 iperf3 -c 10.0.0.100 -u -p 5002 -b 50M -l 1400 -t 60 --json > /tmp/embb.json &

# mMTC traffic (periodic, low bandwidth)
mininet> mmtc_h1 iperf3 -c 10.0.0.100 -u -p 5003 -b 1M -l 256 -t 60 --json > /tmp/mmtc.json &
```

---

## 📈 Monitoring & Visualization

### Access Kibana Dashboard

1. Open browser: **http://localhost:5601**
2. Go to **Management → Stack Management → Index Patterns**
3. Create index pattern: `sdn-*`
4. Select `@timestamp` as the time field

### Create Visualizations

#### Bandwidth per Slice (Line Chart)
1. Go to **Visualize Library → Create visualization**
2. Select **Line**
3. Y-axis: Average of `bandwidth_mbps`
4. X-axis: Date Histogram on `@timestamp`
5. Split series by `slice_name`

#### Latency Comparison (Bar Chart)
1. Create **Vertical Bar**
2. Y-axis: Average of `latency_ms`
3. X-axis: Terms on `slice_name`
4. Add color by `sla_status`

#### SLA Violations (Metric)
1. Create **Metric** visualization
2. Count where `sla_status = "violated"`
3. Split by `slice_name`

### Sample Kibana Dashboard

Create a dashboard with:
- [x] Bandwidth over time (per slice)
- [x] Latency distribution
- [x] Jitter comparison
- [x] Packet loss percentage
- [x] SLA violation count
- [x] Real-time metrics table

---

## 🔬 Understanding the Results

### What the Controller Does

1. **Switch Connection**: Installs default table-miss rule
2. **Meter Installation**: Creates bandwidth limiters per slice
3. **Slice Rules**: Matches UDP port → applies DSCP + meter
4. **Statistics**: Collects flow stats every 5 seconds
5. **Export**: Writes JSON metrics for ELK ingestion

### Expected Traffic Behavior

| Slice | Expected Bandwidth | Expected Latency | Packet Loss |
|-------|-------------------|------------------|-------------|
| URLLC | ~5 Mbps | <5 ms | <0.01% |
| eMBB | ~50 Mbps | <20 ms | <1% |
| mMTC | ~1 Mbps | <100 ms | <1% |

### SLA Violation Detection

The system detects violations when:
- Bandwidth falls below minimum threshold
- Latency exceeds maximum threshold
- Jitter exceeds maximum threshold
- Packet loss exceeds maximum threshold

---

## 🛠️ Troubleshooting

### Common Issues

#### Controller Not Connecting

```bash
# Check if OVS is running
sudo service openvswitch-switch status

# Restart OVS
sudo service openvswitch-switch restart

# Check controller reachability
telnet 127.0.0.1 6653
```

#### Mininet Cleanup

```bash
# Clean up previous Mininet session
sudo mn -c

# Kill any leftover processes
sudo pkill -f ryu-manager
sudo pkill -f iperf3
```

#### ELK Stack Issues

```bash
# Check container logs
docker-compose logs elasticsearch
docker-compose logs logstash
docker-compose logs kibana

# Restart services
docker-compose restart

# Full reset
docker-compose down -v
docker-compose up -d
```

#### No Flow Statistics

```bash
# Check flows on switch
sudo ovs-ofctl -O OpenFlow13 dump-flows s1

# Check meters
sudo ovs-ofctl -O OpenFlow13 dump-meters s1

# Verify controller connection
sudo ovs-vsctl show
```

---

## 📚 API Reference

### Controller REST API

```bash
# Get all flows
curl http://localhost:8080/stats/flow/1

# Get port statistics
curl http://localhost:8080/stats/port/1

# Get meter statistics
curl http://localhost:8080/stats/meter/1
```

### Slice Manager API

```python
from slice_manager import get_slice_config, check_sla

# Get slice configuration
config = get_slice_config('URLLC')

# Check SLA compliance
metrics = {
    'bandwidth_mbps': 4.5,
    'latency_ms': 6.0,
    'jitter_ms': 0.5,
    'packet_loss_pct': 0.0
}
result = check_sla('URLLC', metrics)
# result['status'] == 'violated' (bandwidth too low)
```

---

## 🧪 Running Tests

### Unit Tests

```bash
# Test slice manager
python3 -c "from slice_manager import SliceManager; m = SliceManager(); print(m.format_sla_report('URLLC'))"

# Test traffic profiles
python3 -c "from traffic import load_profiles; p = load_profiles(); print(p)"
```

### Integration Test

```bash
# Run full experiment with orchestrator
python3 orchestrator.py --duration 30 --slices URLLC eMBB mMTC
```

---

## 📖 Academic Defense Points

### Why This Implementation is Valid

1. **Real Traffic**: Uses iperf3 for actual UDP traffic generation
2. **Real QoS**: OpenFlow 1.3 meters enforce bandwidth limits
3. **Real Metrics**: Flow statistics from actual packet counts
4. **Standard Protocols**: OpenFlow, DSCP are industry standards
5. **Reproducible**: All parameters are configurable and documented

### Key Contributions

1. **Simplified Architecture**: Demonstrates slicing without complexity
2. **Modular Design**: Each component is independent and testable
3. **Real Measurements**: No simulated or random metrics
4. **Complete Pipeline**: From traffic generation to visualization

### Limitations (Honest Assessment)

1. **Latency Estimation**: Uses jitter as proxy (real RTT needs ping)
2. **Single Switch**: Simplified topology (production uses multiple)
3. **Static Slices**: No dynamic slice creation/modification
4. **Local Deployment**: Not tested on distributed infrastructure

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

## 📄 License

This project is licensed under the MIT License.

---

## 👥 Authors

SDN-5G Network Slicing Team

---

## 🔗 References

1. 3GPP TS 23.501 - 5G System Architecture
2. ONF SDN Architecture Overview
3. Ryu SDN Framework Documentation
4. Open vSwitch with OpenFlow 1.3
5. IETF RFC 2474 - Differentiated Services Field
