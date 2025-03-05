#!/usr/bin/env python
"""
Point d'entrée unique pour GBPBot
Ce script:
1. Vérifie et installe les dépendances manquantes
2. Propose de lancer le dashboard en parallèle
3. Affiche le menu principal pour gérer le bot
"""

import subprocess
import sys
import os
import time
import signal
import atexit
from typing import List, Optional

# Liste des dépendances essentielles
REQUIRED_PACKAGES = [
    "loguru",
    "pandas",
    "web3",
    "pytest",
    "pytest-asyncio",
    "python-dotenv",
    "rich"
]

# Variables globales pour les processus
dashboard_process = None

def print_colored(text, color="green"):
    """Affiche du texte coloré dans la console"""
    colors = {
        "green": "\033[92m",
        "yellow": "\033[93m",
        "red": "\033[91m",
        "blue": "\033[94m",
        "cyan": "\033[96m",
        "magenta": "\033[95m",
        "reset": "\033[0m"
    }
    print(f"{colors.get(color, '')}{text}{colors['reset']}")

def install_missing_packages():
    """Vérifie et installe les packages manquants"""
    print_colored("Vérification des dépendances...", "blue")
    
    for package in REQUIRED_PACKAGES:
        try:
            __import__(package)
            print_colored(f"✓ {package} est déjà installé", "green")
        except ImportError:
            print_colored(f"! Installation de {package}...", "yellow")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print_colored(f"✓ {package} installé avec succès", "green")
    
    print_colored("Toutes les dépendances sont installées!", "green")

