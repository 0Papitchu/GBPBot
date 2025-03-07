#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module de Backtesting pour GBPBot
================================

Ce module fournit des outils pour le backtesting et la simulation des stratégies
de trading du GBPBot, permettant de tester et d'optimiser les stratégies avant
leur déploiement en environnement réel.

Composants principaux:
- Engine: Moteur principal de backtesting
- DataLoader: Chargement et préparation des données historiques
- MarketSimulator: Simulation des conditions de marché
- PerformanceAnalyzer: Analyse des performances des stratégies
- ParameterOptimizer: Optimisation des paramètres des stratégies
- Visualization: Visualisation des résultats
- Reporting: Génération de rapports détaillés
"""

__version__ = "0.1.0"

# Imports des composants principaux
from gbpbot.backtesting.engine import BacktestEngine
from gbpbot.backtesting.data_loader import DataLoader
from gbpbot.backtesting.market_simulator import MarketSimulator
from gbpbot.backtesting.performance_analyzer import PerformanceAnalyzer
from gbpbot.backtesting.parameter_optimizer import ParameterOptimizer
from gbpbot.backtesting.visualization import BacktestVisualizer
from gbpbot.backtesting.reporting import ReportGenerator

# Fonction de création rapide d'un backtest
def create_backtest(
    strategy_name,
    symbols,
    start_date,
    end_date,
    timeframe="1h",
    initial_capital=10000,
    data_source="local",
    **strategy_params
):
    """
    Crée et configure rapidement un backtest pour une stratégie donnée.
    
    Args:
        strategy_name (str): Nom de la stratégie à tester
        symbols (list): Liste des symboles à trader
        start_date (str): Date de début au format 'YYYY-MM-DD'
        end_date (str): Date de fin au format 'YYYY-MM-DD'
        timeframe (str): Timeframe des données ('1m', '5m', '15m', '1h', '4h', '1d')
        initial_capital (float): Capital initial pour le backtest
        data_source (str): Source des données ('local', 'exchange', 'csv')
        **strategy_params: Paramètres spécifiques à la stratégie
        
    Returns:
        BacktestEngine: Instance configurée du moteur de backtest
    """
    # Création du chargeur de données
    data_loader = DataLoader(
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        timeframe=timeframe,
        source=data_source
    )
    
    # Création du moteur de backtest
    engine = BacktestEngine(
        data_loader=data_loader,
        strategy_name=strategy_name,
        initial_capital=initial_capital,
        strategy_params=strategy_params
    )
    
    return engine

# Fonction pour l'optimisation rapide des paramètres
def optimize_strategy(
    strategy_name,
    symbols,
    start_date,
    end_date,
    param_grid,
    timeframe="1h",
    initial_capital=10000,
    optimization_method="grid",
    n_jobs=-1,
    metric="sharpe"
):
    """
    Optimise les paramètres d'une stratégie via backtesting.
    
    Args:
        strategy_name (str): Nom de la stratégie à optimiser
        symbols (list): Liste des symboles à trader
        start_date (str): Date de début au format 'YYYY-MM-DD'
        end_date (str): Date de fin au format 'YYYY-MM-DD'
        param_grid (dict): Grille de paramètres à tester
        timeframe (str): Timeframe des données ('1m', '5m', '15m', '1h', '4h', '1d')
        initial_capital (float): Capital initial pour le backtest
        optimization_method (str): Méthode d'optimisation ('grid', 'random', 'bayesian', 'genetic')
        n_jobs (int): Nombre de jobs parallèles (-1 pour utiliser tous les CPU)
        metric (str): Métrique à optimiser ('sharpe', 'sortino', 'cagr', 'max_drawdown', 'profit')
        
    Returns:
        dict: Meilleurs paramètres et leurs performances
    """
    # Création du chargeur de données
    data_loader = DataLoader(
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        timeframe=timeframe,
        source="local"
    )
    
    # Création de l'optimiseur
    optimizer = ParameterOptimizer(
        data_loader=data_loader,
        strategy_name=strategy_name,
        initial_capital=initial_capital,
        param_grid=param_grid,
        method=optimization_method,
        n_jobs=n_jobs,
        metric=metric
    )
    
    # Lancement de l'optimisation
    results = optimizer.run()
    
    return results

# Exports pour l'API publique
__all__ = [
    'BacktestEngine',
    'DataLoader',
    'MarketSimulator',
    'PerformanceAnalyzer',
    'ParameterOptimizer',
    'BacktestVisualizer',
    'ReportGenerator',
    'create_backtest',
    'optimize_strategy'
] 