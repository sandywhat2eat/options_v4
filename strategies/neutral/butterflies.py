"""
Butterfly strategies (Iron Butterfly)
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from strategies.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)

class IronButterfly(BaseStrategy):
    """Iron Butterfly strategy implementation"""
    
    def get_strategy_name(self) -> str:
        return "Iron Butterfly"
    
    def get_market_outlook(self) -> str:
        return "neutral"
    
    def get_iv_preference(self) -> str:
        return "high"  # Sell volatility at center strike
    
    def construct_strategy(self, wing_width: int = 5) -> Dict:
        """
        Construct Iron Butterfly strategy
        
        Structure:
        - Short ATM Call and Put (body)
        - Long OTM Call and Put (wings)
        
        Args:
            wing_width: Distance from ATM to wing strikes (default 5)
        """
        try:
            # Find ATM strike
            atm_strike = self._find_atm_strike()
            
            # Calculate wing strikes
            call_wing_strike = atm_strike + wing_width
            put_wing_strike = atm_strike - wing_width
            
            # Validate all strikes
            strikes = [put_wing_strike, atm_strike, call_wing_strike]
            if not self.validate_strikes(strikes):
                return {'success': False, 'reason': 'Strikes not available or illiquid'}
            
            # Validate proper ordering
            if not (put_wing_strike < atm_strike < call_wing_strike):
                return {'success': False, 'reason': 'Invalid strike structure'}
            
            # Get option data
            atm_call_data = self._get_option_data(atm_strike, 'CALL')
            atm_put_data = self._get_option_data(atm_strike, 'PUT')
            call_wing_data = self._get_option_data(call_wing_strike, 'CALL')
            put_wing_data = self._get_option_data(put_wing_strike, 'PUT')
            
            if any(data is None for data in [atm_call_data, atm_put_data, call_wing_data, put_wing_data]):
                return {'success': False, 'reason': 'Option data not available'}
            
            # Additional risk check
            if not self._validate_iron_butterfly_risk(atm_call_data, atm_put_data):
                return {'success': False, 'reason': 'Risk parameters not suitable'}
            
            # Construct legs
            self.legs = [
                {
                    'option_type': 'CALL',
                    'position': 'SHORT',
                    'strike': atm_strike,
                    'premium': atm_call_data.get('last_price', 0),
                    'delta': atm_call_data.get('delta', 0),
                    'rationale': 'Short ATM call (body)'
                },
                {
                    'option_type': 'PUT',
                    'position': 'SHORT',
                    'strike': atm_strike,
                    'premium': atm_put_data.get('last_price', 0),
                    'delta': atm_put_data.get('delta', 0),
                    'rationale': 'Short ATM put (body)'
                },
                {
                    'option_type': 'CALL',
                    'position': 'LONG',
                    'strike': call_wing_strike,
                    'premium': call_wing_data.get('last_price', 0),
                    'delta': call_wing_data.get('delta', 0),
                    'rationale': 'Long OTM call (wing)'
                },
                {
                    'option_type': 'PUT',
                    'position': 'LONG',
                    'strike': put_wing_strike,
                    'premium': put_wing_data.get('last_price', 0),
                    'delta': put_wing_data.get('delta', 0),
                    'rationale': 'Long OTM put (wing)'
                }
            ]
            
            # Calculate metrics
            net_credit = self._calculate_net_credit()
            max_profit = net_credit
            max_loss = wing_width - net_credit
            
            # Breakeven points
            upper_breakeven = atm_strike + net_credit
            lower_breakeven = atm_strike - net_credit
            
            # Profit zone
            profit_zone_pct = (2 * net_credit / self.spot_price) * 100
            
            greeks = self.get_greeks_summary()
            
            return {
                'success': True,
                'strategy_name': self.get_strategy_name(),
                'legs': self.legs,
                'max_profit': max_profit,
                'max_loss': max_loss,
                'breakeven_points': [lower_breakeven, upper_breakeven],
                'profit_zone': (lower_breakeven, upper_breakeven),
                'profit_zone_pct': profit_zone_pct,
                'wing_width': wing_width,
                'center_strike': atm_strike,
                'delta_exposure': greeks['delta'],
                'theta_decay': greeks['theta'],
                'vega_exposure': greeks['vega'],
                'optimal_outcome': f"Stock pins at {atm_strike:.2f} at expiry",
                'risk_reward_ratio': max_profit / max_loss if max_loss > 0 else 0,
                'strategy_note': 'Maximum profit when stock expires exactly at center strike'
            }
            
        except Exception as e:
            logger.error(f"Error constructing Iron Butterfly: {e}")
            return {'success': False, 'reason': f'Construction error: {e}'}
    
    def _find_atm_strike(self) -> float:
        """Find ATM strike closest to spot price"""
        try:
            all_strikes = self.options_df['strike'].unique()
            strike_diffs = np.abs(all_strikes - self.spot_price)
            atm_strike = all_strikes[np.argmin(strike_diffs)]
            return float(atm_strike)
            
        except Exception as e:
            logger.error(f"Error finding ATM strike: {e}")
            # Round to nearest standard strike
            return round(self.spot_price / 5) * 5
    
    def _validate_iron_butterfly_risk(self, atm_call_data: pd.Series, atm_put_data: pd.Series) -> bool:
        """Validate risk parameters for Iron Butterfly"""
        try:
            # Check IV levels - need reasonable IV to sell
            call_iv = atm_call_data.get('iv', 0)
            put_iv = atm_put_data.get('iv', 0)
            avg_iv = (call_iv + put_iv) / 2
            
            if avg_iv < 20:
                logger.warning(f"IV too low for Iron Butterfly: {avg_iv}")
                return False
            
            # Check liquidity at ATM
            call_oi = atm_call_data.get('open_interest', 0)
            put_oi = atm_put_data.get('open_interest', 0)
            
            if call_oi < 200 or put_oi < 200:  # Higher requirement for ATM
                logger.warning("Insufficient OI at ATM for Iron Butterfly")
                return False
            
            # Check bid-ask spreads
            call_spread = (atm_call_data.get('ask', 0) - atm_call_data.get('bid', 0))
            put_spread = (atm_put_data.get('ask', 0) - atm_put_data.get('bid', 0))
            
            call_mid = (atm_call_data.get('ask', 0) + atm_call_data.get('bid', 0)) / 2
            put_mid = (atm_put_data.get('ask', 0) + atm_put_data.get('bid', 0)) / 2
            
            if call_mid > 0 and put_mid > 0:
                call_spread_pct = call_spread / call_mid
                put_spread_pct = put_spread / put_mid
                
                if call_spread_pct > 0.1 or put_spread_pct > 0.1:  # 10% max spread
                    logger.warning("Bid-ask spreads too wide for Iron Butterfly")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating Iron Butterfly risk: {e}")
            return False
    
    def _calculate_net_credit(self) -> float:
        """Calculate net credit received"""
        try:
            total_credit = 0.0
            
            for leg in self.legs:
                premium = leg.get('premium', 0)
                if leg['position'] == 'SHORT':
                    total_credit += premium
                else:  # LONG
                    total_credit -= premium
            
            return total_credit
            
        except Exception as e:
            logger.error(f"Error calculating net credit: {e}")
            return 0.0