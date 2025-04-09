"""
Module d'optimisation du GBPBot
==============================

Ce module fournit des fonctionnalités pour optimiser les performances
du GBPBot sur différentes plateformes et configurations matérielles.

Il inclut:
- Optimisation matérielle (CPU, GPU, mémoire, disque)
- Optimisation des transactions MEV
- Paramétrage automatique pour maximiser la réactivité

Fonctions principales:
- initialize_hardware_optimization: Configure les optimisations matérielles
- apply_optimization_profile: Applique un profil d'optimisation
- get_optimization_status: Obtient l'état actuel des optimisations
"""

import os
import sys
import time
import logging
import importlib
from typing import Dict, Any, Optional, List, Union, Callable, Type

logger = logging.getLogger("gbpbot.core.optimization")

# Variables pour suivre l'état des optimisations
_optimizations_initialized = False
_hardware_optimizer = None
_current_profile = None

# Fonction utilitaire pour obtenir l'horodatage actuel
def get_current_timestamp() -> float:
    """
    Retourne l'horodatage actuel en secondes depuis l'époque.
    
    Returns:
        float: Horodatage actuel
    """
    return time.time()

def initialize_hardware_optimization(config: Optional[Dict[str, Any]] = None, profile: str = "default") -> bool:
    """
    Initialise l'optimiseur matériel en fonction de la configuration du système.
    
    Args:
        config: Configuration optionnelle pour l'optimiseur
        profile: Nom du profil d'optimisation à utiliser (si disponible)
        
    Returns:
        True si l'optimisation a été initialisée avec succès, False sinon
    """
    global _optimizations_initialized, _hardware_optimizer, _current_profile
    
    try:
        # Importer l'optimiseur matériel (import conditionnel pour gérer l'absence de dépendances)
        hw_optimizer = get_hardware_optimizer_instance(config)
        if not hw_optimizer:
            logger.warning("Impossible d'initialiser l'optimiseur matériel. Vérifiez les dépendances.")
            return False
        
        # Appliquer le profil d'optimisation si demandé
        if profile != "none":
            if not apply_optimization_profile(profile):
                # Si le profil spécifié n'existe pas, essayer avec le profil par défaut
                if profile != "default":
                    logger.warning(f"Profil '{profile}' introuvable, utilisation du profil par défaut.")
                    apply_optimization_profile("default")
        
        # Marquer comme initialisé
        _optimizations_initialized = True
        _hardware_optimizer = hw_optimizer
        _current_profile = profile
        
        logger.info(f"Optimisation matérielle initialisée avec profil: {profile}")
        return True
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation de l'optimisation matérielle: {str(e)}")
        return False

def apply_optimization_profile(profile: str) -> bool:
    """
    Applique un profil d'optimisation prédéfini.
    
    Args:
        profile: Nom du profil d'optimisation ('default', 'performance', 'balanced', 'power_saving', 'custom')
        
    Returns:
        True si le profil a été appliqué avec succès, False sinon
    """
    global _current_profile
    
    try:
        # Vérifier si l'optimiseur est disponible
        hw_optimizer = get_hardware_optimizer_instance()
        if not hw_optimizer:
            logger.warning("Optimiseur matériel non disponible pour appliquer le profil.")
            return False
        
        # Charger les paramètres du profil
        profiles_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "profiles")
        profile_file = os.path.join(profiles_dir, f"{profile}.json")
        
        if os.path.exists(profile_file):
            # Charger le profil depuis le fichier
            import json
            with open(profile_file, 'r') as f:
                profile_config = json.load(f)
            
            # Appliquer les optimisations
            hw_optimizer.update_config(profile_config)
            result = hw_optimizer.apply_optimizations()
            
            if result:
                _current_profile = profile
                logger.info(f"Profil d'optimisation '{profile}' appliqué avec succès.")
                return True
            else:
                logger.warning(f"Échec de l'application du profil '{profile}'.")
                return False
        else:
            logger.warning(f"Profil '{profile}' introuvable: {profile_file}")
            return False
    except Exception as e:
        logger.error(f"Erreur lors de l'application du profil '{profile}': {str(e)}")
        return False

