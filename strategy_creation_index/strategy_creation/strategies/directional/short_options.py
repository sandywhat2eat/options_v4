"""
Short options strategies (Short Call, Short Put)
"""

import pandas as pd
import logging
from typing import Dict, List
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from strategies.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)

class ShortCall(BaseStrategy):
    """Short Call strategy implementation"""
    
    def get_strategy_name(self) -> str:
        return "Short Call"
    
    def get_market_outlook(self) -> str:
        return "bearish"
    
    def get_iv_preference(self) -> str:
        return "high"
    
    def construct_strategy(self, strike: float = None, use_expected_moves: bool = True, target_delta: float = -0.30) -> Dict:
        """
        Construct Short Call strategy
        
        Args:
            strike: Specific strike to use (optional)
            use_expected_moves: Use intelligent strike selection based on expected moves
            target_delta: Target delta for option selection (default -0.30, slightly OTM)
        """
        try:
            logger.info(f"Constructing Short Call for {self.symbol} at spot {self.spot_price}")
            
            # Check IV environment - prefer high IV for premium collection
            market_analysis = getattr(self, 'market_analysis', {})
            iv_analysis = market_analysis.get('iv_analysis', {})
            atm_iv = iv_analysis.get('atm_iv', 0)
            
            if atm_iv < 15:  # Skip if IV too low for attractive premium
                logger.info("IV too low for Short Call premium collection")
                return {
                    'success': False,
                    'reason': 'IV too low for attractive premium collection'
                }
            
            if strike is None:
                if use_expected_moves and self.market_analysis and hasattr(self, 'strike_selector') and self.strike_selector:
                    # Use intelligent strike selection
                    logger.info("Using intelligent strike selection")
                    strike = self.strike_selector.select_optimal_strike(
                        self.options_df, self.spot_price, self.market_analysis,
                        'Short Call', 'CALL'
                    )
                else:
                    # Use OTM strike for better probability of keeping premium
                    logger.info(f"Using delta-based selection with target delta {target_delta}")
                    strike = self._find_optimal_strike(target_delta, 'CALL')
            
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
            
            # Construct leg
            self.legs = [{
                'option_type': 'CALL',
                'position': 'SHORT',
                'strike': strike,
                'premium': call_data.get('last_price', 0),
                'delta': call_data.get('delta', 0),
                'rationale': 'Premium collection on bearish/neutral outlook'
            }]
            
            # Calculate metrics
            risk_metrics = self.get_risk_metrics()
            greeks = self.get_greeks_summary()
            
            # Calculate probability of profit for short call
            # Short call profits if stock stays below strike at expiry
            call_delta = abs(call_data.get('delta', 0.30))
            
            # Probability of profit ≈ 1 - delta (probability stock stays below strike)
            probability_profit = max(0.45, min(0.85, 1.0 - call_delta))
            
            logger.info(f"Short Call PoP calculation: Delta={call_delta:.3f}, PoP={probability_profit:.3f}")
            
            strategy_data = {
                'success': True,
                'strategy_name': self.get_strategy_name(),
                'market_outlook': self.get_market_outlook(),
                'iv_preference': self.get_iv_preference(),
                'legs': self.legs,
                'risk_metrics': risk_metrics,
                'greeks': greeks,
                'probability_profit': probability_profit,
                'setup_cost': -call_data.get('last_price', 0),  # Negative because we receive premium
                'max_profit': call_data.get('last_price', 0),
                'max_loss': 'Unlimited',
                'breakeven': strike + call_data.get('last_price', 0),
                'expiry_date': self.options_df['expiry'].iloc[0] if not self.options_df.empty else None,
                'days_to_expiry': self._get_days_to_expiry(),
                'rationale': f"Short Call at strike {strike}: Premium collection in high IV environment, expecting stock to stay below {strike}"
            }
            
            return strategy_data
            
        except Exception as e:
            logger.error(f"Error constructing Short Call: {e}")
            return {'success': False, 'reason': f'Construction error: {str(e)}'}


