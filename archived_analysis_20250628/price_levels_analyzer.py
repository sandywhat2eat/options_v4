"""
Price Levels Analyzer for support/resistance and expected moves
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

class PriceLevelsAnalyzer:
    """Analyzes price levels, support/resistance, and expected moves"""
    
    def __init__(self):
        self.support_resistance_thresholds = {
            'strong': 0.03,  # Within 3% is considered strong
            'moderate': 0.05,  # Within 5% is moderate
            'weak': 0.08     # Within 8% is weak
        }
    
    def analyze_price_levels(self, symbol: str, options_df: pd.DataFrame, 
                           spot_price: float, technical_data: Dict = None) -> Dict:
        """
        Comprehensive price levels analysis matching original sophistication
        
        Args:
            symbol: Stock symbol
            options_df: Options chain data
            spot_price: Current spot price
            technical_data: Technical analysis data (support/resistance from TA)
        
        Returns:
            Dictionary with price levels analysis
        """
        try:
            logger.info(f"\n=== Price Levels Analysis for {symbol} ===")
            logger.info(f"Spot Price: {spot_price}")
            
            # 1. Options-based Support/Resistance
            options_levels = self._analyze_options_based_levels(options_df, spot_price)
            
            # 2. Expected Move Calculation
            expected_moves = self._calculate_expected_moves(options_df, spot_price)
            
            # 3. Max Pain Analysis
            max_pain_analysis = self._analyze_max_pain(options_df, spot_price)
            
            # 4. Value Area Analysis
            value_area = self._calculate_value_area(options_df, spot_price)
            
            # 5. Combined Support/Resistance Levels
            combined_levels = self._combine_support_resistance(
                options_levels, 
                technical_data.get('support_resistance', {}) if technical_data else {},
                max_pain_analysis,
                value_area
            )
            
            # 6. Price Targets
            price_targets = self._calculate_price_targets(
                spot_price,
                expected_moves,
                combined_levels,
                technical_data
            )
            
            return {
                'short_term': {
                    'support': combined_levels['short_term_support'],
                    'resistance': combined_levels['short_term_resistance'],
                    'strength': combined_levels['short_term_strength'],
                    'timeframe': '1-5 days'
                },
                'mid_term': {
                    'support': combined_levels['mid_term_support'],
                    'resistance': combined_levels['mid_term_resistance'],
                    'strength': combined_levels['mid_term_strength'],
                    'timeframe': '10-30 days'
                },
                'expected_moves': expected_moves,
                'max_pain': max_pain_analysis,
                'value_area': value_area,
                'price_targets': price_targets,
                'key_levels': combined_levels['key_levels'],
                'spot_position': self._analyze_spot_position(
                    spot_price,
                    combined_levels,
                    max_pain_analysis
                )
            }
            
        except Exception as e:
            logger.error(f"Error analyzing price levels for {symbol}: {e}")
            return self._default_price_levels(spot_price)
    
    def _analyze_options_based_levels(self, options_df: pd.DataFrame, spot_price: float) -> Dict:
        """Analyze support/resistance from options OI and volume"""
        try:
            calls = options_df[options_df['option_type'] == 'CALL']
            puts = options_df[options_df['option_type'] == 'PUT']
            
            # Find high OI strikes
            if not calls.empty and not puts.empty:
                # Sort by OI
                high_oi_calls = calls.nlargest(5, 'open_interest')
                high_oi_puts = puts.nlargest(5, 'open_interest')
                
                # OI-weighted strikes
                call_resistance = self._calculate_oi_weighted_strikes(high_oi_calls, 'resistance')
                put_support = self._calculate_oi_weighted_strikes(high_oi_puts, 'support')
                
                # Volume-based levels (more recent activity)
                high_vol_calls = calls.nlargest(5, 'volume')
                high_vol_puts = puts.nlargest(5, 'volume')
                
                vol_resistance = high_vol_calls['strike'].min() if not high_vol_calls.empty else spot_price * 1.05
                vol_support = high_vol_puts['strike'].max() if not high_vol_puts.empty else spot_price * 0.95
                
                logger.info(f"OI-based Resistance: {call_resistance}, Support: {put_support}")
                logger.info(f"Volume-based Resistance: {vol_resistance}, Support: {vol_support}")
                
                return {
                    'oi_resistance': call_resistance,
                    'oi_support': put_support,
                    'volume_resistance': vol_resistance,
                    'volume_support': vol_support,
                    'resistance_strikes': high_oi_calls['strike'].tolist(),
                    'support_strikes': high_oi_puts['strike'].tolist()
                }
            
            return self._default_options_levels(spot_price)
            
        except Exception as e:
            logger.error(f"Error analyzing options-based levels: {e}")
            return self._default_options_levels(spot_price)
    
    def _calculate_oi_weighted_strikes(self, options: pd.DataFrame, level_type: str) -> float:
        """Calculate OI-weighted strike levels"""
        try:
            if options.empty:
                return 0
            
            total_oi = options['open_interest'].sum()
            if total_oi == 0:
                return options['strike'].mean()
            
            weighted_strike = (options['strike'] * options['open_interest']).sum() / total_oi
            
            # For resistance, bias towards lower strikes with high OI
            # For support, bias towards higher strikes with high OI
            if level_type == 'resistance':
                # Find the lowest strike with significant OI (>20% of max)
                max_oi = options['open_interest'].max()
                significant = options[options['open_interest'] > max_oi * 0.2]
                if not significant.empty:
                    weighted_strike = significant['strike'].min()
            else:  # support
                # Find the highest strike with significant OI
                max_oi = options['open_interest'].max()
                significant = options[options['open_interest'] > max_oi * 0.2]
                if not significant.empty:
                    weighted_strike = significant['strike'].max()
            
            return weighted_strike
            
        except Exception as e:
            logger.error(f"Error calculating OI-weighted strikes: {e}")
            return options['strike'].mean() if not options.empty else 0
    
    def _calculate_expected_moves(self, options_df: pd.DataFrame, spot_price: float) -> Dict:
        """Calculate expected moves from ATM straddle prices"""
        try:
            # Find ATM strike
            strikes = options_df['strike'].unique()
            atm_strike = min(strikes, key=lambda x: abs(x - spot_price))
            
            # Get ATM options
            atm_options = options_df[options_df['strike'] == atm_strike]
            atm_calls = atm_options[atm_options['option_type'] == 'CALL']
            atm_puts = atm_options[atm_options['option_type'] == 'PUT']
            
            if not atm_calls.empty and not atm_puts.empty and 'premium' in options_df.columns:
                # ATM straddle price
                atm_call_price = atm_calls['premium'].iloc[0]
                atm_put_price = atm_puts['premium'].iloc[0]
                straddle_price = atm_call_price + atm_put_price
                
                # Expected move calculation (80% probability range)
                one_sd_move = straddle_price * 0.85
                one_sd_pct = (one_sd_move / spot_price) * 100
                
                # Daily expected move (assuming weekly options)
                daily_move = one_sd_move / np.sqrt(7)
                daily_pct = (daily_move / spot_price) * 100
                
                logger.info(f"ATM Straddle: {straddle_price:.2f}")
                logger.info(f"Expected Move (1SD): ±{one_sd_move:.2f} ({one_sd_pct:.1f}%)")
                logger.info(f"Daily Expected Move: ±{daily_move:.2f} ({daily_pct:.1f}%)")
                
                return {
                    'straddle_price': straddle_price,
                    'one_sd_move': one_sd_move,
                    'one_sd_pct': one_sd_pct,
                    'two_sd_move': one_sd_move * 2,
                    'two_sd_pct': one_sd_pct * 2,
                    'daily_move': daily_move,
                    'daily_pct': daily_pct,
                    'upper_expected': spot_price + one_sd_move,
                    'lower_expected': spot_price - one_sd_move,
                    'upper_2sd': spot_price + (one_sd_move * 2),
                    'lower_2sd': spot_price - (one_sd_move * 2)
                }
            
            # Fallback calculation using IV if available
            return self._expected_move_from_iv(options_df, spot_price)
            
        except Exception as e:
            logger.error(f"Error calculating expected moves: {e}")
            return self._default_expected_moves(spot_price)
    
    def _expected_move_from_iv(self, options_df: pd.DataFrame, spot_price: float) -> Dict:
        """Calculate expected move from IV if straddle prices not available"""
        try:
            if 'iv' not in options_df.columns:
                return self._default_expected_moves(spot_price)
            
            # Use ATM IV
            atm_options = options_df[abs(options_df['strike'] - spot_price) <= spot_price * 0.02]
            if atm_options.empty:
                atm_iv = options_df['iv'].mean()
            else:
                atm_iv = atm_options['iv'].mean()
            
            # Convert IV to expected move (assuming weekly expiry)
            days_to_expiry = 7
            one_sd_pct = atm_iv * np.sqrt(days_to_expiry / 365)
            one_sd_move = spot_price * (one_sd_pct / 100)
            
            daily_pct = atm_iv / np.sqrt(365)
            daily_move = spot_price * (daily_pct / 100)
            
            return {
                'straddle_price': one_sd_move * 1.18,  # Approximation
                'one_sd_move': one_sd_move,
                'one_sd_pct': one_sd_pct,
                'two_sd_move': one_sd_move * 2,
                'two_sd_pct': one_sd_pct * 2,
                'daily_move': daily_move,
                'daily_pct': daily_pct,
                'upper_expected': spot_price + one_sd_move,
                'lower_expected': spot_price - one_sd_move,
                'upper_2sd': spot_price + (one_sd_move * 2),
                'lower_2sd': spot_price - (one_sd_move * 2),
                'method': 'iv_based'
            }
            
        except Exception as e:
            logger.error(f"Error calculating expected move from IV: {e}")
            return self._default_expected_moves(spot_price)
    
    def _analyze_max_pain(self, options_df: pd.DataFrame, spot_price: float) -> Dict:
        """Analyze max pain and spot position relative to it"""
        try:
            calls = options_df[options_df['option_type'] == 'CALL']
            puts = options_df[options_df['option_type'] == 'PUT']
            
            if calls.empty or puts.empty:
                return {'max_pain': spot_price, 'spot_vs_max_pain': 0, 'bias': 'Neutral'}
            
            # Calculate max pain
            strikes = pd.concat([calls['strike'], puts['strike']]).unique()
            max_pain = self._calculate_max_pain_strike(calls, puts, strikes)
            
            # Spot vs max pain
            spot_vs_mp = ((spot_price - max_pain) / max_pain) * 100
            
            # Determine bias
            if spot_vs_mp > 3:
                bias = 'Bullish - Spot above max pain'
            elif spot_vs_mp < -3:
                bias = 'Bearish - Spot below max pain'
            else:
                bias = 'Neutral - Spot near max pain'
            
            # Pin risk analysis
            days_to_expiry = 7  # Assuming weekly
            pin_risk = 'High' if days_to_expiry <= 2 and abs(spot_vs_mp) < 2 else 'Low'
            
            logger.info(f"Max Pain: {max_pain}, Spot vs MP: {spot_vs_mp:.1f}%, Bias: {bias}")
            
            return {
                'max_pain': max_pain,
                'spot_vs_max_pain': spot_vs_mp,
                'bias': bias,
                'pin_risk': pin_risk,
                'convergence_expected': abs(spot_vs_mp) > 5
            }
            
        except Exception as e:
            logger.error(f"Error analyzing max pain: {e}")
            return {'max_pain': spot_price, 'spot_vs_max_pain': 0, 'bias': 'Unknown'}
    
    def _calculate_max_pain_strike(self, calls: pd.DataFrame, puts: pd.DataFrame, 
                                  strikes: np.ndarray) -> float:
        """Calculate the max pain strike price"""
        try:
            min_pain_value = float('inf')
            max_pain_strike = strikes[0] if len(strikes) > 0 else 0
            
            for strike in strikes:
                # ITM calls value at expiry
                itm_calls = calls[calls['strike'] < strike].copy()
                if not itm_calls.empty:
                    itm_calls['value'] = (strike - itm_calls['strike']) * itm_calls['open_interest']
                    call_pain = itm_calls['value'].sum()
                else:
                    call_pain = 0
                
                # ITM puts value at expiry
                itm_puts = puts[puts['strike'] > strike].copy()
                if not itm_puts.empty:
                    itm_puts['value'] = (itm_puts['strike'] - strike) * itm_puts['open_interest']
                    put_pain = itm_puts['value'].sum()
                else:
                    put_pain = 0
                
                total_pain = call_pain + put_pain
                
                if total_pain < min_pain_value:
                    min_pain_value = total_pain
                    max_pain_strike = strike
            
            return max_pain_strike
            
        except Exception as e:
            logger.error(f"Error calculating max pain strike: {e}")
            return np.median(strikes) if len(strikes) > 0 else 0
    
    def _calculate_value_area(self, options_df: pd.DataFrame, spot_price: float) -> Dict:
        """Calculate value area based on volume distribution"""
        try:
            # Combine volume at each strike
            volume_profile = options_df.groupby('strike')['volume'].sum().sort_values(ascending=False)
            
            if volume_profile.empty:
                return self._default_value_area(spot_price)
            
            # Point of Control (highest volume strike)
            poc = volume_profile.index[0]
            
            # Value Area (70% of volume)
            total_volume = volume_profile.sum()
            cumsum_volume = 0
            value_area_strikes = []
            
            for strike, volume in volume_profile.items():
                cumsum_volume += volume
                value_area_strikes.append(strike)
                if cumsum_volume >= total_volume * 0.7:
                    break
            
            vah = max(value_area_strikes)  # Value Area High
            val = min(value_area_strikes)  # Value Area Low
            
            # Developing vs Established
            va_width = (vah - val) / spot_price
            va_type = 'Narrow' if va_width < 0.03 else 'Wide' if va_width > 0.06 else 'Normal'
            
            logger.info(f"Value Area: {val:.0f} - {vah:.0f}, POC: {poc}, Type: {va_type}")
            
            return {
                'poc': poc,
                'vah': vah,
                'val': val,
                'va_type': va_type,
                'va_width_pct': va_width * 100,
                'spot_in_va': val <= spot_price <= vah
            }
            
        except Exception as e:
            logger.error(f"Error calculating value area: {e}")
            return self._default_value_area(spot_price)
    
    def _combine_support_resistance(self, options_levels: Dict, technical_levels: Dict,
                                  max_pain: Dict, value_area: Dict) -> Dict:
        """Combine multiple sources of support/resistance"""
        try:
            # Collect all support levels
            support_levels = []
            if options_levels.get('oi_support'):
                support_levels.append(('OI', options_levels['oi_support'], 'strong'))
            if options_levels.get('volume_support'):
                support_levels.append(('Volume', options_levels['volume_support'], 'moderate'))
            if technical_levels.get('support'):
                support_levels.append(('Technical', technical_levels['support'], 'strong'))
            if value_area.get('val'):
                support_levels.append(('VAL', value_area['val'], 'moderate'))
            
            # Collect all resistance levels
            resistance_levels = []
            if options_levels.get('oi_resistance'):
                resistance_levels.append(('OI', options_levels['oi_resistance'], 'strong'))
            if options_levels.get('volume_resistance'):
                resistance_levels.append(('Volume', options_levels['volume_resistance'], 'moderate'))
            if technical_levels.get('resistance'):
                resistance_levels.append(('Technical', technical_levels['resistance'], 'strong'))
            if value_area.get('vah'):
                resistance_levels.append(('VAH', value_area['vah'], 'moderate'))
            
            # Add max pain as a key level
            if max_pain.get('max_pain'):
                mp = max_pain['max_pain']
                support_levels.append(('MaxPain', mp, 'moderate'))
                resistance_levels.append(('MaxPain', mp, 'moderate'))
            
            # Sort and deduplicate
            support_levels = sorted(support_levels, key=lambda x: x[1])
            resistance_levels = sorted(resistance_levels, key=lambda x: x[1], reverse=True)
            
            # Find strongest levels
            short_term_support = self._find_strongest_level(support_levels, 'support', near_term=True)
            short_term_resistance = self._find_strongest_level(resistance_levels, 'resistance', near_term=True)
            
            mid_term_support = self._find_strongest_level(support_levels, 'support', near_term=False)
            mid_term_resistance = self._find_strongest_level(resistance_levels, 'resistance', near_term=False)
            
            # Create key levels list
            key_levels = []
            for source, level, strength in support_levels[:3]:
                key_levels.append({
                    'level': level,
                    'type': 'support',
                    'source': source,
                    'strength': strength
                })
            for source, level, strength in resistance_levels[:3]:
                key_levels.append({
                    'level': level,
                    'type': 'resistance',
                    'source': source,
                    'strength': strength
                })
            
            return {
                'short_term_support': short_term_support['level'],
                'short_term_resistance': short_term_resistance['level'],
                'short_term_strength': f"{short_term_support['strength']}/{short_term_resistance['strength']}",
                'mid_term_support': mid_term_support['level'],
                'mid_term_resistance': mid_term_resistance['level'],
                'mid_term_strength': f"{mid_term_support['strength']}/{mid_term_resistance['strength']}",
                'key_levels': sorted(key_levels, key=lambda x: x['level'])
            }
            
        except Exception as e:
            logger.error(f"Error combining support/resistance: {e}")
            return self._default_combined_levels(options_levels.get('oi_support', 0))
    
    def _find_strongest_level(self, levels: List[Tuple], level_type: str, near_term: bool) -> Dict:
        """Find the strongest support/resistance level"""
        try:
            if not levels:
                return {'level': 0, 'strength': 'weak', 'source': 'none'}
            
            # Filter for near-term (exclude technical for short-term)
            if near_term:
                filtered = [l for l in levels if l[0] != 'Technical']
            else:
                filtered = levels
            
            if not filtered:
                filtered = levels
            
            # Prioritize strong levels
            strong_levels = [l for l in filtered if l[2] == 'strong']
            if strong_levels:
                return {
                    'level': strong_levels[0][1],
                    'strength': 'strong',
                    'source': strong_levels[0][0]
                }
            
            # Otherwise take the first available
            return {
                'level': filtered[0][1],
                'strength': filtered[0][2],
                'source': filtered[0][0]
            }
            
        except Exception as e:
            logger.error(f"Error finding strongest level: {e}")
            return {'level': 0, 'strength': 'weak', 'source': 'error'}
    
    def _calculate_price_targets(self, spot_price: float, expected_moves: Dict,
                               combined_levels: Dict, technical_data: Dict = None) -> Dict:
        """Calculate price targets based on various methods"""
        try:
            targets = {
                'bullish': {},
                'bearish': {}
            }
            
            # Expected move targets
            targets['bullish']['expected_1sd'] = expected_moves.get('upper_expected', spot_price * 1.02)
            targets['bullish']['expected_2sd'] = expected_moves.get('upper_2sd', spot_price * 1.04)
            targets['bearish']['expected_1sd'] = expected_moves.get('lower_expected', spot_price * 0.98)
            targets['bearish']['expected_2sd'] = expected_moves.get('lower_2sd', spot_price * 0.96)
            
            # Resistance/Support targets
            targets['bullish']['resistance_1'] = combined_levels.get('short_term_resistance', spot_price * 1.03)
            targets['bullish']['resistance_2'] = combined_levels.get('mid_term_resistance', spot_price * 1.05)
            targets['bearish']['support_1'] = combined_levels.get('short_term_support', spot_price * 0.97)
            targets['bearish']['support_2'] = combined_levels.get('mid_term_support', spot_price * 0.95)
            
            # Technical targets if available
            if technical_data and 'target' in technical_data:
                targets['bullish']['technical'] = technical_data['target']
            if technical_data and 'stop_loss' in technical_data:
                targets['bearish']['technical'] = technical_data['stop_loss']
            
            # Consensus targets
            bullish_targets = [v for v in targets['bullish'].values() if v > spot_price]
            bearish_targets = [v for v in targets['bearish'].values() if v < spot_price]
            
            targets['consensus'] = {
                'bullish_target': np.mean(bullish_targets) if bullish_targets else spot_price * 1.03,
                'bearish_target': np.mean(bearish_targets) if bearish_targets else spot_price * 0.97
            }
            
            return targets
            
        except Exception as e:
            logger.error(f"Error calculating price targets: {e}")
            return {
                'bullish': {'expected_1sd': spot_price * 1.02},
                'bearish': {'expected_1sd': spot_price * 0.98},
                'consensus': {
                    'bullish_target': spot_price * 1.03,
                    'bearish_target': spot_price * 0.97
                }
            }
    
    def _analyze_spot_position(self, spot_price: float, combined_levels: Dict,
                             max_pain: Dict) -> Dict:
        """Analyze current spot position relative to key levels"""
        try:
            position_analysis = {
                'description': '',
                'bias': 'Neutral',
                'key_observations': []
            }
            
            # Position vs support/resistance
            short_support = combined_levels.get('short_term_support', 0)
            short_resistance = combined_levels.get('short_term_resistance', float('inf'))
            
            if spot_price <= short_support * 1.01:
                position_analysis['description'] = 'At/Near Support'
                position_analysis['bias'] = 'Bullish'
                position_analysis['key_observations'].append('Testing support level')
            elif spot_price >= short_resistance * 0.99:
                position_analysis['description'] = 'At/Near Resistance'
                position_analysis['bias'] = 'Bearish'
                position_analysis['key_observations'].append('Testing resistance level')
            else:
                sr_range = short_resistance - short_support
                position_in_range = (spot_price - short_support) / sr_range if sr_range > 0 else 0.5
                
                if position_in_range > 0.7:
                    position_analysis['description'] = 'Upper Range'
                    position_analysis['bias'] = 'Slightly Bearish'
                elif position_in_range < 0.3:
                    position_analysis['description'] = 'Lower Range'
                    position_analysis['bias'] = 'Slightly Bullish'
                else:
                    position_analysis['description'] = 'Mid Range'
                    position_analysis['bias'] = 'Neutral'
            
            # Max pain consideration
            if max_pain.get('convergence_expected'):
                position_analysis['key_observations'].append(
                    f"Max pain convergence expected towards {max_pain.get('max_pain', spot_price)}"
                )
            
            # Key levels proximity
            for level_info in combined_levels.get('key_levels', []):
                level = level_info['level']
                if abs(spot_price - level) / spot_price < 0.01:  # Within 1%
                    position_analysis['key_observations'].append(
                        f"Near {level_info['type']} at {level} ({level_info['source']})"
                    )
            
            return position_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing spot position: {e}")
            return {
                'description': 'Unknown',
                'bias': 'Neutral',
                'key_observations': []
            }
    
    def _default_options_levels(self, spot_price: float) -> Dict:
        """Return default options levels when calculation fails"""
        return {
            'oi_resistance': spot_price * 1.05,
            'oi_support': spot_price * 0.95,
            'volume_resistance': spot_price * 1.03,
            'volume_support': spot_price * 0.97,
            'resistance_strikes': [],
            'support_strikes': []
        }
    
    def _default_expected_moves(self, spot_price: float) -> Dict:
        """Return default expected moves when calculation fails"""
        daily_move = spot_price * 0.015  # 1.5% daily
        weekly_move = daily_move * np.sqrt(7)
        
        return {
            'straddle_price': weekly_move * 1.18,
            'one_sd_move': weekly_move,
            'one_sd_pct': (weekly_move / spot_price) * 100,
            'two_sd_move': weekly_move * 2,
            'two_sd_pct': (weekly_move * 2 / spot_price) * 100,
            'daily_move': daily_move,
            'daily_pct': 1.5,
            'upper_expected': spot_price + weekly_move,
            'lower_expected': spot_price - weekly_move,
            'upper_2sd': spot_price + (weekly_move * 2),
            'lower_2sd': spot_price - (weekly_move * 2),
            'method': 'default'
        }
    
    def _default_value_area(self, spot_price: float) -> Dict:
        """Return default value area when calculation fails"""
        return {
            'poc': spot_price,
            'vah': spot_price * 1.02,
            'val': spot_price * 0.98,
            'va_type': 'Unknown',
            'va_width_pct': 4.0,
            'spot_in_va': True
        }
    
    def _default_combined_levels(self, base_price: float) -> Dict:
        """Return default combined levels when calculation fails"""
        if base_price == 0:
            base_price = 100  # Fallback
            
        return {
            'short_term_support': base_price * 0.97,
            'short_term_resistance': base_price * 1.03,
            'short_term_strength': 'weak/weak',
            'mid_term_support': base_price * 0.95,
            'mid_term_resistance': base_price * 1.05,
            'mid_term_strength': 'weak/weak',
            'key_levels': []
        }
    
    def _default_price_levels(self, spot_price: float) -> Dict:
        """Return default price levels analysis when calculation fails"""
        return {
            'short_term': {
                'support': spot_price * 0.97,
                'resistance': spot_price * 1.03,
                'strength': 'weak/weak',
                'timeframe': '1-5 days'
            },
            'mid_term': {
                'support': spot_price * 0.95,
                'resistance': spot_price * 1.05,
                'strength': 'weak/weak',
                'timeframe': '10-30 days'
            },
            'expected_moves': self._default_expected_moves(spot_price),
            'max_pain': {'max_pain': spot_price, 'spot_vs_max_pain': 0, 'bias': 'Neutral'},
            'value_area': self._default_value_area(spot_price),
            'price_targets': {
                'bullish': {'expected_1sd': spot_price * 1.02},
                'bearish': {'expected_1sd': spot_price * 0.98},
                'consensus': {
                    'bullish_target': spot_price * 1.03,
                    'bearish_target': spot_price * 0.97
                }
            },
            'key_levels': [],
            'spot_position': {
                'description': 'Unknown',
                'bias': 'Neutral',
                'key_observations': []
            }
        }