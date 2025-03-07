#!/usr/bin/env python3
"""
Exemple d'utilisation du système de backtesting de GBPBot avec les stratégies d'arbitrage.

Ce script montre comment configurer et exécuter des backtests pour les stratégies d'arbitrage,
analyser les résultats et optimiser les paramètres.
"""

import os
import sys
import logging
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Ajouter le répertoire parent au chemin de recherche des modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importer les modules de GBPBot
from gbpbot.backtesting.backtesting_engine import BacktestingEngine
from gbpbot.backtesting.arbitrage_strategy import (
    SimpleArbitrageStrategy,
    TriangularArbitrageStrategy,
    StatisticalArbitrageStrategy
)

# Configuration du logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('backtest_arbitrage_example.log')
    ]
)
logger = logging.getLogger(__name__)

def run_simple_arbitrage_backtest():
    """
    Exécute un backtest pour la stratégie d'arbitrage simple.
    """
    logger.info("=== Exécution du backtest pour la stratégie d'arbitrage simple ===")
    
    # Configuration du backtest
    config = {
        "RESULTS_DIR": "backtest_results",
        "DATA_DIR": "historical_data",
        "REPORT_DIR": "backtest_reports",
        "SLIPPAGE_MODEL": "fixed",
        "SLIPPAGE_RATE": 0.001,  # 0.1% de slippage
        "TRANSACTION_FEE_RATE": 0.001,  # 0.1% de frais de transaction
        "EXECUTION_LATENCY": 1,  # 1 seconde de latence
        "EXECUTION_PROBABILITY": 0.99,  # 99% de probabilité d'exécution
        "MARKET_IMPACT_MODEL": "linear",
        "MARKET_IMPACT_FACTOR": 0.0001,  # Facteur d'impact sur le marché
    }
    
    # Initialiser le moteur de backtesting
    engine = BacktestingEngine(config)
    
    # Paramètres de la stratégie
    strategy_params = {
        "symbol": "BTC/USDT",
        "market_a": "binance",
        "market_b": "kucoin",
        "min_spread_pct": 0.5,  # 0.5% d'écart minimum
        "trade_size": 0.1,  # 0.1 BTC par trade
        "max_position": 1.0,  # Position maximale de 1 BTC
        "cooldown_minutes": 5  # 5 minutes entre les trades
    }
    
    # Période de backtest
    start_date = "2023-01-01"
    end_date = "2023-01-31"
    
    # Solde initial
    initial_balance = {
        "USDT": 10000.0,
        "BTC": 0.0
    }
    
    # Exécuter le backtest
    results = engine.run_backtest(
        strategy_class=SimpleArbitrageStrategy,
        strategy_params=strategy_params,
        symbols=["binance:BTC/USDT", "kucoin:BTC/USDT"],
        start_date=start_date,
        end_date=end_date,
        initial_balance=initial_balance,
        timeframe="1m",
        data_source="binance"
    )
    
    # Afficher les résultats
    logger.info(f"Backtest terminé. ID: {results['backtest_id']}")
    logger.info(f"Solde initial: {initial_balance}")
    logger.info(f"Solde final: {results['final_balance']}")
    logger.info(f"Nombre de trades: {len(results['trades'])}")
    logger.info(f"Métriques de performance: {results['performance_metrics']}")
    logger.info(f"Rapport généré: {results['report_path']}")
    
    return results


