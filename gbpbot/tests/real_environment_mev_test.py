#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test du module MEV en environnement réel pour GBPBot
===================================================

Ce script exécute une série de tests en environnement réel pour
valider le fonctionnement du module MEV/Frontrunning.

Ces tests sont conçus pour fonctionner sur le testnet et incluent :
1. La détection d'opportunités de MEV réelles
2. L'analyse de transactions dans le mempool
3. La simulation d'exécution de stratégies
4. La vérification de l'optimisation du gas
5. L'intégration avec l'interface unifiée
"""

import os
import sys
import json
import time
import asyncio
import logging
import argparse
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta

# Ajout du chemin racine au path pour les imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import des modules GBPBot
from gbpbot.strategies.mev import MEVStrategy
from gbpbot.core.optimization.avax_mev_optimizer import AVAXMEVOptimizer, AVAXMEVConfig, MempoolMonitor
from gbpbot.core.optimization.jito_mev_optimizer import JitoMEVOptimizer, JitoConfig
from gbpbot.core.blockchain.avax_client import AVAXClient
from gbpbot.core.blockchain.solana_client import SolanaClient
from gbpbot.utils.config_loader import ConfigLoader
from gbpbot.interface.unified_interface import UnifiedInterface
from gbpbot.core.rpc.rpc_manager import rpc_manager
from gbpbot.utils.logging import setup_logger

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("real_env_mev_test")

class RealEnvironmentMEVTester:
    """
    Testeur de stratégies MEV en environnement réel.
    
    Cette classe exécute des tests en environnement réel pour valider 
    le fonctionnement du module MEV/Frontrunning.
    """
    
    def __init__(self, config_path: str = None, testnet: bool = True):
        """
        Initialise le testeur de MEV.
        
        Args:
            config_path: Chemin vers le fichier de configuration
            testnet: Utiliser le testnet (True) ou le mainnet (False)
        """
        # Charge la configuration
        self.config = self._load_config(config_path)
        self.testnet = testnet
        
        # Configure la blockchain
        self.blockchain = self.config.get("blockchain", "avax").lower()
        self.config["testnet"] = testnet
        
        # Statistiques et résultats des tests
        self.results = {
            "mempool_monitoring": {
                "success": False,
                "detected_transactions": 0,
                "time_elapsed": 0,
                "status": "Non exécuté"
            },
            "transaction_analysis": {
                "success": False,
                "analyzed_transactions": 0,
                "potential_opportunities": 0,
                "time_elapsed": 0,
                "status": "Non exécuté"
            },
            "strategy_simulation": {
                "success": False,
                "simulated_transactions": 0,
                "expected_profit": 0.0,
                "time_elapsed": 0,
                "status": "Non exécuté"
            },
            "gas_optimization": {
                "success": False,
                "optimized_transactions": 0,
                "gas_savings": 0.0,
                "time_elapsed": 0,
                "status": "Non exécuté"
            },
            "unified_interface": {
                "success": False,
                "launched_module": False,
                "stopped_module": False,
                "status": "Non exécuté"
            }
        }
        self.start_time = None
        self.mev_strategy = None
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """
        Charge la configuration depuis un fichier ou utilise la configuration par défaut.
        
        Args:
            config_path: Chemin vers le fichier de configuration
            
        Returns:
            Configuration chargée ou configuration par défaut
        """
        if config_path and os.path.exists(config_path):
            return ConfigLoader.load_config(config_path)
        
        # Configuration par défaut pour les tests
        return {
            "blockchain": "avax",
            "min_profit_threshold": 0.005,
            "min_sandwich_profit_threshold": 0.01,
            "max_gas_price_gwei": 100.0,
            "gas_boost_percentage": 5.0,
            "monitoring_duration_seconds": 60,
            "simulation_only": True,  # Ne pas exécuter de vraies transactions
            "private_keys": [],  # À remplir avec des clés de test si nécessaire
            "pairs_to_monitor": [
                {"token0": "WAVAX", "token1": "USDC"},
                {"token0": "WAVAX", "token1": "USDT"},
                {"token0": "WAVAX", "token1": "WETH"}
            ]
        }
        
    async def initialize_mev_strategy(self) -> bool:
        """
        Initialise la stratégie MEV.
        
        Returns:
            True si l'initialisation est réussie, False sinon
        """
        try:
            self.mev_strategy = MEVStrategy(self.config)
            await self.mev_strategy.initialize()
            logger.info(f"Stratégie MEV initialisée pour {self.blockchain}")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de la stratégie MEV: {str(e)}")
            return False
            
    async def test_mempool_monitoring(self, duration_seconds: int = 60) -> Dict[str, Any]:
        """
        Teste la surveillance du mempool.
        
        Args:
            duration_seconds: Durée du test en secondes
            
        Returns:
            Résultats du test
        """
        start_time = time.time()
        self.results["mempool_monitoring"]["status"] = "En cours"
        logger.info(f"Démarrage du test de surveillance du mempool ({duration_seconds}s)...")
        
        try:
            # Initialiser la stratégie MEV si nécessaire
            if not self.mev_strategy:
                if not await self.initialize_mev_strategy():
                    self.results["mempool_monitoring"]["status"] = "Échec d'initialisation"
                    return self.results["mempool_monitoring"]
                    
            # Démarre la surveillance du mempool
            await self.mev_strategy.start_mempool_monitoring()
            
            # Attendre la durée spécifiée
            await asyncio.sleep(duration_seconds)
            
            # Récupère les statistiques
            detected_txs = len(self.mev_strategy.mempool_transactions)
            
            # Arrête la surveillance
            await self.mev_strategy.stop_mempool_monitoring()
            
            # Met à jour les résultats
            elapsed_time = time.time() - start_time
            self.results["mempool_monitoring"] = {
                "success": detected_txs > 0,
                "detected_transactions": detected_txs,
                "time_elapsed": elapsed_time,
                "status": "Réussi" if detected_txs > 0 else "Aucune transaction détectée"
            }
            
            logger.info(f"Test de surveillance du mempool terminé: {detected_txs} transactions détectées en {elapsed_time:.2f}s")
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            self.results["mempool_monitoring"] = {
                "success": False,
                "detected_transactions": 0,
                "time_elapsed": elapsed_time,
                "status": f"Erreur: {str(e)}"
            }
            logger.error(f"Erreur lors du test de surveillance du mempool: {str(e)}")
            
        return self.results["mempool_monitoring"]
            
    async def test_transaction_analysis(self) -> Dict[str, Any]:
        """
        Teste l'analyse des transactions.
        
        Returns:
            Résultats du test
        """
        start_time = time.time()
        self.results["transaction_analysis"]["status"] = "En cours"
        logger.info("Démarrage du test d'analyse des transactions...")
        
        try:
            # Vérifie que le test de mempool a été exécuté
            if not self.results["mempool_monitoring"]["success"]:
                logger.warning("Le test de surveillance du mempool n'a pas été exécuté avec succès. Exécution...")
                await self.test_mempool_monitoring()
                
            # Vérifie qu'il y a des transactions à analyser
            if not self.mev_strategy or len(self.mev_strategy.mempool_transactions) == 0:
                self.results["transaction_analysis"] = {
                    "success": False,
                    "analyzed_transactions": 0,
                    "potential_opportunities": 0,
                    "time_elapsed": time.time() - start_time,
                    "status": "Aucune transaction à analyser"
                }
                return self.results["transaction_analysis"]
                
            # Analyse les transactions
            analyzed_count = 0
            opportunities_count = 0
            
            for tx_hash, tx_data in self.mev_strategy.mempool_transactions.items():
                analyzed_count += 1
                # Analyse pour détecter les opportunités
                is_opportunity = await self.mev_strategy.analyze_transaction(tx_data)
                if is_opportunity:
                    opportunities_count += 1
            
            # Met à jour les résultats
            elapsed_time = time.time() - start_time
            self.results["transaction_analysis"] = {
                "success": analyzed_count > 0,
                "analyzed_transactions": analyzed_count,
                "potential_opportunities": opportunities_count,
                "time_elapsed": elapsed_time,
                "status": f"Réussi: {opportunities_count} opportunités détectées sur {analyzed_count} transactions"
            }
            
            logger.info(f"Test d'analyse des transactions terminé: {opportunities_count} opportunités sur {analyzed_count} transactions")
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            self.results["transaction_analysis"] = {
                "success": False,
                "analyzed_transactions": 0,
                "potential_opportunities": 0,
                "time_elapsed": elapsed_time,
                "status": f"Erreur: {str(e)}"
            }
            logger.error(f"Erreur lors du test d'analyse des transactions: {str(e)}")
            
        return self.results["transaction_analysis"]
    
    async def test_strategy_simulation(self) -> Dict[str, Any]:
        """
        Teste la simulation des stratégies.
        
        Returns:
            Résultats du test
        """
        start_time = time.time()
        self.results["strategy_simulation"]["status"] = "En cours"
        logger.info("Démarrage du test de simulation des stratégies...")
        
        try:
            # Vérifie que l'analyse des transactions a été exécutée
            if not self.results["transaction_analysis"]["success"]:
                logger.warning("Le test d'analyse des transactions n'a pas été exécuté avec succès. Exécution...")
                await self.test_transaction_analysis()
                
            # Vérifie qu'il y a des opportunités à simuler
            if self.results["transaction_analysis"]["potential_opportunities"] == 0:
                self.results["strategy_simulation"] = {
                    "success": False,
                    "simulated_transactions": 0,
                    "expected_profit": 0.0,
                    "time_elapsed": time.time() - start_time,
                    "status": "Aucune opportunité à simuler"
                }
                return self.results["strategy_simulation"]
                
            # Simule les transactions
            simulated_count = 0
            total_expected_profit = 0.0
            
            # Récupère les opportunités et simule les stratégies
            for opportunity in self.mev_strategy.opportunities:
                simulated_result = await self.mev_strategy.simulate_strategy(opportunity)
                if simulated_result["success"]:
                    simulated_count += 1
                    total_expected_profit += simulated_result["expected_profit"]
            
            # Met à jour les résultats
            elapsed_time = time.time() - start_time
            self.results["strategy_simulation"] = {
                "success": simulated_count > 0,
                "simulated_transactions": simulated_count,
                "expected_profit": total_expected_profit,
                "time_elapsed": elapsed_time,
                "status": f"Réussi: {simulated_count} simulations avec {total_expected_profit:.6f} profit attendu"
            }
            
            logger.info(f"Test de simulation terminé: {simulated_count} stratégies simulées avec {total_expected_profit:.6f} profit attendu")
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            self.results["strategy_simulation"] = {
                "success": False,
                "simulated_transactions": 0,
                "expected_profit": 0.0,
                "time_elapsed": elapsed_time,
                "status": f"Erreur: {str(e)}"
            }
            logger.error(f"Erreur lors du test de simulation des stratégies: {str(e)}")
            
        return self.results["strategy_simulation"]
    
    async def test_gas_optimization(self) -> Dict[str, Any]:
        """
        Teste l'optimisation du gas.
        
        Returns:
            Résultats du test
        """
        start_time = time.time()
        self.results["gas_optimization"]["status"] = "En cours"
        logger.info("Démarrage du test d'optimisation du gas...")
        
        try:
            # Vérifie que la simulation des stratégies a été exécutée
            if not self.results["strategy_simulation"]["success"]:
                logger.warning("Le test de simulation des stratégies n'a pas été exécuté avec succès. Exécution...")
                await self.test_strategy_simulation()
                
            # Vérifie qu'il y a des transactions à optimiser
            if self.results["strategy_simulation"]["simulated_transactions"] == 0:
                self.results["gas_optimization"] = {
                    "success": False,
                    "optimized_transactions": 0,
                    "gas_savings": 0.0,
                    "time_elapsed": time.time() - start_time,
                    "status": "Aucune transaction à optimiser"
                }
                return self.results["gas_optimization"]
                
            # Optimise les transactions
            optimized_count = 0
            total_gas_savings = 0.0
            
            # Récupère les transactions simulées et optimise le gas
            for tx in self.mev_strategy.simulated_transactions:
                original_gas = tx.get("gas_price", 0)
                optimized_result = await self.mev_strategy.optimize_gas(tx)
                if optimized_result["success"]:
                    optimized_count += 1
                    new_gas = optimized_result.get("optimized_gas_price", original_gas)
                    savings = (original_gas - new_gas) * tx.get("gas_limit", 0)
                    total_gas_savings += savings
            
            # Met à jour les résultats
            elapsed_time = time.time() - start_time
            self.results["gas_optimization"] = {
                "success": optimized_count > 0,
                "optimized_transactions": optimized_count,
                "gas_savings": total_gas_savings,
                "time_elapsed": elapsed_time,
                "status": f"Réussi: {optimized_count} transactions optimisées avec {total_gas_savings:.6f} économies de gas"
            }
            
            logger.info(f"Test d'optimisation du gas terminé: {optimized_count} transactions optimisées")
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            self.results["gas_optimization"] = {
                "success": False,
                "optimized_transactions": 0,
                "gas_savings": 0.0,
                "time_elapsed": elapsed_time,
                "status": f"Erreur: {str(e)}"
            }
            logger.error(f"Erreur lors du test d'optimisation du gas: {str(e)}")
            
        return self.results["gas_optimization"]
    
    async def test_unified_interface(self) -> Dict[str, Any]:
        """
        Teste l'intégration avec l'interface unifiée.
        
        Returns:
            Résultats du test
        """
        start_time = time.time()
        self.results["unified_interface"]["status"] = "En cours"
        logger.info("Démarrage du test d'intégration avec l'interface unifiée...")
        
        try:
            # Initialise l'interface unifiée
            ui = UnifiedInterface()
            await ui.initialize()
            
            # Lance le module MEV/Frontrunning
            launch_result, message = await ui.launch_module(
                module_name="MEV/Frontrunning", 
                mode="simulation" if self.testnet else "live",
                autonomy_level="semi-autonome"
            )
            
            if not launch_result:
                self.results["unified_interface"] = {
                    "success": False,
                    "launched_module": False,
                    "stopped_module": False,
                    "status": f"Échec du lancement: {message}"
                }
                return self.results["unified_interface"]
                
            # Attendre un peu
            await asyncio.sleep(5)
            
            # Vérifier que le module est en cours d'exécution
            running_modules = await ui.get_running_modules()
            module_running = "MEV/Frontrunning" in running_modules
            
            # Arrêter le module
            stop_result, stop_message = await ui.stop_module("MEV/Frontrunning")
            
            # Met à jour les résultats
            elapsed_time = time.time() - start_time
            self.results["unified_interface"] = {
                "success": launch_result and module_running and stop_result,
                "launched_module": launch_result,
                "stopped_module": stop_result,
                "time_elapsed": elapsed_time,
                "status": "Réussi: Module lancé et arrêté avec succès" if (launch_result and stop_result) else f"Échec: {message}, {stop_message}"
            }
            
            logger.info(f"Test d'intégration avec l'interface unifiée terminé: {self.results['unified_interface']['status']}")
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            self.results["unified_interface"] = {
                "success": False,
                "launched_module": False,
                "stopped_module": False,
                "time_elapsed": elapsed_time,
                "status": f"Erreur: {str(e)}"
            }
            logger.error(f"Erreur lors du test d'intégration avec l'interface unifiée: {str(e)}")
            
        return self.results["unified_interface"]
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """
        Exécute tous les tests.
        
        Returns:
            Résultats de tous les tests
        """
        self.start_time = time.time()
        logger.info("Démarrage de tous les tests en environnement réel...")
        
        # Exécution séquentielle des tests
        await self.test_mempool_monitoring()
        await self.test_transaction_analysis()
        await self.test_strategy_simulation()
        await self.test_gas_optimization()
        await self.test_unified_interface()
        
        # Calcul du résultat global
        total_success = sum([1 for test, result in self.results.items() if result["success"]])
        success_rate = total_success / len(self.results) * 100
        
        total_time = time.time() - self.start_time
        
        overall_result = {
            "success_rate": success_rate,
            "total_time": total_time,
            "tests_passed": total_success,
            "tests_total": len(self.results),
            "detailed_results": self.results,
            "status": "Tous les tests réussis" if success_rate == 100 else f"{total_success}/{len(self.results)} tests réussis"
        }
        
        logger.info(f"Tests terminés: {overall_result['status']} en {total_time:.2f}s")
        return overall_result
    
    def display_results(self) -> None:
        """Affiche les résultats des tests."""
        if not self.results:
            print("Aucun test n'a été exécuté.")
            return
            
        print("\n" + "="*80)
        print(f"RÉSULTATS DES TESTS MEV EN ENVIRONNEMENT RÉEL ({self.blockchain.upper()})")
        print("="*80)
        
        for test_name, result in self.results.items():
            status_color = "\033[92m" if result["success"] else "\033[91m"  # Vert si succès, rouge si échec
            print(f"\n{test_name.upper()}: {status_color}{result['status']}\033[0m")
            
            # Affiche les détails spécifiques à chaque test
            if test_name == "mempool_monitoring":
                print(f"  Transactions détectées: {result['detected_transactions']}")
                print(f"  Temps écoulé: {result['time_elapsed']:.2f}s")
                
            elif test_name == "transaction_analysis":
                print(f"  Transactions analysées: {result['analyzed_transactions']}")
                print(f"  Opportunités potentielles: {result['potential_opportunities']}")
                print(f"  Temps écoulé: {result['time_elapsed']:.2f}s")
                
            elif test_name == "strategy_simulation":
                print(f"  Transactions simulées: {result['simulated_transactions']}")
                print(f"  Profit attendu: {result['expected_profit']:.6f}")
                print(f"  Temps écoulé: {result['time_elapsed']:.2f}s")
                
            elif test_name == "gas_optimization":
                print(f"  Transactions optimisées: {result['optimized_transactions']}")
                print(f"  Économies de gas: {result['gas_savings']:.6f}")
                print(f"  Temps écoulé: {result['time_elapsed']:.2f}s")
                
            elif test_name == "unified_interface":
                print(f"  Module lancé: {result['launched_module']}")
                print(f"  Module arrêté: {result['stopped_module']}")
                if "time_elapsed" in result:
                    print(f"  Temps écoulé: {result['time_elapsed']:.2f}s")
                
        # Affiche le résumé
        if hasattr(self, 'start_time') and self.start_time:
            total_time = time.time() - self.start_time
            success_count = sum([1 for result in self.results.values() if result["success"]])
            success_rate = success_count / len(self.results) * 100
            
            print("\n" + "-"*80)
            status_color = "\033[92m" if success_rate == 100 else "\033[93m" if success_rate >= 50 else "\033[91m"
            print(f"RÉSUMÉ: {status_color}{success_count}/{len(self.results)} tests réussis ({success_rate:.1f}%)\033[0m")
            print(f"Temps total d'exécution: {total_time:.2f}s")
            print("-"*80)


async def initialize() -> bool:
    """
    Initialise les composants nécessaires pour les tests MEV.
    
    Returns:
        bool: True si l'initialisation est réussie, False sinon
    """
    try:
        logger.info("Initialisation des composants pour les tests MEV...")
        
        # Initialiser le gestionnaire RPC
        await rpc_manager.start()
        
        return True
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation: {str(e)}")
        return False

async def test_mempool_monitoring(config: Dict[str, Any]) -> bool:
    """
    Teste la surveillance du mempool.
    
    Args:
        config: Configuration du test
        
    Returns:
        bool: True si le test est réussi, False sinon
    """
    try:
        logger.info("Test de surveillance du mempool...")
        
        # Créer et initialiser la stratégie MEV
        mev_strategy = MEVStrategy(
            blockchain=config.get("blockchain", "avax"),
            config=config
        )
        
        if not await mev_strategy.initialize():
            logger.error("Échec de l'initialisation de la stratégie MEV")
            return False
        
        # Démarrer la surveillance du mempool
        if not await mev_strategy.start_mempool_monitoring():
            logger.error("Échec du démarrage de la surveillance du mempool")
            return False
        
        # Surveiller pendant la durée spécifiée
        monitoring_duration = config.get("monitoring_duration_seconds", 30)
        logger.info(f"Surveillance du mempool pendant {monitoring_duration} secondes...")
        
        start_time = time.time()
        opportunities_detected = 0
        
        while time.time() - start_time < monitoring_duration:
            # Attendre 1 seconde entre chaque vérification
            await asyncio.sleep(1)
            
            # Afficher les opportunités détectées
            if hasattr(mev_strategy, 'opportunities') and len(mev_strategy.opportunities) > opportunities_detected:
                new_opportunities = len(mev_strategy.opportunities) - opportunities_detected
                logger.info(f"Nouvelles opportunités détectées: {new_opportunities}")
                opportunities_detected = len(mev_strategy.opportunities)
        
        # Arrêter la surveillance du mempool
        await mev_strategy.stop_mempool_monitoring()
        
        logger.info(f"Test terminé. Opportunités détectées: {opportunities_detected}")
        return True
    except Exception as e:
        logger.error(f"Erreur lors du test de surveillance du mempool: {str(e)}")
        return False

async def test_transaction_analysis(config: Dict[str, Any]) -> bool:
    """
    Teste l'analyse de transactions.
    
    Args:
        config: Configuration du test
        
    Returns:
        bool: True si le test est réussi, False sinon
    """
    try:
        logger.info("Test d'analyse de transactions...")
        
        # Créer et initialiser la stratégie MEV
        mev_strategy = MEVStrategy(
            blockchain=config.get("blockchain", "avax"),
            config=config
        )
        
        if not await mev_strategy.initialize():
            logger.error("Échec de l'initialisation de la stratégie MEV")
            return False
        
        # Créer des transactions de test
        test_transactions = [
            {
                "hash": f"0x{i:064x}",
                "from": f"0x{i+1:040x}",
                "to": f"0x{i+2:040x}",
                "value": (i+1) * 10**18,
                "gas": 21000 + i * 1000,
                "gasPrice": (50 + i) * 10**9,
                "input": f"0x{i+3:0100x}"
            }
            for i in range(5)
        ]
        
        # Analyser les transactions
        results = []
        for tx in test_transactions:
            is_opportunity = await mev_strategy.analyze_transaction(tx)
            results.append(is_opportunity)
            logger.info(f"Transaction {tx['hash'][:10]}...: {'Opportunité détectée' if is_opportunity else 'Pas d\\'opportunité'}")
        
        logger.info(f"Test terminé. Opportunités détectées: {sum(results)}/{len(results)}")
        return True
    except Exception as e:
        logger.error(f"Erreur lors du test d'analyse de transactions: {str(e)}")
        return False

async def test_gas_optimization(config: Dict[str, Any]) -> bool:
    """
    Teste l'optimisation du gas.
    
    Args:
        config: Configuration du test
        
    Returns:
        bool: True si le test est réussi, False sinon
    """
    try:
        logger.info("Test d'optimisation du gas...")
        
        # Créer et initialiser la stratégie MEV
        mev_strategy = MEVStrategy(
            blockchain=config.get("blockchain", "avax"),
            config=config
        )
        
        if not await mev_strategy.initialize():
            logger.error("Échec de l'initialisation de la stratégie MEV")
            return False
        
        # Créer des transactions de test
        test_transactions = [
            {
                "hash": f"0x{i:064x}",
                "gas_price": (50 + i * 10) * 10**9,
                "gas_limit": 21000 + i * 5000
            }
            for i in range(5)
        ]
        
        # Optimiser le gas pour chaque transaction
        total_savings = 0.0
        for i, tx in enumerate(test_transactions):
            result = await mev_strategy.optimize_gas(tx)
            
            if result.get("success", False):
                original_gas = result.get("original_gas_price", 0)
                optimized_gas = result.get("optimized_gas_price", 0)
                savings_percentage = result.get("savings_percentage", 0.0)
                
                logger.info(f"Transaction {i+1}: Gas original: {original_gas/10**9:.2f} Gwei, "
                           f"Gas optimisé: {optimized_gas/10**9:.2f} Gwei, "
                           f"Économie: {savings_percentage:.2f}%")
                
                total_savings += savings_percentage
            else:
                logger.warning(f"Échec de l'optimisation du gas pour la transaction {i+1}: {result.get('reason', 'Raison inconnue')}")
        
        average_savings = total_savings / len(test_transactions) if test_transactions else 0
        logger.info(f"Test terminé. Économie moyenne de gas: {average_savings:.2f}%")
        return True
    except Exception as e:
        logger.error(f"Erreur lors du test d'optimisation du gas: {str(e)}")
        return False

async def main():
    """Fonction principale pour exécuter les tests."""
    parser = argparse.ArgumentParser(description="Tests en environnement réel pour le module MEV/Frontrunning")
    parser.add_argument("--config", type=str, required=True, help="Chemin vers le fichier de configuration JSON")
    parser.add_argument("--test", type=str, default="all", choices=["all", "mempool", "analysis", "gas"], 
                        help="Test spécifique à exécuter (all, mempool, analysis, gas)")
    
    args = parser.parse_args()
    
    # Charger la configuration
    try:
        with open(args.config, 'r') as f:
            config = json.load(f)
    except Exception as e:
        logger.error(f"Erreur lors du chargement de la configuration: {str(e)}")
        return
    
    # Initialiser les composants
    if not await initialize():
        logger.error("Échec de l'initialisation. Arrêt des tests.")
        return
    
    # Exécuter les tests
    tests = {
        "mempool": test_mempool_monitoring,
        "analysis": test_transaction_analysis,
        "gas": test_gas_optimization
    }
    
    if args.test == "all":
        # Exécuter tous les tests
        for name, test_func in tests.items():
            logger.info(f"=== Test: {name} ===")
            await test_func(config)
            logger.info("=" * 40)
    else:
        # Exécuter le test spécifique
        if args.test in tests:
            await tests[args.test](config)
        else:
            logger.error(f"Test inconnu: {args.test}")


if __name__ == "__main__":
    # S'assurer d'utiliser asyncio.run pour gérer correctement la boucle d'événements
    asyncio.run(main()) 