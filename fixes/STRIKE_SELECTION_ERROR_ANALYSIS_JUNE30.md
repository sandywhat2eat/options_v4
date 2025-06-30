# Strike Selection Error Analysis - June 30, 2025

## Executive Summary

Analysis of `/Users/jaykrish/Documents/digitalocean/cronjobs/options_v4/output.txt` reveals **241 total strike selection errors** across 235 symbols processed, with 55 "Intelligent strike selection failed" instances requiring fallback mechanisms.

## Error Counts

| Error Type | Count | Details |
|------------|-------|---------|
| **Intelligent strike selection failed** | **55** | Complete selection system failures |
| **No candidate strikes found** | **157** | Constraint filters too restrictive |
| **Failed to find strike** | **84** | Unable to locate suitable strikes |

## Strategy-Specific Failure Patterns

### Most Affected Strategies
1. **Bull Put Spread** - 37 failures (44% of all strategy failures)
2. **Iron Condor** - 14 failures (17% of all strategy failures)  
3. **Bear Call Spread** - 9 failures (11% of all strategy failures)
4. **Long Straddle** - 8 failures (10% of all strategy failures)

### Strike Type Failure Distribution
```
long_strike:    74 failures (47% of strike-specific errors)
short_strike:   20 failures (13% of strike-specific errors)
put_long:       14 failures (9% of strike-specific errors)
call_long:      10 failures (6% of strike-specific errors)
```

## Root Cause Analysis

### 1. **Overly Restrictive Moneyness Constraints**

**Problem**: Bull Put Spread constraints are too narrow for available options data:
- `short_strike`: min_moneyness=-0.08, max_moneyness=-0.02 (6% range)
- `long_strike`: min_moneyness=-0.15, max_moneyness=-0.08 (7% range)

**Impact**: For stocks with limited strike intervals, these constraints eliminate all available strikes.

### 2. **Liquidity Requirements Mismatch**

**Problem**: Minimum liquidity requirements (open_interest >= 100, volume > 0) too high for many stocks.

**Evidence**: Error messages show "Strike X has low liquidity (OI: 0)" followed by constraint failures.

### 3. **Expected Move Calculation Issues**

**Problem**: Expected move targets place strikes outside available strike range.

**Examples**:
- `Iron Condor put_long`: target_value=-1.5 with min_moneyness=-0.20 
- `Bear Call Spread long_strike`: target_value=1.2 with min_moneyness=0.08

### 4. **Strategy Construction Cascading Failures**

**Pattern**: Strike selection failures → Strategy construction failures → Fallback to simpler strategies

**Examples**:
```
Bull Put Spread construction failed: No net credit for spread
Cash-Secured Put construction failed: Premium too low for cash-secured put
Iron Condor construction failed: Invalid strike selection
```

## Specific Error Examples

### Bull Put Spread Failure Pattern
```
No candidate strikes found for short_strike
Failed to find strike for short_strike in Bull Put Spread
No candidate strikes found for long_strike  
Failed to find strike for long_strike in Bull Put Spread
Used relaxed constraints for long_strike
Intelligent strike selection failed, using fallback
⚠️ Bull Put Spread construction failed: No net credit for spread
```

### Cash-Secured Put Failure Pattern
```
No candidate strikes found for strike
Failed to find strike for strike in Cash-Secured Put
No strikes selected for Cash-Secured Put
Intelligent strike selection failed, using fallback
⚠️ Cash-Secured Put construction failed: Premium too low for cash-secured put
```

## Impact Assessment

### Portfolio Construction Impact
- **Strategy Diversity Reduced**: Limited to simpler strategies (Long Call, Covered Call)
- **Risk Profile Skewed**: Missing neutral and income strategies
- **Execution Efficiency**: 55/235 symbols (23%) experiencing intelligent selection failures

### Performance Implications
- **Return Potential**: Missing higher probability strategies like Bull Put Spreads
- **Risk Management**: Lack of neutral strategies reduces portfolio balance
- **Market Exposure**: Over-reliance on directional strategies

## Recommended Fixes

