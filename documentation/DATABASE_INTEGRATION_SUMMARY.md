# Options V4 Database Integration Summary

## 📋 Overview

This document provides a comprehensive overview of the database schema, integration points, and data flow for the Options V4 trading system with Supabase.

## 🎯 Critical Execution Requirements

### **For `options_v4_executor.py` to Execute a Strategy**

The executor queries strategies with these EXACT criteria:
```sql
SELECT * FROM strategies 
WHERE marked_for_execution = TRUE 
  AND execution_status = 'marked'  -- MUST be 'marked', not 'pending'
  AND execution_priority > 0
ORDER BY execution_priority DESC;
```

**Required Field Values:**
- `marked_for_execution`: **TRUE** (boolean)
- `execution_status`: **'marked'** (string - NOT 'pending', 'executed', 'failed')
- `execution_priority`: **>= 1** (integer - higher numbers executed first)

## 📊 Core Tables

### 1. **strategies** (Main Strategy Records)
Primary table storing all generated strategies with analysis results.

**Key Columns:**
- `id`: Unique identifier
- `stock_name`: Symbol (e.g., 'DIXON')
- `strategy_name`: Full strategy name
- `strategy_type`: Category (directional, neutral, volatility, etc.)
- `total_score`: Overall strategy score (0-1)
- `probability_of_profit`: Success probability (0-1)
- `expected_profit`: Maximum profit potential
- `max_loss`: Maximum loss potential
- `conviction_level`: High/Medium/Low
- `market_outlook`: Bullish/Bearish/Neutral
- **`marked_for_execution`**: Boolean flag for execution
- **`execution_status`**: 'pending', 'marked', 'executed', 'failed'
- **`execution_priority`**: Integer priority (higher = first)
- `execution_notes`: Text notes about execution
- `generated_on`: Timestamp when created
- `executed_at`: Timestamp when executed

### 2. **strategy_details** (Option Legs)
Individual option legs that make up each strategy.

**Key Columns:**
- `id`: Unique identifier
- `strategy_id`: Foreign key to strategies table
- `leg_number`: Order of leg in strategy
- `option_type`: CE/PE (Call/Put)
- `strike_price`: Strike price
- `premium`: Option premium
- `lots`: Number of lots
- `setup_type`: BUY/SELL
- Greeks: delta, gamma, theta, vega, rho

### 3. **strategy_parameters** (Strategy Metrics)
Detailed parameters and calculations for each strategy.

**Key Columns:**
- `strategy_id`: Foreign key to strategies table
- `breakeven_points`: JSON array of breakeven prices
- `profit_ranges`: JSON array of profitable price ranges
- `expected_value`: Probability-weighted expected return
- `sharpe_ratio`: Risk-adjusted return metric
- `iv_percentile`: Current IV relative to historical
- `days_to_expiry`: DTE at strategy creation

### 4. **strategy_exit_levels** (Exit Conditions)
Granular exit conditions for each strategy.

**Key Columns:**
- `strategy_id`: Foreign key to strategies table
- `profit_target_1` through `profit_target_3`: Tiered profit targets
- `stop_loss`: Maximum acceptable loss
- `time_exit_dte`: Days to expiry trigger
- `delta_exit_threshold`: Delta-based exit trigger
- `vega_exit_threshold`: Vega-based exit trigger

### 5. **industry_allocations_current** (Industry Weights)
Current industry allocation targets.

**Key Columns:**
- `industry`: Industry name
- `weight_percentage`: Target allocation percentage
- `position_type`: LONG/SHORT bias
- `rating`: Overweight/Neutral/Underweight
- `updated_date`: Last update timestamp

### 6. **sector_allocations_current** (Sector Weights)
Current sector allocation targets.

**Key Columns:**
- `sector`: Sector name
- `weight_percentage`: Target allocation percentage
- `position_type`: LONG/SHORT bias
- `updated_date`: Last update timestamp

### 7. **stock_data** (Symbol Master)
Master list of tradeable symbols with metadata.

**Key Columns:**
- `symbol`: Stock symbol
- `industry`: Industry classification
- `sector`: Sector classification
- `fno_stock`: 'yes'/'no' - F&O availability
- `lot_size`: F&O lot size
- `market_cap`: Market capitalization

### 8. **option_chain_data** (Live Options Data)
Real-time options chain data for analysis.

**Key Columns:**
- `symbol`: Underlying symbol
- `option_type`: CE/PE
- `strike_price`: Strike price
- `expiry_date`: Expiry date
- `volume`: Trading volume
- `open_interest`: Open interest
- `bid`/`ask`: Market prices
- `index`: Boolean (true for NIFTY)

