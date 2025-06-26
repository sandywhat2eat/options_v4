"""
Advanced Options Allocator Package
A modular system for sophisticated options portfolio allocation
"""

from .core import (
    AdvancedOptionsAllocator,
    AllocationResult,
    MarketDirectionAnalyzer,
    IndustryAllocator,
    MarketCapAllocator,
    StockSelector,
    StrategySelector,
    PositionSizer
)

__version__ = '1.0.0'

__all__ = [
    'AdvancedOptionsAllocator',
    'AllocationResult',
    'MarketDirectionAnalyzer',
    'IndustryAllocator',
    'MarketCapAllocator',
    'StockSelector',
    'StrategySelector',
    'PositionSizer'
]