-- =====================================================
-- Options Trading Views for Derivatives Experts
-- =====================================================
-- Professional trading views for strategy analysis and execution
-- Designed for options traders, portfolio managers, and execution teams
-- =====================================================

-- =====================================================
-- 1. TRADE EXECUTION VIEW
-- =====================================================
-- Complete strategy details ready for trade execution

CREATE OR REPLACE VIEW v_trade_execution AS
SELECT 
    -- Strategy Identification
    s.id as strategy_id,
    s.stock_name as symbol,
    s.strategy_name,
    s.strategy_type,
    s.conviction_level,
    s.total_score,
    s.probability_of_profit,
    s.spot_price,
    s.generated_on as analysis_time,
    
    -- Market Context
    sma.market_direction,
    sma.direction_confidence,
    sma.timeframe_duration as time_horizon,
    sma.iv_skew,
    sma.flow_intensity,
    sia.iv_environment,
    sia.atm_iv,
    
    -- Risk/Reward Metrics
    sp.max_profit,
    sp.max_loss,
    sp.risk_reward_ratio,
    sp.probability_profit,
    
    -- Entry Details
    sd.setup_type as leg_action,
    sd.option_type,
    sd.strike_price,
    sd.entry_price as premium,
    sd.quantity,
    sd.delta,
    sd.gamma,
    sd.theta,
    sd.vega,
    sd.implied_volatility as iv,
    
    -- Exit Conditions
    srm.profit_target_primary,
    srm.profit_target_pct,
    srm.strategy_level_stop as stop_loss_pct,
    srm.time_stop_dte,
    
    -- Net Position Greeks
    sge.net_delta,
    sge.net_gamma,
    sge.net_theta,
    sge.net_vega,
    
    -- Key Levels
    CASE 
        WHEN sma.market_direction = 'Bullish' THEN 
            (SELECT level FROM strategy_price_levels spl WHERE spl.strategy_id = s.id AND level_type = 'resistance' ORDER BY level LIMIT 1)
        ELSE 
            (SELECT level FROM strategy_price_levels spl WHERE spl.strategy_id = s.id AND level_type = 'support' ORDER BY level DESC LIMIT 1)
    END as key_level,
    
    -- Expected Moves
    sem.one_sd_move,
    sem.upper_expected_1sd,
    sem.lower_expected_1sd,
    
    -- Trade Urgency (based on time and scores)
    CASE 
        WHEN s.total_score > 0.7 AND s.conviction_level IN ('HIGH', 'VERY_HIGH') THEN 'IMMEDIATE'
        WHEN s.total_score > 0.6 AND s.conviction_level = 'HIGH' THEN 'HIGH'
        WHEN s.total_score > 0.5 THEN 'MEDIUM'
        ELSE 'LOW'
    END as trade_priority

FROM strategies s
LEFT JOIN strategy_details sd ON s.id = sd.strategy_id
LEFT JOIN strategy_parameters sp ON s.id = sp.strategy_id
LEFT JOIN strategy_market_analysis sma ON s.id = sma.strategy_id
LEFT JOIN strategy_iv_analysis sia ON s.id = sia.strategy_id
LEFT JOIN strategy_risk_management srm ON s.id = srm.strategy_id
LEFT JOIN strategy_greek_exposures sge ON s.id = sge.strategy_id
LEFT JOIN strategy_expected_moves sem ON s.id = sem.strategy_id
ORDER BY s.generated_on DESC, s.total_score DESC, sd.id;

COMMENT ON VIEW v_trade_execution IS 'Complete strategy view for trade execution with all legs, Greeks, and risk parameters';

-- =====================================================
-- 2. PORTFOLIO DASHBOARD VIEW
-- =====================================================
-- High-level portfolio view for decision making

