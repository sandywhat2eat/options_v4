#!/usr/bin/env python3
"""
Hybrid Portfolio Allocator Runner
Command-line interface for the hybrid portfolio allocation system
"""

import sys
import json
import logging
import argparse
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from database.supabase_integration import SupabaseIntegration
from portfolio_allocation.core.hybrid_portfolio_engine import (
    HybridPortfolioEngine, display_portfolio_results
)

# Setup logging
def setup_logging(verbose: bool = False):
    """Setup logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(f'logs/hybrid_allocator_{datetime.now().strftime("%Y%m%d")}.log')
        ]
    )
    return logging.getLogger(__name__)


def save_results(positions, summary, capital, output_file):
    """Save allocation results to JSON file"""
    results = {
        'timestamp': datetime.now().isoformat(),
        'total_capital': capital,
        'market_conditions': summary.get('market_conditions', {}),
        'portfolio_summary': summary,
        'positions': []
    }
    
    # Convert positions to serializable format
    for pos in positions:
        position_data = {
            'stock_name': pos.strategy.stock_name,
            'strategy_name': pos.strategy.strategy_name,
            'tier': pos.tier,
            'industry': pos.industry,
            'industry_weight': pos.industry_weight,
            'position_type': pos.position_type,
            'market_cap_category': pos.market_cap_category,
            'allocated_capital': pos.allocated_capital,
            'number_of_lots': pos.number_of_lots,
            'actual_capital_deployed': pos.actual_capital_deployed,
            'expected_monthly_income': pos.expected_monthly_income,
            'net_premium': pos.strategy.net_premium,
            'lot_size': pos.strategy.lot_size,
            'premium_per_lot': pos.strategy.premium_per_lot,
            'probability_of_profit': pos.strategy.probability_of_profit,
            'risk_reward_ratio': pos.strategy.risk_reward_ratio,
            'total_score': pos.strategy.total_score,
            'conviction_level': pos.strategy.conviction_level,
            'greeks': {
                'delta': pos.strategy.net_delta,
                'gamma': pos.strategy.net_gamma,
                'theta': pos.strategy.net_theta,
                'vega': pos.strategy.net_vega
            },
            'position_risk_score': pos.position_risk_score
        }
        results['positions'].append(position_data)
    
    # Save to file
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📁 Results saved to: {output_file}")


def main():
    """Main runner function"""
    parser = argparse.ArgumentParser(
        description='Hybrid Portfolio Allocator - Combines Tiers with Industry Allocation'
    )
    
    parser.add_argument(
        '--capital', type=float, default=1500000,
        help='Total capital to allocate (default: ₹15,00,000)'
    )
    
    parser.add_argument(
        '--output', type=str, 
        default=f'portfolio_allocation/results/hybrid_allocation_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json',
        help='Output file for results'
    )
    
    parser.add_argument(
        '--dry-run', action='store_true',
        help='Run without saving to database'
    )
    
    parser.add_argument(
        '--verbose', action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    logger = setup_logging(args.verbose)
    
    try:
        print("\n" + "="*80)
        print("🚀 HYBRID PORTFOLIO ALLOCATOR - TIER + INDUSTRY APPROACH")
        print("="*80)
        print(f"\n💰 Capital: ₹{args.capital:,.0f}")
        print(f"🎯 Target: 4% monthly return (₹{args.capital * 0.04:,.0f})")
        
        # Initialize database connection
        print("\n📊 Connecting to database...")
        supabase = SupabaseIntegration(logger=logger)
        
        if not supabase.client:
            raise ValueError("Failed to connect to database")
        
        # Create engine
        print("🔧 Initializing hybrid portfolio engine...")
        engine = HybridPortfolioEngine(supabase.client)
        
        # Build portfolio
        print("🏗️ Building portfolio...")
        positions, summary = engine.build_hybrid_portfolio(args.capital)
        
        # Display results
        display_portfolio_results(positions, summary, args.capital)
        
        # Save results
        save_results(positions, summary, args.capital, args.output)
        
        # Performance summary
        print("\n" + "="*80)
        print("📊 PERFORMANCE SUMMARY")
        print("="*80)
        print(f"Target Monthly Income: ₹{args.capital * 0.04:,.0f}")
        print(f"Expected Monthly Income: ₹{summary['expected_monthly_income']:,.0f}")
        print(f"Target Achievement: {(summary['expected_monthly_income'] / (args.capital * 0.04)) * 100:.1f}%")
        
        if summary['deployment_percentage'] < 85:
            print(f"\n⚠️  WARNING: Low capital deployment ({summary['deployment_percentage']:.1f}%)")
            print("   Consider adjusting risk parameters for better capital utilization")
        
        print("\n✅ Portfolio allocation completed successfully!")
        
    except Exception as e:
        logger.error(f"Error in portfolio allocation: {e}")
        print(f"\n❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()