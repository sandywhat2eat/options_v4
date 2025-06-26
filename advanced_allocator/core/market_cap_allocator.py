"""
Market Cap Allocator Module
Distributes capital across market cap categories based on market conditions
"""

import logging
from typing import Dict, List
import yaml
from pathlib import Path

logger = logging.getLogger(__name__)


class MarketCapAllocator:
    """Allocates capital across different market cap categories"""
    
    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config" / "market_conditions.yaml"
            
        self.config = self._load_config(config_path)
        self.market_cap_ranges = {
            'large_cap': {'min': 20000, 'max': float('inf')},  # > 20,000 Cr
            'mid_cap': {'min': 5000, 'max': 20000},  # 5,000 - 20,000 Cr
            'small_cap': {'min': 500, 'max': 5000},  # 500 - 5,000 Cr
            'micro_cap': {'min': 0, 'max': 500}  # < 500 Cr
        }
        
    def _load_config(self, config_path: Path) -> Dict:
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            # Return default config
            return {
                'market_cap_allocation': {
                    'neutral': {
                        'large_cap': 45,
                        'mid_cap': 30,
                        'small_cap': 20,
                        'micro_cap': 5
                    }
                }
            }
    
    def allocate_by_market_condition(self, total_capital: float, 
                                   market_state: str) -> Dict[str, float]:
        """Allocate capital to market cap categories based on market state"""
        try:
            # Get allocation percentages for market state
            allocations = self.config['market_cap_allocation'].get(
                market_state,
                self.config['market_cap_allocation']['neutral']
            )
            
            # Calculate capital for each market cap
            result = {}
            for market_cap, percentage in allocations.items():
                result[market_cap] = total_capital * (percentage / 100)
                
            logger.info(f"Market cap allocation for {market_state}: {allocations}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in market cap allocation: {e}")
            # Return default neutral allocation
            return {
                'large_cap': total_capital * 0.45,
                'mid_cap': total_capital * 0.30,
                'small_cap': total_capital * 0.20,
                'micro_cap': total_capital * 0.05
            }
    
    def categorize_stocks(self, stocks_data: List[Dict]) -> Dict[str, List[str]]:
        """Categorize stocks by market cap"""
        categorized = {
            'large_cap': [],
            'mid_cap': [],
            'small_cap': [],
            'micro_cap': []
        }
        
        try:
            for stock in stocks_data:
                market_cap_category = stock.get('market_cap_category', '')
                symbol = stock.get('symbol', '')
                
                if not symbol or not market_cap_category:
                    continue
                
                # Map database category to our internal categories
                category_mapping = {
                    'Large Cap': 'large_cap',
                    'Mid Cap': 'mid_cap', 
                    'Small Cap': 'small_cap',
                    'Micro Cap': 'micro_cap'
                }
                
                internal_category = category_mapping.get(market_cap_category)
                if internal_category and internal_category in categorized:
                    categorized[internal_category].append(symbol)
                        
            # Log categorization results
            for category, symbols in categorized.items():
                logger.info(f"{category}: {len(symbols)} stocks")
                
            return categorized
            
        except Exception as e:
            logger.error(f"Error categorizing stocks: {e}")
            return categorized
    
    def get_allocation_constraints(self, market_cap: str) -> Dict:
        """Get allocation constraints for a market cap category"""
        constraints = {
            'large_cap': {
                'max_positions': 8,
                'min_allocation_per_position': 0.08,  # 8%
                'max_allocation_per_position': 0.20,  # 20%
                'liquidity_requirement': 'low'
            },
            'mid_cap': {
                'max_positions': 6,
                'min_allocation_per_position': 0.10,  # 10%
                'max_allocation_per_position': 0.25,  # 25%
                'liquidity_requirement': 'medium'
            },
            'small_cap': {
                'max_positions': 4,
                'min_allocation_per_position': 0.15,  # 15%
                'max_allocation_per_position': 0.30,  # 30%
                'liquidity_requirement': 'high'
            },
            'micro_cap': {
                'max_positions': 2,
                'min_allocation_per_position': 0.25,  # 25%
                'max_allocation_per_position': 0.50,  # 50%
                'liquidity_requirement': 'very_high'
            }
        }
        
        return constraints.get(market_cap, constraints['mid_cap'])
    
    def adjust_for_volatility(self, base_allocations: Dict[str, float], 
                            vix_level: float) -> Dict[str, float]:
        """Adjust market cap allocations based on VIX levels"""
        try:
            # VIX-based adjustment factors
            if vix_level < 15:  # Low volatility
                adjustments = {
                    'large_cap': 0.9,
                    'mid_cap': 1.0,
                    'small_cap': 1.1,
                    'micro_cap': 1.2
                }
            elif vix_level < 20:  # Normal volatility
                adjustments = {
                    'large_cap': 1.0,
                    'mid_cap': 1.0,
                    'small_cap': 1.0,
                    'micro_cap': 1.0
                }
            elif vix_level < 25:  # Elevated volatility
                adjustments = {
                    'large_cap': 1.1,
                    'mid_cap': 1.0,
                    'small_cap': 0.9,
                    'micro_cap': 0.8
                }
            else:  # High volatility
                adjustments = {
                    'large_cap': 1.2,
                    'mid_cap': 1.0,
                    'small_cap': 0.8,
                    'micro_cap': 0.6
                }
                
            # Apply adjustments
            adjusted = {}
            total_adjusted = 0
            
            for market_cap, capital in base_allocations.items():
                adjusted[market_cap] = capital * adjustments.get(market_cap, 1.0)
                total_adjusted += adjusted[market_cap]
                
            # Normalize to maintain total capital
            if total_adjusted > 0:
                for market_cap in adjusted:
                    adjusted[market_cap] = adjusted[market_cap] * (sum(base_allocations.values()) / total_adjusted)
                    
            logger.info(f"VIX level {vix_level}: Adjusted allocations from {base_allocations} to {adjusted}")
            
            return adjusted
            
        except Exception as e:
            logger.error(f"Error adjusting for volatility: {e}")
            return base_allocations