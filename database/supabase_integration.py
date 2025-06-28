"""
Supabase integration module for Options V4 trading system

This module handles:
1. Connection to Supabase
2. Data transformation from options_v4 output to Supabase schema
3. Batch insertion with transaction management
4. Error handling and rollback
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from decimal import Decimal
import logging
import numpy as np
import pandas as pd

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    print("Warning: Supabase not installed. Run: pip install supabase")

from dotenv import load_dotenv
load_dotenv()

class SupabaseIntegration:
    """Handles integration between Options V4 output and Supabase database"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize Supabase client and setup logging
        
        Args:
            logger: Optional logger instance
        """
        self.logger = logger or self._setup_default_logger()
        
        if not SUPABASE_AVAILABLE:
            self.logger.error("Supabase package not available")
            self.client = None
            return
            
        # Get Supabase credentials from environment (check both patterns)
        self.supabase_url = os.getenv('NEXT_PUBLIC_SUPABASE_URL') or os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('NEXT_PUBLIC_SUPABASE_ANON_KEY') or os.getenv('SUPABASE_ANON_KEY')
        
        if not self.supabase_url or not self.supabase_key:
            self.logger.error("Supabase credentials not found in environment")
            self.client = None
            return
            
        try:
            self.client: Client = create_client(self.supabase_url, self.supabase_key)
            self.logger.info("Supabase client initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize Supabase client: {e}")
            self.client = None
    
    def _setup_default_logger(self) -> logging.Logger:
        """Setup default logger if none provided"""
        logger = logging.getLogger('SupabaseIntegration')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
        return logger
    
    def _clean_value(self, value: Any) -> Any:
        """Clean a single value for JSON serialization"""
        # Handle None/null
        if value is None:
            return None
            
        # Handle numpy types
        if isinstance(value, (np.integer, np.int64)):
            return int(value)
        elif isinstance(value, (np.floating, np.float64)):
            if np.isnan(value) or np.isinf(value):
                return 0  # Default to 0 for NaN/Inf
            return float(value)
        elif isinstance(value, (np.bool_, bool)):
            return bool(value)
        elif isinstance(value, np.ndarray):
            # Clean each element in the array
            return [self._clean_value(v) for v in value.tolist()]
        elif isinstance(value, pd.Series):
            # Clean each element in the series
            return [self._clean_value(v) for v in value.tolist()]
        elif isinstance(value, (pd.Timestamp, np.datetime64)):
            return str(value)
        elif isinstance(value, Decimal):
            return float(value)
        elif isinstance(value, float):
            # Handle regular Python float NaN/Inf
            if np.isnan(value) or np.isinf(value):
                return 0
            return value
        elif isinstance(value, list):
            # Recursively clean lists
            return [self._clean_value(v) for v in value]
        elif isinstance(value, dict):
            # Recursively clean dictionaries
            return {k: self._clean_value(v) for k, v in value.items()}
        return value
    
    def _clean_data(self, data: Any) -> Any:
        """Recursively clean data for JSON serialization"""
        if isinstance(data, dict):
            return {k: self._clean_data(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._clean_data(item) for item in data]
        else:
            return self._clean_value(data)
    
    def store_analysis_results(self, analysis_results: Dict) -> Dict[str, Any]:
        """
        Store complete analysis results in Supabase
        
        Args:
            analysis_results: Complete output from OptionsAnalyzer
            
        Returns:
            Dictionary with success status and stored strategy IDs
        """
        if not self.client:
            return {'success': False, 'error': 'Supabase client not initialized'}
            
        stored_strategies = {}
        errors = []
        
        try:
            # Process portfolio results
            if 'symbol_results' in analysis_results:
                for symbol, symbol_data in analysis_results['symbol_results'].items():
                    if not symbol_data.get('success', False):
                        continue
                        
                    result = self._store_symbol_analysis(symbol, symbol_data)
                    if result['success']:
                        stored_strategies[symbol] = result['strategy_ids']
                    else:
                        errors.append(f"{symbol}: {result['error']}")
            
            # Process single symbol result
            elif analysis_results.get('success') and 'top_strategies' in analysis_results:
                symbol = analysis_results.get('symbol', 'UNKNOWN')
                result = self._store_symbol_analysis(symbol, analysis_results)
                if result['success']:
                    stored_strategies[symbol] = result['strategy_ids']
                else:
                    errors.append(f"{symbol}: {result['error']}")
            
            return {
                'success': len(stored_strategies) > 0,
                'stored_strategies': stored_strategies,
                'errors': errors,
                'total_stored': sum(len(ids) for ids in stored_strategies.values())
            }
            
        except Exception as e:
            self.logger.error(f"Error storing analysis results: {e}")
            return {'success': False, 'error': str(e)}
    
    def _store_symbol_analysis(self, symbol: str, symbol_data: Dict) -> Dict[str, Any]:
        """Store analysis for a single symbol"""
        strategy_ids = []
        
        try:
            # Extract common data
            spot_price = symbol_data.get('spot_price', 0)
            market_analysis = symbol_data.get('market_analysis', {})
            price_levels = symbol_data.get('price_levels', {})
            
            # Store each recommended strategy
            for strategy_rank in symbol_data.get('top_strategies', []):
                strategy_id = self._store_single_strategy(
                    symbol, 
                    strategy_rank, 
                    spot_price,
                    market_analysis,
                    price_levels
                )
                if strategy_id:
                    strategy_ids.append(strategy_id)
            
            return {
                'success': True,
                'strategy_ids': strategy_ids
            }
            
        except Exception as e:
            self.logger.error(f"Error storing symbol {symbol}: {e}")
            return {'success': False, 'error': str(e)}
    
    def _store_single_strategy(self, symbol: str, strategy_data: Dict, 
                              spot_price: float, market_analysis: Dict,
                              price_levels: Dict) -> Optional[int]:
        """Store a single strategy with all related data"""
        try:
            # 1. Insert main strategy record
            strategy_id = self._insert_strategy_main(
                symbol, strategy_data, spot_price, market_analysis
            )
            
            if not strategy_id:
                return None
            
            # 2. Insert strategy legs
            self._insert_strategy_legs(strategy_id, strategy_data.get('legs', []))
            
            # 3. Insert strategy parameters
            self._insert_strategy_parameters(strategy_id, strategy_data)
            
            # 4. Insert Greek exposures
            self._insert_greek_exposures(strategy_id, strategy_data.get('legs', []))
            
            # 5. Insert monitoring levels
            self._insert_monitoring_levels(strategy_id, market_analysis, price_levels)
            
            # 6. Insert risk management
            self._insert_risk_management(strategy_id, strategy_data)
            
            # 7. Insert market analysis
            self._insert_market_analysis(strategy_id, market_analysis)
            
            # 8. Insert IV analysis
            if 'iv_analysis' in market_analysis:
                self._insert_iv_analysis(strategy_id, market_analysis['iv_analysis'])
            
            # 9. Insert price levels
            self._insert_price_levels(strategy_id, price_levels)
            
            # 10. Insert expected moves
            if 'expected_moves' in price_levels:
                self._insert_expected_moves(strategy_id, price_levels)
            
            # 11. Insert exit levels
            if 'exit_conditions' in strategy_data:
                self._insert_exit_levels(strategy_id, strategy_data['exit_conditions'])
            
            # 12. Insert component scores
            if 'component_scores' in strategy_data:
                self._insert_component_scores(strategy_id, strategy_data['component_scores'])
            
            self.logger.info(f"Successfully stored strategy {strategy_id}: {strategy_data['name']} for {symbol}")
            return strategy_id
            
        except Exception as e:
            self.logger.error(f"Error storing strategy: {e}")
            return None
    
    def _insert_strategy_main(self, symbol: str, strategy_data: Dict, 
                             spot_price: float, market_analysis: Dict) -> Optional[int]:
        """Insert main strategy record with duplicate prevention"""
        try:
            # Get today's date in ISO format for duplicate check
            today = datetime.now().date().isoformat()
            
            # Check for existing record for same symbol + date + strategy
            existing_check = self.client.table('strategies').select('id').eq(
                'stock_name', symbol
            ).eq(
                'strategy_name', strategy_data['name']
            ).gte(
                'generated_on', f"{today}T00:00:00"
            ).lte(
                'generated_on', f"{today}T23:59:59"
            ).execute()
            
            if existing_check.data and len(existing_check.data) > 0:
                self.logger.info(f"Strategy {strategy_data['name']} for {symbol} already exists for today, skipping insert")
                return existing_check.data[0]['id']
            
            # Fetch sector and industry from stock_data table
            sector = None
            industry = None
            try:
                stock_data_result = self.client.table('stock_data').select('sector,industry').eq('symbol', symbol).execute()
                if stock_data_result.data and len(stock_data_result.data) > 0:
                    sector = stock_data_result.data[0].get('sector')
                    industry = stock_data_result.data[0].get('industry')
                    self.logger.debug(f"Found sector: {sector}, industry: {industry} for symbol: {symbol}")
                else:
                    self.logger.warning(f"No sector/industry data found for symbol: {symbol}")
            except Exception as e:
                self.logger.warning(f"Error fetching sector/industry for {symbol}: {e}")
                # Continue with None values
            
            # Map confidence to conviction level
            confidence = market_analysis.get('confidence', 0.5)
            conviction_level = self._map_conviction_level(confidence)
            
            # Calculate risk/reward ratio
            max_profit = strategy_data.get('max_profit', 0)
            max_loss = abs(strategy_data.get('max_loss', 0))
            risk_reward_ratio = max_profit / max_loss if max_loss > 0 else 0
            
            # Get net premium from legs
            net_premium = sum(
                leg.get('premium', 0) * (-1 if leg.get('position') == 'SHORT' else 1)
                for leg in strategy_data.get('legs', [])
            )
            
            strategy_record = {
                'stock_name': symbol,
                'strategy_name': strategy_data['name'],
                'strategy_type': self._get_strategy_type(strategy_data['name']),
                'time_horizon': market_analysis.get('timeframe', {}).get('duration', '10-30 days'),
                'market_outlook': f"{market_analysis.get('direction', 'Neutral')} {market_analysis.get('sub_category', '')}".strip(),
                'probability_of_profit': self._clean_value(strategy_data.get('probability_profit', 0)),
                'risk_reward_ratio': self._clean_value(risk_reward_ratio),
                'market_view': json.dumps(self._clean_data(market_analysis.get('details', {}))),
                'technical_factors': json.dumps(self._clean_data(market_analysis.get('details', {}).get('technical', {}))),
                'volatility_outlook': market_analysis.get('iv_analysis', {}).get('iv_environment', 'NORMAL'),
                'key_risks': self._extract_key_risks(strategy_data),
                'description': strategy_data.get('optimal_outcome', ''),
                'net_premium': self._clean_value(net_premium),
                'conviction_level': conviction_level,
                'generated_on': datetime.now().isoformat(),
                # New fields
                'total_score': self._clean_value(strategy_data.get('total_score', 0)),
                'confidence_score': self._clean_value(confidence),
                'market_direction_strength': self._clean_value(market_analysis.get('strength', 0)),
                'iv_percentile': self._clean_value(market_analysis.get('iv_analysis', {}).get('percentile_analysis', {}).get('percentile', 50)),
                'iv_environment': market_analysis.get('iv_analysis', {}).get('iv_environment', 'NORMAL'),
                'spot_price': self._clean_value(spot_price),
                'analysis_timestamp': datetime.now().isoformat(),
                'market_sub_category': market_analysis.get('sub_category', ''),
                'component_scores': json.dumps(self._clean_data(strategy_data.get('component_scores', {}))),
                'optimal_outcome': strategy_data.get('optimal_outcome', ''),
                # Sector and industry fields fetched from stock_data table
                'sector': sector,
                'industry': industry
            }
            
            # Insert and get ID
            result = self.client.table('strategies').insert(strategy_record).execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]['id']
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error inserting strategy main: {e}")
            return None
    
    def _insert_strategy_legs(self, strategy_id: int, legs: List[Dict]) -> None:
        """Insert strategy leg details"""
        try:
            leg_records = []
            
            for leg in legs:
                leg_record = {
                    'strategy_id': strategy_id,
                    'setup_type': 'BUY' if leg.get('position') == 'LONG' else 'SELL',
                    'instrument': f"{leg.get('option_type', '')}_OPTION",  # Placeholder
                    'lots': 1,  # Default, should be calculated based on capital
                    'quantity': 50,  # Default lot size, should come from lot_size lookup
                    'strike_price': self._clean_value(leg.get('strike', 0)),
                    'option_type': 'CE' if leg.get('option_type') == 'CALL' else 'PE',
                    'expiry_date': None,  # Should be provided
                    'entry_price': self._clean_value(leg.get('premium', 0)),
                    'delta': self._clean_value(leg.get('delta', 0)),
                    'gamma': self._clean_value(leg.get('gamma', 0)),  # Not in current output
                    'theta': self._clean_value(leg.get('theta', 0)),  # Not in current output
                    'vega': self._clean_value(leg.get('vega', 0)),    # Not in current output
                    'implied_volatility': self._clean_value(leg.get('iv', 0)),  # Not in current output
                    'rationale': leg.get('rationale', ''),
                    'entry_min_price': self._clean_value(leg.get('premium', 0) * 0.95),  # 5% buffer
                    'entry_max_price': self._clean_value(leg.get('premium', 0) * 1.05)   # 5% buffer
                }
                leg_records.append(leg_record)
            
            if leg_records:
                self.client.table('strategy_details').insert(leg_records).execute()
                
        except Exception as e:
            self.logger.error(f"Error inserting strategy legs: {e}")
    
    def _insert_strategy_parameters(self, strategy_id: int, strategy_data: Dict) -> None:
        """Insert strategy parameters"""
        try:
            max_profit = strategy_data.get('max_profit', 0)
            max_loss = abs(strategy_data.get('max_loss', 0))
            
            params_record = {
                'strategy_id': strategy_id,
                'max_profit': self._clean_value(max_profit),
                'max_loss': self._clean_value(max_loss),
                'breakeven_point': 0,  # Should be calculated
                'margin_required': 0,  # Should be calculated
                'expiry_date': None,   # Should be provided
                'risk_reward_ratio': self._clean_value(max_profit / max_loss if max_loss > 0 else 0),
                'probability_profit': self._clean_value(strategy_data.get('probability_profit', 0)),
                'expected_value': 0,   # Should be calculated
                'target_price': self._clean_value(self._extract_numeric_from_exit_conditions(strategy_data.get('exit_conditions', {}), 'profit_target')),
                'stop_loss': self._clean_value(self._extract_numeric_from_exit_conditions(strategy_data.get('exit_conditions', {}), 'stop_loss'))
            }
            
            self.client.table('strategy_parameters').insert(params_record).execute()
            
        except Exception as e:
            self.logger.error(f"Error inserting strategy parameters: {e}")
    
    def _insert_greek_exposures(self, strategy_id: int, legs: List[Dict]) -> None:
        """Insert net Greek exposures"""
        try:
            # Calculate net Greeks from legs
            net_delta = sum(leg.get('delta', 0) for leg in legs)
            net_gamma = sum(leg.get('gamma', 0) for leg in legs)
            net_theta = sum(leg.get('theta', 0) for leg in legs)
            net_vega = sum(leg.get('vega', 0) for leg in legs)
            
            greek_record = {
                'strategy_id': strategy_id,
                'net_delta': self._clean_value(net_delta),
                'net_gamma': self._clean_value(net_gamma),
                'net_theta': self._clean_value(net_theta),
                'net_vega': self._clean_value(net_vega)
            }
            
            self.client.table('strategy_greek_exposures').insert(greek_record).execute()
            
        except Exception as e:
            self.logger.error(f"Error inserting Greek exposures: {e}")
    
    def _insert_monitoring_levels(self, strategy_id: int, market_analysis: Dict, price_levels: Dict) -> None:
        """Insert monitoring levels"""
        try:
            # Extract support/resistance from key_levels
            key_levels = price_levels.get('key_levels', [])
            support_levels = [l['level'] for l in key_levels if l['type'] == 'support']
            resistance_levels = [l['level'] for l in key_levels if l['type'] == 'resistance']
            
            monitoring_record = {
                'strategy_id': strategy_id,
                'support_level': self._clean_value(min(support_levels) if support_levels else 0),
                'resistance_level': self._clean_value(max(resistance_levels) if resistance_levels else 0),
                'iv_upper_limit': self._clean_value(market_analysis.get('iv_analysis', {}).get('sector_normal_range', [0, 40])[1]),
                'iv_lower_limit': self._clean_value(market_analysis.get('iv_analysis', {}).get('sector_normal_range', [25, 0])[0]),
                'max_pain': self._clean_value(price_levels.get('max_pain', {}).get('max_pain', 0)),
                'spot_vs_max_pain': self._clean_value(price_levels.get('max_pain', {}).get('spot_vs_max_pain', 0)),
                'poc_level': self._clean_value(price_levels.get('value_area', {}).get('poc', 0)),
                'value_area_high': self._clean_value(price_levels.get('value_area', {}).get('vah', 0)),
                'value_area_low': self._clean_value(price_levels.get('value_area', {}).get('val', 0)),
                'expected_move_1sd': self._clean_value(price_levels.get('expected_moves', {}).get('one_sd_move', 0)),
                'expected_move_2sd': self._clean_value(price_levels.get('expected_moves', {}).get('two_sd_move', 0))
            }
            
            self.client.table('strategy_monitoring').insert(monitoring_record).execute()
            
        except Exception as e:
            self.logger.error(f"Error inserting monitoring levels: {e}")
    
    def _insert_risk_management(self, strategy_id: int, strategy_data: Dict) -> None:
        """Insert risk management data"""
        try:
            exit_conditions = strategy_data.get('exit_conditions', {})
            
            # Handle both nested structure and simple string-based structure
            if isinstance(exit_conditions.get('profit_targets'), dict):
                # New nested structure
                profit_targets = exit_conditions.get('profit_targets', {})
                stop_losses = exit_conditions.get('stop_losses', {})
                time_exits = exit_conditions.get('time_exits', {})
            else:
                # Legacy simple string structure - extract defaults
                profit_targets = {}
                stop_losses = {}
                time_exits = {}
            
            risk_record = {
                'strategy_id': strategy_id,
                'total_capital': 1000000,  # Default, should be configurable
                'capital_per_trade': 50000,  # Default, should be calculated
                'max_capital_at_risk': self._clean_value(abs(strategy_data.get('max_loss', 0))),
                'strategy_level_stop': self._clean_value(stop_losses.get('primary', {}).get('loss_pct', 50)),
                'trailing_stop': self._clean_value(profit_targets.get('trailing', {}).get('trail_by', 0)),
                'time_based_stop': str(time_exits.get('primary_dte', 7)) + ' DTE',
                'adjustment_criteria': json.dumps(self._clean_data(exit_conditions.get('adjustment_triggers', exit_conditions.get('adjustment', {})))),
                'exit_conditions': json.dumps(self._clean_data(exit_conditions)),
                'overall_risk': 'MEDIUM',  # Should be calculated
                # New fields
                'profit_target_primary': self._clean_value(profit_targets.get('primary', {}).get('target', 0)),
                'profit_target_pct': self._clean_value(profit_targets.get('primary', {}).get('target_pct', 50)),
                'scaling_exits': json.dumps(self._clean_data(profit_targets.get('scaling', {}))),
                'trailing_stop_activation': self._clean_value(profit_targets.get('trailing', {}).get('activate_at', 0)),
                'technical_stops': json.dumps(self._clean_data(stop_losses.get('technical', {}))),
                'time_stop_dte': time_exits.get('primary_dte', 7),
                'greek_triggers': json.dumps(self._clean_data(exit_conditions.get('greek_triggers', {})))
            }
            
            self.client.table('strategy_risk_management').insert(risk_record).execute()
            
        except Exception as e:
            self.logger.error(f"Error inserting risk management: {e}")
    
    def _insert_market_analysis(self, strategy_id: int, market_analysis: Dict) -> None:
        """Insert detailed market analysis"""
        try:
            technical = market_analysis.get('details', {}).get('technical', {})
            options = market_analysis.get('details', {}).get('options', {})
            price_action = market_analysis.get('details', {}).get('price_action', {})
            
            market_record = {
                'strategy_id': strategy_id,
                # Market Direction
                'market_direction': market_analysis.get('direction', 'Neutral'),
                'direction_confidence': self._clean_value(market_analysis.get('confidence', 0)),
                'direction_strength': self._clean_value(market_analysis.get('strength', 0)),
                'final_market_score': self._clean_value(market_analysis.get('final_score', 0)),
                'timeframe': market_analysis.get('timeframe', {}).get('timeframe', 'mid'),
                'timeframe_duration': market_analysis.get('timeframe', {}).get('duration', '10-30 days'),
                
                # Technical Analysis
                'technical_score': self._clean_value(market_analysis.get('components', {}).get('technical_score', 0)),
                'trend': technical.get('trend', ''),
                'ema_alignment': technical.get('ema_alignment', ''),
                'rsi': self._clean_value(technical.get('rsi', 0)),
                'macd_signal': technical.get('macd_signal', ''),
                'volume_ratio': self._clean_value(technical.get('volume_ratio', 0)),
                'volume_trend': technical.get('volume_trend', ''),
                'bb_width': self._clean_value(technical.get('bb_width', 0)),
                'atr': self._clean_value(technical.get('atr', 0)),
                'price_position': technical.get('price_position', ''),
                'pattern': technical.get('pattern', ''),
                
                # Options Flow
                'options_score': self._clean_value(market_analysis.get('components', {}).get('options_score', 0)),
                'volume_pcr': self._clean_value(options.get('volume_pcr', 0)),
                'oi_pcr': self._clean_value(options.get('oi_pcr', 0)),
                'pcr_interpretation': options.get('pcr_interpretation', ''),
                'atm_call_volume': self._clean_value(options.get('atm_call_volume', 0)),
                'atm_put_volume': self._clean_value(options.get('atm_put_volume', 0)),
                'atm_bias': options.get('atm_bias', ''),
                'iv_skew': self._clean_value(options.get('iv_skew', 0)),
                'iv_skew_type': options.get('iv_skew_type', ''),
                'flow_intensity': options.get('flow_intensity', ''),
                'smart_money_direction': options.get('smart_money_direction', ''),
                'unusual_activity': json.dumps(self._clean_data(options.get('unusual_activity', []))),
                
                # Price Action
                'price_action_score': self._clean_value(market_analysis.get('components', {}).get('price_action_score', 0)),
                'oi_max_pain': self._clean_value(options.get('oi_max_pain', 0)),
                'oi_support': self._clean_value(options.get('oi_support', 0)),
                'oi_resistance': self._clean_value(options.get('oi_resistance', 0))
            }
            
            self.client.table('strategy_market_analysis').insert(market_record).execute()
            
        except Exception as e:
            self.logger.error(f"Error inserting market analysis: {e}")
    
    def _insert_iv_analysis(self, strategy_id: int, iv_analysis: Dict) -> None:
        """Insert IV analysis data"""
        try:
            iv_record = {
                'strategy_id': strategy_id,
                'atm_iv': self._clean_value(iv_analysis.get('atm_iv', 0)),
                'iv_environment': iv_analysis.get('iv_environment', 'NORMAL'),
                'atm_call_iv': self._clean_value(iv_analysis.get('atm_call_iv', 0)),
                'atm_put_iv': self._clean_value(iv_analysis.get('atm_put_iv', 0)),
                'call_put_iv_diff': self._clean_value(iv_analysis.get('call_put_iv_diff', 0)),
                
                # IV Relativity
                'sector_relative': iv_analysis.get('iv_relativity', {}).get('sector_relative', ''),
                'percentile_in_sector': self._clean_value(iv_analysis.get('iv_relativity', {}).get('percentile_in_sector', 50)),
                'market_relative': iv_analysis.get('iv_relativity', {}).get('market_relative', ''),
                'iv_vs_market_pct': self._clean_value(iv_analysis.get('iv_relativity', {}).get('iv_vs_market_pct', 0)),
                'sector_normal_range_low': self._clean_value(iv_analysis.get('sector_normal_range', [25, 40])[0]),
                'sector_normal_range_high': self._clean_value(iv_analysis.get('sector_normal_range', [25, 40])[1]),
                'iv_interpretation': iv_analysis.get('iv_relativity', {}).get('interpretation', ''),
                
                # Mean Reversion
                'reversion_potential': iv_analysis.get('mean_reversion', {}).get('reversion_potential', ''),
                'reversion_direction': iv_analysis.get('mean_reversion', {}).get('direction', ''),
                'reversion_confidence': self._clean_value(iv_analysis.get('mean_reversion', {}).get('confidence', 0)),
                'expected_iv': self._clean_value(iv_analysis.get('mean_reversion', {}).get('expected_iv', 0)),
                'reversion_time_horizon': iv_analysis.get('mean_reversion', {}).get('time_horizon', ''),
                
                # Recommendations
                'preferred_strategies': json.dumps(self._clean_data(iv_analysis.get('recommendations', {}).get('preferred_strategies', []))),
                'avoid_strategies': json.dumps(self._clean_data(iv_analysis.get('recommendations', {}).get('avoid_strategies', []))),
                'reasoning': iv_analysis.get('recommendations', {}).get('reasoning', '')
            }
            
            self.client.table('strategy_iv_analysis').insert(iv_record).execute()
            
        except Exception as e:
            self.logger.error(f"Error inserting IV analysis: {e}")
    
    def _insert_price_levels(self, strategy_id: int, price_levels: Dict) -> None:
        """Insert individual price levels"""
        try:
            level_records = []
            
            for level_data in price_levels.get('key_levels', []):
                level_record = {
                    'strategy_id': strategy_id,
                    'level': self._clean_value(level_data.get('level', 0)),
                    'level_type': level_data.get('type', ''),
                    'source': level_data.get('source', ''),
                    'strength': level_data.get('strength', ''),
                    'timeframe': 'mid'  # Default
                }
                level_records.append(level_record)
            
            if level_records:
                self.client.table('strategy_price_levels').insert(level_records).execute()
                
        except Exception as e:
            self.logger.error(f"Error inserting price levels: {e}")
    
    def _insert_expected_moves(self, strategy_id: int, price_levels: Dict) -> None:
        """Insert expected move calculations"""
        try:
            expected_moves = price_levels.get('expected_moves', {})
            value_area = price_levels.get('value_area', {})
            price_targets = price_levels.get('price_targets', {})
            
            moves_record = {
                'strategy_id': strategy_id,
                'straddle_price': self._clean_value(expected_moves.get('straddle_price', 0)),
                'one_sd_move': self._clean_value(expected_moves.get('one_sd_move', 0)),
                'one_sd_pct': self._clean_value(expected_moves.get('one_sd_pct', 0)),
                'two_sd_move': self._clean_value(expected_moves.get('two_sd_move', 0)),
                'two_sd_pct': self._clean_value(expected_moves.get('two_sd_pct', 0)),
                'daily_move': self._clean_value(expected_moves.get('daily_move', 0)),
                'daily_pct': self._clean_value(expected_moves.get('daily_pct', 0)),
                'upper_expected_1sd': self._clean_value(expected_moves.get('upper_expected', 0)),
                'lower_expected_1sd': self._clean_value(expected_moves.get('lower_expected', 0)),
                'upper_expected_2sd': self._clean_value(expected_moves.get('upper_2sd', 0)),
                'lower_expected_2sd': self._clean_value(expected_moves.get('lower_2sd', 0)),
                'poc': self._clean_value(value_area.get('poc', 0)),
                'value_area_high': self._clean_value(value_area.get('vah', 0)),
                'value_area_low': self._clean_value(value_area.get('val', 0)),
                'va_width_pct': self._clean_value(value_area.get('va_width_pct', 0)),
                'spot_in_va': value_area.get('spot_in_va', False),
                'bullish_consensus_target': self._clean_value(price_targets.get('consensus', {}).get('bullish_target', 0)),
                'bearish_consensus_target': self._clean_value(price_targets.get('consensus', {}).get('bearish_target', 0))
            }
            
            self.client.table('strategy_expected_moves').insert(moves_record).execute()
            
        except Exception as e:
            self.logger.error(f"Error inserting expected moves: {e}")
    
    def _extract_numeric_from_exit_conditions(self, exit_conditions: Dict, field: str) -> float:
        """Extract numeric value from exit conditions which may be in string format"""
        try:
            # Handle nested structure
            if isinstance(exit_conditions.get('profit_targets'), dict):
                if field == 'profit_target':
                    return exit_conditions.get('profit_targets', {}).get('primary', {}).get('target', 0)
                elif field == 'stop_loss':
                    return exit_conditions.get('stop_losses', {}).get('primary', {}).get('loss_amount', 0)
            
            # Handle simple string structure - try to extract percentage
            value_str = exit_conditions.get(field, '')
            if isinstance(value_str, str):
                # Extract numeric value from strings like "50-100% of debit paid"
                import re
                numbers = re.findall(r'(\d+)', value_str)
                if numbers:
                    return float(numbers[0])  # Return first number found
            
            return 0
        except Exception:
            return 0
    
    def _insert_exit_levels(self, strategy_id: int, exit_conditions: Dict) -> None:
        """Insert detailed exit condition levels"""
        try:
            # Handle both nested and simple string structures
            if not isinstance(exit_conditions.get('profit_targets'), dict):
                # Simple string structure - skip detailed exit levels
                return
                
            exit_records = []
            
            # Profit targets
            profit_targets = exit_conditions.get('profit_targets', {})
            if 'primary' in profit_targets:
                exit_records.append({
                    'strategy_id': strategy_id,
                    'exit_type': 'profit_target',
                    'level_name': 'primary',
                    'trigger_value': self._clean_value(profit_targets['primary'].get('target', 0)),
                    'trigger_type': 'price',
                    'action': profit_targets['primary'].get('action', ''),
                    'reasoning': profit_targets['primary'].get('reasoning', '')
                })
            
            # Scaling exits
            for level, data in profit_targets.get('scaling', {}).items():
                exit_records.append({
                    'strategy_id': strategy_id,
                    'exit_type': 'profit_target',
                    'level_name': f'scaling_{level}',
                    'trigger_value': self._clean_value(data.get('profit', 0)),
                    'trigger_type': 'price',
                    'action': data.get('action', ''),
                    'reasoning': f'Scaling exit at {level}'
                })
            
            # Stop losses
            stop_losses = exit_conditions.get('stop_losses', {})
            if 'primary' in stop_losses:
                exit_records.append({
                    'strategy_id': strategy_id,
                    'exit_type': 'stop_loss',
                    'level_name': 'primary',
                    'trigger_value': self._clean_value(stop_losses['primary'].get('loss_pct', 50)),
                    'trigger_type': 'percentage',
                    'action': stop_losses['primary'].get('action', ''),
                    'reasoning': stop_losses['primary'].get('type', '')
                })
            
            # Time exits
            time_exits = exit_conditions.get('time_exits', {})
            if 'primary_dte' in time_exits:
                exit_records.append({
                    'strategy_id': strategy_id,
                    'exit_type': 'time_exit',
                    'level_name': 'primary',
                    'trigger_value': time_exits['primary_dte'],
                    'trigger_type': 'dte',
                    'action': 'Close position',
                    'reasoning': 'Time decay acceleration'
                })
            
            if exit_records:
                self.client.table('strategy_exit_levels').insert(exit_records).execute()
                
        except Exception as e:
            self.logger.error(f"Error inserting exit levels: {e}")
    
    def _insert_component_scores(self, strategy_id: int, component_scores: Dict) -> None:
        """Insert strategy component scores"""
        try:
            scores_record = {
                'strategy_id': strategy_id,
                'probability_score': self._clean_value(component_scores.get('probability', 0)),
                'risk_reward_score': self._clean_value(component_scores.get('risk_reward', 0)),
                'direction_score': self._clean_value(component_scores.get('direction', 0)),
                'iv_fit_score': self._clean_value(component_scores.get('iv_fit', 0)),
                'liquidity_score': self._clean_value(component_scores.get('liquidity', 0))
            }
            
            self.client.table('strategy_component_scores').insert(scores_record).execute()
            
        except Exception as e:
            self.logger.error(f"Error inserting component scores: {e}")
    
    # Helper methods
    
    def _map_conviction_level(self, confidence: float) -> str:
        """Map confidence score to conviction level"""
        if confidence >= 0.8:  # Reduced from 0.9
            return 'VERY_HIGH'
        elif confidence >= 0.65:  # Reduced from 0.7
            return 'HIGH'
        elif confidence >= 0.45:  # Reduced from 0.5
            return 'MEDIUM'
        elif confidence >= 0.25:  # Reduced from 0.3
            return 'LOW'
        else:
            return 'VERY_LOW'
    
    def _get_strategy_type(self, strategy_name: str) -> str:
        """Determine strategy type from name"""
        strategy_types = {
            'Long Call': 'Directional',
            'Long Put': 'Directional',
            'Bull Call Spread': 'Directional',
            'Bear Put Spread': 'Directional',
            'Bull Put Spread': 'Directional',
            'Bear Call Spread': 'Directional',
            'Iron Condor': 'Neutral',
            'Iron Butterfly': 'Neutral',
            'Butterfly Spread': 'Neutral',
            'Short Straddle': 'Neutral',
            'Short Strangle': 'Neutral',
            'Long Straddle': 'Volatility',
            'Long Strangle': 'Volatility',
            'Cash-Secured Put': 'Income',
            'Covered Call': 'Income',
            'Calendar Spread': 'Advanced',
            'Diagonal Spread': 'Advanced',
            'Call Ratio Spread': 'Advanced',
            'Put Ratio Spread': 'Advanced',
            'Jade Lizard': 'Advanced',
            'Broken Wing Butterfly': 'Advanced'
        }
        return strategy_types.get(strategy_name, 'Unknown')
    
    def _extract_key_risks(self, strategy_data: Dict) -> str:
        """Extract key risks from strategy data"""
        risks = []
        
        # Add risk based on strategy type
        strategy_name = strategy_data.get('name', '')
        if 'Long' in strategy_name:
            risks.append('Time decay acceleration near expiry')
        if 'Short' in strategy_name:
            risks.append('Unlimited risk if uncovered')
        if 'Spread' in strategy_name:
            risks.append('Pin risk at expiration')
        if 'Condor' in strategy_name or 'Butterfly' in strategy_name:
            risks.append('Assignment risk on short strikes')
            
        # Add general risks
        risks.extend([
            'Market gap risk',
            'Liquidity risk in fast markets',
            'Early assignment on American options'
        ])
        
        return '; '.join(risks[:3])  # Return top 3 risks