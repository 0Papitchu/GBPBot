"""
Core components of the GBP Bot application.

This package contains the core components of the application, including
blockchain clients, transaction handling, and other essential functionality.
"""

# Define what should be imported with "from gbpbot.core import *"
__all__ = []

# Importer les modules principaux
from gbpbot.core.rpc.rpc_manager import rpc_manager
from gbpbot.core.price_feed import (
    PriceManager,
    DEXPriceFeed,
    CEXPriceFeed,
    PriceNormalizer,
    EnhancedPriceNormalizer,
    PriceAggregator
)

# Exporter les classes et fonctions principales
__all__ = [
    'rpc_manager',
    'PriceManager',
    'DEXPriceFeed',
    'CEXPriceFeed',
    'PriceNormalizer',
    'EnhancedPriceNormalizer',
    'PriceAggregator'
] 