#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script pour exécuter des tests spécifiques du GBPBot.

Ce script simplifie l'exécution des tests spécifiques en fournissant
une interface simple et en gérant automatiquement les dépendances.
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path
import logging

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("gbpbot_specific_tests")

# Chemin racine du projet
ROOT_DIR = Path(__file__).resolve().parent

def parse_arguments():
    """
    Parse les arguments de ligne de commande.
    
    Returns:
        argparse.Namespace: Arguments parsés.
    """
    parser = argparse.ArgumentParser(description="Exécute des tests spécifiques du GBPBot")
    
    parser.add_argument(
        "--test",
        type=str,
        required=True,
        help="Module à tester (ex: config, security, sniping, etc.)"
    )
    
    parser.add_argument(
        "--type",
        type=str,
        choices=["unit", "integration", "all"],
        default="all",
        help="Type de test à exécuter (unit, integration ou all)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Affiche des détails supplémentaires pendant l'exécution des tests"
    )
    
    parser.add_argument(
        "--install-deps",
        action="store_true",
        help="Installe automatiquement les dépendances manquantes"
    )
    
    parser.add_argument(
        "--mock-deps",
        action="store_true",
        help="Utilise des mocks pour les dépendances manquantes"
    )
    
    return parser.parse_args()

def setup_environment(install_deps=False, mock_deps=False):
    """
    Configure l'environnement pour l'exécution des tests.
    
    Args:
        install_deps (bool): Si True, installe automatiquement les dépendances manquantes.
        mock_deps (bool): Si True, utilise des mocks pour les dépendances manquantes.
        
    Returns:
        bool: True si la configuration a réussi, False sinon.
    """
    # Exécuter le script de configuration de l'environnement s'il existe
    setup_script = ROOT_DIR / "setup_test_environment.py"
    
    if setup_script.exists():
        logger.info("Configuration de l'environnement de test...")
        
        cmd = [sys.executable, str(setup_script)]
        if install_deps:
            cmd.append("--install-deps")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"Erreur lors de la configuration de l'environnement: {result.stderr}")
            return False
        
        logger.info("Environnement de test configuré avec succès")
    else:
        logger.warning("Script de configuration de l'environnement non trouvé.")
        
        # Installation manuelle des dépendances de base pour les tests
        if install_deps:
            try:
                dependencies = [
                    "pytest>=7.4.0",
                    "pytest-mock>=3.12.0",
                    "pytest-cov>=4.1.0",
                    "xgboost>=1.7.5"
                ]
                
                logger.info(f"Installation des dépendances de base pour les tests: {dependencies}")
                
                cmd = [sys.executable, "-m", "pip", "install"] + dependencies
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode != 0:
                    logger.error(f"Erreur lors de l'installation des dépendances: {result.stderr}")
                    return False
                
                logger.info("Dépendances de base installées avec succès")
            except Exception as e:
                logger.error(f"Erreur lors de l'installation des dépendances: {str(e)}")
                return False
    
    # Si mock_deps est activé, créer un fichier de mock pour tensorflow
    if mock_deps:
        mock_dir = ROOT_DIR / "gbpbot" / "tests" / "mocks"
        mock_dir.mkdir(exist_ok=True, parents=True)
        
        # Créer un mock pour tensorflow
        tf_mock_path = mock_dir / "tensorflow.py"
        with open(tf_mock_path, "w") as f:
            f.write("""
# Mock pour tensorflow
class MockTensor:
    def __init__(self, value=None):
        self.value = value

def constant(*args, **kwargs):
    return MockTensor()

def Variable(*args, **kwargs):
    return MockTensor()

class keras:
    class layers:
        class Dense:
            def __init__(self, *args, **kwargs):
                pass
            def __call__(self, *args, **kwargs):
                return MockTensor()
        
        class Input:
            def __init__(self, *args, **kwargs):
                pass
            def __call__(self, *args, **kwargs):
                return MockTensor()
        
        class LSTM:
            def __init__(self, *args, **kwargs):
                pass
            def __call__(self, *args, **kwargs):
                return MockTensor()
    
    class Model:
        def __init__(self, *args, **kwargs):
            pass
        def compile(self, *args, **kwargs):
            pass
        def fit(self, *args, **kwargs):
            class History:
                def __init__(self):
                    self.history = {"loss": [0.1, 0.05], "val_loss": [0.2, 0.1]}
            return History()
        def predict(self, *args, **kwargs):
            import numpy as np
            return np.array([0.5, 0.7, 0.3])
        def save(self, *args, **kwargs):
            pass
        def load_weights(self, *args, **kwargs):
            pass
    
    class optimizers:
        class Adam:
            def __init__(self, *args, **kwargs):
                pass
    
    class losses:
        mse = "mse"
        categorical_crossentropy = "categorical_crossentropy"
    
    class callbacks:
        class EarlyStopping:
            def __init__(self, *args, **kwargs):
                pass
        class ModelCheckpoint:
            def __init__(self, *args, **kwargs):
                pass
""")
        
        # Ajouter le répertoire de mocks au début du PYTHONPATH
        sys.path.insert(0, str(mock_dir))
        logger.info(f"Mocks pour les dépendances créés dans {mock_dir}")
    
    return True

def run_tests(module, test_type="all", verbose=False):
    """
    Exécute les tests pour un module spécifique.
    
    Args:
        module (str): Nom du module à tester.
        test_type (str): Type de test à exécuter ("unit", "integration" ou "all").
        verbose (bool): Si True, affiche plus de détails.
        
    Returns:
        int: Code de retour des tests (0 si succès).
    """
    # Construire le pattern de module
    module_pattern = f"test_{module}"
    if not module_pattern.endswith("_module"):
        module_pattern += "_module"
    
    # Déterminer les sous-répertoires à tester
    test_dirs = []
    
    if test_type in ["unit", "all"]:
        test_dirs.append(f"gbpbot/tests/unit/{module_pattern}.py")
    
    if test_type in ["integration", "all"]:
        test_dirs.append(f"gbpbot/tests/integration/{module_pattern}.py")
    
    # Vérifier si les fichiers de test existent
    test_paths = []
    for test_dir in test_dirs:
        path = ROOT_DIR / test_dir
        if path.exists():
            test_paths.append(str(path))
    
    if not test_paths:
        logger.error(f"Aucun test trouvé pour le module '{module}' avec le type '{test_type}'")
        return 1
    
    # Construire la commande pytest
    cmd = [sys.executable, "-m", "pytest"]
    
    if verbose:
        cmd.append("-v")
    
    cmd.extend(test_paths)
    
    # Exécuter pytest
    logger.info(f"Exécution des tests pour le module '{module}' (type: {test_type})")
    logger.info(f"Commande: {' '.join(cmd)}")
    
    result = subprocess.run(cmd)
    
    return result.returncode

def main():
    """
    Fonction principale du script.
    """
    # Ajouter le répertoire racine au PYTHONPATH
    sys.path.insert(0, str(ROOT_DIR))
    
    # Analyser les arguments
    args = parse_arguments()
    
    logger.info("=" * 80)
    logger.info(f"Exécution des tests pour le module '{args.test}' (type: {args.type})")
    logger.info("=" * 80)
    
    # Configurer l'environnement
    if not setup_environment(args.install_deps, args.mock_deps):
        return 1
    
    # Exécuter les tests
    exit_code = run_tests(args.test, args.type, args.verbose)
    
    logger.info("=" * 80)
    logger.info(f"Tests terminés avec code de sortie: {exit_code}")
    logger.info("=" * 80)
    
    return exit_code

if __name__ == "__main__":
    sys.exit(main()) 