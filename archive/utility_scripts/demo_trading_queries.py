#!/usr/bin/env python3
"""
Demo trading queries for options derivatives expert
Shows real data from the database in trader-friendly format
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

def format_currency(amount):
    """Format currency values"""
    if amount is None:
        return "N/A"
    return f"₹{amount:,.0f}"

def format_percentage(value):
    """Format percentage values"""
    if value is None:
        return "N/A"
    return f"{value:.1%}"

def demo_trading_queries():
    """Demonstrate key trading queries with real data"""
    
    db = SupabaseIntegration()
    if not db.client:
        print("❌ No database connection")
        return
    
    print("📈 OPTIONS DERIVATIVES EXPERT - TRADING DASHBOARD")
    print("=" * 70)
    
    # 1. High-Priority Trading Opportunities
    print("\n🔥 HIGH-PRIORITY TRADING OPPORTUNITIES")
    print("-" * 50)
    
    try:
        # Get high-score strategies
        high_priority = db.client.table('strategies').select(
            'stock_name, strategy_name, total_score, conviction_level, probability_of_profit, generated_on'
        ).gte('total_score', 0.5).order('total_score', desc=True).limit(5).execute()
        
        if high_priority.data:
            for i, strategy in enumerate(high_priority.data, 1):
                score = strategy.get('total_score', 0) or 0
                prob = strategy.get('probability_of_profit', 0) or 0
                print(f"{i}. {strategy['stock_name']} - {strategy['strategy_name']}")
                print(f"   Score: {score:.3f} | Conviction: {strategy['conviction_level']} | Prob: {prob:.1%}")
                print(f"   Time: {strategy['generated_on'][:16]}")
                print()
    except Exception as e:
        print(f"Error: {e}")
    
    # 2. Complete Trade Execution Details
    print("\n⚡ COMPLETE TRADE EXECUTION - DIXON BEAR PUT SPREAD")
    print("-" * 60)
    
    try:
        # Get strategy details for execution
        strategy_details = db.client.table('strategies').select(
            '*, strategy_details(*), strategy_parameters(*), strategy_greek_exposures(*)'
        ).eq('stock_name', 'DIXON').eq('strategy_name', 'Bear Put Spread').limit(1).execute()
        
        if strategy_details.data:
            strategy = strategy_details.data[0]
            print(f"Symbol: {strategy['stock_name']}")
            print(f"Strategy: {strategy['strategy_name']}")
            print(f"Spot Price: ₹{strategy['spot_price']:,.0f}")
            print(f"Score: {strategy.get('total_score', 0):.3f}")
            print(f"Conviction: {strategy['conviction_level']}")
            print()
            
            # Leg details
            print("OPTION LEGS:")
            for leg in strategy.get('strategy_details', []):
                action = leg['setup_type']
                option_type = leg['option_type']
                strike = leg['strike_price']
                premium = leg['entry_price']
                delta = leg.get('delta', 0)
                print(f"  {action} {option_type} {strike} @ ₹{premium} (Δ={delta:.3f})")
            
            # Risk metrics
            if strategy.get('strategy_parameters'):
                params = strategy['strategy_parameters'][0]
                print(f"\nRISK/REWARD:")
                print(f"  Max Profit: {format_currency(params.get('max_profit'))}")
                print(f"  Max Loss: {format_currency(params.get('max_loss'))}")
                print(f"  Risk/Reward: {params.get('risk_reward_ratio', 0):.2f}")
            
            # Greeks
            if strategy.get('strategy_greek_exposures'):
                greeks = strategy['strategy_greek_exposures'][0]
                print(f"\nNET GREEKS:")
                print(f"  Delta: {greeks.get('net_delta', 0):.3f}")
                print(f"  Theta: {greeks.get('net_theta', 0):.2f}")
                print(f"  Vega: {greeks.get('net_vega', 0):.2f}")
    
    except Exception as e:
        print(f"Error: {e}")
    
    # 3. Risk Management View
    print("\n🛡️ RISK MANAGEMENT ANALYSIS")
    print("-" * 40)
    
    try:
        # Get risk analysis for recent strategies
        risk_analysis = db.client.table('strategies').select(
            'stock_name, strategy_name, total_score, conviction_level, strategy_parameters(*), strategy_greek_exposures(*)'
        ).gte('total_score', 0.4).order('generated_on', desc=True).limit(3).execute()
        
        if risk_analysis.data:
            for strategy in risk_analysis.data:
                symbol = strategy['stock_name']
                name = strategy['strategy_name']
                score = strategy.get('total_score', 0) or 0
                conviction = strategy['conviction_level']
                
                print(f"{symbol} - {name}")
                print(f"  Score: {score:.3f} | Conviction: {conviction}")
                
                # Risk assessment
                if strategy.get('strategy_parameters'):
                    params = strategy['strategy_parameters'][0]
                    max_loss = abs(params.get('max_loss', 0))
                    rr_ratio = params.get('risk_reward_ratio', 0)
                    
                    # Position size recommendation
                    if conviction in ['HIGH', 'VERY_HIGH'] and rr_ratio >= 2.0:
                        pos_size = "MEDIUM (2-3%)"
                    elif conviction == 'MEDIUM' and rr_ratio >= 1.0:
                        pos_size = "SMALL (1-2%)"
                    else:
                        pos_size = "MINIMAL (<1%)"
                    
                    print(f"  Risk: {format_currency(max_loss)} | RR: {rr_ratio:.2f}")
                    print(f"  Position Size: {pos_size}")
                
                # Greeks risk
                if strategy.get('strategy_greek_exposures'):
                    greeks = strategy['strategy_greek_exposures'][0]
                    delta = abs(greeks.get('net_delta', 0))
                    gamma = abs(greeks.get('net_gamma', 0))
                    
                    if delta > 0.5 and gamma > 0.01:
                        risk_level = "HIGH"
                    elif delta > 0.3:
                        risk_level = "MEDIUM"
                    else:
                        risk_level = "LOW"
                    
                    print(f"  Greeks Risk: {risk_level}")
                print()
        
    except Exception as e:
        print(f"Error: {e}")
    
    # 4. Market Analysis Summary
    print("\n📊 MARKET ANALYSIS SUMMARY")
    print("-" * 35)
    
    try:
        # Get market analysis for recent strategies
        market_analysis = db.client.table('strategies').select(
            'stock_name, strategy_name, spot_price, strategy_market_analysis(*), strategy_iv_analysis(*)'
        ).order('generated_on', desc=True).limit(3).execute()
        
        if market_analysis.data:
            for strategy in market_analysis.data:
                symbol = strategy['stock_name']
                spot = strategy['spot_price']
                
                print(f"{symbol} @ ₹{spot:,.0f}")
                
                # Market direction
                if strategy.get('strategy_market_analysis'):
                    ma = strategy['strategy_market_analysis'][0]
                    direction = ma.get('market_direction', 'N/A')
                    confidence = ma.get('direction_confidence', 0)
                    flow = ma.get('flow_intensity', 'N/A')
                    
                    print(f"  Direction: {direction} ({confidence:.1%} confidence)")
                    print(f"  Options Flow: {flow}")
                
                # IV analysis
                if strategy.get('strategy_iv_analysis'):
                    iv = strategy['strategy_iv_analysis'][0]
                    iv_env = iv.get('iv_environment', 'N/A')
                    atm_iv = iv.get('atm_iv', 0)
                    
                    print(f"  IV Environment: {iv_env} (ATM: {atm_iv:.1f}%)")
                print()
        
    except Exception as e:
        print(f"Error: {e}")
    
    # 5. Trading Alerts
    print("\n🚨 TRADING ALERTS")
    print("-" * 20)
    
    try:
        # High score alerts
        high_score_alerts = db.client.table('strategies').select(
            'stock_name, strategy_name, total_score, conviction_level, generated_on'
        ).gte('total_score', 0.6).order('generated_on', desc=True).limit(3).execute()
        
        if high_score_alerts.data:
            for alert in high_score_alerts.data:
                score = alert.get('total_score', 0) or 0
                print(f"🔥 HIGH SCORE: {alert['stock_name']} {alert['strategy_name']}")
                print(f"   Score: {score:.3f} | Conviction: {alert['conviction_level']}")
                print(f"   Time: {alert['generated_on'][:16]}")
                print()
        
        # High conviction alerts
        high_conviction = db.client.table('strategies').select(
            'stock_name, strategy_name, conviction_level, probability_of_profit, generated_on'
        ).in_('conviction_level', ['HIGH', 'VERY_HIGH']).order('generated_on', desc=True).limit(2).execute()
        
        if high_conviction.data:
            for alert in high_conviction.data:
                prob = alert.get('probability_of_profit', 0) or 0
                print(f"⚡ HIGH CONVICTION: {alert['stock_name']} {alert['strategy_name']}")
                print(f"   Conviction: {alert['conviction_level']} | Prob: {prob:.1%}")
                print(f"   Time: {alert['generated_on'][:16]}")
                print()
        
    except Exception as e:
        print(f"Error: {e}")
    
    print("=" * 70)
    print("📋 NEXT STEPS:")
    print("1. Create views using trading_views.sql in Supabase SQL Editor")
    print("2. Use v_trade_execution for complete trade details")
    print("3. Monitor v_trading_alerts for real-time opportunities")
    print("4. Reference TRADERS_GUIDE.md for detailed usage")
    print("=" * 70)

if __name__ == "__main__":
    demo_trading_queries()