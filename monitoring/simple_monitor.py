#!/usr/bin/env python3
"""
Simple Monitoring Dashboard for 5G Network Slicing
===================================================
Lightweight monitoring solution that doesn't require Docker/ELK.
Displays real-time metrics in terminal and generates HTML reports.
"""

import json
import time
import os
import sys
from datetime import datetime
from collections import defaultdict
import threading

# ANSI colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

class SimpleMonitor:
    """Simple real-time monitoring for 5G network slices."""
    
    def __init__(self, metrics_dir="monitoring/metrics"):
        self.metrics_dir = metrics_dir
        self.slice_metrics = defaultdict(list)
        self.running = False
        
        # SLA thresholds
        self.sla_thresholds = {
            'urllc': {'bandwidth': 50, 'latency': 1, 'jitter': 0.1, 'packet_loss': 0.001},
            'embb': {'bandwidth': 100, 'latency': 10, 'jitter': 2, 'packet_loss': 0.01},
            'mmtc': {'bandwidth': 1, 'latency': 100, 'jitter': 10, 'packet_loss': 0.1}
        }
        
        os.makedirs(metrics_dir, exist_ok=True)
        os.makedirs("monitoring/reports", exist_ok=True)
    
    def clear_screen(self):
        """Clear terminal screen."""
        os.system('clear' if os.name != 'nt' else 'cls')
    
    def check_sla(self, slice_type, metrics):
        """Check if metrics meet SLA requirements."""
        violations = []
        thresholds = self.sla_thresholds.get(slice_type, {})
        
        if metrics.get('bandwidth', 0) < thresholds.get('bandwidth', 0):
            violations.append(f"Bandwidth: {metrics.get('bandwidth', 0):.2f} < {thresholds['bandwidth']} Mbps")
        if metrics.get('latency', 0) > thresholds.get('latency', float('inf')):
            violations.append(f"Latency: {metrics.get('latency', 0):.2f} > {thresholds['latency']} ms")
        if metrics.get('jitter', 0) > thresholds.get('jitter', float('inf')):
            violations.append(f"Jitter: {metrics.get('jitter', 0):.3f} > {thresholds['jitter']} ms")
        if metrics.get('packet_loss', 0) > thresholds.get('packet_loss', 1):
            violations.append(f"Packet Loss: {metrics.get('packet_loss', 0)*100:.3f}% > {thresholds['packet_loss']*100}%")
        
        return violations
    
    def get_status_color(self, violations):
        """Get color based on SLA status."""
        if not violations:
            return Colors.GREEN
        elif len(violations) <= 2:
            return Colors.YELLOW
        return Colors.RED
    
    def display_dashboard(self):
        """Display real-time dashboard in terminal."""
        self.clear_screen()
        
        print(f"{Colors.BOLD}{Colors.CYAN}")
        print("=" * 80)
        print("        5G NETWORK SLICING - REAL-TIME MONITORING DASHBOARD")
        print("=" * 80)
        print(f"{Colors.ENDC}")
        print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  Press Ctrl+C to stop monitoring")
        print()
        
        for slice_type in ['urllc', 'embb', 'mmtc']:
            metrics = self.slice_metrics.get(slice_type, [{}])[-1] if self.slice_metrics.get(slice_type) else {}
            violations = self.check_sla(slice_type, metrics)
            status_color = self.get_status_color(violations)
            status = "✓ OK" if not violations else f"✗ {len(violations)} VIOLATION(S)"
            
            # Slice header
            slice_names = {'urllc': 'URLLC (Ultra-Reliable Low Latency)', 
                          'embb': 'eMBB (Enhanced Mobile Broadband)',
                          'mmtc': 'mMTC (Massive Machine Type Comm.)'}
            
            print(f"{Colors.BOLD}┌{'─' * 78}┐{Colors.ENDC}")
            print(f"{Colors.BOLD}│ {slice_names.get(slice_type, slice_type):40} {status_color}{status:>35}{Colors.ENDC} │")
            print(f"{Colors.BOLD}├{'─' * 78}┤{Colors.ENDC}")
            
            if metrics:
                bw = metrics.get('bandwidth', 0)
                lat = metrics.get('latency', 0)
                jit = metrics.get('jitter', 0)
                pl = metrics.get('packet_loss', 0) * 100
                
                # Create bar charts
                bw_bar = self._create_bar(bw, self.sla_thresholds[slice_type]['bandwidth'] * 2)
                lat_bar = self._create_bar(lat, self.sla_thresholds[slice_type]['latency'] * 2, reverse=True)
                
                print(f"│  Bandwidth:    {bw:8.2f} Mbps  {bw_bar:40} │")
                print(f"│  Latency:      {lat:8.2f} ms    {lat_bar:40} │")
                print(f"│  Jitter:       {jit:8.3f} ms                                              │")
                print(f"│  Packet Loss:  {pl:8.4f} %                                              │")
                
                if violations:
                    print(f"│  {Colors.RED}SLA Violations:{Colors.ENDC}                                                      │")
                    for v in violations:
                        print(f"│    {Colors.RED}• {v:70}{Colors.ENDC} │")
            else:
                print(f"│  {Colors.YELLOW}Waiting for metrics...{Colors.ENDC}                                               │")
            
            print(f"└{'─' * 78}┘")
            print()
    
    def _create_bar(self, value, max_val, width=30, reverse=False):
        """Create ASCII progress bar."""
        if max_val == 0:
            pct = 0
        else:
            pct = min(value / max_val, 1.0)
        
        filled = int(width * pct)
        empty = width - filled
        
        if reverse:
            # For latency: lower is better
            if pct < 0.3:
                color = Colors.GREEN
            elif pct < 0.7:
                color = Colors.YELLOW
            else:
                color = Colors.RED
        else:
            # For bandwidth: higher is better
            if pct > 0.7:
                color = Colors.GREEN
            elif pct > 0.3:
                color = Colors.YELLOW
            else:
                color = Colors.RED
        
        return f"{color}{'█' * filled}{'░' * empty}{Colors.ENDC}"
    
    def record_metrics(self, slice_type, bandwidth, latency, jitter, packet_loss):
        """Record metrics for a slice."""
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'slice_type': slice_type,
            'bandwidth': bandwidth,
            'latency': latency,
            'jitter': jitter,
            'packet_loss': packet_loss
        }
        
        self.slice_metrics[slice_type].append(metrics)
        
        # Keep only last 100 metrics per slice
        if len(self.slice_metrics[slice_type]) > 100:
            self.slice_metrics[slice_type] = self.slice_metrics[slice_type][-100:]
        
        # Save to file
        metrics_file = os.path.join(self.metrics_dir, f"{slice_type}_metrics.json")
        with open(metrics_file, 'w') as f:
            json.dump(self.slice_metrics[slice_type], f, indent=2)
    
    def load_metrics_from_files(self):
        """Load metrics from JSON files."""
        for slice_type in ['urllc', 'embb', 'mmtc']:
            metrics_file = os.path.join(self.metrics_dir, f"{slice_type}_metrics.json")
            if os.path.exists(metrics_file):
                try:
                    with open(metrics_file, 'r') as f:
                        self.slice_metrics[slice_type] = json.load(f)
                except:
                    pass
    
    def generate_html_report(self):
        """Generate HTML report with metrics."""
        html = """<!DOCTYPE html>
<html>
<head>
    <title>5G Network Slicing Report</title>
    <meta http-equiv="refresh" content="5">
    <style>
        body { font-family: Arial, sans-serif; background: #1a1a2e; color: #eee; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 { color: #00d9ff; text-align: center; }
        .slice-card { background: #16213e; border-radius: 10px; padding: 20px; margin: 20px 0; }
        .slice-header { display: flex; justify-content: space-between; align-items: center; }
        .slice-name { font-size: 1.5em; color: #00d9ff; }
        .status-ok { color: #00ff88; }
        .status-warn { color: #ffaa00; }
        .status-error { color: #ff4444; }
        .metrics { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-top: 15px; }
        .metric { background: #0f3460; padding: 15px; border-radius: 8px; text-align: center; }
        .metric-value { font-size: 2em; font-weight: bold; }
        .metric-label { color: #888; font-size: 0.9em; }
        .bar { height: 8px; background: #333; border-radius: 4px; margin-top: 10px; }
        .bar-fill { height: 100%; border-radius: 4px; }
        .timestamp { text-align: center; color: #666; margin-top: 30px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🛜 5G Network Slicing Dashboard</h1>
"""
        
        slice_names = {
            'urllc': 'URLLC - Ultra-Reliable Low Latency',
            'embb': 'eMBB - Enhanced Mobile Broadband', 
            'mmtc': 'mMTC - Massive Machine Type Communications'
        }
        
        for slice_type in ['urllc', 'embb', 'mmtc']:
            metrics = self.slice_metrics.get(slice_type, [{}])[-1] if self.slice_metrics.get(slice_type) else {}
            violations = self.check_sla(slice_type, metrics)
            
            status_class = "status-ok" if not violations else ("status-warn" if len(violations) <= 2 else "status-error")
            status_text = "✓ SLA OK" if not violations else f"✗ {len(violations)} Violation(s)"
            
            bw = metrics.get('bandwidth', 0)
            lat = metrics.get('latency', 0)
            jit = metrics.get('jitter', 0)
            pl = metrics.get('packet_loss', 0) * 100
            
            html += f"""
        <div class="slice-card">
            <div class="slice-header">
                <span class="slice-name">{slice_names[slice_type]}</span>
                <span class="{status_class}">{status_text}</span>
            </div>
            <div class="metrics">
                <div class="metric">
                    <div class="metric-value" style="color: #00d9ff;">{bw:.2f}</div>
                    <div class="metric-label">Bandwidth (Mbps)</div>
                </div>
                <div class="metric">
                    <div class="metric-value" style="color: #ffaa00;">{lat:.2f}</div>
                    <div class="metric-label">Latency (ms)</div>
                </div>
                <div class="metric">
                    <div class="metric-value" style="color: #aa88ff;">{jit:.3f}</div>
                    <div class="metric-label">Jitter (ms)</div>
                </div>
                <div class="metric">
                    <div class="metric-value" style="color: #ff6688;">{pl:.4f}</div>
                    <div class="metric-label">Packet Loss (%)</div>
                </div>
            </div>
        </div>
"""
        
        html += f"""
        <div class="timestamp">Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
    </div>
</body>
</html>
"""
        
        report_path = "monitoring/reports/dashboard.html"
        with open(report_path, 'w') as f:
            f.write(html)
        
        return report_path
    
    def run_demo(self):
        """Run with simulated metrics for demonstration."""
        import random
        
        print(f"{Colors.CYAN}Starting demo mode with simulated metrics...{Colors.ENDC}")
        print(f"{Colors.YELLOW}Press Ctrl+C to stop{Colors.ENDC}")
        time.sleep(2)
        
        self.running = True
        
        try:
            while self.running:
                # Generate simulated metrics
                for slice_type in ['urllc', 'embb', 'mmtc']:
                    if slice_type == 'urllc':
                        bw = random.uniform(45, 60)
                        lat = random.uniform(0.5, 1.5)
                        jit = random.uniform(0.05, 0.15)
                        pl = random.uniform(0, 0.002)
                    elif slice_type == 'embb':
                        bw = random.uniform(80, 120)
                        lat = random.uniform(5, 15)
                        jit = random.uniform(1, 3)
                        pl = random.uniform(0, 0.02)
                    else:  # mmtc
                        bw = random.uniform(0.5, 2)
                        lat = random.uniform(50, 150)
                        jit = random.uniform(5, 15)
                        pl = random.uniform(0, 0.15)
                    
                    self.record_metrics(slice_type, bw, lat, jit, pl)
                
                self.display_dashboard()
                self.generate_html_report()
                time.sleep(2)
                
        except KeyboardInterrupt:
            self.running = False
            print(f"\n{Colors.YELLOW}Monitoring stopped.{Colors.ENDC}")
            print(f"HTML report saved to: monitoring/reports/dashboard.html")
    
    def run_live(self):
        """Run with live metrics from files."""
        print(f"{Colors.CYAN}Starting live monitoring...{Colors.ENDC}")
        print(f"{Colors.YELLOW}Watching for metrics in {self.metrics_dir}{Colors.ENDC}")
        print(f"{Colors.YELLOW}Press Ctrl+C to stop{Colors.ENDC}")
        time.sleep(2)
        
        self.running = True
        
        try:
            while self.running:
                self.load_metrics_from_files()
                self.display_dashboard()
                self.generate_html_report()
                time.sleep(2)
                
        except KeyboardInterrupt:
            self.running = False
            print(f"\n{Colors.YELLOW}Monitoring stopped.{Colors.ENDC}")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='5G Network Slicing Monitor')
    parser.add_argument('--demo', action='store_true', help='Run with simulated metrics')
    parser.add_argument('--report', action='store_true', help='Generate HTML report only')
    args = parser.parse_args()
    
    monitor = SimpleMonitor()
    
    if args.report:
        monitor.load_metrics_from_files()
        report_path = monitor.generate_html_report()
        print(f"Report generated: {report_path}")
    elif args.demo:
        monitor.run_demo()
    else:
        monitor.run_live()


if __name__ == "__main__":
    main()
