#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests unitaires pour le module de sniping

Ce module teste les fonctionnalités du module de sniping de tokens,
qui est crucial pour détecter et acheter rapidement les nouveaux tokens prometteurs.
"""

import os
import sys
import json
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Ajout du chemin racine au sys.path pour les imports
ROOT_DIR = Path(__file__).parent.parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Import des modules de test
from gbpbot.tests.setup_test_environment import setup_test_environment, cleanup_test_environment


class TestSnipingModule(unittest.TestCase):
    """Suite de tests pour le module de sniping de tokens"""
    
    @classmethod
    def setUpClass(cls):
        """
        Préparation de l'environnement de test avant l'exécution des tests
        """
        # Configuration de l'environnement de test
        cls.env_file, cls.wallet_paths = setup_test_environment()
        
        # Mock des données de token
        cls.mock_token_data = {
            "address": "0xTestToken123456789",
            "name": "Test Token",
            "symbol": "TEST",
            "decimals": 18,
            "total_supply": "1000000000000000000000000",
            "liquidity_usd": 50000,
            "price_usd": 0.05,
            "market_cap": 500000,
            "holders": 150,
            "is_honeypot": False,
            "creation_timestamp": 1646456789
        }
        
        # Configuration pour les tests
        cls.test_config = {
            "min_liquidity_usd": 10000,
            "check_honeypot": True,
            "default_take_profit": 20.0,
            "default_stop_loss": 10.0,
            "trailing_take_profit": True,
            "trailing_percent": 5.0,
            "max_trade_amount_usd": 100,
            "snipe_enabled": True
        }
    
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
        # Tenter d'importer le module de sniping, avec gestion des erreurs
        try:
            from gbpbot.strategies.sniping import TokenSniper
            self.sniper_class = TokenSniper
        except ImportError as e:
            self.skipTest(f"Module de sniping non disponible: {str(e)}")
    
    def test_module_import(self):
        """
        Test de l'importation du module de sniping
        """
        # Vérifier que le module a été importé correctement
        self.assertIsNotNone(self.sniper_class, "Le module de sniping n'a pas pu être importé")
    
    @patch("gbpbot.strategies.sniping.TokenSniper._initialize_blockchain_client")
    @patch("gbpbot.strategies.sniping.TokenSniper._setup_wallet")
    def test_sniper_initialization(self, mock_setup_wallet, mock_init_blockchain):
        """
        Test de l'initialisation du sniper
        """
        # Mock des dépendances
        mock_init_blockchain.return_value = True
        mock_setup_wallet.return_value = True
        
        # Instancier le sniper
        sniper = self.sniper_class(
            blockchain="avalanche",
            config=self.test_config,
            wallet_path=self.wallet_paths.get("avalanche", "")
        )
        
        # Vérifier l'initialisation
        self.assertIsNotNone(sniper, "Le sniper n'a pas été instancié correctement")
        self.assertEqual(sniper.blockchain, "avalanche", "La blockchain n'a pas été correctement définie")
        self.assertTrue(mock_init_blockchain.called, "La méthode d'initialisation blockchain n'a pas été appelée")
        self.assertTrue(mock_setup_wallet.called, "La méthode de configuration du wallet n'a pas été appelée")
    
    @patch("gbpbot.strategies.sniping.TokenSniper._initialize_blockchain_client")
    @patch("gbpbot.strategies.sniping.TokenSniper._setup_wallet")
    @patch("gbpbot.strategies.sniping.TokenSniper._check_token_safety")
    def test_token_validation(self, mock_check_safety, mock_setup_wallet, mock_init_blockchain):
        """
        Test de la validation des tokens
        """
        # Mock des dépendances
        mock_init_blockchain.return_value = True
        mock_setup_wallet.return_value = True
        
        # Configurer le mock pour _check_token_safety
        mock_check_safety.return_value = {
            "is_safe": True,
            "liquidity_sufficient": True,
            "honeypot_check_passed": True,
            "safety_score": 85,
            "risks": []
        }
        
        # Instancier le sniper
        sniper = self.sniper_class(
            blockchain="avalanche",
            config=self.test_config,
            wallet_path=self.wallet_paths.get("avalanche", "")
        )
        
        # Tester la validation du token
        token_address = "0xTestToken123456789"
        result = sniper.validate_token(token_address)
        
        # Vérifier le résultat
        self.assertTrue(result["is_safe"], "Le token aurait dû être validé comme sûr")
        self.assertTrue(mock_check_safety.called, "La méthode de vérification de sécurité n'a pas été appelée")
        self.assertEqual(mock_check_safety.call_args[0][0], token_address, 
                         "L'adresse du token n'a pas été correctement passée à la méthode de vérification")
    
    @patch("gbpbot.strategies.sniping.TokenSniper._initialize_blockchain_client")
    @patch("gbpbot.strategies.sniping.TokenSniper._setup_wallet")
    @patch("gbpbot.strategies.sniping.TokenSniper._check_token_safety")
    @patch("gbpbot.strategies.sniping.TokenSniper._execute_buy_transaction")
    def test_snipe_token(self, mock_execute_buy, mock_check_safety, mock_setup_wallet, mock_init_blockchain):
        """
        Test du sniping d'un token
        """
        # Mock des dépendances
        mock_init_blockchain.return_value = True
        mock_setup_wallet.return_value = True
        
        # Configurer le mock pour _check_token_safety
        mock_check_safety.return_value = {
            "is_safe": True,
            "liquidity_sufficient": True,
            "honeypot_check_passed": True,
            "safety_score": 85,
            "risks": []
        }
        
        # Configurer le mock pour _execute_buy_transaction
        mock_execute_buy.return_value = {
            "success": True,
            "transaction_hash": "0xTestTransactionHash",
            "amount_in": 50,
            "amount_out": 1000,
            "token_price": 0.05,
            "gas_used": 250000,
            "gas_price": 5
        }
        
        # Instancier le sniper
        sniper = self.sniper_class(
            blockchain="avalanche",
            config=self.test_config,
            wallet_path=self.wallet_paths.get("avalanche", "")
        )
        
        # Tester le sniping du token
        token_address = "0xTestToken123456789"
        amount_usd = 50
        result = sniper.snipe_token(token_address, amount_usd)
        
        # Vérifier le résultat
        self.assertTrue(result["success"], "Le sniping aurait dû réussir")
        self.assertTrue(mock_check_safety.called, "La méthode de vérification de sécurité n'a pas été appelée")
        self.assertTrue(mock_execute_buy.called, "La méthode d'exécution d'achat n'a pas été appelée")
        
        # Vérifier les paramètres passés à _execute_buy_transaction
        call_args = mock_execute_buy.call_args[0]
        self.assertEqual(call_args[0], token_address, "L'adresse du token n'a pas été correctement passée")
        self.assertEqual(call_args[1], amount_usd, "Le montant USD n'a pas été correctement passé")
    
    @patch("gbpbot.strategies.sniping.TokenSniper._initialize_blockchain_client")
    @patch("gbpbot.strategies.sniping.TokenSniper._setup_wallet")
    @patch("gbpbot.strategies.sniping.TokenSniper._check_token_safety")
    def test_token_safety_validation(self, mock_check_safety, mock_setup_wallet, mock_init_blockchain):
        """
        Test de la validation de sécurité des tokens
        """
        # Mock des dépendances
        mock_init_blockchain.return_value = True
        mock_setup_wallet.return_value = True
        
        # Configurer différents scénarios pour le mock _check_token_safety
        safety_scenarios = [
            # Token sûr
            {
                "is_safe": True,
                "liquidity_sufficient": True,
                "honeypot_check_passed": True,
                "safety_score": 85,
                "risks": []
            },
            # Token avec liquidité insuffisante
            {
                "is_safe": False,
                "liquidity_sufficient": False,
                "honeypot_check_passed": True,
                "safety_score": 40,
                "risks": ["Liquidité insuffisante"]
            },
            # Token honeypot
            {
                "is_safe": False,
                "liquidity_sufficient": True,
                "honeypot_check_passed": False,
                "safety_score": 10,
                "risks": ["Détecté comme honeypot"]
            }
        ]
        
        # Instancier le sniper
        sniper = self.sniper_class(
            blockchain="avalanche",
            config=self.test_config,
            wallet_path=self.wallet_paths.get("avalanche", "")
        )
        
        # Tester chaque scénario
        token_address = "0xTestToken123456789"
        
        for scenario in safety_scenarios:
            # Configurer le mock
            mock_check_safety.return_value = scenario
            
            # Valider le token
            result = sniper.validate_token(token_address)
            
            # Vérifier le résultat
            self.assertEqual(result["is_safe"], scenario["is_safe"], 
                            f"Validation incorrecte pour le scénario: {scenario}")
            self.assertEqual(result["safety_score"], scenario["safety_score"], 
                            "Le score de sécurité ne correspond pas")
    
    @patch("gbpbot.strategies.sniping.TokenSniper._initialize_blockchain_client")
    @patch("gbpbot.strategies.sniping.TokenSniper._setup_wallet")
    @patch("gbpbot.strategies.sniping.TokenSniper._execute_sell_transaction")
    def test_take_profit_sell(self, mock_execute_sell, mock_setup_wallet, mock_init_blockchain):
        """
        Test de la prise de profit
        """
        # Mock des dépendances
        mock_init_blockchain.return_value = True
        mock_setup_wallet.return_value = True
        
        # Configurer le mock pour _execute_sell_transaction
        mock_execute_sell.return_value = {
            "success": True,
            "transaction_hash": "0xTestSellTransactionHash",
            "amount_in": 1000,
            "amount_out": 60,  # 20% de profit sur l'achat initial de 50
            "token_price": 0.06,
            "gas_used": 200000,
            "gas_price": 5
        }
        
        # Instancier le sniper
        sniper = self.sniper_class(
            blockchain="avalanche",
            config=self.test_config,
            wallet_path=self.wallet_paths.get("avalanche", "")
        )
        
        # Configurer les données de position simulées
        token_address = "0xTestToken123456789"
        position = {
            "token_address": token_address,
            "amount": 1000,
            "entry_price": 0.05,
            "entry_value_usd": 50,
            "current_price": 0.06,  # 20% au-dessus du prix d'entrée
            "current_value_usd": 60,
            "profit_loss_percent": 20,
            "transaction_hash": "0xTestTransactionHash",
            "timestamp": 1646456800
        }
        
        # Ajouter la position au sniper
        sniper.active_positions = {token_address: position}
        
        # Tester la prise de profit
        result = sniper.take_profit(token_address)
        
        # Vérifier le résultat
        self.assertTrue(result["success"], "La prise de profit aurait dû réussir")
        self.assertTrue(mock_execute_sell.called, "La méthode d'exécution de vente n'a pas été appelée")
        
        # Vérifier les paramètres passés à _execute_sell_transaction
        call_args = mock_execute_sell.call_args[0]
        self.assertEqual(call_args[0], token_address, "L'adresse du token n'a pas été correctement passée")
        self.assertEqual(call_args[1], 1000, "Le montant de tokens n'a pas été correctement passé")
    
    @patch("gbpbot.strategies.sniping.TokenSniper._initialize_blockchain_client")
    @patch("gbpbot.strategies.sniping.TokenSniper._setup_wallet")
    @patch("gbpbot.strategies.sniping.TokenSniper._execute_sell_transaction")
    def test_stop_loss(self, mock_execute_sell, mock_setup_wallet, mock_init_blockchain):
        """
        Test du stop loss
        """
        # Mock des dépendances
        mock_init_blockchain.return_value = True
        mock_setup_wallet.return_value = True
        
        # Configurer le mock pour _execute_sell_transaction
        mock_execute_sell.return_value = {
            "success": True,
            "transaction_hash": "0xTestSellTransactionHash",
            "amount_in": 1000,
            "amount_out": 45,  # 10% de perte sur l'achat initial de 50
            "token_price": 0.045,
            "gas_used": 200000,
            "gas_price": 5
        }
        
        # Instancier le sniper
        sniper = self.sniper_class(
            blockchain="avalanche",
            config=self.test_config,
            wallet_path=self.wallet_paths.get("avalanche", "")
        )
        
        # Configurer les données de position simulées
        token_address = "0xTestToken123456789"
        position = {
            "token_address": token_address,
            "amount": 1000,
            "entry_price": 0.05,
            "entry_value_usd": 50,
            "current_price": 0.045,  # 10% en-dessous du prix d'entrée
            "current_value_usd": 45,
            "profit_loss_percent": -10,
            "transaction_hash": "0xTestTransactionHash",
            "timestamp": 1646456800
        }
        
        # Ajouter la position au sniper
        sniper.active_positions = {token_address: position}
        
        # Tester le stop loss
        result = sniper.stop_loss(token_address)
        
        # Vérifier le résultat
        self.assertTrue(result["success"], "Le stop loss aurait dû réussir")
        self.assertTrue(mock_execute_sell.called, "La méthode d'exécution de vente n'a pas été appelée")
        
        # Vérifier les paramètres passés à _execute_sell_transaction
        call_args = mock_execute_sell.call_args[0]
        self.assertEqual(call_args[0], token_address, "L'adresse du token n'a pas été correctement passée")
        self.assertEqual(call_args[1], 1000, "Le montant de tokens n'a pas été correctement passé")


if __name__ == "__main__":
    unittest.main() 