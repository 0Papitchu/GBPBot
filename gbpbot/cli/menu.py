#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Menu principal de l'interface CLI du GBPBot
===========================================

Ce module gère l'affichage du menu principal et la navigation entre les différentes
fonctionnalités du GBPBot via l'interface en ligne de commande.
"""

import os
import sys
import time
import logging
import asyncio
from typing import Dict, List, Optional, Any, Union, Callable, cast, Awaitable
from datetime import datetime

# Configuration du logging
logger = logging.getLogger("gbpbot.cli.menu")

# Variables pour suivre l'état des importations
commands_imported = False

# Importer les commandes avec gestion des erreurs
try:
    from gbpbot.cli.commands import (
        start_arbitrage_module,
        stop_module
    )
    from gbpbot.cli.display import (
        clear_screen,
        print_banner,
        print_header,
        print_menu_option,
        print_status
    )
    
    # Définir des fonctions de remplacement si les modules ne sont pas importés
    if not 'start_sniping_module' in locals():
        async def start_sniping_module(*args, **kwargs):
            logger.warning("Module de sniping non disponible")
            print("Module de sniping non disponible. Vérifiez l'installation du module.")
            await asyncio.sleep(2)
            return False
            
    if not 'start_backtesting_module' in locals():
        async def start_backtesting_module(*args, **kwargs):
            logger.warning("Module de backtesting non disponible")
            print("Module de backtesting non disponible. Vérifiez l'installation du module.")
            await asyncio.sleep(2)
            return False
            
    if not 'start_ai_assistant_module' in locals():
        async def start_ai_assistant_module(*args, **kwargs):
            logger.warning("Module d'assistant IA non disponible")
            print("Module d'assistant IA non disponible. Vérifiez l'installation du module.")
            await asyncio.sleep(2)
            return False
    
    # Importation des sous-menus avec gestion des erreurs
    try:
        from gbpbot.cli.commands.arbitrage import display_arbitrage_menu
    except ImportError:
        async def display_arbitrage_menu(*args, **kwargs):
            print_header("Module d'arbitrage")
            print("Ce module n'est pas disponible dans cette installation.")
            await asyncio.sleep(2)
            return
    
    try:
        from gbpbot.cli.commands.sniping import display_sniping_menu
    except ImportError:
        async def display_sniping_menu(*args, **kwargs):
            print_header("Module de sniping")
            print("Ce module n'est pas disponible dans cette installation.")
            await asyncio.sleep(2)
            return
    
    try:
        from gbpbot.cli.commands.auto_mode import display_auto_mode_menu
    except ImportError:
        async def display_auto_mode_menu(*args, **kwargs):
            print_header("Module automatique")
            print("Ce module n'est pas disponible dans cette installation.")
            await asyncio.sleep(2)
            return
    
    try:
        from gbpbot.cli.commands.ai import display_ai_menu
    except ImportError:
        async def display_ai_menu(*args, **kwargs):
            print_header("Assistant IA")
            print("Ce module n'est pas disponible dans cette installation.")
            await asyncio.sleep(2)
            return
    
    try:
        from gbpbot.cli.commands.backtesting import display_backtesting_menu
    except ImportError:
        async def display_backtesting_menu(*args, **kwargs):
            print_header("Module de backtesting")
            print("Ce module n'est pas disponible dans cette installation.")
            await asyncio.sleep(2)
            return
    
    try:
        from gbpbot.cli.commands.config import display_config_menu
    except ImportError:
        async def display_config_menu(*args, **kwargs):
            print_header("Configuration")
            print("Ce module n'est pas disponible dans cette installation.")
            await asyncio.sleep(2)
            return
    
    try:
        from gbpbot.cli.commands.stats import display_stats_menu
    except ImportError:
        async def display_stats_menu(*args, **kwargs):
            print_header("Statistiques et logs")
            print("Ce module n'est pas disponible dans cette installation.")
            await asyncio.sleep(2)
            return
    
    try:
        from gbpbot.cli.commands.wallet import display_wallet_menu
    except ImportError:
        async def display_wallet_menu(*args, **kwargs):
            print_header("Gestion des wallets")
            print("Ce module n'est pas disponible dans cette installation.")
            await asyncio.sleep(2)
            return
    
    try:
        from gbpbot.cli.commands.auto_optimization import display_auto_optimization_menu
    except ImportError:
        async def display_auto_optimization_menu(*args, **kwargs):
            print_header("Optimisation automatique")
            print("Ce module n'est pas disponible dans cette installation.")
            await asyncio.sleep(2)
            return
    
    commands_imported = True
except ImportError as e:
    logger.error(f"Erreur lors de l'importation des commandes: {e}")
    commands_imported = False
    
    # Définir des fonctions de remplacement pour éviter les erreurs
    async def dummy_function(*args, **kwargs):
        print("Cette fonctionnalité n'est pas disponible en raison d'une erreur d'importation.")
        print("Vérifiez les logs pour plus d'informations.")
        await asyncio.sleep(2)
        return None
    
    # Remplacer les fonctions manquantes par des fonctions factices
    start_arbitrage_module = dummy_function
    start_sniping_module = dummy_function
    start_backtesting_module = dummy_function
    start_ai_assistant_module = dummy_function
    stop_module = dummy_function
    
    # Fonctions d'affichage de base
    def clear_screen():
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def print_banner():
        print("""
    ██████╗ ██████╗ ██████╗ ██████╗  ██████╗ ████████╗
    ██╔════╝ ██╔══██╗██╔══██╗██╔══██╗██╔═══██╗╚══██╔══╝
    ██║  ███╗██████╔╝██████╔╝██████╔╝██║   ██║   ██║   
    ██║   ██║██╔══██╗██╔═══╝ ██╔══██╗██║   ██║   ██║   
    ╚██████╔╝██████╔╝██║     ██████╔╝╚██████╔╝   ██║   
     ╚═════╝ ╚═════╝ ╚═╝     ╚═════╝  ╚═════╝    ╚═╝   
    ============================================================
    Bot de Trading Optimisé pour PC Local
    ============================================================
        """)
    
    def print_header(text):
        print(f"\n--- {text} ---\n")
    
    def print_menu_option(idx, text):
        print(f"{idx}. {text}")
    
    def print_status(text, status="info"):
        status_prefix = {
            "info": "[INFO]",
            "success": "[SUCCÈS]",
            "warning": "[ATTENTION]",
            "error": "[ERREUR]"
        }.get(str(status).lower(), "[INFO]")
        print(f"{status_prefix} {text}")
    
    # Remplacer les sous-menus manquants par des fonctions factices asynchrones
    display_arbitrage_menu = dummy_function
    display_sniping_menu = dummy_function
    display_auto_mode_menu = dummy_function
    display_ai_menu = dummy_function
    display_backtesting_menu = dummy_function
    display_config_menu = dummy_function
    display_stats_menu = dummy_function
    display_wallet_menu = dummy_function
    display_auto_optimization_menu = dummy_function


class Colors:
    """Couleurs ANSI pour le terminal"""
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    HEADER = '\033[95m'


async def display_main_menu(bot_context: Dict[str, Any]) -> None:
    """
    Affiche le menu principal et gère la navigation entre les différentes fonctionnalités.
    
    Args:
        bot_context: Contexte du bot contenant l'état actuel et les configurations
    """
    running = True
    
    while running:
        clear_screen()
        display_banner()
        display_bot_status(bot_context)
        
        print_header("Menu Principal")
        
        print_menu_option(1, "Démarrer le Bot")
        print_menu_option(2, "Configurer les paramètres")
        print_menu_option(3, "Afficher la configuration actuelle")
        print_menu_option(4, "Statistiques et Logs")
        print_menu_option(5, "Afficher les Modules Disponibles")
        print_menu_option(6, "Quitter")
        
        print()
        choice = input("Entrez votre choix (1-6): ")
        
        if choice == "1":
            # Menu de sélection de module
            clear_screen()
            print_header("Sélection de Module")
            
            print_menu_option(1, "Arbitrage entre les DEX")
            print_menu_option(2, "Sniping de Token")
            print_menu_option(3, "Lancer automatiquement le bot")
            print_menu_option(4, "AI Assistant")
            print_menu_option(5, "Backtesting et Simulation")
            print_menu_option(6, "Retour au menu principal")
            
            print()
            module_choice = input("Entrez votre choix (1-6): ")
            
            if module_choice == "1":
                await display_arbitrage_menu(bot_context)
            elif module_choice == "2":
                await display_sniping_menu(bot_context)
            elif module_choice == "3":
                await display_auto_mode_menu(bot_context)
            elif module_choice == "4":
                await display_ai_menu(bot_context)
            elif module_choice == "5":
                await display_backtesting_menu(bot_context)
            # Si 6 ou autre, retour au menu principal
            
        elif choice == "2":
            # Configuration des paramètres
            await display_config_menu(bot_context)
            
        elif choice == "3":
            # Afficher la configuration actuelle
            clear_screen()
            print_header("Configuration Actuelle")
            
            # Afficher la configuration
            config = bot_context.get("config", {})
            for key, value in config.items():
                if isinstance(value, dict):
                    print(f"\n{key}:")
                    for subkey, subvalue in value.items():
                        print(f"  {subkey}: {subvalue}")
                else:
                    print(f"{key}: {value}")
            
            input("\nAppuyez sur Entrée pour continuer...")
            
        elif choice == "4":
            # Statistiques et logs
            await display_stats_menu(bot_context)
            
        elif choice == "5":
            # Afficher les modules disponibles
            clear_screen()
            print_header("Modules Disponibles")
            
            modules = bot_context.get("available_modules", [])
            if modules:
                for i, module in enumerate(modules, 1):
                    status = "Actif" if module.get("active", False) else "Inactif"
                    print_menu_option(i, f"{module['name']} - {status}")
            else:
                print_status("Aucun module disponible", "warning")
            
            input("\nAppuyez sur Entrée pour continuer...")
            
        elif choice == "6":
            # Quitter
            if confirm_exit():
                running = False
                print_status("Fermeture du GBPBot...", "info")
                
                # Arrêter les modules actifs
                active_modules = bot_context.get("active_modules", [])
                for module in active_modules:
                    print_status(f"Arrêt du module {module['name']}...", "info")
                    # Appeler la fonction d'arrêt du module
                    if "stop_function" in module and callable(module["stop_function"]):
                        try:
                            # Si c'est une coro, l'exécuter avec await, sinon l'appeler directement
                            stop_func = module["stop_function"]
                            if asyncio.iscoroutinefunction(stop_func):
                                await stop_func()
                            else:
                                stop_func()
                        except Exception as e:
                            print_status(f"Erreur lors de l'arrêt du module {module['name']}: {e}", "error")
                
                print_status("GBPBot fermé avec succès", "success")
        else:
            print_status("Option invalide. Veuillez entrer un nombre entre 1 et 6.", "error")
            time.sleep(1)


def display_banner() -> None:
    """Affiche la bannière du GBPBot"""
    banner = f"""
{Colors.BLUE}{Colors.BOLD}    ██████╗ ██████╗ ██████╗ ██████╗  ██████╗ ████████╗
    ██╔════╝ ██╔══██╗██╔══██╗██╔══██╗██╔═══██╗╚══██╔══╝
    ██║  ███╗██████╔╝██████╔╝██████╔╝██║   ██║   ██║   
    ██║   ██║██╔══██╗██╔═══╝ ██╔══██╗██║   ██║   ██║   
    ╚██████╔╝██████╔╝██║     ██████╔╝╚██████╔╝   ██║   
     ╚═════╝ ╚═════╝ ╚═╝     ╚═════╝  ╚═════╝    ╚═╝   {Colors.ENDC}
{Colors.BOLD}============================================================{Colors.ENDC}
{Colors.CYAN}                Bot de Trading Optimisé pour PC Local{Colors.ENDC}
{Colors.BOLD}============================================================{Colors.ENDC}
"""
    print(banner)


def display_bot_status(bot_context: Dict[str, Any]) -> None:
    """
    Affiche l'état actuel du bot
    
    Args:
        bot_context: Contexte du bot contenant l'état actuel
    """
    status = bot_context.get("status", "Arrêté")
    uptime = bot_context.get("uptime", 0)
    
    # Formater le temps d'activité
    hours, remainder = divmod(uptime, 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime_str = f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
    
    # Afficher les informations de base
    print(f"{Colors.BOLD}État actuel:{Colors.ENDC} {status}")
    print(f"{Colors.BOLD}Temps d'activité:{Colors.ENDC} {uptime_str}")
    
    # Afficher les modules actifs
    active_modules = bot_context.get("active_modules", [])
    if active_modules:
        print(f"{Colors.BOLD}Modules actifs:{Colors.ENDC} {', '.join([m['name'] for m in active_modules])}")
    
    # Afficher les ressources système
    resources = bot_context.get("resources", {})
    if resources:
        cpu = resources.get("cpu", 0)
        memory = resources.get("memory", 0)
        print(f"{Colors.BOLD}Ressources:{Colors.ENDC} CPU: {cpu}%, Mémoire: {memory}%")
    
    print()


def confirm_exit() -> bool:
    """
    Demande confirmation avant de quitter
    
    Returns:
        bool: True si l'utilisateur confirme, False sinon
    """
    while True:
        choice = input("Êtes-vous sûr de vouloir quitter ? (o/n): ").lower()
        if choice in ["o", "oui", "y", "yes"]:
            return True
        elif choice in ["n", "non", "no"]:
            return False
        else:
            print_status("Veuillez répondre par 'o' ou 'n'", "warning")


async def run_cli() -> None:
    """
    Point d'entrée principal pour l'interface CLI
    """
    # Initialiser le contexte du bot
    bot_context = {
        "status": "Prêt",
        "uptime": 0,
        "start_time": time.time(),
        "active_modules": [],
        "available_modules": [
            {"name": "Arbitrage", "active": False},
            {"name": "Sniping", "active": False},
            {"name": "Auto Mode", "active": False},
            {"name": "AI Assistant", "active": False},
            {"name": "Backtesting", "active": False}
        ],
        "config": {
            "general": {
                "performance_mode": "balanced",
                "auto_optimization": True,
                "debug_mode": False
            },
            "blockchain": {
                "preferred_rpc": "https://api.mainnet-beta.solana.com",
                "backup_rpc": "https://solana-api.projectserum.com"
            },
            "trading": {
                "max_slippage": 1.0,
                "gas_limit": "auto",
                "auto_approve": False
            }
        },
        "resources": {
            "cpu": 0,
            "memory": 0,
            "disk": 0
        }
    }
    
    # Mettre à jour les ressources système périodiquement
    async def update_resources():
        while True:
            try:
                # Simuler la mise à jour des ressources
                # Dans une implémentation réelle, cela appellerait le moniteur de ressources
                import random
                bot_context["resources"]["cpu"] = random.randint(5, 30)
                bot_context["resources"]["memory"] = random.randint(20, 60)
                bot_context["resources"]["disk"] = random.randint(30, 70)
                
                # Mettre à jour le temps d'activité
                bot_context["uptime"] = time.time() - bot_context["start_time"]
            except Exception as e:
                logger.error(f"Erreur lors de la mise à jour des ressources: {e}")
            
            await asyncio.sleep(5)  # Mettre à jour toutes les 5 secondes
    
    # Démarrer la tâche de mise à jour des ressources
    resource_task = asyncio.create_task(update_resources())
    
    try:
        # Afficher le menu principal
        await display_main_menu(bot_context)
    except KeyboardInterrupt:
        print("\nInterruption détectée. Fermeture du GBPBot...")
    except Exception as e:
        logger.error(f"Erreur non gérée: {e}")
        print(f"\nUne erreur s'est produite: {e}")
    finally:
        # Annuler la tâche de mise à jour des ressources
        resource_task.cancel()
        try:
            await resource_task
        except asyncio.CancelledError:
            pass


def main() -> None:
    """
    Point d'entrée pour le lancement du CLI
    """
    try:
        # Configurer asyncio pour Windows
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        # Exécuter la boucle asyncio
        asyncio.run(run_cli())
    except Exception as e:
        logger.error(f"Erreur lors du lancement du CLI: {e}")
        print(f"Une erreur s'est produite lors du lancement du CLI: {e}")
        input("Appuyez sur Entrée pour quitter...")


if __name__ == "__main__":
    main() 