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
                        'reason': evaluation.get('action_reason')
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
                
                # Display summary
                print(f"\n📊 Cycle {cycles_run} Summary:")
                print(f"   Positions: {results.get('positions_monitored', 0)}")
                print(f"   Alerts: {results.get('alerts_generated', 0)}")
                print(f"   Exits: {results.get('exits_executed', 0)}")
                
                if results.get('errors'):
                    print(f"   ⚠️  Errors: {len(results['errors'])}")
                
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
            
            print("\n📊 Monitoring Results:")
            print(json.dumps(results, indent=2))
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