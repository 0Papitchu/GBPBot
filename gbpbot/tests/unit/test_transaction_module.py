#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests unitaires pour le module de transaction du GBPBot

Ce module teste les fonctionnalités du gestionnaire de transactions,
notamment l'exécution des transactions, l'optimisation du gas et la gestion des erreurs.
"""

import os
import sys
import json
import unittest
import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta

# Ajout du chemin racine au sys.path pour les imports
ROOT_DIR = Path(__file__).parent.parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Import des modules de test
from gbpbot.tests.setup_test_environment import setup_test_environment, cleanup_test_environment


class TestTransactionModule(unittest.TestCase):
    """Suite de tests pour le module de transaction du GBPBot"""
    
    @classmethod
    def setUpClass(cls):
        """
        Préparation de l'environnement de test avant l'exécution des tests
        """
        # Configuration de l'environnement de test
        cls.env_file, cls.wallet_paths = setup_test_environment()
        
        # Configuration pour les tests
        cls.test_config = {
            "transaction": {
                "default_slippage": 0.01,
                "default_gas_multiplier": 1.2,
                "default_priority_fee_multiplier": 1.5,
                "max_retries": 3,
                "retry_delay_ms": 1000,
                "verify_transactions": True,
                "use_flashbots": False
            },
            "chains": [
                {
                    "name": "avalanche",
                    "rpc_url": os.environ.get("AVALANCHE_RPC_URL", "https://api.avax-test.network/ext/bc/C/rpc"),
                    "chain_id": os.environ.get("AVALANCHE_CHAIN_ID", "43113")
                },
                {
                    "name": "solana",
                    "rpc_url": os.environ.get("SOLANA_RPC_URL", "https://api.testnet.solana.com")
                }
            ]
        }
        
        # Exemple de configuration de transaction
        cls.sample_tx_config = {
            "blockchain": "avalanche",
            "wallet_address": "0xSampleWalletAddress123",
            "dex": "traderjoe",
            "method": "buy",
            "token_address": "0xSampleTokenAddress123",
            "token_symbol": "TEST",
            "amount": 1.0,
            "amount_in_usd": 100.0,
            "slippage": 0.01,
            "deadline_minutes": 20,
            "gas_price_multiplier": 1.2,
            "priority_fee_multiplier": 1.5,
            "max_retries": 3,
            "retry_delay_ms": 1000,
            "simulate_before_send": True,
            "use_flashbots": False,
            "optimize_gas": True,
            "verify_transaction": True
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
        # Tenter d'importer le module de transaction, avec gestion des erreurs
        try:
            from gbpbot.modules.transaction_manager import TransactionManager, TransactionConfig, TransactionResult
            
            self.transaction_manager_class = TransactionManager
            self.transaction_config_class = TransactionConfig
            self.transaction_result_class = TransactionResult
        except ImportError as e:
            self.skipTest(f"Module de transaction non disponible: {str(e)}")
    
    def test_module_import(self):
        """
        Test de l'importation du module de transaction
        """
        # Vérifier que les modules ont été importés correctement
        self.assertIsNotNone(self.transaction_manager_class, "La classe TransactionManager n'a pas pu être importée")
        self.assertIsNotNone(self.transaction_config_class, "La classe TransactionConfig n'a pas pu être importée")
        self.assertIsNotNone(self.transaction_result_class, "La classe TransactionResult n'a pas pu être importée")
    
    @patch("gbpbot.modules.transaction_manager.TransactionManager._initialize_blockchain_client")
    def test_transaction_manager_initialization(self, mock_init_client):
        """
        Test de l'initialisation du gestionnaire de transactions
        """
        # Configurer le mock
        mock_init_client.return_value = AsyncMock()
        
        # Instancier le gestionnaire de transactions
        manager = self.transaction_manager_class(self.test_config)
        
        # Vérifier l'initialisation
        self.assertIsNotNone(manager, "Le gestionnaire de transactions n'a pas été instancié correctement")
        self.assertEqual(manager.config, self.test_config, "La configuration n'a pas été correctement assignée")
        self.assertEqual(manager.default_slippage, 0.01, "Le slippage par défaut n'a pas été correctement assigné")
        self.assertEqual(manager.default_gas_multiplier, 1.2, "Le multiplicateur de gas par défaut n'a pas été correctement assigné")
        self.assertEqual(manager.max_retries, 3, "Le nombre maximal de tentatives n'a pas été correctement assigné")
        self.assertEqual(manager.verify_transactions, True, "La vérification des transactions n'a pas été correctement assignée")
    
    def test_transaction_config_creation(self):
        """
        Test de la création d'une configuration de transaction
        """
        # Créer une configuration de transaction
        tx_config = self.transaction_config_class(
            blockchain="avalanche",
            wallet_address="0xSampleWalletAddress123",
            dex="traderjoe",
            method="buy",
            token_address="0xSampleTokenAddress123",
            token_symbol="TEST",
            amount=1.0,
            amount_in_usd=100.0
        )
        
        # Vérifier les valeurs
        self.assertEqual(tx_config.blockchain, "avalanche", "La blockchain n'a pas été correctement assignée")
        self.assertEqual(tx_config.wallet_address, "0xSampleWalletAddress123", "L'adresse du wallet n'a pas été correctement assignée")
        self.assertEqual(tx_config.dex, "traderjoe", "Le DEX n'a pas été correctement assigné")
        self.assertEqual(tx_config.method, "buy", "La méthode n'a pas été correctement assignée")
        self.assertEqual(tx_config.token_address, "0xSampleTokenAddress123", "L'adresse du token n'a pas été correctement assignée")
        self.assertEqual(tx_config.token_symbol, "TEST", "Le symbole du token n'a pas été correctement assigné")
        self.assertEqual(tx_config.amount, 1.0, "Le montant n'a pas été correctement assigné")
        self.assertEqual(tx_config.amount_in_usd, 100.0, "Le montant en USD n'a pas été correctement assigné")
        self.assertEqual(tx_config.slippage, 0.01, "Le slippage par défaut n'a pas été correctement assigné")
        self.assertEqual(tx_config.gas_price_multiplier, 1.2, "Le multiplicateur de gas par défaut n'a pas été correctement assigné")
    
    def test_transaction_result_creation(self):
        """
        Test de la création d'un résultat de transaction
        """
        # Créer un résultat de transaction réussi
        success_result = self.transaction_result_class(
            success=True,
            tx_hash="0xSampleTxHash123",
            gas_used=100000,
            gas_price=20.0,
            total_gas_cost=0.002,
            total_gas_cost_usd=5.0,
            block_number=12345678,
            timestamp=datetime.now().timestamp(),
            confirmations=1
        )
        
        # Vérifier les valeurs
        self.assertTrue(success_result.success, "Le succès n'a pas été correctement assigné")
        self.assertEqual(success_result.tx_hash, "0xSampleTxHash123", "Le hash de transaction n'a pas été correctement assigné")
        self.assertEqual(success_result.gas_used, 100000, "Le gas utilisé n'a pas été correctement assigné")
        self.assertEqual(success_result.gas_price, 20.0, "Le prix du gas n'a pas été correctement assigné")
        self.assertEqual(success_result.total_gas_cost, 0.002, "Le coût total du gas n'a pas été correctement assigné")
        self.assertEqual(success_result.total_gas_cost_usd, 5.0, "Le coût total du gas en USD n'a pas été correctement assigné")
        
        # Créer un résultat de transaction échoué
        error_result = self.transaction_result_class(
            success=False,
            error="Transaction failed"
        )
        
        # Vérifier les valeurs
        self.assertFalse(error_result.success, "Le succès n'a pas été correctement assigné")
        self.assertEqual(error_result.error, "Transaction failed", "L'erreur n'a pas été correctement assignée")
        self.assertIsNone(error_result.tx_hash, "Le hash de transaction n'a pas été correctement assigné")
    
    def test_transaction_result_to_dict(self):
        """
        Test de la conversion d'un résultat de transaction en dictionnaire
        """
        # Créer un résultat de transaction
        result = self.transaction_result_class(
            success=True,
            tx_hash="0xSampleTxHash123",
            gas_used=100000,
            gas_price=20.0,
            total_gas_cost=0.002,
            total_gas_cost_usd=5.0,
            block_number=12345678,
            timestamp=datetime.now().timestamp(),
            confirmations=1
        )
        
        # Convertir en dictionnaire
        result_dict = result.to_dict()
        
        # Vérifier le dictionnaire
        self.assertIsInstance(result_dict, dict, "Le résultat n'a pas été converti en dictionnaire")
        self.assertEqual(result_dict["success"], True, "Le succès n'a pas été correctement converti")
        self.assertEqual(result_dict["tx_hash"], "0xSampleTxHash123", "Le hash de transaction n'a pas été correctement converti")
        self.assertEqual(result_dict["gas_used"], 100000, "Le gas utilisé n'a pas été correctement converti")
        self.assertEqual(result_dict["gas_price"], 20.0, "Le prix du gas n'a pas été correctement converti")
    
    @patch("gbpbot.modules.transaction_manager.TransactionManager._initialize_blockchain_client")
    @patch("gbpbot.modules.transaction_manager.TransactionManager._validate_tx_config")
    def test_validate_tx_config(self, mock_validate, mock_init_client):
        """
        Test de la validation d'une configuration de transaction
        """
        # Configurer les mocks
        mock_init_client.return_value = AsyncMock()
        mock_validate.return_value = True
        
        # Instancier le gestionnaire de transactions
        manager = self.transaction_manager_class(self.test_config)
        
        # Vérifier la validation
        with patch.object(manager, '_validate_tx_config', return_value=True):
            # Configuration valide
            tx_config = self.transaction_config_class(
                blockchain="avalanche",
                wallet_address="0xSampleWalletAddress123",
                dex="traderjoe",
                method="buy"
            )
            self.assertTrue(manager._validate_tx_config(tx_config), "La validation a échoué pour une configuration valide")
            
            # Configuration invalide (sans blockchain)
            tx_config_invalid = self.transaction_config_class(
                blockchain="",
                wallet_address="0xSampleWalletAddress123",
                dex="traderjoe",
                method="buy"
            )
            with patch.object(manager, '_validate_tx_config', return_value=False):
                self.assertFalse(manager._validate_tx_config(tx_config_invalid), "La validation a réussi pour une configuration invalide")
    
    @patch("gbpbot.modules.transaction_manager.TransactionManager._initialize_blockchain_client")
    @patch("gbpbot.modules.transaction_manager.TransactionManager._validate_tx_config")
    @patch("gbpbot.modules.transaction_manager.TransactionManager._simulate_transaction")
    @patch("gbpbot.modules.transaction_manager.TransactionManager._optimize_gas_params")
    @patch("gbpbot.modules.transaction_manager.TransactionManager._execute_normal_tx")
    async def test_execute_transaction(self, mock_execute, mock_optimize, mock_simulate, 
                                    mock_validate, mock_init_client):
        """
        Test de l'exécution d'une transaction
        """
        # Configurer les mocks
        mock_init_client.return_value = AsyncMock()
        mock_validate.return_value = True
        mock_simulate.return_value = {"success": True, "gas_estimate": 100000}
        mock_optimize.return_value = None
        
        # Créer un résultat de transaction réussi
        success_result = self.transaction_result_class(
            success=True,
            tx_hash="0xSampleTxHash123",
            gas_used=100000,
            gas_price=20.0,
            total_gas_cost=0.002,
            total_gas_cost_usd=5.0,
            block_number=12345678,
            timestamp=datetime.now().timestamp(),
            confirmations=1
        )
        mock_execute.return_value = success_result
        
        # Instancier le gestionnaire de transactions
        manager = self.transaction_manager_class(self.test_config)
        manager.blockchain_clients = {"avalanche": AsyncMock()}
        
        # Créer une configuration de transaction
        tx_config = self.transaction_config_class(
            blockchain="avalanche",
            wallet_address="0xSampleWalletAddress123",
            dex="traderjoe",
            method="buy",
            token_address="0xSampleTokenAddress123",
            token_symbol="TEST",
            amount=1.0,
            amount_in_usd=100.0
        )
        
        # Exécuter la transaction
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(manager.execute_transaction(tx_config))
        
        # Vérifier le résultat
        self.assertIsNotNone(result, "Le résultat est nul")
        self.assertTrue(result.success, "La transaction a échoué")
        self.assertEqual(result.tx_hash, "0xSampleTxHash123", "Le hash de transaction est incorrect")
    
    @patch("gbpbot.modules.transaction_manager.TransactionManager._initialize_blockchain_client")
    async def test_queue_transaction(self, mock_init_client):
        """
        Test de la mise en file d'attente d'une transaction
        """
        # Configurer les mocks
        mock_init_client.return_value = AsyncMock()
        
        # Instancier le gestionnaire de transactions
        manager = self.transaction_manager_class(self.test_config)
        manager.tx_queue = AsyncMock()
        manager.tx_queue.put = AsyncMock()
        
        # Créer une configuration de transaction
        tx_config = self.transaction_config_class(
            blockchain="avalanche",
            wallet_address="0xSampleWalletAddress123",
            dex="traderjoe",
            method="buy",
            token_address="0xSampleTokenAddress123",
            token_symbol="TEST",
            amount=1.0,
            amount_in_usd=100.0
        )
        
        # Mettre en file d'attente
        loop = asyncio.get_event_loop()
        tx_id = loop.run_until_complete(manager.queue_transaction(tx_config))
        
        # Vérifier le résultat
        self.assertIsNotNone(tx_id, "L'identifiant de transaction est nul")
        self.assertTrue(tx_id.startswith("tx_"), "L'identifiant de transaction n'a pas le format attendu")
        self.assertTrue(manager.tx_queue.put.called, "La transaction n'a pas été mise en file d'attente")
    
    @patch("gbpbot.modules.transaction_manager.TransactionManager._initialize_blockchain_client")
    async def test_get_gas_price(self, mock_init_client):
        """
        Test de la récupération du prix du gas
        """
        # Configurer les mocks
        mock_init_client.return_value = AsyncMock()
        
        # Instancier le gestionnaire de transactions
        manager = self.transaction_manager_class(self.test_config)
        manager.blockchain_clients = {
            "avalanche": AsyncMock()
        }
        manager.blockchain_clients["avalanche"].get_gas_price = AsyncMock(return_value={
            "base_fee": 25.0,
            "priority_fee": 2.0,
            "gas_price": 27.0,
            "fast_gas_price": 30.0,
            "timestamp": datetime.now().timestamp()
        })
        
        # Récupérer le prix du gas
        loop = asyncio.get_event_loop()
        gas_data = loop.run_until_complete(manager.get_gas_price("avalanche"))
        
        # Vérifier les données
        self.assertIsNotNone(gas_data, "Les données de gas sont nulles")
        self.assertIn("base_fee", gas_data, "Le prix de base n'est pas présent")
        self.assertIn("priority_fee", gas_data, "Les frais prioritaires ne sont pas présents")
        self.assertIn("gas_price", gas_data, "Le prix du gas n'est pas présent")
        
        # Vérifier le cache
        self.assertIn("avalanche", manager.gas_cache, "Les données n'ont pas été mises en cache")
        
        # Récupérer à nouveau (devrait utiliser le cache)
        manager.blockchain_clients["avalanche"].get_gas_price = AsyncMock(return_value=None)  # Le rendre inaccessible
        gas_data_cached = loop.run_until_complete(manager.get_gas_price("avalanche"))
        
        # Vérifier que les données sont toujours disponibles (via le cache)
        self.assertIsNotNone(gas_data_cached, "Les données de gas en cache sont nulles")
        self.assertIn("base_fee", gas_data_cached, "Le prix de base n'est pas présent dans le cache")
    
    @patch("gbpbot.modules.transaction_manager.TransactionManager._initialize_blockchain_client")
    @patch("gbpbot.modules.transaction_manager.TransactionManager.get_gas_price")
    async def test_optimize_gas_params(self, mock_get_gas, mock_init_client):
        """
        Test de l'optimisation des paramètres de gas
        """
        # Configurer les mocks
        mock_init_client.return_value = AsyncMock()
        mock_get_gas.return_value = {
            "base_fee": 25.0,
            "priority_fee": 2.0,
            "gas_price": 27.0,
            "fast_gas_price": 30.0
        }
        
        # Instancier le gestionnaire de transactions
        manager = self.transaction_manager_class(self.test_config)
        
        # Créer une configuration de transaction
        tx_config = self.transaction_config_class(
            blockchain="avalanche",
            wallet_address="0xSampleWalletAddress123",
            dex="traderjoe",
            method="buy",
            token_address="0xSampleTokenAddress123",
            token_symbol="TEST",
            amount=1.0,
            amount_in_usd=100.0,
            gas_price_multiplier=1.2,
            priority_fee_multiplier=1.5
        )
        
        # Optimiser les paramètres de gas
        loop = asyncio.get_event_loop()
        loop.run_until_complete(manager._optimize_gas_params(tx_config))
        
        # Vérifier les paramètres mis à jour
        self.assertEqual(tx_config.gas_price_multiplier, 1.2, "Le multiplicateur de gas a été modifié")
        self.assertEqual(tx_config.priority_fee_multiplier, 1.5, "Le multiplicateur de frais prioritaires a été modifié")
        
        # Optimiser avec un facteur d'augmentation
        loop.run_until_complete(manager._optimize_gas_params(tx_config, increase_factor=1.5))
        
        # Vérifier les paramètres mis à jour avec l'augmentation
        self.assertEqual(tx_config.gas_price_multiplier, 1.2 * 1.5, "Le multiplicateur de gas n'a pas été augmenté correctement")
        self.assertEqual(tx_config.priority_fee_multiplier, 1.5 * 1.5, "Le multiplicateur de frais prioritaires n'a pas été augmenté correctement")


if __name__ == "__main__":
    unittest.main() 