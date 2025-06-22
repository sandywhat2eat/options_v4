# 🚀 Options V4 + Dhan API Execution Integration

## 📋 Overview

This integration enables seamless execution of Options V4 trading strategies through Dhan broker API. The system provides flexibility to select which strategies to execute, with complete tracking and audit trail.

---

## 🏗️ Architecture

```
Options V4 Analysis → Supabase DB → Strategy Selection → Dhan API Execution
                          ↓                    ↓                  ↓
                     strategies table    mark_for_execution   trades table
```

### Key Components:
1. **mark_for_execution.py** - Strategy selection interface
2. **options_v4_executor.py** - Dhan API execution bridge
3. **dhan_security_mapper.py** - Security ID mapping utility
4. **Database Views** - v_execution_queue for monitoring

---

## 🔧 Setup Instructions

### 1. Database Setup (Already Completed)
The following columns have been added to the strategies table:
- `execution_status` - pending/marked/executed/failed
- `marked_for_execution` - boolean flag
- `execution_priority` - integer (higher = higher priority)
- `execution_notes` - text for notes
- `executed_at` - timestamp

### 2. Environment Setup
Ensure your `.env` file has:
```bash
# Supabase credentials (existing)
NEXT_PUBLIC_SUPABASE_URL=your_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_key

# Or
SUPABASE_URL=your_url
SUPABASE_KEY=your_key
```

### 3. Install Dependencies
```bash
source /Users/jaykrish/agents/project_output/venv/bin/activate
pip install dhanhq tabulate
```

---

## 📖 Usage Guide

### 1. 📊 View Pending Strategies

List all strategies awaiting execution:
```bash
python mark_for_execution.py list
```

Filter options:
```bash
# Filter by symbol
python mark_for_execution.py list --symbol NIFTY

# Filter by minimum score
python mark_for_execution.py list --min-score 0.6

# Combine filters
python mark_for_execution.py list --symbol BANKNIFTY --min-score 0.5
```

### 2. ✅ Mark Strategies for Execution

Mark a single strategy:
```bash
# Basic marking
python mark_for_execution.py mark 123

# With priority (higher number = higher priority)
python mark_for_execution.py mark 123 --priority 5

# With notes
python mark_for_execution.py mark 123 --priority 3 --notes "High conviction trade"
```

Mark multiple strategies:
```bash
# Mark multiple at once
python mark_for_execution.py bulk 123 124 125 --priority 2
```

Mark top strategies automatically:
```bash
# Mark top 5 strategies with score > 0.6
python mark_for_execution.py top --count 5 --min-score 0.6
```

### 3. 👁️ View Marked Strategies

See all strategies queued for execution:
```bash
python mark_for_execution.py show
```

### 4. ❌ Unmark Strategies

Remove from execution queue:
```bash
python mark_for_execution.py unmark 123
```

### 5. 🎯 Execute Marked Strategies

Execute all marked strategies via Dhan API:
```bash
python options_v4_executor.py
```

The executor will:
- Fetch all marked strategies ordered by priority
- Map option details to Dhan security IDs
- Place orders for each leg
- Update execution status
- Store trades in the database

---

## 📊 Execution Workflow

### Step-by-Step Process:

1. **Generate Strategies**
   ```bash
   python main.py
   ```
   Options V4 analyzes and stores strategies in Supabase

2. **Review Strategies**
   ```bash
   python mark_for_execution.py list
   ```
   View pending strategies with scores and details

3. **Select for Execution**
   ```bash
   # Mark high-score strategies
   python mark_for_execution.py mark 101 --priority 5
   python mark_for_execution.py mark 102 --priority 3
   
   # Or mark top performers
   python mark_for_execution.py top --count 3 --min-score 0.7
   ```

4. **Verify Selection**
   ```bash
   python mark_for_execution.py show
   ```

5. **Execute via Dhan**
   ```bash
   python options_v4_executor.py
   ```

6. **Monitor in Database**
   - Check `execution_status` in strategies table
   - View executed trades in trades table
   - Review execution logs

---

## 🔍 Database Views

### v_execution_queue
Shows strategies marked for execution:
```sql
SELECT * FROM v_execution_queue
ORDER BY execution_priority DESC, total_score DESC;
```

### v_trade_execution
Complete trade details with execution status:
```sql
SELECT * FROM v_trade_execution
WHERE execution_status IN ('marked', 'executed')
ORDER BY executed_at DESC;
```

