# Options V4 Documentation - Quick Reference

## 📋 Document Purpose Guide

### For Daily Trading
- **[USER_GUIDE.md](./USER_GUIDE.md)** - Complete trading workflow and best practices
- **[EXECUTION_WORKFLOW_GUIDE.md](./EXECUTION_WORKFLOW_GUIDE.md)** - Step-by-step execution procedures

### For Technical Understanding  
- **[TECHNICAL_REFERENCE.md](./TECHNICAL_REFERENCE.md)** - System architecture and implementation
- **[DATABASE_INTEGRATION_SUMMARY.md](./DATABASE_INTEGRATION_SUMMARY.md)** - Database schema and queries

### For System Maintenance
- **[CLAUDE.md](./CLAUDE.md)** - Quick commands and troubleshooting
- **[STRIKE_SELECTION_IMPROVEMENTS.md](./STRIKE_SELECTION_IMPROVEMENTS.md)** - Recent improvements

### For Specialized Topics
- **[INDUSTRY_ALLOCATION_FRAMEWORK.md](./INDUSTRY_ALLOCATION_FRAMEWORK.md)** - Allocation methodology
- **[DHAN_EXECUTION_GUIDE.md](./DHAN_EXECUTION_GUIDE.md)** - Dhan API specifics

## 🚀 Quick Start Commands

```bash
# Generate strategies
python main.py --risk moderate

# Select for execution  
python mark_for_execution.py --interactive

# Execute trades
python options_v4_executor.py --execute

# Monitor performance
python execution_status.py
```

## 🔧 Common Tasks

| Task | Command | Documentation |
|------|---------|---------------|
| Run analysis | `python main.py` | USER_GUIDE.md |
| Debug errors | Check logs/ | CLAUDE.md |
| Database queries | See SQL examples | DATABASE_INTEGRATION_SUMMARY.md |
| Add new strategy | Modify strategies/ | TECHNICAL_REFERENCE.md |

## ⚡ Most Used References

1. **Exit Conditions** → USER_GUIDE.md#exit-management
2. **Risk Limits** → USER_GUIDE.md#risk-management  
3. **Strike Selection** → STRIKE_SELECTION_IMPROVEMENTS.md
4. **Error Fixes** → CLAUDE.md#common-issues-solutions
