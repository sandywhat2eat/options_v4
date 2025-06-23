"""
Broken Wing Butterfly Strategy - Asymmetric butterfly for directional bias
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import logging

from ..base_strategy import BaseStrategy

logger = logging.getLogger(__name__)

class BrokenWingButterfly(BaseStrategy):
    """
    Broken Wing Butterfly: Asymmetric butterfly with directional bias
    Buy 1 ITM + Sell 2 ATM + Buy 1 Far OTM (wider wing on one side)
    
    Market Outlook: Directional with limited risk
    Profit: Maximum at middle strike with directional edge
    Risk: Limited, potentially credit on one side
    Ideal: Moderate directional view with volatility contraction
    """
    
    def get_strategy_name(self) -> str:
        return "Broken Wing Butterfly"
    
    def get_market_outlook(self) -> str:
        return "neutral"
    
    def get_iv_preference(self) -> str:
        return "high"
    
    def get_required_legs(self) -> int:
        return 4  # 3 strikes, middle with 2x quantity
    
    def get_market_bias(self) -> List[str]:
        return ['moderate_bullish', 'moderate_bearish', 'volatility_contraction']
    
    def construct_strategy(self, **kwargs) -> Dict:
        """Construct broken wing butterfly"""
        market_analysis = kwargs.get('market_analysis', {})
        # Removed self.spot_price extraction - using self.spot_price
        market_analysis = kwargs.get('market_analysis', {})
        
        try:
            # Filter liquid options
            # Using self.options_df directly
            if self.options_df.empty:
                return {
                    'success': False,
                    'reason': 'No liquid options available for Broken Wing Butterfly'
                }
            
            # Get market direction
            direction = market_analysis.get('direction', 'neutral').lower()
            confidence = market_analysis.get('confidence', 0.5)
            
            if 'neutral' in direction or confidence < 0.4:
                logger.info("Need directional bias for Broken Wing Butterfly")
                return None
            
            # Decide on calls or puts
            use_calls = 'bullish' in direction
            option_type = 'CALL' if use_calls else 'PUT'
            
            type_options = self.options_df[self.options_df['option_type'] == option_type]
            if len(type_options) < 3:
                return None
            
            strikes = sorted(type_options['strike'].unique())
            
            # Find ATM strike (body)
            atm_strike = min(strikes, key=lambda x: abs(x - self.spot_price))
            
            if use_calls:
                # Bullish broken wing - wider upper wing
                lower_strikes = [s for s in strikes if s < atm_strike]
                upper_strikes = [s for s in strikes if s > atm_strike]
                
                if not lower_strikes or len(upper_strikes) < 2:
                    return None
                
                # Standard lower wing (2-3% below ATM)
                lower_target = atm_strike * 0.975
                lower_strike = max(lower_strikes, key=lambda x: -abs(x - lower_target))
                
                # Extended upper wing (5-7% above ATM)
                upper_target = atm_strike * 1.06
                upper_strike = min([s for s in upper_strikes if s >= upper_target], 
                                 default=max(upper_strikes))
            else:
                # Bearish broken wing - wider lower wing
                lower_strikes = [s for s in strikes if s < atm_strike]
                upper_strikes = [s for s in strikes if s > atm_strike]
                
                if len(lower_strikes) < 2 or not upper_strikes:
                    return None
                
                # Extended lower wing (5-7% below ATM)
                lower_target = atm_strike * 0.94
                lower_strike = max([s for s in lower_strikes if s <= lower_target], 
                                 default=min(lower_strikes))
                
                # Standard upper wing (2-3% above ATM)
                upper_target = atm_strike * 1.025
                upper_strike = min(upper_strikes, key=lambda x: abs(x - upper_target))
            
            # Get options
            lower_option = type_options[type_options['strike'] == lower_strike].iloc[0]
            atm_option = type_options[type_options['strike'] == atm_strike].iloc[0]
            upper_option = type_options[type_options['strike'] == upper_strike].iloc[0]
            
            # Create legs
            legs = [
                self._create_leg(lower_option, 'LONG', 1, f'Lower wing at {lower_strike}'),
                self._create_leg(atm_option, 'SHORT', 2, f'Body at {atm_strike} (2x)'),
                self._create_leg(upper_option, 'LONG', 1, f'Upper wing at {upper_strike}')
            ]
            
            # Calculate strategy metrics
            metrics = self._calculate_metrics(
                legs, self.spot_price, market_analysis,
                lower_strike, atm_strike, upper_strike,
                use_calls
            )
            
            if not metrics:
                return None
            
            # Add exit conditions
            metrics['exit_conditions'] = {
                'profit_target': '40-60% of max profit',
                'stop_loss': 'If position shows 50% of max loss',
                'time_exit': 'With 14 days to expiry',
                'price_exit': 'If price moves beyond extended wing',
                'adjustment': 'Close profitable side if direction changes'
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error constructing Broken Wing Butterfly: {e}")
            return None
    
    def _calculate_metrics(self, legs: List[Dict], spot_price: float,
                         market_analysis: Dict, lower_strike: float,
                         atm_strike: float, upper_strike: float,
                         use_calls: bool) -> Optional[Dict]:
        """Calculate broken wing butterfly metrics"""
        try:
            # Extract premiums
            lower_debit = legs[0]['premium']
            atm_credit = -legs[1]['premium'] * 2  # Sold 2x
            upper_debit = legs[2]['premium']
            
            # Net cost (could be credit)
            net_cost = lower_debit + upper_debit - atm_credit
            is_credit = net_cost < 0
            
            # Wing widths
            lower_wing = atm_strike - lower_strike
            upper_wing = upper_strike - atm_strike
            wider_wing = max(lower_wing, upper_wing)
            narrower_wing = min(lower_wing, upper_wing)
            
            # Max profit at ATM
            if is_credit:
                max_profit = abs(net_cost) + narrower_wing
            else:
                max_profit = narrower_wing - net_cost
            
            # Max loss
            if is_credit:
                # No risk on credit side
                if use_calls and upper_wing > lower_wing:
                    max_loss = 0  # Credit received, bullish bias
                elif not use_calls and lower_wing > upper_wing:
                    max_loss = 0  # Credit received, bearish bias
                else:
                    max_loss = wider_wing - narrower_wing - abs(net_cost)
            else:
                max_loss = wider_wing - narrower_wing + net_cost
            
            # Ensure max_loss is not negative
            max_loss = max(0, max_loss)
            
            # Breakevens
            if is_credit:
                if use_calls:
                    lower_breakeven = lower_strike - abs(net_cost)
                    upper_breakeven = upper_strike + abs(net_cost)
                else:
                    lower_breakeven = lower_strike - abs(net_cost)
                    upper_breakeven = upper_strike + abs(net_cost)
            else:
                lower_breakeven = lower_strike + net_cost
                upper_breakeven = upper_strike - net_cost
            
            # Probability calculations
            prob_profit = self._calculate_probability_range(
                lower_breakeven,
                upper_breakeven,
                self.spot_price,
                market_analysis or {}
            )
            
            # Greeks
            total_delta = sum(
                leg['delta'] * leg.get('quantity', 1) * 
                (-1 if leg['position'] == 'SHORT' else 1)
                for leg in legs
            )
            
            # Directional edge
            if use_calls:
                directional_edge = upper_wing > lower_wing
                edge_description = "Bullish bias - wider upper wing"
            else:
                directional_edge = lower_wing > upper_wing
                edge_description = "Bearish bias - wider lower wing"
            
            return {
                'legs': legs,
                'max_profit': max_profit,
                'max_loss': max_loss,
                'probability_profit': prob_profit,
                'net_cost': net_cost,
                'is_credit': is_credit,
                'breakevens': {
                    'lower': lower_breakeven,
                    'upper': upper_breakeven,
                    'sweet_spot': atm_strike
                },
                'wings': {
                    'lower_wing': lower_wing,
                    'upper_wing': upper_wing,
                    'asymmetry_ratio': wider_wing / narrower_wing,
                    'directional_edge': edge_description
                },
                'strikes': {
                    'lower': lower_strike,
                    'middle': atm_strike,
                    'upper': upper_strike
                },
                'greeks': {
                    'delta': total_delta,
                    'position_type': 'Delta positive' if total_delta > 0 else 'Delta negative'
                },
                'risk_metrics': {
                    'risk_reward': max_profit / max_loss if max_loss > 0 else float('inf'),
                    'risk_type': 'No risk' if max_loss == 0 else 'Limited risk'
                },
                'optimal_conditions': {
                    'market_outlook': f'{"Bullish" if use_calls else "Bearish"} with target at {atm_strike}',
                    'iv_environment': 'Normal to high IV',
                    'volatility_forecast': 'Decreasing',
                    'key_advantage': 'Directional edge with limited risk'
                }
            }
            
        except Exception as e:
            logger.error(f"Error calculating Broken Wing Butterfly metrics: {e}")
            return {
                'success': False,
                'reason': f'Error constructing Broken Wing Butterfly: {str(e)}'
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