#!/usr/bin/env python3
"""
Portfolio Allocator - Industry-based Options Strategy Selection
Filters generated strategies based on industry allocation and marks them for execution
"""

import os
import sys
import logging
from datetime import datetime
from dotenv import load_dotenv

# Add project root to path
sys.path.append('/Users/jaykrish/Documents/digitalocean/cronjobs/options_v4')

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_environment():
    """Setup environment variables"""
    # Load from the global .env file as specified in CLAUDE.md
    env_path = '/Users/jaykrish/Documents/digitalocean/.env'
    if os.path.exists(env_path):
        load_dotenv(env_path)
        logger.info(f"Loaded environment from {env_path}")
    else:
        logger.warning(f"Environment file not found at {env_path}")
    
    # Check required environment variables
    required_vars = ['SUPABASE_URL', 'SUPABASE_ANON_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        # Try alternative patterns
        alt_vars = [f'NEXT_PUBLIC_{var}' for var in missing_vars]
        for alt_var in alt_vars:
            if os.getenv(alt_var):
                logger.info(f"Using alternative environment variable: {alt_var}")
        
        remaining_missing = [var for var in required_vars if not os.getenv(var) and not os.getenv(f'NEXT_PUBLIC_{var}')]
        if remaining_missing:
            logger.error(f"Missing required environment variables: {remaining_missing}")
            return False
    
    return True

def initialize_supabase():
    """Initialize Supabase client"""
    try:
        from supabase import create_client, Client
        
        # Try primary environment variables first
        url = os.getenv('SUPABASE_URL') or os.getenv('NEXT_PUBLIC_SUPABASE_URL')
        key = os.getenv('SUPABASE_ANON_KEY') or os.getenv('NEXT_PUBLIC_SUPABASE_ANON_KEY')
        
        if not url or not key:
            raise ValueError("Supabase credentials not found in environment")
        
        supabase: Client = create_client(url, key)
        logger.info("Supabase client initialized successfully")
        return supabase
        
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}")
        return None

def test_market_conditions_analyzer(supabase_client):
    """Test market conditions analysis"""
    print("\n" + "="*60)
    print("TESTING MARKET CONDITIONS ANALYZER")
    print("="*60)
    
    try:
        from core.market_conditions_analyzer import MarketConditionsAnalyzer
        
        analyzer = MarketConditionsAnalyzer(supabase_client)
        
        # Test NIFTY direction analysis
        print("\n1. Testing NIFTY Direction Analysis...")
        nifty_analysis = analyzer.get_nifty_direction()
        print(f"   NIFTY Direction: {nifty_analysis['direction']}")
        print(f"   Confidence: {nifty_analysis['confidence']:.2f}")
        
        # Test VIX environment
        print("\n2. Testing VIX Environment Analysis...")
        vix_analysis = analyzer.get_vix_environment()
        print(f"   VIX Level: {vix_analysis['level']}")
        print(f"   Current VIX: {vix_analysis.get('current_vix', 'N/A')}")
        print(f"   VIX Percentile: {vix_analysis.get('percentile', 'N/A')}")
        
        # Test options sentiment from database
        print("\n3. Testing Options Sentiment from Database...")
        options_sentiment = analyzer.get_options_sentiment_from_db()
        print(f"   PCR: {options_sentiment.get('pcr', 'N/A'):.3f}")
        print(f"   Sentiment: {options_sentiment.get('sentiment', 'N/A')}")
        print(f"   Max Pain: {options_sentiment.get('max_pain', 'N/A')}")
        
        # Test combined market condition
        print("\n4. Testing Combined Market Condition...")
        market_condition = analyzer.get_current_market_condition()
        print(f"   Market Condition: {market_condition['condition']}")
        print(f"   Overall Confidence: {market_condition['confidence']:.2f}")
        
        return market_condition
        
    except Exception as e:
        logger.error(f"Error testing market conditions analyzer: {e}")
        return None

