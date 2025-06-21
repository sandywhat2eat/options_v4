"""
Short Strangle Strategy - Wide range premium collection
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import logging

from ..base_strategy import BaseStrategy

logger = logging.getLogger(__name__)

class ShortStrangle(BaseStrategy):
    """
    Short Strangle: Sell OTM Call + Sell OTM Put
    
    Market Outlook: Neutral, expecting range-bound movement
    Profit: From theta decay within the strikes
    Risk: Unlimited on both sides
    Ideal: High IV environments, stable markets
    """
    
    def get_strategy_name(self) -> str:
        return "Short Strangle"
    
    def get_market_outlook(self) -> str:
        return "neutral"
    
    def get_iv_preference(self) -> str:
        return "high"
    
    def get_required_legs(self) -> int:
        return 2
    
    def get_market_bias(self) -> List[str]:
        return ['neutral', 'low_volatility']
    
    def construct_strategy(self, **kwargs) -> Dict:
        """Construct short strangle with OTM options"""
        market_analysis = kwargs.get('market_analysis', {})
        
        try:
            
            # Check IV environment - prefer high IV
            atm_iv = market_analysis.get('iv_analysis', {}).get('atm_iv', 30)
            if atm_iv < 30:  # Skip if IV too low
                logger.info("IV too low for Short Strangle")
                return None
            
            # Separate calls and puts
            calls = self.options_df[self.options_df['option_type'] == 'CALL']
            puts = self.options_df[self.options_df['option_type'] == 'PUT']
            
            if calls.empty or puts.empty:
                return None
            
            # Find OTM strikes (3-4% away from spot)
            call_target = self.spot_price * 1.035  # 3.5% OTM
            put_target = self.spot_price * 0.965   # 3.5% OTM
            
            # Get OTM strikes
            call_strikes_otm = calls[calls['strike'] > self.spot_price]['strike'].unique()
            put_strikes_otm = puts[puts['strike'] < self.spot_price]['strike'].unique()
            
            if len(call_strikes_otm) == 0 or len(put_strikes_otm) == 0:
                return None
            
            # Find strikes closest to targets
            call_strike = min(call_strikes_otm, key=lambda x: abs(x - call_target))
            put_strike = max(put_strikes_otm, key=lambda x: abs(x - put_target))
            
            # Validate strikes are available
            if not self.validate_strikes([call_strike, put_strike]):
                return None
            
            # Get option data
            call_data = self._get_option_data(call_strike, 'CALL')
            put_data = self._get_option_data(put_strike, 'PUT')
            
            if call_data is None or put_data is None:
                return None
            
            # Create legs
            legs = [
                {
                    'option_type': 'CALL',
                    'position': 'SHORT',
                    'strike': call_strike,
                    'premium': call_data.get('last_price', 0),
                    'delta': call_data.get('delta', 0),
                    'gamma': call_data.get('gamma', 0),
                    'theta': call_data.get('theta', 0),
                    'vega': call_data.get('vega', 0),
                    'rationale': 'Short OTM Call'
                },
                {
                    'option_type': 'PUT',
                    'position': 'SHORT',
                    'strike': put_strike,
                    'premium': put_data.get('last_price', 0),
                    'delta': put_data.get('delta', 0),
                    'gamma': put_data.get('gamma', 0),
                    'theta': put_data.get('theta', 0),
                    'vega': put_data.get('vega', 0),
                    'rationale': 'Short OTM Put'
                }
            ]
            
            # Calculate strategy metrics
            metrics = self._calculate_metrics(legs, self.spot_price, market_analysis)
            if not metrics:
                return None
            
            # Add exit conditions
            metrics['exit_conditions'] = {
                'profit_target': '25-50% of max credit',
                'stop_loss': 'If loss exceeds 2x credit received',
                'time_exit': 'With 21 days to expiry',
                'delta_exit': 'If any strike delta exceeds 0.50',
                'adjustment': 'Roll untested side or convert to Iron Condor'
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error constructing Short Strangle: {e}")
            return None
    
    def _calculate_metrics(self, legs: List[Dict], spot_price: float,
                         market_analysis: Dict) -> Optional[Dict]:
        """Calculate short strangle specific metrics"""
        try:
            # Extract leg details
            call_leg = next(l for l in legs if l['option_type'] == 'CALL')
            put_leg = next(l for l in legs if l['option_type'] == 'PUT')
            
            # Calculate credit received (negative premiums for short)
            call_credit = -call_leg['premium']
            put_credit = -put_leg['premium']
            total_credit = -(call_credit + put_credit)  # Positive credit
            
            # Breakevens
            upper_breakeven = call_leg['strike'] + total_credit
            lower_breakeven = put_leg['strike'] - total_credit
            
            # Max profit/loss
            max_profit = total_credit
            max_loss = float('inf')  # Unlimited
            
            # Calculate probability of profit
            # Simplified probability estimate for staying in range
            profit_range = upper_breakeven - lower_breakeven
            range_pct = (profit_range / spot_price) * 100
            # Larger range = higher probability of staying within
            probability_profit = max(0.3, min(0.8, 0.5 + (range_pct - 15) * 0.015))
            
            # Greeks (negative for short positions)
            total_delta = -call_leg['delta'] - put_leg['delta']
            total_gamma = -call_leg.get('gamma', 0) - put_leg.get('gamma', 0)
            total_theta = -call_leg.get('theta', 0) - put_leg.get('theta', 0)
            total_vega = -call_leg.get('vega', 0) - put_leg.get('vega', 0)
            
            # Range analysis
            profit_range = upper_breakeven - lower_breakeven
            profit_range_pct = (profit_range / spot_price) * 100
            
            # Strike width
            strike_width = call_leg['strike'] - put_leg['strike']
            strike_width_pct = (strike_width / spot_price) * 100
            
            # Risk metrics
            margin_requirement = max(
                call_leg['strike'] * 0.15,
                put_leg['strike'] * 0.15
            ) - total_credit
            
            return_on_margin = (max_profit / margin_requirement) * 100 if margin_requirement > 0 else 0
            
            return {
                'legs': legs,
                'max_profit': max_profit,
                'max_loss': max_loss,
                'probability_profit': probability_profit,
                'breakevens': {
                    'upper': upper_breakeven,
                    'lower': lower_breakeven,
                    'profit_range': profit_range,
                    'profit_range_pct': profit_range_pct
                },
                'strikes': {
                    'call_strike': call_leg['strike'],
                    'put_strike': put_leg['strike'],
                    'width': strike_width,
                    'width_pct': strike_width_pct
                },
                'greeks': {
                    'delta': total_delta,
                    'gamma': total_gamma,
                    'theta': total_theta,
                    'vega': total_vega
                },
                'risk_metrics': {
                    'risk_reward': 0,  # Undefined for unlimited risk
                    'credit_received': total_credit,
                    'margin_requirement': margin_requirement,
                    'return_on_margin': return_on_margin
                },
                'optimal_conditions': {
                    'iv_environment': 'High (>60th percentile)',
                    'market_outlook': 'Range-bound',
                    'time_to_expiry': '30-45 days',
                    'iv_forecast': 'Stable or decreasing'
                }
            }
            
        except Exception as e:
            logger.error(f"Error calculating Short Strangle metrics: {e}")
            return None