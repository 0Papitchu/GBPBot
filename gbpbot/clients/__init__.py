#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module clients pour GBPBot
=========================

Ce module fournit des clients pour interagir avec différentes blockchains
et services externes.
"""

import logging

# Configuration du logger
logger = logging.getLogger("gbpbot.clients")

# Importation des clients
try:
    from .blockchain_client_factory import BlockchainClientFactory
except ImportError as e:
    logger.warning(f"Erreur lors de l'importation de BlockchainClientFactory: {e}")
    # Créer une classe factice pour éviter les erreurs d'importation
    class BlockchainClientFactory:
        """Classe factice pour BlockchainClientFactory."""
        @staticmethod
        def create_client(*args, **kwargs):
            logger.error("BlockchainClientFactory n'est pas disponible.")
            return None

# Exports
__all__ = [
    'BlockchainClientFactory',
] 