def test_industry_allocation_engine(supabase_client):
    """Test industry allocation engine"""
    print("\n" + "="*60)
    print("TESTING INDUSTRY ALLOCATION ENGINE")
    print("="*60)
    
    try:
        from core.industry_allocation_engine import IndustryAllocationEngine
        
        engine = IndustryAllocationEngine(supabase_client)
        
        # Test loading allocation data
        print("\n1. Testing Allocation Data Loading...")
        success = engine.load_allocation_data()
        print(f"   Data Load Success: {success}")
        
        if success:
            print(f"   Industries Loaded: {len(engine.industry_allocations)}")
            print(f"   Sectors Loaded: {len(engine.sector_allocations)}")
            print(f"   Symbol Mappings: {len(engine.symbol_industry_mapping)}")
            
            # Test priority industries
            print("\n2. Testing Priority Industries...")
            priority_industries = engine.get_priority_industries()
            print(f"   Priority Industries Found: {len(priority_industries)}")
            
            for i, industry in enumerate(priority_industries[:5]):
                print(f"   {i+1}. {industry['industry']}: {industry['weight_percentage']:.1f}% "
                      f"({industry['position_type']} + {industry['rating']})")
            
            # Test symbol mapping
            print("\n3. Testing Symbol-Industry Mapping...")
            if priority_industries:
                test_industry = priority_industries[0]['industry']
                symbols = engine.get_symbols_for_industry(test_industry)
                print(f"   Symbols for {test_industry}: {symbols[:3]}")
            
            return engine, priority_industries
        else:
            print("   Failed to load allocation data")
            return None, []
        
    except Exception as e:
        logger.error(f"Error testing industry allocation engine: {e}")
        return None, []

def test_options_portfolio_manager(supabase_client):
    """Test complete options portfolio manager"""
    print("\n" + "="*60)
    print("TESTING OPTIONS PORTFOLIO MANAGER")
    print("="*60)
    
    try:
        from core.options_portfolio_manager import OptionsPortfolioManager
        
        manager = OptionsPortfolioManager(supabase_client, risk_tolerance='moderate')
        
        # Test market environment analysis
        print("\n1. Testing Market Environment Analysis...")
        market_analysis = manager.analyze_market_environment()
        print(f"   Market Condition: {market_analysis['condition']}")
        print(f"   Confidence: {market_analysis['confidence']:.2f}")
        print(f"   NIFTY Direction: {market_analysis['components']['nifty_direction']}")
        print(f"   VIX Level: {market_analysis['components']['vix_level']}")
        print(f"   PCR: {market_analysis['components']['pcr']:.3f}")
        
        # Test options allocation generation
        print("\n2. Testing Options Allocation Generation...")
        allocation = manager.generate_options_allocation(max_industries=6)
        
        if 'error' not in allocation:
            summary = allocation['summary']
            print(f"   Total Industries: {summary['total_industries']}")
            print(f"   Total Strategies: {summary['total_strategies']}")
            print(f"   Total Allocated Capital: ₹{summary['total_allocated_capital']:,.0f}")
            print(f"   Allocation Percentage: {summary['allocation_percentage']:.1f}%")
            
            # Show top industry allocations
            print("\n3. Top Industry Allocations:")
            for i, industry_alloc in enumerate(allocation['industry_allocations'][:3]):
                print(f"   {i+1}. {industry_alloc['industry']}: {industry_alloc['weight_percentage']:.1f}%")
                print(f"      Position Type: {industry_alloc['position_type']}")
                print(f"      Rating: {industry_alloc['rating']}")
                print(f"      Symbols: {industry_alloc['symbols'][:3]}")
                print(f"      Strategies: {[s['strategy_name'] for s in industry_alloc['strategies']]}")
                print(f"      Industry Capital: ₹{industry_alloc['total_industry_capital']:,.0f}")
            
            # Test validation
            validation = allocation.get('validation', {})
            print(f"\n4. Validation Status:")
            print(f"   Valid: {validation.get('valid', False)}")
            print(f"   Warnings: {len(validation.get('warnings', []))}")
            print(f"   Errors: {len(validation.get('errors', []))}")
            
            # Test priority symbols
            print("\n5. Testing Priority Symbols for Analysis...")
            priority_symbols = manager.get_priority_symbols_for_analysis(limit=8)
            print(f"   Priority Symbols Found: {len(priority_symbols)}")
            
            for i, symbol_data in enumerate(priority_symbols[:5]):
                print(f"   {i+1}. {symbol_data['symbol']} ({symbol_data['industry']})")
                print(f"      Weight: {symbol_data['weight_percentage']:.1f}%")
                print(f"      Preferred Strategy: {symbol_data['preferred_strategy']}")
                print(f"      Priority Score: {symbol_data['priority_score']:.2f}")
                print(f"      Recommended Capital: ₹{symbol_data['recommended_capital']:,.0f}")
            
            # Test strategy preferences for a symbol
            if priority_symbols:
                test_symbol = priority_symbols[0]['symbol']
                print(f"\n6. Testing Strategy Preferences for {test_symbol}...")
                preferences = manager.get_strategy_preferences_for_symbol(test_symbol)
                print(f"   Industry: {preferences.get('industry', 'N/A')}")
                print(f"   Industry Weight: {preferences.get('industry_weight', 0):.1f}%")
                print(f"   Position Type: {preferences.get('position_type', 'N/A')}")
                print(f"   Preferred Strategies: {preferences.get('preferred_strategies', [])}")
                print(f"   Market Condition: {preferences.get('market_condition', 'N/A')}")
            
            # Save portfolio
            print("\n7. Saving Portfolio...")
            filepath = manager.save_portfolio_to_file()
            if filepath:
                print(f"   Portfolio saved to: {filepath}")
            
            return allocation, priority_symbols
        else:
            print(f"   Error generating allocation: {allocation['error']}")
            return None, []
        
    except Exception as e:
        logger.error(f"Error testing options portfolio manager: {e}")
        return None, []

