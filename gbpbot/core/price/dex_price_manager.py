#!/usr/bin/env python3
"""
Module de gestion des prix DEX pour GBPBot.
Gère la récupération et le traitement des prix des exchanges décentralisés.
"""

import asyncio
from typing import Dict, List, Optional, Tuple
from web3 import Web3
from loguru import logger

from gbpbot.core.rpc.rpc_manager import RPCManager
from gbpbot.config.config_manager import ConfigManager

class DexPriceManager:
    def __init__(self):
        self.config = ConfigManager().get_config()
        self.rpc_manager = RPCManager()
        self.prices: Dict[str, float] = {}
        self.last_update: Dict[str, float] = {}
        
    async def get_dex_price(self, token_address: str, dex_name: str) -> Optional[float]:
        """Récupère le prix d'un token sur un DEX spécifique."""
        try:
            # Obtenir le meilleur RPC disponible
            rpc_url = self.rpc_manager.get_best_rpc_url()
            if not rpc_url:
                logger.error(f"Aucun RPC disponible pour {dex_name}")
                return None
                
            # Appel au smart contract du DEX
            contract_address = self.config["dex"][dex_name]["router_address"]
            result = await self.rpc_manager.call_rpc(
                "getAmountsOut",
                [Web3.to_wei(1, 'ether'), [token_address, self.config["tokens"]["weth"]]],
                contract_address
            )
            
            if not result or len(result) != 2:
                logger.warning(f"Résultat invalide pour {token_address} sur {dex_name}")
                return None
                
            price = Web3.from_wei(result[1], 'ether')
            self.prices[f"{token_address}_{dex_name}"] = float(price)
            self.last_update[f"{token_address}_{dex_name}"] = asyncio.get_event_loop().time()
            
            return float(price)
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du prix sur {dex_name}: {str(e)}")
            return None
            
    async def get_all_dex_prices(self, token_address: str) -> Dict[str, float]:
        """Récupère les prix d'un token sur tous les DEX configurés."""
        prices = {}
        dex_list = self.config["dex"].keys()
        
        tasks = [
            self.get_dex_price(token_address, dex)
            for dex in dex_list
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for dex, price in zip(dex_list, results):
            if isinstance(price, Exception):
                logger.error(f"Erreur pour {dex}: {str(price)}")
                continue
            if price is not None:
                prices[dex] = price
                
        return prices
        
    def is_price_fresh(self, token_address: str, dex_name: str, max_age: float = 30.0) -> bool:
        """Vérifie si le prix en cache est suffisamment récent."""
        key = f"{token_address}_{dex_name}"
        if key not in self.last_update:
            return False
        current_time = asyncio.get_event_loop().time()
        return (current_time - self.last_update[key]) <= max_age 