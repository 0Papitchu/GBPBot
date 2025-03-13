# Guide d'Intégration de l'IA dans GBPBot

> **IMPORTANT** : Ce document est obsolète et a été remplacé par un guide unifié plus complet.
> 
> Veuillez consulter [AI_README.md](AI_README.md) pour la documentation à jour sur l'intégration de l'IA.

---

## Redirection

Cette documentation a été consolidée avec `AI_INTEGRATION.md`, `AI_TRADING_INTEGRATION.md` et `README_IA.md` en un guide complet.

Le nouveau document unifié contient :
- Une vue d'ensemble des capacités d'IA dans GBPBot
- Un guide complet de configuration des modèles d'IA
- Des exemples pratiques d'utilisation de l'IA pour le trading
- Des conseils de dépannage et bonnes pratiques
- Des modèles de code pour l'intégration avec d'autres modules

**Merci de vous référer au nouveau guide : [AI_README.md](AI_README.md)**

## Introduction

Ce guide explique comment l'intelligence artificielle (IA) est intégrée dans GBPBot pour améliorer les décisions de trading, notamment pour le sniping de tokens et l'arbitrage. L'IA permet d'analyser plus efficacement les opportunités de marché, de détecter les scams potentiels et d'optimiser les stratégies de trading.

## Prérequis

Pour utiliser les fonctionnalités d'IA de GBPBot, vous devez avoir :

1. **Bibliothèques Python** : `langchain`, `openai`, et selon votre configuration `llama-cpp-python` ou `vllm`
2. **Clé API OpenAI** : Une clé API valide si vous utilisez le fournisseur OpenAI
3. **Ressources matérielles** : Pour les modèles locaux comme LLaMA, une carte graphique NVIDIA avec au moins 8 Go de VRAM

## Configuration

### Configuration des Fournisseurs d'IA

GBPBot prend en charge deux fournisseurs principaux d'IA :

1. **OpenAI (ChatGPT)** : Utilise l'API OpenAI pour les analyses
2. **LLaMA** : Exécute un modèle LLaMA localement sur votre machine

Pour configurer le fournisseur d'IA, vous pouvez :

- Définir la variable d'environnement `AI_PROVIDER` à `openai`, `llama`, ou `auto`
- Spécifier dans la configuration du bot :

```json
{
  "ai_settings": {
    "provider": "openai",
    "openai_api_key": "votre-clé-api",
    "model": "gpt-3.5-turbo"
  }
}
```

### Variables d'Environnement pour l'IA

| Variable | Description | Valeur par défaut |
|----------|-------------|-------------------|
| `AI_PROVIDER` | Fournisseur d'IA à utiliser | `auto` |
| `OPENAI_API_KEY` | Clé API OpenAI | - |
| `USE_AI_ANALYSIS` | Activer l'analyse par IA | `true` |
| `LLAMA_MODEL_PATH` | Chemin vers le modèle LLaMA local | `models/llama-2-7b.gguf` |

## Fonctionnalités d'IA Disponibles

### 1. Analyse de Marché

L'IA peut analyser les données du marché pour détecter des tendances, des patterns et faire des prédictions.

**Utilisation** :

```python
from gbpbot.ai import create_ai_client, get_prompt_manager
from gbpbot.ai.market_analyzer import MarketAnalyzer

# Créer un client IA
ai_client = create_ai_client(provider="openai")
prompt_manager = get_prompt_manager()

# Créer l'analyseur de marché
market_analyzer = MarketAnalyzer(ai_client, prompt_manager)

# Analyser les données du marché
market_data = {
    "token": {
        "symbol": "MEME",
        "price_history": [...],
        "volume_24h": 1500000,
        # ...
    },
    "market_conditions": {
        "btc_price": 35000,
        # ...
    }
}

analysis = market_analyzer.analyze_market_data(market_data)
print(f"Tendance: {analysis['trend']}, Confiance: {analysis['confidence']}")
```

### 2. Analyse des Contrats de Tokens

L'IA peut analyser le code des contrats pour détecter des problèmes de sécurité ou des fonctions malveillantes.

**Utilisation** :

