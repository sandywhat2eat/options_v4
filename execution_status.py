#!/usr/bin/env python3
"""
Execution Status Monitor for Options V4
View and monitor strategy execution status
"""

import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv
from tabulate import tabulate
import argparse

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv('/Users/jaykrish/Documents/digitalocean/.env')

from database import SupabaseIntegration

class ExecutionMonitor:
    def __init__(self):
        """Initialize monitor with database connection"""
        self.db = SupabaseIntegration()
        if not self.db.client:
            print("❌ Failed to connect to database")
            sys.exit(1)
    
    def get_execution_summary(self):
        """Get summary of execution statuses"""
        try:
            # Get count by status
            result = self.db.client.rpc('get_execution_summary', {}).execute()
            
            # If RPC doesn't exist, do it manually
            statuses = ['pending', 'marked', 'executing', 'executed', 'failed']
            summary = {}
            
            for status in statuses:
                count_result = self.db.client.table('strategies').select(
                    'id', count='exact'
                ).eq('execution_status', status).execute()
                
                summary[status] = count_result.count
            
            return summary
            
        except:
            # Manual count
            statuses = ['pending', 'marked', 'executing', 'executed', 'failed']
            summary = {}
            
            for status in statuses:
                result = self.db.client.table('strategies').select(
                    'id'
                ).eq('execution_status', status).execute()
                
                summary[status] = len(result.data) if result.data else 0
            
            return summary
    
    def show_summary(self):
        """Display execution summary"""
        summary = self.get_execution_summary()
        
        print("\n📊 EXECUTION STATUS SUMMARY")
        print("=" * 40)
        
        total = sum(summary.values())
        
        for status, count in summary.items():
            percentage = (count / total * 100) if total > 0 else 0
            
            # Status emojis
            emoji = {
                'pending': '⏳',
                'marked': '🎯',
                'executing': '⚡',
                'executed': '✅',
                'failed': '❌'
            }.get(status, '❓')
            
            print(f"{emoji} {status.upper()}: {count} ({percentage:.1f}%)")
        
        print(f"\n📈 TOTAL: {total} strategies")
    
    def show_recent_executions(self, hours=24):
        """Show recently executed strategies"""
        try:
            since = (datetime.now() - timedelta(hours=hours)).isoformat()
            
            result = self.db.client.table('strategies').select(
                'id, stock_name, strategy_name, total_score, execution_status, '
                'executed_at, execution_priority'
            ).eq('execution_status', 'executed').gte(
                'executed_at', since
            ).order('executed_at', desc=True).execute()
            
            if not result.data:
                print(f"\n📭 No executions in the last {hours} hours")
                return
            
            print(f"\n✅ RECENT EXECUTIONS (Last {hours} hours)")
            print("=" * 80)
            
            table_data = []
            for s in result.data:
                executed_at = s['executed_at'][:16] if s['executed_at'] else 'N/A'
                score = s.get('total_score', 0) or 0
                
                table_data.append([
                    s['id'],
                    s['stock_name'],
                    s['strategy_name'][:30],
                    f"{score:.3f}",
                    s.get('execution_priority', ''),
                    executed_at
                ])
            
            headers = ['ID', 'Symbol', 'Strategy', 'Score', 'Priority', 'Executed At']
            print(tabulate(table_data, headers=headers, tablefmt='grid'))
            
        except Exception as e:
            print(f"❌ Error fetching recent executions: {e}")
    
    def show_failed_executions(self):
        """Show failed executions with error details"""
        try:
            result = self.db.client.table('strategies').select(
                'id, stock_name, strategy_name, execution_status, '
                'execution_notes, generated_on'
            ).eq('execution_status', 'failed').order('generated_on', desc=True).execute()
            
            if not result.data:
                print("\n✅ No failed executions")
                return
            
            print("\n❌ FAILED EXECUTIONS")
            print("=" * 80)
            
            for s in result.data:
                print(f"\nID: {s['id']} | {s['stock_name']} - {s['strategy_name']}")
                print(f"Generated: {s['generated_on'][:16]}")
                
                if s.get('execution_notes'):
                    print(f"Error Details:")
                    # Parse execution details from notes
                    notes = s['execution_notes']
                    if 'Execution Details:' in notes:
                        details = notes.split('Execution Details:')[1]
                        print(details[:500])  # Show first 500 chars
                    else:
                        print(notes[:200])
                
                print("-" * 40)
            
        except Exception as e:
            print(f"❌ Error fetching failed executions: {e}")
    
    def show_execution_queue(self):
        """Show current execution queue"""
        try:
            result = self.db.client.table('strategies').select(
                'id, stock_name, strategy_name, total_score, conviction_level, '
                'execution_priority, execution_notes'
            ).eq('marked_for_execution', True).order(
                'execution_priority', desc=True
            ).execute()
            
            if not result.data:
                print("\n📭 No strategies in execution queue")
                return
            
            print("\n🎯 EXECUTION QUEUE")
            print("=" * 80)
            
            table_data = []
            for s in result.data:
                score = s.get('total_score', 0) or 0
                notes = s.get('execution_notes', '')[:20] + '...' if s.get('execution_notes') and len(s.get('execution_notes')) > 20 else s.get('execution_notes', '')
                
                table_data.append([
                    s['id'],
                    s['stock_name'],
                    s['strategy_name'][:30],
                    f"{score:.3f}",
                    s['conviction_level'],
                    s['execution_priority'],
                    notes
                ])
            
            headers = ['ID', 'Symbol', 'Strategy', 'Score', 'Conviction', 'Priority', 'Notes']
            print(tabulate(table_data, headers=headers, tablefmt='grid'))
            print(f"\nTotal in queue: {len(result.data)}")
            
        except Exception as e:
            print(f"❌ Error fetching execution queue: {e}")
    
    def show_today_trades(self):
        """Show today's executed trades"""
        try:
            today = datetime.now().date().isoformat()
            
            result = self.db.client.table('trades').select(
                'id, symbol, strategy, action, type, strike_price, '
                'quantity, price, order_status, timestamp'
            ).gte('timestamp', today).order('timestamp', desc=True).execute()
            
            if not result.data:
                print("\n📭 No trades executed today")
                return
            
            print("\n📈 TODAY'S EXECUTED TRADES")
            print("=" * 100)
            
            table_data = []
            for t in result.data:
                time = t['timestamp'][11:16] if t['timestamp'] else 'N/A'
                
                table_data.append([
                    t['id'],
                    time,
                    t['symbol'],
                    t['strategy'][:20],
                    t['action'],
                    t['type'],
                    t.get('strike_price', ''),
                    t['quantity'],
                    t.get('price', 0),
                    t['order_status']
                ])
            
            headers = ['ID', 'Time', 'Symbol', 'Strategy', 'Action', 'Type', 
                      'Strike', 'Qty', 'Price', 'Status']
            print(tabulate(table_data, headers=headers, tablefmt='grid'))
            print(f"\nTotal trades today: {len(result.data)}")
            
        except Exception as e:
            print(f"❌ Error fetching today's trades: {e}")

def main():
    parser = argparse.ArgumentParser(description='Monitor Options V4 execution status')
    
    parser.add_argument('--summary', action='store_true', help='Show execution summary')
    parser.add_argument('--recent', type=int, metavar='HOURS', help='Show recent executions (last N hours)')
    parser.add_argument('--failed', action='store_true', help='Show failed executions')
    parser.add_argument('--queue', action='store_true', help='Show execution queue')
    parser.add_argument('--trades', action='store_true', help='Show today\'s trades')
    parser.add_argument('--all', action='store_true', help='Show all information')
    
    args = parser.parse_args()
    
    monitor = ExecutionMonitor()
    
    # If no args, show summary
    if not any(vars(args).values()):
        monitor.show_summary()
        monitor.show_execution_queue()
        return
    
    if args.summary or args.all:
        monitor.show_summary()
    
    if args.recent or args.all:
        hours = args.recent if args.recent else 24
        monitor.show_recent_executions(hours)
    
    if args.failed or args.all:
        monitor.show_failed_executions()
    
    if args.queue or args.all:
        monitor.show_execution_queue()
    
    if args.trades or args.all:
        monitor.show_today_trades()

if __name__ == "__main__":
    main()