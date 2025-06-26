# Advanced Options Allocator - Complete Guide

## Overview

The Advanced Options Allocator is a sophisticated portfolio allocation system that automatically selects the best options strategies based on market conditions, industry allocations, and real-time data analysis.

## Quick Start

### Prerequisites

1. **Environment Setup**
   ```bash
   source /Users/jaykrish/agents/project_output/venv/bin/activate
   ```

2. **Environment Variables** (in root .env file)
   ```
   SUPABASE_URL=your_supabase_url
   SUPABASE_ANON_KEY=your_supabase_key
   DHAN_CLIENT_ID=your_dhan_client_id
   DHAN_ACCESS_TOKEN=your_dhan_access_token
   ```

### Basic Usage

```bash
cd advanced_allocator/

# Run with 1 crore capital (default)
python runner.py

# Run with custom capital amount
python runner.py --capital 1000000    # 10 lakh
python runner.py --capital 5000000    # 50 lakh

# Run with custom VIX level (optional)
python runner.py --capital 1000000 --vix 15.5

# Save to custom output file
python runner.py --output my_allocation.json

# Run in dry-run mode (no database updates)
python runner.py --dry-run

# Update database with allocations
python runner.py --update-database
```

## System Architecture

### Core Components

1. **Market Direction Analyzer** (`core/market_direction.py`)
   - Analyzes real-time market conditions using Dhan API
   - Combines technical analysis, options flow, and price action
   - Provides directional bias and confidence levels

2. **Industry Allocator** (`core/industry_allocator.py`)
   - Uses `industry_allocations_current` table for sector allocation
   - Maps industries to position types (LONG/SHORT)
   - Selects best strategies per symbol based on total_score

3. **Market Cap Allocator** (`core/market_cap_allocator.py`)
   - Distributes capital across market cap categories
   - Adjusts allocations based on VIX levels
   - Handles Large/Mid/Small/Micro cap distributions

4. **Stock Selector** (`core/stock_selector.py`)
   - Ranks symbols using composite scoring
   - Filters by minimum score thresholds
   - Ensures diversification across sectors

5. **Position Sizer** (`core/position_sizer.py`)
   - Calculates position sizes using Kelly Criterion
   - Considers probability of profit and risk-reward ratios
   - Implements risk management controls

### Data Flow

```
Market Analysis → Industry Allocation → Market Cap Distribution → 
Stock Selection → Strategy Selection → Position Sizing → Portfolio Output
```

## Market Analysis Details

### Technical Analysis Score (40% weight)
- **Momentum Score**: Based on price momentum (0-1 scale)
- **Overall Strength**: Technical strength indicators
- **RSI Analysis**: Overbought/oversold conditions
- **Confidence Scaling**: Applied based on data quality

### Options Flow Score (35% weight)
- **PCR Analysis**: Put-Call Ratio interpretation (contrarian)
- **Volume PCR**: Immediate market sentiment
- **Open Interest PCR**: Longer-term positioning
- **Weighted Combination**: 50% Volume + 30% PCR + 20% OI

### Price Action Score (25% weight)
- **Momentum Data**: Direct from market conditions analyzer
- **Trend Analysis**: Short and medium-term trends
- **Support/Resistance**: Key technical levels

## Industry Allocation System

### Data Source
- Uses `industry_allocations_current` table from Supabase
- Each industry has a position_type: LONG or SHORT
- Weight percentages determine capital allocation

### Symbol Mapping Process
1. Fetch industries from allocation table
2. Query `strategies` table for symbols in each industry
3. Select best strategy per symbol (highest total_score)
4. Ensure no symbol appears in both LONG and SHORT

### Strategy Selection Logic
```python
# For each industry, get best strategy per symbol
SELECT stock_name, total_score, strategy_name, probability_of_profit, risk_reward_ratio
FROM strategies 
WHERE industry = ? AND total_score >= 0.4
ORDER BY total_score DESC
```

## Market Cap Distribution

### Base Allocations
- **Neutral Market**: Large 45%, Mid 30%, Small 20%, Micro 5%
- **Bullish Market**: Increased small/mid cap exposure
- **Bearish Market**: Defensive shift to large caps

### VIX Adjustments
- **Low VIX (<15)**: Increased small cap allocation
- **High VIX (>25)**: Defensive positioning
- **Current VIX** (12.96): Low volatility regime

## Output Format

