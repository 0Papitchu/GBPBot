# Guide d'Utilisation des Modules de Monitoring et de Wallets

Ce guide explique comment utiliser les nouveaux modules de monitoring et de gestion des wallets du GBPBot pour améliorer votre expérience de trading.

## Table des matières

1. [Monitoring Système](#1-monitoring-système)
2. [Suivi des Performances de Trading](#2-suivi-des-performances-de-trading)
3. [Gestion des Wallets](#3-gestion-des-wallets)
4. [Intégration avec Telegram](#4-intégration-avec-telegram)
5. [Exemples Pratiques](#5-exemples-pratiques)

## 1. Monitoring Système

Le module `SystemMonitor` vous permet de surveiller les ressources système utilisées par le GBPBot (CPU, mémoire, disque, réseau) et de recevoir des alertes en cas de problème.

### 1.1 Démarrage du Monitoring

```python
from gbpbot.monitoring import get_system_monitor

# Obtenir l'instance du moniteur système
system_monitor = get_system_monitor()

# Démarrer le monitoring avec un intervalle de 5 secondes
system_monitor.start_monitoring(interval=5.0)

# Pour arrêter le monitoring
system_monitor.stop_monitoring()
```

### 1.2 Configuration des Seuils d'Alerte

```python
# Configurer les seuils d'alerte
system_monitor.set_all_thresholds(
    cpu_percent=90.0,  # Alerte à 90% d'utilisation CPU
    memory_percent=85.0,  # Alerte à 85% d'utilisation mémoire
    disk_percent=95.0,  # Alerte à 95% d'utilisation disque
    process_cpu_percent=80.0,  # Alerte à 80% d'utilisation CPU par le processus
    process_memory_percent=80.0  # Alerte à 80% d'utilisation mémoire par le processus
)

# Ou configurer un seuil spécifique
system_monitor.set_threshold("cpu_percent", 85.0)
```

### 1.3 Gestion des Alertes

```python
# Définir un gestionnaire d'alertes
def alert_handler(metric_name, value, threshold):
    print(f"ALERTE: {metric_name} = {value:.2f} (seuil: {threshold:.2f})")
    # Vous pouvez ajouter ici votre propre logique (envoi d'email, SMS, etc.)

# Enregistrer le gestionnaire
system_monitor.register_alert_callback(alert_handler)

# Supprimer le gestionnaire si nécessaire
system_monitor.unregister_alert_callback(alert_handler)
```

### 1.4 Consultation des Métriques

```python
# Obtenir toutes les métriques
metrics = system_monitor.get_metrics()
print(f"CPU: {metrics['cpu']['percent']}%")
print(f"Mémoire: {metrics['memory']['percent']}%")
print(f"Disque: {metrics['disk']['percent']}%")

# Obtenir uniquement les informations système
system_info = system_monitor.get_system_info()
print(f"OS: {system_info['platform']} {system_info['platform_release']}")
print(f"Python: {system_info['python_version']}")
print(f"Uptime: {system_info['uptime'] / 3600:.2f} heures")

# Obtenir un résumé de l'utilisation
usage = system_monitor.get_system_usage()
print(f"CPU: {usage['cpu_percent']}%")
print(f"Mémoire: {usage['memory_percent']}%")
print(f"Disque: {usage['disk_percent']}%")
```

### 1.5 Génération de Rapports

```python
# Générer un rapport système
report_path = system_monitor.save_report()
print(f"Rapport sauvegardé dans: {report_path}")

# Générer un rapport avec un nom spécifique
report_path = system_monitor.save_report("rapport_système_20240310.json")
```

### 1.6 Optimisation du Système

```python
# Obtenir des suggestions d'optimisation
optimizations = system_monitor.optimize_system()

# Afficher les suggestions
for suggestion in optimizations["suggestions"]:
    print(f"- {suggestion}")

# Vérifier le statut global
print(f"Statut: {optimizations['status']}")  # 'ok' ou 'warning'
```

## 2. Suivi des Performances de Trading

Le module `PerformanceMonitor` vous permet de suivre et d'analyser les performances de trading du GBPBot.

### 2.1 Ajout et Mise à Jour de Transactions

```python
from gbpbot.monitoring import get_performance_monitor
from gbpbot.monitoring.performance_monitor import TradeRecord
from datetime import datetime

# Obtenir l'instance du moniteur de performance
performance_monitor = get_performance_monitor()

# Créer une transaction
trade = TradeRecord(
    trade_id="tx123",
    token_symbol="SOL",
    blockchain="solana",
    entry_price=100.0,
    amount=1.0,
    strategy="sniping",
    timestamp_start=datetime.now()
)

# Ajouter la transaction
performance_monitor.add_trade(trade)

# Mettre à jour une transaction
performance_monitor.update_trade(
    trade_id="tx123",
    strategy="arbitrage"  # Changer la stratégie
)

# Fermer une transaction (avec profit)
performance_monitor.close_trade(
    trade_id="tx123",
    exit_price=120.0  # 20% de profit
)
```

### 2.2 Consultation des Transactions

```python
# Obtenir une transaction spécifique
trade = performance_monitor.get_trade("tx123")
if trade:
    print(f"Token: {trade.token_symbol}")
    print(f"Profit: {trade.profit_loss}")

# Obtenir toutes les transactions
all_trades = performance_monitor.get_all_trades()
print(f"Nombre total de transactions: {len(all_trades)}")

# Obtenir les transactions ouvertes
open_trades = performance_monitor.get_open_trades()
print(f"Transactions ouvertes: {len(open_trades)}")

# Obtenir les transactions fermées
closed_trades = performance_monitor.get_closed_trades()
print(f"Transactions fermées: {len(closed_trades)}")

# Obtenir les transactions échouées
failed_trades = performance_monitor.get_failed_trades()
print(f"Transactions échouées: {len(failed_trades)}")
```

### 2.3 Analyse des Performances

```python
# Obtenir les statistiques des dernières 24 heures
stats_24h = performance_monitor.get_stats(hours=24)
print(f"Transactions (24h): {stats_24h['total_trades']}")
print(f"Win Rate (24h): {stats_24h['win_rate']:.2f}%")
print(f"Profit (24h): {stats_24h['profit_total']:.2f}")

# Obtenir les statistiques des dernières 7 jours (168 heures)
stats_7d = performance_monitor.get_stats(hours=168)
print(f"Transactions (7j): {stats_7d['total_trades']}")
print(f"Win Rate (7j): {stats_7d['win_rate']:.2f}%")
print(f"Profit (7j): {stats_7d['profit_total']:.2f}")

# Obtenir les statistiques pour une période spécifique
from datetime import datetime, timedelta
start_time = datetime.now() - timedelta(days=30)
end_time = datetime.now()

stats_period = performance_monitor.get_period_stats(start_time, end_time)
print(f"Transactions (période): {stats_period['total_trades']}")
print(f"Win Rate (période): {stats_period['win_rate']:.2f}%")
print(f"Profit (période): {stats_period['profit_total']:.2f}")

# Analyser les performances par blockchain
for blockchain, stats in stats_24h['blockchain_stats'].items():
    print(f"Blockchain: {blockchain}")
    print(f"  Transactions: {stats['trades']}")
    print(f"  Profit: {stats['profit']:.2f}")
    print(f"  Taux de réussite: {stats['success_rate']:.2f}%")

# Analyser les performances par stratégie
for strategy, stats in stats_24h['strategy_stats'].items():
    print(f"Stratégie: {strategy}")
    print(f"  Transactions: {stats['trades']}")
    print(f"  Profit: {stats['profit']:.2f}")
    print(f"  Taux de réussite: {stats['success_rate']:.2f}%")
```

## 3. Gestion des Wallets

Le module `WalletManager` permet de gérer les wallets sur différentes blockchains (Solana, Avalanche, Ethereum, Sonic).

### 3.1 Création et Importation de Wallets

```python
from gbpbot.modules.wallet_manager import get_wallet_manager, WalletConfig

# Obtenir l'instance du gestionnaire de wallets
wallet_manager = get_wallet_manager()

# Créer un nouveau wallet Solana
solana_wallet_id = wallet_manager.create_solana_wallet(label="Solana Principal")
print(f"Wallet Solana créé: {solana_wallet_id}")

# Créer un nouveau wallet AVAX
avax_wallet_id = wallet_manager.create_evm_wallet(blockchain="avax", label="AVAX Principal")
print(f"Wallet AVAX créé: {avax_wallet_id}")

# Créer un nouveau wallet Sonic
sonic_wallet_id = wallet_manager.create_evm_wallet(blockchain="sonic", label="Sonic Principal")
print(f"Wallet Sonic créé: {sonic_wallet_id}")

# Importer un wallet existant à partir d'une clé privée
imported_wallet_id = wallet_manager.import_wallet_from_private_key(
    blockchain="solana",
    private_key="your_private_key_here",
    label="Solana Importé"
)
print(f"Wallet importé: {imported_wallet_id}")
```

### 3.2 Gestion des Wallets

```python
# Obtenir un wallet par ID
wallet = wallet_manager.get_wallet(solana_wallet_id)
if wallet:
    print(f"Blockchain: {wallet.blockchain}")
    print(f"Adresse: {wallet.address}")
    print(f"Label: {wallet.label}")

# Obtenir un wallet par adresse
wallet = wallet_manager.get_wallet_by_address("wallet_address_here", blockchain="solana")
if wallet:
    print(f"ID: {solana_wallet_id}")
    print(f"Label: {wallet.label}")

# Obtenir tous les wallets pour une blockchain
solana_wallets = wallet_manager.get_wallets_for_blockchain("solana")
print(f"Nombre de wallets Solana: {len(solana_wallets)}")

# Définir un wallet comme wallet par défaut
wallet_manager.set_default_wallet(solana_wallet_id)

# Obtenir le wallet par défaut pour une blockchain
default_wallet = wallet_manager.get_default_wallet("solana")
if default_wallet:
    print(f"Wallet par défaut pour Solana: {default_wallet.label}")

# Supprimer un wallet
wallet_manager.remove_wallet(sonic_wallet_id)
```

### 3.3 Gestion des Balances

```python
# Mettre à jour les balances d'un wallet
wallet_manager.update_balances(
    wallet_id=solana_wallet_id,
    balances={
        "SOL": 10.5,
        "USDC": 1000.0,
        "RAY": 250.0
    }
)

# Obtenir les balances d'un token spécifique
sol_balance = wallet_manager.get_balance(solana_wallet_id, "SOL")
print(f"Balance SOL: {sol_balance}")

# Obtenir toutes les balances
all_balances = wallet_manager.get_balances()
for wallet_label, tokens in all_balances.items():
    print(f"Wallet: {wallet_label}")
    for token, amount in tokens.items():
        print(f"  {token}: {amount}")

# Obtenir les balances pour une blockchain spécifique
solana_balances = wallet_manager.get_balances(blockchain="solana")
for wallet_label, tokens in solana_balances.items():
    print(f"Wallet Solana: {wallet_label}")
    for token, amount in tokens.items():
        print(f"  {token}: {amount}")

# Obtenir la balance totale d'un token sur tous les wallets
total_sol = wallet_manager.get_total_balance("SOL")
print(f"Balance totale SOL: {total_sol}")
```

### 3.4 Vérification des Blockchains Supportées

```python
# Obtenir la liste des blockchains supportées
supported_chains = wallet_manager.get_supported_chains()
print(f"Blockchains supportées: {', '.join(supported_chains)}")

# Vérifier si une blockchain est disponible
if wallet_manager.is_wallet_available("solana"):
    print("Au moins un wallet Solana est disponible")
else:
    print("Aucun wallet Solana n'est disponible")
```

## 4. Intégration avec Telegram

Les modules de monitoring et de gestion de wallets sont intégrés à l'interface Telegram du GBPBot, permettant l'accès à distance à ces fonctionnalités.

### 4.1 Commandes de Monitoring Système

- `/status` - Affiche le statut actuel du système (CPU, mémoire, disque)
- `/status_refresh` - Rafraîchit les informations de statut

### 4.2 Commandes de Suivi des Performances

- `/stats` - Affiche les statistiques de performance des dernières 24h
- `/stats 48` - Affiche les statistiques sur 48h
- `/stats 168` - Affiche les statistiques sur 7 jours (168h)

### 4.3 Commandes de Gestion des Wallets

- `/balance` - Affiche les soldes de tous les wallets
- `/balance solana` - Affiche les soldes des wallets Solana
- `/balance avax` - Affiche les soldes des wallets Avalanche
- `/balance sonic` - Affiche les soldes des wallets Sonic

## 5. Exemples Pratiques

### 5.1 Configuration Complète du Monitoring

```python
from gbpbot.monitoring import initialize_monitoring, get_system_monitor, get_performance_monitor
import time
import logging

# Configurer le logging
logging.basicConfig(level=logging.INFO)

# Initialiser tous les moniteurs avec un intervalle de 10 secondes
initialize_monitoring(check_interval=10.0, auto_start=True)

# Obtenir les instances
system_monitor = get_system_monitor()
performance_monitor = get_performance_monitor()

# Configurer les seuils d'alerte
system_monitor.set_all_thresholds(
    cpu_percent=85.0,
    memory_percent=80.0,
    disk_percent=90.0
)

# Définir un gestionnaire d'alertes
def alert_handler(metric_name, value, threshold):
    print(f"ALERTE: {metric_name} = {value:.2f} (seuil: {threshold:.2f})")
    # Vous pourriez envoyer un email ou une notification ici

# Enregistrer le gestionnaire
system_monitor.register_alert_callback(alert_handler)

# Boucle principale
try:
    while True:
        # Obtenir et afficher les métriques actuelles
        usage = system_monitor.get_system_usage()
        print(f"CPU: {usage['cpu_percent']:.2f}%, Mémoire: {usage['memory_percent']:.2f}%")
        
        # Obtenir et afficher les statistiques de trading
        stats = performance_monitor.get_stats(hours=24)
        if stats['total_trades'] > 0:
            print(f"Trades: {stats['total_trades']}, Win Rate: {stats['win_rate']:.2f}%")
        
        # Attendre 30 secondes
        time.sleep(30)
except KeyboardInterrupt:
    print("Arrêt du monitoring...")
    system_monitor.stop_monitoring()
```

### 5.2 Gestion Complète des Wallets

```python
from gbpbot.modules.wallet_manager import get_wallet_manager, WalletConfig
import json

# Obtenir l'instance du gestionnaire de wallets
wallet_manager = get_wallet_manager()

# Fonction pour afficher les informations d'un wallet
def print_wallet_info(wallet_id):
    wallet = wallet_manager.get_wallet(wallet_id)
    if not wallet:
        print(f"Wallet {wallet_id} non trouvé")
        return
    
    print(f"=== Wallet: {wallet.label} ===")
    print(f"Blockchain: {wallet.blockchain}")
    print(f"Adresse: {wallet.address}")
    
    # Obtenir les balances
    balances = wallet_manager.get_balances()
    
    if wallet.label in balances:
        print("Balances:")
        for token, amount in balances[wallet.label].items():
            print(f"  {token}: {amount}")
    else:
        print("Aucune balance disponible")
    print("")

# Créer des wallets pour chaque blockchain supportée
wallets = {
    "solana": None,
    "avax": None,
    "sonic": None
}

# Création des wallets
wallets["solana"] = wallet_manager.create_solana_wallet(label="Solana Trading")
wallets["avax"] = wallet_manager.create_evm_wallet(blockchain="avax", label="AVAX Trading")
wallets["sonic"] = wallet_manager.create_evm_wallet(blockchain="sonic", label="Sonic Trading")

# Définir les wallets par défaut
for blockchain, wallet_id in wallets.items():
    if wallet_id:
        wallet_manager.set_default_wallet(wallet_id)
        print(f"Wallet par défaut pour {blockchain}: {wallet_id}")

# Ajouter des balances fictives
wallet_manager.update_balances(
    wallet_id=wallets["solana"],
    balances={
        "SOL": 15.75,
        "USDC": 2500.0,
        "RAY": 350.0,
        "BONK": 100000.0
    }
)

wallet_manager.update_balances(
    wallet_id=wallets["avax"],
    balances={
        "AVAX": 45.2,
        "USDC.e": 1800.0,
        "JOE": 200.0
    }
)

wallet_manager.update_balances(
    wallet_id=wallets["sonic"],
    balances={
        "SONIC": 100.0,
        "USDC": 500.0
    }
)

# Afficher les informations de tous les wallets
for blockchain, wallet_id in wallets.items():
    if wallet_id:
        print_wallet_info(wallet_id)

# Afficher les balances totales par token
total_balances = {}
for wallet_label, tokens in wallet_manager.get_balances().items():
    for token, amount in tokens.items():
        if token not in total_balances:
            total_balances[token] = 0
        total_balances[token] += amount

print("=== Balances Totales ===")
for token, amount in total_balances.items():
    print(f"{token}: {amount}")
```

Ces exemples vous aideront à intégrer rapidement les modules de monitoring et de gestion des wallets dans votre utilisation du GBPBot pour optimiser votre expérience de trading. 