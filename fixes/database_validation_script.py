#!/usr/bin/env python3
"""
Database Population Validation Script
Analyzes all strategy-related tables to identify gaps and issues
"""

import os
import sys
from dotenv import load_dotenv
from supabase import create_client
import json
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

def get_supabase_client():
    """Initialize Supabase client"""
    load_dotenv()
    return create_client(
        os.getenv('NEXT_PUBLIC_SUPABASE_URL'),
        os.getenv('NEXT_PUBLIC_SUPABASE_ANON_KEY')
    )

def analyze_table_population(client, table_name, expected_fields=None):
    """Analyze population rate for a specific table"""
    try:
        # Get sample of records
        response = client.table(table_name).select('*').limit(100).execute()
        
        if not response.data:
            return {
                'table': table_name,
                'status': 'EMPTY',
                'total_records': 0,
                'issues': ['No data found in table']
            }
        
        total_records = len(response.data)
        all_fields = list(response.data[0].keys())
        issues = []
        field_stats = {}
        
        # Analyze each field
        for field in all_fields:
            null_count = sum(1 for record in response.data if record.get(field) is None)
            zero_count = sum(1 for record in response.data if record.get(field) == 0)
            empty_string_count = sum(1 for record in response.data if record.get(field) == '')
            
            populated_rate = ((total_records - null_count) / total_records) * 100
            
            field_stats[field] = {
                'populated_rate': populated_rate,
                'null_count': null_count,
                'zero_count': zero_count,
                'empty_string_count': empty_string_count
            }
            
            # Flag issues
            if populated_rate < 50:
                issues.append(f"{field}: Only {populated_rate:.1f}% populated")
            elif zero_count > total_records * 0.8:
                issues.append(f"{field}: {zero_count}/{total_records} records are zero")
        
        # Calculate overall status
        avg_population = sum(stats['populated_rate'] for stats in field_stats.values()) / len(field_stats)
        
        if avg_population > 90:
            status = 'EXCELLENT'
        elif avg_population > 70:
            status = 'GOOD'
        elif avg_population > 50:
            status = 'PARTIAL'
        else:
            status = 'FAILING'
        
        return {
            'table': table_name,
            'status': status,
            'total_records': total_records,
            'avg_population_rate': avg_population,
            'field_stats': field_stats,
            'issues': issues
        }
        
    except Exception as e:
        return {
            'table': table_name,
            'status': 'ERROR',
            'total_records': 0,
            'issues': [str(e)]
        }

def validate_data_relationships(client):
    """Validate foreign key relationships and data consistency"""
    issues = []
    
    try:
        # Check strategies without details
        strategies_response = client.table('strategies').select('id').execute()
        strategy_ids = [s['id'] for s in strategies_response.data]
        
        details_response = client.table('strategy_details').select('strategy_id').execute()
        detail_strategy_ids = set([d['strategy_id'] for d in details_response.data])
        
        orphaned_strategies = [sid for sid in strategy_ids if sid not in detail_strategy_ids]
        if orphaned_strategies:
            issues.append(f"Strategies without details: {len(orphaned_strategies)} records")
        
        # Check for missing critical tables
        tables_to_check = [
            'strategy_parameters', 'strategy_greek_exposures', 
            'strategy_risk_management', 'strategy_exit_levels'
        ]
        
        for table in tables_to_check:
            try:
                response = client.table(table).select('strategy_id').execute()
                table_strategy_ids = set([r['strategy_id'] for r in response.data])
                missing = len(strategy_ids) - len(table_strategy_ids)
                if missing > 0:
                    issues.append(f"{table}: Missing {missing}/{len(strategy_ids)} records")
            except Exception as e:
                issues.append(f"{table}: Error accessing table - {e}")
        
        return issues
        
    except Exception as e:
        return [f"Relationship validation error: {e}"]

def check_specific_data_quality(client):
    """Check for specific data quality issues identified in analysis"""
    issues = []
    
    try:
        # Check for null expiry dates in strategy_details
        response = client.table('strategy_details').select('id, expiry_date').is_('expiry_date', 'null').limit(10).execute()
        if response.data:
            issues.append(f"strategy_details: {len(response.data)} records with NULL expiry_date")
        
        # Check for zero Greeks in strategy_greek_exposures  
        response = client.table('strategy_greek_exposures').select('id, net_gamma, net_theta, net_vega').eq('net_gamma', 0).eq('net_theta', 0).eq('net_vega', 0).limit(10).execute()
        if response.data:
            issues.append(f"strategy_greek_exposures: {len(response.data)} records with all Greeks = 0")
        
        # Check for null max_profit in strategy_parameters
        response = client.table('strategy_parameters').select('id, max_profit').is_('max_profit', 'null').limit(10).execute()
        if response.data:
            issues.append(f"strategy_parameters: {len(response.data)} records with NULL max_profit")
        
        # Check for empty descriptions in strategies
        response = client.table('strategies').select('id, description').eq('description', '').limit(10).execute()
        if response.data:
            issues.append(f"strategies: {len(response.data)} records with empty description")
            
        return issues
        
    except Exception as e:
        return [f"Data quality check error: {e}"]

