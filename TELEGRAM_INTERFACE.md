# Interface Telegram pour GBPBot

Ce document explique comment configurer et utiliser l'interface Telegram pour contrôler GBPBot à distance.

## Fonctionnalités

L'interface Telegram vous permet de :

1. Contrôler GBPBot à distance depuis n'importe quel appareil
2. Démarrer et arrêter le bot
3. Gérer les modules (Arbitrage, Sniping, etc.)
4. Consulter les statistiques et les profits
5. Recevoir des alertes en temps réel
6. Accéder aux analyses d'IA avec Claude 3.7
7. Obtenir des analyses de marché et recommandations de trading

## Configuration

Pour utiliser l'interface Telegram, vous devez d'abord la configurer :

1. Créez un bot Telegram via [@BotFather](https://t.me/BotFather)
   - Envoyez `/newbot` à BotFather
   - Suivez les instructions pour créer votre bot
   - Notez le token API qui vous est fourni

2. Configurez le token dans GBPBot :
   - Dans le menu principal de GBPBot, sélectionnez "Interface Telegram"
   - Choisissez "Configurer le token Telegram"
   - Entrez le token fourni par BotFather

3. Configurez les utilisateurs autorisés :
   - Obtenez votre ID Telegram en envoyant un message à [@userinfobot](https://t.me/userinfobot)
   - Dans le menu Telegram de GBPBot, configurez les utilisateurs autorisés

4. Démarrez l'interface Telegram depuis le menu

## Commandes disponibles

### Commandes de base
- `/start` - Démarrer le bot Telegram
- `/help` - Afficher l'aide
- `/status` - Vérifier l'état du GBPBot
- `/modules` - Gérer les modules actifs

### Contrôle du GBPBot
- `/start_bot` - Démarrer les modules du GBPBot
- `/stop_bot` - Arrêter les modules du GBPBot

### Statistiques et Performance
- `/stats` - Afficher les statistiques de trading
- `/profits` - Montrer les profits réalisés

### Analyse IA Classique
- `/analyze_market` - Analyser les conditions actuelles du marché
- `/analyze_token [symbole]` - Analyser un token spécifique
- `/predict [symbole] [durée]` - Prédire le mouvement de prix

### Analyse IA avancée avec Claude 3.7
- `/claude_analyze` - Informations sur les analyses Claude 3.7
- `/market_overview` - Obtenir une vue d'ensemble du marché crypto en temps réel
- `/token_score [symbol] [chain]` - Évaluer le potentiel d'un token avec recherche web et scoring
- `/trading_strategy [symbol] [chain] [type] [risque]` - Générer une stratégie de trading optimisée

## Exemples d'utilisation de Claude 3.7

### Vue d'ensemble du marché
```
/market_overview
```
Cette commande génère une analyse complète du marché crypto actuel incluant :
- Tendance globale du marché
- Sentiment général (Bullish/Bearish/Neutre)
- Secteurs performants
- Tokens à surveiller
- Opportunités et risques identifiés

### Évaluation d'un token
```
/token_score BONK solana
```
Analyse complète d'un token spécifique sur la blockchain indiquée :
- Score global sur 100
- Évaluation de la liquidité
- Risque de rug pull
- Potentiel de croissance
- Drapeaux rouges identifiés
- Recommandation (Acheter/Surveiller/Éviter)

### Génération de stratégie
```
/trading_strategy BONK solana scalping aggressive
```
Génère une stratégie de trading détaillée :
- Points d'entrée optimaux
- Points de sortie recommandés
- Take profit et stop loss suggérés
- Taille de position recommandée
- Indicateurs techniques à surveiller

Les paramètres optionnels sont :
- Type de stratégie : `auto`, `scalping`, `day_trading`, `swing`, `long_term`
- Profil de risque : `conservative`, `balanced`, `aggressive`

## Configuration avancée

Vous pouvez personnaliser davantage le comportement de l'interface Telegram en modifiant le fichier `.env` :

```env
# INTERFACE TELEGRAM
TELEGRAM_ENABLED=true               # Activer l'interface Telegram
TELEGRAM_BOT_TOKEN=your_token_here  # Token du bot Telegram
TELEGRAM_AUTHORIZED_USERS=123456,789012  # IDs Telegram des utilisateurs autorisés
TELEGRAM_NOTIFICATIONS={"profit":true,"error":true,"security":true,"all":false,"none":false}
TELEGRAM_STARTUP_NOTIFICATION=true  # Envoyer une notification lors du démarrage du bot
TELEGRAM_PROFIT_THRESHOLD=5.0       # Seuil de profit (USD) pour envoyer une notification

# CONFIGURATION IA CLAUDE 3.7
AI_PROVIDER=claude                  # Définir "claude" pour utiliser Claude 3.7
CLAUDE_API_KEY=your_key_here        # Votre clé API Anthropic Claude
CLAUDE_MODEL=claude-3-7-sonnet-20240229  # Modèle à utiliser
SERPER_API_KEY=your_key_here        # Clé API Serper pour la recherche web
```

## Sécurité

Quelques points importants concernant la sécurité :

- Limitez l'accès à votre bot Telegram en configurant les utilisateurs autorisés
- Ne partagez jamais votre token Telegram avec d'autres personnes
- Définissez un seuil de transaction maximum pour éviter les pertes importantes
- Utilisez les commandes avec prudence, particulièrement sur les réseaux publics

## Dépannage

Si vous rencontrez des problèmes :

- Vérifiez que l'interface Telegram est bien démarrée dans GBPBot
- Assurez-vous d'avoir démarré une conversation avec le bot sur Telegram
- Confirmez que votre ID Telegram est bien dans la liste des utilisateurs autorisés
- Vérifiez la configuration des notifications dans le menu Telegram
- Assurez-vous que les messages ne sont pas bloqués par votre client Telegram

Pour les problèmes avec l'analyse Claude 3.7 :
- Vérifiez que AI_PROVIDER est réglé sur "claude" dans votre fichier .env
- Assurez-vous que votre clé CLAUDE_API_KEY est valide et active
- Vérifiez que SERPER_API_KEY est configuré pour la recherche web 