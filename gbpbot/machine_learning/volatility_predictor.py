#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module de Prédiction de Volatilité pour GBPBot
=============================================

Ce module utilise des techniques de machine learning pour prédire la volatilité
à court terme des memecoins, détecter précocement les mouvements de prix majeurs,
et ajuster dynamiquement les stratégies de trading en fonction de ces prédictions.
"""

import os
import time
import json
import logging
import numpy as np
import pandas as pd
import asyncio
from typing import Dict, List, Any, Optional, Tuple, Union, Callable
from datetime import datetime, timedelta
import pickle
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import xgboost as xgb
import lightgbm as lgb
import tensorflow as tf
from tensorflow.keras.models import Sequential, load_model, save_model
from tensorflow.keras.layers import Dense, LSTM, GRU, Dropout, BatchNormalization
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau
import warnings

# Suppression des avertissements pour rendre la sortie plus propre
warnings.filterwarnings("ignore")

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("volatility_predictor")

class VolatilityPredictor:
    """
    Prédicteur de volatilité pour les memecoins.
    
    Cette classe utilise des modèles de machine learning pour prédire la volatilité 
    future des memecoins sur différentes périodes (1min, 5min, 15min), détecter les 
    mouvements de prix majeurs, et fournir des suggestions pour ajuster les stratégies 
    de trading en fonction de ces prédictions.
    """
    
    def __init__(
        self, 
        config: Optional[Dict[str, Any]] = None,
        models_dir: str = "data/volatility_models",
        data_dir: str = "data/volatility_data",
        use_gpu: bool = True
    ):
        """
        Initialise le prédicteur de volatilité.
        
        Args:
            config: Configuration pour le prédicteur
            models_dir: Répertoire pour stocker les modèles entraînés
            data_dir: Répertoire pour stocker les données d'entraînement et de prédiction
            use_gpu: Utiliser le GPU pour l'entraînement et la prédiction si disponible
        """
        self.config = config or {}
        self.models_dir = models_dir
        self.data_dir = data_dir
        self.use_gpu = use_gpu
        
        # Créer les répertoires s'ils n'existent pas
        os.makedirs(self.models_dir, exist_ok=True)
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Configurer GPU/CPU
        self._setup_hardware()
        
        # Initialiser les scaler pour normaliser les données
        self.feature_scaler = MinMaxScaler()
        self.target_scaler = MinMaxScaler()
        
        # Modèles pour différentes fenêtres de temps
        self.models = {
            "1min": None,  # Modèle pour prédiction 1 minute
            "5min": None,  # Modèle pour prédiction 5 minutes
            "15min": None  # Modèle pour prédiction 15 minutes
        }
        
        # Métriques et statistiques
        self.stats = {
            "total_predictions": 0,
            "correct_predictions": 0,
            "false_positives": 0,
            "false_negatives": 0,
            "high_volatility_captured": 0,
            "profit_enhanced": 0.0,
            "losses_avoided": 0.0,
            "average_confidence": 0.0,
            "model_performance": {}
        }
        
        # Charger les modèles existants s'ils existent
        self._load_models()
        
        logger.info("VolatilityPredictor initialisé")
    
    def _setup_hardware(self) -> None:
        """Configure le hardware (GPU/CPU) pour l'entraînement et la prédiction."""
        if self.use_gpu:
            try:
                gpus = tf.config.list_physical_devices('GPU')
                if gpus:
                    logger.info(f"GPUs disponibles: {len(gpus)}")
                    for gpu in gpus:
                        tf.config.experimental.set_memory_growth(gpu, True)
                    logger.info("GPU configuré pour l'entraînement")
                else:
                    logger.warning("Aucun GPU détecté, utilisation du CPU")
                    self.use_gpu = False
            except Exception as e:
                logger.warning(f"Erreur lors de la configuration du GPU: {e}")
                self.use_gpu = False
        else:
            logger.info("Utilisation du CPU configurée")
    
    def _load_models(self) -> None:
        """Charge les modèles pré-entraînés depuis le disque."""
        for timeframe in self.models.keys():
            model_path = os.path.join(self.models_dir, f"volatility_model_{timeframe}.keras")
            scaler_path = os.path.join(self.models_dir, f"feature_scaler_{timeframe}.pkl")
            target_scaler_path = os.path.join(self.models_dir, f"target_scaler_{timeframe}.pkl")
            
            try:
                if os.path.exists(model_path) and os.path.exists(scaler_path) and os.path.exists(target_scaler_path):
                    self.models[timeframe] = load_model(model_path)
                    
                    with open(scaler_path, 'rb') as f:
                        self.feature_scaler = pickle.load(f)
                    
                    with open(target_scaler_path, 'rb') as f:
                        self.target_scaler = pickle.load(f)
                    
                    logger.info(f"Modèle pour {timeframe} chargé avec succès")
                else:
                    logger.info(f"Aucun modèle existant pour {timeframe}, un nouveau sera entraîné")
            except Exception as e:
                logger.error(f"Erreur lors du chargement du modèle {timeframe}: {e}")
    
    def _save_models(self) -> None:
        """Sauvegarde les modèles entraînés sur le disque."""
        for timeframe, model in self.models.items():
            if model is not None:
                model_path = os.path.join(self.models_dir, f"volatility_model_{timeframe}.keras")
                scaler_path = os.path.join(self.models_dir, f"feature_scaler_{timeframe}.pkl")
                target_scaler_path = os.path.join(self.models_dir, f"target_scaler_{timeframe}.pkl")
                
                try:
                    model.save(model_path)
                    
                    with open(scaler_path, 'wb') as f:
                        pickle.dump(self.feature_scaler, f)
                    
                    with open(target_scaler_path, 'wb') as f:
                        pickle.dump(self.target_scaler, f)
                    
                    logger.info(f"Modèle pour {timeframe} sauvegardé avec succès")
                except Exception as e:
                    logger.error(f"Erreur lors de la sauvegarde du modèle {timeframe}: {e}")
    
    def add_historical_data(self, token_symbol: str, price_data: List[Dict[str, Any]]) -> None:
        """
        Ajoute des données historiques pour l'entraînement des modèles.
        
        Args:
            token_symbol: Symbole du token
            price_data: Liste de dictionnaires contenant les données de prix
                        (doit contenir timestamp, open, high, low, close, volume)
        """
        if not price_data:
            logger.warning(f"Aucune donnée fournie pour {token_symbol}")
            return
        
        # Vérifier que les données contiennent les champs nécessaires
        required_fields = ["timestamp", "open", "high", "low", "close", "volume"]
        if not all(field in price_data[0] for field in required_fields):
            logger.error(f"Données incomplètes pour {token_symbol}, champs requis: {required_fields}")
            return
        
        # Créer un DataFrame et calculer la volatilité
        df = pd.DataFrame(price_data)
        
        # Convertir timestamp en datetime si nécessaire
        if isinstance(df["timestamp"][0], (int, float)):
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit='s')
        
        df.set_index("timestamp", inplace=True)
        df.sort_index(inplace=True)
        
        # Calculer les caractéristiques de volatilité
        self._calculate_volatility_features(df)
        
        # Sauvegarder les données
        file_path = os.path.join(self.data_dir, f"{token_symbol}_price_data.csv")
        df.to_csv(file_path)
        
        logger.info(f"Données historiques pour {token_symbol} ajoutées ({len(df)} points)")
    
    def _calculate_volatility_features(self, df: pd.DataFrame) -> None:
        """
        Calcule les caractéristiques de volatilité pour un DataFrame.
        
        Args:
            df: DataFrame contenant les données de prix
        """
        # Calculer les rendements logarithmiques
        df['log_return'] = np.log(df['close'] / df['close'].shift(1))
        
        # Calcul de la volatilité réalisée (écart-type des rendements)
        df['volatility_1min'] = df['log_return'].rolling(window=1).std()
        df['volatility_5min'] = df['log_return'].rolling(window=5).std()
        df['volatility_15min'] = df['log_return'].rolling(window=15).std()
        
        # Calcul de la volatilité future pour l'entraînement
        df['future_volatility_1min'] = df['volatility_1min'].shift(-1)
        df['future_volatility_5min'] = df['volatility_5min'].shift(-5)
        df['future_volatility_15min'] = df['volatility_15min'].shift(-15)
        
        # Caractéristiques techniques supplémentaires
        # Différence entre high et low (amplitude de prix)
        df['price_range'] = df['high'] - df['low']
        df['price_range_pct'] = df['price_range'] / df['low']
        
        # Indicateurs de tendance
        df['ma_5'] = df['close'].rolling(window=5).mean()
        df['ma_15'] = df['close'].rolling(window=15).mean()
        df['ma_ratio'] = df['ma_5'] / df['ma_15']
        
        # Caractéristiques basées sur le volume
        df['volume_change'] = df['volume'].pct_change()
        df['volume_ma_5'] = df['volume'].rolling(window=5).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma_5']
    
    def train_models(self, token_symbols: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Entraîne les modèles de prédiction de volatilité.
        
        Args:
            token_symbols: Liste de symboles de tokens à utiliser pour l'entraînement
                          (si None, tous les tokens disponibles sont utilisés)
        
        Returns:
            Dict[str, Any]: Résultats de l'entraînement
        """
        logger.info("Démarrage de l'entraînement des modèles de volatilité")
        
        # Charger et combiner les données de tous les tokens
        all_data = []
        data_files = os.listdir(self.data_dir)
        csv_files = [f for f in data_files if f.endswith('_price_data.csv')]
        
        if token_symbols:
            filtered_files = [f for f in csv_files if any(symbol in f for symbol in token_symbols)]
            if filtered_files:
                csv_files = filtered_files
            else:
                logger.warning(f"Aucun fichier trouvé pour les tokens demandés: {token_symbols}")
        
        if not csv_files:
            logger.error("Aucune donnée disponible pour l'entraînement")
            return {"success": False, "error": "Aucune donnée disponible"}
        
        # Charger et fusionner les données
        for file in csv_files:
            file_path = os.path.join(self.data_dir, file)
            try:
                df = pd.read_csv(file_path)
                all_data.append(df)
                logger.info(f"Données chargées: {file} ({len(df)} points)")
            except Exception as e:
                logger.error(f"Erreur lors du chargement de {file}: {e}")
        
        if not all_data:
            logger.error("Échec du chargement des données")
            return {"success": False, "error": "Échec du chargement des données"}
        
        # Fusionner tous les dataframes
        combined_data = pd.concat(all_data, ignore_index=True)
        combined_data.dropna(inplace=True)
        
        # Résultats pour chaque période
        results = {}
        
        # Entraîner un modèle pour chaque période
        for timeframe in self.models.keys():
            logger.info(f"Entraînement du modèle pour {timeframe}")
            model_result = self._train_model_for_timeframe(combined_data, timeframe)
            results[timeframe] = model_result
        
        # Sauvegarder les modèles
        self._save_models()
        
        # Mettre à jour les statistiques
        self.stats["model_performance"] = results
        
        return {
            "success": True,
            "results": results,
            "data_points": len(combined_data)
        }
    
    def _train_model_for_timeframe(self, df: pd.DataFrame, timeframe: str) -> Dict[str, Any]:
        """
        Entraîne un modèle pour une période spécifique.
        
        Args:
            df: DataFrame contenant les données
            timeframe: Période ("1min", "5min", ou "15min")
        
        Returns:
            Dict[str, Any]: Résultats de l'entraînement
        """
        # Sélectionner la colonne cible en fonction de la période
        target_col = f"future_volatility_{timeframe}"
        
        # Vérifier si la colonne existe
        if target_col not in df.columns:
            logger.error(f"Colonne {target_col} non trouvée dans les données")
            return {"success": False, "error": f"Colonne {target_col} non trouvée"}
        
        # Sélectionner les caractéristiques et la cible
        features = [
            'log_return', f'volatility_{timeframe}', 'price_range', 'price_range_pct',
            'ma_ratio', 'volume_change', 'volume_ratio'
        ]
        
        # Supprimer les lignes avec des valeurs NaN
        df_clean = df.dropna(subset=features + [target_col])
        
        if len(df_clean) < 100:
            logger.error(f"Pas assez de données pour {timeframe} après nettoyage")
            return {"success": False, "error": "Données insuffisantes"}
        
        # Séparer caractéristiques et cible
        X = df_clean[features].values
        y = df_clean[target_col].values.reshape(-1, 1)
        
        # Normaliser les données
        X_scaled = self.feature_scaler.fit_transform(X)
        y_scaled = self.target_scaler.fit_transform(y)
        
        # Diviser en ensembles d'entraînement et de test
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y_scaled, test_size=0.2, random_state=42
        )
        
        # Préparer les données pour LSTM (reshaper)
        X_train_lstm = X_train.reshape(X_train.shape[0], 1, X_train.shape[1])
        X_test_lstm = X_test.reshape(X_test.shape[0], 1, X_test.shape[1])
        
        # Créer le modèle
        model = self._create_lstm_model(input_shape=(1, X_train.shape[1]))
        
        # Callbacks pour éviter le surapprentissage
        callbacks = [
            EarlyStopping(patience=20, verbose=1, restore_best_weights=True),
            ReduceLROnPlateau(factor=0.5, patience=10, verbose=1, min_lr=0.0001)
        ]
        
        # Entraîner le modèle
        history = model.fit(
            X_train_lstm, y_train,
            validation_data=(X_test_lstm, y_test),
            epochs=100,
            batch_size=32,
            callbacks=callbacks,
            verbose=1
        )
        
        # Évaluer le modèle
        y_pred_scaled = model.predict(X_test_lstm)
        y_pred = self.target_scaler.inverse_transform(y_pred_scaled)
        y_test_orig = self.target_scaler.inverse_transform(y_test)
        
        mse = mean_squared_error(y_test_orig, y_pred)
        mae = mean_absolute_error(y_test_orig, y_pred)
        r2 = r2_score(y_test_orig, y_pred)
        
        # Stocker le modèle
        self.models[timeframe] = model
        
        logger.info(f"Modèle pour {timeframe} entraîné: MSE={mse:.6f}, MAE={mae:.6f}, R2={r2:.4f}")
        
        return {
            "success": True,
            "mse": mse,
            "mae": mae,
            "r2": r2,
            "data_points": len(df_clean),
            "features": features
        }
    
    def _create_lstm_model(self, input_shape: Tuple[int, int]) -> tf.keras.Model:
        """
        Crée un modèle LSTM pour la prédiction de volatilité.
        
        Args:
            input_shape: Forme des données d'entrée (timesteps, features)
        
        Returns:
            tf.keras.Model: Modèle LSTM compilé
        """
        model = Sequential([
            LSTM(64, return_sequences=True, input_shape=input_shape),
            Dropout(0.2),
            LSTM(32),
            Dropout(0.2),
            Dense(16, activation='relu'),
            BatchNormalization(),
            Dense(1)
        ])
        
        model.compile(
            optimizer=Adam(learning_rate=0.001),
            loss='mean_squared_error'
        )
        
        return model
    
    async def predict_volatility(
        self, 
        token_data: Dict[str, Any], 
        timeframe: str = "15min"
    ) -> Dict[str, Any]:
        """
        Prédit la volatilité future pour un token donné.
        
        Args:
            token_data: Données du token (prix OHLCV récents)
            timeframe: Période de prédiction ("1min", "5min", ou "15min")
        
        Returns:
            Dict[str, Any]: Prédiction de volatilité et recommandations
        """
        if timeframe not in self.models or not self.models[timeframe]:
            logger.warning(f"Aucun modèle disponible pour {timeframe}")
            return {
                "success": False,
                "error": f"Aucun modèle disponible pour {timeframe}"
            }
        
        try:
            # Convertir les données en DataFrame
            df = pd.DataFrame([token_data])
            
            # Calculer les caractéristiques
            if 'log_return' not in df.columns:
                # Utiliser les données actuelles pour calculer les caractéristiques
                df['log_return'] = token_data.get('log_return', 0)
                df[f'volatility_{timeframe}'] = token_data.get('volatility', 0)
                df['price_range'] = token_data['high'] - token_data['low']
                df['price_range_pct'] = df['price_range'] / token_data['low']
                df['ma_ratio'] = token_data.get('ma_ratio', 1)
                df['volume_change'] = token_data.get('volume_change', 0)
                df['volume_ratio'] = token_data.get('volume_ratio', 1)
            
            # Sélectionner les caractéristiques
            features = [
                'log_return', f'volatility_{timeframe}', 'price_range', 'price_range_pct',
                'ma_ratio', 'volume_change', 'volume_ratio'
            ]
            
            # Normaliser les données
            X = df[features].values
            X_scaled = self.feature_scaler.transform(X)
            
            # Reshaper pour LSTM
            X_scaled_lstm = X_scaled.reshape(X_scaled.shape[0], 1, X_scaled.shape[1])
            
            # Prédire
            y_pred_scaled = self.models[timeframe].predict(X_scaled_lstm)
            y_pred = self.target_scaler.inverse_transform(y_pred_scaled)
            
            # Calculer le niveau de volatilité et le score de confiance
            predicted_volatility = float(y_pred[0][0])
            historical_volatility = token_data.get('volatility', 0)
            
            # Déterminer si la volatilité est élevée, moyenne ou faible
            volatility_threshold_high = self.config.get("volatility_threshold_high", 0.05)
            volatility_threshold_low = self.config.get("volatility_threshold_low", 0.01)
            
            if predicted_volatility > volatility_threshold_high:
                volatility_level = "élevée"
                confidence_score = min(predicted_volatility / volatility_threshold_high, 1.0) * 0.7 + 0.3
            elif predicted_volatility < volatility_threshold_low:
                volatility_level = "faible"
                confidence_score = 1.0 - (predicted_volatility / volatility_threshold_low) * 0.3
            else:
                volatility_level = "moyenne"
                confidence_score = 0.5
            
            # Générer des recommandations basées sur la volatilité prédite
            recommendations = self._generate_recommendations(
                predicted_volatility, 
                historical_volatility, 
                volatility_level
            )
            
            # Mettre à jour les statistiques
            self.stats["total_predictions"] += 1
            self.stats["average_confidence"] = (
                (self.stats["average_confidence"] * (self.stats["total_predictions"] - 1) + confidence_score)
                / self.stats["total_predictions"]
            )
            
            return {
                "success": True,
                "token_symbol": token_data.get("symbol", "Unknown"),
                "timeframe": timeframe,
                "current_price": token_data.get("close", 0),
                "historical_volatility": historical_volatility,
                "predicted_volatility": predicted_volatility,
                "volatility_level": volatility_level,
                "confidence_score": confidence_score,
                "recommendations": recommendations,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de la prédiction de volatilité: {str(e)}")
            return {
                "success": False,
                "error": f"Erreur lors de la prédiction: {str(e)}"
            }
    
    def _generate_recommendations(
        self, 
        predicted_volatility: float, 
        historical_volatility: float,
        volatility_level: str
    ) -> Dict[str, Any]:
        """
        Génère des recommandations basées sur la volatilité prédite.
        
        Args:
            predicted_volatility: Volatilité prédite
            historical_volatility: Volatilité historique
            volatility_level: Niveau de volatilité (élevée, moyenne, faible)
        
        Returns:
            Dict[str, Any]: Recommandations pour différentes stratégies
        """
        volatility_ratio = predicted_volatility / max(historical_volatility, 0.0001)
        
        recommendations = {
            "sniping": {
                "action": None,
                "stop_loss": None,
                "take_profit": None,
                "reason": None
            },
            "arbitrage": {
                "action": None,
                "priority": None,
                "reason": None
            },
            "position_sizing": {
                "recommendation": None,
                "max_allocation": None,
                "reason": None
            }
        }
        
        # Recommandations pour le sniping
        if volatility_level == "élevée":
            if volatility_ratio > 1.5:  # Volatilité en forte augmentation
                recommendations["sniping"]["action"] = "attendre"
                recommendations["sniping"]["reason"] = "Volatilité en forte augmentation, risque élevé"
                recommendations["sniping"]["stop_loss"] = "serré"
                recommendations["sniping"]["take_profit"] = "échelonné"
            else:
                recommendations["sniping"]["action"] = "vigilance"
                recommendations["sniping"]["reason"] = "Volatilité élevée, opportunités possibles mais risquées"
                recommendations["sniping"]["stop_loss"] = "moyen"
                recommendations["sniping"]["take_profit"] = "échelonné"
        elif volatility_level == "moyenne":
            recommendations["sniping"]["action"] = "normal"
            recommendations["sniping"]["reason"] = "Volatilité normale, équilibrer risque et potentiel"
            recommendations["sniping"]["stop_loss"] = "standard"
            recommendations["sniping"]["take_profit"] = "standard"
        else:  # faible
            if volatility_ratio < 0.5:  # Volatilité en forte baisse
                recommendations["sniping"]["action"] = "conservateur"
                recommendations["sniping"]["reason"] = "Volatilité très faible, peu d'opportunités"
                recommendations["sniping"]["stop_loss"] = "large"
                recommendations["sniping"]["take_profit"] = "modéré"
            else:
                recommendations["sniping"]["action"] = "sélectif"
                recommendations["sniping"]["reason"] = "Volatilité faible, sélectionner avec soin"
                recommendations["sniping"]["stop_loss"] = "standard"
                recommendations["sniping"]["take_profit"] = "modéré"
        
        # Recommandations pour l'arbitrage
        if volatility_level == "élevée":
            recommendations["arbitrage"]["action"] = "agressif"
            recommendations["arbitrage"]["priority"] = "haute"
            recommendations["arbitrage"]["reason"] = "Forte volatilité crée des écarts de prix"
        elif volatility_level == "moyenne":
            recommendations["arbitrage"]["action"] = "normal"
            recommendations["arbitrage"]["priority"] = "moyenne"
            recommendations["arbitrage"]["reason"] = "Opportunités standards d'arbitrage"
        else:
            recommendations["arbitrage"]["action"] = "conservateur"
            recommendations["arbitrage"]["priority"] = "basse"
            recommendations["arbitrage"]["reason"] = "Peu d'écarts de prix en faible volatilité"
        
        # Recommandations pour le dimensionnement des positions
        if volatility_level == "élevée":
            recommendations["position_sizing"]["recommendation"] = "réduire"
            recommendations["position_sizing"]["max_allocation"] = "25%"
            recommendations["position_sizing"]["reason"] = "Risque élevé nécessite des positions plus petites"
        elif volatility_level == "moyenne":
            recommendations["position_sizing"]["recommendation"] = "standard"
            recommendations["position_sizing"]["max_allocation"] = "50%"
            recommendations["position_sizing"]["reason"] = "Allocation standard adaptée"
        else:
            recommendations["position_sizing"]["recommendation"] = "augmenter"
            recommendations["position_sizing"]["max_allocation"] = "75%"
            recommendations["position_sizing"]["reason"] = "Faible volatilité permet des positions plus importantes"
        
        return recommendations
    
    def update_performance(self, prediction_result: Dict[str, Any], actual_outcome: Dict[str, Any]) -> None:
        """
        Met à jour les performances du modèle en comparant les prédictions aux résultats réels.
        
        Args:
            prediction_result: Résultat de prédiction précédent
            actual_outcome: Résultat réel observé
        """
        if not prediction_result.get("success", False):
            return
        
        predicted_volatility = prediction_result.get("predicted_volatility", 0)
        actual_volatility = actual_outcome.get("actual_volatility", 0)
        profit_impact = actual_outcome.get("profit_impact", 0)
        
        # Mettre à jour les statistiques
        prediction_error = abs(predicted_volatility - actual_volatility)
        relative_error = prediction_error / max(actual_volatility, 0.0001)
        
        if relative_error < 0.2:  # Prédiction correcte (moins de 20% d'erreur)
            self.stats["correct_predictions"] += 1
        
        # Haute volatilité correctement prédite
        if predicted_volatility > 0.05 and actual_volatility > 0.05:
            self.stats["high_volatility_captured"] += 1
        
        # Impact sur les profits
        if profit_impact > 0:
            self.stats["profit_enhanced"] += profit_impact
        elif profit_impact < 0:
            self.stats["losses_avoided"] -= profit_impact  # Conversion en valeur positive
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Récupère les statistiques de performance du prédicteur.
        
        Returns:
            Dict[str, Any]: Statistiques et métriques de performance
        """
        # Calculer les métriques supplémentaires
        if self.stats["total_predictions"] > 0:
            accuracy = self.stats["correct_predictions"] / self.stats["total_predictions"]
        else:
            accuracy = 0
        
        # Ajouter les métriques calculées
        stats = {
            **self.stats,
            "accuracy": accuracy,
            "prediction_success_rate": accuracy * 100,
            "profit_impact": self.stats["profit_enhanced"] + self.stats["losses_avoided"],
            "last_updated": datetime.now().isoformat()
        }
        
        return stats
    
    def plot_volatility_forecast(
        self, 
        token_symbol: str,
        timeframes: List[str] = ["1min", "5min", "15min"],
        output_file: Optional[str] = None
    ) -> str:
        """
        Génère un graphique de prévision de volatilité.
        
        Args:
            token_symbol: Symbole du token
            timeframes: Liste des périodes à inclure
            output_file: Chemin du fichier de sortie (optionnel)
        
        Returns:
            str: Chemin du fichier de graphique généré
        """
        # Charger les données historiques
        file_path = os.path.join(self.data_dir, f"{token_symbol}_price_data.csv")
        if not os.path.exists(file_path):
            logger.error(f"Aucune donnée trouvée pour {token_symbol}")
            return None
        
        df = pd.read_csv(file_path)
        
        # Définir le fichier de sortie si non fourni
        if not output_file:
            os.makedirs("reports", exist_ok=True)
            output_file = f"reports/volatility_forecast_{token_symbol}_{int(time.time())}.png"
        
        plt.figure(figsize=(12, 8))
        
        # Tracer le prix
        ax1 = plt.subplot(2, 1, 1)
        ax1.plot(df['close'], label='Prix', color='blue')
        ax1.set_title(f"Prévision de Volatilité pour {token_symbol}")
        ax1.set_ylabel('Prix')
        ax1.legend(loc='upper left')
        
        # Tracer la volatilité historique et prédite
        ax2 = plt.subplot(2, 1, 2, sharex=ax1)
        
        for tf in timeframes:
            if f"volatility_{tf}" in df.columns:
                ax2.plot(df[f"volatility_{tf}"], label=f'Volatilité {tf}')
                
            if f"future_volatility_{tf}" in df.columns:
                ax2.plot(df[f"future_volatility_{tf}"], label=f'Prédiction {tf}', linestyle='--')
        
        ax2.set_xlabel('Temps')
        ax2.set_ylabel('Volatilité')
        ax2.legend(loc='upper left')
        
        plt.tight_layout()
        plt.savefig(output_file)
        plt.close()
        
        logger.info(f"Graphique de volatilité sauvegardé: {output_file}")
        return output_file

def create_volatility_predictor(
    config: Optional[Dict[str, Any]] = None,
    models_dir: str = "data/volatility_models",
    data_dir: str = "data/volatility_data",
    use_gpu: bool = True
) -> VolatilityPredictor:
    """
    Crée et initialise un prédicteur de volatilité.
    
    Args:
        config: Configuration pour le prédicteur
        models_dir: Répertoire pour stocker les modèles entraînés
        data_dir: Répertoire pour stocker les données d'entraînement et de prédiction
        use_gpu: Utiliser le GPU pour l'entraînement et la prédiction si disponible
    
    Returns:
        VolatilityPredictor: Instance de prédicteur de volatilité
    """
    return VolatilityPredictor(config=config, models_dir=models_dir, data_dir=data_dir, use_gpu=use_gpu) 