### 1. **Relax Moneyness Constraints** (High Priority)
```python
# Current Bull Put Spread constraints
'Bull Put Spread': [
    StrikeRequest('short_strike', 'PUT', 'expected_move', -0.5,
                 StrikeConstraint(min_moneyness=-0.08, max_moneyness=-0.02)),  # Too narrow
    StrikeRequest('long_strike', 'PUT', 'expected_move', -1.2,
                 StrikeConstraint(min_moneyness=-0.15, max_moneyness=-0.08))   # Too narrow
]

# Recommended relaxed constraints
'Bull Put Spread': [
    StrikeRequest('short_strike', 'PUT', 'expected_move', -0.5,
                 StrikeConstraint(min_moneyness=-0.12, max_moneyness=-0.01)),  # Wider range
    StrikeRequest('long_strike', 'PUT', 'expected_move', -1.2,
                 StrikeConstraint(min_moneyness=-0.25, max_moneyness=-0.06))   # Wider range
]
```

### 2. **Adaptive Liquidity Requirements** (High Priority)
```python
# Implement dynamic liquidity based on stock size/volume
def get_dynamic_liquidity_requirement(self, symbol: str, market_cap: float) -> int:
    if market_cap > 50000:  # Large cap
        return 100
    elif market_cap > 10000:  # Mid cap  
        return 50
    else:  # Small cap
        return 25
```

### 3. **Enhanced Fallback Mechanisms** (Medium Priority)
```python
# Multi-tier fallback system
def get_candidate_strikes_with_fallback(self, request, options_df, spot_price):
    # Tier 1: Original constraints
    candidates = self.get_candidate_strikes_strict(request, options_df, spot_price)
    if not candidates.empty:
        return candidates
    
    # Tier 2: Relaxed moneyness (50% wider)
    candidates = self.get_candidate_strikes_relaxed(request, options_df, spot_price)
    if not candidates.empty:
        return candidates
    
    # Tier 3: Liquidity-only filter
    candidates = self.get_candidate_strikes_liquidity_only(request, options_df, spot_price)
    return candidates
```

### 4. **Strike Availability Pre-Check** (Medium Priority)
```python
def validate_strategy_feasibility(self, strategy_type: str, options_df: pd.DataFrame, 
                                spot_price: float) -> bool:
    """Pre-validate if strategy can be constructed with available strikes"""
    config = self.strategy_configs.get(strategy_type, [])
    available_strikes = self._get_available_strikes(options_df)
    
    for request in config:
        if not self._check_strike_availability(request, available_strikes, spot_price):
            return False
    return True
```

### 5. **Expected Move Calibration** (Low Priority)
```python
# Scale expected moves based on available strike range
def calibrate_expected_move(self, expected_move: float, available_range: float) -> float:
    """Scale expected move to fit within available strike range"""
    max_move = available_range * 0.8  # Use 80% of available range
    return min(expected_move, max_move)
```

## Implementation Priority

1. **Immediate (Week 1)**: Relax Bull Put Spread and Iron Condor constraints
2. **Short-term (Week 2)**: Implement adaptive liquidity requirements  
3. **Medium-term (Week 3-4)**: Enhanced fallback mechanisms
4. **Long-term (Month 2)**: Complete constraint optimization and pre-validation

## Success Metrics

- **Target**: Reduce intelligent selection failures from 55 to <10 (80% reduction)
- **Strategy Mix**: Achieve 60% income, 30% momentum, 10% volatility allocation
- **Coverage**: 95% of symbols should have at least 2 constructible strategies
- **Error Rate**: <5% strike selection failures across all symbols

## Files to Modify

1. `/Users/jaykrish/Documents/digitalocean/cronjobs/options_v4/strategy_creation/strike_selector.py` - Primary constraints
2. `/Users/jaykrish/Documents/digitalocean/cronjobs/options_v4/strategy_creation/strategies/directional/spreads.py` - Bull Put Spread logic
3. `/Users/jaykrish/Documents/digitalocean/cronjobs/options_v4/strategy_creation/strategies/neutral/iron_condor.py` - Iron Condor constraints
4. `/Users/jaykrish/Documents/digitalocean/cronjobs/options_v4/main.py` - Strategy selection logic

---

**Analysis completed**: June 30, 2025  
**Next review**: After implementing Tier 1 fixes (expected July 7, 2025)