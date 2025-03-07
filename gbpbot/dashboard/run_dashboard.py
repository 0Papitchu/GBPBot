#!/usr/bin/env python3
"""
Script de démarrage du dashboard GBPBot.
Ce script permet de lancer l'interface web du GBPBot avec différentes options.
"""

import os
import sys
import asyncio
import signal
import argparse
import logging
import random
import json
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, List, Set, Optional
import time

# Ajouter le répertoire parent au PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import des modules du dashboard
try:
    from gbpbot.dashboard.server import Dashboard, broadcast_metrics
    # Importation conditionnelle pour éviter les erreurs de linter
    try:
        from gbpbot.core.config import get_config, update_config
    except ImportError:
        # Définir des fonctions stub si les importations échouent
        def get_config():
            """Fonction stub pour get_config."""
            return {}
        
        def update_config(path, value):
            """Fonction stub pour update_config."""
            return True
except ImportError as e:
    print(f"Erreur d'importation: {str(e)}")
    print("Assurez-vous que les modules nécessaires sont installés.")
    sys.exit(1)

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("dashboard.log")
    ]
)
logger = logging.getLogger("run_dashboard")

# Variables globales pour le contrôle du dashboard
dashboard_instance = None
stop_event = asyncio.Event()

async def simulate_metrics_updates():
    """
    Génère des métriques simulées pour tester le dashboard.
    Cette fonction est utile pour le développement et les démonstrations.
    """
    if not dashboard_instance:
        logger.error("Dashboard non initialisé. Impossible de simuler les métriques.")
        return

    logger.info("Démarrage de la simulation des métriques...")
    
    # État initial des métriques
    balance = 10000.0
    portfolio_value = 12500.0
    trades_count = 0
    win_count = 0
    detected_opportunities = 0
    executed_opportunities = 0
    
    strategies = {
        "arbitrage": {
            "status": "running",
            "profit": 0.0,
            "trades": 0,
            "opportunities": 0,
            "win_rate": 0.0
        },
        "sniping": {
            "status": "stopped",
            "profit": 0.0,
            "trades": 0,
            "opportunities": 0,
            "win_rate": 0.0
        },
        "auto_mode": {
            "status": "stopped",
            "profit": 0.0,
            "trades": 0,
            "opportunities": 0,
            "win_rate": 0.0
        }
    }
    
    # Historique des balances pour le graphique (30 jours)
    balance_history = []
    current_date = datetime.now() - timedelta(days=30)
    
    # Générer l'historique initial
    temp_balance = 10000.0
    for i in range(31):  # 31 points pour 30 jours
        # Ajout d'une petite variation aléatoire
        variation = random.uniform(-0.02, 0.03)
        temp_balance *= (1 + variation)
        
        balance_history.append({
            "date": (current_date + timedelta(days=i)).isoformat(),
            "balance": round(temp_balance, 2)
        })
    
    # Boucle de mise à jour des métriques simulées
    while not stop_event.is_set():
        try:
            # Mise à jour des métriques
            daily_variation = random.uniform(-0.05, 0.08)
            portfolio_value *= (1 + daily_variation)
            
            # Simuler des trades aléatoires
            if random.random() < 0.3:  # 30% de chance d'avoir un nouveau trade
                trades_count += 1
                if random.random() < 0.65:  # 65% de win rate
                    win_count += 1
                    
                # Déterminer la stratégie qui a fait le trade
                strategy = random.choice(list(strategies.keys()))
                if strategies[strategy]["status"] == "running":
                    strategies[strategy]["trades"] += 1
                    if random.random() < 0.65:
                        strategies[strategy]["profit"] += random.uniform(0.5, 5.0)
                    else:
                        strategies[strategy]["profit"] -= random.uniform(0.2, 2.0)
                    
                    # Mettre à jour le win rate
                    if strategies[strategy]["trades"] > 0:
                        win_trades = int(strategies[strategy]["trades"] * 0.65)
                        strategies[strategy]["win_rate"] = round((win_trades / strategies[strategy]["trades"]) * 100, 2)
            
            # Simuler des opportunités détectées
            if random.random() < 0.5:  # 50% de chance d'avoir une nouvelle opportunité
                detected_opportunities += 1
                if random.random() < 0.4:  # 40% des opportunités sont exécutées
                    executed_opportunities += 1
                    
                    # Déterminer la stratégie qui a détecté l'opportunité
                    strategy = random.choice(list(strategies.keys()))
                    if strategies[strategy]["status"] == "running":
                        strategies[strategy]["opportunities"] += 1
            
            # Mise à jour de l'historique des balances
            now = datetime.now()
            balance_history.append({
                "date": now.isoformat(),
                "balance": round(portfolio_value, 2)
            })
            
            # Conserver seulement les 31 derniers points (30 jours)
            if len(balance_history) > 31:
                balance_history = balance_history[-31:]
            
            # Calculer la variation quotidienne
            daily_change_pct = ((portfolio_value / balance) - 1) * 100
            
            # Créer les métriques à envoyer
            metrics = {
                "general": {
                    "balance": round(balance, 2),
                    "portfolio_value": round(portfolio_value, 2),
                    "daily_change_pct": round(daily_change_pct, 2),
                    "trades_count": trades_count,
                    "win_count": win_count,
                    "win_rate": round((win_count / trades_count * 100), 2) if trades_count > 0 else 0,
                    "detected_opportunities": detected_opportunities,
                    "executed_opportunities": executed_opportunities,
                    "execution_rate": round((executed_opportunities / detected_opportunities * 100), 2) if detected_opportunities > 0 else 0,
                    "last_update": datetime.now().isoformat()
                },
                "strategies": strategies,
                "balance_history": balance_history
            }
            
            # Mise à jour des métriques via le dashboard
            await dashboard_instance.update_metrics(metrics)
            logger.debug("Métriques simulées envoyées")
            
            # Attendre avant la prochaine mise à jour
            await asyncio.sleep(5)  # Mise à jour toutes les 5 secondes
            
        except Exception as e:
            logger.exception(f"Erreur lors de la simulation des métriques: {str(e)}")
            await asyncio.sleep(10)  # Attendre plus longtemps en cas d'erreur

