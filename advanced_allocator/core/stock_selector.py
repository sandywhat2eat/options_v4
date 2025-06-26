"""
Stock Selector Module
Selects stocks within market cap categories based on various criteria
"""

import logging
from typing import Dict, List, Tuple
from dataclasses import dataclass
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class StockScore:
    """Strategy-based scoring data"""
    symbol: str
    strategy_score: float  # From strategies table
    probability_of_profit: float
    risk_reward_ratio: float
    market_cap_category: str
    industry: str
    position_type: str  # LONG or SHORT
    composite_score: float = 0.0  # Calculated composite score for sorting


class StockSelector:
    """Selects stocks using strategy-level data"""
    
    def __init__(self, supabase_client):
        self.supabase = supabase_client
        
    def select_stocks(self, market_cap_category: str, 
                     symbols: List[str], 
                     position_type: str,
                     max_positions: int = 5) -> List[StockScore]:
        """Select top stocks from given symbols using strategy data"""
        try:
            if not symbols:
                return []
                
            # Get strategy data for these symbols
            strategy_scores = self._get_strategy_scores(symbols, position_type)
            
            # Get market cap data
            market_cap_data = self._get_market_cap_data(symbols)
            
            # Create stock scores from strategy data
            stock_scores = []
            for symbol in symbols:
                if symbol in strategy_scores and symbol in market_cap_data:
                    strategy_data = strategy_scores[symbol]
                    market_cap_category_data = market_cap_data[symbol]
                    
                    # Calculate composite score from strategy data
                    composite_score = (
                        0.5 * strategy_data['total_score'] +
                        0.3 * strategy_data['probability_of_profit'] +
                        0.2 * min(strategy_data['risk_reward_ratio'] / 3.0, 1.0)
                    )
                    
                    stock_score = StockScore(
                        symbol=symbol,
                        strategy_score=strategy_data['total_score'],
                        probability_of_profit=strategy_data['probability_of_profit'],
                        risk_reward_ratio=strategy_data['risk_reward_ratio'],
                        market_cap_category=market_cap_category_data,
                        industry=strategy_data.get('industry', ''),
                        position_type=position_type
                    )
                    # Use composite_score for sorting
                    stock_score.composite_score = composite_score
                    stock_scores.append(stock_score)
                    
            # Sort by composite score
            stock_scores.sort(key=lambda x: x.composite_score, reverse=True)
            
            # Return top N stocks
            selected = stock_scores[:max_positions]
            
            logger.info(f"Selected {len(selected)} stocks for {market_cap_category} {position_type}")
            
            return selected
            
        except Exception as e:
            logger.error(f"Error selecting stocks: {e}")
            return []
    
    def _get_strategy_scores(self, symbols: List[str], position_type: str) -> Dict:
        """Get strategy scores from strategies table"""
        try:
            if not self.supabase:
                # Mock data for testing
                return {symbol: {
                    'total_score': np.random.uniform(0.4, 0.9),
                    'probability_of_profit': np.random.uniform(0.3, 0.8),
                    'risk_reward_ratio': np.random.uniform(1.0, 3.0),
                    'industry': 'Mock Industry'
                } for symbol in symbols}
                
            # Query strategies table for best strategies for these symbols
            response = self.supabase.table('strategies').select(
                'stock_name, total_score, probability_of_profit, risk_reward_ratio, industry'
            ).in_('stock_name', symbols).gte('total_score', 0.4).order('total_score', desc=True).execute()
            
            if not response.data:
                return {}
                
            # Group by symbol and take best strategy per symbol
            symbol_scores = {}
            for row in response.data:
                symbol = row['stock_name']
                if symbol not in symbol_scores:
                    symbol_scores[symbol] = {
                        'total_score': row['total_score'],
                        'probability_of_profit': row['probability_of_profit'],
                        'risk_reward_ratio': row['risk_reward_ratio'],
                        'industry': row.get('industry', '')
                    }
                    
            return symbol_scores
            
        except Exception as e:
            logger.error(f"Error getting strategy scores: {e}")
            return {}
    
    def _get_market_cap_data(self, symbols: List[str]) -> Dict:
        """Get market cap category for symbols from stock_rankings table"""
        try:
            if not self.supabase:
                # Mock data for testing
                return {symbol: 'Large Cap' for symbol in symbols}
                
            # Query stock_rankings for market cap categories
            response = self.supabase.table('stock_rankings').select(
                'symbol, market_cap_category'
            ).in_('symbol', symbols).execute()
            
            if not response.data:
                return {}
                
            # Create mapping
            market_cap_data = {}
            for row in response.data:
                market_cap_data[row['symbol']] = row['market_cap_category']
                
            return market_cap_data
            
        except Exception as e:
            logger.error(f"Error getting market cap data: {e}")
            return {}
    
