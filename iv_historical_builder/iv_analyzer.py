"""
IV Analyzer - Calculates IV percentiles and rankings from historical data
Updates iv_percentiles table with current statistics
"""

import os
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

class IVAnalyzer:
    def __init__(self):
        """Initialize IV Analyzer with Supabase connection"""
        # Load .env from root digitalocean directory
        load_dotenv('/Users/jaykrish/Documents/digitalocean/.env')
        
        # Initialize Supabase client
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_ANON_KEY')
        
        if not supabase_url or not supabase_key:
            raise ValueError("Supabase credentials not found in environment variables")
        
        self.supabase: Client = create_client(supabase_url, supabase_key)
        logger.info("IV Analyzer initialized successfully")
        
        # Lookback periods to calculate
        self.lookback_periods = [5, 10, 20, 30]
    
    def get_symbols(self):
        """Get all unique symbols from historical_iv_summary"""
        try:
            response = self.supabase.table('historical_iv_summary')\
                .select('symbol')\
                .execute()
            
            if not response.data:
                return []
            
            symbols = list(set([row['symbol'] for row in response.data]))
            logger.info(f"Found {len(symbols)} symbols to analyze")
            return symbols
            
        except Exception as e:
            logger.error(f"Error getting symbols: {e}")
            return []
    
    def calculate_percentiles(self, symbol, lookback_days):
        """Calculate IV percentiles for a symbol over specified lookback period"""
        try:
            # Get historical data
            cutoff_date = (datetime.now() - timedelta(days=lookback_days)).strftime('%Y-%m-%d')
            
            response = self.supabase.table('historical_iv_summary')\
                .select('date, atm_iv')\
                .eq('symbol', symbol)\
                .gte('date', cutoff_date)\
                .order('date', desc=True)\
                .execute()
            
            if not response.data or len(response.data) < 2:
                data_count = len(response.data) if response.data else 0
                logger.warning(f"Insufficient data for {symbol} ({data_count} days)")
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame(response.data)
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            
            # Get current (latest) IV
            current_iv = df.iloc[-1]['atm_iv']
            current_iv_date = df.iloc[-1]['date'].strftime('%Y-%m-%d')
            
            # Calculate statistics
            iv_values = df['atm_iv'].values
            
            # Percentiles
            percentiles = {
                'percentile_10': np.percentile(iv_values, 10),
                'percentile_25': np.percentile(iv_values, 25),
                'percentile_50': np.percentile(iv_values, 50),
                'percentile_75': np.percentile(iv_values, 75),
                'percentile_90': np.percentile(iv_values, 90)
            }
            
            # IV Rank: (Current - Min) / (Max - Min) * 100
            iv_low = iv_values.min()
            iv_high = iv_values.max()
            iv_rank = ((current_iv - iv_low) / (iv_high - iv_low) * 100) if iv_high > iv_low else 50
            
            # IV Percentile: What % of days in lookback had IV lower than current
            iv_percentile = (iv_values < current_iv).sum() / len(iv_values) * 100
            
            return {
                'symbol': symbol,
                'lookback_days': lookback_days,
                'current_iv': round(current_iv, 3),
                'current_iv_date': current_iv_date,
                'percentile_10': round(percentiles['percentile_10'], 3),
                'percentile_25': round(percentiles['percentile_25'], 3),
                'percentile_50': round(percentiles['percentile_50'], 3),
                'percentile_75': round(percentiles['percentile_75'], 3),
                'percentile_90': round(percentiles['percentile_90'], 3),
                'iv_low': round(iv_low, 3),
                'iv_high': round(iv_high, 3),
                'iv_rank': round(iv_rank, 2),
                'iv_percentile': round(iv_percentile, 2),
                'data_days': len(df)
            }
            
        except Exception as e:
            logger.error(f"Error calculating percentiles for {symbol}: {e}")
            return None
    
    def update_percentiles(self, symbol):
        """Update percentiles for all lookback periods for a symbol"""
        try:
            results = []
            
            for lookback in self.lookback_periods:
                percentile_data = self.calculate_percentiles(symbol, lookback)
                if percentile_data:
                    results.append(percentile_data)
            
            if results:
                # Upsert results
                response = self.supabase.table('iv_percentiles')\
                    .upsert(results, on_conflict='symbol,lookback_days')\
                    .execute()
                
                if response.data:
                    logger.info(f"Updated {len(results)} percentile records for {symbol}")
            
        except Exception as e:
            logger.error(f"Error updating percentiles for {symbol}: {e}")
    
    def analyze_all_symbols(self):
        """Analyze all symbols and update percentiles"""
        try:
            symbols = self.get_symbols()
            
            if not symbols:
                logger.warning("No symbols found to analyze")
                return
            
            logger.info(f"Analyzing {len(symbols)} symbols")
            
            for i, symbol in enumerate(symbols):
                logger.info(f"Processing {symbol} ({i+1}/{len(symbols)})")
                self.update_percentiles(symbol)
            
            logger.info("Analysis completed successfully")
            
        except Exception as e:
            logger.error(f"Error analyzing all symbols: {e}")
    
    def get_iv_environment(self, symbol, lookback_days=30):
        """Get current IV environment for a symbol"""
        try:
            response = self.supabase.table('iv_percentiles')\
                .select('*')\
                .eq('symbol', symbol)\
                .eq('lookback_days', lookback_days)\
                .execute()
            
            if not response.data:
                return None
            
            data = response.data[0]
            
            # Determine environment
            percentile = data['iv_percentile']
            if percentile < 20:
                environment = 'LOW'
            elif percentile < 40:
                environment = 'SUBDUED'
            elif percentile < 60:
                environment = 'NORMAL'
            elif percentile < 80:
                environment = 'ELEVATED'
            else:
                environment = 'HIGH'
            
            return {
                'symbol': symbol,
                'current_iv': data['current_iv'],
                'iv_percentile': data['iv_percentile'],
                'iv_rank': data['iv_rank'],
                'iv_environment': environment,
                'iv_range': (data['iv_low'], data['iv_high']),
                'percentiles': {
                    '10th': data['percentile_10'],
                    '25th': data['percentile_25'],
                    '50th': data['percentile_50'],
                    '75th': data['percentile_75'],
                    '90th': data['percentile_90']
                },
                'data_days': data['data_days'],
                'last_updated': data['last_updated']
            }
            
        except Exception as e:
            logger.error(f"Error getting IV environment for {symbol}: {e}")
            return None


def main():
    """Main function to run IV analysis"""
    analyzer = IVAnalyzer()
    
    # Analyze all symbols
    analyzer.analyze_all_symbols()
    
    # Example: Get IV environment for a specific symbol
    if len(os.sys.argv) > 1:
        symbol = os.sys.argv[1]
        env = analyzer.get_iv_environment(symbol)
        if env:
            print(f"\nIV Environment for {symbol}:")
            print(f"Current IV: {env['current_iv']}")
            print(f"IV Percentile: {env['iv_percentile']}%")
            print(f"IV Rank: {env['iv_rank']}%")
            print(f"Environment: {env['iv_environment']}")
            print(f"IV Range: {env['iv_range']}")


if __name__ == "__main__":
    main()