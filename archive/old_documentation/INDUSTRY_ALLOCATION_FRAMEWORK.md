# Industry-First Options Allocation Framework

## 🎯 Overview

The Industry-First Options Allocation Framework is a revolutionary approach to options strategy selection that prioritizes trades based on industry allocation weights from your existing portfolio rather than arbitrary stock selection. This framework integrates seamlessly with the Options V4 system to provide intelligent, market-aware strategy recommendations.

## 📊 Key Features

### ✅ **Industry-First Approach**
- Queries `industry_allocations_current` and `sector_allocations_current` tables
- Prioritizes symbols based on industry weight percentages
- Maps position types (LONG/SHORT) to strategy preferences
- Allocates capital proportionally to industry weights

### ✅ **Advanced Market Environment Integration**
- **NIFTY Direction Analysis**: 
  - **Primary**: Uses existing Dhan NIFTY historical data (90 days)
  - **Fallback**: yfinance technical analysis for reliability
  - **Advanced Indicators**: RSI, MACD, Bollinger Bands, Support/Resistance
  - **Multi-timeframe Analysis**: 1W, 2W, 1M, 3M weighted analysis
- **VIX Environment Assessment**: 
  - **Primary**: Leverages existing Dhan India VIX historical data (90 days)
  - **Fallback**: yfinance VIX data for redundancy
  - **Advanced Metrics**: Percentile analysis, volatility regime detection, days since spike
  - **Trend Analysis**: 5-day and 20-day moving averages with momentum detection
- **Options Sentiment (PCR)**: Real-time Put-Call Ratio from `option_chain_data` table
- **Combined Market Conditions**: 9 market states with enhanced confidence scoring

### ✅ **Intelligent Position Sizing**
- Capital allocation based on industry weight percentages
- Risk management limits by industry, strategy, and symbol
- Premium vs margin strategy differentiation
- Configurable exposure limits and risk tolerance

### ✅ **Complete Integration**
- Seamless integration with existing Options V4 system
- Database storage using existing Supabase infrastructure
- 50-symbol portfolio analysis capability
- Real-time strategy selection and execution

## 🏗️ System Architecture

### Core Components

#### 1. **MarketConditionsAnalyzer** (`core/market_conditions_analyzer.py`)
```python
# Analyzes market conditions using multiple data sources
analyzer = MarketConditionsAnalyzer(supabase_client)
market_condition = analyzer.get_current_market_condition()
# Returns: {'condition': 'Bullish_Low_VIX', 'confidence': 0.90, ...}
```

**Features:**
- NIFTY technical analysis (RSI, MA, momentum)
- VIX environment classification (Low/Normal/High/Spike)
- PCR calculation from database options data
- Max Pain analysis from open interest
- Combined market condition determination

#### 2. **IndustryAllocationEngine** (`core/industry_allocation_engine.py`)
```python
# Manages industry-based allocation and strategy selection
engine = IndustryAllocationEngine(supabase_client)
allocation = engine.generate_portfolio_allocation(market_condition, 'moderate')
# Returns: Complete portfolio allocation with strategies and position sizing
```

**Features:**
- Industry data loading from allocation tables
- Priority industry identification by weight
- Strategy selection based on position type and rating
- Position sizing calculation with risk limits
- Portfolio validation and optimization

#### 3. **OptionsPortfolioManager** (`core/options_portfolio_manager.py`)
```python
# Main orchestrator combining market analysis and allocation
manager = OptionsPortfolioManager(supabase_client, 'moderate')
portfolio = manager.generate_options_allocation()
priority_symbols = manager.get_priority_symbols_for_analysis()
```

**Features:**
- Market environment analysis coordination
- Portfolio construction and validation
- Priority symbol generation for Options V4 analysis
- Integration with existing analysis workflows
- Results caching and portfolio tracking

## 🎛️ Configuration System

### **Options Configuration** (`config/options_config.py`)

#### Capital Management
```python
OPTIONS_TOTAL_EXPOSURE = 30000000  # ₹3 crores
OPTIONS_ALLOCATION_BY_RISK = {
    'conservative': 15,  # 15% of total portfolio
    'moderate': 25,      # 25% of total portfolio  
    'aggressive': 40     # 40% of total portfolio
}
```

#### Market Conditions Framework
```python
MARKET_CONDITIONS = {
    'Bullish_Low_VIX': {
        'preferred_strategies': ['Bull Call Spreads', 'Cash-Secured Puts'],
        'avoid_strategies': ['Long Straddles', 'Bear Spreads'],
        'time_preference': 'medium_term',  # 30-45 DTE
        'probability_threshold': 0.30
    },
    'Bearish_High_VIX': {
        'preferred_strategies': ['Bear Put Spreads', 'Short Straddles'],
        'avoid_strategies': ['Bull Spreads', 'Long Volatility'],
        'time_preference': 'short_term',   # 15-30 DTE
        'probability_threshold': 0.35
    }
    # ... 7 more market conditions
}
```

