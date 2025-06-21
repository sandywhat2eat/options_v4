"""
Straddle strategies (Long/Short Straddle)
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from strategies.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)

class LongStraddle(BaseStrategy):
    """Long Straddle strategy implementation"""
    
    def get_strategy_name(self) -> str:
        return "Long Straddle"
    
    def get_market_outlook(self) -> str:
        return "neutral"  # Expects big move in either direction
    
    def get_iv_preference(self) -> str:
        return "low"  # Buy volatility when it's cheap
    
    def construct_strategy(self, strike: float = None) -> Dict:
        """
        Construct Long Straddle strategy
        
        Args:
            strike: ATM strike (defaults to closest to spot)
        """
        try:
            if strike is None:
                strike = self._find_atm_strike()
            
            if not self.validate_strikes([strike]):
                return {'success': False, 'reason': 'Strike not available or illiquid'}
            
            # Get option data
            call_data = self._get_option_data(strike, 'CALL')
            put_data = self._get_option_data(strike, 'PUT')
            
            if call_data is None or put_data is None:
                return {'success': False, 'reason': 'Option data not available'}
            
            # Construct legs
            self.legs = [
                {
                    'option_type': 'CALL',
                    'position': 'LONG',
                    'strike': strike,
                    'premium': call_data.get('last_price', 0),
                    'delta': call_data.get('delta', 0),
                    'rationale': 'Long call for upside movement'
                },
                {
                    'option_type': 'PUT',
                    'position': 'LONG',
                    'strike': strike,
                    'premium': put_data.get('last_price', 0),
                    'delta': put_data.get('delta', 0),
                    'rationale': 'Long put for downside movement'
                }
            ]
            
            # Calculate metrics
            total_premium = call_data.get('last_price', 0) + put_data.get('last_price', 0)
            upper_breakeven = strike + total_premium
            lower_breakeven = strike - total_premium
            
            # Estimate move required (based on premium)
            move_required_pct = (total_premium / self.spot_price) * 100
            
            greeks = self.get_greeks_summary()
            
            return {
                'success': True,
                'strategy_name': self.get_strategy_name(),
                'legs': self.legs,
                'max_profit': float('inf'),  # Unlimited in both directions
                'max_loss': total_premium,
                'breakeven_points': [lower_breakeven, upper_breakeven],
                'move_required': total_premium,
                'move_required_pct': move_required_pct,
                'delta_exposure': greeks['delta'],  # Should be near zero
                'theta_decay': greeks['theta'],     # Negative (time decay hurts)
                'vega_exposure': greeks['vega'],    # Positive (benefits from vol expansion)
                'optimal_outcome': f"Big move beyond {lower_breakeven:.2f} or {upper_breakeven:.2f}"
            }
            
        except Exception as e:
            logger.error(f"Error constructing Long Straddle: {e}")
            return {'success': False, 'reason': f'Construction error: {e}'}
    
    def _find_atm_strike(self) -> float:
        """Find ATM strike closest to spot price"""
        try:
            # Get unique strikes from both calls and puts
            all_strikes = self.options_df['strike'].unique()
            
            # Find closest to spot
            strike_diffs = np.abs(all_strikes - self.spot_price)
            atm_strike = all_strikes[np.argmin(strike_diffs)]
            
            return float(atm_strike)
            
        except Exception as e:
            logger.error(f"Error finding ATM strike: {e}")
            return self.spot_price

class ShortStraddle(BaseStrategy):
    """Short Straddle strategy implementation"""
    
    def get_strategy_name(self) -> str:
        return "Short Straddle"
    
    def get_market_outlook(self) -> str:
        return "neutral"  # Expects low movement
    
    def get_iv_preference(self) -> str:
        return "high"  # Sell volatility when it's expensive
    
    def construct_strategy(self, strike: float = None) -> Dict:
        """
        Construct Short Straddle strategy
        
        Args:
            strike: ATM strike (defaults to closest to spot)
        """
        try:
            if strike is None:
                strike = self._find_atm_strike()
            
            if not self.validate_strikes([strike]):
                return {'success': False, 'reason': 'Strike not available or illiquid'}
            
            # Get option data
            call_data = self._get_option_data(strike, 'CALL')
            put_data = self._get_option_data(strike, 'PUT')
            
            if call_data is None or put_data is None:
                return {'success': False, 'reason': 'Option data not available'}
            
            # Additional risk check for short straddle
            if not self._validate_short_straddle_risk(call_data, put_data):
                return {'success': False, 'reason': 'Risk too high for short straddle'}
            
            # Construct legs
            self.legs = [
                {
                    'option_type': 'CALL',
                    'position': 'SHORT',
                    'strike': strike,
                    'premium': call_data.get('last_price', 0),
                    'delta': call_data.get('delta', 0),
                    'rationale': 'Short call to collect premium'
                },
                {
                    'option_type': 'PUT',
                    'position': 'SHORT',
                    'strike': strike,
                    'premium': put_data.get('last_price', 0),
                    'delta': put_data.get('delta', 0),
                    'rationale': 'Short put to collect premium'
                }
            ]
            
            # Calculate metrics
            total_credit = call_data.get('last_price', 0) + put_data.get('last_price', 0)
            upper_breakeven = strike + total_credit
            lower_breakeven = strike - total_credit
            
            # Profit zone
            profit_zone_pct = (2 * total_credit / self.spot_price) * 100
            
            greeks = self.get_greeks_summary()
            
            return {
                'success': True,
                'strategy_name': self.get_strategy_name(),
                'legs': self.legs,
                'max_profit': total_credit,
                'max_loss': float('inf'),  # Unlimited risk - requires margin
                'breakeven_points': [lower_breakeven, upper_breakeven],
                'profit_zone': (lower_breakeven, upper_breakeven),
                'profit_zone_pct': profit_zone_pct,
                'delta_exposure': greeks['delta'],  # Should be near zero
                'theta_decay': greeks['theta'],     # Positive (time decay helps)
                'vega_exposure': greeks['vega'],    # Negative (hurt by vol expansion)
                'optimal_outcome': f"Stock stays between {lower_breakeven:.2f} and {upper_breakeven:.2f}",
                'margin_requirement': 'HIGH',
                'risk_warning': 'Unlimited loss potential - monitor closely'
            }
            
        except Exception as e:
            logger.error(f"Error constructing Short Straddle: {e}")
            return {'success': False, 'reason': f'Construction error: {e}'}
    
    def _find_atm_strike(self) -> float:
        """Find ATM strike closest to spot price"""
        try:
            all_strikes = self.options_df['strike'].unique()
            strike_diffs = np.abs(all_strikes - self.spot_price)
            atm_strike = all_strikes[np.argmin(strike_diffs)]
            return float(atm_strike)
            
        except Exception as e:
            logger.error(f"Error finding ATM strike: {e}")
            return self.spot_price
    
    def _validate_short_straddle_risk(self, call_data: pd.Series, put_data: pd.Series) -> bool:
        """Additional risk validation for short straddle"""
        try:
            # Check IV levels - don't sell if IV is too low
            call_iv = call_data.get('iv', 0)
            put_iv = put_data.get('iv', 0)
            avg_iv = (call_iv + put_iv) / 2
            
            if avg_iv < 25:  # Don't sell straddles when IV is below 25%
                logger.warning(f"IV too low for short straddle: {avg_iv}")
                return False
            
            # Check liquidity for assignment risk
            call_oi = call_data.get('open_interest', 0)
            put_oi = put_data.get('open_interest', 0)
            
            if call_oi < 100 or put_oi < 100:
                logger.warning("Insufficient OI for short straddle")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating short straddle risk: {e}")
            return False