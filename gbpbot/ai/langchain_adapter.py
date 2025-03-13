"""
Module LangChainAdapter - Adaptateur pour l'intégration avec LangChain

Ce module fournit des adaptateurs pour intégrer nos fournisseurs de LLM
existants (Claude, OpenAI, LLaMA) avec LangChain, permettant leur utilisation
dans le système d'agents LangChain.
"""

import os
import json
import asyncio
import logging
from typing import Dict, List, Any, Optional, Union, Mapping, Callable
from functools import partial

# Importations LangChain
from langchain.llms.base import LLM
from langchain.callbacks.manager import CallbackManagerForLLMRun
from langchain.schema import AIMessage, HumanMessage, SystemMessage
from langchain.schema.output import Generation, LLMResult
from langchain.tools import BaseTool

# Importations internes
from gbpbot.utils.logger import setup_logger
from gbpbot.ai.llm_provider import get_ai_client, LLMProvider, AiClientResponseFormat

# Configuration du logger
logger = setup_logger("langchain_adapter", logging.INFO)

class LLMProviderAdapter(LLM):
    """
    Adaptateur pour utiliser nos fournisseurs LLM personnalisés avec LangChain.
    
    Cette classe adapte notre interface LLMProvider à l'interface LLM de LangChain,
    permettant d'utiliser nos intégrations existantes (Claude, OpenAI, LLaMA) avec 
    LangChain.
    """
    
    llm_provider: LLMProvider
    """Le fournisseur LLM sous-jacent"""
    
    max_tokens: int = 4096
    """Nombre maximal de tokens dans la réponse"""
    
    temperature: float = 0.7
    """Température pour la génération (0.0-1.0)"""
    
    def __init__(
        self, 
        llm_provider: Optional[LLMProvider] = None,
        **kwargs: Any
    ):
        """
        Initialise l'adaptateur LLMProviderAdapter.
        
        Args:
            llm_provider: Fournisseur LLM personnalisé à adapter
            **kwargs: Arguments supplémentaires pour LLM
        """
        super().__init__(**kwargs)
        
        self.llm_provider = llm_provider
        
        # Charger le provider depuis le cache si non fourni
        if self.llm_provider is None:
            # Note: get_ai_client est normalement asynchrone, mais nous devons l'appeler
            # de manière synchrone ici pour la compatibilité avec LangChain
            try:
                # Utiliser une future pour exécuter la fonction asynchrone de manière synchrone
                async def async_get_client():
                    return await get_ai_client()
                
                loop = asyncio.get_event_loop()
                self.llm_provider = loop.run_until_complete(async_get_client())
            except Exception as e:
                logger.error(f"Erreur lors de l'initialisation du provider LLM: {str(e)}")
                self.llm_provider = None
        
        if self.llm_provider:
            # Définir les attributs en fonction du provider
            self.provider_name = self.llm_provider.provider
            self.model_name = getattr(self.llm_provider, "model", "unknown")
            
            # Configurer les paramètres par défaut
            if hasattr(self.llm_provider, "capabilities"):
                self.max_tokens = getattr(self.llm_provider.capabilities, "max_tokens", 4096)
    
    @property
    def _llm_type(self) -> str:
        """Type de LLM pour LangChain."""
        return f"gbpbot-{self.provider_name}" if self.llm_provider else "gbpbot-unknown"
    
    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """
        Méthode principale de LangChain LLM pour générer une réponse.
        
        Args:
            prompt: Prompt à envoyer au modèle
            stop: Séquences pour arrêter la génération
            run_manager: Gestionnaire de callbacks pour LLM (LangChain)
            **kwargs: Arguments supplémentaires pour la génération
            
        Returns:
            Texte généré par le modèle
        """
        if not self.llm_provider:
            raise ValueError("LLMProvider non initialisé")
        
        # Fusionner les paramètres par défaut avec ceux fournis
        params = {
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stop_sequences": stop,
            **kwargs
        }
        
        # Exécuter la génération de manière synchrone
        try:
            async def async_generate():
                return await self.llm_provider.generate(
                    prompt=prompt,
                    **{k: v for k, v in params.items() if v is not None}
                )
            
            loop = asyncio.get_event_loop()
            response = loop.run_until_complete(async_generate())
            
            return response.content
        except Exception as e:
            logger.error(f"Erreur lors de la génération avec {self._llm_type}: {str(e)}")
            return f"Erreur: {str(e)}"
    
    @property
    def _identifying_params(self) -> Mapping[str, Any]:
        """Paramètres d'identification pour LangChain."""
        return {
            "provider_name": getattr(self, "provider_name", "unknown"),
            "model_name": getattr(self, "model_name", "unknown"),
            "max_tokens": self.max_tokens,
            "temperature": self.temperature
        }

