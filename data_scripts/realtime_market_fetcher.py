#!/usr/bin/env python3
"""
Real-time Market Quote Fetcher with WebSocket Support
Combines REST API fallback with WebSocket streaming for live price updates
"""

import os
import json
import time
import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional, List, Callable
from dotenv import load_dotenv
from dhanhq import dhanhq

# Import existing components
import sys
sys.path.append('/Users/jaykrish/Documents/digitalocean/cronjobs/options_v4')
from database.supabase_integration import SupabaseIntegration
from trade_monitoring.realtime.websocket_manager import WebSocketManager
from data_scripts.market_quote_fetcher import MarketQuoteFetcher

# Load environment variables
load_dotenv()

class RealtimeMarketFetcher:
    """
    Enhanced Market Quote Fetcher with WebSocket streaming capabilities
    Provides both real-time streaming and REST API fallback
    """
    
    def __init__(self, enable_websocket=True, enable_cache=True):
        """
        Initialize real-time market fetcher
        
        Args:
            enable_websocket: Enable WebSocket streaming (default True)
            enable_cache: Enable Redis caching (default True)
        """
        self.logger = logging.getLogger(__name__)
        
        # Initialize traditional market fetcher as fallback
        self.rest_fetcher = MarketQuoteFetcher()
        
        # Dhan API credentials
        self.dhan_client_id = os.getenv('DHAN_CLIENT_ID')
        self.dhan_access_token = os.getenv('DHAN_ACCESS_TOKEN')
        
        if not all([self.dhan_client_id, self.dhan_access_token]):
            raise ValueError("Missing required Dhan credentials in .env file")
        
        # Initialize Dhan client
        self.dhan = dhanhq(self.dhan_client_id, self.dhan_access_token)
        
        # Configuration
        self.enable_websocket = enable_websocket
        self.enable_cache = enable_cache
        
        # WebSocket Manager
        self.websocket_manager = None
        if self.enable_websocket:
            try:
                self.websocket_manager = WebSocketManager(
                    dhan_client=self.dhan,
                    redis_host='localhost',
                    redis_port=6379
                )
                self.websocket_manager.add_price_tick_handler(self._handle_price_update)
                self.logger.info("WebSocket manager initialized")
            except Exception as e:
                self.logger.warning(f"WebSocket manager initialization failed: {e}")
                self.websocket_manager = None
        
        # Price update handlers
        self.price_update_handlers = []
        
        # Subscribed instruments tracking
        self.current_instruments = set()
        
        # Operating mode
        self.is_realtime_active = False
        
        self.logger.info("Real-time Market Fetcher initialized")
    
    def add_price_update_handler(self, handler: Callable):
        """Add handler for real-time price updates"""
        self.price_update_handlers.append(handler)
    
    async def start_realtime_feed(self):
        """Start real-time WebSocket feed"""
        if not self.websocket_manager:
            self.logger.warning("WebSocket manager not available, falling back to REST only")
            return False
        
        try:
            await self.websocket_manager.start()
            self.is_realtime_active = True
            
            # Subscribe to current instruments
            await self._subscribe_to_current_instruments()
            
            self.logger.info("Real-time feed started successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start real-time feed: {e}")
            self.is_realtime_active = False
            return False
    
    async def stop_realtime_feed(self):
        """Stop real-time WebSocket feed"""
        if self.websocket_manager:
            await self.websocket_manager.stop()
        
        self.is_realtime_active = False
        self.logger.info("Real-time feed stopped")
    
    async def _subscribe_to_current_instruments(self):
        """Subscribe to WebSocket feed for current instruments"""
        if not self.websocket_manager:
            return
        
        try:
            # Get current instruments from REST fetcher
            all_instruments = []
            all_instruments.extend(self.rest_fetcher.instruments.get('NSE_EQ', []))
            all_instruments.extend(self.rest_fetcher.instruments.get('NSE_FNO', []))
            
            if all_instruments:
                await self.websocket_manager.subscribe_to_instruments(all_instruments)
                self.current_instruments = set(all_instruments)
                self.logger.info(f"Subscribed to {len(all_instruments)} instruments")
            
        except Exception as e:
            self.logger.error(f"Error subscribing to instruments: {e}")
    
    async def update_instrument_subscriptions(self, new_instruments: Dict[str, List[int]]):
        """Update WebSocket subscriptions when instruments change"""
        if not self.websocket_manager:
            return
        
        try:
            # Flatten new instruments list
            new_instrument_set = set()
            for exchange, instruments in new_instruments.items():
                new_instrument_set.update(instruments)
            
            # Find instruments to add and remove
            to_add = new_instrument_set - self.current_instruments
            to_remove = self.current_instruments - new_instrument_set
            
            # Update subscriptions
            if to_add:
                await self.websocket_manager.subscribe_to_instruments(list(to_add))
                self.logger.info(f"Added subscriptions for {len(to_add)} instruments")
            
            if to_remove:
                await self.websocket_manager.unsubscribe_from_instruments(list(to_remove))
                self.logger.info(f"Removed subscriptions for {len(to_remove)} instruments")
            
            self.current_instruments = new_instrument_set
            
            # Update REST fetcher instruments too
            self.rest_fetcher.instruments = new_instruments
            
        except Exception as e:
            self.logger.error(f"Error updating subscriptions: {e}")
    
    def get_latest_price(self, security_id: int) -> Optional[Dict]:
        """
        Get latest price for a security ID
        
        Args:
            security_id: Security ID to get price for
        
        Returns:
            Price data dictionary or None if not available
        """
        # Try WebSocket cache first (fastest)
        if self.websocket_manager and self.is_realtime_active:
            cached_price = self.websocket_manager.get_latest_price(security_id)
            if cached_price:
                return cached_price
        
        # Fallback to REST API
        try:
            instruments = {"NSE_FNO": [security_id]}  # Assuming most are options
            response = self.dhan.quote_data(securities=instruments)
            
            if response and 'data' in response:
                # Handle Dhan API response structure: response['data']['data']
                outer_data = response['data']
                
                # Check if this is the nested Dhan API format
                if isinstance(outer_data, dict) and 'data' in outer_data:
                    quote_data = outer_data['data']
                    
                    # Handle format: {exchange: {security_id: quote_data}}
                    if isinstance(quote_data, dict):
                        for exchange, securities in quote_data.items():
                            if isinstance(securities, dict):
                                sec_id_str = str(security_id)
                                if sec_id_str in securities:
                                    quote = securities[sec_id_str]
                                    return {
                                        'security_id': security_id,
                                        'ltp': quote.get('last_price', 0),
                                        'volume': quote.get('volume', 0),
                                        'timestamp': time.time(),
                                        'last_update': datetime.now().isoformat(),
                                        'source': 'REST'
                                    }
                else:
                    # Fallback to original logic for other API formats
                    quote_data = outer_data
                    if isinstance(quote_data, dict):
                        for exchange, quotes in quote_data.items():
                            if isinstance(quotes, list):
                                for quote in quotes:
                                    if isinstance(quote, dict) and quote.get('securityId') == security_id:
                                        return {
                                            'security_id': security_id,
                                            'ltp': quote.get('ltp', 0),
                                            'volume': quote.get('totalVolume', 0),
                                            'timestamp': time.time(),
                                            'last_update': datetime.now().isoformat(),
                                            'source': 'REST'
                                        }
            
        except Exception as e:
            self.logger.error(f"Error fetching price via REST: {e}")
        
        return None
    
    def get_multiple_latest_prices(self, security_ids: List[int]) -> Dict[int, Dict]:
        """
        Get latest prices for multiple security IDs
        
        Args:
            security_ids: List of security IDs
        
        Returns:
            Dictionary mapping security_id to price data
        """
        prices = {}
        
        # Try WebSocket cache first for all IDs
        if self.websocket_manager and self.is_realtime_active:
            for security_id in security_ids:
                cached_price = self.websocket_manager.get_latest_price(security_id)
                if cached_price:
                    prices[security_id] = cached_price
        
        # Get missing prices via REST API
        missing_ids = [sid for sid in security_ids if sid not in prices]
        
        if missing_ids:
            try:
                # Group by exchange (assuming NSE_FNO for options)
                instruments = {"NSE_FNO": missing_ids}
                response = self.dhan.quote_data(securities=instruments)
                
                if response and 'data' in response:
                    # Handle Dhan API response structure: response['data']['data']
                    outer_data = response['data']
                    
                    # Check if this is the nested Dhan API format
                    if isinstance(outer_data, dict) and 'data' in outer_data:
                        quote_data = outer_data['data']
                        
                        # Handle format: {exchange: {security_id: quote_data}}
                        if isinstance(quote_data, dict):
                            for exchange, securities in quote_data.items():
                                if isinstance(securities, dict):
                                    for sec_id_str, quote in securities.items():
                                        security_id = int(sec_id_str)
                                        if security_id in missing_ids:
                                            prices[security_id] = {
                                                'security_id': security_id,
                                                'ltp': quote.get('last_price', 0),
                                                'volume': quote.get('volume', 0),
                                                'timestamp': time.time(),
                                                'last_update': datetime.now().isoformat(),
                                                'source': 'REST'
                                            }
                    else:
                        # Fallback to original logic for other API formats
                        quote_data = outer_data
                        if isinstance(quote_data, dict):
                            for exchange, quotes in quote_data.items():
                                if isinstance(quotes, list):
                                    for quote in quotes:
                                        if isinstance(quote, dict):
                                            security_id = quote.get('securityId')
                                            if security_id in missing_ids:
                                                prices[security_id] = {
                                                    'security_id': security_id,
                                                    'ltp': quote.get('ltp', 0),
                                                    'volume': quote.get('totalVolume', 0),
                                                    'timestamp': time.time(),
                                                    'last_update': datetime.now().isoformat(),
                                                    'source': 'REST'
                                                }
                
            except Exception as e:
                self.logger.error(f"Error fetching multiple prices via REST: {e}")
        
        return prices
    
    def get_market_quotes(self) -> Optional[Dict]:
        """
        Get market quotes for all configured instruments
        Uses WebSocket cache where possible, REST API as fallback
        
        Returns:
            Dictionary containing market quotes for all instruments
        """
        try:
            # Get all configured instruments
            all_security_ids = []
            all_security_ids.extend(self.rest_fetcher.instruments.get('NSE_EQ', []))
            all_security_ids.extend(self.rest_fetcher.instruments.get('NSE_FNO', []))
            
            if not all_security_ids:
                self.logger.warning("No instruments configured")
                return None
            
            # Get prices for all instruments
            all_prices = self.get_multiple_latest_prices(all_security_ids)
            
            # Format response to match original structure
            result = {
                'data': {
                    'NSE_EQ': [],
                    'NSE_FNO': []
                },
                'timestamp': datetime.now().isoformat(),
                'total_instruments': len(all_security_ids),
                'realtime_count': sum(1 for p in all_prices.values() if p.get('source') != 'REST'),
                'rest_count': sum(1 for p in all_prices.values() if p.get('source') == 'REST')
            }
            
            # Group by exchange
            for security_id in self.rest_fetcher.instruments.get('NSE_EQ', []):
                if security_id in all_prices:
                    price_data = all_prices[security_id]
                    result['data']['NSE_EQ'].append({
                        'securityId': security_id,
                        'ltp': price_data['ltp'],
                        'totalVolume': price_data['volume'],
                        'lastUpdate': price_data['last_update'],
                        'source': price_data.get('source', 'WebSocket')
                    })
            
            for security_id in self.rest_fetcher.instruments.get('NSE_FNO', []):
                if security_id in all_prices:
                    price_data = all_prices[security_id]
                    result['data']['NSE_FNO'].append({
                        'securityId': security_id,
                        'ltp': price_data['ltp'],
                        'totalVolume': price_data['volume'],
                        'lastUpdate': price_data['last_update'],
                        'source': price_data.get('source', 'WebSocket')
                    })
            
            self.logger.info(f"Fetched quotes: {result['realtime_count']} real-time, {result['rest_count']} REST")
            return result
            
        except Exception as e:
            self.logger.error(f"Error getting market quotes: {e}")
            # Fallback to original REST fetcher
            return self.rest_fetcher.get_market_quotes()
    
    async def _handle_price_update(self, price_data: Dict):
        """Handle real-time price updates from WebSocket"""
        try:
            # Notify all registered handlers
            for handler in self.price_update_handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(price_data)
                    else:
                        # Run sync handler in background
                        asyncio.create_task(asyncio.to_thread(handler, price_data))
                except Exception as e:
                    self.logger.error(f"Error in price update handler: {e}")
        
        except Exception as e:
            self.logger.error(f"Error handling price update: {e}")
    
    def refresh_instruments_from_database(self):
        """Refresh instruments from database and update subscriptions"""
        try:
            # Use the REST fetcher to reload from database
            self.rest_fetcher._fetch_instruments_from_database()
            
            # Update WebSocket subscriptions if real-time is active
            if self.is_realtime_active:
                asyncio.create_task(
                    self.update_instrument_subscriptions(self.rest_fetcher.instruments)
                )
            
            self.logger.info("Instruments refreshed from database")
            
        except Exception as e:
            self.logger.error(f"Error refreshing instruments: {e}")
    
    def get_connection_status(self) -> Dict:
        """Get status of all connections"""
        status = {
            'realtime_active': self.is_realtime_active,
            'websocket_available': self.websocket_manager is not None,
            'subscribed_instruments': len(self.current_instruments),
            'rest_fallback_available': True
        }
        
        if self.websocket_manager:
            ws_status = self.websocket_manager.get_connection_status()
            status.update({
                'websocket_connected': ws_status['is_connected'],
                'cached_prices': ws_status['cached_prices'],
                'reconnect_attempts': ws_status['reconnect_attempts']
            })
        
        return status

