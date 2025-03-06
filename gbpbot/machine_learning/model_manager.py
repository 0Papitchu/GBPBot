#!/usr/bin/env python3
"""
Gestionnaire de modèles d'apprentissage automatique pour GBPBot
==============================================================

Ce module gère les modèles d'apprentissage automatique utilisés par GBPBot
pour l'analyse des tokens, la prédiction des prix et l'optimisation des stratégies.
"""

import os
import logging
import numpy as np
import json
import time
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime
import pickle
from pathlib import Path
import asyncio
import random
import traceback

# Configuration du logging
logger = logging.getLogger(__name__)

# Intégration de librairies de ML (selon votre configuration)
try:
    from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    logging.warning("Les librairies de machine learning ne sont pas disponibles. Fonctionnement en mode dégradé.")

class ModelManager:
    """
    Gestionnaire central des modèles d'apprentissage automatique
    
    Cette classe gère le chargement, l'entraînement et la prédiction
    des différents modèles utilisés par GBPBot.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialisation du gestionnaire de modèles
        
        Args:
            config: Configuration des modèles
        """
        self.config = config or {}
        
        # Répertoire pour sauvegarder les modèles
        self.models_dir = self.config.get("models_dir", "models")
        os.makedirs(self.models_dir, exist_ok=True)
        
        # État des modèles
        self.models = {}
        self.model_stats = {}
        
        # Initialiser les modèles disponibles
        self._initialize_models()
        
        logger.info("Gestionnaire de modèles initialisé")
    
    def _initialize_models(self) -> None:
        """Initialise les différents modèles d'apprentissage automatique"""
        try:
            # Modèle pour l'analyse de tokens
            self.models["token_analyzer"] = self._load_model("token_analyzer")
            
            # Modèle pour la prédiction des prix
            self.models["price_predictor"] = self._load_model("price_predictor")
            
            # Modèle pour l'optimisation des stratégies
            self.models["strategy_optimizer"] = self._load_model("strategy_optimizer")
            
            # Modèle pour la détection des whales
            self.models["whale_detector"] = self._load_model("whale_detector")
            
            # Modèle pour la détection des rugpulls
            self.models["rugpull_detector"] = self._load_model("rugpull_detector")
            
            logger.info(f"Modèles initialisés: {', '.join(self.models.keys())}")
            
        except Exception as e:
            logger.exception(f"Erreur lors de l'initialisation des modèles: {e}")
    
    def _load_model(self, model_name: str) -> Any:
        """
        Charge un modèle depuis le disque ou crée un nouveau modèle
        
        Args:
            model_name: Nom du modèle à charger
            
        Returns:
            Le modèle chargé ou un nouveau modèle si le fichier n'existe pas
        """
        model_path = os.path.join(self.models_dir, f"{model_name}.pkl")
        
        try:
            if os.path.exists(model_path):
                logger.info(f"Chargement du modèle '{model_name}' depuis {model_path}")
                with open(model_path, "rb") as f:
                    model = pickle.load(f)
                
                # Enregistrer les statistiques du modèle
                self.model_stats[model_name] = {
                    "loaded_from_file": True,
                    "last_loaded": datetime.now().isoformat(),
                    "file_path": model_path,
                    "file_size_bytes": os.path.getsize(model_path)
                }
                
                return model
            else:
                logger.info(f"Création d'un nouveau modèle '{model_name}'")
                model = self._create_new_model(model_name)
                
                # Enregistrer les statistiques du modèle
                self.model_stats[model_name] = {
                    "loaded_from_file": False,
                    "created_at": datetime.now().isoformat(),
                    "is_trained": False
                }
                
                return model
                
        except Exception as e:
            logger.exception(f"Erreur lors du chargement du modèle '{model_name}': {e}")
            
            # Créer un modèle par défaut en cas d'erreur
            logger.info(f"Création d'un modèle par défaut pour '{model_name}'")
            return self._create_new_model(model_name)
    
    def _create_new_model(self, model_name: str) -> Any:
        """
        Crée un nouveau modèle en fonction du nom
        
        Args:
            model_name: Nom du modèle à créer
            
        Returns:
            Un nouveau modèle non entraîné
        """
        # Dans une implémentation complète, on créerait ici de vrais modèles
        # basés sur scikit-learn, TensorFlow, PyTorch, etc.
        # Pour l'instant, on utilise un dictionnaire simple
        
        model = {
            "name": model_name,
            "created_at": datetime.now().isoformat(),
            "is_trained": False,
            "version": "0.1",
            "parameters": {},
            "weights": {}
        }
        
        return model
    
    def save_model(self, model_name: str) -> bool:
        """
        Sauvegarde un modèle sur le disque
        
        Args:
            model_name: Nom du modèle à sauvegarder
            
        Returns:
            bool: True si la sauvegarde a réussi, False sinon
        """
        if model_name not in self.models:
            logger.error(f"Impossible de sauvegarder le modèle '{model_name}': modèle non trouvé")
            return False
            
        model_path = os.path.join(self.models_dir, f"{model_name}.pkl")
        
        try:
            # Sauvegarder le modèle
            with open(model_path, "wb") as f:
                pickle.dump(self.models[model_name], f)
                
            # Mettre à jour les statistiques
            self.model_stats[model_name].update({
                "last_saved": datetime.now().isoformat(),
                "file_path": model_path,
                "file_size_bytes": os.path.getsize(model_path)
            })
            
            logger.info(f"Modèle '{model_name}' sauvegardé avec succès")
            return True
            
        except Exception as e:
            logger.exception(f"Erreur lors de la sauvegarde du modèle '{model_name}': {e}")
            return False
    
    def analyze_token(self, token_data: Dict) -> Dict:
        """
        Analyse un token avec le modèle d'analyse de tokens
        
        Args:
            token_data: Données du token à analyser
            
        Returns:
            Dict: Résultat de l'analyse
        """
        try:
            # Vérifier que le modèle existe
            if "token_analyzer" not in self.models:
                logger.error("Modèle d'analyse de tokens non disponible")
                return {"score": 0, "confidence": 0, "error": "Modèle non disponible"}
                
            # Préparer les données pour l'analyse
            # Dans une implémentation réelle, il faudrait extraire les features pertinentes
            features = self._extract_token_features(token_data)
            
            # Simuler une analyse avec des scores aléatoires
            # Dans une implémentation réelle, on utiliserait le modèle pour prédire
            score = self._simulate_token_analysis(token_data, features)
            
            return score
            
        except Exception as e:
            logger.exception(f"Erreur lors de l'analyse du token: {e}")
            return {"score": 0, "confidence": 0, "error": str(e)}
    
    def _extract_token_features(self, token_data: Dict) -> Dict:
        """
        Extrait les caractéristiques importantes d'un token pour l'analyse
        
        Args:
            token_data: Données brutes du token
            
        Returns:
            Dict: Caractéristiques extraites
        """
        # Dans une implémentation réelle, on extrairait des features importantes
        # comme le volume, la liquidité, l'âge du token, etc.
        features = {}
        
        # Volume de transactions
        features["volume_24h"] = token_data.get("volume_24h", 0)
        
        # Liquidité
        features["liquidity"] = token_data.get("liquidity", 0)
        
        # Ratio liquidité/market cap
        market_cap = token_data.get("market_cap", 1)  # éviter division par zéro
        features["liquidity_to_mc_ratio"] = features["liquidity"] / market_cap if market_cap > 0 else 0
        
        # Nombre de transactions
        features["tx_count_24h"] = token_data.get("tx_count_24h", 0)
        
        # Âge du token (en heures)
        creation_time = token_data.get("creation_time", time.time())
        features["age_hours"] = (time.time() - creation_time) / 3600
        
        # Distribution des tokens
        features["top_holder_percentage"] = token_data.get("top_holder_percentage", 0)
        
        # Vérification du code
        features["is_verified"] = 1 if token_data.get("is_verified", False) else 0
        
        # Taxes
        features["tax_percentage"] = token_data.get("tax_percentage", 0)
        
        return features
    
    def _simulate_token_analysis(self, token_data: Dict, features: Dict) -> Dict:
        """
        Simule une analyse de token (à remplacer par un vrai modèle)
        
        Args:
            token_data: Données du token
            features: Caractéristiques extraites
            
        Returns:
            Dict: Résultat de l'analyse simulée
        """
        # Calculer un score de base
        base_score = 50  # score neutre
        
        # Ajuster le score en fonction des caractéristiques
        
        # Volume élevé est positif
        if features["volume_24h"] > 500000:  # $500K
            base_score += 15
        elif features["volume_24h"] > 100000:  # $100K
            base_score += 10
        elif features["volume_24h"] < 10000:  # $10K
            base_score -= 10
        
        # Ratio liquidité/market cap sain (>5%)
        if features["liquidity_to_mc_ratio"] > 0.05:
            base_score += 10
        else:
            base_score -= 10
        
        # Nombre de transactions élevé est positif
        if features["tx_count_24h"] > 25000:
            base_score += 15
        elif features["tx_count_24h"] > 10000:
            base_score += 10
        elif features["tx_count_24h"] < 1000:
            base_score -= 10
        
        # Token trop récent est risqué
        if features["age_hours"] < 1:
            base_score -= 5
        
        # Concentration élevée des tokens est risquée
        if features["top_holder_percentage"] > 0.30:  # >30% pour le top holder
            base_score -= 20
        
        # Code non vérifié est risqué
        if features["is_verified"] == 0:
            base_score -= 15
        
        # Taxes élevées sont risquées
        if features["tax_percentage"] > 5:
            base_score -= 15
        
        # Normaliser le score entre 0 et 100
        final_score = max(0, min(100, base_score))
        
        # Calculer la confiance (simulée)
        confidence = 0.7 + (0.3 * (1 - abs(0.5 - final_score/100)))
        
        # Déterminer la recommandation
        if final_score >= 75:
            recommendation = "STRONG_BUY"
            explanation = "Token avec fort potentiel et faibles risques"
        elif final_score >= 60:
            recommendation = "BUY"
            explanation = "Token intéressant avec risques modérés"
        elif final_score >= 40:
            recommendation = "NEUTRAL"
            explanation = "Token à surveiller, ratio risque/récompense équilibré"
        elif final_score >= 25:
            recommendation = "AVOID"
            explanation = "Token risqué, éviter l'investissement"
        else:
            recommendation = "HIGH_RISK"
            explanation = "Token très risqué, fort potentiel de scam"
        
        return {
            "score": final_score,
            "confidence": confidence,
            "recommendation": recommendation,
            "explanation": explanation,
            "risk_factors": self._identify_risk_factors(features),
            "positive_factors": self._identify_positive_factors(features),
            "timestamp": datetime.now().isoformat()
        }
    
    def _identify_risk_factors(self, features: Dict) -> List[str]:
        """Identifie les facteurs de risque dans les caractéristiques du token"""
        risk_factors = []
        
        if features["top_holder_percentage"] > 0.30:
            risk_factors.append("Concentration élevée des tokens (>30%)")
        
        if features["is_verified"] == 0:
            risk_factors.append("Code non vérifié")
        
        if features["tax_percentage"] > 5:
            risk_factors.append(f"Taxes élevées ({features['tax_percentage']}%)")
        
        if features["liquidity_to_mc_ratio"] < 0.05:
            risk_factors.append("Faible ratio liquidité/market cap (<5%)")
        
        if features["age_hours"] < 1:
            risk_factors.append("Token très récent (<1h)")
        
        return risk_factors
    
    def _identify_positive_factors(self, features: Dict) -> List[str]:
        """Identifie les facteurs positifs dans les caractéristiques du token"""
        positive_factors = []
        
        if features["volume_24h"] > 500000:
            positive_factors.append("Volume élevé (>$500K)")
        
        if features["tx_count_24h"] > 25000:
            positive_factors.append("Activité transactionnelle forte (>25K tx)")
        
        if features["liquidity_to_mc_ratio"] > 0.05:
            positive_factors.append("Bon ratio liquidité/market cap (>5%)")
        
        if features["is_verified"] == 1:
            positive_factors.append("Code vérifié")
        
        if features["tax_percentage"] < 3:
            positive_factors.append("Taxes faibles (<3%)")
        
        return positive_factors
    
    def optimize_strategy_parameters(self, strategy_name: str, performance_data: Dict) -> Dict:
        """
        Optimise les paramètres d'une stratégie en fonction des performances passées
        
        Args:
            strategy_name: Nom de la stratégie à optimiser
            performance_data: Données de performance de la stratégie
            
        Returns:
            Dict: Paramètres optimisés pour la stratégie
        """
        try:
            # Vérifier que le modèle existe
            if "strategy_optimizer" not in self.models:
                logger.error("Modèle d'optimisation de stratégie non disponible")
                return {}
                
            # Dans une implémentation réelle, on utiliserait le modèle pour 
            # optimiser les paramètres. Pour l'instant, on retourne des valeurs simulées.
            if strategy_name == "arbitrage":
                return self._optimize_arbitrage_parameters(performance_data)
            elif strategy_name == "sniping":
                return self._optimize_sniping_parameters(performance_data)
            else:
                logger.warning(f"Stratégie inconnue: {strategy_name}")
                return {}
                
        except Exception as e:
            logger.exception(f"Erreur lors de l'optimisation de la stratégie {strategy_name}: {e}")
            return {}
    
    def _optimize_arbitrage_parameters(self, performance_data: Dict) -> Dict:
        """
        Optimise les paramètres de la stratégie d'arbitrage
        
        Args:
            performance_data: Données de performance
            
        Returns:
            Dict: Paramètres optimisés
        """
        # Simuler une optimisation
        optimized_params = {
            "min_profit_threshold": 0.5,  # Pourcentage de profit minimum
            "max_slippage": 0.3,          # Slippage maximum
            "gas_boost": 1.1,             # Boost de gas
            "check_interval": 5           # Intervalle de vérification (secondes)
        }
        
        # Ajuster en fonction des performances
        success_rate = performance_data.get("success_rate", 0.5)
        avg_profit = performance_data.get("avg_profit", 0.0)
        
        # Si le taux de succès est faible, augmenter le seuil de profit minimum
        if success_rate < 0.3:
            optimized_params["min_profit_threshold"] += 0.2
        
        # Si le profit moyen est élevé, on peut réduire le seuil pour plus d'opportunités
        if avg_profit > 1.0:
            optimized_params["min_profit_threshold"] -= 0.1
            
        # Limiter les valeurs
        optimized_params["min_profit_threshold"] = max(0.2, min(1.0, optimized_params["min_profit_threshold"]))
        
        return optimized_params
    
    def _optimize_sniping_parameters(self, performance_data: Dict) -> Dict:
        """
        Optimise les paramètres de la stratégie de sniping
        
        Args:
            performance_data: Données de performance
            
        Returns:
            Dict: Paramètres optimisés
        """
        # Simuler une optimisation
        optimized_params = {
            "min_score": 60,              # Score minimum pour acheter
            "min_liquidity": 10000,       # Liquidité minimum en USD
            "min_liq_to_mc_ratio": 0.05,  # Ratio liquidité/market cap minimum
            "max_tax": 5,                 # Taxe maximum
            "take_profit_percentage": 20,  # Pourcentage de prise de profit
            "stop_loss_percentage": 10    # Pourcentage de stop loss
        }
        
        # Ajuster en fonction des performances
        success_rate = performance_data.get("success_rate", 0.5)
        avg_profit = performance_data.get("avg_profit", 0.0)
        
        # Si le taux de succès est faible, augmenter le score minimum
        if success_rate < 0.3:
            optimized_params["min_score"] += 10
        
        # Si le profit moyen est élevé, on peut ajuster les prises de profit
        if avg_profit > 30:
            optimized_params["take_profit_percentage"] += 10
            
        # Limiter les valeurs
        optimized_params["min_score"] = max(40, min(80, optimized_params["min_score"]))
        
        return optimized_params
    
    def get_model_stats(self) -> Dict:
        """
        Obtient les statistiques des modèles
        
        Returns:
            Dict: Statistiques des modèles
        """
        return self.model_stats 

    async def initialize(self) -> bool:
        """
        Initialise les modèles ML en les chargeant ou en les créant si nécessaires
        
        Returns:
            bool: True si l'initialisation a réussi, False sinon
        """
        try:
            logger.info("Initialisation des modèles ML...")
            
            # Vérifier si le ML est disponible
            if not ML_AVAILABLE:
                logger.warning("Fonctionnalités ML limitées: sklearn non disponible")
                return False
            
            # Charger les modèles existants
            for model_name in self.models.keys():
                model_path = os.path.join(self.models_dir, f"{model_name}.pkl")
                scaler_path = os.path.join(self.models_dir, f"{model_name}_scaler.pkl")
                
                if os.path.exists(model_path) and os.path.exists(scaler_path):
                    try:
                        with open(model_path, 'rb') as f:
                            self.models[model_name] = pickle.load(f)
                        with open(scaler_path, 'rb') as f:
                            self.scalers[model_name] = pickle.load(f)
                        logger.info(f"Modèle '{model_name}' chargé avec succès")
                    except Exception as e:
                        logger.error(f"Erreur lors du chargement du modèle '{model_name}': {e}")
                else:
                    logger.info(f"Modèle '{model_name}' non trouvé, création d'un modèle par défaut")
                    await self._create_default_model(model_name)
            
            # Charger les données historiques pour l'entraînement
            self._load_historical_data()
            
            logger.info("Initialisation des modèles ML terminée")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation des modèles ML: {e}")
            traceback.print_exc()
            return False
    
    async def _create_default_model(self, model_name: str) -> None:
        """
        Crée un modèle par défaut lorsqu'aucun modèle existant n'est disponible
        
        Args:
            model_name: Nom du modèle à créer
        """
        if not ML_AVAILABLE:
            logger.warning(f"Impossible de créer le modèle '{model_name}': ML non disponible")
            return
        
        try:
            logger.info(f"Création d'un modèle par défaut '{model_name}'")
            
            # Créer un scaler par défaut
            self.scalers[model_name] = StandardScaler()
            
            # Créer des modèles spécifiques selon le type
            if model_name == "allocation_optimizer":
                self.models[model_name] = GradientBoostingRegressor(
                    n_estimators=100, 
                    learning_rate=0.1, 
                    max_depth=3, 
                    random_state=42
                )
            elif model_name == "trade_probability":
                self.models[model_name] = RandomForestRegressor(
                    n_estimators=100, 
                    max_depth=5, 
                    random_state=42
                )
            elif model_name == "profit_predictor":
                self.models[model_name] = GradientBoostingRegressor(
                    n_estimators=150, 
                    learning_rate=0.05, 
                    max_depth=4, 
                    random_state=42
                )
            elif model_name == "risk_evaluator":
                self.models[model_name] = RandomForestRegressor(
                    n_estimators=120, 
                    max_depth=4, 
                    random_state=42
                )
            
            # Enregistrement du modèle vide (sera entraîné plus tard)
            self._save_model(model_name)
            
            logger.info(f"Modèle '{model_name}' créé avec succès")
            
        except Exception as e:
            logger.error(f"Erreur lors de la création du modèle '{model_name}': {e}")
    
    def _save_model(self, model_name: str) -> None:
        """
        Sauvegarde un modèle et son scaler sur disque
        
        Args:
            model_name: Nom du modèle à sauvegarder
        """
        if model_name not in self.models or self.models[model_name] is None:
            logger.warning(f"Impossible de sauvegarder le modèle '{model_name}': modèle non initialisé")
            return
            
        try:
            model_path = os.path.join(self.models_dir, f"{model_name}.pkl")
            scaler_path = os.path.join(self.models_dir, f"{model_name}_scaler.pkl")
            
            with open(model_path, 'wb') as f:
                pickle.dump(self.models[model_name], f)
                
            if model_name in self.scalers and self.scalers[model_name] is not None:
                with open(scaler_path, 'wb') as f:
                    pickle.dump(self.scalers[model_name], f)
                    
            logger.info(f"Modèle '{model_name}' sauvegardé avec succès")
            
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde du modèle '{model_name}': {e}")
    
    def _load_historical_data(self) -> None:
        """Charge les données historiques pour l'entraînement des modèles"""
        try:
            data_path = os.path.join(self.models_dir, "training_data", "historical_data.json")
            if os.path.exists(data_path):
                with open(data_path, 'r') as f:
                    self.historical_data = json.load(f)
                logger.info(f"Données historiques chargées: {len(self.historical_data['allocation'])} entrées")
        except Exception as e:
            logger.error(f"Erreur lors du chargement des données historiques: {e}")
    
    def _save_historical_data(self) -> None:
        """Sauvegarde les données historiques pour l'entraînement futur"""
        try:
            data_path = os.path.join(self.models_dir, "training_data", "historical_data.json")
            with open(data_path, 'w') as f:
                json.dump(self.historical_data, f, indent=2)
            logger.debug("Données historiques sauvegardées")
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des données historiques: {e}")
    
    async def predict_optimal_allocation(self, prediction_data: Dict) -> Optional[Dict]:
        """
        Prédit l'allocation optimale des ressources entre les stratégies
        
        Args:
            prediction_data: Données pour la prédiction
            
        Returns:
            Dict: Allocation optimale des ressources ou None en cas d'erreur
        """
        try:
            # Si ML non disponible, retourner une allocation par défaut
            if not ML_AVAILABLE or "allocation_optimizer" not in self.models or self.models["allocation_optimizer"] is None:
                logger.warning("Prédiction d'allocation par défaut (ML non disponible)")
                return {
                    "arbitrage": 0.5,
                    "sniping": 0.5
                }
            
            # Vérifier le cache
            cache_key = str(hash(str(prediction_data)))
            if cache_key in self.prediction_cache:
                cache_entry = self.prediction_cache[cache_key]
                # Si la prédiction est encore fraîche (moins de 5 minutes)
                if time.time() - cache_entry["timestamp"] < 300:
                    return cache_entry["result"]
            
            # Prétraitement des données
            features = self._extract_allocation_features(prediction_data)
            
            # Normaliser les features
            if "allocation_optimizer" in self.scalers and self.scalers["allocation_optimizer"] is not None:
                # Si le scaler est déjà entraîné
                features_scaled = self.scalers["allocation_optimizer"].transform([features])[0]
            else:
                # Sinon utiliser les features brutes
                features_scaled = features
            
            # Utiliser le modèle pour prédire l'allocation
            if len(self.historical_data["allocation"]) > 10:  # Assez de données pour prédire
                # Prédire avec le modèle
                allocation_ratio = self.models["allocation_optimizer"].predict([features_scaled])[0]
                
                # S'assurer que la valeur est entre 0.2 et 0.8 (limites raisonnables)
                allocation_ratio = max(0.2, min(0.8, allocation_ratio))
                
                allocation = {
                    "arbitrage": allocation_ratio,
                    "sniping": 1.0 - allocation_ratio
                }
            else:
                # Pas assez de données historiques, donner une allocation par défaut
                # avec une légère pondération basée sur les profits récents
                arb_profit = prediction_data.get("arbitrage_profit", 0)
                snip_profit = prediction_data.get("sniping_profit", 0)
                
                # Éviter la division par zéro
                total_profit = max(0.1, abs(arb_profit) + abs(snip_profit))
                
                # Si les deux sont profitables, allouer en fonction du ratio de profit
                if arb_profit > 0 and snip_profit > 0:
                    arb_alloc = 0.5 * (arb_profit / total_profit)
                # Si l'un est profitable et l'autre non, favoriser celui qui est profitable
                elif arb_profit > 0:
                    arb_alloc = 0.7  # Favoriser l'arbitrage
                elif snip_profit > 0:
                    arb_alloc = 0.3  # Favoriser le sniping
                else:
                    arb_alloc = 0.5  # Allocation égale par défaut
                
                # S'assurer que l'allocation est dans des limites raisonnables
                arb_alloc = max(0.2, min(0.8, arb_alloc))
                
                allocation = {
                    "arbitrage": arb_alloc,
                    "sniping": 1.0 - arb_alloc
                }
            
            # Mettre à jour le cache
            self.prediction_cache[cache_key] = {
                "timestamp": time.time(),
                "result": allocation
            }
            
            # Nettoyer le cache si nécessaire
            self._cleanup_cache()
            
            # Enregistrer les données pour l'entraînement futur
            self._record_allocation_data(prediction_data, allocation)
            
            # Entraîner périodiquement le modèle
            asyncio.create_task(self._periodic_training())
            
            self.stats["prediction_count"] += 1
            return allocation
            
        except Exception as e:
            logger.error(f"Erreur lors de la prédiction d'allocation optimale: {e}")
            traceback.print_exc()
            # Retourner une allocation par défaut en cas d'erreur
            return {
                "arbitrage": 0.5,
                "sniping": 0.5
            }
    
    def _extract_allocation_features(self, prediction_data: Dict) -> List[float]:
        """
        Extrait les caractéristiques pertinentes pour la prédiction d'allocation
        
        Args:
            prediction_data: Données brutes pour la prédiction
            
        Returns:
            List[float]: Vecteur de caractéristiques
        """
        # Extraction des caractéristiques principales
        features = [
            prediction_data.get("arbitrage_profit", 0),
            prediction_data.get("sniping_profit", 0),
            prediction_data.get("arbitrage_trades", 0),
            prediction_data.get("sniping_trades", 0)
        ]
        
        # Ajouter des caractéristiques sur les conditions du marché
        market_conditions = prediction_data.get("market_conditions", {})
        features.extend([
            market_conditions.get("volatility", 0.5),
            market_conditions.get("volume", 1000),
            1.0 if market_conditions.get("trend") == "bullish" else 0.0,
            1.0 if market_conditions.get("trend") == "bearish" else 0.0
        ])
        
        return features
    
    def _record_allocation_data(self, prediction_data: Dict, allocation: Dict) -> None:
        """
        Enregistre les données d'allocation pour un entraînement futur
        
        Args:
            prediction_data: Données utilisées pour la prédiction
            allocation: Allocation prédite
        """
        try:
            # Extraire les caractéristiques
            features = self._extract_allocation_features(prediction_data)
            
            # Enregistrer les données
            self.historical_data["allocation"].append({
                "timestamp": time.time(),
                "features": features,
                "allocation": allocation["arbitrage"],  # Nous n'avons besoin que d'une valeur, l'autre est 1-cette valeur
                "market_conditions": prediction_data.get("market_conditions", {})
            })
            
            # Limiter la taille de l'historique (garder les 10000 dernières entrées)
            if len(self.historical_data["allocation"]) > 10000:
                self.historical_data["allocation"] = self.historical_data["allocation"][-10000:]
            
            # Sauvegarder périodiquement
            if len(self.historical_data["allocation"]) % 50 == 0:
                self._save_historical_data()
                
        except Exception as e:
            logger.error(f"Erreur lors de l'enregistrement des données d'allocation: {e}")
    
    async def _periodic_training(self) -> None:
        """Entraîne périodiquement les modèles avec les nouvelles données"""
        # Vérifier si un entraînement est nécessaire
        if self.stats["last_training"] is None or time.time() - self.stats["last_training"] > 3600:  # 1 heure
            if len(self.historical_data["allocation"]) > 100:  # Assez de données pour l'entraînement
                await self.train_allocation_model()
    
    async def train_allocation_model(self) -> bool:
        """
        Entraîne le modèle d'allocation optimale
        
        Returns:
            bool: True si l'entraînement a réussi, False sinon
        """
        if not ML_AVAILABLE:
            logger.warning("Entraînement du modèle d'allocation impossible: ML non disponible")
            return False
            
        if len(self.historical_data["allocation"]) < 50:
            logger.info("Pas assez de données pour entraîner le modèle d'allocation")
            return False
            
        try:
            logger.info("Entraînement du modèle d'allocation...")
            
            # Préparer les données d'entraînement
            X = [entry["features"] for entry in self.historical_data["allocation"]]
            y = [entry["allocation"] for entry in self.historical_data["allocation"]]
            
            # Diviser en ensembles d'entraînement et de test
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            # Normaliser les données
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Entraîner le modèle
            model = GradientBoostingRegressor(
                n_estimators=100, 
                learning_rate=0.1, 
                max_depth=3, 
                random_state=42
            )
            model.fit(X_train_scaled, y_train)
            
            # Évaluer le modèle
            accuracy = model.score(X_test_scaled, y_test)
            logger.info(f"Précision du modèle d'allocation: {accuracy:.4f}")
            
            # Mettre à jour le modèle si l'accuracy est suffisante
            if accuracy > 0.6:  # Une accuracy minimale
                self.models["allocation_optimizer"] = model
                self.scalers["allocation_optimizer"] = scaler
                self._save_model("allocation_optimizer")
                
                # Mettre à jour les statistiques
                self.stats["training_count"] += 1
                self.stats["last_training"] = time.time()
                self.stats["model_accuracy"]["allocation_optimizer"] = accuracy
                
                logger.info("Modèle d'allocation entraîné et sauvegardé avec succès")
                return True
            else:
                logger.warning(f"Accuracy du modèle trop faible ({accuracy:.4f}), modèle non sauvegardé")
                return False
                
        except Exception as e:
            logger.error(f"Erreur lors de l'entraînement du modèle d'allocation: {e}")
            traceback.print_exc()
            return False
    
    def _cleanup_cache(self) -> None:
        """Nettoie le cache de prédiction pour éviter qu'il ne grossisse trop"""
        # Nettoyer au maximum toutes les 10 minutes
        if time.time() - self.last_cache_cleanup < 600:
            return
            
        try:
            # Supprimer les entrées plus anciennes que 10 minutes
            cutoff_time = time.time() - 600
            keys_to_remove = [
                k for k, v in self.prediction_cache.items() 
                if v["timestamp"] < cutoff_time
            ]
            
            for key in keys_to_remove:
                del self.prediction_cache[key]
                
            self.last_cache_cleanup = time.time()
            
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage du cache: {e}")
            
    def get_stats(self) -> Dict:
        """
        Obtient les statistiques d'utilisation des modèles ML
        
        Returns:
            Dict: Statistiques d'utilisation
        """
        return {
            "training_count": self.stats["training_count"],
            "prediction_count": self.stats["prediction_count"],
            "last_training": self.stats["last_training"],
            "models_accuracy": self.stats["model_accuracy"],
            "historical_data_size": {
                "allocation": len(self.historical_data["allocation"]),
                "market_conditions": len(self.historical_data["market_conditions"]),
                "trade_results": len(self.historical_data["trade_results"])
            }
        } 