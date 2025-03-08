"""
Moniteur de ressources système pour GBPBot
==========================================

Ce module fournit une implémentation de BaseMonitor spécialisée dans la
surveillance des ressources système : CPU, mémoire, disque et réseau.
Il remplace et unifie les fonctionnalités de resource_monitor.py et
performance_monitor.py.
"""

import os
import platform
import time
from typing import Dict, Any, Optional
from datetime import datetime

from .base_monitor import BaseMonitor, MetricValue, MonitoringException

# Gestion de l'import de psutil
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    # Classe factice pour éviter les erreurs
    class FakePsutil:
        @staticmethod
        def cpu_percent(*args, **kwargs):
            return 0.0
        @staticmethod
        def virtual_memory():
            class FakeMemory:
                percent = 0.0
                available = 0
                total = 0
            return FakeMemory()
        @staticmethod
        def disk_usage(path):
            class FakeDisk:
                percent = 0.0
                total = 0
                used = 0
            return FakeDisk()
        @staticmethod
        def Process(*args, **kwargs):
            class FakeProcess:
                def cpu_percent(self, *args, **kwargs):
                    return 0.0
                def memory_info(self):
                    class FakeMemInfo:
                        rss = 0
                    return FakeMemInfo()
                def io_counters(self):
                    class FakeIO:
                        read_bytes = 0
                        write_bytes = 0
                    return FakeIO()
            return FakeProcess()
        @staticmethod
        def net_io_counters():
            class FakeNetIO:
                bytes_sent = 0
                bytes_recv = 0
            return FakeNetIO()
        @staticmethod
        def disk_io_counters():
            class FakeDiskIO:
                read_bytes = 0
                write_bytes = 0
            return FakeDiskIO()
        @staticmethod
        def cpu_count(logical=True):
            return 4
        @staticmethod
        def cpu_freq():
            class FakeCpuFreq:
                current = 0.0
            return FakeCpuFreq()
    psutil = FakePsutil()


