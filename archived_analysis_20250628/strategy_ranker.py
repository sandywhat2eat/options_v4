"""
Strategy Ranker with probability-based filtering and multi-factor scoring
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Tuple, Optional
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strategy_creation import ProbabilityEngine, IVAnalyzer, RiskManager

logger = logging.getLogger(__name__)

class StrategyRanker:
    """
    Ranks and filters strategies based on multiple factors including probability
    """
    
    def __init__(self):
        self.probability_engine = ProbabilityEngine()
        self.iv_analyzer = IVAnalyzer()
        self.risk_manager = RiskManager()
        
        # Scoring weights for different factors
        self.scoring_weights = {
            'probability_profit': 0.35,    # Highest weight to PoP
            'risk_reward_ratio': 0.25,     # Risk-reward importance
            'direction_alignment': 0.20,   # Market direction fit
            'iv_compatibility': 0.15,      # IV environment fit
            'liquidity_score': 0.05        # Basic liquidity weight
        }
    
    def rank_strategies(self, strategies: Dict, market_analysis: Dict, 
                       risk_tolerance: str = 'moderate') -> List[Tuple[str, Dict]]:
        """
        Rank strategies with comprehensive scoring and probability filtering
        
        Args:
            strategies: Dictionary of constructed strategies
            market_analysis: Market direction and IV analysis
            risk_tolerance: Risk tolerance level for filtering
        
        Returns:
            List of (strategy_name, strategy_data) tuples ranked by score
        """
        try:
            logger.info(f"Ranking {len(strategies)} strategies with probability filtering...")
            
            scored_strategies = {}
            
            for strategy_name, strategy_data in strategies.items():
                if not strategy_data.get('success', False):
                    logger.debug(f"Skipping failed strategy: {strategy_name}")
                    continue
                
                # Calculate comprehensive score
                score_data = self._calculate_strategy_score(
                    strategy_name, strategy_data, market_analysis
                )
                
                if score_data['total_score'] > 0:
                    scored_strategies[strategy_name] = {
                        **strategy_data,
                        **score_data
                    }
            
            # Apply probability-based filtering
            filtered_strategies = self.probability_engine.filter_strategies_by_probability(
                scored_strategies, risk_tolerance
            )
            
            # Apply risk management filters
            risk_filtered_strategies = self._apply_risk_filters(filtered_strategies)
            
            # Sort by total score
            ranked_strategies = sorted(
                risk_filtered_strategies.items(),
                key=lambda x: x[1].get('total_score', 0),
                reverse=True
            )
            
            logger.info(f"Final ranking: {len(ranked_strategies)} strategies passed all filters")
            
            return ranked_strategies
            
        except Exception as e:
            logger.error(f"Error ranking strategies: {e}")
            return []
    
    def _calculate_strategy_score(self, strategy_name: str, strategy_data: Dict, 
                                market_analysis: Dict) -> Dict:
        """Calculate comprehensive score for a strategy"""
        try:
            # 1. Calculate Probability of Profit
            probability_profit = self._calculate_probability_of_profit(
                strategy_name, strategy_data
            )
            
            # Also use metadata scoring if available
            try:
                from strategies.strategy_metadata import get_strategy_metadata, calculate_strategy_score
                metadata = get_strategy_metadata(strategy_name)
                if metadata:
                    metadata_score = calculate_strategy_score(metadata, market_analysis)
                else:
                    metadata_score = 0.5
            except ImportError:
                metadata_score = 0.5
            
            # 2. Calculate Risk-Reward Ratio
            risk_reward_ratio = self._calculate_risk_reward_score(strategy_data)
            
            # 3. Calculate Direction Alignment
            direction_alignment = self._calculate_direction_alignment(
                strategy_data, market_analysis
            )
            
            # 4. Calculate IV Compatibility  
            iv_compatibility = self._calculate_iv_compatibility(
                strategy_data, market_analysis
            )
            
            # 5. Basic liquidity score (placeholder - can be enhanced)
            liquidity_score = 0.8  # Default good liquidity
            
            # Calculate weighted total score
            total_score = (
                probability_profit * self.scoring_weights['probability_profit'] +
                risk_reward_ratio * self.scoring_weights['risk_reward_ratio'] +
                direction_alignment * self.scoring_weights['direction_alignment'] +
                iv_compatibility * self.scoring_weights['iv_compatibility'] +
                liquidity_score * self.scoring_weights['liquidity_score']
            )
            
            # Add metadata score as a bonus (up to 10% boost)
            total_score = total_score * (1 + metadata_score * 0.1)
            
            return {
                'probability_profit': probability_profit,
                'risk_reward_ratio': risk_reward_ratio,
                'direction_alignment': direction_alignment,
                'iv_compatibility': iv_compatibility,
                'liquidity_score': liquidity_score,
                'total_score': total_score,
                'component_scores': {
                    'probability': probability_profit,
                    'risk_reward': risk_reward_ratio,
                    'direction': direction_alignment,
                    'iv_fit': iv_compatibility,
                    'liquidity': liquidity_score
                }
            }
            
        except Exception as e:
            logger.error(f"Error calculating strategy score for {strategy_name}: {e}")
            return {'total_score': 0.0, 'probability_profit': 0.0}
    
    def _calculate_probability_of_profit(self, strategy_name: str, strategy_data: Dict) -> float:
        """Calculate probability of profit based on strategy type and Greeks"""
        try:
            legs = strategy_data.get('legs', [])
            if not legs:
                return 0.0
            
            # Strategy-specific probability calculations
            if 'Long Call' in strategy_name:
                return self._calculate_long_option_probability(legs[0], 'CALL')
            
            elif 'Long Put' in strategy_name:
                return self._calculate_long_option_probability(legs[0], 'PUT')
            
            elif 'Bull Call Spread' in strategy_name or 'Bear Put Spread' in strategy_name:
                return self._calculate_debit_spread_probability(legs)
            
            elif 'Bear Call Spread' in strategy_name or 'Bull Put Spread' in strategy_name:
                return self._calculate_credit_spread_probability(legs)
            
            elif 'Iron Condor' in strategy_name:
                return self._calculate_iron_condor_probability(legs)
            
            elif 'Straddle' in strategy_name:
                return self._calculate_straddle_probability(strategy_name, legs)
            
            else:
                # Default calculation for other strategies
                return self._calculate_default_probability(legs)
            
        except Exception as e:
            logger.error(f"Error calculating PoP for {strategy_name}: {e}")
            return 0.0
    
    def _calculate_long_option_probability(self, leg: Dict, option_type: str) -> float:
        """Calculate PoP for long options"""
        try:
            delta = abs(leg.get('delta', 0))
            # Long options need to overcome premium + be ITM
            # Less conservative estimate: delta * 0.92 (8% haircut for premium)
            base_prob = min(0.92, delta * 0.92)
            
            # Add momentum boost if available from market analysis
            # This would be passed through strategy_data in future enhancement
            # For now, use base probability
            
            return base_prob
        except:
            return 0.45
    
    def _calculate_credit_spread_probability(self, legs: List[Dict]) -> float:
        """Calculate PoP for credit spreads"""
        try:
            # Find short leg (premium collected)
            short_leg = next((leg for leg in legs if leg['position'] == 'SHORT'), None)
            if short_leg is None:
                return 0.5
            
            delta = abs(short_leg.get('delta', 0))
            
            # Credit spreads profit when short option expires OTM
            if short_leg['option_type'] == 'CALL':
                # Bear call spread - profit when price stays below short strike
                return 1.0 - delta
            else:  # PUT
                # Bull put spread - profit when price stays above short strike  
                return delta
            
        except Exception as e:
            logger.error(f"Error calculating credit spread PoP: {e}")
            return 0.5
    
    def _calculate_debit_spread_probability(self, legs: List[Dict]) -> float:
        """Calculate PoP for debit spreads"""
        try:
            # Find long leg (premium paid)
            long_leg = next((leg for leg in legs if leg['position'] == 'LONG'), None)
            if long_leg is None:
                return 0.5
            
            delta = abs(long_leg.get('delta', 0))
            
            # Debit spreads need favorable price movement
            # Conservative estimate with premium consideration
            return min(0.7, delta * 0.8)
            
        except Exception as e:
            logger.error(f"Error calculating debit spread PoP: {e}")
            return 0.4
    
    def _calculate_iron_condor_probability(self, legs: List[Dict]) -> float:
        """Calculate PoP for Iron Condor"""
        try:
            # Find short strikes
            call_short = next((leg for leg in legs 
                             if leg['option_type'] == 'CALL' and leg['position'] == 'SHORT'), None)
            put_short = next((leg for leg in legs 
                            if leg['option_type'] == 'PUT' and leg['position'] == 'SHORT'), None)
            
            if call_short is None or put_short is None:
                return 0.5
            
            call_delta = abs(call_short.get('delta', 0))
            put_delta = abs(put_short.get('delta', 0))
            
            # Probability of staying between short strikes
            prob_below_call = 1.0 - call_delta
            prob_above_put = put_delta
            
            # Rough estimate: probability of staying in profit zone
            return min(0.8, prob_below_call * prob_above_put * 2.5)
            
        except Exception as e:
            logger.error(f"Error calculating Iron Condor PoP: {e}")
            return 0.5
    
    def _calculate_straddle_probability(self, strategy_name: str, legs: List[Dict]) -> float:
        """Calculate PoP for straddle strategies"""
        try:
            if 'Long' in strategy_name:
                # Long straddle needs big move - conservative estimate
                return 0.35  # Historically challenging
            else:  # Short straddle
                # Short straddle profits from low movement - but risky
                return 0.65  # Higher PoP but unlimited risk
        except:
            return 0.4
    
    def _calculate_default_probability(self, legs: List[Dict]) -> float:
        """Default probability calculation for unspecified strategies"""
        try:
            if not legs:
                return 0.0
            
            # Simple average of leg deltas with position adjustment
            total_delta = 0.0
            for leg in legs:
                delta = leg.get('delta', 0)
                multiplier = 1 if leg['position'] == 'LONG' else -1
                total_delta += delta * multiplier
            
            # Convert to probability estimate
            prob = 0.5 + (total_delta * 0.3)  # Rough conversion
            return max(0.2, min(0.8, prob))
            
        except Exception as e:
            logger.error(f"Error calculating default probability: {e}")
            return 0.4
    
    def _calculate_risk_reward_score(self, strategy_data: Dict) -> float:
        """Calculate risk-reward score"""
        try:
            max_profit = strategy_data.get('max_profit', 0)
            max_loss = strategy_data.get('max_loss', 1)
            
            if max_loss <= 0:
                return 0.0
            
            if max_profit == float('inf'):
                # Unlimited profit potential gets high score
                return 1.0
            
            risk_reward_ratio = max_profit / max_loss
            
            # Convert to 0-1 score (cap at 3:1 ratio)
            return min(1.0, risk_reward_ratio / 3.0)
            
        except Exception as e:
            logger.error(f"Error calculating risk-reward score: {e}")
            return 0.0
    
    def _calculate_direction_alignment(self, strategy_data: Dict, market_analysis: Dict) -> float:
        """Calculate how well strategy aligns with market direction"""
        try:
            strategy_name = strategy_data.get('strategy_name', '')
            market_direction = market_analysis.get('direction', 'neutral').lower()
            confidence = market_analysis.get('confidence', 0.5)
            
            # Strategy direction mapping
            bullish_strategies = ['bull', 'long call']
            bearish_strategies = ['bear', 'long put']
            neutral_strategies = ['iron condor', 'straddle', 'strangle', 'butterfly']
            
            strategy_lower = strategy_name.lower()
            
            alignment_score = 0.5  # Default neutral alignment
            
            if market_direction == 'bullish':
                if any(keyword in strategy_lower for keyword in bullish_strategies):
                    alignment_score = 0.9
                elif any(keyword in strategy_lower for keyword in bearish_strategies):
                    alignment_score = 0.1
                else:
                    alignment_score = 0.6  # Neutral strategies
            
            elif market_direction == 'bearish':
                if any(keyword in strategy_lower for keyword in bearish_strategies):
                    alignment_score = 0.9
                elif any(keyword in strategy_lower for keyword in bullish_strategies):
                    alignment_score = 0.1
                else:
                    alignment_score = 0.6
            
            else:  # neutral market
                if any(keyword in strategy_lower for keyword in neutral_strategies):
                    alignment_score = 0.9
                else:
                    alignment_score = 0.5
            
            # Weight by market confidence
            final_score = alignment_score * confidence + 0.5 * (1 - confidence)
            
            return final_score
            
        except Exception as e:
            logger.error(f"Error calculating direction alignment: {e}")
            return 0.5
    
    def _calculate_iv_compatibility(self, strategy_data: Dict, market_analysis: Dict) -> float:
        """Calculate IV environment compatibility"""
        try:
            strategy_name = strategy_data.get('strategy_name', '')
            iv_analysis = market_analysis.get('iv_analysis', {})
            iv_environment = iv_analysis.get('iv_environment', 'NORMAL')
            
            strategy_lower = strategy_name.lower()
            
            # IV preference mapping
            if iv_environment == 'HIGH' or iv_environment == 'EXTREME':
                # High IV favors premium selling strategies
                if any(keyword in strategy_lower for keyword in ['iron condor', 'credit', 'short']):
                    return 0.9
                elif 'long' in strategy_lower:
                    return 0.3
                else:
                    return 0.6
            
            elif iv_environment == 'LOW':
                # Low IV favors premium buying strategies
                if 'long' in strategy_lower or 'straddle' in strategy_lower:
                    return 0.9
                elif any(keyword in strategy_lower for keyword in ['iron condor', 'short']):
                    return 0.3
                else:
                    return 0.6
            
            else:  # NORMAL IV
                return 0.7  # Most strategies work reasonably in normal IV
            
        except Exception as e:
            logger.error(f"Error calculating IV compatibility: {e}")
            return 0.5
    
    def _apply_risk_filters(self, strategies: Dict) -> Dict:
        """Apply risk management filters"""
        try:
            filtered_strategies = {}
            
            for strategy_name, strategy_data in strategies.items():
                # Basic risk assessment
                risk_assessment = self.risk_manager.assess_strategy_risk(strategy_data)
                
                if risk_assessment.get('passes_risk_check', False):
                    strategy_data['risk_assessment'] = risk_assessment
                    filtered_strategies[strategy_name] = strategy_data
                else:
                    logger.info(f"Strategy {strategy_name} filtered out by risk management")
            
            return filtered_strategies
            
        except Exception as e:
            logger.error(f"Error applying risk filters: {e}")
            return strategies