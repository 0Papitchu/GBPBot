#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pour mettre à jour la configuration de GBPBot.
Ce script permet de modifier des paramètres spécifiques dans le fichier de configuration
sans avoir à éditer manuellement le fichier YAML.
"""

import os
import sys
import argparse
import logging
import yaml
from pathlib import Path
from datetime import datetime
import shutil

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"logs/config_update_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    ]
)
logger = logging.getLogger("config_updater")

def parse_arguments():
    """Parse les arguments de ligne de commande."""
    parser = argparse.ArgumentParser(description="Mettre à jour la configuration de GBPBot")
    
    parser.add_argument("--config", type=str, default="config/active_config.yaml",
                        help="Chemin vers le fichier de configuration (défaut: config/active_config.yaml)")
    
    parser.add_argument("--param", type=str, required=True,
                        help="Paramètre à mettre à jour (format: section.sous_section.paramètre)")
    
    parser.add_argument("--value", type=str, required=True,
                        help="Nouvelle valeur pour le paramètre")
    
    parser.add_argument("--backup", action="store_true",
                        help="Créer une sauvegarde du fichier de configuration avant modification")
    
    parser.add_argument("--dry-run", action="store_true",
                        help="Afficher les modifications sans les appliquer")
    
    return parser.parse_args()

def load_config(config_path):
    """
    Charge la configuration depuis le fichier YAML.
    
    Args:
        config_path (str): Chemin vers le fichier de configuration
        
    Returns:
        dict: Configuration chargée
    """
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        logger.info(f"Configuration chargée depuis {config_path}")
        return config
    except Exception as e:
        logger.error(f"Erreur lors du chargement de la configuration: {e}")
        sys.exit(1)

def save_config(config, config_path, dry_run=False):
    """
    Sauvegarde la configuration dans le fichier YAML.
    
    Args:
        config (dict): Configuration à sauvegarder
        config_path (str): Chemin vers le fichier de configuration
        dry_run (bool): Si True, n'écrit pas réellement le fichier
    """
    if dry_run:
        logger.info("Mode dry-run: la configuration ne sera pas sauvegardée")
        logger.info(f"Contenu qui serait écrit dans {config_path}:")
        yaml_content = yaml.dump(config, default_flow_style=False, sort_keys=False)
        print(yaml_content)
        return
    
    try:
        with open(config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        logger.info(f"Configuration sauvegardée dans {config_path}")
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde de la configuration: {e}")
        sys.exit(1)

def backup_config(config_path):
    """
    Crée une sauvegarde du fichier de configuration.
    
    Args:
        config_path (str): Chemin vers le fichier de configuration
        
    Returns:
        str: Chemin vers le fichier de sauvegarde
    """
    backup_dir = Path("config/backups")
    backup_dir.mkdir(exist_ok=True, parents=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    config_filename = Path(config_path).name
    backup_path = backup_dir / f"{config_filename}.{timestamp}.bak"
    
    try:
        shutil.copy2(config_path, backup_path)
        logger.info(f"Sauvegarde créée: {backup_path}")
        return str(backup_path)
    except Exception as e:
        logger.error(f"Erreur lors de la création de la sauvegarde: {e}")
        sys.exit(1)

def update_config_param(config, param_path, value):
    """
    Met à jour un paramètre spécifique dans la configuration.
    
    Args:
        config (dict): Configuration à mettre à jour
        param_path (str): Chemin du paramètre (format: section.sous_section.paramètre)
        value (str): Nouvelle valeur pour le paramètre
        
    Returns:
        dict: Configuration mise à jour
    """
    # Conversion de la valeur au type approprié
    try:
        # Essayer de convertir en nombre
        if value.lower() == "true":
            typed_value = True
        elif value.lower() == "false":
            typed_value = False
        elif value.lower() == "null" or value.lower() == "none":
            typed_value = None
        elif "." in value and all(c.isdigit() or c == "." for c in value.replace("-", "", 1)):
            typed_value = float(value)
        elif value.isdigit() or (value.startswith("-") and value[1:].isdigit()):
            typed_value = int(value)
        elif value.startswith("[") and value.endswith("]"):
            # Liste simple
            items = value[1:-1].split(",")
            typed_value = [item.strip() for item in items]
        else:
            typed_value = value
    except ValueError:
        typed_value = value
    
    # Séparation du chemin en parties
    parts = param_path.split(".")
    
    # Navigation dans la configuration
    current = config
    for i, part in enumerate(parts[:-1]):
        if part not in current:
            # Création des sections manquantes
            current[part] = {}
            logger.info(f"Création de la section manquante: {'.'.join(parts[:i+1])}")
        current = current[part]
    
    # Mise à jour du paramètre
    last_part = parts[-1]
    old_value = current.get(last_part, "non défini")
    current[last_part] = typed_value
    
    logger.info(f"Paramètre {param_path} mis à jour: {old_value} -> {typed_value}")
    
    return config

def main():
    """Fonction principale."""
    # Création du répertoire de logs s'il n'existe pas
    os.makedirs("logs", exist_ok=True)
    
    # Parsing des arguments
    args = parse_arguments()
    
    # Vérification de l'existence du fichier de configuration
    if not os.path.exists(args.config):
        logger.error(f"Le fichier de configuration {args.config} n'existe pas")
        sys.exit(1)
    
    # Création d'une sauvegarde si demandé
    if args.backup:
        backup_path = backup_config(args.config)
        logger.info(f"Sauvegarde créée: {backup_path}")
    
    # Chargement de la configuration
    config = load_config(args.config)
    
    # Mise à jour du paramètre
    updated_config = update_config_param(config, args.param, args.value)
    
    # Sauvegarde de la configuration mise à jour
    save_config(updated_config, args.config, args.dry_run)
    
    if not args.dry_run:
        logger.info(f"Configuration mise à jour avec succès: {args.param} = {args.value}")
    else:
        logger.info(f"Mode dry-run: la configuration n'a pas été modifiée")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Opération annulée par l'utilisateur")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Erreur fatale: {e}", exc_info=True)
        sys.exit(1) 