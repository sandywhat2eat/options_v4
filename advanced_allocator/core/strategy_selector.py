"""
Strategy Selector Module
Selects appropriate options strategies based on simple criteria
"""

import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
import yaml
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class StrategySelection:
    """Selected strategy details"""
    symbol: str
    strategy_name: str
    conviction_level: str
    probability_of_profit: float
    total_score: float
    risk_reward_ratio: float
    max_loss: float
    max_profit: float
    strategy_id: str
    position_type: str  # LONG or SHORT


class StrategySelector:
    """Selects strategies based on simple criteria"""
    
    def __init__(self, supabase_client, config_path: str = None):
        self.supabase = supabase_client
        
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config" / "strategy_filters.yaml"
            
        self.config = self._load_config(config_path)
        
    def _load_config(self, config_path: Path) -> Dict:
        """Load strategy filter configuration"""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return {}
    
    def select_strategies(self, symbol: str, 
                         market_cap: str,
                         position_type: str,
                         industry_rating: str) -> List[StrategySelection]:
        """Select strategies for a symbol based on criteria"""
        try:
            # Get available strategies for symbol
            strategies = self._get_available_strategies(symbol)
            
            if not strategies:
                logger.warning(f"No strategies found for {symbol}")
                return []
            
            # Filter by market cap constraints
            allowed_strategies = self._get_allowed_strategies(market_cap)
            strategies = [s for s in strategies if s['strategy_name'] in allowed_strategies]
            
            # Apply quality filters
            quality_filters = self.config.get('quality_filters', {})
            filtered = []
            
            for strategy in strategies:
                if self._passes_quality_filters(strategy, quality_filters):
                    # Apply industry rating filters
                    if self._passes_risk_filters(strategy, industry_rating, position_type):
                        filtered.append(strategy)
            
            # Convert to StrategySelection objects
            selections = []
            for strategy in filtered:
                selection = StrategySelection(
                    symbol=symbol,
                    strategy_name=strategy['strategy_name'],
                    conviction_level=strategy['conviction_level'],
                    probability_of_profit=strategy['probability_of_profit'],
                    total_score=strategy['total_score'],
                    risk_reward_ratio=strategy.get('risk_reward_ratio', 0),
                    max_loss=strategy.get('max_loss', 0),
                    max_profit=strategy.get('max_profit', 0),
                    strategy_id=strategy.get('strategy_id', ''),
                    position_type=position_type
                )
                selections.append(selection)
            
            # Sort by ranking priorities
            sorted_selections = self._sort_by_priorities(selections)
            
            logger.info(f"Selected {len(sorted_selections)} strategies for {symbol}")
            
            return sorted_selections
            
        except Exception as e:
            logger.error(f"Error selecting strategies for {symbol}: {e}")
            return []
    
    def _get_available_strategies(self, symbol: str) -> List[Dict]:
        """Get available strategies from database"""
        try:
            if not self.supabase:
                logger.error("CRITICAL: Database client is required for real trading system")
                raise ValueError("Database client is required for real trading system")
            
            # Query strategies from database
            response = self.supabase.table('options_strategies_live').select('*').eq(
                'symbol', symbol
            ).execute()
            
            return response.data if response.data else []
            
        except Exception as e:
            logger.error(f"Error fetching strategies: {e}")
            return []
    
    def _get_allowed_strategies(self, market_cap: str) -> List[str]:
        """Get allowed strategies for market cap"""
        market_cap_config = self.config.get('strategy_by_market_cap', {})
        cap_config = market_cap_config.get(market_cap, market_cap_config.get('mid_cap', {}))
        
        allowed = cap_config.get('allowed_strategies', [])
        if allowed == 'all':
            # All strategies allowed
            return [
                'Iron Condor', 'Bull Call Spread', 'Bear Put Spread',
                'Butterfly Spread', 'Calendar Spread', 'Cash-Secured Put',
                'Covered Call', 'Long Call', 'Long Put', 'Straddle',
                'Strangle', 'Iron Butterfly', 'Ratio Spread'
            ]
        
        return allowed
    
    def _passes_quality_filters(self, strategy: Dict, filters: Dict) -> bool:
        """Check if strategy passes quality filters"""
        # Check minimum total score
        min_score = filters.get('min_total_score', 0.6)
        if strategy.get('total_score', 0) < min_score:
            return False
        
        # Check probability of profit
        min_prob = filters.get('min_probability_of_profit', 0.5)
        if strategy.get('probability_of_profit', 0) < min_prob:
            return False
        
        # Check conviction level
        allowed_levels = filters.get('min_conviction_levels', ['MEDIUM', 'HIGH', 'VERY_HIGH'])
        if strategy.get('conviction_level', 'LOW') not in allowed_levels:
            return False
        
        return True
    
    def _passes_risk_filters(self, strategy: Dict, industry_rating: str, 
                           position_type: str) -> bool:
        """Check if strategy passes risk filters based on industry rating"""
        risk_config = self.config.get('risk_by_industry_rating', {})
        risk_params = risk_config.get(industry_rating, risk_config.get('moderate_overweight', {}))
        
        # Check probability threshold
        min_prob = risk_params.get('min_probability', 0.45)
        if strategy.get('probability_of_profit', 0) < min_prob:
            return False
        
        # Check risk-reward ratio
        min_rr = risk_params.get('min_risk_reward', 1.5)
        if strategy.get('risk_reward_ratio', 0) < min_rr:
            return False
        
        # Check if directional strategies allowed
        allow_directional = risk_params.get('allow_directional', False)
        if not allow_directional:
            directional_strategies = ['Long Call', 'Long Put']
            if strategy.get('strategy_name') in directional_strategies:
                return False
        
        return True
    
    def _sort_by_priorities(self, selections: List[StrategySelection]) -> List[StrategySelection]:
        """Sort strategies by configured priorities"""
        priorities = self.config.get('ranking_priorities', [])
        
        # Create sorting key function
        def sort_key(selection):
            key_values = []
            
            for priority in priorities:
                field = priority['field']
                order = priority.get('order', 'desc')
                
                if field == 'conviction_level':
                    # Map conviction levels to numeric values
                    level_map = {
                        'VERY_HIGH': 4,
                        'HIGH': 3,
                        'MEDIUM': 2,
                        'LOW': 1
                    }
                    value = level_map.get(selection.conviction_level, 0)
                    key_values.append(-value if order == 'desc' else value)
                    
                elif field == 'total_score':
                    value = selection.total_score
                    key_values.append(-value if order == 'desc' else value)
                    
                elif field == 'probability_of_profit':
                    value = selection.probability_of_profit
                    key_values.append(-value if order == 'desc' else value)
                    
            return tuple(key_values)
        
        # Sort selections
        sorted_selections = sorted(selections, key=sort_key)
        
        return sorted_selections
    
    def get_best_strategy(self, symbol: str, market_cap: str, 
                         position_type: str, industry_rating: str) -> Optional[StrategySelection]:
        """Get the best strategy for a symbol"""
        strategies = self.select_strategies(symbol, market_cap, position_type, industry_rating)
        
        if strategies:
            return strategies[0]
            
        return None