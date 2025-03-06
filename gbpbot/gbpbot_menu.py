#!/usr/bin/env python3
"""
Menu principal du GBPBot - Interface utilisateur améliorée
==========================================================

Ce module fournit une interface en ligne de commande intuitive pour GBPBot,
permettant d'accéder rapidement aux différentes fonctionnalités du bot.
"""

import os
import sys
import time
import logging
import json
import asyncio
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import subprocess
import platform

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"logs/gbpbot_{datetime.now().strftime('%Y-%m-%d')}.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("gbpbot.menu")

# Tentative d'importation des modules GBPBot
try:
    from gbpbot.core import config
    from gbpbot.strategies import arbitrage, sniping
    from gbpbot.core.blockchain.base import BlockchainClientFactory
    from gbpbot.utils.environment import print_environment_report
    from gbpbot.utils.config import get_config  # Importer la fonction correcte pour charger la configuration
    from gbpbot.sniping import SolanaSnipingIntegration
except ImportError as e:
    logger.error(f"Erreur lors de l'importation des modules GBPBot: {str(e)}")
    logger.error("Assurez-vous que GBPBot est correctement installé")
    sys.exit(1)

# Constantes pour les couleurs
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# État global du bot
class BotState:
    def __init__(self):
        self.running = False
        self.active_modules = {
            "arbitrage": False,
            "sniping": False,
            "auto_mode": False,
            "solana_sniping": False,  # Ajout du module de sniping Solana
            "solana_frontrun": False,
            "cross_dex_arbitrage": False
        }
        self.start_time = None
        self.blockchain_clients = {}
        self.strategies = {}
        self.config = None
        self.module_instances = {}
    
    def start(self):
        """Démarre le bot"""
        self.running = True
        self.start_time = time.time()
    
    def stop(self):
        """Arrête le bot"""
        self.running = False
        self.start_time = None
        self.active_modules = {
            "arbitrage": False,
            "sniping": False,
            "auto_mode": False,
            "solana_sniping": False,
            "solana_frontrun": False,
            "cross_dex_arbitrage": False
        }
        self.module_instances = {}

# Instanciation de l'état global
bot_state = BotState()

def clear_screen():
    """Efface l'écran selon le système d'exploitation"""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header(text: str):
    """Affiche un texte formaté comme titre"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{text}{Colors.ENDC}")

def print_menu_option(number: int, text: str):
    """Affiche une option de menu formatée"""
    print(f"{Colors.BLUE}{number}.{Colors.ENDC} {text}")

def print_status(label: str, status: bool):
    """Affiche un statut avec couleur selon l'état"""
    status_text = f"{Colors.GREEN}ACTIF{Colors.ENDC}" if status else f"{Colors.RED}INACTIF{Colors.ENDC}"
    print(f"{label}: {status_text}")

def format_duration(seconds: float) -> str:
    """Formate une durée en secondes en format lisible"""
    if seconds is None:
        return "N/A"
    
    minutes, seconds = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    
    if days > 0:
        return f"{days}j {hours}h {minutes}m {seconds}s"
    elif hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"

async def initialize_bot(config_path: Optional[str] = None):
    """
    Initialise les composants du bot
    
    Args:
        config_path: Chemin vers le fichier de configuration (optionnel)
    
    Returns:
        bool: True si l'initialisation a réussi, False sinon
    """
    try:
        logger.info("Initialisation du GBPBot en cours...")
        
        # Charger la configuration avec la fonction appropriée
        bot_state.config = get_config(config_path)
        
        # S'assurer que la configuration n'est pas None
        if bot_state.config is None:
            logger.error("Impossible de charger la configuration")
            return False
        
        # Initialiser les clients blockchain
        blockchains = bot_state.config.get("blockchains", {})
        for blockchain_name, blockchain_config in blockchains.items():
            if blockchain_config.get("enabled", False):
                logger.info(f"Initialisation de la blockchain {blockchain_name}...")
                client = BlockchainClientFactory.get_client(blockchain_name, blockchain_config)
                connected = await client.connect()
                
                if connected:
                    logger.info(f"Connexion réussie à {blockchain_name}")
                    bot_state.blockchain_clients[blockchain_name] = client
                else:
                    logger.error(f"Impossible de se connecter à {blockchain_name}")
        
        if not bot_state.blockchain_clients:
            logger.error("Aucune blockchain n'a pu être initialisée")
            return False
        
        logger.info("Initialisation terminée avec succès")
        return True
    
    except Exception as e:
        logger.exception(f"Erreur lors de l'initialisation: {e}")
        return False

async def start_arbitrage_module():
    """Démarre le module d'arbitrage"""
    if not bot_state.running:
        print(f"{Colors.RED}Le bot doit être démarré avant d'activer un module.{Colors.ENDC}")
        return
    
    try:
        print(f"{Colors.YELLOW}Démarrage du module d'arbitrage...{Colors.ENDC}")
        
        # Vérifier que la configuration existe
        if bot_state.config is None:
            print(f"{Colors.RED}Configuration non disponible{Colors.ENDC}")
            return
        
        # Obtenir la configuration pour l'arbitrage
        arbitrage_config = bot_state.config.get("strategies", {}).get("arbitrage", {})
        
        # Sélectionner la blockchain (par défaut Avalanche si disponible)
        blockchain_name = arbitrage_config.get("blockchain", "avalanche")
        blockchain_client = bot_state.blockchain_clients.get(
            blockchain_name, 
            next(iter(bot_state.blockchain_clients.values()), None)
        )
        
        if not blockchain_client:
            print(f"{Colors.RED}Aucun client blockchain disponible pour le module d'arbitrage{Colors.ENDC}")
            return
        
        # Créer et initialiser la stratégie d'arbitrage
        arbitrage_strategy = arbitrage.ArbitrageStrategy(blockchain_client, arbitrage_config)
        await arbitrage_strategy.initialize()
        
        # Stocker la stratégie et marquer le module comme actif
        bot_state.strategies["arbitrage"] = arbitrage_strategy
        bot_state.active_modules["arbitrage"] = True
        
        # Démarrer la recherche d'opportunités en arrière-plan
        # Note: Dans une implémentation réelle, cela devrait être une tâche asyncio
        # token_pairs = arbitrage_config.get("token_pairs", [])
        # asyncio.create_task(arbitrage_strategy.run(token_pairs))
        
        print(f"{Colors.GREEN}Module d'arbitrage démarré avec succès{Colors.ENDC}")
    
    except Exception as e:
        logger.exception(f"Erreur lors du démarrage du module d'arbitrage: {e}")
        print(f"{Colors.RED}Erreur lors du démarrage du module d'arbitrage: {str(e)}{Colors.ENDC}")

