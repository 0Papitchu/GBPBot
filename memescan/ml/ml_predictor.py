from typing import Dict, List, Optional, Union, Tuple
import numpy as np
import pandas as pd
from loguru import logger
import joblib
import xgboost as xgb
import lightgbm as lgb
from pathlib import Path
import time
import asyncio
from datetime import datetime, timedelta
import os
import json
import requests

from ..utils.config import Config
from ..storage.database import Database
from .data_loader import DataLoader

try:
    MODELS_AVAILABLE = True
except ImportError:
    logger.warning("xgboost or lightgbm not installed, using dummy model")
    MODELS_AVAILABLE = False

class MLPredictor:
    """Prédicteur ML pour l'analyse des tokens"""
    
    # Constantes pour les catégories de prédiction
    HIGH_POTENTIAL = "high_potential"
    NEUTRAL = "neutral"
    HIGH_RISK = "high_risk"
    
    def __init__(self, config: Config, db: Database):
        """
        Initialise le prédicteur ML
        
        Args:
            config: Configuration du système
            db: Instance de la base de données
        """
        self.config = config
        self.db = db
        self.data_loader = DataLoader(config, db)
        self.model = None
        self.model_type = None
        self.feature_names = []
        self.last_prediction_time = 0
        self.prediction_interval = 300  # 5 minutes en secondes
        
        # Charger le modèle
        self._load_model()
        
    def _load_model(self):
        """Charge le modèle pré-entraîné"""
        try:
            # Chemins des modèles
            xgb_model_path = self.config.CACHE_DIR / "xgboost_model.json"
            lgb_model_path = self.config.CACHE_DIR / "lightgbm_model.txt"
            feature_names_path = self.config.CACHE_DIR / "feature_names.joblib"
            
            # Vérifier si les modèles existent
            if xgb_model_path.exists():
                logger.info("Loading XGBoost model")
                self.model = xgb.Booster()
                self.model.load_model(str(xgb_model_path))
                self.model_type = "xgboost"
            elif lgb_model_path.exists():
                logger.info("Loading LightGBM model")
                self.model = lgb.Booster(model_file=str(lgb_model_path))
                self.model_type = "lightgbm"
            else:
                logger.warning("No pre-trained model found, using default model")
                self._load_default_model()
                
            # Charger les noms des caractéristiques
            if feature_names_path.exists():
                self.feature_names = joblib.load(feature_names_path)
                logger.info(f"Loaded {len(self.feature_names)} feature names")
            
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            self._load_default_model()
            
    def _load_default_model(self):
        """Charge un modèle par défaut simple"""
        try:
            logger.info("Loading default model")
            # Créer un modèle XGBoost simple
            params = {
                'objective': 'multi:softprob',
                'num_class': 3,
                'max_depth': 4,
                'eta': 0.1,
                'subsample': 0.8,
                'colsample_bytree': 0.8,
                'min_child_weight': 1,
                'tree_method': 'hist',  # Pour les performances
                'predictor': 'cpu_predictor'  # Pour la compatibilité
            }
            
            self.model = xgb.Booster(params)
            self.model_type = "xgboost"
            
            # Définir les caractéristiques par défaut
            self.feature_names = [
                'volume_24h', 'volume_1h', 'market_cap', 'tvl', 'price',
                'holders', 'transactions_24h', 'token_age_days',
                'volume_to_mcap', 'tvl_to_mcap', 'holder_concentration', 'trading_activity'
            ]
            
        except Exception as e:
            logger.error(f"Error loading default model: {str(e)}")
            self.model = None
            
    def download_pretrained_model(self, model_url: str):
        """
        Télécharge un modèle pré-entraîné depuis une URL
        
        Args:
            model_url: URL du modèle à télécharger
        """
        try:
            from tqdm import tqdm
            
            logger.info(f"Downloading pre-trained model from {model_url}")
            
            # Déterminer le type de modèle
            if "xgboost" in model_url.lower():
                model_path = self.config.CACHE_DIR / "xgboost_model.json"
                model_type = "xgboost"
            elif "lightgbm" in model_url.lower():
                model_path = self.config.CACHE_DIR / "lightgbm_model.txt"
                model_type = "lightgbm"
            else:
                logger.error("Unknown model type in URL")
                return
                
            # Télécharger le modèle
            response = requests.get(model_url, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            block_size = 1024
            
            with open(model_path, 'wb') as f:
                for data in tqdm(response.iter_content(block_size), 
                                total=total_size//block_size, unit='KB'):
                    f.write(data)
                    
            logger.info(f"Model downloaded to {model_path}")
            
            # Recharger le modèle
            self._load_model()
            
        except Exception as e:
            logger.error(f"Error downloading model: {str(e)}")
            
    async def predict(self, force: bool = False) -> Dict[str, List[Dict]]:
        """
        Effectue des prédictions sur les tokens
        
        Args:
            force: Forcer la prédiction même si l'intervalle n'est pas écoulé
            
        Returns:
            Dictionnaire contenant les tokens classés par catégorie
        """
        # Vérifier si l'intervalle de prédiction est écoulé
        current_time = time.time()
        if not force and (current_time - self.last_prediction_time) < self.prediction_interval:
            logger.info("Prediction interval not elapsed, skipping prediction")
            return {}
            
        try:
            if self.model is None:
                logger.error("No model available for prediction")
                return {}
                
            # Charger les données les plus récentes
            df = await self.data_loader.get_latest_token_data()
            if df.empty:
                logger.warning("No data available for prediction")
                return {}
                
            # Préparer les caractéristiques
            X, feature_names = self.data_loader.prepare_features(df)
            if len(X) == 0:
                logger.warning("No features available for prediction")
                return {}
                
            # Vérifier la compatibilité des caractéristiques
            if self.feature_names and set(feature_names) != set(self.feature_names):
                logger.warning("Feature mismatch between model and data")
                # Adapter les caractéristiques si nécessaire
                # Cette partie peut être complexe et dépend du modèle
                
            # Effectuer la prédiction
            if self.model_type == "xgboost":
                dmatrix = xgb.DMatrix(X)
                predictions = self.model.predict(dmatrix)
            elif self.model_type == "lightgbm":
                predictions = self.model.predict(X)
            else:
                logger.error("Unknown model type")
                return {}
                
            # Traiter les résultats
            results = self._process_predictions(df, predictions)
            
            # Mettre à jour le temps de dernière prédiction
            self.last_prediction_time = current_time
            
            return results
            
        except Exception as e:
            logger.error(f"Error during prediction: {str(e)}")
            return {}
            
    def _process_predictions(self, df: pd.DataFrame, predictions: np.ndarray) -> Dict[str, List[Dict]]:
        """
        Traite les prédictions brutes en résultats exploitables
        
        Args:
            df: DataFrame contenant les données des tokens
            predictions: Prédictions brutes du modèle
            
        Returns:
            Dictionnaire contenant les tokens classés par catégorie
        """
        try:
            # Initialiser les résultats
            results = {
                self.HIGH_POTENTIAL: [],
                self.NEUTRAL: [],
                self.HIGH_RISK: []
            }
            
            # Déterminer le format des prédictions
            if len(predictions.shape) > 1 and predictions.shape[1] == 3:
                # Prédictions de probabilité pour 3 classes
                class_indices = np.argmax(predictions, axis=1)
                confidences = np.max(predictions, axis=1)
            else:
                # Prédictions directes de classe
                class_indices = predictions.astype(int)
                confidences = np.ones_like(class_indices)
                
            # Mapper les indices aux catégories
            category_map = {
                0: self.HIGH_POTENTIAL,
                1: self.NEUTRAL,
                2: self.HIGH_RISK
            }
            
            # Traiter chaque token
            for i, (_, row) in enumerate(df.iterrows()):
                category = category_map.get(class_indices[i], self.NEUTRAL)
                confidence = float(confidences[i])
                
                # Créer l'objet de résultat
                token_result = {
                    "address": row["address"],
                    "chain": row["chain"],
                    "name": row["name"],
                    "symbol": row["symbol"],
                    "price": float(row["price"]),
                    "volume_24h": float(row["volume_24h"]),
                    "market_cap": float(row["market_cap"]),
                    "confidence": confidence,
                    "prediction_time": datetime.now().isoformat()
                }
                
                # Ajouter à la catégorie appropriée
                results[category].append(token_result)
                
            # Trier par confiance
            for category in results:
                results[category] = sorted(
                    results[category], 
                    key=lambda x: x["confidence"], 
                    reverse=True
                )
                
            # Journaliser les résultats
            logger.info(f"Prediction results: {len(results[self.HIGH_POTENTIAL])} high potential, "
                       f"{len(results[self.NEUTRAL])} neutral, {len(results[self.HIGH_RISK])} high risk")
                
            return results
            
        except Exception as e:
            logger.error(f"Error processing predictions: {str(e)}")
            return {self.HIGH_POTENTIAL: [], self.NEUTRAL: [], self.HIGH_RISK: []}
            
    async def save_predictions_to_db(self, predictions: Dict[str, List[Dict]]):
        """
        Sauvegarde les prédictions dans la base de données
        
        Args:
            predictions: Dictionnaire des prédictions par catégorie
        """
        try:
            # Préparer les données à insérer
            prediction_records = []
            
            for category, tokens in predictions.items():
                for token in tokens:
                    record = {
                        "token_address": token["address"],
                        "prediction_category": category,
                        "confidence": token["confidence"],
                        "prediction_time": datetime.now(),
                        "additional_data": {
                            "price": token["price"],
                            "volume_24h": token["volume_24h"],
                            "market_cap": token["market_cap"]
                        }
                    }
                    prediction_records.append(record)
                    
            # Insérer dans la base de données
            if prediction_records:
                async with self.db.async_session() as session:
                    query = """
                        INSERT INTO token_predictions (
                            token_address, prediction_category, confidence, 
                            prediction_time, additional_data
                        ) VALUES (
                            :token_address, :prediction_category, :confidence,
                            :prediction_time, :additional_data
                        )
                    """
                    
                    for record in prediction_records:
                        await session.execute(query, record)
                        
                    await session.commit()
                    
                logger.info(f"Saved {len(prediction_records)} predictions to database")
                
        except Exception as e:
            logger.error(f"Error saving predictions to database: {str(e)}")
            
    async def run_prediction_loop(self):
        """Exécute la boucle de prédiction périodique"""
        try:
            logger.info("Starting prediction loop")
            
            while True:
                # Effectuer les prédictions
                predictions = await self.predict()
                
                # Sauvegarder les prédictions
                if predictions:
                    await self.save_predictions_to_db(predictions)
                    
                # Attendre l'intervalle configuré
                await asyncio.sleep(self.prediction_interval)
                
        except Exception as e:
            logger.error(f"Error in prediction loop: {str(e)}")
            
    def get_feature_importance(self) -> Dict[str, float]:
        """
        Récupère l'importance des caractéristiques du modèle
        
        Returns:
            Dictionnaire des caractéristiques et leur importance
        """
        try:
            if self.model is None:
                logger.warning("No model available for feature importance")
                return {}
                
            importance_dict = {}
            
            if self.model_type == "xgboost":
                # Pour XGBoost
                importance_scores = self.model.get_score(importance_type='gain')
                for feature, score in importance_scores.items():
                    # Convertir les indices de caractéristiques en noms si nécessaire
                    if feature.startswith('f'):
                        try:
                            idx = int(feature[1:])
                            if idx < len(self.feature_names):
                                feature = self.feature_names[idx]
                        except:
                            pass
                    importance_dict[feature] = score
                    
            elif self.model_type == "lightgbm":
                # Pour LightGBM
                importance_scores = self.model.feature_importance(importance_type='gain')
                for i, score in enumerate(importance_scores):
                    if i < len(self.feature_names):
                        importance_dict[self.feature_names[i]] = score
                        
            # Normaliser les scores
            if importance_dict:
                total = sum(importance_dict.values())
                if total > 0:
                    importance_dict = {k: v/total for k, v in importance_dict.items()}
                    
            return importance_dict
            
        except Exception as e:
            logger.error(f"Error getting feature importance: {str(e)}")
            return {} 