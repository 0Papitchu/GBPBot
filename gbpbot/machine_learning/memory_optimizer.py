"""
Module d'Optimisation Mémoire pour GBPBot
=========================================

Ce module contient des fonctions pour optimiser l'utilisation de la mémoire
des modèles de machine learning dans GBPBot, permettant une exécution
efficace sur des systèmes avec des contraintes de mémoire.
"""

import os
import time
import gc
import psutil
import logging
import threading
import numpy as np
from typing import Dict, Optional, Any, Callable, List, Union
import sys

# Configuration du logging
logger = logging.getLogger("gbpbot.machine_learning.memory_optimizer")

# Importer le gestionnaire de ressources
try:
    from gbpbot import resource_monitor
except ImportError:
    resource_monitor = None
    logger.warning("Module resource_monitor non disponible, optimisation automatique désactivée")

# Variables globales pour le suivi de l'utilisation mémoire
memory_monitor_active = False
memory_monitor_thread = None
memory_usage_callback = None
current_memory_usage = 0
memory_usage_limit = 0
ml_models_cache = {}  # Cache pour les modèles ML
ml_models_last_used = {}  # Timestamp de dernière utilisation des modèles
ml_models_size_estimates = {}  # Estimation de la taille des modèles en mémoire

def init_memory_monitoring(config: Dict, callback: Optional[Callable] = None) -> bool:
    """
    Initialise la surveillance de la mémoire pour le ML
    
    Args:
        config: Configuration du bot
        callback: Fonction à appeler quand l'utilisation de la mémoire dépasse la limite
        
    Returns:
        bool: True si initialisé avec succès, False sinon
    """
    global memory_monitor_active, memory_monitor_thread, memory_usage_callback, memory_usage_limit
    
    try:
        # Récupérer la configuration
        memory_monitoring = config.get("MEMORY_MONITORING", "true").lower() == "true"
        max_memory_percent = float(config.get("MAX_MEMORY_USAGE_PERCENT", 80))
        
        # Définir la limite mémoire explicite en MB si disponible, sinon basée sur pourcentage
        if "ML_MAX_MEMORY_USAGE" in config and config["ML_MAX_MEMORY_USAGE"]:
            max_memory_mb = int(config.get("ML_MAX_MEMORY_USAGE", 4096))  # 4GB par défaut
            total_memory = psutil.virtual_memory().total / (1024 * 1024)  # En MB
            memory_usage_limit = min(max_memory_mb, total_memory * max_memory_percent / 100)
        else:
            # Basé sur le pourcentage de la mémoire système
            total_memory = psutil.virtual_memory().total / (1024 * 1024)  # En MB
            memory_usage_limit = total_memory * max_memory_percent / 100
        
        # Accepter le callback pour notification
        memory_usage_callback = callback
        
        # Démarrer le thread de surveillance si demandé et pas déjà actif
        if memory_monitoring and not memory_monitor_active:
            memory_monitor_active = True
            memory_monitor_thread = threading.Thread(target=_monitor_memory_usage, daemon=True)
            memory_monitor_thread.start()
            
            # S'inscrire à l'optimiseur de ressources si disponible
            if resource_monitor:
                resource_monitor.register_handler(_handle_resource_optimization)
            
            logger.info(f"Surveillance mémoire ML activée (limite: {memory_usage_limit:.2f} MB, {max_memory_percent}%)")
            return True
        elif not memory_monitoring:
            logger.info("Surveillance mémoire ML désactivée par configuration")
            return False
        else:
            logger.info("Surveillance mémoire ML déjà active")
            return True
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation de la surveillance mémoire: {str(e)}")
        return False