async def start_sniping_module():
    """Démarre le module de sniping"""
    if not bot_state.running:
        print(f"{Colors.RED}Le bot doit être démarré avant d'activer un module.{Colors.ENDC}")
        return
    
    try:
        print(f"{Colors.YELLOW}Démarrage du module de sniping...{Colors.ENDC}")
        
        # Vérifier que la configuration existe
        if bot_state.config is None:
            print(f"{Colors.RED}Configuration non disponible{Colors.ENDC}")
            return
        
        # Obtenir la configuration pour le sniping
        sniping_config = bot_state.config.get("strategies", {}).get("sniping", {})
        
        # Sélectionner la blockchain (priorité à Solana selon les spécifications)
        blockchain_name = sniping_config.get("blockchain", "solana")
        blockchain_client = bot_state.blockchain_clients.get(
            blockchain_name, 
            next(iter(bot_state.blockchain_clients.values()), None)
        )
        
        if not blockchain_client:
            print(f"{Colors.RED}Aucun client blockchain disponible pour le module de sniping{Colors.ENDC}")
            return
        
        # Créer et initialiser la stratégie de sniping
        sniping_strategy = sniping.SnipingStrategy(blockchain_client)
        
        # Stocker la stratégie et marquer le module comme actif
        bot_state.strategies["sniping"] = sniping_strategy
        bot_state.active_modules["sniping"] = True
        
        # Démarrer la surveillance en arrière-plan
        # Note: Dans une implémentation réelle, cela devrait être une tâche asyncio
        # asyncio.create_task(sniping_strategy.start_monitoring())
        
        print(f"{Colors.GREEN}Module de sniping démarré avec succès{Colors.ENDC}")
    
    except Exception as e:
        logger.exception(f"Erreur lors du démarrage du module de sniping: {e}")
        print(f"{Colors.RED}Erreur lors du démarrage du module de sniping: {str(e)}{Colors.ENDC}")

async def start_auto_module():
    """Démarre le mode automatique intelligent"""
    try:
        print(f"{Colors.BLUE}Initialisation du mode automatique...{Colors.ENDC}")
        
        if not bot_state.running:
            print(f"{Colors.RED}Erreur: Le bot doit être démarré avant d'activer le mode automatique.{Colors.ENDC}")
            input("Appuyez sur Entrée pour continuer...")
            return
        
        # Vérifier que les autres modules ne sont pas déjà actifs
        if bot_state.active_modules["arbitrage"] or bot_state.active_modules["sniping"]:
            print(f"{Colors.YELLOW}Attention: Les autres modules doivent être désactivés pour utiliser le mode automatique.{Colors.ENDC}")
            choice = input("Voulez-vous désactiver les autres modules et continuer? (o/n): ")
            if choice.lower() != "o":
                return
                
            # Désactiver les autres modules
            if bot_state.active_modules["arbitrage"]:
                await stop_module("arbitrage")
            if bot_state.active_modules["sniping"]:
                await stop_module("sniping")
        
        # Configurer et lancer le mode automatique
        from gbpbot.strategies.auto_mode import AutoModeStrategy
        
        # Récupérer le client blockchain depuis l'initialisation du bot
        blockchain_client = None
        try:
            from gbpbot.core import app_context
            blockchain_client = app_context.get_blockchain_client()
        except (ImportError, AttributeError) as e:
            logger.error(f"Impossible de récupérer le client blockchain: {e}")
            
        if blockchain_client is None:
            # Créer un client blockchain si on ne peut pas le récupérer du contexte
            try:
                from gbpbot.core.blockchain.base import BlockchainClient
                from gbpbot.utils.config import get_config
                
                config = get_config()
                blockchain_config = config.get("blockchain", {})
                blockchain_type = blockchain_config.get("default", "avalanche")
                
                # Créer une instance sans passer par la factory
                blockchain_client = BlockchainClient(blockchain_type, blockchain_config)
                await blockchain_client.initialize()
            except Exception as e:
                logger.error(f"Impossible de créer un client blockchain: {e}")
                print(f"{Colors.RED}Erreur: Impossible de créer un client blockchain.{Colors.ENDC}")
                input("Appuyez sur Entrée pour continuer...")
                return
        
        # Créer et initialiser la stratégie
        auto_strategy = AutoModeStrategy(blockchain_client)
        initialized = await auto_strategy.initialize()
        
        if not initialized:
            print(f"{Colors.RED}Erreur: Impossible d'initialiser le mode automatique.{Colors.ENDC}")
            input("Appuyez sur Entrée pour continuer...")
            return
            
        # Démarrer la stratégie
        success = await auto_strategy.start()
        
        if success:
            print(f"{Colors.GREEN}Mode automatique démarré avec succès!{Colors.ENDC}")
            bot_state.active_modules["auto_mode"] = True
            bot_state.module_instances["auto_mode"] = auto_strategy
        else:
            print(f"{Colors.RED}Erreur: Impossible de démarrer le mode automatique.{Colors.ENDC}")
            
        input("Appuyez sur Entrée pour continuer...")
            
    except Exception as e:
        print(f"{Colors.RED}Erreur lors du démarrage du mode automatique: {str(e)}{Colors.ENDC}")
        logger.exception("Erreur lors du démarrage du mode automatique")
        input("Appuyez sur Entrée pour continuer...")

