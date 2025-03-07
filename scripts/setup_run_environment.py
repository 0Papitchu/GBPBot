#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de configuration de l'environnement d'exécution du GBPBot.

Ce script permet de configurer facilement toutes les variables nécessaires
au fonctionnement du GBPBot en une seule étape.
"""

import os
import sys
import json
import logging
import shutil
import getpass
from pathlib import Path
from datetime import datetime
import argparse

# Ajouter le répertoire racine au path
script_dir = Path(__file__).parent
root_dir = script_dir.parent
sys.path.insert(0, str(root_dir))

# Configuration du logging
log_dir = root_dir / "logs"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f"setup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("setup")

def print_header():
    """Affiche l'en-tête du script"""
    print("\n" + "="*60)
    print(" "*20 + "GBPBot - Configuration")
    print("="*60 + "\n")
    print("Ce script va vous guider pour configurer GBPBot.\n")

def parse_arguments():
    """Parse les arguments de ligne de commande"""
    parser = argparse.ArgumentParser(description="Configuration de l'environnement GBPBot")
    parser.add_argument("--non-interactive", action="store_true", help="Mode non interactif")
    parser.add_argument("--config-file", help="Fichier de configuration existant")
    parser.add_argument("--only-missing", action="store_true", help="Ne configurer que les paramètres manquants")
    parser.add_argument("--skip-blockchain", action="store_true", help="Ignorer la configuration blockchain")
    parser.add_argument("--skip-telegram", action="store_true", help="Ignorer la configuration Telegram")
    parser.add_argument("--skip-openai", action="store_true", help="Ignorer la configuration OpenAI")
    parser.add_argument("--skip-security", action="store_true", help="Ignorer la configuration du gestionnaire de secrets")
    return parser.parse_args()

def create_env_file():
    """Crée le fichier .env à partir du modèle ou copie l'optimisé"""
    env_path = root_dir / ".env"
    if env_path.exists():
        backup_file = root_dir / f".env.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(env_path, backup_file)
        print(f"Fichier .env existant sauvegardé dans {backup_file}")
    
    optimized_env = root_dir / ".env.optimized"
    example_env = root_dir / ".env.example"
    
    if optimized_env.exists():
        shutil.copy2(optimized_env, env_path)
        print("Fichier .env optimisé copié.")
        return True
    elif example_env.exists():
        shutil.copy2(example_env, env_path)
        print("Fichier .env créé à partir du modèle d'exemple.")
        return True
    else:
        print("ERREUR: Aucun fichier modèle trouvé (.env.example ou .env.optimized)")
        return False

