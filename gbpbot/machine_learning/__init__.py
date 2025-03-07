"""
Modules de Machine Learning pour GBPBot
======================================

Ce package contient les différents modules d'apprentissage automatique
et d'intelligence artificielle utilisés par GBPBot pour l'analyse et
l'optimisation des stratégies de trading.
"""

from typing import Dict, Any, Optional

# Exporter les fonctions de création des analyseurs/predicteurs
from gbpbot.machine_learning.contract_analyzer import create_contract_analyzer
from gbpbot.machine_learning.lightweight_models import create_model_manager
from gbpbot.machine_learning.prediction_model import create_prediction_model
from gbpbot.machine_learning.volatility_predictor import create_volatility_predictor

__all__ = [
    "create_contract_analyzer", 
    "create_model_manager",
    "create_prediction_model",
    "create_volatility_predictor"
] 