#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script d'application des optimisations GBPBot

Ce script applique les optimisations du fichier .env.optimized au fichier .env principal.
Il préserve les paramètres existants et n'ajoute que les nouveaux paramètres d'optimisation.
"""

import os
import sys
import shutil
import logging
from datetime import datetime

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("apply_optimizations.log")
    ]
)
logger = logging.getLogger("GBPBot-OptimizationApplier")

# Chemins des fichiers
ENV_FILE = ".env"
OPTIMIZED_ENV_FILE = ".env.optimized"
BACKUP_ENV_FILE = f".env.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

def read_env_file(file_path):
    """Lit un fichier .env et retourne un dictionnaire des variables."""
    env_vars = {}
    
    if not os.path.exists(file_path):
        logger.warning(f"Le fichier {file_path} n'existe pas.")
        return env_vars
    
    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            if '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()
    
    return env_vars

def merge_env_files(original_env, optimized_env):
    """Fusionne les variables d'environnement, en préservant les originales et en ajoutant les optimisations."""
    # Copier les variables originales
    merged_env = original_env.copy()
    
    # Ajouter les variables d'optimisation
    for key, value in optimized_env.items():
        if key.startswith(('MAX_', 'RPC_', 'ML_')):  # Identifier les variables d'optimisation
            merged_env[key] = value
    
    return merged_env

def write_env_file(file_path, env_vars, original_file=None):
    """Écrit les variables d'environnement dans un fichier, en préservant les commentaires."""
    # Lire le fichier original pour préserver les commentaires
    lines = []
    sections = {}
    current_section = None
    
    if original_file and os.path.exists(original_file):
        with open(original_file, 'r') as f:
            lines = f.readlines()
        
        # Identifier les sections
        for i, line in enumerate(lines):
            if line.strip().startswith('#') and '####' in line:
                section_name = line.strip()
                sections[section_name] = i
                if 'OPTIMISATIONS DE PERFORMANCE' in section_name:
                    current_section = section_name
    
    # Si la section d'optimisation n'existe pas, l'ajouter
    if not current_section:
        optimization_section = "\n#######################\n# OPTIMISATIONS DE PERFORMANCE\n#######################\n\n"
        lines.append(optimization_section)
        current_section = "# OPTIMISATIONS DE PERFORMANCE"
        sections[current_section] = len(lines) - 1
    
    # Mettre à jour les variables existantes
    updated_keys = set()
    for i, line in enumerate(lines):
        if '=' in line and not line.strip().startswith('#'):
            key = line.split('=', 1)[0].strip()
            if key in env_vars:
                lines[i] = f"{key}={env_vars[key]}\n"
                updated_keys.add(key)
    
    # Ajouter les nouvelles variables d'optimisation
    new_optimization_lines = []
    for key, value in env_vars.items():
        if key not in updated_keys and key.startswith(('MAX_', 'RPC_', 'ML_')):
            new_optimization_lines.append(f"{key}={value}\n")
    
    # Insérer les nouvelles variables dans la section d'optimisation
    if new_optimization_lines:
        # Trouver où insérer les nouvelles variables
        insert_index = sections.get(current_section, len(lines))
        
        # Trouver la fin de la section
        for i in range(insert_index + 1, len(lines)):
            if lines[i].strip().startswith('#') and '####' in lines[i]:
                insert_index = i - 1
                break
            elif i == len(lines) - 1:
                insert_index = i + 1
        
        # Insérer les nouvelles variables
        lines = lines[:insert_index] + new_optimization_lines + lines[insert_index:]
    
    # Écrire le fichier mis à jour
    with open(file_path, 'w') as f:
        f.writelines(lines)

def main():
    """Fonction principale."""
    logger.info("Démarrage de l'application des optimisations...")
    
    # Vérifier si les fichiers existent
    if not os.path.exists(ENV_FILE):
        logger.error(f"Le fichier {ENV_FILE} n'existe pas.")
        return 1
    
    if not os.path.exists(OPTIMIZED_ENV_FILE):
        logger.error(f"Le fichier {OPTIMIZED_ENV_FILE} n'existe pas.")
        return 1
    
    # Créer une sauvegarde du fichier .env original
    shutil.copy2(ENV_FILE, BACKUP_ENV_FILE)
    logger.info(f"Sauvegarde créée: {BACKUP_ENV_FILE}")
    
    # Lire les fichiers .env
    original_env = read_env_file(ENV_FILE)
    optimized_env = read_env_file(OPTIMIZED_ENV_FILE)
    
    # Fusionner les variables
    merged_env = merge_env_files(original_env, optimized_env)
    
    # Écrire le fichier .env mis à jour
    write_env_file(ENV_FILE, merged_env, ENV_FILE)
    logger.info(f"Optimisations appliquées au fichier {ENV_FILE}")
    
    # Afficher les optimisations appliquées
    optimization_vars = {k: v for k, v in optimized_env.items() if k.startswith(('MAX_', 'RPC_', 'ML_'))}
    logger.info(f"Variables d'optimisation appliquées: {optimization_vars}")
    
    logger.info("Application des optimisations terminée avec succès.")
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        logger.error(f"Erreur lors de l'application des optimisations: {e}", exc_info=True)
        sys.exit(1) 