"""
Hybrid Portfolio Engine - Combines Tier System with Industry Allocations
Professional-grade options portfolio allocation engine

This module implements:
1. Three-tier allocation (Income 60%, Momentum 30%, Volatility 10%)
2. Industry-based allocation within each tier
3. Correct position sizing using database lot sizes
4. Full capital deployment targeting 90%+
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import json
import sys
import yaml
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from database.supabase_integration import SupabaseIntegration
from data_scripts.market_quote_fetcher import MarketQuoteFetcher

logger = logging.getLogger(__name__)


@dataclass
class StrategyDataEnhanced:
    """Enhanced strategy information with lot size details"""
    strategy_id: int
    stock_name: str
    strategy_name: str
    net_premium: float
    lot_size: int  # From strategy_details.quantity
    probability_of_profit: float
    risk_reward_ratio: float
    total_score: float
    conviction_level: str
    strategy_type: str
    sector: str
    industry: str
    market_cap_category: str  # Large Cap, Mid Cap, Small Cap, Micro Cap
    
    # Greeks
    net_delta: float
    net_gamma: float
    net_theta: float
    net_vega: float
    
    # Component scores
    component_scores: Dict
    
    # Market analysis
    market_view: Dict
    
    # Calculated fields
    premium_per_lot: float  # net_premium * lot_size
    
    def calculate_lots_required(self, allocated_capital: float) -> int:
        """Calculate number of lots based on allocated capital"""
        if self.premium_per_lot <= 0:
            return 0
        
        # For credit strategies (negative premium), use absolute value
        premium_required = abs(self.premium_per_lot)
        lots = int(allocated_capital / premium_required)
        return max(1, lots)  # Minimum 1 lot


@dataclass 
class HybridPosition:
    """Position with hybrid tier-industry allocation"""
    strategy: StrategyDataEnhanced
    tier: str  # INCOME, MOMENTUM, VOLATILITY
    industry: str
    industry_weight: float
    position_type: str  # LONG or SHORT
    market_cap_category: str  # Large Cap, Mid Cap, Small Cap, Micro Cap
    
    # Position sizing
    allocated_capital: float
    number_of_lots: int
    actual_capital_deployed: float
    
    # Expected returns
    expected_monthly_income: float
    
    # Risk metrics
    position_risk_score: float
    greek_contribution: Dict[str, float]


class HybridPortfolioEngine:
    """Hybrid allocation engine combining tiers and industries"""
    
    def __init__(self, supabase_client):
        self.supabase = supabase_client
        self.quote_fetcher = MarketQuoteFetcher()
        
        # Tier allocations
        self.TIER_ALLOCATIONS = {
            'INCOME': 0.60,      # 60% - High probability income
            'MOMENTUM': 0.30,    # 30% - Directional momentum
            'VOLATILITY': 0.10   # 10% - Volatility arbitrage
        }
        
        # Strategy mapping to tiers with directional bias
        self.BULLISH_STRATEGIES = {
            'INCOME': [
                'Cash-Secured Put', 'Bull Put Spread', 'Short Put',
                'Covered Call', 'Short Put Spread'
            ],
            'MOMENTUM': [
                'Long Call', 'Bull Call Spread', 'Call Debit Spread',
                'Synthetic Long'
            ],
            'VOLATILITY': [
                'Call Ratio Spread', 'Call Calendar Spread',
                'Bullish Diagonal Spread'
            ]
        }
        
        self.BEARISH_STRATEGIES = {
            'INCOME': [
                'Bear Call Spread', 'Short Call', 'Call Credit Spread',
                'Covered Put'
            ],
            'MOMENTUM': [
                'Long Put', 'Bear Put Spread', 'Put Debit Spread',
                'Synthetic Short'
            ],
            'VOLATILITY': [
                'Put Ratio Spread', 'Put Calendar Spread',
                'Bearish Diagonal Spread'
            ]
        }
        
        self.NEUTRAL_STRATEGIES = {
            'INCOME': [
                'Iron Condor', 'Iron Butterfly', 'Butterfly Spread',
                'Short Straddle', 'Short Strangle'
            ],
            'MOMENTUM': [
                'Straddle', 'Strangle'
            ],
            'VOLATILITY': [
                'Long Straddle', 'Long Strangle', 'Calendar Spread',
                'Diagonal Spread', 'Jade Lizard', 'Broken Wing Butterfly'
            ]
        }
        
        # Risk parameters
        self.MIN_PROBABILITY_SCORE = 0.50
        self.MIN_TOTAL_SCORE = 0.60
        self.MIN_POSITION_SIZE = 25000  # Minimum ₹25k per position
        self.TARGET_DEPLOYMENT = 0.90  # Target 90% capital deployment
        
        self._industry_allocations = {}
        self._all_strategies = []
        self._market_conditions = self.load_market_conditions()
    
    def load_market_conditions(self) -> Dict:
        """Load market conditions from YAML configuration"""
        try:
            config_path = Path(__file__).parent.parent / "market_conditions.yaml"
            with open(config_path, 'r') as file:
                config = yaml.safe_load(file)
            
            # Get market direction
            if config['manual_market_direction']['enabled']:
                market_direction = config['manual_market_direction']['direction']
            else:
                # TODO: Implement automatic market direction calculation
                market_direction = 'neutral'
            
            # Get long/short ratio for this market direction
            long_short_ratio = config['long_short_ratio'][market_direction]
            
            # Get market cap allocations
            market_cap_allocation = config.get('market_cap_allocation', {
                'Large Cap': 45,
                'Mid Cap': 30,
                'Small Cap': 20,
                'Micro Cap': 5
            })
            
            # Get position sizing by market cap
            position_sizing = config.get('position_sizing', {
                'Large Cap': {'min': 50000, 'max': 200000},
                'Mid Cap': {'min': 40000, 'max': 150000},
                'Small Cap': {'min': 30000, 'max': 100000},
                'Micro Cap': {'min': 25000, 'max': 50000}
            })
            
            logger.info(f"Market Direction: {market_direction}")
            logger.info(f"Long/Short Allocation: {long_short_ratio[0]}%/{long_short_ratio[1]}%")
            logger.info(f"Market Cap Allocation: {market_cap_allocation}")
            
            return {
                'direction': market_direction,
                'long_percentage': long_short_ratio[0] / 100,
                'short_percentage': long_short_ratio[1] / 100,
                'market_cap_allocation': market_cap_allocation,
                'position_sizing': position_sizing
            }
            
        except Exception as e:
            logger.error(f"Error loading market conditions: {e}")
            # Default to neutral market
            return {
                'direction': 'neutral',
                'long_percentage': 0.5,
                'short_percentage': 0.5
            }
        
    def load_strategies_with_lot_sizes(self) -> List[StrategyDataEnhanced]:
        """Load strategies with proper lot sizes from strategy_details"""
        try:
            logger.info("Loading strategies with lot sizes...")
            
            # Get strategies with scores above threshold
            strategies_response = self.supabase.table('strategies').select(
                'id, stock_name, strategy_name, net_premium, probability_of_profit, '
                'risk_reward_ratio, total_score, conviction_level, strategy_type, '
                'sector, industry, market_view, component_scores'
            ).gte('total_score', self.MIN_TOTAL_SCORE).execute()
            
            if not strategies_response.data:
                logger.warning("No strategies found")
                return []
            
            strategy_ids = [s['id'] for s in strategies_response.data]
            stock_names = list(set([s['stock_name'] for s in strategies_response.data]))
            
            # Get lot sizes from strategy_details
            details_response = self.supabase.table('strategy_details').select(
                'strategy_id, quantity, strike_price, option_type, setup_type'
            ).in_('strategy_id', strategy_ids).execute()
            
            # Get Greeks
            greeks_response = self.supabase.table('strategy_greek_exposures').select(
                'strategy_id, net_delta, net_gamma, net_theta, net_vega'
            ).in_('strategy_id', strategy_ids).execute()
            
            # Get market cap categories from stock_rankings
            market_cap_response = self.supabase.table('stock_rankings').select(
                'symbol, market_cap_category'
            ).in_('symbol', stock_names).execute()
            
            # Create lookup dictionaries
            lot_sizes = {}
            for detail in details_response.data:
                if detail['strategy_id'] not in lot_sizes:
                    # Use the first leg's quantity as lot size
                    lot_sizes[detail['strategy_id']] = detail['quantity']
            
            greeks_dict = {g['strategy_id']: g for g in greeks_response.data}
            market_cap_dict = {m['symbol']: m['market_cap_category'] for m in market_cap_response.data}
            
            # Build enhanced strategy objects
            strategies = []
            for row in strategies_response.data:
                strategy_id = row['id']
                
                # Get lot size (default to 50 if not found)
                lot_size = lot_sizes.get(strategy_id, 50)
                
                # Get Greeks
                greeks = greeks_dict.get(strategy_id, {})
                
                # Parse JSON fields
                market_view = json.loads(row.get('market_view', '{}')) if row.get('market_view') else {}
                component_scores = json.loads(row.get('component_scores', '{}')) if row.get('component_scores') else {}
                
                # Calculate premium per lot
                net_premium = float(row.get('net_premium', 0))
                premium_per_lot = net_premium * lot_size
                
                # Get market cap category (default to Mid Cap if not found)
                stock_name = row['stock_name']
                market_cap_category = market_cap_dict.get(stock_name, 'Mid Cap')
                
                strategy = StrategyDataEnhanced(
                    strategy_id=strategy_id,
                    stock_name=stock_name,
                    strategy_name=row['strategy_name'],
                    net_premium=net_premium,
                    lot_size=lot_size,
                    probability_of_profit=float(row.get('probability_of_profit', 0)),
                    risk_reward_ratio=float(row.get('risk_reward_ratio', 0)),
                    total_score=float(row.get('total_score', 0)),
                    conviction_level=row.get('conviction_level', 'MEDIUM'),
                    strategy_type=row.get('strategy_type', 'Unknown'),
                    sector=row.get('sector', 'Unknown'),
                    industry=row.get('industry', 'Unknown'),
                    market_cap_category=market_cap_category,
                    net_delta=float(greeks.get('net_delta', 0)),
                    net_gamma=float(greeks.get('net_gamma', 0)),
                    net_theta=float(greeks.get('net_theta', 0)),
                    net_vega=float(greeks.get('net_vega', 0)),
                    component_scores=component_scores,
                    market_view=market_view,
                    premium_per_lot=premium_per_lot
                )
                
                strategies.append(strategy)
            
            logger.info(f"Loaded {len(strategies)} strategies with lot sizes")
            self._all_strategies = strategies
            return strategies
            
        except Exception as e:
            logger.error(f"Error loading strategies: {e}")
            return []
    
    def load_industry_allocations(self) -> Dict[str, Dict]:
        """Load industry allocations with weights and position types"""
        try:
            response = self.supabase.table('industry_allocations_current').select(
                'industry, weight_percentage, position_type'
            ).execute()
            
            # Create industry lookup with weight and position type
            industry_data = {}
            total_weight = 0
            
            for row in response.data:
                industry = row['industry']
                weight = row['weight_percentage'] / 100  # Convert to decimal
                position_type = row['position_type']  # LONG or SHORT
                
                if industry not in industry_data:
                    industry_data[industry] = {
                        'weight': weight,
                        'position_type': position_type
                    }
                else:
                    # If same industry appears twice, take higher weight
                    if weight > industry_data[industry]['weight']:
                        industry_data[industry] = {
                            'weight': weight,
                            'position_type': position_type
                        }
                
                total_weight += weight
            
            # Normalize weights to sum to 1.0
            if total_weight > 0:
                for industry in industry_data:
                    industry_data[industry]['weight'] = industry_data[industry]['weight'] / total_weight
            
            self._industry_allocations = industry_data
            logger.info(f"Loaded {len(industry_data)} industry allocations with position types")
            
            # Log position type breakdown
            long_industries = [ind for ind, data in industry_data.items() if data['position_type'] == 'LONG']
            short_industries = [ind for ind, data in industry_data.items() if data['position_type'] == 'SHORT']
            logger.info(f"LONG industries: {len(long_industries)}, SHORT industries: {len(short_industries)}")
            
            return industry_data
            
        except Exception as e:
            logger.error(f"Error loading industry allocations: {e}")
            return {}
    
    def categorize_strategies_by_tier(self, strategies: List[StrategyDataEnhanced]) -> Dict[str, List[StrategyDataEnhanced]]:
        """Categorize strategies into appropriate tiers based on position type"""
        tier_strategies = {
            'INCOME': [],
            'MOMENTUM': [],
            'VOLATILITY': []
        }
        
        for strategy in strategies:
            # Get industry position type
            industry_info = self._industry_allocations.get(strategy.industry, {})
            position_type = industry_info.get('position_type', 'LONG')
            
            # Determine tier based on strategy name and position type
            tier_assigned = False
            
            # Check bullish strategies for LONG industries
            if position_type == 'LONG':
                for tier, strategy_names in self.BULLISH_STRATEGIES.items():
                    if strategy.strategy_name in strategy_names:
                        tier_strategies[tier].append(strategy)
                        tier_assigned = True
                        break
            
            # Check bearish strategies for SHORT industries
            elif position_type == 'SHORT':
                for tier, strategy_names in self.BEARISH_STRATEGIES.items():
                    if strategy.strategy_name in strategy_names:
                        tier_strategies[tier].append(strategy)
                        tier_assigned = True
                        break
            
            # Check neutral strategies if not assigned
            if not tier_assigned:
                for tier, strategy_names in self.NEUTRAL_STRATEGIES.items():
                    if strategy.strategy_name in strategy_names:
                        tier_strategies[tier].append(strategy)
                        tier_assigned = True
                        break
            
            # If still not assigned, use heuristics based on position type
            if not tier_assigned:
                if position_type == 'LONG':
                    # For LONG industries, only accept bullish strategies
                    if 'Call' in strategy.strategy_name and 'Bear' not in strategy.strategy_name:
                        if strategy.net_premium < 0:
                            tier_strategies['INCOME'].append(strategy)
                        else:
                            tier_strategies['MOMENTUM'].append(strategy)
                    elif 'Put' in strategy.strategy_name and 'Bull' in strategy.strategy_name:
                        tier_strategies['INCOME'].append(strategy)
                
                elif position_type == 'SHORT':
                    # For SHORT industries, only accept bearish strategies
                    if 'Put' in strategy.strategy_name and 'Bull' not in strategy.strategy_name:
                        if strategy.net_premium < 0:
                            tier_strategies['INCOME'].append(strategy)
                        else:
                            tier_strategies['MOMENTUM'].append(strategy)
                    elif 'Call' in strategy.strategy_name and 'Bear' in strategy.strategy_name:
                        tier_strategies['INCOME'].append(strategy)
        
        # Log distribution
        for tier, strategies_list in tier_strategies.items():
            logger.info(f"{tier} tier: {len(strategies_list)} strategies")
        
        return tier_strategies
    
    def allocate_capital_within_tier(self, tier_capital: float, tier_strategies: List[StrategyDataEnhanced], 
                                   tier_name: str) -> List[HybridPosition]:
        """Allocate capital within a tier following industry weights"""
        positions = []
        target_positions = self.TARGET_POSITIONS[tier_name]
        
        # Sort all strategies by quality
        tier_strategies.sort(key=lambda s: (s.total_score, s.probability_of_profit), reverse=True)
        
        # Group strategies by industry
        industry_strategies = {}
        for strategy in tier_strategies:
            industry = strategy.industry
            if industry not in industry_strategies:
                industry_strategies[industry] = []
            industry_strategies[industry].append(strategy)
        
        # Calculate positions per industry based on weights
        industry_positions = {}
        total_weight = sum(data['weight'] for data in self._industry_allocations.values())
        
        for industry, industry_info in self._industry_allocations.items():
            if industry in industry_strategies:
                weight = industry_info['weight']
                # Allocate positions proportional to weight
                positions_for_industry = max(1, int(target_positions * (weight / total_weight)))
                industry_positions[industry] = min(positions_for_industry, self.MAX_POSITIONS_PER_INDUSTRY_TIER)
        
        # Adjust to meet target
        current_total = sum(industry_positions.values())
        if current_total < target_positions:
            # Add more to industries with highest weights
            sorted_industries = sorted(industry_positions.items(), 
                                     key=lambda x: self._industry_allocations.get(x[0], {'weight': 0})['weight'], 
                                     reverse=True)
            for industry, _ in sorted_industries:
                if current_total >= target_positions:
                    break
                if len(industry_strategies[industry]) > industry_positions[industry]:
                    industry_positions[industry] += 1
                    current_total += 1
        
        # Now allocate capital to selected positions
        allocated_so_far = 0
        
        for industry, strategies in industry_strategies.items():
            if industry not in industry_positions or industry_positions[industry] == 0:
                continue
                
            # Get industry weight and capital
            industry_info = self._industry_allocations.get(industry, {'weight': 0.02, 'position_type': 'LONG'})
            industry_weight = industry_info['weight']
            num_positions = industry_positions[industry]
            
            # Select top strategies
            selected_strategies = strategies[:num_positions]
            
            if not selected_strategies:
                continue
            
            # Calculate capital per position
            per_position_capital = tier_capital / target_positions
            
            for strategy in selected_strategies:
                # Ensure minimum position size
                position_capital = max(per_position_capital, self.MIN_POSITION_SIZE)
                
                # Calculate number of lots
                lots = strategy.calculate_lots_required(position_capital)
                
                if lots == 0:
                    continue
                
                # Calculate actual capital deployed
                actual_capital = abs(strategy.premium_per_lot) * lots
                
                # Skip if actual capital is too small
                if actual_capital < self.MIN_POSITION_SIZE:
                    continue
                
                # Calculate expected monthly income (conservative estimates)
                if strategy.net_premium < 0:  # Credit strategy
                    # For credit strategies, income is the premium received
                    # Assume 70% probability of keeping premium
                    monthly_income = abs(strategy.premium_per_lot * lots) * 0.7
                else:  # Debit strategy
                    # For debit strategies, use conservative estimates
                    if tier_name == 'VOLATILITY':
                        # Volatility strategies - target 5-7% monthly return
                        monthly_income = actual_capital * 0.06
                    elif tier_name == 'MOMENTUM':
                        # Momentum strategies - target 4-6% monthly return  
                        monthly_income = actual_capital * 0.05
                    else:
                        # Default conservative 3-5% monthly return
                        monthly_income = actual_capital * 0.04
                
                # Calculate position risk score
                risk_score = self._calculate_position_risk(strategy)
                
                # Calculate Greek contribution
                greek_contribution = {
                    'delta': strategy.net_delta * lots,
                    'gamma': strategy.net_gamma * lots,
                    'theta': strategy.net_theta * lots,
                    'vega': strategy.net_vega * lots
                }
                
                position = HybridPosition(
                    strategy=strategy,
                    tier=tier_name,
                    industry=industry,
                    industry_weight=industry_weight,
                    position_type=industry_info.get('position_type', 'LONG'),
                    allocated_capital=position_capital,
                    number_of_lots=lots,
                    actual_capital_deployed=actual_capital,
                    expected_monthly_income=monthly_income,
                    position_risk_score=risk_score,
                    greek_contribution=greek_contribution
                )
                
                positions.append(position)
                allocated_so_far += actual_capital
        
        return positions
    
    def _calculate_position_risk(self, strategy: StrategyDataEnhanced) -> float:
        """Calculate risk score for a position"""
        # Simple risk scoring based on multiple factors
        risk_factors = []
        
        # Probability risk (inverse)
        risk_factors.append(1 - strategy.probability_of_profit)
        
        # Score risk (inverse)
        risk_factors.append(1 - strategy.total_score)
        
        # Greek risk (normalized)
        greek_risk = (abs(strategy.net_delta) / 100 + 
                     abs(strategy.net_gamma) * 10 + 
                     abs(strategy.net_vega) / 50)
        risk_factors.append(min(greek_risk, 1.0))
        
        # Average risk score
        return np.mean(risk_factors)
    
    def build_hybrid_portfolio(self, total_capital: float) -> Tuple[List[HybridPosition], Dict]:
        """Build portfolio using market cap, tier, and LONG/SHORT allocation"""
        try:
            logger.info(f"Building hybrid portfolio with ₹{total_capital:,.0f}")
            logger.info(f"Market Direction: {self._market_conditions['direction']}")
            
            # Get market cap allocations
            market_cap_allocation = self._market_conditions['market_cap_allocation']
            position_sizing = self._market_conditions['position_sizing']
            
            # Load data
            strategies = self.load_strategies_with_lot_sizes()
            if not strategies:
                raise ValueError("No strategies loaded")
            
            industry_weights = self.load_industry_allocations()
            if not industry_weights:
                logger.warning("No industry weights loaded, using equal weights")
            
            all_positions = []
            total_deployed = 0
            
            # Process allocation by market cap category
            for market_cap, cap_percentage in market_cap_allocation.items():
                cap_allocation = total_capital * (cap_percentage / 100)
                logger.info(f"\n📊 {market_cap}: ₹{cap_allocation:,.0f} ({cap_percentage}%)")
                
                # Get strategies for this market cap
                cap_strategies = [s for s in strategies if s.market_cap_category == market_cap]
                if not cap_strategies:
                    logger.warning(f"No strategies found for {market_cap}")
                    continue
                
                # Separate by position type
                long_strategies = [s for s in cap_strategies if self._industry_allocations.get(s.industry, {}).get('position_type') == 'LONG']
                short_strategies = [s for s in cap_strategies if self._industry_allocations.get(s.industry, {}).get('position_type') == 'SHORT']
                
                # Calculate LONG/SHORT split for this market cap
                long_allocation = cap_allocation * self._market_conditions['long_percentage']
                short_allocation = cap_allocation * self._market_conditions['short_percentage']
                
                # Allocate LONG capital
                if long_strategies and long_allocation > 0:
                    long_positions = self._allocate_market_cap_capital(
                        long_allocation, long_strategies, market_cap, 'LONG', position_sizing[market_cap]
                    )
                    all_positions.extend(long_positions)
                    long_deployed = sum(p.actual_capital_deployed for p in long_positions)
                    logger.info(f"  LONG: {len(long_positions)} positions, ₹{long_deployed:,.0f} deployed")
                
                # Allocate SHORT capital
                if short_strategies and short_allocation > 0:
                    short_positions = self._allocate_market_cap_capital(
                        short_allocation, short_strategies, market_cap, 'SHORT', position_sizing[market_cap]
                    )
                    all_positions.extend(short_positions)
                    short_deployed = sum(p.actual_capital_deployed for p in short_positions)
                    logger.info(f"  SHORT: {len(short_positions)} positions, ₹{short_deployed:,.0f} deployed")
            
            # If deployment is low, do another pass with relaxed constraints
            deployed_capital = sum(p.actual_capital_deployed for p in all_positions)
            deployment_rate = deployed_capital / total_capital
            
            if deployment_rate < self.TARGET_DEPLOYMENT:
                logger.info(f"\n⚠️ Low deployment: {deployment_rate:.1%}. Running second pass...")
                remaining_capital = total_capital - deployed_capital
                additional_positions = self._allocate_remaining_capital(remaining_capital, strategies, all_positions)
                all_positions.extend(additional_positions)
                logger.info(f"Added {len(additional_positions)} positions in second pass")
            
            # Calculate portfolio summary
            summary = self._calculate_portfolio_summary(all_positions, total_capital)
            
            # Add market conditions to summary
            summary['market_conditions'] = self._market_conditions
            summary['long_capital_allocated'] = sum(p.actual_capital_deployed for p in all_positions if p.position_type == 'LONG')
            summary['short_capital_allocated'] = sum(p.actual_capital_deployed for p in all_positions if p.position_type == 'SHORT')
            
            logger.info(f"\n📊 PORTFOLIO SUMMARY:")
            logger.info(f"Total positions: {len(all_positions)}")
            logger.info(f"Capital deployed: ₹{summary['capital_deployed']:,.0f} ({summary['deployment_percentage']:.1f}%)")
            logger.info(f"LONG capital: ₹{summary['long_capital_allocated']:,.0f}")
            logger.info(f"SHORT capital: ₹{summary['short_capital_allocated']:,.0f}")
            logger.info(f"Expected monthly income: ₹{summary['expected_monthly_income']:,.0f}")
            
            return all_positions, summary
            
        except Exception as e:
            logger.error(f"Error building portfolio: {e}")
            raise
    
    def _allocate_market_cap_capital(self, capital: float, strategies: List[StrategyDataEnhanced], 
                                   market_cap: str, position_type: str, sizing_config: Dict) -> List[HybridPosition]:
        """Allocate capital for a specific market cap category"""
        positions = []
        remaining_capital = capital
        min_size = sizing_config['min']
        max_size = sizing_config['max']
        
        # Categorize strategies by tier
        tier_strategies = self.categorize_strategies_by_tier(strategies)
        
        # Allocate across tiers
        for tier_name, tier_percentage in self.TIER_ALLOCATIONS.items():
            tier_capital = capital * tier_percentage
            strategies_in_tier = tier_strategies[tier_name]
            
            if not strategies_in_tier:
                continue
                
            # Sort by quality
            strategies_in_tier.sort(key=lambda s: (s.total_score, s.probability_of_profit), reverse=True)
            
            # Allocate to best strategies
            for strategy in strategies_in_tier:
                if remaining_capital < min_size:
                    break
                    
                # Dynamic position sizing based on score
                score_factor = strategy.total_score  # 0 to 1
                position_size = min_size + (max_size - min_size) * score_factor
                position_size = min(position_size, remaining_capital)
                
                # Calculate lots
                lots = strategy.calculate_lots_required(position_size)
                if lots == 0:
                    continue
                    
                actual_capital = abs(strategy.premium_per_lot) * lots
                if actual_capital < min_size:
                    continue
                
                # Create position
                position = self._create_position(
                    strategy, tier_name, position_size, lots, actual_capital, market_cap
                )
                
                positions.append(position)
                remaining_capital -= actual_capital
                
                # Break if we've deployed enough
                if remaining_capital < min_size:
                    break
        
        return positions
    
    def _allocate_remaining_capital(self, remaining_capital: float, all_strategies: List[StrategyDataEnhanced],
                                   existing_positions: List[HybridPosition]) -> List[HybridPosition]:
        """Allocate remaining capital with relaxed constraints"""
        positions = []
        
        # Get stocks already in portfolio
        existing_stocks = set(p.strategy.stock_name for p in existing_positions)
        
        # Filter out existing stocks and sort by score
        available_strategies = [s for s in all_strategies if s.stock_name not in existing_stocks]
        available_strategies.sort(key=lambda s: s.total_score, reverse=True)
        
        # Try to allocate with progressively lower thresholds
        score_thresholds = [0.65, 0.60, 0.55, 0.50]
        
        for threshold in score_thresholds:
            if remaining_capital < self.MIN_POSITION_SIZE:
                break
                
            for strategy in available_strategies:
                if strategy.total_score < threshold:
                    continue
                    
                if remaining_capital < self.MIN_POSITION_SIZE:
                    break
                    
                # Get position sizing for this market cap
                sizing = self._market_conditions['position_sizing'].get(
                    strategy.market_cap_category, 
                    {'min': 25000, 'max': 100000}
                )
                
                position_size = min(sizing['max'], remaining_capital)
                
                lots = strategy.calculate_lots_required(position_size)
                if lots == 0:
                    continue
                    
                actual_capital = abs(strategy.premium_per_lot) * lots
                if actual_capital < self.MIN_POSITION_SIZE:
                    continue
                
                # Determine tier
                tier = self._determine_strategy_tier(strategy)
                
                position = self._create_position(
                    strategy, tier, position_size, lots, actual_capital, strategy.market_cap_category
                )
                
                positions.append(position)
                remaining_capital -= actual_capital
                existing_stocks.add(strategy.stock_name)
        
        return positions
    
    def _create_position(self, strategy: StrategyDataEnhanced, tier: str, allocated_capital: float,
                        lots: int, actual_capital: float, market_cap: str) -> HybridPosition:
        """Create a position with all necessary calculations"""
        # Get industry info
        industry_info = self._industry_allocations.get(strategy.industry, {})
        industry_weight = industry_info.get('weight', 0.02)
        position_type = industry_info.get('position_type', 'LONG')
        
        # Calculate expected income
        if strategy.net_premium < 0:  # Credit strategy
            monthly_income = abs(strategy.premium_per_lot * lots) * 0.7
        else:  # Debit strategy
            if tier == 'VOLATILITY':
                monthly_income = actual_capital * 0.06
            elif tier == 'MOMENTUM':
                monthly_income = actual_capital * 0.05
            else:
                monthly_income = actual_capital * 0.04
        
        # Calculate risk score
        risk_score = self._calculate_position_risk(strategy)
        
        # Calculate Greek contribution
        greek_contribution = {
            'delta': strategy.net_delta * lots,
            'gamma': strategy.net_gamma * lots,
            'theta': strategy.net_theta * lots,
            'vega': strategy.net_vega * lots
        }
        
        return HybridPosition(
            strategy=strategy,
            tier=tier,
            industry=strategy.industry,
            industry_weight=industry_weight,
            position_type=position_type,
            market_cap_category=market_cap,
            allocated_capital=allocated_capital,
            number_of_lots=lots,
            actual_capital_deployed=actual_capital,
            expected_monthly_income=monthly_income,
            position_risk_score=risk_score,
            greek_contribution=greek_contribution
        )
    
    def _determine_strategy_tier(self, strategy: StrategyDataEnhanced) -> str:
        """Determine which tier a strategy belongs to"""
        # Get position type from industry
        position_type = self._industry_allocations.get(strategy.industry, {}).get('position_type', 'LONG')
        
        # Check each tier
        if position_type == 'LONG':
            for tier, strategies in self.BULLISH_STRATEGIES.items():
                if strategy.strategy_name in strategies:
                    return tier
        elif position_type == 'SHORT':
            for tier, strategies in self.BEARISH_STRATEGIES.items():
                if strategy.strategy_name in strategies:
                    return tier
        
        # Check neutral strategies
        for tier, strategies in self.NEUTRAL_STRATEGIES.items():
            if strategy.strategy_name in strategies:
                return tier
        
        # Default based on characteristics
        if strategy.net_premium < 0:
            return 'INCOME'
        elif 'Call' in strategy.strategy_name or 'Put' in strategy.strategy_name:
            return 'MOMENTUM'
        else:
            return 'VOLATILITY'
    
    def _calculate_portfolio_summary(self, positions: List[HybridPosition], total_capital: float) -> Dict:
        """Calculate portfolio summary statistics"""
        if not positions:
            return {
                'total_positions': 0,
                'capital_deployed': 0,
                'deployment_percentage': 0,
                'expected_monthly_income': 0,
                'monthly_return_percentage': 0
            }
        
        # Basic metrics
        capital_deployed = sum(p.actual_capital_deployed for p in positions)
        expected_income = sum(p.expected_monthly_income for p in positions)
        
        # Tier breakdown
        tier_breakdown = {}
        for tier in self.TIER_ALLOCATIONS:
            tier_positions = [p for p in positions if p.tier == tier]
            tier_breakdown[tier] = {
                'positions': len(tier_positions),
                'capital': sum(p.actual_capital_deployed for p in tier_positions),
                'income': sum(p.expected_monthly_income for p in tier_positions)
            }
        
        # Industry breakdown
        industry_breakdown = {}
        for position in positions:
            industry = position.industry
            if industry not in industry_breakdown:
                industry_breakdown[industry] = {
                    'positions': 0,
                    'capital': 0,
                    'income': 0
                }
            industry_breakdown[industry]['positions'] += 1
            industry_breakdown[industry]['capital'] += position.actual_capital_deployed
            industry_breakdown[industry]['income'] += position.expected_monthly_income
        
        # Market cap breakdown
        market_cap_breakdown = {}
        for position in positions:
            market_cap = position.market_cap_category
            if market_cap not in market_cap_breakdown:
                market_cap_breakdown[market_cap] = {
                    'positions': 0,
                    'capital': 0,
                    'income': 0
                }
            market_cap_breakdown[market_cap]['positions'] += 1
            market_cap_breakdown[market_cap]['capital'] += position.actual_capital_deployed
            market_cap_breakdown[market_cap]['income'] += position.expected_monthly_income
        
        # Portfolio Greeks
        portfolio_greeks = {
            'delta': sum(p.greek_contribution['delta'] for p in positions),
            'gamma': sum(p.greek_contribution['gamma'] for p in positions),
            'theta': sum(p.greek_contribution['theta'] for p in positions),
            'vega': sum(p.greek_contribution['vega'] for p in positions)
        }
        
        return {
            'total_positions': len(positions),
            'capital_deployed': capital_deployed,
            'deployment_percentage': (capital_deployed / total_capital) * 100,
            'expected_monthly_income': expected_income,
            'monthly_return_percentage': (expected_income / total_capital) * 100,
            'tier_breakdown': tier_breakdown,
            'industry_breakdown': industry_breakdown,
            'market_cap_breakdown': market_cap_breakdown,
            'portfolio_greeks': portfolio_greeks,
            'average_position_size': capital_deployed / len(positions) if positions else 0,
            'positions_by_tier': {tier: len([p for p in positions if p.tier == tier]) 
                                for tier in self.TIER_ALLOCATIONS}
        }


# Utility functions
def display_portfolio_results(positions: List[HybridPosition], summary: Dict, total_capital: float):
    """Display portfolio results in a formatted way"""
    print("\n" + "="*80)
    print("🚀 HYBRID PORTFOLIO ALLOCATION RESULTS")
    print("="*80)
    
    # Market conditions
    if 'market_conditions' in summary:
        market_info = summary['market_conditions']
        print(f"\n🌊 MARKET CONDITIONS")
        print(f"Direction: {market_info['direction'].upper()}")
        print(f"Target Allocation: {market_info['long_percentage']*100:.0f}% LONG / {market_info['short_percentage']*100:.0f}% SHORT")
    
    print(f"\n💰 CAPITAL SUMMARY")
    print(f"Total Capital: ₹{total_capital:,.0f}")
    print(f"Capital Deployed: ₹{summary['capital_deployed']:,.0f} ({summary['deployment_percentage']:.1f}%)")
    print(f"Capital Available: ₹{total_capital - summary['capital_deployed']:,.0f}")
    
    # Show long/short breakdown if available
    if 'long_capital_allocated' in summary:
        long_cap = summary['long_capital_allocated']
        short_cap = summary['short_capital_allocated']
        total_deployed = long_cap + short_cap
        if total_deployed > 0:
            print(f"LONG Deployed: ₹{long_cap:,.0f} ({long_cap/total_deployed*100:.1f}%)")
            print(f"SHORT Deployed: ₹{short_cap:,.0f} ({short_cap/total_deployed*100:.1f}%)")
    
    print(f"\n📈 EXPECTED RETURNS")
    print(f"Monthly Income: ₹{summary['expected_monthly_income']:,.0f}")
    print(f"Monthly Return: {summary['monthly_return_percentage']:.2f}%")
    print(f"Annualized Return: {summary['monthly_return_percentage'] * 12:.1f}%")
    
    print(f"\n🎯 TIER BREAKDOWN")
    for tier, data in summary['tier_breakdown'].items():
        print(f"{tier}: {data['positions']} positions, ₹{data['capital']:,.0f} deployed, ₹{data['income']:,.0f} income")
    
    # Show market cap breakdown
    if 'market_cap_breakdown' in summary:
        print(f"\n📊 MARKET CAP BREAKDOWN")
        for market_cap in ['Large Cap', 'Mid Cap', 'Small Cap', 'Micro Cap']:
            if market_cap in summary['market_cap_breakdown']:
                data = summary['market_cap_breakdown'][market_cap]
                print(f"{market_cap}: {data['positions']} positions, ₹{data['capital']:,.0f} deployed ({data['capital']/summary['capital_deployed']*100:.1f}%)")
    
    print(f"\n🏭 TOP INDUSTRIES BY CAPITAL")
    sorted_industries = sorted(summary['industry_breakdown'].items(), 
                             key=lambda x: x[1]['capital'], reverse=True)[:5]
    for industry, data in sorted_industries:
        print(f"{industry}: {data['positions']} positions, ₹{data['capital']:,.0f}")
    
    print(f"\n⚡ PORTFOLIO GREEKS")
    greeks = summary['portfolio_greeks']
    print(f"Delta: {greeks['delta']:.2f}, Gamma: {greeks['gamma']:.4f}, "
          f"Theta: {greeks['theta']:.2f}, Vega: {greeks['vega']:.2f}")
    
    print(f"\n📊 TOP 10 POSITIONS BY CAPITAL")
    print(f"{'Stock':<12} {'Strategy':<20} {'Type':<6} {'Tier':<10} {'Lots':<6} {'Capital':<12} {'Income':<12}")
    print("-"*94)
    
    sorted_positions = sorted(positions, key=lambda p: p.actual_capital_deployed, reverse=True)[:10]
    for pos in sorted_positions:
        print(f"{pos.strategy.stock_name:<12} "
              f"{pos.strategy.strategy_name:<20} "
              f"{pos.position_type:<6} "
              f"{pos.tier:<10} "
              f"{pos.number_of_lots:<6} "
              f"₹{pos.actual_capital_deployed:>10,.0f} "
              f"₹{pos.expected_monthly_income:>10,.0f}")
    
    print("\n" + "="*80)