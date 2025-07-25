"""
Strategy Metadata and Registry System

Defines characteristics for all strategies to enable smart selection
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
from enum import Enum

class MarketBias(Enum):
    """Market direction bias for strategies"""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    ANY = "any"

class IVEnvironment(Enum):
    """IV environment preferences"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    ELEVATED = "elevated"
    SUBDUED = "subdued"
    EXTREME = "extreme"  # Added for very high IV scenarios
    ANY = "any"

class TimeDecayProfile(Enum):
    """Time decay characteristics"""
    POSITIVE = "positive"  # Benefits from time decay
    NEGATIVE = "negative"  # Hurt by time decay
    NEUTRAL = "neutral"    # Minimal time impact

@dataclass
class StrategyMetadata:
    """Metadata for each strategy defining its characteristics"""
    name: str
    category: str  # directional, neutral, volatility, income, advanced
    market_bias: List[MarketBias]  # Market conditions where strategy works
    iv_preference: List[IVEnvironment]  # Preferred IV environments
    complexity: int  # 1-5 (1=simple, 5=complex)
    capital_efficiency: float  # 0-1 (0=ties up lots of capital, 1=very efficient)
    time_decay_profile: TimeDecayProfile
    liquidity_requirements: str  # low, medium, high
    risk_profile: str  # limited, unlimited, defined
    description: str

