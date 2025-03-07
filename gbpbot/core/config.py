"""
Module de gestion de la configuration pour GBPBot
================================================

Ce module gère la configuration de GBPBot, y compris le chargement
des paramètres depuis les fichiers de configuration et les variables d'environnement.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union, List
from dotenv import load_dotenv

# Configurer le logging
logger = logging.getLogger(__name__)

# Chemins de configuration par défaut
CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "config")
DEFAULT_CONFIG_FILE = "config.json"
DEFAULT_CONFIG_PATH = os.path.join(CONFIG_DIR, DEFAULT_CONFIG_FILE)

# Configuration par défaut
DEFAULT_CONFIG = {
    "version": "1.0.0",
    "system": {
        "log_level": "INFO",
        "log_file": "logs/gbpbot.log",
        "debug_mode": False
    },
    "blockchain": {
        "solana": {
            "enabled": True,
            "rpc_url": "https://api.mainnet-beta.solana.com",
            "websocket_url": "wss://api.mainnet-beta.solana.com",
            "commitment": "processed"
        },
        "avalanche": {
            "enabled": True,
            "rpc_url": "https://api.avax.network/ext/bc/C/rpc",
            "websocket_url": "wss://api.avax.network/ext/bc/C/ws",
            "chain_id": 43114
        },
        "sonic": {
            "enabled": False,
            "rpc_url": "https://mainnet.sonic.ooo/rpc",
            "websocket_url": "wss://mainnet.sonic.ooo/ws",
            "chain_id": 1
        }
    },
    "wallets": {
        "main_private_key": "",
        "main_address": "",
        "backup_private_key": "",
        "backup_address": ""
    },
    "trading": {
        "max_slippage": 2.0,
        "gas_price_multiplier": 1.2,
        "max_trade_amount_usd": 500,
        "transaction_timeout": 60,
        "min_profit_threshold": 0.5
    },
    "sniping": {
        "enabled": True,
        "check_honeypot": True,
        "min_liquidity_usd": 10000,
        "default_take_profit": 20.0,
        "default_stop_loss": 10.0,
        "trailing_take_profit": True,
        "trailing_percent": 5.0,
        "max_tokens_per_day": 5,
        "blacklisted_tokens": []
    },
    "arbitrage": {
        "enabled": True,
        "min_profit_threshold": 0.5,
        "max_arbitrage_amount_usd": 1000,
        "check_interval": 5.0,
        "use_flash_loans": False
    },
    "mev": {
        "enabled": True,
        "mempool_scan_interval": 0.1,
        "gas_boost_multiplier": 1.5,
        "priority_gas": 2.0
    },
    "security": {
        "stealth_mode": True,
        "tx_delay_random": True,
        "tx_delay_min": 1,
        "tx_delay_max": 3,
        "wallet_rotation": True,
        "transaction_variance": 0.15
    },
    "ai": {
        "enabled": True,
        "provider": "auto",
        "openai_api_key": "",
        "llama_model_path": "",
        "risk_threshold": 0.7,
        "confidence_threshold": 0.8
    },
    "backtesting": {
        "enabled": True,
        "default_timeframe": "1h",
        "default_data_source": "binance",
        "default_initial_balance": {"USDT": 1000}
    },
    "dashboard": {
        "enabled": True,
        "host": "0.0.0.0",
        "port": 8000,
        "debug": False
    },
    "telegram": {
        "enabled": False,
        "bot_token": "",
        "allowed_user_ids": []
    }
}

def ensure_config_dir():
    """Crée le répertoire de configuration s'il n'existe pas"""
    os.makedirs(CONFIG_DIR, exist_ok=True)

def load_env_vars() -> Dict[str, Any]:
    """
    Charge les variables d'environnement depuis le fichier .env
    
    Returns:
        Dict[str, Any]: Variables d'environnement chargées
    """
    # Charger les variables d'environnement depuis .env
    load_dotenv()
    
    # Extraire les variables pertinentes
    env_vars = {}
    for key, value in os.environ.items():
        if key.startswith(("GBPBOT_", "BOT_", "SOLANA_", "AVALANCHE_", "SONIC_", "OPENAI_")):
            env_vars[key] = value
    
    return env_vars

def env_to_config(env_vars: Dict[str, str]) -> Dict[str, Any]:
    """
    Convertit les variables d'environnement en configuration structurée
    
    Args:
        env_vars: Variables d'environnement
        
    Returns:
        Dict[str, Any]: Configuration structurée
    """
    config = {}
    
    # Mapping des variables d'environnement vers la configuration
    mappings = {
        # Système
        "BOT_MODE": ("system", "mode"),
        "LOG_LEVEL": ("system", "log_level"),
        "DEBUG_MODE": ("system", "debug_mode"),
        
        # Blockchain - Solana
        "SOLANA_ENABLED": ("blockchain", "solana", "enabled"),
        "SOLANA_RPC_URL": ("blockchain", "solana", "rpc_url"),
        "SOLANA_WEBSOCKET_URL": ("blockchain", "solana", "websocket_url"),
        
        # Blockchain - Avalanche
        "AVALANCHE_ENABLED": ("blockchain", "avalanche", "enabled"),
        "AVAX_RPC_URL": ("blockchain", "avalanche", "rpc_url"),
        "AVALANCHE_CHAIN_ID": ("blockchain", "avalanche", "chain_id"),
        
        # Blockchain - Sonic
        "SONIC_ENABLED": ("blockchain", "sonic", "enabled"),
        "SONIC_RPC_URL": ("blockchain", "sonic", "rpc_url"),
        
        # Wallets
        "PRIVATE_KEY": ("wallets", "main_private_key"),
        "WALLET_ADDRESS": ("wallets", "main_address"),
        
        # Trading
        "MAX_SLIPPAGE": ("trading", "max_slippage"),
        "GAS_PRICE_MULTIPLIER": ("trading", "gas_price_multiplier"),
        "MAX_TRADE_AMOUNT_USD": ("trading", "max_trade_amount_usd"),
        "TRANSACTION_TIMEOUT": ("trading", "transaction_timeout"),
        
        # Sniping
        "SNIPING_ENABLED": ("sniping", "enabled"),
        "CHECK_HONEYPOT": ("sniping", "check_honeypot"),
        "MIN_LIQUIDITY_USD": ("sniping", "min_liquidity_usd"),
        "DEFAULT_TAKE_PROFIT": ("sniping", "default_take_profit"),
        "DEFAULT_STOP_LOSS": ("sniping", "default_stop_loss"),
        
        # Arbitrage
        "ARBITRAGE_ENABLED": ("arbitrage", "enabled"),
        "MIN_PROFIT_THRESHOLD": ("arbitrage", "min_profit_threshold"),
        "MAX_ARBITRAGE_AMOUNT_USD": ("arbitrage", "max_arbitrage_amount_usd"),
        
        # MEV
        "MEV_ENABLED": ("mev", "enabled"),
        "MEMPOOL_SCAN_INTERVAL": ("mev", "mempool_scan_interval"),
        "GAS_BOOST_MULTIPLIER": ("mev", "gas_boost_multiplier"),
        
        # Security
        "STEALTH_MODE": ("security", "stealth_mode"),
        "TX_DELAY_RANDOM": ("security", "tx_delay_random"),
        
        # AI
        "AI_ENABLED": ("ai", "enabled"),
        "OPENAI_API_KEY": ("ai", "openai_api_key"),
        
        # Dashboard
        "DASHBOARD_ENABLED": ("dashboard", "enabled"),
        "DASHBOARD_PORT": ("dashboard", "port"),
        
        # Telegram
        "TELEGRAM_ENABLED": ("telegram", "enabled"),
        "TELEGRAM_BOT_TOKEN": ("telegram", "bot_token")
    }
    
    # Appliquer les mappings
    for env_key, value in env_vars.items():
        if env_key in mappings:
            path = mappings[env_key]
            
            # Convertir les valeurs
            if value.lower() in ("true", "yes", "1"):
                value = True
            elif value.lower() in ("false", "no", "0"):
                value = False
            elif value.isdigit():
                value = int(value)
            elif value.replace(".", "", 1).isdigit():
                value = float(value)
            
            # Créer la structure imbriquée
            current = config
            for i, key in enumerate(path):
                if i == len(path) - 1:
                    current[key] = value
                else:
                    if key not in current:
                        current[key] = {}
                    current = current[key]
    
    return config

def load(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Charge la configuration du GBPBot
    
    Args:
        config_path: Chemin vers le fichier de configuration (optionnel)
        
    Returns:
        Dict[str, Any]: Configuration chargée
    """
    config = DEFAULT_CONFIG.copy()
    
    # Assurer que le répertoire de configuration existe
    ensure_config_dir()
    
    # Charger depuis le fichier de configuration
    if config_path is None:
        config_path = DEFAULT_CONFIG_PATH
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                file_config = json.load(f)
                # Mise à jour récursive de la configuration
                deep_update(config, file_config)
            logger.info(f"Configuration chargée depuis {config_path}")
        except Exception as e:
            logger.error(f"Erreur lors du chargement de la configuration depuis {config_path}: {e}")
    else:
        logger.warning(f"Fichier de configuration {config_path} non trouvé, utilisation des valeurs par défaut")
        # Créer un fichier de configuration par défaut
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(DEFAULT_CONFIG, f, indent=4)
            logger.info(f"Fichier de configuration par défaut créé à {config_path}")
        except Exception as e:
            logger.error(f"Erreur lors de la création du fichier de configuration par défaut: {e}")
    
    # Charger les variables d'environnement
    env_vars = load_env_vars()
    env_config = env_to_config(env_vars)
    
    # Mettre à jour la configuration avec les variables d'environnement
    deep_update(config, env_config)
    
    return config

