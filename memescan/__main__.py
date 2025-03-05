import asyncio
import sys
import os
import signal
import argparse
from datetime import datetime
from loguru import logger
from pathlib import Path
from .utils.config import Config
from .storage.database import Database
from .collectors.token_collector import TokenCollector
from .analyzers.wallet_analyzer import WalletAnalyzer
from .ml.data_loader import DataLoader
from .ml.ml_predictor import MLPredictor
from .ml.ml_results import MLResults
from .ml.alerts import AlertSystem
from .collectors.token_detector import TokenDetector
from .analyzers.auto_sniping import AutoSniper
from .utils.simulator import TradingSimulator, run_simulation

# Gestionnaire de signaux pour arrêter proprement
stop_event = asyncio.Event()

def signal_handler(sig, frame):
    """Gestionnaire de signaux pour arrêter proprement"""
    logger.info("Arrêt demandé...")
    stop_event.set()

async def main():
    """Point d'entrée principal du programme"""
    try:
        # Analyser les arguments de ligne de commande
        parser = argparse.ArgumentParser(description='MemeScan - Détection et sniping de meme coins')
        parser.add_argument('--simulate', action='store_true', help='Exécuter en mode simulation')
        parser.add_argument('--days', type=int, default=7, help='Nombre de jours de simulation')
        parser.add_argument('--speed', type=int, default=100, help='Vitesse de simulation (1=temps réel, >1=accéléré)')
        parser.add_argument('--balance', type=float, default=5.0, help='Balance initiale pour la simulation (AVAX)')
        args = parser.parse_args()
        
        # Initialisation de la configuration
        config = Config()
        
        # Configuration du logging
        logger.remove()
        logger.add(
            sys.stdout,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
            level=config.LOG_LEVEL
        )
        logger.add(
            os.path.join(config.LOG_DIR, "memescan_{time:YYYYMMDD}.log"),
            rotation="1 day",
            retention="7 days",
            level=config.LOG_LEVEL
        )
        
        # Initialisation de la base de données
        db = Database(config)
        await db.init_db()
        
        # Mode simulation
        if args.simulate:
            logger.info(f"Démarrage en mode simulation avec {args.balance} AVAX sur {args.days} jours (vitesse x{args.speed})")
            
            # Initialisation du ML predictor pour la simulation
            ml_predictor = MLPredictor(config, db)
            
            # Créer le simulateur
            simulator = TradingSimulator(config, db, ml_predictor)
            simulator.initial_balance = args.balance
            simulator.current_balance = args.balance
            simulator.simulation_days = args.days
            simulator.simulation_speed = args.speed
            
            # Exécuter la simulation
            await simulator.start_simulation()
            
            # Terminer après la simulation
            logger.info("Simulation terminée.")
            return
        
        # Mode normal
        logger.info("Starting MemeScan...")
        
        # Initialisation des composants
        token_collector = TokenCollector(config, db)
        wallet_analyzer = WalletAnalyzer(config, db)
        
        # Initialisation des composants ML
        data_loader = DataLoader(config, db)
        ml_predictor = MLPredictor(config, db)
        ml_results = MLResults(config, db)
        alert_system = AlertSystem(config, db)
        
        # Initialisation des composants de détection et sniping
        token_detector = TokenDetector(config, db)
        auto_sniper = AutoSniper(config, db, ml_predictor)
        
        # Enregistrer le gestionnaire de signaux
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Créer les tâches asynchrones
        tasks = [
            asyncio.create_task(run_data_collection(config, token_collector)),
            asyncio.create_task(run_wallet_analysis(config, wallet_analyzer)),
            asyncio.create_task(run_ml_predictions(config, ml_predictor, ml_results, alert_system)),
            asyncio.create_task(run_token_detection(config, token_detector)),
            asyncio.create_task(run_auto_sniping(config, auto_sniper))
        ]
        
        # Attendre que toutes les tâches soient terminées ou que l'arrêt soit demandé
        await asyncio.gather(*tasks, return_exceptions=True)
                
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        sys.exit(1)
        
    finally:
        # Nettoyage
        await db.close()
        logger.info("MemeScan stopped.")

async def run_data_collection(config: Config, token_collector: TokenCollector):
    """Tâche de collecte de données"""
    try:
        logger.info("Starting data collection task")
        
        while not stop_event.is_set():
            try:
                # Collecter les tokens de toutes les chaînes
                await token_collector.collect_all_chains()
                
                # Attendre l'intervalle configuré
                await asyncio.sleep(config.SCRAPING_INTERVAL)
                
            except Exception as e:
                logger.error(f"Error in data collection: {str(e)}")
                await asyncio.sleep(60)  # Attendre en cas d'erreur
                
    except Exception as e:
        logger.error(f"Fatal error in data collection task: {str(e)}")

async def run_wallet_analysis(config: Config, wallet_analyzer: WalletAnalyzer):
    """Tâche d'analyse des wallets"""
    try:
        logger.info("Starting wallet analysis task")
        
        # Attendre que la collecte de données ait commencé
        await asyncio.sleep(60)
        
        while not stop_event.is_set():
            try:
                # Analyser les wallets
                await wallet_analyzer.analyze_wallets()
                
                # Attendre l'intervalle configuré
                await asyncio.sleep(config.ANALYSIS_INTERVAL)
                
            except Exception as e:
                logger.error(f"Error in wallet analysis: {str(e)}")
                await asyncio.sleep(60)
                
    except Exception as e:
        logger.error(f"Fatal error in wallet analysis task: {str(e)}")

async def run_ml_predictions(config: Config, ml_predictor: MLPredictor, ml_results: MLResults, alert_system: AlertSystem):
    """Tâche de prédictions ML"""
    try:
        logger.info("Starting ML prediction task")
        
        # Attendre que la collecte de données ait commencé
        await asyncio.sleep(120)
        
        while not stop_event.is_set():
            try:
                # Effectuer les prédictions
                predictions = await ml_predictor.predict()
                
                if predictions:
                    # Générer les visualisations
                    await ml_results.generate_visualizations(predictions)
                    
                    # Exporter les prédictions
                    await ml_results.export_predictions(predictions)
                    
                    # Envoyer les alertes pour les tokens à fort potentiel
                    await alert_system.check_and_send_alerts(predictions)
                
                # Attendre l'intervalle configuré
                await asyncio.sleep(config.ML_PREDICTION_INTERVAL)
                
            except Exception as e:
                logger.error(f"Error in ML predictions: {str(e)}")
                await asyncio.sleep(60)
                
    except Exception as e:
        logger.error(f"Fatal error in ML prediction task: {str(e)}")

async def run_token_detection(config: Config, token_detector: TokenDetector):
    """Tâche de détection en temps réel des nouveaux tokens"""
    try:
        logger.info("Starting real-time token detection task")
        
        # Démarrer la surveillance en temps réel
        await token_detector.start_monitoring()
        
    except Exception as e:
        logger.error(f"Fatal error in token detection task: {str(e)}")

async def run_auto_sniping(config: Config, auto_sniper: AutoSniper):
    """Tâche de sniping automatique"""
    try:
        logger.info("Starting automatic sniping task")
        
        # Attendre que la détection de tokens ait commencé
        await asyncio.sleep(30)
        
        # Démarrer le sniping automatique
        await auto_sniper.start_auto_sniping()
        
    except Exception as e:
        logger.error(f"Fatal error in auto sniping task: {str(e)}")

if __name__ == "__main__":
    # Créer le répertoire de logs
    Path("logs").mkdir(exist_ok=True)
    
    # Lancer la boucle principale
    asyncio.run(main()) 