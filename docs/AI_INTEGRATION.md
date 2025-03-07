# Guide d'Intégration de l'IA dans GBPBot

## Introduction

Ce document explique comment l'intelligence artificielle (IA) est intégrée dans GBPBot pour améliorer les stratégies de trading, l'analyse de marché, et la prise de décision. GBPBot utilise des modèles de langage avancés (LLMs) pour analyser les données de marché, détecter les patterns, et fournir des recommandations personnalisées.

## Table des Matières

1. [Vue d'ensemble](#vue-densemble)
2. [Configuration requise](#configuration-requise)
3. [Types de modèles d'IA](#types-de-modèles-dia)
4. [Fonctionnalités d'IA](#fonctionnalités-dia)
5. [Configuration](#configuration)
6. [Utilisation](#utilisation)
7. [Personnalisation des prompts](#personnalisation-des-prompts)
8. [Dépannage](#dépannage)
9. [Bonnes pratiques](#bonnes-pratiques)

## Vue d'ensemble

L'IA dans GBPBot est conçue pour:

- **Analyser les conditions du marché** pour détecter les tendances et opportunités
- **Évaluer les tokens** pour identifier les meilleurs candidats pour le trading
- **Détecter les patterns de prix** pour améliorer les décisions d'entrée/sortie
- **Analyser les contrats** pour identifier les risques potentiels et éviter les scams
- **Prédire les mouvements de prix** pour optimiser les stratégies de trading
- **Générer des rapports** pour faciliter la prise de décision informée

L'architecture d'IA de GBPBot est modulaire, ce qui vous permet de choisir entre différents fournisseurs d'IA (OpenAI, LLaMA) en fonction de vos besoins et ressources disponibles.

## Configuration requise

### Pour OpenAI (API distante)

- Connexion Internet stable
- Clé API OpenAI valide
- Python 3.8+
- Package `openai` installé (`pip install openai`)

### Pour LLaMA (modèle local)

- CPU: Minimum Intel i5/AMD Ryzen 5 (Intel i7/AMD Ryzen 7 ou mieux recommandé)
- RAM: Minimum 16 Go (32 Go ou plus recommandé)
- GPU: NVIDIA avec au moins 6 Go de VRAM (pour les versions plus légères)
- Espace disque: 10-20 Go pour les modèles
- Python 3.8+
- Package `vllm` installé (`pip install vllm`)

## Types de modèles d'IA

GBPBot peut utiliser deux types principaux de modèles d'IA:

### 1. Modèles OpenAI (cloud)

- **Avantages**: Puissance, précision, pas de ressources locales requises
- **Inconvénients**: Coût par requête, nécessite une connexion Internet
- **Modèles recommandés**: GPT-3.5-turbo, GPT-4 (pour une analyse plus approfondie)

### 2. Modèles LLaMA (local)

- **Avantages**: Pas de coût par requête, fonctionne hors ligne, confidentialité
- **Inconvénients**: Nécessite des ressources matérielles, moins puissant que GPT-4
- **Modèles recommandés**: LLaMA 2 7B/13B pour la plupart des analyses

## Fonctionnalités d'IA

### Analyse de marché

L'IA analyse les conditions globales du marché pour détecter les tendances, les sentiments et les opportunités. Elle examine:

- Capitalisation du marché
- Volumes d'échange
- Dominance BTC/ETH
- Tokens en tendance
- Indicateurs de peur et d'avidité

### Analyse de tokens

Pour chaque token, l'IA évalue:

- Tendance actuelle
- Forces et faiblesses
- Risques potentiels
- Opportunités d'investissement
- Recommandations personnalisées

### Détection de patterns

L'IA identifie les patterns techniques comme:

- Formations de chandeliers
- Figures chartistes
- Points de retournement
- Signes d'accumulation/distribution

### Analyse de contrats

Pour éviter les scams et les risques:

- Détection de fonctions malveillantes (honeypots, rug pulls)
- Évaluation des risques de sécurité
- Vérification de la liquidité et des permissions
- Recommandation (faire confiance/prudence/éviter)

### Prédiction de prix

L'IA fournit des prédictions de mouvement de prix basées sur:

- Données historiques
- Tendances actuelles
- Analyse technique
- Sentiment du marché

## Configuration

### Configuration d'OpenAI

1. Obtenez une clé API sur [OpenAI Platform](https://platform.openai.com/account/api-keys)
2. Configurez votre clé dans GBPBot:
   
   ```
   # Dans le menu principal:
   > Options 4 (Assistant IA)
   > Options 6 (Configurer)
   > Sélectionnez "OpenAI" comme fournisseur
   > Entrez votre clé API
   ```

   Ou modifiez directement le fichier de configuration:
   ```json
   {
     "AI_PROVIDER": "openai",
     "AI_MODEL": "gpt-3.5-turbo",
     "AI_TEMPERATURE": "0.7",
     "OPENAI_API_KEY": "votre-clé-api"
   }
   ```

### Configuration de LLaMA (local)

1. Téléchargez un modèle LLaMA compatible (LLaMA 2 7B/13B recommandé)
2. Placez le modèle dans un dossier accessible
3. Configurez GBPBot pour utiliser ce modèle:

   ```
   # Dans le menu principal:
   > Options 4 (Assistant IA)
   > Options 6 (Configurer)
   > Sélectionnez "llama" comme fournisseur
   > Entrez le chemin vers votre modèle
   ```

   Ou modifiez directement le fichier de configuration:
   ```json
   {
     "AI_PROVIDER": "llama",
     "AI_MODEL": "llama2-7b",
     "AI_TEMPERATURE": "0.7",
     "AI_LOCAL_MODEL_PATH": "/chemin/vers/votre/modele"
   }
   ```

### Options de configuration avancées

- **AI_TEMPERATURE**: Contrôle la créativité (0.0-1.0). Valeurs plus basses = plus prévisible, valeurs plus hautes = plus créatif
- **AI_MAX_TOKENS**: Limite la longueur des réponses
- **AI_CONTEXT_SIZE**: Taille du contexte pour les modèles locaux

## Utilisation

### Activation du module IA

1. Lancez GBPBot
2. Dans le menu principal, sélectionnez "4. Assistant IA"
3. Suivez les instructions pour activer le module

### Fonctionnalités disponibles

Une fois le module activé, vous pouvez:

1. **Analyser les conditions du marché**
   - Obtenir une vision globale du marché
   - Identifier les tendances actuelles
   - Recevoir des recommandations générales

2. **Analyser un token spécifique**
   - Entrez le symbole du token (ex: SOL, AVAX, BONK)
   - Obtenez une analyse détaillée des forces/faiblesses
   - Recevez des recommandations spécifiques

3. **Prédire le mouvement de prix**
   - Sélectionnez un token et une période
   - Obtenez une prédiction de direction, amplitude, et confiance
   - Consultez les facteurs clés influençant la prédiction

4. **Analyser un contrat intelligent**
   - Fournissez l'adresse du contrat ou le code source
   - Identifiez les problèmes de sécurité potentiels
   - Évaluez le niveau de risque global

5. **Générer un rapport de marché**
   - Obtenez un rapport complet sur l'état du marché
   - Visualisez les tendances et opportunités

### Intégration avec les modules de trading

L'IA s'intègre également avec les autres modules de GBPBot:

- **Module de Sniping**: Utilise l'IA pour scorer les tokens et éviter les scams
- **Module d'Arbitrage**: Utilise l'IA pour prédire les mouvements de prix et optimiser les entrées/sorties
- **Mode Auto**: Utilise l'IA pour ajuster dynamiquement les paramètres de trading

## Personnalisation des prompts

Les templates de prompts utilisés pour interagir avec les modèles d'IA peuvent être personnalisés pour répondre à vos besoins spécifiques.

### Localisation des templates

Les templates se trouvent dans le dossier `gbpbot/ai/prompts/`, avec les fichiers suivants:

- `market_analysis_prompt.txt`: Template pour l'analyse de marché
- `token_contract_analysis_prompt.txt`: Template pour l'analyse de tokens et contrats
- `code_analysis_prompt.txt`: Template pour l'analyse de code

### Modification des templates

Pour modifier un template:

1. Ouvrez le fichier correspondant dans un éditeur de texte
2. Modifiez le contenu tout en conservant les variables entre accolades (`{variable}`)
3. Sauvegardez le fichier
4. Redémarrez le module IA pour appliquer les changements

### Exemple de template personnalisé

```
PROMPT_TEMPLATE = """
Analyser les données de marché suivantes pour le trading de memecoins:
{market_data}

Je veux une analyse détaillée avec les éléments suivants:
1. Tendance générale du marché (haussière/baissière/neutre)
2. Niveau de confiance (0-100%)
3. Top 3 des indicateurs techniques pertinents
4. Patterns chartistes identifiés
5. Prédiction à court terme (24h)
6. Recommandations d'actions spécifiques
7. Niveau de risque global

Formatez la réponse en JSON structuré.
"""
```

## Dépannage

### Problèmes courants et solutions

1. **"Les modules d'IA ne sont pas disponibles"**
   - Assurez-vous d'avoir installé les dépendances requises:
     ```
     pip install openai langchain vllm
     ```

2. **"Impossible de créer le client IA"**
   - Vérifiez votre configuration (clé API, chemin du modèle)
   - Assurez-vous que le fournisseur sélectionné est disponible

3. **"Erreur lors de l'analyse"**
   - Vérifiez votre connexion Internet (pour OpenAI)
   - Vérifiez que vous avez suffisamment de ressources (pour LLaMA)
   - Consultez les logs pour plus de détails

4. **Réponses de mauvaise qualité**
   - Ajustez la température (valeurs plus basses pour plus de précision)
   - Essayez un modèle plus puissant
   - Personnalisez les templates de prompts

### Logs et diagnostics

Les logs liés à l'IA se trouvent dans:
- `logs/gbpbot_ai.log`

Pour un diagnostic plus approfondi, activez le mode de débogage:
```
# Dans le menu de configuration
> Options avancées
> Activer le mode débogage
```

## Bonnes pratiques

1. **Choix du modèle**
   - Utilisez GPT-3.5 pour la plupart des cas d'usage
   - Réservez GPT-4 pour les analyses critiques (économie de crédits)
   - Utilisez LLaMA pour les analyses fréquentes ou en déplacement

2. **Optimisation des coûts**
   - Activez le cache pour éviter les requêtes répétées
   - Limitez la longueur des outputs
   - Utilisez les modèles locaux pour les analyses fréquentes

3. **Validation des réponses**
   - Ne vous fiez pas aveuglément aux prédictions de l'IA
   - Combinez avec votre propre analyse
   - Utilisez plusieurs sources pour les décisions importantes

4. **Personnalisation**
   - Adaptez les templates à vos besoins spécifiques
   - Ajustez les paramètres de génération (température, tokens)
   - Créez des prompts spécifiques pour les tokens ou marchés que vous suivez

---

Pour plus d'informations ou de l'aide supplémentaire, consultez le Discord officiel de GBPBot ou ouvrez une issue sur le GitHub du projet.

**Avertissement**: Les prédictions de l'IA sont basées sur des données historiques et des patterns identifiés, mais ne garantissent pas les résultats futurs. Utilisez toujours GBPBot de manière responsable et ne tradez pas au-delà de ce que vous pouvez vous permettre de perdre. 