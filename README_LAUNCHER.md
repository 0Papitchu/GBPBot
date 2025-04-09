# GBPBot - Système de Lancement Unifié

Ce document explique l'architecture et le fonctionnement du système de lancement unifié de GBPBot.

## 📋 Architecture du Système de Lancement

Le système de lancement de GBPBot suit une architecture en trois couches conçue pour être robuste, facile à maintenir et compatible avec différentes plateformes.

### 1. Scripts de Lancement Spécifiques à la Plateforme
- **Windows:** `launch_gbpbot.bat`
- **Linux/macOS:** `launch_gbpbot.sh`

Ces scripts sont le point d'entrée pour les utilisateurs. Ils vérifient l'environnement de base (Python installé, etc.) et lancent le lanceur Python principal.

### 2. Lanceur Python Principal
- **Fichier:** `gbpbot_launcher.py`

Ce lanceur central unifie toutes les fonctionnalités de lancement en un seul fichier. Il gère :
- La vérification complète de l'environnement
- L'installation des dépendances manquantes
- La configuration automatique
- Le démarrage des différents modes du bot
- La gestion des erreurs

### 3. Librairie d'Initialisation
Les fonctions d'initialisation sont séparées du code de lancement pour permettre leur réutilisation dans différents contextes.

## 🚀 Comment Utiliser les Scripts de Lancement

### Windows
```bash
# Double-cliquez simplement sur le fichier
launch_gbpbot.bat

# Ou lancez depuis une invite de commande
launch_gbpbot.bat
```

### Linux/macOS
```bash
# Rendre le script exécutable (première fois uniquement)
chmod +x launch_gbpbot.sh

# Lancer GBPBot
./launch_gbpbot.sh
```

### Options de Ligne de Commande (Python Direct)
Pour les utilisateurs avancés, vous pouvez invoquer directement le lanceur Python avec des options spécifiques :

```bash
python gbpbot_launcher.py [OPTIONS]

Options:
  --mode MODE     Mode de lancement: cli, dashboard, auto, simulation
  --debug         Active les logs détaillés 
  --no-checks     Ignore les vérifications d'environnement
  --config PATH   Utilise un fichier de configuration spécifique
```

## 🛠️ Caractéristiques Techniques

### Vérifications Automatiques
Le lanceur effectue automatiquement plusieurs vérifications pour garantir un environnement de fonctionnement optimal :

- **Python :** Version et modules installés
- **Configuration :** Fichiers `.env` valides et complets
- **Dépendances :** Packages Python requis
- **Accès RPC :** Connexion aux nœuds blockchain
- **Wallets :** Existence et validité des wallets configurés

### Gestion des Erreurs
Le système implémente une gestion robuste des erreurs :

- **Détection précoce :** Les problèmes sont identifiés avant le lancement
- **Messages d'erreur clairs :** Instructions précises pour résoudre les problèmes
- **Correction automatique :** Résolution automatique des problèmes courants lorsque possible

### Cross-Platform
Le système de lancement est conçu pour fonctionner de manière identique sur :
- Windows (7/8/10/11)
- Linux (Ubuntu, Debian, etc.)
- macOS (10.15+)

## 🔧 Maintenance et Personnalisation

### Ajouter un Nouveau Mode de Lancement

Pour ajouter un nouveau mode au lanceur, modifiez `gbpbot_launcher.py` :

1. Créez une nouvelle fonction de lancement pour votre mode :
```python
def launch_new_mode() -> int:
    """Lancer le nouveau mode."""
    # Votre code ici
    return 0  # Retournez 0 pour succès, autre pour erreur
```

2. Mettez à jour la fonction `main()` pour ajouter votre mode :
```python
if mode == "newmode":
    return launch_new_mode()
```

3. Mettez à jour les scripts batch/shell pour inclure votre nouveau mode dans le menu.

### Architecture de Gestion des Erreurs

Le système utilise un modèle de gestion d'erreurs en couches :

1. **Scripts shell/batch :** Détectent les erreurs d'environnement de base
2. **Lanceur Python :** Valide l'environnement complet et les dépendances
3. **Système de logs :** Capture et stocke les erreurs pour analyse

## 📝 Dépannage

Si vous rencontrez des problèmes avec le système de lancement, consultez :

- [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) - Guide de dépannage complet
- [LANCEMENT_GBPBOT.md](docs/LANCEMENT_GBPBOT.md) - Documentation détaillée du lancement

## 🔄 Évolutions Futures

- Intégration d'un système d'auto-mise à jour pour les dépendances et le code
- Support pour les containers Docker
- Interface graphique de lancement (GUI) pour Windows 