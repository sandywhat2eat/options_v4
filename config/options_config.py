# Options Trading Configuration
# Industry-First Allocation Strategy with Market Environment Integration

import os
from typing import Dict, List, Optional
from datetime import datetime

# Options Capital Management
OPTIONS_TOTAL_EXPOSURE = 30000000  # 3 crores in rupees
OPTIONS_RISK_TOLERANCE = 'moderate'  # conservative, moderate, aggressive

# Capital Allocation Percentages (% of total portfolio in options)
OPTIONS_ALLOCATION_BY_RISK = {
    'conservative': 15,  # 15% of total portfolio in options
    'moderate': 25,      # 25% of total portfolio in options  
    'aggressive': 40     # 40% of total portfolio in options
}

# Industry-First Strategy Mapping (based on allocation tables)
INDUSTRY_STRATEGY_MAPPING = {
    # High Weight Industries (>10%) - Primary focus
    'Electronic Equipment/Instruments': {
        'weight_threshold': 10.0,
        'LONG + Strong Overweight': ['Bull Call Spreads', 'Cash-Secured Puts', 'Covered Calls'],
        'LONG + Moderate Overweight': ['Bull Put Spreads', 'Iron Condors', 'Calendar Spreads'],
        'SHORT + Moderate Underweight': ['Bear Put Spreads', 'Bear Call Spreads'],
        'SHORT + Strong Underweight': ['Bear Put Spreads', 'Protective Puts']
    },
    'Wholesale Distributors': {
        'weight_threshold': 10.0,
        'LONG + Strong Overweight': ['Bull Call Spreads', 'Cash-Secured Puts'],
        'LONG + Moderate Overweight': ['Iron Condors', 'Butterflies'],
        'SHORT + Moderate Underweight': ['Bear Call Spreads', 'Credit Spreads'],
        'SHORT + Strong Underweight': ['Bear Put Spreads', 'Naked Puts']
    },
    'Pharmaceuticals': {
        'weight_threshold': 8.0,
        'LONG + Strong Overweight': ['Bull Call Spreads', 'Long Calls'],
        'LONG + Moderate Overweight': ['Bull Put Spreads', 'Covered Calls'],
        'SHORT + Moderate Underweight': ['Bear Call Spreads', 'Short Straddles'],
        'SHORT + Strong Underweight': ['Bear Put Spreads', 'Long Puts']
    },
    'Packaged Software': {
        'weight_threshold': 8.0,
        'LONG + Strong Overweight': ['Bull Call Spreads', 'Cash-Secured Puts'],
        'LONG + Moderate Overweight': ['Iron Condors', 'Calendar Spreads'],
        'SHORT + Moderate Underweight': ['Bear Call Spreads', 'Credit Spreads'],
        'SHORT + Strong Underweight': ['Bear Put Spreads', 'Protective Puts']
    },
    'Motor Vehicles': {
        'weight_threshold': 8.0,
        'LONG + Strong Overweight': ['Bull Call Spreads', 'Cash-Secured Puts'],
        'LONG + Moderate Overweight': ['Bull Put Spreads', 'Iron Condors'],
        'SHORT + Moderate Underweight': ['Bear Call Spreads', 'Short Straddles'],
        'SHORT + Strong Underweight': ['Bear Put Spreads', 'Long Puts']
    }
}