def run_triangular_arbitrage_backtest():
    """
    Exécute un backtest pour la stratégie d'arbitrage triangulaire.
    """
    logger.info("=== Exécution du backtest pour la stratégie d'arbitrage triangulaire ===")
    
    # Configuration du backtest
    config = {
        "RESULTS_DIR": "backtest_results",
        "DATA_DIR": "historical_data",
        "REPORT_DIR": "backtest_reports",
        "SLIPPAGE_MODEL": "fixed",
        "SLIPPAGE_RATE": 0.001,  # 0.1% de slippage
        "TRANSACTION_FEE_RATE": 0.001,  # 0.1% de frais de transaction
        "EXECUTION_LATENCY": 1,  # 1 seconde de latence
        "EXECUTION_PROBABILITY": 0.99,  # 99% de probabilité d'exécution
        "MARKET_IMPACT_MODEL": "linear",
        "MARKET_IMPACT_FACTOR": 0.0001,  # Facteur d'impact sur le marché
    }
    
    # Initialiser le moteur de backtesting
    engine = BacktestingEngine(config)
    
    # Paramètres de la stratégie
    strategy_params = {
        "market": "binance",
        "base_asset": "USDT",
        "asset1": "BTC",
        "asset2": "ETH",
        "min_profit_pct": 0.3,  # 0.3% de profit minimum
        "trade_size": 1000.0,  # 1000 USDT par trade
        "cooldown_minutes": 5  # 5 minutes entre les trades
    }
    
    # Période de backtest
    start_date = "2023-01-01"
    end_date = "2023-01-31"
    
    # Solde initial
    initial_balance = {
        "USDT": 10000.0,
        "BTC": 0.0,
        "ETH": 0.0
    }
    
    # Exécuter le backtest
    results = engine.run_backtest(
        strategy_class=TriangularArbitrageStrategy,
        strategy_params=strategy_params,
        symbols=["binance:BTC/USDT", "binance:ETH/BTC", "binance:ETH/USDT"],
        start_date=start_date,
        end_date=end_date,
        initial_balance=initial_balance,
        timeframe="1m",
        data_source="binance"
    )
    
    # Afficher les résultats
    logger.info(f"Backtest terminé. ID: {results['backtest_id']}")
    logger.info(f"Solde initial: {initial_balance}")
    logger.info(f"Solde final: {results['final_balance']}")
    logger.info(f"Nombre de trades: {len(results['trades'])}")
    logger.info(f"Métriques de performance: {results['performance_metrics']}")
    logger.info(f"Rapport généré: {results['report_path']}")
    
    return results


def run_statistical_arbitrage_backtest():
    """
    Exécute un backtest pour la stratégie d'arbitrage statistique.
    """
    logger.info("=== Exécution du backtest pour la stratégie d'arbitrage statistique ===")
    
    # Configuration du backtest
    config = {
        "RESULTS_DIR": "backtest_results",
        "DATA_DIR": "historical_data",
        "REPORT_DIR": "backtest_reports",
        "SLIPPAGE_MODEL": "fixed",
        "SLIPPAGE_RATE": 0.001,  # 0.1% de slippage
        "TRANSACTION_FEE_RATE": 0.001,  # 0.1% de frais de transaction
        "EXECUTION_LATENCY": 1,  # 1 seconde de latence
        "EXECUTION_PROBABILITY": 0.99,  # 99% de probabilité d'exécution
        "MARKET_IMPACT_MODEL": "linear",
        "MARKET_IMPACT_FACTOR": 0.0001,  # Facteur d'impact sur le marché
    }
    
    # Initialiser le moteur de backtesting
    engine = BacktestingEngine(config)
    
    # Paramètres de la stratégie
    strategy_params = {
        "market": "binance",
        "pair_a": "BTC/USDT",
        "pair_b": "ETH/USDT",
        "window": 100,  # Fenêtre de 100 barres
        "entry_threshold": 2.0,  # Seuil d'entrée de 2 écarts-types
        "exit_threshold": 0.5,  # Seuil de sortie de 0.5 écart-type
        "trade_size": 1.0,  # 1 unité par trade
        "max_position": 5.0  # Position maximale de 5 unités
    }
    
    # Période de backtest
    start_date = "2023-01-01"
    end_date = "2023-03-31"
    
    # Solde initial
    initial_balance = {
        "USDT": 10000.0,
        "BTC": 0.0,
        "ETH": 0.0
    }
    
    # Exécuter le backtest
    results = engine.run_backtest(
        strategy_class=StatisticalArbitrageStrategy,
        strategy_params=strategy_params,
        symbols=["binance:BTC/USDT", "binance:ETH/USDT"],
        start_date=start_date,
        end_date=end_date,
        initial_balance=initial_balance,
        timeframe="1h",  # Timeframe horaire pour l'arbitrage statistique
        data_source="binance"
    )
    
    # Afficher les résultats
    logger.info(f"Backtest terminé. ID: {results['backtest_id']}")
    logger.info(f"Solde initial: {initial_balance}")
    logger.info(f"Solde final: {results['final_balance']}")
    logger.info(f"Nombre de trades: {len(results['trades'])}")
    logger.info(f"Métriques de performance: {results['performance_metrics']}")
    logger.info(f"Rapport généré: {results['report_path']}")
    
    return results


