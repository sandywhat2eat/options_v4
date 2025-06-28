-- SQL Schema for Historical IV Tracking System

-- Table to store daily IV summaries for each symbol
CREATE TABLE IF NOT EXISTS historical_iv_summary (
    symbol TEXT NOT NULL,
    date DATE NOT NULL,
    atm_iv NUMERIC NOT NULL,
    iv_mean NUMERIC NOT NULL,
    iv_median NUMERIC,
    iv_std NUMERIC,
    call_iv_mean NUMERIC,
    put_iv_mean NUMERIC,
    iv_skew NUMERIC, -- Put IV - Call IV
    total_volume BIGINT,
    total_oi BIGINT,
    spot_price NUMERIC,
    data_points INTEGER NOT NULL, -- Number of valid IV data points
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (symbol, date)
);

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_historical_iv_symbol_date ON historical_iv_summary(symbol, date DESC);

-- Table to store current IV percentiles and rankings
CREATE TABLE IF NOT EXISTS iv_percentiles (
    symbol TEXT NOT NULL,
    lookback_days INTEGER NOT NULL,
    current_iv NUMERIC NOT NULL,
    current_iv_date DATE NOT NULL,
    percentile_10 NUMERIC,
    percentile_25 NUMERIC,
    percentile_50 NUMERIC,
    percentile_75 NUMERIC,
    percentile_90 NUMERIC,
    iv_low NUMERIC,  -- Lowest IV in lookback period
    iv_high NUMERIC, -- Highest IV in lookback period
    iv_rank NUMERIC, -- (Current IV - Low) / (High - Low) * 100
    iv_percentile NUMERIC, -- Actual percentile of current IV
    data_days INTEGER, -- Actual number of days with data
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (symbol, lookback_days)
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_iv_percentiles_symbol ON iv_percentiles(symbol);

-- View to get latest IV environment for each symbol
CREATE OR REPLACE VIEW current_iv_environment AS
SELECT 
    p.symbol,
    p.current_iv,
    p.iv_percentile as percentile_30d,
    p.iv_rank as rank_30d,
    CASE 
        WHEN p.iv_percentile < 20 THEN 'LOW'
        WHEN p.iv_percentile < 40 THEN 'SUBDUED'
        WHEN p.iv_percentile < 60 THEN 'NORMAL'
        WHEN p.iv_percentile < 80 THEN 'ELEVATED'
        ELSE 'HIGH'
    END as iv_environment,
    p.last_updated
FROM iv_percentiles p
WHERE p.lookback_days = 30
ORDER BY p.symbol;

-- Function to get IV statistics for a symbol
CREATE OR REPLACE FUNCTION get_iv_stats(
    p_symbol TEXT,
    p_days INTEGER DEFAULT 30
)
RETURNS TABLE (
    current_iv NUMERIC,
    percentile NUMERIC,
    rank NUMERIC,
    environment TEXT,
    days_of_data INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p.current_iv,
        p.iv_percentile,
        p.iv_rank,
        CASE 
            WHEN p.iv_percentile < 20 THEN 'LOW'
            WHEN p.iv_percentile < 40 THEN 'SUBDUED'
            WHEN p.iv_percentile < 60 THEN 'NORMAL'
            WHEN p.iv_percentile < 80 THEN 'ELEVATED'
            ELSE 'HIGH'
        END as environment,
        p.data_days
    FROM iv_percentiles p
    WHERE p.symbol = p_symbol
    AND p.lookback_days = p_days
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;