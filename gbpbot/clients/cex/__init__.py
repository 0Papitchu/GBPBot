#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module des clients d'échanges centralisés (CEX) pour GBPBot.

Ce module fournit des implémentations pour interagir avec différentes plateformes
d'échange centralisées comme Binance, KuCoin, Gate.io, etc.
"""

import logging
from typing import List

# Import des classes de base
from gbpbot.clients.base_cex_client import BaseCEXClient
from gbpbot.clients.cex_client_factory import CEXClientFactory

# Import des implémentations spécifiques
from gbpbot.clients.binance_client import BinanceClient

# Configuration du logger
logger = logging.getLogger(__name__)

# Enregistrement des clients disponibles dans la factory
CEXClientFactory.register_client_class("binance", BinanceClient)

# Liste des échanges supportés
SUPPORTED_EXCHANGES: List[str] = ["binance"]

# Exportation des classes et fonctions publiques
__all__ = [
    "BaseCEXClient",
    "CEXClientFactory",
    "BinanceClient",
    "SUPPORTED_EXCHANGES"
]

logger.info(f"Module CEX initialisé avec {len(SUPPORTED_EXCHANGES)} échange(s) supporté(s): {', '.join(SUPPORTED_EXCHANGES)}") 