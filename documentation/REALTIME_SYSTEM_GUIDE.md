# Real-time Trading System Implementation

## Overview

This implementation adds real-time capabilities to the existing options trading system, transforming it from a polling-based (5-minute intervals) system to a hybrid real-time system with sub-second exit triggers.

## Key Improvements

### Before (Polling System)
- ⏰ **Exit Speed**: Up to 5-minute delay
- 📊 **Market Data**: REST API every 5 minutes
- 💾 **Position Tracking**: Database queries each cycle
- 🔄 **Trade Updates**: Periodic checks

### After (Real-time System)
- ⚡ **Exit Speed**: Sub-second triggers
- 📈 **Market Data**: WebSocket streaming + REST fallback
- 💨 **Position Tracking**: In-memory cache with real-time updates
- 🔔 **Trade Updates**: Instant database change notifications

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                Real-time Trading System                     │
├─────────────────────┬───────────────────┬───────────────────┤
│   Market Data       │   Position Cache   │   Database        │
│                     │                   │   Integration     │
│ WebSocket Manager   │ Position Cache    │ Supabase Realtime │
│ ├─ Dhan Feed       │ Manager           │ ├─ Trade Updates  │
│ ├─ Price Cache     │ ├─ In-memory      │ ├─ Strategy       │
│ └─ Reconnection    │ ├─ Real-time P&L  │ │   Changes       │
│                     │ └─ Database Sync  │ └─ Exit Levels    │
├─────────────────────┴───────────────────┴───────────────────┤
│              Realtime Automated Monitor                     │
│        ├─ Event-driven Exit Evaluation                     │
│        ├─ Instant Order Execution                          │
│        └─ Hybrid Polling + Real-time Mode                  │
└─────────────────────────────────────────────────────────────┘
```

## Components Implemented

### 1. WebSocket Manager (`core/websocket_manager.py`)
- **Purpose**: Manages Dhan live market feed WebSocket connections
- **Features**:
  - Auto-reconnection with exponential backoff
  - Instrument subscription management
  - Price caching (Redis + in-memory fallback)
  - Event-driven price update notifications

### 2. Supabase Realtime (`core/supabase_realtime.py`)
- **Purpose**: Real-time database change notifications
- **Features**:
  - Trade table change subscriptions
  - Strategy and exit level monitoring
  - Event-driven position updates
  - Connection management

### 3. Position Cache Manager (`core/position_cache_manager.py`)
- **Purpose**: In-memory position tracking with real-time P&L
- **Features**:
  - Fast position lookups
  - Real-time price updates and P&L calculation
  - Database synchronization
  - Security-to-position mapping for efficient updates

### 4. Realtime Market Fetcher (`data_scripts/realtime_market_fetcher.py`)
- **Purpose**: Enhanced market data with WebSocket streaming
- **Features**:
  - WebSocket price streaming
  - REST API fallback
  - Unified interface for both real-time and batch price queries
  - Connection status monitoring

### 5. Realtime Automated Monitor (`realtime_automated_monitor.py`)
- **Purpose**: Main monitoring system with real-time capabilities
- **Features**:
  - Event-driven exit evaluation
  - Instant price-based triggers
  - Hybrid polling + real-time mode
  - Graceful fallback to REST-only mode

## Usage

### Basic Usage

```bash
# Install new dependencies
pip install websockets redis asyncio-mqtt uvloop

# Run in simulation mode (recommended for testing)
python realtime_automated_monitor.py

# Run with real-time features but no WebSocket (REST only)
python realtime_automated_monitor.py --no-websocket

# Run in LIVE mode (executes actual trades)
python realtime_automated_monitor.py --execute

# Run once and exit (useful for testing)
python realtime_automated_monitor.py --once
```

### Testing

```bash
# Run integration tests
python test_realtime_integration.py

# Run system demo (5-minute simulation)
python demo_realtime_system.py

# Run demo in live mode (USE WITH CAUTION)
python demo_realtime_system.py --mode live --duration 2
```

## Configuration

### Environment Variables
The system uses the same `.env` configuration as the existing system:

```env
# Dhan API (required for WebSocket feed)
DHAN_CLIENT_ID=your_client_id
DHAN_ACCESS_TOKEN=your_access_token

