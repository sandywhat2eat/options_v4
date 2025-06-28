"""
Strangle strategies (Long/Short Strangle)
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from strategies.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)

class LongStrangle(BaseStrategy):
    """Long Strangle strategy implementation"""
    
    def get_strategy_name(self) -> str:
        return "Long Strangle"
    
    def get_market_outlook(self) -> str:
        return "neutral"  # Expects big move in either direction
    
    def get_iv_preference(self) -> str:
        return "low"  # Buy volatility when it's cheap
    
    def construct_strategy(self, call_delta: float = 0.25, put_delta: float = -0.25) -> Dict:
        """
        Construct Long Strangle strategy (OTM Call + OTM Put)
        
        Args:
            call_delta: Target delta for OTM call (default 0.25)
            put_delta: Target delta for OTM put (default -0.25)
        """
        try:
            # Find OTM strikes
            call_strike = self._find_strike_by_delta(call_delta, 'CALL')
            put_strike = self._find_strike_by_delta(abs(put_delta), 'PUT')
            
            # Validate strikes
            if call_strike <= self.spot_price or put_strike >= self.spot_price:
                return {'success': False, 'reason': 'Invalid OTM strike selection'}
            
            if not self.validate_strikes([call_strike, put_strike]):
                return {'success': False, 'reason': 'Strikes not available or illiquid'}
            
            # Get option data
            call_data = self._get_option_data(call_strike, 'CALL')
            put_data = self._get_option_data(put_strike, 'PUT')
            
            if call_data is None or put_data is None:
                return {'success': False, 'reason': 'Option data not available'}
            
            # Construct legs
            self.legs = [
                {
                    'option_type': 'CALL',
                    'position': 'LONG',
                    'strike': call_strike,
                    'premium': call_data.get('last_price', 0),
                    'delta': call_data.get('delta', 0),
                    'rationale': 'Long OTM call for upside movement'
                },
                {
                    'option_type': 'PUT',
                    'position': 'LONG',
                    'strike': put_strike,
                    'premium': put_data.get('last_price', 0),
                    'delta': put_data.get('delta', 0),
                    'rationale': 'Long OTM put for downside movement'
                }
            ]
            
            # Calculate metrics
            total_premium = call_data.get('last_price', 0) + put_data.get('last_price', 0)
            upper_breakeven = call_strike + total_premium
            lower_breakeven = put_strike - total_premium
            
            # Distance between strikes (strangle width)
            strike_width = call_strike - put_strike
            move_required_pct = (total_premium / self.spot_price) * 100
            
            greeks = self.get_greeks_summary()
            
            # Apply lot size multiplier for real position sizing
            total_cost = total_premium * self.lot_size
            total_move_required = total_premium * self.lot_size
            
            # Calculate probability of profit for strangle
            # Needs to move beyond breakeven in either direction
            # Use historical volatility and current IV to estimate
            iv_avg = (call_data.get('implied_volatility', 30) + put_data.get('implied_volatility', 30)) / 2
            days_to_expiry = 30  # Default, should get from actual expiry
            expected_move_pct = (iv_avg / 100) * np.sqrt(days_to_expiry / 365)
            
            # Probability of moving beyond required move
            # Conservative estimate: 30-40% for OTM strangle (lower than straddle)
            probability_profit = min(0.40, 0.30 + (expected_move_pct - move_required_pct) * 1.5)
            
            return {
                'success': True,
                'strategy_name': self.get_strategy_name(),
                'legs': self.legs,
                'max_profit': float('inf'),  # Unlimited in both directions
                'max_loss': total_cost,
                'breakeven_points': [lower_breakeven, upper_breakeven],
                'probability_profit': probability_profit,  # ADDED THIS FIELD
                'strike_width': strike_width,
                'move_required': total_premium,  # Per share breakeven
                'move_required_pct': move_required_pct,
                'delta_exposure': greeks['delta'],
                'theta_decay': greeks['theta'],
                'vega_exposure': greeks['vega'],
                'optimal_outcome': f"Big move beyond {lower_breakeven:.2f} or {upper_breakeven:.2f}",
                'strategy_note': 'Cheaper than straddle but requires larger move',
                'position_details': {
                    'lot_size': self.lot_size,
                    'premium_per_lot': total_premium,
                    'total_cost': total_cost,
                    'total_contracts': self.lot_size * 2  # 2 legs (call + put)
                }
            }
            
        except Exception as e:
            logger.error(f"Error constructing Long Strangle: {e}")
            return {'success': False, 'reason': f'Construction error: {e}'}
    
    def _find_strike_by_delta(self, target_delta: float, option_type: str) -> float:
        """Find strike closest to target delta"""
        try:
            type_options = self.options_df[
                (self.options_df['option_type'] == option_type) &
                (self.options_df['open_interest'] >= 50)  # Basic liquidity filter
            ]
            
            if type_options.empty:
                return self.spot_price
            
            # For puts, compare absolute delta values
            if option_type == 'PUT':
                type_options['delta_diff'] = abs(abs(type_options['delta']) - target_delta)
            else:  # CALL
                type_options['delta_diff'] = abs(type_options['delta'] - target_delta)
            
            optimal_option = type_options.loc[type_options['delta_diff'].idxmin()]
            return float(optimal_option['strike'])
            
        except Exception as e:
            logger.error(f"Error finding strike by delta: {e}")
            return self.spot_price

class ShortStrangle(BaseStrategy):
    """Short Strangle strategy implementation"""
    
    def get_strategy_name(self) -> str:
        return "Short Strangle"
    
    def get_market_outlook(self) -> str:
        return "neutral"  # Expects low movement
    
    def get_iv_preference(self) -> str:
        return "high"  # Sell volatility when it's expensive
    
    def construct_strategy(self, call_delta: float = 0.20, put_delta: float = -0.20) -> Dict:
        """
        Construct Short Strangle strategy (Short OTM Call + Short OTM Put)
        
        Args:
            call_delta: Target delta for OTM call (default 0.20)
            put_delta: Target delta for OTM put (default -0.20)
        """
        try:
            # Find OTM strikes (slightly more conservative than long strangle)
            call_strike = self._find_strike_by_delta(call_delta, 'CALL')
            put_strike = self._find_strike_by_delta(abs(put_delta), 'PUT')
            
            # Validate strikes
            if call_strike <= self.spot_price or put_strike >= self.spot_price:
                return {'success': False, 'reason': 'Invalid OTM strike selection'}
            
            if not self.validate_strikes([call_strike, put_strike]):
                return {'success': False, 'reason': 'Strikes not available or illiquid'}
            
            # Get option data
            call_data = self._get_option_data(call_strike, 'CALL')
            put_data = self._get_option_data(put_strike, 'PUT')
            
            if call_data is None or put_data is None:
                return {'success': False, 'reason': 'Option data not available'}
            
            # Additional risk check for short strangle
            if not self._validate_short_strangle_risk(call_data, put_data):
                return {'success': False, 'reason': 'Risk too high for short strangle'}
            
            # Construct legs
            self.legs = [
                {
                    'option_type': 'CALL',
                    'position': 'SHORT',
                    'strike': call_strike,
                    'premium': call_data.get('last_price', 0),
                    'delta': call_data.get('delta', 0),
                    'rationale': 'Short OTM call to collect premium'
                },
                {
                    'option_type': 'PUT',
                    'position': 'SHORT',
                    'strike': put_strike,
                    'premium': put_data.get('last_price', 0),
                    'delta': put_data.get('delta', 0),
                    'rationale': 'Short OTM put to collect premium'
                }
            ]
            
            # Calculate metrics
            total_credit = call_data.get('last_price', 0) + put_data.get('last_price', 0)
            upper_breakeven = call_strike + total_credit
            lower_breakeven = put_strike - total_credit
            
            # Profit zone
            profit_zone_width = call_strike - put_strike
            profit_zone_pct = (profit_zone_width / self.spot_price) * 100
            
            greeks = self.get_greeks_summary()
            
            # Apply lot size multiplier for real position sizing
            total_credit_received = total_credit * self.lot_size
            
            # Calculate probability of profit for short strangle
            # Profits when price stays between strikes
            # Use delta approximation
            call_prob_itm = abs(call_data.get('delta', 0.2))
            put_prob_itm = abs(put_data.get('delta', 0.2))
            
            # Probability of staying between strikes
            probability_profit = 1.0 - (call_prob_itm + put_prob_itm)
            # Conservative adjustment for early assignment risk
            probability_profit *= 0.85
            
            return {
                'success': True,
                'strategy_name': self.get_strategy_name(),
                'legs': self.legs,
                'max_profit': total_credit_received,
                'max_loss': float('inf'),  # Unlimited risk - requires margin
                'breakeven_points': [lower_breakeven, upper_breakeven],
                'probability_profit': probability_profit,  # ADDED THIS FIELD
                'profit_zone': (put_strike, call_strike),
                'profit_zone_width': profit_zone_width,
                'profit_zone_pct': profit_zone_pct,
                'delta_exposure': greeks['delta'],
                'theta_decay': greeks['theta'],
                'vega_exposure': greeks['vega'],
                'optimal_outcome': f"Stock stays between {put_strike:.2f} and {call_strike:.2f}",
                'margin_requirement': 'HIGH',
                'risk_warning': 'Unlimited loss potential - requires strict risk management',
                'strategy_note': 'Higher probability than short straddle but lower premium',
                'position_details': {
                    'lot_size': self.lot_size,
                    'credit_per_lot': total_credit,
                    'total_credit_received': total_credit_received,
                    'total_contracts': self.lot_size * 2  # 2 legs (call + put)
                }
            }
            
        except Exception as e:
            logger.error(f"Error constructing Short Strangle: {e}")
            return {'success': False, 'reason': f'Construction error: {e}'}
    
    def _find_strike_by_delta(self, target_delta: float, option_type: str) -> float:
        """Find strike closest to target delta"""
        try:
            type_options = self.options_df[
                (self.options_df['option_type'] == option_type) &
                (self.options_df['open_interest'] >= 100)  # Higher liquidity requirement
            ]
            
            if type_options.empty:
                return self.spot_price
            
            # For puts, compare absolute delta values
            if option_type == 'PUT':
                type_options['delta_diff'] = abs(abs(type_options['delta']) - target_delta)
            else:  # CALL
                type_options['delta_diff'] = abs(type_options['delta'] - target_delta)
            
            optimal_option = type_options.loc[type_options['delta_diff'].idxmin()]
            return float(optimal_option['strike'])
            
        except Exception as e:
            logger.error(f"Error finding strike by delta: {e}")
            return self.spot_price
    
    def _validate_short_strangle_risk(self, call_data: pd.Series, put_data: pd.Series) -> bool:
        """Additional risk validation for short strangle"""
        try:
            # Check IV levels - don't sell if IV is too low
            call_iv = call_data.get('iv', 0)
            put_iv = put_data.get('iv', 0)
            avg_iv = (call_iv + put_iv) / 2
            
            if avg_iv < 20:  # Don't sell strangles when IV is below 20%
                logger.warning(f"IV too low for short strangle: {avg_iv}")
                return False
            
            # Check liquidity for assignment risk
            call_oi = call_data.get('open_interest', 0)
            put_oi = put_data.get('open_interest', 0)
            
            if call_oi < 100 or put_oi < 100:
                logger.warning("Insufficient OI for short strangle")
                return False
            
            # Check delta exposure (combined should be manageable)
            total_delta_exposure = abs(call_data.get('delta', 0)) + abs(put_data.get('delta', 0))
            if total_delta_exposure > 0.5:
                logger.warning(f"Combined delta exposure too high: {total_delta_exposure}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating short strangle risk: {e}")
            return False