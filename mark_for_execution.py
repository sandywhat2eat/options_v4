#!/usr/bin/env python3
"""
Strategy Execution Marker for Options V4
Allows traders to select and mark strategies for execution via Dhan API
"""

import os
import sys
import argparse
from datetime import datetime
from dotenv import load_dotenv
from tabulate import tabulate
import json

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv('/Users/jaykrish/Documents/digitalocean/.env')

from database import SupabaseIntegration

class ExecutionMarker:
    def __init__(self):
        """Initialize the execution marker with database connection"""
        self.db = SupabaseIntegration()
        if not self.db.client:
            print("❌ Failed to connect to database")
            sys.exit(1)
    
    def list_pending_strategies(self, symbol=None, strategy_type=None, min_score=None):
        """List all pending strategies available for execution"""
        try:
            # Build query
            query = self.db.client.table('strategies').select(
                'id, stock_name, strategy_name, total_score, conviction_level, '
                'probability_of_profit, spot_price, generated_on, execution_status, '
                'marked_for_execution, execution_priority'
            ).eq('execution_status', 'pending')
            
            # Apply filters
            if symbol:
                query = query.eq('stock_name', symbol.upper())
            if strategy_type:
                query = query.eq('strategy_type', strategy_type)
            if min_score:
                query = query.gte('total_score', min_score)
            
            # Order by score and priority
            query = query.order('execution_priority', desc=True).order('total_score', desc=True)
            
            result = query.execute()
            
            if not result.data:
                print("📭 No pending strategies found")
                return []
            
            return result.data
            
        except Exception as e:
            print(f"❌ Error fetching strategies: {e}")
            return []
    
    def display_strategies(self, strategies):
        """Display strategies in a formatted table"""
        if not strategies:
            return
        
        # Prepare data for tabulation
        table_data = []
        for s in strategies:
            marked = "✓" if s.get('marked_for_execution') else ""
            priority = s.get('execution_priority', 0)
            score = s.get('total_score', 0) or 0
            prob = s.get('probability_of_profit', 0) or 0
            
            table_data.append([
                s['id'],
                s['stock_name'],
                s['strategy_name'][:30],  # Truncate long names
                f"{score:.3f}",
                s['conviction_level'],
                f"{prob:.1%}",
                marked,
                priority if priority > 0 else "",
                s['generated_on'][:16]
            ])
        
        headers = ['ID', 'Symbol', 'Strategy', 'Score', 'Conviction', 
                   'Prob', 'Marked', 'Priority', 'Generated']
        
        print("\n📊 PENDING STRATEGIES FOR EXECUTION")
        print("=" * 100)
        print(tabulate(table_data, headers=headers, tablefmt='grid'))
        print(f"\nTotal: {len(strategies)} strategies")
    
    def mark_strategy(self, strategy_id, priority=1, notes=None):
        """Mark a strategy for execution"""
        try:
            # First check if strategy exists and is pending
            check = self.db.client.table('strategies').select(
                'id, stock_name, strategy_name, execution_status'
            ).eq('id', strategy_id).execute()
            
            if not check.data:
                print(f"❌ Strategy {strategy_id} not found")
                return False
            
            strategy = check.data[0]
            
            if strategy['execution_status'] != 'pending':
                print(f"❌ Strategy {strategy_id} is not pending (status: {strategy['execution_status']})")
                return False
            
            # Mark for execution
            update_data = {
                'marked_for_execution': True,
                'execution_priority': priority,
                'execution_status': 'marked'
            }
            
            if notes:
                update_data['execution_notes'] = notes
            
            result = self.db.client.table('strategies').update(
                update_data
            ).eq('id', strategy_id).execute()
            
            if result.data:
                print(f"✅ Marked strategy {strategy_id} ({strategy['stock_name']} - {strategy['strategy_name']}) for execution with priority {priority}")
                return True
            else:
                print(f"❌ Failed to mark strategy {strategy_id}")
                return False
                
        except Exception as e:
            print(f"❌ Error marking strategy: {e}")
            return False
    
    def unmark_strategy(self, strategy_id):
        """Unmark a strategy from execution queue"""
        try:
            result = self.db.client.table('strategies').update({
                'marked_for_execution': False,
                'execution_priority': 0,
                'execution_status': 'pending'
            }).eq('id', strategy_id).execute()
            
            if result.data:
                print(f"✅ Unmarked strategy {strategy_id}")
                return True
            else:
                print(f"❌ Failed to unmark strategy {strategy_id}")
                return False
                
        except Exception as e:
            print(f"❌ Error unmarking strategy: {e}")
            return False
    
    def list_marked_strategies(self):
        """List all strategies marked for execution"""
        try:
            result = self.db.client.table('strategies').select(
                'id, stock_name, strategy_name, total_score, conviction_level, '
                'execution_priority, execution_notes, marked_for_execution'
            ).eq('marked_for_execution', True).order('execution_priority', desc=True).execute()
            
            if not result.data:
                print("📭 No strategies marked for execution")
                return []
            
            print("\n🎯 STRATEGIES MARKED FOR EXECUTION")
            print("=" * 80)
            
            table_data = []
            for s in result.data:
                table_data.append([
                    s['id'],
                    s['stock_name'],
                    s['strategy_name'][:30],
                    f"{s.get('total_score', 0):.3f}",
                    s['conviction_level'],
                    s['execution_priority'],
                    s.get('execution_notes', '')[:30] if s.get('execution_notes') else ''
                ])
            
            headers = ['ID', 'Symbol', 'Strategy', 'Score', 'Conviction', 'Priority', 'Notes']
            print(tabulate(table_data, headers=headers, tablefmt='grid'))
            print(f"\nTotal: {len(result.data)} strategies marked")
            
            return result.data
            
        except Exception as e:
            print(f"❌ Error fetching marked strategies: {e}")
            return []
    
    def bulk_mark(self, strategy_ids, priority=1):
        """Mark multiple strategies at once"""
        success_count = 0
        for sid in strategy_ids:
            if self.mark_strategy(sid, priority):
                success_count += 1
        
        print(f"\n✅ Successfully marked {success_count}/{len(strategy_ids)} strategies")
    
    def mark_top_strategies(self, count=5, min_score=0.6):
        """Mark top N strategies by score"""
        strategies = self.list_pending_strategies(min_score=min_score)
        
        if not strategies:
            print("No strategies found matching criteria")
            return
        
        # Take top N
        top_strategies = strategies[:count]
        strategy_ids = [s['id'] for s in top_strategies]
        
        print(f"\n🎯 Marking top {len(top_strategies)} strategies:")
        for s in top_strategies:
            print(f"  - {s['stock_name']} {s['strategy_name']} (Score: {s.get('total_score', 0):.3f})")
        
        confirm = input("\nConfirm marking these strategies? (y/n): ")
        if confirm.lower() == 'y':
            self.bulk_mark(strategy_ids)

