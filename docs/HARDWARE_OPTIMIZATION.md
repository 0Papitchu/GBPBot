# Optimisation Matérielle de GBPBot

## Introduction

L'optimisation matérielle est une fonctionnalité clé du GBPBot qui permet d'adapter ses performances à votre configuration spécifique. Grâce à cette optimisation, le bot peut:

- Utiliser efficacement votre CPU (nombre de cœurs, fréquence)
- Exploiter la puissance de votre GPU pour les modèles d'IA
- Gérer intelligemment l'utilisation de la mémoire
- Optimiser les accès disque et les performances réseau

Cette documentation explique comment configurer, activer et exploiter au mieux les capacités d'optimisation matérielle du GBPBot.

## Configuration Recommandée

GBPBot est optimisé pour fonctionner sur une large gamme de configurations, mais certaines spécifications minimales sont recommandées:

| Composant | Minimum | Recommandé | Optimal (IA) |
|-----------|---------|------------|--------------|
| CPU | Intel i3 / Ryzen 3 | Intel i5-12400F / Ryzen 5 | Intel i7 / Ryzen 7+ |
| RAM | 8 Go | 16 Go | 32 Go+ |
| GPU | Non requis | RTX 3050 | RTX 3060/3070+ |
| Stockage | HDD 1 To | SSD 512 Go | SSD NVMe 1 To+ |
| Réseau | 10 Mbps | 100 Mbps | 1 Gbps |

## Activation de l'Optimisation

### Via la Ligne de Commande

Pour activer l'optimisation matérielle, utilisez le paramètre `--optimize` lors du lancement du GBPBot:

```bash
python run_gbpbot.py --optimize
```

Vous pouvez également spécifier un profil d'optimisation particulier:

```bash
python run_gbpbot.py --optimize --optimization-profile=high_performance
```

### Via le Fichier de Configuration

Vous pouvez également activer l'optimisation dans votre fichier de configuration `.env`:

```
GBPBOT_OPTIMIZATION_ENABLED=true
GBPBOT_OPTIMIZATION_PROFILE=high_performance
```

Ou dans votre fichier JSON de configuration:

```json
{
  "optimization": {
    "enabled": true,
    "profile": "high_performance"
  }
}
```

## Profils d'Optimisation

GBPBot inclut plusieurs profils d'optimisation prédéfinis:

| Profil | Description | Usage recommandé |
|--------|-------------|------------------|
| `default` | Équilibre entre performance et consommation de ressources | Usage général |
| `high_performance` | Maximise la performance au détriment de la consommation | Trading intensif, sniping rapide |
| `low_resource` | Minimise l'utilisation des ressources | Opérations de longue durée |
| `ai_focused` | Optimise l'utilisation du GPU pour les modèles d'IA | Analyse de marché avancée |
| `stealth` | Répartit l'utilisation des ressources pour être discret | Éviter la détection |

## Optimisation Automatique pour Votre Matériel

### Détection Automatique

Lors de sa première exécution avec l'optimisation activée, GBPBot détecte automatiquement:

- Votre CPU (modèle, nombre de cœurs, fréquence)
- Votre GPU (modèle, mémoire, support CUDA)
- Votre mémoire disponible
- Les caractéristiques de votre disque (type, vitesse)
- Vos interfaces réseau

Ces informations sont utilisées pour créer un profil d'optimisation personnalisé adapté à votre configuration.

### Création d'un Profil Personnalisé

Pour créer un profil personnalisé, exécutez l'outil d'optimisation matérielle:

```bash
python -m gbpbot.core.optimization.optimize_hardware --save --profile=my_custom_profile
```

Cet outil:
1. Détecte votre matériel
2. Effectue des tests de performance
3. Génère des paramètres optimaux
4. Sauvegarde le profil pour une utilisation future

## Optimisations Spécifiques

### CPU

- **Allocation de threads**: Distribue les threads pour les différentes tâches (trading, IA, surveillance)
- **Affinité CPU**: Assigne des tâches spécifiques à des cœurs spécifiques
- **Priorité des processus**: Ajuste la priorité des processus pour les opérations critiques

Pour l'**Intel i5-12400F**, l'optimisation:
- Alloue 4 threads pour le trading (sur 12 disponibles)
- Réserve 2 threads pour l'IA/ML
- Utilise 1 thread pour la surveillance
- Configure la priorité du processus à "high" pour les opérations critiques

### GPU

