"""
Arbitrage strategy implementation.

This module provides an implementation of an arbitrage strategy for GBPBot.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Tuple, Union

from gbpbot.core.blockchain import BlockchainClient
from gbpbot.core.price_feed import PriceManager
from gbpbot.core.performance_tracker import PerformanceTracker
from gbpbot.core.opportunity_analyzer import OpportunityAnalyzer
from gbpbot.config.trading_config import TradingConfig

logger = logging.getLogger(__name__)

class ArbitrageStrategy:
    """Stratégie d'arbitrage optimisée pour la rapidité et la profitabilité"""
    
    def __init__(self, blockchain: BlockchainClient, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the arbitrage strategy.
        
        Args:
            blockchain: The blockchain client to use for transactions
            config: Configuration dictionary for the strategy
        """
        self.blockchain = blockchain
        self.config = config or {}
        
        # Initialize price feed
        self.price_feed = PriceManager(self.blockchain)
        
        # Performance tracking
        self.performance_tracker = PerformanceTracker()
        
        # Configuration de la stratégie
        self.min_profit_threshold = self.config.get('min_profit_threshold', 0.5)  # 0.5% minimum de profit
        self.max_slippage = self.config.get('max_slippage', 0.3)  # 0.3% de slippage maximum
        self.gas_boost = self.config.get('gas_boost', 1.1)  # 10% boost for gas price
        self.check_interval = self.config.get('check_interval', 5)  # Check every 5 seconds
        
        # Opportunity analyzer
        self.opportunity_analyzer = OpportunityAnalyzer(performance_tracker=self.performance_tracker)
        
        # State
        self.running = False
        self.opportunities_found = 0
        self.trades_executed = 0
        self.total_profit = 0.0
        
        logger.info(f"Arbitrage strategy initialized with profit threshold: {self.min_profit_threshold}%")
    
    async def initialize(self) -> None:
        """Initialize the strategy and its dependencies."""
        logger.info("Initializing arbitrage strategy...")
        # Any async initialization can go here
        logger.info("Arbitrage strategy initialized successfully")
        
    async def analyze_pair(self, token_in: str, token_out: str, amount_in: int, symbol: str) -> Optional[Dict]:
        """
        Analyze a token pair for arbitrage opportunities.
        
        Args:
            token_in: Address of the input token
            token_out: Address of the output token
            amount_in: Amount of input token to use
            symbol: Trading symbol (e.g., "ETH/USDT")
            
        Returns:
            Dictionary containing opportunity details or None if no opportunity found
        """
        logger.info(f"Analyzing pair {symbol} for arbitrage opportunities...")
        
        try:
            # Get prices from different exchanges
            prices = await self._get_prices_from_exchanges(token_in, token_out, amount_in, symbol)
            
            if not prices or len(prices) < 2:
                logger.debug(f"Not enough price data for {symbol}")
                return None
                
            # Find the best buy and sell prices
            buy_price = min(prices, key=lambda x: x['price'])
            sell_price = max(prices, key=lambda x: x['price'])
            
            price_diff = sell_price['price'] - buy_price['price']
            price_diff_percent = (price_diff / buy_price['price']) * 100
            
            logger.debug(f"Price difference for {symbol}: {price_diff_percent:.2f}%")
            
            if price_diff_percent <= self.min_profit_threshold:
                logger.debug(f"Profit too low for {symbol}: {price_diff_percent:.2f}%")
                return None
                
            # Calculate potential profit
            amount_out = amount_in * sell_price['price'] / buy_price['price']
            profit = amount_out - amount_in
            profit_percent = (profit / amount_in) * 100
            
            # Estimate gas costs
            gas_cost = await self._estimate_gas_cost({
                'buy_exchange': buy_price['exchange'],
                'sell_exchange': sell_price['exchange']
            }, token_in, token_out, amount_in)
            
            # Convert gas cost to token amount
            gas_cost_in_tokens = gas_cost / buy_price['price']
            
            # Calculate net profit
            net_profit = profit - gas_cost_in_tokens
            net_profit_percent = (net_profit / amount_in) * 100
            
            if net_profit_percent <= self.min_profit_threshold:
                logger.debug(f"Net profit too low for {symbol}: {net_profit_percent:.2f}%")
                return None
                
            # Create opportunity object
            opportunity = {
                'token_in': token_in,
                'token_out': token_out,
                'symbol': symbol,
                'buy_exchange': buy_price['exchange'],
                'sell_exchange': sell_price['exchange'],
                'buy_price': buy_price['price'],
                'sell_price': sell_price['price'],
                'amount_in': amount_in,
                'expected_amount_out': amount_out,
                'profit': profit,
                'profit_percent': profit_percent,
                'gas_cost': gas_cost,
                'gas_cost_in_tokens': gas_cost_in_tokens,
                'net_profit': net_profit,
                'net_profit_percent': net_profit_percent,
                'timestamp': time.time()
            }
            
            logger.info(f"Found arbitrage opportunity for {symbol}: {net_profit_percent:.2f}% net profit")
            return opportunity
            
        except Exception as e:
            logger.error(f"Error analyzing pair {symbol}: {str(e)}")
            return None
    
    async def execute_trade(self, opportunity: Dict) -> bool:
        """
        Execute an arbitrage trade based on the identified opportunity.
        
        Args:
            opportunity: Dictionary containing opportunity details
            
        Returns:
            True if the trade was successful, False otherwise
        """
        token_in = opportunity['token_in']
        token_out = opportunity['token_out']
        symbol = opportunity['symbol']
        amount_in = opportunity['amount_in']
        
        logger.info(f"Executing arbitrage trade for {symbol}...")
        
        try:
            # Prepare buy transaction
            buy_tx_params = await self._prepare_dex_swap(
                opportunity['buy_exchange'],
                token_in,
                token_out,
                amount_in,
                int(opportunity['expected_amount_out'] * (1 - self.max_slippage / 100)),
                'high'  # Use high priority for faster execution
            )
            
            if not buy_tx_params:
                logger.error(f"Failed to prepare buy transaction for {symbol}")
                return False
                
            # Execute buy transaction
            buy_result = await self.blockchain.execute_transaction(buy_tx_params)
            
            if not buy_result or not buy_result.get('tx_hash'):
                logger.error(f"Failed to send buy transaction for {symbol}")
                return False
                
            buy_tx_hash = buy_result['tx_hash']
            logger.info(f"Buy transaction sent: {buy_tx_hash}")
            
            # Wait for buy transaction to be confirmed
            buy_receipt = await self.blockchain.wait_for_transaction(buy_tx_hash, 60)
            
            if not buy_receipt or buy_receipt.get('status') != 1:
                logger.error(f"Buy transaction failed for {symbol}")
                return False
                
            logger.info(f"Buy transaction confirmed for {symbol}")
            
            # Get actual amount received
            actual_amount_out = await self._get_actual_amount_out(buy_receipt, token_out)
            
            # Prepare sell transaction
            sell_tx_params = await self._prepare_dex_swap(
                opportunity['sell_exchange'],
                token_out,
                token_in,
                actual_amount_out,
                int(amount_in * (1 + self.min_profit_threshold / 100)),  # Ensure minimum profit
                'high'  # Use high priority for faster execution
            )
            
            if not sell_tx_params:
                logger.error(f"Failed to prepare sell transaction for {symbol}")
                return False
                
            # Execute sell transaction
            sell_result = await self.blockchain.execute_transaction(sell_tx_params)
            
            if not sell_result or not sell_result.get('tx_hash'):
                logger.error(f"Failed to send sell transaction for {symbol}")
                return False
                
            sell_tx_hash = sell_result['tx_hash']
            logger.info(f"Sell transaction sent: {sell_tx_hash}")
            
            # Wait for sell transaction to be confirmed
            sell_receipt = await self.blockchain.wait_for_transaction(sell_tx_hash, 60)
            
            if not sell_receipt or sell_receipt.get('status') != 1:
                logger.error(f"Sell transaction failed for {symbol}")
                return False
                
            logger.info(f"Sell transaction confirmed for {symbol}")
            
            # Get actual amount received back
            actual_amount_in = await self._get_actual_amount_out(sell_receipt, token_in)
            
            # Calculate actual profit
            actual_profit = actual_amount_in - amount_in
            actual_profit_percent = (actual_profit / amount_in) * 100
            
            # Record trade
            self._record_trade(opportunity, buy_tx_hash, sell_tx_hash)
            
            # Update stats
            self.trades_executed += 1
            self.total_profit += actual_profit
            
            logger.info(f"Arbitrage trade completed for {symbol} with {actual_profit_percent:.2f}% profit")
            return True
            
        except Exception as e:
            logger.error(f"Error executing trade for {symbol}: {str(e)}")
            return False
    
    async def _get_actual_amount_out(self, receipt: Dict, token: str) -> int:
        """Get the actual amount of tokens received from a transaction."""
        # This is a simplified implementation
        # In a real implementation, you would parse the transaction logs
        # to find the actual amount of tokens transferred
        return int(receipt.get('logs', [{}])[0].get('data', '0x0'), 16)
    
    async def _estimate_gas_cost(self, opportunity: Dict, token_in: str, token_out: str, amount_in: int) -> int:
        """Estimate the gas cost for an arbitrage trade."""
        # This is a simplified implementation
        # In a real implementation, you would estimate the gas cost based on
        # the current gas price and the gas limit for the transactions
        return 100000  # Simplified gas cost estimate
    
    async def _prepare_dex_swap(self, dex: str, token_in: str, token_out: str, amount_in: int, min_amount_out: int, priority: str = "normal") -> Optional[Dict]:
        """Prepare a DEX swap transaction."""
        # This is a simplified implementation
        # In a real implementation, you would prepare the transaction parameters
        # for the specific DEX and tokens
        return {
            'to': '0x1234567890123456789012345678901234567890',  # Example DEX router address
            'data': '0x',  # Example transaction data
            'value': 0,  # Example value (for ETH transactions)
            'gas': 200000,  # Example gas limit
        }
    
    async def _get_prices_from_exchanges(self, token_in_address: str, token_out_address: str, amount_in: int, symbol: str) -> List[Dict]:
        """Get prices from different exchanges."""
        # This is a simplified implementation
        # In a real implementation, you would query different DEXes for prices
        return [
            {'exchange': 'uniswap', 'price': 100.0},
            {'exchange': 'sushiswap', 'price': 101.0},
            {'exchange': 'pancakeswap', 'price': 99.5},
        ]
    
    def _record_trade(self, opportunity: Dict, buy_tx: str, sell_tx: str) -> None:
        """Record a completed trade."""
        # This is a simplified implementation
        # In a real implementation, you would record the trade details
        # for performance tracking and analysis
        # Just log the trade for now since we don't know the exact interface
        logger.info(f"Trade recorded: {opportunity['symbol']} with {opportunity['net_profit_percent']:.2f}% profit")
        # Store trade in memory
        trade_record = {
            'timestamp': time.time(),
            'symbol': opportunity['symbol'],
            'profit_percent': opportunity['net_profit_percent'],
            'buy_tx': buy_tx,
            'sell_tx': sell_tx
        }
        # We could store this in a database or file in a real implementation
    
    async def find_opportunities(self, token_pairs: List[Dict]) -> List[Dict]:
        """
        Find arbitrage opportunities for a list of token pairs.
        
        Args:
            token_pairs: List of dictionaries containing token pair information
            
        Returns:
            List of dictionaries containing opportunity details
        """
        logger.info(f"Searching for arbitrage opportunities in {len(token_pairs)} token pairs...")
        
        opportunities = []
        
        for pair in token_pairs:
            token_in = pair['token_in']
            token_out = pair['token_out']
            amount_in = pair.get('amount_in', 1000000)  # Default amount
            symbol = pair.get('symbol', f"{token_in[-4:]}/{token_out[-4:]}")
            
            opportunity = await self.analyze_pair(token_in, token_out, amount_in, symbol)
            
            if opportunity:
                opportunities.append(opportunity)
        
        # Sort opportunities by profit
        opportunities.sort(key=lambda x: x['net_profit_percent'], reverse=True)
        
        logger.info(f"Found {len(opportunities)} arbitrage opportunities")
        return opportunities
    
    async def run(self, token_pairs: List[Dict]) -> None:
        """
        Run the arbitrage strategy continuously.
        
        Args:
            token_pairs: List of dictionaries containing token pair information
        """
        logger.info("Starting arbitrage strategy...")
        self.running = True
        
        while self.running:
            try:
                # Find opportunities
                opportunities = await self.find_opportunities(token_pairs)
                
                if opportunities:
                    self.opportunities_found += len(opportunities)
                    
                    # Execute the best opportunity
                    best_opportunity = opportunities[0]
                    logger.info(f"Executing best opportunity: {best_opportunity['symbol']} with {best_opportunity['net_profit_percent']:.2f}% profit")
                    
                    success = await self.execute_trade(best_opportunity)
                    
                    if success:
                        logger.info(f"Successfully executed arbitrage trade for {best_opportunity['symbol']}")
                    else:
                        logger.warning(f"Failed to execute arbitrage trade for {best_opportunity['symbol']}")
                
                # Wait for next check
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Error in arbitrage strategy: {str(e)}")
                await asyncio.sleep(self.check_interval)
    
    async def stop(self) -> None:
        """Stop the arbitrage strategy."""
        logger.info("Stopping arbitrage strategy...")
        self.running = False
    
    def get_performance_stats(self) -> Dict:
        """Get performance statistics for the strategy."""
        return {
            'opportunities_found': self.opportunities_found,
            'trades_executed': self.trades_executed,
            'success_rate': (self.trades_executed / self.opportunities_found * 100) if self.opportunities_found > 0 else 0,
            'total_profit': self.total_profit,
            'average_profit': (self.total_profit / self.trades_executed) if self.trades_executed > 0 else 0
        } 