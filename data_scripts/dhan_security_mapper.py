#!/usr/bin/env python3
"""
Dhan Security ID Mapper
Maps Options V4 strategy details to Dhan security IDs using Dhan API
"""

import os
import sys
import logging
from datetime import datetime
from dotenv import load_dotenv
from dhanhq import dhanhq
import pandas as pd

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv('/Users/jaykrish/Documents/digitalocean/.env')

from database import SupabaseIntegration

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DhanSecurityMapper:
    def __init__(self):
        """Initialize with Dhan API and database connections"""
        # Initialize DHAN client
        try:
            self.dhan = dhanhq(
                client_id="1100526168", 
                access_token="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzM2OTA5Mzg4LCJ0b2tlbkNvbnN1bWVyVHlwZSI6IlNFTEYiLCJ3ZWJob29rVXJsIjoiIiwiZGhhbkNsaWVudElkIjoiMTEwMDUyNjE2OCJ9.OOrHsLk-49l-mMxaFEW0gs16TQ8OIqRB50JSaVTMDVk2lq9CHVER-NWWPVEnBFWN4wHLaS3dNimTRTlGPd2n3w"
            )
            logger.info("DHAN client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize DHAN client: {str(e)}")
            raise
        
        self.db = SupabaseIntegration(logger)
        if not self.db.client:
            raise Exception("Failed to connect to Supabase")
        
        # Cache for security mappings
        self.security_cache = {}
    
    def download_scrip_master(self):
        """Download latest scrip master from Dhan"""
        try:
            logger.info("Downloading scrip master from Dhan API...")
            
            # Download all segments scrip master
            scrip_master = self.dhan.download_scrip_master()
            
            # Focus on NSE F&O segment
            if 'NSE_FNO' in scrip_master:
                fno_scrips = scrip_master['NSE_FNO']
                logger.info(f"Downloaded {len(fno_scrips)} F&O instruments")
                return fno_scrips
            else:
                logger.error("NSE_FNO segment not found in scrip master")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"Error downloading scrip master: {e}")
            return pd.DataFrame()
    
    def find_security_id(self, symbol, option_type, strike_price, expiry_date=None):
        """Find security ID for given option details"""
        # Check cache first
        cache_key = f"{symbol}_{option_type}_{strike_price}_{expiry_date}"
        if cache_key in self.security_cache:
            return self.security_cache[cache_key]
        
        try:
            # Download fresh scrip master if not already done
            if not hasattr(self, 'fno_scrips') or self.fno_scrips.empty:
                self.fno_scrips = self.download_scrip_master()
            
            if self.fno_scrips.empty:
                logger.error("No F&O scrips available")
                return None, None
            
            # Filter for the specific option
            filtered = self.fno_scrips[
                (self.fno_scrips['SEM_TRADING_SYMBOL'].str.contains(symbol, case=False)) &
                (self.fno_scrips['SEM_OPTION_TYPE'] == option_type) &
                (self.fno_scrips['SEM_STRIKE_PRICE'] == strike_price)
            ]
            
            # Further filter by expiry if provided
            if expiry_date and not filtered.empty:
                # Convert expiry_date to match format
                if isinstance(expiry_date, str):
                    exp_date = pd.to_datetime(expiry_date).date()
                else:
                    exp_date = expiry_date
                
                filtered = filtered[
                    pd.to_datetime(filtered['SEM_EXPIRY_DATE']).dt.date == exp_date
                ]
            
            if not filtered.empty:
                # Get the first match (or nearest expiry)
                result = filtered.iloc[0]
                security_id = result['SEM_SMST_SECURITY_ID']
                lot_size = result['SEM_LOT_UNITS']
                
                # Cache the result
                self.security_cache[cache_key] = (security_id, lot_size)
                
                logger.info(f"Found security ID {security_id} for {symbol} {strike_price} {option_type}")
                return security_id, lot_size
            else:
                logger.warning(f"No match found for {symbol} {strike_price} {option_type}")
                return None, None
                
        except Exception as e:
            logger.error(f"Error finding security ID: {e}")
            return None, None
    
    def map_strategy_securities(self, strategy_id):
        """Map all legs of a strategy to security IDs"""
        try:
            # Fetch strategy with details
            result = self.db.client.table('strategies').select(
                '*, strategy_details(*), strategy_parameters(*)'
            ).eq('id', strategy_id).execute()
            
            if not result.data:
                logger.error(f"Strategy {strategy_id} not found")
                return []
            
            strategy = result.data[0]
            symbol = strategy['stock_name']
            
            # Get expiry from parameters
            expiry_date = None
            if strategy.get('strategy_parameters') and len(strategy['strategy_parameters']) > 0:
                expiry_date = strategy['strategy_parameters'][0].get('expiry_date')
            
            mappings = []
            
            for leg in strategy.get('strategy_details', []):
                security_id, lot_size = self.find_security_id(
                    symbol,
                    leg['option_type'],
                    leg['strike_price'],
                    expiry_date
                )
                
                mappings.append({
                    'leg_id': leg['id'],
                    'symbol': symbol,
                    'option_type': leg['option_type'],
                    'strike_price': leg['strike_price'],
                    'security_id': security_id,
                    'lot_size': lot_size,
                    'setup_type': leg['setup_type'],
                    'lots': leg.get('lots', 1)
                })
            
            return mappings
            
        except Exception as e:
            logger.error(f"Error mapping strategy securities: {e}")
            return []
    
    def store_security_mappings(self, mappings):
        """Store security mappings in database for future use"""
        try:
            # Create a security_mappings table if needed
            for mapping in mappings:
                if mapping['security_id']:
                    data = {
                        'symbol': mapping['symbol'],
                        'option_type': mapping['option_type'],
                        'strike_price': mapping['strike_price'],
                        'security_id': mapping['security_id'],
                        'lot_size': mapping['lot_size'],
                        'last_updated': datetime.now().isoformat()
                    }
                    
                    # Upsert the mapping
                    self.db.client.table('security_mappings').upsert(
                        data,
                        on_conflict='symbol,option_type,strike_price'
                    ).execute()
                    
            logger.info(f"Stored {len(mappings)} security mappings")
            
        except Exception as e:
            logger.error(f"Error storing mappings: {e}")
    
    def test_mapping(self, symbol='NIFTY', strike=24000, option_type='CE'):
        """Test security ID mapping"""
        logger.info(f"\nTesting mapping for {symbol} {strike} {option_type}")
        
        security_id, lot_size = self.find_security_id(symbol, option_type, strike)
        
        if security_id:
            logger.info(f"✅ Found: Security ID = {security_id}, Lot Size = {lot_size}")
        else:
            logger.info("❌ Not found")
        
        return security_id, lot_size

def main():
    """Main function to test mapping"""
    try:
        mapper = DhanSecurityMapper()
        
        # Test some common mappings
        logger.info("Testing security ID mappings...")
        
        mapper.test_mapping('NIFTY', 24000, 'CE')
        mapper.test_mapping('NIFTY', 24000, 'PE')
        mapper.test_mapping('BANKNIFTY', 52000, 'CE')
        mapper.test_mapping('BANKNIFTY', 51000, 'PE')
        
        # Test mapping a strategy
        strategy_id = input("\nEnter a strategy ID to map (or press Enter to skip): ")
        if strategy_id:
            mappings = mapper.map_strategy_securities(int(strategy_id))
            
            if mappings:
                logger.info("\nStrategy Security Mappings:")
                for m in mappings:
                    status = "✅" if m['security_id'] else "❌"
                    logger.info(f"{status} Leg {m['leg_id']}: {m['symbol']} {m['strike_price']} {m['option_type']} → Security ID: {m['security_id']}")
        
    except Exception as e:
        logger.error(f"Mapping test failed: {e}", exc_info=True)

if __name__ == "__main__":
    main()