- **Utilisation CUDA**: Active l'accélération GPU pour les modèles d'IA
- **Batch size optimal**: Définit la taille de lot optimale pour votre GPU
- **Précision adaptative**: Utilise une précision FP16 ou FP32 selon les capacités
- **Mémoire GPU**: Alloue intelligemment la mémoire entre les différents modèles

Pour l'**RTX 3060**, l'optimisation:
- Utilise la précision FP16 pour économiser la mémoire
- Configure une batch size de 16 pour les inférences
- Active TensorCores pour les modèles compatibles
- Alloue 70% de la mémoire GPU aux modèles d'IA

### Mémoire

- **Allocation stratégique**: Répartit la mémoire entre les différentes fonctionnalités
- **Garbage collection**: Programme la libération périodique de la mémoire
- **Cache adaptatif**: Ajuste dynamiquement la taille du cache selon l'utilisation

Pour **16 Go de RAM**, l'optimisation:
- Limite l'utilisation totale à 70% (environ 11 Go)
- Alloue 30% pour le trading (environ 4,8 Go)
- Réserve 20% pour l'IA (environ 3,2 Go)
- Utilise 10% pour le cache (environ 1,6 Go)

### Disque

- **Optimisation I/O**: Ajuste les tampons de lecture/écriture
- **Cache stratégique**: Met en cache les données fréquemment accédées
- **Compression intelligente**: Compresse les données rarement utilisées

Pour les **SSD NVMe**, l'optimisation:
- Utilise des buffers de lecture/écriture de 16 Ko
- Configure une stratégie de cache "ultra" (jusqu'à 2 Go)
- Mesure et s'adapte à la vitesse d'I/O réelle

## Surveillance des Performances

### Métriques Disponibles

GBPBot surveille en permanence:

- Utilisation CPU (globale et par thread)
- Utilisation mémoire (totale et par module)
- Utilisation GPU (si disponible)
- Activité disque (lecture/écriture)
- Performance réseau

### Accès aux Métriques

Pour accéder aux métriques de performance:

```python
from gbpbot.core.optimization import get_optimization_status

status = get_optimization_status()
print(f"CPU: {status['current_metrics']['cpu']}%")
print(f"RAM: {status['current_metrics']['memory']}%")
print(f"GPU: {status['current_metrics']['gpu']}%")
```

Via le CLI, utilisez la commande:

```
status performance
```

Ou via le dashboard web, consultez l'onglet "Performance".

## Installation des Dépendances

Pour utiliser toutes les fonctionnalités d'optimisation, installez les dépendances supplémentaires:

```bash
python -m gbpbot.core.optimization.install_dependencies
```

Ce script détecte votre matériel et installe uniquement les packages nécessaires pour votre configuration.

## Recommandations Spécifiques

### Pour i5-12400F + RTX 3060 + 16 Go RAM

1. Activez l'optimisation avec le profil "high_performance"
2. Déplacez les calculs intensifs sur le GPU (TensorFlow, PyTorch)
3. Limitez le nombre de stratégies simultanées à 2-3
4. Utilisez la précision FP16 pour les modèles d'IA
5. Activez le mode économie de ressources pour les opérations >4h

## Dépannage

### Problèmes Courants

**Erreur: "CUDA not available"**
- Solution: Installez les pilotes NVIDIA à jour

**Utilisation CPU/RAM excessive**
- Solution: Utilisez le profil "low_resource"

**Erreur: "Failed to initialize optimization"**
- Solution: Exécutez le script d'installation des dépendances

**Performance réseau faible**
- Solution: Réduisez `concurrent_connections` dans la configuration

## Architecture du Module d'Optimisation

```
gbpbot/core/optimization/
├── __init__.py                # Interface principale
├── hardware_optimizer.py      # Optimiseur matériel
├── install_dependencies.py    # Installation des dépendances
├── optimize_hardware.py       # Script utilitaire
└── profiles/                  # Profils prédéfinis
    ├── default.json
    ├── high_performance.json
    └── low_resource.json
```

## Conclusion

L'optimisation matérielle du GBPBot vous permet d'exploiter pleinement les capacités de votre système tout en garantissant des performances optimales pour le trading de MEME coins. En adaptant les paramètres à votre configuration spécifique, vous obtenez un bot plus rapide, plus réactif et plus efficace.

Pour toute question ou assistance supplémentaire concernant l'optimisation, consultez la documentation complète ou contactez l'équipe de support. 