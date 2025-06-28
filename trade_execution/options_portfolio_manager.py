"""
Options Portfolio Manager - Main Integration Controller
Combines market conditions, industry allocations, and strategy selection
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strategy_creation.market_conditions_analyzer import MarketConditionsAnalyzer
from strategy_creation.industry_allocation_engine import IndustryAllocationEngine
try:
    from config.options_config import (
        OPTIONS_TOTAL_EXPOSURE, OPTIONS_RISK_TOLERANCE,
        MARKET_CONDITIONS, STRATEGY_FILTER_THRESHOLDS,
        INTEGRATION_CONFIG
    )
except ImportError:
    # Fallback configuration
    OPTIONS_TOTAL_EXPOSURE = 30000000
    OPTIONS_RISK_TOLERANCE = 'moderate'
    MARKET_CONDITIONS = {
        'Neutral_Normal_VIX': {'preferred_strategies': ['Iron Condors'], 'probability_threshold': 0.30}
    }
    STRATEGY_FILTER_THRESHOLDS = {
        'moderate': {'min_probability': 0.25, 'max_risk_per_trade': 0.05}
    }
    INTEGRATION_CONFIG = {'use_existing_nifty_analysis': True}

logger = logging.getLogger(__name__)

class OptionsPortfolioManager:
    """
    Main controller that orchestrates:
    1. Market condition analysis (NIFTY + VIX + PCR)
    2. Industry-first allocation selection
    3. Strategy selection and position sizing
    4. Portfolio construction and validation
    """
    
    def __init__(self, supabase_client=None, risk_tolerance: str = 'moderate'):
        self.supabase = supabase_client
        self.risk_tolerance = risk_tolerance
        
        # Initialize sub-components
        self.market_analyzer = MarketConditionsAnalyzer(supabase_client)
        self.allocation_engine = IndustryAllocationEngine(supabase_client)
        
        self.current_portfolio = {}
        self.analysis_cache = {}
        
    def analyze_market_environment(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Analyze current market environment using all available data sources
        """
        try:
            cache_key = 'market_environment'
            
            # Check cache first
            if not force_refresh and cache_key in self.analysis_cache:
                cached_data = self.analysis_cache[cache_key]
                if datetime.now() < cached_data['expires_at']:
                    logger.info("Using cached market environment data")
                    return cached_data['data']
            
            logger.info("Analyzing market environment...")
            
            # Get market conditions from analyzer
            market_conditions = self.market_analyzer.get_current_market_condition()
            
            # Extract key components
            condition = market_conditions.get('condition', 'Neutral_Normal_VIX')
            confidence = market_conditions.get('confidence', 0.5)
            components = market_conditions.get('components', {})
            
            # Get market configuration
            market_config = MARKET_CONDITIONS.get(condition, MARKET_CONDITIONS['Neutral_Normal_VIX'])
            
            # Prepare comprehensive analysis
            market_analysis = {
                'condition': condition,
                'confidence': confidence,
                'config': market_config,
                'components': {
                    'nifty_direction': components.get('nifty', {}).get('direction', 'neutral'),
                    'nifty_confidence': components.get('nifty', {}).get('confidence', 0.5),
                    'vix_level': components.get('vix', {}).get('level', 'normal'),
                    'vix_current': components.get('vix', {}).get('current_vix'),
                    'vix_percentile': components.get('vix', {}).get('percentile', 50),
                    'pcr': components.get('options', {}).get('pcr', 1.0),
                    'options_sentiment': components.get('options', {}).get('sentiment', 'neutral'),
                    'max_pain': components.get('options', {}).get('max_pain')
                },
                'strategy_preferences': {
                    'preferred': market_config.get('preferred_strategies', []),
                    'avoid': market_config.get('avoid_strategies', []),
                    'time_preference': market_config.get('time_preference', 'medium_term'),
                    'probability_threshold': market_config.get('probability_threshold', 0.30),
                    'iv_preference': market_config.get('iv_preference', 'neutral')
                },
                'risk_assessment': self._assess_market_risk(condition, confidence, components),
                'last_updated': datetime.now(),
                'next_update_due': datetime.now() + timedelta(hours=2)
            }
            
            # Cache the analysis
            self.analysis_cache[cache_key] = {
                'data': market_analysis,
                'expires_at': datetime.now() + timedelta(hours=1)
            }
            
            logger.info(f"Market analysis complete: {condition} (confidence: {confidence:.2f})")
            return market_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing market environment: {e}")
            return {
                'condition': 'Neutral_Normal_VIX',
                'confidence': 0.5,
                'error': str(e),
                'last_updated': datetime.now()
            }
    
    def generate_options_allocation(self, max_industries: int = 8) -> Dict[str, Any]:
        """
        Generate industry-based options allocation
        """
        try:
            logger.info("Generating options allocation based on industry weights...")
            
            # Get current market environment
            market_analysis = self.analyze_market_environment()
            
            # Generate portfolio allocation
            allocation = self.allocation_engine.generate_portfolio_allocation(
                market_condition=market_analysis,
                risk_tolerance=self.risk_tolerance,
                max_industries=max_industries
            )
            
            if 'error' in allocation:
                logger.error(f"Failed to generate allocation: {allocation['error']}")
                return allocation
            
            # Validate allocation
            validation = self.allocation_engine.validate_portfolio_allocation(allocation)
            
            # Add market context to allocation
            allocation['market_context'] = {
                'condition': market_analysis['condition'],
                'confidence': market_analysis['confidence'],
                'nifty_direction': market_analysis['components']['nifty_direction'],
                'vix_level': market_analysis['components']['vix_level'],
                'pcr': market_analysis['components']['pcr'],
                'strategy_bias': market_analysis['strategy_preferences']
            }
            
            allocation['validation'] = validation
            
            # Store in current portfolio
            self.current_portfolio = allocation
            
            logger.info(f"Generated allocation for {allocation['summary']['total_industries']} industries")
            logger.info(f"Total strategies: {allocation['summary']['total_strategies']}")
            logger.info(f"Capital allocation: ₹{allocation['summary']['total_allocated_capital']:,.0f} ({allocation['summary']['allocation_percentage']:.1f}%)")
            
            return allocation
            
        except Exception as e:
            logger.error(f"Error generating options allocation: {e}")
            return {'error': str(e)}
    
    def get_priority_symbols_for_analysis(self, limit: int = 10) -> List[Dict]:
        """
        Get priority symbols for options analysis based on industry allocation
        """
        try:
            if not self.current_portfolio:
                allocation = self.generate_options_allocation()
                if 'error' in allocation:
                    return []
            else:
                allocation = self.current_portfolio
            
            priority_symbols = []
            
            for industry_alloc in allocation['industry_allocations']:
                industry = industry_alloc['industry']
                weight_pct = industry_alloc['weight_percentage']
                position_type = industry_alloc['position_type']
                symbols = industry_alloc['symbols']
                strategies = industry_alloc['strategies']
                
                for symbol in symbols:
                    for strategy in strategies:
                        priority_symbols.append({
                            'symbol': symbol,
                            'industry': industry,
                            'weight_percentage': weight_pct,
                            'position_type': position_type,
                            'preferred_strategy': strategy['strategy_name'],
                            'priority_score': strategy['priority_score'],
                            'recommended_capital': strategy['recommended_capital'],
                            'risk_percentage': strategy['risk_percentage']
                        })
            
            # Sort by priority score and limit
            priority_symbols.sort(key=lambda x: x['priority_score'], reverse=True)
            return priority_symbols[:limit]
            
        except Exception as e:
            logger.error(f"Error getting priority symbols: {e}")
            return []
    
    def get_strategy_preferences_for_symbol(self, symbol: str) -> Dict[str, Any]:
        """
        Get strategy preferences for a specific symbol based on its industry allocation
        """
        try:
            # Get symbol's industry
            if symbol not in self.allocation_engine.symbol_industry_mapping:
                # Load mapping if not available
                self.allocation_engine.load_allocation_data()
            
            industry = self.allocation_engine.symbol_industry_mapping.get(symbol)
            if not industry:
                logger.warning(f"Industry not found for symbol {symbol}")
                return self._get_default_strategy_preferences()
            
            # Find industry allocation
            if not self.current_portfolio:
                self.generate_options_allocation()
            
            industry_preferences = None
            for industry_alloc in self.current_portfolio.get('industry_allocations', []):
                if industry_alloc['industry'] == industry:
                    industry_preferences = industry_alloc
                    break
            
            if not industry_preferences:
                logger.warning(f"No allocation found for industry {industry}")
                return self._get_default_strategy_preferences()
            
            # Get market context
            market_context = self.current_portfolio.get('market_context', {})
            
            # Prepare strategy preferences
            preferences = {
                'symbol': symbol,
                'industry': industry,
                'industry_weight': industry_preferences['weight_percentage'],
                'position_type': industry_preferences['position_type'],
                'rating': industry_preferences['rating'],
                'preferred_strategies': [s['strategy_name'] for s in industry_preferences['strategies']],
                'strategy_details': industry_preferences['strategies'],
                'market_condition': market_context.get('condition', 'Neutral_Normal_VIX'),
                'market_bias': market_context.get('strategy_bias', {}),
                'position_sizing': {
                    'max_capital_per_strategy': max([s['recommended_capital'] for s in industry_preferences['strategies']], default=0),
                    'risk_tolerance': self.risk_tolerance,
                    'industry_allocation_pct': industry_preferences['weight_percentage']
                },
                'filters': STRATEGY_FILTER_THRESHOLDS[self.risk_tolerance]
            }
            
            return preferences
            
        except Exception as e:
            logger.error(f"Error getting strategy preferences for {symbol}: {e}")
            return self._get_default_strategy_preferences()
    
    def update_portfolio_with_analysis_results(self, symbol: str, analysis_results: Dict) -> bool:
        """
        Update portfolio with completed analysis results
        """
        try:
            if 'top_strategies' not in analysis_results:
                logger.warning(f"No strategies found in analysis results for {symbol}")
                return False
            
            # Find symbol in current portfolio
            symbol_found = False
            for industry_alloc in self.current_portfolio.get('industry_allocations', []):
                if symbol in industry_alloc['symbols']:
                    # Add analysis results
                    if 'analysis_results' not in industry_alloc:
                        industry_alloc['analysis_results'] = {}
                    
                    industry_alloc['analysis_results'][symbol] = {
                        'strategies_found': len(analysis_results['top_strategies']),
                        'best_strategy': analysis_results['top_strategies'][0]['name'] if analysis_results['top_strategies'] else None,
                        'best_score': analysis_results['top_strategies'][0]['total_score'] if analysis_results['top_strategies'] else None,
                        'success': analysis_results.get('success', False),
                        'analyzed_at': datetime.now().isoformat(),
                        'full_results': analysis_results
                    }
                    symbol_found = True
                    break
            
            if not symbol_found:
                logger.warning(f"Symbol {symbol} not found in current portfolio allocation")
                return False
            
            logger.info(f"Updated portfolio with analysis results for {symbol}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating portfolio with analysis results: {e}")
            return False
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive portfolio summary
        """
        try:
            if not self.current_portfolio:
                return {'error': 'No portfolio generated yet'}
            
            summary = {
                'portfolio_overview': self.current_portfolio['summary'],
                'market_context': self.current_portfolio.get('market_context', {}),
                'validation_status': self.current_portfolio.get('validation', {}),
                'industry_breakdown': [],
                'symbol_analysis_status': {},
                'overall_statistics': {
                    'total_symbols': 0,
                    'analyzed_symbols': 0,
                    'successful_analyses': 0,
                    'analysis_completion_rate': 0.0
                }
            }
            
            total_symbols = 0
            analyzed_symbols = 0
            successful_analyses = 0
            
            for industry_alloc in self.current_portfolio['industry_allocations']:
                industry_summary = {
                    'industry': industry_alloc['industry'],
                    'weight_percentage': industry_alloc['weight_percentage'],
                    'position_type': industry_alloc['position_type'],
                    'rating': industry_alloc['rating'],
                    'total_capital': industry_alloc['total_industry_capital'],
                    'strategy_count': len(industry_alloc['strategies']),
                    'symbol_count': len(industry_alloc['symbols']),
                    'symbols': industry_alloc['symbols']
                }
                
                # Add analysis status if available
                analysis_results = industry_alloc.get('analysis_results', {})
                industry_summary['analysis_status'] = {
                    'completed': len(analysis_results),
                    'successful': sum(1 for r in analysis_results.values() if r.get('success', False)),
                    'pending': len(industry_alloc['symbols']) - len(analysis_results)
                }
                
                summary['industry_breakdown'].append(industry_summary)
                summary['symbol_analysis_status'].update(analysis_results)
                
                # Update overall stats
                total_symbols += len(industry_alloc['symbols'])
                analyzed_symbols += len(analysis_results)
                successful_analyses += sum(1 for r in analysis_results.values() if r.get('success', False))
            
            # Calculate completion rate
            summary['overall_statistics'] = {
                'total_symbols': total_symbols,
                'analyzed_symbols': analyzed_symbols,
                'successful_analyses': successful_analyses,
                'analysis_completion_rate': (analyzed_symbols / total_symbols * 100) if total_symbols > 0 else 0.0,
                'success_rate': (successful_analyses / analyzed_symbols * 100) if analyzed_symbols > 0 else 0.0
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating portfolio summary: {e}")
            return {'error': str(e)}
    
    def save_portfolio_to_file(self, filename: Optional[str] = None) -> str:
        """
        Save current portfolio allocation to JSON file
        """
        try:
            if not self.current_portfolio:
                raise ValueError("No portfolio to save")
            
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"options_portfolio_allocation_{timestamp}.json"
            
            filepath = f"results/{filename}"
            
            # Add metadata
            portfolio_with_metadata = {
                'metadata': {
                    'generated_at': datetime.now().isoformat(),
                    'risk_tolerance': self.risk_tolerance,
                    'total_exposure': OPTIONS_TOTAL_EXPOSURE,
                    'system_version': 'Options V4 - Industry Allocation'
                },
                'portfolio': self.current_portfolio
            }
            
            with open(filepath, 'w') as f:
                json.dump(portfolio_with_metadata, f, indent=2, default=str)
            
            logger.info(f"Portfolio saved to {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error saving portfolio: {e}")
            return ""
    
    def _assess_market_risk(self, condition: str, confidence: float, components: Dict) -> Dict:
        """Assess overall market risk level"""
        risk_factors = []
        
        # VIX-based risk
        vix_level = components.get('vix', {}).get('level', 'normal')
        if vix_level in ['high', 'spike']:
            risk_factors.append('High volatility environment')
        
        # PCR-based risk
        pcr = components.get('options', {}).get('pcr', 1.0)
        if pcr > 1.5:
            risk_factors.append('Extreme bearish sentiment')
        elif pcr < 0.6:
            risk_factors.append('Extreme bullish sentiment')
        
        # Confidence-based risk
        if confidence < 0.6:
            risk_factors.append('Low confidence in market direction')
        
        # Overall risk level
        if len(risk_factors) >= 3:
            risk_level = 'HIGH'
        elif len(risk_factors) >= 1:
            risk_level = 'MEDIUM'
        else:
            risk_level = 'LOW'
        
        return {
            'level': risk_level,
            'factors': risk_factors,
            'score': len(risk_factors),
            'recommendation': self._get_risk_recommendation(risk_level)
        }
    
    def _get_risk_recommendation(self, risk_level: str) -> str:
        """Get risk management recommendation"""
        recommendations = {
            'LOW': 'Normal position sizing, consider moderately aggressive strategies',
            'MEDIUM': 'Reduce position sizes by 25%, focus on higher probability strategies',
            'HIGH': 'Reduce position sizes by 50%, focus on defensive strategies only'
        }
        return recommendations.get(risk_level, 'Exercise caution')
    
    def _get_default_strategy_preferences(self) -> Dict[str, Any]:
        """Get default strategy preferences when industry mapping fails"""
        return {
            'symbol': 'UNKNOWN',
            'industry': 'UNKNOWN',
            'preferred_strategies': ['Iron Condors', 'Bull Put Spreads'],
            'market_condition': 'Neutral_Normal_VIX',
            'position_sizing': {
                'max_capital_per_strategy': OPTIONS_TOTAL_EXPOSURE * 0.02,
                'risk_tolerance': self.risk_tolerance
            },
            'filters': STRATEGY_FILTER_THRESHOLDS[self.risk_tolerance]
        }