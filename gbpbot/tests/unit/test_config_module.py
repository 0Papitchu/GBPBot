#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests unitaires pour le module de configuration du GBPBot

Ce module teste les fonctionnalités de gestion de la configuration,
notamment le chargement des paramètres, la validation et le chiffrement
des données sensibles comme les clés API et les wallets.
"""

import os
import sys
import json
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

# Ajout du chemin racine au sys.path pour les imports
ROOT_DIR = Path(__file__).parent.parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Import des modules de test
from gbpbot.tests.setup_test_environment import setup_test_environment, cleanup_test_environment


class TestConfigModule(unittest.TestCase):
    """Suite de tests pour le module de configuration du GBPBot"""
    
    @classmethod
    def setUpClass(cls):
        """
        Préparation de l'environnement de test avant l'exécution des tests
        """
        # Configuration de l'environnement de test
        cls.env_file, cls.wallet_paths = setup_test_environment()
        
        # Configuration de test
        cls.test_config = {
            "general": {
                "environment": "testnet",
                "log_level": "INFO",
                "data_dir": "data",
                "max_concurrent_tasks": 10
            },
            "security": {
                "encryption_enabled": True,
                "encryption_key_file": "keys/encryption.key",
                "api_keys_file": "keys/api_keys.enc",
                "wallets_file": "keys/wallets.enc"
            },
            "blockchain": {
                "avalanche": {
                    "rpc_url": os.environ.get("AVALANCHE_RPC_URL", "https://api.avax-test.network/ext/bc/C/rpc"),
                    "chain_id": os.environ.get("AVALANCHE_CHAIN_ID", "43113"),
                    "websocket": os.environ.get("AVALANCHE_WEBSOCKET", "wss://api.avax-test.network/ext/bc/C/ws")
                },
                "solana": {
                    "rpc_url": os.environ.get("SOLANA_RPC_URL", "https://api.testnet.solana.com"),
                    "websocket": os.environ.get("SOLANA_WEBSOCKET_URL", "wss://api.testnet.solana.com")
                }
            },
            "api_keys": {
                "openai": "sk-test-key-not-real",
                "binance": "test-binance-key",
                "kucoin": "test-kucoin-key"
            },
            "wallets": {
                "avalanche": {
                    "address": "0xTestWalletAddress123",
                    "private_key": "test-private-key-not-real"
                },
                "solana": {
                    "address": "TestSolanaAddress123",
                    "private_key": "test-solana-private-key-not-real"
                }
            },
            "trading": {
                "max_slippage": 1.0,
                "gas_multiplier": 1.2,
                "default_amount_usd": 100,
                "max_amount_usd": 1000
            }
        }
        
        # Données sensibles de test
        cls.test_sensitive_data = {
            "api_keys": {
                "openai": "sk-test-key-not-real",
                "binance": "test-binance-key",
                "kucoin": "test-kucoin-key"
            },
            "wallets": {
                "avalanche": {
                    "address": "0xTestWalletAddress123",
                    "private_key": "test-private-key-not-real"
                },
                "solana": {
                    "address": "TestSolanaAddress123",
                    "private_key": "test-solana-private-key-not-real"
                }
            }
        }
        
        # Clé de chiffrement de test
        cls.test_encryption_key = b"test-encryption-key-12345678901234567890123456789012"
    
    @classmethod
    def tearDownClass(cls):
        """
        Nettoyage après l'exécution de tous les tests
        """
        # Nettoyer l'environnement de test
        cleanup_test_environment(cls.env_file, cls.wallet_paths)
    
    def setUp(self):
        """
        Préparation avant chaque test
        """
        # Tenter d'importer les modules de configuration, avec gestion des erreurs
        try:
            from gbpbot.core.config.config_manager import ConfigManager
            from gbpbot.core.config.encryption_manager import EncryptionManager
            from gbpbot.core.config.wallet_manager import WalletManager
            
            self.config_manager_class = ConfigManager
            self.encryption_manager_class = EncryptionManager
            self.wallet_manager_class = WalletManager
        except ImportError as e:
            self.skipTest(f"Module de configuration non disponible: {str(e)}")
    
    def test_module_import(self):
        """
        Test de l'importation du module de configuration
        """
        # Vérifier que les modules ont été importés correctement
        self.assertIsNotNone(self.config_manager_class, "La classe ConfigManager n'a pas pu être importée")
        self.assertIsNotNone(self.encryption_manager_class, "La classe EncryptionManager n'a pas pu être importée")
        self.assertIsNotNone(self.wallet_manager_class, "La classe WalletManager n'a pas pu être importée")
    
    @patch("gbpbot.core.config.config_manager.ConfigManager._load_config_file")
    def test_config_manager_initialization(self, mock_load_config):
        """
        Test de l'initialisation du gestionnaire de configuration
        """
        # Configurer le mock
        mock_load_config.return_value = self.test_config
        
        # Instancier le gestionnaire de configuration
        config_manager = self.config_manager_class()
        
        # Vérifier l'initialisation
        self.assertIsNotNone(config_manager, "Le gestionnaire de configuration n'a pas été instancié correctement")
        self.assertEqual(config_manager.config, self.test_config, "La configuration n'a pas été correctement chargée")
    
    @patch("gbpbot.core.config.config_manager.ConfigManager._validate_config")
    @patch("gbpbot.core.config.config_manager.ConfigManager._load_config_file")
    def test_config_validation(self, mock_load_config, mock_validate):
        """
        Test de la validation de la configuration
        """
        # Configurer les mocks
        mock_load_config.return_value = self.test_config
        mock_validate.return_value = True
        
        # Instancier le gestionnaire de configuration
        config_manager = self.config_manager_class()
        
        # Valider la configuration
        is_valid = config_manager.validate_config()
        
        # Vérifier la validation
        self.assertTrue(is_valid, "La configuration valide a été marquée comme invalide")
        self.assertTrue(mock_validate.called, "La méthode de validation n'a pas été appelée")
    
    @patch("gbpbot.core.config.config_manager.ConfigManager._save_config_file")
    @patch("gbpbot.core.config.config_manager.ConfigManager._load_config_file")
    def test_config_update(self, mock_load_config, mock_save_config):
        """
        Test de la mise à jour de la configuration
        """
        # Configurer les mocks
        mock_load_config.return_value = self.test_config
        mock_save_config.return_value = True
        
        # Instancier le gestionnaire de configuration
        config_manager = self.config_manager_class()
        
        # Mettre à jour la configuration
        updates = {
            "trading": {
                "max_slippage": 2.0,
                "gas_multiplier": 1.5
            }
        }
        
        success = config_manager.update_config(updates)
        
        # Vérifier la mise à jour
        self.assertTrue(success, "La mise à jour de la configuration a échoué")
        self.assertEqual(config_manager.config["trading"]["max_slippage"], 2.0, 
                       "Le paramètre max_slippage n'a pas été mis à jour")
        self.assertEqual(config_manager.config["trading"]["gas_multiplier"], 1.5, 
                       "Le paramètre gas_multiplier n'a pas été mis à jour")
        self.assertTrue(mock_save_config.called, "La méthode de sauvegarde n'a pas été appelée")
    
    @patch("gbpbot.core.config.encryption_manager.EncryptionManager._load_encryption_key")
    def test_encryption_manager_initialization(self, mock_load_key):
        """
        Test de l'initialisation du gestionnaire de chiffrement
        """
        # Configurer le mock
        mock_load_key.return_value = self.test_encryption_key
        
        # Instancier le gestionnaire de chiffrement
        encryption_manager = self.encryption_manager_class(self.test_config["security"])
        
        # Vérifier l'initialisation
        self.assertIsNotNone(encryption_manager, "Le gestionnaire de chiffrement n'a pas été instancié correctement")
        self.assertEqual(encryption_manager.encryption_key, self.test_encryption_key, 
                       "La clé de chiffrement n'a pas été correctement chargée")
    
    @patch("gbpbot.core.config.encryption_manager.EncryptionManager._load_encryption_key")
    def test_data_encryption_decryption(self, mock_load_key):
        """
        Test du chiffrement et déchiffrement des données
        """
        # Configurer le mock
        mock_load_key.return_value = self.test_encryption_key
        
        # Instancier le gestionnaire de chiffrement
        encryption_manager = self.encryption_manager_class(self.test_config["security"])
        
        # Données à chiffrer
        test_data = json.dumps(self.test_sensitive_data)
        
        # Chiffrer les données
        encrypted_data = encryption_manager.encrypt_data(test_data)
        
        # Vérifier le chiffrement
        self.assertIsNotNone(encrypted_data, "Les données chiffrées sont nulles")
        self.assertNotEqual(encrypted_data, test_data, "Les données n'ont pas été chiffrées")
        
        # Déchiffrer les données
        decrypted_data = encryption_manager.decrypt_data(encrypted_data)
        
        # Vérifier le déchiffrement
        self.assertEqual(decrypted_data, test_data, "Les données n'ont pas été correctement déchiffrées")
    
    @patch("gbpbot.core.config.wallet_manager.WalletManager._load_wallets")
    def test_wallet_manager_initialization(self, mock_load_wallets):
        """
        Test de l'initialisation du gestionnaire de wallets
        """
        # Configurer le mock
        mock_load_wallets.return_value = self.test_config["wallets"]
        
        # Instancier le gestionnaire de wallets
        wallet_manager = self.wallet_manager_class(self.test_config)
        
        # Vérifier l'initialisation
        self.assertIsNotNone(wallet_manager, "Le gestionnaire de wallets n'a pas été instancié correctement")
        self.assertEqual(wallet_manager.wallets, self.test_config["wallets"], 
                       "Les wallets n'ont pas été correctement chargés")
    
    @patch("gbpbot.core.config.wallet_manager.WalletManager._validate_wallet")
    @patch("gbpbot.core.config.wallet_manager.WalletManager._load_wallets")
    def test_wallet_validation(self, mock_load_wallets, mock_validate_wallet):
        """
        Test de la validation des wallets
        """
        # Configurer les mocks
        mock_load_wallets.return_value = self.test_config["wallets"]
        mock_validate_wallet.return_value = True
        
        # Instancier le gestionnaire de wallets
        wallet_manager = self.wallet_manager_class(self.test_config)
        
        # Valider les wallets
        for blockchain, wallet in self.test_config["wallets"].items():
            is_valid = wallet_manager.validate_wallet(blockchain, wallet)
            self.assertTrue(is_valid, f"Le wallet {blockchain} valide a été marqué comme invalide")
    
    @patch("gbpbot.core.config.wallet_manager.WalletManager._save_wallets")
    @patch("gbpbot.core.config.wallet_manager.WalletManager._load_wallets")
    def test_wallet_update(self, mock_load_wallets, mock_save_wallets):
        """
        Test de la mise à jour des wallets
        """
        # Configurer les mocks
        mock_load_wallets.return_value = self.test_config["wallets"]
        mock_save_wallets.return_value = True
        
        # Instancier le gestionnaire de wallets
        wallet_manager = self.wallet_manager_class(self.test_config)
        
        # Nouveau wallet à ajouter
        new_wallet = {
            "address": "0xNewWalletAddress789",
            "private_key": "test-new-private-key-not-real"
        }
        
        # Ajouter le nouveau wallet
        success = wallet_manager.add_wallet("avalanche", new_wallet)
        
        # Vérifier l'ajout
        self.assertTrue(success, "L'ajout du wallet a échoué")
        self.assertEqual(wallet_manager.wallets["avalanche"], new_wallet, 
                       "Le nouveau wallet n'a pas été correctement ajouté")
        self.assertTrue(mock_save_wallets.called, "La méthode de sauvegarde n'a pas été appelée")


if __name__ == "__main__":
    unittest.main() 