def main():
    parser = argparse.ArgumentParser(description='Mark Options V4 strategies for execution')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List pending strategies')
    list_parser.add_argument('--symbol', help='Filter by symbol')
    list_parser.add_argument('--min-score', type=float, help='Minimum score filter')
    list_parser.add_argument('--type', help='Filter by strategy type')
    
    # Mark command
    mark_parser = subparsers.add_parser('mark', help='Mark strategy for execution')
    mark_parser.add_argument('strategy_id', type=int, help='Strategy ID to mark')
    mark_parser.add_argument('--priority', type=int, default=1, help='Execution priority (default: 1)')
    mark_parser.add_argument('--notes', help='Execution notes')
    
    # Unmark command
    unmark_parser = subparsers.add_parser('unmark', help='Remove strategy from execution queue')
    unmark_parser.add_argument('strategy_id', type=int, help='Strategy ID to unmark')
    
    # Show marked
    show_parser = subparsers.add_parser('show', help='Show marked strategies')
    
    # Bulk mark
    bulk_parser = subparsers.add_parser('bulk', help='Mark multiple strategies')
    bulk_parser.add_argument('strategy_ids', nargs='+', type=int, help='Strategy IDs to mark')
    bulk_parser.add_argument('--priority', type=int, default=1, help='Execution priority')
    
    # Mark top
    top_parser = subparsers.add_parser('top', help='Mark top N strategies by score')
    top_parser.add_argument('--count', type=int, default=5, help='Number of strategies to mark')
    top_parser.add_argument('--min-score', type=float, default=0.6, help='Minimum score threshold')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    marker = ExecutionMarker()
    
    if args.command == 'list':
        strategies = marker.list_pending_strategies(
            symbol=args.symbol,
            strategy_type=args.type,
            min_score=args.min_score
        )
        marker.display_strategies(strategies)
    
    elif args.command == 'mark':
        marker.mark_strategy(args.strategy_id, args.priority, args.notes)
    
    elif args.command == 'unmark':
        marker.unmark_strategy(args.strategy_id)
    
    elif args.command == 'show':
        marker.list_marked_strategies()
    
    elif args.command == 'bulk':
        marker.bulk_mark(args.strategy_ids, args.priority)
    
    elif args.command == 'top':
        marker.mark_top_strategies(args.count, args.min_score)

if __name__ == "__main__":
    main()