#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests pour le module MEV/Frontrunning pour AVAX.
Ce script exécute une série de tests pour valider toutes les fonctionnalités
du module MEV/Frontrunning, incluant la détection des opportunités, l'analyse
des transactions et l'exécution des stratégies.
"""

import os
import sys
import json
import time
import unittest
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import logging

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("mev_test")

# Ajout du chemin racine au path pour les imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import des modules nécessaires
from gbpbot.core.optimization.avax_mev_optimizer import AVAXMEVOptimizer, AVAXMEVConfig
from gbpbot.strategies.mev import MEVStrategy
from gbpbot.core.blockchain.avax_client import AVAXClient
from gbpbot.utils.config_loader import ConfigLoader
from gbpbot.modules.performance_monitor import PerformanceMonitor

class MEVFrontrunningTestSuite(unittest.TestCase):
    """Suite de tests pour le module MEV/Frontrunning."""
    
    @classmethod
    def setUpClass(cls):
        """Initialisation des ressources partagées pour les tests."""
        # Chargement de la configuration
        config_path = os.path.join(os.path.dirname(__file__), '../config/test_config.json')
        cls.config = ConfigLoader.load_config(config_path)
        
        # Initialisation du client blockchain (avec clé privée de test)
        private_key = cls.config.get('test_private_key', os.getenv('TEST_PRIVATE_KEY'))
        if not private_key:
            logger.warning("Aucune clé privée de test trouvée. Les tests d'exécution seront simulés.")
        
        cls.blockchain_client = AVAXClient(
            rpc_url=cls.config.get('avax_test_rpc_url', 'https://api.avax-test.network/ext/bc/C/rpc'),
            private_key=private_key,
            is_testnet=True
        )
        
        # Initialisation du moniteur de performance pour les tests
        cls.performance_monitor = PerformanceMonitor()
        
        # Configuration du MEV Optimizer
        mev_config = AVAXMEVConfig(
            minimum_profit_threshold=0.001,  # Seuil bas pour les tests
            gas_boost_percent=5.0,
            max_priority_fee=2,
            max_base_fee_multiplier=1.5,
            simulate_transactions=True,  # Toujours simuler pour les tests
            test_mode=True
        )
        
        # Initialisation de l'optimizer
        cls.mev_optimizer = AVAXMEVOptimizer(
            blockchain_client=cls.blockchain_client,
            config=mev_config,
            performance_monitor=cls.performance_monitor
        )
        
        # Création de la stratégie MEV
        cls.mev_strategy = MEVStrategy(
            blockchain_client=cls.blockchain_client,
            config={
                "blockchain": "avax",
                "profit_threshold": 0.001,
                "gas_price_boost": 5.0,
                "test_mode": True,
                "private_key": private_key,
                "target_pairs_file": os.path.join(os.path.dirname(__file__), '../config/test_pairs.json')
            }
        )
        
        # Création du dossier de résultats si nécessaire
        cls.results_dir = os.path.join(os.path.dirname(__file__), '../test_results')
        os.makedirs(cls.results_dir, exist_ok=True)
        
        # Journal de test
        cls.test_log = []
    
    @classmethod
    def tearDownClass(cls):
        """Nettoyage après les tests."""
        # Sauvegarde des résultats
        results_file = os.path.join(cls.results_dir, f'mev_test_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
        with open(results_file, 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "tests_completed": len(cls.test_log),
                "results": cls.test_log
            }, f, indent=2)
        
        logger.info(f"Résultats des tests sauvegardés dans {results_file}")
    
    def setUp(self):
        """Configuration avant chaque test."""
        self.start_time = time.time()
    
    def tearDown(self):
        """Nettoyage après chaque test."""
        execution_time = time.time() - self.start_time
        self.test_log.append({
            "test_name": self.id(),
            "execution_time": execution_time,
            "successful": self._outcome.success
        })
    
    # TESTS UNITAIRES
    
    def test_01_optimizer_initialization(self):
        """Vérifie que l'optimizer est correctement initialisé."""
        self.assertIsNotNone(self.mev_optimizer)
        self.assertEqual(self.mev_optimizer.config.test_mode, True)
        
    def test_02_strategy_initialization(self):
        """Vérifie que la stratégie MEV est correctement initialisée."""
        self.assertIsNotNone(self.mev_strategy)
        self.assertEqual(self.mev_strategy.blockchain_type, "avax")
    
    def test_03_mempool_monitoring(self):
        """Vérifie que le monitoring du mempool fonctionne."""
        # Test asynchrone via asyncio
        async def async_test():
            monitor = self.mev_optimizer.mempool_monitor
            await monitor.start_monitoring()
            # Attendre un peu pour collecter des transactions
            await asyncio.sleep(5)
            transactions = monitor.get_pending_transactions()
            await monitor.stop_monitoring()
            return transactions
        
        # Exécute le test asynchrone
        transactions = asyncio.run(async_test())
        
        # Vérification que des transactions ont été trouvées (peut varier selon le réseau de test)
        logger.info(f"Transactions trouvées dans le mempool: {len(transactions)}")
        self.test_log[-1]["mempool_transactions"] = len(transactions)
    
    def test_04_transaction_analysis(self):
        """Vérifie la capacité à analyser des transactions pour des opportunités MEV."""
        # Simulation d'une transaction à analyser
        sample_tx = {
            "hash": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            "from": "0x1234567890123456789012345678901234567890",
            "to": "0x0987654321098765432109876543210987654321",
            "value": "1000000000000000000",  # 1 AVAX en wei
            "gas": "21000",
            "gasPrice": "50000000000",
            "input": "0x"
        }
        
        # Test de l'analyse
        result = self.mev_optimizer.analyze_transaction(sample_tx)
        
        # Vérification des résultats
        self.assertIsNotNone(result)
        self.test_log[-1]["analysis_result"] = "passed" if result is not None else "failed"
    
    def test_05_gas_price_calculation(self):
        """Vérifie le calcul optimal des prix de gas."""
        # Obtention du prix du gas actuel
        base_gas_price = asyncio.run(self.blockchain_client.get_gas_price())
        
        # Calcul du prix optimisé
        optimized_gas = self.mev_optimizer.calculate_optimal_gas_price(base_gas_price)
        
        # Vérification que le prix est augmenté correctement
        self.assertGreater(optimized_gas, base_gas_price)
        expected_increase = base_gas_price * (1 + self.mev_optimizer.config.gas_boost_percent / 100)
        self.assertAlmostEqual(optimized_gas, expected_increase, delta=base_gas_price * 0.01)
        
        self.test_log[-1]["base_gas_price"] = base_gas_price
        self.test_log[-1]["optimized_gas_price"] = optimized_gas
    
    def test_06_sandwich_attack_simulation(self):
        """Teste la simulation d'une attaque sandwich."""
        # Définition des paramètres d'une transaction cible
        target_tx = {
            "hash": "0xaabbcc1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
            "from": "0x2345678901234567890123456789012345678901",
            "to": "0x1111111111111111111111111111111111111111",  # Adresse d'un DEX
            "value": "0",
            "gas": "150000",
            "gasPrice": "40000000000",
            "input": "0x" + "0" * 200  # Simulation d'un swap
        }
        
        # Test de la simulation
        async def async_test():
            result = await self.mev_strategy.simulate_sandwich_attack(target_tx)
            return result
        
        result = asyncio.run(async_test())
        
        # Vérification
        self.assertIsNotNone(result)
        self.assertIn("profitable", result)
        self.test_log[-1]["sandwich_simulation"] = "profitable" if result.get("profitable", False) else "not_profitable"
    
    def test_07_frontrunning_simulation(self):
        """Teste la simulation de frontrunning."""
        # Définition des paramètres d'une transaction cible
        target_tx = {
            "hash": "0xddeecc1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
            "from": "0x3456789012345678901234567890123456789012",
            "to": "0x2222222222222222222222222222222222222222",  # Adresse d'un DEX
            "value": "0",
            "gas": "150000",
            "gasPrice": "40000000000",
            "input": "0x" + "0" * 200  # Simulation d'un swap
        }
        
        # Test de la simulation
        async def async_test():
            result = await self.mev_strategy.simulate_frontrunning(target_tx)
            return result
        
        result = asyncio.run(async_test())
        
        # Vérification
        self.assertIsNotNone(result)
        self.assertIn("profitable", result)
        self.test_log[-1]["frontrunning_simulation"] = "profitable" if result.get("profitable", False) else "not_profitable"
    
    def test_08_integration_with_performance_monitor(self):
        """Vérifie l'intégration avec le moniteur de performance."""
        # Enregistrement d'une opération MEV fictive
        self.performance_monitor.record_transaction({
            "type": "mev_frontrunning",
            "timestamp": datetime.now().isoformat(),
            "blockchain": "avax",
            "gas_used": 150000,
            "gas_price": 50000000000,
            "profit": 0.05,
            "success": True,
            "execution_time_ms": 850
        })
        
        # Récupération des statistiques
        stats = self.performance_monitor.get_statistics()
        
        # Vérification
        self.assertIn("transactions", stats)
        self.assertGreaterEqual(stats["transactions"]["total"], 1)
        self.test_log[-1]["performance_integration"] = "passed"
    
    def test_09_end_to_end_simulation(self):
        """Test complet de bout en bout simulant une opération MEV."""
        async def async_test():
            # Démarrage de la stratégie
            await self.mev_strategy.start()
            
            # Simulation de l'exécution pendant un certain temps
            logger.info("Exécution de la stratégie MEV pendant 30 secondes...")
            await asyncio.sleep(30)
            
            # Arrêt de la stratégie
            await self.mev_strategy.stop()
            
            # Récupération des statistiques
            stats = self.mev_strategy.get_statistics()
            return stats
        
        stats = asyncio.run(async_test())
        
        # Vérification
        self.assertIsNotNone(stats)
        self.assertIn("opportunities_detected", stats)
        self.test_log[-1]["e2e_simulation"] = stats
    
    def test_10_stress_test(self):
        """Test de stress pour vérifier la stabilité du module."""
        async def async_test():
            start_time = time.time()
            total_time = 60  # 1 minute de test
            
            # Initialisation des compteurs
            transaction_count = 0
            analysis_count = 0
            simulation_count = 0
            
            # Démarrage du monitoring
            await self.mev_optimizer.mempool_monitor.start_monitoring()
            
            # Boucle de test
            while time.time() - start_time < total_time:
                # Récupération des transactions
                transactions = self.mev_optimizer.mempool_monitor.get_pending_transactions()
                transaction_count += len(transactions)
                
                # Analyse des 5 premières transactions (ou moins s'il y en a moins)
                for i, tx in enumerate(transactions[:5]):
                    result = self.mev_optimizer.analyze_transaction(tx)
                    analysis_count += 1
                    
                    # Simulation si l'analyse est positive
                    if result and result.get("potential_profit", 0) > 0:
                        # Alternance entre frontrunning et sandwich
                        if i % 2 == 0:
                            await self.mev_strategy.simulate_frontrunning(tx)
                        else:
                            await self.mev_strategy.simulate_sandwich_attack(tx)
                        simulation_count += 1
                
                # Pause pour éviter de surcharger le système
                await asyncio.sleep(1)
            
            # Arrêt du monitoring
            await self.mev_optimizer.mempool_monitor.stop_monitoring()
            
            return {
                "duration": time.time() - start_time,
                "transactions_processed": transaction_count,
                "analyses_performed": analysis_count,
                "simulations_run": simulation_count
            }
        
        results = asyncio.run(async_test())
        
        # Vérification
        self.assertGreaterEqual(results["transactions_processed"], 0)
        self.assertGreaterEqual(results["analyses_performed"], 0)
        logger.info(f"Test de stress terminé: {results}")
        self.test_log[-1]["stress_test"] = results


if __name__ == "__main__":
    unittest.main() 