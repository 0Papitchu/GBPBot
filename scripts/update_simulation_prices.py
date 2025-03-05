#!/usr/bin/env python3
"""
Script pour mettre à jour les prix de simulation dans le client blockchain.
Ce script récupère les prix réels du marché et met à jour les valeurs simulées
dans le code source de gbpbot/core/blockchain.py.
"""

import asyncio
import re
import requests
from typing import Dict, Any
import os
import sys
import time
from datetime import datetime
from loguru import logger

# Configurer le logger
logger.remove()
logger.add(sys.stdout, level="INFO")
logger.add("update_simulation_prices.log", rotation="10 MB")

# URLs des API
COINGECKO_API = "https://api.coingecko.com/api/v3/simple/price"
BINANCE_API = "https://api.binance.com/api/v3/ticker/price"

# Chemin vers le fichier blockchain.py
BLOCKCHAIN_PY_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "gbpbot", "core", "blockchain.py"
)

async def get_coingecko_prices() -> Dict[str, float]:
    """
    Récupère les prix depuis CoinGecko.
    
    Returns:
        Dict[str, float]: Dictionnaire des prix
    """
    try:
        params = {
            "ids": "avalanche-2,ethereum,tether,usd-coin",
            "vs_currencies": "usd"
        }
        response = requests.get(COINGECKO_API, params=params)
        data = response.json()
        
        # Créer un dictionnaire des prix
        prices = {
            "AVAX/USDT": data["avalanche-2"]["usd"],
            "AVAX/USDC": data["avalanche-2"]["usd"],
            "ETH/USDT": data["ethereum"]["usd"],
            "ETH/USDC": data["ethereum"]["usd"],
            "AVAX/ETH": data["avalanche-2"]["usd"] / data["ethereum"]["usd"],
            "USDT/USDC": 1.0
        }
        
        logger.info(f"Prix récupérés depuis CoinGecko: {prices}")
        return prices
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des prix depuis CoinGecko: {str(e)}")
        return {}

async def get_binance_prices() -> Dict[str, float]:
    """
    Récupère les prix depuis Binance.
    
    Returns:
        Dict[str, float]: Dictionnaire des prix
    """
    try:
        response = requests.get(BINANCE_API)
        data = response.json()
        
        # Créer un dictionnaire pour accéder facilement aux prix
        binance_prices = {}
        for item in data:
            binance_prices[item["symbol"]] = float(item["price"])
        
        # Créer un dictionnaire des prix
        prices = {
            "AVAX/USDT": binance_prices.get("AVAXUSDT", 0),
            "AVAX/USDC": binance_prices.get("AVAXUSDC", binance_prices.get("AVAXUSDT", 0)),
            "ETH/USDT": binance_prices.get("ETHUSDT", 0),
            "ETH/USDC": binance_prices.get("ETHUSDC", binance_prices.get("ETHUSDT", 0)),
            "AVAX/ETH": binance_prices.get("AVAXETH", 0) or (
                binance_prices.get("AVAXUSDT", 0) / binance_prices.get("ETHUSDT", 1) if
                binance_prices.get("ETHUSDT", 0) > 0 else 0
            ),
            "USDT/USDC": 1.0
        }
        
        logger.info(f"Prix récupérés depuis Binance: {prices}")
        return prices
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des prix depuis Binance: {str(e)}")
        return {}

