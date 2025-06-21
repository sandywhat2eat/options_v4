"""
Short Straddle Strategy - High IV premium collection
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import logging

from ..base_strategy import BaseStrategy

logger = logging.getLogger(__name__)

class ShortStraddle(BaseStrategy):
    """
    Short Straddle: Sell ATM Call + Sell ATM Put
    
    Market Outlook: Neutral with low volatility expectation
    Profit: From theta decay and volatility contraction
    Risk: Unlimited on both sides
    Ideal: High IV environments, range-bound markets
    """
    
    def get_strategy_name(self) -> str:
        return "Short Straddle"
    
    def get_market_outlook(self) -> str:
        return "neutral"
    
    def get_iv_preference(self) -> str:
        return "high"
    
    def get_required_legs(self) -> int:
        return 2
    
    def get_market_bias(self) -> List[str]:
        return ['neutral', 'range_bound']
    
    def construct_strategy(self, **kwargs) -> Dict:
        """Construct short straddle at ATM strikes"""
        market_analysis = kwargs.get('market_analysis', {})
        
        try:
            
            # Check IV environment - prefer high IV
            atm_iv = market_analysis.get('iv_analysis', {}).get('atm_iv', 30)
            if atm_iv < 25:  # Skip if IV too low
                logger.info("IV too low for Short Straddle")
                return None
            
            # Find ATM strike
            strikes = self.options_df['strike'].unique()
            atm_strike = min(strikes, key=lambda x: abs(x - self.spot_price))
            
            # Validate strike is available
            if not self.validate_strikes([atm_strike]):
                return None
            
            # Get ATM options data
            call_data = self._get_option_data(atm_strike, 'CALL')
            put_data = self._get_option_data(atm_strike, 'PUT')
            
            if call_data is None or put_data is None:
                return None
            
            # Create legs
            legs = [
                {
                    'option_type': 'CALL',
                    'position': 'SHORT',
                    'strike': atm_strike,
                    'premium': call_data.get('last_price', 0),
                    'delta': call_data.get('delta', 0),
                    'gamma': call_data.get('gamma', 0),
                    'theta': call_data.get('theta', 0),
                    'vega': call_data.get('vega', 0),
                    'rationale': 'ATM Call - Premium collection'
                },
                {
                    'option_type': 'PUT',
                    'position': 'SHORT',
                    'strike': atm_strike,
                    'premium': put_data.get('last_price', 0),
                    'delta': put_data.get('delta', 0),
                    'gamma': put_data.get('gamma', 0),
                    'theta': put_data.get('theta', 0),
                    'vega': put_data.get('vega', 0),
                    'rationale': 'ATM Put - Premium collection'
                }
            ]
            
            # Calculate strategy metrics
            metrics = self._calculate_metrics(legs, self.spot_price, market_analysis)
            if not metrics:
                return None
            
            # Add exit conditions
            metrics['exit_conditions'] = {
                'profit_target': '25-30% of max profit',
                'stop_loss': 'If underlying moves beyond breakeven points',
                'time_exit': 'If 50% of time value collected or 5 DTE',
                'volatility_exit': 'If IV contracts significantly',
                'adjustment': 'Convert to Iron Condor if threatened'
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error constructing Short Straddle: {e}")
            return None
    
    def _calculate_metrics(self, legs: List[Dict], spot_price: float,
                         market_analysis: Dict) -> Optional[Dict]:
        """Calculate short straddle specific metrics"""
        try:
            # Extract leg details
            call_leg = next(l for l in legs if l['option_type'] == 'CALL')
            put_leg = next(l for l in legs if l['option_type'] == 'PUT')
            
            # Premiums (negative for short positions)
            call_premium = -call_leg['premium']
            put_premium = -put_leg['premium']
            total_credit = -(call_premium + put_premium)  # Positive credit received
            
            strike = call_leg['strike']
            
            # Calculate breakevens
            upper_breakeven = strike + total_credit
            lower_breakeven = strike - total_credit
            
            # Profit/Loss calculations
            max_profit = total_credit
            max_loss = float('inf')  # Unlimited
            
            # Greeks
            total_delta = -call_leg['delta'] - put_leg['delta']  # Both short
            total_gamma = -call_leg.get('gamma', 0) - put_leg.get('gamma', 0)
            total_theta = -call_leg.get('theta', 0) - put_leg.get('theta', 0)  # Positive for short
            total_vega = -call_leg.get('vega', 0) - put_leg.get('vega', 0)  # Negative for short
            
            # Probability calculations
            # Simplified probability estimate
            breakeven_range = upper_breakeven - lower_breakeven
            range_pct = (breakeven_range / spot_price) * 100
            # Rough estimate: smaller range = lower probability
            probability_profit = max(0.2, min(0.8, 0.6 - (range_pct - 10) * 0.02))
            
            # Risk metrics
            breakeven_width = upper_breakeven - lower_breakeven
            breakeven_pct = (breakeven_width / spot_price) * 100
            
            # Expected value consideration
            expected_move = market_analysis.get('price_levels', {}).get(
                'expected_moves', {}
            ).get('one_sd_move', spot_price * 0.02)
            
            # Adjust probability if expected move is large
            if expected_move > total_credit * 0.8:
                probability_profit *= 0.85  # Reduce probability
            
            return {
                'legs': legs,
                'max_profit': max_profit,
                'max_loss': max_loss,
                'probability_profit': probability_profit,
                'breakevens': {
                    'upper': upper_breakeven,
                    'lower': lower_breakeven,
                    'width': breakeven_width,
                    'width_pct': breakeven_pct
                },
                'greeks': {
                    'delta': total_delta,
                    'gamma': total_gamma,
                    'theta': total_theta,
                    'vega': total_vega
                },
                'risk_metrics': {
                    'risk_reward': 0,  # Undefined for unlimited risk
                    'required_margin': strike * 0.15,  # Approximate
                    'rom': (max_profit / (strike * 0.15)) * 100  # Return on margin
                },
                'optimal_conditions': {
                    'iv_environment': 'High (>75th percentile)',
                    'market_outlook': 'Range-bound',
                    'time_to_expiry': '30-45 days',
                    'volatility_forecast': 'Decreasing'
                },
                'strategy_notes': 'High risk strategy with unlimited loss potential. Requires active management and strict stop losses.'
            }
            
        except Exception as e:
            logger.error(f"Error calculating Short Straddle metrics: {e}")
            return None