def compare_arbitrage_strategies():
    """
    Compare les différentes stratégies d'arbitrage.
    """
    logger.info("=== Comparaison des stratégies d'arbitrage ===")
    
    # Configuration du backtest
    config = {
        "RESULTS_DIR": "backtest_results",
        "DATA_DIR": "historical_data",
        "REPORT_DIR": "backtest_reports",
        "SLIPPAGE_MODEL": "fixed",
        "SLIPPAGE_RATE": 0.001,  # 0.1% de slippage
        "TRANSACTION_FEE_RATE": 0.001,  # 0.1% de frais de transaction
        "EXECUTION_LATENCY": 1,  # 1 seconde de latence
        "EXECUTION_PROBABILITY": 0.99,  # 99% de probabilité d'exécution
        "MARKET_IMPACT_MODEL": "linear",
        "MARKET_IMPACT_FACTOR": 0.0001,  # Facteur d'impact sur le marché
    }
    
    # Initialiser le moteur de backtesting
    engine = BacktestingEngine(config)
    
    # Paramètres des stratégies
    simple_arbitrage_params = {
        "symbol": "BTC/USDT",
        "market_a": "binance",
        "market_b": "kucoin",
        "min_spread_pct": 0.5,
        "trade_size": 0.1,
        "max_position": 1.0,
        "cooldown_minutes": 5
    }
    
    triangular_arbitrage_params = {
        "market": "binance",
        "base_asset": "USDT",
        "asset1": "BTC",
        "asset2": "ETH",
        "min_profit_pct": 0.3,
        "trade_size": 1000.0,
        "cooldown_minutes": 5
    }
    
    statistical_arbitrage_params = {
        "market": "binance",
        "pair_a": "BTC/USDT",
        "pair_b": "ETH/USDT",
        "window": 100,
        "entry_threshold": 2.0,
        "exit_threshold": 0.5,
        "trade_size": 1.0,
        "max_position": 5.0
    }
    
    # Liste des stratégies à comparer
    strategies = [
        (SimpleArbitrageStrategy, simple_arbitrage_params),
        (TriangularArbitrageStrategy, triangular_arbitrage_params),
        (StatisticalArbitrageStrategy, statistical_arbitrage_params)
    ]
    
    # Période de backtest
    start_date = "2023-01-01"
    end_date = "2023-01-31"
    
    # Solde initial
    initial_balance = {
        "USDT": 10000.0,
        "BTC": 0.0,
        "ETH": 0.0
    }
    
    # Exécuter la comparaison
    comparison_results = engine.compare_strategies(
        strategies=strategies,
        symbols=["binance:BTC/USDT", "kucoin:BTC/USDT", "binance:ETH/BTC", "binance:ETH/USDT"],
        start_date=start_date,
        end_date=end_date,
        initial_balance=initial_balance,
        timeframe="1m",
        data_source="binance"
    )
    
    # Afficher les résultats
    logger.info(f"Comparaison terminée. ID: {comparison_results['comparison_id']}")
    logger.info(f"Stratégies comparées: {comparison_results['strategies']}")
    logger.info(f"Résultats de la comparaison: {comparison_results['comparison_results']}")
    logger.info(f"Rapport généré: {comparison_results['report_path']}")
    
    return comparison_results


