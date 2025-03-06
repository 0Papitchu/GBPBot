#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
GBPBot - Optimiseur Automatique
-------------------------------
Ce script surveille automatiquement les performances de GBPBot et
applique des ajustements d'optimisation si nécessaire.
"""

import os
import sys
import time
import json
import signal
import logging
import argparse
import subprocess
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple, Union

# Configuration du logging
log_file = f"auto_optimizer_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("GBPBot-AutoOptimizer")

# Variables globales
stop_event = threading.Event()
monitor_process = None
gbpbot_pid = None
optimization_interval = 30  # minutes
last_optimization = None
monitor_log_file = "gbpbot_performance.log"
env_file = ".env"

class ResourceMonitor:
    """Classe pour surveiller les ressources système."""
    
    def __init__(self):
        """Initialise le moniteur de ressources."""
        self.monitor_running = False
        self.monitor_thread = None
        self.monitor_process = None
    
    def start_monitor(self, no_gui: bool = False, gbpbot_pid: Optional[int] = None) -> bool:
        """Démarre le moniteur de performances en arrière-plan."""
        if self.monitor_running:
            logger.warning("Le moniteur est déjà en cours d'exécution")
            return True
        
        # Vérifier que le script du moniteur existe
        if not os.path.exists("monitor_performance.py"):
            logger.error("Le fichier monitor_performance.py est introuvable")
            return False
        
        # Construire la commande
        cmd = [sys.executable, "monitor_performance.py"]
        if no_gui:
            cmd.append("--no-gui")
        if gbpbot_pid:
            cmd.extend(["--pid", str(gbpbot_pid)])
        
        try:
            # Démarrer le moniteur en tant que processus séparé
            self.monitor_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
            )
            
            # Vérifier si le processus a démarré correctement
            if self.monitor_process.poll() is not None:  # Le processus s'est terminé immédiatement
                stdout, stderr = self.monitor_process.communicate()
                logger.error(f"Échec du démarrage du moniteur: {stderr}")
                return False
            
            logger.info(f"Moniteur de performances démarré (PID: {self.monitor_process.pid})")
            self.monitor_running = True
            
            # Démarrer un thread pour collecter la sortie du processus
            self.monitor_thread = threading.Thread(target=self._collect_monitor_output, daemon=True)
            self.monitor_thread.start()
            
            return True
        
        except Exception as e:
            logger.error(f"Erreur lors du démarrage du moniteur: {e}")
            return False
    
    def _collect_monitor_output(self) -> None:
        """Collecte la sortie du processus du moniteur."""
        if not self.monitor_process or not self.monitor_process.stdout:
            logger.error("Impossible de collecter la sortie du moniteur (stdout non disponible)")
            return
            
        while self.monitor_process and self.monitor_process.poll() is None:
            try:
                line = self.monitor_process.stdout.readline()
                if line:
                    logger.debug(f"Moniteur: {line.strip()}")
            except (ValueError, IOError):
                break
            except Exception as e:
                logger.error(f"Erreur lors de la lecture de la sortie du moniteur: {e}")
                break
    
    def stop_monitor(self) -> bool:
        """Arrête le moniteur de performances."""
        if not self.monitor_running or not self.monitor_process:
            logger.warning("Le moniteur n'est pas en cours d'exécution")
            return True
        
        try:
            # Envoyer un signal d'arrêt au processus
            if os.name == 'nt':
                self.monitor_process.send_signal(signal.CTRL_C_EVENT)
            else:
                self.monitor_process.send_signal(signal.SIGINT)
            
            # Attendre que le processus se termine
            try:
                self.monitor_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("Le moniteur ne répond pas, arrêt forcé")
                self.monitor_process.kill()
            
            logger.info("Moniteur de performances arrêté")
            self.monitor_running = False
            return True
        
        except Exception as e:
            logger.error(f"Erreur lors de l'arrêt du moniteur: {e}")
            return False

class PerformanceAnalyzer:
    """Classe pour analyser les performances système."""
    
    def __init__(self, log_file: str = monitor_log_file):
        """Initialise l'analyseur de performances."""
        self.log_file = log_file
        self.log_data: Dict[str, List[float]] = {
            'cpu': [],
            'memory': [],
            'gpu': [],
            'gpu_memory': []
        }
    
    def parse_log(self, time_window: int = 10) -> bool:
        """
        Analyse le fichier de log pour extraire les métriques de performance.
        
        Args:
            time_window (int): Fenêtre de temps en minutes pour filtrer les entrées
            
        Returns:
            bool: True si l'analyse a réussi, False sinon
        """
        if not os.path.exists(self.log_file):
            logger.error(f"Le fichier de log {self.log_file} est introuvable")
            return False
        
        # Réinitialiser les données
        for key in self.log_data:
            self.log_data[key] = []
        
        # Calculer le seuil de temps
        threshold_time = datetime.now() - timedelta(minutes=time_window)
        
        try:
            # Extraction des métriques du fichier log
            with open(self.log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        # Extraction de la date et de l'heure
                        timestamp_str = line.split(' - ')[0]
                        timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S,%f")
                        
                        # Filtrer par fenêtre de temps
                        if timestamp < threshold_time:
                            continue
                        
                        # Extraction des métriques
                        if "CPU:" in line:
                            cpu_match = line.split("CPU:")[1].split("%")[0].strip()
                            try:
                                cpu_value = float(cpu_match)
                                self.log_data['cpu'].append(cpu_value)
                            except ValueError:
                                pass
                        
                        if "Mémoire:" in line:
                            mem_match = line.split("Mémoire:")[1].split("%")[0].strip()
                            try:
                                mem_value = float(mem_match)
                                self.log_data['memory'].append(mem_value)
                            except ValueError:
                                pass
                        
                        if "GPU:" in line:
                            gpu_match = line.split("GPU:")[1].split("%")[0].strip()
                            try:
                                gpu_value = float(gpu_match)
                                self.log_data['gpu'].append(gpu_value)
                            except ValueError:
                                pass
                        
                        if "Mémoire GPU:" in line:
                            gpu_mem_match = line.split("Mémoire GPU:")[1].split("%")[0].strip()
                            try:
                                gpu_mem_value = float(gpu_mem_match)
                                self.log_data['gpu_memory'].append(gpu_mem_value)
                            except ValueError:
                                pass
                    
                    except Exception as e:
                        logger.debug(f"Erreur lors de l'analyse d'une ligne: {e}")
                        continue
            
            # Vérifier si des données ont été extraites
            data_found = False
            for values in self.log_data.values():
                if values:
                    data_found = True
                    break
            
            if not data_found:
                logger.warning(f"Aucune donnée de performance trouvée dans les {time_window} dernières minutes")
                return False
            
            logger.info(f"Analyse des logs de performance réussie ({len(self.log_data['cpu'])} entrées CPU, {len(self.log_data['memory'])} entrées mémoire)")
            return True
        
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse du fichier log: {e}")
            return False
    
    def get_performance_summary(self) -> Dict[str, Dict[str, float]]:
        """
        Calcule un résumé des performances système.
        
        Returns:
            Dict[str, Dict[str, float]]: Résumé des performances
        """
        summary: Dict[str, Dict[str, float]] = {}
        
        for metric, values in self.log_data.items():
            if values:
                summary[metric] = {
                    'min': min(values),
                    'max': max(values),
                    'avg': sum(values) / len(values),
                    'count': float(len(values))
                }
        
        return summary
    
    def needs_optimization(self, thresholds: Dict[str, float]) -> Tuple[bool, str]:
        """
        Détermine si des optimisations sont nécessaires.
        
        Args:
            thresholds (Dict[str, float]): Seuils d'utilisation des ressources
            
        Returns:
            Tuple[bool, str]: (Besoin d'optimisation, Raison)
        """
        summary = self.get_performance_summary()
        
        # Vérifier l'utilisation du CPU
        if 'cpu' in summary and summary['cpu']['avg'] > thresholds.get('cpu_high', 90):
            return True, f"Utilisation CPU élevée: {summary['cpu']['avg']:.1f}% (seuil: {thresholds.get('cpu_high', 90)}%)"
        
        # Vérifier l'utilisation de la mémoire
        if 'memory' in summary and summary['memory']['avg'] > thresholds.get('memory_high', 85):
            return True, f"Utilisation mémoire élevée: {summary['memory']['avg']:.1f}% (seuil: {thresholds.get('memory_high', 85)}%)"
        
        # Vérifier l'utilisation du GPU
        if 'gpu' in summary and summary['gpu']['avg'] > thresholds.get('gpu_high', 85):
            return True, f"Utilisation GPU élevée: {summary['gpu']['avg']:.1f}% (seuil: {thresholds.get('gpu_high', 85)}%)"
        
        # Vérifier l'utilisation de la mémoire GPU
        if 'gpu_memory' in summary and summary['gpu_memory']['avg'] > thresholds.get('gpu_memory_high', 85):
            return True, f"Utilisation mémoire GPU élevée: {summary['gpu_memory']['avg']:.1f}% (seuil: {thresholds.get('gpu_memory_high', 85)}%)"
        
        # Vérifier sous-utilisation du GPU
        if 'gpu' in summary and summary['gpu']['avg'] < thresholds.get('gpu_low', 20) and 'gpu' in self.log_data and len(self.log_data['gpu']) > 5:
            return True, f"Sous-utilisation GPU: {summary['gpu']['avg']:.1f}% (seuil: {thresholds.get('gpu_low', 20)}%)"
        
        return False, "Les performances sont normales"

class Optimizer:
    """Classe pour optimiser GBPBot en fonction des performances."""
    
    def __init__(self, env_file_path: str = env_file):
        """Initialise l'optimiseur."""
        self.env_file = env_file_path
        self.update_script = "update_optimizations.py"
    
    def apply_optimizations(self, force: bool = False, generate_report: bool = True) -> bool:
        """
        Applique les optimisations en fonction des performances actuelles.
        
        Args:
            force (bool): Force l'application des optimisations même si elles ne sont pas nécessaires
            generate_report (bool): Génère un rapport détaillé des optimisations
            
        Returns:
            bool: True si les optimisations ont été appliquées avec succès, False sinon
        """
        if not os.path.exists(self.update_script):
            logger.error(f"Le script d'optimisation {self.update_script} est introuvable")
            return False
        
        try:
            # Préparer la commande
            cmd = [sys.executable, self.update_script, "--apply"]
            if generate_report:
                cmd.append("--report")
            
            # Exécuter le script d'optimisation
            logger.info("Exécution du script d'optimisation...")
            process = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True
            )
            
            # Vérifier si les optimisations ont été appliquées
            if "Optimisations appliquées avec succès" in process.stdout:
                logger.info("Optimisations appliquées avec succès")
                return True
            else:
                logger.info("Aucune optimisation n'a été appliquée")
                return False
        
        except subprocess.CalledProcessError as e:
            logger.error(f"Erreur lors de l'exécution du script d'optimisation: {e.stderr}")
            return False
        
        except Exception as e:
            logger.error(f"Erreur lors de l'application des optimisations: {e}")
            return False

