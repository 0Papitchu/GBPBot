"""
Module CLI pour GBPBot
=====================

Ce module fournit une interface en ligne de commande pour GBPBot,
permettant d'accéder facilement aux fonctionnalités du bot.
"""

from gbpbot.cli.menu import display_main_menu, display_modules_menu, run_cli
from gbpbot.cli.commands import (
    start_arbitrage_module,
    start_sniping_module,
    start_backtesting_module,
    start_ai_assistant_module,
    stop_module
)

__all__ = [
    'run_cli',
    'display_main_menu',
    'display_modules_menu',
    'start_arbitrage_module',
    'start_sniping_module',
    'start_backtesting_module',
    'start_ai_assistant_module',
    'stop_module'
] 