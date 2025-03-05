#!/usr/bin/env python3
"""
Module pour l'exécution des trades sur les exchanges centralisés (CEX).
"""

import asyncio
from decimal import Decimal
from typing import Dict, Optional
import ccxt.async_support as ccxt
from loguru import logger

from gbpbot.config.config_manager import ConfigManager
from gbpbot.core.exceptions import CEXTradeError

class CEXTradeExecutor:
    """Gestionnaire des trades sur les exchanges centralisés."""

    def __init__(self):
        """Initialise le CEXTradeExecutor avec la configuration."""
        self.config = ConfigManager().get_config()
        self.exchanges: Dict[str, ccxt.Exchange] = {}
        self._initialize_exchanges()

    def _initialize_exchanges(self):
        """Initialise les connexions aux exchanges configurés."""
        for exchange_id, config in self.config["cex"].items():
            if "api_key" in config and "api_secret" in config:
                exchange_class = getattr(ccxt, exchange_id)
                self.exchanges[exchange_id] = exchange_class({
                    'apiKey': config['api_key'],
                    'secret': config['api_secret'],
                    'enableRateLimit': True,
                    'options': {'adjustForTimeDifference': True}
                })

    async def execute_trade(self, opportunity: Dict) -> bool:
        """
        Exécute un trade sur un CEX.
        
        Args:
            opportunity: Dictionnaire contenant les détails de l'opportunité
            
        Returns:
            bool: True si le trade a réussi, False sinon
        """
        try:
            exchange_id = opportunity["cex_name"]
            if exchange_id not in self.exchanges:
                logger.error(f"Exchange {exchange_id} non configuré")
                return False

            exchange = self.exchanges[exchange_id]
            
            # Vérification des conditions de marché
            if not await self._verify_market_conditions(exchange, opportunity):
                return False

            # Calcul du montant optimal pour le trade
            amount = await self._calculate_trade_amount(exchange, opportunity)
            if amount is None:
                return False

            # Exécution du trade
            order = await self._place_order(exchange, opportunity, amount)
            if order is None:
                return False

            # Attente de la confirmation
            success = await self._wait_for_order_completion(exchange, order["id"])
            
            return success

        except Exception as e:
            logger.error(f"Erreur lors de l'exécution du trade CEX: {str(e)}")
            return False

    async def _verify_market_conditions(self, exchange: ccxt.Exchange, opportunity: Dict) -> bool:
        """Vérifie que les conditions de marché sont toujours valables."""
        try:
            symbol = opportunity["symbol"]
            current_price = await self._get_current_price(exchange, symbol)
            
            if current_price is None:
                return False

            expected_price = Decimal(opportunity["cex_price"])
            price_change = abs(Decimal(current_price) - expected_price) / expected_price
            
            if price_change > Decimal(str(self.config["security"]["max_price_change"])):
                logger.warning(f"Prix changé de {price_change*100}% - annulation du trade")
                return False

            return True

        except Exception as e:
            logger.error(f"Erreur lors de la vérification des conditions: {str(e)}")
            return False

    async def _calculate_trade_amount(self, exchange: ccxt.Exchange, opportunity: Dict) -> Optional[float]:
        """Calcule le montant optimal pour le trade en respectant les limites."""
        try:
            # Récupération des limites de l'exchange
            market = await exchange.load_markets()
            symbol = opportunity["symbol"]
            
            if symbol not in market:
                logger.error(f"Symbole {symbol} non trouvé sur {exchange.id}")
                return None

            limits = market[symbol]["limits"]
            
            # Calcul du montant en respectant les limites
            amount = min(
                float(opportunity["amount"]),
                float(self.config["arbitrage"]["max_trade_amount"]),
                limits["amount"]["max"] if limits["amount"]["max"] else float("inf")
            )
            
            if amount < limits["amount"]["min"]:
                logger.warning(f"Montant {amount} inférieur au minimum {limits['amount']['min']}")
                return None

            return amount

        except Exception as e:
            logger.error(f"Erreur lors du calcul du montant: {str(e)}")
            return None

    async def _place_order(self, exchange: ccxt.Exchange, opportunity: Dict, amount: float) -> Optional[Dict]:
        """Place un ordre sur l'exchange."""
        try:
            symbol = opportunity["symbol"]
            side = "buy" if float(opportunity["price_difference"]) > 0 else "sell"
            
            order = await exchange.create_order(
                symbol=symbol,
                type="market",
                side=side,
                amount=amount
            )
            
            logger.info(f"Ordre placé sur {exchange.id}: {order['id']}")
            return order

        except Exception as e:
            logger.error(f"Erreur lors du placement de l'ordre: {str(e)}")
            return None

    async def _wait_for_order_completion(self, exchange: ccxt.Exchange, order_id: str) -> bool:
        """Attend la confirmation de l'exécution de l'ordre."""
        max_attempts = self.config["security"]["max_confirmation_attempts"]
        attempt = 0
        
        while attempt < max_attempts:
            try:
                order = await exchange.fetch_order(order_id)
                
                if order["status"] == "closed":
                    logger.info(f"Ordre {order_id} exécuté avec succès")
                    return True
                elif order["status"] == "canceled":
                    logger.warning(f"Ordre {order_id} annulé")
                    return False
                
                await asyncio.sleep(1)
                attempt += 1
                
            except Exception as e:
                logger.error(f"Erreur lors de la vérification de l'ordre: {str(e)}")
                return False
        
        logger.warning(f"Timeout lors de l'attente de la confirmation de l'ordre {order_id}")
        return False

    async def _get_current_price(self, exchange: ccxt.Exchange, symbol: str) -> Optional[float]:
        """Récupère le prix actuel sur l'exchange."""
        try:
            ticker = await exchange.fetch_ticker(symbol)
            return ticker["last"]
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du prix: {str(e)}")
            return None

    async def close(self):
        """Ferme proprement les connexions aux exchanges."""
        for exchange in self.exchanges.values():
            await exchange.close() 