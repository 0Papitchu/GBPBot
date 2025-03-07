# Structure du Projet GBPBot

Ce document détaille la structure des répertoires et fichiers du projet GBPBot, expliquant le rôle de chaque composant et la façon dont ils interagissent.

## Vue d'Ensemble

GBPBot est organisé selon une architecture modulaire, avec une séparation claire des responsabilités entre les différents composants. La structure suit les principes de conception orientée objet et assure une maintenabilité et une extensibilité optimales.

## Architecture de Haut Niveau

```
gbpbot/
├── core/                 # Composants fondamentaux du système
├── blockchain/           # Interfaces avec les blockchains (Solana, AVAX, Sonic)
├── strategies/           # Stratégies de trading
├── ai/                   # Intégration d'intelligence artificielle
├── machine_learning/     # Modèles de machine learning
├── backtesting/          # Système de backtesting et simulation
├── cli/                  # Interface en ligne de commande
├── dashboard/            # Interface web
├── telegram/             # Interface Telegram
└── utils/                # Utilitaires communs
```

## Composants Principaux

### Core

Le répertoire `core/` contient les composants fondamentaux du système:

```
core/
├── config/               # Gestion de la configuration
├── transaction/          # Gestion des transactions et signatures
├── price_feed/           # Sources de données de prix en temps réel
├── rpc/                  # Gestion des connexions RPC
├── analysis/             # Moteur d'analyse et scoring
├── security/             # Vérification et sécurité
└── optimization/         # Optimisations MEV et Gas
```

### Blockchain

Le répertoire `blockchain/` contient les interfaces avec les différentes blockchains:

```
blockchain/
├── solana/               # Client Solana et utilitaires
├── avalanche/            # Client Avalanche et utilitaires
└── sonic/                # Client Sonic et utilitaires
```

### Strategies

Le répertoire `strategies/` contient les implémentations des stratégies de trading:

```
strategies/
├── arbitrage/            # Stratégies d'arbitrage
├── sniping/              # Stratégies de sniping
├── scalping/             # Stratégies de scalping
└── mev/                  # Stratégies MEV/Frontrunning
```

### AI

Le répertoire `ai/` contient les modules d'intégration d'intelligence artificielle:

```
ai/
├── llm_provider.py       # Interface avec les modèles de langage
├── openai_client.py      # Client pour OpenAI
├── llama_client.py       # Client pour LLaMA (local)
├── market_analyzer.py    # Analyse de marché avec IA
├── token_contract_analyzer.py # Analyse de contrats avec IA
├── prompts/              # Templates de prompts
└── config.py             # Configuration des modèles d'IA
```

### Machine Learning

Le répertoire `machine_learning/` contient les modèles de machine learning:

```
machine_learning/
├── models/               # Modèles préentraînés et configurations
├── lightweight_models.py # Modèles légers optimisés
├── market_microstructure_analyzer.py # Analyse de microstructure
├── volatility_predictor.py # Prédiction de volatilité
└── token_scorer.py       # Scoring de tokens
```

### Backtesting

Le répertoire `backtesting/` contient le système de backtesting et simulation:

```
backtesting/
├── engine.py             # Moteur principal de backtesting
├── data_loader.py        # Chargement des données historiques
├── market_simulator.py   # Simulation des conditions de marché
├── performance_analyzer.py # Analyse des performances
├── parameter_optimizer.py # Optimisation des paramètres
└── base_strategy.py      # Classe de base pour les stratégies
```

### CLI

Le répertoire `cli/` contient l'interface en ligne de commande:

```
cli/
├── menu.py               # Menus principaux
├── display.py            # Fonctions d'affichage
├── commands/             # Commandes spécifiques
│   ├── arbitrage.py      # Commandes pour l'arbitrage
│   ├── sniping.py        # Commandes pour le sniping
│   ├── backtesting.py    # Commandes pour le backtesting
│   ├── ai_assistant.py   # Commandes pour l'assistant IA
│   └── module_control.py # Gestion des modules
└── utils.py              # Utilitaires pour le CLI
```

### Dashboard

Le répertoire `dashboard/` contient l'interface web:

```
dashboard/
├── server.py             # Serveur web (FastAPI)
├── static/               # Fichiers statiques (CSS, JS)
│   ├── css/              # Styles CSS
│   ├── js/               # Scripts JavaScript
│   └── img/              # Images
├── templates/            # Templates HTML
└── api/                  # API pour l'interface web
```

### Telegram

Le répertoire `telegram/` contient l'interface Telegram:

```
telegram/
├── bot.py                # Bot Telegram principal
├── commands/             # Commandes Telegram
└── handlers/             # Gestionnaires de messages
```

### Utils

Le répertoire `utils/` contient des utilitaires communs:

```
utils/
├── logging/              # Configuration et gestion des logs
├── caching/              # Système de mise en cache
├── concurrency/          # Utilitaires pour la concurrence
└── formatting/           # Formatage des données
```

## Scripts Principaux

- `run_gbpbot.py`: Point d'entrée principal pour démarrer le GBPBot
- `start_gbpbot.bat` / `start_gbpbot.sh`: Scripts de lancement pour Windows/Linux
- `run_dashboard.bat` / `run_dashboard.sh`: Scripts pour démarrer uniquement le dashboard

## Dépendances Externes

GBPBot utilise plusieurs bibliothèques externes:

- **Blockchain**: solana-py, solders, web3-py
- **IA/ML**: OpenAI API, llama-cpp-python, PyTorch, TensorFlow Lite
- **Web**: FastAPI, websockets, aiohttp
- **Bases de données**: SQLite, Redis (optionnel)
- **Monitoring**: Prometheus, Grafana (optionnel)

## Conventions de Codage

Le projet suit les conventions suivantes:

- **Nommage**: snake_case pour les variables et fonctions, PascalCase pour les classes
- **Documentation**: Docstrings pour toutes les fonctions et classes
- **Type Annotations**: Annotations de type pour améliorer la lisibilité et la vérification
- **Tests**: Tests unitaires et d'intégration pour les composants critiques
- **Logging**: Utilisation cohérente du système de logging 