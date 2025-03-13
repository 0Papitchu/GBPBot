# Documentation du Client Sonic pour GBPBot

> **IMPORTANT** : Ce document est obsolète et a été remplacé par un guide unifié plus complet.
> 
> Veuillez consulter [SONIC_GUIDE.md](SONIC_GUIDE.md) pour la documentation à jour sur l'intégration Sonic.

---

## Redirection

Cette documentation a été consolidée avec `sonic_client_guide.md` et `SONIC_INTEGRATION.md` en un seul guide complet.

Le nouveau document unifié contient :
- Une architecture détaillée des composants Sonic
- Un guide complet de configuration et d'utilisation
- Des exemples pratiques de sniping et d'arbitrage
- Des conseils de dépannage et bonnes pratiques
- Des modèles de code pour l'intégration avec d'autres modules

**Merci de vous référer au nouveau guide : [SONIC_GUIDE.md](SONIC_GUIDE.md)**

## Introduction

Le module Client Sonic est une composante essentielle de l'expansion du GBPBot vers la blockchain Sonic (basée sur Fantom). Il fournit une interface simplifiée et optimisée pour interagir avec la blockchain Sonic, ses DEX, et ses tokens.

Cette documentation détaille l'utilisation du client, ses fonctionnalités et son intégration avec les autres modules du GBPBot.

## Fonctionnalités principales

- **Connexion blockchain** : Interface avec les nœuds RPC Sonic (Fantom)
- **Gestion des transactions** : Création, signature et envoi de transactions
- **Interaction avec les DEX** : Support de SpiritSwap et SpookySwap
- **Monitoring de tokens** : Détection et analyse des nouveaux tokens
- **Évaluation de prix** : Récupération et analyse des prix de tokens
- **Gestion des pools** : Interrogation et analyse des pools de liquidité
- **Analyse des contrats** : Récupération et évaluation des contrats intelligents

## Installation des dépendances

Le client Sonic nécessite les dépendances suivantes :

```bash
pip install web3 aiohttp asyncio
```

## Configuration

La configuration du client Sonic se fait via le fichier `config.yaml` dans le répertoire `config/` :

```yaml
blockchains:
  sonic:
    enabled: true
    rpc_url: "https://rpc.sonic.fantom.network/"
    ws_url: "wss://sonic.fantom.network/"
    commitment: "confirmed"
    sniper:
      enabled: true
      max_buy_amount: 0.1
      min_liquidity: 10000
      max_tax_percentage: 5.0
      auto_sell: true
      take_profit_percentage: 50.0
      stop_loss_percentage: 10.0
    arbitrage:
      enabled: true
      min_profit_percentage: 0.7
      max_slippage: 0.5
      gas_priority: "medium"
      max_concurrent_trades: 2
      dexes:
        - "spiritswap"
        - "spookyswap"
```

## Utilisation du Client

### Initialisation

```python
from gbpbot.clients.blockchain_client_factory import BlockchainClientFactory

# Création du client Sonic
sonic_client = BlockchainClientFactory.create_client("sonic")

# Vérification de la connexion
is_connected = await sonic_client.test_connection()
print(f"Connexion établie: {is_connected}")
```

### Interrogation des prix

```python
# Récupérer le prix d'un token
token_address = "0x21be370D5312f44cB42ce377BC9b8a0cEF1A4C83"  # WFTM
price = await sonic_client.get_token_price(token_address)
print(f"Prix actuel: {price}")
```

### Récupération des informations d'un token

```python
# Récupérer les informations d'un token
token_info = await sonic_client.get_token_info(token_address)
print(f"Nom: {token_info['name']}")
print(f"Symbole: {token_info['symbol']}")
print(f"Décimales: {token_info['decimals']}")
```

### Swap de tokens

```python
# Effectuer un swap de tokens
from_token = "0x21be370D5312f44cB42ce377BC9b8a0cEF1A4C83"  # WFTM
to_token = "0x04068DA6C83AFCFA0e13ba15A6696662335D5B75"  # USDC
amount_in = 1000000000000000000  # 1 WFTM
min_amount_out = 1  # Valeur minimale acceptable

tx_hash = await sonic_client.swap_tokens(
    token_in=from_token,
    token_out=to_token,
    amount_in=amount_in,
    min_amount_out=min_amount_out,
    dex="spiritswap"
)
print(f"Transaction envoyée: {tx_hash}")
```

### Surveillance des nouveaux tokens

```python
# Définir le callback pour les nouveaux tokens
async def token_callback(token_data):
    print(f"Nouveau token détecté!")
    print(f"Adresse: {token_data['address']}")
    print(f"Nom: {token_data['name']}")
    print(f"Symbole: {token_data['symbol']}")

# Démarrer la surveillance
await sonic_client.monitor_new_tokens(token_callback)
```

## Intégration avec le Sniper

Le client Sonic est intégré au module `SonicSniper` qui utilise ses fonctionnalités pour détecter et acheter les tokens prometteurs :

```python
from gbpbot.modules.sonic_sniper import SonicSniper

# Créer le sniper
sniper = SonicSniper()

# Démarrer le sniping
await sniper.start()

# Arrêter le sniping
await sniper.stop()

# Obtenir les statistiques
stats = sniper.get_stats()
print(f"Tokens détectés: {stats['tokens_detected']}")
print(f"Tokens achetés: {stats['tokens_bought']}")
print(f"Profit total: {stats['total_profit']}")
```

