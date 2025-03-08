#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module de logging avancé pour GBPBot
===================================

Ce module fournit une configuration de logging avancée pour GBPBot,
avec rotation des fichiers de logs, formatage enrichi, et intégration
de la gestion d'erreurs.
"""

import os
import sys
import time
import json
import traceback
import platform
import inspect
from pathlib import Path
from functools import wraps
from datetime import datetime
from typing import Any, Dict, Optional, Callable, Union, List, Tuple

try:
    from loguru import logger
except ImportError:
    # Si loguru n'est pas installé, on utilise le logger standard
    import logging
    logger = logging.getLogger("gbpbot")
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s:%(funcName)s:%(lineno)d - %(message)s"
    ))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class LoggingConfig:
    """Configuration centralisée pour le logging dans GBPBot."""
    
    DEFAULT_LOG_PATH = "logs"
    DEFAULT_LOG_LEVEL = "INFO"
    DEFAULT_ROTATION = "10 MB"
    DEFAULT_RETENTION = "7 days"
    DEFAULT_COMPRESSION = "zip"
    DEFAULT_FORMAT = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )
    
    def __init__(
        self,
        log_path: Optional[str] = None,
        log_level: str = DEFAULT_LOG_LEVEL,
        rotation: str = DEFAULT_ROTATION,
        retention: str = DEFAULT_RETENTION,
        compression: str = DEFAULT_COMPRESSION,
        format_string: str = DEFAULT_FORMAT,
        catch_exceptions: bool = True
    ):
        """
        Initialise la configuration de logging.
        
        Args:
            log_path: Chemin vers le dossier de logs
            log_level: Niveau de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            rotation: Taille max d'un fichier de log avant rotation ("10 MB")
            retention: Durée de conservation des logs ("7 days")
            compression: Format de compression ("zip")
            format_string: Format des logs
            catch_exceptions: Intercepte les exceptions non gérées
        """
        self.log_path = log_path or self.DEFAULT_LOG_PATH
        self.log_level = log_level
        self.rotation = rotation
        self.retention = retention
        self.compression = compression
        self.format_string = format_string
        self.catch_exceptions = catch_exceptions
        
        # Créer le dossier de logs s'il n'existe pas
        os.makedirs(self.log_path, exist_ok=True)

    def setup(self):
        """Configure le système de logging."""
        # Si nous utilisons le logger standard, on ne peut pas utiliser loguru
        if not hasattr(logger, "configure"):
            return
        
        # Supprimer les handlers existants
        logger.remove()
        
        # Ajouter un handler pour la sortie console
        logger.add(
            sys.stderr,
            format=self.format_string,
            level=self.log_level,
            colorize=True
        )
        
        # Ajouter un handler pour les fichiers de logs généraux
        logger.add(
            os.path.join(self.log_path, "gbpbot_{time}.log"),
            rotation=self.rotation,
            retention=self.retention,
            compression=self.compression,
            format=self.format_string,
            level=self.log_level
        )
        
        # Ajouter un handler séparé pour les erreurs
        logger.add(
            os.path.join(self.log_path, "errors_{time}.log"),
            rotation=self.rotation,
            retention=self.retention,
            compression=self.compression,
            format=self.format_string,
            level="ERROR"
        )
        
        # Intercepter les exceptions non gérées
        if self.catch_exceptions:
            self._setup_exception_handling()
    
    def _setup_exception_handling(self):
        """Configure l'interception des exceptions non gérées."""
        def handle_exception(exc_type, exc_value, exc_traceback):
            """Gestionnaire d'exception personnalisé."""
            if issubclass(exc_type, KeyboardInterrupt):
                # Laisser le KeyboardInterrupt se propager normalement
                sys.__excepthook__(exc_type, exc_value, exc_traceback)
                return
            
            # Journaliser l'exception
            logger.opt(exception=(exc_type, exc_value, exc_traceback)).error(
                "Exception non gérée: {}", exc_value
            )
        
        # Remplacer le gestionnaire d'exception par défaut
        sys.excepthook = handle_exception


