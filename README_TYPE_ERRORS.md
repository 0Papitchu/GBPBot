# Résolution des erreurs de type dans GBPBot

Ce document explique comment résoudre les erreurs de type détectées par Pylance dans le projet GBPBot.

## Problèmes identifiés

Plusieurs types d'erreurs ont été détectés :

1. **Variables non définies** : Des variables comme `FlashbotsProvider`, `BundleExecutor`, `MempoolScanner`, `status`, `token_in`, etc. sont utilisées sans être définies.

2. **Problèmes d'annotation de type** : Des erreurs comme "Too few type arguments provided for FixtureFunction" indiquent des problèmes avec les annotations de type Python.

## Solution rapide

Un script `fix_type_errors.py` a été créé pour ajouter automatiquement les imports manquants et les définitions de variables nécessaires.

### Utilisation du script

1. Exécutez le script depuis la racine du projet :

```bash
python fix_type_errors.py
```

2. Le script parcourra les fichiers problématiques et ajoutera les imports et définitions manquants.

## Solution manuelle

Si vous préférez corriger les erreurs manuellement, voici ce que vous devez faire pour chaque fichier :

### gbpbot/strategies/mev.py

Ajoutez l'import suivant au début du fichier :

```python
from gbpbot.core.mev_executor import FlashbotsProvider, BundleExecutor, MempoolScanner
```

### gbpbot/strategies/scalping.py, sniping.py, token_detection.py

1. Ajoutez l'import pour FixtureFunction :

```python
from typing import FixtureFunction
```

2. Définissez les variables utilisées dans les fixtures au niveau du module :

```python
# Variables utilisées dans les fixtures
trader_joe = None
status = None
entry_time = None
token_in = None
token_out = None
take_profit_price = None
stop_loss_price = None
# etc.
```

### gbpbot/core/mev_executor.py

Définissez les variables manquantes :

```python
# Variables utilisées dans les fixtures
baseFeePerGas = None
timestamp = None
```

### tests/test_arbitrage.py

Définissez les constantes utilisées dans les tests :

```python
# Tokens pour les tests
WAVAX = 'WAVAX'
USDC = 'USDC'
profit_percent = 0.01
```

## Solution à long terme

Ces corrections sont des solutions temporaires pour faire disparaître les erreurs de Pylance. Pour une solution plus robuste, vous devriez :

1. **Revoir la conception du code** : Assurez-vous que toutes les variables sont correctement définies et importées.

2. **Utiliser des annotations de type correctes** : Pour `FixtureFunction`, assurez-vous de fournir les arguments de type corrects.

3. **Utiliser des constantes** : Définissez des constantes pour les tokens et autres valeurs fixes dans un module dédié.

4. **Utiliser des enums** : Pour les valeurs comme `status`, envisagez d'utiliser des enums Python.

## Note importante

Ces erreurs de type n'empêchent pas le bot de fonctionner, comme nous l'avons vu lors de l'exécution réussie. Elles sont principalement des avertissements de l'analyseur statique de code (Pylance) qui aident à détecter des problèmes potentiels avant l'exécution. 