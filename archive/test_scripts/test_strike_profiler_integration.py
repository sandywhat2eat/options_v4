#!/usr/bin/env python3
"""
Test script to verify strike selector integration with stock profiler
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import the modules
from core.strike_selector import IntelligentStrikeSelector
from core.stock_profiler import StockProfiler

def create_mock_options_chain(spot_price):
    """Create a realistic options chain for testing"""
    # Generate strikes around spot price
    strike_interval = 50 if spot_price > 1000 else 10
    min_strike = int(spot_price * 0.85 / strike_interval) * strike_interval
    max_strike = int(spot_price * 1.15 / strike_interval) * strike_interval
    
    strikes = np.arange(min_strike, max_strike + strike_interval, strike_interval)
    
    data = []
    for strike in strikes:
        for option_type in ['CALL', 'PUT']:
            # Calculate moneyness
            moneyness = (strike - spot_price) / spot_price
            
            # Simulate realistic open interest (higher near ATM)
            distance_from_atm = abs(moneyness)
            base_oi = 5000
            open_interest = int(base_oi * np.exp(-distance_from_atm * 10))
            
            # Simulate volume
            volume = int(open_interest * 0.2 * (1 + np.random.random()))
            
            # Simulate IV (smile effect)
            base_iv = 25
            iv = base_iv + distance_from_atm * 15
            
            data.append({
                'strike': strike,
                'option_type': option_type,
                'open_interest': open_interest,
                'volume': volume,
                'iv': iv,
                'bid': 10.0,  # Simplified
                'ask': 11.0   # Simplified
            })
    
    return pd.DataFrame(data)

def test_integration():
    """Test the integration between strike selector and stock profiler"""
    
    logger.info("=== Testing Strike Selector with Stock Profiler Integration ===")
    
    # Initialize components
    profiler = StockProfiler()
    strike_selector = IntelligentStrikeSelector(stock_profiler=profiler)
    
    # Test cases with different volatility profiles
    test_cases = [
        {
            'symbol': 'RELIANCE',
            'spot_price': 2500,
            'description': 'Large cap, low volatility stock'
        },
        {
            'symbol': 'RBLBANK',
            'spot_price': 150,
            'description': 'High volatility financial stock'
        },
        {
            'symbol': 'INFY',
            'spot_price': 1400,
            'description': 'Medium volatility IT stock'
        }
    ]
    
    for test_case in test_cases:
        logger.info(f"\n{'='*60}")
        logger.info(f"Testing {test_case['symbol']} - {test_case['description']}")
        logger.info(f"Spot Price: {test_case['spot_price']}")
        
        # Create mock options chain
        options_df = create_mock_options_chain(test_case['spot_price'])
        
        # Create mock market analysis
        market_analysis = {
            'symbol': test_case['symbol'],
            'outlook': 'BULLISH',
            'confidence': 0.65,
            'timeframe': {'duration': '10-20 days'},
            'iv_environment': 'NORMAL',
            'expected_moves': {
                'one_sd_move': test_case['spot_price'] * 0.05,  # This will be overridden
                'two_sd_move': test_case['spot_price'] * 0.10   # This will be overridden
            }
        }
        
        # Test different strategies
        strategies = ['Long Call', 'Bull Call Spread', 'Iron Condor']
        
        for strategy in strategies:
            logger.info(f"\n--- Testing {strategy} ---")
            
            try:
                # Select strikes using the integrated system
                selected_strikes = strike_selector.select_strikes(
                    strategy_type=strategy,
                    options_df=options_df,
                    spot_price=test_case['spot_price'],
                    market_analysis=market_analysis
                )
                
                logger.info(f"Selected strikes for {strategy}:")
                for strike_name, strike_value in selected_strikes.items():
                    moneyness = (strike_value - test_case['spot_price']) / test_case['spot_price'] * 100
                    logger.info(f"  {strike_name}: {strike_value} (Moneyness: {moneyness:.1f}%)")
                
                # If profiler is available, show the expected move calculation
                if strike_selector.stock_profiler:
                    expected_move = strike_selector.stock_profiler.calculate_expected_move(
                        symbol=test_case['symbol'],
                        timeframe_days=15  # 10-20 days midpoint
                    )
                    
                    if 'adjusted_expected_pct' in expected_move:
                        logger.info(f"  Expected move: ±{expected_move['adjusted_expected_pct']:.1f}% "
                                  f"(±{expected_move['adjusted_expected_move']:.0f} points)")
                        logger.info(f"  Components: IV={expected_move['components']['iv_move']:.0f}, "
                                  f"ATR={expected_move['components']['atr_move']:.0f}, "
                                  f"HV={expected_move['components']['hv_move']:.0f}, "
                                  f"Beta={expected_move['components']['beta_move']:.0f}")
                
            except Exception as e:
                logger.error(f"Error testing {strategy}: {e}")
                import traceback
                traceback.print_exc()
    
    logger.info(f"\n{'='*60}")
    logger.info("Integration test completed!")
    
    # Test edge cases
    logger.info("\n=== Testing Edge Cases ===")
    
    # Test with missing profiler data
    logger.info("\nTest 1: Strike selection when profiler data is unavailable")
    market_analysis_no_profile = {
        'symbol': 'UNKNOWN',
        'outlook': 'NEUTRAL',
        'confidence': 0.5,
        'timeframe': {'duration': '20-30 days'}
    }
    
    try:
        selected = strike_selector.select_strikes(
            strategy_type='Iron Condor',
            options_df=create_mock_options_chain(1000),
            spot_price=1000,
            market_analysis=market_analysis_no_profile
        )
        logger.info("Successfully handled missing profiler data")
        logger.info(f"Selected strikes: {selected}")
    except Exception as e:
        logger.error(f"Failed to handle missing profiler data: {e}")

if __name__ == "__main__":
    test_integration()