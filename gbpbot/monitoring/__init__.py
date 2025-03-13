"""
Module de Monitoring pour GBPBot
===============================

Ce package fournit des fonctionnalités pour surveiller et analyser les 
performances du système et du trading du GBPBot.

Il inclut:
- Monitoring des ressources système (CPU, mémoire, disque, réseau)
- Suivi des performances de trading (ROI, taux de réussite, profits/pertes)
- Alertes et notifications en cas de seuils dépassés
"""

import logging

# Configuration du logger
logger = logging.getLogger("gbpbot.monitoring")

# Import des sous-modules
from .system_monitor import SystemMonitor, get_system_monitor
from .performance_monitor import PerformanceMonitor, get_performance_monitor

# Fonction utilitaire pour initialiser tous les moniteurs
def initialize_monitoring(check_interval: float = 5.0, auto_start: bool = True) -> None:
    """
    Initialise tous les moniteurs avec les paramètres spécifiés.
    
    Args:
        check_interval: Intervalle entre les vérifications en secondes
        auto_start: Démarrer automatiquement les moniteurs
    """
    system_monitor = get_system_monitor()
    performance_monitor = get_performance_monitor()
    
    # Démarrer les moniteurs si demandé
    if auto_start:
        if hasattr(system_monitor, "start_monitoring"):
            system_monitor.start_monitoring(check_interval)
            logger.info(f"Moniteur système démarré avec intervalle de {check_interval}s")
    
    logger.info("Initialisation des moniteurs terminée")

# Exporter les classes et fonctions publiques
__all__ = [
    'SystemMonitor',
    'PerformanceMonitor',
    'get_system_monitor',
    'get_performance_monitor',
    'initialize_monitoring'
] 