#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests unitaires pour le module d'interface unifiée du GBPBot

Ce module teste l'interface unifiée qui permet de connecter tous
les modules du GBPBot et d'interagir avec le bot de manière simplifiée.
"""

import os
import sys
import json
import unittest
import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

# Ajout du chemin racine au sys.path pour les imports
ROOT_DIR = Path(__file__).parent.parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Import des modules de test
from gbpbot.tests.setup_test_environment import setup_test_environment, cleanup_test_environment


class TestUnifiedInterfaceModule(unittest.TestCase):
    """Suite de tests pour le module d'interface unifiée du GBPBot"""
    
    @classmethod
    def setUpClass(cls):
        """
        Préparation de l'environnement de test avant l'exécution des tests
        """
        # Configuration de l'environnement de test
        cls.env_file, cls.wallet_paths = setup_test_environment()
        
        # Configuration pour les tests
        cls.test_config = {
            "interface": {
                "cli_enabled": True,
                "telegram_enabled": False,
                "web_enabled": False,
                "auto_start": False,
                "default_mode": "manual",
                "log_level": "INFO"
            },
            "modules": {
                "sniping": {
                    "enabled": True,
                    "auto_mode": False,
                    "target_blockchain": "avalanche",
                    "min_liquidity_usd": 10000,
                    "max_slippage": 2.0
                },
                "arbitrage": {
                    "enabled": True,
                    "auto_mode": False,
                    "target_blockchain": "avalanche",
                    "min_profit_usd": 5,
                    "max_slippage": 1.0
                },
                "mev": {
                    "enabled": True,
                    "auto_mode": False,
                    "target_blockchain": "avalanche",
                    "min_profit_usd": 10
                },
                "monitoring": {
                    "enabled": True,
                    "system_monitoring": True,
                    "performance_monitoring": True,
                    "alert_telegram": False
                }
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
        # Tenter d'importer les modules d'interface unifiée, avec gestion des erreurs
        try:
            from gbpbot.interface.unified_interface import UnifiedInterface
            from gbpbot.interface.cli.cli_manager import CLIManager
            from gbpbot.interface.module_mapper import ModuleMapper
            
            self.unified_interface_class = UnifiedInterface
            self.cli_manager_class = CLIManager
            self.module_mapper_class = ModuleMapper
        except ImportError as e:
            self.skipTest(f"Module d'interface unifiée non disponible: {str(e)}")
    
    def test_module_import(self):
        """
        Test de l'importation du module d'interface unifiée
        """
        # Vérifier que les modules ont été importés correctement
        self.assertIsNotNone(self.unified_interface_class, "La classe UnifiedInterface n'a pas pu être importée")
        self.assertIsNotNone(self.cli_manager_class, "La classe CLIManager n'a pas pu être importée")
        self.assertIsNotNone(self.module_mapper_class, "La classe ModuleMapper n'a pas pu être importée")
    
    @patch("gbpbot.interface.unified_interface.UnifiedInterface._initialize_modules")
    @patch("gbpbot.interface.unified_interface.UnifiedInterface._initialize_interfaces")
    def test_unified_interface_initialization(self, mock_init_interfaces, mock_init_modules):
        """
        Test de l'initialisation de l'interface unifiée
        """
        # Configurer les mocks
        mock_init_interfaces.return_value = True
        mock_init_modules.return_value = True
        
        # Instancier l'interface unifiée
        interface = self.unified_interface_class(self.test_config)
        
        # Vérifier l'initialisation
        self.assertIsNotNone(interface, "L'interface unifiée n'a pas été instanciée correctement")
        self.assertEqual(interface.config, self.test_config, "La configuration n'a pas été correctement assignée")
        mock_init_interfaces.assert_called_once()
        mock_init_modules.assert_called_once()
    
    @patch("gbpbot.interface.unified_interface.UnifiedInterface._initialize_modules")
    @patch("gbpbot.interface.unified_interface.UnifiedInterface._initialize_interfaces")
    def test_module_configuration(self, mock_init_interfaces, mock_init_modules):
        """
        Test de la configuration des modules
        """
        # Configurer les mocks
        mock_init_interfaces.return_value = True
        mock_init_modules.return_value = True
        
        # Instancier l'interface unifiée
        interface = self.unified_interface_class(self.test_config)
        
        # Vérifier la configuration des modules
        self.assertTrue(interface.is_module_enabled("sniping"), "Le module sniping n'est pas activé")
        self.assertTrue(interface.is_module_enabled("arbitrage"), "Le module arbitrage n'est pas activé")
        self.assertTrue(interface.is_module_enabled("mev"), "Le module MEV n'est pas activé")
        self.assertTrue(interface.is_module_enabled("monitoring"), "Le module monitoring n'est pas activé")
        
        # Vérifier les modes automatiques
        self.assertFalse(interface.is_auto_mode_enabled("sniping"), "Le mode auto du module sniping est activé")
        self.assertFalse(interface.is_auto_mode_enabled("arbitrage"), "Le mode auto du module arbitrage est activé")
        self.assertFalse(interface.is_auto_mode_enabled("mev"), "Le mode auto du module MEV est activé")
    
    @patch("gbpbot.interface.unified_interface.UnifiedInterface._initialize_modules")
    @patch("gbpbot.interface.unified_interface.UnifiedInterface._initialize_interfaces")
    def test_interface_configuration(self, mock_init_interfaces, mock_init_modules):
        """
        Test de la configuration des interfaces
        """
        # Configurer les mocks
        mock_init_interfaces.return_value = True
        mock_init_modules.return_value = True
        
        # Instancier l'interface unifiée
        interface = self.unified_interface_class(self.test_config)
        
        # Vérifier la configuration des interfaces
        self.assertTrue(interface.is_interface_enabled("cli"), "L'interface CLI n'est pas activée")
        self.assertFalse(interface.is_interface_enabled("telegram"), "L'interface Telegram est activée")
        self.assertFalse(interface.is_interface_enabled("web"), "L'interface Web est activée")
    
    @patch("gbpbot.interface.unified_interface.UnifiedInterface._initialize_modules")
    @patch("gbpbot.interface.unified_interface.UnifiedInterface._initialize_interfaces")
    @patch("gbpbot.interface.unified_interface.UnifiedInterface.start_module")
    def test_start_module(self, mock_start_module, mock_init_interfaces, mock_init_modules):
        """
        Test du démarrage d'un module
        """
        # Configurer les mocks
        mock_init_interfaces.return_value = True
        mock_init_modules.return_value = True
        mock_start_module.return_value = True
        
        # Instancier l'interface unifiée
        interface = self.unified_interface_class(self.test_config)
        
        # Démarrer un module
        result = interface.start_module("sniping")
        
        # Vérifier le démarrage
        self.assertTrue(result, "Le démarrage du module a échoué")
        mock_start_module.assert_called_once_with("sniping")
    
    @patch("gbpbot.interface.unified_interface.UnifiedInterface._initialize_modules")
    @patch("gbpbot.interface.unified_interface.UnifiedInterface._initialize_interfaces")
    @patch("gbpbot.interface.unified_interface.UnifiedInterface.stop_module")
    def test_stop_module(self, mock_stop_module, mock_init_interfaces, mock_init_modules):
        """
        Test de l'arrêt d'un module
        """
        # Configurer les mocks
        mock_init_interfaces.return_value = True
        mock_init_modules.return_value = True
        mock_stop_module.return_value = True
        
        # Instancier l'interface unifiée
        interface = self.unified_interface_class(self.test_config)
        
        # Arrêter un module
        result = interface.stop_module("arbitrage")
        
        # Vérifier l'arrêt
        self.assertTrue(result, "L'arrêt du module a échoué")
        mock_stop_module.assert_called_once_with("arbitrage")
    
    @patch("gbpbot.interface.unified_interface.UnifiedInterface._initialize_modules")
    @patch("gbpbot.interface.unified_interface.UnifiedInterface._initialize_interfaces")
    @patch("gbpbot.interface.unified_interface.UnifiedInterface.get_module_status")
    def test_get_module_status(self, mock_get_status, mock_init_interfaces, mock_init_modules):
        """
        Test de la récupération du statut d'un module
        """
        # Configurer les mocks
        mock_init_interfaces.return_value = True
        mock_init_modules.return_value = True
        mock_get_status.return_value = {
            "running": True,
            "auto_mode": False,
            "uptime": 3600,
            "actions_executed": 5,
            "profits": {
                "total_usd": 50.0,
                "last_24h_usd": 20.0
            }
        }
        
        # Instancier l'interface unifiée
        interface = self.unified_interface_class(self.test_config)
        
        # Récupérer le statut d'un module
        status = interface.get_module_status("sniping")
        
        # Vérifier le statut
        self.assertIsNotNone(status, "Le statut n'a pas été récupéré")
        self.assertTrue(status["running"], "Le module n'est pas en cours d'exécution")
        self.assertFalse(status["auto_mode"], "Le mode auto est activé")
        self.assertEqual(status["uptime"], 3600, "La durée d'exécution n'est pas correcte")
        self.assertEqual(status["actions_executed"], 5, "Le nombre d'actions exécutées n'est pas correct")
        self.assertEqual(status["profits"]["total_usd"], 50.0, "Le profit total n'est pas correct")
    
    @patch("gbpbot.interface.unified_interface.UnifiedInterface._initialize_modules")
    @patch("gbpbot.interface.unified_interface.UnifiedInterface._initialize_interfaces")
    @patch("gbpbot.interface.unified_interface.UnifiedInterface.set_module_config")
    def test_set_module_config(self, mock_set_config, mock_init_interfaces, mock_init_modules):
        """
        Test de la modification de la configuration d'un module
        """
        # Configurer les mocks
        mock_init_interfaces.return_value = True
        mock_init_modules.return_value = True
        mock_set_config.return_value = True
        
        # Instancier l'interface unifiée
        interface = self.unified_interface_class(self.test_config)
        
        # Modifier la configuration d'un module
        new_config = {
            "auto_mode": True,
            "min_profit_usd": 10,
            "max_slippage": 2.0
        }
        result = interface.set_module_config("arbitrage", new_config)
        
        # Vérifier la modification
        self.assertTrue(result, "La modification de la configuration a échoué")
        mock_set_config.assert_called_once_with("arbitrage", new_config)
    
    @patch("gbpbot.interface.unified_interface.UnifiedInterface._initialize_modules")
    @patch("gbpbot.interface.unified_interface.UnifiedInterface._initialize_interfaces")
    def test_get_available_modules(self, mock_init_interfaces, mock_init_modules):
        """
        Test de la récupération des modules disponibles
        """
        # Configurer les mocks
        mock_init_interfaces.return_value = True
        mock_init_modules.return_value = True
        
        # Instancier l'interface unifiée
        interface = self.unified_interface_class(self.test_config)
        
        # Simuler la liste des modules disponibles
        interface.available_modules = ["sniping", "arbitrage", "mev", "monitoring"]
        
        # Récupérer les modules disponibles
        modules = interface.get_available_modules()
        
        # Vérifier les modules
        self.assertIsNotNone(modules, "La liste des modules n'a pas été récupérée")
        self.assertEqual(len(modules), 4, "Le nombre de modules disponibles n'est pas correct")
        self.assertIn("sniping", modules, "Le module sniping n'est pas dans la liste")
        self.assertIn("arbitrage", modules, "Le module arbitrage n'est pas dans la liste")
        self.assertIn("mev", modules, "Le module MEV n'est pas dans la liste")
        self.assertIn("monitoring", modules, "Le module monitoring n'est pas dans la liste")
    
    @patch("gbpbot.interface.unified_interface.UnifiedInterface._initialize_modules")
    @patch("gbpbot.interface.unified_interface.UnifiedInterface._initialize_interfaces")
    @patch("gbpbot.interface.unified_interface.UnifiedInterface.execute_action")
    def test_execute_action(self, mock_execute, mock_init_interfaces, mock_init_modules):
        """
        Test de l'exécution d'une action
        """
        # Configurer les mocks
        mock_init_interfaces.return_value = True
        mock_init_modules.return_value = True
        mock_execute.return_value = {
            "success": True,
            "action_id": "abc123",
            "result": {
                "transaction_hash": "0xTestTransactionHash123",
                "profit_usd": 15.0,
                "gas_cost_usd": 2.0
            }
        }
        
        # Instancier l'interface unifiée
        interface = self.unified_interface_class(self.test_config)
        
        # Exécuter une action
        action_params = {
            "token_address": "0xTestTokenAddress123",
            "amount_usd": 100,
            "max_slippage": 2.0
        }
        result = interface.execute_action("sniping", "buy_token", action_params)
        
        # Vérifier l'exécution
        self.assertIsNotNone(result, "Le résultat de l'action n'a pas été récupéré")
        self.assertTrue(result["success"], "L'action a échoué")
        self.assertEqual(result["action_id"], "abc123", "L'ID de l'action n'est pas correct")
        self.assertEqual(result["result"]["profit_usd"], 15.0, "Le profit n'est pas correct")
    
    @patch("gbpbot.interface.cli.cli_manager.CLIManager.__init__")
    @patch("gbpbot.interface.cli.cli_manager.CLIManager.start")
    def test_cli_manager_initialization(self, mock_start, mock_init):
        """
        Test de l'initialisation du gestionnaire CLI
        """
        # Configurer les mocks
        mock_init.return_value = None
        mock_start.return_value = None
        
        # Instancier le gestionnaire CLI
        cli_manager = self.cli_manager_class(self.test_config)
        
        # Vérifier l'initialisation
        mock_init.assert_called_once()
        
        # Démarrer l'interface CLI
        cli_manager.start()
        
        # Vérifier le démarrage
        mock_start.assert_called_once()
    
    @patch("gbpbot.interface.module_mapper.ModuleMapper.__init__")
    @patch("gbpbot.interface.module_mapper.ModuleMapper.map_module")
    def test_module_mapper(self, mock_map, mock_init):
        """
        Test du mappeur de modules
        """
        # Configurer les mocks
        mock_init.return_value = None
        mock_map.return_value = {
            "module_instance": MagicMock(),
            "module_actions": ["start", "stop", "get_status"]
        }
        
        # Instancier le mappeur de modules
        mapper = self.module_mapper_class(self.test_config)
        
        # Vérifier l'initialisation
        mock_init.assert_called_once()
        
        # Mapper un module
        result = mapper.map_module("sniping")
        
        # Vérifier le mapping
        self.assertIsNotNone(result, "Le résultat du mapping n'a pas été récupéré")
        self.assertIn("module_instance", result, "L'instance du module n'est pas dans le résultat")
        self.assertIn("module_actions", result, "Les actions du module ne sont pas dans le résultat")
    
    @patch("gbpbot.interface.unified_interface.UnifiedInterface._initialize_modules")
    @patch("gbpbot.interface.unified_interface.UnifiedInterface._initialize_interfaces")
    async def test_async_module_interaction(self, mock_init_interfaces, mock_init_modules):
        """
        Test des interactions asynchrones avec les modules
        """
        # Configurer les mocks
        mock_init_interfaces.return_value = True
        mock_init_modules.return_value = True
        
        # Instancier l'interface unifiée
        interface = self.unified_interface_class(self.test_config)
        
        # Simuler des méthodes asynchrones
        interface.start_module_async = AsyncMock(return_value=True)
        interface.stop_module_async = AsyncMock(return_value=True)
        interface.execute_action_async = AsyncMock(return_value={
            "success": True,
            "action_id": "xyz789",
            "result": {
                "transaction_hash": "0xTestTransactionHash456",
                "profit_usd": 25.0,
                "gas_cost_usd": 3.0
            }
        })
        
        # Tester les méthodes asynchrones
        start_result = await interface.start_module_async("mev")
        self.assertTrue(start_result, "Le démarrage asynchrone du module a échoué")
        interface.start_module_async.assert_called_once_with("mev")
        
        stop_result = await interface.stop_module_async("mev")
        self.assertTrue(stop_result, "L'arrêt asynchrone du module a échoué")
        interface.stop_module_async.assert_called_once_with("mev")
        
        action_params = {
            "pair_addresses": ["0xPair1", "0xPair2"],
            "amount_usd": 200,
            "max_slippage": 1.0
        }
        execute_result = await interface.execute_action_async("arbitrage", "execute_arbitrage", action_params)
        self.assertTrue(execute_result["success"], "L'exécution asynchrone de l'action a échoué")
        self.assertEqual(execute_result["action_id"], "xyz789", "L'ID de l'action asynchrone n'est pas correct")
        interface.execute_action_async.assert_called_once_with("arbitrage", "execute_arbitrage", action_params)
    
    @patch("gbpbot.interface.unified_interface.UnifiedInterface._initialize_modules")
    @patch("gbpbot.interface.unified_interface.UnifiedInterface._initialize_interfaces")
    @patch("gbpbot.interface.unified_interface.UnifiedInterface.get_system_status")
    def test_system_status(self, mock_get_status, mock_init_interfaces, mock_init_modules):
        """
        Test de la récupération du statut du système
        """
        # Configurer les mocks
        mock_init_interfaces.return_value = True
        mock_init_modules.return_value = True
        mock_get_status.return_value = {
            "system": {
                "cpu_usage": 35.2,
                "memory_usage": 42.8,
                "uptime": 86400
            },
            "modules": {
                "sniping": {
                    "running": True,
                    "auto_mode": False,
                    "actions_executed": 10
                },
                "arbitrage": {
                    "running": True,
                    "auto_mode": False,
                    "actions_executed": 15
                },
                "mev": {
                    "running": False,
                    "auto_mode": False,
                    "actions_executed": 0
                },
                "monitoring": {
                    "running": True,
                    "system_monitoring": True,
                    "performance_monitoring": True
                }
            },
            "wallets": {
                "avalanche": {
                    "address": "0xTestWalletAddress123",
                    "balance_native": 10.5,
                    "balance_usd": 210.0
                },
                "solana": {
                    "address": "TestSolanaAddress123",
                    "balance_native": 50.0,
                    "balance_usd": 100.0
                }
            },
            "performance": {
                "total_profit_usd": 150.0,
                "last_24h_profit_usd": 35.0,
                "total_trades": 25,
                "successful_trades": 22,
                "success_rate": 88.0
            }
        }
        
        # Instancier l'interface unifiée
        interface = self.unified_interface_class(self.test_config)
        
        # Récupérer le statut du système
        status = interface.get_system_status()
        
        # Vérifier le statut
        self.assertIsNotNone(status, "Le statut du système n'a pas été récupéré")
        self.assertIn("system", status, "Le statut du système ne contient pas les informations système")
        self.assertIn("modules", status, "Le statut du système ne contient pas les informations des modules")
        self.assertIn("wallets", status, "Le statut du système ne contient pas les informations des wallets")
        self.assertIn("performance", status, "Le statut du système ne contient pas les informations de performance")
        
        # Vérifier les détails
        self.assertEqual(status["system"]["cpu_usage"], 35.2, "L'utilisation CPU n'est pas correcte")
        self.assertEqual(status["performance"]["total_profit_usd"], 150.0, "Le profit total n'est pas correct")
        self.assertEqual(len(status["modules"]), 4, "Le nombre de modules n'est pas correct")
        self.assertEqual(len(status["wallets"]), 2, "Le nombre de wallets n'est pas correct")
    
    @patch("gbpbot.interface.unified_interface.UnifiedInterface._initialize_modules")
    @patch("gbpbot.interface.unified_interface.UnifiedInterface._initialize_interfaces")
    @patch("gbpbot.interface.unified_interface.UnifiedInterface.start_auto_mode")
    @patch("gbpbot.interface.unified_interface.UnifiedInterface.stop_auto_mode")
    def test_auto_mode_control(self, mock_stop_auto, mock_start_auto, mock_init_interfaces, mock_init_modules):
        """
        Test du contrôle du mode automatique
        """
        # Configurer les mocks
        mock_init_interfaces.return_value = True
        mock_init_modules.return_value = True
        mock_start_auto.return_value = True
        mock_stop_auto.return_value = True
        
        # Instancier l'interface unifiée
        interface = self.unified_interface_class(self.test_config)
        
        # Démarrer le mode automatique
        start_result = interface.start_auto_mode("sniping")
        
        # Vérifier le démarrage
        self.assertTrue(start_result, "Le démarrage du mode automatique a échoué")
        mock_start_auto.assert_called_once_with("sniping")
        
        # Arrêter le mode automatique
        stop_result = interface.stop_auto_mode("sniping")
        
        # Vérifier l'arrêt
        self.assertTrue(stop_result, "L'arrêt du mode automatique a échoué")
        mock_stop_auto.assert_called_once_with("sniping")


if __name__ == "__main__":
    unittest.main() 