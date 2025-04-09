"""
Module de compatibilité pour GBPBot
==================================

Ce module fournit une couche de compatibilité pour assurer la transition en douceur
entre l'ancienne implémentation des systèmes de monitoring et d'optimisation
et la nouvelle architecture unifiée.

Il expose les anciennes interfaces, mais utilise les nouvelles implémentations
en arrière-plan, permettant ainsi d'éviter de casser le code existant.
"""

import logging
import importlib
from typing import Dict, Any, Optional, List, Union, Callable

# Configuration du logging
logger = logging.getLogger("gbpbot.compatibility")

# Import depuis le module monitoring sans créer de dépendance circulaire
from gbpbot.core.monitoring import SystemMonitor, get_system_monitor

# Import lazy pour éviter la dépendance circulaire
def _get_optimization_module():
    """
    Fonction d'import tardif (lazy import) pour éviter les imports circulaires.
    Retourne le module d'optimisation lorsqu'il est nécessaire.
    """
    try:
        return importlib.import_module("gbpbot.core.optimization")
    except ImportError as e:
        logger.warning(f"Impossible d'importer le module d'optimisation: {str(e)}")
        return None

# Classes de compatibilité pour le monitoring

class ResourceMonitorCompat:
    """
    Classe de compatibilité pour l'ancienne classe ResourceMonitor.
    Utilise le nouveau SystemMonitor en arrière-plan.
    """
    
    def __init__(self):
        """
        Initialise le moniteur de ressources compatible.
        Utilise le nouveau SystemMonitor en arrière-plan.
        """
        self._system_monitor = get_system_monitor()
        self._callbacks = {}
        self._active = False
        
        # Configuration par défaut
        self.config = {
            "cpu_threshold": 80,        # en pourcentage
            "memory_threshold": 85,     # en pourcentage
            "disk_threshold": 90,       # en pourcentage
            "check_interval": 5,        # en secondes
            "auto_optimize": True,      # activer l'optimisation automatique
            "ml_memory_limit": 2048,    # limite de mémoire pour ML en MB
            "tx_history_limit": 10000,  # limite d'historique de transactions
            "connection_pool_size": 20, # taille du pool de connexions
        }
        
        logger.info("ResourceMonitorCompat initialisé")
        
    def start(self):
        """Lance la surveillance des ressources."""
        self._active = True
        return self._system_monitor.start()
        
    def stop(self):
        """Arrête la surveillance des ressources."""
        self._active = False
        return self._system_monitor.stop()
        
    def _check_resources(self):
        """Vérification des ressources (méthode de compatibilité)."""
        if not self._active:
            return
        # Cette méthode existe pour des raisons de compatibilité mais n'est plus nécessaire
        pass
        
    def _apply_system_optimizations(self):
        """
        Applique les optimisations système (méthode de compatibilité).
        Utilise le nouveau HardwareOptimizer en arrière-plan.
        """
        optimizer = get_hardware_optimizer_compat()
        if optimizer:
            return optimizer.apply_optimizations()
        return False
    
    def subscribe(self, event_type: str, callback: Callable) -> bool:
        """
        S'abonne à un événement de ressources système.
        
        Args:
            event_type: Type d'événement ('cpu', 'memory', 'disk', 'all')
            callback: Fonction à appeler lors de l'événement
            
        Returns:
            True si l'abonnement a réussi, False sinon
        """
        if event_type not in ('cpu', 'memory', 'disk', 'all'):
            logger.warning(f"Type d'événement non supporté: {event_type}")
            return False
            
        # Adapter le callback au nouveau format
        def callback_wrapper(metric_name, value, threshold):
            # Convertir en format attendu par l'ancien callback
            metric_data = {
                "name": metric_name,
                "value": value,
                "threshold": threshold,
                "timestamp": self._system_monitor.get_current_timestamp()
            }
            callback(metric_data)
            
        # Enregistrer dans le système de monitoring
        self._callbacks[callback] = callback_wrapper
        return self._system_monitor.subscribe(event_type, callback_wrapper)
    
    def unsubscribe(self, event_type: str, callback: Callable) -> bool:
        """
        Se désabonne d'un événement de ressources système.
        
        Args:
            event_type: Type d'événement ('cpu', 'memory', 'disk', 'all')
            callback: Fonction à désabonner
            
        Returns:
            True si le désabonnement a réussi, False sinon
        """
        if callback in self._callbacks:
            wrapper = self._callbacks[callback]
            result = self._system_monitor.unsubscribe(event_type, wrapper)
            if result:
                del self._callbacks[callback]
            return result
        return False
    
    def get_current_state(self) -> Dict[str, Any]:
        """
        Récupère l'état actuel des ressources système.
        
        Returns:
            Dictionnaire contenant les mesures actuelles des ressources
        """
        metrics = self._system_monitor.get_current_metrics()
        
        # Adapter au format attendu par l'ancien API
        return {
            "cpu": {
                "usage": metrics.get("cpu_percent", 0),
                "threshold": self.config["cpu_threshold"],
                "cores": metrics.get("cpu_count", 0),
                "temperature": metrics.get("cpu_temperature", 0),
            },
            "memory": {
                "usage": metrics.get("memory_percent", 0),
                "available": metrics.get("memory_available", 0),
                "total": metrics.get("memory_total", 0),
                "threshold": self.config["memory_threshold"],
            },
            "disk": {
                "usage": metrics.get("disk_percent", 0),
                "available": metrics.get("disk_available", 0),
                "total": metrics.get("disk_total", 0),
                "threshold": self.config["disk_threshold"],
            },
            "timestamp": metrics.get("timestamp", 0),
        }
    
    def update_thresholds(self, cpu=None, memory=None, disk=None, interval=None):
        """
        Met à jour les seuils de déclenchement des alertes.
        
        Args:
            cpu: Seuil CPU en pourcentage
            memory: Seuil mémoire en pourcentage
            disk: Seuil disque en pourcentage
            interval: Intervalle de vérification en secondes
        """
        if cpu is not None:
            self.config["cpu_threshold"] = cpu
        if memory is not None:
            self.config["memory_threshold"] = memory
        if disk is not None:
            self.config["disk_threshold"] = disk
        if interval is not None:
            self.config["check_interval"] = interval
            
        # Mettre à jour la configuration du moniteur système
        return self._system_monitor.update_config(self.config)
    
    def get_optimization_values(self) -> Dict[str, Any]:
        """
        Récupère les valeurs de configuration des optimisations.
        
        Returns:
            Dictionnaire contenant les valeurs de configuration des optimisations
        """
        return {
            "auto_optimize": self.config["auto_optimize"],
            "ml_memory_limit": self.config["ml_memory_limit"],
            "tx_history_limit": self.config["tx_history_limit"],
            "connection_pool_size": self.config["connection_pool_size"],
        }
    
    def set_optimization_values(self, auto_optimize=None, ml_memory_limit=None,
                      tx_history_limit=None, connection_pool_size=None) -> bool:
        """
        Configure les valeurs d'optimisation.
        
        Args:
            auto_optimize: Activer l'optimisation automatique
            ml_memory_limit: Limite de mémoire pour ML en MB
            tx_history_limit: Limite d'historique de transactions
            connection_pool_size: Taille du pool de connexions
            
        Returns:
            True si la configuration a réussi, False sinon
        """
        if auto_optimize is not None:
            self.config["auto_optimize"] = auto_optimize
        if ml_memory_limit is not None:
            self.config["ml_memory_limit"] = ml_memory_limit
        if tx_history_limit is not None:
            self.config["tx_history_limit"] = tx_history_limit
        if connection_pool_size is not None:
            self.config["connection_pool_size"] = connection_pool_size
            
        # Obtenir l'optimiseur matériel (si disponible) et mettre à jour sa configuration
        optimizer = get_hardware_optimizer_compat()
        if optimizer:
            return optimizer.update_config(self.config)
        return True

