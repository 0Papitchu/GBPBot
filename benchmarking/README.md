# GBPBot - Suite de Benchmarking

Ce répertoire contient une collection d'outils pour benchmarker les performances de votre système et des réseaux blockchain, spécifiquement conçus pour optimiser GBPBot pour une utilisation locale.

## Objectif

Ces scripts de benchmarking vous permettent de:

1. Évaluer les capacités de votre PC pour exécuter GBPBot
2. Identifier les meilleurs endpoints RPC pour Solana
3. Analyser les performances des DEX Solana
4. Comprendre les caractéristiques des transactions Solana pour optimiser le sniping

## Prérequis

- Python 3.7 ou supérieur
- Connexion Internet stable
- Permissions pour installer des packages Python

## Installation

Toutes les dépendances peuvent être installées automatiquement par le script principal. Les packages nécessaires sont:

- `psutil` - Pour les métriques système
- `aiohttp` - Pour les requêtes HTTP asynchrones
- `speedtest-cli` - Pour les tests de vitesse Internet
- `matplotlib` - Pour la génération de graphiques
- `pandas` - Pour l'analyse des données

## Scripts disponibles

### system_benchmark.py

Évalue les performances de votre PC, incluant:
- CPU (charge, vitesse)
- RAM (disponibilité, vitesse)
- Stockage (vitesse de lecture/écriture)
- Réseau (bande passante, latence)

### blockchain_benchmark.py

Teste différents endpoints RPC Solana pour:
- Temps de réponse
- Fiabilité
- Limites de taux
- Fonctionnalités spécifiques

### dex_benchmark.py

Analyse les DEX Solana pour:
- Disponibilité des paires de trading
- Temps de réponse des API
- Précision des prix
- Profondeur de liquidité

### transaction_benchmark.py

Mesure les caractéristiques des transactions Solana:
- Temps moyen entre les blocs
- Temps de confirmation des transactions
- Opportunités MEV potentielles
- Impact des frais de priorité

### run_benchmarks.py

Script principal qui coordonne tous les benchmarks et génère un rapport consolidé.

## Utilisation

```bash
# Exécuter tous les benchmarks
python run_benchmarks.py --all

# Exécuter un benchmark spécifique
python run_benchmarks.py --system
python run_benchmarks.py --blockchain
python run_benchmarks.py --dex
python run_benchmarks.py --transaction

# Générer uniquement le rapport à partir des résultats existants
python run_benchmarks.py --report
```

## Interprétation des résultats

Les résultats sont sauvegardés dans plusieurs formats:

1. Fichiers JSON individuels pour chaque benchmark
2. Un rapport consolidé dans `benchmark_results/consolidated_results.json`
3. Graphiques et tableaux HTML dans `benchmark_results/charts/`

### Recommandations pour GBPBot

En fonction des résultats du benchmark, vous devriez:

#### Si votre PC a des ressources limitées:
- Réduire le nombre de paires surveillées dans le module d'arbitrage
- Utiliser le endpoint RPC le plus rapide identifié par le benchmark
- Limiter la profondeur de l'historique stocké
- Activer le mode d'économie de ressources

#### Si vous avez une bande passante réseau limitée:
- Augmenter l'intervalle entre les requêtes API
- Mettre en cache aggressivement les données
- Utiliser des WebSockets plutôt que le polling
- Limiter les connexions parallèles

#### Pour un sniping optimal:
- Utiliser le endpoint RPC le plus rapide
- Configurer les frais de priorité en fonction des résultats du benchmark
- Soumettre les transactions juste après l'apparition d'un nouveau bloc
- Cibler les DEX avec les temps de réponse les plus rapides

## Fréquence d'exécution

Il est recommandé d'exécuter ces benchmarks:
- Lors de la configuration initiale de GBPBot
- Après chaque mise à jour majeure du système
- Périodiquement (une fois par mois) pour réévaluer les performances
- Lorsque de nouveaux endpoints RPC ou DEX deviennent disponibles

## Dépannage

Si vous rencontrez des problèmes:

1. Assurez-vous que toutes les dépendances sont correctement installées
2. Vérifiez votre connexion Internet
3. Exécutez les benchmarks individuellement pour isoler le problème
4. Consultez les fichiers de résultats JSON pour des messages d'erreur spécifiques

## Contribution

Pour contribuer à l'amélioration de ces scripts:

1. Ajoutez de nouveaux tests ou métriques
2. Optimisez les scripts existants
3. Améliorez la visualisation des résultats
4. Signalez les bugs ou problèmes

## Sécurité

Ces scripts ne stockent ni n'envoient aucune donnée en dehors de votre système local. Tous les résultats sont sauvegardés uniquement sur votre machine.

---

*Note: Ces benchmarks sont conçus pour donner des indications, pas des garanties absolues. Les performances réelles peuvent varier en fonction des conditions du réseau et de la blockchain.* 