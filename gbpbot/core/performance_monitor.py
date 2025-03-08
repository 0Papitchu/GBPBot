"""
Module de Monitoring des Performances pour GBPBot
=================================================

Ce module fournit des fonctionnalités pour surveiller les performances
du GBPBot en temps réel, incluant l'utilisation des ressources système
(CPU, RAM, disque, réseau) et des métriques spécifiques à l'application
(temps de réponse, taux de succès des transactions, etc.).

Il permet d'identifier les goulots d'étranglement et d'optimiser les
performances du bot pour un trading plus efficace et rapide.
"""

import functools
import time
import threading
import logging
import platform
import json
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable, TypeVar, cast
from collections import deque
from pathlib import Path

# Gestion de l'import de psutil
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    # Classe factice pour éviter les erreurs
    class FakePsutil:
        @staticmethod
        def cpu_percent(*args, **kwargs):
            return 0.0
        @staticmethod
        def virtual_memory():
            class FakeMemory:
                percent = 0.0
                available = 0
            return FakeMemory()
        @staticmethod
        def disk_usage(path):
            class FakeDisk:
                percent = 0.0
            return FakeDisk()
        @staticmethod
        def Process(*args, **kwargs):
            class FakeProcess:
                def cpu_percent(self, *args, **kwargs):
                    return 0.0
                def memory_info(self):
                    class FakeMemInfo:
                        rss = 0
                    return FakeMemInfo()
            return FakeProcess()
        @staticmethod
        def net_io_counters():
            class FakeNetIO:
                bytes_sent = 0
                bytes_recv = 0
            return FakeNetIO()
        @staticmethod
        def disk_io_counters():
            class FakeDiskIO:
                read_bytes = 0
                write_bytes = 0
            return FakeDiskIO()
        @staticmethod
        def cpu_count(logical=True):
            return 4
        @staticmethod
        def cpu_freq():
            class FakeCpuFreq:
                current = 0.0
            return FakeCpuFreq()
    psutil = FakePsutil()

# Importation conditionnelle des dépendances optionnelles
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    np = None

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False
    pd = None

try:
    from matplotlib import pyplot as plt
    HAS_MPL = True
except ImportError:
    HAS_MPL = False
    plt = None

from gbpbot.config.config_manager import config_manager
from gbpbot.utils.distributed_cache import get_distributed_cache

# Configuration du logger
logger = logging.getLogger("gbpbot.core.performance_monitor")

# Type pour le singleton
T = TypeVar('T', bound='PerformanceMonitor')

class MetricError(Exception):
    """Exception de base pour les erreurs liées aux métriques"""
    pass

