#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
GBPBot - Installation des Outils d'Optimisation
-----------------------------------------------
Ce script installe et configure tous les outils d'optimisation de GBPBot en une seule étape.
"""

import os
import sys
import time
import shutil
import logging
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

# Configuration du logging
log_file = f"setup_optimization_tools_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("GBPBot-Setup")

# Liste des fichiers d'optimisation
OPTIMIZATION_FILES = [
    "monitor_performance.py",
    "install_performance_monitor.py",
    "update_optimizations.py",
    "apply_optimizations.py",
    "start_performance_monitor.bat",
    "start_performance_monitor.sh",
    "OPTIMIZATIONS.md",
    "OPTIMIZATIONS_SUMMARY.md",
    "PERFORMANCE_README.md",
    "README_OPTIMISATIONS.md",
    ".env.optimized"
]

def check_python_version():
    """Vérifie que la version de Python est compatible."""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 7):
        logger.error(f"Python 3.7+ est requis. Version actuelle: {sys.version}")
        return False
    logger.info(f"Version Python compatible: {sys.version}")
    return True

def check_files_exist():
    """Vérifie que tous les fichiers d'optimisation existent."""
    missing_files = []
    for file in OPTIMIZATION_FILES:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        logger.error(f"Fichiers manquants: {', '.join(missing_files)}")
        return False
    
    logger.info("Tous les fichiers d'optimisation sont présents")
    return True

def install_dependencies():
    """Installe les dépendances nécessaires pour les outils d'optimisation."""
    logger.info("Installation des dépendances...")
    
    try:
        # Mise à jour de pip
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], check=True)
        logger.info("pip mis à jour avec succès")
        
        # Installation des dépendances via le script dédié
        if os.path.exists("install_performance_monitor.py"):
            subprocess.run([sys.executable, "install_performance_monitor.py"], check=True)
            logger.info("Dépendances installées avec succès via install_performance_monitor.py")
            return True
        else:
            # Installation manuelle des dépendances de base
            dependencies = ["psutil", "matplotlib", "numpy"]
            for dep in dependencies:
                subprocess.run([sys.executable, "-m", "pip", "install", dep], check=True)
                logger.info(f"{dep} installé avec succès")
            
            # Tentative d'installation de PyTorch
            try:
                subprocess.run([sys.executable, "-m", "pip", "install", "torch"], check=True)
                logger.info("PyTorch installé avec succès")
            except subprocess.CalledProcessError:
                logger.warning("Impossible d'installer PyTorch. La surveillance GPU sera désactivée.")
            
            return True
    
    except subprocess.CalledProcessError as e:
        logger.error(f"Erreur lors de l'installation des dépendances: {e}")
        return False

def apply_optimizations():
    """Applique les optimisations au fichier .env."""
    logger.info("Application des optimisations...")
    
    try:
        # Vérification de l'existence des fichiers
        if not os.path.exists("apply_optimizations.py"):
            logger.error("Le fichier apply_optimizations.py est introuvable")
            return False
        
        # Application des optimisations
        subprocess.run([sys.executable, "apply_optimizations.py"], check=True)
        logger.info("Optimisations appliquées avec succès")
        return True
    
    except subprocess.CalledProcessError as e:
        logger.error(f"Erreur lors de l'application des optimisations: {e}")
        return False

def setup_startup_scripts():
    """Configure les scripts de démarrage pour qu'ils soient exécutables."""
    logger.info("Configuration des scripts de démarrage...")
    
    # Pour les systèmes Unix/Linux/macOS
    if os.name == "posix":
        try:
            if os.path.exists("start_performance_monitor.sh"):
                os.chmod("start_performance_monitor.sh", 0o755)  # Rendre le script exécutable
                logger.info("Script start_performance_monitor.sh rendu exécutable")
            else:
                logger.warning("Le fichier start_performance_monitor.sh est introuvable")
        except Exception as e:
            logger.error(f"Erreur lors de la configuration du script de démarrage: {e}")
    
    # Pour Windows, créer un raccourci bureau si possible
    elif os.name == "nt":
        try:
            desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
            if os.path.exists(desktop_path) and os.path.exists("start_performance_monitor.bat"):
                # Créer un lien symbolique ou une copie sur le bureau
                desktop_shortcut = os.path.join(desktop_path, "GBPBot Performance Monitor.bat")
                
                # Utiliser un lien symbolique si possible, sinon copier
                try:
                    os.symlink(os.path.abspath("start_performance_monitor.bat"), desktop_shortcut)
                    logger.info(f"Raccourci créé sur le bureau: {desktop_shortcut}")
                except (OSError, AttributeError):
                    shutil.copy2("start_performance_monitor.bat", desktop_shortcut)
                    logger.info(f"Script copié sur le bureau: {desktop_shortcut}")
            else:
                logger.warning("Impossible de créer un raccourci sur le bureau")
        except Exception as e:
            logger.error(f"Erreur lors de la création du raccourci: {e}")
    
    return True

