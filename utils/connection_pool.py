"""
Connection pool manager for Supabase connections
Handles rate limiting and connection reuse
"""

import os
import time
import logging
from threading import Lock, Semaphore
from typing import Optional, Any, Callable
from functools import wraps
from supabase import create_client, Client

logger = logging.getLogger(__name__)

class ConnectionPool:
    """
    Manages a pool of Supabase connections with rate limiting
    """
    
    def __init__(self, max_connections: int = 5, requests_per_second: int = 10):
        """
        Initialize connection pool
        
        Args:
            max_connections: Maximum concurrent connections
            requests_per_second: Rate limit for API requests
        """
        self.max_connections = max_connections
        self.requests_per_second = requests_per_second
        self.min_request_interval = 1.0 / requests_per_second
        
        # Connection management
        self.connection_semaphore = Semaphore(max_connections)
        self.rate_limit_lock = Lock()
        self.last_request_time = 0
        
        # Create base client
        self.url = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
        self.key = os.getenv('NEXT_PUBLIC_SUPABASE_ANON_KEY')
        
        if not self.url or not self.key:
            raise ValueError("Supabase credentials not found in environment")
            
        logger.info(f"Connection pool initialized: max_connections={max_connections}, rps={requests_per_second}")
    
    def get_client(self) -> Client:
        """
        Get a Supabase client from the pool
        
        Returns:
            Supabase client instance
        """
        # For thread safety, create a new client for each request
        # Supabase Python client is thread-safe this way
        return create_client(self.url, self.key)
    
    def rate_limited_request(self, func: Callable) -> Callable:
        """
        Decorator to apply rate limiting to API requests
        
        Args:
            func: Function making API request
            
        Returns:
            Rate-limited function
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Acquire connection slot
            with self.connection_semaphore:
                # Apply rate limiting
                with self.rate_limit_lock:
                    current_time = time.time()
                    time_since_last = current_time - self.last_request_time
                    
                    if time_since_last < self.min_request_interval:
                        sleep_time = self.min_request_interval - time_since_last
                        time.sleep(sleep_time)
                    
                    self.last_request_time = time.time()
                
                # Make the request
                return func(*args, **kwargs)
        
        return wrapper
    
    def execute_with_retry(self, func: Callable, max_retries: int = 3, 
                          initial_delay: float = 1.0) -> Any:
        """
        Execute function with exponential backoff retry
        
        Args:
            func: Function to execute
            max_retries: Maximum retry attempts
            initial_delay: Initial retry delay in seconds
            
        Returns:
            Function result
        """
        delay = initial_delay
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                return func()
            except Exception as e:
                last_exception = e
                if "[Errno 35]" in str(e) and attempt < max_retries - 1:
                    logger.warning(f"Connection error, retrying in {delay}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff
                else:
                    raise
        
        raise last_exception

# Global connection pool instance
_connection_pool: Optional[ConnectionPool] = None

def get_connection_pool() -> ConnectionPool:
    """
    Get or create the global connection pool
    
    Returns:
        ConnectionPool instance
    """
    global _connection_pool
    
    if _connection_pool is None:
        # Adjust based on system capabilities
        max_connections = int(os.getenv('SUPABASE_MAX_CONNECTIONS', '5'))
        requests_per_second = int(os.getenv('SUPABASE_RPS', '10'))
        
        _connection_pool = ConnectionPool(
            max_connections=max_connections,
            requests_per_second=requests_per_second
        )
    
    return _connection_pool

def close_connection_pool():
    """Close the connection pool"""
    global _connection_pool
    if _connection_pool:
        logger.info("Closing connection pool")
        _connection_pool = None