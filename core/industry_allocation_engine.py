"""
Industry-First Allocation Engine for Options Strategy Selection
Uses industry_allocations_current and sector_allocations_current tables
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

try:
    from config.options_config import (
        INDUSTRY_STRATEGY_MAPPING, POSITION_SIZING_RULES, 
        STRATEGY_SCORING_WEIGHTS, STRATEGY_FILTER_THRESHOLDS,
        SUPABASE_CONFIG, OPTIONS_TOTAL_EXPOSURE
    )
except ImportError:
    # Fallback configuration
    INDUSTRY_STRATEGY_MAPPING = {
        'Electronic Equipment/Instruments': {
            'LONG + Strong Overweight': ['Bull Call Spreads', 'Cash-Secured Puts'],
            'LONG + Moderate Overweight': ['Iron Condors', 'Bull Put Spreads']
        }
    }
    POSITION_SIZING_RULES = {
        'MAX_SINGLE_STRATEGY_EXPOSURE': 0.15,
        'MAX_INDUSTRY_OPTIONS_EXPOSURE': 0.30,
        'MAX_SINGLE_SYMBOL_EXPOSURE': 0.10
    }
    STRATEGY_SCORING_WEIGHTS = {'probability_profit': 0.30, 'risk_reward_ratio': 0.25}
    STRATEGY_FILTER_THRESHOLDS = {
        'moderate': {'min_probability': 0.25, 'max_risk_per_trade': 0.05}
    }
    SUPABASE_CONFIG = {'min_industry_weight': 5.0}
    OPTIONS_TOTAL_EXPOSURE = 30000000

logger = logging.getLogger(__name__)

class IndustryAllocationEngine:
    """
    Select options strategies based on industry allocation weights and position types
    """
    
    def __init__(self, supabase_client=None):
        self.supabase = supabase_client
        self.industry_allocations = {}
        self.sector_allocations = {}
        self.symbol_industry_mapping = {}
        
    def load_allocation_data(self) -> bool:
        """
        Load industry and sector allocation data from database
        """
        try:
            if not self.supabase:
                logger.error("No Supabase client available")
                return False
            
            # Load industry allocations (primary data source)
            industry_query = self.supabase.table('industry_allocations_current') \
                .select('*') \
                .gte('weight_percentage', SUPABASE_CONFIG['min_industry_weight']) \
                .order('weight_percentage', desc=True)
            
            industry_result = industry_query.execute()
            
            if not industry_result.data:
                logger.error("No industry allocation data found")
                return False
            
            # Convert to DataFrame for easier processing
            self.industry_allocations = pd.DataFrame(industry_result.data)
            
            # Load sector allocations (for hierarchical context)
            sector_query = self.supabase.table('sector_allocations_current') \
                .select('*') \
                .order('weight_percentage', desc=True)
            
            sector_result = sector_query.execute()
            self.sector_allocations = pd.DataFrame(sector_result.data) if sector_result.data else pd.DataFrame()
            
            # Load symbol-industry mapping
            stock_query = self.supabase.table('stock_data') \
                .select('symbol,industry,sector')
            
            stock_result = stock_query.execute()
            if stock_result.data:
                stock_df = pd.DataFrame(stock_result.data)
                self.symbol_industry_mapping = dict(zip(stock_df['symbol'], stock_df['industry']))
            
            logger.info(f"Loaded {len(self.industry_allocations)} industry allocations")
            logger.info(f"Loaded {len(self.sector_allocations)} sector allocations")
            logger.info(f"Loaded {len(self.symbol_industry_mapping)} symbol mappings")
            
            return True
            
        except Exception as e:
            logger.error(f"Error loading allocation data: {e}")
            return False
    
    def get_priority_industries(self, min_weight: float = 5.0) -> List[Dict]:
        """
        Get industries prioritized by weight percentage
        """
        if self.industry_allocations.empty:
            if not self.load_allocation_data():
                return []
        
        # Filter by minimum weight and sort by priority
        priority_industries = self.industry_allocations[
            self.industry_allocations['weight_percentage'] >= min_weight
        ].copy()
        
        # Add priority score (weight + position type factor)
        priority_industries['priority_score'] = priority_industries.apply(
            self._calculate_industry_priority, axis=1
        )
        
        priority_industries = priority_industries.sort_values(
            'priority_score', ascending=False
        )
        
        return priority_industries.to_dict('records')
    
    def get_symbols_for_industry(self, industry: str, limit: int = 5) -> List[str]:
        """
        Get symbols for a specific industry
        """
        symbols = [symbol for symbol, ind in self.symbol_industry_mapping.items() 
                  if ind == industry]
        
        # For now, return first 'limit' symbols
        # TODO: Add ranking/scoring logic here
        return symbols[:limit]
    
    def select_strategies_for_industry(self, industry_data: Dict, 
                                     market_condition: Dict) -> List[Dict]:
        """
        Select preferred strategies for an industry based on allocation and market condition
        """
        try:
            industry = industry_data['industry']
            weight_percentage = industry_data['weight_percentage']
            position_type = industry_data['position_type']
            rating = industry_data['rating']
            
            # Create allocation key
            allocation_key = f"{position_type} + {rating}"
            
            # Get strategy preferences from mapping
            if industry in INDUSTRY_STRATEGY_MAPPING:
                industry_strategies = INDUSTRY_STRATEGY_MAPPING[industry]
                preferred_strategies = industry_strategies.get(allocation_key, [])
            else:
                # Use generic mapping based on allocation key
                preferred_strategies = self._get_generic_strategies(allocation_key)
            
            # Filter strategies based on market condition
            market_config = market_condition.get('config', {})
            market_preferred = market_config.get('preferred_strategies', [])
            market_avoid = market_config.get('avoid_strategies', [])
            
            # Find intersection of industry and market preferences
            final_strategies = []
            for strategy in preferred_strategies:
                if strategy in market_avoid:
                    continue
                
                # Boost score if also preferred by market condition
                boost = 1.2 if strategy in market_preferred else 1.0
                
                final_strategies.append({
                    'strategy_name': strategy,
                    'industry': industry,
                    'weight_percentage': weight_percentage,
                    'position_type': position_type,
                    'rating': rating,
                    'allocation_key': allocation_key,
                    'market_boost': boost,
                    'priority_score': self._calculate_strategy_priority(
                        strategy, weight_percentage, allocation_key, boost
                    )
                })
            
            # Sort by priority score
            final_strategies.sort(key=lambda x: x['priority_score'], reverse=True)
            
            return final_strategies
            
        except Exception as e:
            logger.error(f"Error selecting strategies for industry {industry_data}: {e}")
            return []
    
    def calculate_position_size(self, strategy_data: Dict, 
                              risk_tolerance: str = 'moderate') -> Dict:
        """
        Calculate position size based on industry allocation and risk limits
        """
        try:
            weight_percentage = strategy_data['weight_percentage']
            industry = strategy_data['industry']
            strategy_name = strategy_data['strategy_name']
            
            # Calculate industry capital allocation
            industry_capital = OPTIONS_TOTAL_EXPOSURE * (weight_percentage / 100)
            
            # Get risk limits
            risk_limits = STRATEGY_FILTER_THRESHOLDS[risk_tolerance]
            max_risk_per_trade = risk_limits['max_risk_per_trade']
            
            # Calculate maximum position size based on various limits
            max_by_industry = industry_capital * POSITION_SIZING_RULES['MAX_INDUSTRY_OPTIONS_EXPOSURE']
            max_by_strategy = OPTIONS_TOTAL_EXPOSURE * POSITION_SIZING_RULES['MAX_SINGLE_STRATEGY_EXPOSURE']
            max_by_risk = OPTIONS_TOTAL_EXPOSURE * max_risk_per_trade
            
            # Take the most conservative limit
            max_position_size = min(max_by_industry, max_by_strategy, max_by_risk)
            
            # Strategy-specific position sizing
            if self._is_premium_strategy(strategy_name):
                # For strategies that require premium outlay
                recommended_size = max_position_size * 0.5  # Conservative for premium strategies
            elif self._is_margin_strategy(strategy_name):
                # For strategies that require margin
                recommended_size = max_position_size * 0.8  # Can use more for margin strategies
            else:
                # Default sizing
                recommended_size = max_position_size * 0.6
            
            return {
                'industry_capital': industry_capital,
                'max_position_size': max_position_size,
                'recommended_size': recommended_size,
                'max_by_industry': max_by_industry,
                'max_by_strategy': max_by_strategy,
                'max_by_risk': max_by_risk,
                'sizing_logic': self._get_sizing_logic(strategy_name),
                'risk_percentage': (recommended_size / OPTIONS_TOTAL_EXPOSURE) * 100
            }
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return {
                'recommended_size': OPTIONS_TOTAL_EXPOSURE * 0.01,  # 1% fallback
                'error': str(e)
            }
    
    def generate_portfolio_allocation(self, market_condition: Dict,
                                    risk_tolerance: str = 'moderate',
                                    max_industries: int = 10) -> Dict:
        """
        Generate complete portfolio allocation based on industry weights
        """
        try:
            if not self.load_allocation_data():
                return {'error': 'Failed to load allocation data'}
            
            # Get priority industries
            priority_industries = self.get_priority_industries()[:max_industries]
            
            portfolio_allocation = {
                'total_exposure': OPTIONS_TOTAL_EXPOSURE,
                'market_condition': market_condition.get('condition', 'Unknown'),
                'risk_tolerance': risk_tolerance,
                'industry_allocations': [],
                'summary': {
                    'total_industries': 0,
                    'total_strategies': 0,
                    'total_allocated_capital': 0,
                    'allocation_percentage': 0
                },
                'generated_at': datetime.now().isoformat()
            }
            
            total_allocated = 0
            
            for industry_data in priority_industries:
                industry = industry_data['industry']
                
                # Get symbols for this industry
                symbols = self.get_symbols_for_industry(industry, limit=3)
                
                if not symbols:
                    logger.warning(f"No symbols found for industry {industry}")
                    continue
                
                # Select strategies for this industry
                strategies = self.select_strategies_for_industry(industry_data, market_condition)
                
                if not strategies:
                    logger.warning(f"No strategies selected for industry {industry}")
                    continue
                
                # Calculate position sizing
                industry_allocation = {
                    'industry': industry,
                    'weight_percentage': industry_data['weight_percentage'],
                    'position_type': industry_data['position_type'],
                    'rating': industry_data['rating'],
                    'symbols': symbols,
                    'strategies': [],
                    'total_industry_capital': 0
                }
                
                for strategy in strategies[:2]:  # Top 2 strategies per industry
                    position_sizing = self.calculate_position_size(strategy, risk_tolerance)
                    
                    strategy_allocation = {
                        'strategy_name': strategy['strategy_name'],
                        'priority_score': strategy['priority_score'],
                        'recommended_capital': position_sizing['recommended_size'],
                        'max_capital': position_sizing['max_position_size'],
                        'risk_percentage': position_sizing['risk_percentage'],
                        'symbols_to_analyze': symbols,
                        'position_sizing_details': position_sizing
                    }
                    
                    industry_allocation['strategies'].append(strategy_allocation)
                    industry_allocation['total_industry_capital'] += position_sizing['recommended_size']
                
                portfolio_allocation['industry_allocations'].append(industry_allocation)
                total_allocated += industry_allocation['total_industry_capital']
            
            # Update summary
            portfolio_allocation['summary'] = {
                'total_industries': len(portfolio_allocation['industry_allocations']),
                'total_strategies': sum(len(ind['strategies']) for ind in portfolio_allocation['industry_allocations']),
                'total_allocated_capital': total_allocated,
                'allocation_percentage': (total_allocated / OPTIONS_TOTAL_EXPOSURE) * 100
            }
            
            return portfolio_allocation
            
        except Exception as e:
            logger.error(f"Error generating portfolio allocation: {e}")
            return {'error': str(e)}
    
    def _calculate_industry_priority(self, row) -> float:
        """Calculate priority score for industry"""
        base_score = row['weight_percentage']
        
        # Boost for overweight positions
        if 'Overweight' in row['rating']:
            base_score *= 1.3
        elif 'Underweight' in row['rating']:
            base_score *= 0.8
        
        # Boost for LONG positions (easier to trade options on)
        if row['position_type'] == 'LONG':
            base_score *= 1.1
        
        return base_score
    
    def _get_generic_strategies(self, allocation_key: str) -> List[str]:
        """Get generic strategies for allocation key not in mapping"""
        generic_mapping = {
            'LONG + Strong Overweight': ['Bull Call Spreads', 'Cash-Secured Puts'],
            'LONG + Moderate Overweight': ['Iron Condors', 'Bull Put Spreads'],
            'SHORT + Moderate Underweight': ['Bear Call Spreads', 'Bear Put Spreads'],
            'SHORT + Strong Underweight': ['Bear Put Spreads', 'Long Puts']
        }
        
        return generic_mapping.get(allocation_key, ['Iron Condors'])
    
    def _calculate_strategy_priority(self, strategy: str, weight: float, 
                                   allocation_key: str, market_boost: float) -> float:
        """Calculate priority score for strategy"""
        base_score = weight * market_boost
        
        # Strategy-specific boosts
        strategy_multipliers = {
            'Bull Call Spreads': 1.2,
            'Bear Put Spreads': 1.2,
            'Iron Condors': 1.1,
            'Cash-Secured Puts': 1.0,
            'Covered Calls': 1.0,
            'Long Options': 0.8,  # Lower priority due to time decay
        }
        
        multiplier = strategy_multipliers.get(strategy, 1.0)
        return base_score * multiplier
    
    def _is_premium_strategy(self, strategy_name: str) -> bool:
        """Check if strategy requires premium outlay"""
        premium_strategies = [
            'Bull Call Spreads', 'Bear Put Spreads', 
            'Long Calls', 'Long Puts', 'Long Straddles', 'Long Strangles'
        ]
        return strategy_name in premium_strategies
    
    def _is_margin_strategy(self, strategy_name: str) -> bool:
        """Check if strategy requires margin"""
        margin_strategies = [
            'Cash-Secured Puts', 'Covered Calls', 'Bear Call Spreads',
            'Bull Put Spreads', 'Short Straddles', 'Short Strangles'
        ]
        return strategy_name in margin_strategies
    
    def _get_sizing_logic(self, strategy_name: str) -> str:
        """Get sizing logic explanation"""
        if self._is_premium_strategy(strategy_name):
            return "Conservative sizing for premium outlay strategies"
        elif self._is_margin_strategy(strategy_name):
            return "Moderate sizing for margin-based strategies"
        else:
            return "Default sizing for complex strategies"
    
    def validate_portfolio_allocation(self, allocation: Dict) -> Dict:
        """Validate portfolio allocation against risk limits"""
        validation_results = {
            'valid': True,
            'warnings': [],
            'errors': [],
            'summary': {}
        }
        
        try:
            total_allocated = allocation['summary']['total_allocated_capital']
            allocation_pct = allocation['summary']['allocation_percentage']
            
            # Check total allocation
            if allocation_pct > 50:  # Don't allocate more than 50% to options
                validation_results['warnings'].append(
                    f"High options allocation: {allocation_pct:.1f}%"
                )
            
            # Check industry diversification
            industry_count = allocation['summary']['total_industries']
            if industry_count < 3:
                validation_results['warnings'].append(
                    f"Low diversification: only {industry_count} industries"
                )
            
            # Check individual position sizes
            for industry_alloc in allocation['industry_allocations']:
                industry_capital = industry_alloc['total_industry_capital']
                industry_pct = (industry_capital / OPTIONS_TOTAL_EXPOSURE) * 100
                
                if industry_pct > POSITION_SIZING_RULES['MAX_INDUSTRY_OPTIONS_EXPOSURE'] * 100:
                    validation_results['errors'].append(
                        f"Industry {industry_alloc['industry']} exceeds max allocation: {industry_pct:.1f}%"
                    )
                    validation_results['valid'] = False
            
            validation_results['summary'] = {
                'total_allocation_check': 'PASS' if allocation_pct <= 50 else 'WARNING',
                'diversification_check': 'PASS' if industry_count >= 3 else 'WARNING',
                'position_size_check': 'PASS' if validation_results['valid'] else 'FAIL'
            }
            
        except Exception as e:
            validation_results['errors'].append(f"Validation error: {str(e)}")
            validation_results['valid'] = False
        
        return validation_results