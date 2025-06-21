"""
Spread strategies (Bull/Bear Call/Put Spreads)
"""

import pandas as pd
import logging
from typing import Dict, List
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from strategies.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)

class BullCallSpread(BaseStrategy):
    """Bull Call Spread strategy implementation"""
    
    def get_strategy_name(self) -> str:
        return "Bull Call Spread"
    
    def get_market_outlook(self) -> str:
        return "bullish"
    
    def get_iv_preference(self) -> str:
        return "neutral"
    
    def construct_strategy(self, short_delta: float = 0.3, long_delta: float = 0.15) -> Dict:
        """Construct Bull Call Spread (Buy lower strike, Sell higher strike)"""
        try:
            # Find optimal strikes
            long_strike = self._find_strike_by_delta(long_delta, 'CALL')
            short_strike = self._find_strike_by_delta(short_delta, 'CALL')
            
            if long_strike >= short_strike:
                return {'success': False, 'reason': 'Invalid strike relationship'}
            
            if not self.validate_strikes([long_strike, short_strike]):
                return {'success': False, 'reason': 'Invalid strikes'}
            
            # Get option data
            long_call_data = self._get_option_data(long_strike, 'CALL')
            short_call_data = self._get_option_data(short_strike, 'CALL')
            
            if long_call_data is None or short_call_data is None:
                return {'success': False, 'reason': 'Option data not available'}
            
            # Construct legs
            self.legs = [
                {
                    'option_type': 'CALL',
                    'position': 'LONG',
                    'strike': long_strike,
                    'premium': long_call_data.get('last_price', 0),
                    'delta': long_call_data.get('delta', 0),
                    'rationale': 'Long the lower strike for upside participation'
                },
                {
                    'option_type': 'CALL',
                    'position': 'SHORT',
                    'strike': short_strike,
                    'premium': short_call_data.get('last_price', 0),
                    'delta': short_call_data.get('delta', 0),
                    'rationale': 'Short the higher strike to reduce cost'
                }
            ]
            
            # Calculate metrics
            net_debit = long_call_data.get('last_price', 0) - short_call_data.get('last_price', 0)
            max_profit = (short_strike - long_strike) - net_debit
            
            greeks = self.get_greeks_summary()
            
            return {
                'success': True,
                'strategy_name': self.get_strategy_name(),
                'legs': self.legs,
                'max_profit': max_profit,
                'max_loss': net_debit,
                'breakeven': long_strike + net_debit,
                'delta_exposure': greeks['delta'],
                'theta_decay': greeks['theta'],
                'optimal_outcome': f"Stock closes above {short_strike} at expiry"
            }
            
        except Exception as e:
            logger.error(f"Error constructing Bull Call Spread: {e}")
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
            
            type_options['delta_diff'] = abs(type_options['delta'] - target_delta)
            optimal_option = type_options.loc[type_options['delta_diff'].idxmin()]
            
            return optimal_option['strike']
            
        except Exception as e:
            logger.error(f"Error finding strike by delta: {e}")
            return self.spot_price

