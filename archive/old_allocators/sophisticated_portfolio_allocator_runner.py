#!/usr/bin/env python3
"""
Sophisticated Portfolio Allocator Runner
A production-ready runner script that integrates with the existing Options V4 system
to perform quantum-level portfolio allocation with VIX-based strategy selection.
"""

import os
import sys
import json
import argparse
import logging
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Optional, List

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import our sophisticated allocator
from core.sophisticated_portfolio_allocator import SophisticatedPortfolioAllocator
from database import SupabaseIntegration
from utils.logger import setup_logger, get_default_log_file

# Import VIX data fetcher
try:
    from data_scripts.india_vix_historical_data import IndiaVixHistoricalDataFetcher
    VIX_FETCHER_AVAILABLE = True
except ImportError:
    VIX_FETCHER_AVAILABLE = False

class ProductionAllocatorRunner:
    """Production runner for the sophisticated portfolio allocator"""
    
    def __init__(self, config_path: str = None, enable_database: bool = True):
        """Initialize the runner"""
        
        # Set up logging
        self.logger = setup_logger(
            'SophisticatedAllocator',
            log_file=get_default_log_file('sophisticated_allocator')
        )
        
        # Initialize database integration
        self.enable_database = enable_database
        self.db_integration = None
        
        if self.enable_database:
            try:
                self.db_integration = SupabaseIntegration(self.logger)
                self.logger.info("Database integration enabled")
            except Exception as e:
                self.logger.warning(f"Database integration failed: {e}")
                self.db_integration = None
        
        # Initialize sophisticated allocator
        self.allocator = SophisticatedPortfolioAllocator(
            config_path=config_path,
            db_integration=self.db_integration
        )
        
        self.logger.info("Sophisticated Portfolio Allocator Runner initialized")
    
    def load_strategies_from_database(self) -> Optional[Dict]:
        """Load strategies from the database with real data integration"""
        
        if not self.db_integration or not self.db_integration.client:
            self.logger.error("Database integration not available")
            return None
        
        try:
            # Use Supabase query builder instead of raw SQL
            # First, get strategies from the last 2 days
            from datetime import timezone
            two_days_ago = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
            
            # Query strategies table
            strategies_result = self.db_integration.client.table('strategies').select(
                'id, stock_name, strategy_name, strategy_type, probability_of_profit, '
                'risk_reward_ratio, total_score, net_premium, conviction_level, '
                'market_outlook, iv_environment, spot_price, generated_on'
            ).gte('generated_on', two_days_ago).gte('probability_of_profit', 0.3).gte('total_score', 0.4).order('total_score', desc=False).execute()
            
            if not strategies_result.data:
                self.logger.warning("No strategies found in database")
                return {'strategies': [], 'status': 'no_data'}
            
            strategies = strategies_result.data
            
            # For each strategy, get its details for open interest and volume
            for strategy in strategies:
                # Try to get details - different tables might have different column names
                try:
                    strategy_details_result = self.db_integration.client.table('strategy_details').select(
                        '*'
                    ).eq('strategy_id', strategy['id']).execute()
                except Exception as e:
                    self.logger.debug(f"Could not fetch strategy details: {e}")
                    strategy_details_result = None
                
                if strategy_details_result and strategy_details_result.data:
                    # Sum up open interest and volume
                    total_oi = sum(d.get('open_interest', 0) or 0 for d in strategy_details_result.data)
                    total_volume = sum(d.get('volume', 0) or 0 for d in strategy_details_result.data)
                    strategy['open_interest'] = total_oi
                    strategy['volume'] = total_volume
                else:
                    strategy['open_interest'] = 0
                    strategy['volume'] = 0
            
            self.logger.info(f"Loaded {len(strategies)} strategies from database")
            return {'strategies': strategies, 'status': 'success'}
                
        except Exception as e:
            self.logger.error(f"Error loading strategies from database: {e}")
            return None
    
    def get_real_vix_data(self) -> Dict:
        """Get real VIX data using the VIX fetcher"""
        
        try:
            if VIX_FETCHER_AVAILABLE:
                vix_fetcher = IndiaVixHistoricalDataFetcher()
                
                # Get last 90 days of VIX data for percentile calculation
                historical_data = vix_fetcher.get_historical_data(days=90)
                
                if historical_data and len(historical_data) > 0:
                    # Extract closing prices
                    vix_values = [record['close'] for record in historical_data if 'close' in record]
                    
                    if vix_values:
                        # Current VIX is the most recent value
                        current_vix = vix_values[-1]
                        
                        # Calculate percentile
                        vix_percentile = (sum(1 for v in vix_values if v <= current_vix) / len(vix_values)) * 100
                        
                        self.logger.info(f"Retrieved real VIX data: Current {current_vix:.2f}, Percentile {vix_percentile:.1f}")
                        
                        return {
                            'current_vix': current_vix,
                            'vix_percentile': vix_percentile,
                            'source': 'dhan_api'
                        }
            
            self.logger.warning("VIX fetcher not available, falling back to database")
        except Exception as e:
            self.logger.error(f"Error fetching VIX data: {e}")
        
        # Fallback to database or defaults
        return None
    
    def get_market_environment_from_database(self) -> Dict:
        """Get real market environment data from database or API"""
        
        try:
            # First try to get real VIX data from API
            vix_data = self.get_real_vix_data()
            
            if vix_data:
                # Successfully got VIX from API
                market_env = {
                    'current_vix': vix_data['current_vix'],
                    'vix_percentile': vix_data['vix_percentile'],
                    'iv_contango': 0.0,  # Would need options chain data
                    'last_updated': datetime.now().isoformat(),
                    'source': vix_data['source']
                }
            else:
                # Try to get from database
                if self.db_integration and self.db_integration.client:
                    # Query market_conditions table
                    result = self.db_integration.client.table('market_conditions').select(
                        'vix_level, vix_percentile, updated_at'
                    ).order('updated_at', desc=True).limit(1).execute()
                    
                    if result.data and len(result.data) > 0:
                        data = result.data[0]
                        market_env = {
                            'current_vix': data.get('vix_level', 15.0),
                            'vix_percentile': data.get('vix_percentile', 50.0),
                            'iv_contango': 0.0,
                            'last_updated': data.get('updated_at', datetime.now().isoformat()),
                            'source': 'database'
                        }
                    else:
                        # Use defaults if no data found
                        market_env = {
                            'current_vix': 15.0,
                            'vix_percentile': 50.0,
                            'iv_contango': 0.0,
                            'last_updated': datetime.now().isoformat(),
                            'source': 'default'
                        }
                else:
                    # No database available, use defaults
                    market_env = {
                        'current_vix': 15.0,
                        'vix_percentile': 50.0,
                        'iv_contango': 0.0,
                        'last_updated': datetime.now().isoformat(),
                        'source': 'default'
                    }
            
            self.logger.info(f"Market environment: VIX {market_env['current_vix']:.2f}, "
                           f"Percentile: {market_env['vix_percentile']:.1f} (Source: {market_env['source']})")
            
            return market_env
            
        except Exception as e:
            self.logger.error(f"Error getting market environment: {e}")
            # Return default environment
            return {
                'current_vix': 15.0,
                'vix_percentile': 50.0,
                'iv_contango': 0.0,
                'last_updated': datetime.now().isoformat(),
                'source': 'error_default'
            }
    
    def update_database_with_allocations(self, allocations: List[Dict]) -> bool:
        """Update database with allocation results"""
        
        if not self.db_integration or not self.db_integration.client or not allocations:
            self.logger.warning("Cannot update database: missing integration or allocations")
            return False
        
        try:
            self.logger.info("Updating database with sophisticated allocations...")
            
            # Step 1: Clear previous allocations
            clear_result = self.db_integration.client.table('strategies').update({
                'marked_for_execution': False,
                'execution_priority': 0,
                'execution_status': 'pending',
                'execution_notes': None
            }).eq('marked_for_execution', True).execute()
            
            self.logger.info("Cleared previous allocation marks")
            
            # Step 2: Mark new strategies
            updated_count = 0
            
            for allocation in allocations:
                try:
                    # Calculate priority (higher allocation = higher priority)
                    priority = int(allocation.get('allocation_percent', 0) * 1000)
                    
                    # Create execution notes
                    notes = (
                        f"Sophisticated Allocator: {allocation.get('allocation_percent', 0):.1f}% allocation, "
                        f"Quantum Score: {allocation.get('quantum_score', 0):.1f}, "
                        f"VIX Fit: {allocation.get('vix_fit_score', 0):.1f}"
                    )
                    
                    # Update strategy
                    update_result = self.db_integration.client.table('strategies').update({
                        'marked_for_execution': True,
                        'execution_status': 'marked',
                        'execution_priority': priority,
                        'execution_notes': notes
                    }).eq('id', allocation.get('strategy_id')).execute()
                    
                    if update_result.data:
                        updated_count += len(update_result.data)
                        self.logger.debug(f"Updated strategy {allocation.get('strategy_id')}: "
                                        f"{allocation.get('stock_name')} - {allocation.get('strategy_name')}")
                    
                except Exception as e:
                    self.logger.error(f"Error updating strategy {allocation.get('strategy_id')}: {e}")
            
            self.logger.info(f"Successfully updated {updated_count} strategies in database")
            return updated_count > 0
            
        except Exception as e:
            self.logger.error(f"Error updating database with allocations: {e}")
            return False
    
    def run_allocation(self, update_database: bool = True, save_report: bool = True) -> Dict:
        """Run the complete allocation process"""
        
        self.logger.info("=" * 60)
        self.logger.info("SOPHISTICATED OPTIONS PORTFOLIO ALLOCATOR")
        self.logger.info("=" * 60)
        
        start_time = datetime.now()
        
        try:
            # Step 1: Load real market environment
            market_env = self.get_market_environment_from_database()
            
            # Update allocator with real data
            self.allocator.current_vix = market_env['current_vix']
            self.allocator.current_vix_percentile = market_env['vix_percentile']
            
            # Step 2: Load real strategies data
            if self.enable_database:
                strategies_data = self.load_strategies_from_database()
                if strategies_data and strategies_data['status'] == 'success' and strategies_data['strategies']:
                    # Convert to DataFrame format expected by allocator
                    import pandas as pd
                    self.allocator.strategies_df = pd.DataFrame(strategies_data['strategies'])
                    # Also set external strategies for the allocator's internal logic
                    self.allocator.set_external_strategies(strategies_data['strategies'])
                    self.logger.info(f"Using {len(strategies_data['strategies'])} strategies from database")
                else:
                    self.logger.warning("Using mock data due to database issues or no strategies found")
            
            # Step 3: Execute sophisticated allocation
            allocation_result = self.allocator.execute_allocation()
            
            if 'error' in allocation_result:
                self.logger.error(f"Allocation failed: {allocation_result['error']}")
                return allocation_result
            
            # Add market environment to result
            allocation_result['market_environment'] = {
                'vix_level': market_env['current_vix'],
                'vix_percentile': market_env['vix_percentile'],
                'vix_environment': self.allocator._get_vix_environment() if hasattr(self.allocator, '_get_vix_environment') else 'unknown',
                'source': market_env['source']
            }
            
            # Step 4: Update database with results
            if update_database and self.enable_database:
                # Convert allocated strategies to list of dicts for database update
                allocations_list = []
                if hasattr(self.allocator, 'allocated_strategies'):
                    self.logger.info(f"Found {len(self.allocator.allocated_strategies)} allocated strategies")
                    for strategy in self.allocator.allocated_strategies:
                        # Handle StrategyAllocation objects which have attributes, not dict methods
                        allocations_list.append({
                            'strategy_id': getattr(strategy, 'strategy_id', getattr(strategy, 'id', None)),
                            'stock_name': getattr(strategy, 'stock_name', ''),
                            'strategy_name': getattr(strategy, 'strategy_name', ''),
                            'allocation_percent': getattr(strategy, 'allocation_percent', 0),
                            'quantum_score': getattr(strategy, 'quantum_score', 0),
                            'vix_fit_score': getattr(strategy, 'vix_fit_score', 0)
                        })
                
                update_success = self.update_database_with_allocations(allocations_list)
                allocation_result['database_updated'] = update_success
            
            # Step 5: Save detailed report
            if save_report:
                report_path = self.save_allocation_report(allocation_result)
                allocation_result['report_saved'] = report_path
            
            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()
            allocation_result['execution_time_seconds'] = execution_time
            
            # Log summary
            metrics = allocation_result.get('portfolio_metrics', {})
            self.logger.info(f"Allocation completed successfully:")
            self.logger.info(f"  • Strategies: {metrics.get('total_strategies', 0)}")
            self.logger.info(f"  • Capital Allocated: {metrics.get('total_allocation_percent', 0):.1f}%")
            self.logger.info(f"  • Expected Return: {metrics.get('expected_annual_return', 0):.1f}%")
            self.logger.info(f"  • Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}")
            self.logger.info(f"  • Execution Time: {execution_time:.1f} seconds")
            
            return allocation_result
            
        except Exception as e:
            self.logger.error(f"Error in allocation process: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {
                'error': str(e),
                'execution_time_seconds': (datetime.now() - start_time).total_seconds()
            }
    
    def save_allocation_report(self, allocation_result: Dict) -> str:
        """Save detailed allocation report to file"""
        
        try:
            # Create results directory if it doesn't exist
            results_dir = 'results'
            os.makedirs(results_dir, exist_ok=True)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'sophisticated_allocation_report_{timestamp}.json'
            filepath = os.path.join(results_dir, filename)
            
            # Save report
            with open(filepath, 'w') as f:
                json.dump(allocation_result, f, indent=2, default=str)
            
            self.logger.info(f"Allocation report saved to: {filepath}")
            return filepath
            
        except Exception as e:
            self.logger.error(f"Error saving allocation report: {e}")
            return ""
    
    def print_allocation_summary(self, allocation_result: Dict):
        """Print a human-readable allocation summary"""
        
        if 'error' in allocation_result:
            print(f"❌ Allocation failed: {allocation_result['error']}")
            return
        
        metrics = allocation_result.get('portfolio_metrics', {})
        
        print("\n" + "=" * 80)
        print("🚀 SOPHISTICATED OPTIONS PORTFOLIO ALLOCATION SUMMARY")
        print("=" * 80)
        
        print(f"\n📊 PORTFOLIO METRICS:")
        print(f"   • Total Strategies: {metrics.get('total_strategies', 0)}")
        print(f"   • Capital Allocated: ₹{metrics.get('total_capital_allocated', 0):,.0f} ({metrics.get('total_allocation_percent', 0):.1f}%)")
        print(f"   • Expected Annual Return: {metrics.get('expected_annual_return', 0):.1f}%")
        print(f"   • Portfolio Volatility: {metrics.get('portfolio_volatility', 0):.1f}%")
        print(f"   • Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}")
        
        greeks = metrics.get('portfolio_greeks', {})
        print(f"\n🏛️ PORTFOLIO GREEKS:")
        print(f"   • Delta: {greeks.get('delta', 0):.3f}")
        print(f"   • Gamma: {greeks.get('gamma', 0):.3f}")
        print(f"   • Theta: {greeks.get('theta', 0):.3f}")
        print(f"   • Vega: {greeks.get('vega', 0):.3f}")
        
        # Top strategies
        top_strategies = allocation_result.get('top_strategies', [])
        if top_strategies:
            print(f"\n🏆 TOP 5 ALLOCATED STRATEGIES:")
            for i, strategy in enumerate(top_strategies[:5], 1):
                print(f"   {i}. {strategy['stock_name']} - {strategy['strategy_name']}")
                print(f"      Allocation: {strategy['allocation_percent']:.1f}% (₹{strategy['capital_amount']:,.0f})")
                print(f"      Quantum Score: {strategy['quantum_score']:.1f}, Kelly: {strategy['kelly_percent']:.1f}%")
        
        # Allocation by industry
        by_industry = allocation_result.get('allocation_by_industry', {})
        if by_industry:
            print(f"\n🏭 ALLOCATION BY INDUSTRY:")
            for industry, data in sorted(by_industry.items(), 
                                       key=lambda x: x[1]['allocation_percent'], reverse=True)[:5]:
                print(f"   • {industry}: {data['allocation_percent']:.1f}% ({data['strategy_count']} strategies)")
        
        # Market environment
        market_env = allocation_result.get('market_environment', {})
        if market_env:
            print(f"\n🌍 MARKET ENVIRONMENT:")
            print(f"   • VIX Level: {market_env.get('vix_level', 'N/A')}")
            print(f"   • VIX Percentile: {market_env.get('vix_percentile', 'N/A')}")
            print(f"   • Environment: {market_env.get('vix_environment', 'N/A').replace('_', ' ').title()}")
            print(f"   • Data Source: {market_env.get('source', 'N/A')}")
        
        print("\n" + "=" * 80)
        
        # Database update status
        if allocation_result.get('database_updated'):
            print("✅ Database updated with allocation priorities")
        else:
            print("⚠️  Database not updated (run with --update-database to enable)")
        
        # Report file
        if allocation_result.get('report_saved'):
            print(f"📄 Detailed report saved: {allocation_result['report_saved']}")
        
        print(f"⏱️  Execution time: {allocation_result.get('execution_time_seconds', 0):.1f} seconds")
        print("=" * 80)


