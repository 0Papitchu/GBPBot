#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pour démarrer le dashboard de monitoring de GBPBot en mode autonome.
Ce script permet de lancer le dashboard indépendamment du bot, pour surveiller
un bot déjà en cours d'exécution.
"""

import os
import sys
import argparse
import logging
import yaml
import asyncio
import signal
import json
from pathlib import Path
from datetime import datetime

# Ajout du répertoire parent au path pour pouvoir importer les modules du projet
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from gbpbot.core.monitoring.dashboard import DashboardServer
    from gbpbot.core.monitoring.advanced_monitor import AdvancedMonitor
    from gbpbot.core.config import load_config
except ImportError as e:
    print(f"Erreur d'importation: {e}")
    print("Assurez-vous que le projet GBPBot est correctement installé.")
    sys.exit(1)

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"logs/dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    ]
)
logger = logging.getLogger("dashboard")

class DashboardStarter:
    """Classe pour gérer le démarrage et l'exécution du dashboard."""
    
    def __init__(self, config_path, data_dir, port, log_level):
        """
        Initialise le gestionnaire de dashboard.
        
        Args:
            config_path (str): Chemin vers le fichier de configuration
            data_dir (str): Répertoire contenant les données du bot
            port (int): Port sur lequel démarrer le dashboard
            log_level (str): Niveau de logging
        """
        self.config_path = config_path
        self.data_dir = Path(data_dir)
        self.port = port
        
        # Configuration du niveau de logging
        numeric_level = getattr(logging, log_level.upper(), None)
        if isinstance(numeric_level, int):
            logger.setLevel(numeric_level)
        
        # Chargement de la configuration
        self.config = self._load_config()
        
        # Initialisation des composants
        self.dashboard = None
        self.monitor = None
        self.running = False
        
        # Configuration des gestionnaires de signaux
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _load_config(self):
        """Charge la configuration depuis le fichier YAML."""
        try:
            config = load_config(self.config_path)
            logger.info(f"Configuration chargée depuis {self.config_path}")
            return config
        except Exception as e:
            logger.error(f"Erreur lors du chargement de la configuration: {e}")
            sys.exit(1)
    
    def _load_metrics_data(self):
        """
        Charge les données de métriques depuis les fichiers de données.
        Cela permet au dashboard de fonctionner en mode observateur.
        """
        metrics = {
            "market": {},
            "performance": {},
            "system": {},
            "errors": [],
            "trades": []
        }
        
        # Chargement des métriques de marché
        market_file = self.data_dir / "market_metrics.json"
        if market_file.exists():
            try:
                with open(market_file, 'r') as f:
                    metrics["market"] = json.load(f)
                logger.info(f"Métriques de marché chargées depuis {market_file}")
            except Exception as e:
                logger.warning(f"Erreur lors du chargement des métriques de marché: {e}")
        
        # Chargement des métriques de performance
        perf_file = self.data_dir / "performance_metrics.json"
        if perf_file.exists():
            try:
                with open(perf_file, 'r') as f:
                    metrics["performance"] = json.load(f)
                logger.info(f"Métriques de performance chargées depuis {perf_file}")
            except Exception as e:
                logger.warning(f"Erreur lors du chargement des métriques de performance: {e}")
        
        # Chargement des métriques système
        sys_file = self.data_dir / "system_metrics.json"
        if sys_file.exists():
            try:
                with open(sys_file, 'r') as f:
                    metrics["system"] = json.load(f)
                logger.info(f"Métriques système chargées depuis {sys_file}")
            except Exception as e:
                logger.warning(f"Erreur lors du chargement des métriques système: {e}")
        
        # Chargement de l'historique des erreurs
        errors_file = self.data_dir / "error_history.json"
        if errors_file.exists():
            try:
                with open(errors_file, 'r') as f:
                    metrics["errors"] = json.load(f)
                logger.info(f"Historique des erreurs chargé depuis {errors_file}")
            except Exception as e:
                logger.warning(f"Erreur lors du chargement de l'historique des erreurs: {e}")
        
        # Chargement de l'historique des trades
        trades_file = self.data_dir / "trade_history.json"
        if trades_file.exists():
            try:
                with open(trades_file, 'r') as f:
                    metrics["trades"] = json.load(f)
                logger.info(f"Historique des trades chargé depuis {trades_file}")
            except Exception as e:
                logger.warning(f"Erreur lors du chargement de l'historique des trades: {e}")
        
        return metrics
    
    def _signal_handler(self, sig, frame):
        """Gestionnaire de signaux pour arrêter proprement le dashboard."""
        logger.info(f"Signal {sig} reçu, arrêt du dashboard...")
        self.running = False
        if self.dashboard:
            asyncio.create_task(self.dashboard.stop())
    
    async def start(self):
        """Démarre le dashboard et le moniteur."""
        self.running = True
        
        # Création du moniteur (mode observateur)
        monitor_config = self.config.get("monitoring", {})
        self.monitor = AdvancedMonitor(
            config=monitor_config,
            data_dir=self.data_dir
        )
        
        # Chargement des données existantes
        metrics = self._load_metrics_data()
        self.monitor.market_metrics = metrics["market"]
        self.monitor.performance_metrics = metrics["performance"]
        self.monitor.system_metrics = metrics["system"]
        self.monitor.error_history = metrics["errors"]
        self.monitor.trade_history = metrics["trades"]
        
        # Création et démarrage du dashboard
        dashboard_config = monitor_config.get("dashboard", {})
        self.dashboard = DashboardServer(
            monitor=self.monitor,
            port=self.port or dashboard_config.get("port", 8080),
            refresh_interval=dashboard_config.get("refresh_interval", 2)
        )
        
        # Démarrage du dashboard
        await self.dashboard.start()
        logger.info(f"Dashboard démarré sur le port {self.dashboard.port}")
        
        # Boucle principale pour maintenir le dashboard actif
        while self.running:
            try:
                # Vérification périodique des nouvelles données
                await self._check_for_updates()
                await asyncio.sleep(5)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Erreur dans la boucle principale: {e}")
                await asyncio.sleep(5)
        
        # Arrêt propre du dashboard
        if self.dashboard:
            await self.dashboard.stop()
            logger.info("Dashboard arrêté")
    
    async def _check_for_updates(self):
        """Vérifie s'il y a des mises à jour dans les fichiers de données."""
        # Cette méthode pourrait être étendue pour surveiller les changements
        # dans les fichiers de données et mettre à jour le moniteur en conséquence
        pass

