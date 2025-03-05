# Guide des Méthodes de Lancement de GBPBot

Ce document explique en détail les différentes méthodes disponibles pour lancer GBPBot, leurs avantages, et quand utiliser chacune d'elles.

## Résumé des méthodes de lancement

| Méthode | Description | Avantages | Cas d'utilisation |
|---------|-------------|-----------|-------------------|
| Interface CLI Interactive | Interface complète avec menus | Configuration complète, tous les modes disponibles | Utilisation quotidienne, configuration avancée |
| Mode Simulation Rapide | Lance directement le bot en simulation | Rapide, simple | Tests rapides, démonstrations |
| Lancement des composants individuels | Lance chaque composant séparément | Contrôle granulaire | Développement, débogage |

## 1. Interface CLI Interactive

### Fichiers concernés
- `gbpbot_cli.py` - Script Python principal
- `launch_gbpbot_cli.bat` - Script batch Windows pour lancement facile

### Comment lancer
```bash
# Méthode 1 (Windows) - Double-cliquer sur le fichier
launch_gbpbot_cli.bat

# Méthode 2 - Via terminal
python gbpbot_cli.py
```

### Fonctionnalités
- Menu principal avec options pour lancer le bot, configurer les paramètres, etc.
- Configuration complète de tous les aspects du bot
- Choix entre les modes TEST, SIMULATION et LIVE
- Sauvegarde automatique des configurations
- Affichage des statistiques et performances
- Contrôle du bot pendant l'exécution (pause, arrêt, etc.)

### Avantages
- Interface utilisateur conviviale
- Pas besoin de modifier le code source
- Accès à toutes les fonctionnalités du bot
- Configurations sauvegardées entre les sessions

### Quand l'utiliser
- Pour une utilisation quotidienne du bot
- Lorsque vous avez besoin de modifier fréquemment les paramètres
- Pour accéder à tous les modes de fonctionnement
- Pour les utilisateurs qui préfèrent une interface interactive

## 2. Mode Simulation Rapide

### Fichiers concernés
- `run_bot.py` - Script Python simplifié
- `run_bot.bat` - Script batch Windows pour lancement facile

### Comment lancer
```bash
# Méthode 1 (Windows) - Double-cliquer sur le fichier
run_bot.bat

# Méthode 2 - Via terminal
python run_bot.py
```

### Fonctionnalités
- Lance directement le bot en mode simulation
- Utilise des paramètres prédéfinis (balances simulées, réseau testnet)
- Affiche les logs des transactions et performances dans la console

### Avantages
- Démarrage rapide sans passer par les menus
- Idéal pour les tests rapides
- Simple à utiliser

### Quand l'utiliser
- Pour tester rapidement les stratégies de trading
- Pour des démonstrations
- Lorsque vous n'avez pas besoin de modifier les paramètres
- Pour les utilisateurs qui préfèrent une approche directe

### Personnalisation
Pour modifier les paramètres du mode simulation rapide, vous pouvez éditer le fichier `run_bot.py` :
```python
# Exemple de modification des balances simulées
simulated_balances = {
    "WAVAX": 10.0,  # Modifier la valeur selon vos besoins
    "USDT": 1000.0,
    "USDC": 1000.0,
    "WETH": 0.5
}
```

## 3. Lancement des Composants Individuels

### Fichiers concernés
- `main.py` - Bot principal
- `api_server.py` - Serveur API
- `web_dashboard.py` - Interface web
- `start_servers.py` - Script pour lancer tous les services

### Comment lancer
```bash
# Lancer le bot principal
python main.py

# Lancer le serveur API
python api_server.py

# Lancer l'interface web
python web_dashboard.py

# Lancer tous les services
python start_servers.py
```

### Fonctionnalités
- Contrôle granulaire sur chaque composant
- Options de ligne de commande pour configuration avancée
- Possibilité de lancer les composants sur différentes machines

### Avantages
- Flexibilité maximale
- Idéal pour le développement et le débogage
- Permet une architecture distribuée

### Quand l'utiliser
- Pendant le développement
- Pour le débogage de composants spécifiques
- Pour les déploiements avancés (ex: composants sur différentes machines)
- Pour les utilisateurs avancés qui ont besoin d'un contrôle total

## Comparaison des Méthodes

### Interface CLI vs Mode Simulation Rapide

L'interface CLI offre une flexibilité complète mais nécessite de naviguer dans les menus, tandis que le mode simulation rapide est plus direct mais moins flexible.

### Interface CLI vs Composants Individuels

L'interface CLI est plus conviviale et gère automatiquement le lancement des composants nécessaires, tandis que le lancement des composants individuels offre un contrôle plus granulaire mais nécessite plus de connaissances techniques.

### Mode Simulation Rapide vs Composants Individuels

Le mode simulation rapide est optimisé pour la simplicité et les tests rapides, tandis que le lancement des composants individuels est conçu pour le développement et les déploiements avancés.

## Bonnes Pratiques

1. **Commencez avec l'interface CLI** pour vous familiariser avec toutes les options
2. **Utilisez le mode simulation rapide** pour des tests fréquents avec les mêmes paramètres
3. **Lancez les composants individuellement** uniquement si vous avez besoin d'un contrôle spécifique
4. **Sauvegardez vos configurations** importantes dans l'interface CLI
5. **Créez des scripts batch personnalisés** pour vos cas d'utilisation fréquents 