def find_gbpbot_pid() -> Optional[int]:
    """
    Trouve le PID du processus GBPBot.
    
    Returns:
        Optional[int]: PID du processus GBPBot, ou None s'il n'est pas trouvé
    """
    import psutil
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            # Recherche des processus Python qui pourraient être GBPBot
            if proc.info['name'] == 'python' or proc.info['name'] == 'python.exe':
                cmdline = ' '.join(proc.info['cmdline']).lower()
                if 'gbpbot' in cmdline or 'main.py' in cmdline:
                    logger.info(f"GBPBot trouvé avec PID: {proc.info['pid']}")
                    return proc.info['pid']
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    
    logger.warning("Aucun processus GBPBot trouvé")
    return None

def monitor_loop() -> None:
    """Boucle principale de surveillance et d'optimisation."""
    global last_optimization, gbpbot_pid
    
    # Trouver le PID de GBPBot s'il n'est pas déjà défini
    if not gbpbot_pid:
        gbpbot_pid = find_gbpbot_pid()
    
    # Initialiser les composants
    resource_monitor = ResourceMonitor()
    performance_analyzer = PerformanceAnalyzer()
    optimizer = Optimizer()
    
    # Démarrer le moniteur de performances
    if not resource_monitor.start_monitor(no_gui=True, gbpbot_pid=gbpbot_pid):
        logger.error("Impossible de démarrer le moniteur de performances")
        stop_event.set()
        return
    
    try:
        # Boucle principale
        while not stop_event.is_set():
            try:
                # Attendre que suffisamment de données soient collectées
                logger.info("Collecte des données de performances...")
                time.sleep(60)  # Attendre au moins 1 minute pour la collecte des données
                
                # Analyser les performances
                logger.info("Analyse des performances...")
                if not performance_analyzer.parse_log(time_window=5):
                    logger.warning("Impossible d'analyser les performances, tentative suivante dans 5 minutes")
                    time.sleep(300)
                    continue
                
                # Afficher le résumé des performances
                summary = performance_analyzer.get_performance_summary()
                for metric, stats in summary.items():
                    logger.info(f"{metric.upper()}: min={stats['min']:.1f}%, max={stats['max']:.1f}%, avg={stats['avg']:.1f}%, échantillons={stats['count']}")
                
                # Vérifier si des optimisations sont nécessaires
                needs_opt, reason = performance_analyzer.needs_optimization({
                    'cpu_high': 90,
                    'memory_high': 85,
                    'gpu_high': 85,
                    'gpu_memory_high': 85,
                    'cpu_low': 20,
                    'memory_low': 30,
                    'gpu_low': 20
                })
                
                # Si des optimisations sont nécessaires et que le dernier ajustement date d'il y a plus de X minutes
                current_time = datetime.now()
                optimization_needed = needs_opt and (
                    last_optimization is None or 
                    (current_time - last_optimization).total_seconds() / 60 >= optimization_interval
                )
                
                if optimization_needed:
                    logger.warning(f"Optimisation nécessaire: {reason}")
                    
                    # Appliquer les optimisations
                    if optimizer.apply_optimizations(generate_report=True):
                        last_optimization = current_time
                        logger.info(f"Optimisations appliquées. Prochaine optimisation possible dans {optimization_interval} minutes")
                    else:
                        logger.error("Échec de l'application des optimisations")
                
                elif needs_opt and last_optimization is not None:
                    minutes_to_wait = optimization_interval - (current_time - last_optimization).total_seconds() / 60
                    logger.info(f"Optimisation nécessaire ({reason}), mais doit attendre encore {minutes_to_wait:.1f} minutes")
                
                else:
                    logger.info(f"Pas d'optimisation nécessaire: {reason}")
                
                # Attendre avant la prochaine analyse
                logger.info(f"Prochaine analyse dans 5 minutes...")
                for _ in range(5):  # 5 minutes avec vérification toutes les minutes
                    if stop_event.is_set():
                        break
                    time.sleep(60)
            
            except Exception as e:
                logger.error(f"Erreur dans la boucle de surveillance: {e}")
                time.sleep(300)  # Attendre 5 minutes en cas d'erreur
    
    finally:
        # Arrêter le moniteur de performances
        resource_monitor.stop_monitor()

