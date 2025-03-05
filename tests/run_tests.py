import pytest
import argparse
import sys
from typing import Dict, List
import os
import importlib
import inspect

class TestRunner:
    def __init__(self):
        self.test_modules = {
            'arbitrage': {
                'path': 'test_arbitrage.py',
                'description': 'Tests du module arbitrage',
                'tests': {
                    'analyze_pair': 'Test de l\'analyse des paires de trading',
                    'execute_trade': 'Test de l\'exécution des trades',
                    'calculate_net_profit': 'Test du calcul du profit net',
                    'validate_opportunity': 'Test de la validation des opportunités',
                    'network_issues': 'Test des scénarios de problèmes réseau',
                    'slippage_scenarios': 'Test des scénarios de slippage',
                    'failed_transactions': 'Test des transactions échouées',
                    'input_validation': 'Test de la validation des inputs',
                    'performance': 'Test des performances'
                }
            },
            'sniping': {
                'path': 'test_sniping.py',
                'description': 'Tests du module de sniping de tokens',
                'tests': {
                    'detect_new_token': 'Test de la détection de nouveaux tokens',
                    'analyze_token': 'Test de l\'analyse des tokens',
                    'validate_token': 'Test de la validation des tokens',
                    'execute_buy': 'Test de l\'achat de tokens',
                    'monitor_price': 'Test du monitoring des prix'
                }
            },
            'mev': {
                'path': 'test_mev.py',
                'description': 'Tests du module MEV',
                'tests': {
                    'sandwich_attack': 'Test de la détection des opportunités sandwich',
                    'frontrun_detection': 'Test de la détection du frontrunning',
                    'backrun_detection': 'Test de la détection du backrunning',
                    'gas_optimization': 'Test de l\'optimisation du gas'
                }
            }
        }

    def list_modules(self):
        """Affiche la liste des modules disponibles"""
        print("\nModules de test disponibles:")
        print("-----------------------------")
        for module, info in self.test_modules.items():
            print(f"\n{module.upper()} - {info['description']}")
            print("Tests disponibles:")
            for test_name, description in info['tests'].items():
                print(f"  - {test_name}: {description}")

    def run_specific_test(self, module: str, test_name: str):
        """Lance un test spécifique d'un module"""
        if module not in self.test_modules:
            print(f"Module '{module}' non trouvé!")
            return False

        module_info = self.test_modules[module]
        test_path = module_info['path']
        
        if test_name not in module_info['tests']:
            print(f"Test '{test_name}' non trouvé dans le module {module}!")
            return False

        print(f"\nLancement du test: {test_name}")
        print(f"Description: {module_info['tests'][test_name]}")
        
        # Construction du chemin complet du test
        test_id = f"tests/{test_path}::TestArbitrageStrategy::test_{test_name}"
        pytest.main(["-v", test_id])

    def run_module_tests(self, module: str):
        """Lance tous les tests d'un module"""
        if module not in self.test_modules:
            print(f"Module '{module}' non trouvé!")
            return False

        module_info = self.test_modules[module]
        test_path = f"tests/{module_info['path']}"
        
        print(f"\nLancement de tous les tests du module {module.upper()}")
        print(f"Description: {module_info['description']}")
        
        pytest.main(["-v", test_path])

def main():
    parser = argparse.ArgumentParser(description='Runner de tests pour GBPBot')
    parser.add_argument('--list', action='store_true', help='Liste tous les modules et tests disponibles')
    parser.add_argument('--module', type=str, help='Module à tester')
    parser.add_argument('--test', type=str, help='Nom du test spécifique à lancer')
    
    args = parser.parse_args()
    runner = TestRunner()
    
    if args.list:
        runner.list_modules()
        return
    
    if args.module:
        if args.test:
            runner.run_specific_test(args.module, args.test)
        else:
            runner.run_module_tests(args.module)
    else:
        print("Utilisation:")
        print("  --list : Liste tous les modules et tests disponibles")
        print("  --module <nom_module> : Lance tous les tests du module spécifié")
        print("  --module <nom_module> --test <nom_test> : Lance un test spécifique du module")
        print("\nExemples:")
        print("  python -m tests.run_tests --list")
        print("  python -m tests.run_tests --module arbitrage")
        print("  python -m tests.run_tests --module arbitrage --test analyze_pair")

if __name__ == '__main__':
    main() 