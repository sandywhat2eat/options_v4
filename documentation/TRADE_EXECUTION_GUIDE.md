# ⚡ Trade Execution Guide

## Overview

The Trade Execution module handles order placement, execution management, and trade lifecycle operations through the Dhan API integration with comprehensive safety controls.

## Quick Start

```bash
# Activate environment
source /Users/jaykrish/agents/project_output/venv/bin/activate

# Execute all marked strategies
python trade_execution/options_v4_executor.py --execute

# Execute specific strategy
python trade_execution/options_v4_executor.py --strategy-id 3359

# Mark strategies for execution
python trade_execution/mark_for_execution.py
```

## System Architecture

### Core Components

```
trade_execution/
├── options_v4_executor.py          # Main execution script
├── exit_manager.py                 # Exit condition management
├── exit_evaluator.py               # Exit logic evaluation
├── exit_executor.py                # Order placement & execution
├── options_portfolio_manager.py    # Portfolio orchestration
├── position_cache_manager.py       # Position caching
└── mark_for_execution.py           # Strategy marking utility
```

## Execution Process Flow

### 1. Strategy Preparation
- **Strategy Marking**: Mark strategies for execution in database
- **Validation**: Verify strategy completeness and parameters
- **Risk Checks**: Pre-execution risk validation

### 2. Order Construction
- **Leg Analysis**: Parse multi-leg strategies into individual orders
- **Price Calculation**: Determine order prices based on strategy type
- **Quantity Validation**: Ensure lot size compliance

### 3. Order Execution
- **Sequential Execution**: Execute legs in optimal order
- **Error Handling**: Retry logic for failed orders
- **Price Fetching**: Post-execution price confirmation

### 4. Position Management
- **Database Updates**: Store execution details with entry prices
- **P&L Initialization**: Set up profit/loss tracking
- **Monitoring Setup**: Enable position monitoring

## Key Features

### Multi-Leg Strategy Support
```python
# Example: Iron Condor execution
strategy_legs = [
    {'action': 'SELL', 'option_type': 'PUT', 'strike': 1400, 'qty': 1},
    {'action': 'BUY', 'option_type': 'PUT', 'strike': 1350, 'qty': 1},
    {'action': 'SELL', 'option_type': 'CALL', 'strike': 1500, 'qty': 1},
    {'action': 'BUY', 'option_type': 'CALL', 'strike': 1550, 'qty': 1}
]
```

### Intelligent Order Management
- **Order Sequencing**: Optimal leg execution order
- **Price Improvement**: Market/limit order logic
- **Partial Fill Handling**: Manages partial executions
- **Error Recovery**: Automatic retry mechanisms

### Safety Controls
```python
# Pre-execution validation
SAFETY_CHECKS = {
    'max_position_size': 500000,     # ₹5L maximum per position
    'max_daily_trades': 50,          # Maximum trades per day
    'market_hours_only': True,       # Only during market hours
    'duplicate_prevention': True     # Prevent duplicate executions
}
```

## Execution Types

### 1. Batch Execution
```bash
# Execute all marked strategies
python trade_execution/options_v4_executor.py --execute
```

### 2. Individual Strategy Execution  
```bash
# Execute specific strategy by ID
python trade_execution/options_v4_executor.py --strategy-id 3359
```

### 3. Strategy Marking
```bash
# Mark strategies for execution
python trade_execution/mark_for_execution.py
```

## Order Types & Logic

### Market Orders
- **Use Case**: Immediate execution required
- **Spread Strategies**: Market orders for spread legs
- **Slippage**: Acceptable for immediate fills

### Limit Orders
- **Use Case**: Price-sensitive executions
- **Single Legs**: Limit orders for individual options
- **Price Improvement**: Better fill prices

### Strategy-Specific Logic
```python
# Example execution logic
if strategy_type == 'Long Call':
    order_type = 'MARKET'  # Quick execution for directional plays
elif strategy_type == 'Iron Condor':
    order_type = 'LIMIT'   # Price-sensitive for spread strategies
```

## Integration with Dhan API

### Authentication
```python
# Environment variables required
DHAN_CLIENT_ID = "your_client_id"
DHAN_ACCESS_TOKEN = "your_access_token"
```

### Order Placement
```python
# Example order placement
order_response = dhan.place_order(
    security_id=security_id,
    exchange_segment='NSE_FNO',
    transaction_type='BUY',
    quantity=quantity,
    order_type='MARKET',
    product_type='INTRADAY'
)
```

### Order Status Tracking
- **Real-time Updates**: Order status monitoring
- **Fill Confirmation**: Execution price capture
- **Error Handling**: Failed order management

## Position Management