CREATE OR REPLACE VIEW v_portfolio_dashboard AS
SELECT 
    s.stock_name as symbol,
    s.strategy_name,
    s.conviction_level,
    s.total_score,
    s.probability_of_profit,
    s.spot_price,
    
    -- Market Signals
    sma.market_direction,
    sma.direction_confidence,
    sma.timeframe_duration,
    sia.iv_environment,
    sia.atm_iv,
    
    -- Risk Metrics
    sp.max_profit,
    sp.max_loss,
    sp.risk_reward_ratio,
    ROUND(sp.max_profit / NULLIF(ABS(sp.max_loss), 0), 2) as profit_loss_ratio,
    
    -- Position Summary
    COUNT(sd.id) as num_legs,
    STRING_AGG(DISTINCT sd.option_type, ', ') as option_types,
    STRING_AGG(DISTINCT sd.setup_type, ', ') as actions,
    
    -- Greeks Summary
    sge.net_delta,
    sge.net_theta,
    sge.net_vega,
    
    -- Key Levels
    (SELECT COUNT(*) FROM strategy_price_levels spl WHERE spl.strategy_id = s.id AND level_type = 'support') as support_levels,
    (SELECT COUNT(*) FROM strategy_price_levels spl WHERE spl.strategy_id = s.id AND level_type = 'resistance') as resistance_levels,
    
    -- Trade Recommendation
    CASE 
        WHEN s.total_score > 0.7 AND s.conviction_level IN ('HIGH', 'VERY_HIGH') THEN 'STRONG BUY'
        WHEN s.total_score > 0.6 AND s.conviction_level = 'HIGH' THEN 'BUY'
        WHEN s.total_score > 0.5 THEN 'CONSIDER'
        ELSE 'AVOID'
    END as recommendation,
    
    s.generated_on as analysis_time

FROM strategies s
LEFT JOIN strategy_details sd ON s.id = sd.strategy_id
LEFT JOIN strategy_parameters sp ON s.id = sp.strategy_id
LEFT JOIN strategy_market_analysis sma ON s.id = sma.strategy_id
LEFT JOIN strategy_iv_analysis sia ON s.id = sia.strategy_id
LEFT JOIN strategy_greek_exposures sge ON s.id = sge.strategy_id
WHERE s.generated_on >= NOW() - INTERVAL '7 days'  -- Last 7 days
GROUP BY s.id, s.stock_name, s.strategy_name, s.conviction_level, s.total_score, 
         s.probability_of_profit, s.spot_price, sma.market_direction, sma.direction_confidence,
         sma.timeframe_duration, sia.iv_environment, sia.atm_iv, sp.max_profit, sp.max_loss,
         sp.risk_reward_ratio, sge.net_delta, sge.net_theta, sge.net_vega, s.generated_on
ORDER BY s.total_score DESC, s.probability_of_profit DESC;

COMMENT ON VIEW v_portfolio_dashboard IS 'High-level portfolio view for quick decision making and opportunity identification';

-- =====================================================
-- 3. RISK MANAGEMENT VIEW
-- =====================================================
-- Detailed risk analysis for position sizing and management

