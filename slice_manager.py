#!/usr/bin/env python3
"""
5G Network Slice Manager
========================
Manages slice definitions, SLA parameters, and SLA violation detection.

Slice Types:
- URLLC (Ultra-Reliable Low-Latency Communication)
- eMBB (Enhanced Mobile Broadband)
- mMTC (Massive Machine Type Communication)

SLA Parameters:
- Bandwidth (minimum guaranteed, Mbps)
- Latency (maximum allowed, ms)
- Jitter (maximum allowed, ms)
- Packet Loss (maximum allowed, %)

Author: SDN-5G Project
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('SliceManager')


class SliceType(Enum):
    """Enumeration of supported 5G slice types."""
    URLLC = "URLLC"    # Ultra-Reliable Low-Latency Communication
    EMBB = "eMBB"      # Enhanced Mobile Broadband
    MMTC = "mMTC"      # Massive Machine Type Communication


class SLAStatus(Enum):
    """SLA compliance status."""
    COMPLIANT = "compliant"
    VIOLATED = "violated"
    UNKNOWN = "unknown"


@dataclass
class SLARequirements:
    """
    SLA requirements for a network slice.
    
    Attributes:
        min_bandwidth_mbps: Minimum guaranteed bandwidth (Mbps)
        max_latency_ms: Maximum allowed latency (ms)
        max_jitter_ms: Maximum allowed jitter (ms)
        max_packet_loss_pct: Maximum allowed packet loss (%)
    """
    min_bandwidth_mbps: float
    max_latency_ms: float
    max_jitter_ms: float
    max_packet_loss_pct: float
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class SliceConfig:
    """
    Complete configuration for a network slice.
    
    Attributes:
        name: Slice name (URLLC, eMBB, mMTC)
        slice_type: Type of slice
        port: UDP destination port for traffic classification
        dscp: DSCP value for QoS marking
        sla: SLA requirements
        priority: Slice priority (higher = more important)
        description: Human-readable description
    """
    name: str
    slice_type: SliceType
    port: int
    dscp: int
    sla: SLARequirements
    priority: int
    description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'slice_type': self.slice_type.value,
            'port': self.port,
            'dscp': self.dscp,
            'sla': self.sla.to_dict(),
            'priority': self.priority,
            'description': self.description
        }


@dataclass
class SLAViolation:
    """
    Record of an SLA violation.
    
    Attributes:
        slice_name: Name of the affected slice
        violation_type: Type of violation (bandwidth, latency, jitter, loss)
        expected_value: Expected SLA value
        actual_value: Actual measured value
        timestamp: When the violation occurred
        severity: Severity level (minor, major, critical)
    """
    slice_name: str
    violation_type: str
    expected_value: float
    actual_value: float
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    severity: str = "minor"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class SliceManager:
    """
    Manager for 5G network slices and SLA enforcement.
    
    Provides:
    - Slice configuration management
    - SLA validation and violation detection
    - Metrics collection and reporting
    """
    
    # Default SLA definitions per slice type
    DEFAULT_SLAS = {
        SliceType.URLLC: SLARequirements(
            min_bandwidth_mbps=5.0,
            max_latency_ms=5.0,
            max_jitter_ms=1.0,
            max_packet_loss_pct=0.001  # 0.001% = ultra-reliable
        ),
        SliceType.EMBB: SLARequirements(
            min_bandwidth_mbps=50.0,
            max_latency_ms=20.0,
            max_jitter_ms=5.0,
            max_packet_loss_pct=1.0
        ),
        SliceType.MMTC: SLARequirements(
            min_bandwidth_mbps=1.0,
            max_latency_ms=100.0,
            max_jitter_ms=20.0,
            max_packet_loss_pct=1.0
        )
    }
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize the Slice Manager.
        
        Args:
            config_dir: Directory containing slice configuration files
        """
        self.config_dir = Path(config_dir) if config_dir else Path('config')
        self.slices: Dict[str, SliceConfig] = {}
        self.violations: List[SLAViolation] = []
        self.violation_counts: Dict[str, int] = {}
        
        # Initialize default slices
        self._init_default_slices()
        
        logger.info("SliceManager initialized")
        logger.info(f"Loaded {len(self.slices)} slice configurations")
    
    def _init_default_slices(self):
        """Initialize default slice configurations."""
        # URLLC Slice
        self.slices['URLLC'] = SliceConfig(
            name='URLLC',
            slice_type=SliceType.URLLC,
            port=5001,
            dscp=46,  # Expedited Forwarding (EF)
            sla=self.DEFAULT_SLAS[SliceType.URLLC],
            priority=100,
            description='Ultra-Reliable Low-Latency Communication for critical applications'
        )
        
        # eMBB Slice
        self.slices['eMBB'] = SliceConfig(
            name='eMBB',
            slice_type=SliceType.EMBB,
            port=5002,
            dscp=34,  # Assured Forwarding (AF41)
            sla=self.DEFAULT_SLAS[SliceType.EMBB],
            priority=50,
            description='Enhanced Mobile Broadband for high-throughput applications'
        )
        
        # mMTC Slice
        self.slices['mMTC'] = SliceConfig(
            name='mMTC',
            slice_type=SliceType.MMTC,
            port=5003,
            dscp=10,  # Assured Forwarding (AF11)
            sla=self.DEFAULT_SLAS[SliceType.MMTC],
            priority=10,
            description='Massive Machine Type Communication for IoT devices'
        )
        
        # Initialize violation counts
        for name in self.slices:
            self.violation_counts[name] = 0
    
    def get_slice_config(self, slice_name: str) -> Optional[SliceConfig]:
        """
        Get configuration for a specific slice.
        
        Args:
            slice_name: Name of the slice (URLLC, eMBB, mMTC)
        
        Returns:
            SliceConfig or None if not found
        """
        return self.slices.get(slice_name)
    
    def get_all_slices(self) -> Dict[str, SliceConfig]:
        """
        Get all slice configurations.
        
        Returns:
            Dictionary of all slice configurations
        """
        return self.slices.copy()
    
    def get_sla(self, slice_name: str) -> Optional[SLARequirements]:
        """
        Get SLA requirements for a specific slice.
        
        Args:
            slice_name: Name of the slice
        
        Returns:
            SLARequirements or None if not found
        """
        config = self.slices.get(slice_name)
        return config.sla if config else None
    
    def check_sla(self, slice_name: str, metrics: Dict[str, float]) -> Dict[str, Any]:
        """
        Check if current metrics comply with slice SLA.
        
        Args:
            slice_name: Name of the slice
            metrics: Dictionary with measured metrics:
                - bandwidth_mbps: Measured bandwidth
                - latency_ms: Measured latency
                - jitter_ms: Measured jitter
                - packet_loss_pct: Measured packet loss
        
        Returns:
            Dictionary with:
                - status: SLAStatus (compliant/violated)
                - violations: List of specific violations
                - details: Detailed comparison
        """
        config = self.slices.get(slice_name)
        if not config:
            return {
                'status': SLAStatus.UNKNOWN,
                'violations': [],
                'details': {'error': f'Unknown slice: {slice_name}'}
            }
        
        sla = config.sla
        violations = []
        details = {}
        
        # Check bandwidth (minimum requirement)
        bandwidth = metrics.get('bandwidth_mbps', 0)
        details['bandwidth'] = {
            'required_min': sla.min_bandwidth_mbps,
            'actual': bandwidth,
            'compliant': bandwidth >= sla.min_bandwidth_mbps
        }
        if bandwidth < sla.min_bandwidth_mbps:
            violation = SLAViolation(
                slice_name=slice_name,
                violation_type='bandwidth',
                expected_value=sla.min_bandwidth_mbps,
                actual_value=bandwidth,
                severity=self._get_severity(
                    sla.min_bandwidth_mbps, bandwidth, 'min'
                )
            )
            violations.append(violation)
        
        # Check latency (maximum requirement)
        latency = metrics.get('latency_ms', 0)
        details['latency'] = {
            'required_max': sla.max_latency_ms,
            'actual': latency,
            'compliant': latency <= sla.max_latency_ms
        }
        if latency > sla.max_latency_ms:
            violation = SLAViolation(
                slice_name=slice_name,
                violation_type='latency',
                expected_value=sla.max_latency_ms,
                actual_value=latency,
                severity=self._get_severity(
                    sla.max_latency_ms, latency, 'max'
                )
            )
            violations.append(violation)
        
        # Check jitter (maximum requirement)
        jitter = metrics.get('jitter_ms', 0)
        details['jitter'] = {
            'required_max': sla.max_jitter_ms,
            'actual': jitter,
            'compliant': jitter <= sla.max_jitter_ms
        }
        if jitter > sla.max_jitter_ms:
            violation = SLAViolation(
                slice_name=slice_name,
                violation_type='jitter',
                expected_value=sla.max_jitter_ms,
                actual_value=jitter,
                severity=self._get_severity(
                    sla.max_jitter_ms, jitter, 'max'
                )
            )
            violations.append(violation)
        
        # Check packet loss (maximum requirement)
        packet_loss = metrics.get('packet_loss_pct', 0)
        details['packet_loss'] = {
            'required_max': sla.max_packet_loss_pct,
            'actual': packet_loss,
            'compliant': packet_loss <= sla.max_packet_loss_pct
        }
        if packet_loss > sla.max_packet_loss_pct:
            violation = SLAViolation(
                slice_name=slice_name,
                violation_type='packet_loss',
                expected_value=sla.max_packet_loss_pct,
                actual_value=packet_loss,
                severity=self._get_severity(
                    sla.max_packet_loss_pct, packet_loss, 'max'
                )
            )
            violations.append(violation)
        
        # Update violation tracking
        if violations:
            self.violations.extend(violations)
            self.violation_counts[slice_name] += len(violations)
        
        # Determine overall status
        status = SLAStatus.COMPLIANT if not violations else SLAStatus.VIOLATED
        
        return {
            'status': status,
            'violations': [v.to_dict() for v in violations],
            'details': details
        }
    
    def _get_severity(self, expected: float, actual: float, 
                      requirement_type: str) -> str:
        """
        Determine violation severity based on deviation.
        
        Args:
            expected: Expected SLA value
            actual: Actual measured value
            requirement_type: 'min' for minimum or 'max' for maximum
        
        Returns:
            Severity level: 'minor', 'major', or 'critical'
        """
        if expected == 0:
            return 'critical'
        
        if requirement_type == 'min':
            # For minimum requirements (e.g., bandwidth)
            ratio = actual / expected
            if ratio >= 0.8:
                return 'minor'
            elif ratio >= 0.5:
                return 'major'
            else:
                return 'critical'
        else:
            # For maximum requirements (e.g., latency)
            ratio = actual / expected
            if ratio <= 1.2:
                return 'minor'
            elif ratio <= 2.0:
                return 'major'
            else:
                return 'critical'
    
    def get_violation_summary(self) -> Dict[str, Any]:
        """
        Get summary of all SLA violations.
        
        Returns:
            Dictionary with violation statistics
        """
        summary = {
            'total_violations': len(self.violations),
            'violations_by_slice': self.violation_counts.copy(),
            'violations_by_type': {},
            'severity_distribution': {
                'minor': 0,
                'major': 0,
                'critical': 0
            }
        }
        
        # Count by type and severity
        for v in self.violations:
            vtype = v.violation_type
            summary['violations_by_type'][vtype] = \
                summary['violations_by_type'].get(vtype, 0) + 1
            summary['severity_distribution'][v.severity] += 1
        
        return summary
    
    def clear_violations(self):
        """Clear all recorded violations."""
        self.violations = []
        for name in self.violation_counts:
            self.violation_counts[name] = 0
        logger.info("Violations cleared")
    
    def export_config(self, output_path: str):
        """
        Export all slice configurations to JSON file.
        
        Args:
            output_path: Path to output file
        """
        config_data = {
            name: config.to_dict() 
            for name, config in self.slices.items()
        }
        
        with open(output_path, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        logger.info(f"Configuration exported to {output_path}")
    
    def export_violations(self, output_path: str):
        """
        Export all violations to JSON file.
        
        Args:
            output_path: Path to output file
        """
        violations_data = {
            'summary': self.get_violation_summary(),
            'violations': [v.to_dict() for v in self.violations]
        }
        
        with open(output_path, 'w') as f:
            json.dump(violations_data, f, indent=2)
        
        logger.info(f"Violations exported to {output_path}")
    
    def get_slice_by_port(self, port: int) -> Optional[str]:
        """
        Get slice name by UDP port.
        
        Args:
            port: UDP destination port
        
        Returns:
            Slice name or None
        """
        for name, config in self.slices.items():
            if config.port == port:
                return name
        return None
    
    def format_sla_report(self, slice_name: str) -> str:
        """
        Generate a formatted SLA report for a slice.
        
        Args:
            slice_name: Name of the slice
        
        Returns:
            Formatted string report
        """
        config = self.slices.get(slice_name)
        if not config:
            return f"Unknown slice: {slice_name}"
        
        sla = config.sla
        violations = self.violation_counts.get(slice_name, 0)
        
        report = f"""
╔══════════════════════════════════════════════════════════════╗
║ SLA Report: {config.name:48} ║
╠══════════════════════════════════════════════════════════════╣
║ Description: {config.description[:45]:45} ║
║ Priority: {config.priority:<51} ║
║ DSCP Value: {config.dscp:<49} ║
║ UDP Port: {config.port:<51} ║
╠══════════════════════════════════════════════════════════════╣
║ SLA Requirements:                                            ║
║   • Min Bandwidth: {sla.min_bandwidth_mbps:>8.1f} Mbps                          ║
║   • Max Latency:   {sla.max_latency_ms:>8.1f} ms                            ║
║   • Max Jitter:    {sla.max_jitter_ms:>8.1f} ms                            ║
║   • Max Pkt Loss:  {sla.max_packet_loss_pct:>8.3f} %                           ║
╠══════════════════════════════════════════════════════════════╣
║ Violations Count: {violations:<42} ║
╚══════════════════════════════════════════════════════════════╝
"""
        return report


# Convenience function for module-level access
_manager_instance: Optional[SliceManager] = None


def get_slice_manager() -> SliceManager:
    """Get the singleton SliceManager instance."""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = SliceManager()
    return _manager_instance


def get_slice_config(slice_name: str) -> Optional[Dict[str, Any]]:
    """
    Convenience function to get slice configuration.
    
    Args:
        slice_name: Name of the slice
    
    Returns:
        Slice configuration as dictionary
    """
    manager = get_slice_manager()
    config = manager.get_slice_config(slice_name)
    return config.to_dict() if config else None


def check_sla(slice_name: str, metrics: Dict[str, float]) -> Dict[str, Any]:
    """
    Convenience function to check SLA compliance.
    
    Args:
        slice_name: Name of the slice
        metrics: Measured metrics dictionary
    
    Returns:
        SLA check result
    """
    manager = get_slice_manager()
    return manager.check_sla(slice_name, metrics)


# Main entry point for testing
if __name__ == '__main__':
    # Create manager
    manager = SliceManager()
    
    # Print SLA reports
    for name in ['URLLC', 'eMBB', 'mMTC']:
        print(manager.format_sla_report(name))
    
    # Test SLA checking
    print("\n=== Testing SLA Compliance ===\n")
    
    # Good metrics (compliant)
    good_metrics = {
        'bandwidth_mbps': 10.0,
        'latency_ms': 2.0,
        'jitter_ms': 0.5,
        'packet_loss_pct': 0.0
    }
    result = manager.check_sla('URLLC', good_metrics)
    print(f"URLLC with good metrics: {result['status'].value}")
    
    # Bad metrics (violated)
    bad_metrics = {
        'bandwidth_mbps': 2.0,  # Below 5 Mbps minimum
        'latency_ms': 10.0,     # Above 5 ms maximum
        'jitter_ms': 2.0,       # Above 1 ms maximum
        'packet_loss_pct': 0.0
    }
    result = manager.check_sla('URLLC', bad_metrics)
    print(f"URLLC with bad metrics: {result['status'].value}")
    print(f"Violations: {len(result['violations'])}")
    
    # Summary
    print("\n=== Violation Summary ===")
    print(json.dumps(manager.get_violation_summary(), indent=2))