# Async wrapper functions for backward compatibility
async def get_realtime_quotes(fetcher: RealtimeMarketFetcher) -> Optional[Dict]:
    """Async wrapper for getting market quotes"""
    return fetcher.get_market_quotes()

async def start_realtime_monitoring(
    fetcher: RealtimeMarketFetcher,
    price_handler: Callable = None
) -> bool:
    """Start real-time monitoring with optional price handler"""
    if price_handler:
        fetcher.add_price_update_handler(price_handler)
    
    return await fetcher.start_realtime_feed()

# Example usage and testing
if __name__ == "__main__":
    async def example_price_handler(price_data):
        """Example handler for price updates"""
        print(f"Price update: {price_data['security_id']} = ₹{price_data['ltp']}")
    
    async def main():
        # Initialize real-time fetcher
        fetcher = RealtimeMarketFetcher(enable_websocket=True)
        
        # Add price update handler
        fetcher.add_price_update_handler(example_price_handler)
        
        # Start real-time feed
        success = await fetcher.start_realtime_feed()
        if success:
            print("✅ Real-time feed started")
        else:
            print("⚠️ Falling back to REST-only mode")
        
        # Get market quotes (will use real-time where available)
        quotes = fetcher.get_market_quotes()
        if quotes:
            print(f"📊 Got quotes for {quotes['total_instruments']} instruments")
            print(f"   Real-time: {quotes['realtime_count']}")
            print(f"   REST: {quotes['rest_count']}")
        
        # Keep running for real-time updates
        try:
            print("🔄 Monitoring for real-time updates... (Ctrl+C to stop)")
            while True:
                await asyncio.sleep(10)
                status = fetcher.get_connection_status()
                print(f"Status: RT={status['realtime_active']}, "
                      f"Instruments={status['subscribed_instruments']}, "
                      f"Cached={status.get('cached_prices', 0)}")
        except KeyboardInterrupt:
            print("\n🛑 Stopping real-time feed...")
            await fetcher.stop_realtime_feed()
            print("✅ Stopped")
    
    # Run the example
    asyncio.run(main())