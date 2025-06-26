#!/usr/bin/env python3
"""
Validation Script for Sophisticated Portfolio Allocator
Validates the complete end-to-end workflow integration
"""

import sys
import os
from datetime import datetime

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SupabaseIntegration
import pandas as pd

class SophisticatedAllocatorValidator:
    """Validates the sophisticated allocator integration"""
    
    def __init__(self):
        """Initialize validator"""
        self.db = SupabaseIntegration()
        
    def check_database_strategies(self):
        """Check available strategies in database"""
        
        print("🔍 CHECKING DATABASE STRATEGIES...")
        print("-" * 50)
        
        # Get total strategies
        total_result = self.db.client.table('strategies').select('count').execute()
        total_count = total_result.data[0]['count'] if total_result.data else 0
        
        # Get recent strategies (last 2 days)
        recent_result = self.db.client.table('strategies').select('count').gte('generated_on', '2025-06-23T00:00:00').execute()
        recent_count = recent_result.data[0]['count'] if recent_result.data else 0
        
        # Get quality strategies
        quality_result = self.db.client.table('strategies').select('count').gte('generated_on', '2025-06-23T00:00:00').gte('total_score', 0.5).gte('probability_of_profit', 0.4).execute()
        quality_count = quality_result.data[0]['count'] if quality_result.data else 0
        
        print(f"✅ Total strategies in database: {total_count}")
        print(f"✅ Recent strategies (last 2 days): {recent_count}")
        print(f"✅ High-quality strategies (score >0.5, prob >0.4): {quality_count}")
        
        # Check strategy type distribution
        type_result = self.db.client.table('strategies').select('strategy_type').gte('generated_on', '2025-06-23T00:00:00').execute()
        
        if type_result.data:
            types_df = pd.DataFrame(type_result.data)
            type_counts = types_df['strategy_type'].value_counts()
            print(f"\n📊 Strategy Type Distribution:")
            for strategy_type, count in type_counts.items():
                print(f"   • {strategy_type}: {count}")
        
        return recent_count > 0
    
    def check_current_allocations(self):
        """Check currently marked strategies"""
        
        print("\n🎯 CHECKING CURRENT ALLOCATIONS...")
        print("-" * 50)
        
        # Get marked strategies
        marked_result = self.db.client.table('strategies').select(
            'id,stock_name,strategy_name,marked_for_execution,execution_status,execution_priority,execution_notes'
        ).eq('marked_for_execution', True).order('execution_priority', desc=True).execute()
        
        if marked_result.data:
            print(f"✅ Strategies marked for execution: {len(marked_result.data)}")
            print(f"\n🏆 Top 5 marked strategies:")
            for i, strategy in enumerate(marked_result.data[:5], 1):
                print(f"   {i}. {strategy['stock_name']} - {strategy['strategy_name']}")
                print(f"      Priority: {strategy['execution_priority']}, Status: {strategy['execution_status']}")
                if strategy.get('execution_notes'):
                    print(f"      Notes: {strategy['execution_notes']}")
        else:
            print("⚠️ No strategies currently marked for execution")
        
        return len(marked_result.data) if marked_result.data else 0
    
    def simulate_execution_query(self):
        """Simulate the query that options_v4_executor.py would run"""
        
        print("\n🚀 SIMULATING EXECUTION ENGINE QUERY...")
        print("-" * 50)
        
        # This is the exact query that options_v4_executor.py would run
        execution_result = self.db.client.table('strategies').select(
            'id,stock_name,strategy_name,strategy_type,execution_priority'
        ).eq('marked_for_execution', True).eq('execution_status', 'marked').gt('execution_priority', 0).order('execution_priority', desc=True).execute()
        
        if execution_result.data:
            print(f"✅ Strategies ready for execution: {len(execution_result.data)}")
            print(f"\n📋 Execution Queue (top 10):")
            for i, strategy in enumerate(execution_result.data[:10], 1):
                print(f"   {i}. {strategy['stock_name']} - {strategy['strategy_name']} (Priority: {strategy['execution_priority']})")
        else:
            print("⚠️ No strategies ready for execution")
            print("   (Requires marked_for_execution=true, execution_status='marked', execution_priority>0)")
        
        return len(execution_result.data) if execution_result.data else 0
    
    def test_sophisticated_allocator_integration(self):
        """Test if sophisticated allocator would work with current data"""
        
        print("\n🧠 TESTING SOPHISTICATED ALLOCATOR COMPATIBILITY...")
        print("-" * 50)
        
        # Test database query that sophisticated allocator uses
        test_result = self.db.client.table('strategies').select(
            'id,stock_name,strategy_name,strategy_type,probability_of_profit,risk_reward_ratio,total_score'
        ).gte('generated_on', '2025-06-23T00:00:00').gte('total_score', 0.4).gte('probability_of_profit', 0.3).limit(5).execute()
        
        if test_result.data:
            print(f"✅ Compatible strategies found: {len(test_result.data)}")
            print(f"\n📊 Sample strategies for sophisticated allocator:")
            for i, strategy in enumerate(test_result.data, 1):
                print(f"   {i}. {strategy['stock_name']} - {strategy['strategy_name']}")
                print(f"      Score: {strategy['total_score']:.3f}, Prob: {strategy['probability_of_profit']:.1%}")
        else:
            print("❌ No compatible strategies found")
            print("   Requirements: total_score ≥ 0.4, probability_of_profit ≥ 0.3")
        
        return len(test_result.data) if test_result.data else 0
    
    def run_validation(self):
        """Run complete validation"""
        
        print("🔬 SOPHISTICATED PORTFOLIO ALLOCATOR - VALIDATION")
        print("=" * 70)
        
        # Step 1: Check database strategies
        strategies_available = self.check_database_strategies()
        
        # Step 2: Check current allocations
        current_allocations = self.check_current_allocations()
        
        # Step 3: Simulate execution query
        execution_ready = self.simulate_execution_query()
        
        # Step 4: Test sophisticated allocator compatibility
        allocator_compatible = self.test_sophisticated_allocator_integration()
        
        # Summary
        print("\n📋 VALIDATION SUMMARY")
        print("=" * 70)
        
        if strategies_available:
            print("✅ Database has sufficient strategies for analysis")
        else:
            print("❌ Database lacks sufficient strategies")
        
        if allocator_compatible > 0:
            print("✅ Sophisticated allocator can process existing strategies")
        else:
            print("❌ No strategies meet sophisticated allocator requirements")
        
        if execution_ready > 0:
            print("✅ Strategies are properly marked for execution")
        else:
            print("⚠️ No strategies currently marked for execution")
            print("   (Run sophisticated allocator with --update-db to mark strategies)")
        
        # Overall assessment
        print(f"\n🎯 OVERALL ASSESSMENT:")
        
        if strategies_available and allocator_compatible > 0:
            print("✅ READY: Sophisticated allocator can be deployed")
            print("   Next step: Run 'python sophisticated_allocator_db_runner.py --update-db'")
        elif strategies_available:
            print("⚠️ PARTIAL: Database has strategies but quality may be low")
            print("   Next step: Review strategy generation parameters")
        else:
            print("❌ NOT READY: Need to generate strategies first")
            print("   Next step: Run 'python main.py --risk moderate'")
        
        return strategies_available and allocator_compatible > 0

def main():
    """Main validation execution"""
    
    try:
        validator = SophisticatedAllocatorValidator()
        success = validator.run_validation()
        
        sys.exit(0 if success else 1)
        
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()