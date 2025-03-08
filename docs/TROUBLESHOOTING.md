# Guide de Dépannage GBPBot

Ce document fournit des solutions aux problèmes les plus courants rencontrés lors de l'utilisation de GBPBot. Suivez ces instructions pas à pas pour résoudre les difficultés techniques.

## Table des Matières

1. [Problèmes d'Installation](#problèmes-dinstallation)
2. [Erreurs de Lancement](#erreurs-de-lancement)
3. [Problèmes de Connexion RPC](#problèmes-de-connexion-rpc)
4. [Erreurs de Transaction](#erreurs-de-transaction)
5. [Problèmes de Performance](#problèmes-de-performance)
6. [Erreurs d'API](#erreurs-dapi)
7. [Logs et Diagnostics](#logs-et-diagnostics)
8. [Résolution Avancée](#résolution-avancée)
9. [Mise à Jour de Sécurité - Mars 2025](#mise-à-jour-de-sécurité---mars-2025)

## Problèmes d'Installation

### Erreurs Pip / Dépendances

#### Conflit de dépendances avec `anchorpy` et `anchorpy-core`

**Symptôme** : Messages d'erreur comme "anchorpy 0.17.0 requires anchorpy-core<0.2.0,>=0.1.2, but you have anchorpy-core 0.2.0"

**Solution** :
```bash
# Solution 1: Désinstaller et réinstaller avec les versions correctes
pip uninstall -y anchorpy anchorpy-core
pip install "anchorpy>=0.17.0,<0.18.0" "anchorpy-core>=0.1.2,<0.2.0"

# Solution 2: Utiliser le script bridge qui gère les dépendances
python gbpbot_cli_bridge.py
# Puis sélectionner "1. Installer les dépendances essentielles"
```

#### Erreur de compilation pour `zstandard`

**Symptôme** : "Microsoft Visual C++ 14.0 or greater is required" lors de l'installation

**Solution** :
1. [Téléchargez les outils de build Microsoft C++](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
2. Installez-les en sélectionnant "C++ build tools" dans l'installateur
3. Redémarrez votre terminal et réessayez l'installation

Alternativement, utilisez une version précompilée :
```bash
pip install --only-binary :all: zstandard
```

### Versions Python Incompatibles

**Symptôme** : Erreurs indiquant que votre version de Python est incompatible

**Solution** :
- GBPBot fonctionne avec Python 3.7 à 3.11
- Vérifiez votre version : `python --version`
- Installez une version compatible si nécessaire depuis [Python.org](https://www.python.org/downloads/)

## Erreurs de Lancement

### Erreur "no running event loop"

**Symptôme** : `RuntimeError: no running event loop` sur Windows

**Solution** :
```bash
# Solution 1: Utiliser le script bridge
python gbpbot_cli_bridge.py
# Puis sélectionner "3. Lancer le bot standard (CLI complet)"

# Solution 2: Utiliser le script de lancement spécifique à Windows
.\lancer_gbpbot_depannage.bat
```

### Erreur "cannot import name 'ResourceMonitorCompat'"

**Symptôme** : `ImportError: cannot import name 'ResourceMonitorCompat' from 'gbpbot.core.monitoring.compatibility'`

**Solution** :
```bash
# Solution 1: Utiliser le script bridge qui corrige les importations circulaires
python gbpbot_cli_bridge.py

# Solution 2: Mise à jour de GBPBot
git pull
pip install -e .
```

### Fichier .env Manquant ou Mal Configuré

**Symptôme** : Messages d'erreur concernant des variables d'environnement ou des clés API manquantes

**Solution** :
1. Copiez le fichier d'exemple : `cp .env.example .env`
2. Éditez le fichier `.env` et ajoutez vos clés API et URLs RPC
3. Utilisez l'outil de validation : `python validate_env.py`

## Problèmes de Connexion RPC

### Endpoints RPC Non Disponibles

**Symptôme** : Erreurs comme "Connection refused" ou "Timeout" lors des appels RPC

**Solutions** :
1. Vérifiez votre connexion internet
2. Testez les endpoints RPC directement :
   ```bash
   curl -X POST -H "Content-Type: application/json" --data '{"jsonrpc":"2.0","id":1,"method":"eth_blockNumber","params":[]}' YOUR_RPC_URL
   ```
3. Essayez des endpoints alternatifs dans votre fichier `.env` :

   - Pour Solana :
     ```
     SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
     ```
   
   - Pour Avalanche :
     ```
     AVALANCHE_RPC_URL=https://api.avax.network/ext/bc/C/rpc
     ```
   
   - Pour Ethereum :
     ```
     ETH_RPC_URL=https://ethereum.publicnode.com
     ```

### Erreurs de Rate Limiting

**Symptôme** : Erreurs "Too many requests" ou 429 status code

**Solution** :
1. Utilisez un endpoint RPC payant avec des limites plus élevées
2. Réduisez la fréquence des requêtes dans la configuration
3. Répartissez les charges entre plusieurs endpoints RPC

## Erreurs de Transaction

### Transaction Rejected

**Symptôme** : Les transactions sont rejetées par la blockchain

**Solutions possibles** :
1. Vérifiez les fonds disponibles sur votre wallet
2. Augmentez le gas/fee dans les paramètres du bot
3. Vérifiez si votre nonce est correct (pour Ethereum)
4. Assurez-vous que le token n'a pas de restrictions de trading

### Slippage Trop Élevé

**Symptôme** : Les transactions échouent avec "Slippage too high" ou "Price impact too high"

**Solution** :
1. Ajustez les paramètres de slippage dans la configuration
2. Réduisez la taille des transactions
3. Utilisez des DEX avec plus de liquidité

## Problèmes de Performance

### Utilisation Élevée du CPU/Mémoire

**Symptôme** : GBPBot ralentit votre système ou consomme trop de ressources

**Solution** :
1. Réduisez le nombre de paires surveillées simultanément
2. Augmentez l'intervalle entre les vérifications
3. Désactivez les modules non essentiels
4. Utilisez le HardwareOptimizer intégré :
   ```python
   from gbpbot.core.monitoring.compatibility import get_hardware_optimizer
   optimizer = get_hardware_optimizer()
   optimizer.apply_optimizations()
   ```

### Bot Trop Lent pour Sniper ou Front-run

**Symptôme** : D'autres bots vous battent systématiquement sur les transactions

**Solution** :
1. Utilisez un RPC privé avec accès mempool
2. Activez le mode MEV dans les paramètres
3. Réduisez les vérifications de sécurité non essentielles
4. Utilisez un serveur avec une latence plus faible (AWS, GCP proches des nœuds blockchain)

## Erreurs d'API

### Clé API Invalide

**Symptôme** : Erreurs "Invalid API key" ou "Unauthorized"

**Solution** :
1. Vérifiez que votre clé API est correctement copiée dans le fichier `.env`
2. Régénérez une nouvelle clé API si nécessaire
3. Vérifiez les restrictions d'IP pour votre clé API

### Limites API Dépassées

**Symptôme** : Erreurs "Rate limit exceeded" ou "Too many requests"

**Solution** :
1. Réduisez la fréquence des requêtes
2. Passez à un plan API supérieur
3. Implémentez un système de mise en cache pour réduire les appels API

## Logs et Diagnostics

### Activer les Logs Détaillés

Pour obtenir plus d'informations sur les erreurs :

```python
# Dans votre code
from gbpbot.advanced_logging import configure_logging
config = configure_logging()
config.log_level = "DEBUG"
config.setup()
```

Ou directement dans la configuration :
```yaml
logging:
  level: DEBUG
  file: gbpbot_debug.log
  console: true
```

### Extraction des Logs pour Support

Pour partager vos logs avec le support :

```bash
# Compresser tous les logs récents
cd logs
zip -r gbpbot_logs_$(date +%Y%m%d).zip *.log

# Ou sous Windows
Compress-Archive -Path .\logs\*.log -DestinationPath .\logs\gbpbot_logs_$(Get-Date -Format "yyyyMMdd").zip
```

### Rapport de Diagnostic

Exécutez l'outil de diagnostic intégré :

```bash
python -m gbpbot.tools.diagnostic
```

Cela générera un rapport détaillé sur votre système, la configuration du bot, et les éventuels problèmes.

## Résolution Avancée

### Mode de Récupération

Si le bot ne démarre pas du tout :

```bash
# Lancer en mode récupération (sans modules optionnels)
python gbpbot_cli.py --recovery-mode

# Ou avec le script bridge
python gbpbot_cli_bridge.py
# Puis sélectionner "Lancer le bot en mode récupération"
```

### Nettoyage Complet

Si vous souhaitez repartir à zéro :

```bash
# Sauvegarder la configuration
cp .env .env.backup

# Nettoyer l'installation
pip uninstall -y gbpbot
rm -rf build dist *.egg-info

# Réinstaller proprement
pip install -e .
```

### Diagnostiquer les Stubs Manquants

En cas d'erreurs d'importation circulaire :

```bash
# Vérifier si les stubs sont correctement créés
python -c "import sys; print('stubs' in sys.path)"
python -c "from stubs.compatibility_stub import HardwareOptimizerCompat; print('Stub OK')"

# Créer manuellement les stubs si nécessaire
mkdir -p stubs
# Puis copiez les fichiers stub nécessaires depuis la documentation
```

## Mise à Jour de Sécurité - Mars 2025

Des vulnérabilités de sécurité ont été identifiées et corrigées dans plusieurs dépendances utilisées par GBPBot. Il est fortement recommandé de mettre à jour votre installation pour prévenir les risques d'exploitation de ces failles.

### Vulnérabilités Corrigées

#### 1. cryptography < 43.0.1
- **Vulnérabilité :** Attaque de timing oracle de type Bleichenbacher qui peut compromettre les échanges de clés RSA dans les connexions TLS
- **Impact potentiel :** Décryptage de communications sensibles
- **Version corrigée :** ≥ 43.0.1
- **Instruction de mise à jour :** `pip install "cryptography>=43.0.1"`

#### 2. aiohttp < 3.9.4
- **Vulnérabilité :** Boucle infinie lors du traitement de requêtes POST multipart/form-data spécialement conçues
- **Impact potentiel :** Déni de service (DoS)
- **Version corrigée :** ≥ 3.10.11
- **Instruction de mise à jour :** `pip install "aiohttp>=3.10.11"`

#### 3. gunicorn < 22.0.0
- **Vulnérabilité :** Validation incorrecte des en-têtes Transfer-Encoding permettant le HTTP Request Smuggling (HRS)
- **Impact potentiel :** Contournement de restrictions d'accès
- **Version corrigée :** ≥ 22.0.0
- **Instruction de mise à jour :** `pip install "gunicorn>=22.0.0"`

### Comment Mettre à Jour

Exécutez la commande suivante pour mettre à jour toutes les dépendances vulnérables en une seule fois :

```bash
pip install -U "cryptography>=43.0.1" "aiohttp>=3.10.11" "gunicorn>=22.0.0"
```

Ou mettez à jour l'ensemble des dépendances en utilisant le fichier requirements.txt mis à jour :

```bash
pip install -U -r requirements.txt
```

### Vérification de la Mise à Jour

Pour vérifier que les mises à jour ont été correctement appliquées :

```bash
pip list | grep -E 'cryptography|aiohttp|gunicorn'
```

Le résultat devrait montrer des versions égales ou supérieures à celles recommandées.

### Remarques Importantes

- Ces mises à jour peuvent potentiellement introduire des changements dans l'API des bibliothèques, surtout pour aiohttp. En cas de problèmes après la mise à jour, consultez la section [Résolution Avancée](#résolution-avancée).
- Si vous utilisez des environnements de développement et de production séparés, assurez-vous de mettre à jour les deux.
- Ces mises à jour sont critiques pour la sécurité de votre système et devraient être appliquées dès que possible.

---

Si vous rencontrez un problème qui n'est pas couvert dans ce guide, veuillez :

1. Consulter la [documentation complète](./README.md)
2. Consulter les [issues GitHub](https://github.com/username/gbpbot/issues)
3. Créer une nouvelle issue avec les logs et les détails du problème

**N'oubliez pas** : En cas de problème critique avec des fonds en jeu, arrêtez immédiatement le bot avec `Ctrl+C` pour éviter toute perte. 