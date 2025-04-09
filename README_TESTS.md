# Suite de Tests pour GBPBot

Ce répertoire contient une suite de tests pour le GBPBot, un bot de trading automatisé pour les cryptomonnaies.

## Structure des Tests

La suite de tests est organisée en deux catégories principales :

1. **Tests Simples** : Tests unitaires légers qui ne nécessitent pas de dépendances complexes.
2. **Tests Complets** : Tests unitaires et d'intégration qui testent l'ensemble du système.

### Tests Simples

Les tests simples sont conçus pour fonctionner sans dépendances externes complexes comme TensorFlow, PyTorch, ou des connexions RPC actives. Ils utilisent des mocks pour simuler ces dépendances.

Liste des tests simples :

- `simple_test.py` : Tests de base pour l'environnement et les imports
- `simple_config_test.py` : Tests pour le module de configuration
- `simple_ai_test.py` : Tests pour le module d'IA avec mock TensorFlow
- `simple_security_test.py` : Tests pour le module de sécurité
- `simple_arbitrage_test.py` : Tests pour le module d'arbitrage
- `simple_sniping_test.py` : Tests pour le module de sniping de tokens

### Tests Complets

Les tests complets nécessitent toutes les dépendances et peuvent se connecter à des réseaux de test pour valider le comportement du bot.

## Exécution des Tests

### Tests Simples

Pour exécuter tous les tests simples :

```bash
python run_simple_tests.py
```

Pour exécuter un module spécifique :

```bash
python run_simple_tests.py --module [module_name]
```

Options disponibles pour `--module` :
- `all` : Tous les tests simples
- `env` : Tests d'environnement
- `config` : Tests de configuration
- `ai` : Tests d'IA
- `security` : Tests de sécurité
- `arbitrage` : Tests d'arbitrage
- `sniping` : Tests de sniping

Pour afficher les détails des tests :

```bash
python run_simple_tests.py --verbose
```

### Tests Complets

Pour exécuter tous les tests complets :

```bash
python run_all_tests.py
```

## Mocks

Les tests simples utilisent des mocks pour simuler les dépendances externes :

- `gbpbot/tests/mocks/tensorflow.py` : Mock pour TensorFlow et Keras
- Autres mocks selon les besoins

## Développement de Nouveaux Tests

Pour ajouter un nouveau test simple :

1. Créer un fichier `simple_[module]_test.py`
2. Implémenter les tests en utilisant le framework `unittest`
3. Ajouter le module à la liste des patterns dans `run_simple_tests.py`

## Couverture des Tests

Les modules suivants sont couverts par les tests :

- **Configuration** : Chargement et validation de la configuration
- **IA** : Modèles de prédiction et d'analyse
- **Sécurité** : Détection des risques et validation des transactions
- **Arbitrage** : Détection et exécution d'opportunités d'arbitrage
- **Sniping** : Détection et achat de nouveaux tokens

## Roadmap des Tests

Modules à tester prochainement :

- **MEV/Frontrunning** : Tests pour le module de frontrunning
- **Interface Unifiée** : Tests pour l'interface utilisateur
- **Gestion des Wallets** : Tests pour la gestion des portefeuilles
- **Monitoring** : Tests pour le module de surveillance

## Contribution

Pour contribuer aux tests, veuillez suivre ces directives :

1. Assurez-vous que les tests sont indépendants et peuvent s'exécuter de manière isolée
2. Utilisez des mocks pour les dépendances externes
3. Documentez clairement le but de chaque test
4. Suivez les conventions de nommage existantes 