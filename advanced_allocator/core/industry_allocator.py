"""
Industry Allocator Module
Manages industry allocations from database and filters symbols based on ratings
"""

import logging
from typing import Dict, List, Tuple
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class IndustryAllocation:
    """Industry allocation details"""
    industry: str
    position_type: str  # LONG or SHORT
    weight_percentage: float
    rating: str  # strong_overweight, moderate_overweight, etc.
    symbols: List[str]
    updated_at: datetime


class IndustryAllocator:
    """Manages industry allocations and symbol selection"""
    
    def __init__(self, supabase_client):
        self.supabase = supabase_client
        self._cache = {}
        
    def get_industry_allocations(self) -> Tuple[List[IndustryAllocation], List[IndustryAllocation]]:
        """Get current industry allocations split by LONG and SHORT"""
        try:
            # Query industry allocations
            response = self.supabase.table('industry_allocations_current').select('*').execute()
            
            if not response.data:
                logger.warning("No industry allocations found")
                return [], []
            
            long_allocations = []
            short_allocations = []
            
            for row in response.data:
                allocation = IndustryAllocation(
                    industry=row['industry'],
                    position_type=row['position_type'],
                    weight_percentage=row['weight_percentage'],
                    rating=row['rating'],
                    symbols=row.get('symbols', []),
                    updated_at=datetime.fromisoformat(row['last_updated']) if row.get('last_updated') else datetime.now()
                )
                
                if row['position_type'] == 'LONG':
                    long_allocations.append(allocation)
                else:
                    short_allocations.append(allocation)
            
            # Verify weights sum to 100%
            long_total = sum(a.weight_percentage for a in long_allocations)
            short_total = sum(a.weight_percentage for a in short_allocations)
            
            if abs(long_total - 100) > 0.1:
                logger.warning(f"Long allocations sum to {long_total}%, not 100%")
            if abs(short_total - 100) > 0.1:
                logger.warning(f"Short allocations sum to {short_total}%, not 100%")
                
            logger.info(f"Loaded {len(long_allocations)} LONG and {len(short_allocations)} SHORT industry allocations")
            
            return long_allocations, short_allocations
            
        except Exception as e:
            logger.error(f"Error fetching industry allocations: {e}")
            return [], []
    
    def get_symbols_by_rating(self, min_rating: str = "moderate_overweight") -> Dict[str, List[str]]:
        """Get symbols grouped by industry for given minimum rating"""
        try:
            long_allocations, short_allocations = self.get_industry_allocations()
            
            # Rating hierarchy
            rating_hierarchy = {
                "strong_overweight": 4,
                "moderate_overweight": 3,
                "moderate_underweight": 2,
                "strong_underweight": 1
            }
            
            min_rating_value = rating_hierarchy.get(min_rating, 3)
            
            # Filter allocations by rating
            filtered_allocations = []
            
            # Add LONG positions with overweight ratings
            for alloc in long_allocations:
                rating_value = rating_hierarchy.get(alloc.rating, 0)
                if rating_value >= min_rating_value:
                    filtered_allocations.append(alloc)
                    
            # Add SHORT positions with underweight ratings
            for alloc in short_allocations:
                if alloc.rating in ["strong_underweight", "moderate_underweight"]:
                    filtered_allocations.append(alloc)
            
            # Group symbols by industry
            result = {}
            for alloc in filtered_allocations:
                key = f"{alloc.industry}_{alloc.position_type}"
                result[key] = alloc.symbols
                
            return result
            
        except Exception as e:
            logger.error(f"Error getting symbols by rating: {e}")
            return {}
    
    def get_industry_risk_parameters(self, industry: str, rating: str) -> Dict:
        """Get risk parameters based on industry rating"""
        # Risk parameters by rating
        risk_params = {
            "strong_overweight": {
                "min_probability": 0.35,
                "min_risk_reward": 2.0,
                "allow_directional": True,
                "max_risk_per_trade": 0.03,  # 3% of allocated capital
                "position_sizing_multiplier": 1.2
            },
            "moderate_overweight": {
                "min_probability": 0.45,
                "min_risk_reward": 1.5,
                "allow_directional": False,
                "max_risk_per_trade": 0.02,  # 2% of allocated capital
                "position_sizing_multiplier": 1.0
            },
            "strong_underweight": {
                "min_probability": 0.40,
                "min_risk_reward": 1.8,
                "allow_directional": True,
                "max_risk_per_trade": 0.025,
                "position_sizing_multiplier": 1.1
            },
            "moderate_underweight": {
                "min_probability": 0.50,
                "min_risk_reward": 1.5,
                "allow_directional": False,
                "max_risk_per_trade": 0.015,
                "position_sizing_multiplier": 0.9
            }
        }
        
        return risk_params.get(rating, risk_params["moderate_overweight"])
    
    def allocate_capital_to_industries(self, total_capital: float, 
                                     long_percentage: float) -> Dict[str, float]:
        """Allocate capital to industries based on weights and long/short ratio"""
        try:
            long_allocations, short_allocations = self.get_industry_allocations()
            
            long_capital = total_capital * (long_percentage / 100)
            short_capital = total_capital * ((100 - long_percentage) / 100)
            
            allocations = {}
            
            # Allocate long capital
            for alloc in long_allocations:
                key = f"{alloc.industry}_LONG"
                allocations[key] = long_capital * (alloc.weight_percentage / 100)
                
            # Allocate short capital
            for alloc in short_allocations:
                key = f"{alloc.industry}_SHORT"
                allocations[key] = short_capital * (alloc.weight_percentage / 100)
                
            return allocations
            
        except Exception as e:
            logger.error(f"Error allocating capital to industries: {e}")
            return {}
    
    def get_tradeable_symbols(self) -> Dict[str, Dict]:
        """Get all tradeable symbols with their best strategies by position type"""
        try:
            long_allocations, short_allocations = self.get_industry_allocations()
            symbols_info = {}
            
            # Process LONG positions - select best strategy for each symbol
            for alloc in long_allocations:
                # Query strategies table for best strategies in this industry
                symbols_result = self.supabase.table('strategies').select(
                    'stock_name, total_score, strategy_name, probability_of_profit, risk_reward_ratio'
                ).eq('industry', alloc.industry).gte('total_score', 0.4).order('total_score', desc=True).execute()
                
                if symbols_result.data:
                    # Group by symbol and pick best strategy (highest total_score)
                    symbol_strategies = {}
                    for row in symbols_result.data:
                        symbol = row['stock_name']
                        if symbol not in symbol_strategies or row['total_score'] > symbol_strategies[symbol]['total_score']:
                            symbol_strategies[symbol] = row
                    
                    # Add best strategy for each symbol
                    for symbol, best_strategy in symbol_strategies.items():
                        symbols_info[symbol] = {
                            'industry': alloc.industry,
                            'position_type': 'LONG',
                            'rating': alloc.rating,
                            'weight': alloc.weight_percentage,
                            'strategy_name': best_strategy['strategy_name'],
                            'total_score': best_strategy['total_score'],
                            'probability_of_profit': best_strategy['probability_of_profit'],
                            'risk_reward_ratio': best_strategy['risk_reward_ratio']
                        }
                        
            # Process SHORT positions - select best strategy for each symbol
            for alloc in short_allocations:
                # Query strategies table for best strategies in this industry
                symbols_result = self.supabase.table('strategies').select(
                    'stock_name, total_score, strategy_name, probability_of_profit, risk_reward_ratio'
                ).eq('industry', alloc.industry).gte('total_score', 0.4).order('total_score', desc=True).execute()
                
                if symbols_result.data:
                    # Group by symbol and pick best strategy (highest total_score)
                    symbol_strategies = {}
                    for row in symbols_result.data:
                        symbol = row['stock_name']
                        if symbol not in symbol_strategies or row['total_score'] > symbol_strategies[symbol]['total_score']:
                            symbol_strategies[symbol] = row
                    
                    # Add best strategy for each symbol (skip if already exists from LONG)
                    for symbol, best_strategy in symbol_strategies.items():
                        if symbol not in symbols_info:  # Only add if not already in LONG
                            symbols_info[symbol] = {
                                'industry': alloc.industry,
                                'position_type': 'SHORT',
                                'rating': alloc.rating,
                                'weight': alloc.weight_percentage,
                                'strategy_name': best_strategy['strategy_name'],
                                'total_score': best_strategy['total_score'],
                                'probability_of_profit': best_strategy['probability_of_profit'],
                                'risk_reward_ratio': best_strategy['risk_reward_ratio']
                            }
                        
            logger.info(f"Found {len(symbols_info)} tradeable symbols with best strategies from strategies table")
            return symbols_info
            
        except Exception as e:
            logger.error(f"Error getting tradeable symbols: {e}")
            return {}