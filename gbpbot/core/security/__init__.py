#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Module de sécurité du GBPBot.

Ce module fournit les outils essentiels pour assurer la sécurité du GBPBot, notamment:
- Gestion des secrets (clés API, clés privées)
- Protection contre le MEV (sandwich attack, front-running)
- Validation des transactions avant exécution
- Détection des contrats malveillants
"""

# Version et auteur
__version__ = "1.0.0"
__author__ = "GBPBot Team"

# Importation des classes principales pour faciliter l'accès
try:
    from .secrets_manager import SecretsManager
except ImportError:
    import logging
    logging.getLogger(__name__).warning("Module secrets_manager non disponible")

# Autres imports du package security
from .emergency_system import EmergencySystem
from .trade_protection import TradeProtection
from .mev_protection import MEVProtection 