class ErrorTracker:
    """
    Suit et gère les erreurs dans GBPBot.
    Cette classe conserve un historique des erreurs et fournit des recommandations.
    """
    
    def __init__(self, max_errors: int = 100):
        """
        Initialise le tracker d'erreurs.
        
        Args:
            max_errors: Nombre maximal d'erreurs à conserver en mémoire
        """
        self.max_errors = max_errors
        self.errors = []
        self.error_counts = {}
        self.last_error_time = None
    
    def record_error(
        self,
        error: Exception,
        module: str = None,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Enregistre une erreur dans l'historique.
        
        Args:
            error: L'exception à enregistrer
            module: Le module où l'erreur s'est produite
            context: Contexte supplémentaire (variables, état, etc.)
        
        Returns:
            Dict[str, Any]: Informations sur l'erreur
        """
        # Obtenir des informations sur la stack trace
        frame = inspect.currentframe().f_back
        frame_info = inspect.getframeinfo(frame)
        
        # Obtenir le module si non fourni
        if module is None:
            module = frame_info.filename
        
        # Créer un enregistrement d'erreur
        error_type = type(error).__name__
        error_key = f"{error_type}:{str(error)}"
        error_info = {
            "type": error_type,
            "message": str(error),
            "module": module,
            "file": frame_info.filename,
            "line": frame_info.lineno,
            "function": frame_info.function,
            "time": datetime.now().isoformat(),
            "context": context or {},
            "traceback": traceback.format_exc()
        }
        
        # Mettre à jour les statistiques
        if error_key in self.error_counts:
            self.error_counts[error_key] += 1
        else:
            self.error_counts[error_key] = 1
        
        # Ajouter à l'historique des erreurs
        self.errors.append(error_info)
        
        # Limiter la taille de l'historique
        if len(self.errors) > self.max_errors:
            self.errors.pop(0)
        
        # Mettre à jour le timestamp de la dernière erreur
        self.last_error_time = time.time()
        
        # Journaliser l'erreur
        logger.error(
            "{} dans {}: {} à {}:{}",
            error_type, module, str(error),
            frame_info.filename, frame_info.lineno
        )
        
        return error_info
    
    def get_recommendations(self, error_info: Dict[str, Any]) -> List[str]:
        """
        Génère des recommandations basées sur l'erreur.
        
        Args:
            error_info: Informations sur l'erreur
        
        Returns:
            List[str]: Recommandations pour résoudre l'erreur
        """
        error_type = error_info["type"]
        recommendations = []
        
        # Recommandations générales basées sur le type d'erreur
        if error_type == "ConnectionError":
            recommendations.append("Vérifiez votre connexion internet")
            recommendations.append("Vérifiez que les URLs des RPC sont correctes dans votre fichier .env")
            recommendations.append("Essayez un autre fournisseur RPC")
        
        elif error_type == "TimeoutError":
            recommendations.append("Le serveur RPC ne répond pas, essayez de réduire la fréquence des requêtes")
            recommendations.append("Essayez un autre fournisseur RPC qui soit plus rapide")
        
        elif error_type == "JSONDecodeError":
            recommendations.append("La réponse reçue n'est pas au format JSON valide")
            recommendations.append("Vérifiez la compatibilité avec le fournisseur RPC")
        
        elif error_type == "KeyError" or error_type == "AttributeError":
            recommendations.append("Une clé ou un attribut manquant a été détecté")
            recommendations.append("Vérifiez les formats de données attendus par les fonctions")
        
        elif error_type == "ImportError" or error_type == "ModuleNotFoundError":
            recommendations.append("Exécutez `pip install -r requirements.txt` pour installer les dépendances manquantes")
            recommendations.append("Vérifiez que l'environnement virtuel est activé")
        
        # Recommandation spécifique à la blockchain
        if "core.blockchain" in error_info.get("module", ""):
            recommendations.append("Vérifiez que les clés privées et mnémoniques sont correctement configurés")
            recommendations.append("Assurez-vous d'avoir suffisamment de fonds pour les transactions")
        
        # Fréquence de l'erreur
        error_key = f"{error_type}:{error_info['message']}"
        count = self.error_counts.get(error_key, 0)
        if count > 5:
            recommendations.append(f"Cette erreur s'est produite {count} fois, envisagez un redémarrage du bot")
        if count > 20:
            recommendations.append("Erreur récurrente! Consultez la documentation ou signalez ce problème")
        
        # Recommandation générique
        if not recommendations:
            recommendations.append("Vérifiez les logs pour plus de détails sur cette erreur")
            recommendations.append("Si le problème persiste, consultez la documentation ou contactez le support")
        
        return recommendations
    
    def get_error_summary(self) -> Dict[str, Any]:
        """
        Génère un résumé des erreurs récentes.
        
        Returns:
            Dict[str, Any]: Résumé des erreurs
        """
        most_frequent = sorted(
            self.error_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        return {
            "total_errors": sum(self.error_counts.values()),
            "unique_errors": len(self.error_counts),
            "most_frequent": most_frequent,
            "recent_errors": self.errors[-5:] if self.errors else []
        }


def retry_on_exception(
    max_attempts: int = 3,
    exceptions: Union[Exception, Tuple[Exception, ...]] = Exception,
    interval: float = 1.0,
    backoff_factor: float = 2.0,
    logger_func: Optional[Callable] = None
):
    """
    Décorateur pour réessayer une fonction en cas d'exception.
    
    Args:
        max_attempts: Nombre maximal de tentatives
        exceptions: Exception(s) à intercepter pour réessayer
        interval: Intervalle initial entre les tentatives (en secondes)
        backoff_factor: Facteur multiplicatif pour l'intervalle entre les tentatives
        logger_func: Fonction de logging à utiliser (par défaut: logger.warning)
    
    Returns:
        Callable: Décorateur
    """
    if logger_func is None:
        logger_func = logger.warning
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_attempt = 0
            current_interval = interval
            last_exception = None
            
            while current_attempt < max_attempts:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    current_attempt += 1
                    last_exception = e
                    
                    if current_attempt < max_attempts:
                        logger_func(
                            f"L'appel à {func.__name__} a échoué (tentative {current_attempt}/{max_attempts}): {e}. "
                            f"Nouvelle tentative dans {current_interval:.2f}s"
                        )
                        time.sleep(current_interval)
                        current_interval *= backoff_factor
                    else:
                        logger_func(
                            f"L'appel à {func.__name__} a échoué définitivement après {max_attempts} tentative(s): {e}"
                        )
            
            # Toutes les tentatives ont échoué, relancer la dernière exception
            raise last_exception
        
        return wrapper
    
    return decorator


def log_execution_time(func=None, *, name=None, level="DEBUG"):
    """
    Décorateur pour mesurer et journaliser le temps d'exécution d'une fonction.
    
    Args:
        func: Fonction à décorer
        name: Nom personnalisé pour le log (par défaut: nom de la fonction)
        level: Niveau de log (DEBUG, INFO, WARNING, ERROR)
    
    Returns:
        Callable: Fonction décorée
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            func_name = name or func.__name__
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                # Choisir la méthode de logging selon le niveau
                log_method = getattr(logger, level.lower())
                log_method(f"{func_name} exécuté en {execution_time:.4f}s")
                
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(
                    f"{func_name} a échoué après {execution_time:.4f}s: {str(e)}"
                )
                raise
        
        return wrapper
    
    # Permettre l'utilisation avec ou sans arguments
    if func is None:
        return decorator
    return decorator(func)


def get_system_info() -> Dict[str, Any]:
    """
    Récupère des informations sur le système pour le diagnostic.
    
    Returns:
        Dict[str, Any]: Informations système
    """
    import psutil
    
    # Informations système de base
    system_info = {
        "platform": platform.system(),
        "platform_version": platform.version(),
        "python_version": platform.python_version(),
        "processor": platform.processor(),
        "hostname": platform.node(),
        "time": datetime.now().isoformat(),
    }
    
    # Informations CPU
    system_info["cpu_count_physical"] = psutil.cpu_count(logical=False)
    system_info["cpu_count_logical"] = psutil.cpu_count(logical=True)
    system_info["cpu_percent"] = psutil.cpu_percent(interval=0.1)
    
    # Informations mémoire
    memory = psutil.virtual_memory()
    system_info["memory_info"] = {
        "total": memory.total,
        "available": memory.available,
        "percent": memory.percent,
        "used": memory.used,
        "free": memory.free
    }
    
    # Informations disque
    disk = psutil.disk_usage('/')
    system_info["disk_info"] = {
        "total": disk.total,
        "used": disk.used,
        "free": disk.free,
        "percent": disk.percent
    }
    
    # Informations réseau
    net_io = psutil.net_io_counters()
    system_info["network_info"] = {
        "bytes_sent": net_io.bytes_sent,
        "bytes_recv": net_io.bytes_recv,
        "packets_sent": net_io.packets_sent,
        "packets_recv": net_io.packets_recv
    }
    
    # Détection CUDA
    system_info["cuda_available"] = False
    system_info["cuda_device_count"] = 0
    system_info["cuda_device_name"] = "Non disponible"
    
    try:
        import torch
        system_info["cuda_available"] = torch.cuda.is_available()
        if system_info["cuda_available"]:
            system_info["cuda_device_count"] = torch.cuda.device_count()
            system_info["cuda_device_name"] = torch.cuda.get_device_name(0)
    except (ImportError, Exception):
        pass
    
    return system_info


def configure_logging():
    """Configure le système de logging avec les paramètres par défaut."""
    config = LoggingConfig()
    config.setup()
    return config


# Initialiser le tracker d'erreurs global
error_tracker = ErrorTracker()

# Si ce script est exécuté directement, configurer le logging
if __name__ == "__main__":
    # Configurer le logging
    config = configure_logging()
    
    # Afficher un message de test
    logger.info("Module de logging avancé initialisé avec succès")
    
    # Tester le tracking d'erreurs
    try:
        1 / 0
    except Exception as e:
        error_info = error_tracker.record_error(e)
        recommendations = error_tracker.get_recommendations(error_info)
        
        logger.info(f"Recommandations pour l'erreur: {recommendations}")
    
    # Afficher les informations système
    try:
        system_info = get_system_info()
        logger.info(f"Informations système: CPU: {system_info['cpu_percent']}%, "
                   f"RAM: {system_info['memory_info']['percent']}%, "
                   f"Disque: {system_info['disk_info']['percent']}%")
    except Exception as e:
        logger.error(f"Impossible de récupérer les informations système: {e}")
    
    logger.info("Test du module de logging terminé") 