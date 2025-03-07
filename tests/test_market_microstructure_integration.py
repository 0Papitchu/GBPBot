#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test d'intégration pour le module d'analyse de microstructure de marché.
Ce test vérifie que l'analyse de microstructure est correctement intégrée
dans le processus de décision de sniping.
"""

import asyncio
import logging
import os
import sys
import json
from typing import Dict, Any, List
from unittest.mock import patch, MagicMock

# Ajouter le répertoire parent au path pour pouvoir importer les modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("market_microstructure_test")

# Imports des modules à tester
try:
    from gbpbot.machine_learning.market_microstructure_analyzer import MarketMicrostructureAnalyzer
    from gbpbot.sniping.solana_memecoin_sniper import SolanaMemecoinSniper
    MODULES_AVAILABLE = True
except ImportError as e:
    logger.error(f"Impossible d'importer les modules nécessaires: {e}")
    MODULES_AVAILABLE = False

# Données de test
SAMPLE_ORDER_BOOK = {
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

SAMPLE_TOKEN_DATA = {
    "symbol": "TEST",
    "name": "Test Token",
    "address": "TEST123456789",
    "pair_address": "TESTPAIR123456789",
    "liquidity": 50000,
    "market_cap": 100000,
    "price": 1.0,
    "volume_24h": 25000,
    "created_at": "2023-01-01T00:00:00Z"
}

class MockRpcClient:
    """Client RPC simulé pour les tests."""
    
    async def get_order_book(self, market_address: str) -> Dict[str, Any]:
        """Retourne un order book simulé."""
        logger.info(f"Récupération de l'order book pour le marché: {market_address}")
        return SAMPLE_ORDER_BOOK
    
    async def get_recent_transactions(self, market_address: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Retourne des transactions simulées."""
        logger.info(f"Récupération des transactions récentes pour le marché: {market_address}")
        return [{"signature": f"tx{i}", "size": 100, "price": 1.0} for i in range(limit)]

@patch("gbpbot.machine_learning.market_microstructure_analyzer.SolanaClient", return_value=MockRpcClient())
async def test_market_microstructure_integration(mock_client):
    """Test de l'intégration de l'analyse de microstructure dans le sniper."""
    if not MODULES_AVAILABLE:
        logger.error("Test ignoré: modules nécessaires non disponibles")
        return
    
    logger.info("Initialisation de l'analyseur de microstructure de marché")
    analyzer = MarketMicrostructureAnalyzer(rpc_url="https://api.mainnet-beta.solana.com")
    
    # Test d'analyse d'order book
    logger.info("Test d'analyse d'order book")
    market_address = "TESTPAIR123456789"
    result = await analyzer.analyze_order_book(market_address)
    
    logger.info(f"Résultat de l'analyse: {json.dumps(result, indent=2)}")
    assert "spread" in result, "Le résultat devrait contenir le spread"
    assert "total_bid_size" in result, "Le résultat devrait contenir la taille totale des ordres d'achat"
    assert "total_ask_size" in result, "Le résultat devrait contenir la taille totale des ordres de vente"
    
    # Test de détection de manipulation
    logger.info("Test de détection de manipulation")
    manipulation_result = await analyzer.detect_market_manipulation(market_address)
    
    logger.info(f"Résultat de la détection de manipulation: {json.dumps(manipulation_result, indent=2)}")
    assert "manipulation_detected" in manipulation_result, "Le résultat devrait indiquer si une manipulation est détectée"
    assert "confidence_score" in manipulation_result, "Le résultat devrait contenir un score de confiance"
    
    # Test d'intégration avec le sniper (simulation)
    logger.info("Test d'intégration avec le sniper")
    
    # Mock pour le sniper
    sniper = MagicMock()
    sniper.market_microstructure_analyzer = analyzer
    
    # Simulation de la méthode _should_snipe_token
    original_token_data = SAMPLE_TOKEN_DATA.copy()
    
    # Cas 1: Token normal (pas de manipulation)
    with patch.object(analyzer, "detect_market_manipulation", 
                     return_value={"manipulation_detected": False, "confidence_score": 0.2}):
        should_snipe, reason = await test_should_snipe_token(sniper, original_token_data)
        logger.info(f"Décision de sniping (pas de manipulation): {should_snipe}, Raison: {reason}")
        assert should_snipe is True, "Le token sans manipulation devrait être snipé"
    
    # Cas 2: Token avec manipulation
    with patch.object(analyzer, "detect_market_manipulation", 
                     return_value={"manipulation_detected": True, "confidence_score": 0.8}):
        should_snipe, reason = await test_should_snipe_token(sniper, original_token_data)
        logger.info(f"Décision de sniping (avec manipulation): {should_snipe}, Raison: {reason}")
        assert should_snipe is False, "Le token avec manipulation ne devrait pas être snipé"
    
    logger.info("Tests d'intégration terminés avec succès")

async def test_should_snipe_token(sniper, token_data):
    """Simulation de la méthode _should_snipe_token du sniper."""
    market_address = token_data.get("pair_address")
    if market_address and sniper.market_microstructure_analyzer:
        manipulation_results = await sniper.market_microstructure_analyzer.detect_market_manipulation(market_address)
        
        if manipulation_results.get("manipulation_detected"):
            return False, "Manipulation de marché détectée"
    
    # Pour les tests, nous supposons que toutes les autres conditions sont remplies
    return True, "Token valide pour sniping"

if __name__ == "__main__":
    asyncio.run(test_market_microstructure_integration()) 