# Database Setup Guide for Options V4

## Overview
This guide explains how to set up the Supabase database integration for storing Options V4 analysis results.

## Prerequisites
1. A Supabase account and project
2. Python with pip installed
3. Options V4 system set up

## Setup Steps

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Database Schema
Run the SQL script on your Supabase database:
1. Go to your Supabase project dashboard
2. Navigate to SQL Editor
3. Copy and paste the contents of `database_schema_updates.sql`
4. Execute the script

### 3. Set Up Environment Variables
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your Supabase credentials
# - SUPABASE_URL: Your project URL
# - SUPABASE_ANON_KEY: Your anonymous/public key
```

### 4. Test Database Connection
```python
from database import SupabaseIntegration

# Test connection
db = SupabaseIntegration()
# Should see: "Supabase client initialized successfully"
```

## Usage

### Basic Usage (with database storage)
```bash
# Run with database storage enabled (default)
python main.py

# Analyze specific symbol
python main.py --symbol RELIANCE

# Set risk tolerance
python main.py --risk aggressive
```

### Without Database Storage
```bash
# Disable database storage
python main.py --no-database
```

## Database Schema Overview

### Core Tables (Existing)
1. **strategies** - Main strategy information
2. **strategy_details** - Individual option legs
3. **strategy_parameters** - Risk/reward parameters
4. **strategy_greek_exposures** - Net Greek exposures
5. **strategy_monitoring** - Technical levels to monitor
6. **strategy_risk_management** - Exit conditions and risk controls

### New Tables (Added)
1. **strategy_market_analysis** - Detailed market analysis
2. **strategy_iv_analysis** - IV analysis and recommendations
3. **strategy_price_levels** - Individual support/resistance levels
4. **strategy_expected_moves** - Expected move calculations
5. **strategy_exit_levels** - Granular exit conditions
6. **strategy_component_scores** - Strategy scoring breakdown

## Data Mapping

The integration maps Options V4 output to database tables as follows:

```
Options V4 Output → Database Tables
├── symbol → strategies.stock_name
├── top_strategies[] → strategies (one row per strategy)
│   ├── name → strategy_name
│   ├── probability_profit → probability_of_profit
│   ├── legs[] → strategy_details (one row per leg)
│   └── exit_conditions → strategy_risk_management
├── market_analysis → strategy_market_analysis
├── iv_analysis → strategy_iv_analysis
└── price_levels → strategy_price_levels + strategy_expected_moves
```

## Monitoring

### Check Stored Strategies
```sql
-- View recent strategies
SELECT 
    s.stock_name,
    s.strategy_name,
    s.conviction_level,
    s.probability_of_profit,
    s.generated_on
FROM strategies s
ORDER BY s.generated_on DESC
LIMIT 10;

-- High conviction strategies
SELECT * FROM v_high_conviction_strategies;
```

### Database Storage Status
The system will log database operations:
- "Stored X strategies in database" - Success
- "Database storage failed: ..." - Error message
- Check logs/options_v4_main_*.log for details

## Troubleshooting

### Connection Issues
1. Verify .env file exists and has correct values
2. Check Supabase project is active
3. Verify network connectivity

### Schema Issues
1. Ensure all SQL scripts have been run
2. Check for any error messages in SQL execution
3. Verify table permissions

### Data Issues
1. Check logs for specific error messages
2. Verify data types match schema
3. Look for NULL values in required fields

## Best Practices

1. **Regular Backups**: Export your data regularly
2. **Monitor Usage**: Check Supabase dashboard for usage metrics
3. **Clean Old Data**: Archive old strategies periodically
4. **Index Performance**: Monitor query performance

## Support

For issues:
1. Check logs in `logs/` directory
2. Review error messages in console output
3. Verify database schema is up to date
4. Check Supabase service status