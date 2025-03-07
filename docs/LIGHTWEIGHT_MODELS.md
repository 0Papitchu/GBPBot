# Modèles d'IA Légers pour GBPBot

## Introduction

Les modèles d'IA légers constituent une composante essentielle de GBPBot, permettant d'effectuer des analyses en temps réel avec une latence minimale. Contrairement aux grands modèles de langage (LLM) comme OpenAI GPT ou LLaMA qui nécessitent un appel API ou des ressources importantes, ces modèles légers sont optimisés pour s'exécuter localement et rapidement, tout en conservant des capacités d'analyse suffisantes pour la prise de décision en trading.

Ce document explique comment les modèles légers sont intégrés à GBPBot, leurs avantages, et comment les configurer et les utiliser efficacement.

## Avantages des Modèles Légers

### 1. Performance Ultra-Rapide

- **Temps de réponse < 50ms** pour la plupart des analyses
- **Exécution locale** sans dépendance à des services externes
- **Taille réduite** (~50MB par modèle vs. plusieurs GB pour les LLM)
- **Optimisation CPU/GPU** pour une utilisation efficace des ressources

### 2. Applications Critiques en Temps Réel

- **Analyse de contrats** pour détecter les risques de sécurité
- **Évaluation du potentiel** des nouveaux tokens
- **Prédiction de volatilité** à court terme
- **Détection de patterns** dans les données de marché

### 3. Complémentarité avec les LLM

Les modèles légers complètent parfaitement les capacités des grands modèles de langage :

|                        | Modèles Légers                   | Grands Modèles (LLM)              |
|------------------------|----------------------------------|-----------------------------------|
| **Temps de réponse**   | Ultra-rapide (10-50ms)          | Plus lent (500-3000ms)            |
| **Précision**          | Bonne pour tâches spécifiques    | Excellente pour analyses complexes|
| **Couverture**         | Limitée à certains patterns      | Très large                        |
| **Adaptabilité**       | Figée après entraînement         | Plus flexible                     |
| **Consommation**       | Très faible                      | Élevée                            |
| **Disponibilité**      | 100% (exécution locale)          | Dépend des API externes           |

## Architecture des Modèles Légers

GBPBot utilise une architecture modulaire pour les modèles légers, organisée comme suit :

```
gbpbot/
├── machine_learning/
│   ├── lightweight_models.py      # Gestionnaire de modèles légers
│   ├── contract_analyzer.py       # Analyseur de contrats léger
│   ├── models/                    # Répertoire des modèles
│   │   ├── contract_security/     # Modèle d'analyse de sécurité
│   │   │   ├── model_config.json  # Configuration du modèle
│   │   │   └── contract_security_model.onnx  # Modèle ONNX
│   │   ├── token_potential/       # Modèle d'évaluation de potentiel
│   │   │   ├── model_config.json
│   │   │   └── token_potential_model.onnx
│   │   └── ...
```

### Formats de Modèles Supportés

GBPBot prend en charge plusieurs formats de modèles optimisés :

1. **ONNX** : Format optimisé et interopérable, idéal pour le déploiement sur différentes architectures
2. **TensorFlow Lite** : Version allégée des modèles TensorFlow
3. **PyTorch JIT** : Modèles PyTorch tracés pour une inférence plus rapide
4. **XGBOOST/LightGBM** : Pour les modèles traditionnels de machine learning
5. **Format personnalisé** : Pour les modèles spécifiques

## Modèles Disponibles

### 1. Analyseur de Sécurité de Contrats

Ce modèle analyse rapidement les contrats de tokens pour détecter les risques de sécurité :

- **Type** : ONNX
- **Tâche** : Analyse de sécurité
- **Temps d'exécution** : Typiquement 10-30ms
- **Entrées** : Code source du contrat ou bytecode
- **Sorties** : Scores de risque pour différentes catégories (honeypot, rugpull, backdoor, etc.)
- **Précision** : ~92% sur les contrats typiques

Le modèle détecte 7 catégories de risques :
- Secure (sécurisé)
- Honeypot Risk (risque de honeypot)
- Rugpull Risk (risque de rug pull)
- Backdoor Risk (risque de backdoor)
- Tax Manipulation Risk (risque de manipulation des taxes)
- Privileged Functions Risk (risque de fonctions privilégiées)
- Transfer Blocking Risk (risque de blocage des transferts)

### 2. Évaluateur de Potentiel de Token

En cours de développement, ce modèle évalue le potentiel de croissance d'un token basé sur ses caractéristiques techniques et de marché.

### 3. Prédicteur de Volatilité

En cours de développement, ce modèle prédit la volatilité à court terme (1-15 minutes) pour optimiser les entrées/sorties.

### 4. Détecteur de Patterns de Prix

En cours de développement, ce modèle détecte les patterns récurrents dans les données de prix pour anticiper les mouvements.

## Intégration dans GBPBot

