"""
Intégrateur Machine Learning pour GBPBot
======================================

Ce module intègre le machine learning aux stratégies de trading du GBPBot
en connectant les prédictions du modèle aux décisions d'exécution.
"""

import os
import logging
import asyncio
from typing import Dict, Any, Optional, List, Tuple, Union

# Import conditionnel des modules de ML
try:
    from gbpbot.machine_learning.prediction_model import TradingPredictionModel, create_prediction_model
    ML_IMPORTS_OK = True
except ImportError:
    ML_IMPORTS_OK = False

# Configuration du logging
logger = logging.getLogger("gbpbot.machine_learning.ml_integrator")

class MLIntegrator:
    """
    Intégrateur de machine learning pour optimiser les stratégies de trading.
    
    Cette classe sert de pont entre les modèles de prédiction et les stratégies
    de trading, permettant d'utiliser les prédictions pour améliorer les décisions
    de trading et optimiser les paramètres des stratégies.
    """
    
    def __init__(self, config: Dict = None):
        """
        Initialise l'intégrateur ML
        
        Args:
            config: Configuration pour l'intégrateur
        """
        self.config = config or {}
        self.enabled = self.config.get("ML_ENABLED", "true").lower() == "true"
        
        # Si le ML n'est pas activé, on s'arrête là
        if not self.enabled:
            logger.info("Machine Learning désactivé dans la configuration")
            self.prediction_model = None
            return
            
        # Vérifier que les imports ML sont disponibles
        if not ML_IMPORTS_OK:
            logger.warning("Modules de Machine Learning non disponibles, fonctionnalités désactivées")
            self.enabled = False
            self.prediction_model = None
            return
            
        # Créer le modèle de prédiction
        try:
            self.prediction_model = create_prediction_model(config=self.config)
            logger.info("Intégrateur ML initialisé avec succès")
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du modèle de prédiction: {str(e)}")
            self.enabled = False
            self.prediction_model = None
    
    def is_enabled(self) -> bool:
        """
        Vérifie si l'intégrateur ML est activé
        
        Returns:
            bool: True si activé, False sinon
        """
        return self.enabled and self.prediction_model is not None
    
    def evaluate_sniping_opportunity(self, token_data: Dict) -> Tuple[bool, float, Dict]:
        """
        Évalue une opportunité de sniping avec le ML
        
        Args:
            token_data: Données du token à évaluer
            
        Returns:
            Tuple[bool, float, Dict]: (Recommandation, Confiance, Paramètres optimisés)
        """
        if not self.is_enabled():
            # Si ML désactivé, utiliser une heuristique simple
            should_snipe = (
                token_data.get("liquidity_usd", 0) > float(self.config.get("MIN_LIQUIDITY_USD", 10000)) and
                token_data.get("dev_wallet_percentage", 100) < float(self.config.get("MAX_DEV_WALLET_PERCENTAGE", 30))
            )
            return should_snipe, 0.5, self.config
        
        try:
            # Adapter les données du token au format attendu par le modèle
            features = {
                "liquidity_usd": token_data.get("liquidity_usd", 0),
                "market_cap": token_data.get("market_cap", 0),
                "holder_count": token_data.get("holder_count", 0),
                "creation_time_seconds": token_data.get("creation_time_seconds", 0),
                "volume_24h": token_data.get("volume_24h", 0),
                "price_change_24h": token_data.get("price_change_24h", 0),
                "dev_wallet_percentage": token_data.get("dev_wallet_percentage", 0),
                "initial_price": token_data.get("initial_price", 0),
                "is_verified": 1 if token_data.get("is_verified", False) else 0
            }
            
            # Obtenir la prédiction
            should_snipe, confidence = self.prediction_model.predict_opportunity("sniping", features)
            
            # Obtenir les paramètres optimisés
            optimized_params = self.prediction_model.optimize_parameters("sniping", self.config)
            
            logger.info(f"Évaluation ML pour sniping: {should_snipe} (conf: {confidence:.2f})")
            return should_snipe, confidence, optimized_params
            
        except Exception as e:
            logger.error(f"Erreur lors de l'évaluation d'une opportunité de sniping: {str(e)}")
            # En cas d'erreur, utiliser une heuristique simple
            should_snipe = token_data.get("liquidity_usd", 0) > float(self.config.get("MIN_LIQUIDITY_USD", 10000))
            return should_snipe, 0.5, self.config
    
    def evaluate_frontrun_opportunity(self, transaction_data: Dict) -> Tuple[bool, float, Dict]:
        """
        Évalue une opportunité de frontrunning avec le ML
        
        Args:
            transaction_data: Données de la transaction à évaluer
            
        Returns:
            Tuple[bool, float, Dict]: (Recommandation, Confiance, Paramètres optimisés)
        """
        if not self.is_enabled():
            # Si ML désactivé, utiliser une heuristique simple
            should_frontrun = (
                transaction_data.get("transaction_value_usd", 0) > float(self.config.get("MIN_TRANSACTION_VALUE_USD", 5000)) and
                transaction_data.get("gas_price", 0) < float(self.config.get("MAX_GAS_PRICE", 100))
            )
            return should_frontrun, 0.5, self.config
        
        try:
            # Adapter les données de la transaction au format attendu par le modèle
            features = {
                "transaction_value_usd": transaction_data.get("transaction_value_usd", 0),
                "gas_price": transaction_data.get("gas_price", 0),
                "gas_limit": transaction_data.get("gas_limit", 0),
                "dex_used": transaction_data.get("dex_used", ""),
                "token_price": transaction_data.get("token_price", 0),
                "token_volume_24h": transaction_data.get("token_volume_24h", 0),
                "token_liquidity": transaction_data.get("token_liquidity", 0),
                "token_market_cap": transaction_data.get("token_market_cap", 0),
                "mempool_position": transaction_data.get("mempool_position", 0)
            }
            
            # Obtenir la prédiction
            should_frontrun, confidence = self.prediction_model.predict_opportunity("frontrun", features)
            
            # Obtenir les paramètres optimisés
            optimized_params = self.prediction_model.optimize_parameters("frontrun", self.config)
            
            logger.info(f"Évaluation ML pour frontrunning: {should_frontrun} (conf: {confidence:.2f})")
            return should_frontrun, confidence, optimized_params
            
        except Exception as e:
            logger.error(f"Erreur lors de l'évaluation d'une opportunité de frontrunning: {str(e)}")
            # En cas d'erreur, utiliser une heuristique simple
            should_frontrun = transaction_data.get("transaction_value_usd", 0) > float(self.config.get("MIN_TRANSACTION_VALUE_USD", 5000))
            return should_frontrun, 0.5, self.config
    
    def evaluate_arbitrage_opportunity(self, opportunity_data: Dict) -> Tuple[bool, float, Dict]:
        """
        Évalue une opportunité d'arbitrage avec le ML
        
        Args:
            opportunity_data: Données de l'opportunité à évaluer
            
        Returns:
            Tuple[bool, float, Dict]: (Recommandation, Confiance, Paramètres optimisés)
        """
        if not self.is_enabled():
            # Si ML désactivé, utiliser une heuristique simple
            should_arbitrage = (
                opportunity_data.get("price_diff_percentage", 0) > float(self.config.get("MIN_PROFIT_THRESHOLD", 0.5)) and
                opportunity_data.get("amount_in_usd", 0) <= float(self.config.get("MAX_ARBITRAGE_AMOUNT_USD", 1000))
            )
            return should_arbitrage, 0.5, self.config
        
        try:
            # Adapter les données de l'opportunité au format attendu par le modèle
            features = {
                "price_diff_percentage": opportunity_data.get("price_diff_percentage", 0),
                "buy_dex_liquidity": opportunity_data.get("buy_dex_liquidity", 0),
                "sell_dex_liquidity": opportunity_data.get("sell_dex_liquidity", 0),
                "token_volume_24h": opportunity_data.get("token_volume_24h", 0),
                "amount_in_usd": opportunity_data.get("amount_in_usd", 0),
                "execution_time_ms": opportunity_data.get("execution_time_ms", 0),
                "pair_volatility": opportunity_data.get("pair_volatility", 0),
                "blockchain_congestion": opportunity_data.get("blockchain_congestion", 0),
                "gas_cost_usd": opportunity_data.get("gas_cost_usd", 0)
            }
            
            # Obtenir la prédiction
            should_arbitrage, confidence = self.prediction_model.predict_opportunity("arbitrage", features)
            
            # Obtenir les paramètres optimisés
            optimized_params = self.prediction_model.optimize_parameters("arbitrage", self.config)
            
            logger.info(f"Évaluation ML pour arbitrage: {should_arbitrage} (conf: {confidence:.2f})")
            return should_arbitrage, confidence, optimized_params
            
        except Exception as e:
            logger.error(f"Erreur lors de l'évaluation d'une opportunité d'arbitrage: {str(e)}")
            # En cas d'erreur, utiliser une heuristique simple
            should_arbitrage = opportunity_data.get("price_diff_percentage", 0) > float(self.config.get("MIN_PROFIT_THRESHOLD", 0.5))
            return should_arbitrage, 0.5, self.config
    
    def record_transaction_result(self, strategy: str, transaction_data: Dict, result: Dict) -> None:
        """
        Enregistre le résultat d'une transaction pour l'apprentissage
        
        Args:
            strategy: Nom de la stratégie ('sniping', 'frontrun', 'arbitrage')
            transaction_data: Données initiales de la transaction
            result: Résultat de la transaction
        """
        if not self.is_enabled():
            return
            
        try:
            # Fusionner les données de transaction et le résultat
            data = {**transaction_data, **result}
            
            # Ajouter les données au modèle
            self.prediction_model.add_performance_data(strategy, data)
            
            logger.debug(f"Données de performance enregistrées pour {strategy}")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'enregistrement des données de performance: {str(e)}")
    
    def get_ml_stats(self) -> Dict:
        """
        Récupère les statistiques du modèle ML
        
        Returns:
            Dict: Statistiques du modèle
        """
        if not self.is_enabled():
            return {
                "enabled": False,
                "status": "ML désactivé dans la configuration"
            }
            
        try:
            # Obtenir les statistiques du modèle
            stats = self.prediction_model.get_stats()
            
            # Ajouter quelques informations supplémentaires
            stats["enabled"] = True
            stats["config"] = {
                "confidence_threshold": self.prediction_model.confidence_threshold,
                "min_training_samples": self.prediction_model.min_training_samples,
                "retraining_interval_hours": self.prediction_model.retraining_interval / 3600
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des statistiques ML: {str(e)}")
            return {
                "enabled": True,
                "status": f"Erreur: {str(e)}"
            }


# Fonction utilitaire pour créer facilement une instance de l'intégrateur
def create_ml_integrator(config: Dict = None) -> MLIntegrator:
    """
    Crée une nouvelle instance de l'intégrateur ML
    
    Args:
        config: Configuration pour l'intégrateur
        
    Returns:
        MLIntegrator: Instance de l'intégrateur
    """
    return MLIntegrator(config=config) 