### Terminal Display
```
MARKET DIRECTION ANALYSIS
Technical Analysis Score: 0.089 (Weight: 40%)
Options Flow Score: 0.000 (Weight: 35%)
Price Action Score: 0.139 (Weight: 25%)
Composite Score: 0.070
Market State: NEUTRAL
Confidence: 60.0%
Long/Short Allocation: 50%/50%

PORTFOLIO SUMMARY
Total Positions: 20
Long Positions: 5 | Short Positions: 15
Total Premium at Risk: ₹100,000
Total Position Value: ₹1,000,000
Average Probability: 62.6%
```

### JSON Output
```json
{
  "market_analysis": {
    "market_state": "neutral",
    "direction_score": 0.07,
    "confidence": 0.6,
    "technical_score": 0.089,
    "options_flow_score": 0.0,
    "price_action_score": 0.139
  },
  "allocations": [
    {
      "symbol": "ADANIPORTS",
      "strategy_name": "Butterfly Spread",
      "position_type": "LONG",
      "allocated_capital": 50000,
      "number_of_lots": 1,
      "premium_at_risk": 5000,
      "probability_of_profit": 0.67,
      "total_score": 0.82
    }
  ]
}
```

## Configuration

### Market Conditions (`config/market_conditions.yaml`)
```yaml
neutral:
  large_cap: 45
  mid_cap: 30
  small_cap: 20
  micro_cap: 5

bullish:
  large_cap: 35
  mid_cap: 35
  small_cap: 25
  micro_cap: 5
```

### Strategy Filters (`config/strategy_filters.yaml`)
```yaml
min_total_score: 0.4
min_probability: 0.35
max_positions_per_cap: 10
risk_percentage: 2.0
```

## Database Tables Used

1. **industry_allocations_current**
   - Fields: industry, position_type, weight_percentage, rating
   - Purpose: Sector allocation and position bias

2. **strategies**
   - Fields: stock_name, industry, total_score, strategy_name, probability_of_profit
   - Purpose: Strategy data and scoring

3. **stock_rankings**
   - Fields: symbol, market_cap_category
   - Purpose: Market cap classification

## Error Handling

### Market Data Failures
- System fails gracefully if MarketConditionsAnalyzer unavailable
- No fallback to mock data (production requirement)
- Comprehensive error logging

### Database Issues
- Connection validation before processing
- Graceful handling of missing tables
- Detailed error messages for debugging

### Strategy Selection Failures
- Fallback to next best strategy if primary unavailable
- Minimum score threshold enforcement
- Warning logs for low-quality selections

## Performance Metrics

- **Processing Time**: ~10-15 seconds for full allocation
- **Database Queries**: Optimized batch queries for efficiency
- **Memory Usage**: Minimal footprint with proper cleanup
- **Success Rate**: 100% allocation when data available

## Monitoring and Logs

### Log Files
- `logs/advanced_allocator_YYYYMMDD.log`: Main system logs
- `results/advanced_allocation_YYYYMMDD_HHMMSS.json`: Allocation outputs

### Key Metrics to Monitor
- Market analysis scores (should not be zero)
- Number of positions generated
- Total capital allocated
- Average probability of profit

## Troubleshooting

### Common Issues

1. **Zero Market Scores**
   - Check MarketConditionsAnalyzer connectivity
   - Verify Dhan API credentials
   - Review market hours

2. **No Positions Generated**
   - Check industry_allocations_current table data
   - Verify strategies table has data with total_score >= 0.4
   - Review market cap allocation logic

3. **Low Position Count**
   - Increase capital amount
   - Lower minimum score threshold
   - Check symbol availability in stock_rankings

### Debug Mode
```bash
# Enable detailed logging
python runner.py --capital 1000000 --verbose

# Check specific components
python -c "from core.market_direction import MarketDirectionAnalyzer; print('OK')"
```

## Integration with Legacy System

The Advanced Allocator can work alongside the existing options_v4 system:

1. **Strategy Generation**: Use legacy `main.py` to populate strategies table
2. **Allocation**: Use Advanced Allocator for portfolio allocation
3. **Execution**: Use legacy `options_v4_executor.py` for trade execution
4. **Monitoring**: Use legacy monitoring tools for position tracking

## Future Enhancements

1. **Real-time Updates**: WebSocket integration for live market data
2. **Risk Management**: Advanced position sizing with correlation analysis
3. **Portfolio Optimization**: Multi-objective optimization algorithms
4. **Machine Learning**: Predictive models for strategy selection
5. **Backtesting**: Historical performance analysis capabilities

## Support

For issues or questions:
1. Check logs in `logs/` directory
2. Review database table contents
3. Verify environment variables
4. Test with smaller capital amounts first