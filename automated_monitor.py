#!/usr/bin/env python3
"""
Automated Position Monitor for Options V4
Continuously monitors positions and executes exits when conditions are triggered
"""

import os
import sys
import time
import logging
import argparse
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from tabulate import tabulate
from colorama import init, Fore, Back, Style

# Initialize colorama for cross-platform colored output
init()

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.position_monitor import PositionMonitor
from core.exit_evaluator import ExitEvaluator
from core.exit_executor import ExitExecutor
from database.supabase_integration import SupabaseIntegration

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/automated_monitor.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class AutomatedMonitor:
    """
    Automated monitoring service for options positions
    
    Features:
    - Continuous monitoring at set intervals
    - Automatic exit execution
    - Alert generation
    - Audit logging
    """
    
    def __init__(self, execute_exits: bool = False, alert_only: bool = False):
        """
        Initialize automated monitor
        
        Args:
            execute_exits: Whether to actually execute exits (vs simulation)
            alert_only: Only generate alerts, don't execute
        """
        try:
            self.position_monitor = PositionMonitor(logger)
            self.exit_evaluator = ExitEvaluator(logger)
            self.exit_executor = ExitExecutor(logger)
            self.db = SupabaseIntegration(logger)
            
            self.execute_exits = execute_exits
            self.alert_only = alert_only
            
            # Track executed exits to avoid duplicates
            self.executed_exits = set()
            
            logger.info(f"Automated Monitor initialized (execute_exits={execute_exits}, alert_only={alert_only})")
            
        except Exception as e:
            logger.error(f"Failed to initialize automated monitor: {e}")
            raise
    
    def run_monitoring_cycle(self) -> Dict:
        """Run a single monitoring cycle"""
        try:
            cycle_start = datetime.now()
            logger.info(f"Starting monitoring cycle at {cycle_start}")
            
            results = {
                'timestamp': cycle_start.isoformat(),
                'positions_monitored': 0,
                'alerts_generated': 0,
                'exits_executed': 0,
                'errors': [],
                'details': []
            }
            
            # Fetch open positions
            positions = self.position_monitor.get_open_positions()
            results['positions_monitored'] = len(positions)
            
            if not positions:
                logger.info("No open positions to monitor")
                return results
            
            # Get current prices
            current_prices = self.position_monitor.get_current_prices(positions)
            
            # Process each position
            for position in positions:
                try:
                    # Skip if already executed in this session
                    position_key = f"{position['strategy_id']}_{position['symbol']}"
                    if position_key in self.executed_exits:
                        continue
                    
                    # Calculate P&L
                    pnl_data = self.position_monitor.calculate_position_pnl(position, current_prices)
                    
                    # Get exit conditions
                    exit_conditions = self.position_monitor.get_exit_conditions(position['strategy_id'])
                    
                    # Evaluate exit conditions
                    evaluation = self.exit_evaluator.evaluate_position(pnl_data, exit_conditions)
                    
                    # Log position status
                    position_info = {
                        'symbol': position['symbol'],
                        'strategy': position['strategy_name'],
                        'pnl': pnl_data.get('total_pnl', 0),
                        'pnl_pct': pnl_data.get('total_pnl_pct', 0),
                        'action': evaluation.get('recommended_action'),
                        'urgency': evaluation.get('urgency'),
                        'reason': evaluation.get('action_reason'),
                        'days_in_trade': pnl_data.get('days_in_trade', 0),
                        'entry_value': pnl_data.get('entry_value', 0),
                        'current_value': pnl_data.get('current_value', 0)
                    }
                    
                    results['details'].append(position_info)
                    
                    # Process based on urgency and action
                    if evaluation.get('urgency') in ['HIGH', 'MEDIUM'] and \
                       evaluation.get('recommended_action') != 'MONITOR':
                        
                        results['alerts_generated'] += 1
                        
                        # Generate alert
                        self._generate_alert(position, pnl_data, evaluation)
                        
                        # Execute exit if enabled
                        if not self.alert_only and evaluation.get('recommended_action') in [
                            'CLOSE_IMMEDIATELY', 'CLOSE_POSITION'
                        ]:
                            if self.execute_exits:
                                # Execute actual exit
                                exit_result = self.exit_executor.execute_exit(position, evaluation)
                            else:
                                # Simulate exit
                                exit_result = self.exit_executor.simulate_exit(position, evaluation)
                            
                            if exit_result['success']:
                                results['exits_executed'] += 1
                                self.executed_exits.add(position_key)
                                
                                # Log exit execution
                                self._log_exit_execution(position, evaluation, exit_result)
                            else:
                                results['errors'].append({
                                    'position': position_key,
                                    'error': exit_result.get('message', 'Unknown error')
                                })
                    
                except Exception as e:
                    logger.error(f"Error processing position {position.get('symbol')}: {e}")
                    results['errors'].append({
                        'position': position.get('symbol'),
                        'error': str(e)
                    })
            
            # Log cycle summary
            cycle_duration = (datetime.now() - cycle_start).total_seconds()
            logger.info(
                f"Monitoring cycle completed in {cycle_duration:.2f}s - "
                f"Positions: {results['positions_monitored']}, "
                f"Alerts: {results['alerts_generated']}, "
                f"Exits: {results['exits_executed']}"
            )
            
            # Save results to database
            self._save_monitoring_results(results)
            
            return results
            
        except Exception as e:
            logger.error(f"Error in monitoring cycle: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'positions_monitored': 0
            }
    
    def _generate_alert(self, position: Dict, pnl_data: Dict, evaluation: Dict):
        """Generate alert for position requiring attention"""
        try:
            alert_data = {
                'alert_type': evaluation.get('urgency'),
                'strategy_id': position.get('strategy_id'),
                'symbol': position.get('symbol'),
                'strategy_name': position.get('strategy_name'),
                'current_pnl': pnl_data.get('total_pnl'),
                'current_pnl_pct': pnl_data.get('total_pnl_pct'),
                'recommended_action': evaluation.get('recommended_action'),
                'action_reason': evaluation.get('action_reason'),
                'details': json.dumps(evaluation.get('details', [])),
                'created_at': datetime.now().isoformat()
            }
            
            # Save to alerts table (if it exists)
            try:
                self.db.client.table('position_alerts').insert(alert_data).execute()
            except:
                # Table might not exist, log to file instead
                pass
            
            # Log alert
            logger.warning(
                f"ALERT [{alert_data['alert_type']}] {alert_data['symbol']} - "
                f"{alert_data['strategy_name']}: {alert_data['recommended_action']} "
                f"(P&L: {alert_data['current_pnl']:.2f})"
            )
            
            # TODO: Send email/SMS notification
            
        except Exception as e:
            logger.error(f"Error generating alert: {e}")
    
    def _log_exit_execution(self, position: Dict, evaluation: Dict, exit_result: Dict):
        """Log exit execution details"""
        try:
            execution_log = {
                'timestamp': datetime.now().isoformat(),
                'strategy_id': position.get('strategy_id'),
                'symbol': position.get('symbol'),
                'strategy_name': position.get('strategy_name'),
                'action': evaluation.get('recommended_action'),
                'reason': evaluation.get('action_reason'),
                'result': exit_result,
                'mode': 'LIVE' if self.execute_exits else 'SIMULATION'
            }
            
            # Log to file
            with open('logs/exit_executions.json', 'a') as f:
                f.write(json.dumps(execution_log) + '\n')
            
            logger.info(f"Exit executed: {execution_log}")
            
        except Exception as e:
            logger.error(f"Error logging exit execution: {e}")
    
    def _save_monitoring_results(self, results: Dict):
        """Save monitoring results to database"""
        try:
            # Create monitoring log entry
            log_entry = {
                'timestamp': results['timestamp'],
                'positions_monitored': results['positions_monitored'],
                'alerts_generated': results['alerts_generated'],
                'exits_executed': results['exits_executed'],
                'errors': json.dumps(results.get('errors', [])),
                'summary': json.dumps(results.get('details', []))
            }
            
            # Try to save to database
            try:
                self.db.client.table('monitoring_logs').insert(log_entry).execute()
            except:
                # Table might not exist
                pass
            
        except Exception as e:
            logger.error(f"Error saving monitoring results: {e}")
    
    def get_colored_pnl(self, pnl: float, pnl_pct: float) -> str:
        """Return colored P&L string"""
        if pnl > 0:
            return f"{Fore.GREEN}₹{pnl:,.2f} ({pnl_pct:.2f}%){Style.RESET_ALL}"
        elif pnl < 0:
            return f"{Fore.RED}₹{pnl:,.2f} ({pnl_pct:.2f}%){Style.RESET_ALL}"
        else:
            return f"₹{pnl:,.2f} ({pnl_pct:.2f}%)"
    
    def get_colored_status(self, position_data: Dict, exit_conditions: Dict) -> str:
        """Get colored status indicator based on proximity to exit levels"""
        pnl_pct = position_data.get('total_pnl_pct', 0)
        
        # Check profit targets
        profit_targets = exit_conditions.get('profit_targets', {})
        if 'primary' in profit_targets:
            target_pct = profit_targets['primary'].get('trigger_value', 50)
            if pnl_pct >= target_pct * 0.8:  # Within 80% of target
                return f"{Fore.YELLOW}📈 Near Target{Style.RESET_ALL}"
        
        # Check stop losses
        stop_losses = exit_conditions.get('stop_losses', {})
        if 'primary' in stop_losses:
            stop_pct = stop_losses['primary'].get('trigger_value', 50)
            if pnl_pct <= -(stop_pct * 0.8):  # Within 80% of stop
                return f"{Fore.RED}⚠️  Near Stop{Style.RESET_ALL}"
        
        # Check time exits
        days_in_trade = position_data.get('days_in_trade', 0)
        time_exits = exit_conditions.get('time_exits', {})
        if 'primary' in time_exits:
            dte_threshold = time_exits['primary'].get('trigger_value', 7)
            estimated_dte = max(30 - days_in_trade, 0)
            if estimated_dte <= dte_threshold:
                return f"{Fore.YELLOW}⏰ Time Exit{Style.RESET_ALL}"
        
        return f"{Fore.GREEN}✓ Normal{Style.RESET_ALL}"
    
    def display_position_table(self, results: Dict):
        """Display detailed position table with P&L and status"""
        if not results.get('details'):
            return
        
        # Clear screen and display header
        os.system('cls' if os.name == 'nt' else 'clear')
        
        print(f"\n{Fore.CYAN}{'=' * 140}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}AUTOMATED POSITION MONITOR - LIVE STATUS{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Mode: {'LIVE EXECUTION' if self.execute_exits else 'SIMULATION'}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'=' * 140}{Style.RESET_ALL}\n")
        
        # Group positions by strategy for better organization
        positions_by_strategy = {}
        for detail in results['details']:
            strategy = detail.get('strategy', 'Unknown')
            if strategy not in positions_by_strategy:
                positions_by_strategy[strategy] = []
            positions_by_strategy[strategy].append(detail)
        
        # Create table data
        all_table_data = []
        strategy_summaries = []
        
        for strategy_name, positions in positions_by_strategy.items():
            strategy_pnl = sum(p.get('pnl', 0) for p in positions)
            strategy_summaries.append({
                'strategy': strategy_name,
                'positions': len(positions),
                'total_pnl': strategy_pnl
            })
            
            for pos in positions:
                # Get exit conditions for status
                try:
                    # Fetch exit conditions for this position
                    strategy_id = self._get_strategy_id_for_position(pos['symbol'], strategy_name)
                    exit_conditions = {}
                    if strategy_id:
                        exit_cond_result = self.db.client.table('strategy_exit_levels').select(
                            '*'
                        ).eq('strategy_id', strategy_id).execute()
                        
                        if exit_cond_result.data:
                            exit_conditions = self._parse_exit_conditions(exit_cond_result.data)
                    
                    # Mock position data for status calculation
                    position_data = {
                        'total_pnl_pct': pos.get('pnl_pct', 0),
                        'days_in_trade': 2  # Placeholder - you'd get this from actual data
                    }
                    
                    status = self.get_colored_status(position_data, exit_conditions)
                except:
                    status = f"{Fore.GRAY}Unknown{Style.RESET_ALL}"
                
                all_table_data.append([
                    strategy_name,
                    pos.get('symbol', 'N/A'),
                    self.get_colored_pnl(pos.get('pnl', 0), pos.get('pnl_pct', 0)),
                    status,
                    pos.get('action', 'MONITOR'),
                    pos.get('urgency', 'NORMAL'),
                    pos.get('reason', '')[:40]  # Truncate reason
                ])
        
        # Display position table
        if all_table_data:
            print(f"{Fore.YELLOW}📊 POSITION DETAILS{Style.RESET_ALL}")
            print("-" * 140)
            
            headers = ['Strategy', 'Symbol', 'Current P&L', 'Status', 'Action', 'Urgency', 'Reason']
            print(tabulate(all_table_data, headers=headers, tablefmt='grid'))
        
        # Display strategy summary
        if strategy_summaries:
            print(f"\n{Fore.YELLOW}📈 STRATEGY SUMMARY{Style.RESET_ALL}")
            print("-" * 80)
            
            summary_data = []
            total_positions = 0
            total_pnl = 0
            
            for summary in strategy_summaries:
                total_positions += summary['positions']
                total_pnl += summary['total_pnl']
                
                summary_data.append([
                    summary['strategy'],
                    summary['positions'],
                    self.get_colored_pnl(summary['total_pnl'], 0)
                ])
            
            # Add total row
            summary_data.append([
                f"{Fore.CYAN}TOTAL{Style.RESET_ALL}",
                total_positions,
                self.get_colored_pnl(total_pnl, 0)
            ])
            
            headers = ['Strategy', 'Positions', 'Total P&L']
            print(tabulate(summary_data, headers=headers, tablefmt='grid'))
        
        # Display alerts if any
        high_alerts = [d for d in results['details'] if d.get('urgency') == 'HIGH']
        medium_alerts = [d for d in results['details'] if d.get('urgency') == 'MEDIUM']
        
        if high_alerts or medium_alerts:
            print(f"\n{Fore.YELLOW}⚠️  ALERTS{Style.RESET_ALL}")
            print("-" * 80)
            
            if high_alerts:
                print(f"\n{Back.RED}{Fore.WHITE} HIGH PRIORITY {Style.RESET_ALL}")
                for alert in high_alerts:
                    print(f"  🚨 {alert['symbol']} - {alert['strategy']}: {alert['action']}")
                    print(f"     Reason: {alert['reason']}")
            
            if medium_alerts:
                print(f"\n{Back.YELLOW}{Fore.BLACK} MEDIUM PRIORITY {Style.RESET_ALL}")
                for alert in medium_alerts:
                    print(f"  ⚡ {alert['symbol']} - {alert['strategy']}: {alert['action']}")
                    print(f"     Reason: {alert['reason']}")
        
        # Display summary statistics
        print(f"\n{Fore.YELLOW}📊 CYCLE SUMMARY{Style.RESET_ALL}")
        print("-" * 60)
        print(f"Total Positions: {results.get('positions_monitored', 0)}")
        print(f"Alerts Generated: {results.get('alerts_generated', 0)}")
        print(f"Exits Executed: {results.get('exits_executed', 0)}")
        
        profitable = sum(1 for d in results['details'] if d.get('pnl', 0) > 0)
        losing = sum(1 for d in results['details'] if d.get('pnl', 0) < 0)
        
        if results.get('positions_monitored', 0) > 0:
            print(f"Profitable: {Fore.GREEN}{profitable} ({profitable/results['positions_monitored']*100:.1f}%){Style.RESET_ALL}")
            print(f"Losing: {Fore.RED}{losing} ({losing/results['positions_monitored']*100:.1f}%){Style.RESET_ALL}")
    
    def _get_strategy_id_for_position(self, symbol: str, strategy_name: str) -> Optional[int]:
        """Helper to get strategy ID for a position"""
        try:
            # This is a simplified lookup - you might need to enhance based on your schema
            result = self.db.client.table('strategies').select('id').eq(
                'stock_name', symbol
            ).eq('strategy_name', strategy_name).order(
                'created_at'
            ).limit(1).execute()
            
            if result.data:
                return result.data[0]['id']
        except:
            pass
        return None
    
    def _parse_exit_conditions(self, exit_data: List[Dict]) -> Dict:
        """Parse exit conditions from database format"""
        conditions = {
            'profit_targets': {},
            'stop_losses': {},
            'time_exits': {}
        }
        
        for item in exit_data:
            level_type = item.get('level_type', '')
            if 'profit' in level_type.lower():
                conditions['profit_targets']['primary'] = {
                    'trigger_value': item.get('profit_percentage', 50)
                }
            elif 'stop' in level_type.lower():
                conditions['stop_losses']['primary'] = {
                    'trigger_value': item.get('stop_percentage', 50)
                }
        
        return conditions
    
    def run_continuous(self, interval_minutes: int = 5, max_cycles: Optional[int] = None):
        """
        Run continuous monitoring
        
        Args:
            interval_minutes: Minutes between monitoring cycles
            max_cycles: Maximum number of cycles (None for infinite)
        """
        logger.info(f"Starting continuous monitoring (interval: {interval_minutes} minutes)")
        
        if self.execute_exits:
            logger.warning("⚠️  LIVE MODE - Exits will be executed automatically!")
            print("\n⚠️  WARNING: Running in LIVE MODE - Exits will be executed automatically!")
            print("Press Ctrl+C to stop\n")
            time.sleep(5)  # Give user time to cancel
        else:
            logger.info("Running in SIMULATION mode - no actual trades will be executed")
        
        cycles_run = 0
        
        try:
            while max_cycles is None or cycles_run < max_cycles:
                # Run monitoring cycle
                results = self.run_monitoring_cycle()
                
                cycles_run += 1
                
                # Display detailed position table instead of simple summary
                self.display_position_table(results)
                
                if results.get('errors'):
                    print(f"\n⚠️  Errors encountered: {len(results['errors'])}")
                    for error in results['errors'][:3]:  # Show first 3 errors
                        print(f"   - {error.get('position', 'Unknown')}: {error.get('error', 'Unknown error')}")
                
                # Sleep until next cycle
                if max_cycles is None or cycles_run < max_cycles:
                    next_run = datetime.now() + timedelta(minutes=interval_minutes)
                    print(f"\n⏰ Next cycle at {next_run.strftime('%H:%M:%S')}")
                    time.sleep(interval_minutes * 60)
                    
        except KeyboardInterrupt:
            logger.info("Monitoring stopped by user")
            print("\n👋 Monitoring stopped")
        except Exception as e:
            logger.error(f"Fatal error in continuous monitoring: {e}")
            raise

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Automated options position monitor')
    
    parser.add_argument('--interval', '-i', type=int, default=5,
                       help='Monitoring interval in minutes (default: 5)')
    parser.add_argument('--execute', '-e', action='store_true',
                       help='Execute exits (LIVE MODE - use with caution!)')
    parser.add_argument('--alert-only', '-a', action='store_true',
                       help='Only generate alerts, don\'t execute exits')
    parser.add_argument('--cycles', '-c', type=int,
                       help='Number of cycles to run (default: infinite)')
    parser.add_argument('--once', action='store_true',
                       help='Run only one monitoring cycle')
    
    args = parser.parse_args()
    
    try:
        # Initialize monitor
        monitor = AutomatedMonitor(
            execute_exits=args.execute,
            alert_only=args.alert_only
        )
        
        if args.once:
            # Run single cycle
            results = monitor.run_monitoring_cycle()
            
            # Display the position table for single runs too
            monitor.display_position_table(results)
        else:
            # Run continuous monitoring
            monitor.run_continuous(
                interval_minutes=args.interval,
                max_cycles=args.cycles
            )
            
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()