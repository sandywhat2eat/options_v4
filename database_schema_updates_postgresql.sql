-- =====================================================
-- Options V4 Database Schema Updates for PostgreSQL
-- =====================================================
-- This script updates existing tables and creates new ones
-- to store comprehensive options analysis output
-- Compatible with PostgreSQL/Supabase
-- =====================================================

-- =====================================================
-- PART 1: ALTER EXISTING TABLES
-- =====================================================

-- 1. Update strategies table with additional fields
ALTER TABLE strategies
ADD COLUMN IF NOT EXISTS total_score DECIMAL(10,4),
ADD COLUMN IF NOT EXISTS confidence_score DECIMAL(10,4),
ADD COLUMN IF NOT EXISTS market_direction_strength DECIMAL(10,4),
ADD COLUMN IF NOT EXISTS iv_percentile DECIMAL(10,2),
ADD COLUMN IF NOT EXISTS iv_environment VARCHAR(20),
ADD COLUMN IF NOT EXISTS spot_price DECIMAL(10,2),
ADD COLUMN IF NOT EXISTS analysis_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
ADD COLUMN IF NOT EXISTS market_sub_category VARCHAR(50),
ADD COLUMN IF NOT EXISTS component_scores JSON,
ADD COLUMN IF NOT EXISTS optimal_outcome TEXT;

-- Add comments to strategies columns
COMMENT ON COLUMN strategies.total_score IS 'Overall strategy ranking score';
COMMENT ON COLUMN strategies.confidence_score IS 'Market analysis confidence';
COMMENT ON COLUMN strategies.market_direction_strength IS 'Strength of market direction signal';
COMMENT ON COLUMN strategies.iv_percentile IS 'Current IV percentile rank';
COMMENT ON COLUMN strategies.iv_environment IS 'HIGH/LOW/NORMAL/ELEVATED';
COMMENT ON COLUMN strategies.spot_price IS 'Spot price at analysis time';
COMMENT ON COLUMN strategies.analysis_timestamp IS 'When analysis was performed';
COMMENT ON COLUMN strategies.market_sub_category IS 'Strong/Weak/Sideways';
COMMENT ON COLUMN strategies.component_scores IS 'Individual scoring components';
COMMENT ON COLUMN strategies.optimal_outcome IS 'Optimal outcome description';

-- 2. Update strategy_details table with missing Greeks
ALTER TABLE strategy_details
ADD COLUMN IF NOT EXISTS gamma DECIMAL(10,6),
ADD COLUMN IF NOT EXISTS theta DECIMAL(10,4),
ADD COLUMN IF NOT EXISTS vega DECIMAL(10,4),
ADD COLUMN IF NOT EXISTS implied_volatility DECIMAL(10,2),
ADD COLUMN IF NOT EXISTS rationale TEXT,
ADD COLUMN IF NOT EXISTS days_to_expiry INTEGER;

-- Add comments to strategy_details columns
COMMENT ON COLUMN strategy_details.gamma IS 'Option gamma';
COMMENT ON COLUMN strategy_details.theta IS 'Option theta (daily)';
COMMENT ON COLUMN strategy_details.vega IS 'Option vega';
COMMENT ON COLUMN strategy_details.implied_volatility IS 'IV percentage';
COMMENT ON COLUMN strategy_details.rationale IS 'Reason for this leg';
COMMENT ON COLUMN strategy_details.days_to_expiry IS 'Days until expiration';

-- 3. Update strategy_parameters with additional fields
ALTER TABLE strategy_parameters
ADD COLUMN IF NOT EXISTS risk_reward_ratio DECIMAL(10,2),
ADD COLUMN IF NOT EXISTS breakeven_upper DECIMAL(10,2),
ADD COLUMN IF NOT EXISTS breakeven_lower DECIMAL(10,2),
ADD COLUMN IF NOT EXISTS probability_profit DECIMAL(10,4),
ADD COLUMN IF NOT EXISTS expected_value DECIMAL(10,2),
ADD COLUMN IF NOT EXISTS days_to_expiry INTEGER;

-- Add comments to strategy_parameters columns
COMMENT ON COLUMN strategy_parameters.risk_reward_ratio IS 'Risk/Reward ratio';
COMMENT ON COLUMN strategy_parameters.breakeven_upper IS 'Upper breakeven for spreads';
COMMENT ON COLUMN strategy_parameters.breakeven_lower IS 'Lower breakeven for spreads';
COMMENT ON COLUMN strategy_parameters.probability_profit IS 'Probability of profit';
COMMENT ON COLUMN strategy_parameters.expected_value IS 'Statistical expected value';
COMMENT ON COLUMN strategy_parameters.days_to_expiry IS 'Days until strategy expiry';