#### Industry Strategy Mapping
```python
INDUSTRY_STRATEGY_MAPPING = {
    'Electronic Equipment/Instruments': {
        'LONG + Strong Overweight': ['Bull Call Spreads', 'Cash-Secured Puts'],
        'LONG + Moderate Overweight': ['Iron Condors', 'Bull Put Spreads'],
        'SHORT + Moderate Underweight': ['Bear Put Spreads', 'Bear Call Spreads']
    }
    # ... more industries
}
```

#### Risk Management Limits
```python
POSITION_SIZING_RULES = {
    'MAX_SINGLE_STRATEGY_EXPOSURE': 0.15,    # 15% of options capital
    'MAX_INDUSTRY_OPTIONS_EXPOSURE': 0.30,   # 30% of options capital
    'MAX_SINGLE_SYMBOL_EXPOSURE': 0.10,     # 10% of options capital
    'MAX_TIME_DECAY_EXPOSURE': 0.40,        # 40% in theta-positive
    'MAX_VEGA_EXPOSURE': 100000,            # Absolute vega limit
}
```

## 📈 Usage Guide

### **1. Basic Portfolio Analysis**
```bash
# Full portfolio analysis with industry allocation
python main.py --risk moderate

# Results: 50 symbols analyzed, industry-weighted strategy selection
# Output: ₹8.1M allocated across 6 industries, 12 strategies
```

### **2. Industry Allocation Testing**
```bash
# Test the complete industry allocation framework
python test_industry_allocation_system.py

# Results: Market conditions + Industry allocation + Options V4 integration
```

### **3. Single Symbol Analysis**
```bash
# Analyze specific symbol with industry context
python main.py --symbol DIXON --risk aggressive
```

### **4. Programmatic Usage**
```python
from core.options_portfolio_manager import OptionsPortfolioManager

# Initialize with Supabase client
manager = OptionsPortfolioManager(supabase_client, risk_tolerance='moderate')

# Generate portfolio allocation
allocation = manager.generate_options_allocation(max_industries=8)

# Get priority symbols for Options V4 analysis
priority_symbols = manager.get_priority_symbols_for_analysis(limit=10)

# Analyze each priority symbol
for symbol_data in priority_symbols:
    symbol = symbol_data['symbol']
    preferences = manager.get_strategy_preferences_for_symbol(symbol)
    
    # Run Options V4 analysis with preferences
    analyzer = OptionsAnalyzer()
    results = analyzer.analyze_symbol(symbol, preferences['risk_tolerance'])
    
    # Update portfolio with results
    manager.update_portfolio_with_analysis_results(symbol, results)
```

## 📊 Performance Metrics

### **Current System Performance**
- **Portfolio Analysis**: 50 symbols in ~18 minutes
- **Success Rate**: 68% (34/50 symbols successfully analyzed)
- **Strategy Distribution**: 43 total strategies generated
- **Industry Coverage**: 6 major industries with 12 strategy types
- **Capital Efficiency**: 27.1% allocation rate with risk controls

### **Strategy Recommendation Distribution**
1. **Covered Call**: 44% (19 instances) - Primary income strategy
2. **Butterfly Spread**: 16% (7 instances) - Neutral volatility plays
3. **Cash-Secured Put**: 12% (5 instances) - Bullish income generation
4. **Bear Put Spread**: 9% (4 instances) - Bearish directional plays
5. **Iron Condor**: 7% (3 instances) - Range-bound strategies

### **Market Sentiment Analysis**
- **Bullish Bias**: 47% (20 symbols) - Reflects current market conditions
- **Neutral Stance**: 19% (8 symbols) - Range-bound opportunities
- **Bearish Outlook**: 14% (6 symbols) - Defensive positioning

## 🎛️ Configuration Management

### **Sample Size Control**
```python
# File: core/data_manager.py, Line 30
response = self.supabase.table('stock_data').select('symbol').eq('fno_stock', 'yes').limit(50).execute()

# Adjust sample size:
.limit(5)    # Small test (5 symbols)
.limit(25)   # Medium portfolio (25 symbols)
.limit(50)   # Large portfolio (50 symbols) - CURRENT
.limit(100)  # Full portfolio (100+ symbols)
```

### **Risk Tolerance Adjustment**
```python
# Conservative: Higher probability thresholds, lower position sizes
STRATEGY_FILTER_THRESHOLDS = {
    'conservative': {
        'min_probability': 0.45,
        'max_risk_per_trade': 0.02,
        'preferred_strategies': ['Cash-Secured Puts', 'Covered Calls']
    }
}

# Aggressive: Lower thresholds, higher position sizes
'aggressive': {
    'min_probability': 0.15,
    'max_risk_per_trade': 0.10,
    'preferred_strategies': ['Long Options', 'Ratio Spreads']
}
```

