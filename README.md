# Options V4 Trading System

A sophisticated automated options trading system with strategy analysis, portfolio allocation, and execution capabilities.

## 🚀 Quick Start

```bash
# Clone and setup
git clone <repository>
cd options_v4
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials:
# - SUPABASE_URL
# - SUPABASE_ANON_KEY  
# - DHAN_CLIENT_ID
# - DHAN_ACCESS_TOKEN

# Run daily workflow
python main.py --risk moderate                                      # 1. Generate strategies
python sophisticated_portfolio_allocator_runner.py --update-database # 2. Allocate portfolio
python options_v4_executor.py --execute                            # 3. Execute trades
python monitor_positions.py --continuous                            # 4. Monitor positions
```

## 📋 System Overview

### Key Features
- **22+ Options Strategies**: Comprehensive coverage for all market conditions
- **Portfolio Analysis**: Analyzes 50+ symbols across 6 industries
- **Two Allocation Systems**:
  - **Sophisticated Allocator**: VIX-based quantum scoring (Production Ready)
  - **Advanced Allocator**: Industry-based with market direction analysis (Beta)
- **Real-Time Monitoring**: Live P&L tracking with automated exit management
- **Database Integration**: Complete strategy storage and tracking
- **Direct Execution**: Seamless Dhan API integration

### System Components

```
options_v4/
├── main.py                                    # Strategy generation engine
├── sophisticated_portfolio_allocator_runner.py # Portfolio allocation (PRODUCTION)
├── options_v4_executor.py                     # Trade execution
├── monitor_positions.py                       # Real-time monitoring
├── automated_monitor.py                       # Automated monitoring & exits
│
├── advanced_allocator/                        # New allocation system (BETA)
│   ├── runner.py                             # CLI interface
│   ├── config/                               # Configuration files
│   └── core/                                 # Core components
│
├── core/                                      # Core system components
├── strategies/                                # 22+ strategy implementations
├── database/                                  # Database integration
└── documentation/                             # Detailed documentation
```

## 🎯 Usage Guide

### 1. Strategy Generation

```bash
# Analyze full portfolio (50 symbols)
python main.py --risk moderate

# Analyze single symbol
python main.py --symbol RELIANCE --risk aggressive

# Run without database (testing)
python main.py --no-database
```

### 2. Portfolio Allocation

#### Option A: Sophisticated Allocator (Recommended)
```bash
# Run allocation with database update
python sophisticated_portfolio_allocator_runner.py --update-database

# Dry run (no database update)
python sophisticated_portfolio_allocator_runner.py --no-database

# Custom configuration
python sophisticated_portfolio_allocator_runner.py --config custom_config.yaml
```

#### Option B: Advanced Allocator (Beta - Requires Additional Setup)
```bash
# Run with custom capital
python advanced_allocator/runner.py --capital 10000000 --update-database

# Specify VIX level
python advanced_allocator/runner.py --vix 25.5 --output results/allocation.json

# Dry run mode
python advanced_allocator/runner.py --dry-run
```

### 3. Trade Execution

```bash
# Execute trades (with confirmation)
python options_v4_executor.py --execute --confirm

# Execute specific strategies
python options_v4_executor.py --execute --strategy-ids 123,456,789

# Simulation mode
python options_v4_executor.py --execute --simulate
```

### 4. Position Monitoring

```bash
# Interactive dashboard (updates every 5 min)
python monitor_positions.py --continuous

# Single snapshot
python monitor_positions.py

# Detailed view (shows individual legs)
python monitor_positions.py --detailed

# Automated monitoring with alerts
python automated_monitor.py --interval 10 --alert-only

# LIVE MODE - Auto-execute exits (USE WITH CAUTION!)
python automated_monitor.py --execute --interval 5
```

### 5. Performance Tracking

```bash
# Check execution status
python execution_status.py

# Performance dashboard
python execution_status.py --performance-dashboard

# Today's summary
python check_stored_data.py --today
```

## 🔧 Configuration

