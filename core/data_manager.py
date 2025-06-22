"""
Data Manager for fetching and processing market data
"""

import pandas as pd
from supabase import create_client
import os
import logging
from datetime import datetime
from typing import Dict, Optional, List

from .lot_size_manager import LotSizeManager

logger = logging.getLogger(__name__)

class DataManager:
    """Handles all data fetching and processing operations"""
    
    def __init__(self):
        self.supabase = create_client(
            os.getenv('NEXT_PUBLIC_SUPABASE_URL'),
            os.getenv('NEXT_PUBLIC_SUPABASE_ANON_KEY')
        )
        self.lot_manager = LotSizeManager()
        
    def get_portfolio_symbols(self) -> List[str]:
        """Fetch FNO-enabled stocks from stock_data table"""
        try:
            # Fetch from stock_data where fno_stock = 'yes', limit to 50 for portfolio analysis
            response = self.supabase.table('stock_data').select('symbol').eq('fno_stock', 'yes').limit(50).execute()
            
            if not response.data:
                logger.warning("No FNO stocks found")
                return []
            
            symbols = [row['symbol'] for row in response.data]
            logger.info(f"Fetched {len(symbols)} FNO-enabled stocks")
            return symbols
        except Exception as e:
            logger.error(f"Error fetching FNO stocks: {e}")
            return []
    
    def get_options_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Fetch options chain data for symbol"""
        try:
            response = self.supabase.table('option_chain_data').select('*').eq('symbol', symbol).execute()
            if not response.data:
                return None
            
            df = pd.DataFrame(response.data)
            
            # Convert numeric columns (using actual database column names)
            numeric_cols = ['strike_price', 'open_interest', 'volume', 'ltp', 
                          'bid', 'ask', 'delta', 'gamma', 'theta', 'vega', 'implied_volatility',
                          'underlying_price', 'prev_oi', 'prev_close']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Standardize column names for consistency with our code
            df = df.rename(columns={
                'strike_price': 'strike',
                'ltp': 'last_price', 
                'implied_volatility': 'iv',
                'underlying_price': 'spot_price'
            })
            
            return df
            
        except Exception as e:
            logger.error(f"Error fetching options data for {symbol}: {e}")
            return None
    
    def get_spot_price(self, symbol: str) -> Optional[float]:
        """Get current spot price for symbol"""
        try:
            options_df = self.get_options_data(symbol)
            if options_df is None or options_df.empty:
                return None
            
            # Get spot price from options data (now mapped to spot_price from underlying_price)
            if 'spot_price' in options_df.columns:
                spot_price = options_df['spot_price'].iloc[0]
                return float(spot_price) if spot_price else None
            else:
                logger.error(f"No spot price found for {symbol}")
                return None
            
        except Exception as e:
            logger.error(f"Error getting spot price for {symbol}: {e}")
            return None
    
    def get_liquid_options(self, symbol: str, min_oi: int = 100, min_volume: int = 50, 
                          max_spread_pct: float = 0.05) -> Optional[pd.DataFrame]:
        """Filter options for liquidity"""
        try:
            df = self.get_options_data(symbol)
            if df is None or df.empty:
                return None
            
            # Apply liquidity filters
            liquid_mask = (
                (df['open_interest'] >= min_oi) &
                (df['volume'] >= min_volume) &
                (df['bid'] > 0) & (df['ask'] > 0) &
                ((df['ask'] - df['bid']) / ((df['ask'] + df['bid']) / 2) <= max_spread_pct)
            )
            
            return df[liquid_mask].copy()
            
        except Exception as e:
            logger.error(f"Error filtering liquid options for {symbol}: {e}")
            return None
    
    def get_atm_strike(self, symbol: str) -> Optional[float]:
        """Find ATM strike for symbol"""
        try:
            spot_price = self.get_spot_price(symbol)
            if spot_price is None:
                return None
            
            df = self.get_options_data(symbol)
            if df is None or df.empty:
                return None
            
            # Find closest strike to spot
            df['strike_diff'] = abs(df['strike'] - spot_price)
            atm_strike = df.loc[df['strike_diff'].idxmin(), 'strike']
            
            return float(atm_strike)
            
        except Exception as e:
            logger.error(f"Error finding ATM strike for {symbol}: {e}")
            return None
    
    def get_strikes_by_delta(self, symbol: str, target_delta: float, 
                           option_type: str = 'CALL', tolerance: float = 0.05) -> List[float]:
        """Find strikes near target delta"""
        try:
            df = self.get_liquid_options(symbol)
            if df is None or df.empty:
                return []
            
            # Filter by option type
            type_df = df[df['option_type'] == option_type.upper()]
            if type_df.empty:
                return []
            
            # Find strikes within delta tolerance
            type_df['delta_diff'] = abs(type_df['delta'] - abs(target_delta))
            matches = type_df[type_df['delta_diff'] <= tolerance]
            
            if matches.empty:
                # If no matches, get closest
                closest_idx = type_df['delta_diff'].idxmin()
                return [float(type_df.loc[closest_idx, 'strike'])]
            
            return sorted(matches['strike'].tolist())
            
        except Exception as e:
            logger.error(f"Error finding strikes by delta for {symbol}: {e}")
            return []
    
    def get_lot_size(self, symbol: str) -> int:
        """
        Get lot size for symbol using LotSizeManager
        
        Args:
            symbol: Clean symbol name (e.g., 'DIXON')
            
        Returns:
            Lot size for the symbol
        """
        return self.lot_manager.get_current_lot_size(symbol)
    
    def get_position_multiplier(self, symbol: str) -> int:
        """
        Alias for get_lot_size for clarity in position calculations
        
        Args:
            symbol: Clean symbol name
            
        Returns:
            Position multiplier (lot size)
        """
        return self.get_lot_size(symbol)