"""
Package de commandes Telegram pour GBPBot
=========================================

Ce package regroupe toutes les commandes disponibles pour l'interface Telegram du GBPBot.
"""

# Import des modules de commandes
from gbpbot.telegram.commands.base import register_command_handlers
from gbpbot.telegram.commands.status import status_command, view_stats_command, check_balance_command, register_status_command_handlers
from gbpbot.telegram.commands.analyze import analyze_market_command, analyze_token_command, list_trending_command, register_analyze_command_handlers
from gbpbot.telegram.commands.backtesting import run_backtest_command, list_backtests_command, register_backtest_command_handlers
from gbpbot.telegram.commands.strategy import start_strategy_command, stop_strategy_command, list_strategies_command, configure_strategy_command, register_strategy_command_handlers
from gbpbot.telegram.commands.auto_optimization import run_optimization_command, view_optimization_results_command, register_optimization_command_handlers

# Fonction principale pour enregistrer toutes les commandes
def register_all_commands(application):
    """
    Enregistre tous les gestionnaires de commandes pour l'application Telegram.
    
    Args:
        application: L'instance de l'application Telegram
    """
    # Enregistrement des commandes de base
    register_command_handlers(application)
    
    # Enregistrement des commandes de statut
    register_status_command_handlers(application)
    
    # Enregistrement des commandes d'analyse
    register_analyze_command_handlers(application)
    
    # Enregistrement des commandes de backtesting
    register_backtest_command_handlers(application)
    
    # Enregistrement des commandes de stratégie
    register_strategy_command_handlers(application)
    
    # Enregistrement des commandes d'optimisation
    register_optimization_command_handlers(application)
    
    return application 