def get_optimization_status() -> Dict[str, Any]:
    """
    Récupère l'état actuel des optimisations.
    
    Returns:
        Dict contenant l'état des optimisations
    """
    try:
        # Vérifier si l'optimiseur est disponible
        hw_optimizer = get_hardware_optimizer_instance()
        if not hw_optimizer:
            return {
                "status": "not_available",
                "initialized": _optimizations_initialized,
                "current_profile": _current_profile,
                "timestamp": get_current_timestamp()
            }
        
        # Récupérer le statut de l'optimiseur
        optimizer_status = hw_optimizer.get_optimization_status() if hasattr(hw_optimizer, "get_optimization_status") else {}
        
        # Construire le statut complet
        status = {
            "status": optimizer_status.get("status", "unknown"),
            "initialized": _optimizations_initialized,
            "current_profile": _current_profile,
            "applied_optimizations": optimizer_status.get("applied", []),
            "hardware_info": hw_optimizer.hardware_info if hasattr(hw_optimizer, "hardware_info") else {},
            "timestamp": get_current_timestamp()
        }
        
        return status
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du statut d'optimisation: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": get_current_timestamp()
        }

def save_current_optimization_profile(profile_name: str = "custom") -> bool:
    """
    Sauvegarde la configuration actuelle en tant que profil d'optimisation.
    
    Args:
        profile_name: Nom du profil à sauvegarder
        
    Returns:
        True si le profil a été sauvegardé avec succès, False sinon
    """
    try:
        # Vérifier si l'optimiseur est disponible
        hw_optimizer = get_hardware_optimizer_instance()
        if not hw_optimizer:
            logger.warning("Optimiseur matériel non disponible pour sauvegarder le profil.")
            return False
        
        # Récupérer la configuration actuelle
        if not hasattr(hw_optimizer, "get_config"):
            logger.warning("L'optimiseur ne prend pas en charge la récupération de configuration.")
            return False
        
        config = hw_optimizer.get_config()
        
        # Créer le répertoire des profils s'il n'existe pas
        profiles_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "profiles")
        os.makedirs(profiles_dir, exist_ok=True)
        
        # Sauvegarder le profil
        profile_file = os.path.join(profiles_dir, f"{profile_name}.json")
        import json
        with open(profile_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"Profil d'optimisation '{profile_name}' sauvegardé avec succès.")
        return True
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde du profil '{profile_name}': {str(e)}")
        return False

def get_hardware_recommendations() -> Dict[str, Any]:
    """
    Génère des recommandations d'optimisation matérielle basées sur la configuration actuelle.
    
    Returns:
        Dict contenant des recommandations pour l'optimisation du matériel
    """
    try:
        # Vérifier si l'optimiseur est disponible
        hw_optimizer = get_hardware_optimizer_instance()
        if not hw_optimizer:
            return {
                "status": "not_available",
                "recommendations": [
                    "Installer les dépendances requises pour l'optimisation matérielle."
                ]
            }
        
        # Récupérer les recommandations de l'optimiseur
        if hasattr(hw_optimizer, "get_recommendations"):
            recommendations = hw_optimizer.get_recommendations()
            return {
                "status": "success",
                "recommendations": recommendations
            }
        else:
            # Générer des recommandations de base si la fonction n'est pas disponible
            hw_info = hw_optimizer.hardware_info if hasattr(hw_optimizer, "hardware_info") else {}
            
            recommendations = []
            
            # Recommandations CPU
            cpu_info = hw_info.get("cpu", {})
            cpu_cores = cpu_info.get("cores", 0)
            if cpu_cores < 4:
                recommendations.append("Votre CPU dispose de peu de cœurs. Limitez le nombre de stratégies simultanées.")
            elif cpu_cores < 8:
                recommendations.append("Pour de meilleures performances, envisagez de limiter le traitement en arrière-plan.")
            
            # Recommandations mémoire
            memory_info = hw_info.get("memory", {})
            memory_total = memory_info.get("total", 0)
            memory_gb = memory_total / (1024 * 1024 * 1024) if memory_total > 0 else 0
            if memory_gb < 8:
                recommendations.append("Votre système dispose de peu de RAM. Les performances peuvent être limitées.")
            elif memory_gb < 16:
                recommendations.append("16 Go de RAM ou plus sont recommandés pour des performances optimales.")
            
            # Recommandations GPU
            gpu_info = hw_info.get("gpu", {})
            gpu_model = gpu_info.get("model", "Unknown")
            if "RTX" not in gpu_model and "GTX" not in gpu_model:
                recommendations.append("Une carte GPU NVIDIA RTX ou GTX améliorerait les performances d'analyse.")
            
            # Recommandations générales
            recommendations.append("Utilisez un SSD pour de meilleures performances d'accès au disque.")
            recommendations.append("Assurez-vous que votre connexion Internet est stable pour les opérations de trading.")
            
            return {
                "status": "basic",
                "recommendations": recommendations
            }
    except Exception as e:
        logger.error(f"Erreur lors de la génération des recommandations: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "recommendations": [
                "Une erreur s'est produite lors de la génération des recommandations."
            ]
        }

