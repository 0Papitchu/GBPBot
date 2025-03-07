#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Installation des dépendances pour l'optimisation matérielle
=========================================================

Ce script installe les bibliothèques Python nécessaires pour
le module d'optimisation matérielle du GBPBot, notamment les
bibliothèques pour la détection du matériel et l'optimisation
des performances.
"""

import os
import sys
import subprocess
import platform
import logging
from typing import List, Dict, Any, Tuple

# Configuration du logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("install_optimization_deps")

# Dépendances requises pour l'optimisation matérielle
REQUIRED_PACKAGES = [
    "psutil>=5.9.0",       # Surveillance système
    "humanize>=4.0.0",     # Formatage convivial des chiffres
]

# Dépendances optionnelles par plateforme
PLATFORM_PACKAGES = {
    "win32": [
        "pywin32>=300",     # Accès aux API Windows
        "wmi>=1.5.1",       # Accès WMI pour la détection matérielle
    ],
    "linux": [
        "py-cpuinfo>=8.0.0",  # Informations CPU détaillées
    ],
    "darwin": [
        "py-cpuinfo>=8.0.0",  # Informations CPU détaillées
    ]
}

# Dépendances pour l'optimisation GPU par type
GPU_PACKAGES = {
    "tensorflow": [
        "tensorflow>=2.9.0;platform_system!='Darwin' or platform_machine!='arm64'",  # TensorFlow pour GPU
        "tensorflow-macos>=2.9.0;platform_system=='Darwin' and platform_machine=='arm64'",  # TensorFlow pour Mac M1
    ],
    "torch": [
        "torch>=1.11.0",    # PyTorch
        "torchvision>=0.12.0",  # Modules de vision pour PyTorch
    ],
    "common": [
        "numpy>=1.22.0",    # Calcul numérique
    ]
}

def print_banner():
    """Affiche la bannière d'installation"""
    banner = """
╔════════════════════════════════════════════════════════════╗
║                                                            ║
║   ██████╗ ██████╗ ██████╗ ██████╗  ██████╗ ████████╗      ║
║  ██╔════╝ ██╔══██╗██╔══██╗██╔══██╗██╔═══██╗╚══██╔══╝      ║
║  ██║  ███╗██████╔╝██████╔╝██████╔╝██║   ██║   ██║         ║
║  ██║   ██║██╔══██╗██╔═══╝ ██╔══██╗██║   ██║   ██║         ║
║  ╚██████╔╝██████╔╝██║     ██████╔╝╚██████╔╝   ██║         ║
║   ╚═════╝ ╚═════╝ ╚═╝     ╚═════╝  ╚═════╝    ╚═╝         ║
║                                                            ║
║        Installation des Dépendances d'Optimisation         ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
    """
    print(banner)

def get_gpu_info() -> Dict[str, Any]:
    """
    Détecte la présence d'un GPU NVIDIA ou AMD et retourne les informations.
    
    Returns:
        Dict contenant les informations GPU détectées
    """
    gpu_info = {
        "nvidia_available": False,
        "amd_available": False,
        "intel_available": False,
        "apple_silicon": False,
        "model": None
    }
    
    # Détection Apple Silicon
    if platform.system() == "Darwin" and platform.machine() == "arm64":
        gpu_info["apple_silicon"] = True
        gpu_info["model"] = "Apple Silicon"
        return gpu_info
    
    try:
        if platform.system() == "Windows":
            # Utiliser WMI pour détecter les GPU sur Windows
            try:
                import wmi
                w = wmi.WMI()
                for gpu in w.Win32_VideoController():
                    if "NVIDIA" in gpu.Name:
                        gpu_info["nvidia_available"] = True
                        gpu_info["model"] = gpu.Name
                        break
                    elif "AMD" in gpu.Name or "Radeon" in gpu.Name:
                        gpu_info["amd_available"] = True
                        gpu_info["model"] = gpu.Name
                        break
                    elif "Intel" in gpu.Name:
                        gpu_info["intel_available"] = True
                        gpu_info["model"] = gpu.Name
            except ImportError:
                logger.warning("WMI non disponible, impossible de détecter le GPU")
        
        elif platform.system() == "Linux":
            # Vérifier la présence de NVIDIA via lspci
            try:
                output = subprocess.check_output(["lspci"], text=True)
                if "NVIDIA" in output:
                    gpu_info["nvidia_available"] = True
                    # Essayer d'extraire le nom du modèle
                    for line in output.split("\n"):
                        if "NVIDIA" in line:
                            gpu_info["model"] = line.split(":")[-1].strip()
                            break
                elif "AMD" in output or "Radeon" in output:
                    gpu_info["amd_available"] = True
                    # Essayer d'extraire le nom du modèle
                    for line in output.split("\n"):
                        if "AMD" in line or "Radeon" in line:
                            gpu_info["model"] = line.split(":")[-1].strip()
                            break
                elif "Intel" in output and "Graphics" in output:
                    gpu_info["intel_available"] = True
                    # Essayer d'extraire le nom du modèle
                    for line in output.split("\n"):
                        if "Intel" in line and "Graphics" in line:
                            gpu_info["model"] = line.split(":")[-1].strip()
                            break
            except (subprocess.SubprocessError, FileNotFoundError):
                logger.warning("lspci non disponible, impossible de détecter le GPU")
    
    except Exception as e:
        logger.warning(f"Erreur lors de la détection du GPU: {str(e)}")
    
    return gpu_info

