"""
Income generation strategies
"""

from .cash_secured_put import CashSecuredPut
from .covered_call import CoveredCall

__all__ = ['CashSecuredPut', 'CoveredCall']