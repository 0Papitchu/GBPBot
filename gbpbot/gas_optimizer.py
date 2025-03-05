#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module d'optimisation du gas pour éviter le front-running.
Ce module permet d'ajuster dynamiquement les frais de gas en fonction de la congestion
du réseau et de la concurrence pour maximiser les chances de succès des transactions.
"""

import os
import sys
import time
import json
import asyncio
import statistics
from typing import Dict, List, Any, Optional, Tuple, Callable
from web3 import Web3
from loguru import logger
from dotenv import load_dotenv
import aiohttp
import requests

# Charger les variables d'environnement
load_dotenv()

# Configurer le logger
logger.remove()
logger.add(sys.stderr, level="INFO")
logger.add("gas_optimizer.log", rotation="10 MB", level="DEBUG")

class GasOptimizer:
    """Classe pour l'optimisation des frais de gas."""
    
    def __init__(self, 
                 web3_provider: str = None,
                 gas_api_key: str = None,
                 max_gas_price: float = 500.0,  # en gwei
                 min_gas_price: float = 1.0,    # en gwei
                 gas_price_strategy: str = "aggressive",
                 update_interval: int = 15,     # en secondes
                 chain_id: int = 1):            # 1 = Ethereum, 56 = BSC
        """
        Initialiser le module d'optimisation du gas.
        
        Args:
            web3_provider: URL du fournisseur Web3 (ex: Infura, Alchemy)
            gas_api_key: Clé API pour les services de gas (ex: Etherscan, GasNow)
            max_gas_price: Prix maximum du gas à utiliser (en gwei)
            min_gas_price: Prix minimum du gas à utiliser (en gwei)
            gas_price_strategy: Stratégie de prix du gas ("safe", "standard", "fast", "aggressive")
            update_interval: Intervalle de mise à jour des prix du gas (en secondes)
            chain_id: ID de la chaîne (1 = Ethereum, 56 = BSC, etc.)
        """
        # Configuration Web3
        self.web3_provider = web3_provider or os.getenv("WEB3_PROVIDER_URL")
        self.gas_api_key = gas_api_key or os.getenv("GAS_API_KEY")
        
        if not self.web3_provider:
            raise ValueError("Web3 provider URL is required")
        
        self.web3 = Web3(Web3.HTTPProvider(self.web3_provider))
        
        # Vérifier la connexion
        if not self.web3.is_connected():
            raise ConnectionError("Failed to connect to Web3 provider")
        
        # Configuration du gas
        self.max_gas_price = max_gas_price
        self.min_gas_price = min_gas_price
        self.gas_price_strategy = gas_price_strategy
        self.update_interval = update_interval
        self.chain_id = chain_id
        
        # Données de suivi
        self.current_gas_prices = {
            "safe": 0,
            "standard": 0,
            "fast": 0,
            "rapid": 0
        }
        self.gas_price_history = []
        self.last_update_time = 0
        self.is_updating = False
        self.update_task = None
        
        # Callbacks
        self.on_gas_price_updated = None
        
        # Facteurs de multiplication pour les stratégies
        self.strategy_multipliers = {
            "safe": 0.8,       # 80% du prix standard
            "standard": 1.0,   # Prix standard
            "fast": 1.2,       # 120% du prix standard
            "aggressive": 1.5  # 150% du prix standard
        }
        
        # Initialiser les prix du gas
        self._update_gas_prices()
        
        logger.info(f"Gas optimizer initialized with {gas_price_strategy} strategy")
    
    def start_auto_update(self):
        """Démarrer la mise à jour automatique des prix du gas."""
        if self.update_task is None:
            self.is_updating = True
            self.update_task = asyncio.create_task(self._auto_update_gas_prices())
            logger.info("Automatic gas price updates started")
    
    async def _auto_update_gas_prices(self):
        """Mettre à jour automatiquement les prix du gas à intervalles réguliers."""
        while self.is_updating:
            try:
                self._update_gas_prices()
                await asyncio.sleep(self.update_interval)
            except Exception as e:
                logger.error(f"Error in auto update gas prices: {e}")
                await asyncio.sleep(5)  # Attendre un peu plus en cas d'erreur
    
    def stop_auto_update(self):
        """Arrêter la mise à jour automatique des prix du gas."""
        self.is_updating = False
        if self.update_task:
            self.update_task.cancel()
            self.update_task = None
            logger.info("Automatic gas price updates stopped")
    
    def _update_gas_prices(self):
        """Mettre à jour les prix du gas à partir de différentes sources."""
        try:
            # Obtenir les prix du gas à partir de différentes sources
            prices = []
            
            # 1. Web3 (toujours disponible)
            web3_price = self._get_web3_gas_price()
            if web3_price:
                prices.append(("web3", web3_price))
            
            # 2. API externe (si disponible)
            api_prices = self._get_api_gas_prices()
            if api_prices:
                prices.extend(api_prices)
            
            # Calculer les prix finaux en fonction des sources disponibles
            if prices:
                # Calculer les prix pour chaque catégorie
                safe_prices = [price for source, price in prices if source in ["web3", "etherscan_safe", "gasnow_safe"]]
                standard_prices = [price for source, price in prices if source in ["web3", "etherscan_average", "gasnow_standard"]]
                fast_prices = [price for source, price in prices if source in ["web3", "etherscan_fast", "gasnow_fast"]]
                rapid_prices = [price for source, price in prices if source in ["etherscan_fastest", "gasnow_rapid"]]
                
                # Calculer les moyennes (ou utiliser une valeur par défaut)
                safe_price = statistics.median(safe_prices) if safe_prices else 0
                standard_price = statistics.median(standard_prices) if standard_prices else 0
                fast_price = statistics.median(fast_prices) if fast_prices else 0
                rapid_price = statistics.median(rapid_prices) if rapid_prices else 0
                
                # Si certaines catégories n'ont pas de prix, les dériver des autres
                if not safe_price and standard_price:
                    safe_price = standard_price * 0.8
                if not standard_price and (safe_price or fast_price):
                    if safe_price:
                        standard_price = safe_price / 0.8
                    else:
                        standard_price = fast_price / 1.2
                if not fast_price and standard_price:
                    fast_price = standard_price * 1.2
                if not rapid_price and fast_price:
                    rapid_price = fast_price * 1.5
                
                # Mettre à jour les prix actuels
                self.current_gas_prices = {
                    "safe": max(self.min_gas_price, min(self.max_gas_price, safe_price)),
                    "standard": max(self.min_gas_price, min(self.max_gas_price, standard_price)),
                    "fast": max(self.min_gas_price, min(self.max_gas_price, fast_price)),
                    "rapid": max(self.min_gas_price, min(self.max_gas_price, rapid_price))
                }
                
                # Ajouter à l'historique
                self.gas_price_history.append({
                    "timestamp": time.time(),
                    "prices": self.current_gas_prices.copy()
                })
                
                # Limiter la taille de l'historique
                max_history = 1000
                if len(self.gas_price_history) > max_history:
                    self.gas_price_history = self.gas_price_history[-max_history:]
                
                self.last_update_time = time.time()
                
                logger.debug(f"Gas prices updated: {self.current_gas_prices}")
                
                # Exécuter le callback si défini
                if self.on_gas_price_updated:
                    self.on_gas_price_updated(self.current_gas_prices)
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error updating gas prices: {e}")
            return False
    
    def _get_web3_gas_price(self) -> float:
        """
        Obtenir le prix du gas à partir de Web3.
        
        Returns:
            float: Prix du gas en gwei
        """
        try:
            # Obtenir le prix du gas en wei
            gas_price_wei = self.web3.eth.gas_price
            
            # Convertir en gwei
            gas_price_gwei = self.web3.from_wei(gas_price_wei, "gwei")
            
            return float(gas_price_gwei)
            
        except Exception as e:
            logger.error(f"Error getting Web3 gas price: {e}")
            return 0
    
    def _get_api_gas_prices(self) -> List[Tuple[str, float]]:
        """
        Obtenir les prix du gas à partir d'APIs externes.
        
        Returns:
            List[Tuple[str, float]]: Liste de tuples (source, prix en gwei)
        """
        prices = []
        
        # Essayer différentes APIs en fonction de la chaîne
        if self.chain_id == 1:  # Ethereum
            # Etherscan API
            etherscan_prices = self._get_etherscan_gas_prices()
            if etherscan_prices:
                prices.extend(etherscan_prices)
            
            # GasNow API (alternative)
            gasnow_prices = self._get_gasnow_gas_prices()
            if gasnow_prices:
                prices.extend(gasnow_prices)
        
        elif self.chain_id == 56:  # BSC
            # BSCScan API
            bscscan_prices = self._get_bscscan_gas_prices()
            if bscscan_prices:
                prices.extend(bscscan_prices)
        
        return prices
    
    def _get_etherscan_gas_prices(self) -> List[Tuple[str, float]]:
        """
        Obtenir les prix du gas à partir de l'API Etherscan.
        
        Returns:
            List[Tuple[str, float]]: Liste de tuples (source, prix en gwei)
        """
        try:
            if not self.gas_api_key:
                return []
            
            url = f"https://api.etherscan.io/api?module=gastracker&action=gasoracle&apikey={self.gas_api_key}"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                
                if data["status"] == "1":
                    result = data["result"]
                    
                    return [
                        ("etherscan_safe", float(result["SafeGasPrice"])),
                        ("etherscan_average", float(result["ProposeGasPrice"])),
                        ("etherscan_fast", float(result["FastGasPrice"])),
                        ("etherscan_fastest", float(result["FastGasPrice"]) * 1.2)
                    ]
            
            return []
            
        except Exception as e:
            logger.error(f"Error getting Etherscan gas prices: {e}")
            return []
    
    def _get_gasnow_gas_prices(self) -> List[Tuple[str, float]]:
        """
        Obtenir les prix du gas à partir de l'API GasNow (ou alternative).
        
        Returns:
            List[Tuple[str, float]]: Liste de tuples (source, prix en gwei)
        """
        try:
            # Note: GasNow n'est plus disponible, ceci est un exemple avec une API alternative
            url = "https://www.gasnow.org/api/v3/gas/price"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                
                if data["code"] == 200:
                    result = data["data"]
                    
                    return [
                        ("gasnow_safe", self.web3.from_wei(result["slow"], "gwei")),
                        ("gasnow_standard", self.web3.from_wei(result["standard"], "gwei")),
                        ("gasnow_fast", self.web3.from_wei(result["fast"], "gwei")),
                        ("gasnow_rapid", self.web3.from_wei(result["rapid"], "gwei"))
                    ]
            
            return []
            
        except Exception as e:
            logger.debug(f"Error getting GasNow gas prices (expected if service is down): {e}")
            return []
    
    def _get_bscscan_gas_prices(self) -> List[Tuple[str, float]]:
        """
        Obtenir les prix du gas à partir de l'API BSCScan.
        
        Returns:
            List[Tuple[str, float]]: Liste de tuples (source, prix en gwei)
        """
        try:
            if not self.gas_api_key:
                return []
            
            url = f"https://api.bscscan.com/api?module=gastracker&action=gasoracle&apikey={self.gas_api_key}"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                
                if data["status"] == "1":
                    result = data["result"]
                    
                    return [
                        ("bscscan_safe", float(result["SafeGasPrice"])),
                        ("bscscan_average", float(result["ProposeGasPrice"])),
                        ("bscscan_fast", float(result["FastGasPrice"])),
                        ("bscscan_fastest", float(result["FastGasPrice"]) * 1.2)
                    ]
            
            return []
            
        except Exception as e:
            logger.error(f"Error getting BSCScan gas prices: {e}")
            return []
    
    def get_gas_price(self, strategy: Optional[str] = None) -> float:
        """
        Obtenir le prix du gas en fonction de la stratégie.
        
        Args:
            strategy: Stratégie de prix du gas ("safe", "standard", "fast", "aggressive")
                     Si None, utilise la stratégie par défaut
        
        Returns:
            float: Prix du gas en gwei
        """
        # Mettre à jour les prix si nécessaire
        if time.time() - self.last_update_time > self.update_interval:
            self._update_gas_prices()
        
        # Utiliser la stratégie spécifiée ou celle par défaut
        strategy = strategy or self.gas_price_strategy
        
        # Obtenir le prix de base en fonction de la stratégie
        if strategy == "safe":
            base_price = self.current_gas_prices["safe"]
        elif strategy == "standard":
            base_price = self.current_gas_prices["standard"]
        elif strategy == "fast":
            base_price = self.current_gas_prices["fast"]
        elif strategy == "aggressive":
            base_price = self.current_gas_prices["rapid"]
        else:
            base_price = self.current_gas_prices["standard"]
        
        # Appliquer le multiplicateur de stratégie
        multiplier = self.strategy_multipliers.get(strategy, 1.0)
        gas_price = base_price * multiplier
        
        # Limiter le prix
        gas_price = max(self.min_gas_price, min(self.max_gas_price, gas_price))
        
        return gas_price
    
    def get_gas_price_wei(self, strategy: Optional[str] = None) -> int:
        """
        Obtenir le prix du gas en wei en fonction de la stratégie.
        
        Args:
            strategy: Stratégie de prix du gas ("safe", "standard", "fast", "aggressive")
                     Si None, utilise la stratégie par défaut
        
        Returns:
            int: Prix du gas en wei
        """
        gas_price_gwei = self.get_gas_price(strategy)
        gas_price_wei = self.web3.to_wei(gas_price_gwei, "gwei")
        
        return int(gas_price_wei)
    
    def estimate_transaction_fee(self, gas_limit: int, strategy: Optional[str] = None) -> Dict[str, Any]:
        """
        Estimer les frais de transaction en fonction de la stratégie.
        
        Args:
            gas_limit: Limite de gas pour la transaction
            strategy: Stratégie de prix du gas
        
        Returns:
            Dict[str, Any]: Estimation des frais de transaction
        """
        gas_price_gwei = self.get_gas_price(strategy)
        gas_price_wei = self.web3.to_wei(gas_price_gwei, "gwei")
        
        # Calculer les frais en wei et en ether
        fee_wei = gas_price_wei * gas_limit
        fee_eth = self.web3.from_wei(fee_wei, "ether")
        
        return {
            "gas_price_gwei": gas_price_gwei,
            "gas_price_wei": gas_price_wei,
            "gas_limit": gas_limit,
            "fee_wei": fee_wei,
            "fee_eth": fee_eth
        }
    
    def optimize_gas_for_transaction(self, tx_params: Dict[str, Any], strategy: Optional[str] = None) -> Dict[str, Any]:
        """
        Optimiser les paramètres de gas pour une transaction.
        
        Args:
            tx_params: Paramètres de la transaction
            strategy: Stratégie de prix du gas
        
        Returns:
            Dict[str, Any]: Paramètres de transaction optimisés
        """
        # Copier les paramètres pour ne pas modifier l'original
        optimized_params = tx_params.copy()
        
        # Obtenir le prix du gas optimisé
        gas_price_wei = self.get_gas_price_wei(strategy)
        
        # Mettre à jour le prix du gas
        optimized_params["gasPrice"] = gas_price_wei
        
        # Si la limite de gas n'est pas spécifiée, l'estimer
        if "gas" not in optimized_params and "to" in optimized_params and "data" in optimized_params:
            try:
                estimated_gas = self.web3.eth.estimate_gas({
                    "to": optimized_params["to"],
                    "from": optimized_params.get("from", self.web3.eth.default_account),
                    "value": optimized_params.get("value", 0),
                    "data": optimized_params.get("data", "0x")
                })
                
                # Ajouter une marge de sécurité (20%)
                optimized_params["gas"] = int(estimated_gas * 1.2)
                
            except Exception as e:
                logger.error(f"Error estimating gas: {e}")
        
        return optimized_params
    
    def detect_front_running(self, tx_hash: str, timeout: int = 60) -> Dict[str, Any]:
        """
        Détecter si une transaction est victime de front-running.
        
        Args:
            tx_hash: Hash de la transaction à surveiller
            timeout: Délai d'attente maximum en secondes
        
        Returns:
            Dict[str, Any]: Résultat de la détection
        """
        try:
            start_time = time.time()
            
            # Attendre que la transaction soit minée ou que le timeout soit atteint
            while time.time() - start_time < timeout:
                try:
                    # Vérifier si la transaction est minée
                    receipt = self.web3.eth.get_transaction_receipt(tx_hash)
                    
                    if receipt:
                        # Transaction minée, vérifier si elle a réussi
                        if receipt.status == 1:
                            return {
                                "front_running_detected": False,
                                "status": "success",
                                "block_number": receipt.blockNumber,
                                "gas_used": receipt.gasUsed
                            }
                        else:
                            # Transaction échouée, vérifier si c'est dû à un front-running
                            block = self.web3.eth.get_block(receipt.blockNumber, full_transactions=True)
                            
                            # Analyser les transactions du bloc pour détecter le front-running
                            tx_index = None
                            for i, tx in enumerate(block.transactions):
                                if tx.hash.hex() == tx_hash:
                                    tx_index = i
                                    break
                            
                            if tx_index is not None and tx_index > 0:
                                # Vérifier les transactions précédentes dans le même bloc
                                potential_front_runners = []
                                
                                for i in range(tx_index):
                                    prev_tx = block.transactions[i]
                                    
                                    # Vérifier si la transaction précédente interagit avec le même contrat
                                    if prev_tx.to == self.web3.eth.get_transaction(tx_hash).to:
                                        potential_front_runners.append({
                                            "tx_hash": prev_tx.hash.hex(),
                                            "from": prev_tx.get("from", ""),
                                            "gas_price": self.web3.from_wei(prev_tx.gasPrice, "gwei")
                                        })
                                
                                if potential_front_runners:
                                    return {
                                        "front_running_detected": True,
                                        "status": "failed",
                                        "block_number": receipt.blockNumber,
                                        "gas_used": receipt.gasUsed,
                                        "potential_front_runners": potential_front_runners
                                    }
                            
                            return {
                                "front_running_detected": False,
                                "status": "failed",
                                "block_number": receipt.blockNumber,
                                "gas_used": receipt.gasUsed
                            }
                    
                    # Transaction non encore minée, attendre
                    time.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error checking transaction: {e}")
                    time.sleep(1)
            
            # Timeout atteint
            return {
                "front_running_detected": False,
                "status": "pending",
                "message": "Transaction still pending after timeout"
            }
            
        except Exception as e:
            logger.error(f"Error detecting front-running: {e}")
            return {
                "front_running_detected": False,
                "status": "error",
                "message": str(e)
            }
    
    def get_gas_price_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Obtenir l'historique des prix du gas.
        
        Args:
            hours: Nombre d'heures d'historique à retourner
        
        Returns:
            List[Dict[str, Any]]: Historique des prix du gas
        """
        # Calculer le timestamp minimum
        min_timestamp = time.time() - (hours * 3600)
        
        # Filtrer l'historique
        filtered_history = [
            entry for entry in self.gas_price_history
            if entry["timestamp"] >= min_timestamp
        ]
        
        return filtered_history
    
    def set_on_gas_price_updated_callback(self, callback: Callable[[Dict[str, float]], None]):
        """
        Définir le callback à exécuter lorsque les prix du gas sont mis à jour.
        
        Args:
            callback: Fonction à appeler avec les nouveaux prix
        """
        self.on_gas_price_updated = callback
    
    def set_gas_price_strategy(self, strategy: str):
        """
        Définir la stratégie de prix du gas.
        
        Args:
            strategy: Stratégie de prix du gas ("safe", "standard", "fast", "aggressive")
        """
        if strategy in ["safe", "standard", "fast", "aggressive"]:
            self.gas_price_strategy = strategy
            logger.info(f"Gas price strategy set to {strategy}")
        else:
            logger.warning(f"Invalid gas price strategy: {strategy}")
    
    def set_gas_price_limits(self, min_price: float, max_price: float):
        """
        Définir les limites de prix du gas.
        
        Args:
            min_price: Prix minimum du gas (en gwei)
            max_price: Prix maximum du gas (en gwei)
        """
        if min_price > 0 and max_price > min_price:
            self.min_gas_price = min_price
            self.max_gas_price = max_price
            logger.info(f"Gas price limits set to {min_price}-{max_price} gwei")
        else:
            logger.warning(f"Invalid gas price limits: {min_price}-{max_price}")

# Exemple d'utilisation
async def main():
    """Fonction principale pour tester le module."""
    # Créer une instance du module d'optimisation
    optimizer = GasOptimizer()
    
    # Définir un callback pour les mises à jour de prix
    def on_gas_price_updated(prices):
        print(f"Gas prices updated: {prices}")
    
    optimizer.set_on_gas_price_updated_callback(on_gas_price_updated)
    
    # Obtenir le prix du gas pour différentes stratégies
    print(f"Safe gas price: {optimizer.get_gas_price('safe')} gwei")
    print(f"Standard gas price: {optimizer.get_gas_price('standard')} gwei")
    print(f"Fast gas price: {optimizer.get_gas_price('fast')} gwei")
    print(f"Aggressive gas price: {optimizer.get_gas_price('aggressive')} gwei")
    
    # Estimer les frais de transaction
    fee_estimate = optimizer.estimate_transaction_fee(21000, "fast")
    print(f"Estimated transaction fee: {fee_estimate['fee_eth']} ETH")
    
    # Démarrer la mise à jour automatique
    optimizer.start_auto_update()
    
    # Attendre quelques mises à jour
    await asyncio.sleep(60)
    
    # Arrêter la mise à jour automatique
    optimizer.stop_auto_update()

if __name__ == "__main__":
    asyncio.run(main()) 