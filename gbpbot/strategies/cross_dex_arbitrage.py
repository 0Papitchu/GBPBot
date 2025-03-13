"""
Module d'arbitrage cross-DEX pour GBPBot
========================================

Ce module implémente une stratégie d'arbitrage entre différents DEX
sur une même blockchain, permettant de profiter des écarts de prix
en exécutant des transactions optimisées.
"""

import asyncio
import logging
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import json
import os

from gbpbot.core.blockchain import BlockchainClient
from gbpbot.core.price_feed import PriceManager
from gbpbot.core.opportunity_analyzer import OpportunityAnalyzer
from gbpbot.core.performance_tracker import PerformanceTracker
from gbpbot.utils.config_utils import load_config

logger = logging.getLogger(__name__)

@dataclass
class ArbitrageConfig:
    """Configuration pour la stratégie d'arbitrage cross-DEX."""
    # Seuils de profitabilité
    min_profit_threshold_percent: float = 0.5  # Profit minimum en pourcentage pour exécuter
    min_profit_absolute: float = 0.05  # Profit minimum en AVAX/SOL/ETH
    
    # Limites de transaction
    max_input_amount: float = 2.0  # Montant maximum à utiliser par transaction
    min_input_amount: float = 0.1  # Montant minimum à utiliser par transaction
    
    # Contrôle du risque
    max_slippage_percent: float = 0.5  # Slippage maximum autorisé
    
    # Optimisation des transactions
    gas_boost_percent: float = 10.0  # Boost de gas pour passer en priorité
    
    # Contrôle d'exécution
    check_interval_seconds: float = 3.0  # Intervalle entre les vérifications
    execution_timeout_seconds: float = 30.0  # Timeout pour l'exécution de l'arbitrage
    
    # DEX supportés par blockchain
    supported_dex_pairs: Dict[str, List[Tuple[str, str]]] = None
    
    # Tokens à surveiller
    watchlist: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Initialise les valeurs par défaut pour les listes et dictionnaires."""
        if self.supported_dex_pairs is None:
            self.supported_dex_pairs = {
                "avax": [
                    ("traderjoe", "pangolin"),
                    ("traderjoe", "sushiswap"),
                    ("pangolin", "sushiswap")
                ],
                "solana": [
                    ("raydium", "orca"),
                    ("raydium", "serum"),
                    ("orca", "serum")
                ]
            }
            
        if self.watchlist is None:
            self.watchlist = []


class CrossDEXArbitrageStrategy:
    """
    Stratégie d'arbitrage entre différents DEX sur une même blockchain.
    Elle détecte et exploite les écarts de prix entre les DEX pour
    générer des profits.
    """
    
    def __init__(self, blockchain_client: BlockchainClient, config: Optional[Dict[str, Any]] = None):
        """
        Initialise la stratégie d'arbitrage cross-DEX.
        
        Args:
            blockchain_client: Client blockchain pour les interactions
            config: Configuration pour la stratégie
        """
        self.blockchain = blockchain_client
        
        # Charger la configuration
        raw_config = config or {}
        self.config = ArbitrageConfig(
            min_profit_threshold_percent=raw_config.get("min_profit_threshold_percent", 0.5),
            min_profit_absolute=raw_config.get("min_profit_absolute", 0.05),
            max_input_amount=raw_config.get("max_input_amount", 2.0),
            min_input_amount=raw_config.get("min_input_amount", 0.1),
            max_slippage_percent=raw_config.get("max_slippage_percent", 0.5),
            gas_boost_percent=raw_config.get("gas_boost_percent", 10.0),
            check_interval_seconds=raw_config.get("check_interval_seconds", 3.0),
            execution_timeout_seconds=raw_config.get("execution_timeout_seconds", 30.0),
            supported_dex_pairs=raw_config.get("supported_dex_pairs"),
            watchlist=raw_config.get("watchlist", [])
        )
        
        # Initialiser le gestionnaire de prix
        self.price_manager = PriceManager(self.blockchain)
        
        # Initialiser l'analyseur d'opportunités
        self.opportunity_analyzer = OpportunityAnalyzer()
        
        # Initialiser le tracker de performance
        self.performance_tracker = PerformanceTracker()
        
        # Données internes
        self.running = False
        self.paused = False
        self.last_check_time = 0
        self.opportunities_found = 0
        self.arbitrages_executed = 0
        self.successful_arbitrages = 0
        self.total_profit = 0.0
        
        # Cache de prix
        self.price_cache = {}
        self.price_cache_time = {}
        self.price_cache_max_age = 10  # secondes
        
        # File des opportunités détectées
        self.opportunity_queue = asyncio.Queue()
        
        # Historique d'exécution
        self.execution_history = []
        
        logger.info("CrossDEXArbitrageStrategy initialisée")
    
    async def start(self):
        """Démarre la stratégie d'arbitrage."""
        if self.running:
            logger.warning("La stratégie est déjà en cours d'exécution")
            return
            
        self.running = True
        self.paused = False
        logger.info("Démarrage de la stratégie d'arbitrage cross-DEX")
        
        # Démarrer les routines asynchrones
        asyncio.create_task(self._monitoring_loop())
        asyncio.create_task(self._execution_loop())
        
        logger.info("Stratégie d'arbitrage cross-DEX démarrée")
    
    async def stop(self):
        """Arrête la stratégie d'arbitrage."""
        if not self.running:
            return
            
            self.running = False
        logger.info("Arrêt de la stratégie d'arbitrage cross-DEX")
        
        # Attendre que les files soient vides
        if not self.opportunity_queue.empty():
            logger.info("Attente de traitement des opportunités restantes...")
            try:
                await asyncio.wait_for(self.opportunity_queue.join(), timeout=10.0)
            except asyncio.TimeoutError:
                logger.warning("Timeout en attendant la fin du traitement des opportunités")
        
        logger.info("Stratégie d'arbitrage cross-DEX arrêtée")
    
    async def pause(self):
        """Met en pause la stratégie d'arbitrage."""
        if not self.running:
            return
            
        self.paused = True
        logger.info("Stratégie d'arbitrage cross-DEX mise en pause")
    
    async def resume(self):
        """Reprend la stratégie d'arbitrage après une pause."""
        if not self.running or not self.paused:
            return
            
        self.paused = False
        logger.info("Stratégie d'arbitrage cross-DEX reprise")
    
    async def _monitoring_loop(self):
        """Boucle principale pour la recherche d'opportunités d'arbitrage."""
        while self.running:
            try:
                if not self.paused:
                    # Vérifier si l'intervalle minimum est passé
                    current_time = time.time()
                    if current_time - self.last_check_time >= self.config.check_interval_seconds:
                        self.last_check_time = current_time
                        
                        # Rechercher des opportunités d'arbitrage
                        await self._check_arbitrage_opportunities()
                
            except Exception as e:
                logger.error(f"Erreur dans la boucle de surveillance: {e}")
                
            # Attendre avant la prochaine vérification
            await asyncio.sleep(0.5)
    
    async def _execution_loop(self):
        """Boucle d'exécution des opportunités d'arbitrage détectées."""
        while self.running:
            try:
                # Récupérer une opportunité de la file
                opportunity = await self.opportunity_queue.get()
                
                try:
                    # Vérifier que l'opportunité est toujours valide
                    if await self._validate_opportunity(opportunity):
                        # Exécuter l'arbitrage
                        success, profit = await self._execute_arbitrage(opportunity)
                        
                        if success:
                            self.successful_arbitrages += 1
                            self.total_profit += profit
                            logger.info(f"Arbitrage réussi! Profit: {profit:.6f}")
                        else:
                            logger.warning("Échec de l'arbitrage")
                            
                        self.arbitrages_executed += 1
                    else:
                        logger.info("Opportunité d'arbitrage non valide, ignorée")
                        
                except Exception as e:
                    logger.error(f"Erreur lors de l'exécution de l'arbitrage: {e}")
                    
                finally:
                    # Marquer la tâche comme terminée
                    self.opportunity_queue.task_done()
            
        except Exception as e:
                logger.error(f"Erreur dans la boucle d'exécution: {e}")
                
            # Petite pause pour éviter de surcharger le CPU
            await asyncio.sleep(0.1)
    
    async def _check_arbitrage_opportunities(self):
        """Vérifie les opportunités d'arbitrage pour toutes les paires configurées."""
        # Récupérer les paires à surveiller pour la blockchain actuelle
        blockchain_name = self.blockchain.get_blockchain_name().lower()
        dex_pairs = self.config.supported_dex_pairs.get(blockchain_name, [])
        
        if not dex_pairs:
            logger.warning(f"Aucune paire de DEX configurée pour {blockchain_name}")
            return
            
        # Vérifier chaque paire de DEX
        for dex1, dex2 in dex_pairs:
            # Vérifier les tokens de la watchlist
            for token_info in self.config.watchlist:
                token_address = token_info.get("address")
                base_token = token_info.get("base_token", "WAVAX" if blockchain_name == "avax" else "WSOL")
                
                if not token_address:
                    continue
                
                # Récupérer les prix sur les deux DEX
                price1 = await self._get_token_price(token_address, base_token, dex1)
                price2 = await self._get_token_price(token_address, base_token, dex2)
                
                if not price1 or not price2:
                    continue
                    
                # Calculer les opportunités d'arbitrage
                await self._analyze_price_difference(token_address, base_token, dex1, dex2, price1, price2)
    
    async def _analyze_price_difference(self, token_address: str, base_token: str, 
                                       dex1: str, dex2: str, price1: float, price2: float):
        """
        Analyse les différences de prix et détecte les opportunités d'arbitrage.
        
        Args:
            token_address: Adresse du token
            base_token: Token de base (WAVAX, WSOL, etc.)
            dex1: Premier DEX
            dex2: Deuxième DEX
            price1: Prix sur le premier DEX
            price2: Prix sur le deuxième DEX
        """
        # Calculer la différence de prix en pourcentage
        if price1 <= 0 or price2 <= 0:
            return
            
        # Calculer les directions d'arbitrage possibles
        if price1 < price2:
            # Acheter sur dex1, vendre sur dex2
            price_diff_percent = (price2 - price1) / price1 * 100
            direction = f"{dex1} -> {dex2}"
            buy_dex = dex1
            sell_dex = dex2
            buy_price = price1
            sell_price = price2
        else:
            # Acheter sur dex2, vendre sur dex1
            price_diff_percent = (price1 - price2) / price2 * 100
            direction = f"{dex2} -> {dex1}"
            buy_dex = dex2
            sell_dex = dex1
            buy_price = price2
            sell_price = price1
        
        # Vérifier si la différence de prix dépasse le seuil minimal
        if price_diff_percent < self.config.min_profit_threshold_percent:
            return
            
        # Estimer les frais (gas, slippage, frais de DEX)
        base_token_price_usd = await self._get_base_token_price_usd(base_token)
        transaction_amount = min(self.config.max_input_amount, 
                               max(self.config.min_input_amount, self.total_profit * 0.2 + 0.1))
        
        # Estimation des coûts
        estimated_gas_cost = await self._estimate_gas_cost(token_address, base_token, transaction_amount)
        dex_fees = (transaction_amount * buy_price * 0.003) + (transaction_amount * buy_price * 0.003)  # 0.3% sur chaque DEX
        slippage_cost = transaction_amount * buy_price * (self.config.max_slippage_percent / 100)
        
        total_costs = estimated_gas_cost + dex_fees + slippage_cost
        
        # Calculer le profit estimé
        gross_profit = transaction_amount * buy_price * (price_diff_percent / 100)
        net_profit = gross_profit - total_costs
        
        # Vérifier si le profit est suffisant
        if net_profit < self.config.min_profit_absolute:
            return
            
        # Créer l'opportunité d'arbitrage
        opportunity = {
            "token_address": token_address,
            "base_token": base_token,
            "buy_dex": buy_dex,
            "sell_dex": sell_dex,
            "buy_price": buy_price,
            "sell_price": sell_price,
            "price_diff_percent": price_diff_percent,
            "transaction_amount": transaction_amount,
            "estimated_gas_cost": estimated_gas_cost,
            "dex_fees": dex_fees,
            "slippage_cost": slippage_cost,
            "gross_profit": gross_profit,
            "net_profit": net_profit,
            "timestamp": time.time(),
            "direction": direction
        }
        
        # Ajouter l'opportunité à la file d'exécution
        self.opportunities_found += 1
        await self.opportunity_queue.put(opportunity)
        
        logger.info(f"Opportunité d'arbitrage détectée: {direction}, différence: {price_diff_percent:.2f}%, profit estimé: {net_profit:.6f}")
    
    async def _validate_opportunity(self, opportunity: Dict[str, Any]) -> bool:
        """
        Valide qu'une opportunité est toujours profitable avant exécution.
        
        Args:
            opportunity: Opportunité à valider
            
        Returns:
            True si l'opportunité est toujours valide, False sinon
        """
        # Vérifier si l'opportunité n'est pas trop ancienne
        if time.time() - opportunity["timestamp"] > 10:
            logger.warning("Opportunité trop ancienne, validation échouée")
            return False
            
        # Revérifier les prix pour s'assurer que l'opportunité existe toujours
        token_address = opportunity["token_address"]
        base_token = opportunity["base_token"]
        buy_dex = opportunity["buy_dex"]
        sell_dex = opportunity["sell_dex"]
        
        # Récupérer les prix actuels
        current_buy_price = await self._get_token_price(token_address, base_token, buy_dex, cache=False)
        current_sell_price = await self._get_token_price(token_address, base_token, sell_dex, cache=False)
        
        if not current_buy_price or not current_sell_price:
            logger.warning("Impossible de récupérer les prix actuels, validation échouée")
            return False
            
        # Calculer la différence de prix actuelle
        current_price_diff = (current_sell_price - current_buy_price) / current_buy_price * 100
        
        # Vérifier si la différence de prix est toujours suffisante
        if current_price_diff < self.config.min_profit_threshold_percent:
            logger.warning(f"Différence de prix insuffisante: {current_price_diff:.2f}% < {self.config.min_profit_threshold_percent:.2f}%")
            return False
            
        # Recalculer le profit estimé
        transaction_amount = opportunity["transaction_amount"]
        estimated_gas_cost = opportunity["estimated_gas_cost"]
        
        current_gross_profit = transaction_amount * current_buy_price * (current_price_diff / 100)
        dex_fees = (transaction_amount * current_buy_price * 0.003) + (transaction_amount * current_buy_price * 0.003)
        slippage_cost = transaction_amount * current_buy_price * (self.config.max_slippage_percent / 100)
        
        current_net_profit = current_gross_profit - estimated_gas_cost - dex_fees - slippage_cost
        
        # Vérifier si le profit est toujours suffisant
        if current_net_profit < self.config.min_profit_absolute:
            logger.warning(f"Profit net insuffisant: {current_net_profit:.6f} < {self.config.min_profit_absolute:.6f}")
            return False
            
        # Mettre à jour l'opportunité avec les valeurs actuelles
        opportunity["buy_price"] = current_buy_price
        opportunity["sell_price"] = current_sell_price
        opportunity["price_diff_percent"] = current_price_diff
        opportunity["gross_profit"] = current_gross_profit
        opportunity["net_profit"] = current_net_profit
        
        return True
    
    async def _execute_arbitrage(self, opportunity: Dict[str, Any]) -> Tuple[bool, float]:
        """
        Exécute un arbitrage en fonction de l'opportunité détectée.
        
        Args:
            opportunity: Opportunité d'arbitrage à exécuter
            
        Returns:
            Tuple contenant le succès de l'arbitrage et le profit réalisé
        """
        token_address = opportunity["token_address"]
        base_token = opportunity["base_token"]
        buy_dex = opportunity["buy_dex"]
        sell_dex = opportunity["sell_dex"]
        amount = opportunity["transaction_amount"]
        
        # Enregistrer le début de l'exécution
        execution_start = time.time()
        
        try:
            # Étape 1: Achat sur le DEX moins cher
            logger.info(f"Achat de {amount} {base_token} de {token_address} sur {buy_dex}")
            buy_tx = await self.blockchain.swap_tokens(
                from_token=base_token,
                to_token=token_address,
                amount=amount,
                dex=buy_dex,
                slippage_percent=self.config.max_slippage_percent,
                gas_boost_percent=self.config.gas_boost_percent
            )
            
            if not buy_tx or not buy_tx.get("success"):
                logger.error(f"Échec de l'achat: {buy_tx.get('error', 'Raison inconnue')}")
                return False, 0
                
            # Récupérer le montant de tokens reçus
            tokens_received = buy_tx.get("tokens_received", 0)
            actual_buy_price = amount / tokens_received if tokens_received > 0 else 0
            
            if tokens_received <= 0:
                logger.error("Aucun token reçu lors de l'achat")
                return False, 0
                
            logger.info(f"Achat réussi, tokens reçus: {tokens_received}")
            
            # Étape 2: Vente sur le DEX plus cher
            logger.info(f"Vente de {tokens_received} {token_address} sur {sell_dex}")
            sell_tx = await self.blockchain.swap_tokens(
                from_token=token_address,
                to_token=base_token,
                amount=tokens_received,
                dex=sell_dex,
                slippage_percent=self.config.max_slippage_percent,
                gas_boost_percent=self.config.gas_boost_percent
            )
            
            if not sell_tx or not sell_tx.get("success"):
                logger.error(f"Échec de la vente: {sell_tx.get('error', 'Raison inconnue')}")
                return False, 0
                
            # Récupérer le montant de base_token reçus
            base_tokens_received = sell_tx.get("tokens_received", 0)
            actual_sell_price = base_tokens_received / tokens_received if tokens_received > 0 else 0
            
            # Calculer le profit réel
            actual_profit = base_tokens_received - amount
            
            # Calculer les coûts réels
            buy_gas_cost = buy_tx.get("gas_cost", 0)
            sell_gas_cost = sell_tx.get("gas_cost", 0)
            total_gas_cost = buy_gas_cost + sell_gas_cost
            
            # Profit net
            net_profit = actual_profit - total_gas_cost
            
            # Enregistrer l'exécution dans l'historique
            execution_time = time.time() - execution_start
            execution_record = {
                "timestamp": time.time(),
                "token_address": token_address,
                "base_token": base_token,
                "buy_dex": buy_dex,
                "sell_dex": sell_dex,
                "amount": amount,
                "tokens_received": tokens_received,
                "base_tokens_received": base_tokens_received,
                "estimated_profit": opportunity["net_profit"],
                "actual_profit": actual_profit,
                "gas_cost": total_gas_cost,
                "net_profit": net_profit,
                "execution_time": execution_time,
                "buy_tx_hash": buy_tx.get("tx_hash"),
                "sell_tx_hash": sell_tx.get("tx_hash")
            }
            
            self.execution_history.append(execution_record)
            
            # Si l'historique devient trop grand, supprimer les entrées les plus anciennes
            if len(self.execution_history) > 100:
                self.execution_history = self.execution_history[-100:]
                
            # Enregistrer les performances
            self.performance_tracker.record_arbitrage(
                token_address=token_address,
                base_token=base_token,
                buy_dex=buy_dex,
                sell_dex=sell_dex,
                price_diff_percent=opportunity["price_diff_percent"],
                estimated_profit=opportunity["net_profit"],
                actual_profit=net_profit,
                execution_time=execution_time,
                success=True
            )
            
            logger.info(f"Arbitrage réussi! Profit net: {net_profit:.6f} {base_token}")
            return True, net_profit
            
        except Exception as e:
            logger.error(f"Erreur lors de l'exécution de l'arbitrage: {e}")
            
            # Enregistrer l'échec
            self.performance_tracker.record_arbitrage(
                token_address=token_address,
                base_token=base_token,
                buy_dex=buy_dex,
                sell_dex=sell_dex,
                price_diff_percent=opportunity["price_diff_percent"],
                estimated_profit=opportunity["net_profit"],
                actual_profit=0,
                execution_time=time.time() - execution_start,
                success=False,
                error=str(e)
            )
            
            return False, 0
    
    async def _get_token_price(self, token_address: str, base_token: str, dex: str, cache: bool = True) -> Optional[float]:
        """
        Récupère le prix d'un token sur un DEX spécifique.
        
        Args:
            token_address: Adresse du token
            base_token: Token de base (WAVAX, WSOL, etc.)
            dex: DEX sur lequel récupérer le prix
            cache: Utiliser le cache si disponible
            
        Returns:
            Prix du token ou None si non disponible
        """
        cache_key = f"{token_address}_{base_token}_{dex}"
        
        # Vérifier le cache si activé
        if cache and cache_key in self.price_cache:
            cache_time = self.price_cache_time.get(cache_key, 0)
            if time.time() - cache_time < self.price_cache_max_age:
                return self.price_cache[cache_key]
        
        try:
            # Récupérer le prix depuis le manager de prix
            price = await self.price_manager.get_token_price(token_address, base_token, dex)
            
            # Mettre à jour le cache
            if price is not None:
                self.price_cache[cache_key] = price
                self.price_cache_time[cache_key] = time.time()
                
            return price
            
        except Exception as e:
            logger.warning(f"Erreur lors de la récupération du prix {token_address} sur {dex}: {e}")
            return None
    
    async def _get_base_token_price_usd(self, base_token: str) -> float:
        """
        Récupère le prix en USD du token de base.
        
        Args:
            base_token: Token de base (WAVAX, WSOL, etc.)
        
        Returns:
            Prix en USD du token de base
        """
        try:
            # Essayer différents DEX pour obtenir le prix USD
            blockchain_name = self.blockchain.get_blockchain_name().lower()
            dex_pairs = self.config.supported_dex_pairs.get(blockchain_name, [])
            
            if not dex_pairs:
                return 0
                
            # Essayer le premier DEX disponible
            price = await self.price_manager.get_token_price_usd(base_token, dex_pairs[0][0])
            
            if price is None:
                # Essayer le deuxième DEX disponible
                price = await self.price_manager.get_token_price_usd(base_token, dex_pairs[0][1])
                
            return price or 0
            
        except Exception as e:
            logger.warning(f"Erreur lors de la récupération du prix USD de {base_token}: {e}")
            return 0
    
    async def _estimate_gas_cost(self, token_address: str, base_token: str, amount: float) -> float:
        """
        Estime le coût en gas d'une paire de transactions (achat + vente).
    
    Args:
            token_address: Adresse du token
            base_token: Token de base
            amount: Montant de la transaction
        
    Returns:
            Coût estimé en gas (en tokens de base)
    """
    try:
            # Obtenir le coût de gas estimé depuis le client blockchain
            blockchain_name = self.blockchain.get_blockchain_name().lower()
            
            if blockchain_name == "avax":
                # Coût estimé pour AVAX (en AVAX)
                gas_limit_buy = 250000
                gas_limit_sell = 250000
                gas_price = await self.blockchain.get_gas_price()
                
                # Convertir le gas price en AVAX (de Wei à AVAX)
                gas_price_avax = gas_price * 1e-18
                
                # Coût total = (gas limit buy + gas limit sell) * gas price
                total_gas_cost = (gas_limit_buy + gas_limit_sell) * gas_price_avax
                
                # Ajouter le boost
                return total_gas_cost * (1 + self.config.gas_boost_percent / 100)
                
            elif blockchain_name == "solana":
                # Coût estimé pour Solana (en SOL)
                # Transactions Solana ont généralement un coût fixe
                return 0.000005 * 2  # Estimation pour deux transactions
                
            else:
                # Blockchain non supportée
                return 0.01  # Valeur par défaut conservative
                
        except Exception as e:
            logger.warning(f"Erreur lors de l'estimation du coût du gas: {e}")
            return 0.01  # Valeur par défaut conservative
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Récupère les statistiques de la stratégie d'arbitrage.
        
        Returns:
            Statistiques de la stratégie
        """
        return {
            "opportunities_found": self.opportunities_found,
            "arbitrages_executed": self.arbitrages_executed,
            "successful_arbitrages": self.successful_arbitrages,
            "success_rate": self.successful_arbitrages / self.arbitrages_executed if self.arbitrages_executed > 0 else 0,
            "total_profit": self.total_profit,
            "average_profit": self.total_profit / self.successful_arbitrages if self.successful_arbitrages > 0 else 0,
            "queue_size": self.opportunity_queue.qsize(),
            "recent_executions": self.execution_history[-10:] if self.execution_history else []
        }
    
    def export_performance_data(self, file_path: Optional[str] = None) -> bool:
        """
        Exporte les données de performance dans un fichier JSON.
    
    Args:
            file_path: Chemin du fichier de sortie (généré si non fourni)
        
    Returns:
            True si l'export a réussi, False sinon
    """
    try:
            if not file_path:
                data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data")
                os.makedirs(data_dir, exist_ok=True)
                file_path = os.path.join(data_dir, f"arbitrage_performance_{int(time.time())}.json")
                
            # Récupérer les données de performance
            performance_data = {
                "export_time": time.time(),
                "statistics": self.get_statistics(),
                "execution_history": self.execution_history,
                "configuration": {
                    "min_profit_threshold_percent": self.config.min_profit_threshold_percent,
                    "min_profit_absolute": self.config.min_profit_absolute,
                    "max_input_amount": self.config.max_input_amount,
                    "min_input_amount": self.config.min_input_amount,
                    "max_slippage_percent": self.config.max_slippage_percent,
                    "gas_boost_percent": self.config.gas_boost_percent,
                    "check_interval_seconds": self.config.check_interval_seconds
                }
            }
            
            # Sauvegarder dans un fichier JSON
            with open(file_path, "w") as f:
                json.dump(performance_data, f, indent=2)
                
            logger.info(f"Données de performance exportées vers {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'export des données de performance: {e}")
            return False 