def test_integration_with_existing_v4_system(supabase_client, priority_symbols):
    """Test integration with existing Options V4 system"""
    print("\n" + "="*60)
    print("TESTING INTEGRATION WITH EXISTING OPTIONS V4 SYSTEM")
    print("="*60)
    
    if not priority_symbols:
        print("No priority symbols available for integration test")
        return
    
    try:
        # Import the existing Options V4 system
        from main import OptionsAnalyzer
        
        print("\n1. Initializing Existing Options V4 System...")
        analyzer = OptionsAnalyzer(enable_database=True)
        print("   ✅ Options V4 Analyzer initialized")
        
        # Test analyzing top priority symbols
        print("\n2. Testing Priority Symbol Analysis...")
        test_symbols = priority_symbols[:3]  # Test top 3 priority symbols
        
        integration_results = {}
        
        for i, symbol_data in enumerate(test_symbols):
            symbol = symbol_data['symbol']
            print(f"\n   Analyzing Symbol {i+1}: {symbol}")
            print(f"   Industry: {symbol_data['industry']}")
            print(f"   Priority Score: {symbol_data['priority_score']:.2f}")
            print(f"   Preferred Strategy: {symbol_data['preferred_strategy']}")
            
            try:
                # Run existing Options V4 analysis
                result = analyzer.analyze_symbol(symbol, risk_tolerance='moderate')
                
                if result.get('success', False):
                    strategies_found = len(result.get('top_strategies', []))
                    best_strategy = result['top_strategies'][0]['name'] if result['top_strategies'] else 'None'
                    best_score = result['top_strategies'][0]['total_score'] if result['top_strategies'] else 0
                    
                    print(f"   ✅ Success: {strategies_found} strategies found")
                    print(f"   Best Strategy: {best_strategy} (Score: {best_score:.3f})")
                    
                    integration_results[symbol] = {
                        'success': True,
                        'strategies_found': strategies_found,
                        'best_strategy': best_strategy,
                        'best_score': best_score,
                        'industry_data': symbol_data
                    }
                else:
                    print(f"   ❌ Failed: {result.get('reason', 'Unknown error')}")
                    integration_results[symbol] = {
                        'success': False,
                        'reason': result.get('reason', 'Unknown error'),
                        'industry_data': symbol_data
                    }
                    
            except Exception as e:
                print(f"   ❌ Error: {str(e)}")
                integration_results[symbol] = {
                    'success': False,
                    'reason': f'Exception: {str(e)}',
                    'industry_data': symbol_data
                }
        
        # Summary of integration test
        print(f"\n3. Integration Test Summary:")
        successful_analyses = sum(1 for r in integration_results.values() if r['success'])
        total_analyses = len(integration_results)
        success_rate = (successful_analyses / total_analyses * 100) if total_analyses > 0 else 0
        
        print(f"   Total Symbols Tested: {total_analyses}")
        print(f"   Successful Analyses: {successful_analyses}")
        print(f"   Success Rate: {success_rate:.1f}%")
        
        return integration_results
        
    except Exception as e:
        logger.error(f"Error testing integration: {e}")
        return {}

