-- =====================================================
-- Options V4 Database Schema Updates
-- =====================================================
-- This script updates existing tables and creates new ones
-- to store comprehensive options analysis output
-- =====================================================

-- =====================================================
-- PART 1: ALTER EXISTING TABLES
-- =====================================================

-- 1. Update strategies table with additional fields
ALTER TABLE strategies
ADD COLUMN IF NOT EXISTS total_score DECIMAL(10,4) COMMENT 'Overall strategy ranking score',
ADD COLUMN IF NOT EXISTS confidence_score DECIMAL(10,4) COMMENT 'Market analysis confidence',
ADD COLUMN IF NOT EXISTS market_direction_strength DECIMAL(10,4) COMMENT 'Strength of market direction signal',
ADD COLUMN IF NOT EXISTS iv_percentile DECIMAL(10,2) COMMENT 'Current IV percentile rank',
ADD COLUMN IF NOT EXISTS iv_environment VARCHAR(20) COMMENT 'HIGH/LOW/NORMAL/ELEVATED',
ADD COLUMN IF NOT EXISTS spot_price DECIMAL(10,2) COMMENT 'Spot price at analysis time',
ADD COLUMN IF NOT EXISTS analysis_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'When analysis was performed',
ADD COLUMN IF NOT EXISTS market_sub_category VARCHAR(50) COMMENT 'Strong/Weak/Sideways',
ADD COLUMN IF NOT EXISTS component_scores JSON COMMENT 'Individual scoring components',
ADD COLUMN IF NOT EXISTS optimal_outcome TEXT COMMENT 'Optimal outcome description';

-- 2. Update strategy_details table with missing Greeks
ALTER TABLE strategy_details
ADD COLUMN IF NOT EXISTS gamma DECIMAL(10,6) COMMENT 'Option gamma',
ADD COLUMN IF NOT EXISTS theta DECIMAL(10,4) COMMENT 'Option theta (daily)',
ADD COLUMN IF NOT EXISTS vega DECIMAL(10,4) COMMENT 'Option vega',
ADD COLUMN IF NOT EXISTS implied_volatility DECIMAL(10,2) COMMENT 'IV percentage',
ADD COLUMN IF NOT EXISTS rationale TEXT COMMENT 'Reason for this leg',
ADD COLUMN IF NOT EXISTS days_to_expiry INTEGER COMMENT 'Days until expiration';

-- 3. Update strategy_parameters with additional fields
ALTER TABLE strategy_parameters
ADD COLUMN IF NOT EXISTS risk_reward_ratio DECIMAL(10,2) COMMENT 'Risk/Reward ratio',
ADD COLUMN IF NOT EXISTS breakeven_upper DECIMAL(10,2) COMMENT 'Upper breakeven for spreads',
ADD COLUMN IF NOT EXISTS breakeven_lower DECIMAL(10,2) COMMENT 'Lower breakeven for spreads',
ADD COLUMN IF NOT EXISTS probability_profit DECIMAL(10,4) COMMENT 'Probability of profit',
ADD COLUMN IF NOT EXISTS expected_value DECIMAL(10,2) COMMENT 'Statistical expected value',
ADD COLUMN IF NOT EXISTS days_to_expiry INTEGER COMMENT 'Days until strategy expiry';

-- 4. Update strategy_risk_management with detailed exit conditions
ALTER TABLE strategy_risk_management
ADD COLUMN IF NOT EXISTS profit_target_primary DECIMAL(10,2) COMMENT 'Primary profit target amount',
ADD COLUMN IF NOT EXISTS profit_target_pct DECIMAL(5,2) COMMENT 'Primary profit target percentage',
ADD COLUMN IF NOT EXISTS scaling_exits JSON COMMENT 'Scaling exit levels (25%, 50%, 75%)',
ADD COLUMN IF NOT EXISTS trailing_stop_activation DECIMAL(10,2) COMMENT 'Profit level to activate trailing stop',
ADD COLUMN IF NOT EXISTS technical_stops JSON COMMENT 'Technical level based stops',
ADD COLUMN IF NOT EXISTS time_stop_dte INTEGER DEFAULT 7 COMMENT 'Days to expiry for time stop',
ADD COLUMN IF NOT EXISTS greek_triggers JSON COMMENT 'Greek-based exit triggers',
ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- 5. Update strategy_monitoring with more fields
ALTER TABLE strategy_monitoring
ADD COLUMN IF NOT EXISTS max_pain DECIMAL(10,2) COMMENT 'Options max pain level',
ADD COLUMN IF NOT EXISTS spot_vs_max_pain DECIMAL(10,2) COMMENT 'Percentage difference',
ADD COLUMN IF NOT EXISTS poc_level DECIMAL(10,2) COMMENT 'Point of Control',
ADD COLUMN IF NOT EXISTS value_area_high DECIMAL(10,2) COMMENT 'Value Area High',
ADD COLUMN IF NOT EXISTS value_area_low DECIMAL(10,2) COMMENT 'Value Area Low',
ADD COLUMN IF NOT EXISTS expected_move_1sd DECIMAL(10,2) COMMENT '1 standard deviation move',
ADD COLUMN IF NOT EXISTS expected_move_2sd DECIMAL(10,2) COMMENT '2 standard deviation move';