# Strategy Registry with comprehensive metadata
STRATEGY_REGISTRY = {
    # Directional Strategies
    "Long Call": StrategyMetadata(
        name="Long Call",
        category="directional",
        market_bias=[MarketBias.BULLISH],  # Removed NEUTRAL - should only be for bullish views
        iv_preference=[IVEnvironment.LOW, IVEnvironment.SUBDUED, IVEnvironment.NORMAL],
        complexity=1,
        capital_efficiency=0.9,
        time_decay_profile=TimeDecayProfile.NEGATIVE,
        liquidity_requirements="low",
        risk_profile="limited",
        description="Simple bullish bet with limited risk"
    ),
    
    "Long Put": StrategyMetadata(
        name="Long Put",
        category="directional",
        market_bias=[MarketBias.BEARISH],  # Removed NEUTRAL - should only be for bearish views
        iv_preference=[IVEnvironment.LOW, IVEnvironment.SUBDUED, IVEnvironment.NORMAL],
        complexity=1,
        capital_efficiency=0.9,
        time_decay_profile=TimeDecayProfile.NEGATIVE,
        liquidity_requirements="low",
        risk_profile="limited",
        description="Simple bearish bet with limited risk"
    ),
    
    "Short Call": StrategyMetadata(
        name="Short Call",
        category="directional",
        market_bias=[MarketBias.BEARISH, MarketBias.NEUTRAL],
        iv_preference=[IVEnvironment.HIGH, IVEnvironment.ELEVATED],
        complexity=2,
        capital_efficiency=0.3,  # Ties up margin
        time_decay_profile=TimeDecayProfile.POSITIVE,
        liquidity_requirements="low",
        risk_profile="unlimited",
        description="Premium collection with unlimited upside risk"
    ),
    
    "Short Put": StrategyMetadata(
        name="Short Put",
        category="directional", 
        market_bias=[MarketBias.BULLISH, MarketBias.NEUTRAL],
        iv_preference=[IVEnvironment.HIGH, IVEnvironment.ELEVATED],
        complexity=2,
        capital_efficiency=0.3,  # Ties up margin
        time_decay_profile=TimeDecayProfile.POSITIVE,
        liquidity_requirements="low",
        risk_profile="limited",  # Limited to strike price
        description="Premium collection with downside risk to strike"
    ),
    
    "Bull Call Spread": StrategyMetadata(
        name="Bull Call Spread",
        category="directional",
        market_bias=[MarketBias.BULLISH],
        iv_preference=[IVEnvironment.ANY],
        complexity=2,
        capital_efficiency=0.8,
        time_decay_profile=TimeDecayProfile.NEUTRAL,
        liquidity_requirements="medium",
        risk_profile="limited",
        description="Bullish spread with defined risk/reward"
    ),
    
    "Bear Call Spread": StrategyMetadata(
        name="Bear Call Spread",
        category="directional",
        market_bias=[MarketBias.BEARISH, MarketBias.NEUTRAL],
        iv_preference=[IVEnvironment.HIGH, IVEnvironment.ELEVATED, IVEnvironment.NORMAL],
        complexity=2,
        capital_efficiency=0.6,
        time_decay_profile=TimeDecayProfile.POSITIVE,
        liquidity_requirements="medium",
        risk_profile="limited",
        description="Bearish credit spread benefiting from time decay"
    ),
    
    "Bull Put Spread": StrategyMetadata(
        name="Bull Put Spread",
        category="directional",
        market_bias=[MarketBias.BULLISH],  # Removed NEUTRAL - primarily bullish strategy
        iv_preference=[IVEnvironment.HIGH, IVEnvironment.ELEVATED, IVEnvironment.NORMAL],  # Better with higher IV
        complexity=2,
        capital_efficiency=0.6,
        time_decay_profile=TimeDecayProfile.POSITIVE,
        liquidity_requirements="medium",
        risk_profile="limited",
        description="Bullish credit spread benefiting from time decay"
    ),
    
    "Bear Put Spread": StrategyMetadata(
        name="Bear Put Spread",
        category="directional",
        market_bias=[MarketBias.BEARISH],
        iv_preference=[IVEnvironment.ANY],
        complexity=2,
        capital_efficiency=0.8,
        time_decay_profile=TimeDecayProfile.NEUTRAL,
        liquidity_requirements="medium",
        risk_profile="limited",
        description="Bearish spread with defined risk/reward"
    ),
    
    # Neutral Strategies
    "Iron Condor": StrategyMetadata(
        name="Iron Condor",
        category="neutral",
        market_bias=[MarketBias.NEUTRAL],  # Should primarily be for neutral markets
        iv_preference=[IVEnvironment.HIGH, IVEnvironment.ELEVATED, IVEnvironment.NORMAL],
        complexity=3,
        capital_efficiency=0.7,
        time_decay_profile=TimeDecayProfile.POSITIVE,
        liquidity_requirements="high",
        risk_profile="limited",
        description="Range-bound strategy with positive theta"
    ),
    
    "Butterfly Spread": StrategyMetadata(
        name="Butterfly Spread",
        category="neutral",
        market_bias=[MarketBias.NEUTRAL],
        iv_preference=[IVEnvironment.ANY],
        complexity=3,
        capital_efficiency=0.9,
        time_decay_profile=TimeDecayProfile.POSITIVE,
        liquidity_requirements="high",
        risk_profile="limited",
        description="Precise neutral strategy for minimal movement"
    ),
    
    "Iron Butterfly": StrategyMetadata(
        name="Iron Butterfly",
        category="neutral",
        market_bias=[MarketBias.NEUTRAL],
        iv_preference=[IVEnvironment.HIGH, IVEnvironment.ELEVATED],
        complexity=3,
        capital_efficiency=0.8,
        time_decay_profile=TimeDecayProfile.POSITIVE,
        liquidity_requirements="high",
        risk_profile="limited",
        description="ATM neutral strategy with high theta"
    ),
    
    # Volatility Strategies
    "Long Straddle": StrategyMetadata(
        name="Long Straddle",
        category="volatility",
        market_bias=[MarketBias.NEUTRAL],  # Changed from ANY to NEUTRAL - best for uncertain direction
        iv_preference=[IVEnvironment.LOW, IVEnvironment.SUBDUED],
        complexity=2,
        capital_efficiency=0.5,
        time_decay_profile=TimeDecayProfile.NEGATIVE,
        liquidity_requirements="medium",
        risk_profile="limited",
        description="Volatility play expecting big moves"
    ),
    
    "Short Straddle": StrategyMetadata(
        name="Short Straddle",
        category="volatility",
        market_bias=[MarketBias.NEUTRAL],
        iv_preference=[IVEnvironment.HIGH, IVEnvironment.ELEVATED],
        complexity=3,
        capital_efficiency=0.3,
        time_decay_profile=TimeDecayProfile.POSITIVE,
        liquidity_requirements="high",
        risk_profile="unlimited",
        description="Premium collection expecting low volatility"
    ),
    
    "Long Strangle": StrategyMetadata(
        name="Long Strangle",
        category="volatility",
        market_bias=[MarketBias.NEUTRAL],  # Changed from ANY to NEUTRAL - best for uncertain direction
        iv_preference=[IVEnvironment.LOW, IVEnvironment.SUBDUED],
        complexity=2,
        capital_efficiency=0.7,
        time_decay_profile=TimeDecayProfile.NEGATIVE,
        liquidity_requirements="medium",
        risk_profile="limited",
        description="Cheaper volatility play than straddle"
    ),
    
    "Short Strangle": StrategyMetadata(
        name="Short Strangle",
        category="volatility",
        market_bias=[MarketBias.NEUTRAL],
        iv_preference=[IVEnvironment.HIGH, IVEnvironment.ELEVATED],
        complexity=3,
        capital_efficiency=0.4,
        time_decay_profile=TimeDecayProfile.POSITIVE,
        liquidity_requirements="high",
        risk_profile="unlimited",
        description="Wide premium collection strategy"
    ),
    
    # Income Strategies
    "Cash-Secured Put": StrategyMetadata(
        name="Cash-Secured Put",
        category="income",
        market_bias=[MarketBias.BULLISH, MarketBias.NEUTRAL],  # Removed BEARISH - not suitable for bearish markets
        iv_preference=[IVEnvironment.HIGH, IVEnvironment.ELEVATED, IVEnvironment.NORMAL],  # Better in higher IV
        complexity=1,
        capital_efficiency=0.2,
        time_decay_profile=TimeDecayProfile.POSITIVE,
        liquidity_requirements="low",
        risk_profile="limited",
        description="Income generation with potential stock acquisition"
    ),
    
    "Covered Call": StrategyMetadata(
        name="Covered Call",
        category="income",
        market_bias=[MarketBias.NEUTRAL, MarketBias.BULLISH],  # Removed BEARISH - not suitable for bearish markets
        iv_preference=[IVEnvironment.HIGH, IVEnvironment.ELEVATED, IVEnvironment.NORMAL],  # Better in higher IV
        complexity=1,
        capital_efficiency=0.1,
        time_decay_profile=TimeDecayProfile.POSITIVE,
        liquidity_requirements="low",
        risk_profile="limited",
        description="Income on existing stock positions"
    ),
    
    # Advanced Strategies
    "Calendar Spread": StrategyMetadata(
        name="Calendar Spread",
        category="advanced",
        market_bias=[MarketBias.NEUTRAL],  # Primarily for neutral markets
        iv_preference=[IVEnvironment.LOW, IVEnvironment.NORMAL],
        complexity=4,
        capital_efficiency=0.8,
        time_decay_profile=TimeDecayProfile.POSITIVE,
        liquidity_requirements="high",
        risk_profile="limited",
        description="Time decay arbitrage between expiries"
    ),
    
    "Diagonal Spread": StrategyMetadata(
        name="Diagonal Spread",
        category="advanced",
        market_bias=[MarketBias.BULLISH, MarketBias.BEARISH],
        iv_preference=[IVEnvironment.LOW, IVEnvironment.NORMAL],
        complexity=4,
        capital_efficiency=0.7,
        time_decay_profile=TimeDecayProfile.POSITIVE,
        liquidity_requirements="high",
        risk_profile="limited",
        description="Directional calendar with different strikes"
    ),
    
    "Call Ratio Spread": StrategyMetadata(
        name="Call Ratio Spread",
        category="advanced",
        market_bias=[MarketBias.BULLISH, MarketBias.NEUTRAL],
        iv_preference=[IVEnvironment.HIGH, IVEnvironment.ELEVATED],
        complexity=4,
        capital_efficiency=0.9,
        time_decay_profile=TimeDecayProfile.POSITIVE,
        liquidity_requirements="high",
        risk_profile="unlimited",
        description="Bullish strategy with upside risk"
    ),
    
    "Put Ratio Spread": StrategyMetadata(
        name="Put Ratio Spread",
        category="advanced",
        market_bias=[MarketBias.BEARISH, MarketBias.NEUTRAL],
        iv_preference=[IVEnvironment.HIGH, IVEnvironment.ELEVATED],
        complexity=4,
        capital_efficiency=0.9,
        time_decay_profile=TimeDecayProfile.POSITIVE,
        liquidity_requirements="high",
        risk_profile="unlimited",
        description="Bearish strategy with downside risk"
    ),
    
    "Jade Lizard": StrategyMetadata(
        name="Jade Lizard",
        category="advanced",
        market_bias=[MarketBias.NEUTRAL, MarketBias.BULLISH],
        iv_preference=[IVEnvironment.HIGH, IVEnvironment.ELEVATED],
        complexity=5,
        capital_efficiency=0.6,
        time_decay_profile=TimeDecayProfile.POSITIVE,
        liquidity_requirements="high",
        risk_profile="limited",
        description="No upside risk neutral/bullish strategy"
    ),
    
    "Broken Wing Butterfly": StrategyMetadata(
        name="Broken Wing Butterfly",
        category="advanced",
        market_bias=[MarketBias.NEUTRAL, MarketBias.BULLISH, MarketBias.BEARISH],
        iv_preference=[IVEnvironment.NORMAL, IVEnvironment.HIGH],
        complexity=5,
        capital_efficiency=0.8,
        time_decay_profile=TimeDecayProfile.POSITIVE,
        liquidity_requirements="high",
        risk_profile="limited",
        description="Asymmetric butterfly with directional bias"
    )
}

