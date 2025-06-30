"""
Parallel processor for concurrent symbol analysis
"""

import os
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Callable, Any, Optional
from threading import Lock
import time
from datetime import datetime

logger = logging.getLogger(__name__)

class ParallelProcessor:
    """
    Handles parallel processing of symbols with progress tracking
    """
    
    def __init__(self, max_workers: int = 5):
        """
        Initialize parallel processor
        
        Args:
            max_workers: Maximum number of concurrent threads (default: 8)
        """
        self.max_workers = max_workers
        self.progress_lock = Lock()
        self.completed_count = 0
        self.total_count = 0
        self.start_time = None
        
    def process_symbols_parallel(self, 
                               symbols: List[str], 
                               process_func: Callable[[str], Dict],
                               callback_func: Optional[Callable[[str, Dict], None]] = None) -> Dict[str, Dict]:
        """
        Process symbols in parallel using ThreadPoolExecutor
        
        Args:
            symbols: List of symbols to process
            process_func: Function to process each symbol
            callback_func: Optional callback after each symbol completion
            
        Returns:
            Dictionary mapping symbols to their results
        """
        results = {}
        self.total_count = len(symbols)
        self.completed_count = 0
        self.start_time = time.time()
        
        logger.info(f"Starting parallel processing of {self.total_count} symbols with {self.max_workers} workers")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_symbol = {
                executor.submit(process_func, symbol): symbol 
                for symbol in symbols
            }
            
            # Process completed tasks
            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                
                try:
                    result = future.result()
                    results[symbol] = result
                    
                    # Update progress
                    with self.progress_lock:
                        self.completed_count += 1
                        self._log_progress(symbol, result.get('success', False))
                    
                    # Execute callback if provided
                    if callback_func:
                        callback_func(symbol, result)
                        
                except Exception as e:
                    logger.error(f"Error processing {symbol}: {e}")
                    results[symbol] = {
                        'success': False,
                        'reason': f'Processing error: {str(e)}'
                    }
                    
                    with self.progress_lock:
                        self.completed_count += 1
                        self._log_progress(symbol, False)
        
        elapsed_time = time.time() - self.start_time
        logger.info(f"Parallel processing completed in {elapsed_time:.1f} seconds")
        logger.info(f"Average time per symbol: {elapsed_time/self.total_count:.2f} seconds")
        
        return results
    
    def process_in_batches(self,
                          items: List[Any],
                          batch_size: int,
                          process_func: Callable[[List[Any]], Any]) -> List[Any]:
        """
        Process items in batches with parallel execution
        
        Args:
            items: List of items to process
            batch_size: Size of each batch
            process_func: Function to process each batch
            
        Returns:
            Combined results from all batches
        """
        results = []
        batches = [items[i:i + batch_size] for i in range(0, len(items), batch_size)]
        
        logger.info(f"Processing {len(items)} items in {len(batches)} batches of size {batch_size}")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_batch = {
                executor.submit(process_func, batch): i 
                for i, batch in enumerate(batches)
            }
            
            for future in as_completed(future_to_batch):
                batch_index = future_to_batch[future]
                
                try:
                    batch_result = future.result()
                    results.extend(batch_result if isinstance(batch_result, list) else [batch_result])
                    logger.info(f"Completed batch {batch_index + 1}/{len(batches)}")
                    
                except Exception as e:
                    logger.error(f"Error processing batch {batch_index}: {e}")
        
        return results
    
    def _log_progress(self, symbol: str, success: bool):
        """Log progress with ETA calculation"""
        elapsed = time.time() - self.start_time
        avg_time_per_symbol = elapsed / self.completed_count if self.completed_count > 0 else 0
        remaining = self.total_count - self.completed_count
        eta_seconds = remaining * avg_time_per_symbol
        
        status = "✅" if success else "❌"
        progress_pct = (self.completed_count / self.total_count) * 100
        
        eta_str = f"{int(eta_seconds // 60)}m {int(eta_seconds % 60)}s" if eta_seconds > 0 else "calculating..."
        
        logger.info(
            f"{status} [{self.completed_count}/{self.total_count}] {progress_pct:.1f}% - "
            f"{symbol} - ETA: {eta_str}"
        )

class SymbolBatcher:
    """
    Helper class for batching symbols based on characteristics
    """
    
    @staticmethod
    def create_balanced_batches(symbols: List[str], batch_size: int = 10) -> List[List[str]]:
        """
        Create balanced batches of symbols
        
        Args:
            symbols: List of symbols to batch
            batch_size: Target size for each batch
            
        Returns:
            List of symbol batches
        """
        # Simple batching for now - could be enhanced to balance by sector/volatility
        batches = []
        for i in range(0, len(symbols), batch_size):
            batches.append(symbols[i:i + batch_size])
        
        return batches
    
    @staticmethod
    def prioritize_symbols(symbols: List[str], criteria: Dict[str, Any]) -> List[str]:
        """
        Prioritize symbols based on given criteria
        
        Args:
            symbols: List of symbols
            criteria: Dictionary with prioritization criteria
            
        Returns:
            Reordered list of symbols
        """
        # For now, return as-is. Could be enhanced to prioritize by liquidity, volatility, etc.
        return symbols