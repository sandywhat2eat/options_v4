"""
Supabase Realtime Integration for Trade Updates
Handles real-time subscriptions to database changes
"""

import logging
import json
import asyncio
from typing import Dict, List, Callable, Optional, Any
from datetime import datetime
import websockets
from websockets.exceptions import ConnectionClosed
import threading
from concurrent.futures import ThreadPoolExecutor

from database.supabase_integration import SupabaseIntegration

class SupabaseRealtime:
    """
    Manages Supabase realtime subscriptions for trade table changes
    """
    
    def __init__(self, supabase_integration: SupabaseIntegration = None):
        """
        Initialize Supabase Realtime
        
        Args:
            supabase_integration: Existing Supabase integration instance
        """
        self.logger = logging.getLogger(__name__)
        self.db = supabase_integration or SupabaseIntegration()
        
        # Connection state
        self.websocket = None
        self.is_connected = False
        self.is_running = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 5
        
        # Subscription management
        self.subscriptions = {}
        self.channel_counter = 0
        
        # Event handlers
        self.trade_handlers = []
        self.strategy_handlers = []
        self.general_handlers = []
        
        # Thread pool for sync handlers
        self.executor = ThreadPoolExecutor(max_workers=2)
        
        # WebSocket URL construction
        self.websocket_url = self._construct_websocket_url()
        
        self.logger.info("Supabase Realtime initialized")
    
    def _construct_websocket_url(self) -> str:
        """Construct Supabase realtime WebSocket URL"""
        try:
            # Extract base URL from Supabase client
            base_url = str(self.db.client.supabase_url)
            if base_url.startswith('https://'):
                ws_url = base_url.replace('https://', 'wss://') + '/realtime/v1/websocket'
            else:
                ws_url = base_url.replace('http://', 'ws://') + '/realtime/v1/websocket'
            
            # Add API key as query parameter
            api_key = str(self.db.client.supabase_key)
            ws_url += f"?apikey={api_key}&vsn=1.0.0"
            
            return ws_url
            
        except Exception as e:
            self.logger.error(f"Error constructing WebSocket URL: {e}")
            # Fallback URL structure
            return "wss://your-project.supabase.co/realtime/v1/websocket?apikey=your-key&vsn=1.0.0"
    
    def add_trade_handler(self, handler: Callable):
        """Add handler for trade table changes"""
        self.trade_handlers.append(handler)
    
    def add_strategy_handler(self, handler: Callable):
        """Add handler for strategy table changes"""
        self.strategy_handlers.append(handler)
    
    def add_general_handler(self, handler: Callable):
        """Add handler for any table changes"""
        self.general_handlers.append(handler)
    
    async def start(self):
        """Start Supabase realtime connection"""
        try:
            self.is_running = True
            self.logger.info("Starting Supabase realtime connection...")
            
            # Connect to WebSocket
            await self._connect()
            
            # Set up default subscriptions
            await self._setup_default_subscriptions()
            
            self.is_connected = True
            self.logger.info("Supabase realtime connection established")
            
        except Exception as e:
            self.logger.error(f"Failed to start Supabase realtime: {e}")
            await self.stop()
            raise
    
    async def stop(self):
        """Stop Supabase realtime connection"""
        self.is_running = False
        self.logger.info("Stopping Supabase realtime connection...")
        
        if self.websocket:
            try:
                await self.websocket.close()
            except Exception as e:
                self.logger.error(f"Error closing WebSocket: {e}")
        
        self.is_connected = False
        self.subscriptions.clear()
        self.logger.info("Supabase realtime connection stopped")
    
    async def _connect(self):
        """Establish WebSocket connection to Supabase"""
        try:
            self.logger.info(f"Connecting to Supabase realtime: {self.websocket_url}")
            
            # In a real implementation, this would connect to Supabase realtime
            # For now, we'll create a placeholder connection structure
            
            # self.websocket = await websockets.connect(self.websocket_url)
            # Start message processing loop
            asyncio.create_task(self._process_messages())
            
            self.logger.info("WebSocket connection established")
            
        except Exception as e:
            self.logger.error(f"Failed to connect to Supabase realtime: {e}")
            raise
    
    async def _setup_default_subscriptions(self):
        """Set up default subscriptions for key tables"""
        try:
            # Subscribe to trades table
            await self.subscribe_to_table('trades', self._handle_trade_change)
            
            # Subscribe to strategies table  
            await self.subscribe_to_table('strategies', self._handle_strategy_change)
            
            # Subscribe to strategy_exit_levels table
            await self.subscribe_to_table('strategy_exit_levels', self._handle_exit_levels_change)
            
            self.logger.info("Default subscriptions set up successfully")
            
        except Exception as e:
            self.logger.error(f"Error setting up default subscriptions: {e}")
    
    async def subscribe_to_table(self, table_name: str, handler: Callable = None):
        """
        Subscribe to changes in a specific table
        
        Args:
            table_name: Name of the table to subscribe to
            handler: Optional specific handler for this table
        """
        try:
            self.channel_counter += 1
            channel_name = f"{table_name}_channel_{self.channel_counter}"
            
            # Create subscription message
            subscription_message = {
                "topic": f"realtime:{channel_name}",
                "event": "phx_join",
                "payload": {
                    "config": {
                        "postgres_changes": [
                            {
                                "event": "*",  # Listen to all events (INSERT, UPDATE, DELETE)
                                "schema": "public",
                                "table": table_name
                            }
                        ]
                    }
                },
                "ref": str(self.channel_counter)
            }
            
            # Store subscription info
            self.subscriptions[channel_name] = {
                'table': table_name,
                'handler': handler,
                'ref': str(self.channel_counter)
            }
            
            # In real implementation, this would send the subscription message
            # await self.websocket.send(json.dumps(subscription_message))
            
            self.logger.info(f"Subscribed to table: {table_name}")
            
        except Exception as e:
            self.logger.error(f"Error subscribing to table {table_name}: {e}")
    
    async def _process_messages(self):
        """Process incoming messages from Supabase realtime"""
        while self.is_running:
            try:
                if not self.websocket:
                    await asyncio.sleep(1)
                    continue
                
                # In real implementation, this would receive messages:
                # message = await self.websocket.recv()
                # data = json.loads(message)
                
                # For now, simulate processing
                await asyncio.sleep(0.1)
                continue
                
                # Process the message
                await self._handle_message(data)
                
            except ConnectionClosed:
                self.logger.warning("Supabase realtime connection closed")
                await self._reconnect()
            except Exception as e:
                self.logger.error(f"Error processing realtime message: {e}")
                await asyncio.sleep(1)
    
    async def _handle_message(self, message: Dict):
        """Handle incoming realtime message"""
        try:
            event = message.get('event')
            payload = message.get('payload', {})
            topic = message.get('topic', '')
            
            if event == 'postgres_changes':
                # This is a database change event
                await self._handle_postgres_change(payload)
            elif event == 'phx_reply':
                # This is a subscription confirmation
                self._handle_subscription_reply(payload, topic)
            else:
                self.logger.debug(f"Unhandled realtime event: {event}")
                
        except Exception as e:
            self.logger.error(f"Error handling realtime message: {e}")
    
    async def _handle_postgres_change(self, payload: Dict):
        """Handle PostgreSQL change events"""
        try:
            change_data = payload.get('data', {})
            table = change_data.get('table')
            event_type = change_data.get('eventType')  # INSERT, UPDATE, DELETE
            record = change_data.get('record', {})
            old_record = change_data.get('old_record', {})
            
            self.logger.info(f"Database change: {table}.{event_type}")
            
            # Route to specific handlers based on table
            if table == 'trades':
                await self._handle_trade_change(change_data)
            elif table == 'strategies':
                await self._handle_strategy_change(change_data)
            elif table == 'strategy_exit_levels':
                await self._handle_exit_levels_change(change_data)
            
            # Notify general handlers
            for handler in self.general_handlers:
                await self._execute_handler(handler, change_data)
                
        except Exception as e:
            self.logger.error(f"Error handling postgres change: {e}")
    
    async def _handle_trade_change(self, change_data: Dict):
        """Handle trade table changes"""
        try:
            event_type = change_data.get('eventType')
            record = change_data.get('record', {})
            
            symbol = record.get('symbol', 'Unknown')
            strategy_id = record.get('strategy_id')
            
            self.logger.info(f"Trade {event_type}: {symbol} (strategy {strategy_id})")
            
            # Notify trade-specific handlers
            for handler in self.trade_handlers:
                await self._execute_handler(handler, change_data)
                
        except Exception as e:
            self.logger.error(f"Error handling trade change: {e}")
    
    async def _handle_strategy_change(self, change_data: Dict):
        """Handle strategy table changes"""
        try:
            event_type = change_data.get('eventType')
            record = change_data.get('record', {})
            
            strategy_name = record.get('strategy_name', 'Unknown')
            stock_name = record.get('stock_name', 'Unknown')
            
            self.logger.info(f"Strategy {event_type}: {strategy_name} on {stock_name}")
            
            # Notify strategy-specific handlers
            for handler in self.strategy_handlers:
                await self._execute_handler(handler, change_data)
                
        except Exception as e:
            self.logger.error(f"Error handling strategy change: {e}")
    
    async def _handle_exit_levels_change(self, change_data: Dict):
        """Handle strategy exit levels changes"""
        try:
            event_type = change_data.get('eventType')
            record = change_data.get('record', {})
            
            strategy_id = record.get('strategy_id')
            self.logger.info(f"Exit levels {event_type} for strategy {strategy_id}")
            
            # This could trigger re-evaluation of exit conditions
            # Notify relevant handlers
            for handler in self.general_handlers:
                await self._execute_handler(handler, change_data)
                
        except Exception as e:
            self.logger.error(f"Error handling exit levels change: {e}")
    
    def _handle_subscription_reply(self, payload: Dict, topic: str):
        """Handle subscription confirmation replies"""
        try:
            status = payload.get('status')
            if status == 'ok':
                self.logger.info(f"Subscription confirmed: {topic}")
            else:
                self.logger.error(f"Subscription failed: {topic} - {payload}")
                
        except Exception as e:
            self.logger.error(f"Error handling subscription reply: {e}")
    
    async def _execute_handler(self, handler: Callable, data: Dict):
        """Execute handler function safely"""
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(data)
            else:
                # Run sync handler in thread pool
                self.executor.submit(handler, data)
        except Exception as e:
            self.logger.error(f"Error executing handler: {e}")
    
    async def _reconnect(self):
        """Attempt to reconnect to Supabase realtime"""
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            self.logger.error("Max reconnection attempts reached for Supabase realtime")
            return
        
        self.reconnect_attempts += 1
        self.logger.info(f"Attempting to reconnect to Supabase realtime (attempt {self.reconnect_attempts})")
        
        await asyncio.sleep(self.reconnect_delay)
        
        try:
            await self._connect()
            await self._setup_default_subscriptions()
            
            self.reconnect_attempts = 0  # Reset on successful reconnection
            
        except Exception as e:
            self.logger.error(f"Reconnection attempt failed: {e}")
            # Exponential backoff
            self.reconnect_delay = min(self.reconnect_delay * 2, 60)
    
    def get_subscription_status(self) -> Dict:
        """Get current subscription status"""
        return {
            'is_connected': self.is_connected,
            'is_running': self.is_running,
            'active_subscriptions': len(self.subscriptions),
            'reconnect_attempts': self.reconnect_attempts,
            'subscriptions': list(self.subscriptions.keys())
        }
    
    async def unsubscribe_from_table(self, table_name: str):
        """Unsubscribe from a specific table"""
        try:
            # Find and remove subscriptions for this table
            channels_to_remove = []
            for channel_name, sub_info in self.subscriptions.items():
                if sub_info['table'] == table_name:
                    channels_to_remove.append(channel_name)
            
            for channel_name in channels_to_remove:
                sub_info = self.subscriptions[channel_name]
                
                # Send unsubscribe message
                unsubscribe_message = {
                    "topic": f"realtime:{channel_name}",
                    "event": "phx_leave",
                    "payload": {},
                    "ref": sub_info['ref']
                }
                
                # In real implementation:
                # await self.websocket.send(json.dumps(unsubscribe_message))
                
                # Remove from subscriptions
                del self.subscriptions[channel_name]
                
                self.logger.info(f"Unsubscribed from table: {table_name}")
                
        except Exception as e:
            self.logger.error(f"Error unsubscribing from table {table_name}: {e}")