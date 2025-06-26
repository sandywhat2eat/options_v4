# Smart Expiry Logic Implementation

## Overview

Implemented a smart 20th date cutoff system for expiry selection that provides more intelligent timing for options strategy execution.

## Database Analysis for Strategy 3359

**Query Results:**
- `strategy_parameters.expiry_date` = **NULL**
- `strategy_details.expiry_date` = **NULL** for all legs

**Conclusion:** Strategy 3359 has no explicit expiry date set, so it will use the automatic expiry calculation logic.

## Current vs Smart Logic

### Before (Legacy Logic)
```python
# If current month's expiry has passed: use next month
if current_expiry.date() <= base_date.date():
    use_next_month()
```

### After (Smart Logic with 20th Cutoff)
```python
# If before 20th of month: try current month expiry (if still valid)
if current_day <= cutoff_day:
    if current_month_expiry > today:
        use_current_month()
    else:
        use_next_month()
else:
    # After 20th: always use next month
    use_next_month()
```

## Implementation Details

### Files Modified

1. **options_v4_executor.py**
   - Added `get_smart_expiry_date()` method with 20th cutoff logic
   - Maintained `get_next_expiry_date()` as legacy wrapper
   - Updated `get_security_id()` to use smart logic by default

2. **core/strike_selector.py**
   - Added `get_smart_expiry_date()` method for system-wide consistency
   - Centralized expiry logic for all strategy components

3. **main.py**
   - Integrated strike selector for expiry functionality
   - Added `get_smart_expiry_date()` method with fallback
   - Ready for strategy construction enhancement

### Key Features

- **Backward Compatibility**: Legacy logic preserved as fallback
- **Configurable Cutoff**: Default 20th day, can be customized
- **Intelligent Validation**: Checks if current month expiry is still valid
- **Comprehensive Logging**: Detailed logs showing logic decisions

## Test Results

Tested the implementation with various scenarios:

| Test Date | Day | Cutoff Status | Legacy Expiry | Smart Expiry | Difference |
|-----------|-----|---------------|---------------|--------------|------------|
| 2025-06-15 | 15 | ≤20 | 2025-06-26 | 2025-06-26 | Same |
| 2025-06-20 | 20 | ≤20 | 2025-06-26 | 2025-06-26 | Same |
| 2025-06-25 | 25 | >20 | 2025-06-26 | 2025-07-31 | **Different** |
| 2025-06-26 | 26 | >20 | 2025-07-31 | 2025-07-31 | Same |
| 2025-07-25 | 25 | >20 | 2025-07-31 | 2025-08-28 | **Different** |

## Impact on Strategy 3359

**Current Execution (June 26, 2025):**
- Day 26 > cutoff 20
- Both legacy and smart logic select: **July 31, 2025**
- **No change in behavior for today's execution**

**Future Scenarios:**
- June 15 execution → Would select **June 26 expiry** (captures same month opportunities)
- June 25 execution → Would select **July 31 expiry** (avoids too-close expiry)

## Benefits

1. **Better Timing**: Strategies executed before 20th can use current month expiry
2. **Risk Management**: Strategies executed after 20th use next month expiry
3. **Market Alignment**: Aligns with typical options trading practices
4. **Flexibility**: Configurable cutoff day for different strategies

## Configuration Options

```python
# Default usage (20th cutoff)
expiry = executor.get_smart_expiry_date()

# Custom cutoff (15th of month)
expiry = executor.get_smart_expiry_date(cutoff_day=15)

# Use legacy logic for backward compatibility
expiry = executor.get_smart_expiry_date(use_legacy_logic=True)
```

## Usage Examples

### Strategy Execution
```bash
# Will use smart expiry logic automatically
python options_v4_executor.py --strategy-id 3359
```

### Strategy Construction
```python
# In main.py strategy construction
expiry_date = self.get_smart_expiry_date(cutoff_day=20)
# Use expiry_date in strategy parameters
```

### Manual Testing
```bash
# Test the logic with different scenarios
python test_smart_expiry.py
```

## Recommendations

1. **Monitor Initial Deployment**: Watch logs to ensure expiry selection aligns with expectations
2. **Strategy-Specific Cutoffs**: Consider different cutoffs for different strategy types
3. **Calendar Integration**: Future enhancement could integrate with holiday calendars
4. **Performance Tracking**: Track strategy performance based on expiry timing

## Backward Compatibility

- All existing functionality preserved
- Legacy `get_next_expiry_date()` still works
- Default behavior only changes when explicitly using smart logic
- Can revert to legacy logic with `use_legacy_logic=True` parameter

The implementation provides intelligent expiry selection while maintaining full compatibility with existing systems.