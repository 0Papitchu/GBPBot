"""
Module d'Optimisation pour GBPBot
================================

Ce module applique diverses optimisations au GBPBot pour améliorer ses performances
sur la configuration matérielle de l'utilisateur, en ajustant l'utilisation mémoire,
la configuration des logs, et l'utilisation du GPU.
"""

import os
import sys
import re
import logging
import platform
import subprocess
import psutil
from typing import Dict, Any, Optional

# Configuration du logging basique
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("gbpbot.optimizer")

# Variables globales pour le suivi de l'optimisation
optimization_applied = False
hardware_info = None

def apply_optimizations(config: Dict) -> Dict:
    """
    Applique toutes les optimisations au GBPBot en fonction de la configuration matérielle
    
    Args:
        config: Configuration actuelle du bot
        
    Returns:
        Dict: Configuration optimisée
    """
    global optimization_applied, hardware_info
    
    if optimization_applied:
        logger.info("Les optimisations ont déjà été appliquées")
        return config
    
    logger.info("Application des optimisations pour le GBPBot...")
    
    try:
        # Récupérer les informations sur le matériel
        hardware_info = get_hardware_info()
        logger.info(f"Configuration matérielle détectée: {hardware_info}")
        
        # Optimiser la configuration
        optimized_config = optimize_config_for_hardware(config, hardware_info)
        
        # Configurer la rotation des logs
        try:
            from gbpbot.utils.log_optimizer import setup_optimized_logging
            setup_optimized_logging(optimized_config)
        except ImportError:
            logger.warning("Module d'optimisation des logs non disponible")
        
        # Configurer l'optimisation mémoire pour le ML
        try:
            from gbpbot.machine_learning.memory_optimizer import init_memory_monitoring, setup_gpu_acceleration
            init_memory_monitoring(optimized_config, memory_warning_callback)
            
            # Configurer l'accélération GPU si disponible
            if hardware_info.get("has_gpu", False):
                setup_gpu_acceleration(optimized_config)
        except ImportError:
            logger.warning("Module d'optimisation mémoire ML non disponible")
        
        # Installer les dépendances manquantes si nécessaire
        if optimized_config.get("INSTALL_MISSING_DEPENDENCIES", "true").lower() == "true":
            install_missing_dependencies(hardware_info)
        
        optimization_applied = True
        logger.info("Optimisations appliquées avec succès!")
        
        return optimized_config
        
    except Exception as e:
        logger.error(f"Erreur lors de l'application des optimisations: {str(e)}")
        return config

def get_hardware_info() -> Dict:
    """
    Récupère les informations sur le matériel
    
    Returns:
        Dict: Informations sur le matériel
    """
    info = {}
    
    try:
        # CPU
        info["cpu_count"] = os.cpu_count()
        info["cpu_threads"] = psutil.cpu_count(logical=True)
        info["cpu_physical"] = psutil.cpu_count(logical=False)
        
        # OS
        info["os"] = platform.system()
        info["os_version"] = platform.version()
        
        # RAM
        mem = psutil.virtual_memory()
        info["ram_total_gb"] = round(mem.total / (1024**3), 2)
        info["ram_available_gb"] = round(mem.available / (1024**3), 2)
        
        # Détection GPU
        info["has_gpu"] = False
        info["gpu_name"] = "None"
        info["gpu_memory_gb"] = 0
        
        # Tenter de détecter NVIDIA GPU avec CUDA
        try:
            import pynvml
            pynvml.nvmlInit()
            device_count = pynvml.nvmlDeviceGetCount()
            if device_count > 0:
                handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                info["has_gpu"] = True
                info["gpu_name"] = pynvml.nvmlDeviceGetName(handle).decode('utf-8')
                memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                info["gpu_memory_gb"] = round(memory_info.total / (1024**3), 2)
            pynvml.nvmlShutdown()
        except Exception:
            pass

        # Si pas détecté avec CUDA, essayer avec Windows WMI
        if not info["has_gpu"] and platform.system() == "Windows":
            try:
                import wmi
                computer = wmi.WMI()
                gpu_info = computer.Win32_VideoController()[0]
                info["has_gpu"] = True
                info["gpu_name"] = gpu_info.Name
                info["gpu_memory_gb"] = round(int(gpu_info.AdapterRAM) / (1024**3), 2) if hasattr(gpu_info, "AdapterRAM") else 0
            except Exception:
                pass

        # Si toujours pas détecté, essayer avec lshw sur Linux
        if not info["has_gpu"] and platform.system() == "Linux":
            try:
                gpu_info = subprocess.check_output(['lshw', '-C', 'display']).decode('utf-8')
                if 'product' in gpu_info:
                    info["has_gpu"] = True
                    info["gpu_name"] = re.search(r'product: (.*)', gpu_info).group(1)
            except Exception:
                pass

        return info
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des informations matérielles: {str(e)}")
        return {"error": str(e)}

