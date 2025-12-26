# 🛜 5G Network Slicing with SDN

A complete implementation of **5G Network Slicing** using **Software-Defined Networking (SDN)**. This project creates virtual network "slices" on a single physical network, where each slice has different Quality of Service (QoS) requirements.

---

## 📖 What is This Project?

This project demonstrates **5G Network Slicing** using **Software-Defined Networking (SDN)**. It creates virtual network "slices" on a single physical network, where each slice has different Quality of Service (QoS) requirements.

### Key Features:
- ✅ **Traffic Classification** - Automatically identifies URLLC, eMBB, mMTC traffic
- ✅ **QoS Enforcement** - DSCP marking and bandwidth meters
- ✅ **Real Traffic Generation** - Using iperf3
- ✅ **Real-time Monitoring** - Dashboard with live metrics
- ✅ **One-Click Automation** - Start everything with single command

---

## 🎯 The 3 Network Slices (5G Use Cases)

| Slice | Name | Purpose | Requirements |
|-------|------|---------|--------------|
| **URLLC** | Ultra-Reliable Low Latency | Autonomous cars, remote surgery | <1ms latency, 99.999% reliability |
| **eMBB** | Enhanced Mobile Broadband | Video streaming, gaming | High bandwidth (100+ Mbps) |
| **mMTC** | Massive Machine Type Comm. | IoT sensors, smart meters | Many devices, low bandwidth |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CONTROL PLANE                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    Ryu SDN Controller (controller.py)                │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐   │   │
│  │  │ Slice Manager│  │ Flow Manager │  │ QoS / Meter Manager      │   │   │
│  │  │ (SLA rules)  │  │ (OpenFlow)   │  │ (Bandwidth enforcement)  │   │   │
│  │  └──────────────┘  └──────────────┘  └──────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              ↕ OpenFlow 1.3                                 │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                            DATA PLANE (Mininet)                             │
│                                                                             │
│   ┌──────────┐      ┌──────────┐      ┌──────────┐      ┌──────────┐       │
│   │ urllc_h1 │      │ embb_h1  │      │ mmtc_h1  │      │  server  │       │
│   │ 10.0.0.1 │      │ 10.0.0.2 │      │ 10.0.0.3 │      │10.0.0.100│       │
│   │ Port:5001│      │ Port:5002│      │ Port:5003│      │ iperf3   │       │
│   └────┬─────┘      └────┬─────┘      └────┬─────┘      └────┬─────┘       │
│        │                 │                 │                 │             │
│   ┌────▼─────┐      ┌────▼─────┐      ┌────▼─────┐           │             │
│   │ Switch 1 │──────│ Switch 2 │──────│ Switch 3 │───────────┘             │
│   │ (OVS s1) │      │ (OVS s2) │      │ (OVS s3) │                         │
│   │ DSCP=46  │      │ DSCP=34  │      │ DSCP=10  │                         │
│   └──────────┘      └──────────┘      └──────────┘                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                          MONITORING PLANE                                   │
│  ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────────┐   │
│  │ simple_monitor.py │  │ REST API (:8080)  │  │ Web Dashboard (:8000) │   │
│  │ (Stats collector) │  │ (Flow stats)      │  │ (HTML visualization)  │   │
│  └───────────────────┘  └───────────────────┘  └───────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
SDN-5G/
├── controller.py        # Ryu SDN Controller + Flow/Meter Manager
├── topology.py          # Mininet Topology (3 slices + server)
├── slice_manager.py     # SLA definitions & monitoring
├── orchestrator.py      # High-level experiment control
├── manual_test.py       # Interactive testing menu
├── start_all.sh         # ONE-CLICK START
├── stop_all.sh          # ONE-CLICK STOP
├── monitoring/
│   └── simple_monitor.py  # Dashboard generator
├── data-input/          # Traffic profiles (JSON)
│   ├── latency.json     # URLLC profile
│   ├── video.json       # eMBB profile
│   └── mmtc.json        # mMTC profile
└── requirements.txt     # Python dependencies
```

---

## 🔧 Component Details

### **1. controller.py - SDN Controller**
```
Role: Brain of the network
- Receives packets from switches via OpenFlow
- Classifies traffic by destination port (5001/5002/5003)
- Applies DSCP marking for QoS
- Installs flow rules on switches
- Enforces bandwidth limits with meters
```

### **2. topology.py - Network Topology**
```
Role: Creates virtual network in Mininet
- 3 host machines (one per slice)
- 1 server (receives traffic)
- 3 OpenFlow switches (connected linearly)
- Links with bandwidth limits
```

### **3. slice_manager.py - SLA Manager**
```
Role: Defines & monitors SLA requirements
- URLLC: 50 Mbps, <1ms latency, <0.001% loss
- eMBB: 100 Mbps, <10ms latency, <0.01% loss
- mMTC: 5 Mbps, <100ms latency, <0.1% loss
- Detects SLA violations
```

### **4. orchestrator.py - Orchestrator**
```
Role: High-level experiment control
- Loads traffic profiles from JSON
- Coordinates traffic generation
- Aggregates metrics
```

### **5. simple_monitor.py - Dashboard**
```
Role: Real-time visualization
- Collects metrics per slice
- Generates HTML dashboard
- Shows bandwidth, latency, jitter, packet loss
```

---

## 🔄 How Traffic Classification Works

```
1. URLLC host sends traffic to port 5001
   ↓
