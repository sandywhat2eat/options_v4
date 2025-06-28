# Options V4 Trading System - Claude Development Guide

## Quick Reference

### System Overview
- **Purpose**: Automated options strategy analysis, portfolio allocation, and trade execution
- **Current System**: Modular 4-Operation Architecture
- **Strategy Creation**: Advanced market analysis with IV profiling and strategy construction
- **Portfolio Allocation**: Hybrid tier + industry allocation targeting 4% monthly returns
- **Trade Execution**: Dhan API integration with automated order management
- **Trade Monitoring**: Real-time WebSocket monitoring + Legacy polling system
- **Database**: Supabase with real-time updates

### Key Commands

```bash
# ACTIVATE ENVIRONMENT (REQUIRED FOR ALL OPERATIONS)
source /Users/jaykrish/agents/project_output/venv/bin/activate

# 1. STRATEGY CREATION (Market Analysis & Strategy Generation)
python main.py                                    # Analyze portfolio symbols, generate strategies
python main.py --symbol RELIANCE                  # Analyze specific symbol
python main.py --risk aggressive                  # Adjust risk tolerance
python main.py --no-database                      # Run without database storage

# 2. PORTFOLIO ALLOCATION (Capital Allocation Across Strategies)
python run_allocator.py 1500000                   # Allocate ₹15L capital (recommended)
python run_allocator.py 1000000                   # Allocate ₹10L capital
python run_allocator.py 2000000                   # Allocate ₹20L capital

# 3. TRADE EXECUTION (Order Placement & Management)
python trade_execution/options_v4_executor.py --execute           # Execute all marked strategies
python trade_execution/options_v4_executor.py --strategy-id 3359  # Execute specific strategy
python trade_execution/mark_for_execution.py                      # Mark strategies for execution

# 4A. REAL-TIME MONITORING (WebSocket - RECOMMENDED)
# Method 1: Using launcher (works from anywhere)
python run_monitoring.py realtime                      # Real-time monitoring (simulation)
python run_monitoring.py realtime --execute            # Live execution (⚠️ REAL MONEY)
python run_monitoring.py realtime --interval 10        # Custom interval
python run_monitoring.py realtime --once               # Single cycle

# Method 2: Direct execution (from project root only)
python trade_monitoring/realtime/realtime_automated_monitor.py              # Real-time monitoring (simulation)
python trade_monitoring/realtime/realtime_automated_monitor.py --execute    # Live execution (⚠️ REAL MONEY)

# 4B. LEGACY MONITORING (Polling - Backward Compatibility)
# Method 1: Using launcher (works from anywhere)
python run_monitoring.py legacy --execute --interval 5  # Legacy 5-minute polling
python run_monitoring.py interactive --continuous       # Interactive dashboard

# Method 2: Direct execution (from project root only)
python trade_monitoring/legacy/automated_monitor.py --execute --interval 5  # Legacy 5-minute polling
python trade_monitoring/legacy/monitor.py --continuous                      # Interactive dashboard

# DATA MAINTENANCE
python data_scripts/import_scrip_master.py        # Update security master
python data_scripts/update_trade_prices.py        # Fix zero-price trades
python data_scripts/market_quote_fetcher.py       # Fetch current market data

# IV HISTORICAL SYSTEM (DAILY WORKFLOW)
python3 iv_historical_builder/iv_collector.py --latest    # Collect today's IV data
python3 iv_historical_builder/iv_analyzer.py              # Update IV percentiles
```

### Recent Improvements

1. **IV Historical System Implementation** (June 28, 2025)
   - **✅ Real IV Percentiles**: Replaced default 50% fallbacks with actual historical data
   - **✅ 212 Symbols Backfilled**: Complete historical IV data for 7+ days (June 20-28, 2025)
   - **✅ Pagination Fixed**: IV collector now processes 20,000+ records per date (was limited to 1000)
   - **✅ Accurate IV Environments**: Proper LOW/NORMAL/HIGH classifications based on real data
   - **✅ Daily Workflow**: Automated IV collection and percentile calculation system
   - **✅ Strategy Optimization**: Better volatility-based strategy selection and recommendations
   - **Database Tables**: `historical_iv_summary` and `iv_percentiles` for comprehensive IV tracking
   - **Integration**: Main system automatically uses updated percentiles for strategy selection

2. **Complete System Reorganization** (June 28, 2025)
   - **4-Operation Architecture**: Clean separation of strategy creation, allocation, execution, and monitoring
   - **Modular Directory Structure**: Each operation has its own dedicated directory
   - **Import Path Fixes**: All cross-module imports properly resolved
   - **Trade Execution/Monitoring Split**: Execution logic separated from monitoring systems
   - **Real-time vs Legacy Monitoring**: WebSocket monitoring separated from polling-based monitoring
   - **Root Directory Cleanup**: Only essential entry points and documentation in root
   - **Strategy Organization**: All strategy implementations moved to strategy_creation/strategies/
   - **Professional Structure**: Clean, maintainable codebase with logical organization

