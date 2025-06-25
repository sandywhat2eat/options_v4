#!/usr/bin/env python3
"""
Update recent trades with correct prices
Updates the specific trades from the test execution
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.supabase_integration import SupabaseIntegration

# Load environment variables
load_dotenv()

def update_recent_trades():
    """Update the recent test trades with correct prices"""
    
    # Known prices from the test execution
    trade_updates = [
        {'order_id': '12250625310205', 'price': 382.5},   # BUY 13750 CE
        {'order_id': '92250625410305', 'price': 161.5},   # SELL 14000 CE  
        {'order_id': '72250625315005', 'price': 69.85}    # BUY 14250 CE
    ]
    
    try:
        # Initialize database
        db = SupabaseIntegration()
        if not db.client:
            print("❌ Failed to initialize Supabase client")
            return
        
        print("✅ Database connected")
        print(f"\n{'='*60}")
        print("Updating recent trade prices")
        print(f"{'='*60}")
        
        updated_count = 0
        
        for trade_update in trade_updates:
            order_id = trade_update['order_id']
            price = trade_update['price']
            
            try:
                # Update the trade
                result = db.client.table('trades').update({
                    'price': price
                }).eq('order_id', order_id).execute()
                
                if result.data:
                    print(f"✅ Updated order {order_id} with price ₹{price}")
                    updated_count += 1
                else:
                    print(f"❌ Failed to update order {order_id}")
                    
            except Exception as e:
                print(f"❌ Error updating order {order_id}: {e}")
        
        print(f"\n{'='*60}")
        print(f"Update Summary: {updated_count}/{len(trade_updates)} trades updated")
        print(f"{'='*60}")
        
        # Verify the updates
        print("\nVerifying updates...")
        for trade_update in trade_updates:
            order_id = trade_update['order_id']
            
            result = db.client.table('trades').select(
                'order_id, price, symbol, type, strike_price, action'
            ).eq('order_id', order_id).execute()
            
            if result.data:
                trade = result.data[0]
                print(f"Order {order_id}: {trade['symbol']} {trade['strike_price']} {trade['type']} "
                      f"({trade['action']}) - Price: ₹{trade['price']}")
            else:
                print(f"❌ Could not find order {order_id}")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    update_recent_trades()