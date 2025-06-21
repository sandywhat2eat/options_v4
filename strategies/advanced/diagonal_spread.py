"""
Diagonal Spread Strategy - Calendar with different strikes
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import logging

from ..base_strategy import BaseStrategy

logger = logging.getLogger(__name__)

class DiagonalSpread(BaseStrategy):
    """
    Diagonal Spread: Sell near-term OTM + Buy far-term ATM/ITM
    
    Market Outlook: Directional with time decay benefit
    Profit: From time decay and directional movement
    Risk: Limited to net debit
    Ideal: Trending markets with IV term structure
    """
    
    def get_strategy_name(self) -> str:
        return "Diagonal Spread"
    
    def get_market_outlook(self) -> str:
        return "bullish"
    
    def get_iv_preference(self) -> str:
        return "low"
    
    def get_required_legs(self) -> int:
        return 2
    
    def get_market_bias(self) -> List[str]:
        return ['moderate_bullish', 'moderate_bearish', 'time_decay']
    
    def construct_strategy(self, **kwargs) -> Dict:
        """Construct diagonal spread"""
        market_analysis = kwargs.get('market_analysis', {})
        # Removed self.spot_price extraction - using self.spot_price
        market_analysis = kwargs.get('market_analysis', {})
        
        try:
            # Check if we have multiple expiries
            if 'expiry' not in options_df.columns:
                return None
            
            unique_expiries = sorted(options_df['expiry'].unique())
            if len(unique_expiries) < 2:
                return None
            
            # Use first two expiries
            near_expiry = unique_expiries[0]
            far_expiry = unique_expiries[1]
            
            # Get market direction
            direction = market_analysis.get('direction', 'neutral').lower()
            
            # Decide on calls or puts based on direction
            if 'bullish' in direction:
                option_type = 'CALL'
                use_calls = True
            elif 'bearish' in direction:
                option_type = 'PUT'
                use_calls = False
            else:
                # Neutral - skip diagonal
                return None
            
            # Filter options
            near_options = self._filter_liquid_options(
                options_df[(options_df['expiry'] == near_expiry) & 
                          (options_df['option_type'] == option_type)]
            )
            far_options = self._filter_liquid_options(
                options_df[(options_df['expiry'] == far_expiry) & 
                          (options_df['option_type'] == option_type)]
            )
            
            if near_options.empty or far_options.empty:
                return None
            
            # Strike selection
            if use_calls:
                # Bull diagonal: sell OTM call, buy ATM/ITM call
                far_strike = min(far_options['strike'].unique(), 
                               key=lambda x: abs(x - self.spot_price))
                near_strikes = near_options[near_options['strike'] > self.spot_price * 1.02]['strike'].unique()
                if len(near_strikes) == 0:
                    return None
                near_strike = min(near_strikes)
            else:
                # Bear diagonal: sell OTM put, buy ATM/ITM put
                far_strike = min(far_options['strike'].unique(), 
                               key=lambda x: abs(x - self.spot_price))
                near_strikes = near_options[near_options['strike'] < self.spot_price * 0.98]['strike'].unique()
                if len(near_strikes) == 0:
                    return None
                near_strike = max(near_strikes)
            
            # Get options
            near_option = near_options[near_options['strike'] == near_strike].iloc[0]
            far_option = far_options[far_options['strike'] == far_strike].iloc[0]
            
            # Create legs
            legs = [
                self._create_leg(near_option, 'SHORT', 1, f'Sell {near_expiry} {near_strike}'),
                self._create_leg(far_option, 'LONG', 1, f'Buy {far_expiry} {far_strike}')
            ]
            
            # Calculate strategy metrics
            metrics = self._calculate_metrics(
                legs, self.spot_price, market_analysis,
                use_calls, direction
            )
            
            if not metrics:
                return None
            
            # Add exit conditions
            metrics['exit_conditions'] = {
                'profit_target': '30-50% of max profit potential',
                'stop_loss': 'If debit loses 50% of value',
                'time_exit': 'Roll or close before near expiry',
                'directional_exit': 'If direction reverses',
                'adjustment': 'Roll short strike if tested'
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error constructing Diagonal Spread: {e}")
            return None
    
    def _calculate_metrics(self, legs: List[Dict], spot_price: float,
                         market_analysis: Dict, use_calls: bool,
                         direction: str) -> Optional[Dict]:
        """Calculate diagonal spread metrics"""
        try:
            # Extract details
            near_premium = -legs[0]['premium']  # Short
            far_premium = legs[1]['premium']    # Long
            
            net_debit = far_premium - near_premium
            
            # Diagonal P&L is complex
            # Estimate based on intrinsic value potential
            near_strike = legs[0]['strike']
            far_strike = legs[1]['strike']
            
            if use_calls:
                # Bull diagonal
                if self.spot_price > far_strike:
                    intrinsic_value = self.spot_price - far_strike
                else:
                    intrinsic_value = 0
                max_profit_estimate = near_strike - far_strike + near_premium
            else:
                # Bear diagonal
                if self.spot_price < far_strike:
                    intrinsic_value = far_strike - self.spot_price
                else:
                    intrinsic_value = 0
                max_profit_estimate = far_strike - near_strike + near_premium
            
            max_loss = net_debit
            
            # Greeks
            net_delta = legs[1]['delta'] - legs[0]['delta']
            net_theta = -legs[0].get('theta', 0) + legs[1].get('theta', 0)
            net_vega = -legs[0].get('vega', 0) + legs[1].get('vega', 0)
            
            # Probability estimate
            if use_calls:
                target_price = near_strike
                prob_profit = 1 - self._calculate_probability_itm(
                    target_price, self.spot_price, market_analysis, 'CALL'
                )
            else:
                target_price = near_strike
                prob_profit = self._calculate_probability_itm(
                    target_price, self.spot_price, market_analysis, 'PUT'
                )
            
            return {
                'legs': legs,
                'max_profit_estimate': max_profit_estimate,
                'max_loss': max_loss,
                'probability_profit': prob_profit,
                'net_debit': net_debit,
                'direction': direction,
                'strikes': {
                    'near_strike': near_strike,
                    'far_strike': far_strike,
                    'strike_difference': abs(near_strike - far_strike),
                    'diagonal_type': 'Bull Diagonal' if use_calls else 'Bear Diagonal'
                },
                'greeks': {
                    'delta': net_delta,
                    'theta': net_theta,
                    'vega': net_vega,
                    'positive_theta': net_theta > 0
                },
                'risk_metrics': {
                    'risk_reward': max_profit_estimate / max_loss if max_loss > 0 else 0,
                    'debit_as_pct': (net_debit / self.spot_price) * 100
                },
                'optimal_conditions': {
                    'market_outlook': f'{direction.title()} with time decay benefit',
                    'iv_environment': 'Favorable term structure',
                    'price_target': f'Move toward {near_strike}',
                    'time_decay': 'Accelerating in near term'
                }
            }
            
        except Exception as e:
            logger.error(f"Error calculating Diagonal Spread metrics: {e}")
            return None