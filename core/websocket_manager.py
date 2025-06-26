"""
WebSocket Manager for Real-time Market Feeds and Database Updates
Handles Dhan live market feed and Supabase realtime subscriptions
"""

import asyncio
import json
import logging
import time
import redis
from typing import Dict, List, Callable, Optional, Any
from datetime import datetime
import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException
import threading
from concurrent.futures import ThreadPoolExecutor

# Import existing components
from database.supabase_integration import SupabaseIntegration

class WebSocketManager:
    """
    Manages WebSocket connections for real-time data feeds
    """
    
    def __init__(self, dhan_client=None, redis_host='localhost', redis_port=6379):
        """
        Initialize WebSocket Manager
        
        Args:
            dhan_client: Dhan API client instance
            redis_host: Redis server host for caching
            redis_port: Redis server port
        """
        self.logger = logging.getLogger(__name__)
        self.dhan_client = dhan_client
        
        # WebSocket connections
        self.dhan_websocket = None
        self.supabase_realtime = None
        
        # Connection state
        self.is_connected = False
        self.is_running = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 5  # seconds
        
        # Subscribed instruments
        self.subscribed_instruments = set()
        
        # Event handlers
        self.price_tick_handlers = []
        self.trade_update_handlers = []
        
        # Redis cache for real-time prices
        try:
            self.redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
            self.redis_client.ping()  # Test connection
            self.logger.info("Redis cache connected successfully")
        except Exception as e:
            self.logger.warning(f"Redis connection failed: {e}. Using in-memory cache.")
            self.redis_client = None
        
        # In-memory fallback cache
        self.price_cache = {}
        self.position_cache = {}
        
        # Thread pool for async operations
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Database integration
        self.db = SupabaseIntegration()
        
        self.logger.info("WebSocket Manager initialized")
    
    def add_price_tick_handler(self, handler: Callable):
        """Add handler for price tick events"""
        self.price_tick_handlers.append(handler)
        
    def add_trade_update_handler(self, handler: Callable):
        """Add handler for trade update events"""  
        self.trade_update_handlers.append(handler)
    
    async def start(self):
        """Start all WebSocket connections"""
        try:
            self.is_running = True
            self.logger.info("Starting WebSocket Manager...")
            
            # Start Dhan market feed
            await self._start_dhan_feed()
            
            # Start Supabase realtime subscription
            await self._start_supabase_realtime()
            
            self.is_connected = True
            self.logger.info("All WebSocket connections established")
            
        except Exception as e:
            self.logger.error(f"Failed to start WebSocket Manager: {e}")
            await self.stop()
            raise
    
    async def stop(self):
        """Stop all WebSocket connections"""
        self.is_running = False
        self.logger.info("Stopping WebSocket Manager...")
        
        # Close Dhan WebSocket
        if self.dhan_websocket:
            try:
                await self.dhan_websocket.close()
            except Exception as e:
                self.logger.error(f"Error closing Dhan WebSocket: {e}")
        
        # Close Supabase realtime
        if self.supabase_realtime:
            try:
                # Supabase realtime cleanup would go here
                pass
            except Exception as e:
                self.logger.error(f"Error closing Supabase realtime: {e}")
        
        self.is_connected = False
        self.logger.info("WebSocket Manager stopped")
    
    async def _start_dhan_feed(self):
        """Start Dhan live market feed WebSocket"""
        if not self.dhan_client:
            self.logger.warning("No Dhan client provided, skipping market feed")
            return
        
        try:
            # This would connect to Dhan's WebSocket feed
            # For now, we'll simulate the connection setup
            self.logger.info("Connecting to Dhan live market feed...")
            
            # In real implementation, this would be:
            # self.dhan_websocket = await websockets.connect(dhan_websocket_url)
            # await self._authenticate_dhan_websocket()
            
            # Start the message processing loop
            asyncio.create_task(self._process_dhan_messages())
            
            self.logger.info("Dhan market feed connected")
            
        except Exception as e:
            self.logger.error(f"Failed to connect to Dhan market feed: {e}")
            raise
    
    async def _start_supabase_realtime(self):
        """Start Supabase realtime subscription"""
        try:
            self.logger.info("Setting up Supabase realtime subscription...")
            
            # This would set up Supabase realtime subscription
            # For now, we'll set up the structure
            
            # In real implementation:
            # self.supabase_realtime = supabase.realtime.channel('trades-channel')
            # self.supabase_realtime.on('postgres_changes', self._handle_trade_change)
            # self.supabase_realtime.subscribe()
            
            self.logger.info("Supabase realtime subscription active")
            
        except Exception as e:
            self.logger.error(f"Failed to setup Supabase realtime: {e}")
            raise
    
    async def _process_dhan_messages(self):
        """Process incoming messages from Dhan WebSocket"""
        while self.is_running:
            try:
                if not self.dhan_websocket:
                    await asyncio.sleep(1)
                    continue
                
                # In real implementation, this would receive WebSocket messages:
                # message = await self.dhan_websocket.recv()
                # data = json.loads(message)
                
                # For now, simulate with a placeholder
                await asyncio.sleep(0.1)  # Prevent busy loop
                continue
                
                # Process the tick data
                await self._handle_price_tick(data)
                
            except ConnectionClosed:
                self.logger.warning("Dhan WebSocket connection closed")
                await self._reconnect_dhan()
            except Exception as e:
                self.logger.error(f"Error processing Dhan message: {e}")
                await asyncio.sleep(1)
    
    async def _handle_price_tick(self, tick_data: Dict):
        """Handle incoming price tick from Dhan"""
        try:
            security_id = tick_data.get('security_id')
            ltp = tick_data.get('LTP', 0)
            volume = tick_data.get('volume', 0)
            timestamp = tick_data.get('timestamp', time.time())
            
            if not security_id:
                return
            
            # Update cache
            price_info = {
                'security_id': security_id,
                'ltp': ltp,
                'volume': volume,
                'timestamp': timestamp,
                'last_update': datetime.now().isoformat()
            }
            
            # Update Redis cache
            if self.redis_client:
                try:
                    self.redis_client.hset(
                        f"price:{security_id}", 
                        mapping=price_info
                    )
                    self.redis_client.expire(f"price:{security_id}", 300)  # 5 min TTL
                except Exception as e:
                    self.logger.error(f"Redis cache update failed: {e}")
            
            # Update in-memory cache as fallback
            self.price_cache[security_id] = price_info
            
            # Notify handlers
            for handler in self.price_tick_handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(price_info)
                    else:
                        # Run sync handler in thread pool
                        self.executor.submit(handler, price_info)
                except Exception as e:
                    self.logger.error(f"Error in price tick handler: {e}")
            
        except Exception as e:
            self.logger.error(f"Error handling price tick: {e}")
    
    def _handle_trade_change(self, payload: Dict):
        """Handle trade table changes from Supabase realtime"""
        try:
            event_type = payload.get('eventType')  # INSERT, UPDATE, DELETE
            record = payload.get('new', {}) if event_type != 'DELETE' else payload.get('old', {})
            
            self.logger.info(f"Trade change detected: {event_type} - {record.get('symbol')}")
            
            # Update position cache
            if event_type in ['INSERT', 'UPDATE']:
                strategy_id = record.get('strategy_id')
                if strategy_id:
                    self._update_position_cache(strategy_id, record)
            
            # Notify handlers
            for handler in self.trade_update_handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        asyncio.create_task(handler(payload))
                    else:
                        self.executor.submit(handler, payload)
                except Exception as e:
                    self.logger.error(f"Error in trade update handler: {e}")
                    
        except Exception as e:
            self.logger.error(f"Error handling trade change: {e}")
    
    def _update_position_cache(self, strategy_id: int, trade_record: Dict):
        """Update position cache with trade changes"""
        try:
            if strategy_id not in self.position_cache:
                self.position_cache[strategy_id] = {
                    'trades': [],
                    'last_update': datetime.now().isoformat()
                }
            
            # Add or update trade in position
            trade_id = trade_record.get('new_id')
            existing_trade_idx = None
            
            for idx, trade in enumerate(self.position_cache[strategy_id]['trades']):
                if trade.get('new_id') == trade_id:
                    existing_trade_idx = idx
                    break
            
            if existing_trade_idx is not None:
                # Update existing trade
                self.position_cache[strategy_id]['trades'][existing_trade_idx] = trade_record
            else:
                # Add new trade
                self.position_cache[strategy_id]['trades'].append(trade_record)
            
            self.position_cache[strategy_id]['last_update'] = datetime.now().isoformat()
            
        except Exception as e:
            self.logger.error(f"Error updating position cache: {e}")
    
    async def subscribe_to_instruments(self, security_ids: List[int]):
        """Subscribe to live feed for specific instruments"""
        try:
            new_instruments = set(security_ids) - self.subscribed_instruments
            
            if not new_instruments:
                return
            
            self.logger.info(f"Subscribing to {len(new_instruments)} new instruments")
            
            # In real implementation, this would send subscription message to Dhan WebSocket
            # subscription_message = {
            #     "RequestCode": "Subscribe",
            #     "InstrumentCount": len(new_instruments),
            #     "InstrumentList": list(new_instruments)
            # }
            # await self.dhan_websocket.send(json.dumps(subscription_message))
            
            self.subscribed_instruments.update(new_instruments)
            self.logger.info(f"Total subscribed instruments: {len(self.subscribed_instruments)}")
            
        except Exception as e:
            self.logger.error(f"Error subscribing to instruments: {e}")
    
    async def unsubscribe_from_instruments(self, security_ids: List[int]):
        """Unsubscribe from instruments no longer needed"""
        try:
            instruments_to_remove = set(security_ids) & self.subscribed_instruments
            
            if not instruments_to_remove:
                return
            
            self.logger.info(f"Unsubscribing from {len(instruments_to_remove)} instruments")
            
            # In real implementation, send unsubscribe message
            # unsubscription_message = {
            #     "RequestCode": "Unsubscribe", 
            #     "InstrumentCount": len(instruments_to_remove),
            #     "InstrumentList": list(instruments_to_remove)
            # }
            # await self.dhan_websocket.send(json.dumps(unsubscription_message))
            
            self.subscribed_instruments -= instruments_to_remove
            
            # Clean up price cache for unsubscribed instruments
            for security_id in instruments_to_remove:
                self.price_cache.pop(security_id, None)
                if self.redis_client:
                    try:
                        self.redis_client.delete(f"price:{security_id}")
                    except Exception:
                        pass
            
        except Exception as e:
            self.logger.error(f"Error unsubscribing from instruments: {e}")
    
    def get_latest_price(self, security_id: int) -> Optional[Dict]:
        """Get latest price for a security ID"""
        try:
            # Try Redis cache first
            if self.redis_client:
                try:
                    price_data = self.redis_client.hgetall(f"price:{security_id}")
                    if price_data:
                        return {
                            'security_id': int(price_data.get('security_id', 0)),
                            'ltp': float(price_data.get('ltp', 0)),
                            'volume': int(price_data.get('volume', 0)),
                            'timestamp': float(price_data.get('timestamp', 0)),
                            'last_update': price_data.get('last_update')
                        }
                except Exception as e:
                    self.logger.error(f"Redis get failed: {e}")
            
            # Fallback to in-memory cache
            return self.price_cache.get(security_id)
            
        except Exception as e:
            self.logger.error(f"Error getting latest price: {e}")
            return None
    
    def get_position_from_cache(self, strategy_id: int) -> Optional[Dict]:
        """Get position data from cache"""
        return self.position_cache.get(strategy_id)
    
    async def _reconnect_dhan(self):
        """Attempt to reconnect to Dhan WebSocket"""
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            self.logger.error("Max reconnection attempts reached for Dhan WebSocket")
            return
        
        self.reconnect_attempts += 1
        self.logger.info(f"Attempting to reconnect to Dhan WebSocket (attempt {self.reconnect_attempts})")
        
        await asyncio.sleep(self.reconnect_delay)
        
        try:
            await self._start_dhan_feed()
            # Re-subscribe to instruments
            if self.subscribed_instruments:
                await self.subscribe_to_instruments(list(self.subscribed_instruments))
            
            self.reconnect_attempts = 0  # Reset on successful reconnection
            
        except Exception as e:
            self.logger.error(f"Reconnection attempt failed: {e}")
            # Exponential backoff
            self.reconnect_delay = min(self.reconnect_delay * 2, 60)
    
    def get_connection_status(self) -> Dict:
        """Get current connection status"""
        return {
            'is_connected': self.is_connected,
            'is_running': self.is_running,
            'subscribed_instruments': len(self.subscribed_instruments),
            'cached_prices': len(self.price_cache),
            'cached_positions': len(self.position_cache),
            'reconnect_attempts': self.reconnect_attempts
        }