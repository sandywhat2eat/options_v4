# Strategy Data Deletion Guide

This guide provides multiple methods to delete **ALL** strategy data from your Supabase database.

## ⚠️ CRITICAL WARNING

**These scripts will permanently delete ALL strategy data from your database. This action cannot be undone.**

The deletion includes:
- All strategies (main table)
- All strategy details (option legs)
- All strategy parameters
- All strategy Greek exposures
- All strategy monitoring data
- All strategy risk management data
- All strategy market analysis
- All strategy IV analysis
- All strategy price levels
- All strategy expected moves
- All strategy exit levels
- All strategy component scores

## Available Deletion Methods

### Method 1: Python Script with Supabase Client (Recommended)

**File:** `delete_all_strategies_data.py`

This is the most comprehensive and safe method. It:
- Requires confirmation before proceeding
- Shows progress during deletion
- Handles large datasets efficiently
- Deletes in correct order to avoid foreign key issues

**Requirements:**
```bash
pip install supabase python-dotenv
```

**Setup:**
1. Ensure your `.env` file contains:
   ```
   SUPABASE_URL=your_supabase_url
   SUPABASE_ANON_KEY=your_supabase_key
   ```

**Usage:**
```bash
python delete_all_strategies_data.py
```

**What it does:**
- Prompts for confirmation (type "DELETE ALL" then "YES")
- Deletes all related tables in correct order
- Shows progress for each table
- Reports total deleted records

### Method 2: SQL Commands Generator

**File:** `delete_strategies_mcp.py`

This script generates SQL commands that you can execute manually.

**Usage:**
```bash
python delete_strategies_mcp.py
```

**What it does:**
- Prompts for confirmation
- Generates SQL DELETE commands in correct order
- You copy/paste commands into Supabase SQL editor

### Method 3: Direct SQL Reference

**File:** `execute_deletion_via_mcp.py`

This shows the raw SQL commands you need to execute.

**Usage:**
```bash
python execute_deletion_via_mcp.py
```

## Manual SQL Execution (Direct via Supabase)

If you prefer to execute SQL commands directly in Supabase SQL editor, use these commands **in this exact order**:

```sql
-- Step 1: Delete child table data first
DELETE FROM strategy_component_scores;
DELETE FROM strategy_exit_levels;
DELETE FROM strategy_expected_moves;
DELETE FROM strategy_price_levels;
DELETE FROM strategy_iv_analysis;
DELETE FROM strategy_market_analysis;
DELETE FROM strategy_risk_management;
DELETE FROM strategy_monitoring;
DELETE FROM strategy_greek_exposures;
DELETE FROM strategy_parameters;
DELETE FROM strategy_details;

-- Step 2: Delete parent table last
DELETE FROM strategies;
```

## Using MCP Tools (via Cursor/Claude)

If you're using MCP tools, you can convert SQL to REST API calls:

```python
# Example using MCP tools
mcp_supabase_sqlToRest("DELETE FROM strategy_component_scores")
```

Then execute the REST API calls using `mcp_supabase_postgrestRequest`.

## Verification

After deletion, verify all tables are empty:

```sql
-- Check record counts
SELECT 'strategies' as table_name, COUNT(*) as record_count FROM strategies
UNION ALL
SELECT 'strategy_details', COUNT(*) FROM strategy_details
UNION ALL
SELECT 'strategy_parameters', COUNT(*) FROM strategy_parameters
UNION ALL
SELECT 'strategy_greek_exposures', COUNT(*) FROM strategy_greek_exposures
UNION ALL
SELECT 'strategy_monitoring', COUNT(*) FROM strategy_monitoring
UNION ALL
SELECT 'strategy_risk_management', COUNT(*) FROM strategy_risk_management
UNION ALL
SELECT 'strategy_market_analysis', COUNT(*) FROM strategy_market_analysis
UNION ALL
SELECT 'strategy_iv_analysis', COUNT(*) FROM strategy_iv_analysis
UNION ALL
SELECT 'strategy_price_levels', COUNT(*) FROM strategy_price_levels
UNION ALL
SELECT 'strategy_expected_moves', COUNT(*) FROM strategy_expected_moves
UNION ALL
SELECT 'strategy_exit_levels', COUNT(*) FROM strategy_exit_levels
UNION ALL
SELECT 'strategy_component_scores', COUNT(*) FROM strategy_component_scores;
```

All counts should be 0 after successful deletion.

## Important Notes

1. **Deletion Order Matters**: Child tables must be deleted before parent tables to avoid foreign key constraint errors.

2. **No Undo**: Once deleted, data cannot be recovered unless you have backups.

3. **Large Datasets**: The Python script handles large datasets by processing in batches.

4. **Database Connections**: Ensure you have proper database access before running any script.

5. **Backup First**: Consider exporting your data before deletion if you might need it later.

## Troubleshooting

### Foreign Key Constraint Errors
If you get foreign key errors, ensure you're deleting in the correct order (child tables first).

### Connection Errors
- Verify your Supabase credentials in `.env` file
- Check if your Supabase project is active
- Ensure you have network connectivity

### Permission Errors
- Verify your Supabase key has DELETE permissions
- Check if Row Level Security (RLS) is affecting operations

## Recovery

If you accidentally delete data and need to recover:
1. Check if you have database backups in Supabase
2. Restore from backup if available
3. Re-run your Options V4 analysis to regenerate data

## Files Overview

| File | Purpose | Method |
|------|---------|---------|
| `delete_all_strategies_data.py` | Interactive Python deletion | Supabase Python client |
| `delete_strategies_mcp.py` | SQL command generator | Generates SQL commands |
| `execute_deletion_via_mcp.py` | SQL reference | Shows raw SQL commands |
| `DELETION_GUIDE.md` | This guide | Documentation |

Choose the method that best fits your workflow and comfort level. 