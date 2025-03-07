#!/usr/bin/env python
"""
Binance Client for GBPBot.

This module provides a client for interacting with the Binance exchange.
It implements the BaseCEXClient interface and provides Binance-specific functionality.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Tuple, Union

try:
    from binance.client import Client as BinanceAPIClient
    from binance.exceptions import BinanceAPIException, BinanceRequestException
    BINANCE_SDK_AVAILABLE = True
except ImportError:
    BINANCE_SDK_AVAILABLE = False
    logging.warning("Binance SDK not available. Install with 'pip install python-binance'")

from gbpbot.clients.base_cex_client import BaseCEXClient
from gbpbot.utils.exceptions import ExchangeConnectionError, ExchangeAPIError


class BinanceClient(BaseCEXClient):
    """
    Client for interacting with the Binance exchange.
    
    This client implements the BaseCEXClient interface and provides
    Binance-specific functionality for trading and market data.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the Binance client.
        
        Args:
            config: Configuration dictionary for the client
        """
        super().__init__(config)
        self.exchange_name = "binance"
        
        # Get API credentials from config
        self.api_key = config.get("BINANCE_API_KEY", "")
        self.api_secret = config.get("BINANCE_API_SECRET", "")
        
        # Initialize client
        self.client = None
        
        # Set rate limit delay
        self.rate_limit_delay = 0.2  # 200ms between requests
        
        # Symbol format mapping
        self.symbol_format_map = {}
        
        if not BINANCE_SDK_AVAILABLE:
            self.logger.error("Binance SDK not available. Install with 'pip install python-binance'")
    
    async def connect(self) -> bool:
        """
        Connect to the Binance exchange.
        
        Returns:
            True if connection was successful, False otherwise
        """
        if not BINANCE_SDK_AVAILABLE:
            self.logger.error("Binance SDK not available. Cannot connect.")
            return False
        
        if not self.api_key or not self.api_secret:
            self.logger.error("API key or secret not provided. Cannot connect.")
            return False
        
        try:
            self.logger.info("Connecting to Binance...")
            
            # Create client
            self.client = BinanceAPIClient(api_key=self.api_key, api_secret=self.api_secret)
            
            # Test connection
            server_time = self.client.get_server_time()
            
            if not server_time:
                self.logger.error("Failed to get server time. Connection failed.")
                return False
            
            # Get exchange info to populate symbol mapping
            await self._populate_symbol_mapping()
            
            self.connected = True
            self.logger.info("Connected to Binance")
            return True
            
        except (BinanceAPIException, BinanceRequestException) as e:
            self.logger.error(f"Error connecting to Binance: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error connecting to Binance: {e}")
            return False
    
    async def disconnect(self) -> bool:
        """
        Disconnect from the Binance exchange.
        
        Returns:
            True if disconnection was successful, False otherwise
        """
        self.logger.info("Disconnecting from Binance...")
        self.client = None
        self.connected = False
        self.logger.info("Disconnected from Binance")
        return True
    
    async def _populate_symbol_mapping(self):
        """
        Populate symbol format mapping from exchange info.
        """
        try:
            # Get exchange info
            exchange_info = self.client.get_exchange_info()
            
            # Populate symbol mapping
            for symbol_info in exchange_info["symbols"]:
                base_asset = symbol_info["baseAsset"]
                quote_asset = symbol_info["quoteAsset"]
                standard_format = f"{base_asset}/{quote_asset}"
                binance_format = symbol_info["symbol"]
                
                self.symbol_format_map[standard_format] = binance_format
            
            self.logger.info(f"Populated symbol mapping with {len(self.symbol_format_map)} symbols")
            
        except Exception as e:
            self.logger.error(f"Error populating symbol mapping: {e}")
    
    def _format_symbol(self, symbol: str) -> str:
        """
        Format symbol according to Binance requirements.
        
        Args:
            symbol: Trading symbol (e.g., "BTC/USDT")
            
        Returns:
            Formatted symbol (e.g., "BTCUSDT")
        """
        # Check if symbol is in mapping
        if symbol in self.symbol_format_map:
            return self.symbol_format_map[symbol]
        
        # Default formatting
        return symbol.replace("/", "")
    
    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Get ticker information for a symbol.
        
        Args:
            symbol: Trading symbol (e.g., "BTC/USDT")
            
        Returns:
            Dictionary containing ticker information
        """
        if not self.connected or not self.client:
            raise ExchangeConnectionError("Not connected to Binance")
        
        # Check cache first
        cached_ticker = self._get_cached_ticker(symbol)
        if cached_ticker:
            return cached_ticker
        
        try:
            # Apply rate limiting
            self._rate_limit()
            
            # Format symbol
            formatted_symbol = self._format_symbol(symbol)
            
            # Get ticker
            ticker = self.client.get_ticker(symbol=formatted_symbol)
            
            # Format response
            result = {
                "symbol": symbol,
                "bid": float(ticker["bidPrice"]),
                "ask": float(ticker["askPrice"]),
                "last": float(ticker["lastPrice"]),
                "volume": float(ticker["volume"]),
                "timestamp": ticker["closeTime"] / 1000,  # Convert to seconds
                "exchange": "binance"
            }
            
            # Update cache
            self._update_ticker_cache(symbol, result)
            
            return result
            
        except (BinanceAPIException, BinanceRequestException) as e:
            self._handle_error(e, "get_ticker")
            raise ExchangeAPIError(f"Error getting ticker for {symbol}: {e}")
        except Exception as e:
            self._handle_error(e, "get_ticker")
            raise ExchangeAPIError(f"Unexpected error getting ticker for {symbol}: {e}")
    
    async def get_balance(self, asset: str) -> float:
        """
        Get balance for an asset.
        
        Args:
            asset: Asset symbol (e.g., "BTC")
            
        Returns:
            Balance of the asset
        """
        if not self.connected or not self.client:
            raise ExchangeConnectionError("Not connected to Binance")
        
        try:
            # Apply rate limiting
            self._rate_limit()
            
            # Get account information
            account = self.client.get_account()
            
            # Find asset balance
            for balance in account["balances"]:
                if balance["asset"] == asset:
                    return float(balance["free"])
            
            # Asset not found
            return 0.0
            
        except (BinanceAPIException, BinanceRequestException) as e:
            self._handle_error(e, "get_balance")
            raise ExchangeAPIError(f"Error getting balance for {asset}: {e}")
        except Exception as e:
            self._handle_error(e, "get_balance")
            raise ExchangeAPIError(f"Unexpected error getting balance for {asset}: {e}")
    
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
        if not self.connected or not self.client:
            raise ExchangeConnectionError("Not connected to Binance")
        
        try:
            # Apply rate limiting
            self._rate_limit()
            
            # Format symbol
            formatted_symbol = self._format_symbol(symbol)
            
            # Format side
            formatted_side = side.upper()
            
            # Format order type
            formatted_order_type = order_type.upper()
            
            # Prepare order parameters
            params = {
                "symbol": formatted_symbol,
                "side": formatted_side,
                "type": formatted_order_type,
                "quantity": amount
            }
            
            # Add price for limit orders
            if formatted_order_type == "LIMIT" and price is not None:
                params["price"] = price
                params["timeInForce"] = "GTC"  # Good Till Cancelled
            
            # Place order
            order = self.client.create_order(**params)
            
            # Format response
            result = {
                "id": order["orderId"],
                "symbol": symbol,
                "side": side,
                "type": order_type,
                "amount": float(order["origQty"]),
                "price": float(order.get("price", 0)),
                "status": order["status"].lower(),
                "timestamp": order["transactTime"] / 1000,  # Convert to seconds
                "exchange": "binance"
            }
            
            return result
            
        except (BinanceAPIException, BinanceRequestException) as e:
            self._handle_error(e, "place_order")
            raise ExchangeAPIError(f"Error placing order for {symbol}: {e}")
        except Exception as e:
            self._handle_error(e, "place_order")
            raise ExchangeAPIError(f"Unexpected error placing order for {symbol}: {e}")
    
    async def get_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """
        Get information about an order.
        
        Args:
            order_id: Order ID
            symbol: Trading symbol (e.g., "BTC/USDT")
            
        Returns:
            Dictionary containing order information
        """
        if not self.connected or not self.client:
            raise ExchangeConnectionError("Not connected to Binance")
        
        try:
            # Apply rate limiting
            self._rate_limit()
            
            # Format symbol
            formatted_symbol = self._format_symbol(symbol)
            
            # Get order
            order = self.client.get_order(symbol=formatted_symbol, orderId=order_id)
            
            # Format response
            result = {
                "id": order["orderId"],
                "symbol": symbol,
                "side": order["side"].lower(),
                "type": order["type"].lower(),
                "amount": float(order["origQty"]),
                "filled": float(order["executedQty"]),
                "price": float(order.get("price", 0)),
                "status": order["status"].lower(),
                "timestamp": order["time"] / 1000,  # Convert to seconds
                "exchange": "binance"
            }
            
            return result
            
        except (BinanceAPIException, BinanceRequestException) as e:
            self._handle_error(e, "get_order")
            raise ExchangeAPIError(f"Error getting order {order_id} for {symbol}: {e}")
        except Exception as e:
            self._handle_error(e, "get_order")
            raise ExchangeAPIError(f"Unexpected error getting order {order_id} for {symbol}: {e}")
    
    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """
        Cancel an order.
        
        Args:
            order_id: Order ID
            symbol: Trading symbol (e.g., "BTC/USDT")
            
        Returns:
            True if cancellation was successful, False otherwise
        """
        if not self.connected or not self.client:
            raise ExchangeConnectionError("Not connected to Binance")
        
        try:
            # Apply rate limiting
            self._rate_limit()
            
            # Format symbol
            formatted_symbol = self._format_symbol(symbol)
            
            # Cancel order
            result = self.client.cancel_order(symbol=formatted_symbol, orderId=order_id)
            
            # Check if cancellation was successful
            return result["status"] == "CANCELED"
            
        except (BinanceAPIException, BinanceRequestException) as e:
            self._handle_error(e, "cancel_order")
            
            # Check if order was already cancelled or filled
            if "Unknown order" in str(e):
                self.logger.warning(f"Order {order_id} for {symbol} already cancelled or filled")
                return True
            
            raise ExchangeAPIError(f"Error cancelling order {order_id} for {symbol}: {e}")
        except Exception as e:
            self._handle_error(e, "cancel_order")
            raise ExchangeAPIError(f"Unexpected error cancelling order {order_id} for {symbol}: {e}")
    
    async def get_order_book(self, symbol: str, limit: int = 20) -> Dict[str, Any]:
        """
        Get order book for a symbol.
        
        Args:
            symbol: Trading symbol (e.g., "BTC/USDT")
            limit: Number of orders to retrieve
            
        Returns:
            Dictionary containing order book information
        """
        if not self.connected or not self.client:
            raise ExchangeConnectionError("Not connected to Binance")
        
        try:
            # Apply rate limiting
            self._rate_limit()
            
            # Format symbol
            formatted_symbol = self._format_symbol(symbol)
            
            # Get order book
            order_book = self.client.get_order_book(symbol=formatted_symbol, limit=limit)
            
            # Format response
            result = {
                "symbol": symbol,
                "bids": [[float(price), float(amount)] for price, amount in order_book["bids"]],
                "asks": [[float(price), float(amount)] for price, amount in order_book["asks"]],
                "timestamp": order_book["lastUpdateId"] / 1000,  # Use lastUpdateId as timestamp
                "exchange": "binance"
            }
            
            return result
            
        except (BinanceAPIException, BinanceRequestException) as e:
            self._handle_error(e, "get_order_book")
            raise ExchangeAPIError(f"Error getting order book for {symbol}: {e}")
        except Exception as e:
            self._handle_error(e, "get_order_book")
            raise ExchangeAPIError(f"Unexpected error getting order book for {symbol}: {e}")
    
    async def get_trading_pairs(self) -> List[str]:
        """
        Get list of available trading pairs.
        
        Returns:
            List of trading pairs
        """
        if not self.connected or not self.client:
            raise ExchangeConnectionError("Not connected to Binance")
        
        try:
            # Apply rate limiting
            self._rate_limit()
            
            # Get exchange info
            exchange_info = self.client.get_exchange_info()
            
            # Extract trading pairs
            pairs = []
            for symbol_info in exchange_info["symbols"]:
                if symbol_info["status"] == "TRADING":
                    base_asset = symbol_info["baseAsset"]
                    quote_asset = symbol_info["quoteAsset"]
                    pairs.append(f"{base_asset}/{quote_asset}")
            
            return pairs
            
        except (BinanceAPIException, BinanceRequestException) as e:
            self._handle_error(e, "get_trading_pairs")
            raise ExchangeAPIError(f"Error getting trading pairs: {e}")
        except Exception as e:
            self._handle_error(e, "get_trading_pairs")
            raise ExchangeAPIError(f"Unexpected error getting trading pairs: {e}")
    
    def _handle_error(self, error: Exception, method_name: str) -> None:
        """
        Handle errors from Binance API calls.
        
        Args:
            error: Exception that occurred
            method_name: Name of the method that raised the exception
        """
        super()._handle_error(error, method_name)
        
        # Handle Binance-specific errors
        if isinstance(error, BinanceAPIException):
            if error.code == -1021:  # Timestamp for this request is outside of the recvWindow
                self.logger.warning("Timestamp error. Check system clock synchronization.")
            elif error.code == -1022:  # Signature for this request is not valid
                self.logger.error("Invalid signature. Check API key and secret.")
            elif error.code == -2010:  # Insufficient balance
                self.logger.warning("Insufficient balance for requested action.")
            elif error.code == -2011:  # Order would trigger immediately
                self.logger.warning("Order would trigger immediately. Adjust price.")
            elif error.code == -1003:  # Too many requests
                self.logger.warning("Rate limit exceeded. Increasing delay between requests.")
                self.rate_limit_delay *= 2  # Double the delay 