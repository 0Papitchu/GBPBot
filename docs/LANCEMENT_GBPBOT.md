# Guide de Lancement de GBPBot

Ce document explique en détail les différentes méthodes disponibles pour lancer GBPBot, leurs avantages, et quand utiliser chacune d'elles.

## 🌟 Méthode Recommandée - Scripts Unifiés

Les scripts de lancement unifiés sont la méthode **recommandée** pour démarrer GBPBot. Ils offrent une expérience cohérente sur toutes les plateformes et gèrent automatiquement l'environnement virtuel, les dépendances et la configuration.

### Pour Windows
```launch_gbpbot_cli.bat
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
- ✅ Gestion automatique de l'environnement virtuel Python
- ✅ Installation des dépendances manquantes
- ✅ Vérification et création des fichiers de configuration
- ✅ Menu interactif avec options avancées (mode debug, sans environnement virtuel)
- ✅ Expérience cohérente sur toutes les plateformes
- ✅ Gestion des erreurs et messages d'aide

## 📋 Tableau Comparatif des Méthodes de Lancement

| Méthode | Description | Avantages | Cas d'utilisation |
|---------|-------------|-----------|-------------------|
| Scripts Unifiés<br>(`launch_gbpbot_cli.bat`<br>`launch_gbpbot.sh`) | Interface complète avec menu interactif et gestion de l'environnement | Facilité d'utilisation, configuration automatique, multi-plateforme | Utilisation quotidienne, première fois |
| Script Python Direct<br>(`gbpbot_cli.py`) | Lancement direct via Python | Contrôle des arguments, intégration avec d'autres scripts | Scripts automatisés, développement |
| Script Pont<br>(`gbpbot_cli_bridge.py`) | Script de diagnostic et résolution des problèmes | Résout les problèmes d'asyncio et de dépendances, interface simplifiée | Dépannage, erreurs de lancement, systèmes spécifiques |
| PowerShell<br>(`gbpbot.ps1`) | Script PowerShell avancé | Options avancées, configuration détaillée | Utilisateurs avancés, personnalisation |
| Mode Simulation<br>(`run_bot.py`/`run_bot.bat`) | Lance le bot en mode simulation | Démarrage rapide, tests sans configuration | Tests rapides, démonstrations |

## 🚀 Méthodes de Lancement Détaillées

### 1. Scripts de Lancement Unifiés (Recommandé)

Les scripts de lancement unifiés sont conçus pour simplifier le processus de démarrage et fournir une expérience cohérente sur toutes les plateformes.

#### Fichiers concernés
- `launch_gbpbot_cli.bat` - Script batch Windows
- `launch_gbpbot.sh` - Script shell Linux/macOS
- `gbpbot_cli.py` - Script Python principal (appelé par les scripts ci-dessus)

#### Fonctionnalités
- Menu interactif avec options de lancement
- Gestion automatique de l'environnement virtuel Python
- Installation des dépendances manquantes
- Vérification et création des fichiers de configuration
- Gestion des erreurs et messages d'aide détaillés
- Options avancées (mode debug, sans environnement virtuel)

#### Options disponibles
- **Lancement normal** - Vérifie l'environnement et lance GBPBot
- **Sans environnement virtuel** - Lance GBPBot sans créer/activer d'environnement virtuel
- **Mode debug** - Active plus de logs pour le débogage
- **Quitter** - Ferme le lanceur

### 2. Script Python Direct

Vous pouvez également lancer GBPBot directement via le script Python principal.

#### Comment lancer
```bash
# Méthode basique
python gbpbot_cli.py

# Avec options
python gbpbot_cli.py --no-venv  # Sans environnement virtuel
python gbpbot_cli.py --debug    # Mode debug avec plus de logs
```

#### Avantages
- Contrôle direct des arguments de ligne de commande
- Intégration facile avec d'autres scripts
- Utilisation dans des environnements restreints

### 3. Script PowerShell Avancé

Le script PowerShell offre des options avancées pour les utilisateurs Windows.

#### Fichier concerné
- `gbpbot.ps1` - Script PowerShell complet

#### Comment lancer
```powershell
# Menu principal
.\gbpbot.ps1