async def stop_module(module_name: str):
    """Arrête un module spécifique"""
    if not bot_state.active_modules.get(module_name, False):
        print(f"{Colors.YELLOW}Le module {module_name} n'est pas actif.{Colors.ENDC}")
        return
    
    try:
        print(f"{Colors.YELLOW}Arrêt du module {module_name}...{Colors.ENDC}")
        
        # Récupérer la stratégie associée
        strategy = bot_state.strategies.get(module_name)
        
        if strategy and hasattr(strategy, "stop"):
            await strategy.stop()
        
        # Marquer le module comme inactif
        bot_state.active_modules[module_name] = False
        
        # Si on arrête le mode auto, on ne désactive pas les autres modules
        if module_name != "auto_mode":
            # Si on arrête un module et que le mode auto est actif, on désactive aussi le mode auto
            if bot_state.active_modules["auto_mode"]:
                bot_state.active_modules["auto_mode"] = False
                print(f"{Colors.YELLOW}Le mode automatique a été désactivé.{Colors.ENDC}")
        
        print(f"{Colors.GREEN}Module {module_name} arrêté avec succès{Colors.ENDC}")
    
    except Exception as e:
        logger.exception(f"Erreur lors de l'arrêt du module {module_name}: {e}")
        print(f"{Colors.RED}Erreur lors de l'arrêt du module {module_name}: {str(e)}{Colors.ENDC}")

async def display_main_menu():
    """Affiche le menu principal et traite les entrées utilisateur"""
    clear_screen()
    
    print(f"{Colors.HEADER}============================================================{Colors.ENDC}")
    print(f"{Colors.HEADER}                 GBPBot - Menu Principal                    {Colors.ENDC}")
    print(f"{Colors.HEADER}============================================================{Colors.ENDC}")
    
    if bot_state.running:
        uptime = format_duration(time.time() - bot_state.start_time) if bot_state.start_time is not None else "N/A"
        modules_actifs = sum(1 for active in bot_state.active_modules.values() if active)
        print(f"\n{Colors.GREEN}Bot en cours d'exécution (Actif depuis: {uptime}){Colors.ENDC}")
        print(f"{Colors.GREEN}Modules actifs: {modules_actifs}/{len(bot_state.active_modules)}{Colors.ENDC}")
        
        # Afficher l'état du bot Telegram s'il existe
        if "telegram_bot" in bot_state.strategies:
            telegram_bot = bot_state.strategies["telegram_bot"]
            if telegram_bot.running:
                print(f"{Colors.GREEN}Interface Telegram active{Colors.ENDC}")
            else:
                print(f"{Colors.YELLOW}Interface Telegram configurée mais inactive{Colors.ENDC}")
    else:
        print(f"\n{Colors.RED}Bot arrêté{Colors.ENDC}")
    
    print("\nVeuillez choisir une option:")
    print_menu_option(1, "Démarrer le Bot")
    print_menu_option(2, "Configurer les paramètres")
    print_menu_option(3, "Afficher la configuration actuelle")
    print_menu_option(4, "Statistiques et Logs")
    print_menu_option(5, "Afficher les Modules Disponibles")
    print_menu_option(6, "Machine Learning et Optimisation")
    print_menu_option(7, "Interface Telegram")
    print_menu_option(8, "Quitter")
    
    choice = input("\nVotre choix: ")
    
    if choice == "1":
        # Démarrer le bot
        if not bot_state.running:
            await initialize_bot()
            bot_state.start()
            print(f"{Colors.GREEN}Le bot a été démarré avec succès !{Colors.ENDC}")
            time.sleep(1)
        else:
            print(f"{Colors.YELLOW}Le bot est déjà en cours d'exécution.{Colors.ENDC}")
            time.sleep(1)
    
    elif choice == "2":
        # Configurer les paramètres
        print(f"{Colors.YELLOW}Cette fonctionnalité sera disponible dans une prochaine version.{Colors.ENDC}")
        input("Appuyez sur Entrée pour continuer...")
    
    elif choice == "3":
        # Afficher la configuration actuelle
        print(f"{Colors.YELLOW}Cette fonctionnalité sera disponible dans une prochaine version.{Colors.ENDC}")
        input("Appuyez sur Entrée pour continuer...")
    
    elif choice == "4":
        # Statistiques et Logs
        print(f"{Colors.YELLOW}Cette fonctionnalité sera disponible dans une prochaine version.{Colors.ENDC}")
        input("Appuyez sur Entrée pour continuer...")
    
    elif choice == "5":
        # Afficher les modules disponibles
        if not bot_state.running:
            print(f"{Colors.YELLOW}Veuillez démarrer le bot avant d'accéder aux modules.{Colors.ENDC}")
            input("Appuyez sur Entrée pour continuer...")
            return
        
        await display_modules_menu()
    
    elif choice == "6":
        # Machine Learning et Optimisation
        await display_ml_menu()
    
    elif choice == "7":
        # Interface Telegram
        await display_telegram_menu()
    
    elif choice == "8":
        # Quitter
        if bot_state.running:
            confirm = input(f"{Colors.YELLOW}Le bot est en cours d'exécution. Voulez-vous vraiment quitter? (o/n): {Colors.ENDC}")
            if confirm.lower() != "o":
                await display_main_menu()
                return
        print(f"{Colors.BLUE}Merci d'avoir utilisé GBPBot. À bientôt!{Colors.ENDC}")
        return
    
    else:
        print(f"{Colors.RED}Choix invalide. Veuillez réessayer.{Colors.ENDC}")
        time.sleep(1)
    
    # Afficher à nouveau le menu principal (récursion)
    await display_main_menu()