def test_monitor():
    """Teste le moniteur de performances."""
    logger.info("Test du moniteur de performances...")
    
    try:
        # Vérification de l'existence du moniteur
        if not os.path.exists("monitor_performance.py"):
            logger.error("Le fichier monitor_performance.py est introuvable")
            return False
        
        # Test d'importation des modules
        test_code = """
import psutil
import matplotlib
import matplotlib.pyplot as plt
print('Test d\\'importation réussi')

# Test optionnel pour GPU
try:
    import torch
    print(f'PyTorch disponible: {torch.__version__}')
    print(f'CUDA disponible: {torch.cuda.is_available()}')
    if torch.cuda.is_available():
        print(f'GPU détecté: {torch.cuda.get_device_name(0)}')
except ImportError:
    print('PyTorch non disponible')
"""
        
        # Exécution du test
        result = subprocess.run(
            [sys.executable, "-c", test_code], 
            check=False, 
            capture_output=True,
            text=True
        )
        
        logger.info(f"Résultat du test: \n{result.stdout}")
        if result.stderr:
            logger.warning(f"Erreurs de test: \n{result.stderr}")
        
        if "Test d'importation réussi" in result.stdout:
            logger.info("Test du moniteur réussi")
            return True
        else:
            logger.error("Test du moniteur échoué")
            return False
    
    except Exception as e:
        logger.error(f"Erreur lors du test du moniteur: {e}")
        return False

def create_desktop_shortcut():
    """Crée un raccourci sur le bureau pour lancer le moniteur de performances."""
    if os.name != "nt":
        logger.info("Création de raccourci bureau uniquement disponible sous Windows")
        return True
    
    try:
        # Chemin du bureau
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        if not os.path.exists(desktop_path):
            logger.warning(f"Dossier Bureau introuvable: {desktop_path}")
            return False
        
        # Création d'un fichier .bat personnalisé
        shortcut_path = os.path.join(desktop_path, "GBPBot Moniteur.bat")
        with open(shortcut_path, "w") as f:
            f.write('@echo off\n')
            f.write('echo Démarrage du moniteur de performances GBPBot...\n')
            f.write(f'cd /d "{os.getcwd()}"\n')
            f.write('python monitor_performance.py\n')
            f.write('pause\n')
        
        logger.info(f"Raccourci créé sur le bureau: {shortcut_path}")
        return True
    
    except Exception as e:
        logger.error(f"Erreur lors de la création du raccourci bureau: {e}")
        return False

def main():
    """Fonction principale."""
    parser = argparse.ArgumentParser(description='Installation des outils d\'optimisation GBPBot')
    parser.add_argument('--skip-dependencies', action='store_true', help='Ignorer l\'installation des dépendances')
    parser.add_argument('--skip-optimizations', action='store_true', help='Ignorer l\'application des optimisations')
    parser.add_argument('--create-shortcut', action='store_true', help='Créer un raccourci sur le bureau (Windows uniquement)')
    args = parser.parse_args()
    
    logger.info("=== Installation des outils d'optimisation GBPBot ===")
    
    # Étape 1: Vérification de l'environnement
    if not check_python_version():
        logger.error("Version Python incompatible")
        return 1
    
    # Étape 2: Vérification des fichiers
    if not check_files_exist():
        logger.error("Fichiers manquants")
        return 1
    
    # Étape 3: Installation des dépendances
    if not args.skip_dependencies:
        if not install_dependencies():
            logger.error("Échec de l'installation des dépendances")
            return 1
    else:
        logger.info("Installation des dépendances ignorée")
    
    # Étape 4: Application des optimisations
    if not args.skip_optimizations:
        if not apply_optimizations():
            logger.error("Échec de l'application des optimisations")
            return 1
    else:
        logger.info("Application des optimisations ignorée")
    
    # Étape 5: Configuration des scripts de démarrage
    if not setup_startup_scripts():
        logger.warning("Problème lors de la configuration des scripts de démarrage")
    
    # Étape 6: Test du moniteur
    if not test_monitor():
        logger.warning("Test du moniteur échoué, mais l'installation continue")
    
    # Étape 7: Création d'un raccourci bureau (Windows uniquement)
    if args.create_shortcut:
        if not create_desktop_shortcut():
            logger.warning("Échec de la création du raccourci bureau")
    
    # Fin de l'installation
    logger.info("=== Installation des outils d'optimisation terminée avec succès ===")
    logger.info("Pour démarrer le moniteur de performances, exécutez:")
    if os.name == "nt":
        logger.info("start_performance_monitor.bat")
    else:
        logger.info("./start_performance_monitor.sh")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 