def launch_dashboard():
    """Lance le dashboard en arrière-plan"""
    global dashboard_process
    
    print_colored("\nLancement du dashboard...", "blue")
    
    # Déterminer la commande appropriée selon le système d'exploitation
    if os.name == 'nt':  # Windows
        dashboard_cmd = [sys.executable, "-m", "gbpbot.cli"]
        # Utiliser CREATE_NEW_CONSOLE pour ouvrir dans une nouvelle fenêtre sous Windows
        dashboard_process = subprocess.Popen(
            dashboard_cmd,
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
    else:  # Linux/Mac
        dashboard_cmd = [sys.executable, "-m", "gbpbot.cli"]
        dashboard_process = subprocess.Popen(
            dashboard_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True
        )
    
    print_colored("Dashboard lancé en arrière-plan (PID: {})".format(dashboard_process.pid), "green")
    return dashboard_process.pid

def cleanup_processes():
    """Nettoie les processus en arrière-plan lors de la sortie"""
    global dashboard_process
    
    if dashboard_process:
        print_colored("\nArrêt du dashboard...", "yellow")
        try:
            if os.name == 'nt':  # Windows
                subprocess.call(['taskkill', '/F', '/T', '/PID', str(dashboard_process.pid)])
            else:  # Linux/Mac
                os.killpg(os.getpgid(dashboard_process.pid), signal.SIGTERM)
            print_colored("Dashboard arrêté avec succès", "green")
        except Exception as e:
            print_colored(f"Erreur lors de l'arrêt du dashboard: {e}", "red")

def display_menu():
    """Affiche le menu principal"""
    print_colored("\n" + "="*50, "cyan")
    print_colored("               MENU PRINCIPAL", "cyan")
    print_colored("="*50, "cyan")
    print_colored("1 : Lancer le bot")
    print_colored("2 : Configurer les paramètres")
    print_colored("3 : Afficher la configuration actuelle")
    print_colored("4 : Afficher les statistiques")
    print_colored("5 : Quitter")
    print_colored("="*50, "cyan")
    return input("Votre choix : ")

def run_bot():
    """Lance le bot en mode terminal"""
    print_colored("\nLancement du bot en mode terminal...", "blue")
    try:
        # Importer et lancer le bot avec le code réel
        print_colored("Importation des modules du bot...", "blue")
        
        # Ajouter le répertoire courant au chemin Python si nécessaire
        if os.path.abspath('.') not in sys.path:
            sys.path.insert(0, os.path.abspath('.'))

        try:
            # Vérifier si dotenv est installé
            try:
                from dotenv import load_dotenv
                load_dotenv()  # Charger les variables d'environnement depuis .env
                print_colored("Variables d'environnement chargées depuis .env", "green")
            except ImportError:
                print_colored("Module dotenv non trouvé. Installation...", "yellow")
                subprocess.check_call([sys.executable, "-m", "pip", "install", "python-dotenv"])
                from dotenv import load_dotenv
                load_dotenv()
                print_colored("Variables d'environnement chargées depuis .env", "green")
            
            # Importer l'interface CLI et le bot
            from gbpbot.cli_interface import CLIInterface
            from gbpbot.main import GBPBot
            import asyncio
            
            # Configuration de l'event loop pour Windows (résout le problème aiodns)
            if os.name == 'nt':  # Windows
                import asyncio
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
                print_colored("Event loop configuré pour Windows (résout le problème aiodns)", "green")
            
            # Créer l'interface CLI
            cli = CLIInterface()
            
            # Afficher les menus de sélection
            mode_choice = cli.display_mode_selection()
            module_choice = cli.display_module_selection()
            
            # Convertir le choix du mode en paramètres pour le bot
            simulation_mode = (mode_choice != "3")  # Modes 1 et 2 sont simulation
            is_testnet = (mode_choice == "1")  # Mode 1 est test
            
            # Afficher la configuration
            print_colored(f"Configuration du bot:", "blue")
            print_colored(f"- Mode simulation: {simulation_mode}", "cyan")
            print_colored(f"- Réseau de test: {is_testnet}", "cyan")
            
            # Créer et démarrer le bot avec les paramètres sélectionnés
            print_colored("Création de l'instance du bot...", "blue")
            bot = GBPBot(simulation_mode=simulation_mode, is_testnet=is_testnet)
            
            # Définir le solde initial si en mode simulation
            if simulation_mode:
                bot.blockchain.simulated_balances = {
                    "WAVAX": float(os.getenv("INITIAL_WAVAX", "5.0")),
                    "USDT": float(os.getenv("INITIAL_USDT", "0.0")),
                    "USDC": float(os.getenv("INITIAL_USDC", "0.0")),
                    "WETH": float(os.getenv("INITIAL_WETH", "0.0"))
                }
                print_colored("Soldes initiaux configurés:", "cyan")
                for token, amount in bot.blockchain.simulated_balances.items():
                    print_colored(f"- {token}: {amount}", "cyan")
            
            print_colored("Bot initialisé avec succès", "green")
            print_colored(f"Démarrage du bot en mode {mode_choice} avec le module {module_choice}...", "blue")
            print_colored("Appuyez sur Ctrl+C pour arrêter le bot", "yellow")
            
            # Lancer le bot avec le module sélectionné
            # TODO: Implémenter la sélection du module
            asyncio.run(bot.start())
            
        except ImportError as e:
            print_colored(f"Erreur d'importation: {e}", "red")
            print_colored("Vérifiez que le module gbpbot est accessible dans le chemin Python.", "yellow")
            print_colored("Conseil: Assurez-vous que tous les modules requis sont installés.", "yellow")
            return
        except Exception as e:
            print_colored(f"Erreur lors de l'initialisation du bot: {e}", "red")
            return
            
    except KeyboardInterrupt:
        print_colored("\nArrêt du bot demandé par l'utilisateur", "yellow")
    except Exception as e:
        print_colored(f"\nErreur lors de l'exécution du bot: {e}", "red")
    finally:
        print_colored("Bot arrêté", "green")

def configure_parameters():
    """Configure les paramètres du bot"""
    print_colored("\nConfiguration des paramètres", "blue")
    
    # Vérifier si le fichier .env existe
    env_file = ".env"
    env_params = {}
    
    if os.path.exists(env_file):
        # Lire les paramètres actuels
        try:
            with open(env_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        env_params[key.strip()] = value.strip()
        except Exception as e:
            print_colored(f"Erreur lors de la lecture du fichier .env: {e}", "red")
    
    # Définir les paramètres configurables
    configurable_params = [
        {
            "name": "SIMULATION_MODE",
            "description": "Mode simulation (True/False)",
            "default": "True",
            "type": "bool"
        },
        {
            "name": "TESTNET",
            "description": "Utiliser le réseau de test (True/False)",
            "default": "True",
            "type": "bool"
        },
        {
            "name": "MIN_PROFIT_THRESHOLD",
            "description": "Seuil de profit minimum (%)",
            "default": "1.5",
            "type": "float"
        },
        {
            "name": "MAX_GAS_PRICE",
            "description": "Prix maximum du gas (GWEI)",
            "default": "50",
            "type": "float"
        },
        {
            "name": "ENTRY_TOKEN",
            "description": "Token d'entrée (WAVAX, USDC, etc.)",
            "default": "WAVAX",
            "type": "str"
        }
    ]
    
    print_colored("\nConfiguration des paramètres du bot:", "cyan")
    print_colored("(Appuyez sur Entrée pour conserver la valeur actuelle)", "yellow")
    
    # Demander à l'utilisateur de configurer chaque paramètre
    for param in configurable_params:
        name = param["name"]
        current_value = env_params.get(name, param["default"])
        
        print_colored(f"\n{param['description']}", "blue")
        print_colored(f"Valeur actuelle: {current_value}", "green")
        
        new_value = input(f"Nouvelle valeur (ou Entrée pour conserver): ")
        
        if new_value.strip():
            env_params[name] = new_value
            print_colored(f"Paramètre {name} mis à jour: {new_value}", "green")
    
    # Enregistrer les modifications dans le fichier .env
    try:
        with open(env_file, "w") as f:
            for key, value in env_params.items():
                f.write(f"{key}={value}\n")
        print_colored(f"\nConfiguration enregistrée dans {env_file}", "green")
    except Exception as e:
        print_colored(f"Erreur lors de l'enregistrement du fichier .env: {e}", "red")
    
    input("Appuyez sur Entrée pour continuer...")

def display_configuration():
    """Affiche la configuration actuelle"""
    print_colored("\nConfiguration actuelle", "blue")
    
    # Lire et afficher le contenu du fichier .env s'il existe
    if os.path.exists(".env"):
        print_colored("Contenu du fichier .env :", "cyan")
        try:
            with open(".env", "r") as f:
                for line in f:
                    # Masquer les informations sensibles
                    if "API_KEY" in line or "SECRET" in line or "PASSWORD" in line:
                        key, value = line.split("=", 1)
                        print_colored(f"{key}=****", "yellow")
                    else:
                        print_colored(line.strip(), "green")
        except Exception as e:
            print_colored(f"Erreur lors de la lecture du fichier .env: {e}", "red")
    else:
        print_colored("Fichier .env non trouvé", "red")
    
    input("Appuyez sur Entrée pour continuer...")

def display_statistics():
    """Affiche les statistiques du bot"""
    print_colored("\nStatistiques", "blue")
    
    # Vérifier si le dossier logs existe
    if os.path.exists("logs"):
        print_colored("Dernières entrées des logs :", "cyan")
        try:
            # Trouver le fichier log le plus récent
            log_files = [f for f in os.listdir("logs") if f.endswith(".log")]
            if log_files:
                latest_log = max(log_files, key=lambda x: os.path.getmtime(os.path.join("logs", x)))
                log_path = os.path.join("logs", latest_log)
                
                # Afficher les 10 dernières lignes
                if os.name == 'nt':  # Windows
                    result = subprocess.run(["powershell", "-Command", f"Get-Content -Tail 10 {log_path}"], 
                                           capture_output=True, text=True)
                    for line in result.stdout.splitlines():
                        print_colored(line, "green")
                else:  # Linux/Mac
                    result = subprocess.run(["tail", "-n", "10", log_path], 
                                           capture_output=True, text=True)
                    for line in result.stdout.splitlines():
                        print_colored(line, "green")
            else:
                print_colored("Aucun fichier log trouvé", "yellow")
        except Exception as e:
            print_colored(f"Erreur lors de la lecture des logs: {e}", "red")
    else:
        print_colored("Dossier logs non trouvé", "red")
    
    input("Appuyez sur Entrée pour continuer...")

def ensure_env_file_exists():
    """Crée un fichier .env par défaut s'il n'existe pas"""
    env_file = ".env"
    
    if not os.path.exists(env_file):
        print_colored("Fichier .env non trouvé. Création d'un fichier par défaut...", "yellow")
        
        default_env = """# Configuration par défaut pour GBPBot
# Modifiez ces valeurs selon vos besoins

# Mode de fonctionnement
SIMULATION_MODE=True
TESTNET=True

# Paramètres de trading
MIN_PROFIT_THRESHOLD=1.5
MAX_GAS_PRICE=50
ENTRY_TOKEN=WAVAX

# Soldes initiaux (pour le mode simulation)
INITIAL_WAVAX=5.0
INITIAL_USDT=0.0
INITIAL_USDC=0.0
INITIAL_WETH=0.0

# Paramètres RPC
RPC_ENDPOINT=https://api.avax.network/ext/bc/C/rpc
WEBSOCKET_ENDPOINT=wss://api.avax.network/ext/bc/C/ws

# Logging
LOG_LEVEL=INFO
"""
        
        try:
            with open(env_file, "w") as f:
                f.write(default_env)
            print_colored(f"Fichier .env créé avec succès", "green")
        except Exception as e:
            print_colored(f"Erreur lors de la création du fichier .env: {e}", "red")

def main():
    """Fonction principale"""
    # Enregistrer la fonction de nettoyage à exécuter à la sortie
    atexit.register(cleanup_processes)
    
    print_colored("=== GBPBot - Point d'entrée unique ===", "magenta")
    
    # Étape 1: Installation des dépendances manquantes
    install_missing_packages()
    
    # Étape 1.5: S'assurer que le fichier .env existe
    ensure_env_file_exists()
    
    # Étape 2: Demander si l'utilisateur souhaite lancer le dashboard
    print_colored("\nSouhaitez-vous lancer le dashboard en parallèle? (y/n)", "cyan")
    choice = input("Votre choix : ").lower()
    
    if choice == 'y':
        launch_dashboard()
    
    # Étape 3: Afficher le menu principal et gérer les choix
    while True:
        choice = display_menu()
        
        if choice == '1':
            run_bot()
        elif choice == '2':
            configure_parameters()
        elif choice == '3':
            display_configuration()
        elif choice == '4':
            display_statistics()
        elif choice == '5':
            print_colored("\nFermeture du programme...", "yellow")
            break
        else:
            print_colored("\nChoix invalide. Veuillez réessayer.", "red")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_colored("\nProgramme interrompu par l'utilisateur", "yellow")
    except Exception as e:
        print_colored(f"\nErreur inattendue: {e}", "red")
    finally:
        # Assurer que les processus sont nettoyés même en cas d'erreur
        cleanup_processes()
        print_colored("\nProgramme terminé", "green") 