# Options V4 Trading System - Complete Guide

## System Overview

The Options V4 Trading System is a comprehensive automated options trading platform that:
- Analyzes 50 symbols across 6 industries
- Generates 22+ types of options strategies
- Uses sophisticated portfolio allocation with VIX-based strategy selection
- Executes trades via Dhan API integration
- Stores all data in Supabase database

## Quick Start

### Daily Trading Workflow

```bash
# Step 1: Generate strategies
python main.py --risk moderate

# Step 2: Run sophisticated portfolio allocation
python sophisticated_portfolio_allocator_runner.py --update-database

# Step 3: Execute selected strategies
python options_v4_executor.py --execute

! Now you can execute strategy ID 
  using:
python options_v4_executor.py --strategy-id 3359


# Step 4: Monitor execution status
python execution_status.py
```

## Key Components

### 1. Strategy Generation (`main.py`)
- Analyzes market data for 50 symbols
- Generates optimal strategies based on risk profile
- Stores strategies in Supabase database
- Success rate: ~68% (34/50 symbols)

### 2. Sophisticated Portfolio Allocator
**Main Script**: `sophisticated_portfolio_allocator_runner.py`
- VIX-based strategy selection
- Quantum scoring system (7-component methodology)
- Kelly Criterion position sizing
- Target: 25-35 strategies, 80-95% capital deployment
- Expected Sharpe Ratio: 1.2-1.8

### 3. Trade Execution (`options_v4_executor.py`)
- Executes marked strategies via Dhan API
- Handles order placement and monitoring
- Average execution time: 4.2 seconds per strategy

### 4. Database Integration
- **Platform**: Supabase
- **Tables**: strategies, strategy_details, executions, market_conditions
- **Features**: Duplicate prevention, real-time updates

## Configuration

### Environment Variables (.env)
```bash
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_key
DHAN_CLIENT_ID=your_dhan_client_id
DHAN_ACCESS_TOKEN=your_dhan_token
```

### Risk Profiles
- **Conservative**: Lower risk, income-focused strategies
- **Moderate**: Balanced risk/reward (default)
- **Aggressive**: Higher risk, directional strategies

## Recent Improvements (June 2025)

1. **Fixed Strategy Selection Bias**
   - Reduced complexity penalty: 10% → 5%
   - Added market momentum weight: 12%
   - Result: More directional strategies now appear

2. **Enhanced Conviction Levels**
   - Increased base confidence: 0.45 → 0.65
   - Adjusted thresholds for better distribution
   - Result: 40%+ strategies have MEDIUM+ conviction

3. **Real VIX Data Integration**
   - Fetches live India VIX data from Dhan API
   - Dynamic strategy selection based on VIX percentile
   - No more hardcoded values

## Monitoring & Maintenance

### Daily Health Checks
```bash
# Check for errors
grep ERROR logs/options_v4_main_$(date +%Y%m%d).log

# Verify stored strategies
python check_stored_data.py --today

# Review execution status
python execution_status.py --summary
```

### Weekly Maintenance
```bash
# Update security master
python import_scrip_master.py

# Clean up old files
python cleanup_scripts/cleanup_old_results.py
```

## Performance Metrics

- **Strategy Generation**: ~18 minutes for 50 symbols
- **Portfolio Allocation**: ~5 seconds
- **Database Operations**: <5 seconds per symbol
- **Expected Annual Return**: 25-35%
- **Win Rate Target**: 65-75%

## Troubleshooting

### Common Issues

1. **Strike Not Available**
   - System auto-selects nearest available strike
   - Check logs for fallback details

2. **Low Success Rate**
   - Verify API connectivity
   - Ensure markets are open
   - Check symbol validity

3. **Database Errors**
   - Verify Supabase credentials
   - Check table permissions
   - Review connection logs

## Support Scripts

- `check_stored_data.py`: Verify database storage
- `execution_status.py`: Monitor trade execution
- `mark_for_execution.py`: Manual strategy marking
- `import_scrip_master.py`: Update security master

## Directory Structure

```
options_v4/
├── core/                    # Core system components
│   ├── sophisticated_portfolio_allocator.py
│   ├── strike_selector.py
│   └── options_portfolio_manager.py
├── strategies/              # 22+ strategy implementations
├── database/               # Database integration
├── utils/                  # Utilities and helpers
├── config/                 # Configuration files
├── logs/                   # System logs
├── results/                # Allocation reports
└── documentation/          # System documentation
```

## Contact & Support

For issues or questions:
- Check logs in `logs/` directory
- Review error patterns in documentation
- Ensure all dependencies are installed

---

Last Updated: June 24, 2025