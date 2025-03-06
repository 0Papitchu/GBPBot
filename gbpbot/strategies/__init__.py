"""
Trading strategies for GBPBot.

This module contains various trading strategies that can be used with GBPBot.
"""

from gbpbot.strategies.arbitrage import ArbitrageStrategy
from gbpbot.strategies.sniping import SnipingStrategy
from gbpbot.strategies.auto_mode import AutoModeStrategy

__all__ = ['ArbitrageStrategy', 'SnipingStrategy', 'AutoModeStrategy'] 