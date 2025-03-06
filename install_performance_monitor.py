#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script d'installation des dépendances pour le moniteur de performances GBPBot
----------------------------------------------------------------------------
Ce script installe les dépendances nécessaires pour le moniteur de performances.
"""

import os
import sys
import subprocess
import platform
import logging
from datetime import datetime

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"install_monitor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("GBPBot-Install")

def check_python_version():
    """Vérifie que la version de Python est compatible."""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 7):
        logger.error(f"Python 3.7+ est requis. Version actuelle: {sys.version}")
        return False
    logger.info(f"Version Python compatible: {sys.version}")
    return True

def check_pip():
    """Vérifie que pip est installé et à jour."""
    try:
        subprocess.run([sys.executable, "-m", "pip", "--version"], check=True, capture_output=True)
        logger.info("pip est installé")
        
        # Mise à jour de pip
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], check=True)
        logger.info("pip a été mis à jour")
        return True
    except subprocess.CalledProcessError:
        logger.error("pip n'est pas installé ou ne fonctionne pas correctement")
        return False

def install_dependencies():
    """Installe les dépendances nécessaires pour le moniteur de performances."""
    dependencies = [
        "psutil",
        "matplotlib",
        "numpy",
        "argparse"
    ]
    
    logger.info("Installation des dépendances de base...")
    for dep in dependencies:
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", dep], check=True)
            logger.info(f"{dep} installé avec succès")
        except subprocess.CalledProcessError as e:
            logger.error(f"Erreur lors de l'installation de {dep}: {e}")
            return False
    
    # Installation de PyTorch pour la surveillance GPU
    logger.info("Tentative d'installation de PyTorch pour la surveillance GPU...")
    
    try:
        # Détection du système d'exploitation et de la configuration GPU
        os_name = platform.system().lower()
        
        if os_name == "windows":
            # Installation de PyTorch pour Windows
            cmd = [sys.executable, "-m", "pip", "install", "torch", "torchvision", "torchaudio"]
            if check_nvidia_gpu():
                cmd.append("--index-url")
                cmd.append("https://download.pytorch.org/whl/cu118")  # CUDA 11.8
            
            subprocess.run(cmd, check=True)
            logger.info("PyTorch installé avec succès")
        
        elif os_name == "linux":
            # Installation de PyTorch pour Linux
            cmd = [sys.executable, "-m", "pip", "install", "torch", "torchvision", "torchaudio"]
            if check_nvidia_gpu():
                cmd.append("--index-url")
                cmd.append("https://download.pytorch.org/whl/cu118")  # CUDA 11.8
            
            subprocess.run(cmd, check=True)
            logger.info("PyTorch installé avec succès")
        
        elif os_name == "darwin":  # macOS
            # Installation de PyTorch pour macOS
            subprocess.run([sys.executable, "-m", "pip", "install", "torch", "torchvision", "torchaudio"], check=True)
            logger.info("PyTorch installé avec succès")
        
        else:
            logger.warning(f"Système d'exploitation non reconnu: {os_name}. Installation de PyTorch standard.")
            subprocess.run([sys.executable, "-m", "pip", "install", "torch"], check=True)
    
    except subprocess.CalledProcessError as e:
        logger.error(f"Erreur lors de l'installation de PyTorch: {e}")
        logger.warning("La surveillance GPU sera désactivée")
    
    return True

def check_nvidia_gpu():
    """Vérifie si un GPU NVIDIA est présent sur le système."""
    try:
        if platform.system().lower() == "windows":
            # Vérification sur Windows
            result = subprocess.run(["nvidia-smi"], capture_output=True, text=True)
            return result.returncode == 0
        else:
            # Vérification sur Linux/macOS
            result = subprocess.run(["nvidia-smi"], capture_output=True, text=True)
            return result.returncode == 0
    except FileNotFoundError:
        logger.warning("nvidia-smi non trouvé, aucun GPU NVIDIA détecté")
        return False

def test_imports():
    """Teste l'importation des modules installés."""
    modules = {
        "psutil": "Module pour la surveillance des ressources système",
        "matplotlib": "Module pour l'affichage des graphiques",
        "numpy": "Module pour les calculs numériques",
        "torch": "Module pour l'accélération GPU (optionnel)"
    }
    
    all_success = True
    logger.info("Test des importations...")
    
    for module, description in modules.items():
        try:
            __import__(module)
            logger.info(f"✅ {module}: OK - {description}")
        except ImportError:
            if module == "torch":
                logger.warning(f"⚠️ {module}: Non installé - {description} - La surveillance GPU sera désactivée")
            else:
                logger.error(f"❌ {module}: Échec - {description}")
                all_success = False
    
    return all_success

def main():
    """Fonction principale."""
    logger.info("=== Installation des dépendances du moniteur de performances GBPBot ===")
    
    # Vérification de la version de Python
    if not check_python_version():
        logger.error("Version de Python incompatible. Arrêt de l'installation.")
        return 1
    
    # Vérification de pip
    if not check_pip():
        logger.error("pip est requis pour l'installation. Veuillez installer pip et réessayer.")
        return 1
    
    # Installation des dépendances
    if not install_dependencies():
        logger.error("Erreur lors de l'installation des dépendances.")
        return 1
    
    # Test des importations
    if not test_imports():
        logger.warning("Certaines importations ont échoué. Le moniteur pourrait ne pas fonctionner correctement.")
    
    logger.info("=== Installation terminée avec succès ===")
    logger.info("Vous pouvez maintenant exécuter le moniteur de performances avec la commande:")
    logger.info("python monitor_performance.py")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 