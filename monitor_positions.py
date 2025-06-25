#!/usr/bin/env python3
"""
Real-time Position Monitor for Options V4
Monitors open positions and evaluates exit conditions
"""

import os
import sys
import time
import logging
import argparse
from datetime import datetime
from typing import List, Dict
from tabulate import tabulate
from colorama import init, Fore, Back, Style

# Initialize colorama for cross-platform colored output
init()

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.position_monitor import PositionMonitor
from core.exit_evaluator import ExitEvaluator
from database.supabase_integration import SupabaseIntegration

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/position_monitor.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class OptionsMonitorDashboard:
    """
    Interactive dashboard for monitoring options positions
    """
    
    def __init__(self):
        """Initialize dashboard components"""
        try:
            self.position_monitor = PositionMonitor(logger)
            self.exit_evaluator = ExitEvaluator(logger)
            self.db = SupabaseIntegration(logger)
            logger.info("Monitor dashboard initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize dashboard: {e}")
            raise
    
    def get_colored_pnl(self, pnl: float, pnl_pct: float) -> str:
        """Return colored P&L string"""
        if pnl > 0:
            return f"{Fore.GREEN}₹{pnl:,.2f} ({pnl_pct:.2f}%){Style.RESET_ALL}"
        elif pnl < 0:
            return f"{Fore.RED}₹{pnl:,.2f} ({pnl_pct:.2f}%){Style.RESET_ALL}"
        else:
            return f"₹{pnl:,.2f} ({pnl_pct:.2f}%)"
    
    def get_colored_action(self, action: str, urgency: str) -> str:
        """Return colored action string based on urgency"""
        if urgency == 'HIGH':
            return f"{Back.RED}{Fore.WHITE} {action} {Style.RESET_ALL}"
        elif urgency == 'MEDIUM':
            return f"{Back.YELLOW}{Fore.BLACK} {action} {Style.RESET_ALL}"
        else:
            return action
    
    def display_dashboard(self, detailed: bool = False):
        """Display the complete monitoring dashboard"""
        try:
            # Clear screen
            os.system('cls' if os.name == 'nt' else 'clear')
            
            # Header
            print(f"\n{Fore.CYAN}{'=' * 120}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}OPTIONS V4 - REAL-TIME POSITION MONITOR{Style.RESET_ALL}")
            print(f"{Fore.CYAN}Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}{'=' * 120}{Style.RESET_ALL}\n")
            
            # Fetch positions
            positions = self.position_monitor.get_open_positions()
            
            if not positions:
                print(f"{Fore.YELLOW}📭 No open positions found{Style.RESET_ALL}")
                return
            
            # Get current prices
            current_prices = self.position_monitor.get_current_prices(positions)
            
            # Calculate P&L and evaluate exits for each position
            position_data = []
            evaluations = []
            total_pnl = 0
            
            for position in positions:
                # Calculate P&L
                pnl_data = self.position_monitor.calculate_position_pnl(position, current_prices)
                
                # Get exit conditions
                exit_conditions = self.position_monitor.get_exit_conditions(position['strategy_id'])
                
                # Evaluate exit conditions
                evaluation = self.exit_evaluator.evaluate_position(pnl_data, exit_conditions)
                
                position_data.append(pnl_data)
                evaluations.append(evaluation)
                total_pnl += pnl_data.get('total_pnl', 0)
            
            # Display positions table
            self._display_positions_table(position_data, evaluations)
            
            # Display summary
            self._display_summary(position_data, total_pnl)
            
            # Display exit recommendations
            self._display_exit_recommendations(evaluations)
            
            # Display alerts
            self._display_alerts(evaluations)
            
            # Display detailed leg information if requested
            if detailed:
                self._display_detailed_legs(position_data, current_prices)
            
        except Exception as e:
            logger.error(f"Error displaying dashboard: {e}")
            print(f"{Fore.RED}❌ Error: {e}{Style.RESET_ALL}")
    
    def _display_positions_table(self, position_data: List[Dict], evaluations: List[Dict]):
        """Display positions in a formatted table"""
        print(f"\n{Fore.YELLOW}📊 OPEN POSITIONS{Style.RESET_ALL}")
        print("-" * 120)
        
        table_data = []
        for pos, eval in zip(position_data, evaluations):
            # Skip positions with errors
            if pos.get('status') == 'ERROR':
                continue
            
            row = [
                pos.get('strategy_id', 'N/A'),
                pos.get('symbol', 'N/A'),
                pos.get('strategy_name', 'N/A')[:25],
                pos.get('days_in_trade', 0),
                f"₹{pos.get('entry_value', 0):,.2f}",
                self.get_colored_pnl(pos.get('total_pnl', 0), pos.get('total_pnl_pct', 0)),
                self.get_colored_action(eval.get('recommended_action', 'MONITOR'), 
                                      eval.get('urgency', 'NORMAL')),
                eval.get('action_reason', '')[:30]
            ]
            table_data.append(row)
        
        headers = ['ID', 'Symbol', 'Strategy', 'Days', 'Entry Value', 'Current P&L', 'Action', 'Reason']
        print(tabulate(table_data, headers=headers, tablefmt='grid'))
    
    def _display_summary(self, position_data: List[Dict], total_pnl: float):
        """Display portfolio summary"""
        print(f"\n{Fore.YELLOW}📈 PORTFOLIO SUMMARY{Style.RESET_ALL}")
        print("-" * 60)
        
        total_positions = len(position_data)
        profitable = sum(1 for p in position_data if p.get('total_pnl', 0) > 0)
        losing = sum(1 for p in position_data if p.get('total_pnl', 0) < 0)
        
        print(f"Total Positions: {total_positions}")
        print(f"Profitable: {Fore.GREEN}{profitable} ({profitable/total_positions*100:.1f}%){Style.RESET_ALL}")
        print(f"Losing: {Fore.RED}{losing} ({losing/total_positions*100:.1f}%){Style.RESET_ALL}")
        print(f"Total P&L: {self.get_colored_pnl(total_pnl, 0)}")
    
    def _display_exit_recommendations(self, evaluations: List[Dict]):
        """Display exit recommendations"""
        action_summary = self.exit_evaluator.get_action_summary(evaluations)
        
        print(f"\n{Fore.YELLOW}🎯 EXIT RECOMMENDATIONS{Style.RESET_ALL}")
        print("-" * 60)
        
        print(f"Immediate Actions Required: {Fore.RED}{action_summary['immediate_actions']}{Style.RESET_ALL}")
        print(f"Adjustments Needed: {Fore.YELLOW}{action_summary['adjustments_needed']}{Style.RESET_ALL}")
        print(f"Monitoring Only: {Fore.GREEN}{action_summary['monitoring']}{Style.RESET_ALL}")
        
        # Display actions by type
        if action_summary['actions_by_type']:
            print("\nActions by Type:")
            for action, count in action_summary['actions_by_type'].items():
                print(f"  • {action}: {count}")
    
    def _display_alerts(self, evaluations: List[Dict]):
        """Display high priority alerts"""
        high_urgency = [e for e in evaluations if e.get('urgency') == 'HIGH']
        medium_urgency = [e for e in evaluations if e.get('urgency') == 'MEDIUM']
        
        if high_urgency or medium_urgency:
            print(f"\n{Fore.YELLOW}⚠️  ALERTS{Style.RESET_ALL}")
            print("-" * 60)
            
            if high_urgency:
                print(f"\n{Back.RED}{Fore.WHITE} HIGH PRIORITY {Style.RESET_ALL}")
                for alert in high_urgency:
                    print(f"  🚨 {alert['symbol']} - {alert['strategy_name']}: {alert['recommended_action']}")
                    for detail in alert.get('details', []):
                        print(f"     → {detail}")
            
            if medium_urgency:
                print(f"\n{Back.YELLOW}{Fore.BLACK} MEDIUM PRIORITY {Style.RESET_ALL}")
                for alert in medium_urgency:
                    print(f"  ⚡ {alert['symbol']} - {alert['strategy_name']}: {alert['recommended_action']}")
                    for detail in alert.get('details', []):
                        print(f"     → {detail}")
    
    def _display_detailed_legs(self, position_data: List[Dict], current_prices: Dict[int, float]):
        """Display detailed information for each leg"""
        print(f"\n{Fore.YELLOW}📊 DETAILED LEG INFORMATION{Style.RESET_ALL}")
        print("-" * 120)
        
        for pos in position_data:
            if pos.get('status') == 'ERROR':
                continue
                
            print(f"\n{Fore.CYAN}{pos['symbol']} - {pos['strategy_name']} (Strategy ID: {pos['strategy_id']}){Style.RESET_ALL}")
            
            for leg in pos.get('legs', []):
                action_emoji = "🔴" if leg['action'] == 'SELL' else "🟢"
                pnl_color = Fore.GREEN if leg['pnl'] >= 0 else Fore.RED
                
                print(f"   {action_emoji} {leg['action']} {leg.get('strike', 'N/A')} {leg.get('type', '')}:")
                print(f"      Entry: ₹{leg['entry_price']:.2f} | Current: ₹{leg['current_price']:.2f}")
                print(f"      Qty: {leg['quantity']} | P&L: {pnl_color}₹{leg['pnl']:.2f} ({leg['pnl_pct']:.2f}%){Style.RESET_ALL}")
                print(f"      Security ID: {leg.get('security_id', 'N/A')}")
    
    def run_continuous_monitor(self, interval: int = 300, detailed: bool = False):
        """Run dashboard in continuous loop"""
        print(f"\n{Fore.GREEN}Starting continuous monitoring (interval: {interval} seconds){Style.RESET_ALL}")
        print("Press Ctrl+C to stop\n")
        
        try:
            while True:
                self.display_dashboard(detailed=detailed)
                
                # Show countdown
                print(f"\n{Fore.CYAN}⏰ Next update in {interval} seconds...{Style.RESET_ALL}")
                
                # Sleep with countdown display
                for remaining in range(interval, 0, -10):
                    print(f"\r{Fore.CYAN}⏰ Next update in {remaining} seconds...{Style.RESET_ALL}", end='')
                    time.sleep(min(10, remaining))
                
        except KeyboardInterrupt:
            print(f"\n\n{Fore.YELLOW}👋 Monitoring stopped by user{Style.RESET_ALL}")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Real-time options position monitor with exit evaluation')
    parser.add_argument('--continuous', '-c', action='store_true', 
                       help='Run in continuous monitoring mode')
    parser.add_argument('--interval', '-i', type=int, default=300,
                       help='Update interval in seconds (default: 300)')
    parser.add_argument('--detailed', '-d', action='store_true',
                       help='Show detailed leg information')
    parser.add_argument('--export', '-e', type=str,
                       help='Export results to file (csv/json)')
    
    args = parser.parse_args()
    
    try:
        dashboard = OptionsMonitorDashboard()
        
        if args.continuous:
            dashboard.run_continuous_monitor(args.interval, detailed=args.detailed)
        else:
            dashboard.display_dashboard(detailed=args.detailed)
            
            # Export if requested
            if args.export:
                print(f"\n{Fore.YELLOW}📁 Exporting to {args.export}...{Style.RESET_ALL}")
                # TODO: Implement export functionality
        
    except Exception as e:
        print(f"{Fore.RED}❌ Error: {e}{Style.RESET_ALL}")
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()