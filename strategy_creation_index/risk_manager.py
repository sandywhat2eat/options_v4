"""
Risk Manager for position sizing and risk assessment
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, Optional, List, Tuple

logger = logging.getLogger(__name__)

class RiskManager:
    """Handles risk assessment and position sizing"""
    
    def __init__(self):
        self.liquidity_thresholds = {
            'min_oi': 100,
            'min_volume': 50,
            'max_spread_pct': 0.05,
            'min_liquidity_score': 0.4
        }
        
        self.risk_limits = {
            'max_position_size': 10000,  # Max position value
            'max_single_leg_delta': 0.5,  # Max delta exposure per leg
            'max_portfolio_delta': 2.0,   # Max total delta exposure
            'min_probability_profit': 0.45,  # Minimum PoP
            'max_loss_per_trade': 5000    # Max loss per trade
        }
    
    def assess_liquidity(self, options_df: pd.DataFrame, strikes: List[float]) -> Dict:
        """Assess liquidity for given strikes"""
        try:
            liquidity_scores = {}
            
            for strike in strikes:
                strike_data = options_df[options_df['strike'] == strike]
                if strike_data.empty:
                    liquidity_scores[strike] = 0.0
                    continue
                
                # Calculate liquidity score
                score = self._calculate_liquidity_score(strike_data.iloc[0])
                liquidity_scores[strike] = score
            
            avg_liquidity = np.mean(list(liquidity_scores.values()))
            min_liquidity = min(liquidity_scores.values())
            
            return {
                'individual_scores': liquidity_scores,
                'average_liquidity': avg_liquidity,
                'minimum_liquidity': min_liquidity,
                'passes_threshold': min_liquidity >= self.liquidity_thresholds['min_liquidity_score'],
                'quality_rating': self._get_liquidity_rating(avg_liquidity)
            }
            
        except Exception as e:
            logger.error(f"Error assessing liquidity: {e}")
            return {'passes_threshold': False, 'quality_rating': 'POOR'}
    
    def _calculate_liquidity_score(self, option_data: pd.Series) -> float:
        """Calculate liquidity score for single option"""
        try:
            # Open Interest component (40% weight)
            oi = option_data.get('open_interest', 0)
            oi_score = min(1.0, oi / 500) * 0.4  # Normalize to 500 as excellent
            
            # Volume component (30% weight)
            volume = option_data.get('volume', 0)
            volume_score = min(1.0, volume / 200) * 0.3  # Normalize to 200 as excellent
            
            # Bid-Ask Spread component (30% weight)
            bid = option_data.get('bid', 0)
            ask = option_data.get('ask', 0)
            
            if bid > 0 and ask > 0:
                mid_price = (bid + ask) / 2
                spread_pct = (ask - bid) / mid_price if mid_price > 0 else 1.0
                spread_score = max(0.0, 1.0 - (spread_pct / 0.1)) * 0.3  # 10% spread = 0 score
            else:
                spread_score = 0.0
            
            total_score = oi_score + volume_score + spread_score
            return min(1.0, total_score)
            
        except Exception as e:
            logger.error(f"Error calculating liquidity score: {e}")
            return 0.0
    
    def _get_liquidity_rating(self, score: float) -> str:
        """Convert liquidity score to rating"""
        if score >= 0.8:
            return 'EXCELLENT'
        elif score >= 0.6:
            return 'GOOD'
        elif score >= 0.4:
            return 'FAIR'
        elif score >= 0.2:
            return 'POOR'
        else:
            return 'VERY_POOR'
    
    def calculate_position_size(self, strategy_data: Dict, account_size: float = 100000,
                              risk_per_trade: float = 0.02) -> Dict:
        """Calculate appropriate position size"""
        try:
            max_loss = strategy_data.get('max_loss', 0)
            if max_loss <= 0:
                return {'position_size': 0, 'contracts': 0, 'reason': 'Invalid max loss'}
            
            # Risk-based position sizing
            max_risk_amount = account_size * risk_per_trade
            contracts_by_risk = int(max_risk_amount / max_loss)
            
            # Hard limit constraints
            contracts_by_limit = int(self.risk_limits['max_position_size'] / max_loss)
            
            # Take minimum
            recommended_contracts = min(contracts_by_risk, contracts_by_limit, 10)  # Max 10 contracts
            
            if recommended_contracts <= 0:
                return {'position_size': 0, 'contracts': 0, 'reason': 'Risk too high'}
            
            total_position_value = recommended_contracts * max_loss
            
            return {
                'contracts': recommended_contracts,
                'position_size': total_position_value,
                'risk_amount': total_position_value,
                'risk_percentage': (total_position_value / account_size) * 100,
                'sizing_method': 'risk_based'
            }
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return {'position_size': 0, 'contracts': 0, 'reason': f'Error: {e}'}
    
    def assess_strategy_risk(self, strategy_data: Dict) -> Dict:
        """Comprehensive risk assessment for strategy"""
        try:
            risk_factors = []
            risk_score = 0.0
            
            # Probability of Profit assessment
            pop = strategy_data.get('probability_profit', 0.0)
            if pop < 0.5:
                risk_factors.append(f"Low PoP: {pop:.2f}")
                risk_score += 0.3
            elif pop < 0.6:
                risk_score += 0.1
            
            # Delta exposure assessment
            total_delta = abs(strategy_data.get('delta_exposure', 0.0))
            if total_delta > 0.5:
                risk_factors.append(f"High delta exposure: {total_delta:.2f}")
                risk_score += 0.2
            
            # Max loss assessment
            max_loss = strategy_data.get('max_loss', 0)
            max_profit = strategy_data.get('max_profit', 0)
            
            if max_loss > 0 and max_profit > 0:
                risk_reward = max_profit / max_loss
                if risk_reward < 0.3:
                    risk_factors.append(f"Poor risk-reward: {risk_reward:.2f}")
                    risk_score += 0.2
            
            # Liquidity assessment
            liquidity_data = strategy_data.get('liquidity_assessment', {})
            if not liquidity_data.get('passes_threshold', True):
                risk_factors.append("Poor liquidity")
                risk_score += 0.3
            
            # Overall risk rating
            if risk_score <= 0.2:
                risk_rating = 'LOW'
            elif risk_score <= 0.5:
                risk_rating = 'MODERATE'
            elif risk_score <= 0.8:
                risk_rating = 'HIGH'
            else:
                risk_rating = 'EXTREME'
            
            return {
                'risk_score': risk_score,
                'risk_rating': risk_rating,
                'risk_factors': risk_factors,
                'recommended_action': self._get_risk_action(risk_rating),
                'passes_risk_check': risk_score <= 0.6
            }
            
        except Exception as e:
            logger.error(f"Error assessing strategy risk: {e}")
            return {'risk_rating': 'EXTREME', 'passes_risk_check': False}
    
    def _get_risk_action(self, risk_rating: str) -> str:
        """Get recommended action based on risk rating"""
        actions = {
            'LOW': 'PROCEED',
            'MODERATE': 'PROCEED_WITH_CAUTION',
            'HIGH': 'REDUCE_SIZE',
            'EXTREME': 'AVOID'
        }
        return actions.get(risk_rating, 'AVOID')
    
    def validate_strategy_limits(self, strategy_data: Dict) -> Dict:
        """Validate strategy against risk limits"""
        try:
            violations = []
            
            # Check delta limits
            delta_exposure = abs(strategy_data.get('delta_exposure', 0.0))
            if delta_exposure > self.risk_limits['max_single_leg_delta']:
                violations.append(f"Delta exposure {delta_exposure:.2f} > limit {self.risk_limits['max_single_leg_delta']}")
            
            # Check probability limits
            pop = strategy_data.get('probability_profit', 0.0)
            if pop < self.risk_limits['min_probability_profit']:
                violations.append(f"PoP {pop:.2f} < minimum {self.risk_limits['min_probability_profit']}")
            
            # Check loss limits
            max_loss = strategy_data.get('max_loss', 0)
            if max_loss > self.risk_limits['max_loss_per_trade']:
                violations.append(f"Max loss {max_loss} > limit {self.risk_limits['max_loss_per_trade']}")
            
            return {
                'passes_limits': len(violations) == 0,
                'violations': violations,
                'total_violations': len(violations)
            }
            
        except Exception as e:
            logger.error(f"Error validating strategy limits: {e}")
            return {'passes_limits': False, 'violations': [f'Error: {e}']}
    
    def get_exit_conditions(self, strategy_data: Dict) -> Dict:
        """Generate exit conditions based on strategy and risk parameters"""
        try:
            strategy_name = strategy_data.get('name', '')
            max_profit = strategy_data.get('max_profit', 0)
            max_loss = strategy_data.get('max_loss', 0)
            
            # Standard exit conditions
            profit_target_pct = 0.5  # Take profit at 50% of max profit
            stop_loss_pct = 0.5      # Stop loss at 50% of max loss
            
            # Adjust based on strategy type
            if 'Spread' in strategy_name:
                profit_target_pct = 0.5
                stop_loss_pct = 0.5
            elif 'Iron Condor' in strategy_name:
                profit_target_pct = 0.4
                stop_loss_pct = 0.5
            elif 'Long' in strategy_name:
                profit_target_pct = 1.0  # Let profits run
                stop_loss_pct = 0.3      # Tight stop loss
            
            return {
                'profit_target': max_profit * profit_target_pct,
                'stop_loss': max_loss * stop_loss_pct,
                'time_exit': 'Close at 50% time decay or 5 DTE',
                'adjustment_trigger': max_loss * 0.3,
                'early_exit_conditions': [
                    'Volatility expansion > 20%',
                    'Significant news announcement',
                    'Technical level breach'
                ]
            }
            
        except Exception as e:
            logger.error(f"Error generating exit conditions: {e}")
            return {'profit_target': 0, 'stop_loss': 0}