-- =====================================================
-- PART 2: CREATE NEW TABLES
-- =====================================================

-- 1. Market Analysis Context Table
CREATE TABLE IF NOT EXISTS strategy_market_analysis (
    id SERIAL PRIMARY KEY,
    strategy_id INTEGER REFERENCES strategies(id) ON DELETE CASCADE,
    -- Market Direction Analysis
    market_direction VARCHAR(20) NOT NULL COMMENT 'Bullish/Bearish/Neutral',
    direction_confidence DECIMAL(10,4) NOT NULL COMMENT 'Direction confidence score',
    direction_strength DECIMAL(10,4) COMMENT 'Direction strength score',
    final_market_score DECIMAL(10,4) COMMENT 'Combined market score',
    timeframe VARCHAR(50) COMMENT 'short/mid/long term',
    timeframe_duration VARCHAR(50) COMMENT '1-5 days, 10-30 days, etc',
    
    -- Technical Analysis Components
    technical_score DECIMAL(10,4) COMMENT 'Technical analysis score',
    trend VARCHAR(50) COMMENT 'Uptrend/Downtrend/Sideways',
    ema_alignment VARCHAR(50) COMMENT 'EMA alignment status',
    rsi DECIMAL(10,2) COMMENT 'RSI value',
    macd_signal VARCHAR(20) COMMENT 'Bullish/Bearish/Neutral',
    volume_ratio DECIMAL(10,2) COMMENT 'Volume ratio',
    volume_trend VARCHAR(20) COMMENT 'Increasing/Decreasing',
    bb_width DECIMAL(10,4) COMMENT 'Bollinger Band width',
    atr DECIMAL(10,2) COMMENT 'Average True Range',
    price_position VARCHAR(50) COMMENT 'Near Support/Resistance',
    pattern VARCHAR(100) COMMENT 'Detected pattern',
    
    -- Options Flow Analysis
    options_score DECIMAL(10,4) COMMENT 'Options flow score',
    volume_pcr DECIMAL(10,4) COMMENT 'Put/Call volume ratio',
    oi_pcr DECIMAL(10,4) COMMENT 'Put/Call OI ratio',
    pcr_interpretation VARCHAR(20) COMMENT 'Bullish/Bearish interpretation',
    atm_call_volume DECIMAL(15,2) COMMENT 'ATM call volume',
    atm_put_volume DECIMAL(15,2) COMMENT 'ATM put volume',
    atm_bias VARCHAR(20) COMMENT 'Call/Put bias',
    iv_skew DECIMAL(10,2) COMMENT 'IV skew value',
    iv_skew_type VARCHAR(20) COMMENT 'call_skew/put_skew',
    flow_intensity VARCHAR(20) COMMENT 'HIGH/MEDIUM/LOW',
    smart_money_direction VARCHAR(20) COMMENT 'Smart money direction',
    unusual_activity JSON COMMENT 'Array of unusual strike activities',
    
    -- Price Action Analysis
    price_action_score DECIMAL(10,4) COMMENT 'Price action score',
    oi_max_pain DECIMAL(10,2) COMMENT 'Max pain strike',
    oi_support DECIMAL(10,2) COMMENT 'OI-based support',
    oi_resistance DECIMAL(10,2) COMMENT 'OI-based resistance',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_strategy_market (strategy_id),
    INDEX idx_direction (market_direction)
) COMMENT='Detailed market analysis for each strategy';

