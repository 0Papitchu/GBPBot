#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Module de configuration pour GBPBot.

Ce module gère le chargement et la validation des paramètres de configuration
depuis le fichier .env et d'autres sources.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union, List, TypedDict, cast
from dotenv import load_dotenv

# TypedDict pour la configuration
class Config(TypedDict, total=False):
    """TypedDict pour la configuration de GBPBot."""
    # Configuration générale
    DEBUG: bool
    LOG_LEVEL: str
    ENVIRONMENT: str
    
    # Configuration Solana
    SOLANA_RPC_URL: str
    SOLANA_PRIVATE_KEY: str
    
    # Configuration AVAX
    AVAX_RPC_URL: str
    AVAX_PRIVATE_KEY: str
    
    # Configuration Sonic
    SONIC_RPC_URL: str
    SONIC_PRIVATE_KEY: str
    
    # Paramètres trading
    MAX_SLIPPAGE: float
    GAS_PRIORITY: str
    MAX_TRANSACTION_AMOUNT: float
    ENABLE_SNIPING: bool
    ENABLE_ARBITRAGE: bool
    ENABLE_AUTO_MODE: bool
    
    # Sécurité
    REQUIRE_CONTRACT_ANALYSIS: bool
    ENABLE_STOP_LOSS: bool
    DEFAULT_STOP_LOSS_PERCENTAGE: float
    
    # Interface utilisateur
    ENABLE_WEB_DASHBOARD: bool
    WEB_DASHBOARD_PORT: int
    
    # IA et Machine Learning
    ENABLE_AI_ANALYSIS: bool
    USE_LOCAL_MODELS: bool
    USE_OPENAI_API: bool
    OPENAI_API_KEY: str
    
    # Configuration avancée
    MEMPOOL_MONITORING: bool
    MEV_PROTECTION: bool
    ENABLE_ANTI_RUGPULL: bool

# Valeurs par défaut pour la configuration
DEFAULT_CONFIG: Config = {
    # Configuration générale
    "DEBUG": False,
    "LOG_LEVEL": "info",
    "ENVIRONMENT": "production",
    
    # Configuration Solana
    "SOLANA_RPC_URL": "https://api.mainnet-beta.solana.com",
    "SOLANA_PRIVATE_KEY": "",
    
    # Configuration AVAX
    "AVAX_RPC_URL": "https://api.avax.network/ext/bc/C/rpc",
    "AVAX_PRIVATE_KEY": "",
    
    # Configuration Sonic
    "SONIC_RPC_URL": "https://rpc.sonic.fantom.network/",
    "SONIC_PRIVATE_KEY": "",
    
    # Paramètres trading
    "MAX_SLIPPAGE": 1.0,
    "GAS_PRIORITY": "medium",
    "MAX_TRANSACTION_AMOUNT": 0.1,
    "ENABLE_SNIPING": True,
    "ENABLE_ARBITRAGE": False,
    "ENABLE_AUTO_MODE": False,
    
    # Sécurité
    "REQUIRE_CONTRACT_ANALYSIS": True,
    "ENABLE_STOP_LOSS": True,
    "DEFAULT_STOP_LOSS_PERCENTAGE": 5.0,
    
    # Interface utilisateur
    "ENABLE_WEB_DASHBOARD": True,
    "WEB_DASHBOARD_PORT": 8080,
    
    # IA et Machine Learning
    "ENABLE_AI_ANALYSIS": True,
    "USE_LOCAL_MODELS": True,
    "USE_OPENAI_API": False,
    "OPENAI_API_KEY": "",
    
    # Configuration avancée
    "MEMPOOL_MONITORING": True,
    "MEV_PROTECTION": True,
    "ENABLE_ANTI_RUGPULL": True
}

# Singleton pour la configuration
_config_instance: Optional[Config] = None

