"""
Real-time Trade Monitoring

WebSocket-based monitoring system with sub-second updates.
Recommended for live trading with immediate execution capabilities.
"""

# Note: Individual modules can be imported directly due to optional dependencies
# from .realtime_automated_monitor import RealtimeAutomatedMonitor
# from .supabase_realtime import SupabaseRealtime
# from .websocket_manager import WebSocketManager

__all__ = [
    'RealtimeAutomatedMonitor',
    'SupabaseRealtime', 
    'WebSocketManager'
]