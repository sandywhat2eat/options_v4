# Advanced Options Allocator

A modular system for sophisticated options portfolio allocation based on market conditions, industry ratings, and dynamic position sizing.

## Overview

The Advanced Options Allocator combines multiple analysis components to create a comprehensive portfolio allocation system:

1. **Market Direction Analysis** - Analyzes Nifty direction using technical indicators, options flow, and price action
2. **Industry Allocation** - Uses industry ratings (Strong Overweight, Moderate Overweight, etc.) to determine risk appetite
3. **Market Cap Allocation** - Dynamically adjusts exposure across market caps based on market conditions
4. **Stock Selection** - Scores and selects stocks within each category
5. **Strategy Selection** - Chooses appropriate options strategies based on simple criteria
6. **Position Sizing** - Calculates position sizes based on premium at risk

## Key Features

- **Dynamic Long/Short Allocation**: Adjusts long:short ratio from 80:20 (bullish) to 20:80 (bearish) based on Nifty direction
- **Market Cap Rotation**: More small/micro cap in bull markets, more large cap in bear markets
- **Industry-Based Risk**: Uses industry ratings to determine acceptable risk levels
- **Premium-Based Sizing**: Position sizing based on premium at risk, not notional value
- **VIX Adjustment**: Modifies allocations based on volatility levels

## Usage

### Basic Usage

```bash
python advanced_allocator/runner.py --capital 10000000
```

### With Custom Parameters

```bash
python advanced_allocator/runner.py \
  --capital 10000000 \
  --vix 22.5 \
  --output results/my_allocation.json \
  --update-database
```

### Command Line Options

- `--capital`: Total capital for options allocation (default: 10000000)
- `--vix`: Current VIX level (auto-fetched if not provided)
- `--output`: Output file path for results
- `--dry-run`: Run without database updates
- `--update-database`: Save allocations to database

## Configuration

### Market Conditions (config/market_conditions.yaml)

Defines:
- Market cap allocations for each market state
- Long/short ratios based on market direction
- Direction score thresholds

### Strategy Filters (config/strategy_filters.yaml)

Defines:
- Quality filters (min scores, conviction levels)
- Allowed strategies by market cap
- Risk parameters by industry rating

## Components

### 1. Market Direction Analyzer
- **Weights**: Technical (40%), Options Flow (35%), Price Action (25%)
- **Output**: Composite score from -1 (bearish) to +1 (bullish)
- **States**: strong_bullish, moderate_bullish, weak_bullish, neutral, weak_bearish, moderate_bearish, strong_bearish

### 2. Industry Allocator
- Sources allocations from `industry_allocations_current` table
- Manages both LONG and SHORT positions
- Applies risk parameters based on industry ratings

### 3. Market Cap Allocator
- **Categories**: Large Cap (>20k Cr), Mid Cap (5-20k Cr), Small Cap (500-5k Cr), Micro Cap (<500 Cr)
- Adjusts allocations based on market state and VIX
- Provides position constraints per category

### 4. Stock Selector
- Scores stocks on: Technical (30%), Fundamental (25%), Momentum (25%), Liquidity (20%)
- Applies market cap specific filters
- Inverts scores for SHORT positions

### 5. Strategy Selector
- Filters strategies based on:
  - Probability of profit
  - Conviction level
  - Total score
  - Risk-reward ratio
- Applies market cap and industry rating constraints

### 6. Position Sizer
- Uses Kelly Criterion (quarter Kelly for safety)
- Maximum 3% risk per position
- Calculates lots based on premium at risk
- Applies strategy-specific position limits

## Output

The system generates a comprehensive allocation report including:
- Market analysis and direction
- Position details with risk metrics
- Summary statistics by market cap, strategy, and industry
- Risk parameters and Kelly fractions

## Example Allocation Flow

1. Market is analyzed as "moderate_bullish" (score: 0.6)
2. Long/Short ratio set to 70:30
3. Capital allocated: Large Cap 30%, Mid Cap 30%, Small Cap 25%, Micro Cap 15%
4. Industries filtered by ratings, capital distributed
5. Stocks selected and scored within each category
6. Strategies chosen based on constraints
7. Position sizes calculated using premium at risk
8. Results saved and optionally updated in database