def get_strategy_metadata(strategy_name: str) -> Optional[StrategyMetadata]:
    """Get metadata for a specific strategy"""
    return STRATEGY_REGISTRY.get(strategy_name)

def get_compatible_strategies(market_view: str, iv_env: str, 
                            exclude_categories: List[str] = None) -> List[str]:
    """
    Get all strategies compatible with current market conditions
    
    Args:
        market_view: Current market direction (bullish/bearish/neutral)
        iv_env: Current IV environment
        exclude_categories: Categories to exclude (e.g., ['advanced'] for beginners)
    
    Returns:
        List of compatible strategy names
    """
    compatible = []
    exclude_categories = exclude_categories or []
    
    # Safe enum conversion with fallback
    try:
        market_bias = MarketBias(market_view.lower()) if market_view else MarketBias.ANY
    except ValueError:
        market_bias = MarketBias.ANY
        
    try:
        iv_environment = IVEnvironment(iv_env.lower()) if iv_env else IVEnvironment.ANY
    except ValueError:
        # Handle unknown IV environments gracefully
        iv_environment = IVEnvironment.ANY
    
    for name, metadata in STRATEGY_REGISTRY.items():
        # Check if category should be excluded
        if metadata.category in exclude_categories:
            continue
            
        # Check market bias compatibility
        market_compatible = (MarketBias.ANY in metadata.market_bias or 
                           market_bias in metadata.market_bias or
                           market_bias == MarketBias.ANY)
        
        # Check IV environment compatibility
        iv_compatible = (IVEnvironment.ANY in metadata.iv_preference or
                        iv_environment in metadata.iv_preference or
                        iv_environment == IVEnvironment.ANY)
        
        if market_compatible and iv_compatible:
            compatible.append(name)
    
    return compatible

