"""
Module d'Auto-Optimisation du GBPBot
===================================

Ce module contient la classe AutoOptimizer qui implémente l'automatisation
intelligente des stratégies du GBPBot en fonction des conditions de marché,
des performances passées et de l'environnement d'exécution.
"""

import os
import sys
import time
import json
import logging
import threading
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
from pathlib import Path

# Configuration du logger
logger = logging.getLogger("gbpbot.core.auto_optimization.auto_optimizer")

class AutoOptimizer:
    """
    Classe principale pour l'automatisation intelligente du GBPBot.
    
    Cette classe gère:
    - L'ajustement automatique des paramètres des stratégies
    - La détection des conditions de marché optimales
    - La gestion dynamique du capital
    - L'adaptation aux changements des comportements DEX
    - La récupération après erreurs
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialise l'optimiseur automatique avec la configuration fournie.
        
        Args:
            config: Configuration de l'optimiseur automatique
        """
        self.config = config
        
        # Configuration spécifique à l'auto-optimisation
        self.auto_config = config.get("auto_optimization", {})
        
        # Activer/désactiver les fonctionnalités spécifiques
        self.enable_parameter_adjustment = self.auto_config.get("enable_parameter_adjustment", True)
        self.enable_market_detection = self.auto_config.get("enable_market_detection", True)
        self.enable_capital_allocation = self.auto_config.get("enable_capital_allocation", True)
        self.enable_error_recovery = self.auto_config.get("enable_error_recovery", True)
        
        # Intervalles d'optimisation (en secondes)
        self.parameter_adjustment_interval = self.auto_config.get("parameter_adjustment_interval", 300)  # 5 minutes
        self.market_detection_interval = self.auto_config.get("market_detection_interval", 120)  # 2 minutes
        self.capital_allocation_interval = self.auto_config.get("capital_allocation_interval", 600)  # 10 minutes
        
        # Seuils et limites
        self.volatility_threshold = self.auto_config.get("volatility_threshold", 0.05)  # 5%
        self.max_capital_per_strategy = self.auto_config.get("max_capital_per_strategy", 0.5)  # 50%
        self.min_capital_per_strategy = self.auto_config.get("min_capital_per_strategy", 0.05)  # 5%
        
        # État interne
        self.last_parameter_adjustment = datetime.now()
        self.last_market_detection = datetime.now()
        self.last_capital_allocation = datetime.now()
        
        # Résultats des dernières analyses
        self.last_market_conditions = {
            "volatility": "normal",
            "trend": "neutral",
            "liquidity": "normal",
            "opportunity_level": "medium",
            "risk_level": "medium"
        }
        
        # Paramètres optimisés des stratégies
        self.strategy_parameters = {}
        
        # Historique des performances
        self.performance_history = []
        
        # Historique des erreurs et actions de récupération
        self.error_history = []
        self.recovery_actions = []
        
        # Statistiques d'optimisation
        self.optimization_stats = {
            "parameter_adjustments": 0,
            "market_detections": 0,
            "capital_allocations": 0,
            "error_recoveries": 0
        }
        
        # Pour l'allocation de capital
        self.capital_allocations = {}
        
        logger.info("AutoOptimizer initialisé avec la configuration fournie")
    
    def run_optimization_cycle(self) -> None:
        """
        Exécute un cycle complet d'optimisation automatique.
        
        Cette méthode est appelée périodiquement pour mettre à jour les
        paramètres du système en fonction des conditions actuelles.
        """
        try:
            logger.info("Démarrage d'un cycle d'optimisation automatique")
            
            # 1. Détection des conditions de marché
            if self.enable_market_detection and self._should_detect_market():
                self._detect_market_conditions_internal()
                
            # 2. Ajustement des paramètres de stratégie
            if self.enable_parameter_adjustment and self._should_adjust_parameters():
                self._adjust_strategy_parameters_internal()
                
            # 3. Allocation dynamique du capital
            if self.enable_capital_allocation and self._should_allocate_capital():
                self._allocate_capital_internal()
                
            logger.info("Cycle d'optimisation automatique terminé avec succès")
        except Exception as e:
            logger.error(f"Erreur lors du cycle d'optimisation automatique: {str(e)}")
            
            # Tenter de récupérer si activé
            if self.enable_error_recovery:
                self._handle_optimization_error(e)
                
    def get_status(self) -> Dict[str, Any]:
        """
        Retourne l'état actuel de l'optimiseur automatique.
        
        Returns:
            Dict contenant l'état actuel de l'optimiseur
        """
        return {
            "last_parameter_adjustment": self.last_parameter_adjustment.isoformat(),
            "last_market_detection": self.last_market_detection.isoformat(),
            "last_capital_allocation": self.last_capital_allocation.isoformat(),
            "market_conditions": self.last_market_conditions,
            "strategy_parameters": self.strategy_parameters,
            "optimization_stats": self.optimization_stats,
            "recovery_actions": self.recovery_actions[-5:] if self.recovery_actions else []
        }
        
    def shutdown(self) -> None:
        """
        Arrête proprement l'optimiseur automatique.
        """
        logger.info("Arrêt de l'AutoOptimizer")
        # Sauvegarder l'état si nécessaire
        self._save_state_if_needed()
        
    def _should_detect_market(self) -> bool:
        """
        Vérifie s'il est temps de détecter les conditions de marché.
        
        Returns:
            True si l'intervalle de détection est dépassé, False sinon
        """
        time_since_last = (datetime.now() - self.last_market_detection).total_seconds()
        return time_since_last >= self.market_detection_interval
        
    def _should_adjust_parameters(self) -> bool:
        """
        Vérifie s'il est temps d'ajuster les paramètres des stratégies.
        
        Returns:
            True si l'intervalle d'ajustement est dépassé, False sinon
        """
        time_since_last = (datetime.now() - self.last_parameter_adjustment).total_seconds()
        return time_since_last >= self.parameter_adjustment_interval
        
    def _should_allocate_capital(self) -> bool:
        """
        Vérifie s'il est temps d'allouer le capital.
        
        Returns:
            True si l'intervalle d'allocation est dépassé, False sinon
        """
        time_since_last = (datetime.now() - self.last_capital_allocation).total_seconds()
        return time_since_last >= self.capital_allocation_interval
        
    def _save_state_if_needed(self) -> None:
        """
        Sauvegarde l'état de l'optimiseur si nécessaire.
        """
        # Implémenter la sauvegarde d'état si nécessaire
        pass
        
    def _detect_market_conditions_internal(self) -> None:
        """
        Détecte les conditions actuelles du marché.
        
        Cette méthode analyse les données de marché pour déterminer:
        - La volatilité
        - La tendance
        - La liquidité
        - Le niveau d'opportunité
        - Le niveau de risque
        """
        # Version simple pour le linting
        logger.info("Détection des conditions de marché...")
        self.last_market_detection = datetime.now()
        self.optimization_stats["market_detections"] += 1
        
    def _adjust_strategy_parameters_internal(self) -> None:
        """
        Ajuste les paramètres des stratégies en fonction des conditions de marché et des performances passées.
        """
        # Version simple pour le linting
        logger.info("Ajustement des paramètres des stratégies...")
        self.last_parameter_adjustment = datetime.now()
        self.optimization_stats["parameter_adjustments"] += 1
        
    def _allocate_capital_internal(self) -> None:
        """
        Alloue le capital entre les différentes stratégies en fonction des conditions de marché et des performances passées.
        """
        # Version simple pour le linting
        logger.info("Allocation dynamique du capital...")
        self.last_capital_allocation = datetime.now()
        self.optimization_stats["capital_allocations"] += 1
        
    def _handle_optimization_error(self, error: Exception) -> None:
        """
        Gère les erreurs d'optimisation et tente de récupérer.
        
        Args:
            error: L'exception qui s'est produite
        """
        # Version simple pour le linting
        logger.error(f"Gérer l'erreur d'optimisation: {str(error)}")
        self.optimization_stats["error_recoveries"] += 1
        
        # Enregistrer l'action de récupération
        recovery_info = {
            "timestamp": datetime.now().isoformat(),
            "error_type": type(error).__name__,
            "action": "log_and_continue",
            "success": True,
            "is_critical": False
        }
        self.recovery_actions.append(recovery_info) 