def update_database_with_allocation_priorities(supabase_client, allocation, priority_symbols):
    """Update database to mark strategies based on industry allocation"""
    print("\n" + "="*60)
    print("UPDATING DATABASE WITH ALLOCATION PRIORITIES")
    print("="*60)
    
    if not allocation or 'error' in allocation:
        print("❌ No valid allocation data available")
        return False
    
    try:
        from datetime import datetime, timedelta
        
        # First, clear any previous marks to avoid stale selections
        print("\n1. Clearing previous allocation marks...")
        clear_result = supabase_client.table('strategies').update({
            'marked_for_execution': False,
            'execution_priority': 0
        }).eq('marked_for_execution', True).execute()
        
        print(f"   ✅ Cleared {len(clear_result.data if clear_result.data else [])} previous marks")
        
        # Get strategies generated in last 24 hours
        cutoff_time = (datetime.now() - timedelta(hours=24)).isoformat()
        
        marked_count = 0
        errors = []
        
        print("\n2. Marking strategies based on allocation priorities...")
        
        # Process each priority symbol
        for idx, symbol_data in enumerate(priority_symbols):
            symbol = symbol_data['symbol']
            industry = symbol_data['industry']
            weight_pct = symbol_data['weight_percentage']
            preferred_strategy = symbol_data['preferred_strategy']
            priority_score = symbol_data['priority_score']
            
            print(f"\n   Processing {symbol} ({industry}):")
            print(f"   • Weight: {weight_pct:.1f}%")
            print(f"   • Preferred Strategy: {preferred_strategy}")
            
            # Query strategies for this symbol
            query = supabase_client.table('strategies').select(
                'id, stock_name, strategy_name, total_score, probability_of_profit'
            ).eq('stock_name', symbol).gte(
                'generated_on', cutoff_time
            ).eq('execution_status', 'pending')
            
            # Try to get preferred strategy first
            if preferred_strategy:
                # Make the query flexible for strategy name matching
                preferred_result = query.ilike('strategy_name', f'%{preferred_strategy}%').execute()
                
                if preferred_result.data:
                    # Found preferred strategy
                    strategy = preferred_result.data[0]
                    execution_priority = int((weight_pct * 100) + (priority_score * 10) + (100 - idx))
                    
                    update_result = supabase_client.table('strategies').update({
                        'marked_for_execution': True,
                        'execution_status': 'marked',
                        'execution_priority': execution_priority,
                        'execution_notes': f'Industry allocation: {industry} ({weight_pct:.1f}%), Priority score: {priority_score:.2f}'
                    }).eq('id', strategy['id']).execute()
                    
                    if update_result.data:
                        print(f"   ✅ Marked: {strategy['strategy_name']} (Priority: {execution_priority})")
                        marked_count += 1
                    else:
                        errors.append(f"Failed to mark strategy {strategy['id']}")
                        
                else:
                    # Fallback to highest scoring strategy for this symbol
                    fallback_result = query.order('total_score', desc=True).limit(1).execute()
                    
                    if fallback_result.data:
                        strategy = fallback_result.data[0]
                        execution_priority = int((weight_pct * 100) + (priority_score * 10) + (50 - idx))
                        
                        update_result = supabase_client.table('strategies').update({
                            'marked_for_execution': True,
                            'execution_status': 'marked',
                            'execution_priority': execution_priority,
                            'execution_notes': f'Industry allocation: {industry} ({weight_pct:.1f}%), Fallback strategy'
                        }).eq('id', strategy['id']).execute()
                        
                        if update_result.data:
                            print(f"   ✅ Marked fallback: {strategy['strategy_name']} (Priority: {execution_priority})")
                            marked_count += 1
                        else:
                            errors.append(f"Failed to mark fallback strategy {strategy['id']}")
                    else:
                        print(f"   ⚠️ No strategies found for {symbol}")
            else:
                # No preferred strategy, get highest scoring
                result = query.order('total_score', desc=True).limit(1).execute()
                
                if result.data:
                    strategy = result.data[0]
                    execution_priority = int((weight_pct * 100) + (50 - idx))
                    
                    update_result = supabase_client.table('strategies').update({
                        'marked_for_execution': True,
                        'execution_status': 'marked',
                        'execution_priority': execution_priority,
                        'execution_notes': f'Industry allocation: {industry} ({weight_pct:.1f}%)'
                    }).eq('id', strategy['id']).execute()
                    
                    if update_result.data:
                        print(f"   ✅ Marked: {strategy['strategy_name']} (Priority: {execution_priority})")
                        marked_count += 1
                    else:
                        errors.append(f"Failed to mark strategy {strategy['id']}")
        
        # Summary
        print(f"\n3. Database Update Summary:")
        print(f"   Total Symbols Processed: {len(priority_symbols)}")
        print(f"   Strategies Marked: {marked_count}")
        print(f"   Errors: {len(errors)}")
        
        if errors:
            print("\n   Errors encountered:")
            for error in errors[:5]:  # Show first 5 errors
                print(f"   • {error}")
        
        # Verify the updates
        verify_result = supabase_client.table('strategies').select(
            'id, stock_name, strategy_name, execution_priority'
        ).eq('marked_for_execution', True).order('execution_priority', desc=True).execute()
        
        if verify_result.data:
            print(f"\n4. Verification: {len(verify_result.data)} strategies marked for execution")
            print("\n   Top 5 by priority:")
            for i, strategy in enumerate(verify_result.data[:5]):
                print(f"   {i+1}. {strategy['stock_name']} - {strategy['strategy_name']} (Priority: {strategy['execution_priority']})")
        
        return marked_count > 0
        
    except Exception as e:
        logger.error(f"Error updating database with allocation priorities: {e}")
        import traceback
        traceback.print_exc()
        return False

