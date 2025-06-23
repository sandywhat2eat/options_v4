#!/usr/bin/env python3
"""
Direct execution script to delete ALL data from strategies table and related tables via MCP.
This will permanently delete all strategy data from the database.

This script shows the SQL commands that need to be executed.
"""

def main():
    """Show the SQL commands that need to be executed to delete all strategy data."""
    
    print("🗄️  Strategy Data Deletion via MCP")
    print("===================================")
    print()
    print("⚠️  WARNING: The following SQL commands will permanently delete ALL strategy data!")
    print()
    print("Execute these SQL commands in your Supabase SQL editor or via MCP tools:")
    print("(Execute them in this exact order to avoid foreign key constraint violations)")
    print()
    
    # SQL commands in correct order (child tables first)
    sql_commands = [
        ("strategy_component_scores", "DELETE FROM strategy_component_scores;"),
        ("strategy_exit_levels", "DELETE FROM strategy_exit_levels;"),
        ("strategy_expected_moves", "DELETE FROM strategy_expected_moves;"),
        ("strategy_price_levels", "DELETE FROM strategy_price_levels;"),
        ("strategy_iv_analysis", "DELETE FROM strategy_iv_analysis;"),
        ("strategy_market_analysis", "DELETE FROM strategy_market_analysis;"),
        ("strategy_risk_management", "DELETE FROM strategy_risk_management;"),
        ("strategy_monitoring", "DELETE FROM strategy_monitoring;"),
        ("strategy_greek_exposures", "DELETE FROM strategy_greek_exposures;"),
        ("strategy_parameters", "DELETE FROM strategy_parameters;"),
        ("strategy_details", "DELETE FROM strategy_details;"),
        ("strategies", "DELETE FROM strategies;")  # Parent table last
    ]
    
    for i, (table_name, sql_command) in enumerate(sql_commands, 1):
        print(f"Step {i}: Clear {table_name}")
        print(f"SQL: {sql_command}")
        print()
    
    print("=" * 60)
    print("🔥 After executing all commands, your strategies database will be completely empty.")
    print("⚠️  This action cannot be undone!")
    print()
    print("💡 Alternative: Run the Python scripts for interactive deletion:")
    print("   - delete_all_strategies_data.py (uses Supabase Python client)")
    print("   - delete_strategies_mcp.py (generates SQL commands)")

if __name__ == "__main__":
    main() 