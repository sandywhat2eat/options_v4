"""
INDEX Profiler - Comprehensive INDEX volatility and characteristic analysis
Provides volatility profiling, beta calculation, and INDEX-specific metrics for strategy selection
INDEX VERSION - NO STOCKS
"""

import numpy as np
import pandas as pd
import yfinance as yf
import logging
from typing import Dict, Optional, Tuple, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class StockProfiler:
    """
    Comprehensive INDEX profiling system that analyzes:
    - Volatility characteristics (HV, ATR, IV) for INDEXES ONLY
    - Market relationships (Beta, correlation with NIFTY)
    - INDEX-specific characteristics with Dhan API integration
    INDEX VERSION - NO STOCKS
    """
    
    def __init__(self, supabase_client=None):
        self.supabase = supabase_client
        self._metadata_cache = {}  # Cache for index data
        
        # INDEX SYMBOLS - ALL symbols in this system are indexes
        self.INDEX_SYMBOLS = [
            'NIFTY 50', 'BANK NIFTY', 'NIFTY FIN SERVICE', 
            'NIFTY IT', 'NIFTY MIDCAP 50'
        ]
        
        # Volatility profile definitions
        self.VOLATILITY_PROFILES = {
            'ultra_high': {
                'atr_pct_range': [4.0, 100],  # >4%
                'typical_beta': [1.5, 3.0],   # High beta stocks
                'examples': ['ZOMATO', 'PAYTM', 'NYKAA', 'RBLBANK', 'ANGELONE'],
                'daily_move_range': [3, 8],   # 3-8% daily
                'weekly_move_range': [10, 25], # 10-25% weekly
                'preferred_strategies': ['Long Call', 'Long Put', 'Bull Call Spread', 'Bear Put Spread'],
                'avoid_strategies': ['Iron Condor', 'Short Straddle', 'Iron Butterfly'],
                'position_size_multiplier': 0.3,
                'min_spread_width': 0.08,      # 8% minimum spread width
                'expected_move_multiplier': 1.5, # Use 150% of calculated move
                'min_probability_threshold': 0.15  # Lower threshold for volatile stocks
            },
            
            'high': {
                'atr_pct_range': [2.5, 4.0],
                'typical_beta': [1.2, 1.5],
                'examples': ['BAJFINANCE', 'TATAPOWER', 'ADANIGREEN', 'HAL'],
                'daily_move_range': [2, 4],
                'weekly_move_range': [5, 15],
                'preferred_strategies': ['Bull Call Spread', 'Bear Put Spread', 'Long Strangle', 'Diagonal Spread'],
                'avoid_strategies': ['Iron Butterfly', 'Short Straddle'],
                'position_size_multiplier': 0.5,
                'min_spread_width': 0.05,
                'expected_move_multiplier': 1.2,
                'min_probability_threshold': 0.20
            },
            
            'medium': {
                'atr_pct_range': [1.5, 2.5],
                'typical_beta': [0.8, 1.2],
                'examples': ['INFY', 'WIPRO', 'TATAMOTORS', 'M&M', 'LT'],
                'daily_move_range': [1, 2.5],
                'weekly_move_range': [3, 8],
                'preferred_strategies': ['Iron Condor', 'Calendar Spread', 'Bull Put Spread', 'Bear Call Spread'],
                'avoid_strategies': [],  # Flexible
                'position_size_multiplier': 0.75,
                'min_spread_width': 0.03,
                'expected_move_multiplier': 1.0,
                'min_probability_threshold': 0.25
            },
            
            'low': {
                'atr_pct_range': [0, 1.5],
                'typical_beta': [0.5, 0.8],
                'examples': ['RELIANCE', 'TCS', 'HDFC', 'HDFCBANK', 'ITC'],
                'daily_move_range': [0.5, 2],
                'weekly_move_range': [2, 5],
                'preferred_strategies': ['Iron Condor', 'Short Strangle', 'Butterfly Spread', 'Credit Spreads'],
                'avoid_strategies': ['Long Straddle', 'Long Call', 'Long Put'],
                'position_size_multiplier': 1.0,
                'min_spread_width': 0.02,
                'expected_move_multiplier': 0.8,
                'min_probability_threshold': 0.35
            }
        }
        
        # Sector volatility characteristics
        self.SECTOR_VOLATILITY_PROFILES = {
            'Technology Services': {'typical_vol': 'medium', 'beta_range': [0.8, 1.2]},
            'Finance': {'typical_vol': 'medium_high', 'beta_range': [1.0, 1.5]},
            'Consumer Durables': {'typical_vol': 'high', 'beta_range': [1.2, 1.8]},
            'Energy Minerals': {'typical_vol': 'medium', 'beta_range': [0.7, 1.1]},
            'Health Technology': {'typical_vol': 'low_medium', 'beta_range': [0.6, 1.0]},
            'Electronic Technology': {'typical_vol': 'high', 'beta_range': [1.1, 1.8]},
            'Utilities': {'typical_vol': 'low', 'beta_range': [0.5, 0.9]},
            'Consumer Non-Durables': {'typical_vol': 'low', 'beta_range': [0.5, 0.8]}
        }
    
    def is_index(self, symbol: str) -> bool:
        """Check if symbol is an index - ALL symbols should be indexes in this system"""
        return symbol in self.INDEX_SYMBOLS
    
    def get_complete_profile(self, symbol: str) -> Dict:
        """
        Get comprehensive INDEX profile including all volatility and market metrics
        
        Args:
            symbol: Index name - INDEX ONLY
            
        Returns:
            Dictionary with complete index profile
        """
        try:
            logger.info(f"Generating INDEX profile for {symbol}")
            
            # INDEX-ONLY: All symbols should be indexes
            if not self.is_index(symbol):
                logger.error(f"Unknown index symbol: {symbol}. This system only works with indexes.")
                return self._get_default_profile(symbol)
            
            # Get index profile
            return self._get_index_profile(symbol)
            
        except Exception as e:
            logger.error(f"Error generating INDEX profile for {symbol}: {e}")
            return self._get_default_profile(symbol)
    
    def prefetch_metadata(self, symbols: List[str]) -> None:
        """
        Prefetch INDEX metadata - INDEX ONLY
        
        Args:
            symbols: List of INDEX symbols to fetch metadata for
        """
        if not symbols:
            return
            
        try:
            # Clear existing cache
            self._metadata_cache.clear()
            
            # INDEX-ONLY: Add placeholder metadata for all indexes
            for index_symbol in symbols:
                if self.is_index(index_symbol):
                    self._metadata_cache[index_symbol] = {
                        'sector': 'Index',
                        'industry': 'Index', 
                        'market_capitalization': 0,  # Not applicable
                        'atm_iv': None  # Will be fetched from options data
                    }
                else:
                    logger.warning(f"Non-index symbol {index_symbol} ignored in INDEX-only system")
                
            logger.info(f"Prefetched metadata for {len(self._metadata_cache)} indexes")
            
        except Exception as e:
            logger.error(f"Error prefetching INDEX metadata: {e}")
            # Continue without cache
    
    def _get_database_data(self, symbol: str) -> Dict:
        """Get stock data from database or cache"""
        try:
            # Check cache first
            if symbol in self._metadata_cache:
                return self._metadata_cache[symbol]
                
            if not self.supabase:
                return {}
            
            # For indexes, return placeholder data
            if self.is_index(symbol):
                return {
                    'sector': 'Index',
                    'industry': 'Index',
                    'market_capitalization': 0,
                    'atm_iv': None
                }
                
            response = self.supabase.table('stock_data').select('*').eq('symbol', symbol).execute()
            if response.data and len(response.data) > 0:
                # Cache the result
                self._metadata_cache[symbol] = response.data[0]
                return response.data[0]
            return {}
            
        except Exception as e:
            logger.error(f"Error fetching database data for {symbol}: {e}")
            return {}
    
    def _get_price_history(self, symbol: str, period: str = "1y") -> Optional[pd.DataFrame]:
        """Get price history for INDEX symbols using Dhan API - INDEX ONLY"""
        try:
            # INDEX-ONLY: Only work with index symbols
            if not self.is_index(symbol):
                logger.error(f"Non-index symbol {symbol} not supported in INDEX-only system")
                return None
            
            # Use Dhan API data for indexes
            dhan_data = self._get_index_historical_data_from_dhan(symbol)
            if dhan_data is not None:
                logger.info(f"Using Dhan API historical data for INDEX {symbol}")
                return dhan_data
            else:
                logger.warning(f"Dhan API data not available for INDEX {symbol}, trying Yahoo Finance fallback")
                
                # Fallback to Yahoo Finance for indexes
                index_yf_mapping = {
                    'NIFTY 50': '^NSEI',
                    'BANK NIFTY': '^NSEBANK',
                    'NIFTY FIN SERVICE': 'FINNIFTY.NS',
                    'NIFTY IT': '^CNXIT',
                    'NIFTY MIDCAP 50': 'NIFTYMIDCAP50.NS'
                }
                
                yf_symbol = index_yf_mapping.get(symbol, symbol)
                ticker = yf.Ticker(yf_symbol)
                hist = ticker.history(period=period)
                
                return hist if not hist.empty else None
            
        except Exception as e:
            logger.error(f"Error fetching INDEX price history for {symbol}: {e}")
            return None
    
    def _get_index_historical_data_from_dhan(self, symbol: str) -> Optional[pd.DataFrame]:
        """Get historical data for indexes using Dhan API"""
        try:
            # Check if Dhan credentials are available
            import os
            if not all([os.getenv('DHAN_CLIENT_ID'), os.getenv('DHAN_ACCESS_TOKEN')]):
                logger.debug(f"Dhan API credentials not found, skipping for {symbol}")
                return None
            
            # Try to import and use the Dhan fetcher
            import sys
            
            # Add data_scripts to path
            data_scripts_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data_scripts')
            if data_scripts_path not in sys.path:
                sys.path.append(data_scripts_path)
            
            from all_indices_historical_data import AllIndicesHistoricalDataFetcher
            
            # Initialize fetcher
            fetcher = AllIndicesHistoricalDataFetcher()
            
            # Get 90 days of data
            historical_data = fetcher.get_historical_data_for_index(symbol, days=90)
            
            if not historical_data:
                logger.warning(f"No historical data returned from Dhan API for {symbol}")
                return None
            
            # Convert to pandas DataFrame in yfinance format
            df_data = []
            for record in historical_data:
                df_data.append({
                    'Open': record['open'],
                    'High': record['high'], 
                    'Low': record['low'],
                    'Close': record['close'],
                    'Volume': record.get('volume', 0),
                    'Date': record['date']
                })
            
            df = pd.DataFrame(df_data)
            df['Date'] = pd.to_datetime(df['Date'])
            df.set_index('Date', inplace=True)
            df = df.sort_index()
            
            logger.info(f"Successfully fetched {len(df)} days of Dhan API data for {symbol}")
            return df
            
        except ImportError as e:
            logger.debug(f"Dhan API module not available: {e}")
            return None
        except Exception as e:
            logger.warning(f"Error fetching Dhan historical data for {symbol}: {e}")
            return None
    
    def _calculate_historical_volatility(self, price_data: pd.DataFrame, period: int) -> float:
        """Calculate historical volatility (annualized)"""
        try:
            if len(price_data) < period:
                period = len(price_data)
            
            returns = price_data['Close'].pct_change().dropna()
            if len(returns) < period:
                return 0.0
                
            # Use last N days
            recent_returns = returns.tail(period)
            
            # Annualized volatility
            hv = recent_returns.std() * np.sqrt(252) * 100
            
            return round(hv, 2)
            
        except Exception as e:
            logger.error(f"Error calculating HV: {e}")
            return 20.0  # Default
    
    def _calculate_atr(self, price_data: pd.DataFrame, period: int = 14) -> float:
        """Calculate Average True Range"""
        try:
            high = price_data['High']
            low = price_data['Low']
            close = price_data['Close']
            
            # True Range calculation
            tr1 = high - low
            tr2 = abs(high - close.shift())
            tr3 = abs(low - close.shift())
            
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            
            # ATR is EMA of TR
            atr = tr.ewm(span=period, adjust=False).mean().iloc[-1]
            
            return round(float(atr), 2)
            
        except Exception as e:
            logger.error(f"Error calculating ATR: {e}")
            return 0.0
    
    def _calculate_atr_percentage(self, price_data: pd.DataFrame) -> float:
        """Calculate ATR as percentage of price"""
        try:
            atr = self._calculate_atr(price_data)
            current_price = float(price_data['Close'].iloc[-1])
            
            if current_price > 0:
                atr_pct = (atr / current_price) * 100
                return round(atr_pct, 2)
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Error calculating ATR%: {e}")
            return 2.0  # Default medium volatility
    
    def _calculate_beta_vs_nifty(self, symbol: str, stock_data: pd.DataFrame) -> float:
        """Calculate beta relative to NIFTY"""
        try:
            # Get NIFTY data
            nifty = yf.Ticker("^NSEI")
            nifty_data = nifty.history(period="1y")
            
            if nifty_data.empty:
                logger.warning("Could not fetch NIFTY data")
                return 1.0
            
            # Align dates
            common_dates = stock_data.index.intersection(nifty_data.index)
            if len(common_dates) < 60:  # Need at least 60 days
                return 1.0
            
            # Calculate returns
            stock_returns = stock_data.loc[common_dates, 'Close'].pct_change().dropna()
            nifty_returns = nifty_data.loc[common_dates, 'Close'].pct_change().dropna()
            
            # Calculate beta
            covariance = stock_returns.cov(nifty_returns)
            nifty_variance = nifty_returns.var()
            
            if nifty_variance > 0:
                beta = covariance / nifty_variance
                return round(beta, 2)
            
            return 1.0
            
        except Exception as e:
            logger.error(f"Error calculating beta for {symbol}: {e}")
            return 1.0
    
    def _calculate_correlation_nifty(self, symbol: str, stock_data: pd.DataFrame) -> float:
        """Calculate correlation with NIFTY"""
        try:
            # Get NIFTY data
            nifty = yf.Ticker("^NSEI")
            nifty_data = nifty.history(period="1y")
            
            if nifty_data.empty:
                return 0.5
            
            # Align and calculate returns
            common_dates = stock_data.index.intersection(nifty_data.index)
            stock_returns = stock_data.loc[common_dates, 'Close'].pct_change().dropna()
            nifty_returns = nifty_data.loc[common_dates, 'Close'].pct_change().dropna()
            
            # Calculate correlation
            correlation = stock_returns.corr(nifty_returns)
            
            return round(correlation, 2)
            
        except Exception as e:
            logger.error(f"Error calculating correlation: {e}")
            return 0.5
    
    def _calculate_relative_strength(self, symbol: str, stock_data: pd.DataFrame) -> float:
        """Calculate relative strength vs NIFTY"""
        try:
            # Get NIFTY data
            nifty = yf.Ticker("^NSEI")
            nifty_data = nifty.history(period="3mo")
            
            if nifty_data.empty or len(stock_data) < 63 or len(nifty_data) < 63:
                return 1.0
            
            # Calculate 3-month returns
            stock_return = (stock_data['Close'].iloc[-1] / stock_data['Close'].iloc[-63]) - 1
            nifty_return = (nifty_data['Close'].iloc[-1] / nifty_data['Close'].iloc[-63]) - 1
            
            # Relative strength
            if nifty_return != 0:
                rs = (1 + stock_return) / (1 + nifty_return)
                return round(rs, 2)
            
            return 1.0
            
        except Exception as e:
            logger.error(f"Error calculating RS: {e}")
            return 1.0
    
    def _calculate_price_change(self, price_data: pd.DataFrame, days: int) -> float:
        """Calculate price change over specified days"""
        try:
            if len(price_data) < days:
                return 0.0
                
            current_price = float(price_data['Close'].iloc[-1])
            past_price = float(price_data['Close'].iloc[-days])
            
            if past_price > 0:
                return round(((current_price / past_price) - 1) * 100, 2)
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Error calculating price change: {e}")
            return 0.0
    
    def _classify_market_cap(self, market_cap: float) -> str:
        """Classify market cap category"""
        if market_cap >= 5e12:  # 5 trillion+
            return "Mega Cap"
        elif market_cap >= 1e12:  # 1 trillion+
            return "Large Cap"
        elif market_cap >= 3e11:  # 300 billion+
            return "Mid Cap"
        elif market_cap >= 1e11:  # 100 billion+
            return "Small Cap"
        else:
            return "Micro Cap"
    
    def _classify_volatility(self, atr_pct: float, market_cap: float, current_iv: float) -> str:
        """
        Classify stock into volatility bucket based on multiple factors
        """
        # Primary classification by ATR%
        if atr_pct >= 4.0:
            return 'ultra_high'
        elif atr_pct >= 2.5:
            return 'high'
        elif atr_pct >= 1.5:
            return 'medium'
        else:
            # For low ATR, check if it's genuinely low vol or just a large cap
            if market_cap > 5e12 and current_iv < 20:
                return 'low'
            elif market_cap > 1e12 and current_iv < 25:
                return 'low'
            else:
                return 'medium'  # Default to medium if unclear
    
    def _get_sector_volatility_profile(self, sector: str) -> Dict:
        """Get sector-specific volatility characteristics"""
        return self.SECTOR_VOLATILITY_PROFILES.get(
            sector, 
            {'typical_vol': 'medium', 'beta_range': [0.8, 1.2]}
        )
    
    def _get_index_profile(self, symbol: str) -> Dict:
        """
        Get profile for index symbols which don't have sector/industry data
        
        Args:
            symbol: Index symbol (e.g., 'NIFTY 50', 'BANK NIFTY')
            
        Returns:
            Dictionary with index profile
        """
        try:
            logger.info(f"Generating index profile for {symbol}")
            
            # Index-specific configurations
            index_configs = {
                'NIFTY 50': {
                    'volatility_bucket': 'low',
                    'typical_atr_pct': 1.0,
                    'typical_iv': 12.0,
                    'beta': 1.0,  # NIFTY is the benchmark
                    'yf_symbol': '^NSEI'
                },
                'BANK NIFTY': {
                    'volatility_bucket': 'medium',
                    'typical_atr_pct': 1.8,
                    'typical_iv': 18.0,
                    'beta': 1.2,
                    'yf_symbol': '^NSEBANK'
                },
                'NIFTY FIN SERVICE': {
                    'volatility_bucket': 'medium',
                    'typical_atr_pct': 1.5,
                    'typical_iv': 16.0,
                    'beta': 1.1,
                    'yf_symbol': 'FINNIFTY.NS'
                },
                'NIFTY IT': {
                    'volatility_bucket': 'medium',
                    'typical_atr_pct': 2.2,
                    'typical_iv': 20.0,
                    'beta': 1.1,
                    'yf_symbol': '^CNXIT'
                },
                'NIFTY MIDCAP 50': {
                    'volatility_bucket': 'medium_high',
                    'typical_atr_pct': 2.5,
                    'typical_iv': 22.0,
                    'beta': 1.3,
                    'yf_symbol': 'NIFTYMIDCAP50.NS'
                }
            }
            
            config = index_configs.get(symbol, {})
            
            # Try to get price history for the index (use Dhan API)
            price_data = self._get_price_history(symbol)  # This will now use Dhan API for indexes
            
            # Calculate actual metrics if price data available
            if price_data is not None and not price_data.empty:
                atr_pct = self._calculate_atr_percentage(price_data)
                hv_20 = self._calculate_historical_volatility(price_data, 20)
                spot_price = float(price_data['Close'].iloc[-1])
                logger.info(f"Using real market data for {symbol}: ATR={atr_pct:.2f}%, HV={hv_20:.1f}%, Spot={spot_price:.2f}")
            else:
                # Use typical values if no price data
                atr_pct = config.get('typical_atr_pct', 1.5)
                hv_20 = config.get('typical_iv', 15.0)
                spot_price = 20000  # Default for indices
                logger.warning(f"Using fallback values for {symbol}: ATR={atr_pct:.2f}%, HV={hv_20:.1f}%")
            
            # Get IV from options data if available
            current_iv = config.get('typical_iv', hv_20)
            if self.supabase:
                try:
                    # Try to get IV from option_chain_data
                    response = self.supabase.table('option_chain_data')\
                        .select('implied_volatility')\
                        .eq('symbol', symbol)\
                        .eq('index', True)\
                        .limit(10)\
                        .execute()
                    
                    if response.data:
                        ivs = [float(r['implied_volatility']) for r in response.data if r['implied_volatility']]
                        if ivs:
                            current_iv = np.mean(ivs)
                except Exception as e:
                    logger.warning(f"Could not fetch IV for index {symbol}: {e}")
            
            profile = {
                'symbol': symbol,
                'timestamp': datetime.now(),
                'is_index': True,
                'volatility_bucket': config.get('volatility_bucket', 'medium'),
                'atr_pct': atr_pct,
                'beta_nifty': config.get('beta', 1.0),
                'current_iv': current_iv,
                'hv_20': hv_20,
                'iv_hv_ratio': current_iv / hv_20 if hv_20 > 0 else 1.0,
                'spot_price': spot_price,
                'market_cap_category': 'Index',
                'sector': 'Index',
                'volatility_details': self.VOLATILITY_PROFILES[config.get('volatility_bucket', 'medium')],
                'avg_volume': 0,  # Not applicable for indices
                'price_change_1m': 0,
                'price_change_3m': 0,
                'correlation_nifty': 1.0 if symbol == 'NIFTY 50' else 0.8,
                'relative_strength': 1.0
            }
            
            logger.info(f"Index profile complete for {symbol}: {profile['volatility_bucket']} volatility, "
                       f"ATR%: {profile['atr_pct']:.2f}%, IV: {profile['current_iv']:.1f}%")
            
            return profile
            
        except Exception as e:
            logger.error(f"Error generating index profile for {symbol}: {e}")
            return self._get_default_profile(symbol)
    
    def _get_default_profile(self, symbol: str) -> Dict:
        """Return default profile when data is unavailable"""
        return {
            'symbol': symbol,
            'timestamp': datetime.now(),
            'volatility_bucket': 'medium',
            'atr_pct': 2.0,
            'beta_nifty': 1.0,
            'current_iv': 25.0,
            'hv_20': 25.0,
            'iv_hv_ratio': 1.0,
            'market_cap_category': 'Unknown',
            'volatility_details': self.VOLATILITY_PROFILES['medium'],
            'error': 'Could not fetch complete data'
        }
    
    def calculate_expected_move(self, symbol: str, timeframe_days: int, 
                               profile: Optional[Dict] = None) -> Dict:
        """
        Calculate expected move for a stock over specified timeframe
        
        Args:
            symbol: Stock symbol
            timeframe_days: Number of days for expected move
            profile: Pre-calculated profile (optional)
            
        Returns:
            Dictionary with expected move calculations
        """
        try:
            # Get profile if not provided
            if profile is None:
                profile = self.get_complete_profile(symbol)
            
            spot_price = profile.get('spot_price', 1000)
            current_iv = profile.get('current_iv', 25) / 100  # Convert to decimal
            atr_pct = profile.get('atr_pct', 2) / 100  # Convert to decimal
            hv_20 = profile.get('hv_20', 25) / 100  # Convert to decimal
            beta = profile.get('beta_nifty', 1.0)
            volatility_bucket = profile.get('volatility_bucket', 'medium')
            
            # IV-based move (options market expectation)
            iv_move = spot_price * current_iv * np.sqrt(timeframe_days / 365)
            
            # ATR-based move (recent actual volatility)
            # ATR is daily, so multiply by sqrt of days
            atr_move = spot_price * atr_pct * np.sqrt(timeframe_days)
            
            # HV-based move (historical volatility)
            hv_move = spot_price * hv_20 * np.sqrt(timeframe_days / 252)
            
            # Beta-adjusted market move (assuming NIFTY vol of 15%)
            nifty_vol = 0.15
            nifty_move = spot_price * nifty_vol * np.sqrt(timeframe_days / 252)
            beta_move = nifty_move * beta
            
            # Weighted combination - emphasize realized vol over implied
            base_expected_move = (
                0.30 * iv_move +      # 30% weight to IV
                0.40 * atr_move +     # 40% weight to ATR (recent realized)
                0.20 * hv_move +      # 20% weight to HV
                0.10 * beta_move      # 10% weight to market beta
            )
            
            # Apply volatility bucket multiplier
            multiplier = self.VOLATILITY_PROFILES[volatility_bucket]['expected_move_multiplier']
            adjusted_move = base_expected_move * multiplier
            
            # Calculate percentage moves
            base_pct = (base_expected_move / spot_price) * 100
            adjusted_pct = (adjusted_move / spot_price) * 100
            
            return {
                'timeframe_days': timeframe_days,
                'base_expected_move': round(base_expected_move, 2),
                'base_expected_pct': round(base_pct, 2),
                'adjusted_expected_move': round(adjusted_move, 2),
                'adjusted_expected_pct': round(adjusted_pct, 2),
                'upper_expected': round(spot_price + adjusted_move, 2),
                'lower_expected': round(spot_price - adjusted_move, 2),
                'components': {
                    'iv_move': round(iv_move, 2),
                    'atr_move': round(atr_move, 2),
                    'hv_move': round(hv_move, 2),
                    'beta_move': round(beta_move, 2)
                },
                'volatility_multiplier': multiplier
            }
            
        except Exception as e:
            logger.error(f"Error calculating expected move for {symbol}: {e}")
            # Return conservative default
            return {
                'timeframe_days': timeframe_days,
                'base_expected_move': spot_price * 0.02 * np.sqrt(timeframe_days),
                'base_expected_pct': 2.0 * np.sqrt(timeframe_days),
                'error': str(e)
            }
    
    def get_strategy_preferences(self, symbol: str, profile: Optional[Dict] = None) -> Dict:
        """
        Get strategy preferences based on stock profile
        
        Args:
            symbol: Stock symbol
            profile: Pre-calculated profile (optional)
            
        Returns:
            Dictionary with strategy preferences and parameters
        """
        try:
            # Get profile if not provided
            if profile is None:
                profile = self.get_complete_profile(symbol)
            
            volatility_bucket = profile.get('volatility_bucket', 'medium')
            beta = profile.get('beta_nifty', 1.0)
            
            # Get base preferences from volatility profile
            vol_profile = self.VOLATILITY_PROFILES[volatility_bucket]
            
            preferences = {
                'symbol': symbol,
                'volatility_bucket': volatility_bucket,
                'preferred_strategies': vol_profile['preferred_strategies'].copy(),
                'avoid_strategies': vol_profile['avoid_strategies'].copy(),
                'position_size_multiplier': vol_profile['position_size_multiplier'],
                'min_spread_width': vol_profile['min_spread_width'],
                'min_probability_threshold': vol_profile['min_probability_threshold'],
                'expected_move_multiplier': vol_profile['expected_move_multiplier']
            }
            
            # Beta adjustments
            if beta > 1.5:
                preferences['beta_adjustment'] = 'high_beta'
                preferences['beta_position_adjustment'] = 0.8  # Reduce size
            elif beta < 0.5:
                preferences['beta_adjustment'] = 'low_beta'
                preferences['beta_position_adjustment'] = 1.2  # Increase size
            else:
                preferences['beta_adjustment'] = 'normal_beta'
                preferences['beta_position_adjustment'] = 1.0
            
            # Add profile summary
            preferences['profile_summary'] = {
                'atr_pct': profile.get('atr_pct', 0),
                'beta': beta,
                'iv_hv_ratio': profile.get('iv_hv_ratio', 1),
                'market_cap_category': profile.get('market_cap_category', 'Unknown')
            }
            
            return preferences
            
        except Exception as e:
            logger.error(f"Error getting strategy preferences for {symbol}: {e}")
            return {
                'symbol': symbol,
                'volatility_bucket': 'medium',
                'preferred_strategies': ['Iron Condor', 'Bull Put Spread'],
                'avoid_strategies': [],
                'error': str(e)
            }