### Entry Price Tracking
```python
# Automatic entry price fetching
def fetch_entry_prices(trade_id):
    # Wait 5 seconds for order settlement
    time.sleep(5)
    
    # Fetch order details from Dhan
    order_details = dhan.get_order_by_id(order_id)
    entry_price = order_details['price']
    
    # Update database with actual entry price
    update_trade_entry_price(trade_id, entry_price)
```

### P&L Calculation Setup
- **Net Premium**: Calculate net credit/debit
- **Breakeven Points**: Determine profit/loss levels
- **Max Profit/Loss**: Set theoretical limits

### Database Integration
```python
# Trade storage structure
trade_record = {
    'strategy_id': strategy_id,
    'symbol': symbol,
    'strategy_name': strategy_name,
    'entry_date': datetime.now(),
    'entry_price': actual_entry_price,
    'net_premium': net_premium,
    'quantity': total_quantity,
    'status': 'ACTIVE'
}
```

## Risk Management

### Pre-Execution Checks
- **Capital Limits**: Ensure sufficient capital
- **Position Limits**: Check position concentration
- **Market Hours**: Validate trading hours
- **Duplicate Prevention**: Prevent re-execution

### Execution Monitoring
- **Order Status**: Track order progression
- **Partial Fills**: Handle incomplete executions
- **Failed Orders**: Error logging and alerts

### Post-Execution Validation
- **Price Verification**: Confirm reasonable fill prices
- **Position Reconciliation**: Verify database accuracy
- **Alert Generation**: Notify on execution issues

## Error Handling

### Common Errors
```python
ERROR_HANDLING = {
    'insufficient_margin': 'Reduce position size',
    'invalid_security_id': 'Check symbol mapping',
    'market_closed': 'Retry during market hours',
    'order_rejected': 'Review order parameters'
}
```

### Retry Logic
- **Transient Errors**: Automatic retry with backoff
- **Permanent Errors**: Manual intervention required
- **Logging**: Comprehensive error logging

### Alerting System
- **Email Alerts**: Critical execution failures
- **Database Logging**: All execution attempts logged
- **Status Updates**: Real-time status in database

## Monitoring Integration

### → Real-time Monitoring
Executed positions automatically monitored by the real-time monitoring system.

### → Legacy Monitoring
Positions also tracked by legacy monitoring for redundancy.

### Position Status
- **ACTIVE**: Currently monitored positions
- **CLOSED**: Exited positions
- **ERROR**: Positions with execution issues

## Common Use Cases

### 1. Daily Execution
```bash
# Morning routine: Execute overnight allocations
python trade_execution/options_v4_executor.py --execute
```

### 2. Selective Execution
```bash
# Execute only high-conviction strategies
python trade_execution/mark_for_execution.py --min-score 0.8
python trade_execution/options_v4_executor.py --execute
```

### 3. Emergency Execution
```bash
# Execute specific strategy immediately
python trade_execution/options_v4_executor.py --strategy-id 3359
```

## Configuration

### Execution Parameters
```python
# Modify in options_v4_executor.py
EXECUTION_CONFIG = {
    'order_delay': 2,           # Seconds between leg executions
    'max_retries': 3,           # Maximum retry attempts
    'price_tolerance': 0.05,    # 5% price tolerance
    'simulation_mode': False    # Set True for testing
}
```

### Risk Limits
```python
RISK_LIMITS = {
    'max_position_value': 500000,     # ₹5L per position
    'max_daily_trades': 50,           # Daily trade limit
    'max_portfolio_exposure': 0.8,    # 80% of total capital
}
```

## Troubleshooting

### Execution Failures
**Common Causes**:
- Insufficient margin
- Invalid security IDs
- Market closure
- Network issues

**Solutions**:
- Verify account balance
- Check symbol mapping
- Confirm market hours
- Check network connectivity

### Price Discrepancies
**Causes**:
- Market volatility during execution
- Bid-ask spread widening
- Liquidity issues

**Solutions**:
- Use limit orders for price-sensitive strategies
- Execute during high liquidity periods
- Review execution timing

### Database Sync Issues
**Causes**:
- Failed database updates
- Network connectivity
- Transaction rollbacks

**Solutions**:
- Check database connectivity
- Review transaction logs
- Manual data reconciliation

## Advanced Features

### Smart Order Routing
- **Leg Optimization**: Optimal execution sequence
- **Market Conditions**: Adapt to current market state
- **Liquidity Assessment**: Route to best execution venue

### Portfolio-Level Controls
- **Exposure Limits**: Total portfolio exposure controls
- **Sector Limits**: Industry concentration limits
- **Strategy Limits**: Maximum positions per strategy type

### Performance Analytics
- **Execution Quality**: Track slippage and fill quality
- **Timing Analysis**: Optimal execution timing
- **Cost Analysis**: Transaction cost monitoring

**⚡ Trade Execution: Precise, reliable order management with comprehensive safety controls**