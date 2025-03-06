"""
Module d'optimisation de mémoire pour GBPBot
===========================================

Ce module fournit des utilitaires pour surveiller et limiter l'utilisation
de la mémoire par les modules intensifs comme le Machine Learning.
"""

import os
import gc
import time
import logging
import threading
import psutil
from typing import Dict, Any, Optional, Callable

# Configuration du logging
logger = logging.getLogger("gbpbot.utils.memory_optimizer")

class MemoryMonitor:
    """
    Moniteur de mémoire qui surveille l'utilisation RAM et applique des optimisations
    si nécessaire pour éviter les problèmes de mémoire insuffisante.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialise le moniteur de mémoire
        
        Args:
            config: Configuration avec les limites de mémoire
        """
        self.config = config or {}
        
        # Récupérer les limites de la configuration ou utiliser des valeurs par défaut
        self.max_memory_mb = int(self.config.get("ML_MAX_MEMORY_USAGE", 4096))  # 4GB par défaut
        self.warning_threshold = 0.8  # 80% de la limite max
        self.critical_threshold = 0.95  # 95% de la limite max
        
        # Récupérer l'intervalle de vérification ou utiliser une valeur par défaut
        self.check_interval = int(self.config.get("MEMORY_CHECK_INTERVAL", 60))  # 60 secondes par défaut
        
        # État du moniteur
        self.running = False
        self.monitoring_thread = None
        
        # Statistiques
        self.stats = {
            "peak_memory_usage_mb": 0,
            "last_memory_usage_mb": 0,
            "memory_cleanup_count": 0,
            "last_cleanup_time": None
        }
        
        logger.info(f"Moniteur de mémoire initialisé (limite: {self.max_memory_mb}MB)")
    
    def start(self) -> bool:
        """
        Démarre le moniteur de mémoire
        
        Returns:
            bool: True si démarré avec succès, False sinon
        """
        if self.running:
            logger.warning("Le moniteur de mémoire est déjà en cours d'exécution")
            return True
            
        try:
            self.running = True
            self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            self.monitoring_thread.start()
            logger.info("Moniteur de mémoire démarré avec succès")
            return True
        except Exception as e:
            logger.error(f"Erreur lors du démarrage du moniteur de mémoire: {str(e)}")
            self.running = False
            return False
    
    def stop(self) -> bool:
        """
        Arrête le moniteur de mémoire
        
        Returns:
            bool: True si arrêté avec succès, False sinon
        """
        if not self.running:
            logger.warning("Le moniteur de mémoire n'est pas en cours d'exécution")
            return True
            
        try:
            self.running = False
            if self.monitoring_thread and self.monitoring_thread.is_alive():
                self.monitoring_thread.join(timeout=5)
            logger.info("Moniteur de mémoire arrêté avec succès")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de l'arrêt du moniteur de mémoire: {str(e)}")
            return False
    
    def _monitoring_loop(self) -> None:
        """
        Boucle de surveillance de la mémoire
        """
        while self.running:
            try:
                # Récupérer l'utilisation de la mémoire actuelle
                current_usage = self.get_memory_usage()
                self.stats["last_memory_usage_mb"] = current_usage
                
                # Mettre à jour l'utilisation maximale
                if current_usage > self.stats["peak_memory_usage_mb"]:
                    self.stats["peak_memory_usage_mb"] = current_usage
                
                # Vérifier si nous dépassons le seuil critique
                if current_usage > self.max_memory_mb * self.critical_threshold:
                    logger.warning(f"ALERTE MÉMOIRE CRITIQUE: {current_usage}MB utilisés (seuil: {self.max_memory_mb * self.critical_threshold}MB)")
                    self._perform_emergency_cleanup()
                    
                # Vérifier si nous dépassons le seuil d'avertissement
                elif current_usage > self.max_memory_mb * self.warning_threshold:
                    logger.info(f"Avertissement mémoire: {current_usage}MB utilisés (seuil: {self.max_memory_mb * self.warning_threshold}MB)")
                    self._perform_cleanup()
                
                # Attendre avant la prochaine vérification
                time.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Erreur dans la boucle de surveillance mémoire: {str(e)}")
                time.sleep(self.check_interval)
    
    def get_memory_usage(self) -> float:
        """
        Récupère l'utilisation de mémoire actuelle du processus en MB
        
        Returns:
            float: Utilisation de mémoire en MB
        """
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        return memory_info.rss / (1024 * 1024)  # Convertir en MB
    
    def _perform_cleanup(self) -> None:
        """
        Effectue un nettoyage standard de la mémoire
        """
        # Déclencher le ramasse-miettes
        gc.collect()
        
        # Mettre à jour les statistiques
        self.stats["memory_cleanup_count"] += 1
        self.stats["last_cleanup_time"] = time.time()
        
        logger.info("Nettoyage mémoire standard effectué")
    
    def _perform_emergency_cleanup(self) -> None:
        """
        Effectue un nettoyage d'urgence de la mémoire
        """
        # Déclencher le ramasse-miettes plusieurs fois
        for _ in range(3):
            gc.collect()
        
        # Mettre à jour les statistiques
        self.stats["memory_cleanup_count"] += 1
        self.stats["last_cleanup_time"] = time.time()
        
        logger.warning("Nettoyage mémoire d'urgence effectué")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Récupère les statistiques du moniteur de mémoire
        
        Returns:
            Dict[str, Any]: Statistiques du moniteur
        """
        # Mettre à jour les statistiques avec les valeurs actuelles
        self.stats["last_memory_usage_mb"] = self.get_memory_usage()
        
        # Calculer des statistiques additionnelles
        memory_usage_percent = (self.stats["last_memory_usage_mb"] / self.max_memory_mb) * 100
        
        return {
            **self.stats,
            "max_memory_mb": self.max_memory_mb,
            "memory_usage_percent": memory_usage_percent,
            "status": "ok" if memory_usage_percent < 80 else "warning" if memory_usage_percent < 95 else "critical"
        }


class MemoryOptimizedML:
    """
    Classe utilitaire pour optimiser l'utilisation de la mémoire
    dans les opérations de Machine Learning.
    """
    
    @staticmethod
    def limit_batch_size(original_size: int, config: Dict[str, Any]) -> int:
        """
        Calcule une taille de batch optimisée en fonction de la configuration
        
        Args:
            original_size: Taille de batch initiale
            config: Configuration avec les limites de mémoire
            
        Returns:
            int: Taille de batch optimisée
        """
        max_memory_mb = int(config.get("ML_MAX_MEMORY_USAGE", 4096))
        memory_usage = psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)
        memory_remaining = max(max_memory_mb - memory_usage, 512)  # Au moins 512MB
        
        # Réduire la taille du batch en fonction de la mémoire disponible
        if memory_remaining < 1024:  # Moins de 1GB disponible
            return min(original_size, 16)
        elif memory_remaining < 2048:  # Moins de 2GB disponible
            return min(original_size, 32)
        else:
            return min(original_size, 64)  # 64 max pour votre configuration
    
    @staticmethod
    def batch_process(items: list, process_func: Callable, config: Dict[str, Any]) -> list:
        """
        Traite une liste d'éléments par lots pour limiter l'utilisation de mémoire
        
        Args:
            items: Liste d'éléments à traiter
            process_func: Fonction de traitement qui prend un lot en entrée
            config: Configuration avec les limites de mémoire
            
        Returns:
            list: Résultats combinés
        """
        batch_size = MemoryOptimizedML.limit_batch_size(64, config)
        results = []
        
        # Traiter par lots
        for i in range(0, len(items), batch_size):
            batch = items[i:i+batch_size]
            batch_result = process_func(batch)
            results.extend(batch_result)
            
            # Nettoyer la mémoire entre les lots
            if i + batch_size < len(items):
                gc.collect()
                time.sleep(0.1)  # Petit délai pour laisser le GC travailler
        
        return results


def create_memory_monitor(config: Dict[str, Any] = None) -> MemoryMonitor:
    """
    Crée une instance du moniteur de mémoire
    
    Args:
        config: Configuration avec les limites de mémoire
        
    Returns:
        MemoryMonitor: Instance du moniteur
    """
    return MemoryMonitor(config=config) 