### Environment Variables (.env)
```bash
# Supabase Configuration
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_key

# Dhan API Configuration  
DHAN_CLIENT_ID=your_client_id
DHAN_ACCESS_TOKEN=your_access_token

# Optional
LOG_LEVEL=INFO
MAX_WORKERS=5
```

### Risk Profiles
- **Conservative**: Lower risk strategies, tighter stops
- **Moderate**: Balanced approach (recommended)
- **Aggressive**: Higher risk/reward strategies

## 📊 Allocation Systems Comparison

| Feature | Sophisticated Allocator | Advanced Allocator |
|---------|------------------------|-------------------|
| Status | Production Ready ✅ | Beta ⚠️ |
| Strategy Selection | VIX-based quantum scoring | Market direction + Industry ratings |
| Position Sizing | Kelly Criterion | Premium-based with Kelly |
| Market Analysis | VIX percentile | Nifty technical + options flow |
| Industry Allocation | Fixed weights | Dynamic from database |
| Database Requirements | Minimal | Extensive (needs setup) |
| Best For | Daily production use | Advanced users with full DB |

## 🛠️ Troubleshooting

### Common Issues

1. **"No liquid options data"**
   - Markets may be closed
   - Symbol might not have active F&O
   - Check API connectivity

2. **Database Errors**
   - Verify Supabase credentials
   - Check table permissions
   - Ensure internet connectivity

3. **Strike Selection Errors**
   - System auto-selects nearest available strike
   - Check logs for details
   - May need to update strike intervals

4. **Advanced Allocator: Missing Tables**
   - Requires additional database tables
   - See CONSOLIDATED_FIX_PLAN.md for setup
   - Use sophisticated allocator for production

### Checking Logs

```bash
# Today's main log
tail -f logs/options_v4_main_$(date +%Y%m%d).log

# Execution logs
tail -f logs/options_v4_execution.log

# Monitor logs
tail -f logs/position_monitor.log

# Check for errors
grep ERROR logs/options_v4_main_$(date +%Y%m%d).log
```

## 📈 Performance Metrics

- Portfolio Analysis: ~18 minutes for 50 symbols
- Strategy Success Rate: 68% (market dependent)
- Execution Speed: 4.2 seconds per strategy
- Monitoring Update: Real-time with 5-minute intervals

## 🔒 Safety Features

- **Duplicate Prevention**: Checks before database insertion
- **Strike Fallback**: Intelligent selection when exact strike unavailable
- **Position Limits**: Configurable max positions per symbol
- **Exit Management**: Automated monitoring with manual override
- **Simulation Mode**: Test all features without real trades

## 📚 Documentation

For detailed information, see:
- [User Guide](documentation/USER_GUIDE.md) - Complete user manual
- [Technical Reference](documentation/TECHNICAL_REFERENCE.md) - System architecture
- [Database Reference](documentation/DATABASE_REFERENCE.md) - Schema details
- [CLAUDE.md](documentation/CLAUDE.md) - Development guide

## 🚦 Daily Workflow

```bash
# Morning (9:00 AM)
python main.py --risk moderate

# Pre-market (9:10 AM) 
python sophisticated_portfolio_allocator_runner.py --update-database

# Market Open (9:15 AM)
python options_v4_executor.py --execute --confirm

# Throughout the day
python monitor_positions.py --continuous

# End of day
python execution_status.py --performance-dashboard
```

## ⚡ Quick Commands Reference

```bash
# Testing
python main.py --symbol RELIANCE --no-database

# Production
python sophisticated_portfolio_allocator_runner.py --update-database

# Monitoring
python monitor_positions.py

# Maintenance
python import_scrip_master.py
python cleanup_scripts/cleanup_old_results.py
```

## 🆘 Support

- Check documentation in `documentation/` folder
- Review logs in `logs/` directory  
- Ensure all required database tables exist
- Verify API credentials are valid

---

**Note**: Always test with single symbols or simulation mode before running full portfolio operations.

Version 4.0 | Last Updated: June 24, 2025