def optimize_simple_arbitrage_strategy():
    """
    Optimise les paramètres de la stratégie d'arbitrage simple.
    """
    logger.info("=== Optimisation de la stratégie d'arbitrage simple ===")
    
    # Configuration du backtest
    config = {
        "RESULTS_DIR": "backtest_results",
        "DATA_DIR": "historical_data",
        "REPORT_DIR": "backtest_reports",
        "SLIPPAGE_MODEL": "fixed",
        "SLIPPAGE_RATE": 0.001,  # 0.1% de slippage
        "TRANSACTION_FEE_RATE": 0.001,  # 0.1% de frais de transaction
        "EXECUTION_LATENCY": 1,  # 1 seconde de latence
        "EXECUTION_PROBABILITY": 0.99,  # 99% de probabilité d'exécution
        "MARKET_IMPACT_MODEL": "linear",
        "MARKET_IMPACT_FACTOR": 0.0001,  # Facteur d'impact sur le marché
        "OPTIMIZATION_METHOD": "grid",  # Méthode d'optimisation
        "N_JOBS": -1,  # Utiliser tous les cœurs disponibles
        "RANDOM_STATE": 42,
        "N_CALLS": 50,  # Nombre d'appels pour l'optimisation bayésienne
        "N_INITIAL_POINTS": 10
    }
    
    # Initialiser le moteur de backtesting
    engine = BacktestingEngine(config)
    
    # Grille de paramètres à optimiser
    param_grid = {
        "min_spread_pct": [0.1, 0.2, 0.3, 0.5, 0.7, 1.0],
        "trade_size": [0.05, 0.1, 0.2, 0.5],
        "cooldown_minutes": [1, 5, 10, 15, 30]
    }
    
    # Paramètres fixes
    fixed_params = {
        "symbol": "BTC/USDT",
        "market_a": "binance",
        "market_b": "kucoin",
        "max_position": 1.0
    }
    
    # Période de backtest
    start_date = "2023-01-01"
    end_date = "2023-01-31"
    
    # Solde initial
    initial_balance = {
        "USDT": 10000.0,
        "BTC": 0.0
    }
    
    # Exécuter l'optimisation
    optimization_results = engine.optimize_strategy(
        strategy_class=SimpleArbitrageStrategy,
        param_grid=param_grid,
        symbols=["binance:BTC/USDT", "kucoin:BTC/USDT"],
        start_date=start_date,
        end_date=end_date,
        initial_balance=initial_balance,
        timeframe="1m",
        data_source="binance",
        optimization_method="grid",
        maximize_metric="sharpe_ratio",
        n_iter=50
    )
    
    # Afficher les résultats
    logger.info(f"Optimisation terminée. ID: {optimization_results['optimization_id']}")
    logger.info(f"Meilleurs paramètres: {optimization_results['best_params']}")
    logger.info(f"Meilleure valeur: {optimization_results['best_value']}")
    logger.info(f"Backtest final: {optimization_results['final_backtest_id']}")
    
    return optimization_results


def main():
    """
    Fonction principale.
    """
    logger.info("Démarrage de l'exemple de backtesting des stratégies d'arbitrage")
    
    # Créer les répertoires nécessaires
    os.makedirs("backtest_results", exist_ok=True)
    os.makedirs("historical_data", exist_ok=True)
    os.makedirs("backtest_reports", exist_ok=True)
    
    # Exécuter les backtests
    simple_results = run_simple_arbitrage_backtest()
    triangular_results = run_triangular_arbitrage_backtest()
    statistical_results = run_statistical_arbitrage_backtest()
    
    # Comparer les stratégies
    comparison_results = compare_arbitrage_strategies()
    
    # Optimiser la stratégie d'arbitrage simple
    optimization_results = optimize_simple_arbitrage_strategy()
    
    logger.info("Exemple de backtesting terminé")


if __name__ == "__main__":
    main() 