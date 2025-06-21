"""
Technical Analysis Module for Options V4
Incorporates essential technical indicators from tecnicalopy.py
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, Optional, Tuple
import yfinance as yf
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class TechnicalAnalyzer:
    """
    Technical analysis for options strategy selection
    Based on the proven tecnicalopy.py implementation
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def analyze_technical_indicators(self, symbol: str, period: str = '3mo', 
                                   interval: str = '1d') -> Dict:
        """
        Perform comprehensive technical analysis
        
        Args:
            symbol: Stock symbol
            period: Data period (3mo, 6mo, 1y)
            interval: Data interval (1d, 1h, 5m)
        
        Returns:
            Dictionary with technical analysis results
        """
        try:
            # Fetch historical data
            df = self._fetch_price_data(symbol, period, interval)
            if df.empty:
                return self._empty_technical_analysis()
            
            # Calculate all technical indicators
            analysis = {
                'price_trend': self._analyze_price_trend(df),
                'momentum': self._analyze_momentum(df),
                'volume': self._analyze_volume(df),
                'volatility': self._calculate_volatility(df),
                'support_resistance': self._find_support_resistance(df),
                'patterns': self._identify_patterns(df),
                'overall_signal': self._calculate_overall_signal(df)
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error in technical analysis for {symbol}: {e}")
            return self._empty_technical_analysis()
    
    def _fetch_price_data(self, symbol: str, period: str, interval: str) -> pd.DataFrame:
        """Fetch price data from Yahoo Finance"""
        try:
            ticker = yf.Ticker(f"{symbol}.NS")  # NSE suffix for Indian stocks
            df = ticker.history(period=period, interval=interval)
            
            if df.empty:
                # Try without suffix
                ticker = yf.Ticker(symbol)
                df = ticker.history(period=period, interval=interval)
            
            return df
            
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            return pd.DataFrame()
    
    def _analyze_price_trend(self, df: pd.DataFrame) -> Dict:
        """Analyze price trend using EMAs and ADX"""
        try:
            current_price = df['Close'].iloc[-1]
            start_price = df['Close'].iloc[0]
            
            # Calculate EMAs if enough data
            ema_values = {}
            data_length = len(df)
            
            ema_periods = {
                'ema_20': 20,
                'ema_50': 50,
                'ema_200': 200
            }
            
            for ema_name, period in ema_periods.items():
                if data_length >= period:
                    ema_values[ema_name] = df['Close'].ewm(span=period, adjust=False).mean().iloc[-1]
                else:
                    ema_values[ema_name] = None
            
            # Determine trend
            if ema_values.get('ema_20') and ema_values.get('ema_50'):
                trend = "Uptrend" if ema_values['ema_20'] > ema_values['ema_50'] else "Downtrend"
            else:
                trend = "Uptrend" if current_price > start_price else "Downtrend"
            
            # EMA alignment
            if all(v is not None for v in ema_values.values()):
                if ema_values['ema_20'] > ema_values['ema_50'] > ema_values['ema_200']:
                    ema_alignment = "Bullish"
                elif ema_values['ema_20'] < ema_values['ema_50'] < ema_values['ema_200']:
                    ema_alignment = "Bearish"
                else:
                    ema_alignment = "Mixed"
            else:
                ema_alignment = "Insufficient Data"
            
            return {
                'trend': trend,
                'ema_alignment': ema_alignment,
                'ema_values': ema_values,
                'price_change_pct': ((current_price - start_price) / start_price) * 100
            }
            
        except Exception as e:
            logger.error(f"Error analyzing price trend: {e}")
            return {'trend': 'Unknown', 'ema_alignment': 'Unknown'}
    
    def _analyze_momentum(self, df: pd.DataFrame) -> Dict:
        """Analyze momentum indicators (RSI, MACD)"""
        try:
            # RSI Calculation
            rsi = self._calculate_rsi(df['Close'])
            
            # MACD Calculation
            exp1 = df['Close'].ewm(span=12, adjust=False).mean()
            exp2 = df['Close'].ewm(span=26, adjust=False).mean()
            macd = exp1 - exp2
            signal = macd.ewm(span=9, adjust=False).mean()
            macd_histogram = macd - signal
            
            # Momentum signals
            rsi_signal = "Oversold" if rsi < 30 else "Overbought" if rsi > 70 else "Neutral"
            macd_signal = "Bullish" if macd.iloc[-1] > signal.iloc[-1] else "Bearish"
            
            return {
                'rsi': rsi,
                'rsi_signal': rsi_signal,
                'macd': macd.iloc[-1],
                'macd_signal_line': signal.iloc[-1],
                'macd_histogram': macd_histogram.iloc[-1],
                'macd_signal': macd_signal
            }
            
        except Exception as e:
            logger.error(f"Error analyzing momentum: {e}")
            return {'rsi': 50, 'rsi_signal': 'Neutral', 'macd_signal': 'Neutral'}
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """Calculate RSI"""
        try:
            deltas = prices.diff()
            gain = (deltas.where(deltas > 0, 0)).rolling(window=period).mean()
            loss = (-deltas.where(deltas < 0, 0)).rolling(window=period).mean()
            
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            return rsi.iloc[-1]
            
        except Exception as e:
            logger.error(f"Error calculating RSI: {e}")
            return 50.0
    
    def _analyze_volume(self, df: pd.DataFrame) -> Dict:
        """Analyze volume patterns"""
        try:
            current_volume = df['Volume'].iloc[-1]
            avg_volume = df['Volume'].rolling(window=20).mean().iloc[-1]
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
            
            # Volume trend
            volume_sma = df['Volume'].rolling(window=5).mean()
            volume_trend = "Increasing" if volume_sma.iloc[-1] > volume_sma.iloc[-5] else "Decreasing"
            
            return {
                'current_volume': current_volume,
                'avg_volume_20d': avg_volume,
                'volume_ratio': volume_ratio,
                'volume_trend': volume_trend,
                'volume_signal': "High" if volume_ratio > 1.5 else "Low" if volume_ratio < 0.5 else "Normal"
            }
            
        except Exception as e:
            logger.error(f"Error analyzing volume: {e}")
            return {'volume_signal': 'Normal', 'volume_trend': 'Unknown'}
    
    def _calculate_volatility(self, df: pd.DataFrame) -> Dict:
        """Calculate volatility metrics"""
        try:
            # Historical volatility (20-day)
            returns = df['Close'].pct_change()
            hist_vol = returns.rolling(window=20).std() * np.sqrt(252) * 100
            current_vol = hist_vol.iloc[-1]
            
            # ATR (Average True Range)
            high_low = df['High'] - df['Low']
            high_close = np.abs(df['High'] - df['Close'].shift())
            low_close = np.abs(df['Low'] - df['Close'].shift())
            
            ranges = pd.concat([high_low, high_close, low_close], axis=1)
            true_range = np.max(ranges, axis=1)
            atr = true_range.rolling(14).mean().iloc[-1]
            
            # Bollinger Bands
            sma = df['Close'].rolling(window=20).mean()
            std = df['Close'].rolling(window=20).std()
            upper_band = sma + (std * 2)
            lower_band = sma - (std * 2)
            
            bb_position = (df['Close'].iloc[-1] - lower_band.iloc[-1]) / (upper_band.iloc[-1] - lower_band.iloc[-1])
            
            return {
                'historical_volatility': current_vol,
                'atr': atr,
                'atr_pct': (atr / df['Close'].iloc[-1]) * 100,
                'bollinger_position': bb_position,
                'volatility_regime': "High" if current_vol > 30 else "Low" if current_vol < 15 else "Normal"
            }
            
        except Exception as e:
            logger.error(f"Error calculating volatility: {e}")
            return {'volatility_regime': 'Normal', 'historical_volatility': 20}
    
    def _find_support_resistance(self, df: pd.DataFrame) -> Dict:
        """Find key support and resistance levels"""
        try:
            current_price = df['Close'].iloc[-1]
            
            # Recent highs and lows
            recent_high = df['High'].rolling(window=20).max().iloc[-1]
            recent_low = df['Low'].rolling(window=20).min().iloc[-1]
            
            # Pivot points
            pivot = (df['High'].iloc[-1] + df['Low'].iloc[-1] + df['Close'].iloc[-1]) / 3
            r1 = 2 * pivot - df['Low'].iloc[-1]
            s1 = 2 * pivot - df['High'].iloc[-1]
            
            return {
                'current_price': current_price,
                'resistance_1': r1,
                'support_1': s1,
                'recent_high': recent_high,
                'recent_low': recent_low,
                'pivot_point': pivot,
                'price_position': "Near Resistance" if current_price > (recent_high * 0.95) else 
                                "Near Support" if current_price < (recent_low * 1.05) else "Mid-Range"
            }
            
        except Exception as e:
            logger.error(f"Error finding support/resistance: {e}")
            return {'price_position': 'Unknown'}
    
    def _identify_patterns(self, df: pd.DataFrame) -> Dict:
        """Identify basic price patterns"""
        try:
            # Simple pattern detection
            closes = df['Close'].values[-10:]  # Last 10 days
            
            # Higher highs and higher lows (uptrend)
            highs = df['High'].values[-10:]
            lows = df['Low'].values[-10:]
            
            higher_highs = all(highs[i] <= highs[i+1] for i in range(len(highs)-3, len(highs)-1))
            higher_lows = all(lows[i] <= lows[i+1] for i in range(len(lows)-3, len(lows)-1))
            
            lower_highs = all(highs[i] >= highs[i+1] for i in range(len(highs)-3, len(highs)-1))
            lower_lows = all(lows[i] >= lows[i+1] for i in range(len(lows)-3, len(lows)-1))
            
            if higher_highs and higher_lows:
                pattern = "Uptrend Pattern"
            elif lower_highs and lower_lows:
                pattern = "Downtrend Pattern"
            else:
                pattern = "Consolidation"
            
            return {
                'pattern': pattern,
                'trend_strength': "Strong" if (higher_highs and higher_lows) or (lower_highs and lower_lows) else "Weak"
            }
            
        except Exception as e:
            logger.error(f"Error identifying patterns: {e}")
            return {'pattern': 'Unknown', 'trend_strength': 'Unknown'}
    
    def _calculate_overall_signal(self, df: pd.DataFrame) -> Dict:
        """Calculate overall technical signal"""
        try:
            # Gather all signals
            trend = self._analyze_price_trend(df)
            momentum = self._analyze_momentum(df)
            
            bullish_signals = 0
            bearish_signals = 0
            
            # Count signals
            if trend['trend'] == "Uptrend":
                bullish_signals += 1
            else:
                bearish_signals += 1
            
            if trend.get('ema_alignment') == "Bullish":
                bullish_signals += 1
            elif trend.get('ema_alignment') == "Bearish":
                bearish_signals += 1
            
            if momentum['rsi_signal'] == "Oversold":
                bullish_signals += 1
            elif momentum['rsi_signal'] == "Overbought":
                bearish_signals += 1
            
            if momentum['macd_signal'] == "Bullish":
                bullish_signals += 1
            else:
                bearish_signals += 1
            
            # Overall signal
            total_signals = bullish_signals + bearish_signals
            if total_signals > 0:
                bullish_pct = bullish_signals / total_signals
                if bullish_pct > 0.7:
                    overall = "Strong Buy"
                elif bullish_pct > 0.5:
                    overall = "Buy"
                elif bullish_pct < 0.3:
                    overall = "Strong Sell"
                elif bullish_pct < 0.5:
                    overall = "Sell"
                else:
                    overall = "Neutral"
            else:
                overall = "Neutral"
            
            return {
                'signal': overall,
                'bullish_signals': bullish_signals,
                'bearish_signals': bearish_signals,
                'confidence': abs(bullish_signals - bearish_signals) / max(total_signals, 1)
            }
            
        except Exception as e:
            logger.error(f"Error calculating overall signal: {e}")
            return {'signal': 'Neutral', 'confidence': 0}
    
    def _empty_technical_analysis(self) -> Dict:
        """Return empty technical analysis structure"""
        return {
            'price_trend': {'trend': 'Unknown', 'ema_alignment': 'Unknown'},
            'momentum': {'rsi_signal': 'Neutral', 'macd_signal': 'Neutral'},
            'volume': {'volume_signal': 'Normal', 'volume_trend': 'Unknown'},
            'volatility': {'volatility_regime': 'Normal'},
            'support_resistance': {'price_position': 'Unknown'},
            'patterns': {'pattern': 'Unknown'},
            'overall_signal': {'signal': 'Neutral', 'confidence': 0}
        }