#!/usr/bin/env python3
"""
Test script for centralized strike selection improvements
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import the centralized strike selector
from core.strike_selector import IntelligentStrikeSelector, StrikeRequest, StrikeConstraint

def create_mock_options_data(spot_price):
    """Create mock options data for testing"""
    strikes = np.arange(spot_price * 0.8, spot_price * 1.2, spot_price * 0.01)
    
    data = []
    for strike in strikes:
        for option_type in ['CALL', 'PUT']:
            # Simulate realistic data
            moneyness = (strike - spot_price) / spot_price
            
            if option_type == 'CALL':
                delta = 0.5 * (1 + moneyness * 5) if moneyness < 0 else 0.5 * (1 - moneyness * 5)
                delta = max(0.05, min(0.95, delta))
            else:
                delta = -0.5 * (1 - moneyness * 5) if moneyness > 0 else -0.5 * (1 + moneyness * 5)
                delta = max(-0.95, min(-0.05, delta))
            
            # Simulate liquidity - ATM has highest liquidity
            distance_from_atm = abs(moneyness)
            open_interest = int(1000 * np.exp(-distance_from_atm * 10))
            volume = int(open_interest * 0.3 * np.random.random())
            
            # Simulate IV - higher for OTM options
            iv = 30 + distance_from_atm * 20
            
            # Simulate premium
            if option_type == 'CALL':
                premium = max(0, spot_price - strike) + spot_price * 0.05 * np.exp(-distance_from_atm * 5)
            else:
                premium = max(0, strike - spot_price) + spot_price * 0.05 * np.exp(-distance_from_atm * 5)
            
            data.append({
                'strike': strike,
                'option_type': option_type,
                'delta': delta,
                'open_interest': open_interest,
                'volume': volume,
                'implied_volatility': iv,
                'last_price': premium,
                'bid': premium * 0.95,
                'ask': premium * 1.05,
                'spot_price': spot_price
            })
    
    return pd.DataFrame(data)

def create_market_analysis(spot_price):
    """Create mock market analysis data"""
    return {
        'direction': 'Bullish',
        'confidence': 0.65,
        'timeframe': {
            'duration': '10-20 days'
        },
        'price_levels': {
            'expected_moves': {
                'one_sd_move': spot_price * 0.05,
                'two_sd_move': spot_price * 0.10,
                'one_sd_pct': 5.0,
                'two_sd_pct': 10.0
            }
        },
        'iv_analysis': {
            'iv_environment': 'NORMAL',
            'atm_iv': 30
        }
    }

def test_strategy_strikes(selector, strategy_name, options_df, spot_price, market_analysis):
    """Test strike selection for a specific strategy"""
    logger.info(f"\n{'='*60}")
    logger.info(f"Testing {strategy_name}")
    logger.info(f"{'='*60}")
    
    try:
        strikes = selector.select_strikes(
            strategy_type=strategy_name,
            options_df=options_df,
            spot_price=spot_price,
            market_analysis=market_analysis
        )
        
        if strikes:
            logger.info(f"Successfully selected strikes for {strategy_name}:")
            for name, strike in strikes.items():
                logger.info(f"  {name}: {strike:.2f}")
                
            # Validate strike relationships
            if strategy_name == 'Bull Call Spread':
                if strikes.get('long_strike', 0) < strikes.get('short_strike', 0):
                    logger.info("✓ Strike relationship valid (long < short)")
                else:
                    logger.error("✗ Invalid strike relationship!")
                    
            elif strategy_name == 'Iron Condor':
                if (strikes.get('put_long', 0) < strikes.get('put_short', 0) < 
                    spot_price < strikes.get('call_short', 0) < strikes.get('call_long', 0)):
                    logger.info("✓ Strike relationship valid (PL < PS < Spot < CS < CL)")
                else:
                    logger.error("✗ Invalid strike relationship!")
        else:
            logger.error(f"Failed to select strikes for {strategy_name}")
            
    except Exception as e:
        logger.error(f"Error testing {strategy_name}: {e}")

def test_nan_handling():
    """Test NaN handling in database integration"""
    logger.info(f"\n{'='*60}")
    logger.info("Testing NaN Handling")
    logger.info(f"{'='*60}")
    
    from database.supabase_integration import SupabaseIntegration
    
    db = SupabaseIntegration()
    
    # Test various NaN scenarios
    test_values = [
        np.nan,
        float('nan'),
        np.inf,
        float('inf'),
        [1, 2, np.nan, 4],
        {'a': 1, 'b': np.nan, 'c': {'d': np.inf}},
        pd.Series([1, 2, np.nan, 4])
    ]
    
    for i, value in enumerate(test_values):
        cleaned = db._clean_value(value)
        logger.info(f"Test {i+1}: {type(value).__name__} -> {cleaned}")

def main():
    """Run all tests"""
    # Test parameters
    spot_price = 100.0
    
    # Create test data
    options_df = create_mock_options_data(spot_price)
    market_analysis = create_market_analysis(spot_price)
    
    # Initialize selector
    selector = IntelligentStrikeSelector()
    
    # Test various strategies
    strategies_to_test = [
        'Bull Call Spread',
        'Bear Put Spread',
        'Iron Condor',
        'Long Straddle',
        'Cash-Secured Put',
        'Butterfly Spread',
        'Jade Lizard'
    ]
    
    for strategy in strategies_to_test:
        test_strategy_strikes(selector, strategy, options_df, spot_price, market_analysis)
    
    # Test NaN handling
    test_nan_handling()
    
    logger.info(f"\n{'='*60}")
    logger.info("All tests completed!")
    logger.info(f"{'='*60}")

if __name__ == "__main__":
    main()