"""
Market Direction Analyzer for Nifty
Determines bullish/bearish bias using technical indicators, options flow, and price action
"""

import logging
from typing import Dict, Tuple
from dataclasses import dataclass
import numpy as np
import sys
import os

# Add parent directories to path to import from core
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, parent_dir)

logger = logging.getLogger(__name__)

try:
    # Import from the main options_v4 core directory
    sys.path.insert(0, os.path.join(parent_dir, 'core'))
    from market_conditions_analyzer import MarketConditionsAnalyzer
except ImportError as e:
    logger.error(f"CRITICAL: Could not import MarketConditionsAnalyzer: {e}")
    logger.error("This is a REAL trading system - cannot use mock data!")
    raise ImportError("MarketConditionsAnalyzer is required for real trading system") from e


@dataclass
class MarketDirectionScore:
    """Market direction analysis results"""
    technical_score: float  # -1 to 1
    options_flow_score: float  # -1 to 1
    price_action_score: float  # -1 to 1
    composite_score: float  # -1 to 1
    market_state: str  # strong_bullish, moderate_bullish, etc.
    confidence: float  # 0 to 1


class MarketDirectionAnalyzer:
    """Analyzes Nifty market direction using multiple signals"""
    
    # Weights for composite score
    TECHNICAL_WEIGHT = 0.40
    OPTIONS_FLOW_WEIGHT = 0.35
    PRICE_ACTION_WEIGHT = 0.25
    
    def __init__(self, supabase_client=None):
        self.supabase = supabase_client
        # Initialize the existing market conditions analyzer - REQUIRED for real trading
        if not supabase_client:
            raise ValueError("Database client is required for real trading system")
        self.market_analyzer = MarketConditionsAnalyzer(supabase_client)
        
    def get_market_direction(self) -> MarketDirectionScore:
        """Get current market direction score"""
        try:
            # Use existing market conditions analyzer - REQUIRED for real trading
            # Get Nifty direction from existing analyzer
            nifty_analysis = self.market_analyzer.get_nifty_direction()
            vix_analysis = self.market_analyzer.get_vix_environment()
            options_analysis = self.market_analyzer.get_options_sentiment_from_db()
            
            # Use enhanced scoring based on rich data from MarketConditionsAnalyzer
            # Technical score: Use momentum and strength indicators
            momentum_score = nifty_analysis.get('momentum_score', {}).get('score', 0.5)
            overall_strength = nifty_analysis.get('strength_indicators', {}).get('overall_strength', 0.5)
            rsi = nifty_analysis.get('strength_indicators', {}).get('current_rsi', 50)
            
            # Convert momentum and strength to technical score
            technical_score = self._calculate_enhanced_technical_score(
                momentum_score, overall_strength, rsi, nifty_analysis.get('confidence', 0.5)
            )
            
            # Convert PCR to options flow score (enhanced)
            pcr = options_analysis.get('pcr', 1.0)
            pcr_volume = options_analysis.get('pcr_volume', 1.0)
            pcr_oi = options_analysis.get('pcr_oi', 1.0)
            options_flow_score = self._calculate_enhanced_options_score(pcr, pcr_volume, pcr_oi)
            
            # Use momentum as price action score
            momentum_data = nifty_analysis.get('momentum_score', {})
            price_action_score = momentum_data.get('score', 0.5) * 2 - 1  # Convert 0-1 to -1 to 1
            
            # Calculate composite score
            composite_score = (
                self.TECHNICAL_WEIGHT * technical_score +
                self.OPTIONS_FLOW_WEIGHT * options_flow_score +
                self.PRICE_ACTION_WEIGHT * price_action_score
            )
            
            # Use the confidence from Nifty analysis
            confidence = nifty_analysis.get('confidence', 0.5)
            
            # Determine market state
            market_state = self._get_market_state(composite_score)
            
            # Calculate confidence based on agreement between signals
            final_confidence = self._calculate_confidence(
                technical_score, options_flow_score, price_action_score
            )
            
            return MarketDirectionScore(
                technical_score=technical_score,
                options_flow_score=options_flow_score,
                price_action_score=price_action_score,
                composite_score=composite_score,
                market_state=market_state,
                confidence=final_confidence
            )
            
        except Exception as e:
            logger.error(f"CRITICAL ERROR in market direction analysis: {e}")
            logger.error("Real trading system cannot continue without market direction data!")
            raise RuntimeError(f"Market direction analysis failed: {e}") from e
    
    def _convert_direction_to_score(self, direction: str, confidence: float) -> float:
        """Convert direction string to numeric score (-1 to 1)"""
        direction_map = {
            'bullish': 0.7,
            'bearish': -0.7,
            'neutral': 0.0
        }
        
        base_score = direction_map.get(direction.lower(), 0.0)
        # Scale by confidence
        return base_score * confidence
    
    def _convert_pcr_to_score(self, pcr: float, sentiment: str) -> float:
        """Convert PCR to options flow score (-1 to 1)"""
        # PCR interpretation (contrarian):
        # High PCR (>1.2) = Bearish sentiment = Bullish signal
        # Low PCR (<0.8) = Bullish sentiment = Bearish signal
        
        if pcr > 1.5:
            return 0.8  # Very bullish (contrarian)
        elif pcr > 1.2:
            return 0.5  # Bullish
        elif pcr > 1.0:
            return 0.2  # Slightly bullish
        elif pcr > 0.8:
            return 0.0  # Neutral
        elif pcr > 0.6:
            return -0.3  # Slightly bearish
        else:
            return -0.6  # Bearish (contrarian)
    
    def _calculate_enhanced_technical_score(self, momentum: float, strength: float, rsi: float, confidence: float) -> float:
        """Calculate enhanced technical score using momentum, strength, and RSI"""
        # Convert momentum (0-1) to score (-1 to 1)
        momentum_score = (momentum - 0.5) * 2
        
        # Convert strength (0-1) to score (-1 to 1)
        strength_score = (strength - 0.5) * 2
        
        # Convert RSI to score (-1 to 1)
        if rsi > 70:
            rsi_score = -0.5  # Overbought
        elif rsi > 60:
            rsi_score = 0.3   # Bullish
        elif rsi > 50:
            rsi_score = 0.1   # Slightly bullish
        elif rsi > 40:
            rsi_score = -0.1  # Slightly bearish
        elif rsi > 30:
            rsi_score = -0.3  # Bearish
        else:
            rsi_score = 0.5   # Oversold (bullish contrarian)
        
        # Weighted combination
        composite = (0.5 * momentum_score + 0.3 * strength_score + 0.2 * rsi_score)
        
        # Apply confidence scaling
        return composite * confidence
    
    def _calculate_enhanced_options_score(self, pcr: float, pcr_volume: float, pcr_oi: float) -> float:
        """Calculate enhanced options flow score using PCR, volume PCR, and OI PCR"""
        # Get individual scores
        pcr_score = self._convert_pcr_to_score(pcr, 'neutral')
        vol_score = self._convert_pcr_to_score(pcr_volume, 'neutral') 
        oi_score = self._convert_pcr_to_score(pcr_oi, 'neutral')
        
        # Weighted combination (volume PCR is most important for immediate sentiment)
        return 0.5 * vol_score + 0.3 * pcr_score + 0.2 * oi_score
    
    def _get_market_state(self, composite_score: float) -> str:
        """Convert composite score to market state"""
        if composite_score > 0.6:
            return "strong_bullish"
        elif composite_score > 0.2:
            return "moderate_bullish"
        elif composite_score > -0.2:
            return "neutral"
        elif composite_score > -0.6:
            return "moderate_bearish"
        else:
            return "strong_bearish"
    
    def _calculate_confidence(self, technical: float, options_flow: float, price_action: float) -> float:
        """Calculate confidence based on signal agreement"""
        signals = [technical, options_flow, price_action]
        
        # Check if signals agree (same direction)
        positive_count = sum(1 for s in signals if s > 0.1)
        negative_count = sum(1 for s in signals if s < -0.1)
        neutral_count = len(signals) - positive_count - negative_count
        
        if positive_count >= 2 or negative_count >= 2:
            return 0.8  # High confidence when 2+ signals agree
        elif positive_count == 1 and negative_count == 1:
            return 0.4  # Low confidence when signals conflict
        else:
            return 0.6  # Medium confidence
    
    # DEPRECATED METHODS - Use MarketConditionsAnalyzer instead
    def _analyze_technical_indicators(self) -> float:
        """DEPRECATED: Use MarketConditionsAnalyzer.get_nifty_direction() instead"""
        raise NotImplementedError("Use MarketConditionsAnalyzer.get_nifty_direction() instead")
    
    def _analyze_options_flow(self) -> float:
        """DEPRECATED: Use MarketConditionsAnalyzer.get_options_sentiment_from_db() instead"""
        raise NotImplementedError("Use MarketConditionsAnalyzer.get_options_sentiment_from_db() instead")
    
    def _analyze_price_action(self) -> float:
        """DEPRECATED: Use MarketConditionsAnalyzer.get_nifty_direction() instead"""
        raise NotImplementedError("Use MarketConditionsAnalyzer.get_nifty_direction() instead")
    
    def get_long_short_ratio(self) -> Tuple[float, float]:
        """Get recommended long/short allocation ratio"""
        direction = self.get_market_direction()
        
        # Ratios from config
        ratio_map = {
            "strong_bullish": (80, 20),
            "moderate_bullish": (70, 30),
            "weak_bullish": (60, 40),
            "neutral": (50, 50),
            "weak_bearish": (40, 60),
            "moderate_bearish": (30, 70),
            "strong_bearish": (20, 80)
        }
        
        return ratio_map.get(direction.market_state, (50, 50))