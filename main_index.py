"""
Main orchestrator for INDEX-ONLY Options V4 trading system

INDEX VERSION - NO STOCKS
This version works exclusively with index options (NIFTY 50, BANK NIFTY, etc.)
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

# Import INDEX-ONLY modules
from strategy_creation_index import DataManager, IVAnalyzer, ProbabilityEngine, RiskManager, StockProfiler
from trade_execution import ExitManager
from strategy_creation_index import MarketAnalyzer
from analysis import StrategyRanker, PriceLevelsAnalyzer
from utils.parallel_processor import ParallelProcessor
from strategy_creation.strategies import (
    # Directional
    LongCall, LongPut, ShortCall, ShortPut, BullCallSpread, BearCallSpread, 
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

# Strategy class mapping for INDEX system
STRATEGY_CLASSES = {
    # Directional
    'Long Call': LongCall,
    'Long Put': LongPut,
    'Short Call': ShortCall,
    'Short Put': ShortPut,
    'Bull Call Spread': BullCallSpread,
    'Bear Call Spread': BearCallSpread,
    'Bull Put Spread': BullPutSpreadStrategy,
    'Bear Put Spread': BearPutSpreadStrategy,
    
    # Neutral
    'Iron Condor': IronCondor,
    'Butterfly Spread': ButterflySpread,
    'Iron Butterfly': IronButterfly,
    
    # Volatility
    'Long Straddle': LongStraddle,
    'Short Straddle': ShortStraddle,
    'Long Strangle': LongStrangle,
    'Short Strangle': ShortStrangle,
    
    # Income
    'Cash-Secured Put': CashSecuredPut,
    'Covered Call': CoveredCall,
    
    # Advanced
    'Calendar Spread': CalendarSpread,
    'Diagonal Spread': DiagonalSpread,
    'Call Ratio Spread': CallRatioSpread,
    'Put Ratio Spread': PutRatioSpread,
    'Jade Lizard': JadeLizard,
    'Broken Wing Butterfly': BrokenWingButterfly
}

# Configure logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/options_v4_index_main.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class IndexOptionsAnalyzer:
    """INDEX-ONLY Options Analysis System"""
    
    def __init__(self):
        """Initialize INDEX-ONLY analyzer with all components"""
        logger.info("Initializing INDEX-ONLY Options Analyzer...")
        
        # Load environment variables
        if DOTENV_AVAILABLE:
            load_dotenv()
        
        # Initialize INDEX-ONLY components
        self.data_manager = DataManager()
        self.iv_analyzer = IVAnalyzer()
        self.prob_engine = ProbabilityEngine()
        self.risk_manager = RiskManager()
        self.profiler = StockProfiler()
        self.market_analyzer = MarketAnalyzer()
        self.strategy_ranker = StrategyRanker()
        self.price_analyzer = PriceLevelsAnalyzer()
        self.exit_manager = ExitManager()
        
        # Strategy mapping
        self.strategy_map = STRATEGY_CLASSES
        
        logger.info("INDEX-ONLY Options Analyzer initialized successfully")
    
    def analyze_index_portfolio(self, risk_tolerance: str = 'moderate', max_workers: int = 8) -> Dict:
        """
        Analyze INDEX portfolio and generate strategies
        
        Args:
            risk_tolerance: Risk tolerance level
            max_workers: Number of parallel workers
            
        Returns:
            Analysis results dictionary
        """
        try:
            logger.info("Starting INDEX-ONLY portfolio analysis...")
            
            # Get INDEX symbols only
            symbols = self.data_manager.get_portfolio_symbols()
            logger.info(f"Analyzing {len(symbols)} INDEX symbols: {symbols}")
            
            if not symbols:
                logger.error("No INDEX symbols found!")
                return {"success": False, "error": "No index symbols available"}
            
            # Prefetch metadata for all indexes
            self.profiler.prefetch_metadata(symbols)
            
            # Process indexes in parallel
            processor = ParallelProcessor(max_workers=max_workers)
            results = processor.process_symbols_parallel(
                symbols=symbols,
                process_func=self._analyze_single_index,
                callback_func=self._store_index_result
            )
            
            # Compile final results
            successful_results = {k: v for k, v in results.items() if v.get('success', False)}
            
            final_result = {
                'success': True,
                'analysis_timestamp': datetime.now().isoformat(),
                'symbol_results': successful_results,
                'total_symbols': len(symbols),
                'successful_analyses': len(successful_results)
            }
            
            # Save results to file
            self._save_results(final_result)
            
            logger.info(f"INDEX portfolio analysis complete: {len(successful_results)}/{len(symbols)} successful")
            return final_result
            
        except Exception as e:
            logger.error(f"Error in INDEX portfolio analysis: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}
    
    def _analyze_single_index(self, symbol: str) -> Dict:
        """Analyze a single INDEX symbol"""
        try:
            logger.info(f"Analyzing INDEX: {symbol}")
            
            # Get options data
            options_data = self.data_manager.get_options_data(symbol)
            if options_data is None or options_data.empty:
                logger.warning(f"No options data for INDEX {symbol}")
                return {"success": False, "symbol": symbol, "error": "No options data"}
            
            # Get spot price
            spot_price = self.data_manager.get_spot_price(symbol)
            if not spot_price:
                logger.warning(f"No spot price for INDEX {symbol}")
                return {"success": False, "symbol": symbol, "error": "No spot price"}
            
            # Generate market analysis
            market_analysis = self.market_analyzer.analyze_market_direction(
                symbol, options_data, spot_price
            )
            
            # Generate price levels
            price_levels = self.price_analyzer.analyze_price_levels(
                symbol, options_data, spot_price, market_analysis
            )
            
            # Build strategies
            strategies = self._build_index_strategies(symbol, options_data, market_analysis, spot_price)
            
            if not strategies:
                logger.warning(f"No strategies generated for INDEX {symbol}")
                return {"success": False, "symbol": symbol, "error": "No strategies generated"}
            
            # Filter and rank strategies
            filtered_strategies = self._filter_strategies(strategies, market_analysis)
            ranked_strategies = self.strategy_ranker.rank_strategies(filtered_strategies, market_analysis)
            
            return {
                'success': True,
                'symbol': symbol,
                'spot_price': spot_price,
                'market_analysis': market_analysis,
                'price_levels': price_levels,
                'total_strategies_generated': len(strategies),
                'strategies_after_filtering': len(filtered_strategies),
                'top_strategies': ranked_strategies[:5]  # Top 5 strategies
            }
            
        except Exception as e:
            logger.error(f"Error analyzing INDEX {symbol}: {e}")
            return {"success": False, "symbol": symbol, "error": str(e)}
    
    def _build_index_strategies(self, symbol: str, options_data, market_analysis: Dict, spot_price: float) -> List[Dict]:
        """Build strategies for INDEX symbol"""
        try:
            strategies = []
            
            # Get strategy selection for this market condition
            selected_strategies = self._select_index_strategies(symbol, market_analysis)
            
            logger.info(f"Building {len(selected_strategies)} strategies for INDEX {symbol}")
            
            for strategy_name in selected_strategies:
                try:
                    strategy_class = self.strategy_map.get(strategy_name)
                    if not strategy_class:
                        logger.warning(f"Strategy class not found: {strategy_name}")
                        continue
                    
                    # Initialize strategy
                    strategy = strategy_class(
                        symbol=symbol,
                        options_data=options_data,
                        market_analysis=market_analysis,
                        risk_manager=self.risk_manager
                    )
                    
                    # Construct strategy
                    result = strategy.construct_strategy()
                    if result and result.get('success'):
                        strategies.append(result)
                        logger.debug(f"Successfully built {strategy_name} for INDEX {symbol}")
                    else:
                        logger.debug(f"Failed to build {strategy_name} for INDEX {symbol}")
                        
                except Exception as e:
                    logger.warning(f"Error building {strategy_name} for INDEX {symbol}: {e}")
                    continue
            
            return strategies
            
        except Exception as e:
            logger.error(f"Error building strategies for INDEX {symbol}: {e}")
            return []
    
    def _select_index_strategies(self, symbol: str, market_analysis: Dict) -> List[str]:
        """Select appropriate strategies for INDEX based on market analysis"""
        direction = market_analysis.get('direction', 'Neutral')
        confidence = market_analysis.get('confidence', 0.5)
        iv_analysis = market_analysis.get('iv_analysis', {})
        iv_environment = iv_analysis.get('iv_environment', 'NORMAL')
        
        strategies = []
        
        # INDEX-specific strategy selection with larger position sizes
        if direction == 'Bullish':
            if confidence > 0.7:
                strategies.extend(['Long Call', 'Bull Call Spread'])
            else:
                strategies.extend(['Bull Call Spread', 'Bull Put Spread'])
        
        elif direction == 'Bearish':
            if confidence > 0.7:
                strategies.extend(['Long Put', 'Bear Put Spread'])
            else:
                strategies.extend(['Bear Put Spread', 'Bear Call Spread'])
        
        else:  # Neutral
            strategies.extend(['Iron Condor', 'Butterfly Spread', 'Short Strangle'])
        
        # Add volatility strategies based on IV environment
        if iv_environment in ['LOW', 'SUBDUED']:
            strategies.extend(['Long Straddle', 'Long Strangle'])
        elif iv_environment in ['HIGH', 'ELEVATED']:
            strategies.extend(['Short Straddle', 'Iron Condor'])
        
        # Always consider income strategies for indexes
        strategies.extend(['Cash-Secured Put', 'Covered Call'])
        
        return list(set(strategies))  # Remove duplicates
    
    def _filter_strategies(self, strategies: List[Dict], market_analysis: Dict) -> List[Dict]:
        """Filter strategies based on probability and risk criteria"""
        filtered = []
        
        for strategy in strategies:
            # Check probability
            prob_profit = strategy.get('probability_profit', 0)
            if prob_profit < 0.25:  # Minimum 25% probability for indexes
                continue
            
            # Check risk-reward
            max_profit = strategy.get('max_profit', 0)
            max_loss = strategy.get('max_loss', float('inf'))
            
            if max_loss > 0 and max_profit > 0:
                risk_reward = max_profit / max_loss
                if risk_reward < 0.5:  # Minimum 0.5:1 for indexes
                    continue
            
            filtered.append(strategy)
        
        return filtered
    
    def _store_index_result(self, symbol: str, result: Dict) -> None:
        """Store individual INDEX result (callback for parallel processing)"""
        if result.get('success'):
            logger.info(f"✅ INDEX {symbol}: {result.get('strategies_after_filtering', 0)} strategies")
        else:
            logger.warning(f"❌ INDEX {symbol}: {result.get('error', 'Unknown error')}")
    
    def _save_results(self, results: Dict) -> None:
        """Save analysis results to file"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'results/options_v4_index_analysis_{timestamp}.json'
            
            os.makedirs('results', exist_ok=True)
            
            with open(filename, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            
            logger.info(f"INDEX results saved to {filename}")
            
        except Exception as e:
            logger.error(f"Error saving INDEX results: {e}")

def main():
    """Main entry point for INDEX-ONLY analysis"""
    try:
        print("🔍 INDEX-ONLY Options V4 Analysis System")
        print("=" * 50)
        
        analyzer = IndexOptionsAnalyzer()
        results = analyzer.analyze_index_portfolio(
            risk_tolerance='moderate',
            max_workers=4  # Smaller number for indexes
        )
        
        if results.get('success'):
            print(f"\n✅ INDEX Analysis Complete!")
            print(f"   • Total indexes: {results['total_symbols']}")
            print(f"   • Successful: {results['successful_analyses']}")
            print(f"   • Results saved to results/")
        else:
            print(f"\n❌ INDEX Analysis Failed: {results.get('error')}")
            
    except Exception as e:
        print(f"\n💥 CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()