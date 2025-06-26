"""
Position Monitor for Options V4
Real-time monitoring of open positions with P&L tracking
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from decimal import Decimal

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.supabase_integration import SupabaseIntegration
from data_scripts.market_quote_fetcher import MarketQuoteFetcher

logger = logging.getLogger(__name__)

class PositionMonitor:
    """
    Real-time position monitoring for options strategies
    
    Features:
    - Fetch open positions from database
    - Get real-time quotes
    - Calculate P&L
    - Track exit conditions
    - Monitor time decay
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize position monitor with database and market data connections"""
        self.logger = logger or self._setup_logger()
        
        # Initialize database connection
        self.db = SupabaseIntegration(self.logger)
        if not self.db.client:
            raise ValueError("Failed to initialize database connection")
        
        # Initialize market quote fetcher
        try:
            self.quote_fetcher = MarketQuoteFetcher()
            self.logger.info("Position Monitor initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize market quote fetcher: {e}")
            raise
    
    def _setup_logger(self) -> logging.Logger:
        """Setup default logger if none provided"""
        logger = logging.getLogger('PositionMonitor')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def get_open_positions(self) -> List[Dict]:
        """Fetch all open positions from database"""
        try:
            # Get open trades
            response = self.db.client.table('trades').select(
                '*'
            ).eq(
                'order_status', 'open'
            ).order('timestamp', desc=False).execute()
            
            if not response.data:
                self.logger.info("No open positions found")
                return []
            
            # Group trades by strategy
            positions = {}
            for trade in response.data:
                strategy_id = trade.get('strategy_id')
                if strategy_id not in positions:
                    # Fetch strategy info separately if needed
                    positions[strategy_id] = {
                        'strategy_id': strategy_id,
                        'symbol': trade.get('symbol'),
                        'strategy_name': trade.get('strategy'),
                        'legs': [],
                        'entry_time': trade.get('timestamp'),
                        'total_quantity': 0,
                        'net_premium': 0
                    }
                
                # Add leg details
                leg = {
                    'trade_id': trade.get('new_id'),
                    'security_id': trade.get('security_id'),
                    'action': trade.get('action'),  # BUY/SELL
                    'type': trade.get('type'),      # CE/PE
                    'strike_price': trade.get('strike_price'),
                    'quantity': trade.get('quantity', 0),
                    'entry_price': trade.get('price', 0),
                    'order_id': trade.get('order_id'),
                    'expiry_date': trade.get('expiry_date')
                }
                
                positions[strategy_id]['legs'].append(leg)
                positions[strategy_id]['total_quantity'] = max(
                    positions[strategy_id]['total_quantity'], 
                    trade.get('quantity', 0)
                )
                
                # Calculate net premium (positive for credit, negative for debit)
                if trade.get('action') == 'SELL':
                    positions[strategy_id]['net_premium'] += trade.get('price', 0) * trade.get('quantity', 0)
                else:
                    positions[strategy_id]['net_premium'] -= trade.get('price', 0) * trade.get('quantity', 0)
            
            return list(positions.values())
            
        except Exception as e:
            self.logger.error(f"Error fetching open positions: {e}")
            return []
    
    def get_current_prices(self, positions: List[Dict]) -> Dict[int, float]:
        """Get current market prices for all security IDs in positions"""
        try:
            # Extract unique security IDs
            security_ids = set()
            for position in positions:
                for leg in position['legs']:
                    if leg.get('security_id'):
                        security_ids.add(leg['security_id'])
            
            if not security_ids:
                return {}
            
            # Update quote fetcher with our security IDs
            self.quote_fetcher.instruments = {
                "NSE_EQ": [],
                "NSE_FNO": list(security_ids)  # Options are typically FNO
            }
            
            # Fetch quotes
            quotes = self.quote_fetcher.get_market_quotes()
            
            if not quotes or 'data' not in quotes:
                self.logger.error("Failed to fetch market quotes")
                return {}
            
            # Extract last prices
            current_prices = {}
            for exchange, instruments in quotes['data'].items():
                if isinstance(instruments, dict):
                    for security_id, quote_data in instruments.items():
                        try:
                            sid = int(security_id)
                            current_prices[sid] = quote_data.get('last_price', 0)
                        except:
                            pass
            
            return current_prices
            
        except Exception as e:
            self.logger.error(f"Error fetching current prices: {e}")
            return {}
    
    def calculate_position_pnl(self, position: Dict, current_prices: Dict[int, float]) -> Dict:
        """Calculate P&L for a single position"""
        try:
            pnl_details = {
                'strategy_id': position['strategy_id'],
                'symbol': position['symbol'],
                'strategy_name': position['strategy_name'],
                'legs': [],
                'total_pnl': 0,
                'total_pnl_pct': 0,
                'unrealized_pnl': 0,
                'current_value': 0,
                'entry_value': abs(position['net_premium']),
                'days_in_trade': 0,
                'status': 'UNKNOWN'
            }
            
            # Calculate days in trade
            if position.get('entry_time'):
                entry_date = datetime.fromisoformat(position['entry_time'].replace('Z', '+00:00'))
                pnl_details['days_in_trade'] = (datetime.now() - entry_date.replace(tzinfo=None)).days
            
            # Calculate actual DTE from expiry date
            expiry_dates = []
            for leg in position['legs']:
                if leg.get('expiry_date'):
                    expiry_dates.append(leg['expiry_date'])
            
            if expiry_dates:
                # Use the earliest expiry date if multiple legs
                earliest_expiry = min(expiry_dates)
                expiry_dt = datetime.strptime(earliest_expiry, '%Y-%m-%d')
                actual_dte = (expiry_dt - datetime.now()).days
                pnl_details['actual_dte'] = max(actual_dte, 0)  # Don't go negative
                pnl_details['expiry_date'] = earliest_expiry
            else:
                pnl_details['actual_dte'] = None
                pnl_details['expiry_date'] = None
            
            # Calculate P&L for each leg
            total_current_value = 0
            total_entry_value = 0
            
            for leg in position['legs']:
                security_id = leg.get('security_id')
                current_price = current_prices.get(security_id, 0)
                entry_price = leg.get('entry_price', 0)
                quantity = leg.get('quantity', 0)
                
                # Calculate leg P&L
                if leg['action'] == 'BUY':
                    leg_pnl = (current_price - entry_price) * quantity
                    leg_entry_value = entry_price * quantity
                    leg_current_value = current_price * quantity
                else:  # SELL
                    leg_pnl = (entry_price - current_price) * quantity
                    leg_entry_value = entry_price * quantity
                    leg_current_value = current_price * quantity
                
                leg_details = {
                    'security_id': security_id,
                    'strike': leg.get('strike_price'),
                    'type': leg.get('type'),
                    'action': leg.get('action'),
                    'entry_price': entry_price,
                    'current_price': current_price,
                    'quantity': quantity,
                    'pnl': leg_pnl,
                    'pnl_pct': (leg_pnl / (entry_price * quantity) * 100) if entry_price > 0 else 0
                }
                
                pnl_details['legs'].append(leg_details)
                pnl_details['total_pnl'] += leg_pnl
                
                # Track values for percentage calculation
                if leg['action'] == 'BUY':
                    total_entry_value += leg_entry_value
                    total_current_value += leg_current_value
                else:
                    total_entry_value -= leg_entry_value
                    total_current_value -= leg_current_value
            
            # Calculate overall percentage
            if position['net_premium'] > 0:  # Credit strategy
                # For credit strategies, profit is when we can buy back for less
                pnl_details['total_pnl_pct'] = (pnl_details['total_pnl'] / position['net_premium']) * 100
            else:  # Debit strategy
                # For debit strategies, profit is when value increases
                if total_entry_value > 0:
                    pnl_details['total_pnl_pct'] = (pnl_details['total_pnl'] / total_entry_value) * 100
            
            pnl_details['current_value'] = total_current_value
            pnl_details['unrealized_pnl'] = pnl_details['total_pnl']
            
            # Determine status
            if pnl_details['total_pnl'] > 0:
                pnl_details['status'] = 'PROFIT'
            elif pnl_details['total_pnl'] < 0:
                pnl_details['status'] = 'LOSS'
            else:
                pnl_details['status'] = 'BREAKEVEN'
            
            return pnl_details
            
        except Exception as e:
            self.logger.error(f"Error calculating P&L for position {position.get('strategy_id')}: {e}")
            return {
                'strategy_id': position.get('strategy_id'),
                'error': str(e),
                'status': 'ERROR'
            }
    
    def get_exit_conditions(self, strategy_id: int) -> Dict:
        """Fetch exit conditions for a strategy from database"""
        try:
            # Get exit levels
            exit_response = self.db.client.table('strategy_exit_levels').select(
                '*'
            ).eq('strategy_id', strategy_id).execute()
            
            # Get risk management data
            risk_response = self.db.client.table('strategy_risk_management').select(
                '*'
            ).eq('strategy_id', strategy_id).execute()
            
            exit_conditions = {
                'profit_targets': {},
                'stop_losses': {},
                'time_exits': {},
                'adjustments': {}
            }
            
            # Process exit levels
            if exit_response.data:
                for exit in exit_response.data:
                    exit_type = exit.get('exit_type')
                    level_name = exit.get('level_name')
                    
                    if exit_type == 'profit_target':
                        exit_conditions['profit_targets'][level_name] = {
                            'trigger_value': exit.get('trigger_value'),
                            'trigger_type': exit.get('trigger_type'),
                            'action': exit.get('action'),
                            'reasoning': exit.get('reasoning')
                        }
                    elif exit_type == 'stop_loss':
                        exit_conditions['stop_losses'][level_name] = {
                            'trigger_value': exit.get('trigger_value'),
                            'trigger_type': exit.get('trigger_type'),
                            'action': exit.get('action'),
                            'reasoning': exit.get('reasoning')
                        }
                    elif exit_type == 'time_exit':
                        exit_conditions['time_exits'][level_name] = {
                            'trigger_value': exit.get('trigger_value'),
                            'trigger_type': exit.get('trigger_type'),
                            'action': exit.get('action'),
                            'reasoning': exit.get('reasoning')
                        }
            
            # Add risk management data
            if risk_response.data and len(risk_response.data) > 0:
                risk_data = risk_response.data[0]
                exit_conditions['max_loss'] = risk_data.get('max_capital_at_risk', 0)
                exit_conditions['adjustment_criteria'] = risk_data.get('adjustment_criteria', {})
            
            return exit_conditions
            
        except Exception as e:
            self.logger.error(f"Error fetching exit conditions for strategy {strategy_id}: {e}")
            return {}
    
    def get_position_summary(self, positions: List[Dict]) -> pd.DataFrame:
        """Create summary DataFrame of all positions with P&L"""
        try:
            # Get current prices
            current_prices = self.get_current_prices(positions)
            
            # Calculate P&L for each position
            summary_data = []
            
            for position in positions:
                pnl_data = self.calculate_position_pnl(position, current_prices)
                exit_conditions = self.get_exit_conditions(position['strategy_id'])
                
                # Get profit target and stop loss values
                profit_target = 0
                stop_loss = 0
                
                if 'profit_targets' in exit_conditions and 'primary' in exit_conditions['profit_targets']:
                    profit_target = exit_conditions['profit_targets']['primary'].get('trigger_value', 0)
                
                if 'stop_losses' in exit_conditions and 'primary' in exit_conditions['stop_losses']:
                    stop_loss = exit_conditions['stop_losses']['primary'].get('trigger_value', 0)
                
                summary_data.append({
                    'Strategy ID': position['strategy_id'],
                    'Symbol': position['symbol'],
                    'Strategy': position['strategy_name'],
                    'Entry Time': position['entry_time'],
                    'Days': pnl_data['days_in_trade'],
                    'Entry Value': position['net_premium'],
                    'Current P&L': pnl_data['total_pnl'],
                    'P&L %': pnl_data['total_pnl_pct'],
                    'Status': pnl_data['status'],
                    'Profit Target': profit_target,
                    'Stop Loss': stop_loss,
                    'Exit Signal': self._check_exit_signal(pnl_data, exit_conditions)
                })
            
            return pd.DataFrame(summary_data)
            
        except Exception as e:
            self.logger.error(f"Error creating position summary: {e}")
            return pd.DataFrame()
    
    def _check_exit_signal(self, pnl_data: Dict, exit_conditions: Dict) -> str:
        """Check if any exit condition is triggered"""
        signals = []
        
        # Check profit target
        if 'profit_targets' in exit_conditions and 'primary' in exit_conditions['profit_targets']:
            target = exit_conditions['profit_targets']['primary'].get('trigger_value', 0)
            if target > 0 and pnl_data['total_pnl'] >= target:
                signals.append('PROFIT_TARGET_HIT')
        
        # Check stop loss
        if 'stop_losses' in exit_conditions and 'primary' in exit_conditions['stop_losses']:
            stop_pct = exit_conditions['stop_losses']['primary'].get('trigger_value', 50)
            max_loss = exit_conditions.get('max_loss', 0)
            if max_loss > 0 and abs(pnl_data['total_pnl']) >= (max_loss * stop_pct / 100):
                signals.append('STOP_LOSS_HIT')
        
        # Check time exit (if we had expiry dates)
        if pnl_data['days_in_trade'] > 21:  # Default time exit
            signals.append('TIME_EXIT_APPROACHING')
        
        return ' | '.join(signals) if signals else 'MONITOR'
    
    def display_positions(self, detailed: bool = False):
        """Display current positions with P&L"""
        try:
            positions = self.get_open_positions()
            
            if not positions:
                print("\n📊 No open positions found")
                return
            
            print(f"\n📊 OPEN POSITIONS MONITOR - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 120)
            
            # Get summary
            summary_df = self.get_position_summary(positions)
            
            if not summary_df.empty:
                # Format numeric columns
                summary_df['Entry Value'] = summary_df['Entry Value'].apply(lambda x: f"₹{x:,.2f}")
                summary_df['Current P&L'] = summary_df['Current P&L'].apply(lambda x: f"₹{x:,.2f}")
                summary_df['P&L %'] = summary_df['P&L %'].apply(lambda x: f"{x:.2f}%")
                summary_df['Profit Target'] = summary_df['Profit Target'].apply(lambda x: f"₹{x:,.2f}" if x > 0 else "N/A")
                summary_df['Stop Loss'] = summary_df['Stop Loss'].apply(lambda x: f"₹{x:,.2f}" if x > 0 else "N/A")
                
                print(summary_df.to_string(index=False))
                
                # Summary statistics
                total_positions = len(positions)
                profitable = len(summary_df[summary_df['Status'] == 'PROFIT'])
                losing = len(summary_df[summary_df['Status'] == 'LOSS'])
                
                print(f"\n📈 SUMMARY:")
                print(f"   Total Positions: {total_positions}")
                print(f"   Profitable: {profitable} ({profitable/total_positions*100:.1f}%)")
                print(f"   Losing: {losing} ({losing/total_positions*100:.1f}%)")
                
                # If detailed view requested, show individual legs
                if detailed:
                    current_prices = self.get_current_prices(positions)
                    print("\n📊 DETAILED LEG INFORMATION:")
                    print("-" * 120)
                    
                    for position in positions:
                        pnl_data = self.calculate_position_pnl(position, current_prices)
                        print(f"\n{position['symbol']} - {position['strategy_name']} (ID: {position['strategy_id']})")
                        
                        for leg in pnl_data.get('legs', []):
                            action_emoji = "🔴" if leg['action'] == 'SELL' else "🟢"
                            print(f"   {action_emoji} {leg['action']} {leg['strike']} {leg['type']}: "
                                  f"Entry: ₹{leg['entry_price']:.2f} | "
                                  f"Current: ₹{leg['current_price']:.2f} | "
                                  f"P&L: ₹{leg['pnl']:.2f} ({leg['pnl_pct']:.2f}%)")
            
        except Exception as e:
            self.logger.error(f"Error displaying positions: {e}")
            import traceback
            traceback.print_exc()

def main():
    """Main function for testing"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Monitor open options positions')
    parser.add_argument('--detailed', action='store_true', help='Show detailed leg information')
    parser.add_argument('--loop', action='store_true', help='Run in continuous loop')
    parser.add_argument('--interval', type=int, default=300, help='Loop interval in seconds (default: 300)')
    
    args = parser.parse_args()
    
    try:
        monitor = PositionMonitor()
        
        if args.loop:
            print(f"Starting continuous monitoring (interval: {args.interval} seconds)")
            print("Press Ctrl+C to stop")
            
            while True:
                monitor.display_positions(detailed=args.detailed)
                print(f"\n⏰ Next update in {args.interval} seconds...")
                time.sleep(args.interval)
        else:
            monitor.display_positions(detailed=args.detailed)
            
    except KeyboardInterrupt:
        print("\n\n👋 Monitoring stopped by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import time
    main()