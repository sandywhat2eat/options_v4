"""
Base Strategy class for all options strategies
"""

from abc import ABC, abstractmethod
import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

class BaseStrategy(ABC):
    """Abstract base class for all options strategies"""
    
    def __init__(self, symbol: str, spot_price: float, options_df: pd.DataFrame, 
                 lot_size: int = 1, market_analysis: Dict = None):
        self.symbol = symbol
        self.spot_price = spot_price
        self.options_df = options_df
        self.lot_size = lot_size  # Number of contracts per lot
        self.market_analysis = market_analysis or {}
        self.legs = []
        self.strategy_data = {}
        self.expected_moves = self._extract_expected_moves()
        
        # Initialize strike selector
        try:
            from core.strike_selector import IntelligentStrikeSelector
            self.strike_selector = IntelligentStrikeSelector()
        except ImportError:
            # Fallback if strike selector not available
            self.strike_selector = None
    
    @abstractmethod
    def construct_strategy(self, **kwargs) -> Dict:
        """Construct the strategy with specific parameters"""
        pass
    
    @abstractmethod
    def get_strategy_name(self) -> str:
        """Return strategy name"""
        pass
    
    @abstractmethod
    def get_market_outlook(self) -> str:
        """Return required market outlook (bullish/bearish/neutral)"""
        pass
    
    @abstractmethod
    def get_iv_preference(self) -> str:
        """Return IV preference (high/low/neutral)"""
        pass
    
    def calculate_payoff(self, underlying_prices: List[float]) -> Dict:
        """Calculate payoff at different underlying prices"""
        try:
            payoffs = []
            
            for price in underlying_prices:
                total_payoff = 0.0
                
                for leg in self.legs:
                    leg_payoff = self._calculate_leg_payoff(leg, price)
                    total_payoff += leg_payoff
                
                payoffs.append(total_payoff)
            
            return {
                'prices': underlying_prices,
                'payoffs': payoffs,
                'max_profit': max(payoffs),
                'max_loss': min(payoffs),
                'breakeven_points': self._find_breakeven_points(underlying_prices, payoffs)
            }
            
        except Exception as e:
            logger.error(f"Error calculating payoff for {self.get_strategy_name()}: {e}")
            return {'prices': [], 'payoffs': [], 'max_profit': 0, 'max_loss': 0}
    
    def _calculate_leg_payoff(self, leg: Dict, underlying_price: float) -> float:
        """Calculate payoff for individual leg"""
        try:
            strike = leg['strike']
            option_type = leg['option_type']
            position = leg['position']
            premium = leg['premium']
            
            # Intrinsic value calculation
            if option_type.upper() == 'CALL':
                intrinsic = max(0, underlying_price - strike)
            else:  # PUT
                intrinsic = max(0, strike - underlying_price)
            
            # Position adjustment
            if position.upper() == 'LONG':
                return intrinsic - premium
            else:  # SHORT
                return premium - intrinsic
                
        except Exception as e:
            logger.error(f"Error calculating leg payoff: {e}")
            return 0.0
    
    def _find_breakeven_points(self, prices: List[float], payoffs: List[float]) -> List[float]:
        """Find breakeven points where payoff crosses zero"""
        breakevens = []
        
        try:
            for i in range(len(payoffs) - 1):
                if (payoffs[i] <= 0 and payoffs[i + 1] > 0) or (payoffs[i] >= 0 and payoffs[i + 1] < 0):
                    # Linear interpolation to find exact breakeven
                    price_diff = prices[i + 1] - prices[i]
                    payoff_diff = payoffs[i + 1] - payoffs[i]
                    
                    if payoff_diff != 0:
                        breakeven = prices[i] - (payoffs[i] * price_diff / payoff_diff)
                        breakevens.append(round(breakeven, 2))
            
            return sorted(set(breakevens))  # Remove duplicates and sort
            
        except Exception as e:
            logger.error(f"Error finding breakeven points: {e}")
            return []
    
    def get_greeks_summary(self) -> Dict:
        """Calculate total Greeks for the strategy"""
        try:
            total_delta = 0.0
            total_gamma = 0.0
            total_theta = 0.0
            total_vega = 0.0
            
            for leg in self.legs:
                option_data = self._get_option_data(leg['strike'], leg['option_type'])
                if option_data is None:
                    continue
                
                multiplier = 1 if leg['position'].upper() == 'LONG' else -1
                
                total_delta += multiplier * option_data.get('delta', 0)
                total_gamma += multiplier * option_data.get('gamma', 0)
                total_theta += multiplier * option_data.get('theta', 0)
                total_vega += multiplier * option_data.get('vega', 0)
            
            return {
                'delta': round(total_delta, 4),
                'gamma': round(total_gamma, 4),
                'theta': round(total_theta, 4),
                'vega': round(total_vega, 4)
            }
            
        except Exception as e:
            logger.error(f"Error calculating Greeks summary: {e}")
            return {'delta': 0, 'gamma': 0, 'theta': 0, 'vega': 0}
    
    def _get_option_data(self, strike: float, option_type: str) -> Optional[pd.Series]:
        """Get option data for specific strike and type"""
        try:
            option_data = self.options_df[
                (self.options_df['strike'] == strike) & 
                (self.options_df['option_type'] == option_type.upper())
            ]
            
            if option_data.empty:
                return None
            
            return option_data.iloc[0]
            
        except Exception as e:
            logger.error(f"Error getting option data: {e}")
            return None
    
    def validate_strikes(self, strikes: List[float]) -> bool:
        """Validate that all required strikes are available and liquid"""
        try:
            for strike in strikes:
                calls = self.options_df[
                    (self.options_df['strike'] == strike) & 
                    (self.options_df['option_type'] == 'CALL')
                ]
                puts = self.options_df[
                    (self.options_df['strike'] == strike) & 
                    (self.options_df['option_type'] == 'PUT')
                ]
                
                # Check if strike exists and has minimum liquidity
                if calls.empty or puts.empty:
                    logger.warning(f"Strike {strike} not available for {self.symbol}")
                    return False
                
                # Basic liquidity check
                call_data = calls.iloc[0]
                put_data = puts.iloc[0]
                
                if (call_data.get('open_interest', 0) < 50 or 
                    put_data.get('open_interest', 0) < 50):
                    logger.warning(f"Strike {strike} has poor liquidity for {self.symbol}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating strikes: {e}")
            return False
    
    def get_risk_metrics(self) -> Dict:
        """Calculate risk metrics for the strategy"""
        try:
            # Generate price range for analysis
            price_range = np.linspace(self.spot_price * 0.8, self.spot_price * 1.2, 100)
            payoff_data = self.calculate_payoff(price_range.tolist())
            
            max_profit = payoff_data['max_profit']
            max_loss = abs(payoff_data['max_loss'])  # Make positive
            
            return {
                'max_profit': max_profit,
                'max_loss': max_loss,
                'risk_reward_ratio': max_profit / max_loss if max_loss > 0 else 0,
                'breakeven_points': payoff_data['breakeven_points'],
                'profit_range': self._calculate_profit_range(payoff_data),
                'days_to_expiry': self._get_days_to_expiry()
            }
            
        except Exception as e:
            logger.error(f"Error calculating risk metrics: {e}")
            return {'max_profit': 0, 'max_loss': 0, 'risk_reward_ratio': 0}
    
    def _calculate_profit_range(self, payoff_data: Dict) -> Tuple[float, float]:
        """Calculate price range where strategy is profitable"""
        try:
            prices = payoff_data['prices']
            payoffs = payoff_data['payoffs']
            
            profitable_prices = [price for price, payoff in zip(prices, payoffs) if payoff > 0]
            
            if not profitable_prices:
                return (0.0, 0.0)
            
            return (min(profitable_prices), max(profitable_prices))
            
        except Exception as e:
            logger.error(f"Error calculating profit range: {e}")
            return (0.0, 0.0)
    
    def _get_days_to_expiry(self) -> int:
        """Get days to expiry from options data"""
        try:
            if self.options_df.empty:
                return 30  # Default
            
            # Try to extract from expiry date if available
            if 'expiry' in self.options_df.columns:
                expiry_str = self.options_df['expiry'].iloc[0]
                # Add logic to parse expiry date and calculate days
                return 7  # Default weekly expiry
            
            return 7  # Default for weekly options
            
        except Exception as e:
            logger.error(f"Error getting days to expiry: {e}")
            return 7
    
    def to_dict(self) -> Dict:
        """Convert strategy to dictionary format"""
        try:
            greeks = self.get_greeks_summary()
            risk_metrics = self.get_risk_metrics()
            
            return {
                'name': self.get_strategy_name(),
                'symbol': self.symbol,
                'market_outlook': self.get_market_outlook(),
                'iv_preference': self.get_iv_preference(),
                'legs': self.legs,
                'greeks': greeks,
                'risk_metrics': risk_metrics,
                'constructed_at': pd.Timestamp.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error converting strategy to dict: {e}")
            return {'name': self.get_strategy_name(), 'error': str(e)}
    
    def _find_atm_strike(self, option_type: str = 'CALL') -> Optional[float]:
        """Find the at-the-money strike"""
        try:
            strikes = self.options_df[self.options_df['option_type'] == option_type]['strike'].unique()
            if len(strikes) == 0:
                return None
            
            # Find strike closest to spot price
            strike_diffs = np.abs(strikes - self.spot_price)
            atm_idx = np.argmin(strike_diffs)
            return strikes[atm_idx]
            
        except Exception as e:
            logger.error(f"Error finding ATM strike: {e}")
            return None
    
    def _find_optimal_strike(self, target_delta: float, option_type: str) -> Optional[float]:
        """Find strike closest to target delta"""
        try:
            options = self.options_df[self.options_df['option_type'] == option_type]
            if options.empty:
                return None
            
            # If delta not available, use distance from spot as proxy
            if 'delta' not in options.columns:
                if option_type == 'CALL':
                    # For calls, slightly OTM is around 0.3-0.4 delta
                    target_price = self.spot_price * (1 + 0.02) if target_delta < 0.5 else self.spot_price
                else:
                    # For puts, slightly OTM is around 0.3-0.4 delta  
                    target_price = self.spot_price * (1 - 0.02) if target_delta < 0.5 else self.spot_price
                
                strike_diffs = np.abs(options['strike'] - target_price)
                optimal_idx = np.argmin(strike_diffs)
                return options.iloc[optimal_idx]['strike']
            
            # Find strike with delta closest to target
            delta_diffs = np.abs(options['delta'] - target_delta)
            optimal_idx = np.argmin(delta_diffs)
            return options.iloc[optimal_idx]['strike']
            
        except Exception as e:
            logger.error(f"Error finding optimal strike: {e}")
            return None
    
    def _find_nearest_available_strike(self, target_strike: float, option_type: str) -> Optional[float]:
        """Find the nearest available strike to target strike"""
        try:
            strikes = self.options_df[self.options_df['option_type'] == option_type]['strike'].unique()
            if len(strikes) == 0:
                return None
            
            # Find closest available strike
            strike_diffs = np.abs(strikes - target_strike)
            nearest_idx = np.argmin(strike_diffs)
            return strikes[nearest_idx]
            
        except Exception as e:
            logger.error(f"Error finding nearest strike: {e}")
            return None
    
    def _get_available_strikes(self, option_type: str, min_strike: float = None, 
                             max_strike: float = None) -> List[float]:
        """Get all available strikes within range"""
        try:
            strikes = self.options_df[self.options_df['option_type'] == option_type]['strike'].unique()
            strikes = sorted(strikes)
            
            if min_strike is not None:
                strikes = [s for s in strikes if s >= min_strike]
            if max_strike is not None:
                strikes = [s for s in strikes if s <= max_strike]
                
            return strikes
            
        except Exception as e:
            logger.error(f"Error getting available strikes: {e}")
            return []
    
    def _extract_expected_moves(self) -> Dict:
        """Extract expected moves from market analysis"""
        try:
            price_levels = self.market_analysis.get('price_levels', {})
            expected_moves = price_levels.get('expected_moves', {})
            
            return {
                'one_sd_move': expected_moves.get('one_sd_move', self.spot_price * 0.05),
                'two_sd_move': expected_moves.get('two_sd_move', self.spot_price * 0.10),
                'one_sd_pct': expected_moves.get('one_sd_pct', 5.0),
                'two_sd_pct': expected_moves.get('two_sd_pct', 10.0),
                'upper_expected': expected_moves.get('upper_expected', self.spot_price * 1.05),
                'lower_expected': expected_moves.get('lower_expected', self.spot_price * 0.95),
                'timeframe': self.market_analysis.get('timeframe', {}).get('duration', '10-30 days')
            }
        except Exception as e:
            logger.error(f"Error extracting expected moves: {e}")
            return {
                'one_sd_move': self.spot_price * 0.05,
                'two_sd_move': self.spot_price * 0.10,
                'timeframe': '10-30 days'
            }
    
    def _calculate_probability_itm(self, strike: float, spot_price: float, market_analysis: Dict, option_type: str) -> float:
        """
        Calculate probability of option finishing in-the-money using delta approximation
        
        Args:
            strike: Option strike price
            spot_price: Current underlying price  
            market_analysis: Market analysis data containing option info
            option_type: 'CALL' or 'PUT'
        
        Returns:
            Probability (0.0 to 1.0) of finishing ITM
        """
        try:
            # Try to get delta from option data
            option_data = self._get_option_data(strike, option_type)
            if option_data is not None and 'delta' in option_data:
                delta = abs(option_data['delta'])
                return min(1.0, max(0.0, delta))
            
            # Fallback: Use moneyness-based approximation
            if option_type.upper() == 'CALL':
                if strike <= spot_price:
                    # ITM call - high probability
                    moneyness = spot_price / strike
                    return min(0.95, 0.5 + (moneyness - 1) * 2)
                else:
                    # OTM call - lower probability based on distance
                    moneyness = strike / spot_price
                    return max(0.05, 0.5 - (moneyness - 1) * 1.5)
            else:  # PUT
                if strike >= spot_price:
                    # ITM put - high probability  
                    moneyness = strike / spot_price
                    return min(0.95, 0.5 + (moneyness - 1) * 2)
                else:
                    # OTM put - lower probability based on distance
                    moneyness = spot_price / strike
                    return max(0.05, 0.5 - (moneyness - 1) * 1.5)
                    
        except Exception as e:
            logger.error(f"Error calculating probability ITM: {e}")
            return 0.5  # Default 50% if calculation fails