#!/usr/bin/env python3
"""
5G Network Slicing Metrics Collector
=====================================
Collects metrics from multiple sources and exports them to ELK stack.

Sources:
1. Ryu Controller REST API (flow statistics)
2. iperf3 output files (traffic metrics)
3. System metrics (CPU, memory, network interfaces)

Exports:
- JSON files for Logstash file input
- HTTP POST to Logstash endpoint
- Real-time logging for debugging

Author: SDN-5G Project
"""

import json
import time
import logging
import requests
import threading
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('MetricsCollector')


@dataclass
class FlowMetric:
    """Metric from OpenFlow flow statistics."""
    timestamp: str
    slice_name: str
    bandwidth_mbps: float
    packets: int
    bytes: int
    duration_sec: int
    priority: int
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass  
class SliceMetric:
    """Aggregated metric for a network slice."""
    timestamp: str
    slice_name: str
    bandwidth_mbps: float
    latency_ms: float
    jitter_ms: float
    packet_loss_pct: float
    packets_sent: int
    packets_received: int
    bytes_transferred: int
    sla_status: str
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SystemMetric:
    """System-level metrics."""
    timestamp: str
    cpu_percent: float
    memory_percent: float
    network_bytes_sent: int
    network_bytes_recv: int
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MetricsCollector:
    """
    Collects and exports metrics for the 5G Network Slicing system.
    """
    
    # Configuration
    CONTROLLER_API = 'http://127.0.0.1:8080'
    LOGSTASH_HTTP = 'http://127.0.0.1:5044'
    COLLECTION_INTERVAL = 5  # seconds
    
    # Slice port mapping
    PORT_TO_SLICE = {
        5001: 'URLLC',
        5002: 'eMBB',
        5003: 'mMTC'
    }
    
    def __init__(self, output_dir: Optional[str] = None):
        """
        Initialize the metrics collector.
        
        Args:
            output_dir: Directory for metric output files
        """
        self.output_dir = Path(output_dir or 'monitoring/metrics')
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.running = False
        self.collection_thread = None
        
        # Metrics storage
        self.flow_metrics: List[FlowMetric] = []
        self.slice_metrics: List[SliceMetric] = []
        
        # Previous stats for delta calculation
        self.prev_flow_stats: Dict[str, Dict] = {}
        self.prev_time = time.time()
        
        logger.info(f"MetricsCollector initialized. Output: {self.output_dir}")
    
    def start(self):
        """Start continuous metrics collection."""
        if self.running:
            logger.warning("Collector already running")
            return
        
        self.running = True
        self.collection_thread = threading.Thread(
            target=self._collection_loop,
            daemon=True
        )
        self.collection_thread.start()
        logger.info("Metrics collection started")
    
    def stop(self):
        """Stop metrics collection."""
        self.running = False
        if self.collection_thread:
            self.collection_thread.join(timeout=10)
        logger.info("Metrics collection stopped")
    
    def _collection_loop(self):
        """Main collection loop running in background thread."""
        while self.running:
            try:
                # Collect from all sources
                self._collect_controller_metrics()
                self._collect_iperf_metrics()
                
                # Export metrics
                self._export_metrics()
                
            except Exception as e:
                logger.error(f"Collection error: {e}")
            
            time.sleep(self.COLLECTION_INTERVAL)
    
    def _collect_controller_metrics(self):
        """Collect flow statistics from Ryu controller REST API."""
        try:
            # Get all switches (assumption: DPID 1 is main switch)
            response = requests.get(
                f'{self.CONTROLLER_API}/stats/flow/1',
                timeout=5
            )
            
            if response.status_code != 200:
                logger.debug(f"Controller API returned {response.status_code}")
                return
            
            data = response.json()
            current_time = time.time()
            time_delta = current_time - self.prev_time
            
            # Process flow entries
            flows = data.get('1', [])  # DPID 1
            
            for flow in flows:
                # Check if this is a slice flow (has UDP port match)
                match = flow.get('match', {})
                udp_dst = match.get('udp_dst')
                
                if udp_dst and udp_dst in self.PORT_TO_SLICE:
                    slice_name = self.PORT_TO_SLICE[udp_dst]
                    
                    byte_count = flow.get('byte_count', 0)
                    packet_count = flow.get('packet_count', 0)
                    duration = flow.get('duration_sec', 0)
                    priority = flow.get('priority', 0)
                    
                    # Calculate bandwidth
                    prev_bytes = self.prev_flow_stats.get(
                        slice_name, {}
                    ).get('bytes', 0)
                    
                    if time_delta > 0:
                        byte_delta = byte_count - prev_bytes
                        bandwidth_mbps = (byte_delta * 8) / (time_delta * 1_000_000)
                        bandwidth_mbps = max(0, bandwidth_mbps)
                    else:
                        bandwidth_mbps = 0
                    
                    # Create metric
                    metric = FlowMetric(
                        timestamp=datetime.utcnow().isoformat() + 'Z',
                        slice_name=slice_name,
                        bandwidth_mbps=round(bandwidth_mbps, 3),
                        packets=packet_count,
                        bytes=byte_count,
                        duration_sec=duration,
                        priority=priority
                    )
                    
                    self.flow_metrics.append(metric)
                    
                    # Update previous stats
                    self.prev_flow_stats[slice_name] = {
                        'bytes': byte_count,
                        'packets': packet_count
                    }
            
            self.prev_time = current_time
            logger.debug(f"Collected {len(flows)} flow entries")
            
        except requests.exceptions.RequestException as e:
            logger.debug(f"Controller not available: {e}")
        except Exception as e:
            logger.error(f"Error collecting controller metrics: {e}")
    
    def _collect_iperf_metrics(self):
        """Collect metrics from iperf3 output files."""
        iperf_files = {
            'URLLC': '/tmp/iperf3_URLLC.json',
            'eMBB': '/tmp/iperf3_eMBB.json',
            'mMTC': '/tmp/iperf3_mMTC.json'
        }
        
        for slice_name, filepath in iperf_files.items():
            path = Path(filepath)
            if not path.exists():
                continue
            
            try:
                # Check if file was recently modified
                mtime = path.stat().st_mtime
                if time.time() - mtime > 120:  # Skip if older than 2 minutes
                    continue
                
                with open(path, 'r') as f:
                    data = json.load(f)
                
                # Parse iperf3 results
                metric = self._parse_iperf_data(slice_name, data)
                if metric:
                    self.slice_metrics.append(metric)
                    logger.debug(f"Collected iperf metrics for {slice_name}")
                    
            except json.JSONDecodeError:
                logger.debug(f"Invalid JSON in {filepath}")
            except Exception as e:
                logger.error(f"Error reading {filepath}: {e}")
    
    def _parse_iperf_data(self, slice_name: str, 
                          data: Dict) -> Optional[SliceMetric]:
        """Parse iperf3 JSON output into SliceMetric."""
        try:
            end = data.get('end', {})
            
            # Get summary data
            if 'sum' in end:
                sum_data = end['sum']
            elif 'sum_sent' in end:
                sum_data = end['sum_sent']
            else:
                return None
            
            # Extract basic metrics
            bytes_transferred = sum_data.get('bytes', 0)
            bits_per_second = sum_data.get('bits_per_second', 0)
            bandwidth_mbps = bits_per_second / 1_000_000
            
            # UDP-specific metrics
            jitter_ms = 0
            lost_packets = 0
            total_packets = 0
            lost_percent = 0
            
            streams = end.get('streams', [])
            if streams:
                udp_data = streams[0].get('udp', {})
                jitter_ms = udp_data.get('jitter_ms', 0)
                lost_packets = udp_data.get('lost_packets', 0)
                total_packets = udp_data.get('packets', 0)
                lost_percent = udp_data.get('lost_percent', 0)
            
            packets_received = total_packets - lost_packets
            
            # Estimate latency (simplified)
            latency_ms = jitter_ms * 2
            
            # Determine SLA status
            sla_status = self._check_sla(slice_name, {
                'bandwidth_mbps': bandwidth_mbps,
                'latency_ms': latency_ms,
                'jitter_ms': jitter_ms,
                'packet_loss_pct': lost_percent
            })
            
            return SliceMetric(
                timestamp=datetime.utcnow().isoformat() + 'Z',
                slice_name=slice_name,
                bandwidth_mbps=round(bandwidth_mbps, 3),
                latency_ms=round(latency_ms, 3),
                jitter_ms=round(jitter_ms, 3),
                packet_loss_pct=round(lost_percent, 3),
                packets_sent=total_packets,
                packets_received=packets_received,
                bytes_transferred=bytes_transferred,
                sla_status=sla_status
            )
            
        except Exception as e:
            logger.error(f"Error parsing iperf data: {e}")
            return None
    
    def _check_sla(self, slice_name: str, metrics: Dict) -> str:
        """
        Check if metrics comply with SLA requirements.
        
        Returns:
            "compliant" or "violated"
        """
        # SLA thresholds
        sla_requirements = {
            'URLLC': {
                'min_bandwidth_mbps': 5,
                'max_latency_ms': 5,
                'max_jitter_ms': 1,
                'max_packet_loss_pct': 0.001
            },
            'eMBB': {
                'min_bandwidth_mbps': 50,
                'max_latency_ms': 20,
                'max_jitter_ms': 5,
                'max_packet_loss_pct': 1.0
            },
            'mMTC': {
                'min_bandwidth_mbps': 1,
                'max_latency_ms': 100,
                'max_jitter_ms': 20,
                'max_packet_loss_pct': 1.0
            }
        }
        
        sla = sla_requirements.get(slice_name)
        if not sla:
            return "unknown"
        
        violations = []
        
        if metrics['bandwidth_mbps'] < sla['min_bandwidth_mbps']:
            violations.append('bandwidth')
        if metrics['latency_ms'] > sla['max_latency_ms']:
            violations.append('latency')
        if metrics['jitter_ms'] > sla['max_jitter_ms']:
            violations.append('jitter')
        if metrics['packet_loss_pct'] > sla['max_packet_loss_pct']:
            violations.append('packet_loss')
        
        return "violated" if violations else "compliant"
    
    def _export_metrics(self):
        """Export collected metrics to files and Logstash."""
        # Export flow metrics
        if self.flow_metrics:
            self._write_metrics_file(
                'flow_metrics.json',
                [m.to_dict() for m in self.flow_metrics[-100:]]  # Last 100
            )
            self._send_to_logstash(self.flow_metrics[-10:])  # Last 10
        
        # Export slice metrics
        if self.slice_metrics:
            self._write_metrics_file(
                'slice_metrics.json',
                [m.to_dict() for m in self.slice_metrics[-100:]]
            )
            self._send_to_logstash(self.slice_metrics[-10:])
    
    def _write_metrics_file(self, filename: str, metrics: List[Dict]):
        """Write metrics to JSON file (newline-delimited)."""
        filepath = self.output_dir / filename
        
        with open(filepath, 'a') as f:
            for metric in metrics:
                f.write(json.dumps(metric) + '\n')
    
    def _send_to_logstash(self, metrics: List):
        """Send metrics to Logstash via HTTP."""
        for metric in metrics:
            try:
                response = requests.post(
                    self.LOGSTASH_HTTP,
                    json=metric.to_dict() if hasattr(metric, 'to_dict') else metric,
                    timeout=2
                )
                if response.status_code != 200:
                    logger.debug(f"Logstash returned {response.status_code}")
            except requests.exceptions.RequestException:
                pass  # Logstash may not be available
    
    def collect_once(self) -> Dict[str, Any]:
        """
        Perform a single collection cycle and return results.
        
        Returns:
            Dictionary with collected metrics
        """
        self._collect_controller_metrics()
        self._collect_iperf_metrics()
        
        return {
            'flow_metrics': [m.to_dict() for m in self.flow_metrics[-10:]],
            'slice_metrics': [m.to_dict() for m in self.slice_metrics[-10:]],
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary of collected metrics.
        
        Returns:
            Summary statistics
        """
        summary = {
            'total_flow_metrics': len(self.flow_metrics),
            'total_slice_metrics': len(self.slice_metrics),
            'slices': {}
        }
        
        # Aggregate by slice
        for slice_name in ['URLLC', 'eMBB', 'mMTC']:
            slice_data = [m for m in self.slice_metrics 
                         if m.slice_name == slice_name]
            
            if slice_data:
                avg_bw = sum(m.bandwidth_mbps for m in slice_data) / len(slice_data)
                avg_lat = sum(m.latency_ms for m in slice_data) / len(slice_data)
                violations = sum(1 for m in slice_data 
                               if m.sla_status == 'violated')
                
                summary['slices'][slice_name] = {
                    'samples': len(slice_data),
                    'avg_bandwidth_mbps': round(avg_bw, 3),
                    'avg_latency_ms': round(avg_lat, 3),
                    'sla_violations': violations
                }
        
        return summary


def main():
    """Main entry point for standalone execution."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='5G Network Slicing Metrics Collector'
    )
    parser.add_argument(
        '--interval', '-i',
        type=int,
        default=5,
        help='Collection interval in seconds (default: 5)'
    )
    parser.add_argument(
        '--duration', '-d',
        type=int,
        default=60,
        help='Collection duration in seconds (default: 60)'
    )
    parser.add_argument(
        '--output', '-o',
        default='monitoring/metrics',
        help='Output directory for metrics files'
    )
    parser.add_argument(
        '--once',
        action='store_true',
        help='Collect once and exit'
    )
    
    args = parser.parse_args()
    
    collector = MetricsCollector(output_dir=args.output)
    collector.COLLECTION_INTERVAL = args.interval
    
    if args.once:
        # Single collection
        results = collector.collect_once()
        print(json.dumps(results, indent=2))
    else:
        # Continuous collection
        collector.start()
        
        try:
            logger.info(f"Collecting for {args.duration} seconds...")
            time.sleep(args.duration)
        except KeyboardInterrupt:
            logger.info("Interrupted")
        
        collector.stop()
        
        # Print summary
        summary = collector.get_summary()
        print("\n=== Collection Summary ===")
        print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
