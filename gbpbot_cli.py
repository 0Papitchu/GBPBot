#!/usr/bin/env python
"""
Script d'entrée pour lancer l'interface CLI de GBPBot
====================================================

Ce script est le point d'entrée unique pour lancer GBPBot sur toutes les plateformes.
Il gère automatiquement:
- La vérification et création de l'environnement virtuel Python
- L'installation des dépendances requises
- La vérification et création des fichiers de configuration
- Le lancement de l'interface utilisateur avec le menu principal

Usage:
    python gbpbot_cli.py [--no-venv] [--debug]
"""

import os
import sys
import subprocess
import importlib.util
import argparse
import json
import time
from pathlib import Path

# Couleurs pour le terminal
COLORS = {
    "GREEN": "\033[92m",
    "YELLOW": "\033[93m",
    "RED": "\033[91m",
    "BLUE": "\033[94m",
    "CYAN": "\033[96m",
    "MAGENTA": "\033[95m",
    "BOLD": "\033[1m",
    "END": "\033[0m"
}

def print_colored(message, color="GREEN", bold=False):
    """Affiche un message coloré dans le terminal"""
    prefix = COLORS.get(color.upper(), "")
    if bold:
        prefix += COLORS["BOLD"]
    suffix = COLORS["END"]
    print(f"{prefix}{message}{suffix}")

def display_banner():
    """Affiche la bannière ASCII du GBPBot"""
    banner = f"""
{COLORS["BLUE"]}{COLORS["BOLD"]}    ██████╗ ██████╗ ██████╗ ██████╗  ██████╗ ████████╗
    ██╔════╝ ██╔══██╗██╔══██╗██╔══██╗██╔═══██╗╚══██╔══╝
    ██║  ███╗██████╔╝██████╔╝██████╔╝██║   ██║   ██║   
    ██║   ██║██╔══██╗██╔═══╝ ██╔══██╗██║   ██║   ██║   
    ╚██████╔╝██████╔╝██║     ██████╔╝╚██████╔╝   ██║   
     ╚═════╝ ╚═════╝ ╚═╝     ╚═════╝  ╚═════╝    ╚═╝   {COLORS["END"]}
{COLORS["CYAN"]}    ================================================
    Trading Bot Ultra-Rapide pour MEME Coins
    Solana | AVAX | Sonic
    ================================================{COLORS["END"]}
    """
    print(banner)

def parse_arguments():
    """Parse les arguments de la ligne de commande"""
    parser = argparse.ArgumentParser(description="Lance l'interface CLI de GBPBot")
    parser.add_argument("--no-venv", action="store_true", help="Ne pas utiliser d'environnement virtuel")
    parser.add_argument("--debug", action="store_true", help="Active le mode debug avec plus de logs")
    return parser.parse_args()

def check_environment(no_venv=False):
    """Vérifie que l'environnement est correctement configuré"""
    if no_venv:
        print_colored("Option --no-venv détectée: ignorer la gestion de l'environnement virtuel", "YELLOW")
        return
    
    # Vérifier si nous sommes dans un environnement virtuel
    in_venv = sys.prefix != sys.base_prefix
    if not in_venv:
        print_colored("AVERTISSEMENT: Non exécuté dans un environnement virtuel.", "YELLOW")
        
        # Vérifier si l'environnement virtuel existe
        venv_paths = ["venv", "env", "venv_310", ".venv", "venv_new"]
        found_venv = None
        
        for venv_path in venv_paths:
            if os.path.exists(venv_path):
                found_venv = venv_path
                break
        
        if found_venv:
            print_colored(f"Environnement virtuel trouvé: {found_venv}", "BLUE")
            activate_venv(found_venv)
        else:
            print_colored("Aucun environnement virtuel trouvé. Création d'un nouvel environnement...", "YELLOW")
            create_venv()
    else:
        print_colored("Environnement virtuel actif ✓", "GREEN")

def create_venv():
    """Crée un nouvel environnement virtuel"""
    print_colored("Création d'un environnement virtuel 'venv'...", "BLUE")
    try:
        subprocess.check_call([sys.executable, "-m", "venv", "venv"])
        print_colored("Environnement virtuel créé avec succès ✓", "GREEN")
        activate_venv("venv")
    except subprocess.CalledProcessError:
        print_colored("Erreur lors de la création de l'environnement virtuel!", "RED")
        print_colored("Tentative de continuer sans environnement virtuel...", "YELLOW")

