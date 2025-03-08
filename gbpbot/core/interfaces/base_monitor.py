#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Interface de Base pour les Moniteurs de Ressources et Performance
===============================================================

Ce module définit l'interface abstraite que tous les moniteurs
doivent implémenter pour assurer une uniformité dans le comportement
et faciliter l'interchangeabilité des modules.
"""

import abc
import logging
from typing import Dict, List, Any, Optional, Union, Tuple, Callable
from datetime import datetime
from enum import Enum, auto

class MonitoringType(Enum):
    """Énumération des types de monitoring disponibles."""
    SYSTEM = auto()         # Monitoring système (CPU, RAM, etc.)
    NETWORK = auto()        # Monitoring réseau (latence, bande passante)
    TRADING = auto()        # Monitoring des transactions de trading
    PERFORMANCE = auto()    # Monitoring des performances (temps d'exécution)
    BLOCKCHAIN = auto()     # Monitoring blockchain (mempool, gas)
    SECURITY = auto()       # Monitoring de sécurité (détection d'anomalies)
    ALL = auto()            # Tous les types de monitoring

class BaseMonitor(abc.ABC):
    """
    Classe abstraite définissant l'interface pour tous les moniteurs.
    
    Cette interface assure que tous les moniteurs, quel que soit
    le type, implémentent un ensemble commun de méthodes.
    """
    
    @abc.abstractmethod
    def initialize(self, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Initialise le moniteur avec une configuration spécifique.
        
        Args:
            config: Configuration optionnelle pour le moniteur
            
        Returns:
            True si l'initialisation a réussi, False sinon
        """
        pass
    
    @abc.abstractmethod
    def start(self, monitoring_types: Optional[List[MonitoringType]] = None) -> bool:
        """
        Démarre le monitoring des ressources spécifiées.
        
        Args:
            monitoring_types: Types de monitoring à activer (par défaut: tous)
            
        Returns:
            True si le démarrage a réussi, False sinon
        """
        pass
    
    @abc.abstractmethod
    def stop(self, monitoring_types: Optional[List[MonitoringType]] = None) -> bool:
        """
        Arrête le monitoring des ressources spécifiées.
        
        Args:
            monitoring_types: Types de monitoring à désactiver (par défaut: tous)
            
        Returns:
            True si l'arrêt a réussi, False sinon
        """
        pass
    
    @abc.abstractmethod
    def pause(self, monitoring_types: Optional[List[MonitoringType]] = None) -> bool:
        """
        Met en pause le monitoring des ressources spécifiées
        sans arrêter complètement le système.
        
        Args:
            monitoring_types: Types de monitoring à mettre en pause (par défaut: tous)
            
        Returns:
            True si la mise en pause a réussi, False sinon
        """
        pass
    
    @abc.abstractmethod
    def resume(self, monitoring_types: Optional[List[MonitoringType]] = None) -> bool:
        """
        Reprend le monitoring des ressources spécifiées après une pause.
        
        Args:
            monitoring_types: Types de monitoring à reprendre (par défaut: tous)
            
        Returns:
            True si la reprise a réussi, False sinon
        """
        pass
    
    @abc.abstractmethod
    def get_current_metrics(self, monitoring_types: Optional[List[MonitoringType]] = None) -> Dict[str, Any]:
        """
        Récupère les métriques actuelles du système.
        
        Args:
            monitoring_types: Types de monitoring dont on veut les métriques (par défaut: tous)
            
        Returns:
            Dictionnaire contenant les métriques actuelles
        """
        pass
    
    @abc.abstractmethod
    def get_metrics_history(self, 
                           start_time: Optional[datetime] = None,
                           end_time: Optional[datetime] = None,
                           monitoring_types: Optional[List[MonitoringType]] = None,
                           aggregation: Optional[str] = None) -> Dict[str, Any]:
        """
        Récupère l'historique des métriques sur une période donnée.
        
        Args:
            start_time: Début de la période (par défaut: 1 heure avant now)
            end_time: Fin de la période (par défaut: now)
            monitoring_types: Types de monitoring dont on veut l'historique
            aggregation: Méthode d'agrégation des données (avg, min, max, sum)
            
        Returns:
            Dictionnaire contenant l'historique des métriques
        """
        pass
    
    @abc.abstractmethod
    def set_alert_threshold(self, metric_name: str, threshold: float, 
                           callback: Optional[Callable[[str, float, float], None]] = None) -> bool:
        """
        Définit un seuil d'alerte pour une métrique spécifique.
        
        Args:
            metric_name: Nom de la métrique
            threshold: Valeur du seuil
            callback: Fonction à appeler lorsque le seuil est dépassé
            
        Returns:
            True si le seuil a été défini avec succès, False sinon
        """
        pass
    
    @abc.abstractmethod
    def remove_alert_threshold(self, metric_name: str) -> bool:
        """
        Supprime un seuil d'alerte pour une métrique spécifique.
        
        Args:
            metric_name: Nom de la métrique
            
        Returns:
            True si le seuil a été supprimé avec succès, False sinon
        """
        pass
    
    @abc.abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """
        Récupère l'état actuel du moniteur.
        
        Returns:
            État actuel du moniteur
        """
        pass
    
    @abc.abstractmethod
    def configure(self, new_config: Dict[str, Any]) -> bool:
        """
        Reconfigure le moniteur pendant son fonctionnement.
        
        Args:
            new_config: Nouvelle configuration à appliquer
            
        Returns:
            True si la reconfiguration a réussi, False sinon
        """
        pass
    
    @abc.abstractmethod
    def get_recommendations(self) -> Dict[str, Any]:
        """
        Récupère des recommandations d'optimisation basées sur les métriques.
        
        Returns:
            Dictionnaire contenant des recommandations d'optimisation
        """
        pass 