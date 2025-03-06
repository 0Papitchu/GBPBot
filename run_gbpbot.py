#!/usr/bin/env python3
"""
Script de lancement pour le GBPBot
=================================

Ce script permet de démarrer le menu principal du GBPBot avec une meilleure
gestion des erreurs et une vérification de l'environnement.
"""

import sys
import os
import logging
import asyncio
import traceback
import argparse
from pathlib import Path

# Configurer le logging de base
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"logs/gbpbot_launcher.log", mode='a'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("gbpbot.launcher")

def ensure_directories():
    """Crée les répertoires nécessaires au fonctionnement du bot"""
    directories = [
        "logs",
        "data", 
        "data/models", 
        "data/tokens", 
        "data/trading", 
        "data/auto_mode",
        "exports"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        
    logger.info("Répertoires vérifiés et créés si nécessaire")

def check_dependencies():
    """Vérifie que les dépendances Python sont installées"""
    try:
        # Liste des packages critiques à vérifier
        critical_packages = [
            "web3", "loguru", "numpy", "requests", 
            "pandas", "aiohttp", "pydantic"
        ]
        
        missing_packages = []
        
        for package in critical_packages:
            try:
                __import__(package)
            except ImportError:
                missing_packages.append(package)
                
        if missing_packages:
            logger.warning(f"Dépendances manquantes: {', '.join(missing_packages)}")
            return False, missing_packages
        
        return True, []
        
    except Exception as e:
        logger.error(f"Erreur lors de la vérification des dépendances: {e}")
        return False, ["Erreur lors de la vérification"]

async def main():
    """Fonction principale pour lancer le GBPBot"""
    try:
        # Afficher un message de bienvenue
        print("\n" + "="*60)
        print("               GBPBot - Trading Automatisé                ")
        print("="*60 + "\n")
        
        # Vérifier que Python 3.7+ est utilisé
        if sys.version_info < (3, 7):
            print("❌ GBPBot nécessite Python 3.7 ou supérieur")
            sys.exit(1)
        
        # S'assurer que les répertoires nécessaires existent
        ensure_directories()
        
        # Vérifier les dépendances
        deps_ok, missing_packages = check_dependencies()
        if not deps_ok:
            print(f"⚠️ Certaines dépendances sont manquantes: {', '.join(missing_packages)}")
            choice = input("Voulez-vous essayer de les installer maintenant? (o/n): ")
            if choice.lower() == "o":
                try:
                    import subprocess
                    print("Installation des dépendances en cours...")
                    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
                    print("✅ Les dépendances ont été installées avec succès.")
                except Exception as install_error:
                    print(f"❌ Erreur lors de l'installation: {install_error}")
                    sys.exit(1)
            else:
                print("⚠️ Le bot pourrait ne pas fonctionner correctement sans ces dépendances.")
        
        # Vérifier les fichiers de configuration
        config_path = Path(".env")
        if not config_path.exists():
            print("⚠️ Fichier .env non trouvé.")
            if Path(".env.example").exists():
                choice = input("Voulez-vous copier .env.example vers .env? (o/n): ")
                if choice.lower() == "o":
                    import shutil
                    shutil.copy(".env.example", ".env")
                    print("✅ Fichier .env créé à partir du modèle.")
                else:
                    print("⚠️ Vous devrez créer un fichier .env manuellement.")
            else:
                print("❌ Fichier .env.example non trouvé. Veuillez créer un fichier .env manuellement.")
        
        # Vérifier l'installation et exécuter le menu principal
        try:
            from gbpbot.gbpbot_menu import main as gbpbot_main
            
            print("✅ Initialisation terminée. Démarrage du GBPBot...")
            # Exécuter le menu principal du GBPBot
            await gbpbot_main()
            
        except ImportError as e:
            logger.error(f"Erreur lors de l'importation des modules: {e}")
            print(f"❌ Erreur lors de l'importation de GBPBot: {e}")
            print("⚠️ Assurez-vous que GBPBot est correctement installé")
            
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️ Interruption par l'utilisateur. Fermeture de GBPBot.")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"Erreur inattendue: {e}")
        print(f"\n❌ Une erreur inattendue s'est produite: {str(e)}")
        traceback.print_exc()
        sys.exit(1)

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Lanceur pour GBPBot")
    parser.add_argument("--testnet", action="store_true", help="Démarrer le bot en mode testnet")
    parser.add_argument("--debug", action="store_true", help="Activer les logs de debug")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    
    # Configurer le niveau de logging si debug est activé
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Mode debug activé")
    
    # Exécuter la fonction principale
    asyncio.run(main()) 