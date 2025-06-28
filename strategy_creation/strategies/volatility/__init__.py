"""
Volatility-based options strategies
"""

from .straddles import LongStraddle
from .short_straddle import ShortStraddle
from .long_strangle import LongStrangle
from .short_strangle import ShortStrangle

__all__ = ['LongStraddle', 'ShortStraddle', 'LongStrangle', 'ShortStrangle']