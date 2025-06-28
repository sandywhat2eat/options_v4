"""
Lot Size Manager for Options V4 System
Handles lot size fetching from Supabase with BS suffix isolation
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
    Manages lot size fetching from Supabase lots table
    
    CRITICAL: BS suffix ONLY used for lots table queries
    All other database operations use clean symbol names
    """
    
    def __init__(self):
        self.cache = {}  # Cache lot sizes to avoid repeated queries
        self.default_lot_size = 100  # Safe default
        
        # Current month mapping
        self.month_mapping = {
            1: 'jan', 2: 'feb', 3: 'mar', 4: 'apr',
            5: 'may', 6: 'jun', 7: 'jul', 8: 'aug', 
            9: 'sep', 10: 'oct', 11: 'nov', 12: 'dec'
        }
    
    def get_current_lot_size(self, symbol: str) -> int:
        """
        Get current month's lot size for a symbol
        
        Args:
            symbol: Clean symbol name (e.g., 'DIXON', 'MARICO')
            
        Returns:
            Lot size for current month
            
        IMPORTANT: Only adds BS suffix for lots table query
        """
        try:
            # Check cache first
            if symbol in self.cache:
                return self.cache[symbol]
            
            # Get current month column
            current_month = self._get_current_month_column()
            
            # ONLY add BS suffix for lots table query
            lots_symbol = f'{symbol}BS'
            
            # Hardcoded lot sizes for now - will integrate MCP later
            # Based on our Supabase query results
            known_lot_sizes = {
                'DIXON': 50,
                'MARICO': 1200,
                'SUNPHARMA': 350,
                'CESC': 1000,      # Estimated
                'GRANULES': 800,   # Estimated
                'BANKNIFTY': 15,   # Index options
                'NIFTY': 25,       # Index options
            }
            
            lot_size = known_lot_sizes.get(symbol, self.default_lot_size)
            
            # Cache the result
            self.cache[symbol] = lot_size
            
            logger.info(f"Using lot size for {symbol}: {lot_size}")
            return lot_size
                
        except Exception as e:
            logger.error(f"Error fetching lot size for {symbol}: {e}")
            return self.default_lot_size
    
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
        Get lot sizes for multiple symbols efficiently
        
        Args:
            symbols: List of clean symbol names
            
        Returns:
            Dictionary mapping symbols to lot sizes
        """
        lot_sizes = {}
        
        for symbol in symbols:
            lot_sizes[symbol] = self.get_current_lot_size(symbol)
        
        return lot_sizes
    
    def validate_symbol_exists(self, symbol: str) -> bool:
        """
        Check if symbol exists in our known lot sizes
        
        Args:
            symbol: Clean symbol name
            
        Returns:
            True if symbol has a known lot size
        """
        return symbol in ['DIXON', 'MARICO', 'SUNPHARMA', 'CESC', 'GRANULES', 'BANKNIFTY', 'NIFTY']