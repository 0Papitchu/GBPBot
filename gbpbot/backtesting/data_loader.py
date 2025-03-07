#!/usr/bin/env python3
"""
Module de chargement de données historiques pour le backtesting de GBPBot.

Ce module fournit des fonctionnalités pour charger et préparer des données historiques
de prix, volumes et autres métriques de marché pour les tests de stratégies de trading.
"""

import os
import json
import time
import logging
import asyncio
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime, timedelta
import aiohttp
import ccxt.async_support as ccxt

from gbpbot.utils.config import get_config
from gbpbot.utils.exceptions import ConfigurationError

# Configuration du logger
logger = logging.getLogger(__name__)

class DataLoader:
    """
    Classe pour charger et préparer des données historiques pour le backtesting.
    
    Cette classe fournit des méthodes pour charger des données depuis différentes sources
    (fichiers CSV, APIs, bases de données) et les préparer pour le backtesting.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialise le chargeur de données.
        
        Args:
            config: Configuration pour le chargeur de données
        """
        self.config = config
        
        # Répertoire de données
        self.data_dir = config.get("DATA_DIR", "data/historical")
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Sources de données
        self.data_sources = {
            "binance": self._load_from_binance,
            "kucoin": self._load_from_kucoin,
            "gateio": self._load_from_gateio,
            "csv": self._load_from_csv,
            "json": self._load_from_json,
            "database": self._load_from_database
        }
        
        # Paramètres par défaut
        self.default_timeframe = config.get("DEFAULT_TIMEFRAME", "1m")
        self.default_limit = int(config.get("DEFAULT_LIMIT", 1000))
        
        logger.info("Chargeur de données initialisé")
    
    async def load_data(self, symbol: str, timeframe: Optional[str] = None,
                      start_time: Optional[Union[int, datetime]] = None,
                      end_time: Optional[Union[int, datetime]] = None,
                      source: str = "binance", limit: Optional[int] = None,
                      columns: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Charge des données historiques pour un symbole.
        
        Args:
            symbol: Symbole du marché (ex: "BTC/USDT")
            timeframe: Intervalle de temps (ex: "1m", "1h", "1d")
            start_time: Heure de début (timestamp ou datetime)
            end_time: Heure de fin (timestamp ou datetime)
            source: Source des données (ex: "binance", "csv")
            limit: Nombre maximum de points de données
            columns: Colonnes à inclure dans le DataFrame
            
        Returns:
            DataFrame contenant les données historiques
        """
        # Paramètres par défaut
        timeframe = timeframe or self.default_timeframe
        limit = limit or self.default_limit
        
        # Convertir les datetime en timestamp si nécessaire
        if isinstance(start_time, datetime):
            start_time = int(start_time.timestamp() * 1000)
        
        if isinstance(end_time, datetime):
            end_time = int(end_time.timestamp() * 1000)
        
        # Vérifier que la source est supportée
        if source not in self.data_sources:
            raise ValueError(f"Source de données non supportée: {source}")
        
        # Charger les données depuis la source spécifiée
        loader_func = self.data_sources[source]
        df = await loader_func(symbol, timeframe, start_time, end_time, limit)
        
        # Filtrer les colonnes si spécifié
        if columns:
            df = df[columns]
        
        logger.info(f"Chargé {len(df)} points de données pour {symbol} ({timeframe}) depuis {source}")
        
        return df
    
    async def load_multiple_symbols(self, symbols: List[str], timeframe: Optional[str] = None,
                                  start_time: Optional[Union[int, datetime]] = None,
                                  end_time: Optional[Union[int, datetime]] = None,
                                  source: str = "binance", limit: Optional[int] = None,
                                  columns: Optional[List[str]] = None) -> Dict[str, pd.DataFrame]:
        """
        Charge des données historiques pour plusieurs symboles.
        
        Args:
            symbols: Liste des symboles du marché
            timeframe: Intervalle de temps (ex: "1m", "1h", "1d")
            start_time: Heure de début (timestamp ou datetime)
            end_time: Heure de fin (timestamp ou datetime)
            source: Source des données (ex: "binance", "csv")
            limit: Nombre maximum de points de données
            columns: Colonnes à inclure dans le DataFrame
            
        Returns:
            Dictionnaire de DataFrames contenant les données historiques pour chaque symbole
        """
        results = {}
        
        # Charger les données pour chaque symbole
        for symbol in symbols:
            try:
                df = await self.load_data(
                    symbol, timeframe, start_time, end_time, source, limit, columns
                )
                results[symbol] = df
            except Exception as e:
                logger.error(f"Erreur lors du chargement des données pour {symbol}: {e}")
        
        return results
    
    async def save_data(self, df: pd.DataFrame, symbol: str, timeframe: str, 
                      format: str = "csv", filename: Optional[str] = None) -> str:
        """
        Sauvegarde des données historiques dans un fichier.
        
        Args:
            df: DataFrame contenant les données historiques
            symbol: Symbole du marché
            timeframe: Intervalle de temps
            format: Format de fichier (ex: "csv", "json")
            filename: Nom de fichier personnalisé
            
        Returns:
            Chemin du fichier sauvegardé
        """
        # Créer le nom de fichier si non spécifié
        if not filename:
            # Remplacer les caractères non valides dans le nom de fichier
            safe_symbol = symbol.replace("/", "_")
            filename = f"{safe_symbol}_{timeframe}_{int(time.time())}"
        
        # Créer le chemin complet
        filepath = os.path.join(self.data_dir, f"{filename}.{format}")
        
        # Sauvegarder dans le format spécifié
        if format.lower() == "csv":
            df.to_csv(filepath, index=True)
        elif format.lower() == "json":
            df.to_json(filepath, orient="records")
        elif format.lower() == "parquet":
            df.to_parquet(filepath, index=True)
        elif format.lower() == "pickle":
            df.to_pickle(filepath)
        else:
            raise ValueError(f"Format de fichier non supporté: {format}")
        
        logger.info(f"Données sauvegardées dans {filepath}")
        
        return filepath
    
    async def _load_from_binance(self, symbol: str, timeframe: str,
                               start_time: Optional[int] = None,
                               end_time: Optional[int] = None,
                               limit: int = 1000) -> pd.DataFrame:
        """
        Charge des données historiques depuis Binance.
        
        Args:
            symbol: Symbole du marché (ex: "BTC/USDT")
            timeframe: Intervalle de temps (ex: "1m", "1h", "1d")
            start_time: Timestamp de début en millisecondes
            end_time: Timestamp de fin en millisecondes
            limit: Nombre maximum de points de données
            
        Returns:
            DataFrame contenant les données historiques
        """
        try:
            # Initialiser le client Binance
            exchange = ccxt.binance()
            
            # Paramètres de la requête
            params = {}
            if start_time:
                params["since"] = start_time
            if end_time:
                params["until"] = end_time
            
            # Récupérer les données OHLCV
            ohlcv = await exchange.fetch_ohlcv(symbol, timeframe, limit=limit, params=params)
            
            # Fermer le client
            await exchange.close()
            
            # Convertir en DataFrame
            df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
            
            # Convertir le timestamp en datetime
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            
            # Définir le timestamp comme index
            df.set_index("timestamp", inplace=True)
            
            return df
            
        except Exception as e:
            logger.error(f"Erreur lors du chargement des données depuis Binance: {e}")
            raise
    
    async def _load_from_kucoin(self, symbol: str, timeframe: str,
                              start_time: Optional[int] = None,
                              end_time: Optional[int] = None,
                              limit: int = 1000) -> pd.DataFrame:
        """
        Charge des données historiques depuis KuCoin.
        
        Args:
            symbol: Symbole du marché (ex: "BTC/USDT")
            timeframe: Intervalle de temps (ex: "1m", "1h", "1d")
            start_time: Timestamp de début en millisecondes
            end_time: Timestamp de fin en millisecondes
            limit: Nombre maximum de points de données
            
        Returns:
            DataFrame contenant les données historiques
        """
        try:
            # Initialiser le client KuCoin
            exchange = ccxt.kucoin()
            
            # Paramètres de la requête
            params = {}
            if start_time:
                params["since"] = start_time
            if end_time:
                params["until"] = end_time
            
            # Récupérer les données OHLCV
            ohlcv = await exchange.fetch_ohlcv(symbol, timeframe, limit=limit, params=params)
            
            # Fermer le client
            await exchange.close()
            
            # Convertir en DataFrame
            df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
            
            # Convertir le timestamp en datetime
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            
            # Définir le timestamp comme index
            df.set_index("timestamp", inplace=True)
            
            return df
            
        except Exception as e:
            logger.error(f"Erreur lors du chargement des données depuis KuCoin: {e}")
            raise
    
    async def _load_from_gateio(self, symbol: str, timeframe: str,
                              start_time: Optional[int] = None,
                              end_time: Optional[int] = None,
                              limit: int = 1000) -> pd.DataFrame:
        """
        Charge des données historiques depuis Gate.io.
        
        Args:
            symbol: Symbole du marché (ex: "BTC/USDT")
            timeframe: Intervalle de temps (ex: "1m", "1h", "1d")
            start_time: Timestamp de début en millisecondes
            end_time: Timestamp de fin en millisecondes
            limit: Nombre maximum de points de données
            
        Returns:
            DataFrame contenant les données historiques
        """
        try:
            # Initialiser le client Gate.io
            exchange = ccxt.gateio()
            
            # Paramètres de la requête
            params = {}
            if start_time:
                params["since"] = start_time
            if end_time:
                params["until"] = end_time
            
            # Récupérer les données OHLCV
            ohlcv = await exchange.fetch_ohlcv(symbol, timeframe, limit=limit, params=params)
            
            # Fermer le client
            await exchange.close()
            
            # Convertir en DataFrame
            df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
            
            # Convertir le timestamp en datetime
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            
            # Définir le timestamp comme index
            df.set_index("timestamp", inplace=True)
            
            return df
            
        except Exception as e:
            logger.error(f"Erreur lors du chargement des données depuis Gate.io: {e}")
            raise
    
    async def _load_from_csv(self, symbol: str, timeframe: str,
                           start_time: Optional[int] = None,
                           end_time: Optional[int] = None,
                           limit: int = 1000) -> pd.DataFrame:
        """
        Charge des données historiques depuis un fichier CSV.
        
        Args:
            symbol: Symbole du marché (ex: "BTC/USDT")
            timeframe: Intervalle de temps (ex: "1m", "1h", "1d")
            start_time: Timestamp de début en millisecondes
            end_time: Timestamp de fin en millisecondes
            limit: Nombre maximum de points de données
            
        Returns:
            DataFrame contenant les données historiques
        """
        try:
            # Remplacer les caractères non valides dans le nom de fichier
            safe_symbol = symbol.replace("/", "_")
            
            # Chercher les fichiers correspondants
            pattern = f"{safe_symbol}_{timeframe}_*.csv"
            matching_files = []
            
            for filename in os.listdir(self.data_dir):
                if filename.startswith(f"{safe_symbol}_{timeframe}_") and filename.endswith(".csv"):
                    matching_files.append(os.path.join(self.data_dir, filename))
            
            if not matching_files:
                raise FileNotFoundError(f"Aucun fichier trouvé pour {symbol} ({timeframe})")
            
            # Utiliser le fichier le plus récent
            filepath = sorted(matching_files)[-1]
            
            # Charger le CSV
            df = pd.read_csv(filepath, index_col=0, parse_dates=True)
            
            # Filtrer par date si spécifié
            if start_time:
                start_dt = pd.to_datetime(start_time, unit="ms")
                df = df[df.index >= start_dt]
            
            if end_time:
                end_dt = pd.to_datetime(end_time, unit="ms")
                df = df[df.index <= end_dt]
            
            # Limiter le nombre de points de données
            if limit and len(df) > limit:
                df = df.iloc[-limit:]
            
            return df
            
        except Exception as e:
            logger.error(f"Erreur lors du chargement des données depuis CSV: {e}")
            raise
    
    async def _load_from_json(self, symbol: str, timeframe: str,
                            start_time: Optional[int] = None,
                            end_time: Optional[int] = None,
                            limit: int = 1000) -> pd.DataFrame:
        """
        Charge des données historiques depuis un fichier JSON.
        
        Args:
            symbol: Symbole du marché (ex: "BTC/USDT")
            timeframe: Intervalle de temps (ex: "1m", "1h", "1d")
            start_time: Timestamp de début en millisecondes
            end_time: Timestamp de fin en millisecondes
            limit: Nombre maximum de points de données
            
        Returns:
            DataFrame contenant les données historiques
        """
        try:
            # Remplacer les caractères non valides dans le nom de fichier
            safe_symbol = symbol.replace("/", "_")
            
            # Chercher les fichiers correspondants
            pattern = f"{safe_symbol}_{timeframe}_*.json"
            matching_files = []
            
            for filename in os.listdir(self.data_dir):
                if filename.startswith(f"{safe_symbol}_{timeframe}_") and filename.endswith(".json"):
                    matching_files.append(os.path.join(self.data_dir, filename))
            
            if not matching_files:
                raise FileNotFoundError(f"Aucun fichier trouvé pour {symbol} ({timeframe})")
            
            # Utiliser le fichier le plus récent
            filepath = sorted(matching_files)[-1]
            
            # Charger le JSON
            df = pd.read_json(filepath, orient="records")
            
            # Convertir le timestamp en datetime si nécessaire
            if "timestamp" in df.columns and not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
                df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            
            # Définir le timestamp comme index si nécessaire
            if "timestamp" in df.columns and df.index.name != "timestamp":
                df.set_index("timestamp", inplace=True)
            
            # Filtrer par date si spécifié
            if start_time:
                start_dt = pd.to_datetime(start_time, unit="ms")
                df = df[df.index >= start_dt]
            
            if end_time:
                end_dt = pd.to_datetime(end_time, unit="ms")
                df = df[df.index <= end_dt]
            
            # Limiter le nombre de points de données
            if limit and len(df) > limit:
                df = df.iloc[-limit:]
            
            return df
            
        except Exception as e:
            logger.error(f"Erreur lors du chargement des données depuis JSON: {e}")
            raise
    
    async def _load_from_database(self, symbol: str, timeframe: str,
                                start_time: Optional[int] = None,
                                end_time: Optional[int] = None,
                                limit: int = 1000) -> pd.DataFrame:
        """
        Charge des données historiques depuis une base de données.
        
        Args:
            symbol: Symbole du marché (ex: "BTC/USDT")
            timeframe: Intervalle de temps (ex: "1m", "1h", "1d")
            start_time: Timestamp de début en millisecondes
            end_time: Timestamp de fin en millisecondes
            limit: Nombre maximum de points de données
            
        Returns:
            DataFrame contenant les données historiques
        """
        # Cette méthode est un placeholder pour l'implémentation future
        # Elle devrait être implémentée en fonction de la base de données utilisée
        
        logger.warning("Chargement depuis la base de données non implémenté")
        raise NotImplementedError("Chargement depuis la base de données non implémenté")
    
    async def download_historical_data(self, symbol: str, timeframe: str,
                                     start_time: Optional[Union[int, datetime]] = None,
                                     end_time: Optional[Union[int, datetime]] = None,
                                     source: str = "binance", save_format: str = "csv") -> str:
        """
        Télécharge et sauvegarde des données historiques.
        
        Args:
            symbol: Symbole du marché (ex: "BTC/USDT")
            timeframe: Intervalle de temps (ex: "1m", "1h", "1d")
            start_time: Heure de début (timestamp ou datetime)
            end_time: Heure de fin (timestamp ou datetime)
            source: Source des données (ex: "binance", "kucoin")
            save_format: Format de sauvegarde (ex: "csv", "json")
            
        Returns:
            Chemin du fichier sauvegardé
        """
        # Charger les données
        df = await self.load_data(symbol, timeframe, start_time, end_time, source)
        
        # Sauvegarder les données
        filepath = await self.save_data(df, symbol, timeframe, save_format)
        
        return filepath
    
    async def resample_data(self, df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        """
        Rééchantillonne les données à un intervalle de temps différent.
        
        Args:
            df: DataFrame contenant les données historiques
            timeframe: Nouvel intervalle de temps (ex: "1h", "1d")
            
        Returns:
            DataFrame rééchantillonné
        """
        # Vérifier que le DataFrame a un index datetime
        if not pd.api.types.is_datetime64_any_dtype(df.index):
            raise ValueError("Le DataFrame doit avoir un index datetime")
        
        # Mapper les timeframes aux règles de rééchantillonnage pandas
        timeframe_map = {
            "1m": "1min",
            "3m": "3min",
            "5m": "5min",
            "15m": "15min",
            "30m": "30min",
            "1h": "1H",
            "2h": "2H",
            "4h": "4H",
            "6h": "6H",
            "8h": "8H",
            "12h": "12H",
            "1d": "1D",
            "3d": "3D",
            "1w": "1W",
            "1M": "1M"
        }
        
        if timeframe not in timeframe_map:
            raise ValueError(f"Intervalle de temps non supporté: {timeframe}")
        
        rule = timeframe_map[timeframe]
        
        # Rééchantillonner les données
        resampled = df.resample(rule).agg({
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum"
        })
        
        # Supprimer les lignes avec des valeurs manquantes
        resampled.dropna(inplace=True)
        
        return resampled
    
    async def merge_dataframes(self, dfs: List[pd.DataFrame], on: str = "timestamp") -> pd.DataFrame:
        """
        Fusionne plusieurs DataFrames en un seul.
        
        Args:
            dfs: Liste de DataFrames à fusionner
            on: Colonne ou index sur lequel fusionner
            
        Returns:
            DataFrame fusionné
        """
        if not dfs:
            raise ValueError("La liste de DataFrames est vide")
        
        # Si on fusionne sur l'index, réinitialiser l'index
        if on == "timestamp" and all(df.index.name == "timestamp" for df in dfs):
            dfs = [df.reset_index() for df in dfs]
        
        # Fusionner les DataFrames
        result = dfs[0]
        for i, df in enumerate(dfs[1:], 1):
            # Ajouter un suffixe pour éviter les conflits de noms de colonnes
            result = pd.merge(result, df, on=on, suffixes=("", f"_{i}"))
        
        # Remettre le timestamp comme index si nécessaire
        if on == "timestamp" and "timestamp" in result.columns:
            result.set_index("timestamp", inplace=True)
        
        return result 