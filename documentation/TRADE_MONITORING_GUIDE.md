# 👁️ Trade Monitoring Guide

## Overview

The Trade Monitoring module provides comprehensive position tracking with two systems: Real-time WebSocket monitoring (recommended) and Legacy polling-based monitoring (backward compatibility).

## Quick Start

```bash
# Activate environment
source /Users/jaykrish/agents/project_output/venv/bin/activate

# Real-time monitoring (RECOMMENDED)
python trade_monitoring/realtime/realtime_automated_monitor.py

# Legacy monitoring (backward compatibility)
python trade_monitoring/legacy/automated_monitor.py --execute --interval 5
```

## System Architecture

### Real-time Monitoring (RECOMMENDED)
```
trade_monitoring/realtime/
├── realtime_automated_monitor.py    # Main real-time monitoring
├── websocket_manager.py             # WebSocket connections
└── supabase_realtime.py             # Real-time database updates
```

### Legacy Monitoring (Backward Compatibility)
```
trade_monitoring/legacy/
├── automated_monitor.py             # Legacy 5-minute polling
├── monitor.py                       # Interactive dashboard
└── position_monitor.py              # Position tracking utilities
```

## System Comparison

| Feature | Real-time System | Legacy System |
|---------|------------------|---------------|
| **Update Frequency** | Sub-second | 5+ minutes |
| **Technology** | WebSocket + Redis | REST API polling |
| **Price Source** | Live WebSocket feed | Batch API calls |
| **Exit Speed** | Immediate | Delayed by interval |
| **Resource Usage** | Moderate | Low |
| **Reliability** | High (with fallback) | Depends on rate limits |
| **Recommended For** | Live trading | Monitoring only |

## Real-time Monitoring System

### Key Features
- **Sub-second Updates**: WebSocket-based price feeds
- **Automatic Failover**: REST API fallback if WebSocket fails
- **Redis Caching**: High-performance price caching
- **Real-time P&L**: Instant profit/loss calculations
- **Immediate Exits**: Sub-second exit execution

### Commands
```bash
# Basic monitoring (simulation mode)
python trade_monitoring/realtime/realtime_automated_monitor.py

# Live execution mode (⚠️ REAL MONEY)
python trade_monitoring/realtime/realtime_automated_monitor.py --execute

# Custom monitoring interval
python trade_monitoring/realtime/realtime_automated_monitor.py --interval 10

# Single monitoring cycle
python trade_monitoring/realtime/realtime_automated_monitor.py --once
```

### Configuration
```python
# Real-time monitoring settings
REALTIME_CONFIG = {
    'websocket_url': 'wss://api.dhan.co/ws',
    'redis_host': 'localhost',
    'redis_port': 6379,
    'update_frequency': 0.5,        # 500ms updates
    'max_reconnect_attempts': 10,
    'fallback_to_rest': True
}
```

## Legacy Monitoring System

### Key Features
- **Polling-based**: Configurable interval monitoring
- **Lower Resource**: Minimal system requirements
- **Batch Processing**: Efficient for large portfolios
- **Stable**: Well-tested, reliable system
- **Interactive Dashboard**: Colored terminal display

### Commands
```bash
# Basic monitoring (simulation mode)
python trade_monitoring/legacy/automated_monitor.py

# Live execution mode
python trade_monitoring/legacy/automated_monitor.py --execute --interval 5

# Interactive dashboard
python trade_monitoring/legacy/monitor.py --continuous

# Single monitoring cycle
python trade_monitoring/legacy/automated_monitor.py --once
```

### Configuration
```python
# Legacy monitoring settings
LEGACY_CONFIG = {
    'default_interval': 300,        # 5-minute intervals
    'max_concurrent_requests': 10,
    'request_timeout': 30,
    'batch_size': 50
}
```

## Monitoring Process Flow

### 1. Position Discovery
- **Database Query**: Fetch active positions from trades table
- **Status Filtering**: Only monitor ACTIVE positions
- **Instrument Mapping**: Map positions to tradeable instruments

### 2. Price Fetching
- **Real-time**: WebSocket feeds with Redis caching
- **Legacy**: REST API batch requests
- **Error Handling**: Fallback mechanisms for failed requests

### 3. P&L Calculation
```python
# P&L calculation logic
current_pnl = (current_price - entry_price) * quantity * multiplier
pnl_percentage = (current_pnl / position_value) * 100
```

### 4. Exit Evaluation
- **Profit Targets**: Multiple scaling levels (25%, 50%, 75%)
- **Stop Losses**: Percentage and absolute thresholds
- **Time Exits**: DTE-based exit triggers
- **Greek Limits**: Delta, gamma exposure limits

### 5. Exit Execution
- **Automatic Execution**: Based on exit conditions
- **Safety Checks**: Multiple validation layers
- **Order Placement**: Via trade execution module
- **Confirmation**: Real-time status updates

## Exit Conditions

### Profit Targets
```python
PROFIT_TARGETS = {
    'primary': 0.5,           # 50% profit target
    'scaling': [0.25, 0.5, 0.75],  # Scaling exit levels
    'trailing_stop': 0.2      # 20% trailing stop
}
```