class BearCallSpread(BaseStrategy):
    """Bear Call Spread strategy implementation"""
    
    def get_strategy_name(self) -> str:
        return "Bear Call Spread"
    
    def get_market_outlook(self) -> str:
        return "bearish"
    
    def get_iv_preference(self) -> str:
        return "neutral"
    
    def construct_strategy(self, short_delta: float = 0.3, long_delta: float = 0.15) -> Dict:
        """Construct Bear Call Spread (Sell lower strike, Buy higher strike)"""
        try:
            # Find optimal strikes
            short_strike = self._find_strike_by_delta(short_delta, 'CALL')
            long_strike = self._find_strike_by_delta(long_delta, 'CALL')
            
            if short_strike >= long_strike:
                return {'success': False, 'reason': 'Invalid strike relationship'}
            
            if not self.validate_strikes([short_strike, long_strike]):
                return {'success': False, 'reason': 'Invalid strikes'}
            
            # Get option data
            short_call_data = self._get_option_data(short_strike, 'CALL')
            long_call_data = self._get_option_data(long_strike, 'CALL')
            
            if short_call_data is None or long_call_data is None:
                return {'success': False, 'reason': 'Option data not available'}
            
            # Construct legs
            self.legs = [
                {
                    'option_type': 'CALL',
                    'position': 'SHORT',
                    'strike': short_strike,
                    'premium': short_call_data.get('last_price', 0),
                    'delta': short_call_data.get('delta', 0),
                    'rationale': 'Short the lower strike to collect premium'
                },
                {
                    'option_type': 'CALL',
                    'position': 'LONG',
                    'strike': long_strike,
                    'premium': long_call_data.get('last_price', 0),
                    'delta': long_call_data.get('delta', 0),
                    'rationale': 'Long the higher strike for risk management'
                }
            ]
            
            # Calculate metrics
            net_credit = short_call_data.get('last_price', 0) - long_call_data.get('last_price', 0)
            max_loss = (long_strike - short_strike) - net_credit
            
            greeks = self.get_greeks_summary()
            
            return {
                'success': True,
                'strategy_name': self.get_strategy_name(),
                'legs': self.legs,
                'max_profit': net_credit,
                'max_loss': max_loss,
                'breakeven': short_strike + net_credit,
                'delta_exposure': greeks['delta'],
                'theta_decay': greeks['theta'],
                'optimal_outcome': f"Stock closes below {short_strike} at expiry"
            }
            
        except Exception as e:
            logger.error(f"Error constructing Bear Call Spread: {e}")
            return {'success': False, 'reason': f'Construction error: {e}'}
    
    def _find_strike_by_delta(self, target_delta: float, option_type: str) -> float:
        """Find strike closest to target delta"""
        try:
            type_options = self.options_df[
                (self.options_df['option_type'] == option_type) &
                (self.options_df['open_interest'] >= 50)
            ]
            
            if type_options.empty:
                return self.spot_price
            
            type_options['delta_diff'] = abs(type_options['delta'] - target_delta)
            optimal_option = type_options.loc[type_options['delta_diff'].idxmin()]
            
            return optimal_option['strike']
            
        except Exception as e:
            logger.error(f"Error finding strike by delta: {e}")
            return self.spot_price

class BullPutSpread(BaseStrategy):
    """Bull Put Spread strategy implementation"""
    
    def get_strategy_name(self) -> str:
        return "Bull Put Spread"
    
    def get_market_outlook(self) -> str:
        return "bullish"
    
    def get_iv_preference(self) -> str:
        return "neutral"
    
    def construct_strategy(self, short_delta: float = -0.3, long_delta: float = -0.15) -> Dict:
        """Construct Bull Put Spread (Sell higher strike, Buy lower strike)"""
        try:
            # Find optimal strikes (using absolute values for put deltas)
            short_strike = self._find_strike_by_delta(abs(short_delta), 'PUT')
            long_strike = self._find_strike_by_delta(abs(long_delta), 'PUT')
            
            if short_strike <= long_strike:
                return {'success': False, 'reason': 'Invalid strike relationship'}
            
            if not self.validate_strikes([short_strike, long_strike]):
                return {'success': False, 'reason': 'Invalid strikes'}
            
            # Get option data
            short_put_data = self._get_option_data(short_strike, 'PUT')
            long_put_data = self._get_option_data(long_strike, 'PUT')
            
            if short_put_data is None or long_put_data is None:
                return {'success': False, 'reason': 'Option data not available'}
            
            # Construct legs
            self.legs = [
                {
                    'option_type': 'PUT',
                    'position': 'SHORT',
                    'strike': short_strike,
                    'premium': short_put_data.get('last_price', 0),
                    'delta': short_put_data.get('delta', 0),
                    'rationale': 'Short the higher strike to collect premium'
                },
                {
                    'option_type': 'PUT',
                    'position': 'LONG',
                    'strike': long_strike,
                    'premium': long_put_data.get('last_price', 0),
                    'delta': long_put_data.get('delta', 0),
                    'rationale': 'Long the lower strike for risk management'
                }
            ]
            
            # Calculate metrics
            net_credit = short_put_data.get('last_price', 0) - long_put_data.get('last_price', 0)
            max_loss = (short_strike - long_strike) - net_credit
            
            greeks = self.get_greeks_summary()
            
            return {
                'success': True,
                'strategy_name': self.get_strategy_name(),
                'legs': self.legs,
                'max_profit': net_credit,
                'max_loss': max_loss,
                'breakeven': short_strike - net_credit,
                'delta_exposure': greeks['delta'],
                'theta_decay': greeks['theta'],
                'optimal_outcome': f"Stock closes above {short_strike} at expiry"
            }
            
        except Exception as e:
            logger.error(f"Error constructing Bull Put Spread: {e}")
            return {'success': False, 'reason': f'Construction error: {e}'}
    
    def _find_strike_by_delta(self, target_delta: float, option_type: str) -> float:
        """Find strike closest to target delta"""
        try:
            type_options = self.options_df[
                (self.options_df['option_type'] == option_type) &
                (self.options_df['open_interest'] >= 50)
            ]
            
            if type_options.empty:
                return self.spot_price
            
            # For puts, compare absolute delta values
            type_options['delta_diff'] = abs(abs(type_options['delta']) - target_delta)
            optimal_option = type_options.loc[type_options['delta_diff'].idxmin()]
            
            return optimal_option['strike']
            
        except Exception as e:
            logger.error(f"Error finding strike by delta: {e}")
            return self.spot_price

