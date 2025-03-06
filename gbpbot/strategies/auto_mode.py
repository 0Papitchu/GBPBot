#!/usr/bin/env python3
"""
Mode Automatique Intelligent pour GBPBot
=======================================

Ce module implémente une stratégie combinée qui utilise l'apprentissage
automatique pour optimiser les décisions de trading entre arbitrage et sniping.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Tuple, Union
import random
from datetime import datetime
import json
import os

from gbpbot.core.blockchain import BlockchainClient
from gbpbot.core.performance_tracker import PerformanceTracker
from gbpbot.core.opportunity_analyzer import OpportunityAnalyzer
from gbpbot.strategies.arbitrage import ArbitrageStrategy
from gbpbot.strategies.sniping import SnipingStrategy
from gbpbot.machine_learning.model_manager import ModelManager

# Configuration du logging
logger = logging.getLogger(__name__)

class AutoModeStrategy:
    """
    Stratégie d'exécution automatique intelligente combinant
    arbitrage et sniping avec adaptation constante des paramètres.
    """
    
    def __init__(self, blockchain: BlockchainClient, config: Optional[Dict[str, Any]] = None):
        """
        Initialisation de la stratégie automatique
        
        Args:
            blockchain: Client blockchain à utiliser
            config: Configuration de la stratégie
        """
        self.blockchain = blockchain
        self.config = config or {}
        
        # Initialiser les sous-stratégies
        self.arbitrage_strategy = ArbitrageStrategy(blockchain, self.config.get("arbitrage", {}))
        self.sniping_strategy = SnipingStrategy(blockchain)
        
        # Performance tracking
        self.performance_tracker = PerformanceTracker()
        
        # Initialiser le gestionnaire de modèles ML
        self.model_manager = ModelManager()
        
        # État de la stratégie
        self.running = False
        self.adaptation_interval = self.config.get("adaptation_interval", 300)  # 5 minutes par défaut
        self._adaptation_task = None
        
        # Paramètres d'équilibrage
        self.resource_allocation = {
            "arbitrage": 0.5,  # Allocation initiale 50/50
            "sniping": 0.5
        }
        
        # Crée le dossier de données s'il n'existe pas
        os.makedirs("data/auto_mode", exist_ok=True)
        
        # Statistiques de performance
        self.stats = {
            "arbitrage_trades": 0,
            "sniping_trades": 0,
            "arbitrage_profit": 0.0,
            "sniping_profit": 0.0,
            "total_profit": 0.0,
            "start_time": None,
            "allocation_history": []
        }
        
        logger.info("Stratégie automatique initialisée")

    async def initialize(self) -> bool:
        """
        Initialise les composants de la stratégie automatique
        
        Returns:
            bool: True si l'initialisation a réussi, False sinon
        """
        try:
            logger.info("Initialisation de la stratégie automatique...")
            
            # Charger ou créer les modèles ML nécessaires
            await self.model_manager.initialize()
            
            # Récupérer les historiques si disponibles
            self._load_history()
            
            # Initialiser les sous-stratégies
            await self.arbitrage_strategy.initialize()
            
            # Le sniping_strategy n'a pas de méthode initialize explicite mais commence
            # avec start_monitoring
            
            logger.info("Stratégie automatique initialisée avec succès")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de la stratégie automatique: {e}")
            return False

    async def start(self) -> bool:
        """
        Démarre la stratégie automatique
        
        Returns:
            bool: True si le démarrage a réussi, False sinon
        """
        if self.running:
            logger.warning("La stratégie automatique est déjà en cours d'exécution")
            return True
            
        try:
            logger.info("Démarrage de la stratégie automatique...")
            
            # Définir l'heure de début
            self.stats["start_time"] = time.time()
            
            # Démarrer la boucle d'adaptation
            self._adaptation_task = asyncio.create_task(self._adaptation_loop())
            
            # Démarrer les sous-stratégies avec les allocations actuelles
            arbitrage_config = self._get_arbitrage_config()
            sniping_config = self._get_sniping_config()
            
            # Démarrer l'arbitrage
            await self.arbitrage_strategy.initialize()
            # Comme l'arbitrage a une méthode run, nous la démarrons en arrière-plan
            asyncio.create_task(self.arbitrage_strategy.run(arbitrage_config.get("token_pairs", [])))
            
            # Démarrer le sniping
            await self.sniping_strategy.start_monitoring()
            
            self.running = True
            logger.info("Stratégie automatique démarrée avec succès")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors du démarrage de la stratégie automatique: {e}")
            return False

    async def stop(self) -> None:
        """Arrête la stratégie automatique"""
        if not self.running:
            logger.warning("La stratégie automatique n'est pas en cours d'exécution")
            return
            
        try:
            logger.info("Arrêt de la stratégie automatique...")
            
            # Arrêter la boucle d'adaptation
            if self._adaptation_task and not self._adaptation_task.done():
                self._adaptation_task.cancel()
                try:
                    await self._adaptation_task
                except asyncio.CancelledError:
                    pass
            
            # Arrêter les sous-stratégies
            await self.arbitrage_strategy.stop()
            
            # Le sniping n'a pas de méthode stop explicite, mais nous pouvons arrêter
            # les tâches en cours (à implémenter dans SnipingStrategy)
            if hasattr(self.sniping_strategy, 'stop'):
                await self.sniping_strategy.stop()
            
            # Sauvegarder l'historique
            self._save_history()
            
            self.running = False
            logger.info("Stratégie automatique arrêtée avec succès")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'arrêt de la stratégie automatique: {e}")

    async def _adaptation_loop(self) -> None:
        """Boucle d'adaptation automatique des paramètres"""
        logger.info("Démarrage de la boucle d'adaptation")
        try:
            while True:
                # Attendre l'intervalle configuré
                await asyncio.sleep(self.adaptation_interval)
                
                # Collecter les performances des deux stratégies
                arbitrage_performance = self.arbitrage_strategy.get_performance_stats()
                
                # Le sniping peut ne pas avoir de méthode get_performance_stats
                sniping_performance = {}
                if hasattr(self.sniping_strategy, 'get_performance_stats'):
                    sniping_performance = self.sniping_strategy.get_performance_stats()
                
                # Adapter les paramètres
                await self._adapt_parameters(arbitrage_performance, sniping_performance)
                
                # Enregistrer l'historique d'allocation
                self.stats["allocation_history"].append({
                    "timestamp": time.time(),
                    "arbitrage": self.resource_allocation["arbitrage"],
                    "sniping": self.resource_allocation["sniping"]
                })
                
                # Sauvegarder l'historique périodiquement
                self._save_history()
                
        except asyncio.CancelledError:
            logger.info("Boucle d'adaptation arrêtée")
        except Exception as e:
            logger.error(f"Erreur dans la boucle d'adaptation: {e}")

    async def _adapt_parameters(self, arbitrage_performance: Dict, sniping_performance: Dict) -> None:
        """
        Adapte les paramètres des stratégies en fonction des performances
        
        Args:
            arbitrage_performance: Statistiques de performance de l'arbitrage
            sniping_performance: Statistiques de performance du sniping
        """
        logger.info("Adaptation des paramètres basée sur les performances...")
        
        # Utiliser le ML pour prédire la meilleure allocation
        prediction_data = {
            "arbitrage_profit": arbitrage_performance.get("profit_total", 0),
            "sniping_profit": sniping_performance.get("profit_total", 0),
            "arbitrage_trades": arbitrage_performance.get("trades_count", 0),
            "sniping_trades": sniping_performance.get("trades_count", 0),
            "market_conditions": self._get_market_conditions()
        }
        
        try:
            # Obtenir la prédiction optimale
            optimal_allocation = await self.model_manager.predict_optimal_allocation(prediction_data)
            
            # Ajuster l'allocation des ressources
            if optimal_allocation:
                self.resource_allocation = optimal_allocation
                logger.info(f"Nouvelle allocation: Arbitrage={optimal_allocation['arbitrage']:.2f}, Sniping={optimal_allocation['sniping']:.2f}")
            
            # Adapter les paramètres spécifiques
            await self._adapt_arbitrage_params()
            await self._adapt_sniping_params()
            
            # Mettre à jour les statistiques
            self.stats["arbitrage_profit"] = arbitrage_performance.get("profit_total", 0)
            self.stats["sniping_profit"] = sniping_performance.get("profit_total", 0)
            self.stats["total_profit"] = self.stats["arbitrage_profit"] + self.stats["sniping_profit"]
            self.stats["arbitrage_trades"] = arbitrage_performance.get("trades_count", 0)
            self.stats["sniping_trades"] = sniping_performance.get("trades_count", 0)
            
        except Exception as e:
            logger.error(f"Erreur lors de l'adaptation des paramètres: {e}")

    def _get_market_conditions(self) -> Dict:
        """
        Récupère les conditions actuelles du marché
        
        Returns:
            Dict: Données sur les conditions du marché
        """
        # Cette fonction devrait être implémentée pour obtenir des données
        # sur la volatilité du marché, le volume, etc.
        # Pour l'instant, retournons des données factices
        return {
            "volatility": random.uniform(0.1, 0.9),
            "volume": random.uniform(1000, 10000000),
            "trend": random.choice(["bullish", "bearish", "sideways"])
        }

    async def _adapt_arbitrage_params(self) -> None:
        """Adapte les paramètres de la stratégie d'arbitrage"""
        # Adapter les paramètres spécifiques à l'arbitrage
        # Comme le gas_boost, les seuils de profit, etc.
        pass

    async def _adapt_sniping_params(self) -> None:
        """Adapte les paramètres de la stratégie de sniping"""
        # Adapter les paramètres spécifiques au sniping
        # Comme les stop-loss, take-profit, etc.
        pass
        
    def _get_arbitrage_config(self) -> Dict:
        """
        Génère la configuration pour la stratégie d'arbitrage
        
        Returns:
            Dict: Configuration pour l'arbitrage
        """
        # Récupérer et adapter la configuration de base
        base_config = self.config.get("arbitrage", {})
        
        # Ajuster en fonction de l'allocation actuelle
        allocation = self.resource_allocation["arbitrage"]
        
        # On peut ajuster des paramètres comme le nombre de paires à surveiller,
        # la fréquence des vérifications, etc.
        
        return base_config
        
    def _get_sniping_config(self) -> Dict:
        """
        Génère la configuration pour la stratégie de sniping
        
        Returns:
            Dict: Configuration pour le sniping
        """
        # Récupérer et adapter la configuration de base
        base_config = self.config.get("sniping", {})
        
        # Ajuster en fonction de l'allocation actuelle
        allocation = self.resource_allocation["sniping"]
        
        # On peut ajuster des paramètres comme le montant max par trade,
        # la sensibilité de la détection, etc.
        
        return base_config
        
    def _save_history(self) -> None:
        """Sauvegarde l'historique des performances et allocations"""
        try:
            with open("data/auto_mode/history.json", "w") as f:
                json.dump(self.stats, f, indent=2)
            logger.debug("Historique sauvegardé avec succès")
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde de l'historique: {e}")
            
    def _load_history(self) -> None:
        """Charge l'historique des performances et allocations"""
        try:
            if os.path.exists("data/auto_mode/history.json"):
                with open("data/auto_mode/history.json", "r") as f:
                    self.stats = json.load(f)
                logger.debug("Historique chargé avec succès")
        except Exception as e:
            logger.error(f"Erreur lors du chargement de l'historique: {e}")

    def get_performance_stats(self) -> Dict:
        """
        Obtient les statistiques de performance de la stratégie automatique
        
        Returns:
            Dict: Statistiques de performance
        """
        current_time = time.time()
        runtime = current_time - (self.stats["start_time"] or current_time)
        
        return {
            "arbitrage_allocation": self.resource_allocation["arbitrage"],
            "sniping_allocation": self.resource_allocation["sniping"],
            "arbitrage_profit": self.stats["arbitrage_profit"],
            "sniping_profit": self.stats["sniping_profit"],
            "total_profit": self.stats["total_profit"],
            "arbitrage_trades": self.stats["arbitrage_trades"],
            "sniping_trades": self.stats["sniping_trades"],
            "total_trades": self.stats["arbitrage_trades"] + self.stats["sniping_trades"],
            "runtime_seconds": runtime,
            "average_profit_per_hour": (self.stats["total_profit"] / runtime * 3600) if runtime > 0 else 0
        }

# Alias de classe pour suivre la convention de nommage
AutoModeStrategy = AutoModeStrategy 