class PerformanceMetric:
    """
    Classe représentant une métrique de performance avec son historique
    """
    
    def __init__(self, name: str, max_history: int = 1000, alert_threshold: Optional[float] = None):
        """
        Initialise une métrique de performance
        
        Args:
            name: Nom de la métrique
            max_history: Nombre maximum de valeurs historiques à conserver
            alert_threshold: Seuil pour déclencher une alerte (None = pas d'alerte)
        """
        self.name = name
        self.values = deque(maxlen=max_history)
        self.timestamps = deque(maxlen=max_history)
        self.alert_threshold = alert_threshold
        self.alert_triggered = False
        self.created_at = datetime.now()
        self.last_updated = None
        self.total_samples = 0
        
    def add_value(self, value: float) -> bool:
        """
        Ajoute une valeur à l'historique de la métrique
        
        Args:
            value: Valeur à ajouter
            
        Returns:
            bool: True si une alerte a été déclenchée, False sinon
        """
        self.values.append(value)
        self.timestamps.append(time.time())
        self.last_updated = datetime.now()
        self.total_samples += 1
        
        # Vérifier si la valeur dépasse le seuil d'alerte
        if self.alert_threshold is not None:
            if value > self.alert_threshold:
                self.alert_triggered = True
                return True
            else:
                self.alert_triggered = False
        
        return False
    
    def get_average(self, window: Optional[int] = None) -> float:
        """
        Calcule la moyenne des valeurs sur une fenêtre donnée
        
        Args:
            window: Taille de la fenêtre (None = toutes les valeurs)
            
        Returns:
            float: Moyenne des valeurs
        """
        if not self.values:
            return 0.0
        
        if window and window < len(self.values):
            values = list(self.values)[-window:]
        else:
            values = self.values
        
        return sum(values) / len(values)
    
    def get_max(self, window: Optional[int] = None) -> float:
        """
        Récupère la valeur maximale sur une fenêtre donnée
        
        Args:
            window: Taille de la fenêtre (None = toutes les valeurs)
            
        Returns:
            float: Valeur maximale
        """
        if not self.values:
            return 0.0
        
        if window and window < len(self.values):
            values = list(self.values)[-window:]
        else:
            values = self.values
        
        return max(values)
    
    def get_min(self, window: Optional[int] = None) -> float:
        """
        Récupère la valeur minimale sur une fenêtre donnée
        
        Args:
            window: Taille de la fenêtre (None = toutes les valeurs)
            
        Returns:
            float: Valeur minimale
        """
        if not self.values:
            return 0.0
        
        if window and window < len(self.values):
            values = list(self.values)[-window:]
        else:
            values = self.values
        
        return min(values)
    
    def get_percentile(self, percentile: float, window: Optional[int] = None) -> float:
        """
        Calcule un percentile donné des valeurs sur une fenêtre donnée
        
        Args:
            percentile: Percentile à calculer (0-100)
            window: Taille de la fenêtre (None = toutes les valeurs)
            
        Returns:
            float: Valeur du percentile
        """
        if not self.values or not HAS_NUMPY or np is None:
            return 0.0
        
        if window and window < len(self.values):
            values = list(self.values)[-window:]
        else:
            values = self.values
        
        return float(np.percentile(values, percentile))
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convertit la métrique en dictionnaire
        
        Returns:
            Dict[str, Any]: Dictionnaire représentant la métrique
        """
        return {
            "name": self.name,
            "values": list(self.values) if self.values else [],
            "timestamps": list(self.timestamps) if self.timestamps else [],
            "average": self.get_average(),
            "max": self.get_max(),
            "min": self.get_min(),
            "total_samples": self.total_samples,
            "alert_threshold": self.alert_threshold,
            "alert_triggered": self.alert_triggered,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None
        }

class PerformanceMonitor:
    """
    Classe principale pour le monitoring des performances du GBPBot
    """
    
    _instance = None
    
    def __new__(cls: type[T]) -> T:
        """Implémentation du pattern Singleton"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """
        Initialise le moniteur de performances
        """
        if not hasattr(self, 'initialized'):
            # Vérifier que psutil est disponible
            if not HAS_PSUTIL:
                logger.warning("Module psutil non disponible. Fonctionnalités de monitoring limitées.")
            
            # Configuration
            self.config = config_manager.get_config("performance_monitor", {})
            
            # Regrouper les seuils d'alerte
            self.alert_thresholds = {
                "cpu": self.config.get("cpu_alert_threshold", 90.0),
                "memory": self.config.get("memory_alert_threshold", 90.0),
                "disk": self.config.get("disk_alert_threshold", 90.0),
                "tx_latency": self.config.get("tx_latency_alert_threshold", 10.0),
                "rpc_time": self.config.get("rpc_time_alert_threshold", 5.0)
            }
            
            # Métriques système
            self.metrics: Dict[str, PerformanceMetric] = {
                # Métriques CPU
                "cpu_usage": PerformanceMetric("cpu_usage", alert_threshold=self.alert_thresholds["cpu"]),
                "cpu_frequency": PerformanceMetric("cpu_frequency"),
                "process_cpu": PerformanceMetric("process_cpu"),
                
                # Métriques mémoire
                "memory_usage": PerformanceMetric("memory_usage", alert_threshold=self.alert_thresholds["memory"]),
                "memory_available": PerformanceMetric("memory_available"),
                "process_memory": PerformanceMetric("process_memory"),
                
                # Métriques disque
                "disk_usage": PerformanceMetric("disk_usage", alert_threshold=self.alert_thresholds["disk"]),
                "disk_io_read": PerformanceMetric("disk_io_read"),
                "disk_io_write": PerformanceMetric("disk_io_write"),
                
                # Métriques réseau
                "network_sent": PerformanceMetric("network_sent"),
                "network_received": PerformanceMetric("network_received"),
                
                # Métriques GBPBot
                "transaction_latency": PerformanceMetric("transaction_latency", 
                                                         alert_threshold=self.alert_thresholds["tx_latency"]),
                "transaction_success_rate": PerformanceMetric("transaction_success_rate"),
                "rpc_response_time": PerformanceMetric("rpc_response_time", 
                                                      alert_threshold=self.alert_thresholds["rpc_time"]),
                "cache_hit_rate": PerformanceMetric("cache_hit_rate"),
                "arbitrage_detection_time": PerformanceMetric("arbitrage_detection_time"),
                "model_inference_time": PerformanceMetric("model_inference_time"),
                "token_analysis_time": PerformanceMetric("token_analysis_time")
            }
            
            # Ajouter des métriques personnalisées si définies dans la configuration
            custom_metrics = self.config.get("custom_metrics", {})
            for name, config in custom_metrics.items():
                self.metrics[name] = PerformanceMetric(
                    name=name,
                    max_history=config.get("max_history", 1000),
                    alert_threshold=config.get("alert_threshold")
                )
            
            # Alertes
            self.alert_callbacks: List[Callable[[str, float, float], None]] = []
            self.alert_history: List[Dict[str, Any]] = []
            self.alert_cooldown = {}  # Pour éviter trop d'alertes répétées
            self.alert_cooldown_period = self.config.get("alert_cooldown_period", 300)  # 5 minutes par défaut
            
            # État du monitoring
            self.running = False
            self.monitoring_thread = None
            self.monitoring_interval = self.config.get("monitoring_interval", 5.0)  # secondes
            self.log_interval = self.config.get("log_interval", 60.0)  # secondes
            self.last_log_time = 0
            
            # Données système
            self.process = psutil.Process()
            
            # Données de réseau précédentes pour calculer le delta
            self.last_network_io = psutil.net_io_counters()
            self.last_network_time = time.time()
            
            # Données de disque précédentes pour calculer le delta
            self.last_disk_io = psutil.disk_io_counters()
            self.last_disk_time = time.time()
            
            # Intégration avec le cache distribué
            self.distributed_cache = get_distributed_cache()
            
            # Marquer comme initialisé
            self.initialized = True
            logger.info("PerformanceMonitor initialisé")
    
    def start_monitoring(self) -> bool:
        """
        Démarre le monitoring des performances en arrière-plan
        
        Returns:
            bool: True si le monitoring a été démarré, False sinon
        """
        if self.running:
            logger.warning("Le monitoring est déjà en cours d'exécution")
            return False
        
        self.running = True
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True,
            name="PerformanceMonitoringThread"
        )
        self.monitoring_thread.start()
        logger.info("Monitoring des performances démarré (intervalle: %s secondes)", self.monitoring_interval)
        return True
    
    def stop_monitoring(self) -> bool:
        """
        Arrête le monitoring des performances
        
        Returns:
            bool: True si le monitoring a été arrêté, False sinon
        """
        if not self.running:
            logger.warning("Le monitoring n'est pas en cours d'exécution")
            return False
        
        self.running = False
        
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5.0)
            self.monitoring_thread = None
        
        logger.info("Monitoring des performances arrêté")
        return True
    
    def register_alert_callback(self, callback: Callable[[str, float, float], None]) -> None:
        """
        Enregistre une fonction de rappel pour les alertes
        
        Args:
            callback: Fonction à appeler lorsqu'une alerte est déclenchée.
                     Les arguments sont (nom_métrique, valeur, seuil)
        """
        self.alert_callbacks.append(callback)
    
    def _monitoring_loop(self) -> None:
        """
        Boucle principale de monitoring exécutée en arrière-plan
        """
        logger.debug("Démarrage de la boucle de monitoring")
        
        while self.running:
            try:
                # Collecter les métriques système
                self._collect_system_metrics()
                
                # Collecter les métriques de l'application depuis le cache distribué
                self._collect_app_metrics()
                
                # Enregistrer les métriques dans le log à intervalle régulier
                current_time = time.time()
                if current_time - self.last_log_time >= self.log_interval:
                    self._log_metrics()
                    self.last_log_time = current_time
                
                # Attendre avant la prochaine collecte
                time.sleep(self.monitoring_interval)
                
            except KeyboardInterrupt:
                logger.info("Monitoring interrompu par l'utilisateur")
                break
            except (IOError, OSError) as e:
                logger.error("Erreur d'E/S dans la boucle de monitoring: %s", e)
                time.sleep(self.monitoring_interval * 2)
            except Exception as e:
                logger.error("Erreur dans la boucle de monitoring: %s", e)
                # Continuer malgré l'erreur, mais attendre un peu
                time.sleep(self.monitoring_interval * 2)
    
    def _collect_system_metrics(self) -> None:
        """
        Collecte les métriques système (CPU, mémoire, disque, réseau)
        """
        try:
            # CPU
            cpu_percent = psutil.cpu_percent(interval=None)
            self.metrics["cpu_usage"].add_value(cpu_percent)
            
            cpu_freq = psutil.cpu_freq()
            if cpu_freq:
                self.metrics["cpu_frequency"].add_value(cpu_freq.current)
            
            process_cpu = self.process.cpu_percent(interval=None) / psutil.cpu_count()
            self.metrics["process_cpu"].add_value(process_cpu)
            
            # Mémoire
            memory = psutil.virtual_memory()
            self.metrics["memory_usage"].add_value(memory.percent)
            self.metrics["memory_available"].add_value(memory.available / (1024 * 1024))  # MB
            
            process_memory = self.process.memory_info().rss / (1024 * 1024)  # MB
            self.metrics["process_memory"].add_value(process_memory)
            
            # Disque
            disk = psutil.disk_usage('/')
            self.metrics["disk_usage"].add_value(disk.percent)
            
            # Disque I/O
            self._collect_disk_io_metrics()
            
            # Réseau
            self._collect_network_metrics()
        
        except (AttributeError, OSError) as e:
            logger.error("Erreur lors de la collecte des métriques système: %s", e)
    
    def _collect_disk_io_metrics(self) -> None:
        """Collecte les métriques d'I/O disque"""
        try:
            current_disk_io = psutil.disk_io_counters()
            current_disk_time = time.time()
            
            if current_disk_io is None:
                logger.debug("Les compteurs d'I/O disque ne sont pas disponibles sur ce système")
                return
                
            disk_time_delta = current_disk_time - self.last_disk_time
            
            if disk_time_delta > 0 and self.last_disk_io:
                read_bytes_delta = current_disk_io.read_bytes - self.last_disk_io.read_bytes
                write_bytes_delta = current_disk_io.write_bytes - self.last_disk_io.write_bytes
                
                read_speed = read_bytes_delta / disk_time_delta / (1024 * 1024)  # MB/s
                write_speed = write_bytes_delta / disk_time_delta / (1024 * 1024)  # MB/s
                
                self.metrics["disk_io_read"].add_value(read_speed)
                self.metrics["disk_io_write"].add_value(write_speed)
            
            self.last_disk_io = current_disk_io
            self.last_disk_time = current_disk_time
        except (AttributeError, OSError) as e:
            logger.debug("Erreur lors de la collecte des métriques d'I/O disque: %s", e)
    
    def _collect_network_metrics(self) -> None:
        """Collecte les métriques réseau"""
        try:
            current_network_io = psutil.net_io_counters()
            current_network_time = time.time()
            
            if current_network_io is None:
                logger.debug("Les compteurs réseau ne sont pas disponibles sur ce système")
                return
                
            network_time_delta = current_network_time - self.last_network_time
            
            if network_time_delta > 0 and self.last_network_io:
                sent_bytes_delta = current_network_io.bytes_sent - self.last_network_io.bytes_sent
                recv_bytes_delta = current_network_io.bytes_recv - self.last_network_io.bytes_recv
                
                sent_speed = sent_bytes_delta / network_time_delta / 1024  # KB/s
                recv_speed = recv_bytes_delta / network_time_delta / 1024  # KB/s
                
                self.metrics["network_sent"].add_value(sent_speed)
                self.metrics["network_received"].add_value(recv_speed)
            
            self.last_network_io = current_network_io
            self.last_network_time = current_network_time
        except (AttributeError, OSError) as e:
            logger.debug("Erreur lors de la collecte des métriques réseau: %s", e)
    
    def _collect_app_metrics(self) -> None:
        """
        Collecte les métriques spécifiques à l'application depuis le cache distribué
        """
        try:
            # Récupérer les métriques disponibles dans le cache distribué
            app_metrics = self.distributed_cache.get("app_metrics", {})
            
            # Mettre à jour les métriques locales
            for name, value in app_metrics.items():
                if name in self.metrics:
                    # Déclencher une alerte si nécessaire
                    alert_triggered = self.metrics[name].add_value(value)
                    
                    if alert_triggered and self.metrics[name].alert_threshold is not None:
                        threshold = cast(float, self.metrics[name].alert_threshold)
                        self._trigger_alert(name, value, threshold)
            
            # Récupérer les statistiques du cache
            self._update_cache_metrics()
        
        except (KeyError, TypeError) as e:
            logger.error("Erreur lors de la collecte des métriques de l'application: %s", e)
    
    def _update_cache_metrics(self) -> None:
        """Met à jour les métriques du cache"""
        try:
            cache_stats = self.distributed_cache.get_stats()
            if "hits" in cache_stats and "misses" in cache_stats:
                total_requests = cache_stats["hits"] + cache_stats["misses"]
                if total_requests > 0:
                    hit_rate = (cache_stats["hits"] / total_requests) * 100
                    self.metrics["cache_hit_rate"].add_value(hit_rate)
        except Exception as e:
            logger.debug("Erreur lors de la mise à jour des métriques de cache: %s", e)
    
    def _log_metrics(self) -> None:
        """
        Enregistre les principales métriques dans le log
        """
        try:
            log_metrics = {
                "cpu_usage": self.metrics["cpu_usage"].get_average(10),
                "memory_usage": self.metrics["memory_usage"].get_average(10),
                "process_memory_mb": self.metrics["process_memory"].get_average(10),
                "disk_usage": self.metrics["disk_usage"].get_average(10),
                "network_recv_kbps": self.metrics["network_received"].get_average(10),
                "network_sent_kbps": self.metrics["network_sent"].get_average(10),
            }
            
            # Ajouter les métriques spécifiques au trading si disponibles
            self._add_trading_metrics_to_log(log_metrics)
            
            # Enregistrer dans le log
            logger.info("Métriques de performance: %s", json.dumps(log_metrics))
            
        except Exception as e:
            logger.error("Erreur lors de l'enregistrement des métriques: %s", e)
    
    def _add_trading_metrics_to_log(self, log_metrics: Dict[str, float]) -> None:
        """Ajoute les métriques de trading au log si disponibles"""
        if self.metrics["transaction_latency"].total_samples > 0:
            log_metrics["tx_latency_avg"] = self.metrics["transaction_latency"].get_average(10)
            log_metrics["tx_latency_max"] = self.metrics["transaction_latency"].get_max(10)
        
        if self.metrics["transaction_success_rate"].total_samples > 0:
            log_metrics["tx_success_rate"] = self.metrics["transaction_success_rate"].get_average(10)
        
        if self.metrics["cache_hit_rate"].total_samples > 0:
            log_metrics["cache_hit_rate"] = self.metrics["cache_hit_rate"].get_average(10)
    
    def _trigger_alert(self, metric_name: str, value: float, threshold: float) -> None:
        """
        Déclenche une alerte pour une métrique donnée
        
        Args:
            metric_name: Nom de la métrique
            value: Valeur actuelle
            threshold: Seuil d'alerte
        """
        # Vérifier le cooldown pour éviter les alertes répétitives
        current_time = time.time()
        last_alert_time = self.alert_cooldown.get(metric_name, 0)
        
        if current_time - last_alert_time < self.alert_cooldown_period:
            # Encore en période de cooldown
            return
            
        # Mettre à jour le temps de dernière alerte
        self.alert_cooldown[metric_name] = current_time
        
        alert = {
            "metric": metric_name,
            "value": value,
            "threshold": threshold,
            "timestamp": datetime.now().isoformat()
        }
        
        # Ajouter à l'historique des alertes
        self.alert_history.append(alert)
        
        # Limiter la taille de l'historique
        if len(self.alert_history) > 100:
            self.alert_history = self.alert_history[-100:]
        
        # Enregistrer dans le log
        logger.warning("ALERTE - %s: %.2f (seuil: %.2f)", metric_name, value, threshold)
        
        # Notifier les callbacks
        for callback in self.alert_callbacks:
            try:
                callback(metric_name, value, threshold)
            except Exception as e:
                logger.error("Erreur dans le callback d'alerte: %s", e)
    
    def track_metric(self, name: str, value: float) -> None:
        """
        Enregistre une métrique spécifique à l'application
        
        Args:
            name: Nom de la métrique
            value: Valeur à enregistrer
        """
        if not isinstance(value, (int, float)):
            logger.warning("Valeur de métrique invalide pour %s: %s", name, value)
            return
            
        # Mettre à jour la métrique locale si elle existe
        if name in self.metrics:
            # Déclencher une alerte si nécessaire
            alert_triggered = self.metrics[name].add_value(value)
            
            if alert_triggered and self.metrics[name].alert_threshold is not None:
                threshold = cast(float, self.metrics[name].alert_threshold)
                self._trigger_alert(name, value, threshold)
        
        # Stocker dans le cache distribué pour qu'elle soit disponible pour les autres instances
        try:
            app_metrics = self.distributed_cache.get("app_metrics", {})
            app_metrics[name] = value
            self.distributed_cache.set("app_metrics", app_metrics, ttl=300)  # 5 minutes
        except Exception as e:
            logger.debug("Erreur lors du stockage de la métrique dans le cache distribué: %s", e)
    
    def get_metrics_report(self) -> Dict[str, Any]:
        """
        Génère un rapport complet des métriques de performance
        
        Returns:
            Dict[str, Any]: Rapport de métriques
        """
        report = {
            "timestamp": datetime.now().isoformat(),
            "system_info": {
                "platform": platform.platform(),
                "processor": platform.processor(),
                "python_version": platform.python_version(),
                "cpu_count": psutil.cpu_count(),
                "physical_cpu_count": psutil.cpu_count(logical=False)
            },
            "metrics": {},
            "alerts": self.alert_history[-10:] if self.alert_history else []
        }
        
        # Ajouter les statistiques pour chaque métrique
        for name, metric in self.metrics.items():
            if metric.total_samples > 0:
                report["metrics"][name] = {
                    "current": metric.values[-1] if metric.values else None,
                    "average": metric.get_average(),
                    "max": metric.get_max(),
                    "min": metric.get_min(),
                    "samples": metric.total_samples,
                    "last_updated": metric.last_updated.isoformat() if metric.last_updated else None
                }
                
                # Ajouter les percentiles si numpy est disponible
                if HAS_NUMPY and np is not None and metric.values:
                    report["metrics"][name]["percentiles"] = {
                        "50": metric.get_percentile(50),
                        "90": metric.get_percentile(90),
                        "95": metric.get_percentile(95),
                        "99": metric.get_percentile(99)
                    }
        
        return report
    
    def export_metrics_to_csv(self, output_dir: str) -> Optional[str]:
        """
        Exporte les métriques vers des fichiers CSV
        
        Args:
            output_dir: Répertoire de sortie pour les fichiers CSV
            
        Returns:
            Optional[str]: Chemin du répertoire de sortie ou None en cas d'erreur
        """
        if not HAS_PANDAS or pd is None:
            logger.error("L'exportation vers CSV nécessite pandas")
            return None
        
        try:
            # Créer le répertoire de sortie s'il n'existe pas
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Date et heure pour le nom du fichier
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Exporter chaque métrique dans un fichier séparé
            exported_files = []
            for name, metric in self.metrics.items():
                if not metric.values or not metric.timestamps:
                    continue  # Ignorer les métriques vides
                
                # Créer un DataFrame pour la métrique
                df = pd.DataFrame({
                    "timestamp": [datetime.fromtimestamp(ts) for ts in metric.timestamps],
                    "value": metric.values
                })
                
                # Trier par timestamp
                df = df.sort_values("timestamp")
                
                # Définir le chemin du fichier
                file_path = output_path / f"{name}_{timestamp}.csv"
                
                # Exporter vers CSV
                df.to_csv(str(file_path), index=False)
                exported_files.append(str(file_path))
            
            logger.info("Métriques exportées vers %s (%d fichiers)", output_dir, len(exported_files))
            return output_dir
        
        except (IOError, OSError) as e:
            logger.error("Erreur lors de l'exportation des métriques vers CSV: %s", e)
            return None
    
    def generate_performance_plots(self, output_dir: str) -> Optional[List[str]]:
        """
        Génère des graphiques de performance pour les métriques principales
        
        Args:
            output_dir: Répertoire de sortie pour les graphiques
            
        Returns:
            Optional[List[str]]: Liste des chemins des graphiques générés ou None en cas d'erreur
        """
        if not HAS_MPL or not HAS_PANDAS or plt is None or pd is None:
            logger.error("La génération de graphiques nécessite matplotlib et pandas")
            return None
        
        try:
            # Créer le répertoire de sortie s'il n'existe pas
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Date et heure pour le nom du fichier
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Liste des métriques à tracer
            plot_metrics = [
                "cpu_usage", "memory_usage", "disk_usage",
                "network_sent", "network_received",
                "transaction_latency", "transaction_success_rate",
                "cache_hit_rate"
            ]
            
            # Générer les graphiques
            generated_files = []
            for name in plot_metrics:
                if name not in self.metrics or not self.metrics[name].values or not self.metrics[name].timestamps:
                    continue  # Ignorer les métriques vides
                
                # Créer un graph pour cette métrique
                file_path = self._generate_metric_plot(name, timestamp, output_path)
                if file_path:
                    generated_files.append(file_path)
            
            logger.info("Graphiques générés dans %s (%d fichiers)", output_dir, len(generated_files))
            return generated_files
        
        except (IOError, OSError) as e:
            logger.error("Erreur lors de la génération des graphiques: %s", e)
            return None
    
    def _generate_metric_plot(self, metric_name: str, timestamp: str, output_path: Path) -> Optional[str]:
        """Génère un graphique pour une métrique spécifique"""
        if plt is None or pd is None:
            return None
            
        try:
            metric = self.metrics[metric_name]
            
            # Créer un DataFrame pour la métrique
            df = pd.DataFrame({
                "timestamp": [datetime.fromtimestamp(ts) for ts in metric.timestamps],
                "value": metric.values
            })
            
            # Trier par timestamp
            df = df.sort_values("timestamp")
            
            # Créer le graphique
            plt.figure(figsize=(10, 6))
            plt.plot(df["timestamp"], df["value"])
            plt.title(f"{metric_name} - {timestamp}")
            plt.xlabel("Timestamp")
            plt.ylabel("Value")
            plt.grid(True)
            
            # Ajouter le seuil d'alerte si défini
            if metric.alert_threshold is not None:
                plt.axhline(y=metric.alert_threshold, color='r', linestyle='--',
                           label=f"Alert threshold ({metric.alert_threshold})")
                plt.legend()
            
            # Définir le chemin du fichier
            file_path = output_path / f"{metric_name}_{timestamp}.png"
            
            # Sauvegarder le graphique
            plt.savefig(str(file_path))
            plt.close()
            
            return str(file_path)
        except Exception as e:
            logger.debug("Erreur lors de la génération du graphique pour %s: %s", metric_name, e)
            return None

# Instance singleton du PerformanceMonitor
performance_monitor = PerformanceMonitor()

def get_performance_monitor() -> PerformanceMonitor:
    """
    Récupère l'instance singleton du PerformanceMonitor
    
    Returns:
        PerformanceMonitor: Instance du moniteur de performance
    """
    return performance_monitor

def track_execution_time(metric_name: str):
    """
    Décorateur pour suivre le temps d'exécution d'une fonction
    
    Args:
        metric_name: Nom de la métrique pour stocker le temps d'exécution
    
    Returns:
        Callable: Décorateur
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            # Enregistrer le temps d'exécution
            performance_monitor.track_metric(metric_name, execution_time)
            
            return result
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            # Enregistrer le temps d'exécution
            performance_monitor.track_metric(metric_name, execution_time)
            
            return result
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return wrapper
    
    return decorator 