class PerformanceMonitorCompat:
    """
    Classe de compatibilité pour l'ancienne classe PerformanceMonitor.
    Utilise le nouveau SystemMonitor en arrière-plan.
    """
    
    def __init__(self):
        self._system_monitor = get_system_monitor()
        self._callbacks = []
    
    def start_monitoring(self) -> bool:
        """Lance la surveillance des performances."""
        return self._system_monitor.start()
    
    def stop_monitoring(self) -> bool:
        """Arrête la surveillance des performances."""
        return self._system_monitor.stop()
    
    def register_alert_callback(self, callback: Callable) -> None:
        """
        Enregistre une fonction de rappel pour les alertes de performance.
        
        Args:
            callback: Fonction à appeler lors d'une alerte
        """
        if callback not in self._callbacks:
            self._callbacks.append(callback)
            
            # Adapter le callback au nouveau format
            def wrapper(metric_name, value, threshold):
                callback({
                    "name": metric_name,
                    "value": value,
                    "threshold": threshold,
                    "timestamp": self._system_monitor.get_current_timestamp()
                })
            
            self._system_monitor.subscribe("performance", wrapper)
    
    def track_metric(self, name: str, value: float) -> None:
        """
        Enregistre une métrique personnalisée.
        
        Args:
            name: Nom de la métrique
            value: Valeur de la métrique
        """
        self._system_monitor.track_metric(name, value)
        
        # Vérifier si la métrique dépasse un seuil
        for callback in self._callbacks:
            callback({
                "name": name,
                "value": value,
                "threshold": None,
                "timestamp": self._system_monitor.get_current_timestamp()
            })
    
    def get_metrics_report(self) -> Dict[str, Any]:
        """
        Récupère un rapport des métriques de performance.
        
        Returns:
            Dictionnaire contenant les métriques de performance
        """
        metrics = self._system_monitor.get_performance_metrics()
        
        # Adapter au format attendu par l'ancien API
        result = {
            "system": {
                "cpu": metrics.get("cpu_percent", 0),
                "memory": metrics.get("memory_percent", 0),
                "disk": metrics.get("disk_percent", 0),
                "network": {
                    "sent": metrics.get("network_sent", 0),
                    "received": metrics.get("network_received", 0),
                },
            },
            "application": {
                "response_time": metrics.get("app_response_time", 0),
                "tx_count": metrics.get("tx_count", 0),
                "error_rate": metrics.get("error_rate", 0),
            },
            "blockchain": {
                "block_time": metrics.get("block_time", 0),
                "gas_price": metrics.get("gas_price", 0),
                "confirmation_time": metrics.get("confirmation_time", 0),
            },
            "custom": {},
            "timestamp": metrics.get("timestamp", 0),
        }
        
        # Ajouter les métriques personnalisées
        custom_metrics = self._system_monitor.get_custom_metrics()
        for name, data in custom_metrics.items():
            result["custom"][name] = data.get("value", 0)
            
        return result

