#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module d'IA pour GBPBot
======================

Ce module intègre des capacités d'IA dans GBPBot, fournissant des interfaces
pour les modèles de langage (LLMs) et d'autres fonctionnalités d'IA pour
améliorer les stratégies de trading.
"""

import os
import logging
from typing import Optional, Dict, Any, Literal

# Configuration du logger
logger = logging.getLogger("gbpbot.ai")

# Tentative d'importation des composants
try:
    from .llm_provider import LLMProvider
    from .prompt_manager import get_prompt_manager, PromptManager
    
    # Clients spécifiques
    try:
        from .openai_client import OpenAIClient
    except ImportError:
        logger.warning("OpenAIClient non disponible. Vérifiez l'installation du package openai.")
        OpenAIClient = None
    
    try:
        from .llama_client import LLaMAClient
    except ImportError:
        logger.warning("LLaMAClient non disponible. Vérifiez l'installation des packages requis.")
        LLaMAClient = None
    
    components_loaded = True
    
except ImportError as e:
    logger.error(f"Erreur lors du chargement des composants d'IA: {e}")
    components_loaded = False


def create_ai_client(provider: Literal['openai', 'llama', 'auto'] = 'auto', 
                     config: Optional[Dict[str, Any]] = None) -> Optional[LLMProvider]:
    """
    Crée un client d'IA approprié en fonction du fournisseur spécifié.
    
    Args:
        provider: Le fournisseur d'IA à utiliser ('openai', 'llama', ou 'auto')
        config: Configuration spécifique pour le client
        
    Returns:
        Une instance du client d'IA ou None en cas d'erreur
    """
    if not components_loaded:
        logger.error("Impossible de créer un client d'IA: composants non chargés.")
        return None
    
    # Utiliser une configuration vide si non spécifiée
    if config is None:
        config = {}
    
    # Déterminer automatiquement le meilleur fournisseur si 'auto'
    if provider == 'auto':
        if OpenAIClient is not None:
            provider = 'openai'
        elif LLaMAClient is not None:
            provider = 'llama'
        else:
            logger.error("Aucun fournisseur d'IA disponible.")
            return None
    
    # Créer le client approprié
    try:
        if provider == 'openai':
            if OpenAIClient is None:
                logger.error("OpenAIClient non disponible mais demandé.")
                return None
            return OpenAIClient(**config)
        
        elif provider == 'llama':
            if LLaMAClient is None:
                logger.error("LLaMAClient non disponible mais demandé.")
                return None
            return LLaMAClient(**config)
        
        else:
            logger.error(f"Fournisseur d'IA non reconnu: {provider}")
            return None
    
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation du client {provider}: {e}")
        return None


# Exposer les éléments importants du module
__all__ = [
    'create_ai_client',
    'LLMProvider',
    'get_prompt_manager',
    'PromptManager'
]

if OpenAIClient is not None:
    __all__.append('OpenAIClient')
if LLaMAClient is not None:
    __all__.append('LLaMAClient') 