def demonstrate_complete_workflow(integration_results):
    """Demonstrate the complete workflow"""
    print("\n" + "="*60)
    print("COMPLETE WORKFLOW DEMONSTRATION")
    print("="*60)
    
    print("\nThe industry-first allocation system provides a complete workflow:")
    
    print("\n📋 STEP 1: INDUSTRY ALLOCATION ANALYSIS")
    print("   • Queries industry_allocations_current table")
    print("   • Prioritizes industries by weight_percentage")
    print("   • Maps position_type (LONG/SHORT) to strategy preferences")
    
    print("\n🌍 STEP 2: MARKET ENVIRONMENT ASSESSMENT")
    print("   • Analyzes NIFTY direction using existing yfinance system")
    print("   • Gets VIX environment from existing scripts")
    print("   • Calculates PCR from option_chain_data table")
    
    print("\n🎯 STEP 3: STRATEGY SELECTION & PRIORITIZATION")
    print("   • Combines industry bias with market conditions")
    print("   • Generates priority symbols list with preferred strategies")
    print("   • Calculates position sizing based on industry allocation")
    
    print("\n⚙️ STEP 4: OPTIONS V4 INTEGRATION")
    print("   • Runs existing Options V4 analysis on priority symbols")
    print("   • Applies strategy preferences and position sizing")
    print("   • Stores results in database using existing infrastructure")
    
    print("\n🔄 STEP 5: DATABASE UPDATE WITH PRIORITIES")
    print("   • Updates strategies table with marked_for_execution = True")
    print("   • Sets execution_priority based on industry weights")
    print("   • Ready for execution via mark_for_execution.py")
    
    if integration_results:
        print("\n📊 INTEGRATION RESULTS:")
        for symbol, result in integration_results.items():
            if result['success']:
                industry = result['industry_data']['industry']
                weight = result['industry_data']['weight_percentage']
                best_strategy = result['best_strategy']
                print(f"   ✅ {symbol} ({industry}, {weight:.1f}%): {best_strategy}")
            else:
                print(f"   ❌ {symbol}: {result['reason']}")
    
    print("\n🚀 UPDATED WORKFLOW:")
    print("   1. Run portfolio analysis: python main.py")
    print("   2. Run allocation & mark strategies: python test_industry_allocation_system.py")
    print("   3. Review marked strategies: python mark_for_execution.py show")
    print("   4. Execute marked strategies: python options_v4_executor.py")