class HardwareOptimizerCompat:
    """
    Classe de compatibilité pour l'ancienne classe HardwareOptimizer.
    Utilise le nouveau HardwareOptimizer en arrière-plan via lazy import.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialise l'optimiseur matériel compatible.
        
        Args:
            config: Configuration optionnelle pour l'optimiseur
        """
        self.config = config or {}
        self._hardware_info = None
        self._optimization_status = {
            "status": "not_initialized",
            "applied": [],
            "last_update": 0,
        }
        
        # Stocker en cache les informations matérielles pour éviter les dépendances circulaires
        self._hardware_info = self._generate_hw_info()
        
        logger.info("HardwareOptimizerCompat initialisé")
        
    def _generate_hw_info(self) -> Dict[str, Any]:
        """
        Génère des informations matérielles de base pour éviter les dépendances circulaires.
        Sera remplacé par les vraies infos lorsque le vrai optimiseur sera chargé.
        
        Returns:
            Dictionnaire d'informations matérielles
        """
        import platform
        import os
        
        try:
            # Tenter d'obtenir des informations de base
            import psutil
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                "cpu": {
                    "model": platform.processor() or "Unknown CPU",
                    "cores": os.cpu_count() or 4,
                    "architecture": platform.machine(),
                    "frequency": getattr(psutil.cpu_freq(), "current", 0) if hasattr(psutil, "cpu_freq") else 0,
                },
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                },
                "disk": {
                    "total": disk.total,
                    "free": disk.free,
                },
                "gpu": self._detect_gpu(),
                "os": {
                    "name": platform.system(),
                    "version": platform.version(),
                },
            }
        except ImportError:
            # Version minimale si psutil n'est pas disponible
            return {
                "cpu": {
                    "model": platform.processor() or "Unknown CPU",
                    "cores": os.cpu_count() or 4,
                    "architecture": platform.machine(),
                },
                "memory": {
                    "total": 0,
                    "available": 0,
                },
                "disk": {
                    "total": 0,
                    "free": 0,
                },
                "gpu": self._detect_gpu(),
                "os": {
                    "name": platform.system(),
                    "version": platform.version(),
                },
            }
            
    def _detect_gpu(self) -> Dict[str, Any]:
        """
        Détecte les informations GPU de base.
        
        Returns:
            Dictionnaire d'informations GPU
        """
        gpu_info = {"model": "Unknown", "vram": 0}
        
        try:
            # Essayer de détecter les GPU NVIDIA avec pynvml
            import pynvml
            pynvml.nvmlInit()
            device_count = pynvml.nvmlDeviceGetCount()
            
            if device_count > 0:
                handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                gpu_info["model"] = pynvml.nvmlDeviceGetName(handle)
                gpu_info["vram"] = pynvml.nvmlDeviceGetMemoryInfo(handle).total
                pynvml.nvmlShutdown()
                return gpu_info
        except (ImportError, Exception):
            pass
            
        return gpu_info
    
    @property
    def hardware_info(self) -> Dict[str, Any]:
        """
        Récupère les informations matérielles.
        
        Returns:
            Dictionnaire contenant les informations matérielles
        """
        # Essayer d'obtenir les vraies infos si l'optimiseur est disponible
        try:
            # Import tardif pour éviter les dépendances circulaires
            opt_module = _get_optimization_module()
            if opt_module:
                hw_optimizer = opt_module.get_hardware_optimizer_instance(self.config)
                if hw_optimizer:
                    return hw_optimizer.hardware_info
        except Exception as e:
            logger.warning(f"Impossible d'obtenir les infos hardware: {str(e)}")
            
        # Utiliser les infos en cache si l'optimiseur n'est pas disponible
        return self._hardware_info
    
    def apply_optimizations(self, target: str = "all") -> bool:
        """
        Applique les optimisations matérielles.
        
        Args:
            target: Cible de l'optimisation ('cpu', 'memory', 'disk', 'network', 'gpu', 'all')
            
        Returns:
            True si les optimisations ont été appliquées avec succès, False sinon
        """
        try:
            # Import tardif pour éviter les dépendances circulaires
            opt_module = _get_optimization_module()
            if opt_module:
                # Tenter d'appliquer les optimisations via le nouveau système
                hw_optimizer = opt_module.get_hardware_optimizer_instance(self.config)
                if hw_optimizer:
                    result = hw_optimizer.apply_optimizations(target)
                    
                    # Mettre à jour le statut des optimisations
                    self._optimization_status = {
                        "status": "optimized" if result else "failed",
                        "applied": hw_optimizer.get_applied_optimizations() if hasattr(hw_optimizer, "get_applied_optimizations") else [],
                        "last_update": opt_module.get_current_timestamp() if hasattr(opt_module, "get_current_timestamp") else 0,
                    }
                    
                    return result
        except Exception as e:
            logger.error(f"Erreur lors de l'application des optimisations: {str(e)}")
            self._optimization_status["status"] = "error"
            
        # Optimisations basiques si l'optimiseur n'est pas disponible
        try:
            if target in ("all", "memory"):
                import gc
                gc.collect()
                
            self._optimization_status = {
                "status": "basic_optimized",
                "applied": [f"basic_{target}_optimization"],
                "last_update": 0,
            }
            
            return True
        except Exception:
            return False
    
    def start_monitoring(self) -> bool:
        """
        Démarre la surveillance des performances matérielles.
        
        Returns:
            True si la surveillance a démarré avec succès, False sinon
        """
        try:
            # Import tardif pour éviter les dépendances circulaires
            opt_module = _get_optimization_module()
            if opt_module:
                hw_optimizer = opt_module.get_hardware_optimizer_instance(self.config)
                if hw_optimizer and hasattr(hw_optimizer, "start_monitoring"):
                    return hw_optimizer.start_monitoring()
        except Exception as e:
            logger.error(f"Erreur lors du démarrage de la surveillance: {str(e)}")
            
        return False
    
    def stop_monitoring(self) -> bool:
        """
        Arrête la surveillance des performances matérielles.
        
        Returns:
            True si la surveillance a été arrêtée avec succès, False sinon
        """
        try:
            # Import tardif pour éviter les dépendances circulaires
            opt_module = _get_optimization_module()
            if opt_module:
                hw_optimizer = opt_module.get_hardware_optimizer_instance(self.config)
                if hw_optimizer and hasattr(hw_optimizer, "stop_monitoring"):
                    return hw_optimizer.stop_monitoring()
        except Exception as e:
            logger.error(f"Erreur lors de l'arrêt de la surveillance: {str(e)}")
            
        return False
    
    def get_optimization_status(self) -> Dict[str, Any]:
        """
        Récupère l'état actuel des optimisations.
        
        Returns:
            Dictionnaire contenant l'état des optimisations
        """
        try:
            # Import tardif pour éviter les dépendances circulaires
            opt_module = _get_optimization_module()
            if opt_module:
                hw_optimizer = opt_module.get_hardware_optimizer_instance(self.config)
                if hw_optimizer and hasattr(hw_optimizer, "get_optimization_status"):
                    return hw_optimizer.get_optimization_status()
        except Exception:
            pass
            
        # Utiliser le statut en cache si l'optimiseur n'est pas disponible
        return self._optimization_status
    
    def save_optimization_profile(self, profile_name: str = "default") -> bool:
        """
        Sauvegarde le profil d'optimisation actuel.
        
        Args:
            profile_name: Nom du profil
            
        Returns:
            True si le profil a été sauvegardé avec succès, False sinon
        """
        try:
            # Import tardif pour éviter les dépendances circulaires
            opt_module = _get_optimization_module()
            if opt_module and hasattr(opt_module, "save_current_optimization_profile"):
                return opt_module.save_current_optimization_profile(profile_name)
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde du profil: {str(e)}")
            
        return False
    
    def load_optimization_profile(self, profile_name: str = "default") -> bool:
        """
        Charge un profil d'optimisation.
        
        Args:
            profile_name: Nom du profil
            
        Returns:
            True si le profil a été chargé avec succès, False sinon
        """
        try:
            # Import tardif pour éviter les dépendances circulaires
            opt_module = _get_optimization_module()
            if opt_module and hasattr(opt_module, "apply_optimization_profile"):
                return opt_module.apply_optimization_profile(profile_name)
        except Exception as e:
            logger.error(f"Erreur lors du chargement du profil: {str(e)}")
            
        return False
    
    def get_recommendations(self) -> List[str]:
        """
        Récupère les recommandations d'optimisation matérielle.
        
        Returns:
            Liste des recommandations
        """
        try:
            # Import tardif pour éviter les dépendances circulaires
            opt_module = _get_optimization_module()
            if opt_module:
                hw_optimizer = opt_module.get_hardware_optimizer_instance(self.config)
                if hw_optimizer and hasattr(hw_optimizer, "get_recommendations"):
                    return hw_optimizer.get_recommendations()
                
                # Alternative: utiliser la fonction du module si disponible
                if hasattr(opt_module, "get_hardware_recommendations"):
                    recommendations = opt_module.get_hardware_recommendations()
                    return recommendations.get("recommendations", [])
        except Exception as e:
            logger.warning(f"Impossible d'obtenir les recommandations: {str(e)}")
            
        # Recommandations par défaut
        return [
            "Vérifiez que votre système dispose d'au moins 16 Go de RAM pour des performances optimales",
            "Une carte graphique NVIDIA avec CUDA améliorerait les performances d'analyse",
            "Assurez-vous que votre connexion Internet est stable pour les opérations de trading",
            "Utilisez un SSD pour de meilleures performances d'accès au disque"
        ]