CREATE OR REPLACE VIEW v_risk_management AS
SELECT 
    s.id as strategy_id,
    s.stock_name as symbol,
    s.strategy_name,
    s.spot_price,
    s.conviction_level,
    s.total_score,
    
    -- Position Risk
    sp.max_profit,
    sp.max_loss,
    sp.risk_reward_ratio,
    sp.probability_profit,
    
    -- Greeks Risk
    sge.net_delta as position_delta,
    sge.net_gamma as gamma_risk,
    sge.net_theta as daily_decay,
    sge.net_vega as vol_risk,
    
    -- Volatility Analysis
    sia.atm_iv,
    sia.iv_environment,
    sia.percentile_in_sector as iv_percentile,
    sia.reversion_potential,
    
    -- Exit Management
    srm.profit_target_primary,
    srm.profit_target_pct,
    srm.strategy_level_stop,
    srm.time_stop_dte,
    srm.trailing_stop_activation,
    
    -- Market Risk Factors
    sma.volume_ratio,
    sma.iv_skew,
    sma.flow_intensity,
    sma.smart_money_direction,
    
    -- Key Price Levels
    (SELECT level FROM strategy_price_levels spl WHERE spl.strategy_id = s.id AND level_type = 'support' ORDER BY ABS(level - s.spot_price) LIMIT 1) as nearest_support,
    (SELECT level FROM strategy_price_levels spl WHERE spl.strategy_id = s.id AND level_type = 'resistance' ORDER BY ABS(level - s.spot_price) LIMIT 1) as nearest_resistance,
    
    -- Expected Moves
    sem.one_sd_move,
    sem.daily_move,
    sem.upper_expected_1sd,
    sem.lower_expected_1sd,
    
    -- Position Sizing Recommendation
    CASE 
        WHEN s.conviction_level = 'VERY_HIGH' AND sp.risk_reward_ratio > 2 THEN 'LARGE (3-5%)'
        WHEN s.conviction_level = 'HIGH' AND sp.risk_reward_ratio > 1.5 THEN 'MEDIUM (2-3%)'
        WHEN s.conviction_level = 'MEDIUM' AND sp.risk_reward_ratio > 1 THEN 'SMALL (1-2%)'
        ELSE 'MINIMAL (<1%)'
    END as position_size_rec,
    
    -- Risk Alert Level
    CASE 
        WHEN ABS(sge.net_delta) > 0.5 AND ABS(sge.net_gamma) > 0.01 THEN 'HIGH'
        WHEN ABS(sge.net_delta) > 0.3 OR ABS(sge.net_vega) > 20 THEN 'MEDIUM'
        ELSE 'LOW'
    END as risk_level,
    
    s.generated_on as analysis_time

FROM strategies s
LEFT JOIN strategy_parameters sp ON s.id = sp.strategy_id
LEFT JOIN strategy_greek_exposures sge ON s.id = sge.strategy_id
LEFT JOIN strategy_iv_analysis sia ON s.id = sia.strategy_id
LEFT JOIN strategy_risk_management srm ON s.id = srm.strategy_id
LEFT JOIN strategy_market_analysis sma ON s.id = sma.strategy_id
LEFT JOIN strategy_expected_moves sem ON s.id = sem.strategy_id
ORDER BY s.generated_on DESC, s.total_score DESC;

COMMENT ON VIEW v_risk_management IS 'Comprehensive risk analysis for position sizing and risk management decisions';

-- =====================================================
-- 4. MARKET OPPORTUNITIES VIEW
-- =====================================================
-- Market-focused view for identifying trading opportunities

