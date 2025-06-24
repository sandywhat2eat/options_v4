# 📈 Options Derivatives Expert - Trading Guide

## 🎯 **FOR PROFESSIONAL OPTIONS TRADERS**

This guide provides database views and queries specifically designed for options derivatives experts to make informed trading decisions and execute strategies efficiently.

---

## 🚀 **QUICK START**

### 1. **Create Trading Views**
Run the SQL script in Supabase SQL Editor:
```sql
-- Copy and execute: trading_views.sql
```

### 2. **Key Views for Trading**
| View | Purpose | Use Case |
|------|---------|----------|
| `v_trade_execution` | Complete trade details | Strategy execution |
| `v_portfolio_dashboard` | High-level opportunities | Portfolio decisions |
| `v_risk_management` | Risk analysis | Position sizing |
| `v_trading_alerts` | Urgent opportunities | Real-time alerts |

---

## 📊 **TRADING VIEWS BREAKDOWN**

### 🎯 **1. TRADE EXECUTION VIEW**
**Purpose**: Complete strategy details ready for execution

```sql
SELECT * FROM v_trade_execution 
WHERE trade_priority IN ('IMMEDIATE', 'HIGH')
ORDER BY total_score DESC;
```

**Key Fields**:
- `symbol`, `strategy_name`, `conviction_level`
- `leg_action` (BUY/SELL), `option_type` (CE/PE), `strike_price`, `premium`
- `net_delta`, `net_theta`, `net_vega` (position Greeks)
- `profit_target_primary`, `stop_loss_pct`, `time_stop_dte`
- `trade_priority` (IMMEDIATE/HIGH/MEDIUM/LOW)

### 📈 **2. PORTFOLIO DASHBOARD**
**Purpose**: High-level portfolio view for decision making

```sql
SELECT * FROM v_portfolio_dashboard 
WHERE recommendation IN ('STRONG BUY', 'BUY')
ORDER BY total_score DESC;
```

**Key Fields**:
- Strategy summary with risk/reward metrics
- Market direction and confidence
- Greeks exposure summary
- `recommendation` (STRONG BUY/BUY/CONSIDER/AVOID)

### ⚠️ **3. RISK MANAGEMENT VIEW**
**Purpose**: Detailed risk analysis for position sizing

```sql
SELECT * FROM v_risk_management 
WHERE risk_level IN ('HIGH', 'MEDIUM')
ORDER BY total_score DESC;
```

**Key Fields**:
- `position_delta`, `gamma_risk`, `daily_decay`, `vol_risk`
- `position_size_rec` (LARGE/MEDIUM/SMALL/MINIMAL)
- `risk_level` (HIGH/MEDIUM/LOW)
- `nearest_support`, `nearest_resistance`

### 🔥 **4. TRADING ALERTS**
**Purpose**: High-priority urgent opportunities

```sql
SELECT * FROM v_trading_alerts 
WHERE alert_time >= CURRENT_DATE
ORDER BY alert_time DESC, total_score DESC;
```

**Alert Types**:
- `HIGH_SCORE`: Strategies with score > 0.7
- `HIGH_CONVICTION`: HIGH/VERY_HIGH conviction levels
- `UNUSUAL_FLOW`: High options flow intensity

---

## 🎯 **TRADING DECISION WORKFLOWS**

### **🔍 Morning Market Scan**
```sql
-- 1. Check overnight opportunities
SELECT * FROM v_trading_alerts WHERE alert_time >= CURRENT_DATE;

-- 2. Review portfolio opportunities
SELECT * FROM v_portfolio_dashboard 
WHERE recommendation IN ('STRONG BUY', 'BUY') 
ORDER BY total_score DESC;

-- 3. Identify high-priority trades
SELECT * FROM v_trade_execution 
WHERE trade_priority = 'IMMEDIATE'
ORDER BY total_score DESC;
```

### **📊 Strategy Selection Process**
```sql
-- 1. Compare strategies for specific symbol
SELECT * FROM v_strategy_comparison 
WHERE symbol = 'DIXON'
ORDER BY rank_by_score;

-- 2. Check market fit
SELECT * FROM v_market_opportunities 
WHERE strategy_market_fit IN ('PERFECT', 'EXCELLENT')
AND opportunity_score >= 70;

-- 3. Risk assessment
SELECT * FROM v_risk_management 
WHERE symbol = 'DIXON'
ORDER BY total_score DESC;
```