def save(config: Dict[str, Any], config_path: Optional[str] = None) -> bool:
    """
    Sauvegarde la configuration du GBPBot
    
    Args:
        config: Configuration à sauvegarder
        config_path: Chemin vers le fichier de configuration (optionnel)
        
    Returns:
        bool: True si la sauvegarde a réussi, False sinon
    """
    if config_path is None:
        config_path = DEFAULT_CONFIG_PATH
    
    # Assurer que le répertoire de configuration existe
    ensure_config_dir()
    
    try:
        # Créer une sauvegarde du fichier existant
        if os.path.exists(config_path):
            backup_path = f"{config_path}.bak"
            try:
                with open(config_path, 'r', encoding='utf-8') as src:
                    with open(backup_path, 'w', encoding='utf-8') as dst:
                        dst.write(src.read())
                logger.info(f"Sauvegarde de la configuration créée à {backup_path}")
            except Exception as e:
                logger.warning(f"Impossible de créer une sauvegarde de la configuration: {e}")
        
        # Sauvegarder la nouvelle configuration
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)
        
        logger.info(f"Configuration sauvegardée à {config_path}")
        return True
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde de la configuration: {e}")
        return False

def deep_update(target: Dict[str, Any], source: Dict[str, Any]) -> Dict[str, Any]:
    """
    Met à jour récursivement un dictionnaire avec les valeurs d'un autre
    
    Args:
        target: Dictionnaire cible
        source: Dictionnaire source
        
    Returns:
        Dict[str, Any]: Dictionnaire cible mis à jour
    """
    for key, value in source.items():
        if key in target and isinstance(target[key], dict) and isinstance(value, dict):
            deep_update(target[key], value)
        else:
            target[key] = value
    
    return target

def get_config_value(config: Dict[str, Any], path: List[str], default: Any = None) -> Any:
    """
    Récupère une valeur dans la configuration en suivant un chemin
    
    Args:
        config: Configuration
        path: Chemin vers la valeur
        default: Valeur par défaut si le chemin n'existe pas
        
    Returns:
        Any: Valeur trouvée ou valeur par défaut
    """
    current = config
    for key in path:
        if key in current:
            current = current[key]
        else:
            return default
    
    return current

def set_config_value(config: Dict[str, Any], path: List[str], value: Any) -> Dict[str, Any]:
    """
    Définit une valeur dans la configuration en suivant un chemin
    
    Args:
        config: Configuration
        path: Chemin vers la valeur
        value: Nouvelle valeur
        
    Returns:
        Dict[str, Any]: Configuration mise à jour
    """
    if not path:
        return config
    
    current = config
    for i, key in enumerate(path):
        if i == len(path) - 1:
            current[key] = value
        else:
            if key not in current:
                current[key] = {}
            current = current[key]
    
    return config 