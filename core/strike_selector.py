"""
Intelligent Strike Selection System
Centralized strike selection for all options strategies
Selects optimal strikes based on expected moves, timeframe, and risk/reward
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class StrikeSelectionMode(Enum):
    """Strike selection modes"""
    EXACT = "exact"           # Must match exactly
    NEAREST = "nearest"       # Find nearest available
    FLEXIBLE = "flexible"     # Allow tolerance range
    LIQUIDITY = "liquidity"   # Prioritize liquid strikes

@dataclass
class StrikeConstraint:
    """Constraints for strike selection"""
    min_delta: Optional[float] = None
    max_delta: Optional[float] = None
    min_moneyness: Optional[float] = None  # (strike - spot) / spot
    max_moneyness: Optional[float] = None
    min_liquidity: int = 0  # Minimum open interest
    max_distance_pct: float = 0.10  # Max 10% from target by default
    mode: StrikeSelectionMode = StrikeSelectionMode.FLEXIBLE

@dataclass
class StrikeRequest:
    """Request for strike selection"""
    name: str  # e.g., 'long_strike', 'short_strike'
    option_type: str  # 'CALL' or 'PUT'
    target_type: str  # 'atm', 'otm', 'itm', 'expected_move', 'delta', 'moneyness'
    target_value: Optional[float] = None  # Value for delta/moneyness targets
    constraint: Optional[StrikeConstraint] = None

class IntelligentStrikeSelector:
    """
    Centralized strike selection for all options strategies
    
    Key features:
    - Strategy-agnostic strike selection based on requirements
    - Intelligent fallback mechanisms
    - Consistent liquidity and availability checks
    - Support for all strategy types
    """
    
    def __init__(self, stock_profiler=None):
        # Initialize stock profiler for dynamic expected moves
        if stock_profiler is None:
            try:
                from .stock_profiler import StockProfiler
                self.stock_profiler = StockProfiler()
            except ImportError:
                logger.warning("StockProfiler not available, using fallback calculations")
                self.stock_profiler = None
        else:
            self.stock_profiler = stock_profiler
            
        # Timeframe multipliers for expected moves
        self.timeframe_multipliers = {
            '1-5 days': 0.3,      # Use 30% of 1SD move
            '5-10 days': 0.5,     # Use 50% of 1SD move
            '10-20 days': 0.75,   # Use 75% of 1SD move
            '20-30 days': 1.0,    # Use full 1SD move
            '30+ days': 1.25      # Use 125% of 1SD move
        }
        
        # Strategy-specific adjustments for expected moves
        self.strategy_adjustments = {
            'Long Call': {'multiplier': 0.8},      # Slightly OTM
            'Long Put': {'multiplier': 0.8},       # Slightly OTM
            'Bull Call Spread': {'multiplier': 1.0},
            'Bear Put Spread': {'multiplier': 1.0},
            'Bull Put Spread': {'multiplier': 0.7},  # More conservative
            'Bear Call Spread': {'multiplier': 0.7}, # More conservative
            'Iron Condor': {'multiplier': 1.2},     # Wider strikes
            'Iron Butterfly': {'multiplier': 0.5},  # Tighter strikes
            'Butterfly Spread': {'multiplier': 0.5},
            'Long Straddle': {'multiplier': 0.0},   # ATM
            'Short Straddle': {'multiplier': 0.0},  # ATM
            'Long Strangle': {'multiplier': 1.0},
            'Short Strangle': {'multiplier': 1.2},
            'Calendar Spread': {'multiplier': 0.0}, # ATM
            'Diagonal Spread': {'multiplier': 0.5},
            'Cash-Secured Put': {'multiplier': 0.8},
            'Covered Call': {'multiplier': 0.8}
        }
        
        # Strategy configurations - what strikes each strategy needs
        self.strategy_configs = {
            # Directional Strategies
            'Long Call': [
                StrikeRequest('strike', 'CALL', 'otm', 0.02, 
                             StrikeConstraint(min_moneyness=0.0, max_moneyness=0.05))
            ],
            'Long Put': [
                StrikeRequest('strike', 'PUT', 'otm', 0.02,
                             StrikeConstraint(min_moneyness=-0.05, max_moneyness=0.0))
            ],
            
            # Vertical Spreads
            'Bull Call Spread': [
                StrikeRequest('long_strike', 'CALL', 'atm', None,
                             StrikeConstraint(min_moneyness=-0.02, max_moneyness=0.02)),
                StrikeRequest('short_strike', 'CALL', 'expected_move', 0.8,
                             StrikeConstraint(min_moneyness=0.02, max_moneyness=0.10))
            ],
            'Bear Put Spread': [
                StrikeRequest('long_strike', 'PUT', 'atm', None,
                             StrikeConstraint(min_moneyness=-0.02, max_moneyness=0.02)),
                StrikeRequest('short_strike', 'PUT', 'expected_move', -0.8,
                             StrikeConstraint(min_moneyness=-0.10, max_moneyness=-0.02))
            ],
            'Bull Put Spread': [
                StrikeRequest('short_strike', 'PUT', 'expected_move', -0.5,
                             StrikeConstraint(min_moneyness=-0.08, max_moneyness=-0.02)),
                StrikeRequest('long_strike', 'PUT', 'expected_move', -1.2,
                             StrikeConstraint(min_moneyness=-0.15, max_moneyness=-0.08))
            ],
            'Bear Call Spread': [
                StrikeRequest('short_strike', 'CALL', 'expected_move', 0.5,
                             StrikeConstraint(min_moneyness=0.02, max_moneyness=0.08)),
                StrikeRequest('long_strike', 'CALL', 'expected_move', 1.2,
                             StrikeConstraint(min_moneyness=0.08, max_moneyness=0.15))
            ],
            
            # Neutral Strategies
            'Iron Condor': [
                StrikeRequest('put_short', 'PUT', 'expected_move', -1.0,
                             StrikeConstraint(min_moneyness=-0.10, max_moneyness=-0.03)),
                StrikeRequest('put_long', 'PUT', 'expected_move', -1.5,
                             StrikeConstraint(min_moneyness=-0.20, max_moneyness=-0.10)),
                StrikeRequest('call_short', 'CALL', 'expected_move', 1.0,
                             StrikeConstraint(min_moneyness=0.03, max_moneyness=0.10)),
                StrikeRequest('call_long', 'CALL', 'expected_move', 1.5,
                             StrikeConstraint(min_moneyness=0.10, max_moneyness=0.20))
            ],
            'Iron Butterfly': [
                StrikeRequest('atm_strike', 'CALL', 'atm', None,
                             StrikeConstraint(min_moneyness=-0.01, max_moneyness=0.01)),
                StrikeRequest('put_long', 'PUT', 'expected_move', -1.0,
                             StrikeConstraint(min_moneyness=-0.10, max_moneyness=-0.03)),
                StrikeRequest('call_long', 'CALL', 'expected_move', 1.0,
                             StrikeConstraint(min_moneyness=0.03, max_moneyness=0.10))
            ],
            'Butterfly Spread': [
                StrikeRequest('atm_strike', 'CALL', 'atm', None,
                             StrikeConstraint(min_moneyness=-0.01, max_moneyness=0.01)),
                StrikeRequest('lower_strike', 'CALL', 'expected_move', -0.5,
                             StrikeConstraint(min_moneyness=-0.08, max_moneyness=-0.02)),
                StrikeRequest('upper_strike', 'CALL', 'expected_move', 0.5,
                             StrikeConstraint(min_moneyness=0.02, max_moneyness=0.08))
            ],
            
            # Volatility Strategies
            'Long Straddle': [
                StrikeRequest('strike', 'BOTH', 'atm', None,
                             StrikeConstraint(min_moneyness=-0.01, max_moneyness=0.01, min_liquidity=100))
            ],
            'Short Straddle': [
                StrikeRequest('strike', 'BOTH', 'atm', None,
                             StrikeConstraint(min_moneyness=-0.01, max_moneyness=0.01, min_liquidity=200))
            ],
            'Long Strangle': [
                StrikeRequest('put_strike', 'PUT', 'expected_move', -0.5,
                             StrikeConstraint(min_moneyness=-0.08, max_moneyness=-0.02)),
                StrikeRequest('call_strike', 'CALL', 'expected_move', 0.5,
                             StrikeConstraint(min_moneyness=0.02, max_moneyness=0.08))
            ],
            'Short Strangle': [
                StrikeRequest('put_strike', 'PUT', 'expected_move', -0.7,
                             StrikeConstraint(min_moneyness=-0.10, max_moneyness=-0.03, min_liquidity=100)),
                StrikeRequest('call_strike', 'CALL', 'expected_move', 0.7,
                             StrikeConstraint(min_moneyness=0.03, max_moneyness=0.10, min_liquidity=100))
            ],
            
            # Income Strategies
            'Cash-Secured Put': [
                StrikeRequest('strike', 'PUT', 'expected_move', -0.3,
                             StrikeConstraint(min_moneyness=-0.08, max_moneyness=-0.01, min_liquidity=50))
            ],
            'Covered Call': [
                StrikeRequest('strike', 'CALL', 'expected_move', 0.3,
                             StrikeConstraint(min_moneyness=0.01, max_moneyness=0.08, min_liquidity=50))
            ],
            
            # Advanced Strategies
            'Calendar Spread': [
                StrikeRequest('strike', 'BOTH', 'atm', None,
                             StrikeConstraint(min_moneyness=-0.02, max_moneyness=0.02, min_liquidity=100))
            ],
            'Diagonal Spread': [
                StrikeRequest('short_strike', 'CALL', 'expected_move', 0.5,
                             StrikeConstraint(min_moneyness=0.02, max_moneyness=0.08)),
                StrikeRequest('long_strike', 'CALL', 'atm', None,
                             StrikeConstraint(min_moneyness=-0.02, max_moneyness=0.02))
            ],
            'Call Ratio Spread': [
                StrikeRequest('long_strike', 'CALL', 'atm', None,
                             StrikeConstraint(min_moneyness=-0.02, max_moneyness=0.02)),
                StrikeRequest('short_strike', 'CALL', 'expected_move', 0.7,
                             StrikeConstraint(min_moneyness=0.03, max_moneyness=0.10, min_liquidity=100))
            ],
            'Put Ratio Spread': [
                StrikeRequest('long_strike', 'PUT', 'atm', None,
                             StrikeConstraint(min_moneyness=-0.02, max_moneyness=0.02)),
                StrikeRequest('short_strike', 'PUT', 'expected_move', -0.7,
                             StrikeConstraint(min_moneyness=-0.10, max_moneyness=-0.03, min_liquidity=100))
            ],
            'Jade Lizard': [
                StrikeRequest('put_strike', 'PUT', 'expected_move', -0.5,
                             StrikeConstraint(min_moneyness=-0.08, max_moneyness=-0.02)),
                StrikeRequest('call_short', 'CALL', 'expected_move', 0.5,
                             StrikeConstraint(min_moneyness=0.02, max_moneyness=0.08)),
                StrikeRequest('call_long', 'CALL', 'expected_move', 1.0,
                             StrikeConstraint(min_moneyness=0.08, max_moneyness=0.15))
            ],
            'Broken Wing Butterfly': [
                StrikeRequest('atm_strike', 'PUT', 'atm', None,
                             StrikeConstraint(min_moneyness=-0.01, max_moneyness=0.01)),
                StrikeRequest('lower_strike', 'PUT', 'expected_move', -0.7,
                             StrikeConstraint(min_moneyness=-0.10, max_moneyness=-0.03)),
                StrikeRequest('upper_strike', 'PUT', 'expected_move', 0.3,
                             StrikeConstraint(min_moneyness=0.01, max_moneyness=0.05))
            ]
        }
    
    def get_smart_expiry_date(self, base_date=None, cutoff_day=20):
        """
        Get expiry date using smart 20th date cutoff logic
        
        Args:
            base_date: Base date for calculation (default: now)
            cutoff_day: Cutoff day of month (default: 20)
        
        Returns:
            datetime: Expiry date (last Thursday of target month)
        """
        import calendar
        from datetime import datetime
        
        if base_date is None:
            base_date = datetime.now()
        
        # Helper function to get last Thursday of a month
        def get_last_thursday(year, month):
            # Get last day of month
            last_day = calendar.monthrange(year, month)[1]
            # Find last Thursday
            for day in range(last_day, 0, -1):
                if datetime(year, month, day).weekday() == 3:  # Thursday = 3
                    return datetime(year, month, day)
            return None
        
        current_day = base_date.day
        
        # If before cutoff day of month: try current month expiry
        if current_day <= cutoff_day:
            target_month = base_date.month
            target_year = base_date.year
            
            # Check if current month's expiry is still valid (hasn't passed)
            current_month_expiry = get_last_thursday(target_year, target_month)
            if current_month_expiry and current_month_expiry.date() > base_date.date():
                logger.info(f"Using current month expiry (day {current_day} <= cutoff {cutoff_day}): {current_month_expiry.strftime('%Y-%m-%d')}")
                return current_month_expiry
            else:
                # Current month expiry has passed, use next month
                logger.info(f"Current month expiry has passed, using next month")
                if target_month == 12:
                    target_month = 1
                    target_year += 1
                else:
                    target_month += 1
        else:
            # After cutoff day: use next month expiry
            logger.info(f"Using next month expiry (day {current_day} > cutoff {cutoff_day})")
            if base_date.month == 12:
                target_month = 1
                target_year = base_date.year + 1
            else:
                target_month = base_date.month + 1
                target_year = base_date.year
        
        target_expiry = get_last_thursday(target_year, target_month)
        logger.info(f"Selected expiry date: {target_expiry.strftime('%Y-%m-%d')}")
        return target_expiry
    
    def select_optimal_strike(self, options_df: pd.DataFrame, spot_price: float,
                            market_analysis: Dict, strategy_type: str,
                            option_type: str = 'CALL') -> float:
        """
        Select optimal strike based on expected moves and strategy requirements
        
        Args:
            options_df: Options chain data
            spot_price: Current spot price
            market_analysis: Market analysis including expected moves
            strategy_type: Type of strategy (e.g., 'Long Call')
            option_type: 'CALL' or 'PUT'
            
        Returns:
            Optimal strike price
        """
        try:
            # Extract expected moves - use dynamic calculation if available
            symbol = market_analysis.get('symbol', '')
            if self.stock_profiler and symbol:
                # Get dynamic expected move
                timeframe = market_analysis.get('timeframe', {}).get('duration', '10-30 days')
                days = self._extract_days_from_timeframe(timeframe)
                expected_move_data = self.stock_profiler.calculate_expected_move(symbol, days)
                one_sd_move = expected_move_data.get('adjusted_expected_move', spot_price * 0.05)
            else:
                # Fallback to static calculation
                expected_moves = market_analysis.get('price_levels', {}).get('expected_moves', {})
                one_sd_move = expected_moves.get('one_sd_move', spot_price * 0.05)
            
            # Extract timeframe
            timeframe = market_analysis.get('timeframe', {}).get('duration', '10-30 days')
            timeframe_mult = self.timeframe_multipliers.get(timeframe, 0.75)
            
            # Get strategy-specific adjustments
            strategy_config = self.strategy_adjustments.get(strategy_type, {})
            strategy_mult = strategy_config.get('multiplier', 1.0)
            
            # Calculate target price based on strategy and expected moves
            if strategy_type in ['Long Call', 'Bull Call Spread', 'Bull Put Spread']:
                # Bullish strategies
                target_move = one_sd_move * timeframe_mult * strategy_mult
                target_price = spot_price + target_move
            elif strategy_type in ['Long Put', 'Bear Put Spread', 'Bear Call Spread']:
                # Bearish strategies
                target_move = one_sd_move * timeframe_mult * strategy_mult
                target_price = spot_price - target_move
            else:
                # Neutral strategies - prefer ATM
                target_price = spot_price
            
            # Find nearest available strike
            strike = self._find_optimal_strike_near_target(
                options_df, target_price, option_type, spot_price
            )
            
            # Validate strike selection
            if self._validate_strike_selection(strike, spot_price, option_type, strategy_type):
                logger.info(f"Selected {option_type} strike {strike} for {strategy_type} "
                          f"(Target: {target_price:.2f}, Expected move: {one_sd_move:.2f})")
                return strike
            else:
                # Fallback to traditional selection
                return self._fallback_strike_selection(options_df, spot_price, option_type)
                
        except Exception as e:
            logger.error(f"Error in strike selection: {e}")
            return self._fallback_strike_selection(options_df, spot_price, option_type)
    
    def select_spread_strikes(self, options_df: pd.DataFrame, spot_price: float,
                            market_analysis: Dict, strategy_type: str) -> Tuple[float, float]:
        """
        Select optimal strikes for spread strategies
        
        Returns:
            Tuple of (short_strike, long_strike)
        """
        try:
            # Get dynamic expected moves
            symbol = market_analysis.get('symbol', '')
            if self.stock_profiler and symbol:
                timeframe = market_analysis.get('timeframe', {}).get('duration', '10-30 days')
                days = self._extract_days_from_timeframe(timeframe)
                expected_move_data = self.stock_profiler.calculate_expected_move(symbol, days)
                one_sd_move = expected_move_data.get('adjusted_expected_move', spot_price * 0.05)
                two_sd_move = one_sd_move * 2  # Approximate 2 SD as 2x 1 SD
            else:
                # Fallback
                expected_moves = market_analysis.get('price_levels', {}).get('expected_moves', {})
                one_sd_move = expected_moves.get('one_sd_move', spot_price * 0.05)
                two_sd_move = expected_moves.get('two_sd_move', spot_price * 0.10)
            
            timeframe = market_analysis.get('timeframe', {}).get('duration', '10-30 days')
            timeframe_mult = self.timeframe_multipliers.get(timeframe, 0.75)
            
            if 'Bull' in strategy_type:
                # Bull spreads
                if 'Call' in strategy_type:
                    # Bull Call Spread: Buy ATM/ITM, Sell OTM
                    long_strike = self._find_optimal_strike_near_target(
                        options_df, spot_price, 'CALL', spot_price
                    )
                    short_target = spot_price + (one_sd_move * timeframe_mult * 0.8)
                    short_strike = self._find_optimal_strike_near_target(
                        options_df, short_target, 'CALL', spot_price
                    )
                else:
                    # Bull Put Spread: Sell OTM Put, Buy further OTM Put
                    short_target = spot_price - (one_sd_move * timeframe_mult * 0.5)
                    short_strike = self._find_optimal_strike_near_target(
                        options_df, short_target, 'PUT', spot_price
                    )
                    long_target = spot_price - (one_sd_move * timeframe_mult * 1.2)
                    long_strike = self._find_optimal_strike_near_target(
                        options_df, long_target, 'PUT', spot_price
                    )
                    
            elif 'Bear' in strategy_type:
                # Bear spreads
                if 'Put' in strategy_type:
                    # Bear Put Spread: Buy ATM/ITM, Sell OTM
                    long_strike = self._find_optimal_strike_near_target(
                        options_df, spot_price, 'PUT', spot_price
                    )
                    short_target = spot_price - (one_sd_move * timeframe_mult * 0.8)
                    short_strike = self._find_optimal_strike_near_target(
                        options_df, short_target, 'PUT', spot_price
                    )
                else:
                    # Bear Call Spread: Sell OTM Call, Buy further OTM Call
                    short_target = spot_price + (one_sd_move * timeframe_mult * 0.5)
                    short_strike = self._find_optimal_strike_near_target(
                        options_df, short_target, 'CALL', spot_price
                    )
                    long_target = spot_price + (one_sd_move * timeframe_mult * 1.2)
                    long_strike = self._find_optimal_strike_near_target(
                        options_df, long_target, 'CALL', spot_price
                    )
            
            return (short_strike, long_strike)
            
        except Exception as e:
            logger.error(f"Error selecting spread strikes: {e}")
            # Fallback to nearest strikes
            return self._fallback_spread_selection(options_df, spot_price, strategy_type)
    
    def _find_optimal_strike_near_target(self, options_df: pd.DataFrame, 
                                       target_price: float, option_type: str,
                                       spot_price: float) -> float:
        """Find the optimal strike near target price with good liquidity"""
        try:
            # Filter for option type and liquidity
            type_options = options_df[
                (options_df['option_type'] == option_type) &
                (options_df['open_interest'] >= 100) &  # Minimum liquidity
                (options_df['volume'] > 0)              # Some trading activity
            ].copy()
            
            if type_options.empty:
                # Relax liquidity requirements
                type_options = options_df[
                    options_df['option_type'] == option_type
                ].copy()
            
            if type_options.empty:
                return spot_price
            
            # Calculate distance from target
            type_options['distance'] = abs(type_options['strike'] - target_price)
            
            # Prefer strikes with better liquidity
            max_oi = type_options['open_interest'].max()
            if max_oi > 0:
                type_options['liquidity_score'] = (
                    type_options['open_interest'] + type_options['volume']
                ) / max_oi
            else:
                type_options['liquidity_score'] = 0
            
            # Combined score: 70% distance, 30% liquidity
            max_distance = type_options['distance'].max()
            if max_distance > 0:
                type_options['score'] = (
                    0.7 * (1 - type_options['distance'] / max_distance) +
                    0.3 * type_options['liquidity_score']
                )
            else:
                # All strikes at same distance, use liquidity only
                type_options['score'] = type_options['liquidity_score']
            
            # Get best strike
            if type_options.empty or type_options['score'].isna().all():
                # Fall back to simple nearest strike if no valid scores
                return self._simple_nearest_strike(options_df, target_price, option_type)
            
            best_idx = type_options['score'].idxmax()
            return float(type_options.loc[best_idx, 'strike'])
            
        except Exception as e:
            logger.error(f"Error finding optimal strike: {e}")
            return self._simple_nearest_strike(options_df, target_price, option_type)
    
    def _validate_strike_selection(self, strike: float, spot_price: float,
                                  option_type: str, strategy_type: str) -> bool:
        """Validate if the selected strike makes sense"""
        try:
            moneyness = (strike - spot_price) / spot_price
            
            # Strategy-specific validation
            if 'Long' in strategy_type:
                if option_type == 'CALL':
                    # Long calls should be OTM to slightly ITM
                    return -0.05 <= moneyness <= 0.10
                else:  # PUT
                    # Long puts should be OTM to slightly ITM
                    return -0.10 <= moneyness <= 0.05
            
            # Spreads have wider acceptable range
            return -0.15 <= moneyness <= 0.15
            
        except:
            return True
    
    def _fallback_strike_selection(self, options_df: pd.DataFrame,
                                  spot_price: float, option_type: str) -> float:
        """Fallback to simple ATM selection"""
        try:
            type_options = options_df[options_df['option_type'] == option_type]
            if type_options.empty:
                return spot_price
                
            strikes = type_options['strike'].unique()
            return min(strikes, key=lambda x: abs(x - spot_price))
            
        except:
            return spot_price
    
    def _simple_nearest_strike(self, options_df: pd.DataFrame,
                             target_price: float, option_type: str) -> float:
        """Simple nearest strike selection"""
        try:
            type_options = options_df[options_df['option_type'] == option_type]
            strikes = type_options['strike'].unique()
            return min(strikes, key=lambda x: abs(x - target_price))
        except:
            return target_price
    
    def _fallback_spread_selection(self, options_df: pd.DataFrame,
                                  spot_price: float, strategy_type: str) -> Tuple[float, float]:
        """Fallback spread strike selection"""
        try:
            if 'Call' in strategy_type:
                strikes = sorted(options_df[options_df['option_type'] == 'CALL']['strike'].unique())
            else:
                strikes = sorted(options_df[options_df['option_type'] == 'PUT']['strike'].unique())
            
            atm_idx = min(range(len(strikes)), key=lambda i: abs(strikes[i] - spot_price))
            
            if 'Bull' in strategy_type:
                if atm_idx < len(strikes) - 1:
                    return (strikes[atm_idx], strikes[atm_idx + 1])
            else:  # Bear
                if atm_idx > 0:
                    return (strikes[atm_idx], strikes[atm_idx - 1])
            
            return (strikes[atm_idx], strikes[atm_idx])
            
        except:
            return (spot_price, spot_price)
    
    def _extract_days_from_timeframe(self, timeframe: str) -> int:
        """Extract number of days from timeframe string"""
        try:
            # Handle different timeframe formats
            if '1-5 days' in timeframe:
                return 3  # Use midpoint
            elif '5-10 days' in timeframe:
                return 7
            elif '10-20 days' in timeframe:
                return 15
            elif '20-30 days' in timeframe:
                return 25
            elif '30+ days' in timeframe or '30-60 days' in timeframe:
                return 45
            else:
                # Try to extract first number
                import re
                numbers = re.findall(r'\d+', timeframe)
                if numbers:
                    return int(numbers[0])
                else:
                    return 20  # Default to 20 days
        except Exception as e:
            logger.error(f"Error extracting days from timeframe '{timeframe}': {e}")
            return 20  # Default fallback
    
    def select_strikes(self, strategy_type: str, options_df: pd.DataFrame, 
                      spot_price: float, market_analysis: Dict,
                      custom_config: Optional[List[StrikeRequest]] = None) -> Dict[str, float]:
        """
        Universal entry point for all strike selection
        
        Args:
            strategy_type: Name of the strategy
            options_df: Options chain data
            spot_price: Current spot price
            market_analysis: Market analysis data
            custom_config: Optional custom strike configuration
            
        Returns:
            Dictionary mapping strike names to selected strikes
        """
        try:
            # Get strategy configuration
            strike_requests = custom_config or self.strategy_configs.get(strategy_type, [])
            
            if not strike_requests:
                logger.warning(f"No configuration found for strategy {strategy_type}")
                return {}
            
            # Process each strike request
            selected_strikes = {}
            available_strikes = self._get_available_strikes(options_df)
            
            for request in strike_requests:
                strike = self._select_single_strike(
                    request, options_df, spot_price, market_analysis, available_strikes
                )
                
                if strike is not None:
                    selected_strikes[request.name] = strike
                    
                    # Handle BOTH option type (for straddles/strangles)
                    if request.option_type == 'BOTH':
                        selected_strikes[f"{request.name}_put"] = strike
                        selected_strikes[f"{request.name}_call"] = strike
                else:
                    logger.error(f"Failed to find strike for {request.name} in {strategy_type}")
                    # Try relaxed constraints
                    relaxed_request = self._relax_constraints(request)
                    strike = self._select_single_strike(
                        relaxed_request, options_df, spot_price, market_analysis, available_strikes
                    )
                    if strike is not None:
                        selected_strikes[request.name] = strike
                        logger.warning(f"Used relaxed constraints for {request.name}")
            
            # Validate strike relationships
            if not self._validate_strike_relationships(selected_strikes, strategy_type):
                logger.warning(f"Strike relationships invalid for {strategy_type}, attempting to fix")
                selected_strikes = self._fix_strike_relationships(selected_strikes, strategy_type, options_df)
            
            return selected_strikes
            
        except Exception as e:
            logger.error(f"Error in centralized strike selection: {e}")
            return self._emergency_fallback(strategy_type, options_df, spot_price)
    
    def _select_single_strike(self, request: StrikeRequest, options_df: pd.DataFrame,
                            spot_price: float, market_analysis: Dict,
                            available_strikes: Dict[str, List[float]]) -> Optional[float]:
        """
        Select a single strike based on request parameters
        """
        try:
            # Calculate target price based on request type
            target_price = self._calculate_target_price(
                request, spot_price, market_analysis
            )
            
            # Get candidate strikes
            candidates = self._get_candidate_strikes(
                request, target_price, spot_price, options_df, available_strikes
            )
            
            if candidates.empty:
                logger.warning(f"No candidate strikes found for {request.name}")
                return None
            
            # Score and select best strike
            if len(candidates) > 0:
                best_strike = self._score_and_select_strike(
                    candidates, target_price, request.constraint
                )
                return best_strike
            else:
                return None
            
        except Exception as e:
            logger.error(f"Error selecting single strike: {e}")
            return None
    
    def _calculate_target_price(self, request: StrikeRequest, spot_price: float,
                              market_analysis: Dict) -> float:
        """
        Calculate target price based on request type using dynamic expected moves
        """
        if request.target_type == 'atm':
            return spot_price
            
        elif request.target_type == 'expected_move':
            # Use stock profiler for dynamic expected moves if available
            if self.stock_profiler and hasattr(market_analysis, 'get'):
                symbol = market_analysis.get('symbol', '')
                if symbol:
                    # Get timeframe in days
                    timeframe = market_analysis.get('timeframe', {}).get('duration', '10-30 days')
                    if '30+' in timeframe:
                        days = 30
                    elif '-' in timeframe:
                        # Extract average from range
                        parts = timeframe.split('-')
                        try:
                            days = (int(parts[0]) + int(parts[1].split()[0])) // 2
                        except:
                            days = 15
                    else:
                        days = 15  # Default
                    
                    # Get expected move from profiler
                    expected_move_data = self.stock_profiler.calculate_expected_move(symbol, days)
                    expected_move = expected_move_data.get('adjusted_expected_move', spot_price * 0.05)
                    
                    # Apply request multiplier
                    move = expected_move * (request.target_value or 1.0)
                    return spot_price + move
            
            # Fallback to original logic if profiler not available
            expected_moves = market_analysis.get('price_levels', {}).get('expected_moves', {})
            one_sd_move = expected_moves.get('one_sd_move', spot_price * 0.05)
            timeframe = market_analysis.get('timeframe', {}).get('duration', '10-30 days')
            timeframe_mult = self.timeframe_multipliers.get(timeframe, 0.75)
            
            move = one_sd_move * timeframe_mult * (request.target_value or 1.0)
            return spot_price + move
            
        elif request.target_type == 'moneyness':
            return spot_price * (1 + (request.target_value or 0))
            
        elif request.target_type == 'otm':
            if request.option_type == 'CALL':
                return spot_price * (1 + (request.target_value or 0.03))
            else:  # PUT
                return spot_price * (1 - (request.target_value or 0.03))
                
        elif request.target_type == 'itm':
            if request.option_type == 'CALL':
                return spot_price * (1 - (request.target_value or 0.03))
            else:  # PUT
                return spot_price * (1 + (request.target_value or 0.03))
                
        else:
            return spot_price
    
    def _get_candidate_strikes(self, request: StrikeRequest, target_price: float,
                             spot_price: float, options_df: pd.DataFrame,
                             available_strikes: Dict[str, List[float]]) -> pd.DataFrame:
        """
        Get candidate strikes that meet constraints
        """
        try:
            # Filter by option type
            if request.option_type == 'BOTH':
                # For straddles/strangles, use calls as reference
                candidates = options_df[options_df['option_type'] == 'CALL'].copy()
            else:
                candidates = options_df[options_df['option_type'] == request.option_type].copy()
            
            if candidates.empty:
                return pd.DataFrame()
            
            # Apply constraints
            if request.constraint is None:
                constraint = StrikeConstraint()
            elif isinstance(request.constraint, dict):
                constraint = StrikeConstraint(**request.constraint)
            else:
                constraint = request.constraint
            
            # Liquidity filter
            if constraint.min_liquidity > 0:
                candidates = candidates[candidates['open_interest'] >= constraint.min_liquidity]
            
            # Moneyness filter
            candidates['moneyness'] = (candidates['strike'] - spot_price) / spot_price
            
            if constraint.min_moneyness is not None:
                candidates = candidates[candidates['moneyness'] >= constraint.min_moneyness]
            if constraint.max_moneyness is not None:
                candidates = candidates[candidates['moneyness'] <= constraint.max_moneyness]
            
            # Distance from target filter
            candidates['distance_pct'] = abs(candidates['strike'] - target_price) / target_price
            candidates = candidates[candidates['distance_pct'] <= constraint.max_distance_pct]
            
            return candidates
            
        except Exception as e:
            logger.error(f"Error getting candidate strikes: {e}")
            return pd.DataFrame()
    
    def _score_and_select_strike(self, candidates: pd.DataFrame, target_price: float,
                               constraint: Optional[StrikeConstraint]) -> Optional[float]:
        """
        Score candidates and select best strike
        """
        try:
            if candidates.empty:
                return None
            
            # Calculate scores
            candidates = candidates.copy()
            
            # Distance score (40% weight)
            max_distance = candidates['distance_pct'].max()
            if max_distance > 0:
                candidates['distance_score'] = 1 - (candidates['distance_pct'] / max_distance)
            else:
                candidates['distance_score'] = 1.0
            
            # Liquidity score (30% weight)
            max_oi = candidates['open_interest'].max()
            if max_oi > 0:
                candidates['liquidity_score'] = candidates['open_interest'] / max_oi
            else:
                candidates['liquidity_score'] = 0.5
            
            # Spread score (20% weight) - tighter spreads are better
            if 'bid' in candidates.columns and 'ask' in candidates.columns:
                candidates['spread'] = candidates['ask'] - candidates['bid']
                candidates['spread_pct'] = candidates['spread'] / candidates['ask'].clip(lower=0.01)
                candidates['spread_score'] = 1 - candidates['spread_pct'].clip(upper=1.0)
            else:
                candidates['spread_score'] = 0.5
            
            # Volume score (10% weight) - recent activity
            max_volume = candidates['volume'].max() if 'volume' in candidates.columns else 0
            if max_volume > 0:
                candidates['volume_score'] = candidates['volume'] / max_volume
            else:
                candidates['volume_score'] = 0.5
            
            # Calculate total score
            candidates['total_score'] = (
                0.40 * candidates['distance_score'] +
                0.30 * candidates['liquidity_score'] +
                0.20 * candidates['spread_score'] +
                0.10 * candidates['volume_score']
            )
            
            # Select best strike
            best_idx = candidates['total_score'].idxmax()
            return float(candidates.loc[best_idx, 'strike'])
            
        except Exception as e:
            logger.error(f"Error scoring strikes: {e}")
            # Fallback to nearest strike
            if not candidates.empty:
                return float(candidates.iloc[0]['strike'])
            return None
    
    def _get_available_strikes(self, options_df: pd.DataFrame) -> Dict[str, List[float]]:
        """
        Get all available strikes by option type
        """
        available = {}
        for opt_type in ['CALL', 'PUT']:
            strikes = sorted(options_df[options_df['option_type'] == opt_type]['strike'].unique())
            available[opt_type] = strikes
        return available
    
    def _relax_constraints(self, request: StrikeRequest) -> StrikeRequest:
        """
        Relax constraints for better strike availability
        """
        relaxed = StrikeRequest(
            name=request.name,
            option_type=request.option_type,
            target_type=request.target_type,
            target_value=request.target_value
        )
        
        if request.constraint:
            relaxed_constraint = StrikeConstraint(
                min_delta=None,  # Remove delta constraints
                max_delta=None,
                min_moneyness=request.constraint.min_moneyness * 1.5 if request.constraint.min_moneyness else None,
                max_moneyness=request.constraint.max_moneyness * 1.5 if request.constraint.max_moneyness else None,
                min_liquidity=max(0, request.constraint.min_liquidity // 2),  # Halve liquidity requirement
                max_distance_pct=min(0.20, request.constraint.max_distance_pct * 2),  # Double distance tolerance
                mode=StrikeSelectionMode.NEAREST
            )
            relaxed.constraint = relaxed_constraint
        
        return relaxed
    
    def _validate_strike_relationships(self, strikes: Dict[str, float], strategy_type: str) -> bool:
        """
        Validate that strike relationships make sense for the strategy
        """
        try:
            if strategy_type in ['Bull Call Spread', 'Bull Put Spread']:
                # Long strike should be lower than short strike
                return strikes.get('long_strike', 0) < strikes.get('short_strike', float('inf'))
                
            elif strategy_type in ['Bear Call Spread', 'Bear Put Spread']:
                # Short strike should be lower than long strike
                return strikes.get('short_strike', 0) < strikes.get('long_strike', float('inf'))
                
            elif strategy_type == 'Iron Condor':
                # Put long < Put short < Call short < Call long
                return (strikes.get('put_long', 0) < strikes.get('put_short', float('inf')) and
                        strikes.get('put_short', 0) < strikes.get('call_short', float('inf')) and
                        strikes.get('call_short', 0) < strikes.get('call_long', float('inf')))
                        
            elif strategy_type in ['Butterfly Spread', 'Iron Butterfly']:
                # Lower < ATM < Upper
                return (strikes.get('lower_strike', 0) < strikes.get('atm_strike', float('inf')) and
                        strikes.get('atm_strike', 0) < strikes.get('upper_strike', float('inf')))
                        
            else:
                # No specific validation needed
                return True
                
        except Exception as e:
            logger.error(f"Error validating strike relationships: {e}")
            return False
    
    def _fix_strike_relationships(self, strikes: Dict[str, float], strategy_type: str,
                                options_df: pd.DataFrame) -> Dict[str, float]:
        """
        Attempt to fix invalid strike relationships
        """
        try:
            # For spreads, ensure proper ordering
            if strategy_type in ['Bull Call Spread', 'Bear Put Spread']:
                if strikes.get('long_strike', 0) >= strikes.get('short_strike', 0):
                    # Swap them
                    strikes['long_strike'], strikes['short_strike'] = strikes['short_strike'], strikes['long_strike']
                    
            elif strategy_type in ['Bear Call Spread', 'Bull Put Spread']:
                if strikes.get('short_strike', 0) >= strikes.get('long_strike', 0):
                    # Swap them
                    strikes['short_strike'], strikes['long_strike'] = strikes['long_strike'], strikes['short_strike']
            
            return strikes
            
        except Exception as e:
            logger.error(f"Error fixing strike relationships: {e}")
            return strikes
    
    def _emergency_fallback(self, strategy_type: str, options_df: pd.DataFrame,
                          spot_price: float) -> Dict[str, float]:
        """
        Emergency fallback when normal selection fails
        """
        try:
            strikes = {}
            
            # Get all available strikes
            call_strikes = sorted(options_df[options_df['option_type'] == 'CALL']['strike'].unique())
            put_strikes = sorted(options_df[options_df['option_type'] == 'PUT']['strike'].unique())
            
            if not call_strikes or not put_strikes:
                return {}
            
            # Find ATM strikes
            atm_call_idx = min(range(len(call_strikes)), key=lambda i: abs(call_strikes[i] - spot_price))
            atm_put_idx = min(range(len(put_strikes)), key=lambda i: abs(put_strikes[i] - spot_price))
            
            # Simple fallback based on strategy type
            if strategy_type in ['Long Call', 'Covered Call']:
                strikes['strike'] = call_strikes[min(atm_call_idx + 1, len(call_strikes) - 1)]
                
            elif strategy_type in ['Long Put', 'Cash-Secured Put']:
                strikes['strike'] = put_strikes[max(atm_put_idx - 1, 0)]
                
            elif strategy_type in ['Bull Call Spread', 'Bear Put Spread']:
                strikes['long_strike'] = call_strikes[atm_call_idx] if 'Call' in strategy_type else put_strikes[atm_put_idx]
                strikes['short_strike'] = call_strikes[min(atm_call_idx + 2, len(call_strikes) - 1)] if 'Call' in strategy_type else put_strikes[max(atm_put_idx - 2, 0)]
                
            elif strategy_type in ['Long Straddle', 'Short Straddle']:
                strikes['strike'] = call_strikes[atm_call_idx]
                
            elif strategy_type == 'Iron Condor':
                strikes['put_short'] = put_strikes[max(atm_put_idx - 2, 0)]
                strikes['put_long'] = put_strikes[max(atm_put_idx - 4, 0)]
                strikes['call_short'] = call_strikes[min(atm_call_idx + 2, len(call_strikes) - 1)]
                strikes['call_long'] = call_strikes[min(atm_call_idx + 4, len(call_strikes) - 1)]
            
            logger.warning(f"Used emergency fallback for {strategy_type}: {strikes}")
            return strikes
            
        except Exception as e:
            logger.error(f"Emergency fallback failed: {e}")
            return {}