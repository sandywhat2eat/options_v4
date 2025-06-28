"""
IV Collector - Collects and processes daily IV data from option_chain_data table
Builds historical IV summaries for percentile calculations
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dotenv import load_dotenv
from supabase import create_client, Client
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class IVCollector:
    def __init__(self):
        """Initialize IV Collector with Supabase connection"""
        # Load .env from root digitalocean directory
        load_dotenv('/Users/jaykrish/Documents/digitalocean/.env')
        
        # Initialize Supabase client
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_ANON_KEY')
        
        if not supabase_url or not supabase_key:
            raise ValueError("Supabase credentials not found in environment variables")
        
        self.supabase: Client = create_client(supabase_url, supabase_key)
        logger.info("IV Collector initialized successfully")
    
    def get_unique_dates(self, start_date=None):
        """Get all unique dates in option_chain_data table"""
        try:
            # Get all dates with pagination to handle large datasets
            all_dates = []
            offset = 0
            limit = 1000
            
            while True:
                query = self.supabase.table('option_chain_data')\
                    .select('created_at')\
                    .range(offset, offset + limit - 1)
                
                if start_date:
                    query = query.gte('created_at', start_date)
                
                response = query.execute()
                
                if not response.data:
                    break
                
                all_dates.extend(response.data)
                
                if len(response.data) < limit:
                    break
                    
                offset += limit
            
            if not all_dates:
                logger.warning("No data found in option_chain_data")
                return []
            
            # Extract unique dates
            dates_df = pd.DataFrame(all_dates)
            dates_df['date'] = pd.to_datetime(dates_df['created_at']).dt.date
            unique_dates = sorted(dates_df['date'].unique())
            
            logger.info(f"Found {len(unique_dates)} unique dates from {len(all_dates)} records")
            return unique_dates
            
        except Exception as e:
            logger.error(f"Error getting unique dates: {e}")
            return []
    
    def process_date(self, process_date):
        """Process IV data for a specific date"""
        try:
            # Convert date to string format
            date_str = process_date.strftime('%Y-%m-%d')
            logger.info(f"Processing IV data for {date_str}")
            
            # Fetch all options data for this date with pagination
            all_data = []
            offset = 0
            limit = 1000
            
            while True:
                response = self.supabase.table('option_chain_data')\
                    .select('*')\
                    .gte('created_at', f"{date_str}T00:00:00")\
                    .lt('created_at', f"{date_str}T23:59:59")\
                    .range(offset, offset + limit - 1)\
                    .execute()
                
                if not response.data:
                    break
                
                all_data.extend(response.data)
                logger.info(f"Fetched {len(response.data)} records for {date_str} (total: {len(all_data)})")
                
                if len(response.data) < limit:
                    break
                    
                offset += limit
            
            if not all_data:
                logger.warning(f"No data found for {date_str}")
                return
            
            logger.info(f"Total records fetched for {date_str}: {len(all_data)}")
            
            # Convert to DataFrame
            df = pd.DataFrame(all_data)
            
            # Filter out NULL IV values and invalid data
            df = df[df['implied_volatility'].notna()]
            df = df[df['implied_volatility'] > 0]
            
            # Get unique symbols
            symbols = df['symbol'].unique()
            logger.info(f"Processing {len(symbols)} symbols for {date_str}")
            
            # Process each symbol
            summaries = []
            for symbol in symbols:
                summary = self.calculate_iv_summary(df[df['symbol'] == symbol], symbol, process_date)
                if summary:
                    summaries.append(summary)
            
            # Insert summaries into database
            if summaries:
                self.insert_iv_summaries(summaries)
                logger.info(f"Inserted {len(summaries)} IV summaries for {date_str}")
            
        except Exception as e:
            logger.error(f"Error processing date {process_date}: {e}")
    
    def calculate_iv_summary(self, symbol_df, symbol, date):
        """Calculate IV summary statistics for a symbol on a specific date"""
        try:
            # Basic validations
            if len(symbol_df) < 5:  # Need minimum data points
                return None
            
            # Get spot price
            spot_price = symbol_df['underlying_price'].iloc[0]
            
            # Calculate ATM IV
            symbol_df['strike_distance'] = abs(symbol_df['strike_price'] - spot_price)
            symbol_df = symbol_df.sort_values('strike_distance')
            
            # Get 5 closest strikes for ATM calculation
            atm_options = symbol_df.head(10)
            atm_iv = atm_options['implied_volatility'].mean()
            
            # Overall IV statistics
            iv_mean = symbol_df['implied_volatility'].mean()
            iv_median = symbol_df['implied_volatility'].median()
            iv_std = symbol_df['implied_volatility'].std()
            
            # Separate calls and puts
            calls = symbol_df[symbol_df['option_type'] == 'CALL']
            puts = symbol_df[symbol_df['option_type'] == 'PUT']
            
            # Calculate means
            call_iv_mean = calls['implied_volatility'].mean() if len(calls) > 0 else iv_mean
            put_iv_mean = puts['implied_volatility'].mean() if len(puts) > 0 else iv_mean
            
            # IV Skew (Put IV - Call IV)
            iv_skew = put_iv_mean - call_iv_mean
            
            # Volume and OI
            total_volume = symbol_df['volume'].sum()
            total_oi = symbol_df['open_interest'].sum()
            
            return {
                'symbol': symbol,
                'date': date.strftime('%Y-%m-%d'),
                'atm_iv': round(atm_iv, 3),
                'iv_mean': round(iv_mean, 3),
                'iv_median': round(iv_median, 3),
                'iv_std': round(iv_std, 3),
                'call_iv_mean': round(call_iv_mean, 3),
                'put_iv_mean': round(put_iv_mean, 3),
                'iv_skew': round(iv_skew, 3),
                'total_volume': int(total_volume),
                'total_oi': int(total_oi),
                'spot_price': round(spot_price, 2),
                'data_points': len(symbol_df)
            }
            
        except Exception as e:
            logger.error(f"Error calculating IV summary for {symbol}: {e}")
            return None
    
    def insert_iv_summaries(self, summaries):
        """Insert IV summaries into database"""
        try:
            # Use upsert to handle duplicates
            response = self.supabase.table('historical_iv_summary')\
                .upsert(summaries, on_conflict='symbol,date')\
                .execute()
            
            if response.data:
                logger.info(f"Successfully inserted {len(summaries)} IV summaries")
            
        except Exception as e:
            logger.error(f"Error inserting IV summaries: {e}")
    
    def backfill_historical_data(self, days_back=30):
        """Backfill historical IV data for specified number of days"""
        try:
            # Get unique dates
            all_dates = self.get_unique_dates()
            
            if not all_dates:
                logger.warning("No dates found to process")
                return
            
            # Filter to last N days
            cutoff_date = datetime.now().date() - timedelta(days=days_back)
            dates_to_process = [d for d in all_dates if d >= cutoff_date]
            
            logger.info(f"Backfilling {len(dates_to_process)} days of IV data")
            
            # Process each date
            for date in dates_to_process:
                logger.info(f"Processing {date}")
                self.process_date(date)
            
            logger.info("Backfill completed successfully")
            
        except Exception as e:
            logger.error(f"Error during backfill: {e}")
    
    def process_latest_date(self):
        """Process only the most recent date's data"""
        try:
            # Get the latest date
            dates = self.get_unique_dates()
            if not dates:
                logger.warning("No dates found to process")
                return
            
            latest_date = dates[-1]
            logger.info(f"Processing latest date: {latest_date}")
            
            self.process_date(latest_date)
            
        except Exception as e:
            logger.error(f"Error processing latest date: {e}")


def main():
    """Main function to run IV collection"""
    collector = IVCollector()
    
    # Check command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == '--backfill':
            days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
            logger.info(f"Running backfill for {days} days")
            collector.backfill_historical_data(days)
        elif sys.argv[1] == '--latest':
            logger.info("Processing latest date only")
            collector.process_latest_date()
    else:
        # Default: process latest date
        logger.info("Processing latest date (use --backfill N for historical data)")
        collector.process_latest_date()


if __name__ == "__main__":
    main()