### Stop Losses
```python
STOP_LOSSES = {
    'percentage': -0.5,       # -50% stop loss
    'absolute': -25000,       # ₹25k absolute stop
    'time_based': 7          # Exit if loss > threshold with < 7 DTE
}
```

### Time Exits
```python
TIME_EXITS = {
    'primary_dte': 7,         # Primary exit at 7 DTE
    'theta_threshold': 21,    # Theta decay threshold
    'max_holding_period': 45  # Maximum days in trade
}
```

## Position Display

### Real-time Dashboard
```
📊 POSITION MONITOR - Real-time Mode
===============================================
RELIANCE Long Call (ID: 1234)
Entry: ₹45.50  Current: ₹52.30  P&L: ₹6.80 (+14.9%)
Status: 🟢 MONITOR  DTE: 12  Urgency: NORMAL
```

### Portfolio Summary
```
💰 PORTFOLIO SUMMARY
================================
Total Positions: 15
Current Value: ₹14,85,320
Total P&L: ₹1,23,450 (+9.07%)
Winning: 12  Losing: 3
```

## Alert System

### Urgency Levels
- **🔴 HIGH**: Immediate attention required (stop loss hit)
- **🟡 MEDIUM**: Important (approaching targets/stops)
- **🟢 NORMAL**: Informational (regular monitoring)

### Alert Types
```python
ALERT_TYPES = {
    'profit_target_hit': 'HIGH',
    'stop_loss_triggered': 'HIGH',
    'approaching_target': 'MEDIUM',
    'time_exit_warning': 'MEDIUM',
    'position_update': 'NORMAL'
}
```

## Safety Features

### Multi-level Safety
- **Simulation Mode**: Default mode, no real trades
- **Alert-only Mode**: Monitoring without execution
- **Explicit Execute Flag**: `--execute` required for live trading

### Risk Controls
```python
RISK_CONTROLS = {
    'duplicate_exit_prevention': True,
    'max_loss_limits': True,
    'position_size_validation': True,
    'market_hours_verification': True
}
```

### Audit Trail
- **Complete Logging**: All actions logged to files
- **Database Records**: Exit executions stored in database
- **Status History**: Position status change tracking

## Integration Points

### ← Trade Execution
Monitors positions created by the trade execution module.

### → Exit Execution
Triggers exit orders through the trade execution module when conditions are met.

### Database Dependencies
- **Trades Table**: Source of positions to monitor
- **Real-time Updates**: Live database change notifications
- **Exit History**: Records of all exit executions

## Common Use Cases

### 1. Continuous Monitoring
```bash
# Set and forget monitoring
python trade_monitoring/realtime/realtime_automated_monitor.py --execute
```

### 2. Alert-only Monitoring
```bash
# Generate alerts without execution
python trade_monitoring/legacy/automated_monitor.py --alert-only --interval 10
```

### 3. Interactive Monitoring
```bash
# Manual monitoring with dashboard
python trade_monitoring/legacy/monitor.py --continuous
```

### 4. Testing/Development
```bash
# Test monitoring without real money
python trade_monitoring/realtime/realtime_automated_monitor.py --once
```

## Performance Optimization

### Real-time System
- **Connection Pooling**: Efficient WebSocket management
- **Redis Caching**: Sub-millisecond price lookups
- **Batch Updates**: Efficient database operations
- **Async Processing**: Non-blocking operations

### Legacy System
- **Request Batching**: Multiple symbols per API call
- **Intelligent Caching**: Reduce redundant API calls
- **Parallel Processing**: Concurrent position monitoring
- **Rate Limit Management**: API call optimization

## Troubleshooting

### Real-time System Issues
**WebSocket Disconnections**:
- Auto-reconnection logic
- Fallback to REST API
- Redis cache maintains continuity

**High CPU Usage**:
- Adjust update frequency
- Enable selective monitoring
- Use batch processing

### Legacy System Issues
**Slow Updates**:
- Reduce monitoring interval
- Increase batch sizes
- Optimize database queries

**API Rate Limits**:
- Increase intervals between calls
- Implement request queuing
- Use request batching

### General Issues
**Database Connectivity**:
- Check network connectivity
- Verify database credentials
- Review connection pooling

**Position Sync Issues**:
- Manual position reconciliation
- Database integrity checks
- Re-sync from execution records

## Advanced Features

### Custom Exit Strategies
```python
# Example custom exit logic
def custom_exit_logic(position):
    if position.strategy_type == 'Iron Condor':
        return evaluate_iron_condor_exit(position)
    elif position.is_trending():
        return evaluate_trending_exit(position)
```

### Portfolio-level Monitoring
- **Greek Exposure**: Monitor portfolio-level Greeks
- **Sector Exposure**: Industry concentration tracking
- **Risk Metrics**: VaR, maximum drawdown monitoring

### Performance Analytics
- **Exit Timing**: Analyze optimal exit timing
- **P&L Attribution**: Track profit sources
- **Strategy Performance**: Monitor strategy effectiveness

**👁️ Trade Monitoring: Vigilant, intelligent position management with real-time precision**