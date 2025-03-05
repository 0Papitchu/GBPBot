# GBPBot - Advanced Arbitrage Trading Bot

GBPBot est un bot d'arbitrage avancé conçu pour détecter et exécuter des opportunités d'arbitrage sur la blockchain Avalanche (AVAX) et d'autres blockchains.

## Caractéristiques

- **Multi-blockchain** : Support pour Avalanche (AVAX) avec possibilité d'extension à d'autres blockchains
- **Détection d'arbitrage** : Identification des opportunités d'arbitrage entre différents DEX
- **Exécution optimisée** : Transactions optimisées pour maximiser les profits
- **Protection MEV** : Mécanismes de protection contre le frontrunning et autres attaques MEV
- **Gestion des RPC** : Pool de connexions RPC avec sélection intelligente des fournisseurs
- **Cache de prix** : Système de cache LRU pour les prix des tokens
- **Monitoring** : Surveillance des performances et des opportunités d'arbitrage

## Architecture

GBPBot est construit avec une architecture modulaire qui permet une grande flexibilité et extensibilité :

```
gbpbot/
├── core/
│   ├── blockchain_factory.py    # Clients blockchain et factory
│   ├── exceptions.py            # Exceptions personnalisées
│   ├── mev_monitor.py           # Surveillance et protection MEV
│   └── ...
├── strategies/
│   ├── arbitrage_strategy.py    # Stratégies d'arbitrage
│   └── ...
├── utils/
│   ├── config.py                # Gestion de la configuration
│   ├── logger.py                # Configuration des logs
│   └── ...
└── main.py                      # Point d'entrée principal
```

## Installation

### Prérequis

- Python 3.8+
- pip

### Installation des dépendances

```bash
pip install -r requirements.txt
```

## Configuration

Créez un fichier de configuration `config.yaml` à la racine du projet :

```yaml
# Configuration générale
general:
  log_level: INFO
  debug_mode: false

# Configuration Avalanche
avalanche:
  chain_id: 43114
  native_token_address: "0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7"  # WAVAX
  rpc_providers:
    - url: "https://api.avax.network/ext/bc/C/rpc"
      weight: 10
    - url: "https://rpc.ankr.com/avalanche"
      weight: 8
    - url: "https://avalanche-c-chain.publicnode.com"
      weight: 5
  dex_routers:
    traderjoe: "0x60aE616a2155Ee3d9A68541Ba4544862310933d4"
    pangolin: "0xE54Ca86531e17Ef3616d22Ca28b0D458b6C89106"
    sushiswap: "0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506"

# Configuration des tokens
tokens:
  base_tokens:
    - symbol: "WAVAX"
      address: "0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7"
    - symbol: "USDC"
      address: "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E"
  target_tokens:
    - symbol: "JOE"
      address: "0x6e84a6216eA6dACC71eE8E6b0a5B7322EEbC0fDd"
    - symbol: "PNG"
      address: "0x60781C2586D68229fde47564546784ab3fACA982"
    - symbol: "LINK"
      address: "0x5947BB275c521040051D82396192181b413227A3"

# Configuration de l'arbitrage
arbitrage:
  min_profit_percentage: 0.5
  max_slippage: 0.5
  gas_boost: 1.2
  deadline_minutes: 20
  mev_protection: true
```

## Utilisation

### Démarrage du bot

```bash
python main.py
```

### Commandes disponibles

- `python main.py --config=custom_config.yaml` : Utiliser un fichier de configuration personnalisé
- `python main.py --debug` : Activer le mode debug
- `python main.py --monitor-only` : Exécuter uniquement la surveillance sans exécuter d'arbitrages

## Sécurité

### Gestion des clés privées

Les clés privées doivent être stockées de manière sécurisée. Nous recommandons d'utiliser des variables d'environnement ou un gestionnaire de secrets comme HashiCorp Vault.

### Protection contre le MEV

GBPBot intègre plusieurs mécanismes pour se protéger contre les attaques MEV :

1. **Surveillance des transactions** : Détection des attaques sandwich et du frontrunning
2. **Optimisation du gas** : Ajustement dynamique du gas price pour éviter le frontrunning
3. **Mempools privés** : Support pour les mempools privés (comme Flashbots)

## Développement

### Ajout d'une nouvelle blockchain

Pour ajouter le support d'une nouvelle blockchain, créez une nouvelle classe qui hérite de `BaseBlockchainClient` et implémentez les méthodes abstraites.

### Ajout d'une nouvelle stratégie d'arbitrage

Pour ajouter une nouvelle stratégie d'arbitrage, créez une nouvelle classe dans le dossier `strategies/` qui implémente l'interface de stratégie.

## Licence

Ce projet est sous licence MIT. Voir le fichier LICENSE pour plus de détails.

## Avertissement

Le trading de crypto-monnaies comporte des risques importants. Ce bot est fourni à titre éducatif et expérimental. Utilisez-le à vos propres risques.

## Contribution

Les contributions sont les bienvenues ! N'hésitez pas à ouvrir une issue ou une pull request.