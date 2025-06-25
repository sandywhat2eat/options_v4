# Options V4 Trading System - User Guide

## 🚀 Quick Start

### Prerequisites
```bash
# Activate virtual environment
source /Users/jaykrish/agents/project_output/venv/bin/activate

# Ensure environment variables are set
# SUPABASE_URL, SUPABASE_ANON_KEY, DHAN_CLIENT_ID, DHAN_ACCESS_TOKEN
```

### Daily Trading Workflow

#### 1. Generate Strategies
```bash
python main.py --risk moderate
```

#### 2. Allocate Portfolio
```bash
python sophisticated_portfolio_allocator_runner.py --update-database
```

#### 3. Execute Trades
```bash
# Execute all marked strategies
python options_v4_executor.py --execute

# OR execute specific strategy
python options_v4_executor.py --strategy-id 3359
```

#### 4. Monitor Positions
```bash
# Interactive dashboard
python monitor_positions.py --detailed

# Continuous monitoring
python monitor_positions.py --continuous
```

#### 5. Automated Exit Management
```bash
# Safe testing (simulation mode)
python automated_monitor.py --once

# Alert generation only
python automated_monitor.py --alert-only --interval 10

# LIVE automated exits
python automated_monitor.py --execute --interval 5
```

## 📊 Real-Time Monitoring

### Interactive Dashboard

**Basic monitoring:**
```bash
python monitor_positions.py
```

**Detailed view with individual legs:**
```bash
python monitor_positions.py --detailed
```

**Continuous monitoring:**
```bash
python monitor_positions.py --continuous --detailed
```

### Dashboard Features
- ✅ Real-time P&L calculation
- ✅ Colored profit/loss display
- ✅ Individual leg breakdown
- ✅ Exit condition status
- ✅ Portfolio summary
- ✅ Alert highlighting

## 🤖 Automated Exit Management

### Safety Progression (Recommended)

#### Step 1: Test Run (Safe)
```bash
python automated_monitor.py --once
```
- **What it does**: Single monitoring cycle in simulation mode
- **Safety**: No real trades executed
- **Use case**: Test the system, verify exit conditions

#### Step 2: Alert Mode
```bash
python automated_monitor.py --alert-only --interval 10
```
- **What it does**: Generates alerts every 10 minutes, no execution
- **Safety**: Only creates alerts and logs
- **Use case**: Monitor system recommendations

#### Step 3: Live Automation
```bash
python automated_monitor.py --execute --interval 5
```
- **What it does**: Automatically executes exits every 5 minutes
- **Safety**: LIVE MODE - Will place real exit orders!
- **Use case**: Full automated exit management

### Exit Triggers

The system automatically monitors for:

1. **Profit Targets**
   - Primary profit targets (e.g., 50% of max profit)
   - Scaling exits (25%, 50%, 75% position closure)
   - Trailing stop activation

2. **Stop Losses**
   - Percentage-based stops (e.g., -50% of max loss)
   - Absolute value stops (e.g., ₹5,000 loss limit)
   - Time-based stop losses

3. **Time-Based Exits**
   - DTE (Days to Expiry) thresholds
   - Theta decay triggers
   - Maximum holding periods

4. **Strategy Adjustments**
   - Defensive adjustments (position under pressure)
   - Offensive adjustments (capitalize on movement)
   - Strategy-specific triggers

### Alert Urgency Levels

- **🔴 HIGH**: Immediate action required (stop losses hit)
- **🟡 MEDIUM**: Action recommended (profit targets, time exits)
- **🟢 NORMAL**: Monitoring only

## 🔧 Troubleshooting

### Common Issues

#### 1. Entry Prices Showing ₹0.00
**Problem**: Trades stored with zero entry price
**Solution**:
```bash
python update_recent_trades.py
# OR for batch update
python data_scripts/update_trade_prices.py
```

#### 2. No Positions Found
**Problem**: No open trades in monitoring system
**Check**:
- Verify trades are in database with `order_status='open'`
- Confirm strategy names match (e.g., 'Butterfly Spread')
- Check if market quote fetcher finds instruments

