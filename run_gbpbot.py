#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de lancement du GBPBot
=============================

Ce script est le point d'entrée principal pour lancer le GBPBot avec toutes ses fonctionnalités.
Il permet de démarrer le bot en mode CLI, Telegram ou Dashboard, et de configurer les différentes
stratégies de trading.
"""

import os
import sys
import time
import signal
import argparse
import logging
import threading
import subprocess
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

# Ajouter le répertoire parent au path pour les imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

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
    ██████╗ ██████╗ ██████╗ ██████╗  ██████╗ ████████╗
    ██╔════╝ ██╔══██╗██╔══██╗██╔══██╗██╔═══██╗╚══██╔══╝
    ██║  ███╗██████╔╝██████╔╝██████╔╝██║   ██║   ██║   
    ██║   ██║██╔══██╗██╔═══╝ ██╔══██╗██║   ██║   ██║   
    ╚██████╔╝██████╔╝██║     ██████╔╝╚██████╔╝   ██║   
     ╚═════╝ ╚═════╝ ╚═╝     ╚═════╝  ╚═════╝    ╚═╝   
    ================================================
    Trading Bot Ultra-Rapide pour MEME Coins
    Solana | AVAX | Sonic
    ================================================
    """
    print(banner)

def load_config(config_path: str = None) -> Dict[str, Any]:
    """
    Charge la configuration du bot depuis un fichier JSON ou .env
    
    Args:
        config_path: Chemin vers le fichier de configuration
        
    Returns:
        Dict[str, Any]: Configuration chargée
    """
    # Essayer d'importer le module de configuration
    try:
        from gbpbot.core.config import load as load_config_func
        return load_config_func(config_path)
    except ImportError:
        logger.warning("Module de configuration non trouvé, utilisation de la configuration par défaut")
    
    # Fallback: charger depuis .env
    config = {}
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        # Charger les variables d'environnement dans la configuration
        for key, value in os.environ.items():
            if key.startswith(("GBPBOT_", "BOT_", "SOLANA_", "AVALANCHE_", "SONIC_")):
                config[key] = value
                
        logger.info(f"Configuration chargée depuis les variables d'environnement: {len(config)} paramètres")
    except ImportError:
        logger.warning("Module python-dotenv non trouvé, impossible de charger .env")
    
    # Fallback: charger depuis un fichier JSON
    if not config and config_path and os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception as e:
            logger.error(f"Erreur lors du chargement du fichier de configuration: {str(e)}")
    
    return config

def initialize_optimization(config: Dict[str, Any], args: argparse.Namespace) -> bool:
    """
    Initialise les optimisations matérielles si activées
    
    Args:
        config: Configuration du bot
        args: Arguments de ligne de commande
        
    Returns:
        bool: True si l'initialisation a réussi, False sinon
    """
    optimization_enabled = args.optimize or config.get("optimization", {}).get("enabled", False)
    
    if not optimization_enabled:
        logger.info("Optimisation matérielle désactivée")
        return False
    
    try:
        from gbpbot.core.optimization import initialize_hardware_optimization
        
        # Déterminer le profil d'optimisation à utiliser
        profile = args.optimization_profile or config.get("optimization", {}).get("profile", "default")
        
        # Initialiser l'optimisation matérielle
        success = initialize_hardware_optimization(config.get("optimization", {}), profile)
        
        if success:
            logger.info(f"Optimisation matérielle initialisée avec succès (profil: {profile})")
            
            # Afficher l'état de l'optimisation si le mode verbeux est activé
            if args.verbose:
                from gbpbot.core.optimization import get_optimization_status, get_hardware_recommendations
                
                status = get_optimization_status()
                hardware_info = status.get("hardware_info", {})
                
                logger.info(f"Matériel détecté: "
                           f"CPU: {hardware_info.get('cpu', {}).get('model', 'Inconnu')}, "
                           f"RAM: {hardware_info.get('memory', {}).get('total', 0) / (1024**3):.1f} Go, "
                           f"GPU: {hardware_info.get('gpu', {}).get('model', 'Non détecté')}")
                
                # Afficher les recommandations
                recommendations = get_hardware_recommendations().get("recommendations", [])
                if recommendations:
                    logger.info("Recommandations d'optimisation:")
                    for i, rec in enumerate(recommendations, 1):
                        logger.info(f"  {i}. {rec}")
        else:
            logger.warning("Échec de l'initialisation de l'optimisation matérielle")
        
        return success
    
    except ImportError:
        logger.warning("Module d'optimisation matérielle non disponible")
        return False
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation de l'optimisation: {str(e)}")
        return False

