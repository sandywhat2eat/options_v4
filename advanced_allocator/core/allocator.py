"""
Advanced Options Allocator
Main orchestrator that combines all components for portfolio allocation
"""

import logging
from typing import Dict, List, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import json

from .market_direction import MarketDirectionAnalyzer
from .industry_allocator import IndustryAllocator
from .market_cap_allocator import MarketCapAllocator
from .stock_selector import StockSelector
from .strategy_selector import StrategySelector
from .position_sizer import PositionSizer

logger = logging.getLogger(__name__)


@dataclass
class AllocationResult:
    """Complete allocation result"""
    timestamp: datetime
    market_analysis: Dict
    allocations: List[Dict]
    summary: Dict
    parameters: Dict


class AdvancedOptionsAllocator:
    """Main allocator combining all components"""
    
    def __init__(self, supabase_client, total_capital: float = 10000000):  # 1 Cr default
        self.supabase = supabase_client
        self.total_capital = total_capital
        
        # Initialize components
        self.market_analyzer = MarketDirectionAnalyzer(supabase_client)
        self.industry_allocator = IndustryAllocator(supabase_client)
        self.market_cap_allocator = MarketCapAllocator()
        self.stock_selector = StockSelector(supabase_client)
        self.strategy_selector = StrategySelector(supabase_client)
        self.position_sizer = PositionSizer()
        
    def allocate_portfolio(self, vix_level: float = 20.0) -> AllocationResult:
        """Main allocation method"""
        try:
            logger.info(f"Starting portfolio allocation with capital: {self.total_capital}")
            
            # Step 1: Analyze market direction
            market_direction = self.market_analyzer.get_market_direction()
            long_pct, short_pct = self.market_analyzer.get_long_short_ratio()
            
            # Print detailed market analysis
            print("\n" + "="*60)
            print("MARKET DIRECTION ANALYSIS")
            print("="*60)
            print(f"Technical Analysis Score: {market_direction.technical_score:.3f} (Weight: 40%)")
            print(f"Options Flow Score: {market_direction.options_flow_score:.3f} (Weight: 35%)")
            print(f"Price Action Score: {market_direction.price_action_score:.3f} (Weight: 25%)")
            print(f"Composite Score: {market_direction.composite_score:.3f}")
            print(f"Market State: {market_direction.market_state.upper()}")
            print(f"Confidence: {market_direction.confidence:.1%}")
            print(f"Long/Short Allocation: {long_pct}%/{short_pct}%")
            print("="*60)
            
            logger.info(f"Market state: {market_direction.market_state}, "
                       f"Long/Short: {long_pct}/{short_pct}")
            
            # Step 2: Get industry allocations
            long_industries, short_industries = self.industry_allocator.get_industry_allocations()
            
            # Step 3: Allocate capital to market caps based on market condition
            market_cap_allocation = self.market_cap_allocator.allocate_by_market_condition(
                self.total_capital, market_direction.market_state
            )
            
            # Adjust for VIX
            market_cap_allocation = self.market_cap_allocator.adjust_for_volatility(
                market_cap_allocation, vix_level
            )
            
            # Step 4: Allocate to industries considering long/short ratio
            industry_capital = self.industry_allocator.allocate_capital_to_industries(
                self.total_capital, long_pct
            )
            
            # Step 5: Get all tradeable symbols with info
            symbols_info = self.industry_allocator.get_tradeable_symbols()
            
            # Step 6: Build positions
            positions = self._build_positions(
                market_cap_allocation,
                industry_capital,
                symbols_info,
                long_industries + short_industries
            )
            
            # Step 7: Create result
            result = self._create_allocation_result(
                market_direction,
                positions,
                {
                    'total_capital': self.total_capital,
                    'vix_level': vix_level,
                    'long_percentage': long_pct,
                    'short_percentage': short_pct
                }
            )
            
            logger.info(f"Allocation complete: {len(positions)} positions")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in portfolio allocation: {e}")
            raise
    
    def _build_positions(self, market_cap_allocation: Dict[str, float],
                        industry_capital: Dict[str, float],
                        symbols_info: Dict[str, Dict],
                        all_industries: List) -> List[Dict]:
        """Build actual positions"""
        positions = []
        
        try:
            # Get stocks data for categorization
            stocks_data = self._get_all_stocks_data(list(symbols_info.keys()))
            
            # Categorize stocks by market cap
            categorized_stocks = self.market_cap_allocator.categorize_stocks(stocks_data)
            
            # Process each market cap category
            for market_cap, cap_allocation in market_cap_allocation.items():
                if cap_allocation <= 0:
                    continue
                    
                # Get stocks in this market cap
                symbols_in_cap = categorized_stocks.get(market_cap, [])
                
                if not symbols_in_cap:
                    logger.warning(f"No symbols found for {market_cap}")
                    continue
                
                # Get allocation constraints
                constraints = self.market_cap_allocator.get_allocation_constraints(market_cap)
                max_positions = constraints['max_positions']
                
                # Calculate per-position allocation
                positions_in_cap = min(len(symbols_in_cap), max_positions)
                if positions_in_cap > 0:
                    per_position_allocation = cap_allocation / positions_in_cap
                else:
                    continue
                
                # Select stocks within this market cap using pre-loaded strategy data
                selected_stocks = []
                
                for symbol in symbols_in_cap:
                    symbol_data = symbols_info.get(symbol, {})
                    
                    # Skip if no strategy data (shouldn't happen with our new logic)
                    if not symbol_data.get('total_score'):
                        continue
                    
                    # Calculate composite score for ranking
                    composite_score = (
                        0.5 * symbol_data['total_score'] +
                        0.3 * symbol_data['probability_of_profit'] +
                        0.2 * min(symbol_data['risk_reward_ratio'] / 3.0, 1.0)
                    )
                    
                    selected_stocks.append({
                        'symbol': symbol,
                        'composite_score': composite_score,
                        'total_score': symbol_data['total_score'],
                        'probability_of_profit': symbol_data['probability_of_profit'],
                        'risk_reward_ratio': symbol_data['risk_reward_ratio'],
                        'strategy_name': symbol_data['strategy_name'],
                        'industry': symbol_data['industry'],
                        'position_type': symbol_data['position_type']
                    })
                
                # Sort by composite score and limit selections
                selected_stocks.sort(key=lambda x: x['composite_score'], reverse=True)
                selected_stocks = selected_stocks[:max_positions]
                
                # Create positions for selected stocks
                for stock in selected_stocks:
                    # Get industry allocation
                    industry_key = f"{stock['industry']}_{stock['position_type']}"
                    industry_alloc = industry_capital.get(industry_key, 0)
                    
                    if industry_alloc <= 0:
                        continue
                    
                    # Calculate actual allocation (minimum of market cap and industry allocation)
                    stock_allocation = min(per_position_allocation, industry_alloc * 0.2)  # Max 20% per stock in industry
                    
                    # Calculate simple position size based on capital allocation
                    position_size = self._calculate_simple_position_size(
                        stock_allocation,
                        stock['probability_of_profit'],
                        stock['risk_reward_ratio']
                    )
                    
                    # Create position entry using simplified data
                    position = {
                        'symbol': stock['symbol'],
                        'strategy_name': stock['strategy_name'],
                        'strategy_id': f"{stock['symbol']}_strategy",
                        'position_type': stock['position_type'],
                        'industry': stock['industry'],
                        'industry_rating': symbols_info[stock['symbol']]['rating'],
                        'market_cap': market_cap,
                        'allocated_capital': stock_allocation,
                        'number_of_lots': position_size['number_of_lots'],
                        'lot_size': position_size['lot_size'],
                        'premium_at_risk': position_size['premium_at_risk'],
                        'position_value': position_size['position_value'],
                        'risk_percentage': position_size['risk_percentage'],
                        'kelly_fraction': position_size['kelly_fraction'],
                        'probability_of_profit': stock['probability_of_profit'],
                        'conviction_level': 'high' if stock['total_score'] > 0.7 else 'medium',
                        'total_score': stock['total_score'],
                        'max_loss': position_size['premium_at_risk'],
                        'max_profit': position_size['premium_at_risk'] * stock['risk_reward_ratio'],
                        'risk_reward_ratio': stock['risk_reward_ratio']
                    }
                    
                    positions.append(position)
            
            return positions
            
        except Exception as e:
            logger.error(f"Error building positions: {e}")
            return []
    
    def _calculate_simple_position_size(self, allocated_capital: float, 
                                      probability_of_profit: float, 
                                      risk_reward_ratio: float) -> Dict:
        """Calculate simplified position size"""
        try:
            # Simplified position sizing
            lot_size = 50  # Standard lot size
            premium_per_lot = 5000  # Estimated premium per lot in Rs
            
            # Calculate number of lots based on allocated capital
            max_lots_by_capital = int(allocated_capital // premium_per_lot)
            
            # Apply kelly criterion for risk management
            kelly_fraction = min(probability_of_profit * risk_reward_ratio - (1 - probability_of_profit), 0.25)
            kelly_fraction = max(kelly_fraction, 0.01)  # Minimum 1%
            
            # Final number of lots
            number_of_lots = max(1, int(max_lots_by_capital * kelly_fraction))
            
            # Calculate position metrics
            premium_at_risk = number_of_lots * premium_per_lot
            position_value = number_of_lots * lot_size * 1000  # Estimated position value
            risk_percentage = (premium_at_risk / allocated_capital) * 100
            
            return {
                'number_of_lots': number_of_lots,
                'lot_size': lot_size,
                'premium_at_risk': premium_at_risk,
                'position_value': position_value,
                'risk_percentage': min(risk_percentage, 5.0),  # Cap at 5%
                'kelly_fraction': kelly_fraction
            }
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return {
                'number_of_lots': 1,
                'lot_size': 50,
                'premium_at_risk': 5000,
                'position_value': 50000,
                'risk_percentage': 2.0,
                'kelly_fraction': 0.02
            }
    
    def _get_all_stocks_data(self, symbols: List[str]) -> List[Dict]:
        """Get stocks data for categorization"""
        try:
            if not self.supabase:
                logger.error("CRITICAL: Database client is required for real trading system")
                raise ValueError("Database client is required for real trading system")
            
            # Query in batches
            all_data = []
            batch_size = 100
            
            for i in range(0, len(symbols), batch_size):
                batch = symbols[i:i + batch_size]
                response = self.supabase.table('stock_rankings').select(
                    'symbol, market_cap_category'
                ).in_('symbol', batch).execute()
                
                if response.data:
                    all_data.extend(response.data)
            
            return all_data
            
        except Exception as e:
            logger.error(f"Error getting stocks data: {e}")
            return []
    
    def _create_allocation_result(self, market_direction, 
                                positions: List[Dict], 
                                parameters: Dict) -> AllocationResult:
        """Create allocation result object"""
        # Calculate summary statistics
        summary = {
            'total_positions': len(positions),
            'long_positions': len([p for p in positions if p['position_type'] == 'LONG']),
            'short_positions': len([p for p in positions if p['position_type'] == 'SHORT']),
            'total_premium_at_risk': sum(p['premium_at_risk'] for p in positions),
            'total_position_value': sum(p['position_value'] for p in positions),
            'average_probability': np.mean([p['probability_of_profit'] for p in positions]) if positions else 0,
            'market_cap_distribution': {},
            'strategy_distribution': {},
            'industry_distribution': {}
        }
        
        # Calculate distributions
        for position in positions:
            # Market cap distribution
            cap = position['market_cap']
            if cap not in summary['market_cap_distribution']:
                summary['market_cap_distribution'][cap] = {'count': 0, 'value': 0}
            summary['market_cap_distribution'][cap]['count'] += 1
            summary['market_cap_distribution'][cap]['value'] += position['position_value']
            
            # Strategy distribution
            strategy = position['strategy_name']
            if strategy not in summary['strategy_distribution']:
                summary['strategy_distribution'][strategy] = {'count': 0, 'value': 0}
            summary['strategy_distribution'][strategy]['count'] += 1
            summary['strategy_distribution'][strategy]['value'] += position['position_value']
            
            # Industry distribution
            industry = position['industry']
            if industry not in summary['industry_distribution']:
                summary['industry_distribution'][industry] = {'count': 0, 'value': 0}
            summary['industry_distribution'][industry]['count'] += 1
            summary['industry_distribution'][industry]['value'] += position['position_value']
        
        return AllocationResult(
            timestamp=datetime.now(),
            market_analysis={
                'direction_score': market_direction.composite_score,
                'market_state': market_direction.market_state,
                'confidence': market_direction.confidence,
                'technical_score': market_direction.technical_score,
                'options_flow_score': market_direction.options_flow_score,
                'price_action_score': market_direction.price_action_score
            },
            allocations=positions,
            summary=summary,
            parameters=parameters
        )
    
    def save_allocation_result(self, result: AllocationResult, filepath: str):
        """Save allocation result to file"""
        try:
            # Convert to dict for JSON serialization
            result_dict = {
                'timestamp': result.timestamp.isoformat(),
                'market_analysis': result.market_analysis,
                'allocations': result.allocations,
                'summary': result.summary,
                'parameters': result.parameters
            }
            
            with open(filepath, 'w') as f:
                json.dump(result_dict, f, indent=2)
                
            logger.info(f"Saved allocation result to {filepath}")
            
        except Exception as e:
            logger.error(f"Error saving result: {e}")


# Add numpy import at the top
import numpy as np