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
from dotenv import load_dotenv, set_key
import logging

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
bot_process = None  # Nouvelle variable pour suivre le processus du bot

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
    global dashboard_process, bot_process
    
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
    
    if bot_process:
        print_colored("\nArrêt du bot...", "yellow")
        try:
            if os.name == 'nt':  # Windows
                subprocess.call(['taskkill', '/F', '/T', '/PID', str(bot_process.pid)])
            else:  # Linux/Mac
                os.killpg(os.getpgid(bot_process.pid), signal.SIGTERM)
            print_colored("Bot arrêté avec succès", "green")
        except Exception as e:
            print_colored(f"Erreur lors de l'arrêt du bot: {e}", "red")

def display_menu():
    """Affiche le menu principal"""
    os.system('cls' if os.name == 'nt' else 'clear')
    print("=" * 60)
    print(" " * 20 + "GBPBot - Menu Principal" + " " * 20)
    print("=" * 60)
    print("Bienvenue dans GBPBot, votre assistant de trading sur Avalanche!")
    print("\nVeuillez choisir une option:")
    print("1. Démarrer le Bot")
    print("2. Configurer les paramètres")
    print("3. Afficher la configuration actuelle")
    print("4. Statistiques et Logs")
    print("5. Afficher les Modules Disponibles")
    print("6. Quitter")
    print("\nVotre choix: ", end="")

