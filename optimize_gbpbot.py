#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GBPBot Optimizer

Ce script implémente des optimisations de performance pour GBPBot,
adaptées à la configuration matérielle de l'utilisateur.

Il applique:
1. Optimisations de mémoire pour les collections et caches
2. Optimisations des connexions RPC
3. Optimisations pour le module de Machine Learning
4. Surveillance des ressources système
"""

import os
import sys
import logging
import json
import psutil
import time
from pathlib import Path
from typing import Dict, Any, List, Set, Optional
import importlib
import gc
from decimal import Decimal

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("optimization.log")
    ]
)
logger = logging.getLogger("GBPBot-Optimizer")

# Constantes
DEFAULT_MAX_TRANSACTION_HISTORY = 5000
DEFAULT_MAX_TOKEN_CACHE_SIZE = 1000
DEFAULT_MAX_BLACKLIST_SIZE = 5000
DEFAULT_MAX_CACHED_OPPORTUNITIES = 3000

DEFAULT_RPC_CONNECTION_LIMIT = 20
DEFAULT_RPC_MAX_CONNECTIONS_PER_HOST = 5
DEFAULT_RPC_SESSION_REFRESH_INTERVAL = 3600  # secondes

DEFAULT_ML_MAX_MEMORY_USAGE = 4096  # Mo
DEFAULT_ML_MAX_MODEL_SIZE = 512  # Mo
DEFAULT_ML_BATCH_SIZE = 64
DEFAULT_ML_GPU_ACCELERATION = "auto"
DEFAULT_ML_MAX_GPU_MEMORY_MB = 2048  # Mo

# Chemins des fichiers
ENV_FILE = ".env"
OPTIMIZED_ENV_FILE = ".env.optimized"

class SystemMonitor:
    """Surveille les ressources système et fournit des recommandations."""
    
    def __init__(self):
        self.cpu_count = psutil.cpu_count(logical=True)
        self.memory_total = psutil.virtual_memory().total
        self.gpu_info = self._get_gpu_info()
        
    def _get_gpu_info(self) -> Dict[str, Any]:
        """Récupère les informations sur le GPU si disponible."""
        gpu_info = {
            "available": False,
            "name": "Unknown",
            "memory": 0,
            "cuda_available": False
        }
        
        try:
            # Essayer d'importer torch pour vérifier CUDA
            import torch
            gpu_info["cuda_available"] = torch.cuda.is_available()
            if gpu_info["cuda_available"]:
                gpu_info["available"] = True
                gpu_info["name"] = torch.cuda.get_device_name(0)
                gpu_info["memory"] = torch.cuda.get_device_properties(0).total_memory
        except (ImportError, Exception):
            # Si torch n'est pas disponible, essayer avec nvidia-smi
            try:
                import subprocess
                result = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total', '--format=csv,noheader,nounits'], 
                                        stdout=subprocess.PIPE, text=True)
                if result.returncode == 0:
                    output = result.stdout.strip().split(',')
                    gpu_info["available"] = True
                    gpu_info["name"] = output[0].strip()
                    gpu_info["memory"] = int(output[1].strip()) * 1024 * 1024  # Convertir en octets
            except Exception:
                pass
        
        return gpu_info
    
    def get_system_info(self) -> Dict[str, Any]:
        """Récupère les informations système actuelles."""
        return {
            "cpu": {
                "count": self.cpu_count,
                "usage_percent": psutil.cpu_percent(interval=1)
            },
            "memory": {
                "total": self.memory_total,
                "available": psutil.virtual_memory().available,
                "percent_used": psutil.virtual_memory().percent
            },
            "gpu": self.gpu_info,
            "disk": {
                "total": psutil.disk_usage('/').total,
                "free": psutil.disk_usage('/').free,
                "percent_used": psutil.disk_usage('/').percent
            }
        }
    
    def get_optimization_recommendations(self) -> Dict[str, Any]:
        """Génère des recommandations d'optimisation basées sur le système."""
        system_info = self.get_system_info()
        
        # Calculer les recommandations
        memory_gb = system_info["memory"]["total"] / (1024 ** 3)
        
        recommendations = {
            "MAX_TRANSACTION_HISTORY": min(10000, int(memory_gb * 1000)),
            "MAX_TOKEN_CACHE_SIZE": min(2000, int(memory_gb * 200)),
            "MAX_BLACKLIST_SIZE": min(10000, int(memory_gb * 1000)),
            "MAX_CACHED_OPPORTUNITIES": min(5000, int(memory_gb * 500)),
            
            "RPC_CONNECTION_LIMIT": min(50, max(10, self.cpu_count * 3)),
            "RPC_MAX_CONNECTIONS_PER_HOST": min(10, max(3, self.cpu_count)),
            "RPC_SESSION_REFRESH_INTERVAL": 3600,
            
            "ML_MAX_MEMORY_USAGE": int(memory_gb * 256),  # Mo
            "ML_MAX_MODEL_SIZE": int(min(1024, memory_gb * 64)),  # Mo
            "ML_BATCH_SIZE": 32 if memory_gb < 8 else 64 if memory_gb < 16 else 128,
            "ML_GPU_ACCELERATION": "disable" if not system_info["gpu"]["available"] else "auto",
            "ML_MAX_GPU_MEMORY_MB": 0 if not system_info["gpu"]["available"] else int(system_info["gpu"]["memory"] / (1024 * 1024) * 0.8)
        }
        
        return recommendations

