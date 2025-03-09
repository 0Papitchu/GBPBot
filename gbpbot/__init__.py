#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GBPBot - Trading Bot pour opérations d'arbitrage, sniping et MEV
===============================================================

Système de trading automatisé pour Avalanche, Solana et autres blockchains,
avec des fonctionnalités d'arbitrage, sniping de tokens et MEV.

Copyright (c) 2023-2024 GBPBot Team
"""

import os
import sys
from pathlib import Path

# Vérifier si le répertoire principal existe dans le sys.path
base_dir = Path(__file__).parent.parent.absolute()
if str(base_dir) not in sys.path:
    sys.path.insert(0, str(base_dir))

# Charger le module de démarrage
try:
    from gbpbot.boot import boot
    
    # Initialiser l'environnement
    boot()
except ImportError:
    # En cas d'erreur, ne pas bloquer l'import
    print("Avertissement: Le module de démarrage n'a pas pu être chargé.")
    print("Les variables d'environnement peuvent ne pas être correctement initialisées.")

# Version du package
__version__ = "0.9.0"
__author__ = "GBPBot Team"
__email__ = "contact@gbpbot.com"

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