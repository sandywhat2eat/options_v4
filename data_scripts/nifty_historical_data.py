#!/usr/bin/env python3
"""
NIFTY 50 Historical Data Fetcher
Fetches last 90 days of historical data for NIFTY 50 using Dhan API
Security ID: 13
"""

import os
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
from dhanhq import dhanhq

# Load environment variables
load_dotenv("/root/.env")

class NiftyHistoricalDataFetcher:
    def __init__(self):
        """Initialize with Dhan API client"""
        self.dhan_client_id = os.getenv('DHAN_CLIENT_ID')
        self.dhan_access_token = os.getenv('DHAN_ACCESS_TOKEN')
        
        if not all([self.dhan_client_id, self.dhan_access_token]):
            raise ValueError("Missing required Dhan credentials in .env file")
        
        # Initialize Dhan client
        self.dhan = dhanhq(self.dhan_client_id, self.dhan_access_token)
        
        # NIFTY 50 configuration
        self.nifty_config = {
            'security_id': 13,
            'symbol': 'NIFTY 50',
            'exchange_segment': 'IDX_I',  # Index segment
            'instrument_type': 'INDEX'
        }
        
        print("✅ NIFTY 50 Historical Data Fetcher initialized")
        print(f"📊 Target: {self.nifty_config['symbol']} (ID: {self.nifty_config['security_id']})")
    
    def get_historical_data(self, days: int = 90) -> Optional[List[Dict]]:
        """
        Fetch historical data for NIFTY 50 for the specified number of days
        
        Args:
            days: Number of days to fetch (default: 90)
            
        Returns:
            List of historical data records or None if failed
        """
        try:
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Format dates for Dhan API (YYYY-MM-DD)
            from_date = start_date.strftime('%Y-%m-%d')
            to_date = end_date.strftime('%Y-%m-%d')
            
            print(f"📅 Fetching NIFTY 50 historical data from {from_date} to {to_date}")
            print(f"🔍 Security ID: {self.nifty_config['security_id']}")
            print(f"📊 Exchange Segment: {self.nifty_config['exchange_segment']}")
            
            # Rate limiting
            time.sleep(1)
            
            # Fetch historical data using Dhan API
            # Using daily timeframe for 90 days of data
            response = self.dhan.historical_daily_data(
                security_id=self.nifty_config['security_id'],
                exchange_segment=self.nifty_config['exchange_segment'],
                instrument_type=self.nifty_config['instrument_type'],
                from_date=from_date,
                to_date=to_date,
                expiry_code=0  # 0 for non-derivatives
            )
            
            if response and 'data' in response:
                historical_data = response['data']
                print(f"✅ Successfully fetched data for NIFTY 50")
                
                # Process and format the data - Dhan returns arrays for each field
                processed_data = []
                
                # Extract arrays from response
                opens = historical_data.get('open', [])
                highs = historical_data.get('high', [])
                lows = historical_data.get('low', [])
                closes = historical_data.get('close', [])
                volumes = historical_data.get('volume', [])
                timestamps = historical_data.get('timestamp', [])
                
                # Ensure all arrays have the same length
                data_length = min(len(opens), len(highs), len(lows), len(closes), len(volumes), len(timestamps))
                print(f"📊 Processing {data_length} records for NIFTY 50")
                
                for i in range(data_length):
                    # Convert timestamp to readable date
                    try:
                        date_obj = datetime.fromtimestamp(timestamps[i])
                        date_str = date_obj.strftime('%Y-%m-%d')
                    except:
                        date_str = str(timestamps[i])
                    
                    processed_record = {
                        'symbol': self.nifty_config['symbol'],
                        'security_id': self.nifty_config['security_id'],
                        'date': date_str,
                        'open': float(opens[i]),
                        'high': float(highs[i]),
                        'low': float(lows[i]),
                        'close': float(closes[i]),
                        'volume': int(volumes[i]),
                        'exchange_segment': self.nifty_config['exchange_segment'],
                        'instrument_type': self.nifty_config['instrument_type'],
                        'fetched_at': datetime.now().isoformat()
                    }
                    processed_data.append(processed_record)
                
                return processed_data
            else:
                print(f"❌ No historical data received for NIFTY 50")
                print(f"Response: {response}")
                return None
                
        except Exception as e:
            print(f"❌ Error fetching NIFTY 50 historical data: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def save_to_json(self, data: List[Dict], filename: str = None) -> bool:
        """
        Save historical data to JSON file
        
        Args:
            data: List of historical data records
            filename: Optional custom filename
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not data:
                print("⚠️ No data to save")
                return False
            
            if not filename:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"/root/nifty_historical_data_{timestamp}.json"
            
            print(f"💾 Saving NIFTY 50 historical data to {filename}...")
            
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            print(f"✅ Successfully saved NIFTY 50 data to {filename}")
            return True
            
        except Exception as e:
            print(f"❌ Error saving NIFTY 50 data to JSON: {e}")
            return False
    
    def run_fetch_and_save(self, days: int = 90):
        """
        Main function to fetch and save NIFTY 50 historical data
        
        Args:
            days: Number of days to fetch (default: 90)
        """
        try:
            print("\n" + "=" * 60)
            print("📊 NIFTY 50 HISTORICAL DATA FETCHER")
            print("=" * 60)
            
            # Fetch historical data
            historical_data = self.get_historical_data(days)
            
            if not historical_data:
                print("❌ Failed to fetch historical data")
                return
            
            print(f"\n📈 Data Summary:")
            print(f"   • Symbol: {self.nifty_config['symbol']}")
            print(f"   • Security ID: {self.nifty_config['security_id']}")
            print(f"   • Records: {len(historical_data)}")
            print(f"   • Date Range: {historical_data[0]['date']} to {historical_data[-1]['date']}")
            print(f"   • Latest Close: ₹{historical_data[-1]['close']:,.2f}")
            
            # Save to JSON file
            file_success = self.save_to_json(historical_data)
            if not file_success:
                print("⚠️ File save failed, but continuing...")
            
            print("\n✅ NIFTY 50 historical data fetch completed!")
            
        except Exception as e:
            print(f"❌ Error in run_fetch_and_save: {e}")
            import traceback
            traceback.print_exc()

def main():
    """Main execution function"""
    try:
        fetcher = NiftyHistoricalDataFetcher()
        
        # Fetch last 90 days of NIFTY 50 data
        fetcher.run_fetch_and_save(days=90)
        
    except Exception as e:
        print(f"❌ Failed to initialize NIFTY 50 fetcher: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
