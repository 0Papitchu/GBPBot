 #!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Interface de Base pour les Sniper de Tokens
==========================================

Ce module définit l'interface abstraite que tous les sniper de tokens
doivent implémenter pour assurer une uniformité dans le comportement
et faciliter l'interchangeabilité des modules.
"""

import abc
import logging
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime

class BaseSniper(abc.ABC):
    """
    Classe abstraite définissant l'interface pour tous les sniper de tokens.
    
    Cette interface assure que tous les sniper de tokens, quelle que soit
    la blockchain ciblée, implémentent un ensemble commun de méthodes.
    """
    
    @abc.abstractmethod
    async def initialize(self, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Initialise le sniper avec une configuration spécifique.
        
        Args:
            config: Configuration du sniper (optionnel)
            
        Returns:
            bool: True si l'initialisation a réussi, False sinon
        """
        pass
    
    @abc.abstractmethod
    async def start(self) -> bool:
        """
        Démarre le processus de sniping.
        
        Returns:
            bool: True si le démarrage a réussi, False sinon
        """
        pass
    
    @abc.abstractmethod
    async def stop(self) -> bool:
        """
        Arrête le processus de sniping.
        
        Returns:
            bool: True si l'arrêt a réussi, False sinon
        """
        pass
    
    @abc.abstractmethod
    async def pause(self) -> bool:
        """
        Met en pause le processus de sniping sans le stopper complètement.
        
        Returns:
            bool: True si la mise en pause a réussi, False sinon
        """
        pass
    
    @abc.abstractmethod
    async def resume(self) -> bool:
        """
        Reprend le processus de sniping après une pause.
        
        Returns:
            bool: True si la reprise a réussi, False sinon
        """
        pass
    
    @abc.abstractmethod
    async def analyze_token(self, token_address: str, blockchain: str) -> Dict[str, Any]:
        """
        Analyse un token pour déterminer s'il est intéressant à acheter.
        
        Args:
            token_address: Adresse du token à analyser
            blockchain: Blockchain sur laquelle se trouve le token
            
        Returns:
            Dict[str, Any]: Résultat de l'analyse avec score et recommandation
        """
        pass
    
    @abc.abstractmethod
    async def buy_token(self, token_address: str, amount: float, blockchain: str, 
                         max_slippage: Optional[float] = None) -> Dict[str, Any]:
        """
        Achète un token après analyse positive.
        
        Args:
            token_address: Adresse du token à acheter
            amount: Montant à investir
            blockchain: Blockchain sur laquelle se trouve le token
            max_slippage: Slippage maximum autorisé en pourcentage (optionnel)
            
        Returns:
            Dict[str, Any]: Résultat de l'achat avec transaction hash et statut
        """
        pass
    
    @abc.abstractmethod
    async def sell_token(self, token_address: str, percentage: float, blockchain: str,
                          max_slippage: Optional[float] = None) -> Dict[str, Any]:
        """
        Vend un token précédemment acheté.
        
        Args:
            token_address: Adresse du token à vendre
            percentage: Pourcentage de la position à vendre (0-100)
            blockchain: Blockchain sur laquelle se trouve le token
            max_slippage: Slippage maximum autorisé en pourcentage (optionnel)
            
        Returns:
            Dict[str, Any]: Résultat de la vente avec transaction hash et statut
        """
        pass
    
    @abc.abstractmethod
    async def get_token_balance(self, token_address: str, blockchain: str) -> Dict[str, Any]:
        """
        Récupère le solde d'un token spécifique dans le portefeuille.
        
        Args:
            token_address: Adresse du token
            blockchain: Blockchain sur laquelle se trouve le token
            
        Returns:
            Dict[str, Any]: Solde avec informations supplémentaires (valeur estimée, etc.)
        """
        pass
    
    @abc.abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """
        Récupère les statistiques du sniper.
        
        Returns:
            Dict[str, Any]: Statistiques détaillées du sniper
        """
        pass
    
    @abc.abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """
        Récupère l'état actuel du sniper.
        
        Returns:
            Dict[str, Any]: État actuel du sniper (actif, en pause, arrêté, etc.)
        """
        pass
    
    @abc.abstractmethod
    async def configure(self, new_config: Dict[str, Any]) -> bool:
        """
        Met à jour la configuration du sniper.
        
        Args:
            new_config: Nouvelle configuration à appliquer
            
        Returns:
            bool: True si la mise à jour a réussi, False sinon
        """
        pass