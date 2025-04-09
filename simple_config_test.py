#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test simple pour le module de configuration du GBPBot.
"""

import os
import sys
import unittest
import yaml
from pathlib import Path

# Ajouter le répertoire racine au PYTHONPATH
ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

class SimpleConfigTest(unittest.TestCase):
    """Tests simples pour le module de configuration."""
    
    def setUp(self):
        """Configuration avant chaque test."""
        # Chemin vers le fichier de configuration
        self.config_file = ROOT_DIR / "config" / "config.yaml"
        
        # Vérifier que le fichier de configuration existe
        if not self.config_file.exists():
            self.skipTest(f"Le fichier de configuration n'existe pas: {self.config_file}")
        
        # Charger la configuration
        with open(self.config_file, "r") as f:
            self.config = yaml.safe_load(f)
    
    def test_config_structure(self):
        """Vérifie que la structure de la configuration est correcte."""
        # Vérifier que la configuration est un dictionnaire
        self.assertIsInstance(self.config, dict)
        
        # Vérifier que les sections principales sont présentes
        expected_sections = ["general", "blockchains", "wallets", "modules", "ai", "notifications", "exchanges", "arbitrage"]
        for section in expected_sections:
            self.assertIn(section, self.config, f"Section '{section}' manquante dans la configuration")
    
    def test_network_config(self):
        """Vérifie que la configuration des réseaux est correcte."""
        # Vérifier que la section blockchains existe
        self.assertIn("blockchains", self.config)
        
        # Vérifier que la section blockchains est un dictionnaire
        self.assertIsInstance(self.config["blockchains"], dict)
        
        # Vérifier qu'au moins un réseau est configuré
        self.assertGreater(len(self.config["blockchains"]), 0, "Aucun réseau configuré")
        
        # Vérifier la structure de chaque réseau
        for network_name, network_config in self.config["blockchains"].items():
            self.assertIsInstance(network_config, dict)
            
            # Vérifier les champs obligatoires
            required_fields = ["enabled", "rpc_url"]
            for field in required_fields:
                self.assertIn(field, network_config, f"Champ '{field}' manquant dans la configuration du réseau '{network_name}'")
    
    def test_trading_config(self):
        """Vérifie que la configuration du trading est correcte."""
        # Vérifier que la section modules existe
        self.assertIn("modules", self.config)
        
        # Vérifier que la section modules est un dictionnaire
        self.assertIsInstance(self.config["modules"], dict)
        
        # Vérifier les modules existants
        expected_modules = ["arbitrage", "sniping", "auto_trader"]
        for module in expected_modules:
            self.assertIn(module, self.config["modules"], f"Module '{module}' manquant")
            self.assertIn("enabled", self.config["modules"][module], f"Champ 'enabled' manquant dans le module '{module}'")
            self.assertIsInstance(self.config["modules"][module]["enabled"], bool, f"Le champ 'enabled' du module '{module}' n'est pas un booléen")

if __name__ == "__main__":
    unittest.main() 