def calculate_strategy_score(metadata: StrategyMetadata, market_analysis: Dict,
                           portfolio_context: Dict = None) -> float:
    """
    Calculate simple 3-factor score for a strategy
    
    Args:
        metadata: Strategy metadata
        market_analysis: Current market analysis
        portfolio_context: Not used anymore - keeping for compatibility
    
    Returns:
        Score between 0 and 1
    """
    score = 0.0
    
    # Factor 1: Market direction alignment (40% weight)
    market_view = market_analysis.get('direction', 'neutral').lower()
    
    # Simplify to clear market direction detection
    if 'bullish' in market_view:
        market_bias = MarketBias.BULLISH
    elif 'bearish' in market_view:
        market_bias = MarketBias.BEARISH
    else:
        market_bias = MarketBias.NEUTRAL
    
    if market_bias in metadata.market_bias:
        market_score = 1.0  # Perfect match
    elif MarketBias.ANY in metadata.market_bias:
        market_score = 0.5  # Strategy works in any market
    else:
        market_score = 0.0  # No match
    
    score += market_score * 0.4
    
    # Factor 2: IV environment fit (40% weight)
    iv_env = market_analysis.get('iv_analysis', {}).get('iv_environment', 'NORMAL')
    iv_env_lower = iv_env.lower()
    
    try:
        iv_enum = IVEnvironment(iv_env_lower)
        if iv_enum in metadata.iv_preference:
            iv_score = 1.0  # Perfect match
        elif IVEnvironment.ANY in metadata.iv_preference:
            iv_score = 0.5  # Strategy works in any IV
        else:
            iv_score = 0.0  # No match
    except ValueError:
        # Unknown IV environment - neutral score
        iv_score = 0.5
    
    score += iv_score * 0.4
    
    # Factor 3: Complexity penalty (20% weight) - prefer simpler strategies
    # Complexity ranges from 1-5, normalize to 0-1 (inverted)
    complexity_score = 1.0 - ((metadata.complexity - 1) / 4.0)
    score += complexity_score * 0.2
    
    # Bonus adjustments based on market conditions
    confidence = market_analysis.get('confidence', 0.5)
    
    # High confidence markets: boost simple directional strategies
    if confidence > 0.7 and metadata.category == 'directional' and metadata.complexity <= 2:
        score *= 1.2  # 20% boost for simple directional in trending markets
    
    # Low confidence markets: boost volatility strategies
    elif confidence < 0.4 and metadata.category == 'volatility':
        score *= 1.15  # 15% boost for volatility plays in uncertain markets
    
    # Neutral markets with high IV: boost premium selling
    elif market_bias == MarketBias.NEUTRAL and iv_score > 0.8:
        if metadata.time_decay_profile == TimeDecayProfile.POSITIVE:
            score *= 1.1  # 10% boost for theta positive strategies
    
    return min(1.0, max(0.0, score))