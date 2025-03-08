#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module d'Interfaces pour GBPBot
==============================

Ce module expose toutes les interfaces abstraites utilisées dans le GBPBot,
permettant une conception orientée objet cohérente et modulaire.
"""

# Importer les interfaces de base
from .base_sniper import BaseSniper
from .base_arbitrage import BaseArbitrage, ArbitrageOpportunity
from .base_monitor import BaseMonitor, MonitoringType
from .base_token_analyzer import BaseTokenAnalyzer, TokenRiskLevel, TokenAnalysisAspect
from .base_optimizer import BaseOptimizer, OptimizationType, OptimizationProfile

# Re-exporter les interfaces pour faciliter l'accès
__all__ = [
    # Interfaces Sniper
    'BaseSniper',
    
    # Interfaces Arbitrage
    'BaseArbitrage',
    'ArbitrageOpportunity',
    
    # Interfaces Monitoring
    'BaseMonitor',
    'MonitoringType',
    
    # Interfaces Analyse de Tokens
    'BaseTokenAnalyzer',
    'TokenRiskLevel',
    'TokenAnalysisAspect',
    
    # Interfaces Optimisation
    'BaseOptimizer',
    'OptimizationType',
    'OptimizationProfile'
] 