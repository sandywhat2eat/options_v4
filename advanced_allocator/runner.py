"""
Advanced Options Allocator Runner
CLI interface for running the advanced allocation system
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path
import os
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from core.allocator import AdvancedOptionsAllocator
from database.supabase_integration import SupabaseIntegration

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'../logs/advanced_allocator_{datetime.now().strftime("%Y%m%d")}.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Main runner function"""
    parser = argparse.ArgumentParser(
        description='Advanced Options Portfolio Allocator'
    )
    
    parser.add_argument(
        '--capital',
        type=float,
        default=10000000,  # 1 Cr
        help='Total capital for options allocation (default: 10000000)'
    )
    
    parser.add_argument(
        '--vix',
        type=float,
        default=None,
        help='Current VIX level (fetched automatically if not provided)'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='Output file path for allocation results'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run without saving to database'
    )
    
    parser.add_argument(
        '--update-database',
        action='store_true',
        help='Update allocations in database'
    )
    
    args = parser.parse_args()
    
    try:
        # Load environment variables
        load_dotenv()
        
        # Initialize Supabase client
        logger.info("Connecting to database...")
        supabase_integration = SupabaseIntegration()
        supabase = supabase_integration.client
        
        # Initialize allocator first to access MarketConditionsAnalyzer
        logger.info(f"Initializing allocator with capital: ₹{args.capital:,.0f}")
        allocator = AdvancedOptionsAllocator(supabase, args.capital)
        
        # Get current VIX if not provided - use MarketConditionsAnalyzer
        vix_level = args.vix
        if vix_level is None:
            try:
                vix_analysis = allocator.market_analyzer.market_analyzer.get_vix_environment()
                vix_level = vix_analysis.get('current_vix', 20.0)
                logger.info(f"Fetched real VIX from MarketConditionsAnalyzer: {vix_level}")
            except Exception as e:
                logger.warning(f"Could not fetch real VIX: {e}, using default 20.0")
                vix_level = 20.0
        
        # Run allocation
        logger.info("Running portfolio allocation...")
        result = allocator.allocate_portfolio(vix_level)
        
        # Display results
        display_allocation_results(result)
        
        # Save results if output path provided
        if args.output:
            allocator.save_allocation_result(result, args.output)
        else:
            # Default output path
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"results/advanced_allocation_{timestamp}.json"
            allocator.save_allocation_result(result, output_path)
            logger.info(f"Results saved to: {output_path}")
        
        # Update database if requested
        if args.update_database and not args.dry_run:
            update_database_allocations(supabase, result)
        
    except Exception as e:
        logger.error(f"Error in allocation: {e}")
        sys.exit(1)


def get_current_vix(supabase) -> float:
    """Get current VIX level - MarketConditionsAnalyzer handles VIX data fetching"""
    logger.info("Using default VIX level 20.0 - MarketConditionsAnalyzer will fetch real VIX data")
    return 20.0


def display_allocation_results(result):
    """Display allocation results in readable format"""
    print("\n" + "="*80)
    print("ADVANCED OPTIONS PORTFOLIO ALLOCATION RESULTS")
    print("="*80)
    
    # Market Analysis
    print("\n1. MARKET ANALYSIS")
    print("-"*40)
    analysis = result.market_analysis
    print(f"Market State: {analysis['market_state'].upper()}")
    print(f"Direction Score: {analysis['direction_score']:.2f}")
    print(f"Confidence: {analysis['confidence']:.1%}")
    print(f"Technical: {analysis['technical_score']:.2f} | "
          f"Options Flow: {analysis['options_flow_score']:.2f} | "
          f"Price Action: {analysis['price_action_score']:.2f}")
    
    # Portfolio Summary
    print("\n2. PORTFOLIO SUMMARY")
    print("-"*40)
    summary = result.summary
    print(f"Total Positions: {summary['total_positions']}")
    print(f"Long Positions: {summary['long_positions']} | "
          f"Short Positions: {summary['short_positions']}")
    print(f"Total Premium at Risk: ₹{summary['total_premium_at_risk']:,.0f}")
    print(f"Total Position Value: ₹{summary['total_position_value']:,.0f}")
    print(f"Average Probability: {summary['average_probability']:.1%}")
    
    # Market Cap Distribution
    print("\n3. MARKET CAP DISTRIBUTION")
    print("-"*40)
    for cap, data in summary['market_cap_distribution'].items():
        print(f"{cap.replace('_', ' ').title()}: "
              f"{data['count']} positions, ₹{data['value']:,.0f}")
    
    # Strategy Distribution
    print("\n4. STRATEGY DISTRIBUTION")
    print("-"*40)
    for strategy, data in summary['strategy_distribution'].items():
        print(f"{strategy}: {data['count']} positions, ₹{data['value']:,.0f}")
    
    # Top Positions
    print("\n5. TOP POSITIONS BY RISK")
    print("-"*40)
    print(f"{'Symbol':<10} {'Strategy':<20} {'Type':<6} {'Lots':<5} "
          f"{'Risk':>10} {'Prob':>6} {'Score':>6}")
    print("-"*70)
    
    # Sort positions by premium at risk
    sorted_positions = sorted(
        result.allocations, 
        key=lambda x: x['premium_at_risk'], 
        reverse=True
    )[:10]
    
    for pos in sorted_positions:
        print(f"{pos['symbol']:<10} "
              f"{pos['strategy_name']:<20} "
              f"{pos['position_type']:<6} "
              f"{pos['number_of_lots']:<5} "
              f"₹{pos['premium_at_risk']:>9,.0f} "
              f"{pos['probability_of_profit']:>5.1%} "
              f"{pos['total_score']:>6.2f}")
    
    print("\n" + "="*80)


def update_database_allocations(supabase, result):
    """Update allocations in database"""
    try:
        logger.info("Updating database allocations...")
        
        # Prepare allocation records
        allocations = []
        for position in result.allocations:
            allocation = {
                'symbol': position['symbol'],
                'strategy_id': position.get('strategy_id'),
                'strategy_name': position['strategy_name'],
                'position_type': position['position_type'],
                'allocated_capital': position['allocated_capital'],
                'number_of_lots': position['number_of_lots'],
                'premium_at_risk': position['premium_at_risk'],
                'position_value': position['position_value'],
                'probability_of_profit': position['probability_of_profit'],
                'conviction_level': position['conviction_level'],
                'market_cap': position['market_cap'],
                'industry': position['industry'],
                'allocation_date': datetime.now().isoformat(),
                'market_state': result.market_analysis['market_state'],
                'allocation_type': 'advanced'
            }
            allocations.append(allocation)
        
        # Insert allocations
        if allocations:
            response = supabase.table('portfolio_allocations').insert(allocations).execute()
            logger.info(f"Updated {len(allocations)} allocations in database")
        
    except Exception as e:
        logger.error(f"Error updating database: {e}")


if __name__ == "__main__":
    main()