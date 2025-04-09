#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de configuration de l'environnement de test pour GBPBot

Ce script prépare l'environnement pour exécuter les tests du GBPBot
en installant toutes les dépendances nécessaires, en vérifiant les
configurations et en préparant les données de test.
"""

import os
import sys
import subprocess
import logging
import shutil
import tempfile
from pathlib import Path

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("gbpbot_setup")

# Chemin racine du projet
ROOT_DIR = Path(__file__).resolve().parent

# Liste des dépendances essentielles pour les tests
DEPENDENCIES = [
    # Dépendances de base
    "web3>=6.5.0",
    "eth-account==0.9.0", 
    "solana==0.35.1",
    "base58==2.1.1",
    "cryptography>=43.0.1",
    "python-dotenv==1.0.0",
    "requests==2.31.0",
    "websockets>=10.0,<11.0",
    "aiohttp>=3.10.11",
    
    # Dépendances pour le trading
    "ccxt>=3.1.0,<3.2.0",
    "pandas==2.1.4",
    "numpy>=1.24.3,<1.26.0",
    "ta==0.11.0",
    
    # Dépendances pour la machine learning
    "matplotlib<3.8.0",
    "pandas-ta<0.4.0",
    "xgboost==1.7.6",
    "lightgbm==4.1.0",
    
    # Dépendances pour la sécurité
    "eth-utils>=2.1.1,<2.3.0",
    "eth-typing>=3.3.0,<3.5.0",
    "eth-hash==0.5.2",
    "eth-abi>=5.0.1",
    
    # Dépendances pour les tests
    "pytest==7.4.3",
    "pytest-asyncio>=0.21.1,<0.22.0",
    "pytest-cov==4.1.0",
    "pytest-mock==3.12.0",
    "pytest-timeout==2.2.0",
    "pytest-xdist==3.5.0",
    "pytest-xprocess>=0.23.0",
    "anchorpy>=0.18.0"
]

def check_python_version():
    """
    Vérifie si la version de Python est compatible avec GBPBot.
    
    Returns:
        bool: True si la version est compatible, False sinon
    """
    required_version = (3, 9)
    current_version = sys.version_info
    
    if current_version < required_version:
        logger.error(f"Version de Python incompatible. Python {required_version[0]}.{required_version[1]}+ requis, "
                    f"vous utilisez Python {current_version[0]}.{current_version[1]}")
        return False
    
    logger.info(f"Version de Python compatible: {current_version[0]}.{current_version[1]}")
    return True

def check_dependencies():
    """
    Vérifie si toutes les dépendances requises sont installées.
    
    Returns:
        tuple: (bool, list) où bool indique si toutes les dépendances sont installées,
               et list contient les dépendances manquantes
    """
    try:
        import pkg_resources
        
        missing_deps = []
        installed_deps = {}
        
        # Collecter les dépendances installées
        for package in pkg_resources.working_set:
            installed_deps[package.key] = package.version
        
        # Vérifier les dépendances requises
        for dep in DEPENDENCIES:
            # Extraire le nom du package et la contrainte de version
            parts = dep.replace(">", "=").replace("<", "=").split("=", 1)
            package_name = parts[0].lower()
            
            if package_name not in installed_deps:
                missing_deps.append(dep)
        
        if missing_deps:
            logger.warning(f"Dépendances manquantes: {missing_deps}")
            return False, missing_deps
        
        logger.info("Toutes les dépendances requises sont installées")
        return True, []
    except ImportError:
        # Si pkg_resources n'est pas disponible, on utilise une méthode alternative
        import importlib
        
        missing_deps = []
        
        for dep in DEPENDENCIES:
            # Extraire le nom du package
            package_name = dep.split("==")[0].split(">=")[0].split("<=")[0].split("<")[0].split(">")[0].strip()
            
            try:
                importlib.import_module(package_name)
            except ImportError:
                missing_deps.append(dep)
        
        if missing_deps:
            logger.warning(f"Dépendances manquantes: {missing_deps}")
            return False, missing_deps
        
        logger.info("Toutes les dépendances requises sont installées")
        return True, []

def install_dependencies(missing_deps):
    """
    Installe les dépendances manquantes.
    
    Args:
        missing_deps (list): Liste des dépendances à installer
        
    Returns:
        bool: True si l'installation a réussi, False sinon
    """
    if not missing_deps:
        return True
    
    logger.info(f"Installation des dépendances manquantes: {missing_deps}")
    
    try:
        # Utiliser pip pour installer les dépendances
        cmd = [sys.executable, "-m", "pip", "install"] + missing_deps
        process = subprocess.run(cmd, capture_output=True, text=True)
        
        if process.returncode != 0:
            logger.error(f"Erreur lors de l'installation des dépendances: {process.stderr}")
            return False
        
        logger.info("Dépendances installées avec succès")
        return True
    except Exception as e:
        logger.error(f"Erreur lors de l'installation des dépendances: {str(e)}")
        return False

def check_env_variables():
    """
    Vérifie si les variables d'environnement nécessaires sont configurées.
    Si elles ne sont pas présentes, crée un fichier .env.test avec des valeurs par défaut.
    
    Returns:
        bool: True si la vérification/configuration a réussi, False sinon
    """
    required_vars = [
        "AVALANCHE_RPC_URL",
        "AVALANCHE_CHAIN_ID",
        "AVALANCHE_WEBSOCKET",
        "SOLANA_RPC_URL",
        "SOLANA_WEBSOCKET_URL"
    ]
    
    missing_vars = [var for var in required_vars if os.environ.get(var) is None]
    
    if missing_vars:
        logger.warning(f"Variables d'environnement manquantes: {missing_vars}")
        
        # Créer un fichier .env.test avec des valeurs par défaut pour les tests
        env_file = ROOT_DIR / ".env.test"
        
        with open(env_file, "w") as f:
            f.write("# Fichier de configuration pour les tests\n\n")
            f.write("GBPBOT_ENV=test\n")
            
            # Ajouter les variables manquantes avec des valeurs par défaut
            for var in missing_vars:
                if var == "AVALANCHE_RPC_URL":
                    f.write("AVALANCHE_RPC_URL=https://api.avax-test.network/ext/bc/C/rpc\n")
                elif var == "AVALANCHE_CHAIN_ID":
                    f.write("AVALANCHE_CHAIN_ID=43113\n")
                elif var == "AVALANCHE_WEBSOCKET":
                    f.write("AVALANCHE_WEBSOCKET=wss://api.avax-test.network/ext/bc/C/ws\n")
                elif var == "SOLANA_RPC_URL":
                    f.write("SOLANA_RPC_URL=https://api.testnet.solana.com\n")
                elif var == "SOLANA_WEBSOCKET_URL":
                    f.write("SOLANA_WEBSOCKET_URL=wss://api.testnet.solana.com\n")
        
        # Charger les variables d'environnement depuis le fichier .env.test
        import dotenv
        dotenv.load_dotenv(env_file)
        
        logger.info(f"Variables d'environnement configurées dans {env_file}")
    
    return True

def create_test_wallets():
    """
    Crée des fichiers de configuration de wallet pour les tests.
    
    Returns:
        list: Liste des chemins des fichiers de wallet créés
    """
    wallet_dir = ROOT_DIR / "test_wallets"
    wallet_dir.mkdir(exist_ok=True)
    
    # Créer des fichiers de wallet de test
    wallets = {
        "avalanche_wallet.json": {
            "address": "0xTestWalletAddress123",
            "private_key": "test-private-key-not-real"
        },
        "solana_wallet.json": {
            "address": "TestSolanaAddress123",
            "private_key": "test-solana-private-key-not-real"
        }
    }
    
    wallet_paths = []
    
    for filename, content in wallets.items():
        wallet_path = wallet_dir / filename
        
        import json
        with open(wallet_path, "w") as f:
            json.dump(content, f, indent=4)
        
        wallet_paths.append(str(wallet_path))
    
    logger.info(f"Wallets de test créés dans {wallet_dir}")
    return wallet_paths

def check_test_data():
    """
    Vérifie si les données de test nécessaires sont disponibles.
    Si elles ne sont pas présentes, crée des données de test par défaut.
    
    Returns:
        bool: True si la vérification/création a réussi, False sinon
    """
    test_data_dir = ROOT_DIR / "test_data"
    test_data_dir.mkdir(exist_ok=True)
    
    # Données de test pour les modules
    test_data = {
        "price_history": {
            "AVAX-USDC_1h.csv": [
                "timestamp,open,high,low,close,volume",
                "1640995200,86.23,87.45,85.67,86.98,120000",
                "1640998800,86.98,88.12,86.54,87.65,145000",
                "1641002400,87.65,89.34,87.21,88.97,180000"
            ],
            "AVAX-USDC_1d.csv": [
                "timestamp,open,high,low,close,volume",
                "1609459200,54.23,57.45,52.67,56.98,520000",
                "1609545600,56.98,58.12,55.54,57.65,645000",
                "1609632000,57.65,59.34,56.21,58.97,780000"
            ]
        },
        "tokens": {
            "tokens.json": {
                "tokens": [
                    {
                        "symbol": "AVAX",
                        "name": "Avalanche",
                        "address": "0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7",
                        "decimals": 18,
                        "chainId": 43114
                    },
                    {
                        "symbol": "USDC",
                        "name": "USD Coin",
                        "address": "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E",
                        "decimals": 6,
                        "chainId": 43114
                    }
                ]
            }
        }
    }
    
    # Créer les fichiers de données de test
    for category, files in test_data.items():
        category_dir = test_data_dir / category
        category_dir.mkdir(exist_ok=True)
        
        for filename, content in files.items():
            file_path = category_dir / filename
            
            if filename.endswith(".csv"):
                # Fichier CSV
                with open(file_path, "w") as f:
                    f.write("\n".join(content))
            elif filename.endswith(".json"):
                # Fichier JSON
                import json
                with open(file_path, "w") as f:
                    json.dump(content, f, indent=4)
    
    logger.info(f"Données de test créées dans {test_data_dir}")
    return True

def setup_environment():
    """
    Configure l'environnement de test complet.
    
    Returns:
        bool: True si la configuration a réussi, False sinon
    """
    # Vérifier la version de Python
    if not check_python_version():
        return False
    
    # Vérifier les dépendances
    deps_ok, missing_deps = check_dependencies()
    if not deps_ok:
        # Installer les dépendances manquantes
        if not install_dependencies(missing_deps):
            return False
    
    # Vérifier les variables d'environnement
    if not check_env_variables():
        return False
    
    # Créer des wallets de test
    wallet_paths = create_test_wallets()
    
    # Vérifier/créer les données de test
    if not check_test_data():
        return False
    
    logger.info("Environnement de test configuré avec succès")
    return True

def main():
    """
    Fonction principale du script.
    """
    logger.info("=" * 80)
    logger.info("Configuration de l'environnement de test pour GBPBot")
    logger.info("=" * 80)
    
    # Configurer l'environnement
    success = setup_environment()
    
    logger.info("=" * 80)
    logger.info(f"Configuration {'terminée avec succès' if success else 'échouée'}")
    logger.info("=" * 80)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 