def signal_handler(sig, frame) -> None:
    """Gestionnaire de signal pour arrêter proprement le script."""
    logger.info("Signal d'arrêt reçu, arrêt en cours...")
    stop_event.set()

def main() -> int:
    """Fonction principale."""
    global optimization_interval, gbpbot_pid, monitor_log_file, env_file
    
    # Analyser les arguments de la ligne de commande
    parser = argparse.ArgumentParser(description='GBPBot - Optimiseur Automatique')
    parser.add_argument('--interval', type=int, default=30, help='Intervalle en minutes entre les optimisations')
    parser.add_argument('--pid', type=int, help='PID du processus GBPBot à surveiller')
    parser.add_argument('--log-file', default=monitor_log_file, help='Fichier de log du moniteur de performances')
    parser.add_argument('--env-file', default=env_file, help='Fichier .env à mettre à jour')
    args = parser.parse_args()
    
    # Mettre à jour les variables globales
    optimization_interval = args.interval
    monitor_log_file = args.log_file
    env_file = args.env_file
    if args.pid:
        gbpbot_pid = args.pid
    
    # Configurer le gestionnaire de signal
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("=== GBPBot - Optimiseur Automatique ===")
    logger.info(f"Intervalle d'optimisation: {optimization_interval} minutes")
    logger.info(f"Fichier log: {monitor_log_file}")
    logger.info(f"Fichier .env: {env_file}")
    
    try:
        # Démarrer la boucle de surveillance dans un thread séparé
        monitor_thread = threading.Thread(target=monitor_loop)
        monitor_thread.daemon = True
        monitor_thread.start()
        
        # Attendre que le thread se termine
        while monitor_thread.is_alive():
            try:
                monitor_thread.join(1)
            except (KeyboardInterrupt, SystemExit):
                logger.info("Interruption détectée, arrêt en cours...")
                stop_event.set()
                break
        
        logger.info("=== GBPBot - Optimiseur Automatique arrêté ===")
        return 0
    
    except Exception as e:
        logger.error(f"Erreur dans la fonction principale: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 