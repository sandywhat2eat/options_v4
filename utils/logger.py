"""
Centralized logging configuration for Options V4 system
"""

import logging
import os
from datetime import datetime
from typing import Optional

def setup_logger(name: str, log_level: str = 'INFO', 
                log_file: Optional[str] = None) -> logging.Logger:
    """
    Set up a logger with both file and console handlers
    
    Args:
        name: Logger name
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional log file path
    """
    
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler
    if log_file:
        # Create logs directory if it doesn't exist
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(getattr(logging, log_level.upper()))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

def get_default_log_file(module_name: str) -> str:
    """Get default log file path for a module"""
    timestamp = datetime.now().strftime('%Y%m%d')
    log_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'logs'
    )
    return os.path.join(log_dir, f'{module_name}_{timestamp}.log')