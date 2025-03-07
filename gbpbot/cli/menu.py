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
from typing import Dict, List, Optional, Any, Union, Callable
from datetime import datetime

# Configuration du logging
logger = logging.getLogger("gbpbot.cli.menu")

# Importer les commandes
from gbpbot.cli.commands import (
    start_arbitrage_module,
    start_sniping_module,
    start_backtesting_module,
    start_ai_assistant_module,
    stop_module
)
from gbpbot.cli.display import (
    clear_screen,
    print_banner,
    print_header,
    print_menu_option,
    print_status
)

# Importation des sous-menus
try:
    from gbpbot.cli.commands.arbitrage import display_arbitrage_menu
    from gbpbot.cli.commands.sniping import display_sniping_menu
    from gbpbot.cli.commands.auto_mode import display_auto_mode_menu
    from gbpbot.cli.commands.ai import display_ai_menu
    from gbpbot.cli.commands.backtesting import display_backtesting_menu
    from gbpbot.cli.commands.config import display_config_menu
    from gbpbot.cli.commands.stats import display_stats_menu
    from gbpbot.cli.commands.wallet import display_wallet_menu
    from gbpbot.cli.commands.auto_optimization import display_auto_optimization_menu
    
    CLI_MODULES_LOADED = True
except ImportError as e:
    logging.warning(f"Certains modules CLI n'ont pas pu être importés: {str(e)}")
    CLI_MODULES_LOADED = False

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

async def display_main_menu(bot_context: Dict[str, Any]) -> None:
    """
    Affiche le menu principal du GBPBot et gère les interactions utilisateur.
    
    Args:
        bot_context: Contexte contenant la configuration et les modules du bot
    """
    while True:
        clear_screen()
        
        # Afficher la bannière
        display_banner()
        
        # Afficher l'état du bot
        display_bot_status(bot_context)
        
        # Options du menu principal
        print("\nOptions:")
        print("1. Arbitrage entre les DEX")
        print("2. Sniping de Token")
        print("3. Mode Automatique")
        print("4. Assistant IA")
        print("5. Backtesting et Simulation")
        print("6. Automatisation Intelligente")
        print("\n7. Configuration")
        print("8. Statistiques et Logs")
        print("9. Gestion des Wallets")
        print("\n0. Quitter")
        
        choice = input("\nChoisissez une option (0-9): ")
        
        if choice == '1':
            if 'display_arbitrage_menu' in globals():
                display_arbitrage_menu(bot_context)
            else:
                print("Module d'arbitrage non disponible.")
                time.sleep(1)
        elif choice == '2':
            if 'display_sniping_menu' in globals():
                display_sniping_menu(bot_context)
            else:
                print("Module de sniping non disponible.")
                time.sleep(1)
        elif choice == '3':
            if 'display_auto_mode_menu' in globals():
                display_auto_mode_menu(bot_context)
            else:
                print("Module de mode automatique non disponible.")
                time.sleep(1)
        elif choice == '4':
            if 'display_ai_menu' in globals():
                display_ai_menu(bot_context)
            else:
                print("Module IA non disponible.")
                time.sleep(1)
        elif choice == '5':
            if 'display_backtesting_menu' in globals():
                display_backtesting_menu(bot_context)
            else:
                print("Module de backtesting non disponible.")
                time.sleep(1)
        elif choice == '6':
            if 'display_auto_optimization_menu' in globals():
                display_auto_optimization_menu(bot_context)
            else:
                print("Module d'automatisation intelligente non disponible.")
                time.sleep(1)
        elif choice == '7':
            if 'display_config_menu' in globals():
                display_config_menu(bot_context)
            else:
                print("Module de configuration non disponible.")
                time.sleep(1)
        elif choice == '8':
            if 'display_stats_menu' in globals():
                display_stats_menu(bot_context)
            else:
                print("Module de statistiques non disponible.")
                time.sleep(1)
        elif choice == '9':
            if 'display_wallet_menu' in globals():
                display_wallet_menu(bot_context)
            else:
                print("Module de gestion des wallets non disponible.")
                time.sleep(1)
        elif choice == '0':
            if confirm_exit():
                clear_screen()
                print("Merci d'avoir utilisé GBPBot. À bientôt!")
                break
        else:
            print("Option invalide. Veuillez réessayer.")
            time.sleep(1)

def display_banner() -> None:
    """Affiche la bannière du GBPBot"""
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

def display_bot_status(bot_context: Dict[str, Any]) -> None:
    """
    Affiche l'état actuel du bot.
    
    Args:
        bot_context: Contexte contenant l'état du bot
    """
    # Récupérer le statut actuel
    modules = bot_context.get("modules", {})
    
    # Vérifier quels modules sont actifs
    arbitrage_active = "arbitrage_strategy" in modules
    sniping_active = "sniper_strategy" in modules
    auto_mode_active = "auto_strategy" in modules
    
    # Vérifier si l'automatisation intelligente est activée
    auto_optimization_enabled = bot_context.get("config", {}).get("auto_optimization", {}).get("enabled", False)
    
    # Nombre de stratégies actives
    active_count = sum([arbitrage_active, sniping_active, auto_mode_active])
    
    # Afficher le statut
    print("\nStatut du GBPBot:")
    print(f"Stratégies Actives: {active_count}/3 | ", end="")
    print(f"Arbitrage: {'✅' if arbitrage_active else '❌'} | ", end="")
    print(f"Sniping: {'✅' if sniping_active else '❌'} | ", end="")
    print(f"Auto Mode: {'✅' if auto_mode_active else '❌'}")
    print(f"Automatisation Intelligente: {'✅ Activée' if auto_optimization_enabled else '❌ Désactivée'}")

def confirm_exit() -> bool:
    """
    Demande confirmation avant de quitter.
    
    Returns:
        True si l'utilisateur confirme, False sinon
    """
    while True:
        choice = input("\n⚠️ Êtes-vous sûr de vouloir quitter? (o/n): ")
        if choice.lower() in ['o', 'oui', 'y', 'yes']:
            return True
        elif choice.lower() in ['n', 'non', 'no']:
            return False
        else:
            print("Réponse invalide. Veuillez répondre par 'o' (oui) ou 'n' (non).")

def run_cli():
    """
    Point d'entrée principal pour l'interface CLI
    """
    try:
        # Configurer asyncio pour Windows si nécessaire
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        # Exécuter le menu principal
        asyncio.run(display_main_menu())
    except KeyboardInterrupt:
        print("\n\nGBPBot arrêté par l'utilisateur.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution du CLI: {e}")
        print(f"\nErreur: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_cli() 