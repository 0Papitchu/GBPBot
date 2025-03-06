# Module de Machine Learning pour GBPBot

Ce module fournit des fonctionnalités d'apprentissage automatique pour optimiser les stratégies de trading du GBPBot, en particulier pour le sniping de memecoins, le frontrunning et l'arbitrage.

## Fonctionnalités principales

- **Prédiction d'opportunités** : Détermination automatique des meilleures opportunités de trading
- **Optimisation des paramètres** : Ajustement dynamique des seuils de trading
- **Analyse de performance** : Suivi des résultats et amélioration continue
- **Auto-apprentissage** : Le modèle s'améliore en fonction des résultats passés

## Architecture

Le module de ML se compose de deux composants principaux :

1. **TradingPredictionModel** : Modèle de prédiction basé sur le machine learning
   - Utilise Gradient Boosting pour les prédictions
   - Recueille et analyse les données de performance
   - S'entraîne automatiquement à intervalles réguliers

2. **MLIntegrator** : Interface entre le modèle et les stratégies
   - Évalue les opportunités de trading
   - Optimise les paramètres des stratégies
   - Fournit des statistiques de performance

## Utilisation

### Configuration

Le module se configure via les paramètres suivants dans le fichier `.env` :

```
# Machine Learning
ML_ENABLED=true                     # Activer l'optimisation par machine learning
ML_MODEL_PATH=models/gbpbot_ml.pkl  # Chemin vers le modèle ML entraîné
PREDICTION_CONFIDENCE_THRESHOLD=0.7 # Seuil de confiance pour les prédictions
MIN_TRAINING_SAMPLES=100            # Nombre minimum d'échantillons pour l'entraînement
RETRAINING_INTERVAL_HOURS=24        # Intervalle de réentraînement en heures
```

### Intégration dans les stratégies

Pour intégrer le ML dans une stratégie de trading :

```python
from gbpbot.machine_learning import create_ml_integrator

# Créer l'intégrateur ML
ml_integrator = create_ml_integrator(config=config)

# Évaluer une opportunité de sniping
should_snipe, confidence, optimized_params = ml_integrator.evaluate_sniping_opportunity(token_data)

# Enregistrer le résultat pour l'apprentissage
ml_integrator.record_transaction_result("sniping", token_data, result)
```

## Données d'apprentissage

Le modèle apprend à partir des données suivantes :

### Sniping
- **Entrée** : Liquidité, market cap, nombre de détenteurs, âge du token, volume...
- **Sortie** : Probabilité de profit

### Frontrunning
- **Entrée** : Valeur de la transaction, prix du gaz, liquidité, position dans le mempool...
- **Sortie** : Probabilité de profit

### Arbitrage
- **Entrée** : Écart de prix, liquidité sur les DEX, coût du gaz, volatilité de la paire...
- **Sortie** : Probabilité de profit

## Fonctionnement interne

1. **Collecte de données** : À chaque transaction, les données pertinentes sont stockées
2. **Entraînement** : Le modèle s'entraîne périodiquement sur les données collectées
3. **Prédiction** : Pour chaque opportunité, le modèle calcule une probabilité de succès
4. **Optimisation** : Les paramètres sont ajustés en fonction des performances historiques

## Prérequis

Pour utiliser ce module, vous devez installer les dépendances suivantes :

```bash
pip install scikit-learn numpy pandas
```

## Gestion via l'interface

Une interface dédiée est disponible dans le menu principal :

1. **Activer/Désactiver le ML** : Allumer ou éteindre les fonctionnalités ML
2. **Statistiques du modèle** : Voir les performances des modèles
3. **Entraînement forcé** : Déclencher l'entraînement des modèles manuellement
4. **Configuration** : Ajuster les paramètres ML 