def update_blockchain_py(prices: Dict[str, float]) -> bool:
    """
    Met à jour les prix dans le fichier blockchain.py.
    
    Args:
        prices: Dictionnaire des prix à mettre à jour
        
    Returns:
        bool: True si la mise à jour a réussi, False sinon
    """
    try:
        # Lire le contenu du fichier
        with open(BLOCKCHAIN_PY_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Mettre à jour les prix DEX
        content = re.sub(
            r'base_price = 34\.75\s+# Prix AVAX/USDT mis à jour',
            f'base_price = {prices["AVAX/USDT"]:.2f}  # Prix AVAX/USDT mis à jour',
            content
        )
        content = re.sub(
            r'base_price = 34\.75\s+# Prix AVAX/USDC mis à jour',
            f'base_price = {prices["AVAX/USDC"]:.2f}  # Prix AVAX/USDC mis à jour',
            content
        )
        content = re.sub(
            r'base_price = 0\.0195\s+# Prix AVAX/ETH mis à jour',
            f'base_price = {prices["AVAX/ETH"]:.6f}  # Prix AVAX/ETH mis à jour',
            content
        )
        
        # Mettre à jour pour les conversions inverses
        content = re.sub(
            r'base_price = 1/34\.75\s+# 1 USDT = 1/34\.75 AVAX',
            f'base_price = 1/{prices["AVAX/USDT"]:.2f}  # 1 USDT = 1/{prices["AVAX/USDT"]:.2f} AVAX',
            content
        )
        content = re.sub(
            r'base_price = 0\.000562\s+# 1 USDT = 0\.000562 ETH',
            f'base_price = {1/prices["ETH/USDT"]:.6f}  # 1 USDT = {1/prices["ETH/USDT"]:.6f} ETH',
            content
        )
        
        # Mettre à jour les prix CEX
        content = re.sub(
            r'base_price = 34\.85\s+# Prix AVAX/USDT mis à jour',
            f'base_price = {prices["AVAX/USDT"]:.2f}  # Prix AVAX/USDT mis à jour',
            content
        )
        content = re.sub(
            r'base_price = 34\.85\s+# Prix AVAX/USDC mis à jour',
            f'base_price = {prices["AVAX/USDC"]:.2f}  # Prix AVAX/USDC mis à jour',
            content
        )
        content = re.sub(
            r'base_price = 1785\.0\s+# Prix ETH/USDT mis à jour',
            f'base_price = {prices["ETH/USDT"]:.2f}  # Prix ETH/USDT mis à jour',
            content
        )
        content = re.sub(
            r'base_price = 1785\.0\s+# Prix ETH/USDC mis à jour',
            f'base_price = {prices["ETH/USDC"]:.2f}  # Prix ETH/USDC mis à jour',
            content
        )
        content = re.sub(
            r'base_price = 0\.0195\s+# Prix AVAX/ETH mis à jour',
            f'base_price = {prices["AVAX/ETH"]:.6f}  # Prix AVAX/ETH mis à jour',
            content
        )
        
        # Écrire le contenu mis à jour
        with open(BLOCKCHAIN_PY_PATH, "w", encoding="utf-8") as f:
            f.write(content)
            
        logger.success(f"Mise à jour des prix dans {BLOCKCHAIN_PY_PATH} réussie")
        return True
        
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour des prix dans {BLOCKCHAIN_PY_PATH}: {str(e)}")
        return False

async def main():
    """Fonction principale"""
    logger.info("Démarrage de la mise à jour des prix de simulation...")
    
    # Récupérer les prix
    coingecko_prices = await get_coingecko_prices()
    binance_prices = await get_binance_prices()
    
    # Utiliser les prix de Binance s'ils sont disponibles, sinon CoinGecko
    prices = {}
    for key in coingecko_prices:
        if key in binance_prices and binance_prices[key] > 0:
            prices[key] = binance_prices[key]
        else:
            prices[key] = coingecko_prices[key]
    
    # Si aucun prix n'est disponible, quitter
    if not prices:
        logger.error("Aucun prix disponible, abandon de la mise à jour")
        return
    
    # Mettre à jour le fichier blockchain.py
    success = update_blockchain_py(prices)
    
    if success:
        logger.info(f"Mise à jour des prix terminée avec succès le {datetime.now().strftime('%Y-%m-%d à %H:%M:%S')}")
    else:
        logger.error("Échec de la mise à jour des prix")

if __name__ == "__main__":
    asyncio.run(main()) 