class GBPBotTool(BaseTool):
    """
    Outil GBPBot pour LangChain.
    
    Cette classe permet d'adapter les fonctions du GBPBot pour être utilisées
    comme outils dans l'agent LangChain.
    """
    
    name: str = ""
    """Nom de l'outil"""
    
    description: str = ""
    """Description de l'outil"""
    
    func: Callable[..., Any] = None
    """Fonction à exécuter"""
    
    async_func: bool = True
    """Indique si la fonction est asynchrone"""
    
    def __init__(
        self,
        name: str,
        description: str,
        func: Callable[..., Any],
        async_func: bool = True,
        **kwargs: Any
    ):
        """
        Initialise un outil GBPBot pour LangChain.
        
        Args:
            name: Nom de l'outil
            description: Description de l'outil
            func: Fonction à exécuter
            async_func: Indique si la fonction est asynchrone
            **kwargs: Arguments supplémentaires
        """
        self.name = name
        self.description = description
        self.func = func
        self.async_func = async_func
        
        super().__init__(name=name, description=description, **kwargs)
    
    def _run(
        self,
        *args: Any,
        **kwargs: Any
    ) -> Any:
        """
        Exécute l'outil de manière synchrone.
        
        Args:
            *args: Arguments positionnels
            **kwargs: Arguments nommés
            
        Returns:
            Résultat de l'exécution
        """
        if self.async_func:
            # Convertir la fonction asynchrone en synchrone
            async def run_async():
                return await self.func(*args, **kwargs)
            
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(run_async())
        else:
            # Exécuter directement la fonction synchrone
            return self.func(*args, **kwargs)
    
    async def _arun(
        self,
        *args: Any,
        **kwargs: Any
    ) -> Any:
        """
        Exécute l'outil de manière asynchrone.
        
        Args:
            *args: Arguments positionnels
            **kwargs: Arguments nommés
            
        Returns:
            Résultat de l'exécution
        """
        if self.async_func:
            # Exécuter directement la fonction asynchrone
            return await self.func(*args, **kwargs)
        else:
            # Convertir la fonction synchrone en asynchrone
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                partial(self.func, *args, **kwargs)
            )

async def create_langchain_llm(
    llm_provider: Optional[LLMProvider] = None,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None
) -> LLMProviderAdapter:
    """
    Crée et initialise un adaptateur LLM pour LangChain.
    
    Args:
        llm_provider: Fournisseur LLM personnalisé à adapter
        temperature: Température pour la génération (0.0-1.0)
        max_tokens: Nombre maximal de tokens dans la réponse
        
    Returns:
        Instance de LLMProviderAdapter initialisée
    """
    # Obtenir un client AI si non fourni
    if llm_provider is None:
        llm_provider = await get_ai_client()
    
    # Créer l'adaptateur
    adapter = LLMProviderAdapter(
        llm_provider=llm_provider,
        temperature=temperature
    )
    
    # Configurer max_tokens si spécifié
    if max_tokens is not None:
        adapter.max_tokens = max_tokens
    
    return adapter 