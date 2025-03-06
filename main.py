#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GBPBot - Point d'entrée principal
==================================

Ce fichier sert de point d'entrée principal pour le GBPBot, permettant de lancer:
- Le mode interactif avec menu CLI
- Le mode Telegram
- Le mode entièrement automatique
- Le monitoring des performances
"""

import os
import sys
import time
import signal
import argparse
import logging
from typing import Dict, List, Optional, Union, Any
from datetime import datetime
import threading
import json

# Ajout du répertoire parent au path pour les imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configuration du logging
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = os.path.join(log_dir, f"gbpbot_{timestamp}.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("GBPBot")

# Bannière ASCII pour l'interface CLI
def display_banner():
    """Affiche la bannière ASCII du GBPBot"""
    banner = """
╔════════════════════════════════════════════════════════════════════════════╗
║                                                                            ║
║   ██████╗ ██████╗ ██████╗ ██████╗  ██████╗ ████████╗                      ║
║  ██╔════╝ ██╔══██╗██╔══██╗██╔══██╗██╔═══██╗╚══██╔══╝                      ║
║  ██║  ███╗██████╔╝██████╔╝██████╔╝██║   ██║   ██║                         ║
║  ██║   ██║██╔══██╗██╔═══╝ ██╔══██╗██║   ██║   ██║                         ║
║  ╚██████╔╝██████╔╝██║     ██████╔╝╚██████╔╝   ██║                         ║
║   ╚═════╝ ╚═════╝ ╚═╝     ╚═════╝  ╚═════╝    ╚═╝  v1.0.0                 ║
║                                                                            ║
║  Trading Bot pour MEME Coins sur Solana, AVAX et Sonic                     ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝
"""
    print(banner)

# Variables globales pour les modules actifs
active_modules = {}
stop_event = threading.Event()

def load_config(config_path: str = None) -> Dict[str, Any]:
    """
    Charge la configuration du bot depuis les fichiers .env et config.json
    
    Args:
        config_path: Chemin vers le fichier de configuration (optionnel)
        
    Returns:
        Dict contenant la configuration complète
    """
    from dotenv import load_dotenv
    
    # Chargement des variables d'environnement depuis .env
    load_dotenv()
    
    config = {
        # Configuration générale
        "mode": os.getenv("BOT_MODE", "interactive"),
        "log_level": os.getenv("LOG_LEVEL", "INFO"),
        
        # Configuration des blockchains
        "blockchains": {
            "solana": {
                "enabled": os.getenv("ENABLE_SOLANA", "true").lower() == "true",
                "rpc_url": os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com"),
                "private_key": os.getenv("SOLANA_PRIVATE_KEY", ""),
                "alternative_rpcs": json.loads(os.getenv("SOLANA_ALTERNATIVE_RPCS", "[]"))
            },
            "avalanche": {
                "enabled": os.getenv("ENABLE_AVALANCHE", "true").lower() == "true",
                "rpc_url": os.getenv("AVALANCHE_RPC_URL", "https://api.avax.network/ext/bc/C/rpc"),
                "private_key": os.getenv("AVALANCHE_PRIVATE_KEY", ""),
                "alternative_rpcs": json.loads(os.getenv("AVALANCHE_ALTERNATIVE_RPCS", "[]"))
            },
            "sonic": {
                "enabled": os.getenv("ENABLE_SONIC", "false").lower() == "true",
                "rpc_url": os.getenv("SONIC_RPC_URL", ""),
                "private_key": os.getenv("SONIC_PRIVATE_KEY", ""),
                "alternative_rpcs": json.loads(os.getenv("SONIC_ALTERNATIVE_RPCS", "[]"))
            }
        },
        
        # Configuration des modules
        "modules": {
            "arbitrage": {
                "enabled": os.getenv("ENABLE_ARBITRAGE", "true").lower() == "true",
                "min_profit_percentage": float(os.getenv("ARBITRAGE_MIN_PROFIT", "0.5")),
                "max_slippage": float(os.getenv("ARBITRAGE_MAX_SLIPPAGE", "1.0")),
                "gas_multiplier": float(os.getenv("ARBITRAGE_GAS_MULTIPLIER", "1.05")),
                "scan_interval": int(os.getenv("ARBITRAGE_SCAN_INTERVAL", "5")),
                "pairs": json.loads(os.getenv("ARBITRAGE_PAIRS", "[]")),
                "exchanges": json.loads(os.getenv("ARBITRAGE_EXCHANGES", "[]"))
            },
            "token_sniper": {
                "enabled": os.getenv("ENABLE_TOKEN_SNIPER", "true").lower() == "true",
                "min_liquidity": float(os.getenv("SNIPER_MIN_LIQUIDITY", "5000")),
                "max_buy_amount": float(os.getenv("SNIPER_MAX_BUY_AMOUNT", "0.1")),
                "auto_sell_multiplier": float(os.getenv("SNIPER_AUTO_SELL_MULTIPLIER", "1.5")),
                "stop_loss_percentage": float(os.getenv("SNIPER_STOP_LOSS", "0.9")),
                "scan_interval": int(os.getenv("SNIPER_SCAN_INTERVAL", "2")),
                "blacklist_tokens": json.loads(os.getenv("SNIPER_BLACKLIST", "[]")),
                "whitelist_tokens": json.loads(os.getenv("SNIPER_WHITELIST", "[]"))
            },
            "auto_mode": {
                "enabled": os.getenv("ENABLE_AUTO_MODE", "false").lower() == "true",
                "strategy": os.getenv("AUTO_MODE_STRATEGY", "balanced"),
                "max_concurrent_trades": int(os.getenv("AUTO_MAX_CONCURRENT_TRADES", "3")),
                "max_allocation_percentage": float(os.getenv("AUTO_MAX_ALLOCATION", "30")),
                "risk_level": os.getenv("AUTO_RISK_LEVEL", "medium")
            },
            "telegram": {
                "enabled": os.getenv("ENABLE_TELEGRAM", "false").lower() == "true",
                "token": os.getenv("TELEGRAM_BOT_TOKEN", ""),
                "allowed_users": json.loads(os.getenv("TELEGRAM_ALLOWED_USERS", "[]")),
                "chat_id": os.getenv("TELEGRAM_CHAT_ID", "")
            },
            "performance": {
                "enabled": os.getenv("ENABLE_PERFORMANCE_MONITOR", "false").lower() == "true",
                "auto_optimize": os.getenv("ENABLE_AUTO_OPTIMIZER", "false").lower() == "true"
            }
        },
        
        # Paramètres d'optimisation
        "optimization": {
            "max_transaction_history": int(os.getenv("MAX_TRANSACTION_HISTORY", "10000")),
            "max_token_cache_size": int(os.getenv("MAX_TOKEN_CACHE_SIZE", "2000")),
            "max_concurrent_requests": int(os.getenv("MAX_CONCURRENT_REQUESTS", "100")),
            "websocket_batch_size": int(os.getenv("WEBSOCKET_BATCH_SIZE", "20")),
            "use_async_processing": os.getenv("USE_ASYNC_PROCESSING", "true").lower() == "true",
            "memory_limit_mb": int(os.getenv("MEMORY_LIMIT_MB", "2048")),
            "thread_pool_size": int(os.getenv("THREAD_POOL_SIZE", "8"))
        }
    }
    
    # Si un fichier de configuration supplémentaire est spécifié, le charger
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                file_config = json.load(f)
                
            # Fusionner la configuration du fichier avec celle de l'environnement
            def deep_merge(source, destination):
                for key, value in source.items():
                    if key in destination and isinstance(destination[key], dict) and isinstance(value, dict):
                        deep_merge(value, destination[key])
                    else:
                        destination[key] = value
                return destination
            
            config = deep_merge(file_config, config)
            logger.info(f"Configuration chargée depuis {config_path}")
        except Exception as e:
            logger.error(f"Erreur lors du chargement de la configuration depuis {config_path}: {e}")
    
    return config

def initialize_modules(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Initialise les modules du bot en fonction de la configuration
    
    Args:
        config: Dictionnaire de configuration
        
    Returns:
        Dict contenant les instances des modules initialisés
    """
    from gbpbot.clients.blockchain_client_factory import BlockchainClientFactory
    from gbpbot.modules.arbitrage_engine import ArbitrageEngine
    from gbpbot.modules.token_sniper import TokenSniper
    from gbpbot.modules.auto_trader import AutoTrader
    
    modules = {}
    
    # Initialisation des clients blockchain
    blockchain_clients = {}
    for chain_name, chain_config in config["blockchains"].items():
        if chain_config["enabled"] and chain_config["rpc_url"]:
            try:
                client = BlockchainClientFactory.create_client(
                    blockchain=chain_name,
                    rpc_url=chain_config["rpc_url"],
                    private_key=chain_config["private_key"],
                    alternative_rpcs=chain_config["alternative_rpcs"]
                )
                blockchain_clients[chain_name] = client
                logger.info(f"Client {chain_name} initialisé avec succès")
            except Exception as e:
                logger.error(f"Erreur lors de l'initialisation du client {chain_name}: {e}")
    
    # Initialisation du module d'arbitrage
    if config["modules"]["arbitrage"]["enabled"]:
        try:
            arbitrage_engine = ArbitrageEngine(
                blockchain_clients=blockchain_clients,
                config=config["modules"]["arbitrage"]
            )
            modules["arbitrage"] = arbitrage_engine
            logger.info("Module d'arbitrage initialisé avec succès")
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du module d'arbitrage: {e}")
    
    # Initialisation du module de sniping de tokens
    if config["modules"]["token_sniper"]["enabled"]:
        try:
            token_sniper = TokenSniper(
                blockchain_clients=blockchain_clients,
                config=config["modules"]["token_sniper"]
            )
            modules["token_sniper"] = token_sniper
            logger.info("Module de sniping de tokens initialisé avec succès")
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du module de sniping: {e}")
    
    # Initialisation du module automatique
    if config["modules"]["auto_mode"]["enabled"]:
        try:
            auto_trader = AutoTrader(
                blockchain_clients=blockchain_clients,
                arbitrage_engine=modules.get("arbitrage"),
                token_sniper=modules.get("token_sniper"),
                config=config["modules"]["auto_mode"]
            )
            modules["auto_mode"] = auto_trader
            logger.info("Module automatique initialisé avec succès")
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du module automatique: {e}")
    
    # Initialisation du monitoring de performances
    if config["modules"]["performance"]["enabled"]:
        try:
            from gbpbot.utils.performance_monitor import SystemMonitor
            performance_monitor = SystemMonitor(
                auto_optimize=config["modules"]["performance"]["auto_optimize"]
            )
            modules["performance"] = performance_monitor
            logger.info("Module de monitoring de performances initialisé avec succès")
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du monitoring: {e}")
    
    return modules

