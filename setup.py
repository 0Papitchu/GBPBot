#!/usr/bin/env python3
"""
GBPBot - Script d'installation
===============================

Ce script installe toutes les dépendances nécessaires pour GBPBot
et configure l'environnement de développement.
"""

import os
import sys
import platform
import subprocess
import shutil
from setuptools import setup, find_packages

# Version du package
VERSION = "1.0.0"

# Liste des dépendances communes
COMMON_REQUIRES = [
    "aiohttp==3.8.5",
    "asyncio==3.4.3",
    "python-dotenv==1.0.0",
    "pyyaml==6.0.1",
    "colorama==0.4.6",
    "pytz==2023.3",
    "tqdm==4.66.1",
    "requests==2.31.0",
    "typing-extensions==4.7.1",
    "psutil==5.9.5",
    "matplotlib==3.7.2",
    "numpy==1.24.3",
    "pandas==2.0.3",
    "websockets>=9.0,<11.0",
    "cryptography==41.0.3",
    "telegram-send==0.34",
]

# Dépendances spécifiques à Solana
SOLANA_REQUIRES = [
    "solana==0.30.2",
    "solders>=0.15.1,<0.16.0",
    "anchorpy==0.17.0",
    "base58==2.1.1",
]

# Dépendances spécifiques à Avalanche
AVAX_REQUIRES = [
    "web3==6.5.0",
    "eth-account==0.8.0",
    "eth-hash==0.5.1",
    "eth-typing==3.3.0",
    "eth-utils==2.1.1",
]

# Dépendances de développement
DEV_REQUIRES = [
    "pytest==7.4.0",
    "pytest-asyncio==0.21.1",
    "black==23.7.0",
    "mypy==1.4.1",
    "flake8==6.1.0",
    "isort==5.12.0",
]

def print_colored(text, color):
    """Affiche du texte en couleur dans la console."""
    colors = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "purple": "\033[95m",
        "end": "\033[0m",
    }
    # Remplacer les caractères Unicode par des alternatives ASCII
    text = text.replace("✓", "OK")
    print(f"{colors.get(color, '')}{text}{colors.get('end', '')}")

def check_python_version():
    """Vérifie la version de Python."""
    min_version = (3, 8)
    current_version = sys.version_info[:2]
    
    if current_version < min_version:
        print_colored(
            f"Erreur: Python {min_version[0]}.{min_version[1]} ou supérieur est requis. "
            f"Vous utilisez Python {current_version[0]}.{current_version[1]}",
            "red"
        )
        sys.exit(1)
    
    print_colored(
        f"Python {current_version[0]}.{current_version[1]} détecté. OK",
        "green"
    )

def install_platform_dependencies():
    """Installe les dépendances spécifiques à la plateforme."""
    system = platform.system().lower()
    
    if system == "windows":
        print_colored("Installation des dépendances Windows...", "blue")
        # Windows-specific dependencies or actions if needed
    
    elif system == "linux":
        print_colored("Installation des dépendances Linux...", "blue")
        try:
            subprocess.run(["apt-get", "update"], check=True)
            subprocess.run(
                ["apt-get", "install", "-y", "build-essential", "libssl-dev"],
                check=True,
            )
        except subprocess.CalledProcessError:
            print_colored(
                "Avertissement: Impossible d'installer les dépendances Linux. "
                "Vous devrez peut-être les installer manuellement.", 
                "yellow"
            )
    
    elif system == "darwin":  # macOS
        print_colored("Installation des dépendances macOS...", "blue")
        try:
            # Install homebrew if not installed
            if shutil.which("brew") is None:
                print_colored("Installation de Homebrew...", "blue")
                homebrew_install = (
                    '/bin/bash -c "$(curl -fsSL '
                    'https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
                )
                subprocess.run(homebrew_install, shell=True, check=True)
            
            # Install required packages
            subprocess.run(["brew", "install", "openssl"], check=True)
        except subprocess.CalledProcessError:
            print_colored(
                "Avertissement: Impossible d'installer les dépendances macOS. "
                "Vous devrez peut-être les installer manuellement.",
                "yellow"
            )

def create_env_file():
    """Crée un fichier .env à partir du modèle s'il n'existe pas."""
    if not os.path.exists(".env") and os.path.exists(".env.example"):
        print_colored("Création du fichier .env à partir du modèle...", "blue")
        shutil.copy(".env.example", ".env")
        print_colored("Fichier .env créé. Veuillez l'éditer avec vos informations.", "green")

def setup_optimization_tools():
    """Configure les outils d'optimisation."""
    if os.path.exists("setup_optimization_tools.py"):
        print_colored("Configuration des outils d'optimisation...", "blue")
        try:
            subprocess.run([sys.executable, "setup_optimization_tools.py"], check=True)
            print_colored("Outils d'optimisation configurés avec succès. OK", "green")
        except subprocess.CalledProcessError:
            print_colored(
                "Avertissement: Impossible de configurer les outils d'optimisation. "
                "Vous pouvez les configurer manuellement plus tard avec la commande: "
                "python setup_optimization_tools.py",
                "yellow"
            )

def main():
    """Fonction principale d'installation."""
    print_colored("\n=== GBPBot - Installation ===\n", "purple")
    
    # Vérifier la version de Python
    check_python_version()
    
    # Installer les dépendances spécifiques à la plateforme
    install_platform_dependencies()
    
    # Combinaison de toutes les dépendances
    all_requires = COMMON_REQUIRES + SOLANA_REQUIRES + AVAX_REQUIRES
    
    # Configuration de setuptools
    setup(
        name="gbpbot",
        version=VERSION,
        description="Trading Bot pour MEME Coins sur Solana, AVAX et Sonic",
        author="GBPBot Team",
        author_email="contact@gbpbot.com",
        url="https://github.com/yourusername/GBPBot",
        packages=find_packages(),
        install_requires=all_requires,
        extras_require={
            "dev": DEV_REQUIRES,
            "solana": SOLANA_REQUIRES,
            "avax": AVAX_REQUIRES,
            "all": SOLANA_REQUIRES + AVAX_REQUIRES + DEV_REQUIRES,
        },
        entry_points={
            "console_scripts": [
                "gbpbot=gbpbot.main:main",
            ],
        },
        python_requires=">=3.8",
        classifiers=[
            "Development Status :: 4 - Beta",
            "Intended Audience :: Financial and Insurance Industry",
            "License :: OSI Approved :: MIT License",
            "Programming Language :: Python :: 3",
            "Programming Language :: Python :: 3.8",
            "Programming Language :: Python :: 3.9",
            "Programming Language :: Python :: 3.10",
            "Topic :: Office/Business :: Financial :: Investment",
        ],
    )
    
    # Créer le fichier .env
    create_env_file()
    
    # Configurer les outils d'optimisation
    setup_optimization_tools()
    
    print_colored("\n=== Installation de GBPBot terminée ===\n", "purple")
    print_colored("Pour démarrer GBPBot, exécutez:", "blue")
    print_colored("  python -m gbpbot.gbpbot_menu", "green")
    print_colored("ou:", "blue")
    print_colored("  python main.py", "green")
    
    print_colored("\nPour plus d'informations, consultez README.md\n", "blue")

if __name__ == "__main__":
    main() 