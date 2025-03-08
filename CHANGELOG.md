# Changelog

Tous les changements notables apportés à ce projet seront documentés dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/),
et ce projet adhère au [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.1] - 2025-04-08

### Sécurité
- Mise à jour de `cryptography` vers ≥43.0.1 pour corriger une vulnérabilité d'attaque timing oracle
- Mise à jour de `aiohttp` vers ≥3.10.11 pour corriger une vulnérabilité de DoS dans le traitement multipart/form-data
- Mise à jour de `gunicorn` vers ≥22.0.0 pour corriger une vulnérabilité de HTTP Request Smuggling
- Mise à jour de `pyarrow` vers ≥14.0.1 pour corriger une vulnérabilité critique permettant l'exécution de code arbitraire
- Mise à jour de `eth-abi` vers ≥5.0.1 pour corriger une vulnérabilité DoS récursive
- Mise à jour de `scikit-learn` vers ≥1.5.0 pour corriger une fuite de données sensibles
- Mise à jour de `pymongo` vers ≥4.6.3 pour corriger une vulnérabilité de lecture hors limites
- Mise à jour de `pydantic` vers ≥2.4.0 pour corriger une vulnérabilité de déni de service par expression régulière
- Ajout de fichiers de verrouillage des dépendances (requirements-core.lock) pour permettre à Dependabot de gérer automatiquement les mises à jour de sécurité

## [1.0.0] - 2025-03-04

### Ajouté
- Système de monitoring live avec alertes pour détecter les anomalies et erreurs en temps réel
- Implémentation des stop-loss / take-profit pour éviter des pertes massives
- Protection contre les attaques MEV, sandwich, frontrunning
- Validation complète des transactions simulées pour garantir leur fiabilité
- Système de mise en cache intelligente des appels RPC

### Modifié
- Décomposition de `price_feed.py` en sous-modules pour une meilleure organisation
- Optimisation du `RPCManager` avec suppression des redondances entre `call_rpc()` et `batch_call_rpc()`
- Amélioration de la gestion des erreurs (RPC, WebSockets, API externes)
- Optimisation des boucles pour réduire la consommation CPU
- Gestion optimisée des WebSockets avec suppression des reconnexions inutiles
- Optimisation du moteur d'arbitrage avec amélioration de la détection et normalisation des prix

### Corrigé
- Correction des exceptions silencieuses
- Ajout de validations des entrées et transactions pour éviter les opérations risquées
- Optimisation des frais de gas (EIP-1559) pour réduire les coûts transactionnels
- Vérification et correction de la gestion des fonds

### Sécurité
- Implémentation d'un retry intelligent avec backoff exponentiel pour éviter les appels RPC défectueux
- Amélioration de la détection des prix anormaux pour éviter les faux signaux
- Vérification de la gestion des fonds pour s'assurer que les profits sont bien envoyés au wallet sécurisé 