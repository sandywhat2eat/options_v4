"""
Exit Management System for all strategies
Handles profit targets, stop losses, time-based exits, and adjustments
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class ExitManager:
    """
    Comprehensive exit management for options strategies
    
    Features:
    - Profit target management
    - Stop loss triggers
    - Time-based exits
    - Greeks-based exits
    - Adjustment recommendations
    """
    
    def __init__(self):
        # Default exit parameters by strategy type
        self.default_exits = {
            'directional': {
                'profit_target_pct': 0.5,  # 50% of max profit
                'stop_loss_pct': 0.5,      # 50% of max loss
                'time_exit_dte': 7,        # Days to expiry
                'delta_threshold': 0.8,    # Delta threshold for exit
            },
            'neutral': {
                'profit_target_pct': 0.25,  # 25% of max profit
                'stop_loss_pct': 0.5,       # 50% of max loss
                'time_exit_dte': 21,        # Earlier exit for theta strategies
                'delta_threshold': 0.5,     # Breach threshold
            },
            'volatility': {
                'profit_target_pct': 0.75,  # 75% for vol expansion
                'stop_loss_pct': 0.5,       # 50% of premium
                'time_exit_dte': 10,        # Time decay accelerates
                'vega_threshold': -0.5,     # Vega turns negative
            },
            'income': {
                'profit_target_pct': 0.5,   # 50% of credit
                'stop_loss_pct': 2.0,       # 2x credit received
                'time_exit_dte': 21,        # Manage early
                'assignment_prob': 0.3,     # 30% ITM probability
            }
        }
    
    def generate_exit_conditions(self, strategy_name: str, strategy_metrics: Dict,
                               market_analysis: Dict) -> Dict:
        """
        Generate comprehensive exit conditions for a strategy
        
        Args:
            strategy_name: Name of the strategy
            strategy_metrics: Strategy calculation results
            market_analysis: Current market analysis
            
        Returns:
            Dictionary with detailed exit conditions
        """
        try:
            # Determine strategy category
            category = self._categorize_strategy(strategy_name)
            
            # Get base exit parameters
            base_exits = self.default_exits.get(category, self.default_exits['neutral'])
            
            # Calculate specific exit levels
            exit_conditions = {
                'profit_targets': self._calculate_profit_targets(
                    strategy_metrics, base_exits, category, market_analysis
                ),
                'stop_losses': self._calculate_stop_losses(
                    strategy_metrics, base_exits, category
                ),
                'time_exits': self._calculate_time_exits(
                    strategy_metrics, base_exits, category
                ),
                'greek_triggers': self._calculate_greek_triggers(
                    strategy_metrics, base_exits, category
                ),
                'adjustment_triggers': self._calculate_adjustment_triggers(
                    strategy_name, strategy_metrics, market_analysis
                ),
                'monitoring': self._generate_monitoring_plan(
                    strategy_name, category
                )
            }
            
            # Add strategy-specific conditions
            exit_conditions['specific_conditions'] = self._get_strategy_specific_exits(
                strategy_name, strategy_metrics
            )
            
            return exit_conditions
            
        except Exception as e:
            logger.error(f"Error generating exit conditions: {e}")
            return self._default_exit_conditions()
    
    def _categorize_strategy(self, strategy_name: str) -> str:
        """Categorize strategy for exit management"""
        strategy_categories = {
            'directional': [
                'Long Call', 'Long Put', 'Bull Call Spread', 'Bear Call Spread',
                'Bull Put Spread', 'Bear Put Spread'
            ],
            'neutral': [
                'Iron Condor', 'Iron Butterfly', 'Butterfly Spread',
                'Short Straddle', 'Short Strangle'
            ],
            'volatility': [
                'Long Straddle', 'Long Strangle'
            ],
            'income': [
                'Cash-Secured Put', 'Covered Call', 'Jade Lizard'
            ],
            'advanced': [
                'Calendar Spread', 'Diagonal Spread', 'Call Ratio Spread',
                'Put Ratio Spread', 'Broken Wing Butterfly'
            ]
        }
        
        for category, strategies in strategy_categories.items():
            if strategy_name in strategies:
                return category
        
        return 'neutral'  # Default
    
    def _calculate_profit_targets(self, metrics: Dict, base_exits: Dict,
                                category: str, market_analysis: Dict = None) -> Dict:
        """Calculate profit target levels based on realistic expected moves"""
        try:
            max_profit = metrics.get('max_profit', 0)
            
            # Check if we should use realistic targets based on expected moves
            if market_analysis and category in ['directional']:
                realistic_profit = self._calculate_realistic_profit(metrics, market_analysis)
                if realistic_profit and realistic_profit < max_profit:
                    # Use realistic profit instead of theoretical max
                    max_profit = realistic_profit
            
            if max_profit == float('inf'):
                # For unlimited profit strategies
                return {
                    'primary': {
                        'target': '50-100% of debit paid',
                        'action': 'Close position',
                        'reasoning': 'Capture significant gains'
                    },
                    'scaling': {
                        'level_1': '50% profit - close half position',
                        'level_2': '100% profit - close 75% position',
                        'level_3': 'Trail stop on remainder'
                    }
                }
            
            # Calculate specific levels
            primary_target = max_profit * base_exits['profit_target_pct']
            
            # Scaling targets
            scale_1 = max_profit * 0.25
            scale_2 = max_profit * 0.50
            scale_3 = max_profit * 0.75
            
            return {
                'primary': {
                    'target': primary_target,
                    'target_pct': base_exits['profit_target_pct'] * 100,
                    'action': 'Close entire position' if category != 'directional' else 'Close 50%',
                    'reasoning': self._get_profit_reasoning(category)
                },
                'scaling': {
                    'level_1': {'profit': scale_1, 'action': 'Close 25%'},
                    'level_2': {'profit': scale_2, 'action': 'Close 50%'},
                    'level_3': {'profit': scale_3, 'action': 'Close 75%'}
                },
                'trailing': {
                    'activate_at': primary_target,
                    'trail_by': max_profit * 0.1  # Trail by 10% of max profit
                }
            }
            
        except Exception as e:
            logger.error(f"Error calculating profit targets: {e}")
            return {'primary': {'target': 'Manual monitoring required'}}
    
    def _calculate_stop_losses(self, metrics: Dict, base_exits: Dict,
                             category: str) -> Dict:
        """Calculate stop loss levels"""
        try:
            max_loss = abs(metrics.get('max_loss', 0))
            net_credit = metrics.get('net_credit', 0)
            
            if max_loss == float('inf'):
                # For unlimited risk strategies
                if net_credit > 0:
                    return {
                        'primary': {
                            'trigger': f'{base_exits["stop_loss_pct"]}x credit received',
                            'action': 'Close position immediately',
                            'type': 'Credit-based stop'
                        },
                        'technical': {
                            'trigger': 'Breach of key support/resistance',
                            'action': 'Evaluate for exit or adjustment'
                        }
                    }
                else:
                    return {
                        'primary': {
                            'trigger': '2x debit paid',
                            'action': 'Close position',
                            'type': 'Multiple-based stop'
                        }
                    }
            
            # Calculate specific stop levels
            primary_stop = max_loss * base_exits['stop_loss_pct']
            
            return {
                'primary': {
                    'loss_amount': primary_stop,
                    'loss_pct': base_exits['stop_loss_pct'] * 100,
                    'action': 'Close entire position',
                    'type': 'Percentage-based stop'
                },
                'technical': {
                    'breakeven_breach': 'Monitor if price exceeds breakeven',
                    'support_resistance': 'Exit if key levels broken',
                    'trend_reversal': 'Exit on confirmed reversal'
                },
                'time_stop': {
                    'trigger': f'Loss > {primary_stop/2} with < {base_exits["time_exit_dte"]} DTE',
                    'action': 'Close to avoid gamma risk'
                }
            }
            
        except Exception as e:
            logger.error(f"Error calculating stop losses: {e}")
            return {'primary': {'trigger': 'Manual monitoring required'}}
    
    def _calculate_time_exits(self, metrics: Dict, base_exits: Dict,
                            category: str) -> Dict:
        """Calculate time-based exit triggers"""
        try:
            # Different time exits by strategy type
            time_exits = {
                'primary_dte': base_exits['time_exit_dte'],
                'theta_decay_threshold': {
                    'dte': base_exits['time_exit_dte'],
                    'action': 'Close if not profitable',
                    'reasoning': 'Theta decay accelerates'
                }
            }
            
            if category == 'income':
                time_exits['assignment_prevention'] = {
                    'dte': 7,
                    'condition': 'If short option ITM',
                    'action': 'Roll or close'
                }
            elif category == 'neutral':
                time_exits['gamma_risk'] = {
                    'dte': 14,
                    'condition': 'Price near short strikes',
                    'action': 'Reduce position size'
                }
            elif category == 'volatility':
                time_exits['vol_contraction'] = {
                    'dte': 10,
                    'condition': 'If IV contracted significantly',
                    'action': 'Close to capture remaining value'
                }
            
            # Add percentage time decay triggers
            time_exits['time_decay_levels'] = {
                '25%_time_passed': 'Evaluate position performance',
                '50%_time_passed': 'Consider closing if at profit',
                '75%_time_passed': 'Exit unless strong conviction'
            }
            
            return time_exits
            
        except Exception as e:
            logger.error(f"Error calculating time exits: {e}")
            return {'primary_dte': 7}
    
    def _calculate_greek_triggers(self, metrics: Dict, base_exits: Dict,
                                category: str) -> Dict:
        """Calculate Greeks-based exit triggers"""
        try:
            greeks = metrics.get('greeks', {})
            
            greek_triggers = {}
            
            # Delta triggers
            if 'delta' in greeks:
                if category in ['neutral', 'income']:
                    greek_triggers['delta'] = {
                        'threshold': base_exits.get('delta_threshold', 0.5),
                        'condition': 'Position delta exceeds threshold',
                        'action': 'Adjust or exit to maintain neutrality'
                    }
                elif category == 'directional':
                    greek_triggers['delta'] = {
                        'threshold': base_exits.get('delta_threshold', 0.8),
                        'condition': 'Option becomes deep ITM',
                        'action': 'Consider taking profits'
                    }
            
            # Gamma triggers
            if 'gamma' in greeks:
                greek_triggers['gamma'] = {
                    'threshold': abs(greeks['gamma']) * 2,
                    'condition': 'Gamma risk doubles',
                    'action': 'Reduce position or hedge'
                }
            
            # Theta triggers
            if 'theta' in greeks:
                if category == 'volatility':
                    greek_triggers['theta'] = {
                        'condition': 'Daily theta > 5% of position value',
                        'action': 'Exit to stop time decay losses'
                    }
                else:
                    greek_triggers['theta'] = {
                        'condition': 'Theta income < expected',
                        'action': 'Evaluate for better opportunities'
                    }
            
            # Vega triggers
            if 'vega' in greeks:
                if category == 'volatility':
                    greek_triggers['vega'] = {
                        'condition': 'IV contracts > 20%',
                        'action': 'Close long volatility positions'
                    }
                else:
                    greek_triggers['vega'] = {
                        'condition': 'IV expands > 50%',
                        'action': 'Consider closing short vol positions'
                    }
            
            return greek_triggers
            
        except Exception as e:
            logger.error(f"Error calculating Greek triggers: {e}")
            return {}
    
    def _calculate_adjustment_triggers(self, strategy_name: str, metrics: Dict,
                                     market_analysis: Dict) -> Dict:
        """Calculate adjustment triggers and actions"""
        try:
            adjustments = {
                'defensive': self._get_defensive_adjustments(strategy_name, metrics),
                'offensive': self._get_offensive_adjustments(strategy_name, metrics),
                'rolling': self._get_rolling_adjustments(strategy_name, metrics),
                'morphing': self._get_morphing_adjustments(strategy_name, metrics)
            }
            
            # Add market-based adjustments
            if market_analysis.get('direction') != market_analysis.get('original_direction'):
                adjustments['direction_change'] = {
                    'trigger': 'Market direction reversed',
                    'action': 'Close directional strategies, adjust neutral strategies'
                }
            
            return adjustments
            
        except Exception as e:
            logger.error(f"Error calculating adjustments: {e}")
            return {}
    
    def _get_defensive_adjustments(self, strategy_name: str, metrics: Dict) -> Dict:
        """Get defensive adjustment options"""
        defensive = {}
        
        if strategy_name == 'Iron Condor':
            defensive['threatened_side'] = {
                'trigger': 'Price approaches short strike',
                'actions': [
                    'Roll untested side closer for credit',
                    'Close threatened side',
                    'Convert to Iron Butterfly'
                ]
            }
        elif strategy_name in ['Short Straddle', 'Short Strangle']:
            defensive['breach_defense'] = {
                'trigger': 'Price exceeds expected range',
                'actions': [
                    'Buy protective option',
                    'Roll to next expiry',
                    'Convert to Iron Butterfly/Condor'
                ]
            }
        elif 'Ratio' in strategy_name:
            defensive['ratio_defense'] = {
                'trigger': 'Price threatens naked side',
                'actions': [
                    'Buy back one short option',
                    'Add protective long option',
                    'Close entire position'
                ]
            }
        
        return defensive
    
    def _get_offensive_adjustments(self, strategy_name: str, metrics: Dict) -> Dict:
        """Get offensive adjustment options"""
        offensive = {}
        
        if strategy_name in ['Long Call', 'Long Put']:
            offensive['momentum'] = {
                'trigger': 'Strong directional momentum',
                'actions': [
                    'Add to position on pullback',
                    'Roll to higher/lower strike',
                    'Convert to spread to lock profits'
                ]
            }
        elif strategy_name == 'Calendar Spread':
            offensive['vol_expansion'] = {
                'trigger': 'IV expands in back month',
                'actions': [
                    'Close for profit',
                    'Roll to next cycle',
                    'Add diagonal element'
                ]
            }
        
        return offensive
    
    def _get_rolling_adjustments(self, strategy_name: str, metrics: Dict) -> Dict:
        """Get rolling adjustment options"""
        rolling = {}
        
        if strategy_name in ['Cash-Secured Put', 'Covered Call']:
            rolling['assignment_prevention'] = {
                'trigger': 'Short option ITM near expiry',
                'actions': [
                    'Roll out to next expiry',
                    'Roll out and down/up',
                    'Accept assignment if desired'
                ]
            }
        elif 'Spread' in strategy_name:
            rolling['spread_roll'] = {
                'trigger': 'Near expiry with profit',
                'actions': [
                    'Roll entire spread to next expiry',
                    'Roll winning side only',
                    'Widen/narrow strikes on roll'
                ]
            }
        
        return rolling
    
    def _get_morphing_adjustments(self, strategy_name: str, metrics: Dict) -> Dict:
        """Get strategy morphing options"""
        morphing = {}
        
        morphing['general'] = {
            'long_to_spread': 'Convert long option to spread to reduce cost',
            'spread_to_condor': 'Add opposite spread to create condor',
            'straddle_to_butterfly': 'Add wings to straddle for protection'
        }
        
        if strategy_name == 'Long Straddle':
            morphing['specific'] = {
                'trigger': 'One side profitable',
                'actions': [
                    'Close profitable side, ride the other',
                    'Convert to Iron Butterfly',
                    'Roll profitable side to spread'
                ]
            }
        
        return morphing
    
    def _generate_monitoring_plan(self, strategy_name: str, category: str) -> Dict:
        """Generate monitoring frequency and key metrics"""
        try:
            # Base monitoring frequency
            if category in ['neutral', 'income']:
                frequency = 'Daily'
                critical_times = ['Market open', 'Market close']
            elif category == 'volatility':
                frequency = '2-3 times daily'
                critical_times = ['Open', 'Midday', 'Close']
            else:
                frequency = 'Daily with alerts'
                critical_times = ['Major market moves']
            
            # Key metrics to monitor
            monitor_metrics = {
                'price': 'Spot price vs strikes/breakevens',
                'pnl': 'Current P&L vs targets',
                'greeks': 'Delta, Gamma, Theta changes',
                'iv': 'Implied volatility changes',
                'liquidity': 'Bid-ask spreads',
                'news': 'Company/market news'
            }
            
            # Alert conditions
            alerts = {
                'price_alerts': [
                    'Within 2% of breakeven',
                    'At short strike',
                    'Major support/resistance'
                ],
                'pnl_alerts': [
                    'At 50% of profit target',
                    'At 50% of stop loss',
                    'Unusual P&L swings'
                ],
                'greek_alerts': [
                    'Delta exceeds threshold',
                    'Gamma doubles',
                    'Vega risk increases'
                ]
            }
            
            return {
                'frequency': frequency,
                'critical_times': critical_times,
                'monitor_metrics': monitor_metrics,
                'alerts': alerts
            }
            
        except Exception as e:
            logger.error(f"Error generating monitoring plan: {e}")
            return {'frequency': 'Daily'}
    
    def _get_strategy_specific_exits(self, strategy_name: str, metrics: Dict) -> Dict:
        """Get strategy-specific exit conditions"""
        specific = {}
        
        if strategy_name == 'Iron Condor':
            specific['21_dte_rule'] = 'Close if profitable at 21 DTE'
            specific['loss_management'] = 'Exit if loss > 2x credit'
            specific['wing_test'] = 'Adjust if price tests either wing'
            
        elif strategy_name == 'Calendar Spread':
            specific['iv_convergence'] = 'Exit if front/back month IV converges'
            specific['pin_risk'] = 'Manage carefully near front month expiry'
            
        elif strategy_name == 'Jade Lizard':
            specific['no_upside_risk'] = 'Let call spread expire if OTM'
            specific['put_management'] = 'Roll put if tested'
            
        elif 'Ratio' in strategy_name:
            specific['ratio_risk'] = 'Monitor naked option exposure closely'
            specific['delta_neutral'] = 'Maintain delta neutrality if possible'
        
        return specific
    
    def _get_profit_reasoning(self, category: str) -> str:
        """Get reasoning for profit targets by category"""
        reasons = {
            'directional': 'Capture gains before time decay accelerates',
            'neutral': 'Theta strategies benefit from early profit taking',
            'volatility': 'Vol can contract quickly, lock in expansion gains',
            'income': 'Consistent income more important than max profit',
            'advanced': 'Complex strategies need active management'
        }
        return reasons.get(category, 'Risk management best practice')
    
    def _calculate_realistic_profit(self, metrics: Dict, market_analysis: Dict) -> float:
        """Calculate realistic profit based on expected moves"""
        try:
            # Extract key data
            legs = metrics.get('legs', [])
            if not legs:
                return None
                
            # Get expected moves
            expected_moves = market_analysis.get('price_levels', {}).get('expected_moves', {})
            one_sd_move = expected_moves.get('one_sd_move', 0)
            two_sd_move = expected_moves.get('two_sd_move', 0)
            spot_price = market_analysis.get('spot_price', 0)
            
            # For Long Put
            if len(legs) == 1 and legs[0]['option_type'] == 'PUT' and legs[0]['position'] == 'LONG':
                strike = legs[0]['strike']
                premium = legs[0]['premium']
                
                # Calculate profit at 1SD and 2SD moves
                target_1sd = spot_price - one_sd_move
                target_2sd = spot_price - two_sd_move
                
                # Profit at 1SD move
                if target_1sd < strike:
                    profit_1sd = (strike - target_1sd - premium) * metrics.get('position_details', {}).get('lot_size', 1)
                else:
                    profit_1sd = 0
                    
                # Use 1SD profit as realistic target (achievable in timeframe)
                return profit_1sd
                
            # For Long Call
            elif len(legs) == 1 and legs[0]['option_type'] == 'CALL' and legs[0]['position'] == 'LONG':
                strike = legs[0]['strike']
                premium = legs[0]['premium']
                
                # Calculate profit at 1SD move
                target_1sd = spot_price + one_sd_move
                
                if target_1sd > strike:
                    profit_1sd = (target_1sd - strike - premium) * metrics.get('position_details', {}).get('lot_size', 1)
                else:
                    profit_1sd = 0
                    
                return profit_1sd
                
            # For spreads, use spread width as max realistic profit
            elif len(legs) == 2:
                # This is already realistic for spreads
                return metrics.get('max_profit', 0)
                
            return None
            
        except Exception as e:
            logger.error(f"Error calculating realistic profit: {e}")
            return None
    
    def _default_exit_conditions(self) -> Dict:
        """Return default exit conditions"""
        return {
            'profit_targets': {
                'primary': {'target': '50% of max profit', 'action': 'Close position'}
            },
            'stop_losses': {
                'primary': {'trigger': '50% of max loss', 'action': 'Close position'}
            },
            'time_exits': {
                'primary_dte': 7,
                'action': 'Close or roll position'
            },
            'monitoring': {
                'frequency': 'Daily',
                'alerts': ['Price near breakeven', 'Significant P&L change']
            }
        }