#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stubs de compatibilité pour GBPBot
=================================

Ce fichier contient des versions simplifiées (stubs) des classes de compatibilité
utilisées dans gbpbot/core/monitoring/compatibility.py pour éviter les importations circulaires.
"""

from typing import Dict, Any, Optional, List, Union


class HardwareOptimizerCompat:
    """
    Stub pour la classe HardwareOptimizerCompat.
    Cette implémentation minimaliste évite les importations circulaires.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialise le stub.
        
        Args:
            config: Configuration optionnelle
        """
        self.config = config or {}
        self.active_optimizations = {
            "cpu": False,
            "gpu": False,
            "memory": False,
            "disk": False,
            "network": False
        }
        self._hw_info = self._generate_hw_info()
    
    def _generate_hw_info(self) -> Dict[str, Any]:
        """
        Génère des informations matérielles basiques.
        
        Returns:
            Dict[str, Any]: Informations matérielles simulées
        """
        return {
            "platform": "Stub Platform",
            "cpu": {
                "model": "Stub CPU",
                "cores_physical": 4,
                "cores_logical": 8,
                "frequency": 3000,
                "is_i5_12400f": False
            },
            "memory": {
                "total": 16 * 1024 * 1024 * 1024,  # 16GB
                "available": 8 * 1024 * 1024 * 1024,  # 8GB
                "percent_used": 50.0
            },
            "disk": {
                "total": 500 * 1024 * 1024 * 1024,  # 500GB
                "free": 250 * 1024 * 1024 * 1024,  # 250GB
                "is_nvme": True,
                "io_speed": 1000
            },
            "gpu": {
                "available": True,
                "model": "Stub GPU",
                "memory": 4 * 1024 * 1024 * 1024,  # 4GB
                "cuda_available": True,
                "is_rtx_3060": False
            },
            "network": {
                "interfaces": 1
            }
        }
    
    def apply_optimizations(self, target: str = "all") -> bool:
        """
        Simule l'application des optimisations.
        
        Args:
            target: Composant à optimiser

        Returns:
            bool: Toujours True
        """
        if target == "all":
            for key in self.active_optimizations:
                self.active_optimizations[key] = True
        elif target in self.active_optimizations:
            self.active_optimizations[target] = True
        
        return True
    
    def get_optimization_status(self) -> Dict[str, Any]:
        """
        Retourne un statut d'optimisation simulé.
        
        Returns:
            Dict[str, Any]: Statut des optimisations
        """
        return {
            "optimizations": self.active_optimizations,
            "hardware_info": self._hw_info,
            "current_metrics": {
                "cpu": 20.0,
                "memory": 50.0,
                "gpu": 10.0,
                "disk_free_percent": 50.0
            }
        }
    
    def get_recommendations(self) -> List[str]:
        """
        Retourne des recommandations d'optimisation simulées.
        
        Returns:
            List[str]: Liste de recommandations
        """
        return [
            "Utilisez le nouveau système d'optimisation (stub)",
            "Cette version est un stub pour éviter les importations circulaires"
        ]
    
    @property
    def hardware_info(self) -> Dict[str, Any]:
        """
        Récupère les informations matérielles simulées.
        
        Returns:
            Dict[str, Any]: Informations matérielles
        """
        return self._hw_info


class ResourceMonitorCompat:
    """
    Stub pour la classe ResourceMonitorCompat.
    Cette implémentation minimaliste évite les importations circulaires.
    """
    
    def __init__(self):
        """Initialise le stub."""
        self._metrics = {
            "cpu_percent": 20.0,
            "memory_percent": 50.0,
            "disk_percent": 40.0,
            "swap_percent": 10.0,
            "process_cpu_percent": 5.0,
            "process_memory_mb": 200.0,
            "net_sent_rate": 100.0,
            "net_recv_rate": 200.0
        }
        self._callbacks = {}
    
    def start_monitoring(self) -> bool:
        """
        Simule le démarrage du monitoring.
        
        Returns:
            bool: Toujours True
        """
        return True
    
    def stop_monitoring(self) -> bool:
        """
        Simule l'arrêt du monitoring.
        
        Returns:
            bool: Toujours True
        """
        return True
    
    def get_current_state(self) -> Dict[str, Any]:
        """
        Récupère l'état courant simulé.
        
        Returns:
            Dict[str, Any]: État courant des ressources
        """
        return {
            "cpu_usage": self._metrics["cpu_percent"],
            "memory_usage": self._metrics["memory_percent"],
            "disk_usage": self._metrics["disk_percent"],
            "is_cpu_high": self._metrics["cpu_percent"] > 80,
            "is_memory_high": self._metrics["memory_percent"] > 80,
            "is_disk_high": self._metrics["disk_percent"] > 80,
            "timestamp": 0,
            "applied_optimizations": []
        }
    
    def update_thresholds(self, cpu=None, memory=None, disk=None, interval=None):
        """
        Simule la mise à jour des seuils.
        
        Args:
            cpu: Seuil CPU
            memory: Seuil mémoire
            disk: Seuil disque
            interval: Intervalle de vérification
        """
        pass
    
    def subscribe(self, event_type: str, callback: callable) -> bool:
        """
        Simule l'abonnement à un événement.
        
        Args:
            event_type: Type d'événement
            callback: Fonction à appeler
            
        Returns:
            bool: Toujours True
        """
        if event_type not in self._callbacks:
            self._callbacks[event_type] = []
        
        self._callbacks[event_type].append(callback)
        return True
    
    def unsubscribe(self, event_type: str, callback: callable) -> bool:
        """
        Simule la désinscription d'un événement.
        
        Args:
            event_type: Type d'événement
            callback: Fonction à supprimer
            
        Returns:
            bool: Toujours True
        """
        return True
    
    def get_metrics_report(self) -> Dict[str, Any]:
        """
        Génère un rapport de métriques simulé.
        
        Returns:
            Dict[str, Any]: Rapport de métriques
        """
        return {
            "system": {
                "cpu": self._metrics["cpu_percent"],
                "memory": self._metrics["memory_percent"],
                "disk": self._metrics["disk_percent"],
                "swap": self._metrics["swap_percent"]
            },
            "process": {
                "cpu": self._metrics["process_cpu_percent"],
                "memory_mb": self._metrics["process_memory_mb"]
            },
            "network": {
                "sent_rate": self._metrics["net_sent_rate"],
                "recv_rate": self._metrics["net_recv_rate"]
            },
            "custom": {}
        }


class PerformanceMonitorCompat:
    """
    Stub pour la classe PerformanceMonitorCompat.
    Cette implémentation minimaliste évite les importations circulaires.
    """
    
    def __init__(self):
        """Initialise le stub."""
        self._metrics = {}
    
    def track_operation(self, operation_name: str, duration_ms: float) -> None:
        """
        Simule le suivi d'une opération.
        
        Args:
            operation_name: Nom de l'opération
            duration_ms: Durée en millisecondes
        """
        if operation_name not in self._metrics:
            self._metrics[operation_name] = {
                "count": 0,
                "total_ms": 0,
                "avg_ms": 0,
                "min_ms": float('inf'),
                "max_ms": 0
            }
        
        m = self._metrics[operation_name]
        m["count"] += 1
        m["total_ms"] += duration_ms
        m["avg_ms"] = m["total_ms"] / m["count"]
        m["min_ms"] = min(m["min_ms"], duration_ms)
        m["max_ms"] = max(m["max_ms"], duration_ms)
    
    def get_operation_stats(self, operation_name: str = None) -> Dict[str, Any]:
        """
        Récupère les statistiques des opérations.
        
        Args:
            operation_name: Nom de l'opération (optionnel)
            
        Returns:
            Dict[str, Any]: Statistiques des opérations
        """
        if operation_name:
            return self._metrics.get(operation_name, {
                "count": 0,
                "total_ms": 0,
                "avg_ms": 0,
                "min_ms": 0,
                "max_ms": 0
            })
        
        return self._metrics
    
    def reset_stats(self, operation_name: str = None) -> None:
        """
        Réinitialise les statistiques.
        
        Args:
            operation_name: Nom de l'opération (optionnel)
        """
        if operation_name:
            if operation_name in self._metrics:
                self._metrics[operation_name] = {
                    "count": 0,
                    "total_ms": 0,
                    "avg_ms": 0,
                    "min_ms": float('inf'),
                    "max_ms": 0
                }
        else:
            self._metrics = {}


# Fonctions utilitaires pour obtenir des instances des stubs

def get_resource_monitor():
    """
    Retourne une instance du stub ResourceMonitorCompat.
    
    Returns:
        ResourceMonitorCompat: Instance du stub
    """
    return ResourceMonitorCompat()

def get_performance_monitor():
    """
    Retourne une instance du stub PerformanceMonitorCompat.
    
    Returns:
        PerformanceMonitorCompat: Instance du stub
    """
    return PerformanceMonitorCompat()

def get_hardware_optimizer(config=None):
    """
    Retourne une instance du stub HardwareOptimizerCompat.
    
    Args:
        config: Configuration optionnelle
        
    Returns:
        HardwareOptimizerCompat: Instance du stub
    """
    return HardwareOptimizerCompat(config) 