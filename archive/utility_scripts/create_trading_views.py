#!/usr/bin/env python3
"""
Create trading views in Supabase database
"""

import os
import sys
from dotenv import load_dotenv

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv('/Users/jaykrish/Documents/digitalocean/.env')

from database import SupabaseIntegration

def create_trading_views():
    """Create essential trading views in Supabase"""
    
    db = SupabaseIntegration()
    if not db.client:
        print("❌ No database connection")
        return
    
    print("🚀 Creating Trading Views for Options Derivatives Expert")
    print("=" * 60)
    
    # Create Trade Execution View
    trade_execution_view = """
    CREATE OR REPLACE VIEW v_trade_execution AS
    SELECT 
        -- Strategy Identification
        s.id as strategy_id,
        s.stock_name as symbol,
        s.strategy_name,
        s.strategy_type,
        s.conviction_level,
        s.total_score,
        s.probability_of_profit,
        s.spot_price,
        s.generated_on as analysis_time,
        
        -- Market Context
        sma.market_direction,
        sma.direction_confidence,
        sma.timeframe_duration as time_horizon,
        sma.iv_skew,
        sma.flow_intensity,
        sia.iv_environment,
        sia.atm_iv,
        
        -- Risk/Reward Metrics
        sp.max_profit,
        sp.max_loss,
        sp.risk_reward_ratio,
        sp.probability_profit,
        
        -- Entry Details
        sd.setup_type as leg_action,
        sd.option_type,
        sd.strike_price,
        sd.entry_price as premium,
        sd.quantity,
        sd.delta,
        sd.gamma,
        sd.theta,
        sd.vega,
        sd.implied_volatility as iv,
        
        -- Exit Conditions
        srm.profit_target_primary,
        srm.profit_target_pct,
        srm.strategy_level_stop as stop_loss_pct,
        srm.time_stop_dte,
        
        -- Net Position Greeks
        sge.net_delta,
        sge.net_gamma,
        sge.net_theta,
        sge.net_vega,
        
        -- Expected Moves
        sem.one_sd_move,
        sem.upper_expected_1sd,
        sem.lower_expected_1sd,
        
        -- Trade Urgency
        CASE 
            WHEN s.total_score > 0.7 AND s.conviction_level IN ('HIGH', 'VERY_HIGH') THEN 'IMMEDIATE'
            WHEN s.total_score > 0.6 AND s.conviction_level = 'HIGH' THEN 'HIGH'
            WHEN s.total_score > 0.5 THEN 'MEDIUM'
            ELSE 'LOW'
        END as trade_priority

    FROM strategies s
    LEFT JOIN strategy_details sd ON s.id = sd.strategy_id
    LEFT JOIN strategy_parameters sp ON s.id = sp.strategy_id
    LEFT JOIN strategy_market_analysis sma ON s.id = sma.strategy_id
    LEFT JOIN strategy_iv_analysis sia ON s.id = sia.strategy_id
    LEFT JOIN strategy_risk_management srm ON s.id = srm.strategy_id
    LEFT JOIN strategy_greek_exposures sge ON s.id = sge.strategy_id
    LEFT JOIN strategy_expected_moves sem ON s.id = sem.strategy_id
    ORDER BY s.generated_on DESC, s.total_score DESC, sd.id;
    """
    
    try:
        # Note: Direct view creation via Supabase client may not work
        # This would typically be done via SQL editor in Supabase dashboard
        print("📋 Trade Execution View SQL created")
        print("✅ View definition ready for Supabase SQL editor")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Create sample query to demonstrate the views
    print("\n📊 Sample Query Results:")
    
    # Query recent strategies in a trader-friendly format
    try:
        # Get recent strategies with key trading information
        query = """
        SELECT 
            s.stock_name as symbol,
            s.strategy_name,
            s.total_score,
            s.conviction_level,
            s.probability_of_profit,
            s.spot_price,
            sp.max_profit,
            sp.max_loss,
            sp.risk_reward_ratio,
            sge.net_delta,
            sge.net_theta,
            sma.market_direction,
            sma.direction_confidence,
            sia.iv_environment,
            CASE 
                WHEN s.total_score > 0.7 AND s.conviction_level IN ('HIGH', 'VERY_HIGH') THEN 'IMMEDIATE'
                WHEN s.total_score > 0.6 AND s.conviction_level = 'HIGH' THEN 'HIGH'
                WHEN s.total_score > 0.5 THEN 'MEDIUM'
                ELSE 'LOW'
            END as trade_priority
        FROM strategies s
        LEFT JOIN strategy_parameters sp ON s.id = sp.strategy_id
        LEFT JOIN strategy_greek_exposures sge ON s.id = sge.strategy_id
        LEFT JOIN strategy_market_analysis sma ON s.id = sma.strategy_id
        LEFT JOIN strategy_iv_analysis sia ON s.id = sia.strategy_id
        WHERE s.generated_on >= NOW() - INTERVAL '24 hours'
        ORDER BY s.total_score DESC
        LIMIT 5
        """
        
        result = db.client.rpc('execute_sql', {'sql': query}).execute()
        print("Query executed successfully")
        
    except Exception as e:
        print(f"Note: Direct SQL execution not available via client: {e}")
        print("Views should be created manually in Supabase SQL editor")

def main():
    create_trading_views()
    
    print("\n" + "=" * 60)
    print("🎯 NEXT STEPS FOR DERIVATIVES EXPERT:")
    print("=" * 60)
    print("1. Open Supabase SQL Editor")
    print("2. Run the SQL file: trading_views.sql")
    print("3. Use these views for trading decisions:")
    print("   • v_trade_execution - Complete trade details")
    print("   • v_portfolio_dashboard - High-level opportunities")
    print("   • v_risk_management - Position sizing & risk")
    print("   • v_market_opportunities - Market-driven trades")
    print("   • v_strategy_comparison - Compare strategies")
    print("   • v_execution_checklist - Pre-trade validation")
    print("   • v_trading_alerts - Urgent opportunities")
    print("\n📖 See trading_views.sql for complete documentation")

if __name__ == "__main__":
    main()