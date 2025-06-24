# Options V4 Trading System - Technical Reference

## System Architecture

### Core Components

```
options_v4/
├── core/                           # Core system components
│   ├── data_manager.py            # Options data fetching (50-symbol batch)
│   ├── market_conditions_analyzer.py # NIFTY/VIX/PCR analysis
│   ├── industry_allocation_engine.py # Database-driven allocation
│   ├── sophisticated_portfolio_allocator.py # Quantum-level portfolio allocation
│   ├── options_portfolio_manager.py  # Main orchestration
│   ├── strike_selector.py         # Centralized strike selection
│   ├── exit_manager.py            # Exit condition generation
│   └── probability_engine.py      # Probability calculations
│
├── strategies/                     # 22+ Strategy implementations
│   ├── base_strategy.py           # Abstract base class
│   ├── directional/               # Long/Short, Spreads (6)
│   ├── neutral/                   # Condors, Butterflies (5)
│   ├── volatility/                # Straddles, Strangles (4)
│   ├── income/                    # CSP, Covered Calls (2)
│   └── advanced/                  # Calendars, Ratios (5)
│
├── analysis/                       # Market analysis modules
│   ├── technical_analyzer.py      # Technical indicators
│   ├── price_levels_analyzer.py   # Support/resistance
│   └── iv_analyzer.py             # IV analysis & skew
│
├── database/                       # Database integration
│   └── supabase_integration.py    # Complete DB interface
│
├── execution/                      # Trading execution
│   ├── deploy_sophisticated_allocator.py # Production allocator deployment
│   ├── validate_sophisticated_allocator.py # Allocator validation
│   ├── mark_for_execution.py      # Strategy selection (legacy)
│   ├── options_v4_executor.py     # Order execution
│   └── execution_status.py        # Monitoring
│
└── results/                        # Output files and reports
```

### Data Flow Architecture

```
1. Data Collection
   ├── Dhan API → Options Chain Data
   ├── Database → Industry Allocations
   └── YFinance → Price History

2. Analysis Pipeline
   ├── Market Conditions Analysis
   │   ├── NIFTY Technical (9 indicators)
   │   ├── VIX Environment (5 levels)
   │   └── PCR Sentiment (3 states)
   │
   ├── Industry Allocation
   │   ├── Weight-based prioritization
   │   ├── Position type matching
   │   └── Risk distribution
   │
   ├── Sophisticated Portfolio Allocation
   │   ├── VIX-based strategy selection
   │   ├── Quantum scoring (7 components)
   │   ├── Kelly Criterion position sizing
   │   └── Intelligent fallback hierarchy
   │
   └── Strategy Generation
       ├── Market-aligned selection
       ├── Strike optimization
       └── Exit condition creation

3. Storage & Execution
   ├── Database Storage (12+ tables)
   ├── Sophisticated Allocation (automated)
   ├── Order Execution (Dhan API)
   └── Performance Monitoring
```

## Strategy Implementation

### Base Strategy Pattern

All strategies inherit from `BaseStrategy`:

```python
class BaseStrategy(ABC):
    def __init__(self, symbol, spot_price, options_df, lot_size, market_analysis):
        self.symbol = symbol
        self.spot_price = spot_price
        self.options_df = options_df
        self.lot_size = lot_size
        self.market_analysis = market_analysis
        self.strike_selector = IntelligentStrikeSelector()
    
    @abstractmethod
    def construct_strategy(self, **kwargs) -> Dict
    
    @abstractmethod
    def get_strategy_name(self) -> str
    
    @abstractmethod
    def get_market_outlook(self) -> str
    
    @abstractmethod
    def get_iv_preference(self) -> str
```

### Strategy Categories

1. **Directional Strategies** (6 total)
   - Long Call/Put: Simple directional bets
   - Bull/Bear Call Spreads: Limited risk directional
   - Bull/Bear Put Spreads: Credit directional
   - **Recent Fix**: Improved selection probability from 0% to normal levels

2. **Neutral Strategies** (5 total)
   - Iron Condor: Range-bound, high probability
   - Iron Butterfly: ATM neutral, high theta
   - Butterfly Spread: Low-cost neutral
   - Short Straddle/Strangle: Pure premium collection
   - **Recent Fix**: Reduced bias towards neutral strategies

3. **Volatility Strategies** (4 total)
   - Long Straddle/Strangle: Volatility expansion
   - Short Straddle/Strangle: Volatility contraction

4. **Income Strategies** (2 total)
   - Cash-Secured Put: Stock acquisition + income
   - Covered Call: Stock holding + income

5. **Advanced Strategies** (5 total)
   - Calendar/Diagonal: Time decay arbitrage
   - Call/Put Ratio: Directional with edge
   - Jade Lizard: No upside risk neutral
   - Broken Wing Butterfly: Asymmetric risk

## Strike Selection System

### Centralized Strike Selector

The `IntelligentStrikeSelector` provides:

```python
class IntelligentStrikeSelector:
    def select_strikes(self, strategy_type, options_df, spot_price, market_analysis):
        # 1. Get strategy configuration
        strike_requests = self.strategy_configs[strategy_type]
        
        # 2. Process each strike requirement
        for request in strike_requests:
            strike = self._select_single_strike(request, ...)
            
        # 3. Validate relationships
        self._validate_strike_relationships(strikes, strategy_type)
        
        # 4. Return selected strikes
        return strikes
```

### Selection Algorithm