def activate_venv(venv_path):
    """Active l'environnement virtuel"""
    print_colored(f"Activation de l'environnement virtuel '{venv_path}'...", "BLUE")
    
    # Déterminer le chemin du script d'activation selon la plateforme
    if sys.platform == "win32":
        python_path = os.path.join(venv_path, "Scripts", "python.exe")
    else:
        python_path = os.path.join(venv_path, "bin", "python")
    
    # Relancer ce script avec le Python de l'environnement virtuel
    if os.path.exists(python_path):
        # Obtenir le chemin absolu du script actuel
        current_script = os.path.abspath(__file__)
        
        # Passer les arguments originaux au nouveau processus
        args = sys.argv[1:]
        
        # Réexécuter ce script avec le Python de l'environnement virtuel
        print_colored("Relancement dans l'environnement virtuel...", "BLUE")
        os.execl(python_path, python_path, current_script, *args)
    else:
        print_colored(f"Erreur: Python non trouvé dans l'environnement virtuel '{venv_path}'", "RED")
        print_colored("Tentative de continuer sans environnement virtuel...", "YELLOW")

def install_missing_packages():
    """Vérifie et installe les packages manquants"""
    # Vérifier si le fichier requirements.txt existe
    if os.path.exists("requirements.txt"):
        with open("requirements.txt", "r") as f:
            requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    else:
        # Liste de base si requirements.txt n'existe pas
        requirements = ["solana", "web3", "pandas", "numpy", "requests", "python-dotenv", "psutil", "rich", "loguru"]
    
    missing_packages = []
    
    # Vérifier les packages requis
    for package in requirements:
        # Gérer les spécifications de version (ex: pandas==1.3.5)
        pkg_name = package.split("==")[0].split(">=")[0].split("<=")[0].strip()
        if importlib.util.find_spec(pkg_name) is None:
            missing_packages.append(package)
    
    # Installer les packages manquants
    if missing_packages:
        print_colored(f"Installation des packages requis manquants: {', '.join(missing_packages)}", "YELLOW")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing_packages)
            print_colored("Packages installés avec succès ✓", "GREEN")
        except subprocess.CalledProcessError:
            print_colored("Erreur lors de l'installation des packages!", "RED")
            print_colored("Certaines fonctionnalités pourraient ne pas fonctionner correctement.", "RED")
    else:
        print_colored("Tous les packages requis sont installés ✓", "GREEN")

def ensure_config_exists():
    """S'assure que les fichiers de configuration existent"""
    # Vérifier le fichier .env
    if not os.path.exists(".env"):
        if os.path.exists(".env.example"):
            print_colored("Fichier de configuration .env non trouvé. Création à partir de .env.example...", "YELLOW")
            with open(".env.example", "r") as src, open(".env", "w") as dst:
                dst.write(src.read())
            print_colored("Fichier .env créé avec succès. N'oubliez pas de le configurer!", "GREEN")
        else:
            print_colored("Fichier .env.example non trouvé. Création d'un fichier .env vide...", "YELLOW")
            with open(".env", "w") as f:
                f.write("# Configuration GBPBot\n")
            print_colored("Fichier .env vide créé. Veuillez le configurer!", "YELLOW")
    
    # Vérifier le répertoire de configuration utilisateur
    config_dir = Path.home() / ".gbpbot"
    if not config_dir.exists():
        config_dir.mkdir(exist_ok=True)
        print_colored(f"Répertoire de configuration utilisateur créé: {config_dir}", "GREEN")
    
    # Vérifier le fichier de configuration utilisateur
    user_config_file = config_dir / "user_config.json"
    if not user_config_file.exists():
        # Créer un fichier de configuration par défaut
        default_config = {
            "mode": "TEST",
            "simulation": {
                "initial_balance": 5.0,
                "duration": 43200
            },
            "trading": {
                "max_amount": 5.0,
                "min_profit": 0.5,
                "max_slippage": 0.3,
                "risk_level": "medium"
            },
            "monitoring": {
                "update_interval": 5,
                "alert_threshold": 10.0
            },
            "security": {
                "auto_transfer_profits": True,
                "profit_threshold": 10.0,
                "transfer_percentage": 30.0
            }
        }
        
        try:
            with open(user_config_file, "w") as f:
                json.dump(default_config, f, indent=4)
            print_colored(f"Fichier de configuration utilisateur créé: {user_config_file}", "GREEN")
        except Exception as e:
            print_colored(f"Erreur lors de la création du fichier de configuration: {str(e)}", "RED")

