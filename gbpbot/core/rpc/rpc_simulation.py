#!/usr/bin/env python3
"""
Module de simulation RPC pour GBPBot.
Fournit des réponses simulées pour les appels RPC en mode simulation.
"""

import asyncio
import json
import time
from typing import Dict, List, Any, Optional
from loguru import logger
from web3 import Web3
import random
from decimal import Decimal

class SimulatedRPCProvider:
    """Fournisseur RPC simulé qui renvoie des réponses prédéfinies sans connexion réseau."""
    
    def __init__(self, endpoint_url: str, chain_id: int = 43114):
        self.endpoint_url = endpoint_url
        self.chain_id = chain_id
        self.is_connected = True
        self.block_number = 10_000_000
        self.gas_price = 30_000_000_000  # 30 Gwei
        self.timestamp = int(time.time())
        self.simulated_latency = 0.05  # 50ms de latence simulée
        logger.debug(f"Fournisseur RPC simulé initialisé: {endpoint_url}")
        
    async def make_request(self, method: str, params: List[Any] = None) -> Dict[str, Any]:
        """Simule une requête RPC et renvoie une réponse prédéfinie."""
        params = params or []
        
        # Simuler une latence réseau
        await asyncio.sleep(self.simulated_latency)
        
        # Incrémenter le numéro de bloc toutes les 2 secondes environ
        current_time = int(time.time())
        if current_time > self.timestamp:
            blocks_to_add = (current_time - self.timestamp) // 2
            self.block_number += blocks_to_add
            self.timestamp = current_time
            
            # Fluctuation aléatoire du gas price
            self.gas_price = int(self.gas_price * (1 + (random.random() - 0.5) * 0.1))
        
        # Simuler différentes méthodes RPC
        if method == "eth_blockNumber":
            return {"result": hex(self.block_number)}
        elif method == "eth_chainId":
            return {"result": hex(self.chain_id)}
        elif method == "eth_gasPrice":
            return {"result": hex(self.gas_price)}
        elif method == "eth_getBlockByNumber":
            block_number = params[0]
            return {
                "result": {
                    "number": block_number,
                    "hash": f"0x{random.getrandbits(256):064x}",
                    "parentHash": f"0x{random.getrandbits(256):064x}",
                    "timestamp": hex(self.timestamp),
                    "gasLimit": hex(15_000_000),
                    "gasUsed": hex(5_000_000),
                    "baseFeePerGas": hex(int(self.gas_price * 0.8))
                }
            }
        elif method == "eth_call":
            # Simuler différents types d'appels de contrat
            return {"result": "0x0000000000000000000000000000000000000000000000000000000000000000"}
        elif method == "eth_getBalance":
            return {"result": hex(1000000000000000000)}  # 1 AVAX
        else:
            # Pour toute autre méthode, retourner une réponse générique
            return {"result": "0x"}

class SimulatedRPCManager:
    """Gestionnaire de connexions RPC simulées."""
    
    def __init__(self):
        """Initialise le gestionnaire RPC simulé avec plusieurs endpoints."""
        self.providers = [
            SimulatedRPCProvider("https://api.avax.network/ext/bc/C/rpc"),
            SimulatedRPCProvider("https://rpc.ankr.com/avalanche"),
            SimulatedRPCProvider("https://avalanche-mainnet.infura.io")
        ]
        self.current_provider_index = 0
        logger.info("Gestionnaire RPC simulé initialisé avec 3 endpoints simulés")
        
    async def get_web3(self) -> Web3:
        """Retourne une instance Web3 configurée pour utiliser notre middleware simulé."""
        # Créer une instance Web3 qui utilisera notre provider simulé
        w3 = Web3()
        
        # Remplacer le provider par notre provider simulé
        provider = self.get_current_provider()
        w3.provider = SimulatedWeb3Provider(provider)
        
        return w3
    
    def get_current_provider(self) -> SimulatedRPCProvider:
        """Retourne le fournisseur RPC actuellement utilisé."""
        return self.providers[self.current_provider_index]
    
    def rotate_provider(self):
        """Passe au fournisseur RPC suivant."""
        self.current_provider_index = (self.current_provider_index + 1) % len(self.providers)
        logger.debug(f"Passage au fournisseur RPC suivant: {self.providers[self.current_provider_index].endpoint_url}")
        
    async def check_rpc_health(self) -> Dict[str, Any]:
        """Vérifie la santé des nœuds RPC simulés."""
        results = {
            "active_nodes": len(self.providers),
            "total_nodes": len(self.providers),
            "nodes": []
        }
        
        for provider in self.providers:
            results["nodes"].append({
                "endpoint": provider.endpoint_url,
                "status": "active",
                "latency_ms": int(provider.simulated_latency * 1000),
                "block_number": provider.block_number
            })
            
        return results
    
    async def get_gas_price(self) -> int:
        """Obtient le prix du gas actuel simulé."""
        provider = self.get_current_provider()
        return provider.gas_price

class SimulatedWeb3Provider:
    """Provider Web3 qui utilise notre fournisseur RPC simulé."""
    
    def __init__(self, rpc_provider: SimulatedRPCProvider):
        self.rpc_provider = rpc_provider
        
    def make_request(self, method, params):
        """Adapte la requête Web3 à notre format simulé."""
        # Convertir la requête asyncio en requête synchrone
        loop = asyncio.get_event_loop()
        response = loop.run_until_complete(self.rpc_provider.make_request(method, params))
        return response

# Singleton pour l'accès global
simulated_rpc_manager = SimulatedRPCManager() 