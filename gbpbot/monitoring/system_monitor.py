"""
Moniteur de Ressources Système pour GBPBot
==========================================

Ce module fournit des fonctionnalités pour surveiller les ressources système
utilisées par le GBPBot, incluant l'utilisation du CPU, de la mémoire, 
du disque et du réseau.

Il permet d'optimiser les performances et d'identifier les goulots d'étranglement.
"""

import os
import sys
import platform
import logging
import threading
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Union, Callable
from pathlib import Path

# Configuration du logger
logger = logging.getLogger("gbpbot.monitoring.system")

# Gestion de l'import de psutil
try:
    import psutil
    has_psutil = True
except ImportError:
    has_psutil = False
    logger.warning("Module psutil non disponible. Certaines fonctionnalités de monitoring seront limitées.")

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
                total = 0
            return FakeMemory()
        
        @staticmethod
        def disk_usage(path):
            class FakeDisk:
                percent = 0.0
                total = 0
                used = 0
                free = 0
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
                
                def io_counters(self):
                    class FakeIO:
                        read_bytes = 0
                        write_bytes = 0
                    return FakeIO()
                
                def memory_percent(self):
                    return 0.0
                
                def threads(self):
                    return []
                
                def connections(self):
                    return []
                
                def create_time(self):
                    return time.time()
                
                def status(self):
                    return "running"
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
            return 1
        
        @staticmethod
        def cpu_freq():
            class FakeCpuFreq:
                current = 0.0
            return FakeCpuFreq()
        
        @staticmethod
        def boot_time():
            return time.time()
        
        # Classe d'exception pour simuler psutil.AccessDenied
        class AccessDenied(Exception):
            pass

    # Utiliser la classe factice si psutil n'est pas disponible
    psutil = FakePsutil()


