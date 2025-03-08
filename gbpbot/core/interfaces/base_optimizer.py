#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Interface de Base pour les Optimisateurs
=======================================

Ce module définit l'interface abstraite que tous les optimisateurs
doivent implémenter pour assurer une uniformité dans le comportement
et faciliter l'interchangeabilité des modules.
"""

import abc
import logging
from typing import Dict, List, Any, Optional, Union, Tuple, Callable
from enum import Enum, auto

class OptimizationType(Enum):
    """Énumération des types d'optimisation disponibles."""
    CPU = auto()          # Optimisation du CPU
    MEMORY = auto()       # Optimisation de la mémoire
    GPU = auto()          # Optimisation du GPU
    NETWORK = auto()      # Optimisation du réseau
    STORAGE = auto()      # Optimisation du stockage
    TRADING = auto()      # Optimisation des stratégies de trading
    GAS = auto()          # Optimisation des coûts de gaz
    MEV = auto()          # Optimisation Maximum Extractable Value
    ALL = auto()          # Tous les types d'optimisation

class OptimizationProfile(Enum):
    """Énumération des profils d'optimisation prédéfinis."""
    BALANCED = auto()     # Équilibre entre performance et consommation
    PERFORMANCE = auto()  # Priorité à la performance maximale
    EFFICIENCY = auto()   # Priorité à l'efficacité énergétique
    LOW_MEMORY = auto()   # Optimisé pour une faible utilisation mémoire
    STEALTH = auto()      # Optimisé pour une faible détectabilité
    TRADING = auto()      # Optimisé pour le trading haute fréquence
    CUSTOM = auto()       # Profil personnalisé

class BaseOptimizer(abc.ABC):
    """
    Classe abstraite définissant l'interface pour tous les optimisateurs.
    
    Cette interface assure que tous les optimisateurs, quel que soit
    le type, implémentent un ensemble commun de méthodes.
    """
    
    @abc.abstractmethod
    def initialize(self, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Initialise l'optimisateur avec une configuration spécifique.
        
        Args:
            config: Configuration optionnelle pour l'optimisateur
            
        Returns:
            True si l'initialisation a réussi, False sinon
        """
        pass
    
    @abc.abstractmethod
    def apply_optimizations(self, optimization_types: Optional[List[OptimizationType]] = None) -> bool:
        """
        Applique les optimisations spécifiées.
        
        Args:
            optimization_types: Types d'optimisation à appliquer (par défaut: tous)
            
        Returns:
            True si l'application a réussi, False sinon
        """
        pass
    
    @abc.abstractmethod
    def revert_optimizations(self, optimization_types: Optional[List[OptimizationType]] = None) -> bool:
        """
        Annule les optimisations spécifiées et revient aux paramètres par défaut.
        
        Args:
            optimization_types: Types d'optimisation à annuler (par défaut: tous)
            
        Returns:
            True si l'annulation a réussi, False sinon
        """
        pass
    
    @abc.abstractmethod
    def load_optimization_profile(self, profile: Union[str, OptimizationProfile]) -> bool:
        """
        Charge un profil d'optimisation prédéfini ou personnalisé.
        
        Args:
            profile: Nom du profil à charger ou énumération OptimizationProfile
            
        Returns:
            True si le chargement a réussi, False sinon
        """
        pass
    
    @abc.abstractmethod
    def save_optimization_profile(self, name: str) -> bool:
        """
        Sauvegarde les optimisations actuelles sous forme de profil personnalisé.
        
        Args:
            name: Nom du profil à sauvegarder
            
        Returns:
            True si la sauvegarde a réussi, False sinon
        """
        pass
    
    @abc.abstractmethod
    def get_hardware_info(self) -> Dict[str, Any]:
        """
        Récupère les informations sur le matériel.
        
        Returns:
            Dictionnaire contenant les informations sur le matériel
        """
        pass
    
    @abc.abstractmethod
    def get_optimization_status(self) -> Dict[str, Any]:
        """
        Récupère l'état actuel des optimisations.
        
        Returns:
            Dictionnaire contenant l'état des optimisations
        """
        pass
    
    @abc.abstractmethod
    def get_optimization_metrics(self) -> Dict[str, Any]:
        """
        Récupère les métriques d'optimisation (gains de performance, etc.).
        
        Returns:
            Dictionnaire contenant les métriques d'optimisation
        """
        pass
    
    @abc.abstractmethod
    def start_monitoring(self) -> bool:
        """
        Démarre la surveillance des performances pour une optimisation continue.
        
        Returns:
            True si le démarrage a réussi, False sinon
        """
        pass
    
    @abc.abstractmethod
    def stop_monitoring(self) -> bool:
        """
        Arrête la surveillance des performances.
        
        Returns:
            True si l'arrêt a réussi, False sinon
        """
        pass
    
    @abc.abstractmethod
    def get_recommendations(self) -> List[str]:
        """
        Récupère des recommandations d'optimisation supplémentaires.
        
        Returns:
            Liste de recommandations d'optimisation
        """
        pass
    
    @abc.abstractmethod
    def configure(self, new_config: Dict[str, Any]) -> bool:
        """
        Reconfigure l'optimisateur pendant son fonctionnement.
        
        Args:
            new_config: Nouvelle configuration à appliquer
            
        Returns:
            True si la reconfiguration a réussi, False sinon
        """
        pass
    
    @abc.abstractmethod
    def optimize_for_activity(self, activity_type: str, 
                             params: Optional[Dict[str, Any]] = None) -> bool:
        """
        Optimise spécifiquement pour un type d'activité particulier.
        
        Args:
            activity_type: Type d'activité (sniping, arbitrage, etc.)
            params: Paramètres optionnels pour l'optimisation
            
        Returns:
            True si l'optimisation a réussi, False sinon
        """
        pass 