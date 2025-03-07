#!/usr/bin/env python
# -*- coding: utf-8 -*-

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
from typing import Dict, List, Optional, Any, Union, Callable
from datetime import datetime
import subprocess
import platform

# Création du dossier logs s'il n'existe pas
os.makedirs("logs", exist_ok=True)

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

# Constantes pour les couleurs
class Colors:
    """Classe pour les couleurs dans le terminal"""
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    HEADER = '\033[95m'  # Même couleur que PURPLE pour les titres

# État global du bot
class BotState:
    def __init__(self):
        self.running = False
        self.active_modules = {
            "arbitrage": False,
            "sniping": False,
            "auto_mode": False,
            "solana_sniping": False,
            "solana_frontrun": False,
            "cross_dex_arbitrage": False,
            "ai_assistant": False
        }
        self.start_time = None
        self.blockchain_clients = {}
        self.strategies = {}
        self.config: Dict[str, Any] = {}  # Initialiser comme un dictionnaire vide au lieu de None
        self.module_instances = {}
    
    def start(self):
        """Démarre le bot et initialise le timer."""
        self.running = True
        self.start_time = time.time()
        logger.info("Bot démarré")
    
    def stop(self):
        """Arrête le bot et réinitialise le timer."""
        self.running = False
        self.start_time = None
        logger.info("Bot arrêté")

# Instanciation de l'état global
bot_state = BotState()

# Fonctions utilitaires
def clear_screen():
    """Efface l'écran selon le système d'exploitation."""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header(text: str):
    """Affiche un texte formaté comme titre."""
    print(f"\n{Colors.PURPLE}{Colors.BOLD}{text}{Colors.ENDC}")

def print_menu_option(number: int, text: str):
    """Affiche une option de menu formatée."""
    print(f"{Colors.BLUE}{number}.{Colors.ENDC} {text}")

def print_status(label: str, status: bool):
    """Affiche un statut avec couleur selon l'état."""
    status_text = f"{Colors.GREEN}ACTIF{Colors.ENDC}" if status else f"{Colors.RED}INACTIF{Colors.ENDC}"
    print(f"{label}: {status_text}")

def format_duration(seconds: float) -> str:
    """Formate une durée en secondes en format lisible."""
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

def get_config(config_path: str = "config.json") -> Dict[str, Any]:
    """
    Charge la configuration depuis le fichier de configuration.
    
    Args:
        config_path: Chemin vers le fichier de configuration
        
    Returns:
        Dict[str, Any]: Configuration chargée ou dictionnaire vide si échec
    """
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        logger.info(f"Configuration chargée depuis {config_path}")
        return config
    except FileNotFoundError:
        logger.warning(f"Fichier de configuration {config_path} non trouvé")
        return {}
    except json.JSONDecodeError:
        logger.error(f"Erreur de format JSON dans {config_path}")
        return {}
    except Exception as e:
        logger.error(f"Erreur lors du chargement de la configuration: {str(e)}")
        return {}

def save_config(config: Dict[str, Any], config_path: str = "config.json") -> bool:
    """
    Sauvegarde la configuration dans un fichier.
    
    Args:
        config: Configuration à sauvegarder
        config_path: Chemin du fichier de configuration
        
    Returns:
        bool: True si sauvegarde réussie, False sinon
    """
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        logger.info(f"Configuration sauvegardée dans {config_path}")
        return True
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde de la configuration: {str(e)}")
        return False

def initialize_bot(config_path: str = "config.json") -> bool:
    """
    Initialise le GBPBot.
    
    Args:
        config_path: Chemin vers le fichier de configuration
        
    Returns:
        bool: True si l'initialisation a réussi, False sinon
    """
    try:
        logger.info("Initialisation du GBPBot en cours...")
        
        # Charger la configuration
        config = get_config(config_path)
        bot_state.config = config

        # S'assurer que la configuration n'est pas vide
        if not bot_state.config:
            logger.error("Impossible de charger la configuration")
            return False

        logger.info("Initialisation terminée avec succès")
        return True
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation du bot: {str(e)}")
        return False

async def display_main_menu():
    """Affiche le menu principal du GBPBot."""
    clear_screen()
    print_header("GBPBot - Menu Principal")
    print("=" * 60)
    print("Bienvenue dans GBPBot, votre assistant de trading sur MEME coins!")
    print()
    print_menu_option(1, "Démarrer le Bot")
    print_menu_option(2, "Configurer les paramètres")
    print_menu_option(3, "Afficher la configuration actuelle")
    print_menu_option(4, "Statistiques et Logs")
    print_menu_option(5, "Afficher les Modules Disponibles")
    print_menu_option(6, "Quitter")
    print()
    
    # Afficher l'état actuel du bot
    print(f"État du bot: {'ACTIF' if bot_state.running else 'INACTIF'}")
    if bot_state.start_time is not None:
        uptime = format_duration(time.time() - bot_state.start_time)
        print(f"Temps d'exécution: {uptime}")
    print()

