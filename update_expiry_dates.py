#!/usr/bin/env python3
"""
Update existing trades with expiry dates from Dhan API
"""

import os
import sys
import logging
from dotenv import load_dotenv
from dhanhq import dhanhq
from datetime import datetime
import time

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.supabase_integration import SupabaseIntegration

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def update_trade_expiry_dates():
    """Update expiry dates for all open trades"""
    try:
        # Initialize database
        db = SupabaseIntegration(logger)
        if not db.client:
            logger.error("Failed to initialize database connection")
            return
        
        # Initialize Dhan client
        client_id = os.getenv('DHAN_CLIENT_ID', '1100526168')
        access_token = os.getenv('DHAN_ACCESS_TOKEN')
        
        if not access_token:
            logger.error("DHAN_ACCESS_TOKEN not found in environment")
            return
        
        dhan = dhanhq(client_id, access_token)
        logger.info("✅ Dhan client initialized")
        
        # Fetch all open trades with NULL expiry_date
        logger.info("Fetching open trades without expiry dates...")
        result = db.client.table('trades').select(
            'new_id, order_id, symbol, strike_price, type, expiry_date'
        ).eq('order_status', 'open').is_('expiry_date', 'null').execute()
        
        if not result.data:
            logger.info("No open trades found with missing expiry dates")
            return
        
        trades = result.data
        logger.info(f"Found {len(trades)} trades to update")
        
        # Process each trade
        updated_count = 0
        failed_count = 0
        
        for trade in trades:
            order_id = trade.get('order_id')
            if not order_id:
                logger.warning(f"Trade {trade['new_id']} has no order_id, skipping")
                continue
            
            logger.info(f"\nProcessing order {order_id} ({trade['symbol']} {trade['strike_price']} {trade['type']})")
            
            try:
                # Fetch order details from Dhan
                order_response = dhan.get_order_by_id(order_id)
                
                if order_response and order_response.get('status') == 'success':
                    order_data_list = order_response.get('data', [])
                    
                    if order_data_list and len(order_data_list) > 0:
                        order_data = order_data_list[0]
                        expiry_date = order_data.get('drvExpiryDate')
                        
                        if expiry_date:
                            # Update the trade with expiry date
                            update_result = db.client.table('trades').update({
                                'expiry_date': expiry_date
                            }).eq('new_id', trade['new_id']).execute()
                            
                            if update_result.data:
                                logger.info(f"✅ Updated trade {trade['new_id']} with expiry date: {expiry_date}")
                                updated_count += 1
                                
                                # Calculate days to expiry
                                expiry_dt = datetime.strptime(expiry_date, '%Y-%m-%d')
                                days_to_expiry = (expiry_dt - datetime.now()).days
                                
                                if days_to_expiry <= 1:
                                    logger.warning(f"⚠️  URGENT: {trade['symbol']} expires in {days_to_expiry} days!")
                            else:
                                logger.error(f"Failed to update trade {trade['new_id']}")
                                failed_count += 1
                        else:
                            logger.warning(f"No expiry date found in order response for {order_id}")
                            failed_count += 1
                    else:
                        logger.warning(f"No order data found for {order_id}")
                        failed_count += 1
                else:
                    logger.error(f"Failed to fetch order details for {order_id}: {order_response}")
                    failed_count += 1
                
                # Add small delay to avoid rate limiting
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error processing order {order_id}: {e}")
                failed_count += 1
                continue
        
        # Summary
        logger.info(f"\n{'='*60}")
        logger.info("UPDATE SUMMARY")
        logger.info(f"{'='*60}")
        logger.info(f"Total trades processed: {len(trades)}")
        logger.info(f"Successfully updated: {updated_count}")
        logger.info(f"Failed: {failed_count}")
        
        # Check for positions expiring soon
        logger.info("\nChecking for near-expiry positions...")
        near_expiry_result = db.client.table('trades').select(
            'symbol, strike_price, type, expiry_date'
        ).eq('order_status', 'open').not_.is_('expiry_date', 'null').execute()
        
        if near_expiry_result.data:
            urgent_positions = []
            for trade in near_expiry_result.data:
                if trade.get('expiry_date'):
                    expiry_dt = datetime.strptime(trade['expiry_date'], '%Y-%m-%d')
                    days_to_expiry = (expiry_dt - datetime.now()).days
                    
                    if days_to_expiry <= 1:
                        urgent_positions.append({
                            'symbol': trade['symbol'],
                            'strike': trade['strike_price'],
                            'type': trade['type'],
                            'expiry': trade['expiry_date'],
                            'days_remaining': days_to_expiry
                        })
            
            if urgent_positions:
                logger.warning(f"\n🚨 URGENT: {len(urgent_positions)} positions expiring soon!")
                for pos in urgent_positions:
                    logger.warning(f"   - {pos['symbol']} {pos['strike']} {pos['type']} expires {pos['expiry']} ({pos['days_remaining']} days)")
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    update_trade_expiry_dates()