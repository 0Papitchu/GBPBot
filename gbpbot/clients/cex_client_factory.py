#!/usr/bin/env python
"""
CEX Client Factory for GBPBot.

This module provides a factory for creating clients for different centralized
exchanges (CEX) like Binance, KuCoin, and Gate.io.
"""

import logging
from typing import Dict, Any, Optional, Type

# Import base client
from gbpbot.clients.base_cex_client import BaseCEXClient

# Import specific clients
try:
    from gbpbot.clients.binance_client import BinanceClient
    BINANCE_AVAILABLE = True
except ImportError:
    BINANCE_AVAILABLE = False
    logging.warning("Binance client not available. Install with 'pip install python-binance'")

try:
    from gbpbot.clients.kucoin_client import KuCoinClient
    KUCOIN_AVAILABLE = True
except ImportError:
    KUCOIN_AVAILABLE = False
    logging.warning("KuCoin client not available. Install with 'pip install kucoin-python'")

try:
    from gbpbot.clients.gateio_client import GateIOClient
    GATEIO_AVAILABLE = True
except ImportError:
    GATEIO_AVAILABLE = False
    logging.warning("Gate.io client not available. Install with 'pip install gate-api'")


class CEXClientFactory:
    """
    Factory for creating CEX clients.
    
    This factory creates clients for different centralized exchanges (CEX)
    based on the provided configuration.
    """
    
    # Registry of available clients
    _clients: Dict[str, Type[BaseCEXClient]] = {}
    
    @classmethod
    def register_client(cls, name: str, client_class: Type[BaseCEXClient]):
        """
        Register a CEX client.
        
        Args:
            name: Name of the CEX
            client_class: Client class for the CEX
        """
        cls._clients[name.lower()] = client_class
        logging.info(f"Registered CEX client: {name}")
    
    @classmethod
    def get_client(cls, cex_name: str, config: Dict[str, Any]) -> Optional[BaseCEXClient]:
        """
        Get a CEX client.
        
        Args:
            cex_name: Name of the CEX
            config: Configuration for the client
            
        Returns:
            CEX client instance or None if not available
        """
        cex_name = cex_name.lower()
        
        if cex_name not in cls._clients:
            logging.error(f"CEX client not found: {cex_name}")
            return None
        
        try:
            client = cls._clients[cex_name](config)
            logging.info(f"Created CEX client: {cex_name}")
            return client
        except Exception as e:
            logging.error(f"Error creating CEX client {cex_name}: {e}")
            return None
    
    @classmethod
    def get_available_clients(cls) -> Dict[str, bool]:
        """
        Get available CEX clients.
        
        Returns:
            Dictionary of available clients and their availability status
        """
        return {
            "binance": BINANCE_AVAILABLE,
            "kucoin": KUCOIN_AVAILABLE,
            "gateio": GATEIO_AVAILABLE
        }


# Register available clients
if BINANCE_AVAILABLE:
    CEXClientFactory.register_client("binance", BinanceClient)

if KUCOIN_AVAILABLE:
    CEXClientFactory.register_client("kucoin", KuCoinClient)

if GATEIO_AVAILABLE:
    CEXClientFactory.register_client("gateio", GateIOClient) 