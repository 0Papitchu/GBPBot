# Module de Machine Learning pour GBPBot

Ce module fournit des fonctionnalités d'apprentissage automatique pour optimiser les stratégies de trading du GBPBot, en particulier pour le sniping de memecoins, le frontrunning, l'arbitrage et la prédiction de volatilité.

## Fonctionnalités principales

- **Prédiction d'opportunités** : Détermination automatique des meilleures opportunités de trading
- **Optimisation des paramètres** : Ajustement dynamique des seuils de trading
- **Analyse de performance** : Suivi des résultats et amélioration continue
- **Auto-apprentissage** : Le modèle s'améliore en fonction des résultats passés
- **Prédiction de volatilité** : Anticipation des mouvements de prix à court terme (1-15min)

## Architecture

Le module de ML se compose de plusieurs composants principaux :

1. **TradingPredictionModel** : Modèle de prédiction basé sur le machine learning
   - Utilise Gradient Boosting pour les prédictions
   - Recueille et analyse les données de performance
   - S'entraîne automatiquement à intervalles réguliers

2. **MLIntegrator** : Interface entre le modèle et les stratégies
   - Évalue les opportunités de trading
   - Optimise les paramètres des stratégies
   - Fournit des statistiques de performance

3. **VolatilityPredictor** : Prédiction de la volatilité future des memecoins
   - Utilise des modèles LSTM pour la prédiction de séries temporelles
   - Analyse les données historiques pour détecter des patterns
   - Fournit des recommandations adaptées au niveau de volatilité prédit
   - S'entraîne sur plusieurs horizons temporels (1min, 5min, 15min)

4. **ContractAnalyzer** : Analyse des contrats intelligents pour détecter les risques
   - Détecte les fonctions malveillantes dans le code
   - Évalue le risque global d'un contrat
   - Combine approche classique et modèles d'IA

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

# Prédiction de Volatilité
VOLATILITY_ENABLED=true                    # Activer la prédiction de volatilité
VOLATILITY_MODELS_DIR=data/volatility_models  # Répertoire des modèles de volatilité
VOLATILITY_THRESHOLD_HIGH=0.05             # Seuil de volatilité élevée
VOLATILITY_THRESHOLD_LOW=0.01              # Seuil de volatilité faible
USE_GPU_FOR_PREDICTION=true                # Utiliser le GPU pour les prédictions
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

### Utilisation du prédicteur de volatilité

```python
from gbpbot.machine_learning import create_volatility_predictor

# Créer le prédicteur de volatilité
volatility_predictor = create_volatility_predictor(config={
    "volatility_threshold_high": 0.05,
    "volatility_threshold_low": 0.01
})

# Ajouter des données historiques pour l'entraînement
volatility_predictor.add_historical_data("MEMECOIN", historical_price_data)

# Entraîner les modèles
training_results = volatility_predictor.train_models()

# Prédire la volatilité future
prediction = await volatility_predictor.predict_volatility(current_token_data, timeframe="15min")

# Adapter la stratégie en fonction des recommandations
if prediction["success"]:
    volatility_level = prediction["volatility_level"]
    confidence = prediction["confidence_score"]
    recommendations = prediction["recommendations"]
    
    # Ajuster les paramètres de trading en fonction des recommandations
    if volatility_level == "élevée":
        # Stratégie pour haute volatilité
        stop_loss = set_tight_stop_loss(current_price)
        take_profit = set_scaled_take_profit(current_price)
    else:
        # Stratégie pour volatilité normale/faible
        stop_loss = set_normal_stop_loss(current_price)
        take_profit = set_normal_take_profit(current_price)
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

### Prédiction de volatilité
- **Entrée** : Prix OHLCV, rendements, volatilité historique, indicateurs techniques...
- **Sortie** : Niveau de volatilité prédit, recommandations d'ajustement de stratégie

## Fonctionnement interne

1. **Collecte de données** : À chaque transaction, les données pertinentes sont stockées
2. **Entraînement** : Le modèle s'entraîne périodiquement sur les données collectées
3. **Prédiction** : Pour chaque opportunité, le modèle calcule une probabilité de succès
4. **Optimisation** : Les paramètres sont ajustés en fonction des performances historiques
5. **Adaptation** : Les stratégies s'adaptent aux conditions de marché prédites

## Prérequis

Pour utiliser ce module, vous devez installer les dépendances suivantes :

```bash
# Dépendances de base
pip install scikit-learn numpy pandas

# Pour la prédiction de volatilité
pip install tensorflow matplotlib xgboost lightgbm

# Version GPU (optionnel, recommandé)
pip install tensorflow-gpu
```

## Gestion via l'interface

Une interface dédiée est disponible dans le menu principal :

1. **Activer/Désactiver le ML** : Allumer ou éteindre les fonctionnalités ML
2. **Statistiques du modèle** : Voir les performances des modèles
3. **Entraînement forcé** : Déclencher l'entraînement des modèles manuellement
4. **Configuration** : Ajuster les paramètres ML
5. **Prédiction de volatilité** : Visualiser les prévisions de volatilité pour les tokens surveillés 