#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mise à jour du fichier .env pour GBPBot
=======================================

Ce script met à jour le fichier .env existant avec les paramètres nécessaires
pour les connexions blockchain et autres configurations.
"""

import os
import sys
import re
import json
import getpass
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("env_updater")

# Essayer d'importer dotenv
try:
    from dotenv import load_dotenv, set_key, find_dotenv
    logger.info("Module python-dotenv trouvé")
except ImportError:
    logger.error("Module python-dotenv non trouvé. Installez-le avec: pip install python-dotenv")
    sys.exit(1)

def read_env_file(env_path: str) -> Dict[str, str]:
    """
    Lit un fichier .env et retourne son contenu sous forme de dictionnaire
    
    Args:
        env_path: Chemin vers le fichier .env
        
    Returns:
        Dict[str, str]: Variables d'environnement et leurs valeurs
    """
    env_dict = {}
    
    try:
        with open(env_path, 'r') as file:
            for line in file:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                    
                if '=' in line:
                    key, value = line.split('=', 1)
                    env_dict[key.strip()] = value.strip()
    except Exception as e:
        logger.error(f"Erreur lors de la lecture du fichier .env: {e}")
    
    return env_dict

def update_env_file(env_path: str, updates: Dict[str, str]) -> bool:
    """
    Met à jour un fichier .env avec de nouvelles valeurs
    
    Args:
        env_path: Chemin vers le fichier .env
        updates: Dictionnaire des variables à mettre à jour
        
    Returns:
        bool: True si la mise à jour a réussi, False sinon
    """
    try:
        # Charger l'environnement actuel
        dotenv_path = find_dotenv(env_path)
        if not dotenv_path:
            logger.error(f"Fichier .env non trouvé à {env_path}")
            return False
            
        # Mettre à jour chaque variable
        for key, value in updates.items():
            logger.info(f"Mise à jour de {key}")
            set_key(dotenv_path, key, value)
            
        logger.info(f"Fichier .env mis à jour avec succès: {env_path}")
        return True
        
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour du fichier .env: {e}")
        return False

def check_env_exists():
    """Vérifie si le fichier .env existe et propose de le créer si nécessaire"""
    if not os.path.exists(".env"):
        logger.warning("Fichier .env non trouvé")
        
        # Vérifier si .env.example existe
        if os.path.exists(".env.example"):
            logger.info("Fichier .env.example trouvé")
            create = input("Voulez-vous créer un fichier .env à partir de .env.example? (O/n): ")
            
            if create.lower() != "n":
                try:
                    with open(".env.example", "r") as example_file:
                        with open(".env", "w") as env_file:
                            env_file.write(example_file.read())
                    logger.info("Fichier .env créé avec succès")
                    return True
                except Exception as e:
                    logger.error(f"Erreur lors de la création du fichier .env: {e}")
                    return False
            else:
                logger.info("Création du fichier .env annulée")
                return False
        else:
            logger.error("Fichier .env.example non trouvé")
            create_empty = input("Voulez-vous créer un fichier .env vide? (O/n): ")
            
            if create_empty.lower() != "n":
                try:
                    with open(".env", "w") as env_file:
                        env_file.write("# Configuration GBPBot\n\n")
                    logger.info("Fichier .env vide créé avec succès")
                    return True
                except Exception as e:
                    logger.error(f"Erreur lors de la création du fichier .env: {e}")
                    return False
            else:
                logger.info("Création du fichier .env annulée")
                return False
    else:
        logger.info("Fichier .env trouvé")
        return True

def get_blockchain_configs() -> Dict[str, str]:
    """
    Demande à l'utilisateur les configurations blockchain nécessaires
    
    Returns:
        Dict[str, str]: Configurations blockchain
    """
    configs = {}
    
    # Solana RPC
    default_solana_rpc = "https://api.mainnet-beta.solana.com"
    solana_rpc = input(f"URL RPC Solana [{default_solana_rpc}]: ")
    configs["SOLANA_RPC_URL"] = solana_rpc if solana_rpc else default_solana_rpc
    
    # Solana WebSocket
    default_solana_ws = "wss://api.mainnet-beta.solana.com"
    solana_ws = input(f"URL WebSocket Solana [{default_solana_ws}]: ")
    configs["SOLANA_WEBSOCKET_URL"] = solana_ws if solana_ws else default_solana_ws
    
    # Solana Private Key (option pour masquer l'entrée)
    solana_key = getpass.getpass("Clé privée Solana (laissez vide pour garder existante): ")
    if solana_key:
        configs["SOLANA_PRIVATE_KEY"] = solana_key
    
    # Avalanche RPC
    default_avalanche_rpc = "https://api.avax.network/ext/bc/C/rpc"
    avalanche_rpc = input(f"URL RPC Avalanche [{default_avalanche_rpc}]: ")
    configs["AVALANCHE_RPC_URL"] = avalanche_rpc if avalanche_rpc else default_avalanche_rpc
    
    # Avalanche Private Key (option pour masquer l'entrée)
    avalanche_key = getpass.getpass("Clé privée Avalanche (laissez vide pour garder existante): ")
    if avalanche_key:
        configs["AVALANCHE_PRIVATE_KEY"] = avalanche_key
    
    return configs

def get_dex_configs() -> Dict[str, str]:
    """
    Demande à l'utilisateur les configurations DEX nécessaires
    
    Returns:
        Dict[str, str]: Configurations DEX
    """
    configs = {}
    
    # TraderJoe (utilise Avalanche par défaut)
    use_custom_traderjoe = input("Utiliser un RPC personnalisé pour TraderJoe? (o/N): ")
    if use_custom_traderjoe.lower() == "o":
        traderjoe_rpc = input("URL RPC TraderJoe: ")
        if traderjoe_rpc:
            configs["TRADERJOE_RPC_URL"] = traderjoe_rpc
    
    # Raydium (utilise Solana par défaut)
    use_custom_raydium = input("Utiliser un RPC personnalisé pour Raydium? (o/N): ")
    if use_custom_raydium.lower() == "o":
        raydium_rpc = input("URL RPC Raydium: ")
        if raydium_rpc:
            configs["RAYDIUM_RPC_URL"] = raydium_rpc
    
    return configs

def get_bot_configs() -> Dict[str, str]:
    """
    Demande à l'utilisateur les configurations générales du bot
    
    Returns:
        Dict[str, str]: Configurations générales
    """
    configs = {}
    
    # Mode simulation
    simulation_mode = input("Activer le mode simulation? (O/n): ")
    configs["SIMULATION_MODE"] = "True" if simulation_mode.lower() != "n" else "False"
    
    # Mode debug
    debug_mode = input("Activer le mode debug? (o/N): ")
    configs["DEBUG_MODE"] = "True" if debug_mode.lower() == "o" else "False"
    
    # Niveau de log
    log_level_options = ["INFO", "DEBUG", "WARNING", "ERROR", "CRITICAL"]
    log_level = input(f"Niveau de log {log_level_options} [INFO]: ")
    configs["LOG_LEVEL"] = log_level if log_level in log_level_options else "INFO"
    
    return configs

def main():
    """Fonction principale pour mettre à jour le fichier .env"""
    print("\n" + "="*50)
    print(" "*10 + "GBPBot - Mise à jour des Configurations")
    print("="*50 + "\n")
    
    # Vérifier si .env existe
    if not check_env_exists():
        return
    
    # Charger les variables d'environnement actuelles
    load_dotenv()
    env_path = os.path.abspath(".env")
    
    print("\nCette utilitaire va mettre à jour votre fichier .env avec les paramètres nécessaires.")
    print("Appuyez sur Enter pour conserver les valeurs par défaut ou existantes.\n")
    
    # Sélectionner les configurations à mettre à jour
    print("Quelles configurations souhaitez-vous mettre à jour?")
    print("1. Connexions blockchain")
    print("2. Connexions DEX")
    print("3. Configurations générales du bot")
    print("4. Tout mettre à jour")
    print("5. Quitter sans modifications")
    
    choice = input("\nVotre choix (1-5): ")
    
    updates = {}
    
    if choice == "1" or choice == "4":
        blockchain_configs = get_blockchain_configs()
        updates.update(blockchain_configs)
    
    if choice == "2" or choice == "4":
        dex_configs = get_dex_configs()
        updates.update(dex_configs)
    
    if choice == "3" or choice == "4":
        bot_configs = get_bot_configs()
        updates.update(bot_configs)
    
    if choice == "5":
        print("Aucune modification effectuée. Au revoir!")
        return
    
    # Mettre à jour le fichier .env
    if updates:
        print("\nRécapitulatif des modifications:")
        for key, value in updates.items():
            # Masquer les clés privées
            if "PRIVATE_KEY" in key:
                display_value = "***" + value[-4:] if value else "(vide)"
            else:
                display_value = value
            print(f"{key}: {display_value}")
        
        confirm = input("\nConfirmer ces modifications? (O/n): ")
        
        if confirm.lower() != "n":
            success = update_env_file(env_path, updates)
            
            if success:
                print("\n✅ Fichier .env mis à jour avec succès!")
                
                # Suggérer le test des connexions
                test_connections = input("\nSouhaitez-vous tester les connexions blockchain maintenant? (O/n): ")
                if test_connections.lower() != "n":
                    try:
                        # Exécuter le script de test
                        import subprocess
                        subprocess.run([sys.executable, "test_blockchain_connections.py"])
                    except Exception as e:
                        logger.error(f"Erreur lors du lancement du test: {e}")
                
            else:
                print("\n❌ Échec de la mise à jour du fichier .env.")
        else:
            print("\nMise à jour annulée.")
    
    print("\nAu revoir!")

if __name__ == "__main__":
    main() 