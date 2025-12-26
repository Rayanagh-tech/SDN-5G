#!/usr/bin/env python3
"""
5G Network Slicing Traffic Generator
=====================================
Generates realistic traffic for network slicing experiments using iperf3.

Traffic Types:
- URLLC: Small packets, high frequency, low latency requirements
- eMBB: Large packets, high throughput, multiple parallel streams
- mMTC: Periodic small packets, low bandwidth IoT-like traffic

Features:
- Loads traffic profiles from JSON configuration
- Executes iperf3 with appropriate parameters
- Supports parallel traffic generation for multiple slices
- Collects and exports iperf3 results in JSON format

Author: SDN-5G Project
"""

import json
import subprocess
import threading
import logging
import time
from pathlib import Path
from typing import Dict, Optional, List, Any
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('TrafficGenerator')


@dataclass
class TrafficConfig:
    """Configuration for traffic generation."""
    slice_name: str
    server_ip: str
    port: int
    bitrate: str        # e.g., "5M", "50M", "1M"
    packet_size: int    # UDP packet size in bytes
    duration: int       # Duration in seconds
    interval: float     # Reporting interval
    parallel: int = 1   # Number of parallel streams
    reverse: bool = False  # Reverse mode (server sends)


class TrafficGenerator:
    """
    Manages traffic generation using iperf3.
    
    Supports:
    - Multiple concurrent traffic streams
    - Customizable traffic patterns
    - JSON result collection
    """
    
    # Default iperf3 binary path
    IPERF3_BIN = 'iperf3'
    
    # Output directory for results
    OUTPUT_DIR = Path('/tmp')
    
    def __init__(self, output_dir: Optional[Path] = None):
        """
        Initialize the traffic generator.
        
        Args:
            output_dir: Directory for iperf3 output files
        """
        self.output_dir = output_dir or self.OUTPUT_DIR
        self.active_processes: Dict[str, subprocess.Popen] = {}
        self.results: Dict[str, Dict] = {}
        
        logger.info("TrafficGenerator initialized")
    
    def start_traffic(self, slice_name: str, server_ip: str, port: int,
                     bitrate: str, packet_size: int, duration: int,
                     interval: float = 1.0, parallel: int = 1) -> bool:
        """
        Start traffic generation for a slice.
        
        Args:
            slice_name: Name of the slice (URLLC, eMBB, mMTC)
            server_ip: IP address of the iperf3 server
            port: UDP destination port
            bitrate: Target bitrate (e.g., "5M" for 5 Mbps)
            packet_size: UDP datagram size in bytes
            duration: Test duration in seconds
            interval: Reporting interval in seconds
            parallel: Number of parallel streams
        
        Returns:
            True if started successfully, False otherwise
        """
        if slice_name in self.active_processes:
            logger.warning(f"Traffic for {slice_name} already running")
            return False
        
        # Build iperf3 command
        output_file = self.output_dir / f'iperf3_{slice_name}.json'
        
        cmd = [
            self.IPERF3_BIN,
            '-c', server_ip,           # Client mode, connect to server
            '-p', str(port),           # Server port
            '-u',                      # UDP mode
            '-b', bitrate,             # Target bitrate
            '-l', str(packet_size),    # UDP packet length
            '-t', str(duration),       # Duration
            '-i', str(interval),       # Reporting interval
            '-P', str(parallel),       # Parallel streams
            '--json',                  # JSON output
            '--logfile', str(output_file)  # Output file
        ]
        
        logger.info(f"Starting traffic for {slice_name}:")
        logger.info(f"  Server: {server_ip}:{port}")
        logger.info(f"  Bitrate: {bitrate}, Packet size: {packet_size} bytes")
        logger.info(f"  Duration: {duration}s, Streams: {parallel}")
        logger.info(f"  Command: {' '.join(cmd)}")
        
        try:
            # Start iperf3 process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            self.active_processes[slice_name] = process
            logger.info(f"Traffic started for {slice_name} (PID: {process.pid})")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start traffic for {slice_name}: {e}")
            return False
    
    def start_traffic_from_config(self, config: TrafficConfig) -> bool:
        """
        Start traffic generation from a TrafficConfig object.
        
        Args:
            config: TrafficConfig object
        
        Returns:
            True if started successfully
        """
        return self.start_traffic(
            slice_name=config.slice_name,
            server_ip=config.server_ip,
            port=config.port,
            bitrate=config.bitrate,
            packet_size=config.packet_size,
            duration=config.duration,
            interval=config.interval,
            parallel=config.parallel
        )
    
    def stop_traffic(self, slice_name: str) -> bool:
        """
        Stop traffic generation for a slice.
        
        Args:
            slice_name: Name of the slice
        
        Returns:
            True if stopped successfully
        """
        if slice_name not in self.active_processes:
            logger.warning(f"No active traffic for {slice_name}")
            return False
        
        process = self.active_processes[slice_name]
        
        try:
            process.terminate()
            process.wait(timeout=5)
            logger.info(f"Traffic stopped for {slice_name}")
        except subprocess.TimeoutExpired:
            process.kill()
            logger.warning(f"Traffic killed for {slice_name}")
        
        del self.active_processes[slice_name]
        return True
    
    def stop_all_traffic(self):
        """Stop all active traffic generators."""
        for slice_name in list(self.active_processes.keys()):
            self.stop_traffic(slice_name)
        logger.info("All traffic stopped")
    
    def wait_for_completion(self, timeout: Optional[int] = None) -> Dict[str, bool]:
        """
        Wait for all active traffic generators to complete.
        
        Args:
            timeout: Maximum wait time in seconds
        
        Returns:
            Dictionary of slice_name -> completion status
        """
        completion_status = {}
        
        for slice_name, process in list(self.active_processes.items()):
            try:
                process.wait(timeout=timeout)
                completion_status[slice_name] = True
                logger.info(f"Traffic completed for {slice_name}")
            except subprocess.TimeoutExpired:
                completion_status[slice_name] = False
                logger.warning(f"Traffic timeout for {slice_name}")
            
            del self.active_processes[slice_name]
        
        return completion_status
    
    def get_results(self, slice_name: str) -> Optional[Dict[str, Any]]:
        """
        Get iperf3 results for a slice.
        
        Args:
            slice_name: Name of the slice
        
        Returns:
            Parsed JSON results or None
        """
        output_file = self.output_dir / f'iperf3_{slice_name}.json'
        
        if not output_file.exists():
            logger.warning(f"No results file for {slice_name}")
            return None
        
        try:
            with open(output_file, 'r') as f:
                data = json.load(f)
            
            self.results[slice_name] = data
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {output_file}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error reading results for {slice_name}: {e}")
            return None
    
    def parse_results(self, slice_name: str) -> Optional[Dict[str, float]]:
        """
        Parse iperf3 results into simplified metrics.
        
        Args:
            slice_name: Name of the slice
        
        Returns:
            Dictionary with simplified metrics
        """
        data = self.get_results(slice_name)
        if not data:
            return None
        
        try:
            end = data.get('end', {})
            
            # Handle different iperf3 output structures
            if 'sum' in end:
                sum_data = end['sum']
            elif 'sum_sent' in end:
                sum_data = end['sum_sent']
            else:
                sum_data = {}
            
            # Extract metrics
            bytes_transferred = sum_data.get('bytes', 0)
            bits_per_second = sum_data.get('bits_per_second', 0)
            
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
            
            metrics = {
                'bandwidth_mbps': bits_per_second / 1_000_000,
                'bytes_transferred': bytes_transferred,
                'jitter_ms': jitter_ms,
                'lost_packets': lost_packets,
                'total_packets': total_packets,
                'packet_loss_pct': lost_percent
            }
            
            logger.info(f"Parsed results for {slice_name}:")
            logger.info(f"  Bandwidth: {metrics['bandwidth_mbps']:.2f} Mbps")
            logger.info(f"  Jitter: {metrics['jitter_ms']:.2f} ms")
            logger.info(f"  Packet Loss: {metrics['packet_loss_pct']:.3f}%")
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error parsing results for {slice_name}: {e}")
            return None
    
    def is_running(self, slice_name: str) -> bool:
        """Check if traffic generation is running for a slice."""
        if slice_name not in self.active_processes:
            return False
        
        process = self.active_processes[slice_name]
        return process.poll() is None
    
    def get_active_slices(self) -> List[str]:
        """Get list of slices with active traffic."""
        return [name for name in self.active_processes 
                if self.is_running(name)]


