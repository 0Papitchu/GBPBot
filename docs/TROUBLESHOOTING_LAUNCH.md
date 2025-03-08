# Guide de Dépannage pour le Lancement de GBPBot

Ce document couvre les problèmes courants rencontrés lors du lancement de GBPBot et les solutions implémentées pour les résoudre.

## Problèmes Courants de Lancement

Lors du développement et du déploiement de GBPBot, plusieurs problèmes peuvent survenir, particulièrement liés à l'environnement Python et aux dépendances.

### 1. Problèmes d'Importation de Modules

```
Erreur: Module 'gbpbot.cli_interface' non trouvé.
```

Ce problème survient lorsque Python ne peut pas localiser le package `gbpbot` ou ses sous-modules. Causes possibles:
- Le répertoire du projet n'est pas dans le PYTHONPATH
- Le package n'est pas installé en mode développement
- Structure de fichiers incorrecte

### 2. Dépendances Manquantes

```
Impossible d'importer le package anchorpy: No module named 'anchorpy'
```

Ce problème survient lorsque certaines dépendances requises ne sont pas installées. Les dépendances critiques incluent:
- `anchorpy` - pour l'interaction avec les programmes Solana Anchor
- `web3` - pour l'interaction avec les blockchains Ethereum/Avalanche
- `asyncio` - pour la gestion asynchrone

### 3. Erreurs de Boucle d'Événements Asyncio

```
RuntimeError: no running event loop
```

Ce problème survient particulièrement sur Windows lorsque le code asynchrone n'est pas correctement configuré:
- Absence d'une boucle d'événements asyncio en cours d'exécution
- Configuration incorrecte de la politique d'événements sur Windows

### 4. Erreurs de Compilation

```
Microsoft Visual C++ 14.0 or greater is required
```

Certaines dépendances comme `zstandard` nécessitent une compilation et peuvent échouer si l'environnement de développement approprié n'est pas installé.

## Script Pont `gbpbot_cli_bridge.py`

Pour résoudre ces problèmes sans modifier le code source principal, nous avons créé un script pont (`gbpbot_cli_bridge.py`) qui:

1. **Configure correctement l'environnement Python** - Ajoute le répertoire du projet au PYTHONPATH
2. **Installe les dépendances critiques** - Installe les packages essentiels de manière flexible
3. **Génère un lanceur asyncio** - Crée un script temporaire qui configure correctement la boucle d'événements
4. **Crée des stubs pour les fonctions manquantes** - Fournit des implémentations temporaires pour les fonctions manquantes

### Utilisation du Script Pont

Pour utiliser ce script, suivez ces étapes:

1. Lancez le script depuis le répertoire principal du projet:
   ```bash
   python gbpbot_cli_bridge.py
   ```

2. Depuis le menu, sélectionnez:
   - **Option 1**: Pour installer les dépendances essentielles
   - **Option 2**: Pour configurer le fichier .env si nécessaire
   - **Option 3**: Pour lancer le bot

3. Si vous choisissez l'option 1, vous aurez plusieurs niveaux d'installation:
   - **Installation minimale**: Installe uniquement les packages essentiels
   - **Installation standard**: Installe la plupart des packages nécessaires
   - **Installation du package gbpbot**: Installe le package directement depuis le répertoire local

4. Après l'installation des dépendances, utilisez l'option 3 pour lancer le bot.

## Dépannage Avancé

Si vous rencontrez toujours des problèmes après avoir utilisé le script pont:

1. **Vérifiez l'environnement virtuel**
   - Assurez-vous d'utiliser un environnement virtuel Python propre et isolé
   - Python 3.9+ est recommandé pour éviter les conflits de dépendances

2. **Installez les outils de développement C++**
   - Pour Windows: Installez "Microsoft C++ Build Tools"
   - Pour Linux: Installez `build-essential` et `python3-dev`

3. **Vérifiez la structure du projet**
   - Le fichier `cli_interface.py` doit être présent dans le répertoire `gbpbot/`
   - Le fichier `__init__.py` doit être présent dans chaque répertoire Python

4. **Utilisez une version spécifique de Python**
   - Python 3.9 ou 3.10 est recommandé pour GBPBot
   - Évitez d'utiliser Python 3.11+ qui peut avoir des incompatibilités avec certaines dépendances

## Architecture des Scripts de Lancement

La hiérarchie des scripts de lancement:

```
lancer_gbpbot.bat -> gbpbot_cli_bridge.py -> gbpbot_async_launcher.py -> gbpbot/cli.py
```

Cette approche en plusieurs couches permet:
1. Une expérience utilisateur simple avec le script batch
2. Une configuration robuste de l'environnement avec le script pont
3. Une gestion correcte d'asyncio avec le lanceur asynchrone
4. L'utilisation du code original de GBPBot sans modification majeure 