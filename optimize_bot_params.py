#!/usr/bin/env python
"""
Script pour optimiser les paramètres du bot en fonction des conditions du marché
"""

import os
import json
import logging
import asyncio
import datetime
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any
from dotenv import load_dotenv

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("optimization_results.log"),
        logging.StreamHandler()
    ]
)

# Charger les variables d'environnement
load_dotenv()

# Paramètres à optimiser et leurs plages
PARAMETERS_TO_OPTIMIZE = {
    "ARBITRAGE_THRESHOLD": {
        "min": 0.5,
        "max": 5.0,
        "step": 0.1,
        "description": "Seuil de profit minimum pour exécuter un arbitrage (%)"
    },
    "SLEEP_TIME": {
        "min": 0.1,
        "max": 5.0,
        "step": 0.1,
        "description": "Temps d'attente entre les analyses (secondes)"
    },
    "GAS_ESTIMATION": {
        "min": 0.0005,
        "max": 0.005,
        "step": 0.0001,
        "description": "Estimation des frais de gas (ETH)"
    },
    "DEX_FEE_ESTIMATION": {
        "min": 0.001,
        "max": 0.01,
        "step": 0.0005,
        "description": "Estimation des frais DEX (%)"
    },
    "TRANSACTION_VARIANCE": {
        "min": 0.05,
        "max": 0.3,
        "step": 0.01,
        "description": "Variance des montants de transaction pour éviter la détection (%)"
    },
    "GAS_BOOST_MULTIPLIER": {
        "min": 1.0,
        "max": 2.0,
        "step": 0.05,
        "description": "Multiplicateur de boost de gas pour les transactions MEV"
    }
}

# Conditions de marché à considérer
MARKET_CONDITIONS = {
    "volatility": {
        "low": {
            "description": "Faible volatilité (< 2% par jour)",
            "ARBITRAGE_THRESHOLD": 1.0,
            "SLEEP_TIME": 2.0,
            "GAS_ESTIMATION": 0.001,
            "DEX_FEE_ESTIMATION": 0.003,
            "TRANSACTION_VARIANCE": 0.1,
            "GAS_BOOST_MULTIPLIER": 1.1
        },
        "medium": {
            "description": "Volatilité moyenne (2-5% par jour)",
            "ARBITRAGE_THRESHOLD": 1.5,
            "SLEEP_TIME": 1.0,
            "GAS_ESTIMATION": 0.0015,
            "DEX_FEE_ESTIMATION": 0.003,
            "TRANSACTION_VARIANCE": 0.15,
            "GAS_BOOST_MULTIPLIER": 1.3
        },
        "high": {
            "description": "Forte volatilité (> 5% par jour)",
            "ARBITRAGE_THRESHOLD": 2.5,
            "SLEEP_TIME": 0.5,
            "GAS_ESTIMATION": 0.002,
            "DEX_FEE_ESTIMATION": 0.003,
            "TRANSACTION_VARIANCE": 0.2,
            "GAS_BOOST_MULTIPLIER": 1.5
        }
    },
    "liquidity": {
        "low": {
            "description": "Faible liquidité (< $100k par paire)",
            "ARBITRAGE_THRESHOLD": 3.0,
            "SLEEP_TIME": 2.0,
            "GAS_ESTIMATION": 0.002,
            "DEX_FEE_ESTIMATION": 0.004,
            "TRANSACTION_VARIANCE": 0.1,
            "GAS_BOOST_MULTIPLIER": 1.2
        },
        "medium": {
            "description": "Liquidité moyenne ($100k-$1M par paire)",
            "ARBITRAGE_THRESHOLD": 1.5,
            "SLEEP_TIME": 1.0,
            "GAS_ESTIMATION": 0.0015,
            "DEX_FEE_ESTIMATION": 0.003,
            "TRANSACTION_VARIANCE": 0.15,
            "GAS_BOOST_MULTIPLIER": 1.3
        },
        "high": {
            "description": "Forte liquidité (> $1M par paire)",
            "ARBITRAGE_THRESHOLD": 0.8,
            "SLEEP_TIME": 0.5,
            "GAS_ESTIMATION": 0.001,
            "DEX_FEE_ESTIMATION": 0.002,
            "TRANSACTION_VARIANCE": 0.2,
            "GAS_BOOST_MULTIPLIER": 1.4
        }
    },
    "gas_price": {
        "low": {
            "description": "Prix du gas bas (< 30 Gwei)",
            "ARBITRAGE_THRESHOLD": 1.0,
            "SLEEP_TIME": 1.0,
            "GAS_ESTIMATION": 0.001,
            "DEX_FEE_ESTIMATION": 0.003,
            "TRANSACTION_VARIANCE": 0.15,
            "GAS_BOOST_MULTIPLIER": 1.1
        },
        "medium": {
            "description": "Prix du gas moyen (30-60 Gwei)",
            "ARBITRAGE_THRESHOLD": 1.5,
            "SLEEP_TIME": 1.0,
            "GAS_ESTIMATION": 0.0015,
            "DEX_FEE_ESTIMATION": 0.003,
            "TRANSACTION_VARIANCE": 0.15,
            "GAS_BOOST_MULTIPLIER": 1.3
        },
        "high": {
            "description": "Prix du gas élevé (> 60 Gwei)",
            "ARBITRAGE_THRESHOLD": 2.5,
            "SLEEP_TIME": 1.5,
            "GAS_ESTIMATION": 0.002,
            "DEX_FEE_ESTIMATION": 0.003,
            "TRANSACTION_VARIANCE": 0.15,
            "GAS_BOOST_MULTIPLIER": 1.5
        }
    }
}

