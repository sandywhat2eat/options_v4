#!/usr/bin/env python3
"""
Portfolio Monitor - Simple Options Portfolio Tracking System
Track P&L, Greeks, Risk Metrics for multi-strategy options portfolio
"""

import numpy as np
from datetime import datetime
from typing import Dict, List
import logging
from dataclasses import dataclass
from collections import defaultdict

@dataclass
class PositionMetrics:
    """Metrics for individual position"""
    symbol: str
    strategy_name: str
    entry_date: datetime
    expiry_date: datetime
    premium_paid: float  # Negative for debit, Positive for credit
    current_value: float
    pnl: float
    pnl_percent: float
    delta: float
    gamma: float
    theta: float
    vega: float
    max_profit: float
    max_loss: float
    days_to_expiry: int
    is_winning: bool

class PortfolioMonitor:
    """Monitor and track options portfolio metrics"""
    
    def __init__(self, capital: float = 1500000):
        self.total_capital = capital
        self.positions = []
        self.logger = logging.getLogger(__name__)
        
    def add_position(self, position_data: Dict):
        """Add a position to monitor"""
        # Calculate current metrics
        current_value = self._calculate_current_value(position_data)
        premium = position_data.get('premium_collected', 0) - position_data.get('premium_paid', 0)
        pnl = current_value - premium
        pnl_percent = (pnl / abs(premium)) * 100 if premium != 0 else 0
        
        # Days to expiry
        expiry = datetime.strptime(position_data['expiry_date'], '%Y-%m-%d')
        days_to_expiry = (expiry - datetime.now()).days
        
        position = PositionMetrics(
            symbol=position_data['symbol'],
            strategy_name=position_data['strategy_name'],
            entry_date=datetime.strptime(position_data['entry_date'], '%Y-%m-%d'),
            expiry_date=expiry,
            premium_paid=premium,
            current_value=current_value,
            pnl=pnl,
            pnl_percent=pnl_percent,
            delta=position_data.get('delta', 0),
            gamma=position_data.get('gamma', 0),
            theta=position_data.get('theta', 0),
            vega=position_data.get('vega', 0),
            max_profit=position_data.get('max_profit', 0),
            max_loss=position_data.get('max_loss', 0),
            days_to_expiry=days_to_expiry,
            is_winning=pnl > 0
        )
        
        self.positions.append(position)
    
    def _calculate_current_value(self, position_data: Dict) -> float:
        """Calculate current value of position"""
        # Simplified - in real implementation would use live prices
        # For now, simulate with entry price + some random movement
        base_value = position_data.get('premium_collected', 0) - position_data.get('premium_paid', 0)
        # Simulate 10% random movement
        movement = np.random.uniform(-0.1, 0.1)
        return base_value * (1 + movement)
    
    def get_portfolio_summary(self) -> Dict:
        """Get complete portfolio summary"""
        if not self.positions:
            return self._empty_summary()
        
        # Calculate totals
        total_deployed = sum(abs(p.premium_paid) for p in self.positions)
        current_value = sum(p.current_value for p in self.positions)
        total_pnl = sum(p.pnl for p in self.positions)
        
        # Portfolio Greeks
        portfolio_delta = sum(p.delta for p in self.positions)
        portfolio_theta = sum(p.theta for p in self.positions)
        portfolio_vega = sum(p.vega for p in self.positions)
        portfolio_gamma = sum(p.gamma for p in self.positions)
        
        # Risk metrics
        max_portfolio_loss = sum(p.max_loss for p in self.positions)
        max_portfolio_profit = sum(p.max_profit for p in self.positions)
        
        # Position analysis
        winning_positions = [p for p in self.positions if p.is_winning]
        losing_positions = [p for p in self.positions if not p.is_winning]
        
        # Expiry analysis
        expiry_buckets = self._analyze_expiries()
        
        # Strategy distribution
        strategy_distribution = self._analyze_strategies()
        
        return {
            'overview': {
                'total_capital': self.total_capital,
                'deployed_capital': total_deployed,
                'deployed_percent': (total_deployed / self.total_capital) * 100,
                'cash_available': self.total_capital - total_deployed,
                'cash_percent': ((self.total_capital - total_deployed) / self.total_capital) * 100,
                'current_portfolio_value': self.total_capital + total_pnl,
                'total_pnl': total_pnl,
                'total_pnl_percent': (total_pnl / self.total_capital) * 100,
                'position_count': len(self.positions)
            },
            'greeks': {
                'portfolio_delta': portfolio_delta,
                'portfolio_theta': portfolio_theta,
                'portfolio_vega': portfolio_vega,
                'portfolio_gamma': portfolio_gamma,
                'delta_per_lakh': portfolio_delta / (self.total_capital / 100000),
                'daily_theta_income': portfolio_theta,
                'theta_as_percent': (portfolio_theta / self.total_capital) * 100
            },
            'risk_metrics': {
                'max_portfolio_loss': max_portfolio_loss,
                'max_loss_percent': (abs(max_portfolio_loss) / self.total_capital) * 100,
                'max_portfolio_profit': max_portfolio_profit,
                'max_profit_percent': (max_portfolio_profit / self.total_capital) * 100,
                'risk_reward_ratio': abs(max_portfolio_profit / max_portfolio_loss) if max_portfolio_loss != 0 else 0,
                'average_position_size': total_deployed / len(self.positions) if self.positions else 0,
                'largest_position_size': max(abs(p.premium_paid) for p in self.positions) if self.positions else 0
            },
            'position_analysis': {
                'winning_count': len(winning_positions),
                'losing_count': len(losing_positions),
                'win_rate': (len(winning_positions) / len(self.positions)) * 100 if self.positions else 0,
                'average_winner': np.mean([p.pnl for p in winning_positions]) if winning_positions else 0,
                'average_loser': np.mean([p.pnl for p in losing_positions]) if losing_positions else 0,
                'best_position': self._get_best_position(),
                'worst_position': self._get_worst_position()
            },
            'expiry_analysis': expiry_buckets,
            'strategy_distribution': strategy_distribution,
            'warnings': self._check_warnings()
        }
    
    def _analyze_expiries(self) -> Dict:
        """Analyze positions by expiry"""
        buckets = {
            'this_week': [],
            'next_week': [],
            'this_month': [],
            'next_month': []
        }
        
        # Removed unused 'today' variable
        
        for position in self.positions:
            if position.days_to_expiry <= 7:
                buckets['this_week'].append(position)
            elif position.days_to_expiry <= 14:
                buckets['next_week'].append(position)
            elif position.days_to_expiry <= 30:
                buckets['this_month'].append(position)
            else:
                buckets['next_month'].append(position)
        
        return {
            'this_week': {
                'count': len(buckets['this_week']),
                'premium_at_risk': sum(abs(p.premium_paid) for p in buckets['this_week']),
                'current_pnl': sum(p.pnl for p in buckets['this_week'])
            },
            'next_week': {
                'count': len(buckets['next_week']),
                'premium_at_risk': sum(abs(p.premium_paid) for p in buckets['next_week']),
                'current_pnl': sum(p.pnl for p in buckets['next_week'])
            },
            'this_month': {
                'count': len(buckets['this_month']),
                'premium_at_risk': sum(abs(p.premium_paid) for p in buckets['this_month']),
                'current_pnl': sum(p.pnl for p in buckets['this_month'])
            },
            'next_month': {
                'count': len(buckets['next_month']),
                'premium_at_risk': sum(abs(p.premium_paid) for p in buckets['next_month']),
                'current_pnl': sum(p.pnl for p in buckets['next_month'])
            }
        }
    
    def _analyze_strategies(self) -> Dict:
        """Analyze distribution by strategy type"""
        strategy_stats = defaultdict(lambda: {'count': 0, 'pnl': 0, 'deployed': 0})
        
        for position in self.positions:
            strategy = position.strategy_name
            strategy_stats[strategy]['count'] += 1
            strategy_stats[strategy]['pnl'] += position.pnl
            strategy_stats[strategy]['deployed'] += abs(position.premium_paid)
        
        # Calculate percentages
        total_deployed = sum(abs(p.premium_paid) for p in self.positions)
        
        result = {}
        for strategy, stats in strategy_stats.items():
            result[strategy] = {
                'count': stats['count'],
                'total_pnl': stats['pnl'],
                'deployed_amount': stats['deployed'],
                'percent_of_portfolio': (stats['deployed'] / total_deployed) * 100 if total_deployed > 0 else 0,
                'average_pnl': stats['pnl'] / stats['count'] if stats['count'] > 0 else 0
            }
        
        return result
    
    def _get_best_position(self) -> Dict:
        """Get best performing position"""
        if not self.positions:
            return {}
        
        best = max(self.positions, key=lambda x: x.pnl)
        return {
            'symbol': best.symbol,
            'strategy': best.strategy_name,
            'pnl': best.pnl,
            'pnl_percent': best.pnl_percent
        }
    
    def _get_worst_position(self) -> Dict:
        """Get worst performing position"""
        if not self.positions:
            return {}
        
        worst = min(self.positions, key=lambda x: x.pnl)
        return {
            'symbol': worst.symbol,
            'strategy': worst.strategy_name,
            'pnl': worst.pnl,
            'pnl_percent': worst.pnl_percent
        }
    
    def _check_warnings(self) -> List[str]:
        """Check for portfolio warnings"""
        warnings = []
        
        if not self.positions:
            return warnings
        
        # Calculate needed metrics directly without calling get_portfolio_summary()
        portfolio_delta = sum(p.delta for p in self.positions)
        portfolio_theta = sum(p.theta for p in self.positions)
        max_loss = sum(p.max_loss for p in self.positions)
        max_loss_percent = (abs(max_loss) / self.total_capital) * 100
        
        # Get largest position
        largest_position = max(abs(p.premium_paid) for p in self.positions) if self.positions else 0
        
        # Count expiries this week
        this_week_count = sum(1 for p in self.positions if p.days_to_expiry <= 7)
        
        # Check Greeks
        if abs(portfolio_delta) > 1000:
            warnings.append(f"⚠️ High Portfolio Delta: {portfolio_delta:.0f}")
        
        if portfolio_theta < 0:
            warnings.append(f"⚠️ Negative Theta: ₹{portfolio_theta:.0f}/day")
        
        # Check risk
        if max_loss_percent > 20:
            warnings.append(f"⚠️ High Risk: Max loss {max_loss_percent:.1f}% of capital")
        
        # Check concentration
        if largest_position > self.total_capital * 0.1:
            warnings.append("⚠️ Position Concentration: Largest position > 10% of capital")
        
        # Check expiries
        if this_week_count > 5:
            warnings.append(f"⚠️ Many Expiries: {this_week_count} positions expiring this week")
        
        return warnings
    
    def _empty_summary(self) -> Dict:
        """Return empty summary structure"""
        return {
            'overview': {
                'total_capital': self.total_capital,
                'deployed_capital': 0,
                'deployed_percent': 0,
                'cash_available': self.total_capital,
                'cash_percent': 100,
                'current_portfolio_value': self.total_capital,
                'total_pnl': 0,
                'total_pnl_percent': 0,
                'position_count': 0
            },
            'greeks': {
                'portfolio_delta': 0,
                'portfolio_theta': 0,
                'portfolio_vega': 0,
                'portfolio_gamma': 0,
                'delta_per_lakh': 0,
                'daily_theta_income': 0,
                'theta_as_percent': 0
            },
            'risk_metrics': {},
            'position_analysis': {},
            'expiry_analysis': {},
            'strategy_distribution': {},
            'warnings': []
        }
    
    def display_dashboard(self):
        """Display portfolio dashboard in terminal"""
        summary = self.get_portfolio_summary()
        
        print("\n" + "="*60)
        print("📊 OPTIONS PORTFOLIO DASHBOARD")
        print("="*60)
        
        # Overview
        print("\n💰 PORTFOLIO OVERVIEW")
        print(f"Total Capital: ₹{summary['overview']['total_capital']:,.0f}")
        print(f"Deployed: ₹{summary['overview']['deployed_capital']:,.0f} ({summary['overview']['deployed_percent']:.1f}%)")
        print(f"Cash: ₹{summary['overview']['cash_available']:,.0f} ({summary['overview']['cash_percent']:.1f}%)")
        print(f"Current Value: ₹{summary['overview']['current_portfolio_value']:,.0f}")
        print(f"Total P&L: ₹{summary['overview']['total_pnl']:,.0f} ({summary['overview']['total_pnl_percent']:+.1f}%)")
        
        # Greeks
        print("\n📈 PORTFOLIO GREEKS")
        print(f"Delta: {summary['greeks']['portfolio_delta']:+.0f} ({summary['greeks']['delta_per_lakh']:.1f} per lakh)")
        print(f"Theta: ₹{summary['greeks']['portfolio_theta']:+,.0f}/day ({summary['greeks']['theta_as_percent']:+.2f}%)")
        print(f"Vega: ₹{summary['greeks']['portfolio_vega']:+,.0f}")
        
        # Risk
        print("\n⚠️ RISK METRICS")
        print(f"Max Loss: ₹{summary['risk_metrics']['max_portfolio_loss']:,.0f} ({summary['risk_metrics']['max_loss_percent']:.1f}%)")
        print(f"Max Profit: ₹{summary['risk_metrics']['max_portfolio_profit']:,.0f} ({summary['risk_metrics']['max_profit_percent']:.1f}%)")
        print(f"Risk:Reward = 1:{summary['risk_metrics']['risk_reward_ratio']:.1f}")
        
        # Positions
        print("\n🎯 POSITION ANALYSIS")
        print(f"Winning: {summary['position_analysis']['winning_count']} | Losing: {summary['position_analysis']['losing_count']}")
        print(f"Win Rate: {summary['position_analysis']['win_rate']:.1f}%")
        
        if summary['position_analysis'].get('best_position'):
            best = summary['position_analysis']['best_position']
            print(f"Best: {best['symbol']} {best['strategy']} +₹{best['pnl']:,.0f}")
        
        if summary['position_analysis'].get('worst_position'):
            worst = summary['position_analysis']['worst_position']
            print(f"Worst: {worst['symbol']} {worst['strategy']} -₹{abs(worst['pnl']):,.0f}")
        
        # Warnings
        if summary['warnings']:
            print("\n🚨 WARNINGS")
            for warning in summary['warnings']:
                print(f"  {warning}")
        
        print("\n" + "="*60)

