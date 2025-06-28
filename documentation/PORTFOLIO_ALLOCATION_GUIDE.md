# 💰 Portfolio Allocation Guide

## Overview

The Portfolio Allocation module distributes capital across selected strategies using a hybrid tier-based + industry allocation approach, targeting 4% monthly returns with 95%+ capital deployment.

## Quick Start

```bash
# Activate environment
source /Users/jaykrish/agents/project_output/venv/bin/activate

# Allocate ₹15 lakh (recommended)
python run_allocator.py 1500000

# Other capital amounts
python run_allocator.py 1000000    # ₹10 lakh
python run_allocator.py 2000000    # ₹20 lakh
```

## System Architecture

### Core Components

```
portfolio_allocation/
├── core/
│   ├── hybrid_portfolio_engine.py    # Main allocation engine
│   └── hybrid_runner.py              # Command-line interface
├── market_conditions.yaml            # Market condition configurations
└── results/                          # Allocation output files
```

## Hybrid Allocation Strategy

### Tier-Based Allocation (Primary)
```
Income Tier:     60% of capital  # Theta-positive, consistent income
Momentum Tier:   30% of capital  # Directional, trend-following
Volatility Tier: 10% of capital  # Volatility plays, event strategies
```

### Industry Weight Integration (Secondary)
- **Industry Allocations**: Uses `industry_allocations_current` table
- **Position Type Logic**: Respects LONG/SHORT designations per industry
- **Dynamic Weighting**: Industry weights determine relative allocation within tiers

### Market Condition Adaptation
```yaml
# market_conditions.yaml
neutral:
  long_percentage: 0.5      # 50% LONG positions
  short_percentage: 0.5     # 50% SHORT positions

strong_bullish:
  long_percentage: 0.8      # 80% LONG positions  
  short_percentage: 0.2     # 20% SHORT positions

strong_bearish:
  long_percentage: 0.2      # 20% LONG positions
  short_percentage: 0.8     # 80% SHORT positions
```

## Process Flow

### 1. Market Condition Assessment
- **Direction Detection**: Determines current market sentiment
- **LONG/SHORT Split**: Calculates target allocation percentages
- **Market Cap Distribution**: Large (45%), Mid (30%), Small (20%), Micro (5%)

### 2. Strategy Selection
- **Database Query**: Fetches strategies from Supabase with scores > threshold
- **Tier Mapping**: Maps strategies to Income/Momentum/Volatility tiers
- **Quality Filtering**: Filters by minimum probability and total scores

### 3. Position Sizing
- **Dynamic Sizing**: Based on strategy scores and market cap category
- **Risk Adjustment**: Position sizes adjusted for stock volatility
- **Lot Size Optimization**: Ensures positions align with lot size requirements

### 4. Capital Deployment
- **Allocation Algorithm**: Distributes capital across selected positions
- **Target Achievement**: Aims for 95%+ capital deployment
- **Income Optimization**: Targets 4%+ monthly returns

## Key Features

### Strategy-to-Tier Mapping
```python
INCOME_STRATEGIES = [
    'Butterfly Spread', 'Iron Butterfly', 'Iron Condor',
    'Cash-Secured Put', 'Covered Call', 'Bull Put Spread',
    'Bear Call Spread', 'Short Put Spread'
]

MOMENTUM_STRATEGIES = [
    'Long Call', 'Long Put', 'Bull Call Spread',
    'Bear Put Spread', 'Call Debit Spread', 'Put Debit Spread'
]

VOLATILITY_STRATEGIES = [
    'Long Straddle', 'Long Strangle', 'Calendar Spread',
    'Diagonal Spread', 'Call Ratio Spread', 'Put Ratio Spread'
]
```

### Position Type Logic
```python
# Respects database position_type field
if industry_allocation.position_type == 'LONG':
    target_strategies = [s for s in strategies if s.is_long_biased()]
elif industry_allocation.position_type == 'SHORT':
    target_strategies = [s for s in strategies if s.is_short_biased()]
```

### Quality Thresholds
```python
MIN_PROBABILITY_SCORE = 0.45    # Minimum PoP for inclusion
MIN_TOTAL_SCORE = 0.50          # Minimum composite score
MIN_POSITION_SIZE = 20000       # Minimum position size (₹20k)
MAX_POSITIONS_PER_TIER = 15     # Maximum positions per tier
```

## Market Cap Based Sizing

### Position Size Ranges
```python
POSITION_SIZING = {
    'Large Cap': {'min': 50000, 'max': 200000},    # ₹50k - ₹2L
    'Mid Cap':   {'min': 40000, 'max': 150000},    # ₹40k - ₹1.5L  
    'Small Cap': {'min': 30000, 'max': 100000},    # ₹30k - ₹1L
    'Micro Cap': {'min': 25000, 'max': 50000}      # ₹25k - ₹50k
}
```

