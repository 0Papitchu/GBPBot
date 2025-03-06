"""
Module de Machine Learning pour GBPBot
======================================

Ce module fournit des fonctionnalités d'apprentissage automatique pour optimiser
les stratégies de trading du GBPBot.
"""

from gbpbot.machine_learning.ml_integrator import MLIntegrator, create_ml_integrator

try:
    from gbpbot.machine_learning.prediction_model import TradingPredictionModel, create_prediction_model
    PREDICTION_MODEL_AVAILABLE = True
except ImportError:
    PREDICTION_MODEL_AVAILABLE = False

__all__ = ['MLIntegrator', 'create_ml_integrator']
if PREDICTION_MODEL_AVAILABLE:
    __all__.extend(['TradingPredictionModel', 'create_prediction_model']) 