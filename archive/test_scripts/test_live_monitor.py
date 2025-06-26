#!/usr/bin/env python3
"""
Test Live Monitoring with Real Trade
Tests the monitoring system with the live ASTRAL trade
"""

import sys
import os
import asyncio
import logging
from datetime import datetime

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.position_monitor import PositionMonitor
from core.exit_evaluator import ExitEvaluator
from core.exit_executor import ExitExecutor
from data_scripts.market_quote_fetcher import MarketQuoteFetcher

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LiveMonitorTest:
    """Test live monitoring with real trade data"""
    
    def __init__(self):
        self.position_monitor = PositionMonitor()
        self.exit_evaluator = ExitEvaluator()
        self.exit_executor = ExitExecutor()
        self.market_fetcher = MarketQuoteFetcher()
        
    async def test_live_monitoring(self):
        """Test the monitoring system with live trade"""
        try:
            logger.info("🔍 Testing Live Trade Monitoring")
            logger.info("=" * 50)
            
            # Step 1: Get live positions
            logger.info("📊 Fetching live positions...")
            positions = self.position_monitor.get_open_positions()
            
            if not positions:
                logger.warning("⚠️ No open positions found")
                return
            
            logger.info(f"✅ Found {len(positions)} open positions")
            
            # Step 2: Update market fetcher to use all open trades
            await self.update_market_fetcher_for_all_trades()
            
            # Step 3: Get current market quotes
            logger.info("📈 Fetching current market quotes...")
            current_prices = self.market_fetcher.get_market_quotes()
            
            if not current_prices:
                logger.error("❌ Failed to fetch market quotes")
                return
            
            logger.info("✅ Market quotes fetched successfully")
            
            # Step 4: Process each position
            for i, position in enumerate(positions):
                await self.process_live_position(position, current_prices, i+1)
            
            logger.info("🎉 Live monitoring test completed successfully!")
            
        except Exception as e:
            logger.error(f"Live monitoring test failed: {e}")
    
    async def update_market_fetcher_for_all_trades(self):
        """Update market fetcher to include all open trades"""
        try:
            logger.info("🔧 Updating market fetcher for all open trades...")
            
            # Get all open trades
            response = self.market_fetcher.supabase_integration.client.table('trades').select(
                'security_id, symbol, type, strategy, action, strike_price'
            ).eq('order_status', 'open').execute()
            
            if response.data:
                # Extract unique security IDs
                security_ids = list(set(trade.get('security_id') for trade in response.data if trade.get('security_id')))
                
                # Update instruments
                self.market_fetcher.instruments = {
                    'NSE_EQ': [],
                    'NSE_FNO': security_ids
                }
                
                logger.info(f"✅ Updated market fetcher with {len(security_ids)} instruments")
            
        except Exception as e:
            logger.error(f"Error updating market fetcher: {e}")
    
    async def process_live_position(self, position, current_prices, position_num):
        """Process a single live position"""
        try:
            symbol = position.get('symbol', 'Unknown')
            strategy_name = position.get('strategy_name', 'Unknown')
            strategy_id = position.get('strategy_id')
            
            logger.info(f"\n📍 Position {position_num}: {symbol} - {strategy_name}")
            logger.info("-" * 40)
            
            # Show position details
            legs = position.get('legs', [])
            logger.info(f"Legs: {len(legs)}")
            for j, leg in enumerate(legs):
                strike = leg.get('strike_price', 0)
                option_type = leg.get('type', 'CE')
                action = leg.get('action', 'BUY')
                quantity = leg.get('quantity', 0)
                entry_price = leg.get('entry_price', 0)
                security_id = leg.get('security_id')
                
                logger.info(f"  Leg {j+1}: {action} {quantity} {symbol} {strike} {option_type}")
                logger.info(f"         Entry: ₹{entry_price}, Security ID: {security_id}")
            
            # Calculate P&L
            logger.info("💰 Calculating P&L...")
            pnl_data = self.position_monitor.calculate_position_pnl(position, current_prices)
            
            if pnl_data:
                total_pnl = pnl_data.get('total_pnl', 0)
                total_pnl_pct = pnl_data.get('total_pnl_pct', 0)
                entry_value = pnl_data.get('entry_value', 0)
                current_value = pnl_data.get('current_value', 0)
                days_in_trade = pnl_data.get('days_in_trade', 0)
                
                logger.info(f"  Entry Value: ₹{entry_value:.2f}")
                logger.info(f"  Current Value: ₹{current_value:.2f}")
                logger.info(f"  P&L: ₹{total_pnl:.2f} ({total_pnl_pct:.2f}%)")
                logger.info(f"  Days in Trade: {days_in_trade}")
            else:
                logger.warning("  ⚠️ Could not calculate P&L")
            
            # Get exit conditions
            logger.info("🎯 Checking exit conditions...")
            exit_conditions = self.position_monitor.get_exit_conditions(strategy_id)
            
            if exit_conditions:
                logger.info(f"  Exit conditions found: {len(exit_conditions)} levels")
            else:
                logger.warning("  ⚠️ No exit conditions found")
            
            # Evaluate exit conditions
            if pnl_data and exit_conditions:
                logger.info("⚖️ Evaluating exit conditions...")
                evaluation = self.exit_evaluator.evaluate_position(pnl_data, exit_conditions)
                
                if evaluation:
                    action = evaluation.get('recommended_action', 'MONITOR')
                    urgency = evaluation.get('urgency', 'LOW')
                    reason = evaluation.get('action_reason', 'No reason')
                    
                    logger.info(f"  Recommendation: {action}")
                    logger.info(f"  Urgency: {urgency}")
                    logger.info(f"  Reason: {reason}")
                    
                    # Check if action is needed
                    if action in ['CLOSE_IMMEDIATELY', 'CLOSE_POSITION'] and urgency in ['HIGH', 'MEDIUM']:
                        logger.info("🚨 EXIT SIGNAL DETECTED!")
                        logger.info("  In live mode, this would execute exit orders")
                        
                        # Simulate exit execution (don't actually execute)
                        logger.info("🔄 Simulating exit execution...")
                        exit_result = self.exit_executor.simulate_exit(position, evaluation)
                        
                        if exit_result.get('success'):
                            logger.info("  ✅ Exit simulation successful")
                        else:
                            logger.info(f"  ❌ Exit simulation failed: {exit_result.get('message')}")
                    else:
                        logger.info("✅ No immediate action required")
                else:
                    logger.warning("  ⚠️ Could not evaluate exit conditions")
            else:
                logger.info("  ℹ️ Skipping evaluation (missing data)")
            
        except Exception as e:
            logger.error(f"Error processing position {position_num}: {e}")

async def main():
    """Run the live monitoring test"""
    logger.info("🚀 Starting Live Trade Monitoring Test")
    logger.info(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    test = LiveMonitorTest()
    await test.test_live_monitoring()

if __name__ == "__main__":
    asyncio.run(main())