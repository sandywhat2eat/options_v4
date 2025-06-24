# Options V4 Trading System - User Guide

## Table of Contents
1. [Introduction](#introduction)
2. [System Setup](#system-setup)
3. [Daily Trading Workflow](#daily-trading-workflow)
4. [Strategy Analysis](#strategy-analysis)
5. [Strategy Selection](#strategy-selection)
6. [Order Execution](#order-execution)
7. [Performance Monitoring](#performance-monitoring)
8. [Risk Management](#risk-management)
9. [Common Issues](#common-issues)
10. [Best Practices](#best-practices)

---

## Introduction

The Options V4 Trading System is an automated options strategy analyzer that:
- Analyzes 50 symbols across 6 industries
- Generates strategies from a library of 22+ option strategies
- Stores analysis in Supabase database
- Executes trades via Dhan API
- Monitors performance in real-time

### Key Features
- **Sophisticated Portfolio Allocator** with VIX-based strategy selection and quantum scoring
- **Industry-based allocation** for diversified risk with Kelly Criterion position sizing
- **Market-aware strategy selection** using NIFTY, VIX, and PCR data
- **Intelligent fallback hierarchy** ensuring 80-95% capital deployment
- **Automated exit management** with profit targets and stop losses
- **Complete trade lifecycle** from analysis to execution

---

## System Setup

### 1. Environment Configuration

Create a `.env` file with your credentials:
```bash
# Database Configuration
SUPABASE_URL=your_supabase_project_url
SUPABASE_ANON_KEY=your_supabase_anon_key

# Trading API Configuration  
DHAN_CLIENT_ID=your_dhan_client_id
DHAN_ACCESS_TOKEN=your_dhan_access_token
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Verify Database Connection
```bash
python check_stored_data.py
```

### 4. Import Security Master (One-time setup)
```bash
python import_scrip_master.py
```

---

## Daily Trading Workflow

### Morning Routine (9:00 AM - 9:30 AM)

#### 1. Generate Fresh Analysis
```bash
# Run complete portfolio analysis
python main.py --risk moderate

# Or analyze specific symbol
python main.py --symbol RELIANCE --risk moderate
```

#### 2. Review Generated Strategies
```bash
# List today's strategies
python mark_for_execution.py --list-recent

# View detailed analysis
cat results/options_v4_analysis_[YYYYMMDD]_[HHMMSS].json
```

#### 3. Run Sophisticated Portfolio Allocation
```bash
# Deploy sophisticated allocator with VIX-based selection
python deploy_sophisticated_allocator.py

# Or validate allocator readiness first
python validate_sophisticated_allocator.py
```

#### 4. Execute Selected Strategies
```bash
# Preview execution plan
python options_v4_executor.py --preview

# Execute with confirmation
python options_v4_executor.py --execute --confirm
```

#### 5. Monitor Execution
```bash
# Check execution status
python execution_status.py

# View performance dashboard
python execution_status.py --performance-dashboard
```

---

## Strategy Analysis

### Understanding the Analysis Output

Each analysis generates:
1. **Market Analysis** - Direction, confidence, IV environment
2. **Top Strategies** - Ranked by total score
3. **Exit Conditions** - Profit targets, stop losses, time exits
4. **Risk Metrics** - Max profit/loss, probability of profit

### Risk Profiles

- **Conservative**: Lower risk strategies, tighter stops
- **Moderate**: Balanced risk/reward (recommended)
- **Aggressive**: Higher risk tolerance, wider stops

### Analysis Parameters
```bash
# Full portfolio with specific risk profile
python main.py --risk aggressive

# Single symbol analysis
python main.py --symbol INFY --risk moderate

# Industry allocation test
python test_industry_allocation_system.py
```

---

## Strategy Selection

### Selection Criteria

Consider these factors when selecting strategies:

1. **Total Score** (0.5-1.0 range)
   - >0.8: Excellent opportunity
   - 0.6-0.8: Good opportunity
   - <0.6: Consider skipping

2. **Probability of Profit**
   - Conservative: >60%
   - Moderate: >50%
   - Aggressive: >40%

3. **Risk/Reward Ratio**
   - Look for >1.5:1 ratio
   - Higher is better

4. **Market Alignment**
   - Strategy matches market outlook
   - IV environment appropriate

### Selection Commands

```bash
# Interactive selection (recommended)
python mark_for_execution.py --interactive

# Mark best strategy per symbol
python mark_for_execution.py --mark-best RELIANCE

# Mark all with score > threshold
python mark_for_execution.py --mark-above-score 0.75

# Unmark strategies
python mark_for_execution.py --unmark [strategy_id]
```

---

## Order Execution

### Pre-Execution Checklist

1. ✓ Verify market hours (9:15 AM - 3:30 PM)
2. ✓ Check account balance and margin
3. ✓ Review selected strategies
4. ✓ Ensure proper risk allocation

### Execution Process

```bash
# 1. Preview execution plan (always do this first)
python options_v4_executor.py --preview

# 2. Execute with confirmation prompts
python options_v4_executor.py --execute --confirm

# 3. Execute without prompts (use carefully)
python options_v4_executor.py --execute --no-confirm

# 4. Execute specific strategy
python options_v4_executor.py --execute --strategy-id 123
```

### Execution Monitoring

The system provides real-time updates:
- Order placement status
- Fill confirmations
- Execution prices
- Slippage tracking

---

## Performance Monitoring

### Real-time Monitoring
```bash
# Basic status check
python execution_status.py

# Detailed performance metrics
python execution_status.py --performance-dashboard

# Export performance report
python execution_status.py --export-report
```

### Key Metrics to Track

1. **Win Rate**: Percentage of profitable trades
2. **Average P&L**: Per trade profit/loss
3. **Sharpe Ratio**: Risk-adjusted returns
4. **Max Drawdown**: Largest peak-to-trough decline

### Database Queries

View strategies in database:
```sql
-- Today's executed strategies
SELECT * FROM strategy_execution_status 
WHERE DATE(executed_at) = CURRENT_DATE
ORDER BY executed_at DESC;

-- Performance by strategy type
SELECT strategy_type, 
       COUNT(*) as trades,
       AVG(realized_pnl) as avg_pnl
FROM strategy_execution_status
GROUP BY strategy_type;
```

---

## Risk Management

### Position Sizing Rules

1. **Per-Trade Risk**: Maximum 2% of capital per trade
2. **Industry Limits**: Follow allocation framework weights
3. **Strategy Limits**: Maximum 5 positions per strategy type
4. **Daily Limits**: Maximum 10 new positions per day

### Exit Management

The system automatically generates exit conditions:

#### Profit Targets
- **Conservative**: 25-40% of max profit
- **Moderate**: 40-60% of max profit  
- **Aggressive**: 60-75% of max profit

#### Stop Losses
- **Conservative**: 50% of max loss
- **Moderate**: 75% of max loss
- **Aggressive**: 100% of max loss

#### Time Exits
- Close positions with <7 DTE
- Reduce size at 50% time elapsed
- Full exit at expiry week

---

## Common Issues

### 1. Strike Not Available
**Issue**: "Strike X not available for SYMBOL"
**Solution**: System automatically selects nearest available strike

### 2. Low Liquidity
**Issue**: "Insufficient liquidity for strategy"
**Solution**: Skip the strategy or reduce position size

### 3. Database Connection Failed
**Issue**: "Failed to connect to Supabase"
**Solution**: 
- Check internet connection
- Verify .env credentials
- Check Supabase service status

### 4. Execution Failed
**Issue**: "Order rejected by broker"
**Solution**:
- Check margin requirements
- Verify trading hours
- Review order parameters

### 5. Analysis Timeout
**Issue**: Analysis takes too long
**Solution**:
- Reduce symbol count
- Check API rate limits
- Use --no-database flag for testing

---

## Best Practices

### Daily Operations

1. **Run analysis before market open** (9:00-9:15 AM)
2. **Review and select strategies** (9:15-9:25 AM)
3. **Execute after market settles** (9:30 AM+)
4. **Monitor throughout the day**
5. **Review performance after close**

### Strategy Selection

1. **Diversify across industries** - Don't concentrate in one sector
2. **Mix strategy types** - Combine directional, neutral, and income
3. **Consider market conditions** - Align strategies with market view
4. **Respect position limits** - Don't over-leverage

### Risk Management

1. **Always use stop losses** - Never disable exit conditions
2. **Size positions appropriately** - Follow the 2% rule
3. **Monitor correlations** - Avoid similar positions
4. **Keep cash reserves** - Maintain 30% cash for opportunities

### System Maintenance

1. **Check logs daily** - Review for errors or warnings
2. **Update security master** - Weekly update recommended
3. **Archive old results** - Keep last 30 days active
4. **Monitor database size** - Clean up old execution records

---

## Advanced Features

### Custom Strategy Analysis
```python
# In main.py, modify strategy selection
custom_strategies = ['Iron Condor', 'Bull Put Spread', 'Cash-Secured Put']
```

### Batch Operations
```bash
# Mark multiple strategies
python mark_for_execution.py --mark-ids 123,124,125

# Execute in batches
python options_v4_executor.py --execute --batch-size 5
```

### Performance Analytics
```bash
# Generate detailed reports
python generate_performance_report.py --days 30

# Export to Excel
python export_trades.py --format excel --output trades.xlsx
```

---

## Support & Troubleshooting

### Log Files
- Analysis logs: `logs/options_v4_main_YYYYMMDD.log`
- Execution logs: `logs/options_v4_execution.log`
- Error details: Check latest entries for issues

### Common Commands Reference
```bash
# Help for any script
python [script_name].py --help

# Verbose output
python main.py --symbol INFY --verbose

# Debug mode
python options_v4_executor.py --debug
```

### Getting Help
1. Check this user guide
2. Review error messages in log files
3. Verify database connectivity
4. Ensure API credentials are valid

---

Remember: **Always start with small positions until you're comfortable with the system!**