2. Switch receives packet, sends to Controller (table-miss)
   ↓
3. Controller checks: dst_port=5001 → URLLC slice
   ↓
4. Controller installs flow:
   - Match: dst_port=5001
   - Action: Set DSCP=46, apply meter_1 (50Mbps), forward
   ↓
5. Future URLLC packets flow directly through switch
   (no controller involvement - line-rate forwarding)
```

---

## 🚀 Quick Start

### Prerequisites
- Mininet VM (Ubuntu)
- Python 3.8+
- Ryu SDN Framework
- iperf3

### Installation

```bash
# Clone the repository
git clone https://github.com/Rayanagh-tech/SDN-5G.git
cd SDN-5G

# Install dependencies
pip3 install ryu eventlet webob

# Make scripts executable
chmod +x start_all.sh stop_all.sh
```

### One-Click Start

```bash
sudo ./start_all.sh
```

**What Happens:**
1. ✅ Cleans previous sessions
2. ✅ Starts Ryu Controller (port 6653)
3. ✅ Starts Mininet Topology (3 hosts + server + 3 switches)
4. ✅ Starts Monitoring Dashboard
5. ✅ Starts Web Server (port 8000)
6. ✅ Shows you the Dashboard URL

---

## 🔧 Manual Testing

Open a **NEW terminal** and run:

```bash
cd ~/SDN-5G
sudo python3 manual_test.py
```

### Menu Options:
```
1 - Test connectivity (pingall)
2 - Start iperf3 servers
3 - Generate URLLC traffic (50 Mbps → port 5001)
4 - Generate eMBB traffic (100 Mbps → port 5002)
5 - Generate mMTC traffic (5 Mbps → port 5003)
6 - Generate ALL traffic
7 - Show switch flows
8 - Show network status
9 - Stop all traffic
0 - Exit
```

---

## 📊 View Dashboard

### Web Dashboard (from Windows browser):
```
http://<VM_IP>:8000/monitoring/reports/dashboard.html
```

### REST API:
```
http://<VM_IP>:8080/stats/flow/1      # Flow statistics
http://<VM_IP>:8080/stats/switches    # Connected switches
```

---

## ⏹️ Stop Everything

```bash
sudo ./stop_all.sh
```

---

## 📈 Expected Results

| Metric | URLLC | eMBB | mMTC |
|--------|-------|------|------|
| Bandwidth | ~50 Mbps | ~100 Mbps | ~5 Mbps |
| DSCP | 46 (EF) | 34 (AF41) | 10 (AF11) |
| Port | 5001 | 5002 | 5003 |
| Priority | Highest | Medium | Lowest |

---

## 🎓 Key SDN/5G Concepts Demonstrated

1. **Network Slicing** - Logical separation of traffic types
2. **OpenFlow 1.3** - Protocol for switch-controller communication
3. **DSCP Marking** - QoS differentiation at Layer 3
4. **Meters** - Bandwidth rate limiting
5. **Flow Tables** - Hardware-accelerated packet forwarding
6. **SLA Monitoring** - Ensuring QoS guarantees

---

## 🛠️ Troubleshooting

### Controller not starting
```bash
# Check if port is in use
sudo lsof -i :6653
# Kill existing process
sudo pkill -f ryu-manager
```

### Mininet cleanup
```bash
sudo mn -c
```

### Check switch flows
```bash
sudo ovs-ofctl dump-flows s1 -O OpenFlow13
```

### View logs
```bash
tail -f monitoring/logs/controller.log
tail -f monitoring/logs/mininet.log
```

---

## 📚 References

- [Ryu SDN Framework](https://ryu-sdn.org/)
- [Mininet](http://mininet.org/)
- [OpenFlow 1.3 Specification](https://opennetworking.org/software-defined-standards/specifications/)
- [3GPP 5G Network Slicing](https://www.3gpp.org/)

---

## 📝 License

This project is for educational purposes.

---

## 👤 Author

Created for 5G Network Slicing demonstration with SDN.
