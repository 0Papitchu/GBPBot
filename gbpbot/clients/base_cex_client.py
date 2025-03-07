#!/usr/bin/env python
"""
Base CEX Client for GBPBot.

This module provides a base class for all centralized exchange (CEX) clients.
All specific CEX clients should inherit from this class and implement its methods.
"""

import abc
import logging
import time
from typing import Dict, List, Optional, Any, Tuple, Union


class BaseCEXClient(abc.ABC):
    """
    Base class for all CEX clients.
    
    This abstract class defines the interface that all CEX clients must implement.
    It provides common functionality and defines abstract methods that must be
    implemented by specific CEX clients.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the base CEX client.
        
        Args:
            config: Configuration dictionary for the client
        """
        self.config = config
        self.logger = logging.getLogger(f"gbpbot.clients.{self.__class__.__name__.lower()}")
        self.exchange_name = "unknown"
        self.connected = False
        self.last_request_time = 0
        self.rate_limit_delay = 0.1  # Default delay between requests in seconds
        
        # Cache for market data
        self.ticker_cache = {}
        self.ticker_cache_time = {}
        self.ticker_cache_expiry = 60  # Cache expiry in seconds
        
        self.logger.info(f"Initialized {self.__class__.__name__}")
    
    @abc.abstractmethod
    async def connect(self) -> bool:
        """
        Connect to the exchange.
        
        Returns:
            True if connection was successful, False otherwise
        """
        pass
    
    @abc.abstractmethod
    async def disconnect(self) -> bool:
        """
        Disconnect from the exchange.
        
        Returns:
            True if disconnection was successful, False otherwise
        """
        pass
    
    @abc.abstractmethod
    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Get ticker information for a symbol.
        
        Args:
            symbol: Trading symbol (e.g., "BTC/USDT")
            
        Returns:
            Dictionary containing ticker information
        """
        pass
    
    @abc.abstractmethod
    async def get_balance(self, asset: str) -> float:
        """
        Get balance for an asset.
        
        Args:
            asset: Asset symbol (e.g., "BTC")
            
        Returns:
            Balance of the asset
        """
        pass
    
    @abc.abstractmethod
    async def place_order(self, symbol: str, side: str, order_type: str, 
                         amount: float, price: Optional[float] = None) -> Dict[str, Any]:
        """
        Place an order on the exchange.
        
        Args:
            symbol: Trading symbol (e.g., "BTC/USDT")
            side: Order side ("buy" or "sell")
            order_type: Order type ("limit", "market", etc.)
            amount: Order amount
            price: Order price (required for limit orders)
            
        Returns:
            Dictionary containing order information
        """
        pass
    
    @abc.abstractmethod
    async def get_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """
        Get information about an order.
        
        Args:
            order_id: Order ID
            symbol: Trading symbol (e.g., "BTC/USDT")
            
        Returns:
            Dictionary containing order information
        """
        pass
    
    @abc.abstractmethod
    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """
        Cancel an order.
        
        Args:
            order_id: Order ID
            symbol: Trading symbol (e.g., "BTC/USDT")
            
        Returns:
            True if cancellation was successful, False otherwise
        """
        pass
    
    @abc.abstractmethod
    async def get_order_book(self, symbol: str, limit: int = 20) -> Dict[str, Any]:
        """
        Get order book for a symbol.
        
        Args:
            symbol: Trading symbol (e.g., "BTC/USDT")
            limit: Number of orders to retrieve
            
        Returns:
            Dictionary containing order book information
        """
        pass
    
    @abc.abstractmethod
    async def get_trading_pairs(self) -> List[str]:
        """
        Get list of available trading pairs.
        
        Returns:
            List of trading pairs
        """
        pass
    
    def _rate_limit(self):
        """
        Apply rate limiting to avoid hitting exchange limits.
        """
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        
        self.last_request_time = time.time()
    
    def _update_ticker_cache(self, symbol: str, ticker: Dict[str, Any]):
        """
        Update ticker cache.
        
        Args:
            symbol: Trading symbol
            ticker: Ticker information
        """
        self.ticker_cache[symbol] = ticker
        self.ticker_cache_time[symbol] = time.time()
    
    def _get_cached_ticker(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get cached ticker information.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Cached ticker information or None if not cached or expired
        """
        if symbol in self.ticker_cache:
            cache_time = self.ticker_cache_time.get(symbol, 0)
            if time.time() - cache_time < self.ticker_cache_expiry:
                return self.ticker_cache[symbol]
        
        return None
    
    def _format_symbol(self, symbol: str) -> str:
        """
        Format symbol according to exchange requirements.
        
        Args:
            symbol: Trading symbol (e.g., "BTC/USDT")
            
        Returns:
            Formatted symbol
        """
        # Default implementation, override in specific clients if needed
        return symbol.replace("/", "")
    
    def _handle_error(self, error: Exception, method_name: str) -> None:
        """
        Handle errors from exchange API calls.
        
        Args:
            error: Exception that occurred
            method_name: Name of the method that raised the exception
        """
        self.logger.error(f"Error in {method_name}: {error}")
        
        # Check if error is related to authentication
        if "auth" in str(error).lower() or "key" in str(error).lower() or "permission" in str(error).lower():
            self.logger.error("Authentication error. Check your API keys.")
        
        # Check if error is related to rate limiting
        if "rate" in str(error).lower() or "limit" in str(error).lower():
            self.logger.warning("Rate limit hit. Increasing delay between requests.")
            self.rate_limit_delay *= 2  # Double the delay 