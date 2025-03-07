# Documentation de l'Intégration CEX pour GBPBot

## Introduction

Le module d'intégration CEX (Centralized Exchange) permet à GBPBot d'interagir avec les plateformes d'échange centralisées comme Binance, KuCoin et Gate.io. Cette intégration étend considérablement les capacités du bot en permettant le trading sur ces plateformes et l'arbitrage entre les CEX et les DEX (Decentralized Exchanges).

Cette documentation détaille l'architecture, l'utilisation et l'intégration des modules CEX avec le reste du GBPBot.

## Architecture

L'intégration CEX est basée sur une architecture modulaire avec les composants suivants :

1. **Interface commune (`BaseCEXClient`)** : Définit l'interface que tous les clients CEX doivent implémenter.
2. **Clients spécifiques** : Implémentations pour chaque plateforme d'échange (Binance, KuCoin, etc.).
3. **Factory (`CEXClientFactory`)** : Crée les instances de clients CEX appropriées.
4. **Module d'arbitrage CEX-DEX** : Exploite les opportunités d'arbitrage entre CEX et DEX.

### Diagramme d'architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  BinanceClient  │     │  KuCoinClient   │     │   GateClient    │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         └───────────┬───────────┴───────────┬───────────┘
                     │                       │
           ┌─────────▼─────────┐   ┌─────────▼─────────┐
           │   BaseCEXClient   │   │  CEXClientFactory │
           └─────────┬─────────┘   └─────────┬─────────┘
                     │                       │
                     └───────────┬───────────┘
                                 │
                     ┌───────────▼───────────┐
                     │   CEXDEXArbitrage     │
                     └───────────┬───────────┘
                                 │
                     ┌───────────▼───────────┐
                     │      GBPBot Core      │
                     └───────────────────────┘
```

## Fonctionnalités principales

- **Trading sur CEX** : Achat et vente de tokens sur les plateformes centralisées.
- **Récupération de données de marché** : Prix, carnets d'ordres, historique des trades.
- **Gestion des ordres** : Création, annulation et suivi des ordres.
- **Arbitrage CEX-DEX** : Détection et exploitation des opportunités d'arbitrage entre CEX et DEX.
- **Gestion des limites de rate** : Respect des limites d'API des plateformes.
- **Mise en cache** : Optimisation des performances via la mise en cache des données fréquemment utilisées.

## Installation des dépendances

L'intégration CEX nécessite les dépendances suivantes :

```bash
pip install aiohttp hmac hashlib
```

## Configuration

La configuration des CEX se fait via le fichier `config.yaml` dans le répertoire `config/` :

```yaml
# Configuration des plateformes d'échange centralisées (CEX)
exchanges:
  binance:
    enabled: true
    api_key: "votre_api_key"
    api_secret: "votre_api_secret"
    testnet: false
    rate_limits:
      requests_per_second: 10
      requests_per_minute: 1200
  kucoin:
    enabled: false
    api_key: ""
    api_secret: ""
    passphrase: ""
    testnet: false
  gate:
    enabled: false
    api_key: ""
    api_secret: ""
    testnet: false

# Configuration de l'arbitrage
arbitrage:
  cex_dex:
    enabled: true
    auto_execute: false
    min_profit_percentage: 0.5
    max_trade_amount: 100.0
    check_interval: 5
    cex:
      - "binance"
    dex:
      - "solana"
      - "avalanche"
    pairs:
      - "BTC/USDT"
      - "ETH/USDT"
      - "SOL/USDT"
    token_addresses:
      solana:
        BTC: "9n4nbM75f5Ui33ZbPYXn59EwSgE8CGsHtAeTH5YFeJ9E"
        ETH: "2FPyTwcZLUg1MDrwsyoP4D6s1tM7hAkHYRjkNb5w6Pxk"
        SOL: "So11111111111111111111111111111111111111112"
        USDT: "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"
```

## Utilisation des clients CEX

### Création d'un client

```python
from gbpbot.clients.cex.cex_client_factory import CEXClientFactory

# Création d'un client Binance
binance_client = CEXClientFactory.create_client("binance")

# Création d'un client avec des paramètres spécifiques
binance_client = CEXClientFactory.create_client(
    exchange="binance",
    api_key="votre_api_key",
    api_secret="votre_api_secret",
    testnet=True
)
```

### Récupération des prix

```python
# Récupérer le ticker pour une paire
ticker = await binance_client.get_ticker("BTC/USDT")
print(f"Prix actuel: {ticker['last']}")
print(f"Meilleur bid: {ticker['bid']}")
print(f"Meilleur ask: {ticker['ask']}")

# Récupérer uniquement le prix
price = await binance_client.get_price("BTC/USDT")
print(f"Prix: {price}")
```

### Récupération du carnet d'ordres

```python
# Récupérer le carnet d'ordres
orderbook = await binance_client.get_orderbook("BTC/USDT", limit=20)
print(f"Bids: {orderbook['bids']}")
print(f"Asks: {orderbook['asks']}")
```

### Récupération des soldes

```python
# Récupérer tous les soldes
balances = await binance_client.get_balance()
print(f"Soldes: {balances}")

