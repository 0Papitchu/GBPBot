# Module de Sniping de Memecoins Solana pour GBPBot

Ce module fournit une fonctionnalité spécialisée et optimisée pour le sniping ultra-rapide de nouveaux memecoins sur la blockchain Solana. Il est conçu pour détecter, analyser et trader automatiquement les nouveaux tokens avec une vitesse d'exécution maximale et une sécurité intégrée.

## Fonctionnalités principales

- **Détection ultra-rapide** : Surveillance du mempool Solana pour repérer les nouveaux tokens dès leur création
- **Analyse automatique** : Vérification de la liquidité, distribution des tokens et autres indicateurs de sécurité
- **Stop-loss intelligent** : Protection contre les pertes avec stop-loss et trailing stop automatiques
- **Take-profit adaptatif** : Maximisation des gains avec des stratégies de prise de profit adaptatives
- **Anti-Honeypot** : Détection des tokens malveillants et protection contre les arnaques
- **Statistiques en temps réel** : Suivi détaillé des performances de trading

## Prérequis

Pour utiliser ce module, vous devez installer les dépendances Solana suivantes :

```bash
pip install solana-py solders anchorpy base58
```

## Configuration

Le module utilise les variables d'environnement suivantes (configurables dans le fichier `.env`) :

```
# Solana RPC
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
SOLANA_WEBSOCKET_URL=wss://api.mainnet-beta.solana.com
SOLANA_PREFLIGHT_COMMITMENT=processed

# Wallet
MAIN_PRIVATE_KEY=VOTRE_CLE_PRIVEE_ICI

# Sniping
SOLANA_AUTO_SNIPE=true
SOLANA_MAX_SNIPE_AMOUNT_USD=100
DEFAULT_TAKE_PROFIT=20.0
DEFAULT_STOP_LOSS=10.0
TRAILING_TAKE_PROFIT=true
TRAILING_PERCENT=5.0
CHECK_HONEYPOT=true
MIN_LIQUIDITY_USD=10000
```

## Utilisation

### Via le menu GBPBot

Le module est intégré au menu principal de GBPBot. Vous pouvez l'activer en choisissant l'option "Sniping de Memecoins Solana (Spécialisé)" dans le menu des modules.

### En mode autonome

Vous pouvez également exécuter le module de manière autonome :

```python
from gbpbot.sniping import SolanaSnipingIntegration

# Créer une instance du sniper
sniper = SolanaSnipingIntegration()

# Démarrer le sniper
await sniper.start()

# Récupérer les statistiques
stats = sniper.get_performance_stats()
print(stats)

# Arrêter le sniper
await sniper.stop()
```

## Fonctionnement détaillé

1. **Détection** : Le module surveille en permanence le mempool Solana pour détecter les nouveaux tokens et les ajouts de liquidité.

2. **Analyse** : Chaque nouveau token détecté est rapidement analysé pour évaluer :
   - Sa liquidité initiale
   - La distribution des tokens (pour éviter les rug pulls)
   - Les potentiels honeypots
   - Les caractéristiques du contrat du token

3. **Décision** : Sur la base de l'analyse, le module décide s'il faut sniper le token selon les critères configurés.

4. **Exécution** : Si la décision est positive, le module exécute un achat ultra-rapide pour maximiser les profits potentiels.

5. **Gestion** : Après l'achat, le module surveille en permanence le prix et applique les stratégies de prise de profit et de stop-loss.

## Sécurité

Le module intègre plusieurs mécanismes de sécurité :

- **Vérification des honeypots** : Simulation de la vente du token avant achat
- **Limites d'achat** : Montant maximum par transaction pour limiter l'exposition
- **Stop-loss automatique** : Protection contre les baisses de prix importantes
- **Anti-rug** : Vérification de la distribution des tokens et de l'âge du token
- **Blacklist** : Support pour une liste noire de tokens à éviter

## Optimisations

Pour de meilleures performances, vous pouvez:

1. Utiliser un RPC Solana rapide et fiable (idéalement un nœud privé)
2. Configurer correctement les seuils de prise de profit et de stop-loss
3. Ajuster le montant max par snipe selon votre stratégie de risque
4. Utiliser un endpoint RPC Solana avec support du websocket pour une détection plus rapide

## Support

En cas de problème ou pour des questions sur ce module, veuillez consulter la documentation complète du GBPBot ou contacter l'équipe de support. 