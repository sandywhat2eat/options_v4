#!/usr/bin/env python3
"""
Reorganize documentation files to remove duplicates and create cleaner structure
"""

import os
import shutil
from datetime import datetime

def reorganize_docs():
    """Reorganize documentation files"""
    
    docs_dir = "../documentation"
    archive_dir = f"../documentation/archive_{datetime.now().strftime('%Y%m%d')}"
    
    # Create archive directory
    os.makedirs(archive_dir, exist_ok=True)
    
    # Files to archive (duplicates/old versions)
    files_to_archive = [
        "SYSTEM_OVERVIEW_V4.md",  # Content merged into TECHNICAL_REFERENCE.md
        "TRADING_INTEGRATION_SUMMARY.md",  # Content merged into USER_GUIDE.md
        "TRADERS_GUIDE.md",  # Content merged into USER_GUIDE.md
        "OPTIONS_V4_EXECUTION_INTEGRATION.md",  # Duplicate of execution workflow
        "DATABASE_SETUP.md",  # Old setup guide, superseded
        "SUPABASE_DATA_VALIDATION_REPORT.md"  # Old validation report
    ]
    
    # Core files to keep
    core_files = [
        "README.md",
        "USER_GUIDE.md", 
        "TECHNICAL_REFERENCE.md",
        "CLAUDE.md",
        "DATABASE_INTEGRATION_SUMMARY.md",
        "EXECUTION_WORKFLOW_GUIDE.md",
        "INDUSTRY_ALLOCATION_FRAMEWORK.md",
        "DHAN_EXECUTION_GUIDE.md",
        "STRIKE_SELECTION_IMPROVEMENTS.md"
    ]
    
    print("=== Documentation Reorganization ===")
    print(f"\nArchiving to: {archive_dir}")
    
    # Archive old files
    archived_count = 0
    for filename in files_to_archive:
        src = os.path.join(docs_dir, filename)
        if os.path.exists(src):
            dst = os.path.join(archive_dir, filename)
            shutil.move(src, dst)
            print(f"✓ Archived: {filename}")
            archived_count += 1
        else:
            print(f"✗ Not found: {filename}")
    
    print(f"\nArchived {archived_count} files")
    
    # List remaining files
    print("\n=== Active Documentation ===")
    for filename in sorted(os.listdir(docs_dir)):
        if filename.endswith('.md') and not filename.startswith('.'):
            filepath = os.path.join(docs_dir, filename)
            size = os.path.getsize(filepath) / 1024  # KB
            print(f"✓ {filename:<40} ({size:>6.1f} KB)")
    
    # Create quick reference file
    create_quick_reference(docs_dir)
    
    print("\n✅ Documentation reorganization complete!")
    print(f"   Old files archived to: {archive_dir}")
    print("   New structure is cleaner with no duplicates")

def create_quick_reference(docs_dir):
    """Create a quick reference guide"""
    
    quick_ref_content = """# Options V4 Documentation - Quick Reference

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
"""
    
    with open(os.path.join(docs_dir, "QUICK_REFERENCE.md"), 'w') as f:
        f.write(quick_ref_content)
    
    print("\n✓ Created QUICK_REFERENCE.md")

if __name__ == "__main__":
    reorganize_docs()