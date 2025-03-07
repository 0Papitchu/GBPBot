# Guide de Lancement du GBPBot

Ce document explique les différentes méthodes pour lancer le GBPBot et ses composants.

## 🚀 Options de Lancement

Le GBPBot dispose de plusieurs scripts de lancement adaptés à différents systèmes d'exploitation et cas d'utilisation:

### 1. Scripts Principaux Recommandés

#### Pour Windows:
```batch
start_gbpbot.bat
```

#### Pour Linux/macOS:
```bash
./start_gbpbot.sh
```

Ces scripts vérifient l'environnement, installent les dépendances nécessaires et offrent un menu interactif avec les options suivantes:
- Mode normal (CLI)
- Mode simulation (sans transactions réelles)
- Mode debug (logs supplémentaires)
- Dashboard web
- Quitter

### 2. Scripts Python Spécifiques

#### Script principal du bot:
```bash
python run_gbpbot.py [options]
```

Options disponibles:
- `--mode {cli,dashboard,auto,telegram}`: Mode de fonctionnement
- `--debug`: Active les logs détaillés
- `--simulation`: Lance le bot en mode simulation (sans transactions réelles)
- `--optimize`: Active les optimisations matérielles
- `--blockchains BLOCKCHAINS`: Liste des blockchains à utiliser (séparées par des virgules)

#### Dashboard uniquement:
```bash
python gbpbot/dashboard/run_dashboard.py [options]
```

Options disponibles:
- `--host HOST`: Adresse d'hôte (défaut: 0.0.0.0)
- `--port PORT`: Port d'écoute (défaut: 8000)
- `--simulate`: Active la génération de métriques simulées pour les tests
- `--log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}`: Niveau de log

### 3. Script Unifié Alternatif

```bash
python run_bot.py
```

Ce script offre une interface unifiée qui:
- Vérifie et installe automatiquement les dépendances manquantes
- Propose de lancer le dashboard en parallèle
- Affiche un menu interactif pour gérer le bot

## 🔧 Choix de la Méthode de Lancement

### Méthode recommandée
- **Utilisateurs Windows**: Utilisez `start_gbpbot.bat`
- **Utilisateurs Linux/macOS**: Utilisez `start_gbpbot.sh`

Ces scripts sont optimisés pour chaque système d'exploitation et offrent la meilleure expérience utilisateur avec une interface colorée, une gestion des erreurs robuste et une configuration guidée.

### Cas d'utilisation spécifiques
- **Lancement du dashboard uniquement**: Utilisez `python gbpbot/dashboard/run_dashboard.py`
- **Intégration dans des scripts personnalisés**: Utilisez `run_gbpbot.py` avec les options appropriées
- **Développement et tests**: Utilisez `run_bot.py` qui offre une expérience simplifiée

## 📋 Exemple de Configuration

Avant de lancer le GBPBot, assurez-vous d'avoir un fichier `.env` correctement configuré avec vos clés API, préférences de trading, etc.

Vous pouvez générer ce fichier en exécutant:
```bash
python scripts/setup_run_environment.py
```

## 🔍 Vérification du Système

Pour vérifier que votre système est correctement configuré pour exécuter le GBPBot:
```bash
python scripts/system_check.py
```

Ce script vérifiera:
- La version de Python
- Les dépendances requises
- Les connexions aux blockchains
- Les capacités GPU pour l'IA
- Les permissions de stockage

## 🛠️ Dépannage

1. **Problèmes de dépendances**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Erreurs d'affichage des emojis dans les logs**:
   Sur Windows, utilisez un terminal qui supporte UTF-8 comme Windows Terminal.

3. **Le dashboard ne se lance pas**:
   Vérifiez que les modules `fastapi` et `uvicorn` sont installés:
   ```bash
   pip install fastapi uvicorn websockets
   ```

4. **Problèmes de connexion aux API blockchain**:
   Vérifiez vos clés API et connexion internet.

## 🔄 Options Avancées

Pour les utilisateurs avancés, vous pouvez personnaliser le comportement du GBPBot en:

1. Créant des scripts batch/shell personnalisés basés sur les existants
2. Modifiant directement les scripts Python
3. Utilisant les modules Python du GBPBot dans vos propres applications 