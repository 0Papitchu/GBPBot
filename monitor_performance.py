#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
GBPBot Performance Monitor
--------------------------
Ce script surveille les performances système pendant l'exécution de GBPBot.
Il enregistre l'utilisation du CPU, de la mémoire et du GPU (si disponible).
"""

import os
import sys
import time
import psutil
import logging
import argparse
import threading
import datetime
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from collections import deque

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("gbpbot_performance.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("GBPBot-Monitor")

# Taille maximale des données à conserver pour les graphiques
MAX_DATA_POINTS = 300  # 5 minutes à raison d'une mesure par seconde

class GPUMonitor:
    """Classe pour surveiller l'utilisation du GPU."""
    
    def __init__(self):
        self.gpu_available = False
        self.gpu_info = {}
        self._check_gpu()
    
    def _check_gpu(self):
        """Vérifie si un GPU compatible est disponible."""
        try:
            import torch
            if torch.cuda.is_available():
                self.gpu_available = True
                self.gpu_info['name'] = torch.cuda.get_device_name(0)
                self.gpu_info['count'] = torch.cuda.device_count()
                logger.info(f"GPU détecté: {self.gpu_info['name']}")
            else:
                logger.info("Aucun GPU compatible CUDA détecté")
        except ImportError:
            logger.info("PyTorch non installé, la surveillance GPU sera désactivée")
            
    def get_gpu_usage(self):
        """Obtient l'utilisation actuelle du GPU."""
        if not self.gpu_available:
            return None
            
        try:
            import subprocess
            import re
            
            # Pour NVIDIA GPUs
            result = subprocess.run(['nvidia-smi', '--query-gpu=utilization.gpu,memory.used,memory.total', '--format=csv,noheader,nounits'], 
                                   stdout=subprocess.PIPE, text=True)
            
            if result.returncode == 0:
                output = result.stdout.strip().split(',')
                if len(output) >= 3:
                    gpu_util = float(output[0].strip())
                    mem_used = float(output[1].strip())
                    mem_total = float(output[2].strip())
                    
                    return {
                        'utilization': gpu_util,
                        'memory_used': mem_used,
                        'memory_total': mem_total,
                        'memory_percent': (mem_used / mem_total) * 100 if mem_total > 0 else 0
                    }
            
            return None
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des données GPU: {e}")
            return None

class SystemMonitor:
    """Classe pour surveiller les ressources système."""
    
    def __init__(self, pid=None):
        self.pid = pid
        self.process = None
        self.gpu_monitor = GPUMonitor()
        
        if pid:
            try:
                self.process = psutil.Process(pid)
                logger.info(f"Surveillance du processus GBPBot (PID: {pid})")
            except psutil.NoSuchProcess:
                logger.error(f"Processus avec PID {pid} non trouvé")
                self.process = None
        
        # Initialisation des données pour les graphiques
        self.timestamps = deque(maxlen=MAX_DATA_POINTS)
        self.cpu_usage = deque(maxlen=MAX_DATA_POINTS)
        self.memory_usage = deque(maxlen=MAX_DATA_POINTS)
        self.gpu_usage = deque(maxlen=MAX_DATA_POINTS)
        self.gpu_memory = deque(maxlen=MAX_DATA_POINTS)
        
    def get_system_metrics(self):
        """Récupère les métriques système actuelles."""
        metrics = {
            'timestamp': datetime.datetime.now(),
            'cpu': psutil.cpu_percent(interval=0.1),
            'memory': psutil.virtual_memory().percent,
            'disk_io': psutil.disk_io_counters() if hasattr(psutil, 'disk_io_counters') else None,
        }
        
        # Ajouter les métriques GPU si disponibles
        gpu_data = self.gpu_monitor.get_gpu_usage()
        if gpu_data:
            metrics['gpu'] = gpu_data
            
        return metrics
        
    def get_process_metrics(self):
        """Récupère les métriques du processus GBPBot si disponible."""
        if not self.process:
            return None
            
        try:
            with self.process.oneshot():
                return {
                    'cpu': self.process.cpu_percent(interval=0.1),
                    'memory': self.process.memory_percent(),
                    'threads': self.process.num_threads(),
                    'io_counters': self.process.io_counters() if hasattr(self.process, 'io_counters') else None,
                }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            logger.error("Processus GBPBot non accessible ou terminé")
            self.process = None
            return None
            
    def update_data(self):
        """Met à jour les données pour les graphiques."""
        now = datetime.datetime.now()
        self.timestamps.append(now)
        
        # Métriques système
        sys_metrics = self.get_system_metrics()
        self.cpu_usage.append(sys_metrics['cpu'])
        self.memory_usage.append(sys_metrics['memory'])
        
        # Métriques GPU
        if 'gpu' in sys_metrics:
            self.gpu_usage.append(sys_metrics['gpu']['utilization'])
            self.gpu_memory.append(sys_metrics['gpu']['memory_percent'])
        else:
            self.gpu_usage.append(0)
            self.gpu_memory.append(0)
            
        # Enregistrer les métriques
        if len(self.timestamps) % 60 == 0:  # Log toutes les minutes
            logger.info(f"CPU: {sys_metrics['cpu']}%, Mémoire: {sys_metrics['memory']}%")
            if 'gpu' in sys_metrics:
                logger.info(f"GPU: {sys_metrics['gpu']['utilization']}%, Mémoire GPU: {sys_metrics['gpu']['memory_percent']}%")
                
        # Métriques du processus si disponible
        proc_metrics = self.get_process_metrics()
        if proc_metrics:
            if len(self.timestamps) % 60 == 0:  # Log toutes les minutes
                logger.info(f"GBPBot - CPU: {proc_metrics['cpu']}%, Mémoire: {proc_metrics['memory']}%")