-- 4. Update strategy_risk_management with detailed exit conditions
ALTER TABLE strategy_risk_management
ADD COLUMN IF NOT EXISTS profit_target_primary DECIMAL(10,2),
ADD COLUMN IF NOT EXISTS profit_target_pct DECIMAL(5,2),
ADD COLUMN IF NOT EXISTS scaling_exits JSON,
ADD COLUMN IF NOT EXISTS trailing_stop_activation DECIMAL(10,2),
ADD COLUMN IF NOT EXISTS technical_stops JSON,
ADD COLUMN IF NOT EXISTS time_stop_dte INTEGER DEFAULT 7,
ADD COLUMN IF NOT EXISTS greek_triggers JSON,
ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Add comments to strategy_risk_management columns
COMMENT ON COLUMN strategy_risk_management.profit_target_primary IS 'Primary profit target amount';
COMMENT ON COLUMN strategy_risk_management.profit_target_pct IS 'Primary profit target percentage';
COMMENT ON COLUMN strategy_risk_management.scaling_exits IS 'Scaling exit levels (25%, 50%, 75%)';
COMMENT ON COLUMN strategy_risk_management.trailing_stop_activation IS 'Profit level to activate trailing stop';
COMMENT ON COLUMN strategy_risk_management.technical_stops IS 'Technical level based stops';
COMMENT ON COLUMN strategy_risk_management.time_stop_dte IS 'Days to expiry for time stop';
COMMENT ON COLUMN strategy_risk_management.greek_triggers IS 'Greek-based exit triggers';

-- 5. Update strategy_monitoring with more fields
ALTER TABLE strategy_monitoring
ADD COLUMN IF NOT EXISTS max_pain DECIMAL(10,2),
ADD COLUMN IF NOT EXISTS spot_vs_max_pain DECIMAL(10,2),
ADD COLUMN IF NOT EXISTS poc_level DECIMAL(10,2),
ADD COLUMN IF NOT EXISTS value_area_high DECIMAL(10,2),
ADD COLUMN IF NOT EXISTS value_area_low DECIMAL(10,2),
ADD COLUMN IF NOT EXISTS expected_move_1sd DECIMAL(10,2),
ADD COLUMN IF NOT EXISTS expected_move_2sd DECIMAL(10,2);

-- Add comments to strategy_monitoring columns
COMMENT ON COLUMN strategy_monitoring.max_pain IS 'Options max pain level';
COMMENT ON COLUMN strategy_monitoring.spot_vs_max_pain IS 'Percentage difference';
COMMENT ON COLUMN strategy_monitoring.poc_level IS 'Point of Control';
COMMENT ON COLUMN strategy_monitoring.value_area_high IS 'Value Area High';
COMMENT ON COLUMN strategy_monitoring.value_area_low IS 'Value Area Low';
COMMENT ON COLUMN strategy_monitoring.expected_move_1sd IS '1 standard deviation move';
COMMENT ON COLUMN strategy_monitoring.expected_move_2sd IS '2 standard deviation move';

-- =====================================================
-- PART 2: CREATE NEW TABLES
-- =====================================================

