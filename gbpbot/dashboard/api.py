#!/usr/bin/env python3
"""
API REST pour le dashboard GBPBot.
Fournit des endpoints pour interagir avec toutes les fonctionnalités du bot.
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query, Path
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional, Union, Any, Tuple
import asyncio
import logging
from datetime import datetime, timedelta
import os
import json
import sys

# Ajouter le répertoire parent au PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import des modules du GBPBot
from gbpbot.core.config import get_config, update_config
from gbpbot.backtesting.backtesting_engine import BacktestingEngine
from gbpbot.strategies.arbitrage import ArbitrageStrategy
from gbpbot.strategies.sniping import SnipingStrategy
from gbpbot.strategies.auto_mode import AutoModeStrategy

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("dashboard_api.log")
    ]
)
logger = logging.getLogger("dashboard_api")

# Création du router FastAPI
router = APIRouter(prefix="/api", tags=["GBPBot API"])

# Modèles de données (Pydantic)
class ConfigUpdate(BaseModel):
    """Modèle pour mettre à jour la configuration."""
    path: str = Field(..., description="Chemin de la configuration à mettre à jour")
    value: Any = Field(..., description="Nouvelle valeur")

class StrategyConfig(BaseModel):
    """Configuration d'une stratégie."""
    name: str = Field(..., description="Nom de la stratégie")
    enabled: bool = Field(True, description="Si la stratégie est activée")
    params: Dict[str, Any] = Field({}, description="Paramètres spécifiques")

class BacktestConfig(BaseModel):
    """Configuration pour un backtest."""
    strategy: str = Field(..., description="Stratégie à tester")
    start_date: datetime = Field(..., description="Date de début")
    end_date: datetime = Field(..., description="Date de fin")
    initial_balance: float = Field(1000.0, description="Balance initiale")
    pairs: List[str] = Field(..., description="Paires à tester")
    params: Dict[str, Any] = Field({}, description="Paramètres spécifiques")
    
    @validator("end_date")
    def end_date_must_be_after_start_date(cls, v, values):
        if "start_date" in values and v <= values["start_date"]:
            raise ValueError("La date de fin doit être postérieure à la date de début")
        return v

# Variables globales pour stocker les références aux objets
running_strategies = {}
backtesting_tasks = {}
last_metrics = {}

# Endpoints API

@router.get("/status")
async def get_status():
    """Récupérer le statut global du GBPBot."""
    try:
        config = get_config()
        return {
            "status": "running" if running_strategies else "idle",
            "active_strategies": list(running_strategies.keys()),
            "backtests_running": list(backtesting_tasks.keys()),
            "blockchain_clients": config.get("blockchain_clients", []),
            "last_update": datetime.now().isoformat()
        }
    except Exception as e:
        logger.exception("Erreur lors de la récupération du statut")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/config")
async def get_full_config():
    """Récupérer la configuration complète."""
    try:
        return get_config()
    except Exception as e:
        logger.exception("Erreur lors de la récupération de la configuration")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/config")
async def update_config_value(update: ConfigUpdate):
    """Mettre à jour une valeur spécifique de la configuration."""
    try:
        current_config = get_config()
        success = update_config(update.path, update.value)
        if not success:
            raise HTTPException(status_code=400, detail=f"Impossible de mettre à jour {update.path}")
        return {"status": "success", "message": f"Configuration {update.path} mise à jour"}
    except Exception as e:
        logger.exception(f"Erreur lors de la mise à jour de la configuration: {update.path}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/strategies")
async def get_available_strategies():
    """Récupérer la liste des stratégies disponibles et leur statut."""
    try:
        strategies = {
            "arbitrage": {
                "name": "Arbitrage entre DEX",
                "description": "Exploite les écarts de prix entre différents DEX et/ou CEX",
                "running": "arbitrage" in running_strategies,
                "config": get_config().get("strategies", {}).get("arbitrage", {})
            },
            "sniping": {
                "name": "Sniping de Token",
                "description": "Détecte et achète rapidement les nouveaux tokens prometteurs",
                "running": "sniping" in running_strategies,
                "config": get_config().get("strategies", {}).get("sniping", {})
            },
            "auto_mode": {
                "name": "Mode Automatique Intelligent",
                "description": "Combine les modules d'arbitrage et de sniping de manière intelligente",
                "running": "auto_mode" in running_strategies,
                "config": get_config().get("strategies", {}).get("auto_mode", {})
            }
        }
        return strategies
    except Exception as e:
        logger.exception("Erreur lors de la récupération des stratégies")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/strategies/{strategy_name}/start")
