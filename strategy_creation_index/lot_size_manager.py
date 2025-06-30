"""
Lot Size Manager for INDEX Options V4 System
Handles INDEX-ONLY lot size fetching from Supabase with BS suffix isolation
INDEX VERSION - NO STOCKS
"""

import logging
from typing import Optional
from datetime import datetime
import sys
import os

# Add parent directory for MCP imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

logger = logging.getLogger(__name__)

class LotSizeManager:
    """
    Manages INDEX-ONLY lot size fetching from Supabase lots table
    
    CRITICAL: BS suffix ONLY used for lots table queries
    All other database operations use clean index names
    INDEX ONLY - NO STOCKS
    """
    
    def __init__(self):
        self.cache = {}  # Cache lot sizes to avoid repeated queries
        self.default_lot_size = 100  # Safe default
        
        # Initialize Supabase client
        try:
            from supabase import create_client
            import os
            from dotenv import load_dotenv
            load_dotenv()
            
            self.supabase = create_client(
                os.getenv('NEXT_PUBLIC_SUPABASE_URL'),
                os.getenv('NEXT_PUBLIC_SUPABASE_ANON_KEY')
            )
            self.db_available = True
            logger.info("LotSizeManager: Supabase client initialized")
        except Exception as e:
            logger.error(f"LotSizeManager: Failed to initialize Supabase client: {e}")
            self.supabase = None
            self.db_available = False
        
        # Current month mapping
        self.month_mapping = {
            1: 'jan', 2: 'feb', 3: 'mar', 4: 'apr',
            5: 'may', 6: 'jun', 7: 'jul', 8: 'aug', 
            9: 'sep', 10: 'oct', 11: 'nov', 12: 'dec'
        }
        
        # Index name mapping from option_chain_data to lots table
        self.index_name_mapping = {
            'NIFTY 50': 'NIFTY',
            'BANK NIFTY': 'BANKNIFTY',
            'NIFTY FIN SERVICE': 'FINNIFTY',
            'NIFTY IT': 'NIFTYIT',  # Need to verify this mapping
            'NIFTY MIDCAP 50': 'MIDCPNIFTY'
        }
    
    def get_current_lot_size(self, symbol: str) -> int:
        """
        Get current month's lot size for an INDEX from database
        
        Args:
            symbol: Index name (e.g., 'NIFTY 50', 'BANK NIFTY') - INDEX ONLY
            
        Returns:
            Lot size for current month
            
        IMPORTANT: Only adds BS suffix for lots table query
        """
        try:
            # Check cache first
            if symbol in self.cache:
                return self.cache[symbol]
            
            # If database not available, use fallback
            if not self.db_available:
                return self._get_fallback_lot_size(symbol)
            
            # Get current month column
            current_month = self._get_current_month_column()
            
            # INDEX-ONLY: Handle index name mapping
            if symbol in self.index_name_mapping:
                # Convert index name from option_chain_data format to lots table format
                mapped_symbol = self.index_name_mapping[symbol]
                lots_symbol = f'{mapped_symbol}BS'
                logger.info(f"Mapping index {symbol} to {lots_symbol} for lots table")
            else:
                # Unknown index - raise error since we only work with indexes
                logger.error(f"Unknown index symbol: {symbol}. Index-only system requires known index mappings.")
                return self._get_fallback_lot_size(symbol)
            
            # Query lots table for this symbol
            response = self.supabase.table('lots').select(f'symbol,{current_month}').eq('symbol', lots_symbol).execute()
            
            if response.data and len(response.data) > 0:
                lot_size = response.data[0].get(current_month)
                if lot_size is not None:
                    lot_size = int(lot_size)
                    self.cache[symbol] = lot_size
                    logger.info(f"Database lot size for {symbol}: {lot_size}")
                    return lot_size
                else:
                    logger.warning(f"Null lot size for {symbol} in month {current_month}")
            else:
                logger.warning(f"No lot size found for {lots_symbol} in lots table")
            
            # Fallback to default if not found
            fallback_size = self._get_fallback_lot_size(symbol)
            self.cache[symbol] = fallback_size
            logger.info(f"Fallback lot size for {symbol}: {fallback_size}")
            return fallback_size
                
        except Exception as e:
            logger.error(f"Error fetching lot size for {symbol}: {e}")
            fallback_size = self._get_fallback_lot_size(symbol)
            self.cache[symbol] = fallback_size
            return fallback_size
    
    def _get_current_month_column(self) -> str:
        """Get current month column name for lots table"""
        try:
            current_month_num = datetime.now().month
            return self.month_mapping.get(current_month_num, 'jun')  # Default to jun
        except Exception as e:
            logger.error(f"Error getting current month: {e}")
            return 'jun'  # Safe default
    
    def get_clean_symbol(self, symbol: str) -> str:
        """
        Returns clean symbol for ALL other database operations
        
        Args:
            symbol: Symbol name
            
        Returns:
            Clean symbol (no BS suffix) for use with all other tables
        """
        return symbol  # Always return as-is for other tables
    
    def clear_cache(self):
        """Clear lot size cache"""
        self.cache.clear()
        logger.info("Lot size cache cleared")
    
    def get_all_lot_sizes(self, symbols: list) -> dict:
        """
        Get lot sizes for multiple INDEX symbols efficiently
        
        Args:
            symbols: List of index names - INDEX ONLY
            
        Returns:
            Dictionary mapping index symbols to lot sizes
        """
        lot_sizes = {}
        
        for symbol in symbols:
            lot_sizes[symbol] = self.get_current_lot_size(symbol)
        
        return lot_sizes
    
    def _get_fallback_lot_size(self, symbol: str) -> int:
        """
        Get fallback lot size for INDEX symbols not found in database
        
        Args:
            symbol: Index name - INDEX ONLY
            
        Returns:
            Fallback lot size based on known index values
        """
        # Known INDEX-ONLY lot sizes (as backup)
        known_lot_sizes = {
            # Index lot sizes (mapped names for lots table)
            'BANKNIFTY': 35,
            'NIFTY': 75,
            'FINNIFTY': 65,
            'MIDCPNIFTY': 140,
            'NIFTYIT': 200,
            # Index lot sizes (original names from option_chain_data)
            'NIFTY 50': 75,
            'BANK NIFTY': 35,
            'NIFTY FIN SERVICE': 65,
            'NIFTY IT': 200,
            'NIFTY MIDCAP 50': 140,
        }
        
        return known_lot_sizes.get(symbol, self.default_lot_size)

    def validate_symbol_exists(self, symbol: str) -> bool:
        """
        Check if INDEX symbol exists in database or fallback values
        
        Args:
            symbol: Index name - INDEX ONLY
            
        Returns:
            True if index symbol has a known lot size
        """
        if not self.db_available:
            # Check INDEX symbols only
            fallback_indexes = ['BANKNIFTY', 'NIFTY', 'FINNIFTY', 'MIDCPNIFTY', 'NIFTYIT',
                              'NIFTY 50', 'BANK NIFTY', 'NIFTY FIN SERVICE', 'NIFTY IT', 'NIFTY MIDCAP 50']
            return symbol in fallback_indexes
        
        try:
            # INDEX-ONLY: Handle index name mapping
            if symbol in self.index_name_mapping:
                mapped_symbol = self.index_name_mapping[symbol]
                lots_symbol = f'{mapped_symbol}BS'
            else:
                # Unknown index
                logger.error(f"Unknown index symbol: {symbol}. Index-only system.")
                return False
                
            response = self.supabase.table('lots').select('symbol').eq('symbol', lots_symbol).execute()
            return bool(response.data and len(response.data) > 0)
        except Exception as e:
            logger.error(f"Error validating index existence for {symbol}: {e}")
            return False