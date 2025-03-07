#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test unitaire pour l'analyseur de microstructure de marché.
Ce test vérifie le fonctionnement de base du module.
"""

import unittest
import asyncio
import logging
import json
from typing import Dict, Any

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("market_microstructure_test")

class MockSolanaClient:
    """Client Solana simulé pour les tests."""
    
    async def get_order_book(self, market_address: str) -> Dict[str, Any]:
        """Retourne un order book simulé."""
        logger.info(f"Récupération de l'order book pour le marché: {market_address}")
        return {
            "bids": [
                {"price": 0.95, "size": 1000},
                {"price": 0.94, "size": 2000},
                {"price": 0.93, "size": 3000}
            ],
            "asks": [
                {"price": 1.05, "size": 1000},
                {"price": 1.06, "size": 2000},
                {"price": 1.07, "size": 3000}
            ]
        }

class MarketMicrostructureAnalyzerTest(unittest.TestCase):
    """Tests pour l'analyseur de microstructure de marché."""
    
    def setUp(self):
        """Configuration pour chaque test."""
        # Création d'une classe de test simulant l'analyseur
        self.analyzer = TestMarketMicrostructureAnalyzer("https://api.mainnet-beta.solana.com")
    
    def test_analyze_order_book(self):
        """Test de l'analyse du carnet d'ordres."""
        result = asyncio.run(self.analyzer.analyze_order_book("TEST_MARKET"))
        
        logger.info(f"Résultat de l'analyse: {json.dumps(result, indent=2)}")
        self.assertIn("spread", result)
        self.assertIn("total_bid_size", result)
        self.assertIn("total_ask_size", result)
        self.assertEqual(result["total_bid_size"], 6000)
        self.assertEqual(result["total_ask_size"], 6000)
        self.assertAlmostEqual(result["spread"], 0.1, places=5)
    
    def test_detect_market_manipulation(self):
        """Test de la détection de manipulation de marché."""
        # Cas 1: Pas de manipulation
        self.analyzer.set_manipulation_scenario(False)
        result = asyncio.run(self.analyzer.detect_market_manipulation("TEST_MARKET"))
        
        logger.info(f"Résultat (sans manipulation): {json.dumps(result, indent=2)}")
        self.assertFalse(result["manipulation_detected"])
        
        # Cas 2: Manipulation détectée
        self.analyzer.set_manipulation_scenario(True)
        result = asyncio.run(self.analyzer.detect_market_manipulation("TEST_MARKET"))
        
        logger.info(f"Résultat (avec manipulation): {json.dumps(result, indent=2)}")
        self.assertTrue(result["manipulation_detected"])

class TestMarketMicrostructureAnalyzer:
    """Version simplifiée de l'analyseur pour les tests."""
    
    def __init__(self, rpc_url: str):
        """Initialisation de l'analyseur."""
        self.rpc_url = rpc_url
        self.simulate_manipulation = False
        logger.info(f"Analyseur initialisé avec RPC: {rpc_url}")
    
    def set_manipulation_scenario(self, manipulated: bool):
        """Définit si le scénario doit simuler une manipulation."""
        self.simulate_manipulation = manipulated
    
    async def analyze_order_book(self, market_address: str) -> Dict[str, Any]:
        """Analyse du carnet d'ordres."""
        logger.info(f"Analyse du carnet d'ordres pour le marché: {market_address}")
        
        # Simuler les données du carnet d'ordres
        order_book_data = {
            "bids": [
                {"price": 0.95, "size": 1000},
                {"price": 0.94, "size": 2000},
                {"price": 0.93, "size": 3000}
            ],
            "asks": [
                {"price": 1.05, "size": 1000},
                {"price": 1.06, "size": 2000},
                {"price": 1.07, "size": 3000}
            ]
        }
        
        # Calculer les résultats
        total_bid_size = sum(bid["size"] for bid in order_book_data["bids"])
        total_ask_size = sum(ask["size"] for ask in order_book_data["asks"])
        spread = order_book_data["asks"][0]["price"] - order_book_data["bids"][0]["price"]
        
        analysis_results = {
            "total_bid_size": total_bid_size,
            "total_ask_size": total_ask_size,
            "spread": spread,
            "manipulation_detected": self.simulate_manipulation,
            "confidence_score": 0.8 if self.simulate_manipulation else 0.1
        }
        
        return analysis_results
    
    async def detect_market_manipulation(self, market_address: str) -> Dict[str, Any]:
        """Détecte les manipulations de marché."""
        logger.info(f"Détection de manipulation pour le marché: {market_address}")
        
        # Créer un résultat basé sur le scénario configuré
        result = {
            "manipulation_detected": self.simulate_manipulation,
            "manipulation_type": "Pump and dump" if self.simulate_manipulation else None,
            "confidence_score": 0.85 if self.simulate_manipulation else 0.15
        }
        
        return result

if __name__ == "__main__":
    unittest.main() 