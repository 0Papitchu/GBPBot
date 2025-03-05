from typing import Dict, List, Optional, Union, Tuple
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from loguru import logger
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.impute import SimpleImputer
import joblib
from pathlib import Path

from ..storage.database import Database
from ..utils.config import Config

class DataLoader:
    """Chargeur et préprocesseur de données pour le ML"""
    
    def __init__(self, config: Config, db: Database):
        """
        Initialise le chargeur de données
        
        Args:
            config: Configuration du système
            db: Instance de la base de données
        """
        self.config = config
        self.db = db
        self.cache_dir = config.CACHE_DIR
        
        # Préprocesseurs
        self.scaler = None
        self.imputer = None
        self.encoder = None
        
        # Charger ou initialiser les préprocesseurs
        self._init_preprocessors()
        
    def _init_preprocessors(self):
        """Initialise ou charge les préprocesseurs"""
        scaler_path = self.cache_dir / "scaler.joblib"
        imputer_path = self.cache_dir / "imputer.joblib"
        encoder_path = self.cache_dir / "encoder.joblib"
        
        try:
            if scaler_path.exists() and imputer_path.exists() and encoder_path.exists():
                logger.info("Loading preprocessors from cache")
                self.scaler = joblib.load(scaler_path)
                self.imputer = joblib.load(imputer_path)
                self.encoder = joblib.load(encoder_path)
            else:
                logger.info("Initializing new preprocessors")
                self.scaler = StandardScaler()
                self.imputer = SimpleImputer(strategy='median')
                self.encoder = OneHotEncoder(sparse_output=False, handle_unknown='ignore')
        except Exception as e:
            logger.error(f"Error initializing preprocessors: {str(e)}")
            self.scaler = StandardScaler()
            self.imputer = SimpleImputer(strategy='median')
            self.encoder = OneHotEncoder(sparse_output=False, handle_unknown='ignore')
            
    def save_preprocessors(self):
        """Sauvegarde les préprocesseurs"""
        try:
            joblib.dump(self.scaler, self.cache_dir / "scaler.joblib")
            joblib.dump(self.imputer, self.cache_dir / "imputer.joblib")
            joblib.dump(self.encoder, self.cache_dir / "encoder.joblib")
            logger.info("Preprocessors saved to cache")
        except Exception as e:
            logger.error(f"Error saving preprocessors: {str(e)}")
            
    async def load_token_data(self, days: int = 30) -> pd.DataFrame:
        """
        Charge les données des tokens depuis la base de données
        
        Args:
            days: Nombre de jours d'historique à charger
            
        Returns:
            DataFrame contenant les données des tokens
        """
        try:
            # Calculer la date limite
            start_date = datetime.now() - timedelta(days=days)
            
            # Requête SQL pour récupérer les données
            query = """
                SELECT 
                    t.address, t.chain, t.name, t.symbol, t.created_at, t.total_supply, t.holders_count,
                    m.timestamp, m.volume_24h, m.volume_1h, m.market_cap, m.tvl, m.price, 
                    m.holders, m.transactions_24h
                FROM tokens t
                JOIN token_metrics m ON t.address = m.token_address
                WHERE m.timestamp >= :start_date
                ORDER BY t.address, m.timestamp
            """
            
            # Exécuter la requête
            async with self.db.async_session() as session:
                result = await session.execute(query, {"start_date": start_date})
                rows = [dict(row) for row in result]
                
            if not rows:
                logger.warning("No token data found in database")
                return pd.DataFrame()
                
            # Convertir en DataFrame
            df = pd.DataFrame(rows)
            
            # Ajouter des colonnes dérivées
            df = self._add_derived_features(df)
            
            # Supprimer les valeurs aberrantes
            df = self._remove_outliers(df)
            
            logger.info(f"Loaded data for {df['address'].nunique()} tokens")
            return df
            
        except Exception as e:
            logger.error(f"Error loading token data: {str(e)}")
            return pd.DataFrame()
            
    def _add_derived_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Ajoute des caractéristiques dérivées au DataFrame
        
        Args:
            df: DataFrame d'entrée
            
        Returns:
            DataFrame avec caractéristiques dérivées
        """
        try:
            # Convertir les timestamps en datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['created_at'] = pd.to_datetime(df['created_at'])
            
            # Âge du token en jours
            df['token_age_days'] = (df['timestamp'] - df['created_at']).dt.total_seconds() / (24 * 3600)
            
            # Ratio volume/market cap
            df['volume_to_mcap'] = df['volume_24h'] / df['market_cap'].replace(0, np.nan)
            
            # Ratio TVL/market cap
            df['tvl_to_mcap'] = df['tvl'] / df['market_cap'].replace(0, np.nan)
            
            # Concentration des holders (holders/total_supply)
            df['holder_concentration'] = df['holders'] / df['total_supply'].replace(0, np.nan)
            
            # Activité de trading (transactions/holders)
            df['trading_activity'] = df['transactions_24h'] / df['holders'].replace(0, np.nan)
            
            # Volatilité du prix (à calculer si on a des données historiques)
            # Nécessite des données groupées par token avec plusieurs points temporels
            
            return df
            
        except Exception as e:
            logger.error(f"Error adding derived features: {str(e)}")
            return df
            
    def _remove_outliers(self, df: pd.DataFrame, z_threshold: float = 3.0) -> pd.DataFrame:
        """
        Supprime les valeurs aberrantes du DataFrame
        
        Args:
            df: DataFrame d'entrée
            z_threshold: Seuil de score Z pour considérer une valeur comme aberrante
            
        Returns:
            DataFrame sans valeurs aberrantes
        """
        try:
            # Colonnes numériques à vérifier
            numeric_cols = [
                'volume_24h', 'volume_1h', 'market_cap', 'tvl', 'price',
                'volume_to_mcap', 'tvl_to_mcap', 'trading_activity'
            ]
            
            # Copie du DataFrame
            df_clean = df.copy()
            
            # Traiter chaque colonne
            for col in numeric_cols:
                if col in df_clean.columns:
                    # Calculer le score Z
                    mean = df_clean[col].mean()
                    std = df_clean[col].std()
                    if std > 0:
                        z_scores = (df_clean[col] - mean) / std
                        # Remplacer les valeurs aberrantes par NaN
                        df_clean.loc[abs(z_scores) > z_threshold, col] = np.nan
            
            # Nombre de lignes supprimées
            removed = len(df) - len(df_clean)
            if removed > 0:
                logger.info(f"Removed {removed} outlier rows")
                
            return df_clean
            
        except Exception as e:
            logger.error(f"Error removing outliers: {str(e)}")
            return df
            
    def prepare_features(self, df: pd.DataFrame) -> Tuple[np.ndarray, List[str]]:
        """
        Prépare les caractéristiques pour le modèle ML
        
        Args:
            df: DataFrame contenant les données
            
        Returns:
            Tuple contenant les caractéristiques préparées et les noms des colonnes
        """
        try:
            if df.empty:
                logger.warning("Empty DataFrame, cannot prepare features")
                return np.array([]), []
                
            # Sélectionner les colonnes numériques
            numeric_features = [
                'volume_24h', 'volume_1h', 'market_cap', 'tvl', 'price',
                'holders', 'transactions_24h', 'token_age_days',
                'volume_to_mcap', 'tvl_to_mcap', 'holder_concentration', 'trading_activity'
            ]
            
            # Sélectionner les colonnes catégorielles
            categorical_features = ['chain']
            
            # Filtrer les colonnes existantes
            numeric_features = [col for col in numeric_features if col in df.columns]
            categorical_features = [col for col in categorical_features if col in df.columns]
            
            # Extraire les caractéristiques
            X_numeric = df[numeric_features].values
            X_categorical = df[categorical_features].values if categorical_features else None
            
            # Imputer les valeurs manquantes
            X_numeric = self.imputer.fit_transform(X_numeric)
            
            # Normaliser les caractéristiques numériques
            X_numeric = self.scaler.fit_transform(X_numeric)
            
            # Encoder les caractéristiques catégorielles
            if X_categorical is not None:
                X_categorical = self.encoder.fit_transform(X_categorical)
                
                # Combiner les caractéristiques
                X = np.hstack([X_numeric, X_categorical])
                feature_names = numeric_features + [f"{col}_{cat}" for col in categorical_features 
                                                for cat in self.encoder.categories_[0]]
            else:
                X = X_numeric
                feature_names = numeric_features
                
            # Sauvegarder les préprocesseurs
            self.save_preprocessors()
            
            return X, feature_names
            
        except Exception as e:
            logger.error(f"Error preparing features: {str(e)}")
            return np.array([]), []
            
    async def get_latest_token_data(self) -> pd.DataFrame:
        """
        Récupère les données les plus récentes pour chaque token
        
        Returns:
            DataFrame contenant les dernières données pour chaque token
        """
        try:
            # Requête SQL pour récupérer les dernières métriques de chaque token
            query = """
                WITH latest_metrics AS (
                    SELECT 
                        token_address,
                        MAX(timestamp) as latest_timestamp
                    FROM token_metrics
                    GROUP BY token_address
                )
                SELECT 
                    t.address, t.chain, t.name, t.symbol, t.created_at, t.total_supply, t.holders_count,
                    m.timestamp, m.volume_24h, m.volume_1h, m.market_cap, m.tvl, m.price, 
                    m.holders, m.transactions_24h
                FROM tokens t
                JOIN latest_metrics lm ON t.address = lm.token_address
                JOIN token_metrics m ON lm.token_address = m.token_address AND lm.latest_timestamp = m.timestamp
            """
            
            # Exécuter la requête
            async with self.db.async_session() as session:
                result = await session.execute(query)
                rows = [dict(row) for row in result]
                
            if not rows:
                logger.warning("No token data found in database")
                return pd.DataFrame()
                
            # Convertir en DataFrame
            df = pd.DataFrame(rows)
            
            # Ajouter des colonnes dérivées
            df = self._add_derived_features(df)
            
            logger.info(f"Loaded latest data for {len(df)} tokens")
            return df
            
        except Exception as e:
            logger.error(f"Error loading latest token data: {str(e)}")
            return pd.DataFrame()
            
    async def get_token_price_history(self, token_address: str, days: int = 30) -> pd.DataFrame:
        """
        Récupère l'historique des prix d'un token
        
        Args:
            token_address: Adresse du token
            days: Nombre de jours d'historique
            
        Returns:
            DataFrame contenant l'historique des prix
        """
        try:
            # Calculer la date limite
            start_date = datetime.now() - timedelta(days=days)
            
            # Requête SQL
            query = """
                SELECT 
                    token_address, timestamp, price, volume_24h
                FROM token_metrics
                WHERE token_address = :token_address
                AND timestamp >= :start_date
                ORDER BY timestamp
            """
            
            # Exécuter la requête
            async with self.db.async_session() as session:
                result = await session.execute(query, {
                    "token_address": token_address,
                    "start_date": start_date
                })
                rows = [dict(row) for row in result]
                
            if not rows:
                logger.warning(f"No price history found for token {token_address}")
                return pd.DataFrame()
                
            # Convertir en DataFrame
            df = pd.DataFrame(rows)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            return df
            
        except Exception as e:
            logger.error(f"Error getting token price history: {str(e)}")
            return pd.DataFrame() 