# Example usage
if __name__ == "__main__":
    # Create monitor
    monitor = PortfolioMonitor(capital=1500000)
    
    # Add sample positions
    sample_positions = [
        {
            'symbol': 'RELIANCE',
            'strategy_name': 'Iron Condor',
            'entry_date': '2025-01-25',
            'expiry_date': '2025-02-27',
            'premium_collected': 18000,
            'premium_paid': 0,
            'delta': -50,
            'theta': 450,
            'vega': -120,
            'gamma': -0.5,
            'max_profit': 18000,
            'max_loss': -32000
        },
        {
            'symbol': 'TCS',
            'strategy_name': 'Long Call',
            'entry_date': '2025-01-26',
            'expiry_date': '2025-02-27',
            'premium_collected': 0,
            'premium_paid': 12000,
            'delta': 450,
            'theta': -180,
            'vega': 80,
            'gamma': 1.2,
            'max_profit': 100000,
            'max_loss': -12000
        },
        {
            'symbol': 'HDFC',
            'strategy_name': 'Bull Put Spread',
            'entry_date': '2025-01-24',
            'expiry_date': '2025-02-06',
            'premium_collected': 8500,
            'premium_paid': 3000,
            'delta': 120,
            'theta': 280,
            'vega': -40,
            'gamma': -0.3,
            'max_profit': 5500,
            'max_loss': -14500
        }
    ]
    
    # Add positions
    for pos in sample_positions:
        monitor.add_position(pos)
    
    # Display dashboard
    monitor.display_dashboard()