def run_bot():
    """Lance le bot en mode terminal"""
    global bot_process
    
    print_colored("\nLancement du bot en mode terminal...", "blue")
    
    try:
        # Récupérer les paramètres de mode depuis le fichier .env
        load_dotenv(override=True)  # Forcer le rechargement des variables d'environnement
        
        # Lire directement depuis le fichier .env pour éviter les problèmes de cache
        env_params = {}
        try:
            with open(".env", "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        env_params[key.strip()] = value.strip()
        except Exception as e:
            print_colored(f"Erreur lors de la lecture du fichier .env: {e}", "red")
            return
        
        # Récupérer les valeurs depuis env_params
        simulation_mode_str = env_params.get("SIMULATION_MODE", "True")
        is_testnet_str = env_params.get("TESTNET", "False")
        module = env_params.get("TRADING_MODULE", "arbitrage")
        
        # Convertir en booléens
        simulation_mode = simulation_mode_str.lower() in ["true", "1", "yes", "y"]
        is_testnet = is_testnet_str.lower() in ["true", "1", "yes", "y"]
        
        # Afficher la configuration
        mode_str = "TEST" if is_testnet else ("SIMULATION" if simulation_mode else "RÉEL")
        print_colored(f"Configuration du bot:", "blue")
        print_colored(f"- Mode: {mode_str}", "cyan")
        print_colored(f"- Réseau: {'Testnet' if is_testnet else 'Mainnet'}", "cyan")
        print_colored(f"- Module: {module}", "cyan")
        
        # Exécuter le bot directement dans ce terminal
        print_colored("\nDémarrage du bot...", "green")
        print_colored("Appuyez sur Ctrl+C pour arrêter le bot", "yellow")
        print_colored("=" * 50, "blue")
        
        # Importer et exécuter le bot directement
        import asyncio
        from gbpbot.main import GBPBot
        
        # Configuration de l'event loop pour Windows (résout le problème aiodns)
        if os.name == 'nt':  # Windows
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        # Créer l'instance du bot
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
        
        # Exécuter le bot
        asyncio.run(bot.start())
        
    except KeyboardInterrupt:
        print_colored("\nBot arrêté par l'utilisateur", "yellow")
    except Exception as e:
        print_colored(f"\nErreur lors du lancement du bot: {e}", "red")
    finally:
        print_colored("\nBot arrêté", "yellow")
        print_colored("\nAppuyez sur Entrée pour revenir au menu principal...", "cyan")
        input()

def configure_parameters():
    """Permet à l'utilisateur de configurer les paramètres du bot"""
    os.system('cls' if os.name == 'nt' else 'clear')
    print("=" * 60)
    print(" " * 20 + "GBPBot - Configuration" + " " * 20)
    print("=" * 60)
    
    # Vérifier si le fichier .env existe
    if not os.path.exists(".env"):
        print("Fichier .env non trouvé. Création d'un fichier par défaut...")
        ensure_env_file_exists()
    
    # Charger les variables d'environnement
    load_dotenv()
    
    parameters = {
        "1": ("SIMULATION_MODE", "Mode Simulation (True/False)", lambda x: x.lower() in ["true", "false"]),
        "2": ("TESTNET", "Testnet (True/False)", lambda x: x.lower() in ["true", "false"]),
        "3": ("MIN_PROFIT_THRESHOLD", "Seuil de profit minimum (%)", lambda x: x.replace(".", "", 1).isdigit()),
        "4": ("MAX_GAS_PRICE", "Prix de gaz maximum (GWEI)", lambda x: x.isdigit()),
        "5": ("ENTRY_TOKEN", "Token d'entrée (WAVAX, USDC, etc.)", lambda x: bool(x))
    }
    
    while True:
        print("\nParamètres configurables:")
        for key, (param, desc, _) in parameters.items():
            current_value = os.getenv(param, "Non défini")
            print(f"{key}. {desc}: {current_value}")
        
        print("6. Revenir au menu principal")
        
        choice = input("\nVeuillez sélectionner un paramètre à modifier (1-6): ")
        
        if choice == "6":
            break
        
        if choice not in parameters:
            print("Choix invalide, veuillez réessayer.")
            time.sleep(1)
            continue
        
        param, desc, validator = parameters[choice]
        new_value = input(f"Nouvelle valeur pour {desc} [{os.getenv(param, '')}]: ")
        
        if not new_value:
            print("Aucune modification n'a été apportée.")
            time.sleep(1)
            continue
        
        if not validator(new_value):
            print("Valeur invalide, veuillez réessayer.")
            time.sleep(1)
            continue
        
        # Mettre à jour le fichier .env
        set_key(".env", param, new_value)
        print(f"Paramètre {param} mis à jour avec succès!")
        time.sleep(1)
        
        # Recharger les variables d'environnement
        load_dotenv()
        
        # Rafraîchir l'affichage
        os.system('cls' if os.name == 'nt' else 'clear')
        print("=" * 60)
        print(" " * 20 + "GBPBot - Configuration" + " " * 20)
        print("=" * 60)

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
    # Installer les packages manquants
    install_missing_packages()
    
    # S'assurer que le fichier .env existe
    ensure_env_file_exists()
    
    # Demander à l'utilisateur s'il souhaite lancer le dashboard
    launch_dashboard = input("Souhaitez-vous lancer le dashboard? (o/n): ").lower() == 'o'
    
    if launch_dashboard:
        launch_dashboard()
    
    while True:
        display_menu()
        choice = input()
        
        if choice == "1":
            module = select_module()
            if module:
                run_bot()
            
        elif choice == "2":
            configure_parameters()
            
        elif choice == "3":
            display_configuration()
            
        elif choice == "4":
            display_statistics()
            
        elif choice == "5":
            _ = select_module()  # Ignorer la valeur de retour, juste pour afficher les modules
            
        elif choice == "6":
            print("\nMerci d'avoir utilisé GBPBot. À bientôt!")
            sys.exit(0)
            
        else:
            print("\nOption invalide. Veuillez réessayer.")
            time.sleep(2)

def select_module():
    """Permet à l'utilisateur de sélectionner un module"""
    os.system('cls' if os.name == 'nt' else 'clear')
    print("=" * 60)
    print(" " * 20 + "GBPBot - Sélection de Module" + " " * 20)
    print("=" * 60)
    
    modules = [
        ("arbitrage", "Arbitrage entre les DEX"),
        ("sniping", "Sniping de Token"),
        ("lending", "Optimisation de Lending"),
        ("staking", "Staking Automatisé")
    ]
    
    for i, (module_id, description) in enumerate(modules, 1):
        print(f"{i}. {description}")
    
    print("5. Retour au menu principal")
    
    while True:
        try:
            choice = input("\nVeuillez sélectionner un module (1-5): ")
            
            if choice == "5":
                return None
                
            if not choice.isdigit() or int(choice) < 1 or int(choice) > 4:
                print("Choix invalide, veuillez réessayer.")
                continue
                
            selected_module = modules[int(choice) - 1][0]
            
            # Mettre à jour le fichier .env
            set_key(".env", "TRADING_MODULE", selected_module)
            print(f"\nModule '{selected_module}' sélectionné avec succès!")
            time.sleep(2)
            return selected_module
            
        except Exception as e:
            print(f"Erreur lors de la sélection du module: {e}")
            time.sleep(2)

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