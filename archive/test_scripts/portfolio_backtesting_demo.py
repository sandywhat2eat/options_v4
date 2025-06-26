#!/usr/bin/env python3
"""
Portfolio Backtesting and Performance Analysis Demo
Shows how to analyze historical performance of selected strategies
"""

import os
import sys
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SupabaseIntegration

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

class PortfolioBacktester:
    """
    Demonstrates backtesting and performance analysis for options strategies
    """
    
    def __init__(self, capital: float = 10000000):
        """Initialize with capital amount"""
        self.capital = capital
        self.db = SupabaseIntegration()
        
    def analyze_historical_performance(self, days_back: int = 30) -> Dict:
        """
        Analyze historical performance of strategies
        
        Args:
            days_back: Number of days to analyze
            
        Returns:
            Performance metrics dictionary
        """
        
        if not self.db.client:
            print("❌ No database connection")
            return {}
        
        try:
            # Get historical strategies
            from datetime import timezone
            date_threshold = (datetime.now(timezone.utc) - timedelta(days=days_back)).isoformat()
            
            strategies = self.db.client.table('strategies').select(
                'id, stock_name, strategy_name, strategy_type, '
                'probability_of_profit, risk_reward_ratio, total_score, '
                'net_premium, conviction_level, generated_on, '
                'strategy_parameters(*)'
            ).gte('generated_on', date_threshold) \
             .gte('total_score', 0.5) \
             .execute()
            
            if not strategies.data:
                return {}
            
            # Analyze performance metrics
            df = pd.DataFrame(strategies.data)
            
            performance_metrics = {
                'total_strategies': len(df),
                'avg_probability': df['probability_of_profit'].mean(),
                'avg_risk_reward': df['risk_reward_ratio'].mean(),
                'avg_score': df['total_score'].mean(),
                'by_conviction': df.groupby('conviction_level').size().to_dict(),
                'by_strategy_type': df.groupby('strategy_type').size().to_dict()
            }
            
            # Calculate theoretical returns
            theoretical_returns = []
            for _, strategy in df.iterrows():
                if strategy.get('strategy_parameters'):
                    params = strategy['strategy_parameters'][0]
                    max_profit = params.get('max_profit', 0)
                    max_loss = abs(params.get('max_loss', 0))
                    prob = strategy['probability_of_profit']
                    
                    # Simple expected value calculation
                    expected_return = (prob * max_profit) - ((1 - prob) * max_loss)
                    theoretical_returns.append({
                        'strategy': f"{strategy['stock_name']} {strategy['strategy_name']}",
                        'expected_return': expected_return,
                        'return_pct': (expected_return / max_loss * 100) if max_loss > 0 else 0
                    })
            
            performance_metrics['theoretical_returns'] = theoretical_returns
            
            return performance_metrics
            
        except Exception as e:
            print(f"❌ Error analyzing performance: {e}")
            return {}
    
    def demonstrate_backtesting_framework(self):
        """Show how to build a backtesting framework"""
        
        print("\n📊 OPTIONS BACKTESTING FRAMEWORK")
        print("=" * 70)
        
        print("\n1️⃣ KEY METRICS TO TRACK:")
        print("   • Win Rate: Actual vs Expected probability of profit")
        print("   • Average P&L: Per strategy and overall")
        print("   • Maximum Drawdown: Largest peak-to-trough decline")
        print("   • Sharpe Ratio: Risk-adjusted returns")
        print("   • Hit Rate: Strategies reaching profit target")
        
        print("\n2️⃣ BACKTESTING ASSUMPTIONS:")
        print("   • Entry at mid-price between bid-ask")
        print("   • Include commission costs (₹20-40 per lot)")
        print("   • Account for slippage (0.1-0.2% of premium)")
        print("   • Early exit at 50% profit target")
        print("   • Stop loss at 2x credit received")
        
        print("\n3️⃣ PERFORMANCE ATTRIBUTION:")
        print("   • By Strategy Type (Income, Volatility, Directional)")
        print("   • By Market Condition (Trending, Range-bound)")
        print("   • By VIX Level (Low, Normal, High)")
        print("   • By Time Decay (Days to expiration)")
    
    def simulate_portfolio_performance(self, num_trades: int = 100):
        """
        Simulate portfolio performance based on historical probabilities
        """
        
        print("\n🎲 MONTE CARLO SIMULATION")
        print("=" * 70)
        print(f"Simulating {num_trades} trades with ₹{self.capital:,.0f} capital")
        
        # Get recent strategies for simulation parameters
        performance = self.analyze_historical_performance(days_back=30)
        
        if not performance:
            print("No historical data available")
            return
        
        avg_prob = performance.get('avg_probability', 0.5)
        avg_rr = performance.get('avg_risk_reward', 1.5)
        
        print(f"\nSimulation Parameters:")
        print(f"  • Average Win Rate: {avg_prob:.1%}")
        print(f"  • Average Risk-Reward: {avg_rr:.2f}")
        print(f"  • Position Size: 2% risk per trade")
        
        # Run simulation
        np.random.seed(42)  # For reproducibility
        position_size = self.capital * 0.02  # 2% risk per trade
        
        results = []
        cumulative_pnl = 0
        peak_capital = self.capital
        max_drawdown = 0
        
        for i in range(num_trades):
            # Simulate win/loss
            win = np.random.random() < avg_prob
            
            if win:
                pnl = position_size * (avg_rr - 1)  # Profit
            else:
                pnl = -position_size  # Loss
            
            cumulative_pnl += pnl
            current_capital = self.capital + cumulative_pnl
            
            # Track drawdown
            if current_capital > peak_capital:
                peak_capital = current_capital
            drawdown = (peak_capital - current_capital) / peak_capital
            max_drawdown = max(max_drawdown, drawdown)
            
            results.append({
                'trade': i + 1,
                'win': win,
                'pnl': pnl,
                'cumulative_pnl': cumulative_pnl,
                'capital': current_capital
            })
        
        # Calculate statistics
        df_results = pd.DataFrame(results)
        wins = df_results['win'].sum()
        win_rate = wins / num_trades
        total_return = cumulative_pnl / self.capital
        
        print(f"\n📈 SIMULATION RESULTS:")
        print(f"  • Total P&L: {format_currency(cumulative_pnl)}")
        print(f"  • Total Return: {total_return:.1%}")
        print(f"  • Win Rate: {win_rate:.1%} ({wins}/{num_trades} trades)")
        print(f"  • Max Drawdown: {max_drawdown:.1%}")
        print(f"  • Final Capital: {format_currency(self.capital + cumulative_pnl)}")
        
        # Show distribution
        print(f"\n📊 P&L DISTRIBUTION:")
        print(f"  • Best Trade: {format_currency(df_results['pnl'].max())}")
        print(f"  • Worst Trade: {format_currency(df_results['pnl'].min())}")
        print(f"  • Average Trade: {format_currency(df_results['pnl'].mean())}")
        print(f"  • Std Dev: {format_currency(df_results['pnl'].std())}")
    
    def analyze_strategy_performance_by_type(self):
        """Analyze performance by strategy type"""
        
        print("\n📊 PERFORMANCE BY STRATEGY TYPE")
        print("=" * 70)
        
        if not self.db.client:
            print("❌ No database connection")
            return
        
        try:
            # Get strategies grouped by type
            strategy_types = ['Income', 'Volatility', 'Neutral', 'Directional']
            
            for strategy_type in strategy_types:
                strategies = self.db.client.table('strategies').select(
                    'probability_of_profit, risk_reward_ratio, total_score, '
                    'strategy_parameters(*)'
                ).eq('strategy_type', strategy_type) \
                 .gte('total_score', 0.5) \
                 .limit(100) \
                 .execute()
                
                if strategies.data:
                    df = pd.DataFrame(strategies.data)
                    
                    # Calculate expected returns
                    expected_returns = []
                    for _, row in df.iterrows():
                        if row.get('strategy_parameters'):
                            params = row['strategy_parameters'][0]
                            max_profit = params.get('max_profit', 0)
                            max_loss = abs(params.get('max_loss', 0))
                            prob = row['probability_of_profit']
                            
                            exp_return = (prob * max_profit) - ((1 - prob) * max_loss)
                            if max_loss > 0:
                                return_pct = (exp_return / max_loss) * 100
                                expected_returns.append(return_pct)
                    
                    if expected_returns:
                        avg_return = np.mean(expected_returns)
                        avg_prob = df['probability_of_profit'].mean()
                        avg_rr = df['risk_reward_ratio'].mean()
                        
                        print(f"\n{strategy_type.upper()} STRATEGIES:")
                        print(f"  • Count: {len(df)}")
                        print(f"  • Avg Probability: {avg_prob:.1%}")
                        print(f"  • Avg Risk-Reward: {avg_rr:.2f}")
                        print(f"  • Expected Return: {avg_return:.1f}%")
                        
        except Exception as e:
            print(f"❌ Error analyzing by type: {e}")
    
    def show_risk_metrics_calculation(self):
        """Demonstrate how to calculate various risk metrics"""
        
        print("\n📐 RISK METRICS CALCULATION")
        print("=" * 70)
        
        print("\n1. VALUE AT RISK (VaR):")
        print("   • 95% VaR = Portfolio Value × Volatility × 1.65")
        print("   • For ₹1 crore with 20% volatility:")
        print(f"     Daily VaR = {format_currency(10000000 * 0.20 * 1.65 / np.sqrt(252))}")
        
        print("\n2. MAXIMUM POSITION SIZES:")
        position_examples = [
            ("Conservative", 0.01, 0.02),
            ("Moderate", 0.02, 0.05),
            ("Aggressive", 0.03, 0.08)
        ]
        
        for style, risk_per_trade, max_per_position in position_examples:
            print(f"\n   {style}:")
            print(f"   • Risk per trade: {risk_per_trade:.1%} = {format_currency(self.capital * risk_per_trade)}")
            print(f"   • Max per position: {max_per_position:.1%} = {format_currency(self.capital * max_per_position)}")
        
        print("\n3. PORTFOLIO HEAT (TOTAL RISK):")
        print("   • Sum of all open position risks")
        print("   • Should not exceed 6-10% of capital")
        print("   • Example: 5 positions × 2% risk = 10% heat")
        
        print("\n4. CORRELATION RISK:")
        print("   • Avoid multiple positions in same sector")
        print("   • Limit correlated trades (e.g., NIFTY + BANKNIFTY)")
        print("   • Use correlation matrix for position sizing")
    
    def demonstrate_performance_tracking(self):
        """Show how to track actual performance"""
        
        print("\n📈 PERFORMANCE TRACKING TEMPLATE")
        print("=" * 70)
        
        print("\n1. DAILY TRACKING:")
        print("   Date | Strategy | Entry | Exit | P&L | % Return | Days Held")
        print("   " + "-" * 60)
        print("   Today | RELIANCE IC | 5,000 | 2,500 | 2,500 | 50% | 15")
        print("   Today | TCS CSP | 3,000 | -6,000 | -3,000 | -100% | 30")
        
        print("\n2. MONTHLY SUMMARY:")
        print("   • Total Trades: 20")
        print("   • Winners: 14 (70%)")
        print("   • Total P&L: ₹1,25,000")
        print("   • Return on Capital: 1.25%")
        print("   • Average Winner: ₹15,000")
        print("   • Average Loser: ₹8,500")
        
        print("\n3. KEY RATIOS TO MONITOR:")
        print("   • Win Rate vs Expected (Actual 70% vs Expected 65%)")
        print("   • Profit Factor (Total Wins / Total Losses)")
        print("   • Recovery Factor (Net Profit / Max Drawdown)")
        print("   • Expectancy per Trade")


