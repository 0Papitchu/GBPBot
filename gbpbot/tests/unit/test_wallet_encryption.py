#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests unitaires pour le module de chiffrement des wallets

Ce module teste les fonctionnalités de chiffrement et déchiffrement des wallets,
une fonctionnalité critique pour la sécurité du GBPBot.
"""

import os
import sys
import json
import unittest
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional
from unittest.mock import patch, MagicMock

# Ajout du chemin racine au sys.path pour les imports
ROOT_DIR = Path(__file__).parent.parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Import des modules de test
from gbpbot.tests.setup_test_environment import setup_test_environment, cleanup_test_environment


class TestWalletEncryption(unittest.TestCase):
    """Suite de tests pour le module de chiffrement des wallets"""
    
    @classmethod
    def setUpClass(cls):
        """
        Préparation de l'environnement de test avant l'exécution des tests
        """
        # Configuration de l'environnement de test
        cls.env_file, cls.wallet_paths = setup_test_environment()
        cls.test_password = "test_secure_password_123!"
        
        # Chemins temporaires pour les tests
        cls.temp_dir = tempfile.mkdtemp(prefix="wallet_encryption_test_")
        cls.encrypted_wallet_path = os.path.join(cls.temp_dir, "encrypted_wallet.json")
        
        # Contenu d'un wallet de test
        cls.test_wallet_data = {
            "private_key": "0x1111111111111111111111111111111111111111111111111111111111111111",
            "address": "0xTestWallet1234567890",
            "blockchain": "avalanche",
            "is_test_wallet": True
        }
        
        # Créer un fichier de wallet de test
        cls.test_wallet_path = os.path.join(cls.temp_dir, "test_wallet.json")
        with open(cls.test_wallet_path, "w") as f:
            json.dump(cls.test_wallet_data, f, indent=2)
    
    @classmethod
    def tearDownClass(cls):
        """
        Nettoyage après l'exécution de tous les tests
        """
        # Supprimer les fichiers temporaires
        for file_path in [cls.test_wallet_path, cls.encrypted_wallet_path]:
            if os.path.exists(file_path):
                os.remove(file_path)
        
        if os.path.exists(cls.temp_dir):
            os.rmdir(cls.temp_dir)
        
        # Nettoyer l'environnement de test
        cleanup_test_environment(cls.env_file, cls.wallet_paths)
    
    def setUp(self):
        """
        Préparation avant chaque test
        """
        # Tenter d'importer le module de chiffrement, avec gestion des erreurs
        try:
            from gbpbot.security.wallet_encryption import WalletEncryption
            self.encryption_module = WalletEncryption
        except ImportError as e:
            self.skipTest(f"Module de chiffrement non disponible: {str(e)}")
    
    def test_module_import(self):
        """
        Test de l'importation du module de chiffrement
        """
        # Vérifier que le module a été importé correctement
        self.assertIsNotNone(self.encryption_module, "Le module de chiffrement n'a pas pu être importé")
    
    def test_encryption_availability(self):
        """
        Test de la disponibilité du chiffrement
        """
        # Instancier le module
        encryption = self.encryption_module()
        
        # Vérifier si le chiffrement est disponible
        self.assertTrue(encryption.encryption_available, 
                        "Le chiffrement devrait être disponible avec les bibliothèques installées")
    
    @patch("gbpbot.security.wallet_encryption.WalletEncryption.encryption_available", return_value=True)
    def test_encrypt_wallet(self, mock_encryption_available):
        """
        Test du chiffrement d'un wallet
        """
        # Instancier le module
        encryption = self.encryption_module()
        
        # Chiffrer le wallet de test
        result = encryption.encrypt_wallet(
            wallet_path=self.test_wallet_path, 
            password=self.test_password,
            output_path=self.encrypted_wallet_path
        )
        
        # Vérifier le résultat
        self.assertTrue(result, "Le chiffrement du wallet a échoué")
        self.assertTrue(os.path.exists(self.encrypted_wallet_path), 
                       "Le fichier de wallet chiffré n'a pas été créé")
        
        # Lire le fichier chiffré et vérifier sa structure
        with open(self.encrypted_wallet_path, "r") as f:
            encrypted_data = json.load(f)
        
        # Vérifier que le fichier chiffré a les champs nécessaires
        self.assertIn("encrypted_data", encrypted_data, "Données chiffrées manquantes")
        self.assertIn("salt", encrypted_data, "Sel manquant")
        self.assertIn("nonce", encrypted_data, "Nonce manquant")
        self.assertIn("tag", encrypted_data, "Tag manquant")
    
    @patch("gbpbot.security.wallet_encryption.WalletEncryption.encryption_available", return_value=True)
    def test_decrypt_wallet(self, mock_encryption_available):
        """
        Test du déchiffrement d'un wallet
        """
        # Instancier le module
        encryption = self.encryption_module()
        
        # D'abord chiffrer le wallet
        encryption.encrypt_wallet(
            wallet_path=self.test_wallet_path, 
            password=self.test_password,
            output_path=self.encrypted_wallet_path
        )
        
        # Ensuite déchiffrer le wallet
        decrypted_data = encryption.decrypt_wallet(
            encrypted_wallet_path=self.encrypted_wallet_path,
            password=self.test_password
        )
        
        # Vérifier que les données déchiffrées correspondent aux données originales
        self.assertIsNotNone(decrypted_data, "Le déchiffrement a échoué")
        self.assertEqual(decrypted_data["private_key"], self.test_wallet_data["private_key"],
                        "La clé privée déchiffrée ne correspond pas à l'originale")
        self.assertEqual(decrypted_data["address"], self.test_wallet_data["address"],
                        "L'adresse déchiffrée ne correspond pas à l'originale")
    
    @patch("gbpbot.security.wallet_encryption.WalletEncryption.encryption_available", return_value=True)
    def test_wrong_password(self, mock_encryption_available):
        """
        Test avec un mot de passe incorrect
        """
        # Instancier le module
        encryption = self.encryption_module()
        
        # D'abord chiffrer le wallet
        encryption.encrypt_wallet(
            wallet_path=self.test_wallet_path, 
            password=self.test_password,
            output_path=self.encrypted_wallet_path
        )
        
        # Tenter de déchiffrer avec un mauvais mot de passe
        wrong_password = "wrong_password_123"
        decrypted_data = encryption.decrypt_wallet(
            encrypted_wallet_path=self.encrypted_wallet_path,
            password=wrong_password
        )
        
        # Le déchiffrement devrait échouer
        self.assertIsNone(decrypted_data, 
                         "Le déchiffrement aurait dû échouer avec un mot de passe incorrect")
    
    @patch("gbpbot.security.wallet_encryption.WalletEncryption.encryption_available", return_value=True)
    def test_file_not_found(self, mock_encryption_available):
        """
        Test avec un fichier inexistant
        """
        # Instancier le module
        encryption = self.encryption_module()
        
        # Tenter d'utiliser un fichier inexistant
        non_existent_file = os.path.join(self.temp_dir, "non_existent_wallet.json")
        
        # Test de chiffrement
        result = encryption.encrypt_wallet(
            wallet_path=non_existent_file, 
            password=self.test_password,
            output_path=self.encrypted_wallet_path
        )
        self.assertFalse(result, "Le chiffrement aurait dû échouer avec un fichier inexistant")
        
        # Test de déchiffrement
        decrypted_data = encryption.decrypt_wallet(
            encrypted_wallet_path=non_existent_file,
            password=self.test_password
        )
        self.assertIsNone(decrypted_data, 
                         "Le déchiffrement aurait dû échouer avec un fichier inexistant")
    
    @patch("gbpbot.security.wallet_encryption.WalletEncryption.encryption_available", return_value=False)
    def test_encryption_unavailable(self, mock_encryption_available):
        """
        Test quand le chiffrement n'est pas disponible
        """
        # Instancier le module
        encryption = self.encryption_module()
        
        # Tenter de chiffrer quand le chiffrement n'est pas disponible
        result = encryption.encrypt_wallet(
            wallet_path=self.test_wallet_path, 
            password=self.test_password,
            output_path=self.encrypted_wallet_path
        )
        self.assertFalse(result, "Le chiffrement aurait dû échouer si non disponible")
        
        # Tenter de déchiffrer quand le chiffrement n'est pas disponible
        decrypted_data = encryption.decrypt_wallet(
            encrypted_wallet_path=self.encrypted_wallet_path,
            password=self.test_password
        )
        self.assertIsNone(decrypted_data, "Le déchiffrement aurait dû échouer si non disponible")


if __name__ == "__main__":
    unittest.main() 