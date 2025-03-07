#!/usr/bin/env python3
"""
Script pour vérifier l'intégrité du projet GBPBot.
Ce script vérifie que tous les modules et fichiers nécessaires sont présents
et que la structure du projet est cohérente.
"""

import os
import sys
import importlib
import logging
from typing import Dict, List, Tuple, Set

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Modules clés à vérifier
KEY_MODULES = [
    # Modules implémentés
    "gbpbot.core.optimization.jito_mev_optimizer",
    "gbpbot.ai.token_contract_analyzer",
    "gbpbot.machine_learning.lightweight_models",
    "gbpbot.machine_learning.market_microstructure_analyzer",
    "gbpbot.machine_learning.volatility_predictor",
    "gbpbot.sniping.solana_memecoin_sniper",
    
    # Modules en cours d'implémentation
    "gbpbot.blockchain.sonic_client",
    "gbpbot.clients.binance_client",
    "gbpbot.clients.base_cex_client",
    "gbpbot.clients.cex_client_factory",
    "gbpbot.strategies.cex_dex_arbitrage",
    "gbpbot.utils.resource_monitor",
    "gbpbot.utils.cache_manager",
    "gbpbot.core.rpc.rpc_manager",
    "gbpbot.dashboard.app",
    "gbpbot.backtesting.engine",
]

# Fichiers clés à vérifier
KEY_FILES = [
    # Modules implémentés
    "gbpbot/core/optimization/jito_mev_optimizer.py",
    "gbpbot/ai/token_contract_analyzer.py",
    "gbpbot/machine_learning/lightweight_models.py",
    "gbpbot/machine_learning/market_microstructure_analyzer.py",
    "gbpbot/machine_learning/volatility_predictor.py",
    "gbpbot/sniping/solana_memecoin_sniper.py",
    
    # Modules en cours d'implémentation
    "gbpbot/blockchain/sonic_client.py",
    "gbpbot/clients/binance_client.py",
    "gbpbot/clients/base_cex_client.py",
    "gbpbot/clients/cex_client_factory.py",
    "gbpbot/strategies/cex_dex_arbitrage.py",
    "gbpbot/utils/resource_monitor.py",
    "gbpbot/utils/cache_manager.py",
    "gbpbot/core/rpc/rpc_manager.py",
    "gbpbot/dashboard/app.py",
    "gbpbot/backtesting/engine.py",
    
    # Fichiers de documentation
    "docs/ROADMAP_PROGRESS.md",
    "gbpbot/USER_GUIDE.md",
    "gbpbot/TECHNICAL_DOCUMENTATION.md",
]

def check_file_exists(file_path: str) -> bool:
    """
    Vérifie si un fichier existe.
    
    Args:
        file_path: Chemin du fichier à vérifier
        
    Returns:
        True si le fichier existe, False sinon
    """
    return os.path.exists(file_path)

def check_module_imports(module_name: str) -> Tuple[bool, str]:
    """
    Vérifie si un module peut être importé.
    
    Args:
        module_name: Nom du module à importer
        
    Returns:
        Tuple (succès, message d'erreur)
    """
    try:
        # Essayer d'importer le module
        importlib.import_module(module_name)
        return True, ""
    except ImportError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Erreur inattendue: {str(e)}"

def check_project_integrity():
    """
    Vérifie l'intégrité du projet GBPBot.
    """
    logger.info("Vérification de l'intégrité du projet GBPBot...")
    
    # Vérifier les fichiers clés
    missing_files = []
    for file_path in KEY_FILES:
        if not check_file_exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        logger.warning(f"Fichiers manquants ({len(missing_files)}):")
        for file_path in missing_files:
            logger.warning(f"  - {file_path}")
    else:
        logger.info("Tous les fichiers clés sont présents.")
    
    # Vérifier les imports de modules
    failed_imports = []
    for module_name in KEY_MODULES:
        success, error_message = check_module_imports(module_name)
        if not success:
            failed_imports.append((module_name, error_message))
    
    if failed_imports:
        logger.warning(f"Modules avec des problèmes d'importation ({len(failed_imports)}):")
        for module_name, error_message in failed_imports:
            logger.warning(f"  - {module_name}: {error_message}")
    else:
        logger.info("Tous les modules clés peuvent être importés.")
    
    # Résumé
    if not missing_files and not failed_imports:
        logger.info("Vérification de l'intégrité terminée avec succès.")
        return True
    else:
        logger.warning("Vérification de l'intégrité terminée avec des problèmes.")
        return False

if __name__ == "__main__":
    success = check_project_integrity()
    sys.exit(0 if success else 1) 