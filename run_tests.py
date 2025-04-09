#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script d'exécution des tests du GBPBot

Ce script exécute les tests unitaires et d'intégration du GBPBot.
Il permet également d'exécuter des tests spécifiques pour certains
modules, ou de combiner des tests unitaires et d'intégration.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

# Obtenir le chemin absolu du répertoire racine du projet
ROOT_DIR = Path(__file__).resolve().parent

def parse_arguments():
    """Parse les arguments de ligne de commande."""
    parser = argparse.ArgumentParser(description="Exécution des tests du GBPBot")
    
    parser.add_argument(
        "--module", 
        type=str, 
        help="Module spécifique à tester (ex: wallet, sniping, arbitrage, mev, interface)"
    )
    
    parser.add_argument(
        "--unit-only", 
        action="store_true", 
        help="Exécuter uniquement les tests unitaires"
    )
    
    parser.add_argument(
        "--integration-only", 
        action="store_true", 
        help="Exécuter uniquement les tests d'intégration"
    )
    
    parser.add_argument(
        "--integration-test",
        type=str,
        choices=["sniping-arbitrage", "all"],
        help="Test d'intégration spécifique à exécuter"
    )
    
    parser.add_argument(
        "--verbose", 
        action="store_true", 
        help="Affichage détaillé des résultats des tests"
    )
    
    parser.add_argument(
        "--coverage", 
        action="store_true", 
        help="Générer un rapport de couverture des tests"
    )
    
    return parser.parse_args()

def run_tests():
    """Exécute les tests en utilisant le script run_all_tests.py ou directement avec unittest."""
    args = parse_arguments()
    
    # Si un test d'intégration spécifique est demandé
    if args.integration_test:
        return run_specific_integration_test(args.integration_test, args.verbose)
    
    # Sinon, utiliser le script run_all_tests.py
    test_script_path = ROOT_DIR / "gbpbot" / "tests" / "run_all_tests.py"
    
    if not test_script_path.exists():
        print(f"Erreur: Le script de test n'existe pas à l'emplacement {test_script_path}")
        return 1
    
    cmd = [sys.executable, str(test_script_path)]
    
    # Ajouter les arguments
    if args.module:
        cmd.extend(["--module", args.module])
    
    if args.unit_only:
        cmd.append("--unit-only")
    
    if args.integration_only:
        cmd.append("--integration-only")
    
    if args.verbose:
        cmd.append("--verbose")
    
    if args.coverage:
        cmd.append("--coverage")
    
    # Exécuter la commande
    print(f"Exécution de la commande: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    
    return result.returncode

def run_specific_integration_test(test_name, verbose=False):
    """
    Exécute un test d'intégration spécifique.
    
    Args:
        test_name (str): Nom du test d'intégration ('sniping-arbitrage', 'all')
        verbose (bool): Affichage détaillé des résultats
        
    Returns:
        int: Code de retour (0 pour succès, non-zéro pour échec)
    """
    import unittest
    import importlib.util
    
    test_dir = ROOT_DIR / "gbpbot" / "tests" / "integration"
    
    if not test_dir.exists():
        print(f"Erreur: Le répertoire de tests d'intégration n'existe pas: {test_dir}")
        return 1
    
    # Déterminer les tests à exécuter
    test_files = []
    
    if test_name == "sniping-arbitrage":
        test_files.append("test_sniping_arbitrage_integration.py")
    elif test_name == "all":
        # Trouver tous les fichiers de test d'intégration
        for file in test_dir.glob("test_*.py"):
            test_files.append(file.name)
    
    if not test_files:
        print(f"Erreur: Aucun test d'intégration trouvé pour '{test_name}'")
        return 1
    
    # Ajouter le répertoire racine au PYTHONPATH
    sys.path.insert(0, str(ROOT_DIR))
    
    # Préparer la suite de tests
    test_suite = unittest.TestSuite()
    
    for file_name in test_files:
        file_path = test_dir / file_name
        if not file_path.exists():
            print(f"Avertissement: Fichier de test non trouvé: {file_path}")
            continue
        
        # Charger le module de test
        module_name = file_name[:-3]  # Retirer l'extension .py
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None:
            print(f"Erreur: Impossible de charger le module {module_name} depuis {file_path}")
            continue
            
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Ajouter les tests au TestSuite
        for name in dir(module):
            obj = getattr(module, name)
            if isinstance(obj, type) and issubclass(obj, unittest.TestCase) and obj != unittest.TestCase:
                test_suite.addTest(unittest.makeSuite(obj))
    
    # Exécuter les tests
    verbosity = 2 if verbose else 1
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(test_suite)
    
    # Retourner le code d'erreur
    return 0 if result.wasSuccessful() else 1

def main():
    """Fonction principale."""
    print("=" * 80)
    print("Démarrage des tests du GBPBot")
    print("=" * 80)
    
    # Ajouter le répertoire racine au PYTHONPATH
    sys.path.insert(0, str(ROOT_DIR))
    
    # Exécuter les tests
    exit_code = run_tests()
    
    print("=" * 80)
    print(f"Fin des tests du GBPBot (code de sortie: {exit_code})")
    print("=" * 80)
    
    return exit_code

if __name__ == "__main__":
    sys.exit(main()) 