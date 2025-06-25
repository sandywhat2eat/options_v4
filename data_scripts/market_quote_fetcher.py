#!/usr/bin/env python3
"""
Market Quote Fetcher for Multiple Instruments
Fetches real-time market quotes for multiple instruments using Dhan API
"""

import os
import json
import time
from datetime import datetime
from typing import Dict, Optional
from dotenv import load_dotenv
from dhanhq import dhanhq

# Import Supabase integration
import sys
sys.path.append('/Users/jaykrish/Documents/digitalocean/cronjobs/options_v4')
from database.supabase_integration import SupabaseIntegration

# Load environment variables
load_dotenv()

class MarketQuoteFetcher:
    def __init__(self):
        """Initialize with Dhan API client and Supabase integration"""
        self.dhan_client_id = os.getenv('DHAN_CLIENT_ID')
        self.dhan_access_token = os.getenv('DHAN_ACCESS_TOKEN')
        
        if not all([self.dhan_client_id, self.dhan_access_token]):
            raise ValueError("Missing required Dhan credentials in .env file")
        
        # Initialize Dhan client
        self.dhan = dhanhq(self.dhan_client_id, self.dhan_access_token)
        
        # Initialize Supabase integration
        self.supabase_integration = SupabaseIntegration()
        if not self.supabase_integration.client:
            raise ValueError("Failed to initialize Supabase client")
        
        # Initialize empty instruments - will be populated from database
        self.instruments = {"NSE_EQ": [], "NSE_FNO": []}
        
        print("✅ Market Quote Fetcher initialized")
        print("🔗 Supabase integration ready")
        
        # Fetch instruments from database
        self._fetch_instruments_from_database()
    
    def _fetch_instruments_from_database(self):
        """
        Fetch security IDs from Supabase trades table where:
        - order_status = 'open'
        - strategy = 'Butterfly Spread'
        """
        try:
            print("🔍 Fetching open Butterfly Spread trades from database...")
            
            # Query trades table for open Butterfly Spread positions
            response = self.supabase_integration.client.table('trades').select(
                'security_id, symbol, type, strategy, action, strike_price, order_status'
            ).eq(
                'order_status', 'open'
            ).eq(
                'strategy', 'Butterfly Spread'
            ).execute()
            
            if not response.data:
                print("⚠️ No open Butterfly Spread trades found in database")
                print("📊 Using fallback instruments for demonstration")
                # Fallback to demo instruments
                self.instruments = {
                    "NSE_EQ": [11536],
                    "NSE_FNO": [49081, 49082]
                }
                return
            
            # Group security IDs by exchange
            nse_eq_ids = []
            nse_fno_ids = []
            
            trade_count = len(response.data)
            print(f"📊 Found {trade_count} open Butterfly Spread trades")
            
            for trade in response.data:
                security_id = trade.get('security_id')
                symbol = trade.get('symbol', f'ID_{security_id}')
                option_type = trade.get('type', 'CE')  # CE or PE
                strike_price = trade.get('strike_price', 0)
                action = trade.get('action', 'BUY')
                
                # Determine exchange (options are typically NSE_FNO)
                exchange = 'NSE_FNO'  # Default for options
                
                # Create detailed instrument info
                instrument_info = f"{symbol} {strike_price} {option_type}"
                
                if security_id:
                    if exchange == 'NSE_EQ':
                        nse_eq_ids.append(security_id)
                    else:
                        nse_fno_ids.append(security_id)
                    
                    print(f"  • {instrument_info} ({security_id}) - {action} position")
            
            # Remove duplicates and update instruments
            self.instruments = {
                "NSE_EQ": list(set(nse_eq_ids)),
                "NSE_FNO": list(set(nse_fno_ids))
            }
            
            total_instruments = len(self.instruments["NSE_EQ"]) + len(self.instruments["NSE_FNO"])
            print(f"✅ Configured {total_instruments} unique instruments from open trades")
            print(f"   NSE_EQ: {len(self.instruments['NSE_EQ'])} instruments")
            print(f"   NSE_FNO: {len(self.instruments['NSE_FNO'])} instruments")
            
        except Exception as e:
            print(f"❌ Error fetching instruments from database: {e}")
            print("📊 Using fallback instruments for demonstration")
            # Fallback to demo instruments
            self.instruments = {
                "NSE_EQ": [11536],
                "NSE_FNO": [49081, 49082]
            }
    
    def get_market_quotes(self) -> Optional[Dict]:
        """
        Fetch market quotes for all configured instruments
        
        Returns:
            Dictionary containing market quotes for all instruments or None if failed
        """
        try:
            print(f"📊 Fetching market quotes for instruments...")
            print(f"🔍 NSE_EQ: {self.instruments['NSE_EQ']}")
            print(f"🔍 NSE_FNO: {self.instruments['NSE_FNO']}")
            
            all_quotes = {}
            
            # Fetch quotes for all instruments in one call
            print(f"\n📈 Fetching market quotes for all instruments...")
            time.sleep(1)  # Rate limiting
            
            try:
                response = self.dhan.quote_data(securities=self.instruments)
                
                if response and 'data' in response:
                    all_quotes = response['data']
                    
                    # Count instruments per exchange
                    for exchange, quotes in all_quotes.items():
                        if isinstance(quotes, list):
                            print(f"✅ Successfully fetched {len(quotes)} {exchange} quotes")
                        else:
                            print(f"✅ Successfully fetched {exchange} quotes")
                else:
                    print(f"❌ No market data received")
                    print(f"Response: {response}")
                    all_quotes = {'NSE_EQ': [], 'NSE_FNO': []}
                    
            except Exception as e:
                print(f"❌ Error fetching market quotes: {e}")
                import traceback
                traceback.print_exc()
                all_quotes = {'NSE_EQ': [], 'NSE_FNO': []}
            
            # Add metadata
            all_quotes['metadata'] = {
                'fetched_at': datetime.now().isoformat(),
                'total_instruments': sum(len(instruments) for instruments in self.instruments.values()),
                'exchanges': list(self.instruments.keys())
            }
            
            return all_quotes
            
        except Exception as e:
            print(f"❌ Error fetching market quotes: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def format_quote_data(self, quotes: Dict) -> Dict:
        """
        Format and enhance quote data for better readability
        
        Args:
            quotes: Raw quotes data from API
            
        Returns:
            Formatted quotes data
        """
        try:
            formatted_quotes = {
                'metadata': quotes.get('metadata', {}),
                'quotes': {}
            }
            
            # Handle the nested structure from Dhan API
            if 'data' in quotes:
                api_data = quotes['data']
                for exchange, instruments in api_data.items():
                    if exchange == 'metadata':
                        continue
                        
                    formatted_quotes['quotes'][exchange] = []
                    
                    # Each exchange contains a dict of security_id -> quote_data
                    for security_id, quote_data in instruments.items():
                        ohlc = quote_data.get('ohlc', {})
                        
                        formatted_quote = {
                            'security_id': security_id,
                            'last_price': quote_data.get('last_price'),
                            'net_change': quote_data.get('net_change'),
                            'change_percent': round((quote_data.get('net_change', 0) / ohlc.get('close', 1)) * 100, 2) if ohlc.get('close') else 0,
                            'volume': quote_data.get('volume'),
                            'open': ohlc.get('open'),
                            'high': ohlc.get('high'),
                            'low': ohlc.get('low'),
                            'close': ohlc.get('close'),
                            'buy_quantity': quote_data.get('buy_quantity'),
                            'sell_quantity': quote_data.get('sell_quantity'),
                            'last_trade_time': quote_data.get('last_trade_time'),
                            'oi': quote_data.get('oi'),
                            'oi_day_high': quote_data.get('oi_day_high'),
                            'oi_day_low': quote_data.get('oi_day_low'),
                            'average_price': quote_data.get('average_price'),
                            'upper_circuit_limit': quote_data.get('upper_circuit_limit'),
                            'lower_circuit_limit': quote_data.get('lower_circuit_limit'),
                            'raw_data': quote_data
                        }
                        formatted_quotes['quotes'][exchange].append(formatted_quote)
            
            return formatted_quotes
            
        except Exception as e:
            print(f"❌ Error formatting quote data: {e}")
            import traceback
            traceback.print_exc()
            return quotes
    
    def print_quotes_summary(self, quotes: Dict):
        """
        Print a formatted summary of the market quotes
        
        Args:
            quotes: Formatted quotes data
        """
        try:
            print("\n" + "=" * 80)
            print("📊 MARKET QUOTES SUMMARY")
            print("=" * 80)
            
            if 'metadata' in quotes:
                metadata = quotes['metadata']
                print(f"🕒 Fetched at: {metadata.get('fetched_at', 'Unknown')}")
                print(f"📈 Total instruments: {metadata.get('total_instruments', 0)}")
                print(f"🏛️ Exchanges: {', '.join(metadata.get('exchanges', []))}")
            
            if 'quotes' in quotes:
                for exchange, quote_list in quotes['quotes'].items():
                    print(f"\n📊 {exchange} ({len(quote_list)} instruments):")
                    print("-" * 80)
                    
                    for quote in quote_list:
                        security_id = quote.get('security_id', 'Unknown')
                        last_price = quote.get('last_price', 0)
                        change = quote.get('net_change', 0)
                        change_percent = quote.get('change_percent', 0)
                        volume = quote.get('volume', 0)
                        
                        # Format change display
                        change_sign = "+" if change >= 0 else ""
                        change_color = "🟢" if change >= 0 else "🔴"
                        
                        print(f"  • Security ID: {security_id}")
                        print(f"    LTP: ₹{last_price:<10.2f} | Change: {change_color} {change_sign}{change:<8.2f} ({change_sign}{change_percent:<6.2f}%)")
                        print(f"    Volume: {volume:,} | O: {quote.get('open', 0)} | H: {quote.get('high', 0)} | L: {quote.get('low', 0)} | C: {quote.get('close', 0)}")
                        
                        # Show additional data for derivatives (FNO)
                        if exchange == 'NSE_FNO':
                            oi = quote.get('oi', 0)
                            print(f"    OI: {oi:,} | Buy Qty: {quote.get('buy_quantity', 0):,} | Sell Qty: {quote.get('sell_quantity', 0):,}")
                        
                        print(f"    Last Trade: {quote.get('last_trade_time', 'N/A')}")
                        print()
            
            print("=" * 80)
            
        except Exception as e:
            print(f"❌ Error printing quotes summary: {e}")
            import traceback
            traceback.print_exc()
    
    def save_to_json(self, data: Dict, filename: str = None) -> bool:
        """
        Save market quotes to JSON file
        
        Args:
            data: Market quotes data
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
                filename = f"/Users/jaykrish/Documents/digitalocean/cronjobs/options_v4/data_scripts/market_quotes_{timestamp}.json"
            
            print(f"💾 Saving market quotes to {filename}...")
            
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            print(f"✅ Successfully saved market quotes to {filename}")
            return True
            
        except Exception as e:
            print(f"❌ Error saving market quotes to JSON: {e}")
            return False
    
    def run_fetch_and_display(self, save_to_file: bool = True):
        """
        Main function to fetch and display market quotes
        
        Args:
            save_to_file: Whether to save quotes to JSON file (default: True)
        """
        try:
            print("\n" + "=" * 80)
            print("📊 MARKET QUOTE FETCHER")
            print("=" * 80)
            
            # Fetch market quotes
            raw_quotes = self.get_market_quotes()
            
            if not raw_quotes:
                print("❌ Failed to fetch market quotes")
                return
            
            # Format quotes data
            formatted_quotes = self.format_quote_data(raw_quotes)
            
            # Print summary
            self.print_quotes_summary(formatted_quotes)
            
            # Save to file if requested
            if save_to_file:
                file_success = self.save_to_json(formatted_quotes)
                if not file_success:
                    print("⚠️ File save failed, but continuing...")
            
            print("\n✅ Market quote fetch completed!")
            return formatted_quotes
            
        except Exception as e:
            print(f"❌ Error in run_fetch_and_display: {e}")
            import traceback
            traceback.print_exc()
            return None

def main():
    """Main execution function"""
    try:
        fetcher = MarketQuoteFetcher()
        
        # Fetch and display market quotes
        quotes = fetcher.run_fetch_and_display(save_to_file=True)
        
        if quotes:
            print("\n🎉 Market quotes fetched successfully!")
        else:
            print("\n❌ Failed to fetch market quotes")
        
    except Exception as e:
        print(f"❌ Failed to initialize market quote fetcher: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()