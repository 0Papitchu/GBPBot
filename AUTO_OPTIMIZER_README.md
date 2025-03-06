# GBPBot - Optimiseur Automatique

## Présentation

L'optimiseur automatique de GBPBot est un outil avancé conçu pour surveiller en temps réel les performances du bot et appliquer automatiquement des ajustements d'optimisation lorsque nécessaire. Cette solution permet de maintenir une performance optimale sans intervention manuelle, en adaptant dynamiquement les paramètres du bot en fonction de l'utilisation des ressources système.

![Auto-Optimizer](https://via.placeholder.com/800x400?text=GBPBot+Auto-Optimizer)

## Fonctionnalités

- **Surveillance en temps réel** des performances système (CPU, mémoire, GPU, mémoire GPU)
- **Détection intelligente** des problèmes de performances
- **Optimisation automatique** des paramètres du bot en fonction des besoins
- **Détection du processus GBPBot** sans configuration manuelle
- **Rapports détaillés** sur les performances et les optimisations appliquées
- **Intervalles configurables** entre les optimisations
- **Interface non-intrusive** fonctionnant en arrière-plan

## Prérequis

- Python 3.7 ou supérieur
- Modules Python: psutil, matplotlib, numpy
- GBPBot installé et configuré
- Fichiers d'optimisation préalablement installés:
  - `monitor_performance.py`
  - `update_optimizations.py`

## Installation

1. Exécutez le script d'installation:

```bash
python install_auto_optimizer.py
```

2. Le script vérifiera automatiquement:
   - Votre version de Python
   - La présence des fichiers requis
   - Installera les dépendances nécessaires
   - Créera des scripts de démarrage adaptés à votre système d'exploitation

## Utilisation

### Démarrage simple

Sur Windows:
```
Double-cliquez sur start_auto_optimizer.bat
```

Sur Linux/macOS:
```bash
./start_auto_optimizer.sh
```

### Options avancées

Pour des configurations personnalisées, utilisez les options de ligne de commande:

```bash
python auto_optimizer.py --interval 15 --log-file custom_performance.log --env-file .env.custom
```

Options disponibles:
- `--interval` : Intervalle en minutes entre les optimisations (défaut: 30)
- `--pid` : PID du processus GBPBot à surveiller (détection auto si non spécifié)
- `--log-file` : Fichier de log du moniteur de performances
- `--env-file` : Fichier .env à mettre à jour

## Comment ça fonctionne

1. **Démarrage et détection** : L'optimiseur détecte automatiquement le processus GBPBot en cours d'exécution
2. **Phase de surveillance** : Collecte des données de performances (utilisation CPU, mémoire, GPU)
3. **Analyse des métriques** : Traitement des données collectées pour déterminer si des optimisations sont nécessaires
4. **Décision d'optimisation** : Si les seuils critiques sont dépassés (par exemple >90% CPU, >85% mémoire)
5. **Application des ajustements** : Modification automatique des paramètres d'optimisation
6. **Période de refroidissement** : Attente d'un intervalle défini avant de nouvelles optimisations

## Seuils et règles d'optimisation

| Métrique | Seuil bas | Seuil haut | Action |
|----------|-----------|------------|--------|
| CPU | <20% | >90% | Ajustement des limites de transactions et des connections RPC |
| Mémoire | <30% | >85% | Réduction de la taille des caches en mémoire |
| GPU | <20% | >85% | Optimisation des processus de machine learning |
| Mémoire GPU | - | >85% | Réduction de la taille des modèles et des batchs |

## Fichiers de logs

L'optimiseur génère des logs détaillés pour vous permettre de suivre son fonctionnement:

- `auto_optimizer_YYYYMMDD_HHMMSS.log` : Journal principal de l'optimiseur
- `gbpbot_performance.log` : Données de performance collectées
- `optimization_reports/` : Rapports d'optimisation détaillés (générés lors des ajustements)

## Dépannage

### Le moniteur ne démarre pas

Vérifiez que vous avez bien installé les dépendances requises:
```bash
pip install psutil matplotlib numpy
```

### L'optimiseur ne détecte pas GBPBot

Vous pouvez spécifier manuellement le PID du processus:
```bash
python auto_optimizer.py --pid 1234
```

### Erreurs d'optimisation

Si les optimisations ne s'appliquent pas correctement, vérifiez:
1. Les permissions d'accès au fichier `.env`
2. La présence du script `update_optimizations.py`
3. Les logs pour des messages d'erreur spécifiques

## Améliorations prévues

- Interface web pour la visualisation des performances en temps réel
- Optimisations prédictives basées sur l'apprentissage des patterns d'utilisation
- Support pour la détection de plusieurs instances de GBPBot
- Notifications Telegram/Discord en cas de problèmes de performance

## Intégration avec l'écosystème GBPBot

L'optimiseur automatique s'intègre parfaitement avec les autres outils d'optimisation:

- **Performance Monitor** : Visualisation graphique des performances
- **Update Optimizations** : Moteur d'application des optimisations
- **Optimization Summary** : Rapports détaillés sur les changements appliqués

## Contribution

Les contributions sont les bienvenues! Si vous souhaitez améliorer l'optimiseur automatique, n'hésitez pas à:

1. Forker le projet
2. Créer une branche (`git checkout -b feature/amazing-feature`)
3. Commit vos changements (`git commit -m 'Add some amazing feature'`)
4. Push vers la branche (`git push origin feature/amazing-feature`)
5. Ouvrir une Pull Request

## Licence

Distribué sous licence MIT. Voir `LICENSE` pour plus d'informations.

---

**GBPBot Auto-Optimizer** - Partie de la suite d'optimisation GBPBot  
Développé pour maximiser les performances dans le trading de MEME coins 