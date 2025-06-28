#!/usr/bin/env python3
"""
Real-time Automated Position Monitor
Enhanced version with WebSocket streaming and instant exit triggers
"""

import asyncio
import logging
import signal
import sys
import time
import argparse
from datetime import datetime
from typing import Dict, List, Optional
from tabulate import tabulate
import os

# Import existing components
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from trade_monitoring.legacy.position_monitor import PositionMonitor
from trade_execution.exit_evaluator import ExitEvaluator
from trade_execution.exit_executor import ExitExecutor
from data_scripts.realtime_market_fetcher import RealtimeMarketFetcher
from trade_monitoring.realtime.websocket_manager import WebSocketManager
from trade_monitoring.realtime.supabase_realtime import SupabaseRealtime
from database.supabase_integration import SupabaseIntegration

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/realtime_automated_monitor.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class RealtimeAutomatedMonitor:
    """
    Real-time automated position monitor with WebSocket streaming
    """
    
    def __init__(self, execute_exits=False, alert_only=False, enable_websocket=True):
        """
        Initialize real-time automated monitor
        
        Args:
            execute_exits: Whether to execute actual exit orders
            alert_only: Whether to only generate alerts (no exits)
            enable_websocket: Enable WebSocket real-time features
        """
        self.logger = logging.getLogger(__name__)
        
        # Configuration
        self.execute_exits = execute_exits
        self.alert_only = alert_only
        self.enable_websocket = enable_websocket
        
        # Running state
        self.is_running = False
        self.shutdown_requested = False
        
        # Initialize core components
        self.position_monitor = PositionMonitor()
        self.exit_evaluator = ExitEvaluator()
        self.exit_executor = ExitExecutor()
        
        # Initialize real-time market fetcher
        self.market_fetcher = RealtimeMarketFetcher(
            enable_websocket=enable_websocket,
            enable_cache=True
        )
        
        # Add price update handler for instant evaluation
        self.market_fetcher.add_price_update_handler(self._handle_price_update)
        
        # Initialize Supabase realtime for trade updates
        self.supabase_realtime = None
        if enable_websocket:
            try:
                self.supabase_realtime = SupabaseRealtime()
                self.supabase_realtime.add_trade_handler(self._handle_trade_update)
                self.logger.info("Supabase realtime initialized")
            except Exception as e:
                self.logger.warning(f"Supabase realtime initialization failed: {e}")
        
        # Exit tracking to prevent duplicates
        self.executed_exits = set()
        self.last_evaluation_time = {}
        
        # Statistics
        self.stats = {
            'positions_monitored': 0,
            'alerts_generated': 0,
            'exits_executed': 0,
            'price_updates_processed': 0,
            'trade_updates_processed': 0,
            'errors': 0
        }
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        mode = "LIVE EXECUTION" if execute_exits else "SIMULATION"
        rt_status = "ENABLED" if enable_websocket else "DISABLED"
        self.logger.info(f"Realtime Automated Monitor initialized")
        self.logger.info(f"Mode: {mode}, WebSocket: {rt_status}")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.shutdown_requested = True
    
    async def start(self, interval_seconds=300):
        """
        Start the real-time monitoring system
        
        Args:
            interval_seconds: Fallback polling interval (default 5 minutes)
        """
        try:
            self.is_running = True
            self.logger.info("Starting real-time automated monitor...")
            
            # Start real-time market feed
            if self.enable_websocket:
                rt_success = await self.market_fetcher.start_realtime_feed()
                if rt_success:
                    self.logger.info("✅ Real-time market feed active")
                else:
                    self.logger.warning("⚠️ Real-time feed failed, using REST fallback")
                
                # Start Supabase realtime
                if self.supabase_realtime:
                    try:
                        await self.supabase_realtime.start()
                        self.logger.info("✅ Supabase realtime active")
                    except Exception as e:
                        self.logger.warning(f"Supabase realtime failed: {e}")
            
            # Start periodic monitoring task
            monitor_task = asyncio.create_task(
                self._periodic_monitoring_loop(interval_seconds)
            )
            
            # Start real-time price evaluation task
            if self.enable_websocket:
                price_eval_task = asyncio.create_task(
                    self._realtime_evaluation_loop()
                )
                
                # Wait for either task to complete or shutdown
                await asyncio.gather(monitor_task, price_eval_task, return_exceptions=True)
            else:
                await monitor_task
            
        except Exception as e:
            self.logger.error(f"Error in monitoring system: {e}")
        finally:
            await self.stop()
    
    async def stop(self):
        """Stop the monitoring system"""
        self.is_running = False
        self.logger.info("Stopping real-time monitoring system...")
        
        # Stop real-time feeds
        if self.market_fetcher:
            await self.market_fetcher.stop_realtime_feed()
        
        if self.supabase_realtime:
            await self.supabase_realtime.stop()
        
        # Log final statistics
        self._log_final_statistics()
        self.logger.info("Real-time monitoring system stopped")
    
    async def _periodic_monitoring_loop(self, interval_seconds):
        """Periodic monitoring loop as fallback and comprehensive check"""
        while self.is_running and not self.shutdown_requested:
            try:
                start_time = time.time()
                
                # Perform comprehensive monitoring cycle
                results = await self._perform_monitoring_cycle()
                
                # Update statistics
                self.stats['positions_monitored'] = results.get('total_positions', 0)
                self.stats['alerts_generated'] += results.get('alerts_generated', 0)
                self.stats['exits_executed'] += results.get('exits_executed', 0)
                
                # Display results
                self._display_monitoring_results(results)
                
                cycle_time = time.time() - start_time
                self.logger.info(f"Monitoring cycle completed in {cycle_time:.2f}s")
                
                # Wait for next cycle
                await asyncio.sleep(interval_seconds)
                
            except Exception as e:
                self.logger.error(f"Error in periodic monitoring: {e}")
                self.stats['errors'] += 1
                await asyncio.sleep(30)  # Wait before retrying
    
    async def _realtime_evaluation_loop(self):
        """Real-time evaluation loop for instant price-based exits"""
        self.logger.info("Real-time evaluation loop started")
        
        while self.is_running and not self.shutdown_requested:
            try:
                # This loop handles events triggered by price updates
                # The actual work is done in _handle_price_update
                await asyncio.sleep(1)  # Minimal sleep to prevent busy loop
                
            except Exception as e:
                self.logger.error(f"Error in real-time evaluation loop: {e}")
                await asyncio.sleep(5)
    
    async def _perform_monitoring_cycle(self):
        """Perform a complete monitoring cycle"""
        try:
            self.logger.info("Starting monitoring cycle...")
            
            # Get all open positions
            positions = self.position_monitor.get_open_positions()
            
            if not positions:
                self.logger.info("No open positions found")
                return {
                    'total_positions': 0,
                    'alerts_generated': 0,
                    'exits_executed': 0,
                    'details': []
                }
            
            # Get security IDs from positions
            security_ids = []
            for position in positions:
                for leg in position['legs']:
                    if leg.get('security_id'):
                        security_ids.append(leg['security_id'])
            
            # Get current market prices using realtime fetcher
            if security_ids:
                current_prices_dict = self.market_fetcher.get_multiple_latest_prices(security_ids)
                # Convert to format expected by position monitor: {security_id: ltp}
                current_prices = {}
                for security_id, price_data in current_prices_dict.items():
                    current_prices[security_id] = price_data.get('ltp', 0)
            else:
                current_prices = {}
            
            if not current_prices:
                self.logger.error("Failed to fetch market prices")
                return {'total_positions': len(positions), 'alerts_generated': 0, 'exits_executed': 0}
            
            # Process each position
            results = {
                'total_positions': len(positions),
                'alerts_generated': 0,
                'exits_executed': 0,
                'details': []
            }
            
            for position in positions:
                try:
                    await self._process_position(position, current_prices, results)
                except Exception as e:
                    self.logger.error(f"Error processing position {position.get('symbol')}: {e}")
                    self.stats['errors'] += 1
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error in monitoring cycle: {e}")
            return {'total_positions': 0, 'alerts_generated': 0, 'exits_executed': 0}
    
    async def _process_position(self, position: Dict, current_prices: Dict, results: Dict):
        """Process a single position for exit conditions"""
        try:
            position_key = f"{position['strategy_id']}_{position['symbol']}"
            
            # Skip if already executed in this session
            if position_key in self.executed_exits:
                return
            
            # Calculate P&L
            pnl_data = self.position_monitor.calculate_position_pnl(position, current_prices)
            
            # Get exit conditions
            exit_conditions = self.position_monitor.get_exit_conditions(position['strategy_id'])
            
            # Evaluate exit conditions
            evaluation = self.exit_evaluator.evaluate_position(pnl_data, exit_conditions)
            
            # Create position info for results
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
                'current_value': pnl_data.get('current_value', 0),
                'actual_dte': pnl_data.get('actual_dte'),
                'expiry_date': pnl_data.get('expiry_date')
            }
            
            results['details'].append(position_info)
            
            # Process based on urgency and action
            if evaluation.get('urgency') in ['HIGH', 'MEDIUM'] and \
               evaluation.get('recommended_action') != 'MONITOR':
                
                results['alerts_generated'] += 1
                
                # Generate alert
                await self._generate_alert(position, pnl_data, evaluation)
                
                # Execute exit if enabled
                if not self.alert_only and evaluation.get('recommended_action') in [
                    'CLOSE_IMMEDIATELY', 'CLOSE_POSITION'
                ]:
                    success = await self._execute_position_exit(position, evaluation)
                    if success:
                        results['exits_executed'] += 1
                        self.executed_exits.add(position_key)
            
        except Exception as e:
            self.logger.error(f"Error processing position: {e}")
            self.stats['errors'] += 1
    
    async def _handle_price_update(self, price_data: Dict):
        """Handle real-time price updates for instant evaluation"""
        try:
            self.stats['price_updates_processed'] += 1
            security_id = price_data.get('security_id')
            ltp = price_data.get('ltp', 0)
            
            # Get positions that include this security ID
            affected_positions = self._get_positions_for_security(security_id)
            
            for position in affected_positions:
                position_key = f"{position['strategy_id']}_{position['symbol']}"
                
                # Skip if already executed
                if position_key in self.executed_exits:
                    continue
                
                # Throttle evaluation (max once per 5 seconds per position)
                current_time = time.time()
                last_eval = self.last_evaluation_time.get(position_key, 0)
                if current_time - last_eval < 5:
                    continue
                
                self.last_evaluation_time[position_key] = current_time
                
                # Quick evaluation for critical exit conditions
                await self._quick_evaluate_position(position, price_data)
                
        except Exception as e:
            self.logger.error(f"Error handling price update: {e}")
            self.stats['errors'] += 1
    
    async def _handle_trade_update(self, trade_data: Dict):
        """Handle real-time trade table updates"""
        try:
            self.stats['trade_updates_processed'] += 1
            
            event_type = trade_data.get('eventType')
            record = trade_data.get('record', {})
            
            self.logger.info(f"Trade update: {event_type} - {record.get('symbol')}")
            
            # If new trade opened, refresh instruments and subscriptions
            if event_type == 'INSERT':
                await self._handle_new_trade(record)
            elif event_type == 'UPDATE':
                await self._handle_trade_update_event(record)
                
        except Exception as e:
            self.logger.error(f"Error handling trade update: {e}")
            self.stats['errors'] += 1
    
    def _get_positions_for_security(self, security_id: int) -> List[Dict]:
        """Get positions that include a specific security ID"""
        try:
            all_positions = self.position_monitor.get_open_positions()
            affected_positions = []
            
            for position in all_positions:
                for leg in position.get('legs', []):
                    if leg.get('security_id') == security_id:
                        affected_positions.append(position)
                        break
            
            return affected_positions
            
        except Exception as e:
            self.logger.error(f"Error getting positions for security: {e}")
            return []
    
    async def _quick_evaluate_position(self, position: Dict, price_data: Dict):
        """Quick evaluation for critical exit conditions"""
        try:
            # Get current prices with the updated price
            current_prices = self.market_fetcher.get_market_quotes()
            
            # Calculate P&L
            pnl_data = self.position_monitor.calculate_position_pnl(position, current_prices)
            
            # Get exit conditions
            exit_conditions = self.position_monitor.get_exit_conditions(position['strategy_id'])
            
            # Quick evaluation focusing on critical conditions
            evaluation = self.exit_evaluator.evaluate_position(pnl_data, exit_conditions)
            
            # Only act on HIGH urgency exits
            if evaluation.get('urgency') == 'HIGH' and \
               evaluation.get('recommended_action') in ['CLOSE_IMMEDIATELY']:
                
                self.logger.warning(f"URGENT EXIT TRIGGERED: {position['symbol']} - {evaluation.get('action_reason')}")
                
                # Generate alert
                await self._generate_alert(position, pnl_data, evaluation)
                
                # Execute exit immediately if enabled
                if not self.alert_only:
                    position_key = f"{position['strategy_id']}_{position['symbol']}"
                    success = await self._execute_position_exit(position, evaluation)
                    if success:
                        self.executed_exits.add(position_key)
                        self.stats['exits_executed'] += 1
                        self.logger.info(f"URGENT EXIT EXECUTED: {position['symbol']}")
                
        except Exception as e:
            self.logger.error(f"Error in quick evaluation: {e}")
    
    async def _execute_position_exit(self, position: Dict, evaluation: Dict) -> bool:
        """Execute position exit"""
        try:
            if self.execute_exits:
                # Execute actual exit
                exit_result = self.exit_executor.execute_exit(position, evaluation)
            else:
                # Simulate exit
                exit_result = self.exit_executor.simulate_exit(position, evaluation)
            
            success = exit_result.get('success', False)
            
            if success:
                self.logger.info(f"Exit executed: {position['symbol']} - {evaluation.get('action_reason')}")
            else:
                self.logger.error(f"Exit failed: {position['symbol']} - {exit_result.get('message')}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error executing exit: {e}")
            return False
    
    async def _generate_alert(self, position: Dict, pnl_data: Dict, evaluation: Dict):
        """Generate alert for position"""
        try:
            urgency = evaluation.get('urgency', 'LOW')
            symbol = position.get('symbol', 'Unknown')
            strategy = position.get('strategy_name', 'Unknown')
            action = evaluation.get('recommended_action', 'MONITOR')
            reason = evaluation.get('action_reason', 'No reason')
            pnl = pnl_data.get('total_pnl', 0)
            
            alert_msg = f"ALERT [{urgency}] {symbol} - {strategy}: {action} (P&L: {pnl:.2f})"
            
            if urgency == 'HIGH':
                self.logger.warning(alert_msg)
            else:
                self.logger.info(alert_msg)
            
            # Could send to external alert system here
            
        except Exception as e:
            self.logger.error(f"Error generating alert: {e}")
    
    async def _handle_new_trade(self, trade_record: Dict):
        """Handle new trade insertion"""
        try:
            self.logger.info(f"New trade detected: {trade_record.get('symbol')}")
            
            # Refresh instruments from database
            self.market_fetcher.refresh_instruments_from_database()
            
            # The subscription update will happen automatically via refresh
            
        except Exception as e:
            self.logger.error(f"Error handling new trade: {e}")
    
    async def _handle_trade_update_event(self, trade_record: Dict):
        """Handle trade update (e.g., exit order filled)"""
        try:
            symbol = trade_record.get('symbol')
            order_status = trade_record.get('order_status')
            
            self.logger.info(f"Trade updated: {symbol} - Status: {order_status}")
            
            # If trade was closed, we can remove it from monitoring
            if order_status == 'closed':
                strategy_id = trade_record.get('strategy_id')
                position_key = f"{strategy_id}_{symbol}"
                self.executed_exits.add(position_key)
                
        except Exception as e:
            self.logger.error(f"Error handling trade update: {e}")
    
    def _display_monitoring_results(self, results: Dict):
        """Display monitoring results in a formatted table"""
        try:
            print("\n" + "="*100)
            print(f"REAL-TIME POSITION MONITOR - STATUS")
            print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            mode = "LIVE EXECUTION" if self.execute_exits else "SIMULATION"
            print(f"Mode: {mode}")
            print("="*100)
            
            details = results.get('details', [])
            if details:
                # Prepare table data
                table_data = []
                for detail in details:
                    table_data.append([
                        detail['strategy'],
                        detail['symbol'],
                        f"₹{detail['pnl']:.2f} ({detail['pnl_pct']:.2f}%)",
                        detail['action'],
                        detail['urgency'],
                        detail['reason'][:30] + "..." if len(detail['reason']) > 30 else detail['reason']
                    ])
                
                headers = ['Strategy', 'Symbol', 'P&L', 'Action', 'Urgency', 'Reason']
                print("\n📊 POSITION DETAILS")
                print(tabulate(table_data, headers=headers, tablefmt='grid'))
            
            # Statistics
            print(f"\n📈 STATISTICS")
            print(f"Positions: {results['total_positions']}")
            print(f"Alerts: {results['alerts_generated']}")
            print(f"Exits: {results['exits_executed']}")
            print(f"Price Updates: {self.stats['price_updates_processed']}")
            print(f"Trade Updates: {self.stats['trade_updates_processed']}")
            print(f"Errors: {self.stats['errors']}")
            
            # Connection status
            if self.enable_websocket:
                status = self.market_fetcher.get_connection_status()
                print(f"\n🔗 CONNECTION STATUS")
                print(f"Real-time: {'✅' if status['realtime_active'] else '❌'}")
                print(f"WebSocket: {'✅' if status['websocket_connected'] else '❌'}")
                print(f"Cached Prices: {status.get('cached_prices', 0)}")
                print(f"Subscribed Instruments: {status['subscribed_instruments']}")
            
        except Exception as e:
            self.logger.error(f"Error displaying results: {e}")
    
    def _log_final_statistics(self):
        """Log final statistics"""
        self.logger.info("=== FINAL STATISTICS ===")
        self.logger.info(f"Positions Monitored: {self.stats['positions_monitored']}")
        self.logger.info(f"Alerts Generated: {self.stats['alerts_generated']}")
        self.logger.info(f"Exits Executed: {self.stats['exits_executed']}")
        self.logger.info(f"Price Updates Processed: {self.stats['price_updates_processed']}")
        self.logger.info(f"Trade Updates Processed: {self.stats['trade_updates_processed']}")
        self.logger.info(f"Errors Encountered: {self.stats['errors']}")
        self.logger.info("=== END STATISTICS ===")

# CLI Interface
async def main():
    parser = argparse.ArgumentParser(description='Real-time Automated Position Monitor')
    parser.add_argument('--execute', action='store_true', 
                       help='Execute actual exit orders (default: simulation)')
    parser.add_argument('--alert-only', action='store_true',
                       help='Generate alerts only, no exit execution')
    parser.add_argument('--interval', type=int, default=300,
                       help='Fallback polling interval in seconds (default: 300)')
    parser.add_argument('--no-websocket', action='store_true',
                       help='Disable WebSocket features (REST only)')
    parser.add_argument('--once', action='store_true',
                       help='Run once and exit')
    
    args = parser.parse_args()
    
    # Initialize monitor
    monitor = RealtimeAutomatedMonitor(
        execute_exits=args.execute,
        alert_only=args.alert_only,
        enable_websocket=not args.no_websocket
    )
    
    try:
        if args.once:
            # Run a single monitoring cycle
            results = await monitor._perform_monitoring_cycle()
            monitor._display_monitoring_results(results)
        else:
            # Start continuous monitoring
            await monitor.start(interval_seconds=args.interval)
            
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        await monitor.stop()

if __name__ == "__main__":
    asyncio.run(main())