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
from typing import Dict, Any, Optional, List, Union

# Classe temporaire pour éviter l'importation cyclique
class HardwareOptimizerCompat:
    @staticmethod
    def get_instance():
        return None

def get_hardware_optimizer_compat():
    return None

# Classe temporaire pour éviter l'importation cyclique
class HardwareOptimizerCompat:
    @staticmethod
    def get_instance():
        return None

def get_hardware_optimizer_compat():
    return None

from gbpbot.core.monitoring import SystemMonitor, get_system_monitor
# Temporairement commenté pour éviter l'importation cyclique
# # Temporairement commenté pour éviter l'importation cyclique
# from gbpbot.core.optimization import (
    get_hardware_optimizer, # # HardwareOptimizer,
    OptimizationResult, OptimizationConfig
)

# Configuration du logging
logger = logging.getLogger("gbpbot.compatibility")

# Classes de compatibilité pour le monitoring

class ResourceMonitorCompat:
    """
    Classe de compatibilité pour l'ancienne classe ResourceMonitor.
    Utilise le nouveau SystemMonitor en arrière-plan.
    """
    
    def __init__(self):
        """Initialise l'instance de compatibilité."""
        self._monitor = get_system_monitor()
        
        # Mapping des anciennes métriques vers les nouvelles
        self._metric_mapping = {
            "cpu_usage": "cpu_percent",
            "memory_usage": "memory_percent",
            "disk_usage": "disk_percent",
            "is_cpu_high": "cpu_high",
            "is_memory_high": "memory_high",
            "is_disk_high": "disk_high"
        }
        
        # Mapping des anciens événements vers les nouveaux
        self._event_mapping = {
            "cpu_high": "cpu_percent",
            "memory_high": "memory_percent",
            "disk_high": "disk_percent",
            "resources_normal": "system_normal",
            "optimization_applied": "optimization_applied"
        }
    
    def start(self):
        """Démarre la surveillance des ressources."""
        return self._monitor.start()
    
    def stop(self):
        """Arrête la surveillance des ressources."""
        return self._monitor.stop()
    
    def _check_resources(self):
        """
        Méthode de compatibilité pour vérifier les ressources.
        Utilise directement collect_metrics() du nouveau moniteur.
        """
        self._monitor.collect_metrics()
    
    def _apply_system_optimizations(self):
        """
        Méthode de compatibilité pour appliquer les optimisations système.
        Utilise optimize_system() du nouveau moniteur.
        """
        return self._monitor.optimize_system()
    
    def subscribe(self, event_type: str, callback: callable) -> bool:
        """
        S'abonne à un événement.
        
        Args:
            event_type: Type d'événement (ancien format)
            callback: Fonction à appeler lors de l'événement
            
        Returns:
            bool: True si l'abonnement a réussi, False sinon
        """
        # Convertir l'ancien type d'événement vers le nouveau
        new_event_type = self._event_mapping.get(event_type, event_type)
        
        # Créer un wrapper pour adapter le format des paramètres
        def callback_wrapper(metric_name, value, threshold):
            # Convertir en format attendu par l'ancien callback
            state = {m: self._monitor.get_metric(m) for m in self._monitor.get_all_metrics()}
            return callback(state)
        
        # Enregistrer le callback
        return self._monitor.register_callback(new_event_type, callback_wrapper)
    
    def unsubscribe(self, event_type: str, callback: callable) -> bool:
        """
        Se désabonne d'un événement.
        
        Args:
            event_type: Type d'événement (ancien format)
            callback: Fonction à supprimer
            
        Returns:
            bool: True si la désinscription a réussi, False sinon
        """
        # Trop compliqué de désabonner des wrappers, on laisse tel quel pour l'instant
        logger.warning("La désinscription des callbacks n'est pas totalement prise en charge en mode compatibilité")
        return True
    
    def get_current_state(self) -> Dict[str, Any]:
        """
        Récupère l'état actuel des ressources.
        
        Returns:
            Dict[str, Any]: État actuel des ressources (ancien format)
        """
        # Obtenir l'état du nouveau moniteur
        metrics = self._monitor.get_all_metrics()
        
        # Convertir vers l'ancien format
        state = {}
        for old_name, new_name in self._metric_mapping.items():
            state[old_name] = metrics.get(new_name, 0)
        
        # Ajouter les champs manquants
        state["timestamp"] = self._monitor.last_check_time.timestamp() if self._monitor.last_check_time else 0
        state["applied_optimizations"] = []
        
        return state
    
    def update_thresholds(self, cpu=None, memory=None, disk=None, interval=None):
        """
        Met à jour les seuils d'alerte.
        
        Args:
            cpu: Seuil CPU (%)
            memory: Seuil mémoire (%)
            disk: Seuil disque (%)
            interval: Intervalle de vérification
        """
        if interval is not None:
            self._monitor.check_interval = interval
        
        self._monitor.set_all_thresholds(cpu, memory, disk)
    
    def get_optimization_values(self) -> Dict[str, Any]:
        """
        Récupère les valeurs d'optimisation.
        
        Returns:
            Dict[str, Any]: Valeurs d'optimisation
        """
        # Simuler l'ancien format
        return {
            "auto_optimize": True,
            "ml_memory_limit": 4096,
            "tx_history_limit": 10000,
            "connection_pool_size": 20
        }
    
    def set_optimization_values(self, auto_optimize=None, ml_memory_limit=None,
                          tx_history_limit=None, connection_pool_size=None) -> bool:
        """
        Définit les valeurs d'optimisation.
        
        Args:
            auto_optimize: Activer l'optimisation automatique
            ml_memory_limit: Limite mémoire pour le ML (MB)
            tx_history_limit: Limite d'historique de transactions
            connection_pool_size: Taille du pool de connexions
            
        Returns:
            bool: True si les valeurs ont été définies, False sinon
        """
        # Ces valeurs seront ignorées, car elles sont gérées différemment dans le nouveau système
        logger.info("Paramètres d'optimisation définis en mode compatibilité (certains peuvent être ignorés)")
        return True


