"""
Module d'optimisation matérielle pour GBPBot
============================================

Ce module fournit des fonctionnalités pour optimiser les performances
du GBPBot en fonction du matériel spécifique de l'utilisateur.
Il s'adapte aux capacités du CPU, GPU, RAM et stockage pour 
maximiser l'efficacité tout en minimisant la consommation de ressources.

Optimisations principales:
- CPU: Adapte le nombre de threads et la priorité des processus
- GPU: Configure l'utilisation optimale du GPU pour les modèles d'IA
- RAM: Gère efficacement l'utilisation de la mémoire
- Disque: Optimise les opérations d'I/O et la mise en cache
"""

import os
import sys
import logging
import platform
import threading
import multiprocessing
import psutil
import json
import time
from typing import Dict, List, Tuple, Optional, Any, Union
from pathlib import Path

# Imports conditionnels pour les fonctionnalités liées au GPU
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

try:
    import tensorflow as tf
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

# Configuration du logger
logger = logging.getLogger("gbpbot.core.optimization.hardware_optimizer")

class HardwareOptimizer:
    """
    Classe principale pour l'optimisation matérielle du GBPBot.
    
    Cette classe détecte les spécifications matérielles et applique
    des optimisations adaptées pour maximiser les performances
    tout en minimisant l'utilisation des ressources.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialise l'optimiseur matériel.
        
        Args:
            config: Configuration optionnelle. Si None, utilise la détection automatique.
        """
        self.config = config or {}
        
        # Informations matérielles détectées
        self.hardware_info = self._detect_hardware()
        
        # Paramètres d'optimisation
        self.optimization_params = self._generate_optimization_params()
        
        # État actuel des optimisations
        self.active_optimizations = {
            "cpu": False,
            "gpu": False,
            "memory": False,
            "disk": False,
            "network": False
        }
        
        # Suivi des performances
        self.performance_metrics = {
            "cpu_usage": [],
            "memory_usage": [],
            "gpu_usage": [],
            "disk_io": [],
            "network_io": []
        }
        
        # Intervalle d'échantillonnage pour la surveillance des performances (en secondes)
        self.monitoring_interval = 5.0
        
        # Thread de surveillance
        self.monitoring_thread = None
        self.monitoring_active = False
        
        logger.info(f"HardwareOptimizer initialisé: {self.hardware_info['summary']}")
    
    def _detect_hardware(self) -> Dict[str, Any]:
        """
        Détecte les spécifications matérielles du système.
        
        Returns:
            Dict contenant les informations matérielles détectées.
        """
        hw_info = {
            "platform": platform.platform(),
            "cpu": {
                "model": platform.processor(),
                "cores_physical": psutil.cpu_count(logical=False) or 1,
                "cores_logical": psutil.cpu_count(logical=True) or 2,
                "frequency": psutil.cpu_freq().max if psutil.cpu_freq() else 0,
                "is_i5_12400f": "i5-12400F" in platform.processor()
            },
            "memory": {
                "total": psutil.virtual_memory().total,
                "available": psutil.virtual_memory().available,
                "percent_used": psutil.virtual_memory().percent
            },
            "disk": {
                "total": 0,
                "free": 0,
                "is_nvme": False,
                "io_speed": None  # Sera mesuré lors de l'optimisation
            },
            "gpu": {
                "available": False,
                "model": None,
                "memory": 0,
                "cuda_available": False,
                "is_rtx_3060": False
            },
            "network": {
                "interfaces": len(psutil.net_if_addrs())
            },
            "summary": ""
        }
        
        # Détection du disque sur lequel le projet est installé
        cwd = Path.cwd()
        try:
            disk_usage = psutil.disk_usage(cwd.anchor)
            hw_info["disk"]["total"] = disk_usage.total
            hw_info["disk"]["free"] = disk_usage.free
            
            # Vérification si le disque est NVMe (approximatif)
            if sys.platform == "win32":
                import wmi
                c = wmi.WMI()
                for disk in c.Win32_DiskDrive():
                    if "NVMe" in disk.Caption:
                        hw_info["disk"]["is_nvme"] = True
                        break
        except:
            logger.warning("Impossible de détecter les spécifications du disque")
        
        # Détection du GPU et support CUDA/TensorFlow
        if TORCH_AVAILABLE:
            hw_info["gpu"]["available"] = torch.cuda.is_available()
            hw_info["gpu"]["cuda_available"] = torch.cuda.is_available()
            
            if torch.cuda.is_available():
                hw_info["gpu"]["model"] = torch.cuda.get_device_name(0)
                hw_info["gpu"]["memory"] = torch.cuda.get_device_properties(0).total_memory
                hw_info["gpu"]["is_rtx_3060"] = "RTX 3060" in torch.cuda.get_device_name(0)
        
        # Créer un résumé du matériel détecté
        hw_info["summary"] = (
            f"Système: {hw_info['platform']}, "
            f"CPU: {hw_info['cpu']['model']} ({hw_info['cpu']['cores_physical']} cœurs physiques, "
            f"{hw_info['cpu']['cores_logical']} threads), "
            f"RAM: {hw_info['memory']['total'] // (1024**3)} Go, "
            f"GPU: {hw_info['gpu']['model'] if hw_info['gpu']['available'] else 'Non détecté'}, "
            f"Disque: {hw_info['disk']['total'] // (1024**3)} Go "
            f"({'NVMe' if hw_info['disk']['is_nvme'] else 'Standard'})"
        )
        
        return hw_info
    
    def _generate_optimization_params(self) -> Dict[str, Any]:
        """
        Génère des paramètres d'optimisation basés sur le matériel détecté.
        
        Returns:
            Dict contenant les paramètres d'optimisation.
        """
        hw = self.hardware_info
        params = {
            "cpu": {
                "optimal_threads": min(hw["cpu"]["cores_logical"] - 1, 8),
                "background_priority": True if hw["cpu"]["cores_logical"] >= 8 else False,
                "process_priority": "above_normal" if hw["cpu"]["cores_logical"] >= 6 else "normal",
                "thread_allocation": {
                    "trading": round(hw["cpu"]["cores_logical"] * 0.5),
                    "monitoring": 1,
                    "ai": max(1, round(hw["cpu"]["cores_logical"] * 0.3)),
                    "misc": 1
                }
            },
            "memory": {
                "max_usage_percent": 70,  # Limite d'utilisation de la RAM en pourcentage
                "trading_allocation_mb": int((hw["memory"]["total"] * 0.3) / 1024 / 1024),
                "cache_allocation_mb": int((hw["memory"]["total"] * 0.1) / 1024 / 1024),
                "ai_allocation_mb": int((hw["memory"]["total"] * 0.2) / 1024 / 1024),
                "garbage_collection_frequency": 300,  # secondes
                "cache_strategy": "adaptive" if hw["memory"]["total"] >= 8 * (1024**3) else "minimal"
            },
            "gpu": {
                "enabled": hw["gpu"]["available"],
                "optimal_batch_size": 8 if hw["gpu"]["is_rtx_3060"] else 4,
                "precision": "float16" if hw["gpu"]["is_rtx_3060"] else "float32",
                "models_to_gpu": ["token_analyzer", "market_predictor"] if hw["gpu"]["available"] else [],
                "memory_allocation": int(hw["gpu"]["memory"] * 0.7) if hw["gpu"]["available"] else 0,
                "use_tensor_cores": hw["gpu"]["is_rtx_3060"]
            },
            "disk": {
                "io_optimization": "high" if hw["disk"]["is_nvme"] else "medium",
                "read_buffer_size": 8192 if hw["disk"]["is_nvme"] else 4096,
                "write_buffer_size": 8192 if hw["disk"]["is_nvme"] else 4096,
                "log_level": "INFO",
                "cache_trading_data": True,
                "cache_dir": os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "cache"),
                "max_cache_size_mb": 2048 if hw["disk"]["is_nvme"] else 1024
            },
            "network": {
                "concurrent_connections": 32,
                "timeout_ms": 2000,
                "retry_attempts": 3,
                "priority_endpoints": ["mempool", "price_feed"]
            }
        }
        
        # Optimisations spécifiques pour i5-12400F
        if hw["cpu"]["is_i5_12400f"]:
            params["cpu"]["thread_allocation"]["trading"] = 4
            params["cpu"]["thread_allocation"]["ai"] = 2
            params["cpu"]["process_priority"] = "high"
        
        # Optimisations spécifiques pour RTX 3060
        if hw["gpu"]["is_rtx_3060"]:
            params["gpu"]["optimal_batch_size"] = 16
            params["gpu"]["models_to_gpu"].extend(["risk_evaluator", "pattern_detector"])
            params["gpu"]["precision"] = "float16"  # Utiliser half precision pour économiser de la mémoire
        
        return params
    
    def apply_optimizations(self, target: str = "all") -> bool:
        """
        Applique les optimisations pour le matériel cible.
        
        Args:
            target: Le composant à optimiser ("cpu", "gpu", "memory", "disk", "network" ou "all")
            
        Returns:
            True si les optimisations ont été appliquées avec succès, False sinon
        """
        success = True
        
        if target == "all" or target == "cpu":
            success = success and self._optimize_cpu()
            
        if target == "all" or target == "gpu":
            success = success and self._optimize_gpu()
            
        if target == "all" or target == "memory":
            success = success and self._optimize_memory()
            
        if target == "all" or target == "disk":
            success = success and self._optimize_disk()
            
        if target == "all" or target == "network":
            success = success and self._optimize_network()
        
        logger.info(f"Optimisations appliquées pour: {target}")
        
        # Démarrer la surveillance si toutes les optimisations sont actives
        if all(self.active_optimizations.values()):
            self.start_monitoring()
        
        return success
    
    def _optimize_cpu(self) -> bool:
        """
        Applique les optimisations CPU.
        
        Returns:
            True si les optimisations ont été appliquées avec succès, False sinon
        """
        try:
            params = self.optimization_params["cpu"]
            
            # Définir l'affinité CPU pour le processus principal si possible
            if sys.platform == "win32":
                try:
                    import win32api
                    import win32process
                    import win32con
                    
                    # Obtenir le handle du processus actuel
                    pid = win32api.GetCurrentProcessId()
                    handle = win32api.OpenProcess(win32con.PROCESS_ALL_ACCESS, True, pid)
                    
                    # Définir la priorité du processus
                    priority_map = {
                        "low": win32process.IDLE_PRIORITY_CLASS,
                        "below_normal": win32process.BELOW_NORMAL_PRIORITY_CLASS,
                        "normal": win32process.NORMAL_PRIORITY_CLASS,
                        "above_normal": win32process.ABOVE_NORMAL_PRIORITY_CLASS,
                        "high": win32process.HIGH_PRIORITY_CLASS,
                        "realtime": win32process.REALTIME_PRIORITY_CLASS
                    }
                    
                    priority_class = priority_map.get(params["process_priority"], win32process.NORMAL_PRIORITY_CLASS)
                    win32process.SetPriorityClass(handle, priority_class)
                    
                    logger.info(f"Priorité CPU définie à: {params['process_priority']}")
                except ImportError:
                    logger.warning("Impossible de définir la priorité CPU: module win32api non disponible")
            
            # Configurer le nombre de threads pour le pool de threads
            threading.stack_size(262144)  # 256KB stack size
            
            # Limiter le nombre maximal de threads
            max_workers = params["optimal_threads"]
            if hasattr(threading, "_thread_spawner"):
                threading._thread_spawner._max_workers = max_workers
            
            # Configurer le pool de processus pour limiter l'utilisation du CPU
            multiprocessing.cpu_count = lambda: params["optimal_threads"]
            
            self.active_optimizations["cpu"] = True
            logger.info(f"Optimisations CPU appliquées: {max_workers} threads optimaux")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'optimisation CPU: {str(e)}")
            return False
    
    def _optimize_gpu(self) -> bool:
        """
        Applique les optimisations GPU.
        
        Returns:
            True si les optimisations ont été appliquées avec succès, False sinon
        """
        if not self.hardware_info["gpu"]["available"]:
            logger.info("Aucun GPU détecté, optimisations GPU ignorées")
            return False
        
        try:
            params = self.optimization_params["gpu"]
            
            if TORCH_AVAILABLE and torch.cuda.is_available():
                # Configuration pour PyTorch
                torch.backends.cudnn.benchmark = True
                
                # Pour RTX 3060 avec architecture Ampere, activer TF32 si disponible
                if self.hardware_info["gpu"]["is_rtx_3060"]:
                    if hasattr(torch.backends.cuda, 'matmul') and hasattr(torch.backends.cudnn, 'allow_tf32'):
                        torch.backends.cuda.matmul.allow_tf32 = True
                        torch.backends.cudnn.allow_tf32 = True
                
                # Configuration de la précision
                if params["precision"] == "float16" and torch.cuda.is_available():
                    if torch.cuda.get_device_capability(0)[0] >= 7:  # Volta+ GPUs
                        torch.set_default_dtype(torch.float16)
                
                logger.info(f"Optimisations GPU PyTorch appliquées: {torch.cuda.get_device_name(0)}")
            
            if TF_AVAILABLE:
                # Configuration pour TensorFlow
                if tf.config.list_physical_devices('GPU'):
                    for gpu in tf.config.list_physical_devices('GPU'):
                        try:
                            # Limiter la mémoire GPU utilisée par TensorFlow
                            gpu_memory_limit = int(params["memory_allocation"] * 0.8)  # 80% de l'allocation définie
                            tf.config.experimental.set_memory_growth(gpu, True)
                            tf.config.set_logical_device_configuration(
                                gpu,
                                [tf.config.LogicalDeviceConfiguration(memory_limit=gpu_memory_limit)]
                            )
                        except RuntimeError as e:
                            logger.warning(f"Erreur lors de la configuration TensorFlow GPU: {str(e)}")
                    
                    # Utiliser la précision mixte pour économiser de la mémoire et accélérer le calcul
                    if params["precision"] == "float16":
                        policy = tf.keras.mixed_precision.Policy('mixed_float16')
                        tf.keras.mixed_precision.set_global_policy(policy)
                    
                    logger.info("Optimisations GPU TensorFlow appliquées")
            
            # Configuration de l'allocation de mémoire et du cache
            # (Ces optimisations sont théoriques et devraient être ajustées selon les besoins réels)
            os.environ["CUDA_CACHE_MAXSIZE"] = "2147483648"  # 2GB de cache CUDA
            os.environ["CUDA_CACHE_DISABLE"] = "0"  # Activer le cache CUDA
            
            self.active_optimizations["gpu"] = True
            logger.info(f"Optimisations GPU appliquées: {params['precision']}, batch size {params['optimal_batch_size']}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'optimisation GPU: {str(e)}")
            return False
    
    def _optimize_memory(self) -> bool:
        """
        Applique les optimisations de mémoire.
        
        Returns:
            True si les optimisations ont été appliquées avec succès, False sinon
        """
        try:
            params = self.optimization_params["memory"]
            
            # Définir la limite d'utilisation de la mémoire pour les modules
            # (Cette information sera utilisée par les autres modules)
            max_memory = self.hardware_info["memory"]["total"] * (params["max_usage_percent"] / 100)
            
            # Configuration des allocations par module
            self.memory_allocations = {
                "trading": params["trading_allocation_mb"] * 1024 * 1024,  # Conversion en octets
                "cache": params["cache_allocation_mb"] * 1024 * 1024,
                "ai": params["ai_allocation_mb"] * 1024 * 1024
            }
            
            # Fonctions de récupération de mémoire
            def collect_garbage():
                import gc
                gc.collect()
            
            # Configurer la collecte de déchets périodique
            if params["garbage_collection_frequency"] > 0:
                threading.Timer(params["garbage_collection_frequency"], collect_garbage).start()
            
            self.active_optimizations["memory"] = True
            logger.info(f"Optimisations mémoire appliquées: max {params['max_usage_percent']}% d'utilisation")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'optimisation de la mémoire: {str(e)}")
            return False
    
    def _optimize_disk(self) -> bool:
        """
        Applique les optimisations de disque.
        
        Returns:
            True si les optimisations ont été appliquées avec succès, False sinon
        """
        try:
            params = self.optimization_params["disk"]
            
            # Créer le répertoire de cache s'il n'existe pas
            cache_dir = Path(params["cache_dir"])
            if not cache_dir.exists():
                cache_dir.mkdir(parents=True, exist_ok=True)
            
            # Configurer les tampons d'E/S pour les opérations de fichier
            # (Ces valeurs sont théoriques et devraient être ajustées selon les tests de performance)
            if hasattr(os, "posix_fadvise"):  # Linux
                def file_read_optimized(file_path, mode="rb"):
                    fd = os.open(file_path, os.O_RDONLY)
                    os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_SEQUENTIAL)
                    return os.fdopen(fd, mode, buffering=params["read_buffer_size"])
                
                self.file_read_optimized = file_read_optimized
            
            # Mesurer les performances d'I/O
            start_time = time.time()
            test_file = os.path.join(params["cache_dir"], "io_test.bin")
            
            # Test d'écriture
            with open(test_file, "wb") as f:
                f.write(b"\0" * 10 * 1024 * 1024)  # 10 MB
            
            # Test de lecture
            with open(test_file, "rb") as f:
                f.read()
            
            # Suppression du fichier de test
            if os.path.exists(test_file):
                os.remove(test_file)
            
            elapsed = time.time() - start_time
            io_speed = (20 * 1024 * 1024) / elapsed  # Octets par seconde (lecture + écriture)
            
            self.hardware_info["disk"]["io_speed"] = io_speed
            logger.info(f"Vitesse I/O mesurée: {io_speed / (1024 * 1024):.2f} MB/s")
            
            # Ajuster les optimisations en fonction de la vitesse d'I/O mesurée
            if io_speed > 500 * 1024 * 1024:  # Plus de 500 MB/s
                self.optimization_params["disk"]["io_optimization"] = "ultra"
                self.optimization_params["disk"]["read_buffer_size"] = 16384
                self.optimization_params["disk"]["write_buffer_size"] = 16384
            
            self.active_optimizations["disk"] = True
            logger.info(f"Optimisations disque appliquées: mode {params['io_optimization']}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'optimisation du disque: {str(e)}")
            return False
    
    def _optimize_network(self) -> bool:
        """
        Applique les optimisations réseau.
        
        Returns:
            True si les optimisations ont été appliquées avec succès, False sinon
        """
        try:
            params = self.optimization_params["network"]
            
            # Ces optimisations sont principalement des recommandations qui seront utilisées
            # par les modules de communication réseau
            
            # Configurer les sockets pour le balayage rapide de la mempool
            if hasattr(socket, "TCP_NODELAY") and sys.platform != "win32":
                socket.TCP_NODELAY = True
            
            self.active_optimizations["network"] = True
            logger.info(f"Optimisations réseau appliquées: {params['concurrent_connections']} connexions simultanées")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'optimisation réseau: {str(e)}")
            return False
    
    def start_monitoring(self) -> bool:
        """
        Démarre la surveillance des performances du système.
        
        Returns:
            True si la surveillance a démarré avec succès, False sinon
        """
        if self.monitoring_active:
            logger.warning("La surveillance est déjà active")
            return True
        
        try:
            self.monitoring_active = True
            
            def monitoring_loop():
                while self.monitoring_active:
                    try:
                        # Collecter les métriques de performance
                        self.performance_metrics["cpu_usage"].append(psutil.cpu_percent(interval=0.1))
                        self.performance_metrics["memory_usage"].append(psutil.virtual_memory().percent)
                        
                        # Collecter les métriques GPU si disponible
                        if self.hardware_info["gpu"]["available"] and TORCH_AVAILABLE:
                            try:
                                gpu_usage = torch.cuda.memory_allocated(0) / torch.cuda.max_memory_allocated(0) * 100 if torch.cuda.max_memory_allocated(0) > 0 else 0
                                self.performance_metrics["gpu_usage"].append(gpu_usage)
                            except:
                                self.performance_metrics["gpu_usage"].append(0)
                        
                        # Limiter la taille des historiques (garder les 60 derniers points = 5 minutes à 5s d'intervalle)
                        max_history = 60
                        for key in self.performance_metrics:
                            if len(self.performance_metrics[key]) > max_history:
                                self.performance_metrics[key] = self.performance_metrics[key][-max_history:]
                        
                        # Pause entre les mesures
                        time.sleep(self.monitoring_interval)
                    except Exception as e:
                        logger.error(f"Erreur dans la boucle de surveillance: {str(e)}")
                        time.sleep(5)  # Pause plus longue en cas d'erreur
                        
            # Démarrer le thread de surveillance
            self.monitoring_thread = threading.Thread(target=monitoring_loop, daemon=True)
            self.monitoring_thread.start()
            
            logger.info(f"Surveillance des performances démarrée (intervalle: {self.monitoring_interval}s)")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors du démarrage de la surveillance: {str(e)}")
            self.monitoring_active = False
            return False
    
    def stop_monitoring(self) -> bool:
        """
        Arrête la surveillance des performances.
        
        Returns:
            True si la surveillance a été arrêtée avec succès
        """
        self.monitoring_active = False
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=2.0)
        
        logger.info("Surveillance des performances arrêtée")
        return True
    
    def get_optimization_status(self) -> Dict[str, Any]:
        """
        Retourne l'état actuel des optimisations et les métriques de performance.
        
        Returns:
            Dict contenant l'état des optimisations et les métriques de performance
        """
        current_metrics = {
            "cpu": psutil.cpu_percent(),
            "memory": psutil.virtual_memory().percent,
            "gpu": 0,
            "disk_free_percent": 100 - psutil.disk_usage(Path.cwd().anchor).percent
        }
        
        # Obtenir l'utilisation GPU si disponible
        if self.hardware_info["gpu"]["available"] and TORCH_AVAILABLE:
            try:
                current_metrics["gpu"] = torch.cuda.memory_allocated(0) / torch.cuda.get_device_properties(0).total_memory * 100
            except:
                pass
        
        # Calculer les moyennes des métriques collectées
        avg_metrics = {}
        for key, values in self.performance_metrics.items():
            if values:
                avg_metrics[key] = sum(values) / len(values)
            else:
                avg_metrics[key] = 0
        
        return {
            "optimizations": self.active_optimizations,
            "hardware_info": self.hardware_info,
            "current_metrics": current_metrics,
            "average_metrics": avg_metrics,
            "optimization_params": self.optimization_params
        }
    
    def save_optimization_profile(self, profile_name: str = "default") -> bool:
        """
        Sauvegarde le profil d'optimisation actuel.
        
        Args:
            profile_name: Nom du profil à sauvegarder
            
        Returns:
            True si le profil a été sauvegardé avec succès, False sinon
        """
        try:
            config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "config", "optimization")
            os.makedirs(config_dir, exist_ok=True)
            
            profile_path = os.path.join(config_dir, f"{profile_name}.json")
            
            profile_data = {
                "hardware_info": self.hardware_info,
                "optimization_params": self.optimization_params,
                "active_optimizations": self.active_optimizations,
                "created_at": time.time(),
                "version": "1.0"
            }
            
            with open(profile_path, "w") as f:
                json.dump(profile_data, f, indent=2)
            
            logger.info(f"Profil d'optimisation sauvegardé: {profile_path}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde du profil d'optimisation: {str(e)}")
            return False
    
    def load_optimization_profile(self, profile_name: str = "default") -> bool:
        """
        Charge un profil d'optimisation.
        
        Args:
            profile_name: Nom du profil à charger
            
        Returns:
            True si le profil a été chargé avec succès, False sinon
        """
        try:
            config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "config", "optimization")
            profile_path = os.path.join(config_dir, f"{profile_name}.json")
            
            if not os.path.exists(profile_path):
                logger.warning(f"Profil d'optimisation non trouvé: {profile_path}")
                return False
            
            with open(profile_path, "r") as f:
                profile_data = json.load(f)
            
            # Mettre à jour les paramètres depuis le profil
            if "optimization_params" in profile_data:
                self.optimization_params = profile_data["optimization_params"]
            
            logger.info(f"Profil d'optimisation chargé: {profile_path}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors du chargement du profil d'optimisation: {str(e)}")
            return False
    
    def get_recommendations(self) -> List[str]:
        """
        Génère des recommandations d'optimisation basées sur le matériel détecté.
        
        Returns:
            Liste de recommandations pour améliorer les performances
        """
        recommendations = []
        hw = self.hardware_info
        
        # Recommandations CPU
        if hw["cpu"]["cores_logical"] < 8:
            recommendations.append("Réduire le nombre de stratégies simultanées pour éviter la surcharge CPU")
        
        # Recommandations RAM
        ram_gb = hw["memory"]["total"] / (1024**3)
        if ram_gb < 16:
            recommendations.append("Limiter l'utilisation des modèles d'IA gourmands en mémoire")
        
        # Recommandations GPU
        if not hw["gpu"]["available"]:
            recommendations.append("Exécuter les modèles d'IA en mode CPU (performances réduites)")
        elif not hw["gpu"]["is_rtx_3060"]:
            recommendations.append("Utiliser des modèles d'IA plus légers adaptés à votre GPU")
        
        # Recommandations disque
        if not hw["disk"]["is_nvme"]:
            recommendations.append("Activer la mise en cache agressive pour compenser la vitesse du disque")
        
        # Recommandations spécifiques pour i5-12400F + RTX 3060
        if hw["cpu"]["is_i5_12400f"] and hw["gpu"]["is_rtx_3060"]:
            recommendations.append("Configuration optimale: déplacer les calculs intensifs sur GPU pour libérer le CPU")
            recommendations.append("Activer CUDA pour les modèles de trading et d'analyse")
        
        return recommendations