# Fonctions de compatibilité pour récupérer les instances

def get_resource_monitor():
    """
    Récupère l'instance du moniteur de ressources compatible.
    
    Returns:
        Instance de ResourceMonitorCompat
    """
    return ResourceMonitorCompat()

def get_performance_monitor():
    """
    Récupère l'instance du moniteur de performances compatible.
    
    Returns:
        Instance de PerformanceMonitorCompat
    """
    return PerformanceMonitorCompat()

def get_hardware_optimizer_compat(config=None):
    """
    Récupère l'instance de l'optimiseur matériel compatible.
    
    Args:
        config: Configuration optionnelle pour l'optimiseur
        
    Returns:
        Instance de HardwareOptimizerCompat
    """
    # D'abord essayer d'obtenir l'instance via le module d'optimisation
    try:
        opt_module = _get_optimization_module()
        if opt_module and hasattr(opt_module, "get_hardware_optimizer_instance"):
            hw_optimizer = opt_module.get_hardware_optimizer_instance(config)
            if hw_optimizer:
                # Retourner une instance compatible qui délègue au vrai optimiseur
                compat = HardwareOptimizerCompat(config)
                return compat
    except Exception as e:
        logger.debug(f"Utilisation de l'optimiseur de compatibilité: {str(e)}")
    
    # Utiliser l'implémentation de compatibilité
    return HardwareOptimizerCompat(config) 