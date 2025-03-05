#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests unitaires pour le système GBPBot.
Ces tests vérifient le bon fonctionnement des différentes composantes du système.
"""

import os
import sys
import time
import json
import unittest
import requests
from dotenv import load_dotenv
from simulation_data import SimulationData
import threading
import tempfile
import shutil
import pytest
from loguru import logger

# Charger les variables d'environnement
load_dotenv()

# Configurer le logger
logger.remove()
logger.add(sys.stderr, level="INFO")
logger.add("test_gbpbot.log", rotation="10 MB", level="DEBUG")

# URL de l'API pour les tests
API_URL = os.getenv("GBPBOT_API_URL", "http://127.0.0.1:5000")
API_KEY = os.getenv("GBPBOT_API_KEY", "your_secure_api_key_here")

class TestSimulationData(unittest.TestCase):
    """Tests pour la classe SimulationData."""
    
    def setUp(self):
        """Initialiser les tests."""
        # Créer un répertoire temporaire pour les tests
        self.test_dir = tempfile.mkdtemp()
        # Changer le répertoire de travail
        self.old_dir = os.getcwd()
        os.chdir(self.test_dir)
        # Créer une instance de SimulationData avec une graine fixe pour la reproductibilité
        self.sim = SimulationData(seed=42)
    
    def tearDown(self):
        """Nettoyer après les tests."""
        # Revenir au répertoire de travail initial
        os.chdir(self.old_dir)
        # Supprimer le répertoire temporaire
        shutil.rmtree(self.test_dir)
    
    def test_initial_state(self):
        """Tester l'état initial de SimulationData."""
        self.assertEqual(self.sim.opportunities_detected, 0)
        self.assertEqual(self.sim.trades_executed, 0)
        self.assertEqual(self.sim.total_profit, 0.0)
        self.assertEqual(self.sim.bot_status, "running")
        self.assertEqual(self.sim.bot_mode, "SIMULATION")
        self.assertFalse(self.sim.strategies["sniping"])
        self.assertFalse(self.sim.strategies["arbitrage"])
        self.assertFalse(self.sim.strategies["mev"])
    
    def test_simulate_tick(self):
        """Tester la simulation d'un tick."""
        # Activer une stratégie pour permettre les trades
        self.sim.toggle_strategy("sniping", True)
        
        # Simuler 100 ticks
        for _ in range(100):
            self.sim.simulate_tick()
        
        # Vérifier que des opportunités ont été détectées
        self.assertGreater(self.sim.opportunities_detected, 0)
        
        # Vérifier que des trades ont été exécutés
        self.assertGreater(self.sim.trades_executed, 0)
        
        # Vérifier que l'historique des trades a été mis à jour
        self.assertGreater(len(self.sim.trades_history), 0)
        
        # Vérifier que l'historique des performances a été mis à jour
        self.assertGreater(len(self.sim.performance_history), 0)
    
    def test_change_mode(self):
        """Tester le changement de mode."""
        # Changer en mode TEST
        result = self.sim.change_mode("TEST")
        self.assertTrue(result)
        self.assertEqual(self.sim.bot_mode, "TEST")
        
        # Changer en mode LIVE
        result = self.sim.change_mode("LIVE")
        self.assertTrue(result)
        self.assertEqual(self.sim.bot_mode, "LIVE")
        
        # Changer en mode invalide
        result = self.sim.change_mode("INVALID")
        self.assertFalse(result)
        self.assertEqual(self.sim.bot_mode, "LIVE")  # Le mode ne change pas
    
    def test_toggle_strategy(self):
        """Tester l'activation/désactivation des stratégies."""
        # Activer la stratégie de sniping
        result = self.sim.toggle_strategy("sniping", True)
        self.assertTrue(result)
        self.assertTrue(self.sim.strategies["sniping"])
        
        # Désactiver la stratégie de sniping
        result = self.sim.toggle_strategy("sniping", False)
        self.assertTrue(result)
        self.assertFalse(self.sim.strategies["sniping"])
        
        # Activer une stratégie invalide
        result = self.sim.toggle_strategy("invalid_strategy", True)
        self.assertFalse(result)
    
    def test_stop_start_bot(self):
        """Tester l'arrêt et le démarrage du bot."""
        # Arrêter le bot
        result = self.sim.stop_bot()
        self.assertTrue(result)
        self.assertEqual(self.sim.bot_status, "stopped")
        
        # Essayer d'arrêter le bot à nouveau
        result = self.sim.stop_bot()
        self.assertFalse(result)  # Déjà arrêté
        
        # Démarrer le bot
        result = self.sim.start_bot()
        self.assertTrue(result)
        self.assertEqual(self.sim.bot_status, "running")
        
        # Essayer de démarrer le bot à nouveau
        result = self.sim.start_bot()
        self.assertFalse(result)  # Déjà démarré
    
    def test_reset_bot(self):
        """Tester la réinitialisation du bot."""
        # Activer une stratégie et simuler quelques ticks
        self.sim.toggle_strategy("sniping", True)
        for _ in range(10):
            self.sim.simulate_tick()
        
        # Vérifier que des données ont été générées
        self.assertGreater(self.sim.opportunities_detected, 0)
        self.assertGreater(self.sim.trades_executed, 0)
        
        # Réinitialiser le bot
        result = self.sim.reset_bot()
        self.assertTrue(result)
        
        # Vérifier que les statistiques ont été réinitialisées
        self.assertEqual(self.sim.opportunities_detected, 0)
        self.assertEqual(self.sim.trades_executed, 0)
        self.assertEqual(self.sim.total_profit, 0.0)
        self.assertEqual(len(self.sim.trades_history), 0)
        self.assertEqual(len(self.sim.performance_history), 0)
    
    def test_get_runtime(self):
        """Tester l'obtention du temps d'exécution."""
        # Le temps d'exécution doit être positif
        self.assertGreaterEqual(self.sim.get_runtime(), 0)
        
        # Arrêter le bot et vérifier que le temps d'exécution est 0
        self.sim.stop_bot()
        self.assertEqual(self.sim.get_runtime(), 0)
    
    def test_get_runtime_formatted(self):
        """Tester l'obtention du temps d'exécution formaté."""
        # Le format doit être HH:MM:SS
        runtime = self.sim.get_runtime_formatted()
        self.assertRegex(runtime, r"^\d{2}:\d{2}:\d{2}$")

