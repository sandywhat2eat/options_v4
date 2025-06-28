"""
Position Cache Manager for Real-time Trading
Manages in-memory position cache with database synchronization
"""

import asyncio
import logging
import json
import time
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor
import threading

from database.supabase_integration import SupabaseIntegration

@dataclass
class PositionLeg:
    """Represents a single leg of a position"""
    trade_id: int
    security_id: int
    action: str  # BUY/SELL
    type: str   # CE/PE
    strike_price: float
    quantity: int
    entry_price: float
    order_id: str
    expiry_date: str
    current_price: float = 0.0
    last_price_update: str = None

@dataclass
class CachedPosition:
    """Represents a cached position with real-time updates"""
    strategy_id: int
    symbol: str
    strategy_name: str
    legs: List[PositionLeg]
    total_quantity: int
    net_premium: float
    entry_time: str
    last_update: str
    status: str = 'open'  # open, closing, closed
    
    # Real-time calculated fields
    current_value: float = 0.0
    total_pnl: float = 0.0
    total_pnl_pct: float = 0.0
    last_pnl_update: str = None
    
    # Exit tracking
    exit_conditions_checked: str = None
    last_evaluation: Dict = None

class PositionCacheManager:
    """
    Manages in-memory position cache with real-time updates and database sync
    """
    
    def __init__(self, sync_interval_seconds=60):
        """
        Initialize Position Cache Manager
        
        Args:
            sync_interval_seconds: How often to sync with database (default 60s)
        """
        self.logger = logging.getLogger(__name__)
        
        # Database integration
        self.db = SupabaseIntegration()
        
        # Cache storage
        self.positions_cache: Dict[int, CachedPosition] = {}  # strategy_id -> position
        self.security_to_positions: Dict[int, Set[int]] = {}  # security_id -> set(strategy_ids)
        
        # Synchronization
        self.sync_interval = sync_interval_seconds
        self.last_db_sync = 0
        self.sync_lock = threading.RLock()
        
        # Background tasks
        self.sync_task = None
        self.is_running = False
        
        # Thread pool for database operations
        self.executor = ThreadPoolExecutor(max_workers=2)
        
        # Statistics
        self.stats = {
            'cache_hits': 0,
            'cache_misses': 0,
            'db_syncs': 0,
            'price_updates': 0,
            'positions_tracked': 0
        }
        
        self.logger.info("Position Cache Manager initialized")
    
    async def start(self):
        """Start the cache manager and background sync"""
        try:
            self.is_running = True
            
            # Load initial positions from database
            await self.refresh_from_database()
            
            # Start background sync task
            self.sync_task = asyncio.create_task(self._background_sync_loop())
            
            self.logger.info(f"Position cache started with {len(self.positions_cache)} positions")
            
        except Exception as e:
            self.logger.error(f"Failed to start position cache: {e}")
            raise
    
    async def stop(self):
        """Stop the cache manager"""
        self.is_running = False
        
        if self.sync_task:
            self.sync_task.cancel()
            try:
                await self.sync_task
            except asyncio.CancelledError:
                pass
        
        # Final sync before shutdown
        await self.sync_to_database()
        
        self.logger.info("Position cache manager stopped")
    
    async def refresh_from_database(self):
        """Refresh cache from database"""
        try:
            self.logger.info("Refreshing position cache from database...")
            
            # Clear current cache
            with self.sync_lock:
                self.positions_cache.clear()
                self.security_to_positions.clear()
            
            # Fetch open trades from database
            response = self.db.client.table('trades').select('*').eq(
                'order_status', 'open'
            ).order('timestamp', desc=False).execute()
            
            if not response.data:
                self.logger.info("No open trades found in database")
                return
            
            # Group trades by strategy_id
            strategy_trades = {}
            for trade in response.data:
                strategy_id = trade.get('strategy_id')
                if not strategy_id:
                    continue
                
                if strategy_id not in strategy_trades:
                    strategy_trades[strategy_id] = []
                strategy_trades[strategy_id].append(trade)
            
            # Create cached positions
            for strategy_id, trades in strategy_trades.items():
                await self._create_cached_position(strategy_id, trades)
            
            self.stats['positions_tracked'] = len(self.positions_cache)
            self.logger.info(f"Loaded {len(self.positions_cache)} positions into cache")
            
        except Exception as e:
            self.logger.error(f"Error refreshing from database: {e}")
    
    async def _create_cached_position(self, strategy_id: int, trades: List[Dict]):
        """Create a cached position from trade data"""
        try:
            if not trades:
                return
            
            # Get strategy info from first trade
            first_trade = trades[0]
            symbol = first_trade.get('symbol', f'STRATEGY_{strategy_id}')
            strategy_name = first_trade.get('strategy', 'Unknown')
            
            # Create position legs
            legs = []
            total_quantity = 0
            net_premium = 0.0
            
            for trade in trades:
                leg = PositionLeg(
                    trade_id=trade.get('new_id', trade.get('id')),
                    security_id=trade.get('security_id'),
                    action=trade.get('action'),
                    type=trade.get('type'),
                    strike_price=trade.get('strike_price', 0),
                    quantity=trade.get('quantity', 0),
                    entry_price=trade.get('price', 0),
                    order_id=trade.get('order_id', ''),
                    expiry_date=trade.get('expiry_date', ''),
                    current_price=trade.get('price', 0),  # Will be updated with real-time prices
                    last_price_update=datetime.now().isoformat()
                )
                
                legs.append(leg)
                
                # Update totals
                total_quantity = max(total_quantity, leg.quantity)
                
                # Calculate net premium (positive for credit, negative for debit)
                if leg.action == 'SELL':
                    net_premium += leg.entry_price * leg.quantity
                else:
                    net_premium -= leg.entry_price * leg.quantity
                
                # Update security mapping
                security_id = leg.security_id
                if security_id:
                    if security_id not in self.security_to_positions:
                        self.security_to_positions[security_id] = set()
                    self.security_to_positions[security_id].add(strategy_id)
            
            # Create cached position
            position = CachedPosition(
                strategy_id=strategy_id,
                symbol=symbol,
                strategy_name=strategy_name,
                legs=legs,
                total_quantity=total_quantity,
                net_premium=net_premium,
                entry_time=first_trade.get('timestamp', datetime.now().isoformat()),
                last_update=datetime.now().isoformat(),
                status='open'
            )
            
            # Store in cache
            with self.sync_lock:
                self.positions_cache[strategy_id] = position
            
            self.logger.debug(f"Cached position: {symbol} (strategy {strategy_id})")
            
        except Exception as e:
            self.logger.error(f"Error creating cached position: {e}")
    
    def get_position(self, strategy_id: int) -> Optional[CachedPosition]:
        """Get a position from cache"""
        try:
            with self.sync_lock:
                position = self.positions_cache.get(strategy_id)
                
                if position:
                    self.stats['cache_hits'] += 1
                    return position
                else:
                    self.stats['cache_misses'] += 1
                    return None
                    
        except Exception as e:
            self.logger.error(f"Error getting position from cache: {e}")
            return None
    
    def get_all_positions(self) -> List[CachedPosition]:
        """Get all cached positions"""
        try:
            with self.sync_lock:
                return list(self.positions_cache.values())
        except Exception as e:
            self.logger.error(f"Error getting all positions: {e}")
            return []
    
    def get_positions_for_security(self, security_id: int) -> List[CachedPosition]:
        """Get all positions that include a specific security"""
        try:
            with self.sync_lock:
                strategy_ids = self.security_to_positions.get(security_id, set())
                positions = []
                
                for strategy_id in strategy_ids:
                    position = self.positions_cache.get(strategy_id)
                    if position:
                        positions.append(position)
                
                return positions
                
        except Exception as e:
            self.logger.error(f"Error getting positions for security: {e}")
            return []
    
    async def update_price(self, security_id: int, price: float, timestamp: str = None):
        """Update price for a security across all affected positions"""
        try:
            if timestamp is None:
                timestamp = datetime.now().isoformat()
            
            affected_positions = self.get_positions_for_security(security_id)
            
            with self.sync_lock:
                for position in affected_positions:
                    # Update leg prices
                    for leg in position.legs:
                        if leg.security_id == security_id:
                            leg.current_price = price
                            leg.last_price_update = timestamp
                    
                    # Recalculate position P&L
                    self._calculate_position_pnl(position)
                    position.last_update = timestamp
            
            self.stats['price_updates'] += 1
            
            if affected_positions:
                self.logger.debug(f"Updated price for security {security_id}: ₹{price} "
                                f"(affected {len(affected_positions)} positions)")
            
        except Exception as e:
            self.logger.error(f"Error updating price: {e}")
    
    def _calculate_position_pnl(self, position: CachedPosition):
        """Calculate P&L for a position"""
        try:
            current_value = 0.0
            entry_value = position.net_premium
            
            for leg in position.legs:
                leg_value = leg.current_price * leg.quantity
                
                if leg.action == 'SELL':
                    # Short position: profit when price goes down
                    current_value += leg_value
                else:
                    # Long position: profit when price goes up
                    current_value -= leg_value
            
            # Total P&L (current value minus what we paid/received)
            position.current_value = current_value
            position.total_pnl = current_value - entry_value
            
            # P&L percentage
            if abs(entry_value) > 0:
                position.total_pnl_pct = (position.total_pnl / abs(entry_value)) * 100
            else:
                position.total_pnl_pct = 0.0
            
            position.last_pnl_update = datetime.now().isoformat()
            
        except Exception as e:
            self.logger.error(f"Error calculating P&L: {e}")
    
    async def mark_position_closing(self, strategy_id: int):
        """Mark a position as closing (exit in progress)"""
        try:
            with self.sync_lock:
                position = self.positions_cache.get(strategy_id)
                if position:
                    position.status = 'closing'
                    position.last_update = datetime.now().isoformat()
                    self.logger.info(f"Marked position {position.symbol} as closing")
                    
        except Exception as e:
            self.logger.error(f"Error marking position as closing: {e}")
    
    async def mark_position_closed(self, strategy_id: int):
        """Mark a position as closed and remove from active cache"""
        try:
            with self.sync_lock:
                position = self.positions_cache.get(strategy_id)
                if position:
                    position.status = 'closed'
                    position.last_update = datetime.now().isoformat()
                    
                    # Remove from security mappings
                    for leg in position.legs:
                        if leg.security_id in self.security_to_positions:
                            self.security_to_positions[leg.security_id].discard(strategy_id)
                            if not self.security_to_positions[leg.security_id]:
                                del self.security_to_positions[leg.security_id]
                    
                    # Remove from main cache
                    del self.positions_cache[strategy_id]
                    
                    self.logger.info(f"Removed closed position {position.symbol} from cache")
                    
        except Exception as e:
            self.logger.error(f"Error marking position as closed: {e}")
    
    async def update_exit_evaluation(self, strategy_id: int, evaluation: Dict):
        """Update the last exit evaluation for a position"""
        try:
            with self.sync_lock:
                position = self.positions_cache.get(strategy_id)
                if position:
                    position.last_evaluation = evaluation
                    position.exit_conditions_checked = datetime.now().isoformat()
                    position.last_update = datetime.now().isoformat()
                    
        except Exception as e:
            self.logger.error(f"Error updating exit evaluation: {e}")
    
    async def _background_sync_loop(self):
        """Background loop for periodic database synchronization"""
        while self.is_running:
            try:
                await asyncio.sleep(self.sync_interval)
                
                if self.is_running:
                    await self.sync_to_database()
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in background sync loop: {e}")
                await asyncio.sleep(30)  # Wait before retrying
    
    async def sync_to_database(self):
        """Sync position updates back to database"""
        try:
            current_time = time.time()
            
            # Don't sync too frequently
            if current_time - self.last_db_sync < 30:  # Min 30 seconds between syncs
                return
            
            with self.sync_lock:
                positions_to_sync = list(self.positions_cache.values())
            
            if not positions_to_sync:
                return
            
            self.logger.debug(f"Syncing {len(positions_to_sync)} positions to database")
            
            # Update position P&L and status in database
            for position in positions_to_sync:
                try:
                    # You could update a positions summary table here
                    # For now, we'll just log the sync
                    pass
                    
                except Exception as e:
                    self.logger.error(f"Error syncing position {position.strategy_id}: {e}")
            
            self.last_db_sync = current_time
            self.stats['db_syncs'] += 1
            
            self.logger.debug("Database sync completed")
            
        except Exception as e:
            self.logger.error(f"Error in database sync: {e}")
    
    def get_cache_statistics(self) -> Dict:
        """Get cache performance statistics"""
        with self.sync_lock:
            return {
                'positions_cached': len(self.positions_cache),
                'securities_tracked': len(self.security_to_positions),
                'cache_hits': self.stats['cache_hits'],
                'cache_misses': self.stats['cache_misses'],
                'hit_ratio': self.stats['cache_hits'] / max(1, self.stats['cache_hits'] + self.stats['cache_misses']),
                'db_syncs': self.stats['db_syncs'],
                'price_updates': self.stats['price_updates'],
                'last_sync': self.last_db_sync,
                'is_running': self.is_running
            }
    
    def export_positions_to_dict(self) -> Dict:
        """Export all cached positions to dictionary format"""
        try:
            with self.sync_lock:
                return {
                    strategy_id: {
                        'position': asdict(position),
                        'export_time': datetime.now().isoformat()
                    }
                    for strategy_id, position in self.positions_cache.items()
                }
        except Exception as e:
            self.logger.error(f"Error exporting positions: {e}")
            return {}

# Utility functions for integration
async def create_position_cache_manager(sync_interval=60) -> PositionCacheManager:
    """Create and start a position cache manager"""
    manager = PositionCacheManager(sync_interval_seconds=sync_interval)
    await manager.start()
    return manager

def get_position_summary(position: CachedPosition) -> Dict:
    """Get a summary of a cached position"""
    return {
        'strategy_id': position.strategy_id,
        'symbol': position.symbol,
        'strategy_name': position.strategy_name,
        'legs_count': len(position.legs),
        'total_quantity': position.total_quantity,
        'net_premium': position.net_premium,
        'current_value': position.current_value,
        'total_pnl': position.total_pnl,
        'total_pnl_pct': position.total_pnl_pct,
        'status': position.status,
        'last_update': position.last_update,
        'last_pnl_update': position.last_pnl_update
    }