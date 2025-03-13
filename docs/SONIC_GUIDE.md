# Guide Complet de l'Intégration Sonic pour GBPBot

## Table des matières

1. [Introduction](#introduction)
2. [Fonctionnalités principales](#fonctionnalités-principales)
3. [Architecture et composants](#architecture-et-composants)
4. [Configuration requise](#configuration-requise)
5. [Installation](#installation)
6. [Configuration](#configuration)
7. [Utilisation du client Sonic](#utilisation-du-client-sonic)
   - [Initialisation](#initialisation)
   - [Opérations de base](#opérations-de-base)
   - [Vérification de solde](#vérification-de-solde)
   - [Obtention du prix d'un token](#obtention-du-prix-dun-token)
   - [Approbation de tokens](#approbation-de-tokens)
   - [Exécution de swaps](#exécution-de-swaps)
   - [Analyse de contrats](#analyse-de-contrats)
8. [Module de Sniping Sonic](#module-de-sniping-sonic)
9. [Module d'arbitrage sur Sonic](#module-darbitrage-sur-sonic)
10. [Intégration avec le reste de GBPBot](#intégration-avec-le-reste-de-gbpbot)
11. [Gestion des erreurs](#gestion-des-erreurs)
12. [Bonnes pratiques](#bonnes-pratiques)
13. [Exemples complets](#exemples-complets)
14. [Dépannage](#dépannage)

---

## Introduction

Le module Sonic est une extension du GBPBot qui permet de trader sur la blockchain Sonic (basée sur Fantom). Cette intégration permet aux utilisateurs de GBPBot d'étendre leurs opérations de trading de memecoins à une blockchain supplémentaire, augmentant ainsi les opportunités de profit et la diversification.

Cette documentation détaille l'utilisation du client Sonic, ses fonctionnalités, et son intégration avec les autres modules du GBPBot, en combinant les aspects techniques et les guides pratiques d'utilisation.

## Fonctionnalités principales

- **Connexion blockchain** : Interface avec les nœuds RPC Sonic (Fantom)
- **Gestion des transactions** : Création, signature et envoi de transactions
- **Interaction avec les DEX** : Support complet de SpiritSwap et SpookySwap
- **Monitoring de tokens** : Détection et analyse des nouveaux tokens
- **Évaluation de prix** : Récupération et analyse des prix de tokens
- **Gestion des pools** : Interrogation et analyse des pools de liquidité
- **Analyse des contrats** : Récupération et évaluation des contrats intelligents
- **Sniping intelligent** : Détection et achat automatique des nouveaux tokens prometteurs
- **Arbitrage multi-DEX** : Exploitation des écarts de prix entre DEX
- **Intégration IA** : Analyse des tokens via l'intelligence artificielle

## Architecture et composants

L'intégration Sonic dans GBPBot comprend les composants clés suivants :

```
┌─────────────────────┐      ┌───────────────────┐      ┌───────────────────┐
│                     │      │                   │      │                   │
│  SonicBlockchain    │<─────│  SonicManager     │<─────│  Modules GBPBot   │
│  Client             │      │                   │      │  (Core, IA, etc.) │
│                     │      │                   │      │                   │
└─────────────────────┘      └───────────────────┘      └───────────────────┘
         │                           │                           │
         ▼                           ▼                           ▼
┌─────────────────────┐      ┌───────────────────┐      ┌───────────────────┐
│                     │      │                   │      │                   │
│  Blockchain Sonic   │      │  SonicSniper      │      │  Interfaces       │
│  (Fantom)           │      │  Module           │      │  utilisateur      │
│                     │      │                   │      │                   │
└─────────────────────┘      └───────────────────┘      └───────────────────┘
```

1. **SonicBlockchainClient (`sonic_client.py`)** :
   - Gère les connexions RPC à la blockchain Sonic
   - Interface avec les contrats intelligents sur Sonic
   - Fournit les méthodes de base pour les transactions

2. **SonicManager (`sonic_manager.py`)** :
   - Coordonne les opérations sur Sonic
   - Gère les configurations et les paramètres
   - Monitore l'état global de la blockchain

3. **SonicSniper (`sonic_sniper.py`)** :
   - Détecte les nouveaux tokens sur Sonic
   - Analyse la viabilité et le potentiel des tokens
   - Exécute les stratégies de sniping

## Configuration requise

### Dépendances système

- Python 3.9+
- Accès Internet stable
- Mémoire : minimum 4 GB RAM
- Stockage : minimum 10 GB d'espace libre

### Dépendances Python

Le client Sonic nécessite les bibliothèques Python suivantes :

```bash
pip install web3==6.0.0 aiohttp==3.8.5 asyncio eth-account==0.8.0 eth-typing==3.2.0
```

Pour l'analyse IA des tokens (optionnel mais recommandé) :

```bash
pip install langchain==0.0.267 tensorflow-lite==2.12.0
```

## Installation

L'intégration Sonic est incluse dans l'installation standard de GBPBot. Si vous avez besoin de l'installer séparément :

```bash
# Clone du dépôt GBPBot
git clone https://github.com/yourusername/GBPBot.git
cd GBPBot

# Installation des dépendances spécifiques à Sonic
pip install -r requirements-sonic.txt

# Installation en mode développement
pip install -e .
```

## Configuration

La configuration du client Sonic se fait via le fichier `config.yaml` dans le répertoire `config/` :

```yaml
sonic:
  # Endpoints RPC pour la blockchain Sonic (Fantom)
  rpc:
    mainnet:
      - "https://rpc.ftm.tools"
      - "https://rpc.ankr.com/fantom"
      - "https://rpcapi.fantom.network"
    testnet:
      - "https://rpc.testnet.fantom.network"
  
  # Configuration des DEX supportés
  dex:
    spookyswap:
      router: "0x31F63A33141fFee63D4B26755430a390ACdD8a4d"
      factory: "0x152eE697f2E276fA89E96742e9bB9aB1F2E61bE3"
    spiritswap:
      router: "0x16327E3FbDaCA3bcF7E38F5Af2599D2DDc33aE52"
      factory: "0xEF45d134b73241eDa7703fa787148D9C9F4950b0"
  
  # Paramètres de wallet et de gas
  wallet:
    gas_multiplier: 1.2
    max_gas_price: 10000  # en Gwei
    priority_fee: 2  # en Gwei
    default_slippage: 3.0  # en pourcentage
  
  # Paramètres de sniping
  sniping:
    min_liquidity: 5000  # en USD
    max_buy_tax: 10  # en pourcentage
    max_sell_tax: 15  # en pourcentage
    enable_contract_analysis: true
    blacklisted_tokens: []
  
  # Paramètres d'arbitrage
  arbitrage:
    min_profit_threshold: 0.5  # en pourcentage
    max_path_length: 3
    gas_overhead_estimate: 200000
```

## Utilisation du client Sonic

### Initialisation

Pour initialiser le client Sonic dans votre code :

```python
from gbpbot.blockchains.sonic.client import SonicBlockchainClient

# Initialisation basique
client = SonicBlockchainClient()

# Initialisation avec un chemin personnalisé pour la configuration
client = SonicBlockchainClient(config_path="chemin/vers/config.yaml")

# Initialisation avec un wallet spécifique
client = SonicBlockchainClient(wallet_private_key="0xvotre_clé_privée")
```

### Opérations de base

#### Connexion à la blockchain

```python
# Connexion à la mainnet
await client.connect()

# Connexion à la testnet
await client.connect(network="testnet")

# Vérification de la connexion
is_connected = await client.check_connection()
print(f"Connecté: {is_connected}")
```

### Vérification de solde

```python
# Obtenir le solde FTM
ftm_balance = await client.get_balance()
print(f"Solde FTM: {ftm_balance}")

# Obtenir le solde d'un token spécifique
token_address = "0xadresse_du_token"
token_balance = await client.get_token_balance(token_address)
print(f"Solde du token: {token_balance}")
```

### Obtention du prix d'un token

```python
# Obtenir le prix en USD
token_address = "0xadresse_du_token"
price_usd = await client.get_token_price_usd(token_address)
print(f"Prix: ${price_usd}")

# Obtenir le prix en FTM
price_ftm = await client.get_token_price_in_ftm(token_address)
print(f"Prix: {price_ftm} FTM")

# Obtenir les informations complètes d'un token
token_info = await client.get_token_info(token_address)
print(f"Nom: {token_info['name']}")
print(f"Symbole: {token_info['symbol']}")
print(f"Décimales: {token_info['decimals']}")
print(f"Offre totale: {token_info['totalSupply']}")
```

### Approbation de tokens

Avant d'échanger des tokens, vous devez les approuver pour le router DEX :

```python
# Approuver un token pour SpookySwap
token_address = "0xadresse_du_token"
amount_to_approve = 1000 * 10**18  # 1000 tokens avec 18 décimales
tx_hash = await client.approve_token(token_address, amount_to_approve, dex="spookyswap")
print(f"Transaction d'approbation envoyée: {tx_hash}")

# Approuver un token pour une utilisation illimitée
tx_hash = await client.approve_token(token_address, client.MAX_UINT256, dex="spiritswap")
print(f"Approbation illimitée envoyée: {tx_hash}")
```

### Exécution de swaps

```python
# Swap de FTM vers un token
token_address = "0xadresse_du_token"
amount_ftm = 0.1 * 10**18  # 0.1 FTM en wei
slippage = 3.0  # 3%
tx_hash = await client.swap_exact_ftm_for_tokens(
    amount_ftm,
    token_address,
    slippage=slippage,
    dex="spookyswap"
)
print(f"Swap envoyé: {tx_hash}")

# Swap d'un token vers FTM
token_amount = 100 * 10**18  # 100 tokens
min_ftm_out = 0.05 * 10**18  # Au moins 0.05 FTM
tx_hash = await client.swap_exact_tokens_for_ftm(
    token_amount,
    min_ftm_out,
    token_address,
    dex="spiritswap"
)
print(f"Swap envoyé: {tx_hash}")
```

### Analyse de contrats

```python
# Analyser un contrat de token
token_address = "0xadresse_du_token"
security_report = await client.analyze_token_contract(token_address)

# Vérifier la sécurité du token
if security_report["is_safe"]:
    print("Le token semble sûr.")
else:
    print("Attention! Token potentiellement dangereux:")
    for issue in security_report["issues"]:
        print(f"- {issue}")
```

## Module de Sniping Sonic

Le module de sniping Sonic (`sonic_sniper.py`) permet de détecter et d'acheter automatiquement les nouveaux tokens prometteurs.

### Initialisation du sniper

```python
from gbpbot.blockchains.sonic.sniper import SonicSniper

# Initialisation du sniper
sniper = SonicSniper()

# Démarrer le monitoring des nouveaux tokens
await sniper.start_monitoring()
```

### Configuration du sniping

```python
# Configurer les critères de sniping
sniper.configure({
    "min_liquidity_usd": 10000,  # Liquidité minimale en USD
    "max_buy_tax": 8,            # Taxe d'achat maximale (%)
    "max_sell_tax": 10,          # Taxe de vente maximale (%)
    "buy_amount_ftm": 0.2,       # Montant à investir en FTM
    "take_profit": 50,           # Take profit à +50%
    "stop_loss": 20,             # Stop loss à -20%
    "use_ai_analysis": True      # Utiliser l'analyse IA
})
```

### Exemple de sniping automatique

```python
# Callback de notification
def on_token_detected(token_data):
    print(f"Nouveau token détecté: {token_data['symbol']}")
    print(f"Adresse: {token_data['address']}")
    print(f"Score IA: {token_data['ai_score']}/100")

# Enregistrer le callback
sniper.register_token_callback(on_token_detected)

# Démarrer le sniping automatique
await sniper.start_auto_sniping()

# Pour arrêter le sniping
# await sniper.stop_auto_sniping()
```

## Module d'arbitrage sur Sonic

Le module d'arbitrage Sonic permet d'exploiter les écarts de prix entre les différents DEX sur Sonic.

### Initialisation de l'arbitrage

```python
from gbpbot.blockchains.sonic.arbitrage import SonicArbitrage

# Initialisation du module d'arbitrage
arbitrage = SonicArbitrage()

# Démarrer la recherche d'opportunités
await arbitrage.start_monitoring()
```

### Configuration de l'arbitrage

```python
# Configurer les paramètres d'arbitrage
arbitrage.configure({
    "min_profit_percentage": 0.5,  # Profit minimum en pourcentage
    "max_trade_amount_ftm": 1.0,   # Montant maximum par transaction en FTM
    "gas_price_multiplier": 1.2,   # Multiplicateur de prix du gas
    "dex_pairs": [                 # Paires de DEX à surveiller
        ("spookyswap", "spiritswap")
    ]
})
```

### Exemple d'arbitrage automatique

```python
# Callback de notification
def on_opportunity_found(opportunity):
    print(f"Opportunité d'arbitrage trouvée!")
    print(f"Chemin: {opportunity['path']}")
    print(f"Profit estimé: {opportunity['estimated_profit_percentage']}%")

# Enregistrer le callback
arbitrage.register_opportunity_callback(on_opportunity_found)

# Démarrer l'arbitrage automatique
await arbitrage.start_auto_arbitrage()

# Pour arrêter l'arbitrage
# await arbitrage.stop_auto_arbitrage()
```

## Intégration avec le reste de GBPBot

L'intégration Sonic s'intègre parfaitement avec les autres modules de GBPBot :

### Utilisation avec le mode automatique

```python
from gbpbot.auto_mode import AutoMode
from gbpbot.blockchains.sonic.manager import SonicManager

# Initialiser le gestionnaire Sonic
sonic_manager = SonicManager()

# Ajouter Sonic au mode automatique
auto_mode = AutoMode()
auto_mode.register_blockchain_manager(sonic_manager)

# Démarrer le mode automatique
await auto_mode.start()
```

### Utilisation avec l'IA

```python
from gbpbot.ai.analyzer import TokenAnalyzer
from gbpbot.blockchains.sonic.client import SonicBlockchainClient

# Initialiser le client Sonic
sonic_client = SonicBlockchainClient()

# Initialiser l'analyseur IA
token_analyzer = TokenAnalyzer()

# Analyser un token Sonic avec l'IA
token_address = "0xadresse_du_token"
token_data = await sonic_client.get_token_info(token_address)
contract_code = await sonic_client.get_contract_code(token_address)

# Analyse IA
analysis_result = await token_analyzer.analyze_token(
    token_data,
    contract_code,
    blockchain="sonic"
)

print(f"Score IA: {analysis_result['score']}/100")
print(f"Risques: {analysis_result['risks']}")
print(f"Opportunités: {analysis_result['opportunities']}")
```

## Gestion des erreurs

Le client Sonic inclut une gestion robuste des erreurs :

```python
from gbpbot.blockchains.sonic.exceptions import (
    SonicConnectionError,
    SonicTransactionError,
    SonicContractError,
    SonicLiquidityError
)

try:
    # Code qui peut générer une erreur
    await client.swap_exact_ftm_for_tokens(amount, token_address)
except SonicConnectionError as e:
    print(f"Erreur de connexion: {e}")
    # Tenter de reconnecter
    await client.reconnect()
except SonicTransactionError as e:
    print(f"Erreur de transaction: {e}")
    # Analyser l'erreur pour déterminer si c'est un problème de gas
    if "gas" in str(e).lower():
        # Augmenter le gas
        client.increase_gas_settings(multiplier=1.5)
except SonicContractError as e:
    print(f"Erreur de contrat: {e}")
    # Token potentiellement malveillant
except SonicLiquidityError as e:
    print(f"Erreur de liquidité: {e}")
    # Pas assez de liquidité dans le pool
except Exception as e:
    print(f"Erreur inattendue: {e}")
```

## Bonnes pratiques

Pour une utilisation optimale du client Sonic, suivez ces bonnes pratiques :

1. **Toujours analyser les contrats** avant d'interagir avec de nouveaux tokens
2. **Commencer avec de petits montants** pour tester les transactions
3. **Utiliser des slippages adaptés** au marché (3-5% pour les tokens volatils)
4. **Consulter les statistiques du réseau** pour optimiser les prix du gas
5. **Maintenir une liste noire** des tokens problématiques
6. **Utiliser l'analyse IA** pour évaluer la sécurité et le potentiel des tokens
7. **Monitorer régulièrement les balances** pour détecter les anomalies
8. **Configurer les alertes de prix** pour les prises de profit automatiques
9. **Diversifier entre les DEX** pour maximiser les opportunités
10. **Régulièrement mettre à jour** la configuration pour suivre l'évolution de l'écosystème

## Exemples complets

### Exemple 1: Détection et achat d'un nouveau token

```python
import asyncio
from gbpbot.blockchains.sonic.client import SonicBlockchainClient
from gbpbot.blockchains.sonic.sniper import SonicSniper
from gbpbot.ai.analyzer import TokenAnalyzer

async def snipe_new_token():
    # Initialisation
    client = SonicBlockchainClient()
    sniper = SonicSniper()
    analyzer = TokenAnalyzer()
    
    # Configurer le sniper
    sniper.configure({
        "min_liquidity_usd": 8000,
        "max_buy_tax": 10,
        "buy_amount_ftm": 0.15,
        "take_profit": 40,
        "stop_loss": 15
    })
    
    # Fonction de callback
    async def on_token_detected(token_data):
        print(f"Nouveau token détecté: {token_data['symbol']}")
        
        # Analyse IA
        score = await analyzer.quick_analyze(token_data)
        
        if score >= 70:
            print(f"Score IA élevé ({score}/100), achat en cours...")
            
            # Acheter le token
            tx_hash = await client.swap_exact_ftm_for_tokens(
                0.15 * 10**18,  # 0.15 FTM
                token_data['address'],
                slippage=5.0
            )
            
            print(f"Achat effectué! TX: {tx_hash}")
            
            # Configurer un suivi du prix
            await client.setup_price_monitor(
                token_data['address'],
                take_profit=40,
                stop_loss=15,
                callback=sell_token
            )
        else:
            print(f"Score IA insuffisant ({score}/100), achat ignoré")
    
    # Fonction de vente
    async def sell_token(token_address, price_change, trigger_type):
        print(f"{trigger_type} déclenché! Variation de prix: {price_change}%")
        
        # Obtenir la balance
        balance = await client.get_token_balance(token_address)
        
        if balance > 0:
            # Vendre tous les tokens
            tx_hash = await client.swap_exact_tokens_for_ftm(
                balance,
                0,  # Montant minimum de FTM (calculé automatiquement avec slippage)
                token_address,
                slippage=5.0
            )
            
            print(f"Vente effectuée! TX: {tx_hash}")
    
    # Enregistrer le callback
    sniper.register_token_callback(on_token_detected)
    
    # Démarrer le monitoring
    await sniper.start_monitoring()
    
    # Garder le script en cours d'exécution
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("Arrêt du sniping...")
        await sniper.stop_monitoring()

# Exécuter le script
if __name__ == "__main__":
    asyncio.run(snipe_new_token())
```

### Exemple 2: Arbitrage entre SpookySwap et SpiritSwap

```python
import asyncio
from gbpbot.blockchains.sonic.client import SonicBlockchainClient
from gbpbot.blockchains.sonic.arbitrage import SonicArbitrage

async def run_arbitrage():
    # Initialisation
    client = SonicBlockchainClient()
    arbitrage = SonicArbitrage()
    
    # Configurer l'arbitrage
    arbitrage.configure({
        "min_profit_percentage": 0.7,
        "max_trade_amount_ftm": 0.5,
        "gas_price_multiplier": 1.1,
        "check_interval_seconds": 5
    })
    
    # Fonction de callback pour les opportunités
    async def on_opportunity(opportunity):
        print(f"Opportunité trouvée entre {opportunity['dex_from']} et {opportunity['dex_to']}")
        print(f"Token: {opportunity['token_symbol']} ({opportunity['token_address']})")
        print(f"Profit estimé: {opportunity['estimated_profit_percentage']}%")
        
        # Vérifier que le profit estimé dépasse les frais de transaction
        if opportunity['estimated_profit_usd'] > opportunity['estimated_gas_cost_usd']:
            print("Exécution de l'arbitrage...")
            
            # Exécuter l'arbitrage
            result = await arbitrage.execute_arbitrage(opportunity)
            
            if result['success']:
                print(f"Arbitrage réussi! TX: {result['tx_hash']}")
                print(f"Profit réalisé: {result['actual_profit_percentage']}%")
            else:
                print(f"Échec de l'arbitrage: {result['error']}")
        else:
            print("Profit insuffisant pour couvrir les frais de gas, arbitrage ignoré")
    
    # Enregistrer le callback
    arbitrage.register_opportunity_callback(on_opportunity)
    
    # Démarrer la recherche d'opportunités
    await arbitrage.start_monitoring()
    
    print("Recherche d'opportunités d'arbitrage en cours...")
    
    # Garder le script en cours d'exécution
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("Arrêt de l'arbitrage...")
        await arbitrage.stop_monitoring()

# Exécuter le script
if __name__ == "__main__":
    asyncio.run(run_arbitrage())
```

## Dépannage

### Problèmes de connexion RPC

Si vous rencontrez des problèmes de connexion RPC :

1. Vérifiez votre connexion Internet
2. Essayez un autre endpoint RPC dans la configuration
3. Utilisez cette méthode pour tester la connexion :

```python
async def test_rpc_connection():
    client = SonicBlockchainClient()
    
    # Tester chaque endpoint RPC
    rpc_endpoints = client.config["sonic"]["rpc"]["mainnet"]
    
    for endpoint in rpc_endpoints:
        try:
            # Créer un client Web3 temporaire
            from web3 import Web3
            w3 = Web3(Web3.HTTPProvider(endpoint))
            
            # Tester la connexion
            connected = w3.is_connected()
            block_number = w3.eth.block_number if connected else "N/A"
            
            print(f"Endpoint: {endpoint}")
            print(f"Connecté: {connected}")
            print(f"Numéro de bloc: {block_number}")
            print("-" * 50)
        except Exception as e:
            print(f"Erreur avec l'endpoint {endpoint}: {str(e)}")
            print("-" * 50)

# Exécuter le test
asyncio.run(test_rpc_connection())
```

### Problèmes de transaction

Si vos transactions échouent :

1. **Gas insuffisant** : Augmentez le multiplicateur de gas dans la configuration
2. **Slippage insuffisant** : Augmentez le slippage pour les tokens à faible liquidité
3. **Problèmes d'approbation** : Vérifiez que le token est bien approuvé pour le router DEX

```python
# Vérifier l'approbation
async def check_approval(token_address, dex="spookyswap"):
    client = SonicBlockchainClient()
    
    # Obtenir l'allowance actuelle
    allowance = await client.get_token_allowance(
        token_address,
        client.get_dex_router_address(dex)
    )
    
    print(f"Approbation actuelle pour {dex}: {allowance}")
    
    # Si l'approbation est insuffisante
    if allowance == 0:
        print("Token non approuvé. Approbation en cours...")
        await client.approve_token(token_address, client.MAX_UINT256, dex=dex)
        print("Approbation effectuée!")
```

### Analyse avancée des erreurs

```python
# Fonction d'analyse d'erreur
def analyze_error(error_message):
    if "gas required exceeds allowance" in error_message:
        return "Augmentez la limite de gas ou réduisez le montant de la transaction"
    elif "insufficient funds" in error_message:
        return "Solde insuffisant pour la transaction (incluant les frais de gas)"
    elif "TRANSFER_FROM_FAILED" in error_message:
        return "Échec du transfert, vérifiez l'approbation ou si le token a des restrictions"
    elif "INSUFFICIENT_OUTPUT_AMOUNT" in error_message:
        return "Slippage trop faible pour cette transaction"
    elif "execution reverted" in error_message:
        return "Contrat révoqué, token potentiellement problématique"
    else:
        return "Erreur inconnue, vérifiez les logs pour plus de détails"
```

---

Ce guide unifié combine toutes les informations nécessaires pour utiliser efficacement l'intégration Sonic dans GBPBot. Pour toute question supplémentaire, consultez les canaux de support officiels.

> **Note** : Ce document remplace les guides précédents `SONIC_CLIENT.md`, `sonic_client_guide.md` et `SONIC_INTEGRATION.md`. 