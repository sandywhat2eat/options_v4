# Options V4 Trading System - Claude Build Instructions

## System Overview
This is a comprehensive options trading strategy analysis system with 22+ strategies, industry-first allocation framework, complete database integration, and direct execution capabilities via Dhan API.

## Project Structure
```
options_v4/
├── main.py                          # Main entry point (50-symbol support)
├── requirements.txt                 # Python dependencies
├── config/
│   └── options_config.py           # Industry allocation configuration
├── core/                           # Core system components
│   ├── data_manager.py             # Data fetching (50-symbol limit)
│   ├── market_conditions_analyzer.py # Market environment analysis
│   ├── industry_allocation_engine.py # Industry-based allocation
│   ├── options_portfolio_manager.py  # Main orchestration controller
│   ├── strike_selector.py          # Intelligent strike selection
│   ├── exit_manager.py             # Exit condition generation
│   └── probability_engine.py       # Probability calculations
├── strategies/                     # 22+ strategy implementations
├── analysis/                       # Market analysis modules
├── database/
│   └── supabase_integration.py     # Complete database interface
├── documentation/                  # Complete documentation library
├── data_scripts/                   # VIX & NIFTY historical data fetchers
├── execution/                      # Trading execution scripts
│   ├── mark_for_execution.py       # Strategy selection for execution
│   ├── options_v4_executor.py      # Dhan API order execution
│   └── execution_status.py         # Execution monitoring
├── logs/                          # System logs
└── results/                       # Analysis output files
```

## Key Features
- **22+ Options Strategies**: Complete strategy library covering all market conditions
- **Industry-First Allocation**: Uses database allocation tables for strategy prioritization
- **50-Symbol Portfolio Analysis**: Enhanced from 5 to 50-symbol capability (68% success rate)
- **Market Conditions Integration**: NIFTY + VIX + PCR analysis with 9 market states
- **Complete Database Integration**: 12+ tables for comprehensive strategy storage
- **Direct Execution**: Dhan API integration for order placement and monitoring
- **Exit Management**: Comprehensive exit conditions with profit targets, stop losses, time exits
- **Risk Management**: Industry diversification and position sizing controls
- **Real-time Monitoring**: Live execution status and performance tracking

## Core Components

### Strategies (22+ Total)
**Directional (6)**: Long Call/Put, Bull/Bear Call/Put Spreads
**Neutral (5)**: Iron Condor, Iron Butterfly, Butterfly, Short Straddle/Strangle  
**Volatility (4)**: Long/Short Straddle, Long/Short Strangle
**Income (2)**: Cash-Secured Put, Covered Call
**Advanced (5)**: Calendar, Diagonal, Call/Put Ratio Spreads, Jade Lizard, Broken Wing Butterfly

### Exit Management System
- **Profit Targets**: 25-75% based on strategy type
- **Stop Losses**: 50% to 2x based on risk profile
- **Time Exits**: 7-21 DTE depending on strategy
- **Greek Triggers**: Delta, Gamma, Theta, Vega monitoring
- **Adjustments**: Defensive, offensive, rolling, morphing options

## Complete Trading Workflow

### Phase 1: Strategy Analysis & Database Storage
```bash
# Run complete portfolio analysis (50 symbols with industry allocation)
python main.py --risk moderate

# Run industry allocation framework testing
python test_industry_allocation_system.py

# Single symbol analysis
python main.py --symbol DIXON --risk moderate
```

### Phase 2: Strategy Selection & Marking for Execution
```bash
# Review generated strategies
python mark_for_execution.py --list-recent

# Interactive strategy selection
python mark_for_execution.py --interactive

# Mark top strategies by score
python mark_for_execution.py --mark-top 5

# Mark best strategy for specific symbol
python mark_for_execution.py --mark-best DIXON
```

### Phase 3: Order Execution & Monitoring
```bash
# Preview execution plan (dry run)
python options_v4_executor.py --preview

# Execute all marked strategies
python options_v4_executor.py --execute

# Monitor execution status
python execution_status.py

# View performance dashboard
python execution_status.py --performance-dashboard
```

## Configuration

### Industry Allocation Framework
The system uses database-driven allocation:
- **Industry Tables**: `industry_allocations_current`, `sector_allocations_current`
- **Weight-based Prioritization**: Strategies selected based on industry weight percentages
- **Market Conditions**: 9 market states (Bullish/Bearish/Neutral × Low/Normal/High VIX)
- **Position Sizing**: Capital allocation based on industry weights (₹3 crores total)

