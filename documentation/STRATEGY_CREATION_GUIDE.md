# 📊 Strategy Creation Guide

## Overview

The Strategy Creation module analyzes market conditions, profiles stocks, and generates optimal options strategies with precise strike selection and exit conditions.

## Quick Start

```bash
# Activate environment
source /Users/jaykrish/agents/project_output/venv/bin/activate

# Analyze entire portfolio
python main.py

# Analyze specific symbol
python main.py --symbol RELIANCE

# Adjust risk tolerance
python main.py --risk aggressive

# Run without database storage
python main.py --no-database
```

## System Architecture

### Core Components

```
strategy_creation/
├── data_manager.py              # Market data fetching & processing
├── iv_analyzer.py               # Implied volatility analysis
├── probability_engine.py        # Probability calculations
├── stock_profiler.py            # Stock profiling & volatility bucketing
├── strike_selector.py           # Intelligent strike selection
├── market_conditions_analyzer.py # Market direction analysis
└── strategies/                  # Strategy implementations
    ├── directional/             # Long Call/Put, Bull/Bear Spreads
    ├── neutral/                 # Iron Condor, Butterfly, Iron Butterfly
    ├── volatility/              # Straddles, Strangles
    ├── income/                  # Covered Call, Cash-Secured Put
    └── advanced/                # Calendar, Diagonal, Ratio spreads
```

## Process Flow

### 1. Market Data Analysis
- **Data Manager**: Fetches liquid options, spot prices, lot sizes
- **Stock Profiler**: Creates volatility profile (low/medium/high/extreme)
- **Market Analyzer**: Determines market direction (Bullish/Bearish/Neutral)

### 2. Strategy Selection
- **Metadata System**: Intelligent strategy selection based on market conditions
- **Volatility Matching**: Strategies matched to stock volatility profile
- **Direction Filtering**: Strategies aligned with market direction

### 3. Strike Selection
- **Intelligent Strike Selector**: Delta-based strike selection
- **Liquidity Filtering**: Ensures adequate open interest and volume
- **Fallback Logic**: Multiple strike selection methods

### 4. Strategy Construction
- **Multi-Strategy Generation**: 25-30 strategies per symbol
- **Probability Calculation**: PoP, max profit/loss, breakevens
- **Greeks Calculation**: Delta, gamma, theta, vega

### 5. Strategy Ranking
- **Composite Scoring**: Probability + Risk/Reward + Direction + IV fit
- **Quality Filtering**: Minimum probability and score thresholds
- **Exit Condition Generation**: Automated exit logic for each strategy

## Key Features

### Stock Profiler
```python
# Volatility bucketing based on ATR%, Beta, and correlation
volatility_buckets = {
    'low': {'atr_pct': [0.5, 1.5], 'preferred_strategies': ['Iron Condor', 'Calendar Spread']},
    'medium': {'atr_pct': [1.5, 2.5], 'preferred_strategies': ['Bull Put Spread', 'Iron Butterfly']},
    'high': {'atr_pct': [2.5, 4.0], 'preferred_strategies': ['Long Straddle', 'Short Strangle']},
    'extreme': {'atr_pct': [4.0, 10.0], 'preferred_strategies': ['Long Options', 'Wide Spreads']}
}
```

### Market Conditions Analysis
- **Direction**: Bullish/Bearish/Neutral with strength (Weak/Moderate/Strong)
- **Confidence**: 0-100% confidence in direction
- **Timeframe**: Short-term (1-5 days) vs Mid-term (10-30 days)
- **IV Environment**: LOW/SUBDUED/NORMAL/ELEVATED/HIGH based on real historical percentiles

### IV Analysis System (Enhanced June 28, 2025)
- **✅ Real Historical Data**: Actual IV percentiles from 7+ days of historical data (not estimates)
- **✅ Accurate Rankings**: True percentile rankings from historical_iv_summary table
- **✅ Environment Classification**: 
  - LOW: < 20th percentile (buy volatility opportunities)
  - SUBDUED: 20-40th percentile (moderate volatility buying)
  - NORMAL: 40-60th percentile (directional strategies preferred)
  - ELEVATED: 60-80th percentile (moderate volatility selling)
  - HIGH: > 80th percentile (sell volatility opportunities)
- **✅ Strategy Optimization**: Better strategy selection based on actual IV vs historical ranges
- **✅ Growing Dataset**: Daily collection improves accuracy over time

