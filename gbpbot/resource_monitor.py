"""
Module de surveillance des ressources système
============================================

Ce module permet de surveiller l'utilisation des ressources du système
et d'adapter le comportement de GBPBot en conséquence pour éviter
de surcharger le PC.
"""

import os
import time
import psutil
import threading
import logging
from typing import Dict, Any, Optional, Callable, List, Tuple

# Configurer le logging
logger = logging.getLogger(__name__)

# Importer la configuration
try:
    from gbpbot.core import config
except ImportError:
    # Utiliser des valeurs par défaut si le module de configuration n'est pas disponible
    logger.warning("Module de configuration non disponible, utilisation des valeurs par défaut")
    config = None


class ResourceMonitor:
    """Classe pour surveiller les ressources système et adapter le comportement du bot"""
    
    def __init__(self):
        """Initialise le moniteur de ressources"""
        self.running = False
        self.monitor_thread = None
        self.check_interval = 5  # secondes
        
        # Seuils d'utilisation des ressources - adaptés à un i5-12400F avec 16GB RAM
        self.cpu_threshold = 70  # pourcentage - réduit pour laisser de la marge au système
        self.memory_threshold = 70  # pourcentage - réduit pour éviter le swapping
        self.disk_threshold = 85  # pourcentage
        
        # Valeurs d'optimisation automatique
        self.auto_optimize = True  # Activation de l'optimisation automatique
        self.ml_memory_limit = 4096  # 4GB maximum pour machine learning en MB
        self.tx_history_limit = 10000  # Nombre maximal de transactions à conserver en mémoire
        self.connection_pool_size = 20  # Taille du pool de connexions RPC
        
        # Callbacks et abonnés
        self.callbacks = {
            "cpu_high": [],
            "memory_high": [],
            "disk_high": [],
            "resources_normal": [],
            "optimization_applied": []  # Nouveau type d'événement
        }
        
        # État actuel des ressources
        self.current_state = {
            "cpu_usage": 0,
            "memory_usage": 0,
            "disk_usage": 0,
            "is_cpu_high": False,
            "is_memory_high": False,
            "is_disk_high": False,
            "timestamp": time.time(),
            "applied_optimizations": []  # Liste des optimisations appliquées
        }
        
        # Charger les seuils depuis la configuration si disponible
        self._load_thresholds()
        
    def _load_thresholds(self):
        """Charge les seuils depuis la configuration"""
        if config:
            resource_limits = config.get("resource_limits", {})
            self.cpu_threshold = resource_limits.get("max_cpu_usage_percent", self.cpu_threshold)
            self.memory_threshold = resource_limits.get("max_ram_usage_percent", self.memory_threshold)
            self.disk_threshold = resource_limits.get("max_disk_usage_percent", self.disk_threshold)
            self.check_interval = resource_limits.get("resource_check_interval", self.check_interval)
            
            # Chargement des paramètres d'optimisation
            self.auto_optimize = resource_limits.get("auto_optimize", self.auto_optimize)
            self.ml_memory_limit = resource_limits.get("ml_memory_limit", self.ml_memory_limit)
            self.tx_history_limit = resource_limits.get("tx_history_limit", self.tx_history_limit)
            self.connection_pool_size = resource_limits.get("connection_pool_size", self.connection_pool_size)
            
    def start(self):
        """Démarre la surveillance des ressources"""
        if self.running:
            logger.warning("Le moniteur de ressources est déjà en cours d'exécution")
            return
            
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Moniteur de ressources démarré")
        
        # Appliquer les optimisations initiales basées sur la configuration matérielle
        if self.auto_optimize:
            self._apply_system_optimizations()
        
    def stop(self):
        """Arrête la surveillance des ressources"""
        if not self.running:
            logger.warning("Le moniteur de ressources n'est pas en cours d'exécution")
            return
            
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
        logger.info("Moniteur de ressources arrêté")
        
    def _monitor_loop(self):
        """Boucle principale de surveillance des ressources"""
        while self.running:
            try:
                self._check_resources()
                
                # Appliquer des optimisations si nécessaire
                if self.auto_optimize and (self.current_state["is_cpu_high"] or 
                                           self.current_state["is_memory_high"] or 
                                           self.current_state["is_disk_high"]):
                    self._apply_dynamic_optimizations()
                
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Erreur lors de la surveillance des ressources: {str(e)}")
                time.sleep(self.check_interval * 2)  # Attendre plus longtemps en cas d'erreur
                
    def _check_resources(self):
        """Vérifie l'état des ressources système"""
        # Collecter les métriques
        cpu_usage = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage(os.path.abspath(os.sep))
        
        # Mettre à jour l'état actuel
        previous_state = self.current_state.copy()
        self.current_state.update({
            "cpu_usage": cpu_usage,
            "memory_usage": memory.percent,
            "disk_usage": disk.percent,
            "is_cpu_high": cpu_usage > self.cpu_threshold,
            "is_memory_high": memory.percent > self.memory_threshold,
            "is_disk_high": disk.percent > self.disk_threshold,
            "timestamp": time.time()
        })
        
        # Déterminer si l'état des ressources a changé
        cpu_changed = previous_state["is_cpu_high"] != self.current_state["is_cpu_high"]
        memory_changed = previous_state["is_memory_high"] != self.current_state["is_memory_high"]
        disk_changed = previous_state["is_disk_high"] != self.current_state["is_disk_high"]
        
        # Logger les changements d'état
        if cpu_changed:
            if self.current_state["is_cpu_high"]:
                logger.warning(f"L'utilisation du CPU est élevée: {cpu_usage:.1f}% > {self.cpu_threshold}%")
            else:
                logger.info(f"L'utilisation du CPU est revenue à la normale: {cpu_usage:.1f}% <= {self.cpu_threshold}%")
                
        if memory_changed:
            if self.current_state["is_memory_high"]:
                logger.warning(f"L'utilisation de la mémoire est élevée: {memory.percent:.1f}% > {self.memory_threshold}%")
            else:
                logger.info(f"L'utilisation de la mémoire est revenue à la normale: {memory.percent:.1f}% <= {self.memory_threshold}%")
                
        if disk_changed:
            if self.current_state["is_disk_high"]:
                logger.warning(f"L'utilisation du disque est élevée: {disk.percent:.1f}% > {self.disk_threshold}%")
            else:
                logger.info(f"L'utilisation du disque est revenue à la normale: {disk.percent:.1f}% <= {self.disk_threshold}%")
                
        # Appeler les callbacks appropriés
        if self.current_state["is_cpu_high"] and (cpu_changed or self._should_repeat_notification("cpu_high")):
            self._notify_subscribers("cpu_high", self.current_state)
            
        if self.current_state["is_memory_high"] and (memory_changed or self._should_repeat_notification("memory_high")):
            self._notify_subscribers("memory_high", self.current_state)
            
        if self.current_state["is_disk_high"] and (disk_changed or self._should_repeat_notification("disk_high")):
            self._notify_subscribers("disk_high", self.current_state)
            
        # Si toutes les ressources sont revenues à la normale
        if not any([self.current_state["is_cpu_high"], 
                  self.current_state["is_memory_high"], 
                  self.current_state["is_disk_high"]]):
            # Et qu'elles étaient élevées auparavant
            if any([previous_state["is_cpu_high"],
                  previous_state["is_memory_high"],
                  previous_state["is_disk_high"]]):
                self._notify_subscribers("resources_normal", self.current_state)
                
    def _should_repeat_notification(self, event_type: str) -> bool:
        """Détermine si une notification doit être répétée"""
        # Répéter les notifications toutes les minutes (12 intervalles de 5 secondes)
        notification_interval = 12 * self.check_interval
        last_notification = getattr(self, f"_last_{event_type}_notification", 0)
        now = time.time()
        
        if now - last_notification > notification_interval:
            setattr(self, f"_last_{event_type}_notification", now)
            return True
            
        return False
    
    def _apply_system_optimizations(self):
        """Applique des optimisations initiales basées sur la configuration matérielle"""
        optimizations_applied = []
        
        try:
            # Détection du nombre de cœurs CPU pour optimiser les pools de threads
            cpu_count = psutil.cpu_count(logical=True)  # Nombre de threads logiques
            physical_cores = psutil.cpu_count(logical=False)  # Nombre de cœurs physiques
            
            # Optimiser les valeurs pour le i5-12400F (6 cœurs / 12 threads)
            thread_pool_size = max(2, min(cpu_count - 2, 8))  # Max 8 threads, garder 2 libres
            
            # Configurer manuellement la taille du pool de connexions RPC
            self.connection_pool_size = max(5, min(thread_pool_size * 2, 20))
            
            # Déterminer la limite mémoire pour le ML en fonction de la RAM totale
            total_memory_mb = psutil.virtual_memory().total / (1024 * 1024)
            # 25% de la RAM totale mais pas plus de 4GB
            self.ml_memory_limit = min(int(total_memory_mb * 0.25), 4096)
            
            # Optimiser la taille de l'historique de transactions
            if total_memory_mb <= 8192:  # 8GB ou moins
                self.tx_history_limit = 5000
            elif total_memory_mb <= 16384:  # 16GB
                self.tx_history_limit = 10000
            else:  # Plus de 16GB
                self.tx_history_limit = 20000
                
            optimizations_applied = [
                f"Thread pool: {thread_pool_size}",
                f"Connection pool: {self.connection_pool_size}",
                f"ML memory limit: {self.ml_memory_limit}MB",
                f"TX history limit: {self.tx_history_limit}"
            ]
                
            logger.info(f"Optimisations système appliquées: {', '.join(optimizations_applied)}")
            
            # Mettre à jour l'état des optimisations
            self.current_state["applied_optimizations"] = optimizations_applied
            self._notify_subscribers("optimization_applied", {
                "type": "system",
                "optimizations": optimizations_applied
            })
            
            return True
        except Exception as e:
            logger.error(f"Erreur lors de l'application des optimisations système: {str(e)}")
            return False
    
    def _apply_dynamic_optimizations(self):
        """Applique des optimisations basées sur l'utilisation actuelle des ressources"""
        try:
            optimizations_applied = []
            
            # Optimisations CPU
            if self.current_state["is_cpu_high"]:
                # Réduire la fréquence de surveillance de certains modules
                if self.check_interval < 10:
                    self.check_interval = min(10, self.check_interval * 1.5)
                    optimizations_applied.append(f"Intervalle de surveillance augmenté à {self.check_interval}s")
                
                # Réduire le nombre de connexions RPC simultanées
                if self.connection_pool_size > 5:
                    self.connection_pool_size = max(5, self.connection_pool_size - 5)
                    optimizations_applied.append(f"Pool de connexions réduit à {self.connection_pool_size}")
            
            # Optimisations mémoire
            if self.current_state["is_memory_high"]:
                # Réduire la limite mémoire pour le ML
                current_limit = self.ml_memory_limit
                self.ml_memory_limit = max(1024, int(current_limit * 0.8))  # Réduire de 20%, minimum 1GB
                optimizations_applied.append(f"Limite mémoire ML réduite à {self.ml_memory_limit}MB")
                
                # Réduire la taille de l'historique des transactions
                current_limit = self.tx_history_limit
                self.tx_history_limit = max(1000, int(current_limit * 0.7))  # Réduire de 30%, minimum 1000
                optimizations_applied.append(f"Limite historique TX réduite à {self.tx_history_limit}")
                
                # Nettoyer les caches
                self._clean_memory_caches()
                optimizations_applied.append("Nettoyage des caches mémoire")
            
            # Optimisations disque
            if self.current_state["is_disk_high"]:
                # Forcer la purge des logs
                self._purge_old_logs()
                optimizations_applied.append("Purge des anciens logs")
            
            if optimizations_applied:
                logger.info(f"Optimisations dynamiques appliquées: {', '.join(optimizations_applied)}")
                
                # Mettre à jour l'état des optimisations
                self.current_state["applied_optimizations"].extend(optimizations_applied)
                self._notify_subscribers("optimization_applied", {
                    "type": "dynamic",
                    "optimizations": optimizations_applied
                })
                
            return True
        except Exception as e:
            logger.error(f"Erreur lors de l'application des optimisations dynamiques: {str(e)}")
            return False
    
    def _clean_memory_caches(self):
        """Nettoie les caches mémoire pour libérer de la RAM"""
        try:
            # Forcer le garbage collector
            import gc
            gc.collect()
            
            # Informer les modules d'optimiser leur mémoire
            self._notify_subscribers("memory_high", {
                "type": "cache_cleanup",
                "memory_usage": self.current_state["memory_usage"],
                "memory_threshold": self.memory_threshold
            })
            
            return True
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage des caches mémoire: {str(e)}")
            return False
    
    def _purge_old_logs(self):
        """Purge les anciens fichiers de logs"""
        try:
            log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs")
            if os.path.exists(log_dir):
                current_time = time.time()
                deleted_count = 0
                deleted_size = 0
                
                for file in os.listdir(log_dir):
                    if file.endswith(".log"):
                        file_path = os.path.join(log_dir, file)
                        file_time = os.path.getmtime(file_path)
                        file_age_days = (current_time - file_time) / (60 * 60 * 24)
                        
                        # Supprimer les logs de plus de 7 jours
                        if file_age_days > 7:
                            size = os.path.getsize(file_path)
                            deleted_size += size
                            os.remove(file_path)
                            deleted_count += 1
                
                if deleted_count > 0:
                    logger.info(f"Purge des logs: {deleted_count} fichiers supprimés, {deleted_size / (1024*1024):.2f} MB libérés")
            
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la purge des logs: {str(e)}")
            return False
        
    def _notify_subscribers(self, event_type: str, state: Dict[str, Any]):
        """Notifie les abonnés d'un événement"""
        for callback in self.callbacks.get(event_type, []):
            try:
                callback(state)
            except Exception as e:
                logger.error(f"Erreur lors de l'appel du callback '{event_type}': {str(e)}")
                
    def subscribe(self, event_type: str, callback: Callable[[Dict[str, Any]], None]) -> bool:
        """
        Abonne une fonction à un type d'événement
        
        Args:
            event_type: Type d'événement (cpu_high, memory_high, disk_high, resources_normal, optimization_applied)
            callback: Fonction à appeler lors de l'événement
            
        Returns:
            bool: True si l'abonnement a réussi, False sinon
        """
        if event_type not in self.callbacks:
            logger.error(f"Type d'événement inconnu: {event_type}")
            return False
            
        if callback not in self.callbacks[event_type]:
            self.callbacks[event_type].append(callback)
            logger.debug(f"Abonnement au type d'événement '{event_type}' réussi")
            return True
            
        return False
        
    def unsubscribe(self, event_type: str, callback: Callable[[Dict[str, Any]], None]) -> bool:
        """
        Désabonne une fonction d'un type d'événement
        
        Args:
            event_type: Type d'événement
            callback: Fonction à désabonner
            
        Returns:
            bool: True si le désabonnement a réussi, False sinon
        """
        if event_type not in self.callbacks:
            logger.error(f"Type d'événement inconnu: {event_type}")
            return False
            
        if callback in self.callbacks[event_type]:
            self.callbacks[event_type].remove(callback)
            logger.debug(f"Désabonnement du type d'événement '{event_type}' réussi")
            return True
            
        logger.warning(f"Fonction non abonnée à l'événement '{event_type}'")
        return False
        
    def get_current_state(self) -> Dict[str, Any]:
        """
        Récupère l'état actuel des ressources
        
        Returns:
            Dict: État actuel des ressources
        """
        return self.current_state.copy()
        
    def update_thresholds(self, cpu: Optional[int] = None, memory: Optional[int] = None, 
                       disk: Optional[int] = None, interval: Optional[int] = None):
        """
        Met à jour les seuils d'utilisation des ressources
        
        Args:
            cpu: Seuil d'utilisation du CPU (pourcentage)
            memory: Seuil d'utilisation de la mémoire (pourcentage)
            disk: Seuil d'utilisation du disque (pourcentage)
            interval: Intervalle de vérification (secondes)
        """
        if cpu is not None:
            self.cpu_threshold = max(10, min(cpu, 95))  # Entre 10% et 95%
        
        if memory is not None:
            self.memory_threshold = max(10, min(memory, 95))  # Entre 10% et 95%
            
        if disk is not None:
            self.disk_threshold = max(10, min(disk, 95))  # Entre 10% et 95%
            
        if interval is not None:
            self.check_interval = max(1, min(interval, 60))  # Entre 1s et 60s
            
        logger.info(f"Seuils mis à jour: CPU {self.cpu_threshold}%, Mémoire {self.memory_threshold}%, "
                   f"Disque {self.disk_threshold}%, Intervalle {self.check_interval}s")
    
    def get_optimization_values(self) -> Dict[str, Any]:
        """
        Récupère les valeurs actuelles d'optimisation
        
        Returns:
            Dict: Valeurs d'optimisation
        """
        return {
            "auto_optimize": self.auto_optimize,
            "ml_memory_limit": self.ml_memory_limit,
            "tx_history_limit": self.tx_history_limit,
            "connection_pool_size": self.connection_pool_size,
            "applied_optimizations": self.current_state.get("applied_optimizations", [])
        }
    
    def set_optimization_values(self, auto_optimize: Optional[bool] = None,
                               ml_memory_limit: Optional[int] = None,
                               tx_history_limit: Optional[int] = None,
                               connection_pool_size: Optional[int] = None) -> bool:
        """
        Définit les valeurs d'optimisation
        
        Args:
            auto_optimize: Activer l'optimisation automatique
            ml_memory_limit: Limite mémoire pour le ML (MB)
            tx_history_limit: Limite de l'historique des transactions
            connection_pool_size: Taille du pool de connexions RPC
            
        Returns:
            bool: True si les valeurs ont été mises à jour, False sinon
        """
        try:
            if auto_optimize is not None:
                self.auto_optimize = bool(auto_optimize)
                
            if ml_memory_limit is not None:
                self.ml_memory_limit = max(512, min(ml_memory_limit, 8192))  # Entre 512MB et 8GB
                
            if tx_history_limit is not None:
                self.tx_history_limit = max(1000, min(tx_history_limit, 50000))  # Entre 1000 et 50000
                
            if connection_pool_size is not None:
                self.connection_pool_size = max(5, min(connection_pool_size, 50))  # Entre 5 et 50
                
            logger.info(f"Valeurs d'optimisation mises à jour: Auto-optimize {self.auto_optimize}, "
                       f"ML memory limit {self.ml_memory_limit}MB, "
                       f"TX history limit {self.tx_history_limit}, "
                       f"Connection pool size {self.connection_pool_size}")
            
            # Notifier les abonnés
            self._notify_subscribers("optimization_applied", {
                "type": "manual",
                "optimizations": [
                    f"Auto-optimize: {self.auto_optimize}",
                    f"ML memory limit: {self.ml_memory_limit}MB",
                    f"TX history limit: {self.tx_history_limit}",
                    f"Connection pool size: {self.connection_pool_size}"
                ]
            })
            
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour des valeurs d'optimisation: {str(e)}")
            return False


