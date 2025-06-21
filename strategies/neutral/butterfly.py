"""
Butterfly Spread Strategy - Precise range targeting
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import logging

from ..base_strategy import BaseStrategy

logger = logging.getLogger(__name__)

class ButterflySpread(BaseStrategy):
    """
    Butterfly Spread: Buy 1 ITM + Sell 2 ATM + Buy 1 OTM (same type)
    
    Market Outlook: Neutral with precise target
    Profit: Maximum at middle strike
    Risk: Limited to net debit
    Ideal: Low volatility, specific price target
    """
    
    def get_strategy_name(self) -> str:
        return "Butterfly Spread"
    
    def get_market_outlook(self) -> str:
        return "neutral"
    
    def get_iv_preference(self) -> str:
        return "high"
    
    def get_required_legs(self) -> int:
        return 4  # Can be 3 unique strikes with 2x ATM
    
    def get_market_bias(self) -> List[str]:
        return ['neutral', 'low_volatility']
    
    def construct_strategy(self, **kwargs) -> Dict:
        """Construct butterfly spread centered at spot"""
        market_analysis = kwargs.get('market_analysis', {})
        
        try:
            
            # Decide on call or put butterfly based on skew
            iv_skew = market_analysis.get('iv_analysis', {}).get('iv_skew', {})
            use_puts = iv_skew.get('skew_type') == 'put_skew'
            
            option_type = 'PUT' if use_puts else 'CALL'
            type_options = self.options_df[self.options_df['option_type'] == option_type]
            
            if len(type_options) < 3:
                return None
            
            # Find strikes for butterfly
            # Center at ATM, wings at ~2-3% away
            strikes = sorted(type_options['strike'].unique())
            atm_strike = min(strikes, key=lambda x: abs(x - self.spot_price))
            
            # Find wing strikes
            wing_distance = self.spot_price * 0.025  # 2.5% wings
            
            lower_strikes = [s for s in strikes if s < atm_strike - wing_distance/2]
            upper_strikes = [s for s in strikes if s > atm_strike + wing_distance/2]
            
            if not lower_strikes or not upper_strikes:
                return None
            
            # Select strikes
            lower_strike = max(lower_strikes)  # Closest to ATM
            upper_strike = min(upper_strikes)  # Closest to ATM
            
            # Validate strikes are available
            if not self.validate_strikes([lower_strike, atm_strike, upper_strike]):
                return None
            
            # Get options data for each strike
            lower_data = self._get_option_data(lower_strike, option_type)
            atm_data = self._get_option_data(atm_strike, option_type)
            upper_data = self._get_option_data(upper_strike, option_type)
            
            if any(data is None for data in [lower_data, atm_data, upper_data]):
                return None
            
            # Create legs
            legs = [
                {
                    'option_type': option_type,
                    'position': 'LONG',
                    'strike': lower_strike,
                    'premium': lower_data.get('last_price', 0),
                    'delta': lower_data.get('delta', 0),
                    'gamma': lower_data.get('gamma', 0),
                    'theta': lower_data.get('theta', 0),
                    'vega': lower_data.get('vega', 0),
                    'quantity': 1,
                    'rationale': f'Lower wing at {lower_strike}'
                },
                {
                    'option_type': option_type,
                    'position': 'SHORT',
                    'strike': atm_strike,
                    'premium': atm_data.get('last_price', 0),
                    'delta': atm_data.get('delta', 0),
                    'gamma': atm_data.get('gamma', 0),
                    'theta': atm_data.get('theta', 0),
                    'vega': atm_data.get('vega', 0),
                    'quantity': 2,
                    'rationale': f'Body at {atm_strike} (2x)'
                },
                {
                    'option_type': option_type,
                    'position': 'LONG',
                    'strike': upper_strike,
                    'premium': upper_data.get('last_price', 0),
                    'delta': upper_data.get('delta', 0),
                    'gamma': upper_data.get('gamma', 0),
                    'theta': upper_data.get('theta', 0),
                    'vega': upper_data.get('vega', 0),
                    'quantity': 1,
                    'rationale': f'Upper wing at {upper_strike}'
                }
            ]
            
            # Calculate strategy metrics
            metrics = self._calculate_metrics(
                legs, self.spot_price, market_analysis, 
                lower_strike, atm_strike, upper_strike
            )
            
            if not metrics:
                return None
            
            # Add exit conditions
            metrics['exit_conditions'] = {
                'profit_target': '50-70% of max profit',
                'stop_loss': 'If loss exceeds 50% of max risk',
                'time_exit': '50% time decay or 10 DTE',
                'price_exit': 'If price moves beyond wings',
                'adjustment': 'Roll untested wing if directional move'
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error constructing Butterfly Spread: {e}")
            return None
    
    def _calculate_metrics(self, legs: List[Dict], spot_price: float,
                         market_analysis: Dict, lower_strike: float,
                         atm_strike: float, upper_strike: float) -> Optional[Dict]:
        """Calculate butterfly specific metrics"""
        try:
            # Extract premiums
            lower_premium = legs[0]['premium']
            atm_premium = legs[1]['premium'] * 2  # Sold 2x
            upper_premium = legs[2]['premium']
            
            # Net debit (usually)
            net_debit = lower_premium - atm_premium + upper_premium
            
            # Max profit at ATM strike
            max_profit = (atm_strike - lower_strike) - net_debit
            max_loss = net_debit
            
            # Breakevens
            lower_breakeven = lower_strike + net_debit
            upper_breakeven = upper_strike - net_debit
            
            # Probability calculations
            # Simplified probability estimate
            profit_range = upper_breakeven - lower_breakeven
            range_pct = (profit_range / spot_price) * 100
            probability_profit = max(0.2, min(0.7, 0.5 + (range_pct - 8) * 0.02))
            
            # Sweet spot probability (within 1% of ATM strike)
            sweet_spot_range = atm_strike * 0.01
            prob_sweet_spot = 0.15  # Conservative estimate
            
            # Risk metrics
            risk_reward = max_profit / max_loss if max_loss > 0 else float('inf')
            
            # Greeks (simplified)
            total_delta = sum(leg['delta'] * leg['quantity'] for leg in legs)
            total_gamma = sum(leg.get('gamma', 0) * leg['quantity'] for leg in legs)
            total_theta = sum(leg.get('theta', 0) * leg['quantity'] for leg in legs)
            total_vega = sum(leg.get('vega', 0) * leg['quantity'] for leg in legs)
            
            return {
                'legs': legs,
                'max_profit': max_profit,
                'max_loss': max_loss,
                'probability_profit': probability_profit,
                'breakevens': {
                    'lower': lower_breakeven,
                    'upper': upper_breakeven,
                    'sweet_spot': atm_strike,
                    'sweet_spot_probability': prob_sweet_spot
                },
                'strikes': {
                    'lower': lower_strike,
                    'middle': atm_strike,
                    'upper': upper_strike,
                    'width': upper_strike - lower_strike
                },
                'greeks': {
                    'delta': total_delta,
                    'gamma': total_gamma,
                    'theta': total_theta,
                    'vega': total_vega
                },
                'risk_metrics': {
                    'risk_reward': risk_reward,
                    'max_risk_pct': (max_loss / spot_price) * 100
                },
                'optimal_conditions': {
                    'iv_environment': 'Normal to high',
                    'market_outlook': 'Neutral with specific target',
                    'time_to_expiry': '30-60 days',
                    'expected_movement': 'Minimal'
                }
            }
            
        except Exception as e:
            logger.error(f"Error calculating Butterfly metrics: {e}")
            return None
    
    def _calculate_probability_range(self, lower: float, upper: float,
                                   spot: float, market_analysis: Dict) -> float:
        """Calculate probability of price ending in range"""
        try:
            # Simplified calculation using normal distribution assumption
            iv = market_analysis.get('iv_analysis', {}).get('atm_iv', 30) / 100
            days_to_expiry = 30  # Assumption
            
            # Standard deviation
            std_dev = spot * iv * np.sqrt(days_to_expiry / 365)
            
            # Z-scores
            z_lower = (lower - spot) / std_dev
            z_upper = (upper - spot) / std_dev
            
            # Probability using normal CDF
            from scipy import stats
            prob = stats.norm.cdf(z_upper) - stats.norm.cdf(z_lower)
            
            return prob
            
        except:
            # Fallback
            return 0.15  # Conservative estimate