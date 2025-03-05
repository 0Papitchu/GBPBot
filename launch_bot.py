#!/usr/bin/env python
"""
Script de lancement simplifié pour GBPBot
Ce script:
1. Vérifie et installe les dépendances manquantes
2. Lance le bot
"""

import subprocess
import sys
import os
import time

# Liste des dépendances essentielles
REQUIRED_PACKAGES = [
    "loguru",
    "pandas",
    "web3",
    "pytest",
    "pytest-asyncio"
]

def print_colored(text, color="green"):
    """Affiche du texte coloré dans la console"""
    colors = {
        "green": "\033[92m",
        "yellow": "\033[93m",
        "red": "\033[91m",
        "blue": "\033[94m",
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

def launch_bot():
    """Lance le bot"""
    print_colored("\nLancement du GBPBot...", "blue")
    try:
        # Tentative de lancement via le module
        subprocess.run([sys.executable, "-m", "gbpbot.cli"], check=True)
    except subprocess.CalledProcessError:
        print_colored("Erreur lors du lancement via module. Tentative alternative...", "yellow")
        try:
            # Tentative alternative avec le fichier batch
            if os.path.exists("launch_gbpbot_cli.bat"):
                subprocess.run(["launch_gbpbot_cli.bat"], check=True)
            else:
                # Dernière tentative avec le fichier CLI direct
                subprocess.run([sys.executable, "gbpbot_cli.py"], check=True)
        except subprocess.CalledProcessError as e:
            print_colored(f"Erreur lors du lancement du bot: {e}", "red")
            return False
    return True

if __name__ == "__main__":
    print_colored("=== GBPBot - Lanceur Simplifié ===", "blue")
    
    # Étape 1: Installation des dépendances manquantes
    install_missing_packages()
    
    # Étape 2: Lancement du bot
    success = launch_bot()
    
    if success:
        print_colored("\nBot lancé avec succès!", "green")
    else:
        print_colored("\nÉchec du lancement du bot. Veuillez vérifier les erreurs ci-dessus.", "red") 