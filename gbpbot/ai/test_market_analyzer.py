#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de test pour l'analyseur de marché basé sur l'IA
======================================================

Ce script démontre l'utilisation de l'analyseur de marché en utilisant
des données factices pour simuler une analyse de marché.
"""

import os
import json
import logging
import sys
from typing import Dict, Any

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

# Ajouter le répertoire parent au path pour l'importation
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(parent_dir)

try:
    from gbpbot.ai import create_ai_client, get_prompt_manager
    from gbpbot.ai.market_analyzer import MarketAnalyzer
except ImportError as e:
    logging.error(f"Erreur d'importation: {e}")
    logging.error("Assurez-vous que le module gbpbot.ai est correctement installé.")
    sys.exit(1)

# Données factices pour les tests
def get_mock_market_data() -> Dict[str, Any]:
    """
    Génère des données de marché factices pour les tests.
    
    Returns:
        Données de marché factices
    """
    return {
        "token": {
            "symbol": "MEME",
            "name": "MemeCoin",
            "current_price": 0.00015,
            "price_history": [
                {"timestamp": "2023-07-01T00:00:00", "price": 0.00010},
                {"timestamp": "2023-07-02T00:00:00", "price": 0.00012},
                {"timestamp": "2023-07-03T00:00:00", "price": 0.00014},
                {"timestamp": "2023-07-04T00:00:00", "price": 0.00013},
                {"timestamp": "2023-07-05T00:00:00", "price": 0.00015}
            ],
            "volume_24h": 1500000,
            "market_cap": 15000000,
            "liquidity": 750000,
            "holders": 1200,
            "social_metrics": {
                "twitter_followers": 5000,
                "telegram_members": 2500,
                "sentiment_score": 0.7
            }
        },
        "market_conditions": {
            "btc_price": 35000,
            "btc_dominance": 45.5,
            "total_market_cap": 1750000000000,
            "fear_greed_index": 65
        },
        "exchange_data": {
            "dex": "TraderJoe",
            "trading_pairs": ["MEME/AVAX", "MEME/USDT"],
            "slippage": 0.02
        }
    }

def get_mock_contract_code() -> str:
    """
    Génère un code de contrat factice pour les tests.
    
    Returns:
        Code de contrat factice
    """
    return """
    // SPDX-License-Identifier: MIT
    pragma solidity ^0.8.0;

    import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
    import "@openzeppelin/contracts/access/Ownable.sol";

    contract MemeCoin is ERC20, Ownable {
        uint256 public constant MAX_SUPPLY = 1000000000 * 10**18;
        uint256 public constant INITIAL_SUPPLY = 500000000 * 10**18;
        
        constructor() ERC20("MemeCoin", "MEME") {
            _mint(msg.sender, INITIAL_SUPPLY);
        }
        
        function mint(address to, uint256 amount) public onlyOwner {
            require(totalSupply() + amount <= MAX_SUPPLY, "Exceeds max supply");
            _mint(to, amount);
        }
    }
    """

def main():
    """
    Fonction principale pour tester l'analyseur de marché.
    """
    try:
        # Créer un client d'IA
        logging.info("Création du client d'IA...")
        ai_client = create_ai_client(provider="openai")
        
        if ai_client is None:
            logging.error("Impossible de créer le client d'IA. Vérifiez la configuration.")
            return
        
        # Créer le gestionnaire de prompts
        prompt_manager = get_prompt_manager()
        
        # Créer l'analyseur de marché
        logging.info("Initialisation de l'analyseur de marché...")
        market_analyzer = MarketAnalyzer(ai_client, prompt_manager)
        
        # Obtenir des données factices
        market_data = get_mock_market_data()
        contract_code = get_mock_contract_code()
        
        # Afficher les données pour référence
        logging.info("Données de marché factices:")
        print(json.dumps(market_data, indent=2))
        
        # Analyser les données du marché
        logging.info("Analyse des données du marché...")
        market_analysis = market_analyzer.analyze_market_data(market_data)
        
        # Afficher les résultats
        logging.info("Résultat de l'analyse du marché:")
        print(json.dumps(market_analysis, indent=2))
        
        # Détecter les patterns
        logging.info("Détection des patterns...")
        patterns = market_analyzer.detect_pattern(market_data["token"])
        
        # Afficher les patterns détectés
        logging.info("Patterns détectés:")
        print(json.dumps(patterns, indent=2))
        
        # Évaluer le score du token
        logging.info("Évaluation du score du token...")
        token_score = market_analyzer.evaluate_token_score(
            market_data["token"], 
            contract_code
        )
        
        # Afficher le score
        logging.info(f"Score du token: {token_score:.2f}")
        
        # Prédire le mouvement de prix
        logging.info("Prédiction du mouvement de prix...")
        price_prediction = market_analyzer.predict_price_movement(
            market_data["token"], 
            timeframe_hours=24
        )
        
        # Afficher la prédiction
        logging.info("Prédiction de prix:")
        print(json.dumps(price_prediction, indent=2))
        
        logging.info("Tests terminés avec succès.")
    
    except Exception as e:
        logging.error(f"Erreur lors des tests: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 