#!/usr/bin/env python3
"""
Real-time Trading System Demo
Demonstrates the hybrid real-time monitoring system in action
"""

import asyncio
import logging
import signal
import sys
from datetime import datetime

# Import real-time components
sys.path.append('/Users/jaykrish/Documents/digitalocean/cronjobs/options_v4')

from realtime_automated_monitor import RealtimeAutomatedMonitor
from data_scripts.realtime_market_fetcher import RealtimeMarketFetcher
from core.position_cache_manager import PositionCacheManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

class RealtimeSystemDemo:
    """
    Demonstration of the real-time trading system
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Components
        self.monitor = None
        self.market_fetcher = None
        self.position_cache = None
        
        # Demo state
        self.is_running = False
        self.demo_start_time = None
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info("Received shutdown signal, stopping demo...")
        self.is_running = False
    
    async def run_demo(self, mode='simulation', duration_minutes=5):
        """
        Run the real-time system demo
        
        Args:
            mode: 'simulation' or 'live' (determines if exits are executed)
            duration_minutes: How long to run the demo
        """
        try:
            self.demo_start_time = datetime.now()
            self.is_running = True
            
            self.logger.info("🚀 Starting Real-time Trading System Demo")
            self.logger.info(f"Mode: {mode.upper()}")
            self.logger.info(f"Duration: {duration_minutes} minutes")
            self.logger.info("=" * 60)
            
            # Initialize components
            await self._initialize_components(mode)
            
            # Display initial status
            await self._display_initial_status()
            
            # Run demo monitoring
            await self._run_demo_monitoring(duration_minutes)
            
        except Exception as e:
            self.logger.error(f"Demo failed: {e}")
        finally:
            await self._cleanup()
    
    async def _initialize_components(self, mode):
        """Initialize all real-time components"""
        self.logger.info("🔧 Initializing real-time components...")
        
        try:
            # Initialize Position Cache Manager
            self.logger.info("  • Starting Position Cache Manager...")
            self.position_cache = PositionCacheManager(sync_interval_seconds=30)
            await self.position_cache.start()
            
            # Initialize Real-time Market Fetcher
            self.logger.info("  • Starting Real-time Market Fetcher...")
            self.market_fetcher = RealtimeMarketFetcher(
                enable_websocket=True,
                enable_cache=True
            )
            
            # Add demo price handler
            self.market_fetcher.add_price_update_handler(self._demo_price_handler)
            
            # Start real-time feed
            rt_success = await self.market_fetcher.start_realtime_feed()
            if rt_success:
                self.logger.info("  ✅ Real-time market feed active")
            else:
                self.logger.info("  ⚠️ Using REST fallback mode")
            
            # Initialize Real-time Monitor
            self.logger.info("  • Starting Real-time Monitor...")
            execute_exits = (mode.lower() == 'live')
            
            self.monitor = RealtimeAutomatedMonitor(
                execute_exits=execute_exits,
                alert_only=False,
                enable_websocket=True
            )
            
            self.logger.info("✅ All components initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize components: {e}")
            raise
    
    async def _display_initial_status(self):
        """Display initial system status"""
        self.logger.info("\n📊 INITIAL SYSTEM STATUS")
        self.logger.info("-" * 40)
        
        try:
            # Position Cache Status
            if self.position_cache:
                cache_stats = self.position_cache.get_cache_statistics()
                positions = self.position_cache.get_all_positions()
                
                self.logger.info(f"Position Cache:")
                self.logger.info(f"  • Positions cached: {len(positions)}")
                self.logger.info(f"  • Securities tracked: {cache_stats['securities_tracked']}")
                
                if positions:
                    self.logger.info(f"  • Sample positions:")
                    for i, pos in enumerate(positions[:3]):  # Show first 3
                        self.logger.info(f"    - {pos.symbol} ({pos.strategy_name}): "
                                       f"₹{pos.total_pnl:.2f} ({pos.total_pnl_pct:.1f}%)")
            
            # Market Fetcher Status
            if self.market_fetcher:
                connection_status = self.market_fetcher.get_connection_status()
                self.logger.info(f"Market Fetcher:")
                self.logger.info(f"  • Real-time active: {connection_status['realtime_active']}")
                self.logger.info(f"  • Subscribed instruments: {connection_status['subscribed_instruments']}")
                self.logger.info(f"  • Cached prices: {connection_status.get('cached_prices', 0)}")
            
            # Get current market data sample
            if self.market_fetcher:
                quotes = self.market_fetcher.get_market_quotes()
                if quotes:
                    total = quotes.get('total_instruments', 0)
                    rt_count = quotes.get('realtime_count', 0)
                    rest_count = quotes.get('rest_count', 0)
                    
                    self.logger.info(f"Market Data:")
                    self.logger.info(f"  • Total instruments: {total}")
                    self.logger.info(f"  • Real-time prices: {rt_count}")
                    self.logger.info(f"  • REST prices: {rest_count}")
            
        except Exception as e:
            self.logger.error(f"Error displaying initial status: {e}")
        
        self.logger.info("-" * 40)
    
    async def _run_demo_monitoring(self, duration_minutes):
        """Run the main demo monitoring loop"""
        self.logger.info(f"\n🔄 Starting {duration_minutes}-minute monitoring demo...")
        self.logger.info("Press Ctrl+C to stop early\n")
        
        # Start the real-time monitor in background
        monitor_task = None
        if self.monitor:
            monitor_task = asyncio.create_task(
                self.monitor.start(interval_seconds=60)  # 1-minute cycles for demo
            )
        
        # Demo statistics
        demo_stats = {
            'cycles_completed': 0,
            'price_updates_seen': 0,
            'alerts_generated': 0,
            'exits_executed': 0
        }
        
        start_time = asyncio.get_event_loop().time()
        end_time = start_time + (duration_minutes * 60)
        
        try:
            while self.is_running and asyncio.get_event_loop().time() < end_time:
                # Display periodic status updates
                await self._display_demo_status(demo_stats)
                
                # Wait for next status update
                await asyncio.sleep(30)  # Update every 30 seconds
                demo_stats['cycles_completed'] += 1
                
        except asyncio.CancelledError:
            self.logger.info("Demo monitoring cancelled")
        finally:
            # Stop monitor
            if monitor_task:
                monitor_task.cancel()
                try:
                    await monitor_task
                except asyncio.CancelledError:
                    pass
        
        # Display final demo summary
        await self._display_demo_summary(demo_stats)
    
    async def _display_demo_status(self, demo_stats):
        """Display current demo status"""
        current_time = datetime.now()
        elapsed = current_time - self.demo_start_time
        
        self.logger.info(f"\n📈 DEMO STATUS - {current_time.strftime('%H:%M:%S')} "
                        f"(Elapsed: {elapsed.total_seconds()/60:.1f}m)")
        self.logger.info("-" * 50)
        
        try:
            # Position updates
            if self.position_cache:
                positions = self.position_cache.get_all_positions()
                cache_stats = self.position_cache.get_cache_statistics()
                
                self.logger.info(f"Positions: {len(positions)} active")
                self.logger.info(f"Price updates: {cache_stats['price_updates']}")
                self.logger.info(f"Cache hits: {cache_stats['cache_hits']}")
                
                # Show position P&L updates
                if positions:
                    total_pnl = sum(pos.total_pnl for pos in positions)
                    self.logger.info(f"Portfolio P&L: ₹{total_pnl:.2f}")
            
            # Monitor statistics
            if self.monitor and hasattr(self.monitor, 'stats'):
                monitor_stats = self.monitor.stats
                self.logger.info(f"Alerts generated: {monitor_stats['alerts_generated']}")
                self.logger.info(f"Exits executed: {monitor_stats['exits_executed']}")
                self.logger.info(f"Price updates processed: {monitor_stats['price_updates_processed']}")
            
            # Connection health
            if self.market_fetcher:
                conn_status = self.market_fetcher.get_connection_status()
                health = "🟢" if conn_status['realtime_active'] else "🟡"
                self.logger.info(f"Connection health: {health}")
        
        except Exception as e:
            self.logger.error(f"Error in demo status display: {e}")
    
    async def _demo_price_handler(self, price_data):
        """Demo handler for price updates"""
        security_id = price_data.get('security_id')
        ltp = price_data.get('ltp', 0)
        
        self.logger.debug(f"💰 Price update: Security {security_id} = ₹{ltp}")
        
        # Update position cache
        if self.position_cache:
            await self.position_cache.update_price(security_id, ltp)
    
    async def _display_demo_summary(self, demo_stats):
        """Display final demo summary"""
        self.logger.info("\n" + "=" * 60)
        self.logger.info("📋 DEMO SUMMARY")
        self.logger.info("=" * 60)
        
        # Time summary
        if self.demo_start_time:
            total_time = datetime.now() - self.demo_start_time
            self.logger.info(f"Demo duration: {total_time.total_seconds()/60:.1f} minutes")
        
        # Component statistics
        if self.position_cache:
            cache_stats = self.position_cache.get_cache_statistics()
            self.logger.info(f"\nPosition Cache Performance:")
            self.logger.info(f"  • Hit ratio: {cache_stats['hit_ratio']:.1%}")
            self.logger.info(f"  • Price updates: {cache_stats['price_updates']}")
            self.logger.info(f"  • Database syncs: {cache_stats['db_syncs']}")
        
        if self.monitor and hasattr(self.monitor, 'stats'):
            monitor_stats = self.monitor.stats
            self.logger.info(f"\nMonitoring Performance:")
            self.logger.info(f"  • Positions monitored: {monitor_stats['positions_monitored']}")
            self.logger.info(f"  • Alerts generated: {monitor_stats['alerts_generated']}")
            self.logger.info(f"  • Exits executed: {monitor_stats['exits_executed']}")
            self.logger.info(f"  • Price updates processed: {monitor_stats['price_updates_processed']}")
            self.logger.info(f"  • Errors: {monitor_stats['errors']}")
        
        if self.market_fetcher:
            conn_status = self.market_fetcher.get_connection_status()
            self.logger.info(f"\nConnection Summary:")
            self.logger.info(f"  • Real-time mode: {'Active' if conn_status['realtime_active'] else 'Inactive'}")
            self.logger.info(f"  • WebSocket available: {'Yes' if conn_status['websocket_available'] else 'No'}")
            self.logger.info(f"  • REST fallback: Available")
        
        # Performance assessment
        self.logger.info(f"\n🎯 PERFORMANCE ASSESSMENT:")
        
        if self.position_cache:
            cache_stats = self.position_cache.get_cache_statistics()
            if cache_stats['hit_ratio'] > 0.8:
                self.logger.info("✅ Cache performance: Excellent")
            elif cache_stats['hit_ratio'] > 0.6:
                self.logger.info("⚠️ Cache performance: Good")
            else:
                self.logger.info("❌ Cache performance: Needs improvement")
        
        if self.monitor and hasattr(self.monitor, 'stats'):
            monitor_stats = self.monitor.stats
            error_rate = monitor_stats['errors'] / max(1, monitor_stats['positions_monitored'])
            if error_rate < 0.1:
                self.logger.info("✅ Monitoring reliability: Excellent")
            elif error_rate < 0.2:
                self.logger.info("⚠️ Monitoring reliability: Good")
            else:
                self.logger.info("❌ Monitoring reliability: Needs improvement")
        
        self.logger.info("\n🎉 Demo completed successfully!")
        self.logger.info("=" * 60)
    
    async def _cleanup(self):
        """Clean up demo resources"""
        self.logger.info("\n🧹 Cleaning up demo resources...")
        
        try:
            if self.monitor:
                await self.monitor.stop()
            
            if self.market_fetcher:
                await self.market_fetcher.stop_realtime_feed()
            
            if self.position_cache:
                await self.position_cache.stop()
            
            self.logger.info("✅ Cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")

# CLI Interface
async def main():
    """Main demo execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Real-time Trading System Demo')
    parser.add_argument('--mode', choices=['simulation', 'live'], default='simulation',
                       help='Demo mode (default: simulation)')
    parser.add_argument('--duration', type=int, default=5,
                       help='Demo duration in minutes (default: 5)')
    
    args = parser.parse_args()
    
    if args.mode == 'live':
        response = input("⚠️ LIVE mode will execute actual trades. Are you sure? (yes/no): ")
        if response.lower() != 'yes':
            print("Demo cancelled.")
            return
    
    demo = RealtimeSystemDemo()
    await demo.run_demo(mode=args.mode, duration_minutes=args.duration)

if __name__ == "__main__":
    print("🚀 Real-time Trading System Demo")
    print("This will demonstrate the hybrid real-time monitoring system.")
    print("Use --mode live to execute actual trades (use with caution!)")
    print()
    
    asyncio.run(main())