def get_all_packages() -> List[str]:
    """
    Détermine toutes les dépendances à installer en fonction du matériel détecté.
    
    Returns:
        Liste des packages à installer
    """
    packages = REQUIRED_PACKAGES.copy()
    
    # Ajouter les packages spécifiques à la plateforme
    system = platform.system().lower()
    if system == "windows":
        packages.extend(PLATFORM_PACKAGES["win32"])
    elif system == "linux":
        packages.extend(PLATFORM_PACKAGES["linux"])
    elif system == "darwin":
        packages.extend(PLATFORM_PACKAGES["darwin"])
    
    # Détecter le GPU et ajouter les packages correspondants
    gpu_info = get_gpu_info()
    if gpu_info["nvidia_available"]:
        # NVIDIA est détecté, ajouter PyTorch avec CUDA
        logger.info(f"GPU NVIDIA détecté: {gpu_info['model']}")
        packages.extend(GPU_PACKAGES["torch"])
        packages.extend(GPU_PACKAGES["tensorflow"])
    elif gpu_info["amd_available"] or gpu_info["intel_available"] or gpu_info["apple_silicon"]:
        # AMD/Intel/Apple Silicon détecté, ajouter PyTorch sans CUDA
        logger.info(f"GPU détecté: {gpu_info['model']}")
        packages.extend(GPU_PACKAGES["torch"])
        packages.extend(GPU_PACKAGES["tensorflow"])
    
    # Dans tous les cas, ajouter les packages GPU communs
    packages.extend(GPU_PACKAGES["common"])
    
    return packages

def install_packages(packages: List[str]) -> bool:
    """
    Installe les packages spécifiés avec pip.
    
    Args:
        packages: Liste des packages à installer
        
    Returns:
        True si l'installation a réussi, False sinon
    """
    if not packages:
        logger.info("Aucun package à installer")
        return True
    
    logger.info(f"Installation de {len(packages)} packages...")
    
    try:
        # Construire la commande pip avec tous les packages
        cmd = [sys.executable, "-m", "pip", "install", "--upgrade"]
        cmd.extend(packages)
        
        # Exécuter l'installation
        logger.info(f"Exécution de la commande: {' '.join(cmd)}")
        subprocess.check_call(cmd)
        
        logger.info("Installation des packages terminée avec succès")
        return True
    
    except subprocess.CalledProcessError as e:
        logger.error(f"Erreur lors de l'installation des packages: {str(e)}")
        return False

def check_cuda_availability() -> Tuple[bool, str]:
    """
    Vérifie si CUDA est disponible et retourne sa version.
    
    Returns:
        Tuple (disponibilité, version)
    """
    try:
        import torch
        
        cuda_available = torch.cuda.is_available()
        cuda_version = torch.version.cuda if cuda_available else "Non disponible"
        
        return cuda_available, cuda_version
    
    except ImportError:
        return False, "PyTorch non installé"

def main():
    """Fonction principale d'installation des dépendances"""
    print_banner()
    
    print("\n📋 Vérification du système...")
    system = platform.system()
    release = platform.release()
    machine = platform.machine()
    
    print(f"Système détecté: {system} {release} ({machine})")
    
    # Obtenir la liste complète des packages à installer
    packages = get_all_packages()
    
    print(f"\n📦 Packages à installer ({len(packages)}):")
    for package in packages:
        print(f"  - {package}")
    
    # Demander confirmation à l'utilisateur
    confirm = input("\n🔄 Continuer avec l'installation? (o/n): ")
    if confirm.lower() != "o":
        print("❌ Installation annulée")
        return 1
    
    # Installer les packages
    print("\n🔄 Installation des packages...")
    success = install_packages(packages)
    
    if success:
        print("\n✅ Installation terminée avec succès!")
        
        # Vérifier la disponibilité de CUDA si un GPU NVIDIA est détecté
        gpu_info = get_gpu_info()
        if gpu_info["nvidia_available"]:
            cuda_available, cuda_version = check_cuda_availability()
            
            if cuda_available:
                print(f"\n🎮 CUDA est disponible (version {cuda_version})!")
                print("  → Optimisations GPU activées pour les modèles d'IA.")
            else:
                print("\n⚠️ CUDA n'est pas disponible malgré la détection d'un GPU NVIDIA.")
                print("  → Les performances GPU pourraient être limitées.")
        
        print("\n📝 Pour utiliser l'optimiseur matériel, exécutez:")
        print("  python -m gbpbot.core.optimization.optimize_hardware")
        return 0
    else:
        print("\n❌ L'installation a échoué. Consultez les messages d'erreur ci-dessus.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 