2. **Hybrid Portfolio Allocation Engine** (June 27-28, 2025)
   - **Tier + Industry Hybrid Approach**: Combines 60/30/10 tier allocation with industry weights
   - **LONG/SHORT Position Logic**: Proper integration of position_type from industry_allocations_current
   - **Market Condition Integration**: Dynamic allocation based on market_conditions.yaml
   - **High Capital Deployment**: Achieving 95%+ deployment vs previous 8-40%
   - **Target Achievement**: Consistently achieving 109%+ of 4% monthly return target
   - **Quality Strategy Selection**: Manageable 20-30 position portfolios with diverse strategies

3. **Real-Time Trading System Deployment** (June 26, 2025)
   - **LIVE SYSTEM OPERATIONAL**: Real-time monitoring successfully deployed and tested
   - **Live Trade Verification**: Tested with ASTRAL Long Call (Security ID: 78165)
   - **Price Fetching Fixed**: Dhan API integration working with live market data
   - **P&L Calculations Accurate**: Real-time P&L showing ₹-1,020 (-4.21%) correctly
   - **WebSocket Connections**: Sub-second price updates and database notifications
   - **System Performance**: 0.5-second monitoring cycles with 0 errors
   - **Exit Logic Verified**: Properly identifying MONITOR vs CLOSE_IMMEDIATELY conditions
   - **Production Ready**: Safe simulation mode tested, ready for live execution

2. **Advanced Allocator System** (June 26, 2025)
   - **Complete System Rewrite**: New advanced_allocator/ module replacing old sophisticated allocator
   - **Enhanced Market Analysis**: Real VIX data (12.96) with sophisticated technical scoring
   - **Best Strategy Selection**: Automatically selects highest total_score strategy per symbol
   - **Real Market Direction**: Uses momentum, strength indicators, and RSI for accurate analysis
   - **Improved Options Flow**: Multi-factor PCR analysis (PCR, PCR Volume, PCR OI)
   - **No Mock Data**: System fails gracefully if real data unavailable (production-ready)
   - **Industry-Based Allocation**: Uses industry_allocations_current table for position types
   - **Clean Architecture**: Modular design with proper separation of concerns

2. **Entry Price Fix & Enhanced Execution** (June 25, 2025)
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
# CURRENT SYSTEM (4-Operation Architecture)

# 1. STRATEGY CREATION
strategy_creation/
├── data_manager.py                      # Market data fetching
├── iv_analyzer.py                       # Implied volatility analysis
├── probability_engine.py               # Probability calculations
├── stock_profiler.py                   # Stock profiling & volatility bucketing
├── strike_selector.py                  # Intelligent strike selection
├── market_conditions_analyzer.py       # Market direction analysis
└── strategies/                         # All strategy implementations
    ├── directional/                     # Long Call/Put, Spreads
    ├── neutral/                         # Iron Condor, Butterfly
    ├── volatility/                      # Straddles, Strangles
    ├── income/                          # Covered Call, Cash-Secured Put
    └── advanced/                        # Calendar, Diagonal, Ratio spreads

# 2. PORTFOLIO ALLOCATION  
portfolio_allocation/
├── core/
│   ├── hybrid_portfolio_engine.py      # Main hybrid allocation engine
│   └── hybrid_runner.py                # Command-line interface
├── market_conditions.yaml              # Market condition configs
└── results/                            # Allocation outputs

# 3. TRADE EXECUTION
trade_execution/
├── options_v4_executor.py              # Main execution script
├── exit_manager.py                     # Exit condition management
├── exit_evaluator.py                   # Exit logic evaluation
├── exit_executor.py                    # Order placement
├── options_portfolio_manager.py        # Portfolio orchestration
└── mark_for_execution.py               # Strategy marking utility

# 4. TRADE MONITORING
trade_monitoring/
├── realtime/                           # WebSocket monitoring (RECOMMENDED)
│   ├── realtime_automated_monitor.py   # Real-time monitoring
│   ├── websocket_manager.py            # WebSocket connections
│   └── supabase_realtime.py            # Real-time database
└── legacy/                             # Polling monitoring (Backward compatibility)
    ├── automated_monitor.py            # Legacy 5-minute polling
    ├── monitor.py                      # Interactive dashboard
    └── position_monitor.py             # Position tracking utilities

# SHARED COMPONENTS
├── main.py                              # Strategy creation entry point
├── run_allocator.py                     # Portfolio allocation entry point
├── iv_historical_builder/              # IV Historical System (NEW)
│   ├── iv_collector.py                 # Daily IV data collection with pagination
│   ├── iv_analyzer.py                  # IV percentile calculation
│   ├── iv_integration.py               # Integration with main system
│   ├── database_schema.sql             # IV tables schema
│   └── README.md                       # IV system documentation
├── database/
│   ├── supabase_integration.py         # Database interface
│   ├── database_schema_updates.sql     # Schema updates
│   └── trading_views.sql               # Database views
├── data_scripts/
│   ├── market_quote_fetcher.py         # Market data fetching
│   ├── import_scrip_master.py          # Security master updates
│   └── update_trade_prices.py          # Price fixing utilities
├── analysis/                           # Market analysis utilities
├── config/                             # Configuration files
└── utils/                              # Common utilities

