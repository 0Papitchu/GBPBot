#!/usr/bin/env python3
"""
Module de gestion des prix des exchanges décentralisés (DEX).
"""

import asyncio
from typing import Dict, List, Optional
from decimal import Decimal
from web3 import Web3
from loguru import logger

from gbpbot.core.monitoring.monitor import BotMonitor
from gbpbot.core.rpc.rpc_manager import RPCManager
from .base import BasePriceFeed

class DEXPriceFeed(BasePriceFeed):
    """Price feed pour les DEX."""
    
    def __init__(self, config: Dict, monitor: BotMonitor):
        """
        Initialise le feed de prix DEX.
        
        Args:
            config: Configuration du bot
            monitor: Instance du moniteur
        """
        super().__init__(config)
        self.monitor = monitor
        self.rpc_manager = RPCManager()  # Obtenir l'instance du gestionnaire RPC
        self.price_cache = {}
        self.liquidity_cache = {}
        
        # État du service
        self.is_running = False
        self.prices: Dict[str, Dict] = {}
        self.last_update = 0
        
        # Configuration des DEX
        self.dex_configs = self.config.get('dex', {})
        self.update_interval = self.config.get('price_feed', {}).get('dex_update_interval', 1)
        
        # Contrats et ABIs
        self.router_contracts = {}
        self.pair_contracts = {}
        self.token_contracts = {}
        
        logger.info("Feed DEX initialisé")

    async def start(self) -> None:
        """Démarre le monitoring des prix DEX."""
        try:
            logger.info("Démarrage du feed DEX")
            self.is_running = True
            await self._init_contracts()
            await self._start_price_monitoring()
            logger.info("Feed DEX démarré avec succès")
        except Exception as e:
            logger.error(f"Erreur lors du démarrage du feed DEX: {str(e)}")
            self.is_running = False
            raise
        
    async def stop(self) -> None:
        """Arrête le monitoring des prix."""
        try:
            logger.info("Arrêt du feed DEX")
            self.is_running = False
            logger.info("Feed DEX arrêté avec succès")
        except Exception as e:
            logger.error(f"Erreur lors de l'arrêt du feed DEX: {str(e)}")
            raise
        
    async def get_price(self, token_address: str) -> Optional[Decimal]:
        """
        Récupère le prix d'un token sur le DEX.
        
        Args:
            token_address: Adresse du token
            
        Returns:
            Optional[Decimal]: Prix du token ou None si non disponible
        """
        try:
            # Vérifier si le prix est dans le cache
            for key, price_info in self.prices.items():
                if key.startswith(f"{token_address}_"):
                    logger.debug(f"Prix trouvé dans le cache pour {token_address}: {price_info['price']}")
                    return price_info['price']
            
            # Si le prix n'est pas dans le cache, le récupérer depuis le DEX
            logger.debug(f"Prix non trouvé dans le cache pour {token_address}, récupération depuis le DEX")
            price = await self._get_price_from_dex(token_address)
            return price
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du prix pour {token_address}: {str(e)}")
            return None
            
    async def get_liquidity(self, token_address: str) -> Optional[Decimal]:
        """
        Récupère la liquidité d'un token sur le DEX.
        
        Args:
            token_address: Adresse du token
            
        Returns:
            Optional[Decimal]: Liquidité du token ou None si non disponible
        """
        try:
            # Vérifier si la liquidité est dans le cache
            if token_address in self.liquidity_cache:
                logger.debug(f"Liquidité trouvée dans le cache pour {token_address}: {self.liquidity_cache[token_address]['liquidity']}")
                return self.liquidity_cache[token_address]['liquidity']
            
            # Si la liquidité n'est pas dans le cache, la récupérer depuis le DEX
            logger.debug(f"Liquidité non trouvée dans le cache pour {token_address}, récupération depuis le DEX")
            # Implémentation à compléter
            return None
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de la liquidité pour {token_address}: {str(e)}")
            return None
            
    async def validate_price(self, token_address: str, price: Decimal) -> bool:
        """Valide si un prix est cohérent avec les données on-chain."""
        current_price = await self.get_price(token_address)
        if not current_price:
            return False
            
        # Vérifie si le prix est dans une marge acceptable
        deviation = abs(price - current_price) / current_price
        return deviation <= self.config['max_price_deviation']
        
    async def _init_contracts(self) -> None:
        """Initialise les contrats DEX."""
        try:
            logger.debug("Initialisation des contrats DEX")
            web3 = Web3(Web3.HTTPProvider(await self.rpc_manager.get_best_rpc_url()))
            
            for dex_name, dex_config in self.dex_configs.items():
                # Router contract
                router_address = web3.to_checksum_address(dex_config['router_address'])
                router_abi = dex_config['router_abi']
                self.router_contracts[dex_name] = web3.eth.contract(
                    address=router_address,
                    abi=router_abi
                )
                
                # Factory contract si nécessaire
                if 'factory_address' in dex_config and 'factory_abi' in dex_config:
                    factory_address = web3.to_checksum_address(dex_config['factory_address'])
                    factory_abi = dex_config['factory_abi']
                    self.pair_contracts[dex_name] = web3.eth.contract(
                        address=factory_address,
                        abi=factory_abi
                    )
                    
            logger.debug("Contrats DEX initialisés avec succès")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation des contrats DEX: {str(e)}")
            raise

    async def _start_price_monitoring(self) -> None:
        """Démarre le monitoring des prix."""
        try:
            logger.debug("Démarrage du monitoring des prix DEX")
            # TODO: Implémenter la logique de monitoring
            pass
            logger.debug("Monitoring des prix DEX démarré avec succès")
        except Exception as e:
            logger.error(f"Erreur lors du démarrage du monitoring des prix DEX: {str(e)}")
            raise
        
    async def _get_price_from_dex(self, token_address: str) -> Optional[Decimal]:
        """
        Récupère le prix d'un token depuis le DEX.
        
        Args:
            token_address: Adresse du token
            
        Returns:
            Optional[Decimal]: Prix du token ou None si non disponible
        """
        try:
            logger.debug(f"Récupération du prix depuis le DEX pour {token_address}")
            # TODO: Implémenter la récupération des prix via les contrats
            return Decimal('0')
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du prix depuis le DEX pour {token_address}: {str(e)}")
            return None
        
    async def _fetch_onchain_liquidity(self, token_address: str) -> Optional[Decimal]:
        """Récupère la liquidité on-chain d'un token."""
        # TODO: Implémenter la récupération de la liquidité
        pass

    async def get_all_prices(self) -> Dict[str, Dict]:
        """
        Récupère tous les prix disponibles.
        
        Returns:
            Dict[str, Dict]: Dictionnaire des prix par token et DEX
        """
        return self.prices.copy()

    async def update_prices(self):
        """Met à jour les prix de tous les tokens configurés."""
        if not self.is_running:
            return
            
        try:
            current_time = asyncio.get_event_loop().time()
            if current_time - self.last_update < self.update_interval:
                return
                
            # Mettre à jour les prix pour chaque DEX
            for dex_name, dex_config in self.dex_configs.items():
                for token_address in dex_config.get('tokens', []):
                    await self.get_price(token_address)
                    
            self.last_update = current_time
            
            # Mettre à jour les métriques
            await self._update_metrics()
            
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour des prix DEX: {str(e)}")

    async def get_status(self) -> Dict:
        """
        Récupère l'état actuel du feed.
        
        Returns:
            Dict: État du feed
        """
        return {
            'is_running': self.is_running,
            'last_update': self.last_update,
            'prices_count': len(self.prices),
            'dex_count': len(self.dex_configs)
        }

    async def _update_metrics(self):
        """Met à jour les métriques du feed DEX."""
        try:
            metrics = {
                'dex_prices_count': len(self.prices),
                'dex_update_time': asyncio.get_event_loop().time() - self.last_update
            }
            
            # Métriques par DEX
            for dex_name in self.dex_configs:
                dex_prices = [p for k, p in self.prices.items() if p['exchange'] == dex_name]
                metrics[f'dex_{dex_name}_prices'] = len(dex_prices)
                
                if dex_prices:
                    metrics[f'dex_{dex_name}_avg_price'] = sum(
                        float(p['price']) for p in dex_prices
                    ) / len(dex_prices)
                    
            await self.monitor.update_market_metrics(metrics)
            
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour des métriques DEX: {str(e)}") 