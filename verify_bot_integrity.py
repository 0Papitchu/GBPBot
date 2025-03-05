#!/usr/bin/env python
"""
Script pour vérifier l'intégrité du bot et s'assurer que tous les composants fonctionnent correctement
"""

import os
import sys
import json
import logging
import asyncio
import importlib
import traceback
from typing import Dict, List, Tuple, Any
from dotenv import load_dotenv

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("integrity_check.log"),
        logging.StreamHandler()
    ]
)

# Charger les variables d'environnement
load_dotenv()

# Composants essentiels à vérifier
ESSENTIAL_COMPONENTS = [
    {
        "name": "BlockchainClient",
        "module": "gbpbot.core.blockchain",
        "class": "BlockchainClient",
        "methods": ["get_balance", "execute_swap", "approve_token"]
    },
    {
        "name": "PriceFeed",
        "module": "gbpbot.core.price_feed",
        "class": "PriceFeed",
        "methods": ["get_all_prices", "get_dex_price", "fetch_price"]
    },
    {
        "name": "ArbitrageStrategy",
        "module": "gbpbot.strategies.arbitrage",
        "class": "ArbitrageStrategy",
        "methods": ["find_opportunities", "analyze_pair", "execute_trade"]
    },
    {
        "name": "MEVStrategy",
        "module": "gbpbot.strategies.mev",
        "class": "MEVStrategy",
        "methods": ["scan_mempool", "analyze_transaction", "execute_strategy"]
    },
    {
        "name": "SnipingStrategy",
        "module": "gbpbot.strategies.sniping",
        "class": "SnipingStrategy",
        "methods": ["scan_new_tokens", "analyze_token", "execute_buy"]
    },
    {
        "name": "VersionManager",
        "module": "gbpbot.core.version_manager",
        "class": "VersionManager",
        "methods": ["create_backup", "rollback", "get_version_info"]
    }
]

# Fichiers de configuration essentiels
ESSENTIAL_CONFIG_FILES = [
    ".env",
    "config.py",
    "requirements.txt"
]

async def check_component(component: Dict) -> Dict:
    """
    Vérifie un composant spécifique du bot
    
    Args:
        component: Informations sur le composant à vérifier
        
    Returns:
        Dict: Résultats de la vérification
    """
    result = {
        "name": component["name"],
        "status": "ok",
        "issues": [],
        "details": {}
    }
    
    try:
        # Importer le module
        module = importlib.import_module(component["module"])
        result["details"]["module_import"] = "ok"
        
        # Vérifier la classe
        if hasattr(module, component["class"]):
            class_obj = getattr(module, component["class"])
            result["details"]["class_exists"] = "ok"
            
            # Vérifier les méthodes
            missing_methods = []
            for method_name in component["methods"]:
                if not hasattr(class_obj, method_name):
                    missing_methods.append(method_name)
            
            if missing_methods:
                result["status"] = "warning"
                result["issues"].append(f"Méthodes manquantes: {', '.join(missing_methods)}")
                result["details"]["missing_methods"] = missing_methods
            else:
                result["details"]["methods_check"] = "ok"
        else:
            result["status"] = "error"
            result["issues"].append(f"Classe {component['class']} non trouvée dans le module {component['module']}")
            result["details"]["class_exists"] = "error"
    
    except ImportError as e:
        result["status"] = "error"
        result["issues"].append(f"Impossible d'importer le module {component['module']}: {str(e)}")
        result["details"]["module_import"] = "error"
    
    except Exception as e:
        result["status"] = "error"
        result["issues"].append(f"Erreur lors de la vérification du composant: {str(e)}")
        result["details"]["exception"] = str(e)
        result["details"]["traceback"] = traceback.format_exc()
    
    return result

async def check_config_files() -> Dict:
    """
    Vérifie les fichiers de configuration essentiels
    
    Returns:
        Dict: Résultats de la vérification
    """
    result = {
        "status": "ok",
        "missing_files": [],
        "empty_files": [],
        "details": {}
    }
    
    for file_path in ESSENTIAL_CONFIG_FILES:
        full_path = os.path.join(os.path.dirname(__file__), file_path)
        
        if not os.path.exists(full_path):
            result["status"] = "error"
            result["missing_files"].append(file_path)
            result["details"][file_path] = "missing"
        elif os.path.getsize(full_path) == 0:
            result["status"] = "warning"
            result["empty_files"].append(file_path)
            result["details"][file_path] = "empty"
        else:
            result["details"][file_path] = "ok"
    
    return result

async def check_environment_variables() -> Dict:
    """
    Vérifie les variables d'environnement essentielles
    
    Returns:
        Dict: Résultats de la vérification
    """
    result = {
        "status": "ok",
        "missing_vars": [],
        "empty_vars": [],
        "details": {}
    }
    
    # Variables d'environnement essentielles
    essential_vars = [
        "PRIVATE_KEY",
        "WALLET_ADDRESS",
        "RPC_URL",
        "CHAIN_ID",
        "ARBITRAGE_THRESHOLD",
        "SLEEP_TIME"
    ]
    
    for var_name in essential_vars:
        var_value = os.environ.get(var_name)
        
        if var_value is None:
            result["status"] = "error"
            result["missing_vars"].append(var_name)
            result["details"][var_name] = "missing"
        elif var_value.strip() == "":
            result["status"] = "warning"
            result["empty_vars"].append(var_name)
            result["details"][var_name] = "empty"
        else:
            result["details"][var_name] = "ok"
    
    return result