# ARCHIVED COMPONENTS
archived_legacy/                         # Old allocators and deprecated code
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

### Real-Time vs Legacy Monitoring Systems

#### NEW SYSTEM: Real-Time WebSocket Monitoring (RECOMMENDED)
- **File**: `realtime_automated_monitor.py`
- **Technology**: Dhan WebSocket + Supabase Realtime
- **Update Frequency**: Sub-second (instant price updates)
- **Price Source**: Live WebSocket feed with Redis caching
- **Exit Speed**: Immediate execution on trigger
- **Fallback**: Automatic REST API fallback if WebSocket fails
- **Testing**: Verified with live ASTRAL trade (Security ID: 78165)

#### OLD SYSTEM: Polling-Based Monitoring (LEGACY)
- **File**: `automated_monitor.py`
- **Technology**: REST API polling
- **Update Frequency**: Configurable intervals (default 5 minutes)
- **Price Source**: Batch API calls
- **Exit Speed**: Delayed by polling interval
- **Reliability**: Depends on API rate limits
- **Status**: Maintained for backward compatibility

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

### Detailed Operation Guides

For comprehensive guidance on each operation, refer to the dedicated guides:

📊 **[Strategy Creation Guide](STRATEGY_CREATION_GUIDE.md)** - Market analysis, strategy construction, and ranking
💰 **[Portfolio Allocation Guide](PORTFOLIO_ALLOCATION_GUIDE.md)** - Capital distribution and hybrid allocation
⚡ **[Trade Execution Guide](TRADE_EXECUTION_GUIDE.md)** - Order management and position setup
👁️ **[Trade Monitoring Guide](TRADE_MONITORING_GUIDE.md)** - Real-time and legacy monitoring systems

### For Development

When modifying the system:

1. **Adding New Strategy**
   - Inherit from `BaseStrategy` in `strategy_creation/strategies/base_strategy.py`
   - Add to strategy registry in `strategy_creation/strategies/__init__.py`
   - Update metadata in `strategy_creation/strategies/strategy_metadata.py`
   - Test with single symbol first using `main.py --symbol SYMBOL`

2. **Modifying Strike Selection**
   - Update `IntelligentStrikeSelector` in `strategy_creation/strike_selector.py`
   - Add strategy config if needed
   - Test with single symbol first

3. **Database Changes**
   - Update schema in Supabase dashboard
   - Modify SQL files in `database/` directory
   - Update `database/supabase_integration.py`
   - Test with sample data first

4. **Allocation Changes**
   - Modify `portfolio_allocation/market_conditions.yaml`
   - Update `portfolio_allocation/core/hybrid_portfolio_engine.py`
   - Test with `--dry-run` flag first

5. **Execution Changes**
   - Modify `trade_execution/` modules
   - Test in simulation mode first
   - Update safety controls as needed

6. **Monitoring Changes**
   - Real-time: Modify `trade_monitoring/realtime/` modules
   - Legacy: Modify `trade_monitoring/legacy/` modules
   - Test with `--once` flag for single cycles

### Current Directory Structure

```
options_v4/
├── main.py                         # Strategy creation entry point
├── run_allocator.py               # Portfolio allocation entry point
├── requirements.txt               # Project dependencies
│
├── strategy_creation/             # Market analysis & strategy generation
│   ├── strategies/               # All strategy implementations
│   └── [analysis modules]        # IV analysis, probability, etc.
│
├── portfolio_allocation/          # Capital allocation system
│   ├── core/                    # Hybrid allocation engine
│   ├── market_conditions.yaml   # Market condition configs
│   └── results/                 # Allocation outputs
│
├── trade_execution/              # Order placement & management
│   ├── options_v4_executor.py   # Main execution script
│   └── [execution modules]      # Exit management, order handling
│
├── trade_monitoring/             # Position tracking systems
│   ├── realtime/               # WebSocket monitoring (recommended)
│   └── legacy/                 # Polling monitoring (compatibility)
│
├── iv_historical_builder/        # IV Historical System (NEW - June 28, 2025)
│   ├── iv_collector.py          # Daily IV data collection with pagination
│   ├── iv_analyzer.py           # IV percentile calculation & ranking
│   ├── iv_integration.py        # Integration with main options system
│   ├── database_schema.sql      # Database tables for IV data
│   └── README.md                # Complete IV system documentation
│
├── database/                    # Database integration & schema
├── data_scripts/               # Market data fetchers & utilities
├── analysis/                   # Market analysis utilities
├── config/                     # Configuration files
├── logs/                       # System logs
├── results/                    # Analysis results
├── utils/                      # Common utilities
├── documentation/              # Comprehensive documentation
└── archived_legacy/            # Archived old allocators & code
```

Remember: Always test changes with single symbol before full portfolio run!