"""
Enhanced Sophisticated Portfolio Allocator Improvements
Leverages all available database views for superior allocation
"""

class EnhancedQuantumScoring:
    """Enhanced scoring using market microstructure data"""
    
    def calculate_enhanced_quantum_score(self, strategy, market_data, risk_data):
        """
        Calculate enhanced quantum score with 10 components
        """
        # Base components (adjusted weights)
        probability_score = strategy.get('probability_of_profit', 0) * 0.20
        risk_reward_score = min(strategy.get('risk_reward_ratio', 0) / 3, 1) * 0.20
        
        # NEW: Market opportunity score from v_market_opportunities
        market_opportunity = market_data.get('opportunity_score', 50) / 100 * 0.15
        
        # NEW: Options flow score
        flow_score = self._calculate_flow_score(market_data) * 0.10
        
        # NEW: Technical alignment score
        technical_score = self._calculate_technical_score(market_data) * 0.10
        
        # Base strategy score
        total_score = strategy.get('total_score', 0) * 0.10
        
        # Kelly criterion (reduced weight)
        kelly_score = min(strategy.get('kelly_percent', 0) / 25, 1) * 0.05
        
        # NEW: IV reversion potential
        iv_reversion_score = self._calculate_iv_reversion_score(strategy) * 0.05
        
        # NEW: Risk level integration
        risk_level_score = self._calculate_risk_level_score(risk_data) * 0.03
        
        # Liquidity score (reduced weight)
        liquidity_score = strategy.get('liquidity_score', 0.5) * 0.02
        
        # Calculate total quantum score
        quantum_score = (
            probability_score + risk_reward_score + market_opportunity +
            flow_score + technical_score + total_score + kelly_score +
            iv_reversion_score + risk_level_score + liquidity_score
        ) * 100
        
        return quantum_score
    
    def _calculate_flow_score(self, market_data):
        """Calculate options flow score"""
        flow_intensity = market_data.get('flow_intensity', 'MEDIUM')
        smart_money = market_data.get('smart_money_direction', 'Neutral')
        pcr_interpretation = market_data.get('pcr_interpretation', 'Neutral')
        
        # Score based on flow alignment
        flow_scores = {'HIGH': 1.0, 'MEDIUM': 0.6, 'LOW': 0.3}
        base_score = flow_scores.get(flow_intensity, 0.5)
        
        # Boost for smart money alignment
        if smart_money == 'Bullish' and 'Bull' in pcr_interpretation:
            base_score *= 1.2
        elif smart_money == 'Bearish' and 'Bear' in pcr_interpretation:
            base_score *= 1.2
            
        return min(base_score, 1.0)
    
    def _calculate_technical_score(self, market_data):
        """Calculate technical alignment score"""
        trend = market_data.get('trend', 'Neutral')
        rsi = market_data.get('rsi', 50)
        macd_signal = market_data.get('macd_signal', 'Neutral')
        
        score = 0.5  # Base score
        
        # Trend alignment
        if trend == 'Uptrend' and rsi < 70:
            score += 0.2
        elif trend == 'Downtrend' and rsi > 30:
            score += 0.2
            
        # MACD confirmation
        if macd_signal == trend.replace('trend', 'ish'):
            score += 0.3
            
        return min(score, 1.0)
    
    def _calculate_iv_reversion_score(self, strategy):
        """Calculate IV mean reversion potential score"""
        iv_data = strategy.get('iv_analysis', {})
        reversion_potential = iv_data.get('reversion_potential', 'Low')
        reversion_confidence = iv_data.get('reversion_confidence', 0.3)
        
        potential_scores = {
            'High': 1.0,
            'Moderate': 0.6,
            'Low': 0.3
        }
        
        base_score = potential_scores.get(reversion_potential.split(' ')[0], 0.3)
        return base_score * reversion_confidence
    
    def _calculate_risk_level_score(self, risk_data):
        """Calculate risk level score (inverse - lower risk = higher score)"""
        risk_level = risk_data.get('risk_level', 'MEDIUM')
        risk_scores = {
            'LOW': 1.0,
            'MEDIUM': 0.6,
            'HIGH': 0.3
        }
        return risk_scores.get(risk_level, 0.5)


