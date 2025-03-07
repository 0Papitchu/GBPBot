#!/usr/bin/env python
"""
CEX-DEX Arbitrage Strategy for GBPBot.

This module provides a strategy for arbitrage between centralized exchanges (CEX)
and decentralized exchanges (DEX). It monitors price differences and executes
trades to profit from these differences.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Tuple, Union, Set
from decimal import Decimal

from gbpbot.core.blockchain import BlockchainClient
from gbpbot.clients.base_cex_client import BaseCEXClient
from gbpbot.clients.cex_client_factory import CEXClientFactory
from gbpbot.utils.config import get_config
from gbpbot.utils.exceptions import ArbitrageError, TransactionError


class CEXDEXArbitrageStrategy:
    """
    Strategy for arbitrage between CEX and DEX.
    
    This strategy monitors price differences between centralized exchanges (CEX)
    and decentralized exchanges (DEX) and executes trades to profit from these
    differences.
    """
    
    def __init__(self, config: Dict[str, Any], blockchain_clients: Dict[str, BlockchainClient],
                cex_clients: Dict[str, BaseCEXClient]):
        """
        Initialize the CEX-DEX arbitrage strategy.
        
        Args:
            config: Configuration dictionary
            blockchain_clients: Dictionary of blockchain clients
            cex_clients: Dictionary of CEX clients
        """
        self.config = config
        self.blockchain_clients = blockchain_clients
        self.cex_clients = cex_clients
        self.logger = logging.getLogger("gbpbot.strategies.cex_dex_arbitrage")
        
        # Get configuration parameters
        self.min_profit_threshold = float(config.get("MIN_PROFIT_THRESHOLD", 0.5)) / 100  # Convert to decimal
        self.max_arbitrage_amount_usd = float(config.get("MAX_ARBITRAGE_AMOUNT_USD", 1000))
        self.arbitrage_interval = int(config.get("ARBITRAGE_INTERVAL", 5))
        self.flash_arbitrage_enabled = config.get("FLASH_ARBITRAGE_ENABLED", "true").lower() == "true"
        
        # Initialize state
        self.running = False
        self.active_arbitrages = set()
        self.monitored_pairs = set()
        self.price_cache = {}
        self.price_cache_time = {}
        self.price_cache_expiry = 10  # Cache expiry in seconds
        
        # Initialize statistics
        self.stats = {
            "opportunities_found": 0,
            "arbitrages_executed": 0,
            "total_profit_usd": 0,
            "failed_arbitrages": 0
        }
        
        self.logger.info("CEX-DEX arbitrage strategy initialized")
    
    async def start(self):
        """Start the arbitrage strategy."""
        if self.running:
            self.logger.warning("Arbitrage strategy already running")
            return
        
        self.running = True
        self.logger.info("Starting CEX-DEX arbitrage strategy")
        
        # Start monitoring loop
        asyncio.create_task(self._monitoring_loop())
    
    async def stop(self):
        """Stop the arbitrage strategy."""
        if not self.running:
            self.logger.warning("Arbitrage strategy not running")
            return
        
        self.running = False
        self.logger.info("Stopping CEX-DEX arbitrage strategy")
        
        # Wait for active arbitrages to complete
        if self.active_arbitrages:
            self.logger.info(f"Waiting for {len(self.active_arbitrages)} active arbitrages to complete")
            await asyncio.sleep(5)  # Give some time for arbitrages to complete
    
    async def add_monitored_pair(self, token_symbol: str, blockchain: str, cex: str):
        """
        Add a trading pair to monitor for arbitrage opportunities.
        
        Args:
            token_symbol: Symbol of the token (e.g., "BTC/USDT")
            blockchain: Blockchain to monitor
            cex: Centralized exchange to monitor
        """
        pair_key = f"{token_symbol}:{blockchain}:{cex}"
        
        if pair_key in self.monitored_pairs:
            self.logger.warning(f"Pair {pair_key} already monitored")
            return
        
        self.monitored_pairs.add(pair_key)
        self.logger.info(f"Added pair {pair_key} to monitored pairs")
    
    async def remove_monitored_pair(self, token_symbol: str, blockchain: str, cex: str):
        """
        Remove a trading pair from monitoring.
        
        Args:
            token_symbol: Symbol of the token (e.g., "BTC/USDT")
            blockchain: Blockchain to monitor
            cex: Centralized exchange to monitor
        """
        pair_key = f"{token_symbol}:{blockchain}:{cex}"
        
        if pair_key not in self.monitored_pairs:
            self.logger.warning(f"Pair {pair_key} not monitored")
            return
        
        self.monitored_pairs.remove(pair_key)
        self.logger.info(f"Removed pair {pair_key} from monitored pairs")
    
    async def get_monitored_pairs(self) -> List[Dict[str, str]]:
        """
        Get list of monitored pairs.
        
        Returns:
            List of dictionaries containing pair information
        """
        result = []
        
        for pair_key in self.monitored_pairs:
            token_symbol, blockchain, cex = pair_key.split(":")
            result.append({
                "token_symbol": token_symbol,
                "blockchain": blockchain,
                "cex": cex
            })
        
        return result
    
    async def get_statistics(self) -> Dict[str, Any]:
        """
        Get arbitrage statistics.
        
        Returns:
            Dictionary containing arbitrage statistics
        """
        return self.stats
    
    async def _monitoring_loop(self):
        """Main monitoring loop for arbitrage opportunities."""
        self.logger.info("Starting monitoring loop")
        
        while self.running:
            try:
                # Check each monitored pair for arbitrage opportunities
                for pair_key in self.monitored_pairs:
                    token_symbol, blockchain, cex = pair_key.split(":")
                    
                    # Skip if blockchain client or CEX client not available
                    if blockchain not in self.blockchain_clients:
                        self.logger.warning(f"Blockchain client {blockchain} not available")
                        continue
                    
                    if cex not in self.cex_clients:
                        self.logger.warning(f"CEX client {cex} not available")
                        continue
                    
                    # Check for arbitrage opportunity
                    try:
                        opportunity = await self._check_arbitrage_opportunity(
                            token_symbol, blockchain, cex
                        )
                        
                        if opportunity:
                            self.stats["opportunities_found"] += 1
                            self.logger.info(f"Found arbitrage opportunity: {opportunity}")
                            
                            # Execute arbitrage if profit is above threshold
                            if opportunity["profit_percent"] >= self.min_profit_threshold * 100:
                                asyncio.create_task(self._execute_arbitrage(opportunity))
                    
                    except Exception as e:
                        self.logger.error(f"Error checking arbitrage opportunity for {pair_key}: {e}")
                
                # Sleep for the configured interval
                await asyncio.sleep(self.arbitrage_interval)
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(10)  # Sleep longer on error
    
    async def _check_arbitrage_opportunity(self, token_symbol: str, blockchain: str, cex: str) -> Optional[Dict[str, Any]]:
        """
        Check for arbitrage opportunity between CEX and DEX.
        
        Args:
            token_symbol: Symbol of the token (e.g., "BTC/USDT")
            blockchain: Blockchain to check
            cex: Centralized exchange to check
            
        Returns:
            Dictionary containing arbitrage opportunity information or None if no opportunity
        """
        # Get blockchain client and CEX client
        blockchain_client = self.blockchain_clients[blockchain]
        cex_client = self.cex_clients[cex]
        
        # Parse token symbol
        token_parts = token_symbol.split("/")
        if len(token_parts) != 2:
            raise ArbitrageError(f"Invalid token symbol format: {token_symbol}")
        
        base_token, quote_token = token_parts
        
        # Get token addresses for blockchain
        # This is a simplified implementation - in a real system, you would have a token registry
        token_addresses = {
            "BTC": "0x...",  # Example address
            "ETH": "0x...",  # Example address
            "USDT": "0x...",  # Example address
            "USDC": "0x..."   # Example address
        }
        
        if base_token not in token_addresses:
            raise ArbitrageError(f"Token address not found for {base_token}")
        
        if quote_token not in token_addresses:
            raise ArbitrageError(f"Token address not found for {quote_token}")
        
        base_token_address = token_addresses[base_token]
        quote_token_address = token_addresses[quote_token]
        
        # Get prices from CEX and DEX
        try:
            # Get CEX price
            cex_ticker = await cex_client.get_ticker(token_symbol)
            cex_price = float(cex_ticker["last"])
            
            # Get DEX price
            dex_price = await blockchain_client.get_token_price(
                base_token_address, quote_token_address
            )
            
            # Calculate price difference
            price_diff = abs(cex_price - dex_price)
            price_diff_percent = (price_diff / min(cex_price, dex_price)) * 100
            
            # Determine direction (buy on CEX, sell on DEX or vice versa)
            if cex_price < dex_price:
                direction = "cex_to_dex"
                buy_price = cex_price
                sell_price = dex_price
                buy_exchange = cex
                sell_exchange = blockchain
            else:
                direction = "dex_to_cex"
                buy_price = dex_price
                sell_price = cex_price
                buy_exchange = blockchain
                sell_exchange = cex
            
            # Calculate potential profit
            # In a real system, you would account for fees, slippage, etc.
            profit_percent = (sell_price / buy_price - 1) * 100
            
            # Create opportunity object
            opportunity = {
                "token_symbol": token_symbol,
                "base_token": base_token,
                "quote_token": quote_token,
                "base_token_address": base_token_address,
                "quote_token_address": quote_token_address,
                "cex_price": cex_price,
                "dex_price": dex_price,
                "price_diff": price_diff,
                "price_diff_percent": price_diff_percent,
                "direction": direction,
                "buy_exchange": buy_exchange,
                "sell_exchange": sell_exchange,
                "buy_price": buy_price,
                "sell_price": sell_price,
                "profit_percent": profit_percent,
                "timestamp": time.time()
            }
            
            return opportunity
            
        except Exception as e:
            self.logger.error(f"Error checking prices for {token_symbol}: {e}")
            return None
    
    async def _execute_arbitrage(self, opportunity: Dict[str, Any]):
        """
        Execute an arbitrage trade.
        
        Args:
            opportunity: Dictionary containing arbitrage opportunity information
        """
        # Generate a unique ID for this arbitrage
        arbitrage_id = f"{opportunity['token_symbol']}:{int(time.time())}"
        
        # Add to active arbitrages
        self.active_arbitrages.add(arbitrage_id)
        
        try:
            self.logger.info(f"Executing arbitrage {arbitrage_id}: {opportunity['direction']} "
                           f"for {opportunity['token_symbol']} with profit {opportunity['profit_percent']:.2f}%")
            
            # Determine trade amount
            # In a real system, you would calculate this based on available balances, etc.
            trade_amount_usd = min(self.max_arbitrage_amount_usd, 100)  # Example amount
            
            # Convert to token amount
            token_amount = trade_amount_usd / opportunity["buy_price"]
            
            # Execute trades based on direction
            if opportunity["direction"] == "cex_to_dex":
                # Buy on CEX
                cex_client = self.cex_clients[opportunity["buy_exchange"]]
                blockchain_client = self.blockchain_clients[opportunity["sell_exchange"]]
                
                # Place buy order on CEX
                self.logger.info(f"Placing buy order on {opportunity['buy_exchange']} "
                               f"for {token_amount} {opportunity['base_token']}")
                
                # In a real implementation, you would:
                # 1. Place the buy order on the CEX
                # 2. Wait for the order to be filled
                # 3. Transfer the tokens to your wallet if needed
                # 4. Sell the tokens on the DEX
                
                # Simulate successful arbitrage
                await asyncio.sleep(2)  # Simulate execution time
                
                self.logger.info(f"Arbitrage {arbitrage_id} completed successfully")
                
                # Update statistics
                self.stats["arbitrages_executed"] += 1
                profit_usd = trade_amount_usd * (opportunity["profit_percent"] / 100)
                self.stats["total_profit_usd"] += profit_usd
                
            else:  # dex_to_cex
                # Buy on DEX
                blockchain_client = self.blockchain_clients[opportunity["buy_exchange"]]
                cex_client = self.cex_clients[opportunity["sell_exchange"]]
                
                # Execute swap on DEX
                self.logger.info(f"Executing swap on {opportunity['buy_exchange']} "
                               f"for {token_amount} {opportunity['base_token']}")
                
                # In a real implementation, you would:
                # 1. Execute the swap on the DEX
                # 2. Wait for the transaction to be confirmed
                # 3. Transfer the tokens to the CEX if needed
                # 4. Sell the tokens on the CEX
                
                # Simulate successful arbitrage
                await asyncio.sleep(2)  # Simulate execution time
                
                self.logger.info(f"Arbitrage {arbitrage_id} completed successfully")
                
                # Update statistics
                self.stats["arbitrages_executed"] += 1
                profit_usd = trade_amount_usd * (opportunity["profit_percent"] / 100)
                self.stats["total_profit_usd"] += profit_usd
            
        except Exception as e:
            self.logger.error(f"Error executing arbitrage {arbitrage_id}: {e}")
            self.stats["failed_arbitrages"] += 1
        
        finally:
            # Remove from active arbitrages
            self.active_arbitrages.remove(arbitrage_id)
    
    async def _flash_arbitrage(self, opportunity: Dict[str, Any]):
        """
        Execute a flash arbitrage trade (no funds required).
        
        Args:
            opportunity: Dictionary containing arbitrage opportunity information
        """
        # This is a placeholder for flash arbitrage implementation
        # Flash arbitrage typically involves flash loans and complex smart contract interactions
        self.logger.info(f"Flash arbitrage not yet implemented for {opportunity['token_symbol']}")
        
        # In a real implementation, you would:
        # 1. Take a flash loan
        # 2. Execute the arbitrage
        # 3. Repay the flash loan
        # 4. Keep the profit
        
        # For now, we'll just log that this method was called
        self.logger.info(f"Would execute flash arbitrage for {opportunity['token_symbol']} "
                       f"with profit {opportunity['profit_percent']:.2f}%") 