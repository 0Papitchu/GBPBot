# Adaptateur Solana Web3.js

## Introduction

L'adaptateur Solana Web3.js est une solution qui permet à GBPBot de fonctionner avec Python 3.11+, en contournant les limitations de compatibilité de la bibliothèque `solana-py`. Cet adaptateur permet d'utiliser la bibliothèque JavaScript `@solana/web3.js` depuis Python, offrant ainsi toutes les fonctionnalités essentielles pour interagir avec la blockchain Solana.

## Prérequis

- Python 3.11 ou supérieur
- Node.js 16.x ou supérieur
- npm 7.x ou supérieur

## Architecture

L'adaptateur suit une architecture de pont (bridge) entre Python et Node.js :

```
Python (GBPBot) <-> Adaptateur Python <-> Node.js <-> @solana/web3.js <-> Solana Blockchain
```

L'adaptateur est composé des éléments suivants :

1. **Module Python** : `gbpbot/adapters/solana_web3.py`
   - Fournit des classes équivalentes à celles de `solana-py`
   - Gère la communication avec Node.js

2. **Script Node.js** : `gbpbot/adapters/node_bridge/solana_bridge.js`
   - Utilise `@solana/web3.js` pour interagir avec Solana
   - Expose des fonctions accessibles depuis Python

3. **Module d'importation** : `gbpbot/utils/solana_imports.py`
   - Point d'entrée centralisé pour tous les imports liés à Solana
   - Détecte automatiquement si l'adaptateur est disponible

## Fonctionnalités Supportées

L'adaptateur implémente les fonctionnalités essentielles suivantes :

- Création et gestion de portefeuilles
- Récupération de soldes
- Envoi de SOL
- Récupération d'informations de compte
- Récupération de blockhash récents
- Création et signature de transactions
- Récupération de transactions récentes
- Récupération de comptes de tokens

## Installation

L'adaptateur est installé automatiquement lors du démarrage de GBPBot en utilisant le script `start_gbpbot_minimal.bat`. Vous pouvez également l'installer manuellement :

```powershell
# Créer les répertoires nécessaires
mkdir -p gbpbot/adapters/node_bridge

# Initialiser le projet Node.js
cd gbpbot/adapters/node_bridge
npm init -y
npm install @solana/web3.js
```

## Utilisation

L'adaptateur est utilisé automatiquement par GBPBot. Vous n'avez pas besoin de modifier votre code pour l'utiliser, car toutes les importations sont gérées par le module `gbpbot.utils.solana_imports`.

Pour tester manuellement l'adaptateur :

```python
from gbpbot.utils.solana_imports import PublicKey, Keypair, AsyncClient

# Créer un client Solana
client = AsyncClient("https://api.mainnet-beta.solana.com")

# Récupérer le solde d'une adresse
public_key = PublicKey("Ey9dqpS9PBRuMDGVj3Ec2W5d3mfnHNcHMYLMmJ17GVD1")
balance = await client.get_balance(public_key)
sol_balance = balance / 1_000_000_000  # Convertir lamports en SOL
print(f"Solde: {sol_balance} SOL")
```

## Fonctionnalités Avancées

L'adaptateur implémente actuellement les fonctionnalités essentielles pour le fonctionnement de GBPBot. Pour les fonctionnalités avancées comme la création de tokens SPL, les programmes Anchor ou les souscriptions WebSocket, des extensions futures seront nécessaires.

## Dépannage

### Erreur "Node.js n'est pas installé"

Vérifiez que Node.js est installé et dans votre PATH :

```powershell
node -v
npm -v
```

Si ces commandes ne fonctionnent pas, [téléchargez et installez Node.js](https://nodejs.org/).

### Erreur "Module @solana/web3.js introuvable"

Vérifiez que le module est installé :

```powershell
cd gbpbot/adapters/node_bridge
npm list @solana/web3.js
```

Si le module n'est pas installé, exécutez :

```powershell
npm install @solana/web3.js
```

### Erreur lors de l'exécution des tests

Si vous rencontrez des erreurs lors de l'exécution des tests, vérifiez que :

1. Le script JavaScript `solana_bridge.js` existe et est correctement configuré
2. Node.js et npm sont correctement installés
3. Le module `@solana/web3.js` est installé
4. Vous avez accès à Internet pour se connecter aux nœuds Solana

Vous pouvez exécuter le script de test pour vérifier la configuration :

```powershell
python test_solana_web3_adapter.py
```

## Limitations Connues

L'adaptateur actuel présente quelques limitations :

1. **Performance** : La communication entre Python et Node.js via des sous-processus peut introduire une légère latence
2. **Fonctionnalités avancées** : Certaines fonctionnalités avancées de `solana-py` ne sont pas encore implémentées
3. **Souscriptions WebSocket** : Non supportées dans la version actuelle

## Roadmap

- Support pour la création et gestion de tokens SPL
- Support pour les programmes Anchor
- Support pour les souscriptions WebSocket
- Amélioration des performances avec un mécanisme de communication plus rapide 