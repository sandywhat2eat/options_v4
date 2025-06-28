"""
Legacy Trade Monitoring

Polling-based monitoring system with configurable intervals.
Maintained for backward compatibility and non-critical monitoring.
"""

# Note: Individual modules can be imported directly due to optional dependencies
# from .automated_monitor import AutomatedMonitor
# from .position_monitor import PositionMonitor

__all__ = [
    'AutomatedMonitor',
    'PositionMonitor'
]