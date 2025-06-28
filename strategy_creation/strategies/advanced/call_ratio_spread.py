"""
Call Ratio Spread Strategy - Exploit call skew
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import logging

from ..base_strategy import BaseStrategy

logger = logging.getLogger(__name__)

class CallRatioSpread(BaseStrategy):
    """
    Call Ratio Spread: Buy 1 ATM/ITM Call + Sell 2 OTM Calls
    
    Market Outlook: Moderately bullish with upside limit
    Profit: From moderate upward movement
    Risk: Unlimited above upper strike
    Ideal: Call skew present, expecting limited upside
    """
    
    def get_strategy_name(self) -> str:
        return "Call Ratio Spread"
    
    def get_market_outlook(self) -> str:
        return "bullish"
    
    def get_iv_preference(self) -> str:
        return "high"
    
    def get_required_legs(self) -> int:
        return 2  # 2 unique strikes, one with 2x quantity
    
    def get_market_bias(self) -> List[str]:
        return ['moderate_bullish', 'call_skew']
    
    def construct_strategy(self, use_expected_moves: bool = True, **kwargs) -> Dict:
        """Construct call ratio spread"""
        try:
            # Filter call options
            if self.options_df.empty:
                return {'success': False, 'reason': 'No options data available'}
            
            calls = self.options_df[self.options_df['option_type'] == 'CALL'].copy()
            if len(calls) < 2:
                return {'success': False, 'reason': 'Insufficient CALL options for ratio spread'}
            
            # Find strikes - Buy ATM, Sell OTM
            strikes = sorted(calls['strike'].unique())
            
            # Buy strike: ATM or slightly ITM
            buy_strike = min(strikes, key=lambda x: abs(x - self.spot_price))
            
            # Sell strike: 3-5% OTM for limited upside
            if use_expected_moves and self.market_analysis:
                # Use expected moves to set OTM strike
                expected_move = self.market_analysis.get('price_levels', {}).get('expected_moves', {}).get('one_sd_move', self.spot_price * 0.04)
                otm_target = self.spot_price + expected_move * 0.8  # Conservative target
            else:
                otm_target = self.spot_price * 1.04  # 4% OTM fallback
            
            sell_strikes = [s for s in strikes if s > buy_strike]
            if not sell_strikes:
                return {'success': False, 'reason': 'No OTM calls available for ratio spread'}
            
            sell_strike = min(sell_strikes, key=lambda x: abs(x - otm_target))
            
            # Validate strikes
            if not self.validate_strikes([buy_strike, sell_strike]) or buy_strike >= sell_strike:
                return {'success': False, 'reason': 'Invalid strike selection for ratio spread'}
            
            # Get option data
            buy_option_data = self._get_option_data(buy_strike, 'CALL')
            sell_option_data = self._get_option_data(sell_strike, 'CALL')
            
            if buy_option_data is None or sell_option_data is None:
                return {'success': False, 'reason': 'Option data not available'}
            
            # Risk check - don't sell too much if delta is high
            if sell_option_data.get('delta', 0) > 0.25:
                logger.warning(f"Sell strike delta {sell_option_data.get('delta', 0):.3f} may be too high")
            
            # Create legs
            legs = [
                {
                    'option_type': 'CALL',
                    'position': 'LONG',
                    'strike': buy_strike,
                    'premium': buy_option_data.get('last_price', 0),
                    'delta': buy_option_data.get('delta', 0),
                    'theta': buy_option_data.get('theta', 0),
                    'gamma': buy_option_data.get('gamma', 0),
                    'vega': buy_option_data.get('vega', 0),
                    'quantity': 1,
                    'rationale': f'Long 1x {buy_strike} call (ATM/ITM)'
                },
                {
                    'option_type': 'CALL',
                    'position': 'SHORT',
                    'strike': sell_strike,
                    'premium': sell_option_data.get('last_price', 0),
                    'delta': sell_option_data.get('delta', 0),
                    'theta': sell_option_data.get('theta', 0),
                    'gamma': sell_option_data.get('gamma', 0),
                    'vega': sell_option_data.get('vega', 0),
                    'quantity': 2,
                    'rationale': f'Short 2x {sell_strike} call (OTM)'
                }
            ]
            
            # Calculate strategy metrics
            metrics = self._calculate_metrics(legs, buy_strike, sell_strike)
            
            if not metrics:
                return {'success': False, 'reason': 'Unable to calculate strategy metrics'}
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error constructing Call Ratio Spread: {e}")
            return {'success': False, 'reason': f'Construction error: {str(e)}'}
    
    def _calculate_metrics(self, legs: List[Dict], buy_strike: float,
                         sell_strike: float) -> Optional[Dict]:
        """Calculate call ratio spread specific metrics"""
        try:
            # Extract details
            buy_premium = legs[0]['premium']
            sell_premium = legs[1]['premium']  # Per contract
            
            # Net debit/credit per lot
            net_cost_per_lot = buy_premium - (2 * sell_premium)
            is_credit = net_cost_per_lot < 0
            
            # Max profit at sell strike per lot
            if is_credit:
                max_profit_per_lot = abs(net_cost_per_lot) + (sell_strike - buy_strike)
            else:
                max_profit_per_lot = (sell_strike - buy_strike) - net_cost_per_lot
            
            # Max loss is limited to a reasonable amount for risk management
            max_loss_per_lot = abs(net_cost_per_lot) + ((sell_strike - buy_strike) * 2)  # Conservative estimate
            
            # Apply lot size multiplier for real position sizing
            total_max_profit = max_profit_per_lot * self.lot_size
            total_max_loss = max_loss_per_lot * self.lot_size
            total_net_cost = net_cost_per_lot * self.lot_size
            
            # Breakevens
            if is_credit:
                lower_breakeven = buy_strike - abs(net_cost_per_lot)
                upper_breakeven = sell_strike + max_profit_per_lot
            else:
                lower_breakeven = buy_strike + net_cost_per_lot
                upper_breakeven = sell_strike + (sell_strike - buy_strike - net_cost_per_lot)
            
            # Greeks
            buy_delta = legs[0]['delta']
            sell_delta = legs[1]['delta']
            net_delta = buy_delta - (2 * sell_delta)
            
            buy_theta = legs[0].get('theta', 0)
            sell_theta = legs[1].get('theta', 0)
            net_theta = buy_theta - (2 * sell_theta)
            
            buy_gamma = legs[0].get('gamma', 0)
            sell_gamma = legs[1].get('gamma', 0)
            net_gamma = buy_gamma - (2 * sell_gamma)
            
            # Simplified probability
            prob_profit = 0.4  # Conservative estimate for ratio spreads
            
            return {
                'success': True,
                'strategy_name': self.get_strategy_name(),
                'legs': legs,
                'max_profit': total_max_profit,
                'max_loss': total_max_loss,
                'probability_profit': prob_profit,
                'breakeven_points': [lower_breakeven, upper_breakeven],
                'delta_exposure': net_delta,
                'theta_decay': net_theta,
                'gamma_exposure': net_gamma,
                'optimal_outcome': f"Stock moves to {sell_strike} at expiry",
                'margin_requirement': 'HIGH',
                'risk_warning': f'Unlimited loss potential above {upper_breakeven:.2f}',
                'position_details': {
                    'lot_size': self.lot_size,
                    'net_cost_per_lot': net_cost_per_lot,
                    'max_profit_per_lot': max_profit_per_lot,
                    'max_loss_per_lot': max_loss_per_lot,
                    'total_cost': total_net_cost,
                    'total_contracts': self.lot_size * 3,  # 1 long + 2 short
                    'ratio': '1:2'
                },
                'strategy_note': f'{"Credit" if is_credit else "Debit"} ratio spread - Monitor risk above {sell_strike}'
            }
            
        except Exception as e:
            logger.error(f"Error calculating Call Ratio Spread metrics: {e}")
            return None
    
    def _calculate_probability_range(self, lower: float, upper: float,
                                   spot: float, market_analysis: Dict) -> float:
        """Calculate probability of price in range"""
        try:
            iv = market_analysis.get('iv_analysis', {}).get('atm_iv', 30) / 100
            days = 30
            
            std_dev = spot * iv * np.sqrt(days / 365)
            
            z_lower = (lower - spot) / std_dev
            z_upper = (upper - spot) / std_dev
            
            from scipy import stats
            prob = stats.norm.cdf(z_upper) - stats.norm.cdf(z_lower)
            
            return prob
            
        except:
            return 0.5