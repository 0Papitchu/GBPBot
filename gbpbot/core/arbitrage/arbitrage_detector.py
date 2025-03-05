#!/usr/bin/env python3
"""
Module de détection d'arbitrage pour GBPBot.
Implémente la logique de détection des opportunités d'arbitrage avec protections.
"""

import asyncio
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from web3 import Web3
from loguru import logger

from gbpbot.config.config_manager import ConfigManager
from gbpbot.core.price.dex_price_manager import DexPriceManager
from gbpbot.core.price.cex_price_manager import CexPriceManager
from gbpbot.core.rpc.rpc_manager import RPCManager

class ArbitrageDetector:
    def __init__(self):
        self.config = ConfigManager().get_config()
        self.dex_manager = DexPriceManager()
        self.cex_manager = CexPriceManager()
        self.rpc_manager = RPCManager()
        
        # Configuration des seuils
        self.min_profit_threshold = Decimal(self.config["arbitrage"]["min_profit_threshold"])
        self.max_price_impact = Decimal(self.config["arbitrage"]["max_price_impact"])
        self.min_liquidity = Web3.to_wei(self.config["arbitrage"]["min_liquidity"], 'ether')
        
    async def initialize(self):
        """Initialise les composants nécessaires."""
        await self.cex_manager.initialize()
        
    async def detect_opportunities(self, token_address: str) -> List[Dict]:
        """Détecte les opportunités d'arbitrage pour un token donné."""
        opportunities = []
        
        try:
            # Récupérer les prix sur tous les DEX
            dex_prices = await self.dex_manager.get_all_dex_prices(token_address)
            if not dex_prices:
                return []
                
            # Récupérer les prix CEX de référence
            cex_prices = {}
            for cex in self.config["cex"].keys():
                price = await self.cex_manager.get_price(token_address, cex)
                if price:
                    cex_prices[cex] = price
                    
            if not cex_prices:
                return []
                
            # Analyser les opportunités
            for dex_name, dex_price in dex_prices.items():
                for cex_name, cex_price in cex_prices.items():
                    opportunity = await self._analyze_opportunity(
                        token_address,
                        dex_name,
                        cex_name,
                        Decimal(str(dex_price)),
                        Decimal(str(cex_price))
                    )
                    if opportunity:
                        opportunities.append(opportunity)
                        
        except Exception as e:
            logger.error(f"Erreur lors de la détection d'opportunités: {str(e)}")
            
        return opportunities
        
    async def _analyze_opportunity(
        self,
        token_address: str,
        dex_name: str,
        cex_name: str,
        dex_price: Decimal,
        cex_price: Decimal
    ) -> Optional[Dict]:
        """Analyse une opportunité d'arbitrage potentielle."""
        try:
            # Calculer la différence de prix
            price_diff = ((cex_price - dex_price) / dex_price) * Decimal('100')
            
            # Vérifier le seuil minimum de profit
            if abs(price_diff) < self.min_profit_threshold:
                return None
                
            # Vérifier la liquidité
            liquidity = await self._check_liquidity(token_address, dex_name)
            if not liquidity or liquidity < self.min_liquidity:
                return None
                
            # Estimer les frais de gas
            gas_cost = await self._estimate_gas_cost(token_address, dex_name)
            if not gas_cost:
                return None
                
            # Vérifier la rentabilité après frais
            profit_after_fees = self._calculate_profit_after_fees(
                price_diff,
                gas_cost,
                liquidity
            )
            
            if profit_after_fees <= 0:
                return None
                
            # Vérifier les protections anti-MEV
            if not await self._check_mev_protection(token_address, dex_name):
                return None
                
            return {
                "token_address": token_address,
                "dex_name": dex_name,
                "cex_name": cex_name,
                "dex_price": float(dex_price),
                "cex_price": float(cex_price),
                "price_difference": float(price_diff),
                "estimated_profit": float(profit_after_fees),
                "liquidity": str(liquidity),
                "gas_cost": str(gas_cost),
                "timestamp": asyncio.get_event_loop().time()
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse de l'opportunité: {str(e)}")
            return None
            
    async def _check_liquidity(self, token_address: str, dex_name: str) -> Optional[int]:
        """Vérifie la liquidité disponible sur le DEX."""
        try:
            contract_address = self.config["dex"][dex_name]["pair_address"]
            result = await self.rpc_manager.call_rpc(
                "getReserves",
                [],
                contract_address
            )
            if result and len(result) >= 2:
                return min(result[0], result[1])
        except Exception as e:
            logger.error(f"Erreur lors de la vérification de la liquidité: {str(e)}")
        return None
        
    async def _estimate_gas_cost(self, token_address: str, dex_name: str) -> Optional[int]:
        """Estime le coût en gas de la transaction."""
        try:
            # Récupérer le gas price actuel
            gas_price = await self.rpc_manager.call_rpc("eth_gasPrice", [])
            if not gas_price:
                return None
                
            # Estimer la limite de gas pour la transaction
            gas_limit = self.config["arbitrage"]["estimated_gas_limit"]
            
            return int(gas_price, 16) * gas_limit
            
        except Exception as e:
            logger.error(f"Erreur lors de l'estimation du gas: {str(e)}")
            return None
            
    def _calculate_profit_after_fees(
        self,
        price_diff: Decimal,
        gas_cost: int,
        liquidity: int
    ) -> Decimal:
        """Calcule le profit après prise en compte des frais."""
        try:
            # Convertir le gas cost en ETH
            gas_cost_eth = Decimal(str(gas_cost)) / Decimal(str(10**18))
            
            # Calculer le montant optimal de la transaction
            max_trade_amount = min(
                liquidity,
                Web3.to_wei(self.config["arbitrage"]["max_trade_amount"], 'ether')
            )
            
            # Calculer les frais de trading (DEX + CEX)
            dex_fee = Decimal('0.003')  # 0.3% pour Uniswap-like
            cex_fee = Decimal('0.001')  # 0.1% pour les CEX typiques
            
            # Calculer le profit brut
            trade_amount_eth = Decimal(str(max_trade_amount)) / Decimal(str(10**18))
            profit = (price_diff / Decimal('100')) * trade_amount_eth
            
            # Soustraire les frais
            total_fees = (trade_amount_eth * dex_fee) + (trade_amount_eth * cex_fee) + gas_cost_eth
            
            return profit - total_fees
            
        except Exception as e:
            logger.error(f"Erreur lors du calcul du profit: {str(e)}")
            return Decimal('0')
            
    async def _check_mev_protection(self, token_address: str, dex_name: str) -> bool:
        """Vérifie les protections contre les attaques MEV."""
        try:
            # Vérifier le nombre de transactions en attente pour ce token
            pending_txs = await self._get_pending_transactions(token_address)
            if pending_txs > self.config["arbitrage"]["max_pending_txs"]:
                logger.warning(f"Trop de transactions en attente pour {token_address}")
                return False
                
            # Vérifier les changements récents de prix
            price_volatility = await self._check_price_volatility(token_address, dex_name)
            if price_volatility > self.config["arbitrage"]["max_price_volatility"]:
                logger.warning(f"Volatilité trop élevée pour {token_address}")
                return False
                
            # Vérifier la présence de sandwiching
            if await self._detect_sandwich_attack(token_address, dex_name):
                logger.warning(f"Potentielle attaque sandwich détectée pour {token_address}")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la vérification MEV: {str(e)}")
            return False
            
    async def _get_pending_transactions(self, token_address: str) -> int:
        """Récupère le nombre de transactions en attente pour un token."""
        try:
            mempool = await self.rpc_manager.call_rpc("eth_getBlockByNumber", ["pending", True])
            if not mempool or "transactions" not in mempool:
                return 0
                
            count = 0
            for tx in mempool["transactions"]:
                if tx.get("to", "").lower() == token_address.lower():
                    count += 1
            return count
            
        except Exception as e:
            logger.error(f"Erreur lors de la vérification du mempool: {str(e)}")
            return 0
            
    async def _check_price_volatility(self, token_address: str, dex_name: str) -> Decimal:
        """Vérifie la volatilité récente des prix."""
        try:
            # Récupérer l'historique récent des prix
            price_history = await self._get_recent_prices(token_address, dex_name)
            if not price_history or len(price_history) < 2:
                return Decimal('0')
                
            # Calculer la volatilité
            max_price = max(price_history)
            min_price = min(price_history)
            avg_price = sum(price_history) / len(price_history)
            
            return ((max_price - min_price) / avg_price) * Decimal('100')
            
        except Exception as e:
            logger.error(f"Erreur lors du calcul de la volatilité: {str(e)}")
            return Decimal('0')
            
    async def _detect_sandwich_attack(self, token_address: str, dex_name: str) -> bool:
        """Détecte les potentielles attaques sandwich."""
        try:
            # Vérifier les transactions récentes
            recent_txs = await self._get_recent_transactions(token_address)
            if not recent_txs:
                return False
                
            # Analyser les patterns de transaction
            buy_count = 0
            sell_count = 0
            
            for tx in recent_txs:
                if self._is_buy_transaction(tx):
                    buy_count += 1
                elif self._is_sell_transaction(tx):
                    sell_count += 1
                    
            # Si on détecte un pattern suspect (achats/ventes rapprochés)
            return buy_count > 1 and sell_count > 1
            
        except Exception as e:
            logger.error(f"Erreur lors de la détection sandwich: {str(e)}")
            return False
            
    async def cleanup(self):
        """Nettoie les ressources utilisées."""
        await self.cex_manager.cleanup() 