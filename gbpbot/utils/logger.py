"""
Module de gestion des logs pour GBPBot
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime
from typing import Optional

# Configurer les couleurs pour le terminal
COLORS = {
    "GREEN": "\033[92m",
    "YELLOW": "\033[93m",
    "RED": "\033[91m",
    "BLUE": "\033[94m",
    "CYAN": "\033[96m",
    "MAGENTA": "\033[95m",
    "BOLD": "\033[1m",
    "END": "\033[0m"
}

# Formateur personnalisé pour les logs avec couleurs
class ColoredFormatter(logging.Formatter):
    """Formateur personnalisé pour les logs avec couleurs dans la console"""
    
    LEVEL_COLORS = {
        logging.DEBUG: COLORS["BLUE"],
        logging.INFO: COLORS["GREEN"],
        logging.WARNING: COLORS["YELLOW"],
        logging.ERROR: COLORS["RED"],
        logging.CRITICAL: COLORS["RED"] + COLORS["BOLD"]
    }
    
    def format(self, record):
        # Ajouter la couleur au nom du niveau de log
        if record.levelno in self.LEVEL_COLORS:
            color = self.LEVEL_COLORS[record.levelno]
            record.levelname = f"{color}{record.levelname}{COLORS['END']}"
            
        return super().format(record)

def setup_logger(
    name: str,
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    max_size: int = 10 * 1024 * 1024,  # 10 Mo par défaut
    backup_count: int = 5
) -> logging.Logger:
    """
    Configure et retourne un logger personnalisé avec formatage coloré
    et rotation des fichiers de log
    
    Args:
        name: Nom du logger
        level: Niveau de log
        log_file: Fichier de log (optionnel)
        max_size: Taille maximale d'un fichier de log avant rotation
        backup_count: Nombre de fichiers de backup à conserver
        
    Returns:
        Logger configuré
    """
    # Obtenir ou créer le logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Éviter les handlers dupliqués
    if logger.handlers:
        return logger
    
    # Format de base pour tous les logs
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    # Ajouter un handler pour la console avec formatage coloré
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_formatter = ColoredFormatter(log_format, datefmt=date_format)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # Ajouter un handler pour le fichier si spécifié ou utiliser le nom par défaut
    if log_file is None:
        # Déterminer le répertoire de logs
        log_dir = Path(__file__).parent.parent.parent / "logs"
        if not log_dir.exists():
            log_dir.mkdir(parents=True, exist_ok=True)
            
        # Créer un nom de fichier basé sur le nom du logger
        log_file = log_dir / f"{name.lower()}.log"
    
    # Convertir le chemin en string si c'est un Path
    if isinstance(log_file, Path):
        log_file = str(log_file)
    
    # Ajouter le handler de fichier avec rotation
    file_handler = RotatingFileHandler(
        log_file, 
        maxBytes=max_size,
        backupCount=backup_count
    )
    file_handler.setLevel(level)
    file_formatter = logging.Formatter(log_format, datefmt=date_format)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    return logger

# Fonction pour obtenir le niveau de log à partir d'une chaîne
def get_log_level(level_str: str) -> int:
    """
    Convertit une chaîne de niveau de log en constante de logging
    
    Args:
        level_str: Chaîne représentant le niveau (debug, info, warning, error, critical)
        
    Returns:
        Constante de niveau de log
    """
    levels = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "critical": logging.CRITICAL
    }
    
    return levels.get(level_str.lower(), logging.INFO)

# Initialisation du logger racine pour tout le projet
def init_root_logger():
    """Initialise le logger racine pour tout le projet"""
    # Récupérer le niveau de log depuis les variables d'environnement
    log_level_str = os.environ.get("LOG_LEVEL", "info")
    log_level = get_log_level(log_level_str)
    
    # Configurer le logger racine
    root_logger = setup_logger(
        "GBPBot",
        level=log_level,
        log_file=Path(__file__).parent.parent.parent / "logs" / "gbpbot.log"
    )
    
    # Log initial
    root_logger.info(f"GBPBot démarré - Niveau de log: {log_level_str.upper()}")
    return root_logger 