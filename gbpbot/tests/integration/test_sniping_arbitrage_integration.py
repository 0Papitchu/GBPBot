#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests d'intégration entre les modules de sniping et d'arbitrage

Ce module teste l'interaction entre les modules de sniping et d'arbitrage,
vérifiant qu'ils peuvent fonctionner ensemble efficacement dans des scénarios réels.
"""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Ajout du chemin racine au sys.path pour les imports
ROOT_DIR = Path(__file__).parent.parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Import des modules de test
from gbpbot.tests.setup_test_environment import setup_test_environment, cleanup_test_environment


class TestSnipingArbitrageIntegration(unittest.TestCase):
    """Suite de tests d'intégration entre les modules de sniping et d'arbitrage"""
    
    @classmethod
    def setUpClass(cls):
        """
        Préparation de l'environnement de test avant l'exécution des tests
        """
        # Configuration de l'environnement de test
        cls.env_file, cls.wallet_paths = setup_test_environment()
        
        # Configuration pour le test d'intégration
        cls.test_config = {
            "sniping": {
                "min_liquidity_usd": 10000,
                "check_honeypot": True,
                "default_take_profit": 20.0,
                "default_stop_loss": 10.0,
                "trailing_take_profit": True,
                "trailing_percent": 5.0,
                "max_trade_amount_usd": 100,
                "snipe_enabled": True
            },
            "arbitrage": {
                "min_profit_threshold": 0.5,
                "max_slippage": 1.0,
                "gas_price_multiplier": 1.2,
                "max_trade_amount_usd": 1000,
                "transaction_timeout": 30
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
            "dex": {
                "trader_joe": os.environ.get("TRADER_JOE_ROUTER", "0x60aE616a2155Ee3d9A68541Ba4544862310933d4"),
                "pangolin": os.environ.get("PANGOLIN_ROUTER", "0xE54Ca86531e17Ef3616d22Ca28b0D458b6C89106"),
                "raydium": os.environ.get("RAYDIUM_AMM_PROGRAM", "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8")
            }
        }
        
        # Token de test pour le sniping
        cls.test_token = {
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
        
        # Paires pour l'arbitrage
        cls.test_pairs = [
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
        cls.test_dexes = [
            {"name": "TraderJoe", "router": cls.test_config["dex"]["trader_joe"]},
            {"name": "Pangolin", "router": cls.test_config["dex"]["pangolin"]}
        ]
    
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
        # Tenter d'importer les modules nécessaires
        try:
            from gbpbot.strategies.sniping import TokenSniper
            from gbpbot.strategies.cross_dex_arbitrage import CrossDexArbitrageEngine
            from gbpbot.core.blockchain.blockchain_client import BlockchainClient
            
            self.sniper_class = TokenSniper
            self.arbitrage_class = CrossDexArbitrageEngine
            self.blockchain_client_class = BlockchainClient
        except ImportError as e:
            self.skipTest(f"Modules requis non disponibles: {str(e)}")
    
    @patch("gbpbot.core.blockchain.blockchain_client.BlockchainClient")
    def test_modules_import(self, mock_blockchain_client):
        """
        Test de l'importation des modules
        """
        # Vérifier que les modules ont été importés correctement
        self.assertIsNotNone(self.sniper_class, "La classe TokenSniper n'a pas pu être importée")
        self.assertIsNotNone(self.arbitrage_class, "La classe CrossDexArbitrageEngine n'a pas pu être importée")
        self.assertIsNotNone(self.blockchain_client_class, "La classe BlockchainClient n'a pas pu être importée")
    
    @patch("gbpbot.strategies.sniping.TokenSniper._initialize_blockchain_client")
    @patch("gbpbot.strategies.sniping.TokenSniper._setup_wallet")
    @patch("gbpbot.strategies.cross_dex_arbitrage.CrossDexArbitrageEngine._initialize_blockchain_client")
    @patch("gbpbot.strategies.cross_dex_arbitrage.CrossDexArbitrageEngine._setup_wallet")
    def test_modules_initialization(self, mock_arb_setup_wallet, mock_arb_init_blockchain, 
                                 mock_sniper_setup_wallet, mock_sniper_init_blockchain):
        """
        Test de l'initialisation des modules de sniping et d'arbitrage
        """
        # Mock des dépendances
        mock_sniper_init_blockchain.return_value = True
        mock_sniper_setup_wallet.return_value = True
        mock_arb_init_blockchain.return_value = True
        mock_arb_setup_wallet.return_value = True
        
        # Instancier le sniper et le moteur d'arbitrage avec le même client blockchain
        blockchain_client = MagicMock()
        
        # Créer les instances
        sniper = self.sniper_class(
            blockchain="avalanche",
            config=self.test_config["sniping"],
            blockchain_client=blockchain_client,
            wallet_path=self.wallet_paths.get("avalanche", "")
        )
        
        arbitrage = self.arbitrage_class(
            blockchain="avalanche",
            config=self.test_config["arbitrage"],
            blockchain_client=blockchain_client,
            wallet_path=self.wallet_paths.get("avalanche", "")
        )
        
        # Vérifier l'initialisation
        self.assertIsNotNone(sniper, "Le sniper n'a pas été instancié correctement")
        self.assertIsNotNone(arbitrage, "Le moteur d'arbitrage n'a pas été instancié correctement")
        
        # Vérifier que les deux modules utilisent le même client blockchain
        self.assertEqual(sniper.blockchain_client, arbitrage.blockchain_client, 
                      "Les deux modules devraient utiliser le même client blockchain")
    
    @patch("gbpbot.strategies.sniping.TokenSniper._check_token_safety")
    @patch("gbpbot.strategies.sniping.TokenSniper._execute_buy_transaction")
    @patch("gbpbot.strategies.sniping.TokenSniper._initialize_blockchain_client")
    @patch("gbpbot.strategies.sniping.TokenSniper._setup_wallet")
    @patch("gbpbot.strategies.cross_dex_arbitrage.CrossDexArbitrageEngine._get_pair_price")
    @patch("gbpbot.strategies.cross_dex_arbitrage.CrossDexArbitrageEngine._initialize_blockchain_client")
    @patch("gbpbot.strategies.cross_dex_arbitrage.CrossDexArbitrageEngine._setup_wallet")
    def test_snipe_then_arbitrage(self, mock_arb_setup_wallet, mock_arb_init_blockchain, mock_get_pair_price,
                              mock_sniper_setup_wallet, mock_sniper_init_blockchain, 
                              mock_execute_buy, mock_check_safety):
        """
        Test d'un scénario où un token est d'abord snipé puis arbitré entre DEX
        """
        # Mock des dépendances
        mock_sniper_init_blockchain.return_value = True
        mock_sniper_setup_wallet.return_value = True
        mock_arb_init_blockchain.return_value = True
        mock_arb_setup_wallet.return_value = True
        
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
        
        # Configurer le mock pour _get_pair_price (différents prix sur différents DEX)
        prices = {
            # Prix sur TraderJoe
            (self.test_pairs[0], self.test_dexes[0]): 30.5,  # 1 AVAX = 30.5 USDC sur TraderJoe
            (self.test_pairs[1], self.test_dexes[0]): 30.6,  # 1 AVAX = 30.6 USDT sur TraderJoe
            
            # Prix sur Pangolin
            (self.test_pairs[0], self.test_dexes[1]): 30.75,  # 1 AVAX = 30.75 USDC sur Pangolin (plus cher)
            (self.test_pairs[1], self.test_dexes[1]): 30.45,  # 1 AVAX = 30.45 USDT sur Pangolin (moins cher)
        }
        
        def mock_get_price_side_effect(pair, dex):
            return prices.get((pair, dex), 0)
        
        mock_get_pair_price.side_effect = mock_get_price_side_effect
        
        # Instancier le client blockchain partagé
        blockchain_client = MagicMock()
        
        # Instancier le sniper et le moteur d'arbitrage
        sniper = self.sniper_class(
            blockchain="avalanche",
            config=self.test_config["sniping"],
            blockchain_client=blockchain_client,
            wallet_path=self.wallet_paths.get("avalanche", "")
        )
        
        arbitrage = self.arbitrage_class(
            blockchain="avalanche",
            config=self.test_config["arbitrage"],
            blockchain_client=blockchain_client,
            wallet_path=self.wallet_paths.get("avalanche", "")
        )
        
        # Définir manuellement les DEX et les paires pour l'arbitrage
        arbitrage.dexes = self.test_dexes
        arbitrage.pairs = self.test_pairs
        
        # Étape 1: Sniper un nouveau token
        token_address = self.test_token["address"]
        amount_usd = 50
        snipe_result = sniper.snipe_token(token_address, amount_usd)
        
        # Vérifier le résultat du sniping
        self.assertTrue(snipe_result["success"], "Le sniping aurait dû réussir")
        self.assertTrue(mock_check_safety.called, "La méthode de vérification de sécurité n'a pas été appelée")
        self.assertTrue(mock_execute_buy.called, "La méthode d'exécution d'achat n'a pas été appelée")
        
        # Étape 2: Vérifier les opportunités d'arbitrage
        opportunities = arbitrage.check_arbitrage_opportunities()
        
        # Vérifier qu'il y a des opportunités détectées
        self.assertTrue(len(opportunities) > 0, "Aucune opportunité d'arbitrage détectée")
        
        # Vérifier les opportunités détectées
        for opportunity in opportunities:
            self.assertIn("pair", opportunity, "L'opportunité n'a pas de champ 'pair'")
            self.assertIn("buy_dex", opportunity, "L'opportunité n'a pas de champ 'buy_dex'")
            self.assertIn("sell_dex", opportunity, "L'opportunité n'a pas de champ 'sell_dex'")
            self.assertIn("profit_percent", opportunity, "L'opportunité n'a pas de champ 'profit_percent'")
            
            # Vérifier que le profit est supérieur au seuil
            self.assertGreaterEqual(opportunity["profit_percent"], 
                                 self.test_config["arbitrage"]["min_profit_threshold"],
                                 "Le profit détecté est inférieur au seuil minimum")
    
    @patch("gbpbot.strategies.sniping.TokenSniper._check_token_safety")
    @patch("gbpbot.strategies.sniping.TokenSniper._execute_buy_transaction")
    @patch("gbpbot.strategies.cross_dex_arbitrage.CrossDexArbitrageEngine._execute_buy_transaction")
    @patch("gbpbot.strategies.cross_dex_arbitrage.CrossDexArbitrageEngine._execute_sell_transaction")
    @patch("gbpbot.strategies.sniping.TokenSniper._initialize_blockchain_client")
    @patch("gbpbot.strategies.sniping.TokenSniper._setup_wallet")
    @patch("gbpbot.strategies.cross_dex_arbitrage.CrossDexArbitrageEngine._initialize_blockchain_client")
    @patch("gbpbot.strategies.cross_dex_arbitrage.CrossDexArbitrageEngine._setup_wallet")
    def test_sequential_snipe_arbitrage(self, mock_arb_setup_wallet, mock_arb_init_blockchain, 
                                    mock_sniper_setup_wallet, mock_sniper_init_blockchain,
                                    mock_arb_execute_sell, mock_arb_execute_buy, 
                                    mock_sniper_execute_buy, mock_check_safety):
        """
        Test d'un scénario complet où un token est snipé puis arbitré
        """
        # Mock des dépendances
        mock_sniper_init_blockchain.return_value = True
        mock_sniper_setup_wallet.return_value = True
        mock_arb_init_blockchain.return_value = True
        mock_arb_setup_wallet.return_value = True
        
        # Configurer le mock pour _check_token_safety
        mock_check_safety.return_value = {
            "is_safe": True,
            "liquidity_sufficient": True,
            "honeypot_check_passed": True,
            "safety_score": 85,
            "risks": []
        }
        
        # Configurer le mock pour sniper._execute_buy_transaction
        mock_sniper_execute_buy.return_value = {
            "success": True,
            "transaction_hash": "0xTestSniperBuyTransactionHash",
            "amount_in": 50,  # 50 USDC
            "amount_out": 1000,  # 1000 TEST tokens
            "token_price": 0.05,  # 1 TEST = 0.05 USDC
            "gas_used": 250000,
            "gas_price": 5
        }
        
        # Configurer le mock pour arbitrage._execute_buy_transaction
        mock_arb_execute_buy.return_value = {
            "success": True,
            "transaction_hash": "0xTestArbBuyTransactionHash",
            "amount_in": 100,  # 100 USDC
            "amount_out": 3.2,  # 3.2 AVAX
            "token_price": 31.25,  # 1 AVAX = 31.25 USDC
            "gas_used": 200000,
            "gas_price": 30000000000  # 30 Gwei
        }
        
        # Configurer le mock pour arbitrage._execute_sell_transaction
        mock_arb_execute_sell.return_value = {
            "success": True,
            "transaction_hash": "0xTestArbSellTransactionHash",
            "amount_in": 3.2,  # 3.2 AVAX
            "amount_out": 102,  # 102 USDC
            "token_price": 31.875,  # 1 AVAX = 31.875 USDC
            "gas_used": 180000,
            "gas_price": 32000000000  # 32 Gwei
        }
        
        # Instancier le client blockchain partagé
        blockchain_client = MagicMock()
        
        # Instancier le sniper
        sniper = self.sniper_class(
            blockchain="avalanche",
            config=self.test_config["sniping"],
            blockchain_client=blockchain_client,
            wallet_path=self.wallet_paths.get("avalanche", "")
        )
        
        # Instancier le moteur d'arbitrage
        arbitrage = self.arbitrage_class(
            blockchain="avalanche",
            config=self.test_config["arbitrage"],
            blockchain_client=blockchain_client,
            wallet_path=self.wallet_paths.get("avalanche", "")
        )
        
        # Étape 1: Sniper un nouveau token
        token_address = self.test_token["address"]
        amount_usd = 50
        snipe_result = sniper.snipe_token(token_address, amount_usd)
        
        # Vérifier le résultat du sniping
        self.assertTrue(snipe_result["success"], "Le sniping aurait dû réussir")
        
        # Étape 2: Définir une opportunité d'arbitrage
        opportunity = {
            "pair": self.test_pairs[0],  # USDC-AVAX
            "buy_dex": self.test_dexes[0],  # TraderJoe
            "sell_dex": self.test_dexes[1],  # Pangolin
            "buy_price": 31.25,  # 1 AVAX = 31.25 USDC sur TraderJoe
            "sell_price": 31.875,  # 1 AVAX = 31.875 USDC sur Pangolin
            "profit_percent": 2.0  # 2% de profit attendu
        }
        
        # Étape 3: Exécuter l'arbitrage
        arbitrage_result = arbitrage.execute_arbitrage(opportunity, amount=100)
        
        # Vérifier le résultat de l'arbitrage
        self.assertTrue(arbitrage_result["success"], "L'arbitrage aurait dû réussir")
        self.assertTrue(mock_arb_execute_buy.called, "La méthode d'exécution d'achat pour l'arbitrage n'a pas été appelée")
        self.assertTrue(mock_arb_execute_sell.called, "La méthode d'exécution de vente pour l'arbitrage n'a pas été appelée")
        
        # Vérifier les détails du résultat
        self.assertIn("buy_transaction", arbitrage_result, "Pas de transaction d'achat dans le résultat")
        self.assertIn("sell_transaction", arbitrage_result, "Pas de transaction de vente dans le résultat")
        self.assertIn("profit_usd", arbitrage_result, "Pas de profit USD dans le résultat")
        self.assertIn("profit_percent", arbitrage_result, "Pas de pourcentage de profit dans le résultat")
        
        # Vérifier le calcul du profit
        expected_profit = 102 - 100  # 102 USDC reçus - 100 USDC dépensés
        self.assertAlmostEqual(
            arbitrage_result["profit_usd"], 
            expected_profit, 
            places=1,  # Précision à 1 décimale près
            msg="Le profit USD n'est pas calculé correctement"
        )


if __name__ == "__main__":
    unittest.main() 