-- 1. Market Analysis Context Table
CREATE TABLE IF NOT EXISTS strategy_market_analysis (
    id SERIAL PRIMARY KEY,
    strategy_id INTEGER REFERENCES strategies(id) ON DELETE CASCADE,
    -- Market Direction Analysis
    market_direction VARCHAR(20) NOT NULL,
    direction_confidence DECIMAL(10,4) NOT NULL,
    direction_strength DECIMAL(10,4),
    final_market_score DECIMAL(10,4),
    timeframe VARCHAR(50),
    timeframe_duration VARCHAR(50),
    
    -- Technical Analysis Components
    technical_score DECIMAL(10,4),
    trend VARCHAR(50),
    ema_alignment VARCHAR(50),
    rsi DECIMAL(10,2),
    macd_signal VARCHAR(20),
    volume_ratio DECIMAL(10,2),
    volume_trend VARCHAR(20),
    bb_width DECIMAL(10,4),
    atr DECIMAL(10,2),
    price_position VARCHAR(50),
    pattern VARCHAR(100),
    
    -- Options Flow Analysis
    options_score DECIMAL(10,4),
    volume_pcr DECIMAL(10,4),
    oi_pcr DECIMAL(10,4),
    pcr_interpretation VARCHAR(20),
    atm_call_volume DECIMAL(15,2),
    atm_put_volume DECIMAL(15,2),
    atm_bias VARCHAR(20),
    iv_skew DECIMAL(10,2),
    iv_skew_type VARCHAR(20),
    flow_intensity VARCHAR(20),
    smart_money_direction VARCHAR(20),
    unusual_activity JSON,
    
    -- Price Action Analysis
    price_action_score DECIMAL(10,4),
    oi_max_pain DECIMAL(10,2),
    oi_support DECIMAL(10,2),
    oi_resistance DECIMAL(10,2),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add comments to strategy_market_analysis table and columns
COMMENT ON TABLE strategy_market_analysis IS 'Detailed market analysis for each strategy';
COMMENT ON COLUMN strategy_market_analysis.market_direction IS 'Bullish/Bearish/Neutral';
COMMENT ON COLUMN strategy_market_analysis.direction_confidence IS 'Direction confidence score';
COMMENT ON COLUMN strategy_market_analysis.direction_strength IS 'Direction strength score';
COMMENT ON COLUMN strategy_market_analysis.final_market_score IS 'Combined market score';
COMMENT ON COLUMN strategy_market_analysis.timeframe IS 'short/mid/long term';
COMMENT ON COLUMN strategy_market_analysis.timeframe_duration IS '1-5 days, 10-30 days, etc';
COMMENT ON COLUMN strategy_market_analysis.technical_score IS 'Technical analysis score';
COMMENT ON COLUMN strategy_market_analysis.trend IS 'Uptrend/Downtrend/Sideways';
COMMENT ON COLUMN strategy_market_analysis.ema_alignment IS 'EMA alignment status';
COMMENT ON COLUMN strategy_market_analysis.rsi IS 'RSI value';
COMMENT ON COLUMN strategy_market_analysis.macd_signal IS 'Bullish/Bearish/Neutral';
COMMENT ON COLUMN strategy_market_analysis.volume_ratio IS 'Volume ratio';
COMMENT ON COLUMN strategy_market_analysis.volume_trend IS 'Increasing/Decreasing';
COMMENT ON COLUMN strategy_market_analysis.bb_width IS 'Bollinger Band width';
COMMENT ON COLUMN strategy_market_analysis.atr IS 'Average True Range';
COMMENT ON COLUMN strategy_market_analysis.price_position IS 'Near Support/Resistance';
COMMENT ON COLUMN strategy_market_analysis.pattern IS 'Detected pattern';
COMMENT ON COLUMN strategy_market_analysis.options_score IS 'Options flow score';
COMMENT ON COLUMN strategy_market_analysis.volume_pcr IS 'Put/Call volume ratio';
COMMENT ON COLUMN strategy_market_analysis.oi_pcr IS 'Put/Call OI ratio';
COMMENT ON COLUMN strategy_market_analysis.pcr_interpretation IS 'Bullish/Bearish interpretation';
COMMENT ON COLUMN strategy_market_analysis.atm_call_volume IS 'ATM call volume';
COMMENT ON COLUMN strategy_market_analysis.atm_put_volume IS 'ATM put volume';
COMMENT ON COLUMN strategy_market_analysis.atm_bias IS 'Call/Put bias';
COMMENT ON COLUMN strategy_market_analysis.iv_skew IS 'IV skew value';
COMMENT ON COLUMN strategy_market_analysis.iv_skew_type IS 'call_skew/put_skew';
COMMENT ON COLUMN strategy_market_analysis.flow_intensity IS 'HIGH/MEDIUM/LOW';
COMMENT ON COLUMN strategy_market_analysis.smart_money_direction IS 'Smart money direction';
COMMENT ON COLUMN strategy_market_analysis.unusual_activity IS 'Array of unusual strike activities';
COMMENT ON COLUMN strategy_market_analysis.price_action_score IS 'Price action score';
COMMENT ON COLUMN strategy_market_analysis.oi_max_pain IS 'Max pain strike';
COMMENT ON COLUMN strategy_market_analysis.oi_support IS 'OI-based support';
COMMENT ON COLUMN strategy_market_analysis.oi_resistance IS 'OI-based resistance';

-- Create indexes for strategy_market_analysis
CREATE INDEX IF NOT EXISTS idx_strategy_market ON strategy_market_analysis(strategy_id);
CREATE INDEX IF NOT EXISTS idx_direction ON strategy_market_analysis(market_direction);

-- 2. IV Analysis Table
CREATE TABLE IF NOT EXISTS strategy_iv_analysis (
    id SERIAL PRIMARY KEY,
    strategy_id INTEGER REFERENCES strategies(id) ON DELETE CASCADE,
    
    -- Current IV Metrics
    atm_iv DECIMAL(10,2) NOT NULL,
    iv_environment VARCHAR(20),
    atm_call_iv DECIMAL(10,2),
    atm_put_iv DECIMAL(10,2),
    call_put_iv_diff DECIMAL(10,2),
    
    -- IV Relativity
    sector_relative VARCHAR(50),
    percentile_in_sector DECIMAL(10,2),
    market_relative VARCHAR(50),
    iv_vs_market_pct DECIMAL(10,2),
    sector_normal_range_low DECIMAL(10,2),
    sector_normal_range_high DECIMAL(10,2),
    iv_interpretation TEXT,
    
    -- Mean Reversion Analysis
    reversion_potential VARCHAR(50),
    reversion_direction VARCHAR(20),
    reversion_confidence DECIMAL(10,2),
    expected_iv DECIMAL(10,2),
    reversion_time_horizon VARCHAR(50),
    
    -- Strategy Recommendations
    preferred_strategies JSON,
    avoid_strategies JSON,
    reasoning TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add comments to strategy_iv_analysis table and columns
COMMENT ON TABLE strategy_iv_analysis IS 'IV analysis and recommendations';
COMMENT ON COLUMN strategy_iv_analysis.atm_iv IS 'ATM implied volatility';
COMMENT ON COLUMN strategy_iv_analysis.iv_environment IS 'HIGH/LOW/NORMAL/ELEVATED';
COMMENT ON COLUMN strategy_iv_analysis.atm_call_iv IS 'ATM call IV';
COMMENT ON COLUMN strategy_iv_analysis.atm_put_iv IS 'ATM put IV';
COMMENT ON COLUMN strategy_iv_analysis.call_put_iv_diff IS 'Call-Put IV difference';
COMMENT ON COLUMN strategy_iv_analysis.sector_relative IS 'High/Low/Normal relative to sector';
COMMENT ON COLUMN strategy_iv_analysis.percentile_in_sector IS 'IV percentile in sector';
COMMENT ON COLUMN strategy_iv_analysis.market_relative IS 'Relative to market';
COMMENT ON COLUMN strategy_iv_analysis.iv_vs_market_pct IS 'IV vs market percentage';
COMMENT ON COLUMN strategy_iv_analysis.sector_normal_range_low IS 'Sector normal IV low';
COMMENT ON COLUMN strategy_iv_analysis.sector_normal_range_high IS 'Sector normal IV high';
COMMENT ON COLUMN strategy_iv_analysis.iv_interpretation IS 'IV analysis interpretation';
COMMENT ON COLUMN strategy_iv_analysis.reversion_potential IS 'High/Low reversion potential';
COMMENT ON COLUMN strategy_iv_analysis.reversion_direction IS 'Up/Down/Neutral';
COMMENT ON COLUMN strategy_iv_analysis.reversion_confidence IS 'Confidence in reversion';
COMMENT ON COLUMN strategy_iv_analysis.expected_iv IS 'Expected IV target';
COMMENT ON COLUMN strategy_iv_analysis.reversion_time_horizon IS 'Time horizon for reversion';
COMMENT ON COLUMN strategy_iv_analysis.preferred_strategies IS 'Array of preferred strategies';
COMMENT ON COLUMN strategy_iv_analysis.avoid_strategies IS 'Array of strategies to avoid';
COMMENT ON COLUMN strategy_iv_analysis.reasoning IS 'Reasoning for recommendations';

-- Create index for strategy_iv_analysis
CREATE INDEX IF NOT EXISTS idx_strategy_iv ON strategy_iv_analysis(strategy_id);

-- 3. Price Levels Detail Table
CREATE TABLE IF NOT EXISTS strategy_price_levels (
    id SERIAL PRIMARY KEY,
    strategy_id INTEGER REFERENCES strategies(id) ON DELETE CASCADE,
    
    -- Key Support/Resistance Levels
    level DECIMAL(10,2) NOT NULL,
    level_type VARCHAR(20) NOT NULL,
    source VARCHAR(50),
    strength VARCHAR(20),
    timeframe VARCHAR(20),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add comments to strategy_price_levels table and columns
COMMENT ON TABLE strategy_price_levels IS 'Individual price levels for each strategy';
COMMENT ON COLUMN strategy_price_levels.level IS 'Price level';
COMMENT ON COLUMN strategy_price_levels.level_type IS 'support/resistance';
COMMENT ON COLUMN strategy_price_levels.source IS 'OI/Volume/Technical/MaxPain/VAH/VAL/POC';
COMMENT ON COLUMN strategy_price_levels.strength IS 'strong/moderate/weak';
COMMENT ON COLUMN strategy_price_levels.timeframe IS 'short/mid/long term';

-- Create indexes for strategy_price_levels
CREATE INDEX IF NOT EXISTS idx_strategy_levels ON strategy_price_levels(strategy_id);
CREATE INDEX IF NOT EXISTS idx_level_type ON strategy_price_levels(level_type);

-- 4. Expected Moves Table
CREATE TABLE IF NOT EXISTS strategy_expected_moves (
    id SERIAL PRIMARY KEY,
    strategy_id INTEGER REFERENCES strategies(id) ON DELETE CASCADE,
    
    -- Expected Move Calculations
    straddle_price DECIMAL(10,2),
    one_sd_move DECIMAL(10,2),
    one_sd_pct DECIMAL(10,2),
    two_sd_move DECIMAL(10,2),
    two_sd_pct DECIMAL(10,2),
    daily_move DECIMAL(10,2),
    daily_pct DECIMAL(10,2),
    
    -- Price Targets
    upper_expected_1sd DECIMAL(10,2),
    lower_expected_1sd DECIMAL(10,2),
    upper_expected_2sd DECIMAL(10,2),
    lower_expected_2sd DECIMAL(10,2),
    
    -- Value Area
    poc DECIMAL(10,2),
    value_area_high DECIMAL(10,2),
    value_area_low DECIMAL(10,2),
    va_width_pct DECIMAL(10,2),
    spot_in_va BOOLEAN,
    
    -- Consensus Targets
    bullish_consensus_target DECIMAL(10,2),
    bearish_consensus_target DECIMAL(10,2),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add comments to strategy_expected_moves table and columns
COMMENT ON TABLE strategy_expected_moves IS 'Expected move calculations and targets';
COMMENT ON COLUMN strategy_expected_moves.straddle_price IS 'ATM straddle price';
COMMENT ON COLUMN strategy_expected_moves.one_sd_move IS '1 SD move amount';
COMMENT ON COLUMN strategy_expected_moves.one_sd_pct IS '1 SD move percentage';
COMMENT ON COLUMN strategy_expected_moves.two_sd_move IS '2 SD move amount';
COMMENT ON COLUMN strategy_expected_moves.two_sd_pct IS '2 SD move percentage';
COMMENT ON COLUMN strategy_expected_moves.daily_move IS 'Expected daily move';
COMMENT ON COLUMN strategy_expected_moves.daily_pct IS 'Expected daily percentage';
COMMENT ON COLUMN strategy_expected_moves.upper_expected_1sd IS 'Upper 1SD target';
COMMENT ON COLUMN strategy_expected_moves.lower_expected_1sd IS 'Lower 1SD target';
COMMENT ON COLUMN strategy_expected_moves.upper_expected_2sd IS 'Upper 2SD target';
COMMENT ON COLUMN strategy_expected_moves.lower_expected_2sd IS 'Lower 2SD target';
COMMENT ON COLUMN strategy_expected_moves.poc IS 'Point of Control';
COMMENT ON COLUMN strategy_expected_moves.value_area_high IS 'Value Area High';
COMMENT ON COLUMN strategy_expected_moves.value_area_low IS 'Value Area Low';
COMMENT ON COLUMN strategy_expected_moves.va_width_pct IS 'Value Area width percentage';
COMMENT ON COLUMN strategy_expected_moves.spot_in_va IS 'Is spot price in value area';
COMMENT ON COLUMN strategy_expected_moves.bullish_consensus_target IS 'Bullish consensus target';
COMMENT ON COLUMN strategy_expected_moves.bearish_consensus_target IS 'Bearish consensus target';

-- Create index for strategy_expected_moves
CREATE INDEX IF NOT EXISTS idx_strategy_moves ON strategy_expected_moves(strategy_id);

-- 5. Exit Conditions Detail Table
CREATE TABLE IF NOT EXISTS strategy_exit_levels (
    id SERIAL PRIMARY KEY,
    strategy_id INTEGER REFERENCES strategies(id) ON DELETE CASCADE,
    
    -- Exit Level Details
    exit_type VARCHAR(50) NOT NULL,
    level_name VARCHAR(100),
    trigger_value DECIMAL(10,2),
    trigger_type VARCHAR(50),
    action VARCHAR(200),
    reasoning TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add comments to strategy_exit_levels table and columns
COMMENT ON TABLE strategy_exit_levels IS 'Detailed exit conditions with multiple levels';
COMMENT ON COLUMN strategy_exit_levels.exit_type IS 'profit_target/stop_loss/time_exit/greek_trigger';
COMMENT ON COLUMN strategy_exit_levels.level_name IS 'primary/scaling_25/scaling_50/scaling_75/trailing';
COMMENT ON COLUMN strategy_exit_levels.trigger_value IS 'Trigger value (price/percentage/days)';
COMMENT ON COLUMN strategy_exit_levels.trigger_type IS 'price/percentage/dte/greek_value';
COMMENT ON COLUMN strategy_exit_levels.action IS 'Action to take';
COMMENT ON COLUMN strategy_exit_levels.reasoning IS 'Reasoning for this exit';

-- Create indexes for strategy_exit_levels
CREATE INDEX IF NOT EXISTS idx_strategy_exits ON strategy_exit_levels(strategy_id);
CREATE INDEX IF NOT EXISTS idx_exit_type ON strategy_exit_levels(exit_type);

-- 6. Strategy Component Scores Table
CREATE TABLE IF NOT EXISTS strategy_component_scores (
    id SERIAL PRIMARY KEY,
    strategy_id INTEGER REFERENCES strategies(id) ON DELETE CASCADE,
    
    -- Individual Component Scores
    probability_score DECIMAL(10,4),
    risk_reward_score DECIMAL(10,4),
    direction_score DECIMAL(10,4),
    iv_fit_score DECIMAL(10,4),
    liquidity_score DECIMAL(10,4),
    
    -- Weights Used
    probability_weight DECIMAL(10,4) DEFAULT 0.35,
    risk_reward_weight DECIMAL(10,4) DEFAULT 0.25,
    direction_weight DECIMAL(10,4) DEFAULT 0.20,
    iv_fit_weight DECIMAL(10,4) DEFAULT 0.10,
    liquidity_weight DECIMAL(10,4) DEFAULT 0.10,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add comments to strategy_component_scores table and columns
COMMENT ON TABLE strategy_component_scores IS 'Breakdown of strategy scoring components';
COMMENT ON COLUMN strategy_component_scores.probability_score IS 'Probability component score';
COMMENT ON COLUMN strategy_component_scores.risk_reward_score IS 'Risk/Reward component score';
COMMENT ON COLUMN strategy_component_scores.direction_score IS 'Direction alignment score';
COMMENT ON COLUMN strategy_component_scores.iv_fit_score IS 'IV environment fit score';
COMMENT ON COLUMN strategy_component_scores.liquidity_score IS 'Liquidity score';

-- Create index for strategy_component_scores
CREATE INDEX IF NOT EXISTS idx_strategy_scores ON strategy_component_scores(strategy_id);

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
GROUP BY s.id, sp.id, sm.id, sp.max_profit, sp.max_loss, sp.risk_reward_ratio, 
         sm.market_direction, sm.direction_confidence;

-- View for high conviction strategies
CREATE OR REPLACE VIEW v_high_conviction_strategies AS
SELECT * FROM v_strategy_overview 
WHERE conviction_level IN ('HIGH', 'VERY_HIGH')
AND probability_of_profit > 0.6
ORDER BY total_score DESC;

-- =====================================================
-- PART 5: HELPER FUNCTIONS
-- =====================================================

-- Function to map confidence score to conviction level
CREATE OR REPLACE FUNCTION map_conviction_level(confidence DECIMAL(10,4))
RETURNS VARCHAR(20)
LANGUAGE plpgsql
IMMUTABLE
AS $$
BEGIN
    IF confidence >= 0.9 THEN
        RETURN 'VERY_HIGH';
    ELSIF confidence >= 0.7 THEN
        RETURN 'HIGH';
    ELSIF confidence >= 0.5 THEN
        RETURN 'MEDIUM';
    ELSIF confidence >= 0.3 THEN
        RETURN 'LOW';
    ELSE
        RETURN 'VERY_LOW';
    END IF;
END;
$$;

-- =====================================================
-- PART 6: GRANT PERMISSIONS (if needed)
-- =====================================================

-- Grant permissions to authenticated users (adjust as needed)
-- GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO authenticated;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO authenticated;

-- =====================================================
-- END OF SCHEMA UPDATE SCRIPT
-- =====================================================