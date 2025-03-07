#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GBPBot - Vérification du Système
================================

Ce script vérifie la configuration du système pour s'assurer que toutes les 
dépendances et connexions nécessaires sont disponibles pour GBPBot.
"""

import os
import sys
import platform
import logging
import importlib
import subprocess
import requests
import time
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

# Ajouter le répertoire racine au path
script_dir = Path(__file__).parent
root_dir = script_dir.parent
sys.path.insert(0, str(root_dir))

# Définir les caractères de statut selon le système d'exploitation
if platform.system() == "Windows":
    STATUS_SUCCESS = "OK"
    STATUS_ERROR = "ECHEC"
    STATUS_WARNING = "ATTENTION"
else:
    STATUS_SUCCESS = "✅ OK"
    STATUS_ERROR = "❌ ÉCHEC"
    STATUS_WARNING = "⚠️ ATTENTION"

# Configuration du logging
log_dir = root_dir / "logs"
log_dir.mkdir(exist_ok=True)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = log_dir / f"system_check_{timestamp}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("system_check")

# Essayer de charger les variables d'environnement
try:
    from dotenv import load_dotenv
    load_dotenv()
    logger.info("Variables d'environnement chargées depuis .env")
except ImportError:
    logger.warning("Module python-dotenv non trouvé. Les variables d'environnement ne seront pas chargées depuis .env.")
except Exception as e:
    logger.warning(f"Erreur lors du chargement des variables d'environnement: {e}")

def print_header():
    """Affiche l'en-tête du vérificateur de système"""
    print("\n============================================================")
    print("               GBPBot - Vérification Système")
    print("============================================================\n")

def check_python_version():
    """Vérifie que la version de Python est compatible"""
    logger.info("\n--- Vérification: Version Python ---\n")
    print("--- Vérification: Version Python ---")
    
    current_version = platform.python_version()
    major, minor, patch = map(int, current_version.split("."))
    
    if major >= 3 and minor >= 9:
        status = STATUS_SUCCESS
        logger.info(f"Version Python: {status} ({current_version})")
        return True
    else:
        status = STATUS_ERROR + " (Critique)"
        logger.error(f"Version Python: {status} ({current_version})")
        logger.error("Python 3.9+ est requis pour GBPBot.")
        return False

def check_dependency(module_name):
    """Vérifie si un module Python est installé"""
    try:
        importlib.import_module(module_name)
        return True
    except ImportError:
        return False

def check_critical_dependencies():
    """Vérifie les dépendances Python critiques"""
    logger.info("\n--- Vérification: Dépendances critiques ---\n")
    print("\n--- Vérification: Dépendances critiques ---")
    
    critical_dependencies = [
        "python-dotenv",
        "requests",
        "asyncio",
        "websockets",
        "logging",
        "json",
        "pandas",
        "numpy",
        "base58",
        "cryptography"
    ]
    
    missing = []
    
    for dep in critical_dependencies:
        if not check_dependency(dep):
            missing.append(dep)
            
    if missing:
        status = STATUS_ERROR + " (Critique)"
        logger.error(f"Dépendances manquantes: {', '.join(missing)}")
        logger.info("Exécutez: pip install -r requirements.txt")
        logger.error(f"Dépendances critiques: {status}")
        return False
    else:
        status = STATUS_SUCCESS
        logger.info(f"Toutes les dépendances critiques sont installées.")
        logger.info(f"Dépendances critiques: {status}")
        return True

def check_optional_dependencies():
    """Vérifie les dépendances Python optionnelles"""
    logger.info("\n--- Vérification: Dépendances optionnelles ---\n")
    print("\n--- Vérification: Dépendances optionnelles ---")
    
    optional_dependencies = [
        "fastapi",
        "uvicorn",
        "python-telegram-bot",
        "sklearn",
        "matplotlib",
        "seaborn"
    ]
    
    missing = []
    
    for dep in optional_dependencies:
        if not check_dependency(dep):
            missing.append(dep)
            
    if missing:
        status = STATUS_WARNING
        logger.warning(f"Dépendances optionnelles manquantes: {', '.join(missing)}")
        logger.warning("Certaines fonctionnalités pourraient ne pas être disponibles.")
        logger.warning(f"Dépendances optionnelles: {status}")
        return False
    else:
        status = STATUS_SUCCESS
        logger.info(f"Toutes les dépendances optionnelles sont installées.")
        logger.info(f"Dépendances optionnelles: {status}")
        return True

