"""
Cash-Secured Put Strategy Implementation
Income generation strategy for neutral to slightly bullish outlook
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

class CashSecuredPut(BaseStrategy):
    """
    Cash-Secured Put: Sell a put option while holding enough cash to buy shares if assigned
    Income strategy for neutral to bullish outlook
    """
    
    def get_strategy_name(self) -> str:
        return "Cash-Secured Put"
    
    def get_market_outlook(self) -> str:
        return "neutral_bullish"
    
    def get_iv_preference(self) -> str:
        return "high"  # Benefits from high IV for premium collection
    
    def construct_strategy(self, target_delta: float = 0.3, **kwargs) -> Dict:
        """
        Construct Cash-Secured Put strategy
        
        Args:
            target_delta: Target delta for put selection (0.2-0.4 typical)
        """
        try:
            # Filter PUT options
            puts_df = self.options_df[self.options_df['option_type'] == 'PUT'].copy()
            
            if puts_df.empty:
                return {
                    'success': False,
                    'reason': 'No PUT options available'
                }
            
            # Find OTM puts for selling
            otm_puts = puts_df[puts_df['strike'] < self.spot_price].sort_values('strike', ascending=False)
            
            if otm_puts.empty:
                return {
                    'success': False,
                    'reason': 'No OTM PUT strikes available'
                }
            
            # Select strike based on delta or fallback to nearest OTM
            if 'delta' in otm_puts.columns and not otm_puts['delta'].isna().all():
                # Find strike closest to target delta
                otm_puts['delta_diff'] = abs(abs(otm_puts['delta']) - target_delta)
                selected_idx = otm_puts['delta_diff'].idxmin()
                selected_strike = otm_puts.loc[selected_idx, 'strike']
            else:
                # Fallback: Select strike ~2-5% below current price
                target_strike = self.spot_price * 0.95
                selected_strike = self._find_nearest_available_strike(target_strike, 'PUT')
                
                if selected_strike is None:
                    # Further fallback: just take the highest OTM put
                    selected_strike = otm_puts.iloc[0]['strike']
            
            # Get option details
            put_data = self._get_option_data(selected_strike, 'PUT')
            
            if put_data is None:
                return {
                    'success': False,
                    'reason': f'Option data not available for strike {selected_strike}'
                }
            
            premium = put_data['last_price']
            
            # Validate minimum premium (at least 0.5% of strike)
            min_premium = selected_strike * 0.005
            if premium < min_premium:
                return {
                    'success': False,
                    'reason': 'Premium too low for cash-secured put'
                }
            
            # Build strategy
            self.legs = [{
                'option_type': 'PUT',
                'strike': selected_strike,
                'position': 'SHORT',
                'quantity': 1,
                'premium': premium,
                'delta': put_data.get('delta', 0),
                'theta': put_data.get('theta', 0),
                'gamma': put_data.get('gamma', 0),
                'vega': put_data.get('vega', 0),
                'iv': put_data.get('iv', 0)
            }]
            
            # Calculate metrics
            max_profit = premium
            max_loss = selected_strike - premium  # If assigned
            breakeven = selected_strike - premium
            
            # Return on risk (annualized if weekly option)
            days_to_expiry = self._get_days_to_expiry()
            cash_required = selected_strike  # Cash secured
            return_on_cash = (premium / cash_required) * (365 / days_to_expiry) * 100
            
            # Assignment probability (roughly inverse of delta)
            assignment_prob = abs(put_data.get('delta', 0.3))
            
            # Apply lot size multiplier for real position sizing
            total_max_profit = max_profit * self.lot_size
            total_max_loss = max_loss * self.lot_size
            total_premium = premium * self.lot_size
            total_cash_required = cash_required * self.lot_size
            
            return {
                'success': True,
                'strategy_name': self.get_strategy_name(),
                'legs': self.legs,
                'net_premium': total_premium,
                'max_profit': total_max_profit,
                'max_loss': total_max_loss,
                'breakeven': breakeven,
                'cash_required': total_cash_required,
                'return_on_cash_annualized': round(return_on_cash, 2),
                'assignment_probability': round(assignment_prob, 3),
                'net_greeks': {
                    'delta': -put_data.get('delta', 0),
                    'theta': -put_data.get('theta', 0),
                    'gamma': -put_data.get('gamma', 0),
                    'vega': -put_data.get('vega', 0)
                },
                'strategy_type': 'income',
                'optimal_outcome': f'Stock stays above {selected_strike} at expiry',
                'risk_note': f'Obligated to buy {self.lot_size} shares at {selected_strike} if assigned',
                'position_details': {
                    'lot_size': self.lot_size,
                    'premium_per_share': premium,
                    'total_premium': total_premium,
                    'cash_per_share': cash_required,
                    'total_cash_required': total_cash_required
                }
            }
            
        except Exception as e:
            logger.error(f"Error constructing Cash-Secured Put: {e}")
            return {
                'success': False,
                'reason': f'Construction error: {str(e)}'
            }