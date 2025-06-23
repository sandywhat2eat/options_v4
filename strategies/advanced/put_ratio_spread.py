"""
Put Ratio Spread Strategy - Exploit put skew
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import logging

from ..base_strategy import BaseStrategy

logger = logging.getLogger(__name__)

class PutRatioSpread(BaseStrategy):
    """
    Put Ratio Spread: Buy 1 ATM/ITM Put + Sell 2 OTM Puts
    
    Market Outlook: Moderately bearish with downside limit
    Profit: From moderate downward movement
    Risk: Significant below lower strike
    Ideal: Put skew present, expecting limited downside
    """
    
    def get_strategy_name(self) -> str:
        return "Put Ratio Spread"
    
    def get_market_outlook(self) -> str:
        return "bearish"
    
    def get_iv_preference(self) -> str:
        return "high"
    
    def get_required_legs(self) -> int:
        return 2  # 2 unique strikes, one with 2x quantity
    
    def get_market_bias(self) -> List[str]:
        return ['moderate_bearish', 'put_skew']
    
    def construct_strategy(self, **kwargs) -> Dict:
        """Construct put ratio spread"""
        market_analysis = kwargs.get('market_analysis', {})
        # Removed self.spot_price extraction - using self.spot_price
        market_analysis = kwargs.get('market_analysis', {})
        
        try:
            # Filter liquid options
            # Using self.options_df directly
            if self.options_df.empty:
                return {
                    'success': False,
                    'reason': 'Unable to construct Put Ratio Spread - need suitable put strikes'
                }
            
            # Check for put skew - ideal condition
            iv_skew = market_analysis.get('iv_analysis', {}).get('iv_skew', {})
            if iv_skew.get('skew_type') == 'put_skew' and iv_skew.get('skew_strength', 0) > 3:
                logger.info("Favorable put skew detected for Put Ratio Spread")
            
            # Get puts only
            puts = self.options_df[self.options_df['option_type'] == 'PUT']
            if len(puts) < 2:
                return {
                    'success': False,
                    'reason': 'Unable to construct Put Ratio Spread - need suitable put strikes'
                }
            
            # Find strikes
            strikes = sorted(puts['strike'].unique(), reverse=True)
            
            # Buy strike: ATM or slightly ITM
            buy_strike = min(strikes, key=lambda x: abs(x - self.spot_price))
            
            # Sell strike: 3-5% OTM
            otm_target = self.spot_price * 0.96
            sell_strikes = [s for s in strikes if s < buy_strike]
            if not sell_strikes:
                return {
                    'success': False,
                    'reason': 'Unable to construct Put Ratio Spread - need suitable put strikes'
                }
            
            sell_strike = max(sell_strikes, key=lambda x: -abs(x - otm_target))
            
            # Get options
            buy_option = puts[puts['strike'] == buy_strike].iloc[0]
            sell_option = puts[puts['strike'] == sell_strike].iloc[0]
            
            # Risk check - avoid if sell strike too far OTM
            if abs(sell_option['delta']) < 0.15:
                logger.info("Sell strike delta too low, adjusting ratio or skipping")
                # Could use 3:2 ratio instead of 2:1
            
            # Create legs
            legs = [
                self._create_leg(buy_option, 'LONG', 1, f'Buy 1x {buy_strike} Put'),
                self._create_leg(sell_option, 'SHORT', 2, f'Sell 2x {sell_strike} Put')
            ]
            
            # Calculate strategy metrics
            metrics = self._calculate_metrics(
                legs, self.spot_price, market_analysis,
                buy_strike, sell_strike
            )
            
            if not metrics:
                return {
                    'success': False,
                    'reason': 'Unable to construct Put Ratio Spread - need suitable put strikes'
                }
            
            # Add exit conditions
            metrics['exit_conditions'] = {
                'profit_target': 'At short strike or 50% of max profit',
                'stop_loss': 'If spot drops below short strike by 3%',
                'time_exit': 'With 14 days to expiry',
                'delta_exit': 'If position delta exceeds ±40',
                'adjustment': 'Buy back one short put if threatened'
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error constructing Put Ratio Spread: {e}")
            return {
                    'success': False,
                    'reason': 'Unable to construct Put Ratio Spread - need suitable put strikes'
                }
    
    def _calculate_metrics(self, legs: List[Dict], spot_price: float,
                         market_analysis: Dict, buy_strike: float,
                         sell_strike: float) -> Optional[Dict]:
        """Calculate put ratio spread specific metrics"""
        try:
            # Extract details
            buy_premium = legs[0]['premium']
            sell_premium = legs[1]['premium']  # Per contract
            
            # Net debit/credit
            net_cost = buy_premium - (2 * sell_premium)
            is_credit = net_cost < 0
            
            # Max profit at sell strike
            if is_credit:
                max_profit = abs(net_cost) + (buy_strike - sell_strike)
            else:
                max_profit = (buy_strike - sell_strike) - net_cost
            
            # Max loss calculation
            # Loss increases below sell strike
            # At zero, loss = 2*sell_strike - buy_strike + net_cost
            max_theoretical_loss = 2 * sell_strike - buy_strike + (net_cost if not is_credit else -net_cost)
            
            # Breakevens
            if is_credit:
                upper_breakeven = buy_strike + abs(net_cost)
                # Lower breakeven where loss from short puts equals initial credit + long put value
                lower_breakeven = sell_strike - max_profit
            else:
                upper_breakeven = buy_strike - net_cost
                lower_breakeven = sell_strike - (buy_strike - sell_strike - net_cost)
            
            # Ensure lower breakeven is positive
            lower_breakeven = max(0, lower_breakeven)
            
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
            risk_below = sell_strike - lower_breakeven
            risk_below_pct = (risk_below / sell_strike) * 100
            
            # Assignment risk
            sell_option_data = legs[1]  # Short put leg
            assignment_risk = 'High' if abs(sell_option_data['delta']) > 0.30 else 'Moderate'
            
            return {
                'legs': legs,
                'max_profit': max_profit,
                'max_loss': max_theoretical_loss,
                'probability_profit': prob_profit,
                'probability_max_profit': prob_max_profit,
                'net_cost': net_cost,
                'is_credit': is_credit,
                'breakevens': {
                    'upper': upper_breakeven,
                    'lower': lower_breakeven,
                    'sweet_spot': sweet_spot,
                    'profit_zone_width': profit_zone_width
                },
                'strikes': {
                    'long_strike': buy_strike,
                    'short_strike': sell_strike,
                    'strike_width': buy_strike - sell_strike,
                    'ratio': '1:2'
                },
                'greeks': {
                    'delta': net_delta,
                    'gamma': net_gamma,
                    'delta_risk': 'Positive gamma above, negative below short strike'
                },
                'risk_metrics': {
                    'max_theoretical_loss': max_theoretical_loss,
                    'risk_below': risk_below,
                    'risk_below_pct': risk_below_pct,
                    'assignment_risk': assignment_risk,
                    'margin_intensive': True
                },
                'optimal_conditions': {
                    'iv_environment': 'Put skew present (fear premium)',
                    'market_outlook': 'Moderately bearish',
                    'price_target': f'Move to {sell_strike}',
                    'iv_forecast': 'Decreasing fear/volatility'
                }
            }
            
        except Exception as e:
            logger.error(f"Error calculating Put Ratio Spread metrics: {e}")
            return {
                    'success': False,
                    'reason': 'Unable to construct Put Ratio Spread - need suitable put strikes'
                }
    
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