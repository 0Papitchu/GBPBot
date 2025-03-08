# Guide d'Utilisation de l'Interface CLI de GBPBot

## Introduction

L'interface en ligne de commande (CLI) de GBPBot vous permet de contrôler toutes les fonctionnalités du bot directement depuis votre terminal. Ce guide vous explique comment naviguer dans les menus et utiliser les différentes commandes disponibles.

## Structure de l'Interface CLI

L'interface CLI est organisée en plusieurs menus et sous-menus:

```
Menu Principal
├── Démarrer le Bot
│   ├── Arbitrage entre les DEX
│   ├── Sniping de Token
│   ├── Lancer automatiquement le bot
│   ├── AI Assistant
│   └── Backtesting et Simulation
├── Configurer les paramètres
├── Afficher la configuration actuelle
├── Statistiques et Logs
└── Quitter
```

## Démarrage du CLI

Pour lancer l'interface CLI, exécutez la commande suivante depuis le répertoire principal de GBPBot:

```bash
# Sur Windows
python run_gbpbot.py --mode cli

# Sur Linux/Mac
python3 run_gbpbot.py --mode cli
```

Ou utilisez les scripts de lancement:

```bash
# Sur Windows
start_gbpbot.bat

# Sur Linux/Mac
./start_gbpbot.sh
```

## Méthode Alternative de Lancement (Dépannage)

Si vous rencontrez des problèmes avec les méthodes de lancement standard, utilisez le script pont dédié au dépannage :

```bash
# Sur Windows
lancer_gbpbot_depannage.bat
# ou
python gbpbot_cli_bridge.py

# Sur Linux/Mac
python3 gbpbot_cli_bridge.py
```

### Avantages du Script Pont

Le script pont offre plusieurs avantages pour résoudre les problèmes de lancement :

- Résout automatiquement les problèmes d'importation de modules
- Installe les dépendances manquantes avec différents niveaux d'installation
- Contourne les erreurs de boucle asyncio courantes sur Windows
- Fournit un menu simplifié pour configurer le fichier .env
- Offre des diagnostics en cas d'échec du lancement

### Problèmes courants résolus

Le script pont résout automatiquement plusieurs problèmes courants :

- `RuntimeError: no running event loop` - En configurant correctement asyncio
- `Module not found` - En ajustant le PYTHONPATH et en créant des stubs
- Dépendances manquantes - En installant les packages essentiels
- Erreurs d'environnement - En configurant correctement les variables d'environnement

Pour plus d'informations sur la résolution des problèmes, consultez [TROUBLESHOOTING_LAUNCH.md](TROUBLESHOOTING_LAUNCH.md).

## Navigation dans les Menus

La navigation dans les menus est simple et intuitive:

1. Chaque option de menu est numérotée
2. Entrez le numéro correspondant à l'option souhaitée
3. Suivez les instructions à l'écran
4. Pour revenir au menu précédent, sélectionnez l'option "Retour"

## Modules Disponibles

### Module d'Arbitrage entre DEX

Ce module vous permet de détecter et d'exploiter les écarts de prix entre différents DEX (Exchanges Décentralisés) et CEX (Exchanges Centralisés).

Options disponibles:
- Arbitrage inter-DEX (entre différents DEX)
- Arbitrage CEX-DEX (entre exchanges centralisés et décentralisés)
- Configuration des paramètres d'arbitrage
- Visualisation des opportunités récentes

### Module de Sniping de Token

Ce module vous permet de détecter et d'acheter rapidement les nouveaux tokens avec un potentiel de croissance.

Options disponibles:
- Sniping de nouveaux tokens
- Configuration des paramètres de sniping
- Surveillance des tokens
- Visualisation des résultats de sniping

### Mode Automatique

Ce mode permet au bot de fonctionner de manière autonome, en choisissant automatiquement les meilleures stratégies en fonction des conditions du marché.

### AI Assistant

Ce module vous donne accès à un assistant IA pour analyser le marché, les tokens et les contrats intelligents.

Options disponibles:
- Analyse du sentiment du marché
- Évaluation de tokens spécifiques
- Analyse de contrats intelligents
- Génération de rapports de marché

### Backtesting et Simulation

Ce module vous permet de tester vos stratégies sur des données historiques avant de les déployer en environnement réel.

Options disponibles:
- Configuration de tests
- Chargement de données historiques
- Exécution de simulations
- Analyse des résultats

## Exemples d'Utilisation

### Lancer un Arbitrage Inter-DEX

1. Lancez le CLI (`python run_gbpbot.py --mode cli`)
2. Sélectionnez "1" pour "Démarrer le Bot"
3. Sélectionnez "1" pour "Arbitrage entre les DEX"
4. Sélectionnez "1" pour "Démarrer l'arbitrage inter-DEX"
5. Suivez les instructions pour configurer les paramètres d'arbitrage

### Configurer les Paramètres de Sniping

1. Lancez le CLI (`python run_gbpbot.py --mode cli`)
2. Sélectionnez "1" pour "Démarrer le Bot"
3. Sélectionnez "2" pour "Sniping de Token"
4. Sélectionnez "3" pour "Configurer les paramètres de sniping"
5. Suivez les instructions pour configurer les paramètres

## Astuces et Bonnes Pratiques

- Commencez par configurer vos paramètres avant de lancer une stratégie
- Utilisez le module de backtesting pour tester vos stratégies avant de les utiliser en environnement réel
- Surveillez régulièrement les logs pour détecter d'éventuels problèmes
- Arrêtez proprement les modules en utilisant l'option "Arrêt de Module" pour éviter les problèmes

## Résolution des Problèmes Courants

Si vous rencontrez des problèmes avec l'interface CLI:

1. Vérifiez que Python est correctement installé
2. Assurez-vous d'avoir installé toutes les dépendances (`pip install -r requirements.txt`)
3. Vérifiez les logs pour identifier d'éventuelles erreurs
4. Redémarrez le bot en cas de comportement inattendu

## Notes sur la Compatibilité

L'interface CLI est compatible avec:
- Windows (utilisation de cls pour effacer l'écran)
- Linux/Mac (utilisation de clear pour effacer l'écran)
- Terminaux supportant les séquences ANSI pour les couleurs 