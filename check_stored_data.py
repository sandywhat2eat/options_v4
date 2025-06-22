#!/usr/bin/env python3
"""
Check what data was stored in the database
"""

import os
import sys
from dotenv import load_dotenv
import json

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv('/Users/jaykrish/Documents/digitalocean/.env')

from database import SupabaseIntegration

def main():
    print("📊 Checking Stored Database Data")
    print("=" * 50)
    
    db = SupabaseIntegration()
    if not db.client:
        print("❌ No database connection")
        return
    
    # Get recent strategies with details
    strategies = db.client.table('strategies').select('*').order('generated_on', desc=True).limit(3).execute()
    
    print(f"✅ Found {len(strategies.data)} recent strategies:\n")
    
    for i, strategy in enumerate(strategies.data, 1):
        print(f"🎯 Strategy {i}: {strategy.get('strategy_name', 'Unknown')}")
        print(f"   Symbol: {strategy.get('stock_name', 'Unknown')}")
        print(f"   Score: {strategy.get('total_score', 0):.3f}")
        print(f"   Conviction: {strategy.get('conviction_level', 'Unknown')}")
        print(f"   Probability: {strategy.get('probability_of_profit', 0):.1%}")
        print(f"   Market Outlook: {strategy.get('market_outlook', 'Unknown')}")
        print(f"   Spot Price: ${strategy.get('spot_price', 0):,.2f}")
        print(f"   Generated: {strategy.get('generated_on', 'Unknown')}")
        
        # Get strategy details (legs)
        strategy_id = strategy['id']
        legs = db.client.table('strategy_details').select('*').eq('strategy_id', strategy_id).execute()
        print(f"   Legs: {len(legs.data)}")
        for leg in legs.data:
            print(f"     • {leg.get('setup_type', 'Unknown')} {leg.get('option_type', 'Unknown')} "
                  f"Strike {leg.get('strike_price', 0)} @ ${leg.get('entry_price', 0)}")
        
        # Get parameters
        params = db.client.table('strategy_parameters').select('*').eq('strategy_id', strategy_id).execute()
        if params.data:
            param = params.data[0]
            print(f"   Max Profit: ${param.get('max_profit', 0):,.0f}")
            print(f"   Max Loss: ${abs(param.get('max_loss', 0)):,.0f}")
            print(f"   Risk/Reward: {param.get('risk_reward_ratio', 0):.2f}")
        
        # Get market analysis
        market = db.client.table('strategy_market_analysis').select('*').eq('strategy_id', strategy_id).execute()
        if market.data:
            ma = market.data[0]
            print(f"   Direction: {ma.get('market_direction', 'Unknown')} "
                  f"(Confidence: {ma.get('direction_confidence', 0):.1%})")
            print(f"   Technical Score: {ma.get('technical_score', 0):.3f}")
            print(f"   Options Score: {ma.get('options_score', 0):.3f}")
        
        print()
    
    # Check table counts
    print("📋 Table Record Counts:")
    tables = [
        'strategies', 'strategy_details', 'strategy_parameters',
        'strategy_greek_exposures', 'strategy_monitoring', 'strategy_risk_management',
        'strategy_market_analysis', 'strategy_iv_analysis', 'strategy_price_levels',
        'strategy_expected_moves', 'strategy_exit_levels', 'strategy_component_scores'
    ]
    
    for table in tables:
        try:
            count_result = db.client.table(table).select('id', count='exact').execute()
            count = count_result.count if hasattr(count_result, 'count') else len(count_result.data)
            print(f"   {table}: {count} records")
        except Exception as e:
            print(f"   {table}: Error - {e}")

if __name__ == "__main__":
    main()