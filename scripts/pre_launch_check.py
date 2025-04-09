#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de vérification pré-lancement pour GBPBot
================================================

Ce script effectue une série de vérifications critiques avant le lancement
du GBPBot pour s'assurer que tout est correctement configuré et que les 
services nécessaires sont disponibles.
"""

import os
import sys
import time
import json
import logging
import requests
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional

# Ajouter le répertoire parent au chemin pour les imports
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

try:
    from dotenv import load_dotenv
except ImportError:
    print("dotenv non installé. Installation en cours...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "python-dotenv"])
    from dotenv import load_dotenv

# Configuration du logging
LOG_DIR = ROOT_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / f"pre_launch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("pre_launch")

# Constantes
STATUS_SUCCESS = "✅ Réussi"
STATUS_WARNING = "⚠️ Avertissement"
STATUS_ERROR = "❌ Échec"
CONFIG_DIR = ROOT_DIR / "config"

def print_header():
    """Affiche l'en-tête du script"""
    print("\n" + "=" * 60)
    print(f"  VÉRIFICATION PRÉ-LANCEMENT GBPBOT - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60 + "\n")

def check_environment_variables() -> Tuple[bool, Dict]:
    """
    Vérifie les variables d'environnement essentielles
    
    Returns:
        Tuple[bool, Dict]: Succès (True/False) et résultats détaillés
    """
    result = {
        "status": "ok",
        "missing_vars": [],
        "empty_vars": [],
        "details": {}
    }
    
    # Chargement du fichier .env
    env_file = ROOT_DIR / ".env"
    if not env_file.exists():
        logger.error(f"Fichier .env introuvable: {env_file}")
        result["status"] = "error"
        result["details"]["file_exists"] = False
        return False, result
    
    load_dotenv(env_file)
    
    # Variables d'environnement essentielles par catégorie
    essential_vars = {
        "Général": ["BOT_MODE", "LOG_LEVEL"],
        "Blockchain": ["RPC_URL", "CHAIN_ID"],
        "Wallets": ["WALLET_ADDRESS"],
        "Trading": ["MAX_SLIPPAGE", "GAS_PRICE_STRATEGY"]
    }
    
    # Vérification des variables
    for category, vars_list in essential_vars.items():
        result["details"][category] = {}
        
        for var_name in vars_list:
            var_value = os.environ.get(var_name)
            
            if var_value is None:
                result["status"] = "error"
                result["missing_vars"].append(var_name)
                result["details"][category][var_name] = "missing"
            elif var_value.strip() == "":
                result["status"] = "warning"
                result["empty_vars"].append(var_name)
                result["details"][category][var_name] = "empty"
            else:
                result["details"][category][var_name] = "ok"
    
    success = result["status"] == "ok"
    
    if success:
        logger.info("✅ Variables d'environnement: Toutes les variables requises sont présentes")
    else:
        if result["missing_vars"]:
            logger.error(f"❌ Variables d'environnement: Variables manquantes: {', '.join(result['missing_vars'])}")
        if result["empty_vars"]:
            logger.warning(f"⚠️ Variables d'environnement: Variables vides: {', '.join(result['empty_vars'])}")
    
    return success, result

def check_rpc_connection() -> Tuple[bool, Dict]:
    """
    Vérifie la connexion aux nœuds RPC configurés
    
    Returns:
        Tuple[bool, Dict]: Succès (True/False) et résultats détaillés
    """
    results = {
        "success": True,
        "tested": 0,
        "successful": 0,
        "endpoints": {}
    }
    
    # Charger le fichier de configuration
    config_file = CONFIG_DIR / "config.yaml"
    if not config_file.exists():
        logger.error(f"❌ Fichier de configuration introuvable: {config_file}")
        return False, results
    
    # Lire l'URL RPC depuis .env
    rpc_url = os.environ.get("RPC_URL")
    
    if not rpc_url:
        logger.error("❌ URL RPC non trouvée dans .env")
        results["success"] = False
        return False, results
    
    # Tester la connexion
    try:
        results["tested"] += 1
        response = requests.post(
            rpc_url,
            json={"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1},
            timeout=5
        )
        
        results["endpoints"][rpc_url] = {}
        
        if response.status_code == 200 and "result" in response.json():
            logger.info(f"✅ Connexion RPC OK: {rpc_url}")
            results["successful"] += 1
            results["endpoints"][rpc_url]["status"] = "ok"
            results["endpoints"][rpc_url]["block"] = int(response.json()["result"], 16)
        else:
            logger.error(f"❌ Erreur RPC: {response.text}")
            results["success"] = False
            results["endpoints"][rpc_url]["status"] = "error"
            results["endpoints"][rpc_url]["message"] = response.text
    except Exception as e:
        logger.error(f"❌ Erreur de connexion RPC: {str(e)}")
        results["success"] = False
        results["endpoints"][rpc_url] = {"status": "error", "message": str(e)}
    
    return results["success"], results

def check_storage_permissions() -> Tuple[bool, Dict]:
    """
    Vérifie les permissions d'écriture dans les dossiers critiques
    
    Returns:
        Tuple[bool, Dict]: Succès (True/False) et résultats détaillés
    """
    critical_dirs = [
        ("logs", ROOT_DIR / "logs"),
        ("wallets", ROOT_DIR / "wallets"),
        ("config", ROOT_DIR / "config"),
        ("cache", ROOT_DIR / "cache")
    ]
    
    results = {"directories": {}}
    all_success = True
    
    for name, dir_path in critical_dirs:
        # Créer le répertoire s'il n'existe pas
        os.makedirs(dir_path, exist_ok=True)
        
        # Tester l'écriture
        test_file = dir_path / f"test_{int(time.time())}.tmp"
        try:
            with open(test_file, 'w') as f:
                f.write("Test d'écriture")
            
            # Si l'écriture réussit, supprimer le fichier
            os.remove(test_file)
            logger.info(f"✅ Permissions {name}: Écriture OK dans {dir_path}")
            results["directories"][name] = {"path": str(dir_path), "status": "ok"}
        except Exception as e:
            all_success = False
            logger.error(f"❌ Permissions {name}: Échec d'écriture dans {dir_path}: {str(e)}")
            results["directories"][name] = {
                "path": str(dir_path),
                "status": "error",
                "message": str(e)
            }
    
    return all_success, results

def check_python_version() -> Tuple[bool, Dict]:
    """
    Vérifie que la version de Python est compatible
    
    Returns:
        Tuple[bool, Dict]: Succès (True/False) et informations sur la version
    """
    import platform
    
    version = platform.python_version()
    version_info = sys.version_info
    
    # Vérifier que la version est au moins 3.8
    is_compatible = version_info.major == 3 and version_info.minor >= 8
    
    result = {
        "version": version,
        "is_compatible": is_compatible,
        "details": {
            "major": version_info.major,
            "minor": version_info.minor,
            "micro": version_info.micro
        }
    }
    
    if is_compatible:
        logger.info(f"✅ Version Python: {version} (compatible)")
    else:
        logger.error(f"❌ Version Python: {version} (incompatible, Python 3.8+ requis)")
    
    return is_compatible, result

def check_critical_dependencies() -> Tuple[bool, Dict]:
    """
    Vérifie la présence des dépendances critiques
    
    Returns:
        Tuple[bool, Dict]: Succès (True/False) et statut des dépendances
    """
    critical_packages = [
        "web3", "requests", "pyyaml", "python-dotenv"
    ]
    
    result = {"packages": {}}
    all_installed = True
    
    for package in critical_packages:
        try:
            module = __import__(package.replace("-", "_"))
            version = getattr(module, "__version__", "Version inconnue")
            logger.info(f"✅ Dépendance {package}: Installée (version {version})")
            result["packages"][package] = {"installed": True, "version": version}
        except ImportError:
            all_installed = False
            logger.error(f"❌ Dépendance {package}: Non installée")
            result["packages"][package] = {"installed": False}
    
    return all_installed, result

def main():
    """Fonction principale qui exécute toutes les vérifications"""
    print_header()
    
    # Liste des vérifications avec leur criticité
    checks = [
        ("Version Python", check_python_version, True),
        ("Dépendances critiques", check_critical_dependencies, True),
        ("Variables d'environnement", check_environment_variables, True),
        ("Connexion RPC", check_rpc_connection, True),
        ("Permissions de stockage", check_storage_permissions, True)
    ]
    
    success = True
    critical_failures = []
    warnings = []
    
    for name, check_func, critical in checks:
        logger.info(f"\n--- Vérification: {name} ---")
        print(f"\n--- Vérification: {name} ---")
        
        start_time = time.time()
        check_success, check_results = check_func()
        elapsed = time.time() - start_time
        
        if check_success:
            status = STATUS_SUCCESS
            logger.info(f"{name}: {status} ({elapsed:.2f}s)")
            print(f"{name}: {status} ({elapsed:.2f}s)")
        else:
            if critical:
                status = STATUS_ERROR + " (Critique)"
                success = False
                critical_failures.append(name)
                logger.error(f"{name}: {status} ({elapsed:.2f}s)")
                print(f"{name}: {status} ({elapsed:.2f}s)")
            else:
                status = STATUS_WARNING
                warnings.append(name)
                logger.warning(f"{name}: {status} ({elapsed:.2f}s)")
                print(f"{name}: {status} ({elapsed:.2f}s)")
    
    # Résumé final
    print("\n" + "=" * 60)
    print("  RÉSULTAT DES VÉRIFICATIONS")
    print("=" * 60)
    
    if success:
        logger.info("\n✅ SUCCÈS: Toutes les vérifications critiques sont passées")
        print("\n✅ SUCCÈS: Toutes les vérifications critiques sont passées")
        
        if warnings:
            logger.warning(f"⚠️ Avertissements: {', '.join(warnings)}")
            print(f"⚠️ Avertissements: {', '.join(warnings)}")
    else:
        logger.error(f"\n❌ ÉCHEC: Vérifications critiques échouées: {', '.join(critical_failures)}")
        print(f"\n❌ ÉCHEC: Vérifications critiques échouées: {', '.join(critical_failures)}")
        
        # Sortir avec un code d'erreur
        sys.exit(1)
    
    print("\nGBPBot est prêt à être lancé!")
    return success

if __name__ == "__main__":
    main() 