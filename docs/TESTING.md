# Guide des Tests pour GBPBot

Ce document décrit le système de tests implémenté pour GBPBot, un bot de trading automatisé pour les blockchains Avalanche, Solana et autres. Le système de tests permet de valider le bon fonctionnement des modules clés avant leur déploiement en environnement réel.

## 1. Structure des Tests

Les tests sont organisés en deux catégories principales:

### Tests Unitaires
- Situés dans `gbpbot/tests/unit/`
- Testent des composants individuels de manière isolée
- Utilisent des mocks pour simuler les dépendances

### Tests d'Intégration
- Situés dans `gbpbot/tests/integration/`
- Testent l'interaction entre plusieurs modules
- Simulent un environnement plus proche de la réalité

## 2. Environnement de Test

L'environnement de test est configuré automatiquement via le script `setup_test_environment.py`, qui:

- Vérifie la version de Python et les dépendances nécessaires
- Installe automatiquement les dépendances manquantes
- Configure les variables d'environnement pour les tests
- Crée des wallets et des données de test fictives

## 3. Exécution des Tests

### Exécuter tous les tests
Pour exécuter tous les tests (unitaires et d'intégration):

```bash
python run_all_tests.py
```

Options disponibles:
- `--unit-only`: Exécute uniquement les tests unitaires
- `--integration-only`: Exécute uniquement les tests d'intégration
- `--coverage`: Génère un rapport de couverture de code
- `--verbose`: Affiche des détails supplémentaires pendant l'exécution

### Exécuter des tests spécifiques
Pour exécuter les tests d'un module particulier:

```bash
python run_specific_tests.py --test <nom_module>
```

Où `<nom_module>` peut être:
- `config`: Tests du module de configuration
- `security`: Tests du module de sécurité
- `backtesting`: Tests du module de backtesting
- `mev`: Tests du module MEV/Frontrunning
- `arbitrage`: Tests du module d'arbitrage
- `sniping`: Tests du module de sniping
- `wallet`: Tests du module de gestion des wallets
- `interface`: Tests de l'interface unifiée

Options disponibles:
- `--type unit|integration|all`: Type de tests à exécuter (par défaut: all)
- `--verbose`: Affiche des détails supplémentaires
- `--install-deps`: Installe automatiquement les dépendances manquantes

## 4. Rédaction de Nouveaux Tests

Pour créer un nouveau test unitaire, suivez ces étapes:

1. Créez un fichier dans `gbpbot/tests/unit/` nommé `test_<module>_module.py`
2. Utilisez le framework `unittest` ou `pytest` pour structurer vos tests
3. Importez les modules à tester et créez des mocks pour les dépendances
4. Écrivez des méthodes de test avec des assertions claires

Exemple de base:

```python
import unittest
from unittest.mock import MagicMock, patch
from gbpbot.core.module import ModuleClass

class TestModuleClass(unittest.TestCase):
    def setUp(self):
        # Configuration du test
        self.module = ModuleClass()
        
    def test_function_returns_correct_value(self):
        result = self.module.some_function()
        self.assertEqual(result, expected_value)
        
    @patch('gbpbot.core.module.some_dependency')
    def test_with_mocked_dependency(self, mock_dependency):
        # Configure the mock
        mock_dependency.return_value = "mocked_value"
        
        # Test the function
        result = self.module.function_with_dependency()
        self.assertEqual(result, "expected_with_mock")
```

## 5. Rapports de Tests

Après l'exécution des tests, un rapport est généré dans le dossier `test_reports/` contenant:

- La liste des tests exécutés
- Le statut global (succès/échec)
- Des détails sur les éventuelles erreurs

Si l'option `--coverage` est utilisée, un rapport de couverture HTML est généré dans `coverage_report/`.

## 6. Bonnes Pratiques

1. **Isolation**: Chaque test doit être isolé et ne pas dépendre d'autres tests
2. **Déterminisme**: Les tests doivent produire le même résultat à chaque exécution
3. **Clarté**: Nommez vos tests de manière descriptive pour comprendre facilement leur objectif
4. **Rapidité**: Les tests unitaires doivent s'exécuter rapidement (< 1s par test)
5. **Structure**: Utilisez `setUp` et `tearDown` pour la configuration et le nettoyage
6. **Couverture**: Visez une couverture de code d'au moins 80% pour les modules critiques

## 7. Dépannage

### Problèmes courants

#### ImportError pour les modules testés
- Vérifiez que le répertoire racine est dans le PYTHONPATH
- Vérifiez que les importations utilisent les chemins corrects

#### Échec des tests avec des erreurs de connexion
- Les tests d'intégration peuvent nécessiter une connexion Internet
- Utilisez des mocks pour simuler les réponses des API

#### Erreurs liées aux dépendances
- Exécutez `python setup_test_environment.py` pour installer les dépendances
- Ou utilisez l'option `--install-deps` avec `run_specific_tests.py`

## 8. Intégration Continue (À venir)

Un système d'intégration continue (CI/CD) est prévu pour:
- Exécuter automatiquement les tests à chaque commit
- Valider les pull requests uniquement si tous les tests passent
- Générer et publier des rapports de couverture de code
- Déployer automatiquement les versions stables 