#### 3. Automated Monitor Not Executing
**Check**:
- Is `--execute` flag used? (Default is simulation mode)
- Are exit conditions properly configured in database?
- Check logs: `tail -f logs/automated_monitor.log`

#### 4. API Connection Issues
**Check**:
- Dhan API token is valid and not expired
- Supabase credentials are correct
- Network connectivity

### Log Files

Monitor system activity through logs:
```bash
# Main monitoring log
tail -f logs/automated_monitor.log

# Position monitoring
tail -f logs/position_monitor.log

# Exit execution history
cat logs/exit_executions.json

# Daily trading logs
tail -f logs/options_v4_main_$(date +%Y%m%d).log
```

## ⚙️ Configuration

### Exit Conditions Setup

Exit conditions are stored in database tables:

#### `strategy_exit_levels`
- Profit targets (primary, scaling)
- Stop loss levels
- Time-based exits

#### `strategy_risk_management`
- Maximum loss limits
- Position size controls
- Risk parameters

### Customizing Monitoring

#### Interval Settings
```bash
# Check every 1 minute (aggressive)
python automated_monitor.py --execute --interval 1

# Check every 15 minutes (conservative)
python automated_monitor.py --execute --interval 15
```

#### Cycle Limits
```bash
# Run for specific number of cycles
python automated_monitor.py --execute --cycles 10
```

## 🎯 Advanced Usage

### Batch Operations

#### Update Multiple Trades
```bash
python data_scripts/update_trade_prices.py
```

#### Historical Analysis
```bash
python monitor_positions.py --export trades_analysis.csv
```

### Integration with External Systems

#### Alert Notifications
- Logs are written to `logs/automated_monitor.log`
- Exit executions logged to `logs/exit_executions.json`
- Can be integrated with email/SMS systems

#### Database Monitoring
```bash
# Check stored data
python check_stored_data.py --today

# View execution status
python execution_status.py --summary
```

## 🚨 Safety Guidelines

### Production Checklist

Before enabling live automation:

1. **✅ Test in simulation mode**
   ```bash
   python automated_monitor.py --once
   ```

2. **✅ Verify exit conditions**
   - Check profit targets are reasonable
   - Confirm stop losses are appropriate
   - Validate time exits make sense

3. **✅ Monitor alert mode first**
   ```bash
   python automated_monitor.py --alert-only --interval 10
   ```

4. **✅ Start with longer intervals**
   ```bash
   python automated_monitor.py --execute --interval 15
   ```

5. **✅ Monitor logs actively**
   ```bash
   tail -f logs/automated_monitor.log
   ```

### Emergency Procedures

#### Stop Automated Monitoring
- Press `Ctrl+C` to stop the automated monitor
- The system will complete current cycle and stop safely

#### Manual Position Closure
```bash
# View current positions
python monitor_positions.py --detailed

# Close specific position manually via Dhan terminal
# OR use exit_executor directly (advanced)
```

#### System Recovery
```bash
# Fix zero-price trades
python update_recent_trades.py

# Restart monitoring
python automated_monitor.py --once  # Test first
python automated_monitor.py --execute --interval 10  # Resume
```

## 📈 Performance Monitoring

### Key Metrics

Track system performance:
- Exit execution success rate
- Average time to exit
- Profit target achievement
- Stop loss frequency

### Reports

Monitor system effectiveness:
```bash
# Position summary
python monitor_positions.py

# Execution history
cat logs/exit_executions.json | jq '.'

# Daily performance
grep "UPDATE SUMMARY" logs/automated_monitor.log
```

## 🔗 Related Documentation

- **Technical Details**: `/documentation/CLAUDE.md`
- **System Architecture**: `/documentation/OPTIONS_V4_SYSTEM_GUIDE.md`
- **Quick Reference**: `/documentation/QUICK_REFERENCE.md`

## 📞 Support

For issues or questions:
1. Check logs first: `logs/automated_monitor.log`
2. Review this user guide
3. Test in simulation mode: `python automated_monitor.py --once`
4. Verify database connections and API credentials

---

## 🏗️ Legacy Workflow (Reference)

### Previous Daily Trading Workflow

#### Morning Routine (9:00 AM - 9:30 AM)

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

**Remember: Always start with simulation mode until you're comfortable with the automated system!**