### **⚡ Pre-Trade Execution Checklist**
```sql
-- Complete checklist for strategy execution
SELECT * FROM v_execution_checklist 
WHERE strategy_id = 15;  -- Replace with actual strategy ID

-- Verify trade quality
SELECT strategy_id, symbol, strategy_name, trade_quality,
       score_check, rr_check, conviction_check, direction_check
FROM v_execution_checklist 
WHERE trade_quality IN ('EXCELLENT', 'GOOD');
```

---

## 💼 **TRADE EXECUTION EXAMPLES**

### **Example 1: DIXON Bear Put Spread**
```sql
SELECT 
    symbol,
    strategy_name,
    leg_action,
    option_type,
    strike_price,
    premium,
    quantity,
    max_profit,
    max_loss,
    profit_target_primary,
    stop_loss_pct
FROM v_trade_execution 
WHERE strategy_id = 15;
```

**Expected Output**:
```
symbol | strategy_name    | leg_action | option_type | strike_price | premium | quantity
DIXON  | Bear Put Spread  | BUY        | PE          | 14000        | 157.15  | 50
DIXON  | Bear Put Spread  | SELL       | PE          | 13750        | 78.65   | 50

Max Profit: 8,575 | Max Loss: 3,925 | Profit Target: 4,287.5 | Stop: 50%
```

### **Example 2: Risk Analysis**
```sql
SELECT 
    symbol,
    strategy_name,
    position_delta,
    gamma_risk,
    daily_decay,
    vol_risk,
    position_size_rec,
    risk_level
FROM v_risk_management 
WHERE symbol = 'DIXON';
```

**Expected Output**:
```
symbol | strategy_name    | position_delta | daily_decay | position_size_rec | risk_level
DIXON  | Bear Put Spread  | -0.706         | -24.63      | MEDIUM (2-3%)     | MEDIUM
DIXON  | Cash-Secured Put | -0.324         | -6.35       | SMALL (1-2%)      | LOW
```

---

## 📋 **PROFESSIONAL TRADING QUERIES**

### **🎯 Best Opportunities Today**
```sql
SELECT 
    symbol,
    strategy_name,
    total_score,
    conviction_level,
    probability_of_profit,
    max_profit,
    risk_reward_ratio,
    trade_priority
FROM v_trade_execution 
WHERE DATE(analysis_time) = CURRENT_DATE
  AND trade_priority IN ('IMMEDIATE', 'HIGH')
ORDER BY total_score DESC
LIMIT 10;
```

### **⚡ High-Score Strategies**
```sql
SELECT 
    symbol,
    strategy_name,
    total_score,
    conviction_level,
    market_direction,
    direction_confidence,
    iv_environment,
    recommendation
FROM v_portfolio_dashboard 
WHERE total_score >= 0.7
ORDER BY total_score DESC;
```

### **🔥 Unusual Options Flow**
```sql
SELECT 
    symbol,
    strategy_name,
    market_direction,
    flow_intensity,
    smart_money_direction,
    volume_pcr as put_call_ratio,
    opportunity_score
FROM v_market_opportunities 
WHERE flow_intensity = 'HIGH'
  AND opportunity_score >= 70
ORDER BY opportunity_score DESC;
```

### **📊 Risk-Adjusted Opportunities**
```sql
SELECT 
    symbol,
    strategy_name,
    total_score,
    risk_reward_ratio,
    position_size_rec,
    risk_level,
    max_profit,
    max_loss
FROM v_risk_management 
WHERE risk_reward_ratio >= 2.0
  AND risk_level IN ('LOW', 'MEDIUM')
ORDER BY total_score DESC;
```

### **🎯 Strategy Performance Comparison**
```sql
SELECT 
    symbol,
    strategy_name,
    total_score,
    rank_by_score,
    rank_by_rr,
    rank_by_prob,
    relative_score_pct,
    leg_structure
FROM v_strategy_comparison 
WHERE symbol = 'DIXON'
ORDER BY rank_by_score;
```

---

## 🛡️ **RISK MANAGEMENT GUIDELINES**