class DynamicPositionSizer:
    """Dynamic position sizing based on risk management view"""
    
    def get_position_size(self, strategy, risk_data, portfolio_heat):
        """
        Get dynamic position size based on multiple factors
        """
        # Base recommendation from risk management view
        size_recommendation = risk_data.get('position_size_rec', 'SMALL (1-2%)')
        
        # Parse recommendation
        size_map = {
            'MINIMAL (<1%)': (0.005, 0.01),
            'SMALL (1-2%)': (0.01, 0.02),
            'MEDIUM (2-3%)': (0.02, 0.03),
            'LARGE (3-5%)': (0.03, 0.05)
        }
        
        min_size, max_size = size_map.get(size_recommendation, (0.01, 0.02))
        
        # Adjust based on portfolio heat
        if portfolio_heat > 0.8:  # Portfolio already hot
            max_size *= 0.7
        elif portfolio_heat < 0.5:  # Room for more risk
            max_size *= 1.2
            
        # Adjust based on conviction
        conviction = strategy.get('conviction_level', 'MEDIUM')
        conviction_multipliers = {
            'VERY_HIGH': 1.2,
            'HIGH': 1.0,
            'MEDIUM': 0.8,
            'LOW': 0.6
        }
        
        final_size = min_size + (max_size - min_size) * conviction_multipliers.get(conviction, 0.8)
        
        # Never exceed 5% for single position
        return min(final_size, 0.05)


class MarketRegimeAdapter:
    """Adapt allocation based on market regime"""
    
    def get_vix_environment_weights(self, current_vix, vix_percentile):
        """
        Get strategy weights based on granular VIX environment
        """
        if current_vix < 15:  # Very Low VIX
            return {
                'Iron Condor': 0.35,
                'Butterfly Spread': 0.25,
                'Cash-Secured Put': 0.20,
                'Calendar Spread': 0.15,
                'Short Strangle': 0.05
            }
        elif current_vix < 20:  # Low VIX
            return {
                'Iron Condor': 0.25,
                'Butterfly Spread': 0.20,
                'Bull Call Spread': 0.15,
                'Bear Put Spread': 0.15,
                'Calendar Spread': 0.15,
                'Diagonal Spread': 0.10
            }
        elif current_vix < 25:  # Normal VIX
            return {
                'Bull Call Spread': 0.20,
                'Bear Put Spread': 0.20,
                'Iron Condor': 0.15,
                'Calendar Spread': 0.15,
                'Diagonal Spread': 0.15,
                'Long Straddle': 0.10,
                'Butterfly Spread': 0.05
            }
        elif current_vix < 30:  # Elevated VIX
            return {
                'Long Straddle': 0.25,
                'Long Strangle': 0.20,
                'Bull Call Spread': 0.20,
                'Bear Put Spread': 0.20,
                'Calendar Spread': 0.10,
                'Protective Put': 0.05
            }
        else:  # High VIX
            return {
                'Long Straddle': 0.30,
                'Long Strangle': 0.25,
                'Long Call': 0.20,
                'Long Put': 0.15,
                'Protective Put': 0.10
            }
    
    def apply_market_regime_adjustments(self, strategies, market_conditions):
        """
        Apply regime-based adjustments to strategy scores
        """
        # Trend regime adjustments
        trend = market_conditions.get('trend', 'Neutral')
        if trend == 'Strong Uptrend':
            # Boost bullish strategies
            for strategy in strategies:
                if strategy['strategy_type'] == 'Bullish':
                    strategy['regime_boost'] = 1.15
        elif trend == 'Strong Downtrend':
            # Boost bearish strategies
            for strategy in strategies:
                if strategy['strategy_type'] == 'Bearish':
                    strategy['regime_boost'] = 1.15
                    
        # Volatility regime adjustments
        if market_conditions.get('volatility_expanding', False):
            # Boost long volatility strategies
            for strategy in strategies:
                if 'Long' in strategy['strategy_name'] and 'Strad' in strategy['strategy_name']:
                    strategy['regime_boost'] = strategy.get('regime_boost', 1.0) * 1.1
                    
        return strategies


class RealTimeAlertIntegration:
    """Integrate real-time alerts for priority allocation"""
    
    def apply_alert_boosts(self, strategies, active_alerts):
        """
        Apply score boosts based on active alerts
        """
        for strategy in strategies:
            strategy_key = f"{strategy['symbol']}_{strategy['strategy_name']}"
            
            # Check for matching alerts
            for alert in active_alerts:
                if (alert['symbol'] == strategy['symbol'] and 
                    alert['strategy_name'] == strategy['strategy_name']):
                    
                    # Apply boost based on alert type
                    if alert['alert_type'] == 'UNUSUAL_FLOW':
                        strategy['alert_boost'] = 1.15
                    elif alert['alert_type'] == 'HIGH_CONVICTION':
                        strategy['alert_boost'] = 1.10
                    elif alert['alert_type'] == 'HIGH_SCORE':
                        strategy['alert_boost'] = 1.05
                        
                    # Stack boosts for multiple alerts
                    if 'alert_boost' in strategy:
                        strategy['alert_boost'] *= 1.05
                        
        return strategies