def optimize_config_for_hardware(config: Dict, hardware_info: Dict) -> Dict:
    """
    Optimise la configuration en fonction du matériel détecté
    
    Args:
        config: Configuration actuelle
        hardware_info: Informations sur le matériel
        
    Returns:
        Dict: Configuration optimisée
    """
    # Copier la configuration pour ne pas modifier l'original
    optimized = config.copy()
    
    # CPU
    cpu_threads = hardware_info.get("cpu_threads", 0)
    if cpu_threads > 0:
        # Optimiser l'intervalle de vérification pour l'arbitrage en fonction du CPU
        if cpu_threads <= 4:
            optimized["ARBITRAGE_CHECK_INTERVAL"] = "8"  # Plus lent pour les CPU faibles
        elif cpu_threads <= 8:
            optimized["ARBITRAGE_CHECK_INTERVAL"] = "5"  # Moyen pour les CPU moyens
        else:
            optimized["ARBITRAGE_CHECK_INTERVAL"] = "3"  # Rapide pour les CPU puissants
        
        # Optimiser l'intervalle de vérification pour le frontrunning
        if cpu_threads <= 4:
            optimized["FRONTRUN_CHECK_INTERVAL"] = "2.0"  # Plus lent
        elif cpu_threads <= 8:
            optimized["FRONTRUN_CHECK_INTERVAL"] = "1.5"  # Moyen
        else:
            optimized["FRONTRUN_CHECK_INTERVAL"] = "1.0"  # Rapide
    
    # RAM
    ram_gb = hardware_info.get("ram_total_gb", 0)
    if ram_gb > 0:
        # Optimiser l'utilisation de la mémoire pour le ML
        if ram_gb < 8:
            optimized["ML_MAX_MEMORY_USAGE"] = "2048"  # 2GB pour les systèmes < 8GB RAM
            optimized["MAX_PAIRS_MONITORED"] = "10"
        elif ram_gb < 16:
            optimized["ML_MAX_MEMORY_USAGE"] = "4096"  # 4GB pour les systèmes entre 8 et 16GB RAM
            optimized["MAX_PAIRS_MONITORED"] = "18"
        else:
            optimized["ML_MAX_MEMORY_USAGE"] = "8192"  # 8GB pour les systèmes > 16GB RAM
            optimized["MAX_PAIRS_MONITORED"] = "30"
        
        # Limiter l'historique des transactions
        if ram_gb < 8:
            optimized["MAX_TRANSACTION_HISTORY"] = "5000"
        elif ram_gb < 16:
            optimized["MAX_TRANSACTION_HISTORY"] = "10000"
        else:
            optimized["MAX_TRANSACTION_HISTORY"] = "20000"
    
    # GPU
    has_gpu = hardware_info.get("has_gpu", False)
    gpu_memory_gb = hardware_info.get("gpu_memory_gb", 0)
    
    if has_gpu:
        optimized["ML_USE_GPU"] = "true"
        
        # Optimiser la taille de batch pour le ML
        if gpu_memory_gb > 0:
            if gpu_memory_gb < 4:
                optimized["ML_BATCH_SIZE"] = "16"
            elif gpu_memory_gb < 8:
                optimized["ML_BATCH_SIZE"] = "32"
            else:
                optimized["ML_BATCH_SIZE"] = "64"
    else:
        optimized["ML_USE_GPU"] = "false"
    
    # Optimisations générales
    optimized["LOG_MAX_SIZE"] = "50"
    optimized["LOG_BACKUP_COUNT"] = "5"
    optimized["MEMORY_MONITORING"] = "true"
    optimized["USE_WEBSOCKETS"] = "true"
    
    return optimized