# Instance singleton
_resource_monitor = None

def get_instance():
    """Récupère l'instance du moniteur de ressources"""
    global _resource_monitor
    if _resource_monitor is None:
        _resource_monitor = ResourceMonitor()
    return _resource_monitor

def start():
    """Démarre le moniteur de ressources"""
    get_instance().start()

def stop():
    """Arrête le moniteur de ressources"""
    get_instance().stop()

def get_current_state() -> Dict[str, Any]:
    """Récupère l'état actuel des ressources"""
    return get_instance().get_current_state()

def subscribe(event_type: str, callback: Callable[[Dict[str, Any]], None]) -> bool:
    """Abonne une fonction à un type d'événement"""
    return get_instance().subscribe(event_type, callback)

def unsubscribe(event_type: str, callback: Callable[[Dict[str, Any]], None]) -> bool:
    """Désabonne une fonction d'un type d'événement"""
    return get_instance().unsubscribe(event_type, callback)

def update_thresholds(cpu: Optional[int] = None, memory: Optional[int] = None, 
                   disk: Optional[int] = None, interval: Optional[int] = None):
    """Met à jour les seuils d'utilisation des ressources"""
    get_instance().update_thresholds(cpu, memory, disk, interval)

def get_optimization_values() -> Dict[str, Any]:
    """Récupère les valeurs actuelles d'optimisation"""
    return get_instance().get_optimization_values()

def set_optimization_values(auto_optimize: Optional[bool] = None,
                           ml_memory_limit: Optional[int] = None,
                           tx_history_limit: Optional[int] = None,
                           connection_pool_size: Optional[int] = None) -> bool:
    """Définit les valeurs d'optimisation"""
    return get_instance().set_optimization_values(auto_optimize, ml_memory_limit, tx_history_limit, connection_pool_size) 