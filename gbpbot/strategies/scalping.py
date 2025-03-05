from typing import Dict, List, Optional, Tuple
import asyncio
from loguru import logger
from web3 import Web3
import time
from datetime import datetime

from gbpbot.core.blockchain import BlockchainClient
from gbpbot.core.price_feed import PriceManager
from gbpbot.core.performance_tracker import PerformanceTracker
from gbpbot.core.opportunity_analyzer import OpportunityAnalyzer
from gbpbot.config.trading_config import TradingConfig

from typing import FixtureFunction

from typing import FixtureFunction
# Variables utilisées dans les fixtures
trader_joe = None
status = None
entry_time = None
token_in = None
token_out = None
take_profit_price = None
stop_loss_price = None

from typing import FixtureFunction

from typing import FixtureFunction
# Variables utilisées dans les fixtures
trader_joe = None
status = None
entry_time = None
token_in = None
token_out = None
take_profit_price = None
stop_loss_price = None
# Variables utilisées dans les fixtures
trader_joe = None
status = None
entry_time = None
token_in = None
token_out = None
take_profit_price = None
stop_loss_price = None

from typing import FixtureFunction

from typing import FixtureFunction
# Variables utilisées dans les fixtures
trader_joe = None
status = None
entry_time = None
token_in = None
token_out = None
take_profit_price = None
stop_loss_price = None

from typing import FixtureFunction

from typing import FixtureFunction
# Variables utilisées dans les fixtures
trader_joe = None
status = None
entry_time = None
token_in = None
token_out = None
take_profit_price = None
stop_loss_price = None
# Variables utilisées dans les fixtures
trader_joe = None
status = None
entry_time = None
token_in = None
token_out = None
take_profit_price = None
stop_loss_price = None
# Variables utilisées dans les fixtures
trader_joe = None
status = None
entry_time = None
token_in = None
token_out = None
take_profit_price = None
stop_loss_price = None