# Récupérer le solde d'une devise spécifique
btc_balance = await binance_client.get_balance("BTC")
print(f"Solde BTC: {btc_balance}")
```

### Création d'un ordre

```python
# Créer un ordre limit
order = await binance_client.create_order(
    symbol="BTC/USDT",
    order_type="limit",
    side="buy",
    amount=0.001,
    price=50000.0
)
print(f"Ordre créé: {order}")

# Créer un ordre market
order = await binance_client.create_order(
    symbol="BTC/USDT",
    order_type="market",
    side="sell",
    amount=0.001
)
print(f"Ordre créé: {order}")
```

### Annulation d'un ordre

```python
# Annuler un ordre
result = await binance_client.cancel_order(
    order_id="123456789",
    symbol="BTC/USDT"
)
print(f"Ordre annulé: {result}")
```

### Récupération des ordres ouverts

```python
# Récupérer tous les ordres ouverts
orders = await binance_client.get_open_orders()
print(f"Ordres ouverts: {orders}")

# Récupérer les ordres ouverts pour une paire spécifique
orders = await binance_client.get_open_orders("BTC/USDT")
print(f"Ordres ouverts pour BTC/USDT: {orders}")
```

## Utilisation du module d'arbitrage CEX-DEX

### Initialisation et démarrage

```python
from gbpbot.modules.cex_dex_arbitrage import CEXDEXArbitrage

# Créer une instance du module d'arbitrage
arbitrage = CEXDEXArbitrage()

# Démarrer le module
await arbitrage.start()

# Arrêter le module
await arbitrage.stop()

# Récupérer les statistiques
stats = arbitrage.get_stats()
print(f"Opportunités détectées: {stats['opportunities_detected']}")
print(f"Trades exécutés: {stats['trades_executed']}")
print(f"Profit total: {stats['total_profit']}")
```

## Stratégies d'arbitrage

Le module d'arbitrage CEX-DEX implémente deux stratégies principales :

1. **CEX vers DEX** : Achat sur CEX et vente sur DEX lorsque le prix sur DEX est supérieur.
2. **DEX vers CEX** : Achat sur DEX et vente sur CEX lorsque le prix sur CEX est supérieur.

Le module calcule automatiquement le profit potentiel et exécute l'arbitrage si le profit est supérieur au seuil configuré.

### Exemple de détection d'opportunité

```json
{
  "pair": "BTC/USDT",
  "type": "cex_to_dex",
  "buy": {
    "platform": "binance",
    "price": 50000.0
  },
  "sell": {
    "platform": "solana",
    "price": 50500.0
  },
  "profit_percentage": 1.0,
  "timestamp": "2023-06-01T12:00:00.000Z"
}
```

## Sécurité et bonnes pratiques

1. **Clés API** : Stockez vos clés API de manière sécurisée, idéalement dans des variables d'environnement.
2. **Permissions** : Limitez les permissions des clés API au strict nécessaire (lecture, trading).
3. **Testnet** : Testez d'abord sur les réseaux de test avant de passer en production.
4. **Limites** : Respectez les limites de rate des plateformes pour éviter d'être banni.
5. **Monitoring** : Surveillez les performances et les erreurs pour détecter les problèmes rapidement.

## Limitations connues

1. Les clients CEX dépendent de la disponibilité des API des plateformes.
2. Les opportunités d'arbitrage peuvent disparaître rapidement en raison de la latence.
3. Les frais de transaction peuvent réduire ou éliminer les profits d'arbitrage.
4. Les limites de rate peuvent ralentir l'exécution des stratégies.

## Dépannage

### Problèmes courants

1. **Erreur d'authentification** : Vérifiez vos clés API et leurs permissions.
2. **Limite de rate atteinte** : Réduisez la fréquence des requêtes ou augmentez les délais.
3. **Ordre non exécuté** : Vérifiez les conditions du marché et les paramètres de l'ordre.
4. **Erreur de connexion** : Vérifiez votre connexion Internet et la disponibilité de l'API.

### Logs

Les logs sont essentiels pour le dépannage. Activez les logs détaillés en configurant le niveau de log :

```yaml
general:
  log_level: "DEBUG"
```

## Feuille de route

- **v1.0** : Support de base pour Binance avec arbitrage CEX-DEX
- **v1.1** : Ajout du support pour KuCoin et Gate.io
- **v1.2** : Optimisations des stratégies d'arbitrage
- **v1.3** : Support pour les futures et autres produits dérivés
- **v1.4** : Intégration avec l'IA pour l'analyse des opportunités

---

Pour toute question ou assistance, veuillez contacter l'équipe GBPBot ou ouvrir une issue sur GitHub. 