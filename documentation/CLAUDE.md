# Options V4 Trading System - Build & Maintenance Guide

## Quick Reference

### System Overview
- **Purpose**: Automated options strategy analysis, storage, and execution
- **Capacity**: 50 symbols across 6 industries
- **Strategies**: 22+ options strategies
- **Database**: Supabase with 12+ tables
- **Execution**: Dhan API integration

### Key Commands

```bash
# Daily workflow
python main.py --risk moderate                    # Generate strategies
python sophisticated_portfolio_allocator_runner.py --update-database  # Run sophisticated allocation (FIXED)
python options_v4_executor.py --execute          # Execute trades
python execution_status.py                        # Monitor status

# Portfolio allocation testing
python validate_sophisticated_allocator.py        # Validate allocator readiness
python sophisticated_allocator_db_runner.py       # Test with database integration

# Testing & debugging
python test_strike_selection.py                   # Test strike selector
python check_stored_data.py                       # Verify DB storage

# Maintenance
python import_scrip_master.py                     # Update security master
python cleanup_scripts/cleanup_old_results.py     # Archive old files
```

### Recent Improvements

1. **Strategy Selection Bias Fix** (June 24, 2025)
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
   - Replaces basic portfolio_allocator.py with quantum-level sophistication

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
core/
├── strike_selector.py                    # Centralized strike selection
├── sophisticated_portfolio_allocator.py  # Quantum-level portfolio allocation
├── industry_allocation_engine.py         # Industry-based allocation
└── options_portfolio_manager.py          # Main orchestrator

database/
└── supabase_integration.py               # DB interface with duplicate prevention

strategies/
├── base_strategy.py                      # Base class with strike selector integration
└── [22 strategy implementations]

# Production deployment scripts
├── deploy_sophisticated_allocator.py      # Production allocator deployment
├── validate_sophisticated_allocator.py    # Allocator validation
└── sophisticated_allocator_db_runner.py   # Database integration testing
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

### For Development

When modifying the system:

1. **Adding New Strategy**
   - Inherit from `BaseStrategy`
   - Add to strategy registry
   - Update strike selector config

2. **Modifying Strike Selection**
   - Update `IntelligentStrikeSelector`
   - Add strategy config if needed
   - Test with `test_strike_selection.py`

3. **Database Changes**
   - Update schema in Supabase
   - Modify `supabase_integration.py`
   - Test with sample data first

Remember: Always test changes with single symbol before full portfolio run!