from typing import Dict, List, Optional, Union
import pandas as pd
import numpy as np
from loguru import logger
import json
import csv
from pathlib import Path
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
import asyncio

from ..utils.config import Config
from ..storage.database import Database
from .ml_predictor import MLPredictor

class MLResults:
    """Gestionnaire des résultats de prédiction ML"""
    
    def __init__(self, config: Config, db: Database, predictor: MLPredictor):
        """
        Initialise le gestionnaire de résultats
        
        Args:
            config: Configuration du système
            db: Instance de la base de données
            predictor: Instance du prédicteur ML
        """
        self.config = config
        self.db = db
        self.predictor = predictor
        self.export_dir = config.EXPORT_DIR
        
    async def export_predictions_to_csv(self, predictions: Dict[str, List[Dict]], 
                                      filename: Optional[str] = None) -> str:
        """
        Exporte les prédictions dans un fichier CSV
        
        Args:
            predictions: Dictionnaire des prédictions par catégorie
            filename: Nom du fichier (optionnel)
            
        Returns:
            Chemin du fichier exporté
        """
        try:
            # Créer un nom de fichier par défaut si non spécifié
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"token_predictions_{timestamp}.csv"
                
            # Chemin complet du fichier
            filepath = self.export_dir / filename
            
            # Préparer les données pour l'export
            export_data = []
            
            for category, tokens in predictions.items():
                for token in tokens:
                    row = {
                        "address": token["address"],
                        "chain": token["chain"],
                        "name": token["name"],
                        "symbol": token["symbol"],
                        "category": category,
                        "confidence": token["confidence"],
                        "price": token["price"],
                        "volume_24h": token["volume_24h"],
                        "market_cap": token["market_cap"],
                        "prediction_time": token["prediction_time"]
                    }
                    export_data.append(row)
                    
            # Convertir en DataFrame et exporter
            if export_data:
                df = pd.DataFrame(export_data)
                df.to_csv(filepath, index=False)
                logger.info(f"Exported {len(export_data)} predictions to {filepath}")
                return str(filepath)
            else:
                logger.warning("No data to export")
                return ""
                
        except Exception as e:
            logger.error(f"Error exporting predictions to CSV: {str(e)}")
            return ""
            
    async def export_high_potential_tokens(self, predictions: Dict[str, List[Dict]],
                                         min_confidence: float = 0.7) -> List[Dict]:
        """
        Filtre et exporte les tokens à fort potentiel
        
        Args:
            predictions: Dictionnaire des prédictions par catégorie
            min_confidence: Confiance minimale pour considérer un token
            
        Returns:
            Liste des tokens à fort potentiel
        """
        try:
            high_potential = predictions.get(MLPredictor.HIGH_POTENTIAL, [])
            
            # Filtrer par confiance
            filtered_tokens = [
                token for token in high_potential
                if token["confidence"] >= min_confidence
            ]
            
            if filtered_tokens:
                # Exporter en CSV
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"high_potential_tokens_{timestamp}.csv"
                filepath = self.export_dir / filename
                
                # Convertir en DataFrame et exporter
                df = pd.DataFrame(filtered_tokens)
                df.to_csv(filepath, index=False)
                
                logger.info(f"Exported {len(filtered_tokens)} high potential tokens to {filepath}")
                
            return filtered_tokens
            
        except Exception as e:
            logger.error(f"Error exporting high potential tokens: {str(e)}")
            return []
            
    async def generate_prediction_visualizations(self, predictions: Dict[str, List[Dict]]):
        """
        Génère des visualisations des prédictions
        
        Args:
            predictions: Dictionnaire des prédictions par catégorie
        """
        try:
            # Préparer les données
            categories = []
            confidences = []
            chains = []
            
            for category, tokens in predictions.items():
                for token in tokens:
                    categories.append(category)
                    confidences.append(token["confidence"])
                    chains.append(token["chain"])
                    
            if not categories:
                logger.warning("No data for visualization")
                return
                
            # Créer un DataFrame
            df = pd.DataFrame({
                "category": categories,
                "confidence": confidences,
                "chain": chains
            })
            
            # Configurer le style
            sns.set(style="whitegrid")
            
            # 1. Distribution des catégories
            plt.figure(figsize=(10, 6))
            ax = sns.countplot(x="category", data=df, palette="viridis")
            plt.title("Distribution des prédictions par catégorie")
            plt.xlabel("Catégorie")
            plt.ylabel("Nombre de tokens")
            
            # Ajouter les valeurs sur les barres
            for p in ax.patches:
                ax.annotate(f"{p.get_height()}", 
                           (p.get_x() + p.get_width() / 2., p.get_height()),
                           ha='center', va='bottom')
                           
            # Sauvegarder
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            plt.savefig(self.export_dir / f"category_distribution_{timestamp}.png")
            plt.close()
            
            # 2. Distribution des confiances par catégorie
            plt.figure(figsize=(10, 6))
            sns.boxplot(x="category", y="confidence", data=df, palette="viridis")
            plt.title("Distribution des scores de confiance par catégorie")
            plt.xlabel("Catégorie")
            plt.ylabel("Score de confiance")
            plt.savefig(self.export_dir / f"confidence_distribution_{timestamp}.png")
            plt.close()
            
            # 3. Distribution par chaîne
            plt.figure(figsize=(12, 6))
            chain_category = pd.crosstab(df["chain"], df["category"])
            chain_category.plot(kind="bar", stacked=True, figsize=(12, 6), colormap="viridis")
            plt.title("Distribution des prédictions par chaîne")
            plt.xlabel("Chaîne")
            plt.ylabel("Nombre de tokens")
            plt.legend(title="Catégorie")
            plt.savefig(self.export_dir / f"chain_distribution_{timestamp}.png")
            plt.close()
            
            logger.info(f"Generated prediction visualizations in {self.export_dir}")
            
        except Exception as e:
            logger.error(f"Error generating visualizations: {str(e)}")
            
    async def get_historical_predictions(self, token_address: str, days: int = 7) -> pd.DataFrame:
        """
        Récupère l'historique des prédictions pour un token
        
        Args:
            token_address: Adresse du token
            days: Nombre de jours d'historique
            
        Returns:
            DataFrame contenant l'historique des prédictions
        """
        try:
            # Requête SQL
            query = """
                SELECT 
                    token_address, prediction_category, confidence, 
                    prediction_time, additional_data
                FROM token_predictions
                WHERE token_address = :token_address
                AND prediction_time >= NOW() - INTERVAL :days DAY
                ORDER BY prediction_time
            """
            
            # Exécuter la requête
            async with self.db.async_session() as session:
                result = await session.execute(query, {
                    "token_address": token_address,
                    "days": days
                })
                rows = [dict(row) for row in result]
                
            if not rows:
                logger.warning(f"No prediction history found for token {token_address}")
                return pd.DataFrame()
                
            # Convertir en DataFrame
            df = pd.DataFrame(rows)
            df["prediction_time"] = pd.to_datetime(df["prediction_time"])
            
            # Extraire les données additionnelles
            if "additional_data" in df.columns:
                # Convertir les données JSON en colonnes
                additional_data = df["additional_data"].apply(
                    lambda x: json.loads(x) if isinstance(x, str) else x
                )
                
                for key in ["price", "volume_24h", "market_cap"]:
                    df[key] = additional_data.apply(
                        lambda x: x.get(key, None) if isinstance(x, dict) else None
                    )
                    
            return df
            
        except Exception as e:
            logger.error(f"Error getting prediction history: {str(e)}")
            return pd.DataFrame()
            
    async def generate_token_report(self, token_address: str) -> Dict:
        """
        Génère un rapport détaillé pour un token spécifique
        
        Args:
            token_address: Adresse du token
            
        Returns:
            Dictionnaire contenant le rapport
        """
        try:
            # Récupérer les informations du token
            query = """
                SELECT 
                    t.address, t.chain, t.name, t.symbol, t.created_at, 
                    t.total_supply, t.holders_count
                FROM tokens t
                WHERE t.address = :token_address
            """
            
            async with self.db.async_session() as session:
                result = await session.execute(query, {"token_address": token_address})
                token_info = dict(result.fetchone()) if result.rowcount > 0 else {}
                
            if not token_info:
                logger.warning(f"Token {token_address} not found")
                return {}
                
            # Récupérer l'historique des prédictions
            prediction_history = await self.get_historical_predictions(token_address)
            
            # Récupérer les métriques récentes
            query = """
                SELECT 
                    timestamp, volume_24h, volume_1h, market_cap, tvl, 
                    price, holders, transactions_24h
                FROM token_metrics
                WHERE token_address = :token_address
                ORDER BY timestamp DESC
                LIMIT 1
            """
            
            async with self.db.async_session() as session:
                result = await session.execute(query, {"token_address": token_address})
                metrics = dict(result.fetchone()) if result.rowcount > 0 else {}
                
            # Construire le rapport
            report = {
                "token_info": token_info,
                "current_metrics": metrics,
                "prediction_summary": {}
            }
            
            # Résumer les prédictions
            if not prediction_history.empty:
                latest_prediction = prediction_history.iloc[-1]
                report["prediction_summary"] = {
                    "latest_category": latest_prediction["prediction_category"],
                    "latest_confidence": float(latest_prediction["confidence"]),
                    "prediction_time": latest_prediction["prediction_time"].isoformat(),
                    "category_history": prediction_history["prediction_category"].value_counts().to_dict(),
                    "avg_confidence": float(prediction_history["confidence"].mean()),
                    "confidence_trend": "increasing" if prediction_history["confidence"].is_monotonic_increasing else
                                       "decreasing" if prediction_history["confidence"].is_monotonic_decreasing else
                                       "fluctuating"
                }
                
            return report
            
        except Exception as e:
            logger.error(f"Error generating token report: {str(e)}")
            return {}
            
    async def export_feature_importance(self):
        """Exporte l'importance des caractéristiques du modèle"""
        try:
            # Récupérer l'importance des caractéristiques
            importance_dict = self.predictor.get_feature_importance()
            
            if not importance_dict:
                logger.warning("No feature importance data available")
                return
                
            # Convertir en DataFrame
            df = pd.DataFrame({
                "feature": list(importance_dict.keys()),
                "importance": list(importance_dict.values())
            })
            
            # Trier par importance
            df = df.sort_values("importance", ascending=False)
            
            # Exporter en CSV
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = self.export_dir / f"feature_importance_{timestamp}.csv"
            df.to_csv(filepath, index=False)
            
            # Créer une visualisation
            plt.figure(figsize=(12, 8))
            sns.barplot(x="importance", y="feature", data=df.head(15), palette="viridis")
            plt.title("Importance des caractéristiques du modèle")
            plt.xlabel("Importance relative")
            plt.ylabel("Caractéristique")
            plt.tight_layout()
            plt.savefig(self.export_dir / f"feature_importance_{timestamp}.png")
            plt.close()
            
            logger.info(f"Exported feature importance to {filepath}")
            
        except Exception as e:
            logger.error(f"Error exporting feature importance: {str(e)}")
            
    async def run_export_loop(self, interval_minutes: int = 60):
        """
        Exécute une boucle d'export périodique des résultats
        
        Args:
            interval_minutes: Intervalle entre les exports en minutes
        """
        try:
            logger.info(f"Starting export loop with interval of {interval_minutes} minutes")
            
            while True:
                # Obtenir les prédictions actuelles
                predictions = await self.predictor.predict(force=True)
                
                if predictions:
                    # Exporter en CSV
                    await self.export_predictions_to_csv(predictions)
                    
                    # Exporter les tokens à fort potentiel
                    await self.export_high_potential_tokens(predictions)
                    
                    # Générer des visualisations
                    await self.generate_prediction_visualizations(predictions)
                    
                # Exporter l'importance des caractéristiques (moins fréquemment)
                if datetime.now().hour % 6 == 0 and datetime.now().minute < 5:
                    await self.export_feature_importance()
                    
                # Attendre l'intervalle configuré
                await asyncio.sleep(interval_minutes * 60)
                
        except Exception as e:
            logger.error(f"Error in export loop: {str(e)}")
            
    async def get_dashboard_data(self) -> Dict:
        """
        Récupère les données pour le dashboard
        
        Returns:
            Dictionnaire contenant les données du dashboard
        """
        try:
            # Obtenir les prédictions actuelles
            predictions = await self.predictor.predict(force=False)
            
            # Préparer les données du dashboard
            dashboard_data = {
                "summary": {
                    "total_tokens": sum(len(tokens) for tokens in predictions.values()),
                    "high_potential_count": len(predictions.get(MLPredictor.HIGH_POTENTIAL, [])),
                    "neutral_count": len(predictions.get(MLPredictor.NEUTRAL, [])),
                    "high_risk_count": len(predictions.get(MLPredictor.HIGH_RISK, [])),
                    "last_update": datetime.now().isoformat()
                },
                "top_tokens": {
                    "high_potential": predictions.get(MLPredictor.HIGH_POTENTIAL, [])[:5],
                    "high_risk": predictions.get(MLPredictor.HIGH_RISK, [])[:5]
                },
                "chain_distribution": {}
            }
            
            # Calculer la distribution par chaîne
            chain_counts = {}
            for category, tokens in predictions.items():
                for token in tokens:
                    chain = token["chain"]
                    if chain not in chain_counts:
                        chain_counts[chain] = {
                            MLPredictor.HIGH_POTENTIAL: 0,
                            MLPredictor.NEUTRAL: 0,
                            MLPredictor.HIGH_RISK: 0
                        }
                    chain_counts[chain][category] += 1
                    
            dashboard_data["chain_distribution"] = chain_counts
            
            return dashboard_data
            
        except Exception as e:
            logger.error(f"Error getting dashboard data: {str(e)}")
            return {} 