#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Moniteur de Ressources Unifié pour GBPBot
=========================================

Ce module implémente un moniteur de ressources unifié qui consolide les fonctionnalités
des différentes implémentations précédentes (resource_monitor.py dans différents répertoires).
Il fournit des capacités de surveillance pour le CPU, la mémoire, le GPU, le réseau, et
les performances de trading.
"""

import os
import sys
import time
import logging
import psutil
import threading
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple, Callable
from collections import deque

from gbpbot.core.interfaces import BaseMonitor, MonitoringType

# Configuration du logger
logger = logging.getLogger("gbpbot.core.monitoring.resource_monitor")

class ResourceMonitor(BaseMonitor):
    """
    Moniteur de ressources unifié pour GBPBot.
    
    Cette classe consolide les fonctionnalités des différentes implémentations
    de moniteurs de ressources précédentes, offrant une interface cohérente
    pour surveiller les ressources système et les performances de trading.
    """
    
    def __init__(self):
        """
        Initialise le moniteur de ressources.
        """
        self.initialized = False
        self.running = False
        self.paused = False
        
        # Configuration par défaut
        self.config = {
            "monitoring_interval": 5.0,  # Intervalle de surveillance en secondes
            "metrics_history_size": 1000,  # Taille de l'historique des métriques
            "alert_enabled": True,  # Activer les alertes
            "log_to_file": True,  # Journaliser les métriques dans un fichier
            "log_file_path": "logs/resource_monitor.log",  # Chemin du fichier de journal
            "monitoring_types": [t for t in MonitoringType if t != MonitoringType.ALL]  # Tous sauf ALL
        }
        
        # État du moniteur
        self.monitoring_thread = None
        self.stop_event = threading.Event()
        self.metrics_lock = threading.Lock()
        
        # Stockage des métriques
        self.current_metrics = {}
        self.metrics_history = {}
        
        # Seuils d'alerte
        self.alert_thresholds = {}
        self.alert_callbacks = {}
        
        # Variables pour le monitoring GPU
        self.has_gpu = False
        self.gpu_info = {}
        
        # Dernier temps de mise à jour
        self.last_update_time = None
        
    def initialize(self, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Initialise le moniteur avec une configuration spécifique.
        
        Args:
            config: Configuration optionnelle pour le moniteur
            
        Returns:
            True si l'initialisation a réussi, False sinon
        """
        try:
            if config:
                # Mettre à jour la configuration avec les valeurs fournies
                for key, value in config.items():
                    if key in self.config:
                        self.config[key] = value
            
            # Créer le répertoire de logs si nécessaire
            if self.config["log_to_file"]:
                log_dir = os.path.dirname(self.config["log_file_path"])
                if log_dir and not os.path.exists(log_dir):
                    os.makedirs(log_dir)
            
            # Initialiser l'historique des métriques
            for monitoring_type in self.config["monitoring_types"]:
                self.metrics_history[monitoring_type.name] = deque(maxlen=self.config["metrics_history_size"])
            
            # Détecter le GPU si disponible
            self.detect_gpu()
            
            # Initialiser les métriques actuelles
            self._update_metrics()
            
            self.initialized = True
            logger.info("Moniteur de ressources initialisé avec succès")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du moniteur de ressources: {str(e)}")
            return False
    
    def start(self, monitoring_types: Optional[List[MonitoringType]] = None) -> bool:
        """
        Démarre le monitoring des ressources spécifiées.
        
        Args:
            monitoring_types: Types de monitoring à activer (par défaut: tous configurés)
            
        Returns:
            True si le démarrage a réussi, False sinon
        """
        if not self.initialized:
            logger.error("Le moniteur doit être initialisé avant de démarrer")
            return False
        
        if self.running:
            logger.warning("Le moniteur est déjà en cours d'exécution")
            return True
        
        try:
            # Si des types spécifiques sont fournis, mettre à jour la configuration
            if monitoring_types:
                self.config["monitoring_types"] = monitoring_types
            
            # Réinitialiser l'événement d'arrêt
            self.stop_event.clear()
            
            # Démarrer le thread de surveillance
            self.monitoring_thread = threading.Thread(
                target=self._monitoring_loop,
                daemon=True
            )
            self.monitoring_thread.start()
            
            self.running = True
            self.paused = False
            
            logger.info(f"Moniteur de ressources démarré pour les types: {[t.name for t in self.config['monitoring_types']]}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors du démarrage du moniteur de ressources: {str(e)}")
            return False
    
    def stop(self, monitoring_types: Optional[List[MonitoringType]] = None) -> bool:
        """
        Arrête le monitoring des ressources spécifiées.
        
        Args:
            monitoring_types: Types de monitoring à désactiver (par défaut: tous)
            
        Returns:
            True si l'arrêt a réussi, False sinon
        """
        if not self.running:
            logger.warning("Le moniteur n'est pas en cours d'exécution")
            return True
        
        try:
            # Si des types spécifiques sont fournis, on les désactive uniquement
            if monitoring_types:
                for monitoring_type in monitoring_types:
                    if monitoring_type in self.config["monitoring_types"]:
                        self.config["monitoring_types"].remove(monitoring_type)
                
                # S'il reste des types à surveiller, on continue
                if self.config["monitoring_types"]:
                    logger.info(f"Types de monitoring désactivés: {[t.name for t in monitoring_types]}")
                    return True
            
            # Sinon, on arrête complètement le monitoring
            self.stop_event.set()
            
            if self.monitoring_thread and self.monitoring_thread.is_alive():
                self.monitoring_thread.join(timeout=5.0)
            
            self.running = False
            self.paused = False
            
            logger.info("Moniteur de ressources arrêté")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'arrêt du moniteur de ressources: {str(e)}")
            return False
    
    def pause(self, monitoring_types: Optional[List[MonitoringType]] = None) -> bool:
        """
        Met en pause le monitoring des ressources spécifiées
        sans arrêter complètement le système.
        
        Args:
            monitoring_types: Types de monitoring à mettre en pause (par défaut: tous)
            
        Returns:
            True si la mise en pause a réussi, False sinon
        """
        if not self.running or self.paused:
            logger.warning("Le moniteur n'est pas en cours d'exécution ou est déjà en pause")
            return True
        
        try:
            # Si des types spécifiques sont fournis, on les désactive temporairement
            if monitoring_types:
                self._paused_types = [t for t in monitoring_types if t in self.config["monitoring_types"]]
                for monitoring_type in self._paused_types:
                    self.config["monitoring_types"].remove(monitoring_type)
                
                if not self._paused_types:
                    logger.warning("Aucun des types spécifiés n'était actif")
                    return True
                
                logger.info(f"Types de monitoring mis en pause: {[t.name for t in self._paused_types]}")
                return True
            
            # Sinon, on met en pause complètement le monitoring
            self.paused = True
            logger.info("Moniteur de ressources mis en pause")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la mise en pause du moniteur de ressources: {str(e)}")
            return False
    
    def resume(self, monitoring_types: Optional[List[MonitoringType]] = None) -> bool:
        """
        Reprend le monitoring des ressources spécifiées après une pause.
        
        Args:
            monitoring_types: Types de monitoring à reprendre (par défaut: tous)
            
        Returns:
            True si la reprise a réussi, False sinon
        """
        if not self.running:
            logger.warning("Le moniteur n'est pas en cours d'exécution")
            return False
        
        try:
            # Si des types spécifiques sont fournis, on les réactive
            if monitoring_types and hasattr(self, '_paused_types'):
                for monitoring_type in monitoring_types:
                    if monitoring_type in self._paused_types:
                        self.config["monitoring_types"].append(monitoring_type)
                        self._paused_types.remove(monitoring_type)
                
                logger.info(f"Types de monitoring repris: {[t.name for t in monitoring_types]}")
                return True
            
            # Sinon, on reprend complètement le monitoring
            self.paused = False
            logger.info("Moniteur de ressources repris")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la reprise du moniteur de ressources: {str(e)}")
            return False
    
    def get_current_metrics(self, monitoring_types: Optional[List[MonitoringType]] = None) -> Dict[str, Any]:
        """
        Récupère les métriques actuelles du système.
        
        Args:
            monitoring_types: Types de monitoring dont on veut les métriques (par défaut: tous configurés)
            
        Returns:
            Dictionnaire contenant les métriques actuelles
        """
        if not self.initialized:
            logger.warning("Le moniteur n'a pas été initialisé")
            return {}
        
        try:
            # Si le moniteur n'est pas en cours d'exécution, mettre à jour manuellement
            if not self.running or self.paused:
                self._update_metrics()
            
            # Si des types spécifiques sont fournis, filtrer les métriques
            if monitoring_types:
                return {k: v for k, v in self.current_metrics.items() 
                        if any(k.startswith(t.name.lower()) for t in monitoring_types)}
            
            return self.current_metrics.copy()
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des métriques actuelles: {str(e)}")
            return {}
    
    def get_metrics_history(self, 
                           start_time: Optional[datetime] = None,
                           end_time: Optional[datetime] = None,
                           monitoring_types: Optional[List[MonitoringType]] = None,
                           aggregation: Optional[str] = None) -> Dict[str, Any]:
        """
        Récupère l'historique des métriques sur une période donnée.
        
        Args:
            start_time: Début de la période (par défaut: 1 heure avant now)
            end_time: Fin de la période (par défaut: now)
            monitoring_types: Types de monitoring dont on veut l'historique
            aggregation: Méthode d'agrégation des données (avg, min, max, sum)
            
        Returns:
            Dictionnaire contenant l'historique des métriques
        """
        if not self.initialized:
            logger.warning("Le moniteur n'a pas été initialisé")
            return {}
        
        try:
            # Définir les temps par défaut si non fournis
            if not end_time:
                end_time = datetime.now()
            if not start_time:
                start_time = end_time - timedelta(hours=1)
            
            # Filtrer les types de monitoring si spécifiés
            history_types = monitoring_types or [t for t in self.config["monitoring_types"]]
            history_types = [t.name for t in history_types if t != MonitoringType.ALL]
            
            result = {}
            
            # Pour chaque type de monitoring, récupérer l'historique
            for type_name in history_types:
                if type_name in self.metrics_history:
                    # Filtrer par plage de temps
                    filtered_history = [
                        entry for entry in self.metrics_history[type_name]
                        if start_time <= entry.get('timestamp', datetime.min) <= end_time
                    ]
                    
                    # Appliquer l'agrégation si demandée
                    if aggregation and filtered_history:
                        result[type_name] = self._aggregate_metrics(filtered_history, aggregation)
                    else:
                        result[type_name] = filtered_history
            
            return result
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de l'historique des métriques: {str(e)}")
            return {}
    
    def set_alert_threshold(self, metric_name: str, threshold: float, 
                           callback: Optional[Callable[[str, float, float], None]] = None) -> bool:
        """
        Définit un seuil d'alerte pour une métrique spécifique.
        
        Args:
            metric_name: Nom de la métrique
            threshold: Valeur du seuil
            callback: Fonction à appeler lorsque le seuil est dépassé
            
        Returns:
            True si le seuil a été défini avec succès, False sinon
        """
        try:
            self.alert_thresholds[metric_name] = threshold
            
            if callback:
                self.alert_callbacks[metric_name] = callback
            elif metric_name in self.alert_callbacks:
                # Supprimer le callback existant si aucun n'est fourni
                del self.alert_callbacks[metric_name]
            
            logger.info(f"Seuil d'alerte défini pour {metric_name}: {threshold}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la définition du seuil d'alerte: {str(e)}")
            return False
    
    def remove_alert_threshold(self, metric_name: str) -> bool:
        """
        Supprime un seuil d'alerte pour une métrique spécifique.
        
        Args:
            metric_name: Nom de la métrique
            
        Returns:
            True si le seuil a été supprimé avec succès, False sinon
        """
        try:
            if metric_name in self.alert_thresholds:
                del self.alert_thresholds[metric_name]
                
                if metric_name in self.alert_callbacks:
                    del self.alert_callbacks[metric_name]
                
                logger.info(f"Seuil d'alerte supprimé pour {metric_name}")
                return True
            else:
                logger.warning(f"Aucun seuil d'alerte défini pour {metric_name}")
                return False
            
        except Exception as e:
            logger.error(f"Erreur lors de la suppression du seuil d'alerte: {str(e)}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """
        Récupère l'état actuel du moniteur.
        
        Returns:
            État actuel du moniteur
        """
        return {
            "initialized": self.initialized,
            "running": self.running,
            "paused": self.paused,
            "monitoring_types": [t.name for t in self.config["monitoring_types"]],
            "alert_thresholds": self.alert_thresholds.copy(),
            "last_update_time": self.last_update_time,
            "config": self.config.copy()
        }
    
    def configure(self, new_config: Dict[str, Any]) -> bool:
        """
        Reconfigure le moniteur pendant son fonctionnement.
        
        Args:
            new_config: Nouvelle configuration à appliquer
            
        Returns:
            True si la reconfiguration a réussi, False sinon
        """
        try:
            was_running = self.running
            
            # Arrêter le monitoring si nécessaire
            if was_running:
                self.stop()
            
            # Mettre à jour la configuration
            for key, value in new_config.items():
                if key in self.config:
                    self.config[key] = value
            
            # Redémarrer le monitoring si nécessaire
            if was_running:
                self.start()
            
            logger.info("Moniteur de ressources reconfiguré avec succès")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la reconfiguration du moniteur de ressources: {str(e)}")
            return False
    
    def get_recommendations(self) -> Dict[str, Any]:
        """
        Récupère des recommandations d'optimisation basées sur les métriques.
        
        Returns:
            Dictionnaire contenant des recommandations d'optimisation
        """
        if not self.initialized:
            logger.warning("Le moniteur n'a pas été initialisé")
            return {}
        
        try:
            recommendations = {}
            metrics = self.get_current_metrics()
            
            # Recommandations sur l'utilisation du CPU
            if 'system_cpu_percent' in metrics:
                cpu_usage = metrics['system_cpu_percent']
                if cpu_usage > 90:
                    recommendations['cpu'] = "Utilisation CPU très élevée. Considérez réduire le nombre de threads ou augmenter l'intervalle de vérification."
                elif cpu_usage > 75:
                    recommendations['cpu'] = "Utilisation CPU élevée. Surveillez les performances et ajustez les paramètres si nécessaire."
            
            # Recommandations sur l'utilisation de la mémoire
            if 'system_memory_percent' in metrics:
                memory_usage = metrics['system_memory_percent']
                if memory_usage > 90:
                    recommendations['memory'] = "Utilisation mémoire très élevée. Risque de OOM. Réduisez la taille des caches ou le nombre de pairs surveillées."
                elif memory_usage > 80:
                    recommendations['memory'] = "Utilisation mémoire élevée. Considérez optimiser l'utilisation mémoire."
            
            # Recommandations sur l'utilisation du GPU
            if 'system_gpu_percent' in metrics and self.has_gpu:
                gpu_usage = metrics['system_gpu_percent']
                if gpu_usage > 95:
                    recommendations['gpu'] = "Utilisation GPU très élevée. Considérez désactiver certains modèles ML ou réduire la taille des batchs."
            
            # Recommandations sur les performances réseau
            if 'network_latency_avg' in metrics:
                latency = metrics['network_latency_avg']
                if latency > 1000:  # Plus de 1000ms
                    recommendations['network'] = "Latence réseau très élevée. Vérifiez votre connexion ou changez de RPC."
                elif latency > 500:  # Plus de 500ms
                    recommendations['network'] = "Latence réseau élevée. Considérez utiliser un RPC plus rapide."
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des recommandations: {str(e)}")
            return {}
    
    def _monitoring_loop(self):
        """
        Boucle principale de surveillance des ressources.
        """
        logger.info("Démarrage de la boucle de surveillance des ressources")
        
        while not self.stop_event.is_set():
            try:
                # Si le moniteur est en pause, attendre
                if self.paused:
                    time.sleep(1.0)
                    continue
                
                # Mettre à jour les métriques
                self._update_metrics()
                
                # Vérifier les seuils d'alerte
                if self.config["alert_enabled"]:
                    self._check_alerts()
                
                # Journaliser les métriques si demandé
                if self.config["log_to_file"]:
                    self._log_metrics()
                
                # Attendre l'intervalle configuré
                time.sleep(self.config["monitoring_interval"])
                
            except Exception as e:
                logger.error(f"Erreur dans la boucle de surveillance: {str(e)}")
                time.sleep(5.0)  # Attendre un peu plus longtemps en cas d'erreur
        
        logger.info("Boucle de surveillance des ressources arrêtée")
    
    def _update_metrics(self):
        """
        Met à jour les métriques actuelles du système.
        """
        with self.metrics_lock:
            now = datetime.now()
            self.last_update_time = now
            
            # Pour chaque type de monitoring activé
            for monitoring_type in self.config["monitoring_types"]:
                if monitoring_type == MonitoringType.ALL:
                    continue
                
                metrics = {}
                
                # Collecter les métriques en fonction du type
                if monitoring_type == MonitoringType.SYSTEM:
                    metrics.update(self._collect_system_metrics())
                elif monitoring_type == MonitoringType.NETWORK:
                    metrics.update(self._collect_network_metrics())
                elif monitoring_type == MonitoringType.TRADING:
                    metrics.update(self._collect_trading_metrics())
                elif monitoring_type == MonitoringType.PERFORMANCE:
                    metrics.update(self._collect_performance_metrics())
                elif monitoring_type == MonitoringType.BLOCKCHAIN:
                    metrics.update(self._collect_blockchain_metrics())
                elif monitoring_type == MonitoringType.SECURITY:
                    metrics.update(self._collect_security_metrics())
                
                # Ajouter les métriques aux métriques actuelles
                self.current_metrics.update(metrics)
                
                # Ajouter les métriques à l'historique
                if metrics:
                    entry = metrics.copy()
                    entry['timestamp'] = now
                    self.metrics_history[monitoring_type.name].append(entry)
    
    def _collect_system_metrics(self) -> Dict[str, Any]:
        """
        Collecte les métriques système (CPU, mémoire, disque, GPU).
        
        Returns:
            Métriques système
        """
        metrics = {}
        
        # CPU
        metrics['system_cpu_percent'] = psutil.cpu_percent(interval=None)
        metrics['system_cpu_count'] = psutil.cpu_count(logical=True)
        
        # Mémoire
        memory = psutil.virtual_memory()
        metrics['system_memory_total'] = memory.total
        metrics['system_memory_available'] = memory.available
        metrics['system_memory_used'] = memory.used
        metrics['system_memory_percent'] = memory.percent
        
        # Disque
        disk = psutil.disk_usage('/')
        metrics['system_disk_total'] = disk.total
        metrics['system_disk_used'] = disk.used
        metrics['system_disk_free'] = disk.free
        metrics['system_disk_percent'] = disk.percent
        
        # GPU si disponible
        if self.has_gpu:
            metrics.update(self._collect_gpu_metrics())
        
        return metrics
    
    def _collect_network_metrics(self) -> Dict[str, Any]:
        """
        Collecte les métriques réseau.
        
        Returns:
            Métriques réseau
        """
        metrics = {}
        
        # Statistiques réseau
        net_io = psutil.net_io_counters()
        metrics['network_bytes_sent'] = net_io.bytes_sent
        metrics['network_bytes_recv'] = net_io.bytes_recv
        metrics['network_packets_sent'] = net_io.packets_sent
        metrics['network_packets_recv'] = net_io.packets_recv
        
        # Mesure de latence (simulée ici)
        # Dans une implémentation réelle, on pourrait ping les RPC
        metrics['network_latency_avg'] = 100.0  # ms
        
        return metrics
    
    def _collect_trading_metrics(self) -> Dict[str, Any]:
        """
        Collecte les métriques liées au trading.
        
        Returns:
            Métriques de trading
        """
        # Note: Ces métriques devraient être fournies par les modules de trading
        # Ici, nous retournons des valeurs fictives pour l'exemple
        return {
            'trading_transactions_count': 0,
            'trading_success_rate': 0.0,
            'trading_profit_usd': 0.0,
            'trading_volume_usd': 0.0,
            'trading_active_pairs': 0
        }
    
    def _collect_performance_metrics(self) -> Dict[str, Any]:
        """
        Collecte les métriques de performance du bot.
        
        Returns:
            Métriques de performance
        """
        # Note: Ces métriques devraient être fournies par les modules correspondants
        # Ici, nous retournons des valeurs fictives pour l'exemple
        return {
            'performance_avg_execution_time': 0.0,
            'performance_max_execution_time': 0.0,
            'performance_min_execution_time': 0.0,
            'performance_request_count': 0,
            'performance_error_rate': 0.0
        }
    
    def _collect_blockchain_metrics(self) -> Dict[str, Any]:
        """
        Collecte les métriques liées aux blockchains.
        
        Returns:
            Métriques blockchain
        """
        # Note: Ces métriques devraient être fournies par les clients blockchain
        # Ici, nous retournons des valeurs fictives pour l'exemple
        return {
            'blockchain_solana_tps': 0,
            'blockchain_solana_gas_price': 0.0,
            'blockchain_avax_gas_price': 0.0,
            'blockchain_sonic_gas_price': 0.0
        }
    
    def _collect_security_metrics(self) -> Dict[str, Any]:
        """
        Collecte les métriques liées à la sécurité.
        
        Returns:
            Métriques de sécurité
        """
        # Note: Ces métriques devraient être fournies par les modules de sécurité
        # Ici, nous retournons des valeurs fictives pour l'exemple
        return {
            'security_anomalies_detected': 0,
            'security_blocked_requests': 0,
            'security_safety_score': 100.0
        }
    
    def _collect_gpu_metrics(self) -> Dict[str, Any]:
        """
        Collecte les métriques GPU si disponible.
        
        Returns:
            Métriques GPU
        """
        metrics = {}
        
        try:
            # Tenter d'utiliser pynvml pour NVIDIA
            import pynvml
            pynvml.nvmlInit()
            
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            
            # Utilisation du GPU
            utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
            metrics['system_gpu_percent'] = utilization.gpu
            
            # Mémoire GPU
            memory = pynvml.nvmlDeviceGetMemoryInfo(handle)
            metrics['system_gpu_memory_total'] = memory.total
            metrics['system_gpu_memory_used'] = memory.used
            metrics['system_gpu_memory_free'] = memory.free
            metrics['system_gpu_memory_percent'] = (memory.used / memory.total) * 100.0
            
            # Température
            metrics['system_gpu_temperature'] = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
            
            pynvml.nvmlShutdown()
            
        except ImportError:
            logger.debug("pynvml non disponible, impossible de collecter les métriques GPU NVIDIA")
        except Exception as e:
            logger.debug(f"Erreur lors de la collecte des métriques GPU: {str(e)}")
            
            # Utiliser des valeurs par défaut
            if self.has_gpu:
                metrics['system_gpu_percent'] = 0.0
                metrics['system_gpu_memory_percent'] = 0.0
        
        return metrics
    
    def _check_alerts(self):
        """
        Vérifie les seuils d'alerte et déclenche les callbacks si nécessaire.
        """
        for metric_name, threshold in self.alert_thresholds.items():
            if metric_name in self.current_metrics:
                current_value = self.current_metrics[metric_name]
                
                # Vérifier si le seuil est dépassé
                if current_value > threshold:
                    # Journaliser l'alerte
                    logger.warning(f"Alerte: {metric_name} = {current_value} > {threshold}")
                    
                    # Appeler le callback si défini
                    if metric_name in self.alert_callbacks:
                        try:
                            self.alert_callbacks[metric_name](metric_name, current_value, threshold)
                        except Exception as e:
                            logger.error(f"Erreur lors de l'appel du callback pour {metric_name}: {str(e)}")
    
    def _log_metrics(self):
        """
        Journalise les métriques actuelles dans un fichier.
        """
        if not self.config["log_to_file"]:
            return
        
        try:
            # Format simple pour le journal
            log_line = f"{datetime.now().isoformat()} - "
            log_line += ", ".join([f"{k}={v}" for k, v in self.current_metrics.items()])
            
            # Écrire dans le fichier
            with open(self.config["log_file_path"], 'a') as f:
                f.write(log_line + "\n")
                
        except Exception as e:
            logger.error(f"Erreur lors de la journalisation des métriques: {str(e)}")
    
    def _aggregate_metrics(self, metrics_list: List[Dict[str, Any]], aggregation: str) -> Dict[str, Any]:
        """
        Agrège une liste de métriques selon la méthode spécifiée.
        
        Args:
            metrics_list: Liste de dictionnaires de métriques
            aggregation: Méthode d'agrégation (avg, min, max, sum)
            
        Returns:
            Métriques agrégées
        """
        if not metrics_list:
            return {}
        
        result = {}
        
        # Extraire tous les noms de métriques
        metric_names = set()
        for metrics in metrics_list:
            metric_names.update(metrics.keys())
        
        # Pour chaque métrique, appliquer l'agrégation
        for name in metric_names:
            if name == 'timestamp':
                continue
                
            values = [m.get(name) for m in metrics_list if name in m and isinstance(m.get(name), (int, float))]
            
            if not values:
                continue
                
            if aggregation == 'avg':
                result[name] = sum(values) / len(values)
            elif aggregation == 'min':
                result[name] = min(values)
            elif aggregation == 'max':
                result[name] = max(values)
            elif aggregation == 'sum':
                result[name] = sum(values)
            else:
                result[name] = values[-1]  # Dernière valeur par défaut
        
        return result
    
    def detect_gpu(self):
        """
        Détecte la présence d'un GPU et collecte ses informations.
        """
        self.has_gpu = False
        self.gpu_info = {}
        
        try:
            # Tenter d'utiliser pynvml pour NVIDIA
            import pynvml
            pynvml.nvmlInit()
            
            device_count = pynvml.nvmlDeviceGetCount()
            if device_count > 0:
                self.has_gpu = True
                
                # Obtenir les informations du premier GPU
                handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                
                # Nom du GPU
                self.gpu_info['name'] = pynvml.nvmlDeviceGetName(handle).decode('utf-8')
                
                # Mémoire
                memory = pynvml.nvmlDeviceGetMemoryInfo(handle)
                self.gpu_info['memory_total'] = memory.total
                
                # Version du driver
                self.gpu_info['driver_version'] = pynvml.nvmlSystemGetDriverVersion().decode('utf-8')
                
                logger.info(f"GPU détecté: {self.gpu_info['name']} avec {memory.total / (1024**3):.2f} Go de VRAM")
            
            pynvml.nvmlShutdown()
            
        except ImportError:
            logger.debug("pynvml non disponible, tentative avec Windows WMI")
            
            # Essayer avec WMI sur Windows
            if sys.platform == 'win32':
                try:
                    import wmi
                    computer = wmi.WMI()
                    gpu_info = computer.Win32_VideoController()[0]
                    
                    self.has_gpu = True
                    self.gpu_info['name'] = gpu_info.Name
                    self.gpu_info['memory_total'] = int(getattr(gpu_info, 'AdapterRAM', 0))
                    
                    logger.info(f"GPU détecté via WMI: {self.gpu_info['name']}")
                    
                except ImportError:
                    logger.debug("wmi non disponible")
                except Exception as e:
                    logger.debug(f"Erreur lors de la détection du GPU via WMI: {str(e)}")
        
        except Exception as e:
            logger.debug(f"Erreur lors de la détection du GPU: {str(e)}")
        
        return self.has_gpu 