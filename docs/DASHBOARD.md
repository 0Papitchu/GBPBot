# Documentation du Dashboard GBPBot

## Table des matières

1. [Introduction](#introduction)
2. [Installation et lancement](#installation-et-lancement)
3. [Architecture technique](#architecture-technique)
4. [Interface utilisateur](#interface-utilisateur)
5. [Fonctionnalités](#fonctionnalités)
6. [API REST](#api-rest)
7. [WebSockets](#websockets)
8. [Personnalisation](#personnalisation)
9. [Mode Simulation](#mode-simulation)
10. [Dépannage](#dépannage)
11. [FAQ](#faq)

## Introduction

Le Dashboard GBPBot est une interface web moderne et intuitive qui permet de contrôler, surveiller et configurer le GBPBot. Il offre une visualisation en temps réel des performances, des opportunités détectées et des transactions effectuées, ainsi qu'une interface graphique pour la configuration et la gestion des stratégies de trading.

### Principales caractéristiques

- **Tableau de bord en temps réel** : Visualisation des performances, soldes, trades récents et opportunités détectées
- **Gestion des stratégies** : Interface pour démarrer, arrêter et configurer les stratégies de trading
- **Module de backtesting** : Configuration graphique et visualisation des résultats de backtesting
- **Mises à jour en temps réel** : Communication bidirectionnelle via WebSockets
- **Interface responsive** : Adaptée aux différents appareils (desktop, tablette, mobile)
- **Graphiques interactifs** : Visualisation avancée des performances et des données de marché
- **API REST complète** : Contrôle programmatique de toutes les fonctionnalités du bot
- **Mode Simulation** : Génération de données de test pour la démonstration et le développement

## Installation et lancement

### Prérequis

- Python 3.8 ou supérieur
- Navigateur web moderne (Chrome, Firefox, Edge, Safari)
- Connexion Internet (pour les CDN et les API externes)

### Installation

Le dashboard est inclus dans l'installation standard de GBPBot. Pour l'installer séparément ou mettre à jour ses dépendances :

```bash
# Installer les dépendances requises
pip install -r requirements.txt
```

### Lancement

#### Windows

Utilisez le script `run_dashboard.bat` fourni :

```bash
run_dashboard.bat
```

Ou lancez manuellement :

```bash
python -m gbpbot.dashboard.run_dashboard --host 0.0.0.0 --port 8000
```

#### Linux/macOS

Utilisez le script `run_dashboard.sh` fourni :

```bash
chmod +x run_dashboard.sh
./run_dashboard.sh
```

Ou lancez manuellement :

```bash
python -m gbpbot.dashboard.run_dashboard --host 0.0.0.0 --port 8000
```

### Options de lancement

Le script `run_dashboard.py` accepte plusieurs options :

- `--host` : Adresse d'écoute du serveur (défaut : 0.0.0.0)
- `--port` : Port d'écoute du serveur (défaut : 8000)
- `--simulate` : Active la génération de métriques simulées pour les tests et démonstrations
- `--log-level` : Niveau de logs (DEBUG, INFO, WARNING, ERROR, CRITICAL)

Exemple :

```bash
python -m gbpbot.dashboard.run_dashboard --host 127.0.0.1 --port 9000 --simulate --log-level DEBUG
```

## Architecture technique

Le dashboard GBPBot est construit sur une architecture moderne et modulaire :

### Backend

- **FastAPI** : Framework web asynchrone haute performance
- **Uvicorn** : Serveur ASGI pour l'exécution de l'application FastAPI
- **WebSockets** : Communication bidirectionnelle en temps réel
- **Pydantic** : Validation des données et sérialisation

### Frontend

- **Vue.js** : Framework JavaScript progressif pour l'interface utilisateur
- **Chart.js** : Bibliothèque de graphiques interactifs
- **Bootstrap** : Framework CSS pour le design responsive
- **Axios** : Client HTTP pour les requêtes API

### Structure des fichiers

```
gbpbot/dashboard/
├── run_dashboard.py       # Script de lancement
├── server.py              # Serveur FastAPI principal
├── api.py                 # API REST complète
├── static/                # Fichiers statiques
│   ├── css/               # Styles CSS
│   │   └── style.css      # Styles personnalisés
│   ├── js/                # Scripts JavaScript
│   │   └── app.js         # Application Vue.js
│   └── index.html         # Page HTML principale
└── __init__.py            # Initialisation du module
```

## Interface utilisateur

L'interface utilisateur du dashboard est organisée en plusieurs sections accessibles via le menu de navigation :

### Dashboard principal

Le tableau de bord principal affiche une vue d'ensemble des performances et de l'état du système :

- **Solde total** : Valeur totale des actifs avec variation quotidienne
- **Trades aujourd'hui** : Nombre de trades effectués avec taux de réussite
- **Opportunités** : Nombre d'opportunités détectées et exécutées
- **Stratégies actives** : Nombre de stratégies en cours d'exécution
- **Graphique de performance** : Évolution du solde total sur différentes périodes
- **Répartition des actifs** : Visualisation de la répartition du portefeuille
- **Dernières opportunités** : Liste des opportunités récemment détectées
- **Derniers trades** : Liste des transactions récentes

### Stratégies

La section Stratégies permet de gérer les stratégies de trading :

- **Liste des stratégies disponibles** : Affichage des stratégies configurées
- **Configuration des stratégies** : Interface pour modifier les paramètres
- **Démarrage/Arrêt** : Contrôles pour activer ou désactiver les stratégies
- **Statut en temps réel** : Visualisation de l'état des stratégies actives

### Backtesting

La section Backtesting permet de tester et d'optimiser les stratégies :

- **Configuration du backtest** : Sélection de la stratégie, des symboles, de la période, etc.
- **Résultats du backtest** : Affichage des métriques de performance (rendement, Sharpe, drawdown, etc.)
- **Graphique d'équité** : Visualisation de l'évolution du capital
- **Historique des backtests** : Liste des backtests précédents avec leurs résultats

### Trades

La section Trades affiche l'historique détaillé des transactions :

- **Liste des trades** : Transactions avec détails (symbole, prix, montant, etc.)
- **Filtres et recherche** : Outils pour filtrer les transactions
- **Statistiques** : Métriques de performance par symbole, stratégie, etc.
- **Exportation** : Fonctionnalités pour exporter les données

### Configuration

La section Configuration permet de personnaliser le système :

- **Paramètres généraux** : Configuration globale du bot
- **Gestion des API keys** : Interface pour gérer les clés API des exchanges
- **Paramètres de sécurité** : Configuration des mécanismes de protection
- **Préférences utilisateur** : Personnalisation de l'interface

### Logs

La section Logs affiche les journaux du système :

- **Logs en temps réel** : Affichage des événements système
- **Filtres par niveau** : Filtrage par niveau de log (INFO, WARNING, ERROR, etc.)
- **Recherche** : Fonctionnalité de recherche dans les logs
- **Exportation** : Possibilité d'exporter les logs

### AI Assistant

La section IA offre un accès à l'assistant IA intégré au GBPBot :

- **Analyse de tokens** : Évaluation détaillée d'un token spécifique
- **Analyse de marché** : Aperçu des conditions de marché actuelles
- **Recommandations** : Suggestions basées sur les analyses IA
- **Historique des analyses** : Archive des analyses précédentes

## Fonctionnalités

### Mises à jour en temps réel

Le dashboard utilise les WebSockets pour fournir des mises à jour en temps réel sans nécessiter de rafraîchissement de la page :

- **Prix des actifs** : Mise à jour en temps réel des prix
- **Opportunités détectées** : Notification immédiate des nouvelles opportunités
- **Statut des stratégies** : Mise à jour de l'état des stratégies actives
- **Résultats de backtest** : Affichage des résultats dès qu'ils sont disponibles

### Visualisations interactives

Le dashboard offre des visualisations avancées pour analyser les performances :

- **Graphiques d'équité** : Évolution du capital dans le temps
- **Graphiques de performance** : Rendements quotidiens, hebdomadaires, mensuels
- **Diagrammes de répartition** : Visualisation de la composition du portefeuille
- **Heatmaps** : Visualisation des corrélations et des performances

### Gestion des stratégies

L'interface permet une gestion complète des stratégies de trading :

- **Configuration intuitive** : Interface graphique pour ajuster les paramètres
- **Validation des paramètres** : Vérification de la validité des configurations
- **Préréglages** : Sauvegarde et chargement de configurations prédéfinies
- **Monitoring en temps réel** : Suivi des performances des stratégies actives

### Backtesting avancé

Le module de backtesting offre des fonctionnalités avancées :

- **Configuration graphique** : Interface intuitive pour configurer les backtests
- **Analyse de performance** : Calcul de métriques avancées (Sharpe, Sortino, drawdown, etc.)
- **Comparaison de stratégies** : Outils pour comparer différentes stratégies
- **Optimisation de paramètres** : Interface pour l'optimisation automatique des paramètres

### Intégration IA

L'intégration avec les modèles d'IA du GBPBot offre des capacités d'analyse avancées :

- **Analyse de contrats** : Détection des risques et fonctions malveillantes
- **Prédiction de volatilité** : Estimation des mouvements de prix à court terme
- **Scoring de tokens** : Évaluation du potentiel des nouveaux tokens
- **Analyse de sentiment** : Intégration des données sociales et des tendances du marché

## API REST

Le dashboard expose une API REST complète pour l'intégration avec d'autres systèmes :

### Points d'entrée principaux

- `/api/status` : État actuel du bot
- `/api/config` : Configuration du système
- `/api/strategies` : Gestion des stratégies
- `/api/backtest` : Exécution et résultats de backtests
- `/api/wallets` : Informations sur les wallets configurés
- `/api/metrics` : Métriques de performance
- `/api/logs` : Journaux système
- `/api/ai/analyze` : Analyse IA de tokens spécifiques

### Exemple d'utilisation

```javascript
// Récupérer l'état du bot
fetch('/api/status')
  .then(response => response.json())
  .then(data => console.log(data));

// Démarrer une stratégie
fetch('/api/strategies/arbitrage/start', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    name: "arbitrage",
    enabled: true,
    params: {
      min_spread_pct: 0.5,
      max_trade_size: 100,
      target_exchanges: ["binance", "kucoin"]
    }
  })
})
  .then(response => response.json())
  .then(data => console.log(data));
```

## WebSockets

Le dashboard utilise les WebSockets pour la communication en temps réel :

### Connexion

```javascript
const ws = new WebSocket(`ws://${window.location.host}/ws`);

ws.onopen = () => {
  console.log('Connexion WebSocket établie');
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('Message reçu:', message);
};
```

### Types de messages

Les messages WebSocket ont une structure standard :

```json
{
  "event": "metric_update",
  "timestamp": "2023-06-01T12:34:56.789Z",
  "data": {
    // Données spécifiques à l'événement
  }
}
```

Les types d'événements incluent :
- `connected` : Confirmation de connexion réussie
- `metric_update` : Mise à jour des métriques de performance
- `strategy_update` : Changement d'état d'une stratégie
- `trade_executed` : Transaction effectuée
- `opportunity_detected` : Opportunité de trading détectée
- `backtest_update` : Mise à jour des résultats de backtesting

## Personnalisation

Le dashboard peut être personnalisé de plusieurs façons :

### Thèmes et styles

Le fichier `static/css/style.css` contient les styles personnalisés du dashboard. Vous pouvez le modifier pour adapter l'apparence à vos préférences.

### Personnalisation avancée de l'interface utilisateur

Une fois que le GBPBot sera 100% actif et opérationnel, il sera possible de styliser davantage l'interface utilisateur pour suivre les tendances de design modernes comme celles d'Apple, Samsung ou Google Material Design. Voici quelques possibilités :

- **Refonte complète du thème** : Création de thèmes personnalisés avec des palettes de couleurs cohérentes et des transitions fluides
- **Animations avancées** : Ajout d'animations et de transitions pour améliorer l'expérience utilisateur
- **Mode sombre/clair** : Implémentation d'un sélecteur de thème avec support automatique des préférences système
- **Composants personnalisés** : Développement de composants UI spécifiques pour le trading (widgets de prix, graphiques avancés, etc.)
- **Responsive design avancé** : Optimisation pour tous les appareils avec des layouts spécifiques pour mobile, tablette et desktop
- **Glassmorphism/Neumorphism** : Application des tendances de design modernes comme le glassmorphism ou le neumorphism
- **Micro-interactions** : Ajout de micro-interactions pour améliorer l'engagement et le feedback utilisateur
- **Personnalisation par l'utilisateur** : Permettre à l'utilisateur de personnaliser son interface (disposition des widgets, couleurs, etc.)

Ces améliorations peuvent être implémentées sans modifier la structure fondamentale de l'application, en se concentrant uniquement sur les fichiers CSS, HTML et JavaScript de l'interface.

### Ajout de fonctionnalités

Pour ajouter de nouvelles fonctionnalités au dashboard :

1. **Backend** : Ajoutez de nouveaux points d'entrée API dans `api.py`
2. **Frontend** : Modifiez `static/js/app.js` pour ajouter des composants Vue.js
3. **Interface** : Mettez à jour `static/index.html` pour ajouter de nouveaux éléments d'interface

## Mode Simulation

Le dashboard inclut un mode simulation qui génère des données de test pour faciliter le développement et les démonstrations. Ce mode est activé avec l'option `--simulate` lors du lancement.

### Données simulées

Le mode simulation génère des données réalistes pour :

- **Balance et portfolio** : Évolution du capital avec variations aléatoires
- **Trades** : Transactions avec win rates réalistes
- **Opportunités** : Détection et exécution d'opportunités de trading
- **Stratégies** : Statut et performances des différentes stratégies

### Utilisation pour le développement

Le mode simulation est particulièrement utile pour :

1. **Développement frontend** : Tester les composants d'interface sans système backend complet
2. **Démos et présentations** : Montrer les fonctionnalités du GBPBot sans risquer de vrais fonds
3. **Tests d'interface** : Valider les visualisations et les mises à jour en temps réel

Pour activer le mode simulation :

```bash
python -m gbpbot.dashboard.run_dashboard --simulate
```

Les données simulées sont régulièrement mises à jour pour créer une expérience dynamique et réaliste.

## Dépannage

### Problèmes courants

#### Le serveur ne démarre pas

- Vérifiez que toutes les dépendances sont installées : `pip install -r requirements.txt`
- Vérifiez qu'aucun autre service n'utilise le port spécifié
- Vérifiez les logs pour identifier l'erreur spécifique

#### L'interface ne se charge pas correctement

- Vérifiez que les fichiers statiques sont correctement servis
- Videz le cache de votre navigateur
- Vérifiez la console du navigateur pour les erreurs JavaScript

#### Les mises à jour en temps réel ne fonctionnent pas

- Vérifiez que la connexion WebSocket est établie
- Vérifiez que votre navigateur supporte les WebSockets
- Vérifiez les pare-feu ou proxys qui pourraient bloquer les WebSockets

### Logs

Les logs du dashboard sont disponibles dans le fichier `dashboard.log` et dans la console lors de l'exécution. Le niveau de détail peut être ajusté avec l'option `--log-level`.

## FAQ

### Questions générales

**Q: Le dashboard fonctionne-t-il sans le bot principal ?**

R: Oui, le dashboard peut être lancé indépendamment, mais certaines fonctionnalités nécessitent que le bot principal soit en cours d'exécution. Le mode simulation (`--simulate`) permet d'utiliser le dashboard avec des données fictives.

**Q: Puis-je accéder au dashboard à distance ?**

R: Oui, en lançant le serveur avec `--host 0.0.0.0`, le dashboard sera accessible depuis d'autres appareils sur le réseau. Pour un accès sécurisé à distance, il est recommandé d'utiliser un proxy HTTPS comme Nginx ou Caddy.

**Q: Le dashboard est-il sécurisé ?**

R: Le dashboard de base n'inclut pas d'authentification. Pour une utilisation en production, il est recommandé d'ajouter une couche d'authentification et de chiffrement HTTPS.

**Q: Comment intégrer le dashboard avec d'autres outils ?**

R: Le dashboard expose une API REST complète que vous pouvez utiliser pour l'intégrer avec d'autres outils. Consultez la section [API REST](#api-rest) pour plus d'informations.

### Questions techniques

**Q: Comment ajouter une nouvelle page au dashboard ?**

R: Ajoutez une nouvelle section dans `static/index.html`, créez les composants Vue.js correspondants dans `static/js/app.js`, et ajoutez les points d'entrée API nécessaires dans `api.py`.

**Q: Comment personnaliser les graphiques ?**

R: Les graphiques sont créés avec Chart.js. Vous pouvez modifier les options de configuration dans les méthodes `updateXXXChart()` dans `static/js/app.js`.

**Q: Comment optimiser les performances du dashboard ?**

R: Pour améliorer les performances, vous pouvez :
- Limiter la quantité de données chargées à la fois
- Utiliser la pagination pour les grandes listes
- Optimiser les requêtes API pour ne récupérer que les données nécessaires
- Mettre en cache les données qui ne changent pas fréquemment
- Ajuster la fréquence des mises à jour WebSocket (par défaut 5 secondes)

**Q: Comment monitorer les performances du dashboard lui-même ?**

R: Le dashboard enregistre des métriques de performance dans les logs. Vous pouvez également utiliser des outils comme Prometheus et Grafana pour surveiller les performances du serveur. 