# Documentation Technique GBPBot

> **Note de mise à jour**: Cette documentation technique a été mise à jour le 04/03/2024 pour correspondre exactement à l'implémentation actuelle du code source. Les noms de méthodes et leurs signatures ont été vérifiés et corrigés pour refléter fidèlement le code source.

## Table des matières

1. [Architecture globale](#1-architecture-globale)
2. [Modules principaux](#2-modules-principaux)
   - [2.1 Mempool Sniping](#21-mempool-sniping)
   - [2.2 Gas Optimizer](#22-gas-optimizer)
   - [2.3 Bundle Checker](#23-bundle-checker)
   - [2.4 Core](#24-core)
   - [2.5 API Server](#25-api-server)
   - [2.6 Web Dashboard](#26-web-dashboard)
   - [2.7 Interface CLI](#27-interface-cli)
3. [Points d'entrée et scripts de lancement](#3-points-dentrée-et-scripts-de-lancement)
4. [Flux de données](#4-flux-de-données)
5. [API Reference](#5-api-reference)
6. [Sécurité](#6-sécurité)
7. [Monitoring et Maintenance](#7-monitoring-et-maintenance)
8. [Déploiement](#8-déploiement)

---

## 1. Architecture globale

GBPBot est un système de trading automatisé pour les crypto-monnaies, spécialisé dans le sniping de nouveaux tokens et l'arbitrage. L'architecture est modulaire et se compose des éléments suivants:

### Composants principaux

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│  Mempool        │     │  Gas            │     │  Bundle         │
│  Sniping        │     │  Optimizer      │     │  Checker        │
│                 │     │                 │     │                 │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         └───────────────┬───────┴───────────────┬───────┘
                         │                       │
                ┌────────▼────────┐     ┌────────▼────────┐
                │                 │     │                 │
                │  Core           │     │  API Server     │
                │  Engine         │◄────►                 │
                │                 │     │                 │
                └────────┬────────┘     └────────┬────────┘
                         │                       │
                         │              ┌────────▼────────┐
                         │              │                 │
                         └──────────────►  Web            │
                                        │  Dashboard      │
                                        │                 │
                                        └─────────────────┘
```

### Flux d'exécution

1. Le module **Mempool Sniping** surveille la mempool pour détecter les nouvelles paires de trading.
2. Le module **Gas Optimizer** calcule les prix de gas optimaux pour les transactions.
3. Le module **Bundle Checker** analyse les transactions groupées pour détecter les manipulations.
4. Le **Core Engine** coordonne les différents modules et exécute les stratégies de trading.
5. L'**API Server** expose les fonctionnalités du bot via une API REST.
6. Le **Web Dashboard** fournit une interface utilisateur pour contrôler et surveiller le bot.

### Modes de fonctionnement

- **Mode Simulation**: Exécute les stratégies sans effectuer de transactions réelles.
- **Mode Testnet**: Exécute les stratégies sur un réseau de test (Fuji, Goerli, etc.).
- **Mode Production**: Exécute les stratégies sur le réseau principal (Mainnet).

---

## 2. Modules principaux

### 2.1 Mempool Sniping

Le module `mempool_sniping.py` est responsable de la détection et de l'exécution rapide des transactions sur les nouvelles paires de trading.

#### Classes principales

- **MempoolSniping**: Classe principale pour le sniping via surveillance du mempool.

#### Méthodes clés

| Méthode | Description | Paramètres | Retour |
|---------|-------------|------------|--------|
| `__init__` | Initialise le module de sniping mempool | `web3_provider`, `wallet_private_key`, `min_liquidity`, `max_buy_amount`, `gas_boost_percentage`, `target_dexes`, `blacklisted_tokens` | - |
| `start_monitoring` | Démarre la surveillance du mempool | - | `bool` |
| `stop_monitoring` | Arrête la surveillance du mempool | - | `bool` |
| `_process_pending_transaction` | Traite une transaction détectée dans le mempool | `tx_hash` | `dict` |
| `_execute_sniping` | Exécute un achat sur un token détecté | `pair_info` | `dict` |
| `_check_token_eligibility` | Vérifie si un token est éligible pour le sniping | `token_address` | `bool` |
| `_calculate_slippage` | Calcule le slippage pour une transaction | `token_address`, `amount` | `float` |

#### Configuration

```python
# Exemple de configuration
mempool_config = {
    "min_liquidity": 1.0,  # Liquidité minimale en ETH/BNB
    "max_buy_amount": 0.1,  # Montant maximum à dépenser par transaction
    "gas_boost_percentage": 10,  # Pourcentage d'augmentation du gas
    "target_dexes": [
        "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D",  # Uniswap V2
        "0x10ED43C718714eb63d5aA57B78B54704E256024E"   # PancakeSwap
    ],
    "blacklisted_tokens": [
        "0x0000000000000000000000000000000000000000"
    ]
}
```

### 2.2 Gas Optimizer

Le module `gas_optimizer.py` est responsable de l'optimisation des frais de gas pour maximiser les chances de succès des transactions tout en minimisant les coûts.

#### Classes principales

- **GasOptimizer**: Classe principale pour l'optimisation des frais de gas.

#### Méthodes clés

| Méthode | Description | Paramètres | Retour |
|---------|-------------|------------|--------|
| `__init__` | Initialise le module d'optimisation du gas | `web3_provider`, `gas_api_key`, `max_gas_price`, `min_gas_price`, `gas_price_strategy`, `update_interval`, `chain_id` | - |
| `get_gas_price` | Obtient le prix du gas actuel | `strategy` (optionnel) | `float` |
| `get_gas_price_wei` | Obtient le prix du gas actuel en wei | `strategy` (optionnel) | `int` |
| `optimize_gas_for_transaction` | Optimise le gas pour une transaction | `tx_params`, `strategy` (optionnel) | `dict` |
| `_simulate_transaction` | Simule une transaction pour vérifier sa validité | `tx_data`, `gas_price` | `bool` |
| `get_gas_price_history` | Obtient l'historique des prix du gas | `hours` | `list` |
| `_detect_gas_wars` | Détecte si une guerre de gas est en cours | - | `bool` |

#### Configuration

```python
# Exemple de configuration
gas_config = {
    "max_gas_price": 500.0,  # Prix maximum du gas en gwei
    "min_gas_price": 1.0,    # Prix minimum du gas en gwei
    "gas_price_strategy": "aggressive",  # Stratégie de prix du gas
    "update_interval": 15,   # Intervalle de mise à jour en secondes
    "chain_id": 1            # ID de la chaîne (1 = Ethereum, 56 = BSC)
}
```

### 2.3 Bundle Checker

Le module `bundle_checker.py` est responsable de la détection des transactions groupées qui peuvent indiquer une manipulation de marché ou une opportunité de trading.

#### Classes principales

- **BundleChecker**: Classe principale pour la détection des bundles de transactions.

#### Méthodes clés

| Méthode | Description | Paramètres | Retour |
|---------|-------------|------------|--------|
| `__init__` | Initialise le module de détection des bundles | `web3_provider`, `bundle_threshold`, `time_window`, `target_tokens`, `target_dexes` | - |
| `analyze_block` | Analyse un bloc pour détecter les bundles | `block_number` (optionnel) | `list` |
| `_detect_bundles` | Détecte les bundles dans un ensemble de transactions | `token_txs` | `list` |
| `_calculate_manipulation_score` | Calcule un score de manipulation pour un ensemble de transactions | `txs`, `wallets` | `float` |
| `is_token_manipulated` | Détermine si un token est manipulé | `token_address`, `threshold` (optionnel) | `tuple(bool, float)` |
| `get_token_transactions` | Obtient les transactions pour un token spécifique | `token_address`, `block_range` (optionnel) | `list` |
| `get_wallet_activity` | Obtient l'activité d'un wallet | `wallet_address` | `dict` |

#### Configuration

```python
# Exemple de configuration
bundle_config = {
    "bundle_threshold": 3,  # Nombre minimum de transactions pour considérer un bundle
    "time_window": 60,      # Fenêtre de temps pour regrouper les transactions (en secondes)
    "target_tokens": [],    # Liste des tokens à surveiller (vide = tous)
    "target_dexes": [
        "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D",  # Uniswap V2
        "0x10ED43C718714eb63d5aA57B78B54704E256024E"   # PancakeSwap
    ]
}
```

### 2.4 Core

Le module `main.py` est le cœur du système, coordonnant les différents modules et exécutant les stratégies de trading.

#### Classes principales

- **GBPBot**: Classe principale du bot.

#### Méthodes clés

| Méthode | Description | Paramètres | Retour |
|---------|-------------|------------|--------|
| `__init__` | Initialise le bot | `simulation_mode`, `is_testnet` | - |
| `start` | Démarre le bot | - | `bool` |
| `_run_bot` | Exécute la boucle principale du bot | - | - |
| `_monitor_opportunities` | Surveille les opportunités de trading | - | - |
| `_check_balances` | Vérifie les soldes des tokens | - | `dict` |
| `_execute_trade` | Exécute un trade | `from_token`, `to_token`, `amount`, `slippage` | `dict` |
| `_calculate_performance` | Calcule les performances du bot | - | `dict` |
| `_get_trade_history` | Obtient l'historique des trades | `limit` | `list` |
| `_change_mode` | Change le mode du bot | `mode` | `bool` |

#### Configuration

```python
# Exemple de configuration
bot_config = {
    "simulation_mode": True,  # Mode simulation
    "is_testnet": False,      # Utilisation du testnet
    "max_trades_per_day": 10, # Nombre maximum de trades par jour
    "max_gas_per_trade": 0.01, # Montant maximum de gas par trade (en ETH/BNB)
    "stop_loss_percentage": 10, # Pourcentage de stop loss
    "take_profit_percentage": 20 # Pourcentage de take profit
}
```

### 2.5 API Server

Le module `api_server.py` expose les fonctionnalités du bot via une API REST sécurisée.

#### Routes principales

| Route | Méthode | Description | Paramètres | Retour |
|-------|---------|-------------|------------|--------|
| `/status` | GET | Obtient le statut du bot | - | JSON |
| `/trades` | GET | Obtient l'historique des trades | `limit` (optionnel) | JSON |
| `/performance` | GET | Obtient les performances du bot | - | JSON |
| `/change_mode` | POST | Change le mode du bot | `mode` | JSON |
| `/start_sniping` | POST | Démarre le sniping | `simulation_mode` | JSON |
| `/stop_sniping` | POST | Arrête le sniping | - | JSON |
| `/start_arbitrage` | POST | Démarre l'arbitrage | `simulation_mode` | JSON |
| `/stop_arbitrage` | POST | Arrête l'arbitrage | - | JSON |
| `/start_mev` | POST | Démarre le MEV | `simulation_mode` | JSON |
| `/stop_mev` | POST | Arrête le MEV | - | JSON |
| `/stop_bot` | POST | Arrête le bot | - | JSON |
| `/start_bot` | POST | Démarre le bot | `simulation_mode` | JSON |
| `/reset_bot` | POST | Réinitialise le bot | - | JSON |
| `/health` | GET | Vérifie l'état de santé de l'API | - | JSON |

#### Sécurité

- Authentification par clé API
- Limitation du taux de requêtes
- Liste blanche d'IPs
- Support HTTPS

### 2.6 Web Dashboard

Le module `web_dashboard.py` fournit une interface utilisateur pour contrôler et surveiller le bot.

#### Fonctionnalités principales

- Affichage du statut du bot
- Visualisation des performances
- Historique des trades
- Configuration des stratégies
- Contrôle du bot (démarrage, arrêt, etc.)
- Alertes et notifications

### 2.7 Interface CLI

L'interface CLI (Command Line Interface) fournit une interface utilisateur en ligne de commande pour contrôler le bot sans modifier le code source.

#### Architecture

```
┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │
│  CLI Interface  │────►│  Configuration  │
│  (cli_interface)│     │  Manager        │
│                 │     │                 │
└────────┬────────┘     └────────┬────────┘
         │                       │
         │                       │
         │                       │
         ▼                       ▼
┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │
│  Bot Controller │◄────┤  User Config    │
│                 │     │  Storage        │
│                 │     │                 │
└────────┬────────┘     └─────────────────┘
         │
         │
         ▼
┌─────────────────┐
│                 │
│  GBPBot Core    │
│                 │
│                 │
└─────────────────┘
```

#### Composants principaux

- **CLI Interface** (`cli_interface.py`): Gère l'affichage des menus et l'interaction utilisateur
- **Configuration Manager**: Gère la lecture et l'écriture des configurations
- **Bot Controller**: Interface entre l'interface CLI et le core du bot
- **User Config Storage**: Stocke les configurations utilisateur dans `~/.gbpbot/user_config.json`

#### Fonctionnalités

- Menus interactifs pour la configuration et le contrôle du bot
- Sauvegarde et chargement automatique des configurations
- Affichage en temps réel des performances et des statistiques
- Contrôle du bot pendant l'exécution (pause, arrêt, etc.)

---

## 3. Points d'entrée et scripts de lancement

GBPBot offre plusieurs points d'entrée et scripts de lancement pour différents cas d'utilisation.

### 3.1 Points d'entrée principaux

| Fichier | Description | Utilisation |
|---------|-------------|-------------|
| `gbpbot_cli.py` | Point d'entrée pour l'interface CLI interactive | `python gbpbot_cli.py` |
| `main.py` | Point d'entrée principal du bot | `python main.py` |
| `run_bot.py` | Script simplifié pour lancer le bot en mode simulation | `python run_bot.py` |
| `api_server.py` | Serveur API REST | `python api_server.py` |
| `web_dashboard.py` | Interface web | `python web_dashboard.py` |
| `start_servers.py` | Lance tous les services | `python start_servers.py` |

### 3.2 Scripts batch

| Fichier | Description | Utilisation |
|---------|-------------|-------------|
| `launch_gbpbot_cli.bat` | Lance l'interface CLI interactive (Windows) | Double-clic ou `launch_gbpbot_cli.bat` |
| `run_bot.bat` | Lance le bot en mode simulation (Windows) | Double-clic ou `run_bot.bat` |

### 3.3 Flux d'exécution

#### Interface CLI Interactive

```
gbpbot_cli.py
  └── cli_interface.py::main()
      ├── CLIInterface::__init__()
      │   └── _load_user_config()
      └── CLIInterface::start()
          ├── _show_main_menu()
          ├── _handle_menu_selection()
          └── _launch_bot()
              └── GBPBot::start()
```

#### Mode Simulation Rapide

```
run_bot.py
  ├── sys.path.append()  # Ajoute le répertoire courant au PYTHONPATH
  ├── GBPBot::__init__()
  │   └── _initialize_simulation()
  └── asyncio.run(bot.start())
      └── GBPBot::start()
```

---

## 4. Flux de données

### 4.1 Flux de sniping

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│  Mempool        │     │  Gas            │     │  Core           │
│  Sniping        │     │  Optimizer      │     │  Engine         │
│                 │     │                 │     │                 │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         │  1. Détecte           │                       │
         │  nouvelle paire       │                       │
         │                       │                       │
         ├───────────────────────►                       │
         │                       │  2. Calcule           │
         │                       │  gas optimal          │
         │                       │                       │
         │                       ├───────────────────────►
         │                       │                       │  3. Exécute
         │                       │                       │  transaction
         │                       │                       │
         │                       │                       ├───────────┐
         │                       │                       │           │
         │                       │                       │           │
         │                       │                       │           │
         │                       │                       │           │
         │                       │                       │           │
         │                       │                       │           │
         │                       │                       │           ▼
         │                       │                       │     ┌─────────────┐
         │                       │                       │     │             │
         │                       │                       │     │  Blockchain │
         │                       │                       │     │             │
         │                       │                       │     └─────────────┘
```

### 4.2 Flux d'analyse de bundle

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│  Bundle         │     │  Core           │     │  API Server     │
│  Checker        │     │  Engine         │     │                 │
│                 │     │                 │     │                 │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         │  1. Détecte           │                       │
         │  bundle                │                       │
         │                       │                       │
         ├───────────────────────►                       │
         │                       │  2. Analyse           │
         │                       │  opportunité          │
         │                       │                       │
         │                       ├───────────────────────►
         │                       │                       │  3. Notifie
         │                       │                       │  utilisateur
         │                       │                       │
         │                       │                       ├───────────┐
         │                       │                       │           │
         │                       │                       │           │
         │                       │                       │           │
         │                       │                       │           │
         │                       │                       │           │
         │                       │                       │           │
         │                       │                       │           ▼
         │                       │                       │     ┌─────────────┐
         │                       │                       │     │             │
         │                       │                       │     │  Dashboard  │
         │                       │                       │     │             │
         │                       │                       │     └─────────────┘
```

---

## 5. API Reference

### 5.1 API Endpoints

#### Statut et informations

```
GET /status
```

Retourne le statut actuel du bot.

**Réponse**:
```json
{
  "status": "running",
  "mode": "simulation",
  "uptime": 3600,
  "mempool_sniping": {
    "active": true,
    "transactions_processed": 1000
  },
  "gas_optimizer": {
    "active": true,
    "current_gas_price": 20.5
  },
  "bundle_checker": {
    "active": true,
    "bundles_detected": 5
  }
}
```

#### Historique des trades

```
GET /trades
```

Retourne l'historique des trades.

**Paramètres**:
- `limit` (optionnel): Nombre maximum de trades à retourner (défaut: 20)

**Réponse**:
```json
{
  "trades": [
    {
      "id": "1",
      "timestamp": "2023-03-01T12:00:00Z",
      "token": "0x1234567890abcdef1234567890abcdef12345678",
      "token_name": "Example Token",
      "action": "buy",
      "amount": 0.1,
      "price": 100.0,
      "gas_used": 0.005,
      "status": "completed"
    }
  ]
}
```

#### Performances

```
GET /performance
```

Retourne les performances du bot.

**Réponse**:
```json
{
  "total_profit": 1.5,
  "total_trades": 10,
  "successful_trades": 8,
  "failed_trades": 2,
  "success_rate": 80.0,
  "average_profit": 0.15,
  "average_gas_cost": 0.003,
  "roi": 150.0
}
```

#### Démarrer le sniping

```
POST /start_sniping
```

Démarre le sniping.

**Corps de la requête**:
```json
{
  "simulation_mode": true
}
```

**Réponse**:
```json
{
  "success": true,
  "message": "Sniping démarré"
}
```

### 5.2 Authentification

Toutes les requêtes (sauf `/health`) nécessitent une authentification par clé API.

**En-tête**:
```
x-api-key: votre-clé-api
```

### 5.3 Gestion des erreurs

Les erreurs sont retournées au format JSON avec un code HTTP approprié.

**Exemple**:
```json
{
  "error": "Authentification requise"
}
```

---

## 6. Sécurité

### 6.1 Authentification API

Le module `security_config.py` gère la sécurité de l'API.

#### Méthodes clés

| Méthode | Description | Paramètres | Retour |
|---------|-------------|------------|--------|
| `_generate_secure_api_key` | Génère une clé API sécurisée | - | `str` |
| `_parse_ip_whitelist` | Parse la liste des IPs autorisées | `ip_whitelist_str` | `list` |
| `is_ip_allowed` | Vérifie si une IP est autorisée | `ip_str` | `bool` |
| `get_ssl_context` | Obtient le contexte SSL pour Flask | - | `tuple` |
| `check_failed_attempts` | Vérifie les tentatives échouées | `ip` | `bool` |
| `record_failed_attempt` | Enregistre une tentative échouée | `ip` | - |
| `reset_failed_attempts` | Réinitialise les tentatives échouées | `ip` | - |

### 6.2 Protection contre les attaques

- **Rate Limiting**: Limite le nombre de requêtes par IP
- **IP Whitelist**: Restreint l'accès à certaines IPs
- **Brute Force Protection**: Bloque les IPs après trop de tentatives échouées
- **HTTPS**: Chiffre les communications

### 6.3 Stockage sécurisé des clés

Les clés privées et les clés API sont stockées dans un fichier `.env` qui n'est pas versionné.

---

## 7. Monitoring et Maintenance

### 7.1 Monitoring

Le module `monitor_production.py` surveille l'état de santé du bot en production.

#### Méthodes clés

| Méthode | Description | Paramètres | Retour |
|---------|-------------|------------|--------|
| `start_monitoring` | Démarre la surveillance | - | - |
| `_check_health` | Vérifie l'état de santé | - | - |
| `_check_system_resources` | Vérifie les ressources système | - | - |
| `_check_api_server` | Vérifie l'état du serveur API | - | `bool` |
| `_check_dashboard` | Vérifie l'état du dashboard | - | `bool` |
| `_check_module` | Vérifie l'état d'un module | `module_name` | `bool` |
| `_restart_service` | Redémarre un service | `service_name` | `bool` |
| `_send_alert` | Envoie une alerte | `message` | - |

### 7.2 Alertes

Le système peut envoyer des alertes par email et Telegram en cas de problème.

#### Configuration des alertes

```python
# Exemple de configuration
alert_config = {
    "enable_email_alerts": True,
    "email_from": "alerts@gbpbot.com",
    "email_to": "admin@example.com",
    "email_smtp_server": "smtp.gmail.com",
    "email_smtp_port": 587,
    "email_smtp_user": "alerts@gbpbot.com",
    "email_smtp_password": "password",
    "enable_telegram_alerts": True,
    "telegram_bot_token": "your-bot-token",
    "telegram_chat_id": "your-chat-id"
}
```

### 7.3 Logs

Le système utilise `loguru` pour la journalisation.

#### Fichiers de logs

- `bot.log`: Log principal du bot
- `gbpbot_api.log`: Log de l'API
- `gbpbot_dashboard.log`: Log du dashboard
- `monitor.log`: Log du moniteur de production
- `deployment.log`: Log du déploiement

---

## 8. Déploiement

### 8.1 Déploiement en production

Le module `deploy_production.py` automatise le déploiement en production.

#### Méthodes clés

| Méthode | Description | Paramètres | Retour |
|---------|-------------|------------|--------|
| `deploy` | Déploie le bot en production | - | - |
| `_create_directories` | Crée les répertoires nécessaires | - | - |
| `_backup_files` | Sauvegarde les fichiers existants | - | - |
| `_generate_ssl_certificates` | Génère les certificats SSL | - | - |
| `_update_env_variables` | Met à jour les variables d'environnement | - | - |
| `_run_tests` | Exécute les tests avant le déploiement | - | - |
| `_start_servers` | Démarre les serveurs | - | - |
| `_check_servers` | Vérifie que les serveurs sont bien démarrés | - | - |
| `create_systemd_service` | Crée un service systemd | - | `bool` |

### 8.2 Tests de production

Le module `production_test.py` vérifie que tous les composants fonctionnent correctement avant le déploiement.

#### Méthodes clés

| Méthode | Description | Paramètres | Retour |
|---------|-------------|------------|--------|
| `run_all_tests` | Exécute tous les tests | - | - |
| `test_web3_connection` | Teste la connexion Web3 | - | - |
| `test_mempool_sniping` | Teste le module de sniping mempool | - | - |
| `test_gas_optimizer` | Teste le module d'optimisation du gas | - | - |
| `test_bundle_checker` | Teste le module de détection des bundles | - | - |
| `test_servers` | Teste les serveurs API et dashboard | - | - |
| `test_security` | Teste la sécurité | - | - |
| `test_integration` | Teste l'intégration des différents modules | - | - |

---

## Mise à jour de la documentation

Cette documentation est mise à jour manuellement. Pour une documentation générée automatiquement à partir du code, utilisez un outil comme Sphinx.

```bash
# Installer Sphinx
pip install sphinx

# Générer la documentation
cd docs
sphinx-build -b html source build
```

---

© 2023 GBPBot Team. Tous droits réservés. 