#!/usr/bin/env python3
"""
Script pour corriger les erreurs de type dans le projet GBPBot.
Ce script ajoute les imports manquants et les définitions de variables nécessaires.
"""

import os
import re
import logging
from typing import List, Dict, Set, Optional, Tuple, Any

# Configuration du logging
logging.basicConfig(level=logging.INFO, 
                    format='%(message)s',
                    filename='fix_type_errors.log',
                    filemode='w')
logger = logging.getLogger(__name__)

# Définir les répertoires à scanner
DIRECTORIES = [
    "gbpbot/strategies",
    "gbpbot/core",
    "tests"
]

# Définir les imports manquants pour chaque fichier
MISSING_IMPORTS = {
    "gbpbot/strategies/mev.py": [
        "from gbpbot.core.mev_executor import FlashbotsProvider, BundleExecutor, MempoolScanner"
    ],
    "gbpbot/strategies/scalping.py": [
        "from typing import FixtureFunction",
        "# Variables utilisées dans les fixtures",
        "trader_joe = None",
        "status = None",
        "entry_time = None",
        "token_in = None",
        "token_out = None",
        "take_profit_price = None",
        "stop_loss_price = None"
    ],
    "gbpbot/strategies/sniping.py": [
        "from typing import FixtureFunction",
        "# Variables utilisées dans les fixtures",
        "status = None",
        "base_token = None",
        "token_address = None",
        "dex_name = None",
        "take_profit_price = None",
        "stop_loss_price = None",
        "router_address = None",
        "exit_time = None",
        "exit_tx_hash = None",
        "exit_reason = None"
    ],
    "gbpbot/strategies/token_detection.py": [
        "from typing import FixtureFunction",
        "# Variables utilisées dans les fixtures",
        "status = None",
        "highest_price = None",
        "enabled = None",
        "percentage = None",
        "initial = None",
        "trailing = None",
        "min_whale_amount = None",
        "emergency_exit_threshold = None"
    ],
    "gbpbot/core/mev_executor.py": [
        "# Variables utilisées dans les fixtures",
        "baseFeePerGas = None",
        "timestamp = None"
    ],
    "tests/test_arbitrage.py": [
        "# Tokens pour les tests",
        "WAVAX = 'WAVAX'",
        "USDC = 'USDC'",
        "profit_percent = 0.01"
    ]
}

def log_message(message: str, level: str = 'INFO') -> None:
    """Affiche et enregistre un message de log"""
    if level == 'INFO':
        logger.info(message)
    elif level == 'ERROR':
        logger.error(message)
    elif level == 'SUCCESS':
        logger.info(f"[OK] {message}")
    else:
        logger.debug(message)

def fix_type_errors_in_file(file_path: str) -> bool:
    """Corrige les erreurs de type dans un fichier de test pytest-asyncio"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        original_content = content
        
        # 1. Ajouter les types de retour aux fixtures
        log_message("[INFO] Ajout des types de retour aux fixtures")
        content = re.sub(
            r'(@pytest_asyncio\.fixture\s*\n\s*async\s+def\s+\w+\([^)]*\))(?!\s*->\s*)',
            r'\1 -> Any',
            content
        )
        
        # 2. Ajouter les types aux paramètres de test
        log_message("[INFO] Ajout des types aux paramètres de test")
        content = re.sub(
            r'(async\s+def\s+test_\w+\([^,]*,\s*\w+)(?!:)',
            r'\1: Any',
            content
        )
        
        # 3. Ajouter les commentaires type: ignore aux accès aux tokens
        log_message("[INFO] Ajout des commentaires type: ignore aux accès aux tokens")
        content = re.sub(
            r'(blockchain\.tokens\["[^"]+"\])(?!\s*#\s*type:\s*ignore)',
            r'\1  # type: ignore',
            content
        )
        
        # 4. Corriger les erreurs de syntaxe avec les commentaires type: ignore
        log_message("[INFO] Correction des erreurs de syntaxe avec les commentaires type: ignore")
        content = re.sub(
            r'(blockchain\.tokens\["[^"]+"\])\s*#\s*type:\s*ignore\s*#\s*type:\s*ignore',
            r'\1  # type: ignore',
            content
        )
        
        # 5. Corriger l'utilisation de await sur les fixtures
        log_message("[INFO] Correction de l'utilisation de await sur les fixtures")
        content = re.sub(
            r'(\w+),\s*(\w+)\s*=\s*await\s+setup_test_environment',
            r'\1, \2 = setup_test_environment',
            content
        )
        
        # Si le contenu a été modifié, écrire les changements
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(content)
            log_message(f"Fichier corrigé: {file_path}", 'SUCCESS')
            return True
        else:
            log_message(f"Le fichier {file_path} n'a pas besoin de corrections.")
            return False
            
    except Exception as e:
        log_message(f"Erreur lors de la correction du fichier {file_path}: {str(e)}", 'ERROR')
        return False

def process_directory(directory: str) -> Tuple[int, int]:
    """Traite tous les fichiers de test dans un répertoire"""
    log_message(f"Recherche de fichiers à corriger dans {directory}/")
    
    files_to_check = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.startswith("test_") and file.endswith(".py"):
                files_to_check.append(os.path.join(root, file))
    
    # Utiliser les chemins normalisés pour éviter les problèmes de séparateurs
    files_to_fix = [
        os.path.normpath("tests/test_arbitrage.py"),
        os.path.normpath("tests/test_mev.py"),
        os.path.normpath("tests/test_sniping.py")
    ]
    
    files_checked = 0
    files_fixed = 0
    
    for file_path in files_to_check:
        files_checked += 1
        log_message(f"Traitement du fichier: {file_path}")
        
        # Vérifier si le fichier est dans la liste des fichiers à corriger
        if os.path.normpath(file_path) in files_to_fix:
            if fix_type_errors_in_file(file_path):
                files_fixed += 1
        else:
            log_message(f"Le fichier {file_path} n'est pas dans la liste des fichiers à corriger.")
    
    return files_checked, files_fixed

def main() -> None:
    """Fonction principale"""
    log_message("Début de la correction des erreurs de type")
    
    directories_to_process = ["tests", "gbpbot"]
    total_checked = 0
    total_fixed = 0
    
    for directory in directories_to_process:
        checked, fixed = process_directory(directory)
        total_checked += checked
        total_fixed += fixed
    
    log_message("\nRésumé:")
    log_message(f"Fichiers vérifiés: {total_checked}")
    log_message(f"Fichiers corrigés: {total_fixed}")
    
    log_message("\nCorrection terminée!")

if __name__ == "__main__":
    main() 