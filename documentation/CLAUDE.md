# Options V4 Trading System - Claude Development Guide

## Quick Reference

### System Overview
- **Purpose**: Automated options strategy analysis, storage, and execution
- **Capacity**: 50 symbols across 6 industries
- **Strategies**: 22+ options strategies
- **Database**: Supabase with real-time updates
- **Execution**: Dhan API integration
- **Allocation**: VIX-based quantum scoring system

### Key Commands

```bash
# Daily workflow (UPDATED)
python main.py --risk moderate                              # Generate strategies
python sophisticated_portfolio_allocator_runner.py --update-database  # Allocate portfolio
python options_v4_executor.py --execute                    # Execute trades
python execution_status.py                                  # Monitor status

# Real-time monitoring & execution (UPDATED)
python monitor_positions.py                                 # Interactive dashboard
python monitor_positions.py --continuous --detailed         # Live monitoring with leg details
python automated_monitor.py --once                         # Single monitoring cycle (safe)
python automated_monitor.py --alert-only --interval 10     # Alert generation only
python automated_monitor.py --execute --interval 5         # LIVE MODE - Auto exits!

# Strategy execution (UPDATED)
python options_v4_executor.py --execute                    # Execute all marked strategies
python options_v4_executor.py --strategy-id 3359          # Execute specific strategy
python update_recent_trades.py                             # Fix trades with zero prices

# Testing & debugging
python check_stored_data.py                       # Verify DB storage
grep ERROR logs/options_v4_main_$(date +%Y%m%d).log  # Check for errors

# Maintenance
python import_scrip_master.py                     # Update security master
python cleanup_scripts/cleanup_old_results.py     # Archive old files
```

### Recent Improvements

1. **Entry Price Fix & Enhanced Execution** (June 25, 2025)
   - **FIXED**: Entry prices now populate correctly (was showing ₹0.00)
   - **Auto Price Fetching**: Executor waits 5 seconds, fetches order details via Dhan API
   - **Individual Strategy Execution**: Can execute specific strategy by ID
   - **Price Update Scripts**: Utilities to fix existing zero-price trades
   - **Verified P&L Calculations**: Monitoring system now shows accurate profits/losses

2. **Real-Time Monitoring & Exit System** (June 24-25, 2025)
   - **Position Monitor**: Real-time P&L tracking and price updates
   - **Exit Evaluator**: Automated exit condition checking (profit targets, stop losses, time exits)
   - **Interactive Dashboard**: Beautiful colored display with alerts and detailed leg view
   - **Automated Monitor**: Continuous monitoring with auto-execution capability
   - **Exit Executor**: Integrated with Dhan API for order placement
   - **Safety Features**: Simulation mode, alert-only mode, audit logging
   - **Market Quote Fetcher**: Dynamic instrument fetching from open trades

2. **Strategy Selection Bias Fix** (June 24, 2025)
   - Fixed bias towards neutral/complex strategies
   - Improved directional strategy selection (Long Call/Put now appearing)
   - Adjusted metadata scoring weights:
     - Reduced time_decay_profile weight: 15% → 8%
     - Reduced complexity_penalty: 10% → 5%
     - Added market_momentum weight: 12%
   - Expanded strategy construction from 20 to 30 strategies
   - Fixed `strategy_adjustments` attribute error in strike selector

2. **Conviction Level Improvements** (June 24, 2025)
   - Fixed low conviction issue - most strategies were LOW/VERY_LOW
   - Increased base confidence calculation: 0.45 → 0.65 cap
   - Enhanced confidence boosters (0.10 → 0.15)
   - Adjusted conviction thresholds:
     - VERY_HIGH: ≥80% (was 90%)
     - HIGH: ≥65% (was 70%)
     - MEDIUM: ≥45% (was 50%)
   - Result: 40%+ strategies now have MEDIUM or higher conviction

3. **Sophisticated Portfolio Allocator** (June 2025)
   - VIX-based strategy selection with quantum scoring
   - Kelly Criterion position sizing
   - Intelligent fallback hierarchy ensuring 80-95% capital deployment
   - Industry allocation integration with 7-component scoring system
   - **FIXED**: Real VIX data integration (no more hardcoded 13.67)
   - **FIXED**: Database query syntax for Supabase
   - **Production Script**: `sophisticated_portfolio_allocator_runner.py`