async def start_strategy(
    strategy_name: str = Path(..., description="Nom de la stratégie à démarrer"),
    config: Optional[StrategyConfig] = None,
    background_tasks: BackgroundTasks = None
):
    """Démarrer une stratégie spécifique."""
    try:
        if strategy_name in running_strategies:
            return {"status": "warning", "message": f"La stratégie {strategy_name} est déjà en cours d'exécution"}
        
        # Vérifier si la stratégie existe
        if strategy_name not in ["arbitrage", "sniping", "auto_mode"]:
            raise HTTPException(status_code=404, detail=f"Stratégie {strategy_name} non trouvée")
        
        # Créer la stratégie appropriée
        strategy_obj = None
        if strategy_name == "arbitrage":
            strategy_obj = ArbitrageStrategy()
        elif strategy_name == "sniping":
            strategy_obj = SnipingStrategy()
        elif strategy_name == "auto_mode":
            strategy_obj = AutoModeStrategy()
        
        # Configurer la stratégie si nécessaire
        if config and config.params:
            for key, value in config.params.items():
                if hasattr(strategy_obj, key):
                    setattr(strategy_obj, key, value)
        
        # Démarrer la stratégie en arrière-plan
        async def run_strategy():
            try:
                running_strategies[strategy_name] = strategy_obj
                await strategy_obj.start()
            except Exception as e:
                logger.exception(f"Erreur lors de l'exécution de la stratégie {strategy_name}")
            finally:
                if strategy_name in running_strategies:
                    del running_strategies[strategy_name]
        
        if background_tasks:
            background_tasks.add_task(run_strategy)
        else:
            asyncio.create_task(run_strategy())
        
        return {
            "status": "success", 
            "message": f"Stratégie {strategy_name} démarrée",
            "config": config.params if config else {}
        }
    except Exception as e:
        logger.exception(f"Erreur lors du démarrage de la stratégie {strategy_name}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/strategies/{strategy_name}/stop")
async def stop_strategy(strategy_name: str = Path(..., description="Nom de la stratégie à arrêter")):
    """Arrêter une stratégie spécifique."""
    try:
        if strategy_name not in running_strategies:
            raise HTTPException(status_code=404, detail=f"Stratégie {strategy_name} non trouvée ou non démarrée")
        
        strategy = running_strategies[strategy_name]
        await strategy.stop()
        
        # Supprimer la référence
        del running_strategies[strategy_name]
        
        return {"status": "success", "message": f"Stratégie {strategy_name} arrêtée"}
    except Exception as e:
        logger.exception(f"Erreur lors de l'arrêt de la stratégie {strategy_name}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/metrics")
async def get_metrics(
    strategy: Optional[str] = Query(None, description="Filtrer par stratégie"),
    period: str = Query("1h", description="Période (1h, 24h, 7d, 30d)")
):
    """Récupérer les métriques de performance."""
    try:
        # Période en secondes
        period_seconds = {
            "1h": 3600,
            "24h": 86400,
            "7d": 604800,
            "30d": 2592000
        }.get(period, 3600)
        
        # Date limite pour filtrer les métriques
        cutoff_date = datetime.now() - timedelta(seconds=period_seconds)
        
        # Filtrer les métriques selon les critères
        metrics = last_metrics.copy()
        
        # Filtrer par stratégie si spécifié
        if strategy:
            if strategy in metrics:
                return {strategy: metrics[strategy]}
            else:
                return {}
        
        return metrics
    except Exception as e:
        logger.exception("Erreur lors de la récupération des métriques")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/backtest")
async def run_backtest(
    config: BacktestConfig,
    background_tasks: BackgroundTasks
):
    """Lancer un backtest avec la configuration spécifiée."""
    try:
        # Générer un ID unique pour le backtest
        backtest_id = f"backtest_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Créer une instance de BacktestingEngine
        engine = BacktestingEngine()
        
        # Configurer le backtest
        engine.set_initial_balance(config.initial_balance)
        engine.set_date_range(config.start_date, config.end_date)
        engine.set_pairs(config.pairs)
        
        # Configurer la stratégie
        if config.strategy == "arbitrage":
            strategy = ArbitrageStrategy()
        elif config.strategy == "sniping":
            strategy = SnipingStrategy()
        elif config.strategy == "auto_mode":
            strategy = AutoModeStrategy()
        else:
            raise HTTPException(status_code=400, detail=f"Stratégie {config.strategy} non prise en charge pour le backtest")
        
        # Appliquer les paramètres spécifiques
        for key, value in config.params.items():
            if hasattr(strategy, key):
                setattr(strategy, key, value)
        
        engine.set_strategy(strategy)
        
        # Exécuter le backtest en arrière-plan
        async def run_backtest_task():
            try:
                backtesting_tasks[backtest_id] = engine
                results = await engine.run()
                
                # Stocker les résultats (pour récupération ultérieure)
                with open(f"backtest_results_{backtest_id}.json", "w") as f:
                    json.dump(results, f, default=str)
                
                logger.info(f"Backtest {backtest_id} terminé avec succès")
            except Exception as e:
                logger.exception(f"Erreur lors de l'exécution du backtest {backtest_id}")
            finally:
                if backtest_id in backtesting_tasks:
                    del backtesting_tasks[backtest_id]
        
        background_tasks.add_task(run_backtest_task)
        
        return {
            "status": "success", 
            "message": "Backtest démarré", 
            "backtest_id": backtest_id
        }
    except Exception as e:
        logger.exception("Erreur lors du lancement du backtest")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/backtest/{backtest_id}")
