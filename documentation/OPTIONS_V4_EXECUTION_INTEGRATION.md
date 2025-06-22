# 🚀 Options V4 + Dhan API Execution Integration

## 📋 Complete Integration Documentation

### Overview
This system integrates Options V4 trading strategy analysis with Dhan broker API execution, providing complete flexibility to select and execute specific strategies while maintaining full audit trails.

---

## 🗄️ Database Schema Changes

### New Fields Added to `strategies` Table

| Field Name | Type | Default | Purpose |
|------------|------|---------|---------|
| `execution_status` | VARCHAR(50) | 'pending' | Track execution lifecycle |
| `marked_for_execution` | BOOLEAN | false | **PRIMARY FLAG** - Mark strategy for execution |
| `execution_priority` | INTEGER | 0 | Execution order (higher = first) |
| `execution_notes` | TEXT | NULL | Execution comments and error details |
| `executed_at` | TIMESTAMP | NULL | When execution completed |

### 🎯 **Key Field for Execution Selection**
**`marked_for_execution`** - This is the PRIMARY field that determines if a strategy should be executed.
- `true` = Strategy is queued for execution
- `false` = Strategy will not be executed

### Execution Status Lifecycle
```
pending → marked → executing → executed
                            ↘ failed
```

---

## 📁 System Components

### 1. **Strategy Selection Interface**
- **File**: `mark_for_execution.py`
- **Purpose**: CLI tool to mark strategies for execution
- **Updates**: `marked_for_execution`, `execution_priority`, `execution_status`, `execution_notes`

### 2. **Dhan API Executor**
- **File**: `options_v4_executor.py`
- **Purpose**: Execute marked strategies via Dhan API
- **Reads**: Strategies where `marked_for_execution = true`
- **Updates**: `execution_status`, `executed_at`, `execution_notes`

### 3. **Security ID Mapping**
- **File**: `dhan_security_mapper.py`
- **Purpose**: Map option details to Dhan security IDs

### 4. **Monitoring Tools**
- **File**: `execution_status.py`
- **Purpose**: Monitor execution progress and results

---

## 🔧 How to Mark Strategies for Execution

### Method 1: Command Line Interface
```bash
# Mark single strategy
python mark_for_execution.py mark 123 --priority 5

# Mark multiple strategies
python mark_for_execution.py bulk 101 102 103 --priority 3

# Mark top strategies automatically
python mark_for_execution.py top --count 5 --min-score 0.6
```

### Method 2: Direct Database Update
```sql
-- Mark strategy ID 123 for execution with high priority
UPDATE strategies 
SET marked_for_execution = true,
    execution_status = 'marked',
    execution_priority = 5,
    execution_notes = 'High conviction trade'
WHERE id = 123;
```

### Method 3: Using Supabase Client
```python
from database import SupabaseIntegration

db = SupabaseIntegration()

# Mark strategy for execution
db.client.table('strategies').update({
    'marked_for_execution': True,
    'execution_status': 'marked',
    'execution_priority': 5
}).eq('id', 123).execute()
```

---

## 📊 Database Views for Execution

### v_execution_queue
Shows strategies ready for execution:
```sql
CREATE VIEW v_execution_queue AS
SELECT 
    id,
    stock_name,
    strategy_name,
    total_score,
    conviction_level,
    marked_for_execution,
    execution_priority,
    execution_status,
    execution_notes
FROM strategies 
WHERE marked_for_execution = true
ORDER BY execution_priority DESC, total_score DESC;
```

### Query Examples
```sql
-- View all strategies marked for execution
SELECT * FROM strategies 
WHERE marked_for_execution = true
ORDER BY execution_priority DESC;

-- View today's executed strategies
SELECT * FROM strategies 
WHERE execution_status = 'executed'
AND DATE(executed_at) = CURRENT_DATE;

-- View failed executions with error details
SELECT id, stock_name, strategy_name, execution_notes
FROM strategies 
WHERE execution_status = 'failed';
```

---

## 🎯 Execution Workflow

### Step 1: Generate Strategies
```bash
python main.py
```
- Creates strategies in database
- All start with `execution_status = 'pending'`
- All start with `marked_for_execution = false`

### Step 2: Review and Select
```bash
python mark_for_execution.py list --min-score 0.6
```
- Review available strategies
- Filter by score, symbol, etc.

### Step 3: Mark for Execution
```bash
python mark_for_execution.py mark 123 --priority 5 --notes "High conviction"
```
- Sets `marked_for_execution = true`
- Sets `execution_status = 'marked'`
- Sets `execution_priority = 5`

