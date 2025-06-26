#!/usr/bin/env python3
"""
Demo Portfolio Selection Script
Shows how to select the best strategies for a ₹1 crore (10,000,000) portfolio
using the sophisticated options allocation system.
"""

import os
import sys
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SupabaseIntegration
from sophisticated_portfolio_allocator_runner import ProductionAllocatorRunner

def format_currency(amount):
    """Format currency values in Indian format"""
    if amount is None:
        return "N/A"
    return f"₹{amount:,.0f}"

def format_percentage(value):
    """Format percentage values"""
    if value is None:
        return "N/A"
    return f"{value:.1%}"

class PortfolioSelector:
    """
    Demonstrates best practices for selecting strategies for a ₹1 crore portfolio
    """
    
    def __init__(self, capital: float = 10000000):
        """Initialize with capital amount (default ₹1 crore)"""
        self.capital = capital
        self.db = SupabaseIntegration()
        
    def query_best_strategies(self, min_score: float = 0.5, 
                            min_probability: float = 0.4,
                            days_back: int = 2) -> List[Dict]:
        """
        Query the database for the best strategies based on multiple criteria
        
        Args:
            min_score: Minimum total score (0-1)
            min_probability: Minimum probability of profit (0-1)
            days_back: Number of days to look back for strategies
            
        Returns:
            List of top strategies
        """
        
        if not self.db.client:
            print("❌ No database connection")
            return []
        
        try:
            # Calculate date threshold
            from datetime import timezone
            date_threshold = (datetime.now(timezone.utc) - timedelta(days=days_back)).isoformat()
            
            # Query strategies with filters
            strategies = self.db.client.table('strategies').select(
                'id, stock_name, strategy_name, strategy_type, '
                'probability_of_profit, risk_reward_ratio, total_score, '
                'net_premium, conviction_level, market_outlook, '
                'iv_environment, spot_price, generated_on, '
                'strategy_parameters(*), strategy_greek_exposures(*), '
                'strategy_details(*)'
            ).gte('generated_on', date_threshold) \
             .gte('total_score', min_score) \
             .gte('probability_of_profit', min_probability) \
             .order('total_score', desc=True) \
             .limit(50) \
             .execute()
            
            return strategies.data if strategies.data else []
            
        except Exception as e:
            print(f"❌ Error querying strategies: {e}")
            return []
    
    def demonstrate_selection_criteria(self):
        """Show the different criteria for selecting strategies"""
        
        print("\n📋 STRATEGY SELECTION CRITERIA FOR ₹1 CRORE PORTFOLIO")
        print("=" * 70)
        
        print("\n1️⃣ PRIMARY FILTERS:")
        print("   • Total Score ≥ 0.5 (Composite quality metric)")
        print("   • Probability of Profit ≥ 40%")
        print("   • Risk-Reward Ratio ≥ 1.2")
        print("   • Conviction Level: MEDIUM, HIGH, or VERY_HIGH")
        
        print("\n2️⃣ RISK MANAGEMENT RULES:")
        print("   • Maximum per strategy: 5% (₹5,00,000)")
        print("   • Maximum per stock: 15% (₹15,00,000)")
        print("   • Maximum per industry: 12% (₹12,00,000)")
        print("   • Target number of strategies: 20-30")
        
        print("\n3️⃣ VIX-BASED STRATEGY SELECTION:")
        print("   • Low VIX (<15): Iron Condors, Butterflies, Premium Selling")
        print("   • Normal VIX (15-25): Balanced mix of all strategies")
        print("   • High VIX (>25): Long Options, Debit Spreads, Protective Strategies")
        
        print("\n4️⃣ SCORING COMPONENTS (WEIGHTS):")
        print("   • Probability of Profit: 35%")
        print("   • Risk-Reward Ratio: 25%")
        print("   • Market Direction Alignment: 20%")
        print("   • IV Compatibility: 15%")
        print("   • Liquidity Score: 5%")
    
    def show_top_opportunities(self):
        """Display current top opportunities from the database"""
        
        print("\n🔥 CURRENT TOP OPPORTUNITIES")
        print("-" * 60)
        
        strategies = self.query_best_strategies()
        
        if not strategies:
            print("No strategies found meeting criteria")
            return
        
        # Group by conviction level
        conviction_groups = {
            'VERY_HIGH': [],
            'HIGH': [],
            'MEDIUM': []
        }
        
        for strategy in strategies:
            conviction = strategy.get('conviction_level', 'MEDIUM')
            if conviction in conviction_groups:
                conviction_groups[conviction].append(strategy)
        
        # Show top strategies by conviction
        for conviction, group in conviction_groups.items():
            if group:
                print(f"\n{conviction} CONVICTION:")
                for i, strategy in enumerate(group[:5], 1):
                    score = strategy.get('total_score', 0) or 0
                    prob = strategy.get('probability_of_profit', 0) or 0
                    rr = strategy.get('risk_reward_ratio', 0) or 0
                    
                    print(f"{i}. {strategy['stock_name']} - {strategy['strategy_name']}")
                    print(f"   Score: {score:.3f} | PoP: {prob:.1%} | RR: {rr:.2f}")
                    
                    # Show risk metrics if available
                    if strategy.get('strategy_parameters'):
                        params = strategy['strategy_parameters'][0]
                        max_loss = abs(params.get('max_loss', 0))
                        max_profit = params.get('max_profit', 0)
                        print(f"   Max Loss: {format_currency(max_loss)} | Max Profit: {format_currency(max_profit)}")
    
    def demonstrate_portfolio_allocation(self):
        """Run the sophisticated allocator to show optimal allocation"""
        
        print("\n🚀 RUNNING SOPHISTICATED PORTFOLIO ALLOCATION")
        print("=" * 70)
        
        # Initialize the allocator
        runner = ProductionAllocatorRunner(enable_database=True)
        
        # Run allocation without updating database (demo mode)
        result = runner.run_allocation(
            update_database=False,
            save_report=True
        )
        
        if 'error' in result:
            print(f"❌ Allocation failed: {result['error']}")
            return
        
        # Display results
        runner.print_allocation_summary(result)
        
        # Show detailed allocation recommendations
        self._show_allocation_details(result)
    
    def _show_allocation_details(self, allocation_result: Dict):
        """Show detailed allocation recommendations"""
        
        print("\n💼 DETAILED ALLOCATION FOR ₹1 CRORE PORTFOLIO")
        print("-" * 70)
        
        top_strategies = allocation_result.get('top_strategies', [])
        
        if not top_strategies:
            print("No strategies allocated")
            return
        
        total_allocated = 0
        print("\n📊 RECOMMENDED POSITIONS:")
        print(f"{'#':<3} {'Stock':<12} {'Strategy':<20} {'Capital':<15} {'%':<6} {'Score':<6}")
        print("-" * 70)
        
        for i, strategy in enumerate(top_strategies[:20], 1):
            stock = strategy['stock_name']
            name = strategy['strategy_name']
            capital = strategy['capital_amount']
            pct = strategy['allocation_percent']
            score = strategy['quantum_score']
            
            total_allocated += capital
            
            print(f"{i:<3} {stock:<12} {name:<20} {format_currency(capital):<15} "
                  f"{pct:<6.1f} {score:<6.1f}")
        
        print("-" * 70)
        print(f"{'TOTAL:':<36} {format_currency(total_allocated):<15} "
              f"{(total_allocated/self.capital)*100:<6.1f}")
        
        # Risk distribution
        print("\n📈 RISK DISTRIBUTION:")
        risk_dist = allocation_result.get('allocation_by_risk_profile', {})
        for risk_level, data in risk_dist.items():
            print(f"   • {risk_level}: {data['allocation_percent']:.1f}% "
                  f"({data['strategy_count']} strategies)")
        
        # Expected performance
        metrics = allocation_result.get('portfolio_metrics', {})
        print("\n💰 EXPECTED PERFORMANCE:")
        print(f"   • Annual Return: {metrics.get('expected_annual_return', 0):.1f}%")
        print(f"   • Volatility: {metrics.get('portfolio_volatility', 0):.1f}%")
        print(f"   • Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}")
    
    def demonstrate_manual_selection(self):
        """Show how to manually select strategies based on specific criteria"""
        
        print("\n🔧 MANUAL STRATEGY SELECTION EXAMPLES")
        print("=" * 70)
        
        # Example 1: High conviction only
        print("\n1. HIGH CONVICTION STRATEGIES ONLY:")
        high_conviction = self.db.client.table('strategies').select(
            'stock_name, strategy_name, total_score, probability_of_profit, '
            'risk_reward_ratio, net_premium'
        ).in_('conviction_level', ['HIGH', 'VERY_HIGH']) \
         .gte('total_score', 0.6) \
         .order('total_score', desc=True) \
         .limit(5) \
         .execute()
        
        if high_conviction.data:
            for strategy in high_conviction.data:
                print(f"   • {strategy['stock_name']} {strategy['strategy_name']}: "
                      f"Score {strategy['total_score']:.3f}")
        
        # Example 2: Income strategies for low volatility
        print("\n2. INCOME STRATEGIES (PREMIUM COLLECTION):")
        income_strategies = self.db.client.table('strategies').select(
            'stock_name, strategy_name, net_premium, probability_of_profit'
        ).eq('strategy_type', 'Income') \
         .gte('probability_of_profit', 0.6) \
         .order('net_premium', desc=False) \
         .limit(5) \
         .execute()
        
        if income_strategies.data:
            for strategy in income_strategies.data:
                premium = abs(strategy.get('net_premium', 0))
                print(f"   • {strategy['stock_name']} {strategy['strategy_name']}: "
                      f"Premium ₹{premium:,.0f}")
        
        # Example 3: Defensive strategies
        print("\n3. DEFENSIVE STRATEGIES (PROTECTION):")
        defensive = self.db.client.table('strategies').select(
            'stock_name, strategy_name, strategy_type'
        ).in_('strategy_name', ['Protective Put', 'Collar', 'Bear Put Spread']) \
         .limit(5) \
         .execute()
        
        if defensive.data:
            for strategy in defensive.data:
                print(f"   • {strategy['stock_name']} {strategy['strategy_name']}")
    
    def show_position_sizing_rules(self):
        """Demonstrate position sizing calculations"""
        
        print("\n📏 POSITION SIZING GUIDELINES")
        print("=" * 70)
        
        print(f"\nFor ₹{self.capital:,.0f} portfolio:")
        
        # Kelly Criterion based sizing
        print("\n1. KELLY CRITERION BASED:")
        kelly_examples = [
            (0.65, 2.0, "High probability, good RR"),
            (0.55, 1.5, "Moderate probability, decent RR"),
            (0.45, 3.0, "Lower probability, excellent RR")
        ]
        
        for prob, rr, desc in kelly_examples:
            kelly_pct = (prob * rr - (1 - prob)) / rr * 100
            kelly_pct = min(kelly_pct, 25)  # Cap at 25%
            position_size = self.capital * (kelly_pct / 100)
            
            print(f"   • {desc}:")
            print(f"     PoP: {prob:.1%}, RR: {rr:.1f} → Kelly: {kelly_pct:.1f}%")
            print(f"     Position Size: {format_currency(position_size)}")
        
        # Risk-based sizing
        print("\n2. RISK-BASED SIZING (1-2% risk per trade):")
        risk_examples = [
            (50000, "Conservative"),
            (100000, "Moderate"),
            (150000, "Aggressive")
        ]
        
        for max_loss, risk_level in risk_examples:
            risk_pct = (max_loss / self.capital) * 100
            print(f"   • {risk_level}: Max loss {format_currency(max_loss)} = {risk_pct:.1f}% of capital")
        
        # Volatility-based sizing
        print("\n3. VOLATILITY-BASED ADJUSTMENTS:")
        print("   • Low VIX: Normal position sizes")
        print("   • Medium VIX: Reduce sizes by 20-30%")
        print("   • High VIX: Reduce sizes by 40-50%")