def load_config(config_path: Optional[str] = None) -> Config:
    """
    Charge la configuration depuis le fichier .env et d'autres sources.
    
    Args:
        config_path: Chemin optionnel vers un fichier de configuration spécifique.
        
    Returns:
        Dict[str, Any]: La configuration chargée.
    """
    global _config_instance
    
    # Si la configuration est déjà chargée, retourner l'instance singleton
    if _config_instance is not None:
        return _config_instance
    
    # Créer une nouvelle configuration basée sur les valeurs par défaut
    config: Config = DEFAULT_CONFIG.copy()
    
    # Déterminer le chemin du fichier .env
    if config_path is None:
        # Rechercher le fichier .env dans le répertoire courant et les répertoires parents
        current_dir = Path.cwd()
        env_path = None
        
        # Rechercher dans le répertoire courant et jusqu'à 3 niveaux au-dessus
        for i in range(4):
            test_path = current_dir / ".env"
            if test_path.exists():
                env_path = test_path
                break
            current_dir = current_dir.parent
        
        if env_path is not None:
            config_path = str(env_path)
        else:
            logging.warning("Fichier .env non trouvé. Utilisation des valeurs par défaut.")
            _config_instance = config
            return config
    
    # Charger les variables d'environnement depuis le fichier .env
    load_dotenv(dotenv_path=config_path)
    
    # Mettre à jour la configuration avec les variables d'environnement
    for key in config.keys():
        env_value = os.getenv(key)
        if env_value is not None:
            # Convertir les valeurs en types appropriés
            if isinstance(config[key], bool):
                # Convertir les chaînes en booléens
                config[key] = env_value.lower() in ("true", "t", "1", "yes", "y")
            elif isinstance(config[key], int):
                # Convertir les chaînes en entiers
                try:
                    config[key] = int(env_value)
                except ValueError:
                    logging.warning(f"Valeur invalide pour {key}: {env_value}. Utilisation de la valeur par défaut: {config[key]}")
            elif isinstance(config[key], float):
                # Convertir les chaînes en flottants
                try:
                    config[key] = float(env_value)
                except ValueError:
                    logging.warning(f"Valeur invalide pour {key}: {env_value}. Utilisation de la valeur par défaut: {config[key]}")
            else:
                # Pour les chaînes et autres types
                config[key] = env_value
    
    # Stocker la configuration dans le singleton
    _config_instance = config
    
    return config

def get_config() -> Config:
    """
    Retourne la configuration actuelle. La charge si ce n'est pas déjà fait.
    
    Returns:
        Dict[str, Any]: La configuration actuelle.
    """
    global _config_instance
    
    if _config_instance is None:
        _config_instance = load_config()
    
    return _config_instance

def update_config(updates: Dict[str, Any]) -> Config:
    """
    Met à jour la configuration avec de nouvelles valeurs.
    
    Args:
        updates: Dictionnaire des mises à jour à appliquer.
        
    Returns:
        Dict[str, Any]: La configuration mise à jour.
    """
    global _config_instance
    
    if _config_instance is None:
        _config_instance = load_config()
    
    # Mettre à jour la configuration
    for key, value in updates.items():
        if key in _config_instance:
            _config_instance[key] = value
    
    return _config_instance

