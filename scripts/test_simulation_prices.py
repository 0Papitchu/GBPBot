#!/usr/bin/env python3
"""
Script de test pour vérifier la cohérence des prix simulés.
Compare les prix simulés avec les prix réels du marché pour s'assurer qu'ils sont réalistes.
"""

import asyncio
import sys
import os
import time
from typing import Dict, Any
from loguru import logger
import requests
import pandas as pd
from tabulate import tabulate

# Ajouter le répertoire parent au chemin de recherche
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gbpbot.core.blockchain import BlockchainClient
from web3 import Web3
from scripts.update_simulation_prices import get_coingecko_prices, get_binance_prices

# Configurer le logger
logger.remove()
logger.add(sys.stdout, level="INFO")
logger.add("test_simulation_prices.log", rotation="10 MB")

class SimulationPriceTester:
    """
    Classe pour tester la cohérence des prix simulés.
    """
    
    def __init__(self):
        """Initialise le testeur de prix simulés."""
        self.blockchain = BlockchainClient(simulation_mode=True)
        self.real_prices = {}
        self.simulated_prices = {}
        
    async def get_real_prices(self) -> Dict[str, float]:
        """
        Récupère les prix réels du marché.
        
        Returns:
            Dict[str, float]: Dictionnaire des prix réels
        """
        coingecko_prices = await get_coingecko_prices()
        binance_prices = await get_binance_prices()
        
        # Combiner les prix en privilégiant Binance
        prices = {}
        for key in coingecko_prices:
            if key in binance_prices and binance_prices[key] > 0:
                prices[key] = binance_prices[key]
            else:
                prices[key] = coingecko_prices[key]
                
        return prices
        
    async def get_simulated_prices(self) -> Dict[str, float]:
        """
        Récupère les prix simulés du BlockchainClient.
        
        Returns:
            Dict[str, float]: Dictionnaire des prix simulés
        """
        try:
            prices = {}
            
            # Récupérer les adresses des tokens
            wavax_address = self.blockchain.token_addresses["WAVAX"]
            usdt_address = self.blockchain.token_addresses["USDT"]
            usdc_address = self.blockchain.token_addresses["USDC"]
            weth_address = self.blockchain.token_addresses["WETH"]
            
            # Montant d'entrée pour le test
            amount_in = Web3.to_wei(1, "ether")
            
            # Récupérer les prix DEX
            dex_exchanges = ["trader_joe", "pangolin", "sushi"]
            
            # Structure pour stocker les prix DEX par paire
            dex_prices = {
                "AVAX/USDT": [],
                "AVAX/USDC": [],
                "AVAX/ETH": []
            }
            
            # Récupérer les prix DEX
            for dex in dex_exchanges:
                # WAVAX -> USDT
                price = await self.blockchain.get_dex_price(dex, wavax_address, usdt_address, amount_in)
                dex_prices["AVAX/USDT"].append(price)
                
                # WAVAX -> USDC
                price = await self.blockchain.get_dex_price(dex, wavax_address, usdc_address, amount_in)
                dex_prices["AVAX/USDC"].append(price)
                
                # WAVAX -> WETH
                price = await self.blockchain.get_dex_price(dex, wavax_address, weth_address, amount_in)
                dex_prices["AVAX/ETH"].append(price)
            
            # Calculer les moyennes des prix DEX
            for pair, pair_prices in dex_prices.items():
                prices[f"DEX_{pair}"] = sum(pair_prices) / len(pair_prices)
            
            # Récupérer les prix CEX
            cex_exchanges = ["binance", "kucoin", "gate"]
            
            # Structure pour stocker les prix CEX par paire
            cex_prices = {
                "AVAX/USDT": [],
                "AVAX/USDC": [],
                "ETH/USDT": []
            }
            
            # Récupérer les prix CEX
            for cex in cex_exchanges:
                # AVAX/USDT
                price = await self.blockchain.get_cex_price(cex, "AVAX/USDT")
                cex_prices["AVAX/USDT"].append(price)
                
                # AVAX/USDC
                price = await self.blockchain.get_cex_price(cex, "AVAX/USDC")
                cex_prices["AVAX/USDC"].append(price)
                
                # ETH/USDT
                price = await self.blockchain.get_cex_price(cex, "ETH/USDT")
                cex_prices["ETH/USDT"].append(price)
            
            # Calculer les moyennes des prix CEX
            for pair, pair_prices in cex_prices.items():
                prices[f"CEX_{pair}"] = sum(pair_prices) / len(pair_prices)
            
            return prices
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des prix simulés: {str(e)}")
            return {}
    
    def calculate_deviations(self) -> pd.DataFrame:
        """
        Calcule les écarts entre les prix réels et simulés.
        
        Returns:
            pd.DataFrame: Tableau des écarts
        """
        results = []
        
        # Mapper les clés des prix simulés aux clés des prix réels
        key_mapping = {
            "DEX_AVAX/USDT": "AVAX/USDT",
            "DEX_AVAX/USDC": "AVAX/USDC",
            "DEX_AVAX/ETH": "AVAX/ETH",
            "CEX_AVAX/USDT": "AVAX/USDT",
            "CEX_AVAX/USDC": "AVAX/USDC",
            "CEX_ETH/USDT": "ETH/USDT"
        }
        
        for sim_key, sim_value in self.simulated_prices.items():
            real_key = key_mapping.get(sim_key)
            if real_key and real_key in self.real_prices:
                real_value = self.real_prices[real_key]
                if real_value > 0:
                    deviation_pct = ((sim_value - real_value) / real_value) * 100
                    
                    results.append({
                        "Paire": sim_key,
                        "Prix Simulé": round(sim_value, 4),
                        "Prix Réel": round(real_value, 4),
                        "Écart (%)": round(deviation_pct, 2),
                        "Acceptable": abs(deviation_pct) <= 5.0
                    })
        
        return pd.DataFrame(results)
        
    async def run(self):
        """Exécute le test des prix simulés."""
        logger.info("Démarrage du test des prix simulés...")
        
        # Récupérer les prix réels et simulés
        self.real_prices = await self.get_real_prices()
        self.simulated_prices = await self.get_simulated_prices()
        
        # Calculer les écarts
        df_results = self.calculate_deviations()
        
        # Afficher les résultats
        logger.info("\nRésultats du test des prix simulés:\n")
        print(tabulate(df_results, headers="keys", tablefmt="grid", showindex=False))
        
        # Vérifier si tous les écarts sont acceptables
        if df_results["Acceptable"].all():
            logger.success("\nTous les prix simulés sont cohérents avec les prix réels du marché.")
        else:
            logger.warning("\nCertains prix simulés présentent des écarts importants avec les prix réels du marché.")
            logger.warning("Exécutez le script 'update_simulation_prices.py' pour mettre à jour les prix simulés.")
        
async def main():
    """
    Fonction principale.
    """
    tester = SimulationPriceTester()
    await tester.run()

if __name__ == "__main__":
    asyncio.run(main()) 