def main():
    """Main demonstration function"""
    
    print("🎯 OPTIONS PORTFOLIO SELECTION DEMO")
    print("For ₹1 Crore (₹10,000,000) Portfolio")
    print("=" * 80)
    
    # Initialize selector
    selector = PortfolioSelector(capital=10000000)
    
    # Run demonstrations
    selector.demonstrate_selection_criteria()
    selector.show_top_opportunities()
    selector.demonstrate_manual_selection()
    selector.show_position_sizing_rules()
    
    # Ask if user wants to run full allocation
    print("\n" + "=" * 80)
    response = input("\n🤔 Run full sophisticated portfolio allocation? (y/n): ")
    
    if response.lower() == 'y':
        selector.demonstrate_portfolio_allocation()
    
    print("\n✅ Demo completed!")
    print("=" * 80)
    
    # Summary
    print("\n📝 KEY TAKEAWAYS:")
    print("1. Use multiple criteria (score, probability, RR ratio) for selection")
    print("2. Apply proper position sizing (max 5% per strategy)")
    print("3. Ensure diversification across stocks and industries")
    print("4. Adjust for market conditions (VIX levels)")
    print("5. Monitor and rebalance regularly")
    print("\n💡 For production use, run: python sophisticated_portfolio_allocator_runner.py --update-database")


if __name__ == "__main__":
    main()