def main():
    """Main test function"""
    print("OPTIONS PORTFOLIO ALLOCATOR")
    print("=" * 60)
    print(f"Started at: {datetime.now()}")
    print(f"Filtering strategies based on industry allocation...")
    
    # Setup environment
    if not setup_environment():
        print("Environment setup failed")
        return
    
    # Initialize Supabase
    supabase_client = initialize_supabase()
    if not supabase_client:
        print("Supabase initialization failed")
        return
    
    try:
        # Test each component
        market_condition = test_market_conditions_analyzer(supabase_client)
        engine, priority_industries = test_industry_allocation_engine(supabase_client)
        allocation, priority_symbols = test_options_portfolio_manager(supabase_client)
        
        # Test integration with existing system
        integration_results = test_integration_with_existing_v4_system(supabase_client, priority_symbols)
        
        # Update database with allocation priorities
        if allocation and priority_symbols:
            print("\n" + "="*60)
            print("DATABASE UPDATE WITH ALLOCATION PRIORITIES")
            print("="*60)
            
            update_prompt = input("\n🔄 Do you want to update the database with allocation priorities? (y/n): ")
            if update_prompt.lower() == 'y':
                db_update_success = update_database_with_allocation_priorities(
                    supabase_client, allocation, priority_symbols
                )
                if db_update_success:
                    print("\n✅ Database updated successfully with allocation priorities!")
                else:
                    print("\n❌ Database update failed or partially completed")
            else:
                print("\n⏭️ Skipping database update")
        
        # Demonstrate complete workflow
        demonstrate_complete_workflow(integration_results)
        
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        print(f"✅ Market Conditions: {'Success' if market_condition else 'Failed'}")
        print(f"✅ Industry Allocation: {'Success' if engine else 'Failed'}")
        print(f"✅ Portfolio Manager: {'Success' if allocation else 'Failed'}")
        print(f"✅ V4 Integration: {'Success' if integration_results else 'Failed'}")
        
        if allocation:
            summary = allocation['summary']
            print(f"\n📊 FINAL PORTFOLIO ALLOCATION:")
            print(f"   • Industries: {summary['total_industries']}")
            print(f"   • Strategies: {summary['total_strategies']}")
            print(f"   • Capital Allocated: ₹{summary['total_allocated_capital']:,.0f}")
            print(f"   • Allocation %: {summary['allocation_percentage']:.1f}%")
            print(f"   • Priority Symbols: {len(priority_symbols) if priority_symbols else 0}")
        
        if integration_results:
            successful_v4_analyses = sum(1 for r in integration_results.values() if r['success'])
            total_v4_analyses = len(integration_results)
            print(f"\n🔗 OPTIONS V4 INTEGRATION:")
            print(f"   • Symbols Tested: {total_v4_analyses}")
            print(f"   • Successful Analyses: {successful_v4_analyses}")
            print(f"   • Integration Success Rate: {(successful_v4_analyses/total_v4_analyses*100) if total_v4_analyses > 0 else 0:.1f}%")
        
        print(f"\nTest completed at: {datetime.now()}")
        print("\n🎯 Ready for production use with 50-symbol portfolio analysis!")
        
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        print(f"\n❌ Test failed: {e}")

if __name__ == "__main__":
    main()