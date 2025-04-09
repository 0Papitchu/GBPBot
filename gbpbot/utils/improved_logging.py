#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module de journalisation amélioré pour GBPBot
============================================

Ce module fournit des fonctionnalités avancées de journalisation pour le GBPBot,
avec gestion des fichiers de log, rotation, filtrage, et formats personnalisés.
Il est conçu pour faciliter le diagnostic des problèmes et le suivi des opérations.

Caractéristiques:
- Logs séparés par module et niveau
- Rotation automatique des fichiers de log
- Formats de log personnalisés pour différents contextes
- Capture et journalisation des exceptions non gérées
- Métriques d'erreurs et statistiques
"""

import os
import sys
import time
import json
import traceback
import platform
import inspect
from functools import wraps
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Union, Callable, Tuple

# Configuration par défaut
DEFAULT_LOG_FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_LOG_DIR = "logs"

# Essayer d'importer colorama pour les logs colorés dans la console
try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False

# Essayer d'importer loguru pour une journalisation avancée
try:
    from loguru import logger as loguru_logger
    LOGURU_AVAILABLE = True
except ImportError:
    LOGURU_AVAILABLE = False
    import logging


class LogManager:
    """
    Gestionnaire de journalisation avancé pour GBPBot.
    
    Cette classe fournit une configuration centralisée pour tous les loggers
    de l'application, avec des options avancées comme la rotation des fichiers,
    les formats personnalisés par niveau, et l'intégration avec loguru si disponible.
    """
    
    def __init__(
        self,
        log_dir: Union[str, Path] = DEFAULT_LOG_DIR,
        log_level: str = DEFAULT_LOG_LEVEL,
        use_loguru: bool = LOGURU_AVAILABLE,
        rotation: str = "10 MB",
        retention: str = "1 week",
        console_format: Optional[str] = None,
        file_format: Optional[str] = None,
        catch_exceptions: bool = True
    ):
        """
        Initialise le gestionnaire de logs.
        
        Args:
            log_dir: Répertoire où stocker les fichiers de log
            log_level: Niveau de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            use_loguru: Utiliser loguru si disponible
            rotation: Taille maximale d'un fichier avant rotation
            retention: Durée de conservation des fichiers de log
            console_format: Format personnalisé pour la console
            file_format: Format personnalisé pour les fichiers
            catch_exceptions: Intercepter les exceptions non gérées
        """
        self.log_dir = Path(log_dir)
        self.log_level = log_level.upper()
        self.use_loguru = use_loguru and LOGURU_AVAILABLE
        self.rotation = rotation
        self.retention = retention
        self.console_format = console_format
        self.file_format = file_format
        self.catch_exceptions = catch_exceptions
        
        # Créer le répertoire de logs s'il n'existe pas
        self.log_dir.mkdir(exist_ok=True, parents=True)
        
        # Loggers enregistrés
        self.loggers = {}
        
        # Statistiques d'erreurs
        self.error_stats = {
            "total_errors": 0,
            "by_module": {},
            "by_type": {},
            "last_error_time": None,
            "recent_errors": []
        }
        
        # Configurer la journalisation
        self._configure()
    
    def _configure(self):
        """Configure le système de journalisation"""
        if self.use_loguru:
            self._configure_loguru()
        else:
            self._configure_standard_logging()
        
        # Intercepter les exceptions non gérées si demandé
        if self.catch_exceptions:
            self._setup_exception_handler()
    
    def _configure_loguru(self):
        """Configure loguru pour la journalisation"""
        # Supprimer les handlers existants
        loguru_logger.remove()
        
        # Format pour la console
        console_format = self.console_format or (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan> | "
            "<level>{message}</level>"
        )
        
        # Format pour les fichiers
        file_format = self.file_format or (
            "{time:YYYY-MM-DD HH:mm:ss} | "
            "{level: <8} | "
            "{name} | "
            "{file}:{line} | "
            "{message}"
        )
        
        # Ajouter le handler pour la console
        loguru_logger.add(
            sys.stderr,
            format=console_format,
            level=self.log_level,
            colorize=True
        )
        
        # Ajouter le handler pour le fichier de log général
        loguru_logger.add(
            self.log_dir / "gbpbot_{time}.log",
            format=file_format,
            rotation=self.rotation,
            retention=self.retention,
            level=self.log_level
        )
        
        # Ajouter le handler spécifique pour les erreurs
        loguru_logger.add(
            self.log_dir / "errors_{time}.log",
            format=file_format,
            rotation=self.rotation,
            retention=self.retention,
            level="ERROR"
        )
        
        # Définir la méthode get_logger
        self.get_logger = self._get_loguru_logger
    
    def _configure_standard_logging(self):
        """Configure le logging standard"""
        # Configurer le formateur de base
        console_format = self.console_format or DEFAULT_LOG_FORMAT
        file_format = self.file_format or DEFAULT_LOG_FORMAT
        
        # Niveau de log
        level = getattr(logging, self.log_level)
        
        # Configurer le handler de console
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_formatter = logging.Formatter(console_format)
        console_handler.setFormatter(console_formatter)
        
        # Configurer le handler de fichier général
        general_file_handler = self._create_file_handler(
            "gbpbot.log",
            level,
            file_format
        )
        
        # Configurer le handler de fichier d'erreurs
        error_file_handler = self._create_file_handler(
            "errors.log",
            logging.ERROR,
            file_format
        )
        
        # Configurer le logger racine
        root_logger = logging.getLogger()
        root_logger.setLevel(level)
        
        # Supprimer les handlers existants
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Ajouter les nouveaux handlers
        root_logger.addHandler(console_handler)
        root_logger.addHandler(general_file_handler)
        root_logger.addHandler(error_file_handler)
        
        # Définir la méthode get_logger
        self.get_logger = self._get_standard_logger
    
    def _create_file_handler(self, filename, level, format_str):
        """Crée un handler de fichier avec rotation"""
        try:
            from logging.handlers import RotatingFileHandler
            
            handler = RotatingFileHandler(
                self.log_dir / filename,
                maxBytes=10*1024*1024,  # 10 MB
                backupCount=5
            )
        except ImportError:
            # Fallback si RotatingFileHandler n'est pas disponible
            handler = logging.FileHandler(self.log_dir / filename)
        
        handler.setLevel(level)
        formatter = logging.Formatter(format_str)
        handler.setFormatter(formatter)
        
        return handler
    
    def _get_loguru_logger(self, name):
        """Retourne un logger loguru"""
        return loguru_logger.bind(name=name)
    
    def _get_standard_logger(self, name):
        """Retourne un logger standard"""
        if name not in self.loggers:
            logger = logging.getLogger(name)
            if COLORAMA_AVAILABLE:
                # Ajouter un handler coloré pour la console
                self._add_color_handler(logger)
            
            self.loggers[name] = logger
        
        return self.loggers[name]
    
    def _add_color_handler(self, logger):
        """Ajoute un handler coloré à un logger standard"""
        
        class ColoredFormatter(logging.Formatter):
            """Formateur avec des couleurs pour la console"""
            
            COLORS = {
                'DEBUG': Fore.CYAN,
                'INFO': Fore.GREEN,
                'WARNING': Fore.YELLOW,
                'ERROR': Fore.RED,
                'CRITICAL': Fore.MAGENTA + Style.BRIGHT
            }
            
            def format(self, record):
                levelname = record.levelname
                if levelname in self.COLORS:
                    record.levelname = f"{self.COLORS[levelname]}{levelname}{Style.RESET_ALL}"
                    record.msg = f"{self.COLORS[levelname]}{record.msg}{Style.RESET_ALL}"
                return super().format(record)
        
        # Créer et ajouter le handler coloré
        color_handler = logging.StreamHandler()
        color_handler.setFormatter(ColoredFormatter(DEFAULT_LOG_FORMAT))
        logger.addHandler(color_handler)
    
    def _setup_exception_handler(self):
        """Configure le gestionnaire d'exceptions global"""
        original_excepthook = sys.excepthook
        
        def exception_handler(exc_type, exc_value, exc_traceback):
            """Gère les exceptions non interceptées"""
            # Ne pas capturer les interruptions clavier
            if issubclass(exc_type, KeyboardInterrupt):
                original_excepthook(exc_type, exc_value, exc_traceback)
                return
            
            # Journaliser l'exception
            if self.use_loguru:
                loguru_logger.opt(exception=(exc_type, exc_value, exc_traceback)).error(
                    "Exception non gérée de type {}: {}", 
                    exc_type.__name__, str(exc_value)
                )
            else:
                logger = self.get_logger("exception_handler")
                logger.error(
                    "Exception non gérée de type %s: %s\n%s",
                    exc_type.__name__, 
                    str(exc_value),
                    "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
                )
            
            # Mettre à jour les statistiques d'erreur
            self.record_error(exc_value, "uncaught_exception")
        
        sys.excepthook = exception_handler
    
    def record_error(self, error, module=None):
        """
        Enregistre une erreur dans les statistiques
        
        Args:
            error: L'erreur à enregistrer
            module: Le module où l'erreur s'est produite
        """
        error_type = type(error).__name__
        timestamp = datetime.now().isoformat()
        
        # Obtenir des informations sur la frame appelante
        frame = inspect.currentframe().f_back
        frame_info = inspect.getframeinfo(frame)
        
        # Mettre à jour les statistiques globales
        self.error_stats["total_errors"] += 1
        self.error_stats["last_error_time"] = timestamp
        
        # Mettre à jour les statistiques par module
        if module:
            if module not in self.error_stats["by_module"]:
                self.error_stats["by_module"][module] = 0
            self.error_stats["by_module"][module] += 1
        
        # Mettre à jour les statistiques par type d'erreur
        if error_type not in self.error_stats["by_type"]:
            self.error_stats["by_type"][error_type] = 0
        self.error_stats["by_type"][error_type] += 1
        
        # Enregistrer dans les erreurs récentes
        error_info = {
            "timestamp": timestamp,
            "type": error_type,
            "message": str(error),
            "module": module,
            "file": frame_info.filename,
            "line": frame_info.lineno,
            "function": frame_info.function
        }
        
        self.error_stats["recent_errors"].append(error_info)
        
        # Limiter le nombre d'erreurs récentes
        if len(self.error_stats["recent_errors"]) > 100:
            self.error_stats["recent_errors"].pop(0)
    
    def get_error_stats(self):
        """Retourne les statistiques d'erreurs"""
        return self.error_stats
    
    def save_error_stats(self, filename=None):
        """
        Sauvegarde les statistiques d'erreurs dans un fichier JSON
        
        Args:
            filename: Nom du fichier où sauvegarder les statistiques
        """
        if filename is None:
            filename = self.log_dir / f"error_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filename, 'w') as f:
            json.dump(self.error_stats, f, indent=2)