def _handle_resource_optimization(state: Dict[str, Any]) -> None:
    """
    Gère les recommandations d'optimisation des ressources
    
    Args:
        state: État actuel des ressources et recommandations
    """
    global memory_usage_limit
    
    try:
        # Vérifier si l'état contient des recommandations pour le ML
        if "ml_memory_limit" in state:
            new_limit = state["ml_memory_limit"]
            old_limit = memory_usage_limit
            
            # Mettre à jour la limite
            memory_usage_limit = new_limit
            
            # Logger le changement
            logger.info(f"Limite mémoire ML mise à jour: {old_limit:.2f} MB -> {new_limit:.2f} MB")
            
            # Vérifier si nous dépassons déjà la nouvelle limite
            current = get_current_memory_usage()
            if current > new_limit:
                logger.warning(f"Utilisation mémoire ML actuelle ({current:.2f} MB) dépasse la nouvelle limite ({new_limit:.2f} MB)")
                _clean_memory(aggressive=True)
        
        # Si nous sommes proches de la limite système, nettoyer aussi
        if state.get("memory_pressure", False):
            logger.warning("Système sous pression mémoire, nettoyage agressif du cache ML")
            _clean_memory(aggressive=True)
    except Exception as e:
        logger.error(f"Erreur lors du traitement de l'optimisation des ressources pour le ML: {str(e)}")

def stop_memory_monitoring() -> bool:
    """
    Arrête la surveillance de la mémoire
    
    Returns:
        bool: True si arrêté avec succès, False sinon
    """
    global memory_monitor_active, memory_monitor_thread
    
    try:
        # Arrêter le thread de surveillance s'il est actif
        if memory_monitor_active:
            memory_monitor_active = False
            
            # Attendre la fin du thread (avec timeout)
            if memory_monitor_thread and memory_monitor_thread.is_alive():
                memory_monitor_thread.join(timeout=2.0)
            
            # Réinitialiser
            memory_monitor_thread = None
            
            # Se désinscrire de l'optimiseur de ressources
            if resource_monitor:
                resource_monitor.unregister_handler(_handle_resource_optimization)
            
            logger.info("Surveillance mémoire ML désactivée")
            return True
        else:
            logger.info("Surveillance mémoire ML déjà inactive")
            return False
    except Exception as e:
        logger.error(f"Erreur lors de l'arrêt de la surveillance mémoire: {str(e)}")
        return False

def get_current_memory_usage() -> float:
    """
    Obtient l'utilisation mémoire actuelle du processus en MB
    
    Returns:
        float: Mémoire utilisée en MB
    """
    try:
        # Obtenir les infos mémoire du processus
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        return memory_info.rss / (1024 * 1024)  # Convertir en MB
    except Exception:
        return 0

def _monitor_memory_usage() -> None:
    """Thread de surveillance de l'utilisation mémoire"""
    global current_memory_usage, memory_monitor_active
    
    logger.info("Démarrage du thread de surveillance mémoire ML")
    
    while memory_monitor_active:
        try:
            # Mesurer l'utilisation mémoire actuelle
            current_memory_usage = get_current_memory_usage()
            
            # Vérifier si nous dépassons la limite
            if memory_usage_limit > 0 and current_memory_usage > memory_usage_limit:
                logger.warning(f"Utilisation mémoire ML excessive: {current_memory_usage:.2f} MB / {memory_usage_limit:.2f} MB")
                
                # Nettoyer la mémoire
                _clean_memory()
                
                # Notifier via callback si disponible
                if memory_usage_callback:
                    memory_usage_callback({
                        "type": "memory_exceeded",
                        "current": current_memory_usage,
                        "limit": memory_usage_limit,
                        "percent": (current_memory_usage / memory_usage_limit) * 100
                    })
            
            # Si l'utilisation est proche de la limite (>90%), nettoyer préventivement
            elif memory_usage_limit > 0 and current_memory_usage > memory_usage_limit * 0.9:
                logger.info(f"Utilisation mémoire ML proche de la limite: {current_memory_usage:.2f} MB / {memory_usage_limit:.2f} MB (>90%)")
                _clean_memory(aggressive=False)
            
            # Attendre avant la prochaine vérification
            time.sleep(15)  # Vérifier toutes les 15 secondes
        except Exception as e:
            logger.error(f"Erreur dans la surveillance mémoire ML: {str(e)}")
            time.sleep(60)  # Attendre plus longtemps en cas d'erreur