async def analyze_market_conditions() -> Dict[str, str]:
    """
    Analyse les conditions actuelles du marché
    
    Returns:
        Dict[str, str]: Conditions du marché (volatilité, liquidité, prix du gas)
    """
    # Dans une implémentation réelle, cette fonction récupérerait les données
    # du marché à partir d'APIs ou de services externes
    
    # Pour cet exemple, nous utilisons des valeurs simulées
    # En production, remplacez par des appels API réels
    
    logging.info("Analyse des conditions du marché...")
    
    # Simulation de l'analyse du marché
    # En production, remplacez par des appels API réels
    
    # Exemple: Calculer la volatilité à partir des données historiques
    volatility_level = "medium"  # Simulé
    
    # Exemple: Évaluer la liquidité des paires de trading
    liquidity_level = "medium"  # Simulé
    
    # Exemple: Vérifier le prix actuel du gas
    gas_price_level = "medium"  # Simulé
    
    market_conditions = {
        "volatility": volatility_level,
        "liquidity": liquidity_level,
        "gas_price": gas_price_level
    }
    
    logging.info(f"Conditions du marché détectées: {market_conditions}")
    return market_conditions

def get_recommended_parameters(market_conditions: Dict[str, str]) -> Dict[str, float]:
    """
    Obtient les paramètres recommandés en fonction des conditions du marché
    
    Args:
        market_conditions: Conditions actuelles du marché
        
    Returns:
        Dict[str, float]: Paramètres recommandés
    """
    recommended_params = {}
    
    # Calculer la moyenne pondérée des paramètres recommandés pour chaque condition
    for param_name in PARAMETERS_TO_OPTIMIZE.keys():
        # Récupérer les valeurs recommandées pour chaque condition
        values = []
        for condition_type, condition_level in market_conditions.items():
            if condition_type in MARKET_CONDITIONS and condition_level in MARKET_CONDITIONS[condition_type]:
                values.append(MARKET_CONDITIONS[condition_type][condition_level].get(param_name, 0))
        
        # Calculer la moyenne
        if values:
            recommended_params[param_name] = sum(values) / len(values)
    
    return recommended_params

def update_env_file(params: Dict[str, float]) -> bool:
    """
    Met à jour le fichier .env avec les nouveaux paramètres
    
    Args:
        params: Nouveaux paramètres à appliquer
        
    Returns:
        bool: True si la mise à jour a réussi, False sinon
    """
    try:
        # Lire le fichier .env actuel
        env_path = os.path.join(os.path.dirname(__file__), ".env")
        with open(env_path, "r") as f:
            env_content = f.read()
        
        # Mettre à jour chaque paramètre
        lines = env_content.split("\n")
        updated_lines = []
        
        for line in lines:
            updated = False
            for param_name, param_value in params.items():
                if line.startswith(f"{param_name}="):
                    updated_lines.append(f"{param_name}={param_value}")
                    updated = True
                    break
            
            if not updated:
                updated_lines.append(line)
        
        # Écrire le fichier .env mis à jour
        with open(env_path, "w") as f:
            f.write("\n".join(updated_lines))
        
        logging.info(f"Fichier .env mis à jour avec succès")
        return True
        
    except Exception as e:
        logging.error(f"Erreur lors de la mise à jour du fichier .env: {str(e)}")
        return False

async def optimize_parameters():
    """
    Optimise les paramètres du bot en fonction des conditions du marché
    """
    logging.info("Démarrage de l'optimisation des paramètres...")
    
    # Analyser les conditions du marché
    market_conditions = await analyze_market_conditions()
    
    # Obtenir les paramètres recommandés
    recommended_params = get_recommended_parameters(market_conditions)
    
    # Afficher les recommandations
    logging.info("\n===== PARAMÈTRES RECOMMANDÉS =====")
    for param_name, param_value in recommended_params.items():
        param_info = PARAMETERS_TO_OPTIMIZE.get(param_name, {})
        description = param_info.get("description", "")
        logging.info(f"{param_name}: {param_value:.4f} - {description}")
    
    # Demander confirmation pour appliquer les changements
    print("\nVoulez-vous appliquer ces paramètres? (o/n): ", end="")
    response = input().lower()
    
    if response == "o" or response == "oui":
        # Mettre à jour le fichier .env
        if update_env_file(recommended_params):
            logging.info("Paramètres appliqués avec succès")
            
            # Créer un fichier de configuration alternatif
            config_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            config_filename = f"config/bot_params_{config_timestamp}.json"
            
            os.makedirs("config", exist_ok=True)
            
            with open(config_filename, "w") as f:
                json.dump({
                    "timestamp": datetime.datetime.now().isoformat(),
                    "market_conditions": market_conditions,
                    "parameters": recommended_params
                }, f, indent=2)
            
            logging.info(f"Configuration sauvegardée dans {config_filename}")
        else:
            logging.error("Échec de l'application des paramètres")
    else:
        logging.info("Optimisation annulée par l'utilisateur")

if __name__ == "__main__":
    asyncio.run(optimize_parameters()) 