### Strategy Metadata System
```python
# Example strategy metadata
LONG_CALL = {
    'market_views': ['bullish'],
    'iv_preference': ['low', 'normal'],
    'volatility_suitability': ['medium', 'high'],
    'max_loss_type': 'limited',
    'profit_potential': 'unlimited',
    'time_decay': 'negative'
}
```

## Configuration

### Risk Tolerance Levels
- **Conservative**: Lower delta targets, higher probability strategies
- **Moderate**: Balanced approach (default)
- **Aggressive**: Higher delta targets, directional strategies

### Quality Thresholds
```python
MIN_PROBABILITY_SCORE = 0.45    # Minimum probability of profit
MIN_TOTAL_SCORE = 0.50         # Minimum composite score
MIN_POSITION_SIZE = 20000      # Minimum position size in ₹
```

## Output Format

### Strategy Analysis Results
```json
{
  "success": true,
  "symbol": "RELIANCE",
  "spot_price": 1466.2,
  "market_analysis": {
    "direction": "Bullish",
    "confidence": 0.72,
    "iv_environment": "LOW"
  },
  "top_strategies": [
    {
      "rank": 1,
      "name": "Diagonal Spread",
      "total_score": 0.7535,
      "probability_profit": 0.593,
      "max_profit": 2370.0,
      "max_loss": 630.0,
      "legs": [...],
      "exit_conditions": {...}
    }
  ]
}
```

## Common Use Cases

### 1. Daily Analysis
```bash
# Analyze all portfolio symbols
python main.py

# Results saved to results/options_v4_analysis_YYYYMMDD_HHMMSS.json
```

### 2. Single Stock Analysis
```bash
# Focus on specific symbol
python main.py --symbol TATASTEEL
```

### 3. Market Direction Testing
```bash
# Test with different risk levels
python main.py --risk conservative  # More neutral strategies
python main.py --risk aggressive    # More directional strategies
```

### 4. Research Mode
```bash
# Run without database storage for testing
python main.py --no-database
```

## Integration with Other Modules

### → Portfolio Allocation
Strategy creation results feed into the portfolio allocation system for capital deployment.

### → Trade Execution
Top-ranked strategies can be marked for execution via the trade execution module.

### Database Storage
All strategies automatically stored in Supabase with complete metadata for portfolio allocation.

## Troubleshooting

### Common Issues

1. **No Liquid Options**
   - Solution: Check market hours, symbol validity
   - Fallback: System skips illiquid symbols

2. **Low Success Rate**
   - Solution: Verify API connectivity, market data availability
   - Check logs in `logs/options_v4_main_YYYYMMDD.log`

3. **Strike Not Available**
   - Solution: System auto-selects nearest available strike
   - Uses intelligent fallback hierarchy

### Performance Optimization
- **Parallel Processing**: Multiple symbols analyzed concurrently
- **Caching**: Market data cached to reduce API calls
- **Intelligent Filtering**: Pre-filters strategies based on market conditions

## Advanced Features

### Smart Expiry Selection
- **20th Date Logic**: Switches to next month after 20th
- **DTE Optimization**: Targets optimal days to expiration
- **Holiday Handling**: Accounts for market holidays

### IV Analysis (Enhanced with Historical System)
- **✅ Real Percentile Ranking**: Actual historical IV percentiles (not estimates)
- **✅ Accurate Environment Detection**: LOW/SUBDUED/NORMAL/ELEVATED/HIGH classifications
- **✅ Skew Analysis**: Put/call skew identification with sentiment analysis
- **✅ Mean Reversion**: IV reversion probability based on real historical ranges
- **✅ Daily Updates**: Percentiles refresh daily with new market data
- **Database Integration**: Uses `iv_percentiles` table for real-time lookups

### Daily IV Workflow Integration
The system automatically integrates with the IV Historical Builder:

```bash
# Before running strategy creation, ensure IV data is current:
python3 iv_historical_builder/iv_collector.py --latest    # Collect today's IV
python3 iv_historical_builder/iv_analyzer.py              # Update percentiles
python3 main.py                                           # Run strategy creation
```

**Result**: Strategies now selected based on actual IV environments rather than default assumptions

### Exit Condition Generation
- **Profit Targets**: Multiple scaling levels (25%, 50%, 75%)
- **Stop Losses**: Percentage and absolute thresholds
- **Time Exits**: DTE-based exit triggers
- **Greek Triggers**: Delta, gamma, theta thresholds

**📊 Strategy Creation: The foundation of intelligent options trading**