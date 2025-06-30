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
    
    def construct_strategy(self, use_expected_moves: bool = True, **kwargs) -> Dict:
        """Construct diagonal spread"""
        try:
            # Check if we have multiple expiries - simplified approach
            # Since we typically work with single expiry, simulate diagonal with different strikes
            if self.options_df.empty:
                return {'success': False, 'reason': 'No options data available'}
            
            # Get market direction
            direction = self.market_analysis.get('direction', 'neutral').lower() if hasattr(self, 'market_analysis') else 'neutral'
            
            # Decide on calls or puts based on direction
            if 'bullish' in direction:
                option_type = 'CALL'
                use_calls = True
            elif 'bearish' in direction:
                option_type = 'PUT'
                use_calls = False
            else:
                # For neutral, default to calls
                option_type = 'CALL'
                use_calls = True
            
            # Filter options by type
            type_options = self.options_df[self.options_df['option_type'] == option_type].copy()
            
            if type_options.empty or len(type_options) < 2:
                return {'success': False, 'reason': f'Insufficient {option_type} options for diagonal spread'}
            
            # Intelligent strike selection using expected moves
            if use_expected_moves and self.market_analysis and self.strike_selector:
                logger.info(f"Using intelligent strike selection for {option_type} Diagonal Spread")
                
                # For diagonal spread, we want different strikes - simulate near/far expiry effect
                # Get two different strikes based on directional bias
                if use_calls:
                    # Bull diagonal: Buy ATM call, Sell OTM call
                    long_strike = self._find_atm_strike()
                    short_strike = self._find_strike_above_spot(1.03)  # 3% OTM
                else:
                    # Bear diagonal: Buy ATM put, Sell OTM put  
                    long_strike = self._find_atm_strike()
                    short_strike = self._find_strike_below_spot(0.97)  # 3% OTM
            else:
                # Fallback to simple selection
                strikes = sorted(type_options['strike'].unique())
                long_strike = min(strikes, key=lambda x: abs(x - self.spot_price))  # ATM
                if use_calls:
                    otm_strikes = [s for s in strikes if s > self.spot_price * 1.02]
                    short_strike = min(otm_strikes) if otm_strikes else long_strike * 1.05
                else:
                    otm_strikes = [s for s in strikes if s < self.spot_price * 0.98]
                    short_strike = max(otm_strikes) if otm_strikes else long_strike * 0.95
            
            # Validate strikes
            if not self.validate_strikes([long_strike, short_strike]) or long_strike == short_strike:
                return {'success': False, 'reason': 'Invalid strike selection for diagonal spread'}
            
            # Get option data
            long_option_data = self._get_option_data(long_strike, option_type)
            short_option_data = self._get_option_data(short_strike, option_type)
            
            if long_option_data is None or short_option_data is None:
                return {'success': False, 'reason': 'Option data not available'}
            
            # Create legs using base class method for complete data extraction
            legs = [
                self._create_leg(
                    long_option_data, 
                    'LONG', 
                    quantity=1, 
                    rationale=f'Long {option_type} at {long_strike} (ATM)'
                ),
                self._create_leg(
                    short_option_data, 
                    'SHORT', 
                    quantity=1, 
                    rationale=f'Short {option_type} at {short_strike} (OTM)'
                )
            ]
            
            # Calculate strategy metrics
            metrics = self._calculate_metrics(legs, use_calls, direction)
            
            if not metrics:
                return {'success': False, 'reason': 'Unable to calculate strategy metrics'}
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error constructing Diagonal Spread: {e}")
            return None
    
    def _calculate_metrics(self, legs: List[Dict], use_calls: bool,
                         direction: str) -> Optional[Dict]:
        """Calculate diagonal spread metrics"""
        try:
            # Extract details - legs[0] is LONG, legs[1] is SHORT
            long_premium = legs[0]['premium']  # Long
            short_premium = legs[1]['premium']  # Short
            
            net_debit = long_premium - short_premium
            
            # Extract strikes
            long_strike = legs[0]['strike']  # ATM strike
            short_strike = legs[1]['strike']  # OTM strike
            
            # Diagonal spread max profit approximation
            if use_calls and short_strike > long_strike:
                # Bull diagonal call spread
                max_profit_estimate = (short_strike - long_strike) - net_debit
            elif not use_calls and short_strike < long_strike:
                # Bear diagonal put spread  
                max_profit_estimate = (long_strike - short_strike) - net_debit
            else:
                # Fallback estimate
                max_profit_estimate = abs(short_strike - long_strike) * 0.3
            
            max_loss = net_debit
            
            # Apply lot size multiplier for real position sizing
            total_max_profit = max_profit_estimate * self.lot_size
            total_max_loss = max_loss * self.lot_size
            total_net_debit = net_debit * self.lot_size
            
            # Greeks
            net_delta = legs[0]['delta'] - legs[1]['delta']  # Long - Short
            net_theta = legs[0].get('theta', 0) - legs[1].get('theta', 0)
            net_gamma = legs[0].get('gamma', 0) - legs[1].get('gamma', 0)
            net_vega = legs[0].get('vega', 0) - legs[1].get('vega', 0)
            
            # Simplified probability estimate
            prob_profit = 0.45  # Conservative estimate for diagonal spreads
            
            # Breakeven approximation
            if use_calls:
                breakeven = long_strike + net_debit
            else:
                breakeven = long_strike - net_debit
            
            return {
                'success': True,
                'strategy_name': self.get_strategy_name(),
                'legs': legs,
                'max_profit': total_max_profit,
                'max_loss': total_max_loss,
                'probability_profit': prob_profit,
                'breakeven': breakeven,
                'delta_exposure': net_delta,
                'theta_decay': net_theta,
                'gamma_exposure': net_gamma,
                'vega_exposure': net_vega,
                'optimal_outcome': f"Moderate {direction} move toward {short_strike}",
                'position_details': {
                    'lot_size': self.lot_size,
                    'net_debit_per_lot': net_debit,
                    'max_profit_per_lot': max_profit_estimate,
                    'max_loss_per_lot': max_loss,
                    'total_cost': total_net_debit,
                    'total_contracts': self.lot_size * 2  # 2 legs
                },
                'strategy_note': f'{"Bull" if use_calls else "Bear"} Diagonal - Limited risk/reward'
            }
            
        except Exception as e:
            logger.error(f"Error calculating Diagonal Spread metrics: {e}")
            return None
    
    def _find_atm_strike(self) -> float:
        """Find ATM strike closest to spot price"""
        try:
            all_strikes = self.options_df['strike'].unique()
            atm_strike = min(all_strikes, key=lambda x: abs(x - self.spot_price))
            return float(atm_strike)
        except Exception as e:
            logger.error(f"Error finding ATM strike: {e}")
            return self.spot_price
    
    def _find_strike_above_spot(self, multiplier: float) -> float:
        """Find strike above spot by multiplier"""
        try:
            target_price = self.spot_price * multiplier
            call_strikes = self.options_df[self.options_df['option_type'] == 'CALL']['strike'].unique()
            above_strikes = [s for s in call_strikes if s >= target_price]
            return min(above_strikes) if above_strikes else target_price
        except Exception as e:
            logger.error(f"Error finding strike above spot: {e}")
            return self.spot_price * multiplier
    
    def _find_strike_below_spot(self, multiplier: float) -> float:
        """Find strike below spot by multiplier"""
        try:
            target_price = self.spot_price * multiplier
            put_strikes = self.options_df[self.options_df['option_type'] == 'PUT']['strike'].unique()
            below_strikes = [s for s in put_strikes if s <= target_price]
            return max(below_strikes) if below_strikes else target_price
        except Exception as e:
            logger.error(f"Error finding strike below spot: {e}")
            return self.spot_price * multiplier