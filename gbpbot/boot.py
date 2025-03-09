"""
Module d'initialisation de GBPBot

Ce module charge les variables d'environnement et prépare
l'environnement d'exécution pour le bot.
"""

import os
import logging
import sys
from pathlib import Path
from dotenv import load_dotenv

# Configurer le logger
logger = logging.getLogger("Boot")

def initialize_environment():
    """
    Initialise l'environnement d'exécution pour le GBPBot.
    Charge les variables d'environnement depuis les fichiers .env
    """
    try:
        # Définir le chemin de base
        base_path = Path(__file__).parent.parent
        
        # Charger les variables d'environnement
        env_files = [
            base_path / ".env.local",
            base_path / ".env"
        ]
        
        env_loaded = False
        for env_file in env_files:
            if env_file.exists():
                logger.info(f"Chargement des variables d'environnement depuis {env_file}")
                load_dotenv(env_file)
                env_loaded = True
        
        if not env_loaded:
            logger.warning("Aucun fichier d'environnement (.env.local ou .env) trouvé!")
            logger.warning("Certaines fonctionnalités peuvent ne pas fonctionner correctement.")
        
        # Vérifier les variables d'environnement essentielles
        check_essential_env_vars()
        
        # Initialiser les répertoires
        initialize_directories()
        
        return True
        
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation de l'environnement: {str(e)}")
        return False

def check_essential_env_vars():
    """Vérifie que les variables d'environnement essentielles sont définies"""
    essential_vars = [
        "BOT_MODE",
        "DEFAULT_BLOCKCHAIN"
    ]
    
    missing_vars = [var for var in essential_vars if not os.environ.get(var)]
    
    if missing_vars:
        logger.warning(f"Variables d'environnement manquantes: {', '.join(missing_vars)}")
        logger.warning("Certaines fonctionnalités peuvent ne pas fonctionner correctement.")

def initialize_directories():
    """Initialise les répertoires nécessaires pour le bot"""
    try:
        base_path = Path(__file__).parent.parent
        
        # Répertoires à créer s'ils n'existent pas
        directories = [
            base_path / "logs",
            base_path / "data",
            base_path / "wallets",
            base_path / "cache"
        ]
        
        for directory in directories:
            if not directory.exists():
                directory.mkdir(parents=True, exist_ok=True)
                logger.info(f"Répertoire créé: {directory}")
        
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation des répertoires: {str(e)}")

def initialize_logging():
    """Configure le système de logging"""
    logging_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, logging_level, logging.INFO)
    
    # Configuration de base du logging
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(Path(__file__).parent.parent / "logs" / "gbpbot.log")
        ]
    )
    
    # Réduire la verbosité des bibliothèques externes
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("web3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    
    logger.info(f"Système de logging initialisé au niveau {logging_level}")

# Fonction principale d'initialisation
def boot():
    """Initialise complètement l'environnement du bot"""
    print("Initialisation de GBPBot...")
    
    # Initialiser le logging
    initialize_logging()
    
    # Initialiser l'environnement
    if not initialize_environment():
        logger.error("Échec de l'initialisation de l'environnement. Arrêt du bot.")
        sys.exit(1)
    
    logger.info("GBPBot initialisé avec succès!")
    return True 