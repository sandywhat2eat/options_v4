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
    
    def construct_strategy(self, **kwargs) -> Dict:
        """Construct call ratio spread"""
        market_analysis = kwargs.get('market_analysis', {})
        # Removed self.spot_price extraction - using self.spot_price
        market_analysis = kwargs.get('market_analysis', {})
        
        try:
            # Filter liquid options
            # Using self.options_df directly
            if self.options_df.empty:
                return None
            
            # Check for call skew
            iv_skew = market_analysis.get('iv_analysis', {}).get('iv_skew', {})
            if iv_skew.get('skew_type') != 'call_skew':
                logger.info("No call skew for Call Ratio Spread")
                # Continue anyway but note suboptimal conditions
            
            # Get calls only
            calls = self.options_df[self.options_df['option_type'] == 'CALL']
            if len(calls) < 2:
                return None
            
            # Find strikes
            strikes = sorted(calls['strike'].unique())
            
            # Buy strike: ATM or slightly ITM
            buy_strike = min(strikes, key=lambda x: abs(x - self.spot_price))
            
            # Sell strike: 3-5% OTM
            otm_target = self.spot_price * 1.04
            sell_strikes = [s for s in strikes if s > buy_strike]
            if not sell_strikes:
                return None
            
            sell_strike = min(sell_strikes, key=lambda x: abs(x - otm_target))
            
            # Get options
            buy_option = calls[calls['strike'] == buy_strike].iloc[0]
            sell_option = calls[calls['strike'] == sell_strike].iloc[0]
            
            # Check if 2x sell is too risky
            if sell_option['delta'] > 0.25:
                logger.info("Sell strike delta too high for 2x ratio")
                # Could adjust to 1.5x or skip
            
            # Create legs
            legs = [
                self._create_leg(buy_option, 'LONG', 1, f'Buy 1x {buy_strike} Call'),
                self._create_leg(sell_option, 'SHORT', 2, f'Sell 2x {sell_strike} Call')
            ]
            
            # Calculate strategy metrics
            metrics = self._calculate_metrics(
                legs, self.spot_price, market_analysis,
                buy_strike, sell_strike
            )
            
            if not metrics:
                return None
            
            # Add exit conditions
            metrics['exit_conditions'] = {
                'profit_target': 'At short strike or 50% of max profit',
                'stop_loss': 'If spot exceeds short strike by 2%',
                'time_exit': 'With 14 days to expiry',
                'delta_exit': 'If position delta exceeds ±30',
                'adjustment': 'Buy back one short call if threatened'
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error constructing Call Ratio Spread: {e}")
            return None
    
    def _calculate_metrics(self, legs: List[Dict], spot_price: float,
                         market_analysis: Dict, buy_strike: float,
                         sell_strike: float) -> Optional[Dict]:
        """Calculate call ratio spread specific metrics"""
        try:
            # Extract details
            buy_premium = legs[0]['premium']
            sell_premium = legs[1]['premium']  # Per contract
            
            # Net debit/credit
            net_cost = buy_premium - (2 * sell_premium)
            is_credit = net_cost < 0
            
            # Max profit at sell strike
            if is_credit:
                max_profit = abs(net_cost) + (sell_strike - buy_strike)
            else:
                max_profit = (sell_strike - buy_strike) - net_cost
            
            # Max loss is unlimited above
            max_loss = float('inf')
            
            # Breakevens
            if is_credit:
                lower_breakeven = buy_strike - abs(net_cost)
                upper_breakeven = sell_strike + max_profit
            else:
                lower_breakeven = buy_strike + net_cost
                upper_breakeven = sell_strike + (sell_strike - buy_strike - net_cost)
            
            # Profit zone
            profit_zone_width = upper_breakeven - lower_breakeven
            sweet_spot = sell_strike  # Max profit point
            
            # Probability calculations
            prob_profit = self._calculate_probability_range(
                lower_breakeven,
                upper_breakeven,
                self.spot_price,
                market_analysis
            )
            
            prob_max_profit = self._calculate_probability_range(
                sell_strike * 0.98,
                sell_strike * 1.02,
                self.spot_price,
                market_analysis
            )
            
            # Greeks
            buy_delta = legs[0]['delta']
            sell_delta = legs[1]['delta']
            net_delta = buy_delta - (2 * sell_delta)
            
            buy_gamma = legs[0].get('gamma', 0)
            sell_gamma = legs[1].get('gamma', 0)
            net_gamma = buy_gamma - (2 * sell_gamma)
            
            # Risk analysis
            risk_above = upper_breakeven - sell_strike
            risk_above_pct = (risk_above / sell_strike) * 100
            
            return {
                'legs': legs,
                'max_profit': max_profit,
                'max_loss': max_loss,
                'probability_profit': prob_profit,
                'probability_max_profit': prob_max_profit,
                'net_cost': net_cost,
                'is_credit': is_credit,
                'breakevens': {
                    'lower': lower_breakeven,
                    'upper': upper_breakeven,
                    'sweet_spot': sweet_spot,
                    'profit_zone_width': profit_zone_width
                },
                'strikes': {
                    'long_strike': buy_strike,
                    'short_strike': sell_strike,
                    'strike_width': sell_strike - buy_strike,
                    'ratio': '1:2'
                },
                'greeks': {
                    'delta': net_delta,
                    'gamma': net_gamma,
                    'delta_risk': 'Negative gamma above short strike'
                },
                'risk_metrics': {
                    'unlimited_risk': True,
                    'risk_above': risk_above,
                    'risk_above_pct': risk_above_pct,
                    'margin_intensive': True
                },
                'optimal_conditions': {
                    'iv_environment': 'Call skew present',
                    'market_outlook': 'Moderately bullish',
                    'price_target': f'Move to {sell_strike}',
                    'iv_forecast': 'Stable or decreasing'
                }
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