def update_env_var(key, value):
    """Met à jour une variable d'environnement dans le fichier .env"""
    env_path = root_dir / ".env"
    if not env_path.exists():
        logger.error("Fichier .env non trouvé")
        return False
    
    lines = []
    key_found = False
    
    with open(env_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    # Rechercher et mettre à jour la clé
    for i, line in enumerate(lines):
        if line.strip().startswith(f"{key}="):
            lines[i] = f"{key}={value}\n"
            key_found = True
            break
    
    # Si la clé n'existe pas, l'ajouter à la fin
    if not key_found:
        lines.append(f"{key}={value}\n")
    
    # Écrire les modifications
    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    
    return True

def setup_secrets_manager():
    """Configure le gestionnaire de secrets"""
    print("\n--- Configuration du gestionnaire de secrets ---\n")
    
    try:
        # Importer conditionnellement
        from gbpbot.core.security.secrets_manager import SecretsManager
        
        # Créer le gestionnaire de secrets
        if input("Utiliser un mot de passe maître pour le chiffrement? (o/n) [n]: ").lower() in ("o", "oui", "y", "yes"):
            master_password = getpass.getpass("Mot de passe maître: ")
            confirm_password = getpass.getpass("Confirmez le mot de passe: ")
            
            if master_password != confirm_password:
                print("Les mots de passe ne correspondent pas!")
                return None
                
            sm = SecretsManager(master_password=master_password)
        else:
            sm = SecretsManager()
        
        print("✅ Gestionnaire de secrets configuré avec succès")
        return sm
    except ImportError:
        logger.warning("Module de gestion des secrets non disponible")
        return None
    except Exception as e:
        logger.error(f"Erreur lors de la configuration du gestionnaire de secrets: {e}")
        return None

def configure_blockchain(sm=None):
    """Configure les accès blockchain"""
    print("\n--- Configuration Blockchain ---\n")
    
    # Configuration Solana
    solana_private_key = getpass.getpass("Clé privée Solana (laisser vide pour skip): ")
    solana_rpc = input("URL RPC Solana [https://api.mainnet-beta.solana.com]: ") or "https://api.mainnet-beta.solana.com"
    
    # Configuration Avalanche
    avax_private_key = getpass.getpass("Clé privée Avalanche (laisser vide pour skip): ")
    avax_rpc = input("URL RPC Avalanche [https://api.avax.network/ext/bc/C/rpc]: ") or "https://api.avax.network/ext/bc/C/rpc"
    
    # Mettre à jour le .env
    if solana_private_key:
        update_env_var("SOLANA_PRIVATE_KEY", solana_private_key)
    update_env_var("SOLANA_RPC_URL", solana_rpc)
    
    if avax_private_key:
        update_env_var("PRIVATE_KEY", avax_private_key)
    update_env_var("AVAX_RPC_URL", avax_rpc)
    
    # Sécuriser avec SecretsManager si disponible
    if sm and (solana_private_key or avax_private_key):
        try:
            secrets = sm.get_secrets()
            if solana_private_key:
                secrets["SOLANA_PRIVATE_KEY"] = solana_private_key
            if avax_private_key:
                secrets["AVALANCHE_PRIVATE_KEY"] = avax_private_key
            sm.store_secrets(secrets)
            print("Clés privées stockées de façon sécurisée.")
        except Exception as e:
            logger.error(f"Erreur lors du stockage sécurisé des clés: {e}")
    
    print("✅ Configuration blockchain mise à jour.")

def configure_telegram(sm=None):
    """Configure les accès Telegram"""
    print("\n--- Configuration Telegram ---\n")
    
    activate = input("Activer l'interface Telegram? (o/n) [n]: ").lower() in ("o", "oui", "y", "yes")
    
    update_env_var("TELEGRAM_ENABLED", "true" if activate else "false")
    
    if not activate:
        return
    
    telegram_token = input("Token Telegram Bot (obtenable via @BotFather): ")
    telegram_users = input("IDs utilisateurs autorisés (séparés par des virgules): ")
    
    # Mettre à jour le .env
    if telegram_token:
        update_env_var("TELEGRAM_BOT_TOKEN", telegram_token)
    if telegram_users:
        update_env_var("TELEGRAM_ALLOWED_USERS", telegram_users)
    
    # Sécuriser avec SecretsManager si disponible
    if sm and telegram_token:
        try:
            secrets = sm.get_secrets()
            secrets["TELEGRAM_BOT_TOKEN"] = telegram_token
            sm.store_secrets(secrets)
            print("Token Telegram stocké de façon sécurisée.")
        except Exception as e:
            logger.error(f"Erreur lors du stockage sécurisé du token: {e}")
    
    print("✅ Configuration Telegram mise à jour.")

def configure_openai(sm=None):
    """Configure les accès OpenAI pour les fonctionnalités IA"""
    print("\n--- Configuration OpenAI (IA) ---\n")
    
    activate = input("Activer les fonctionnalités IA? (o/n) [n]: ").lower() in ("o", "oui", "y", "yes")
    
    update_env_var("AI_ENABLED", "true" if activate else "false")
    
    if not activate:
        return
    
    openai_key = getpass.getpass("Clé API OpenAI: ")
    openai_model = input("Modèle OpenAI [gpt-3.5-turbo]: ") or "gpt-3.5-turbo"
    
    # Mettre à jour le .env
    if openai_key:
        update_env_var("OPENAI_API_KEY", openai_key)
    update_env_var("OPENAI_MODEL", openai_model)
    
    # Sécuriser avec SecretsManager si disponible
    if sm and openai_key:
        try:
            secrets = sm.get_secrets()
            secrets["OPENAI_API_KEY"] = openai_key
            sm.store_secrets(secrets)
            print("Clé API OpenAI stockée de façon sécurisée.")
        except Exception as e:
            logger.error(f"Erreur lors du stockage sécurisé de la clé API: {e}")
    
    print("✅ Configuration OpenAI mise à jour.")

def configure_trading_limits():
    """Configure les limites de trading pour la sécurité"""
    print("\n--- Configuration des Limites de Trading ---\n")
    
    max_trade = input("Montant maximum par trade en USD [100]: ") or "100"
    max_daily = input("Montant maximum quotidien en USD [500]: ") or "500"
    min_profit = input("Profit minimum pour arbitrage en % [0.5]: ") or "0.5"
    max_slippage = input("Slippage maximum en % [2.0]: ") or "2.0"
    
    # Mettre à jour le .env
    update_env_var("MAX_TRADE_AMOUNT_USD", max_trade)
    update_env_var("MAX_DAILY_AMOUNT_USD", max_daily)
    update_env_var("MIN_PROFIT_THRESHOLD", min_profit)
    update_env_var("MAX_SLIPPAGE", max_slippage)
    
    print("✅ Configuration des limites de trading mise à jour.")

def test_configuration():
    """Teste la configuration pour s'assurer qu'elle est fonctionnelle"""
    print("\n--- Test de la configuration ---\n")
    
    tests_passed = True
    
    # Vérifier le fichier .env
    env_path = root_dir / ".env"
    if not env_path.exists():
        print("❌ Fichier .env non trouvé")
        tests_passed = False
    else:
        print("✅ Fichier .env trouvé")
    
    # Tester l'accès au RPC Solana
    try:
        import requests
        solana_rpc = os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
        response = requests.post(
            solana_rpc,
            json={"jsonrpc": "2.0", "id": 1, "method": "getHealth"},
            timeout=5
        )
        if response.status_code == 200 and "result" in response.json():
            print(f"✅ Connexion au RPC Solana réussie: {solana_rpc}")
        else:
            print(f"❌ Échec de la connexion au RPC Solana: {solana_rpc}")
            tests_passed = False
    except Exception as e:
        print(f"❌ Erreur lors du test de connexion au RPC Solana: {e}")
        tests_passed = False
    
    # Tester les dépendances critiques
    try:
        import solana
        print("✅ Bibliothèque Solana trouvée")
    except ImportError:
        print("❌ Bibliothèque Solana non trouvée")
        tests_passed = False
    
    try:
        from web3 import Web3
        print("✅ Bibliothèque Web3 trouvée")
    except ImportError:
        print("❌ Bibliothèque Web3 non trouvée")
        tests_passed = False
    
    # Vérifier les logs
    logs_dir = root_dir / "logs"
    if not logs_dir.exists() or not logs_dir.is_dir():
        print("❌ Répertoire logs non trouvé")
        tests_passed = False
    else:
        print("✅ Répertoire logs trouvé")
    
    return tests_passed

def main():
    """Fonction principale d'exécution"""
    args = parse_arguments()
    print_header()
    
    # Créer le fichier .env de base
    if not create_env_file():
        print("Impossible de continuer sans fichier de configuration de base.")
        sys.exit(1)
    
    # Configurer le gestionnaire de secrets
    sm = None
    if not args.skip_security:
        sm = setup_secrets_manager()
    
    # Configurer les différentes sections
    if not args.skip_blockchain:
        configure_blockchain(sm)
    
    if not args.skip_telegram:
        configure_telegram(sm)
    
    if not args.skip_openai:
        configure_openai(sm)
    
    # Toujours configurer les limites de trading
    configure_trading_limits()
    
    # Tester la configuration
    print("\n--- Vérification de la configuration ---\n")
    tests_passed = test_configuration()
    
    print("\n" + "="*60)
    if tests_passed:
        print(" "*15 + "Configuration terminée avec succès!")
    else:
        print(" "*10 + "Configuration terminée avec des avertissements!")
        print("Veuillez revoir les messages d'erreur ci-dessus.")
    print("="*60 + "\n")
    
    print("Vous pouvez maintenant démarrer GBPBot:")
    print("  - Windows: start_gbpbot.bat")
    print("  - Linux/Mac: ./start_gbpbot.sh")
    print("\nPour des configurations avancées, éditez le fichier .env directement.")
    print(f"Journal de configuration disponible dans: {log_file}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nConfiguration annulée par l'utilisateur.")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"Erreur lors de la configuration: {e}")
        print(f"\nErreur lors de la configuration: {e}")
        sys.exit(1) 