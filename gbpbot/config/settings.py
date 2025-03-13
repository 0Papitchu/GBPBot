"""
Module de configuration pour GBPBot.

Ce module permet de charger et d'accéder aux paramètres de configuration 
du système, en combinant les sources suivantes :
- Fichiers de configuration (.env, .env.local)
- Variables d'environnement
- Valeurs par défaut du système
"""

import os
import json
import logging
from typing import Dict, Any, Optional, Union
from pathlib import Path
from dotenv import load_dotenv

from gbpbot.utils.logger import setup_logger

# Configuration du logger
logger = setup_logger("settings", logging.INFO)

# Chemin vers le répertoire racine du projet
_ROOT_DIR = Path(__file__).parent.parent.parent.absolute()

# Cache des paramètres
_SETTINGS_CACHE: Dict[str, Any] = {}

def load_settings() -> Dict[str, Any]:
    """
    Charge tous les paramètres depuis les différentes sources.
    
    Returns:
        Dictionnaire des paramètres
    """
    # Si les paramètres sont déjà en cache, les retourner
    if _SETTINGS_CACHE:
        return _SETTINGS_CACHE
    
    settings = {}
    
    # Charger les fichiers .env et .env.local
    _load_dotenv_files()
    
    # Paramètres par défaut
    defaults = _get_default_settings()
    settings.update(defaults)
    
    # Paramètres depuis les variables d'environnement
    env_settings = {k: v for k, v in os.environ.items() if k.startswith(("GBPBOT_", "CLAUDE_", "OPENAI_", "LLAMA_", "AI_"))}
    settings.update(env_settings)
    
    # Charger les configurations spécifiques
    blockchain_config = _load_config_file("blockchain_config.json")
    if blockchain_config:
        settings["BLOCKCHAIN_CONFIG"] = blockchain_config
    
    trading_config = _load_config_file("trading_config.json")
    if trading_config:
        settings["TRADING_CONFIG"] = trading_config
    
    anti_detection_config = _load_config_file("anti_detection_config.json")
    if anti_detection_config:
        settings["ANTI_DETECTION_CONFIG"] = anti_detection_config
    
    # Mettre en cache
    _SETTINGS_CACHE.update(settings)
    
    return settings

def get_settings() -> Dict[str, Any]:
    """
    Retourne les paramètres du système.
    
    Returns:
        Dictionnaire des paramètres
    """
    return load_settings()

def get_setting(key: str, default: Any = None) -> Any:
    """
    Récupère un paramètre spécifique.
    
    Args:
        key: Clé du paramètre
        default: Valeur par défaut si le paramètre n'existe pas
        
    Returns:
        Valeur du paramètre ou default si le paramètre n'existe pas
    """
    settings = get_settings()
    return settings.get(key, default)

def update_setting(key: str, value: Any) -> None:
    """
    Met à jour un paramètre.
    
    Args:
        key: Clé du paramètre
        value: Nouvelle valeur
    """
    settings = get_settings()
    settings[key] = value
    _SETTINGS_CACHE[key] = value

def _load_dotenv_files() -> None:
    """Charge les variables depuis les fichiers .env et .env.local."""
    # Fichier .env (valeurs par défaut)
    env_path = _ROOT_DIR / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
        logger.debug(f"Variables chargées depuis {env_path}")
    
    # Fichier .env.local (valeurs spécifiques à l'installation)
    local_env_path = _ROOT_DIR / ".env.local"
    if local_env_path.exists():
        load_dotenv(dotenv_path=local_env_path, override=True)
        logger.debug(f"Variables chargées depuis {local_env_path}")

def _load_config_file(filename: str) -> Optional[Dict[str, Any]]:
    """
    Charge un fichier de configuration JSON.
    
    Args:
        filename: Nom du fichier
        
    Returns:
        Contenu du fichier ou None si le fichier n'existe pas
    """
    config_path = _ROOT_DIR / "config" / filename
    
    if not config_path.exists():
        return None
    
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Erreur lors du chargement de {filename}: {str(e)}")
        return None

def _get_default_settings() -> Dict[str, Any]:
    """
    Retourne les paramètres par défaut du système.
    
    Returns:
        Dictionnaire des paramètres par défaut
    """
    return {
        # Configuration générale
        "GBPBOT_ENV": "development",
        "GBPBOT_LOG_LEVEL": "INFO",
        "GBPBOT_CONSOLE_LOG": "true",
        "GBPBOT_FILE_LOG": "true",
        
        # Configuration IA
        "AI_PROVIDER": "auto",  # auto, claude, openai, llama
        "AI_RESPONSE_FORMAT": "json",
        "AI_TEMPERATURE": "0.2",
        "AI_CACHE_TTL": "600",  # 10 minutes
        
        # Configuration Claude
        "CLAUDE_MODEL": "claude-3-haiku-20240307",
        "CLAUDE_MAX_TOKENS": "4096",
        
        # Configuration OpenAI
        "OPENAI_MODEL": "gpt-4",
        "OPENAI_MAX_TOKENS": "4096",
        
        # Configuration LLaMA
        "LLAMA_CONTEXT_SIZE": "4096",
        "LLAMA_GPU_LAYERS": "0",
        
        # Configuration des blockchains
        "DEFAULT_BLOCKCHAIN": "solana",
        
        # Configuration du système anti-détection
        "ANTI_DETECTION_ENABLED": "true",
        "AI_PROFILE_MANAGEMENT": "true",
        "PERFORMANCE_PRIORITY": "0.7",  # 0.0-1.0 (0=discrétion max, 1=performance max)
    } 