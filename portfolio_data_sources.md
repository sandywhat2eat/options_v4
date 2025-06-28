# Portfolio Data Sources - Where Your Position Data Comes From

## Current Implementation Gap

**The Issue**: Your current Options V4 system generates trading strategies but doesn't have a real portfolio tracking system connected to your actual broker positions.

## What You Need: Data Integration Points

### 1. **Broker API Integration** (Primary Source)
Your actual positions should come from your broker's API:

```python
# Example broker integration structure
class BrokerPortfolioFetcher:
    def fetch_positions(self):
        """
        Connect to broker API (Zerodha, ICICI Direct, etc.)
        Returns: List of current positions with:
        - Symbol, Strategy Type
        - Entry price, Current price
        - Quantity, Lot size
        - Greeks from broker
        - P&L data
        """
```

**Popular Indian Broker APIs:**
- **Zerodha Kite Connect**: Most comprehensive API
- **ICICI Breeze API**: Good for ICICI Direct users
- **5Paisa API**: Budget-friendly option
- **Alice Blue API**: Good documentation

### 2. **Database Integration** (Your Supabase)
Your system already stores strategies in Supabase. You need to:

```python
# Fetch from your existing database
class DatabasePortfolioFetcher:
    def fetch_active_positions(self):
        """
        Query Supabase for:
        - Strategies with status = 'ACTIVE'
        - Entry details from strategy_recommendations
        - Match with current market prices
        """
        
        query = """
        SELECT * FROM strategy_recommendations 
        WHERE status = 'ACTIVE' 
        AND expiry_date > NOW()
        """
```

### 3. **Manual CSV/Excel Upload**
For testing or manual tracking:

```python
# CSV format example
# symbol,strategy,entry_date,expiry,premium_paid,lots,status
# RELIANCE,Iron Condor,2025-01-28,2025-02-27,18000,1,ACTIVE
# TCS,Long Call,2025-01-28,2025-02-27,12000,1,ACTIVE
```

### 4. **Real-Time Market Data Integration**
To calculate current values:

```python
class MarketDataFetcher:
    def get_option_prices(self, symbol, expiry, strikes):
        """
        Fetch from:
        - NSE website (free but delayed)
        - Broker APIs (real-time)
        - Market data vendors
        """
```

## Implementation Steps for You

### Step 1: Connect to Your Broker
```python
# Add to your options_v4 system
from broker_apis import ZerodhaConnect  # or your broker

class LivePortfolioMonitor(PortfolioMonitor):
    def __init__(self, broker_api_key, broker_secret):
        super().__init__()
        self.broker = ZerodhaConnect(api_key, secret)
    
    def sync_positions(self):
        """Fetch live positions from broker"""
        positions = self.broker.positions()
        
        for pos in positions:
            if pos['instrument_type'] == 'OPT':
                self.add_position({
                    'symbol': pos['tradingsymbol'],
                    'strategy_name': self._identify_strategy(pos),
                    'entry_date': pos['exchange_timestamp'],
                    'expiry_date': pos['expiry'],
                    'premium_paid': pos['buy_value'],
                    'premium_collected': pos['sell_value'],
                    # Greeks from broker or calculate
                    'delta': self._calculate_delta(pos),
                    'theta': self._calculate_theta(pos),
                    # ... other fields
                })
```

### Step 2: Link to Your Database
```python
# Extend your existing database integration
class EnhancedDatabaseIntegration:
    def fetch_active_portfolio(self):
        """Get all active positions from Supabase"""
        response = self.supabase.table('strategy_recommendations')\
            .select('*')\
            .eq('status', 'ACTIVE')\
            .execute()
        
        return self._format_as_positions(response.data)
    
    def update_position_status(self, position_id, current_price, pnl):
        """Update position with current market data"""
        self.supabase.table('strategy_recommendations')\
            .update({
                'current_price': current_price,
                'unrealized_pnl': pnl,
                'last_updated': datetime.now()
            })\
            .eq('id', position_id)\
            .execute()
```

### Step 3: Create Portfolio Sync Service
```python
# New file: portfolio_sync.py
class PortfolioSyncService:
    def __init__(self, broker_config, db_config):
        self.broker = BrokerAPI(**broker_config)
        self.db = DatabaseIntegration(**db_config)
        self.monitor = PortfolioMonitor()
    
    def sync_all_sources(self):
        """Combine broker + database positions"""
        # 1. Get broker positions
        broker_positions = self.broker.get_positions()
        
        # 2. Get database positions
        db_positions = self.db.fetch_active_portfolio()
        
        # 3. Reconcile differences
        reconciled = self._reconcile_positions(
            broker_positions, 
            db_positions
        )
        
        # 4. Update portfolio monitor
        for position in reconciled:
            self.monitor.add_position(position)
        
        return self.monitor.get_portfolio_summary()
```

## Quick Start for Your Current System

### Option 1: Manual Entry (Immediate)
```python
# Create a positions.json file
{
    "positions": [
        {
            "symbol": "RELIANCE",
            "strategy_name": "Iron Condor",
            "entry_date": "2025-01-28",
            "expiry_date": "2025-02-27",
            "legs": [
                {"strike": 2400, "type": "PE", "action": "SELL", "premium": 50},
                {"strike": 2300, "type": "PE", "action": "BUY", "premium": 20},
                {"strike": 2600, "type": "CE", "action": "SELL", "premium": 45},
                {"strike": 2700, "type": "CE", "action": "BUY", "premium": 15}
            ]
        }
    ]
}
```

### Option 2: Use Your Existing Supabase
```python
# Modify your main.py to track executed strategies
if self.enable_database:
    # After storing strategy recommendation
    self.db_integration.create_position_tracking(
        strategy_result,
        status='PENDING_EXECUTION'
    )
```

### Option 3: Broker API Integration
Choose based on your broker:
- **Zerodha**: Use kiteconnect library
- **ICICI**: Use breeze-connect
- **5Paisa**: Use py5paisa

## Missing Pieces in Your Current System

1. **No Position Tracking Table**: Add to your database schema
2. **No Broker Integration**: Need to connect to actual positions
3. **No P&L Calculation**: Need market data feed
4. **No Execution Tracking**: Link recommendations to actual trades

## Next Steps

1. **Immediate**: Create manual position tracking file
2. **Short-term**: Add position tracking to Supabase
3. **Medium-term**: Integrate broker API
4. **Long-term**: Real-time P&L with market data feeds

The portfolio monitor I created is just the visualization layer - you need to connect it to your actual position data sources!