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
            # Fetch from stock_data where fno_stock = 'yes', limit to 250 for portfolio analysis
            response = self.supabase.table('stock_data').select('symbol').eq('fno_stock', 'yes').limit(250).execute()
            
            if not response.data:
                logger.warning("No FNO stocks found")
                return []
            
            symbols = [row['symbol'] for row in response.data]
            logger.info(f"Fetched {len(symbols)} FNO-enabled stocks")
            return symbols
        except Exception as e:
            logger.error(f"Error fetching FNO stocks: {e}")
            return []
    
    def get_options_data(self, symbol: str, multiple_expiries: bool = False) -> Optional[pd.DataFrame]:
        """Fetch options chain data for symbol - MONTHLY EXPIRY ONLY WITH TOP 10 OI STRIKES"""
        try:
            # First get the latest date for this symbol
            latest_date_response = self.supabase.table('option_chain_data')\
                .select('created_at')\
                .eq('symbol', symbol)\
                .order('created_at', desc=True)\
                .limit(1)\
                .execute()
            
            if not latest_date_response.data:
                logger.warning(f"No options data found for {symbol}")
                return None
            
            # Extract date part only (YYYY-MM-DD)
            latest_date = latest_date_response.data[0]['created_at'].split('T')[0]
            
            # Determine which monthly expiry to fetch based on current date
            current_day = datetime.now().day
            
            # Get all available expiries for the latest date
            expiry_response = self.supabase.table('option_chain_data')\
                .select('expiry_date')\
                .eq('symbol', symbol)\
                .gte('created_at', f"{latest_date}T00:00:00")\
                .lt('created_at', f"{latest_date}T23:59:59")\
                .execute()
            
            if not expiry_response.data:
                logger.warning(f"No expiries found for {symbol}")
                return None
            
            # Get unique expiries and sort them
            expiries = sorted(list(set([row['expiry_date'] for row in expiry_response.data])))
            
            if multiple_expiries and len(expiries) >= 2:
                # For strategies like Calendar Spread, fetch first 2 expiries
                target_expiries = expiries[:2]
                logger.info(f"Fetching multiple expiries for {symbol}: {target_expiries}")
                
                # Fetch data for multiple expiries
                response = self.supabase.table('option_chain_data')\
                    .select('*')\
                    .eq('symbol', symbol)\
                    .in_('expiry_date', target_expiries)\
                    .gte('created_at', f"{latest_date}T00:00:00")\
                    .lt('created_at', f"{latest_date}T23:59:59")\
                    .execute()
            else:
                # Select appropriate monthly expiry based on 20th rule
                target_expiry = None
                for expiry in expiries:
                    expiry_date = datetime.strptime(expiry, '%Y-%m-%d')
                    # Check if this is a monthly expiry (last Thursday of month logic can be added)
                    if current_day <= 20:
                        # Use current month expiry
                        if expiry_date.month == datetime.now().month:
                            target_expiry = expiry
                            break
                    else:
                        # Use next month expiry
                        if expiry_date.month > datetime.now().month or expiry_date.year > datetime.now().year:
                            target_expiry = expiry
                            break
                
                if not target_expiry:
                    # Fallback to nearest expiry
                    target_expiry = expiries[0]
                
                logger.info(f"Selected expiry: {target_expiry} for {symbol} (current day: {current_day})")
                
                # Fetch all data for the selected expiry
                response = self.supabase.table('option_chain_data')\
                    .select('*')\
                    .eq('symbol', symbol)\
                    .eq('expiry_date', target_expiry)\
                    .gte('created_at', f"{latest_date}T00:00:00")\
                    .lt('created_at', f"{latest_date}T23:59:59")\
                    .execute()
            
            if not response.data:
                logger.warning(f"No options data found for {symbol} on {latest_date}")
                return None
            
            df = pd.DataFrame(response.data)
            
            # Convert numeric columns (using actual database column names)
            numeric_cols = ['strike_price', 'open_interest', 'volume', 'ltp', 
                          'bid', 'ask', 'delta', 'gamma', 'theta', 'vega', 'implied_volatility',
                          'underlying_price', 'prev_oi', 'prev_close']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Get top 10 OI strikes for CALLs and PUTs
            calls_df = df[df['option_type'] == 'CALL'].copy()
            puts_df = df[df['option_type'] == 'PUT'].copy()
            
            # Get top 10 OI strikes for each type
            top_call_strikes = calls_df.nlargest(10, 'open_interest')['strike_price'].unique()
            top_put_strikes = puts_df.nlargest(10, 'open_interest')['strike_price'].unique()
            
            # Combine unique strikes
            top_strikes = set(top_call_strikes) | set(top_put_strikes)
            
            # Filter dataframe to only include top OI strikes
            df_filtered = df[df['strike_price'].isin(top_strikes)].copy()
            
            logger.info(f"Filtered from {len(df)} to {len(df_filtered)} records (top 10 OI strikes each side)")
            
            # Standardize column names for consistency with our code
            df_filtered = df_filtered.rename(columns={
                'strike_price': 'strike',
                'ltp': 'last_price', 
                'implied_volatility': 'iv',
                'underlying_price': 'spot_price',
                'expiry_date': 'expiry'  # Add expiry mapping for Calendar Spread
            })
            
            return df_filtered
            
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
    
    def get_multi_expiry_options(self, symbol: str) -> Optional[pd.DataFrame]:
        """
        Get options data for multiple expiries (for Calendar Spreads)
        
        Args:
            symbol: Stock symbol
            
        Returns:
            DataFrame with options from multiple expiries, or None if insufficient expiries
        """
        return self.get_options_data(symbol, multiple_expiries=True)