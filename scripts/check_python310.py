#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vérification de Python 3.10 pour GBPBot
=======================================

Ce script vérifie si Python 3.10 est installé et disponible sur le système.
Il affiche des instructions pour l'installer si nécessaire.
"""

import sys
import os
import platform
import subprocess
from pathlib import Path
import logging

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("python_checker")

def get_python_versions():
    """
    Détecte les versions de Python installées sur le système
    
    Returns:
        list: Liste des versions Python détectées
    """
    versions = []
    
    # Méthode pour Windows
    if platform.system() == "Windows":
        try:
            # Rechercher dans les emplacements standards
            program_files = os.environ.get("ProgramFiles", "C:\\Program Files")
            program_files_x86 = os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")
            
            # Chercher dans Program Files
            python_dirs = list(Path(program_files).glob("Python*")) + list(Path(program_files_x86).glob("Python*"))
            
            for python_dir in python_dirs:
                python_exe = python_dir / "python.exe"
                if python_exe.exists():
                    try:
                        # Exécuter python --version pour obtenir la version
                        result = subprocess.run(
                            [str(python_exe), "--version"],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True,
                            check=False
                        )
                        if result.returncode == 0:
                            version_str = result.stdout.strip() or result.stderr.strip()
                            if version_str:
                                versions.append({
                                    "path": str(python_exe),
                                    "version": version_str
                                })
                    except Exception as e:
                        logger.debug(f"Erreur lors de la vérification de {python_exe}: {e}")
            
            # Chercher également avec le launcher py
            try:
                for version in ["3.7", "3.8", "3.9", "3.10", "3.11", "3.12"]:
                    result = subprocess.run(
                        ["py", f"-{version}", "--version"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        check=False
                    )
                    if result.returncode == 0:
                        version_str = result.stdout.strip() or result.stderr.strip()
                        if version_str:
                            # Trouver le chemin complet
                            path_result = subprocess.run(
                                ["py", f"-{version}", "-c", "import sys; print(sys.executable)"],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True,
                                check=False
                            )
                            path = path_result.stdout.strip() if path_result.returncode == 0 else "Unknown"
                            
                            versions.append({
                                "path": path,
                                "version": version_str
                            })
            except Exception as e:
                logger.debug(f"Erreur lors de la vérification avec py: {e}")
                
        except Exception as e:
            logger.error(f"Erreur lors de la recherche des versions Python: {e}")
    
    # Méthode pour Linux/macOS
    else:
        try:
            # Chercher les versions de Python dans le PATH
            for cmd in ["python3.10", "python3.9", "python3.11", "python3.12", "python3.8", "python3.7", "python3"]:
                try:
                    # Vérifier si la commande existe
                    which_result = subprocess.run(
                        ["which", cmd],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        check=False
                    )
                    
                    if which_result.returncode == 0:
                        python_path = which_result.stdout.strip()
                        
                        # Obtenir la version
                        version_result = subprocess.run(
                            [python_path, "--version"],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True,
                            check=False
                        )
                        
                        if version_result.returncode == 0:
                            version_str = version_result.stdout.strip() or version_result.stderr.strip()
                            if version_str:
                                versions.append({
                                    "path": python_path,
                                    "version": version_str
                                })
                except Exception as e:
                    logger.debug(f"Erreur lors de la vérification de {cmd}: {e}")
        except Exception as e:
            logger.error(f"Erreur lors de la recherche des versions Python: {e}")
    
    return versions

def has_python310():
    """
    Vérifie si Python 3.10 est installé
    
    Returns:
        tuple: (bool, str) - True si Python 3.10 est installé, et le chemin vers l'exécutable
    """
    # Vérifier si la version actuelle est 3.10
    current_version = sys.version_info
    if current_version.major == 3 and current_version.minor == 10:
        return True, sys.executable
    
    # Chercher les autres installations
    versions = get_python_versions()
    
    for version_info in versions:
        version_str = version_info["version"]
        if "Python 3.10" in version_str:
            return True, version_info["path"]
    
    return False, None

def create_venv_with_python310(python310_path, venv_name="venv_310"):
    """
    Crée un environnement virtuel avec Python 3.10
    
    Args:
        python310_path: Chemin vers l'exécutable Python 3.10
        venv_name: Nom de l'environnement virtuel à créer
        
    Returns:
        bool: True si la création a réussi, False sinon
    """
    logger.info(f"Création d'un environnement virtuel avec Python 3.10: {venv_name}")
    
    try:
        # Créer l'environnement virtuel
        result = subprocess.run(
            [python310_path, "-m", "venv", venv_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
        
        if result.returncode == 0:
            logger.info(f"Environnement virtuel {venv_name} créé avec succès")
            
            # Afficher les commandes pour activer l'environnement
            if platform.system() == "Windows":
                activate_cmd = f"{venv_name}\\Scripts\\activate"
            else:
                activate_cmd = f"source {venv_name}/bin/activate"
            
            print("\nPour activer l'environnement virtuel:")
            print(f"  {activate_cmd}")
            print("\nPour installer les dépendances:")
            print(f"  {venv_name}\\Scripts\\python scripts\\install_dependencies_py310.py" if platform.system() == "Windows" else f"{venv_name}/bin/python scripts/install_dependencies_py310.py")
            
            return True
        else:
            logger.error(f"Erreur lors de la création de l'environnement virtuel: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"Erreur lors de la création de l'environnement virtuel: {e}")
        return False

def show_install_instructions():
    """Affiche les instructions d'installation de Python 3.10"""
    print("\n" + "="*60)
    print(" "*15 + "Installation de Python 3.10")
    print("="*60 + "\n")
    
    if platform.system() == "Windows":
        print("1. Téléchargez Python 3.10 depuis le site officiel:")
        print("   https://www.python.org/downloads/release/python-31012/")
        print("\n2. Exécutez l'installateur et cochez les options suivantes:")
        print("   - Install launcher for all users")
        print("   - Add Python 3.10 to PATH")
        print("\n3. Cliquez sur 'Install Now'")
        print("\n4. Une fois l'installation terminée, redémarrez votre terminal et réexécutez ce script")
    else:
        print("Instructions pour Linux/macOS:")
        print("\n- Ubuntu/Debian:")
        print("  sudo apt update")
        print("  sudo apt install python3.10 python3.10-venv python3.10-dev")
        print("\n- macOS (avec Homebrew):")
        print("  brew install python@3.10")
        print("\n- Fedora:")
        print("  sudo dnf install python3.10")
        print("\n- Arch Linux:")
        print("  sudo pacman -S python310")
        print("\nUne fois l'installation terminée, réexécutez ce script")
    
    print("\n" + "="*60)