# Lancer directement un module
.\gbpbot.ps1 -mode arbitrage    # Mode arbitrage
.\gbpbot.ps1 -sniper            # Mode sniping
.\gbpbot.ps1 -auto              # Mode automatique

# Autres fonctions
.\gbpbot.ps1 -config            # Configuration
.\gbpbot.ps1 -stats             # Statistiques
.\gbpbot.ps1 -verify            # Vérification du code
.\gbpbot.ps1 -update            # Mise à jour des dépendances
.\gbpbot.ps1 -help              # Afficher l'aide
```

#### Avantages
- Options avancées pour les utilisateurs Windows
- Intégration avec les outils de développement
- Fonctionnalités supplémentaires de maintenance

### 4. Mode Simulation Rapide

Pour des tests rapides, vous pouvez utiliser le mode simulation.

#### Fichiers concernés
- `run_bot.py` - Script Python simplifié
- `run_bot.bat` - Script batch Windows correspondant

#### Comment lancer
```bash
# Méthode 1 (Windows)
run_bot.bat

# Méthode 2 (tous systèmes)
python run_bot.py
```

#### Avantages
- Démarrage rapide sans passer par les menus
- Configuration minimale requise
- Idéal pour les tests et démonstrations

## 📱 Menu Principal

Quelle que soit la méthode de lancement choisie, vous accéderez au menu principal de GBPBot:

```
============================================================
                    GBPBot - Menu Principal
============================================================
Bienvenue dans GBPBot, votre assistant de trading sur MEME coins!

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
4. Retour au menu principal
```

## 💡 Bonnes Pratiques

1. **Utilisez les scripts unifiés** pour une expérience optimale, particulièrement si vous débutez avec GBPBot
2. **Pour les développeurs**, le script Python direct offre plus de flexibilité
3. **Pour les utilisateurs avancés sous Windows**, explorez les options de `gbpbot.ps1`
4. **Créez des raccourcis** vers les scripts de lancement pour un accès rapide
5. **Sauvegardez vos configurations** importantes dans les fichiers appropriés

## 🛠️ Script Pont pour la Résolution de Problèmes

Un nouveau script pont a été créé pour faciliter le lancement de GBPBot en cas de problèmes avec les méthodes standard.

### Utilisation du Script Pont

```bash
# Windows
python gbpbot_cli_bridge.py

# Linux/macOS
python3 gbpbot_cli_bridge.py
```

### Caractéristiques du Script Pont

Le script pont (`gbpbot_cli_bridge.py`) offre une interface simplifiée avec les fonctionnalités suivantes:

- 🔧 **Menu interactif** pour l'installation des dépendances et le lancement du bot
- 🧰 **Installation flexible des dépendances** avec plusieurs niveaux (minimale, standard, package complet)
- 🔍 **Diagnostic des problèmes courants** comme les erreurs d'importation et les dépendances manquantes
- 🧪 **Création automatique de stubs** pour contourner les problèmes connus sans modifier le code source
- 🔄 **Gestion correcte d'asyncio** pour éviter les erreurs de boucle d'événements, particulièrement sur Windows

### Quand Utiliser le Script Pont

Utilisez ce script dans les situations suivantes:

- Lorsque vous rencontrez des erreurs comme `no running event loop` ou `Module not found`
- Si les dépendances comme `anchorpy` ou `web3` causent des problèmes
- En cas d'échec des autres méthodes de lancement
- Pour un diagnostic rapide des problèmes d'environnement

Pour plus d'informations sur la résolution des problèmes de lancement, consultez [TROUBLESHOOTING_LAUNCH.md](TROUBLESHOOTING_LAUNCH.md). 