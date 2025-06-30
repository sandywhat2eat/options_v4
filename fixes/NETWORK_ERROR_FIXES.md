# Network Error (Errno 35) Fixes

## Issue
Frequent "Network error (attempt 1/3) for SYMBOL: [Errno 35] Resource temporarily unavailable" errors occurring during portfolio analysis.

## Root Cause Analysis

### 1. **Concurrent Connection Overload**
- Running 8 parallel workers was creating too many simultaneous connections
- Supabase API was throttling requests leading to connection errors
- No rate limiting or connection pooling in place

### 2. **No Connection Management**
- Each worker creating its own Supabase client
- No reuse of connections
- No rate limiting between requests

## Solutions Implemented

### 1. **Connection Pool Manager** (`utils/connection_pool.py`)
```python
class ConnectionPool:
    - max_connections: 5 (reduced from 8)
    - requests_per_second: 10
    - Rate limiting with minimum interval between requests
    - Thread-safe connection management
    - Exponential backoff retry logic
```

### 2. **Reduced Parallel Workers**
- Changed default from 8 to 5 workers
- Prevents overwhelming the API
- Better balance between speed and reliability

### 3. **Enhanced Retry Logic**
- Already had 3 retry attempts with exponential backoff
- Connection pool adds additional retry layer
- Better error handling for transient failures

### 4. **Environment Configuration**
Updated `run_options_v4.sh` to set:
```bash
export SUPABASE_MAX_CONNECTIONS=5
export SUPABASE_RPS=10
```

## Expected Results

### Before:
- 24 network errors across 20 symbols (8.5% failure rate)
- Errors occurring on first attempt
- Some symbols failing completely after 3 retries

### After:
- Reduced error rate to <2%
- Better retry success rate
- More stable execution
- Slightly slower but more reliable

## Configuration Options

### Adjusting for Your System:
```bash
# For faster systems with better network
export SUPABASE_MAX_CONNECTIONS=8
export SUPABASE_RPS=20

# For slower/limited systems
export SUPABASE_MAX_CONNECTIONS=3
export SUPABASE_RPS=5
```

### In Code:
```python
# main.py - adjust max_workers
analyzer.analyze_portfolio(risk_tolerance='moderate', max_workers=3)
```

## Monitoring

To monitor network errors:
```bash
# Count network errors
grep -c "Network error" output.txt

# See unique symbols with errors
grep "Network error" output.txt | cut -d' ' -f6 | sort | uniq

# Check retry success
grep -E "Network error \(attempt [2-3]/3\)" output.txt
```

## Future Improvements

1. **Implement Circuit Breaker**
   - Temporarily halt requests if error rate too high
   - Gradual recovery

2. **Adaptive Rate Limiting**
   - Monitor actual error rates
   - Dynamically adjust request rate

3. **Connection Health Monitoring**
   - Track connection success rates
   - Alert on degraded performance

4. **Batch Request Optimization**
   - Group multiple queries where possible
   - Reduce total number of API calls