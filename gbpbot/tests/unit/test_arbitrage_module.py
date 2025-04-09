#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests unitaires pour le module d'arbitrage

Ce module teste les fonctionnalités du module d'arbitrage entre DEX,
qui est crucial pour détecter et exploiter les écarts de prix entre différentes plateformes.
"""

import os
import sys
import json
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock, PropertyMock

# Ajout du chemin racine au sys.path pour les imports
ROOT_DIR = Path(__file__).parent.parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Import des modules de test
from gbpbot.tests.setup_test_environment import setup_test_environment, cleanup_test_environment


class TestArbitrageModule(unittest.TestCase):
    """Suite de tests pour le module d'arbitrage entre DEX"""
    
    @classmethod
    def setUpClass(cls):
        """
        Préparation de l'environnement de test avant l'exécution des tests
        """
        # Configuration de l'environnement de test
        cls.env_file, cls.wallet_paths = setup_test_environment()
        
        # Exemple de paires pour l'arbitrage
        cls.pairs = [
            {
                "token_a": "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E",  # USDC
                "token_b": "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",  # AVAX
                "name": "USDC-AVAX"
            },
            {
                "token_a": "0x9702230A8Ea53601f5cD2dc00fDBc13d4dF4A8c7",  # USDT
                "token_b": "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",  # AVAX
                "name": "USDT-AVAX"
            }
        ]
        
        # DEX pour l'arbitrage
        cls.dexes = [
            {"name": "TraderJoe", "router": "0x60aE616a2155Ee3d9A68541Ba4544862310933d4"},
            {"name": "Pangolin", "router": "0xE54Ca86531e17Ef3616d22Ca28b0D458b6C89106"}
        ]
        
        # Configuration pour les tests
        cls.test_config = {
            "min_profit_threshold": 0.5,  # 0.5% de profit minimum
            "max_slippage": 1.0,          # 1% de slippage maximum
            "gas_price_multiplier": 1.2,   # 20% en plus pour le gas
            "max_trade_amount_usd": 1000,  # Montant max par trade
            "transaction_timeout": 30      # Timeout en secondes
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
        # Tenter d'importer le module d'arbitrage, avec gestion des erreurs
        try:
            from gbpbot.strategies.cross_dex_arbitrage import CrossDexArbitrageEngine
            self.arbitrage_class = CrossDexArbitrageEngine
        except ImportError as e:
            self.skipTest(f"Module d'arbitrage non disponible: {str(e)}")
    
    def test_module_import(self):
        """
        Test de l'importation du module d'arbitrage
        """
        # Vérifier que le module a été importé correctement
        self.assertIsNotNone(self.arbitrage_class, "Le module d'arbitrage n'a pas pu être importé")
    
    @patch("gbpbot.strategies.cross_dex_arbitrage.CrossDexArbitrageEngine._initialize_blockchain_client")
    @patch("gbpbot.strategies.cross_dex_arbitrage.CrossDexArbitrageEngine._setup_wallet")
    def test_arbitrage_initialization(self, mock_setup_wallet, mock_init_blockchain):
        """
        Test de l'initialisation du moteur d'arbitrage
        """
        # Mock des dépendances
        mock_init_blockchain.return_value = True
        mock_setup_wallet.return_value = True
        
        # Instancier le moteur d'arbitrage
        arbitrage = self.arbitrage_class(
            blockchain="avalanche",
            config=self.test_config,
            wallet_path=self.wallet_paths.get("avalanche", "")
        )
        
        # Vérifier l'initialisation
        self.assertIsNotNone(arbitrage, "Le moteur d'arbitrage n'a pas été instancié correctement")
        self.assertEqual(arbitrage.blockchain, "avalanche", "La blockchain n'a pas été correctement définie")
        self.assertTrue(mock_init_blockchain.called, "La méthode d'initialisation blockchain n'a pas été appelée")
        self.assertTrue(mock_setup_wallet.called, "La méthode de configuration du wallet n'a pas été appelée")
    
    @patch("gbpbot.strategies.cross_dex_arbitrage.CrossDexArbitrageEngine._initialize_blockchain_client")
    @patch("gbpbot.strategies.cross_dex_arbitrage.CrossDexArbitrageEngine._setup_wallet")
    @patch("gbpbot.strategies.cross_dex_arbitrage.CrossDexArbitrageEngine._get_pair_price")
    def test_check_arbitrage_opportunity(self, mock_get_price, mock_setup_wallet, mock_init_blockchain):
        """
        Test de la vérification des opportunités d'arbitrage
        """
        # Mock des dépendances
        mock_init_blockchain.return_value = True
        mock_setup_wallet.return_value = True
        
        # Configurer le mock pour _get_pair_price (différents prix sur différents DEX)
        # Première paire: USDC-AVAX
        # Deuxième paire: USDT-AVAX
        prices = {
            # Prix sur TraderJoe
            (self.pairs[0], self.dexes[0]): 30.5,  # 1 AVAX = 30.5 USDC sur TraderJoe
            (self.pairs[1], self.dexes[0]): 30.6,  # 1 AVAX = 30.6 USDT sur TraderJoe
            
            # Prix sur Pangolin
            (self.pairs[0], self.dexes[1]): 30.75,  # 1 AVAX = 30.75 USDC sur Pangolin (plus cher)
            (self.pairs[1], self.dexes[1]): 30.45,  # 1 AVAX = 30.45 USDT sur Pangolin (moins cher)
        }
        
        def mock_get_price_side_effect(pair, dex):
            return prices.get((pair, dex), 0)
        
        mock_get_price.side_effect = mock_get_price_side_effect
        
        # Instancier le moteur d'arbitrage
        arbitrage = self.arbitrage_class(
            blockchain="avalanche",
            config=self.test_config,
            wallet_path=self.wallet_paths.get("avalanche", "")
        )
        
        # Définir manuellement les DEX et les paires
        arbitrage.dexes = self.dexes
        arbitrage.pairs = self.pairs
        
        # Tester la vérification des opportunités
        opportunities = arbitrage.check_arbitrage_opportunities()
        
        # Vérifier qu'il y a des opportunités détectées
        self.assertTrue(len(opportunities) > 0, "Aucune opportunité d'arbitrage détectée")
        
        # Vérifier les opportunités détectées
        for opportunity in opportunities:
            self.assertIn("pair", opportunity, "L'opportunité n'a pas de champ 'pair'")
            self.assertIn("buy_dex", opportunity, "L'opportunité n'a pas de champ 'buy_dex'")
            self.assertIn("sell_dex", opportunity, "L'opportunité n'a pas de champ 'sell_dex'")
            self.assertIn("buy_price", opportunity, "L'opportunité n'a pas de champ 'buy_price'")
            self.assertIn("sell_price", opportunity, "L'opportunité n'a pas de champ 'sell_price'")
            self.assertIn("profit_percent", opportunity, "L'opportunité n'a pas de champ 'profit_percent'")
            
            # Vérifier que le profit est supérieur au seuil
            self.assertGreaterEqual(opportunity["profit_percent"], self.test_config["min_profit_threshold"],
                                  "Le profit détecté est inférieur au seuil minimum")
    
    @patch("gbpbot.strategies.cross_dex_arbitrage.CrossDexArbitrageEngine._initialize_blockchain_client")
    @patch("gbpbot.strategies.cross_dex_arbitrage.CrossDexArbitrageEngine._setup_wallet")
    @patch("gbpbot.strategies.cross_dex_arbitrage.CrossDexArbitrageEngine._execute_buy_transaction")
    @patch("gbpbot.strategies.cross_dex_arbitrage.CrossDexArbitrageEngine._execute_sell_transaction")
    def test_execute_arbitrage(self, mock_execute_sell, mock_execute_buy, mock_setup_wallet, mock_init_blockchain):
        """
        Test de l'exécution d'un arbitrage
        """
        # Mock des dépendances
        mock_init_blockchain.return_value = True
        mock_setup_wallet.return_value = True
        
        # Configuration des mocks d'exécution
        mock_execute_buy.return_value = {
            "success": True,
            "transaction_hash": "0xTestBuyTransactionHash",
            "amount_in": 100,  # 100 USDC
            "amount_out": 3.2,  # 3.2 AVAX
            "token_price": 31.25,  # 1 AVAX = 31.25 USDC
            "gas_used": 200000,
            "gas_price": 30000000000  # 30 Gwei
        }
        
        mock_execute_sell.return_value = {
            "success": True,
            "transaction_hash": "0xTestSellTransactionHash",
            "amount_in": 3.2,  # 3.2 AVAX
            "amount_out": 102,  # 102 USDC
            "token_price": 31.875,  # 1 AVAX = 31.875 USDC
            "gas_used": 180000,
            "gas_price": 32000000000  # 32 Gwei
        }
        
        # Instancier le moteur d'arbitrage
        arbitrage = self.arbitrage_class(
            blockchain="avalanche",
            config=self.test_config,
            wallet_path=self.wallet_paths.get("avalanche", "")
        )
        
        # Définir l'opportunité d'arbitrage
        opportunity = {
            "pair": self.pairs[0],  # USDC-AVAX
            "buy_dex": self.dexes[0],  # TraderJoe
            "sell_dex": self.dexes[1],  # Pangolin
            "buy_price": 31.25,  # 1 AVAX = 31.25 USDC sur TraderJoe
            "sell_price": 31.875,  # 1 AVAX = 31.875 USDC sur Pangolin
            "profit_percent": 2.0  # 2% de profit attendu
        }
        
        # Tester l'exécution de l'arbitrage
        result = arbitrage.execute_arbitrage(opportunity, amount=100)  # 100 USDC
        
        # Vérifier le résultat
        self.assertTrue(result["success"], "L'arbitrage aurait dû réussir")
        self.assertTrue(mock_execute_buy.called, "La méthode d'exécution d'achat n'a pas été appelée")
        self.assertTrue(mock_execute_sell.called, "La méthode d'exécution de vente n'a pas été appelée")
        
        # Vérifier les détails du résultat
        self.assertIn("buy_transaction", result, "Pas de transaction d'achat dans le résultat")
        self.assertIn("sell_transaction", result, "Pas de transaction de vente dans le résultat")
        self.assertIn("profit_usd", result, "Pas de profit USD dans le résultat")
        self.assertIn("profit_percent", result, "Pas de pourcentage de profit dans le résultat")
        
        # Vérifier le calcul du profit
        expected_profit = 102 - 100  # 102 USDC reçus - 100 USDC dépensés
        self.assertAlmostEqual(
            result["profit_usd"], 
            expected_profit, 
            places=1,  # Précision à 1 décimale près
            msg="Le profit USD n'est pas calculé correctement"
        )
    
    @patch("gbpbot.strategies.cross_dex_arbitrage.CrossDexArbitrageEngine._initialize_blockchain_client")
    @patch("gbpbot.strategies.cross_dex_arbitrage.CrossDexArbitrageEngine._setup_wallet")
    @patch("gbpbot.strategies.cross_dex_arbitrage.CrossDexArbitrageEngine._get_pair_price")
    def test_no_arbitrage_opportunity(self, mock_get_price, mock_setup_wallet, mock_init_blockchain):
        """
        Test du cas où il n'y a pas d'opportunité d'arbitrage
        """
        # Mock des dépendances
        mock_init_blockchain.return_value = True
        mock_setup_wallet.return_value = True
        
        # Configurer le mock pour _get_pair_price (prix similaires sans opportunité)
        # Première paire: USDC-AVAX
        # Deuxième paire: USDT-AVAX
        prices = {
            # Prix sur TraderJoe
            (self.pairs[0], self.dexes[0]): 30.5,  # 1 AVAX = 30.5 USDC sur TraderJoe
            (self.pairs[1], self.dexes[0]): 30.6,  # 1 AVAX = 30.6 USDT sur TraderJoe
            
            # Prix sur Pangolin (écarts inférieurs au seuil de profit)
            (self.pairs[0], self.dexes[1]): 30.55,  # 1 AVAX = 30.55 USDC sur Pangolin
            (self.pairs[1], self.dexes[1]): 30.58,  # 1 AVAX = 30.58 USDT sur Pangolin
        }
        
        def mock_get_price_side_effect(pair, dex):
            return prices.get((pair, dex), 0)
        
        mock_get_price.side_effect = mock_get_price_side_effect
        
        # Instancier le moteur d'arbitrage avec seuil de profit élevé
        high_threshold_config = self.test_config.copy()
        high_threshold_config["min_profit_threshold"] = 1.0  # 1% minimum
        
        arbitrage = self.arbitrage_class(
            blockchain="avalanche",
            config=high_threshold_config,
            wallet_path=self.wallet_paths.get("avalanche", "")
        )
        
        # Définir manuellement les DEX et les paires
        arbitrage.dexes = self.dexes
        arbitrage.pairs = self.pairs
        
        # Tester la vérification des opportunités
        opportunities = arbitrage.check_arbitrage_opportunities()
        
        # Vérifier qu'il n'y a pas d'opportunités détectées
        self.assertEqual(len(opportunities), 0, "Des opportunités d'arbitrage ont été détectées alors qu'il ne devrait pas y en avoir")
    
    @patch("gbpbot.strategies.cross_dex_arbitrage.CrossDexArbitrageEngine._initialize_blockchain_client")
    @patch("gbpbot.strategies.cross_dex_arbitrage.CrossDexArbitrageEngine._setup_wallet")
    @patch("gbpbot.strategies.cross_dex_arbitrage.CrossDexArbitrageEngine._execute_buy_transaction")
    @patch("gbpbot.strategies.cross_dex_arbitrage.CrossDexArbitrageEngine._execute_sell_transaction")
    def test_failed_arbitrage(self, mock_execute_sell, mock_execute_buy, mock_setup_wallet, mock_init_blockchain):
        """
        Test du cas où l'arbitrage échoue
        """
        # Mock des dépendances
        mock_init_blockchain.return_value = True
        mock_setup_wallet.return_value = True
        
        # Configuration des mocks - l'achat réussit mais la vente échoue
        mock_execute_buy.return_value = {
            "success": True,
            "transaction_hash": "0xTestBuyTransactionHash",
            "amount_in": 100,  # 100 USDC
            "amount_out": 3.2,  # 3.2 AVAX
            "token_price": 31.25,  # 1 AVAX = 31.25 USDC
            "gas_used": 200000,
            "gas_price": 30000000000  # 30 Gwei
        }
        
        mock_execute_sell.return_value = {
            "success": False,
            "error": "Transaction rejected",
            "gas_used": 0,
            "gas_price": 32000000000  # 32 Gwei
        }
        
        # Instancier le moteur d'arbitrage
        arbitrage = self.arbitrage_class(
            blockchain="avalanche",
            config=self.test_config,
            wallet_path=self.wallet_paths.get("avalanche", "")
        )
        
        # Définir l'opportunité d'arbitrage
        opportunity = {
            "pair": self.pairs[0],  # USDC-AVAX
            "buy_dex": self.dexes[0],  # TraderJoe
            "sell_dex": self.dexes[1],  # Pangolin
            "buy_price": 31.25,  # 1 AVAX = 31.25 USDC sur TraderJoe
            "sell_price": 31.875,  # 1 AVAX = 31.875 USDC sur Pangolin
            "profit_percent": 2.0  # 2% de profit attendu
        }
        
        # Tester l'exécution de l'arbitrage
        result = arbitrage.execute_arbitrage(opportunity, amount=100)  # 100 USDC
        
        # Vérifier le résultat
        self.assertFalse(result["success"], "L'arbitrage aurait dû échouer")
        self.assertTrue(mock_execute_buy.called, "La méthode d'exécution d'achat n'a pas été appelée")
        self.assertTrue(mock_execute_sell.called, "La méthode d'exécution de vente n'a pas été appelée")
        
        # Vérifier les détails du résultat
        self.assertIn("buy_transaction", result, "Pas de transaction d'achat dans le résultat")
        self.assertIn("sell_transaction", result, "Pas de transaction de vente dans le résultat")
        self.assertIn("error", result, "Pas d'erreur dans le résultat")


if __name__ == "__main__":
    unittest.main() 