def signal_handler(sig, frame):
    """Gestionnaire de signal pour arrêter proprement le dashboard."""
    logger.info("Signal d'arrêt reçu. Arrêt du dashboard...")
    stop_event.set()

async def start_dashboard(args):
    """
    Démarre le dashboard avec les options spécifiées.
    
    Args:
        args: Arguments de ligne de commande parsés
    """
    global dashboard_instance
    
    try:
        # Créer l'instance du dashboard
        dashboard_instance = Dashboard(host=args.host, port=args.port)
        
        # Enregistrer le gestionnaire de signal
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Tâches à exécuter
        tasks = []
        
        # Tâche du dashboard
        dashboard_task = asyncio.create_task(dashboard_instance.start())
        tasks.append(dashboard_task)
        
        # Si mode simulation est activé, démarrer la simulation des métriques
        if args.simulate:
            logger.info("Mode simulation activé - Génération de métriques simulées pour tests")
            simulate_task = asyncio.create_task(simulate_metrics_updates())
            tasks.append(simulate_task)
        
        # Attendre l'arrêt
        await stop_event.wait()
        
        # Arrêter le dashboard proprement
        if dashboard_instance:
            await dashboard_instance.stop()
        
        # Annuler toutes les tâches en cours
        for task in tasks:
            if not task.done():
                task.cancel()
                
        # Attendre que toutes les tâches soient terminées
        await asyncio.gather(*tasks, return_exceptions=True)
        
    except Exception as e:
        logger.exception(f"Erreur lors du démarrage du dashboard: {str(e)}")
    finally:
        logger.info("Dashboard arrêté")

def main():
    """Point d'entrée principal du script."""
    parser = argparse.ArgumentParser(description="Dashboard GBPBot")
    parser.add_argument("--host", default="0.0.0.0", help="Adresse d'hôte (défaut: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Port d'écoute (défaut: 8000)")
    parser.add_argument("--simulate", action="store_true", help="Activer la génération de métriques simulées pour les tests")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], 
                        default="INFO", help="Niveau de log (défaut: INFO)")
    
    args = parser.parse_args()
    
    # Configurer le niveau de log
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Afficher les informations de démarrage
    logger.info(f"Démarrage du dashboard GBPBot sur {args.host}:{args.port}")
    logger.info(f"Niveau de log: {args.log_level}")
    if args.simulate:
        logger.info("Mode simulation activé")
    
    # Démarrer le dashboard
    try:
        asyncio.run(start_dashboard(args))
    except KeyboardInterrupt:
        logger.info("Arrêt du dashboard (Ctrl+C)")
    except Exception as e:
        logger.exception(f"Erreur non gérée: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 