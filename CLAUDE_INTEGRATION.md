# Intégration de Claude 3.7 dans GBPBot

Ce document explique comment Claude 3.7 est intégré dans GBPBot pour fournir des analyses de marché avancées, des évaluations de tokens et des stratégies de trading optimisées.

## Vue d'ensemble

GBPBot intègre Claude 3.7 d'Anthropic pour offrir des capacités d'analyse avancées et des recommandations de trading basées sur l'intelligence artificielle. Cette intégration comprend:

1. **Analyse de marché en temps réel** - Vue d'ensemble du marché crypto avec tendances, sentiment et opportunités
2. **Évaluation de tokens** - Analyse complète des tokens avec notation de risque et potentiel
3. **Stratégies de trading** - Génération de stratégies personnalisées avec points d'entrée/sortie
4. **Recherche web intégrée** - Enrichissement des analyses avec des données actualisées du web

## Configuration

### Prérequis

Pour utiliser Claude 3.7 avec GBPBot, vous aurez besoin de:

1. Une clé API Claude d'Anthropic (https://console.anthropic.com/)
2. Une clé API Serper pour la recherche web (https://serper.dev/)

### Variables d'environnement

Configurez les variables suivantes dans votre fichier `.env.local`:

```env
# Configuration IA
AI_PROVIDER=claude                  # Définir "claude" pour utiliser Claude 3.7
CLAUDE_API_KEY=your_key_here        # Votre clé API Anthropic Claude
CLAUDE_MODEL=claude-3-7-sonnet-20240229  # Modèle à utiliser

# Recherche Web
SERPER_API_KEY=your_key_here        # Clé API Serper pour la recherche web
WEB_SEARCH_ENABLED=true             # Active la recherche web

# Paramètres d'analyse
USE_AI_ANALYSIS=true                # Active l'analyse IA
AI_ANALYZE_BEFORE_SNIPE=true        # Analyse avant sniping
MIN_TOKEN_SCORE=70                  # Score minimum pour sniping (0-100)
AI_REAL_TIME_MARKET_ANALYSIS=true   # Analyse en temps réel du marché
```

### Fichier de configuration

Un fichier de configuration détaillé est disponible dans `config/claude_config.yaml`. Ce fichier contient:

- Configuration de l'API Claude
- Paramètres du modèle
- Templates de prompts pour différentes analyses
- Paramètres de mise en cache
- Configuration du rate limiting

## Fonctionnalités

### 1. Analyse de marché

L'analyse de marché fournit une vue d'ensemble du marché crypto actuel, incluant:

- Tendance globale (Bullish/Bearish/Neutre)
- Sentiment du marché
- Secteurs performants
- Tokens à surveiller
- Opportunités et risques

#### Utilisation via l'interface CLI:
```bash
python gbpbot_cli_bridge.py market_overview
```

#### Utilisation via Telegram:
```
/market_overview
```

### 2. Évaluation de tokens

L'évaluation de tokens fournit une analyse détaillée d'un token spécifique:

- Score global sur 100
- Niveau de risque
- Évaluation de la liquidité
- Risque de rug pull
- Potentiel de croissance
- Drapeaux rouges
- Recommandation (Acheter/Surveiller/Éviter)

#### Utilisation via l'interface CLI:
```bash
python gbpbot_cli_bridge.py token_score --symbol BONK --chain solana
```

#### Utilisation via Telegram:
```
/token_score BONK solana
```

### 3. Génération de stratégie de trading

La génération de stratégie fournit une stratégie détaillée pour trader un token:

- Points d'entrée optimaux
- Points de sortie recommandés
- Take profit et stop loss suggérés
- Taille de position recommandée
- Indicateurs techniques à surveiller

#### Utilisation via l'interface CLI:
```bash
python gbpbot_cli_bridge.py trading_strategy --symbol BONK --chain solana --type scalping --risk aggressive
```

#### Utilisation via Telegram:
```
/trading_strategy BONK solana scalping aggressive
```

Les types de stratégies disponibles sont:
- `auto` - Automatiquement déterminé par l'IA (par défaut)
- `scalping` - Trading à très court terme
- `day_trading` - Trading intra-journalier
- `swing` - Trading sur plusieurs jours
- `long_term` - Trading à long terme

Les profils de risque disponibles sont:
- `conservative` - Risque minimal
- `balanced` - Équilibre entre risque et rendement (par défaut)
- `aggressive` - Rendement maximal

## Architecture

L'intégration de Claude 3.7 comprend plusieurs composants:

1. **`ClaudeClient` (`gbpbot/ai/claude_client.py`)** - Client API pour interagir avec Claude 3.7
2. **`MarketIntelligence` (`gbpbot/ai/market_intelligence.py`)** - Système d'intelligence de marché qui combine Claude avec la recherche web
3. **`WebSearchProvider` (`gbpbot/ai/web_search.py`)** - Client pour la recherche web en temps réel

### Flux de données

```
[Données Market/Token] -> [WebSearchProvider] -> [MarketIntelligence] -> [ClaudeClient] -> [Résultat formaté]
```

## Utilisation des Tokens et Coûts

Claude 3.7 est un modèle payant. L'utilisation entraîne des coûts en fonction du nombre de tokens traités:

- Chaque requête à Claude 3.7 utilise environ 1000-3000 tokens en entrée
- Les réponses générées utilisent environ 500-2000 tokens
- Le coût par 1000 tokens varie selon le modèle Claude utilisé

Pour minimiser les coûts:
- Le système utilise une mise en cache pour éviter les requêtes répétées
- Les prompts sont optimisés pour la concision
- Les réponses sont structurées pour limiter la verbosité

## Dépannage

### Erreurs d'API

En cas d'erreurs avec l'API Claude:
1. Vérifiez que votre clé API est valide et active
2. Assurez-vous que vous avez suffisamment de crédits sur votre compte Anthropic
3. Vérifiez les logs pour des messages d'erreur spécifiques
4. Vérifiez votre connexion internet

### Problèmes de recherche web

Si la recherche web échoue:
1. Vérifiez que votre clé API Serper est valide
2. Assurez-vous que `WEB_SEARCH_ENABLED` est activé
3. Vérifiez votre connexion internet

### Améliorations futures

- Intégration de modèles Claude 3.7 Opus pour des analyses plus avancées
- Support pour plus de blockchains et de types d'actifs
- Modèles locaux pour les utilisateurs sans accès à l'API Claude
- Historique et traçabilité des analyses et recommandations
- Interface utilisateur dédiée pour visualiser les analyses

## Remarques sur la sécurité

- Toutes les clés API sont stockées localement dans `.env.local` et ne sont jamais partagées
- Les requêtes contenant des informations sensibles ne sont pas enregistrées
- Les interactions avec Claude sont chiffrées via HTTPS

## Références

- [Documentation API Claude](https://docs.anthropic.com/claude/reference/getting-started-with-the-api)
- [Documentation Serper](https://serper.dev/api-docs)
- [Guide des modèles Claude](https://www.anthropic.com/news/claude-3-family) 