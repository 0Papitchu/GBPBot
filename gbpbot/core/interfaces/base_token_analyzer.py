#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Interface de Base pour les Analyseurs de Tokens
==============================================

Ce module définit l'interface abstraite que tous les analyseurs de tokens
doivent implémenter pour assurer une uniformité dans le comportement
et faciliter l'interchangeabilité des modules.
"""

import abc
import logging
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime
from enum import Enum, auto

class TokenRiskLevel(Enum):
    """Énumération des niveaux de risque pour les tokens."""
    SAFE = auto()         # Token sûr, risque minimal
    LOW_RISK = auto()     # Risque faible
    MEDIUM_RISK = auto()  # Risque moyen
    HIGH_RISK = auto()    # Risque élevé
    VERY_HIGH_RISK = auto() # Risque très élevé
    SCAM = auto()         # Arnaque confirmée
    UNKNOWN = auto()      # Risque inconnu

class TokenAnalysisAspect(Enum):
    """Énumération des aspects d'analyse pour les tokens."""
    CONTRACT_CODE = auto()         # Analyse du code du contrat
    LIQUIDITY = auto()            # Analyse de la liquidité
    TRADING_ACTIVITY = auto()     # Analyse de l'activité de trading
    SOCIAL_MEDIA = auto()         # Analyse des réseaux sociaux
    DEVELOPER_ACTIVITY = auto()   # Analyse de l'activité des développeurs
    DISTRIBUTION = auto()         # Analyse de la distribution des tokens
    MARKET_CAP = auto()           # Analyse de la capitalisation boursière
    SECURITY = auto()             # Analyse des aspects de sécurité
    ALL = auto()                  # Tous les aspects

class BaseTokenAnalyzer(abc.ABC):
    """
    Classe abstraite définissant l'interface pour tous les analyseurs de tokens.
    
    Cette interface assure que tous les analyseurs de tokens, quel que soit
    le type d'analyse ou la blockchain ciblée, implémentent un ensemble
    commun de méthodes.
    """
    
    @abc.abstractmethod
    async def initialize(self, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Initialise l'analyseur avec une configuration spécifique.
        
        Args:
            config: Configuration optionnelle pour l'analyseur
            
        Returns:
            True si l'initialisation a réussi, False sinon
        """
        pass
    
    @abc.abstractmethod
    async def analyze_token(self, token_address: str, blockchain: str,
                           aspects: Optional[List[TokenAnalysisAspect]] = None) -> Dict[str, Any]:
        """
        Analyse un token selon les aspects spécifiés.
        
        Args:
            token_address: Adresse du token à analyser
            blockchain: Blockchain sur laquelle se trouve le token
            aspects: Aspects à analyser (par défaut: tous)
            
        Returns:
            Résultats détaillés de l'analyse
        """
        pass
    
    @abc.abstractmethod
    async def validate_token(self, token_address: str, blockchain: str) -> Dict[str, Any]:
        """
        Valide la sécurité d'un token et détecte les risques potentiels.
        
        Args:
            token_address: Adresse du token à valider
            blockchain: Blockchain sur laquelle se trouve le token
            
        Returns:
            Résultat de la validation avec niveau de risque et détails
        """
        pass
    
    @abc.abstractmethod
    async def analyze_contract_code(self, token_address: str, blockchain: str) -> Dict[str, Any]:
        """
        Analyse spécifiquement le code du contrat du token.
        
        Args:
            token_address: Adresse du token dont on veut analyser le contrat
            blockchain: Blockchain sur laquelle se trouve le token
            
        Returns:
            Résultats de l'analyse du code du contrat
        """
        pass
    
    @abc.abstractmethod
    async def check_rugpull_risk(self, token_address: str, blockchain: str) -> Dict[str, Any]:
        """
        Vérifie spécifiquement le risque de rug pull pour un token.
        
        Args:
            token_address: Adresse du token à vérifier
            blockchain: Blockchain sur laquelle se trouve le token
            
        Returns:
            Évaluation du risque de rug pull avec détails
        """
        pass
    
    @abc.abstractmethod
    async def check_honeypot_risk(self, token_address: str, blockchain: str) -> Dict[str, Any]:
        """
        Vérifie spécifiquement le risque de honeypot pour un token.
        
        Args:
            token_address: Adresse du token à vérifier
            blockchain: Blockchain sur laquelle se trouve le token
            
        Returns:
            Évaluation du risque de honeypot avec détails
        """
        pass
    
    @abc.abstractmethod
    async def get_token_metrics(self, token_address: str, blockchain: str) -> Dict[str, Any]:
        """
        Récupère les métriques clés d'un token.
        
        Args:
            token_address: Adresse du token
            blockchain: Blockchain sur laquelle se trouve le token
            
        Returns:
            Métriques clés du token
        """
        pass
    
    @abc.abstractmethod
    async def simulate_token_transaction(self, token_address: str, blockchain: str,
                                     action: str, amount: float) -> Dict[str, Any]:
        """
        Simule une transaction sur un token pour vérifier sa légitimité.
        
        Args:
            token_address: Adresse du token
            blockchain: Blockchain sur laquelle se trouve le token
            action: Type de transaction à simuler ('buy' ou 'sell')
            amount: Montant à utiliser pour la simulation
            
        Returns:
            Résultats de la simulation avec détails
        """
        pass
    
    @abc.abstractmethod
    def get_token_score(self, token_address: str, blockchain: str) -> Dict[str, Any]:
        """
        Calcule un score global pour un token basé sur les analyses précédentes.
        
        Args:
            token_address: Adresse du token
            blockchain: Blockchain sur laquelle se trouve le token
            
        Returns:
            Score global et détails par catégorie
        """
        pass
    
    @abc.abstractmethod
    def configure(self, new_config: Dict[str, Any]) -> bool:
        """
        Reconfigure l'analyseur pendant son fonctionnement.
        
        Args:
            new_config: Nouvelle configuration à appliquer
            
        Returns:
            True si la reconfiguration a réussi, False sinon
        """
        pass 