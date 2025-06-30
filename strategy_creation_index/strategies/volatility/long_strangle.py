"""
Long Strangle Strategy - Cheaper volatility play
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import logging

from ..base_strategy import BaseStrategy

logger = logging.getLogger(__name__)

class LongStrangle(BaseStrategy):
    """
    Long Strangle: Buy OTM Call + Buy OTM Put
    
    Market Outlook: High volatility expected, direction unknown
    Profit: From large moves in either direction
    Risk: Limited to premium paid
    Ideal: Before events, low IV environments
    """
    
    def get_strategy_name(self) -> str:
        return "Long Strangle"
    
    def get_market_outlook(self) -> str:
        return "neutral"
    
    def get_iv_preference(self) -> str:
        return "low"
    
    def get_required_legs(self) -> int:
        return 2
    
    def get_market_bias(self) -> List[str]:
        return ['high_volatility', 'neutral']
    
    def construct_strategy(self, **kwargs) -> Dict:
        """Construct long strangle with OTM options"""
        market_analysis = kwargs.get('market_analysis', {})
        
        try:
            
            # Check IV environment - prefer low to normal IV
            atm_iv = market_analysis.get('iv_analysis', {}).get('atm_iv', 30)
            if atm_iv > 45:  # Skip if IV too high
                logger.info("IV too high for Long Strangle")
                return {
                    'success': False,
                    'reason': f'IV too high ({atm_iv:.1f}%) for Long Strangle - prefer < 45%'
                }
            
            # Separate calls and puts
            calls = self.options_df[self.options_df['option_type'] == 'CALL']
            puts = self.options_df[self.options_df['option_type'] == 'PUT']
            
            if calls.empty or puts.empty:
                return {
                    'success': False,
                    'reason': 'Need both calls and puts for Long Strangle'
                }
            
            # Find OTM strikes (3-5% away from spot)
            otm_call_target = self.spot_price * 1.04  # 4% OTM call
            otm_put_target = self.spot_price * 0.96   # 4% OTM put
            
            # Find nearest available strikes
            call_strikes = calls['strike'].unique()
            put_strikes = puts['strike'].unique()
            
            call_strikes_otm = call_strikes[call_strikes > self.spot_price]
            put_strikes_otm = put_strikes[put_strikes < self.spot_price]
            
            if len(call_strikes_otm) == 0 or len(put_strikes_otm) == 0:
                return {
                    'success': False,
                    'reason': 'No suitable OTM strikes available for Long Strangle'
                }
            
            call_strike = min(call_strikes_otm, 
                            key=lambda x: abs(x - otm_call_target))
            put_strike = max(put_strikes_otm,
                           key=lambda x: abs(x - otm_put_target))
            
            # Validate strikes are available
            if not self.validate_strikes([call_strike, put_strike]):
                return {
                    'success': False,
                    'reason': 'Selected strikes failed validation for Long Strangle'
                }
            
            # Get the options data
            call_data = self._get_option_data(call_strike, 'CALL')
            put_data = self._get_option_data(put_strike, 'PUT')
            
            if call_data is None or put_data is None:
                return {
                    'success': False,
                    'reason': 'Unable to get option data for selected strikes'
                }
            
            # Create legs
            legs = [
                {
                    'option_type': 'CALL',
                    'position': 'LONG',
                    'strike': call_strike,
                    'premium': call_data.get('last_price', 0),
                    'delta': call_data.get('delta', 0),
                    'gamma': call_data.get('gamma', 0),
                    'theta': call_data.get('theta', 0),
                    'vega': call_data.get('vega', 0),
                    'rationale': f'OTM Call at {call_strike}'
                },
                {
                    'option_type': 'PUT',
                    'position': 'LONG',
                    'strike': put_strike,
                    'premium': put_data.get('last_price', 0),
                    'delta': put_data.get('delta', 0),
                    'gamma': put_data.get('gamma', 0),
                    'theta': put_data.get('theta', 0),
                    'vega': put_data.get('vega', 0),
                    'rationale': f'OTM Put at {put_strike}'
                }
            ]
            
            # Calculate strategy metrics
            metrics = self._calculate_metrics(legs, self.spot_price, market_analysis)
            if not metrics:
                return {'success': False, 'reason': 'Failed to calculate metrics'}
            
            # Add exit conditions
            metrics['exit_conditions'] = {
                'profit_target': '50-100% of debit paid',
                'stop_loss': 'If premium loses 50% of value',
                'time_exit': 'With 10 days to expiry or 50% time decay',
                'volatility_exit': 'If IV contracts significantly',
                'adjustment': 'Convert to Iron Condor if one side profitable'
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error constructing Long Strangle: {e}")
            return {'success': False, 'reason': f'Construction error: {str(e)}'}
    
    def _calculate_metrics(self, legs: List[Dict], spot_price: float,
                         market_analysis: Dict) -> Optional[Dict]:
        """Calculate long strangle specific metrics"""
        try:
            # Extract leg details
            call_leg = next(l for l in legs if l['option_type'] == 'CALL')
            put_leg = next(l for l in legs if l['option_type'] == 'PUT')
            
            # Calculate debit paid
            total_debit = call_leg['premium'] + put_leg['premium']
            
            # Breakevens
            upper_breakeven = call_leg['strike'] + total_debit
            lower_breakeven = put_leg['strike'] - total_debit
            
            # Max profit/loss
            max_profit = float('inf')  # Unlimited
            max_loss = total_debit
            
            # Calculate probability of profit
            # Simplified probability estimate for large moves
            breakeven_range = upper_breakeven - lower_breakeven
            range_pct = (breakeven_range / spot_price) * 100
            # Larger range = lower probability of reaching breakevens
            probability_profit = max(0.15, min(0.6, 0.5 - (range_pct - 15) * 0.01))
            
            # Greeks
            total_delta = call_leg['delta'] + put_leg['delta']
            total_gamma = call_leg.get('gamma', 0) + put_leg.get('gamma', 0)
            total_theta = call_leg.get('theta', 0) + put_leg.get('theta', 0)
            total_vega = call_leg.get('vega', 0) + put_leg.get('vega', 0)
            
            # Required move analysis
            required_move_pct = min(
                abs(upper_breakeven - spot_price) / spot_price,
                abs(spot_price - lower_breakeven) / spot_price
            ) * 100
            
            # Compare to expected move
            expected_move = market_analysis.get('price_levels', {}).get(
                'expected_moves', {}
            ).get('one_sd_move', spot_price * 0.02)
            
            move_probability = 'High' if expected_move > total_debit else 'Low'
            
            return {
                'success': True,
                'strategy_name': 'Long Strangle',
                'legs': legs,
                'max_profit': max_profit,
                'max_loss': max_loss,
                'probability_profit': probability_profit,
                'breakevens': {
                    'upper': upper_breakeven,
                    'lower': lower_breakeven,
                    'width': upper_breakeven - lower_breakeven,
                    'required_move_pct': required_move_pct
                },
                'greeks': {
                    'delta': total_delta,
                    'gamma': total_gamma,
                    'theta': total_theta,
                    'vega': total_vega
                },
                'risk_metrics': {
                    'risk_reward': float('inf'),
                    'debit_paid': total_debit,
                    'debit_as_pct_spot': (total_debit / spot_price) * 100
                },
                'movement_analysis': {
                    'required_move': required_move_pct,
                    'expected_move': (expected_move / spot_price) * 100,
                    'move_probability': move_probability
                },
                'optimal_conditions': {
                    'iv_environment': 'Low to normal (<50th percentile)',
                    'market_outlook': 'Expecting large move, direction unknown',
                    'time_to_expiry': '30-60 days',
                    'upcoming_events': 'Earnings, FDA approvals, policy decisions'
                }
            }
            
        except Exception as e:
            logger.error(f"Error calculating Long Strangle metrics: {e}")
            return None