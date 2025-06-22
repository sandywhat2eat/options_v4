#!/usr/bin/env python3
"""
All Indices Historical Data Fetcher
Fetches last 90 days of historical data for all specified indices using Dhan API
Includes: NIFTY 50, BANK NIFTY, NIFTY FIN SERVICE, NIFTY IT, NIFTY MIDCAP 50, and India VIX
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

class AllIndicesHistoricalDataFetcher:
    def __init__(self):
        """Initialize with Dhan API client"""
        self.dhan_client_id = os.getenv('DHAN_CLIENT_ID')
        self.dhan_access_token = os.getenv('DHAN_ACCESS_TOKEN')
        
        if not all([self.dhan_client_id, self.dhan_access_token]):
            raise ValueError("Missing required Dhan credentials in .env file")
        
        # Initialize Dhan client
        self.dhan = dhanhq(self.dhan_client_id, self.dhan_access_token)
        
        # All indices configuration
        self.indices = {
            'NIFTY 50': {'security_id': 13, 'symbol': 'NIFTY 50'},
            'BANK NIFTY': {'security_id': 25, 'symbol': 'BANK NIFTY'},
            'NIFTY FIN SERVICE': {'security_id': 27, 'symbol': 'NIFTY FIN SERVICE'},
            'NIFTY IT': {'security_id': 29, 'symbol': 'NIFTY IT'},
            'NIFTY MIDCAP 50': {'security_id': 38, 'symbol': 'NIFTY MIDCAP 50'},
            'INDIA VIX': {'security_id': 21, 'symbol': 'INDIA VIX'}
        }
        
        # Common configuration for all indices
        self.common_config = {
            'exchange_segment': 'IDX_I',  # Index segment
            'instrument_type': 'INDEX'
        }
        
        print("✅ All Indices Historical Data Fetcher initialized")
        print(f"📊 Target Indices: {list(self.indices.keys())}")
    
    def get_historical_data_for_index(self, index_name: str, days: int = 90) -> Optional[List[Dict]]:
        """
        Fetch historical data for a specific index for the specified number of days
        
        Args:
            index_name: Name of the index
            days: Number of days to fetch (default: 90)
            
        Returns:
            List of historical data records or None if failed
        """
        try:
            if index_name not in self.indices:
                print(f"❌ Unknown index: {index_name}")
                return None
            
            index_config = self.indices[index_name]
            
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Format dates for Dhan API (YYYY-MM-DD)
            from_date = start_date.strftime('%Y-%m-%d')
            to_date = end_date.strftime('%Y-%m-%d')
            
            print(f"📅 Fetching {index_name} historical data from {from_date} to {to_date}")
            print(f"🔍 Security ID: {index_config['security_id']}")
            
            # Rate limiting
            time.sleep(2)  # Increased delay between requests
            
            # Fetch historical data using Dhan API
            response = self.dhan.historical_daily_data(
                security_id=index_config['security_id'],
                exchange_segment=self.common_config['exchange_segment'],
                instrument_type=self.common_config['instrument_type'],
                from_date=from_date,
                to_date=to_date,
                expiry_code=0  # 0 for non-derivatives
            )
            
            if response and 'data' in response:
                historical_data = response['data']
                print(f"✅ Successfully fetched data for {index_name}")
                
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
                print(f"📊 Processing {data_length} records for {index_name}")
                
                for i in range(data_length):
                    # Convert timestamp to readable date
                    try:
                        date_obj = datetime.fromtimestamp(timestamps[i])
                        date_str = date_obj.strftime('%Y-%m-%d')
                    except:
                        date_str = str(timestamps[i])
                    
                    processed_record = {
                        'symbol': index_config['symbol'],
                        'security_id': index_config['security_id'],
                        'date': date_str,
                        'open': float(opens[i]),
                        'high': float(highs[i]),
                        'low': float(lows[i]),
                        'close': float(closes[i]),
                        'volume': int(volumes[i]),
                        'exchange_segment': self.common_config['exchange_segment'],
                        'instrument_type': self.common_config['instrument_type'],
                        'fetched_at': datetime.now().isoformat()
                    }
                    processed_data.append(processed_record)
                
                return processed_data
            else:
                print(f"❌ No historical data received for {index_name}")
                print(f"Response: {response}")
                return None
                
        except Exception as e:
            print(f"❌ Error fetching {index_name} historical data: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def save_to_json(self, index_name: str, data: List[Dict], filename: str = None) -> bool:
        """
        Save historical data to JSON file
        
        Args:
            index_name: Name of the index
            data: List of historical data records
            filename: Optional custom filename
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not data:
                print(f"⚠️ No data to save for {index_name}")
                return False
            
            if not filename:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                safe_name = index_name.lower().replace(' ', '_').replace('-', '_')
                filename = f"/root/{safe_name}_historical_data_{timestamp}.json"
            
            print(f"💾 Saving {index_name} historical data to {filename}...")
            
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            print(f"✅ Successfully saved {index_name} data to {filename}")
            return True
            
        except Exception as e:
            print(f"❌ Error saving {index_name} data to JSON: {e}")
            return False
    
    def run_fetch_all_indices(self, days: int = 90):
        """
        Main function to fetch and save historical data for all indices
        
        Args:
            days: Number of days to fetch (default: 90)
        """
        try:
            print("\n" + "=" * 70)
            print("📊 ALL INDICES HISTORICAL DATA FETCHER")
            print("=" * 70)
            
            successful_indices = 0
            failed_indices = []
            all_data = {}
            
            # Process each index
            for index_name in self.indices.keys():
                print(f"\n{'='*20} {index_name} {'='*20}")
                
                # Fetch historical data
                historical_data = self.get_historical_data_for_index(index_name, days)
                
                if historical_data:
                    all_data[index_name] = historical_data
                    
                    print(f"\n📈 {index_name} Data Summary:")
                    print(f"   • Security ID: {self.indices[index_name]['security_id']}")
                    print(f"   • Records: {len(historical_data)}")
                    print(f"   • Date Range: {historical_data[0]['date']} to {historical_data[-1]['date']}")
                    
                    # Format close price based on index type
                    if 'VIX' in index_name:
                        print(f"   • Latest Close: {historical_data[-1]['close']:.2f}")
                    else:
                        print(f"   • Latest Close: ₹{historical_data[-1]['close']:,.2f}")
                    
                    # Save to JSON file
                    file_success = self.save_to_json(index_name, historical_data)
                    if not file_success:
                        print(f"⚠️ File save failed for {index_name}")
                    
                    successful_indices += 1
                    print(f"✅ {index_name} processing completed")
                else:
                    failed_indices.append(index_name)
                    print(f"❌ {index_name} processing failed")
                
                # Rate limiting between indices
                time.sleep(3)
            
            # Save combined data
            if all_data:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                combined_filename = f"/root/all_indices_historical_data_{timestamp}.json"
                
                try:
                    with open(combined_filename, 'w') as f:
                        json.dump(all_data, f, indent=2, default=str)
                    print(f"\n💾 Combined data saved to {combined_filename}")
                except Exception as e:
                    print(f"⚠️ Failed to save combined data: {e}")
            
            # Final summary
            print("\n" + "=" * 70)
            print("📊 ALL INDICES HISTORICAL DATA FETCH COMPLETE")
            print("=" * 70)
            
            print(f"✅ Successful: {successful_indices}/{len(self.indices)} indices")
            if failed_indices:
                print(f"❌ Failed: {', '.join(failed_indices)}")
            print(f"📅 Data Period: Last {days} days")
            print(f"⏰ Completed at: {datetime.now().isoformat()}")
            
            if successful_indices > 0:
                print(f"\n🎉 SUCCESS! {successful_indices} indices processed successfully!")
            else:
                print("\n❌ FAILED! No indices were successfully processed.")
            
        except Exception as e:
            print(f"❌ Error in run_fetch_all_indices: {e}")
            import traceback
            traceback.print_exc()

def main():
    """Main execution function"""
    try:
        fetcher = AllIndicesHistoricalDataFetcher()
        
        # Fetch last 90 days of data for all indices
        fetcher.run_fetch_all_indices(days=90)
        
    except Exception as e:
        print(f"❌ Failed to initialize All Indices fetcher: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