class ShortPut(BaseStrategy):
    """Short Put strategy implementation"""
    
    def get_strategy_name(self) -> str:
        return "Short Put"
    
    def get_market_outlook(self) -> str:
        return "bullish"
    
    def get_iv_preference(self) -> str:
        return "high"
    
    def construct_strategy(self, strike: float = None, use_expected_moves: bool = True, target_delta: float = 0.30) -> Dict:
        """
        Construct Short Put strategy
        
        Args:
            strike: Specific strike to use (optional)
            use_expected_moves: Use intelligent strike selection based on expected moves
            target_delta: Target delta for option selection (default 0.30, slightly OTM)
        """
        try:
            logger.info(f"Constructing Short Put for {self.symbol} at spot {self.spot_price}")
            
            # Check IV environment - prefer high IV for premium collection
            market_analysis = getattr(self, 'market_analysis', {})
            iv_analysis = market_analysis.get('iv_analysis', {})
            atm_iv = iv_analysis.get('atm_iv', 0)
            
            if atm_iv < 15:  # Skip if IV too low for attractive premium
                logger.info("IV too low for Short Put premium collection")
                return {
                    'success': False,
                    'reason': 'IV too low for attractive premium collection'
                }
            
            if strike is None:
                if use_expected_moves and self.market_analysis and hasattr(self, 'strike_selector') and self.strike_selector:
                    # Use intelligent strike selection
                    logger.info("Using intelligent strike selection")
                    strike = self.strike_selector.select_optimal_strike(
                        self.options_df, self.spot_price, self.market_analysis,
                        'Short Put', 'PUT'
                    )
                else:
                    # Use OTM strike for better probability of keeping premium
                    logger.info(f"Using delta-based selection with target delta {target_delta}")
                    strike = self._find_optimal_strike(target_delta, 'PUT')
            
            logger.info(f"Selected strike: {strike}")
            
            if not self.validate_strikes([strike]):
                logger.warning(f"Strike validation failed for {strike}")
                return {'success': False, 'reason': 'Invalid strike selection'}
            
            # Get option data
            put_data = self._get_option_data(strike, 'PUT')
            if put_data is None:
                logger.warning(f"No option data available for strike {strike}")
                return {'success': False, 'reason': 'Option data not available'}
            
            logger.info(f"Found option data: Delta={put_data.get('delta', 0):.3f}, Premium={put_data.get('last_price', 0)}")
            
            # Construct leg
            self.legs = [{
                'option_type': 'PUT',
                'position': 'SHORT',
                'strike': strike,
                'premium': put_data.get('last_price', 0),
                'delta': put_data.get('delta', 0),
                'rationale': 'Premium collection on bullish/neutral outlook'
            }]
            
            # Calculate metrics
            risk_metrics = self.get_risk_metrics()
            greeks = self.get_greeks_summary()
            
            # Calculate probability of profit for short put
            # Short put profits if stock stays above strike at expiry
            put_delta = abs(put_data.get('delta', -0.30))
            
            # Probability of profit ≈ 1 - |delta| (probability stock stays above strike)
            probability_profit = max(0.45, min(0.85, 1.0 - put_delta))
            
            logger.info(f"Short Put PoP calculation: Delta={put_delta:.3f}, PoP={probability_profit:.3f}")
            
            strategy_data = {
                'success': True,
                'strategy_name': self.get_strategy_name(),
                'market_outlook': self.get_market_outlook(),
                'iv_preference': self.get_iv_preference(),
                'legs': self.legs,
                'risk_metrics': risk_metrics,
                'greeks': greeks,
                'probability_profit': probability_profit,
                'setup_cost': -put_data.get('last_price', 0),  # Negative because we receive premium
                'max_profit': put_data.get('last_price', 0),
                'max_loss': f"Strike - Premium = {strike - put_data.get('last_price', 0):.2f}",
                'breakeven': strike - put_data.get('last_price', 0),
                'expiry_date': self.options_df['expiry'].iloc[0] if not self.options_df.empty else None,
                'days_to_expiry': self._get_days_to_expiry(),
                'rationale': f"Short Put at strike {strike}: Premium collection in high IV environment, expecting stock to stay above {strike}"
            }
            
            return strategy_data
            
        except Exception as e:
            logger.error(f"Error constructing Short Put: {e}")
            return {'success': False, 'reason': f'Construction error: {str(e)}'}