# Supabase (required for realtime subscriptions)
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

### Optional: Redis Cache
For production deployments, install and configure Redis for better performance:

```bash
# Install Redis (macOS)
brew install redis
redis-server

# The system will automatically use Redis if available,
# otherwise falls back to in-memory caching
```

## Performance Improvements

### Exit Execution Speed
- **Before**: 0-300 seconds (5-minute maximum delay)
- **After**: 0-1 seconds (sub-second triggers)

### Risk Management
- **Before**: Snapshot-based, periodic risk assessment
- **After**: Continuous risk monitoring with instant alerts

### Scalability
- **Before**: REST API rate limits (~10 requests/minute)
- **After**: Single WebSocket for unlimited positions

### Resource Usage
- **Before**: High API usage, periodic database queries
- **After**: Minimal API usage, efficient caching, real-time updates

## Fallback Mechanisms

The system is designed with multiple fallback layers:

1. **WebSocket → REST**: If WebSocket fails, automatically falls back to REST API
2. **Redis → In-memory**: If Redis is unavailable, uses in-memory caching
3. **Real-time → Polling**: If real-time features fail, continues with polling
4. **Live → Simulation**: Easy switch between live and simulation modes

## Monitoring and Logging

### Log Files
- `logs/realtime_automated_monitor.log`: Main system log
- `logs/exit_executions.json`: Exit execution records
- `logs/position_monitor.log`: Position monitoring events

### Real-time Statistics
The system provides comprehensive statistics:
- Connection health
- Cache performance
- Exit execution success rates
- Price update frequency
- Error tracking

## Migration from Existing System

### Compatibility
- ✅ **Full backward compatibility** with existing automated_monitor.py
- ✅ **Same database schema** - no changes required
- ✅ **Same API credentials** - uses existing Dhan/Supabase config
- ✅ **Same exit logic** - enhanced with real-time triggers

### Migration Steps
1. **Install dependencies**: `pip install -r requirements.txt`
2. **Test integration**: `python test_realtime_integration.py`
3. **Run demo**: `python demo_realtime_system.py`
4. **Switch gradually**: Run both systems in parallel initially
5. **Full migration**: Replace scheduled automated_monitor.py with realtime version

## Production Deployment

### Recommended Setup
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up Redis (optional but recommended)
sudo systemctl start redis

# 3. Run with systemd or supervisor
python realtime_automated_monitor.py --execute --interval 300
```

### Monitoring
- Monitor log files for connection health
- Set up alerts for exit execution failures
- Track cache hit ratios for performance optimization
- Monitor WebSocket connection stability

## Troubleshooting

### Common Issues

1. **WebSocket Connection Fails**
   - Check Dhan API credentials
   - Verify network connectivity
   - System automatically falls back to REST

2. **Supabase Realtime Issues**
   - Check Supabase URL and key
   - Verify database permissions
   - System continues with polling fallback

3. **Redis Connection Issues**
   - Check Redis server status
   - System automatically uses in-memory fallback

4. **High Memory Usage**
   - Adjust position cache sync interval
   - Monitor position count
   - Consider Redis for large deployments

### Performance Tuning

- **Cache Sync Interval**: Adjust based on position count (default: 60s)
- **Price Update Throttling**: Prevent excessive evaluations (default: 5s per position)
- **WebSocket Reconnection**: Exponential backoff for stability
- **Database Sync**: Batch updates for efficiency

## Future Enhancements

Potential areas for further development:

1. **Super Order Integration**: Batch exit orders for multi-leg strategies
2. **Forever Orders**: Automated position rolling and management
3. **Advanced Analytics**: Real-time portfolio risk metrics
4. **Machine Learning**: Predictive exit timing
5. **Multi-Exchange**: Support for additional exchanges
6. **Mobile Alerts**: Push notifications for critical events

## Support

For issues and questions:
1. Check logs in the `logs/` directory
2. Run integration tests to verify setup
3. Use demo mode to validate functionality
4. Review this guide for configuration options

The real-time system is designed to be robust, performant, and production-ready while maintaining full compatibility with the existing trading infrastructure.