def shutdown_optimization():
    """
    Arrête proprement le système d'optimisation.
    À appeler avant de quitter l'application.
    """
    global _optimizations_initialized, _hardware_optimizer, _current_profile
    
    try:
        # Vérifier si l'optimiseur est disponible
        if _hardware_optimizer:
            # Arrêter le monitoring si actif
            if hasattr(_hardware_optimizer, "stop_monitoring"):
                _hardware_optimizer.stop_monitoring()
            
            # Nettoyer les ressources
            if hasattr(_hardware_optimizer, "cleanup"):
                _hardware_optimizer.cleanup()
            
            # Réinitialiser les variables globales
            _hardware_optimizer = None
            _optimizations_initialized = False
            _current_profile = None
            
            logger.info("Système d'optimisation arrêté proprement.")
    except Exception as e:
        logger.error(f"Erreur lors de l'arrêt du système d'optimisation: {str(e)}")

# Lazy import pour éviter les problèmes d'import circulaire
def get_hardware_optimizer_instance(config=None):
    """
    Récupère une instance de l'optimiseur matériel.
    Utilise un lazy import pour éviter les problèmes d'import circulaire.
    
    Args:
        config: Configuration optionnelle pour l'optimiseur
        
    Returns:
        Instance de HardwareOptimizer ou None si non disponible
    """
    global _hardware_optimizer
    
    # Si une instance existe déjà, la retourner
    if _hardware_optimizer is not None:
        if config and hasattr(_hardware_optimizer, "update_config"):
            _hardware_optimizer.update_config(config)
        return _hardware_optimizer
    
    try:
        # Essayer d'importer dynamiquement l'optimiseur matériel
        hw_optimizer_module = None
        
        try:
            # Essayer d'importer directement
            from .hardware_optimizer import HardwareOptimizer
            hw_optimizer_class = HardwareOptimizer
        except ImportError:
            # Essayer l'import dynamique
            try:
                spec = importlib.util.find_spec(".hardware_optimizer", package="gbpbot.core.optimization")
                if spec:
                    hw_optimizer_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(hw_optimizer_module)
                    hw_optimizer_class = getattr(hw_optimizer_module, "HardwareOptimizer")
                else:
                    logger.warning("Module hardware_optimizer non trouvé.")
                    return None
            except Exception as e:
                logger.warning(f"Erreur lors de l'import dynamique: {str(e)}")
                return None
        
        # Créer une instance de l'optimiseur
        _hardware_optimizer = hw_optimizer_class(config)
        return _hardware_optimizer
    
    except Exception as e:
        logger.warning(f"Impossible de créer l'optimiseur matériel: {str(e)}")
        return None

# Exportation des fonctions et classes publiques
__all__ = [
    'initialize_hardware_optimization',
    'apply_optimization_profile',
    'get_optimization_status',
    'save_current_optimization_profile',
    'get_hardware_recommendations',
    'shutdown_optimization',
    'get_hardware_optimizer_instance',
    'get_current_timestamp'
]

"""
Package d'optimisation unifié pour GBPBot
========================================

Ce package fournit un système unifié pour l'optimisation des performances
et des ressources dans GBPBot, remplaçant les implémentations disparates
précédentes par une architecture cohérente et extensible.
"""

from .base_optimizer import (
    BaseOptimizer, OptimizationManager, get_optimization_manager,
    OptimizationException, OptimizationResult, OptimizationConfig
)
from .hardware_optimizer import HardwareOptimizer, get_hardware_optimizer
from gbpbot.core.monitoring.compatibility import HardwareOptimizerCompat, get_hardware_optimizer_compat

__all__ = [
    'BaseOptimizer',
    'OptimizationManager',
    'get_optimization_manager',
    'OptimizationException',
    'OptimizationResult',
    'OptimizationConfig',
    'HardwareOptimizer',
    'get_hardware_optimizer',
    # Classes de compatibilité
    'HardwareOptimizerCompat',
    'get_hardware_optimizer_compat',
]

# Initialisation de l'optimiseur hardware
_hardware_optimizer = None

def get_hardware_optimizer_instance(config=None):
    """
    Fonction de compatibilité pour maintenir l'interface existante.
    Utilise la nouvelle implémentation HardwareOptimizer.
    """
    global _hardware_optimizer
    if _hardware_optimizer is None:
        _hardware_optimizer = get_hardware_optimizer(config)
    return _hardware_optimizer 