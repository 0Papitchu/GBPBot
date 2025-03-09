# Interface Telegram pour GBPBot

Ce document explique comment configurer et utiliser l'interface Telegram pour contrôler GBPBot à distance.

## Table des matières

1. [Fonctionnalités](#fonctionnalités)
2. [Installation et configuration](#installation-et-configuration)
3. [Commandes disponibles](#commandes-disponibles)
4. [Sécurité et bonnes pratiques](#sécurité-et-bonnes-pratiques)
5. [Configurations avancées](#configurations-avancées)
6. [Optimisation de performance](#optimisation-de-performance)
7. [Résolution des problèmes](#résolution-des-problèmes)

## Fonctionnalités

L'interface Telegram vous permet de :

- Démarrer et arrêter le GBPBot à distance
- Activer et désactiver les modules (sniping, arbitrage, frontrunning, etc.)
- Consulter les statistiques et performances du bot
- Recevoir des alertes en temps réel sur les profits réalisés
- Recevoir des notifications en cas d'erreur ou de problème de sécurité
- Analyser le marché et les tokens spécifiques
- Exécuter des backtests à distance

## Installation et configuration

### Création d'un bot Telegram

1. Créez un bot Telegram via [@BotFather](https://t.me/BotFather)
   - Envoyez `/newbot` à BotFather
   - Suivez les instructions pour créer un nouveau bot
   - Copiez le token que BotFather vous donne (format: `1234567890:ABCDefGhIJKlmnOPQRstUVwxyZ`)

### Configuration de GBPBot

Deux méthodes sont disponibles pour configurer le bot Telegram :

#### Méthode 1 : Via le fichier d'environnement (recommandée)

1. Ouvrez votre fichier `.env` (ou `.env.local`)
2. Configurez les variables suivantes :
   ```
   TELEGRAM_BOT_TOKEN=your_bot_token_here
   TELEGRAM_CHAT_ID=your_chat_id_here
   TELEGRAM_AUTHORIZED_USERS=your_user_id_here
   ```

3. Obtenir votre ID utilisateur Telegram :
   - Envoyez un message à [@userinfobot](https://t.me/userinfobot)
   - Notez l'ID numérique affiché (format: `123456789`)
   - Utilisez cet ID pour les variables `TELEGRAM_CHAT_ID` et `TELEGRAM_AUTHORIZED_USERS`

#### Méthode 2 : Via l'interface du GBPBot

1. Dans le menu principal de GBPBot, sélectionnez "Interface Telegram"
2. Choisissez "Configurer le token Telegram"
3. Collez votre token
4. Configurez également votre ID utilisateur dans les paramètres

### Démarrage du bot Telegram

Pour activer l'interface Telegram :

1. Configurez `BOT_MODE=telegram` dans votre fichier `.env`
2. Démarrez GBPBot normalement avec votre script de lancement
3. Ou utilisez l'option "Démarrer interface Telegram" dans le menu principal

## Commandes disponibles

| Commande | Description |
|----------|-------------|
| `/start` | Démarre l'interaction avec le bot |
| `/help` | Affiche la liste des commandes disponibles |
| `/status` | Affiche l'état actuel du bot |
| `/modules` | Gère les modules actifs |
| `/start_bot` | Démarre le GBPBot |
| `/stop_bot` | Arrête le GBPBot |
| `/stats` | Affiche les statistiques de performance |
| `/profits` | Affiche les profits réalisés |
| `/analyze_market` | Analyse le marché actuel et donne des recommandations |
| `/analyze_token [symbol]` | Analyse un token spécifique |
| `/predict [symbol]` | Fournit une prédiction de mouvement de prix |
| `/run_backtest [config]` | Exécute un backtest avec la configuration spécifiée |

## Gestion des modules

La commande `/modules` affiche les modules disponibles sous forme de boutons interactifs. Vous pouvez activer ou désactiver un module en cliquant sur le bouton correspondant.

Modules disponibles :
- Sniping de tokens
- Arbitrage entre DEX
- Front-running
- Suivi des whales
- Analyses de marché

## Sécurité et bonnes pratiques

⚠️ **Règles de sécurité importantes** ⚠️

1. **Limitez l'accès à votre bot** en configurant `TELEGRAM_AUTHORIZED_USERS`
   - Si cette variable n'est pas définie, n'importe qui pourrait contrôler votre bot
   - Vous pouvez spécifier plusieurs IDs séparés par des virgules

2. **Ne partagez jamais votre token Telegram** avec des personnes non autorisées
   - Un attaquant pourrait utiliser le token pour contrôler votre bot
   - Si vous suspectez une compromission, générez un nouveau token via BotFather

3. **Évitez d'envoyer des clés privées** via Telegram
   - Les messages Telegram ne sont pas chiffrés de bout en bout par défaut
   - Utilisez d'autres canaux sécurisés pour configurer les clés privées

4. **Activez les notifications de sécurité** pour être alerté en cas d'activité suspecte

## Configurations avancées

Vous pouvez personnaliser davantage le comportement de l'interface Telegram en modifiant les variables suivantes dans votre fichier `.env` :

```
# Configuration de base
TELEGRAM_ENABLED=true               # Activer l'interface Telegram
TELEGRAM_BOT_TOKEN=your_token_here  # Token du bot Telegram
TELEGRAM_CHAT_ID=your_chat_id_here  # ID du chat pour recevoir les notifications
TELEGRAM_AUTHORIZED_USERS=user1,user2  # IDs des utilisateurs autorisés

# Configuration des notifications
TELEGRAM_STARTUP_NOTIFICATION=true  # Notification au démarrage du bot
TELEGRAM_PROFIT_THRESHOLD=5.0       # Seuil de profit (USD) pour notification
TELEGRAM_ERROR_NOTIFICATION=true    # Notifications des erreurs critiques
TELEGRAM_SECURITY_NOTIFICATION=true # Alertes de sécurité (rug pulls, etc.)

# Fréquence des notifications
TELEGRAM_MAX_NOTIFICATIONS_PER_HOUR=10  # Limite anti-spam
TELEGRAM_SUMMARY_INTERVAL=3600     # Intervalle (sec) pour résumés périodiques
```

## Optimisation de performance

Pour optimiser les performances du bot Telegram, plusieurs paramètres sont disponibles dans `.env.optimized` :

```
# Paramètres d'optimisation Telegram
MAX_TRANSACTION_HISTORY=10000   # Nombre max de transactions en mémoire
MAX_CACHED_OPPORTUNITIES=5000   # Limite du cache d'opportunités
ML_MAX_MEMORY_USAGE=4060        # Limite mémoire (MB) pour le ML
```

Ces paramètres permettent de limiter l'utilisation des ressources par le bot Telegram, particulièrement utile sur des systèmes avec des ressources limitées.

## Résolution des problèmes

### Le bot ne répond pas aux commandes

- Vérifiez que l'interface Telegram est bien démarrée dans GBPBot
- Assurez-vous d'avoir démarré une conversation avec le bot sur Telegram
  - Envoyez `/start` pour initialiser l'interaction
- Vérifiez que votre ID est dans la liste des utilisateurs autorisés
  - Configurez `TELEGRAM_AUTHORIZED_USERS` avec votre ID Telegram
- Vérifiez les logs du serveur pour des erreurs d'authentification

### Le bot n'envoie pas de notifications

- Vérifiez que `TELEGRAM_CHAT_ID` est correctement configuré
- Assurez-vous que les notifications sont activées dans la configuration
- Vérifiez que le bot a la permission d'envoyer des messages
  - Il doit être administrateur du groupe si utilisé dans un groupe
- Vérifiez la limite anti-spam `TELEGRAM_MAX_NOTIFICATIONS_PER_HOUR`

### Erreur "Bot cannot initiate conversation"

- Telegram ne permet pas aux bots d'initier des conversations
- Vous devez d'abord envoyer un message au bot (par exemple `/start`)
- Ensuite, le bot pourra vous envoyer des messages

### Problèmes de performance

- Si le bot devient lent, vérifiez les paramètres de mise en cache
- Réduisez `MAX_TRANSACTION_HISTORY` et `MAX_CACHED_OPPORTUNITIES`
- Utilisez `TELEGRAM_SUMMARY_INTERVAL` pour réduire la fréquence des notifications
- Limitez le nombre de commandes complexes (/analyze_market, /predict) par heure 