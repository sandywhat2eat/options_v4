# Options V4 Trading System Documentation

## 📚 Documentation Structure

### Core Documentation
1. **[USER_GUIDE.md](./USER_GUIDE.md)** - Complete user guide for traders and operators
2. **[TECHNICAL_REFERENCE.md](./TECHNICAL_REFERENCE.md)** - System architecture and technical details
3. **[DATABASE_REFERENCE.md](./DATABASE_REFERENCE.md)** - Database schema and integration guide
4. **[EXECUTION_WORKFLOW.md](./EXECUTION_WORKFLOW_GUIDE.md)** - Step-by-step execution procedures

### Specialized Guides
- **[INDUSTRY_ALLOCATION_FRAMEWORK.md](./INDUSTRY_ALLOCATION_FRAMEWORK.md)** - Industry allocation methodology
- **[STRIKE_SELECTION_IMPROVEMENTS.md](./STRIKE_SELECTION_IMPROVEMENTS.md)** - Strike selection system documentation
- **[DHAN_EXECUTION_GUIDE.md](./DHAN_EXECUTION_GUIDE.md)** - Dhan API integration specifics
- **[PORTFOLIO_ALLOCATOR_LOGIC.md](./PORTFOLIO_ALLOCATOR_LOGIC.md)** - Sophisticated portfolio allocation methodology

### Quick Links
- [Getting Started](#getting-started)
- [System Overview](#system-overview)
- [Common Tasks](#common-tasks)
- [Troubleshooting](#troubleshooting)

---

## Getting Started

### Prerequisites
- Python 3.8+
- Dhan Trading Account with API access
- Supabase database access
- Required environment variables (see USER_GUIDE.md)

### Quick Setup
```bash
# 1. Clone repository and install dependencies
pip install -r requirements.txt

# 2. Configure environment variables
cp .env.example .env
# Edit .env with your credentials

# 3. Run first analysis
python main.py --symbol RELIANCE --risk moderate
```

## System Overview

The Options V4 Trading System is a comprehensive options strategy analyzer with:
- **22+ Options Strategies** covering all market conditions
- **50-Symbol Portfolio Analysis** capability
- **Sophisticated Portfolio Allocator** with VIX-based strategy selection and quantum scoring
- **Industry-First Allocation Framework** using database-driven weights
- **Kelly Criterion Position Sizing** with intelligent fallback hierarchy
- **Complete Database Integration** for strategy storage and tracking
- **Direct Execution** via Dhan API
- **Real-time Monitoring** and performance tracking

## Common Tasks

### 1. Run Portfolio Analysis
```bash
python main.py --risk moderate
```

### 2. Run Sophisticated Portfolio Allocation
```bash
python deploy_sophisticated_allocator.py
```

### 3. Execute Selected Strategies
```bash
python options_v4_executor.py --execute --confirm
```

### 4. Monitor Performance
```bash
python execution_status.py --performance-dashboard
```

## Troubleshooting

For common issues and solutions, see:
- [EXECUTION_WORKFLOW_GUIDE.md#troubleshooting](./EXECUTION_WORKFLOW_GUIDE.md#troubleshooting)
- [USER_GUIDE.md#common-issues](./USER_GUIDE.md#common-issues)

## Support

For additional help:
- Check the detailed guides in this documentation folder
- Review log files in `logs/` directory
- Ensure all database tables are properly configured