async def display_modules_menu():
    """Affiche le menu des modules"""
    clear_screen()
    
    print(f"{Colors.HEADER}============================================================{Colors.ENDC}")
    print(f"{Colors.HEADER}                 GBPBot - Sélection de Module               {Colors.ENDC}")
    print(f"{Colors.HEADER}============================================================{Colors.ENDC}")
    
    print_menu_option(1, "Arbitrage entre les DEX")
    print_menu_option(2, "Sniping de Token")
    print_menu_option(3, "Lancer automatiquement le bot")
    print_menu_option(4, "Sniping de Memecoins Solana (Spécialisé)")
    print_menu_option(5, "Frontrunning Solana (MEV)")
    print_menu_option(6, "Arbitrage Cross-DEX (Solana/Avalanche)")
    print_menu_option(7, "Retour au menu principal")
    
    print()
    print(f"{Colors.BOLD}Statut des modules:{Colors.ENDC}")
    print_status("Arbitrage", bot_state.active_modules["arbitrage"])
    print_status("Sniping", bot_state.active_modules["sniping"])
    print_status("Mode Auto", bot_state.active_modules["auto_mode"])
    print_status("Sniping Solana", bot_state.active_modules["solana_sniping"])
    print_status("Frontrunning Solana", bot_state.active_modules["solana_frontrun"])
    print_status("Arbitrage Cross-DEX", bot_state.active_modules["cross_dex_arbitrage"])
    
    choice = input("\nChoisissez une option (1-7): ")
    
    if choice == "1":
        await start_arbitrage_module()
    elif choice == "2":
        await start_sniping_module()
    elif choice == "3":
        await start_auto_module()
    elif choice == "4":
        await start_solana_sniping_module()
    elif choice == "5":
        await start_solana_frontrun_module()
    elif choice == "6":
        await start_cross_dex_arbitrage_module()
    elif choice == "7":
        return  # Retour au menu principal
    else:
        print(f"{Colors.RED}Option invalide. Veuillez réessayer.{Colors.ENDC}")
        time.sleep(1)
    
    # Afficher à nouveau le menu des modules
    await display_modules_menu()

async def start_solana_sniping_module():
    """Démarre le module de sniping spécialisé pour les memecoins Solana"""
    if not bot_state.running:
        print(f"{Colors.RED}Le bot doit être démarré avant d'activer un module.{Colors.ENDC}")
        return
    
    try:
        print(f"{Colors.YELLOW}Démarrage du module de sniping Solana...{Colors.ENDC}")
        
        # Vérifier que la configuration existe
        if bot_state.config is None:
            print(f"{Colors.RED}Configuration non disponible{Colors.ENDC}")
            return
        
        # Obtenir la configuration pour le sniping Solana
        solana_config = bot_state.config.get("solana", {})
        
        # Créer et initialiser l'intégration du sniper Solana
        solana_sniper = SolanaSnipingIntegration(config=solana_config)
        
        # Démarrer le sniper
        success = await solana_sniper.start()
        
        if success:
            # Stocker l'intégration et marquer le module comme actif
            bot_state.strategies["solana_sniping"] = solana_sniper
            bot_state.active_modules["solana_sniping"] = True
            
            print(f"{Colors.GREEN}Module de sniping Solana démarré avec succès{Colors.ENDC}")
            print(f"{Colors.BLUE}Surveillance active des nouveaux memecoins sur Solana...{Colors.ENDC}")
        else:
            print(f"{Colors.RED}Échec du démarrage du module de sniping Solana{Colors.ENDC}")
    
    except Exception as e:
        logger.exception(f"Erreur lors du démarrage du module de sniping Solana: {e}")
        print(f"{Colors.RED}Erreur lors du démarrage du module de sniping Solana: {str(e)}{Colors.ENDC}")

async def start_solana_frontrun_module():
    """Démarre le module de frontrunning Solana (MEV)"""
    if not bot_state.running:
        print(f"{Colors.RED}Le bot doit être démarré avant d'activer un module.{Colors.ENDC}")
        return
    
    try:
        print(f"{Colors.YELLOW}Démarrage du module de frontrunning Solana...{Colors.ENDC}")
        
        # Vérifier que la configuration existe
        if bot_state.config is None:
            print(f"{Colors.RED}Configuration non disponible{Colors.ENDC}")
            return
        
        # Obtenir la configuration pour Solana
        solana_config = bot_state.config.get("solana", {})
        
        # Importer la stratégie de frontrunning
        try:
            from gbpbot.strategies.solana_frontrun import create_solana_frontrun_strategy
        except ImportError as e:
            print(f"{Colors.RED}Erreur lors de l'importation du module de frontrunning: {str(e)}{Colors.ENDC}")
            return
        
        # Créer et initialiser la stratégie de frontrunning
        frontrun_strategy = create_solana_frontrun_strategy(config=solana_config)
        
        # Démarrer la stratégie
        success = await frontrun_strategy.start()
        
        if success:
            # Stocker la stratégie et marquer le module comme actif
            bot_state.strategies["solana_frontrun"] = frontrun_strategy
            bot_state.active_modules["solana_frontrun"] = True
            
            print(f"{Colors.GREEN}Module de frontrunning Solana démarré avec succès{Colors.ENDC}")
            print(f"{Colors.BLUE}Surveillance active du mempool Solana pour les opportunités MEV...{Colors.ENDC}")
        else:
            print(f"{Colors.RED}Échec du démarrage du module de frontrunning Solana{Colors.ENDC}")
    
    except Exception as e:
        logger.exception(f"Erreur lors du démarrage du module de frontrunning Solana: {e}")
        print(f"{Colors.RED}Erreur lors du démarrage du module de frontrunning Solana: {str(e)}{Colors.ENDC}")

