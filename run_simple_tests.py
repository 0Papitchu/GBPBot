#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script pour exécuter tous les tests simples du GBPBot.
Ce script permet de tester rapidement les composants de base sans
dépendances complexes.
"""

import os
import sys
import unittest
import argparse
from pathlib import Path

# Ajouter le répertoire racine au PYTHONPATH
ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

# Ajouter le répertoire de mocks au début du PYTHONPATH
mock_dir = ROOT_DIR / "gbpbot" / "tests" / "mocks"
if mock_dir.exists():
    sys.path.insert(0, str(mock_dir))

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Exécuter les tests simples pour GBPBot")
    parser.add_argument("--module", type=str, 
                        choices=["all", "env", "config", "ai", "security", "arbitrage", "sniping"], 
                        default="all", help="Module à tester")
    parser.add_argument("--verbose", "-v", action="store_true", 
                        help="Afficher les détails des tests")
    return parser.parse_args()

def discover_tests(module):
    """Découverte des tests selon le module spécifié."""
    test_loader = unittest.TestLoader()
    
    if module == "all":
        # Charger uniquement les tests simples
        patterns = [
            "simple_test.py", 
            "simple_config_test.py", 
            "simple_ai_test.py",
            "simple_security_test.py",
            "simple_arbitrage_test.py",
            "simple_sniping_test.py"
        ]
    else:
        # Charger un test spécifique
        patterns = [f"simple_{module}_test.py"]
    
    test_suite = unittest.TestSuite()
    for pattern in patterns:
        # Vérifier si le fichier existe
        test_file = ROOT_DIR / pattern
        if test_file.exists():
            try:
                # Charger directement le fichier spécifique sans passer par discover
                if pattern.endswith(".py"):
                    module_name = pattern[:-3]  # Remove .py extension
                    module = __import__(module_name)
                    suite = test_loader.loadTestsFromModule(module)
                    test_suite.addTests(suite)
            except Exception as e:
                print(f"Erreur lors du chargement du test {pattern}: {e}")
    
    return test_suite

def main():
    """Point d'entrée principal."""
    args = parse_arguments()
    
    # Configurer la verbosité
    verbosity = 2 if args.verbose else 1
    
    # Découvrir et exécuter les tests
    test_suite = discover_tests(args.module)
    test_runner = unittest.TextTestRunner(verbosity=verbosity)
    
    print("\n" + "="*60)
    print(f"Exécution des tests simples pour GBPBot - Module: {args.module}")
    print("="*60 + "\n")
    
    result = test_runner.run(test_suite)
    
    print("\n" + "="*60)
    print(f"Résultats: Succès: {result.testsRun - len(result.failures) - len(result.errors)}, "
          f"Échecs: {len(result.failures)}, Erreurs: {len(result.errors)}")
    print("="*60 + "\n")
    
    # Retourner le code de sortie
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(main()) 