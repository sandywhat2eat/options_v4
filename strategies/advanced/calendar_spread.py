"""
Calendar Spread Strategy - Time decay exploitation
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import logging

from ..base_strategy import BaseStrategy

logger = logging.getLogger(__name__)

class CalendarSpread(BaseStrategy):
    """
    Calendar Spread: Sell near-term option + Buy far-term option (same strike)
    
    Market Outlook: Neutral with IV expansion expected
    Profit: From faster time decay of near-term option
    Risk: Limited to net debit paid
    Ideal: Low IV in front month, expecting stability
    """
    
    def get_strategy_name(self) -> str:
        return "Calendar Spread"
    
    def get_market_outlook(self) -> str:
        return "neutral"
    
    def get_iv_preference(self) -> str:
        return "low"
    
    def get_required_legs(self) -> int:
        return 2
    
    def get_market_bias(self) -> List[str]:
        return ['neutral', 'low_volatility']
    
    def construct_strategy(self, **kwargs) -> Dict:
        """Construct calendar spread at ATM strike"""
        market_analysis = kwargs.get('market_analysis', {})
        
        try:
            # Check if we have multiple expiries
            if 'expiry' not in self.options_df.columns:
                logger.info("No expiry information for Calendar Spread")
                return None
            
            unique_expiries = sorted(self.options_df['expiry'].unique())
            if len(unique_expiries) < 2:
                logger.info("Need at least 2 expiries for Calendar Spread")
                return None
            
            # Use first two expiries
            near_expiry = unique_expiries[0]
            far_expiry = unique_expiries[1]
            
            # Filter options for each expiry
            near_options = self.options_df[self.options_df['expiry'] == near_expiry]
            far_options = self.options_df[self.options_df['expiry'] == far_expiry]
            
            if near_options.empty or far_options.empty:
                return None
            
            # Find ATM strike available in both expiries
            strikes = set(near_options['strike'].unique()) & set(far_options['strike'].unique())
            if not strikes:
                return None
            
            atm_strike = min(strikes, key=lambda x: abs(x - self.spot_price))
            
            # Decide on calls or puts based on skew
            iv_skew = market_analysis.get('iv_analysis', {}).get('iv_skew', {})
            use_puts = iv_skew.get('skew_type') == 'put_skew'
            
            option_type = 'PUT' if use_puts else 'CALL'
            
            # Get options
            near_option = near_options[
                (near_options['strike'] == atm_strike) & 
                (near_options['option_type'] == option_type)
            ]
            far_option = far_options[
                (far_options['strike'] == atm_strike) & 
                (far_options['option_type'] == option_type)
            ]
            
            if near_option.empty or far_option.empty:
                return None
            
            # Validate strikes
            if not self.validate_strikes([atm_strike]):
                return None
            
            # Get option data
            near_data = self._get_option_data(atm_strike, option_type)
            far_data = self._get_option_data(atm_strike, option_type)
            
            if near_data is None or far_data is None:
                return None
            
            # Create legs
            legs = [
                {
                    'option_type': option_type,
                    'position': 'SHORT',
                    'strike': atm_strike,
                    'premium': near_data.get('last_price', 0),
                    'delta': near_data.get('delta', 0),
                    'expiry': near_expiry,
                    'rationale': f'Sell {near_expiry} {option_type}'
                },
                {
                    'option_type': option_type,
                    'position': 'LONG',
                    'strike': atm_strike,
                    'premium': far_data.get('last_price', 0),
                    'delta': far_data.get('delta', 0),
                    'expiry': far_expiry,
                    'rationale': f'Buy {far_expiry} {option_type}'
                }
            ]
            
            # Calculate strategy metrics
            metrics = self._calculate_metrics(
                legs, self.spot_price, market_analysis,
                near_expiry, far_expiry, atm_strike
            )
            
            if not metrics:
                return None
            
            # Add exit conditions
            metrics['exit_conditions'] = {
                'profit_target': '25-40% of max profit potential',
                'stop_loss': 'If debit loses 50% of value',
                'time_exit': 'Close before near-term expiry',
                'volatility_exit': 'If IV contracts in back month',
                'adjustment': 'Roll to next expiry cycle if profitable'
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error constructing Calendar Spread: {e}")
            return None
    
    def _calculate_metrics(self, legs: List[Dict], spot_price: float,
                         market_analysis: Dict, near_expiry: str,
                         far_expiry: str, strike: float) -> Optional[Dict]:
        """Calculate calendar spread specific metrics"""
        try:
            # Extract premiums
            near_credit = -legs[0]['premium']  # Short near-term
            far_debit = legs[1]['premium']     # Long far-term
            
            # Net debit
            net_debit = far_debit - near_credit
            
            # Calendar spreads have complex P&L profiles
            # Max profit occurs at strike at near-term expiry
            # Approximate max profit as 20-30% of debit
            estimated_max_profit = net_debit * 0.25
            max_loss = net_debit
            
            # Breakevens are complex for calendars
            # Approximate based on strike and debit
            approx_upper_be = strike + (net_debit * 2)
            approx_lower_be = strike - (net_debit * 2)
            
            # Probability of profit
            # Calendar profits when price stays near strike
            range_width = strike * 0.05  # 5% range
            prob_in_range = self._calculate_probability_range(
                strike - range_width,
                strike + range_width,
                spot_price,
                market_analysis
            )
            
            # Greeks (complex for calendar)
            # Near-term short has negative theta, far-term long has positive
            net_theta = -legs[0].get('theta', 0) + legs[1].get('theta', 0)
            net_vega = -legs[0].get('vega', 0) + legs[1].get('vega', 0)
            
            # IV analysis
            near_iv = legs[0].get('iv', 30)
            far_iv = legs[1].get('iv', 30)
            iv_spread = far_iv - near_iv
            
            # Time analysis
            # Calculate days between expiries
            days_between = 30  # Placeholder - would calculate from actual dates
            
            return {
                'legs': legs,
                'max_profit': estimated_max_profit,
                'max_loss': max_loss,
                'probability_profit': prob_in_range,
                'net_debit': net_debit,
                'expiries': {
                    'near': near_expiry,
                    'far': far_expiry,
                    'days_between': days_between
                },
                'breakevens': {
                    'upper_approx': approx_upper_be,
                    'lower_approx': approx_lower_be,
                    'sweet_spot': strike,
                    'profit_range': range_width * 2
                },
                'greeks': {
                    'theta': net_theta,
                    'vega': net_vega,
                    'theta_ratio': abs(legs[0].get('theta', 1)) / abs(legs[1].get('theta', 1))
                },
                'iv_analysis': {
                    'near_iv': near_iv,
                    'far_iv': far_iv,
                    'iv_spread': iv_spread,
                    'favorable_spread': iv_spread > 0
                },
                'risk_metrics': {
                    'risk_reward': estimated_max_profit / max_loss,
                    'debit_as_pct': (net_debit / spot_price) * 100
                },
                'optimal_conditions': {
                    'iv_environment': 'Low front month, higher back month',
                    'market_outlook': 'Neutral to mildly directional',
                    'time_to_near_expiry': '20-40 days',
                    'price_expectation': f'Pin near {strike}'
                }
            }
            
        except Exception as e:
            logger.error(f"Error calculating Calendar Spread metrics: {e}")
            return None
    
    def _calculate_probability_range(self, lower: float, upper: float,
                                   spot: float, market_analysis: Dict) -> float:
        """Calculate probability of price ending in range"""
        try:
            # Simplified - would use actual probability calculation
            iv = market_analysis.get('iv_analysis', {}).get('atm_iv', 30) / 100
            days = 30
            
            std_dev = spot * iv * np.sqrt(days / 365)
            
            z_lower = (lower - spot) / std_dev
            z_upper = (upper - spot) / std_dev
            
            # Using normal approximation
            from scipy import stats
            prob = stats.norm.cdf(z_upper) - stats.norm.cdf(z_lower)
            
            return prob
            
        except:
            return 0.4  # Default estimate