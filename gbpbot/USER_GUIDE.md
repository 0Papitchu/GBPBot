# Guide d'Utilisation GBPBot

> **Note de mise à jour**: Ce guide d'utilisation a été vérifié le 10/03/2024 et est à jour avec la version actuelle du bot. Toutes les commandes, configurations et fonctionnalités décrites correspondent à l'implémentation actuelle, incluant les nouveaux modules de monitoring et de gestion des wallets.

## Table des matières

1. [Introduction](#1-introduction)
2. [Installation](#2-installation)
3. [Configuration](#3-configuration)
   - [3.1 Fichier .env](#31-fichier-env)
   - [3.2 Configuration des stratégies](#32-configuration-des-stratégies)
   - [3.3 Configuration de la sécurité](#33-configuration-de-la-sécurité)
4. [Utilisation du Bot](#4-utilisation-du-bot)
   - [4.1 Méthodes de lancement](#41-méthodes-de-lancement)
   - [4.2 Interface CLI Interactive](#42-interface-cli-interactive)
   - [4.3 Modes de fonctionnement](#43-modes-de-fonctionnement)
   - [4.4 Stratégies disponibles](#44-stratégies-disponibles)
5. [Interface Web](#5-interface-web)
   - [5.1 Tableau de bord](#51-tableau-de-bord)
   - [5.2 Historique des trades](#52-historique-des-trades)
   - [5.3 Configuration](#53-configuration)
   - [5.4 Alertes](#54-alertes)
6. [API REST](#6-api-rest)
7. [Monitoring et Gestion des Wallets](#7-monitoring-et-gestion-des-wallets)
   - [7.1 Monitoring Système](#71-monitoring-système)
   - [7.2 Monitoring de Performance](#72-monitoring-de-performance)
   - [7.3 Gestion Centralisée des Wallets](#73-gestion-centralisée-des-wallets)
   - [7.4 Intégration Telegram](#74-intégration-telegram)
8. [Maintenance](#8-maintenance)
9. [Dépannage](#9-dépannage)
10. [FAQ](#10-faq)

---

## 1. Introduction

GBPBot est un bot de trading automatisé pour les crypto-monnaies, spécialisé dans le sniping de nouveaux tokens et l'arbitrage. Ce guide vous aidera à configurer et utiliser efficacement le bot pour maximiser vos profits tout en minimisant les risques.

### Fonctionnalités principales

- **Sniping de mempool**: Détecte et exécute des transactions sur les nouvelles paires de trading avant qu'elles ne soient largement connues.
- **Optimisation du gas**: Calcule automatiquement les prix de gas optimaux pour maximiser les chances de succès des transactions.
- **Détection de bundles**: Analyse les transactions groupées pour détecter les manipulations de marché.
- **Interface web**: Contrôle et surveillance du bot via une interface web intuitive.
- **API REST**: Intégration avec d'autres systèmes via une API REST sécurisée.
- **Modes multiples**: Simulation, testnet et production pour tester vos stratégies avant de les déployer.

---

## 2. Installation

### Prérequis

- Python 3.8+
- Accès à un nœud Ethereum/BSC (Infura, Alchemy, etc.)
- Un wallet avec des fonds suffisants pour les transactions

### Installation rapide

1. Clonez le dépôt:
   ```bash
   git clone https://github.com/votre-username/gbpbot.git
   cd gbpbot
   ```

2. Créez un environnement virtuel:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Sur Windows: venv\Scripts\activate
   ```

3. Installez les dépendances:
   ```bash
   pip install -r requirements.txt
   ```

4. Copiez le fichier d'exemple de configuration:
   ```bash
   cp .env.example .env
   ```

5. Modifiez le fichier `.env` avec vos informations (voir section [Configuration](#3-configuration)).

---

## 3. Configuration

### 3.1 Fichier .env

Le fichier `.env` contient toutes les variables d'environnement nécessaires au fonctionnement du bot. La configuration de l'environnement est une étape cruciale pour la sécurité et le bon fonctionnement du GBPBot.

#### Types de fichiers d'environnement

GBPBot utilise plusieurs types de fichiers d'environnement :

- `.env` : Configuration principale utilisée par le bot
- `.env.local` : Configuration locale avec vos données sensibles (non commité dans Git)
- `.env.example` : Modèle de configuration sans données sensibles
- `.env.backup_*` : Sauvegardes automatiques de votre configuration
- `.env.optimized` : Configuration avec paramètres de performance optimisés

#### Outils de gestion des fichiers d'environnement

GBPBot fournit des outils pour gérer vos fichiers d'environnement :

- **Windows** : Utilisez `configure_env.bat` à la racine du projet
- **Linux/Mac** : Utilisez `python scripts/setup_env.py [commande]`

Ces outils vous permettent de :
- Créer des sauvegardes de votre `.env`
- Initialiser `.env` à partir de `.env.local`
- Valider vos configurations

#### Configuration initiale

Pour configurer correctement GBPBot, suivez ces étapes :

1. Copiez le fichier d'exemple :
   ```bash
   cp .env.example .env.local
   ```

2. Modifiez `.env.local` avec vos informations personnelles :
   ```bash
   # Sur Windows
   notepad .env.local
   # Sur Linux/Mac
   nano .env.local
   ```

3. Utilisez l'outil de configuration pour générer `.env` :
   ```bash
   # Sur Windows
   configure_env.bat
   # Puis sélectionnez l'option 2
   
   # Sur Linux/Mac
   python scripts/setup_env.py 2
   ```

#### Variables de configuration essentielles

```ini
# CONFIGURATION GÉNÉRALE
BOT_MODE=manual                     # manual, auto, telegram
DEFAULT_BLOCKCHAIN=solana           # avalanche, solana
DEBUG_MODE=false                    # active les logs détaillés
ENVIRONMENT=development             # development, production
LOG_LEVEL=INFO                      # DEBUG, INFO, WARNING, ERROR

# CONNEXION BLOCKCHAIN
AVALANCHE_RPC_URL=https://api.avax.network/ext/bc/C/rpc
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com

# WALLETS (INFORMATIONS SENSIBLES)
PRIVATE_KEY=your_private_key_here   # Clé privée de votre wallet
WALLET_ADDRESS=your_address_here    # Adresse de votre wallet

# CONFIGURATION TELEGRAM
TELEGRAM_BOT_TOKEN=your_token_here  # Token du bot Telegram
TELEGRAM_CHAT_ID=your_chat_id       # ID pour recevoir les notifications
TELEGRAM_AUTHORIZED_USERS=user_id   # ID des utilisateurs autorisés à contrôler le bot

# CONFIGURATION API
BINANCE_API_KEY=your_api_key        # Clé API Binance
BINANCE_API_SECRET=your_api_secret  # Secret API Binance

# PARAMÈTRES DE TRADING
MAX_SLIPPAGE=2.0                    # % max de slippage accepté
MAX_TRADE_AMOUNT_USD=500            # Montant max par trade en USD
```

#### Protection des données sensibles

⚠️ **IMPORTANT** : Les fichiers `.env` contiennent des informations sensibles et ne doivent jamais être partagés ou publiés.

Bonnes pratiques de sécurité :
1. Utilisez toujours `.env.local` pour vos données sensibles
2. N'incluez jamais `.env` ou `.env.local` dans vos dépôts Git
3. Effectuez des sauvegardes régulières avec l'outil de configuration
4. Utilisez des clés privées dédiées pour le bot, différentes de vos wallets principaux
5. Limitez l'accès au bot Telegram en configurant `TELEGRAM_AUTHORIZED_USERS`

#### Documentation détaillée

Pour plus d'informations sur la gestion des fichiers d'environnement, consultez :
- `docs/ENVIRONMENT_MANAGEMENT.md` : Guide complet de gestion des environnements
- `docs/TELEGRAM_INTERFACE.md` : Configuration détaillée de l'interface Telegram
- `docs/TROUBLESHOOTING.md` : Résolution des problèmes liés à la configuration

### 3.2 Configuration des stratégies

Les stratégies sont configurées dans des fichiers JSON dans le répertoire `config/strategies/`. Voici un exemple de configuration pour la stratégie de sniping:

```json
{
  "name": "mempool_sniping",
  "enabled": true,
  "parameters": {
    "min_liquidity": 1.0,
    "max_buy_amount": 0.1,
    "gas_boost_percentage": 10,
    "target_dexes": [
      "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D",
      "0x10ED43C718714eb63d5aA57B78B54704E256024E"
    ],
    "blacklisted_tokens": [
      "0x0000000000000000000000000000000000000000"
    ]
  }
}
```

#### Paramètres de la stratégie de sniping

| Paramètre | Description | Valeur par défaut | Recommandation |
|-----------|-------------|-------------------|----------------|
| `min_liquidity` | Liquidité minimale en ETH/BNB | 1.0 | 1.0 - 5.0 |
| `max_buy_amount` | Montant maximum à dépenser par transaction | 0.1 | 0.01 - 0.5 |
| `gas_boost_percentage` | Pourcentage d'augmentation du gas | 10 | 5 - 20 |
| `target_dexes` | Liste des DEX à surveiller | Uniswap V2, PancakeSwap | Dépend de la chaîne |
| `blacklisted_tokens` | Liste des tokens à ignorer | [] | Tokens connus pour être des arnaques |

### 3.3 Configuration de la sécurité

La sécurité est configurée dans le fichier `config/security.json`:

```json
{
  "api_key_length": 32,
  "max_failed_attempts": 5,
  "failed_attempts_window": 3600,
  "ip_whitelist": [
    "127.0.0.1",
    "192.168.1.100"
  ],
  "ssl_cert_path": "ssl/cert.pem",
  "ssl_key_path": "ssl/key.pem"
}
```

#### Paramètres de sécurité

| Paramètre | Description | Valeur par défaut | Recommandation |
|-----------|-------------|-------------------|----------------|
| `api_key_length` | Longueur de la clé API | 32 | 32 - 64 |
| `max_failed_attempts` | Nombre maximum de tentatives échouées | 5 | 3 - 10 |
| `failed_attempts_window` | Fenêtre de temps pour les tentatives échouées (en secondes) | 3600 | 1800 - 7200 |
| `ip_whitelist` | Liste des IPs autorisées | ["127.0.0.1"] | IPs de confiance |
| `ssl_cert_path` | Chemin vers le certificat SSL | "ssl/cert.pem" | - |
| `ssl_key_path` | Chemin vers la clé SSL | "ssl/key.pem" | - |

---

## 4. Utilisation du Bot

### 4.1 Méthodes de lancement

GBPBot offre plusieurs méthodes de lancement adaptées à différents besoins :

#### Interface CLI Interactive (Recommandée)

L'interface CLI interactive vous permet de configurer et contrôler le bot via un menu interactif.

```bash
# Lancement via script batch (Windows)
launch_gbpbot_cli.bat

# Lancement direct
python gbpbot_cli.py
```

#### Mode Simulation Rapide

Lance directement le bot en mode simulation avec les paramètres par défaut, sans passer par les menus.

```bash
# Lancement via script batch (Windows)
run_bot.bat

# Lancement direct
python run_bot.py
```

#### Lancement des composants individuels

Pour les utilisateurs avancés qui souhaitent lancer les composants individuellement :

```bash
# Lancement du bot principal
python main.py

# Lancement du serveur API
python api_server.py

# Lancement du dashboard web
python web_dashboard.py

# Lancement de tous les services
python start_servers.py
```

#### Arrêt du bot

Pour arrêter le bot, utilisez `Ctrl+C` dans le terminal, utilisez l'option correspondante dans l'interface CLI, ou utilisez l'API/dashboard web.

### 4.2 Interface CLI Interactive

L'interface CLI (Command Line Interface) interactive offre un moyen convivial de contrôler le bot sans avoir à modifier le code source.

#### Navigation dans les menus

L'interface utilise un système de menus numérotés. Pour sélectionner une option, entrez simplement le numéro correspondant et appuyez sur Entrée.

#### Menu Principal

Le menu principal propose les options suivantes :

1. **Lancer le bot** - Démarre le bot avec la configuration actuelle
2. **Configurer les paramètres** - Accède au menu de configuration
3. **Afficher la configuration actuelle** - Montre les paramètres actuels
4. **Afficher les statistiques** - Affiche les performances du bot

#### Configuration via l'interface CLI

Le menu de configuration vous permet de personnaliser :

- **Mode de fonctionnement** : TEST, SIMULATION ou LIVE
- **Réseau blockchain** : Mainnet ou Testnet
- **Stratégies actives** : Choisir quelles stratégies utiliser
- **Paramètres de trading** : Seuils de profit, gestion des risques, etc.
- **Balances simulées** : Montants initiaux pour le mode simulation

#### Sauvegarde des configurations

Les configurations sont automatiquement sauvegardées dans `~/.gbpbot/user_config.json` et rechargées au prochain démarrage.

#### Commandes pendant l'exécution

Pendant que le bot est en cours d'exécution via l'interface CLI, vous pouvez utiliser ces commandes :

- **P** - Pause/Reprendre le bot
- **S** - Arrêter le bot
- **C** - Afficher la configuration actuelle
- **B** - Afficher les balances actuelles
- **T** - Afficher l'historique des transactions
- **H** - Afficher l'aide

### 4.3 Modes de fonctionnement

Le bot peut fonctionner dans trois modes différents:

#### Mode Simulation

En mode simulation, le bot exécute toutes les stratégies mais n'effectue pas de transactions réelles. C'est utile pour tester vos stratégies sans risquer de fonds.

Pour activer le mode simulation:
```
SIMULATION_MODE=true
```

#### Mode Testnet

En mode testnet, le bot effectue des transactions réelles mais sur un réseau de test (Goerli, Fuji, etc.). C'est utile pour tester vos stratégies avec de petites sommes.

Pour activer le mode testnet:
```
SIMULATION_MODE=false
IS_TESTNET=true
```

#### Mode Production

En mode production, le bot effectue des transactions réelles sur le réseau principal (Mainnet). C'est le mode à utiliser pour le trading réel.

Pour activer le mode production:
```
SIMULATION_MODE=false
IS_TESTNET=false
```

### 4.4 Stratégies disponibles

#### Sniping de mempool

La stratégie de sniping de mempool surveille la mempool pour détecter les nouvelles paires de trading et exécute des transactions avant qu'elles ne soient largement connues.

**Quand l'utiliser**: Pour être parmi les premiers à acheter un nouveau token.

**Risques**: Les nouveaux tokens peuvent être des arnaques ou des honeypots.

**Configuration recommandée**:
```json
{
  "min_liquidity": 2.0,
  "max_buy_amount": 0.05,
  "gas_boost_percentage": 15
}
```

#### Arbitrage

La stratégie d'arbitrage surveille les différences de prix entre les DEX et exécute des transactions pour profiter de ces différences.

**Quand l'utiliser**: Lorsque les marchés sont volatils et que les prix varient entre les DEX.

**Risques**: Les opportunités d'arbitrage peuvent disparaître rapidement.

**Configuration recommandée**:
```json
{
  "min_profit_percentage": 1.0,
  "max_slippage": 0.5,
  "gas_priority": "medium"
}
```

#### MEV (Maximal Extractable Value)

La stratégie MEV surveille les transactions en attente pour détecter les opportunités de sandwich attacks, frontrunning, etc.

**Quand l'utiliser**: Pour les utilisateurs avancés qui comprennent les risques.

**Risques**: Très compétitif, nécessite des connexions rapides et des fonds importants.

**Configuration recommandée**:
```json
{
  "min_transaction_value": 10.0,
  "gas_boost_percentage": 20,
  "target_protocols": ["uniswap", "sushiswap"]
}
```

---

## 5. Interface Web

L'interface web est accessible à l'adresse `http://localhost:8080` (ou `https://localhost:8080` si HTTPS est activé).

### 5.1 Tableau de bord

![Dashboard](https://example.com/dashboard.png)

Le tableau de bord affiche les informations suivantes:

1. **Statut du bot**: Indique si le bot est en cours d'exécution, en pause ou arrêté.
2. **Mode de fonctionnement**: Simulation, testnet ou production.
3. **Performances**: Profit total, nombre de trades, taux de réussite, etc.
4. **Graphiques**: Évolution du profit, du prix du gas, etc.
5. **Alertes**: Notifications importantes concernant le bot.

### 5.2 Historique des trades

![Trades](https://example.com/trades.png)

L'historique des trades affiche les informations suivantes pour chaque trade:

1. **ID**: Identifiant unique du trade.
2. **Timestamp**: Date et heure du trade.
3. **Token**: Adresse et nom du token.
4. **Action**: Achat ou vente.
5. **Montant**: Montant de la transaction.
6. **Prix**: Prix du token au moment de la transaction.
7. **Gas utilisé**: Montant de gas utilisé pour la transaction.
8. **Statut**: Complété, en attente ou échoué.

### 5.3 Configuration

![Configuration](https://example.com/configuration.png)

La page de configuration permet de modifier les paramètres du bot:

1. **Paramètres généraux**: Mode de fonctionnement, limites, etc.
2. **Stratégies**: Configuration des stratégies de trading.
3. **Sécurité**: Configuration de la sécurité de l'API.
4. **Alertes**: Configuration des alertes par email et Telegram.

### 5.4 Alertes

![Alerts](https://example.com/alerts.png)

La page d'alertes affiche les alertes récentes et permet de configurer les règles d'alerte:

1. **Alertes de profit**: Notification lorsqu'un profit est réalisé.
2. **Alertes de perte**: Notification lorsqu'une perte est réalisée.
3. **Alertes de gas**: Notification lorsque le prix du gas dépasse un seuil.
4. **Alertes de sécurité**: Notification en cas de tentative d'accès non autorisée.

---

## 6. API REST

L'API REST est accessible à l'adresse `http://localhost:5000` (ou `https://localhost:5000` si HTTPS est activé).

### Authentification

Toutes les requêtes (sauf `/health`) nécessitent une authentification par clé API.

**En-tête**:
```
x-api-key: votre-clé-api
```

### Endpoints principaux

#### Statut du bot

```
GET /status
```

Retourne le statut actuel du bot.

**Exemple de réponse**:
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

**Exemple de réponse**:
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

**Exemple de réponse**:
```json
{
  "success": true,
  "message": "Sniping démarré"
}
```

Pour une liste complète des endpoints, consultez la [documentation technique](TECHNICAL_DOCUMENTATION.md#4-api-reference).

---

## 7. Monitoring et Gestion des Wallets

GBPBot intègre désormais des modules avancés de monitoring et de gestion des wallets pour assurer un fonctionnement optimal et sécurisé de vos opérations de trading.

### 7.1 Monitoring Système

Le module `SystemMonitor` surveille en temps réel les ressources système utilisées par GBPBot.

#### Démarrage du monitoring

```python
from gbpbot.monitoring import get_system_monitor

# Obtenir l'instance du moniteur système
system_monitor = get_system_monitor()

# Démarrer le monitoring avec un intervalle personnalisé (en secondes)
system_monitor.start_monitoring(interval=10.0)  # Par défaut: 5.0
```

#### Configuration des seuils d'alerte

```python
# Configurer les seuils d'alerte
system_monitor.set_thresholds(
    cpu_threshold=90,        # Alerte si CPU > 90%
    memory_threshold=85,     # Alerte si Mémoire > 85%
    disk_threshold=95,       # Alerte si Disque > 95%
    temperature_threshold=80 # Alerte si Température > 80°C
)
```

#### Consultation des métriques système

```python
# Obtenir les métriques système actuelles
metrics = system_monitor.get_metrics()
print(f"CPU: {metrics['cpu_percent']}%")
print(f"Mémoire: {metrics['memory_percent']}%")
print(f"Disque: {metrics['disk_percent']}%")
print(f"Réseau: {metrics['network_io']}")
```

#### Gestion des alertes

```python
# Ajouter un callback pour les alertes
def alert_callback(alert_type, message, value, threshold):
    print(f"ALERTE {alert_type}: {message} (Valeur: {value}, Seuil: {threshold})")

system_monitor.add_alert_callback(alert_callback)
```

#### Arrêt du monitoring

```python
# Arrêter le monitoring
system_monitor.stop_monitoring()
```

### 7.2 Monitoring de Performance

Le module `PerformanceMonitor` suit les performances de trading et calcule des métriques essentielles.

#### Enregistrement des transactions

```python
from gbpbot.monitoring import get_performance_monitor
from gbpbot.monitoring.performance_monitor import TradeRecord

# Obtenir l'instance du moniteur de performance
perf_monitor = get_performance_monitor()

# Créer un enregistrement de transaction
trade = TradeRecord(
    trade_id="trade_123",
    token_symbol="SOL",
    token_address="So11111111111111111111111111111111111111112",
    blockchain="solana",
    strategy="arbitrage",
    buy_price=50.0,
    buy_amount=1.0,
    buy_timestamp=1646732800,
    buy_tx_hash="tx_hash_buy",
    sell_price=55.0,
    sell_amount=0.98,  # Après frais
    sell_timestamp=1646736400,
    sell_tx_hash="tx_hash_sell",
    fees_usd=2.5,
    profit_loss_usd=2.0,
    status="completed"
)

# Ajouter la transaction
perf_monitor.add_trade(trade)

# Mettre à jour une transaction existante
perf_monitor.update_trade("trade_123", status="completed", sell_price=55.0)
```

#### Consultation des statistiques

```python
# Obtenir les statistiques globales
stats = perf_monitor.get_statistics()
print(f"ROI total: {stats['total_roi']}%")
print(f"Profit total: ${stats['total_profit_usd']}")
print(f"Nombre de trades: {stats['total_trades']}")
print(f"Ratio de réussite: {stats['win_rate']}%")

# Obtenir les statistiques par blockchain
solana_stats = perf_monitor.get_statistics(blockchain="solana")

# Obtenir les statistiques par stratégie
arbitrage_stats = perf_monitor.get_statistics(strategy="arbitrage")
```

#### Génération de rapports

```python
# Générer un rapport détaillé
report = perf_monitor.generate_report(
    start_date="2023-03-01",
    end_date="2023-03-31",
    blockchain="solana",
    strategy="arbitrage"
)

# Exporter le rapport au format CSV
perf_monitor.export_trades("trades_report.csv", start_date="2023-03-01")
```

### 7.3 Gestion Centralisée des Wallets

Le module `WalletManager` offre une gestion centralisée et sécurisée des wallets sur différentes blockchains.

#### Création et import de wallets

```python
from gbpbot.modules.wallet_manager import WalletManager

# Initialiser le gestionnaire de wallets
wallet_manager = WalletManager()

# Créer un nouveau wallet
new_wallet = wallet_manager.create_wallet(
    blockchain="solana",
    name="trading_wallet"
)
print(f"Nouvelle adresse: {new_wallet.address}")
print(f"Clé privée: {new_wallet.private_key}")

# Importer un wallet existant
imported_wallet = wallet_manager.import_wallet(
    blockchain="avalanche",
    private_key="votre_clé_privée",
    name="wallet_principal"
)
```

#### Gestion des wallets

```python
# Lister tous les wallets disponibles
wallets = wallet_manager.list_wallets()
for wallet in wallets:
    print(f"{wallet.name} ({wallet.blockchain}): {wallet.address}")

# Obtenir un wallet spécifique
wallet = wallet_manager.get_wallet("trading_wallet")

# Vérifier les blockchains supportées
supported_chains = wallet_manager.get_supported_blockchains()
print(f"Blockchains supportées: {supported_chains}")
```

#### Gestion des balances

```python
# Obtenir la balance d'un wallet spécifique
balance = wallet_manager.get_balance("trading_wallet")
print(f"Balance: {balance.amount} {balance.symbol}")

# Obtenir toutes les balances (tous wallets)
all_balances = wallet_manager.get_all_balances()
for wallet_name, balances in all_balances.items():
    print(f"Wallet: {wallet_name}")
    for balance in balances:
        print(f"  {balance.symbol}: {balance.amount} (${balance.usd_value})")
```

#### Sécurité des wallets

```python
# Activer le chiffrement des clés privées
wallet_manager.enable_encryption("mot_de_passe_fort")

# Sauvegarder les wallets (clés chiffrées)
wallet_manager.backup_wallets("wallets_backup.json")

# Restaurer des wallets depuis une sauvegarde
wallet_manager.restore_wallets("wallets_backup.json", "mot_de_passe_fort")
```

### 7.4 Intégration Telegram

GBPBot permet d'accéder aux fonctionnalités de monitoring et de gestion des wallets directement via Telegram.

#### Commandes de monitoring système

```
/system_status - Affiche le statut actuel des ressources système
/set_threshold cpu 90 - Configure le seuil d'alerte CPU à 90%
/start_monitoring - Démarre le monitoring système
/stop_monitoring - Arrête le monitoring système
```

#### Commandes de performance

```
/performance - Affiche les statistiques de performance globales
/trades - Affiche les dernières transactions
/report daily - Génère un rapport quotidien
/report weekly - Génère un rapport hebdomadaire
```

#### Commandes de gestion des wallets

```
/wallets - Liste tous les wallets disponibles
/balance <wallet_name> - Affiche la balance d'un wallet spécifique
/all_balances - Affiche toutes les balances de tous les wallets
/create_wallet solana trading_wallet - Crée un nouveau wallet
```

Pour plus d'informations détaillées sur l'utilisation de ces modules, veuillez consulter le [Guide de Monitoring](../docs/MONITORING_GUIDE.md).

---

## 8. Maintenance

### Mises à jour

Pour mettre à jour le bot:

1. Arrêtez tous les services:
   ```bash
   python stop_servers.py
   ```

2. Sauvegardez vos fichiers de configuration:
   ```bash
   cp .env .env.backup
   cp -r config config.backup
   ```

3. Mettez à jour le code:
   ```bash
   git pull
   ```

4. Installez les nouvelles dépendances:
   ```bash
   pip install -r requirements.txt
   ```

5. Redémarrez les services:
   ```bash
   python start_servers.py
   ```

### Sauvegardes

Il est recommandé de sauvegarder régulièrement les fichiers suivants:

- `.env`: Variables d'environnement
- `config/`: Fichiers de configuration
- `logs/`: Fichiers de logs
- `data/`: Données du bot

### Logs

Les logs sont stockés dans le répertoire `logs/`:

- `bot.log`: Log principal du bot
- `gbpbot_api.log`: Log de l'API
- `gbpbot_dashboard.log`: Log du dashboard
- `monitor.log`: Log du moniteur de production
- `deployment.log`: Log du déploiement

---

## 9. Dépannage

### Problèmes courants

#### Le bot ne démarre pas

**Symptômes**: Erreur lors du démarrage du bot.

**Causes possibles**:
- Fichier `.env` mal configuré
- Dépendances manquantes
- Port déjà utilisé

**Solutions**:
1. Vérifiez le fichier `.env`
2. Exécutez `pip install -r requirements.txt`
3. Changez le port dans le fichier `.env`

#### Erreur de connexion Web3

**Symptômes**: Erreur "Could not connect to Web3 provider".

**Causes possibles**:
- URL du fournisseur Web3 incorrecte
- Clé API expirée ou invalide
- Problème de réseau

**Solutions**:
1. Vérifiez l'URL du fournisseur Web3 dans le fichier `.env`
2. Renouvelez votre clé API
3. Vérifiez votre connexion internet

#### Transactions échouées

**Symptômes**: Les transactions sont initiées mais échouent.

**Causes possibles**:
- Gas insuffisant
- Fonds insuffisants
- Slippage trop bas

**Solutions**:
1. Augmentez le `gas_boost_percentage`
2. Ajoutez des fonds à votre wallet
3. Augmentez le slippage maximum

#### Erreur d'authentification API

**Symptômes**: Erreur "Authentication required" lors de l'utilisation de l'API.

**Causes possibles**:
- Clé API incorrecte
- IP non autorisée

**Solutions**:
1. Vérifiez la clé API dans le fichier `.env`
2. Ajoutez votre IP à la liste blanche

### Fichiers de logs

En cas de problème, consultez les fichiers de logs:

```bash
tail -f logs/bot.log
```

### Support

Si vous ne parvenez pas à résoudre un problème, contactez le support:

- Email: support@gbpbot.com
- Telegram: @gbpbot_support

---

## 10. FAQ

### Questions générales

#### Q: Le bot est-il sûr à utiliser?
**R**: Oui, le bot est conçu avec la sécurité comme priorité. Cependant, le trading de crypto-monnaies comporte toujours des risques. Commencez avec de petites sommes et en mode simulation.

#### Q: Puis-je utiliser le bot sur plusieurs chaînes?
**R**: Oui, le bot prend en charge plusieurs chaînes, dont Ethereum, BSC, Polygon, etc. Configurez les fournisseurs Web3 appropriés dans le fichier `.env`.

#### Q: Combien de profit puis-je espérer?
**R**: Les profits dépendent de nombreux facteurs, dont les stratégies utilisées, les conditions du marché, et votre tolérance au risque. Commencez avec des attentes réalistes.

### Questions techniques

#### Q: Comment puis-je ajouter une nouvelle stratégie?
**R**: Créez un nouveau fichier dans `strategies/` et ajoutez-le à `config/strategies/`. Consultez la documentation technique pour plus de détails.

#### Q: Comment puis-je surveiller le bot à distance?
**R**: Configurez l'API pour accepter les connexions distantes et utilisez les alertes par email/Telegram.

#### Q: Le bot fonctionne-t-il 24/7?
**R**: Oui, le bot est conçu pour fonctionner en continu. Utilisez un service comme systemd pour le redémarrer automatiquement en cas de problème.

### Questions sur les stratégies

#### Q: Quelle stratégie est la plus rentable?
**R**: Cela dépend des conditions du marché. Le sniping de mempool est généralement plus rentable dans les marchés haussiers, tandis que l'arbitrage est plus stable dans tous les marchés.

#### Q: Comment éviter les honeypots?
**R**: Le bot inclut une détection de honeypot qui analyse le contrat du token avant d'acheter. Vous pouvez également ajouter des tokens connus pour être des arnaques à la liste noire.

#### Q: Comment optimiser les paramètres de gas?
**R**: Commencez avec les valeurs par défaut et ajustez-les en fonction de vos résultats. Un `gas_boost_percentage` plus élevé augmente les chances de succès mais aussi les coûts.

---

© 2023 GBPBot Team. Tous droits réservés. 