#!/usr/bin/env python3
"""
Options V4 Strategy Executor via Dhan API
Executes marked strategies from Supabase using Dhan broker integration
"""

import os
import sys
import logging
from datetime import datetime
from dotenv import load_dotenv
from dhanhq import dhanhq
import json
import time

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv('/Users/jaykrish/Documents/digitalocean/.env')

from database import SupabaseIntegration

# Set up logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('options_v4_execution.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class OptionsV4Executor:
    def __init__(self):
        """Initialize executor with database and Dhan API connections"""
        # Initialize database
        self.db = SupabaseIntegration(logger)
        if not self.db.client:
            logger.error("Failed to connect to Supabase")
            raise Exception("Database connection failed")
        
        # Initialize DHAN client with token from .env
        try:
            client_id = os.getenv('DHAN_CLIENT_ID', '1100526168')
            access_token = os.getenv('DHAN_ACCESS_TOKEN')
            
            if not access_token:
                raise Exception("DHAN_ACCESS_TOKEN not found in environment variables")
            
            self.dhan = dhanhq(
                client_id=client_id, 
                access_token=access_token
            )
            logger.info("DHAN client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize DHAN client: {str(e)}")
            raise
    
    def get_marked_strategies(self):
        """Fetch all strategies marked for execution"""
        try:
            result = self.db.client.table('strategies').select(
                '*, strategy_details(*), strategy_parameters(*)'
            ).eq('marked_for_execution', True).eq(
                'execution_status', 'marked'
            ).order('execution_priority', desc=True).execute()
            
            if not result.data:
                logger.info("No strategies marked for execution")
                return []
            
            logger.info(f"Found {len(result.data)} strategies marked for execution")
            return result.data
            
        except Exception as e:
            logger.error(f"Error fetching marked strategies: {e}")
            return []
    
    def get_next_expiry_date(self, base_date=None):
        """Get the next monthly expiry (last Thursday of current/next month) - Legacy method"""
        return self.get_smart_expiry_date(base_date, use_legacy_logic=True)
    
    def get_smart_expiry_date(self, base_date=None, cutoff_day=20, use_legacy_logic=False):
        """
        Get expiry date using smart 20th date cutoff logic
        
        Args:
            base_date: Base date for calculation (default: now)
            cutoff_day: Cutoff day of month (default: 20)
            use_legacy_logic: Use old logic for backward compatibility
        
        Returns:
            datetime: Expiry date (last Thursday of target month)
        """
        import calendar
        from datetime import datetime
        
        if base_date is None:
            base_date = datetime.now()
        
        # Helper function to get last Thursday of a month
        def get_last_thursday(year, month):
            # Get last day of month
            last_day = calendar.monthrange(year, month)[1]
            # Find last Thursday
            for day in range(last_day, 0, -1):
                if datetime(year, month, day).weekday() == 3:  # Thursday = 3
                    return datetime(year, month, day)
            return None
        
        # Legacy logic (original behavior)
        if use_legacy_logic:
            year = base_date.year
            month = base_date.month
            current_expiry = get_last_thursday(year, month)
            
            # If current month's expiry has passed, use next month
            if current_expiry and current_expiry.date() <= base_date.date():
                if month == 12:
                    month = 1
                    year += 1
                else:
                    month += 1
                current_expiry = get_last_thursday(year, month)
            
            return current_expiry
        
        # Smart logic: Use 20th date cutoff
        current_day = base_date.day
        
        # If before cutoff day of month: try current month expiry
        if current_day <= cutoff_day:
            target_month = base_date.month
            target_year = base_date.year
            
            # Check if current month's expiry is still valid (hasn't passed)
            current_month_expiry = get_last_thursday(target_year, target_month)
            if current_month_expiry and current_month_expiry.date() > base_date.date():
                logger.info(f"Using current month expiry (day {current_day} <= cutoff {cutoff_day}): {current_month_expiry.strftime('%Y-%m-%d')}")
                return current_month_expiry
            else:
                # Current month expiry has passed, use next month
                logger.info(f"Current month expiry has passed, using next month")
                if target_month == 12:
                    target_month = 1
                    target_year += 1
                else:
                    target_month += 1
        else:
            # After cutoff day: use next month expiry
            logger.info(f"Using next month expiry (day {current_day} > cutoff {cutoff_day})")
            if base_date.month == 12:
                target_month = 1
                target_year = base_date.year + 1
            else:
                target_month = base_date.month + 1
                target_year = base_date.year
        
        target_expiry = get_last_thursday(target_year, target_month)
        logger.info(f"Selected expiry date: {target_expiry.strftime('%Y-%m-%d')}")
        return target_expiry
    
    def get_option_symbol(self, base_symbol, expiry_date, strike_price, option_type):
        """
        Construct option symbol in the format: BASE-MONTHYEAR-STRIKE-OPTIONTYPE
        
        Args:
            base_symbol: Underlying symbol (e.g., 'DIXON')
            expiry_date: Date object for expiry
            strike_price: Strike price (e.g., 14000)
            option_type: 'CE' or 'PE'
        """
        # Format: MMMYYYY (e.g., Aug2025)
        month_year = expiry_date.strftime("%b%Y")
        
        # Format: STRIKE (e.g., 14000)
        strike_str = str(int(strike_price))
        
        # Construct full symbol with hyphens
        symbol = f"{base_symbol}-{month_year}-{strike_str}-{option_type}"
        logger.info(f"Constructed option symbol: {symbol}")
        return symbol

    def get_security_id(self, symbol, option_type, strike_price, expiry_date=None):
        """Map strategy details to Dhan security ID using proven logic"""
        try:
            # Use smart expiry if not provided
            if expiry_date is None:
                expiry_date = self.get_smart_expiry_date()
            
            # Construct the option symbol
            option_symbol = self.get_option_symbol(symbol, expiry_date, strike_price, option_type)
            
            logger.info(f"Looking up security ID for: {option_symbol}")
            
            # Try exact match first using sem_custom_symbol
            exact_query = self.db.client.table('api_scrip_master').select(
                'sem_smst_security_id, sem_lot_units, sem_custom_symbol, sem_trading_symbol'
            ).eq('sem_custom_symbol', option_symbol).eq(
                'sem_option_type', option_type
            ).eq('sem_strike_price', strike_price)
            
            if expiry_date:
                exact_query = exact_query.eq('sem_expiry_date', expiry_date.strftime('%Y-%m-%d'))
            
            result = exact_query.execute()
            
            if result.data:
                security_data = result.data[0]
                logger.info(f"✅ Found exact match: {security_data}")
                return security_data['sem_smst_security_id'], security_data['sem_lot_units']
            
            # Try nearest strike if exact not found
            logger.info("Exact match not found, trying nearest strike...")
            
            nearest_query = self.db.client.table('api_scrip_master').select(
                'sem_smst_security_id, sem_lot_units, sem_strike_price, sem_custom_symbol'
            ).like('sem_custom_symbol', f'{symbol}-{expiry_date.strftime("%b%Y")}-%-%{option_type}').eq(
                'sem_option_type', option_type
            )
            
            if expiry_date:
                nearest_query = nearest_query.eq('sem_expiry_date', expiry_date.strftime('%Y-%m-%d'))
            
            nearest_result = nearest_query.execute()
            
            if nearest_result.data:
                # Find nearest strike
                best_match = None
                min_diff = float('inf')
                
                for item in nearest_result.data:
                    diff = abs(float(item['sem_strike_price']) - float(strike_price))
                    if diff < min_diff:
                        min_diff = diff
                        best_match = item
                
                if best_match:
                    logger.info(f"✅ Found nearest strike: {best_match}")
                    return best_match['sem_smst_security_id'], best_match['sem_lot_units']
            
            logger.error(f"❌ No security ID found for {option_symbol}")
            return None, None
                
        except Exception as e:
            logger.error(f"Error fetching security ID: {e}")
            return None, None
    
    def get_order_details(self, order_id):
        """
        Fetch order details from Dhan API to get executed price
        
        Args:
            order_id: The order ID to fetch details for
            
        Returns:
            Dictionary with order details or None if failed
        """
        try:
            logger.info(f"Fetching order details for order ID: {order_id}")
            
            # Fetch order details from Dhan API
            order_details = self.dhan.get_order_by_id(order_id)
            
            if order_details and order_details.get('status') == 'success':
                order_data_list = order_details.get('data', [])
                
                # Data comes as a list, get the first (and usually only) item
                if order_data_list and len(order_data_list) > 0:
                    order_data = order_data_list[0]
                    
                    # Extract relevant information
                    executed_price = order_data.get('averageTradedPrice', 0) or order_data.get('price', 0)
                    order_status = order_data.get('orderStatus', '')
                    filled_qty = order_data.get('filledQty', 0)
                    
                    logger.info(f"Order {order_id} - Status: {order_status}, Price: {executed_price}, Filled: {filled_qty}")
                    
                    # Extract expiry date
                    expiry_date = order_data.get('drvExpiryDate', None)
                    
                    return {
                        'order_id': order_id,
                        'executed_price': executed_price,
                        'order_status': order_status,
                        'filled_quantity': filled_qty,
                        'expiry_date': expiry_date,
                        'full_details': order_data
                    }
                else:
                    logger.warning(f"No order data found in response for {order_id}")
                    return None
            else:
                logger.warning(f"Failed to fetch order details for {order_id}: {order_details}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching order details for {order_id}: {e}")
            return None
    
    def update_trade_details(self, order_id, price, expiry_date=None):
        """
        Update the price and expiry date in trades table for a given order ID
        
        Args:
            order_id: The order ID to update
            price: The executed price to set
            expiry_date: The expiry date of the option
        """
        try:
            if price <= 0:
                logger.warning(f"Invalid price {price} for order {order_id}, skipping price update")
                # Still update expiry date if available
                if not expiry_date:
                    return False
                
            logger.info(f"Updating trade details for order {order_id} - Price: {price}, Expiry: {expiry_date}")
            
            # Build update data
            update_data = {}
            if price > 0:
                update_data['price'] = price
            if expiry_date:
                update_data['expiry_date'] = expiry_date
            
            # Update trades table
            result = self.db.client.table('trades').update(update_data).eq('order_id', order_id).execute()
            
            if result.data:
                logger.info(f"Successfully updated details for order {order_id}")
                return True
            else:
                logger.error(f"Failed to update details for order {order_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating trade details for order {order_id}: {e}")
            return False
    
    def execute_strategy_legs(self, strategy):
        """Execute all legs of a strategy"""
        strategy_id = strategy['id']
        logger.info(f"Executing strategy {strategy_id}: {strategy['stock_name']} - {strategy['strategy_name']}")
        
        if not strategy.get('strategy_details'):
            logger.error(f"No strategy details found for strategy {strategy_id}")
            return []
        
        all_responses = []
        execution_failed = False
        
        # Get expiry date from strategy_parameters
        expiry_date = None
        if strategy.get('strategy_parameters') and len(strategy['strategy_parameters']) > 0:
            expiry_date = strategy['strategy_parameters'][0].get('expiry_date')
        
        for leg in strategy['strategy_details']:
            logger.info(f"Processing leg: {leg['setup_type']} {leg['strike_price']} {leg['option_type']}")
            
            # Get security ID
            security_id, lot_size = self.get_security_id(
                strategy['stock_name'],
                leg['option_type'],
                leg['strike_price'],
                expiry_date
            )
            
            if not security_id:
                logger.error(f"Cannot find security ID for leg: {leg}")
                execution_failed = True
                all_responses.append({
                    'leg_id': leg['id'],
                    'status': 'failed',
                    'error': 'Security ID not found'
                })
                continue
            
            # Calculate quantity
            lots = leg.get('lots', 1)
            quantity = lots * (lot_size or 25)
            logger.info(f"Calculated quantity: {quantity} (lots: {lots} × lot size: {lot_size})")
            
            # Prepare order parameters
            order_params = {
                'security_id': security_id,
                'exchange_segment': 'NSE_FNO',
                'transaction_type': leg['setup_type'],
                'quantity': quantity,
                'order_type': 'MARKET',
                'product_type': 'MARGIN',
                'price': 0,
                'trigger_price': 0,
                'validity': 'DAY'
            }
            
            logger.info(f"Placing order with params: {order_params}")
            
            try:
                # Place the order
                order_response = self.dhan.place_order(**order_params)
                logger.info(f"Order response: {order_response}")
                
                # Handle response
                if order_response['status'] == 'success':
                    order_id = order_response['data']['orderId']
                    
                    # Store trade in database with initial price as 0
                    self.store_trade(
                        strategy_id=strategy_id,
                        order_id=order_id,
                        security_id=security_id,
                        transaction_type=leg['setup_type'],
                        quantity=quantity,
                        price=0,  # Will be updated after fetching order details
                        option_type=leg['option_type'],
                        strategy_name=strategy['strategy_name'],
                        symbol=strategy['stock_name'],
                        strike_price=leg['strike_price']
                    )
                    
                    # Wait 5 seconds for order to be processed
                    logger.info(f"Waiting 5 seconds before fetching order details for {order_id}...")
                    time.sleep(5)
                    
                    # Fetch order details to get executed price
                    order_details = self.get_order_details(order_id)
                    
                    if order_details:
                        # Update the trade with actual executed price and expiry date
                        self.update_trade_details(
                            order_id, 
                            order_details.get('executed_price', 0),
                            order_details.get('expiry_date')
                        )
                        logger.info(f"Updated order {order_id} with price {order_details.get('executed_price')} and expiry {order_details.get('expiry_date')}")
                    else:
                        logger.warning(f"Could not fetch order details for {order_id}, will need manual update")
                    
                    all_responses.append({
                        'leg_id': leg['id'],
                        'status': 'success',
                        'order_id': order_id,
                        'executed_price': order_details.get('executed_price', 0) if order_details else 0
                    })
                    
                elif 'market closed' in str(order_response.get('remarks', '')).lower():
                    logger.info(f"Market is closed, order deferred")
                    all_responses.append({
                        'leg_id': leg['id'],
                        'status': 'deferred',
                        'remarks': 'Market closed'
                    })
                else:
                    logger.error(f"Order failed: {order_response}")
                    execution_failed = True
                    all_responses.append({
                        'leg_id': leg['id'],
                        'status': 'failed',
                        'error': order_response.get('remarks', 'Unknown error')
                    })
                    
            except Exception as e:
                logger.error(f"Order placement exception: {e}")
                execution_failed = True
                all_responses.append({
                    'leg_id': leg['id'],
                    'status': 'failed',
                    'error': str(e)
                })
        
        # Update strategy execution status
        if not execution_failed:
            self.update_strategy_status(strategy_id, 'executed', all_responses)
        else:
            self.update_strategy_status(strategy_id, 'failed', all_responses)
        
        return all_responses
    
    def store_trade(self, strategy_id, order_id, security_id, transaction_type, 
                   quantity, price, option_type, strategy_name, symbol, strike_price):
        """Store executed trade in Supabase trades table"""
        try:
            trade_data = {
                'strategy_id': strategy_id,
                'order_id': order_id,
                'security_id': security_id,
                'symbol': symbol,
                'type': option_type,
                'strategy': strategy_name,
                'action': transaction_type,
                'trade_type': 'Long' if transaction_type == 'BUY' else 'Short',
                'quantity': quantity,
                'price': price,
                'strike_price': strike_price,
                'order_status': 'open',
                'timestamp': datetime.now().isoformat(),
                'product_type': 'MARGIN',
                'order_type': 'MARKET',
                'account_id': '1100526168',
                'expiry_date': None  # Will be updated after fetching order details
            }
            
            result = self.db.client.table('trades').insert(trade_data).execute()
            
            if result.data:
                logger.info(f"Trade stored successfully for order {order_id}")
            else:
                logger.error(f"Failed to store trade for order {order_id}")
                
        except Exception as e:
            logger.error(f"Error storing trade: {e}")
    
    def update_strategy_status(self, strategy_id, status, execution_details):
        """Update strategy execution status"""
        try:
            update_data = {
                'execution_status': status,
                'executed_at': datetime.now().isoformat()
            }
            
            # Add execution details to notes
            details_json = json.dumps(execution_details, indent=2)
            existing_notes = self.db.client.table('strategies').select(
                'execution_notes'
            ).eq('id', strategy_id).execute()
            
            if existing_notes.data and existing_notes.data[0].get('execution_notes'):
                update_data['execution_notes'] = f"{existing_notes.data[0]['execution_notes']}\n\nExecution Details:\n{details_json}"
            else:
                update_data['execution_notes'] = f"Execution Details:\n{details_json}"
            
            result = self.db.client.table('strategies').update(
                update_data
            ).eq('id', strategy_id).execute()
            
            if result.data:
                logger.info(f"Updated strategy {strategy_id} status to {status}")
            else:
                logger.error(f"Failed to update strategy {strategy_id} status")
                
        except Exception as e:
            logger.error(f"Error updating strategy status: {e}")
    
    def execute_all_marked(self):
        """Execute all strategies marked for execution"""
        strategies = self.get_marked_strategies()
        
        if not strategies:
            logger.info("No strategies to execute")
            return
        
        logger.info(f"Starting execution of {len(strategies)} strategies")
        
        results = []
        for strategy in strategies:
            logger.info(f"\n{'='*60}")
            logger.info(f"Executing: {strategy['stock_name']} - {strategy['strategy_name']}")
            logger.info(f"Priority: {strategy.get('execution_priority', 0)}")
            
            try:
                leg_results = self.execute_strategy_legs(strategy)
                results.append({
                    'strategy_id': strategy['id'],
                    'symbol': strategy['stock_name'],
                    'strategy_name': strategy['strategy_name'],
                    'legs': leg_results
                })
            except Exception as e:
                logger.error(f"Failed to execute strategy {strategy['id']}: {e}")
                self.update_strategy_status(strategy['id'], 'failed', [{'error': str(e)}])
        
        # Summary
        logger.info(f"\n{'='*60}")
        logger.info("EXECUTION SUMMARY")
        logger.info(f"{'='*60}")
        
        successful = sum(1 for r in results if all(leg['status'] == 'success' for leg in r['legs']))
        failed = sum(1 for r in results if any(leg['status'] == 'failed' for leg in r['legs']))
        deferred = sum(1 for r in results if any(leg['status'] == 'deferred' for leg in r['legs']))
        
        logger.info(f"Total strategies: {len(results)}")
        logger.info(f"Successful: {successful}")
        logger.info(f"Failed: {failed}")
        logger.info(f"Deferred (market closed): {deferred}")
        
        return results

    def execute_specific_strategy(self, strategy_id):
        """Execute a specific strategy by ID"""
        try:
            logger.info(f"Fetching strategy {strategy_id} for execution")
            
            # Fetch specific strategy
            result = self.db.client.table('strategies').select(
                '*, strategy_details(*), strategy_parameters(*)'
            ).eq('id', strategy_id).execute()
            
            if not result.data:
                logger.error(f"Strategy {strategy_id} not found")
                return None
            
            strategy = result.data[0]
            logger.info(f"Found strategy: {strategy['stock_name']} - {strategy['strategy_name']}")
            
            # Execute the strategy
            leg_results = self.execute_strategy_legs(strategy)
            
            return {
                'strategy_id': strategy['id'],
                'symbol': strategy['stock_name'],
                'strategy_name': strategy['strategy_name'],
                'legs': leg_results
            }
            
        except Exception as e:
            logger.error(f"Error executing specific strategy {strategy_id}: {e}")
            return None

