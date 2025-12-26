#!/usr/bin/env python3
"""
5G Network Slicing Orchestrator
================================
High-level orchestration component for the 5G Network Slicing system.

Responsibilities:
1. Load traffic profiles from JSON configuration files
2. Coordinate traffic generation across slices
3. Collect and aggregate metrics from the controller
4. Send metrics to ELK stack (Logstash) for visualization
5. Detect and report SLA violations

Components:
- TrafficProfileLoader: Loads eMBB, URLLC, mMTC traffic profiles
- MetricsCollector: Gathers metrics from controller and iperf3
- ExperimentRunner: Manages experiment lifecycle

Author: SDN-5G Project
"""

import json
import time
import logging
import requests
import subprocess
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

# Import local modules
from slice_manager import SliceManager, SLAStatus

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('Orchestrator')


@dataclass
class TrafficProfile:
    """
    Traffic profile definition loaded from JSON.
    
    Attributes:
        slice_name: Name of the slice (URLLC, eMBB, mMTC)
        bitrate: Target bitrate for iperf3 (e.g., "50M")
        packet_size: UDP packet size in bytes
        duration: Test duration in seconds
        interval: Reporting interval in seconds
        port: UDP destination port
        parallel: Number of parallel streams
    """
    slice_name: str
    bitrate: str
    packet_size: int
    duration: int
    interval: float
    port: int
    parallel: int = 1
    description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class TrafficProfileLoader:
    """
    Loads traffic profiles from JSON configuration files.
    """
    
    DEFAULT_PROFILES_DIR = 'data-input'
    
    def __init__(self, profiles_dir: Optional[str] = None):
        """
        Initialize the profile loader.
        
        Args:
            profiles_dir: Directory containing traffic profile JSON files
        """
        self.profiles_dir = Path(profiles_dir or self.DEFAULT_PROFILES_DIR)
        self.profiles: Dict[str, TrafficProfile] = {}
        
        logger.info(f"TrafficProfileLoader initialized: {self.profiles_dir}")
    
    def load_all_profiles(self) -> Dict[str, TrafficProfile]:
        """
        Load all traffic profiles from the profiles directory.
        
        Returns:
            Dictionary of slice_name -> TrafficProfile
        """
        profile_files = {
            'URLLC': 'latency.json',
            'eMBB': 'video.json',
            'mMTC': 'mmtc.json'
        }
        
        for slice_name, filename in profile_files.items():
            filepath = self.profiles_dir / filename
            if filepath.exists():
                profile = self.load_profile(filepath, slice_name)
                if profile:
                    self.profiles[slice_name] = profile
                    logger.info(f"Loaded profile: {slice_name} from {filename}")
            else:
                logger.warning(f"Profile file not found: {filepath}")
        
        return self.profiles
    
    def load_profile(self, filepath: Path, slice_name: str) -> Optional[TrafficProfile]:
        """
        Load a single traffic profile from JSON file.
        
        Args:
            filepath: Path to the JSON file
            slice_name: Name of the slice
        
        Returns:
            TrafficProfile or None if loading fails
        """
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            profile = TrafficProfile(
                slice_name=slice_name,
                bitrate=data.get('bitrate', '1M'),
                packet_size=data.get('packet_size', 1400),
                duration=data.get('duration', 60),
                interval=data.get('interval', 1.0),
                port=data.get('port', 5001),
                parallel=data.get('parallel', 1),
                description=data.get('description', '')
            )
            
            return profile
            
        except Exception as e:
            logger.error(f"Error loading profile {filepath}: {e}")
            return None
    
    def get_profile(self, slice_name: str) -> Optional[TrafficProfile]:
        """Get a loaded profile by slice name."""
        return self.profiles.get(slice_name)


