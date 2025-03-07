#!/usr/bin/env python3
"""
Script pour nettoyer les doublons dans le projet GBPBot.
Ce script identifie et supprime les fichiers en double, en gardant la version la plus récente.
"""

import os
import shutil
import datetime
import logging
from typing import Dict, List, Tuple

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Liste des doublons potentiels à vérifier
POTENTIAL_DUPLICATES = [
    # Format: (chemin1, chemin2, garder_chemin1)
    ('gbpbot/clients/binance_client.py', 'gbpbot/clients/cex/binance_client.py', False),
    ('gbpbot/clients/base_cex_client.py', 'gbpbot/clients/cex/base_cex_client.py', False),
    ('gbpbot/clients/cex_client_factory.py', 'gbpbot/clients/cex/cex_client_factory.py', False),
    ('gbpbot/blockchain/sonic_client.py', 'gbpbot/clients/sonic_client.py', True),
    # Nouveaux doublons identifiés
    ('gbpbot/ai/market_analyzer.py', 'gbpbot/ai/market_analyzer_fixed.py', True),
    ('gbpbot/gbpbot_menu.py', 'gbpbot/gbpbot_menu_fixed.py', False),
]

def get_file_info(filepath: str) -> Tuple[bool, datetime.datetime, int]:
    """
    Obtient les informations sur un fichier.
    
    Args:
        filepath: Chemin du fichier
        
    Returns:
        Tuple contenant (existe, date_modification, taille)
    """
    if not os.path.exists(filepath):
        return (False, datetime.datetime.min, 0)
    
    stat = os.stat(filepath)
    modified = datetime.datetime.fromtimestamp(stat.st_mtime)
    size = stat.st_size
    
    return (True, modified, size)

def cleanup_duplicates():
    """
    Nettoie les fichiers en double dans le projet.
    """
    logger.info("Début du nettoyage des doublons...")
    
    for path1, path2, keep_path1 in POTENTIAL_DUPLICATES:
        exists1, modified1, size1 = get_file_info(path1)
        exists2, modified2, size2 = get_file_info(path2)
        
        if not exists1 and not exists2:
            logger.warning(f"Aucun des fichiers n'existe: {path1} et {path2}")
            continue
        
        if not exists1:
            logger.info(f"Le fichier {path1} n'existe pas, aucune action nécessaire.")
            continue
            
        if not exists2:
            logger.info(f"Le fichier {path2} n'existe pas, aucune action nécessaire.")
            continue
        
        # Les deux fichiers existent, décider lequel garder
        if keep_path1:
            file_to_keep = path1
            file_to_remove = path2
            logger.info(f"Conservation forcée de {path1} selon la configuration.")
        else:
            # Garder le fichier le plus récent par défaut
            if modified1 > modified2:
                file_to_keep = path1
                file_to_remove = path2
                logger.info(f"Conservation de {path1} (plus récent).")
            else:
                file_to_keep = path2
                file_to_remove = path1
                logger.info(f"Conservation de {path2} (plus récent).")
        
        # Créer une sauvegarde du fichier à supprimer
        backup_path = f"{file_to_remove}.bak"
        logger.info(f"Création d'une sauvegarde de {file_to_remove} vers {backup_path}")
        shutil.copy2(file_to_remove, backup_path)
        
        # Supprimer le fichier en double
        logger.info(f"Suppression du fichier en double: {file_to_remove}")
        os.remove(file_to_remove)
        
        logger.info(f"Doublon traité: {file_to_keep} conservé, {file_to_remove} supprimé (sauvegarde: {backup_path})")
    
    logger.info("Nettoyage des doublons terminé.")

if __name__ == "__main__":
    cleanup_duplicates() 