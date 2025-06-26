#!/usr/bin/env python3
"""
Test the volatility-based strategy selection integration
"""

import logging
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from main import OptionsAnalyzer

def test_single_symbol(symbol: str):
    """Test analysis for a single symbol"""
    print(f"\n{'='*60}")
    print(f"Testing {symbol}")
    print('='*60)
    
    # Initialize analyzer
    analyzer = OptionsAnalyzer(enable_database=False)  # No DB for testing
    
    # Analyze symbol
    result = analyzer.analyze_symbol(symbol, risk_tolerance='moderate')
    
    if result['success']:
        print(f"\n✅ Analysis successful for {symbol}")
        
        # Show stock profile info
        if 'market_analysis' in result and 'stock_profile' in result['market_analysis']:
            profile = result['market_analysis']['stock_profile']
            print(f"\nStock Profile:")
            print(f"  - Volatility Bucket: {profile.get('volatility_bucket', 'Unknown')}")
            print(f"  - ATR%: {profile.get('atr_pct', 0):.2f}%")
            print(f"  - Beta vs NIFTY: {profile.get('beta_nifty', 1.0):.2f}")
            print(f"  - Current IV: {profile.get('current_iv', 0):.1f}%")
            print(f"  - Market Cap: {profile.get('market_cap_category', 'Unknown')}")
            
            # Show preferred strategies
            if 'volatility_details' in profile:
                vol_details = profile['volatility_details']
                print(f"\nVolatility-Based Recommendations:")
                print(f"  - Preferred Strategies: {vol_details.get('preferred_strategies', [])}")
                print(f"  - Avoid Strategies: {vol_details.get('avoid_strategies', [])}")
        
        # Show market analysis
        market_analysis = result.get('market_analysis', {})
        print(f"\nMarket Analysis:")
        print(f"  - Direction: {market_analysis.get('direction', 'Unknown')}")
        print(f"  - Confidence: {market_analysis.get('confidence', 0):.1%}")
        print(f"  - IV Environment: {market_analysis.get('iv_analysis', {}).get('iv_environment', 'Unknown')}")
        
        # Show top strategies
        print(f"\nTop Strategies Selected:")
        for i, strategy in enumerate(result.get('top_strategies', [])[:3]):
            print(f"\n{i+1}. {strategy['name']}")
            print(f"   - Score: {strategy.get('total_score', 0):.3f}")
            print(f"   - Probability of Profit: {strategy.get('probability_profit', 0):.1%}")
            print(f"   - Max Profit: ₹{strategy.get('max_profit', 0):,.0f}")
            print(f"   - Max Loss: ₹{strategy.get('max_loss', 0):,.0f}")
            
    else:
        print(f"\n❌ Analysis failed: {result.get('reason', 'Unknown error')}")

def main():
    """Run tests on different volatility stocks"""
    
    print("Testing Volatility-Based Strategy Selection")
    print("=" * 60)
    
    # Test different volatility profiles
    test_symbols = [
        'RELIANCE',  # Large cap, low volatility
        'INFY',      # IT stock, medium volatility
        'BAJFINANCE', # Financial, medium-high volatility
        'RBLBANK',   # High volatility
        'ZOMATO'     # Ultra-high volatility (if available)
    ]
    
    for symbol in test_symbols:
        try:
            test_single_symbol(symbol)
        except Exception as e:
            print(f"\n❌ Error testing {symbol}: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*60)
    print("Testing completed!")

if __name__ == "__main__":
    main()