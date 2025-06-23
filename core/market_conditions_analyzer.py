"""
Market Conditions Analyzer for Options Trading
Integrates with existing NIFTY analysis, VIX data, and database PCR calculations
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import yfinance as yf

try:
    from config.options_config import (
        MARKET_CONDITIONS, VIX_THRESHOLDS, PCR_INTERPRETATION,
        INTEGRATION_CONFIG, SUPABASE_CONFIG
    )
except ImportError:
    # Fallback configuration if config module not available
    MARKET_CONDITIONS = {
        'Bullish_Low_VIX': {'preferred_strategies': ['Bull Call Spreads'], 'pcr_range': (0.7, 1.0)},
        'Bearish_High_VIX': {'preferred_strategies': ['Bear Put Spreads'], 'pcr_range': (1.2, 1.8)},
        'Neutral_Normal_VIX': {'preferred_strategies': ['Iron Condors'], 'pcr_range': (0.9, 1.1)}
    }
    VIX_THRESHOLDS = {'low': 15.0, 'normal': 20.0, 'high': 25.0, 'spike': 30.0}
    PCR_INTERPRETATION = {'extreme_bearish': 1.5, 'bearish': 1.2, 'neutral': 1.0, 'bullish': 0.8, 'extreme_bullish': 0.6}
    INTEGRATION_CONFIG = {'use_existing_nifty_analysis': True, 'use_database_pcr': True}
    SUPABASE_CONFIG = {'min_industry_weight': 5.0}

logger = logging.getLogger(__name__)

class MarketConditionsAnalyzer:
    """
    Analyze market conditions using:
    1. Existing NIFTY technical analysis (yfinance-based)
    2. VIX data from existing scripts
    3. PCR calculation from option_chain_data table
    """
    
    def __init__(self, supabase_client=None):
        self.supabase = supabase_client
        self.current_conditions = {}
        
    def get_nifty_direction(self) -> Dict[str, Any]:
        """
        Get NIFTY direction using existing Dhan historical data scripts for better analysis
        """
        try:
            # First try to use the existing Dhan NIFTY historical data
            nifty_historical_data = self._get_dhan_nifty_data()
            
            if nifty_historical_data and len(nifty_historical_data) > 0:
                # Use Dhan historical data for better analysis
                return self._analyze_dhan_nifty_data(nifty_historical_data)
            else:
                # Fallback to yfinance if Dhan data not available
                logger.warning("Dhan NIFTY data not available, falling back to yfinance")
                return self._analyze_yfinance_nifty_data()
            
        except Exception as e:
            logger.error(f"Error analyzing NIFTY direction: {e}")
            return {
                'direction': 'neutral',
                'confidence': 0.5,
                'details': {},
                'error': str(e)
            }
    
    def _get_dhan_nifty_data(self) -> List[Dict]:
        """
        Get NIFTY data using the existing Dhan historical data fetcher
        """
        try:
            # Import the existing NIFTY fetcher
            import sys
            import os
            sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'data_scripts'))
            
            from nifty_historical_data import NiftyHistoricalDataFetcher
            
            # Initialize fetcher
            fetcher = NiftyHistoricalDataFetcher()
            
            # Get last 90 days of NIFTY data
            nifty_data = fetcher.get_historical_data(days=90)
            
            if nifty_data:
                logger.info(f"Successfully fetched {len(nifty_data)} days of NIFTY data from Dhan")
                return nifty_data
            else:
                logger.warning("No NIFTY data returned from Dhan fetcher")
                return []
                
        except Exception as e:
            logger.warning(f"Error fetching Dhan NIFTY data: {e}")
            return []
    
    def _analyze_dhan_nifty_data(self, nifty_data: List[Dict]) -> Dict[str, Any]:
        """
        Analyze NIFTY direction using Dhan historical data with advanced technical analysis
        """
        try:
            # Convert to pandas for easier analysis
            df = pd.DataFrame(nifty_data)
            
            # Sort by date to ensure chronological order
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            
            # Calculate technical indicators
            df = self._calculate_technical_indicators(df)
            
            # Analyze multiple timeframes
            analysis = {}
            timeframes = {
                '1W': 5,   # Last 5 days
                '2W': 10,  # Last 10 days  
                '1M': 20,  # Last 20 days
                '3M': 60   # Last 60 days
            }
            
            current_price = df['close'].iloc[-1]
            
            for period, days in timeframes.items():
                if len(df) >= days:
                    period_data = df.iloc[-days:]
                    analysis[period] = self._analyze_timeframe(period_data, current_price)
            
            # Aggregate analysis across timeframes
            overall_trend = self._aggregate_trend_signals_advanced(analysis)
            confidence = self._calculate_trend_confidence_advanced(analysis, df)
            
            # Calculate advanced metrics
            momentum_score = self._calculate_momentum_score(df)
            strength_indicators = self._calculate_strength_indicators(df)
            support_resistance = self._identify_support_resistance(df)
            
            return {
                'direction': overall_trend,
                'confidence': confidence,
                'current_price': current_price,
                'momentum_score': momentum_score,
                'strength_indicators': strength_indicators,
                'support_resistance': support_resistance,
                'timeframe_analysis': analysis,
                'technical_summary': self._generate_technical_summary(overall_trend, confidence, momentum_score),
                'data_source': 'dhan_historical',
                'data_points': len(df),
                'last_updated': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing Dhan NIFTY data: {e}")
            return self._analyze_yfinance_nifty_data()
    
    def _calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate comprehensive technical indicators"""
        # Moving averages
        df['ma_5'] = df['close'].rolling(5).mean()
        df['ma_10'] = df['close'].rolling(10).mean()
        df['ma_20'] = df['close'].rolling(20).mean()
        df['ma_50'] = df['close'].rolling(50).mean()
        
        # RSI calculation
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        ema_12 = df['close'].ewm(span=12).mean()
        ema_26 = df['close'].ewm(span=26).mean()
        df['macd'] = ema_12 - ema_26
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']
        
        # Bollinger Bands
        df['bb_middle'] = df['close'].rolling(20).mean()
        bb_std = df['close'].rolling(20).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
        df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        return df
    
    def _analyze_timeframe(self, period_data: pd.DataFrame, current_price: float) -> Dict:
        """Analyze a specific timeframe"""
        if len(period_data) < 5:
            return {'trend': 'neutral', 'strength': 0.5}
        
        # Price action analysis
        start_price = period_data['close'].iloc[0]
        returns = (current_price / start_price - 1) * 100
        
        # Moving average analysis
        ma_20 = period_data['ma_20'].iloc[-1] if not pd.isna(period_data['ma_20'].iloc[-1]) else current_price
        ma_50 = period_data['ma_50'].iloc[-1] if len(period_data) >= 50 and not pd.isna(period_data['ma_50'].iloc[-1]) else current_price
        
        # RSI analysis
        current_rsi = period_data['rsi'].iloc[-1] if not pd.isna(period_data['rsi'].iloc[-1]) else 50
        
        # MACD analysis
        macd_signal = 'neutral'
        if not pd.isna(period_data['macd'].iloc[-1]) and not pd.isna(period_data['macd_signal'].iloc[-1]):
            if period_data['macd'].iloc[-1] > period_data['macd_signal'].iloc[-1]:
                macd_signal = 'bullish'
            elif period_data['macd'].iloc[-1] < period_data['macd_signal'].iloc[-1]:
                macd_signal = 'bearish'
        
        # Determine trend
        trend = self._determine_trend_advanced(current_price, ma_20, ma_50, current_rsi, returns)
        
        # Calculate strength
        strength = self._calculate_period_strength(period_data, returns, current_rsi)
        
        return {
            'trend': trend,
            'strength': strength,
            'returns': returns,
            'rsi': current_rsi,
            'macd_signal': macd_signal,
            'ma_20': ma_20,
            'ma_50': ma_50
        }
    
    def _determine_trend_advanced(self, price: float, ma_20: float, ma_50: float, rsi: float, returns: float) -> str:
        """Advanced trend determination with multiple factors"""
        bullish_signals = 0
        bearish_signals = 0
        
        # Price vs moving averages
        if price > ma_20:
            bullish_signals += 1
        else:
            bearish_signals += 1
            
        if price > ma_50:
            bullish_signals += 1
        else:
            bearish_signals += 1
        
        # RSI analysis
        if rsi > 60:
            bullish_signals += 1
        elif rsi < 40:
            bearish_signals += 1
        
        # Returns analysis
        if returns > 2:
            bullish_signals += 1
        elif returns < -2:
            bearish_signals += 1
        
        # Moving average relationship
        if ma_20 > ma_50:
            bullish_signals += 1
        elif ma_20 < ma_50:
            bearish_signals += 1
        
        if bullish_signals > bearish_signals:
            return 'bullish'
        elif bearish_signals > bullish_signals:
            return 'bearish'
        else:
            return 'neutral'
    
    def _calculate_period_strength(self, period_data: pd.DataFrame, returns: float, rsi: float) -> float:
        """Calculate strength of the trend for a period"""
        strength_factors = []
        
        # Returns strength
        strength_factors.append(min(abs(returns) / 10, 1.0))
        
        # RSI divergence from neutral
        rsi_strength = abs(rsi - 50) / 50
        strength_factors.append(rsi_strength)
        
        # Volatility consideration (lower volatility = higher confidence)
        if len(period_data) > 5:
            volatility = period_data['close'].pct_change().std()
            vol_strength = max(0, 1 - (volatility * 20))  # Scale volatility
            strength_factors.append(vol_strength)
        
        return np.mean(strength_factors)
    
    def _aggregate_trend_signals_advanced(self, analysis: Dict) -> str:
        """Advanced aggregation with weighted timeframes"""
        if not analysis:
            return 'neutral'
        
        # Weight timeframes differently (shorter term has higher weight)
        weights = {
            '1W': 0.4,
            '2W': 0.3,
            '1M': 0.2,
            '3M': 0.1
        }
        
        weighted_scores = {'bullish': 0, 'bearish': 0, 'neutral': 0}
        total_weight = 0
        
        for timeframe, data in analysis.items():
            weight = weights.get(timeframe, 0.1)
            trend = data.get('trend', 'neutral')
            strength = data.get('strength', 0.5)
            
            # Weight by both timeframe importance and signal strength
            effective_weight = weight * strength
            weighted_scores[trend] += effective_weight
            total_weight += effective_weight
        
        if total_weight > 0:
            # Normalize scores
            for trend in weighted_scores:
                weighted_scores[trend] /= total_weight
        
        # Determine overall trend
        max_trend = max(weighted_scores, key=weighted_scores.get)
        max_score = weighted_scores[max_trend]
        
        # Require minimum confidence for directional calls
        if max_score > 0.4:
            return max_trend
        else:
            return 'neutral'
    
    def _calculate_trend_confidence_advanced(self, analysis: Dict, df: pd.DataFrame) -> float:
        """Calculate confidence in trend analysis"""
        if not analysis:
            return 0.5
        
        # Factor 1: Consistency across timeframes
        trends = [data.get('trend', 'neutral') for data in analysis.values()]
        dominant_trend = max(set(trends), key=trends.count)
        consistency = trends.count(dominant_trend) / len(trends)
        
        # Factor 2: Average strength across timeframes
        strengths = [data.get('strength', 0.5) for data in analysis.values()]
        avg_strength = np.mean(strengths)
        
        # Factor 3: Data quality (more data points = higher confidence)
        data_quality = min(len(df) / 90, 1.0)  # Scale to 90 days max
        
        # Combined confidence
        confidence = (consistency * 0.5 + avg_strength * 0.3 + data_quality * 0.2)
        return min(confidence, 1.0)
    
    def _calculate_momentum_score(self, df: pd.DataFrame) -> Dict:
        """Calculate momentum indicators"""
        if len(df) < 20:
            return {'score': 0.5, 'direction': 'neutral'}
        
        # Price momentum over different periods
        returns_5d = (df['close'].iloc[-1] / df['close'].iloc[-6] - 1) * 100 if len(df) >= 6 else 0
        returns_10d = (df['close'].iloc[-1] / df['close'].iloc[-11] - 1) * 100 if len(df) >= 11 else 0
        returns_20d = (df['close'].iloc[-1] / df['close'].iloc[-21] - 1) * 100 if len(df) >= 21 else 0
        
        # Volume momentum (if available)
        volume_trend = 0
        if 'volume' in df.columns and len(df) >= 10:
            recent_volume = df['volume'].iloc[-5:].mean()
            avg_volume = df['volume'].iloc[-20:].mean()
            volume_trend = (recent_volume / avg_volume - 1) if avg_volume > 0 else 0
        
        # Composite momentum score
        momentum_components = [returns_5d * 0.5, returns_10d * 0.3, returns_20d * 0.2]
        momentum_score = sum(momentum_components)
        
        # Normalize to 0-1 range
        normalized_score = max(0, min(1, (momentum_score + 10) / 20))  # Scale -10 to +10 range
        
        direction = 'bullish' if momentum_score > 1 else 'bearish' if momentum_score < -1 else 'neutral'
        
        return {
            'score': normalized_score,
            'direction': direction,
            'returns_5d': returns_5d,
            'returns_10d': returns_10d,
            'returns_20d': returns_20d,
            'volume_trend': volume_trend
        }
    
    def _calculate_strength_indicators(self, df: pd.DataFrame) -> Dict:
        """Calculate market strength indicators"""
        if len(df) < 20:
            return {'overall_strength': 0.5}
        
        # RSI strength
        current_rsi = df['rsi'].iloc[-1] if not pd.isna(df['rsi'].iloc[-1]) else 50
        rsi_strength = abs(current_rsi - 50) / 50
        
        # MACD strength
        macd_strength = 0.5
        if not pd.isna(df['macd_histogram'].iloc[-1]):
            recent_macd_hist = df['macd_histogram'].iloc[-5:].mean()
            macd_strength = max(0, min(1, (recent_macd_hist + 50) / 100))
        
        # Bollinger Band position
        bb_strength = df['bb_position'].iloc[-1] if not pd.isna(df['bb_position'].iloc[-1]) else 0.5
        
        # Overall strength
        overall_strength = (rsi_strength * 0.4 + macd_strength * 0.3 + abs(bb_strength - 0.5) * 2 * 0.3)
        
        return {
            'overall_strength': min(overall_strength, 1.0),
            'rsi_strength': rsi_strength,
            'macd_strength': macd_strength,
            'bb_position': bb_strength,
            'current_rsi': current_rsi
        }
    
    def _identify_support_resistance(self, df: pd.DataFrame) -> Dict:
        """Identify key support and resistance levels"""
        if len(df) < 20:
            return {'support': None, 'resistance': None}
        
        recent_data = df.iloc[-20:]  # Last 20 days
        current_price = df['close'].iloc[-1]
        
        # Simple support/resistance based on recent highs/lows
        resistance = recent_data['high'].max()
        support = recent_data['low'].min()
        
        # Distance from support/resistance
        resistance_distance = (resistance - current_price) / current_price * 100
        support_distance = (current_price - support) / current_price * 100
        
        return {
            'support': support,
            'resistance': resistance,
            'support_distance_pct': support_distance,
            'resistance_distance_pct': resistance_distance,
            'near_support': support_distance < 2,  # Within 2%
            'near_resistance': resistance_distance < 2  # Within 2%
        }
    
    def _generate_technical_summary(self, trend: str, confidence: float, momentum: Dict) -> str:
        """Generate human-readable technical summary"""
        trend_desc = {
            'bullish': 'Bullish',
            'bearish': 'Bearish', 
            'neutral': 'Neutral'
        }.get(trend, 'Neutral')
        
        confidence_desc = 'High' if confidence > 0.7 else 'Medium' if confidence > 0.5 else 'Low'
        momentum_desc = momentum.get('direction', 'neutral').title()
        
        return f"{trend_desc} trend with {confidence_desc.lower()} confidence ({confidence:.1%}). {momentum_desc} momentum."
    
    def _analyze_yfinance_nifty_data(self) -> Dict[str, Any]:
        """
        Fallback NIFTY analysis using yfinance (original method)
        """
        try:
            # Fetch NIFTY data (similar to your stock analysis)
            nifty = yf.Ticker("^NSEI")
            
            # Get multiple timeframes like your existing system
            timeframes = {
                '1M': nifty.history(period="1mo"),
                '3M': nifty.history(period="3mo"),
                '6M': nifty.history(period="6mo")
            }
            
            analysis = {}
            
            for period, data in timeframes.items():
                if data.empty:
                    continue
                    
                # Calculate technical indicators (like your ranking_score approach)
                close_prices = data['Close']
                current_price = close_prices.iloc[-1]
                
                # Moving averages
                ma_20 = close_prices.rolling(20).mean().iloc[-1]
                ma_50 = close_prices.rolling(50).mean().iloc[-1] if len(close_prices) >= 50 else None
                
                # RSI calculation
                delta = close_prices.diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs)).iloc[-1]
                
                # Price momentum (like your momentum_score)
                returns_1w = (current_price / close_prices.iloc[-5] - 1) * 100 if len(close_prices) >= 5 else 0
                returns_1m = (current_price / close_prices.iloc[-21] - 1) * 100 if len(close_prices) >= 21 else 0
                
                analysis[period] = {
                    'current_price': current_price,
                    'ma_20': ma_20,
                    'ma_50': ma_50,
                    'rsi': rsi,
                    'returns_1w': returns_1w,
                    'returns_1m': returns_1m,
                    'trend': self._determine_trend(current_price, ma_20, ma_50, rsi)
                }
            
            # Aggregate analysis (like your composite_score)
            overall_trend = self._aggregate_trend_signals(analysis)
            
            return {
                'direction': overall_trend,
                'confidence': self._calculate_trend_confidence(analysis),
                'details': analysis,
                'data_source': 'yfinance_fallback',
                'last_updated': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing NIFTY direction with yfinance: {e}")
            return {
                'direction': 'neutral',
                'confidence': 0.5,
                'details': {},
                'data_source': 'fallback_default',
                'error': str(e)
            }
    
    def get_vix_environment(self) -> Dict[str, Any]:
        """
        Get VIX environment using existing Dhan VIX historical data scripts
        """
        try:
            # First try to use the existing Dhan VIX historical data
            vix_historical_data = self._get_dhan_vix_data()
            
            if vix_historical_data and len(vix_historical_data) > 0:
                # Use Dhan historical data for better analysis
                return self._analyze_dhan_vix_data(vix_historical_data)
            else:
                # Fallback to yfinance if Dhan data not available
                logger.warning("Dhan VIX data not available, falling back to yfinance")
                return self._analyze_yfinance_vix_data()
            
        except Exception as e:
            logger.error(f"Error analyzing VIX environment: {e}")
            return {
                'level': 'normal',
                'current_vix': None,
                'percentile': 50,
                'error': str(e)
            }
    
    def _get_dhan_vix_data(self) -> List[Dict]:
        """
        Get VIX data using the existing Dhan historical data fetcher
        """
        try:
            # Import the existing VIX fetcher
            import sys
            import os
            sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'data_scripts'))
            
            from india_vix_historical_data import IndiaVixHistoricalDataFetcher
            
            # Initialize fetcher
            fetcher = IndiaVixHistoricalDataFetcher()
            
            # Get last 90 days of VIX data
            vix_data = fetcher.get_historical_data(days=90)
            
            if vix_data:
                logger.info(f"Successfully fetched {len(vix_data)} days of VIX data from Dhan")
                return vix_data
            else:
                logger.warning("No VIX data returned from Dhan fetcher")
                return []
                
        except Exception as e:
            logger.warning(f"Error fetching Dhan VIX data: {e}")
            return []
    
    def _analyze_dhan_vix_data(self, vix_data: List[Dict]) -> Dict[str, Any]:
        """
        Analyze VIX environment using Dhan historical data
        """
        try:
            # Convert to pandas for easier analysis
            df = pd.DataFrame(vix_data)
            
            # Sort by date to ensure chronological order
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            
            # Get current VIX (latest close)
            current_vix = df['close'].iloc[-1]
            
            # Calculate VIX percentile over 90-day period
            vix_percentile = (df['close'] <= current_vix).mean() * 100
            
            # Calculate moving averages for trend analysis
            df['ma_5'] = df['close'].rolling(5).mean()
            df['ma_20'] = df['close'].rolling(20).mean()
            
            # Get recent moving averages
            vix_ma_5 = df['ma_5'].iloc[-1]
            vix_ma_20 = df['ma_20'].iloc[-1]
            
            # Determine VIX trend
            if current_vix > vix_ma_5 and vix_ma_5 > vix_ma_20:
                vix_trend = 'strongly_rising'
            elif current_vix > vix_ma_5:
                vix_trend = 'rising'
            elif current_vix < vix_ma_5 and vix_ma_5 < vix_ma_20:
                vix_trend = 'strongly_falling'
            elif current_vix < vix_ma_5:
                vix_trend = 'falling'
            else:
                vix_trend = 'sideways'
            
            # Determine VIX environment level
            if current_vix < VIX_THRESHOLDS['low']:
                vix_env = 'low'
            elif current_vix < VIX_THRESHOLDS['normal']:
                vix_env = 'normal'
            elif current_vix < VIX_THRESHOLDS['spike']:
                vix_env = 'high'
            else:
                vix_env = 'spike'
            
            # Calculate volatility statistics
            vix_min_90d = df['close'].min()
            vix_max_90d = df['close'].max()
            vix_mean_90d = df['close'].mean()
            vix_std_90d = df['close'].std()
            
            # Advanced analysis
            days_since_spike = self._days_since_vix_spike(df, threshold=VIX_THRESHOLDS['spike'])
            volatility_regime = self._determine_volatility_regime(current_vix, vix_mean_90d, vix_std_90d)
            
            return {
                'level': vix_env,
                'current_vix': current_vix,
                'percentile': vix_percentile,
                'trend': vix_trend,
                'ma_5': vix_ma_5,
                'ma_20': vix_ma_20,
                'statistics': {
                    'min_90d': vix_min_90d,
                    'max_90d': vix_max_90d,
                    'mean_90d': vix_mean_90d,
                    'std_90d': vix_std_90d
                },
                'advanced_metrics': {
                    'days_since_spike': days_since_spike,
                    'volatility_regime': volatility_regime,
                    'data_points': len(df)
                },
                'interpretation': self._interpret_vix_level_advanced(vix_env, vix_trend, vix_percentile),
                'data_source': 'dhan_historical',
                'last_updated': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing Dhan VIX data: {e}")
            # Fallback to yfinance
            return self._analyze_yfinance_vix_data()
    
    def _analyze_yfinance_vix_data(self) -> Dict[str, Any]:
        """
        Fallback VIX analysis using yfinance (original method)
        """
        try:
            vix_data = yf.Ticker("^INDIAVIX")
            hist = vix_data.history(period="6mo")
            
            if hist.empty:
                logger.warning("No VIX data available from yfinance")
                return {'level': 'normal', 'current_vix': None, 'percentile': 50}
            
            current_vix = hist['Close'].iloc[-1]
            vix_percentile = (hist['Close'] <= current_vix).mean() * 100
            
            # Determine environment
            if current_vix < VIX_THRESHOLDS['low']:
                vix_env = 'low'
            elif current_vix < VIX_THRESHOLDS['normal']:
                vix_env = 'normal'
            elif current_vix < VIX_THRESHOLDS['spike']:
                vix_env = 'high'
            else:
                vix_env = 'spike'
            
            # VIX trend analysis
            vix_ma_5 = hist['Close'].rolling(5).mean().iloc[-1]
            vix_trend = 'rising' if current_vix > vix_ma_5 else 'falling'
            
            return {
                'level': vix_env,
                'current_vix': current_vix,
                'percentile': vix_percentile,
                'trend': vix_trend,
                'ma_5': vix_ma_5,
                'interpretation': self._interpret_vix_level(vix_env, vix_trend),
                'data_source': 'yfinance_fallback',
                'last_updated': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Error with yfinance VIX data: {e}")
            return {
                'level': 'normal',
                'current_vix': None,
                'percentile': 50,
                'data_source': 'fallback_default',
                'error': str(e)
            }
    
    def _days_since_vix_spike(self, df: pd.DataFrame, threshold: float = 25.0) -> Optional[int]:
        """Calculate days since last VIX spike above threshold"""
        try:
            spike_dates = df[df['close'] > threshold]['date']
            if len(spike_dates) > 0:
                last_spike = spike_dates.max()
                days_since = (df['date'].max() - last_spike).days
                return days_since
            return None
        except Exception:
            return None
    
    def _determine_volatility_regime(self, current_vix: float, mean_vix: float, std_vix: float) -> str:
        """Determine current volatility regime based on statistical analysis"""
        try:
            z_score = (current_vix - mean_vix) / std_vix
            
            if z_score > 2:
                return 'extreme_high'
            elif z_score > 1:
                return 'high'
            elif z_score > -1:
                return 'normal'
            elif z_score > -2:
                return 'low'
            else:
                return 'extreme_low'
        except Exception:
            return 'normal'
    
    def _interpret_vix_level_advanced(self, level: str, trend: str, percentile: float) -> str:
        """Advanced VIX interpretation with more context"""
        base_interpretations = {
            'low': 'Complacency - Consider buying volatility',
            'normal': 'Balanced volatility environment',
            'high': 'Elevated fear - Consider selling volatility',
            'spike': 'Extreme fear - Major market stress'
        }
        
        trend_context = {
            'strongly_rising': 'with strong upward momentum',
            'rising': 'with upward momentum',
            'sideways': 'with neutral momentum',
            'falling': 'with downward momentum',
            'strongly_falling': 'with strong downward momentum'
        }
        
        base = base_interpretations.get(level, 'Unknown')
        trend_desc = trend_context.get(trend, '')
        percentile_desc = f" ({percentile:.0f}th percentile)"
        
        return f"{base} {trend_desc}{percentile_desc}"
    
    def get_options_sentiment_from_db(self) -> Dict[str, Any]:
        """
        Calculate PCR and options sentiment from option_chain_data table
        (Using your existing database with index=YES filter)
        """
        try:
            if not self.supabase:
                logger.warning("No Supabase client available for PCR calculation")
                return {'pcr': 1.0, 'sentiment': 'neutral', 'error': 'No database connection'}
            
            # Query NIFTY options data from your database
            query = self.supabase.table('option_chain_data') \
                .select('option_type,volume,open_interest,strike_price,underlying_price') \
                .eq('index', True) \
                .eq('symbol', 'NIFTY 50') \
                .order('data_timestamp', desc=True) \
                .limit(1000)  # Get recent data
            
            result = query.execute()
            
            if not result.data:
                logger.warning("No NIFTY options data found in database")
                return {'pcr': 1.0, 'sentiment': 'neutral', 'error': 'No data'}
            
            df = pd.DataFrame(result.data)
            
            # Calculate PCR by volume and OI (like your options analysis)
            call_volume = df[df['option_type'] == 'CALL']['volume'].sum()
            put_volume = df[df['option_type'] == 'PUT']['volume'].sum()
            
            call_oi = df[df['option_type'] == 'CALL']['open_interest'].sum()
            put_oi = df[df['option_type'] == 'PUT']['open_interest'].sum()
            
            # Calculate ratios
            pcr_volume = put_volume / call_volume if call_volume > 0 else 1.0
            pcr_oi = put_oi / call_oi if call_oi > 0 else 1.0
            
            # Average PCR
            avg_pcr = (pcr_volume + pcr_oi) / 2
            
            # Calculate Max Pain (like your max_pain analysis)
            max_pain = self._calculate_max_pain(df)
            
            # Interpret sentiment
            sentiment = self._interpret_pcr(avg_pcr)
            
            return {
                'pcr': avg_pcr,
                'pcr_volume': pcr_volume,
                'pcr_oi': pcr_oi,
                'sentiment': sentiment,
                'max_pain': max_pain,
                'call_volume': call_volume,
                'put_volume': put_volume,
                'call_oi': call_oi,
                'put_oi': put_oi,
                'last_updated': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Error calculating options sentiment: {e}")
            return {
                'pcr': 1.0,
                'sentiment': 'neutral',
                'error': str(e)
            }
    
    def get_current_market_condition(self) -> Dict[str, Any]:
        """
        Combine all market factors to determine overall condition
        (Like your MARKET_CONDITION determination)
        """
        try:
            # Get all components
            nifty_analysis = self.get_nifty_direction()
            vix_analysis = self.get_vix_environment()
            options_sentiment = self.get_options_sentiment_from_db()
            
            # Determine combined condition
            direction = nifty_analysis['direction']
            vix_level = vix_analysis['level']
            
            # Create condition key
            condition_key = f"{direction.title()}_{vix_level.title()}_VIX"
            
            # Validate against our defined conditions
            if condition_key not in MARKET_CONDITIONS:
                logger.warning(f"Condition {condition_key} not defined, using default")
                condition_key = 'Neutral_Normal_VIX'
            
            condition_config = MARKET_CONDITIONS[condition_key]
            
            # Calculate overall confidence
            confidence = self._calculate_overall_confidence(
                nifty_analysis, vix_analysis, options_sentiment
            )
            
            # Validate PCR alignment
            pcr = options_sentiment.get('pcr', 1.0)
            pcr_range = condition_config.get('pcr_range', (0.8, 1.2))
            pcr_aligned = pcr_range[0] <= pcr <= pcr_range[1]
            
            self.current_conditions = {
                'condition': condition_key,
                'config': condition_config,
                'confidence': confidence,
                'components': {
                    'nifty': nifty_analysis,
                    'vix': vix_analysis,
                    'options': options_sentiment
                },
                'pcr_aligned': pcr_aligned,
                'last_updated': datetime.now(),
                'next_update': datetime.now() + timedelta(hours=1)  # Cache for 1 hour
            }
            
            return self.current_conditions
            
        except Exception as e:
            logger.error(f"Error determining market condition: {e}")
            return {
                'condition': 'Neutral_Normal_VIX',
                'config': MARKET_CONDITIONS['Neutral_Normal_VIX'],
                'confidence': 0.5,
                'error': str(e)
            }
    
    def _determine_trend(self, price: float, ma_20: float, ma_50: Optional[float], rsi: float) -> str:
        """Determine trend based on technical indicators"""
        if ma_50 is None:
            # Use only MA20 and RSI
            if price > ma_20 and rsi > 50:
                return 'bullish'
            elif price < ma_20 and rsi < 50:
                return 'bearish'
            else:
                return 'neutral'
        else:
            # Use all indicators
            if price > ma_20 > ma_50 and rsi > 55:
                return 'bullish'
            elif price < ma_20 < ma_50 and rsi < 45:
                return 'bearish'
            else:
                return 'neutral'
    
    def _aggregate_trend_signals(self, analysis: Dict) -> str:
        """Aggregate trends across timeframes"""
        trends = [data['trend'] for data in analysis.values()]
        
        bullish_count = trends.count('bullish')
        bearish_count = trends.count('bearish')
        
        if bullish_count > bearish_count:
            return 'bullish'
        elif bearish_count > bullish_count:
            return 'bearish'
        else:
            return 'neutral'
    
    def _calculate_trend_confidence(self, analysis: Dict) -> float:
        """Calculate confidence in trend analysis"""
        if not analysis:
            return 0.5
        
        trends = [data['trend'] for data in analysis.values()]
        dominant_trend = max(set(trends), key=trends.count)
        confidence = trends.count(dominant_trend) / len(trends)
        
        return confidence
    
    def _interpret_vix_level(self, level: str, trend: str) -> str:
        """Interpret VIX level and trend"""
        interpretations = {
            'low': 'Complacency - Consider buying volatility',
            'normal': 'Balanced volatility environment',
            'high': 'Elevated fear - Consider selling volatility',
            'spike': 'Extreme fear - Major market stress'
        }
        
        base = interpretations.get(level, 'Unknown')
        return f"{base} (VIX {trend})"
    
    def _calculate_max_pain(self, df: pd.DataFrame) -> Optional[float]:
        """Calculate max pain from options data"""
        try:
            # Group by strike and sum OI
            strikes = df.groupby('strike_price')['open_interest'].sum().reset_index()
            
            if strikes.empty:
                return None
            
            # Find strike with maximum OI (simplified max pain)
            if strikes.empty or strikes['open_interest'].isna().all():
                return None
            max_pain_strike = strikes.loc[strikes['open_interest'].idxmax(), 'strike_price']
            
            return float(max_pain_strike)
            
        except Exception as e:
            logger.error(f"Error calculating max pain: {e}")
            return None
    
    def _interpret_pcr(self, pcr: float) -> str:
        """Interpret PCR value"""
        if pcr >= PCR_INTERPRETATION['extreme_bearish']:
            return 'extreme_bearish'
        elif pcr >= PCR_INTERPRETATION['bearish']:
            return 'bearish'
        elif pcr >= PCR_INTERPRETATION['bullish']:
            return 'neutral'
        elif pcr >= PCR_INTERPRETATION['extreme_bullish']:
            return 'bullish'
        else:
            return 'extreme_bullish'
    
    def _calculate_overall_confidence(self, nifty: Dict, vix: Dict, options: Dict) -> float:
        """Calculate overall confidence in market condition"""
        confidences = []
        
        # NIFTY confidence
        if 'confidence' in nifty:
            confidences.append(nifty['confidence'])
        
        # VIX confidence (based on data availability)
        if vix.get('current_vix') is not None:
            confidences.append(0.8)  # High confidence if VIX data available
        
        # Options confidence (based on data quality)
        if options.get('pcr') and 'error' not in options:
            confidences.append(0.9)  # High confidence if PCR calculated
        
        return np.mean(confidences) if confidences else 0.5
    
    def is_cache_valid(self) -> bool:
        """Check if cached market conditions are still valid"""
        if not self.current_conditions:
            return False
        
        next_update = self.current_conditions.get('next_update')
        if not next_update:
            return False
        
        return datetime.now() < next_update
    
    def get_cached_conditions(self) -> Optional[Dict]:
        """Get cached market conditions if valid"""
        if self.is_cache_valid():
            return self.current_conditions
        return None