async def start_cross_dex_arbitrage_module():
    """Démarre le module d'arbitrage cross-DEX"""
    if not bot_state.running:
        print(f"{Colors.RED}Le bot doit être démarré avant d'activer un module.{Colors.ENDC}")
        return
    
    try:
        print(f"{Colors.YELLOW}Démarrage du module d'arbitrage Cross-DEX...{Colors.ENDC}")
        
        # Vérifier que la configuration existe
        if bot_state.config is None:
            print(f"{Colors.RED}Configuration non disponible{Colors.ENDC}")
            return
        
        # Obtenir la configuration pour l'arbitrage
        arbitrage_config = bot_state.config.get("arbitrage", {})
        
        # Importer la stratégie d'arbitrage cross-DEX
        try:
            from gbpbot.strategies.cross_dex_arbitrage import create_cross_dex_arbitrage_strategy
        except ImportError as e:
            print(f"{Colors.RED}Erreur lors de l'importation du module d'arbitrage Cross-DEX: {str(e)}{Colors.ENDC}")
            return
        
        # Créer et initialiser la stratégie d'arbitrage
        arbitrage_strategy = create_cross_dex_arbitrage_strategy(
            blockchain_clients=bot_state.blockchain_clients,
            config=arbitrage_config
        )
        
        # Démarrer la stratégie
        success = await arbitrage_strategy.start()
        
        if success:
            # Stocker la stratégie et marquer le module comme actif
            bot_state.strategies["cross_dex_arbitrage"] = arbitrage_strategy
            bot_state.active_modules["cross_dex_arbitrage"] = True
            
            print(f"{Colors.GREEN}Module d'arbitrage Cross-DEX démarré avec succès{Colors.ENDC}")
            print(f"{Colors.BLUE}Surveillance active des opportunités d'arbitrage entre DEX...{Colors.ENDC}")
        else:
            print(f"{Colors.RED}Échec du démarrage du module d'arbitrage Cross-DEX{Colors.ENDC}")
    
    except Exception as e:
        logger.exception(f"Erreur lors du démarrage du module d'arbitrage Cross-DEX: {e}")
        print(f"{Colors.RED}Erreur lors du démarrage du module d'arbitrage Cross-DEX: {str(e)}{Colors.ENDC}")