async def get_backtest_status(backtest_id: str = Path(..., description="ID du backtest")):
    """Récupérer le statut d'un backtest spécifique."""
    try:
        # Vérifier si le backtest est en cours
        if backtest_id in backtesting_tasks:
            engine = backtesting_tasks[backtest_id]
            return {
                "status": "running",
                "progress": engine.get_progress(),
                "current_step": engine.get_current_step(),
                "estimated_completion": engine.get_estimated_completion_time()
            }
        
        # Vérifier si les résultats existent
        result_file = f"backtest_results_{backtest_id}.json"
        if os.path.exists(result_file):
            with open(result_file, "r") as f:
                results = json.load(f)
            return {
                "status": "completed",
                "results": results
            }
        
        raise HTTPException(status_code=404, detail=f"Backtest {backtest_id} non trouvé")
    except Exception as e:
        logger.exception(f"Erreur lors de la récupération du statut du backtest {backtest_id}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/wallets")
async def get_wallets_info():
    """Récupérer les informations sur les wallets configurés."""
    try:
        config = get_config()
        wallets = config.get("wallets", {})
        
        # Pour des raisons de sécurité, masquer les clés privées
        secure_wallets = {}
        for blockchain, wallet_info in wallets.items():
            secure_wallets[blockchain] = {
                "address": wallet_info.get("address", ""),
                "balance": wallet_info.get("balance", 0),
                "has_private_key": bool(wallet_info.get("private_key")),
            }
        
        return secure_wallets
    except Exception as e:
        logger.exception("Erreur lors de la récupération des informations sur les wallets")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/logs")
async def get_logs(
    level: str = Query("INFO", description="Niveau de log (DEBUG, INFO, WARNING, ERROR)"),
    limit: int = Query(100, description="Nombre maximum de logs à retourner"),
    strategy: Optional[str] = Query(None, description="Filtrer par stratégie")
):
    """Récupérer les logs du GBPBot."""
    try:
        log_levels = {
            "DEBUG": 10,
            "INFO": 20,
            "WARNING": 30,
            "ERROR": 40,
            "CRITICAL": 50
        }
        
        min_level = log_levels.get(level.upper(), 20)
        
        # Lire les logs depuis le fichier
        logs = []
        with open("gbpbot.log", "r") as f:
            for line in f:
                # Parser simplement les lignes de log
                try:
                    parts = line.strip().split(" - ")
                    if len(parts) >= 4:
                        timestamp = parts[0]
                        log_level = parts[2]
                        message = " - ".join(parts[3:])
                        
                        # Filtrer par niveau
                        if log_levels.get(log_level, 0) >= min_level:
                            # Filtrer par stratégie si spécifié
                            if not strategy or strategy in message:
                                logs.append({
                                    "timestamp": timestamp,
                                    "level": log_level,
                                    "message": message
                                })
                except Exception:
                    # Ignorer les lignes non conformes
                    continue
        
        # Trier par timestamp décroissant et limiter le nombre
        logs.sort(key=lambda x: x["timestamp"], reverse=True)
        logs = logs[:limit]
        
        return logs
    except Exception as e:
        logger.exception("Erreur lors de la récupération des logs")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/update_metrics")
async def update_metrics(metrics: Dict[str, Any]):
    """
    Endpoint interne pour mettre à jour les métriques.
    Appelé par le système pour mettre à jour les données affichées sur le dashboard.
    """
    try:
        # Mettre à jour les métriques globales
        last_metrics.update(metrics)
        return {"status": "success"}
    except Exception as e:
        logger.exception("Erreur lors de la mise à jour des métriques")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ai/analyze")
async def ai_analyze_market(
    token: str = Query(..., description="Adresse du token à analyser"),
    blockchain: str = Query("solana", description="Blockchain (solana, avalanche, sonic)")
):
    """
    Analyser un token spécifique avec l'IA.
    Utilise les modèles d'IA pour fournir une analyse approfondie.
    """
    try:
        if blockchain not in ["solana", "avalanche", "sonic"]:
            raise HTTPException(status_code=400, detail=f"Blockchain {blockchain} non prise en charge")
        
        # Importer dynamiquement le module d'analyse
        if blockchain == "solana":
            from gbpbot.ai.token_contract_analyzer import analyze_solana_token
            analysis = await analyze_solana_token(token)
        else:
            # Implémentation pour d'autres blockchains
            raise HTTPException(status_code=501, detail=f"Analyse IA pour {blockchain} non implémentée")
        
        return analysis
    except ImportError:
        logger.exception(f"Module d'analyse pour {blockchain} non disponible")
        raise HTTPException(status_code=501, detail=f"Module d'analyse pour {blockchain} non disponible")
    except Exception as e:
        logger.exception(f"Erreur lors de l'analyse du token {token}")
        raise HTTPException(status_code=500, detail=str(e))

# Point d'entrée pour intégration avec FastAPI
def setup_router(app):
    """Configurer le router pour l'application FastAPI."""
    app.include_router(router)
    logger.info("API REST du dashboard configurée avec succès") 