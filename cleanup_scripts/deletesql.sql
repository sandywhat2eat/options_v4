DELETE FROM strategy_component_scores;
DELETE FROM strategy_exit_levels;
DELETE FROM strategy_expected_moves;
DELETE FROM strategy_price_levels;
DELETE FROM strategy_iv_analysis;
DELETE FROM strategy_market_analysis;
DELETE FROM strategy_risk_management;
DELETE FROM strategy_monitoring;
DELETE FROM strategy_greek_exposures;
DELETE FROM strategy_parameters;
DELETE FROM strategy_details;
DELETE FROM strategies;




DELETE FROM strategy_component_scores 
WHERE strategy_id IN (
    SELECT id FROM strategies 
    WHERE execution_status != 'executed' OR execution_status IS NULL
);

DELETE FROM strategy_exit_levels 
WHERE strategy_id IN (
    SELECT id FROM strategies 
    WHERE execution_status != 'executed' OR execution_status IS NULL
);

DELETE FROM strategy_expected_moves 
WHERE strategy_id IN (
    SELECT id FROM strategies 
    WHERE execution_status != 'executed' OR execution_status IS NULL
);

DELETE FROM strategy_price_levels 
WHERE strategy_id IN (
    SELECT id FROM strategies 
    WHERE execution_status != 'executed' OR execution_status IS NULL
);

DELETE FROM strategy_iv_analysis 
WHERE strategy_id IN (
    SELECT id FROM strategies 
    WHERE execution_status != 'executed' OR execution_status IS NULL
);

DELETE FROM strategy_market_analysis 
WHERE strategy_id IN (
    SELECT id FROM strategies 
    WHERE execution_status != 'executed' OR execution_status IS NULL
);

DELETE FROM strategy_risk_management 
WHERE strategy_id IN (
    SELECT id FROM strategies 
    WHERE execution_status != 'executed' OR execution_status IS NULL
);

DELETE FROM strategy_monitoring 
WHERE strategy_id IN (
    SELECT id FROM strategies 
    WHERE execution_status != 'executed' OR execution_status IS NULL
);

DELETE FROM strategy_greek_exposures 
WHERE strategy_id IN (
    SELECT id FROM strategies 
    WHERE execution_status != 'executed' OR execution_status IS NULL
);

DELETE FROM strategy_parameters 
WHERE strategy_id IN (
    SELECT id FROM strategies 
    WHERE execution_status != 'executed' OR execution_status IS NULL
);

DELETE FROM strategy_details 
WHERE strategy_id IN (
    SELECT id FROM strategies 
    WHERE execution_status != 'executed' OR execution_status IS NULL
);

-- Finally delete from the parent strategies table
DELETE FROM strategies 
WHERE execution_status != 'executed' OR execution_status IS NULL;