def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Options V4 Strategy Executor')
    parser.add_argument('--execute', action='store_true', 
                       help='Execute all marked strategies')
    parser.add_argument('--strategy-id', type=int,
                       help='Execute specific strategy by ID')
    
    args = parser.parse_args()
    
    try:
        logger.info("Starting Options V4 Strategy Executor")
        executor = OptionsV4Executor()
        
        if args.strategy_id:
            # Execute specific strategy
            logger.info(f"Executing specific strategy ID: {args.strategy_id}")
            result = executor.execute_specific_strategy(args.strategy_id)
            
            if result:
                logger.info(f"\nExecution completed for strategy {args.strategy_id}")
                logger.info(f"{result['symbol']} - {result['strategy_name']}:")
                for leg in result['legs']:
                    logger.info(f"  Leg {leg.get('leg_id', 'N/A')}: {leg['status']}")
                    if 'executed_price' in leg:
                        logger.info(f"    Executed Price: {leg['executed_price']}")
            else:
                logger.error(f"Failed to execute strategy {args.strategy_id}")
                
        elif args.execute:
            # Execute all marked strategies
            results = executor.execute_all_marked()
            
            if results:
                logger.info("\nExecution completed")
                for result in results:
                    logger.info(f"\n{result['symbol']} - {result['strategy_name']}:")
                    for leg in result['legs']:
                        logger.info(f"  Leg {leg.get('leg_id', 'N/A')}: {leg['status']}")
            else:
                logger.info("No strategies were executed")
        else:
            parser.print_help()
            
    except Exception as e:
        logger.error(f"Executor failed: {e}", exc_info=True)

if __name__ == "__main__":
    main()