### Strategy Selection
The system intelligently selects strategies based on:
- Industry allocation weights and position types (LONG/SHORT)
- Market direction confidence (NIFTY technical analysis)
- VIX environment (existing Dhan historical data)
- PCR sentiment (calculated from option_chain_data table)
- Risk tolerance and probability thresholds

### Exit Management
Exit conditions are automatically generated for each strategy:
- Strategy-specific profit targets (25-75% based on strategy type)
- Risk-appropriate stop losses (50% to 2x based on risk profile)
- Time-based exit triggers (7-21 DTE depending on strategy)
- Greek-based adjustments and monitoring alerts

## Dependencies
```
pandas>=1.5.0
numpy>=1.20.0
python-dotenv>=0.19.0
pyyaml>=6.0
dhanhq>=1.3.0
supabase>=1.0.0
yfinance>=0.2.0
tabulate>=0.9.0
```

## Data Requirements
- **Database Tables**: Industry/sector allocations, stock mappings, options chain data
- **API Access**: Dhan trading API credentials, Supabase database access
- **Market Data**: Real-time options data with Greeks, volume, open interest
- **Historical Data**: VIX and NIFTY historical data (90 days)

## Performance Metrics
- **Portfolio Analysis**: 50 symbols in ~18 minutes (vs 5 symbols in 8-12 seconds)
- **Success Rate**: 68% (34/50 symbols successfully analyzed)
- **Industry Coverage**: 6 major industries with 12 strategy types
- **Database Storage**: <5 seconds per symbol for complete strategy storage
- **Execution Speed**: 4.2 seconds average for multi-leg strategy execution

## Current Status
✅ **Fully Functional**: All 22+ strategies implemented with lot size integration
✅ **Industry Allocation**: Complete framework with database-driven allocation
✅ **Database Integration**: 12+ tables with comprehensive strategy storage
✅ **Execution Integration**: Dhan API with order management and monitoring
✅ **Portfolio Scaling**: 50-symbol analysis capability (68% success rate)
✅ **Documentation**: Complete documentation library with user guides

## Environment Setup
```bash
# Required environment variables in .env file
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_key
DHAN_CLIENT_ID=your_dhan_client_id
DHAN_ACCESS_TOKEN=your_dhan_access_token
```

## Quick Start Guide
```bash
# 1. Generate strategies (analysis phase)
python main.py --risk moderate

# 2. Review and mark strategies for execution
python mark_for_execution.py --interactive

# 3. Execute marked strategies
python options_v4_executor.py --execute --confirm

# 4. Monitor execution status
python execution_status.py
```

## Key Scripts & Their Functions

### **Analysis Scripts**
- `main.py`: Main portfolio analysis (50 symbols, industry allocation)
- `test_industry_allocation_system.py`: Framework testing and validation

### **Execution Scripts**
- `mark_for_execution.py`: Review and select strategies for execution
- `options_v4_executor.py`: Execute orders via Dhan API
- `execution_status.py`: Monitor execution status and performance

### **Utility Scripts**
- `check_stored_data.py`: Validate database storage
- `demo_trading_queries.py`: Database query examples
- `import_scrip_master.py`: Import Dhan security mappings

## File Locations
```bash
📁 Results & Logs:
├── results/options_v4_analysis_YYYYMMDD_HHMMSS.json  # Analysis results
├── results/options_portfolio_allocation_*.json      # Portfolio allocation
├── logs/options_v4_main_YYYYMMDD.log               # Analysis logs
└── options_v4_execution.log                        # Execution logs

🗄️ Database Tables:
├── strategies                   # Main strategy records  
├── strategy_details            # Individual option legs
├── strategy_execution_status   # Execution tracking
└── industry_allocations_current # Industry weights
```

## Complete Documentation
- **EXECUTION_WORKFLOW_GUIDE.md**: Complete step-by-step execution guide
- **INDUSTRY_ALLOCATION_FRAMEWORK.md**: Industry allocation documentation
- **SYSTEM_OVERVIEW_V4.md**: Comprehensive system architecture
- **DATABASE_INTEGRATION_SUMMARY.md**: Database schema and integration
- **DHAN_EXECUTION_GUIDE.md**: Trading execution framework

## Support
This system provides comprehensive options strategy analysis with industry-first allocation, complete database integration, and direct execution capabilities. The system generates strategies, stores them in database, allows selection for execution, and provides complete monitoring - delivering end-to-end options trading automation.