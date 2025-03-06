#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GBPBot - Trading Bot pour MEME Coins
====================================

Un bot de trading ultra-rapide, furtif et intelligent pour le trading de MEME coins 
sur Solana, AVAX et Sonic, avec scalping automatique, arbitrage entre pools, 
sniping des nouveaux tokens et MEV/Frontrunning.

Copyright (c) 2023-2024 GBPBot Team
"""

__version__ = "1.0.0"
__author__ = "GBPBot Team"
__email__ = "contact@gbpbot.com"

import os
import logging
from pathlib import Path

# Configuration des chemins
ROOT_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = ROOT_DIR / "data"
CONFIG_DIR = ROOT_DIR / "config"
LOG_DIR = ROOT_DIR.parent / "logs"

# Création des répertoires s'ils n'existent pas
for directory in [DATA_DIR, CONFIG_DIR, LOG_DIR]:
    directory.mkdir(exist_ok=True, parents=True)

# Configuration du logger global
def setup_logger(log_level=None):
    """Configure le logger global du package."""
    if log_level is None:
        from dotenv import load_dotenv
        load_dotenv()
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    
    numeric_level = getattr(logging, log_level, logging.INFO)
    
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
        ]
    )
    
    # Réduire le niveau de verbosité des logs des bibliothèques tierces
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("websockets").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("matplotlib").setLevel(logging.WARNING)
    
    return logging.getLogger("gbpbot")

# Exports principaux
from gbpbot.clients import BlockchainClientFactory
from gbpbot.modules import ArbitrageEngine, TokenSniper, AutoTrader

# Export des modules principaux
from . import core
from . import blockchain
from . import strategies
from . import security
from . import db

# Import des fonctions utilitaires principales
try:
    from .run_benchmark import import_module_from_path, ensure_benchmark_modules
except ImportError:
    pass  # Ignorer si les modules requis ne sont pas disponibles

# Define what should be imported with "from gbpbot import *"
__all__ = [
    "BaseBlockchainClient",
    "BlockchainClientFactory",
] 