class BearPutSpread(BaseStrategy):
    """Bear Put Spread strategy implementation"""
    
    def get_strategy_name(self) -> str:
        return "Bear Put Spread"
    
    def get_market_outlook(self) -> str:
        return "bearish"
    
    def get_iv_preference(self) -> str:
        return "neutral"
    
    def construct_strategy(self, short_delta: float = -0.15, long_delta: float = -0.3) -> Dict:
        """Construct Bear Put Spread (Buy higher strike, Sell lower strike)"""
        try:
            # Find optimal strikes (using absolute values for put deltas)
            long_strike = self._find_strike_by_delta(abs(long_delta), 'PUT')
            short_strike = self._find_strike_by_delta(abs(short_delta), 'PUT')
            
            if long_strike <= short_strike:
                return {'success': False, 'reason': 'Invalid strike relationship'}
            
            if not self.validate_strikes([long_strike, short_strike]):
                return {'success': False, 'reason': 'Invalid strikes'}
            
            # Get option data
            long_put_data = self._get_option_data(long_strike, 'PUT')
            short_put_data = self._get_option_data(short_strike, 'PUT')
            
            if long_put_data is None or short_put_data is None:
                return {'success': False, 'reason': 'Option data not available'}
            
            # Construct legs
            self.legs = [
                {
                    'option_type': 'PUT',
                    'position': 'LONG',
                    'strike': long_strike,
                    'premium': long_put_data.get('last_price', 0),
                    'delta': long_put_data.get('delta', 0),
                    'rationale': 'Long the higher strike for downside participation'
                },
                {
                    'option_type': 'PUT',
                    'position': 'SHORT',
                    'strike': short_strike,
                    'premium': short_put_data.get('last_price', 0),
                    'delta': short_put_data.get('delta', 0),
                    'rationale': 'Short the lower strike to reduce cost'
                }
            ]
            
            # Calculate metrics
            net_debit = long_put_data.get('last_price', 0) - short_put_data.get('last_price', 0)
            max_profit = (long_strike - short_strike) - net_debit
            
            greeks = self.get_greeks_summary()
            
            return {
                'success': True,
                'strategy_name': self.get_strategy_name(),
                'legs': self.legs,
                'max_profit': max_profit,
                'max_loss': net_debit,
                'breakeven': long_strike - net_debit,
                'delta_exposure': greeks['delta'],
                'theta_decay': greeks['theta'],
                'optimal_outcome': f"Stock closes below {short_strike} at expiry"
            }
            
        except Exception as e:
            logger.error(f"Error constructing Bear Put Spread: {e}")
            return {'success': False, 'reason': f'Construction error: {e}'}
    
    def _find_strike_by_delta(self, target_delta: float, option_type: str) -> float:
        """Find strike closest to target delta"""
        try:
            type_options = self.options_df[
                (self.options_df['option_type'] == option_type) &
                (self.options_df['open_interest'] >= 50)
            ]
            
            if type_options.empty:
                return self.spot_price
            
            # For puts, compare absolute delta values
            type_options['delta_diff'] = abs(abs(type_options['delta']) - target_delta)
            optimal_option = type_options.loc[type_options['delta_diff'].idxmin()]
            
            return optimal_option['strike']
            
        except Exception as e:
            logger.error(f"Error finding strike by delta: {e}")
            return self.spot_price