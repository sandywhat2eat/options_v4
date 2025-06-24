#!/usr/bin/env python3
"""
Database-Integrated Sophisticated Portfolio Allocator
Connects to real Supabase database and processes actual strategies
"""

import os
import sys
import json
import pandas as pd
import logging
from datetime import datetime
from typing import Dict, List, Optional

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.sophisticated_portfolio_allocator import SophisticatedPortfolioAllocator
from database import SupabaseIntegration
from utils.logger import setup_logger, get_default_log_file

class DatabaseIntegratedAllocator:
    """Database-integrated sophisticated portfolio allocator"""
    
    def __init__(self):
        """Initialize with real database connection"""
        
        # Set up logging
        self.logger = setup_logger(
            'SophisticatedAllocatorDB',
            log_file=get_default_log_file('sophisticated_allocator_db')
        )
        
        # Initialize database integration
        try:
            self.db_integration = SupabaseIntegration(self.logger)
            self.logger.info("Database integration established")
        except Exception as e:
            self.logger.error(f"Database initialization failed: {e}")
            raise
        
        # Initialize sophisticated allocator
        self.allocator = SophisticatedPortfolioAllocator(
            config_path="config/options_portfolio_config.yaml",
            db_integration=self.db_integration
        )
        
        self.logger.info("Database-Integrated Sophisticated Allocator initialized")
    
    def load_real_strategies_data(self) -> pd.DataFrame:
        """Load real strategies from Supabase database"""
        
        try:
            self.logger.info("Loading strategies from Supabase database...")
            
            # Query strategies with comprehensive data
            strategies_query = """
            SELECT 
                id,
                stock_name,
                strategy_name,
                strategy_type,
                probability_of_profit,
                risk_reward_ratio,
                total_score,
                net_premium,
                conviction_level,
                market_outlook,
                iv_environment,
                spot_price,
                generated_on,
                marked_for_execution,
                execution_status,
                execution_priority
            FROM strategies
            WHERE generated_on >= CURRENT_DATE - INTERVAL '2 days'
            AND total_score >= 0.4
            AND probability_of_profit >= 0.3
            ORDER BY total_score DESC
            """
            
            # Use direct table query for better compatibility
            result = self.db_integration.client.table('strategies').select(
                'id,stock_name,strategy_name,strategy_type,probability_of_profit,risk_reward_ratio,total_score,net_premium,conviction_level,market_outlook,iv_environment,spot_price,generated_on,marked_for_execution,execution_status,execution_priority'
            ).gte('generated_on', '2025-06-23T00:00:00').gte('total_score', 0.4).gte('probability_of_profit', 0.3).order('total_score', desc=True).execute()
            
            if not result.data:
                self.logger.warning("No strategies found in database")
                return pd.DataFrame()
            
            # Convert to DataFrame
            strategies_df = pd.DataFrame(result.data)
            
            # Data type conversions and cleaning
            strategies_df['probability_of_profit'] = pd.to_numeric(strategies_df['probability_of_profit'], errors='coerce')
            strategies_df['risk_reward_ratio'] = pd.to_numeric(strategies_df['risk_reward_ratio'], errors='coerce')
            strategies_df['total_score'] = pd.to_numeric(strategies_df['total_score'], errors='coerce')
            
            # Fill NaN values
            strategies_df['probability_of_profit'] = strategies_df['probability_of_profit'].fillna(0.5)
            strategies_df['risk_reward_ratio'] = strategies_df['risk_reward_ratio'].fillna(1.0)
            strategies_df['total_score'] = strategies_df['total_score'].fillna(0.5)
            
            # Add calculated fields needed by allocator
            strategies_df['kelly_percentage'] = 0.0
            strategies_df['quantum_score'] = 0.0
            
            self.logger.info(f"Loaded {len(strategies_df)} strategies from database")
            self.logger.info(f"Strategy types: {strategies_df['strategy_type'].value_counts().to_dict()}")
            self.logger.info(f"Score range: {strategies_df['total_score'].min():.3f} - {strategies_df['total_score'].max():.3f}")
            
            return strategies_df
            
        except Exception as e:
            self.logger.error(f"Error loading strategies from database: {e}")
            return pd.DataFrame()
    
    def get_current_vix_environment(self) -> Dict:
        """Get current VIX environment (mock for now, would be real in production)"""
        
        # In production, this would query actual market data
        # For now, using the current market conditions
        vix_data = {
            'current_vix': 13.67,
            'vix_percentile': 11.86,
            'iv_contango': 2.5,
            'last_updated': datetime.now().isoformat()
        }
        
        self.logger.info(f"VIX Environment: {vix_data['current_vix']} ({vix_data['vix_percentile']:.1f}th percentile)")
        return vix_data
    
    def update_database_allocations(self, allocations: List) -> bool:
        """Update database with sophisticated allocation results"""
        
        if not allocations:
            self.logger.warning("No allocations to update in database")
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
            
            self.logger.info(f"Cleared previous allocation marks")
            
            # Step 2: Mark new strategies for execution
            updated_count = 0
            total_allocation = 0.0
            
            for allocation in allocations:
                try:
                    # Calculate execution priority (higher allocation = higher priority)
                    priority = int(allocation.allocation_percent * 1000)
                    
                    # Create detailed execution notes
                    execution_notes = (
                        f"Sophisticated Allocator: {allocation.allocation_percent:.2f}% allocation, "
                        f"Quantum Score: {allocation.quantum_score:.1f}, "
                        f"Kelly: {allocation.kelly_percent*100:.1f}%, "
                        f"Industry: {allocation.industry}"
                    )
                    
                    # Update strategy in database
                    update_result = self.db_integration.client.table('strategies').update({
                        'marked_for_execution': True,
                        'execution_status': 'marked',
                        'execution_priority': priority,
                        'execution_notes': execution_notes
                    }).eq('id', allocation.strategy_id).execute()
                    
                    if update_result.data:
                        updated_count += 1
                        total_allocation += allocation.allocation_percent
                        self.logger.debug(f"Marked: {allocation.stock_name} - {allocation.strategy_name} ({allocation.allocation_percent:.1f}%)")
                    
                except Exception as e:
                    self.logger.error(f"Error updating strategy {allocation.strategy_id}: {e}")
            
            self.logger.info(f"Successfully marked {updated_count} strategies for execution")
            self.logger.info(f"Total allocation: {total_allocation:.1f}%")
            
            return updated_count > 0
            
        except Exception as e:
            self.logger.error(f"Error updating database allocations: {e}")
            return False
    
    def run_sophisticated_allocation(self, update_db: bool = True) -> Dict:
        """Run the complete sophisticated allocation process with real data"""
        
        self.logger.info("="*80)
        self.logger.info("SOPHISTICATED OPTIONS PORTFOLIO ALLOCATOR - DATABASE INTEGRATION")
        self.logger.info("="*80)
        
        start_time = datetime.now()
        
        try:
            # Step 1: Load real strategies from database
            strategies_df = self.load_real_strategies_data()
            
            if strategies_df.empty:
                raise ValueError("No strategies available in database")
            
            # Set strategies data in allocator
            self.allocator.strategies_df = strategies_df
            
            # Step 2: Get current market environment
            market_env = self.get_current_vix_environment()
            self.allocator.current_vix = market_env['current_vix']
            self.allocator.current_vix_percentile = market_env['vix_percentile']
            
            # Step 3: Run sophisticated allocation
            self.logger.info("Executing sophisticated allocation algorithm...")
            allocation_result = self.allocator.execute_allocation()
            
            if 'error' in allocation_result:
                raise Exception(f"Allocation failed: {allocation_result['error']}")
            
            # Step 4: Update database if requested
            if update_db:
                db_update_success = self.update_database_allocations(
                    self.allocator.allocated_strategies
                )
                allocation_result['database_updated'] = db_update_success
                
                if db_update_success:
                    self.logger.info("✅ Database successfully updated with allocation results")
                else:
                    self.logger.warning("⚠️ Database update failed")
            else:
                allocation_result['database_updated'] = False
                self.logger.info("ℹ️ Database update skipped (dry run mode)")
            
            # Step 5: Calculate execution time and add metadata
            execution_time = (datetime.now() - start_time).total_seconds()
            allocation_result['execution_time_seconds'] = execution_time
            allocation_result['strategies_analyzed'] = len(strategies_df)
            allocation_result['data_source'] = 'supabase_database'
            
            return allocation_result
            
        except Exception as e:
            self.logger.error(f"Sophisticated allocation failed: {e}")
            return {
                'error': str(e),
                'execution_time_seconds': (datetime.now() - start_time).total_seconds(),
                'strategies_analyzed': 0,
                'data_source': 'error'
            }
    
    def print_allocation_summary(self, result: Dict):
        """Print comprehensive allocation summary"""
        
        print("\n" + "="*90)
        print("🚀 SOPHISTICATED OPTIONS PORTFOLIO ALLOCATOR - RESULTS")
        print("="*90)
        
        if 'error' in result:
            print(f"❌ ALLOCATION FAILED: {result['error']}")
            return
        
        # Basic metrics
        metrics = result.get('portfolio_metrics', {})
        print(f"\n📊 PORTFOLIO PERFORMANCE:")
        print(f"   • Strategies Selected: {metrics.get('total_strategies', 0)}")
        print(f"   • Strategies Analyzed: {result.get('strategies_analyzed', 0)}")
        print(f"   • Selection Efficiency: {(metrics.get('total_strategies', 0) / max(result.get('strategies_analyzed', 1), 1) * 100):.1f}%")
        print(f"   • Capital Allocated: ₹{metrics.get('total_capital_allocated', 0):,.0f} ({metrics.get('total_allocation_percent', 0):.1f}%)")
        print(f"   • Expected Annual Return: {metrics.get('expected_annual_return', 0):.1f}%")
        print(f"   • Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}")
        
        # Top strategies
        top_strategies = result.get('top_strategies', [])
        if top_strategies:
            print(f"\n🏆 TOP 5 SELECTED STRATEGIES:")
            for i, strategy in enumerate(top_strategies[:5], 1):
                print(f"   {i}. {strategy['stock_name']} - {strategy['strategy_name']}")
                print(f"      💰 Allocation: {strategy['allocation_percent']:.1f}% (₹{strategy['capital_amount']:,.0f})")
                print(f"      🎯 Quantum Score: {strategy['quantum_score']:.1f}, Kelly: {strategy['kelly_percent']:.1f}%")
        
        # Industry breakdown
        by_industry = result.get('allocation_by_industry', {})
        if by_industry:
            print(f"\n🏭 INDUSTRY ALLOCATION:")
            sorted_industries = sorted(by_industry.items(), key=lambda x: x[1]['allocation_percent'], reverse=True)
            for industry, data in sorted_industries[:6]:
                print(f"   • {industry}: {data['allocation_percent']:.1f}% ({data['strategy_count']} strategies)")
        
        # Strategy type breakdown
        by_strategy_type = result.get('allocation_by_strategy_type', {})
        if by_strategy_type:
            print(f"\n📈 STRATEGY TYPE ALLOCATION:")
            sorted_types = sorted(by_strategy_type.items(), key=lambda x: x[1]['allocation_percent'], reverse=True)
            for strategy_type, data in sorted_types:
                print(f"   • {strategy_type}: {data['allocation_percent']:.1f}% ({data['strategy_count']} strategies)")
        
        # Market environment
        market_env = result.get('market_environment', {})
        print(f"\n🌍 MARKET ENVIRONMENT:")
        print(f"   • VIX Level: {market_env.get('vix_level', 'N/A')}")
        print(f"   • VIX Percentile: {market_env.get('vix_percentile', 'N/A'):.1f}th percentile")
        print(f"   • Environment: {market_env.get('vix_environment', 'N/A').replace('_', ' ').title()}")
        
        # Execution summary
        print(f"\n⚙️ EXECUTION SUMMARY:")
        print(f"   • Execution Time: {result.get('execution_time_seconds', 0):.1f} seconds")
        print(f"   • Data Source: {result.get('data_source', 'unknown').replace('_', ' ').title()}")
        
        if result.get('database_updated'):
            print(f"   • Database Status: ✅ Updated with allocation priorities")
        else:
            print(f"   • Database Status: ⚠️ Not updated (use --update-db flag)")
        
        print("\n" + "="*90)

def main():
    """Main execution"""
    
    import argparse
    
    parser = argparse.ArgumentParser(description="Database-Integrated Sophisticated Portfolio Allocator")
    parser.add_argument('--update-db', action='store_true', help='Update database with allocation results')
    parser.add_argument('--dry-run', action='store_true', help='Run allocation without database updates')
    
    args = parser.parse_args()
    
    try:
        # Initialize allocator
        allocator = DatabaseIntegratedAllocator()
        
        # Run allocation
        update_database = args.update_db and not args.dry_run
        result = allocator.run_sophisticated_allocation(update_db=update_database)
        
        # Print results
        allocator.print_allocation_summary(result)
        
        # Save detailed report
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = f'results/db_allocation_report_{timestamp}.json'
        
        os.makedirs('results', exist_ok=True)
        with open(report_file, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        
        print(f"📄 Detailed report saved: {report_file}")
        
        # Exit with appropriate code
        exit_code = 0 if 'error' not in result else 1
        sys.exit(exit_code)
        
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()