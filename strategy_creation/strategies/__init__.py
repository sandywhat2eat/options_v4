"""
Strategy implementations for Options V4 system
"""

from .base_strategy import BaseStrategy
from .directional.long_options import LongCall, LongPut
from .directional.short_options import ShortCall, ShortPut
from .directional.spreads import BullCallSpread, BearCallSpread
from .directional.bull_put_spread import BullPutSpreadStrategy
from .directional.bear_put_spread import BearPutSpreadStrategy
from .neutral.iron_condor import IronCondor
from .neutral.butterfly import ButterflySpread
from .neutral.iron_butterfly import IronButterfly
from .volatility.straddles import LongStraddle
from .volatility.short_straddle import ShortStraddle
from .volatility.long_strangle import LongStrangle
from .volatility.short_strangle import ShortStrangle
from .advanced.calendar_spread import CalendarSpread
from .advanced.diagonal_spread import DiagonalSpread
from .advanced.call_ratio_spread import CallRatioSpread
from .advanced.put_ratio_spread import PutRatioSpread
from .advanced.jade_lizard import JadeLizard
from .advanced.broken_wing_butterfly import BrokenWingButterfly
from .income.cash_secured_put import CashSecuredPut
from .income.covered_call import CoveredCall

__all__ = [
    'BaseStrategy',
    'LongCall', 'LongPut', 'ShortCall', 'ShortPut',
    'BullCallSpread', 'BearCallSpread', 'BullPutSpreadStrategy', 'BearPutSpreadStrategy',
    'IronCondor', 'ButterflySpread', 'IronButterfly',
    'LongStraddle', 'ShortStraddle', 'LongStrangle', 'ShortStrangle',
    'CalendarSpread', 'DiagonalSpread', 'CallRatioSpread', 'PutRatioSpread',
    'JadeLizard', 'BrokenWingButterfly',
    'CashSecuredPut', 'CoveredCall'
]