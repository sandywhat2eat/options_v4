#!/usr/bin/env python3
"""
Test script to fetch order details from Dhan API
Testing with order IDs from the execution log
"""

import os
from dotenv import load_dotenv
from dhanhq import dhanhq
import json

# Load environment variables
load_dotenv()

def test_order_details():
    """Test fetching order details for recent orders"""
    try:
        # Initialize Dhan client
        client_id = os.getenv('DHAN_CLIENT_ID', '1100526168')
        access_token = os.getenv('DHAN_ACCESS_TOKEN')
        
        if not access_token:
            print("❌ DHAN_ACCESS_TOKEN not found in environment")
            return
        
        dhan = dhanhq(client_id, access_token)
        print("✅ Dhan client initialized")
        
        # Test order IDs from the log
        test_order_ids = [
            '12250625310205',  # First order
            '92250625410305',  # Second order  
            '72250625315005'   # Third order
        ]
        
        for order_id in test_order_ids:
            print(f"\n{'='*60}")
            print(f"Testing order ID: {order_id}")
            print(f"{'='*60}")
            
            try:
                # Test the get_order_by_id method
                response = dhan.get_order_by_id(order_id)
                
                print(f"Response type: {type(response)}")
                print(f"Response: {json.dumps(response, indent=2, default=str)}")
                
                # Try to extract price information
                if isinstance(response, list) and len(response) > 0:
                    order_data = response[0]
                    print(f"\nFirst item in list: {json.dumps(order_data, indent=2, default=str)}")
                    
                    # Look for price fields
                    price_fields = ['average_price', 'price', 'executed_price', 'traded_price']
                    for field in price_fields:
                        if field in order_data:
                            print(f"Found {field}: {order_data[field]}")
                
                elif isinstance(response, dict):
                    if 'data' in response:
                        order_data = response['data']
                        print(f"\nOrder data: {json.dumps(order_data, indent=2, default=str)}")
                    
                    # Look for price fields in main response
                    price_fields = ['average_price', 'price', 'executed_price', 'traded_price']
                    for field in price_fields:
                        if field in response:
                            print(f"Found {field}: {response[field]}")
                
            except Exception as e:
                print(f"❌ Error fetching order {order_id}: {e}")
                import traceback
                traceback.print_exc()
        
        # Also test get_orders method to see all orders
        print(f"\n{'='*60}")
        print("Testing get_orders() method for comparison")
        print(f"{'='*60}")
        
        try:
            all_orders = dhan.get_orders()
            print(f"All orders type: {type(all_orders)}")
            print(f"All orders: {json.dumps(all_orders, indent=2, default=str)}")
            
            # Look for our test order IDs in the response
            if isinstance(all_orders, dict) and 'data' in all_orders:
                orders_list = all_orders['data']
                for order in orders_list:
                    if str(order.get('orderId', '')) in test_order_ids:
                        print(f"\nFound test order in all orders:")
                        print(json.dumps(order, indent=2, default=str))
            
        except Exception as e:
            print(f"❌ Error fetching all orders: {e}")
            
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_order_details()