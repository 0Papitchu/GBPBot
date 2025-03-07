#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module d'Arbitrage CEX-DEX pour GBPBot
=====================================

Ce module fournit des fonctionnalités pour détecter et exploiter les opportunités
d'arbitrage entre les plateformes centralisées (CEX) et décentralisées (DEX).
"""

import logging
import asyncio
import time
from typing import Dict, List, Any, Optional, Union, Tuple
from decimal import Decimal
from datetime import datetime, timedelta

from gbpbot.clients.cex_client_factory import CEXClientFactory
from gbpbot.clients.blockchain_client_factory import BlockchainClientFactory
from gbpbot.config.config_manager import config_manager
from gbpbot.utils.notification_manager import send_notification

# Configuration du logger
logger = logging.getLogger("gbpbot.modules.cex_dex_arbitrage")

class CEXDEXArbitrage:
    """
    Module d'arbitrage entre CEX et DEX.
    
    Cette classe implémente des stratégies pour détecter et exploiter les opportunités
    d'arbitrage entre les plateformes centralisées (CEX) et décentralisées (DEX).
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialise le module d'arbitrage CEX-DEX.
        
        Args:
            config: Configuration du module (optionnel)
        """
        logger.info("Initialisation du module d'arbitrage CEX-DEX")
        
        # Charger la configuration
        self.config = config or config_manager.get_config().get("arbitrage", {}).get("cex_dex", {})
        
        # État du module
        self.running = False
        self.monitoring_task = None
        self.stop_event = asyncio.Event()
        
        # Clients
        self.cex_clients = {}
        self.dex_clients = {}
        
        # Statistiques et suivi
        self.stats = {
            "opportunities_detected": 0,
            "trades_executed": 0,
            "successful_trades": 0,
            "failed_trades": 0,
            "total_profit": 0.0,
            "last_detection": None,
            "last_trade": None,
            "opportunities": []
        }
        
        # Paires à surveiller
        self.pairs = self.config.get("pairs", [])
        
        # Seuil de profit minimum
        self.min_profit_percentage = self.config.get("min_profit_percentage", 0.5)
        
        # Montant maximum par trade
        self.max_trade_amount = self.config.get("max_trade_amount", 100.0)
        
        # Intervalle de vérification
        self.check_interval = self.config.get("check_interval", 5)  # secondes
        
        # Initialiser les clients
        self._init_clients()
        
        logger.info("Module d'arbitrage CEX-DEX initialisé")
    
    def _init_clients(self):
        """
        Initialise les clients CEX et DEX.
        """
        # Initialiser les clients CEX
        for exchange in self.config.get("cex", []):
            try:
                client = CEXClientFactory.create_client(exchange)
                if client:
                    self.cex_clients[exchange] = client
                    logger.info(f"Client CEX {exchange} initialisé")
            except Exception as e:
                logger.error(f"Erreur lors de l'initialisation du client CEX {exchange}: {str(e)}")
        
        # Initialiser les clients DEX
        for blockchain in self.config.get("dex", []):
            try:
                client = BlockchainClientFactory.create_client(blockchain)
                if client:
                    self.dex_clients[blockchain] = client
                    logger.info(f"Client DEX {blockchain} initialisé")
            except Exception as e:
                logger.error(f"Erreur lors de l'initialisation du client DEX {blockchain}: {str(e)}")
    
    async def start(self):
        """
        Démarre le module d'arbitrage CEX-DEX.
        """
        if self.running:
            logger.warning("Le module d'arbitrage CEX-DEX est déjà en cours d'exécution")
            return
        
        logger.info("Démarrage du module d'arbitrage CEX-DEX")
        self.running = True
        self.stop_event.clear()
        
        # Démarrer la tâche de monitoring
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        # Notifier le démarrage
        send_notification(
            "info",
            "Arbitrage CEX-DEX",
            "Module d'arbitrage CEX-DEX démarré",
            {
                "cex": list(self.cex_clients.keys()),
                "dex": list(self.dex_clients.keys()),
                "pairs": self.pairs
            }
        )
        
        logger.info("Module d'arbitrage CEX-DEX démarré")
    
    async def stop(self):
        """
        Arrête le module d'arbitrage CEX-DEX.
        """
        if not self.running:
            logger.warning("Le module d'arbitrage CEX-DEX n'est pas en cours d'exécution")
            return
        
        logger.info("Arrêt du module d'arbitrage CEX-DEX")
        self.running = False
        self.stop_event.set()
        
        # Attendre la fin de la tâche de monitoring
        if self.monitoring_task:
            try:
                await asyncio.wait_for(self.monitoring_task, timeout=10)
            except asyncio.TimeoutError:
                logger.warning("Timeout lors de l'attente de la fin de la tâche de monitoring")
        
        # Notifier l'arrêt
        send_notification(
            "info",
            "Arbitrage CEX-DEX",
            "Module d'arbitrage CEX-DEX arrêté",
            {
                "stats": {
                    "opportunities_detected": self.stats["opportunities_detected"],
                    "trades_executed": self.stats["trades_executed"],
                    "successful_trades": self.stats["successful_trades"],
                    "total_profit": self.stats["total_profit"]
                }
            }
        )
        
        logger.info("Module d'arbitrage CEX-DEX arrêté")
    
    async def _monitoring_loop(self):
        """
        Boucle principale de surveillance des opportunités d'arbitrage.
        """
        logger.info("Démarrage de la boucle de surveillance des opportunités d'arbitrage")
        
        try:
            while not self.stop_event.is_set():
                # Vérifier les opportunités d'arbitrage
                await self._check_arbitrage_opportunities()
                
                # Attendre avant la prochaine vérification
                await asyncio.sleep(self.check_interval)
                
        except Exception as e:
            logger.error(f"Erreur dans la boucle de surveillance: {str(e)}")
        finally:
            logger.info("Boucle de surveillance des opportunités d'arbitrage terminée")
    
    async def _check_arbitrage_opportunities(self):
        """
        Vérifie les opportunités d'arbitrage entre CEX et DEX.
        """
        for pair in self.pairs:
            try:
                # Récupérer les prix sur les CEX
                cex_prices = await self._get_cex_prices(pair)
                
                # Récupérer les prix sur les DEX
                dex_prices = await self._get_dex_prices(pair)
                
                # Trouver les opportunités d'arbitrage
                opportunities = self._find_arbitrage_opportunities(pair, cex_prices, dex_prices)
                
                # Exécuter les opportunités rentables
                for opportunity in opportunities:
                    if opportunity["profit_percentage"] >= self.min_profit_percentage:
                        self.stats["opportunities_detected"] += 1
                        self.stats["last_detection"] = datetime.now()
                        self.stats["opportunities"].append(opportunity)
                        
                        # Limiter la liste des opportunités à 100 éléments
                        if len(self.stats["opportunities"]) > 100:
                            self.stats["opportunities"] = self.stats["opportunities"][-100:]
                        
                        # Notifier l'opportunité
                        send_notification(
                            "info",
                            "Opportunité d'arbitrage",
                            f"Opportunité d'arbitrage détectée: {opportunity['profit_percentage']:.2f}%",
                            opportunity
                        )
                        
                        # Exécuter l'arbitrage si activé
                        if self.config.get("auto_execute", False):
                            await self._execute_arbitrage(opportunity)
                
            except Exception as e:
                logger.error(f"Erreur lors de la vérification des opportunités d'arbitrage pour {pair}: {str(e)}")
    
    async def _get_cex_prices(self, pair: str) -> Dict[str, Decimal]:
        """
        Récupère les prix d'un pair sur les CEX.
        
        Args:
            pair: Paire de trading (ex: BTC/USDT)
            
        Returns:
            Dictionnaire des prix par CEX
        """
        prices = {}
        
        for exchange, client in self.cex_clients.items():
            try:
                ticker = await client.get_ticker(pair)
                prices[exchange] = {
                    "bid": ticker["bid"],
                    "ask": ticker["ask"],
                    "last": ticker["last"]
                }
            except Exception as e:
                logger.warning(f"Erreur lors de la récupération du prix sur {exchange} pour {pair}: {str(e)}")
        
        return prices
    
    async def _get_dex_prices(self, pair: str) -> Dict[str, Decimal]:
        """
        Récupère les prix d'un pair sur les DEX.
        
        Args:
            pair: Paire de trading (ex: BTC/USDT)
            
        Returns:
            Dictionnaire des prix par DEX
        """
        prices = {}
        
        # Extraire les tokens de la paire
        tokens = pair.split("/")
        if len(tokens) != 2:
            logger.warning(f"Format de paire invalide: {pair}")
            return prices
        
        base_token, quote_token = tokens
        
        for blockchain, client in self.dex_clients.items():
            try:
                # Récupérer les adresses des tokens sur cette blockchain
                base_address = self._get_token_address(blockchain, base_token)
                quote_address = self._get_token_address(blockchain, quote_token)
                
                if not base_address or not quote_address:
                    logger.warning(f"Adresses de tokens non trouvées pour {pair} sur {blockchain}")
                    continue
                
                # Récupérer le prix
                price = await client.get_token_price(base_address, quote_address)
                
                # Simuler un bid et un ask (à remplacer par la vraie logique)
                bid = price * Decimal("0.995")  # -0.5%
                ask = price * Decimal("1.005")  # +0.5%
                
                prices[blockchain] = {
                    "bid": bid,
                    "ask": ask,
                    "last": price
                }
            except Exception as e:
                logger.warning(f"Erreur lors de la récupération du prix sur {blockchain} pour {pair}: {str(e)}")
        
        return prices
    
    def _get_token_address(self, blockchain: str, token: str) -> Optional[str]:
        """
        Récupère l'adresse d'un token sur une blockchain.
        
        Args:
            blockchain: Nom de la blockchain
            token: Symbole du token
            
        Returns:
            Adresse du token ou None si non trouvée
        """
        # Récupérer les adresses depuis la configuration
        token_addresses = self.config.get("token_addresses", {})
        blockchain_addresses = token_addresses.get(blockchain, {})
        
        return blockchain_addresses.get(token)
    
    def _find_arbitrage_opportunities(
        self,
        pair: str,
        cex_prices: Dict[str, Dict[str, Decimal]],
        dex_prices: Dict[str, Dict[str, Decimal]]
    ) -> List[Dict[str, Any]]:
        """
        Trouve les opportunités d'arbitrage entre CEX et DEX.
        
        Args:
            pair: Paire de trading
            cex_prices: Prix sur les CEX
            dex_prices: Prix sur les DEX
            
        Returns:
            Liste des opportunités d'arbitrage
        """
        opportunities = []
        
        # Vérifier les opportunités CEX -> DEX
        for cex, cex_price in cex_prices.items():
            for dex, dex_price in dex_prices.items():
                # Opportunité d'achat sur CEX et vente sur DEX
                if cex_price["ask"] < dex_price["bid"]:
                    profit_percentage = (dex_price["bid"] / cex_price["ask"] - 1) * 100
                    
                    opportunity = {
                        "pair": pair,
                        "type": "cex_to_dex",
                        "buy": {
                            "platform": cex,
                            "price": cex_price["ask"]
                        },
                        "sell": {
                            "platform": dex,
                            "price": dex_price["bid"]
                        },
                        "profit_percentage": profit_percentage,
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    opportunities.append(opportunity)
                
                # Opportunité d'achat sur DEX et vente sur CEX
                if dex_price["ask"] < cex_price["bid"]:
                    profit_percentage = (cex_price["bid"] / dex_price["ask"] - 1) * 100
                    
                    opportunity = {
                        "pair": pair,
                        "type": "dex_to_cex",
                        "buy": {
                            "platform": dex,
                            "price": dex_price["ask"]
                        },
                        "sell": {
                            "platform": cex,
                            "price": cex_price["bid"]
                        },
                        "profit_percentage": profit_percentage,
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    opportunities.append(opportunity)
        
        # Trier par profit décroissant
        opportunities.sort(key=lambda x: x["profit_percentage"], reverse=True)
        
        return opportunities
    
    async def _execute_arbitrage(self, opportunity: Dict[str, Any]) -> bool:
        """
        Exécute une opportunité d'arbitrage.
        
        Args:
            opportunity: Opportunité d'arbitrage à exécuter
            
        Returns:
            True si l'arbitrage a réussi, False sinon
        """
        logger.info(f"Exécution de l'arbitrage: {opportunity}")
        
        # Mettre à jour les statistiques
        self.stats["trades_executed"] += 1
        self.stats["last_trade"] = datetime.now()
        
        try:
            # Extraire les informations
            pair = opportunity["pair"]
            buy_platform = opportunity["buy"]["platform"]
            buy_price = opportunity["buy"]["price"]
            sell_platform = opportunity["sell"]["platform"]
            sell_price = opportunity["sell"]["price"]
            
            # Calculer le montant à trader
            amount = self._calculate_trade_amount(opportunity)
            
            # Exécuter l'achat
            buy_success = await self._execute_buy(buy_platform, pair, amount, buy_price)
            if not buy_success:
                logger.error(f"Échec de l'achat sur {buy_platform}")
                return False
            
            # Exécuter la vente
            sell_success = await self._execute_sell(sell_platform, pair, amount, sell_price)
            if not sell_success:
                logger.error(f"Échec de la vente sur {sell_platform}")
                return False
            
            # Calculer le profit
            profit = (sell_price - buy_price) * amount
            
            # Mettre à jour les statistiques
            self.stats["successful_trades"] += 1
            self.stats["total_profit"] += float(profit)
            
            # Notifier le succès
            send_notification(
                "success",
                "Arbitrage réussi",
                f"Arbitrage réussi: {opportunity['profit_percentage']:.2f}%",
                {
                    "opportunity": opportunity,
                    "amount": float(amount),
                    "profit": float(profit)
                }
            )
            
            logger.info(f"Arbitrage réussi: {opportunity['profit_percentage']:.2f}%, profit: {profit}")
            return True
            
        except Exception as e:
            # Mettre à jour les statistiques
            self.stats["failed_trades"] += 1
            
            # Notifier l'échec
            send_notification(
                "error",
                "Échec de l'arbitrage",
                f"Échec de l'arbitrage: {str(e)}",
                {
                    "opportunity": opportunity,
                    "error": str(e)
                }
            )
            
            logger.error(f"Erreur lors de l'exécution de l'arbitrage: {str(e)}")
            return False
    
    def _calculate_trade_amount(self, opportunity: Dict[str, Any]) -> Decimal:
        """
        Calcule le montant à trader pour une opportunité d'arbitrage.
        
        Args:
            opportunity: Opportunité d'arbitrage
            
        Returns:
            Montant à trader
        """
        # Récupérer les paramètres
        pair = opportunity["pair"]
        profit_percentage = opportunity["profit_percentage"]
        
        # Récupérer le montant configuré pour cette paire
        pair_config = next((p for p in self.config.get("pair_configs", []) if p["pair"] == pair), None)
        
        if pair_config:
            base_amount = Decimal(str(pair_config.get("amount", self.max_trade_amount)))
        else:
            base_amount = Decimal(str(self.max_trade_amount))
        
        # Ajuster le montant en fonction du profit
        if profit_percentage > 5.0:
            # Profit élevé, utiliser le montant maximum
            amount = base_amount
        elif profit_percentage > 2.0:
            # Profit moyen, utiliser 75% du montant
            amount = base_amount * Decimal("0.75")
        elif profit_percentage > 1.0:
            # Profit faible, utiliser 50% du montant
            amount = base_amount * Decimal("0.5")
        else:
            # Profit très faible, utiliser 25% du montant
            amount = base_amount * Decimal("0.25")
        
        return amount
    
    async def _execute_buy(
        self,
        platform: str,
        pair: str,
        amount: Decimal,
        price: Decimal
    ) -> bool:
        """
        Exécute un achat sur une plateforme.
        
        Args:
            platform: Plateforme d'achat
            pair: Paire de trading
            amount: Montant à acheter
            price: Prix d'achat
            
        Returns:
            True si l'achat a réussi, False sinon
        """
        logger.info(f"Exécution de l'achat sur {platform} pour {pair}: {amount} @ {price}")
        
        try:
            # Vérifier si la plateforme est un CEX ou un DEX
            if platform in self.cex_clients:
                # Achat sur CEX
                client = self.cex_clients[platform]
                order = await client.create_order(
                    symbol=pair,
                    order_type="limit",
                    side="buy",
                    amount=amount,
                    price=price
                )
                
                # Vérifier si l'ordre a été exécuté
                if order["status"] in ["closed", "filled"]:
                    logger.info(f"Achat réussi sur {platform}: {order}")
                    return True
                else:
                    logger.warning(f"Ordre d'achat non exécuté sur {platform}: {order}")
                    return False
                
            elif platform in self.dex_clients:
                # Achat sur DEX
                client = self.dex_clients[platform]
                
                # Extraire les tokens de la paire
                tokens = pair.split("/")
                if len(tokens) != 2:
                    logger.warning(f"Format de paire invalide: {pair}")
                    return False
                
                base_token, quote_token = tokens
                
                # Récupérer les adresses des tokens
                base_address = self._get_token_address(platform, base_token)
                quote_address = self._get_token_address(platform, quote_token)
                
                if not base_address or not quote_address:
                    logger.warning(f"Adresses de tokens non trouvées pour {pair} sur {platform}")
                    return False
                
                # Calculer le montant d'entrée (en quote_token)
                amount_in = amount * price
                
                # Exécuter le swap
                tx_hash = await client.swap_tokens(
                    token_in=quote_address,
                    token_out=base_address,
                    amount_in=int(amount_in * Decimal("1e18")),  # Convertir en wei
                    min_amount_out=int(amount * Decimal("0.99") * Decimal("1e18"))  # 1% de slippage
                )
                
                if tx_hash:
                    logger.info(f"Achat réussi sur {platform}: {tx_hash}")
                    return True
                else:
                    logger.warning(f"Échec de l'achat sur {platform}")
                    return False
            else:
                logger.warning(f"Plateforme inconnue: {platform}")
                return False
                
        except Exception as e:
            logger.error(f"Erreur lors de l'exécution de l'achat sur {platform}: {str(e)}")
            return False
    
    async def _execute_sell(
        self,
        platform: str,
        pair: str,
        amount: Decimal,
        price: Decimal
    ) -> bool:
        """
        Exécute une vente sur une plateforme.
        
        Args:
            platform: Plateforme de vente
            pair: Paire de trading
            amount: Montant à vendre
            price: Prix de vente
            
        Returns:
            True si la vente a réussi, False sinon
        """
        logger.info(f"Exécution de la vente sur {platform} pour {pair}: {amount} @ {price}")
        
        try:
            # Vérifier si la plateforme est un CEX ou un DEX
            if platform in self.cex_clients:
                # Vente sur CEX
                client = self.cex_clients[platform]
                order = await client.create_order(
                    symbol=pair,
                    order_type="limit",
                    side="sell",
                    amount=amount,
                    price=price
                )
                
                # Vérifier si l'ordre a été exécuté
                if order["status"] in ["closed", "filled"]:
                    logger.info(f"Vente réussie sur {platform}: {order}")
                    return True
                else:
                    logger.warning(f"Ordre de vente non exécuté sur {platform}: {order}")
                    return False
                
            elif platform in self.dex_clients:
                # Vente sur DEX
                client = self.dex_clients[platform]
                
                # Extraire les tokens de la paire
                tokens = pair.split("/")
                if len(tokens) != 2:
                    logger.warning(f"Format de paire invalide: {pair}")
                    return False
                
                base_token, quote_token = tokens
                
                # Récupérer les adresses des tokens
                base_address = self._get_token_address(platform, base_token)
                quote_address = self._get_token_address(platform, quote_token)
                
                if not base_address or not quote_address:
                    logger.warning(f"Adresses de tokens non trouvées pour {pair} sur {platform}")
                    return False
                
                # Calculer le montant minimum de sortie (en quote_token)
                min_amount_out = amount * price * Decimal("0.99")  # 1% de slippage
                
                # Exécuter le swap
                tx_hash = await client.swap_tokens(
                    token_in=base_address,
                    token_out=quote_address,
                    amount_in=int(amount * Decimal("1e18")),  # Convertir en wei
                    min_amount_out=int(min_amount_out * Decimal("1e18"))  # Convertir en wei
                )
                
                if tx_hash:
                    logger.info(f"Vente réussie sur {platform}: {tx_hash}")
                    return True
                else:
                    logger.warning(f"Échec de la vente sur {platform}")
                    return False
            else:
                logger.warning(f"Plateforme inconnue: {platform}")
                return False
                
        except Exception as e:
            logger.error(f"Erreur lors de l'exécution de la vente sur {platform}: {str(e)}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Récupère les statistiques du module d'arbitrage CEX-DEX.
        
        Returns:
            Statistiques du module
        """
        # Ajouter les statistiques dynamiques
        stats = self.stats.copy()
        
        # Calculer le taux de réussite
        if stats["trades_executed"] > 0:
            stats["success_rate"] = (stats["successful_trades"] / stats["trades_executed"]) * 100
        else:
            stats["success_rate"] = 0
        
        # Calculer le profit moyen par trade
        if stats["successful_trades"] > 0:
            stats["avg_profit_per_trade"] = stats["total_profit"] / stats["successful_trades"]
        else:
            stats["avg_profit_per_trade"] = 0
        
        return stats 