class ScalpingStrategy:
    """Stratégie de scalping ultra-rapide optimisée pour TraderJoe"""
    
    def __init__(self, blockchain: BlockchainClient):
        """
        Initialise la stratégie de scalping
        
        Args:
            blockchain: Instance du client blockchain
        """
        self.blockchain = blockchain
        self.web3 = blockchain.web3
        self.price_feed = PriceManager(self.web3)
        self.performance_tracker = PerformanceTracker()
        self.opportunity_analyzer = OpportunityAnalyzer(self.performance_tracker)
        
        # Charger la configuration
        self.config = self._load_config()
        
        # Websocket pour les mises à jour de prix en temps réel
        self.ws_connections = {}
        
        # Cache des prix récents pour analyse de volatilité
        self.price_history = {}
        self.max_price_history = 100  # Nombre maximum d'entrées dans l'historique
        
        # Transactions en cours
        self.active_trades = {}
        
        logger.info("✅ Stratégie de scalping initialisée")
    
    def _load_config(self) -> Dict:
        """Charge la configuration de scalping"""
        # TODO: Créer une configuration spécifique pour le scalping
        # Pour l'instant, on utilise la config d'arbitrage
        config = TradingConfig.get_arbitrage_config()
        
        # Paramètres spécifiques au scalping
        scalping_config = {
            "min_volatility": 0.5,           # Volatilité minimale en % pour entrer
            "take_profit": 0.8,              # Prendre profit à +0.8%
            "stop_loss": -0.4,               # Stop loss à -0.4%
            "max_trade_duration": 180,       # Durée maximale d'un trade en secondes
            "max_active_trades": 3,          # Nombre maximum de trades actifs
            "gas_priority": "high",          # Priorité de gas pour les transactions
            "volume_threshold": 50000,       # Volume minimum en USD
            "volatility_window": 10,         # Fenêtre pour calculer la volatilité (en minutes)
            "price_update_interval": 1,      # Intervalle de mise à jour des prix (en secondes)
            "trader_joe_router": "0x60aE616a2155Ee3d9A68541Ba4544862310933d4"  # Adresse du routeur TraderJoe
        }
        
        return {**config, **scalping_config}
    
    async def start_monitoring(self, token_pairs: List[Dict[str, str]]):
        """
        Démarre le monitoring des paires pour le scalping
        
        Args:
            token_pairs: Liste des paires à surveiller
        """
        logger.info(f"🔍 Démarrage du monitoring de {len(token_pairs)} paires pour le scalping")
        
        # Initialiser les connexions websocket pour chaque paire
        await self._setup_websocket_connections(token_pairs)
        
        # Boucle principale de monitoring
        while True:
            try:
                # Analyser les opportunités de scalping
                opportunities = await self._scan_for_opportunities(token_pairs)
                
                # Filtrer et exécuter les meilleures opportunités
                if opportunities:
                    filtered_opportunities = self._filter_opportunities(opportunities)
                    for opportunity in filtered_opportunities:
                        if len(self.active_trades) < self.config["max_active_trades"]:
                            asyncio.create_task(self._execute_scalping_trade(opportunity))
                
                # Gérer les trades actifs (stop loss, take profit)
                await self._manage_active_trades()
                
                # Attendre avant la prochaine itération
                await asyncio.sleep(self.config["price_update_interval"])
                
            except Exception as e:
                logger.error(f"❌ Erreur dans la boucle de scalping: {str(e)}")
                await asyncio.sleep(5)  # Attendre avant de réessayer
    
    async def _setup_websocket_connections(self, token_pairs: List[Dict[str, str]]):
        """
        Configure les connexions websocket pour les mises à jour de prix en temps réel
        
        Args:
            token_pairs: Liste des paires à surveiller
        """
        # TODO: Implémenter la connexion aux websockets de TraderJoe
        logger.info("🔌 Configuration des connexions websocket pour les mises à jour de prix en temps réel")
    
    async def _scan_for_opportunities(self, token_pairs: List[Dict[str, str]]) -> List[Dict]:
        """
        Scanne les paires pour trouver des opportunités de scalping
        
        Args:
            token_pairs: Liste des paires à surveiller
            
        Returns:
            Liste des opportunités de scalping
        """
        opportunities = []
        
        for pair in token_pairs:
            token_in = pair["token_in"]
            token_out = pair["token_out"]
            
            # Obtenir les prix actuels
            current_prices = await self.price_feed.get_token_prices(token_in, token_out)
            
            # Calculer la volatilité
            volatility = self._calculate_volatility(token_in, token_out)
            
            # Obtenir le volume
            volume = await self.price_feed.get_pair_volume(token_in, token_out, "trader_joe")
            
            # Si la volatilité et le volume sont suffisants, c'est une opportunité
            if volatility >= self.config["min_volatility"] and volume >= self.config["volume_threshold"]:
                # Analyser la tendance
                trend = self._analyze_price_trend(token_in, token_out)
                
                # Créer l'opportunité
                opportunity = {
                    "token_in": token_in,
                    "token_out": token_out,
                    "price": current_prices["trader_joe"],
                    "volatility": volatility,
                    "volume": volume,
                    "trend": trend,
                    "timestamp": datetime.now().timestamp(),
                    "exchange": "trader_joe",
                    "confidence": self._calculate_confidence(volatility, volume, trend)
                }
                
                opportunities.append(opportunity)
                logger.debug(f"💡 Opportunité de scalping détectée: {token_in}/{token_out} - Volatilité: {volatility:.2f}%, Volume: ${volume:,.2f}")
        
        return opportunities
    
    def _filter_opportunities(self, opportunities: List[Dict]) -> List[Dict]:
        """
        Filtre les opportunités pour ne garder que les meilleures
        
        Args:
            opportunities: Liste des opportunités
            
        Returns:
            Liste filtrée des meilleures opportunités
        """
        # Trier par score de confiance
        sorted_opportunities = sorted(opportunities, key=lambda x: x["confidence"], reverse=True)
        
        # Ne garder que les 3 meilleures
        return sorted_opportunities[:3]
    
    def _calculate_volatility(self, token_in: str, token_out: str) -> float:
        """
        Calcule la volatilité d'une paire sur la fenêtre de temps définie
        
        Args:
            token_in: Adresse du token d'entrée
            token_out: Adresse du token de sortie
            
        Returns:
            Volatilité en pourcentage
        """
        # TODO: Implémenter le calcul de volatilité basé sur l'historique des prix
        # Pour l'instant, retourner une valeur aléatoire pour le développement
        import random
        return random.uniform(0.2, 2.0)
    
    def _analyze_price_trend(self, token_in: str, token_out: str) -> str:
        """
        Analyse la tendance des prix
        
        Args:
            token_in: Adresse du token d'entrée
            token_out: Adresse du token de sortie
            
        Returns:
            Tendance: "up", "down" ou "sideways"
        """
        # TODO: Implémenter l'analyse de tendance
        # Pour l'instant, retourner une valeur aléatoire pour le développement
        import random
        trends = ["up", "down", "sideways"]
        return random.choice(trends)
    
    def _calculate_confidence(self, volatility: float, volume: float, trend: str) -> float:
        """
        Calcule un score de confiance pour l'opportunité
        
        Args:
            volatility: Volatilité de la paire
            volume: Volume de trading
            trend: Tendance du prix
            
        Returns:
            Score de confiance entre 0 et 1
        """
        # Base score sur la volatilité
        volatility_score = min(volatility / 2.0, 1.0)  # Max 1.0 à 2% de volatilité
        
        # Score basé sur le volume
        volume_score = min(volume / 100000, 1.0)  # Max 1.0 à $100k de volume
        
        # Bonus pour tendance haussière
        trend_multiplier = 1.2 if trend == "up" else (0.8 if trend == "down" else 1.0)
        
        # Score final
        confidence = (volatility_score * 0.6 + volume_score * 0.4) * trend_multiplier
        
        return min(confidence, 1.0)  # Plafonner à 1.0
    
    async def _execute_scalping_trade(self, opportunity: Dict):
        """
        Exécute un trade de scalping
        
        Args:
            opportunity: Opportunité de scalping
        """
        token_in = opportunity["token_in"]
        token_out = opportunity["token_out"]
        
        # Générer un ID unique pour ce trade
        trade_id = f"{token_in}_{token_out}_{int(time.time())}"
        
        try:
            logger.info(f"🚀 Exécution d'un trade de scalping: {token_in}/{token_out}")
            
            # Déterminer le montant à trader
            amount_in = self.config["trade_amount"]  # En AVAX ou stablecoin
            
            # Préparer la transaction d'achat
            buy_tx = await self._prepare_swap_transaction(token_in, token_out, amount_in)
            
            if not buy_tx:
                logger.error(f"❌ Impossible de préparer la transaction d'achat pour {token_in}/{token_out}")
                return
            
            # Envoyer la transaction avec priorité élevée
            tx_hash = await self.blockchain.send_transaction(
                to=self.config["trader_joe_router"],
                data=buy_tx["data"],
                value=buy_tx["value"],
                priority=self.config["gas_priority"]
            )
            
            if not tx_hash:
                logger.error(f"❌ Échec de l'envoi de la transaction d'achat pour {token_in}/{token_out}")
                return
            
            logger.success(f"✅ Transaction d'achat envoyée: {tx_hash}")
            
            # Enregistrer le trade actif
            self.active_trades[trade_id] = {
                "token_in": token_in,
                "token_out": token_out,
                "amount_in": amount_in,
                "entry_price": opportunity["price"],
                "entry_time": time.time(),
                "take_profit_price": opportunity["price"] * (1 + self.config["take_profit"] / 100),
                "stop_loss_price": opportunity["price"] * (1 + self.config["stop_loss"] / 100),
                "tx_hash": tx_hash,
                "status": "pending"
            }
            
            # Attendre la confirmation de la transaction
            # TODO: Implémenter l'attente de confirmation
            
            # Mettre à jour le statut
            self.active_trades[trade_id]["status"] = "active"
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'exécution du trade de scalping: {str(e)}")
    
    async def _manage_active_trades(self):
        """Gère les trades actifs (stop loss, take profit, expiration)"""
        current_time = time.time()
        trades_to_close = []
        
        for trade_id, trade in self.active_trades.items():
            if trade["status"] != "active":
                continue
                
            # Vérifier si le trade a expiré
            trade_duration = current_time - trade["entry_time"]
            if trade_duration > self.config["max_trade_duration"]:
                logger.warning(f"⏱️ Trade {trade_id} a expiré (durée: {trade_duration:.1f}s)")
                trades_to_close.append((trade_id, "expired"))
                continue
            
            # Obtenir le prix actuel
            current_price = await self.price_feed.get_token_price(
                trade["token_in"], 
                trade["token_out"], 
                "trader_joe"
            )
            
            # Vérifier take profit
            if current_price >= trade["take_profit_price"]:
                logger.success(f"💰 Take profit atteint pour {trade_id} (profit: {self.config['take_profit']}%)")
                trades_to_close.append((trade_id, "take_profit"))
                continue
                
            # Vérifier stop loss
            if current_price <= trade["stop_loss_price"]:
                logger.warning(f"🛑 Stop loss déclenché pour {trade_id} (perte: {self.config['stop_loss']}%)")
                trades_to_close.append((trade_id, "stop_loss"))
                continue
        
        # Fermer les trades
        for trade_id, reason in trades_to_close:
            await self._close_trade(trade_id, reason)
    
    async def _close_trade(self, trade_id: str, reason: str):
        """
        Ferme un trade actif
        
        Args:
            trade_id: ID du trade à fermer
            reason: Raison de la fermeture (take_profit, stop_loss, expired)
        """
        trade = self.active_trades[trade_id]
        
        try:
            logger.info(f"🔄 Fermeture du trade {trade_id} pour raison: {reason}")
            
            # Préparer la transaction de vente
            sell_tx = await self._prepare_swap_transaction(
                trade["token_out"],
                trade["token_in"],
                None  # Vendre tout le solde
            )
            
            if not sell_tx:
                logger.error(f"❌ Impossible de préparer la transaction de vente pour {trade_id}")
                return
            
            # Envoyer la transaction avec priorité élevée
            tx_hash = await self.blockchain.send_transaction(
                to=self.config["trader_joe_router"],
                data=sell_tx["data"],
                value=sell_tx["value"],
                priority=self.config["gas_priority"]
            )
            
            if not tx_hash:
                logger.error(f"❌ Échec de l'envoi de la transaction de vente pour {trade_id}")
                return
            
            logger.success(f"✅ Transaction de vente envoyée: {tx_hash}")
            
            # Mettre à jour le statut du trade
            self.active_trades[trade_id]["status"] = "closed"
            self.active_trades[trade_id]["exit_time"] = time.time()
            self.active_trades[trade_id]["exit_tx_hash"] = tx_hash
            self.active_trades[trade_id]["exit_reason"] = reason
            
            # Calculer et enregistrer les performances
            # TODO: Implémenter le calcul des performances
            
            # Supprimer le trade de la liste des trades actifs après un certain temps
            asyncio.create_task(self._cleanup_trade(trade_id))
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de la fermeture du trade {trade_id}: {str(e)}")
    
    async def _cleanup_trade(self, trade_id: str):
        """
        Nettoie un trade fermé après un certain temps
        
        Args:
            trade_id: ID du trade à nettoyer
        """
        await asyncio.sleep(300)  # Attendre 5 minutes
        if trade_id in self.active_trades:
            del self.active_trades[trade_id]
            logger.debug(f"🧹 Trade {trade_id} supprimé de la liste des trades actifs")
    
    async def _prepare_swap_transaction(self, token_in: str, token_out: str, amount_in: Optional[float]) -> Optional[Dict]:
        """
        Prépare une transaction de swap sur TraderJoe
        
        Args:
            token_in: Adresse du token d'entrée
            token_out: Adresse du token de sortie
            amount_in: Montant à échanger (None pour tout le solde)
            
        Returns:
            Dictionnaire avec les données de transaction
        """
        # TODO: Implémenter la préparation de transaction
        # Pour l'instant, retourner un mock pour le développement
        return {
            "data": b'0x',  # Données de transaction encodées
            "value": 0      # Valeur en wei à envoyer
        } 