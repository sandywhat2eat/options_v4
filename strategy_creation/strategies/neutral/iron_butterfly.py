"""
Iron Butterfly Strategy - ATM premium collection with protection
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import logging

from ..base_strategy import BaseStrategy

logger = logging.getLogger(__name__)

class IronButterfly(BaseStrategy):
    """
    Iron Butterfly: Sell ATM Call + Sell ATM Put + Buy OTM Call + Buy OTM Put
    
    Market Outlook: Neutral, expecting minimal movement
    Profit: Maximum at ATM strike
    Risk: Limited to wing width minus credit
    Ideal: High IV, expecting pin at strike
    """
    
    def get_strategy_name(self) -> str:
        return "Iron Butterfly"
    
    def get_market_outlook(self) -> str:
        return "neutral"
    
    def get_iv_preference(self) -> str:
        return "high"
    
    def get_required_legs(self) -> int:
        return 4
    
    def get_market_bias(self) -> List[str]:
        return ['neutral', 'low_volatility']
    
    def construct_strategy(self, **kwargs) -> Dict:
        """Construct iron butterfly centered at ATM"""
        market_analysis = kwargs.get('market_analysis', {})
        
        try:
            
            # Check IV environment - prefer high IV
            atm_iv = market_analysis.get('iv_analysis', {}).get('atm_iv', 30)
            if atm_iv < 25:
                logger.info("IV too low for Iron Butterfly")
                return {
                    'success': False,
                    'reason': 'Unable to construct Butterfly Spread - need liquid strikes'
                }
            
            # Find ATM strike
            strikes = self.options_df['strike'].unique()
            atm_strike = min(strikes, key=lambda x: abs(x - self.spot_price))
            
            # Find wing strikes (2-3% away)
            wing_distance = self.spot_price * 0.025
            lower_strikes = [s for s in strikes if s < atm_strike - wing_distance/2]
            upper_strikes = [s for s in strikes if s > atm_strike + wing_distance/2]
            
            if not lower_strikes or not upper_strikes:
                return {
                    'success': False,
                    'reason': 'Unable to construct Butterfly Spread - need liquid strikes'
                }
            
            lower_strike = max(lower_strikes)
            upper_strike = min(upper_strikes)
            
            # Validate strikes are available
            if not self.validate_strikes([atm_strike, lower_strike, upper_strike]):
                return {
                    'success': False,
                    'reason': 'Unable to construct Butterfly Spread - need liquid strikes'
                }
            
            # Get option data
            atm_call_data = self._get_option_data(atm_strike, 'CALL')
            atm_put_data = self._get_option_data(atm_strike, 'PUT')
            lower_put_data = self._get_option_data(lower_strike, 'PUT')
            upper_call_data = self._get_option_data(upper_strike, 'CALL')
            
            if any(data is None for data in [atm_call_data, atm_put_data, lower_put_data, upper_call_data]):
                return {
                    'success': False,
                    'reason': 'Unable to construct Butterfly Spread - need liquid strikes'
                }
            
            # Create legs
            legs = [
                {
                    'option_type': 'CALL',
                    'position': 'SHORT',
                    'strike': atm_strike,
                    'premium': atm_call_data.get('last_price', 0),
                    'delta': atm_call_data.get('delta', 0),
                    'gamma': atm_call_data.get('gamma', 0),
                    'theta': atm_call_data.get('theta', 0),
                    'vega': atm_call_data.get('vega', 0),
                    'rationale': 'Short ATM Call'
                },
                {
                    'option_type': 'PUT',
                    'position': 'SHORT',
                    'strike': atm_strike,
                    'premium': atm_put_data.get('last_price', 0),
                    'delta': atm_put_data.get('delta', 0),
                    'gamma': atm_put_data.get('gamma', 0),
                    'theta': atm_put_data.get('theta', 0),
                    'vega': atm_put_data.get('vega', 0),
                    'rationale': 'Short ATM Put'
                },
                {
                    'option_type': 'CALL',
                    'position': 'LONG',
                    'strike': upper_strike,
                    'premium': upper_call_data.get('last_price', 0),
                    'delta': upper_call_data.get('delta', 0),
                    'gamma': upper_call_data.get('gamma', 0),
                    'theta': upper_call_data.get('theta', 0),
                    'vega': upper_call_data.get('vega', 0),
                    'rationale': 'Long OTM Call (protection)'
                },
                {
                    'option_type': 'PUT',
                    'position': 'LONG',
                    'strike': lower_strike,
                    'premium': lower_put_data.get('last_price', 0),
                    'delta': lower_put_data.get('delta', 0),
                    'gamma': lower_put_data.get('gamma', 0),
                    'theta': lower_put_data.get('theta', 0),
                    'vega': lower_put_data.get('vega', 0),
                    'rationale': 'Long OTM Put (protection)'
                }
            ]
            
            # Calculate strategy metrics
            metrics = self._calculate_metrics(
                legs, self.spot_price, market_analysis,
                lower_strike, atm_strike, upper_strike
            )
            
            if not metrics:
                return {
                    'success': False,
                    'reason': 'Unable to construct Butterfly Spread - need liquid strikes'
                }
            
            # Add exit conditions
            metrics['exit_conditions'] = {
                'profit_target': '25-50% of max profit',
                'stop_loss': 'If loss exceeds 50% of max loss',
                'time_exit': 'With 21 days to expiry',
                'price_exit': 'If price moves beyond short strikes',
                'adjustment': 'Roll untested side if breached early'
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error constructing Iron Butterfly: {e}")
            return {
                    'success': False,
                    'reason': 'Unable to construct Butterfly Spread - need liquid strikes'
                }
    
    def _calculate_metrics(self, legs: List[Dict], spot_price: float,
                         market_analysis: Dict, lower_strike: float,
                         atm_strike: float, upper_strike: float) -> Optional[Dict]:
        """Calculate iron butterfly specific metrics"""
        try:
            # Extract premiums
            atm_call_credit = -legs[0]['premium']  # Short
            atm_put_credit = -legs[1]['premium']   # Short
            otm_call_debit = legs[2]['premium']    # Long
            otm_put_debit = legs[3]['premium']     # Long
            
            # Net credit (usually positive for iron butterfly)
            net_credit = -(atm_call_credit + atm_put_credit) - otm_call_debit - otm_put_debit
            
            # Max profit/loss
            max_profit = net_credit
            wing_width = upper_strike - atm_strike  # Assuming symmetric
            max_loss = wing_width - net_credit
            
            # Breakevens
            upper_breakeven = atm_strike + net_credit
            lower_breakeven = atm_strike - net_credit
            
            # Probability calculations
            prob_profit_upper = self._calculate_probability_itm(
                upper_breakeven, spot_price, market_analysis, 'CALL'
            )
            prob_profit_lower = 1 - self._calculate_probability_itm(
                lower_breakeven, spot_price, market_analysis, 'PUT'
            )
            
            probability_profit = prob_profit_upper * prob_profit_lower
            
            # Sweet spot probability (within 50% of max profit zone)
            sweet_spot_upper = atm_strike + (net_credit * 0.5)
            sweet_spot_lower = atm_strike - (net_credit * 0.5)
            
            # Greeks
            total_delta = sum(leg['delta'] * (-1 if leg['position'] == 'SHORT' else 1) 
                            for leg in legs)
            total_gamma = sum(leg.get('gamma', 0) * (-1 if leg['position'] == 'SHORT' else 1) 
                            for leg in legs)
            total_theta = sum(leg.get('theta', 0) * (-1 if leg['position'] == 'SHORT' else 1) 
                            for leg in legs)
            total_vega = sum(leg.get('vega', 0) * (-1 if leg['position'] == 'SHORT' else 1) 
                           for leg in legs)
            
            # Risk metrics
            risk_reward = max_profit / max_loss if max_loss > 0 else float('inf')
            profit_zone_width = upper_breakeven - lower_breakeven
            profit_zone_pct = (profit_zone_width / spot_price) * 100
            
            return {
                'legs': legs,
                'max_profit': max_profit,
                'max_loss': max_loss,
                'probability_profit': probability_profit,
                'net_credit': net_credit,
                'breakevens': {
                    'upper': upper_breakeven,
                    'lower': lower_breakeven,
                    'profit_zone_width': profit_zone_width,
                    'profit_zone_pct': profit_zone_pct
                },
                'strikes': {
                    'lower_wing': lower_strike,
                    'body': atm_strike,
                    'upper_wing': upper_strike,
                    'wing_width': wing_width
                },
                'greeks': {
                    'delta': total_delta,
                    'gamma': total_gamma,
                    'theta': total_theta,
                    'vega': total_vega
                },
                'risk_metrics': {
                    'risk_reward': risk_reward,
                    'max_risk_pct': (max_loss / spot_price) * 100,
                    'return_on_risk': (max_profit / max_loss) * 100 if max_loss > 0 else 0
                },
                'optimal_conditions': {
                    'iv_environment': 'High (>60th percentile)',
                    'market_outlook': 'Neutral with pin risk',
                    'time_to_expiry': '30-45 days',
                    'expected_movement': 'Minimal (<2%)'
                }
            }
            
        except Exception as e:
            logger.error(f"Error calculating Iron Butterfly metrics: {e}")
            return {
                    'success': False,
                    'reason': 'Unable to construct Butterfly Spread - need liquid strikes'
                }