### Step 4: Execute via Dhan
```bash
python options_v4_executor.py
```
- Finds all strategies where `marked_for_execution = true`
- Orders by `execution_priority DESC`
- Places orders via Dhan API
- Updates `execution_status` to 'executed' or 'failed'
- Sets `executed_at` timestamp
- Stores trade details in `trades` table

### Step 5: Monitor Results
```bash
python execution_status.py --all
```

---

## 🗃️ Field Update Details

### When Marking for Execution
The system updates these fields in the `strategies` table:

```python
update_data = {
    'marked_for_execution': True,      # ← PRIMARY FLAG
    'execution_priority': priority,    # User-specified priority
    'execution_status': 'marked',      # Status change
    'execution_notes': notes           # Optional notes
}
```

### During Execution
```python
# Before execution starts
update_data = {
    'execution_status': 'executing'
}

# After successful execution
update_data = {
    'execution_status': 'executed',
    'executed_at': datetime.now().isoformat(),
    'execution_notes': 'Execution Details: {...}'
}

# After failed execution  
update_data = {
    'execution_status': 'failed',
    'execution_notes': 'Error: {...}'
}
```

---

## 📋 Command Reference

### mark_for_execution.py Commands

```bash
# List all pending strategies
python mark_for_execution.py list

# List with filters
python mark_for_execution.py list --symbol NIFTY --min-score 0.6

# Mark single strategy
python mark_for_execution.py mark <strategy_id> [--priority N] [--notes "text"]

# Mark multiple strategies
python mark_for_execution.py bulk <id1> <id2> <id3> [--priority N]

# Mark top strategies automatically
python mark_for_execution.py top [--count N] [--min-score X]

# View marked strategies
python mark_for_execution.py show

# Remove from execution queue
python mark_for_execution.py unmark <strategy_id>
```

### execution_status.py Commands

```bash
# Show summary
python execution_status.py --summary

# Show recent executions
python execution_status.py --recent 24

# Show failed executions
python execution_status.py --failed

# Show execution queue
python execution_status.py --queue

# Show today's trades
python execution_status.py --trades

# Show everything
python execution_status.py --all
```

---

## 🔍 Database Queries for Manual Management

### Mark Strategy for Execution
```sql
UPDATE strategies 
SET marked_for_execution = true,
    execution_status = 'marked',
    execution_priority = 5
WHERE id = 123;
```

### Unmark Strategy
```sql
UPDATE strategies 
SET marked_for_execution = false,
    execution_status = 'pending',
    execution_priority = 0
WHERE id = 123;
```

### View Execution Queue
```sql
SELECT id, stock_name, strategy_name, total_score, 
       execution_priority, execution_notes
FROM strategies 
WHERE marked_for_execution = true
ORDER BY execution_priority DESC, total_score DESC;
```

### View Execution History
```sql
SELECT id, stock_name, strategy_name, execution_status, 
       executed_at, execution_notes
FROM strategies 
WHERE execution_status IN ('executed', 'failed')
ORDER BY executed_at DESC;
```

---

## 🚨 Important Notes

### Primary Execution Control
**The `marked_for_execution` field is the PRIMARY control for strategy execution.**

- Only strategies with `marked_for_execution = true` will be executed
- The executor ignores all other strategies regardless of score or conviction
- This gives you complete control over what gets executed

### Execution Priority
- Higher numbers execute first
- Use 1-10 scale (10 = highest priority)
- Strategies with same priority are ordered by total_score

### Safety Features
- Dry-run capability in executor
- Complete audit trail in execution_notes
- Failed executions preserved for review
- Market hours validation

---

## 📈 Integration Benefits

1. **Selective Execution**: Choose exactly which strategies to execute
2. **Priority Management**: Control execution order
3. **Complete Tracking**: Full audit trail from analysis to execution  
4. **Risk Management**: Review before execution, no automatic trading
5. **Error Handling**: Failed executions preserved with error details
6. **Flexible Interface**: CLI tools, database queries, or programmatic control

---

## 🛠️ Quick Setup Checklist

- ✅ Database columns added to strategies table
- ✅ mark_for_execution.py installed
- ✅ options_v4_executor.py configured with Dhan credentials
- ✅ Security ID mapping working
- ✅ Monitoring tools available

**Ready for production use!**

---

## 📞 Support

For issues or questions:
1. Check execution logs: `options_v4_execution.log`
2. Use monitoring tools: `python execution_status.py --all`
3. Review database: Check `execution_status` and `execution_notes` fields
4. Test flow: `python test_execution_flow.py`