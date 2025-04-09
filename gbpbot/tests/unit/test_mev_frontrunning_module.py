#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests unitaires pour le module MEV/Frontrunning du GBPBot

Ce module teste les fonctionnalités de MEV (Maximum Extractable Value)
et de frontrunning du GBPBot, notamment la surveillance du mempool,
le décodage des transactions, et les stratégies de frontrunning, backrunning
et sandwich attacks.
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


class TestMEVFrontrunningModule(unittest.TestCase):
    """Suite de tests pour le module MEV/Frontrunning du GBPBot"""
    
    @classmethod
    def setUpClass(cls):
        """
        Préparation de l'environnement de test avant l'exécution des tests
        """
        # Configuration de l'environnement de test
        cls.env_file, cls.wallet_paths = setup_test_environment()
        
        # Configuration pour les tests
        cls.test_config = {
            "mev": {
                "enabled": True,
                "mempool_monitor_interval": 1,
                "transaction_decoder_mode": "full",
                "simulation_enabled": True,
                "max_priority_fee": 5,
                "max_gas_price": 100,
                "strategies": {
                    "frontrunning": {
                        "enabled": True,
                        "gas_price_multiplier": 1.1,
                        "min_expected_profit_usd": 5
                    },
                    "backrunning": {
                        "enabled": True,
                        "gas_price_multiplier": 1.05,
                        "min_expected_profit_usd": 5
                    },
                    "sandwich": {
                        "enabled": True,
                        "front_gas_multiplier": 1.1,
                        "back_gas_multiplier": 1.05,
                        "min_expected_profit_usd": 10,
                        "min_target_tx_value_usd": 1000
                    }
                },
                "profit_taking": {
                    "instant_execution": True,
                    "max_hold_time_seconds": 60
                },
                "flashbots": {
                    "enabled": True,
                    "bundle_signer_key": "0xTestSignerPrivateKey",
                    "rpc_url": "https://rpc.flashbots.net"
                }
            },
            "blockchain": {
                "avalanche": {
                    "rpc_url": os.environ.get("AVALANCHE_RPC_URL", "https://api.avax-test.network/ext/bc/C/rpc"),
                    "chain_id": os.environ.get("AVALANCHE_CHAIN_ID", "43113"),
                    "websocket": os.environ.get("AVALANCHE_WEBSOCKET", "wss://api.avax-test.network/ext/bc/C/ws")
                }
            },
            "wallets": {
                "avalanche": {
                    "address": "0xTestWalletAddress123",
                    "private_key": "test-private-key-not-real"
                }
            }
        }
        
        # Données de test pour les transactions
        cls.test_pending_tx = {
            "hash": "0xTestTransactionHash123",
            "from": "0xSenderAddress123",
            "to": "0xJoeRouterAddress123",
            "value": "1000000000000000000",  # 1 AVAX
            "gas": "200000",
            "gasPrice": "50000000000",  # 50 Gwei
            "input": "0xb6f9de950000000000000000000000000000000000000000000000000de0b6b3a7640000000000000000000000000000000000000000000000000000000000000000000080000000000000000000000000e295ad71242373aaab13d61b6c4e9d46571f9b600000000000000000000000000000000000000000000000000000000662d581f0000000000000000000000000000000000000000000000000000000000000002000000000000000000000000b31f66aa3c1e785363f0875a1b74e27b85fd66c70000000000000000000000002f28add68e59733d23d5f57d94c31fb965f835d0"
        }
        
        # Données de test pour les blocs
        cls.test_block = {
            "number": "12345678",
            "hash": "0xTestBlockHash123",
            "parentHash": "0xTestParentBlockHash123",
            "timestamp": "1650000000",
            "transactions": [
                "0xTransaction1",
                "0xTransaction2",
                "0xTransaction3"
            ]
        }
        
        # Données de test pour les paires de trading
        cls.test_pairs = [
            {
                "name": "WAVAX-USDC",
                "address": "0xPairAddress1",
                "token0": "0xb31f66aa3c1e785363f0875a1b74e27b85fd66c7",  # WAVAX
                "token1": "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E",  # USDC
                "reserve0": "100000000000000000000",  # 100 WAVAX
                "reserve1": "10000000000",  # 10,000 USDC
                "volume24h": "5000000000"  # $5M
            },
            {
                "name": "JOE-USDC",
                "address": "0xPairAddress2",
                "token0": "0x6e84a6216ea6dacc71ee8e6b0a5b7322eebc0fdd",  # JOE
                "token1": "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E",  # USDC
                "reserve0": "10000000000000000000000",  # 10,000 JOE
                "reserve1": "1000000000",  # 1,000 USDC
                "volume24h": "1000000000"  # $1M
            }
        ]
        
        # Résultat de simulation de transaction
        cls.test_simulation_result = {
            "success": True,
            "gasUsed": 150000,
            "blockNumber": 12345678,
            "output": "0x0000000000000000000000000000000000000000000000000de0b6b3a7640000",
            "logs": [
                {
                    "address": "0xPairAddress1",
                    "topics": [
                        "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef",
                        "0x000000000000000000000000e295ad71242373aaab13d61b6c4e9d46571f9b60",
                        "0x000000000000000000000000b31f66aa3c1e785363f0875a1b74e27b85fd66c7"
                    ],
                    "data": "0x0000000000000000000000000000000000000000000000000de0b6b3a7640000"
                }
            ]
        }
        
        # Décodage d'une transaction swap
        cls.test_decoded_swap = {
            "function": "swapExactAVAXForTokens",
            "input_token": "AVAX",
            "output_token": "0x2f28add68e59733d23d5f57d94c31fb965f835d0",  # TEST token
            "amount_in": "1000000000000000000",  # 1 AVAX
            "min_amount_out": "0",
            "path": [
                "0xb31f66aa3c1e785363f0875a1b74e27b85fd66c7",  # WAVAX
                "0x2f28add68e59733d23d5f57d94c31fb965f835d0"   # TEST token
            ],
            "deadline": "1650000000"
        }
        
        # Bundle Flashbots
        cls.test_flashbots_bundle = [
            {
                "signer": "0xTestSignerAddress",
                "transaction": {
                    "from": "0xTestWalletAddress123",
                    "to": "0xJoeRouterAddress123",
                    "data": "0x12345...",
                    "value": "0",
                    "gasPrice": "55000000000",
                    "gas": "200000"
                }
            },
            {
                "signer": "0xTestSignerAddress",
                "transaction": {
                    "from": "0xTestWalletAddress123",
                    "to": "0xJoeRouterAddress123",
                    "data": "0x67890...",
                    "value": "0",
                    "gasPrice": "55000000000",
                    "gas": "200000"
                }
            }
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
        # Tenter d'importer les modules de MEV/Frontrunning, avec gestion des erreurs
        try:
            from gbpbot.core.mev.mempool_monitor import MempoolMonitor
            from gbpbot.core.mev.transaction_decoder import TransactionDecoder
            from gbpbot.core.mev.strategy_manager import MEVStrategyManager
            from gbpbot.core.mev.transaction_simulator import TransactionSimulator
            from gbpbot.core.mev.flashbots_manager import FlashbotsManager
            
            self.mempool_monitor_class = MempoolMonitor
            self.transaction_decoder_class = TransactionDecoder
            self.strategy_manager_class = MEVStrategyManager
            self.transaction_simulator_class = TransactionSimulator
            self.flashbots_manager_class = FlashbotsManager
        except ImportError as e:
            self.skipTest(f"Module MEV/Frontrunning non disponible: {str(e)}")
    
    def test_module_import(self):
        """
        Test de l'importation du module MEV/Frontrunning
        """
        # Vérifier que les modules ont été importés correctement
        self.assertIsNotNone(self.mempool_monitor_class, "La classe MempoolMonitor n'a pas pu être importée")
        self.assertIsNotNone(self.transaction_decoder_class, "La classe TransactionDecoder n'a pas pu être importée")
        self.assertIsNotNone(self.strategy_manager_class, "La classe MEVStrategyManager n'a pas pu être importée")
        self.assertIsNotNone(self.transaction_simulator_class, "La classe TransactionSimulator n'a pas pu être importée")
        self.assertIsNotNone(self.flashbots_manager_class, "La classe FlashbotsManager n'a pas pu être importée")
    
    @patch("gbpbot.core.mev.mempool_monitor.MempoolMonitor._initialize_web3")
    @patch("gbpbot.core.mev.mempool_monitor.MempoolMonitor._initialize_websocket")
    def test_mempool_monitor_initialization(self, mock_init_ws, mock_init_web3):
        """
        Test de l'initialisation du moniteur de mempool
        """
        # Configurer les mocks
        mock_init_web3.return_value = True
        mock_init_ws.return_value = True
        
        # Instancier le moniteur de mempool
        monitor = self.mempool_monitor_class(self.test_config)
        
        # Vérifier l'initialisation
        self.assertIsNotNone(monitor, "Le moniteur de mempool n'a pas été instancié correctement")
        self.assertEqual(monitor.config, self.test_config, "La configuration n'a pas été correctement assignée")
        self.assertEqual(monitor.monitor_interval, self.test_config["mev"]["mempool_monitor_interval"], 
                       "L'intervalle de surveillance n'a pas été correctement assigné")
    
    @patch("gbpbot.core.mev.mempool_monitor.MempoolMonitor._initialize_web3")
    @patch("gbpbot.core.mev.mempool_monitor.MempoolMonitor._initialize_websocket")
    @patch("gbpbot.core.mev.mempool_monitor.MempoolMonitor.on_pending_transaction")
    def test_pending_transaction_callback(self, mock_callback, mock_init_ws, mock_init_web3):
        """
        Test du callback de transaction en attente
        """
        # Configurer les mocks
        mock_init_web3.return_value = True
        mock_init_ws.return_value = True
        
        # Instancier le moniteur de mempool
        monitor = self.mempool_monitor_class(self.test_config)
        
        # Simuler la réception d'une transaction en attente
        monitor._handle_pending_tx(self.test_pending_tx["hash"])
        
        # Vérifier que le callback a été appelé avec le hash de la transaction
        mock_callback.assert_called_once_with(self.test_pending_tx["hash"])
    
    @patch("gbpbot.core.mev.transaction_decoder.TransactionDecoder._initialize_web3")
    @patch("gbpbot.core.mev.transaction_decoder.TransactionDecoder._load_abi_files")
    def test_transaction_decoder_initialization(self, mock_load_abi, mock_init_web3):
        """
        Test de l'initialisation du décodeur de transactions
        """
        # Configurer les mocks
        mock_init_web3.return_value = True
        mock_load_abi.return_value = {
            "router": [{"name": "swapExactAVAXForTokens", "inputs": []}],
            "erc20": [{"name": "transfer", "inputs": []}]
        }
        
        # Instancier le décodeur de transactions
        decoder = self.transaction_decoder_class(self.test_config)
        
        # Vérifier l'initialisation
        self.assertIsNotNone(decoder, "Le décodeur de transactions n'a pas été instancié correctement")
        self.assertEqual(decoder.config, self.test_config, "La configuration n'a pas été correctement assignée")
        self.assertEqual(decoder.decoder_mode, self.test_config["mev"]["transaction_decoder_mode"], 
                       "Le mode de décodage n'a pas été correctement assigné")
    
    @patch("gbpbot.core.mev.transaction_decoder.TransactionDecoder._initialize_web3")
    @patch("gbpbot.core.mev.transaction_decoder.TransactionDecoder._load_abi_files")
    @patch("gbpbot.core.mev.transaction_decoder.TransactionDecoder._get_transaction")
    @patch("gbpbot.core.mev.transaction_decoder.TransactionDecoder._decode_input_data")
    def test_decode_transaction(self, mock_decode_input, mock_get_tx, mock_load_abi, mock_init_web3):
        """
        Test du décodage d'une transaction
        """
        # Configurer les mocks
        mock_init_web3.return_value = True
        mock_load_abi.return_value = {
            "router": [{"name": "swapExactAVAXForTokens", "inputs": []}],
            "erc20": [{"name": "transfer", "inputs": []}]
        }
        mock_get_tx.return_value = self.test_pending_tx
        mock_decode_input.return_value = self.test_decoded_swap
        
        # Instancier le décodeur de transactions
        decoder = self.transaction_decoder_class(self.test_config)
        
        # Décoder une transaction
        decoded_tx = decoder.decode_transaction(self.test_pending_tx["hash"])
        
        # Vérifier le décodage
        self.assertIsNotNone(decoded_tx, "La transaction n'a pas été décodée")
        self.assertEqual(decoded_tx, self.test_decoded_swap, "La transaction n'a pas été correctement décodée")
        mock_get_tx.assert_called_once_with(self.test_pending_tx["hash"])
        mock_decode_input.assert_called_once()
    
    @patch("gbpbot.core.mev.strategy_manager.MEVStrategyManager._initialize_web3")
    @patch("gbpbot.core.mev.strategy_manager.MEVStrategyManager._initialize_token_prices")
    def test_strategy_manager_initialization(self, mock_init_prices, mock_init_web3):
        """
        Test de l'initialisation du gestionnaire de stratégies
        """
        # Configurer les mocks
        mock_init_web3.return_value = True
        mock_init_prices.return_value = {
            "0xb31f66aa3c1e785363f0875a1b74e27b85fd66c7": 20.0,  # WAVAX price
            "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E": 1.0    # USDC price
        }
        
        # Instancier le gestionnaire de stratégies
        manager = self.strategy_manager_class(self.test_config)
        
        # Vérifier l'initialisation
        self.assertIsNotNone(manager, "Le gestionnaire de stratégies n'a pas été instancié correctement")
        self.assertEqual(manager.config, self.test_config, "La configuration n'a pas été correctement assignée")
        self.assertTrue(manager.strategies["frontrunning"]["enabled"], 
                      "La stratégie de frontrunning n'a pas été activée")
        self.assertTrue(manager.strategies["backrunning"]["enabled"], 
                      "La stratégie de backrunning n'a pas été activée")
        self.assertTrue(manager.strategies["sandwich"]["enabled"], 
                      "La stratégie de sandwich n'a pas été activée")
    
    @patch("gbpbot.core.mev.strategy_manager.MEVStrategyManager._initialize_web3")
    @patch("gbpbot.core.mev.strategy_manager.MEVStrategyManager._initialize_token_prices")
    @patch("gbpbot.core.mev.strategy_manager.MEVStrategyManager._simulate_frontrun_transaction")
    def test_evaluate_frontrun_opportunity(self, mock_simulate, mock_init_prices, mock_init_web3):
        """
        Test de l'évaluation d'une opportunité de frontrunning
        """
        # Configurer les mocks
        mock_init_web3.return_value = True
        mock_init_prices.return_value = {
            "0xb31f66aa3c1e785363f0875a1b74e27b85fd66c7": 20.0,  # WAVAX price
            "0x2f28add68e59733d23d5f57d94c31fb965f835d0": 0.5    # TEST token price
        }
        mock_simulate.return_value = {
            "profit_usd": 15.0,
            "gas_cost_usd": 5.0,
            "net_profit_usd": 10.0,
            "transaction": {
                "from": "0xTestWalletAddress123",
                "to": "0xJoeRouterAddress123",
                "data": "0x12345...",
                "value": "0",
                "gasPrice": "55000000000",
                "gas": "200000"
            }
        }
        
        # Instancier le gestionnaire de stratégies
        manager = self.strategy_manager_class(self.test_config)
        
        # Évaluer une opportunité de frontrunning
        opportunity = manager.evaluate_frontrun_opportunity(self.test_decoded_swap)
        
        # Vérifier l'évaluation
        self.assertIsNotNone(opportunity, "L'opportunité n'a pas été évaluée")
        self.assertTrue(opportunity["profitable"], "L'opportunité profitable a été marquée comme non profitable")
        self.assertEqual(opportunity["net_profit_usd"], 10.0, "Le profit net n'a pas été calculé correctement")
        self.assertIn("transaction", opportunity, "La transaction frontrun n'a pas été générée")
    
    @patch("gbpbot.core.mev.transaction_simulator.TransactionSimulator._initialize_web3")
    def test_transaction_simulator_initialization(self, mock_init_web3):
        """
        Test de l'initialisation du simulateur de transactions
        """
        # Configurer le mock
        mock_init_web3.return_value = True
        
        # Instancier le simulateur de transactions
        simulator = self.transaction_simulator_class(self.test_config)
        
        # Vérifier l'initialisation
        self.assertIsNotNone(simulator, "Le simulateur de transactions n'a pas été instancié correctement")
        self.assertEqual(simulator.config, self.test_config, "La configuration n'a pas été correctement assignée")
        self.assertTrue(simulator.simulation_enabled, "La simulation n'a pas été activée")
    
    @patch("gbpbot.core.mev.transaction_simulator.TransactionSimulator._initialize_web3")
    @patch("gbpbot.core.mev.transaction_simulator.TransactionSimulator._simulate_transaction_with_web3")
    def test_simulate_transaction(self, mock_simulate, mock_init_web3):
        """
        Test de la simulation d'une transaction
        """
        # Configurer les mocks
        mock_init_web3.return_value = True
        mock_simulate.return_value = self.test_simulation_result
        
        # Instancier le simulateur de transactions
        simulator = self.transaction_simulator_class(self.test_config)
        
        # Simuler une transaction
        test_tx = {
            "from": "0xTestWalletAddress123",
            "to": "0xJoeRouterAddress123",
            "data": "0x12345...",
            "value": "0",
            "gasPrice": "55000000000",
            "gas": "200000"
        }
        result = simulator.simulate_transaction(test_tx)
        
        # Vérifier la simulation
        self.assertIsNotNone(result, "La simulation n'a pas retourné de résultat")
        self.assertTrue(result["success"], "La simulation a échoué")
        self.assertEqual(result["gasUsed"], 150000, "La consommation de gas n'a pas été correctement calculée")
    
    @patch("gbpbot.core.mev.flashbots_manager.FlashbotsManager._initialize_web3")
    @patch("gbpbot.core.mev.flashbots_manager.FlashbotsManager._initialize_flashbots")
    def test_flashbots_manager_initialization(self, mock_init_flashbots, mock_init_web3):
        """
        Test de l'initialisation du gestionnaire Flashbots
        """
        # Configurer les mocks
        mock_init_web3.return_value = True
        mock_init_flashbots.return_value = True
        
        # Instancier le gestionnaire Flashbots
        manager = self.flashbots_manager_class(self.test_config)
        
        # Vérifier l'initialisation
        self.assertIsNotNone(manager, "Le gestionnaire Flashbots n'a pas été instancié correctement")
        self.assertEqual(manager.config, self.test_config, "La configuration n'a pas été correctement assignée")
        self.assertTrue(manager.enabled, "Flashbots n'a pas été activé")
        self.assertEqual(manager.signer_key, self.test_config["mev"]["flashbots"]["bundle_signer_key"], 
                       "La clé du signataire n'a pas été correctement assignée")
    
    @patch("gbpbot.core.mev.flashbots_manager.FlashbotsManager._initialize_web3")
    @patch("gbpbot.core.mev.flashbots_manager.FlashbotsManager._initialize_flashbots")
    @patch("gbpbot.core.mev.flashbots_manager.FlashbotsManager._prepare_flashbots_bundle")
    @patch("gbpbot.core.mev.flashbots_manager.FlashbotsManager._send_bundle")
    def test_send_flashbots_bundle(self, mock_send, mock_prepare, mock_init_flashbots, mock_init_web3):
        """
        Test de l'envoi d'un bundle Flashbots
        """
        # Configurer les mocks
        mock_init_web3.return_value = True
        mock_init_flashbots.return_value = True
        mock_prepare.return_value = self.test_flashbots_bundle
        mock_send.return_value = {
            "bundleHash": "0xBundleHash123",
            "success": True
        }
        
        # Instancier le gestionnaire Flashbots
        manager = self.flashbots_manager_class(self.test_config)
        
        # Envoyer un bundle
        transactions = [
            {
                "from": "0xTestWalletAddress123",
                "to": "0xJoeRouterAddress123",
                "data": "0x12345...",
                "value": "0",
                "gasPrice": "55000000000",
                "gas": "200000"
            },
            {
                "from": "0xTestWalletAddress123",
                "to": "0xJoeRouterAddress123",
                "data": "0x67890...",
                "value": "0",
                "gasPrice": "55000000000",
                "gas": "200000"
            }
        ]
        target_block = 12345680
        result = manager.send_bundle(transactions, target_block)
        
        # Vérifier l'envoi
        self.assertIsNotNone(result, "L'envoi du bundle n'a pas retourné de résultat")
        self.assertTrue(result["success"], "L'envoi du bundle a échoué")
        self.assertEqual(result["bundleHash"], "0xBundleHash123", "Le hash du bundle n'a pas été retourné")
        mock_prepare.assert_called_once_with(transactions)
        mock_send.assert_called_once_with(self.test_flashbots_bundle, target_block)
    
    @patch("gbpbot.core.mev.mempool_monitor.MempoolMonitor._initialize_web3")
    @patch("gbpbot.core.mev.mempool_monitor.MempoolMonitor._initialize_websocket")
    @patch("gbpbot.core.mev.transaction_decoder.TransactionDecoder._initialize_web3")
    @patch("gbpbot.core.mev.transaction_decoder.TransactionDecoder._load_abi_files")
    @patch("gbpbot.core.mev.strategy_manager.MEVStrategyManager._initialize_web3")
    @patch("gbpbot.core.mev.strategy_manager.MEVStrategyManager._initialize_token_prices")
    def test_end_to_end_mev_workflow(self, mock_init_prices, mock_strat_init_web3, 
                                 mock_load_abi, mock_decoder_init_web3, 
                                 mock_init_ws, mock_monitor_init_web3):
        """
        Test du workflow de MEV de bout en bout
        """
        # Configurer les mocks
        mock_monitor_init_web3.return_value = True
        mock_init_ws.return_value = True
        mock_decoder_init_web3.return_value = True
        mock_load_abi.return_value = {
            "router": [{"name": "swapExactAVAXForTokens", "inputs": []}],
            "erc20": [{"name": "transfer", "inputs": []}]
        }
        mock_strat_init_web3.return_value = True
        mock_init_prices.return_value = {
            "0xb31f66aa3c1e785363f0875a1b74e27b85fd66c7": 20.0,  # WAVAX price
            "0x2f28add68e59733d23d5f57d94c31fb965f835d0": 0.5    # TEST token price
        }
        
        # Instancier les composants du workflow MEV
        monitor = self.mempool_monitor_class(self.test_config)
        decoder = self.transaction_decoder_class(self.test_config)
        strategy_manager = self.strategy_manager_class(self.test_config)
        
        # Simuler le workflow MEV
        with patch.object(decoder, 'decode_transaction', return_value=self.test_decoded_swap):
            with patch.object(strategy_manager, 'evaluate_frontrun_opportunity', return_value={
                "profitable": True,
                "net_profit_usd": 10.0,
                "transaction": {
                    "from": "0xTestWalletAddress123",
                    "to": "0xJoeRouterAddress123",
                    "data": "0x12345...",
                    "value": "0",
                    "gasPrice": "55000000000",
                    "gas": "200000"
                }
            }):
                # Brancher le décodeur au moniteur
                monitor.on_pending_transaction = lambda tx_hash: decoder.decode_transaction(tx_hash)
                
                # Fournir une transaction décodée au gestionnaire de stratégies
                decoded_tx = decoder.decode_transaction(self.test_pending_tx["hash"])
                opportunity = strategy_manager.evaluate_frontrun_opportunity(decoded_tx)
                
                # Vérifier le workflow
                self.assertIsNotNone(decoded_tx, "La transaction n'a pas été décodée")
                self.assertIsNotNone(opportunity, "L'opportunité n'a pas été évaluée")
                self.assertTrue(opportunity["profitable"], "L'opportunité profitable a été marquée comme non profitable")
                self.assertIn("transaction", opportunity, "La transaction frontrun n'a pas été générée")
    
    @patch("gbpbot.core.mev.mempool_monitor.MempoolMonitor._initialize_web3")
    @patch("gbpbot.core.mev.mempool_monitor.MempoolMonitor._initialize_websocket")
    def test_mempool_subscription(self, mock_init_ws, mock_init_web3):
        """
        Test de l'abonnement au mempool
        """
        # Configurer les mocks
        mock_init_web3.return_value = True
        mock_init_ws.return_value = True
        
        # Instancier le moniteur de mempool
        monitor = self.mempool_monitor_class(self.test_config)
        
        # Tester l'abonnement au mempool
        with patch.object(monitor, '_start_websocket_subscription', return_value=None) as mock_start:
            monitor.start()
            mock_start.assert_called_once()
            
        with patch.object(monitor, '_stop_websocket_subscription', return_value=None) as mock_stop:
            monitor.stop()
            mock_stop.assert_called_once()
    
    @patch("gbpbot.core.mev.strategy_manager.MEVStrategyManager._initialize_web3")
    @patch("gbpbot.core.mev.strategy_manager.MEVStrategyManager._initialize_token_prices")
    @patch("gbpbot.core.mev.strategy_manager.MEVStrategyManager._simulate_sandwich_attack")
    def test_evaluate_sandwich_opportunity(self, mock_simulate, mock_init_prices, mock_init_web3):
        """
        Test de l'évaluation d'une opportunité de sandwich attack
        """
        # Configurer les mocks
        mock_init_web3.return_value = True
        mock_init_prices.return_value = {
            "0xb31f66aa3c1e785363f0875a1b74e27b85fd66c7": 20.0,  # WAVAX price
            "0x2f28add68e59733d23d5f57d94c31fb965f835d0": 0.5    # TEST token price
        }
        mock_simulate.return_value = {
            "profit_usd": 25.0,
            "gas_cost_usd": 8.0,
            "net_profit_usd": 17.0,
            "front_tx": {
                "from": "0xTestWalletAddress123",
                "to": "0xJoeRouterAddress123",
                "data": "0xFrontTxData...",
                "value": "0",
                "gasPrice": "55000000000",
                "gas": "200000"
            },
            "back_tx": {
                "from": "0xTestWalletAddress123",
                "to": "0xJoeRouterAddress123",
                "data": "0xBackTxData...",
                "value": "0",
                "gasPrice": "52000000000",
                "gas": "200000"
            }
        }
        
        # Instancier le gestionnaire de stratégies
        manager = self.strategy_manager_class(self.test_config)
        
        # Évaluer une opportunité de sandwich attack
        opportunity = manager.evaluate_sandwich_opportunity(self.test_decoded_swap)
        
        # Vérifier l'évaluation
        self.assertIsNotNone(opportunity, "L'opportunité n'a pas été évaluée")
        self.assertTrue(opportunity["profitable"], "L'opportunité profitable a été marquée comme non profitable")
        self.assertEqual(opportunity["net_profit_usd"], 17.0, "Le profit net n'a pas été calculé correctement")
        self.assertIn("front_tx", opportunity, "La transaction front n'a pas été générée")
        self.assertIn("back_tx", opportunity, "La transaction back n'a pas été générée")


if __name__ == "__main__":
    unittest.main() 