@dataclass
class SliceMetrics:
    """
    Aggregated metrics for a network slice.
    """
    slice_name: str
    bandwidth_mbps: float
    latency_ms: float
    jitter_ms: float
    packet_loss_pct: float
    packets_sent: int
    packets_received: int
    bytes_transferred: int
    sla_status: str
    timestamp: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON export."""
        return asdict(self)


class MetricsCollector:
    """
    Collects and aggregates metrics from various sources.
    
    Sources:
    - Controller flow statistics (via REST API)
    - iperf3 results (JSON output)
    - System metrics
    """
    
    CONTROLLER_API_BASE = 'http://127.0.0.1:8080'
    LOGSTASH_ENDPOINT = 'http://127.0.0.1:5044'
    
    def __init__(self, slice_manager: SliceManager):
        """
        Initialize the metrics collector.
        
        Args:
            slice_manager: SliceManager instance for SLA checking
        """
        self.slice_manager = slice_manager
        self.metrics_history: Dict[str, List[SliceMetrics]] = {
            'URLLC': [],
            'eMBB': [],
            'mMTC': []
        }
        self.output_dir = Path('monitoring/metrics')
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("MetricsCollector initialized")
    
    def collect_controller_stats(self) -> Dict[str, Any]:
        """
        Collect flow statistics from the Ryu controller REST API.
        
        Returns:
            Dictionary of flow statistics
        """
        try:
            # Get flow stats from Ryu REST API
            response = requests.get(
                f'{self.CONTROLLER_API_BASE}/stats/flow/1',
                timeout=5
            )
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Controller API returned {response.status_code}")
                return {}
        except requests.exceptions.RequestException as e:
            logger.debug(f"Controller API not available: {e}")
            return {}
    
    def parse_iperf3_output(self, output_file: Path) -> Optional[Dict[str, Any]]:
        """
        Parse iperf3 JSON output file.
        
        Args:
            output_file: Path to iperf3 JSON output
        
        Returns:
            Parsed metrics dictionary
        """
        try:
            with open(output_file, 'r') as f:
                data = json.load(f)
            
            # Extract end summary
            end = data.get('end', {})
            sum_data = end.get('sum', end.get('sum_sent', {}))
            
            # UDP streams have different structure
            streams = end.get('streams', [])
            if streams:
                udp_data = streams[0].get('udp', {})
                return {
                    'bytes': sum_data.get('bytes', 0),
                    'bits_per_second': sum_data.get('bits_per_second', 0),
                    'jitter_ms': udp_data.get('jitter_ms', 0),
                    'lost_packets': udp_data.get('lost_packets', 0),
                    'packets': udp_data.get('packets', 0),
                    'lost_percent': udp_data.get('lost_percent', 0)
                }
            
            return {
                'bytes': sum_data.get('bytes', 0),
                'bits_per_second': sum_data.get('bits_per_second', 0),
                'jitter_ms': 0,
                'lost_packets': 0,
                'packets': 0,
                'lost_percent': 0
            }
            
        except Exception as e:
            logger.error(f"Error parsing iperf3 output {output_file}: {e}")
            return None
    
    def aggregate_metrics(self, slice_name: str, 
                         iperf_data: Optional[Dict[str, Any]] = None,
                         controller_data: Optional[Dict[str, Any]] = None) -> SliceMetrics:
        """
        Aggregate metrics from multiple sources.
        
        Args:
            slice_name: Name of the slice
            iperf_data: iperf3 results
            controller_data: Controller flow statistics
        
        Returns:
            Aggregated SliceMetrics object
        """
        timestamp = datetime.utcnow().isoformat() + 'Z'
        
        # Default values
        bandwidth_mbps = 0.0
        latency_ms = 0.0
        jitter_ms = 0.0
        packet_loss_pct = 0.0
        packets_sent = 0
        packets_received = 0
        bytes_transferred = 0
        
        # Process iperf3 data
        if iperf_data:
            bits_per_second = iperf_data.get('bits_per_second', 0)
            bandwidth_mbps = bits_per_second / 1_000_000
            jitter_ms = iperf_data.get('jitter_ms', 0)
            packet_loss_pct = iperf_data.get('lost_percent', 0)
            packets_sent = iperf_data.get('packets', 0)
            lost_packets = iperf_data.get('lost_packets', 0)
            packets_received = packets_sent - lost_packets
            bytes_transferred = iperf_data.get('bytes', 0)
        
        # Process controller data (if available)
        if controller_data:
            # Controller provides byte counts which can supplement iperf3 data
            pass
        
        # Estimate latency from jitter (simplified model)
        # In real deployment, use ping or other latency measurement
        latency_ms = jitter_ms * 2  # Rough estimate
        
        # Check SLA compliance
        metrics_dict = {
            'bandwidth_mbps': bandwidth_mbps,
            'latency_ms': latency_ms,
            'jitter_ms': jitter_ms,
            'packet_loss_pct': packet_loss_pct
        }
        sla_result = self.slice_manager.check_sla(slice_name, metrics_dict)
        sla_status = sla_result['status'].value
        
        # Create metrics object
        metrics = SliceMetrics(
            slice_name=slice_name,
            bandwidth_mbps=round(bandwidth_mbps, 3),
            latency_ms=round(latency_ms, 3),
            jitter_ms=round(jitter_ms, 3),
            packet_loss_pct=round(packet_loss_pct, 3),
            packets_sent=packets_sent,
            packets_received=packets_received,
            bytes_transferred=bytes_transferred,
            sla_status=sla_status,
            timestamp=timestamp
        )
        
        # Store in history
        self.metrics_history[slice_name].append(metrics)
        
        return metrics
    
    def export_metrics_json(self, metrics: SliceMetrics):
        """
        Export metrics to JSON file for Logstash ingestion.
        
        Args:
            metrics: SliceMetrics to export
        """
        output_file = self.output_dir / 'slice_metrics.json'
        
        # Append as newline-delimited JSON
        with open(output_file, 'a') as f:
            f.write(json.dumps(metrics.to_dict()) + '\n')
    
    def send_to_logstash(self, metrics: SliceMetrics) -> bool:
        """
        Send metrics to Logstash via HTTP.
        
        Args:
            metrics: SliceMetrics to send
        
        Returns:
            True if successful, False otherwise
        """
        try:
            response = requests.post(
                self.LOGSTASH_ENDPOINT,
                json=metrics.to_dict(),
                timeout=5
            )
            return response.status_code == 200
        except requests.exceptions.RequestException as e:
            logger.debug(f"Logstash not available: {e}")
            return False
    
    def get_latest_metrics(self, slice_name: str) -> Optional[SliceMetrics]:
        """Get the most recent metrics for a slice."""
        history = self.metrics_history.get(slice_name, [])
        return history[-1] if history else None
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics for all slices.
        
        Returns:
            Dictionary with summary for each slice
        """
        summary = {}
        
        for slice_name, history in self.metrics_history.items():
            if not history:
                summary[slice_name] = {'samples': 0}
                continue
            
            # Calculate averages
            avg_bandwidth = sum(m.bandwidth_mbps for m in history) / len(history)
            avg_latency = sum(m.latency_ms for m in history) / len(history)
            avg_jitter = sum(m.jitter_ms for m in history) / len(history)
            avg_loss = sum(m.packet_loss_pct for m in history) / len(history)
            
            # Count SLA violations
            violations = sum(1 for m in history if m.sla_status == 'violated')
            
            summary[slice_name] = {
                'samples': len(history),
                'avg_bandwidth_mbps': round(avg_bandwidth, 3),
                'avg_latency_ms': round(avg_latency, 3),
                'avg_jitter_ms': round(avg_jitter, 3),
                'avg_packet_loss_pct': round(avg_loss, 3),
                'sla_violations': violations,
                'compliance_rate': round((len(history) - violations) / len(history) * 100, 1)
            }
        
        return summary


