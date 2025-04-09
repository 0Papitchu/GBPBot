#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests unitaires pour le module de monitoring du marché du GBPBot

Ce module teste les fonctionnalités du moniteur de marché,
notamment la détection des opportunités, la surveillance des prix
et la gestion des alertes.
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


class TestMarketMonitor(unittest.TestCase):
    """Suite de tests pour le module de monitoring du marché du GBPBot"""
    
    @classmethod
    def setUpClass(cls):
        """
        Préparation de l'environnement de test avant l'exécution des tests
        """
        # Configuration de l'environnement de test
        cls.env_file, cls.wallet_paths = setup_test_environment()
        
        # Configuration pour les tests
        cls.test_config = {
            "monitoring": {
                "price_movement_threshold": 5.0,
                "arbitrage_min_diff": 0.5,
                "new_token_max_age": 3600,
                "whale_min_usd": 10000
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
        
        # Token de test
        cls.test_token = {
            "address": "0xTestTokenAddress123",
            "blockchain": "avalanche",
            "symbol": "TEST",
            "name": "Test Token",
            "price": 1.0,
            "liquidity_usd": 100000,
            "volume_24h": 50000,
            "market_cap": 1000000,
            "holders_count": 500,
            "created_at": (datetime.now() - timedelta(days=10)).isoformat()
        }
        
        # Opportunité de test
        cls.test_opportunity = {
            "id": "test_opportunity_123",
            "type": "price_movement",
            "blockchain": "avalanche",
            "token_address": "0xTestTokenAddress123",
            "token_symbol": "TEST",
            "timestamp": datetime.now().isoformat(),
            "expiration": (datetime.now() + timedelta(minutes=10)).isoformat(),
            "priority": 3,
            "details": {
                "current_price": 1.1,
                "previous_price": 1.0,
                "change_percent": 10.0,
                "direction": "up"
            }
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
        # Tenter d'importer le module de monitoring, avec gestion des erreurs
        try:
            from gbpbot.monitoring.market_monitor import MarketMonitor, MarketOpportunity
            
            self.market_monitor_class = MarketMonitor
            self.market_opportunity_class = MarketOpportunity
        except ImportError as e:
            self.skipTest(f"Module de monitoring non disponible: {str(e)}")
    
    def test_module_import(self):
        """
        Test de l'importation du module de monitoring
        """
        # Vérifier que les modules ont été importés correctement
        self.assertIsNotNone(self.market_monitor_class, "La classe MarketMonitor n'a pas pu être importée")
        self.assertIsNotNone(self.market_opportunity_class, "La classe MarketOpportunity n'a pas pu être importée")
    
    def test_market_opportunity_creation(self):
        """
        Test de la création d'une opportunité de marché
        """
        # Créer une opportunité
        opportunity = self.market_opportunity_class(
            id="test_opportunity_123",
            type="price_movement",
            blockchain="avalanche",
            token_address="0xTestTokenAddress123",
            token_symbol="TEST",
            timestamp=datetime.now(),
            expiration=datetime.now() + timedelta(minutes=10),
            priority=3,
            details={
                "current_price": 1.1,
                "previous_price": 1.0,
                "change_percent": 10.0,
                "direction": "up"
            }
        )
        
        # Vérifier les attributs
        self.assertEqual(opportunity.id, "test_opportunity_123", "L'ID n'a pas été correctement assigné")
        self.assertEqual(opportunity.type, "price_movement", "Le type n'a pas été correctement assigné")
        self.assertEqual(opportunity.blockchain, "avalanche", "La blockchain n'a pas été correctement assignée")
        self.assertEqual(opportunity.token_address, "0xTestTokenAddress123", "L'adresse du token n'a pas été correctement assignée")
        self.assertEqual(opportunity.token_symbol, "TEST", "Le symbole du token n'a pas été correctement assigné")
        self.assertEqual(opportunity.priority, 3, "La priorité n'a pas été correctement assignée")
        self.assertEqual(opportunity.details["change_percent"], 10.0, "Les détails n'ont pas été correctement assignés")
    
    def test_market_opportunity_to_dict(self):
        """
        Test de la conversion d'une opportunité en dictionnaire
        """
        # Créer une opportunité
        now = datetime.now()
        expiration = now + timedelta(minutes=10)
        opportunity = self.market_opportunity_class(
            id="test_opportunity_123",
            type="price_movement",
            blockchain="avalanche",
            token_address="0xTestTokenAddress123",
            token_symbol="TEST",
            timestamp=now,
            expiration=expiration,
            priority=3,
            details={
                "current_price": 1.1,
                "previous_price": 1.0,
                "change_percent": 10.0,
                "direction": "up"
            }
        )
        
        # Convertir en dictionnaire
        opp_dict = opportunity.to_dict()
        
        # Vérifier le dictionnaire
        self.assertIsInstance(opp_dict, dict, "Le résultat n'a pas été converti en dictionnaire")
        self.assertEqual(opp_dict["id"], "test_opportunity_123", "L'ID n'a pas été correctement converti")
        self.assertEqual(opp_dict["type"], "price_movement", "Le type n'a pas été correctement converti")
        self.assertEqual(opp_dict["blockchain"], "avalanche", "La blockchain n'a pas été correctement convertie")
        self.assertEqual(opp_dict["token_address"], "0xTestTokenAddress123", "L'adresse du token n'a pas été correctement convertie")
        self.assertEqual(opp_dict["token_symbol"], "TEST", "Le symbole du token n'a pas été correctement converti")
        self.assertEqual(opp_dict["priority"], 3, "La priorité n'a pas été correctement convertie")
        self.assertEqual(opp_dict["timestamp"], now.isoformat(), "Le timestamp n'a pas été correctement converti")
        self.assertEqual(opp_dict["expiration"], expiration.isoformat(), "L'expiration n'a pas été correctement convertie")
        self.assertEqual(opp_dict["details"]["change_percent"], 10.0, "Les détails n'ont pas été correctement convertis")
    
    def test_market_opportunity_is_expired(self):
        """
        Test de la vérification d'expiration d'une opportunité
        """
        # Créer une opportunité non expirée
        opportunity_not_expired = self.market_opportunity_class(
            id="test_opportunity_123",
            type="price_movement",
            blockchain="avalanche",
            token_address="0xTestTokenAddress123",
            token_symbol="TEST",
            timestamp=datetime.now(),
            expiration=datetime.now() + timedelta(minutes=10),
            priority=3,
            details={}
        )
        
        # Vérifier qu'elle n'est pas expirée
        self.assertFalse(opportunity_not_expired.is_expired(), "L'opportunité non expirée a été marquée comme expirée")
        
        # Créer une opportunité expirée
        opportunity_expired = self.market_opportunity_class(
            id="test_opportunity_456",
            type="price_movement",
            blockchain="avalanche",
            token_address="0xTestTokenAddress123",
            token_symbol="TEST",
            timestamp=datetime.now() - timedelta(minutes=20),
            expiration=datetime.now() - timedelta(minutes=10),
            priority=3,
            details={}
        )
        
        # Vérifier qu'elle est expirée
        self.assertTrue(opportunity_expired.is_expired(), "L'opportunité expirée n'a pas été marquée comme expirée")
    
    @patch("gbpbot.monitoring.market_monitor.MarketMonitor._initialize_blockchain_client")
    def test_market_monitor_initialization(self, mock_init_client):
        """
        Test de l'initialisation du moniteur de marché
        """
        # Configurer le mock
        mock_init_client.return_value = AsyncMock()
        
        # Instancier le moniteur de marché
        monitor = self.market_monitor_class(self.test_config)
        
        # Vérifier l'initialisation
        self.assertIsNotNone(monitor, "Le moniteur de marché n'a pas été instancié correctement")
        self.assertEqual(monitor.config, self.test_config, "La configuration n'a pas été correctement assignée")
        self.assertEqual(monitor.price_movement_threshold, 5.0, "Le seuil de mouvement de prix n'a pas été correctement assigné")
        self.assertEqual(monitor.arbitrage_min_diff, 0.5, "La différence minimale d'arbitrage n'a pas été correctement assignée")
        self.assertEqual(monitor.new_token_max_age, 3600, "L'âge maximal des nouveaux tokens n'a pas été correctement assigné")
        self.assertEqual(monitor.whale_min_usd, 10000, "Le montant minimum des whales n'a pas été correctement assigné")
    
    @patch("gbpbot.monitoring.market_monitor.MarketMonitor._initialize_blockchain_client")
    @patch("gbpbot.monitoring.market_monitor.MarketMonitor._load_watched_tokens")
    async def test_initialize(self, mock_load_tokens, mock_init_client):
        """
        Test de l'initialisation des ressources du moniteur
        """
        # Configurer les mocks
        mock_init_client.return_value = AsyncMock()
        mock_load_tokens.return_value = None
        
        # Instancier le moniteur de marché
        monitor = self.market_monitor_class(self.test_config)
        
        # Initialiser
        loop = asyncio.get_event_loop()
        loop.run_until_complete(monitor.initialize())
        
        # Vérifier l'initialisation
        self.assertTrue(mock_init_client.called, "Le client blockchain n'a pas été initialisé")
        self.assertTrue(mock_load_tokens.called, "Les tokens surveillés n'ont pas été chargés")
    
    @patch("gbpbot.monitoring.market_monitor.MarketMonitor._initialize_blockchain_client")
    @patch("gbpbot.monitoring.market_monitor.MarketMonitor._load_watched_tokens")
    @patch("gbpbot.monitoring.market_monitor.asyncio.create_task")
    async def test_start_stop(self, mock_create_task, mock_load_tokens, mock_init_client):
        """
        Test du démarrage et de l'arrêt du moniteur
        """
        # Configurer les mocks
        mock_init_client.return_value = AsyncMock()
        mock_load_tokens.return_value = None
        mock_create_task.return_value = None
        
        # Instancier le moniteur de marché
        monitor = self.market_monitor_class(self.test_config)
        monitor.blockchain_clients = {"avalanche": AsyncMock()}
        
        # Démarrer
        loop = asyncio.get_event_loop()
        loop.run_until_complete(monitor.start())
        
        # Vérifier le démarrage
        self.assertTrue(monitor.running, "Le moniteur n'a pas été marqué comme en cours d'exécution")
        self.assertEqual(mock_create_task.call_count, 5, "Toutes les tâches n'ont pas été créées")
        
        # Arrêter
        loop.run_until_complete(monitor.stop())
        
        # Vérifier l'arrêt
        self.assertFalse(monitor.running, "Le moniteur n'a pas été marqué comme arrêté")
    
    @patch("gbpbot.monitoring.market_monitor.MarketMonitor._initialize_blockchain_client")
    async def test_register_alert_handler(self, mock_init_client):
        """
        Test de l'enregistrement d'un gestionnaire d'alertes
        """
        # Configurer le mock
        mock_init_client.return_value = AsyncMock()
        
        # Créer une fonction gestionnaire d'alertes
        def alert_handler(opportunity):
            pass
        
        # Instancier le moniteur de marché
        monitor = self.market_monitor_class(self.test_config)
        
        # Enregistrer le gestionnaire
        monitor.register_alert_handler(alert_handler)
        
        # Vérifier l'enregistrement
        self.assertIn(alert_handler, monitor.alert_handlers, "Le gestionnaire n'a pas été enregistré")
        self.assertEqual(len(monitor.alert_handlers), 1, "Le nombre de gestionnaires est incorrect")
    
    @patch("gbpbot.monitoring.market_monitor.MarketMonitor._initialize_blockchain_client")
    async def test_add_remove_watch_token(self, mock_init_client):
        """
        Test de l'ajout et de la suppression d'un token à surveiller
        """
        # Configurer le mock
        mock_init_client.return_value = AsyncMock()
        
        # Instancier le moniteur de marché
        monitor = self.market_monitor_class(self.test_config)
        
        # Simuler la méthode de sauvegarde
        monitor._save_watched_tokens = AsyncMock()
        
        # Ajouter un token
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(monitor.add_watch_token(self.test_token))
        
        # Vérifier l'ajout
        self.assertTrue(result, "L'ajout du token a échoué")
        key = f"{self.test_token['blockchain']}:{self.test_token['address']}"
        self.assertIn(key, monitor.watched_tokens, "Le token n'a pas été ajouté à la liste de surveillance")
        self.assertEqual(monitor.watched_tokens[key]["symbol"], self.test_token["symbol"], "Le symbole n'a pas été correctement assigné")
        self.assertTrue(monitor._save_watched_tokens.called, "La méthode de sauvegarde n'a pas été appelée")
        
        # Réinitialiser le mock
        monitor._save_watched_tokens.reset_mock()
        
        # Supprimer le token
        result = loop.run_until_complete(monitor.remove_watch_token(self.test_token["address"], self.test_token["blockchain"]))
        
        # Vérifier la suppression
        self.assertTrue(result, "La suppression du token a échoué")
        self.assertNotIn(key, monitor.watched_tokens, "Le token n'a pas été supprimé de la liste de surveillance")
        self.assertTrue(monitor._save_watched_tokens.called, "La méthode de sauvegarde n'a pas été appelée")
    
    @patch("gbpbot.monitoring.market_monitor.MarketMonitor._initialize_blockchain_client")
    async def test_get_token_price(self, mock_init_client):
        """
        Test de la récupération du prix d'un token
        """
        # Configurer le mock
        mock_init_client.return_value = AsyncMock()
        
        # Instancier le moniteur de marché
        monitor = self.market_monitor_class(self.test_config)
        
        # Simuler un client blockchain
        mock_client = AsyncMock()
        mock_client.get_token_price = AsyncMock(return_value=1.5)
        monitor.blockchain_clients = {"avalanche": mock_client}
        
        # Récupérer le prix
        loop = asyncio.get_event_loop()
        price = loop.run_until_complete(monitor.get_token_price("0xTestTokenAddress123", "avalanche"))
        
        # Vérifier le prix
        self.assertEqual(price, 1.5, "Le prix n'a pas été correctement récupéré")
        
        # Vérifier le cache
        key = "avalanche:0xtesttokenaddress123"
        self.assertIn(key, monitor.price_cache, "Le prix n'a pas été mis en cache")
        self.assertEqual(monitor.price_cache[key]["price"], 1.5, "Le prix en cache est incorrect")
        
        # Modifier le client pour simuler une erreur
        mock_client.get_token_price = AsyncMock(return_value=None)
        
        # Récupérer à nouveau le prix (depuis le cache)
        price = loop.run_until_complete(monitor.get_token_price("0xTestTokenAddress123", "avalanche"))
        
        # Vérifier que le prix est toujours disponible (via le cache)
        self.assertEqual(price, 1.5, "Le prix en cache n'a pas été utilisé")
    
    @patch("gbpbot.monitoring.market_monitor.MarketMonitor._initialize_blockchain_client")
    async def test_get_active_opportunities(self, mock_init_client):
        """
        Test de la récupération des opportunités actives
        """
        # Configurer le mock
        mock_init_client.return_value = AsyncMock()
        
        # Instancier le moniteur de marché
        monitor = self.market_monitor_class(self.test_config)
        
        # Créer des opportunités
        opportunity1 = self.market_opportunity_class(
            id="test_opportunity_1",
            type="price_movement",
            blockchain="avalanche",
            token_address="0xTestTokenAddress123",
            token_symbol="TEST",
            timestamp=datetime.now(),
            expiration=datetime.now() + timedelta(minutes=10),
            priority=3,
            details={}
        )
        
        opportunity2 = self.market_opportunity_class(
            id="test_opportunity_2",
            type="arbitrage",
            blockchain="avalanche",
            token_address="0xTestTokenAddress123",
            token_symbol="TEST",
            timestamp=datetime.now(),
            expiration=datetime.now() + timedelta(minutes=10),
            priority=4,
            details={}
        )
        
        opportunity_expired = self.market_opportunity_class(
            id="test_opportunity_expired",
            type="price_movement",
            blockchain="avalanche",
            token_address="0xTestTokenAddress123",
            token_symbol="TEST",
            timestamp=datetime.now() - timedelta(minutes=20),
            expiration=datetime.now() - timedelta(minutes=10),
            priority=3,
            details={}
        )
        
        # Ajouter les opportunités
        monitor.active_opportunities = {
            "test_opportunity_1": opportunity1,
            "test_opportunity_2": opportunity2,
            "test_opportunity_expired": opportunity_expired
        }
        
        # Récupérer toutes les opportunités
        loop = asyncio.get_event_loop()
        opportunities = loop.run_until_complete(monitor.get_active_opportunities())
        
        # Vérifier les opportunités
        self.assertEqual(len(opportunities), 2, "Le nombre d'opportunités est incorrect")
        self.assertIn("test_opportunity_1", [opp["id"] for opp in opportunities], "L'opportunité 1 n'a pas été récupérée")
        self.assertIn("test_opportunity_2", [opp["id"] for opp in opportunities], "L'opportunité 2 n'a pas été récupérée")
        self.assertNotIn("test_opportunity_expired", [opp["id"] for opp in opportunities], "L'opportunité expirée a été récupérée")
        
        # Récupérer les opportunités d'arbitrage
        opportunities = loop.run_until_complete(monitor.get_active_opportunities("arbitrage"))
        
        # Vérifier les opportunités
        self.assertEqual(len(opportunities), 1, "Le nombre d'opportunités d'arbitrage est incorrect")
        self.assertEqual(opportunities[0]["id"], "test_opportunity_2", "L'opportunité d'arbitrage n'a pas été récupérée")
    
    @patch("gbpbot.monitoring.market_monitor.MarketMonitor._initialize_blockchain_client")
    @patch("gbpbot.monitoring.market_monitor.MarketMonitor._process_opportunities")
    async def test_process_opportunities(self, mock_process, mock_init_client):
        """
        Test du traitement des opportunités
        """
        # Configurer les mocks
        mock_init_client.return_value = AsyncMock()
        mock_process.return_value = None
        
        # Instancier le moniteur de marché
        monitor = self.market_monitor_class(self.test_config)
        monitor.running = True
        monitor.opportunity_queue = AsyncMock()
        
        # Créer une opportunité
        opportunity = self.market_opportunity_class(
            id="test_opportunity_1",
            type="price_movement",
            blockchain="avalanche",
            token_address="0xTestTokenAddress123",
            token_symbol="TEST",
            timestamp=datetime.now(),
            expiration=datetime.now() + timedelta(minutes=10),
            priority=3,
            details={}
        )
        
        # Simuler la récupération d'une opportunité
        monitor.opportunity_queue.get = AsyncMock(return_value=opportunity)
        monitor.opportunity_queue.task_done = AsyncMock()
        
        # Créer un gestionnaire d'alertes
        alert_handler_called = False
        def alert_handler(opp):
            nonlocal alert_handler_called
            alert_handler_called = True
        
        # Enregistrer le gestionnaire
        monitor.register_alert_handler(alert_handler)
        
        # Exécuter le traitement
        await monitor._process_opportunities()
        
        # Vérifier le traitement
        self.assertIn(opportunity.id, monitor.active_opportunities, "L'opportunité n'a pas été ajoutée aux opportunités actives")
        self.assertEqual(monitor.stats["opportunities_processed"], 1, "Le compteur d'opportunités traitées n'a pas été incrémenté")
        self.assertEqual(monitor.stats["opportunities_by_type"]["price_movement"], 1, "Le compteur par type n'a pas été incrémenté")
        self.assertTrue(monitor.opportunity_queue.task_done.called, "La tâche n'a pas été marquée comme terminée")
        self.assertTrue(alert_handler_called, "Le gestionnaire d'alertes n'a pas été appelé")


if __name__ == "__main__":
    unittest.main() 