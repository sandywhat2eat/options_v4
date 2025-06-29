"""
Probability Engine for delta-based probability calculations
"""

import numpy as np
import pandas as pd
import logging
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

class ProbabilityEngine:
    """
    Calculate probabilities of profit using delta-based approximations
    
    Uses Black-Scholes delta as probability proxy since delta ≈ probability of finishing ITM
    """
    
    def __init__(self):
        self.minimum_probability_thresholds = {
            'conservative': 0.40,  # 40% minimum PoP - balanced threshold
            'moderate': 0.35,      # 35% minimum PoP - raised from 25% to prevent low-quality strategies
            'aggressive': 0.30,    # 30% minimum PoP - raised from 20%
            'speculative': 0.25    # 25% minimum PoP - raised from 15%
        }
    
    def calculate_single_leg_probability(self, delta: float, option_type: str, 
                                       position: str) -> float:
        """
        Calculate probability of profit for single option position
        
        Args:
            delta: Option delta
            option_type: 'CALL' or 'PUT'
            position: 'LONG' or 'SHORT'
        """
        try:
            # Delta approximates probability of finishing ITM
            # For probability of profit, we need to consider position type
            
            if option_type.upper() == 'CALL':
                prob_itm = abs(delta)
            else:  # PUT
                prob_itm = abs(delta)
            
            if position.upper() == 'LONG':
                # Long options need to finish ITM + overcome premium
                # More realistic estimate: reduce probability by 5-8%
                prob_profit = max(0.0, prob_itm - 0.06)
            else:  # SHORT
                # Short options profit if option expires OTM
                prob_profit = 1.0 - prob_itm
            
            return min(1.0, max(0.0, prob_profit))
            
        except Exception as e:
            logger.error(f"Error calculating single leg probability: {e}")
            return 0.5  # Default 50% if calculation fails
    
    def calculate_spread_probability(self, short_delta: float, long_delta: float,
                                   option_type: str, spread_type: str) -> float:
        """
        Calculate probability of profit for spread strategies
        
        Args:
            short_delta: Delta of short option
            long_delta: Delta of long option  
            option_type: 'CALL' or 'PUT'
            spread_type: 'CREDIT' or 'DEBIT'
        """
        try:
            if spread_type.upper() == 'CREDIT':
                # Credit spreads profit when short option expires OTM
                if option_type.upper() == 'CALL':
                    # Bear call spread - profit when price stays below short strike
                    prob_profit = 1.0 - abs(short_delta)
                else:  # PUT
                    # Bull put spread - profit when price stays above short strike
                    prob_profit = abs(short_delta)
            else:  # DEBIT
                # Debit spreads need price movement in favorable direction
                if option_type.upper() == 'CALL':
                    # Bull call spread - need price above short strike
                    prob_profit = abs(short_delta)
                else:  # PUT
                    # Bear put spread - need price below short strike
                    prob_profit = 1.0 - abs(short_delta)
            
            return min(1.0, max(0.0, prob_profit))
            
        except Exception as e:
            logger.error(f"Error calculating spread probability: {e}")
            return 0.5
    
    def calculate_iron_condor_probability(self, call_short_delta: float, 
                                        put_short_delta: float, 
                                        call_long_delta: float,
                                        put_long_delta: float) -> float:
        """Calculate probability of profit for Iron Condor"""
        try:
            # Iron Condor profits when price stays between short strikes
            # Probability = 1 - (prob above call strike + prob below put strike)
            
            prob_above_call = abs(call_short_delta)
            prob_below_put = 1.0 - abs(put_short_delta)
            
            # Probability of staying in profit zone
            prob_profit = 1.0 - (prob_above_call + prob_below_put)
            
            # Conservative adjustment for early assignment risk
            prob_profit *= 0.9
            
            return min(1.0, max(0.0, prob_profit))
            
        except Exception as e:
            logger.error(f"Error calculating Iron Condor probability: {e}")
            return 0.5
    
    def calculate_straddle_probability(self, atm_delta: float, iv: float, 
                                     days_to_expiry: int, position: str) -> float:
        """Calculate probability for straddle/strangle strategies"""
        try:
            if position.upper() == 'LONG':
                # Long straddle needs significant price movement
                # Use IV to estimate movement probability
                expected_move_pct = iv * np.sqrt(days_to_expiry / 365) / 100
                
                # Rough approximation: need move > 1 standard deviation
                prob_profit = min(0.7, expected_move_pct * 2.5)
                
            else:  # SHORT
                # Short straddle profits from low movement
                expected_move_pct = iv * np.sqrt(days_to_expiry / 365) / 100
                prob_profit = max(0.3, 1.0 - (expected_move_pct * 2.0))
            
            return min(1.0, max(0.0, prob_profit))
            
        except Exception as e:
            logger.error(f"Error calculating straddle probability: {e}")
            return 0.4
    
    def filter_strategies_by_probability(self, strategy_scores: Dict, 
                                       risk_tolerance: str = 'moderate') -> Dict:
        """Filter strategies based on minimum probability threshold"""
        try:
            min_prob = self.minimum_probability_thresholds.get(risk_tolerance, 0.55)
            
            filtered_strategies = {}
            for strategy_name, strategy_data in strategy_scores.items():
                if isinstance(strategy_data, dict):
                    prob_profit = strategy_data.get('probability_profit', 0.0)
                    if prob_profit >= min_prob:
                        filtered_strategies[strategy_name] = strategy_data
                    else:
                        logger.info(f"Filtered out {strategy_name}: PoP {prob_profit:.2f} < {min_prob:.2f}")
            
            return filtered_strategies
            
        except Exception as e:
            logger.error(f"Error filtering strategies by probability: {e}")
            return strategy_scores
    
    def rank_by_risk_adjusted_probability(self, strategy_scores: Dict) -> Dict:
        """Rank strategies by risk-adjusted probability score"""
        try:
            ranked_strategies = {}
            
            for strategy_name, strategy_data in strategy_scores.items():
                if not isinstance(strategy_data, dict):
                    continue
                
                prob_profit = strategy_data.get('probability_profit', 0.0)
                max_loss = strategy_data.get('max_loss', 1.0)
                max_profit = strategy_data.get('max_profit', 0.0)
                
                # Risk-adjusted score = PoP * (Max Profit / Max Loss)
                risk_reward = max_profit / max_loss if max_loss > 0 else 0.0
                risk_adjusted_score = prob_profit * (1 + risk_reward)
                
                strategy_data['risk_adjusted_score'] = risk_adjusted_score
                ranked_strategies[strategy_name] = strategy_data
            
            # Sort by risk-adjusted score
            return dict(sorted(ranked_strategies.items(), 
                             key=lambda x: x[1].get('risk_adjusted_score', 0), 
                             reverse=True))
            
        except Exception as e:
            logger.error(f"Error ranking by risk-adjusted probability: {e}")
            return strategy_scores
    
    def get_probability_summary(self, strategy_scores: Dict) -> Dict:
        """Generate probability analysis summary"""
        try:
            if not strategy_scores:
                return {'total_strategies': 0, 'avg_probability': 0.0}
            
            probabilities = []
            high_prob_count = 0
            
            for strategy_data in strategy_scores.values():
                if isinstance(strategy_data, dict):
                    prob = strategy_data.get('probability_profit', 0.0)
                    probabilities.append(prob)
                    if prob >= 0.6:
                        high_prob_count += 1
            
            return {
                'total_strategies': len(probabilities),
                'avg_probability': np.mean(probabilities) if probabilities else 0.0,
                'high_probability_count': high_prob_count,
                'probability_range': (min(probabilities), max(probabilities)) if probabilities else (0, 0),
                'strategies_above_60pct': high_prob_count
            }
            
        except Exception as e:
            logger.error(f"Error generating probability summary: {e}")
            return {'total_strategies': 0, 'avg_probability': 0.0}
    
    def validate_probability_calculation(self, delta: float, calculated_prob: float) -> bool:
        """Validate that probability calculation is reasonable"""
        try:
            # Basic sanity checks
            if not (0.0 <= calculated_prob <= 1.0):
                return False
            
            # Delta should correlate with probability
            if abs(delta) > 0.8 and calculated_prob < 0.3:
                return False
            
            if abs(delta) < 0.2 and calculated_prob > 0.8:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating probability: {e}")
            return False
    
    def calculate_market_aware_probability(self, delta: float, option_type: str, 
                                         position: str, iv: float = None, 
                                         days_to_expiry: int = None,
                                         premium_pct_of_strike: float = None,
                                         iv_percentile: float = None) -> float:
        """
        Calculate probability with market context awareness
        
        Args:
            delta: Option delta
            option_type: 'CALL' or 'PUT'
            position: 'LONG' or 'SHORT'
            iv: Implied volatility (as percentage)
            days_to_expiry: Days until expiration
            premium_pct_of_strike: Premium as percentage of strike price
            iv_percentile: Current IV percentile (0-100)
        
        Returns:
            Market-aware probability of profit
        """
        try:
            # Base probability from delta
            base_prob = abs(delta)
            
            # Position adjustments
            if position.upper() == 'LONG':
                # Long options need to overcome premium
                
                # Premium adjustment (more sophisticated than fixed 0.06)
                if premium_pct_of_strike is not None:
                    # Higher premium = lower probability
                    # Cap adjustment at 15%
                    premium_adjustment = min(0.15, premium_pct_of_strike / 100 * 0.8)
                else:
                    # Default fallback
                    premium_adjustment = 0.06
                
                # IV rank adjustment
                iv_bonus = 0.0
                if iv_percentile is not None:
                    if iv_percentile < 30:  # Low IV - good for long options
                        iv_bonus = 0.05
                    elif iv_percentile > 70:  # High IV - bad for long options
                        iv_bonus = -0.05
                
                # Time decay penalty
                time_penalty = 0.02  # Default
                if days_to_expiry is not None:
                    if days_to_expiry < 7:
                        time_penalty = 0.08
                    elif days_to_expiry < 14:
                        time_penalty = 0.04
                    elif days_to_expiry > 45:
                        time_penalty = 0.01
                
                # Calculate final probability
                prob_profit = base_prob - premium_adjustment + iv_bonus - time_penalty
                
                logger.debug(f"Long option PoP: base={base_prob:.3f}, "
                           f"prem_adj=-{premium_adjustment:.3f}, "
                           f"iv_bonus={iv_bonus:.3f}, "
                           f"time_pen=-{time_penalty:.3f}, "
                           f"final={prob_profit:.3f}")
                
            else:  # SHORT position
                # Short options profit from OTM expiration
                
                # Base probability is inverse of ITM probability
                prob_profit = 1.0 - base_prob
                
                # IV rank adjustment (opposite of long)
                if iv_percentile is not None:
                    if iv_percentile > 70:  # High IV - good for short options
                        prob_profit += 0.03
                    elif iv_percentile < 30:  # Low IV - bad for short options
                        prob_profit -= 0.03
                
                # Time bonus for short positions
                if days_to_expiry is not None and days_to_expiry < 21:
                    prob_profit += 0.02  # Theta acceleration helps
            
            # Ensure probability stays within bounds
            return max(0.1, min(0.9, prob_profit))
            
        except Exception as e:
            logger.error(f"Error in market-aware probability calculation: {e}")
            # Fallback to simple delta-based calculation
            if position.upper() == 'LONG':
                return max(0.0, abs(delta) - 0.06)
            else:
                return 1.0 - abs(delta)