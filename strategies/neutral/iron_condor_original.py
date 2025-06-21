"""
Iron Condor strategy implementation
"""

import pandas as pd
import logging
from typing import Dict, List
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from strategies.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)

class IronCondor(BaseStrategy):
    """Iron Condor strategy implementation"""
    
    def get_strategy_name(self) -> str:
        return "Iron Condor"
    
    def get_market_outlook(self) -> str:
        return "neutral"
    
    def get_iv_preference(self) -> str:
        return "high"
    
    def construct_strategy(self, wing_width: str = "wide", 
                         put_short_delta: float = -0.25, 
                         call_short_delta: float = 0.25) -> Dict:
        """
        Construct Iron Condor strategy
        
        Args:
            wing_width: "wide" or "narrow" for different risk/reward profiles
            put_short_delta: Target delta for short put
            call_short_delta: Target delta for short call
        """
        try:
            # Adjust wing deltas based on width
            if wing_width == "wide":
                put_long_delta = -0.10
                call_long_delta = 0.10
                strategy_variant = "Wide Wings"
            else:  # narrow
                put_long_delta = -0.15
                call_long_delta = 0.15
                strategy_variant = "Narrow Wings"
            
            # Find optimal strikes
            put_short_strike = self._find_strike_by_delta(abs(put_short_delta), 'PUT')
            put_long_strike = self._find_strike_by_delta(abs(put_long_delta), 'PUT')
            call_short_strike = self._find_strike_by_delta(call_short_delta, 'CALL')
            call_long_strike = self._find_strike_by_delta(call_long_delta, 'CALL')
            
            # Validate strike relationships
            strikes = [put_long_strike, put_short_strike, call_short_strike, call_long_strike]
            if not self._validate_iron_condor_strikes(strikes):
                return {'success': False, 'reason': 'Invalid strike structure'}
            
            if not self.validate_strikes(strikes):
                return {'success': False, 'reason': 'Strikes not available or illiquid'}
            
            # Get option data
            put_short_data = self._get_option_data(put_short_strike, 'PUT')
            put_long_data = self._get_option_data(put_long_strike, 'PUT')
            call_short_data = self._get_option_data(call_short_strike, 'CALL')
            call_long_data = self._get_option_data(call_long_strike, 'CALL')
            
            if any(data is None for data in [put_short_data, put_long_data, call_short_data, call_long_data]):
                return {'success': False, 'reason': 'Option data not available'}
            
            # Construct legs (Bull Put Spread + Bear Call Spread)
            self.legs = [
                {
                    'option_type': 'PUT',
                    'position': 'SHORT',
                    'strike': put_short_strike,
                    'premium': put_short_data.get('last_price', 0),
                    'delta': put_short_data.get('delta', 0),
                    'rationale': 'Short put for premium collection (Bull Put Spread)'
                },
                {
                    'option_type': 'PUT',
                    'position': 'LONG',
                    'strike': put_long_strike,
                    'premium': put_long_data.get('last_price', 0),
                    'delta': put_long_data.get('delta', 0),
                    'rationale': 'Long put for downside protection'
                },
                {
                    'option_type': 'CALL',
                    'position': 'SHORT',
                    'strike': call_short_strike,
                    'premium': call_short_data.get('last_price', 0),
                    'delta': call_short_data.get('delta', 0),
                    'rationale': 'Short call for premium collection (Bear Call Spread)'
                },
                {
                    'option_type': 'CALL',
                    'position': 'LONG',
                    'strike': call_long_strike,
                    'premium': call_long_data.get('last_price', 0),
                    'delta': call_long_data.get('delta', 0),
                    'rationale': 'Long call for upside protection'
                }
            ]
            
            # Calculate metrics
            net_credit = self._calculate_net_credit()
            put_spread_width = put_short_strike - put_long_strike
            call_spread_width = call_long_strike - call_short_strike
            max_loss = max(put_spread_width, call_spread_width) - net_credit
            
            greeks = self.get_greeks_summary()
            
            # Calculate profit zone
            lower_breakeven = put_short_strike - net_credit
            upper_breakeven = call_short_strike + net_credit
            
            return {
                'success': True,
                'strategy_name': f"{self.get_strategy_name()} ({strategy_variant})",
                'legs': self.legs,
                'max_profit': net_credit,
                'max_loss': max_loss,
                'breakeven_points': [lower_breakeven, upper_breakeven],
                'profit_zone': (lower_breakeven, upper_breakeven),
                'delta_exposure': greeks['delta'],
                'theta_decay': greeks['theta'],
                'optimal_outcome': f"Stock stays between {lower_breakeven:.2f} and {upper_breakeven:.2f}",
                'wing_width': wing_width,
                'put_spread_width': put_spread_width,
                'call_spread_width': call_spread_width
            }
            
        except Exception as e:
            logger.error(f"Error constructing Iron Condor: {e}")
            return {'success': False, 'reason': f'Construction error: {e}'}
    
    def _find_strike_by_delta(self, target_delta: float, option_type: str) -> float:
        """Find strike closest to target delta"""
        try:
            type_options = self.options_df[
                (self.options_df['option_type'] == option_type) &
                (self.options_df['open_interest'] >= 50)  # Basic liquidity filter
            ]
            
            if type_options.empty:
                return self.spot_price
            
            # For puts, compare absolute delta values
            if option_type == 'PUT':
                type_options['delta_diff'] = abs(abs(type_options['delta']) - target_delta)
            else:  # CALL
                type_options['delta_diff'] = abs(type_options['delta'] - target_delta)
            
            optimal_option = type_options.loc[type_options['delta_diff'].idxmin()]
            return optimal_option['strike']
            
        except Exception as e:
            logger.error(f"Error finding strike by delta: {e}")
            return self.spot_price
    
    def _validate_iron_condor_strikes(self, strikes: List[float]) -> bool:
        """Validate Iron Condor strike structure"""
        try:
            put_long, put_short, call_short, call_long = strikes
            
            # Check proper ordering
            if not (put_long < put_short < self.spot_price < call_short < call_long):
                logger.warning(f"Invalid strike ordering: {strikes}")
                return False
            
            # Check minimum spreads
            put_spread = put_short - put_long
            call_spread = call_long - call_short
            
            if put_spread < 1.0 or call_spread < 1.0:
                logger.warning(f"Spreads too narrow: Put={put_spread}, Call={call_spread}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating Iron Condor strikes: {e}")
            return False
    
    def _calculate_net_credit(self) -> float:
        """Calculate net credit received for Iron Condor"""
        try:
            total_credit = 0.0
            
            for leg in self.legs:
                premium = leg.get('premium', 0)
                if leg['position'] == 'SHORT':
                    total_credit += premium
                else:  # LONG
                    total_credit -= premium
            
            return total_credit
            
        except Exception as e:
            logger.error(f"Error calculating net credit: {e}")
            return 0.0