4. **Centralized Strike Selection** (Dec 2024)
   - Fixed 100+ strike availability errors
   - Implemented intelligent fallback logic
   - Added liquidity-aware selection

5. **NaN Handling Fix** (Dec 2024)
   - Fixed JSON serialization errors
   - Recursive cleaning of nested structures
   - Proper handling of pandas/numpy types

6. **Duplicate Prevention** (Dec 2024)
   - Check before database insertion
   - Prevents multiple entries per day
   - Returns existing ID if found

### Critical Files

```
# Main Production Scripts
├── main.py                               # Strategy generation
├── sophisticated_portfolio_allocator_runner.py  # Portfolio allocation (USE THIS)
├── options_v4_executor.py                # Trade execution
└── execution_status.py                   # Monitoring

core/
├── strike_selector.py                    # Centralized strike selection
├── sophisticated_portfolio_allocator.py  # Quantum-level portfolio allocation
└── options_portfolio_manager.py          # Main orchestrator

database/
└── supabase_integration.py               # DB interface with duplicate prevention

strategies/
├── base_strategy.py                      # Base class with strike selector integration
└── [22 strategy implementations]

# Archived Scripts (in archive/ folder)
├── test_*.py                            # All test scripts
├── deploy_sophisticated_allocator.py     # Old deployment (archived)
└── validate_sophisticated_allocator.py   # Old validation (archived)
```

### Environment Variables

```bash
# Required in .env
SUPABASE_URL=
SUPABASE_ANON_KEY=
DHAN_CLIENT_ID=
DHAN_ACCESS_TOKEN=
```

### Performance Benchmarks

- Portfolio analysis: 50 symbols in ~18 minutes
- Success rate: 68% (34/50 symbols)
- Strategy storage: <5 seconds per symbol
- Execution speed: 4.2 seconds per strategy

### Common Issues & Solutions

1. **Strike Not Available**
   - System auto-selects nearest available strike
   - Check logs for details

2. **Low Success Rate**
   - Verify API connectivity
   - Check if markets are open
   - Review symbol list validity

3. **Database Errors**
   - Verify Supabase credentials
   - Check internet connection
   - Review table permissions

### Monitoring & Logs

```bash
# Key log files
logs/options_v4_main_YYYYMMDD.log      # Analysis logs
logs/options_v4_execution.log           # Execution logs

# Check for errors
grep ERROR logs/options_v4_main_$(date +%Y%m%d).log
grep "Strike.*not available" logs/*.log
```

### System Health Checks

```bash
# Daily checks
1. grep -c "ERROR" logs/options_v4_main_$(date +%Y%m%d).log
2. python check_stored_data.py --today
3. python execution_status.py --summary

# Weekly maintenance
1. python import_scrip_master.py
2. python cleanup_scripts/archive_old_data.py
3. Review performance metrics in database
```

### Real-Time Monitoring & Automated Exit System

Complete automated trading system with real-time monitoring and automatic exit execution:

#### System Components

1. **Position Monitor** (`core/position_monitor.py`)
   - Fetches open positions from trades table with accurate entry prices
   - Gets real-time quotes using market_quote_fetcher
   - Calculates current P&L for all positions and individual legs
   - Tracks days in trade and other metrics

2. **Exit Evaluator** (`core/exit_evaluator.py`)
   - Checks profit targets (primary, scaling levels)
   - Monitors stop losses (percentage and absolute thresholds)
   - Evaluates time-based exits (DTE triggers, theta decay)
   - Provides prioritized action recommendations with urgency levels

3. **Exit Executor** (`core/exit_executor.py`)
   - Places exit orders via Dhan API (market orders for immediate execution)
   - Handles full and partial exits (25%, 50%, 75%, 100%)
   - Updates database with exit details and timestamps
   - Includes simulation mode for safe testing

