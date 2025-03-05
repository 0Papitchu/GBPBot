# Guide de Mise en Place du Monitoring en Temps Réel pour GBPBot

Ce document détaille la configuration et l'utilisation du système de monitoring en temps réel pour GBPBot, permettant de surveiller les performances, détecter les anomalies et réagir rapidement aux incidents.

## Table des matières

1. [Vue d'ensemble du système de monitoring](#vue-densemble-du-système-de-monitoring)
2. [Configuration du monitoring](#configuration-du-monitoring)
3. [Démarrage du dashboard](#démarrage-du-dashboard)
4. [Utilisation du dashboard](#utilisation-du-dashboard)
5. [Alertes et notifications](#alertes-et-notifications)
6. [Analyse des performances](#analyse-des-performances)
7. [Intégration avec les procédures de rollback](#intégration-avec-les-procédures-de-rollback)
8. [Personnalisation du dashboard](#personnalisation-du-dashboard)

## Vue d'ensemble du système de monitoring

Le système de monitoring de GBPBot est composé de plusieurs composants :

1. **BotMonitor** : Classe de base pour le monitoring, collecte les métriques essentielles
2. **AdvancedMonitor** : Monitoring avancé avec alertes et notifications
3. **Dashboard Web** : Interface utilisateur en temps réel pour visualiser les métriques
4. **Système d'alertes** : Détection et notification des anomalies
5. **Outils d'analyse** : Scripts pour analyser les logs et les performances

### Architecture du système

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│    GBPBot       │────▶│   BotMonitor    │────▶│   Dashboard     │
│                 │     │ AdvancedMonitor │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │                        │
                               ▼                        ▼
                        ┌─────────────────┐     ┌─────────────────┐
                        │                 │     │                 │
                        │ Système d'alerte│     │  Stockage des   │
                        │                 │     │   métriques     │
                        └─────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌─────────────────┐
                        │                 │
                        │ Notifications   │
                        │                 │
                        └─────────────────┘
```

## Configuration du monitoring

### Configuration dans le fichier YAML

Le monitoring est configurable via le fichier de configuration principal :

```yaml
monitoring:
  # Intervalle de mise à jour des métriques (en secondes)
  update_interval: 5
  
  # Configuration du dashboard
  dashboard:
    enabled: true
    port: 8080
    refresh_interval: 2
    
  # Seuils d'alerte
  alert_thresholds:
    low_balance: 0.1          # Alerte si le solde < 10% du capital initial
    high_gas: 300             # Alerte si gas > 300 Gwei
    low_profit: 0.001         # Alerte si profit < 0.1%
    price_deviation: 0.05     # Alerte si écart de prix > 5%
    error_rate: 0.2           # Alerte si taux d'erreur > 20%
    consecutive_errors: 3     # Alerte après 3 erreurs consécutives
    
  # Configuration des notifications
  notifications:
    email:
      enabled: true
      recipients: ["admin@example.com"]
      
    discord:
      enabled: true
      webhook_url: "https://discord.com/api/webhooks/..."
      
    telegram:
      enabled: true
      bot_token: "YOUR_BOT_TOKEN"
      chat_id: "YOUR_CHAT_ID"
```

### Validation de la configuration

Utilisez le script `validate_config.py` pour vérifier que la configuration du monitoring est valide :

```bash
python scripts/validate_config.py --config=config/active_config.yaml --verbose
```

## Démarrage du dashboard

### Démarrage intégré avec le bot

Le moyen le plus simple de démarrer le dashboard est de l'activer lors du démarrage du bot :

```bash
python scripts/start_bot.py --config=config/active_config.yaml --dashboard --dashboard-port=8080
```

Options disponibles :
- `--dashboard` : Active le dashboard
- `--dashboard-port` : Spécifie le port du dashboard (par défaut : 8080)

### Démarrage séparé (mode observateur)

Vous pouvez également démarrer le dashboard séparément en mode observateur, ce qui permet de surveiller un bot déjà en cours d'exécution :

```bash
python scripts/start_dashboard.py --port=8080 --config=config/active_config.yaml
```

Options disponibles :
- `--port` : Port du dashboard (par défaut : 8080)
- `--config` : Chemin vers le fichier de configuration
- `--data-dir` : Répertoire contenant les données du bot (par défaut : data/)

## Utilisation du dashboard

### Accès au dashboard

Une fois démarré, le dashboard est accessible via un navigateur web à l'adresse :

```
http://localhost:8080
```

Pour un accès distant, remplacez `localhost` par l'adresse IP du serveur.

### Interface principale

Le dashboard est organisé en plusieurs sections :

1. **Vue d'ensemble** : Résumé de l'état du bot et métriques clés
2. **Métriques de marché** : Prix, liquidité, gas, etc.
3. **Métriques de performance** : Profit, ROI, transactions, etc.
4. **Alertes actives** : Liste des alertes en cours
5. **Historique des transactions** : Détail des transactions récentes
6. **Logs en temps réel** : Flux des logs du bot

### Fonctionnalités interactives

Le dashboard offre plusieurs fonctionnalités interactives :

- **Filtrage des données** : Filtrez les métriques par période, token, etc.
- **Zoom sur les graphiques** : Zoomez sur des périodes spécifiques
- **Actions rapides** : Boutons pour des actions comme l'arrêt d'urgence
- **Recherche dans les logs** : Recherchez des mots-clés dans les logs

## Alertes et notifications

### Types d'alertes

Le système de monitoring peut générer plusieurs types d'alertes :

1. **Alertes de marché** :
   - Écarts de prix anormaux
   - Liquidité insuffisante
   - Gas excessif

2. **Alertes de performance** :
   - Profit inférieur au seuil
   - ROI négatif
   - Taux d'échec des transactions élevé

3. **Alertes système** :
   - Erreurs consécutives
   - Problèmes de connectivité RPC
   - Solde de wallet faible

4. **Alertes de sécurité** :
   - Détection d'attaques MEV
   - Transactions suspectes
   - Perte de fonds inexpliquée

### Configuration des notifications

Les notifications peuvent être envoyées via plusieurs canaux :

```yaml
notifications:
  email:
    enabled: true
    smtp_server: "smtp.example.com"
    smtp_port: 587
    username: "bot@example.com"
    password: "password"
    recipients: ["admin@example.com"]
    
  discord:
    enabled: true
    webhook_url: "https://discord.com/api/webhooks/..."
    
  telegram:
    enabled: true
    bot_token: "YOUR_BOT_TOKEN"
    chat_id: "YOUR_CHAT_ID"
```

### Personnalisation des alertes

Vous pouvez personnaliser les seuils d'alerte dans le fichier de configuration :

```yaml
alert_thresholds:
  low_balance: 0.1          # 10% du capital initial
  high_gas: 300             # 300 Gwei
  low_profit: 0.001         # 0.1%
  price_deviation: 0.05     # 5%
  error_rate: 0.2           # 20%
  consecutive_errors: 3     # 3 erreurs consécutives
```

Ou via le script `update_config.py` :

```bash
python scripts/update_config.py --param="monitoring.alert_thresholds.high_gas" --value=400
```

## Analyse des performances

### Métriques en temps réel

Le dashboard affiche plusieurs métriques en temps réel :

1. **Métriques financières** :
   - Profit total
   - ROI
   - Profit par transaction
   - Capital engagé

2. **Métriques de marché** :
   - Prix des tokens
   - Liquidité des pools
   - Prix du gas
   - Spread entre exchanges

3. **Métriques système** :
   - Utilisation CPU/mémoire
   - Latence RPC
   - Taux d'erreur
   - Temps d'exécution des transactions

### Analyse historique

Pour une analyse plus approfondie, utilisez le script `analyze_logs.py` :

```bash
# Analyse des performances sur une période
python scripts/analyze_logs.py --from="2023-04-01T00:00:00" --to="2023-04-02T00:00:00"

# Génération d'un rapport de performance
python scripts/analyze_logs.py --from="2023-04-01T00:00:00" --to="2023-04-02T00:00:00" --output="reports/performance_20230401.txt"
```

Le rapport généré inclut :
- Résumé des performances
- Analyse des opportunités
- Analyse des transactions
- Analyse des erreurs
- Graphiques de performance

## Intégration avec les procédures de rollback

Le système de monitoring est étroitement intégré avec les procédures de rollback :

### Détection automatique des incidents

Le monitoring détecte automatiquement les incidents et peut déclencher des procédures de rollback :

1. **Détection d'anomalies** :
   - Le `AdvancedMonitor` surveille en permanence les métriques
   - Les seuils d'alerte sont vérifiés à chaque mise à jour

2. **Activation du mode d'urgence** :
   - En cas d'anomalie critique, le mode d'urgence est activé
   - L'`EmergencySystem` est notifié pour prendre les mesures appropriées

3. **Notification des incidents** :
   - Les alertes sont affichées sur le dashboard
   - Des notifications sont envoyées via les canaux configurés

### Actions manuelles depuis le dashboard

Le dashboard permet également de déclencher manuellement des actions de rollback :

1. **Arrêt d'urgence** :
   - Bouton "Emergency Stop" pour arrêter immédiatement le bot
   - Formulaire pour spécifier la raison et la gravité

2. **Transfert d'urgence** :
   - Interface pour transférer les fonds vers un wallet sécurisé
   - Options pour spécifier les tokens et la priorité du gas

3. **Annulation des transactions** :
   - Liste des transactions en attente
   - Boutons pour annuler des transactions spécifiques ou toutes les transactions

## Personnalisation du dashboard

### Configuration de l'apparence

Vous pouvez personnaliser l'apparence du dashboard via le fichier de configuration :

```yaml
dashboard:
  theme: "dark"           # "dark" ou "light"
  logo: "path/to/logo.png"
  title: "GBPBot Monitor"
  refresh_interval: 2     # Intervalle de rafraîchissement en secondes
```

### Ajout de widgets personnalisés

Le dashboard est extensible avec des widgets personnalisés :

1. **Création d'un widget** :
   - Créez un fichier JavaScript dans `gbpbot/core/monitoring/dashboard/widgets/`
   - Suivez le modèle des widgets existants

2. **Enregistrement du widget** :
   - Ajoutez le widget dans `gbpbot/core/monitoring/dashboard/widgets/index.js`
   - Configurez son emplacement dans le dashboard

3. **Configuration du widget** :
   - Ajoutez les paramètres du widget dans le fichier de configuration

### Exemple de widget personnalisé

```javascript
// gbpbot/core/monitoring/dashboard/widgets/custom_widget.js
class CustomWidget extends Widget {
  constructor(container, options) {
    super(container, options);
    this.title = options.title || "Custom Widget";
    this.init();
  }
  
  init() {
    // Initialisation du widget
    this.container.innerHTML = `
      <div class="widget-header">${this.title}</div>
      <div class="widget-content" id="custom-content"></div>
    `;
  }
  
  update(data) {
    // Mise à jour du widget avec les nouvelles données
    document.getElementById("custom-content").innerHTML = `
      <div class="metric">${data.value}</div>
    `;
  }
}

// Enregistrement du widget
registerWidget("custom", CustomWidget);
```

---

## Exemples d'utilisation

### Scénario 1 : Surveillance quotidienne

Pour une surveillance quotidienne du bot :

1. Démarrez le bot avec le dashboard :
   ```bash
   python scripts/start_bot.py --config=config/active_config.yaml --dashboard
   ```

2. Accédez au dashboard via votre navigateur :
   ```
   http://localhost:8080
   ```

3. Vérifiez régulièrement :
   - Les métriques de performance
   - Les alertes actives
   - L'historique des transactions

### Scénario 2 : Analyse d'incident

En cas d'incident :

1. Consultez les alertes sur le dashboard pour identifier le problème

2. Analysez les logs autour de l'incident :
   ```bash
   python scripts/analyze_logs.py --from="[TIMESTAMP_INCIDENT-1h]" --to="[TIMESTAMP_INCIDENT+1h]" --level=error
   ```

3. Prenez les mesures appropriées via le dashboard ou les scripts de rollback

4. Documentez l'incident pour référence future

### Scénario 3 : Optimisation des performances

Pour optimiser les performances du bot :

1. Analysez les performances sur une période :
   ```bash
   python scripts/analyze_logs.py --from="2023-04-01T00:00:00" --to="2023-04-02T00:00:00"
   ```

2. Identifiez les opportunités d'amélioration :
   - Tokens les plus rentables
   - Heures de trading optimales
   - Sources de prix les plus fiables

3. Ajustez les paramètres du bot en conséquence :
   ```bash
   python scripts/update_config.py --param="trading.min_profit" --value=0.005
   ```

---

**Note importante** : Le système de monitoring est un outil essentiel pour la sécurité et la performance de GBPBot. Assurez-vous qu'il est correctement configuré et surveillé en permanence, surtout pendant les premières phases de déploiement en production. 