def start_modules(modules: Dict[str, Any], stop_event: threading.Event) -> None:
    """
    Démarre les modules du bot
    
    Args:
        modules: Dictionnaire contenant les instances des modules
        stop_event: Événement pour arrêter les modules
    """
    global active_modules
    
    # Démarrage du monitoring de performances en premier
    if "performance" in modules:
        try:
            modules["performance"].start()
            active_modules["performance"] = modules["performance"]
            logger.info("Module de monitoring de performances démarré")
        except Exception as e:
            logger.error(f"Erreur lors du démarrage du monitoring: {e}")
    
    # Démarrage des modules principaux
    for module_name, module in modules.items():
        if module_name == "performance":
            continue  # Déjà démarré
            
        try:
            if hasattr(module, "start"):
                module.start(stop_event)
                active_modules[module_name] = module
                logger.info(f"Module {module_name} démarré avec succès")
        except Exception as e:
            logger.error(f"Erreur lors du démarrage du module {module_name}: {e}")

def stop_modules() -> None:
    """Arrête tous les modules actifs"""
    global active_modules, stop_event
    
    logger.info("Arrêt des modules en cours...")
    stop_event.set()
    
    # Arrêt des modules dans l'ordre inverse du démarrage
    for module_name, module in reversed(list(active_modules.items())):
        try:
            if hasattr(module, "stop"):
                module.stop()
                logger.info(f"Module {module_name} arrêté avec succès")
        except Exception as e:
            logger.error(f"Erreur lors de l'arrêt du module {module_name}: {e}")
    
    # Réinitialisation des variables globales
    active_modules.clear()
    stop_event.clear()

