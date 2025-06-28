"""
Main orchestrator for Options V4 trading system

This replaces the monolithic 2728-line script with a clean, modular architecture.
"""

import os
import sys
import json
from datetime import datetime
from typing import Dict, List, Optional
import numpy as np
from decimal import Decimal

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import our modules
from strategy_creation import DataManager, IVAnalyzer, ProbabilityEngine, RiskManager, StockProfiler
from trade_execution import ExitManager
from strategy_creation import MarketAnalyzer
from analysis import StrategyRanker, PriceLevelsAnalyzer
from strategy_creation.strategies import (
    # Directional
    LongCall, LongPut, BullCallSpread, BearCallSpread, 
    BullPutSpreadStrategy, BearPutSpreadStrategy,
    # Neutral
    IronCondor, ButterflySpread, IronButterfly,
    # Volatility
    LongStraddle, ShortStraddle, LongStrangle, ShortStrangle,
    # Income
    CashSecuredPut, CoveredCall,
    # Advanced
    CalendarSpread, DiagonalSpread, CallRatioSpread, PutRatioSpread,
    JadeLizard, BrokenWingButterfly
)
from strategy_creation.strategies.strategy_metadata import (
    get_compatible_strategies, 
    get_strategy_metadata,
    calculate_strategy_score,
    STRATEGY_REGISTRY
)
from utils.logger import setup_logger, get_default_log_file
from database import SupabaseIntegration

# Load environment variables
if DOTENV_AVAILABLE:
    load_dotenv()

class NumpyJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle numpy types and NaN values"""
    
    def default(self, obj):
        if isinstance(obj, (np.integer, np.int64)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64)):
            if np.isnan(obj) or np.isinf(obj):
                return None  # Convert NaN/Inf to null
            return float(obj)
        elif isinstance(obj, (np.bool_, bool)):
            return bool(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, (datetime,)):
            return obj.isoformat()
        return super().default(obj)

class OptionsAnalyzer:
    """
    Main orchestrator for the Options V4 trading system
    
    Replaces the monolithic script with clean, modular architecture
    """
    
    def __init__(self, config_path: str = None, enable_database: bool = True):
        # Set up logging
        self.logger = setup_logger(
            'OptionsV4',
            log_file=get_default_log_file('options_v4_main')
        )
        
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Initialize database integration first if enabled
        self.enable_database = enable_database
        self.db_integration = None
        if self.enable_database:
            try:
                self.db_integration = SupabaseIntegration(self.logger)
                self.logger.info("Database integration enabled")
            except Exception as e:
                self.logger.warning(f"Database integration failed to initialize: {e}")
                self.db_integration = None
        
        # Initialize core components
        self.data_manager = DataManager()
        self.iv_analyzer = IVAnalyzer()
        self.price_levels_analyzer = PriceLevelsAnalyzer()
        self.probability_engine = ProbabilityEngine()
        self.risk_manager = RiskManager()
        # Pass supabase client to stock profiler if available
        supabase_client = self.db_integration.client if self.db_integration else None
        self.stock_profiler = StockProfiler(supabase_client=supabase_client)
        self.market_analyzer = MarketAnalyzer()
        self.strategy_ranker = StrategyRanker()
        self.exit_manager = ExitManager()
        
        # Import and initialize strike selector for expiry logic
        try:
            from strategy_creation.strike_selector import IntelligentStrikeSelector
            self.strike_selector = IntelligentStrikeSelector(self.stock_profiler)
        except ImportError:
            self.logger.warning("Strike selector not available")
            self.strike_selector = None
        
        # Strategy mapping
        self.strategy_classes = {
            'Long Call': LongCall,
            'Long Put': LongPut,
            'Bull Call Spread': BullCallSpread,
            'Bear Call Spread': BearCallSpread,
            'Bull Put Spread': BullPutSpreadStrategy,
            'Bear Put Spread': BearPutSpreadStrategy,
            'Iron Condor': IronCondor,
            'Long Straddle': LongStraddle,
            'Short Straddle': ShortStraddle,
            'Long Strangle': LongStrangle,
            'Short Strangle': ShortStrangle,
            'Butterfly Spread': ButterflySpread,
            'Iron Butterfly': IronButterfly,
            'Calendar Spread': CalendarSpread,
            'Diagonal Spread': DiagonalSpread,
            'Call Ratio Spread': CallRatioSpread,
            'Put Ratio Spread': PutRatioSpread,
            'Jade Lizard': JadeLizard,
            'Broken Wing Butterfly': BrokenWingButterfly,
            'Cash-Secured Put': CashSecuredPut,
            'Covered Call': CoveredCall
        }
        
        self.logger.info("Options V4 Analyzer initialized successfully")
    
    def analyze_portfolio(self, risk_tolerance: str = 'moderate') -> Dict:
        """
        Analyze entire portfolio and generate strategy recommendations
        
        Args:
            risk_tolerance: Risk tolerance level (conservative/moderate/aggressive)
        
        Returns:
            Dictionary with portfolio analysis and recommendations
        """
        try:
            self.logger.info("Starting portfolio analysis...")
            
            # Get portfolio symbols
            symbols = self.data_manager.get_portfolio_symbols()
            if not symbols:
                self.logger.error("No symbols found in portfolio")
                return {'success': False, 'reason': 'No portfolio symbols'}
            
            self.logger.info(f"Analyzing {len(symbols)} symbols: {symbols}")
            
            portfolio_results = {}
            successful_analyses = 0
            
            for symbol in symbols:
                self.logger.info(f"\n{'='*50}")
                self.logger.info(f"Analyzing {symbol}")
                self.logger.info(f"{'='*50}")
                
                try:
                    symbol_result = self.analyze_symbol(symbol, risk_tolerance)
                    portfolio_results[symbol] = symbol_result
                    
                    if symbol_result.get('success', False):
                        successful_analyses += 1
                        self.logger.info(f"✅ {symbol} analysis completed successfully")
                        
                        # Store individual symbol result in database immediately
                        if self.enable_database and self.db_integration:
                            try:
                                # Wrap single symbol result for database storage
                                single_symbol_result = {
                                    'success': True,
                                    'analysis_timestamp': symbol_result.get('analysis_timestamp'),
                                    'symbol_results': {symbol: symbol_result},
                                    'total_symbols': 1,
                                    'successful_analyses': 1
                                }
                                db_result = self.db_integration.store_analysis_results(single_symbol_result)
                                if db_result['success']:
                                    self.logger.info(f"💾 Stored {db_result['total_stored']} strategies for {symbol} in database")
                                else:
                                    self.logger.warning(f"💾 Database storage failed for {symbol}: {db_result.get('error', 'Unknown error')}")
                            except Exception as e:
                                self.logger.error(f"💾 Error storing {symbol} to database: {e}")
                    else:
                        self.logger.warning(f"⚠️ {symbol} analysis failed: {symbol_result.get('reason', 'Unknown')}")
                
                except Exception as e:
                    self.logger.error(f"❌ Error analyzing {symbol}: {e}")
                    portfolio_results[symbol] = {
                        'success': False,
                        'reason': f'Analysis error: {str(e)}'
                    }
            
            # Generate portfolio summary
            portfolio_summary = self._generate_portfolio_summary(portfolio_results)
            
            self.logger.info(f"\nPortfolio Analysis Complete: {successful_analyses}/{len(symbols)} successful")
            
            return {
                'success': True,
                'analysis_timestamp': datetime.now().isoformat(),
                'portfolio_summary': portfolio_summary,
                'symbol_results': portfolio_results,
                'total_symbols': len(symbols),
                'successful_analyses': successful_analyses
            }
            
        except Exception as e:
            self.logger.error(f"Error in portfolio analysis: {e}")
            return {'success': False, 'reason': str(e)}
    
    def analyze_symbol(self, symbol: str, risk_tolerance: str = 'moderate') -> Dict:
        """
        Analyze single symbol and generate strategy recommendations
        
        Args:
            symbol: Stock symbol to analyze
            risk_tolerance: Risk tolerance level
        
        Returns:
            Dictionary with symbol analysis and top strategies
        """
        try:
            # 1. Fetch market data
            options_df = self.data_manager.get_liquid_options(symbol)
            if options_df is None or options_df.empty:
                return {'success': False, 'reason': 'No liquid options data'}
            
            spot_price = self.data_manager.get_spot_price(symbol)
            if spot_price is None:
                return {'success': False, 'reason': 'No spot price data'}
            
            self.logger.info(f"Found {len(options_df)} liquid options for {symbol} at spot ${spot_price:.2f}")
            
            # 2. Stock Profile Analysis
            stock_profile = self.stock_profiler.get_complete_profile(symbol)
            self.logger.info(f"Stock Profile: {stock_profile['volatility_bucket']} volatility, "
                           f"Beta: {stock_profile.get('beta_nifty', 1.0):.2f}, "
                           f"ATR%: {stock_profile.get('atr_pct', 2.0):.2f}%")
            
            # 3. Market Analysis (enhanced with stock profile)
            market_analysis = self.market_analyzer.analyze_market_direction(
                symbol, options_df, spot_price
            )
            # Add stock profile to market analysis
            market_analysis['stock_profile'] = stock_profile
            
            # 4. IV Analysis
            # Get sector info from stock profile
            sector = stock_profile.get('sector', 'Unknown')
            iv_analysis = self.iv_analyzer.analyze_current_iv(options_df, symbol, sector)
            market_analysis['iv_analysis'] = iv_analysis
            
            # 3.5 Price Levels Analysis
            price_levels = self.price_levels_analyzer.analyze_price_levels(
                symbol, options_df, spot_price
            )
            market_analysis['price_levels'] = price_levels
            market_analysis['spot_price'] = spot_price  # Add spot price for exit calculations
            
            self.logger.info(f"Market Direction: {market_analysis['direction']} {market_analysis['sub_category']} "
                           f"(Confidence: {market_analysis['confidence']:.1%})")
            self.logger.info(f"IV Environment: {iv_analysis['iv_environment']} "
                           f"(ATM IV: {iv_analysis['atm_iv']:.1f}%)")
            
            # 4. Strategy Construction
            strategies = self._construct_strategies(symbol, options_df, spot_price, market_analysis)
            
            if not strategies:
                return {'success': False, 'reason': 'No strategies could be constructed'}
            
            # 5. Strategy Ranking with Probability Filtering
            ranked_strategies = self.strategy_ranker.rank_strategies(
                strategies, market_analysis, risk_tolerance
            )
            
            if not ranked_strategies:
                return {'success': False, 'reason': 'No strategies passed probability filtering'}
            
            # 6. Select top strategies
            top_strategies = ranked_strategies[:3]  # Top 3 strategies
            
            self.logger.info(f"Generated {len(strategies)} strategies, {len(ranked_strategies)} passed filters")
            
            # 7. Generate exit conditions for top strategies
            top_strategies_with_exits = []
            for i, (strategy_name, strategy_data) in enumerate(top_strategies):
                # Generate exit conditions
                exit_conditions = self.exit_manager.generate_exit_conditions(
                    strategy_name, strategy_data, market_analysis
                )
                
                strategy_result = {
                    'rank': i + 1,
                    'name': strategy_name,
                    'total_score': strategy_data['total_score'],
                    'probability_profit': strategy_data['probability_profit'],
                    'max_profit': strategy_data.get('max_profit', 0),
                    'max_loss': strategy_data.get('max_loss', 0),
                    'legs': strategy_data.get('legs', []),
                    'optimal_outcome': strategy_data.get('optimal_outcome', ''),
                    'component_scores': strategy_data.get('component_scores', {}),
                    'exit_conditions': exit_conditions
                }
                top_strategies_with_exits.append(strategy_result)
            
            return {
                'success': True,
                'symbol': symbol,
                'spot_price': spot_price,
                'market_analysis': market_analysis,
                'price_levels': price_levels,
                'total_strategies_generated': len(strategies),
                'strategies_after_filtering': len(ranked_strategies),
                'top_strategies': top_strategies_with_exits
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing symbol {symbol}: {e}")
            return {'success': False, 'reason': str(e)}
    
    def _construct_strategies(self, symbol: str, options_df, spot_price: float, 
                            market_analysis: Dict) -> Dict:
        """Construct multiple strategies for evaluation"""
        try:
            strategies = {}
            direction = market_analysis.get('direction', 'Neutral').lower()
            confidence = market_analysis.get('confidence', 0.5)
            iv_env = market_analysis.get('iv_analysis', {}).get('iv_environment', 'NORMAL')
            
            # Strategy selection based on market conditions and stock profile
            stock_profile = market_analysis.get('stock_profile')
            strategies_to_try = self._select_strategies_to_construct(
                direction, confidence, iv_env, stock_profile
            )
            
            self.logger.info(f"Constructing {len(strategies_to_try)} strategies: {strategies_to_try}")
            
            for strategy_name in strategies_to_try:
                try:
                    if strategy_name in self.strategy_classes:
                        strategy_class = self.strategy_classes[strategy_name]
                        
                        # Get lot size for this symbol
                        lot_size = self.data_manager.get_lot_size(symbol)
                        
                        # Pass market analysis to strategy for intelligent strike selection
                        strategy_instance = strategy_class(symbol, spot_price, options_df, lot_size, market_analysis)
                        
                        # Construct strategy with appropriate parameters
                        result = self._construct_single_strategy(strategy_instance, strategy_name, market_analysis)
                        
                        if result.get('success', False):
                            strategies[strategy_name] = result
                            self.logger.debug(f"✅ {strategy_name} constructed successfully")
                        else:
                            self.logger.debug(f"⚠️ {strategy_name} construction failed: {result.get('reason', 'Unknown')}")
                
                except Exception as e:
                    self.logger.warning(f"Error constructing {strategy_name}: {e}")
                    continue
            
            return strategies
            
        except Exception as e:
            self.logger.error(f"Error in strategy construction: {e}")
            return {}
    
    def _select_strategies_to_construct(self, direction: str, confidence: float, iv_env: str, 
                                       stock_profile: Optional[Dict] = None) -> List[str]:
        """Select strategies using metadata-based intelligent selection with volatility profiles"""
        try:
            # If stock profile is available, use its strategy preferences
            if stock_profile:
                strategy_prefs = self.stock_profiler.get_strategy_preferences(
                    stock_profile['symbol'], stock_profile
                )
                preferred_strategies = strategy_prefs.get('preferred_strategies', [])
                avoid_strategies = strategy_prefs.get('avoid_strategies', [])
                
                self.logger.info(f"Stock volatility profile suggests: "
                               f"Preferred: {preferred_strategies}, Avoid: {avoid_strategies}")
            else:
                preferred_strategies = []
                avoid_strategies = []
            
            # Get compatible strategies from metadata
            compatible_strategies = get_compatible_strategies(
                market_view=direction,
                iv_env=iv_env
            )
            
            # Score each compatible strategy
            strategy_scores = {}
            
            # Build portfolio context for diversity scoring
            portfolio_context = {
                'existing_categories': set(),  # Could track across portfolio
                'market_confidence': confidence
            }
            
            market_analysis = {
                'direction': direction,
                'confidence': confidence,
                'iv_analysis': {'iv_environment': iv_env}
            }
            
            for strategy_name in compatible_strategies:
                metadata = get_strategy_metadata(strategy_name)
                if metadata and strategy_name in self.strategy_classes:
                    # Skip strategies that should be avoided for this stock
                    if strategy_name in avoid_strategies:
                        continue
                        
                    score = calculate_strategy_score(
                        metadata, 
                        market_analysis,
                        portfolio_context
                    )
                    
                    # Boost score if strategy is preferred for this volatility profile
                    if strategy_name in preferred_strategies:
                        score *= 1.5  # 50% boost for preferred strategies
                        
                    strategy_scores[strategy_name] = score
            
            # Sort by score and select top strategies
            sorted_strategies = sorted(
                strategy_scores.items(),
                key=lambda x: x[1],
                reverse=True
            )
            
            # Select top 25-30 strategies to try
            selected_strategies = [name for name, score in sorted_strategies[:30]]
            
            # Apply minimal exclusions only for extreme confidence
            if confidence > 0.85:  # Very high confidence
                if 'strong' in direction.lower() and 'bullish' in direction.lower():
                    # Remove purely bearish strategies
                    selected_strategies = [s for s in selected_strategies 
                                         if s not in ['Long Put', 'Bear Put Spread', 'Bear Call Spread']]
                elif 'strong' in direction.lower() and 'bearish' in direction.lower():
                    # Remove purely bullish strategies  
                    selected_strategies = [s for s in selected_strategies
                                         if s not in ['Long Call', 'Bull Call Spread']]
            
            # Ensure we always include some income strategies for diversity
            income_strategies = ['Cash-Secured Put', 'Covered Call']
            for income_strat in income_strategies:
                if income_strat in self.strategy_classes and income_strat not in selected_strategies:
                    if len(selected_strategies) < 30:
                        selected_strategies.append(income_strat)
            
            self.logger.info(f"Selected {len(selected_strategies)} strategies based on metadata scoring")
            self.logger.debug(f"Strategy selection details - Direction: {direction}, "
                            f"Confidence: {confidence:.1%}, IV: {iv_env}")
            
            return selected_strategies[:30]  # Ensure max 30 strategies
            
        except Exception as e:
            self.logger.error(f"Error in metadata-based selection: {e}")
            # Fallback to original logic if metadata system fails
            return self._select_strategies_fallback(direction, confidence, iv_env)
    
    def _select_strategies_fallback(self, direction: str, confidence: float, iv_env: str) -> List[str]:
        """Fallback strategy selection if metadata system fails"""
        base_strategies = []
        
        if 'bullish' in direction:
            base_strategies.extend(['Long Call', 'Bull Call Spread', 'Bull Put Spread', 'Covered Call'])
        elif 'bearish' in direction:
            base_strategies.extend(['Long Put', 'Bear Put Spread', 'Bear Call Spread', 'Cash-Secured Put'])
        else:
            base_strategies.extend(['Iron Condor', 'Iron Butterfly', 'Butterfly Spread'])
        
        return base_strategies[:10]
    
    def _construct_single_strategy(self, strategy_instance, strategy_name: str, 
                                 market_analysis: Dict) -> Dict:
        """Construct a single strategy with appropriate parameters"""
        try:
            # Strategy-specific parameter selection
            if 'Iron Condor' in strategy_name:
                wing_width = 'wide' if market_analysis.get('confidence', 0) < 0.6 else 'narrow'
                return strategy_instance.construct_strategy(wing_width=wing_width)
            
            elif 'Spread' in strategy_name:
                # Use default delta targets from config
                return strategy_instance.construct_strategy()
            
            elif 'Long' in strategy_name:
                # For long options, use higher delta for better probability of profit
                confidence = market_analysis.get('confidence', 0)
                if 'Call' in strategy_name:
                    # Long Call: use higher delta for better PoP
                    target_delta = 0.5 if confidence > 0.7 else 0.45
                else:  # Long Put
                    # Long Put: similar approach
                    target_delta = 0.5 if confidence > 0.7 else 0.45
                return strategy_instance.construct_strategy(target_delta=target_delta)
            
            else:
                # Default construction
                return strategy_instance.construct_strategy()
                
        except Exception as e:
            return {'success': False, 'reason': f'Construction error: {str(e)}'}
    
    def _generate_portfolio_summary(self, portfolio_results: Dict) -> Dict:
        """Generate summary statistics for portfolio analysis"""
        try:
            total_symbols = len(portfolio_results)
            successful_symbols = sum(1 for result in portfolio_results.values() 
                                   if result.get('success', False))
            
            # Collect strategy statistics
            all_strategies = []
            direction_counts = {'bullish': 0, 'bearish': 0, 'neutral': 0}
            
            for symbol_result in portfolio_results.values():
                if symbol_result.get('success', False):
                    # Count market directions
                    direction = symbol_result.get('market_analysis', {}).get('direction', 'Neutral').lower()
                    if 'bullish' in direction:
                        direction_counts['bullish'] += 1
                    elif 'bearish' in direction:
                        direction_counts['bearish'] += 1
                    else:
                        direction_counts['neutral'] += 1
                    
                    # Collect top strategies
                    top_strategies = symbol_result.get('top_strategies', [])
                    all_strategies.extend([s['name'] for s in top_strategies])
            
            # Strategy distribution
            from collections import Counter
            strategy_distribution = Counter(all_strategies)
            
            return {
                'total_symbols_analyzed': total_symbols,
                'successful_analyses': successful_symbols,
                'success_rate': successful_symbols / total_symbols if total_symbols > 0 else 0,
                'market_sentiment_distribution': direction_counts,
                'total_strategies_recommended': len(all_strategies),
                'strategy_distribution': dict(strategy_distribution),
                'most_recommended_strategies': strategy_distribution.most_common(5)
            }
            
        except Exception as e:
            self.logger.error(f"Error generating portfolio summary: {e}")
            return {}
    
    def get_smart_expiry_date(self, cutoff_day=20):
        """
        Get expiry date using smart 20th date cutoff logic
        
        Args:
            cutoff_day: Cutoff day of month (default: 20)
        
        Returns:
            datetime: Expiry date (last Thursday of target month)
        """
        if self.strike_selector:
            return self.strike_selector.get_smart_expiry_date(cutoff_day=cutoff_day)
        else:
            # Fallback implementation
            import calendar
            from datetime import datetime
            
            base_date = datetime.now()
            current_day = base_date.day
            
            # Simple fallback logic
            if current_day <= cutoff_day:
                target_month = base_date.month
                target_year = base_date.year
            else:
                if base_date.month == 12:
                    target_month = 1
                    target_year = base_date.year + 1
                else:
                    target_month = base_date.month + 1
                    target_year = base_date.year
            
            # Get last Thursday of target month
            last_day = calendar.monthrange(target_year, target_month)[1]
            for day in range(last_day, 0, -1):
                if datetime(target_year, target_month, day).weekday() == 3:  # Thursday = 3
                    return datetime(target_year, target_month, day)
            
            return None
    
    def _load_config(self, config_path: Optional[str] = None) -> Dict:
        """Load configuration from YAML file"""
        try:
            if config_path is None:
                config_path = os.path.join(
                    os.path.dirname(__file__), 
                    'config', 
                    'strategy_config.yaml'
                )
            
            if os.path.exists(config_path) and YAML_AVAILABLE:
                with open(config_path, 'r') as f:
                    return yaml.safe_load(f)
            else:
                if not YAML_AVAILABLE:
                    self.logger.warning("YAML not available, using default config")
                else:
                    self.logger.warning(f"Config file not found: {config_path}, using defaults")
                return self._get_default_config()
                
        except Exception as e:
            self.logger.error(f"Error loading config: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict:
        """Return default configuration when YAML is not available"""
        return {
            'strategy_categories': {
                'directional_bullish': ['Long Call', 'Bull Call Spread', 'Bull Put Spread'],
                'directional_bearish': ['Long Put', 'Bear Call Spread', 'Bear Put Spread'],
                'neutral_theta': ['Iron Condor', 'Iron Butterfly'],
                'volatility_expansion': ['Long Straddle', 'Long Strangle']
            },
            'delta_targets': {
                'spreads': {'short_delta': 0.30, 'long_delta': 0.15},
                'iron_condor': {'put_short_delta': 0.25, 'call_short_delta': 0.25}
            },
            'liquidity_requirements': {
                'minimum_oi': 100,
                'minimum_volume': 50,
                'max_spread_percentage': 0.05
            }
        }
    
    def _get_symbol_sector(self, symbol: str) -> str:
        """
        Get sector for a symbol. In production, this would query a database
        or API. For now, using a simplified mapping.
        """
        # Simplified sector mapping for common Indian stocks
        sector_map = {
            'TCS': 'IT', 'INFY': 'IT', 'WIPRO': 'IT', 'TECHM': 'IT', 'LTI': 'IT',
            'HDFC': 'Banking', 'ICICIBANK': 'Banking', 'SBIN': 'Banking', 'AXISBANK': 'Banking',
            'SUNPHARMA': 'Pharma', 'DRREDDY': 'Pharma', 'CIPLA': 'Pharma', 'LUPIN': 'Pharma',
            'TATAMOTORS': 'Auto', 'MARUTI': 'Auto', 'M&M': 'Auto', 'BAJAJ-AUTO': 'Auto',
            'ITC': 'FMCG', 'HINDUNILVR': 'FMCG', 'NESTLEIND': 'FMCG', 'BRITANNIA': 'FMCG',
            'TATASTEEL': 'Metals', 'JSWSTEEL': 'Metals', 'HINDALCO': 'Metals', 'VEDL': 'Metals',
            'DLF': 'Realty', 'GODREJPROP': 'Realty', 'OBEROIRLTY': 'Realty',
            'RELIANCE': 'Energy', 'ONGC': 'Energy', 'IOC': 'Energy', 'BPCL': 'Energy'
        }
        
        # Check direct mapping
        if symbol in sector_map:
            return sector_map[symbol]
        
        # Check without exchange suffix
        base_symbol = symbol.replace('.NS', '').replace('.BSE', '')
        if base_symbol in sector_map:
            return sector_map[base_symbol]
        
        # Default sector if not found
        return 'default'
    
    def save_results(self, results: Dict, output_dir: str = None) -> str:
        """Save analysis results to JSON file"""
        try:
            if output_dir is None:
                output_dir = os.path.join(os.path.dirname(__file__), 'results')
            
            os.makedirs(output_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'options_v4_analysis_{timestamp}.json'
            filepath = os.path.join(output_dir, filename)
            
            with open(filepath, 'w') as f:
                json.dump(results, f, indent=2, cls=NumpyJSONEncoder)
            
            self.logger.info(f"Results saved to: {filepath}")
            
            # Store results in database if enabled
            if self.enable_database and self.db_integration:
                try:
                    db_result = self.db_integration.store_analysis_results(results)
                    if db_result['success']:
                        self.logger.info(f"Stored {db_result['total_stored']} strategies in database")
                    else:
                        self.logger.warning(f"Database storage failed: {db_result.get('error', 'Unknown error')}")
                except Exception as e:
                    self.logger.error(f"Error storing to database: {e}")
            
            return filepath
            
        except Exception as e:
            self.logger.error(f"Error saving results: {e}")
            return ""

def main():
    """Main entry point"""
    print("🚀 Options V4 Trading System")
    print("=" * 50)
    
    # Check for command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='Options V4 Trading System')
    parser.add_argument('--no-database', action='store_true', help='Disable database storage')
    parser.add_argument('--symbol', type=str, help='Analyze specific symbol instead of portfolio')
    parser.add_argument('--risk', type=str, default='moderate', choices=['conservative', 'moderate', 'aggressive'],
                        help='Risk tolerance level')
    args = parser.parse_args()
    
    try:
        # Initialize analyzer
        analyzer = OptionsAnalyzer(enable_database=not args.no_database)
        
        # Run analysis based on arguments
        if args.symbol:
            # Single symbol analysis
            print(f"\n🔍 Analyzing {args.symbol}...")
            results = analyzer.analyze_symbol(args.symbol, risk_tolerance=args.risk)
            # Wrap single symbol result for consistent handling
            if results.get('success'):
                results = {
                    'success': True,
                    'analysis_timestamp': datetime.now().isoformat(),
                    'symbol_results': {args.symbol: results},
                    'total_symbols': 1,
                    'successful_analyses': 1
                }
        else:
            # Portfolio analysis
            results = analyzer.analyze_portfolio(risk_tolerance=args.risk)
        
        if results.get('success', False):
            # Save results
            output_file = analyzer.save_results(results)
            
            # Print summary
            summary = results.get('portfolio_summary', {})
            print(f"\n📊 Portfolio Analysis Summary:")
            print(f"   • Symbols Analyzed: {summary.get('total_symbols_analyzed', 0)}")
            print(f"   • Successful Analyses: {summary.get('successful_analyses', 0)}")
            print(f"   • Success Rate: {summary.get('success_rate', 0):.1%}")
            print(f"   • Total Strategies: {summary.get('total_strategies_recommended', 0)}")
            print(f"   • Results saved to: {output_file}")
            
            # Show top strategies
            strategy_dist = summary.get('most_recommended_strategies', [])
            if strategy_dist:
                print(f"\n🎯 Most Recommended Strategies:")
                for strategy, count in strategy_dist:
                    print(f"   • {strategy}: {count} times")
            
            # Show database storage status
            if analyzer.enable_database and analyzer.db_integration:
                print(f"\n💾 Database Storage: Enabled")
            else:
                print(f"\n💾 Database Storage: Disabled")
        
        else:
            print(f"❌ Portfolio analysis failed: {results.get('reason', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ System error: {e}")

if __name__ == "__main__":
    main()