class SystemMonitor(BaseMonitor):
    """
    Moniteur de ressources système pour GBPBot.
    
    Cette classe surveille l'utilisation du CPU, de la mémoire,
    du disque et du réseau, et déclenche des alertes si les seuils
    sont dépassés.
    """
    
    def __init__(self, check_interval: float = 5.0, auto_start: bool = False):
        """
        Initialise le moniteur de ressources système.
        
        Args:
            check_interval: Intervalle entre les vérifications en secondes
            auto_start: Démarrer automatiquement le monitoring
        """
        super().__init__(name="system", check_interval=check_interval, auto_start=False)
        
        # Configurer les seuils par défaut
        # Basés sur l'analyse de la configuration matérielle (i5-12400F, 16Go RAM)
        self.set_threshold("cpu_percent", 70.0)  # % utilisation CPU
        self.set_threshold("memory_percent", 70.0)  # % utilisation mémoire
        self.set_threshold("disk_percent", 85.0)  # % utilisation disque
        self.set_threshold("swap_percent", 50.0)  # % utilisation swap
        
        # Métriques précédentes pour calculer les taux
        self._prev_net_io = None
        self._prev_disk_io = None
        self._prev_io_time = None
        self._process = None
        
        # Initialiser le process
        if HAS_PSUTIL:
            try:
                self._process = psutil.Process(os.getpid())
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                self._process = None
        
        # Initialiser les métriques
        self.reset_metrics()
        
        # Démarrer le monitoring si demandé
        if auto_start:
            self.start()
    
    def reset_metrics(self) -> None:
        """Réinitialise toutes les métriques système."""
        super().reset_metrics()
        
        # Métriques CPU
        self.update_metric("cpu_percent", 0.0)
        self.update_metric("cpu_count", psutil.cpu_count(logical=True) if HAS_PSUTIL else 0)
        self.update_metric("cpu_frequency", 0.0)
        
        # Métriques mémoire
        self.update_metric("memory_percent", 0.0)
        self.update_metric("memory_available", 0)
        self.update_metric("memory_used", 0)
        self.update_metric("memory_total", 0)
        
        # Métriques disque
        self.update_metric("disk_percent", 0.0)
        self.update_metric("disk_used", 0)
        self.update_metric("disk_total", 0)
        self.update_metric("disk_read_rate", 0.0)
        self.update_metric("disk_write_rate", 0.0)
        
        # Métriques réseau
        self.update_metric("net_sent_rate", 0.0)
        self.update_metric("net_recv_rate", 0.0)
        
        # Métriques processus
        self.update_metric("process_cpu_percent", 0.0)
        self.update_metric("process_memory_mb", 0.0)
        self.update_metric("process_io_read_rate", 0.0)
        self.update_metric("process_io_write_rate", 0.0)
        
        # Métriques système
        self.update_metric("system_boot_time", 0)
        self.update_metric("system_uptime", 0)
        
        # Métriques swap
        self.update_metric("swap_percent", 0.0)
        self.update_metric("swap_used", 0)
        self.update_metric("swap_total", 0)
    
    def collect_metrics(self) -> None:
        """Collecte toutes les métriques système."""
        if not HAS_PSUTIL:
            return
        
        # Timestamp actuel pour les calculs de taux
        current_time = time.time()
        
        # Collecter les métriques CPU
        self._collect_cpu_metrics()
        
        # Collecter les métriques mémoire
        self._collect_memory_metrics()
        
        # Collecter les métriques disque
        self._collect_disk_metrics()
        
        # Collecter les métriques réseau
        self._collect_network_metrics()
        
        # Collecter les métriques processus
        self._collect_process_metrics()
        
        # Collecter les métriques système
        self._collect_system_metrics()
        
        # Mettre à jour le timestamp pour les calculs de taux
        if self._prev_io_time is None:
            self._prev_io_time = current_time
    
    def _collect_cpu_metrics(self) -> None:
        """Collecte les métriques liées au CPU."""
        try:
            # Utilisation CPU globale
            cpu_percent = psutil.cpu_percent(interval=None)
            self.update_metric("cpu_percent", cpu_percent)
            
            # Nombre de cœurs CPU
            cpu_count = psutil.cpu_count(logical=True)
            self.update_metric("cpu_count", cpu_count)
            
            # Fréquence CPU
            if hasattr(psutil, "cpu_freq") and callable(getattr(psutil, "cpu_freq")):
                cpu_freq = psutil.cpu_freq()
                if cpu_freq:
                    self.update_metric("cpu_frequency", cpu_freq.current)
        except Exception as e:
            pass  # Ignorer les erreurs dans cette version simplifiée
    
    def _collect_memory_metrics(self) -> None:
        """Collecte les métriques liées à la mémoire."""
        try:
            # Mémoire virtuelle
            vm = psutil.virtual_memory()
            self.update_metric("memory_percent", vm.percent)
            self.update_metric("memory_available", vm.available)
            self.update_metric("memory_used", vm.total - vm.available)
            self.update_metric("memory_total", vm.total)
            
            # Mémoire swap
            if hasattr(psutil, "swap_memory") and callable(getattr(psutil, "swap_memory")):
                swap = psutil.swap_memory()
                self.update_metric("swap_percent", swap.percent)
                self.update_metric("swap_used", swap.used)
                self.update_metric("swap_total", swap.total)
        except Exception as e:
            pass  # Ignorer les erreurs dans cette version simplifiée
    
    def _collect_disk_metrics(self) -> None:
        """Collecte les métriques liées au disque."""
        try:
            # Utilisation disque
            disk = psutil.disk_usage("/")
            self.update_metric("disk_percent", disk.percent)
            self.update_metric("disk_used", disk.used)
            self.update_metric("disk_total", disk.total)
            
            # E/S disque
            current_time = time.time()
            if hasattr(psutil, "disk_io_counters") and callable(getattr(psutil, "disk_io_counters")):
                disk_io = psutil.disk_io_counters()
                
                if self._prev_disk_io is not None and self._prev_io_time is not None:
                    time_diff = current_time - self._prev_io_time
                    
                    if time_diff > 0:
                        read_rate = (disk_io.read_bytes - self._prev_disk_io.read_bytes) / time_diff
                        write_rate = (disk_io.write_bytes - self._prev_disk_io.write_bytes) / time_diff
                        
                        self.update_metric("disk_read_rate", read_rate)
                        self.update_metric("disk_write_rate", write_rate)
                
                self._prev_disk_io = disk_io
                self._prev_io_time = current_time
        except Exception as e:
            pass  # Ignorer les erreurs dans cette version simplifiée
    
    def _collect_network_metrics(self) -> None:
        """Collecte les métriques liées au réseau."""
        try:
            current_time = time.time()
            if hasattr(psutil, "net_io_counters") and callable(getattr(psutil, "net_io_counters")):
                net_io = psutil.net_io_counters()
                
                if self._prev_net_io is not None and self._prev_io_time is not None:
                    time_diff = current_time - self._prev_io_time
                    
                    if time_diff > 0:
                        sent_rate = (net_io.bytes_sent - self._prev_net_io.bytes_sent) / time_diff
                        recv_rate = (net_io.bytes_recv - self._prev_net_io.bytes_recv) / time_diff
                        
                        self.update_metric("net_sent_rate", sent_rate)
                        self.update_metric("net_recv_rate", recv_rate)
                
                self._prev_net_io = net_io
                self._prev_io_time = current_time
        except Exception as e:
            pass  # Ignorer les erreurs dans cette version simplifiée
    
    def _collect_process_metrics(self) -> None:
        """Collecte les métriques liées au processus actuel."""
        if self._process is None:
            return
        
        try:
            # CPU et mémoire
            process_cpu = self._process.cpu_percent(interval=None)
            process_memory = self._process.memory_info().rss / (1024 * 1024)  # MB
            
            self.update_metric("process_cpu_percent", process_cpu)
            self.update_metric("process_memory_mb", process_memory)
            
            # E/S processus
            if hasattr(self._process, "io_counters") and callable(getattr(self._process, "io_counters")):
                current_time = time.time()
                proc_io = self._process.io_counters()
                
                if hasattr(self, "_prev_proc_io") and hasattr(self, "_prev_proc_io_time"):
                    time_diff = current_time - self._prev_proc_io_time
                    
                    if time_diff > 0:
                        read_rate = (proc_io.read_bytes - self._prev_proc_io.read_bytes) / time_diff
                        write_rate = (proc_io.write_bytes - self._prev_proc_io.write_bytes) / time_diff
                        
                        self.update_metric("process_io_read_rate", read_rate)
                        self.update_metric("process_io_write_rate", write_rate)
                
                self._prev_proc_io = proc_io
                self._prev_proc_io_time = current_time
        except Exception as e:
            pass  # Ignorer les erreurs dans cette version simplifiée
    
    def _collect_system_metrics(self) -> None:
        """Collecte les métriques système générales."""
        try:
            # Heure de démarrage et uptime
            if hasattr(psutil, "boot_time") and callable(getattr(psutil, "boot_time")):
                boot_time = psutil.boot_time()
                uptime = time.time() - boot_time
                
                self.update_metric("system_boot_time", boot_time)
                self.update_metric("system_uptime", uptime)
        except Exception as e:
            pass  # Ignorer les erreurs dans cette version simplifiée
    
    def get_hardware_info(self) -> Dict[str, Any]:
        """
        Récupère les informations matérielles du système.
        
        Returns:
            Dict[str, Any]: Informations matérielles
        """
        info = {
            "os": platform.system(),
            "os_version": platform.version(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
        }
        
        if HAS_PSUTIL:
            # CPU
            info["cpu_count_physical"] = psutil.cpu_count(logical=False)
            info["cpu_count_logical"] = psutil.cpu_count(logical=True)
            
            # Mémoire
            vm = psutil.virtual_memory()
            info["memory_total"] = vm.total
            
            # Disque
            disk = psutil.disk_usage("/")
            info["disk_total"] = disk.total
        
        return info
    
    def optimize_system(self) -> Dict[str, Any]:
        """
        Applique des optimisations système basiques pour libérer des ressources.
        
        Returns:
            Dict[str, Any]: Résultats des optimisations
        """
        results = {
            "memory_before": self.get_metric("memory_percent"),
            "memory_after": None,
            "optimizations_applied": []
        }
        
        if not HAS_PSUTIL:
            return results
        
        try:
            # Libérer le cache du système si possible
            if platform.system() == "Linux":
                # Libérer les caches sur Linux
                try:
                    os.system("sync && echo 3 > /proc/sys/vm/drop_caches")
                    results["optimizations_applied"].append("linux_cache_drop")
                except Exception:
                    pass
            
            # Forcer la collecte des déchets de Python
            import gc
            gc.collect()
            results["optimizations_applied"].append("python_gc")
            
            # Mesurer l'utilisation de la mémoire après optimisation
            if HAS_PSUTIL:
                vm = psutil.virtual_memory()
                self.update_metric("memory_percent", vm.percent)
                results["memory_after"] = vm.percent
        
        except Exception as e:
            results["error"] = str(e)
        
        return results
    
    def set_all_thresholds(self, cpu: Optional[float] = None, memory: Optional[float] = None,
                           disk: Optional[float] = None, swap: Optional[float] = None) -> None:
        """
        Définit tous les seuils d'alerte en une seule opération.
        
        Args:
            cpu: Seuil d'utilisation CPU (%)
            memory: Seuil d'utilisation mémoire (%)
            disk: Seuil d'utilisation disque (%)
            swap: Seuil d'utilisation swap (%)
        """
        if cpu is not None:
            self.set_threshold("cpu_percent", cpu)
        
        if memory is not None:
            self.set_threshold("memory_percent", memory)
        
        if disk is not None:
            self.set_threshold("disk_percent", disk)
        
        if swap is not None:
            self.set_threshold("swap_percent", swap)

# Instance singleton pour un accès facile
_instance = None

def get_system_monitor() -> SystemMonitor:
    """
    Récupère l'instance singleton du moniteur système.
    
    Returns:
        SystemMonitor: Instance du moniteur système
    """
    global _instance
    if _instance is None:
        _instance = SystemMonitor()
    return _instance 