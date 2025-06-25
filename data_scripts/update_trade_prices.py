#!/usr/bin/env python3
"""
Update Trade Prices Utility
Fetches order details and updates entry prices for trades with price=0
"""

import os
import sys
import logging
import time
from datetime import datetime
from dotenv import load_dotenv
from dhanhq import dhanhq

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.supabase_integration import SupabaseIntegration

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

class TradePriceUpdater:
    def __init__(self):
        """Initialize with Dhan API and Supabase connections"""
        # Initialize database
        self.db = SupabaseIntegration(logger)
        if not self.db.client:
            raise ValueError("Failed to initialize Supabase client")
        
        # Initialize Dhan client
        try:
            client_id = os.getenv('DHAN_CLIENT_ID', '1100526168')
            access_token = os.getenv('DHAN_ACCESS_TOKEN')
            
            if not access_token:
                raise ValueError("DHAN_ACCESS_TOKEN not found in environment")
            
            self.dhan = dhanhq(client_id, access_token)
            logger.info("Price updater initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize: {e}")
            raise
    
    def get_trades_with_zero_price(self):
        """Fetch all trades with price=0"""
        try:
            logger.info("Fetching trades with zero price...")
            
            response = self.db.client.table('trades').select(
                'id, order_id, security_id, symbol, type, strike_price, quantity, action, timestamp'
            ).eq('price', 0).eq('order_status', 'open').execute()
            
            if response.data:
                logger.info(f"Found {len(response.data)} trades with zero price")
                return response.data
            else:
                logger.info("No trades with zero price found")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching trades: {e}")
            return []
    
    def update_trade_price(self, trade_id, order_id, price):
        """Update price for a specific trade"""
        try:
            if price <= 0:
                logger.warning(f"Invalid price {price} for trade {trade_id}")
                return False
            
            result = self.db.client.table('trades').update({
                'price': price,
                'price_updated_at': datetime.now().isoformat(),
                'price_update_source': 'order_details_api'
            }).eq('id', trade_id).execute()
            
            if result.data:
                logger.info(f"✅ Updated trade {trade_id} (order {order_id}) with price {price}")
                return True
            else:
                logger.error(f"Failed to update trade {trade_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating trade {trade_id}: {e}")
            return False
    
    def get_order_details(self, order_id):
        """Fetch order details from Dhan API"""
        try:
            logger.info(f"Fetching order details for {order_id}")
            
            order_details = self.dhan.get_order_by_id(order_id)
            
            if order_details and order_details.get('status') == 'success':
                order_data = order_details.get('data', {})
                executed_price = order_data.get('average_price', 0) or order_data.get('price', 0)
                
                return {
                    'order_id': order_id,
                    'executed_price': executed_price,
                    'order_status': order_data.get('order_status', ''),
                    'filled_quantity': order_data.get('filled_quantity', 0)
                }
            else:
                logger.warning(f"Failed to fetch order details for {order_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching order details for {order_id}: {e}")
            return None
    
    def update_all_zero_prices(self):
        """Update all trades with zero prices"""
        trades = self.get_trades_with_zero_price()
        
        if not trades:
            logger.info("No trades to update")
            return
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Starting price update for {len(trades)} trades")
        logger.info(f"{'='*60}\n")
        
        updated_count = 0
        failed_count = 0
        
        for trade in trades:
            try:
                trade_id = trade['id']
                order_id = trade['order_id']
                symbol = trade['symbol']
                strike = trade.get('strike_price', 'N/A')
                option_type = trade.get('type', '')
                
                logger.info(f"Processing: {symbol} {strike} {option_type} (Order: {order_id})")
                
                # Fetch order details
                order_details = self.get_order_details(order_id)
                
                if order_details and order_details['executed_price'] > 0:
                    # Update the trade price
                    if self.update_trade_price(trade_id, order_id, order_details['executed_price']):
                        updated_count += 1
                    else:
                        failed_count += 1
                else:
                    logger.warning(f"Could not get price for order {order_id}")
                    failed_count += 1
                
                # Small delay to avoid rate limiting
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error processing trade {trade.get('id')}: {e}")
                failed_count += 1
        
        # Summary
        logger.info(f"\n{'='*60}")
        logger.info("UPDATE SUMMARY")
        logger.info(f"{'='*60}")
        logger.info(f"Total trades processed: {len(trades)}")
        logger.info(f"Successfully updated: {updated_count}")
        logger.info(f"Failed to update: {failed_count}")
        
    def update_trades_with_market_quotes(self):
        """
        Alternative method: Update trades using current market quotes
        This is a fallback when order details are not available
        """
        try:
            logger.info("\n📊 Fetching current market quotes as fallback...")
            
            # Import and use the market quote fetcher
            from market_quote_fetcher import MarketQuoteFetcher
            
            fetcher = MarketQuoteFetcher()
            quotes = fetcher.get_market_quotes()
            
            if not quotes:
                logger.error("Failed to fetch market quotes")
                return
            
            # Get trades with zero price
            trades = self.get_trades_with_zero_price()
            
            updated_count = 0
            for trade in trades:
                security_id = str(trade['security_id'])
                
                # Look for the security in the quotes
                for exchange, instruments in quotes.get('data', {}).items():
                    if security_id in instruments:
                        current_price = instruments[security_id].get('last_price', 0)
                        
                        if current_price > 0:
                            # Update with current market price
                            result = self.db.client.table('trades').update({
                                'price': current_price,
                                'price_updated_at': datetime.now().isoformat(),
                                'price_update_source': 'market_quote_fallback'
                            }).eq('id', trade['id']).execute()
                            
                            if result.data:
                                logger.info(f"✅ Updated trade {trade['id']} with market price {current_price}")
                                updated_count += 1
                        break
            
            logger.info(f"Updated {updated_count} trades with market quotes")
            
        except Exception as e:
            logger.error(f"Error updating with market quotes: {e}")

def main():
    """Main execution function"""
    try:
        updater = TradePriceUpdater()
        
        # First try to update using order details
        updater.update_all_zero_prices()
        
        # Check if any trades still have zero price
        remaining_zero_trades = updater.get_trades_with_zero_price()
        
        if remaining_zero_trades:
            logger.info(f"\n⚠️ {len(remaining_zero_trades)} trades still have zero price")
            logger.info("Note: Order details API only works for same-day orders")
            
            # Optionally update with current market quotes
            response = input("\nUpdate remaining trades with current market prices? (y/n): ")
            if response.lower() == 'y':
                updater.update_trades_with_market_quotes()
        else:
            logger.info("\n✅ All trades have been updated with prices!")
            
    except Exception as e:
        logger.error(f"Failed to run price updater: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()