class ExperimentRunner:
    """
    Manages the experiment lifecycle.
    
    Coordinates:
    - Traffic profile loading
    - Traffic generation
    - Metrics collection
    - Results export
    """
    
    def __init__(self):
        """Initialize the experiment runner."""
        self.slice_manager = SliceManager()
        self.profile_loader = TrafficProfileLoader()
        self.metrics_collector = MetricsCollector(self.slice_manager)
        
        self.running = False
        self.experiment_start_time = None
        self.experiment_results = {}
        
        # Load traffic profiles
        self.profiles = self.profile_loader.load_all_profiles()
        
        logger.info("ExperimentRunner initialized")
    
    def start_experiment(self, duration: int = 60, 
                        slices: Optional[List[str]] = None):
        """
        Start a network slicing experiment.
        
        Args:
            duration: Experiment duration in seconds
            slices: List of slices to test (default: all)
        """
        if self.running:
            logger.warning("Experiment already running")
            return
        
        slices = slices or ['URLLC', 'eMBB', 'mMTC']
        
        logger.info(f"Starting experiment: duration={duration}s, slices={slices}")
        
        self.running = True
        self.experiment_start_time = datetime.utcnow()
        
        # Clear previous violations
        self.slice_manager.clear_violations()
        
        # Start metrics collection thread
        collection_thread = threading.Thread(
            target=self._collect_metrics_loop,
            args=(duration,),
            daemon=True
        )
        collection_thread.start()
        
        # Run experiment
        try:
            self._run_traffic_tests(slices, duration)
        finally:
            self.running = False
        
        # Wait for collection to finish
        collection_thread.join(timeout=5)
        
        # Generate results
        self._generate_results()
        
        logger.info("Experiment completed")
    
    def _run_traffic_tests(self, slices: List[str], duration: int):
        """
        Run traffic tests for specified slices.
        
        Uses the traffic_generator module to launch iperf3 tests.
        """
        from traffic.traffic_generator import TrafficGenerator
        
        generator = TrafficGenerator()
        
        # Start all traffic generators
        for slice_name in slices:
            profile = self.profiles.get(slice_name)
            if profile:
                logger.info(f"Starting traffic for {slice_name}")
                generator.start_traffic(
                    slice_name=slice_name,
                    server_ip='10.0.0.100',
                    port=profile.port,
                    bitrate=profile.bitrate,
                    packet_size=profile.packet_size,
                    duration=duration,
                    interval=profile.interval
                )
        
        # Wait for tests to complete
        time.sleep(duration + 5)
        
        # Collect results
        for slice_name in slices:
            output_file = Path(f'/tmp/iperf3_{slice_name}.json')
            if output_file.exists():
                iperf_data = self.metrics_collector.parse_iperf3_output(output_file)
                if iperf_data:
                    metrics = self.metrics_collector.aggregate_metrics(
                        slice_name, iperf_data
                    )
                    self.metrics_collector.export_metrics_json(metrics)
                    logger.info(f"{slice_name} metrics collected: "
                               f"{metrics.bandwidth_mbps} Mbps, "
                               f"SLA: {metrics.sla_status}")
    
    def _collect_metrics_loop(self, duration: int):
        """
        Background thread for periodic metrics collection.
        
        Args:
            duration: How long to collect metrics
        """
        end_time = time.time() + duration
        
        while time.time() < end_time and self.running:
            # Collect controller stats
            controller_stats = self.metrics_collector.collect_controller_stats()
            
            # Log progress
            elapsed = time.time() - (end_time - duration)
            logger.info(f"Experiment progress: {elapsed:.0f}/{duration}s")
            
            time.sleep(5)  # Collect every 5 seconds
    
    def _generate_results(self):
        """Generate experiment results summary."""
        self.experiment_results = {
            'start_time': self.experiment_start_time.isoformat(),
            'end_time': datetime.utcnow().isoformat(),
            'metrics_summary': self.metrics_collector.get_metrics_summary(),
            'sla_summary': self.slice_manager.get_violation_summary()
        }
        
        # Export results
        output_file = Path('monitoring/metrics/experiment_results.json')
        with open(output_file, 'w') as f:
            json.dump(self.experiment_results, f, indent=2)
        
        # Print summary
        self._print_summary()
    
    def _print_summary(self):
        """Print experiment summary to console."""
        print("\n" + "=" * 70)
        print("EXPERIMENT RESULTS SUMMARY")
        print("=" * 70)
        
        metrics_summary = self.experiment_results['metrics_summary']
        sla_summary = self.experiment_results['sla_summary']
        
        for slice_name in ['URLLC', 'eMBB', 'mMTC']:
            m = metrics_summary.get(slice_name, {})
            print(f"\n{slice_name}:")
            print(f"  Samples: {m.get('samples', 0)}")
            print(f"  Avg Bandwidth: {m.get('avg_bandwidth_mbps', 0):.2f} Mbps")
            print(f"  Avg Latency: {m.get('avg_latency_ms', 0):.2f} ms")
            print(f"  Avg Jitter: {m.get('avg_jitter_ms', 0):.2f} ms")
            print(f"  Avg Packet Loss: {m.get('avg_packet_loss_pct', 0):.3f}%")
            print(f"  SLA Compliance: {m.get('compliance_rate', 0):.1f}%")
        
        print(f"\nTotal SLA Violations: {sla_summary['total_violations']}")
        print("=" * 70 + "\n")
    
    def stop_experiment(self):
        """Stop a running experiment."""
        if self.running:
            logger.info("Stopping experiment")
            self.running = False
    
    def get_results(self) -> Dict[str, Any]:
        """Get experiment results."""
        return self.experiment_results


def main():
    """Main entry point for the orchestrator."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='5G Network Slicing Orchestrator'
    )
    parser.add_argument(
        '--duration', '-d',
        type=int,
        default=60,
        help='Experiment duration in seconds (default: 60)'
    )
    parser.add_argument(
        '--slices', '-s',
        nargs='+',
        default=['URLLC', 'eMBB', 'mMTC'],
        help='Slices to test (default: all)'
    )
    parser.add_argument(
        '--profiles-dir', '-p',
        default='data-input',
        help='Directory containing traffic profiles'
    )
    
    args = parser.parse_args()
    
    logger.info("5G Network Slicing Orchestrator")
    logger.info(f"Duration: {args.duration}s, Slices: {args.slices}")
    
    # Create and run experiment
    runner = ExperimentRunner()
    runner.profile_loader.profiles_dir = Path(args.profiles_dir)
    runner.profiles = runner.profile_loader.load_all_profiles()
    
    try:
        runner.start_experiment(
            duration=args.duration,
            slices=args.slices
        )
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        runner.stop_experiment()
    except Exception as e:
        logger.error(f"Experiment failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Print final results
    results = runner.get_results()
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
