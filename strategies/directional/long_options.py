"""
Long options strategies (Long Call, Long Put)
"""

import pandas as pd
import logging
from typing import Dict, List
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from strategies.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)

class LongCall(BaseStrategy):
    """Long Call strategy implementation"""
    
    def get_strategy_name(self) -> str:
        return "Long Call"
    
    def get_market_outlook(self) -> str:
        return "bullish"
    
    def get_iv_preference(self) -> str:
        return "low"
    
    def construct_strategy(self, strike: float = None, target_delta: float = 0.5) -> Dict:
        """
        Construct Long Call strategy
        
        Args:
            strike: Specific strike to use (optional)
            target_delta: Target delta for strike selection (default 0.5 for ATM)
        """
        try:
            if strike is None:
                strike = self._find_optimal_strike(target_delta, 'CALL')
            
            if not self.validate_strikes([strike]):
                return {'success': False, 'reason': 'Invalid strike selection'}
            
            # Get option data
            call_data = self._get_option_data(strike, 'CALL')
            if call_data is None:
                return {'success': False, 'reason': 'Option data not available'}
            
            # Construct leg
            self.legs = [{
                'option_type': 'CALL',
                'position': 'LONG',
                'strike': strike,
                'premium': call_data.get('last_price', 0),
                'delta': call_data.get('delta', 0),
                'rationale': 'Bullish directional play'
            }]
            
            # Calculate metrics
            risk_metrics = self.get_risk_metrics()
            greeks = self.get_greeks_summary()
            
            # Apply lot size multiplier for real position sizing
            premium_per_contract = call_data.get('last_price', 0)
            total_cost = premium_per_contract * self.lot_size
            total_max_loss = total_cost
            
            return {
                'success': True,
                'strategy_name': self.get_strategy_name(),
                'legs': self.legs,
                'max_profit': float('inf'),  # Unlimited upside
                'max_loss': total_max_loss,  # Total cost with lot size
                'breakeven': strike + premium_per_contract,  # Breakeven per share
                'delta_exposure': greeks['delta'],
                'theta_decay': greeks['theta'],
                'iv_exposure': greeks['vega'],
                'optimal_outcome': f"Stock moves above {strike + premium_per_contract:.2f}",
                'position_details': {
                    'lot_size': self.lot_size,
                    'premium_per_contract': premium_per_contract,
                    'total_cost': total_cost,
                    'total_contracts': self.lot_size
                }
            }
            
        except Exception as e:
            logger.error(f"Error constructing Long Call: {e}")
            return {'success': False, 'reason': f'Construction error: {e}'}
    
    def _find_optimal_strike(self, target_delta: float, option_type: str) -> float:
        """Find strike closest to target delta"""
        try:
            type_options = self.options_df[self.options_df['option_type'] == option_type]
            if type_options.empty:
                return self.spot_price
            
            # Find closest delta
            type_options['delta_diff'] = abs(type_options['delta'] - target_delta)
            optimal_option = type_options.loc[type_options['delta_diff'].idxmin()]
            
            return optimal_option['strike']
            
        except Exception as e:
            logger.error(f"Error finding optimal strike: {e}")
            return self.spot_price

class LongPut(BaseStrategy):
    """Long Put strategy implementation"""
    
    def get_strategy_name(self) -> str:
        return "Long Put"
    
    def get_market_outlook(self) -> str:
        return "bearish"
    
    def get_iv_preference(self) -> str:
        return "low"
    
    def construct_strategy(self, strike: float = None, target_delta: float = -0.5) -> Dict:
        """
        Construct Long Put strategy
        
        Args:
            strike: Specific strike to use (optional)
            target_delta: Target delta for strike selection (default -0.5 for ATM)
        """
        try:
            if strike is None:
                strike = self._find_optimal_strike(abs(target_delta), 'PUT')
            
            if not self.validate_strikes([strike]):
                return {'success': False, 'reason': 'Invalid strike selection'}
            
            # Get option data
            put_data = self._get_option_data(strike, 'PUT')
            if put_data is None:
                return {'success': False, 'reason': 'Option data not available'}
            
            # Construct leg
            self.legs = [{
                'option_type': 'PUT',
                'position': 'LONG',
                'strike': strike,
                'premium': put_data.get('last_price', 0),
                'delta': put_data.get('delta', 0),
                'rationale': 'Bearish directional play'
            }]
            
            # Calculate metrics
            greeks = self.get_greeks_summary()
            premium_per_contract = put_data.get('last_price', 0)
            
            # Apply lot size multiplier for real position sizing
            total_cost = premium_per_contract * self.lot_size
            max_profit_per_contract = strike - premium_per_contract
            total_max_profit = max_profit_per_contract * self.lot_size
            
            return {
                'success': True,
                'strategy_name': self.get_strategy_name(),
                'legs': self.legs,
                'max_profit': total_max_profit,  # Total profit with lot size
                'max_loss': total_cost,  # Total cost with lot size
                'breakeven': strike - premium_per_contract,  # Breakeven per share
                'delta_exposure': greeks['delta'],
                'theta_decay': greeks['theta'],
                'iv_exposure': greeks['vega'],
                'optimal_outcome': f"Stock moves below {strike - premium_per_contract:.2f}",
                'position_details': {
                    'lot_size': self.lot_size,
                    'premium_per_contract': premium_per_contract,
                    'total_cost': total_cost,
                    'total_contracts': self.lot_size
                }
            }
            
        except Exception as e:
            logger.error(f"Error constructing Long Put: {e}")
            return {'success': False, 'reason': f'Construction error: {e}'}
    
    def _find_optimal_strike(self, target_delta: float, option_type: str) -> float:
        """Find strike closest to target delta"""
        try:
            type_options = self.options_df[self.options_df['option_type'] == option_type]
            if type_options.empty:
                return self.spot_price
            
            # For puts, delta is negative, so we compare absolute values
            type_options['delta_diff'] = abs(abs(type_options['delta']) - target_delta)
            optimal_option = type_options.loc[type_options['delta_diff'].idxmin()]
            
            return optimal_option['strike']
            
        except Exception as e:
            logger.error(f"Error finding optimal strike: {e}")
            return self.spot_price