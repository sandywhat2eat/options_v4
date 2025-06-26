"""
Position Sizer Module
Calculates position sizes based on premium at risk
"""

import logging
from typing import Dict, Optional, List
from dataclasses import dataclass
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class PositionSize:
    """Position sizing details"""
    symbol: str
    strategy_name: str
    allocated_capital: float
    premium_at_risk: float
    number_of_lots: int
    lot_size: int
    max_loss_per_lot: float
    position_value: float  # Total premium invested
    risk_percentage: float  # % of allocated capital at risk
    kelly_fraction: float
    


class PositionSizer:
    """Calculates position sizes based on premium risk"""
    
    # Maximum risk limits
    MAX_RISK_PER_POSITION = 0.03  # 3% of total capital
    MAX_RISK_PER_INDUSTRY = 0.05  # 5% of total capital
    
    def __init__(self):
        self.industry_exposure = {}
        
    def calculate_position_size(self, 
                              strategy: Dict,
                              allocated_capital: float,
                              total_portfolio: float,
                              industry_rating: str) -> PositionSize:
        """Calculate position size based on premium at risk"""
        try:
            symbol = strategy.get('symbol', '')
            strategy_name = strategy.get('strategy_name', '')
            max_loss = abs(strategy.get('max_loss', 0))
            max_profit = strategy.get('max_profit', 0)
            probability = strategy.get('probability_of_profit', 0.5)
            lot_size = strategy.get('lot_size', 50)  # NFO default
            
            # Calculate Kelly fraction
            kelly_fraction = self._calculate_kelly_fraction(
                probability, max_profit, max_loss
            )
            
            # Get risk multiplier based on industry rating
            risk_multiplier = self._get_risk_multiplier(industry_rating)
            
            # Calculate base position size
            base_risk_amount = allocated_capital * self.MAX_RISK_PER_POSITION
            adjusted_risk_amount = base_risk_amount * risk_multiplier * kelly_fraction
            
            # Calculate number of lots
            if max_loss > 0:
                max_lots = int(adjusted_risk_amount / max_loss)
            else:
                max_lots = 1
                
            # Apply position limits
            position_limits = self._get_position_limits(strategy_name)
            number_of_lots = min(max_lots, position_limits['max_lots'])
            number_of_lots = max(number_of_lots, position_limits['min_lots'])
            
            # Calculate actual values
            premium_at_risk = number_of_lots * max_loss
            position_value = self._calculate_position_value(strategy, number_of_lots)
            risk_percentage = (premium_at_risk / allocated_capital) * 100
            
            return PositionSize(
                symbol=symbol,
                strategy_name=strategy_name,
                allocated_capital=allocated_capital,
                premium_at_risk=premium_at_risk,
                number_of_lots=number_of_lots,
                lot_size=lot_size,
                max_loss_per_lot=max_loss,
                position_value=position_value,
                risk_percentage=risk_percentage,
                kelly_fraction=kelly_fraction
            )
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            # Return minimal position
            return PositionSize(
                symbol=strategy.get('symbol', ''),
                strategy_name=strategy.get('strategy_name', ''),
                allocated_capital=allocated_capital,
                premium_at_risk=0,
                number_of_lots=1,
                lot_size=50,
                max_loss_per_lot=0,
                position_value=0,
                risk_percentage=0,
                kelly_fraction=0
            )
    
    def _calculate_kelly_fraction(self, probability: float, 
                                max_profit: float, max_loss: float) -> float:
        """Calculate Kelly fraction for position sizing"""
        if max_loss == 0:
            return 0.25  # Default conservative fraction
            
        # Kelly formula: f = (p*b - q) / b
        # where p = probability of profit, q = 1-p, b = profit/loss ratio
        p = probability
        q = 1 - p
        b = max_profit / max_loss if max_loss > 0 else 1
        
        kelly = (p * b - q) / b if b > 0 else 0
        
        # Apply Kelly fraction limits (quarter Kelly for safety)
        kelly = max(0, kelly)  # No negative positions
        kelly = min(kelly, 0.25)  # Max 25% Kelly
        
        return kelly
    
    def _get_risk_multiplier(self, industry_rating: str) -> float:
        """Get risk multiplier based on industry rating"""
        multipliers = {
            'strong_overweight': 1.2,
            'moderate_overweight': 1.0,
            'moderate_underweight': 0.9,
            'strong_underweight': 1.1  # Slightly higher for shorts
        }
        
        return multipliers.get(industry_rating, 1.0)
    
    def _get_position_limits(self, strategy_name: str) -> Dict:
        """Get position limits by strategy type"""
        # Conservative limits by strategy type
        limits = {
            'Long Call': {'min_lots': 1, 'max_lots': 10},
            'Long Put': {'min_lots': 1, 'max_lots': 10},
            'Bull Call Spread': {'min_lots': 2, 'max_lots': 20},
            'Bear Put Spread': {'min_lots': 2, 'max_lots': 20},
            'Iron Condor': {'min_lots': 2, 'max_lots': 10},
            'Butterfly Spread': {'min_lots': 2, 'max_lots': 15},
            'Calendar Spread': {'min_lots': 2, 'max_lots': 15},
            'Cash-Secured Put': {'min_lots': 1, 'max_lots': 5},
            'Covered Call': {'min_lots': 1, 'max_lots': 5},
            'Straddle': {'min_lots': 1, 'max_lots': 8},
            'Strangle': {'min_lots': 1, 'max_lots': 8}
        }
        
        return limits.get(strategy_name, {'min_lots': 1, 'max_lots': 10})
    
    def _calculate_position_value(self, strategy: Dict, number_of_lots: int) -> float:
        """Calculate total position value (premium invested)"""
        # This varies by strategy type
        strategy_name = strategy.get('strategy_name', '')
        
        if strategy_name in ['Long Call', 'Long Put']:
            # Single leg long options
            premium = strategy.get('entry_premium', 0)
            lot_size = strategy.get('lot_size', 50)
            return premium * lot_size * number_of_lots
            
        elif strategy_name in ['Bull Call Spread', 'Bear Put Spread']:
            # Debit spreads
            net_debit = abs(strategy.get('net_debit', 0))
            return net_debit * number_of_lots
            
        elif strategy_name in ['Iron Condor', 'Strangle']:
            # Credit strategies - use margin requirement
            margin_req = strategy.get('margin_requirement', 0)
            return margin_req * number_of_lots
            
        else:
            # Default to max loss as position value
            return abs(strategy.get('max_loss', 0)) * number_of_lots
    
    def validate_industry_exposure(self, positions: List[PositionSize], 
                                 industry: str, total_capital: float) -> bool:
        """Check if adding position would exceed industry limits"""
        current_exposure = sum(
            p.premium_at_risk for p in positions
            if p.symbol in self._get_industry_symbols(industry)
        )
        
        return current_exposure < (total_capital * self.MAX_RISK_PER_INDUSTRY)
    
    def _get_industry_symbols(self, industry: str) -> List[str]:
        """Get symbols belonging to an industry (placeholder)"""
        # This would connect to actual industry mapping
        return []
    
    def get_portfolio_summary(self, positions: List[PositionSize]) -> Dict:
        """Get portfolio risk summary"""
        total_premium_at_risk = sum(p.premium_at_risk for p in positions)
        total_position_value = sum(p.position_value for p in positions)
        
        strategy_breakdown = {}
        for position in positions:
            if position.strategy_name not in strategy_breakdown:
                strategy_breakdown[position.strategy_name] = {
                    'count': 0,
                    'premium_at_risk': 0,
                    'position_value': 0
                }
            
            strategy_breakdown[position.strategy_name]['count'] += 1
            strategy_breakdown[position.strategy_name]['premium_at_risk'] += position.premium_at_risk
            strategy_breakdown[position.strategy_name]['position_value'] += position.position_value
        
        return {
            'total_positions': len(positions),
            'total_premium_at_risk': total_premium_at_risk,
            'total_position_value': total_position_value,
            'average_risk_per_position': total_premium_at_risk / len(positions) if positions else 0,
            'strategy_breakdown': strategy_breakdown
        }