class EnvManager:
    """Gère les fichiers .env pour les optimisations."""
    
    def __init__(self, env_file: str = ENV_FILE):
        self.env_file = env_file
        self.env_vars = self._load_env()
    
    def _load_env(self) -> Dict[str, str]:
        """Charge les variables d'environnement depuis le fichier .env."""
        env_vars = {}
        
        if os.path.exists(self.env_file):
            with open(self.env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    if '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()
        
        return env_vars
    
    def update_env(self, new_vars: Dict[str, Any]) -> None:
        """Met à jour les variables d'environnement."""
        self.env_vars.update({k: str(v) for k, v in new_vars.items()})
    
    def save_env(self, output_file: str = None) -> None:
        """Sauvegarde les variables d'environnement dans un fichier."""
        if output_file is None:
            output_file = self.env_file
        
        # Lire le fichier existant pour préserver les commentaires
        lines = []
        if os.path.exists(self.env_file):
            with open(self.env_file, 'r') as f:
                lines = f.readlines()
        
        # Mettre à jour les valeurs existantes et ajouter les nouvelles
        updated_keys = set()
        for i, line in enumerate(lines):
            if '=' in line and not line.strip().startswith('#'):
                key = line.split('=', 1)[0].strip()
                if key in self.env_vars:
                    lines[i] = f"{key}={self.env_vars[key]}\n"
                    updated_keys.add(key)
        
        # Ajouter les nouvelles variables
        new_vars = []
        for key, value in self.env_vars.items():
            if key not in updated_keys:
                new_vars.append(f"{key}={value}\n")
        
        if new_vars:
            # Ajouter une section pour les optimisations si elle n'existe pas
            if not any("OPTIMISATIONS DE PERFORMANCE" in line for line in lines):
                new_vars.insert(0, "\n#######################\n# OPTIMISATIONS DE PERFORMANCE\n#######################\n\n")
            
            lines.extend(new_vars)
        
        # Écrire le fichier mis à jour
        with open(output_file, 'w') as f:
            f.writelines(lines)
        
        logger.info(f"Fichier d'environnement sauvegardé: {output_file}")

class GBPBotOptimizer:
    """Optimise les performances de GBPBot."""
    
    def __init__(self):
        self.system_monitor = SystemMonitor()
        self.env_manager = EnvManager()
        
    def apply_memory_optimizations(self) -> None:
        """Applique les optimisations de mémoire."""
        recommendations = self.system_monitor.get_optimization_recommendations()
        
        # Mettre à jour les variables d'environnement
        optimization_vars = {
            "MAX_TRANSACTION_HISTORY": recommendations["MAX_TRANSACTION_HISTORY"],
            "MAX_TOKEN_CACHE_SIZE": recommendations["MAX_TOKEN_CACHE_SIZE"],
            "MAX_BLACKLIST_SIZE": recommendations["MAX_BLACKLIST_SIZE"],
            "MAX_CACHED_OPPORTUNITIES": recommendations["MAX_CACHED_OPPORTUNITIES"],
        }
        
        self.env_manager.update_env(optimization_vars)
        logger.info(f"Optimisations de mémoire appliquées: {optimization_vars}")
    
    def apply_rpc_optimizations(self) -> None:
        """Applique les optimisations de connexions RPC."""
        recommendations = self.system_monitor.get_optimization_recommendations()
        
        # Mettre à jour les variables d'environnement
        optimization_vars = {
            "RPC_CONNECTION_LIMIT": recommendations["RPC_CONNECTION_LIMIT"],
            "RPC_MAX_CONNECTIONS_PER_HOST": recommendations["RPC_MAX_CONNECTIONS_PER_HOST"],
            "RPC_SESSION_REFRESH_INTERVAL": recommendations["RPC_SESSION_REFRESH_INTERVAL"],
        }
        
        self.env_manager.update_env(optimization_vars)
        logger.info(f"Optimisations RPC appliquées: {optimization_vars}")
    
    def apply_ml_optimizations(self) -> None:
        """Applique les optimisations pour le machine learning."""
        recommendations = self.system_monitor.get_optimization_recommendations()
        
        # Mettre à jour les variables d'environnement
        optimization_vars = {
            "ML_MAX_MEMORY_USAGE": recommendations["ML_MAX_MEMORY_USAGE"],
            "ML_MAX_MODEL_SIZE": recommendations["ML_MAX_MODEL_SIZE"],
            "ML_BATCH_SIZE": recommendations["ML_BATCH_SIZE"],
            "ML_GPU_ACCELERATION": recommendations["ML_GPU_ACCELERATION"],
            "ML_MAX_GPU_MEMORY_MB": recommendations["ML_MAX_GPU_MEMORY_MB"],
        }
        
        self.env_manager.update_env(optimization_vars)
        logger.info(f"Optimisations ML appliquées: {optimization_vars}")
    
    def optimize_code_files(self) -> None:
        """Optimise les fichiers de code pour limiter l'utilisation de la mémoire."""
        # Optimiser le fichier cross_dex_arbitrage.py
        try:
            self._optimize_cross_dex_arbitrage()
            logger.info("Optimisation du fichier cross_dex_arbitrage.py réussie")
        except Exception as e:
            logger.error(f"Erreur lors de l'optimisation de cross_dex_arbitrage.py: {e}")
        
        # Optimiser le fichier solana_memecoin_sniper.py
        try:
            self._optimize_solana_memecoin_sniper()
            logger.info("Optimisation du fichier solana_memecoin_sniper.py réussie")
        except Exception as e:
            logger.error(f"Erreur lors de l'optimisation de solana_memecoin_sniper.py: {e}")
    
    def _optimize_cross_dex_arbitrage(self) -> None:
        """Optimise le fichier cross_dex_arbitrage.py."""
        file_path = "gbpbot/strategies/cross_dex_arbitrage.py"
        
        if not os.path.exists(file_path):
            logger.warning(f"Fichier {file_path} non trouvé")
            return
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Ajouter l'import de Decimal s'il n'existe pas
        if "from decimal import Decimal" not in content:
            content = content.replace("import random", "import random\nfrom decimal import Decimal")
        
        # Ajouter la configuration de max_known_opportunities
        if "self.max_known_opportunities" not in content:
            content = content.replace(
                "self.known_opportunities = set()",
                "self.max_known_opportunities = int(os.environ.get('MAX_CACHED_OPPORTUNITIES', 5000))\n        self.known_opportunities = set()"
            )
        
        # Optimiser la gestion de known_opportunities
        if "if len(self.known_opportunities) > 10000:" in content:
            content = content.replace(
                "if len(self.known_opportunities) > 10000:",
                "if len(self.known_opportunities) > self.max_known_opportunities:"
            )
            content = content.replace(
                "self.known_opportunities = set(list(self.known_opportunities)[-5000:])",
                "self.known_opportunities = set(list(self.known_opportunities)[-(self.max_known_opportunities // 2):])"
            )
        
        # Utiliser Decimal pour les calculs financiers
        if "'total_profit': 0," in content:
            content = content.replace(
                "'total_profit': 0,",
                "'total_profit': Decimal('0'),"
            )
        
        if "'total_loss': 0," in content:
            content = content.replace(
                "'total_loss': 0,",
                "'total_loss': Decimal('0'),"
            )
        
        with open(file_path, 'w') as f:
            f.write(content)
    
    def _optimize_solana_memecoin_sniper(self) -> None:
        """Optimise le fichier solana_memecoin_sniper.py."""
        file_path = "gbpbot/sniping/solana_memecoin_sniper.py"
        
        if not os.path.exists(file_path):
            logger.warning(f"Fichier {file_path} non trouvé")
            return
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Ajouter les variables de configuration pour les limites de cache
        if "self.max_token_cache_size" not in content:
            content = content.replace(
                "self.token_info_cache = {}",
                "self.max_token_cache_size = int(os.environ.get('MAX_TOKEN_CACHE_SIZE', 1000))\n        self.token_info_cache = {}"
            )
        
        # Ajouter la limite pour blacklisted_tokens
        if "self.max_blacklist_size" not in content:
            content = content.replace(
                "self.blacklisted_tokens = set(os.environ.get('BLACKLISTED_TOKENS', '').split(','))",
                "self.max_blacklist_size = int(os.environ.get('MAX_BLACKLIST_SIZE', 5000))\n        self.blacklisted_tokens = set(os.environ.get('BLACKLISTED_TOKENS', '').split(','))"
            )
        
        # Ajouter la logique de nettoyage du cache de tokens
        if "def _clean_token_cache(self)" not in content:
            cache_cleaning_code = """
    def _clean_token_cache(self):
        \"\"\"Nettoie le cache de tokens si nécessaire.\"\"\"
        if len(self.token_info_cache) > self.max_token_cache_size:
            # Supprimer 20% des entrées les plus anciennes
            items_to_remove = int(self.max_token_cache_size * 0.2)
            oldest_keys = list(self.token_info_cache.keys())[:items_to_remove]
            for key in oldest_keys:
                del self.token_info_cache[key]
            self.logger.info(f"Nettoyage du cache de tokens: {items_to_remove} entrées supprimées")
    
    def _manage_blacklist_size(self):
        \"\"\"Gère la taille de la liste noire de tokens.\"\"\"
        if len(self.blacklisted_tokens) > self.max_blacklist_size:
            # Conserver uniquement les entrées les plus récentes
            self.blacklisted_tokens = set(list(self.blacklisted_tokens)[-(self.max_blacklist_size // 2):])
            self.logger.info(f"Nettoyage de la liste noire: réduite à {len(self.blacklisted_tokens)} tokens")
"""
            # Trouver un bon endroit pour insérer le code
            if "def __init__" in content:
                parts = content.split("def __init__")
                insertion_point = parts[0].rfind("\n\n")
                if insertion_point != -1:
                    content = content[:insertion_point] + cache_cleaning_code + content[insertion_point:]
        
        # Ajouter les appels aux fonctions de nettoyage
        if "self._clean_token_cache()" not in content:
            # Chercher des méthodes où ajouter l'appel
            methods_to_modify = ["get_token_info", "analyze_token", "snipe_token"]
            
            for method in methods_to_modify:
                if f"def {method}" in content:
                    method_start = content.find(f"def {method}")
                    method_end = content.find("def ", method_start + 1)
                    if method_end == -1:
                        method_end = len(content)
                    
                    method_content = content[method_start:method_end]
                    
                    # Trouver la fin de la méthode pour ajouter l'appel
                    lines = method_content.split("\n")
                    indentation = None
                    
                    for i, line in enumerate(lines):
                        if line.strip().startswith("def "):
                            # Trouver l'indentation
                            for j in range(i+1, len(lines)):
                                if lines[j].strip() and not lines[j].strip().startswith("#"):
                                    indentation = lines[j][:lines[j].find(lines[j].strip())]
                                    break
                    
                    if indentation is not None:
                        # Ajouter l'appel à la fin de la méthode
                        clean_call = f"\n{indentation}self._clean_token_cache()"
                        if method == "snipe_token":
                            clean_call += f"\n{indentation}self._manage_blacklist_size()"
                        
                        modified_method = method_content + clean_call
                        content = content.replace(method_content, modified_method)
        
        with open(file_path, 'w') as f:
            f.write(content)
    
    def run(self) -> None:
        """Exécute toutes les optimisations."""
        logger.info("Démarrage de l'optimisation de GBPBot...")
        
        # Afficher les informations système
        system_info = self.system_monitor.get_system_info()
        logger.info(f"Informations système: {json.dumps(system_info, indent=2, default=str)}")
        
        # Appliquer les optimisations
        self.apply_memory_optimizations()
        self.apply_rpc_optimizations()
        self.apply_ml_optimizations()
        
        # Optimiser les fichiers de code
        self.optimize_code_files()
        
        # Sauvegarder les optimisations
        self.env_manager.save_env(OPTIMIZED_ENV_FILE)
        
        logger.info(f"Optimisations terminées. Fichier de configuration optimisé: {OPTIMIZED_ENV_FILE}")
        logger.info("Pour appliquer ces optimisations, copiez le contenu de ce fichier dans votre .env principal")

if __name__ == "__main__":
    try:
        optimizer = GBPBotOptimizer()
        optimizer.run()
    except Exception as e:
        logger.error(f"Erreur lors de l'optimisation: {e}", exc_info=True)
        sys.exit(1) 