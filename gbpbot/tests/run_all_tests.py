#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script d'exécution de tous les tests du GBPBot

Ce script exécute l'ensemble des tests unitaires et d'intégration
pour valider le bon fonctionnement de tous les modules du GBPBot.
Il génère également un rapport de couverture de tests pour identifier
les parties du code qui nécessitent des tests supplémentaires.
"""

import os
import sys
import unittest
import argparse
import logging
from pathlib import Path
from datetime import datetime

# Ajout du chemin racine au sys.path pour les imports
ROOT_DIR = Path(__file__).parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Import des modules de test
from gbpbot.tests.setup_test_environment import setup_test_environment, cleanup_test_environment

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("gbpbot_tests")


def parse_arguments():
    """Analyse les arguments de ligne de commande."""
    parser = argparse.ArgumentParser(description="Exécution des tests du GBPBot")
    
    parser.add_argument(
        "--module", 
        type=str, 
        help="Module spécifique à tester (ex: wallet, sniping, arbitrage)"
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


def discover_tests(test_type="all", module=None):
    """
    Découvre les tests à exécuter en fonction du type et du module spécifié.
    
    Args:
        test_type: Type de tests à exécuter ('unit', 'integration', 'all')
        module: Module spécifique à tester (optionnel)
        
    Returns:
        TestSuite: Suite de tests à exécuter
    """
    tests_dir = Path(__file__).parent
    
    if test_type == "unit":
        search_dir = tests_dir / "unit"
    elif test_type == "integration":
        search_dir = tests_dir / "integration"
    else:
        search_dir = tests_dir
    
    pattern = f"test_{module}_*.py" if module else "test_*.py"
    
    logger.info(f"Recherche des tests dans: {search_dir} avec pattern: {pattern}")
    return unittest.defaultTestLoader.discover(
        start_dir=str(search_dir),
        pattern=pattern,
        top_level_dir=str(tests_dir)
    )


def run_tests(test_suite, verbosity=1):
    """
    Exécute une suite de tests.
    
    Args:
        test_suite: Suite de tests à exécuter
        verbosity: Niveau de détail (1=normal, 2=détaillé)
        
    Returns:
        TestResult: Résultat des tests
    """
    runner = unittest.TextTestRunner(verbosity=verbosity)
    return runner.run(test_suite)


def generate_coverage_report():
    """
    Génère un rapport de couverture des tests.
    Nécessite le package 'coverage'.
    
    Returns:
        bool: True si la génération a réussi, False sinon
    """
    try:
        import coverage
        cov = coverage.Coverage()
        
        # Démarrer la collecte de données de couverture
        cov.start()
        
        # Exécuter tous les tests
        all_tests = discover_tests()
        run_tests(all_tests)
        
        # Arrêter la collecte
        cov.stop()
        
        # Générer le rapport
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_dir = ROOT_DIR / "reports" / "coverage" / timestamp
        os.makedirs(report_dir, exist_ok=True)
        
        # Rapport HTML
        html_report = report_dir / "html"
        cov.html_report(directory=str(html_report))
        
        # Rapport XML pour intégration CI/CD
        xml_report = report_dir / "coverage.xml"
        cov.xml_report(outfile=str(xml_report))
        
        logger.info(f"Rapport de couverture généré dans: {report_dir}")
        return True
        
    except ImportError:
        logger.error("Package 'coverage' non installé. Installez-le avec: pip install coverage")
        return False
    except Exception as e:
        logger.error(f"Erreur lors de la génération du rapport de couverture: {str(e)}")
        return False


def print_test_summary(result, test_type):
    """
    Affiche un résumé des résultats des tests.
    
    Args:
        result: Résultat des tests
        test_type: Type de tests exécutés
    """
    total = result.testsRun
    success = total - len(result.errors) - len(result.failures)
    
    logger.info(f"\n{'='*50}")
    logger.info(f"Résumé des tests {test_type}")
    logger.info(f"{'='*50}")
    logger.info(f"Tests exécutés: {total}")
    logger.info(f"Réussis: {success} ({success/total*100:.1f}%)")
    logger.info(f"Échoués: {len(result.failures)}")
    logger.info(f"Erreurs: {len(result.errors)}")
    
    if result.failures:
        logger.info("\nDétail des échecs:")
        for failure in result.failures:
            logger.info(f"- {failure[0]}")
    
    if result.errors:
        logger.info("\nDétail des erreurs:")
        for error in result.errors:
            logger.info(f"- {error[0]}")


def main():
    """
    Fonction principale d'exécution des tests.
    """
    args = parse_arguments()
    
    # Configurer l'environnement de test
    logger.info("Configuration de l'environnement de test...")
    env_file, wallet_paths = setup_test_environment()
    
    try:
        verbosity = 2 if args.verbose else 1
        
        # Exécuter les tests selon les options spécifiées
        if args.coverage:
            logger.info("Génération du rapport de couverture des tests...")
            generate_coverage_report()
        else:
            if args.unit_only and not args.integration_only:
                # Tests unitaires uniquement
                logger.info("Exécution des tests unitaires...")
                unit_tests = discover_tests(test_type="unit", module=args.module)
                unit_result = run_tests(unit_tests, verbosity)
                print_test_summary(unit_result, "unitaires")
                
            elif args.integration_only and not args.unit_only:
                # Tests d'intégration uniquement
                logger.info("Exécution des tests d'intégration...")
                integration_tests = discover_tests(test_type="integration", module=args.module)
                integration_result = run_tests(integration_tests, verbosity)
                print_test_summary(integration_result, "d'intégration")
                
            else:
                # Tous les tests
                logger.info("Exécution de tous les tests...")
                all_tests = discover_tests(module=args.module)
                all_result = run_tests(all_tests, verbosity)
                print_test_summary(all_result, "complets")
    
    finally:
        # Nettoyage de l'environnement de test
        logger.info("Nettoyage de l'environnement de test...")
        cleanup_test_environment(env_file, wallet_paths)


if __name__ == "__main__":
    logger.info("Démarrage de la suite de tests GBPBot...")
    main()
    logger.info("Fin de l'exécution des tests.") 