def monitor_thread_function(system_monitor, stop_event):
    """Fonction exécutée par le thread de surveillance."""
    while not stop_event.is_set():
        system_monitor.update_data()
        time.sleep(1)  # Mise à jour toutes les secondes

def setup_plot(system_monitor):
    """Configure le graphique pour l'affichage en temps réel."""
    plt.style.use('dark_background')
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 8), sharex=True)
    fig.suptitle('GBPBot - Surveillance des Performances', fontsize=16)
    
    # Ligne pour le CPU
    line_cpu, = ax1.plot([], [], 'r-', linewidth=1.5, label='CPU %')
    ax1.set_ylabel('Utilisation CPU (%)')
    ax1.set_ylim(0, 100)
    ax1.grid(True, linestyle='--', alpha=0.7)
    ax1.legend(loc='upper left')
    
    # Ligne pour la mémoire
    line_mem, = ax2.plot([], [], 'b-', linewidth=1.5, label='Mémoire %')
    ax2.set_ylabel('Utilisation Mémoire (%)')
    ax2.set_ylim(0, 100)
    ax2.grid(True, linestyle='--', alpha=0.7)
    ax2.legend(loc='upper left')
    
    # Lignes pour le GPU
    line_gpu, = ax3.plot([], [], 'g-', linewidth=1.5, label='GPU %')
    line_gpu_mem, = ax3.plot([], [], 'y-', linewidth=1.5, label='Mémoire GPU %')
    ax3.set_ylabel('Utilisation GPU (%)')
    ax3.set_ylim(0, 100)
    ax3.grid(True, linestyle='--', alpha=0.7)
    ax3.legend(loc='upper left')
    
    ax3.set_xlabel('Temps')
    
    plt.tight_layout()
    plt.subplots_adjust(top=0.9)
    
    def update_plot(frame):
        # Mise à jour des données du graphique
        if system_monitor.timestamps:
            times = list(system_monitor.timestamps)
            
            # Mise à jour CPU
            line_cpu.set_data(times, system_monitor.cpu_usage)
            
            # Mise à jour mémoire
            line_mem.set_data(times, system_monitor.memory_usage)
            
            # Mise à jour GPU
            line_gpu.set_data(times, system_monitor.gpu_usage)
            line_gpu_mem.set_data(times, system_monitor.gpu_memory)
            
            # Ajustement de l'axe X
            for ax in [ax1, ax2, ax3]:
                ax.relim()
                ax.autoscale_view(scalex=True, scaley=False)
                
        return line_cpu, line_mem, line_gpu, line_gpu_mem
    
    ani = FuncAnimation(fig, update_plot, interval=1000, blit=True)
    return fig, ani

def find_gbpbot_pid():
    """Tente de trouver le PID du processus GBPBot."""
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            # Recherche des processus Python qui pourraient être GBPBot
            if proc.info['name'] == 'python' or proc.info['name'] == 'python.exe':
                cmdline = ' '.join(proc.info['cmdline']).lower()
                if 'gbpbot' in cmdline or 'main.py' in cmdline:
                    return proc.info['pid']
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return None

def main():
    parser = argparse.ArgumentParser(description='GBPBot Performance Monitor')
    parser.add_argument('--pid', type=int, help='PID du processus GBPBot à surveiller')
    parser.add_argument('--no-gui', action='store_true', help='Exécuter sans interface graphique')
    args = parser.parse_args()
    
    # Trouver le PID de GBPBot si non spécifié
    pid = args.pid
    if not pid:
        pid = find_gbpbot_pid()
        if pid:
            logger.info(f"GBPBot trouvé avec PID: {pid}")
        else:
            logger.warning("GBPBot non trouvé, surveillance du système uniquement")
    
    # Initialiser le moniteur système
    system_monitor = SystemMonitor(pid)
    
    # Créer un événement pour arrêter le thread de surveillance
    stop_event = threading.Event()
    
    # Démarrer le thread de surveillance
    monitor_thread = threading.Thread(target=monitor_thread_function, args=(system_monitor, stop_event))
    monitor_thread.daemon = True
    monitor_thread.start()
    
    try:
        if not args.no_gui:
            # Configurer et afficher le graphique
            fig, ani = setup_plot(system_monitor)
            plt.show()
        else:
            # Mode sans GUI, juste enregistrer les données
            logger.info("Mode sans GUI activé, surveillance en arrière-plan")
            while True:
                time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Arrêt de la surveillance...")
    finally:
        # Arrêter le thread de surveillance
        stop_event.set()
        monitor_thread.join(timeout=2)
        logger.info("Surveillance terminée")

if __name__ == "__main__":
    main() 