# Market Environment Framework (using existing systems)
MARKET_CONDITIONS = {
    'Bullish_Low_VIX': {
        'nifty_direction': 'bullish',
        'vix_environment': 'low',      # VIX < 15
        'pcr_range': (0.7, 1.0),       # Call bias
        'preferred_strategies': ['Bull Call Spreads', 'Cash-Secured Puts', 'Bull Put Spreads'],
        'avoid_strategies': ['Long Straddles', 'Bear Spreads', 'Long Volatility'],
        'time_preference': 'medium_term',  # 30-45 DTE
        'probability_threshold': 0.30,
        'iv_preference': 'sell',  # Sell high IV in low VIX environment
    },
    'Bullish_Normal_VIX': {
        'nifty_direction': 'bullish',
        'vix_environment': 'normal',   # VIX 15-20
        'pcr_range': (0.8, 1.1),       # Balanced
        'preferred_strategies': ['Bull Call Spreads', 'Iron Condors', 'Calendar Spreads'],
        'avoid_strategies': ['Bear Spreads', 'Short Straddles'],
        'time_preference': 'medium_term',
        'probability_threshold': 0.25,
        'iv_preference': 'neutral',
    },
    'Bullish_High_VIX': {
        'nifty_direction': 'bullish',
        'vix_environment': 'high',     # VIX > 20
        'pcr_range': (1.0, 1.3),       # Put bias despite bullish direction
        'preferred_strategies': ['Bull Put Spreads', 'Short Straddles', 'Iron Condors'],
        'avoid_strategies': ['Bull Call Spreads', 'Long Volatility'],
        'time_preference': 'short_term',  # 15-30 DTE
        'probability_threshold': 0.35,
        'iv_preference': 'sell',  # Sell high IV
    },
    'Bearish_Low_VIX': {
        'nifty_direction': 'bearish',
        'vix_environment': 'low',
        'pcr_range': (1.0, 1.3),
        'preferred_strategies': ['Bear Call Spreads', 'Long Puts', 'Bear Put Spreads'],
        'avoid_strategies': ['Bull Spreads', 'Short Volatility'],
        'time_preference': 'medium_term',
        'probability_threshold': 0.30,
        'iv_preference': 'buy',  # Buy low IV before volatility spike
    },
    'Bearish_Normal_VIX': {
        'nifty_direction': 'bearish',
        'vix_environment': 'normal',
        'pcr_range': (1.1, 1.4),
        'preferred_strategies': ['Bear Put Spreads', 'Bear Call Spreads', 'Protective Puts'],
        'avoid_strategies': ['Bull Spreads', 'Short Straddles'],
        'time_preference': 'medium_term',
        'probability_threshold': 0.25,
        'iv_preference': 'neutral',
    },
    'Bearish_High_VIX': {
        'nifty_direction': 'bearish',
        'vix_environment': 'high',
        'pcr_range': (1.2, 1.8),       # Strong put bias
        'preferred_strategies': ['Bear Put Spreads', 'Short Straddles', 'Long Puts'],
        'avoid_strategies': ['Bull Spreads', 'Long Volatility'],
        'time_preference': 'short_term',
        'probability_threshold': 0.35,
        'iv_preference': 'sell',  # Sell high IV even in bearish market
    },
    'Neutral_Low_VIX': {
        'nifty_direction': 'neutral',
        'vix_environment': 'low',
        'pcr_range': (0.9, 1.1),
        'preferred_strategies': ['Iron Condors', 'Butterflies', 'Short Strangles'],
        'avoid_strategies': ['Directional Spreads', 'Long Volatility'],
        'time_preference': 'short_term',
        'probability_threshold': 0.40,
        'iv_preference': 'sell',
    },
    'Neutral_Normal_VIX': {
        'nifty_direction': 'neutral',
        'vix_environment': 'normal',
        'pcr_range': (0.9, 1.1),
        'preferred_strategies': ['Iron Condors', 'Butterflies', 'Calendar Spreads'],
        'avoid_strategies': ['Directional Spreads'],
        'time_preference': 'medium_term',
        'probability_threshold': 0.35,
        'iv_preference': 'neutral',
    },
    'Neutral_High_VIX': {
        'nifty_direction': 'neutral',
        'vix_environment': 'high',
        'pcr_range': (1.0, 1.2),
        'preferred_strategies': ['Short Straddles', 'Iron Condors', 'Short Strangles'],
        'avoid_strategies': ['Long Volatility', 'Directional Spreads'],
        'time_preference': 'short_term',
        'probability_threshold': 0.45,
        'iv_preference': 'sell',
    }
}

# VIX Environment Thresholds
VIX_THRESHOLDS = {
    'low': 15.0,      # VIX < 15
    'normal': 20.0,   # VIX 15-20
    'high': 25.0,     # VIX > 20
    'spike': 30.0     # VIX > 30 (extreme)
}

# PCR (Put-Call Ratio) Interpretation
PCR_INTERPRETATION = {
    'extreme_bearish': 1.5,   # PCR > 1.5
    'bearish': 1.2,           # PCR 1.2-1.5
    'neutral': 1.0,           # PCR 0.8-1.2
    'bullish': 0.8,           # PCR 0.6-0.8
    'extreme_bullish': 0.6   # PCR < 0.6
}

# Position Sizing and Risk Management
POSITION_SIZING_RULES = {
    'MAX_SINGLE_STRATEGY_EXPOSURE': 0.15,    # 15% of options capital per strategy
    'MAX_INDUSTRY_OPTIONS_EXPOSURE': 0.30,   # 30% of options capital per industry
    'MAX_SINGLE_SYMBOL_EXPOSURE': 0.10,     # 10% of options capital per symbol
    'MAX_TIME_DECAY_EXPOSURE': 0.40,        # 40% in theta-positive strategies
    'MAX_VEGA_EXPOSURE': 100000,            # Absolute vega limit per portfolio
    'MAX_DELTA_EXPOSURE': 50000,            # Absolute delta limit per portfolio
}

# Strategy Scoring Weights (similar to equity ranking_score)
STRATEGY_SCORING_WEIGHTS = {
    'probability_profit': 0.30,        # Primary factor (like sharpe_ratio)
    'risk_reward_ratio': 0.25,         # Like total_return weight  
    'industry_allocation_match': 0.20, # NEW: alignment with industry allocation
    'iv_environment_fit': 0.15,        # Like momentum_score
    'liquidity_score': 0.10            # Like volatility_factor
}

