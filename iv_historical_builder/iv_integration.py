"""
IV Integration Helper - Interface between main system and historical IV data
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client
import logging

logger = logging.getLogger(__name__)

class HistoricalIVProvider:
    """Provides IV percentile data from historical IV system"""
    
    def __init__(self):
        """Initialize with Supabase connection"""
        # Load .env from root digitalocean directory
        load_dotenv('/Users/jaykrish/Documents/digitalocean/.env')
        
        # Initialize Supabase client
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_ANON_KEY')
        
        if not supabase_url or not supabase_key:
            raise ValueError("Supabase credentials not found in environment variables")
        
        self.supabase: Client = create_client(supabase_url, supabase_key)
    
    def get_iv_environment(self, symbol: str, lookback_days: int = 30) -> dict:
        """
        Get IV environment for a symbol
        
        Returns:
        {
            'current_iv': float,
            'iv_percentile': float,
            'iv_rank': float, 
            'iv_environment': str,  # LOW/SUBDUED/NORMAL/ELEVATED/HIGH
            'data_quality': str,    # Data quality indicator
            'last_updated': str
        }
        """
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
            
            # Data quality assessment
            data_days = data['data_days']
            if data_days >= 20:
                data_quality = 'GOOD'
            elif data_days >= 10:
                data_quality = 'FAIR'
            elif data_days >= 5:
                data_quality = 'LIMITED'
            else:
                data_quality = 'POOR'
            
            return {
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
                'data_days': data_days,
                'data_quality': data_quality,
                'last_updated': data['last_updated']
            }
            
        except Exception as e:
            logger.error(f"Error getting IV environment for {symbol}: {e}")
            return None
    
    def get_iv_percentile_analysis(self, symbol: str, lookback_days: int = 30) -> dict:
        """
        Get detailed IV percentile analysis for strategy selection
        
        Returns analysis suitable for the main system's IV analyzer
        """
        iv_data = self.get_iv_environment(symbol, lookback_days)
        
        if not iv_data:
            return {
                'percentile': 50,
                'method': 'default_no_data',
                'lookback_days': 0,
                'iv_range': (20, 45),
                'current_rank': 'Unknown',
                'confidence': 'No historical data available'
            }
        
        return {
            'percentile': int(iv_data['iv_percentile']),
            'method': 'historical_data',
            'lookback_days': iv_data['data_days'],
            'iv_range': iv_data['iv_range'],
            'current_rank': iv_data['iv_environment'],
            'confidence': f"{iv_data['data_quality']} - {iv_data['data_days']} days of data",
            'iv_rank': iv_data['iv_rank'],
            'current_iv': iv_data['current_iv']
        }


def get_enhanced_iv_analysis(symbol: str, current_iv: float = None) -> dict:
    """
    Enhanced IV analysis function that can be used in main system
    Combines current IV with historical percentiles
    """
    try:
        provider = HistoricalIVProvider()
        
        # Get historical analysis
        historical_analysis = provider.get_iv_percentile_analysis(symbol)
        
        # If we have current IV, use it; otherwise use historical
        if current_iv is not None:
            historical_analysis['current_iv'] = current_iv
        
        # Enhanced environment categorization
        percentile = historical_analysis['percentile']
        
        if percentile < 20:
            iv_environment = 'LOW'
            strategy_recommendation = 'Buy volatility - Long Straddle, Long Strangle'
        elif percentile < 40:
            iv_environment = 'SUBDUED'
            strategy_recommendation = 'Moderate volatility buying - Calendar Spreads'
        elif percentile < 60:
            iv_environment = 'NORMAL'
            strategy_recommendation = 'Balanced approach - Directional strategies'
        elif percentile < 80:
            iv_environment = 'ELEVATED'
            strategy_recommendation = 'Consider volatility selling - Credit spreads'
        else:
            iv_environment = 'HIGH'
            strategy_recommendation = 'Sell volatility - Iron Condor, Short Straddle'
        
        return {
            'iv_environment': iv_environment,
            'percentile_analysis': historical_analysis,
            'strategy_recommendation': strategy_recommendation,
            'mean_reversion_potential': 'High' if percentile > 80 or percentile < 20 else 'Moderate',
            'data_source': 'historical_iv_system'
        }
        
    except Exception as e:
        logger.error(f"Error in enhanced IV analysis for {symbol}: {e}")
        # Fallback to default
        return {
            'iv_environment': 'NORMAL',
            'percentile_analysis': {
                'percentile': 50,
                'method': 'fallback',
                'confidence': 'Error accessing historical data'
            },
            'strategy_recommendation': 'Directional strategies',
            'mean_reversion_potential': 'Unknown',
            'data_source': 'fallback'
        }


if __name__ == "__main__":
    # Test the integration
    provider = HistoricalIVProvider()
    
    # Test symbols that should have data
    test_symbols = ['SUNPHARMA', 'DIXON', 'MARICO', 'HDFCAMC']
    
    for symbol in test_symbols:
        print(f"\n=== {symbol} ===")
        iv_env = provider.get_iv_environment(symbol)
        if iv_env:
            print(f"Current IV: {iv_env['current_iv']}")
            print(f"IV Percentile: {iv_env['iv_percentile']}%")
            print(f"IV Environment: {iv_env['iv_environment']}")
            print(f"Data Quality: {iv_env['data_quality']} ({iv_env['data_days']} days)")
        else:
            print("No IV data available")
        
        # Test enhanced analysis
        enhanced = get_enhanced_iv_analysis(symbol)
        print(f"Strategy Recommendation: {enhanced['strategy_recommendation']}")
        print(f"Mean Reversion: {enhanced['mean_reversion_potential']}")