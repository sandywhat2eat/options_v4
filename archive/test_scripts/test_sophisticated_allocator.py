#!/usr/bin/env python3
"""
Test Script for Sophisticated Portfolio Allocator
Demonstrates the quantum-level allocation system with mock data
"""

import sys
import os
import json
from datetime import datetime

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sophisticated_portfolio_allocator_runner import ProductionAllocatorRunner

def main():
    """Test the sophisticated allocator with mock data"""
    
    print("🧪 TESTING SOPHISTICATED OPTIONS PORTFOLIO ALLOCATOR")
    print("=" * 70)
    
    # Initialize runner with mock data (no database)
    print("Initializing allocator with mock data...")
    runner = ProductionAllocatorRunner(enable_database=False)
    
    # Run allocation
    print("Running sophisticated allocation...")
    result = runner.run_allocation(
        update_database=False,  # Don't update database in test
        save_report=True        # Save test report
    )
    
    # Print results
    runner.print_allocation_summary(result)
    
    # Additional testing output
    if 'error' not in result:
        print("\n🔬 DETAILED TEST ANALYSIS:")
        print("-" * 50)
        
        # Test allocation efficiency
        metrics = result.get('portfolio_metrics', {})
        allocation_pct = metrics.get('total_allocation_percent', 0)
        
        if allocation_pct >= 90:
            print("✅ Allocation Efficiency: EXCELLENT (≥90%)")
        elif allocation_pct >= 80:
            print("✅ Allocation Efficiency: GOOD (80-90%)")
        elif allocation_pct >= 70:
            print("⚠️  Allocation Efficiency: ACCEPTABLE (70-80%)")
        else:
            print("❌ Allocation Efficiency: POOR (<70%)")
        
        # Test strategy diversification
        strategy_count = metrics.get('total_strategies', 0)
        if strategy_count >= 25:
            print("✅ Strategy Count: EXCELLENT (≥25)")
        elif strategy_count >= 20:
            print("✅ Strategy Count: GOOD (20-25)")
        elif strategy_count >= 15:
            print("⚠️  Strategy Count: ACCEPTABLE (15-20)")
        else:
            print("❌ Strategy Count: POOR (<15)")
        
        # Test expected performance
        sharpe_ratio = metrics.get('sharpe_ratio', 0)
        if sharpe_ratio >= 1.5:
            print("✅ Sharpe Ratio: EXCELLENT (≥1.5)")
        elif sharpe_ratio >= 1.2:
            print("✅ Sharpe Ratio: GOOD (1.2-1.5)")
        elif sharpe_ratio >= 0.8:
            print("⚠️  Sharpe Ratio: ACCEPTABLE (0.8-1.2)")
        else:
            print("❌ Sharpe Ratio: POOR (<0.8)")
        
        # Test industry diversification
        by_industry = result.get('allocation_by_industry', {})
        industry_count = len(by_industry)
        
        if industry_count >= 6:
            print("✅ Industry Diversification: EXCELLENT (≥6)")
        elif industry_count >= 4:
            print("✅ Industry Diversification: GOOD (4-6)")
        elif industry_count >= 3:
            print("⚠️  Industry Diversification: ACCEPTABLE (3-4)")
        else:
            print("❌ Industry Diversification: POOR (<3)")
        
        # Test VIX environment handling
        market_env = result.get('market_environment', {})
        vix_env = market_env.get('vix_environment', '')
        vix_level = market_env.get('vix_level', 0)
        
        print(f"\n🌍 Market Environment Test:")
        print(f"   VIX Level: {vix_level}")
        print(f"   Environment: {vix_env.replace('_', ' ').title()}")
        
        if vix_env == 'low_vix':
            print("✅ VIX Environment: Correctly classified as Low VIX")
            print("   Expected strategies: Iron Condors, Butterflies, Premium Selling")
        
        # Overall test result
        print(f"\n🎯 OVERALL TEST RESULT:")
        if (allocation_pct >= 80 and strategy_count >= 20 and 
            sharpe_ratio >= 1.2 and industry_count >= 4):
            print("✅ PASS - Sophisticated allocator working excellently!")
        elif (allocation_pct >= 70 and strategy_count >= 15 and 
              sharpe_ratio >= 0.8 and industry_count >= 3):
            print("⚠️  PARTIAL PASS - Allocator working acceptably")
        else:
            print("❌ FAIL - Allocator needs improvement")
        
        # Configuration test
        print(f"\n⚙️  CONFIGURATION TEST:")
        config_keys = [
            'vix_allocation_targets', 'fallback_hierarchy', 'strategy_mapping',
            'quality_thresholds', 'position_sizing', 'risk_management'
        ]
        
        allocator = runner.allocator
        for key in config_keys:
            if key in allocator.config:
                print(f"✅ {key}: Loaded")
            else:
                print(f"❌ {key}: Missing")
        
        print(f"\n📊 QUANTUM SCORING TEST:")
        if hasattr(allocator, 'strategies_df') and allocator.strategies_df is not None:
            if 'quantum_score' in allocator.strategies_df.columns:
                scores = allocator.strategies_df['quantum_score']
                print(f"✅ Quantum scores calculated: {len(scores)} strategies")
                print(f"   Score range: {scores.min():.1f} - {scores.max():.1f}")
                print(f"   Average score: {scores.mean():.1f}")
            else:
                print("❌ Quantum scores not calculated")
        
    else:
        print(f"❌ TEST FAILED: {result['error']}")
    
    print("\n" + "=" * 70)
    print("🧪 TEST COMPLETED")
    
    return 0 if 'error' not in result else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)