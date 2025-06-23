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

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

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
        """Get the next monthly expiry (last Thursday of current/next month)"""
        import calendar
        from datetime import datetime
        
        if base_date is None:
            base_date = datetime.now()
        
        # Start with current month
        year = base_date.year
        month = base_date.month
        
        # Get last Thursday of the month
        def get_last_thursday(year, month):
            # Get last day of month
            last_day = calendar.monthrange(year, month)[1]
            # Find last Thursday
            for day in range(last_day, 0, -1):
                if datetime(year, month, day).weekday() == 3:  # Thursday = 3
                    return datetime(year, month, day)
            return None
        
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
            # Use next expiry if not provided
            if expiry_date is None:
                expiry_date = self.get_next_expiry_date()
            
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
                    # Store trade in database
                    self.store_trade(
                        strategy_id=strategy_id,
                        order_id=order_response['data']['orderId'],
                        security_id=security_id,
                        transaction_type=leg['setup_type'],
                        quantity=quantity,
                        price=0,  # Market order
                        option_type=leg['option_type'],
                        strategy_name=strategy['strategy_name'],
                        symbol=strategy['stock_name'],
                        strike_price=leg['strike_price']
                    )
                    
                    all_responses.append({
                        'leg_id': leg['id'],
                        'status': 'success',
                        'order_id': order_response['data']['orderId']
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
                'account_id': '1100526168'
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

def main():
    """Main execution function"""
    try:
        logger.info("Starting Options V4 Strategy Executor")
        executor = OptionsV4Executor()
        
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
            
    except Exception as e:
        logger.error(f"Executor failed: {e}", exc_info=True)

if __name__ == "__main__":
    main()