def check_gpu_capabilities():
    """Vérifie les capacités GPU pour TensorFlow et PyTorch"""
    logger.info("\n--- Vérification: Capacités GPU ---\n")
    print("\n--- Vérification: Capacités GPU ---")
    
    gpu_info = {
        "tensorflow_gpu": False,
        "pytorch_gpu": False,
        "cuda_available": False,
        "cuda_version": None,
        "gpu_info": []
    }
    
    # Vérifier CUDA avec subprocess pour éviter les imports
    try:
        nvcc_output = subprocess.check_output(["nvcc", "--version"], universal_newlines=True)
        gpu_info["cuda_available"] = True
        # Extraire la version CUDA
        for line in nvcc_output.split("\n"):
            if "release" in line.lower():
                gpu_info["cuda_version"] = line.strip()
                break
    except (subprocess.CalledProcessError, FileNotFoundError):
        gpu_info["cuda_available"] = False
    
    # Vérifier les capacités GPU pour TensorFlow sans importer directement
    try:
        # Utiliser subprocess pour éviter d'importer tensorflow
        tf_output = subprocess.check_output(
            [sys.executable, "-c", "import tensorflow as tf; print(tf.config.list_physical_devices('GPU'))"],
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        if "[]" not in tf_output:
            gpu_info["tensorflow_gpu"] = True
            gpu_info["gpu_info"].append("TensorFlow GPU disponible")
            
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    
    # Vérifier les capacités GPU pour PyTorch sans importer directement
    try:
        # Utiliser subprocess pour éviter d'importer torch
        torch_output = subprocess.check_output(
            [sys.executable, "-c", "import torch; print(torch.cuda.is_available())"],
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        if "True" in torch_output:
            gpu_info["pytorch_gpu"] = True
            gpu_info["gpu_info"].append("PyTorch CUDA disponible")
            
            # Obtenir plus d'informations sur le GPU
            torch_gpu_output = subprocess.check_output(
                [sys.executable, "-c", "import torch; print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A')"],
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            if "N/A" not in torch_gpu_output:
                gpu_info["gpu_info"].append(f"GPU: {torch_gpu_output.strip()}")
            
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    
    # Évaluer les résultats
    if gpu_info["tensorflow_gpu"] or gpu_info["pytorch_gpu"]:
        status = STATUS_SUCCESS
        logger.info(f"Support GPU détecté:")
        for info in gpu_info["gpu_info"]:
            logger.info(f"- {info}")
        logger.info(f"Capacités GPU: {status}")
    else:
        status = STATUS_WARNING
        logger.warning("Aucun support GPU n'a été détecté pour TensorFlow ou PyTorch.")
        logger.warning("L'IA fonctionnera sur CPU, ce qui peut être plus lent.")
        logger.warning(f"Capacités GPU: {status}")
    
    return gpu_info["tensorflow_gpu"] or gpu_info["pytorch_gpu"], gpu_info

def check_rpc_connection(url, blockchain, method=None):
    """Vérifie la connexion à un nœud RPC"""
    if not url:
        return False, f"URL RPC {blockchain} non définie"
        
    if method is None:
        if blockchain.lower() == "solana":
            method = "getHealth"
        else:
            method = "eth_blockNumber"
    
    try:
        response = requests.post(
            url,
            json={"jsonrpc": "2.0", "method": method, "params": [], "id": 1},
            timeout=10
        )
        result = response.json()
        if "result" in result:
            return True, f"Connexion RPC {blockchain} OK"
        return False, f"Erreur RPC {blockchain}: {result.get('error', 'Réponse invalide')}"
    except Exception as e:
        return False, f"Erreur de connexion RPC {blockchain}: {str(e)}"

def check_blockchain_connections():
    """Vérifie les connexions blockchain"""
    connections = []
    
    # Vérifier Solana
    solana_rpc = os.getenv("SOLANA_RPC_URL")
    if solana_rpc:
        connections.append(("Solana", solana_rpc, "getHealth"))
    
    # Vérifier Avalanche
    avax_rpc = os.getenv("AVAX_RPC_URL")
    if avax_rpc:
        connections.append(("Avalanche", avax_rpc, "eth_blockNumber"))
    
    # Vérifier Sonic
    sonic_rpc = os.getenv("SONIC_RPC_URL")
    if sonic_rpc:
        connections.append(("Sonic", sonic_rpc, "eth_blockNumber"))
    
    results = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(check_rpc_connection, url, blockchain, method): (blockchain, url) 
                  for blockchain, url, method in connections}
        for future in futures:
            blockchain, url = futures[future]
            success, message = future.result()
            results.append((blockchain, url, success, message))
    
    all_success = all(success for _, _, success, _ in results)
    
    for blockchain, url, success, message in results:
        if success:
            logger.info(message)
        else:
            logger.error(message)
    
    return all_success, results

def check_storage_permissions():
    """Vérifie les permissions d'écriture dans les dossiers critiques"""
    directories = ["logs", "data", "config"]
    results = {}
    all_success = True
    
    for directory in directories:
        dir_path = Path(root_dir) / directory
        dir_path.mkdir(exist_ok=True)
        test_file = dir_path / "permission_test.tmp"
        try:
            with open(test_file, "w") as f:
                f.write("test")
            test_file.unlink()  # Supprimer le fichier de test
            logger.info(f"Permissions d'écriture OK pour: {directory}/")
            results[directory] = True
        except (IOError, PermissionError) as e:
            logger.error(f"Erreur de permission d'écriture pour: {directory}/ - {e}")
            results[directory] = False
            all_success = False
    
    return all_success, results

def check_environment():
    """Vérifie l'environnement complet du système"""
    logger.info("=== VÉRIFICATION DU SYSTÈME GBPBOT ===")
    print_header()
    
    # Liste des vérifications avec leur criticité
    checks = [
        ("Version Python", check_python_version, True),
        ("Dépendances critiques", check_critical_dependencies, True),
        ("Dépendances optionnelles", check_optional_dependencies, False),
        ("Connexions Blockchain", check_blockchain_connections, False),
        ("Permissions de stockage", check_storage_permissions, True),
        ("Capacités GPU", check_gpu_capabilities, False)
    ]
    
    success = True
    results = {}
    
    for name, check_func, critical in checks:
        logger.info(f"\n--- Vérification: {name} ---")
        print(f"\n--- Vérification: {name} ---")
        
        start_time = time.time()
        check_success, check_results = check_func() if "check_results" in locals() else (check_func(), None)
        elapsed = time.time() - start_time
        
        results[name.lower().replace(" ", "_")] = {
            "success": check_success,
            "critical": critical,
            "details": check_results,
            "time": elapsed
        }
        
        if check_success:
            status = STATUS_SUCCESS
            logger.info(f"{name}: {status} ({elapsed:.2f}s)")
            print(f"{name}: {status} ({elapsed:.2f}s)")
        else:
            if critical:
                status = STATUS_ERROR + " (Critique)"
                success = False
                logger.error(f"{name}: {status} ({elapsed:.2f}s)")
                print(f"{name}: {status} ({elapsed:.2f}s)")
            else:
                status = STATUS_WARNING
                logger.warning(f"{name}: {status} ({elapsed:.2f}s)")
                print(f"{name}: {status} ({elapsed:.2f}s)")
    
    # Vérifier l'existence des variables d'environnement critiques
    env_vars = [
        ("SOLANA_RPC_URL", True),
        ("SOLANA_PRIVATE_KEY", True),
        ("PRIVATE_KEY", True),  # Clé Avalanche
        ("AVAX_RPC_URL", True),
        ("TELEGRAM_BOT_TOKEN", False),
        ("TELEGRAM_ALLOWED_USERS", False),
        ("OPENAI_API_KEY", False)
    ]
    
    env_results = {}
    env_check_success = True
    
    print("\n--- Vérification des variables d'environnement ---")
    logger.info("\n--- Vérification des variables d'environnement ---")
    
    for var_name, critical in env_vars:
        var_value = os.getenv(var_name)
        is_set = var_value is not None and var_value.strip() != ""
        
        env_results[var_name] = {"set": is_set, "critical": critical}
        
        if is_set:
            logger.info(f"Variable {var_name}: ✅ Définie")
            print(f"Variable {var_name}: ✅ Définie")
        else:
            if critical:
                logger.error(f"Variable {var_name}: ❌ Non définie (Critique)")
                print(f"Variable {var_name}: ❌ Non définie (Critique)")
                env_check_success = False
                success = False
            else:
                logger.warning(f"Variable {var_name}: ⚠️ Non définie (Non critique)")
                print(f"Variable {var_name}: ⚠️ Non définie (Non critique)")
    
    results["environment_variables"] = {
        "success": env_check_success,
        "critical": True,
        "details": env_results
    }
    
    # Sauvegarder les résultats
    results_file = log_dir / f"system_check_results_{timestamp}.json"
    try:
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2)
        logger.info(f"Résultats sauvegardés dans {results_file}")
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde des résultats: {e}")
    
    # Afficher le résumé
    print("\n" + "="*60)
    logger.info("\n=== RÉSUMÉ DE LA VÉRIFICATION ===")
    print("=== RÉSUMÉ DE LA VÉRIFICATION ===")
    
    if success:
        logger.info("✅ Toutes les vérifications critiques sont passées.")
        print("✅ Toutes les vérifications critiques sont passées.")
    else:
        logger.error("❌ Certaines vérifications critiques ont échoué.")
        print("❌ Certaines vérifications critiques ont échoué.")
    
    print(f"\nLog détaillé disponible dans: {log_file}")
    print(f"Résultats JSON disponibles dans: {results_file}")
    print("\n" + "="*60)
    
    return success

if __name__ == "__main__":
    try:
        os.makedirs("logs", exist_ok=True)
        success = check_environment()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("Vérification annulée par l'utilisateur.")
        print("\nVérification annulée par l'utilisateur.")
        sys.exit(130)
    except Exception as e:
        logger.exception(f"Erreur fatale lors de la vérification: {e}")
        print(f"\nErreur fatale lors de la vérification: {e}")
        sys.exit(1) 