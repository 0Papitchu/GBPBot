"""
Module de base pour le système de monitoring unifié de GBPBot
============================================================

Ce module définit l'interface commune pour tous les différents types de
moniteurs (ressources système, performances, transactions, etc.) dans GBPBot.
Il établit le contrat que tous les moniteurs spécifiques doivent respecter.
"""

import threading
import time
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable, TypeVar, Generic, Union, Tuple

# Configuration du logging
logger = logging.getLogger("gbpbot.monitoring")

# Type générique pour les métriques
MetricValue = Union[float, int, bool, str]
MetricDict = Dict[str, MetricValue]
CallbackType = Callable[[str, MetricValue, Optional[MetricValue]], None]

class MonitoringException(Exception):
    """Exception personnalisée pour les erreurs de monitoring"""
    pass

class BaseMonitor(ABC):
    """
    Classe abstraite définissant l'interface commune pour tous les moniteurs.
    
    Tous les moniteurs spécifiques doivent hériter de cette classe et implémenter
    ses méthodes abstraites. Cela assure une interface cohérente pour tous les
    systèmes de monitoring dans GBPBot.
    """
    
    def __init__(self, name: str, check_interval: float = 5.0, auto_start: bool = False):
        """
        Initialise un moniteur de base.
        
        Args:
            name: Nom unique du moniteur
            check_interval: Intervalle entre les vérifications en secondes
            auto_start: Démarrer automatiquement le monitoring à l'initialisation
        """
        self.name = name
        self.check_interval = check_interval
        self.running = False
        self.monitor_thread = None
        self.last_check_time = None
        self.metrics = {}  # Stockage des métriques
        self.callbacks = {}  # Callbacks pour les alertes
        self.thresholds = {}  # Seuils d'alerte par métrique
        
        # Verrou pour l'accès concurrent aux métriques
        self._metrics_lock = threading.RLock()
        
        if auto_start:
            self.start()
    
    def start(self) -> bool:
        """
        Démarre le monitoring en arrière-plan.
        
        Returns:
            bool: True si le démarrage a réussi, False sinon
        """
        if self.running:
            logger.warning(f"Le moniteur {self.name} est déjà en cours d'exécution")
            return True
        
        self.running = True
        self.monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            name=f"monitoring-{self.name}",
            daemon=True
        )
        self.monitor_thread.start()
        logger.info(f"Moniteur {self.name} démarré")
        return True
    
    def stop(self) -> bool:
        """
        Arrête le monitoring.
        
        Returns:
            bool: True si l'arrêt a réussi, False sinon
        """
        if not self.running:
            logger.warning(f"Le moniteur {self.name} n'est pas en cours d'exécution")
            return True
        
        self.running = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2.0)
        
        logger.info(f"Moniteur {self.name} arrêté")
        return True
    
    def _monitoring_loop(self) -> None:
        """Boucle principale du thread de monitoring."""
        while self.running:
            try:
                self.last_check_time = datetime.now()
                self.collect_metrics()
                self.check_thresholds()
                
                # Attendre l'intervalle de vérification
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Erreur dans la boucle de monitoring {self.name}: {str(e)}")
                time.sleep(max(1.0, self.check_interval / 2))  # Réduire l'intervalle en cas d'erreur
    
    @abstractmethod
    def collect_metrics(self) -> None:
        """
        Collecte les métriques et met à jour l'état interne.
        
        Cette méthode doit être implémentée par les classes dérivées et doit
        collecter les métriques spécifiques au type de moniteur.
        """
        pass
    
    def check_thresholds(self) -> None:
        """Vérifie si les métriques dépassent les seuils définis et déclenche les alertes."""
        with self._metrics_lock:
            for metric_name, value in self.metrics.items():
                if metric_name in self.thresholds:
                    threshold = self.thresholds[metric_name]
                    if self._is_threshold_exceeded(metric_name, value, threshold):
                        self._trigger_alert(metric_name, value, threshold)
    
    def _is_threshold_exceeded(self, metric_name: str, value: MetricValue, threshold: MetricValue) -> bool:
        """
        Vérifie si une métrique dépasse son seuil.
        
        Args:
            metric_name: Nom de la métrique
            value: Valeur actuelle de la métrique
            threshold: Seuil à vérifier
            
        Returns:
            bool: True si le seuil est dépassé, False sinon
        """
        # Logique de base: comparaison directe pour les types numériques
        if isinstance(value, (int, float)) and isinstance(threshold, (int, float)):
            return value >= threshold
        
        # Pour les métriques booléennes, le seuil est la valeur attendue
        if isinstance(value, bool) and isinstance(threshold, bool):
            return value == threshold
        
        # Comparaison chaîne de caractères
        if isinstance(value, str) and isinstance(threshold, str):
            return value == threshold
        
        # Par défaut, pas de dépassement
        return False
    
    def _trigger_alert(self, metric_name: str, value: MetricValue, threshold: MetricValue) -> None:
        """
        Déclenche les callbacks d'alerte pour une métrique.
        
        Args:
            metric_name: Nom de la métrique
            value: Valeur actuelle de la métrique
            threshold: Seuil dépassé
        """
        if metric_name in self.callbacks:
            for callback in self.callbacks[metric_name]:
                try:
                    callback(metric_name, value, threshold)
                except Exception as e:
                    logger.error(f"Erreur dans le callback pour {metric_name}: {str(e)}")
    
    def register_callback(self, metric_name: str, callback: CallbackType) -> bool:
        """
        Enregistre un callback pour une métrique.
        
        Args:
            metric_name: Nom de la métrique
            callback: Fonction à appeler quand le seuil est dépassé
            
        Returns:
            bool: True si l'enregistrement a réussi, False sinon
        """
        if metric_name not in self.callbacks:
            self.callbacks[metric_name] = []
        
        if callback not in self.callbacks[metric_name]:
            self.callbacks[metric_name].append(callback)
            return True
        
        return False
    
    def unregister_callback(self, metric_name: str, callback: CallbackType) -> bool:
        """
        Supprime un callback pour une métrique.
        
        Args:
            metric_name: Nom de la métrique
            callback: Fonction à supprimer
            
        Returns:
            bool: True si la suppression a réussi, False sinon
        """
        if metric_name in self.callbacks and callback in self.callbacks[metric_name]:
            self.callbacks[metric_name].remove(callback)
            return True
        
        return False
    
    def set_threshold(self, metric_name: str, threshold: MetricValue) -> None:
        """
        Définit un seuil pour une métrique.
        
        Args:
            metric_name: Nom de la métrique
            threshold: Valeur seuil
        """
        self.thresholds[metric_name] = threshold
    
    def get_metric(self, metric_name: str) -> Optional[MetricValue]:
        """
        Récupère la valeur d'une métrique.
        
        Args:
            metric_name: Nom de la métrique
            
        Returns:
            Optional[MetricValue]: Valeur de la métrique ou None si non trouvée
        """
        with self._metrics_lock:
            return self.metrics.get(metric_name)
    
    def get_all_metrics(self) -> Dict[str, MetricValue]:
        """
        Récupère toutes les métriques.
        
        Returns:
            Dict[str, MetricValue]: Dictionnaire de toutes les métriques
        """
        with self._metrics_lock:
            return self.metrics.copy()
    
    def update_metric(self, metric_name: str, value: MetricValue) -> None:
        """
        Met à jour la valeur d'une métrique.
        
        Args:
            metric_name: Nom de la métrique
            value: Nouvelle valeur
        """
        with self._metrics_lock:
            self.metrics[metric_name] = value
    
    def reset_metrics(self) -> None:
        """Réinitialise toutes les métriques."""
        with self._metrics_lock:
            self.metrics.clear()
    
    def get_status(self) -> Dict[str, Any]:
        """
        Récupère l'état actuel du moniteur.
        
        Returns:
            Dict[str, Any]: État actuel du moniteur
        """
        return {
            "name": self.name,
            "running": self.running,
            "last_check": self.last_check_time.isoformat() if self.last_check_time else None,
            "check_interval": self.check_interval,
            "metrics_count": len(self.metrics),
            "thresholds_count": len(self.thresholds),
            "callbacks_count": sum(len(callbacks) for callbacks in self.callbacks.values())
        } 