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
        
        # Initialize strike selector - always available
        try:
            from strategy_creation.strike_selector import IntelligentStrikeSelector, StrikeRequest, StrikeConstraint
            self.strike_selector = IntelligentStrikeSelector()
            self.StrikeRequest = StrikeRequest
            self.StrikeConstraint = StrikeConstraint
        except ImportError:
            logger.error("Failed to import IntelligentStrikeSelector")
            self.strike_selector = None
            self.StrikeRequest = None
            self.StrikeConstraint = None
    
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
                
                # Check if strike exists
                if calls.empty and puts.empty:
                    logger.warning(f"Strike {strike} not available for {self.symbol}")
                    # Try to find nearest available strike
                    nearest_call = self._find_nearest_available_strike(strike, 'CALL')
                    nearest_put = self._find_nearest_available_strike(strike, 'PUT')
                    logger.info(f"Nearest available strikes - CALL: {nearest_call}, PUT: {nearest_put}")
                    return False
                
                # Basic liquidity check - more lenient
                if not calls.empty:
                    call_data = calls.iloc[0]
                    if call_data.get('open_interest', 0) < 10:  # Reduced from 50
                        logger.warning(f"Strike {strike} CALL has low liquidity (OI: {call_data.get('open_interest', 0)})")
                        
                if not puts.empty:
                    put_data = puts.iloc[0]
                    if put_data.get('open_interest', 0) < 10:  # Reduced from 50
                        logger.warning(f"Strike {strike} PUT has low liquidity (OI: {put_data.get('open_interest', 0)})")
            
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
    
    def _create_leg(self, option_data, position: str, quantity: int = 1, rationale: str = "") -> Dict:
        """Create a leg dictionary from option data"""
        try:
            # Handle both DataFrame row and dict
            if hasattr(option_data, 'to_dict'):
                option_data = option_data.to_dict()
            
            # Extract Greeks with proper field name handling
            delta_val = option_data.get('delta', 0)
            gamma_val = option_data.get('gamma', 0)
            theta_val = option_data.get('theta', 0)
            vega_val = option_data.get('vega', 0)
            
            # Handle IV field name variations
            iv_val = option_data.get('iv', option_data.get('implied_volatility', 0))
            
            # Handle expiry field if available
            expiry_val = option_data.get('expiry', option_data.get('expiry_date', None))
            
            leg_dict = {
                'option_type': option_data.get('option_type', 'CALL'),
                'position': position,
                'strike': option_data.get('strike', 0),
                'quantity': quantity,
                'premium': option_data.get('last_price', 0),
                'delta': float(delta_val) if delta_val is not None else 0.0,
                'gamma': float(gamma_val) if gamma_val is not None else 0.0,
                'theta': float(theta_val) if theta_val is not None else 0.0,
                'vega': float(vega_val) if vega_val is not None else 0.0,
                'iv': float(iv_val) if iv_val is not None else 0.0,
                'rationale': rationale
            }
            
            # Add expiry if available (for Calendar spreads)
            if expiry_val:
                leg_dict['expiry'] = expiry_val
                
            return leg_dict
            
        except Exception as e:
            logger.error(f"Error creating leg: {e}")
            return {
                'option_type': 'CALL',
                'position': position,
                'strike': 0,
                'quantity': quantity,
                'premium': 0,
                'delta': 0,
                'gamma': 0,
                'theta': 0,
                'vega': 0,
                'iv': 0,
                'rationale': rationale
            }
    
    def _get_days_to_expiry(self) -> int:
        """Get days to expiry from options data"""
        try:
            if self.options_df.empty:
                return 30  # Default
            
            # Try to extract from expiry date if available
            if 'expiry' in self.options_df.columns:
                expiry_str = self.options_df['expiry'].iloc[0]
                
                # Parse expiry date and calculate days to expiry
                try:
                    from datetime import datetime
                    expiry_date = datetime.strptime(expiry_str, '%Y-%m-%d')
                    current_date = datetime.now()
                    days_to_expiry = (expiry_date - current_date).days
                    
                    # Ensure we return at least 1 day
                    return max(1, days_to_expiry)
                    
                except (ValueError, TypeError):
                    logger.warning(f"Could not parse expiry date: {expiry_str}")
                    return 30  # Default monthly expiry
            
            return 30  # Default for monthly options
            
        except Exception as e:
            logger.error(f"Error getting days to expiry: {e}")
            return 30
    
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
        """Find the at-the-money strike using centralized selector"""
        try:
            # Use centralized strike selector if available
            if self.strike_selector:
                strikes = self.strike_selector.select_strikes(
                    strategy_type='ATM_STRIKE',  # Generic ATM request
                    options_df=self.options_df,
                    spot_price=self.spot_price,
                    market_analysis=self.market_analysis,
                    custom_config=[self.StrikeRequest(
                        name='strike',
                        option_type=option_type,
                        target_type='atm',
                        target_value=None,
                        constraint=None
                    )]
                )
                if strikes and 'strike' in strikes:
                    return strikes['strike']
            
            # Fallback to simple selection
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
        """Find strike closest to target delta using centralized selector"""
        try:
            # Use centralized strike selector if available
            if self.strike_selector:
                strikes = self.strike_selector.select_strikes(
                    strategy_type='DELTA_STRIKE',  # Generic delta-based request
                    options_df=self.options_df,
                    spot_price=self.spot_price,
                    market_analysis=self.market_analysis,
                    custom_config=[self.StrikeRequest(
                        name='strike',
                        option_type=option_type,
                        target_type='delta',
                        target_value=target_delta,
                        constraint=None
                    )]
                )
                if strikes and 'strike' in strikes:
                    return strikes['strike']
            
            # Fallback to original logic
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
        """Find the nearest available strike to target strike using centralized selector"""
        try:
            # Use centralized strike selector if available
            if self.strike_selector:
                strikes = self.strike_selector.select_strikes(
                    strategy_type='NEAREST_STRIKE',  # Generic nearest strike request
                    options_df=self.options_df,
                    spot_price=self.spot_price,
                    market_analysis=self.market_analysis,
                    custom_config=[self.StrikeRequest(
                        name='strike',
                        option_type=option_type,
                        target_type='moneyness',
                        target_value=(target_strike - self.spot_price) / self.spot_price,
                        constraint=self.StrikeConstraint(max_distance_pct=0.20)
                    )]
                )
                if strikes and 'strike' in strikes:
                    return strikes['strike']
            
            # Fallback to simple nearest strike
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
            
            # Log available strikes for debugging
            if len(strikes) < 5:
                logger.warning(f"Limited strikes available for {option_type}: {strikes}")
                
            return strikes
            
        except Exception as e:
            logger.error(f"Error getting available strikes: {e}")
            return []
    
    def select_strikes_for_strategy(self, use_expected_moves: bool = True) -> Dict[str, float]:
        """
        Select strikes using centralized strike selector
        
        Returns:
            Dictionary mapping strike names to selected strikes
        """
        try:
            if not self.strike_selector:
                logger.warning("Strike selector not available, using fallback")
                return {}
            
            # Get strikes from centralized selector
            strategy_name = self.get_strategy_name()
            strikes = self.strike_selector.select_strikes(
                strategy_type=strategy_name,
                options_df=self.options_df,
                spot_price=self.spot_price,
                market_analysis=self.market_analysis
            )
            
            if not strikes:
                logger.error(f"No strikes selected for {strategy_name}")
                
            return strikes
            
        except Exception as e:
            logger.error(f"Error in centralized strike selection: {e}")
            return {}
    
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