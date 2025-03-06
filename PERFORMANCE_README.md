# Guide d'Optimisation et de Surveillance des Performances de GBPBot

Ce document explique comment utiliser les optimisations et le moniteur de performances pour GBPBot afin de maximiser l'efficacité du bot sur votre configuration matérielle.

## Table des Matières

1. [Optimisations Appliquées](#optimisations-appliquées)
2. [Utilisation du Moniteur de Performances](#utilisation-du-moniteur-de-performances)
3. [Ajustement des Paramètres](#ajustement-des-paramètres)
4. [Dépannage](#dépannage)

## Optimisations Appliquées

Les optimisations suivantes ont été appliquées à votre GBPBot pour améliorer ses performances sur votre configuration matérielle (Intel i5-12400F, 16 GB RAM, RTX 3060) :

### Gestion de la Mémoire
- `MAX_TRANSACTION_HISTORY=10000` - Limite l'historique des transactions stocké en mémoire
- `MAX_TOKEN_CACHE_SIZE=2000` - Limite le nombre de tokens en cache
- `MAX_BLACKLIST_SIZE=10000` - Limite la taille de la liste noire
- `MAX_CACHED_OPPORTUNITIES=5000` - Limite le nombre d'opportunités en cache

### Connexions RPC
- `RPC_CONNECTION_LIMIT=36` - Limite le nombre total de connexions RPC
- `RPC_MAX_CONNECTIONS_PER_HOST=10` - Limite le nombre de connexions par hôte
- `RPC_SESSION_REFRESH_INTERVAL=3600` - Intervalle de rafraîchissement des sessions en secondes

### Machine Learning
- `ML_MAX_MEMORY_USAGE=4060` - Limite l'utilisation de la mémoire pour le ML (en MB)
- `ML_MAX_MODEL_SIZE=1015` - Taille maximale du modèle (en MB)
- `ML_BATCH_SIZE=64` - Taille des lots pour l'entraînement
- `ML_GPU_ACCELERATION=auto` - Utilisation automatique du GPU pour l'accélération
- `ML_MAX_GPU_MEMORY_MB=9830` - Limite de mémoire GPU pour le ML (en MB)

## Utilisation du Moniteur de Performances

Le script `monitor_performance.py` vous permet de surveiller l'utilisation des ressources système pendant l'exécution de GBPBot.

### Prérequis

Installez les dépendances nécessaires :

```bash
pip install psutil matplotlib
# Pour la surveillance GPU
pip install torch
```

### Lancement du Moniteur

Pour lancer le moniteur avec interface graphique (recommandé) :

```bash
python monitor_performance.py
```

Pour lancer le moniteur en arrière-plan (mode serveur) :

```bash
python monitor_performance.py --no-gui
```

Pour surveiller un processus GBPBot spécifique avec son PID :

```bash
python monitor_performance.py --pid 1234
```

### Interprétation des Résultats

Le moniteur affiche trois graphiques en temps réel :

1. **Utilisation CPU** - Montre le pourcentage d'utilisation du CPU
2. **Utilisation Mémoire** - Montre le pourcentage d'utilisation de la RAM
3. **Utilisation GPU** - Montre l'utilisation du GPU et de sa mémoire

Les données sont également enregistrées dans le fichier `gbpbot_performance.log` pour analyse ultérieure.

## Ajustement des Paramètres

Si vous constatez des problèmes de performances, vous pouvez ajuster les paramètres dans le fichier `.env` :

### Si la mémoire est trop utilisée (>90%)

```
MAX_TRANSACTION_HISTORY=5000  # Réduire de moitié
MAX_TOKEN_CACHE_SIZE=1000     # Réduire de moitié
MAX_CACHED_OPPORTUNITIES=2500 # Réduire de moitié
```

### Si le CPU est saturé (>95% en continu)

```
RPC_CONNECTION_LIMIT=18       # Réduire de moitié
ML_BATCH_SIZE=32              # Réduire de moitié
```

### Si le GPU est sous-utilisé (<30%)

```
ML_GPU_ACCELERATION=force     # Forcer l'utilisation du GPU
ML_MAX_GPU_MEMORY_MB=12000    # Augmenter la mémoire GPU allouée
```

## Dépannage

### Le bot est lent ou se bloque

1. Lancez le moniteur de performances pour identifier le goulot d'étranglement
2. Vérifiez les logs dans `gbpbot_performance.log`
3. Ajustez les paramètres correspondants dans le fichier `.env`

### Erreurs de mémoire insuffisante

Réduisez les valeurs de `MAX_*` dans le fichier `.env` et redémarrez le bot.

### Le moniteur ne détecte pas le GPU

1. Vérifiez que PyTorch est installé : `pip install torch`
2. Vérifiez que les pilotes NVIDIA sont à jour
3. Exécutez `nvidia-smi` pour confirmer que le GPU est détecté par le système

### Le moniteur ne trouve pas le processus GBPBot

Spécifiez manuellement le PID du processus :
```bash
# Trouvez d'abord le PID
tasklist | findstr python
# Puis lancez le moniteur avec ce PID
python monitor_performance.py --pid VOTRE_PID
```

---

Pour toute question ou problème supplémentaire, consultez la documentation complète de GBPBot ou ouvrez une issue sur le dépôt du projet. 