### **Position Sizing Recommendations**
- **LARGE (3-5%)**: VERY_HIGH conviction + RR > 2.0
- **MEDIUM (2-3%)**: HIGH conviction + RR > 1.5
- **SMALL (1-2%)**: MEDIUM conviction + RR > 1.0
- **MINIMAL (<1%)**: LOW conviction or RR < 1.0

### **Risk Level Interpretation**
- **HIGH**: |Delta| > 0.5 AND |Gamma| > 0.01
- **MEDIUM**: |Delta| > 0.3 OR |Vega| > 20
- **LOW**: Conservative Greeks exposure

### **Trade Priority Levels**
- **IMMEDIATE**: Score > 0.7 + HIGH/VERY_HIGH conviction
- **HIGH**: Score > 0.6 + HIGH conviction
- **MEDIUM**: Score > 0.5
- **LOW**: Score ≤ 0.5

---

## 📱 **REAL-TIME MONITORING**

### **Active Position Monitoring**
```sql
-- Monitor current positions
SELECT 
    symbol,
    strategy_name,
    net_delta,
    daily_decay,
    vol_risk,
    nearest_support,
    nearest_resistance,
    days_until_expiry
FROM v_risk_management 
WHERE analysis_time >= CURRENT_DATE - INTERVAL '1 day'
ORDER BY risk_level DESC;
```

### **Market Alert System**
```sql
-- Set up alerts for new opportunities
SELECT 
    alert_type,
    symbol,
    strategy_name,
    alert_message,
    alert_time
FROM v_trading_alerts 
WHERE alert_time >= NOW() - INTERVAL '4 hours'
ORDER BY alert_time DESC;
```

---

## 🔧 **ADVANCED ANALYTICS**

### **Greeks Portfolio Aggregation**
```sql
-- Aggregate Greeks across all positions
SELECT 
    SUM(net_delta) as portfolio_delta,
    SUM(net_gamma) as portfolio_gamma,
    SUM(daily_decay) as portfolio_theta,
    SUM(vol_risk) as portfolio_vega,
    COUNT(*) as total_positions
FROM v_risk_management 
WHERE analysis_time >= CURRENT_DATE;
```

### **Performance Tracking**
```sql
-- Track strategy success rates
SELECT 
    strategy_name,
    COUNT(*) as total_strategies,
    AVG(total_score) as avg_score,
    AVG(probability_of_profit) as avg_prob,
    AVG(risk_reward_ratio) as avg_rr
FROM v_portfolio_dashboard 
WHERE analysis_time >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY strategy_name
ORDER BY avg_score DESC;
```

---

## 🎓 **TRADING BEST PRACTICES**

### **✅ Pre-Trade Checklist**
1. **Score Check**: Total score ≥ 0.5
2. **Risk/Reward**: Ratio ≥ 1.0 (preferably ≥ 1.5)
3. **Conviction**: MEDIUM or higher
4. **Direction**: Confidence ≥ 40%
5. **Greeks**: Acceptable exposure levels
6. **Liquidity**: Adequate volume and OI
7. **Market Fit**: Strategy aligns with market conditions

### **🛡️ Risk Management Rules**
1. **Position Size**: Never exceed recommended allocation
2. **Stop Loss**: Always set mechanical stops
3. **Time Decay**: Monitor theta exposure daily
4. **Volatility**: Watch vega during events
5. **Greeks**: Adjust when limits exceeded
6. **Correlation**: Avoid overconcentration

### **📊 Execution Guidelines**
1. **Market Hours**: Trade during liquid hours
2. **Spreads**: Monitor bid-ask spreads
3. **Slippage**: Use limit orders
4. **Assignment**: Monitor ITM shorts near expiry
5. **Rolling**: Plan exit/adjustment strategies
6. **Documentation**: Track all trades and rationale

---

## 🚀 **CONCLUSION**

These database views provide professional-grade tools for options derivatives experts to:

✅ **Identify high-probability opportunities**  
✅ **Execute trades with complete information**  
✅ **Manage risk systematically**  
✅ **Monitor positions effectively**  
✅ **Make data-driven decisions**  

**The system captures every aspect of options analysis needed for professional trading decisions.**

---

*For technical support or view customization, refer to the database schema documentation.*