def initialize_modules(config: Dict[str, Any], blockchains: List[str]) -> Dict[str, Any]:
    """
    Initialise les modules du bot selon la configuration
    
    Args:
        config: Configuration du bot
        blockchains: Liste des blockchains à activer
        
    Returns:
        Dict[str, Any]: Modules initialisés
    """
    modules = {}
    
    # Initialiser les clients blockchain
    try:
        logger.info(f"Initialisation des clients blockchain: {', '.join(blockchains)}")
        blockchain_clients = {}
        
        for blockchain in blockchains:
            try:
                # Importer dynamiquement le module de client blockchain
                from gbpbot.blockchain import create_blockchain_client
                
                client = create_blockchain_client(blockchain, config.get(blockchain, {}))
                blockchain_clients[blockchain] = client
                logger.info(f"Client {blockchain.capitalize()} initialisé")
            except ImportError as e:
                logger.error(f"Impossible d'initialiser le client {blockchain}: {e}")
            except Exception as e:
                logger.error(f"Erreur lors de l'initialisation du client {blockchain}: {e}")
        
        modules["blockchain_clients"] = blockchain_clients
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation des clients blockchain: {e}")
    
    # Initialiser les stratégies de trading
    try:
        # 1. Stratégie d'arbitrage
        if config.get("arbitrage", {}).get("enabled", False):
            logger.info("Initialisation de la stratégie d'arbitrage...")
            try:
                from gbpbot.strategies.arbitrage import create_arbitrage_strategy
                arbitrage_strategy = create_arbitrage_strategy(blockchain_clients, config.get("arbitrage", {}))
                modules["arbitrage_strategy"] = arbitrage_strategy
                logger.info("Stratégie d'arbitrage initialisée")
            except ImportError as e:
                logger.warning(f"Module d'arbitrage non trouvé: {e}")
        
        # 2. Stratégie de sniping (Solana)
        if "solana" in blockchains and config.get("sniping", {}).get("enabled", False):
            logger.info("Initialisation de la stratégie de sniping Solana...")
            try:
                from gbpbot.strategies.sniping import create_solana_memecoin_sniper
                solana_client = blockchain_clients.get("solana")
                if solana_client:
                    sniper_strategy = create_solana_memecoin_sniper(
                        solana_client,
                        config.get("sniping", {})
                    )
                    modules["sniper_strategy"] = sniper_strategy
                    logger.info("Stratégie de sniping Solana initialisée")
                else:
                    logger.warning("Client Solana non disponible, impossible d'initialiser le sniping")
            except ImportError as e:
                logger.warning(f"Module de sniping non trouvé: {e}")
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation des stratégies de trading: {e}")
    
    # Initialiser le client IA si demandé
    if config.get("ai", {}).get("enabled", False):
        logger.info("Initialisation du client IA...")
        try:
            from gbpbot.ai import create_ai_client
            ai_client = create_ai_client(
                model=config.get("ai", {}).get("model", "local"),
                config=config.get("ai", {})
            )
            modules["ai_client"] = ai_client
            logger.info(f"Client IA initialisé (modèle: {config.get('ai', {}).get('model', 'local')})")
        except ImportError as e:
            logger.warning(f"Module IA non trouvé: {e}")
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du client IA: {e}")
    
    # Initialiser le moteur de backtesting si disponible
    if config.get("backtesting", {}).get("enabled", False):
        logger.info("Initialisation du moteur de backtesting...")
        try:
            from gbpbot.backtesting import BacktestingEngine
            backtesting_engine = BacktestingEngine(config.get("backtesting", {}))
            modules["backtesting_engine"] = backtesting_engine
            logger.info("Moteur de backtesting initialisé")
        except ImportError as e:
            logger.warning(f"Module de backtesting non trouvé: {e}")
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du moteur de backtesting: {e}")
    
    return modules