def signal_handler(sig, frame):
    """Gestionnaire de signal pour arrêter proprement le bot"""
    logger.info("Signal d'arrêt reçu, arrêt du GBPBot en cours...")
    stop_modules()
    logger.info("GBPBot arrêté avec succès")
    sys.exit(0)

def start_interactive_mode(config: Dict[str, Any], modules: Dict[str, Any]) -> None:
    """
    Démarre le bot en mode interactif (menu CLI)
    
    Args:
        config: Dictionnaire de configuration
        modules: Dictionnaire contenant les instances des modules
    """
    from gbpbot.interfaces.cli_menu import start_cli_menu
    start_cli_menu(config, modules, stop_event)

def start_telegram_mode(config: Dict[str, Any], modules: Dict[str, Any]) -> None:
    """
    Démarre le bot en mode Telegram
    
    Args:
        config: Dictionnaire de configuration
        modules: Dictionnaire contenant les instances des modules
    """
    from gbpbot.interfaces.telegram_bot import start_telegram_bot
    start_telegram_bot(config, modules, stop_event)

def start_auto_mode(config: Dict[str, Any], modules: Dict[str, Any]) -> None:
    """
    Démarre le bot en mode entièrement automatique
    
    Args:
        config: Dictionnaire de configuration
        modules: Dictionnaire contenant les instances des modules
    """
    global stop_event
    
    logger.info("Démarrage en mode automatique...")
    
    # Vérifier si le module auto_mode est disponible
    if "auto_mode" not in modules:
        logger.error("Module auto_mode non initialisé. Impossible de démarrer en mode automatique.")
        return
    
    # Démarrer tous les modules
    start_modules(modules, stop_event)
    
    # Maintenir le processus principal en vie jusqu'à interruption
    try:
        while not stop_event.is_set():
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Interruption clavier détectée. Arrêt du GBPBot...")
        stop_modules()

