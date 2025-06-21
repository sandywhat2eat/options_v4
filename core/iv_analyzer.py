"""
IV Analyzer with realistic limitations for current point-in-time IV data
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, Optional, Tuple, List

logger = logging.getLogger(__name__)

class IVAnalyzer:
    """
    Analyzes Implied Volatility with current data limitations
    
    NOTE: This implementation works with point-in-time IV only.
    Historical IV percentiles require separate data collection.
    """
    
    def __init__(self):
        # Conservative IV assumptions without historical data
        self.iv_assumptions = {
            'low_iv_threshold': 20.0,
            'high_iv_threshold': 45.0,
            'normal_iv_range': (25.0, 40.0),
            'extreme_iv_threshold': 60.0
        }
        
        # Sector-specific IV ranges (based on typical Indian market behavior)
        self.sector_iv_ranges = {
            'IT': {'low': 18, 'normal': (20, 35), 'high': 40},
            'Banking': {'low': 22, 'normal': (25, 40), 'high': 45},
            'Pharma': {'low': 20, 'normal': (22, 38), 'high': 42},
            'Auto': {'low': 20, 'normal': (23, 38), 'high': 42},
            'FMCG': {'low': 15, 'normal': (18, 30), 'high': 35},
            'Metals': {'low': 25, 'normal': (28, 45), 'high': 50},
            'Realty': {'low': 25, 'normal': (28, 48), 'high': 55},
            'Energy': {'low': 22, 'normal': (25, 42), 'high': 48},
            'default': {'low': 20, 'normal': (25, 40), 'high': 45}
        }
    
    def analyze_current_iv(self, options_df: pd.DataFrame, symbol: str, 
                          sector: str = None, historical_iv: Dict = None) -> Dict:
        """Analyze current IV environment with available data"""
        try:
            if options_df is None or options_df.empty:
                return self._default_iv_analysis()
            
            # Get ATM IV (most representative)
            atm_iv = self._get_atm_iv(options_df)
            
            # Calculate IV skew with enhanced metrics
            iv_skew = self._calculate_iv_skew_enhanced(options_df)
            
            # Calculate term structure
            term_structure = self._analyze_term_structure(options_df)
            
            # Calculate IV relativity (vs sector/market)
            iv_relativity = self._calculate_iv_relativity(atm_iv, sector, options_df)
            
            # Enhanced percentile calculation
            percentile_analysis = self._calculate_iv_percentile_enhanced(
                atm_iv, sector, historical_iv
            )
            
            # Categorize IV environment with context
            iv_environment = self._categorize_iv_environment_enhanced(
                atm_iv, sector, percentile_analysis['percentile']
            )
            
            # IV mean reversion analysis
            mean_reversion = self._analyze_iv_mean_reversion(
                atm_iv, percentile_analysis, iv_relativity
            )
            
            # Get strategy recommendations
            recommendations = self._get_enhanced_strategy_recommendations(
                atm_iv, iv_environment, iv_skew, mean_reversion
            )
            
            return {
                'atm_iv': atm_iv,
                'iv_skew': iv_skew,
                'term_structure': term_structure,
                'iv_environment': iv_environment,
                'percentile_analysis': percentile_analysis,
                'iv_relativity': iv_relativity,
                'mean_reversion': mean_reversion,
                'call_put_iv_diff': self._get_call_put_iv_difference(options_df),
                'analysis_quality': self._determine_analysis_quality(historical_iv),
                'recommendations': recommendations
            }
            
        except Exception as e:
            logger.error(f"Error analyzing IV for {symbol}: {e}")
            return self._default_iv_analysis()
    
    def _get_atm_iv(self, options_df: pd.DataFrame) -> float:
        """Get ATM implied volatility"""
        try:
            # Find spot price
            spot_price = options_df['spot_price'].iloc[0] if 'spot_price' in options_df.columns else None
            if spot_price is None:
                return options_df['iv'].median()
            
            # Find closest strike to spot
            options_df['strike_diff'] = abs(options_df['strike'] - spot_price)
            atm_options = options_df.nsmallest(10, 'strike_diff')  # Top 10 closest
            
            return atm_options['iv'].mean()
            
        except Exception as e:
            logger.error(f"Error getting ATM IV: {e}")
            return options_df['iv'].median() if not options_df.empty else 30.0
    
    def _calculate_iv_skew(self, options_df: pd.DataFrame) -> Dict:
        """Calculate IV skew patterns"""
        try:
            calls = options_df[options_df['option_type'] == 'CALL']
            puts = options_df[options_df['option_type'] == 'PUT']
            
            if calls.empty or puts.empty:
                return {'skew_type': 'insufficient_data', 'skew_strength': 0.0}
            
            # Simple skew calculation
            otm_calls_iv = calls[calls['strike'] > calls['spot_price'].iloc[0]]['iv'].mean()
            otm_puts_iv = puts[puts['strike'] < puts['spot_price'].iloc[0]]['iv'].mean()
            
            if pd.isna(otm_calls_iv) or pd.isna(otm_puts_iv):
                return {'skew_type': 'normal', 'skew_strength': 0.0}
            
            skew_diff = otm_puts_iv - otm_calls_iv
            
            if skew_diff > 2.0:
                skew_type = 'put_skew'
            elif skew_diff < -2.0:
                skew_type = 'call_skew'
            else:
                skew_type = 'normal'
            
            return {
                'skew_type': skew_type,
                'skew_strength': abs(skew_diff),
                'put_iv': otm_puts_iv,
                'call_iv': otm_calls_iv
            }
            
        except Exception as e:
            logger.error(f"Error calculating IV skew: {e}")
            return {'skew_type': 'normal', 'skew_strength': 0.0}
    
    def _categorize_iv_environment(self, atm_iv: float) -> str:
        """Categorize current IV environment"""
        if atm_iv < self.iv_assumptions['low_iv_threshold']:
            return 'LOW'
        elif atm_iv > self.iv_assumptions['extreme_iv_threshold']:
            return 'EXTREME'
        elif atm_iv > self.iv_assumptions['high_iv_threshold']:
            return 'HIGH'
        elif self.iv_assumptions['normal_iv_range'][0] <= atm_iv <= self.iv_assumptions['normal_iv_range'][1]:
            return 'NORMAL'
        else:
            return 'MODERATE'
    
    def _estimate_iv_percentile(self, atm_iv: float) -> int:
        """
        Rough IV percentile estimation without historical data
        
        This is a crude approximation based on common IV ranges.
        Should be replaced with proper historical percentile calculation.
        """
        if atm_iv < 15:
            return 5
        elif atm_iv < 20:
            return 15
        elif atm_iv < 25:
            return 30
        elif atm_iv < 30:
            return 45
        elif atm_iv < 35:
            return 60
        elif atm_iv < 45:
            return 75
        elif atm_iv < 60:
            return 85
        else:
            return 95
    
    def _get_call_put_iv_difference(self, options_df: pd.DataFrame) -> float:
        """Calculate average IV difference between calls and puts"""
        try:
            calls_iv = options_df[options_df['option_type'] == 'CALL']['iv'].mean()
            puts_iv = options_df[options_df['option_type'] == 'PUT']['iv'].mean()
            
            if pd.isna(calls_iv) or pd.isna(puts_iv):
                return 0.0
            
            return calls_iv - puts_iv
            
        except Exception as e:
            logger.error(f"Error calculating call-put IV difference: {e}")
            return 0.0
    
    def _get_iv_strategy_recommendations(self, atm_iv: float, iv_environment: str) -> Dict:
        """Get strategy recommendations based on IV environment"""
        recommendations = {
            'LOW': {
                'preferred_strategies': ['Long Straddle', 'Long Strangle', 'Long Call', 'Long Put'],
                'avoid_strategies': ['Short Straddle', 'Iron Condor', 'Short Strangle'],
                'reasoning': 'Low IV - Buy volatility'
            },
            'HIGH': {
                'preferred_strategies': ['Iron Condor', 'Short Straddle', 'Credit Spreads'],
                'avoid_strategies': ['Long Straddle', 'Long Options'],
                'reasoning': 'High IV - Sell volatility'
            },
            'NORMAL': {
                'preferred_strategies': ['Bull/Bear Spreads', 'Iron Condor', 'Calendar Spreads'],
                'avoid_strategies': [],
                'reasoning': 'Normal IV - Directional or neutral strategies'
            },
            'EXTREME': {
                'preferred_strategies': ['Iron Condor', 'Iron Butterfly', 'Short Straddle'],
                'avoid_strategies': ['Long Volatility'],
                'reasoning': 'Extreme IV - Aggressive volatility selling'
            }
        }
        
        return recommendations.get(iv_environment, recommendations['NORMAL'])
    
    def _calculate_iv_skew_enhanced(self, options_df: pd.DataFrame) -> Dict:
        """Enhanced IV skew calculation with multiple metrics"""
        try:
            spot_price = options_df['spot_price'].iloc[0] if 'spot_price' in options_df.columns else None
            if spot_price is None:
                return self._calculate_iv_skew(options_df)
            
            calls = options_df[options_df['option_type'] == 'CALL']
            puts = options_df[options_df['option_type'] == 'PUT']
            
            if calls.empty or puts.empty:
                return {'skew_type': 'insufficient_data', 'skew_strength': 0.0}
            
            # Calculate 25-delta skew (approximation)
            otm_call_strikes = calls[calls['strike'] > spot_price * 1.03]
            otm_put_strikes = puts[puts['strike'] < spot_price * 0.97]
            
            otm_calls_iv = otm_call_strikes['iv'].mean() if not otm_call_strikes.empty else calls['iv'].mean()
            otm_puts_iv = otm_put_strikes['iv'].mean() if not otm_put_strikes.empty else puts['iv'].mean()
            atm_iv = self._get_atm_iv(options_df)
            
            # Risk reversal (25 delta)
            risk_reversal = otm_calls_iv - otm_puts_iv
            
            # Butterfly (25 delta)
            butterfly = ((otm_calls_iv + otm_puts_iv) / 2) - atm_iv
            
            # Skew classification
            skew_diff = otm_puts_iv - otm_calls_iv
            if skew_diff > 3.0:
                skew_type = 'put_skew'
                market_sentiment = 'Fearful - Downside protection demand'
            elif skew_diff < -3.0:
                skew_type = 'call_skew'
                market_sentiment = 'Greedy - Upside speculation'
            else:
                skew_type = 'normal'
                market_sentiment = 'Balanced'
            
            # Skew steepness
            skew_steepness = 'Steep' if abs(skew_diff) > 5 else 'Moderate' if abs(skew_diff) > 2 else 'Flat'
            
            return {
                'skew_type': skew_type,
                'skew_strength': abs(skew_diff),
                'put_iv': otm_puts_iv,
                'call_iv': otm_calls_iv,
                'risk_reversal': risk_reversal,
                'butterfly': butterfly,
                'market_sentiment': market_sentiment,
                'skew_steepness': skew_steepness
            }
            
        except Exception as e:
            logger.error(f"Error calculating enhanced IV skew: {e}")
            return self._calculate_iv_skew(options_df)
    
    def _analyze_term_structure(self, options_df: pd.DataFrame) -> Dict:
        """Analyze IV term structure across expiries"""
        try:
            # If we only have one expiry, return simple analysis
            if 'expiry' not in options_df.columns or options_df['expiry'].nunique() <= 1:
                return {
                    'structure': 'Single expiry only',
                    'front_month_iv': self._get_atm_iv(options_df),
                    'calendar_spread_opportunity': 'Unknown',
                    'volatility_expectation': 'Stable'
                }
            
            # Group by expiry and calculate ATM IV for each
            expiry_ivs = {}
            for expiry in sorted(options_df['expiry'].unique()):
                expiry_df = options_df[options_df['expiry'] == expiry]
                expiry_ivs[expiry] = self._get_atm_iv(expiry_df)
            
            # Analyze structure
            iv_values = list(expiry_ivs.values())
            if len(iv_values) >= 2:
                if iv_values[0] > iv_values[1] * 1.1:
                    structure = 'Backwardation'
                    volatility_expectation = 'Near-term event expected'
                elif iv_values[1] > iv_values[0] * 1.1:
                    structure = 'Contango'
                    volatility_expectation = 'Future uncertainty'
                else:
                    structure = 'Flat'
                    volatility_expectation = 'Stable'
                    
                calendar_opportunity = 'Yes' if abs(iv_values[0] - iv_values[1]) > 5 else 'Limited'
            else:
                structure = 'Insufficient data'
                volatility_expectation = 'Unknown'
                calendar_opportunity = 'Unknown'
            
            return {
                'structure': structure,
                'front_month_iv': iv_values[0] if iv_values else None,
                'back_month_iv': iv_values[1] if len(iv_values) > 1 else None,
                'calendar_spread_opportunity': calendar_opportunity,
                'volatility_expectation': volatility_expectation
            }
            
        except Exception as e:
            logger.error(f"Error analyzing term structure: {e}")
            return {
                'structure': 'Unknown',
                'front_month_iv': self._get_atm_iv(options_df),
                'calendar_spread_opportunity': 'Unknown',
                'volatility_expectation': 'Unknown'
            }
    
    def _calculate_iv_relativity(self, atm_iv: float, sector: str, 
                                options_df: pd.DataFrame) -> Dict:
        """Calculate IV relative to sector and market norms"""
        try:
            # Get sector-specific ranges
            sector_ranges = self.sector_iv_ranges.get(sector, self.sector_iv_ranges['default'])
            
            # Calculate position within sector range
            normal_low, normal_high = sector_ranges['normal']
            
            if atm_iv < sector_ranges['low']:
                sector_relative = 'Very Low'
                percentile_in_sector = 10
            elif atm_iv < normal_low:
                sector_relative = 'Low'
                percentile_in_sector = 25
            elif atm_iv <= normal_high:
                sector_relative = 'Normal'
                # Linear interpolation within normal range
                percentile_in_sector = 40 + ((atm_iv - normal_low) / (normal_high - normal_low)) * 30
            elif atm_iv <= sector_ranges['high']:
                sector_relative = 'High'
                percentile_in_sector = 75
            else:
                sector_relative = 'Very High'
                percentile_in_sector = 90
            
            # Market-wide comparison (simplified)
            market_avg_iv = 28.0  # Typical Nifty IV
            iv_vs_market = ((atm_iv - market_avg_iv) / market_avg_iv) * 100
            
            # Relative value assessment
            if iv_vs_market > 20:
                market_relative = 'Premium to market'
            elif iv_vs_market < -20:
                market_relative = 'Discount to market'
            else:
                market_relative = 'In-line with market'
            
            return {
                'sector_relative': sector_relative,
                'percentile_in_sector': percentile_in_sector,
                'market_relative': market_relative,
                'iv_vs_market_pct': iv_vs_market,
                'sector_normal_range': sector_ranges['normal'],
                'interpretation': self._interpret_iv_relativity(sector_relative, market_relative)
            }
            
        except Exception as e:
            logger.error(f"Error calculating IV relativity: {e}")
            return {
                'sector_relative': 'Unknown',
                'percentile_in_sector': 50,
                'market_relative': 'Unknown',
                'iv_vs_market_pct': 0,
                'interpretation': 'Unable to determine relative value'
            }
    
    def _calculate_iv_percentile_enhanced(self, atm_iv: float, sector: str, 
                                        historical_iv: Dict = None) -> Dict:
        """Enhanced IV percentile calculation"""
        try:
            # If we have historical data, use it
            if historical_iv and 'percentile' in historical_iv:
                return {
                    'percentile': historical_iv['percentile'],
                    'method': 'historical',
                    'lookback_days': historical_iv.get('lookback_days', 252),
                    'iv_range': historical_iv.get('iv_range', (15, 60)),
                    'current_rank': historical_iv.get('rank', 'Medium')
                }
            
            # Otherwise use sector-adjusted estimation
            sector_ranges = self.sector_iv_ranges.get(sector, self.sector_iv_ranges['default'])
            
            # More sophisticated percentile estimation
            if atm_iv < sector_ranges['low'] * 0.8:
                percentile = 5
                rank = 'Very Low'
            elif atm_iv < sector_ranges['low']:
                percentile = 15 + ((atm_iv - sector_ranges['low'] * 0.8) / 
                                 (sector_ranges['low'] * 0.2)) * 10
                rank = 'Low'
            elif atm_iv < sector_ranges['normal'][0]:
                percentile = 25 + ((atm_iv - sector_ranges['low']) / 
                                 (sector_ranges['normal'][0] - sector_ranges['low'])) * 15
                rank = 'Below Normal'
            elif atm_iv <= sector_ranges['normal'][1]:
                percentile = 40 + ((atm_iv - sector_ranges['normal'][0]) / 
                                 (sector_ranges['normal'][1] - sector_ranges['normal'][0])) * 30
                rank = 'Normal'
            elif atm_iv <= sector_ranges['high']:
                percentile = 70 + ((atm_iv - sector_ranges['normal'][1]) / 
                                 (sector_ranges['high'] - sector_ranges['normal'][1])) * 15
                rank = 'High'
            else:
                percentile = 85 + min(((atm_iv - sector_ranges['high']) / 
                                     sector_ranges['high']) * 30, 14)
                rank = 'Very High'
            
            return {
                'percentile': int(percentile),
                'method': 'sector_adjusted_estimation',
                'lookback_days': 0,
                'iv_range': (sector_ranges['low'], sector_ranges['high']),
                'current_rank': rank,
                'confidence': 'Low - No historical data'
            }
            
        except Exception as e:
            logger.error(f"Error calculating enhanced IV percentile: {e}")
            return {
                'percentile': self._estimate_iv_percentile(atm_iv),
                'method': 'simple_estimation',
                'current_rank': 'Unknown'
            }
    
    def _categorize_iv_environment_enhanced(self, atm_iv: float, sector: str, 
                                          percentile: int) -> str:
        """Enhanced IV environment categorization"""
        try:
            # Combine absolute IV levels with percentile ranking
            if percentile < 20:
                return 'LOW'
            elif percentile > 80:
                return 'HIGH' if atm_iv < 60 else 'EXTREME'
            elif percentile > 60:
                return 'ELEVATED'
            elif percentile < 40:
                return 'SUBDUED'
            else:
                return 'NORMAL'
                
        except Exception as e:
            logger.error(f"Error categorizing IV environment: {e}")
            return self._categorize_iv_environment(atm_iv)
    
    def _analyze_iv_mean_reversion(self, atm_iv: float, percentile_analysis: Dict,
                                  iv_relativity: Dict) -> Dict:
        """Analyze IV mean reversion potential"""
        try:
            percentile = percentile_analysis['percentile']
            
            # Mean reversion signals
            if percentile > 80:
                reversion_potential = 'High - IV likely to decrease'
                reversion_direction = 'Down'
                confidence = 0.7
            elif percentile < 20:
                reversion_potential = 'High - IV likely to increase'
                reversion_direction = 'Up'
                confidence = 0.7
            elif percentile > 65:
                reversion_potential = 'Moderate - Some downward pressure'
                reversion_direction = 'Down'
                confidence = 0.5
            elif percentile < 35:
                reversion_potential = 'Moderate - Some upward pressure'
                reversion_direction = 'Up'
                confidence = 0.5
            else:
                reversion_potential = 'Low - IV near mean'
                reversion_direction = 'Neutral'
                confidence = 0.3
            
            # Expected IV range (simplified)
            current_rank = percentile_analysis.get('current_rank', 'Normal')
            iv_range = percentile_analysis.get('iv_range', (20, 45))
            
            if reversion_direction == 'Down':
                expected_iv = atm_iv * 0.85 if percentile > 80 else atm_iv * 0.92
            elif reversion_direction == 'Up':
                expected_iv = atm_iv * 1.15 if percentile < 20 else atm_iv * 1.08
            else:
                expected_iv = atm_iv
            
            return {
                'reversion_potential': reversion_potential,
                'direction': reversion_direction,
                'confidence': confidence,
                'expected_iv': expected_iv,
                'time_horizon': '10-30 days',
                'strategy_implication': self._get_reversion_strategy(reversion_direction, percentile)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing IV mean reversion: {e}")
            return {
                'reversion_potential': 'Unknown',
                'direction': 'Neutral',
                'confidence': 0.0
            }
    
    def _get_reversion_strategy(self, direction: str, percentile: int) -> str:
        """Get strategy recommendation based on mean reversion"""
        if direction == 'Down' and percentile > 70:
            return 'Sell volatility - Iron Condor, Short Straddle'
        elif direction == 'Up' and percentile < 30:
            return 'Buy volatility - Long Straddle, Calendar Spread'
        else:
            return 'Directional strategies preferred'
    
    def _get_enhanced_strategy_recommendations(self, atm_iv: float, iv_environment: str,
                                             iv_skew: Dict, mean_reversion: Dict) -> Dict:
        """Enhanced strategy recommendations with multiple factors"""
        try:
            # Base recommendations on IV environment
            base_recommendations = self._get_iv_strategy_recommendations(atm_iv, iv_environment)
            
            # Adjust for skew
            if iv_skew['skew_type'] == 'put_skew' and iv_skew['skew_strength'] > 5:
                base_recommendations['skew_strategies'] = ['Put Ratio Spread', 'Jade Lizard']
                base_recommendations['skew_note'] = 'Put skew creates ratio spread opportunities'
            elif iv_skew['skew_type'] == 'call_skew' and iv_skew['skew_strength'] > 5:
                base_recommendations['skew_strategies'] = ['Call Ratio Spread', 'Call Butterfly']
                base_recommendations['skew_note'] = 'Call skew favors upside ratio trades'
            
            # Adjust for mean reversion
            if mean_reversion['confidence'] > 0.6:
                base_recommendations['mean_reversion_strategies'] = [
                    s for s in mean_reversion['strategy_implication'].split(', ')
                ]
                base_recommendations['time_sensitive'] = True
            
            # Priority ranking
            all_strategies = base_recommendations.get('preferred_strategies', [])
            if 'skew_strategies' in base_recommendations:
                all_strategies = base_recommendations['skew_strategies'] + all_strategies
            
            base_recommendations['ranked_strategies'] = all_strategies[:5]
            
            return base_recommendations
            
        except Exception as e:
            logger.error(f"Error getting enhanced strategy recommendations: {e}")
            return self._get_iv_strategy_recommendations(atm_iv, iv_environment)
    
    def _determine_analysis_quality(self, historical_iv: Dict = None) -> str:
        """Determine the quality of IV analysis"""
        if historical_iv and 'data_points' in historical_iv and historical_iv['data_points'] > 100:
            return 'HIGH - Historical data available'
        elif historical_iv:
            return 'MODERATE - Limited historical data'
        else:
            return 'CURRENT_ONLY - Point-in-time analysis'
    
    def _interpret_iv_relativity(self, sector_relative: str, market_relative: str) -> str:
        """Interpret IV relativity for trading decisions"""
        if sector_relative in ['Very Low', 'Low'] and 'Discount' in market_relative:
            return 'Attractive for volatility buying'
        elif sector_relative in ['Very High', 'High'] and 'Premium' in market_relative:
            return 'Attractive for volatility selling'
        elif sector_relative == 'Normal' and market_relative == 'In-line with market':
            return 'Fair value - focus on directional strategies'
        else:
            return 'Mixed signals - consider other factors'
    
    def _default_iv_analysis(self) -> Dict:
        """Return default IV analysis when data is insufficient"""
        return {
            'atm_iv': 30.0,
            'iv_skew': {'skew_type': 'normal', 'skew_strength': 0.0},
            'term_structure': {'structure': 'Unknown', 'volatility_expectation': 'Unknown'},
            'iv_environment': 'NORMAL',
            'percentile_analysis': {'percentile': 50, 'method': 'default', 'current_rank': 'Normal'},
            'iv_relativity': {'sector_relative': 'Normal', 'market_relative': 'In-line with market'},
            'mean_reversion': {'reversion_potential': 'Unknown', 'direction': 'Neutral'},
            'call_put_iv_diff': 0.0,
            'analysis_quality': 'DEFAULT',
            'recommendations': self._get_iv_strategy_recommendations(30.0, 'NORMAL')
        }