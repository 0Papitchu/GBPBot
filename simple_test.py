#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de test simple pour vérifier que l'environnement de test fonctionne.
"""

import os
import sys
import unittest
from pathlib import Path

# Ajouter le répertoire racine au PYTHONPATH
ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

class SimpleTest(unittest.TestCase):
    """Tests simples pour vérifier que l'environnement de test fonctionne."""
    
    def test_environment_variables(self):
        """Vérifie que les variables d'environnement sont correctement configurées."""
        # Vérifier que le répertoire racine est dans le PYTHONPATH
        self.assertIn(str(ROOT_DIR), sys.path)
        
        # Vérifier que Python est correctement configuré
        self.assertIsNotNone(sys.executable)
        self.assertGreaterEqual(sys.version_info.major, 3)
        self.assertGreaterEqual(sys.version_info.minor, 9)
    
    def test_file_system(self):
        """Vérifie que le système de fichiers est accessible."""
        # Vérifier que le répertoire racine existe
        self.assertTrue(ROOT_DIR.exists())
        
        # Vérifier que le répertoire de configuration existe
        config_dir = ROOT_DIR / "config"
        self.assertTrue(config_dir.exists(), f"Le répertoire de configuration n'existe pas: {config_dir}")
    
    def test_import_basic_modules(self):
        """Vérifie que les modules de base peuvent être importés."""
        # Importer des modules standard
        import json
        import datetime
        import logging
        
        # Vérifier que les modules sont correctement importés
        self.assertIsNotNone(json)
        self.assertIsNotNone(datetime)
        self.assertIsNotNone(logging)
    
    def test_import_third_party_modules(self):
        """Vérifie que les modules tiers peuvent être importés."""
        try:
            import numpy
            import pandas
            self.assertIsNotNone(numpy)
            self.assertIsNotNone(pandas)
        except ImportError as e:
            self.fail(f"Erreur lors de l'importation des modules tiers: {e}")

if __name__ == "__main__":
    unittest.main() 