Les modèles légers sont principalement intégrés au module de sniping pour une analyse rapide avant d'investir. Voici comment ils fonctionnent :

1. **Découverte de Token** : Un nouveau token est détecté
2. **Analyse Légère** : Le modèle léger analyse rapidement le contrat (< 50ms)
3. **Décision Rapide** : 
   - Si risque élevé → Rejet immédiat
   - Si risque moyen → Allocation réduite + analyse approfondie
   - Si faible risque → Approbation préliminaire

Cette approche à deux niveaux permet de rejeter rapidement les tokens clairement dangereux tout en économisant les ressources des analyses approfondies pour les tokens prometteurs.

### Exemple de Flux d'Analyse

```
Detection → Analyse Légère (30ms) → Analyse IA Complète (optionnelle, 500-1000ms) → Décision Finale
```

## Configuration

Pour configurer les modèles légers, modifiez les paramètres suivants dans votre configuration :

```json
{
  "use_lightweight_analyzer": true,
  "lightweight_models_dir": "/chemin/vers/models",
  "lightweight_analysis_timeout_ms": 500,
  "security_threshold": 0.65
}
```

| Paramètre | Description | Valeur par défaut |
|-----------|-------------|-----------------|
| `use_lightweight_analyzer` | Active/désactive l'analyseur léger | `true` |
| `lightweight_models_dir` | Répertoire des modèles légers | Répertoire par défaut |
| `lightweight_analysis_timeout_ms` | Timeout maximum pour l'analyse (ms) | `500` |
| `security_threshold` | Seuil de score pour considérer un contrat comme sûr (0-1) | `0.65` |

## Développement et Entraînement

GBPBot inclut des modèles pré-entraînés, mais vous pouvez entraîner et optimiser vos propres modèles :

### 1. Entraînement des Modèles

Les modèles légers sont généralement entraînés avec TensorFlow, PyTorch ou XGBoost, puis convertis en format optimisé (ONNX).

### 2. Quantification

Pour réduire la taille et améliorer les performances, les modèles sont quantifiés :
- **Quantification INT8** : Réduit la précision des poids à 8 bits
- **Quantification dynamique** : Quantifie à l'exécution
- **Élagage** : Supprime les connexions inutiles

### 3. Configuration

Chaque modèle nécessite un fichier `model_config.json` qui décrit ses caractéristiques :

```json
{
  "name": "contract_security_analyzer",
  "type": "onnx",
  "task": "contract_security",
  "model_path": "contract_security_model.onnx",
  "version": "1.0.0",
  "description": "Modèle léger pour l'analyse rapide de sécurité des contrats",
  "config": {
    "use_cuda": true,
    "threshold_score": 0.65
  },
  "metadata": {
    "input_shape": [1, 768],
    "output_shape": [1, 7],
    "classes": ["secure", "honeypot_risk", "rugpull_risk", "backdoor_risk", "tax_manipulation_risk", "privileged_functions_risk", "transfer_blocking_risk"],
    "accuracy": 0.92
  }
}
```

## Performances et Mesures

GBPBot surveille les performances des modèles légers en temps réel :

```python
stats = sniper.get_stats()
lightweight_stats = stats["lightweight_analysis"]
```

Les statistiques disponibles incluent :

- `total_analyses` : Nombre total d'analyses effectuées
- `analyses_succeeded` : Nombre d'analyses réussies
- `analyses_failed` : Nombre d'analyses échouées
- `tokens_rejected` : Nombre de tokens rejetés suite à l'analyse
- `avg_analysis_time_ms` : Temps moyen d'analyse en millisecondes

## Limitations Actuelles

- **Spécialisation** : Les modèles sont optimisés pour des tâches spécifiques uniquement
- **Évolution du marché** : Nécessité de mettre à jour les modèles périodiquement
- **Précision vs Vitesse** : Compromis entre vitesse et précision
- **Couverture de cas** : Moins efficaces pour les contrats atypiques ou nouveaux patterns

## Feuille de Route

Le développement des modèles légers suit cette feuille de route :

1. **Analyste de contrat v2** : Amélioration de la précision et du temps d'exécution
2. **Prédicteur de prix à 5 minutes** : Modèle de prédiction à court terme
3. **Analyseur de tendance** : Détection de changements de tendance
4. **Évaluateur de liquidité** : Prédiction des mouvements de liquidité
5. **Fusion multi-modèles** : Combinaison des sorties de plusieurs modèles

## Conclusion

Les modèles d'IA légers représentent une avancée significative pour GBPBot, permettant des analyses en temps réel avec une latence minimale. Cette approche hybride, combinant modèles légers pour les décisions rapides et grands modèles pour les analyses approfondies, offre le meilleur des deux mondes : rapidité et précision.

L'intégration continue de modèles plus performants et l'optimisation des modèles existants permettront d'améliorer encore les capacités de prise de décision automatisée du bot, tout en maintenant les temps de réponse sous le seuil critique pour le trading haute fréquence. 