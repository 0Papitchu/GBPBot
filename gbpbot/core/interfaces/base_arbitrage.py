#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Interface de Base pour les Stratégies d'Arbitrage
================================================

Ce module définit l'interface abstraite que toutes les stratégies d'arbitrage
doivent implémenter pour assurer une uniformité dans le comportement
et faciliter l'interchangeabilité des modules.
"""

import abc
import logging
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime
from dataclasses import dataclass

@dataclass
class ArbitrageOpportunity:
    """Représente une opportunité d'arbitrage standardisée."""
    
    id: str
    timestamp: datetime
    blockchain: str
    
    # Éléments communs à tous les types d'arbitrage
    token_address: str
    token_symbol: str
    
    # Plateformes impliquées (DEX, CEX, etc.)
    platform_from: str
    platform_to: str
    
    # Informations de prix
    buy_price: float
    sell_price: float
    price_difference: float
    price_difference_percent: float
    
    # Informations de profit estimé
    estimated_profit_usd: float
    estimated_gas_cost_usd: float
    net_profit_usd: float
    
    # Montant d'entrée
    input_amount_usd: float
    
    # Informations sur les pools (optionnelles)
    liquidity_from_usd: Optional[float] = None
    liquidity_to_usd: Optional[float] = None
    
    # Route spécifique (si applicable)
    route: Optional[List[Dict[str, Any]]] = None
    
    # Type d'arbitrage
    arbitrage_type: str = "standard"  # standard, triangular, cross-chain, cex-dex
    
    # Informations supplémentaires spécifiques au type d'arbitrage
    additional_info: Optional[Dict[str, Any]] = None

class BaseArbitrage(abc.ABC):
    """
    Classe abstraite définissant l'interface pour toutes les stratégies d'arbitrage.
    
    Cette interface assure que toutes les stratégies d'arbitrage, quel que soit
    le type (DEX-DEX, CEX-DEX, cross-chain, triangulaire, etc.), implémentent
    un ensemble commun de méthodes.
    """
    
    @abc.abstractmethod
    async def initialize(self, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Initialise la stratégie d'arbitrage avec une configuration spécifique.
        
        Args:
            config: Configuration optionnelle pour la stratégie
            
        Returns:
            True si l'initialisation a réussi, False sinon
        """
        pass
    
    @abc.abstractmethod
    async def start(self) -> bool:
        """
        Démarre la surveillance des opportunités d'arbitrage.
        
        Returns:
            True si le démarrage a réussi, False sinon
        """
        pass
    
    @abc.abstractmethod
    async def stop(self) -> bool:
        """
        Arrête la surveillance des opportunités d'arbitrage.
        
        Returns:
            True si l'arrêt a réussi, False sinon
        """
        pass
    
    @abc.abstractmethod
    async def pause(self) -> bool:
        """
        Met en pause la surveillance des opportunités d'arbitrage
        sans arrêter complètement le système.
        
        Returns:
            True si la mise en pause a réussi, False sinon
        """
        pass
    
    @abc.abstractmethod
    async def resume(self) -> bool:
        """
        Reprend la surveillance des opportunités d'arbitrage après une pause.
        
        Returns:
            True si la reprise a réussi, False sinon
        """
        pass
    
    @abc.abstractmethod
    async def find_opportunities(self, params: Optional[Dict[str, Any]] = None) -> List[ArbitrageOpportunity]:
        """
        Recherche des opportunités d'arbitrage avec les paramètres spécifiés.
        
        Args:
            params: Paramètres optionnels pour la recherche d'opportunités
            
        Returns:
            Liste des opportunités d'arbitrage trouvées
        """
        pass
    
    @abc.abstractmethod
    async def execute_arbitrage(self, opportunity_id: str) -> Dict[str, Any]:
        """
        Exécute une opportunité d'arbitrage spécifique.
        
        Args:
            opportunity_id: Identifiant de l'opportunité à exécuter
            
        Returns:
            Résultat de l'exécution avec détails sur la transaction
        """
        pass
    
    @abc.abstractmethod
    async def validate_opportunity(self, opportunity: ArbitrageOpportunity) -> Dict[str, Any]:
        """
        Valide une opportunité d'arbitrage avant exécution.
        
        Args:
            opportunity: Opportunité à valider
            
        Returns:
            Résultat de la validation avec score et recommandation
        """
        pass
    
    @abc.abstractmethod
    async def estimate_profit(self, opportunity: ArbitrageOpportunity, 
                              amount: Optional[float] = None) -> Dict[str, Any]:
        """
        Estime le profit potentiel d'une opportunité d'arbitrage.
        
        Args:
            opportunity: Opportunité à évaluer
            amount: Montant optionnel à utiliser pour l'arbitrage
            
        Returns:
            Estimation détaillée du profit
        """
        pass
    
    @abc.abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """
        Récupère les statistiques de la stratégie d'arbitrage.
        
        Returns:
            Statistiques de la stratégie
        """
        pass
    
    @abc.abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """
        Récupère l'état actuel de la stratégie d'arbitrage.
        
        Returns:
            État actuel de la stratégie
        """
        pass
    
    @abc.abstractmethod
    async def configure(self, new_config: Dict[str, Any]) -> bool:
        """
        Reconfigure la stratégie d'arbitrage pendant son fonctionnement.
        
        Args:
            new_config: Nouvelle configuration à appliquer
            
        Returns:
            True si la reconfiguration a réussi, False sinon
        """
        pass 