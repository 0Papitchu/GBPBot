#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Interface abstraite pour les fournisseurs de modèles de langage (LLM)
====================================================================

Cette classe définit l'interface commune que tous les fournisseurs de LLM
doivent implémenter pour s'intégrer avec GBPBot.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union, Tuple

class LLMProvider(ABC):
    """
    Interface abstraite pour les fournisseurs de modèles de langage (LLM).
    
    Chaque implémentation concrète (OpenAI, LLaMA, etc.) doit étendre cette classe
    et implémenter ses méthodes abstraites pour fournir des fonctionnalités
    spécifiques au fournisseur.
    """
    
    @abstractmethod
    def generate_text(
        self, 
        prompt: str,
        max_tokens: int = 500,
        temperature: float = 0.7,
        system_message: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Génère du texte à partir du prompt fourni.
        
        Args:
            prompt: Le texte d'entrée pour guider la génération
            max_tokens: Nombre maximum de tokens à générer
            temperature: Contrôle de la randomité (0.0-1.0)
            system_message: Message système optionnel pour contextualiser
            **kwargs: Arguments supplémentaires spécifiques au modèle
            
        Returns:
            Le texte généré
            
        Raises:
            Exception: Si la génération échoue
        """
        pass
    
    @abstractmethod
    def generate_chat_response(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 500,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """
        Génère une réponse basée sur une conversation.
        
        Args:
            messages: Liste de messages (format: [{"role": "user|assistant|system", "content": "texte"}])
            max_tokens: Nombre maximum de tokens à générer
            temperature: Contrôle de la randomité (0.0-1.0)
            **kwargs: Arguments supplémentaires spécifiques au modèle
            
        Returns:
            La réponse générée
            
        Raises:
            Exception: Si la génération échoue
        """
        pass
    
    @abstractmethod
    def analyze_code(
        self,
        code: str,
        task: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Analyse du code source pour détecter des problèmes ou des opportunités.
        
        Args:
            code: Le code source à analyser
            task: Description de l'analyse à effectuer
            **kwargs: Arguments supplémentaires spécifiques au modèle
            
        Returns:
            Dictionnaire contenant les résultats de l'analyse
            
        Raises:
            Exception: Si l'analyse échoue
        """
        pass
    
    @abstractmethod
    def analyze_token_contract(
        self,
        contract_code: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Analyse un contrat de token pour détecter des problèmes de sécurité ou des fonctions malveillantes.
        
        Args:
            contract_code: Le code source du contrat
            **kwargs: Arguments supplémentaires
            
        Returns:
            Dictionnaire contenant le score de sécurité et les problèmes détectés
            
        Raises:
            Exception: Si l'analyse échoue
        """
        pass
    
    @abstractmethod
    def analyze_market_trend(
        self,
        market_data: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """
        Analyse des données de marché pour identifier des tendances.
        
        Args:
            market_data: Données de marché à analyser
            **kwargs: Arguments supplémentaires
            
        Returns:
            Dictionnaire contenant les tendances identifiées et recommandations
            
        Raises:
            Exception: Si l'analyse échoue
        """
        pass
    
    @abstractmethod
    def get_token_score(
        self,
        token_data: Dict[str, Any],
        **kwargs
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Évalue un token et génère un score de potentiel ou de risque.
        
        Args:
            token_data: Données du token à évaluer
            **kwargs: Arguments supplémentaires
            
        Returns:
            Tuple contenant (score, détails)
            
        Raises:
            Exception: Si l'évaluation échoue
        """
        pass
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Retourne le nom du fournisseur (openai, llama, etc.)"""
        pass
    
    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Vérifie si le fournisseur est disponible et fonctionnel"""
        pass
    
    @property
    @abstractmethod
    def capabilities(self) -> Dict[str, bool]:
        """
        Retourne un dictionnaire des capacités supportées par ce fournisseur.
        
        Par exemple:
        {
            "chat": True,
            "code_analysis": True,
            "token_contract_analysis": False,
            "market_analysis": True,
            "embeddings": False
        }
        """
        pass 