def parse_arguments():
    """Parse les arguments de ligne de commande."""
    parser = argparse.ArgumentParser(description="Démarrer le dashboard de monitoring GBPBot en mode autonome")
    
    parser.add_argument("--config", type=str, default="config/active_config.yaml",
                        help="Chemin vers le fichier de configuration (défaut: config/active_config.yaml)")
    
    parser.add_argument("--data-dir", type=str, default="data",
                        help="Répertoire contenant les données du bot (défaut: data/)")
    
    parser.add_argument("--port", type=int, default=None,
                        help="Port sur lequel démarrer le dashboard (défaut: valeur de la configuration ou 8080)")
    
    parser.add_argument("--log-level", type=str, default="INFO",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                        help="Niveau de logging (défaut: INFO)")
    
    return parser.parse_args()

async def main():
    """Fonction principale."""
    args = parse_arguments()
    
    # Création des répertoires nécessaires s'ils n'existent pas
    os.makedirs("logs", exist_ok=True)
    os.makedirs(args.data_dir, exist_ok=True)
    
    # Démarrage du dashboard
    dashboard_starter = DashboardStarter(
        config_path=args.config,
        data_dir=args.data_dir,
        port=args.port,
        log_level=args.log_level
    )
    
    logger.info("Démarrage du dashboard en mode autonome...")
    await dashboard_starter.start()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Arrêt du dashboard par l'utilisateur")
    except Exception as e:
        logger.critical(f"Erreur fatale: {e}", exc_info=True)
        sys.exit(1) 