CREATE OR REPLACE VIEW v_market_opportunities AS
SELECT 
    s.stock_name as symbol,
    s.spot_price,
    s.strategy_name,
    s.total_score,
    s.conviction_level,
    
    -- Market Direction Analysis
    sma.market_direction,
    sma.direction_confidence,
    sma.final_market_score,
    sma.timeframe_duration,
    
    -- Technical Signals
    sma.trend,
    sma.rsi,
    sma.macd_signal,
    sma.volume_trend,
    sma.price_position,
    
    -- Options Flow
    sma.volume_pcr as put_call_volume_ratio,
    sma.oi_pcr as put_call_oi_ratio,
    sma.pcr_interpretation,
    sma.flow_intensity,
    sma.smart_money_direction,
    
    -- Volatility Opportunity
    sia.iv_environment,
    sia.atm_iv,
    sia.sector_relative as iv_vs_sector,
    sia.reversion_potential,
    
    -- Price Levels Context
    sma.oi_max_pain as max_pain,
    (s.spot_price - sma.oi_max_pain) / s.spot_price * 100 as spot_vs_max_pain_pct,
    
    -- Expected Moves
    sem.one_sd_pct as expected_move_pct,
    sem.daily_pct as daily_move_pct,
    
    -- Strategy Fit Score
    CASE 
        WHEN sma.market_direction = 'Bullish' AND s.strategy_type = 'Directional' AND s.strategy_name LIKE '%Bull%' THEN 'PERFECT'
        WHEN sma.market_direction = 'Bearish' AND s.strategy_type = 'Directional' AND s.strategy_name LIKE '%Bear%' THEN 'PERFECT'
        WHEN sma.market_direction = 'Neutral' AND s.strategy_type IN ('Neutral', 'Income') THEN 'EXCELLENT'
        WHEN sia.iv_environment = 'HIGH' AND s.strategy_type = 'Income' THEN 'EXCELLENT'
        WHEN sia.iv_environment = 'LOW' AND s.strategy_type = 'Volatility' THEN 'GOOD'
        ELSE 'MODERATE'
    END as strategy_market_fit,
    
    -- Opportunity Score (0-100)
    ROUND(
        (s.total_score * 40) + 
        (sma.direction_confidence * 30) + 
        (CASE 
            WHEN sia.iv_environment IN ('HIGH', 'LOW') THEN 20 
            ELSE 10 
        END) + 
        (CASE 
            WHEN s.conviction_level IN ('HIGH', 'VERY_HIGH') THEN 10 
            ELSE 5 
        END)
    ) as opportunity_score,
    
    s.generated_on as analysis_time

FROM strategies s
LEFT JOIN strategy_market_analysis sma ON s.id = sma.strategy_id
LEFT JOIN strategy_iv_analysis sia ON s.id = sia.strategy_id
LEFT JOIN strategy_expected_moves sem ON s.id = sem.strategy_id
WHERE s.generated_on >= NOW() - INTERVAL '3 days'  -- Recent opportunities
ORDER BY opportunity_score DESC, s.total_score DESC;

COMMENT ON VIEW v_market_opportunities IS 'Market-focused view for identifying high-probability trading opportunities';

-- =====================================================
-- 5. STRATEGY COMPARISON VIEW
-- =====================================================
-- Compare multiple strategies for the same symbol

CREATE OR REPLACE VIEW v_strategy_comparison AS
SELECT 
    s.stock_name as symbol,
    s.spot_price,
    s.strategy_name,
    s.strategy_type,
    s.total_score,
    s.conviction_level,
    s.probability_of_profit,
    
    -- Risk/Reward Comparison
    sp.max_profit,
    sp.max_loss,
    sp.risk_reward_ratio,
    
    -- Strategy Ranking within Symbol
    ROW_NUMBER() OVER (PARTITION BY s.stock_name ORDER BY s.total_score DESC) as rank_by_score,
    ROW_NUMBER() OVER (PARTITION BY s.stock_name ORDER BY sp.risk_reward_ratio DESC) as rank_by_rr,
    ROW_NUMBER() OVER (PARTITION BY s.stock_name ORDER BY s.probability_of_profit DESC) as rank_by_prob,
    
    -- Greeks Profile
    sge.net_delta,
    sge.net_theta,
    sge.net_vega,
    
    -- Market Context
    sma.market_direction,
    sma.direction_confidence,
    sia.iv_environment,
    
    -- Strategy Characteristics
    COUNT(sd.id) as num_legs,
    STRING_AGG(CONCAT(sd.setup_type, ' ', sd.option_type, ' ', sd.strike_price), ' | ') as leg_structure,
    
    -- Relative Performance Score
    ROUND(
        (s.total_score / MAX(s.total_score) OVER (PARTITION BY s.stock_name)) * 100
    ) as relative_score_pct,
    
    s.generated_on as analysis_time

