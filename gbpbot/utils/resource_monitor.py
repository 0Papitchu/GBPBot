#!/usr/bin/env python3
"""
Module de surveillance des ressources pour GBPBot.

Ce module fournit des fonctionnalités pour surveiller l'utilisation des ressources
système (CPU, mémoire, réseau) et optimiser les performances du bot en conséquence.
"""

import os
import time
import psutil
import logging
import threading
import asyncio
from typing import Dict, List, Optional, Callable, Any, Tuple

# Configuration du logger
logger = logging.getLogger(__name__)

class ResourceMonitor:
    """
    Classe pour surveiller les ressources système et optimiser les performances.
    """
    
    _instance = None
    
    def __new__(cls):
        """Implémentation du pattern Singleton"""
        if cls._instance is None:
            cls._instance = super(ResourceMonitor, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """
        Initialise le moniteur de ressources.
        """
        if not hasattr(self, 'initialized'):
            self.initialized = True
            self.monitoring_interval = 5  # secondes
            self.monitoring_thread = None
            self.running = False
            self.handlers = []
            self.last_stats = {}
            self.stats_history = []
            self.max_history_size = 60  # Garder 60 points de données (5 minutes avec intervalle de 5s)
            
            # Seuils d'alerte
            self.cpu_threshold = 80  # %
            self.memory_threshold = 80  # %
            self.disk_threshold = 90  # %
            
            logger.info("Moniteur de ressources initialisé")
    
    def start(self):
        """
        Démarre la surveillance des ressources.
        """
        if self.running:
            logger.warning("Le moniteur de ressources est déjà en cours d'exécution")
            return
        
        self.running = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        logger.info("Surveillance des ressources démarrée")
    
    def stop(self):
        """
        Arrête la surveillance des ressources.
        """
        if not self.running:
            logger.warning("Le moniteur de ressources n'est pas en cours d'exécution")
            return
        
        self.running = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=2)
        logger.info("Surveillance des ressources arrêtée")
    
    def register_handler(self, handler: Callable[[Dict[str, Any]], None]):
        """
        Enregistre un gestionnaire pour les événements de ressources.
        
        Args:
            handler: Fonction à appeler avec les statistiques de ressources
        """
        if handler not in self.handlers:
            self.handlers.append(handler)
            logger.debug(f"Gestionnaire enregistré: {handler.__name__}")
    
    def unregister_handler(self, handler: Callable[[Dict[str, Any]], None]):
        """
        Désenregistre un gestionnaire pour les événements de ressources.
        
        Args:
            handler: Fonction à désenregistrer
        """
        if handler in self.handlers:
            self.handlers.remove(handler)
            logger.debug(f"Gestionnaire désenregistré: {handler.__name__}")
    
    def get_current_stats(self) -> Dict[str, Any]:
        """
        Obtient les statistiques actuelles des ressources.
        
        Returns:
            Dictionnaire contenant les statistiques des ressources
        """
        return self._collect_stats()
    
    def get_stats_history(self) -> List[Dict[str, Any]]:
        """
        Obtient l'historique des statistiques des ressources.
        
        Returns:
            Liste de dictionnaires contenant les statistiques des ressources
        """
        return self.stats_history
    
    def _monitoring_loop(self):
        """
        Boucle principale de surveillance des ressources.
        """
        logger.debug("Démarrage de la boucle de surveillance des ressources")
        
        while self.running:
            try:
                # Collecter les statistiques
                stats = self._collect_stats()
                
                # Mettre à jour les dernières statistiques
                self.last_stats = stats
                
                # Ajouter à l'historique
                self.stats_history.append(stats)
                
                # Limiter la taille de l'historique
                if len(self.stats_history) > self.max_history_size:
                    self.stats_history.pop(0)
                
                # Vérifier les seuils d'alerte
                self._check_thresholds(stats)
                
                # Notifier les gestionnaires
                for handler in self.handlers:
                    try:
                        handler(stats)
                    except Exception as e:
                        logger.error(f"Erreur dans le gestionnaire {handler.__name__}: {e}")
                
                # Attendre l'intervalle de surveillance
                time.sleep(self.monitoring_interval)
                
            except Exception as e:
                logger.error(f"Erreur dans la boucle de surveillance: {e}")
                time.sleep(self.monitoring_interval)
    
    def _collect_stats(self) -> Dict[str, Any]:
        """
        Collecte les statistiques des ressources système.
        
        Returns:
            Dictionnaire contenant les statistiques des ressources
        """
        stats = {
            "timestamp": time.time(),
            "cpu": {},
            "memory": {},
            "disk": {},
            "network": {}
        }
        
        # CPU
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_count = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq()
        
        stats["cpu"]["percent"] = cpu_percent
        stats["cpu"]["count"] = cpu_count
        if cpu_freq:
            stats["cpu"]["freq_current"] = cpu_freq.current
            stats["cpu"]["freq_min"] = cpu_freq.min
            stats["cpu"]["freq_max"] = cpu_freq.max
        
        # Mémoire
        memory = psutil.virtual_memory()
        
        stats["memory"]["total"] = memory.total
        stats["memory"]["available"] = memory.available
        stats["memory"]["used"] = memory.used
        stats["memory"]["percent"] = memory.percent
        
        # Disque
        disk = psutil.disk_usage('/')
        
        stats["disk"]["total"] = disk.total
        stats["disk"]["used"] = disk.used
        stats["disk"]["free"] = disk.free
        stats["disk"]["percent"] = disk.percent
        
        # Réseau
        net_io = psutil.net_io_counters()
        
        stats["network"]["bytes_sent"] = net_io.bytes_sent
        stats["network"]["bytes_recv"] = net_io.bytes_recv
        stats["network"]["packets_sent"] = net_io.packets_sent
        stats["network"]["packets_recv"] = net_io.packets_recv
        
        return stats
    
    def _check_thresholds(self, stats: Dict[str, Any]):
        """
        Vérifie si les statistiques dépassent les seuils d'alerte.
        
        Args:
            stats: Statistiques des ressources
        """
        # Vérifier le CPU
        if stats["cpu"]["percent"] > self.cpu_threshold:
            logger.warning(f"Utilisation CPU élevée: {stats['cpu']['percent']}%")
        
        # Vérifier la mémoire
        if stats["memory"]["percent"] > self.memory_threshold:
            logger.warning(f"Utilisation mémoire élevée: {stats['memory']['percent']}%")
        
        # Vérifier le disque
        if stats["disk"]["percent"] > self.disk_threshold:
            logger.warning(f"Utilisation disque élevée: {stats['disk']['percent']}%")

