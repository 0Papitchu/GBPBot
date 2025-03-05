# Procédures de Rollback Complètes pour GBPBot

Ce document détaille les procédures de rollback à suivre en cas de problèmes lors de l'exécution de GBPBot. Ces procédures sont essentielles pour garantir la sécurité des fonds et la stabilité du système.

## Table des matières

1. [Scénarios d'urgence](#scénarios-durgence)
2. [Outils de détection et d'analyse](#outils-de-détection-et-danalyse)
3. [Procédures de rollback automatiques](#procédures-de-rollback-automatiques)
4. [Procédures de rollback manuelles](#procédures-de-rollback-manuelles)
5. [Scripts de rollback](#scripts-de-rollback)
6. [Vérifications post-rollback](#vérifications-post-rollback)
7. [Reprise des opérations](#reprise-des-opérations)
8. [Contacts d'urgence](#contacts-durgence)

## Scénarios d'urgence

### 1. Anomalies de prix

**Détection** : Écart de prix anormal entre les sources (> 5%)

**Impact potentiel** : Exécution de trades basés sur des données erronées

**Niveau de gravité** : Élevé

**Outils de détection** :
- Monitoring en temps réel via le dashboard
- Alertes configurées dans `BotMonitor` et `AdvancedMonitor`
- Logs avec le mot-clé "price deviation" ou "anomaly"

### 2. Problèmes de liquidité

**Détection** : Liquidité insuffisante pour exécuter un trade

**Impact potentiel** : Slippage excessif, transactions bloquées

**Niveau de gravité** : Moyen

**Outils de détection** :
- Monitoring de la liquidité via `TradeProtection`
- Logs avec le mot-clé "liquidity" ou "slippage"

### 3. Attaques MEV détectées

**Détection** : Patterns suspects dans les transactions du mempool

**Impact potentiel** : Perte de fonds due au frontrunning ou sandwich attacks

**Niveau de gravité** : Critique

**Outils de détection** :
- Protection MEV intégrée dans `TradeProtection`
- Logs avec le mot-clé "MEV" ou "attack"

### 4. Problèmes de connectivité RPC

**Détection** : Taux d'erreur RPC > 20%

**Impact potentiel** : Transactions incomplètes, données obsolètes

**Niveau de gravité** : Moyen

**Outils de détection** :
- Monitoring RPC via `RPCManager`
- Logs avec le mot-clé "RPC error" ou "connection"

### 5. Gas excessif

**Détection** : Prix du gas > 500 Gwei

**Impact potentiel** : Coûts de transaction prohibitifs

**Niveau de gravité** : Moyen

**Outils de détection** :
- Monitoring du gas via `GasManager`
- Logs avec le mot-clé "gas price" ou "high gas"

### 6. Erreurs de transaction

**Détection** : Taux d'échec des transactions > 30%

**Impact potentiel** : Perte de fonds, transactions partiellement exécutées

**Niveau de gravité** : Élevé

**Outils de détection** :
- Monitoring des transactions via `TradeExecutor`
- Logs avec le mot-clé "transaction failed" ou "error"

### 7. Perte de fonds

**Détection** : Baisse du solde du wallet > 5% sans transactions correspondantes

**Impact potentiel** : Perte financière directe

**Niveau de gravité** : Critique

**Outils de détection** :
- Monitoring du solde via `BotMonitor` et `AdvancedMonitor`
- Logs avec le mot-clé "balance" ou "funds"

## Outils de détection et d'analyse

### Monitoring en temps réel

Le dashboard de monitoring en temps réel est accessible via :

```bash
python scripts/start_bot.py --config=config/active_config.yaml --dashboard --dashboard-port=8080
```

Le dashboard affiche :
- État actuel du bot
- Métriques de performance
- Alertes actives
- Historique des transactions
- Logs en temps réel

### Analyse des logs

L'outil d'analyse des logs permet d'identifier rapidement les causes d'un incident :

```bash
# Analyse des logs pour une période spécifique
python scripts/analyze_logs.py --from="2023-04-01T10:00:00" --to="2023-04-01T11:00:00"

# Analyse des logs pour un niveau spécifique
python scripts/analyze_logs.py --level=error

# Analyse des logs pour un module spécifique
python scripts/analyze_logs.py --module=trade_executor

# Recherche d'un mot-clé spécifique
python scripts/analyze_logs.py --keyword="transaction failed"

# Affichage détaillé des erreurs
python scripts/analyze_logs.py --show-errors
```

L'outil génère un rapport complet dans le répertoire `reports/` avec :
- Résumé des erreurs
- Statistiques des opportunités
- Analyse des transactions
- Graphiques de performance

## Procédures de rollback automatiques

GBPBot intègre un système de rollback automatique via l'`EmergencySystem` pour les scénarios les plus critiques.

### Activation du mode d'urgence

Le mode d'urgence est activé automatiquement lorsque :
- Une anomalie de prix critique est détectée
- Une attaque MEV est identifiée
- Une perte de fonds inexpliquée est détectée
- Le taux d'erreur des transactions dépasse le seuil critique

### Actions automatiques

1. **Arrêt immédiat des nouvelles transactions**
   - Toutes les nouvelles opportunités d'arbitrage sont ignorées
   - Les transactions en attente sont annulées si possible

2. **Sécurisation des positions ouvertes**
   - Clôture des positions avec stop-loss d'urgence
   - Utilisation de gas prioritaire pour garantir l'exécution

3. **Notification d'urgence**
   - Alerte envoyée via tous les canaux configurés
   - Journalisation détaillée de l'incident

### Configuration du système d'urgence

Les seuils d'activation du système d'urgence sont configurables dans le fichier de configuration :

```yaml
security:
  max_price_change: 0.05  # 5% de changement de prix maximum
  min_liquidity: 100      # Liquidité minimum en ETH
  max_gas_price_gwei: 500 # Prix du gas maximum en Gwei
  emergency_shutdown_threshold: 0.1  # 10% de perte de fonds maximum
```

## Procédures de rollback manuelles

En cas d'échec des procédures automatiques ou pour les scénarios non couverts, suivez ces procédures manuelles.

### 1. Arrêt d'urgence du bot

```bash
# Arrêt immédiat du bot avec raison
python scripts/emergency_stop.py --reason="[RAISON]" --notify=true

# Arrêt immédiat du bot avec niveau de gravité
python scripts/emergency_stop.py --reason="[RAISON]" --severity=critical --notify=true

# Vérification de l'état
python scripts/check_status.py
```

L'arrêt d'urgence effectue les actions suivantes :
1. Arrête toutes les activités du bot
2. Annule les transactions en attente
3. Enregistre l'incident dans `data/incidents/`
4. Envoie des notifications selon la configuration

### 2. Analyse de l'incident

```bash
# Analyse des logs autour de l'incident
python scripts/analyze_logs.py --from="[TIMESTAMP_DEBUT]" --to="[TIMESTAMP_FIN]" --level=error

# Génération d'un rapport d'incident
python scripts/analyze_logs.py --from="[TIMESTAMP_DEBUT]" --to="[TIMESTAMP_FIN]" --output="reports/incident_[DATE].txt"
```

L'analyse doit se concentrer sur :
- La cause racine de l'incident
- L'impact sur les fonds et les transactions
- Les modules affectés
- Les actions correctives nécessaires

### 3. Récupération des fonds

#### 3.1 Transfert d'urgence vers un wallet sécurisé

```bash
# Transfert de tous les tokens vers le wallet de secours
python scripts/emergency_transfer.py --to="[ADRESSE_WALLET_SECOURS]" --gas-priority=high

# Transfert d'un token spécifique
python scripts/emergency_transfer.py --to="[ADRESSE_WALLET_SECOURS]" --token="[ADRESSE_TOKEN]" --gas-priority=high
```

Le script `emergency_transfer.py` effectue les actions suivantes :
1. Vérifie le solde de tous les tokens configurés
2. Calcule le gas nécessaire pour les transferts
3. Transfère d'abord les tokens ERC-20, puis l'ETH
4. Enregistre les détails des transferts dans `data/transfers/`

#### 3.2 Annulation des transactions en attente

```bash
# Liste des transactions en attente
python scripts/list_pending_tx.py

# Annulation avec remplacement par gas plus élevé
python scripts/cancel_tx.py --nonce=[NONCE] --gas-boost=1.5

# Annulation de toutes les transactions en attente
python scripts/cancel_tx.py --all --gas-boost=2.0
```

Le script `cancel_tx.py` utilise la technique de remplacement de transaction avec le même nonce mais un gas price plus élevé pour annuler les transactions en attente.

### 4. Diagnostic et correction

```bash
# Vérification de l'intégrité de la configuration
python scripts/validate_config.py --config="[CONFIG_PATH]" --test-connections

# Vérification de l'intégrité de la base de données
python scripts/check_db_integrity.py

# Correction automatique des problèmes courants
python scripts/repair_config.py
```

Le diagnostic doit identifier :
- Les problèmes de configuration
- Les problèmes de connectivité
- Les problèmes de code
- Les problèmes de données

### 5. Redémarrage contrôlé

```bash
# Redémarrage en mode surveillance uniquement
python scripts/start_bot.py --config="[CONFIG_PATH]" --mode=monitor-only

# Redémarrage en mode test
python scripts/start_bot.py --config="[CONFIG_PATH]" --test-mode --simulation-only

# Redémarrage complet après validation
python scripts/start_bot.py --config="[CONFIG_PATH]" --mode=normal
```

Le redémarrage doit être progressif :
1. D'abord en mode surveillance pour vérifier la détection d'opportunités
2. Puis en mode test avec simulation pour vérifier l'exécution
3. Enfin en mode normal si tout fonctionne correctement

## Scripts de rollback

GBPBot inclut plusieurs scripts pour faciliter les procédures de rollback :

### emergency_stop.py

Arrête immédiatement toutes les activités du bot et enregistre la raison.

```python
# Exemple d'utilisation
python scripts/emergency_stop.py --reason="Anomalie de prix détectée" --notify=true --severity=high
```

Options principales :
- `--reason` : Raison de l'arrêt d'urgence
- `--notify` : Envoyer des notifications
- `--severity` : Niveau de gravité (low, medium, high, critical)
- `--config` : Chemin vers le fichier de configuration

### emergency_transfer.py

Transfère tous les actifs vers une adresse sécurisée.

```python
# Exemple d'utilisation
python scripts/emergency_transfer.py --to="0x123..." --gas-priority=high --dry-run
```

Options principales :
- `--to` : Adresse de destination
- `--token` : Adresse du token à transférer (tous par défaut)
- `--gas-priority` : Priorité du gas (low, medium, high)
- `--dry-run` : Simulation sans exécution réelle
- `--config` : Chemin vers le fichier de configuration

### cancel_tx.py

Annule une transaction en attente en envoyant une transaction avec le même nonce et un gas plus élevé.

```python
# Exemple d'utilisation
python scripts/cancel_tx.py --nonce=42 --gas-boost=1.5
```

Options principales :
- `--nonce` : Nonce de la transaction à annuler
- `--all` : Annuler toutes les transactions en attente
- `--gas-boost` : Facteur d'augmentation du gas
- `--config` : Chemin vers le fichier de configuration

### analyze_logs.py

Analyse les logs pour identifier les causes d'un incident.

```python
# Exemple d'utilisation
python scripts/analyze_logs.py --from="2023-04-01T10:00:00" --to="2023-04-01T11:00:00" --level=ERROR
```

Options principales :
- `--from` : Timestamp de début
- `--to` : Timestamp de fin
- `--level` : Niveau de log à filtrer
- `--module` : Module à filtrer
- `--keyword` : Mot-clé à rechercher
- `--show-errors` : Afficher les détails des erreurs
- `--output` : Chemin de sortie pour le rapport

## Vérifications post-rollback

Après l'exécution d'une procédure de rollback, effectuez ces vérifications :

### 1. Vérification des fonds

```bash
# Vérification des soldes
python scripts/check_balances.py

# Réconciliation des transactions
python scripts/reconcile_transactions.py --from="[TIMESTAMP_DEBUT]"
```

La vérification doit confirmer :
- Que tous les fonds sont sécurisés
- Que toutes les transactions sont dans un état final (succès ou échec)
- Qu'il n'y a pas de transactions en attente

### 2. Analyse des causes

Utilisez l'outil d'analyse des logs pour comprendre ce qui s'est passé :

```bash
python scripts/analyze_logs.py --from="[TIMESTAMP_INCIDENT-1h]" --to="[TIMESTAMP_INCIDENT+1h]" --show-errors
```

L'analyse doit identifier :
- La séquence d'événements qui a conduit à l'incident
- Les conditions de marché au moment de l'incident
- Les potentielles failles de sécurité ou bugs

### 3. Mise à jour des paramètres

Ajustez les paramètres de sécurité en fonction de l'incident :

```bash
# Mise à jour des seuils de sécurité
python scripts/update_config.py --param="security.max_price_change" --value=0.01

# Mise à jour des paramètres de monitoring
python scripts/update_config.py --param="monitoring.alert_thresholds.error_rate" --value=0.2
```

Les paramètres à ajuster dépendent de la nature de l'incident :
- Pour les anomalies de prix : réduire `max_price_change`
- Pour les problèmes de liquidité : augmenter `min_liquidity`
- Pour les problèmes de gas : ajuster `max_gas_price_gwei`
- Pour les erreurs de transaction : réduire `max_pending_transactions`

### 4. Test de validation

Avant de reprendre les opérations normales :

```bash
# Test en mode simulation
python scripts/start_bot.py --config="[CONFIG_PATH]" --mode=normal --test-mode --simulation-only --duration=3600

# Vérification des résultats
python scripts/validate_simulation.py --from="[TIMESTAMP_DEBUT]"
```

Le test doit confirmer :
- Que le bot fonctionne correctement avec les nouveaux paramètres
- Que les mécanismes de sécurité fonctionnent comme prévu
- Que les performances sont acceptables

## Reprise des opérations

Après avoir validé que tout fonctionne correctement, vous pouvez reprendre les opérations normales :

### 1. Déploiement progressif

```bash
# Démarrage avec capital limité
python scripts/start_bot.py --config="[CONFIG_PATH]" --mode=normal --max-capital=50

# Démarrage complet
python scripts/start_bot.py --config="[CONFIG_PATH]" --mode=normal
```

Le déploiement doit être progressif :
1. D'abord avec un capital limité pour vérifier le comportement en conditions réelles
2. Puis avec le capital complet si tout fonctionne correctement

### 2. Surveillance renforcée

```bash
# Démarrage avec dashboard de monitoring
python scripts/start_bot.py --config="[CONFIG_PATH]" --mode=normal --dashboard --dashboard-port=8080
```

Pendant les premières 24-48 heures après un incident, maintenez une surveillance renforcée :
- Vérifiez régulièrement le dashboard
- Analysez les logs plus fréquemment
- Soyez prêt à intervenir rapidement en cas de problème

### 3. Documentation de l'incident

Créez un rapport d'incident détaillé pour référence future :

```bash
# Génération d'un rapport d'incident
python scripts/generate_incident_report.py --incident-id=[ID_INCIDENT] --output="reports/incident_[ID_INCIDENT].pdf"
```

Le rapport doit inclure :
- La chronologie de l'incident
- Les causes identifiées
- Les actions prises
- Les leçons apprises
- Les mesures préventives mises en place

## Contacts d'urgence

En cas d'incident critique nécessitant une intervention immédiate :

- **Administrateur système** : admin@example.com | +33 6 12 34 56 78
- **Responsable sécurité** : security@example.com | +33 6 98 76 54 32
- **Support technique** : support@example.com | +33 6 45 67 89 01

---

**Note importante** : Ces procédures doivent être testées régulièrement dans un environnement de test pour garantir leur efficacité en situation réelle. Utilisez le script `setup_test_env.py` pour configurer un environnement de test approprié. 