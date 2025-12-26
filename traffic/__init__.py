# traffic/__init__.py
"""
Traffic generation module for 5G Network Slicing.

Provides:
- TrafficGenerator: Main class for iperf3-based traffic generation
- TrafficConfig: Configuration dataclass for traffic parameters
- load_profiles: Function to load traffic profiles from JSON files
"""

from .traffic_generator import (
    TrafficGenerator,
    TrafficConfig,
    load_profiles,
    run_experiment
)

__all__ = [
    'TrafficGenerator',
    'TrafficConfig',
    'load_profiles',
    'run_experiment'
]
