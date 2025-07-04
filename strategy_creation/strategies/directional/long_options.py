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
    
    def construct_strategy(self, strike: float = None, use_expected_moves: bool = True, target_delta: float = 0.45) -> Dict:
        """
        Construct Long Call strategy
        
        Args:
            strike: Specific strike to use (optional)
            use_expected_moves: Use intelligent strike selection based on expected moves
            target_delta: Target delta for option selection (default 0.45)
        """
        try:
            logger.info(f"Constructing Long Call for {self.symbol} at spot {self.spot_price}")
            
            if strike is None:
                if use_expected_moves and self.strike_selector:
                    # Use centralized strike selection
                    logger.info("Using intelligent strike selection for Long Call")
                    strikes = self.select_strikes_for_strategy(use_expected_moves=True)
                    
                    if strikes and 'strike' in strikes:
                        strike = strikes['strike']
                        logger.info(f"Selected CALL strike via intelligent selector: {strike}")
                    else:
                        logger.warning("Intelligent strike selection failed, using fallback")
                        strike = self._find_optimal_strike(target_delta, 'CALL')
                else:
                    # Fallback to delta-based selection with higher delta for better probability
                    logger.info(f"Using delta-based selection with target delta {target_delta}")
                    strike = self._find_optimal_strike(target_delta, 'CALL')  # Higher delta for better PoP
            
            logger.info(f"Selected strike: {strike}")
            
            if not self.validate_strikes([strike]):
                logger.warning(f"Strike validation failed for {strike}")
                return {'success': False, 'reason': 'Invalid strike selection'}
            
            # Get option data
            call_data = self._get_option_data(strike, 'CALL')
            if call_data is None:
                logger.warning(f"No option data available for strike {strike}")
                return {'success': False, 'reason': 'Option data not available'}
            
            logger.info(f"Found option data: Delta={call_data.get('delta', 0):.3f}, Premium={call_data.get('last_price', 0)}")
            
            # Construct leg using base class method for complete data extraction
            self.legs = [self._create_leg(
                call_data, 
                'LONG', 
                quantity=1, 
                rationale='Bullish directional play'
            )]
            
            # Calculate metrics
            risk_metrics = self.get_risk_metrics()
            greeks = self.get_greeks_summary()
            
            # Apply lot size multiplier for real position sizing
            premium_per_contract = call_data.get('last_price', 0)
            total_cost = premium_per_contract * self.lot_size
            total_max_loss = total_cost
            
            # Calculate probability of profit using market-aware approach
            delta = abs(call_data.get('delta', 0.5))
            
            # Calculate premium as percentage of strike
            premium_pct = (premium_per_contract / strike) * 100 if strike > 0 else 2.0
            
            # Get IV percentile if available
            iv_percentile = None
            if self.market_analysis and 'iv_analysis' in self.market_analysis:
                iv_percentile = self.market_analysis['iv_analysis'].get('iv_percentile', None)
            
            # Calculate days to expiry (simplified - would need expiry date)
            days_to_expiry = 30  # Default assumption, should get from options data
            
            # Use enhanced probability calculation
            from strategy_creation import ProbabilityEngine
            prob_engine = ProbabilityEngine()
            probability_profit = prob_engine.calculate_market_aware_probability(
                delta=delta,
                option_type='CALL',
                position='LONG',
                iv=call_data.get('iv', 30),
                days_to_expiry=days_to_expiry,
                premium_pct_of_strike=premium_pct,
                iv_percentile=iv_percentile
            )
            
            return {
                'success': True,
                'strategy_name': self.get_strategy_name(),
                'legs': self.legs,
                'max_profit': float('inf'),  # Unlimited upside
                'max_loss': total_max_loss,  # Total cost with lot size
                'breakeven': strike + premium_per_contract,  # Breakeven per share
                'probability_profit': probability_profit,  # ADDED THIS FIELD
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
    
    def construct_strategy(self, strike: float = None, use_expected_moves: bool = True, target_delta: float = 0.35) -> Dict:
        """
        Construct Long Put strategy
        
        Args:
            strike: Specific strike to use (optional)
            use_expected_moves: Use intelligent strike selection based on expected moves
            target_delta: Target delta for option selection (default 0.35)
        """
        try:
            if strike is None:
                if use_expected_moves and self.strike_selector:
                    # Use centralized strike selection
                    logger.info("Using intelligent strike selection for Long Put")
                    strikes = self.select_strikes_for_strategy(use_expected_moves=True)
                    
                    if strikes and 'strike' in strikes:
                        strike = strikes['strike']
                        logger.info(f"Selected PUT strike via intelligent selector: {strike}")
                    else:
                        logger.warning("Intelligent strike selection failed, using fallback")
                        strike = self._find_optimal_strike(target_delta, 'PUT')
                else:
                    # Fallback to delta-based selection
                    logger.info(f"Using delta-based strike selection with target delta {target_delta}")
                    strike = self._find_optimal_strike(target_delta, 'PUT')
            
            if not self.validate_strikes([strike]):
                return {'success': False, 'reason': 'Invalid strike selection'}
            
            # Get option data
            put_data = self._get_option_data(strike, 'PUT')
            if put_data is None:
                return {'success': False, 'reason': 'Option data not available'}
            
            # Construct leg using base class method for complete data extraction
            self.legs = [self._create_leg(
                put_data, 
                'LONG', 
                quantity=1, 
                rationale='Bearish directional play'
            )]
            
            # Calculate metrics
            greeks = self.get_greeks_summary()
            premium_per_contract = put_data.get('last_price', 0)
            
            # Apply lot size multiplier for real position sizing
            total_cost = premium_per_contract * self.lot_size
            max_profit_per_contract = strike - premium_per_contract
            total_max_profit = max_profit_per_contract * self.lot_size
            
            # Calculate probability of profit using market-aware approach
            delta = abs(put_data.get('delta', 0.5))
            
            # Calculate premium as percentage of strike
            premium_pct = (premium_per_contract / strike) * 100 if strike > 0 else 2.0
            
            # Get IV percentile if available
            iv_percentile = None
            if self.market_analysis and 'iv_analysis' in self.market_analysis:
                iv_percentile = self.market_analysis['iv_analysis'].get('iv_percentile', None)
            
            # Calculate days to expiry (simplified - would need expiry date)
            days_to_expiry = 30  # Default assumption, should get from options data
            
            # Use enhanced probability calculation
            from strategy_creation import ProbabilityEngine
            prob_engine = ProbabilityEngine()
            probability_profit = prob_engine.calculate_market_aware_probability(
                delta=delta,
                option_type='PUT',
                position='LONG',
                iv=put_data.get('iv', 30),
                days_to_expiry=days_to_expiry,
                premium_pct_of_strike=premium_pct,
                iv_percentile=iv_percentile
            )
            
            return {
                'success': True,
                'strategy_name': self.get_strategy_name(),
                'legs': self.legs,
                'max_profit': total_max_profit,  # Total profit with lot size
                'max_loss': total_cost,  # Total cost with lot size
                'breakeven': strike - premium_per_contract,  # Breakeven per share
                'probability_profit': probability_profit,  # ADDED THIS FIELD
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