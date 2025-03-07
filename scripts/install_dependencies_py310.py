#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Installation des dépendances pour GBPBot avec Python 3.10
========================================================

Ce script installe les dépendances nécessaires pour GBPBot, en s'assurant
qu'elles sont compatibles avec Python 3.10 (recommandé pour la compatibilité Solana).
"""

import os
import sys
import platform
import subprocess
import argparse
import tempfile
from pathlib import Path
import logging

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("dependencies_installer")

# Vérification de la version de Python
python_version = platform.python_version()
python_major, python_minor, _ = map(int, python_version.split('.'))

if python_major != 3 or python_minor != 10:
    logger.warning(f"Ce script est optimisé pour Python 3.10, mais vous utilisez Python {python_version}")
    if python_major == 3 and python_minor > 10:
        logger.warning("Vous utilisez une version plus récente de Python, certains packages Solana pourraient ne pas être compatibles")
    proceed = input("Voulez-vous continuer quand même? (O/n): ")
    if proceed.lower() == "n":
        sys.exit(0)

# Dépendances de base (compatibles avec toutes les versions de Python)
BASE_DEPENDENCIES = [
    "python-dotenv",
    "requests",
    "pandas",
    "numpy",
    "websockets",
    "asyncio",
    "aiohttp",
    "cryptography",
    "pydantic",
    "loguru",
    "rich",
    "nest_asyncio"
]

# Dépendances optionnelles
OPTIONAL_DEPENDENCIES = [
    "fastapi",
    "uvicorn",
    "python-telegram-bot",
    "matplotlib",
    "seaborn",
    "scikit-learn"
]

# Dépendances spécifiques à Solana (avec gestion de compatibilité)
SOLANA_DEPENDENCIES = [
    "solana-py",  # Alternative à solders, fonctionne sur Python 3.10+
    "base58",
    "construct",
    "PyNaCl"
]

# Dépendances pour Avalanche et EVM
EVM_DEPENDENCIES = [
    "web3",
    "eth-abi",
    "eth-account",
    "eth-typing"
]

# Dépendances TensorFlow et PyTorch pour l'IA (selon GPU disponible)
AI_DEPENDENCIES_CPU = [
    "tensorflow",
    "torch",
    "torchvision",
    "torchaudio"
]

AI_DEPENDENCIES_CUDA = [
    # Ces dépendances seront installées avec une commande spéciale
]

def check_gpu():
    """
    Vérifie si une carte graphique NVIDIA compatible CUDA est disponible
    
    Returns:
        bool: True si une carte NVIDIA est détectée, False sinon
    """
    try:
        # Pour Windows
        if platform.system() == "Windows":
            # Vérifier avec nvidia-smi
            result = subprocess.run(["nvidia-smi"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
            return result.returncode == 0
        # Pour Linux
        else:
            # Essayer lspci
            result = subprocess.run(["lspci"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
            return "NVIDIA" in result.stdout
    except Exception as e:
        logger.debug(f"Erreur lors de la vérification GPU: {e}")
        return False

def create_requirements_file(dependencies, filename="requirements_temp.txt"):
    """
    Crée un fichier requirements.txt temporaire avec les dépendances spécifiées
    
    Args:
        dependencies: Liste des dépendances à inclure
        filename: Nom du fichier à créer
        
    Returns:
        str: Chemin vers le fichier créé
    """
    temp_file = Path(tempfile.gettempdir()) / filename
    
    with open(temp_file, "w") as f:
        for dep in dependencies:
            f.write(f"{dep}\n")
    
    return str(temp_file)

def install_pip_dependencies(dependencies, upgrade=False):
    """
    Installe les dépendances pip spécifiées
    
    Args:
        dependencies: Liste des dépendances à installer
        upgrade: Si True, met à jour les dépendances existantes
        
    Returns:
        bool: True si l'installation a réussi, False sinon
    """
    if not dependencies:
        return True
        
    # Créer le fichier requirements temporaire
    req_file = create_requirements_file(dependencies)
    
    # Commande d'installation
    cmd = [sys.executable, "-m", "pip", "install", "-r", req_file]
    
    if upgrade:
        cmd.insert(5, "--upgrade")
    
    logger.info(f"Installation de {len(dependencies)} dépendances...")
    for dep in dependencies:
        logger.info(f"- {dep}")
    
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
        
        if result.returncode == 0:
            logger.info("Installation réussie")
            return True
        else:
            logger.error(f"Erreur lors de l'installation: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"Erreur lors de l'installation: {e}")
        return False
    finally:
        # Supprimer le fichier temporaire
        try:
            os.remove(req_file)
        except:
            pass

def install_pytorch_cuda():
    """
    Installe PyTorch avec support CUDA
    
    Returns:
        bool: True si l'installation a réussi, False sinon
    """
    logger.info("Installation de PyTorch avec support CUDA...")
    
    # Déterminer la commande d'installation selon le système
    if platform.system() == "Windows":
        cmd = [
            sys.executable, "-m", "pip", "install", 
            "torch", "torchvision", "torchaudio", 
            "--index-url", "https://download.pytorch.org/whl/cu118"
        ]
    else:
        cmd = [
            sys.executable, "-m", "pip", "install", 
            "torch", "torchvision", "torchaudio", 
            "--index-url", "https://download.pytorch.org/whl/cu118"
        ]
    
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
        
        if result.returncode == 0:
            logger.info("Installation de PyTorch avec CUDA réussie")
            return True
        else:
            logger.error(f"Erreur lors de l'installation de PyTorch: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"Erreur lors de l'installation de PyTorch: {e}")
        return False

def install_tensorflow_gpu():
    """
    Installe TensorFlow avec support GPU
    
    Returns:
        bool: True si l'installation a réussi, False sinon
    """
    logger.info("Installation de TensorFlow avec support GPU...")
    
    cmd = [sys.executable, "-m", "pip", "install", "tensorflow"]
    
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
        
        if result.returncode == 0:
            logger.info("Installation de TensorFlow réussie")
            return True
        else:
            logger.error(f"Erreur lors de l'installation de TensorFlow: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"Erreur lors de l'installation de TensorFlow: {e}")
        return False

def check_pip_version():
    """
    Vérifie et met à jour pip si nécessaire
    
    Returns:
        bool: True si pip est à jour, False sinon
    """
    logger.info("Vérification de la version de pip...")
    
    try:
        # Vérifier la version actuelle
        result = subprocess.run([sys.executable, "-m", "pip", "--version"], stdout=subprocess.PIPE, text=True, check=True)
        logger.info(f"Version de pip: {result.stdout.strip()}")
        
        # Mettre à jour pip
        logger.info("Mise à jour de pip...")
        update_result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "pip"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
        
        if update_result.returncode == 0:
            logger.info("Pip mis à jour avec succès")
            return True
        else:
            logger.warning(f"Erreur lors de la mise à jour de pip: {update_result.stderr}")
            logger.warning("Continuation avec la version actuelle")
            return False
    except Exception as e:
        logger.warning(f"Erreur lors de la vérification de pip: {e}")
        return False

def main():
    """Fonction principale pour installer les dépendances"""
    parser = argparse.ArgumentParser(description="Installe les dépendances pour GBPBot")
    parser.add_argument("--all", action="store_true", help="Installe toutes les dépendances")
    parser.add_argument("--base", action="store_true", help="Installe uniquement les dépendances de base")
    parser.add_argument("--blockchain", action="store_true", help="Installe les dépendances blockchain (Solana, Avalanche)")
    parser.add_argument("--ai", action="store_true", help="Installe les dépendances AI (TensorFlow, PyTorch)")
    parser.add_argument("--upgrade", action="store_true", help="Met à jour les dépendances existantes")
    parser.add_argument("--cuda", action="store_true", help="Force l'installation des versions CUDA (GPU)")
    parser.add_argument("--cpu", action="store_true", help="Force l'installation des versions CPU")
    
    args = parser.parse_args()
    
    print("\n" + "="*60)
    print(" "*15 + "GBPBot - Installation des Dépendances")
    print("="*60 + "\n")
    
    # Si aucune option n'est spécifiée, installer tout
    if not (args.all or args.base or args.blockchain or args.ai):
        args.all = True
    
    # Vérifier et mettre à jour pip
    check_pip_version()
    
    # Installer les dépendances de base
    if args.all or args.base:
        logger.info("Installation des dépendances de base...")
        install_pip_dependencies(BASE_DEPENDENCIES, args.upgrade)
    
    # Installer les dépendances blockchain
    if args.all or args.blockchain:
        logger.info("Installation des dépendances blockchain...")
        
        # Installer les dépendances Solana
        logger.info("Installation des dépendances Solana...")
        install_pip_dependencies(SOLANA_DEPENDENCIES, args.upgrade)
        
        # Installer les dépendances EVM (Avalanche)
        logger.info("Installation des dépendances EVM (Avalanche)...")
        install_pip_dependencies(EVM_DEPENDENCIES, args.upgrade)
    
    # Installer les dépendances optionnelles
    if args.all:
        logger.info("Installation des dépendances optionnelles...")
        install_pip_dependencies(OPTIONAL_DEPENDENCIES, args.upgrade)
    
    # Installer les dépendances IA
    if args.all or args.ai:
        logger.info("Installation des dépendances IA...")
        
        # Vérifier si une carte NVIDIA est disponible
        has_gpu = check_gpu()
        
        if has_gpu and not args.cpu:
            logger.info("Carte GPU NVIDIA détectée, installation des versions CUDA")
            # Installer PyTorch avec CUDA
            install_pytorch_cuda()
            # Installer TensorFlow avec GPU
            install_tensorflow_gpu()
        elif args.cuda:
            logger.warning("Installation forcée des versions CUDA demandée")
            install_pytorch_cuda()
            install_tensorflow_gpu()
        else:
            logger.info("Installation des versions CPU des bibliothèques d'IA")
            install_pip_dependencies(AI_DEPENDENCIES_CPU, args.upgrade)
    
    print("\n" + "="*60)
    print(" "*15 + "Installation terminée")
    print("="*60 + "\n")
    
    # Proposer le test des connexions blockchain
    if args.all or args.blockchain:
        test_connections = input("Souhaitez-vous tester les connexions blockchain maintenant? (O/n): ")
        if test_connections.lower() != "n":
            try:
                # Exécuter le script de test
                subprocess.run([sys.executable, "test_blockchain_connections.py"])
            except Exception as e:
                logger.error(f"Erreur lors du lancement du test: {e}")

if __name__ == "__main__":
    main() 