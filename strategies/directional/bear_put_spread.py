"""
Bear Put Spread Strategy Implementation
Debit spread strategy for bearish outlook
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, Optional, List
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ..base_strategy import BaseStrategy

logger = logging.getLogger(__name__)

class BearPutSpreadStrategy(BaseStrategy):
    """
    Bear Put Spread: Buy higher strike put, sell lower strike put
    Net debit strategy for moderately bearish outlook
    """
    
    def get_strategy_name(self) -> str:
        return "Bear Put Spread"
    
    def get_market_outlook(self) -> str:
        return "bearish"
    
    def get_iv_preference(self) -> str:
        return "low"  # Debit strategy benefits from low IV
    
    def construct_strategy(self, **kwargs) -> Dict:
        """Construct Bear Put Spread"""
        try:
            # Filter PUT options
            puts_df = self.options_df[self.options_df['option_type'] == 'PUT'].copy()
            
            if len(puts_df) < 2:
                return {
                    'success': False,
                    'reason': 'Insufficient PUT options for spread'
                }
            
            # Find strikes for bear put spread
            # Buy ITM/ATM put, sell OTM put
            atm_strike = self._find_atm_strike('PUT')
            if atm_strike is None:
                return {
                    'success': False,
                    'reason': 'Unable to find ATM strike'
                }
            
            # Get strikes around ATM
            all_strikes = sorted(puts_df['strike'].unique())
            atm_idx = all_strikes.index(atm_strike)
            
            # Select strikes
            if atm_idx < len(all_strikes) - 1:
                long_strike = atm_strike  # Buy ATM
                short_strike = all_strikes[atm_idx - 1] if atm_idx > 0 else all_strikes[atm_idx + 1]
            else:
                # If ATM is the highest strike, adjust selection
                long_strike = all_strikes[atm_idx - 1] if atm_idx > 0 else atm_strike
                short_strike = all_strikes[atm_idx - 2] if atm_idx > 1 else all_strikes[0]
            
            # Ensure proper ordering (long strike > short strike)
            if long_strike <= short_strike:
                long_strike, short_strike = short_strike, long_strike
            
            # Get option details
            long_put = self._get_option_data(long_strike, 'PUT')
            short_put = self._get_option_data(short_strike, 'PUT')
            
            if long_put is None or short_put is None:
                return {
                    'success': False,
                    'reason': 'Unable to fetch option data for selected strikes'
                }
            
            # Calculate net premium (debit)
            net_premium = long_put['last_price'] - short_put['last_price']
            
            if net_premium <= 0:
                return {
                    'success': False,
                    'reason': 'Invalid premium calculation for bear put spread'
                }
            
            # Build strategy
            legs = [
                {
                    'option_type': 'PUT',
                    'strike': long_strike,
                    'position': 'LONG',
                    'quantity': 1,
                    'premium': long_put['last_price'],
                    'delta': long_put.get('delta', 0),
                    'theta': long_put.get('theta', 0),
                    'gamma': long_put.get('gamma', 0),
                    'vega': long_put.get('vega', 0),
                    'iv': long_put.get('iv', 0)
                },
                {
                    'option_type': 'PUT',
                    'strike': short_strike,
                    'position': 'SHORT',
                    'quantity': 1,
                    'premium': short_put['last_price'],
                    'delta': short_put.get('delta', 0),
                    'theta': short_put.get('theta', 0),
                    'gamma': short_put.get('gamma', 0),
                    'vega': short_put.get('vega', 0),
                    'iv': short_put.get('iv', 0)
                }
            ]
            
            # Calculate max profit/loss
            strike_width = long_strike - short_strike
            max_profit = strike_width - net_premium
            max_loss = net_premium
            
            # Calculate breakeven
            breakeven = long_strike - net_premium
            
            # Net Greeks
            net_delta = long_put.get('delta', 0) - short_put.get('delta', 0)
            net_theta = long_put.get('theta', 0) - short_put.get('theta', 0)
            net_gamma = long_put.get('gamma', 0) - short_put.get('gamma', 0)
            net_vega = long_put.get('vega', 0) - short_put.get('vega', 0)
            
            return {
                'success': True,
                'strategy_name': self.get_strategy_name(),
                'legs': legs,
                'net_premium': -net_premium,  # Negative for debit
                'max_profit': max_profit,
                'max_loss': max_loss,
                'breakeven': breakeven,
                'net_greeks': {
                    'delta': net_delta,
                    'theta': net_theta,
                    'gamma': net_gamma,
                    'vega': net_vega
                },
                'spread_width': strike_width,
                'margin_required': net_premium,
                'strategy_type': 'debit_spread'
            }
            
        except Exception as e:
            logger.error(f"Error constructing Bear Put Spread: {e}")
            return {
                'success': False,
                'reason': f'Construction error: {str(e)}'
            }