def start_modules(modules: Dict[str, Any], stop_event: threading.Event) -> None:
    """
    Démarre les modules actifs du bot
    
    Args:
        modules: Modules initialisés
        stop_event: Événement pour arrêter les modules
    """
    # Démarrer les stratégies dans des threads séparés
    threads = []
    
    # 1. Stratégie d'arbitrage
    if "arbitrage_strategy" in modules:
        arbitrage_strategy = modules["arbitrage_strategy"]
        try:
            arbitrage_thread = threading.Thread(
                target=arbitrage_strategy.run,
                args=(stop_event,),
                name="ArbitrageThread",
                daemon=True
            )
            arbitrage_thread.start()
            threads.append(arbitrage_thread)
            logger.info("Stratégie d'arbitrage démarrée")
        except Exception as e:
            logger.error(f"Erreur lors du démarrage de la stratégie d'arbitrage: {e}")
    
    # 2. Stratégie de sniping
    if "sniper_strategy" in modules:
        sniper_strategy = modules["sniper_strategy"]
        try:
            sniper_thread = threading.Thread(
                target=sniper_strategy.run,
                args=(stop_event,),
                name="SniperThread",
                daemon=True
            )
            sniper_thread.start()
            threads.append(sniper_thread)
            logger.info("Stratégie de sniping démarrée")
        except Exception as e:
            logger.error(f"Erreur lors du démarrage de la stratégie de sniping: {e}")
    
    # 3. Mode automatique
    if "auto_strategy" in modules:
        auto_strategy = modules["auto_strategy"]
        try:
            auto_thread = threading.Thread(
                target=auto_strategy.run,
                args=(stop_event,),
                name="AutoModeThread",
                daemon=True
            )
            auto_thread.start()
            threads.append(auto_thread)
            logger.info("Mode automatique démarré")
        except Exception as e:
            logger.error(f"Erreur lors du démarrage du mode automatique: {e}")
    
    # Définir un gestionnaire de signal pour arrêter proprement
    def signal_handler(sig, frame):
        logger.info("Signal d'arrêt reçu, arrêt des modules...")
        stop_event.set()
        
        # Essayer de nettoyer les ressources d'optimisation
        try:
            from gbpbot.core.optimization import shutdown_optimization
            shutdown_optimization()
            logger.info("Optimisation matérielle arrêtée proprement")
        except ImportError:
            pass
        
        # Attendre que tous les threads se terminent
        for thread in threads:
            thread.join(timeout=5.0)
        
        logger.info("Tous les modules ont été arrêtés")
        sys.exit(0)
    
    # Enregistrer le gestionnaire pour SIGINT (Ctrl+C)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Attendre que tous les threads se terminent
    try:
        while not stop_event.is_set():
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Interruption clavier détectée, arrêt des modules...")
        stop_event.set()
        
        # Arrêter l'optimisation si active
        try:
            from gbpbot.core.optimization import shutdown_optimization
            shutdown_optimization()
        except ImportError:
            pass

def start_interactive_mode(config: Dict[str, Any], modules: Dict[str, Any]) -> None:
    """
    Démarre le bot en mode interactif (CLI)
    
    Args:
        config: Configuration du bot
        modules: Modules initialisés
    """
    try:
        from gbpbot.gbpbot_menu import main as run_menu
        run_menu()
    except ImportError:
        logger.error("Module de menu non trouvé, impossible de démarrer le mode interactif")
        display_banner()
        print("Erreur: Module de menu non trouvé. Veuillez installer le package complet.")
        sys.exit(1)

def start_telegram_mode(config: Dict[str, Any], modules: Dict[str, Any]) -> None:
    """
    Démarre le bot en mode Telegram
    
    Args:
        config: Configuration du bot
        modules: Modules initialisés
    """
    try:
        from gbpbot.telegram_bot import run_telegram_bot
        run_telegram_bot(config, modules)
    except ImportError:
        logger.error("Module Telegram non trouvé, impossible de démarrer le mode Telegram")
        print("Erreur: Module Telegram non trouvé. Veuillez installer le package complet.")
            sys.exit(1)

