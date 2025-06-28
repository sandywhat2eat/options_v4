"""
Exit Condition Evaluator for Options V4
Evaluates current position metrics against stored exit conditions
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import numpy as np

logger = logging.getLogger(__name__)

class ExitEvaluator:
    """
    Evaluates exit conditions for options positions
    
    Features:
    - Check profit targets
    - Check stop losses
    - Check time-based exits
    - Check Greek triggers
    - Recommend actions
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize exit evaluator"""
        self.logger = logger or self._setup_logger()
        
        # Action priorities
        self.action_priorities = {
            'CLOSE_IMMEDIATELY': 1,
            'CLOSE_POSITION': 2,
            'CLOSE_75%': 3,
            'CLOSE_50%': 4,
            'CLOSE_25%': 5,
            'ADJUST': 6,
            'MONITOR': 7,
            'HOLD': 8
        }
    
    def _setup_logger(self) -> logging.Logger:
        """Setup default logger if none provided"""
        logger = logging.getLogger('ExitEvaluator')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def evaluate_position(self, position_data: Dict, exit_conditions: Dict) -> Dict:
        """
        Evaluate a position against its exit conditions
        
        Args:
            position_data: Current position metrics including P&L
            exit_conditions: Stored exit conditions for the strategy
            
        Returns:
            Dictionary with evaluation results and recommendations
        """
        try:
            evaluation = {
                'strategy_id': position_data.get('strategy_id'),
                'symbol': position_data.get('symbol'),
                'strategy_name': position_data.get('strategy_name'),
                'checks': {
                    'profit_target': self._check_profit_targets(position_data, exit_conditions),
                    'stop_loss': self._check_stop_losses(position_data, exit_conditions),
                    'time_exit': self._check_time_exits(position_data, exit_conditions),
                    'adjustment': self._check_adjustments(position_data, exit_conditions)
                },
                'recommended_action': None,
                'action_reason': None,
                'urgency': 'NORMAL',
                'details': []
            }
            
            # Determine highest priority action
            highest_priority_action = self._determine_action(evaluation['checks'])
            
            evaluation['recommended_action'] = highest_priority_action['action']
            evaluation['action_reason'] = highest_priority_action['reason']
            evaluation['urgency'] = highest_priority_action['urgency']
            evaluation['details'] = highest_priority_action.get('details', [])
            
            return evaluation
            
        except Exception as e:
            self.logger.error(f"Error evaluating position: {e}")
            return {
                'strategy_id': position_data.get('strategy_id'),
                'error': str(e),
                'recommended_action': 'MONITOR',
                'urgency': 'NORMAL'
            }
    
    def _check_profit_targets(self, position_data: Dict, exit_conditions: Dict) -> Dict:
        """Check if profit targets are hit"""
        try:
            profit_targets = exit_conditions.get('profit_targets', {})
            current_pnl = position_data.get('total_pnl', 0)
            current_pnl_pct = position_data.get('total_pnl_pct', 0)
            
            results = {
                'triggered': False,
                'action': 'HOLD',
                'details': []
            }
            
            # Check primary profit target
            if 'primary' in profit_targets:
                primary = profit_targets['primary']
                target_value = primary.get('trigger_value', 0)
                
                if primary.get('trigger_type') == 'percentage':
                    if current_pnl_pct >= target_value:
                        results['triggered'] = True
                        results['action'] = primary.get('action', 'CLOSE_POSITION')
                        results['details'].append(
                            f"Primary profit target hit: {current_pnl_pct:.2f}% >= {target_value}%"
                        )
                elif target_value > 0 and current_pnl >= target_value:
                    results['triggered'] = True
                    results['action'] = primary.get('action', 'CLOSE_POSITION')
                    results['details'].append(
                        f"Primary profit target hit: ₹{current_pnl:.2f} >= ₹{target_value:.2f}"
                    )
            
            # Check scaling targets
            for level, data in profit_targets.items():
                if level.startswith('scaling_') or level.startswith('level_'):
                    target = data.get('trigger_value', 0) or data.get('profit', 0)
                    if target > 0 and current_pnl >= target and not results['triggered']:
                        results['triggered'] = True
                        results['action'] = data.get('action', 'CLOSE_25%')
                        results['details'].append(
                            f"Scaling target {level} hit: ₹{current_pnl:.2f} >= ₹{target:.2f}"
                        )
            
            # Check trailing stop activation
            if 'trailing' in profit_targets:
                trailing = profit_targets['trailing']
                activate_at = trailing.get('activate_at', 0)
                if activate_at > 0 and current_pnl >= activate_at:
                    results['details'].append(
                        f"Trailing stop activated at ₹{current_pnl:.2f}"
                    )
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error checking profit targets: {e}")
            return {'triggered': False, 'action': 'HOLD', 'details': [str(e)]}
    
    def _check_stop_losses(self, position_data: Dict, exit_conditions: Dict) -> Dict:
        """Check if stop losses are hit"""
        try:
            stop_losses = exit_conditions.get('stop_losses', {})
            current_pnl = position_data.get('total_pnl', 0)
            current_pnl_pct = position_data.get('total_pnl_pct', 0)
            max_loss = exit_conditions.get('max_loss', 0)
            
            results = {
                'triggered': False,
                'action': 'HOLD',
                'details': [],
                'urgency': 'NORMAL'
            }
            
            # Check primary stop loss
            if 'primary' in stop_losses:
                primary = stop_losses['primary']
                
                # Percentage-based stop loss
                if primary.get('trigger_type') == 'percentage':
                    stop_pct = primary.get('trigger_value', 50)
                    if max_loss > 0:
                        loss_threshold = -(max_loss * stop_pct / 100)
                        if current_pnl <= loss_threshold:
                            results['triggered'] = True
                            results['action'] = 'CLOSE_IMMEDIATELY'
                            results['urgency'] = 'HIGH'
                            results['details'].append(
                                f"STOP LOSS HIT: Loss ₹{current_pnl:.2f} exceeds {stop_pct}% of max loss ₹{max_loss:.2f}"
                            )
                    elif current_pnl_pct <= -stop_pct:
                        results['triggered'] = True
                        results['action'] = 'CLOSE_IMMEDIATELY'
                        results['urgency'] = 'HIGH'
                        results['details'].append(
                            f"STOP LOSS HIT: Loss {current_pnl_pct:.2f}% exceeds {stop_pct}% threshold"
                        )
                
                # Absolute value stop loss
                elif primary.get('loss_amount'):
                    loss_amount = primary.get('loss_amount', 0)
                    if loss_amount > 0 and current_pnl <= -loss_amount:
                        results['triggered'] = True
                        results['action'] = 'CLOSE_IMMEDIATELY'
                        results['urgency'] = 'HIGH'
                        results['details'].append(
                            f"STOP LOSS HIT: Loss ₹{current_pnl:.2f} exceeds ₹{loss_amount:.2f}"
                        )
            
            # Check time-based stop loss
            if 'time_stop' in stop_losses:
                days_in_trade = position_data.get('days_in_trade', 0)
                time_stop = stop_losses['time_stop']
                if isinstance(time_stop, dict):
                    trigger_desc = time_stop.get('trigger', '')
                    # Parse trigger description if needed
                    if 'DTE' in trigger_desc and days_in_trade > 14:
                        if current_pnl < 0:
                            results['details'].append(
                                f"Time stop approaching: {days_in_trade} days in losing trade"
                            )
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error checking stop losses: {e}")
            return {'triggered': False, 'action': 'HOLD', 'details': [str(e)], 'urgency': 'NORMAL'}
    
    def _check_time_exits(self, position_data: Dict, exit_conditions: Dict) -> Dict:
        """Check time-based exit conditions"""
        try:
            time_exits = exit_conditions.get('time_exits', {})
            days_in_trade = position_data.get('days_in_trade', 0)
            
            results = {
                'triggered': False,
                'action': 'HOLD',
                'details': [],
                'urgency': 'NORMAL'
            }
            
            # Get actual DTE from position data
            actual_dte = position_data.get('actual_dte')
            
            # If no actual DTE, try to estimate from days in trade (fallback)
            if actual_dte is None:
                # Use the old estimation method as fallback
                estimated_dte = max(30 - days_in_trade, 0)
                self.logger.warning(f"No actual DTE available, using estimated: {estimated_dte}")
                actual_dte = estimated_dte
            
            # Check primary DTE exit
            if 'primary' in time_exits:
                primary = time_exits['primary']
                dte_threshold = primary.get('trigger_value', 7)
                
                if actual_dte <= dte_threshold:
                    results['triggered'] = True
                    results['action'] = primary.get('action', 'CLOSE_POSITION')
                    results['urgency'] = 'HIGH' if actual_dte <= 1 else 'MEDIUM'
                    results['details'].append(
                        f"Time exit triggered: {actual_dte} DTE <= {dte_threshold} DTE threshold"
                    )
                    
                    # Extra urgent if expiring tomorrow or today
                    if actual_dte <= 1:
                        results['urgency'] = 'HIGH'
                        results['action'] = 'CLOSE_IMMEDIATELY'
                        results['details'].append(f"⚠️ URGENT: Option expires in {actual_dte} days!")
            
            # Check theta decay threshold
            if 'theta_decay_threshold' in time_exits:
                theta_exit = time_exits['theta_decay_threshold']
                dte_threshold = theta_exit.get('dte', 7)
                
                if actual_dte <= dte_threshold and position_data.get('total_pnl', 0) <= 0:
                    results['triggered'] = True
                    results['action'] = theta_exit.get('action', 'CLOSE_POSITION')
                    results['urgency'] = 'HIGH' if actual_dte <= 1 else 'MEDIUM'
                    results['details'].append(
                        f"Theta decay exit: Position unprofitable with {actual_dte} DTE"
                    )
            
            # Special handling for expiry day/tomorrow
            if actual_dte <= 1:
                if not results['triggered']:
                    results['triggered'] = True
                    results['action'] = 'CLOSE_IMMEDIATELY'
                    results['urgency'] = 'HIGH'
                    results['details'].append(f"⚠️ EMERGENCY: Option expires in {actual_dte} days - must exit!")
            
            # General time warnings
            elif actual_dte <= 3:
                results['details'].append(f"⚠️ Position expires in {actual_dte} days - monitor closely")
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error checking time exits: {e}")
            return {'triggered': False, 'action': 'HOLD', 'details': [str(e)], 'urgency': 'NORMAL'}
    
    def _check_adjustments(self, position_data: Dict, exit_conditions: Dict) -> Dict:
        """Check if adjustments are needed"""
        try:
            adjustments = exit_conditions.get('adjustment_criteria', {})
            
            results = {
                'triggered': False,
                'action': 'MONITOR',
                'details': []
            }
            
            # Check if position is under pressure
            current_pnl_pct = position_data.get('total_pnl_pct', 0)
            
            # Defensive adjustment if losing more than 25% but less than stop loss
            if current_pnl_pct < -25 and current_pnl_pct > -50:
                results['triggered'] = True
                results['action'] = 'ADJUST'
                results['details'].append(
                    f"Consider defensive adjustment: Position down {abs(current_pnl_pct):.2f}%"
                )
            
            # Strategy-specific adjustments
            strategy_name = position_data.get('strategy_name', '')
            
            if 'Butterfly Spread' in strategy_name:
                # Butterfly specific adjustments
                if abs(current_pnl_pct) > 30:
                    results['details'].append(
                        "Butterfly position showing significant movement - review for adjustment"
                    )
            
            elif 'Iron Condor' in strategy_name:
                # Iron Condor specific
                results['details'].append(
                    "Monitor short strikes for potential roll or adjustment"
                )
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error checking adjustments: {e}")
            return {'triggered': False, 'action': 'MONITOR', 'details': [str(e)]}
    
    def _determine_action(self, checks: Dict) -> Dict:
        """Determine the highest priority action from all checks"""
        try:
            # Collect all triggered actions
            triggered_actions = []
            
            for check_type, check_result in checks.items():
                if check_result.get('triggered', False):
                    action = check_result.get('action', 'MONITOR')
                    urgency = check_result.get('urgency', 'NORMAL')
                    details = check_result.get('details', [])
                    
                    triggered_actions.append({
                        'check_type': check_type,
                        'action': action,
                        'urgency': urgency,
                        'details': details,
                        'priority': self.action_priorities.get(action, 999)
                    })
            
            # If no actions triggered, return monitor
            if not triggered_actions:
                return {
                    'action': 'MONITOR',
                    'reason': 'No exit conditions triggered',
                    'urgency': 'NORMAL',
                    'details': []
                }
            
            # Sort by priority (lower number = higher priority)
            triggered_actions.sort(key=lambda x: x['priority'])
            
            # Return highest priority action
            highest = triggered_actions[0]
            
            # Adjust urgency based on stop loss
            if highest['check_type'] == 'stop_loss':
                highest['urgency'] = 'HIGH'
            
            return {
                'action': highest['action'],
                'reason': f"{highest['check_type'].replace('_', ' ').title()} triggered",
                'urgency': highest['urgency'],
                'details': highest['details']
            }
            
        except Exception as e:
            self.logger.error(f"Error determining action: {e}")
            return {
                'action': 'MONITOR',
                'reason': 'Error in evaluation',
                'urgency': 'NORMAL',
                'details': [str(e)]
            }
    
    def evaluate_portfolio(self, positions_with_pnl: List[Dict], 
                          exit_conditions_map: Dict[int, Dict]) -> List[Dict]:
        """
        Evaluate entire portfolio of positions
        
        Args:
            positions_with_pnl: List of positions with current P&L data
            exit_conditions_map: Map of strategy_id to exit conditions
            
        Returns:
            List of evaluation results for all positions
        """
        evaluations = []
        
        for position in positions_with_pnl:
            strategy_id = position.get('strategy_id')
            exit_conditions = exit_conditions_map.get(strategy_id, {})
            
            evaluation = self.evaluate_position(position, exit_conditions)
            evaluations.append(evaluation)
        
        # Sort by urgency and action priority
        urgency_order = {'HIGH': 1, 'MEDIUM': 2, 'NORMAL': 3}
        evaluations.sort(
            key=lambda x: (
                urgency_order.get(x.get('urgency', 'NORMAL'), 999),
                self.action_priorities.get(x.get('recommended_action', 'MONITOR'), 999)
            )
        )
        
        return evaluations
    
    def get_action_summary(self, evaluations: List[Dict]) -> Dict:
        """Get summary of recommended actions"""
        summary = {
            'total_positions': len(evaluations),
            'immediate_actions': 0,
            'adjustments_needed': 0,
            'monitoring': 0,
            'high_urgency': [],
            'medium_urgency': [],
            'actions_by_type': {}
        }
        
        for eval in evaluations:
            action = eval.get('recommended_action', 'MONITOR')
            urgency = eval.get('urgency', 'NORMAL')
            
            # Count by action type
            if action in ['CLOSE_IMMEDIATELY', 'CLOSE_POSITION']:
                summary['immediate_actions'] += 1
            elif action == 'ADJUST':
                summary['adjustments_needed'] += 1
            else:
                summary['monitoring'] += 1
            
            # Track urgency
            if urgency == 'HIGH':
                summary['high_urgency'].append({
                    'symbol': eval.get('symbol'),
                    'strategy': eval.get('strategy_name'),
                    'action': action,
                    'reason': eval.get('action_reason')
                })
            elif urgency == 'MEDIUM':
                summary['medium_urgency'].append({
                    'symbol': eval.get('symbol'),
                    'strategy': eval.get('strategy_name'),
                    'action': action,
                    'reason': eval.get('action_reason')
                })
            
            # Count actions by type
            if action not in summary['actions_by_type']:
                summary['actions_by_type'][action] = 0
            summary['actions_by_type'][action] += 1
        
        return summary

def main():
    """Test the exit evaluator"""
    evaluator = ExitEvaluator()
    
    # Test data
    test_position = {
        'strategy_id': 1,
        'symbol': 'TEST',
        'strategy_name': 'Bull Call Spread',
        'total_pnl': 5000,
        'total_pnl_pct': 25,
        'days_in_trade': 10
    }
    
    test_exit_conditions = {
        'profit_targets': {
            'primary': {
                'trigger_value': 4000,
                'trigger_type': 'price',
                'action': 'CLOSE_POSITION'
            }
        },
        'stop_losses': {
            'primary': {
                'trigger_value': 50,
                'trigger_type': 'percentage',
                'action': 'CLOSE_IMMEDIATELY'
            }
        },
        'time_exits': {
            'primary': {
                'trigger_value': 7,
                'trigger_type': 'dte',
                'action': 'CLOSE_POSITION'
            }
        },
        'max_loss': 10000
    }
    
    result = evaluator.evaluate_position(test_position, test_exit_conditions)
    
    print("\n📊 Exit Evaluation Test")
    print("=" * 60)
    print(f"Position: {test_position['symbol']} - {test_position['strategy_name']}")
    print(f"Current P&L: ₹{test_position['total_pnl']} ({test_position['total_pnl_pct']}%)")
    print(f"\nRecommended Action: {result['recommended_action']}")
    print(f"Reason: {result['action_reason']}")
    print(f"Urgency: {result['urgency']}")
    print("\nDetails:")
    for detail in result.get('details', []):
        print(f"  • {detail}")

if __name__ == "__main__":
    main()