def main():
    """Fonction principale"""
    print("\n" + "="*60)
    print(" "*10 + "GBPBot - Vérification de Python 3.10")
    print("="*60 + "\n")
    
    has_310, python310_path = has_python310()
    
    if has_310:
        # Python 3.10 est disponible
        print(f"✅ Python 3.10 est installé: {python310_path}")
        
        # Vérifier s'il s'agit de la version actuelle
        current_version = sys.version_info
        if current_version.major == 3 and current_version.minor == 10:
            print("✅ Vous utilisez déjà Python 3.10")
            
            # Proposer de créer un environnement virtuel
            create_venv = input("Voulez-vous créer un nouvel environnement virtuel avec Python 3.10? (o/N): ")
            if create_venv.lower() == "o":
                venv_name = input("Nom de l'environnement virtuel [venv_310]: ") or "venv_310"
                create_venv_with_python310(python310_path, venv_name)
        else:
            print(f"ℹ️ Vous utilisez actuellement Python {current_version.major}.{current_version.minor}")
            print(f"ℹ️ Python 3.10 est disponible à: {python310_path}")
            
            # Proposer de créer un environnement virtuel
            create_venv = input("Voulez-vous créer un environnement virtuel avec Python 3.10? (O/n): ")
            if create_venv.lower() != "n":
                venv_name = input("Nom de l'environnement virtuel [venv_310]: ") or "venv_310"
                create_venv_with_python310(python310_path, venv_name)
    else:
        # Python 3.10 n'est pas disponible
        print("❌ Python 3.10 n'est pas installé sur votre système")
        print("Python 3.10 est recommandé pour GBPBot car certaines dépendances Solana ne sont pas compatibles avec Python 3.11+")
        
        # Afficher les autres versions disponibles
        versions = get_python_versions()
        if versions:
            print("\nVersions Python détectées:")
            for v in versions:
                print(f"- {v['version']} ({v['path']})")
        
        # Afficher les instructions d'installation
        show_instructions = input("Voulez-vous voir les instructions d'installation de Python 3.10? (O/n): ")
        if show_instructions.lower() != "n":
            show_install_instructions()
    
    print("\nAu revoir!")

if __name__ == "__main__":
    main() 