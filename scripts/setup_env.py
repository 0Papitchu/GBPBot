#!/usr/bin/env python3
"""
Script de gestion des fichiers d'environnement pour GBPBot

Ce script permet de :
1. Créer un fichier .env à partir de .env.local
2. Sauvegarder un fichier .env existant
3. Valider la configuration d'environnement
"""

import os
import shutil
import datetime
import re
import sys
from pathlib import Path

def create_backup(env_file='.env'):
    """Crée une sauvegarde du fichier .env actuel"""
    if not os.path.exists(env_file):
        print(f"Le fichier {env_file} n'existe pas, aucune sauvegarde nécessaire.")
        return
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"{env_file}.backup_{timestamp}"
    shutil.copy2(env_file, backup_file)
    print(f"Sauvegarde créée : {backup_file}")

def copy_local_to_env():
    """Copie le fichier .env.local vers .env après confirmation"""
    if not os.path.exists('.env.local'):
        print("Erreur : Le fichier .env.local n'existe pas.")
        print("Créez d'abord un fichier .env.local à partir de .env.example")
        return False
    
    if os.path.exists('.env'):
        # En mode terminal interactif
        if sys.stdin.isatty():
            response = input("Un fichier .env existe déjà. Voulez-vous le remplacer ? (y/n): ")
            if response.lower() != 'y':
                print("Opération annulée.")
                return False
        else:
            # En mode script, créer automatiquement une sauvegarde
            print("Un fichier .env existe déjà. Création d'une sauvegarde...")
        create_backup()
    
    shutil.copy2('.env.local', '.env')
    print("Le fichier .env.local a été copié vers .env avec succès.")
    return True

def validate_env_file(env_file='.env'):
    """Valide le contenu du fichier .env"""
    if not os.path.exists(env_file):
        print(f"Erreur : Le fichier {env_file} n'existe pas.")
        return False
    
    required_vars = [
        'TELEGRAM_BOT_TOKEN', 
        'TELEGRAM_CHAT_ID',
        'PRIVATE_KEY',
        'WALLET_ADDRESS',
        'BINANCE_API_KEY',
        'BINANCE_API_SECRET'
    ]
    
    missing_vars = []
    placeholder_vars = []
    
    with open(env_file, 'r') as file:
        content = file.read()
        
    for var in required_vars:
        if var not in content:
            missing_vars.append(var)
        elif re.search(f"{var}=VOTRE_", content) or re.search(f"{var}=$", content):
            placeholder_vars.append(var)
    
    if missing_vars:
        print(f"Variables manquantes dans {env_file}:")
        for var in missing_vars:
            print(f"  - {var}")
    
    if placeholder_vars:
        print(f"Variables avec des valeurs par défaut dans {env_file}:")
        for var in placeholder_vars:
            print(f"  - {var}")
    
    if not missing_vars and not placeholder_vars:
        print(f"Le fichier {env_file} est valide.")
        return True
    
    return False

def interactive_menu():
    """Affiche un menu interactif"""
    print("=== Gestionnaire de fichiers d'environnement GBPBot ===")
    print("1. Créer une sauvegarde du fichier .env actuel")
    print("2. Copier .env.local vers .env")
    print("3. Valider le fichier .env")
    print("4. Quitter")
    
    choice = input("Votre choix (1-4): ")
    
    if choice == '1':
        create_backup()
    elif choice == '2':
        copy_local_to_env()
    elif choice == '3':
        validate_env_file()
    elif choice == '4':
        return
    else:
        print("Choix invalide.")

def main():
    """Fonction principale du script"""
    # S'assurer que le script est exécuté depuis la racine du projet
    os.chdir(Path(__file__).parent.parent)
    
    # Mode ligne de commande si des arguments sont fournis
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == '1':
            create_backup()
        elif cmd == '2':
            copy_local_to_env()
        elif cmd == '3':
            validate_env_file()
        else:
            print(f"Commande inconnue: {cmd}")
            print("Usage: setup_env.py [1|2|3]")
            print("  1: Créer une sauvegarde du fichier .env")
            print("  2: Copier .env.local vers .env")
            print("  3: Valider le fichier .env")
    else:
        # Mode interactif sans arguments
        interactive_menu()

if __name__ == "__main__":
    main() 