# Décorateur pour mesurer le temps d'exécution
def log_execution_time(logger=None, level="DEBUG"):
    """
    Décorateur pour mesurer et journaliser le temps d'exécution d'une fonction
    
    Args:
        logger: Logger à utiliser (si None, utilisera le logger du module)
        level: Niveau de log à utiliser
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Récupérer le logger approprié
            if logger is None:
                # Obtenir le module de la fonction
                module_name = func.__module__
                if LOGURU_AVAILABLE:
                    log = loguru_logger.bind(name=module_name)
                else:
                    log = logging.getLogger(module_name)
            else:
                log = logger
            
            start_time = time.time()
            func_name = func.__name__
            
            # Journaliser le début de l'exécution
            if hasattr(log, level.lower()):
                log_method = getattr(log, level.lower())
                log_method(f"Début de l'exécution de {func_name}")
            
            # Exécuter la fonction
            try:
                result = func(*args, **kwargs)
                # Calculer le temps d'exécution
                execution_time = time.time() - start_time
                
                # Journaliser la fin de l'exécution
                if hasattr(log, level.lower()):
                    log_method(f"Fin de l'exécution de {func_name} en {execution_time:.4f}s")
                
                return result
            except Exception as e:
                # Calculer le temps jusqu'à l'erreur
                execution_time = time.time() - start_time
                
                # Journaliser l'erreur
                if hasattr(log, "error"):
                    log.error(f"Erreur dans {func_name} après {execution_time:.4f}s: {str(e)}")
                
                # Propager l'exception
                raise
        
        return wrapper
    
    # Permettre l'utilisation du décorateur avec ou sans arguments
    if callable(logger):
        func, logger = logger, None
        return decorator(func)
    
    return decorator


# Création d'une instance globale du gestionnaire de logs
_log_manager = None

def setup_logging(
    log_dir=DEFAULT_LOG_DIR,
    log_level=DEFAULT_LOG_LEVEL,
    use_loguru=LOGURU_AVAILABLE,
    catch_exceptions=True
):
    """
    Configure le système de journalisation global
    
    Args:
        log_dir: Répertoire où stocker les fichiers de log
        log_level: Niveau de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        use_loguru: Utiliser loguru si disponible
        catch_exceptions: Intercepter les exceptions non gérées
        
    Returns:
        LogManager: Le gestionnaire de logs
    """
    global _log_manager
    _log_manager = LogManager(
        log_dir=log_dir,
        log_level=log_level,
        use_loguru=use_loguru,
        catch_exceptions=catch_exceptions
    )
    return _log_manager

def get_logger(name):
    """
    Obtient un logger configuré
    
    Args:
        name: Nom du logger (généralement le nom du module)
        
    Returns:
        Logger: Logger configuré
    """
    global _log_manager
    if _log_manager is None:
        setup_logging()
    
    return _log_manager.get_logger(name)

def get_error_stats():
    """
    Obtient les statistiques d'erreurs
    
    Returns:
        Dict: Statistiques d'erreurs
    """
    global _log_manager
    if _log_manager is None:
        setup_logging()
    
    return _log_manager.get_error_stats()

def save_error_stats(filename=None):
    """
    Sauvegarde les statistiques d'erreurs
    
    Args:
        filename: Nom du fichier où sauvegarder les statistiques
    """
    global _log_manager
    if _log_manager is None:
        setup_logging()
    
    return _log_manager.save_error_stats(filename)


# Initialiser le système de logging si le module est exécuté directement
if __name__ == "__main__":
    # Configurer le logging
    setup_logging(log_level="DEBUG")
    
    # Obtenir un logger
    logger = get_logger("improved_logging")
    
    # Exemple d'utilisation
    logger.info("Test du système de journalisation amélioré")
    logger.debug("Message de débogage")
    logger.warning("Message d'avertissement")
    
    try:
        # Simuler une erreur
        1 / 0
    except Exception as e:
        logger.error(f"Une erreur s'est produite: {str(e)}")
    
    # Exemple d'utilisation du décorateur
    @log_execution_time
    def function_test():
        """Fonction de test pour le décorateur de temps d'exécution"""
        logger.info("Exécution de la fonction de test")
        time.sleep(1)
        return "Test réussi"
    
    result = function_test()
    logger.info(f"Résultat: {result}")
    
    # Afficher les statistiques d'erreurs
    stats = get_error_stats()
    logger.info(f"Total d'erreurs: {stats['total_errors']}")
    
    print("Test terminé, vérifiez les fichiers de log dans le répertoire 'logs'") 