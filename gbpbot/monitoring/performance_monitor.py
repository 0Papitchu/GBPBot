"""
Moniteur de Performance Trading pour GBPBot
==========================================

Ce module fournit une implémentation spécialisée pour le suivi des
performances de trading du GBPBot: ROI, taux de réussite, nombre
de transactions, profits/pertes, etc.

Il s'intègre avec l'interface Telegram et les autres composants
du système pour fournir des statistiques en temps réel.
"""

import os
import json
import logging
import threading
import time
from typing import Dict, List, Any, Optional, Tuple, Set, Union
from datetime import datetime, timedelta
from collections import defaultdict
import statistics

# Configuration du logger
logger = logging.getLogger("gbpbot.monitoring.performance")

class TradeRecord:
    """Représente un enregistrement de transaction pour le suivi des performances"""
    
    def __init__(
        self,
        trade_id: str,
        token_symbol: str,
        blockchain: str,
        entry_price: float,
        exit_price: float = 0.0,
        amount: float = 0.0,
        timestamp_start: Optional[datetime] = None,
        timestamp_end: Optional[datetime] = None,
        strategy: str = "unknown",
        status: str = "open",
        profit_loss: float = 0.0,
        profit_loss_percent: float = 0.0,
        gas_cost: float = 0.0,
        slippage: float = 0.0,
        trade_type: str = "unknown",
        notes: str = ""
    ):
        """
        Initialise un enregistrement de transaction.
        
        Args:
            trade_id: Identifiant unique de la transaction
            token_symbol: Symbole du token négocié
            blockchain: Blockchain sur laquelle la transaction a eu lieu
            entry_price: Prix d'entrée
            exit_price: Prix de sortie (0 si la transaction est toujours ouverte)
            amount: Montant investi
            timestamp_start: Horodatage de l'entrée
            timestamp_end: Horodatage de la sortie
            strategy: Stratégie utilisée (arbitrage, sniping, etc.)
            status: Statut de la transaction (open, closed, failed)
            profit_loss: Profit ou perte en valeur absolue
            profit_loss_percent: Profit ou perte en pourcentage
            gas_cost: Coût du gas pour la transaction
            slippage: Slippage lors de l'exécution
            trade_type: Type de transaction (spot, swap, etc.)
            notes: Notes supplémentaires
        """
        self.trade_id = trade_id
        self.token_symbol = token_symbol
        self.blockchain = blockchain
        self.entry_price = entry_price
        self.exit_price = exit_price
        self.amount = amount
        self.timestamp_start = timestamp_start or datetime.now()
        self.timestamp_end = timestamp_end
        self.strategy = strategy
        self.status = status
        self.profit_loss = profit_loss
        self.profit_loss_percent = profit_loss_percent
        self.gas_cost = gas_cost
        self.slippage = slippage
        self.trade_type = trade_type
        self.notes = notes
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'enregistrement en dictionnaire"""
        return {
            "trade_id": self.trade_id,
            "token_symbol": self.token_symbol,
            "blockchain": self.blockchain,
            "entry_price": self.entry_price,
            "exit_price": self.exit_price,
            "amount": self.amount,
            "timestamp_start": self.timestamp_start.isoformat() if self.timestamp_start else None,
            "timestamp_end": self.timestamp_end.isoformat() if self.timestamp_end else None,
            "strategy": self.strategy,
            "status": self.status,
            "profit_loss": self.profit_loss,
            "profit_loss_percent": self.profit_loss_percent,
            "gas_cost": self.gas_cost,
            "slippage": self.slippage,
            "trade_type": self.trade_type,
            "notes": self.notes
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TradeRecord':
        """Crée un enregistrement à partir d'un dictionnaire"""
        return cls(
            trade_id=data.get("trade_id", ""),
            token_symbol=data.get("token_symbol", ""),
            blockchain=data.get("blockchain", ""),
            entry_price=data.get("entry_price", 0.0),
            exit_price=data.get("exit_price", 0.0),
            amount=data.get("amount", 0.0),
            timestamp_start=datetime.fromisoformat(data["timestamp_start"]) if data.get("timestamp_start") else None,
            timestamp_end=datetime.fromisoformat(data["timestamp_end"]) if data.get("timestamp_end") else None,
            strategy=data.get("strategy", "unknown"),
            status=data.get("status", "open"),
            profit_loss=data.get("profit_loss", 0.0),
            profit_loss_percent=data.get("profit_loss_percent", 0.0),
            gas_cost=data.get("gas_cost", 0.0),
            slippage=data.get("slippage", 0.0),
            trade_type=data.get("trade_type", "unknown"),
            notes=data.get("notes", "")
        )


class PerformanceMonitor:
    """
    Classe pour le monitoring des performances de trading du GBPBot.
    
    Cette classe assure le suivi des transactions, calcule des statistiques de
    performance et fournit des méthodes pour analyser les résultats de trading.
    """
    
    _instance = None
    
    def __new__(cls):
        """Implémentation du pattern Singleton"""
        if cls._instance is None:
            cls._instance = super(PerformanceMonitor, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialise le moniteur de performance"""
        # Éviter la réinitialisation du singleton
        if getattr(self, "_initialized", False):
            return
            
        self._initialized = True
        self.trades = {}  # Dict[trade_id, TradeRecord]
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "performance")
        self.trade_history_file = os.path.join(self.data_dir, "trade_history.json")
        self.stats_file = os.path.join(self.data_dir, "performance_stats.json")
        
        # Créer le répertoire de données s'il n'existe pas
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Verrou pour l'accès concurrent
        self._lock = threading.RLock()
        
        # Charger les données existantes
        self._load_trades()
    
    def _load_trades(self) -> None:
        """Charge les transactions depuis le fichier"""
        if not os.path.exists(self.trade_history_file):
            logger.info("Fichier d'historique des transactions non trouvé. Création d'un nouveau fichier.")
            return
            
        try:
            with open(self.trade_history_file, 'r') as f:
                data = json.load(f)
                for trade_data in data:
                    trade = TradeRecord.from_dict(trade_data)
                    self.trades[trade.trade_id] = trade
            logger.info(f"Chargé {len(self.trades)} transactions depuis {self.trade_history_file}")
        except Exception as e:
            logger.error(f"Erreur lors du chargement des transactions: {str(e)}")
    
    def _save_trades(self) -> None:
        """Sauvegarde les transactions dans le fichier"""
        try:
            with self._lock:
                with open(self.trade_history_file, 'w') as f:
                    json.dump([trade.to_dict() for trade in self.trades.values()], f, indent=2)
            logger.debug(f"Transactions sauvegardées dans {self.trade_history_file}")
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des transactions: {str(e)}")
    
    def add_trade(self, trade: TradeRecord) -> bool:
        """
        Ajoute une nouvelle transaction au moniteur.
        
        Args:
            trade: L'enregistrement de transaction à ajouter
            
        Returns:
            bool: True si l'ajout a réussi, False sinon
        """
        try:
            with self._lock:
                self.trades[trade.trade_id] = trade
                self._save_trades()
            logger.info(f"Transaction ajoutée: {trade.trade_id} - {trade.token_symbol} sur {trade.blockchain}")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de l'ajout de la transaction: {str(e)}")
            return False
    
    def update_trade(self, trade_id: str, **kwargs) -> bool:
        """
        Met à jour une transaction existante.
        
        Args:
            trade_id: L'identifiant de la transaction à mettre à jour
            **kwargs: Les attributs à mettre à jour et leurs nouvelles valeurs
            
        Returns:
            bool: True si la mise à jour a réussi, False sinon
        """
        try:
            with self._lock:
                if trade_id not in self.trades:
                    logger.warning(f"Transaction {trade_id} non trouvée pour mise à jour")
                    return False
                    
                trade = self.trades[trade_id]
                for key, value in kwargs.items():
                    if hasattr(trade, key):
                        setattr(trade, key, value)
                self._save_trades()
            logger.info(f"Transaction mise à jour: {trade_id}")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour de la transaction: {str(e)}")
            return False
    
    def close_trade(self, trade_id: str, exit_price: float, timestamp_end: Optional[datetime] = None) -> bool:
        """
        Ferme une transaction ouverte.
        
        Args:
            trade_id: L'identifiant de la transaction à fermer
            exit_price: Le prix de sortie
            timestamp_end: L'horodatage de sortie (par défaut: maintenant)
            
        Returns:
            bool: True si la fermeture a réussi, False sinon
        """
        try:
            with self._lock:
                if trade_id not in self.trades:
                    logger.warning(f"Transaction {trade_id} non trouvée pour fermeture")
                    return False
                    
                trade = self.trades[trade_id]
                trade.exit_price = exit_price
                trade.timestamp_end = timestamp_end or datetime.now()
                trade.status = "closed"
                
                # Calculer le profit/perte
                if trade.entry_price > 0:
                    trade.profit_loss = (trade.exit_price - trade.entry_price) * trade.amount
                    trade.profit_loss_percent = ((trade.exit_price / trade.entry_price) - 1) * 100
                
                self._save_trades()
            logger.info(f"Transaction fermée: {trade_id} avec P/L: {trade.profit_loss:.2f} ({trade.profit_loss_percent:.2f}%)")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la fermeture de la transaction: {str(e)}")
            return False
    
    def get_trade(self, trade_id: str) -> Optional[TradeRecord]:
        """
        Récupère une transaction par son identifiant.
        
        Args:
            trade_id: L'identifiant de la transaction
            
        Returns:
            TradeRecord ou None si non trouvée
        """
        with self._lock:
            return self.trades.get(trade_id)
    
    def get_all_trades(self) -> List[TradeRecord]:
        """
        Récupère toutes les transactions.
        
        Returns:
            Liste de toutes les transactions
        """
        with self._lock:
            return list(self.trades.values())
    
    def get_open_trades(self) -> List[TradeRecord]:
        """
        Récupère les transactions ouvertes.
        
        Returns:
            Liste des transactions ouvertes
        """
        with self._lock:
            return [trade for trade in self.trades.values() if trade.status == "open"]
    
    def get_closed_trades(self) -> List[TradeRecord]:
        """
        Récupère les transactions fermées.
        
        Returns:
            Liste des transactions fermées
        """
        with self._lock:
            return [trade for trade in self.trades.values() if trade.status == "closed"]
    
    def get_failed_trades(self) -> List[TradeRecord]:
        """
        Récupère les transactions échouées.
        
        Returns:
            Liste des transactions échouées
        """
        with self._lock:
            return [trade for trade in self.trades.values() if trade.status == "failed"]
    
    def get_stats(self, hours: int = 24) -> Dict[str, Any]:
        """
        Calcule les statistiques de performance pour une période donnée.
        
        Args:
            hours: Nombre d'heures à considérer (par défaut: 24)
            
        Returns:
            Dictionnaire contenant les statistiques de performance
        """
        start_time = datetime.now() - timedelta(hours=hours)
        
        with self._lock:
            # Filtrer les transactions dans la période
            period_trades = [
                trade for trade in self.trades.values()
                if trade.timestamp_start >= start_time or
                (trade.timestamp_end and trade.timestamp_end >= start_time)
            ]
            
            # Compter les transactions fermées dans la période
            closed_trades = [trade for trade in period_trades if trade.status == "closed"]
            total_trades = len(closed_trades)
            
            # Calculer les profits et pertes
            profits = [trade.profit_loss for trade in closed_trades if trade.profit_loss > 0]
            losses = [trade.profit_loss for trade in closed_trades if trade.profit_loss < 0]
            
            profit_count = len(profits)
            loss_count = len(losses)
            
            # Calculer les métriques
            total_profit = sum(profits) if profits else 0
            total_loss = sum(losses) if losses else 0
            net_profit = total_profit + total_loss
            
            # Calculer les statistiques par blockchain
            blockchain_stats = defaultdict(lambda: {"trades": 0, "profit": 0.0, "success_rate": 0.0})
            for trade in closed_trades:
                blockchain_stats[trade.blockchain]["trades"] += 1
                blockchain_stats[trade.blockchain]["profit"] += trade.profit_loss
            
            # Calculer les taux de réussite par blockchain
            for blockchain, stats in blockchain_stats.items():
                blockchain_trades = [trade for trade in closed_trades if trade.blockchain == blockchain]
                profitable_trades = len([trade for trade in blockchain_trades if trade.profit_loss > 0])
                stats["success_rate"] = (profitable_trades / stats["trades"]) * 100 if stats["trades"] > 0 else 0
            
            # Calculer les statistiques par stratégie
            strategy_stats = defaultdict(lambda: {"trades": 0, "profit": 0.0, "success_rate": 0.0})
            for trade in closed_trades:
                strategy_stats[trade.strategy]["trades"] += 1
                strategy_stats[trade.strategy]["profit"] += trade.profit_loss
            
            # Calculer les taux de réussite par stratégie
            for strategy, stats in strategy_stats.items():
                strategy_trades = [trade for trade in closed_trades if trade.strategy == strategy]
                profitable_trades = len([trade for trade in strategy_trades if trade.profit_loss > 0])
                stats["success_rate"] = (profitable_trades / stats["trades"]) * 100 if stats["trades"] > 0 else 0
            
            # Calculer les métriques générales
            win_rate = (profit_count / total_trades) * 100 if total_trades > 0 else 0
            avg_profit = total_profit / profit_count if profit_count > 0 else 0
            avg_loss = total_loss / loss_count if loss_count > 0 else 0
            profit_factor = abs(total_profit / total_loss) if total_loss != 0 else float('inf') if total_profit > 0 else 0
            
            # Obtenir les métriques de max profit/loss
            max_profit = max(profits) if profits else 0
            max_loss = min(losses) if losses else 0
            
            return {
                "period_hours": hours,
                "start_time": start_time.isoformat(),
                "end_time": datetime.now().isoformat(),
                "total_trades": total_trades,
                "profit_trades": profit_count,
                "loss_trades": loss_count,
                "win_rate": win_rate,
                "profit_total": total_profit,
                "loss_total": total_loss,
                "net_profit": net_profit,
                "avg_profit": avg_profit,
                "avg_loss": avg_loss,
                "max_profit": max_profit,
                "max_loss": max_loss,
                "profit_factor": profit_factor,
                "blockchain_stats": dict(blockchain_stats),
                "strategy_stats": dict(strategy_stats)
            }
    
    def get_period_stats(self, start_time: datetime, end_time: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Calcule les statistiques de performance pour une période spécifique.
        
        Args:
            start_time: Début de la période
            end_time: Fin de la période (par défaut: maintenant)
            
        Returns:
            Dictionnaire contenant les statistiques de performance
        """
        end_time = end_time or datetime.now()
        hours = (end_time - start_time).total_seconds() / 3600
        
        with self._lock:
            # Filtrer les transactions dans la période
            period_trades = [
                trade for trade in self.trades.values()
                if (start_time <= trade.timestamp_start <= end_time) or
                (trade.timestamp_end and start_time <= trade.timestamp_end <= end_time)
            ]
            
            # Même logique que get_stats, mais avec la période spécifiée
            closed_trades = [trade for trade in period_trades if trade.status == "closed"]
            total_trades = len(closed_trades)
            
            profits = [trade.profit_loss for trade in closed_trades if trade.profit_loss > 0]
            losses = [trade.profit_loss for trade in closed_trades if trade.profit_loss < 0]
            
            profit_count = len(profits)
            loss_count = len(losses)
            
            total_profit = sum(profits) if profits else 0
            total_loss = sum(losses) if losses else 0
            net_profit = total_profit + total_loss
            
            # Calcul des statistiques blockchain et stratégie comme dans get_stats
            blockchain_stats = defaultdict(lambda: {"trades": 0, "profit": 0.0, "success_rate": 0.0})
            strategy_stats = defaultdict(lambda: {"trades": 0, "profit": 0.0, "success_rate": 0.0})
            
            for trade in closed_trades:
                blockchain_stats[trade.blockchain]["trades"] += 1
                blockchain_stats[trade.blockchain]["profit"] += trade.profit_loss
                
                strategy_stats[trade.strategy]["trades"] += 1
                strategy_stats[trade.strategy]["profit"] += trade.profit_loss
            
            for blockchain, stats in blockchain_stats.items():
                blockchain_trades = [trade for trade in closed_trades if trade.blockchain == blockchain]
                profitable_trades = len([trade for trade in blockchain_trades if trade.profit_loss > 0])
                stats["success_rate"] = (profitable_trades / stats["trades"]) * 100 if stats["trades"] > 0 else 0
            
            for strategy, stats in strategy_stats.items():
                strategy_trades = [trade for trade in closed_trades if trade.strategy == strategy]
                profitable_trades = len([trade for trade in strategy_trades if trade.profit_loss > 0])
                stats["success_rate"] = (profitable_trades / stats["trades"]) * 100 if stats["trades"] > 0 else 0
            
            win_rate = (profit_count / total_trades) * 100 if total_trades > 0 else 0
            avg_profit = total_profit / profit_count if profit_count > 0 else 0
            avg_loss = total_loss / loss_count if loss_count > 0 else 0
            profit_factor = abs(total_profit / total_loss) if total_loss != 0 else float('inf') if total_profit > 0 else 0
            
            max_profit = max(profits) if profits else 0
            max_loss = min(losses) if losses else 0
            
            return {
                "period_hours": hours,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "total_trades": total_trades,
                "profit_trades": profit_count,
                "loss_trades": loss_count,
                "win_rate": win_rate,
                "profit_total": total_profit,
                "loss_total": total_loss,
                "net_profit": net_profit,
                "avg_profit": avg_profit,
                "avg_loss": avg_loss,
                "max_profit": max_profit,
                "max_loss": max_loss,
                "profit_factor": profit_factor,
                "blockchain_stats": dict(blockchain_stats),
                "strategy_stats": dict(strategy_stats)
            }
    
    async def get_stats_async(self, hours: int = 24) -> Dict[str, Any]:
        """Version asynchrone de get_stats pour l'interface Telegram"""
        return self.get_stats(hours)
    
    async def get_period_stats_async(self, start_time: datetime, end_time: Optional[datetime] = None) -> Dict[str, Any]:
        """Version asynchrone de get_period_stats pour l'interface Telegram"""
        return self.get_period_stats(start_time, end_time)


def get_performance_monitor() -> PerformanceMonitor:
    """
    Fonction utilitaire pour obtenir l'instance singleton du moniteur de performance.
    
    Returns:
        Instance singleton de PerformanceMonitor
    """
    return PerformanceMonitor() 