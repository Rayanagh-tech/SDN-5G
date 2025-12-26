#!/usr/bin/env python3
"""
5G Network Slicing SDN Controller
=================================
Ryu-based OpenFlow 1.3 controller implementing network slicing for 5G use cases.

Slices:
- URLLC (Ultra-Reliable Low-Latency Communication) - Port 5001
- eMBB (Enhanced Mobile Broadband) - Port 5002  
- mMTC (Massive Machine Type Communication) - Port 5003

Features:
- Traffic classification by UDP destination port
- DSCP marking for QoS differentiation
- OpenFlow meters for bandwidth enforcement
- Real-time flow statistics collection
- JSON metrics export for ELK integration

Author: SDN-5G Project
"""

import json
import time
import logging
from datetime import datetime
from pathlib import Path

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ipv4, udp
from ryu.lib import hub

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('SlicingController')


class SlicingController(app_manager.RyuApp):
    """
    Ryu SDN Controller for 5G Network Slicing.
    
    Implements traffic classification, QoS enforcement via DSCP marking
    and OpenFlow meters, and real-time metrics collection.
    """
    
    # Use OpenFlow 1.3
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    
    # Slice definitions: port -> (slice_name, dscp_value, meter_id, rate_kbps)
    # DSCP values: URLLC=46 (EF), eMBB=34 (AF41), mMTC=10 (AF11)
    SLICE_CONFIG = {
        5001: {
            'name': 'URLLC',
            'dscp': 46,          # Expedited Forwarding (EF)
            'meter_id': 1,
            'rate_kbps': 10000,  # 10 Mbps max
            'priority': 100      # Highest priority
        },
        5002: {
            'name': 'eMBB',
            'dscp': 34,          # Assured Forwarding (AF41)
            'meter_id': 2,
            'rate_kbps': 100000, # 100 Mbps max
            'priority': 50
        },
        5003: {
            'name': 'mMTC',
            'dscp': 10,          # Assured Forwarding (AF11)
            'meter_id': 3,
            'rate_kbps': 5000,   # 5 Mbps max
            'priority': 10       # Lowest priority
        }
    }
    
    def __init__(self, *args, **kwargs):
        super(SlicingController, self).__init__(*args, **kwargs)
        
        # MAC address table for L2 learning
        self.mac_to_port = {}
        
        # Flow statistics storage
        self.flow_stats = {}
        
        # Metrics storage for export
        self.metrics = {
            'URLLC': {'bytes': 0, 'packets': 0, 'bandwidth_mbps': 0},
            'eMBB': {'bytes': 0, 'packets': 0, 'bandwidth_mbps': 0},
            'mMTC': {'bytes': 0, 'packets': 0, 'bandwidth_mbps': 0}
        }
        
        # Previous stats for bandwidth calculation
        self.prev_stats = {}
        self.prev_time = time.time()
        
        # Metrics output directory
        self.metrics_dir = Path('monitoring/metrics')
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        
        # Start statistics collection thread
        self.monitor_thread = hub.spawn(self._monitor_loop)
        
        logger.info("SlicingController initialized - OpenFlow 1.3")
        logger.info(f"Slice configuration: {list(self.SLICE_CONFIG.keys())}")

    def _monitor_loop(self):
        """
        Background thread for periodic flow statistics collection.
        Runs every 5 seconds to gather metrics from all datapaths.
        """
        while True:
            for datapath in self.datapaths.values():
                self._request_stats(datapath)
            hub.sleep(5)  # Collect stats every 5 seconds

    @property
    def datapaths(self):
        """Get all registered datapaths."""
        if not hasattr(self, '_datapaths'):
            self._datapaths = {}
        return self._datapaths

    def _request_stats(self, datapath):
        """Request flow statistics from a datapath."""
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        
        # Request flow stats
        req = parser.OFPFlowStatsRequest(datapath)
        datapath.send_msg(req)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        """
        Handle switch connection event.
        
        Called when a switch connects to the controller.
        Installs:
        1. Default table-miss flow (send to controller)
        2. Meters for bandwidth enforcement per slice
        3. Slice classification rules
        """
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        dpid = datapath.id
        
        logger.info(f"Switch connected: DPID={dpid}")
        
        # Register datapath
        self.datapaths[dpid] = datapath
        
        # 1. Install table-miss flow entry (lowest priority)
        # Packets not matching any rule are sent to controller
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self._add_flow(datapath, 0, match, actions)
        logger.info(f"  Installed table-miss flow on DPID={dpid}")
        
        # 2. Install meters for bandwidth enforcement
        self._install_meters(datapath)
        
        # 3. Install slice classification rules
        self._install_slice_rules(datapath)

    def _install_meters(self, datapath):
        """
        Install OpenFlow meters for bandwidth rate limiting.
        
        Each slice gets a dedicated meter with DSCP remark action
        when rate is exceeded.
        """
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        
        for port, config in self.SLICE_CONFIG.items():
            meter_id = config['meter_id']
            rate_kbps = config['rate_kbps']
            
            # Create meter with DROP band when rate exceeded
            # Using OFPMBT_DROP to drop packets exceeding the rate
            bands = [
                parser.OFPMeterBandDrop(
                    rate=rate_kbps,      # Rate in kb/s
                    burst_size=rate_kbps // 10  # Burst size
                )
            ]
            
            # Meter modification message
            meter_mod = parser.OFPMeterMod(
                datapath=datapath,
                command=ofproto.OFPMC_ADD,
                flags=ofproto.OFPMF_KBPS,  # Rate in kbps
                meter_id=meter_id,
                bands=bands
            )
            
            datapath.send_msg(meter_mod)
            logger.info(f"  Installed meter {meter_id} for {config['name']}: "
                       f"{rate_kbps} kbps")

    def _install_slice_rules(self, datapath):
        """
        Install flow rules for slice traffic classification.
        
        Rules match on UDP destination port and apply:
        - DSCP marking for QoS
        - Meter for bandwidth enforcement
        """
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        
        for port, config in self.SLICE_CONFIG.items():
            # Match UDP traffic to specific port
            match = parser.OFPMatch(
                eth_type=0x0800,      # IPv4
                ip_proto=17,          # UDP
                udp_dst=port
            )
            
            # Actions: Set DSCP, apply meter, output (will be set on packet-in)
            # DSCP is in the upper 6 bits of IP ToS field
            actions = [
                parser.OFPActionSetField(ip_dscp=config['dscp'])
            ]
            
            # Install with meter instruction
            inst = [
                parser.OFPInstructionMeter(config['meter_id']),
                parser.OFPInstructionActions(
                    ofproto.OFPIT_APPLY_ACTIONS, actions
                ),
                parser.OFPInstructionGotoTable(1)  # Forward to table 1
            ]
            
            # Create flow mod with instructions
            mod = parser.OFPFlowMod(
                datapath=datapath,
                priority=config['priority'],
                match=match,
                instructions=inst,
                table_id=0
            )
            datapath.send_msg(mod)
            
            logger.info(f"  Installed slice rule: port {port} -> "
                       f"{config['name']} (DSCP={config['dscp']})")

    def _add_flow(self, datapath, priority, match, actions, 
                  idle_timeout=0, hard_timeout=0, table_id=0):
        """
        Add a flow entry to the switch.
        
        Args:
            datapath: Switch datapath
            priority: Flow priority (higher = more important)
            match: Match criteria
            actions: Actions to apply
            idle_timeout: Remove after idle seconds (0 = permanent)
            hard_timeout: Remove after seconds (0 = permanent)
            table_id: Flow table ID
        """
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        
        inst = [parser.OFPInstructionActions(
            ofproto.OFPIT_APPLY_ACTIONS, actions
        )]
        
        mod = parser.OFPFlowMod(
            datapath=datapath,
            priority=priority,
            match=match,
            instructions=inst,
            idle_timeout=idle_timeout,
            hard_timeout=hard_timeout,
            table_id=table_id
        )
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        """
        Handle packet-in events.
        
        Implements L2 learning switch behavior:
        1. Learn source MAC -> port mapping
        2. Look up destination MAC
        3. Forward to known port or flood
        """
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        dpid = datapath.id
        in_port = msg.match['in_port']
        
        # Parse packet
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        
        if eth is None:
            return
        
        # Ignore LLDP
        if eth.ethertype == 0x88cc:
            return
        
        src = eth.src
        dst = eth.dst
        
        # Initialize MAC table for this switch
        self.mac_to_port.setdefault(dpid, {})
        
        # Learn source MAC
        self.mac_to_port[dpid][src] = in_port
        
        # Determine output port
        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD
        
        actions = [parser.OFPActionOutput(out_port)]
        
        # Install flow for known destination (avoid controller overhead)
        if out_port != ofproto.OFPP_FLOOD:
            # Check if this is slice traffic
            ipv4_pkt = pkt.get_protocol(ipv4.ipv4)
            udp_pkt = pkt.get_protocol(udp.udp)
            
            if ipv4_pkt and udp_pkt:
                dst_port = udp_pkt.dst_port
                if dst_port in self.SLICE_CONFIG:
                    config = self.SLICE_CONFIG[dst_port]
                    # Add DSCP marking for slice traffic
                    actions = [
                        parser.OFPActionSetField(ip_dscp=config['dscp']),
                        parser.OFPActionOutput(out_port)
                    ]
                    match = parser.OFPMatch(
                        in_port=in_port,
                        eth_dst=dst,
                        eth_type=0x0800,
                        ip_proto=17,
                        udp_dst=dst_port
                    )
                    self._add_flow(datapath, config['priority'], 
                                  match, actions, idle_timeout=60)
                    logger.debug(f"Installed flow: {src}->{dst} port {dst_port} "
                               f"({config['name']})")
            else:
                # Regular L2 flow
                match = parser.OFPMatch(in_port=in_port, eth_dst=dst)
                self._add_flow(datapath, 1, match, actions, idle_timeout=60)
        
        # Send packet out
        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data
        
        out = parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=msg.buffer_id,
            in_port=in_port,
            actions=actions,
            data=data
        )
        datapath.send_msg(out)

    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def flow_stats_reply_handler(self, ev):
        """
        Handle flow statistics reply.
        
        Parses flow stats to calculate per-slice metrics:
        - Bytes transferred
        - Packets transferred
        - Bandwidth (calculated from byte delta)
        
        Exports metrics as JSON for ELK integration.
        """
        body = ev.msg.body
        dpid = ev.msg.datapath.id
        current_time = time.time()
        time_delta = current_time - self.prev_time
        
        # Aggregate stats per slice
        slice_stats = {
            'URLLC': {'bytes': 0, 'packets': 0},
            'eMBB': {'bytes': 0, 'packets': 0},
            'mMTC': {'bytes': 0, 'packets': 0}
        }
        
        for stat in body:
            # Check if this is a slice flow (by UDP port match)
            if 'udp_dst' in stat.match:
                udp_dst = stat.match['udp_dst']
                if udp_dst in self.SLICE_CONFIG:
                    slice_name = self.SLICE_CONFIG[udp_dst]['name']
                    slice_stats[slice_name]['bytes'] += stat.byte_count
                    slice_stats[slice_name]['packets'] += stat.packet_count
        
        # Calculate bandwidth and update metrics
        for slice_name, stats in slice_stats.items():
            current_bytes = stats['bytes']
            prev_bytes = self.prev_stats.get(slice_name, {}).get('bytes', 0)
            
            # Calculate bandwidth in Mbps
            if time_delta > 0:
                byte_delta = current_bytes - prev_bytes
                bandwidth_mbps = (byte_delta * 8) / (time_delta * 1000000)
                bandwidth_mbps = max(0, bandwidth_mbps)  # Ensure non-negative
            else:
                bandwidth_mbps = 0
            
            # Update metrics
            self.metrics[slice_name] = {
                'bytes': current_bytes,
                'packets': stats['packets'],
                'bandwidth_mbps': round(bandwidth_mbps, 3)
            }
        
        # Store current stats for next calculation
        self.prev_stats = slice_stats.copy()
        self.prev_time = current_time
        
        # Export metrics to JSON
        self._export_metrics()
        
        # Log summary
        logger.info(f"Flow stats (DPID={dpid}):")
        for name, m in self.metrics.items():
            logger.info(f"  {name}: {m['bandwidth_mbps']:.2f} Mbps, "
                       f"{m['packets']} pkts, {m['bytes']} bytes")

    def _export_metrics(self):
        """
        Export current metrics to JSON file for Logstash ingestion.
        
        Creates timestamped JSON records with slice metrics.
        """
        timestamp = datetime.utcnow().isoformat() + 'Z'
        
        metrics_records = []
        for slice_name, m in self.metrics.items():
            record = {
                'timestamp': timestamp,
                'slice_name': slice_name,
                'bandwidth_mbps': m['bandwidth_mbps'],
                'packets': m['packets'],
                'bytes': m['bytes'],
                'controller': 'ryu-slicing',
                'type': 'flow_stats'
            }
            metrics_records.append(record)
        
        # Write to JSON file (append mode for Logstash file input)
        metrics_file = self.metrics_dir / 'flow_metrics.json'
        with open(metrics_file, 'a') as f:
            for record in metrics_records:
                f.write(json.dumps(record) + '\n')

    def get_metrics(self):
        """
        Public API to get current metrics.
        
        Returns:
            dict: Current metrics per slice
        """
        return self.metrics.copy()


# Entry point for Ryu application
app_manager.require_app('ryu.app.ofctl_rest')
