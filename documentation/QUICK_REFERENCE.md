# Options V4 - Quick Reference

## Daily Commands

```bash
# Morning workflow
python main.py --risk moderate                              # Generate strategies
python sophisticated_portfolio_allocator_runner.py --update-database  # Allocate
python options_v4_executor.py --execute                    # Execute trades

# Monitoring
python execution_status.py                                  # Check status
python check_stored_data.py --today                        # Verify storage
grep ERROR logs/options_v4_main_$(date +%Y%m%d).log       # Check errors
```

## Key Scripts

| Script | Purpose | When to Use |
|--------|---------|-------------|
| `main.py` | Generate strategies | Daily, before market open |
| `sophisticated_portfolio_allocator_runner.py` | Portfolio allocation | After strategy generation |
| `options_v4_executor.py` | Execute trades | After allocation |
| `execution_status.py` | Monitor executions | Throughout the day |
| `check_stored_data.py` | Verify DB storage | After generation |
| `mark_for_execution.py` | Manual marking | As needed |
| `demo_portfolio_selection.py` | Demo strategy selection | Learning/Testing |
| `portfolio_backtesting_demo.py` | Demo backtesting | Performance analysis |

## Configuration

### Risk Profiles
- `--risk conservative` - Lower risk, income focus
- `--risk moderate` - Balanced (default)
- `--risk aggressive` - Higher risk, directional

### Allocator Options
- `--update-database` - Update DB with allocations
- `--no-database` - Dry run with mock data
- `--quiet` - Minimal output

## Important Numbers

- **Symbols**: 50 across 6 industries
- **Strategies**: Target 25-35 for execution
- **Capital**: ₹1 crore allocation
- **Max per strategy**: 5%
- **Min allocation**: 80%
- **Processing time**: ~20 minutes total

## Troubleshooting

```bash
# If strategies fail
tail -100 logs/options_v4_main_$(date +%Y%m%d).log

# If allocation fails
tail -100 logs/sophisticated_allocator_$(date +%Y%m%d).log

# If execution fails
tail -100 logs/options_v4_execution.log

# Database issues
python check_stored_data.py --debug
```

## File Locations

- **Logs**: `logs/`
- **Results**: `results/`
- **Config**: `config/options_portfolio_config.yaml`
- **Archive**: `archive/` (old scripts and docs)

## Demo Scripts

### Portfolio Selection Demo
```bash
# Learn how to select best strategies for ₹1 crore portfolio
python demo_portfolio_selection.py
```

### Backtesting Demo
```bash
# Analyze historical performance and run simulations
python portfolio_backtesting_demo.py
```

## Strategy Selection Best Practices

1. **Primary Filters**:
   - Total Score ≥ 0.5
   - Probability of Profit ≥ 40%
   - Risk-Reward Ratio ≥ 1.2
   - Conviction: MEDIUM/HIGH/VERY_HIGH

2. **Position Sizing**:
   - Max 5% per strategy (₹5 lakh)
   - Max 15% per stock
   - Max 12% per industry
   - Target 20-30 strategies

3. **VIX-Based Selection**:
   - Low VIX: Iron Condors, Premium Selling
   - Normal VIX: Balanced mix
   - High VIX: Long Options, Debit Spreads