def _clean_memory(aggressive: bool = False) -> None:
    """
    Nettoie la mémoire utilisée par les modèles de ML
    
    Args:
        aggressive: Si True, nettoyage plus agressif (vide le cache)
    """
    global ml_models_cache, ml_models_last_used
    
    try:
        # Forcer collection garbage
        gc.collect()
        
        # Logger avant nettoyage
        memory_before = get_current_memory_usage()
        logger.info(f"Nettoyage mémoire ML initié (utilisation actuelle: {memory_before:.2f} MB)")
        
        # En mode agressif, vider le cache des modèles peu utilisés
        if aggressive and ml_models_cache:
            # Trier les modèles par date de dernière utilisation
            current_time = time.time()
            models_by_age = sorted(
                [(model_name, current_time - ml_models_last_used.get(model_name, 0)) 
                for model_name in ml_models_cache],
                key=lambda x: x[1]
            )
            
            # Supprimer les modèles les plus anciens (50% du cache)
            models_to_remove = models_by_age[len(models_by_age)//2:]
            for model_name, age in models_to_remove:
                if model_name in ml_models_cache:
                    logger.info(f"Suppression du modèle {model_name} du cache (non utilisé depuis {age:.1f}s)")
                    del ml_models_cache[model_name]
                    if model_name in ml_models_last_used:
                        del ml_models_last_used[model_name]
        
        # Réduire les tableaux NumPy en mémoire
        for obj_id, obj in list(gc.get_objects()):
            try:
                if isinstance(obj, np.ndarray) and obj.size > 1_000_000:  # Arrays >1M éléments
                    del obj
            except:
                pass
        
        # Mesurer l'effet du nettoyage
        gc.collect()  # Deuxième collecte après suppression d'objets
        memory_after = get_current_memory_usage()
        logger.info(f"Nettoyage mémoire ML terminé: {memory_before:.2f} MB -> {memory_after:.2f} MB (économie: {memory_before - memory_after:.2f} MB)")
    except Exception as e:
        logger.error(f"Erreur lors du nettoyage mémoire ML: {str(e)}")

def optimize_model_memory(model: Any, config: Dict) -> Any:
    """
    Optimise la consommation mémoire d'un modèle ML
    
    Args:
        model: Modèle à optimiser
        config: Configuration
        
    Returns:
        Any: Modèle optimisé
    """
    if model is None:
        return None
    
    try:
        # Estimer la taille du modèle
        model_size = _estimate_model_size(model)
        logger.debug(f"Taille estimée du modèle avant optimisation: {model_size:.2f} MB")
        
        # Récupérer le seuil de mémoire maximum autorisé par modèle
        max_model_size_mb = int(config.get("ML_MAX_MODEL_SIZE", 512))
        
        # Si le modèle est trop grand, appliquer des optimisations
        if model_size > max_model_size_mb:
            logger.warning(f"Modèle trop volumineux ({model_size:.2f} MB > {max_model_size_mb} MB), application d'optimisations")
            
            # Optimisations spécifiques selon le type de modèle
            model = _apply_model_specific_optimizations(model, config)
            
            # Nouvelle estimation
            new_size = _estimate_model_size(model)
            logger.info(f"Taille du modèle après optimisation: {model_size:.2f} MB -> {new_size:.2f} MB")
        
        return model
    except Exception as e:
        logger.error(f"Erreur lors de l'optimisation mémoire du modèle: {str(e)}")
        return model

def cache_ml_model(model_name: str, model: Any) -> None:
    """
    Met en cache un modèle ML avec suivi de son utilisation
    
    Args:
        model_name: Nom du modèle
        model: Modèle à mettre en cache
    """
    global ml_models_cache, ml_models_last_used, ml_models_size_estimates
    
    try:
        # Estimer la taille du modèle
        model_size = _estimate_model_size(model)
        
        # Mettre à jour le cache
        ml_models_cache[model_name] = model
        ml_models_last_used[model_name] = time.time()
        ml_models_size_estimates[model_name] = model_size
        
        logger.debug(f"Modèle {model_name} mis en cache (taille: {model_size:.2f} MB)")
        
        # Vérifier la taille totale du cache
        total_cache_size = sum(ml_models_size_estimates.values())
        logger.debug(f"Taille totale du cache ML: {total_cache_size:.2f} MB ({len(ml_models_cache)} modèles)")
        
        # Si le cache devient trop grand, nettoyer
        if total_cache_size > memory_usage_limit * 0.7:  # 70% de la limite
            logger.warning(f"Cache ML trop volumineux ({total_cache_size:.2f} MB), nettoyage")
            _clean_memory(aggressive=True)
    except Exception as e:
        logger.error(f"Erreur lors de la mise en cache du modèle {model_name}: {str(e)}")

def get_cached_model(model_name: str) -> Optional[Any]:
    """
    Récupère un modèle du cache et met à jour son timestamp
    
    Args:
        model_name: Nom du modèle à récupérer
        
    Returns:
        Optional[Any]: Le modèle s'il est en cache, None sinon
    """
    global ml_models_cache, ml_models_last_used
    
    if model_name in ml_models_cache:
        # Mettre à jour le timestamp
        ml_models_last_used[model_name] = time.time()
        return ml_models_cache[model_name]
    return None

def _estimate_model_size(model: Any) -> float:
    """
    Estime la taille en mémoire d'un modèle ML
    
    Args:
        model: Modèle à analyser
        
    Returns:
        float: Taille estimée en MB
    """
    try:
        # Méthode 1: Récupérer la taille en utilisant sys.getsizeof()
        size = sys.getsizeof(model) / (1024 * 1024)  # Convertir en MB
        
        # Si c'est très petit, c'est probablement une sous-estimation
        if size < 0.1:
            # Essayer d'estimer via les attributs (pour scikit-learn par exemple)
            if hasattr(model, 'get_params'):
                # Pour les modèles scikit-learn
                params = model.get_params()
                for param_name, param_value in params.items():
                    if isinstance(param_value, np.ndarray):
                        size += param_value.nbytes / (1024 * 1024)
        
        return size
    except Exception:
        # En cas d'erreur, renvoyer une estimation par défaut
        return 10.0  # 10 MB par défaut

def _apply_model_specific_optimizations(model: Any, config: Dict) -> Any:
    """
    Applique des optimisations spécifiques selon le type de modèle
    
    Args:
        model: Modèle à optimiser
        config: Configuration
        
    Returns:
        Any: Modèle optimisé
    """
    try:
        # Optimisations pour les modèles scikit-learn
        from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
        
        if isinstance(model, (RandomForestClassifier, RandomForestRegressor)):
            # Réduire le nombre d'arbres si trop grand
            if hasattr(model, 'n_estimators') and model.n_estimators > 50:
                new_n_estimators = min(model.n_estimators, 50)
                logger.info(f"Réduction du nombre d'arbres: {model.n_estimators} -> {new_n_estimators}")
                model.n_estimators = new_n_estimators
        
        return model
    except (ImportError, Exception) as e:
        logger.warning(f"Impossible d'appliquer les optimisations spécifiques: {str(e)}")
        return model

def setup_gpu_acceleration(config: Dict) -> bool:
    """
    Configure l'accélération GPU pour le ML si disponible
    
    Args:
        config: Configuration du bot
        
    Returns:
        bool: True si l'accélération GPU est activée
    """
    try:
        # Vérifier si l'accélération GPU est demandée
        gpu_acceleration = config.get("ML_GPU_ACCELERATION", "auto").lower()
        
        # Si désactivé explicitement, sortir
        if gpu_acceleration == "false" or gpu_acceleration == "off":
            logger.info("Accélération GPU désactivée par configuration")
            return False
        
        # Tenter de détecter les GPU CUDA
        try:
            import torch
            cuda_available = torch.cuda.is_available()
            
            if cuda_available:
                device_count = torch.cuda.device_count()
                device_names = [torch.cuda.get_device_name(i) for i in range(device_count)]
                
                logger.info(f"GPU CUDA détecté: {device_count} dispositif(s) - {', '.join(device_names)}")
                
                # Limiter l'utilisation mémoire GPU
                if "ML_MAX_GPU_MEMORY_MB" in config:
                    max_gpu_memory = int(config.get("ML_MAX_GPU_MEMORY_MB", 2048))  # 2GB par défaut
                    for i in range(device_count):
                        # Limiter la mémoire pour PyTorch
                        torch.cuda.set_per_process_memory_fraction(
                            min(1.0, max_gpu_memory / (torch.cuda.get_device_properties(i).total_memory / 1024 / 1024))
                        )
                    logger.info(f"Utilisation mémoire GPU limitée à {max_gpu_memory} MB")
                
                return True
            else:
                logger.info("Aucun GPU CUDA détecté")
        except ImportError:
            logger.info("PyTorch non disponible, vérification des GPU TensorFlow")
            
            # Tenter avec TensorFlow si PyTorch n'est pas disponible
            try:
                import tensorflow as tf
                gpus = tf.config.list_physical_devices('GPU')
                
                if gpus:
                    logger.info(f"GPU TensorFlow détecté: {len(gpus)} dispositif(s)")
                    
                    # Limiter l'utilisation mémoire GPU
                    if "ML_MAX_GPU_MEMORY_MB" in config:
                        max_gpu_memory = int(config.get("ML_MAX_GPU_MEMORY_MB", 2048))  # 2GB par défaut
                        for gpu in gpus:
                            tf.config.experimental.set_virtual_device_configuration(
                                gpu,
                                [tf.config.experimental.VirtualDeviceConfiguration(memory_limit=max_gpu_memory)]
                            )
                        logger.info(f"Utilisation mémoire GPU limitée à {max_gpu_memory} MB par GPU")
                    
                    return True
                else:
                    logger.info("Aucun GPU TensorFlow détecté")
            except ImportError:
                logger.info("TensorFlow non disponible")
        
        # Si nous arrivons ici, pas de GPU trouvé ou utilisable
        if gpu_acceleration == "true" or gpu_acceleration == "on":
            logger.warning("Accélération GPU demandée mais aucun GPU disponible")
        
        return False
    except Exception as e:
        logger.error(f"Erreur lors de la configuration de l'accélération GPU: {str(e)}")
        return False

def optimize_batch_size(config: Dict) -> int:
    """
    Détermine la taille de batch optimale pour l'entraînement selon la mémoire disponible
    
    Args:
        config: Configuration
        
    Returns:
        int: Taille de batch recommandée
    """
    try:
        # Récupérer la taille de batch de la configuration
        default_batch_size = int(config.get("ML_BATCH_SIZE", 32))
        
        # Si une valeur explicite est fournie et qu'elle n'est pas "auto", l'utiliser
        if config.get("ML_BATCH_SIZE") and config.get("ML_BATCH_SIZE").lower() != "auto":
            return default_batch_size
        
        # Calculer dynamiquement la taille de batch selon la mémoire disponible
        available_memory = psutil.virtual_memory().available / (1024 * 1024)  # En MB
        
        # Règle empirique:
        # - Très faible mémoire (<1GB): batch size = 8
        # - Faible mémoire (1-2GB): batch size = 16
        # - Mémoire moyenne (2-4GB): batch size = 32
        # - Mémoire élevée (4-8GB): batch size = 64
        # - Mémoire très élevée (>8GB): batch size = 128-256
        
        if available_memory < 1024:
            batch_size = 8
        elif available_memory < 2048:
            batch_size = 16
        elif available_memory < 4096:
            batch_size = 32
        elif available_memory < 8192:
            batch_size = 64
        else:
            batch_size = min(256, int(available_memory / 64))  # 1 de batch size par 64MB disponibles, max 256
        
        logger.info(f"Taille de batch ML optimisée: {batch_size} (mémoire disponible: {available_memory:.2f} MB)")
        return batch_size
    except Exception as e:
        logger.error(f"Erreur lors du calcul de la taille de batch optimale: {str(e)}")
        return 32  # Valeur par défaut sécurisée 