# Options V4 Trading System - Quick Start Reference

## 🚀 Complete Workflow (3 Simple Steps)

### **Step 1: Generate Strategies** 📊
```bash
python main.py --risk moderate
```
**What happens:** Analyzes 50 symbols, generates strategies, stores in database

### **Step 2: Select Strategies** 🎯
```bash
python mark_for_execution.py --interactive
```
**What happens:** Review strategies, mark preferred ones for execution

### **Step 3: Execute & Monitor** ⚡
```bash
python options_v4_executor.py --execute --confirm
python execution_status.py
```
**What happens:** Execute marked strategies via Dhan API, monitor performance

---

## 📋 Key Scripts Reference

| Script | Purpose | Usage |
|--------|---------|-------|
| `main.py` | Generate strategies | `python main.py --risk moderate` |
| `mark_for_execution.py` | Select strategies | `python mark_for_execution.py --interactive` |
| `options_v4_executor.py` | Execute orders | `python options_v4_executor.py --execute` |
| `execution_status.py` | Monitor trades | `python execution_status.py` |

---

## 🎛️ Quick Configuration

### **Risk Tolerance Options:**
- `--risk conservative`: 45% min probability, lower position sizes
- `--risk moderate`: 25% min probability, balanced approach  
- `--risk aggressive`: 15% min probability, higher position sizes

### **Common Flags:**
- `--symbol DIXON`: Analyze specific symbol
- `--preview`: Dry run (no actual execution)
- `--confirm`: Require confirmation before execution
- `--interactive`: Interactive mode for strategy selection

---

## 📊 Expected Results

### **Analysis Output (Step 1):**
- **Success Rate**: ~68% (34/50 symbols)
- **Strategies Generated**: ~43 strategies across 6 industries
- **Processing Time**: ~18 minutes for 50 symbols
- **Database Storage**: All strategies stored in 12+ tables

### **Selection Output (Step 2):**
- **Review Interface**: Table format with scores and probabilities
- **Selection Options**: Mark by ID, symbol, or score threshold
- **Filtering**: By probability, return, strategy type

### **Execution Output (Step 3):**
- **Order Placement**: Direct Dhan API integration
- **Execution Speed**: ~4.2 seconds average per strategy
- **Monitoring**: Real-time P&L and status tracking

---

## 🗂️ File Locations

### **Results:**
- `results/options_v4_analysis_*.json`: Analysis results
- `results/options_portfolio_allocation_*.json`: Portfolio allocation

### **Logs:**
- `logs/options_v4_main_*.log`: Analysis logs
- `options_v4_execution.log`: Execution logs

### **Database:**
- `strategies`: Main strategy records
- `strategy_execution_status`: Execution tracking
- `industry_allocations_current`: Industry weights

---

## 🔧 Environment Setup

```bash
# .env file requirements
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_key
DHAN_CLIENT_ID=your_dhan_client_id
DHAN_ACCESS_TOKEN=your_dhan_access_token
```

---

## 🎯 Daily Trading Routine

### **Morning (9:00 AM):**
```bash
python main.py --risk moderate
```

### **Pre-Market (9:10 AM):**
```bash
python mark_for_execution.py --interactive
```

### **Market Open (9:15 AM):**
```bash
python options_v4_executor.py --execute --confirm
```

### **Throughout Day:**
```bash
python execution_status.py
```

---

## 📈 Performance Metrics

- **Capital Allocation**: ₹3 crores total exposure
- **Industry Coverage**: 6 major industries
- **Strategy Types**: 22+ different strategies
- **Success Rate**: 68% strategy generation
- **Execution Speed**: <5 seconds per strategy

---

## 🆘 Quick Troubleshooting

### **No strategies generated:**
```bash
python main.py --risk aggressive  # Lower probability threshold
```

### **Database connection issues:**
```bash
python check_stored_data.py  # Validate database connection
```

### **Execution failures:**
```bash
python options_v4_executor.py --test-connection  # Test Dhan API
```

---

**📚 For detailed documentation, see `/documentation/EXECUTION_WORKFLOW_GUIDE.md`**