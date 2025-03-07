# Système de Backtesting GBPBot

## Introduction

Le système de backtesting de GBPBot est un outil puissant conçu pour tester et optimiser les stratégies de trading avant leur déploiement en environnement réel. Il permet de simuler des conditions de marché réalistes, d'analyser les performances des stratégies et d'optimiser leurs paramètres pour maximiser les rendements.

## Caractéristiques principales

- **Chargement de données historiques** depuis diverses sources (Binance, KuCoin, Gate.io, CSV, JSON)
- **Simulation réaliste du marché** avec slippage, frais de transaction, latence et impact sur le marché
- **Analyse complète des performances** avec calcul de métriques (Sharpe, Sortino, drawdown, etc.)
- **Visualisation des résultats** avec graphiques d'équité, drawdowns et rendements mensuels
- **Optimisation des paramètres** via différentes méthodes (grille, aléatoire, bayésienne, génétique)
- **Comparaison de stratégies** pour identifier les plus performantes
- **Stratégies prêtes à l'emploi** pour l'arbitrage, le momentum, le mean-reversion, etc.
- **Architecture extensible** permettant de créer facilement de nouvelles stratégies

## Architecture du système

Le système de backtesting est composé de plusieurs modules interconnectés :

```
gbpbot/backtesting/
├── backtesting_engine.py    # Moteur principal de backtesting
├── data_loader.py           # Chargement des données historiques
├── market_simulator.py      # Simulation des conditions de marché
├── performance_analyzer.py  # Analyse des performances
├── parameter_optimizer.py   # Optimisation des paramètres
├── base_strategy.py         # Classe de base pour les stratégies
└── strategies/              # Implémentations de stratégies
    ├── arbitrage_strategy.py    # Stratégies d'arbitrage
    ├── momentum_strategy.py     # Stratégies de momentum
    └── mean_reversion_strategy.py # Stratégies de mean-reversion
```

## Installation et prérequis

Le système de backtesting nécessite les dépendances suivantes :

```bash
pip install pandas numpy matplotlib scikit-learn scikit-optimize optuna
```

Pour les fonctionnalités avancées d'optimisation bayésienne et génétique :

```bash
pip install scikit-optimize
```

## Utilisation de base

### 1. Initialisation du moteur de backtesting

```python
from gbpbot.backtesting.backtesting_engine import BacktestingEngine

# Configuration du backtest
config = {
    "RESULTS_DIR": "backtest_results",
    "DATA_DIR": "historical_data",
    "REPORT_DIR": "backtest_reports",
    "SLIPPAGE_MODEL": "fixed",
    "SLIPPAGE_RATE": 0.001,  # 0.1% de slippage
    "TRANSACTION_FEE_RATE": 0.001,  # 0.1% de frais de transaction
    "EXECUTION_LATENCY": 1,  # 1 seconde de latence
    "EXECUTION_PROBABILITY": 0.99,  # 99% de probabilité d'exécution
}

# Initialiser le moteur de backtesting
engine = BacktestingEngine(config)
```

### 2. Exécution d'un backtest

```python
from gbpbot.backtesting.arbitrage_strategy import SimpleArbitrageStrategy

# Paramètres de la stratégie
strategy_params = {
    "symbol": "BTC/USDT",
    "market_a": "binance",
    "market_b": "kucoin",
    "min_spread_pct": 0.5,
    "trade_size": 0.1,
    "max_position": 1.0,
    "cooldown_minutes": 5
}

# Période de backtest
start_date = "2023-01-01"
end_date = "2023-01-31"

# Solde initial
initial_balance = {
    "USDT": 10000.0,
    "BTC": 0.0
}

# Exécuter le backtest
results = engine.run_backtest(
    strategy_class=SimpleArbitrageStrategy,
    strategy_params=strategy_params,
    symbols=["binance:BTC/USDT", "kucoin:BTC/USDT"],
    start_date=start_date,
    end_date=end_date,
    initial_balance=initial_balance,
    timeframe="1m",
    data_source="binance"
)

# Afficher les résultats
print(f"Solde final: {results['final_balance']}")
print(f"Nombre de trades: {len(results['trades'])}")
print(f"Métriques de performance: {results['performance_metrics']}")
print(f"Rapport généré: {results['report_path']}")
```

### 3. Comparaison de stratégies

```python
from gbpbot.backtesting.arbitrage_strategy import (
    SimpleArbitrageStrategy,
    TriangularArbitrageStrategy,
    StatisticalArbitrageStrategy
)

# Liste des stratégies à comparer
strategies = [
    (SimpleArbitrageStrategy, simple_arbitrage_params),
    (TriangularArbitrageStrategy, triangular_arbitrage_params),
    (StatisticalArbitrageStrategy, statistical_arbitrage_params)
]

# Exécuter la comparaison
comparison_results = engine.compare_strategies(
    strategies=strategies,
    symbols=["binance:BTC/USDT", "kucoin:BTC/USDT", "binance:ETH/BTC", "binance:ETH/USDT"],
    start_date=start_date,
    end_date=end_date,
    initial_balance=initial_balance,
    timeframe="1m",
    data_source="binance"
)
```