FROM strategies s
LEFT JOIN strategy_details sd ON s.id = sd.strategy_id
LEFT JOIN strategy_parameters sp ON s.id = sp.strategy_id
LEFT JOIN strategy_greek_exposures sge ON s.id = sge.strategy_id
LEFT JOIN strategy_market_analysis sma ON s.id = sma.strategy_id
LEFT JOIN strategy_iv_analysis sia ON s.id = sia.strategy_id
WHERE s.generated_on >= NOW() - INTERVAL '24 hours'  -- Today's analysis
GROUP BY s.id, s.stock_name, s.spot_price, s.strategy_name, s.strategy_type, 
         s.total_score, s.conviction_level, s.probability_of_profit,
         sp.max_profit, sp.max_loss, sp.risk_reward_ratio,
         sge.net_delta, sge.net_theta, sge.net_vega,
         sma.market_direction, sma.direction_confidence, sia.iv_environment,
         s.generated_on
ORDER BY s.stock_name, s.total_score DESC;

COMMENT ON VIEW v_strategy_comparison IS 'Compare multiple strategies for the same symbol to select the best option';

-- =====================================================
-- 6. EXECUTION CHECKLIST VIEW
-- =====================================================
-- Pre-trade execution checklist with all required details

CREATE OR REPLACE VIEW v_execution_checklist AS
SELECT 
    s.id as strategy_id,
    s.stock_name as symbol,
    s.strategy_name,
    s.spot_price as current_spot,
    
    -- Leg Details for Order Entry
    sd.setup_type as action,
    sd.option_type,
    sd.strike_price,
    sd.entry_price as target_premium,
    sd.entry_min_price as min_acceptable,
    sd.entry_max_price as max_acceptable,
    sd.quantity,
    sd.implied_volatility as leg_iv,
    
    -- Market Timing
    sma.market_direction,
    sma.direction_confidence,
    sma.flow_intensity,
    
    -- Risk Parameters
    sp.max_profit,
    sp.max_loss,
    ROUND(sp.max_loss / 50000.0 * 100, 1) as portfolio_risk_pct,  -- Assuming 50k per trade
    
    -- Exit Plan
    srm.profit_target_primary as profit_target,
    srm.strategy_level_stop as stop_loss_pct,
    srm.time_stop_dte as time_exit_days,
    
    -- Greeks Monitoring
    sge.net_delta as position_delta,
    sge.net_theta as daily_decay,
    sge.net_vega as vol_exposure,
    
    -- Market Levels to Watch
    (SELECT STRING_AGG(CONCAT(level_type, ': ', level), ', ') 
     FROM strategy_price_levels spl 
     WHERE spl.strategy_id = s.id 
     AND ABS(level - s.spot_price) <= sem.one_sd_move) as key_levels,
    
    -- Expected Moves
    sem.one_sd_move as expected_range,
    sem.daily_move as daily_range,
    
    -- Pre-Flight Checks
    CASE WHEN s.total_score >= 0.5 THEN '✓' ELSE '✗' END as score_check,
    CASE WHEN sp.risk_reward_ratio >= 1.0 THEN '✓' ELSE '✗' END as rr_check,
    CASE WHEN s.conviction_level IN ('MEDIUM', 'HIGH', 'VERY_HIGH') THEN '✓' ELSE '✗' END as conviction_check,
    CASE WHEN sma.direction_confidence >= 0.4 THEN '✓' ELSE '✗' END as direction_check,
    
    -- Overall Trade Quality
    CASE 
        WHEN s.total_score >= 0.7 AND sp.risk_reward_ratio >= 2.0 THEN 'EXCELLENT'
        WHEN s.total_score >= 0.6 AND sp.risk_reward_ratio >= 1.5 THEN 'GOOD'
        WHEN s.total_score >= 0.5 AND sp.risk_reward_ratio >= 1.0 THEN 'ACCEPTABLE'
        ELSE 'QUESTIONABLE'
    END as trade_quality,
    
    s.generated_on as setup_time

