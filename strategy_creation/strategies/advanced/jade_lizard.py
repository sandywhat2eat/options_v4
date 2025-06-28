"""
Jade Lizard Strategy - Skew exploitation with no upside risk
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import logging

from ..base_strategy import BaseStrategy

logger = logging.getLogger(__name__)

class JadeLizard(BaseStrategy):
    """
    Jade Lizard: Sell OTM Put + Sell OTM Call Spread
    Components: Short Put + Short Call + Long Call (further OTM)
    
    Market Outlook: Neutral to slightly bullish
    Profit: Premium collection with no upside risk
    Risk: Downside risk from short put
    Ideal: High IV with put skew
    """
    
    def get_strategy_name(self) -> str:
        return "Jade Lizard"
    
    def get_market_outlook(self) -> str:
        return "neutral"
    
    def get_iv_preference(self) -> str:
        return "high"
    
    def get_required_legs(self) -> int:
        return 3
    
    def get_market_bias(self) -> List[str]:
        return ['neutral_bullish', 'high_iv', 'put_skew']
    
    def construct_strategy(self, **kwargs) -> Dict:
        """Construct jade lizard"""
        market_analysis = kwargs.get('market_analysis', {})
        # Removed self.spot_price extraction - using self.spot_price
        market_analysis = kwargs.get('market_analysis', {})
        
        try:
            # Filter liquid options
            # Using self.options_df directly
            if self.options_df.empty:
                return {
                    'success': False,
                    'reason': 'Unable to construct Jade Lizard - complex strategy needs specific conditions'
                }
            
            # Check IV environment - prefer high IV
            iv_analysis = market_analysis.get('iv_analysis', {})
            atm_iv = iv_analysis.get('atm_iv', 30)
            if atm_iv < 30:
                logger.info("IV too low for Jade Lizard")
                return {
                    'success': False,
                    'reason': 'Unable to construct Jade Lizard - complex strategy needs specific conditions'
                }
            
            # Check for put skew - ideal condition
            if iv_analysis.get('iv_skew', {}).get('skew_type') == 'put_skew':
                logger.info("Favorable put skew for Jade Lizard")
            
            # Separate calls and puts
            calls = self.options_df[self.options_df['option_type'] == 'CALL']
            puts = self.options_df[self.options_df['option_type'] == 'PUT']
            
            if len(calls) < 2 or puts.empty:
                return {
                    'success': False,
                    'reason': 'Unable to construct Jade Lizard - complex strategy needs specific conditions'
                }
            
            # Strike selection
            # Short put: 5-7% OTM
            put_target = self.spot_price * 0.94
            put_strikes = puts[puts['strike'] < self.spot_price]['strike'].unique()
            if len(put_strikes) == 0:
                return {
                    'success': False,
                    'reason': 'Unable to construct Jade Lizard - complex strategy needs specific conditions'
                }
            
            short_put_strike = max(put_strikes, key=lambda x: -abs(x - put_target))
            
            # Call spread: Short 3-4% OTM, Long 6-8% OTM
            short_call_target = self.spot_price * 1.035
            long_call_target = self.spot_price * 1.07
            
            call_strikes = sorted(calls['strike'].unique())
            otm_call_strikes = [s for s in call_strikes if s > self.spot_price]
            
            if len(otm_call_strikes) < 2:
                return {
                    'success': False,
                    'reason': 'Unable to construct Jade Lizard - complex strategy needs specific conditions'
                }
            
            short_call_strike = min(otm_call_strikes, key=lambda x: abs(x - short_call_target))
            long_call_strikes = [s for s in otm_call_strikes if s > short_call_strike]
            
            if not long_call_strikes:
                return {
                    'success': False,
                    'reason': 'Unable to construct Jade Lizard - complex strategy needs specific conditions'
                }
            
            long_call_strike = min(long_call_strikes, key=lambda x: abs(x - long_call_target))
            
            # Get options
            short_put = puts[puts['strike'] == short_put_strike].iloc[0]
            short_call = calls[calls['strike'] == short_call_strike].iloc[0]
            long_call = calls[calls['strike'] == long_call_strike].iloc[0]
            
            # Create legs
            legs = [
                self._create_leg(short_put, 'SHORT', 1, 'Short Put - Premium collection'),
                self._create_leg(short_call, 'SHORT', 1, 'Short Call - Premium collection'),
                self._create_leg(long_call, 'LONG', 1, 'Long Call - Upside protection')
            ]
            
            # Calculate strategy metrics
            metrics = self._calculate_metrics(
                legs, self.spot_price, market_analysis,
                short_put_strike, short_call_strike, long_call_strike
            )
            
            if not metrics:
                return {
                    'success': False,
                    'reason': 'Unable to construct Jade Lizard - complex strategy needs specific conditions'
                }
            
            # Check if total credit > call spread width (no upside risk)
            if not metrics.get('no_upside_risk'):
                logger.info("Jade Lizard credit insufficient - has upside risk")
            
            # Add exit conditions
            metrics['exit_conditions'] = {
                'profit_target': '25-50% of credit received',
                'stop_loss': 'If short put tested or loss > credit',
                'time_exit': 'With 21 days to expiry',
                'adjustment': 'Roll put down if tested, close call spread if profitable'
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error constructing Jade Lizard: {e}")
            return {
                    'success': False,
                    'reason': 'Unable to construct Jade Lizard - complex strategy needs specific conditions'
                }
    
    def _calculate_metrics(self, legs: List[Dict], spot_price: float,
                         market_analysis: Dict, put_strike: float,
                         short_call_strike: float, long_call_strike: float) -> Optional[Dict]:
        """Calculate jade lizard metrics"""
        try:
            # Extract premiums
            put_credit = -legs[0]['premium']      # Short put
            short_call_credit = -legs[1]['premium'] # Short call
            long_call_debit = legs[2]['premium']   # Long call
            
            # Total credit
            total_credit = put_credit + short_call_credit - long_call_debit
            
            # Call spread width
            call_spread_width = long_call_strike - short_call_strike
            
            # Check for no upside risk
            no_upside_risk = total_credit >= call_spread_width
            
            # Max profit = total credit (if no upside risk)
            max_profit = total_credit
            
            # Max loss calculation
            if no_upside_risk:
                # Loss only on downside from put
                max_loss = put_strike - total_credit
            else:
                # Additional loss possible on upside
                upside_loss = call_spread_width - total_credit
                downside_loss = put_strike - total_credit
                max_loss = max(upside_loss, downside_loss)
            
            # Breakevens
            downside_breakeven = put_strike - total_credit
            
            if no_upside_risk:
                upside_breakeven = float('inf')  # No upside risk
            else:
                upside_breakeven = short_call_strike + total_credit
            
            # Probability calculations
            # Profit if above downside breakeven and below short call (if upside risk)
            prob_above_put_be = 1 - self._calculate_probability_itm(
                downside_breakeven, self.spot_price, market_analysis, 'PUT'
            )
            
            if no_upside_risk:
                probability_profit = prob_above_put_be
            else:
                prob_below_call = self._calculate_probability_itm(
                    short_call_strike, self.spot_price, market_analysis, 'CALL'
                )
                probability_profit = prob_above_put_be * prob_below_call
            
            # Greeks
            total_delta = -legs[0]['delta'] - legs[1]['delta'] + legs[2]['delta']
            total_gamma = -legs[0].get('gamma', 0) - legs[1].get('gamma', 0) + legs[2].get('gamma', 0)
            total_theta = -legs[0].get('theta', 0) - legs[1].get('theta', 0) + legs[2].get('theta', 0)
            total_vega = -legs[0].get('vega', 0) - legs[1].get('vega', 0) + legs[2].get('vega', 0)
            
            # Risk metrics
            put_margin = put_strike * 0.15 - put_credit
            call_spread_margin = (call_spread_width - short_call_credit + long_call_debit) * 0.5
            total_margin = max(put_margin, call_spread_margin)
            
            return_on_margin = (max_profit / total_margin) * 100 if total_margin > 0 else 0
            
            return {
                'legs': legs,
                'max_profit': max_profit,
                'max_loss': max_loss,
                'probability_profit': probability_profit,
                'total_credit': total_credit,
                'no_upside_risk': no_upside_risk,
                'breakevens': {
                    'downside': downside_breakeven,
                    'upside': upside_breakeven if not no_upside_risk else 'None',
                    'profit_zone': f'Above {downside_breakeven}'
                },
                'strikes': {
                    'short_put': put_strike,
                    'short_call': short_call_strike,
                    'long_call': long_call_strike,
                    'call_spread_width': call_spread_width
                },
                'greeks': {
                    'delta': total_delta,
                    'gamma': total_gamma,
                    'theta': total_theta,
                    'vega': total_vega
                },
                'risk_metrics': {
                    'risk_reward': max_profit / max_loss if max_loss > 0 else float('inf'),
                    'margin_requirement': total_margin,
                    'return_on_margin': return_on_margin,
                    'assignment_risk': 'Moderate on put side'
                },
                'optimal_conditions': {
                    'iv_environment': 'High IV with put skew',
                    'market_outlook': 'Neutral to slightly bullish',
                    'volatility_forecast': 'Decreasing',
                    'key_advantage': 'No upside risk when properly constructed'
                }
            }
            
        except Exception as e:
            logger.error(f"Error calculating Jade Lizard metrics: {e}")
            return {
                    'success': False,
                    'reason': 'Unable to construct Jade Lizard - complex strategy needs specific conditions'
                }