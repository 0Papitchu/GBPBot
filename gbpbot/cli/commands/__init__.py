"""
Module de commandes pour le CLI de GBPBot
=======================================

Ce module contient les implémentations des commandes disponibles
dans l'interface en ligne de commande (CLI) du GBPBot.
"""

from gbpbot.cli.commands.arbitrage import start_arbitrage_module
from gbpbot.cli.commands.sniping import start_sniping_module
from gbpbot.cli.commands.backtesting import start_backtesting_module
from gbpbot.cli.commands.ai_assistant import start_ai_assistant_module
from gbpbot.cli.commands.module_control import stop_module

__all__ = [
    'start_arbitrage_module',
    'start_sniping_module',
    'start_backtesting_module',
    'start_ai_assistant_module',
    'stop_module'
] 