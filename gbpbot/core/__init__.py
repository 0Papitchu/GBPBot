"""
Fonctionnalités principales de GBPBot
====================================

Ce module contient les fonctionnalités principales du bot GBPBot,
notamment la configuration, la gestion des portefeuilles et les connexions RPC.
"""

# Définir les variables à exporter avec "from gbpbot.core import *"
__all__ = []

# Importer les sous-modules pour qu'ils soient accessibles via gbpbot.core.*
try:
    from . import config
    __all__.append('config')
except ImportError:
    pass

try:
    from . import wallet
    __all__.append('wallet')
except ImportError:
    pass

try:
    from . import rpc
    __all__.append('rpc')
except ImportError:
    pass

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