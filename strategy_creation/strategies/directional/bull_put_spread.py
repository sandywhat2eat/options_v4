"""
Bull Put Spread Strategy Implementation
Credit spread strategy for bullish outlook
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

class BullPutSpreadStrategy(BaseStrategy):
    """
    Bull Put Spread: Sell higher strike put, buy lower strike put
    Net credit strategy for moderately bullish outlook
    """
    
    def get_strategy_name(self) -> str:
        return "Bull Put Spread"
    
    def get_market_outlook(self) -> str:
        return "bullish"
    
    def get_iv_preference(self) -> str:
        return "high"  # Credit strategy benefits from high IV
    
    def construct_strategy(self, use_expected_moves: bool = True, **kwargs) -> Dict:
        """Construct Bull Put Spread"""
        try:
            # Find optimal strikes using intelligent selection
            if use_expected_moves and self.market_analysis and self.strike_selector:
                logger.info("Using intelligent strike selection for Bull Put Spread")
                short_strike, long_strike = self.strike_selector.select_spread_strikes(
                    self.options_df, self.spot_price, self.market_analysis, 'Bull Put Spread'
                )
                logger.info(f"Selected PUT strikes: Short {short_strike}, Long {long_strike}")
            else:
                # Fallback to traditional method
                logger.info("Using traditional strike selection")
                # Filter PUT options
                puts_df = self.options_df[self.options_df['option_type'] == 'PUT'].copy()
                
                if len(puts_df) < 2:
                    return {
                        'success': False,
                        'reason': 'Insufficient PUT options for spread'
                    }
                
                # Find strikes for bull put spread
                # Sell OTM put, buy further OTM put
                otm_puts = puts_df[puts_df['strike'] < self.spot_price].sort_values('strike', ascending=False)
                
                if len(otm_puts) < 2:
                    return {
                        'success': False,
                        'reason': 'Insufficient OTM PUT strikes'
                    }
                
                # Select strikes
                short_strike = otm_puts.iloc[0]['strike']  # Closer to ATM
                long_strike = otm_puts.iloc[1]['strike']   # Further OTM
            
            # Get option details
            short_put = self._get_option_data(short_strike, 'PUT')
            long_put = self._get_option_data(long_strike, 'PUT')
            
            if short_put is None or long_put is None:
                return {
                    'success': False,
                    'reason': 'Unable to fetch option data for selected strikes'
                }
            
            # Calculate net premium (credit)
            net_premium = short_put['last_price'] - long_put['last_price']
            
            if net_premium <= 0:
                return {
                    'success': False,
                    'reason': 'No net credit for spread'
                }
            
            # Build strategy
            legs = [
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
                },
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
                }
            ]
            
            # Calculate max profit/loss
            strike_width = short_strike - long_strike
            max_profit = net_premium
            max_loss = strike_width - net_premium
            
            # Calculate breakeven
            breakeven = short_strike - net_premium
            
            # Net Greeks
            net_delta = short_put.get('delta', 0) - long_put.get('delta', 0)
            net_theta = short_put.get('theta', 0) - long_put.get('theta', 0)
            net_gamma = short_put.get('gamma', 0) - long_put.get('gamma', 0)
            net_vega = short_put.get('vega', 0) - long_put.get('vega', 0)
            
            # Apply lot size multiplier for real position sizing
            total_max_profit = max_profit * self.lot_size
            total_max_loss = max_loss * self.lot_size
            total_net_premium = net_premium * self.lot_size
            
            return {
                'success': True,
                'strategy_name': self.get_strategy_name(),
                'legs': legs,
                'net_premium': total_net_premium,
                'max_profit': total_max_profit,
                'max_loss': total_max_loss,
                'breakeven': breakeven,
                'net_greeks': {
                    'delta': net_delta,
                    'theta': net_theta,
                    'gamma': net_gamma,
                    'vega': net_vega
                },
                'spread_width': strike_width,
                'margin_required': total_max_loss,
                'strategy_type': 'credit_spread',
                'position_details': {
                    'lot_size': self.lot_size,
                    'net_premium_per_lot': net_premium,
                    'max_profit_per_lot': max_profit,
                    'max_loss_per_lot': max_loss,
                    'total_contracts': self.lot_size * 2  # 2 legs
                }
            }
            
        except Exception as e:
            logger.error(f"Error constructing Bull Put Spread: {e}")
            return {
                'success': False,
                'reason': f'Construction error: {str(e)}'
            }