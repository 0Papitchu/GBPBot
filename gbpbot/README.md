# GBPBot - Système de Trading Automatisé

GBPBot est un système de trading automatisé pour les crypto-monnaies, avec une interface de contrôle complète via API et dashboard web.

## Fonctionnalités

- **Bot de Trading** : Exécution automatique de stratégies de trading
- **API REST** : Contrôle complet du bot via une API sécurisée
- **Dashboard Web** : Interface utilisateur intuitive pour surveiller et contrôler le bot
- **Modes d'exécution** : TEST, SIMULATION et LIVE pour une progression sécurisée
- **Stratégies multiples** : Sniping, Arbitrage et MEV

## Installation

1. Clonez ce dépôt :
```
git clone https://github.com/votre-username/gbpbot.git
cd gbpbot
```

2. Installez les dépendances :
```
pip install -r requirements.txt
```

## Démarrage rapide

Pour démarrer l'API et le dashboard en même temps :

```
python start_servers.py
```

Ou démarrez-les séparément :

```
# Terminal 1 - API
python api_server.py

# Terminal 2 - Dashboard
python web_dashboard.py
```

Accédez au dashboard via votre navigateur : http://127.0.0.1:5001

## Configuration

### Clé API

Pour sécuriser l'API, modifiez la clé API dans les fichiers suivants :
- `api_server.py`
- `web_dashboard.py`
- `templates/dashboard.html`

```python
API_KEY = "votre_clé_api_sécurisée"
```

### Modes d'exécution

- **TEST** : Aucune transaction réelle, simulation complète
- **SIMULATION** : Utilise des données réelles mais n'exécute pas de transactions
- **LIVE** : Mode réel, exécute des transactions avec de vrais fonds

### Stratégies

- **Sniping** : Détecte et exploite les opportunités rapides
- **Arbitrage** : Exploite les différences de prix entre les plateformes
- **MEV (Miner Extractable Value)** : Exploite les opportunités avancées

## API REST

L'API est accessible sur http://127.0.0.1:5000

### Endpoints principaux

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/status` | GET | Obtenir l'état actuel du bot |
| `/trades` | GET | Obtenir la liste des transactions |
| `/performance` | GET | Obtenir les données de performance |
| `/start_sniping` | POST | Activer la stratégie de sniping |
| `/stop_sniping` | POST | Désactiver la stratégie de sniping |
| `/start_arbitrage` | POST | Activer la stratégie d'arbitrage |
| `/stop_arbitrage` | POST | Désactiver la stratégie d'arbitrage |
| `/start_mev` | POST | Activer la stratégie MEV |
| `/stop_mev` | POST | Désactiver la stratégie MEV |
| `/stop_bot` | POST | Arrêter le bot |
| `/reset_bot` | POST | Réinitialiser les statistiques |
| `/change_mode` | POST | Changer le mode (TEST, SIMULATION, LIVE) |

### Exemple d'utilisation avec curl

```bash
# Obtenir le statut
curl -H "x-api-key: your_secure_api_key_here" http://127.0.0.1:5000/status

# Activer le sniping
curl -X POST -H "x-api-key: your_secure_api_key_here" http://127.0.0.1:5000/start_sniping

# Changer le mode
curl -X POST -H "Content-Type: application/json" -H "x-api-key: your_secure_api_key_here" -d '{"mode":"SIMULATION"}' http://127.0.0.1:5000/change_mode
```

## Dashboard Web

Le dashboard est accessible sur http://127.0.0.1:5001

### Fonctionnalités du dashboard

- Affichage en temps réel de l'état du bot
- Contrôle des modes d'exécution
- Activation/désactivation des stratégies
- Visualisation des performances avec graphiques
- Historique des transactions

## Sécurité

- L'API est sécurisée par une clé API
- Limitation du nombre de requêtes pour prévenir les abus
- Confirmation requise pour le mode LIVE
- Journalisation détaillée des actions

## Dépannage

### Problèmes de pare-feu

Si vous rencontrez des problèmes de connexion, vérifiez que votre pare-feu autorise les connexions sur les ports 5000 et 5001.

### Erreurs de connexion à l'API

Vérifiez que :
1. Le serveur API est bien démarré
2. La clé API est correcte dans tous les fichiers
3. Vous utilisez la bonne URL (http://127.0.0.1:5000)

## Licence

Ce projet est sous licence MIT. Voir le fichier LICENSE pour plus de détails. 