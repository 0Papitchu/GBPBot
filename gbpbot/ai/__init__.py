#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module d'Intelligence Artificielle pour GBPBot
=============================================

Ce module fournit des fonctionnalités d'analyse et de prise de décision
basées sur l'intelligence artificielle pour améliorer les performances
du GBPBot.

Il intègre des modèles légers pour l'analyse en temps réel et des modèles
plus avancés pour l'analyse approfondie, avec une approche hybride pour
optimiser les performances sur le matériel disponible.
"""

import os
import logging
from typing import Dict, Any, Optional, Union, List

# Configuration du logger
logger = logging.getLogger(__name__)

# Vérifier si les dépendances d'IA sont disponibles
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    logger.warning("NumPy n'est pas disponible. Certaines fonctionnalités d'IA seront limitées.")

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.warning("PyTorch n'est pas disponible. Certaines fonctionnalités d'IA seront limitées.")

try:
    import onnxruntime as ort
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False
    logger.warning("ONNX Runtime n'est pas disponible. Les modèles légers seront plus lents.")

# Vérifier si OpenAI est disponible
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI n'est pas disponible. L'analyse approfondie sera limitée.")

# Vérifier si LLaMA est disponible
try:
    from llama_cpp import Llama
    LLAMA_AVAILABLE = True
except ImportError:
    LLAMA_AVAILABLE = False
    logger.warning("LLaMA n'est pas disponible. L'analyse locale sera limitée.")

# Importer les classes et fonctions principales
from gbpbot.ai.llm_provider import LLMProvider
from gbpbot.ai.prompt_manager import get_prompt_manager, PromptManager

# Fonction pour créer un client IA
def create_ai_client(provider: str = "auto", config: Optional[Dict[str, Any]] = None) -> Optional[LLMProvider]:
    """
    Crée un client IA en fonction du fournisseur spécifié
    
    Args:
        provider: Fournisseur d'IA ("openai", "llama", "auto")
        config: Configuration supplémentaire
        
    Returns:
        LLMProvider: Client IA ou None si aucun fournisseur n'est disponible
    """
    if config is None:
        config = {}
    
    # Déterminer le fournisseur à utiliser
    if provider == "auto":
        if OPENAI_AVAILABLE and "openai_api_key" in config and config["openai_api_key"]:
            provider = "openai"
        elif LLAMA_AVAILABLE:
            provider = "llama"
        else:
            logger.warning("Aucun fournisseur d'IA disponible. L'analyse IA sera désactivée.")
            return None
    
    # Créer le client en fonction du fournisseur
    if provider == "openai":
        if not OPENAI_AVAILABLE:
            logger.error("OpenAI n'est pas disponible. Veuillez installer le package 'openai'.")
            return None
        
        from gbpbot.ai.openai_client import OpenAIClient
        return OpenAIClient(config)
    
    elif provider == "llama":
        if not LLAMA_AVAILABLE:
            logger.error("LLaMA n'est pas disponible. Veuillez installer le package 'llama-cpp-python'.")
            return None
        
        from gbpbot.ai.llama_client import LlamaClient
        return LlamaClient(config)
    
    else:
        logger.error(f"Fournisseur d'IA inconnu: {provider}")
        return None

# Fonction pour créer un analyseur de marché
def create_market_analyzer(ai_client: Optional[LLMProvider] = None, config: Optional[Dict[str, Any]] = None) -> Any:
    """
    Crée un analyseur de marché basé sur l'IA
    
    Args:
        ai_client: Client IA à utiliser
        config: Configuration supplémentaire
        
    Returns:
        MarketAnalyzer: Analyseur de marché
    """
    from gbpbot.ai.market_analyzer import MarketAnalyzer
    return MarketAnalyzer(ai_client, config)

# Fonction pour créer un analyseur de contrats
def create_token_contract_analyzer(ai_client: Optional[LLMProvider] = None, config: Optional[Dict[str, Any]] = None) -> Any:
    """
    Crée un analyseur de contrats de tokens basé sur l'IA
    
    Args:
        ai_client: Client IA à utiliser
        config: Configuration supplémentaire
        
    Returns:
        TokenContractAnalyzer: Analyseur de contrats
    """
    from gbpbot.ai.token_contract_analyzer import create_token_contract_analyzer as create_analyzer
    return create_analyzer(ai_client, config)

# Fonction pour vérifier si l'IA est disponible
def is_ai_available() -> bool:
    """
    Vérifie si les fonctionnalités d'IA sont disponibles
    
    Returns:
        bool: True si l'IA est disponible, False sinon
    """
    return NUMPY_AVAILABLE and (TORCH_AVAILABLE or ONNX_AVAILABLE) and (OPENAI_AVAILABLE or LLAMA_AVAILABLE)

# Fonction pour vérifier si l'accélération GPU est disponible
def is_gpu_available() -> bool:
    """
    Vérifie si l'accélération GPU est disponible
    
    Returns:
        bool: True si le GPU est disponible, False sinon
    """
    if TORCH_AVAILABLE:
        return torch.cuda.is_available()
    elif ONNX_AVAILABLE:
        return "CUDAExecutionProvider" in ort.get_available_providers()
    else:
        return False

# Exporter les classes et fonctions principales
__all__ = [
    "LLMProvider",
    "PromptManager",
    "get_prompt_manager",
    "create_ai_client",
    "create_market_analyzer",
    "create_token_contract_analyzer",
    "is_ai_available",
    "is_gpu_available"
] 