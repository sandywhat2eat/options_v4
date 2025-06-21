"""
Covered Call Strategy Implementation
Income generation strategy for stock holders
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

class CoveredCall(BaseStrategy):
    """
    Covered Call: Sell a call option against owned stock
    Income strategy for neutral to slightly bullish outlook
    """
    
    def get_strategy_name(self) -> str:
        return "Covered Call"
    
    def get_market_outlook(self) -> str:
        return "neutral_bullish"
    
    def get_iv_preference(self) -> str:
        return "high"  # Benefits from high IV for premium collection
    
    def construct_strategy(self, target_delta: float = 0.3, **kwargs) -> Dict:
        """
        Construct Covered Call strategy
        
        Args:
            target_delta: Target delta for call selection (0.2-0.4 typical)
        """
        try:
            # Filter CALL options
            calls_df = self.options_df[self.options_df['option_type'] == 'CALL'].copy()
            
            if calls_df.empty:
                return {
                    'success': False,
                    'reason': 'No CALL options available'
                }
            
            # Find OTM calls for selling
            otm_calls = calls_df[calls_df['strike'] > self.spot_price].sort_values('strike')
            
            if otm_calls.empty:
                # If no OTM calls, try ATM
                atm_strike = self._find_atm_strike('CALL')
                if atm_strike:
                    otm_calls = calls_df[calls_df['strike'] == atm_strike]
                else:
                    return {
                        'success': False,
                        'reason': 'No suitable CALL strikes available'
                    }
            
            # Select strike based on delta or fallback to nearest OTM
            if 'delta' in otm_calls.columns and not otm_calls['delta'].isna().all():
                # Find strike closest to target delta
                otm_calls['delta_diff'] = abs(otm_calls['delta'] - target_delta)
                selected_idx = otm_calls['delta_diff'].idxmin()
                selected_strike = otm_calls.loc[selected_idx, 'strike']
            else:
                # Fallback: Select strike ~2-5% above current price
                target_strike = self.spot_price * 1.03
                selected_strike = self._find_nearest_available_strike(target_strike, 'CALL')
                
                if selected_strike is None:
                    # Further fallback: just take the lowest OTM call
                    selected_strike = otm_calls.iloc[0]['strike']
            
            # Get option details
            call_data = self._get_option_data(selected_strike, 'CALL')
            
            if call_data is None:
                return {
                    'success': False,
                    'reason': f'Option data not available for strike {selected_strike}'
                }
            
            premium = call_data['last_price']
            
            # Validate minimum premium (at least 0.5% of stock price)
            min_premium = self.spot_price * 0.005
            if premium < min_premium:
                return {
                    'success': False,
                    'reason': 'Premium too low for covered call'
                }
            
            # Build strategy
            self.legs = [{
                'option_type': 'CALL',
                'strike': selected_strike,
                'position': 'SHORT',
                'quantity': 1,
                'premium': premium,
                'delta': call_data.get('delta', 0),
                'theta': call_data.get('theta', 0),
                'gamma': call_data.get('gamma', 0),
                'vega': call_data.get('vega', 0),
                'iv': call_data.get('iv', 0),
                'note': 'Against 1 lot of owned stock'
            }]
            
            # Calculate metrics
            max_profit = (selected_strike - self.spot_price) + premium
            max_loss = self.spot_price - premium  # If stock goes to zero
            breakeven = self.spot_price - premium
            
            # Return calculations
            days_to_expiry = self._get_days_to_expiry()
            stock_value = self.spot_price
            
            # Return if called away
            return_if_called = ((selected_strike + premium - self.spot_price) / self.spot_price) * 100
            
            # Return from premium only (annualized)
            premium_return = (premium / stock_value) * (365 / days_to_expiry) * 100
            
            # Probability of being called away
            call_away_prob = call_data.get('delta', 0.3)
            
            return {
                'success': True,
                'strategy_name': self.get_strategy_name(),
                'legs': self.legs,
                'net_premium': premium,
                'max_profit': max_profit,
                'max_loss': max_loss,
                'breakeven': breakeven,
                'stock_required': '1 lot',
                'return_if_called_pct': round(return_if_called, 2),
                'premium_return_annualized': round(premium_return, 2),
                'call_away_probability': round(call_away_prob, 3),
                'net_greeks': {
                    'delta': 1 - call_data.get('delta', 0),  # Stock delta (1) minus call delta
                    'theta': -call_data.get('theta', 0),
                    'gamma': -call_data.get('gamma', 0),
                    'vega': -call_data.get('vega', 0)
                },
                'strategy_type': 'income',
                'optimal_outcome': f'Stock stays below {selected_strike} or gets called at profit',
                'risk_note': f'Upside capped at {selected_strike}, full downside risk minus premium'
            }
            
        except Exception as e:
            logger.error(f"Error constructing Covered Call: {e}")
            return {
                'success': False,
                'reason': f'Construction error: {str(e)}'
            }