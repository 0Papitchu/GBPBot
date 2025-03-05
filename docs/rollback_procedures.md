# Procédures de Rollback pour GBPBot

Ce document détaille les procédures de rollback à suivre en cas de problèmes lors de l'exécution de GBPBot. Ces procédures sont essentielles pour garantir la sécurité des fonds et la stabilité du système.

## Table des matières

1. [Scénarios d'urgence](#scénarios-durgence)
2. [Procédures de rollback automatiques](#procédures-de-rollback-automatiques)
3. [Procédures de rollback manuelles](#procédures-de-rollback-manuelles)
4. [Scripts de rollback](#scripts-de-rollback)
5. [Vérifications post-rollback](#vérifications-post-rollback)

## Scénarios d'urgence

### 1. Anomalies de prix

**Détection** : Écart de prix anormal entre les sources (> 5%)

**Impact potentiel** : Exécution de trades basés sur des données erronées

**Niveau de gravité** : Élevé

### 2. Problèmes de liquidité

**Détection** : Liquidité insuffisante pour exécuter un trade

**Impact potentiel** : Slippage excessif, transactions bloquées

**Niveau de gravité** : Moyen

### 3. Attaques MEV détectées

**Détection** : Patterns suspects dans les transactions du mempool

**Impact potentiel** : Perte de fonds due au frontrunning ou sandwich attacks

**Niveau de gravité** : Critique

### 4. Problèmes de connectivité RPC

**Détection** : Taux d'erreur RPC > 20%

**Impact potentiel** : Transactions incomplètes, données obsolètes

**Niveau de gravité** : Moyen

### 5. Gas excessif

**Détection** : Prix du gas > 500 Gwei

**Impact potentiel** : Coûts de transaction prohibitifs

**Niveau de gravité** : Moyen

### 6. Erreurs de transaction

**Détection** : Taux d'échec des transactions > 30%

**Impact potentiel** : Perte de fonds, transactions partiellement exécutées

**Niveau de gravité** : Élevé

### 7. Perte de fonds

**Détection** : Baisse du solde du wallet > 5% sans transactions correspondantes

**Impact potentiel** : Perte financière directe

**Niveau de gravité** : Critique

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

## Procédures de rollback manuelles

En cas d'échec des procédures automatiques ou pour les scénarios non couverts, suivez ces procédures manuelles.

### 1. Arrêt d'urgence du bot

```bash
# Arrêt immédiat du bot
python scripts/emergency_stop.py --reason="[RAISON]"

# Vérification de l'état
python scripts/check_status.py
```

### 2. Récupération des fonds

#### 2.1 Transfert d'urgence vers un wallet sécurisé

```bash
# Transfert de tous les tokens vers le wallet de secours
python scripts/emergency_transfer.py --to="[ADRESSE_WALLET_SECOURS]"
```

#### 2.2 Annulation des transactions en attente

```bash
# Liste des transactions en attente
python scripts/list_pending_tx.py

# Annulation avec remplacement par gas plus élevé
python scripts/cancel_tx.py --nonce=[NONCE] --priority=high
```

### 3. Diagnostic et correction

```bash
# Analyse des logs pour identifier la cause
python scripts/analyze_logs.py --from="[TIMESTAMP_DEBUT]" --to="[TIMESTAMP_FIN]"

# Vérification de l'intégrité de la base de données
python scripts/check_db_integrity.py
```

### 4. Redémarrage contrôlé

```bash
# Redémarrage en mode surveillance uniquement
python scripts/start_bot.py --mode=monitor-only

# Redémarrage complet après validation
python scripts/start_bot.py --mode=normal
```

## Scripts de rollback

GBPBot inclut plusieurs scripts pour faciliter les procédures de rollback :

### emergency_stop.py

Arrête immédiatement toutes les activités du bot et enregistre la raison.

```python
# Exemple d'utilisation
python scripts/emergency_stop.py --reason="Anomalie de prix détectée" --notify=true
```

### emergency_transfer.py

Transfère tous les actifs vers une adresse sécurisée.

```python
# Exemple d'utilisation
python scripts/emergency_transfer.py --to="0x123..." --gas-priority=high
```

### cancel_tx.py

Annule une transaction en attente en envoyant une transaction avec le même nonce et un gas plus élevé.

```python
# Exemple d'utilisation
python scripts/cancel_tx.py --nonce=42 --gas-boost=1.5
```

### analyze_logs.py

Analyse les logs pour identifier les causes d'un incident.

```python
# Exemple d'utilisation
python scripts/analyze_logs.py --from="2023-04-01T10:00:00" --to="2023-04-01T11:00:00" --level=ERROR
```

## Vérifications post-rollback

Après l'exécution d'une procédure de rollback, effectuez ces vérifications :

### 1. Vérification des fonds

```bash
# Vérification des soldes
python scripts/check_balances.py

# Réconciliation des transactions
python scripts/reconcile_transactions.py --from="[TIMESTAMP_DEBUT]"
```

### 2. Analyse des causes

- Examinez les logs détaillés
- Vérifiez les conditions de marché au moment de l'incident
- Identifiez les potentielles failles de sécurité

### 3. Mise à jour des paramètres

Ajustez les paramètres de sécurité en fonction de l'incident :

```bash
# Mise à jour des seuils de sécurité
python scripts/update_config.py --param="security.max_price_change" --value=0.01
```

### 4. Test de validation

Avant de reprendre les opérations normales :

```bash
# Test en mode simulation
python scripts/start_bot.py --mode=simulation --duration=3600

# Vérification des résultats
python scripts/validate_simulation.py --from="[TIMESTAMP_DEBUT]"
```

## Contacts d'urgence

En cas d'incident critique nécessitant une intervention immédiate :

- **Administrateur système** : admin@example.com | +33 6 12 34 56 78
- **Responsable sécurité** : security@example.com | +33 6 98 76 54 32
- **Support technique** : support@example.com | +33 6 45 67 89 01

---

**Note importante** : Ces procédures doivent être testées régulièrement dans un environnement de test pour garantir leur efficacité en situation réelle. 