FROM strategies s
LEFT JOIN strategy_details sd ON s.id = sd.strategy_id
LEFT JOIN strategy_parameters sp ON s.id = sp.strategy_id
LEFT JOIN strategy_risk_management srm ON s.id = srm.strategy_id
LEFT JOIN strategy_greek_exposures sge ON s.id = sge.strategy_id
LEFT JOIN strategy_market_analysis sma ON s.id = sma.strategy_id
LEFT JOIN strategy_expected_moves sem ON s.id = sem.strategy_id
WHERE s.total_score >= 0.5  -- Only viable trades
ORDER BY s.total_score DESC, s.generated_on DESC, sd.id;

COMMENT ON VIEW v_execution_checklist IS 'Complete pre-trade checklist with all details needed for strategy execution';

-- =====================================================
-- 7. QUICK ALERTS VIEW
-- =====================================================
-- High-priority trading alerts and urgent opportunities

CREATE OR REPLACE VIEW v_trading_alerts AS
SELECT 
    'HIGH_SCORE' as alert_type,
    s.stock_name as symbol,
    s.strategy_name,
    s.total_score,
    s.conviction_level,
    CONCAT('Score: ', ROUND(s.total_score, 3), ' | RR: ', ROUND(sp.risk_reward_ratio, 2)) as alert_message,
    s.generated_on as alert_time
FROM strategies s
LEFT JOIN strategy_parameters sp ON s.id = sp.strategy_id
WHERE s.total_score >= 0.7 
  AND s.generated_on >= NOW() - INTERVAL '4 hours'

UNION ALL

SELECT 
    'HIGH_CONVICTION' as alert_type,
    s.stock_name as symbol,
    s.strategy_name,
    s.total_score,
    s.conviction_level,
    CONCAT('Conviction: ', s.conviction_level, ' | Prob: ', ROUND(s.probability_of_profit * 100, 1), '%') as alert_message,
    s.generated_on as alert_time
FROM strategies s
WHERE s.conviction_level IN ('HIGH', 'VERY_HIGH')
  AND s.generated_on >= NOW() - INTERVAL '4 hours'

UNION ALL

SELECT 
    'UNUSUAL_FLOW' as alert_type,
    s.stock_name as symbol,
    s.strategy_name,
    s.total_score,
    s.conviction_level,
    CONCAT('Flow: ', sma.flow_intensity, ' | Direction: ', sma.smart_money_direction) as alert_message,
    s.generated_on as alert_time
FROM strategies s
LEFT JOIN strategy_market_analysis sma ON s.id = sma.strategy_id
WHERE sma.flow_intensity = 'HIGH'
  AND s.generated_on >= NOW() - INTERVAL '4 hours'

ORDER BY alert_time DESC, total_score DESC;

COMMENT ON VIEW v_trading_alerts IS 'High-priority alerts for urgent trading opportunities';

-- =====================================================
-- USAGE EXAMPLES FOR TRADERS
-- =====================================================

/*
-- Example Queries for Options Traders:

-- 1. Get today's best opportunities
SELECT * FROM v_trading_alerts WHERE alert_time >= CURRENT_DATE;

-- 2. View execution details for a specific strategy
SELECT * FROM v_execution_checklist WHERE strategy_id = 15;

-- 3. Compare all strategies for DIXON
SELECT * FROM v_strategy_comparison WHERE symbol = 'DIXON';

-- 4. Portfolio overview for decision making
SELECT * FROM v_portfolio_dashboard WHERE recommendation IN ('STRONG BUY', 'BUY');

-- 5. Risk analysis for position sizing
SELECT * FROM v_risk_management WHERE risk_level IN ('HIGH', 'MEDIUM') ORDER BY opportunity_score DESC;

-- 6. Market opportunities by IV environment
SELECT * FROM v_market_opportunities WHERE iv_environment = 'HIGH' AND opportunity_score >= 70;

-- 7. Ready-to-trade strategies
SELECT * FROM v_trade_execution WHERE trade_priority IN ('IMMEDIATE', 'HIGH') ORDER BY total_score DESC;

*/