-- 2. IV Analysis Table
CREATE TABLE IF NOT EXISTS strategy_iv_analysis (
    id SERIAL PRIMARY KEY,
    strategy_id INTEGER REFERENCES strategies(id) ON DELETE CASCADE,
    
    -- Current IV Metrics
    atm_iv DECIMAL(10,2) NOT NULL COMMENT 'ATM implied volatility',
    iv_environment VARCHAR(20) COMMENT 'HIGH/LOW/NORMAL/ELEVATED',
    atm_call_iv DECIMAL(10,2) COMMENT 'ATM call IV',
    atm_put_iv DECIMAL(10,2) COMMENT 'ATM put IV',
    call_put_iv_diff DECIMAL(10,2) COMMENT 'Call-Put IV difference',
    
    -- IV Relativity
    sector_relative VARCHAR(50) COMMENT 'High/Low/Normal relative to sector',
    percentile_in_sector DECIMAL(10,2) COMMENT 'IV percentile in sector',
    market_relative VARCHAR(50) COMMENT 'Relative to market',
    iv_vs_market_pct DECIMAL(10,2) COMMENT 'IV vs market percentage',
    sector_normal_range_low DECIMAL(10,2) COMMENT 'Sector normal IV low',
    sector_normal_range_high DECIMAL(10,2) COMMENT 'Sector normal IV high',
    iv_interpretation TEXT COMMENT 'IV analysis interpretation',
    
    -- Mean Reversion Analysis
    reversion_potential VARCHAR(50) COMMENT 'High/Low reversion potential',
    reversion_direction VARCHAR(20) COMMENT 'Up/Down/Neutral',
    reversion_confidence DECIMAL(10,2) COMMENT 'Confidence in reversion',
    expected_iv DECIMAL(10,2) COMMENT 'Expected IV target',
    reversion_time_horizon VARCHAR(50) COMMENT 'Time horizon for reversion',
    
    -- Strategy Recommendations
    preferred_strategies JSON COMMENT 'Array of preferred strategies',
    avoid_strategies JSON COMMENT 'Array of strategies to avoid',
    reasoning TEXT COMMENT 'Reasoning for recommendations',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_strategy_iv (strategy_id)
) COMMENT='IV analysis and recommendations';

-- 3. Price Levels Detail Table
CREATE TABLE IF NOT EXISTS strategy_price_levels (
    id SERIAL PRIMARY KEY,
    strategy_id INTEGER REFERENCES strategies(id) ON DELETE CASCADE,
    
    -- Key Support/Resistance Levels
    level DECIMAL(10,2) NOT NULL COMMENT 'Price level',
    level_type VARCHAR(20) NOT NULL COMMENT 'support/resistance',
    source VARCHAR(50) COMMENT 'OI/Volume/Technical/MaxPain/VAH/VAL/POC',
    strength VARCHAR(20) COMMENT 'strong/moderate/weak',
    timeframe VARCHAR(20) COMMENT 'short/mid/long term',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_strategy_levels (strategy_id),
    INDEX idx_level_type (level_type)
) COMMENT='Individual price levels for each strategy';

-- 4. Expected Moves Table
CREATE TABLE IF NOT EXISTS strategy_expected_moves (
    id SERIAL PRIMARY KEY,
    strategy_id INTEGER REFERENCES strategies(id) ON DELETE CASCADE,
    
    -- Expected Move Calculations
    straddle_price DECIMAL(10,2) COMMENT 'ATM straddle price',
    one_sd_move DECIMAL(10,2) COMMENT '1 SD move amount',
    one_sd_pct DECIMAL(10,2) COMMENT '1 SD move percentage',
    two_sd_move DECIMAL(10,2) COMMENT '2 SD move amount',
    two_sd_pct DECIMAL(10,2) COMMENT '2 SD move percentage',
    daily_move DECIMAL(10,2) COMMENT 'Expected daily move',
    daily_pct DECIMAL(10,2) COMMENT 'Expected daily percentage',
    
    -- Price Targets
    upper_expected_1sd DECIMAL(10,2) COMMENT 'Upper 1SD target',
    lower_expected_1sd DECIMAL(10,2) COMMENT 'Lower 1SD target',
    upper_expected_2sd DECIMAL(10,2) COMMENT 'Upper 2SD target',
    lower_expected_2sd DECIMAL(10,2) COMMENT 'Lower 2SD target',
    
    -- Value Area
    poc DECIMAL(10,2) COMMENT 'Point of Control',
    value_area_high DECIMAL(10,2) COMMENT 'Value Area High',
    value_area_low DECIMAL(10,2) COMMENT 'Value Area Low',
    va_width_pct DECIMAL(10,2) COMMENT 'Value Area width percentage',
    spot_in_va BOOLEAN COMMENT 'Is spot price in value area',
    
    -- Consensus Targets
    bullish_consensus_target DECIMAL(10,2) COMMENT 'Bullish consensus target',
    bearish_consensus_target DECIMAL(10,2) COMMENT 'Bearish consensus target',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_strategy_moves (strategy_id)
) COMMENT='Expected move calculations and targets';