4. **Interactive Dashboard** (`monitor_positions.py`)
   - Real-time colored display with profit/loss highlighting
   - Detailed leg-by-leg breakdown with entry/current prices
   - Exit condition status and urgency alerts
   - Portfolio summary with win/loss statistics

5. **Automated Monitor** (`automated_monitor.py`)
   - Runs continuously at configurable intervals
   - Automatic exit execution with comprehensive safety controls
   - Alert generation with HIGH/MEDIUM/NORMAL urgency levels
   - Complete audit trail and execution logging

#### Usage Examples

```bash
# Interactive Monitoring
python monitor_positions.py                    # Single snapshot view
python monitor_positions.py --continuous       # Live updates every 5 minutes
python monitor_positions.py --detailed         # Show individual leg details

# Automated Monitoring (Recommended Progression)
python automated_monitor.py --once            # Single cycle test (simulation mode)
python automated_monitor.py --alert-only --interval 10     # Alert generation only
python automated_monitor.py --execute --interval 5         # LIVE MODE - Auto exits!

# Strategy Execution (Enhanced)
python options_v4_executor.py --strategy-id 3359          # Execute specific strategy
python options_v4_executor.py --execute                   # Execute all marked strategies

# Price Management
python update_recent_trades.py                            # Fix trades with zero prices
python data_scripts/update_trade_prices.py               # Batch update historical trades
```

#### Automated Exit Triggers

The system automatically monitors and executes exits based on:

1. **Profit Targets**
   - Primary targets (e.g., 50% profit)
   - Scaling targets (25%, 50%, 75% exits)
   - Trailing stop activation

2. **Stop Losses**
   - Percentage-based (e.g., -50% of max loss)
   - Absolute value stops (e.g., ₹5,000 loss)
   - Time-based stop losses

3. **Time-Based Exits**
   - DTE thresholds (e.g., close at 7 DTE)
   - Theta decay triggers
   - Maximum holding period

4. **Adjustment Signals**
   - Defensive adjustments (rolling strikes)
   - Offensive adjustments (adding legs)
   - Strategy-specific triggers

#### Safety & Control Features

1. **Multi-Level Safety**
   - Default simulation mode (no real trades)
   - Alert-only mode for monitoring
   - Explicit --execute flag required for live trading

2. **Risk Controls**
   - Duplicate exit prevention
   - Maximum loss limits
   - Position size validation
   - Market hours verification

3. **Monitoring & Alerts**
   - Real-time urgency classification (HIGH/MEDIUM/NORMAL)
   - Comprehensive logging to `logs/automated_monitor.log`
   - Exit execution history in `logs/exit_executions.json`
   - Database audit trail for all actions

4. **Manual Override**
   - Stop automated monitor with Ctrl+C
   - Manual position closure via dashboard
   - Emergency position management

### For Development

When modifying the system:

1. **Adding New Strategy**
   - Inherit from `BaseStrategy`
   - Add to strategy registry in `main.py`
   - Update strike selector config if needed

2. **Modifying Strike Selection**
   - Update `IntelligentStrikeSelector` in `core/strike_selector.py`
   - Add strategy config if needed
   - Test with single symbol first

3. **Database Changes**
   - Update schema in Supabase dashboard
   - Modify `database/supabase_integration.py`
   - Test with sample data first

4. **Allocation Changes**
   - Modify `config/options_portfolio_config.yaml`
   - Update `core/sophisticated_portfolio_allocator.py`
   - Test with `--no-database` flag first

### Current Directory Structure

```
options_v4/
├── core/                    # Core components
├── strategies/              # Strategy implementations
├── database/               # Database integration
├── data_scripts/           # Market data fetchers (VIX, etc.)
├── config/                 # Configuration files
├── logs/                   # System logs
├── results/                # Allocation reports
├── documentation/          # Clean, focused docs
└── archive/                # Old scripts and docs
    ├── test_scripts/       # Archived test files
    ├── old_deployment/     # Archived deployment scripts
    ├── old_documentation/  # Archived docs
    └── utility_scripts/    # Archived utilities
```

Remember: Always test changes with single symbol before full portfolio run!