def main():
    """Main CLI interface"""
    
    parser = argparse.ArgumentParser(
        description="Sophisticated Options Portfolio Allocator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run allocation with database updates
  python sophisticated_portfolio_allocator_runner.py --update-database
  
  # Run allocation without database (dry run)
  python sophisticated_portfolio_allocator_runner.py --no-database
  
  # Use custom config file
  python sophisticated_portfolio_allocator_runner.py --config custom_config.yaml
  
  # Quiet mode (minimal output)
  python sophisticated_portfolio_allocator_runner.py --quiet
        """
    )
    
    parser.add_argument('--config', '-c', 
                       help='Path to configuration YAML file')
    parser.add_argument('--update-database', action='store_true',
                       help='Update database with allocation results')
    parser.add_argument('--no-database', action='store_true',
                       help='Run without database integration (uses mock data)')
    parser.add_argument('--quiet', '-q', action='store_true',
                       help='Minimal output mode')
    parser.add_argument('--save-report', action='store_true', default=True,
                       help='Save detailed allocation report (default: True)')
    
    args = parser.parse_args()
    
    # Initialize runner
    enable_database = not args.no_database
    runner = ProductionAllocatorRunner(
        config_path=args.config,
        enable_database=enable_database
    )
    
    # Run allocation
    result = runner.run_allocation(
        update_database=args.update_database,
        save_report=args.save_report
    )
    
    # Print summary unless in quiet mode
    if not args.quiet:
        runner.print_allocation_summary(result)
    
    # Exit with appropriate code
    if 'error' in result:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()