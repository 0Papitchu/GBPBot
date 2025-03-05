# GBPBot - Point d'Entrée Unique

Ce document explique comment utiliser le nouveau point d'entrée unifié pour GBPBot, qui permet de lancer le bot et le dashboard avec une seule commande.

## Lancement Simplifié

Pour lancer le bot avec le nouveau système unifié, exécutez simplement :

```bash
python run_bot.py
```

## Fonctionnalités

Le nouveau lanceur offre les fonctionnalités suivantes :

1. **Installation automatique des dépendances**
   - Vérifie et installe automatiquement les packages Python nécessaires
   - Gère les dépendances manquantes comme `python-dotenv`, `loguru`, etc.

2. **Configuration automatique**
   - Crée automatiquement un fichier `.env` par défaut s'il n'existe pas
   - Charge les variables d'environnement pour configurer le bot

3. **Option de lancement du dashboard**
   - Vous pouvez choisir de lancer le dashboard en parallèle du bot
   - Le dashboard s'ouvre dans une fenêtre séparée (sous Windows) ou en arrière-plan (sous Linux/Mac)

4. **Menu principal interactif**
   - Lancer le bot avec les paramètres du fichier `.env`
   - Configurer les paramètres de manière interactive
   - Afficher la configuration actuelle
   - Afficher les statistiques
   - Quitter proprement l'application

5. **Gestion propre des processus**
   - Arrêt automatique du dashboard lors de la fermeture du programme
   - Gestion des interruptions (Ctrl+C)

## Guide d'utilisation

### Première utilisation

1. Exécutez `python run_bot.py`
2. Le script vérifiera et installera les dépendances manquantes
3. Un fichier `.env` par défaut sera créé s'il n'existe pas
4. Vous serez invité à choisir si vous souhaitez lancer le dashboard en parallèle (y/n)
5. Le menu principal s'affichera avec les options disponibles

### Options du menu principal

- **1 : Lancer le bot**
  - Démarre le bot avec les paramètres définis dans le fichier `.env`
  - Affiche la configuration actuelle avant le lancement
  - Utilise les soldes initiaux définis dans le fichier `.env` en mode simulation

- **2 : Configurer les paramètres**
  - Permet de modifier les paramètres du bot de manière interactive
  - Les modifications sont enregistrées dans le fichier `.env`
  - Inclut des options pour le mode simulation, le réseau de test, les seuils de profit, etc.

- **3 : Afficher la configuration actuelle**
  - Affiche les paramètres actuels du bot depuis le fichier `.env`
  - Les informations sensibles (clés API, mots de passe) sont masquées

- **4 : Afficher les statistiques**
  - Affiche les dernières entrées des fichiers de log
  - Utile pour surveiller l'activité récente du bot

- **5 : Quitter**
  - Ferme proprement l'application
  - Arrête tous les processus en arrière-plan

## Compatibilité

Ce lanceur est compatible avec :
- Windows
- Linux
- macOS

## Dépannage

Si vous rencontrez des problèmes :

1. **Le dashboard ne se lance pas**
   - Vérifiez que le module `gbpbot.cli` est correctement installé
   - Essayez de lancer manuellement `python -m gbpbot.cli`

2. **Erreurs d'importation**
   - Vérifiez que vous êtes dans le répertoire racine du projet
   - Assurez-vous que toutes les dépendances sont installées

3. **Le bot ne démarre pas**
   - Vérifiez les fichiers de configuration
   - Consultez les logs pour plus d'informations

## Personnalisation

Vous pouvez personnaliser le comportement du lanceur en modifiant le fichier `run_bot.py`. Les principales sections que vous pourriez vouloir modifier sont :

- La liste `REQUIRED_PACKAGES` pour ajouter ou supprimer des dépendances
- La fonction `run_bot()` pour modifier le comportement du bot
- La liste `configurable_params` dans `configure_parameters()` pour ajouter ou supprimer des paramètres configurables 