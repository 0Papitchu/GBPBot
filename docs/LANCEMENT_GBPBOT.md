# Guide de Lancement de GBPBot

Ce document explique les différentes méthodes disponibles pour lancer GBPBot, leurs avantages, et quand utiliser chacune d'elles.

## 🌟 Méthode Recommandée - Scripts Unifiés

Les scripts de lancement unifiés sont la méthode **recommandée** pour démarrer GBPBot. Ils offrent une expérience cohérente sur toutes les plateformes et gèrent automatiquement l'environnement, les dépendances et la configuration.

### Pour Windows
```bash
launch_gbpbot.bat
```
Double-cliquez simplement sur ce fichier ou exécutez-le depuis une invite de commande.

### Pour Linux/macOS
```bash
# Rendre le script exécutable (première fois uniquement)
chmod +x launch_gbpbot.sh

# Lancer GBPBot
./launch_gbpbot.sh
```

### Avantages des scripts unifiés
- ✅ Détection automatique de l'environnement Python
- ✅ Installation des dépendances manquantes
- ✅ Configuration automatique du bot
- ✅ Interface unifiée sur toutes les plateformes
- ✅ Gestion des erreurs avec recommandations
- ✅ Menu interactif intuitif

## 📋 Méthodes de Lancement

| Méthode | Description | Avantages | Cas d'utilisation |
|---------|-------------|-----------|-------------------|
| **Scripts Shell/Batch**<br>`launch_gbpbot.bat`<br>`launch_gbpbot.sh` | Scripts adaptés à chaque OS avec menu interactif | Facilité d'utilisation, intégration OS | Utilisation quotidienne |
| **Python Direct**<br>`gbpbot_launcher.py` | Lanceur Python unifié avec toutes les fonctionnalités | Contrôle des arguments, options avancées | Automatisation, CI/CD |
| **Mode argumenté**<br>`python gbpbot_launcher.py --mode` | Lancement direct avec options | Configuration flexible, intégration avec scripts | Scripting, environnements spécifiques |

## 🚀 Modes de Lancement Disponibles

Quel que soit le script utilisé, GBPBot propose plusieurs modes de lancement :

### 1. Mode Interactif

Interface complète avec menus pour accéder à toutes les fonctionnalités :
- Gestion des modules (Arbitrage, Sniping, Mode Auto)
- Configuration du bot
- Affichage des statistiques et logs
- Gestion avancée des paramètres

**Comment lancer :**
```bash
# Windows
launch_gbpbot.bat
# Puis sélectionner option 1

# Linux/macOS
./launch_gbpbot.sh
# Puis sélectionner option 1

# Direct Python
python gbpbot_launcher.py
```

### 2. Mode CLI Direct

Lance directement l'interface en ligne de commande du bot :

**Comment lancer :**
```bash
# Windows
launch_gbpbot.bat
# Puis sélectionner option 2

# Linux/macOS
./launch_gbpbot.sh
# Puis sélectionner option 2

# Direct Python
python gbpbot_launcher.py --mode cli
```

### 3. Mode Simulation

Lance le bot en mode simulation (sans transactions réelles) :

**Comment lancer :**
```bash
# Windows
launch_gbpbot.bat
# Puis sélectionner option 3

# Linux/macOS
./launch_gbpbot.sh
# Puis sélectionner option 3

# Direct Python
python gbpbot_launcher.py --mode simulation
```

### 4. Mode Dashboard

Lance l'interface web de visualisation :

**Comment lancer :**
```bash
# Windows
launch_gbpbot.bat
# Puis sélectionner option 4

# Linux/macOS
./launch_gbpbot.sh
# Puis sélectionner option 4

# Direct Python
python gbpbot_launcher.py --mode dashboard
```

### 5. Mode AI Assistant

Lance l'assistant IA pour l'analyse de marché et l'évaluation des tokens :

**Comment lancer :**
```bash
# Windows
launch_gbpbot.bat
# Puis sélectionner option 1 dans le menu principal, puis option 4 dans le menu modules

# Linux/macOS
./launch_gbpbot.sh
# Puis sélectionner option 1 dans le menu principal, puis option 4 dans le menu modules

# Direct Python
python gbpbot_launcher.py --mode ai
```

### 6. Mode Backtesting

Lance l'outil de backtesting et simulation sur données historiques :

**Comment lancer :**
```bash
# Windows
launch_gbpbot.bat
# Puis sélectionner option 1 dans le menu principal, puis option 5 dans le menu modules

# Linux/macOS
./launch_gbpbot.sh
# Puis sélectionner option 1 dans le menu principal, puis option 5 dans le menu modules

# Direct Python
python gbpbot_launcher.py --mode backtesting
```

## 💡 Options Avancées (Ligne de Commande)

Pour les utilisateurs avancés, le lanceur Python supporte des options supplémentaires :

```bash
python gbpbot_launcher.py [OPTIONS]

Options:
  --mode MODE     Mode de lancement: cli, dashboard, auto, simulation, ai, backtesting
  --debug         Active les logs détaillés 
  --no-checks     Ignore les vérifications d'environnement
  --config PATH   Utilise un fichier de configuration spécifique
```
## 📱 Structure du Menu Principal

Lorsque vous utilisez le mode interactif, vous accédez au menu principal de GBPBot :

```
============================================================
                    GBPBot - Menu Principal
============================================================
Veuillez choisir une option:
1. Démarrer le Bot
2. Configurer les paramètres
3. Afficher la configuration actuelle
4. Statistiques et Logs
5. Afficher les Modules Disponibles
6. Quitter
```

### Menu Modules

En sélectionnant "Démarrer le Bot", vous accédez au menu de sélection des modules:

```
============================================================
                GBPBot - Sélection de Module
============================================================
1. Arbitrage entre les DEX
2. Sniping de Token
3. Lancer automatiquement le bot
4. AI Assistant
5. Backtesting et Simulation
6. Retour au menu principal
```

## 💡 Bonnes Pratiques

1. **Pour débutants** : Utilisez les scripts batch/shell pour une expérience guidée
2. **Pour une utilisation avancée** : Utilisez directement `gbpbot_launcher.py` avec les options appropriées
3. **Pour l'intégration avec d'autres outils** : Utilisez les options en ligne de commande
4. **Pour les serveurs/VPS** : Configurez une tâche automatisée avec `python gbpbot_launcher.py --mode auto --no-checks`
5. **Pour les tests** : Utilisez `python gbpbot_launcher.py --mode simulation --debug`

## 🛠️ Résolution des Problèmes Courants

Si vous rencontrez des problèmes lors du lancement, essayez les solutions suivantes :

1. **Le bot ne démarre pas** :
   - Vérifiez que Python 3.8+ est correctement installé
   - Assurez-vous que toutes les dépendances sont installées avec `pip install -r requirements.txt`
   - Vérifiez que le fichier `.env` est correctement configuré

2. **Erreurs d'importation** :
   - Le lanceur devrait installer automatiquement les dépendances manquantes
   - Si des erreurs persistent, exécutez manuellement `pip install -r requirements.txt`

3. **Problèmes avec asyncio** (Windows) :
   - Le lanceur corrige automatiquement les problèmes d'asyncio sur Windows

4. **Erreurs de configuration** :
   - Utilisez l'option "2. Configurer les paramètres" depuis le menu principal
   - Vérifiez le fichier `.env` et assurez-vous que les clés API et paramètres sont corrects

Pour une aide plus détaillée, consultez [TROUBLESHOOTING.md](TROUBLESHOOTING.md). 
