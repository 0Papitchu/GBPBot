"""
Module d'Optimisation des Logs pour GBPBot
==========================================

Ce module fournit des fonctions pour configurer la rotation automatique des
logs, limitant ainsi la taille des fichiers de logs et optimisant l'utilisation
du stockage.
"""

import os
import logging
import logging.handlers
from logging.handlers import RotatingFileHandler
from typing import Dict, Optional, List

# Répertoire des logs
LOG_DIR = "logs"

def setup_optimized_logging(config: Dict) -> None:
    """
    Configure la rotation automatique des logs pour GBPBot
    
    Args:
        config: Configuration du bot
    """
    try:
        # Créer le répertoire de logs s'il n'existe pas
        if not os.path.exists(LOG_DIR):
            os.makedirs(LOG_DIR)
        
        # Récupérer la configuration
        log_level_str = config.get("LOG_LEVEL", "info").upper()
        log_max_size_mb = int(config.get("LOG_MAX_SIZE", 50))
        log_backup_count = int(config.get("LOG_BACKUP_COUNT", 5))
        
        # Convertir le niveau de log
        log_level = getattr(logging, log_level_str, logging.INFO)
        
        # Récupérer le logger racine
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        
        # Supprimer les handlers existants
        for handler in list(root_logger.handlers):
            root_logger.removeHandler(handler)
        
        # Créer un handler pour la console
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(console_format)
        root_logger.addHandler(console_handler)
        
        # Créer un handler pour le fichier de log principal avec rotation
        log_file = os.path.join(LOG_DIR, "gbpbot.log")
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=log_max_size_mb * 1024 * 1024,  # Convertir en octets
            backupCount=log_backup_count
        )
        file_handler.setLevel(log_level)
        file_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_format)
        root_logger.addHandler(file_handler)
        
        # Configurer des loggers spécifiques pour les modules clés
        _setup_module_logger("gbpbot.strategies", config, "strategy.log")
        _setup_module_logger("gbpbot.blockchain", config, "blockchain.log")
        _setup_module_logger("gbpbot.machine_learning", config, "ml.log")
        _setup_module_logger("gbpbot.telegram_bot", config, "telegram.log")
        
        logging.info(f"Logging optimisé configuré avec rotation (taille max: {log_max_size_mb}MB, backups: {log_backup_count})")
        
    except Exception as e:
        # Fallback en cas d'erreur
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        logging.error(f"Erreur lors de la configuration du logging optimisé: {str(e)}")

def _setup_module_logger(module_name: str, config: Dict, log_file: str) -> None:
    """
    Configure un logger spécifique pour un module
    
    Args:
        module_name: Nom du module
        config: Configuration du bot
        log_file: Nom du fichier de log
    """
    try:
        # Récupérer la configuration
        log_level_str = config.get("LOG_LEVEL", "info").upper()
        log_max_size_mb = int(config.get("LOG_MAX_SIZE", 50))
        log_backup_count = int(config.get("LOG_BACKUP_COUNT", 5))
        
        # Convertir le niveau de log
        log_level = getattr(logging, log_level_str, logging.INFO)
        
        # Récupérer le logger du module
        logger = logging.getLogger(module_name)
        logger.setLevel(log_level)
        
        # Vérifier si le logger a déjà des handlers
        for handler in list(logger.handlers):
            if isinstance(handler, RotatingFileHandler):
                logger.removeHandler(handler)
        
        # Créer le handler avec rotation
        log_path = os.path.join(LOG_DIR, log_file)
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=log_max_size_mb * 1024 * 1024,  # Convertir en octets
            backupCount=log_backup_count
        )
        file_handler.setLevel(log_level)
        file_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_format)
        
        # Ajouter le handler au logger
        logger.addHandler(file_handler)
        
    except Exception as e:
        logging.error(f"Erreur lors de la configuration du logger pour {module_name}: {str(e)}")

def get_log_files() -> List[str]:
    """
    Récupère la liste des fichiers de log
    
    Returns:
        List[str]: Liste des fichiers de log
    """
    try:
        if not os.path.exists(LOG_DIR):
            return []
            
        log_files = []
        for file in os.listdir(LOG_DIR):
            if file.endswith(".log") or file.endswith(".log.1") or file.endswith(".log.2"):
                log_files.append(os.path.join(LOG_DIR, file))
                
        return log_files
        
    except Exception as e:
        logging.error(f"Erreur lors de la récupération des fichiers de log: {str(e)}")
        return []

def get_log_usage() -> Dict:
    """
    Récupère les statistiques d'utilisation des logs
    
    Returns:
        Dict: Statistiques d'utilisation des logs
    """
    try:
        log_files = get_log_files()
        
        total_size = 0
        files_count = len(log_files)
        
        for file in log_files:
            if os.path.exists(file):
                total_size += os.path.getsize(file)
                
        return {
            "files_count": files_count,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "files": [{"name": os.path.basename(f), "size_mb": round(os.path.getsize(f) / (1024 * 1024), 2)} for f in log_files]
        }
        
    except Exception as e:
        logging.error(f"Erreur lors de la récupération des statistiques de logs: {str(e)}")
        return {"files_count": 0, "total_size_mb": 0, "files": [], "error": str(e)}

def clean_old_logs(max_days: int = 30) -> int:
    """
    Supprime les fichiers de log plus anciens que max_days
    
    Args:
        max_days: Nombre maximum de jours de conservation des logs
        
    Returns:
        int: Nombre de fichiers supprimés
    """
    try:
        import time
        from datetime import datetime, timedelta
        
        if not os.path.exists(LOG_DIR):
            return 0
            
        # Calcul de la date limite
        cutoff_time = time.time() - (max_days * 86400)  # 86400 = 24 * 60 * 60 (secondes dans une journée)
        
        # Parcourir les fichiers de log
        deleted_count = 0
        for file in os.listdir(LOG_DIR):
            file_path = os.path.join(LOG_DIR, file)
            
            # Vérifier si c'est un fichier de log sauvegardé (format: *.log.N)
            if file.endswith(".log.1") or file.endswith(".log.2") or file.endswith(".log.3"):
                # Vérifier l'âge du fichier
                file_time = os.path.getmtime(file_path)
                if file_time < cutoff_time:
                    # Supprimer le fichier
                    os.remove(file_path)
                    deleted_count += 1
                    
        return deleted_count
        
    except Exception as e:
        logging.error(f"Erreur lors du nettoyage des vieux logs: {str(e)}")
        return 0 