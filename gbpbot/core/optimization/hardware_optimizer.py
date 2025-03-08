"""
Optimiseur hardware pour GBPBot
===============================

Ce module fournit un optimiseur spécialisé pour ajuster les performances
matérielles du système, en optimisant l'utilisation des ressources CPU,
mémoire, disque et réseau.
"""

import os
import sys
import platform
import logging
import gc
from typing import Dict, Any, Optional, List

from .base_optimizer import BaseOptimizer, OptimizationResult, OptimizationConfig, OptimizationException

# Configuration du logging
logger = logging.getLogger("gbpbot.optimization.hardware")

# Tentative d'import de psutil
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    logger.warning("psutil n'est pas installé, certaines optimisations ne seront pas disponibles")

# Tentative d'import de numpy (pour les optimisations liées à NumPy)
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    logger.warning("numpy n'est pas installé, certaines optimisations ne seront pas disponibles")

# Tentative d'import de torch (pour les optimisations GPU)
try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False
    logger.warning("torch n'est pas installé, certaines optimisations GPU ne seront pas disponibles")


class HardwareOptimizer(BaseOptimizer):
    """
    Optimiseur pour les performances matérielles.
    
    Cette classe applique diverses optimisations pour améliorer les performances
    matérielles du GBPBot, en fonction de la configuration détectée.
    """
    
    def __init__(self, config: Optional[OptimizationConfig] = None):
        """
        Initialise l'optimiseur hardware.
        
        Args:
            config: Configuration initiale de l'optimiseur
        """
        super().__init__(name="hardware", config=config or {})
        
        # Configuration par défaut
        default_config = {
            "memory_optimization_level": 2,  # 0-3
            "cpu_optimization_level": 2,  # 0-3
            "io_optimization_level": 1,  # 0-3
            "gpu_optimization_level": 2,  # 0-3
            "enable_gc_optimization": True,
            "enable_memory_profiling": False,
            "enable_cpu_affinity": True,
            "enable_numpy_optimization": True,
            "enable_process_priority": True
        }
        
        # Fusionner avec la configuration fournie
        for key, value in default_config.items():
            if key not in self.config:
                self.config[key] = value
        
        # Définir une priorité élevée pour cet optimiseur
        self.set_priority(90)
        
        # Détection matérielle
        self._hardware_info = self._detect_hardware()
        
        # Dernières optimisations appliquées
        self._last_optimizations = []
    
    def _detect_hardware(self) -> Dict[str, Any]:
        """
        Détecte la configuration matérielle du système.
        
        Returns:
            Dict[str, Any]: Informations sur le matériel détecté
        """
        info = {
            "platform": platform.system(),
            "platform_release": platform.release(),
            "platform_version": platform.version(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
            "python_compiler": platform.python_compiler(),
            "cpu_count": os.cpu_count(),
            "has_psutil": HAS_PSUTIL,
            "has_numpy": HAS_NUMPY,
            "has_torch": HAS_TORCH,
            "memory_info": {}
        }
        
        # Informations supplémentaires avec psutil
        if HAS_PSUTIL:
            try:
                # CPU
                info["cpu_count_logical"] = psutil.cpu_count(logical=True)
                info["cpu_count_physical"] = psutil.cpu_count(logical=False)
                
                # Mémoire
                vm = psutil.virtual_memory()
                info["memory_info"] = {
                    "total": vm.total,
                    "available": vm.available,
                    "percent": vm.percent
                }
                
                # Disque
                disk = psutil.disk_usage("/")
                info["disk_info"] = {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": disk.percent
                }
            except Exception as e:
                logger.warning(f"Erreur lors de la détection matérielle avec psutil: {e}")
        
        # Informations GPU avec torch
        if HAS_TORCH:
            try:
                info["cuda_available"] = torch.cuda.is_available()
                if info["cuda_available"]:
                    info["cuda_device_count"] = torch.cuda.device_count()
                    info["cuda_current_device"] = torch.cuda.current_device()
                    info["cuda_device_name"] = torch.cuda.get_device_name(0)
            except Exception as e:
                logger.warning(f"Erreur lors de la détection GPU avec torch: {e}")
        
        return info
    
    def can_optimize(self) -> bool:
        """
        Vérifie si l'optimiseur hardware peut être utilisé sur ce système.
            
        Returns:
            bool: True si l'optimiseur peut être utilisé, False sinon
        """
        # Vérifier si les prérequis minimaux sont disponibles
        if not HAS_PSUTIL and self.config.get("memory_optimization_level", 0) > 0:
            logger.warning("psutil est requis pour l'optimisation mémoire")
            return False
        
        return True
    
    def optimize(self) -> OptimizationResult:
        """
        Applique les optimisations hardware en fonction de la configuration.
        
        Returns:
            OptimizationResult: Résultats des optimisations appliquées
        """
        optimizations_applied = []
        status = "success"
        details = {}
        
        try:
            # Optimisation de la mémoire
            if self.config.get("memory_optimization_level", 0) > 0:
                memory_results = self._optimize_memory()
                optimizations_applied.extend(memory_results.get("optimizations_applied", []))
                details["memory"] = memory_results
            
            # Optimisation du CPU
            if self.config.get("cpu_optimization_level", 0) > 0:
                cpu_results = self._optimize_cpu()
                optimizations_applied.extend(cpu_results.get("optimizations_applied", []))
                details["cpu"] = cpu_results
            
            # Optimisation des E/S
            if self.config.get("io_optimization_level", 0) > 0:
                io_results = self._optimize_io()
                optimizations_applied.extend(io_results.get("optimizations_applied", []))
                details["io"] = io_results
            
            # Optimisation GPU
            if self.config.get("gpu_optimization_level", 0) > 0 and HAS_TORCH:
                gpu_results = self._optimize_gpu()
                optimizations_applied.extend(gpu_results.get("optimizations_applied", []))
                details["gpu"] = gpu_results
            
            # Optimisation pour NumPy
            if self.config.get("enable_numpy_optimization", True) and HAS_NUMPY:
                numpy_results = self._optimize_numpy()
                optimizations_applied.extend(numpy_results.get("optimizations_applied", []))
                details["numpy"] = numpy_results
            
            # Mettre à jour les dernières optimisations
            self._last_optimizations = optimizations_applied
            
        except Exception as e:
            logger.error(f"Erreur lors de l'optimisation hardware: {str(e)}")
            status = "error"
            details["error"] = str(e)
        
        return {
            "status": status,
            "optimizations_applied": optimizations_applied,
            "details": details
        }
    
    def validate(self) -> bool:
        """
        Valide que les optimisations ont été correctement appliquées.
        
        Returns:
            bool: True si les optimisations sont valides, False sinon
        """
        # Validation simple: vérifier que les optimisations appliquées sont toujours actives
        validated = True
        
        # Vérifier les optimisations NumPy
        if "numpy_threadpool_size" in self._last_optimizations and HAS_NUMPY:
            try:
                import threadpoolctl
                info = threadpoolctl.threadpool_info()
                
                # Vérifier si le threadpool est configuré comme attendu
                if not any(pool.get("num_threads") == self.config.get("numpy_threads", 4) 
                         for pool in info 
                         if pool.get("user_api", "").lower() == "blas"):
                    validated = False
            except ImportError:
                pass
        
        # Vérifier l'optimisation CPU affinity
        if "cpu_affinity" in self._last_optimizations and HAS_PSUTIL:
            try:
                process = psutil.Process()
                current_affinity = process.cpu_affinity()
                
                # Vérifier si l'affinité est configurée comme attendu
                if len(current_affinity) != self.config.get("cpu_threads", os.cpu_count()):
                    validated = False
            except Exception:
                pass
        
        # Vérifier l'optimisation GPU (torch)
        if "cuda_memory_allocation" in self._last_optimizations and HAS_TORCH:
            try:
                # Vérifier si les caches ont été vidés
                if torch.cuda.is_available() and torch.cuda.memory_allocated() > 0:
                    if self.config.get("gpu_optimization_level", 0) > 2:
                        validated = False
            except Exception:
                pass
        
        return validated
    
    def _optimize_memory(self) -> Dict[str, Any]:
        """
        Applique les optimisations liées à la mémoire.
        
        Returns:
            Dict[str, Any]: Résultats des optimisations mémoire
        """
        results = {
            "optimizations_applied": [],
            "before": {},
            "after": {}
        }
        
        if not HAS_PSUTIL:
            return results
        
        try:
            # Mesurer l'utilisation mémoire avant
            vm_before = psutil.virtual_memory()
            results["before"] = {
                "percent": vm_before.percent,
                "available": vm_before.available,
                "total": vm_before.total
            }
            
            level = self.config.get("memory_optimization_level", 0)
            
            # Niveau 1: Garbage collection agressif
            if level >= 1 and self.config.get("enable_gc_optimization", True):
                gc.collect(2)  # Forcer un GC complet
                results["optimizations_applied"].append("gc_collect")
            
            # Niveau 2: Libérer les caches OS
            if level >= 2:
                if platform.system() == "Linux":
                    # Libérer les caches sur Linux
                    try:
                        if os.geteuid() == 0:  # Root uniquement
                            os.system("sync && echo 3 > /proc/sys/vm/drop_caches")
                            results["optimizations_applied"].append("linux_cache_drop")
                    except Exception:
                        pass
                elif platform.system() == "Windows":
                    # Sur Windows, utiliser une alternative comme appeler le rammap (non implémenté)
                    pass
            
            # Niveau 3: Limiter l'utilisation mémoire et ajuster les pools
            if level >= 3:
                # Ajuster les pools NumPy si disponibles
                if HAS_NUMPY:
                    if np.__config__.get_info("lapack_opt_info").get("libraries"):
                        try:
                            import threadpoolctl
                            threadpoolctl.threadpool_limits(limits=self.config.get("numpy_threads", 4), user_api="blas")
                            results["optimizations_applied"].append("numpy_threadpool_size")
                        except ImportError:
                            pass
            
            # Mesurer l'utilisation mémoire après
            vm_after = psutil.virtual_memory()
            results["after"] = {
                "percent": vm_after.percent,
                "available": vm_after.available,
                "total": vm_after.total
            }
            
            # Calcul de l'amélioration
            memory_freed = vm_after.available - vm_before.available
            results["memory_freed"] = memory_freed
            results["memory_freed_mb"] = memory_freed / (1024 * 1024)
            
        except Exception as e:
            results["error"] = str(e)
        
        return results
    
    def _optimize_cpu(self) -> Dict[str, Any]:
        """
        Applique les optimisations liées au CPU.
        
        Returns:
            Dict[str, Any]: Résultats des optimisations CPU
        """
        results = {
            "optimizations_applied": [],
            "before": {},
            "after": {}
        }
        
        if not HAS_PSUTIL:
            return results
        
        try:
            level = self.config.get("cpu_optimization_level", 0)
            
            # Niveau 1: Ajuster la priorité du processus
            if level >= 1 and self.config.get("enable_process_priority", True):
                process = psutil.Process()
                
                # Mesurer avant
                results["before"]["priority"] = process.nice()
                
                if platform.system() == "Windows":
                    # Augmenter la priorité sur Windows (HIGH_PRIORITY_CLASS)
                    try:
                        import win32process
                        win32process.SetPriorityClass(process.pid, win32process.HIGH_PRIORITY_CLASS)
                        results["optimizations_applied"].append("windows_high_priority")
                    except ImportError:
                        # Fallback natif
                        process.nice(psutil.HIGH_PRIORITY_CLASS)
                        results["optimizations_applied"].append("windows_high_priority_fallback")
                else:
                    # Augmenter la priorité sur Unix
                    nice_value = self.config.get("process_nice_value", -10)
                    try:
                        process.nice(nice_value)
                        results["optimizations_applied"].append("unix_process_priority")
                    except psutil.AccessDenied:
                        # Fallback: essayer avec une valeur moins agressive
                        try:
                            process.nice(0)
                            results["optimizations_applied"].append("unix_process_priority_fallback")
                        except Exception:
                            pass
                
                # Mesurer après
                results["after"]["priority"] = process.nice()
            
            # Niveau 2: Configurer l'affinité CPU
            if level >= 2 and self.config.get("enable_cpu_affinity", True):
                process = psutil.Process()
                
                # Mesurer avant
                try:
                    results["before"]["cpu_affinity"] = process.cpu_affinity()
                except Exception:
                    results["before"]["cpu_affinity"] = []
                
                # Configurer l'affinité CPU
                try:
                    cpu_count = psutil.cpu_count(logical=True)
                    cpu_threads = self.config.get("cpu_threads", cpu_count)
                    
                    # Limiter au nombre réel de cœurs
                    cpu_threads = min(cpu_threads, cpu_count)
                    
                    # Affecter à des cœurs spécifiques
                    process.cpu_affinity(list(range(cpu_threads)))
                    results["optimizations_applied"].append("cpu_affinity")
                    
                    # Mesurer après
                    results["after"]["cpu_affinity"] = process.cpu_affinity()
                except Exception as e:
                    results["cpu_affinity_error"] = str(e)
            
        except Exception as e:
            results["error"] = str(e)
        
        return results
    
    def _optimize_io(self) -> Dict[str, Any]:
        """
        Applique les optimisations liées aux opérations d'entrée/sortie.
        
        Returns:
            Dict[str, Any]: Résultats des optimisations I/O
        """
        results = {
            "optimizations_applied": [],
            "before": {},
            "after": {}
        }
        
        try:
            level = self.config.get("io_optimization_level", 0)
            
            # Niveau 1: Optimisation basique (buffering)
            if level >= 1:
                # Configurer le buffering pour stdout/stderr
                if not isinstance(sys.stdout, io.TextIOWrapper) or not isinstance(sys.stderr, io.TextIOWrapper):
                    import io
                    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, write_through=False, line_buffering=True)
                    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, write_through=False, line_buffering=True)
                    results["optimizations_applied"].append("stdout_buffering")
                
                # Configurer le buffer de lecture des fichiers
                import builtins
                original_open = builtins.open
                
                def optimized_open(*args, **kwargs):
                    if 'buffering' not in kwargs:
                        kwargs['buffering'] = self.config.get("file_buffer_size", -1)  # -1 = système par défaut
                    return original_open(*args, **kwargs)
                
                builtins.open = optimized_open
                results["optimizations_applied"].append("file_buffering")
            
            # Niveau 2: Préfetching et optimisations avancées
            if level >= 2:
                # Configurer les optimisations spécifiques au système de fichiers
                if platform.system() == "Linux":
                    # Configurer readahead
                    try:
                        import fcntl
                        for fd in range(3, 10):  # Tester quelques descripteurs
                            try:
                                fcntl.fcntl(fd, fcntl.F_SETFL, os.O_NONBLOCK)
                                results["optimizations_applied"].append("linux_nonblocking_io")
                                break
                            except Exception:
                                pass
                    except ImportError:
                        pass
                
            # Niveau 3: Optimisations agressives
            if level >= 3:
                pass  # À implémenter selon besoins spécifiques
            
        except Exception as e:
            results["error"] = str(e)
        
        return results
    
    def _optimize_gpu(self) -> Dict[str, Any]:
        """
        Applique les optimisations liées au GPU.
        
        Returns:
            Dict[str, Any]: Résultats des optimisations GPU
        """
        results = {
            "optimizations_applied": [],
            "before": {},
            "after": {}
        }
        
        if not HAS_TORCH or not torch.cuda.is_available():
            return results
        
        try:
            level = self.config.get("gpu_optimization_level", 0)
            
            # Mesurer l'utilisation avant
            results["before"]["memory_allocated"] = torch.cuda.memory_allocated()
            results["before"]["memory_reserved"] = torch.cuda.memory_reserved()
            
            # Niveau 1: Configuration basique
            if level >= 1:
                # Configurer NumPy pour utiliser TensorCore si disponible
                if HAS_NUMPY:
                    np.matmul.allow_tf32 = True
                    results["optimizations_applied"].append("numpy_tf32")
                
                # Configurer PyTorch pour utiliser TensorCore si disponible
                torch.backends.cuda.matmul.allow_tf32 = True
                torch.backends.cudnn.allow_tf32 = True
                results["optimizations_applied"].append("torch_tf32")
            
            # Niveau 2: Configuration avancée
            if level >= 2:
                # Activer les algorithmes cudnn déterministes pour plus de performance
                torch.backends.cudnn.benchmark = True
                torch.backends.cudnn.deterministic = False
                results["optimizations_applied"].append("cudnn_benchmark")
                
                # Optimiser l'allocation mémoire
                if hasattr(torch.cuda, 'memory_stats'):
                    # Libérer la mémoire non utilisée
                    torch.cuda.empty_cache()
                    results["optimizations_applied"].append("cuda_memory_allocation")
            
            # Niveau 3: Optimisations agressives
            if level >= 3:
                # Vider tous les caches et forcer un garbage collect
                torch.cuda.empty_cache()
                gc.collect()
                
                # Récupérer tous les tenseurs alloués
                if hasattr(torch.cuda, 'memory_snapshot'):
                    # NV Nsight support
                    torch.cuda.memory_snapshot()
                
                results["optimizations_applied"].append("cuda_aggressive_cleanup")
            
            # Mesurer l'utilisation après
            results["after"]["memory_allocated"] = torch.cuda.memory_allocated()
            results["after"]["memory_reserved"] = torch.cuda.memory_reserved()
            
            # Calcul de l'amélioration
            memory_freed = (results["before"]["memory_allocated"] - results["after"]["memory_allocated"])
            results["memory_freed"] = memory_freed
            results["memory_freed_mb"] = memory_freed / (1024 * 1024)
            
        except Exception as e:
            results["error"] = str(e)
        
        return results
    
    def _optimize_numpy(self) -> Dict[str, Any]:
        """
        Applique les optimisations liées à NumPy.
            
        Returns:
            Dict[str, Any]: Résultats des optimisations NumPy
        """
        results = {
            "optimizations_applied": [],
            "before": {},
            "after": {}
        }
        
        if not HAS_NUMPY:
            return results
        
        try:
            # Configuration multi-threading
            try:
                import threadpoolctl
                info_before = threadpoolctl.threadpool_info()
                results["before"] = {"threadpool_info": info_before}
                
                # Limiter les threads pour économiser des ressources
                cpu_threads = self.config.get("numpy_threads", os.cpu_count())
                threadpoolctl.threadpool_limits(limits=cpu_threads)
                results["optimizations_applied"].append("numpy_threadpool_size")
                
                info_after = threadpoolctl.threadpool_info()
                results["after"] = {"threadpool_info": info_after}
            except ImportError:
                # Configurer manuellement
                os.environ["OMP_NUM_THREADS"] = str(self.config.get("numpy_threads", os.cpu_count()))
                os.environ["MKL_NUM_THREADS"] = str(self.config.get("numpy_threads", os.cpu_count()))
                results["optimizations_applied"].append("numpy_env_threads")
            
            # Optimisations spécifiques à MKL
            if hasattr(np, "__mkl_version__"):
                results["before"]["mkl_version"] = np.__mkl_version__
                
                # Optimiser les petites matrices
                if "mkl_service" in sys.modules:
                    import mkl
                    mkl.set_num_threads(self.config.get("numpy_threads", os.cpu_count()))
                    results["optimizations_applied"].append("mkl_threads")
            
        except Exception as e:
            results["error"] = str(e)
        
        return results

# Instance singleton pour un accès facile
_instance = None

def get_hardware_optimizer(config: OptimizationConfig = None) -> HardwareOptimizer:
    """
    Récupère l'instance singleton de l'optimiseur hardware.
    
    Args:
        config: Configuration optionnelle pour l'optimiseur
        
    Returns:
        HardwareOptimizer: Instance de l'optimiseur hardware
    """
    global _instance
    if _instance is None:
        _instance = HardwareOptimizer(config=config)
    elif config:
        _instance.set_config(config)
    return _instance

# Importation à la fin pour éviter les cycles d'importation
import io 