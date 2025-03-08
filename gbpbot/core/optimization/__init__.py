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
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("gbpbot.core.optimization")

# Variables pour suivre l'état des optimisations
_optimizations_initialized = False
_hardware_optimizer = None
_current_profile = None

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
        try:
            from .hardware_optimizer import get_hardware_optimizer
            hardware_optimizer_available = True
        except ImportError:
            hardware_optimizer_available = False
            logger.warning("Module d'optimisation matérielle non disponible. Certaines fonctionnalités seront limitées.")
            
        if not hardware_optimizer_available:
            return False
            
        # Initialiser l'optimiseur
        _hardware_optimizer = get_hardware_optimizer(config)
        
        # Essayer de charger le profil spécifié s'il existe
        profile_loaded = False
        if profile:
            try:
                profile_loaded = _hardware_optimizer.load_optimization_profile(profile)
                if profile_loaded:
                    _current_profile = profile
                    logger.info(f"Profil d'optimisation '{profile}' chargé")
            except Exception as e:
                logger.warning(f"Impossible de charger le profil d'optimisation '{profile}': {str(e)}")
        
        # Appliquer les optimisations de base si aucun profil n'a été chargé
        if not profile_loaded:
            _hardware_optimizer.apply_optimizations()
            _current_profile = "auto"
            logger.info("Optimisations matérielles auto-détectées appliquées")
        
        # Démarrer la surveillance des performances
        _hardware_optimizer.start_monitoring()
        
        _optimizations_initialized = True
        return True
    
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation des optimisations matérielles: {str(e)}")
        return False

def apply_optimization_profile(profile: str) -> bool:
    """
    Applique un profil d'optimisation spécifique.
    
    Args:
        profile: Nom du profil à appliquer
        
    Returns:
        True si le profil a été appliqué avec succès, False sinon
    """
    global _current_profile
    
    if not _optimizations_initialized or not _hardware_optimizer:
        logger.warning("L'optimisation matérielle n'est pas initialisée")
        return False
    
    try:
        success = _hardware_optimizer.load_optimization_profile(profile)
        if success:
            _current_profile = profile
            logger.info(f"Profil d'optimisation '{profile}' appliqué")
            return True
        else:
            logger.warning(f"Échec de l'application du profil '{profile}'")
            return False
    
    except Exception as e:
        logger.error(f"Erreur lors de l'application du profil d'optimisation: {str(e)}")
        return False

def get_optimization_status() -> Dict[str, Any]:
    """
    Obtient l'état actuel de l'optimisation matérielle.
    
    Returns:
        Dictionnaire contenant l'état des optimisations et les métriques de performance
    """
    if not _optimizations_initialized or not _hardware_optimizer:
        return {
            "initialized": False,
            "profile": None,
            "hardware_detected": False,
            "optimizations": {},
            "metrics": {}
        }
    
    try:
        status = _hardware_optimizer.get_optimization_status()
        
        # Ajouter des informations supplémentaires
        status["initialized"] = _optimizations_initialized
        status["profile"] = _current_profile
        
        return status
    
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de l'état des optimisations: {str(e)}")
        return {
            "initialized": True,
            "profile": _current_profile,
            "error": str(e)
        }

def save_current_optimization_profile(profile_name: str = "custom") -> bool:
    """
    Sauvegarde le profil d'optimisation actuel.
    
    Args:
        profile_name: Nom sous lequel sauvegarder le profil
        
    Returns:
        True si le profil a été sauvegardé avec succès, False sinon
    """
    if not _optimizations_initialized or not _hardware_optimizer:
        logger.warning("L'optimisation matérielle n'est pas initialisée")
        return False
    
    try:
        success = _hardware_optimizer.save_optimization_profile(profile_name)
        if success:
            logger.info(f"Profil d'optimisation sauvegardé sous '{profile_name}'")
            return True
        else:
            logger.warning(f"Échec de la sauvegarde du profil '{profile_name}'")
            return False
    
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde du profil d'optimisation: {str(e)}")
        return False

def get_hardware_recommendations() -> Dict[str, Any]:
    """
    Obtient des recommandations pour optimiser les performances sur le matériel actuel.
    
    Returns:
        Dictionnaire contenant des recommandations d'optimisation
    """
    if not _optimizations_initialized or not _hardware_optimizer:
        return {
            "recommendations": ["Initialiser d'abord l'optimisation matérielle"],
            "hardware_info": {}
        }
    
    try:
        recommendations = _hardware_optimizer.get_recommendations()
        hardware_info = _hardware_optimizer.hardware_info
        
        return {
            "recommendations": recommendations,
            "hardware_info": hardware_info
        }
    
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des recommandations: {str(e)}")
        return {
            "recommendations": [f"Erreur: {str(e)}"],
            "hardware_info": {}
        }

def shutdown_optimization():
    """
    Arrête proprement les services d'optimisation (surveillance, etc.)
    """
    global _optimizations_initialized, _hardware_optimizer
    
    if _optimizations_initialized and _hardware_optimizer:
        try:
            # Arrêter la surveillance des performances
            _hardware_optimizer.stop_monitoring()
            
            # Sauvegarder l'état actuel si nécessaire
            if _current_profile and _current_profile != "auto":
                _hardware_optimizer.save_optimization_profile(_current_profile)
            
            logger.info("Services d'optimisation arrêtés proprement")
        
        except Exception as e:
            logger.error(f"Erreur lors de l'arrêt des services d'optimisation: {str(e)}")
        
        finally:
            _optimizations_initialized = False
            _hardware_optimizer = None

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