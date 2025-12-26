#!/usr/bin/env python3
"""
5G Network Slicing Mininet Topology
====================================
Custom Mininet topology for 5G network slicing simulation.

Topology Structure:
                    
    [urllc_h1]──┐                    ┌──[server]
                │                    │
    [embb_h1]───┼──[s1]────[s2]────[s3]
                │    │              │
    [mmtc_h1]───┘    └─────────────┘

Hosts:
- urllc_h1: URLLC slice client (Ultra-Reliable Low-Latency)
- embb_h1: eMBB slice client (Enhanced Mobile Broadband)
- mmtc_h1: mMTC slice client (Massive Machine Type Communication)
- server: Traffic destination (runs iperf3 servers)

Switches:
- s1: Access switch (connects slice hosts)
- s2: Core switch (central routing)
- s3: Edge switch (connects to server)

Uses RemoteController for Ryu SDN controller connection.

Author: SDN-5G Project
"""

import sys
import time
from mininet.net import Mininet
from mininet.node import RemoteController, OVSKernelSwitch
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.log import setLogLevel, info, error


class NetworkSlicingTopology:
    """
    5G Network Slicing Topology Manager.
    
    Creates and manages a Mininet topology optimized for
    network slicing experiments with SDN control.
    """
    
    # Controller configuration
    CONTROLLER_IP = '127.0.0.1'
    CONTROLLER_PORT = 6653
    
    # Host IP configuration (10.0.0.0/24 subnet)
    HOST_IPS = {
        'urllc_h1': '10.0.0.1',
        'embb_h1': '10.0.0.2',
        'mmtc_h1': '10.0.0.3',
        'server': '10.0.0.100'
    }
    
    # Link parameters for TCLink (optional QoS at link level)
    LINK_CONFIG = {
        'default': {
            'bw': 1000,      # 1 Gbps capacity
            'delay': '1ms',  # 1ms base delay
            'loss': 0,       # No packet loss
            'max_queue_size': 1000
        },
        'access': {
            'bw': 100,       # 100 Mbps access links
            'delay': '2ms',
            'loss': 0,
            'max_queue_size': 500
        }
    }
    
    def __init__(self, controller_ip=None, controller_port=None):
        """
        Initialize the topology manager.
        
        Args:
            controller_ip: SDN controller IP address
            controller_port: SDN controller port
        """
        self.controller_ip = controller_ip or self.CONTROLLER_IP
        self.controller_port = controller_port or self.CONTROLLER_PORT
        self.net = None
        self.hosts = {}
        self.switches = {}
        
        info(f"*** Topology manager initialized\n")
        info(f"*** Controller: {self.controller_ip}:{self.controller_port}\n")
    
    def create_topology(self, use_tc_links=True):
        """
        Create the Mininet network topology.
        
        Args:
            use_tc_links: Whether to use TCLink for QoS-aware links
        
        Returns:
            Mininet: The created network object
        """
        info("*** Creating 5G Network Slicing Topology\n")
        
        # Select link type
        link_cls = TCLink if use_tc_links else None
        
        # Create Mininet with remote controller
        self.net = Mininet(
            controller=RemoteController,
            switch=OVSKernelSwitch,
            link=link_cls,
            autoSetMacs=True,
            autoStaticArp=True
        )
        
        # Add remote controller
        info("*** Adding SDN Controller\n")
        controller = self.net.addController(
            'c0',
            controller=RemoteController,
            ip=self.controller_ip,
            port=self.controller_port,
            protocols='OpenFlow13'
        )
        
        # Create switches
        info("*** Creating switches\n")
        self._create_switches()
        
        # Create hosts
        info("*** Creating hosts\n")
        self._create_hosts()
        
        # Create links
        info("*** Creating links\n")
        self._create_links(use_tc_links)
        
        return self.net
    
    def _create_switches(self):
        """Create OVS switches with OpenFlow 1.3 support."""
        switch_names = ['s1', 's2', 's3']
        
        for name in switch_names:
            # Create switch with OpenFlow 1.3 protocol
            switch = self.net.addSwitch(
                name,
                cls=OVSKernelSwitch,
                protocols='OpenFlow13',
                failMode='secure'  # Secure mode requires controller
            )
            self.switches[name] = switch
            info(f"    Added switch: {name}\n")
    
    def _create_hosts(self):
        """Create slice hosts and server."""
        for name, ip in self.HOST_IPS.items():
            host = self.net.addHost(
                name,
                ip=f"{ip}/24",
                defaultRoute=None
            )
            self.hosts[name] = host
            info(f"    Added host: {name} ({ip})\n")
    
    def _create_links(self, use_tc_links=True):
        """
        Create network links between nodes.
        
        Link topology:
        - Access links: slice hosts <-> s1
        - Core links: s1 <-> s2, s2 <-> s3
        - Redundant link: s1 <-> s3 (for resilience)
        - Server link: s3 <-> server
        """
        # Access links (hosts to access switch s1)
        access_config = self.LINK_CONFIG['access'] if use_tc_links else {}
        
        for host_name in ['urllc_h1', 'embb_h1', 'mmtc_h1']:
            if use_tc_links:
                self.net.addLink(
                    self.hosts[host_name],
                    self.switches['s1'],
                    bw=access_config['bw'],
                    delay=access_config['delay'],
                    loss=access_config['loss'],
                    max_queue_size=access_config['max_queue_size']
                )
            else:
                self.net.addLink(self.hosts[host_name], self.switches['s1'])
            info(f"    Link: {host_name} <-> s1\n")
        
        # Core links (switch to switch)
        core_config = self.LINK_CONFIG['default'] if use_tc_links else {}
        
        switch_links = [
            ('s1', 's2'),  # Access to core
            ('s2', 's3'),  # Core to edge
            ('s1', 's3')   # Redundant path
        ]
        
        for sw1, sw2 in switch_links:
            if use_tc_links:
                self.net.addLink(
                    self.switches[sw1],
                    self.switches[sw2],
                    bw=core_config['bw'],
                    delay=core_config['delay'],
                    loss=core_config['loss'],
                    max_queue_size=core_config['max_queue_size']
                )
            else:
                self.net.addLink(self.switches[sw1], self.switches[sw2])
            info(f"    Link: {sw1} <-> {sw2}\n")
        
        # Server link
        if use_tc_links:
            self.net.addLink(
                self.switches['s3'],
                self.hosts['server'],
                bw=core_config['bw'],
                delay=core_config['delay'],
                loss=core_config['loss'],
                max_queue_size=core_config['max_queue_size']
            )
        else:
            self.net.addLink(self.switches['s3'], self.hosts['server'])
        info("    Link: s3 <-> server\n")
    
    def start(self):
        """Start the network."""
        if self.net is None:
            error("*** Network not created. Call create_topology() first.\n")
            return False
        
        info("*** Starting network\n")
        self.net.start()
        
        # Wait for controller connection
        info("*** Waiting for controller connection...\n")
        time.sleep(3)
        
        # Verify connectivity
        info("*** Testing basic connectivity\n")
        self._test_connectivity()
        
        return True
    
    def _test_connectivity(self):
        """Test basic network connectivity."""
        # Ping from each slice host to server
        server = self.hosts['server']
        server_ip = self.HOST_IPS['server']
        
        for host_name in ['urllc_h1', 'embb_h1', 'mmtc_h1']:
            host = self.hosts[host_name]
            result = host.cmd(f'ping -c 1 -W 2 {server_ip}')
            if '1 received' in result:
                info(f"    {host_name} -> server: OK\n")
            else:
                info(f"    {host_name} -> server: FAILED\n")
    
    def start_iperf_servers(self):
        """
        Start iperf3 servers on the server host.
        
        Starts three iperf3 server instances on different ports:
        - Port 5001: URLLC traffic
        - Port 5002: eMBB traffic
        - Port 5003: mMTC traffic
        """
        info("*** Starting iperf3 servers\n")
        server = self.hosts['server']
        
        # Kill any existing iperf3 processes
        server.cmd('pkill -9 iperf3')
        time.sleep(1)
        
        # Start iperf3 servers on slice ports
        ports = [5001, 5002, 5003]
        slice_names = ['URLLC', 'eMBB', 'mMTC']
        
        for port, name in zip(ports, slice_names):
            # Start iperf3 server in background
            server.cmd(f'iperf3 -s -p {port} -D --logfile /tmp/iperf3_{name}.log')
            info(f"    iperf3 server started on port {port} ({name})\n")
        
        time.sleep(1)
        
        # Verify servers are running
        result = server.cmd('pgrep -a iperf3')
        info(f"    Running iperf3 processes: {result.count('iperf3')}\n")
    
    def stop_iperf_servers(self):
        """Stop all iperf3 servers."""
        info("*** Stopping iperf3 servers\n")
        server = self.hosts['server']
        server.cmd('pkill -9 iperf3')
    
    def run_cli(self):
        """Open Mininet CLI for interactive commands."""
        info("*** Opening Mininet CLI\n")
        info("*** Type 'exit' to quit\n")
        CLI(self.net)
    
    def stop(self):
        """Stop the network and clean up."""
        info("*** Stopping network\n")
        if self.net:
            self.stop_iperf_servers()
            self.net.stop()
            self.net = None
    
    def get_host(self, name):
        """Get a host by name."""
        return self.hosts.get(name)
    
    def get_switch(self, name):
        """Get a switch by name."""
        return self.switches.get(name)
    
    def get_server_ip(self):
        """Get the server IP address."""
        return self.HOST_IPS['server']


def main():
    """Main entry point for standalone topology execution."""
    setLogLevel('info')
    
    info("=" * 60 + "\n")
    info("5G Network Slicing Topology\n")
    info("=" * 60 + "\n")
    
    # Parse command line arguments
    controller_ip = '127.0.0.1'
    controller_port = 6653
    
    if len(sys.argv) > 1:
        controller_ip = sys.argv[1]
    if len(sys.argv) > 2:
        controller_port = int(sys.argv[2])
    
    # Create topology manager
    topo = NetworkSlicingTopology(controller_ip, controller_port)
    
    try:
        # Create and start network
        topo.create_topology(use_tc_links=True)
        topo.start()
        
        # Start iperf3 servers
        topo.start_iperf_servers()
        
        # Open CLI for interactive use
        topo.run_cli()
        
    except Exception as e:
        error(f"*** Error: {e}\n")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up
        topo.stop()
        info("*** Network stopped\n")


if __name__ == '__main__':
    main()
