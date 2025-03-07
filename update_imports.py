#!/usr/bin/env python3
"""
Script pour mettre à jour les imports dans le projet GBPBot après suppression des doublons.
Ce script parcourt tous les fichiers Python et met à jour les imports qui référencent
les fichiers supprimés.
"""

import os
import re
import logging
from typing import Dict, List, Tuple

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Mappings des imports à mettre à jour
IMPORT_MAPPINGS = {
    'from gbpbot.clients.cex.binance_client import': 'from gbpbot.clients.binance_client import',
    'from gbpbot.clients.cex.base_cex_client import': 'from gbpbot.clients.base_cex_client import',
    'from gbpbot.clients.cex.cex_client_factory import': 'from gbpbot.clients.cex_client_factory import',
    'from gbpbot.clients.sonic_client import': 'from gbpbot.blockchain.sonic_client import',
    'import gbpbot.clients.cex.binance_client': 'import gbpbot.clients.binance_client',
    'import gbpbot.clients.cex.base_cex_client': 'import gbpbot.clients.base_cex_client',
    'import gbpbot.clients.cex.cex_client_factory': 'import gbpbot.clients.cex_client_factory',
    'import gbpbot.clients.sonic_client': 'import gbpbot.blockchain.sonic_client',
}

def find_python_files(directory: str) -> List[str]:
    """
    Trouve tous les fichiers Python dans un répertoire et ses sous-répertoires.
    
    Args:
        directory: Répertoire à parcourir
        
    Returns:
        Liste des chemins des fichiers Python
    """
    python_files = []
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    
    return python_files

def update_imports_in_file(file_path: str) -> int:
    """
    Met à jour les imports dans un fichier.
    
    Args:
        file_path: Chemin du fichier à mettre à jour
        
    Returns:
        Nombre de remplacements effectués
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Appliquer les remplacements
        for old_import, new_import in IMPORT_MAPPINGS.items():
            content = content.replace(old_import, new_import)
        
        # Si le contenu a changé, écrire le fichier
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Compter le nombre de remplacements
            replacements = sum(content.count(new_import) for old_import, new_import in IMPORT_MAPPINGS.items())
            logger.info(f"Mis à jour {replacements} imports dans {file_path}")
            return replacements
        
        return 0
    
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour des imports dans {file_path}: {e}")
        return 0

def update_all_imports():
    """
    Met à jour tous les imports dans le projet.
    """
    logger.info("Début de la mise à jour des imports...")
    
    # Trouver tous les fichiers Python
    python_files = find_python_files('gbpbot')
    logger.info(f"Trouvé {len(python_files)} fichiers Python à analyser.")
    
    # Mettre à jour les imports dans chaque fichier
    total_replacements = 0
    for file_path in python_files:
        replacements = update_imports_in_file(file_path)
        total_replacements += replacements
    
    logger.info(f"Mise à jour des imports terminée. {total_replacements} imports mis à jour au total.")

if __name__ == "__main__":
    update_all_imports() 