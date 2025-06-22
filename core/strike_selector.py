"""
Intelligent Strike Selection System
Selects optimal strikes based on expected moves, timeframe, and risk/reward
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

class IntelligentStrikeSelector:
    """
    Selects optimal strikes based on:
    - Expected moves (1SD, 2SD)
    - Timeframe (1 week to 1 month)
    - Risk/reward optimization
    - Probability of success
    """
    
    def __init__(self):
        # Timeframe multipliers for expected moves
        self.timeframe_multipliers = {
            '1-5 days': 0.3,      # Use 30% of 1SD move
            '5-10 days': 0.5,     # Use 50% of 1SD move
            '10-20 days': 0.75,   # Use 75% of 1SD move
            '20-30 days': 1.0,    # Use full 1SD move
            '30+ days': 1.25      # Use 125% of 1SD move
        }
        
        # Strategy-specific adjustments
        self.strategy_adjustments = {
            'Long Call': {'multiplier': 0.8, 'prefer': 'OTM'},
            'Long Put': {'multiplier': 0.8, 'prefer': 'OTM'},
            'Bull Call Spread': {'short_multiplier': 1.2, 'long_multiplier': 0.6},
            'Bear Put Spread': {'short_multiplier': 1.2, 'long_multiplier': 0.6},
            'Iron Condor': {'short_multiplier': 1.1, 'wing_multiplier': 1.5},
            'Short Straddle': {'multiplier': 0, 'prefer': 'ATM'},
            'Long Straddle': {'multiplier': 0, 'prefer': 'ATM'}
        }
    
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
            # Extract expected moves
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
            type_options['liquidity_score'] = (
                type_options['open_interest'] + type_options['volume']
            ) / type_options['open_interest'].max()
            
            # Combined score: 70% distance, 30% liquidity
            type_options['score'] = (
                0.7 * (1 - type_options['distance'] / type_options['distance'].max()) +
                0.3 * type_options['liquidity_score']
            )
            
            # Get best strike
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