def load_profiles(profiles_dir: str = 'data-input') -> Dict[str, Dict]:
    """
    Load traffic profiles from JSON files.
    
    Args:
        profiles_dir: Directory containing profile JSON files
    
    Returns:
        Dictionary of slice_name -> profile data
    """
    profiles = {}
    profiles_path = Path(profiles_dir)
    
    profile_files = {
        'URLLC': 'latency.json',
        'eMBB': 'video.json',
        'mMTC': 'mmtc.json'
    }
    
    for slice_name, filename in profile_files.items():
        filepath = profiles_path / filename
        if filepath.exists():
            with open(filepath, 'r') as f:
                profiles[slice_name] = json.load(f)
            logger.info(f"Loaded profile: {slice_name}")
    
    return profiles


def run_experiment(server_ip: str, duration: int = 60, 
                   profiles_dir: str = 'data-input'):
    """
    Run a complete traffic generation experiment.
    
    Args:
        server_ip: IP address of the iperf3 server
        duration: Test duration in seconds
        profiles_dir: Directory containing traffic profiles
    """
    logger.info("=" * 60)
    logger.info("5G Network Slicing Traffic Generation Experiment")
    logger.info("=" * 60)
    
    # Load profiles
    profiles = load_profiles(profiles_dir)
    
    if not profiles:
        logger.error("No profiles loaded. Check profiles directory.")
        return
    
    # Create traffic generator
    generator = TrafficGenerator()
    
    # Start traffic for each slice
    for slice_name, profile in profiles.items():
        generator.start_traffic(
            slice_name=slice_name,
            server_ip=server_ip,
            port=profile.get('port', 5001),
            bitrate=profile.get('bitrate', '1M'),
            packet_size=profile.get('packet_size', 1400),
            duration=duration,
            interval=profile.get('interval', 1.0),
            parallel=profile.get('parallel', 1)
        )
    
    logger.info(f"All traffic started. Waiting {duration} seconds...")
    
    # Wait for completion
    time.sleep(duration + 5)
    generator.wait_for_completion(timeout=10)
    
    # Collect and display results
    logger.info("\n" + "=" * 60)
    logger.info("RESULTS SUMMARY")
    logger.info("=" * 60)
    
    for slice_name in profiles:
        metrics = generator.parse_results(slice_name)
        if metrics:
            print(f"\n{slice_name}:")
            print(f"  Bandwidth: {metrics['bandwidth_mbps']:.2f} Mbps")
            print(f"  Jitter: {metrics['jitter_ms']:.3f} ms")
            print(f"  Packet Loss: {metrics['packet_loss_pct']:.3f}%")
            print(f"  Total Packets: {metrics['total_packets']}")
    
    logger.info("\nExperiment completed.")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='5G Network Slicing Traffic Generator'
    )
    parser.add_argument(
        '--server', '-s',
        default='10.0.0.100',
        help='iperf3 server IP address (default: 10.0.0.100)'
    )
    parser.add_argument(
        '--duration', '-d',
        type=int,
        default=60,
        help='Test duration in seconds (default: 60)'
    )
    parser.add_argument(
        '--profiles-dir', '-p',
        default='data-input',
        help='Directory containing traffic profiles (default: data-input)'
    )
    parser.add_argument(
        '--slice',
        choices=['URLLC', 'eMBB', 'mMTC'],
        help='Run single slice test only'
    )
    
    args = parser.parse_args()
    
    if args.slice:
        # Single slice test
        profiles = load_profiles(args.profiles_dir)
        if args.slice not in profiles:
            logger.error(f"Profile not found for {args.slice}")
            return
        
        profile = profiles[args.slice]
        generator = TrafficGenerator()
        
        generator.start_traffic(
            slice_name=args.slice,
            server_ip=args.server,
            port=profile.get('port', 5001),
            bitrate=profile.get('bitrate', '1M'),
            packet_size=profile.get('packet_size', 1400),
            duration=args.duration,
            interval=profile.get('interval', 1.0),
            parallel=profile.get('parallel', 1)
        )
        
        time.sleep(args.duration + 2)
        generator.wait_for_completion(timeout=5)
        generator.parse_results(args.slice)
    else:
        # Full experiment
        run_experiment(args.server, args.duration, args.profiles_dir)


if __name__ == '__main__':
    main()