# Filter Thresholds by Risk Tolerance (like Beta/Sharpe thresholds)
STRATEGY_FILTER_THRESHOLDS = {
    'conservative': {
        'min_probability': 0.45,        # Like BETA_THRESHOLDS
        'max_risk_per_trade': 0.02,     # 2% of options capital
        'min_liquidity': 0.7,
        'max_dte': 45,                  # Days to expiration
        'preferred_strategies': ['Cash-Secured Puts', 'Covered Calls', 'Bull Put Spreads']
    },
    'moderate': {
        'min_probability': 0.25,        # Current probability engine setting
        'max_risk_per_trade': 0.05,     # 5% of options capital
        'min_liquidity': 0.5,
        'max_dte': 60,
        'preferred_strategies': ['Iron Condors', 'Bull/Bear Spreads', 'Butterflies']
    },
    'aggressive': {
        'min_probability': 0.15,        # Lower threshold for aggressive trades
        'max_risk_per_trade': 0.10,     # 10% of options capital
        'min_liquidity': 0.3,
        'max_dte': 90,
        'preferred_strategies': ['Long Options', 'Ratio Spreads', 'Straddles']
    }
}

# Time-Based Strategy Preferences
TIME_PREFERENCE_MAPPING = {
    'short_term': {
        'dte_range': (7, 21),
        'theta_preference': 'positive',    # Benefit from time decay
        'gamma_tolerance': 'high',         # Accept high gamma risk
        'strategies': ['Short Straddles', 'Iron Condors', 'Credit Spreads']
    },
    'medium_term': {
        'dte_range': (21, 45),
        'theta_preference': 'neutral',     # Balanced theta exposure
        'gamma_tolerance': 'medium',
        'strategies': ['Bull/Bear Spreads', 'Butterflies', 'Calendar Spreads']
    },
    'long_term': {
        'dte_range': (45, 90),
        'theta_preference': 'negative',    # Accept theta decay for delta exposure
        'gamma_tolerance': 'low',
        'strategies': ['Long Options', 'LEAPS', 'Diagonal Spreads']
    }
}

# Database Query Configurations
SUPABASE_CONFIG = {
    'industry_allocations_table': 'industry_allocations_current',
    'sector_allocations_table': 'sector_allocations_current', 
    'stock_data_table': 'stock_data',
    'option_chain_table': 'option_chain_data',
    'nifty_options_filter': {'index': True, 'symbol': 'NIFTY 50'},
    'min_industry_weight': 5.0,  # Only consider industries with >5% allocation
}

# Integration with Existing Systems
INTEGRATION_CONFIG = {
    'use_existing_nifty_analysis': True,     # Leverage existing yfinance technical analysis
    'use_existing_vix_scripts': True,        # Use data_scripts/india_vix_historical_data.py
    'use_database_pcr': True,                # Calculate PCR from option_chain_data
    'enable_sector_override': False,         # Don't use sectoral indices (redundant)
}

# Logging and Monitoring
LOGGING_CONFIG = {
    'log_level': 'INFO',
    'log_market_conditions': True,
    'log_strategy_selection': True,
    'log_position_sizing': True,
    'save_analysis_results': True
}

# Development and Testing Flags  
DEV_CONFIG = {
    'enable_paper_trading': True,
    'max_symbols_per_industry': 3,  # Limit for testing
    'enable_database_storage': True,
    'validate_allocations': True
}

def get_current_market_condition() -> str:
    """
    Determine current market condition based on NIFTY direction, VIX level, and PCR
    This will be implemented to integrate with existing systems
    """
    # Placeholder - will be implemented with actual data sources
    return 'Bullish_Normal_VIX'

def get_industry_allocation_key(position_type: str, rating: str) -> str:
    """
    Create key for industry strategy mapping
    """
    return f"{position_type} + {rating}"

def validate_options_config() -> bool:
    """
    Validate configuration settings
    """
    # Check if all required thresholds are set
    required_keys = ['VIX_THRESHOLDS', 'PCR_INTERPRETATION', 'POSITION_SIZING_RULES']
    for key in required_keys:
        if key not in globals():
            return False
    
    # Validate percentage allocations sum properly
    total_scoring_weight = sum(STRATEGY_SCORING_WEIGHTS.values())
    if abs(total_scoring_weight - 1.0) > 0.01:
        return False
        
    return True

# Environment Variables Integration
if os.getenv('OPTIONS_RISK_TOLERANCE'):
    OPTIONS_RISK_TOLERANCE = os.getenv('OPTIONS_RISK_TOLERANCE')

if os.getenv('OPTIONS_TOTAL_EXPOSURE'):
    OPTIONS_TOTAL_EXPOSURE = int(os.getenv('OPTIONS_TOTAL_EXPOSURE'))

# Configuration validation on import
if not validate_options_config():
    raise ValueError("Options configuration validation failed")