-- 5. Exit Conditions Detail Table
CREATE TABLE IF NOT EXISTS strategy_exit_levels (
    id SERIAL PRIMARY KEY,
    strategy_id INTEGER REFERENCES strategies(id) ON DELETE CASCADE,
    
    -- Exit Level Details
    exit_type VARCHAR(50) NOT NULL COMMENT 'profit_target/stop_loss/time_exit/greek_trigger',
    level_name VARCHAR(100) COMMENT 'primary/scaling_25/scaling_50/scaling_75/trailing',
    trigger_value DECIMAL(10,2) COMMENT 'Trigger value (price/percentage/days)',
    trigger_type VARCHAR(50) COMMENT 'price/percentage/dte/greek_value',
    action VARCHAR(200) COMMENT 'Action to take',
    reasoning TEXT COMMENT 'Reasoning for this exit',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_strategy_exits (strategy_id),
    INDEX idx_exit_type (exit_type)
) COMMENT='Detailed exit conditions with multiple levels';

-- 6. Strategy Component Scores Table
CREATE TABLE IF NOT EXISTS strategy_component_scores (
    id SERIAL PRIMARY KEY,
    strategy_id INTEGER REFERENCES strategies(id) ON DELETE CASCADE,
    
    -- Individual Component Scores
    probability_score DECIMAL(10,4) COMMENT 'Probability component score',
    risk_reward_score DECIMAL(10,4) COMMENT 'Risk/Reward component score',
    direction_score DECIMAL(10,4) COMMENT 'Direction alignment score',
    iv_fit_score DECIMAL(10,4) COMMENT 'IV environment fit score',
    liquidity_score DECIMAL(10,4) COMMENT 'Liquidity score',
    
    -- Weights Used
    probability_weight DECIMAL(10,4) DEFAULT 0.35,
    risk_reward_weight DECIMAL(10,4) DEFAULT 0.25,
    direction_weight DECIMAL(10,4) DEFAULT 0.20,
    iv_fit_weight DECIMAL(10,4) DEFAULT 0.10,
    liquidity_weight DECIMAL(10,4) DEFAULT 0.10,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_strategy_scores (strategy_id)
) COMMENT='Breakdown of strategy scoring components';

-- =====================================================
-- PART 3: CREATE INDEXES FOR PERFORMANCE
-- =====================================================

-- Add indexes to existing tables if not exists
CREATE INDEX IF NOT EXISTS idx_strategies_symbol ON strategies(stock_name);
CREATE INDEX IF NOT EXISTS idx_strategies_conviction ON strategies(conviction_level);
CREATE INDEX IF NOT EXISTS idx_strategies_timestamp ON strategies(generated_on);
CREATE INDEX IF NOT EXISTS idx_strategy_details_type ON strategy_details(setup_type);
CREATE INDEX IF NOT EXISTS idx_strategy_details_strike ON strategy_details(strike_price);

-- =====================================================
-- PART 4: CREATE VIEWS FOR COMMON QUERIES
-- =====================================================

-- View for complete strategy overview
CREATE OR REPLACE VIEW v_strategy_overview AS
SELECT 
    s.id,
    s.stock_name,
    s.strategy_name,
    s.conviction_level,
    s.probability_of_profit,
    s.net_premium,
    s.total_score,
    sp.max_profit,
    sp.max_loss,
    sp.risk_reward_ratio,
    sm.market_direction,
    sm.direction_confidence,
    COUNT(sd.id) as num_legs
FROM strategies s
LEFT JOIN strategy_parameters sp ON s.id = sp.strategy_id
LEFT JOIN strategy_market_analysis sm ON s.id = sm.strategy_id
LEFT JOIN strategy_details sd ON s.id = sd.strategy_id
GROUP BY s.id, sp.id, sm.id;

-- View for high conviction strategies
CREATE OR REPLACE VIEW v_high_conviction_strategies AS
SELECT * FROM v_strategy_overview 
WHERE conviction_level IN ('HIGH', 'VERY_HIGH')
AND probability_of_profit > 0.6
ORDER BY total_score DESC;

-- =====================================================
-- PART 5: MIGRATION HELPERS
-- =====================================================

-- Function to map confidence score to conviction level
DELIMITER //
CREATE FUNCTION IF NOT EXISTS map_conviction_level(confidence DECIMAL(10,4))
RETURNS VARCHAR(20)
DETERMINISTIC
BEGIN
    IF confidence >= 0.9 THEN
        RETURN 'VERY_HIGH';
    ELSEIF confidence >= 0.7 THEN
        RETURN 'HIGH';
    ELSEIF confidence >= 0.5 THEN
        RETURN 'MEDIUM';
    ELSEIF confidence >= 0.3 THEN
        RETURN 'LOW';
    ELSE
        RETURN 'VERY_LOW';
    END IF;
END//
DELIMITER ;

-- =====================================================
-- END OF SCHEMA UPDATE SCRIPT
-- =====================================================