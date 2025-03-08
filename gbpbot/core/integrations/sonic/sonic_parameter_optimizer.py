#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module d'optimisation des paramètres pour les opérations de trading sur Sonic
Permet d'ajuster automatiquement les stratégies en fonction des conditions de marché
"""

import logging
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import time
from datetime import datetime, timedelta
import json
import os

from gbpbot.core.optimization.base_optimizer import BaseOptimizer
from gbpbot.machine_learning.backtesting.simulation_engine import SimulationEngine
from gbpbot.core.utils.data_processor import DataProcessor

logger = logging.getLogger(__name__)

@dataclass
class MarketCondition:
    """Représentation des conditions de marché pour l'optimisation"""
    volatility: float  # Volatilité moyenne du marché (%)
    volume_usd: float  # Volume de trading en USD
    liquidity_depth: float  # Profondeur de liquidité en USD
    avg_slippage: float  # Slippage moyen observé (%)
    avg_transaction_time: float  # Temps moyen de confirmation des transactions (ms)
    network_congestion: float  # Niveau de congestion du réseau (0-1)
    gas_price: float  # Prix du gas en unités natives
    price_trend: float  # Tendance de prix (-1 à 1, où -1 = baissier, 1 = haussier)
    timestamp: float  # Timestamp UNIX de ces conditions
    
    def to_dict(self) -> Dict:
        """Convertit les conditions de marché en dictionnaire"""
        return {
            "volatility": self.volatility,
            "volume_usd": self.volume_usd,
            "liquidity_depth": self.liquidity_depth,
            "avg_slippage": self.avg_slippage,
            "avg_transaction_time": self.avg_transaction_time,
            "network_congestion": self.network_congestion,
            "gas_price": self.gas_price,
            "price_trend": self.price_trend,
            "timestamp": self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'MarketCondition':
        """Crée une instance de MarketCondition à partir d'un dictionnaire"""
        return cls(
            volatility=data.get("volatility", 0.0),
            volume_usd=data.get("volume_usd", 0.0),
            liquidity_depth=data.get("liquidity_depth", 0.0),
            avg_slippage=data.get("avg_slippage", 0.0),
            avg_transaction_time=data.get("avg_transaction_time", 0.0),
            network_congestion=data.get("network_congestion", 0.0),
            gas_price=data.get("gas_price", 0.0),
            price_trend=data.get("price_trend", 0.0),
            timestamp=data.get("timestamp", time.time())
        )


@dataclass
class TradingParameters:
    """Paramètres de trading optimisables pour Sonic"""
    slippage_tolerance: float  # Tolérance au slippage (%)
    min_liquidity_usd: float  # Liquidité minimale requise (USD)
    gas_priority: int  # Priorité de gas (1-10)
    position_size_pct: float  # Taille de position en % du capital disponible
    profit_target_pct: float  # Objectif de profit (%)
    stop_loss_pct: float  # Niveau de stop loss (%)
    max_execution_time_ms: float  # Temps maximum d'exécution (ms)
    retry_attempts: int  # Nombre de tentatives en cas d'échec
    
    def to_dict(self) -> Dict:
        """Convertit les paramètres en dictionnaire"""
        return {
            "slippage_tolerance": self.slippage_tolerance,
            "min_liquidity_usd": self.min_liquidity_usd,
            "gas_priority": self.gas_priority,
            "position_size_pct": self.position_size_pct,
            "profit_target_pct": self.profit_target_pct,
            "stop_loss_pct": self.stop_loss_pct,
            "max_execution_time_ms": self.max_execution_time_ms,
            "retry_attempts": self.retry_attempts
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'TradingParameters':
        """Crée une instance de TradingParameters à partir d'un dictionnaire"""
        return cls(
            slippage_tolerance=data.get("slippage_tolerance", 1.0),
            min_liquidity_usd=data.get("min_liquidity_usd", 10000.0),
            gas_priority=data.get("gas_priority", 5),
            position_size_pct=data.get("position_size_pct", 0.05),
            profit_target_pct=data.get("profit_target_pct", 1.0),
            stop_loss_pct=data.get("stop_loss_pct", 0.5),
            max_execution_time_ms=data.get("max_execution_time_ms", 5000.0),
            retry_attempts=data.get("retry_attempts", 3)
        )


class SonicParameterOptimizer(BaseOptimizer):
    """
    Optimise les paramètres de trading pour Sonic en fonction des conditions actuelles du marché
    et de l'analyse des performances historiques
    """
    
    def __init__(
        self, 
        historical_data_path: str,
        simulation_engine: Optional[SimulationEngine] = None,
        data_processor: Optional[DataProcessor] = None,
        config: Optional[Dict] = None
    ):
        """
        Initialise l'optimiseur de paramètres Sonic
        
        Args:
            historical_data_path: Chemin vers les données historiques
            simulation_engine: Moteur de simulation pour le backtesting
            data_processor: Processeur de données pour l'analyse historique
            config: Configuration de l'optimiseur
        """
        super().__init__()
        
        self.historical_data_path = historical_data_path
        self.simulation_engine = simulation_engine or SimulationEngine()
        self.data_processor = data_processor or DataProcessor()
        self.config = config or {}
        
        # Historique des optimisations
        self.optimization_results = {}
        
        # Paramètres par défaut
        self.default_parameters = TradingParameters(
            slippage_tolerance=1.0,
            min_liquidity_usd=10000.0,
            gas_priority=5,
            position_size_pct=0.05,
            profit_target_pct=1.0,
            stop_loss_pct=0.5,
            max_execution_time_ms=5000.0,
            retry_attempts=3
        )
        
        # Chemins des fichiers
        self.parameters_history_path = os.path.join(
            os.path.dirname(historical_data_path),
            "sonic_parameters_history.json"
        )
        
        # Chargement des données d'optimisation précédentes
        self._load_optimization_history()
        
        logger.info("SonicParameterOptimizer initialisé avec succès")
    
    def optimize_for_market_conditions(self, current_market_state: MarketCondition) -> TradingParameters:
        """
        Optimise les paramètres de trading en fonction des conditions actuelles du marché
        
        Args:
            current_market_state: Conditions actuelles du marché
            
        Returns:
            Paramètres de trading optimisés
        """
        logger.info("Optimisation des paramètres pour les conditions de marché: %s", 
                   current_market_state.to_dict())
        
        try:
            # Identification des périodes historiques similaires
            similar_periods = self._find_similar_historical_periods(current_market_state)
            
            if not similar_periods:
                logger.warning("Aucune période historique similaire trouvée, utilisation des paramètres par défaut")
                return self._apply_sonic_specific_adjustments(
                    self.default_parameters,
                    network_congestion=current_market_state.network_congestion,
                    price_trend=current_market_state.price_trend
                )
            
            # Configuration des gammes de paramètres à tester
            param_ranges = {
                "slippage_tolerance": np.arange(0.1, 3.0, 0.1),
                "min_liquidity_usd": np.arange(5000, 100000, 5000),
                "gas_priority": np.arange(1, 10, 1),
                "position_size_pct": np.arange(0.01, 0.2, 0.01),
                "profit_target_pct": np.arange(0.5, 10.0, 0.5),
                "stop_loss_pct": np.arange(0.5, 5.0, 0.5),
                "max_execution_time_ms": np.arange(1000, 10000, 1000),
                "retry_attempts": np.arange(1, 5, 1)
            }
            
            # Optimisation bayésienne pour trouver les paramètres optimaux
            optimal_params = self._bayesian_optimization(
                similar_periods, 
                param_ranges,
                iterations=self.config.get("optimization_iterations", 200),
                evaluation_metric=self.config.get("evaluation_metric", "risk_adjusted_return")
            )
            
            # Conversion en objet TradingParameters
            optimal_trading_params = TradingParameters(
                slippage_tolerance=optimal_params["slippage_tolerance"],
                min_liquidity_usd=optimal_params["min_liquidity_usd"],
                gas_priority=int(optimal_params["gas_priority"]),
                position_size_pct=optimal_params["position_size_pct"],
                profit_target_pct=optimal_params["profit_target_pct"],
                stop_loss_pct=optimal_params["stop_loss_pct"],
                max_execution_time_ms=optimal_params["max_execution_time_ms"],
                retry_attempts=int(optimal_params["retry_attempts"])
            )
            
            # Application d'ajustements spécifiques à Sonic
            sonic_adjusted_params = self._apply_sonic_specific_adjustments(
                optimal_trading_params,
                network_congestion=current_market_state.network_congestion,
                price_trend=current_market_state.price_trend
            )
            
            # Enregistrement des résultats d'optimisation
            self._save_optimization_result(current_market_state, sonic_adjusted_params)
            
            return sonic_adjusted_params
            
        except Exception as e:
            logger.error("Erreur lors de l'optimisation des paramètres: %s", str(e), exc_info=True)
            return self.default_parameters
    
    def _find_similar_historical_periods(self, current_state: MarketCondition) -> List[Dict]:
        """
        Identifie les périodes historiques similaires aux conditions actuelles
        
        Args:
            current_state: Conditions actuelles du marché
            
        Returns:
            Liste de périodes historiques similaires
        """
        try:
            # Chargement des données historiques
            historical_data = self._load_historical_data()
            
            if not historical_data:
                return []
            
            # Préparation des données actuelles pour la comparaison
            current_vector = np.array([
                current_state.volatility,
                current_state.volume_usd / 1e6,  # Normalisation en millions
                current_state.liquidity_depth / 1e6,  # Normalisation en millions
                current_state.avg_slippage,
                current_state.network_congestion,
                current_state.price_trend
            ])
            
            # Calcul de la similarité avec chaque période historique
            similarities = []
            for period in historical_data:
                historical_vector = np.array([
                    period["market_condition"]["volatility"],
                    period["market_condition"]["volume_usd"] / 1e6,
                    period["market_condition"]["liquidity_depth"] / 1e6,
                    period["market_condition"]["avg_slippage"],
                    period["market_condition"]["network_congestion"],
                    period["market_condition"]["price_trend"]
                ])
                
                # Distance euclidienne (plus petite = plus similaire)
                distance = np.linalg.norm(current_vector - historical_vector)
                similarities.append((distance, period))
            
            # Tri par similarité (distance la plus faible en premier)
            similarities.sort(key=lambda x: x[0])
            
            # Sélection des N périodes les plus similaires
            max_similar_periods = self.config.get("max_similar_periods", 10)
            similar_periods = [period for _, period in similarities[:max_similar_periods]]
            
            logger.info("Trouvé %d périodes historiques similaires", len(similar_periods))
            return similar_periods
            
        except Exception as e:
            logger.error("Erreur lors de la recherche de périodes similaires: %s", str(e), exc_info=True)
            return []
    
    def _bayesian_optimization(
        self, 
        similar_periods: List[Dict], 
        param_ranges: Dict[str, np.ndarray],
        iterations: int = 200,
        evaluation_metric: str = "risk_adjusted_return"
    ) -> Dict:
        """
        Effectue une optimisation bayésienne pour trouver les meilleurs paramètres
        
        Args:
            similar_periods: Périodes historiques similaires
            param_ranges: Plages de paramètres à tester
            iterations: Nombre d'itérations d'optimisation
            evaluation_metric: Métrique d'évaluation à optimiser
            
        Returns:
            Paramètres optimaux
        """
        try:
            # Note: Dans une implémentation réelle, nous utiliserions skopt, hyperopt ou un package similaire
            # Pour simplifier, nous simulons une optimisation bayésienne ici
            
            logger.info("Démarrage de l'optimisation bayésienne avec %d itérations", iterations)
            
            # Extraction des paramètres ayant fonctionné dans le passé
            historical_successful_params = []
            for period in similar_periods:
                if period.get("performance", {}).get("success", False):
                    historical_successful_params.append(period.get("parameters", {}))
            
            # Si nous avons des paramètres ayant fonctionné dans le passé, utilisons-les comme base
            if historical_successful_params:
                # Calcul des moyennes des paramètres réussis comme point de départ
                optimal_params = {}
                for param_name in param_ranges.keys():
                    values = [params.get(param_name, self.default_parameters.__getattribute__(param_name)) 
                             for params in historical_successful_params]
                    optimal_params[param_name] = float(np.mean(values))
                
                # Ajustement en fonction de la volatilité du marché actuel
                # (ceci est une simplification, l'optimisation bayésienne réelle serait plus complexe)
                volatility_factor = np.mean([period["market_condition"]["volatility"] for period in similar_periods])
                if volatility_factor > 5.0:  # Haute volatilité
                    optimal_params["slippage_tolerance"] *= 1.5
                    optimal_params["gas_priority"] = min(10, optimal_params["gas_priority"] * 1.2)
                    optimal_params["position_size_pct"] *= 0.8  # Réduire la taille des positions
                elif volatility_factor < 1.0:  # Faible volatilité
                    optimal_params["slippage_tolerance"] *= 0.8
                    optimal_params["gas_priority"] = max(1, optimal_params["gas_priority"] * 0.8)
                    optimal_params["position_size_pct"] *= 1.2  # Augmenter la taille des positions
                
                logger.info("Optimisation bayésienne terminée, paramètres optimaux trouvés: %s", optimal_params)
                return optimal_params
            else:
                logger.warning("Aucun paramètre historique réussi trouvé, utilisation des valeurs par défaut")
                return {attr: getattr(self.default_parameters, attr) for attr in dir(self.default_parameters) 
                        if not attr.startswith('_') and attr not in ('to_dict', 'from_dict')}
                
        except Exception as e:
            logger.error("Erreur lors de l'optimisation bayésienne: %s", str(e), exc_info=True)
            return {attr: getattr(self.default_parameters, attr) for attr in dir(self.default_parameters) 
                    if not attr.startswith('_') and attr not in ('to_dict', 'from_dict')}
    
    def _apply_sonic_specific_adjustments(
        self,
        params: TradingParameters,
        network_congestion: float,
        price_trend: float
    ) -> TradingParameters:
        """
        Applique des ajustements spécifiques à Sonic aux paramètres optimisés
        
        Args:
            params: Paramètres de trading optimisés
            network_congestion: Niveau de congestion du réseau (0-1)
            price_trend: Tendance de prix (-1 à 1, où -1 = baissier, 1 = haussier)
            
        Returns:
            Paramètres ajustés
        """
        # Copie des paramètres pour éviter de modifier l'original
        adjusted_params = TradingParameters(
            slippage_tolerance=params.slippage_tolerance,
            min_liquidity_usd=params.min_liquidity_usd,
            gas_priority=params.gas_priority,
            position_size_pct=params.position_size_pct,
            profit_target_pct=params.profit_target_pct,
            stop_loss_pct=params.stop_loss_pct,
            max_execution_time_ms=params.max_execution_time_ms,
            retry_attempts=params.retry_attempts
        )
        
        # Ajustement en fonction de la congestion du réseau
        if network_congestion > 0.8:  # Réseau très congestionné
            adjusted_params.gas_priority = min(10, adjusted_params.gas_priority + 2)
            adjusted_params.slippage_tolerance *= 1.3
            adjusted_params.max_execution_time_ms *= 1.5
            adjusted_params.retry_attempts = max(1, adjusted_params.retry_attempts - 1)
        elif network_congestion < 0.2:  # Réseau peu congestionné
            adjusted_params.gas_priority = max(1, adjusted_params.gas_priority - 1)
            adjusted_params.slippage_tolerance *= 0.9
            adjusted_params.max_execution_time_ms *= 0.8
            
        # Ajustement en fonction de la tendance de prix
        if price_trend > 0.7:  # Tendance fortement haussière
            adjusted_params.profit_target_pct *= 1.2  # Viser plus de profit
            adjusted_params.position_size_pct *= 1.1  # Augmenter la taille des positions
        elif price_trend < -0.7:  # Tendance fortement baissière
            adjusted_params.stop_loss_pct *= 0.8  # Stop loss plus serré
            adjusted_params.position_size_pct *= 0.9  # Réduire la taille des positions
            
        # Ajustements spécifiques à Sonic
        # Note: Ces ajustements seraient basés sur des connaissances spécifiques de l'écosystème Sonic
        # Ajustement pour SpiritSwap (plus lent mais moins de slippage)
        adjusted_params.max_execution_time_ms *= 1.2
        adjusted_params.slippage_tolerance *= 0.95
        
        logger.debug("Paramètres ajustés pour Sonic: %s", adjusted_params.to_dict())
        return adjusted_params
    
    def _load_historical_data(self) -> List[Dict]:
        """
        Charge les données historiques pour l'analyse
        
        Returns:
            Liste de données historiques
        """
        try:
            # Vérifier si le fichier existe
            if not os.path.exists(self.historical_data_path):
                logger.warning("Fichier de données historiques non trouvé: %s", self.historical_data_path)
                return []
            
            # Chargement des données
            with open(self.historical_data_path, 'r') as f:
                data = json.load(f)
                
            logger.info("Chargement de %d entrées de données historiques", len(data))
            return data
            
        except Exception as e:
            logger.error("Erreur lors du chargement des données historiques: %s", str(e), exc_info=True)
            return []
    
    def _load_optimization_history(self) -> None:
        """Charge l'historique des optimisations précédentes"""
        try:
            if os.path.exists(self.parameters_history_path):
                with open(self.parameters_history_path, 'r') as f:
                    self.optimization_results = json.load(f)
                logger.info("Chargement de %d résultats d'optimisation précédents", len(self.optimization_results))
            else:
                logger.info("Aucun historique d'optimisation trouvé, création d'un nouveau")
                self.optimization_results = {}
                
        except Exception as e:
            logger.error("Erreur lors du chargement de l'historique d'optimisation: %s", str(e), exc_info=True)
            self.optimization_results = {}
    
    def _save_optimization_result(self, market_condition: MarketCondition, parameters: TradingParameters) -> None:
        """
        Enregistre le résultat d'une optimisation
        
        Args:
            market_condition: Conditions de marché
            parameters: Paramètres optimisés
        """
        try:
            # Création d'une clé basée sur le timestamp
            timestamp = market_condition.timestamp
            key = str(int(timestamp))
            
            # Enregistrement des résultats
            self.optimization_results[key] = {
                "timestamp": timestamp,
                "market_condition": market_condition.to_dict(),
                "parameters": parameters.to_dict()
            }
            
            # Sauvegarde dans le fichier
            with open(self.parameters_history_path, 'w') as f:
                json.dump(self.optimization_results, f, indent=2)
                
            logger.debug("Résultat d'optimisation enregistré pour le timestamp %s", key)
            
        except Exception as e:
            logger.error("Erreur lors de l'enregistrement du résultat d'optimisation: %s", str(e), exc_info=True)
    
    def get_current_sonic_network_congestion(self) -> float:
        """
        Obtient le niveau actuel de congestion du réseau Sonic
        
        Returns:
            Niveau de congestion (0-1)
        """
        # Note: Cette méthode devrait interroger des APIs ou services pour obtenir des données en temps réel
        # Pour simplifier, nous simulons une valeur aléatoire
        return np.random.random()
    
    def get_sonic_dex_liquidity(self) -> Dict[str, float]:
        """
        Obtient la liquidité actuelle sur les DEX Sonic
        
        Returns:
            Dictionnaire de liquidité par DEX
        """
        # Note: Cette méthode devrait interroger des APIs ou services pour obtenir des données en temps réel
        # Pour simplifier, nous simulons des valeurs aléatoires
        return {
            "SpiritSwap": np.random.uniform(1e6, 1e7),
            "SpookySwap": np.random.uniform(1e6, 1e7)
        } 