# Classes de compatibilité pour l'optimisation

class PerformanceMonitorCompat:
    """
    Classe de compatibilité pour l'ancienne classe PerformanceMonitor.
    Utilise le nouveau SystemMonitor en arrière-plan.
    """
    
    def __init__(self):
        """Initialise l'instance de compatibilité."""
        self._monitor = get_system_monitor()
    
    def start_monitoring(self) -> bool:
        """Démarre le monitoring des performances."""
        return self._monitor.start()
    
    def stop_monitoring(self) -> bool:
        """Arrête le monitoring des performances."""
        return self._monitor.stop()
    
    def register_alert_callback(self, callback: callable) -> None:
        """
        Enregistre un callback pour les alertes.
        
        Args:
            callback: Fonction à appeler lors d'une alerte
        """
        # Enregistrer pour toutes les métriques importantes
        for metric in ["cpu_percent", "memory_percent", "disk_percent", "swap_percent"]:
            self._monitor.register_callback(metric, callback)
    
    def track_metric(self, name: str, value: float) -> None:
        """
        Ajoute une métrique personnalisée.
        
        Args:
            name: Nom de la métrique
            value: Valeur de la métrique
        """
        self._monitor.update_metric(name, value)
    
    def get_metrics_report(self) -> Dict[str, Any]:
        """
        Génère un rapport de métriques.
        
        Returns:
            Dict[str, Any]: Rapport de métriques
        """
        metrics = self._monitor.get_all_metrics()
        
        # Formater en ancien style
        report = {
            "system": {
                "cpu": metrics.get("cpu_percent", 0),
                "memory": metrics.get("memory_percent", 0),
                "disk": metrics.get("disk_percent", 0),
                "swap": metrics.get("swap_percent", 0)
            },
            "process": {
                "cpu": metrics.get("process_cpu_percent", 0),
                "memory_mb": metrics.get("process_memory_mb", 0)
            },
            "network": {
                "sent_rate": metrics.get("net_sent_rate", 0),
                "recv_rate": metrics.get("net_recv_rate", 0)
            },
            "custom": {}
        }
        
        # Ajouter les métriques personnalisées
        for name, value in metrics.items():
            if name.startswith("custom_"):
                report["custom"][name.replace("custom_", "")] = value
        
        return report