def main():
    """Main demonstration function"""
    
    print("📊 OPTIONS PORTFOLIO BACKTESTING & ANALYSIS DEMO")
    print("For ₹1 Crore Portfolio")
    print("=" * 80)
    
    # Initialize backtester
    backtester = PortfolioBacktester(capital=10000000)
    
    # Run demonstrations
    backtester.demonstrate_backtesting_framework()
    
    # Analyze historical performance
    print("\n" + "=" * 80)
    print("📈 ANALYZING HISTORICAL PERFORMANCE (Last 30 days)")
    performance = backtester.analyze_historical_performance(days_back=30)
    
    if performance:
        print(f"\nStrategies Analyzed: {performance.get('total_strategies', 0)}")
        print(f"Average Probability: {performance.get('avg_probability', 0):.1%}")
        print(f"Average Risk-Reward: {performance.get('avg_risk_reward', 0):.2f}")
        print(f"Average Score: {performance.get('avg_score', 0):.3f}")
        
        # Show by conviction
        print("\nBy Conviction Level:")
        for level, count in performance.get('by_conviction', {}).items():
            print(f"  • {level}: {count} strategies")
    
    # Run simulation
    print("\n" + "=" * 80)
    response = input("\n🎲 Run Monte Carlo simulation? (y/n): ")
    if response.lower() == 'y':
        backtester.simulate_portfolio_performance(num_trades=100)
    
    # Analyze by strategy type
    backtester.analyze_strategy_performance_by_type()
    
    # Show risk metrics
    backtester.show_risk_metrics_calculation()
    
    # Show tracking template
    backtester.demonstrate_performance_tracking()
    
    print("\n" + "=" * 80)
    print("✅ Backtesting demo completed!")
    
    print("\n📝 BACKTESTING BEST PRACTICES:")
    print("1. Always account for transaction costs and slippage")
    print("2. Use out-of-sample data for validation")
    print("3. Don't over-optimize (avoid curve fitting)")
    print("4. Consider market regime changes")
    print("5. Track actual vs expected performance")
    print("6. Regularly review and adjust strategy parameters")


if __name__ == "__main__":
    main()