class SystemMonitor:
    """
    Classe pour surveiller les ressources système utilisées par le GBPBot.
    
    Cette classe fournit des méthodes pour collecter et analyser les métriques
    système comme l'utilisation du CPU, de la mémoire, du disque et du réseau.
    """
    
    _instance = None
    
    def __new__(cls):
        """Implémentation du pattern Singleton"""
        if cls._instance is None:
            cls._instance = super(SystemMonitor, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialise le moniteur système"""
        # Éviter la réinitialisation du singleton
        if getattr(self, "_initialized", False):
            return
            
        self._initialized = True
        
        # Données système
        self.metrics = {
            "cpu": {
                "percent": 0.0,
                "count": psutil.cpu_count(logical=True),
                "frequency": getattr(psutil.cpu_freq(), "current", 0) if hasattr(psutil, "cpu_freq") else 0
            },
            "memory": {
                "percent": 0.0,
                "available": 0,
                "total": 0,
                "used": 0
            },
            "disk": {
                "percent": 0.0,
                "total": 0,
                "used": 0,
                "free": 0
            },
            "network": {
                "bytes_sent": 0,
                "bytes_recv": 0,
                "bytes_sent_sec": 0,
                "bytes_recv_sec": 0
            },
            "process": {
                "cpu_percent": 0.0,
                "memory_percent": 0.0,
                "memory_rss": 0,
                "io_read_bytes": 0,
                "io_write_bytes": 0,
                "thread_count": 0,
                "connection_count": 0,
                "uptime": 0
            },
            "system": {
                "boot_time": psutil.boot_time(),
                "platform": platform.system(),
                "platform_release": platform.release(),
                "python_version": platform.python_version(),
                "hostname": platform.node()
            }
        }
        
        # Données pour le calcul des taux
        self._last_check_time = time.time()
        self._last_net_io = psutil.net_io_counters() if has_psutil else None
        self._last_disk_io = psutil.disk_io_counters() if has_psutil else None
        
        # Informations sur le processus actuel
        self.process = psutil.Process(os.getpid()) if has_psutil else None
        
        # Verrou pour l'accès concurrent
        self._lock = threading.RLock()
        
        # Monitoring en arrière-plan
        self._monitoring_thread = None
        self._monitoring_active = False
        self._check_interval = 5.0  # secondes
        
        # Callbacks pour les alertes
        self._alert_callbacks = []
        self._thresholds = {
            "cpu_percent": 90.0,
            "memory_percent": 90.0,
            "disk_percent": 90.0,
            "process_cpu_percent": 90.0,
            "process_memory_percent": 90.0
        }
        
        # Chemin pour les rapports
        self.reports_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "system")
        os.makedirs(self.reports_dir, exist_ok=True)
    
    def start_monitoring(self, interval: float = 5.0) -> bool:
        """
        Démarre le monitoring système en arrière-plan.
        
        Args:
            interval: Intervalle de vérification en secondes
            
        Returns:
            bool: True si le démarrage a réussi, False sinon
        """
        if self._monitoring_active:
            logger.warning("Le monitoring système est déjà actif")
            return False
        
        self._check_interval = interval
        self._monitoring_active = True
        self._monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self._monitoring_thread.start()
        
        logger.info(f"Monitoring système démarré avec un intervalle de {interval} secondes")
        return True
    
    def stop_monitoring(self) -> bool:
        """
        Arrête le monitoring système en arrière-plan.
        
        Returns:
            bool: True si l'arrêt a réussi, False sinon
        """
        if not self._monitoring_active:
            logger.warning("Le monitoring système n'est pas actif")
            return False
        
        self._monitoring_active = False
        if self._monitoring_thread:
            self._monitoring_thread.join(timeout=2.0)
            self._monitoring_thread = None
        
        logger.info("Monitoring système arrêté")
        return True
    
    def _monitoring_loop(self) -> None:
        """Boucle principale du thread de monitoring"""
        while self._monitoring_active:
            try:
                self.collect_metrics()
                self._check_thresholds()
                time.sleep(self._check_interval)
            except Exception as e:
                logger.error(f"Erreur dans la boucle de monitoring système: {str(e)}")
                time.sleep(1.0)  # Délai court en cas d'erreur
    
    def collect_metrics(self) -> None:
        """Collecte toutes les métriques système"""
        try:
            current_time = time.time()
            time_diff = current_time - self._last_check_time
            
            with self._lock:
                # CPU
                self.metrics["cpu"]["percent"] = psutil.cpu_percent(interval=0.1)
                if hasattr(psutil, "cpu_freq") and psutil.cpu_freq():
                    self.metrics["cpu"]["frequency"] = psutil.cpu_freq().current
                
                # Mémoire
                memory = psutil.virtual_memory()
                self.metrics["memory"]["percent"] = memory.percent
                self.metrics["memory"]["available"] = memory.available
                self.metrics["memory"]["total"] = memory.total
                self.metrics["memory"]["used"] = memory.total - memory.available
                
                # Disque
                disk = psutil.disk_usage(os.path.abspath(os.sep))
                self.metrics["disk"]["percent"] = disk.percent
                self.metrics["disk"]["total"] = disk.total
                self.metrics["disk"]["used"] = disk.used
                self.metrics["disk"]["free"] = disk.free
                
                # Réseau
                if has_psutil:
                    current_net_io = psutil.net_io_counters()
                    if self._last_net_io and time_diff > 0:
                        self.metrics["network"]["bytes_sent"] = current_net_io.bytes_sent
                        self.metrics["network"]["bytes_recv"] = current_net_io.bytes_recv
                        self.metrics["network"]["bytes_sent_sec"] = (current_net_io.bytes_sent - self._last_net_io.bytes_sent) / time_diff
                        self.metrics["network"]["bytes_recv_sec"] = (current_net_io.bytes_recv - self._last_net_io.bytes_recv) / time_diff
                    self._last_net_io = current_net_io
                
                # Processus
                if self.process:
                    self.metrics["process"]["cpu_percent"] = self.process.cpu_percent(interval=0.1)
                    self.metrics["process"]["memory_percent"] = self.process.memory_percent()
                    self.metrics["process"]["memory_rss"] = self.process.memory_info().rss
                    self.metrics["process"]["thread_count"] = len(self.process.threads())
                    
                    # IO
                    if hasattr(self.process, "io_counters") and self.process.io_counters():
                        self.metrics["process"]["io_read_bytes"] = self.process.io_counters().read_bytes
                        self.metrics["process"]["io_write_bytes"] = self.process.io_counters().write_bytes
                    
                    # Connexions
                    try:
                        self.metrics["process"]["connection_count"] = len(self.process.connections())
                    except psutil.AccessDenied:
                        self.metrics["process"]["connection_count"] = 0
                    
                    # Uptime
                    self.metrics["process"]["uptime"] = current_time - self.process.create_time()
                
                # Mettre à jour le temps de vérification
                self._last_check_time = current_time
                
        except Exception as e:
            logger.error(f"Erreur lors de la collecte des métriques système: {str(e)}")
    
    def _check_thresholds(self) -> None:
        """Vérifie si les métriques dépassent les seuils définis et déclenche des alertes si nécessaire"""
        with self._lock:
            # Vérifier CPU
            if self.metrics["cpu"]["percent"] > self._thresholds["cpu_percent"]:
                self._trigger_alert("cpu_percent", self.metrics["cpu"]["percent"], self._thresholds["cpu_percent"])
            
            # Vérifier Mémoire
            if self.metrics["memory"]["percent"] > self._thresholds["memory_percent"]:
                self._trigger_alert("memory_percent", self.metrics["memory"]["percent"], self._thresholds["memory_percent"])
            
            # Vérifier Disque
            if self.metrics["disk"]["percent"] > self._thresholds["disk_percent"]:
                self._trigger_alert("disk_percent", self.metrics["disk"]["percent"], self._thresholds["disk_percent"])
            
            # Vérifier CPU Processus
            if self.metrics["process"]["cpu_percent"] > self._thresholds["process_cpu_percent"]:
                self._trigger_alert("process_cpu_percent", self.metrics["process"]["cpu_percent"], self._thresholds["process_cpu_percent"])
            
            # Vérifier Mémoire Processus
            if self.metrics["process"]["memory_percent"] > self._thresholds["process_memory_percent"]:
                self._trigger_alert("process_memory_percent", self.metrics["process"]["memory_percent"], self._thresholds["process_memory_percent"])
    
    def _trigger_alert(self, metric_name: str, value: float, threshold: float) -> None:
        """
        Déclenche une alerte pour une métrique qui dépasse son seuil.
        
        Args:
            metric_name: Nom de la métrique
            value: Valeur actuelle
            threshold: Seuil défini
        """
        message = f"Alerte système: {metric_name} ({value:.2f}) dépasse le seuil ({threshold:.2f})"
        logger.warning(message)
        
        # Appeler les callbacks d'alerte
        for callback in self._alert_callbacks:
            try:
                callback(metric_name, value, threshold)
            except Exception as e:
                logger.error(f"Erreur dans le callback d'alerte: {str(e)}")
    
    def register_alert_callback(self, callback: Callable[[str, float, float], None]) -> None:
        """
        Enregistre un callback à appeler lorsqu'une alerte est déclenchée.
        
        Args:
            callback: Fonction à appeler avec (metric_name, value, threshold)
        """
        self._alert_callbacks.append(callback)
    
    def unregister_alert_callback(self, callback: Callable[[str, float, float], None]) -> bool:
        """
        Supprime un callback d'alerte.
        
        Args:
            callback: Callback à supprimer
            
        Returns:
            bool: True si le callback a été supprimé, False sinon
        """
        if callback in self._alert_callbacks:
            self._alert_callbacks.remove(callback)
            return True
        return False
    
    def set_threshold(self, metric_name: str, threshold: float) -> bool:
        """
        Définit un seuil pour une métrique.
        
        Args:
            metric_name: Nom de la métrique
            threshold: Seuil à définir
            
        Returns:
            bool: True si le seuil a été défini, False sinon
        """
        if metric_name in self._thresholds:
            self._thresholds[metric_name] = threshold
            return True
        return False
    
    def set_all_thresholds(self, cpu_percent: Optional[float] = None, memory_percent: Optional[float] = None,
                          disk_percent: Optional[float] = None, process_cpu_percent: Optional[float] = None, 
                          process_memory_percent: Optional[float] = None) -> None:
        """
        Définit les seuils pour plusieurs métriques à la fois.
        
        Args:
            cpu_percent: Seuil pour l'utilisation du CPU
            memory_percent: Seuil pour l'utilisation de la mémoire
            disk_percent: Seuil pour l'utilisation du disque
            process_cpu_percent: Seuil pour l'utilisation du CPU par le processus
            process_memory_percent: Seuil pour l'utilisation de la mémoire par le processus
        """
        if cpu_percent is not None:
            self._thresholds["cpu_percent"] = cpu_percent
        if memory_percent is not None:
            self._thresholds["memory_percent"] = memory_percent
        if disk_percent is not None:
            self._thresholds["disk_percent"] = disk_percent
        if process_cpu_percent is not None:
            self._thresholds["process_cpu_percent"] = process_cpu_percent
        if process_memory_percent is not None:
            self._thresholds["process_memory_percent"] = process_memory_percent
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Récupère toutes les métriques système actuelles.
        
        Returns:
            Dict: Toutes les métriques collectées
        """
        with self._lock:
            return dict(self.metrics)
    
    def get_system_info(self) -> Dict[str, Any]:
        """
        Récupère les informations système de base.
        
        Returns:
            Dict: Informations système
        """
        info = {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "platform_release": platform.release(),
            "python_version": platform.python_version(),
            "python_implementation": platform.python_implementation(),
            "hostname": platform.node(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "cpu_count": psutil.cpu_count(logical=True),
            "physical_cpu_count": psutil.cpu_count(logical=False) if hasattr(psutil, "cpu_count") else None,
            "memory_total": psutil.virtual_memory().total,
            "uptime": time.time() - psutil.boot_time(),
            "bot_uptime": time.time() - self.process.create_time() if self.process else 0
        }
        return info
    
    def get_cpu_info(self) -> Dict[str, Any]:
        """
        Récupère les informations détaillées sur le CPU.
        
        Returns:
            Dict: Informations sur le CPU
        """
        with self._lock:
            return self.metrics["cpu"]
    
    def get_memory_info(self) -> Dict[str, Any]:
        """
        Récupère les informations détaillées sur la mémoire.
        
        Returns:
            Dict: Informations sur la mémoire
        """
        with self._lock:
            return self.metrics["memory"]
    
    def get_disk_info(self) -> Dict[str, Any]:
        """
        Récupère les informations détaillées sur le disque.
        
        Returns:
            Dict: Informations sur le disque
        """
        with self._lock:
            return self.metrics["disk"]
    
    def get_network_info(self) -> Dict[str, Any]:
        """
        Récupère les informations détaillées sur le réseau.
        
        Returns:
            Dict: Informations sur le réseau
        """
        with self._lock:
            return self.metrics["network"]
    
    def get_process_info(self) -> Dict[str, Any]:
        """
        Récupère les informations détaillées sur le processus.
        
        Returns:
            Dict: Informations sur le processus
        """
        with self._lock:
            return self.metrics["process"]
    
    def save_report(self, filename: Optional[str] = None) -> Optional[str]:
        """
        Sauvegarde un rapport des métriques système actuelles.
        
        Args:
            filename: Nom du fichier de rapport (optionnel)
            
        Returns:
            str: Chemin du fichier de rapport ou None en cas d'erreur
        """
        try:
            # Générer un nom de fichier si aucun n'est fourni
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"system_report_{timestamp}.json"
            
            filepath = os.path.join(self.reports_dir, filename)
            
            # Créer le rapport
            report = {
                "timestamp": datetime.now().isoformat(),
                "metrics": self.get_metrics(),
                "system_info": self.get_system_info(),
                "thresholds": dict(self._thresholds)
            }
            
            # Sauvegarder le rapport
            with open(filepath, 'w') as f:
                json.dump(report, f, indent=2)
            
            logger.info(f"Rapport système sauvegardé dans {filepath}")
            return filepath
        
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde du rapport système: {str(e)}")
            return None

    def get_system_usage(self) -> Dict[str, float]:
        """
        Récupère un résumé de l'utilisation système actuelle.
        
        Returns:
            Dict: Résumé de l'utilisation (pourcentages CPU, mémoire, disque)
        """
        with self._lock:
            return {
                "cpu_percent": self.metrics["cpu"]["percent"],
                "memory_percent": self.metrics["memory"]["percent"],
                "disk_percent": self.metrics["disk"]["percent"],
                "process_cpu_percent": self.metrics["process"]["cpu_percent"],
                "process_memory_percent": self.metrics["process"]["memory_percent"]
            }
    
    def optimize_system(self) -> Dict[str, Any]:
        """
        Tente d'optimiser l'utilisation des ressources système.
        Cette méthode est principalement informative et suggère des optimisations.
        
        Returns:
            Dict: Suggestions d'optimisation et actions effectuées
        """
        # Collecter les métriques actuelles
        self.collect_metrics()
        
        results = {
            "suggestions": [],
            "actions": [],
            "status": "ok"
        }
        
        with self._lock:
            # Vérifier l'utilisation du CPU
            if self.metrics["process"]["cpu_percent"] > 80:
                results["suggestions"].append("Réduire le nombre de threads ou processus parallèles")
                results["suggestions"].append("Augmenter l'intervalle entre les vérifications des opportunités")
                results["status"] = "warning"
            
            # Vérifier l'utilisation de la mémoire
            if self.metrics["process"]["memory_percent"] > 80:
                results["suggestions"].append("Réduire la taille des caches en mémoire")
                results["suggestions"].append("Limiter le nombre de transactions surveillées simultanément")
                results["status"] = "warning"
            
            # Vérifier le nombre de threads
            if self.metrics["process"]["thread_count"] > 100:
                results["suggestions"].append("Réduire le nombre de threads pour éviter le context switching excessif")
                results["status"] = "warning"
            
            # Vérifier l'utilisation du disque
            if self.metrics["disk"]["percent"] > 85:
                results["suggestions"].append("Nettoyer les anciens logs et fichiers temporaires")
                results["suggestions"].append("Archiver les anciennes données de trading")
                results["status"] = "warning"
            
            # Si tout va bien
            if not results["suggestions"]:
                results["suggestions"].append("Aucune optimisation nécessaire, le système fonctionne correctement")
        
        return results
    
    async def get_system_info_async(self) -> Dict[str, Any]:
        """Version asynchrone de get_system_info pour l'interface Telegram"""
        return self.get_system_info()
    
    async def get_system_usage_async(self) -> Dict[str, float]:
        """Version asynchrone de get_system_usage pour l'interface Telegram"""
        return self.get_system_usage()


def get_system_monitor() -> SystemMonitor:
    """
    Fonction utilitaire pour obtenir l'instance singleton du moniteur système.
    
    Returns:
        Instance singleton de SystemMonitor
    """
    return SystemMonitor() 