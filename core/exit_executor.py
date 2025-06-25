"""
Exit Executor for Options V4
Executes exit orders when conditions are triggered
"""

import os
import sys
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dhanhq import dhanhq

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.supabase_integration import SupabaseIntegration

logger = logging.getLogger(__name__)

class ExitExecutor:
    """
    Executes exit orders via Dhan API
    
    Features:
    - Place exit orders
    - Handle partial exits
    - Update database
    - Error handling
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize exit executor with Dhan API and database"""
        self.logger = logger or self._setup_logger()
        
        # Initialize database
        self.db = SupabaseIntegration(self.logger)
        if not self.db.client:
            raise ValueError("Failed to initialize database connection")
        
        # Initialize Dhan API
        try:
            client_id = os.getenv('DHAN_CLIENT_ID', '1100526168')
            access_token = os.getenv('DHAN_ACCESS_TOKEN')
            
            if not access_token:
                raise ValueError("DHAN_ACCESS_TOKEN not found in environment")
            
            self.dhan = dhanhq(client_id=client_id, access_token=access_token)
            self.logger.info("Exit Executor initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Dhan API: {e}")
            raise
    
    def _setup_logger(self) -> logging.Logger:
        """Setup default logger if none provided"""
        logger = logging.getLogger('ExitExecutor')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def execute_exit(self, position: Dict, evaluation: Dict) -> Dict:
        """
        Execute exit based on evaluation recommendation
        
        Args:
            position: Position data with leg details
            evaluation: Exit evaluation with recommended action
            
        Returns:
            Dictionary with execution results
        """
        try:
            action = evaluation.get('recommended_action', 'MONITOR')
            
            if action == 'MONITOR':
                return {
                    'success': True,
                    'action': 'NO_ACTION',
                    'message': 'Position is being monitored, no action needed'
                }
            
            # Log the exit decision
            self.logger.info(f"Executing exit for {position['symbol']} - {position['strategy_name']}")
            self.logger.info(f"Action: {action}, Reason: {evaluation.get('action_reason')}")
            
            # Determine exit type
            if action in ['CLOSE_IMMEDIATELY', 'CLOSE_POSITION']:
                return self._execute_full_exit(position)
            elif action.startswith('CLOSE_'):
                # Partial exit (e.g., CLOSE_50%, CLOSE_25%)
                percentage = self._parse_exit_percentage(action)
                return self._execute_partial_exit(position, percentage)
            elif action == 'ADJUST':
                return self._execute_adjustment(position, evaluation)
            else:
                return {
                    'success': False,
                    'action': action,
                    'message': f'Unknown action type: {action}'
                }
                
        except Exception as e:
            self.logger.error(f"Error executing exit: {e}")
            return {
                'success': False,
                'action': 'ERROR',
                'message': str(e)
            }
    
    def _execute_full_exit(self, position: Dict) -> Dict:
        """Execute full position exit"""
        try:
            results = []
            
            # Place exit orders for each leg
            for leg in position['legs']:
                # Determine exit action (opposite of entry)
                exit_action = 'BUY' if leg['action'] == 'SELL' else 'SELL'
                
                order_result = self._place_exit_order(
                    security_id=leg['security_id'],
                    action=exit_action,
                    quantity=leg['quantity'],
                    symbol=position['symbol'],
                    strike=leg['strike_price'],
                    option_type=leg['type']
                )
                
                results.append(order_result)
                
                # Update trade record
                if order_result['success']:
                    self._update_trade_exit(
                        trade_id=leg['trade_id'],
                        exit_order_id=order_result.get('order_id'),
                        exit_price=order_result.get('price', 0),
                        exit_reason=f"Exit signal: {position.get('exit_signal', 'Manual')}"
                    )
            
            # Check if all exits were successful
            all_success = all(r['success'] for r in results)
            
            return {
                'success': all_success,
                'action': 'FULL_EXIT',
                'message': f"Exited {len(results)} legs",
                'details': results
            }
            
        except Exception as e:
            self.logger.error(f"Error in full exit: {e}")
            return {
                'success': False,
                'action': 'FULL_EXIT',
                'message': str(e)
            }
    
    def _execute_partial_exit(self, position: Dict, percentage: int) -> Dict:
        """Execute partial position exit"""
        try:
            # Calculate quantity to exit
            total_quantity = position.get('total_quantity', 0)
            exit_quantity = int(total_quantity * percentage / 100)
            
            if exit_quantity <= 0:
                return {
                    'success': False,
                    'action': f'PARTIAL_EXIT_{percentage}%',
                    'message': 'Exit quantity too small'
                }
            
            results = []
            
            # Exit proportionally from each leg
            for leg in position['legs']:
                leg_exit_qty = int(leg['quantity'] * percentage / 100)
                if leg_exit_qty > 0:
                    exit_action = 'BUY' if leg['action'] == 'SELL' else 'SELL'
                    
                    order_result = self._place_exit_order(
                        security_id=leg['security_id'],
                        action=exit_action,
                        quantity=leg_exit_qty,
                        symbol=position['symbol'],
                        strike=leg['strike_price'],
                        option_type=leg['type']
                    )
                    
                    results.append(order_result)
            
            return {
                'success': any(r['success'] for r in results),
                'action': f'PARTIAL_EXIT_{percentage}%',
                'message': f"Partially exited {percentage}% of position",
                'details': results
            }
            
        except Exception as e:
            self.logger.error(f"Error in partial exit: {e}")
            return {
                'success': False,
                'action': f'PARTIAL_EXIT_{percentage}%',
                'message': str(e)
            }
    
    def _execute_adjustment(self, position: Dict, evaluation: Dict) -> Dict:
        """Execute position adjustment"""
        # For now, just log the adjustment recommendation
        # Actual adjustment logic would be strategy-specific
        return {
            'success': True,
            'action': 'ADJUSTMENT_LOGGED',
            'message': 'Adjustment recommendation logged for manual review',
            'details': evaluation.get('details', [])
        }
    
    def _place_exit_order(self, security_id: int, action: str, quantity: int,
                         symbol: str, strike: float, option_type: str) -> Dict:
        """Place exit order via Dhan API"""
        try:
            # Prepare order parameters
            order_params = {
                'transaction_type': dhanhq.BUY if action == 'BUY' else dhanhq.SELL,
                'exchange_segment': dhanhq.NSE_FNO,
                'product_type': dhanhq.MARGIN,  # or INTRADAY based on position
                'order_type': dhanhq.MARKET,  # Market order for immediate exit
                'validity': dhanhq.DAY,
                'security_id': str(security_id),
                'quantity': quantity,
                'disclosed_quantity': 0,
                'price': 0,  # Market order
                'trigger_price': 0,
                'after_market_order': False,
                'amo_time': 'OPEN',
                'bo_profit_value': 0,
                'bo_stop_loss_value': 0,
                'drv_expiry_date': None,  # Will be set based on position
                'drv_options_type': 'CE' if option_type == 'CE' else 'PE',
                'drv_strike_price': strike
            }
            
            # Place order
            response = self.dhan.place_order(order_params)
            
            if response and response.get('status') == 'success':
                order_id = response.get('data', {}).get('orderId')
                self.logger.info(f"Exit order placed successfully: {order_id}")
                
                return {
                    'success': True,
                    'order_id': order_id,
                    'security_id': security_id,
                    'action': action,
                    'quantity': quantity,
                    'message': f"Order {order_id} placed for {symbol} {strike} {option_type}"
                }
            else:
                error_msg = response.get('remarks', {}).get('message', 'Unknown error')
                self.logger.error(f"Failed to place exit order: {error_msg}")
                
                return {
                    'success': False,
                    'security_id': security_id,
                    'action': action,
                    'quantity': quantity,
                    'message': f"Order failed: {error_msg}"
                }
                
        except Exception as e:
            self.logger.error(f"Error placing exit order: {e}")
            return {
                'success': False,
                'security_id': security_id,
                'message': str(e)
            }
    
    def _update_trade_exit(self, trade_id: int, exit_order_id: str, 
                          exit_price: float, exit_reason: str):
        """Update trade record with exit details"""
        try:
            update_data = {
                'exit_order_id': exit_order_id,
                'exit_price': exit_price,
                'exit_time': datetime.now().isoformat(),
                'exit_reason': exit_reason,
                'order_status': 'closed'
            }
            
            self.db.client.table('trades').update(update_data).eq(
                'id', trade_id
            ).execute()
            
            self.logger.info(f"Updated trade {trade_id} with exit details")
            
        except Exception as e:
            self.logger.error(f"Error updating trade exit: {e}")
    
    def _parse_exit_percentage(self, action: str) -> int:
        """Parse percentage from action string (e.g., CLOSE_50% -> 50)"""
        try:
            # Extract number from string like "CLOSE_50%"
            import re
            match = re.search(r'(\d+)', action)
            if match:
                return int(match.group(1))
            return 100  # Default to full exit
        except:
            return 100
    
    def simulate_exit(self, position: Dict, evaluation: Dict) -> Dict:
        """Simulate exit without placing actual orders (for testing)"""
        try:
            action = evaluation.get('recommended_action', 'MONITOR')
            
            self.logger.info(f"[SIMULATION] Would execute: {action}")
            self.logger.info(f"[SIMULATION] Position: {position['symbol']} - {position['strategy_name']}")
            self.logger.info(f"[SIMULATION] Reason: {evaluation.get('action_reason')}")
            
            # Simulate order details
            if action in ['CLOSE_IMMEDIATELY', 'CLOSE_POSITION']:
                for leg in position['legs']:
                    exit_action = 'BUY' if leg['action'] == 'SELL' else 'SELL'
                    self.logger.info(
                        f"[SIMULATION] Would place: {exit_action} {leg['quantity']} "
                        f"{position['symbol']} {leg['strike_price']} {leg['type']}"
                    )
            
            return {
                'success': True,
                'action': f'SIMULATED_{action}',
                'message': 'Exit simulation completed'
            }
            
        except Exception as e:
            self.logger.error(f"Error in simulation: {e}")
            return {
                'success': False,
                'action': 'SIMULATION_ERROR',
                'message': str(e)
            }

def main():
    """Test the exit executor"""
    executor = ExitExecutor()
    
    # Test data
    test_position = {
        'strategy_id': 1,
        'symbol': 'TEST',
        'strategy_name': 'Bull Call Spread',
        'total_quantity': 100,
        'legs': [
            {
                'trade_id': 1,
                'security_id': 12345,
                'action': 'BUY',
                'type': 'CE',
                'strike_price': 100,
                'quantity': 100
            },
            {
                'trade_id': 2,
                'security_id': 12346,
                'action': 'SELL',
                'type': 'CE',
                'strike_price': 110,
                'quantity': 100
            }
        ]
    }
    
    test_evaluation = {
        'recommended_action': 'CLOSE_POSITION',
        'action_reason': 'Profit target hit',
        'urgency': 'MEDIUM'
    }
    
    print("\n📊 Exit Executor Test")
    print("=" * 60)
    
    # Simulate exit
    result = executor.simulate_exit(test_position, test_evaluation)
    
    print(f"\nSimulation Result: {result['action']}")
    print(f"Message: {result['message']}")

if __name__ == "__main__":
    main()