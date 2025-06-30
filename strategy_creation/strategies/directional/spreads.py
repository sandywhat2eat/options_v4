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
    
    def construct_strategy(self, use_expected_moves: bool = True) -> Dict:
        """Construct Bull Call Spread (Buy lower strike, Sell higher strike)"""
        try:
            # Use centralized strike selection
            if use_expected_moves and self.strike_selector:
                logger.info("Using intelligent strike selection for Bull Call Spread")
                strikes = self.select_strikes_for_strategy(use_expected_moves=True)
                
                if strikes and 'long_strike' in strikes and 'short_strike' in strikes:
                    long_strike = strikes['long_strike']
                    short_strike = strikes['short_strike']
                    logger.info(f"Selected CALL strikes via intelligent selector: Long {long_strike}, Short {short_strike}")
                else:
                    logger.warning("Intelligent strike selection failed, using fallback")
                    available_strikes = sorted(self.options_df[self.options_df['option_type'] == 'CALL']['strike'].unique())
                    long_strike = self._find_optimal_strike(0.40, 'CALL')   # Higher delta = lower strike
                    short_strike = self._find_optimal_strike(0.20, 'CALL')  # Lower delta = higher strike
            else:
                # Fallback to delta-based selection with wider spread
                logger.info("Using delta-based strike selection")
                # For Bull Call Spread: Buy lower strike (higher delta), Sell higher strike (lower delta)
                available_strikes = sorted(self.options_df[self.options_df['option_type'] == 'CALL']['strike'].unique())
                long_strike = self._find_optimal_strike(0.40, 'CALL')   # Higher delta = lower strike
                short_strike = self._find_optimal_strike(0.20, 'CALL')  # Lower delta = higher strike
                
                # Ensure strikes are different and properly spaced
                if long_strike == short_strike:
                    atm_strike = min(available_strikes, key=lambda x: abs(x - self.spot_price))
                    if atm_strike in available_strikes:
                        idx = available_strikes.index(atm_strike)
                        long_strike = atm_strike
                        # Find next higher strike for short leg
                        if idx < len(available_strikes) - 1:
                            short_strike = available_strikes[idx + 1]
                        else:
                            short_strike = available_strikes[idx - 1] if idx > 0 else atm_strike * 1.05
            
            if long_strike >= short_strike:
                # If strikes are reversed, swap them for Bull Call Spread
                logger.warning(f"Swapping strikes for Bull Call Spread: long={long_strike}, short={short_strike}")
                long_strike, short_strike = short_strike, long_strike
            
            if not self.validate_strikes([long_strike, short_strike]):
                return {'success': False, 'reason': 'Invalid strikes'}
            
            # Get option data
            long_call_data = self._get_option_data(long_strike, 'CALL')
            short_call_data = self._get_option_data(short_strike, 'CALL')
            
            if long_call_data is None or short_call_data is None:
                return {'success': False, 'reason': 'Option data not available'}
            
            # NEW: Get smile-adjusted IVs for accurate spread pricing
            if hasattr(self.options_df, 'attrs') and 'smile_params' in self.options_df.attrs:
                # Get smile-adjusted IVs
                long_call_iv = self.options_df[
                    (self.options_df['strike'] == long_strike) & 
                    (self.options_df['option_type'] == 'CALL')
                ]['smile_adjusted_iv'].iloc[0] if 'smile_adjusted_iv' in self.options_df.columns else long_call_data.get('iv', 25)
                
                short_call_iv = self.options_df[
                    (self.options_df['strike'] == short_strike) & 
                    (self.options_df['option_type'] == 'CALL')
                ]['smile_adjusted_iv'].iloc[0] if 'smile_adjusted_iv' in self.options_df.columns else short_call_data.get('iv', 25)
                
                logger.info(f"Bull Call Spread IVs - Long {long_strike}: {long_call_iv:.1f}%, Short {short_strike}: {short_call_iv:.1f}%")
                
                # Check if IV differential makes sense for a debit spread
                iv_differential = long_call_iv - short_call_iv
                if iv_differential > 2:  # Long strike has significantly higher IV than short
                    logger.warning(f"Unfavorable IV skew for Bull Call Spread (debit): {iv_differential:.1f}%")
            
            # Construct legs using base class method for complete data extraction
            self.legs = [
                self._create_leg(
                    long_call_data, 
                    'LONG', 
                    quantity=1, 
                    rationale='Long the lower strike for upside participation'
                ),
                self._create_leg(
                    short_call_data, 
                    'SHORT', 
                    quantity=1, 
                    rationale='Short the higher strike to reduce cost'
                )
            ]
            
            # Calculate metrics
            net_debit = long_call_data.get('last_price', 0) - short_call_data.get('last_price', 0)
            max_profit = (short_strike - long_strike) - net_debit
            
            greeks = self.get_greeks_summary()
            
            # Apply lot size multiplier for real position sizing
            total_max_profit = max_profit * self.lot_size
            total_max_loss = net_debit * self.lot_size
            total_cost = total_max_loss  # Net debit = cost
            
            # Calculate probability of profit
            # Bull Call Spread profits when price > breakeven
            # Use long call delta as approximation
            probability_profit = 1 - long_call_data.get('delta', 0.5)
            
            return {
                'success': True,
                'strategy_name': self.get_strategy_name(),
                'legs': self.legs,
                'max_profit': total_max_profit,
                'max_loss': total_max_loss,
                'breakeven': long_strike + net_debit,
                'probability_profit': probability_profit,  # ADDED THIS FIELD
                'delta_exposure': greeks['delta'],
                'theta_decay': greeks['theta'],
                'optimal_outcome': f"Stock closes above {short_strike} at expiry",
                'position_details': {
                    'lot_size': self.lot_size,
                    'net_debit_per_lot': net_debit,
                    'max_profit_per_lot': max_profit,
                    'total_cost': total_cost,
                    'total_contracts': self.lot_size * 2  # 2 legs
                }
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
    
    def construct_strategy(self, use_expected_moves: bool = True) -> Dict:
        """Construct Bear Call Spread (Sell lower strike, Buy higher strike)"""
        try:
            # Use centralized strike selection
            if use_expected_moves and self.strike_selector:
                logger.info("Using intelligent strike selection for Bear Call Spread")
                strikes = self.select_strikes_for_strategy(use_expected_moves=True)
                
                if strikes and 'short_strike' in strikes and 'long_strike' in strikes:
                    short_strike = strikes['short_strike']
                    long_strike = strikes['long_strike']
                    logger.info(f"Selected CALL strikes via intelligent selector: Short {short_strike}, Long {long_strike}")
                else:
                    logger.warning("Intelligent strike selection failed, using fallback")
                    short_strike = self._find_optimal_strike(0.30, 'CALL')  # Higher delta = lower strike
                    long_strike = self._find_optimal_strike(0.15, 'CALL')   # Lower delta = higher strike
            else:
                # Fallback to delta-based selection
                logger.info("Using delta-based strike selection")
                # For Bear Call Spread: Sell lower strike (higher delta), Buy higher strike (lower delta)
                short_strike = self._find_optimal_strike(0.30, 'CALL')  # Higher delta = lower strike
                long_strike = self._find_optimal_strike(0.15, 'CALL')   # Lower delta = higher strike
            
            if short_strike >= long_strike:
                # If strikes are reversed, swap them
                short_strike, long_strike = long_strike, short_strike
            
            if not self.validate_strikes([short_strike, long_strike]):
                return {'success': False, 'reason': 'Invalid strikes'}
            
            # Get option data
            short_call_data = self._get_option_data(short_strike, 'CALL')
            long_call_data = self._get_option_data(long_strike, 'CALL')
            
            if short_call_data is None or long_call_data is None:
                return {'success': False, 'reason': 'Option data not available'}
            
            # NEW: Get smile-adjusted IVs for accurate spread pricing
            if hasattr(self.options_df, 'attrs') and 'smile_params' in self.options_df.attrs:
                # Get smile-adjusted IVs
                short_call_iv = self.options_df[
                    (self.options_df['strike'] == short_strike) & 
                    (self.options_df['option_type'] == 'CALL')
                ]['smile_adjusted_iv'].iloc[0] if 'smile_adjusted_iv' in self.options_df.columns else short_call_data.get('iv', 25)
                
                long_call_iv = self.options_df[
                    (self.options_df['strike'] == long_strike) & 
                    (self.options_df['option_type'] == 'CALL')
                ]['smile_adjusted_iv'].iloc[0] if 'smile_adjusted_iv' in self.options_df.columns else long_call_data.get('iv', 25)
                
                logger.info(f"Bear Call Spread IVs - Short {short_strike}: {short_call_iv:.1f}%, Long {long_strike}: {long_call_iv:.1f}%")
                
                # Check if IV differential makes sense for a credit spread
                iv_differential = short_call_iv - long_call_iv
                if iv_differential < -2:  # Short strike has significantly lower IV than long
                    logger.warning(f"Unfavorable IV skew for Bear Call Spread: {iv_differential:.1f}%")
            
            # Construct legs using base class method for complete data extraction
            self.legs = [
                self._create_leg(
                    short_call_data, 
                    'SHORT', 
                    quantity=1, 
                    rationale='Short the lower strike to collect premium'
                ),
                self._create_leg(
                    long_call_data, 
                    'LONG', 
                    quantity=1, 
                    rationale='Long the higher strike for risk management'
                )
            ]
            
            # Calculate metrics
            net_credit = short_call_data.get('last_price', 0) - long_call_data.get('last_price', 0)
            max_loss = (long_strike - short_strike) - net_credit
            
            greeks = self.get_greeks_summary()
            
            # Apply lot size multiplier for real position sizing
            total_max_profit = net_credit * self.lot_size
            total_max_loss = max_loss * self.lot_size
            
            # Calculate probability of profit
            # Bear Call Spread profits when price < short strike
            # Use short call delta as approximation
            probability_profit = 1 - short_call_data.get('delta', 0.3)
            
            return {
                'success': True,
                'strategy_name': self.get_strategy_name(),
                'legs': self.legs,
                'max_profit': total_max_profit,
                'max_loss': total_max_loss,
                'breakeven': short_strike + net_credit,
                'probability_profit': probability_profit,  # ADDED THIS FIELD
                'delta_exposure': greeks['delta'],
                'theta_decay': greeks['theta'],
                'optimal_outcome': f"Stock closes below {short_strike} at expiry",
                'position_details': {
                    'lot_size': self.lot_size,
                    'net_credit_per_lot': net_credit,
                    'max_loss_per_lot': max_loss,
                    'total_credit_received': total_max_profit,
                    'total_contracts': self.lot_size * 2  # 2 legs
                }
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
    
    def construct_strategy(self, short_delta: float = -0.35, long_delta: float = -0.10) -> Dict:
        """Construct Bull Put Spread (Sell higher strike, Buy lower strike)"""
        try:
            # Find optimal strikes (using absolute values for put deltas)
            # Wider spread for better credit potential
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
            
            # Check if we have a net credit
            if net_credit <= 0:
                return {'success': False, 'reason': f'No net credit for spread (short premium: {short_put_data.get("last_price", 0):.2f}, long premium: {long_put_data.get("last_price", 0):.2f})'}
            
            max_loss = (short_strike - long_strike) - net_credit
            
            greeks = self.get_greeks_summary()
            
            # Apply lot size multiplier for real position sizing
            total_max_profit = net_credit * self.lot_size
            total_max_loss = max_loss * self.lot_size
            
            # Calculate probability of profit
            # Bull Put Spread profits when price stays above short strike
            # Use short put delta (negative) as approximation
            probability_profit = 1.0 + short_put_data.get('delta', -0.3)  # Delta is negative for puts
            
            return {
                'success': True,
                'strategy_name': self.get_strategy_name(),
                'legs': self.legs,
                'max_profit': total_max_profit,
                'max_loss': total_max_loss,
                'breakeven': short_strike - net_credit,
                'probability_profit': probability_profit,
                'delta_exposure': greeks['delta'],
                'theta_decay': greeks['theta'],
                'optimal_outcome': f"Stock closes above {short_strike} at expiry",
                'position_details': {
                    'lot_size': self.lot_size,
                    'net_credit_per_lot': net_credit,
                    'max_loss_per_lot': max_loss,
                    'total_credit_received': total_max_profit,
                    'total_contracts': self.lot_size * 2  # 2 legs
                }
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
    
    def construct_strategy(self, use_expected_moves: bool = True, **kwargs) -> Dict:
        """Construct Bear Put Spread (Buy higher strike, Sell lower strike)"""
        try:
            # Use centralized strike selection
            if use_expected_moves and self.strike_selector:
                logger.info("Using intelligent strike selection for Bear Put Spread")
                strikes = self.select_strikes_for_strategy(use_expected_moves=True)
                
                if strikes and 'long_strike' in strikes and 'short_strike' in strikes:
                    long_strike = strikes['long_strike']
                    short_strike = strikes['short_strike']
                    logger.info(f"Selected PUT strikes via intelligent selector: Long {long_strike}, Short {short_strike}")
                else:
                    logger.warning("Intelligent strike selection failed, using fallback")
                    long_strike = self._find_optimal_strike(0.30, 'PUT')
                    short_strike = self._find_optimal_strike(0.15, 'PUT')
            else:
                # Fallback to delta-based selection
                logger.info("Using delta-based strike selection")
                long_strike = self._find_optimal_strike(0.30, 'PUT')
                short_strike = self._find_optimal_strike(0.15, 'PUT')
            
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
            
            # Apply lot size multiplier for real position sizing
            total_max_profit = max_profit * self.lot_size
            total_max_loss = net_debit * self.lot_size
            
            # Calculate probability of profit
            # Bear Put Spread profits when price < breakeven (price drops below short strike)
            # More accurate: Use 1 - short_put_delta since we profit when price drops below short strike
            short_put_delta = abs(short_put_data.get('delta', -0.15))
            probability_profit = min(0.7, (1.0 - short_put_delta) * 0.9)  # Conservative adjustment
            
            return {
                'success': True,
                'strategy_name': self.get_strategy_name(),
                'legs': self.legs,
                'probability_profit': probability_profit,
                'max_profit': total_max_profit,
                'max_loss': total_max_loss,
                'breakeven': long_strike - net_debit,
                'delta_exposure': greeks['delta'],
                'theta_decay': greeks['theta'],
                'optimal_outcome': f"Stock closes below {short_strike} at expiry",
                'position_details': {
                    'lot_size': self.lot_size,
                    'net_debit_per_lot': net_debit,
                    'max_profit_per_lot': max_profit,
                    'total_cost': total_max_loss,
                    'total_contracts': self.lot_size * 2  # 2 legs
                }
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