```python
# Obtenir le code du contrat
contract_code = "// ... code Solidity ou Rust ..."

# Analyser le contrat
contract_analysis = ai_client.analyze_token_contract(contract_code)

if contract_analysis["risk_assessment"] == "high":
    print(f"Contrat à haut risque détecté! Issues: {len(contract_analysis['security_issues'])}")
```

### 3. Sniping de Tokens avec IA

L'IA est intégrée dans le module de sniping pour améliorer la sélection des tokens et la détermination des paramètres de trading.

**Configuration du Sniping avec IA** :

```json
{
  "sniping": {
    "use_ai_analysis": true,
    "min_ai_score": 0.7,
    "ai_provider": "openai"
  }
}
```

Les paramètres de sniping ajustés par l'IA incluent :
- Sélection des tokens à sniper en fonction du score d'analyse
- Montant à investir basé sur le niveau de confiance
- Ajustement dynamique du take profit et stop loss

## Exemples d'Utilisation

### Exécuter une Analyse de Marché

```python
from gbpbot.ai.market_analyzer import MarketAnalyzer
from gbpbot.ai import create_ai_client

# Créer le client et l'analyseur
ai_client = create_ai_client()
analyzer = MarketAnalyzer(ai_client)

# Préparer les données
token_data = {
    "symbol": "SOL",
    "price_history": [...],
    "volume_24h": 500000000
}

# Analyser les données
analysis = analyzer.analyze_market_data({"token": token_data})
print(analysis)

# Détecter les patterns
patterns = analyzer.detect_pattern(token_data)
print(patterns)

# Prédire le mouvement de prix
prediction = analyzer.predict_price_movement(token_data, timeframe_hours=24)
print(prediction)
```

### Démarrer le Sniping avec IA

```python
from gbpbot.sniping.solana_memecoin_sniper import SolanaMemecoinSniper
import asyncio

# Configuration avec IA activée
config = {
    "use_ai_analysis": True,
    "min_ai_score": 0.65,
    "ai_provider": "openai"
}

# Créer et démarrer le sniper
sniper = SolanaMemecoinSniper(config=config)

async def main():
    # Démarrer le sniper
    await sniper.start()
    
    # Laisser le sniper fonctionner pendant un certain temps
    await asyncio.sleep(3600)  # 1 heure
    
    # Arrêter le sniper
    await sniper.stop()

asyncio.run(main())
```

## Personnalisation des Prompts

Vous pouvez personnaliser les prompts utilisés par l'IA en modifiant les fichiers dans le dossier `gbpbot/ai/prompts/`. 

Les prompts disponibles sont :
- `market_analysis_prompt.txt` : Analyse des données de marché
- `code_analysis_prompt.txt` : Analyse de code
- `token_contract_analysis_prompt.txt` : Analyse des contrats de tokens

## Dépannage

### Problèmes Courants et Solutions

1. **Erreur "Model not found"** : Vérifiez que le modèle spécifié est disponible avec votre clé API.

   Solution : Utilisez un modèle disponible dans votre abonnement OpenAI.

2. **Erreur "OpenAI API Key not found"** : 

   Solution : Définissez la variable d'environnement `OPENAI_API_KEY` ou fournissez la clé dans la configuration.

3. **Problèmes de performance avec LLaMA local** :

   Solution : Réduisez la taille du modèle ou utilisez un matériel plus puissant. Alternativement, passez à OpenAI.

4. **Réponses d'IA lentes** :

   Solution : Utilisez un modèle plus petit ou ajustez les paramètres de requête comme `max_tokens` ou `temperature`.

## Limitations Actuelles

- Les modèles d'IA peuvent introduire une latence dans les décisions de trading
- L'analyse de grands volumes de données peut être coûteuse avec OpenAI
- Les modèles locaux comme LLaMA nécessitent des ressources importantes
- Les prédictions de l'IA ne sont pas infaillibles et doivent être considérées comme un outil d'aide à la décision

## Ressources Additionnelles

- [Documentation d'OpenAI](https://platform.openai.com/docs/)
- [Documentation LLaMA](https://github.com/meta-llama/llama)
- [LangChain Documentation](https://python.langchain.com/en/latest/)

---

Pour toute question ou suggestion concernant l'intégration d'IA dans GBPBot, veuillez créer une issue sur le dépôt GitHub. 