def save_config(config_path: Optional[str] = None) -> bool:
    """
    Sauvegarde la configuration actuelle dans le fichier .env.
    
    Args:
        config_path: Chemin optionnel vers un fichier de configuration spécifique.
        
    Returns:
        bool: True si la sauvegarde a réussi, False sinon.
    """
    global _config_instance
    
    if _config_instance is None:
        _config_instance = load_config()
    
    # Déterminer le chemin du fichier .env
    if config_path is None:
        # Rechercher le fichier .env dans le répertoire courant et les répertoires parents
        current_dir = Path.cwd()
        env_path = None
        
        # Rechercher dans le répertoire courant et jusqu'à 3 niveaux au-dessus
        for i in range(4):
            test_path = current_dir / ".env"
            if test_path.exists():
                env_path = test_path
                break
            current_dir = current_dir.parent
        
        if env_path is not None:
            config_path = str(env_path)
        else:
            config_path = ".env"  # Créer le fichier dans le répertoire courant
    
    try:
        # Lire le fichier .env existant
        env_lines: Dict[str, str] = {}
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        env_lines[key.strip()] = value.strip()
        
        # Mettre à jour les valeurs
        for key, value in _config_instance.items():
            env_lines[key] = str(value)
        
        # Écrire le fichier .env
        with open(config_path, "w") as f:
            f.write("# Configuration GBPBot\n")
            f.write("# Généré automatiquement\n\n")
            
            # Écrire les variables d'environnement par sections
            
            # Configuration générale
            f.write("# Configuration générale\n")
            for key in ["DEBUG", "LOG_LEVEL", "ENVIRONMENT"]:
                if key in env_lines:
                    f.write(f"{key}={env_lines[key]}\n")
            f.write("\n")
            
            # Configuration Solana
            f.write("# Configuration Solana\n")
            for key in ["SOLANA_RPC_URL", "SOLANA_PRIVATE_KEY"]:
                if key in env_lines:
                    f.write(f"{key}={env_lines[key]}\n")
            f.write("\n")
            
            # Configuration AVAX
            f.write("# Configuration AVAX\n")
            for key in ["AVAX_RPC_URL", "AVAX_PRIVATE_KEY"]:
                if key in env_lines:
                    f.write(f"{key}={env_lines[key]}\n")
            f.write("\n")
            
            # Configuration Sonic
            f.write("# Configuration Sonic\n")
            for key in ["SONIC_RPC_URL", "SONIC_PRIVATE_KEY"]:
                if key in env_lines:
                    f.write(f"{key}={env_lines[key]}\n")
            f.write("\n")
            
            # Paramètres trading
            f.write("# Paramètres trading\n")
            for key in ["MAX_SLIPPAGE", "GAS_PRIORITY", "MAX_TRANSACTION_AMOUNT", 
                       "ENABLE_SNIPING", "ENABLE_ARBITRAGE", "ENABLE_AUTO_MODE"]:
                if key in env_lines:
                    f.write(f"{key}={env_lines[key]}\n")
            f.write("\n")
            
            # Sécurité
            f.write("# Sécurité\n")
            for key in ["REQUIRE_CONTRACT_ANALYSIS", "ENABLE_STOP_LOSS", 
                       "DEFAULT_STOP_LOSS_PERCENTAGE"]:
                if key in env_lines:
                    f.write(f"{key}={env_lines[key]}\n")
            f.write("\n")
            
            # Interface utilisateur
            f.write("# Interface utilisateur\n")
            for key in ["ENABLE_WEB_DASHBOARD", "WEB_DASHBOARD_PORT"]:
                if key in env_lines:
                    f.write(f"{key}={env_lines[key]}\n")
            f.write("\n")
            
            # IA et Machine Learning
            f.write("# IA et Machine Learning\n")
            for key in ["ENABLE_AI_ANALYSIS", "USE_LOCAL_MODELS", 
                       "USE_OPENAI_API", "OPENAI_API_KEY"]:
                if key in env_lines:
                    f.write(f"{key}={env_lines[key]}\n")
            f.write("\n")
            
            # Configuration avancée
            f.write("# Configuration avancée\n")
            for key in ["MEMPOOL_MONITORING", "MEV_PROTECTION", "ENABLE_ANTI_RUGPULL"]:
                if key in env_lines:
                    f.write(f"{key}={env_lines[key]}\n")
        
        logging.info(f"Configuration sauvegardée dans {config_path}")
        return True
    
    except Exception as e:
        logging.error(f"Erreur lors de la sauvegarde de la configuration: {e}")
        return False

def reset_config() -> Config:
    """
    Réinitialise la configuration aux valeurs par défaut.
    
    Returns:
        Dict[str, Any]: La configuration réinitialisée.
    """
    global _config_instance
    
    _config_instance = DEFAULT_CONFIG.copy()
    
    return _config_instance

# Initialiser la configuration au démarrage du module
if _config_instance is None:
    try:
        _config_instance = load_config()
    except Exception as e:
        logging.error(f"Erreur lors du chargement de la configuration: {e}")
        _config_instance = DEFAULT_CONFIG.copy() 