### Risk Adjustment Factors
- **High Volatility Stocks**: Smaller position sizes
- **Low Volatility Stocks**: Larger position sizes within limits
- **Score-Based Sizing**: Higher scoring strategies get larger allocations

## Output Format

### Allocation Results
```json
{
  "timestamp": "2025-06-28T07:52:43.037736",
  "total_capital": 1500000.0,
  "portfolio_summary": {
    "total_positions": 13,
    "capital_deployed": 1499622.75,
    "deployment_percentage": 99.97,
    "expected_monthly_income": 65816.755,
    "monthly_return_percentage": 4.39,
    "tier_breakdown": {
      "INCOME": {"positions": 8, "capital": 975358.25},
      "MOMENTUM": {"positions": 4, "capital": 465344.5},
      "VOLATILITY": {"positions": 1, "capital": 58920.0}
    }
  }
}
```

### Position Details
```json
{
  "stock_name": "ADANIPORTS",
  "strategy_name": "Butterfly Spread", 
  "tier": "INCOME",
  "position_type": "LONG",
  "market_cap_category": "Large Cap",
  "allocated_capital": 173825.0,
  "number_of_lots": 13,
  "expected_monthly_income": 6545.5,
  "probability_of_profit": 0.67
}
```

## Performance Metrics

### Target Achievement
- **Capital Deployment**: 95%+ (typically 99%+)
- **Monthly Return**: 4%+ target (typically 4.2-4.5%)
- **Position Count**: 20-30 manageable positions
- **Strategy Diversity**: Good mix across all tiers

### Risk Metrics
```python
portfolio_greeks = {
    'delta': 126.99,      # Net directional exposure
    'gamma': 3.26,        # Gamma risk
    'theta': -4911.15,    # Daily theta income
    'vega': 892.93        # Volatility risk
}
```

## Configuration Options

### Market Conditions
Edit `portfolio_allocation/market_conditions.yaml`:
```yaml
# Adjust LONG/SHORT splits based on market outlook
current_condition: "neutral"    # Options: neutral, bullish, bearish

# Custom allocation percentages
custom_allocation:
  long_percentage: 0.6
  short_percentage: 0.4
```

### Tier Allocations
```python
# Modify in hybrid_portfolio_engine.py
TIER_ALLOCATIONS = {
    'INCOME': 0.60,      # 60% to income strategies
    'MOMENTUM': 0.30,    # 30% to momentum strategies  
    'VOLATILITY': 0.10   # 10% to volatility strategies
}
```

## Integration Points

### ← Strategy Creation
Consumes strategies generated by the strategy creation module with scores and metadata.

### → Trade Execution
Allocated positions can be marked for execution using the trade execution module.

### Database Dependencies
- **Strategies Table**: Source of strategies with scores
- **Industry Allocations**: LONG/SHORT position types per industry
- **Stock Rankings**: Market cap categories for position sizing

## Common Use Cases

### 1. Standard Allocation
```bash
# Allocate ₹15 lakh with current market conditions
python run_allocator.py 1500000
```

### 2. Different Capital Amounts
```bash
# Scale up/down based on available capital
python run_allocator.py 500000     # ₹5 lakh
python run_allocator.py 3000000    # ₹30 lakh
```

### 3. Dry Run Mode
```bash
# Test allocation without database writes
python portfolio_allocation/core/hybrid_runner.py --capital 1500000 --dry-run
```

## Troubleshooting

### Low Capital Deployment
**Causes**:
- Insufficient strategies meeting quality thresholds
- Position size constraints eliminating small positions
- Market cap distribution issues

**Solutions**:
- Lower MIN_PROBABILITY_SCORE threshold
- Reduce MIN_POSITION_SIZE
- Check strategy generation quality

### Target Return Shortfall
**Causes**:
- Conservative strategy selection
- Low-income strategies dominating
- Insufficient volatility tier allocation

**Solutions**:
- Increase volatility tier allocation
- Include more momentum strategies
- Adjust quality thresholds for higher-income strategies

### Unbalanced Portfolios
**Causes**:
- Industry allocation constraints
- Limited strategy diversity
- Market cap concentration

**Solutions**:
- Review industry_allocations_current table
- Expand strategy-to-tier mappings
- Adjust market cap target percentages

## Advanced Features

### Dynamic Rebalancing
- **Market Condition Changes**: Auto-adjusts LONG/SHORT ratios
- **Industry Rotation**: Responds to industry allocation updates
- **Strategy Performance**: Can weight based on historical performance

### Risk Management
- **Position Limits**: Maximum positions per stock/industry
- **Correlation Limits**: Prevents over-concentration
- **Greek Limits**: Manages portfolio-level risk exposures

### Performance Tracking
- **Allocation History**: All allocations saved with timestamps
- **Target Achievement**: Tracks deployment and return metrics
- **Strategy Distribution**: Monitors strategy diversity metrics

**💰 Portfolio Allocation: Intelligent capital deployment for consistent returns**