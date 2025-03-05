#!/usr/bin/env python3
"""
Script de démarrage pour GBPBot.
Permet de démarrer le bot avec différentes options et modes de fonctionnement.
"""

import argparse
import logging
import sys
import os
import yaml
import asyncio
import signal
import time
from pathlib import Path
from datetime import datetime

# Ajouter le répertoire parent au path pour pouvoir importer les modules GBPBot
sys.path.append(str(Path(__file__).parent.parent))

# Import des modules GBPBot
try:
    from gbpbot.core.bot import GBPBot
    from gbpbot.core.monitoring.dashboard import start_dashboard
except ImportError as e:
    print(f"Erreur d'importation des modules GBPBot: {str(e)}")
    print("Assurez-vous que le package GBPBot est correctement installé.")
    sys.exit(1)

# Configuration du logging
def setup_logging(log_level, log_file=None):
    """Configure le système de logging."""
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        print(f"Niveau de log invalide: {log_level}")
        sys.exit(1)
        
    # Créer le répertoire de logs si nécessaire
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
    # Configuration du logging
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file) if log_file else logging.NullHandler(),
            logging.StreamHandler()
        ]
    )
    
    # Réduire le niveau de log pour certaines bibliothèques bruyantes
    logging.getLogger("web3").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    
    return logging.getLogger("gbpbot")

# Gestionnaire de signaux pour arrêter proprement le bot
bot_instance = None
dashboard_task = None

def signal_handler(sig, frame):
    """Gestionnaire de signaux pour arrêter proprement le bot."""
    print("\nSignal d'arrêt reçu. Arrêt du bot en cours...")
    
    if dashboard_task:
        dashboard_task.cancel()
        
    if bot_instance:
        asyncio.create_task(bot_instance.stop())
        
    # Laisser le temps au bot de s'arrêter proprement
    time.sleep(2)
    sys.exit(0)

async def start_bot(config_path, args):
    """
    Démarre le bot avec la configuration spécifiée.
    
    Args:
        config_path: Chemin vers le fichier de configuration
        args: Arguments de la ligne de commande
    """
    global bot_instance, dashboard_task
    
    # Configurer le logging
    log_file = f"logs/gbpbot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    logger = setup_logging(args.log_level, log_file)
    
    try:
        # Charger la configuration
        logger.info(f"Chargement de la configuration: {config_path}")
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
            
        if not config:
            logger.error("La configuration est vide ou invalide")
            return 1
            
        # Vérifier si le mode test est activé
        if args.test_mode:
            if "test_mode" not in config:
                config["test_mode"] = {}
            config["test_mode"]["enabled"] = True
            config["test_mode"]["simulation_only"] = args.simulation_only
            logger.warning("Mode test activé")
            
        # Vérifier le mode de fonctionnement
        if args.mode == "monitor-only":
            if "test_mode" not in config:
                config["test_mode"] = {}
            config["test_mode"]["monitor_only"] = True
            logger.warning("Mode surveillance uniquement activé")
            
        # Démarrer le dashboard si demandé
        if args.dashboard:
            logger.info("Démarrage du dashboard")
            dashboard_port = args.dashboard_port or 8080
            dashboard_task = asyncio.create_task(
                start_dashboard(dashboard_port, config.get("monitoring", {}))
            )
            logger.info(f"Dashboard disponible sur http://localhost:{dashboard_port}")
            
        # Créer et démarrer le bot
        logger.info("Initialisation du bot")
        bot_instance = GBPBot(config)
        
        # Enregistrer le gestionnaire de signaux
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Démarrer le bot
        logger.info("Démarrage du bot")
        await bot_instance.start()
        
        # Boucle principale
        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.info("Tâche principale annulée")
        finally:
            # Arrêter le bot proprement
            logger.info("Arrêt du bot")
            await bot_instance.stop()
            
            # Annuler le dashboard si nécessaire
            if dashboard_task:
                dashboard_task.cancel()
                try:
                    await dashboard_task
                except asyncio.CancelledError:
                    pass
                    
        return 0
        
    except Exception as e:
        logger.critical(f"Erreur lors du démarrage du bot: {str(e)}", exc_info=True)
        return 1

def main():
    """Point d'entrée principal."""
    parser = argparse.ArgumentParser(description="Script de démarrage pour GBPBot")
    
    parser.add_argument("--config", default="config/active_config.yaml", help="Chemin vers le fichier de configuration")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], help="Niveau de log")
    parser.add_argument("--mode", default="normal", choices=["normal", "monitor-only"], help="Mode de fonctionnement du bot")
    parser.add_argument("--test-mode", action="store_true", help="Activer le mode test")
    parser.add_argument("--simulation-only", action="store_true", help="Exécuter uniquement en mode simulation (pas de transactions réelles)")
    parser.add_argument("--dashboard", action="store_true", help="Démarrer le dashboard de monitoring")
    parser.add_argument("--dashboard-port", type=int, help="Port pour le dashboard de monitoring")
    
    args = parser.parse_args()
    
    # Vérifier que le fichier de configuration existe
    if not os.path.exists(args.config):
        print(f"Le fichier de configuration n'existe pas: {args.config}")
        sys.exit(1)
        
    # Exécuter la boucle asyncio
    try:
        exit_code = asyncio.run(start_bot(args.config, args))
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nInterruption clavier. Arrêt du bot.")
        sys.exit(0)
    
if __name__ == "__main__":
    main() 