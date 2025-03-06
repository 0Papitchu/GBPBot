"""
Module de Machine Learning pour GBPBot
======================================

Ce module fournit des fonctionnalités d'apprentissage automatique pour
optimiser les stratégies de trading (sniping, frontrunning, arbitrage)
en analysant les performances passées et en prédisant les meilleures
opportunités futures.
"""

import os
import time
import json
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
import pickle
import logging
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from gbpbot.utils.memory_optimizer import MemoryOptimizedML
import gc

# Configuration du logging
logger = logging.getLogger("gbpbot.machine_learning.prediction_model")

class TradingPredictionModel:
    """
    Modèle de prédiction pour optimiser les stratégies de trading du GBPBot.
    Utilise le machine learning pour prédire les opportunités les plus rentables
    et adapter les paramètres des différentes stratégies.
    """
    
    def __init__(self, config: Dict = None, data_dir: str = "data/ml"):
        """
        Initialise le modèle de prédiction
        
        Args:
            config: Configuration du modèle
            data_dir: Répertoire pour stocker les données et modèles
        """
        self.config = config or {}
        self.data_dir = data_dir
        
        # S'assurer que le répertoire de données existe
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Configuration du modèle
        self.model_path = self.config.get("ML_MODEL_PATH", os.path.join(self.data_dir, "gbpbot_ml.pkl"))
        self.confidence_threshold = float(self.config.get("PREDICTION_CONFIDENCE_THRESHOLD", 0.7))
        self.min_training_samples = int(self.config.get("MIN_TRAINING_SAMPLES", 100))
        self.retraining_interval = int(self.config.get("RETRAINING_INTERVAL_HOURS", 24)) * 3600  # en secondes
        
        # Configuration d'optimisation mémoire
        self.max_memory_mb = int(self.config.get("ML_MAX_MEMORY_USAGE", 4096))
        self.batch_size = int(self.config.get("ML_BATCH_SIZE", 64))
        self.use_gpu = self.config.get("ML_USE_GPU", "true").lower() == "true"
        
        # État interne
        self.models = {
            "sniping": None,
            "frontrun": None,
            "arbitrage": None
        }
        self.scalers = {
            "sniping": None,
            "frontrun": None,
            "arbitrage": None
        }
        self.last_training_time = {
            "sniping": 0,
            "frontrun": 0,
            "arbitrage": 0
        }
        self.performance_data = {
            "sniping": [],
            "frontrun": [],
            "arbitrage": []
        }
        
        # Configuration GPU si activée
        if self.use_gpu:
            self._setup_gpu()
        
        # Charger les modèles s'ils existent
        self._load_models()
        
        logger.info(f"Modèle de prédiction initialisé (GPU: {self.use_gpu}, Max memory: {self.max_memory_mb}MB)")
    
    def _setup_gpu(self) -> None:
        """
        Configure l'utilisation du GPU pour l'entraînement et l'inférence
        """
        try:
            # Tenter d'importer TensorFlow pour configurer le GPU
            import tensorflow as tf
            
            # Limiter l'utilisation de la mémoire GPU
            gpus = tf.config.experimental.list_physical_devices('GPU')
            if gpus:
                for gpu in gpus:
                    tf.config.experimental.set_memory_growth(gpu, True)
                
                # Limiter la mémoire GPU utilisée
                tf.config.experimental.set_virtual_device_configuration(
                    gpus[0],
                    [tf.config.experimental.VirtualDeviceConfiguration(memory_limit=self.max_memory_mb)]
                )
                
                logger.info(f"GPU configuré avec succès (limite: {self.max_memory_mb}MB)")
            else:
                logger.warning("GPU demandé mais aucun GPU disponible, utilisation du CPU à la place")
                self.use_gpu = False
        except ImportError:
            logger.warning("TensorFlow non disponible, impossible d'utiliser le GPU")
            self.use_gpu = False
        except Exception as e:
            logger.error(f"Erreur lors de la configuration du GPU: {str(e)}")
            self.use_gpu = False
    
    def _load_models(self) -> None:
        """Charge les modèles de prédiction depuis le disque"""
        try:
            for strategy in self.models.keys():
                model_path = f"{self.model_path}.{strategy}"
                scaler_path = f"{self.model_path}.{strategy}.scaler"
                
                if os.path.exists(model_path):
                    with open(model_path, 'rb') as f:
                        self.models[strategy] = pickle.load(f)
                    logger.info(f"Modèle {strategy} chargé depuis {model_path}")
                    
                    # Charger aussi le scaler si disponible
                    if os.path.exists(scaler_path):
                        with open(scaler_path, 'rb') as f:
                            self.scalers[strategy] = pickle.load(f)
                
        except Exception as e:
            logger.error(f"Erreur lors du chargement des modèles: {str(e)}")
    
    def _save_models(self) -> None:
        """Sauvegarde les modèles de prédiction sur le disque"""
        try:
            for strategy, model in self.models.items():
                if model is not None:
                    model_path = f"{self.model_path}.{strategy}"
                    with open(model_path, 'wb') as f:
                        pickle.dump(model, f)
                    
                    # Sauvegarder aussi le scaler
                    if self.scalers[strategy] is not None:
                        scaler_path = f"{self.model_path}.{strategy}.scaler"
                        with open(scaler_path, 'wb') as f:
                            pickle.dump(self.scalers[strategy], f)
                    
                    logger.info(f"Modèle {strategy} sauvegardé vers {model_path}")
                    
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des modèles: {str(e)}")
    
    def add_performance_data(self, strategy: str, transaction_data: Dict) -> None:
        """
        Ajoute des données de performance pour une transaction
        
        Args:
            strategy: Nom de la stratégie ('sniping', 'frontrun', 'arbitrage')
            transaction_data: Données de la transaction
        """
        if strategy not in self.performance_data:
            logger.warning(f"Stratégie inconnue: {strategy}")
            return
        
        # Ajouter un timestamp
        transaction_data["timestamp"] = time.time()
        
        # Ajouter les données
        self.performance_data[strategy].append(transaction_data)
        
        # Vérifier si nous devons réentraîner le modèle
        current_time = time.time()
        if current_time - self.last_training_time[strategy] > self.retraining_interval:
            if len(self.performance_data[strategy]) >= self.min_training_samples:
                logger.info(f"Réentraînement du modèle {strategy} (intervalle dépassé)")
                self.train_model(strategy)
    
    def _prepare_sniping_features(self, data: List[Dict]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Prépare les features pour le modèle de sniping
        
        Args:
            data: Liste des données de transactions
            
        Returns:
            Tuple[np.ndarray, np.ndarray]: (X, y)
        """
        if not data:
            return np.array([]), np.array([])
            
        # Convertir en DataFrame
        df = pd.DataFrame(data)
        
        # Définir les features et le target
        # Pour le sniping, nous voulons prédire si un token sera profitable
        features = [
            "liquidity_usd", "market_cap", "holder_count",
            "creation_time_seconds", "volume_24h", "price_change_24h",
            "dev_wallet_percentage", "initial_price", "is_verified"
        ]
        
        # Vérifier que toutes les features sont présentes
        for feature in features:
            if feature not in df.columns:
                df[feature] = 0  # Valeur par défaut
        
        # Le target est 1 si le profit est positif, 0 sinon
        df["target"] = (df["profit_percentage"] > 0).astype(int)
        
        # Extraire les features et le target
        X = df[features].values
        y = df["target"].values
        
        return X, y
    
    def _prepare_frontrun_features(self, data: List[Dict]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Prépare les features pour le modèle de frontrunning
        
        Args:
            data: Liste des données de transactions
            
        Returns:
            Tuple[np.ndarray, np.ndarray]: (X, y)
        """
        if not data:
            return np.array([]), np.array([])
            
        # Convertir en DataFrame
        df = pd.DataFrame(data)
        
        # Définir les features et le target
        # Pour le frontrunning, nous voulons prédire si une opportunité sera profitable
        features = [
            "transaction_value_usd", "gas_price", "gas_limit",
            "dex_used", "token_price", "token_volume_24h",
            "token_liquidity", "token_market_cap", "mempool_position"
        ]
        
        # Vérifier que toutes les features sont présentes
        for feature in features:
            if feature not in df.columns:
                df[feature] = 0  # Valeur par défaut
        
        # Convertir les variables catégorielles si nécessaire
        if "dex_used" in df.columns and df["dex_used"].dtype == "object":
            # Convertir en one-hot encoding simplifié
            for dex in ["raydium", "orca", "jupiter"]:
                df[f"dex_{dex}"] = (df["dex_used"] == dex).astype(int)
            features.remove("dex_used")
            features.extend([f"dex_{dex}" for dex in ["raydium", "orca", "jupiter"]])
        
        # Le target est 1 si le profit est positif, 0 sinon
        df["target"] = (df["profit_usd"] > 0).astype(int)
        
        # Extraire les features et le target
        X = df[features].values
        y = df["target"].values
        
        return X, y
    
    def _prepare_arbitrage_features(self, data: List[Dict]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Prépare les features pour le modèle d'arbitrage
        
        Args:
            data: Liste des données de transactions
            
        Returns:
            Tuple[np.ndarray, np.ndarray]: (X, y)
        """
        if not data:
            return np.array([]), np.array([])
            
        # Convertir en DataFrame
        df = pd.DataFrame(data)
        
        # Définir les features et le target
        # Pour l'arbitrage, nous voulons prédire si une opportunité sera profitable
        features = [
            "price_diff_percentage", "buy_dex_liquidity", "sell_dex_liquidity",
            "token_volume_24h", "amount_in_usd", "execution_time_ms",
            "pair_volatility", "blockchain_congestion", "gas_cost_usd"
        ]
        
        # Vérifier que toutes les features sont présentes
        for feature in features:
            if feature not in df.columns:
                df[feature] = 0  # Valeur par défaut
        
        # Le target est 1 si le profit net est positif, 0 sinon
        if "net_profit_usd" in df.columns:
            df["target"] = (df["net_profit_usd"] > 0).astype(int)
        else:
            df["target"] = (df["estimated_profit_usd"] > df.get("gas_cost_usd", 0)).astype(int)
        
        # Extraire les features et le target
        X = df[features].values
        y = df["target"].values
        
        return X, y
    
    def train_model(self, strategy: str) -> bool:
        """
        Entraîne le modèle pour une stratégie donnée
        
        Args:
            strategy: Nom de la stratégie ('sniping', 'frontrun', 'arbitrage')
            
        Returns:
            bool: True si l'entraînement a réussi, False sinon
        """
        if strategy not in self.performance_data:
            logger.warning(f"Stratégie inconnue: {strategy}")
            return False
        
        try:
            # Vérifier qu'il y a assez de données
            if len(self.performance_data[strategy]) < self.min_training_samples:
                logger.warning(f"Pas assez de données pour entraîner le modèle {strategy} (min: {self.min_training_samples})")
                return False
            
            # Préparer les données selon la stratégie
            if strategy == "sniping":
                X, y = self._prepare_sniping_features(self.performance_data[strategy])
            elif strategy == "frontrun":
                X, y = self._prepare_frontrun_features(self.performance_data[strategy])
            elif strategy == "arbitrage":
                X, y = self._prepare_arbitrage_features(self.performance_data[strategy])
            else:
                logger.warning(f"Préparation des features non implémentée pour {strategy}")
                return False
            
            # Vérifier qu'il y a des données après préparation
            if X.size == 0 or y.size == 0:
                logger.warning(f"Pas de données après préparation pour {strategy}")
                return False
            
            # Diviser les données
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            # Normaliser les données
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Sauvegarder le scaler
            self.scalers[strategy] = scaler
            
            # Optimisation mémoire: déterminer la taille de batch
            optimized_batch_size = MemoryOptimizedML.limit_batch_size(self.batch_size, self.config)
            
            # Déterminer le modèle à utiliser (plus léger si nécessaire)
            if self.config.get("ML_LIGHTWEIGHT_MODE", "false").lower() == "true":
                # Utiliser un modèle plus léger pour les systèmes avec moins de RAM
                model = GradientBoostingClassifier(
                    n_estimators=50,  # Moins d'estimateurs
                    learning_rate=0.1,
                    max_depth=3,
                    random_state=42,
                    subsample=0.8,  # Utiliser un sous-échantillon pour économiser la mémoire
                    verbose=0
                )
            else:
                # Modèle standard pour les systèmes avec suffisamment de RAM
                model = GradientBoostingClassifier(
                    n_estimators=100,
                    learning_rate=0.1,
                    max_depth=3,
                    random_state=42,
                    verbose=0
                )
            
            # Entraîner en utilisant le traitement par batch pour économiser la mémoire
            if len(X_train_scaled) > optimized_batch_size:
                # Utiliser une approche de training par incréments
                logger.info(f"Utilisation du training par batch (taille: {optimized_batch_size})")
                
                # Initialiser le modèle avec un petit nombre d'échantillons
                initial_batch = min(optimized_batch_size, len(X_train_scaled))
                model.fit(X_train_scaled[:initial_batch], y_train[:initial_batch])
                
                # Continuer l'entraînement par lots
                for i in range(initial_batch, len(X_train_scaled), optimized_batch_size):
                    end_idx = min(i + optimized_batch_size, len(X_train_scaled))
                    model.n_estimators += 10  # Ajouter plus d'estimateurs progressivement
                    
                    # Log de progression
                    progress = (end_idx / len(X_train_scaled)) * 100
                    logger.info(f"Entraînement du modèle {strategy}: {progress:.1f}% terminé")
                    
                    # S'assurer qu'on ne dépasse pas les limites de mémoire
                    gc.collect()
                    
                    # Entraîner sur ce batch
                    batch_X = X_train_scaled[i:end_idx]
                    batch_y = y_train[i:end_idx]
                    model.fit(batch_X, batch_y)
            else:
                # Entraînement normal si les données sont suffisamment petites
                model.fit(X_train_scaled, y_train)
            
            # Évaluer le modèle
            y_pred = model.predict(X_test_scaled)
            accuracy = accuracy_score(y_test, y_pred)
            precision = precision_score(y_test, y_pred, zero_division=0)
            recall = recall_score(y_test, y_pred, zero_division=0)
            f1 = f1_score(y_test, y_pred, zero_division=0)
            
            logger.info(f"Modèle {strategy} entraîné avec succès.")
            logger.info(f"Performances: Accuracy={accuracy:.4f}, Precision={precision:.4f}, Recall={recall:.4f}, F1={f1:.4f}")
            
            # Libérer la mémoire après l'entraînement
            gc.collect()
            
            # Sauvegarder le modèle si les performances sont bonnes
            if accuracy > 0.6:  # Seuil minimal de performance
                self.models[strategy] = model
                self.last_training_time[strategy] = time.time()
                self._save_models()
                return True
            else:
                logger.warning(f"Performances du modèle {strategy} trop faibles (accuracy={accuracy:.4f})")
                return False
                
        except Exception as e:
            logger.error(f"Erreur lors de l'entraînement du modèle {strategy}: {str(e)}")
            return False
    
    def predict_opportunity(self, strategy: str, features: Dict) -> Tuple[bool, float]:
        """
        Prédit si une opportunité vaut la peine d'être exploitée
        
        Args:
            strategy: Nom de la stratégie ('sniping', 'frontrun', 'arbitrage')
            features: Caractéristiques de l'opportunité
            
        Returns:
            Tuple[bool, float]: (Prédiction, Score de confiance)
        """
        if strategy not in self.models or self.models[strategy] is None:
            # Pas de modèle disponible, utiliser une heuristique simple
            if strategy == "sniping":
                # Pour le sniping, vérifier la liquidité minimale
                return features.get("liquidity_usd", 0) > 10000, 0.5
            elif strategy == "frontrun":
                # Pour le frontrunning, vérifier la valeur de la transaction
                return features.get("transaction_value_usd", 0) > 5000, 0.5
            elif strategy == "arbitrage":
                # Pour l'arbitrage, vérifier l'écart de prix
                return features.get("price_diff_percentage", 0) > 0.5, 0.5
            else:
                return False, 0.0
        
        try:
            # Préparer les features
            if strategy == "sniping":
                feature_list = [
                    "liquidity_usd", "market_cap", "holder_count",
                    "creation_time_seconds", "volume_24h", "price_change_24h",
                    "dev_wallet_percentage", "initial_price", "is_verified"
                ]
            elif strategy == "frontrun":
                feature_list = [
                    "transaction_value_usd", "gas_price", "gas_limit",
                    "dex_used", "token_price", "token_volume_24h",
                    "token_liquidity", "token_market_cap", "mempool_position"
                ]
                # Gérer les variables catégorielles
                if "dex_used" in feature_list and isinstance(features.get("dex_used"), str):
                    dex_used = features.pop("dex_used", "")
                    for dex in ["raydium", "orca", "jupiter"]:
                        features[f"dex_{dex}"] = 1 if dex_used == dex else 0
                    feature_list.remove("dex_used")
                    feature_list.extend([f"dex_{dex}" for dex in ["raydium", "orca", "jupiter"]])
            elif strategy == "arbitrage":
                feature_list = [
                    "price_diff_percentage", "buy_dex_liquidity", "sell_dex_liquidity",
                    "token_volume_24h", "amount_in_usd", "execution_time_ms",
                    "pair_volatility", "blockchain_congestion", "gas_cost_usd"
                ]
            else:
                return False, 0.0
            
            # Construire le vecteur de features
            X = np.array([[features.get(f, 0) for f in feature_list]])
            
            # Normaliser les features
            if self.scalers[strategy] is not None:
                X = self.scalers[strategy].transform(X)
            
            # Faire la prédiction
            probas = self.models[strategy].predict_proba(X)[0]
            prediction = int(probas[1] > self.confidence_threshold)
            confidence = probas[1]
            
            return bool(prediction), float(confidence)
            
        except Exception as e:
            logger.error(f"Erreur lors de la prédiction pour {strategy}: {str(e)}")
            return False, 0.0
    
    def optimize_parameters(self, strategy: str, current_params: Dict) -> Dict:
        """
        Optimise les paramètres d'une stratégie en fonction des performances passées
        
        Args:
            strategy: Nom de la stratégie ('sniping', 'frontrun', 'arbitrage')
            current_params: Paramètres actuels
            
        Returns:
            Dict: Paramètres optimisés
        """
        # Si pas assez de données ou pas de modèle, retourner les paramètres actuels
        if (strategy not in self.performance_data or 
            len(self.performance_data[strategy]) < self.min_training_samples or
            self.models[strategy] is None):
            return current_params
        
        try:
            # Copier les paramètres pour ne pas modifier l'original
            optimized_params = current_params.copy()
            
            # Analyse des performances récentes
            recent_data = self.performance_data[strategy][-100:]  # 100 dernières transactions
            success_rate = sum(1 for d in recent_data if d.get("profit_usd", 0) > 0) / max(1, len(recent_data))
            
            # Stratégies d'optimisation spécifiques
            if strategy == "sniping":
                # Si le taux de réussite est faible, augmenter le seuil de liquidité
                if success_rate < 0.4:
                    optimized_params["MIN_LIQUIDITY_USD"] = current_params.get("MIN_LIQUIDITY_USD", 10000) * 1.2
                    optimized_params["CHECK_HONEYPOT"] = True
                
                # Si le taux de réussite est élevé, ajuster le take profit
                if success_rate > 0.7:
                    avg_profit = sum(d.get("profit_percentage", 0) for d in recent_data if d.get("profit_percentage", 0) > 0) / max(1, sum(1 for d in recent_data if d.get("profit_percentage", 0) > 0))
                    optimized_params["DEFAULT_TAKE_PROFIT"] = min(50, avg_profit * 1.5)  # Ajuster en fonction du profit moyen
                
            elif strategy == "frontrun":
                # Ajuster le seuil de priorité des frais en fonction du taux de réussite
                if success_rate < 0.5:
                    optimized_params["PRIORITY_FEE_MULTIPLIER"] = current_params.get("PRIORITY_FEE_MULTIPLIER", 1.5) * 1.1
                elif success_rate > 0.8:
                    optimized_params["PRIORITY_FEE_MULTIPLIER"] = max(1.1, current_params.get("PRIORITY_FEE_MULTIPLIER", 1.5) * 0.95)
                
            elif strategy == "arbitrage":
                # Ajuster le seuil de profit minimum en fonction du taux de réussite
                if success_rate < 0.5:
                    optimized_params["MIN_PROFIT_THRESHOLD"] = current_params.get("MIN_PROFIT_THRESHOLD", 0.5) * 1.2
                elif success_rate > 0.8:
                    optimized_params["MIN_PROFIT_THRESHOLD"] = max(0.2, current_params.get("MIN_PROFIT_THRESHOLD", 0.5) * 0.9)
            
            return optimized_params
            
        except Exception as e:
            logger.error(f"Erreur lors de l'optimisation des paramètres pour {strategy}: {str(e)}")
            return current_params
    
    def get_stats(self) -> Dict:
        """
        Récupère les statistiques du modèle de prédiction
        
        Returns:
            Dict: Statistiques du modèle
        """
        stats = {
            "models_available": {
                strategy: model is not None for strategy, model in self.models.items()
            },
            "data_counts": {
                strategy: len(data) for strategy, data in self.performance_data.items()
            },
            "last_training": {
                strategy: datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S') if timestamp > 0 else "Jamais"
                for strategy, timestamp in self.last_training_time.items()
            }
        }
        
        # Calculer les performances récentes
        recent_stats = {}
        for strategy, data in self.performance_data.items():
            if not data:
                recent_stats[strategy] = {"success_rate": 0, "avg_profit": 0, "total_profit": 0, "count": 0}
                continue
                
            # Prendre les 100 dernières transactions ou moins
            recent_data = data[-min(100, len(data)):]
            success_count = sum(1 for d in recent_data if d.get("profit_usd", 0) > 0)
            success_rate = success_count / len(recent_data) if recent_data else 0
            
            profit_data = [d.get("profit_usd", 0) for d in recent_data]
            avg_profit = sum(profit_data) / len(profit_data) if profit_data else 0
            total_profit = sum(profit_data)
            
            recent_stats[strategy] = {
                "success_rate": round(success_rate * 100, 2),
                "avg_profit": round(avg_profit, 2),
                "total_profit": round(total_profit, 2),
                "count": len(recent_data)
            }
        
        stats["recent_performance"] = recent_stats
        
        return stats


# Fonction utilitaire pour créer facilement une instance du modèle
def create_prediction_model(config: Dict = None, data_dir: str = "data/ml") -> TradingPredictionModel:
    """
    Crée une nouvelle instance du modèle de prédiction
    
    Args:
        config: Configuration du modèle
        data_dir: Répertoire pour stocker les données et modèles
        
    Returns:
        TradingPredictionModel: Instance du modèle
    """
    return TradingPredictionModel(config=config, data_dir=data_dir) 