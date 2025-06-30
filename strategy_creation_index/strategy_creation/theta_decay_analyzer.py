"""
Theta Decay Analyzer for Options Trading

This module analyzes theta decay impact over holding periods to improve
strategy selection and exit timing for short-term options trading.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class ThetaDecayAnalyzer:
    """
    Analyzes theta decay patterns and impact on option strategies
    over specific holding periods.
    """
    
    def __init__(self):
        """Initialize the theta decay analyzer"""
        self.decay_acceleration_factor = 0.7  # Decay accelerates in last 30% of life
        
    def calculate_decay_impact(self, 
                             current_theta: float, 
                             premium: float,
                             days_to_expiry: int, 
                             holding_days: int,
                             spot_price: float) -> Dict:
        """
        Calculate expected theta decay over holding period
        
        Args:
            current_theta: Current theta value (negative for long positions)
            premium: Option premium paid/received
            days_to_expiry: Days until option expiration
            holding_days: Expected holding period in days
            spot_price: Current spot price of underlying
            
        Returns:
            Dictionary containing:
            - total_decay: Total premium lost to theta
            - daily_decay_curve: Array of daily theta values
            - decay_percentage: Percentage of premium lost
            - decay_per_spot: Decay as percentage of spot price
            - acceleration_warning: True if in rapid decay zone
        """
        try:
            # Ensure theta is negative for decay calculations
            theta_value = -abs(current_theta) if current_theta != 0 else -0.01
            
            # Calculate theta acceleration over time
            daily_decay = []
            cumulative_decay = 0
            
            for day in range(holding_days):
                current_dte = days_to_expiry - day
                
                if current_dte <= 0:
                    break
                
                # Theta accelerates as we approach expiry (square root of time)
                # More aggressive acceleration in final 30% of option life
                if current_dte <= days_to_expiry * 0.3:
                    acceleration = np.sqrt(days_to_expiry / max(current_dte, 1)) * 1.5
                else:
                    acceleration = np.sqrt(days_to_expiry / current_dte)
                
                # Daily theta for this day
                day_theta = theta_value * acceleration
                daily_decay.append(day_theta)
                cumulative_decay += abs(day_theta)
            
            # Calculate decay metrics
            decay_percentage = (cumulative_decay / premium * 100) if premium > 0 else 0
            decay_per_spot = (cumulative_decay / spot_price * 100) if spot_price > 0 else 0
            
            # Warning if entering rapid decay zone
            final_dte = days_to_expiry - holding_days
            acceleration_warning = final_dte <= 15  # Last 15 days see rapid acceleration
            
            # Calculate required move to overcome theta
            required_move_points = cumulative_decay
            required_move_percent = (required_move_points / spot_price * 100) if spot_price > 0 else 0
            
            return {
                'total_decay': cumulative_decay,
                'daily_decay_curve': daily_decay,
                'decay_percentage': decay_percentage,
                'decay_per_spot': decay_per_spot,
                'average_daily_decay': cumulative_decay / holding_days if holding_days > 0 else 0,
                'acceleration_warning': acceleration_warning,
                'final_dte': final_dte,
                'required_move_points': required_move_points,
                'required_move_percent': required_move_percent,
                'theta_risk_score': self._calculate_theta_risk_score(decay_percentage, final_dte)
            }
            
        except Exception as e:
            logger.error(f"Error calculating theta decay impact: {e}")
            return self._default_decay_analysis()
    
    def analyze_strategy_theta(self, strategy_legs: List[Dict], 
                             holding_days: int,
                             spot_price: float) -> Dict:
        """
        Analyze theta impact for multi-leg strategies
        
        Args:
            strategy_legs: List of strategy legs with theta values
            holding_days: Expected holding period
            spot_price: Current spot price
            
        Returns:
            Comprehensive theta analysis for the strategy
        """
        try:
            total_theta = 0
            total_premium_paid = 0
            total_premium_received = 0
            leg_analyses = []
            
            # Analyze each leg
            for leg in strategy_legs:
                theta = leg.get('theta', 0)
                premium = leg.get('premium', 0)
                position = leg.get('position', 'LONG')
                strike = leg.get('strike', spot_price)
                
                # Adjust theta sign based on position
                if position == 'LONG':
                    effective_theta = -abs(theta)  # Negative for long positions
                    total_premium_paid += premium
                else:  # SHORT
                    effective_theta = abs(theta)   # Positive for short positions
                    total_premium_received += premium
                
                total_theta += effective_theta
                
                # Get days to expiry from leg data
                days_to_expiry = leg.get('days_to_expiry', 30)
                
                # Analyze individual leg
                leg_analysis = self.calculate_decay_impact(
                    effective_theta, 
                    premium, 
                    days_to_expiry, 
                    holding_days,
                    spot_price
                )
                leg_analysis['strike'] = strike
                leg_analysis['position'] = position
                leg_analysis['option_type'] = leg.get('option_type', 'CALL')
                
                leg_analyses.append(leg_analysis)
            
            # Calculate net strategy metrics
            net_premium = total_premium_paid - total_premium_received
            net_theta_daily = total_theta
            net_theta_period = net_theta_daily * holding_days
            
            # Determine theta characteristic
            if net_theta_daily > 0:
                theta_characteristic = 'POSITIVE'  # Earning from time decay
                theta_benefit = net_theta_period
                theta_cost = 0
            else:
                theta_characteristic = 'NEGATIVE'  # Losing to time decay
                theta_benefit = 0
                theta_cost = abs(net_theta_period)
            
            # Calculate strategy-level decay percentage
            if net_premium > 0:  # Net debit strategy
                decay_percentage = (theta_cost / net_premium * 100) if theta_cost > 0 else 0
            else:  # Net credit strategy
                decay_percentage = 0  # Credit strategies benefit from decay
            
            # Strategy scoring based on theta
            theta_score = self._calculate_strategy_theta_score(
                theta_characteristic, 
                decay_percentage, 
                holding_days
            )
            
            return {
                'net_theta_daily': net_theta_daily,
                'net_theta_period': net_theta_period,
                'theta_characteristic': theta_characteristic,
                'theta_benefit': theta_benefit,
                'theta_cost': theta_cost,
                'decay_percentage': decay_percentage,
                'theta_score': theta_score,
                'leg_analyses': leg_analyses,
                'net_premium': net_premium,
                'recommendation': self._get_theta_recommendation(
                    theta_characteristic, 
                    decay_percentage, 
                    holding_days
                )
            }
            
        except Exception as e:
            logger.error(f"Error analyzing strategy theta: {e}")
            return self._default_strategy_analysis()
    
    def calculate_theta_adjusted_targets(self, 
                                       strategy_analysis: Dict,
                                       base_profit_target: float,
                                       holding_days: int) -> Dict:
        """
        Calculate profit targets adjusted for theta decay
        
        Args:
            strategy_analysis: Output from analyze_strategy_theta
            base_profit_target: Original profit target percentage
            holding_days: Expected holding period
            
        Returns:
            Adjusted profit targets accounting for theta
        """
        try:
            theta_cost = strategy_analysis.get('theta_cost', 0)
            net_premium = abs(strategy_analysis.get('net_premium', 1))
            theta_characteristic = strategy_analysis.get('theta_characteristic', 'NEGATIVE')
            
            if theta_characteristic == 'POSITIVE':
                # Theta positive strategies can have lower profit targets
                theta_boost = (theta_cost / net_premium) * 100 if net_premium > 0 else 0
                
                adjusted_targets = {
                    'conservative': max(10, base_profit_target - theta_boost),
                    'moderate': max(20, base_profit_target - theta_boost * 0.7),
                    'aggressive': base_profit_target  # Keep original for aggressive
                }
            else:
                # Theta negative strategies need higher targets to overcome decay
                theta_hurdle = (theta_cost / net_premium) * 100 if net_premium > 0 else 0
                
                adjusted_targets = {
                    'conservative': base_profit_target + theta_hurdle * 1.5,
                    'moderate': base_profit_target + theta_hurdle * 1.2,
                    'aggressive': base_profit_target + theta_hurdle
                }
            
            # Time-based scaling
            time_based_targets = []
            for day in [holding_days * 0.25, holding_days * 0.5, holding_days * 0.75, holding_days]:
                day_int = int(day)
                if theta_characteristic == 'NEGATIVE':
                    # Need progressively higher targets as theta decay accumulates
                    day_target = adjusted_targets['moderate'] * (day / holding_days) * 1.2
                else:
                    # Can accept lower targets as theta works in our favor
                    day_target = adjusted_targets['moderate'] * (day / holding_days) * 0.9
                
                time_based_targets.append({
                    'day': day_int,
                    'target_percent': day_target,
                    'action': self._get_exit_action(day_int, holding_days)
                })
            
            return {
                'base_target': base_profit_target,
                'theta_adjusted_targets': adjusted_targets,
                'time_based_targets': time_based_targets,
                'theta_hurdle_percent': (theta_cost / net_premium * 100) if net_premium > 0 else 0,
                'recommendation': self._get_target_recommendation(theta_characteristic, theta_cost)
            }
            
        except Exception as e:
            logger.error(f"Error calculating theta adjusted targets: {e}")
            return {
                'base_target': base_profit_target,
                'theta_adjusted_targets': {
                    'conservative': base_profit_target * 1.2,
                    'moderate': base_profit_target,
                    'aggressive': base_profit_target * 0.8
                },
                'time_based_targets': [],
                'theta_hurdle_percent': 0,
                'recommendation': 'Use base targets due to calculation error'
            }
    
    def _calculate_theta_risk_score(self, decay_percentage: float, final_dte: int) -> float:
        """Calculate risk score based on theta decay (0-1, higher is riskier)"""
        # Decay percentage component (0-50% mapped to 0-0.5)
        decay_score = min(decay_percentage / 100, 0.5)
        
        # Time component (0-30 days mapped to 0-0.5)
        time_score = max(0, 0.5 - (final_dte / 60))
        
        return decay_score + time_score
    
    def _calculate_strategy_theta_score(self, 
                                      characteristic: str, 
                                      decay_percentage: float,
                                      holding_days: int) -> float:
        """Calculate strategy score based on theta characteristics (0-1, higher is better)"""
        if characteristic == 'POSITIVE':
            # Theta positive strategies get high base score
            base_score = 0.8
            # Bonus for shorter holding periods (theta harvest)
            time_bonus = max(0, 0.2 * (1 - holding_days / 30))
            return min(1.0, base_score + time_bonus)
        else:
            # Theta negative strategies penalized by decay rate
            base_score = 0.5
            decay_penalty = min(0.4, decay_percentage / 100)
            return max(0, base_score - decay_penalty)
    
    def _get_theta_recommendation(self, 
                                characteristic: str, 
                                decay_percentage: float,
                                holding_days: int) -> str:
        """Get recommendation based on theta analysis"""
        if characteristic == 'POSITIVE':
            if holding_days <= 7:
                return "Excellent theta profile for short holds. Time decay works in your favor."
            else:
                return "Good theta profile. Consider taking profits if large move occurs early."
        else:
            if decay_percentage > 30:
                return "High theta risk! Need significant move to overcome decay. Consider spreads instead."
            elif decay_percentage > 15:
                return "Moderate theta risk. Monitor closely and exit on profit targets."
            else:
                return "Acceptable theta risk for the holding period."
    
    def _get_target_recommendation(self, characteristic: str, theta_cost: float) -> str:
        """Get profit target recommendation"""
        if characteristic == 'POSITIVE':
            return "Can use lower profit targets as theta provides cushion"
        else:
            if theta_cost > 50:
                return f"Need additional {theta_cost:.0f} points to overcome theta"
            else:
                return f"Adjust targets up by {theta_cost:.0f} points for theta"
    
    def _get_exit_action(self, day: int, total_days: int) -> str:
        """Determine exit action based on time progress"""
        progress = day / total_days
        if progress <= 0.25:
            return "close_25_percent"
        elif progress <= 0.5:
            return "close_50_percent"
        elif progress <= 0.75:
            return "close_75_percent"
        else:
            return "close_remaining"
    
    def _default_decay_analysis(self) -> Dict:
        """Return default analysis on error"""
        return {
            'total_decay': 0,
            'daily_decay_curve': [],
            'decay_percentage': 0,
            'decay_per_spot': 0,
            'average_daily_decay': 0,
            'acceleration_warning': False,
            'final_dte': 30,
            'required_move_points': 0,
            'required_move_percent': 0,
            'theta_risk_score': 0.5
        }
    
    def _default_strategy_analysis(self) -> Dict:
        """Return default strategy analysis on error"""
        return {
            'net_theta_daily': 0,
            'net_theta_period': 0,
            'theta_characteristic': 'NEUTRAL',
            'theta_benefit': 0,
            'theta_cost': 0,
            'decay_percentage': 0,
            'theta_score': 0.5,
            'leg_analyses': [],
            'net_premium': 0,
            'recommendation': 'Unable to analyze theta impact'
        }