class HardwareOptimizerCompat:
    """
    Classe de compatibilité pour l'ancienne classe HardwareOptimizer.
    Utilise le nouveau HardwareOptimizer en arrière-plan.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialise l'instance de compatibilité.
        
        Args:
            config: Configuration optionnelle
        """
        self._optimizer = get_hardware_optimizer(config)
        
        # Simuler les anciens attributs
        self.active_optimizations = {
            "cpu": False,
            "gpu": False,
            "memory": False,
            "disk": False,
            "network": False
        }
        
        # Simuler les informations matérielles
        self._hw_info = self._generate_hw_info()
    
    def _generate_hw_info(self) -> Dict[str, Any]:
        """
        Génère une simulation de l'ancien format d'informations matérielles.
        
        Returns:
            Dict[str, Any]: Informations matérielles au format legacy
        """
        real_info = self._optimizer._hardware_info
        
        # Simuler l'ancien format
        hw_info = {
            "platform": real_info.get("platform", "") + " " + real_info.get("platform_version", ""),
            "cpu": {
                "model": real_info.get("processor", ""),
                "cores_physical": real_info.get("cpu_count_physical", 1),
                "cores_logical": real_info.get("cpu_count_logical", 2),
                "frequency": 0,
                "is_i5_12400f": "i5-12400F" in real_info.get("processor", "")
            },
            "memory": {
                "total": real_info.get("memory_info", {}).get("total", 0),
                "available": real_info.get("memory_info", {}).get("available", 0),
                "percent_used": real_info.get("memory_info", {}).get("percent", 0)
            },
            "disk": {
                "total": real_info.get("disk_info", {}).get("total", 0),
                "free": real_info.get("disk_info", {}).get("free", 0),
                "is_nvme": False,
                "io_speed": None
            },
            "gpu": {
                "available": real_info.get("cuda_available", False),
                "model": real_info.get("cuda_device_name", None),
                "memory": 0,
                "cuda_available": real_info.get("cuda_available", False),
                "is_rtx_3060": "RTX 3060" in real_info.get("cuda_device_name", "")
            },
            "network": {
                "interfaces": 1
            },
            "summary": f"Système: {real_info.get('platform', '')}, CPU: {real_info.get('processor', '')}"
        }
        
        return hw_info
    
    @property
    def hardware_info(self) -> Dict[str, Any]:
        """
        Récupère les informations matérielles au format legacy.
        
        Returns:
            Dict[str, Any]: Informations matérielles
        """
        return self._hw_info
    
    def apply_optimizations(self, target: str = "all") -> bool:
        """
        Applique les optimisations pour le matériel cible.
        
        Args:
            target: Composant à optimiser ("cpu", "gpu", "memory", "disk", "network" ou "all")
            
        Returns:
            bool: True si les optimisations ont été appliquées avec succès, False sinon
        """
        # Configurer le niveau d'optimisation selon la cible
        config = {}
        
        if target == "all" or target == "cpu":
            config["cpu_optimization_level"] = 2
            
        if target == "all" or target == "gpu":
            config["gpu_optimization_level"] = 2
            
        if target == "all" or target == "memory":
            config["memory_optimization_level"] = 2
            
        if target == "all" or target == "disk":
            config["io_optimization_level"] = 2
            
        if target == "all" or target == "network":
            config["io_optimization_level"] = 1
        
        # Appliquer les optimisations
        self._optimizer.set_config(config)
        result = self._optimizer.run()
        
        # Mettre à jour les flags de compatibilité
        success = result.get("status") == "success"
        if success:
            if target == "all":
                for k in self.active_optimizations:
                    self.active_optimizations[k] = True
            else:
                self.active_optimizations[target] = True
        
        return success
    
    def start_monitoring(self) -> bool:
        """
        Méthode de compatibilité pour démarrer le monitoring.
        Ne fait rien car le monitoring est géré séparément.
        
        Returns:
            bool: Toujours True
        """
        logger.info("La méthode start_monitoring() est obsolète et n'a plus d'effet")
        return True
    
    def stop_monitoring(self) -> bool:
        """
        Méthode de compatibilité pour arrêter le monitoring.
        Ne fait rien car le monitoring est géré séparément.
        
        Returns:
            bool: Toujours True
        """
        logger.info("La méthode stop_monitoring() est obsolète et n'a plus d'effet")
        return True
    
    def get_optimization_status(self) -> Dict[str, Any]:
        """
        Retourne l'état actuel des optimisations au format legacy.
        
        Returns:
            Dict[str, Any]: État des optimisations
        """
        # Récupérer le statut du nouvel optimiseur
        status = self._optimizer.get_status()
        
        # Convertir vers l'ancien format
        return {
            "optimizations": self.active_optimizations,
            "hardware_info": self.hardware_info,
            "current_metrics": {
                "cpu": get_system_monitor().get_metric("cpu_percent") or 0,
                "memory": get_system_monitor().get_metric("memory_percent") or 0,
                "gpu": 0,
                "disk_free_percent": 100 - (get_system_monitor().get_metric("disk_percent") or 0)
            },
            "average_metrics": {},
            "optimization_params": {}
        }
    
    def save_optimization_profile(self, profile_name: str = "default") -> bool:
        """
        Méthode de compatibilité pour sauvegarder un profil d'optimisation.
        Ne fait rien car les profils sont gérés différemment.
        
        Args:
            profile_name: Nom du profil
            
        Returns:
            bool: Toujours True
        """
        logger.info(f"Sauvegarde de profil d'optimisation '{profile_name}' simulée en mode compatibilité")
        return True
    
    def load_optimization_profile(self, profile_name: str = "default") -> bool:
        """
        Méthode de compatibilité pour charger un profil d'optimisation.
        Ne fait rien car les profils sont gérés différemment.
        
        Args:
            profile_name: Nom du profil
            
        Returns:
            bool: Toujours True
        """
        logger.info(f"Chargement de profil d'optimisation '{profile_name}' simulé en mode compatibilité")
        return True
    
    def get_recommendations(self) -> List[str]:
        """
        Méthode de compatibilité pour générer des recommandations.
        
        Returns:
            List[str]: Liste de recommandations
        """
        # Générer quelques recommandations statiques
        recs = [
            "Utiliser le nouveau système d'optimisation pour des performances améliorées",
            "Consulter la documentation pour profiter des nouvelles fonctionnalités"
        ]
        
        # Ajouter des recommandations spécifiques au matériel
        hw = self.hardware_info
        
        if hw["cpu"]["cores_logical"] < 8:
            recs.append("Réduire le nombre de stratégies simultanées pour éviter la surcharge CPU")
        
        if not hw["gpu"]["available"]:
            recs.append("Exécuter les modèles d'IA en mode CPU (performances réduites)")
        
        return recs

# Fonctions de compatibilité pour maintenir l'interface publique

def get_resource_monitor():
    """
    Fonction de compatibilité pour obtenir une instance de ResourceMonitor.
    
    Returns:
        ResourceMonitorCompat: Instance de compatibilité
    """
    return ResourceMonitorCompat()

def get_performance_monitor():
    """
    Fonction de compatibilité pour obtenir une instance de PerformanceMonitor.
    
    Returns:
        PerformanceMonitorCompat: Instance de compatibilité
    """
    return PerformanceMonitorCompat()

def get_hardware_optimizer_compat(config=None):
    """
    Fonction de compatibilité pour obtenir une instance de HardwareOptimizer.
    
    Args:
        config: Configuration optionnelle
        
    Returns:
        HardwareOptimizerCompat: Instance de compatibilité
    """
    return HardwareOptimizerCompat(config) 