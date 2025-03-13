# Guide d'utilisation du SonicBlockchainClient

> **IMPORTANT** : Ce document est obsolète et a été remplacé par un guide unifié plus complet.
> 
> Veuillez consulter [SONIC_GUIDE.md](SONIC_GUIDE.md) pour la documentation à jour sur l'intégration Sonic.

---

## Redirection

Cette documentation a été consolidée avec `SONIC_CLIENT.md` et `SONIC_INTEGRATION.md` en un seul guide complet.

Le nouveau document unifié contient :
- Une architecture détaillée des composants Sonic
- Un guide complet de configuration et d'utilisation
- Des exemples pratiques de sniping et d'arbitrage
- Des conseils de dépannage et bonnes pratiques
- Des modèles de code pour l'intégration avec d'autres modules

**Merci de vous référer au nouveau guide : [SONIC_GUIDE.md](SONIC_GUIDE.md)**

## Table des matières

1. [Configuration](#configuration)
2. [Initialisation](#initialisation)
3. [Opérations de base](#opérations-de-base)
   - [Connexion](#connexion)
   - [Vérification de solde](#vérification-de-solde)
   - [Obtention du prix d'un token](#obtention-du-prix-dun-token)
4. [Approbation de tokens](#approbation-de-tokens)
5. [Exécution de swaps](#exécution-de-swaps)
6. [Analyse de contrats](#analyse-de-contrats)
7. [Détection de nouveaux tokens](#détection-de-nouveaux-tokens)
8. [Gestion des erreurs](#gestion-des-erreurs)
9. [Bonnes pratiques](#bonnes-pratiques)
10. [Exemples complets](#exemples-complets)

## Configuration

Le client Sonic nécessite un fichier de configuration JSON structuré avec les informations suivantes :

```json
{
    "rpc": {
        "providers": {
            "sonic": {
                "mainnet": [
                    {"name": "Sonic RPC 1", "url": "https://mainnet.sonic.ooo/rpc", "weight": 2},
                    {"name": "Sonic RPC 2", "url": "https://sonic-api.internetcomputer.org", "weight": 1}
                ]
            }
        },
        "timeout": 30
    },
    "tokens": {
        "icp": "0x4943502D6C6567650000000000000000",
        "wicp": "0x5749435000000000000000000000000000",
        "usdc": "0x555344432D7461687372000000000000000000"
    },
    "dex": {
        "sonic": {
            "router_address": "0x536F6E69635F526F75746572000000000000000000",
            "factory_address": "0x536F6E69635F466163746F727900000000000000"
        }
    },
    "wallet": {
        "private_key": "YOUR_PRIVATE_KEY"
    }
}
```

### Configuration des RPC

- Vous pouvez configurer plusieurs RPC avec des poids différents pour la redondance
- La configuration permet de spécifier des endpoints pour mainnet et testnet
- Le timeout est configurable pour les appels RPC

### Configuration des tokens

- Ajoutez les adresses des tokens couramment utilisés pour faciliter leur accès
- Le token natif (ICP) et le wrapped token (WICP) sont essentiels

### Configuration des DEX

- Spécifiez l'adresse du routeur et du factory pour les interactions avec le DEX
- Ces adresses sont utilisées pour les swaps et la découverte de nouveaux tokens

### Configuration du wallet

- **IMPORTANT** : Ne jamais stocker la clé privée directement dans le code
- Utilisez des variables d'environnement ou un service de gestion de secrets

## Initialisation

Pour initialiser le client :

```python
from gbpbot.core.blockchain_factory import BlockchainFactory

# Chargement de la configuration
with open("config/sonic_config.json", "r") as f:
    config = json.load(f)

# Création du client
client = BlockchainFactory.get_blockchain_client("sonic", config)
```

## Opérations de base

### Connexion

```python
# Connexion asynchrone
connected = await client.connect()
if not connected:
    print("Échec de connexion au réseau Sonic")
```

### Vérification de solde

```python
# Vérifier le solde ICP (token natif)
icp_balance = await client.get_token_balance(client.token_addresses["ICP"])
print(f"Solde ICP: {icp_balance}")

# Vérifier le solde WICP (wrapped token)
wicp_balance = await client.get_token_balance(client.token_addresses["WICP"])
print(f"Solde WICP: {wicp_balance}")

# Vérifier le solde d'un autre token par son adresse
usdc_balance = await client.get_token_balance("0x555344432D7461687372000000000000000000")
print(f"Solde USDC: {usdc_balance}")
```

### Obtention du prix d'un token

```python
# Obtenir le prix ICP en USDC
icp_price = await client.get_token_price(
    client.token_addresses["ICP"],
    client.token_addresses["USDC"]
)
print(f"Prix ICP: {icp_price} USDC")

# Obtenir le prix d'un token personnalisé
custom_token_price = await client.get_token_price(
    "0xADRESSE_DU_TOKEN",
    client.token_addresses["USDC"]
)
print(f"Prix du token: {custom_token_price} USDC")
```

## Approbation de tokens

Avant d'échanger un token, vous devez l'approuver pour le routeur DEX :

```python
# Vérifier si le token est approuvé pour un montant spécifique
is_approved = await client.check_token_approval(
    client.token_addresses["WICP"],
    client.dex_router_address,
    amount=10.0  # Approuver pour 10 WICP
)

if not is_approved:
    # Approuver le token
    approval_result = await client.approve_token(
        client.token_addresses["WICP"],
        client.dex_router_address,
        amount=10.0
    )
    
    if approval_result["success"]:
        print(f"Approbation réussie. Hash de transaction: {approval_result['tx_hash']}")
    else:
        print(f"Échec de l'approbation: {approval_result.get('error')}")
```

Pour une approbation illimitée (utiliser avec précaution) :

```python
unlimited_approval = await client.approve_token(
    client.token_addresses["WICP"],
    client.dex_router_address,
    amount=None  # None signifie une approbation illimitée
)
```

## Exécution de swaps

```python
# Échanger 1 WICP contre USDC avec 0.5% de slippage
swap_result = await client.execute_swap(
    client.token_addresses["WICP"],  # Token d'entrée
    client.token_addresses["USDC"],  # Token de sortie
    amount=1.0,                     # Montant à échanger
    slippage=0.5                    # 0.5% de slippage
)

if swap_result["success"]:
    print(f"Échange réussi:")
    print(f"  - Hash de transaction: {swap_result['tx_hash']}")
    print(f"  - Entrée: {swap_result['amount_in']} WICP")
    print(f"  - Sortie: {swap_result['amount_out']} USDC")
else:
    print(f"Échec de l'échange: {swap_result.get('error')}")
```

## Analyse de contrats

```python
# Analyser un contrat de token pour détecter les risques
analysis = await client.analyze_contract("0xADRESSE_DU_TOKEN")

print(f"Analyse du contrat:")
print(f"  - Nom du token: {analysis['token_name']}")
print(f"  - Symbole: {analysis['token_symbol']}")
print(f"  - Sécurisé: {analysis['is_safe']}")

if len(analysis["risks"]) > 0:
    print(f"  - Risques détectés:")
    for risk in analysis["risks"]:
        print(f"    * {risk}")
else:
    print(f"  - Aucun risque détecté")
```

## Détection de nouveaux tokens

```python
# Récupérer les nouveaux tokens depuis le dernier bloc analysé
new_tokens = await client.get_new_tokens()

for token in new_tokens:
    print(f"Nouveau token détecté:")
    print(f"  - Nom: {token['name']}")
    print(f"  - Symbole: {token['symbol']}")
    print(f"  - Adresse: {token['address']}")
    print(f"  - Bloc: {token['block_number']}")
    print(f"  - Timestamp: {token['timestamp']}")
    
    # Analyser automatiquement le contrat
    analysis = await client.analyze_contract(token["address"])
    if not analysis["is_safe"]:
        print(f"  - ATTENTION: Token potentiellement risqué!")
        print(f"  - Risques: {', '.join(analysis['risks'])}")
```

## Gestion des erreurs

Le client Sonic intègre une gestion d'erreurs robuste. Toutes les méthodes qui effectuent des transactions ou des interactions avec la blockchain renvoient un dictionnaire avec au moins les clés suivantes :

- `success` : booléen indiquant si l'opération a réussi
- `error` : message d'erreur détaillé en cas d'échec (uniquement présent si `success` est `False`)

Exemple de gestion des erreurs :

```python
try:
    result = await client.execute_swap(token_in, token_out, amount)
    if not result["success"]:
        # Gérer l'échec de la transaction
        if "insufficient funds" in result["error"].lower():
            print("Solde insuffisant pour effectuer l'échange")
        elif "slippage" in result["error"].lower():
            print("Échec dû au slippage - le prix a changé trop rapidement")
        else:
            print(f"Échec de l'échange: {result['error']}")
except Exception as e:
    # Gérer les exceptions inattendues
    print(f"Exception inattendue: {str(e)}")
```

## Bonnes pratiques

1. **Sécurité des clés privées** : Ne jamais stocker les clés privées en dur dans le code ou les fichiers de configuration exposés.

2. **Gestion des exceptions** : Enveloppez toujours le code asynchrone dans des blocs try/except pour gérer les erreurs réseau.

3. **Analyse des contrats** : Toujours analyser les nouveaux contrats de tokens avant d'interagir avec eux.

4. **Validation des transactions** : Attendez toujours la confirmation des transactions (via la méthode `wait_for_transaction`) avant de procéder à d'autres opérations.

5. **Limitation du slippage** : Définissez toujours une valeur de slippage raisonnable pour éviter les pertes dues aux mouvements de prix.

6. **Surveillance des gaz** : Surveillez les prix du gaz et ajustez vos transactions en conséquence.

7. **Caching** : Utilisez le cache intégré pour les données fréquemment accédées comme les soldes et les prix.

## Exemples complets

Pour des exemples complets d'utilisation du client Sonic, consultez les scripts suivants :

- `examples/sonic_client_example.py` : Exemple complet d'utilisation du client
- `tests/unit/test_sonic_blockchain.py` : Tests unitaires montrant l'utilisation de chaque méthode

## Exécution des tests

Pour exécuter les tests unitaires et vérifier que l'implémentation fonctionne correctement :

```bash
python tests/run_sonic_tests.py
```

## Dépannage

### Problèmes de connexion RPC

Si vous rencontrez des problèmes de connexion aux RPC Sonic :

1. Vérifiez que les URLs des RPC sont correctes et accessibles
2. Augmentez la valeur du timeout dans la configuration
3. Assurez-vous d'avoir une connexion Internet stable

### Problèmes d'approbation

Si les approbations de tokens échouent :

1. Vérifiez que votre wallet dispose de suffisamment d'ICP pour payer les frais
2. Confirmez que vous utilisez la bonne adresse de routeur DEX
3. Vérifiez que le token que vous essayez d'approuver est valide

### Échecs de transactions

Si les transactions échouent :

1. Vérifiez les soldes de tokens et d'ICP
2. Augmentez la valeur de slippage si le marché est volatil
3. Examinez l'erreur renvoyée par la méthode pour des détails spécifiques

---

Pour toute question ou problème supplémentaire, veuillez ouvrir une issue sur le dépôt du projet ou contacter l'équipe de développement. 