1. **Target Calculation**: Based on expected moves, moneyness, or ATM
2. **Candidate Filtering**: Liquidity, moneyness constraints
3. **Scoring**: Distance (40%), Liquidity (30%), Spread (20%), Volume (10%)
4. **Fallback Logic**: Relaxed constraints if no matches found

## Market Analysis

### Technical Analysis (9 Indicators)

1. **Trend**: EMA alignment, price position
2. **Momentum**: RSI, MACD signal
3. **Volatility**: Bollinger Band width, ATR
4. **Volume**: Volume ratio, trend
5. **Pattern**: Consolidation, breakout detection

### Market Conditions (9 States)

```
Direction (3) × IV Environment (3) = 9 States
- Bullish + Low IV
- Bullish + Normal IV  
- Bullish + High IV
- Neutral + Low IV
- Neutral + Normal IV
- Neutral + High IV
- Bearish + Low IV
- Bearish + Normal IV
- Bearish + High IV
```

### IV Analysis

- **IV Percentile**: Historical ranking
- **IV Skew**: Put/Call skew analysis
- **Term Structure**: Front/back month comparison
- **Mean Reversion**: Expected IV movement

## Database Schema

### Core Tables

1. **strategies** - Main strategy records
2. **strategy_details** - Individual option legs
3. **strategy_parameters** - Risk/reward metrics
4. **strategy_execution_status** - Execution tracking
5. **strategy_monitoring** - Live monitoring data
6. **strategy_exit_levels** - Exit conditions

### Allocation Tables

1. **industry_allocations_current** - Industry weights
2. **sector_allocations_current** - Sector breakdown
3. **stock_industry_mapping** - Symbol mapping

### Market Data Tables

1. **option_chain_data** - Live options data
2. **nifty_historical_data** - Index history
3. **india_vix_data** - VIX history

## Performance Metrics

### System Performance

- **Analysis Speed**: 50 symbols in ~18 minutes
- **Success Rate**: 68% (34/50 symbols)
- **Database Storage**: <5 seconds per symbol
- **Execution Speed**: 4.2 seconds per strategy

### Strategy Performance Tracking

```python
# Key metrics tracked
{
    'total_trades': int,
    'win_rate': float,  # Percentage
    'avg_profit': float,
    'avg_loss': float,
    'profit_factor': float,  # Total profits / Total losses
    'sharpe_ratio': float,
    'max_drawdown': float,
    'avg_days_in_trade': float
}
```

## Configuration

### Environment Variables

```bash
# Required
SUPABASE_URL=
SUPABASE_ANON_KEY=
DHAN_CLIENT_ID=
DHAN_ACCESS_TOKEN=

# Optional
LOG_LEVEL=INFO
MAX_WORKERS=4
BATCH_SIZE=10
```

### System Parameters

```python
# In config/options_config.py
DEFAULT_CONFIG = {
    'max_symbols': 50,
    'min_liquidity_oi': 100,
    'min_volume': 0,
    'max_spread_pct': 0.10,
    'strike_selection_mode': 'centralized',
    'exit_management': {
        'profit_target_mode': 'percentage',
        'stop_loss_mode': 'percentage',
        'time_exit_dte': 7
    }
}
```

## API Integration

### Dhan API

```python
# Order placement
dhan.place_order(
    security_id=security_id,
    exchange_segment=dhan.NSE_FNO,
    transaction_type=transaction_type,
    quantity=quantity,
    order_type=dhan.LIMIT,
    product_type=dhan.MARGIN,
    price=limit_price
)
```

### Supabase Integration

```python
# Strategy storage
supabase.table('strategies').insert({
    'stock_name': symbol,
    'strategy_name': strategy_name,
    'strategy_type': strategy_type,
    'probability_of_profit': probability,
    'risk_reward_ratio': rr_ratio,
    'max_profit': max_profit,
    'max_loss': max_loss
}).execute()
```

## Error Handling

### Common Error Patterns

1. **Strike Availability**: Automatic fallback to nearest
2. **Low Liquidity**: Skip or reduce size
3. **API Timeouts**: Retry with exponential backoff
4. **Database Errors**: Local caching + retry
5. **NaN Values**: Clean before JSON serialization

### Logging System

```python
# Log levels and locations
INFO: General flow → options_v4_main_YYYYMMDD.log
WARNING: Non-critical issues → same file
ERROR: Critical failures → same file + console
DEBUG: Detailed trace → enabled with --debug flag
```

## Optimization & Scaling

### Performance Optimizations

1. **Parallel Processing**: ThreadPoolExecutor for symbols
2. **Batch Operations**: Database inserts/updates
3. **Caching**: Strike availability, security mappings
4. **Query Optimization**: Indexed lookups, views

### Scaling Considerations

- **API Rate Limits**: 1000 requests/minute (Dhan)
- **Database Connections**: Connection pooling
- **Memory Usage**: ~2GB for 50-symbol analysis
- **CPU Usage**: Multi-core utilization

## Security Considerations

1. **API Keys**: Environment variables only
2. **Database**: Row-level security (RLS)
3. **Logging**: No sensitive data in logs
4. **Error Messages**: Sanitized output

## Maintenance

### Daily Tasks
- Archive old results (>30 days)
- Check error logs
- Verify database connectivity

### Weekly Tasks
- Update security master
- Review performance metrics
- Clean execution records

### Monthly Tasks
- Database optimization
- Performance analysis
- Strategy effectiveness review