async def display_modules_menu():
    """Affiche le menu des modules disponibles."""
    clear_screen()
    print_header("GBPBot - Sélection de Module")
    print("=" * 60)
    print_menu_option(1, "Arbitrage entre les DEX")
    print_menu_option(2, "Sniping de Token")
    print_menu_option(3, "Lancer automatiquement le bot")
    print_menu_option(4, "IA Assistant (Nouveau!)")
    print_menu_option(5, "Retour au menu principal")
    print()

async def display_stats():
    """Affiche les statistiques du bot."""
    clear_screen()
    print_header("GBPBot - Statistiques et État")
    print("=" * 60)
    
    print(f"État du bot: {Colors.GREEN}ACTIF{Colors.ENDC}" if bot_state.running else f"État du bot: {Colors.RED}INACTIF{Colors.ENDC}")
    uptime = format_duration(time.time() - bot_state.start_time) if bot_state.start_time is not None else "N/A"
    print(f"Temps d'exécution: {uptime}")
    
    modules_actifs = sum(1 for active in bot_state.active_modules.values() if active)
    print(f"{Colors.GREEN}Modules actifs: {modules_actifs}/{len(bot_state.active_modules)}{Colors.ENDC}")
    
    print("\nÉtat des modules:")
    print_status("Arbitrage", bot_state.active_modules["arbitrage"])
    print_status("Sniping", bot_state.active_modules["sniping"])
    print_status("Mode Auto", bot_state.active_modules["auto_mode"])
    print_status("Assistant IA", bot_state.active_modules.get("ai_assistant", False))
    print_status("Sniping Solana", bot_state.active_modules["solana_sniping"])
    print_status("Frontrunning Solana", bot_state.active_modules["solana_frontrun"])
    print_status("Arbitrage Cross-DEX", bot_state.active_modules["cross_dex_arbitrage"])
    
    print("\nAppuyez sur Entrée pour revenir au menu principal...")
    input()

async def start_bot():
    """Lance le bot avec les modules actifs."""
    if not bot_state.running:
        bot_state.start()
        print(f"{Colors.GREEN}Bot démarré avec succès !{Colors.ENDC}")
    else:
        print(f"{Colors.YELLOW}Le bot est déjà actif.{Colors.ENDC}")
    
    print("\nAppuyez sur Entrée pour revenir au menu principal...")
    input()

async def stop_bot():
    """Arrête le bot et tous ses modules."""
    if bot_state.running:
        bot_state.stop()
        print(f"{Colors.GREEN}Bot arrêté avec succès !{Colors.ENDC}")
    else:
        print(f"{Colors.YELLOW}Le bot n'est pas actif.{Colors.ENDC}")
    
    print("\nAppuyez sur Entrée pour revenir au menu principal...")
    input()

async def main_loop():
    """Boucle principale du menu GBPBot."""
    if not initialize_bot():
        print(f"{Colors.RED}Erreur lors de l'initialisation du bot. Vérifiez les logs pour plus de détails.{Colors.ENDC}")
        print("\nAppuyez sur Entrée pour continuer...")
        input()
    
    while True:
        await display_main_menu()
        
        try:
            choice = input("\nChoisissez une option (1-6): ")
            
            if choice == "1":
                await start_bot()
            elif choice == "2":
                # TODO: Implémenter la configuration
                print(f"{Colors.YELLOW}Fonctionnalité non implémentée{Colors.ENDC}")
                input("Appuyez sur Entrée pour continuer...")
            elif choice == "3":
                # TODO: Afficher la configuration
                print(f"{Colors.YELLOW}Fonctionnalité non implémentée{Colors.ENDC}")
                input("Appuyez sur Entrée pour continuer...")
            elif choice == "4":
                await display_stats()
            elif choice == "5":
                await display_modules_menu()
                module_choice = input("\nChoisissez un module (1-5): ")
                
                if module_choice == "5":
                    continue  # Retour au menu principal
                else:
                    # TODO: Implémenter la gestion des modules
                    print(f"{Colors.YELLOW}Fonctionnalité non implémentée{Colors.ENDC}")
                    input("Appuyez sur Entrée pour continuer...")
            elif choice == "6":
                if bot_state.running:
                    confirm = input(f"{Colors.YELLOW}Le bot est toujours en cours d'exécution. Voulez-vous l'arrêter et quitter ? (o/n): {Colors.ENDC}")
                    if confirm.lower() == "o":
                        await stop_bot()
                        break
                else:
                    print("Merci d'avoir utilisé GBPBot. À bientôt !")
                    break
            else:
                print(f"{Colors.RED}Option invalide. Veuillez réessayer.{Colors.ENDC}")
                input("Appuyez sur Entrée pour continuer...")
        except KeyboardInterrupt:
            print("\nInterruption détectée. Arrêt du bot...")
            await stop_bot()
            break
        except Exception as e:
            print(f"{Colors.RED}Une erreur est survenue: {str(e)}{Colors.ENDC}")
            input("Appuyez sur Entrée pour continuer...")

def main():
    """Fonction principale du menu GBPBot."""
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        print("\nArrêt du programme.")
    except Exception as e:
        logger.exception(f"Erreur non gérée: {str(e)}")
        print(f"\n{Colors.RED}Une erreur fatale est survenue. Consultez les logs pour plus de détails.{Colors.ENDC}")

if __name__ == "__main__":
    main() 