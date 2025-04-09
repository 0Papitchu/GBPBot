#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script pour exécuter tous les tests unitaires et d'intégration de GBPBot.

Ce script découvre et exécute tous les tests du projet GBPBot.
Il permet de:
- Exécuter les tests unitaires ou d'intégration séparément
- Générer un rapport de couverture de code
- Exécuter des tests spécifiques à certains modules
"""

import os
import sys
import argparse
import subprocess
import importlib.util
from pathlib import Path
import logging
import datetime

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("gbpbot_tests")

# Chemin racine du projet
ROOT_DIR = Path(__file__).resolve().parent
TEST_DIR = ROOT_DIR / "gbpbot" / "tests"

def parse_arguments():
    """
    Parse les arguments de ligne de commande.
    
    Returns:
        argparse.Namespace: Arguments parsés.
    """
    parser = argparse.ArgumentParser(description="Exécute les tests du GBPBot")
    
    parser.add_argument(
        "--unit-only",
        action="store_true",
        help="Exécute uniquement les tests unitaires"
    )
    
    parser.add_argument(
        "--integration-only",
        action="store_true",
        help="Exécute uniquement les tests d'intégration"
    )
    
    parser.add_argument(
        "--module",
        type=str,
        help="Exécute uniquement les tests pour le module spécifié"
    )
    
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Génère un rapport de couverture de code"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Affiche des détails supplémentaires pendant l'exécution des tests"
    )
    
    return parser.parse_args()

def check_environment():
    """
    Vérifie si l'environnement de test est correctement configuré.
    
    Returns:
        bool: True si l'environnement est correctement configuré, False sinon.
    """
    # Vérifier si le script de configuration de l'environnement existe
    setup_script = ROOT_DIR / "setup_test_environment.py"
    
    if setup_script.exists():
        logger.info("Configuration de l'environnement de test...")
        
        result = subprocess.run(
            [sys.executable, str(setup_script)],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            logger.error(f"Erreur lors de la configuration de l'environnement: {result.stderr}")
            return False
        
        logger.info("Environnement de test configuré avec succès")
    else:
        logger.warning("Script de configuration de l'environnement non trouvé. Vérifiez manuellement les dépendances.")
    
    return True

def find_test_modules(type_filter=None, module_filter=None):
    """
    Trouve tous les modules de test dans le projet.
    
    Args:
        type_filter (str, optional): Type de test à rechercher ('unit' ou 'integration').
        module_filter (str, optional): Filtre pour les modules spécifiques.
    
    Returns:
        list: Liste des chemins vers les modules de test.
    """
    if not TEST_DIR.exists():
        logger.error(f"Répertoire de tests introuvable: {TEST_DIR}")
        return []
    
    test_modules = []
    
    # Déterminer les sous-répertoires à rechercher
    subdirs = []
    if type_filter == "unit" or type_filter is None:
        unit_dir = TEST_DIR / "unit"
        if unit_dir.exists():
            subdirs.append(unit_dir)
    
    if type_filter == "integration" or type_filter is None:
        integration_dir = TEST_DIR / "integration"
        if integration_dir.exists():
            subdirs.append(integration_dir)
    
    # Rechercher tous les fichiers de test dans les sous-répertoires
    for subdir in subdirs:
        for path in subdir.glob("test_*.py"):
            # Appliquer le filtre de module si spécifié
            if module_filter:
                module_name = path.stem.replace("test_", "").replace("_module", "")
                if module_filter.lower() not in module_name.lower():
                    continue
            
            test_modules.append(path)
    
    return test_modules

def run_pytest(test_modules, coverage=False, verbose=False):
    """
    Exécute les tests avec pytest.
    
    Args:
        test_modules (list): Liste des chemins vers les modules de test.
        coverage (bool): Si True, génère un rapport de couverture.
        verbose (bool): Si True, affiche des détails supplémentaires.
    
    Returns:
        int: Code de retour de pytest (0 en cas de succès).
    """
    if not test_modules:
        logger.warning("Aucun module de test trouvé")
        return 0
    
    logger.info(f"Exécution de {len(test_modules)} modules de test")
    
    # Convertir les chemins de fichier en chaînes
    test_paths = [str(module) for module in test_modules]
    
    # Préparer la commande pytest
    cmd = [sys.executable, "-m", "pytest"]
    
    if verbose:
        cmd.append("-v")
    
    if coverage:
        cmd.extend(["--cov=gbpbot", "--cov-report=term", "--cov-report=html:coverage_report"])
    
    cmd.extend(test_paths)
    
    # Exécuter pytest
    logger.info(f"Commande: {' '.join(cmd)}")
    
    result = subprocess.run(cmd)
    
    return result.returncode

def generate_report(test_modules, exit_code):
    """
    Génère un rapport de résumé des tests.
    
    Args:
        test_modules (list): Liste des modules de test exécutés.
        exit_code (int): Code de sortie des tests.
    """
    success = exit_code == 0
    
    report_dir = ROOT_DIR / "test_reports"
    report_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = report_dir / f"test_report_{timestamp}.txt"
    
    with open(report_file, "w") as f:
        f.write("=" * 80 + "\n")
        f.write(f"Rapport de Test GBPBot - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")
        
        f.write(f"Statut: {'SUCCÈS' if success else 'ÉCHEC'}\n\n")
        
        f.write("Modules testés:\n")
        for i, module in enumerate(test_modules, 1):
            f.write(f"{i}. {module.stem}\n")
        
        f.write("\n")
        
        if success:
            f.write("Tous les tests ont réussi!\n")
        else:
            f.write(f"Des tests ont échoué (code de sortie: {exit_code})\n")
        
        f.write("\n")
        f.write("=" * 80 + "\n")
    
    logger.info(f"Rapport de test généré: {report_file}")

def main():
    """
    Fonction principale du script.
    """
    # Ajouter le répertoire racine au PYTHONPATH
    sys.path.insert(0, str(ROOT_DIR))
    
    # Analyser les arguments
    args = parse_arguments()
    
    logger.info("=" * 80)
    logger.info("Exécution des tests pour GBPBot")
    logger.info("=" * 80)
    
    # Vérifier l'environnement
    if not check_environment():
        return 1
    
    # Déterminer le type de test
    type_filter = None
    if args.unit_only:
        type_filter = "unit"
    elif args.integration_only:
        type_filter = "integration"
    
    # Trouver les modules de test
    test_modules = find_test_modules(type_filter, args.module)
    
    if not test_modules:
        logger.error("Aucun test trouvé avec les critères spécifiés")
        return 1
    
    logger.info(f"Tests trouvés: {len(test_modules)}")
    for module in test_modules:
        logger.info(f"  - {module.relative_to(ROOT_DIR)}")
    
    # Exécuter les tests
    exit_code = run_pytest(test_modules, args.coverage, args.verbose)
    
    # Générer un rapport
    generate_report(test_modules, exit_code)
    
    logger.info("=" * 80)
    logger.info(f"Tests terminés avec code de sortie: {exit_code}")
    logger.info("=" * 80)
    
    return exit_code

if __name__ == "__main__":
    sys.exit(main()) 