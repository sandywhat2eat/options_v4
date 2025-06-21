"""
Market Analyzer for direction and trend analysis
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, Optional, Tuple
import sys
import os

# Add parent directory to import technical analysis
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from .technical_analyzer import TechnicalAnalyzer

logger = logging.getLogger(__name__)

class MarketAnalyzer:
    """Analyzes market direction and trends for strategy selection"""
    
    def __init__(self):
        self.direction_thresholds = {
            'strong_bullish': 0.75,
            'moderate_bullish': 0.5,
            'weak_bullish': 0.25,
            'neutral': 0.0,
            'weak_bearish': -0.25,
            'moderate_bearish': -0.5,
            'strong_bearish': -0.75
        }
        self.technical_analyzer = TechnicalAnalyzer()
    
    def analyze_market_direction(self, symbol: str, options_df: pd.DataFrame, 
                               spot_price: float, stock_info: Dict = None) -> Dict:
        """
        Comprehensive market direction analysis matching original sophistication
        
        Args:
            symbol: Stock symbol
            options_df: Options chain data
            spot_price: Current spot price
            stock_info: Additional stock information (sector/industry IV)
        
        Returns:
            Dictionary with direction analysis
        """
        try:
            logger.info(f"\n=== Market Direction Analysis for {symbol} ===")
            
            # 1. Technical Analysis Component (40% weight)
            logger.info("\n1. Technical Analysis (40% weight):")
            logger.info("-" * 30)
            technical_score, technical_details = self._analyze_technical_indicators_enhanced(symbol, spot_price)
            
            # 2. Options Analysis Component (35% weight)
            logger.info("\n2. Options Data Analysis (35% weight):")
            logger.info("-" * 30)
            options_score, options_details = self._analyze_options_flow_enhanced(options_df, spot_price)
            
            # 3. Price Action Component (25% weight)
            logger.info("\n3. Price Action Analysis (25% weight):")
            logger.info("-" * 30)
            price_action_score, price_action_details = self._analyze_price_action_enhanced(options_df, spot_price)
            
            # 4. Calculate weighted final score
            weights = {
                'technical': 0.40,
                'options': 0.35,
                'price_action': 0.25
            }
            
            final_score = (
                technical_score * weights['technical'] +
                options_score * weights['options'] +
                price_action_score * weights['price_action']
            )
            
            logger.info("\n4. Final Direction Score Calculation:")
            logger.info("-" * 30)
            logger.info(f"Technical Score (40%): {technical_score:.2f}")
            logger.info(f"Options Score (35%): {options_score:.2f}")
            logger.info(f"Price Action Score (25%): {price_action_score:.2f}")
            logger.info(f"\nFinal Score: {final_score:.2f}")
            
            # 5. Determine direction and confidence
            direction, sub_category, confidence = self._interpret_direction_score_enhanced(final_score, technical_details)
            
            logger.info(f"\nMarket Direction: {direction} ({sub_category})")
            logger.info(f"Confidence: {confidence:.2%}")
            
            # 6. Estimate timeframe based on volatility and confidence
            timeframe_analysis = self._estimate_timeframe_enhanced(
                confidence, 
                technical_details.get('bb_width', 0.2),
                options_details.get('iv_environment', 'NORMAL')
            )
            
            return {
                'direction': direction,
                'sub_category': sub_category,
                'confidence': confidence,
                'final_score': final_score,
                'components': {
                    'technical_score': technical_score,
                    'options_score': options_score,
                    'price_action_score': price_action_score
                },
                'timeframe': timeframe_analysis,
                'strength': abs(final_score),
                'details': {
                    'technical': technical_details,
                    'options': options_details,
                    'price_action': price_action_details
                }
            }
            
        except Exception as e:
            logger.error(f"Error analyzing market direction for {symbol}: {e}")
            return self._default_direction_analysis()
    
    def _analyze_technical_indicators_enhanced(self, symbol: str, spot_price: float) -> Tuple[float, Dict]:
        """Enhanced technical analysis with detailed metrics"""
        try:
            # Get comprehensive technical analysis
            technical_analysis = self.technical_analyzer.analyze_technical_indicators(symbol)
            
            # Extract key metrics
            price_trend = technical_analysis.get('price_trend', {})
            momentum = technical_analysis.get('momentum', {})
            volume = technical_analysis.get('volume', {})
            volatility = technical_analysis.get('volatility', {})
            patterns = technical_analysis.get('patterns', {})
            
            # Calculate component scores
            
            # 1. Trend Score
            trend_score = 0
            if price_trend.get('trend') == 'Uptrend':
                trend_score = 0.7
                if price_trend.get('ema_alignment') == 'Bullish':
                    trend_score = 1.0
            elif price_trend.get('trend') == 'Downtrend':
                trend_score = -0.7
                if price_trend.get('ema_alignment') == 'Bearish':
                    trend_score = -1.0
            logger.info(f"Trend: {price_trend.get('trend')} → Score: {trend_score}")
            
            # 2. Momentum Score  
            rsi = momentum.get('rsi', 50)
            momentum_score = 0
            if rsi > 70:
                momentum_score = -0.5  # Overbought
            elif rsi < 30:
                momentum_score = 0.5   # Oversold
            else:
                momentum_score = (rsi - 50) / 100  # Normalized
                
            if momentum.get('macd_signal') == 'Bullish':
                momentum_score += 0.3
            elif momentum.get('macd_signal') == 'Bearish':
                momentum_score -= 0.3
            momentum_score = max(-1, min(1, momentum_score))
            logger.info(f"RSI: {rsi:.1f}, MACD: {momentum.get('macd_signal')} → Score: {momentum_score}")
            
            # 3. Volume Score
            volume_ratio = volume.get('volume_ratio', 1.0)
            volume_trend = volume.get('volume_trend', 'Unknown')
            volume_score = 0
            
            if volume_ratio > 1.5 and volume_trend == 'Increasing':
                volume_score = 0.5 if trend_score > 0 else -0.5
            elif volume_ratio < 0.5:
                volume_score = -0.3
            logger.info(f"Volume Ratio: {volume_ratio:.2f} → Score: {volume_score}")
            
            # 4. Support/Resistance Score
            price_position = technical_analysis.get('support_resistance', {}).get('price_position', 'Mid-Range')
            sr_score = 0
            if price_position == 'Near Support':
                sr_score = 0.5
            elif price_position == 'Near Resistance':
                sr_score = -0.5
            logger.info(f"Price Position: {price_position} → Score: {sr_score}")
            
            # Calculate final technical score
            technical_score = (
                trend_score * 0.4 +
                momentum_score * 0.3 +
                volume_score * 0.2 +
                sr_score * 0.1
            )
            
            logger.info(f"Final Technical Score: {technical_score:.2f}")
            
            # Extract details for response
            details = {
                'trend': price_trend.get('trend'),
                'ema_alignment': price_trend.get('ema_alignment'),
                'rsi': rsi,
                'macd_signal': momentum.get('macd_signal'),
                'volume_ratio': volume_ratio,
                'volume_trend': volume_trend,
                'bb_width': volatility.get('bollinger_position', 0.5),
                'atr': volatility.get('atr', 0),
                'price_position': price_position,
                'pattern': patterns.get('pattern', 'Unknown')
            }
            
            return technical_score, details
            
        except Exception as e:
            logger.error(f"Error in enhanced technical analysis: {e}")
            return 0.0, {}
    
    def _analyze_options_flow_enhanced(self, options_df: pd.DataFrame, spot_price: float) -> Tuple[float, Dict]:
        """Enhanced options flow analysis with detailed metrics"""
        try:
            if options_df.empty:
                return 0.0, {}
            
            # 1. Put-Call Ratio Analysis (Volume and OI)
            calls = options_df[options_df['option_type'] == 'CALL']
            puts = options_df[options_df['option_type'] == 'PUT']
            
            if calls.empty or puts.empty:
                return 0.0, {}
            
            # Volume-based PCR
            call_volume = calls['volume'].sum()
            put_volume = puts['volume'].sum()
            volume_pcr = put_volume / (call_volume + 1)  # Add 1 to avoid division by zero
            
            # OI-based PCR
            call_oi = calls['open_interest'].sum()
            put_oi = puts['open_interest'].sum()
            oi_pcr = put_oi / (call_oi + 1)
            
            logger.info(f"Volume PCR: {volume_pcr:.2f}, OI PCR: {oi_pcr:.2f}")
            
            # 2. ATM Options Analysis
            atm_analysis = self._analyze_atm_options(options_df, spot_price)
            atm_score = atm_analysis['activity_ratio']
            logger.info(f"ATM Activity Ratio: {atm_score:.2f} (Call vs Put)")
            
            # 3. Options Skew Analysis
            skew_analysis = self._analyze_options_skew_enhanced(calls, puts, spot_price)
            skew_score = skew_analysis['skew_score']
            logger.info(f"IV Skew: {skew_analysis['iv_skew']}, Score: {skew_score:.2f}")
            
            # 4. OI Distribution Analysis
            oi_distribution = self._analyze_oi_distribution(calls, puts, spot_price)
            oi_score = oi_distribution['directional_bias']
            logger.info(f"OI Distribution Bias: {oi_score:.2f}")
            
            # 5. Options Flow Intensity
            flow_intensity = self._analyze_flow_intensity(options_df)
            logger.info(f"Flow Intensity: {flow_intensity['intensity']}")
            
            # 6. Smart Money Analysis (large trades)
            smart_money = self._analyze_smart_money_flow(options_df, spot_price)
            smart_money_score = smart_money['smart_money_bias']
            logger.info(f"Smart Money Bias: {smart_money_score:.2f}")
            
            # Combine components with weights
            pcr_score = self._interpret_pcr(volume_pcr, oi_pcr)
            
            options_score = (
                pcr_score * 0.25 +
                atm_score * 0.20 +
                skew_score * 0.20 +
                oi_score * 0.15 +
                smart_money_score * 0.20
            )
            
            logger.info(f"Final Options Score: {options_score:.2f}")
            
            # Compile detailed metrics
            details = {
                'volume_pcr': volume_pcr,
                'oi_pcr': oi_pcr,
                'pcr_interpretation': self._get_pcr_interpretation(volume_pcr, oi_pcr),
                'atm_call_volume': atm_analysis['call_activity'],
                'atm_put_volume': atm_analysis['put_activity'],
                'atm_bias': 'Bullish' if atm_score > 0 else 'Bearish' if atm_score < 0 else 'Neutral',
                'iv_skew': skew_analysis['iv_skew'],
                'iv_skew_type': skew_analysis['skew_type'],
                'oi_max_pain': oi_distribution['max_pain'],
                'oi_support': oi_distribution['major_support'],
                'oi_resistance': oi_distribution['major_resistance'],
                'flow_intensity': flow_intensity['intensity'],
                'unusual_activity': flow_intensity['unusual_strikes'],
                'smart_money_direction': smart_money['direction'],
                'iv_environment': self._classify_iv_environment(options_df)
            }
            
            return max(-1.0, min(1.0, options_score)), details
            
        except Exception as e:
            logger.error(f"Error in enhanced options flow analysis: {e}")
            return 0.0, {}
    
    def _analyze_options_flow(self, options_df: pd.DataFrame, spot_price: float) -> float:
        """Analyze options flow and sentiment"""
        try:
            if options_df.empty:
                return 0.0
            
            # 1. Put-Call Ratio Analysis
            calls = options_df[options_df['option_type'] == 'CALL']
            puts = options_df[options_df['option_type'] == 'PUT']
            
            if calls.empty or puts.empty:
                return 0.0
            
            # Volume-based PCR
            call_volume = calls['volume'].sum()
            put_volume = puts['volume'].sum()
            
            if call_volume + put_volume == 0:
                volume_pcr = 1.0
            else:
                volume_pcr = put_volume / (call_volume + put_volume)
            
            # OI-based PCR
            call_oi = calls['open_interest'].sum()
            put_oi = puts['open_interest'].sum()
            
            if call_oi + put_oi == 0:
                oi_pcr = 1.0
            else:
                oi_pcr = put_oi / (call_oi + put_oi)
            
            # 2. ATM Options Analysis
            atm_analysis = self._analyze_atm_options(options_df, spot_price)
            
            # 3. Skew Analysis
            skew_score = self._analyze_options_skew(calls, puts, spot_price)
            
            # Combine components
            pcr_score = self._interpret_pcr(volume_pcr, oi_pcr)
            
            options_score = (pcr_score * 0.4 + atm_analysis * 0.35 + skew_score * 0.25)
            
            return max(-1.0, min(1.0, options_score))
            
        except Exception as e:
            logger.error(f"Error analyzing options flow: {e}")
            return 0.0
    
    def _analyze_atm_options(self, options_df: pd.DataFrame, spot_price: float) -> Dict:
        """Analyze ATM options for directional bias"""
        try:
            # Find ATM strikes (within 5% of spot)
            atm_range = spot_price * 0.05
            atm_options = options_df[
                abs(options_df['strike'] - spot_price) <= atm_range
            ]
            
            if atm_options.empty:
                return {'activity_ratio': 0.0, 'call_activity': 0, 'put_activity': 0}
            
            atm_calls = atm_options[atm_options['option_type'] == 'CALL']
            atm_puts = atm_options[atm_options['option_type'] == 'PUT']
            
            # Compare ATM call vs put activity
            call_activity = atm_calls['volume'].sum() + (atm_calls['open_interest'].sum() * 0.1)
            put_activity = atm_puts['volume'].sum() + (atm_puts['open_interest'].sum() * 0.1)
            
            if call_activity + put_activity == 0:
                return {'activity_ratio': 0.0, 'call_activity': 0, 'put_activity': 0}
            
            # Positive score = bullish bias, negative = bearish bias
            activity_ratio = (call_activity - put_activity) / (call_activity + put_activity)
            
            return {
                'activity_ratio': activity_ratio,
                'call_activity': call_activity,
                'put_activity': put_activity
            }
            
        except Exception as e:
            logger.error(f"Error analyzing ATM options: {e}")
            return {'activity_ratio': 0.0, 'call_activity': 0, 'put_activity': 0}
    
    def _analyze_options_skew_enhanced(self, calls: pd.DataFrame, puts: pd.DataFrame, 
                                      spot_price: float) -> Dict:
        """Enhanced options skew analysis with IV skew"""
        try:
            if calls.empty or puts.empty:
                return {'skew_score': 0.0, 'iv_skew': 0, 'skew_type': 'neutral'}
            
            # ATM strikes (within 2% of spot)
            atm_range = spot_price * 0.02
            atm_calls = calls[abs(calls['strike'] - spot_price) <= atm_range]
            atm_puts = puts[abs(puts['strike'] - spot_price) <= atm_range]
            
            # OTM analysis
            otm_calls = calls[calls['strike'] > spot_price * 1.02]
            otm_puts = puts[puts['strike'] < spot_price * 0.98]
            
            # Calculate IV skew if IV data available
            iv_skew = 0
            skew_type = 'neutral'
            
            if 'iv' in calls.columns and 'iv' in puts.columns:
                # 25-delta skew approximation
                otm_call_iv = otm_calls['iv'].mean() if not otm_calls.empty else 0
                otm_put_iv = otm_puts['iv'].mean() if not otm_puts.empty else 0
                atm_iv = (atm_calls['iv'].mean() + atm_puts['iv'].mean()) / 2 if not atm_calls.empty and not atm_puts.empty else 0
                
                if atm_iv > 0:
                    iv_skew = ((otm_put_iv - otm_call_iv) / atm_iv) * 100
                    
                    if iv_skew > 5:
                        skew_type = 'put_skew'  # Fear/hedging
                    elif iv_skew < -5:
                        skew_type = 'call_skew'  # Greed/speculation
                    else:
                        skew_type = 'neutral'
            
            # Volume skew
            otm_call_volume = otm_calls['volume'].sum() if not otm_calls.empty else 0
            otm_put_volume = otm_puts['volume'].sum() if not otm_puts.empty else 0
            
            volume_skew_score = 0
            if otm_call_volume + otm_put_volume > 0:
                volume_skew_score = (otm_call_volume - otm_put_volume) / (otm_call_volume + otm_put_volume)
            
            # Combine IV skew and volume skew
            skew_score = volume_skew_score * 0.6
            if iv_skew != 0:
                # Negative IV skew (call skew) is bullish, positive (put skew) is bearish
                iv_skew_score = -iv_skew / 100  # Normalize and invert
                skew_score += iv_skew_score * 0.4
            
            skew_score = max(-1, min(1, skew_score))
            
            return {
                'skew_score': skew_score,
                'iv_skew': iv_skew,
                'skew_type': skew_type,
                'volume_skew': volume_skew_score
            }
            
        except Exception as e:
            logger.error(f"Error analyzing options skew: {e}")
            return {'skew_score': 0.0, 'iv_skew': 0, 'skew_type': 'neutral'}
    
    def _analyze_oi_distribution(self, calls: pd.DataFrame, puts: pd.DataFrame, spot_price: float) -> Dict:
        """Analyze open interest distribution for support/resistance levels"""
        try:
            # Find max OI strikes
            max_call_oi_strike = calls.loc[calls['open_interest'].idxmax(), 'strike'] if not calls.empty else spot_price
            max_put_oi_strike = puts.loc[puts['open_interest'].idxmax(), 'strike'] if not puts.empty else spot_price
            
            # Major support/resistance levels
            call_oi_sorted = calls.nlargest(3, 'open_interest')
            put_oi_sorted = puts.nlargest(3, 'open_interest')
            
            major_resistance = call_oi_sorted['strike'].min() if not call_oi_sorted.empty else spot_price * 1.05
            major_support = put_oi_sorted['strike'].max() if not put_oi_sorted.empty else spot_price * 0.95
            
            # Max pain calculation (simplified)
            all_strikes = pd.concat([calls['strike'], puts['strike']]).unique()
            max_pain = self._calculate_max_pain(calls, puts, all_strikes)
            
            # Directional bias based on OI distribution
            call_oi_above = calls[calls['strike'] > spot_price]['open_interest'].sum()
            put_oi_below = puts[puts['strike'] < spot_price]['open_interest'].sum()
            
            directional_bias = 0
            if call_oi_above + put_oi_below > 0:
                # More call OI above = resistance = bearish
                # More put OI below = support = bullish
                directional_bias = (put_oi_below - call_oi_above) / (call_oi_above + put_oi_below)
            
            return {
                'max_call_oi_strike': max_call_oi_strike,
                'max_put_oi_strike': max_put_oi_strike,
                'major_resistance': major_resistance,
                'major_support': major_support,
                'max_pain': max_pain,
                'directional_bias': directional_bias
            }
            
        except Exception as e:
            logger.error(f"Error analyzing OI distribution: {e}")
            return {
                'max_call_oi_strike': spot_price,
                'max_put_oi_strike': spot_price,
                'major_resistance': spot_price * 1.05,
                'major_support': spot_price * 0.95,
                'max_pain': spot_price,
                'directional_bias': 0
            }
    
    def _calculate_max_pain(self, calls: pd.DataFrame, puts: pd.DataFrame, strikes: np.ndarray) -> float:
        """Calculate max pain strike price"""
        try:
            min_pain_value = float('inf')
            max_pain_strike = strikes[0] if len(strikes) > 0 else 0
            
            for strike in strikes:
                # Calculate total value if expired at this strike
                call_value = calls[calls['strike'] < strike]['open_interest'].mul(
                    strike - calls[calls['strike'] < strike]['strike']
                ).sum()
                
                put_value = puts[puts['strike'] > strike]['open_interest'].mul(
                    puts[puts['strike'] > strike]['strike'] - strike
                ).sum()
                
                total_value = call_value + put_value
                
                if total_value < min_pain_value:
                    min_pain_value = total_value
                    max_pain_strike = strike
            
            return max_pain_strike
            
        except Exception as e:
            logger.error(f"Error calculating max pain: {e}")
            return strikes[len(strikes)//2] if len(strikes) > 0 else 0
    
    def _analyze_flow_intensity(self, options_df: pd.DataFrame) -> Dict:
        """Analyze options flow intensity and unusual activity"""
        try:
            # Volume to OI ratio
            avg_vol_oi_ratio = (options_df['volume'] / (options_df['open_interest'] + 1)).mean()
            
            # Identify unusual activity (volume > 2x OI)
            unusual_activity = options_df[options_df['volume'] > 2 * options_df['open_interest']]
            unusual_strikes = unusual_activity['strike'].tolist() if not unusual_activity.empty else []
            
            # Flow intensity classification
            if avg_vol_oi_ratio > 0.5:
                intensity = 'HIGH'
            elif avg_vol_oi_ratio > 0.3:
                intensity = 'MODERATE'
            else:
                intensity = 'LOW'
            
            return {
                'avg_vol_oi_ratio': avg_vol_oi_ratio,
                'intensity': intensity,
                'unusual_strikes': unusual_strikes[:5]  # Top 5 unusual strikes
            }
            
        except Exception as e:
            logger.error(f"Error analyzing flow intensity: {e}")
            return {'avg_vol_oi_ratio': 0, 'intensity': 'LOW', 'unusual_strikes': []}
    
    def _analyze_smart_money_flow(self, options_df: pd.DataFrame, spot_price: float) -> Dict:
        """Analyze large trades for smart money indicators"""
        try:
            # Define large trades as top 10% by premium
            if 'premium' in options_df.columns:
                options_df['trade_value'] = options_df['volume'] * options_df['premium']
            else:
                options_df['trade_value'] = options_df['volume'] * 10  # Fallback
            
            threshold = options_df['trade_value'].quantile(0.9)
            large_trades = options_df[options_df['trade_value'] >= threshold]
            
            if large_trades.empty:
                return {'smart_money_bias': 0, 'direction': 'Neutral'}
            
            # Analyze direction of large trades
            large_calls = large_trades[large_trades['option_type'] == 'CALL']
            large_puts = large_trades[large_trades['option_type'] == 'PUT']
            
            call_value = large_calls['trade_value'].sum()
            put_value = large_puts['trade_value'].sum()
            
            smart_money_bias = 0
            direction = 'Neutral'
            
            if call_value + put_value > 0:
                smart_money_bias = (call_value - put_value) / (call_value + put_value)
                
                if smart_money_bias > 0.3:
                    direction = 'Bullish'
                elif smart_money_bias < -0.3:
                    direction = 'Bearish'
            
            return {
                'smart_money_bias': smart_money_bias,
                'direction': direction,
                'large_call_value': call_value,
                'large_put_value': put_value
            }
            
        except Exception as e:
            logger.error(f"Error analyzing smart money flow: {e}")
            return {'smart_money_bias': 0, 'direction': 'Neutral'}
    
    def _get_pcr_interpretation(self, volume_pcr: float, oi_pcr: float) -> str:
        """Get interpretation of PCR values"""
        avg_pcr = (volume_pcr + oi_pcr) / 2
        
        if avg_pcr > 1.5:
            return 'Extremely Bearish'
        elif avg_pcr > 1.2:
            return 'Bearish'
        elif avg_pcr > 0.8:
            return 'Neutral'
        elif avg_pcr > 0.5:
            return 'Bullish'
        else:
            return 'Extremely Bullish'
    
    def _classify_iv_environment(self, options_df: pd.DataFrame) -> str:
        """Classify IV environment based on ATM IV"""
        try:
            if 'iv' not in options_df.columns:
                return 'NORMAL'
            
            avg_iv = options_df['iv'].mean()
            
            # These thresholds would ideally be based on historical percentiles
            if avg_iv > 50:
                return 'HIGH'
            elif avg_iv > 30:
                return 'ELEVATED'
            elif avg_iv > 20:
                return 'NORMAL'
            else:
                return 'LOW'
                
        except Exception as e:
            logger.error(f"Error classifying IV environment: {e}")
            return 'NORMAL'
    
    def _analyze_options_skew(self, calls: pd.DataFrame, puts: pd.DataFrame, 
                            spot_price: float) -> float:
        """Analyze options skew for sentiment"""
        try:
            if calls.empty or puts.empty:
                return 0.0
            
            # OTM analysis
            otm_calls = calls[calls['strike'] > spot_price * 1.02]  # 2% OTM
            otm_puts = puts[puts['strike'] < spot_price * 0.98]   # 2% OTM
            
            if otm_calls.empty or otm_puts.empty:
                return 0.0
            
            # Compare OTM activity
            otm_call_activity = otm_calls['volume'].sum()
            otm_put_activity = otm_puts['volume'].sum()
            
            if otm_call_activity + otm_put_activity == 0:
                return 0.0
            
            # More OTM call activity = bullish, more OTM put activity = bearish
            skew_score = (otm_call_activity - otm_put_activity) / (otm_call_activity + otm_put_activity)
            
            return skew_score * 0.5  # Scale down the impact
            
        except Exception as e:
            logger.error(f"Error analyzing options skew: {e}")
            return 0.0
    
    def _interpret_pcr(self, volume_pcr: float, oi_pcr: float) -> float:
        """Interpret Put-Call Ratio for directional bias"""
        try:
            # PCR interpretation (inverted - high PCR = bearish)
            # Normal PCR is around 0.7-1.3
            
            avg_pcr = (volume_pcr + oi_pcr) / 2
            
            if avg_pcr > 1.2:
                return -0.6  # Bearish
            elif avg_pcr > 1.0:
                return -0.3  # Slightly bearish
            elif avg_pcr > 0.8:
                return 0.0   # Neutral
            elif avg_pcr > 0.6:
                return 0.3   # Slightly bullish
            else:
                return 0.6   # Bullish
            
        except Exception as e:
            logger.error(f"Error interpreting PCR: {e}")
            return 0.0
    
    def _analyze_price_action_enhanced(self, options_df: pd.DataFrame, spot_price: float) -> Tuple[float, Dict]:
        """Enhanced price action analysis with market microstructure"""
        try:
            # Price levels analysis
            price_levels = self._analyze_price_levels(options_df, spot_price)
            
            # Market breadth from options data
            market_breadth = self._analyze_market_breadth(options_df)
            
            # Expected move calculation
            expected_move = self._calculate_expected_move(options_df, spot_price)
            
            # Price position relative to key levels
            position_score = self._analyze_price_position(spot_price, price_levels)
            
            # Momentum from options pricing
            momentum_score = self._analyze_options_momentum(options_df, spot_price)
            
            # Calculate final price action score
            price_action_score = (
                position_score * 0.3 +
                momentum_score * 0.3 +
                market_breadth['breadth_score'] * 0.2 +
                price_levels['trend_score'] * 0.2
            )
            
            logger.info(f"Final Price Action Score: {price_action_score:.2f}")
            
            # Compile details
            details = {
                'spot_vs_max_pain': price_levels['spot_vs_max_pain'],
                'price_position': price_levels['position_description'],
                'expected_move_1sd': expected_move['one_sd_move'],
                'expected_move_2sd': expected_move['two_sd_move'],
                'upper_expected': spot_price + expected_move['one_sd_move'],
                'lower_expected': spot_price - expected_move['one_sd_move'],
                'market_breadth': market_breadth['description'],
                'options_momentum': 'Bullish' if momentum_score > 0 else 'Bearish' if momentum_score < 0 else 'Neutral',
                'key_levels': price_levels['key_levels']
            }
            
            return max(-1.0, min(1.0, price_action_score)), details
            
        except Exception as e:
            logger.error(f"Error in enhanced price action analysis: {e}")
            return 0.0, {}
    
    def _analyze_price_levels(self, options_df: pd.DataFrame, spot_price: float) -> Dict:
        """Analyze price levels from options data"""
        try:
            strikes = options_df['strike'].unique()
            
            # Find nearest ITM and OTM strikes
            itm_calls = options_df[(options_df['option_type'] == 'CALL') & (options_df['strike'] < spot_price)]
            otm_calls = options_df[(options_df['option_type'] == 'CALL') & (options_df['strike'] > spot_price)]
            itm_puts = options_df[(options_df['option_type'] == 'PUT') & (options_df['strike'] > spot_price)]
            otm_puts = options_df[(options_df['option_type'] == 'PUT') & (options_df['strike'] < spot_price)]
            
            # Key support/resistance from high OI
            high_oi_calls = options_df[options_df['option_type'] == 'CALL'].nlargest(3, 'open_interest')
            high_oi_puts = options_df[options_df['option_type'] == 'PUT'].nlargest(3, 'open_interest')
            
            key_resistance = high_oi_calls['strike'].tolist() if not high_oi_calls.empty else []
            key_support = high_oi_puts['strike'].tolist() if not high_oi_puts.empty else []
            
            # Calculate max pain if not already done
            all_strikes = pd.concat([options_df[options_df['option_type'] == 'CALL']['strike'],
                                   options_df[options_df['option_type'] == 'PUT']['strike']]).unique()
            max_pain = self._calculate_max_pain(
                options_df[options_df['option_type'] == 'CALL'],
                options_df[options_df['option_type'] == 'PUT'],
                all_strikes
            )
            
            # Price position analysis
            spot_vs_max_pain = ((spot_price - max_pain) / max_pain) * 100
            
            # Determine position and trend
            position_description = 'At Max Pain'
            trend_score = 0
            
            if spot_vs_max_pain > 2:
                position_description = 'Above Max Pain'
                trend_score = 0.3
            elif spot_vs_max_pain < -2:
                position_description = 'Below Max Pain'
                trend_score = -0.3
            
            # Check position relative to key levels
            if key_resistance and spot_price > max(key_resistance):
                position_description += ' - Breakout Above Resistance'
                trend_score += 0.3
            elif key_support and spot_price < min(key_support):
                position_description += ' - Breakdown Below Support'
                trend_score -= 0.3
            
            return {
                'max_pain': max_pain,
                'spot_vs_max_pain': spot_vs_max_pain,
                'position_description': position_description,
                'trend_score': trend_score,
                'key_levels': {
                    'resistance': key_resistance[:3],
                    'support': key_support[:3]
                }
            }
            
        except Exception as e:
            logger.error(f"Error analyzing price levels: {e}")
            return {
                'max_pain': spot_price,
                'spot_vs_max_pain': 0,
                'position_description': 'Unknown',
                'trend_score': 0,
                'key_levels': {'resistance': [], 'support': []}
            }
    
    def _analyze_market_breadth(self, options_df: pd.DataFrame) -> Dict:
        """Analyze market breadth from options data"""
        try:
            # Calculate advancing vs declining based on premium changes
            calls = options_df[options_df['option_type'] == 'CALL']
            puts = options_df[options_df['option_type'] == 'PUT']
            
            # Volume breadth
            call_volume_weighted = (calls['volume'] * calls['strike']).sum() / calls['volume'].sum() if not calls.empty else 0
            put_volume_weighted = (puts['volume'] * puts['strike']).sum() / puts['volume'].sum() if not puts.empty else 0
            
            # More call activity at higher strikes = bullish breadth
            # More put activity at lower strikes = bearish breadth
            breadth_score = 0
            description = 'Neutral'
            
            if call_volume_weighted > put_volume_weighted * 1.05:
                breadth_score = 0.5
                description = 'Bullish - Call activity at higher strikes'
            elif put_volume_weighted > call_volume_weighted * 1.05:
                breadth_score = -0.5
                description = 'Bearish - Put activity at lower strikes'
            
            return {
                'breadth_score': breadth_score,
                'description': description,
                'call_weighted_strike': call_volume_weighted,
                'put_weighted_strike': put_volume_weighted
            }
            
        except Exception as e:
            logger.error(f"Error analyzing market breadth: {e}")
            return {'breadth_score': 0, 'description': 'Unknown'}
    
    def _calculate_expected_move(self, options_df: pd.DataFrame, spot_price: float) -> Dict:
        """Calculate expected move from ATM straddle prices"""
        try:
            # Find ATM options
            atm_strike = min(options_df['strike'].unique(), key=lambda x: abs(x - spot_price))
            atm_options = options_df[options_df['strike'] == atm_strike]
            
            atm_call = atm_options[atm_options['option_type'] == 'CALL']
            atm_put = atm_options[atm_options['option_type'] == 'PUT']
            
            if atm_call.empty or atm_put.empty or 'premium' not in options_df.columns:
                # Fallback: use 1% as default expected move
                return {
                    'one_sd_move': spot_price * 0.01,
                    'two_sd_move': spot_price * 0.02,
                    'method': 'default'
                }
            
            # Expected move = ATM straddle price * 0.85 (approximation)
            straddle_price = atm_call['premium'].iloc[0] + atm_put['premium'].iloc[0]
            one_sd_move = straddle_price * 0.85
            two_sd_move = one_sd_move * 2
            
            return {
                'one_sd_move': one_sd_move,
                'two_sd_move': two_sd_move,
                'method': 'straddle',
                'straddle_price': straddle_price
            }
            
        except Exception as e:
            logger.error(f"Error calculating expected move: {e}")
            return {
                'one_sd_move': spot_price * 0.01,
                'two_sd_move': spot_price * 0.02,
                'method': 'error_default'
            }
    
    def _analyze_price_position(self, spot_price: float, price_levels: Dict) -> float:
        """Analyze spot price position relative to key levels"""
        try:
            score = 0
            
            # Position relative to max pain
            spot_vs_max_pain = price_levels.get('spot_vs_max_pain', 0)
            if abs(spot_vs_max_pain) < 1:
                score = 0  # Neutral at max pain
            elif spot_vs_max_pain > 0:
                score = min(spot_vs_max_pain / 10, 0.5)  # Bullish above max pain
            else:
                score = max(spot_vs_max_pain / 10, -0.5)  # Bearish below max pain
            
            # Adjust for support/resistance
            key_levels = price_levels.get('key_levels', {})
            resistances = key_levels.get('resistance', [])
            supports = key_levels.get('support', [])
            
            if resistances and spot_price > max(resistances):
                score += 0.3  # Breakout
            elif supports and spot_price < min(supports):
                score -= 0.3  # Breakdown
            
            return max(-1, min(1, score))
            
        except Exception as e:
            logger.error(f"Error analyzing price position: {e}")
            return 0
    
    def _analyze_options_momentum(self, options_df: pd.DataFrame, spot_price: float) -> float:
        """Analyze momentum from options pricing dynamics"""
        try:
            # Near-term vs far-term IV (term structure)
            # Higher near-term IV suggests expected movement
            
            # Call/Put demand momentum
            recent_strikes = options_df[
                (options_df['strike'] >= spot_price * 0.95) & 
                (options_df['strike'] <= spot_price * 1.05)
            ]
            
            if recent_strikes.empty:
                return 0
            
            calls = recent_strikes[recent_strikes['option_type'] == 'CALL']
            puts = recent_strikes[recent_strikes['option_type'] == 'PUT']
            
            # Volume momentum
            call_momentum = calls['volume'].sum() if not calls.empty else 0
            put_momentum = puts['volume'].sum() if not puts.empty else 0
            
            if call_momentum + put_momentum == 0:
                return 0
            
            momentum_score = (call_momentum - put_momentum) / (call_momentum + put_momentum)
            
            return momentum_score * 0.5  # Scale down impact
            
        except Exception as e:
            logger.error(f"Error analyzing options momentum: {e}")
            return 0
    
    def _analyze_price_action(self, options_df: pd.DataFrame, spot_price: float) -> float:
        """Analyze price action patterns"""
        try:
            # Simplified price action analysis
            # This would normally use historical price data
            
            # For now, use spot vs strike distribution as proxy
            if options_df.empty:
                return 0.0
            
            strikes = options_df['strike'].unique()
            
            if len(strikes) == 0:
                return 0.0
            
            # Compare spot position relative to strike distribution
            min_strike = strikes.min()
            max_strike = strikes.max()
            
            if max_strike == min_strike:
                return 0.0
            
            spot_position = (spot_price - min_strike) / (max_strike - min_strike)
            
            # If spot is in upper range, slightly bullish bias
            if spot_position > 0.6:
                return 0.2
            elif spot_position < 0.4:
                return -0.2
            else:
                return 0.0
            
        except Exception as e:
            logger.error(f"Error analyzing price action: {e}")
            return 0.0
    
    def _interpret_direction_score_enhanced(self, score: float, technical_details: Dict) -> tuple:
        """Enhanced interpretation with confidence calculation"""
        try:
            abs_score = abs(score)
            
            # Base direction and sub-category
            if score >= 0.7:
                direction, sub_category = 'Bullish', 'Strong'
            elif score >= 0.4:
                direction, sub_category = 'Bullish', 'Moderate'
            elif score >= 0.1:
                direction, sub_category = 'Bullish', 'Weak'
            elif score <= -0.7:
                direction, sub_category = 'Bearish', 'Strong'
            elif score <= -0.4:
                direction, sub_category = 'Bearish', 'Moderate'
            elif score <= -0.1:
                direction, sub_category = 'Bearish', 'Weak'
            else:
                direction, sub_category = 'Neutral', ''
            
            # Calculate confidence based on signal alignment
            confidence_factors = []
            
            # Technical alignment
            if technical_details.get('trend') == 'Uptrend' and score > 0:
                confidence_factors.append(0.2)
            elif technical_details.get('trend') == 'Downtrend' and score < 0:
                confidence_factors.append(0.2)
            
            # EMA alignment
            if technical_details.get('ema_alignment') in ['Bullish', 'Bearish']:
                confidence_factors.append(0.15)
            
            # Momentum confirmation
            rsi = technical_details.get('rsi', 50)
            if (rsi > 50 and score > 0) or (rsi < 50 and score < 0):
                confidence_factors.append(0.1)
            
            # Volume confirmation
            if technical_details.get('volume_trend') == 'Increasing':
                confidence_factors.append(0.1)
            
            # Base confidence from score strength
            base_confidence = min(abs_score, 0.45)
            
            # Total confidence
            confidence = base_confidence + sum(confidence_factors)
            confidence = min(confidence, 0.95)  # Cap at 95%
            
            return direction, sub_category, confidence
            
        except Exception as e:
            logger.error(f"Error interpreting direction score: {e}")
            return 'Neutral', '', 0.5
    
    def _estimate_timeframe_enhanced(self, confidence: float, bb_width: float, iv_environment: str) -> Dict:
        """Enhanced timeframe estimation based on multiple factors"""
        try:
            # Base timeframe on confidence and volatility
            if confidence > 0.7 and bb_width < 0.15:
                timeframe = 'short'
                duration = '1-5 days'
                description = 'High confidence with low volatility suggests near-term move'
            elif confidence > 0.5 or (bb_width > 0.25 and iv_environment in ['HIGH', 'ELEVATED']):
                timeframe = 'mid'
                duration = '10-30 days'
                description = 'Moderate confidence or elevated volatility suggests medium-term view'
            else:
                timeframe = 'long'
                duration = '30+ days'
                description = 'Low confidence or normal conditions suggest longer-term perspective'
            
            # Adjust confidence for timeframe
            timeframe_confidence = confidence * 0.8  # Reduce confidence for time predictions
            
            return {
                'timeframe': timeframe,
                'duration': duration,
                'confidence': timeframe_confidence,
                'description': description,
                'factors': {
                    'market_confidence': confidence,
                    'volatility_width': bb_width,
                    'iv_environment': iv_environment
                }
            }
            
        except Exception as e:
            logger.error(f"Error estimating timeframe: {e}")
            return {
                'timeframe': 'mid',
                'duration': '10-30 days',
                'confidence': 0.3,
                'description': 'Default timeframe due to calculation error'
            }
    
    def _interpret_direction_score(self, score: float) -> tuple:
        """Interpret final direction score"""
        try:
            abs_score = abs(score)
            
            if score >= 0.7:
                return 'Bullish', 'Strong', abs_score
            elif score >= 0.4:
                return 'Bullish', 'Moderate', abs_score
            elif score >= 0.1:
                return 'Bullish', 'Weak', abs_score
            elif score <= -0.7:
                return 'Bearish', 'Strong', abs_score
            elif score <= -0.4:
                return 'Bearish', 'Moderate', abs_score
            elif score <= -0.1:
                return 'Bearish', 'Weak', abs_score
            else:
                return 'Neutral', '', max(0.1, abs_score)
            
        except Exception as e:
            logger.error(f"Error interpreting direction score: {e}")
            return 'Neutral', '', 0.5
    
    def _estimate_timeframe(self, score: float, confidence: float) -> Dict:
        """Estimate timeframe for directional move"""
        try:
            abs_score = abs(score)
            
            if abs_score > 0.7 and confidence > 0.7:
                timeframe = 'short'
                duration = '1-5 days'
            elif abs_score > 0.4 or confidence > 0.5:
                timeframe = 'mid'
                duration = '10-30 days'
            else:
                timeframe = 'long'
                duration = '30+ days'
            
            return {
                'timeframe': timeframe,
                'duration': duration,
                'confidence': confidence * 0.8  # Reduce confidence for timeframe
            }
            
        except Exception as e:
            logger.error(f"Error estimating timeframe: {e}")
            return {'timeframe': 'mid', 'duration': '10-30 days', 'confidence': 0.5}
    
    def _default_direction_analysis(self) -> Dict:
        """Return default direction analysis when calculation fails"""
        return {
            'direction': 'Neutral',
            'sub_category': '',
            'confidence': 0.5,
            'final_score': 0.0,
            'components': {
                'technical_score': 0.0,
                'options_score': 0.0,
                'price_action_score': 0.0
            },
            'timeframe': {
                'timeframe': 'mid',
                'duration': '10-30 days',
                'confidence': 0.3
            },
            'strength': 0.0
        }