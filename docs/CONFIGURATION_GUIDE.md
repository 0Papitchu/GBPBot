# Guide de Configuration Complet du GBPBot

> **Note de mise à jour**: Ce guide de configuration a été créé le 10/03/2024 et regroupe toutes les informations de configuration du système GBPBot en un document unique et complet.

## Table des matières

1. [Introduction](#1-introduction)
2. [Configuration Générale](#2-configuration-générale)
   - [2.1 Fichier .env](#21-fichier-env)
   - [2.2 Gestion des Environnements](#22-gestion-des-environnements)
3. [Configuration des Blockchains](#3-configuration-des-blockchains)
   - [3.1 Solana](#31-solana)
   - [3.2 Avalanche](#32-avalanche)
   - [3.3 Sonic/Fantom](#33-sonicfantom)
4. [Configuration des Wallets](#4-configuration-des-wallets)
   - [4.1 Création et Import](#41-création-et-import)
   - [4.2 Gestion Multi-wallets](#42-gestion-multi-wallets)
   - [4.3 Sécurité des Wallets](#43-sécurité-des-wallets)
5. [Configuration des Modules](#5-configuration-des-modules)
   - [5.1 Module de Sniping](#51-module-de-sniping)
   - [5.2 Module d'Arbitrage](#52-module-darbitrage)
   - [5.3 Module AI](#53-module-ai)
   - [5.4 Module de Monitoring](#54-module-de-monitoring)
6. [Configuration des Stratégies](#6-configuration-des-stratégies)
   - [6.1 Stratégies de Sniping](#61-stratégies-de-sniping)
   - [6.2 Stratégies d'Arbitrage](#62-stratégies-darbitrage)
   - [6.3 Paramètres de Take Profit et Stop Loss](#63-paramètres-de-take-profit-et-stop-loss)
7. [Configuration de l'Interface Utilisateur](#7-configuration-de-linterface-utilisateur)
   - [7.1 Interface CLI](#71-interface-cli)
   - [7.2 Interface Telegram](#72-interface-telegram)
8. [Configuration de la Sécurité](#8-configuration-de-la-sécurité)
   - [8.1 Protection des Fonds](#81-protection-des-fonds)
   - [8.2 Détection des Scams](#82-détection-des-scams)
   - [8.3 Limites de Trading](#83-limites-de-trading)
9. [Configuration des Performances](#9-configuration-des-performances)
   - [9.1 Optimisation du Gas](#91-optimisation-du-gas)
   - [9.2 Optimisation des Connexions RPC](#92-optimisation-des-connexions-rpc)
10. [Dépannage de la Configuration](#10-dépannage-de-la-configuration)

---

## 1. Introduction

Ce guide de configuration est conçu pour vous aider à configurer correctement le GBPBot afin d'optimiser vos performances de trading. Une configuration appropriée est essentielle pour garantir la sécurité de vos fonds, l'efficacité de vos stratégies et la réactivité du bot face aux opportunités de marché.

### Philosophie de configuration

La configuration du GBPBot repose sur trois principes fondamentaux :

1. **Sécurité** : Protection de vos fonds et de vos informations personnelles
2. **Performance** : Optimisation du bot pour une exécution rapide et fiable
3. **Adaptabilité** : Ajustement facile des paramètres en fonction de l'évolution du marché

### Structure des fichiers de configuration

Les fichiers de configuration du GBPBot sont organisés comme suit :

```
GBPBot/
├── .env                     # Variables d'environnement principales
├── .env.example             # Exemple de fichier .env
├── config/                  # Dossier de configuration
│   ├── strategies/          # Configuration des stratégies
│   │   ├── sniping.json     # Stratégie de sniping
│   │   └── arbitrage.json   # Stratégie d'arbitrage
│   ├── security.json        # Configuration de sécurité
│   ├── ui.json              # Configuration de l'interface
│   └── blockchain.json      # Configuration des blockchains
├── wallets/                 # Stockage sécurisé des wallets
└── logs/                    # Journaux et historiques
```

---

## 2. Configuration Générale

### 2.1 Fichier .env

Le fichier `.env` contient les variables d'environnement essentielles pour le fonctionnement du GBPBot. C'est le point de départ de toute configuration.

#### Variables essentielles

```ini
# CONFIGURATION GÉNÉRALE
BOT_MODE=manual                     # manual, auto, telegram
DEFAULT_BLOCKCHAIN=solana           # avalanche, solana, sonic
DEBUG_MODE=false                    # active les logs détaillés
ENVIRONMENT=development             # development, production
LOG_LEVEL=INFO                      # DEBUG, INFO, WARNING, ERROR

# CONNEXION BLOCKCHAIN
AVALANCHE_RPC_URL=https://api.avax.network/ext/bc/C/rpc
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
SONIC_RPC_URL=https://rpc.sonic.fantom.network/

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

#### Configuration du mode de fonctionnement

Le paramètre `BOT_MODE` détermine comment le bot sera contrôlé :

- `manual` : Contrôle manuel via l'interface CLI
- `auto` : Fonctionnement automatique avec les paramètres configurés
- `telegram` : Contrôle à distance via Telegram

#### Configuration de l'environnement

Le paramètre `ENVIRONMENT` définit le contexte d'exécution :

- `development` : Pour les tests et le développement
- `production` : Pour l'exécution en environnement réel avec des fonds réels

### 2.2 Gestion des Environnements

GBPBot supporte plusieurs fichiers d'environnement pour différents contextes :

- `.env` : Configuration principale utilisée par le bot
- `.env.local` : Configuration locale avec vos données sensibles (non commité dans Git)
- `.env.example` : Modèle de configuration sans données sensibles
- `.env.backup_*` : Sauvegardes automatiques de votre configuration
- `.env.optimized` : Configuration avec paramètres de performance optimisés

#### Outils de gestion

Pour faciliter la gestion des fichiers d'environnement, utilisez :

- **Windows** : `configure_env.bat` à la racine du projet
- **Linux/Mac** : `python scripts/setup_env.py [commande]`

Ces outils vous permettent de :
- Créer des sauvegardes de votre `.env`
- Initialiser `.env` à partir de `.env.local`
- Valider vos configurations

#### Bonnes pratiques

1. Ne stockez jamais de clés privées ou d'API directement dans le code
2. Utilisez `.env.local` pour les informations sensibles et ne le partagez jamais
3. Créez des sauvegardes régulières de vos fichiers de configuration
4. Vérifiez vos configurations avec l'utilitaire avant de démarrer le bot

---

## 3. Configuration des Blockchains

GBPBot prend en charge plusieurs blockchains, chacune nécessitant une configuration spécifique.

### 3.1 Solana

#### Configuration RPC

Solana nécessite un endpoint RPC fiable et rapide. Vous pouvez utiliser :

```ini
# Dans .env
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
SOLANA_WS_URL=wss://api.mainnet-beta.solana.com
SOLANA_COMMITMENT=confirmed
```

Options de commitment :
- `processed` : Plus rapide mais moins fiable
- `confirmed` : Bon équilibre entre vitesse et fiabilité (recommandé)
- `finalized` : Plus lent mais garantit la finalité

#### Configuration avancée

Pour des performances optimales sur Solana, ajoutez :

```ini
SOLANA_PRIORITIZATION_FEE=true
SOLANA_MAX_PRIORITY_FEE=0.000005
SOLANA_RETRY_STRATEGY=exponential
```

#### RPC recommandés pour Solana

| Fournisseur | URL | Avantages | Usage |
|-------------|-----|-----------|-------|
| Solana RPC | https://api.mainnet-beta.solana.com | Gratuit, officiel | Test |
| QuickNode | https://your-endpoint.quiknode.pro | Rapide, fiable | Production |
| Alchemy | https://solana-mainnet.g.alchemy.com | Analytics, fiable | Production |
| Jito | https://jito-rpc.memes.com | MEV, rapide | Avancé |

### 3.2 Avalanche

#### Configuration RPC

```ini
# Dans .env
AVALANCHE_RPC_URL=https://api.avax.network/ext/bc/C/rpc
AVALANCHE_WS_URL=wss://api.avax.network/ext/bc/C/ws
AVALANCHE_CHAIN_ID=43114
```

#### Configuration avancée

```ini
AVALANCHE_MAX_GAS_PRICE=225
AVALANCHE_PRIORITY_FEE=2
AVALANCHE_CONFIRMATION_BLOCKS=3
```

#### RPC recommandés pour Avalanche

| Fournisseur | URL | Avantages | Usage |
|-------------|-----|-----------|-------|
| Avalanche | https://api.avax.network/ext/bc/C/rpc | Gratuit, officiel | Test |
| QuickNode | https://avax-mainnet.quicknode.com | Rapide, fiable | Production |
| Ankr | https://rpc.ankr.com/avalanche | Gratuit, stable | Test |
| Blast | https://ava-mainnet.public.blastapi.io | Stable | Production |

### 3.3 Sonic/Fantom

#### Configuration de base

```ini
# Dans .env
SONIC_RPC_URL=https://rpc.sonic.fantom.network/
SONIC_WS_URL=wss://sonic.fantom.network/
SONIC_CHAIN_ID=250
```

#### Configuration avancée

```ini
SONIC_MAX_GAS_PRICE=5000
SONIC_GAS_MULTIPLIER=1.2
SONIC_BLOCK_CONFIRMATION=5
```

Pour plus de détails sur la configuration de Sonic, consultez le [Guide Sonic](SONIC_GUIDE.md).

---

## 4. Configuration des Wallets

### 4.1 Création et Import

Vous pouvez configurer vos wallets de plusieurs façons :

#### Via le fichier .env (méthode simple)

```ini
# Dans .env
PRIVATE_KEY=your_private_key_here
WALLET_ADDRESS=your_address_here
```

#### Via le WalletManager (recommandé)

Le `WalletManager` offre une interface sécurisée pour gérer vos wallets :

```python
from gbpbot.modules.wallet_manager import WalletManager

# Initialiser le gestionnaire
wallet_manager = WalletManager()

# Importer un wallet existant
wallet_manager.import_wallet("solana", "your_private_key", "wallet_name")

# Créer un nouveau wallet
new_wallet = wallet_manager.create_wallet("avalanche", "new_wallet")
print(f"Nouvelle adresse: {new_wallet.address}")
print(f"Nouvelle clé privée: {new_wallet.private_key}")
```

### 4.2 Gestion Multi-wallets

GBPBot permet d'utiliser plusieurs wallets pour différentes blockchains ou stratégies :

```ini
# Dans .env
SOLANA_PRIVATE_KEY=your_solana_private_key
AVALANCHE_PRIVATE_KEY=your_avalanche_private_key
SONIC_PRIVATE_KEY=your_sonic_private_key

# Ou avec préfixes pour stratégies
SNIPING_WALLET_KEY=your_sniping_wallet_key
ARBITRAGE_WALLET_KEY=your_arbitrage_wallet_key
```

Pour plus de détails sur la gestion des wallets, consultez le [Guide de Monitoring](MONITORING_GUIDE.md).

### 4.3 Sécurité des Wallets

#### Chiffrement des clés

GBPBot peut chiffrer vos clés privées pour plus de sécurité :

```ini
# Dans .env
ENCRYPT_KEYS=true
ENCRYPTION_PASSWORD=your_strong_password
```

#### Bonnes pratiques

1. Utilisez des wallets dédiés pour le bot, pas vos wallets principaux
2. Limitez les fonds sur ces wallets au montant nécessaire pour les opérations
3. Activez l'option de chiffrement des clés privées
4. Évitez de stocker les clés privées en texte clair
5. Créez des sauvegardes sécurisées de vos clés privées

---

## 5. Configuration des Modules

### 5.1 Module de Sniping

Le module de sniping est configuré dans `config/strategies/sniping.json` :

```json
{
  "enabled": true,
  "blockchain": "solana",
  "parameters": {
    "min_liquidity_usd": 10000,
    "max_buy_amount_usd": 100,
    "max_tax_percent": 5,
    "slippage_percent": 2.5,
    "gas_priority": "high",
    "auto_sell": true,
    "take_profit_percent": 50,
    "stop_loss_percent": 20,
    "trailing_stop_percent": 10
  },
  "filters": {
    "check_honeypot": true,
    "check_dev_wallet": true,
    "max_dev_wallet_percent": 20,
    "min_holder_count": 10
  },
  "ai_analysis": {
    "enabled": true,
    "min_score": 70,
    "analyze_contract": true
  }
}
```

### 5.2 Module d'Arbitrage

Le module d'arbitrage est configuré dans `config/strategies/arbitrage.json` :

```json
{
  "enabled": true,
  "blockchains": ["solana", "avalanche"],
  "parameters": {
    "min_profit_percent": 0.8,
    "max_slippage_percent": 0.5,
    "gas_priority": "medium",
    "max_concurrent_trades": 3,
    "min_volume_usd": 50000
  },
  "dexes": {
    "solana": ["raydium", "orca"],
    "avalanche": ["traderjoe", "pangolin"],
    "sonic": ["spiritswap", "spookyswap"]
  },
  "token_pairs": [
    {"base": "SOL", "quote": "USDC"},
    {"base": "AVAX", "quote": "USDT"},
    {"base": "ETH", "quote": "USDC"}
  ]
}
```

### 5.3 Module AI

La configuration de l'IA se fait via `config/ai.json` :

```json
{
  "enabled": true,
  "provider": "auto",
  "openai": {
    "api_key": "sk-votre-clé-api",
    "model": "gpt-4-turbo"
  },
  "claude": {
    "api_key": "sk-ant-votre-clé-api",
    "model": "claude-3-opus-20240229"
  },
  "llama": {
    "model_path": "/chemin/vers/modele/llama",
    "context_size": 4096
  },
  "analysis": {
    "token_analysis": true,
    "contract_analysis": true,
    "market_analysis": true
  },
  "performance": {
    "cache_results": true,
    "cache_duration_minutes": 30,
    "max_tokens": 4000
  }
}
```

Pour plus de détails sur la configuration de l'IA, consultez le [Guide IA](AI_README.md).

### 5.4 Module de Monitoring

Le monitoring est configuré dans `config/monitoring.json` :

```json
{
  "system_monitor": {
    "enabled": true,
    "check_interval_seconds": 60,
    "memory_threshold_percent": 90,
    "cpu_threshold_percent": 95,
    "disk_threshold_percent": 90,
    "auto_restart": true
  },
  "performance_monitor": {
    "enabled": true,
    "track_trades": true,
    "track_gas_usage": true,
    "profit_loss_tracking": true,
    "report_interval_hours": 24
  },
  "alerts": {
    "telegram_alerts": true,
    "email_alerts": false,
    "log_alerts": true,
    "alert_levels": ["ERROR", "WARNING"]
  }
}
```

Pour plus de détails sur le monitoring, consultez le [Guide de Monitoring](MONITORING_GUIDE.md).

---

## 6. Configuration des Stratégies

### 6.1 Stratégies de Sniping

Les paramètres clés pour optimiser vos stratégies de sniping sont :

#### Memecoin Sniping

```json
{
  "memecoin_sniping": {
    "target_blockchains": ["solana", "sonic"],
    "min_liquidity_usd": 10000,
    "max_buy_amount_usd": 50,
    "ai_min_score": 75,
    "min_holders": 15,
    "max_dev_wallet_percent": 15,
    "community_signals": true,
    "check_telegram_members": true,
    "min_telegram_members": 500
  }
}
```

#### Sniping Avancé

Pour les utilisateurs avancés, des paramètres supplémentaires sont disponibles :

```json
{
  "advanced_sniping": {
    "use_sandwich_detection": true,
    "mempool_monitoring": true,
    "monitor_whale_wallets": true,
    "priority_fee_multiplier": 1.5,
    "max_wait_blocks": 3,
    "retry_failed_transactions": true,
    "retry_max_attempts": 3
  }
}
```

### 6.2 Stratégies d'Arbitrage

#### Paramètres d'arbitrage standard

```json
{
  "standard_arbitrage": {
    "min_profit_threshold_percent": 0.7,
    "gas_consideration": true,
    "routing_optimization": true,
    "flash_swap_enabled": true,
    "max_route_hops": 3,
    "dex_priority": ["raydium", "orca", "jupiter"]
  }
}
```

#### Arbitrage cross-chain

```json
{
  "cross_chain_arbitrage": {
    "enabled": false,
    "chains": ["solana", "avalanche"],
    "bridges": ["wormhole", "allbridge"],
    "min_profit_after_fees_percent": 2.0,
    "max_bridge_time_seconds": 300
  }
}
```

### 6.3 Paramètres de Take Profit et Stop Loss

#### Configuration basique

```json
{
  "exit_strategy": {
    "take_profit_percent": 30,
    "stop_loss_percent": 15,
    "trailing_stop_enabled": true,
    "trailing_stop_percent": 10,
    "time_based_exit_minutes": 60
  }
}
```

#### Configuration avancée

```json
{
  "advanced_exit_strategy": {
    "dynamic_take_profit": true,
    "dynamic_tp_factor": 0.5,
    "profit_distribution": [
      {"percent": 25, "at_profit": 15},
      {"percent": 50, "at_profit": 30},
      {"percent": 25, "at_profit": 50}
    ],
    "volume_based_exit": true,
    "exit_on_volume_decrease_percent": 50
  }
}
```

---

## 7. Configuration de l'Interface Utilisateur

### 7.1 Interface CLI

L'interface en ligne de commande est configurée dans `config/ui.json` :

```json
{
  "cli": {
    "enable_color": true,
    "log_to_file": true,
    "log_file_path": "logs/cli.log",
    "display_levels": ["INFO", "WARNING", "ERROR"],
    "refresh_rate_seconds": 5,
    "show_balance": true,
    "show_profit_loss": true,
    "compact_mode": false
  }
}
```

### 7.2 Interface Telegram

La configuration Telegram se fait via le fichier `.env` et `config/telegram.json` :

```ini
# Dans .env
TELEGRAM_BOT_TOKEN=your_token_here
TELEGRAM_CHAT_ID=your_chat_id
TELEGRAM_AUTHORIZED_USERS=user_id_1,user_id_2
```

```json
{
  "telegram": {
    "notifications": {
      "startup": true,
      "shutdown": true,
      "trades": true,
      "errors": true,
      "profits": true,
      "system_alerts": true
    },
    "commands": {
      "enable_all": false,
      "allowed_commands": [
        "status", "balance", "start", "stop", 
        "buy", "sell", "profit", "help"
      ]
    },
    "security": {
      "restrict_to_authorized": true,
      "command_throttling": true,
      "max_commands_per_minute": 10
    },
    "formatting": {
      "use_markdown": true,
      "include_timestamps": true,
      "include_emojis": true
    }
  }
}
```

---

## 8. Configuration de la Sécurité

### 8.1 Protection des Fonds

```json
{
  "fund_protection": {
    "max_wallet_exposure_percent": 20,
    "max_single_trade_usd": 100,
    "daily_trading_limit_usd": 1000,
    "require_confirmation_above_usd": 50,
    "emergency_withdraw_enabled": true,
    "auto_withdraw_profits": true,
    "profit_withdraw_threshold_usd": 500,
    "safe_wallet_address": "your_safe_wallet_address"
  }
}
```

### 8.2 Détection des Scams

```json
{
  "scam_detection": {
    "enabled": true,
    "check_contract_code": true,
    "check_token_liquidity": true,
    "min_liquidity_locked_percent": 80,
    "min_liquidity_lock_days": 30,
    "check_ownership_renounced": true,
    "check_hidden_mints": true,
    "blacklisted_functions": [
      "setTaxFeePercent", "setMaxTxPercent", "updateFees"
    ],
    "ai_contract_analysis": true
  }
}
```

### 8.3 Limites de Trading

```json
{
  "trading_limits": {
    "max_concurrent_trades": 5,
    "max_daily_trades": 20,
    "max_daily_volume_usd": 2000,
    "cooldown_between_trades_seconds": 60,
    "max_slippage_percent": 3,
    "require_manual_approval_above_usd": 200
  }
}
```

---

## 9. Configuration des Performances

### 9.1 Optimisation du Gas

```json
{
  "gas_optimization": {
    "strategy": "adaptive",
    "base_multiplier": 1.2,
    "priority_multiplier": 1.5,
    "max_gas_price": {
      "solana": 0.000005,
      "avalanche": 225,
      "sonic": 5000
    },
    "retry_on_failure": true,
    "max_retries": 3,
    "backoff_factor": 1.5
  }
}
```

### 9.2 Optimisation des Connexions RPC

```json
{
  "rpc_optimization": {
    "connection_pooling": true,
    "max_connections": 10,
    "timeout_seconds": 10,
    "retry_count": 3,
    "failover_enabled": true,
    "backup_rpcs": {
      "solana": [
        "https://solana-api.projectserum.com",
        "https://rpc.ankr.com/solana"
      ],
      "avalanche": [
        "https://rpc.ankr.com/avalanche",
        "https://avax-mainnet.gateway.pokt.network/v1/lb/YOUR_API_KEY"
      ]
    },
    "health_check_interval_seconds": 30
  }
}
```

---

## 10. Dépannage de la Configuration

### Problèmes courants et solutions

| Problème | Cause possible | Solution |
|----------|----------------|----------|
| `Connection refused` | URL RPC incorrecte | Vérifiez et corrigez l'URL RPC dans `.env` |
| `Invalid private key` | Format de clé incorrect | Assurez-vous que la clé est au bon format (hex pour ETH, base58 pour Solana) |
| `Insufficient funds` | Fonds insuffisants | Approvisionnez votre wallet ou réduisez `max_buy_amount` |
| `Transaction failed` | Gas trop bas | Augmentez les paramètres de gas dans la configuration |
| `API rate limit exceeded` | Trop de requêtes RPC | Utilisez un RPC premium ou ajustez `check_interval` |

### Validation de la configuration

Utilisez les outils de validation intégrés pour vérifier votre configuration :

```bash
# Vérifier la configuration
python scripts/validate_config.py

# Tester la connexion RPC
python scripts/test_rpc_connection.py

# Vérifier les wallets
python scripts/check_wallets.py
```

### Logs et diagnostics

En cas de problème, consultez les logs :

```
logs/gbpbot.log       # Log principal
logs/transactions.log # Log des transactions
logs/errors.log       # Log des erreurs
```

Pour un diagnostic approfondi, activez le mode DEBUG :

```ini
# Dans .env
DEBUG_MODE=true
LOG_LEVEL=DEBUG
```

---

Pour plus d'informations sur d'autres aspects de la configuration, consultez les guides spécifiques :

- [Guide IA](AI_README.md) - Configuration détaillée de l'intelligence artificielle
- [Guide Sonic](SONIC_GUIDE.md) - Configuration pour la blockchain Sonic/Fantom
- [Guide de Monitoring](MONITORING_GUIDE.md) - Configuration du monitoring et des alertes
- [Documentation Technique](../gbpbot/TECHNICAL_DOCUMENTATION.md) - Référence technique complète

N'hésitez pas à consulter [TROUBLESHOOTING.md](TROUBLESHOOTING.md) pour des solutions aux problèmes courants de configuration. 