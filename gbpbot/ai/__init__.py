#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module d'intégration IA pour GBPBot

Ce module fournit une interface unifiée pour instancier et utiliser
différents fournisseurs d'IA dans GBPBot.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Union

# Configuration du logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("GBPBot_AI")

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
from gbpbot.ai.base import LLMProvider
from gbpbot.ai.prompt_manager import get_prompt_manager, PromptManager

async def create_ai_client(provider: str = None, config: Optional[Dict[str, Any]] = None) -> Optional[LLMProvider]:
    """
    Crée un client IA en fonction du fournisseur spécifié.
    
    Args:
        provider: Nom du fournisseur ('claude', 'openai', 'llama', 'auto')
        config: Configuration spécifique au fournisseur
        
    Returns:
        Client IA initialisé
    """
    # Détecter le fournisseur automatiquement si non spécifié
    if provider is None or provider == "auto":
        provider = os.environ.get("AI_PROVIDER", "auto")
        
        # Logique de sélection automatique du fournisseur
        if provider == "auto":
            # Priorité: 1. Claude, 2. OpenAI, 3. LLaMA (si disponible localement)
            if os.environ.get("CLAUDE_API_KEY"):
                provider = "claude"
            elif os.environ.get("OPENAI_API_KEY"):
                provider = "openai"
            else:
                # Vérifier si un modèle LLaMA local est disponible
                llama_path = os.environ.get("LLAMA_MODEL_PATH")
                if llama_path and Path(llama_path).exists():
                    provider = "llama"
                else:
                    provider = "claude"  # Défaut à Claude
    
    # Créer le client en fonction du fournisseur
    try:
        if provider.lower() == "claude":
            # Import dynamique pour éviter les dépendances circulaires
            from gbpbot.ai.claude_client import create_claude_client
            return await create_claude_client(config)
        elif provider.lower() == "openai":
            # Vérifier si openai_client existe
            try:
                from gbpbot.ai.openai_client import create_openai_client
                return await create_openai_client(config)
            except ImportError:
                logger.warning("Module OpenAI non disponible, utilisation de Claude")
                from gbpbot.ai.claude_client import create_claude_client
                return await create_claude_client(config)
        elif provider.lower() == "llama":
            # Vérifier si llama_client existe
            try:
                from gbpbot.ai.llama_client import create_llama_client
                return await create_llama_client(config)
            except ImportError:
                logger.warning("Module LLaMA non disponible, utilisation de Claude")
                from gbpbot.ai.claude_client import create_claude_client
                return await create_claude_client(config)
        else:
            logger.warning(f"Fournisseur IA inconnu: {provider}, utilisation de Claude par défaut")
            from gbpbot.ai.claude_client import create_claude_client
            return await create_claude_client(config)
    except Exception as e:
        logger.error(f"Erreur lors de la création du client IA {provider}: {str(e)}")
        # Fallback à un fournisseur disponible en cas d'erreur
        try:
            if provider != "claude":
                logger.info("Tentative de fallback vers Claude")
                from gbpbot.ai.claude_client import create_claude_client
                return await create_claude_client(config)
            if provider != "openai":
                logger.info("Tentative de fallback vers OpenAI")
                try:
                    from gbpbot.ai.openai_client import create_openai_client
                    return await create_openai_client(config)
                except ImportError:
                    pass
        except Exception:
            pass
        
        logger.error("Impossible de créer un client IA fonctionnel")
        return None

async def create_market_intelligence(config: Optional[Dict[str, Any]] = None):
    """
    Crée un système d'intelligence de marché basé sur l'IA pour l'analyse
    et la prise de décision automatisée.
    
    Args:
        config: Configuration du système d'intelligence
        
    Returns:
        Système d'intelligence de marché
    """
    # Import dynamique pour éviter les dépendances circulaires
    from gbpbot.ai.market_intelligence import create_market_intelligence as create_mi
    return await create_mi(config)

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
    "is_gpu_available",
    "create_market_intelligence"
] 