---

## 🛡️ Security ID Mapping

### Option 1: Import from MySQL (if available)
```bash
python import_scrip_master.py
```

### Option 2: Use Dhan API directly
```bash
python dhan_security_mapper.py
```

Test mapping:
```python
# In dhan_security_mapper.py
mapper.test_mapping('NIFTY', 24000, 'CE')
```

---

## 📝 Execution Status Flow

```
pending → marked → executing → executed
                            ↘ failed
```

- **pending**: Strategy generated, awaiting selection
- **marked**: Selected for execution
- **executing**: Currently being processed
- **executed**: Successfully placed with broker
- **failed**: Execution failed (check logs)

---

## 🚨 Error Handling

### Common Issues:

1. **Security ID Not Found**
   - Ensure symbol matches exactly (e.g., "NIFTY" not "NIFTY50")
   - Check if expiry date is valid
   - Verify option exists with given strike

2. **Market Closed**
   - Orders will be marked as "deferred"
   - Re-run executor during market hours

3. **Insufficient Margin**
   - Check account balance
   - Reduce position size or lots

4. **Authentication Failed**
   - Update Dhan access token in options_v4_executor.py
   - Token expires periodically

---

## 📊 Monitoring & Logs

### Execution Logs
```bash
tail -f options_v4_execution.log
```

### Database Queries
```sql
-- Recent executions
SELECT * FROM strategies 
WHERE execution_status = 'executed'
ORDER BY executed_at DESC LIMIT 10;

-- Failed executions
SELECT * FROM strategies 
WHERE execution_status = 'failed'
AND execution_notes IS NOT NULL;

-- Today's trades
SELECT * FROM trades 
WHERE DATE(timestamp) = CURRENT_DATE
ORDER BY timestamp DESC;
```

---

## 🔄 Daily Workflow Example

### Morning Routine:
```bash
# 1. Generate fresh analysis
python main.py

# 2. Review high-score opportunities
python mark_for_execution.py list --min-score 0.6

# 3. Mark best strategies
python mark_for_execution.py top --count 5 --min-score 0.65

# 4. Execute during market hours
python options_v4_executor.py
```

### Position Monitoring:
```sql
-- In Supabase SQL Editor
SELECT * FROM v_trade_execution 
WHERE DATE(executed_at) = CURRENT_DATE
ORDER BY execution_priority DESC;
```

---

## 🎯 Best Practices

1. **Strategy Selection**
   - Focus on high conviction (HIGH/VERY_HIGH) strategies
   - Prioritize strategies with score > 0.6
   - Consider risk/reward ratio > 1.5

2. **Execution Priority**
   - Use priority 5+ for urgent trades
   - Priority 3-4 for normal trades
   - Priority 1-2 for low urgency

3. **Risk Management**
   - Set daily execution limits
   - Monitor total exposure
   - Review failed executions

4. **Timing**
   - Execute after 9:30 AM for better liquidity
   - Avoid last 30 minutes for volatile moves
   - Check for economic events

---

## 🔧 Customization

### Modify Execution Logic
Edit `options_v4_executor.py`:
- Change order types (MARKET/LIMIT)
- Add slippage protection
- Implement partial fills

### Add Custom Filters
Edit `mark_for_execution.py`:
- Add strategy type filters
- Include Greeks-based selection
- Custom scoring logic

---

## 📞 Support

### Logs Location:
- `options_v4_execution.log` - Execution details
- `logs/options_v4_main_*.log` - Analysis logs

### Database Tables:
- `strategies` - All generated strategies
- `strategy_details` - Individual legs
- `trades` - Executed trades
- `security_mappings` - Security ID cache

### Key Files:
- `mark_for_execution.py` - Strategy selection
- `options_v4_executor.py` - Dhan execution
- `dhan_security_mapper.py` - Security mapping
- `database/supabase_integration.py` - DB interface

---

## 🚀 Quick Start Commands

```bash
# Daily execution flow
python main.py                          # Generate strategies
python mark_for_execution.py list       # Review opportunities
python mark_for_execution.py top        # Mark best strategies
python mark_for_execution.py show       # Verify selection
python options_v4_executor.py           # Execute via Dhan
```

---

**Note**: Always verify strategies before execution. The system provides tools for selection but trading decisions remain your responsibility.