# Créer une instance singleton
resource_monitor = ResourceMonitor()

# Fonction pour démarrer la surveillance
def start_monitoring():
    """
    Démarre la surveillance des ressources.
    """
    resource_monitor.start()

# Fonction pour arrêter la surveillance
def stop_monitoring():
    """
    Arrête la surveillance des ressources.
    """
    resource_monitor.stop()

# Fonction pour obtenir les statistiques actuelles
def get_current_stats() -> Dict[str, Any]:
    """
    Obtient les statistiques actuelles des ressources.
    
    Returns:
        Dictionnaire contenant les statistiques des ressources
    """
    return resource_monitor.get_current_stats()

# Fonction pour obtenir l'historique des statistiques
def get_stats_history() -> List[Dict[str, Any]]:
    """
    Obtient l'historique des statistiques des ressources.
    
    Returns:
        Liste de dictionnaires contenant les statistiques des ressources
    """
    return resource_monitor.get_stats_history()

# Fonction pour enregistrer un gestionnaire
def register_handler(handler: Callable[[Dict[str, Any]], None]):
    """
    Enregistre un gestionnaire pour les événements de ressources.
    
    Args:
        handler: Fonction à appeler avec les statistiques de ressources
    """
    resource_monitor.register_handler(handler)

# Fonction pour désenregistrer un gestionnaire
def unregister_handler(handler: Callable[[Dict[str, Any]], None]):
    """
    Désenregistre un gestionnaire pour les événements de ressources.
    
    Args:
        handler: Fonction à désenregistrer
    """
    resource_monitor.unregister_handler(handler)

# Démarrer automatiquement la surveillance si le module est importé
if __name__ != "__main__":
    start_monitoring() 