@pytest.mark.skipif(not os.path.exists(".env"), reason="Fichier .env non trouvé")
class TestAPIIntegration(unittest.TestCase):
    """Tests d'intégration pour l'API GBPBot."""
    
    @classmethod
    def setUpClass(cls):
        """Initialiser les tests d'intégration."""
        # Vérifier si l'API est accessible
        try:
            response = requests.get(f"{API_URL}/health", timeout=5)
            if response.status_code != 200:
                raise Exception(f"L'API n'est pas accessible: {response.status_code}")
        except requests.RequestException as e:
            raise Exception(f"Impossible de se connecter à l'API: {e}")
    
    def test_api_status(self):
        """Tester l'endpoint /status."""
        headers = {"x-api-key": API_KEY}
        response = requests.get(f"{API_URL}/status", headers=headers, timeout=5)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("status", data)
        self.assertIn("mode", data)
        self.assertIn("runtime", data)
        self.assertIn("opportunities_detected", data)
        self.assertIn("trades_executed", data)
        self.assertIn("total_profit", data)
    
    def test_api_trades(self):
        """Tester l'endpoint /trades."""
        headers = {"x-api-key": API_KEY}
        response = requests.get(f"{API_URL}/trades", headers=headers, timeout=5)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("trades", data)
        self.assertIsInstance(data["trades"], list)
    
    def test_api_performance(self):
        """Tester l'endpoint /performance."""
        headers = {"x-api-key": API_KEY}
        response = requests.get(f"{API_URL}/performance", headers=headers, timeout=5)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("performance", data)
        self.assertIsInstance(data["performance"], list)
    
    def test_api_change_mode(self):
        """Tester l'endpoint /change_mode."""
        headers = {"x-api-key": API_KEY, "Content-Type": "application/json"}
        
        # Changer en mode TEST
        response = requests.post(f"{API_URL}/change_mode", headers=headers, json={"mode": "TEST"}, timeout=5)
        self.assertEqual(response.status_code, 200)
        
        # Vérifier que le mode a changé
        response = requests.get(f"{API_URL}/status", headers=headers, timeout=5)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["mode"], "TEST")
        
        # Essayer un mode invalide
        response = requests.post(f"{API_URL}/change_mode", headers=headers, json={"mode": "INVALID"}, timeout=5)
        self.assertEqual(response.status_code, 400)
        
        # Revenir en mode SIMULATION
        response = requests.post(f"{API_URL}/change_mode", headers=headers, json={"mode": "SIMULATION"}, timeout=5)
        self.assertEqual(response.status_code, 200)
    
    def test_api_strategies(self):
        """Tester les endpoints des stratégies."""
        headers = {"x-api-key": API_KEY}
        
        # Activer la stratégie de sniping
        response = requests.post(f"{API_URL}/start_sniping", headers=headers, timeout=5)
        self.assertEqual(response.status_code, 200)
        
        # Vérifier que la stratégie est activée
        response = requests.get(f"{API_URL}/status", headers=headers, timeout=5)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["sniping"])
        
        # Désactiver la stratégie de sniping
        response = requests.post(f"{API_URL}/stop_sniping", headers=headers, timeout=5)
        self.assertEqual(response.status_code, 200)
        
        # Vérifier que la stratégie est désactivée
        response = requests.get(f"{API_URL}/status", headers=headers, timeout=5)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["sniping"])
    
    def test_api_bot_control(self):
        """Tester les endpoints de contrôle du bot."""
        headers = {"x-api-key": API_KEY}
        
        # Arrêter le bot
        response = requests.post(f"{API_URL}/stop_bot", headers=headers, timeout=5)
        self.assertEqual(response.status_code, 200)
        
        # Vérifier que le bot est arrêté
        response = requests.get(f"{API_URL}/status", headers=headers, timeout=5)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "stopped")
        
        # Démarrer le bot
        response = requests.post(f"{API_URL}/start_bot", headers=headers, timeout=5)
        self.assertEqual(response.status_code, 200)
        
        # Vérifier que le bot est démarré
        response = requests.get(f"{API_URL}/status", headers=headers, timeout=5)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "running")
    
    def test_api_reset(self):
        """Tester l'endpoint /reset_bot."""
        headers = {"x-api-key": API_KEY}
        
        # Réinitialiser le bot
        response = requests.post(f"{API_URL}/reset_bot", headers=headers, timeout=5)
        self.assertEqual(response.status_code, 200)
        
        # Vérifier que les statistiques ont été réinitialisées
        response = requests.get(f"{API_URL}/status", headers=headers, timeout=5)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["opportunities_detected"], 0)
        self.assertEqual(data["trades_executed"], 0)
        self.assertEqual(data["total_profit"], 0)

if __name__ == "__main__":
    unittest.main() 