async def check_dependencies() -> Dict:
    """
    Vérifie les dépendances Python essentielles
    
    Returns:
        Dict: Résultats de la vérification
    """
    result = {
        "status": "ok",
        "missing_deps": [],
        "details": {}
    }
    
    # Dépendances essentielles
    essential_deps = [
        "web3",
        "ccxt",
        "pandas",
        "numpy",
        "aiohttp",
        "python-dotenv"
    ]
    
    for dep_name in essential_deps:
        try:
            importlib.import_module(dep_name)
            result["details"][dep_name] = "ok"
        except ImportError:
            result["status"] = "error"
            result["missing_deps"].append(dep_name)
            result["details"][dep_name] = "missing"
    
    return result

async def verify_bot_integrity():
    """
    Vérifie l'intégrité complète du bot
    """
    logging.info("Démarrage de la vérification d'intégrité du bot...")
    
    # Résultats globaux
    results = {
        "timestamp": asyncio.get_event_loop().time(),
        "overall_status": "ok",
        "components": {},
        "config_files": {},
        "environment": {},
        "dependencies": {}
    }
    
    # Vérifier les composants
    logging.info("Vérification des composants essentiels...")
    component_tasks = [check_component(component) for component in ESSENTIAL_COMPONENTS]
    component_results = await asyncio.gather(*component_tasks)
    
    for result in component_results:
        results["components"][result["name"]] = result
        if result["status"] != "ok":
            results["overall_status"] = "error" if result["status"] == "error" else (
                "warning" if results["overall_status"] != "error" else results["overall_status"]
            )
    
    # Vérifier les fichiers de configuration
    logging.info("Vérification des fichiers de configuration...")
    config_results = await check_config_files()
    results["config_files"] = config_results
    if config_results["status"] != "ok":
        results["overall_status"] = "error" if config_results["status"] == "error" else (
            "warning" if results["overall_status"] != "error" else results["overall_status"]
        )
    
    # Vérifier les variables d'environnement
    logging.info("Vérification des variables d'environnement...")
    env_results = await check_environment_variables()
    results["environment"] = env_results
    if env_results["status"] != "ok":
        results["overall_status"] = "error" if env_results["status"] == "error" else (
            "warning" if results["overall_status"] != "error" else results["overall_status"]
        )
    
    # Vérifier les dépendances
    logging.info("Vérification des dépendances Python...")
    dep_results = await check_dependencies()
    results["dependencies"] = dep_results
    if dep_results["status"] != "ok":
        results["overall_status"] = "error" if dep_results["status"] == "error" else (
            "warning" if results["overall_status"] != "error" else results["overall_status"]
        )
    
    # Afficher les résultats
    logging.info("\n===== RÉSULTATS DE LA VÉRIFICATION D'INTÉGRITÉ =====")
    logging.info(f"Statut global: {results['overall_status'].upper()}")
    
    # Composants
    logging.info("\nComposants:")
    for component_name, component_result in results["components"].items():
        status_icon = "✅" if component_result["status"] == "ok" else "⚠️" if component_result["status"] == "warning" else "❌"
        logging.info(f"{status_icon} {component_name}: {component_result['status'].upper()}")
        for issue in component_result.get("issues", []):
            logging.info(f"   - {issue}")
    
    # Fichiers de configuration
    logging.info("\nFichiers de configuration:")
    status_icon = "✅" if results["config_files"]["status"] == "ok" else "⚠️" if results["config_files"]["status"] == "warning" else "❌"
    logging.info(f"{status_icon} Statut: {results['config_files']['status'].upper()}")
    if results["config_files"]["missing_files"]:
        logging.info(f"   - Fichiers manquants: {', '.join(results['config_files']['missing_files'])}")
    if results["config_files"]["empty_files"]:
        logging.info(f"   - Fichiers vides: {', '.join(results['config_files']['empty_files'])}")
    
    # Variables d'environnement
    logging.info("\nVariables d'environnement:")
    status_icon = "✅" if results["environment"]["status"] == "ok" else "⚠️" if results["environment"]["status"] == "warning" else "❌"
    logging.info(f"{status_icon} Statut: {results['environment']['status'].upper()}")
    if results["environment"]["missing_vars"]:
        logging.info(f"   - Variables manquantes: {', '.join(results['environment']['missing_vars'])}")
    if results["environment"]["empty_vars"]:
        logging.info(f"   - Variables vides: {', '.join(results['environment']['empty_vars'])}")
    
    # Dépendances
    logging.info("\nDépendances Python:")
    status_icon = "✅" if results["dependencies"]["status"] == "ok" else "⚠️" if results["dependencies"]["status"] == "warning" else "❌"
    logging.info(f"{status_icon} Statut: {results['dependencies']['status'].upper()}")
    if results["dependencies"]["missing_deps"]:
        logging.info(f"   - Dépendances manquantes: {', '.join(results['dependencies']['missing_deps'])}")
    
    # Sauvegarder les résultats dans un fichier JSON
    results_file = "integrity_results.json"
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)
    
    logging.info(f"\nRésultats détaillés sauvegardés dans {results_file}")
    
    # Retourner le code de sortie approprié
    if results["overall_status"] == "error":
        logging.error("La vérification d'intégrité a échoué. Veuillez corriger les erreurs avant de continuer.")
        return 1
    elif results["overall_status"] == "warning":
        logging.warning("La vérification d'intégrité a détecté des avertissements. Veuillez les examiner avant de continuer.")
        return 0
    else:
        logging.info("La vérification d'intégrité a réussi. Le bot est prêt à fonctionner.")
        return 0

if __name__ == "__main__":
    exit_code = asyncio.run(verify_bot_integrity())
    sys.exit(exit_code) 