### 4. Optimisation des paramètres

```python
# Grille de paramètres à optimiser
param_grid = {
    "min_spread_pct": [0.1, 0.2, 0.3, 0.5, 0.7, 1.0],
    "trade_size": [0.05, 0.1, 0.2, 0.5],
    "cooldown_minutes": [1, 5, 10, 15, 30]
}

# Exécuter l'optimisation
optimization_results = engine.optimize_strategy(
    strategy_class=SimpleArbitrageStrategy,
    param_grid=param_grid,
    symbols=["binance:BTC/USDT", "kucoin:BTC/USDT"],
    start_date=start_date,
    end_date=end_date,
    initial_balance=initial_balance,
    timeframe="1m",
    data_source="binance",
    optimization_method="grid",
    maximize_metric="sharpe_ratio",
    n_iter=50
)

# Afficher les meilleurs paramètres
print(f"Meilleurs paramètres: {optimization_results['best_params']}")
print(f"Meilleure valeur: {optimization_results['best_value']}")
```

## Création d'une stratégie personnalisée

Pour créer une stratégie personnalisée, il suffit d'hériter de la classe `BaseStrategy` et d'implémenter les méthodes requises :

```python
from gbpbot.backtesting.base_strategy import BaseStrategy

class MyCustomStrategy(BaseStrategy):
    def __init__(self, market_simulator, **kwargs):
        super().__init__(market_simulator, **kwargs)
        
        # Initialiser les paramètres spécifiques à la stratégie
        self.param1 = kwargs.get("param1", default_value)
        self.param2 = kwargs.get("param2", default_value)
        
        # Initialiser l'état de la stratégie
        self.state = {}
    
    def on_tick(self, timestamp, symbol, data):
        # Logique de trading basée sur les ticks
        pass
    
    def on_bar(self, timestamp, symbol, data):
        # Logique de trading basée sur les barres (chandeliers)
        
        # Exemple : Stratégie simple de moyenne mobile
        if len(data) < 20:
            return
        
        # Calculer les moyennes mobiles
        short_ma = data["close"].rolling(window=10).mean().iloc[-1]
        long_ma = data["close"].rolling(window=20).mean().iloc[-1]
        
        # Générer des signaux
        if short_ma > long_ma:
            # Signal d'achat
            self.place_market_order(symbol, "buy", self.trade_size)
        elif short_ma < long_ma:
            # Signal de vente
            self.place_market_order(symbol, "sell", self.trade_size)
```

## Configuration avancée

### Modèles de slippage

Le système prend en charge différents modèles de slippage :

- **fixed** : Slippage fixe en pourcentage
- **volume_based** : Slippage basé sur le volume de l'ordre
- **volatility_based** : Slippage basé sur la volatilité du marché

```python
config = {
    "SLIPPAGE_MODEL": "volume_based",
    "SLIPPAGE_FACTOR": 0.1,
    "VOLUME_IMPACT_THRESHOLD": 0.01
}
```

### Modèles d'impact sur le marché

Le système prend en charge différents modèles d'impact sur le marché :

- **linear** : Impact linéaire en fonction de la taille de l'ordre
- **square_root** : Impact en racine carrée de la taille de l'ordre
- **custom** : Impact personnalisé

```python
config = {
    "MARKET_IMPACT_MODEL": "square_root",
    "MARKET_IMPACT_FACTOR": 0.0001
}
```

### Méthodes d'optimisation

Le système prend en charge différentes méthodes d'optimisation :

- **grid** : Recherche par grille (exhaustive)
- **random** : Recherche aléatoire
- **bayesian** : Optimisation bayésienne
- **genetic** : Algorithme génétique

```python
config = {
    "OPTIMIZATION_METHOD": "bayesian",
    "N_CALLS": 100,
    "N_INITIAL_POINTS": 10,
    "RANDOM_STATE": 42
}
```

## Exemples

Des exemples d'utilisation du système de backtesting sont disponibles dans le répertoire `examples/` :

- `backtest_arbitrage_example.py` : Exemple de backtesting de stratégies d'arbitrage
- `backtest_momentum_example.py` : Exemple de backtesting de stratégies de momentum
- `backtest_mean_reversion_example.py` : Exemple de backtesting de stratégies de mean-reversion
- `optimization_example.py` : Exemple d'optimisation de paramètres

## Limitations actuelles

- Le système ne prend pas encore en charge les ordres conditionnels (stop-loss, take-profit)
- La simulation de l'impact sur le marché est simplifiée
- Les données historiques doivent être préchargées avant l'exécution du backtest

## Roadmap

- Ajout de stratégies supplémentaires (momentum, mean-reversion)
- Amélioration de l'interface utilisateur pour la configuration des backtests
- Intégration avec le système de reporting global
- Optimisation des performances pour les grands ensembles de données
- Support des ordres conditionnels
- Amélioration des modèles d'impact sur le marché
- Intégration avec le système de trading en temps réel

## Contribution

Les contributions au système de backtesting sont les bienvenues ! N'hésitez pas à soumettre des pull requests pour ajouter de nouvelles fonctionnalités, corriger des bugs ou améliorer la documentation. 