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
    
    def __init__(self, logger: Optional[logging.Logger] = None, batch_size: int = 50):
        """
        Initialize Supabase client and setup logging
        
        Args:
            logger: Optional logger instance
            batch_size: Number of records to insert per batch (default: 50)
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
            
            # Batch processing configuration
            self.batch_size = batch_size
            self.batch_data = {
                'strategies': [],
                'strategy_details': [],
                'strategy_parameters': [],
                'strategy_greek_exposures': [],
                'strategy_monitoring': [],
                'strategy_risk_management': [],
                'strategy_market_analysis': [],
                'strategy_iv_analysis': [],
                'strategy_price_levels': [],
                'strategy_expected_moves': [],
                'strategy_exit_levels': [],
                'strategy_component_scores': []
            }
            
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
        Store complete analysis results in Supabase using batch operations
        
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
            # Clear batch data
            self._clear_batch_data()
            
            # Collect all data in batches
            if 'symbol_results' in analysis_results:
                for symbol, symbol_data in analysis_results['symbol_results'].items():
                    if not symbol_data.get('success', False):
                        continue
                        
                    result = self._collect_symbol_data(symbol, symbol_data)
                    if result['success']:
                        stored_strategies[symbol] = result['strategy_ids']
                    else:
                        errors.append(f"{symbol}: {result['error']}")
            
            # Process single symbol result
            elif analysis_results.get('success') and 'top_strategies' in analysis_results:
                symbol = analysis_results.get('symbol', 'UNKNOWN')
                result = self._collect_symbol_data(symbol, analysis_results)
                if result['success']:
                    stored_strategies[symbol] = result['strategy_ids']
                else:
                    errors.append(f"{symbol}: {result['error']}")
            
            # Execute batch inserts
            batch_result = self._execute_batch_inserts()
            if not batch_result['success']:
                errors.extend(batch_result.get('errors', []))
            
            return {
                'success': len(stored_strategies) > 0,
                'stored_strategies': stored_strategies,
                'errors': errors,
                'total_stored': sum(len(ids) for ids in stored_strategies.values())
            }
            
        except Exception as e:
            self.logger.error(f"Error storing analysis results: {e}")
            return {'success': False, 'error': str(e)}
    
    def _collect_symbol_data(self, symbol: str, symbol_data: Dict) -> Dict[str, Any]:
        """Collect analysis data for a single symbol for batch processing"""
        strategy_ids = []
        
        try:
            # Extract common data
            spot_price = symbol_data.get('spot_price', 0)
            market_analysis = symbol_data.get('market_analysis', {})
            price_levels = symbol_data.get('price_levels', {})
            
            # Collect each recommended strategy
            for strategy_rank in symbol_data.get('top_strategies', []):
                strategy_id = self._collect_single_strategy(
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
            self.logger.error(f"Error collecting symbol {symbol}: {e}")
            return {'success': False, 'error': str(e)}
    
    def _clear_batch_data(self):
        """Clear all batch data collections"""
        for table in self.batch_data:
            self.batch_data[table] = []
    
    def _collect_single_strategy(self, symbol: str, strategy_data: Dict, 
                                spot_price: float, market_analysis: Dict,
                                price_levels: Dict) -> Optional[int]:
        """Collect a single strategy data for batch processing"""
        try:
            # Generate a temporary strategy ID (will be replaced after batch insert)
            temp_strategy_id = f"{symbol}_{strategy_data['name']}_{datetime.now().timestamp()}"
            
            # 1. Collect main strategy record
            strategy_record = self._prepare_strategy_main(
                symbol, strategy_data, spot_price, market_analysis
            )
            if strategy_record:
                strategy_record['temp_id'] = temp_strategy_id
                self.batch_data['strategies'].append(strategy_record)
            else:
                return None  # Skip if strategy already exists or preparation failed
            
            # 2. Collect strategy legs
            self._collect_strategy_legs(temp_strategy_id, strategy_data.get('legs', []), symbol)
            
            # 3. Collect strategy parameters
            self._collect_strategy_parameters(temp_strategy_id, strategy_data)
            
            # 4. Collect Greek exposures
            self._collect_greek_exposures(temp_strategy_id, strategy_data.get('legs', []))
            
            # 5. Collect monitoring levels
            self._collect_monitoring_levels(temp_strategy_id, market_analysis, price_levels)
            
            # 6. Collect risk management
            self._collect_risk_management(temp_strategy_id, strategy_data)
            
            # 7. Collect market analysis
            self._collect_market_analysis(temp_strategy_id, market_analysis)
            
            # 8. Collect IV analysis
            if 'iv_analysis' in market_analysis:
                self._collect_iv_analysis(temp_strategy_id, market_analysis['iv_analysis'])
            
            # 9. Collect price levels
            self._collect_price_levels(temp_strategy_id, price_levels)
            
            # 10. Collect expected moves
            if 'expected_moves' in price_levels:
                self._collect_expected_moves(temp_strategy_id, price_levels)
            
            # 11. Collect exit levels
            if 'exit_conditions' in strategy_data:
                self._collect_exit_levels(temp_strategy_id, strategy_data['exit_conditions'])
            
            # 12. Collect component scores
            if 'component_scores' in strategy_data:
                self._collect_component_scores(temp_strategy_id, strategy_data['component_scores'])
            
            return temp_strategy_id
            
        except Exception as e:
            self.logger.error(f"Error collecting strategy: {e}")
            return None
    
    def _prepare_strategy_main(self, symbol: str, strategy_data: Dict, 
                              spot_price: float, market_analysis: Dict) -> Optional[Dict]:
        """Prepare main strategy record for batch insert"""
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
                return None  # Return None to skip this strategy
            
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
            
            # Get lot size for this symbol for correct net premium calculation
            lot_size = 50  # Default fallback
            try:
                import sys
                import os
                sys.path.append(os.path.dirname(os.path.dirname(__file__)))
                from strategy_creation.lot_size_manager import LotSizeManager
                lot_manager = LotSizeManager()
                lot_size = lot_manager.get_current_lot_size(symbol)
            except Exception as e:
                self.logger.warning(f"Could not get lot size for {symbol} in net premium calculation: {e}")
            
            # Get net premium from legs and calculate spread type (accounting for lot size)
            # Note: For LONG positions, we pay premium (negative cash flow)
            # For SHORT positions, we receive premium (positive cash flow)
            net_premium = sum(
                leg.get('premium', 0) * (1 if leg.get('position') == 'SHORT' else -1) * lot_size
                for leg in strategy_data.get('legs', [])
            )
            
            # Determine spread type based on net premium
            # NET_CREDIT: We receive money (net_premium > 0)
            # NET_DEBIT: We pay money (net_premium < 0)
            if net_premium > 0:
                spread_type = 'NET_CREDIT'
            elif net_premium < 0:
                spread_type = 'NET_DEBIT'
            else:
                spread_type = 'NEUTRAL'
            
            strategy_record = {
                'stock_name': symbol,
                'strategy_name': strategy_data['name'],
                'spread_type': spread_type,
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
                'net_premium': self._clean_value(abs(net_premium)),  # Store absolute value, spread_type indicates direction
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
            
            return strategy_record
            
        except Exception as e:
            self.logger.error(f"Error preparing strategy main: {e}")
            return None
    
    def _collect_strategy_legs(self, temp_strategy_id: str, legs: List[Dict], symbol: str = None) -> None:
        """Collect strategy leg details for batch processing"""
        try:
            # Get lot size for this symbol
            lot_size = 50  # Default fallback
            if symbol:
                try:
                    import sys
                    import os
                    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
                    from strategy_creation.lot_size_manager import LotSizeManager
                    lot_manager = LotSizeManager()
                    lot_size = lot_manager.get_current_lot_size(symbol)
                except Exception as e:
                    self.logger.warning(f"Could not get lot size for {symbol}: {e}")
            
            for leg in legs:
                # Extract expiry date and calculate days to expiry
                expiry_date = leg.get('expiry_date') or leg.get('expiry')
                days_to_expiry = None
                if expiry_date:
                    try:
                        from datetime import datetime
                        if isinstance(expiry_date, str):
                            expiry_dt = datetime.strptime(expiry_date, '%Y-%m-%d')
                            days_to_expiry = (expiry_dt.date() - datetime.now().date()).days
                    except Exception as e:
                        self.logger.warning(f"Could not parse expiry date {expiry_date}: {e}")
                
                leg_record = {
                    'temp_strategy_id': temp_strategy_id,
                    'setup_type': 'BUY' if leg.get('position') == 'LONG' else 'SELL',
                    'instrument': f"{leg.get('option_type', '')}_OPTION",  # Placeholder
                    'lots': 1,  # Default, should be calculated based on capital
                    'quantity': lot_size,  # Use actual lot size from database
                    'strike_price': self._clean_value(leg.get('strike', 0)),
                    'option_type': 'CE' if leg.get('option_type') == 'CALL' else 'PE',
                    'expiry_date': expiry_date,  # Extract from leg data
                    'days_to_expiry': days_to_expiry,  # Calculate from expiry_date
                    'entry_price': self._clean_value(leg.get('premium', 0)),
                    'total_premium': self._clean_value(leg.get('premium', 0) * lot_size),  # Premium * Quantity
                    'delta': self._clean_value(leg.get('delta', 0)),
                    'gamma': self._clean_value(leg.get('gamma', 0)),  # Extract from leg data
                    'theta': self._clean_value(leg.get('theta', 0)),  # Extract from leg data
                    'vega': self._clean_value(leg.get('vega', 0)),    # Extract from leg data
                    'implied_volatility': self._clean_value(leg.get('iv', 0)),  # Extract from leg data
                    'rationale': leg.get('rationale', ''),
                    'entry_min_price': self._clean_value(leg.get('premium', 0) * 0.95),  # 5% buffer
                    'entry_max_price': self._clean_value(leg.get('premium', 0) * 1.05)   # 5% buffer
                }
                self.batch_data['strategy_details'].append(leg_record)
                
        except Exception as e:
            self.logger.error(f"Error collecting strategy legs: {e}")
    
    def _collect_strategy_parameters(self, temp_strategy_id: str, strategy_data: Dict) -> None:
        """Collect strategy parameters for batch processing"""
        try:
            # Safely extract basic values with proper defaults
            max_profit = strategy_data.get('max_profit', 0)
            max_loss = abs(strategy_data.get('max_loss', 0))
            
            # Handle infinite max_profit for risk_reward calculation
            if max_profit == float('inf') or max_profit > 1000000:
                risk_reward_ratio = 999.99  # Cap at reasonable value
            else:
                risk_reward_ratio = max_profit / max_loss if max_loss > 0 else 0
            
            # Safely extract exit conditions
            exit_conditions = strategy_data.get('exit_conditions', {})
            target_price = 0
            stop_loss = 0
            
            try:
                target_price = self._extract_numeric_from_exit_conditions(exit_conditions, 'profit_target')
            except Exception as e:
                self.logger.warning(f"Could not extract target price for {temp_strategy_id}: {e}")
            
            try:
                stop_loss = self._extract_numeric_from_exit_conditions(exit_conditions, 'stop_loss')
            except Exception as e:
                self.logger.warning(f"Could not extract stop loss for {temp_strategy_id}: {e}")
            
            # Calculate entry price from legs
            entry_price = 0
            try:
                legs = strategy_data.get('legs', [])
                for leg in legs:
                    premium = leg.get('premium', 0)
                    position = leg.get('position', 'LONG')
                    # For LONG positions, we pay premium; for SHORT, we receive
                    if position == 'LONG':
                        entry_price += premium
                    else:
                        entry_price -= premium
                entry_price = abs(entry_price)  # Take absolute value for entry cost
            except Exception as e:
                self.logger.warning(f"Could not calculate entry price for {temp_strategy_id}: {e}")
            
            params_record = {
                'temp_strategy_id': temp_strategy_id,
                'max_profit': self._clean_value(max_profit if max_profit != float('inf') else 999999),
                'max_loss': self._clean_value(max_loss),
                'breakeven_point': 0,  # TODO: Calculate breakeven point
                'margin_required': 0,  # TODO: Calculate margin required
                'expiry_date': None,   # TODO: Extract from strategy data
                'risk_reward_ratio': self._clean_value(risk_reward_ratio),
                'probability_profit': self._clean_value(strategy_data.get('probability_profit', 0)),
                'expected_value': 0,   # TODO: Calculate expected value
                'entry_price': self._clean_value(entry_price),
                'target_price': self._clean_value(target_price),
                'stop_loss': self._clean_value(stop_loss)
            }
            
            self.batch_data['strategy_parameters'].append(params_record)
            self.logger.debug(f"Successfully collected parameters for {temp_strategy_id}")
            
        except Exception as e:
            self.logger.error(f"Error collecting strategy parameters for {temp_strategy_id}: {e}")
            # Add minimal record to maintain relationship
            try:
                minimal_record = {
                    'temp_strategy_id': temp_strategy_id,
                    'max_profit': 0,
                    'max_loss': 0,
                    'breakeven_point': 0,
                    'margin_required': 0,
                    'expiry_date': None,
                    'risk_reward_ratio': 0,
                    'probability_profit': 0,
                    'expected_value': 0,
                    'entry_price': 0,
                    'target_price': 0,
                    'stop_loss': 0
                }
                self.batch_data['strategy_parameters'].append(minimal_record)
                self.logger.info(f"Added minimal parameters record for {temp_strategy_id}")
            except Exception as fallback_error:
                self.logger.error(f"Failed to add minimal parameters record for {temp_strategy_id}: {fallback_error}")
    
    def _collect_greek_exposures(self, temp_strategy_id: str, legs: List[Dict]) -> None:
        """Collect net Greek exposures for batch processing"""
        try:
            # Calculate net Greeks from legs
            net_delta = sum(leg.get('delta', 0) for leg in legs)
            net_gamma = sum(leg.get('gamma', 0) for leg in legs)
            net_theta = sum(leg.get('theta', 0) for leg in legs)
            net_vega = sum(leg.get('vega', 0) for leg in legs)
            
            greek_record = {
                'temp_strategy_id': temp_strategy_id,
                'net_delta': self._clean_value(net_delta),
                'net_gamma': self._clean_value(net_gamma),
                'net_theta': self._clean_value(net_theta),
                'net_vega': self._clean_value(net_vega)
            }
            
            self.batch_data['strategy_greek_exposures'].append(greek_record)
            
        except Exception as e:
            self.logger.error(f"Error collecting Greek exposures: {e}")
    
    def _collect_monitoring_levels(self, temp_strategy_id: str, market_analysis: Dict, price_levels: Dict) -> None:
        """Collect monitoring levels for batch processing"""
        try:
            # Extract support/resistance from key_levels
            key_levels = price_levels.get('key_levels', [])
            support_levels = [l['level'] for l in key_levels if l['type'] == 'support']
            resistance_levels = [l['level'] for l in key_levels if l['type'] == 'resistance']
            
            monitoring_record = {
                'temp_strategy_id': temp_strategy_id,
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
            
            self.batch_data['strategy_monitoring'].append(monitoring_record)
            
        except Exception as e:
            self.logger.error(f"Error collecting monitoring levels: {e}")
    
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
    
    def _collect_risk_management(self, temp_strategy_id: str, strategy_data: Dict) -> None:
        """Collect risk management data for batch processing"""
        try:
            exit_conditions = strategy_data.get('exit_conditions', {})
            
            # Safely extract values with proper defaults
            profit_targets = {}
            stop_losses = {} 
            time_exits = {}
            
            try:
                if isinstance(exit_conditions.get('profit_targets'), dict):
                    profit_targets = exit_conditions.get('profit_targets', {})
                    stop_losses = exit_conditions.get('stop_losses', {})
                    time_exits = exit_conditions.get('time_exits', {})
            except Exception as e:
                self.logger.warning(f"Could not parse exit conditions for {temp_strategy_id}: {e}")
            
            # Safely extract numeric values
            max_loss = abs(strategy_data.get('max_loss', 0))
            
            # Safe extraction with fallbacks
            strategy_level_stop = 50  # Default 50%
            try:
                if stop_losses.get('primary', {}).get('loss_pct'):
                    strategy_level_stop = float(stop_losses['primary']['loss_pct'])
            except (ValueError, TypeError, KeyError):
                pass
            
            trailing_stop = 0
            try:
                if profit_targets.get('trailing', {}).get('trail_by'):
                    trail_value = profit_targets['trailing']['trail_by']
                    trailing_stop = self._extract_numeric_from_string(trail_value)
            except (ValueError, TypeError, KeyError):
                pass
            
            profit_target_primary = 0
            try:
                if profit_targets.get('primary', {}).get('target'):
                    target_value = profit_targets['primary']['target']
                    profit_target_primary = self._extract_numeric_from_string(target_value)
            except (ValueError, TypeError, KeyError):
                pass
            
            profit_target_pct = 50  # Default 50%
            try:
                if profit_targets.get('primary', {}).get('target_pct'):
                    pct_value = profit_targets['primary']['target_pct']
                    profit_target_pct = self._extract_numeric_from_string(pct_value)
            except (ValueError, TypeError, KeyError):
                pass
            
            trailing_stop_activation = 0
            try:
                if profit_targets.get('trailing', {}).get('activate_at'):
                    activation_value = profit_targets['trailing']['activate_at']
                    trailing_stop_activation = self._extract_numeric_from_string(activation_value)
            except (ValueError, TypeError, KeyError):
                pass
            
            time_stop_dte = 7  # Default 7 DTE
            try:
                if time_exits.get('primary_dte'):
                    time_stop_dte = int(time_exits['primary_dte'])
            except (ValueError, TypeError, KeyError):
                pass
            
            risk_record = {
                'temp_strategy_id': temp_strategy_id,
                'total_capital': 1000000,  # Default, should be configurable
                'capital_per_trade': 50000,  # Default, should be calculated
                'max_capital_at_risk': self._clean_value(max_loss),
                'strategy_level_stop': self._clean_value(strategy_level_stop),
                'trailing_stop': self._clean_value(trailing_stop),
                'time_based_stop': f"{time_stop_dte} DTE",
                'adjustment_criteria': json.dumps(self._clean_data(exit_conditions.get('adjustment_triggers', {}))),
                'exit_conditions': json.dumps(self._clean_data(exit_conditions)),
                'overall_risk': 'MEDIUM',  # Should be calculated based on max_loss
                # New fields
                'profit_target_primary': self._clean_value(profit_target_primary),
                'profit_target_pct': self._clean_value(profit_target_pct),
                'scaling_exits': json.dumps(self._clean_data(profit_targets.get('scaling', {}))),
                'trailing_stop_activation': self._clean_value(trailing_stop_activation),
                'technical_stops': json.dumps(self._clean_data(stop_losses.get('technical', {}))),
                'time_stop_dte': time_stop_dte,
                'greek_triggers': json.dumps(self._clean_data(exit_conditions.get('greek_triggers', {})))
            }
            
            self.batch_data['strategy_risk_management'].append(risk_record)
            self.logger.debug(f"Successfully collected risk management for {temp_strategy_id}")
            
        except Exception as e:
            self.logger.error(f"Error collecting risk management for {temp_strategy_id}: {e}")
            # Add minimal record to maintain relationship
            try:
                minimal_record = {
                    'temp_strategy_id': temp_strategy_id,
                    'total_capital': 1000000,
                    'capital_per_trade': 50000,
                    'max_capital_at_risk': 0,
                    'strategy_level_stop': 50,
                    'trailing_stop': 0,
                    'time_based_stop': '7 DTE',
                    'adjustment_criteria': '{}',
                    'exit_conditions': '{}',
                    'overall_risk': 'MEDIUM',
                    'profit_target_primary': 0,
                    'profit_target_pct': 50,
                    'scaling_exits': '{}',
                    'trailing_stop_activation': 0,
                    'technical_stops': '{}',
                    'time_stop_dte': 7,
                    'greek_triggers': '{}'
                }
                self.batch_data['strategy_risk_management'].append(minimal_record)
                self.logger.info(f"Added minimal risk management record for {temp_strategy_id}")
            except Exception as fallback_error:
                self.logger.error(f"Failed to add minimal risk management record for {temp_strategy_id}: {fallback_error}")
    
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
    
    def _collect_market_analysis(self, temp_strategy_id: str, market_analysis: Dict) -> None:
        """Collect detailed market analysis for batch processing"""
        try:
            technical = market_analysis.get('details', {}).get('technical', {})
            options = market_analysis.get('details', {}).get('options', {})
            price_action = market_analysis.get('details', {}).get('price_action', {})
            
            market_record = {
                'temp_strategy_id': temp_strategy_id,
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
            
            self.batch_data['strategy_market_analysis'].append(market_record)
            
        except Exception as e:
            self.logger.error(f"Error collecting market analysis: {e}")
    
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
    
    def _collect_iv_analysis(self, temp_strategy_id: str, iv_analysis: Dict) -> None:
        """Collect IV analysis data for batch processing"""
        try:
            iv_record = {
                'temp_strategy_id': temp_strategy_id,
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
            
            self.batch_data['strategy_iv_analysis'].append(iv_record)
            
        except Exception as e:
            self.logger.error(f"Error collecting IV analysis: {e}")
    
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
    
    def _collect_price_levels(self, temp_strategy_id: str, price_levels: Dict) -> None:
        """Collect individual price levels for batch processing"""
        try:
            for level_data in price_levels.get('key_levels', []):
                level_record = {
                    'temp_strategy_id': temp_strategy_id,
                    'level': self._clean_value(level_data.get('level', 0)),
                    'level_type': level_data.get('type', ''),
                    'source': level_data.get('source', ''),
                    'strength': level_data.get('strength', ''),
                    'timeframe': 'mid'  # Default
                }
                self.batch_data['strategy_price_levels'].append(level_record)
                
        except Exception as e:
            self.logger.error(f"Error collecting price levels: {e}")
    
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
    
    def _collect_expected_moves(self, temp_strategy_id: str, price_levels: Dict) -> None:
        """Collect expected move calculations for batch processing"""
        try:
            expected_moves = price_levels.get('expected_moves', {})
            value_area = price_levels.get('value_area', {})
            price_targets = price_levels.get('price_targets', {})
            
            moves_record = {
                'temp_strategy_id': temp_strategy_id,
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
            
            self.batch_data['strategy_expected_moves'].append(moves_record)
            
        except Exception as e:
            self.logger.error(f"Error collecting expected moves: {e}")
    
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
                    target_value = exit_conditions.get('profit_targets', {}).get('primary', {}).get('target', 0)
                    return self._extract_numeric_from_string(target_value)
                elif field == 'stop_loss':
                    loss_value = exit_conditions.get('stop_losses', {}).get('primary', {}).get('loss_amount', 0)
                    return self._extract_numeric_from_string(loss_value)
            
            # Handle simple string structure - try to extract percentage
            value_str = exit_conditions.get(field, '')
            return self._extract_numeric_from_string(value_str)
            
        except Exception:
            return 0
    
    def _extract_numeric_from_string(self, value) -> float:
        """Extract numeric value from string or return numeric value directly"""
        try:
            # If already numeric, return as is
            if isinstance(value, (int, float)):
                return float(value)
            
            # If string, try to extract numeric value
            if isinstance(value, str):
                # Extract numeric value from strings like "50-100% of debit paid"
                import re
                numbers = re.findall(r'(\d+(?:\.\d+)?)', value)
                if numbers:
                    # For ranges like "50-100%", take the average
                    if len(numbers) >= 2:
                        return (float(numbers[0]) + float(numbers[1])) / 2
                    else:
                        return float(numbers[0])
            
            return 0
        except Exception:
            return 0
    
    def _collect_exit_levels(self, temp_strategy_id: str, exit_conditions: Dict) -> None:
        """Collect detailed exit condition levels for batch processing"""
        try:
            levels_created = 0
            
            # Handle nested dictionary structure
            if isinstance(exit_conditions.get('profit_targets'), dict):
                # Profit targets
                profit_targets = exit_conditions.get('profit_targets', {})
                
                # Primary profit target
                if 'primary' in profit_targets and isinstance(profit_targets['primary'], dict):
                    try:
                        target_value = profit_targets['primary'].get('target', 0)
                        numeric_target = self._extract_numeric_from_string(target_value)
                        self.batch_data['strategy_exit_levels'].append({
                            'temp_strategy_id': temp_strategy_id,
                            'exit_type': 'profit_target',
                            'level_name': 'primary',
                            'trigger_value': self._clean_value(numeric_target),
                            'trigger_type': 'price',
                            'action': profit_targets['primary'].get('action', 'Close position'),
                            'reasoning': profit_targets['primary'].get('reasoning', 'Primary profit target')
                        })
                        levels_created += 1
                    except Exception as e:
                        self.logger.warning(f"Could not create primary profit target for {temp_strategy_id}: {e}")
                
                # Scaling exits
                scaling = profit_targets.get('scaling', {})
                if isinstance(scaling, dict):
                    for level_name, level_data in scaling.items():
                        try:
                            if isinstance(level_data, dict):
                                profit_value = level_data.get('profit', 0)
                                action = level_data.get('action', f'Close {level_name}')
                                reasoning = f'Scaling exit at {level_name}'
                            elif isinstance(level_data, str):
                                # Handle string format like "50% profit - close half position"
                                profit_value = self._extract_numeric_from_string(level_data)
                                action = level_data
                                reasoning = f'Scaling exit: {level_data}'
                            else:
                                profit_value = 0
                                action = f'Close {level_name}'
                                reasoning = f'Scaling exit at {level_name}'
                            
                            self.batch_data['strategy_exit_levels'].append({
                                'temp_strategy_id': temp_strategy_id,
                                'exit_type': 'profit_target',
                                'level_name': f'scaling_{level_name}',
                                'trigger_value': self._clean_value(profit_value),
                                'trigger_type': 'price',
                                'action': action,
                                'reasoning': reasoning
                            })
                            levels_created += 1
                        except Exception as e:
                            self.logger.warning(f"Could not create scaling exit {level_name} for {temp_strategy_id}: {e}")
                
                # Stop losses
                stop_losses = exit_conditions.get('stop_losses', {})
                if isinstance(stop_losses, dict) and 'primary' in stop_losses:
                    try:
                        primary_stop = stop_losses['primary']
                        if isinstance(primary_stop, dict):
                            # Try to get loss amount first, then loss_pct
                            loss_value = primary_stop.get('loss_amount', primary_stop.get('loss_pct', 50))
                            trigger_type = 'price' if 'loss_amount' in primary_stop else 'percentage'
                            
                            self.batch_data['strategy_exit_levels'].append({
                                'temp_strategy_id': temp_strategy_id,
                                'exit_type': 'stop_loss',
                                'level_name': 'primary',
                                'trigger_value': self._clean_value(loss_value),
                                'trigger_type': trigger_type,
                                'action': primary_stop.get('action', 'Close entire position'),
                                'reasoning': primary_stop.get('type', 'Primary stop loss')
                            })
                            levels_created += 1
                    except Exception as e:
                        self.logger.warning(f"Could not create primary stop loss for {temp_strategy_id}: {e}")
                
                # Time exits
                time_exits = exit_conditions.get('time_exits', {})
                if isinstance(time_exits, dict) and 'primary_dte' in time_exits:
                    try:
                        dte_value = time_exits['primary_dte']
                        self.batch_data['strategy_exit_levels'].append({
                            'temp_strategy_id': temp_strategy_id,
                            'exit_type': 'time_exit',
                            'level_name': 'primary',
                            'trigger_value': self._clean_value(dte_value),
                            'trigger_type': 'dte',
                            'action': 'Close position',
                            'reasoning': 'Time decay acceleration'
                        })
                        levels_created += 1
                    except Exception as e:
                        self.logger.warning(f"Could not create time exit for {temp_strategy_id}: {e}")
            
            # Handle simple string-based structure or create defaults if nothing was created
            if levels_created == 0:
                self.logger.info(f"No nested exit conditions found for {temp_strategy_id}, creating default exit levels")
                
                # Create basic exit levels based on common patterns
                default_exits = [
                    {
                        'exit_type': 'profit_target',
                        'level_name': 'primary',
                        'trigger_value': 50.0,
                        'trigger_type': 'percentage',
                        'action': 'Close 50%',
                        'reasoning': 'Default profit target'
                    },
                    {
                        'exit_type': 'stop_loss',
                        'level_name': 'primary',
                        'trigger_value': 50.0,
                        'trigger_type': 'percentage', 
                        'action': 'Close entire position',
                        'reasoning': 'Default stop loss'
                    },
                    {
                        'exit_type': 'time_exit',
                        'level_name': 'primary',
                        'trigger_value': 7,
                        'trigger_type': 'dte',
                        'action': 'Close position',
                        'reasoning': 'Time decay acceleration'
                    }
                ]
                
                for exit_level in default_exits:
                    try:
                        exit_record = {
                            'temp_strategy_id': temp_strategy_id,
                            **exit_level
                        }
                        self.batch_data['strategy_exit_levels'].append(exit_record)
                        levels_created += 1
                    except Exception as e:
                        self.logger.warning(f"Could not create default exit level for {temp_strategy_id}: {e}")
            
            self.logger.debug(f"Created {levels_created} exit levels for {temp_strategy_id}")
                
        except Exception as e:
            self.logger.error(f"Error collecting exit levels for {temp_strategy_id}: {e}")
            # Add at least one minimal exit level to maintain data consistency
            try:
                self.batch_data['strategy_exit_levels'].append({
                    'temp_strategy_id': temp_strategy_id,
                    'exit_type': 'stop_loss',
                    'level_name': 'emergency',
                    'trigger_value': 100.0,
                    'trigger_type': 'percentage',
                    'action': 'Close entire position',
                    'reasoning': 'Emergency exit level'
                })
                self.logger.info(f"Added emergency exit level for {temp_strategy_id}")
            except Exception as fallback_error:
                self.logger.error(f"Failed to add emergency exit level for {temp_strategy_id}: {fallback_error}")
    
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
    
    def _collect_component_scores(self, temp_strategy_id: str, component_scores: Dict) -> None:
        """Collect strategy component scores for batch processing"""
        try:
            scores_record = {
                'temp_strategy_id': temp_strategy_id,
                'probability_score': self._clean_value(component_scores.get('probability', 0)),
                'risk_reward_score': self._clean_value(component_scores.get('risk_reward', 0)),
                'direction_score': self._clean_value(component_scores.get('direction', 0)),
                'iv_fit_score': self._clean_value(component_scores.get('iv_fit', 0)),
                'liquidity_score': self._clean_value(component_scores.get('liquidity', 0))
            }
            
            self.batch_data['strategy_component_scores'].append(scores_record)
            
        except Exception as e:
            self.logger.error(f"Error collecting component scores: {e}")
    
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
    
    def _validate_batch_data(self) -> List[str]:
        """Validate batch data before insertion to prevent gaps"""
        validation_errors = []
        
        try:
            # Check for required relationships
            strategy_ids = set(s['temp_strategy_id'] for s in self.batch_data['strategies'])
            
            # Validate each dependent table has matching records
            for table_name in ['strategy_parameters', 'strategy_risk_management', 'strategy_exit_levels']:
                if table_name in self.batch_data:
                    table_ids = set(r['temp_strategy_id'] for r in self.batch_data[table_name])
                    missing_ids = strategy_ids - table_ids
                    if missing_ids:
                        validation_errors.append(f"{table_name}: Missing records for {len(missing_ids)} strategies: {list(missing_ids)[:5]}")
            
            # Check for critical null values
            for strategy in self.batch_data['strategies']:
                if not strategy.get('strategy_name'):
                    validation_errors.append(f"Strategy missing name: {strategy.get('temp_strategy_id')}")
                if strategy.get('probability_of_profit') is None:
                    validation_errors.append(f"Strategy missing probability: {strategy.get('temp_strategy_id')}")
            
            # Check for invalid data types
            for params in self.batch_data.get('strategy_parameters', []):
                if params.get('max_profit') is None or params.get('max_loss') is None:
                    validation_errors.append(f"Parameters missing critical values: {params.get('temp_strategy_id')}")
            
            self.logger.info(f"Batch validation complete: {len(validation_errors)} issues found")
            for error in validation_errors[:5]:  # Log first 5 errors
                self.logger.warning(f"Validation issue: {error}")
                
        except Exception as e:
            validation_errors.append(f"Validation error: {e}")
            
        return validation_errors

    def _execute_batch_inserts(self) -> Dict[str, Any]:
        """Execute all batch inserts in proper sequence"""
        errors = []
        strategy_id_map = {}  # Map temp_id to real strategy_id
        
        try:
            # Validate data before insertion
            validation_errors = self._validate_batch_data()
            if validation_errors:
                self.logger.warning(f"Found {len(validation_errors)} validation issues, proceeding with insertion")
            # 1. Insert strategies first and get real IDs
            if self.batch_data['strategies']:
                # Check for duplicates and filter them out
                unique_strategies = []
                for strategy in self.batch_data['strategies']:
                    # Remove temp_id before checking
                    temp_id = strategy.pop('temp_id')
                    
                    # Check for existing record
                    today = datetime.now().date().isoformat()
                    existing_check = self.client.table('strategies').select('id').eq(
                        'stock_name', strategy['stock_name']
                    ).eq(
                        'strategy_name', strategy['strategy_name']
                    ).gte(
                        'generated_on', f"{today}T00:00:00"
                    ).lte(
                        'generated_on', f"{today}T23:59:59"
                    ).execute()
                    
                    if existing_check.data and len(existing_check.data) > 0:
                        # Map temp_id to existing strategy_id
                        strategy_id_map[temp_id] = existing_check.data[0]['id']
                        self.logger.info(f"Strategy {strategy['strategy_name']} for {strategy['stock_name']} already exists")
                    else:
                        strategy['temp_id'] = temp_id  # Add back for tracking
                        unique_strategies.append(strategy)
                
                # Insert unique strategies in batches
                if unique_strategies:
                    for i in range(0, len(unique_strategies), self.batch_size):
                        batch = unique_strategies[i:i + self.batch_size]
                        # Remove temp_id before insert
                        batch_for_insert = [{k: v for k, v in s.items() if k != 'temp_id'} for s in batch]
                        
                        result = self.client.table('strategies').insert(batch_for_insert).execute()
                        
                        if result.data:
                            # Map temp_ids to real strategy_ids
                            for j, strategy in enumerate(result.data):
                                temp_id = batch[j]['temp_id']
                                strategy_id_map[temp_id] = strategy['id']
                            self.logger.info(f"Inserted {len(result.data)} strategies")
            
            # 2. Update all related records with real strategy_ids
            self._update_batch_data_with_real_ids(strategy_id_map)
            
            # 3. Insert remaining tables in batches
            table_order = [
                'strategy_details',
                'strategy_parameters',
                'strategy_greek_exposures',
                'strategy_monitoring',
                'strategy_risk_management',
                'strategy_market_analysis',
                'strategy_iv_analysis',
                'strategy_price_levels',
                'strategy_expected_moves',
                'strategy_exit_levels',
                'strategy_component_scores'
            ]
            
            for table in table_order:
                if self.batch_data[table]:
                    self._insert_batch_data(table)
            
            return {'success': True, 'errors': errors}
            
        except Exception as e:
            self.logger.error(f"Error executing batch inserts: {e}")
            return {'success': False, 'errors': [str(e)]}
    
    def _update_batch_data_with_real_ids(self, strategy_id_map: Dict[str, int]):
        """Update all batch data with real strategy IDs"""
        # Update all tables that reference strategy_id
        for table in self.batch_data:
            if table != 'strategies':
                for record in self.batch_data[table]:
                    if 'temp_strategy_id' in record:
                        temp_id = record.pop('temp_strategy_id')
                        if temp_id in strategy_id_map:
                            record['strategy_id'] = strategy_id_map[temp_id]
    
    def _insert_batch_data(self, table_name: str):
        """Insert batch data for a specific table"""
        try:
            data = self.batch_data[table_name]
            if not data:
                return
            
            # Insert in batches
            for i in range(0, len(data), self.batch_size):
                batch = data[i:i + self.batch_size]
                result = self.client.table(table_name).insert(batch).execute()
                
                if result.data:
                    self.logger.debug(f"Inserted {len(result.data)} records into {table_name}")
                    
        except Exception as e:
            self.logger.error(f"Error inserting batch data into {table_name}: {e}")