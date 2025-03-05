import numpy as np
import time
from typing import Dict, List, Optional, Tuple, Any, Callable, Union
from loguru import logger
from collections import deque
from gbpbot.config.config_manager import config_manager

class AnomalyDetector:
    """
    Détecteur d'anomalies pour identifier les prix anormaux
    """
    
    _instance = None
    
    def __new__(cls):
        """Implémentation du pattern Singleton"""
        if cls._instance is None:
            cls._instance = super(AnomalyDetector, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """
        Initialise le détecteur d'anomalies
        """
        if not hasattr(self, 'initialized'):
            # Charger la configuration
            self.config = config_manager.get_config("anomaly_detection")
            
            # Initialiser les données
            self.price_history = {}
            self.anomalies = {}
            self.last_check = 0
            
            # Marquer comme initialisé
            self.initialized = True
            logger.info("Détecteur d'anomalies initialisé")
    
    def add_price(self, pair: str, price: float, source: str = "unknown") -> None:
        """
        Ajoute un prix à l'historique
        
        Args:
            pair: Paire de trading (ex: WAVAX/USDC)
            price: Prix
            source: Source du prix (ex: binance, traderjoe, etc.)
        """
        # Créer l'entrée si elle n'existe pas
        if pair not in self.price_history:
            self.price_history[pair] = {}
        
        if source not in self.price_history[pair]:
            self.price_history[pair][source] = {
                "prices": deque(maxlen=self.config["window_size"]),
                "timestamps": deque(maxlen=self.config["window_size"]),
                "last_anomaly": None
            }
        
        # Ajouter le prix et le timestamp
        self.price_history[pair][source]["prices"].append(price)
        self.price_history[pair][source]["timestamps"].append(time.time())
        
        # Vérifier les anomalies si nécessaire
        current_time = time.time()
        if current_time - self.last_check > self.config["check_interval"]:
            self.check_anomalies()
            self.last_check = current_time
    
    def check_anomalies(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Vérifie les anomalies pour toutes les paires et sources
        
        Returns:
            Dict: Anomalies détectées par paire
        """
        # Réinitialiser les anomalies
        self.anomalies = {}
        
        # Parcourir toutes les paires
        for pair, sources in self.price_history.items():
            # Vérifier les anomalies pour chaque source
            for source, data in sources.items():
                # Vérifier si nous avons suffisamment de données
                if len(data["prices"]) < self.config["min_data_points"]:
                    continue
                
                # Convertir en numpy array pour les calculs
                prices = np.array(data["prices"])
                timestamps = np.array(data["timestamps"])
                
                # Calculer les statistiques
                mean = np.mean(prices)
                std = np.std(prices)
                
                # Éviter la division par zéro
                if std == 0:
                    continue
                
                # Calculer les scores Z
                z_scores = (prices - mean) / std
                
                # Identifier les anomalies
                anomaly_indices = np.where(np.abs(z_scores) > self.config["z_score_threshold"])[0]
                
                if len(anomaly_indices) > 0:
                    # Créer l'entrée pour la paire si elle n'existe pas
                    if pair not in self.anomalies:
                        self.anomalies[pair] = []
                    
                    # Ajouter les anomalies
                    for idx in anomaly_indices:
                        anomaly = {
                            "pair": pair,
                            "source": source,
                            "price": float(prices[idx]),
                            "timestamp": float(timestamps[idx]),
                            "z_score": float(z_scores[idx]),
                            "mean": float(mean),
                            "std": float(std),
                            "deviation_percent": float(((prices[idx] - mean) / mean) * 100)
                        }
                        
                        # Ajouter l'anomalie à la liste
                        self.anomalies[pair].append(anomaly)
                        
                        # Mettre à jour la dernière anomalie
                        data["last_anomaly"] = anomaly
                        
                        logger.warning(f"Anomalie détectée pour {pair} ({source}): prix={prices[idx]:.4f}, z-score={z_scores[idx]:.2f}, déviation={anomaly['deviation_percent']:.2f}%")
        
        return self.anomalies
    
    def is_price_anomaly(self, pair: str, price: float, source: str = "unknown") -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Vérifie si un prix est une anomalie
        
        Args:
            pair: Paire de trading (ex: WAVAX/USDC)
            price: Prix à vérifier
            source: Source du prix (ex: binance, traderjoe, etc.)
            
        Returns:
            Tuple[bool, Optional[Dict]]: (est_anomalie, détails_anomalie)
        """
        # Ajouter le prix à l'historique
        self.add_price(pair, price, source)
        
        # Vérifier si nous avons suffisamment de données
        if pair not in self.price_history or source not in self.price_history[pair]:
            return False, None
        
        data = self.price_history[pair][source]
        if len(data["prices"]) < self.config["min_data_points"]:
            return False, None
        
        # Convertir en numpy array pour les calculs
        prices = np.array(data["prices"])
        
        # Calculer les statistiques
        mean = np.mean(prices)
        std = np.std(prices)
        
        # Éviter la division par zéro
        if std == 0:
            return False, None
        
        # Calculer le score Z
        z_score = (price - mean) / std
        
        # Vérifier si c'est une anomalie
        is_anomaly = abs(z_score) > self.config["z_score_threshold"]
        
        if is_anomaly:
            # Créer les détails de l'anomalie
            anomaly_details = {
                "pair": pair,
                "source": source,
                "price": float(price),
                "timestamp": float(time.time()),
                "z_score": float(z_score),
                "mean": float(mean),
                "std": float(std),
                "deviation_percent": float(((price - mean) / mean) * 100)
            }
            
            # Mettre à jour la dernière anomalie
            data["last_anomaly"] = anomaly_details
            
            # Ajouter à la liste des anomalies
            if pair not in self.anomalies:
                self.anomalies[pair] = []
            self.anomalies[pair].append(anomaly_details)
            
            logger.warning(f"Anomalie détectée pour {pair} ({source}): prix={price:.4f}, z-score={z_score:.2f}, déviation={anomaly_details['deviation_percent']:.2f}%")
            
            return True, anomaly_details
        
        return False, None
    
    def get_price_statistics(self, pair: str, source: str = "unknown") -> Optional[Dict[str, Any]]:
        """
        Récupère les statistiques de prix pour une paire et une source
        
        Args:
            pair: Paire de trading (ex: WAVAX/USDC)
            source: Source du prix (ex: binance, traderjoe, etc.)
            
        Returns:
            Dict: Statistiques de prix
        """
        # Vérifier si nous avons des données
        if pair not in self.price_history or source not in self.price_history[pair]:
            return None
        
        data = self.price_history[pair][source]
        if len(data["prices"]) < self.config["min_data_points"]:
            return None
        
        # Convertir en numpy array pour les calculs
        prices = np.array(data["prices"])
        timestamps = np.array(data["timestamps"])
        
        # Calculer les statistiques
        mean = np.mean(prices)
        std = np.std(prices)
        median = np.median(prices)
        min_price = np.min(prices)
        max_price = np.max(prices)
        
        # Calculer les variations
        price_range = max_price - min_price
        volatility = std / mean * 100  # en pourcentage
        
        # Calculer les tendances
        if len(prices) >= 2:
            first_price = prices[0]
            last_price = prices[-1]
            price_change = last_price - first_price
            price_change_percent = (price_change / first_price) * 100
        else:
            price_change = 0
            price_change_percent = 0
        
        return {
            "pair": pair,
            "source": source,
            "count": len(prices),
            "mean": float(mean),
            "median": float(median),
            "std": float(std),
            "min": float(min_price),
            "max": float(max_price),
            "range": float(price_range),
            "volatility": float(volatility),
            "price_change": float(price_change),
            "price_change_percent": float(price_change_percent),
            "last_price": float(prices[-1]) if len(prices) > 0 else None,
            "last_timestamp": float(timestamps[-1]) if len(timestamps) > 0 else None,
            "last_anomaly": data["last_anomaly"]
        }
    
    def get_all_anomalies(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Récupère toutes les anomalies détectées
        
        Returns:
            Dict: Anomalies par paire
        """
        return self.anomalies
    
    def get_anomalies_for_pair(self, pair: str) -> List[Dict[str, Any]]:
        """
        Récupère les anomalies pour une paire spécifique
        
        Args:
            pair: Paire de trading (ex: WAVAX/USDC)
            
        Returns:
            List: Anomalies pour la paire
        """
        return self.anomalies.get(pair, [])
    
    def clear_history(self, pair: Optional[str] = None, source: Optional[str] = None) -> None:
        """
        Efface l'historique des prix
        
        Args:
            pair: Paire de trading à effacer (None pour toutes)
            source: Source à effacer (None pour toutes)
        """
        if pair is None:
            # Effacer tout l'historique
            self.price_history = {}
            self.anomalies = {}
            logger.info("Historique des prix effacé")
            return
        
        if pair in self.price_history:
            if source is None:
                # Effacer toutes les sources pour la paire
                self.price_history[pair] = {}
                if pair in self.anomalies:
                    self.anomalies[pair] = []
                logger.info(f"Historique des prix effacé pour {pair}")
            elif source in self.price_history[pair]:
                # Effacer une source spécifique
                del self.price_history[pair][source]
                if pair in self.anomalies:
                    self.anomalies[pair] = [a for a in self.anomalies[pair] if a["source"] != source]
                logger.info(f"Historique des prix effacé pour {pair} ({source})")

# Créer une instance singleton
anomaly_detector = AnomalyDetector() 