## Architecture interne

Le client Sonic est basé sur l'architecture suivante :

1. **BaseBlockchainClient** : Classe de base pour tous les clients blockchain
2. **SonicClient** : Implémentation spécifique à Sonic de l'interface blockchain
3. **BlockchainClientFactory** : Factory pour créer des instances de clients

Le client utilise Web3.py pour interagir avec la blockchain Fantom et aiohttp pour les requêtes HTTP asynchrones.

## DEX supportés

- **SpiritSwap** : DEX principal sur Fantom, avec des frais de 0.3%
- **SpookySwap** : DEX alternatif sur Fantom, avec des frais de 0.2%

## Tokens importants

- WFTM (Wrapped FTM) : `0x21be370D5312f44cB42ce377BC9b8a0cEF1A4C83`
- USDC : `0x04068DA6C83AFCFA0e13ba15A6696662335D5B75`
- DAI : `0x8D11eC38a3EB5E956B052f67Da8Bdc9bef8Abf3E`

## Optimisations de performances

Le client Sonic inclut plusieurs optimisations pour une exécution à haute performance :

1. **Cache intégré** : Les données récentes sont mises en cache pour réduire les appels RPC
2. **Requêtes asynchrones** : Utilisation d'asyncio pour les opérations non-bloquantes
3. **Gestion intelligente des connexions** : Pool de connexions pour optimiser les requêtes HTTP
4. **Retry automatique** : Mécanisme de retry avec backoff exponentiel pour les erreurs temporaires
5. **Monitoring de santé** : Surveillance continue de la disponibilité et performance RPC

## Gestion des erreurs

Le client implémente une gestion robuste des erreurs :

- **Timeout** : Détection et gestion des timeouts RPC
- **Retry** : Retentatives automatiques pour les erreurs temporaires
- **Fallback** : Basculement vers des nœuds RPC alternatifs en cas de panne
- **Logging** : Journalisation détaillée des erreurs pour le débogage

## Limites connues

1. Le client est limité par la congestion du réseau Sonic/Fantom
2. La détection des nouveaux tokens dépend de la configuration du RPC
3. La précision des estimations de gaz peut varier selon la congestion
4. Les transactions peuvent échouer lors de périodes de haute volatilité

## Exemples complets

### Exemple de surveillance et achat automatique

```python
import asyncio
from gbpbot.clients.blockchain_client_factory import BlockchainClientFactory
from decimal import Decimal

async def monitor_and_buy():
    # Initialiser le client
    client = BlockchainClientFactory.create_client("sonic")
    
    # Définir le callback
    async def on_new_token(token_data):
        token_address = token_data["address"]
        
        # Analyser le token
        token_info = await client.get_token_info(token_address)
        if not token_info["name"] or token_info["error"]:
            print(f"Token ignoré: informations incomplètes")
            return
            
        # Vérifier la liquidité
        price = await client.get_token_price(token_address)
        if price <= 0:
            print(f"Token ignoré: pas de liquidité")
            return
            
        # Acheter le token
        print(f"Achat du token {token_info['symbol']} ({token_address})")
        
        wftm = "0x21be370D5312f44cB42ce377BC9b8a0cEF1A4C83"
        amount = 0.1 * 10**18  # 0.1 FTM
        
        try:
            tx_hash = await client.swap_tokens(
                token_in=wftm,
                token_out=token_address,
                amount_in=amount,
                min_amount_out=1
            )
            print(f"Achat réussi: {tx_hash}")
        except Exception as e:
            print(f"Erreur lors de l'achat: {str(e)}")
    
    # Démarrer la surveillance
    await client.monitor_new_tokens(on_new_token)
    
    # Exécuter pendant 1 heure
    await asyncio.sleep(3600)

# Exécuter la fonction
asyncio.run(monitor_and_buy())
```

## Intégration avec le gestionnaire Sonic

Pour une utilisation complète, il est recommandé d'utiliser le gestionnaire Sonic qui coordonne le sniping et l'arbitrage :

```python
from gbpbot.modules.sonic_manager import get_sonic_manager

# Récupérer l'instance du gestionnaire
manager = get_sonic_manager()

# Démarrer les modules
await manager.start(sniper=True, arbitrage=True)

# Obtenir les statistiques
stats = manager.get_stats()
print(f"Profit total: {stats['total_profit']}")

# Arrêter les modules
await manager.stop()
```

## Contribution

Pour contribuer au développement du client Sonic, veuillez suivre les instructions dans le fichier CONTRIBUTING.md principal du GBPBot.

## Feuille de route

- **v1.0** : Support de base pour Sonic avec sniping et monitoring
- **v1.1** : Ajout du support complet pour l'arbitrage
- **v1.2** : Optimisations MEV pour transactions prioritaires
- **v1.3** : Support multi-chain pour arbitrage cross-chain
- **v1.4** : Intégration avec l'IA pour l'analyse de tokens

---

Pour toute question ou assistance, veuillez contacter l'équipe GBPBot ou ouvrir une issue sur GitHub. 