async def display_ml_menu():
    """Affiche le menu de Machine Learning et Optimisation"""
    clear_screen()
    
    print(f"{Colors.HEADER}============================================================{Colors.ENDC}")
    print(f"{Colors.HEADER}           GBPBot - Machine Learning et Optimisation        {Colors.ENDC}")
    print(f"{Colors.HEADER}============================================================{Colors.ENDC}")
    
    # Vérifier que le bot est démarré
    if not bot_state.running:
        print(f"{Colors.RED}Le bot doit être démarré pour utiliser ces fonctionnalités.{Colors.ENDC}")
        input("\nAppuyez sur Entrée pour revenir au menu principal...")
        return
    
    # Essayer d'importer le module ML
    try:
        from gbpbot.machine_learning import MLIntegrator, create_ml_integrator
        ml_available = True
    except ImportError:
        ml_available = False
    
    if not ml_available:
        print(f"{Colors.RED}Les modules de Machine Learning ne sont pas disponibles.{Colors.ENDC}")
        print(f"{Colors.RED}Vérifiez que scikit-learn, numpy et pandas sont installés.{Colors.ENDC}")
        input("\nAppuyez sur Entrée pour revenir au menu principal...")
        return
    
    # Vérifier si un intégrateur ML existe déjà dans le bot
    if "ml_integrator" not in bot_state.strategies:
        # Créer un nouvel intégrateur ML
        try:
            ml_integrator = create_ml_integrator(config=bot_state.config)
            bot_state.strategies["ml_integrator"] = ml_integrator
        except Exception as e:
            print(f"{Colors.RED}Erreur lors de l'initialisation du ML: {str(e)}{Colors.ENDC}")
            input("\nAppuyez sur Entrée pour revenir au menu principal...")
            return
    else:
        ml_integrator = bot_state.strategies["ml_integrator"]
    
    # Afficher le statut actuel du ML
    ml_enabled = ml_integrator.is_enabled() if ml_integrator else False
    ml_status = "Activé" if ml_enabled else "Désactivé"
    print(f"\nStatut du Machine Learning: {Colors.GREEN if ml_enabled else Colors.RED}{ml_status}{Colors.ENDC}")
    
    # Afficher les options du menu
    print("\nOptions de Machine Learning:")
    print_menu_option(1, f"{'Désactiver' if ml_enabled else 'Activer'} le Machine Learning")
    print_menu_option(2, "Afficher les statistiques du modèle")
    print_menu_option(3, "Forcer l'entraînement des modèles")
    print_menu_option(4, "Configurer les paramètres ML")
    print_menu_option(5, "Retour au menu principal")
    
    choice = input("\nVotre choix: ")
    
    if choice == "1":
        # Activer/désactiver le ML
        if ml_enabled:
            # Désactiver le ML
            if "ML_ENABLED" in bot_state.config:
                bot_state.config["ML_ENABLED"] = "false"
            else:
                bot_state.config["ML_ENABLED"] = "false"
            
            # Recréer l'intégrateur
            ml_integrator = create_ml_integrator(config=bot_state.config)
            bot_state.strategies["ml_integrator"] = ml_integrator
            
            print(f"{Colors.YELLOW}Machine Learning désactivé.{Colors.ENDC}")
        else:
            # Activer le ML
            if "ML_ENABLED" in bot_state.config:
                bot_state.config["ML_ENABLED"] = "true"
            else:
                bot_state.config["ML_ENABLED"] = "true"
            
            # Recréer l'intégrateur
            ml_integrator = create_ml_integrator(config=bot_state.config)
            bot_state.strategies["ml_integrator"] = ml_integrator
            
            print(f"{Colors.GREEN}Machine Learning activé.{Colors.ENDC}")
        
        time.sleep(1)
    
    elif choice == "2":
        # Afficher les statistiques
        if not ml_integrator or not ml_integrator.is_enabled():
            print(f"{Colors.YELLOW}Machine Learning désactivé. Aucune statistique disponible.{Colors.ENDC}")
        else:
            stats = ml_integrator.get_ml_stats()
            
            print(f"\n{Colors.BOLD}Statistiques des modèles de Machine Learning:{Colors.ENDC}")
            
            # Afficher les modèles disponibles
            print("\nModèles disponibles:")
            for strategy, available in stats.get("models_available", {}).items():
                status = f"{Colors.GREEN}Disponible{Colors.ENDC}" if available else f"{Colors.RED}Non disponible{Colors.ENDC}"
                print(f"  - {strategy.capitalize()}: {status}")
            
            # Afficher les compteurs de données
            print("\nDonnées d'entraînement:")
            for strategy, count in stats.get("data_counts", {}).items():
                print(f"  - {strategy.capitalize()}: {count} échantillons")
            
            # Afficher les dates de dernier entraînement
            print("\nDernier entraînement:")
            for strategy, date in stats.get("last_training", {}).items():
                print(f"  - {strategy.capitalize()}: {date}")
            
            # Afficher les performances récentes
            if "recent_performance" in stats:
                print("\nPerformances récentes:")
                for strategy, perf in stats.get("recent_performance", {}).items():
                    if perf["count"] > 0:
                        success_rate = perf["success_rate"]
                        success_color = Colors.GREEN if success_rate > 60 else Colors.YELLOW if success_rate > 40 else Colors.RED
                        print(f"  - {strategy.capitalize()} ({perf['count']} transactions):")
                        print(f"      Taux de succès: {success_color}{success_rate}%{Colors.ENDC}")
                        print(f"      Profit moyen: ${perf['avg_profit']:.2f}")
                        print(f"      Profit total: ${perf['total_profit']:.2f}")
            
            # Afficher la configuration
            if "config" in stats:
                print("\nConfiguration ML:")
                for key, value in stats.get("config", {}).items():
                    print(f"  - {key}: {value}")
        
        input("\nAppuyez sur Entrée pour continuer...")
    
    elif choice == "3":
        # Forcer l'entraînement des modèles
        if not ml_integrator or not ml_integrator.is_enabled():
            print(f"{Colors.YELLOW}Machine Learning désactivé. Impossible d'entraîner les modèles.{Colors.ENDC}")
            time.sleep(1)
        else:
            print(f"{Colors.YELLOW}Entraînement des modèles en cours... (cela peut prendre un moment){Colors.ENDC}")
            
            # Essayer d'accéder directement au modèle de prédiction
            success = False
            try:
                if ml_integrator.prediction_model:
                    for strategy in ["sniping", "frontrun", "arbitrage"]:
                        print(f"Entraînement du modèle {strategy}...")
                        # On pourrait exécuter ici l'entraînement dans un thread ou une tâche asyncio
                        # Pour la simplicité, on le fait de manière synchrone
                        success = ml_integrator.prediction_model.train_model(strategy)
                        if success:
                            print(f"{Colors.GREEN}Modèle {strategy} entraîné avec succès !{Colors.ENDC}")
                        else:
                            print(f"{Colors.YELLOW}Pas assez de données pour entraîner le modèle {strategy}.{Colors.ENDC}")
                    success = True
            except Exception as e:
                print(f"{Colors.RED}Erreur lors de l'entraînement des modèles: {str(e)}{Colors.ENDC}")
            
            if success:
                print(f"{Colors.GREEN}Entraînement terminé !{Colors.ENDC}")
            
            time.sleep(2)
    
    elif choice == "4":
        # Configurer les paramètres ML
        print("\nParamètres de Machine Learning:")
        
        # Afficher les paramètres actuels
        ml_params = {k: v for k, v in bot_state.config.items() if k.startswith("ML_")}
        if not ml_params:
            ml_params = {
                "ML_ENABLED": "true",
                "ML_MODEL_PATH": "models/gbpbot_ml.pkl",
                "PREDICTION_CONFIDENCE_THRESHOLD": "0.7",
                "MIN_TRAINING_SAMPLES": "100",
                "RETRAINING_INTERVAL_HOURS": "24"
            }
        
        for i, (key, value) in enumerate(ml_params.items(), 1):
            print(f"{i}. {key} = {value}")
        
        print(f"{len(ml_params) + 1}. Retour")
        
        # Demander quel paramètre modifier
        param_choice = input("\nQuel paramètre souhaitez-vous modifier? (1-" + str(len(ml_params) + 1) + "): ")
        
        try:
            param_index = int(param_choice) - 1
            if param_index < 0 or param_index >= len(ml_params) + 1:
                raise ValueError("Choix hors limites")
                
            if param_index == len(ml_params):
                # Option "Retour"
                pass
            else:
                # Modifier le paramètre sélectionné
                param_key = list(ml_params.keys())[param_index]
                new_value = input(f"Nouvelle valeur pour {param_key} (actuelle: {ml_params[param_key]}): ")
                
                # Mettre à jour la configuration
                bot_state.config[param_key] = new_value
                
                # Recréer l'intégrateur ML si nécessaire
                if param_key == "ML_ENABLED" or param_key == "ML_MODEL_PATH":
                    ml_integrator = create_ml_integrator(config=bot_state.config)
                    bot_state.strategies["ml_integrator"] = ml_integrator
                
                print(f"{Colors.GREEN}Paramètre {param_key} mis à jour avec succès !{Colors.ENDC}")
                time.sleep(1)
        except (ValueError, IndexError):
            print(f"{Colors.RED}Choix invalide.{Colors.ENDC}")
            time.sleep(1)
    
    elif choice == "5":
        # Retour au menu principal
        return
    
    else:
        print(f"{Colors.RED}Choix invalide. Veuillez réessayer.{Colors.ENDC}")
        time.sleep(1)
    
    # Afficher à nouveau le menu ML (récursion)
    await display_ml_menu()