def start_dashboard_mode(config: Dict[str, Any], modules: Dict[str, Any]) -> None:
    """
    Démarre le dashboard web du bot
    
    Args:
        config: Configuration du bot
        modules: Modules initialisés
    """
    try:
        # Lancer le dashboard dans un processus séparé
        dashboard_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gbpbot", "dashboard", "run_dashboard.py")
        
        if sys.platform.startswith('win'):
            # Windows
            dashboard_process = subprocess.Popen(
                [sys.executable, dashboard_script],
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
        else:
            # Linux/Mac
            dashboard_process = subprocess.Popen(
                [sys.executable, dashboard_script],
                start_new_session=True
            )
        
        logger.info(f"Dashboard démarré (PID: {dashboard_process.pid})")
        
        # Démarrer les modules du bot
        stop_event = threading.Event()
        start_modules(modules, stop_event)
        
    except Exception as e:
        logger.error(f"Erreur lors du démarrage du dashboard: {e}")
        print(f"Erreur: Impossible de démarrer le dashboard: {e}")
        sys.exit(1)

def start_auto_mode(config: Dict[str, Any], modules: Dict[str, Any]) -> None:
    """
    Démarre le bot en mode automatique
    
    Args:
        config: Configuration du bot
        modules: Modules initialisés
    """
    try:
        # Démarrer les modules du bot
        stop_event = threading.Event()
        
        # Importer et initialiser le mode automatique si disponible
        try:
            from gbpbot.strategies.auto_mode import create_auto_mode_strategy
            auto_strategy = create_auto_mode_strategy(modules, config)
            modules["auto_strategy"] = auto_strategy
            logger.info("Stratégie de mode automatique initialisée")
        except ImportError as e:
            logger.warning(f"Module de mode automatique non trouvé: {e}")
            
        # Démarrer les modules
        start_modules(modules, stop_event)
            
    except Exception as e:
        logger.error(f"Erreur lors du démarrage du mode automatique: {e}")
        print(f"Erreur: Impossible de démarrer le mode automatique: {e}")
        sys.exit(1)

def main():
    """Fonction principale du programme"""
    parser = argparse.ArgumentParser(description="GBPBot - Trading Bot Ultra-Rapide pour MEME Coins")
    
    # Mode de fonctionnement
    parser.add_argument("--mode", choices=["cli", "telegram", "dashboard", "auto"], default="cli",
                       help="Mode de fonctionnement (cli, telegram, dashboard, auto)")
    
    # Paramètres généraux
    parser.add_argument("--config", type=str, default=None,
                       help="Chemin vers le fichier de configuration")
    parser.add_argument("--verbose", action="store_true",
                       help="Afficher les messages de débogage")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], default="INFO",
                       help="Niveau de journalisation")
    
    # Optimisation matérielle
    parser.add_argument("--optimize", action="store_true",
                       help="Activer l'optimisation matérielle")
    parser.add_argument("--optimization-profile", type=str, default=None,
                       help="Profil d'optimisation à utiliser")
    
    # Paramètres blockchain
    parser.add_argument("--solana", action="store_true",
                       help="Activer le support Solana")
    parser.add_argument("--avalanche", action="store_true",
                       help="Activer le support Avalanche")
    parser.add_argument("--sonic", action="store_true",
                       help="Activer le support Sonic")
    
    # Paramètres de stratégie
    parser.add_argument("--arbitrage", action="store_true",
                       help="Activer la stratégie d'arbitrage")
    parser.add_argument("--sniping", action="store_true",
                       help="Activer la stratégie de sniping")
    parser.add_argument("--mev", action="store_true",
                       help="Activer les optimisations MEV")
    
    # Paramètres IA
    parser.add_argument("--ai", action="store_true",
                       help="Activer l'intelligence artificielle")
    parser.add_argument("--ai-model", type=str, default=None,
                       help="Modèle d'IA à utiliser")
    
    # Analyser les arguments
    args = parser.parse_args()
    
    # Configurer le niveau de journalisation
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Afficher la bannière
    display_banner()
    
    # Chargement de la configuration
    config = load_config(args.config)
    
    # Initialiser l'optimisation matérielle si demandé
    optimize_success = initialize_optimization(config, args)
    if args.optimize and not optimize_success:
        logger.warning("L'optimisation matérielle a été demandée mais n'a pas pu être initialisée.")
    
    # Déterminer les blockchains à activer
    blockchains = []
    if args.solana or config.get("solana", {}).get("enabled", True):
        blockchains.append("solana")
    if args.avalanche or config.get("avalanche", {}).get("enabled", True):
        blockchains.append("avalanche")
    if args.sonic or config.get("sonic", {}).get("enabled", False):
        blockchains.append("sonic")
    
    # Initialiser les modules du bot
    modules = initialize_modules(config, blockchains)
    
    # Démarrer le bot dans le mode sélectionné
    logger.info(f"Démarrage du GBPBot en mode {args.mode}...")
    
    if args.mode == "cli":
        start_interactive_mode(config, modules)
    elif args.mode == "telegram":
        start_telegram_mode(config, modules)
    elif args.mode == "dashboard":
        start_dashboard_mode(config, modules)
    elif args.mode == "auto":
        start_auto_mode(config, modules)
    else:
        logger.error(f"Mode non reconnu: {args.mode}")
        sys.exit(1)

if __name__ == "__main__":
    # Importer asyncio ici pour éviter les problèmes avec les threads
    import asyncio
    
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Interruption clavier détectée, arrêt du bot")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Erreur non gérée: {e}", exc_info=True)
        sys.exit(1) 