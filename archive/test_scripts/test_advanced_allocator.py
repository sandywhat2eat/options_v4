"""
Test script for Advanced Options Allocator
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from advanced_allocator import AdvancedOptionsAllocator
import logging

logging.basicConfig(level=logging.INFO)

def test_allocator():
    """Test the allocator without database connection"""
    print("Testing Advanced Options Allocator...")
    
    # Create allocator without database (will use mock data)
    allocator = AdvancedOptionsAllocator(None, total_capital=10000000)
    
    # Run allocation
    result = allocator.allocate_portfolio(vix_level=20.0)
    
    # Print results
    print(f"\nMarket Analysis:")
    print(f"  State: {result.market_analysis['market_state']}")
    print(f"  Direction Score: {result.market_analysis['direction_score']:.2f}")
    print(f"  Confidence: {result.market_analysis['confidence']:.1%}")
    
    print(f"\nPortfolio Summary:")
    print(f"  Total Positions: {result.summary['total_positions']}")
    print(f"  Long/Short: {result.summary['long_positions']}/{result.summary['short_positions']}")
    
    print(f"\nMarket Cap Distribution:")
    for cap, data in result.summary['market_cap_distribution'].items():
        print(f"  {cap}: {data['count']} positions")
    
    # Save test results
    test_output = "results/test_advanced_allocation.json"
    allocator.save_allocation_result(result, test_output)
    print(f"\nTest results saved to: {test_output}")
    
    print("\nTest completed successfully!")

if __name__ == "__main__":
    test_allocator()