async def display_telegram_menu():
    """Affiche le menu de configuration et gestion du bot Telegram"""
    clear_screen()
    
    print(f"{Colors.HEADER}============================================================{Colors.ENDC}")
    print(f"{Colors.HEADER}           GBPBot - Interface Telegram                      {Colors.ENDC}")
    print(f"{Colors.HEADER}============================================================{Colors.ENDC}")
    
    # Vérifier que le bot est démarré
    if not bot_state.running:
        print(f"{Colors.RED}Le bot doit être démarré pour utiliser l'interface Telegram.{Colors.ENDC}")
        input("\nAppuyez sur Entrée pour revenir au menu principal...")
        return
    
    # Essayer d'importer le module Telegram
    try:
        from gbpbot.telegram_bot import create_telegram_bot
        telegram_available = True
    except ImportError:
        telegram_available = False
    
    if not telegram_available:
        print(f"{Colors.RED}Le module Telegram n'est pas disponible.{Colors.ENDC}")
        print(f"{Colors.RED}Installez python-telegram-bot avec: pip install python-telegram-bot{Colors.ENDC}")
        input("\nAppuyez sur Entrée pour revenir au menu principal...")
        return
    
    # Vérifier si un bot Telegram existe déjà
    telegram_bot = None
    if "telegram_bot" in bot_state.strategies:
        telegram_bot = bot_state.strategies["telegram_bot"]
        is_running = telegram_bot.running
    else:
        is_running = False
    
    # Afficher le statut actuel
    status = "Actif" if is_running else "Inactif"
    print(f"\nStatut de l'interface Telegram: {Colors.GREEN if is_running else Colors.RED}{status}{Colors.ENDC}")
    
    # Récupérer la configuration Telegram
    telegram_token = bot_state.config.get("TELEGRAM_BOT_TOKEN", "")
    authorized_users = bot_state.config.get("TELEGRAM_AUTHORIZED_USERS", "")
    
    # Afficher la configuration
    print("\nConfiguration actuelle:")
    print(f"Token: {telegram_token[:6] + '...' if telegram_token else 'Non configuré'}")
    print(f"Utilisateurs autorisés: {authorized_users or 'Aucun (tout le monde pourra utiliser le bot)'}")
    
    # Afficher les options
    print("\nOptions:")
    print_menu_option(1, f"{'Arrêter' if is_running else 'Démarrer'} l'interface Telegram")
    print_menu_option(2, "Configurer le token Telegram")
    print_menu_option(3, "Configurer les utilisateurs autorisés")
    print_menu_option(4, "Tester l'envoi d'un message")
    print_menu_option(5, "Configurer les notifications")
    print_menu_option(6, "Retour au menu principal")
    
    choice = input("\nVotre choix: ")
    
    if choice == "1":
        # Démarrer/arrêter l'interface Telegram
        if is_running:
            print(f"{Colors.YELLOW}Arrêt de l'interface Telegram...{Colors.ENDC}")
            try:
                # Créer une tâche asyncio pour arrêter le bot
                await telegram_bot.stop()
                print(f"{Colors.GREEN}Interface Telegram arrêtée avec succès!{Colors.ENDC}")
            except Exception as e:
                print(f"{Colors.RED}Erreur lors de l'arrêt de l'interface Telegram: {str(e)}{Colors.ENDC}")
        else:
            # Vérifier que le token est configuré
            if not telegram_token:
                print(f"{Colors.RED}Le token Telegram n'est pas configuré.{Colors.ENDC}")
                print(f"{Colors.RED}Utilisez l'option 2 pour configurer le token.{Colors.ENDC}")
                time.sleep(2)
                await display_telegram_menu()
                return
                
            print(f"{Colors.YELLOW}Démarrage de l'interface Telegram...{Colors.ENDC}")
            try:
                # Créer une nouvelle instance du bot Telegram
                telegram_bot = create_telegram_bot(token=telegram_token, config=bot_state.config, bot_state=bot_state)
                
                # Démarrer le bot
                success = await telegram_bot.start()
                
                if success:
                    # Stocker le bot dans l'état du bot
                    bot_state.strategies["telegram_bot"] = telegram_bot
                    print(f"{Colors.GREEN}Interface Telegram démarrée avec succès!{Colors.ENDC}")
                    print(f"{Colors.GREEN}Vous pouvez maintenant contrôler le bot via Telegram.{Colors.ENDC}")
                else:
                    print(f"{Colors.RED}Échec du démarrage de l'interface Telegram.{Colors.ENDC}")
            except Exception as e:
                print(f"{Colors.RED}Erreur lors du démarrage de l'interface Telegram: {str(e)}{Colors.ENDC}")
        
        time.sleep(2)
    
    elif choice == "2":
        # Configurer le token
        print("\nPour obtenir un token Telegram, vous devez créer un bot avec @BotFather sur Telegram.")
        print("Envoyez /newbot à @BotFather et suivez les instructions.")
        
        new_token = input("\nEntrez votre token Telegram (laissez vide pour conserver la valeur actuelle): ")
        
        if new_token:
            # Mettre à jour la configuration
            bot_state.config["TELEGRAM_BOT_TOKEN"] = new_token
            print(f"{Colors.GREEN}Token Telegram mis à jour avec succès!{Colors.ENDC}")
            
            # Si le bot est en cours d'exécution, le redémarrer
            if is_running and telegram_bot:
                print(f"{Colors.YELLOW}Redémarrage de l'interface Telegram...{Colors.ENDC}")
                await telegram_bot.stop()
                
                # Créer une nouvelle instance du bot
                telegram_bot = create_telegram_bot(token=new_token, config=bot_state.config, bot_state=bot_state)
                
                # Démarrer le bot
                success = await telegram_bot.start()
                
                if success:
                    bot_state.strategies["telegram_bot"] = telegram_bot
                    print(f"{Colors.GREEN}Interface Telegram redémarrée avec succès!{Colors.ENDC}")
                else:
                    print(f"{Colors.RED}Échec du redémarrage de l'interface Telegram.{Colors.ENDC}")
        
        time.sleep(2)
    
    elif choice == "3":
        # Configurer les utilisateurs autorisés
        print("\nEntrez les IDs des utilisateurs autorisés, séparés par des virgules.")
        print("Vous pouvez obtenir votre ID en envoyant un message à @userinfobot sur Telegram.")
        print("Laissez vide pour autoriser tout le monde.")
        
        new_users = input("\nUtilisateurs autorisés: ")
        
        # Mettre à jour la configuration
        bot_state.config["TELEGRAM_AUTHORIZED_USERS"] = new_users
        print(f"{Colors.GREEN}Utilisateurs autorisés mis à jour avec succès!{Colors.ENDC}")
        
        # Si le bot est en cours d'exécution, recharger la configuration
        if is_running and telegram_bot:
            telegram_bot._load_authorized_users()
            print(f"{Colors.GREEN}Configuration rechargée avec succès!{Colors.ENDC}")
        
        time.sleep(2)
    
    elif choice == "4":
        # Tester l'envoi d'un message
        if not is_running or not telegram_bot:
            print(f"{Colors.RED}L'interface Telegram n'est pas active.{Colors.ENDC}")
            print(f"{Colors.RED}Démarrez-la d'abord avec l'option 1.{Colors.ENDC}")
            time.sleep(2)
            await display_telegram_menu()
            return
            
        test_message = input("\nEntrez le message de test à envoyer: ")
        
        if test_message:
            print(f"{Colors.YELLOW}Envoi du message de test...{Colors.ENDC}")
            
            success = await telegram_bot.send_message(test_message)
            
            if success:
                print(f"{Colors.GREEN}Message envoyé avec succès!{Colors.ENDC}")
            else:
                print(f"{Colors.RED}Échec de l'envoi du message.{Colors.ENDC}")
                print(f"{Colors.RED}Vérifiez que vous avez configuré les utilisateurs autorisés et que vous avez démarré une conversation avec le bot.{Colors.ENDC}")
        
        time.sleep(2)
    
    elif choice == "5":
        # Configurer les notifications
        print("\nConfiguration des notifications Telegram:")
        print("1. Alertes de profit")
        print("2. Alertes d'erreur")
        print("3. Alertes de sécurité")
        print("4. Toutes les notifications")
        print("5. Aucune notification")
        
        notif_choice = input("\nChoisissez une option (1-5): ")
        
        # Configuration des notifications
        if notif_choice in ["1", "2", "3", "4", "5"]:
            notifications = {
                "profit": notif_choice in ["1", "4"],
                "error": notif_choice in ["2", "4"],
                "security": notif_choice in ["3", "4"],
                "all": notif_choice == "4",
                "none": notif_choice == "5"
            }
            
            # Mettre à jour la configuration
            bot_state.config["TELEGRAM_NOTIFICATIONS"] = json.dumps(notifications)
            print(f"{Colors.GREEN}Configuration des notifications mise à jour avec succès!{Colors.ENDC}")
        else:
            print(f"{Colors.RED}Option invalide.{Colors.ENDC}")
        
        time.sleep(2)
    
    elif choice == "6":
        # Retour au menu principal
        return
    
    else:
        print(f"{Colors.RED}Option invalide. Veuillez réessayer.{Colors.ENDC}")
        time.sleep(1)
    
    # Afficher à nouveau le menu Telegram
    await display_telegram_menu()

async def main():
    """Fonction principale"""
    # Créer le répertoire de logs si nécessaire
    os.makedirs("logs", exist_ok=True)
    
    # Afficher le menu principal
    await display_main_menu()

if __name__ == "__main__":
    try:
        # Exécuter la fonction principale de manière asynchrone
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgramme interrompu. Arrêt du GBPBot...")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"Erreur inattendue: {e}")
        print(f"\nUne erreur inattendue s'est produite: {str(e)}")
        sys.exit(1) 