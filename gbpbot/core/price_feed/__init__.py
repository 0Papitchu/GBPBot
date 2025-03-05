"""
Package de gestion des flux de prix pour GBPBot.
Version améliorée avec réduction des duplications fonctionnelles.

Ce module fournit une architecture optimisée pour la gestion des prix,
avec un normalisation avancée, une détection des anomalies et une
gestion des opportunités d'arbitrage.

Notes de migration:
- EnhancedPriceNormalizer est désormais la classe recommandée pour la normalisation des prix
- PriceAggregator a été recentré sur l'agrégation et l'arbitrage, PriceManager gère les sources
"""

# Gestionnaire principal
from .price_manager import PriceManager

# Sources de prix
from .dex_feed import DEXPriceFeed
from .cex_feed import CEXPriceFeed

# Traitement des prix
from .price_normalizer import PriceNormalizer as EnhancedPriceNormalizer
from .normalizer import PriceNormalizer  # Version dépréciée, pour compatibilité
from .aggregator import PriceAggregator

# Classes de base
from .base import BasePriceFeed

# Si le module d'oracle existe, l'importer
try:
    from .sources.oracle import OraclePriceFeed
    has_oracle = True
except ImportError:
    has_oracle = False
    OraclePriceFeed = None

__all__ = [
    'PriceManager',
    'DEXPriceFeed',
    'CEXPriceFeed',
    'PriceNormalizer',  # Gardé pour compatibilité
    'EnhancedPriceNormalizer',  # Recommandé pour les nouvelles implémentations
    'PriceAggregator',
    'BasePriceFeed',
]

# Ajouter OraclePriceFeed si disponible
if has_oracle:
    __all__.append('OraclePriceFeed')

# Informations de version
__version__ = '1.2.0'
__author__ = 'GBPBot Team'
__status__ = 'Production' 