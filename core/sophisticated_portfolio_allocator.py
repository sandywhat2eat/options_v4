"""
Sophisticated Options Portfolio Allocator
A quantum-level portfolio allocation system with VIX-based strategy selection and intelligent fallbacks.
Equivalent sophistication to the equity Gemini system but optimized for options strategies.
"""

import yaml
import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import json

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class StrategyAllocation:
    """Data class for strategy allocation details"""
    strategy_id: int
    stock_name: str
    strategy_name: str
    strategy_type: str
    allocation_percent: float
    capital_amount: float
    quantum_score: float
    kelly_percent: float
    industry: str
    vix_fit_score: float
    risk_profile: str
    
@dataclass
class PortfolioMetrics:
    """Data class for portfolio-level metrics"""
    total_strategies: int
    total_allocation_percent: float
    total_capital_allocated: float
    expected_return: float
    portfolio_volatility: float
    sharpe_ratio: float
    portfolio_delta: float
    portfolio_gamma: float
    portfolio_theta: float
    portfolio_vega: float
    industry_diversification: int
    strategy_type_diversification: int

class SophisticatedPortfolioAllocator:
    """
    Ultra-sophisticated options portfolio allocator with VIX-based strategy selection,
    intelligent fallbacks, and quantum scoring methodology.
    """
    
    def __init__(self, config_path: str = None, db_integration = None):
        """Initialize the sophisticated allocator"""
        self.config_path = config_path or "config/options_portfolio_config.yaml"
        self.db_integration = db_integration
        self.config = self._load_config()
        self.strategies_df = None
        self.industry_allocations = None
        self.current_vix = None
        self.current_vix_percentile = None
        self.allocated_strategies = []
        
        logger.info("Sophisticated Portfolio Allocator initialized")
    
    def _load_config(self) -> Dict:
        """Load configuration from YAML file"""
        try:
            with open(self.config_path, 'r') as file:
                config = yaml.safe_load(file)
            logger.info(f"Configuration loaded from {self.config_path}")
            return config
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            # Return default config
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict:
        """Fallback default configuration"""
        return {
            'portfolio': {
                'total_capital': 10000000,
                'target_strategies': 30,
                'minimum_allocation_target': 80.0,
                'maximum_individual_allocation': 5.0,
                'maximum_symbol_allocation': 15.0,
                'maximum_industry_allocation': 12.0
            },
            'vix_environments': {'low': 15, 'normal': 25, 'high': 999},
            'quality_thresholds': {
                'minimum_probability_of_profit': 0.40,
                'minimum_risk_reward_ratio': 1.2,
                'minimum_total_score': 0.5
            }
        }
    
    def analyze_market_environment(self) -> Dict:
        """Analyze current market environment focusing on VIX"""
        try:
            # Get VIX data from database or market analyzer
            if self.db_integration:
                vix_data = self._get_vix_from_database()
            else:
                vix_data = self._get_mock_vix_data()
            
            self.current_vix = vix_data['current_vix']
            self.current_vix_percentile = vix_data['vix_percentile']
            
            # Determine VIX environment
            vix_env = self._classify_vix_environment(self.current_vix)
            
            environment = {
                'vix_level': self.current_vix,
                'vix_percentile': self.current_vix_percentile,
                'vix_environment': vix_env,
                'iv_contango': vix_data.get('iv_contango', 0),
                'term_structure_factor': self._calculate_term_structure_factor(vix_data),
                'vix_multiplier': self._get_vix_multiplier(self.current_vix_percentile)
            }
            
            logger.info(f"Market Environment: VIX {self.current_vix} ({vix_env}), "
                       f"Percentile: {self.current_vix_percentile:.1f}")
            
            return environment
            
        except Exception as e:
            logger.error(f"Error analyzing market environment: {e}")
            return self._get_default_environment()
    
    def _classify_vix_environment(self, vix_level: float) -> str:
        """Classify VIX environment based on thresholds"""
        thresholds = self.config['vix_environments']
        
        if vix_level <= thresholds['low']:
            return 'low_vix'
        elif vix_level <= thresholds['normal']:
            return 'normal_vix'
        else:
            return 'high_vix'
    
    def _get_vix_multiplier(self, vix_percentile: float) -> float:
        """Calculate VIX-based strategy multiplier"""
        multipliers = self.config['vix_multipliers']
        
        if vix_percentile < 20:
            return multipliers['premium_selling_bias']
        elif vix_percentile > 80:
            return multipliers['premium_buying_bias']
        else:
            return multipliers['neutral_bias']
    
    def _calculate_term_structure_factor(self, vix_data: Dict) -> float:
        """Calculate term structure factor for strategy weighting"""
        contango = vix_data.get('iv_contango', 0)
        
        if contango > 2:
            return 1.3  # Favor calendar spreads
        elif contango < -2:
            return 0.8  # Disfavor calendar spreads
        else:
            return 1.0  # Neutral
    
    def load_strategies_data(self) -> pd.DataFrame:
        """Load strategies data from database with enhanced filtering"""
        try:
            if self.db_integration:
                # Query strategies with comprehensive data
                strategies_data = self._query_strategies_from_database()
            else:
                strategies_data = self._get_mock_strategies_data()
            
            # Apply quality filters
            strategies_filtered = self._apply_quality_filters(strategies_data)
            
            # Calculate additional metrics
            strategies_enhanced = self._enhance_strategies_data(strategies_filtered)
            
            self.strategies_df = strategies_enhanced
            logger.info(f"Loaded {len(self.strategies_df)} qualified strategies")
            
            return self.strategies_df
            
        except Exception as e:
            logger.error(f"Error loading strategies data: {e}")
            return pd.DataFrame()
    
    def _apply_quality_filters(self, strategies_df: pd.DataFrame) -> pd.DataFrame:
        """Apply quality thresholds to filter strategies"""
        thresholds = self.config['quality_thresholds']
        
        filtered_df = strategies_df[
            (strategies_df['probability_of_profit'] >= thresholds['minimum_probability_of_profit']) &
            (strategies_df['risk_reward_ratio'] >= thresholds['minimum_risk_reward_ratio']) &
            (strategies_df['total_score'] >= thresholds['minimum_total_score'])
        ].copy()
        
        logger.info(f"Quality filter: {len(strategies_df)} → {len(filtered_df)} strategies")
        return filtered_df
    
    def calculate_quantum_scores(self, environment: Dict) -> pd.DataFrame:
        """Calculate sophisticated quantum scores for all strategies"""
        if self.strategies_df is None or self.strategies_df.empty:
            logger.error("No strategies data available for scoring")
            return pd.DataFrame()
        
        df = self.strategies_df.copy()
        
        # Base scoring components (0-100 scale)
        df['probability_component'] = df['probability_of_profit'] * 25
        df['risk_reward_component'] = np.minimum(df['risk_reward_ratio'] * 15, 25)  # Cap at 25
        df['total_score_component'] = df['total_score'] * 20
        
        # Kelly Criterion calculation
        df['kelly_percentage'] = self._calculate_kelly_criterion(df)
        df['kelly_component'] = np.minimum(df['kelly_percentage'] * 15, 15)
        
        # Industry fit scoring
        df['industry_fit_component'] = self._calculate_industry_fit(df)
        
        # Strategy type fit based on VIX environment
        df['strategy_type_fit_component'] = self._calculate_strategy_type_fit(df, environment)
        
        # Liquidity scoring
        df['liquidity_component'] = self._calculate_liquidity_score(df) * 5
        
        # Calculate final quantum score
        df['quantum_score'] = (
            df['probability_component'] +
            df['risk_reward_component'] +
            df['total_score_component'] +
            df['kelly_component'] +
            df['industry_fit_component'] +
            df['strategy_type_fit_component'] +
            df['liquidity_component']
        )
        
        # Apply VIX multiplier
        vix_multiplier = environment['vix_multiplier']
        df['quantum_score'] *= self._get_strategy_vix_multiplier(df, environment)
        
        # Normalize to 0-100 scale
        df['quantum_score'] = np.minimum(df['quantum_score'], 100)
        
        logger.info(f"Quantum scores calculated. Range: {df['quantum_score'].min():.1f} - {df['quantum_score'].max():.1f}")
        
        return df
    
    def _calculate_kelly_criterion(self, df: pd.DataFrame) -> pd.Series:
        """Calculate Kelly Criterion percentage for position sizing"""
        # Kelly = (p * b - q) / b
        # where p = probability of profit, q = 1-p, b = risk/reward ratio
        
        p = df['probability_of_profit']
        b = df['risk_reward_ratio']
        q = 1 - p
        
        kelly = (p * b - q) / b
        kelly = np.maximum(kelly, 0)  # No negative Kelly
        kelly = np.minimum(kelly, 0.25)  # Cap at 25% (conservative)
        
        return kelly
    
    def _calculate_industry_fit(self, df: pd.DataFrame) -> pd.Series:
        """Calculate industry fit component based on allocation weights"""
        # This would integrate with your industry allocation system
        # For now, using a simplified scoring
        
        industry_scores = {}
        if self.industry_allocations is not None:
            for _, row in self.industry_allocations.iterrows():
                industry_scores[row['industry']] = row['weight_percentage'] / 10
        
        # Map strategies to industry scores
        industry_fit = df['stock_name'].map(lambda x: self._get_stock_industry_weight(x))
        return industry_fit.fillna(5.0)  # Default 5.0 if no mapping
    
    def _calculate_strategy_type_fit(self, df: pd.DataFrame, environment: Dict) -> pd.Series:
        """Calculate strategy type fit based on VIX environment"""
        vix_env = environment['vix_environment']
        strategy_targets = self.config['vix_allocation_targets'][vix_env]
        
        # Create strategy type mapping
        strategy_mapping = self.config['strategy_mapping']
        type_scores = {}
        
        # Calculate scores based on tier and allocation
        for tier_name, tier_strategies in strategy_targets.items():
            tier_multiplier = {'tier_1': 1.0, 'tier_2': 0.8, 'tier_3': 0.6}.get(tier_name, 0.5)
            for strategy_type, allocation in tier_strategies.items():
                if strategy_type in strategy_mapping:
                    score = (allocation / 20) * 10 * tier_multiplier  # Scale to 0-10
                    for strategy_name in strategy_mapping[strategy_type]:
                        type_scores[strategy_name] = score
        
        # Map strategies to type scores
        type_fit = df['strategy_name'].map(type_scores)
        return type_fit.fillna(2.0)  # Default 2.0 if no mapping
    
    def _calculate_liquidity_score(self, df: pd.DataFrame) -> pd.Series:
        """Calculate liquidity score (0-1 scale)"""
        # This would use actual OI and volume data
        # For now, using a simplified calculation based on available data
        
        # Use total_score as proxy for liquidity (could be enhanced)
        liquidity_score = df['total_score']
        return liquidity_score
    
    def _get_strategy_vix_multiplier(self, df: pd.DataFrame, environment: Dict) -> pd.Series:
        """Get strategy-specific VIX multipliers"""
        vix_percentile = environment['vix_percentile']
        base_multiplier = environment['vix_multiplier']
        
        # Premium selling strategies get higher multiplier in low VIX
        selling_strategies = ['Iron Condor', 'Butterfly Spread', 'Short Strangle', 
                            'Calendar Spread', 'Cash-Secured Put', 'Covered Call']
        
        # Premium buying strategies get higher multiplier in high VIX
        buying_strategies = ['Long Straddle', 'Long Strangle', 'Long Call', 'Long Put']
        
        multipliers = []
        for _, row in df.iterrows():
            strategy_name = row['strategy_name']
            
            if vix_percentile < 20 and strategy_name in selling_strategies:
                multipliers.append(1.5)
            elif vix_percentile > 80 and strategy_name in buying_strategies:
                multipliers.append(1.5)
            else:
                multipliers.append(1.0)
        
        return pd.Series(multipliers, index=df.index)
    
    def allocate_with_intelligent_fallbacks(self, environment: Dict, strategies_df: pd.DataFrame) -> List[StrategyAllocation]:
        """Core allocation algorithm with intelligent fallback system"""
        
        vix_env = environment['vix_environment']
        target_allocations = self.config['vix_allocation_targets'][vix_env]
        fallback_hierarchy = self.config['fallback_hierarchy'][vix_env]
        strategy_mapping = self.config['strategy_mapping']
        
        allocated_strategies = []
        total_allocated = 0.0
        remaining_capital = 100.0
        
        logger.info(f"Starting allocation for {vix_env} environment")
        
        # Process each tier
        for tier_name, tier_targets in target_allocations.items():
            logger.info(f"Processing {tier_name}")
            
            for strategy_type, target_percent in tier_targets.items():
                if remaining_capital <= 0:
                    break
                
                # Get available strategies for this type
                available_strategies = self._get_available_strategies_for_type(
                    strategy_type, strategies_df, strategy_mapping
                )
                
                if available_strategies.empty:
                    logger.warning(f"No strategies available for {strategy_type}")
                    # Apply fallback logic
                    allocated_amount = self._apply_fallback_allocation(
                        strategy_type, target_percent, strategies_df, 
                        fallback_hierarchy, strategy_mapping, remaining_capital
                    )
                else:
                    # Allocate to available strategies
                    allocated_amount = self._allocate_to_strategy_type(
                        strategy_type, target_percent, available_strategies, 
                        remaining_capital
                    )
                
                # Update tracking
                if allocated_amount > 0:
                    total_allocated += allocated_amount
                    remaining_capital -= allocated_amount
                    logger.info(f"Allocated {allocated_amount:.1f}% to {strategy_type}")
        
        # Final sweep: allocate remaining capital to best available strategies
        if remaining_capital > 10.0:
            final_allocation = self._allocate_remaining_capital(
                strategies_df, remaining_capital
            )
            total_allocated += final_allocation
            remaining_capital -= final_allocation
        
        logger.info(f"Total allocation: {total_allocated:.1f}%, Remaining: {remaining_capital:.1f}%")
        
        return allocated_strategies
    
    def _get_available_strategies_for_type(self, strategy_type: str, strategies_df: pd.DataFrame, 
                                         strategy_mapping: Dict) -> pd.DataFrame:
        """Get available strategies for a specific strategy type"""
        
        if strategy_type not in strategy_mapping:
            return pd.DataFrame()
        
        strategy_names = strategy_mapping[strategy_type]
        available = strategies_df[strategies_df['strategy_name'].isin(strategy_names)]
        
        return available.sort_values('quantum_score', ascending=False)
    
    def _apply_fallback_allocation(self, original_strategy_type: str, target_percent: float,
                                 strategies_df: pd.DataFrame, fallback_hierarchy: Dict,
                                 strategy_mapping: Dict, remaining_capital: float) -> float:
        """Apply fallback hierarchy when primary strategy type unavailable"""
        
        if original_strategy_type not in fallback_hierarchy:
            return 0.0
        
        fallback_strategies = fallback_hierarchy[original_strategy_type]
        allocated_amount = 0.0
        remaining_target = target_percent
        
        for fallback_type in fallback_strategies:
            if remaining_target <= 0 or remaining_capital <= 0:
                break
            
            available_strategies = self._get_available_strategies_for_type(
                fallback_type, strategies_df, strategy_mapping
            )
            
            if not available_strategies.empty:
                # Allocate portion of the target to this fallback
                allocation_amount = min(remaining_target, remaining_capital)
                actual_allocated = self._allocate_to_strategy_type(
                    fallback_type, allocation_amount, available_strategies, remaining_capital
                )
                
                allocated_amount += actual_allocated
                remaining_target -= actual_allocated
                
                logger.info(f"Fallback: {actual_allocated:.1f}% allocated to {fallback_type} "
                           f"(originally {original_strategy_type})")
        
        return allocated_amount
    
    def _allocate_to_strategy_type(self, strategy_type: str, target_percent: float,
                                 available_strategies: pd.DataFrame, remaining_capital: float) -> float:
        """Allocate capital to a specific strategy type"""
        
        if available_strategies.empty or target_percent <= 0:
            return 0.0
        
        # Limit allocation to available capital
        actual_target = min(target_percent, remaining_capital)
        allocated_amount = 0.0
        
        # Sort by quantum score and allocate to top strategies
        top_strategies = available_strategies.head(min(10, len(available_strategies)))
        
        for _, strategy in top_strategies.iterrows():
            if allocated_amount >= actual_target:
                break
            
            # Calculate position size based on Kelly criterion and limits
            kelly_size = strategy['kelly_percentage'] * 100  # Convert to percentage
            max_individual = self.config['portfolio']['maximum_individual_allocation']
            
            position_size = min(kelly_size, max_individual, actual_target - allocated_amount)
            
            if position_size > 0.5:  # Minimum 0.5% position
                # Create strategy allocation
                allocation = StrategyAllocation(
                    strategy_id=strategy['id'],
                    stock_name=strategy['stock_name'],
                    strategy_name=strategy['strategy_name'],
                    strategy_type=strategy['strategy_type'],
                    allocation_percent=position_size,
                    capital_amount=position_size * self.config['portfolio']['total_capital'] / 100,
                    quantum_score=strategy['quantum_score'],
                    kelly_percent=strategy['kelly_percentage'],
                    industry=self._get_stock_industry(strategy['stock_name']),
                    vix_fit_score=strategy.get('strategy_type_fit_component', 0),
                    risk_profile=self._classify_risk_profile(strategy)
                )
                
                self.allocated_strategies.append(allocation)
                allocated_amount += position_size
        
        return allocated_amount
    
    def _allocate_remaining_capital(self, strategies_df: pd.DataFrame, remaining_capital: float) -> float:
        """Allocate remaining capital to best available strategies regardless of type"""
        
        if remaining_capital <= 10.0:
            return 0.0
        
        # Get strategies not already allocated
        allocated_ids = [alloc.strategy_id for alloc in self.allocated_strategies]
        remaining_strategies = strategies_df[~strategies_df['id'].isin(allocated_ids)]
        
        if remaining_strategies.empty:
            return 0.0
        
        # Sort by quantum score and allocate
        best_remaining = remaining_strategies.sort_values('quantum_score', ascending=False)
        allocated_amount = 0.0
        
        for _, strategy in best_remaining.head(10).iterrows():
            if allocated_amount >= remaining_capital:
                break
            
            max_individual = self.config['portfolio']['maximum_individual_allocation']
            position_size = min(max_individual, remaining_capital - allocated_amount)
            
            if position_size > 0.5:
                allocation = StrategyAllocation(
                    strategy_id=strategy['id'],
                    stock_name=strategy['stock_name'],
                    strategy_name=strategy['strategy_name'],
                    strategy_type=strategy['strategy_type'],
                    allocation_percent=position_size,
                    capital_amount=position_size * self.config['portfolio']['total_capital'] / 100,
                    quantum_score=strategy['quantum_score'],
                    kelly_percent=strategy.get('kelly_percentage', 0),
                    industry=self._get_stock_industry(strategy['stock_name']),
                    vix_fit_score=strategy.get('strategy_type_fit_component', 0),
                    risk_profile=self._classify_risk_profile(strategy)
                )
                
                self.allocated_strategies.append(allocation)
                allocated_amount += position_size
        
        logger.info(f"Final sweep: {allocated_amount:.1f}% allocated to remaining strategies")
        return allocated_amount
    
    def calculate_portfolio_metrics(self) -> PortfolioMetrics:
        """Calculate comprehensive portfolio metrics"""
        
        if not self.allocated_strategies:
            return PortfolioMetrics(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        
        total_strategies = len(self.allocated_strategies)
        total_allocation = sum(alloc.allocation_percent for alloc in self.allocated_strategies)
        total_capital = sum(alloc.capital_amount for alloc in self.allocated_strategies)
        
        # Calculate weighted portfolio metrics
        weights = [alloc.allocation_percent / total_allocation for alloc in self.allocated_strategies]
        
        # Expected return (simplified calculation)
        expected_returns = []
        for alloc in self.allocated_strategies:
            # Estimate annual return based on quantum score and strategy type
            base_return = alloc.quantum_score / 100 * 0.5  # Scale quantum score to return
            expected_returns.append(base_return)
        
        portfolio_return = sum(w * r for w, r in zip(weights, expected_returns))
        
        # Portfolio volatility (simplified)
        portfolio_volatility = 0.20  # Default 20% for options portfolio
        
        # Sharpe ratio
        risk_free_rate = 0.06  # 6% risk-free rate
        sharpe_ratio = (portfolio_return - risk_free_rate) / portfolio_volatility
        
        # Greeks (would be calculated from actual option data)
        portfolio_delta = 0.1  # Slight positive delta bias
        portfolio_gamma = 0.05
        portfolio_theta = 1.5   # Positive theta from premium selling
        portfolio_vega = -0.5   # Negative vega from premium selling
        
        # Diversification metrics
        industries = set(alloc.industry for alloc in self.allocated_strategies)
        strategy_types = set(alloc.strategy_type for alloc in self.allocated_strategies)
        
        return PortfolioMetrics(
            total_strategies=total_strategies,
            total_allocation_percent=total_allocation,
            total_capital_allocated=total_capital,
            expected_return=portfolio_return,
            portfolio_volatility=portfolio_volatility,
            sharpe_ratio=sharpe_ratio,
            portfolio_delta=portfolio_delta,
            portfolio_gamma=portfolio_gamma,
            portfolio_theta=portfolio_theta,
            portfolio_vega=portfolio_vega,
            industry_diversification=len(industries),
            strategy_type_diversification=len(strategy_types)
        )
    
    def generate_allocation_report(self) -> Dict:
        """Generate comprehensive allocation report"""
        
        metrics = self.calculate_portfolio_metrics()
        
        # Group allocations by various dimensions
        by_industry = {}
        by_strategy_type = {}
        by_risk_profile = {}
        
        for alloc in self.allocated_strategies:
            # By industry
            industry = alloc.industry
            if industry not in by_industry:
                by_industry[industry] = {'count': 0, 'allocation': 0.0, 'strategies': []}
            by_industry[industry]['count'] += 1
            by_industry[industry]['allocation'] += alloc.allocation_percent
            by_industry[industry]['strategies'].append(alloc.strategy_name)
            
            # By strategy type
            strategy_type = alloc.strategy_type
            if strategy_type not in by_strategy_type:
                by_strategy_type[strategy_type] = {'count': 0, 'allocation': 0.0}
            by_strategy_type[strategy_type]['count'] += 1
            by_strategy_type[strategy_type]['allocation'] += alloc.allocation_percent
            
            # By risk profile
            risk_profile = alloc.risk_profile
            if risk_profile not in by_risk_profile:
                by_risk_profile[risk_profile] = {'count': 0, 'allocation': 0.0}
            by_risk_profile[risk_profile]['count'] += 1
            by_risk_profile[risk_profile]['allocation'] += alloc.allocation_percent
        
        # Top strategies by allocation
        top_strategies = sorted(self.allocated_strategies, 
                              key=lambda x: x.allocation_percent, reverse=True)[:10]
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'portfolio_metrics': {
                'total_strategies': metrics.total_strategies,
                'total_allocation_percent': round(metrics.total_allocation_percent, 2),
                'total_capital_allocated': round(metrics.total_capital_allocated, 0),
                'expected_annual_return': round(metrics.expected_return * 100, 2),
                'portfolio_volatility': round(metrics.portfolio_volatility * 100, 2),
                'sharpe_ratio': round(metrics.sharpe_ratio, 3),
                'portfolio_greeks': {
                    'delta': round(metrics.portfolio_delta, 3),
                    'gamma': round(metrics.portfolio_gamma, 3),
                    'theta': round(metrics.portfolio_theta, 3),
                    'vega': round(metrics.portfolio_vega, 3)
                }
            },
            'allocation_by_industry': {k: {'allocation_percent': round(v['allocation'], 2), 
                                         'strategy_count': v['count']} 
                                       for k, v in by_industry.items()},
            'allocation_by_strategy_type': {k: {'allocation_percent': round(v['allocation'], 2), 
                                              'strategy_count': v['count']} 
                                          for k, v in by_strategy_type.items()},
            'allocation_by_risk_profile': {k: {'allocation_percent': round(v['allocation'], 2), 
                                             'strategy_count': v['count']} 
                                         for k, v in by_risk_profile.items()},
            'top_strategies': [
                {
                    'stock_name': alloc.stock_name,
                    'strategy_name': alloc.strategy_name,
                    'allocation_percent': round(alloc.allocation_percent, 2),
                    'capital_amount': round(alloc.capital_amount, 0),
                    'quantum_score': round(alloc.quantum_score, 1),
                    'kelly_percent': round(alloc.kelly_percent * 100, 1)
                }
                for alloc in top_strategies
            ],
            'market_environment': {
                'vix_level': self.current_vix,
                'vix_percentile': round(self.current_vix_percentile, 1) if self.current_vix_percentile else None,
                'vix_environment': self._classify_vix_environment(self.current_vix or 15)
            }
        }
        
        return report
    
    def execute_allocation(self) -> Dict:
        """Main execution method - orchestrates the entire allocation process"""
        
        logger.info("Starting sophisticated options portfolio allocation")
        
        try:
            # Step 1: Analyze market environment
            environment = self.analyze_market_environment()
            
            # Step 2: Load strategies data
            strategies_df = self.load_strategies_data()
            if strategies_df.empty:
                raise ValueError("No strategies data available")
            
            # Step 3: Calculate quantum scores
            strategies_with_scores = self.calculate_quantum_scores(environment)
            
            # Step 4: Execute allocation with fallbacks
            allocated_strategies = self.allocate_with_intelligent_fallbacks(
                environment, strategies_with_scores
            )
            
            # Step 5: Generate comprehensive report
            report = self.generate_allocation_report()
            
            logger.info(f"Allocation complete: {len(self.allocated_strategies)} strategies, "
                       f"{report['portfolio_metrics']['total_allocation_percent']:.1f}% allocated")
            
            return report
            
        except Exception as e:
            logger.error(f"Error in allocation execution: {e}")
            return {'error': str(e), 'allocated_strategies': 0}
    
    # Helper methods for mock data (to be replaced with actual database queries)
    
    def _get_vix_from_database(self) -> Dict:
        """Get VIX data from database"""
        # This would query your actual VIX data
        return {
            'current_vix': 13.67,
            'vix_percentile': 11.86,
            'iv_contango': 2.5
        }
    
    def _get_mock_vix_data(self) -> Dict:
        """Mock VIX data for testing"""
        return {
            'current_vix': 13.67,
            'vix_percentile': 11.86,
            'iv_contango': 2.5
        }
    
    def _query_strategies_from_database(self) -> pd.DataFrame:
        """Query strategies from actual database"""
        # This would use your actual database integration
        # For now, creating mock data structure
        return self._get_mock_strategies_data()
    
    def _get_mock_strategies_data(self) -> pd.DataFrame:
        """Generate mock strategies data for testing"""
        np.random.seed(42)
        
        symbols = ['RELIANCE', 'INFY', 'TCS', 'HDFCBANK', 'ICICIBANK', 
                  'BPCL', 'OIL', 'MARUTI', 'TATAMOTORS', 'DIXON']
        
        strategies = ['Iron Condor', 'Bull Call Spread', 'Cash-Secured Put', 
                     'Butterfly Spread', 'Calendar Spread', 'Long Straddle',
                     'Covered Call', 'Bear Put Spread']
        
        data = []
        for i in range(50):  # Generate 50 mock strategies
            data.append({
                'id': i + 1,
                'stock_name': np.random.choice(symbols),
                'strategy_name': np.random.choice(strategies),
                'strategy_type': np.random.choice(['Directional', 'Neutral', 'Income', 'Volatility']),
                'probability_of_profit': np.random.uniform(0.3, 0.8),
                'risk_reward_ratio': np.random.uniform(1.0, 3.0),
                'total_score': np.random.uniform(0.4, 0.9),
                'net_premium': np.random.uniform(50, 500),
                'max_profit': np.random.uniform(1000, 5000),
                'max_loss': np.random.uniform(500, 2000)
            })
        
        return pd.DataFrame(data)
    
    def _enhance_strategies_data(self, strategies_df: pd.DataFrame) -> pd.DataFrame:
        """Add calculated fields to strategies data"""
        df = strategies_df.copy()
        
        # Add any additional calculated fields here
        df['kelly_percentage'] = 0.0  # Will be calculated later
        df['quantum_score'] = 0.0     # Will be calculated later
        
        return df
    
    def _get_stock_industry(self, stock_name: str) -> str:
        """Get industry for a stock (mock implementation)"""
        industry_mapping = {
            'RELIANCE': 'Oil Refining/Marketing',
            'BPCL': 'Oil Refining/Marketing',
            'OIL': 'Oil Refining/Marketing',
            'INFY': 'Packaged Software',
            'TCS': 'Packaged Software',
            'HDFCBANK': 'Banking',
            'ICICIBANK': 'Banking',
            'MARUTI': 'Motor Vehicles',
            'TATAMOTORS': 'Motor Vehicles',
            'DIXON': 'Electronic Equipment'
        }
        return industry_mapping.get(stock_name, 'Unknown')
    
    def _get_stock_industry_weight(self, stock_name: str) -> float:
        """Get industry weight for a stock (mock implementation)"""
        industry = self._get_stock_industry(stock_name)
        industry_weights = {
            'Oil Refining/Marketing': 11.5,
            'Packaged Software': 10.8,
            'Banking': 8.5,
            'Motor Vehicles': 10.0,
            'Electronic Equipment': 14.6
        }
        return industry_weights.get(industry, 5.0)
    
    def _classify_risk_profile(self, strategy: pd.Series) -> str:
        """Classify strategy risk profile"""
        if strategy['probability_of_profit'] > 0.7:
            return 'Conservative'
        elif strategy['probability_of_profit'] > 0.5:
            return 'Moderate'
        else:
            return 'Aggressive'
    
    def _get_default_environment(self) -> Dict:
        """Default market environment for fallback"""
        return {
            'vix_level': 15.0,
            'vix_percentile': 50.0,
            'vix_environment': 'normal_vix',
            'iv_contango': 0,
            'term_structure_factor': 1.0,
            'vix_multiplier': 1.0
        }


# Example usage and testing
if __name__ == "__main__":
    # Initialize allocator
    allocator = SophisticatedPortfolioAllocator()
    
    # Execute allocation
    result = allocator.execute_allocation()
    
    # Print results
    print(json.dumps(result, indent=2))