def memory_warning_callback(current_usage: int, limit: int) -> None:
    """
    Callback appelé lorsque l'utilisation mémoire dépasse la limite
    
    Args:
        current_usage: Utilisation mémoire actuelle (octets)
        limit: Limite mémoire (octets)
    """
    logger.warning(f"Alerte mémoire: {current_usage / (1024 * 1024):.2f}MB / {limit / (1024 * 1024):.2f}MB")
    
    # Tentative de libération de mémoire
    import gc
    gc.collect()
    
    # Log de l'utilisation mémoire détaillée
    try:
        import psutil
        process = psutil.Process(os.getpid())
        
        logger.warning(f"Détails mémoire: RSS={process.memory_info().rss / (1024*1024):.2f}MB, "
                     f"VMS={process.memory_info().vms / (1024*1024):.2f}MB")
        
        # Afficher les variables utilisant le plus de mémoire (si possible)
        try:
            import objgraph
            
            logger.warning("Top 10 des types d'objets utilisant le plus de mémoire:")
            for obj, count in objgraph.most_common_types(10):
                logger.warning(f"  {obj}: {count} instances")
        except ImportError:
            pass
            
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse mémoire détaillée: {str(e)}")

def install_missing_dependencies(hardware_info: Dict) -> None:
    """
    Installe les dépendances manquantes nécessaires aux optimisations
    
    Args:
        hardware_info: Informations sur le matériel
    """
    try:
        import subprocess
        
        # Liste des dépendances à vérifier
        dependencies = ["psutil"]
        
        # Ajouter PyTorch si GPU détecté
        if hardware_info.get("has_gpu", False):
            if "NVIDIA" in hardware_info.get("gpu_name", ""):
                dependencies.append("torch")
                dependencies.append("torchvision")
        
        # Dépendances optionnelles pour le debugging mémoire
        if os.environ.get("DEBUG_MEMORY", "false").lower() == "true":
            dependencies.append("objgraph")
        
        # Installer les dépendances manquantes
        for dep in dependencies:
            try:
                __import__(dep)
                logger.debug(f"Dépendance {dep} déjà installée")
            except ImportError:
                logger.info(f"Installation de la dépendance manquante: {dep}")
                subprocess.check_call([sys.executable, "-m", "pip", "install", dep])
                
    except Exception as e:
        logger.error(f"Erreur lors de l'installation des dépendances: {str(e)}")

def get_optimization_status() -> Dict:
    """
    Récupère l'état des optimisations
    
    Returns:
        Dict: État des optimisations
    """
    status = {
        "optimized": optimization_applied,
        "hardware": hardware_info,
    }
    
    # Récupérer l'utilisation mémoire actuelle
    try:
        import psutil
        process = psutil.Process(os.getpid())
        
        status["memory_usage"] = {
            "rss_mb": process.memory_info().rss / (1024 * 1024),
            "vms_mb": process.memory_info().vms / (1024 * 1024),
            "percent": process.memory_percent()
        }
    except Exception:
        status["memory_usage"] = "Not available"
    
    # Récupérer l'utilisation du GPU si disponible
    if hardware_info and hardware_info.get("has_gpu", False):
        try:
            import torch
            if torch.cuda.is_available():
                status["gpu_usage"] = {
                    "allocated_mb": torch.cuda.memory_allocated() / (1024 * 1024),
                    "cached_mb": torch.cuda.memory_reserved() / (1024 * 1024),
                    "device": torch.cuda.get_device_name(0)
                }
        except Exception:
            status["gpu_usage"] = "Not available"
    
    return status

# Si ce script est exécuté directement, afficher les infos matérielles
if __name__ == "__main__":
    print("GBPBot Optimizer")
    print("================")
    
    hardware = get_hardware_info()
    print(f"Configuration matérielle détectée:")
    for key, value in hardware.items():
        print(f"- {key}: {value}")
    
    print("\nOptimisations recommandées:")
    optimized_config = optimize_config_for_hardware({}, hardware)
    for key, value in optimized_config.items():
        print(f"- {key}={value}")