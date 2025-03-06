#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
GBPBot - Installation de l'Optimiseur Automatique
-------------------------------------------------
Ce script installe toutes les dépendances nécessaires pour
l'optimiseur automatique de GBPBot.
"""

import os
import sys
import subprocess
import platform
import logging
from typing import List, Tuple

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("install_auto_optimizer.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("GBPBot-Installer")

# Liste des dépendances
DEPENDENCIES = [
    "psutil",       # Pour la gestion des processus
    "matplotlib",   # Pour la visualisation des données
    "numpy",        # Pour le traitement des données
]

def check_python_version() -> bool:
    """
    Vérifie que la version de Python est compatible.
    
    Returns:
        bool: True si la version est compatible, False sinon
    """
    major, minor = sys.version_info[:2]
    if major < 3 or (major == 3 and minor < 7):
        logger.error(f"Version de Python incompatible: {sys.version}")
        logger.error("Python 3.7 ou supérieur est requis.")
        return False
    
    logger.info(f"Version de Python compatible: {sys.version}")
    return True

def install_dependencies() -> bool:
    """
    Installe les dépendances nécessaires.
    
    Returns:
        bool: True si l'installation a réussi, False sinon
    """
    logger.info("Installation des dépendances...")
    
    pip_command = [sys.executable, "-m", "pip", "install", "--upgrade", "pip"]
    try:
        subprocess.run(pip_command, check=True, capture_output=True, text=True)
        logger.info("Pip mis à jour avec succès.")
    except subprocess.CalledProcessError as e:
        logger.warning(f"Erreur lors de la mise à jour de pip: {e.stderr}")
        logger.warning("Tentative d'installation des dépendances sans mettre à jour pip...")
    
    # Installer chaque dépendance séparément
    success = True
    for dep in DEPENDENCIES:
        logger.info(f"Installation de {dep}...")
        try:
            install_cmd = [sys.executable, "-m", "pip", "install", dep]
            result = subprocess.run(install_cmd, check=True, capture_output=True, text=True)
            logger.info(f"{dep} installé avec succès.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Erreur lors de l'installation de {dep}: {e.stderr}")
            success = False
    
    return success

def verify_installations() -> Tuple[bool, List[str]]:
    """
    Vérifie que toutes les dépendances sont correctement installées.
    
    Returns:
        Tuple[bool, List[str]]: (Toutes les dépendances sont installées, Liste des dépendances manquantes)
    """
    missing_deps = []
    
    for dep in DEPENDENCIES:
        try:
            __import__(dep)
            logger.info(f"{dep} vérifié avec succès.")
        except ImportError:
            logger.error(f"{dep} n'est pas correctement installé.")
            missing_deps.append(dep)
    
    if not missing_deps:
        logger.info("Toutes les dépendances sont correctement installées.")
        return True, []
    else:
        logger.error(f"Dépendances manquantes: {', '.join(missing_deps)}")
        return False, missing_deps

def check_required_files() -> bool:
    """
    Vérifie que les fichiers nécessaires sont présents.
    
    Returns:
        bool: True si tous les fichiers sont présents, False sinon
    """
    required_files = [
        "auto_optimizer.py",
        "monitor_performance.py",
        "update_optimizations.py"
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        logger.error(f"Fichiers manquants: {', '.join(missing_files)}")
        return False
    
    logger.info("Tous les fichiers requis sont présents.")
    return True

def create_startup_script() -> bool:
    """
    Crée un script de démarrage pour l'optimiseur automatique.
    
    Returns:
        bool: True si le script a été créé avec succès, False sinon
    """
    try:
        # Pour Windows
        if platform.system() == "Windows":
            with open("start_auto_optimizer.bat", "w") as f:
                f.write("@echo off\n")
                f.write("echo Démarrage de l'optimiseur automatique de GBPBot...\n")
                f.write("python auto_optimizer.py\n")
                f.write("pause\n")
            logger.info("Script de démarrage Windows créé: start_auto_optimizer.bat")
        
        # Pour Linux/macOS
        else:
            with open("start_auto_optimizer.sh", "w") as f:
                f.write("#!/bin/bash\n")
                f.write("echo \"Démarrage de l'optimiseur automatique de GBPBot...\"\n")
                f.write("python3 auto_optimizer.py\n")
            
            # Rendre le script exécutable
            os.chmod("start_auto_optimizer.sh", 0o755)
            logger.info("Script de démarrage Unix créé: start_auto_optimizer.sh")
        
        return True
    
    except Exception as e:
        logger.error(f"Erreur lors de la création du script de démarrage: {e}")
        return False

def main() -> int:
    """
    Fonction principale.
    
    Returns:
        int: Code de retour (0 si succès, 1 si échec)
    """
    logger.info("=== Installation de l'Optimiseur Automatique de GBPBot ===")
    
    # Vérifier la version de Python
    if not check_python_version():
        return 1
    
    # Vérifier les fichiers requis
    if not check_required_files():
        logger.error("Des fichiers nécessaires sont manquants. Veuillez les télécharger ou les recréer.")
        return 1
    
    # Installer les dépendances
    if not install_dependencies():
        logger.warning("Certaines dépendances n'ont pas pu être installées.")
        logger.warning("L'optimiseur pourrait ne pas fonctionner correctement.")
    
    # Vérifier les installations
    success, missing_deps = verify_installations()
    if not success:
        logger.warning("Certaines dépendances ne sont pas installées correctement.")
        logger.warning("Veuillez les installer manuellement:")
        for dep in missing_deps:
            logger.warning(f"  pip install {dep}")
    
    # Créer le script de démarrage
    if not create_startup_script():
        logger.warning("Impossible de créer le script de démarrage.")
        if platform.system() == "Windows":
            logger.info("Pour démarrer l'optimiseur, exécutez: python auto_optimizer.py")
        else:
            logger.info("Pour démarrer l'optimiseur, exécutez: python3 auto_optimizer.py")
    
    logger.info("=== Installation terminée ===")
    logger.info("Pour utiliser l'optimiseur automatique:")
    if platform.system() == "Windows":
        logger.info("  1. Double-cliquez sur start_auto_optimizer.bat")
    else:
        logger.info("  1. Exécutez ./start_auto_optimizer.sh dans un terminal")
    
    logger.info("  2. L'optimiseur surveillera automatiquement les performances de GBPBot")
    logger.info("  3. Les optimisations seront appliquées automatiquement si nécessaire")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 