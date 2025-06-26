# Archive Summary

This archive contains files that are no longer actively used but kept for reference.

## Directory Structure

### test_scripts/
- `test_industry_allocation_system.py` - Old allocation system tests
- `test_sophisticated_allocator.py` - Allocator unit tests
- `test_strike_profiler_integration.py` - Strike profiler tests
- `test_strike_selection.py` - Strike selection tests
- `test_volatility_integration.py` - Volatility tests

### old_deployment/
- `deploy_sophisticated_allocator.py` - Old deployment script (use sophisticated_portfolio_allocator_runner.py instead)
- `validate_sophisticated_allocator.py` - Validation script
- `sophisticated_allocator_db_runner.py` - Old DB runner

### old_documentation/
- `PORTFOLIO_ALLOCATOR_LOGIC.md` - Replaced by sophisticated allocator
- `GEMINI_PORTFOLIO_CONSTRUCTION_LOGIC.md` - Equity system docs
- `INDUSTRY_ALLOCATION_FRAMEWORK.md` - Old framework docs
- `DATABASE_INTEGRATION_SUMMARY.md` - Integrated into main guide
- `EXECUTION_WORKFLOW_GUIDE.md` - Integrated into main guide
- `DOCUMENTATION_CLEANUP_SUMMARY.md` - Previous cleanup notes

### utility_scripts/
- `create_trading_views.py` - Database view creation
- `demo_trading_queries.py` - Demo queries

## Note
These files are archived as they've been replaced by newer implementations or integrated into the main documentation. The current production system uses:
- `sophisticated_portfolio_allocator_runner.py` for allocation
- `OPTIONS_V4_SYSTEM_GUIDE.md` for main documentation