def main():
    """Fonction principale du GBPBot"""
    # Parser les arguments de ligne de commande
    parser = argparse.ArgumentParser(description="GBPBot - Trading Bot pour MEME Coins")
    parser.add_argument(
        "-m", "--mode",
        choices=["interactive", "telegram", "auto"],
        default=None,
        help="Mode de fonctionnement du bot (interactive, telegram, auto)"
    )
    parser.add_argument(
        "-c", "--config",
        default=None,
        help="Chemin vers le fichier de configuration"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Activer le mode verbeux pour le débogage"
    )
    
    args = parser.parse_args()
    
    # Configurer le niveau de log
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug("Mode verbeux activé")
    
    # Afficher la bannière
    display_banner()
    
    # Enregistrer le gestionnaire de signal
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Charger la configuration
    config = load_config(args.config)
    
    # Utiliser le mode spécifié en ligne de commande s'il existe
    if args.mode:
        config["mode"] = args.mode
    
    # Initialiser les modules
    modules = initialize_modules(config)
    
    # Démarrer le bot dans le mode approprié
    if config["mode"] == "telegram":
        if config["modules"]["telegram"]["enabled"]:
            start_telegram_mode(config, modules)
        else:
            logger.error("Mode Telegram sélectionné mais non activé dans la configuration")
            sys.exit(1)
    elif config["mode"] == "auto":
        if config["modules"]["auto_mode"]["enabled"]:
            start_auto_mode(config, modules)
        else:
            logger.error("Mode automatique sélectionné mais non activé dans la configuration")
            sys.exit(1)
    else:  # Mode interactif par défaut
        start_interactive_mode(config, modules)

if __name__ == "__main__":
    main() 