## 🔄 Integration Workflow

### **Complete Trading Workflow**

#### **Phase 1: Market Assessment**
```
1. Analyze NIFTY direction (existing yfinance system)
2. Assess VIX environment (existing VIX scripts)
3. Calculate PCR from option_chain_data table
4. Determine combined market condition (9 possible states)
```

#### **Phase 2: Industry Allocation**
```
1. Query industry_allocations_current table
2. Prioritize industries by weight_percentage
3. Map position_type (LONG/SHORT) to strategy preferences
4. Calculate capital allocation per industry
```

#### **Phase 3: Strategy Selection**
```
1. Combine industry bias with market conditions
2. Generate priority symbols list with preferred strategies
3. Apply position sizing based on industry allocation
4. Validate against risk management limits
```

#### **Phase 4: Options V4 Integration**
```
1. Run existing Options V4 analysis on priority symbols
2. Apply strategy preferences and position sizing
3. Store results in database using existing infrastructure
4. Generate execution instructions for trading
```

## 📁 File Structure

### **Core Framework Files**
```
core/
├── market_conditions_analyzer.py    # Market environment analysis
├── industry_allocation_engine.py    # Industry-based allocation logic
├── options_portfolio_manager.py     # Main orchestration controller
└── data_manager.py                  # Updated with 50-symbol support

config/
└── options_config.py                # Complete configuration system

test_industry_allocation_system.py   # Comprehensive testing framework
```

### **Integration Points**
```
main.py                              # Updated main entry point
database/supabase_integration.py     # Existing database storage
strategies/                          # All 22+ strategy implementations
```

## 🚀 Production Deployment

### **Environment Setup**
```bash
# Required environment variables (existing)
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_key

# Or alternative patterns
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_key
```

### **Database Requirements**
- **industry_allocations_current**: Industry weights and position types
- **sector_allocations_current**: Sector-level allocation data
- **stock_data**: Symbol-to-industry mapping (1000+ symbols)
- **option_chain_data**: NIFTY options for PCR calculation (index=true)

### **Performance Optimization**
```python
# Cache market conditions (1 hour expiry)
market_analysis = manager.analyze_market_environment(force_refresh=False)

# Limit industry count for faster processing
allocation = manager.generate_options_allocation(max_industries=6)

# Control symbol analysis depth
priority_symbols = manager.get_priority_symbols_for_analysis(limit=8)
```

## 🔧 Troubleshooting

### **Common Issues**

#### **No Industry Data Found**
```python
# Check database connection and table existence
engine.load_allocation_data()
# Ensure min_industry_weight is appropriate (default: 5.0%)
```

#### **Low Success Rate**
```python
# Adjust probability thresholds
STRATEGY_FILTER_THRESHOLDS['moderate']['min_probability'] = 0.20

# Increase symbol sample for better results
.limit(50)  # vs .limit(25)
```

#### **Market Condition Errors**
```python
# Fallback configurations are built-in
# Check VIX data availability and PCR calculation
```

### **Monitoring and Alerts**
- Monitor success rates (target: >60%)
- Track capital allocation percentages
- Validate industry weight distributions
- Check market condition accuracy

## 📈 Future Enhancements

### **Planned Features**
1. **Real-time Portfolio Rebalancing**: Dynamic allocation adjustments
2. **Sector Rotation Detection**: Automated sector weight updates
3. **Risk-Parity Integration**: Alternative allocation methodologies
4. **Performance Attribution**: Track returns by industry allocation
5. **Automated Execution**: Direct integration with trading systems

### **Scalability Improvements**
1. **Parallel Processing**: Multi-threaded symbol analysis
2. **Caching Layer**: Redis integration for market data
3. **Microservices**: Split components for independent scaling
4. **API Framework**: REST API for external integrations

## 📚 References

### **Related Documentation**
- `DATABASE_INTEGRATION_SUMMARY.md`: Complete database schema
- `DHAN_EXECUTION_GUIDE.md`: Trading execution framework
- `OPTIONS_V4_EXECUTION_INTEGRATION.md`: Strategy execution details
- `TRADING_INTEGRATION_SUMMARY.md`: End-to-end trading workflow

### **Key Files**
- `main.py`: Primary entry point with 50-symbol support
- `core/data_manager.py`: Sample size configuration (line 30)
- `config/options_config.py`: Complete configuration system
- `test_industry_allocation_system.py`: Comprehensive testing

---

**The Industry-First Options Allocation Framework provides intelligent, market-aware options strategy selection based on actual portfolio allocations, delivering professional-grade trading decisions with complete risk management integration.**