# Fonction d'utilitaire pour obtenir un optimiseur initialisé
def get_hardware_optimizer(config: Dict[str, Any] = None) -> HardwareOptimizer:
    """
    Fonction utilitaire pour obtenir une instance d'optimiseur matériel.
    
    Args:
        config: Configuration optionnelle
        
    Returns:
        Instance de HardwareOptimizer initialisée
    """
    return HardwareOptimizer(config)

# Point d'entrée pour les tests
if __name__ == "__main__":
    # Configuration du logging pour les tests
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Initialiser et tester l'optimiseur
    optimizer = HardwareOptimizer()
    print("Informations matérielles détectées:")
    print(json.dumps(optimizer.hardware_info, indent=2, default=str))
    
    print("\nApplication des optimisations...")
    optimizer.apply_optimizations()
    
    print("\nRecommandations d'optimisation:")
    for rec in optimizer.get_recommendations():
        print(f"- {rec}")
    
    # Démarrer la surveillance et collecter quelques métriques
    optimizer.start_monitoring()
    print("\nSurveillance démarrée, collecte des métriques pendant 10 secondes...")
    time.sleep(10)
    
    # Afficher les résultats
    status = optimizer.get_optimization_status()
    print("\nMétriques de performance actuelles:")
    print(json.dumps(status["current_metrics"], indent=2))
    
    # Arrêter la surveillance
    optimizer.stop_monitoring()
    print("\nSurveillance arrêtée")
    
    # Sauvegarder le profil pour une utilisation future
    optimizer.save_optimization_profile("autodetect")
    print("\nProfil d'optimisation sauvegardé") 