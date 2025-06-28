# IV Historical Builder

This module builds and maintains historical implied volatility (IV) data for options trading strategies.

## ✅ System Status (June 28, 2025)

**Fully Operational**: All 212 symbols have been backfilled with 7 days of historical IV data (June 20-28, 2025)

## Overview

The system consists of two main components:

1. **IV Collector** (`iv_collector.py`) - Collects daily IV data from option_chain_data table with pagination support
2. **IV Analyzer** (`iv_analyzer.py`) - Calculates IV percentiles and rankings from historical data

## Database Tables

### historical_iv_summary
Stores daily IV statistics for each symbol:
- ATM IV
- Mean/Median IV
- Call/Put IV means
- IV skew
- Volume and OI totals

### iv_percentiles
Stores current IV percentiles and rankings:
- Multiple lookback periods (5, 10, 20, 30 days)
- IV rank and percentile
- Historical high/low
- Percentile breakpoints

## Setup

1. Create the database tables using `database_schema.sql`:
```sql
-- Run the SQL commands in database_schema.sql in your Supabase SQL editor
```

2. Ensure environment variables are set:
```bash
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

## Usage

### ⚠️ Initial Backfill (Already Complete)
~~To backfill historical data for the last 30 days:~~
```bash
# ✅ COMPLETED - All data backfilled on June 28, 2025
# python iv_collector.py --backfill 30
```

### 📅 Daily Operations (Run This Daily)

**IMPORTANT**: Run these commands in order after your daily option_chain_data is loaded:

#### 1. Collect Today's IV Data
```bash
cd /Users/jaykrish/Documents/digitalocean/cronjobs/options_v4
python3 iv_historical_builder/iv_collector.py --latest
```

#### 2. Update All Percentiles
```bash
cd /Users/jaykrish/Documents/digitalocean/cronjobs/options_v4
python3 iv_historical_builder/iv_analyzer.py
```

#### 3. Run Main Options System
```bash
cd /Users/jaykrish/Documents/digitalocean/cronjobs/options_v4
python3 main.py
```

### 🔍 Check IV Environment for Specific Symbol
```bash
python3 iv_historical_builder/iv_analyzer.py SUNPHARMA
```

## Integration with Main System

The main options system can query the `iv_percentiles` table to get:
- Current IV percentile (0-100)
- IV rank (0-100)
- IV environment (LOW/SUBDUED/NORMAL/ELEVATED/HIGH)

Example SQL query:
```sql
SELECT * FROM get_iv_stats('SUNPHARMA', 30);
```

Or use the view:
```sql
SELECT * FROM current_iv_environment WHERE symbol = 'SUNPHARMA';
```

## 🔄 Daily Workflow (Your New Routine)

### Step-by-Step Daily Process

After your daily EOD option_chain_data is loaded into Supabase:

1. **Collect Latest IV Data** (1-2 minutes)
   ```bash
   cd /Users/jaykrish/Documents/digitalocean/cronjobs/options_v4
   python3 iv_historical_builder/iv_collector.py --latest
   ```
   - Processes all 200+ symbols for today's date
   - Uses pagination to handle large datasets
   - Stores IV summaries in historical_iv_summary table

2. **Update Percentiles** (2-3 minutes)
   ```bash
   python3 iv_historical_builder/iv_analyzer.py
   ```
   - Calculates percentiles for all symbols across 5, 10, 20, 30-day lookbacks
   - Updates iv_percentiles table with current rankings
   - Determines IV environments (LOW/NORMAL/HIGH)

3. **Run Options Analysis** (5-10 minutes)
   ```bash
   python3 main.py
   ```
   - Uses updated IV percentiles for accurate strategy selection
   - No more default 50% fallbacks
   - Better volatility-based strategy recommendations

### 🎯 Current Benefits (Post-Backfill)
- ✅ **Real IV Percentiles**: Actual historical data instead of estimates
- ✅ **212 Symbols**: All symbols have 7+ days of historical data  
- ✅ **Accurate Environments**: Proper LOW/HIGH/NORMAL classifications
- ✅ **Strategy Optimization**: Better strategy selection based on real IV data
- ✅ **Growing Dataset**: Improves daily as more historical data accumulates

## 📊 Data Quality & Features

### Data Processing
- ✅ **Pagination Support**: Handles 20,000+ records per date (fixed June 28, 2025)
- ✅ **Clean Data**: Filters out NULL IV values and invalid data
- ✅ **ATM Focus**: Uses closest-to-spot strikes for most representative IV
- ✅ **IV Skew**: Calculates call vs put IV differences
- ✅ **Quality Tracking**: Monitors data points per symbol/date

### Historical Data Status
- **Start Date**: June 20, 2025
- **Current Coverage**: 7+ days for all 212 symbols
- **Daily Growth**: +1 day of history per day going forward
- **Lookback Periods**: 5, 10, 20, 30 days (expanding as data grows)

## 🚨 Troubleshooting

### If IV Collector Fails
```bash
# Check if option_chain_data has today's data
python3 -c "
from supabase import create_client
from dotenv import load_dotenv
import os
from datetime import datetime

load_dotenv('/Users/jaykrish/Documents/digitalocean/.env')
supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_ANON_KEY'))

today = datetime.now().strftime('%Y-%m-%d')
result = supabase.table('option_chain_data').select('symbol').gte('created_at', f'{today}T00:00:00').limit(5).execute()
print(f'Today data available: {len(result.data)} records found')
"
```

### If Percentiles Are Wrong
```bash
# Re-run analyzer to recalculate all percentiles
python3 iv_historical_builder/iv_analyzer.py
```

### Emergency: Re-backfill Recent Data
```bash
# Only if needed - re-backfill last 7 days
python3 iv_historical_builder/iv_collector.py --backfill 7
python3 iv_historical_builder/iv_analyzer.py
```