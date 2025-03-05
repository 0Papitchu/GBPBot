#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script de test complet pour vérifier que tous les composants de GBPBot
fonctionnent correctement ensemble avant le déploiement en production.
"""

import os
import sys
import time
import json
import asyncio
from dotenv import load_dotenv
from loguru import logger
import requests
import subprocess
import signal
import threading
from web3 import Web3

# Import des modules GBPBot
from mempool_sniping import MempoolSniping
from gas_optimizer import GasOptimizer
from bundle_checker import BundleChecker
from security_config import SecurityConfig

# Charger les variables d'environnement
load_dotenv()

# Configurer le logger
logger.remove()
logger.add(sys.stderr, level="INFO")
logger.add("production_test.log", rotation="10 MB", level="DEBUG")

class ProductionTest:
    """Classe pour tester tous les composants de GBPBot avant la production."""
    
    def __init__(self):
        """Initialiser le testeur de production."""
        self.web3_provider = os.getenv("WEB3_PROVIDER_URL")
        self.api_url = os.getenv("GBPBOT_API_URL", "http://127.0.0.1:5000")
        self.dashboard_url = os.getenv("GBPBOT_DASHBOARD_URL", "http://127.0.0.1:5001")
        self.api_key = os.getenv("GBPBOT_API_KEY", "your_secure_api_key_here")
        
        # Résultats des tests
        self.test_results = {
            "web3_connection": False,
            "mempool_sniping": False,
            "gas_optimizer": False,
            "bundle_checker": False,
            "api_server": False,
            "dashboard": False,
            "security": False,
            "integration": False
        }
        
        # Processus des serveurs
        self.server_processes = []
        
    async def run_all_tests(self):
        """Exécuter tous les tests de production."""
        logger.info("Démarrage des tests de production...")
        
        try:
            # Test de connexion Web3
            await self.test_web3_connection()
            
            # Test des modules individuels
            await self.test_mempool_sniping()
            await self.test_gas_optimizer()
            await self.test_bundle_checker()
            
            # Test des serveurs
            await self.test_servers()
            
            # Test de sécurité
            await self.test_security()
            
            # Test d'intégration
            await self.test_integration()
            
            # Afficher le résumé
            self.print_summary()
            
        except Exception as e:
            logger.error(f"Erreur lors des tests: {str(e)}")
        finally:
            # Arrêter les serveurs si nécessaire
            self.stop_servers()
    
    async def test_web3_connection(self):
        """Tester la connexion Web3."""
        logger.info("Test de connexion Web3...")
        
        try:
            web3 = Web3(Web3.HTTPProvider(self.web3_provider))
            if web3.is_connected():
                logger.success("Connexion Web3 établie avec succès")
                self.test_results["web3_connection"] = True
            else:
                logger.error("Impossible de se connecter au fournisseur Web3")
        except Exception as e:
            logger.error(f"Erreur de connexion Web3: {str(e)}")
    
    async def test_mempool_sniping(self):
        """Tester le module de sniping mempool."""
        logger.info("Test du module de sniping mempool...")
        
        try:
            mempool_sniping = MempoolSniping(
                web3_provider=self.web3_provider,
                min_liquidity=0.1,
                max_buy_amount=0.01,
                gas_boost_percentage=5
            )
            
            # Vérifier que l'objet est correctement initialisé
            if mempool_sniping.web3 and mempool_sniping.web3.is_connected():
                logger.success("Module de sniping mempool initialisé avec succès")
                self.test_results["mempool_sniping"] = True
            else:
                logger.error("Échec de l'initialisation du module de sniping mempool")
        except Exception as e:
            logger.error(f"Erreur lors du test du module de sniping mempool: {str(e)}")
    
    async def test_gas_optimizer(self):
        """Tester le module d'optimisation du gas."""
        logger.info("Test du module d'optimisation du gas...")
        
        try:
            gas_optimizer = GasOptimizer(
                web3_provider=self.web3_provider,
                max_gas_price=100.0,
                min_gas_price=1.0,
                gas_price_strategy="standard"
            )
            
            # Obtenir le prix du gas
            gas_price = gas_optimizer.get_gas_price()
            
            if gas_price > 0:
                logger.success(f"Module d'optimisation du gas initialisé avec succès (prix actuel: {gas_price} gwei)")
                self.test_results["gas_optimizer"] = True
            else:
                logger.error("Échec de l'initialisation du module d'optimisation du gas")
        except Exception as e:
            logger.error(f"Erreur lors du test du module d'optimisation du gas: {str(e)}")
    
    async def test_bundle_checker(self):
        """Tester le module de détection des bundles."""
        logger.info("Test du module de détection des bundles...")
        
        try:
            bundle_checker = BundleChecker(
                web3_provider=self.web3_provider,
                bundle_threshold=3,
                time_window=60
            )
            
            # Vérifier que l'objet est correctement initialisé
            if bundle_checker.web3 and bundle_checker.web3.is_connected():
                logger.success("Module de détection des bundles initialisé avec succès")
                self.test_results["bundle_checker"] = True
            else:
                logger.error("Échec de l'initialisation du module de détection des bundles")
        except Exception as e:
            logger.error(f"Erreur lors du test du module de détection des bundles: {str(e)}")
    
    async def test_servers(self):
        """Tester les serveurs API et dashboard."""
        logger.info("Test des serveurs API et dashboard...")
        
        try:
            # Démarrer les serveurs
            self.start_servers()
            
            # Attendre que les serveurs démarrent
            await asyncio.sleep(5)
            
            # Tester l'API
            try:
                response = requests.get(f"{self.api_url}/health", 
                                       headers={"x-api-key": self.api_key},
                                       timeout=5)
                if response.status_code == 200:
                    logger.success("Serveur API démarré avec succès")
                    self.test_results["api_server"] = True
                else:
                    logger.error(f"Échec du test du serveur API: {response.status_code}")
            except Exception as e:
                logger.error(f"Erreur lors du test du serveur API: {str(e)}")
            
            # Tester le dashboard
            try:
                response = requests.get(f"{self.dashboard_url}/", timeout=5)
                if response.status_code == 200:
                    logger.success("Serveur dashboard démarré avec succès")
                    self.test_results["dashboard"] = True
                else:
                    logger.error(f"Échec du test du serveur dashboard: {response.status_code}")
            except Exception as e:
                logger.error(f"Erreur lors du test du serveur dashboard: {str(e)}")
                
        except Exception as e:
            logger.error(f"Erreur lors du test des serveurs: {str(e)}")
    
    def start_servers(self):
        """Démarrer les serveurs API et dashboard."""
        logger.info("Démarrage des serveurs...")
        
        # Chemin vers l'interpréteur Python actuel
        python_executable = sys.executable
        
        # Chemin du répertoire courant
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Commandes pour démarrer les serveurs
        api_command = [python_executable, os.path.join(current_dir, "api_server.py")]
        dashboard_command = [python_executable, os.path.join(current_dir, "web_dashboard.py")]
        
        # Démarrer le serveur API
        api_process = subprocess.Popen(api_command, 
                                      stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE,
                                      text=True)
        self.server_processes.append(api_process)
        
        # Attendre un peu pour s'assurer que l'API démarre avant le dashboard
        time.sleep(2)
        
        # Démarrer le serveur dashboard
        dashboard_process = subprocess.Popen(dashboard_command,
                                           stdout=subprocess.PIPE,
                                           stderr=subprocess.PIPE,
                                           text=True)
        self.server_processes.append(dashboard_process)
    
    def stop_servers(self):
        """Arrêter les serveurs API et dashboard."""
        logger.info("Arrêt des serveurs...")
        
        for process in self.server_processes:
            try:
                process.terminate()
                process.wait(timeout=5)
            except Exception as e:
                logger.error(f"Erreur lors de l'arrêt d'un serveur: {str(e)}")
    
    async def test_security(self):
        """Tester la sécurité."""
        logger.info("Test de sécurité...")
        
        try:
            # Tester l'authentification API
            response = requests.get(f"{self.api_url}/status", timeout=5)
            if response.status_code == 401:
                logger.success("Authentification API fonctionnelle")
                
                # Tester avec une clé API valide
                response = requests.get(f"{self.api_url}/status", 
                                       headers={"x-api-key": self.api_key},
                                       timeout=5)
                if response.status_code == 200:
                    logger.success("Authentification avec clé API valide fonctionnelle")
                    self.test_results["security"] = True
                else:
                    logger.error("Échec de l'authentification avec clé API valide")
            else:
                logger.error("L'authentification API ne fonctionne pas correctement")
        except Exception as e:
            logger.error(f"Erreur lors du test de sécurité: {str(e)}")
    
    async def test_integration(self):
        """Tester l'intégration des différents modules."""
        logger.info("Test d'intégration...")
        
        try:
            # Vérifier que tous les modules fonctionnent ensemble
            if (self.test_results["web3_connection"] and
                self.test_results["mempool_sniping"] and
                self.test_results["gas_optimizer"] and
                self.test_results["bundle_checker"] and
                self.test_results["api_server"] and
                self.test_results["dashboard"]):
                
                # Tester l'API pour démarrer le sniping
                response = requests.post(f"{self.api_url}/start_sniping", 
                                        headers={"x-api-key": self.api_key},
                                        json={"simulation_mode": True},
                                        timeout=5)
                
                if response.status_code == 200:
                    logger.success("Test d'intégration réussi")
                    self.test_results["integration"] = True
                else:
                    logger.error(f"Échec du test d'intégration: {response.status_code}")
            else:
                logger.error("Impossible de réaliser le test d'intégration car certains modules ont échoué")
        except Exception as e:
            logger.error(f"Erreur lors du test d'intégration: {str(e)}")
    
    def print_summary(self):
        """Afficher le résumé des tests."""
        logger.info("\n=== Résumé des tests de production ===")
        
        all_passed = True
        for test_name, result in self.test_results.items():
            status = "✅ RÉUSSI" if result else "❌ ÉCHOUÉ"
            if not result:
                all_passed = False
            logger.info(f"{test_name}: {status}")
        
        if all_passed:
            logger.success("\n🚀 Tous les tests ont réussi! Le système est prêt pour la production.")
        else:
            logger.error("\n⚠️ Certains tests ont échoué. Le système n'est pas prêt pour la production.")

async def main():
    """Fonction principale."""
    tester = ProductionTest()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main()) 