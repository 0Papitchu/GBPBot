# Interface Telegram pour GBPBot

Ce document explique comment configurer et utiliser l'interface Telegram pour contrôler GBPBot à distance.

## Fonctionnalités

L'interface Telegram vous permet de :

- Démarrer et arrêter le GBPBot à distance
- Activer et désactiver les modules (sniping, arbitrage, frontrunning, etc.)
- Consulter les statistiques et performances du bot
- Recevoir des alertes en temps réel sur les profits réalisés
- Recevoir des notifications en cas d'erreur ou de problème de sécurité

## Configuration

Pour utiliser l'interface Telegram, vous devez d'abord la configurer :

1. Créez un bot Telegram via [@BotFather](https://t.me/BotFather)
   - Envoyez `/newbot` à BotFather
   - Suivez les instructions pour créer un nouveau bot
   - Copiez le token que BotFather vous donne

2. Configurez votre token dans GBPBot
   - Dans le menu principal de GBPBot, sélectionnez "Interface Telegram"
   - Choisissez "Configurer le token Telegram"
   - Collez votre token

3. (Optionnel) Configurez les utilisateurs autorisés
   - Obtenez votre ID Telegram en envoyant un message à [@userinfobot](https://t.me/userinfobot)
   - Dans le menu Telegram de GBPBot, configurez les utilisateurs autorisés
   - Séparez plusieurs IDs par des virgules

4. Démarrez l'interface Telegram depuis le menu

## Utilisation

Une fois l'interface configurée et démarrée, vous pouvez interagir avec GBPBot via Telegram.

### Commandes disponibles

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

### Gestion des modules

La commande `/modules` affiche les modules disponibles sous forme de boutons. Vous pouvez activer ou désactiver un module en cliquant sur le bouton correspondant.

### Notifications

Le bot peut vous envoyer plusieurs types de notifications :

- **Alertes de profit** : Envoyées lorsqu'une transaction génère un profit supérieur au seuil configuré
- **Alertes d'erreur** : Envoyées en cas d'erreur critique dans le fonctionnement du bot
- **Alertes de sécurité** : Envoyées lorsqu'un risque de sécurité est détecté (rug pull, honeypot, etc.)

## Configuration avancée

Vous pouvez personnaliser davantage le comportement de l'interface Telegram en modifiant le fichier `.env` :

```
# INTERFACE TELEGRAM
TELEGRAM_ENABLED=true               # Activer l'interface Telegram
TELEGRAM_BOT_TOKEN=your_token_here  # Token du bot Telegram
TELEGRAM_AUTHORIZED_USERS=123456,789012  # IDs Telegram des utilisateurs autorisés
TELEGRAM_NOTIFICATIONS={"profit":true,"error":true,"security":true,"all":false,"none":false}
TELEGRAM_STARTUP_NOTIFICATION=true  # Envoyer une notification lors du démarrage du bot
TELEGRAM_PROFIT_THRESHOLD=5.0       # Seuil de profit (USD) pour envoyer une notification
ML_MAX_MEMORY_USAGE=4096         # Limitez l'utilisation mémoire du ML (MB)
MAX_TRANSACTION_HISTORY=10000    # Limitez l'historique des transactions conservé
```

## Sécurité

⚠️ **Attention** ⚠️

- Limitez l'accès à votre bot Telegram en configurant les utilisateurs autorisés
- Ne partagez jamais votre token Telegram avec d'autres personnes
- Le bot ne demandera jamais vos clés privées ou mots de passe
- Vérifiez régulièrement les activités de votre bot pour détecter toute activité suspecte

## Résolution des problèmes

**Le bot ne répond pas aux commandes**
- Vérifiez que l'interface Telegram est bien démarrée dans GBPBot
- Assurez-vous d'avoir démarré une conversation avec le bot sur Telegram
- Vérifiez que votre ID est dans la liste des utilisateurs autorisés

**Le bot n'envoie pas de notifications**
- Vérifiez la configuration des notifications dans le menu Telegram
- Assurez-vous que les messages ne sont pas bloqués par votre client Telegram

**Erreur "Bot cannot initiate conversation"**
- Vous devez d'abord envoyer un message au bot avant qu'il puisse vous envoyer des messages
- Envoyez `/start` à votre bot pour initialiser la conversation 

# Déjà implémenté dans le code:
self.known_opportunities = set(list(self.known_opportunities)[-5000:])  # Limite la mémoire cache 