def main():
    """Run complete database validation"""
    print("🔍 Database Population Validation - Options V4 System")
    print("=" * 60)
    
    client = get_supabase_client()
    
    # Tables to analyze in order
    tables = [
        'strategies',
        'strategy_details', 
        'strategy_parameters',
        'strategy_greek_exposures',
        'strategy_monitoring',
        'strategy_risk_management',
        'strategy_market_analysis',
        'strategy_iv_analysis',
        'strategy_price_levels',
        'strategy_expected_moves',
        'strategy_exit_levels',
        'strategy_component_scores'
    ]
    
    results = []
    
    # Analyze each table
    print("\n📊 TABLE POPULATION ANALYSIS")
    print("-" * 40)
    
    for table in tables:
        print(f"Analyzing {table}...")
        result = analyze_table_population(client, table)
        results.append(result)
        
        status_emoji = {
            'EXCELLENT': '✅',
            'GOOD': '🟢', 
            'PARTIAL': '🔶',
            'FAILING': '🔥',
            'ERROR': '❌',
            'EMPTY': '⚪'
        }
        
        print(f"{status_emoji.get(result['status'], '❓')} {table}: {result['status']} "
              f"({result['total_records']} records)")
        
        if result.get('avg_population_rate'):
            print(f"   Population Rate: {result['avg_population_rate']:.1f}%")
        
        if result['issues']:
            for issue in result['issues'][:3]:  # Show first 3 issues
                print(f"   ⚠️  {issue}")
    
    # Validate relationships
    print("\n🔗 RELATIONSHIP VALIDATION")
    print("-" * 40)
    relationship_issues = validate_data_relationships(client)
    for issue in relationship_issues:
        print(f"❌ {issue}")
    
    # Check specific data quality issues
    print("\n🔍 DATA QUALITY CHECKS")
    print("-" * 40)
    quality_issues = check_specific_data_quality(client)
    for issue in quality_issues:
        print(f"⚠️  {issue}")
    
    # Summary
    print("\n📋 SUMMARY")
    print("-" * 40)
    
    status_counts = {}
    for result in results:
        status = result['status']
        status_counts[status] = status_counts.get(status, 0) + 1
    
    total_tables = len(results)
    working_tables = status_counts.get('EXCELLENT', 0) + status_counts.get('GOOD', 0)
    failing_tables = status_counts.get('FAILING', 0) + status_counts.get('ERROR', 0)
    
    print(f"Total Tables: {total_tables}")
    print(f"Working Well: {working_tables} ({working_tables/total_tables*100:.1f}%)")
    print(f"Failing: {failing_tables} ({failing_tables/total_tables*100:.1f}%)")
    print(f"Partial Issues: {status_counts.get('PARTIAL', 0)}")
    
    # Priority recommendations
    print("\n🎯 PRIORITY ACTIONS")
    print("-" * 40)
    
    critical_tables = [r for r in results if r['status'] in ['FAILING', 'ERROR']]
    if critical_tables:
        print("🔥 CRITICAL - Fix these tables first:")
        for table in critical_tables:
            print(f"   - {table['table']}")
    
    partial_tables = [r for r in results if r['status'] == 'PARTIAL']
    if partial_tables:
        print("🔶 MEDIUM - Improve these tables:")
        for table in partial_tables:
            print(f"   - {table['table']}")
    
    # Save detailed results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"database_validation_results_{timestamp}.json"
    
    validation_results = {
        'timestamp': datetime.now().isoformat(),
        'table_analysis': results,
        'relationship_issues': relationship_issues,
        'data_quality_issues': quality_issues,
        'summary': {
            'total_tables': total_tables,
            'working_tables': working_tables,
            'failing_tables': failing_tables,
            'status_distribution': status_counts
        }
    }
    
    with open(output_file, 'w') as f:
        json.dump(validation_results, f, indent=2)
    
    print(f"\n💾 Detailed results saved to: {output_file}")
    print("\n🔍 For detailed fix recommendations, see:")
    print("   fixes/DATABASE_POPULATION_GAPS_ANALYSIS.md")

if __name__ == "__main__":
    main()