### 9. **api_scrip_master** (Dhan Security Mapping)
Maps symbols to Dhan security IDs for execution.

**Key Columns:**
- `sem_custom_symbol`: Formatted option symbol
- `sem_smst_security_id`: Dhan security ID
- `sem_strike_price`: Strike price
- `sem_option_type`: CE/PE
- `sem_expiry_date`: Expiry date
- `sem_lot_units`: Lot size

### 10. **trades** (Executed Trades)
Records of all executed trades.

**Key Columns:**
- `strategy_id`: Link to strategy
- `order_id`: Broker order ID
- `security_id`: Dhan security ID
- `quantity`: Executed quantity
- `price`: Execution price
- `order_status`: Current status
- `timestamp`: Execution time

## 🔄 Data Flow

### **1. Strategy Generation Flow**
```
main.py 
  ↓ (generates strategies)
strategies table
  ↓ (with details)
strategy_details, strategy_parameters, strategy_exit_levels
```

### **2. Portfolio Allocation Flow**
```
portfolio_allocator.py
  ↓ (reads)
industry_allocations_current + market conditions
  ↓ (updates)
strategies table (marks for execution)
  - marked_for_execution = TRUE
  - execution_status = 'marked'
  - execution_priority = calculated value
```

### **3. Execution Flow**
```
options_v4_executor.py
  ↓ (queries)
strategies WHERE marked_for_execution = TRUE 
            AND execution_status = 'marked'
  ↓ (maps via)
api_scrip_master (security IDs)
  ↓ (executes & stores)
trades table
  ↓ (updates)
strategies.execution_status = 'executed'
```

## 📝 SQL Queries

### **Get Strategies for Execution**
```sql
SELECT s.*, sd.*, sp.*
FROM strategies s
LEFT JOIN strategy_details sd ON s.id = sd.strategy_id
LEFT JOIN strategy_parameters sp ON s.id = sp.strategy_id
WHERE s.marked_for_execution = TRUE
  AND s.execution_status = 'marked'
  AND s.execution_priority > 0
ORDER BY s.execution_priority DESC;
```

### **Get Industry Allocations**
```sql
SELECT *
FROM industry_allocations_current
WHERE weight_percentage >= 5.0
ORDER BY weight_percentage DESC;
```

### **Map Symbol to Security ID**
```sql
SELECT sem_smst_security_id, sem_lot_units
FROM api_scrip_master
WHERE sem_custom_symbol = 'DIXON-Dec2024-14000-CE'
  AND sem_option_type = 'CE'
  AND sem_strike_price = 14000;
```

## 🎛️ Integration Points

### **1. Strategy Generation**
- `main.py` → `database/supabase_integration.py`
- Stores complete strategy analysis results
- Includes all Greeks, probabilities, exit conditions

### **2. Portfolio Allocation**
- `portfolio_allocator.py` → Direct Supabase queries
- Reads industry weights, updates execution marks
- Sets priority based on industry importance

### **3. Execution**
- `options_v4_executor.py` → Direct Supabase queries
- Maps strategies to Dhan security IDs
- Records all trades for audit trail

### **4. Monitoring**
- `execution_status.py` → Read-only queries
- Tracks execution status and P&L
- Provides performance analytics

## 🔧 Key Configuration

### **Environment Variables**
```bash
SUPABASE_URL=your_project_url
SUPABASE_ANON_KEY=your_anon_key
DHAN_CLIENT_ID=your_client_id
DHAN_ACCESS_TOKEN=your_access_token
```

### **Database Connection**
```python
from supabase import create_client
supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_ANON_KEY')
)
```

## 📈 Performance Considerations

### **Indexes Required**
- `strategies.marked_for_execution`
- `strategies.execution_status`
- `strategies.stock_name`
- `strategy_details.strategy_id`
- `api_scrip_master.sem_custom_symbol`

### **Query Optimization**
- Use compound indexes for execution queries
- Limit results with proper pagination
- Cache frequently accessed data (market conditions)

## 🔐 Security

### **Row Level Security (RLS)**
- Enable RLS on sensitive tables
- Use service role key only for admin operations
- Implement user-specific policies for multi-user setup

### **API Key Management**
- Store keys in environment variables
- Never commit keys to repository
- Rotate keys periodically

## 📚 Related Documentation

- `DATABASE_SETUP.md`: Initial setup instructions
- `EXECUTION_WORKFLOW_GUIDE.md`: Complete workflow guide
- `DHAN_EXECUTION_GUIDE.md`: Dhan API integration details
- `INDUSTRY_ALLOCATION_FRAMEWORK.md`: Allocation logic documentation