def check_system_requirements():
    """Vérifie les ressources système et la compatibilité"""
    print_colored("Vérification des ressources système...", "BLUE")
    
    # Vérifier l'utilisation de la mémoire
    try:
        import psutil
        memory_info = psutil.virtual_memory()
        total_memory_gb = memory_info.total / (1024 ** 3)
        available_memory_gb = memory_info.available / (1024 ** 3)
        
        print_colored(f"Mémoire totale: {total_memory_gb:.1f} GB", "CYAN")
        print_colored(f"Mémoire disponible: {available_memory_gb:.1f} GB", "CYAN")
        
        if available_memory_gb < 2.0:
            print_colored("AVERTISSEMENT: Mémoire disponible insuffisante (<2GB). Le bot pourrait rencontrer des problèmes de performance.", "YELLOW")
    except ImportError:
        print_colored("Module psutil non disponible. Impossible de vérifier la mémoire système.", "YELLOW")
    except Exception as e:
        print_colored(f"Erreur lors de la vérification de la mémoire: {str(e)}", "RED")
    
    print_colored("Vérification système terminée.", "GREEN")

def launch_gbpbot():
    """Lance le menu principal du GBPBot"""
    display_banner()
    
    print_colored("\n" + "=" * 60, "BLUE", True)
    print_colored("                    GBPBot - Initialisation", "BLUE", True)
    print_colored("=" * 60 + "\n", "BLUE", True)
    
    # Analyser les arguments de la ligne de commande
    args = parse_arguments()
    
    # Vérifier l'environnement
    check_environment(args.no_venv)
    
    # Installer les packages manquants
    install_missing_packages()
    
    # S'assurer que les fichiers de configuration existent
    ensure_config_exists()
    
    # Vérifier les ressources système
    check_system_requirements()
    
    print_colored("\nDémarrage du GBPBot...\n", "GREEN", True)
    time.sleep(1)  # Pause pour l'affichage
    
    try:
        # Ajouter le répertoire courant au PYTHONPATH pour permettre l'import du package gbpbot
        current_dir = os.path.abspath(os.path.dirname(__file__))
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
        
        # Importer depuis le package gbpbot
        from gbpbot.cli_interface import main
        main()
    except ImportError as e:
        print_colored(f"Erreur lors de l'import: {str(e)}", "RED")
        print_colored("Vérification des dépendances essentielles...", "YELLOW")
        
        # Vérifier les dépendances essentielles pour l'interface CLI
        essential_deps = ["rich", "loguru", "python_dotenv"]
        missing_deps = []
        
        for dep in essential_deps:
            try:
                pkg_name = dep.split("==")[0]
                importlib.import_module(pkg_name)
            except ImportError:
                missing_deps.append(dep)
        
        if missing_deps:
            print_colored(f"Dépendances manquantes: {', '.join(missing_deps)}", "RED")
            print_colored(f"Installez-les avec: pip install {' '.join(missing_deps)}", "YELLOW")
        
        print_colored("\nErreur: Module 'gbpbot.cli_interface' non trouvé.", "RED")
        print_colored("Causes possibles:", "YELLOW")
        print_colored("1. Le répertoire 'gbpbot' n'est pas dans le répertoire courant", "YELLOW")
        print_colored("2. Le fichier 'cli_interface.py' n'existe pas dans le dossier 'gbpbot'", "YELLOW")
        print_colored("3. Des dépendances requises ne sont pas installées", "YELLOW")
        
        sys.exit(1)
    except Exception as e:
        print_colored(f"Erreur lors du lancement du GBPBot: {str(e)}", "RED")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    launch_gbpbot() 