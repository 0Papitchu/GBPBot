#!/usr/bin/env python3
"""
Module de gestion des oracles de prix (Chainlink, Pyth, etc.).
"""

import asyncio
from typing import Dict, List, Optional
from decimal import Decimal
from web3 import Web3
from loguru import logger

from gbpbot.core.monitoring.monitor import BotMonitor
from gbpbot.core.rpc.rpc_manager import rpc_manager
from ..base import BasePriceFeed

class OraclePriceFeed(BasePriceFeed):
    """Price feed pour les oracles."""
    
    def __init__(self, config: Dict, monitor: BotMonitor):
        """
        Initialise le feed de prix des oracles.
        
        Args:
            config: Configuration du bot
            monitor: Instance du moniteur
        """
        super().__init__(config)
        self.monitor = monitor
        self.rpc_manager = rpc_manager
        
        # État du service
        self.is_running = False
        self.prices: Dict[str, Dict] = {}
        self.last_update = 0
        
        # Configuration des oracles
        self.oracle_configs = self.config.get('oracles', {})
        self.update_interval = self.config.get('price_feed', {}).get('oracle_update_interval', 5)
        
        # Cache
        self.price_cache = {}
        self.cache_timeout = 60  # Les prix des oracles sont plus stables
        
        # Contrats
        self.oracle_contracts = {}
        
    async def start(self) -> None:
        """Démarre le monitoring des prix des oracles."""
        self.is_running = True
        await self._init_contracts()
        asyncio.create_task(self._start_price_monitoring())
        logger.info("Oracle price feed démarré")
        
    async def stop(self) -> None:
        """Arrête le monitoring des prix."""
        self.is_running = False
        logger.info("Oracle price feed arrêté")
        
    async def get_price(self, token_symbol: str) -> Optional[Decimal]:
        """
        Récupère le prix d'un token depuis un oracle.
        
        Args:
            token_symbol: Symbole du token (ex: "AVAX")
            
        Returns:
            Optional[Decimal]: Prix du token ou None si non disponible
        """
        if token_symbol in self.prices:
            return Decimal(self.prices[token_symbol]["price"])
        
        # Essayer de récupérer le prix
        price = await self._fetch_oracle_price(token_symbol)
        if price:
            self.prices[token_symbol] = {
                "price": float(price),
                "timestamp": asyncio.get_event_loop().time()
            }
            return price
            
        return None
        
    async def get_all_prices(self) -> Dict[str, Dict]:
        """
        Récupère tous les prix des oracles.
        
        Returns:
            Dict[str, Dict]: Dictionnaire des prix par token
        """
        return self.prices
        
    async def _init_contracts(self) -> None:
        """Initialise les contrats des oracles."""
        # Récupérer une instance Web3
        chain = self.config.get("chain", "avalanche")
        network = self.config.get("network", "mainnet")
        
        try:
            web3 = await self.rpc_manager.get_web3(chain, network)
            
            # Initialiser les contrats Chainlink
            for symbol, config in self.oracle_configs.get("chainlink", {}).items():
                contract_address = config.get("address")
                if contract_address:
                    abi = self.oracle_configs.get("chainlink_abi")
                    if abi:
                        contract = web3.eth.contract(
                            address=Web3.to_checksum_address(contract_address),
                            abi=abi
                        )
                        self.oracle_contracts[f"chainlink_{symbol}"] = contract
            
            # Initialiser les contrats Pyth
            pyth_address = self.oracle_configs.get("pyth", {}).get("address")
            pyth_abi = self.oracle_configs.get("pyth_abi")
            if pyth_address and pyth_abi:
                contract = web3.eth.contract(
                    address=Web3.to_checksum_address(pyth_address),
                    abi=pyth_abi
                )
                self.oracle_contracts["pyth"] = contract
                
            logger.info(f"Contrats des oracles initialisés: {len(self.oracle_contracts)}")
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation des contrats des oracles: {str(e)}")
            
    async def _start_price_monitoring(self) -> None:
        """Démarre la boucle de monitoring des prix."""
        while self.is_running:
            try:
                await self.update_prices()
                await self._update_metrics()
            except Exception as e:
                logger.error(f"Erreur lors de la mise à jour des prix des oracles: {str(e)}")
            
            await asyncio.sleep(self.update_interval)
            
    async def update_prices(self) -> None:
        """Met à jour les prix des oracles."""
        tasks = []
        
        # Mettre à jour les prix Chainlink
        for symbol in self.oracle_configs.get("chainlink", {}).keys():
            tasks.append(self._fetch_chainlink_price(symbol))
            
        # Mettre à jour les prix Pyth
        for symbol, price_id in self.oracle_configs.get("pyth", {}).get("price_ids", {}).items():
            tasks.append(self._fetch_pyth_price(symbol, price_id))
            
        # Exécuter les tâches en parallèle
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Traiter les résultats
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Erreur lors de la récupération d'un prix d'oracle: {str(result)}")
                
    async def _fetch_oracle_price(self, token_symbol: str) -> Optional[Decimal]:
        """
        Récupère le prix d'un token depuis les oracles disponibles.
        
        Args:
            token_symbol: Symbole du token
            
        Returns:
            Optional[Decimal]: Prix du token ou None si non disponible
        """
        # Essayer Chainlink
        price = await self._fetch_chainlink_price(token_symbol)
        if price:
            return price
            
        # Essayer Pyth
        price_id = self.oracle_configs.get("pyth", {}).get("price_ids", {}).get(f"{token_symbol}/USD")
        if price_id:
            price = await self._fetch_pyth_price(token_symbol, price_id)
            if price:
                return price
                
        return None
        
    async def _fetch_chainlink_price(self, token_symbol: str) -> Optional[Decimal]:
        """
        Récupère le prix d'un token depuis Chainlink.
        
        Args:
            token_symbol: Symbole du token
            
        Returns:
            Optional[Decimal]: Prix du token ou None si non disponible
        """
        contract_key = f"chainlink_{token_symbol}"
        if contract_key not in self.oracle_contracts:
            return None
            
        try:
            contract = self.oracle_contracts[contract_key]
            
            # Appeler latestRoundData
            round_data = await self.rpc_manager.call_rpc(
                "eth_call",
                [
                    {
                        "to": contract.address,
                        "data": contract.encodeABI(fn_name="latestRoundData")
                    },
                    "latest"
                ]
            )
            
            # Décoder la réponse
            decoded = contract.decode_function_result("latestRoundData", round_data)
            price = decoded[1]
            
            # Récupérer les décimales
            decimals = await self.rpc_manager.call_rpc(
                "eth_call",
                [
                    {
                        "to": contract.address,
                        "data": contract.encodeABI(fn_name="decimals")
                    },
                    "latest"
                ]
            )
            
            # Décoder les décimales
            decimals = contract.decode_function_result("decimals", decimals)[0]
            
            # Calculer le prix
            price_decimal = Decimal(price) / Decimal(10 ** decimals)
            
            # Mettre à jour le cache
            self.prices[token_symbol] = {
                "price": float(price_decimal),
                "source": "chainlink",
                "timestamp": asyncio.get_event_loop().time()
            }
            
            return price_decimal
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du prix Chainlink pour {token_symbol}: {str(e)}")
            return None
            
    async def _fetch_pyth_price(self, token_symbol: str, price_id: str) -> Optional[Decimal]:
        """
        Récupère le prix d'un token depuis Pyth Network.
        
        Args:
            token_symbol: Symbole du token
            price_id: ID du prix dans Pyth
            
        Returns:
            Optional[Decimal]: Prix du token ou None si non disponible
        """
        if "pyth" not in self.oracle_contracts:
            return None
            
        try:
            contract = self.oracle_contracts["pyth"]
            
            # Appeler getPriceUnsafe
            price_data = await self.rpc_manager.call_rpc(
                "eth_call",
                [
                    {
                        "to": contract.address,
                        "data": contract.encodeABI(
                            fn_name="getPriceUnsafe",
                            args=[price_id]
                        )
                    },
                    "latest"
                ]
            )
            
            # Décoder la réponse
            decoded = contract.decode_function_result("getPriceUnsafe", price_data)
            price = decoded[0]
            expo = decoded[2]
            
            # Calculer le prix
            price_decimal = Decimal(price) * Decimal(10 ** expo)
            
            # Mettre à jour le cache
            self.prices[token_symbol] = {
                "price": float(price_decimal),
                "source": "pyth",
                "timestamp": asyncio.get_event_loop().time()
            }
            
            return price_decimal
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du prix Pyth pour {token_symbol}: {str(e)}")
            return None
            
    async def _update_metrics(self) -> None:
        """Met à jour les métriques de monitoring."""
        if not hasattr(self, 'monitor') or not self.monitor:
            return
            
        try:
            # Nombre de prix disponibles
            self.monitor.set_gauge("oracle_prices_count", len(self.prices))
            
            # Âge moyen des prix
            now = asyncio.get_event_loop().time()
            ages = [now - price_data["timestamp"] for price_data in self.prices.values()]
            if ages:
                avg_age = sum(ages) / len(ages)
                self.monitor.set_gauge("oracle_prices_avg_age", avg_age)
                
            # Prix par source
            sources = {}
            for price_data in self.prices.values():
                source = price_data.get("source", "unknown")
                sources[source] = sources.get(source, 0) + 1
                
            for source, count in sources.items():
                self.monitor.set_gauge(f"oracle_prices_{source}_count", count)
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour des métriques des oracles: {str(e)}")
            
    async def get_status(self) -> Dict:
        """
        Récupère l'état du service.
        
        Returns:
            Dict: État du service
        """
        return {
            "running": self.is_running,
            "prices_count": len(self.prices),
            "contracts_count": len(self.oracle_contracts),
            "last_update": self.last_update
        }
        
    async def get_liquidity(self, token_address: str) -> Optional[Decimal]:
        """
        Les oracles ne fournissent pas d'information sur la liquidité.
        Cette méthode est implémentée pour respecter l'interface BasePriceFeed.
        
        Args:
            token_address: Adresse du token
            
        Returns:
            None: Les oracles ne fournissent pas d'information sur la liquidité
        """
        return None
        
    async def validate_price(self, token_address: str, price: Decimal) -> bool:
        """
        Valide si un prix est cohérent avec les données des oracles.
        
        Args:
            token_address: Adresse du token
            price: Prix à valider
            
        Returns:
            bool: True si le prix est cohérent, False sinon
        """
        # Récupérer le symbole du token
        token_symbol = None
        for symbol, config in self.config.get("tokens", {}).items():
            if config.get("address") == token_address:
                token_symbol = symbol
                break
                
        if not token_symbol:
            return False
            
        # Récupérer le prix de l'oracle
        oracle_price = await self.get_price(token_symbol)
        if not oracle_price:
            return True  # Pas de prix oracle disponible, on ne peut pas valider
            
        # Calculer la différence relative
        diff = abs(price - oracle_price) / oracle_price
        
        # Seuil de tolérance (configurable)
        tolerance = self.config.get("price_feed", {}).get("oracle_tolerance", 0.05)  # 5% par défaut
        
        return diff <= tolerance 