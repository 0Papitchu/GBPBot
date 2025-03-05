from typing import Dict, List, Optional, Tuple, Any
from decimal import Decimal
import logging
import asyncio
from datetime import datetime, timedelta
import time
import uuid
from collections import OrderedDict

from .base import BasePriceFeed
from .dex_feed import DEXPriceFeed
from .cex_feed import CEXPriceFeed
from gbpbot.core.monitoring.monitor import BotMonitor
from .price_manager import PriceManager
from loguru import logger
from .price_normalizer import PriceNormalizer as EnhancedPriceNormalizer

class PriceAggregator:
    """
    Agrégateur de prix optimisé.
    Responsable de l'agrégation des prix et de la détection des opportunités d'arbitrage.
    Délègue la récupération des prix au PriceManager.
    """
    
    def __init__(self, price_manager, monitor: Optional[BotMonitor] = None):
        """
        Initialise l'agrégateur de prix.
        
        Args:
            price_manager: Gestionnaire de prix
            monitor: Moniteur pour les métriques (optionnel)
        """
        logger.info("Initialisation de l'agrégateur de prix")
        self.price_manager = price_manager
        self.monitor = monitor
        self.config = price_manager.config.get('price_feed', {})
        
        # Configuration des seuils
        self.min_spread = self.config.get('min_spread', 0.01)
        self.min_profit = self.config.get('min_profit_threshold', 0.005)
        self.gas_cost_estimate = self.config.get('gas_cost_estimate', 0.002)
        
        # État des positions
        self.positions: Dict[str, Dict[str, Any]] = {}
        
        # État du service
        self.is_running = False
        self.update_task = None
        logger.info("Agrégateur de prix initialisé avec succès")
        
        self.dex_feed = DEXPriceFeed(self.config)
        self.cex_feed = CEXPriceFeed(self.config)
        self.normalizer = EnhancedPriceNormalizer(self.config)
        self.price_cache = {}
        self.last_update = {}
        
    async def start(self) -> None:
        """Démarre le service d'agrégation."""
        try:
            if self.is_running:
                logger.warning("L'agrégateur de prix est déjà en cours d'exécution")
                return
                
            logger.info("Démarrage de l'agrégateur de prix")
            
            # Démarrer le gestionnaire de prix s'il n'est pas déjà démarré
            if not self.price_manager.is_running:
                await self.price_manager.start()
            
            # Démarrer la tâche de mise à jour périodique
            self.is_running = True
            self.update_task = asyncio.create_task(self._periodic_update())
            
            await self.dex_feed.start()
            await self.cex_feed.start()
            
            logger.info("Agrégateur de prix démarré avec succès")
        except Exception as e:
            logger.error(f"Erreur lors du démarrage de l'agrégateur de prix: {str(e)}")
            self.is_running = False
            raise
        
    async def stop(self) -> None:
        """Arrête le service d'agrégation."""
        try:
            if not self.is_running:
                logger.warning("L'agrégateur de prix n'est pas en cours d'exécution")
                return
                
            logger.info("Arrêt de l'agrégateur de prix")
            
            # Arrêter la tâche de mise à jour
            self.is_running = False
            if self.update_task:
                self.update_task.cancel()
                try:
                    await self.update_task
                except asyncio.CancelledError:
                    pass
            
            await self.dex_feed.stop()
            await self.cex_feed.stop()
            
            logger.info("Agrégateur de prix arrêté avec succès")
        except Exception as e:
            logger.error(f"Erreur lors de l'arrêt de l'agrégateur de prix: {str(e)}")
            raise
        
    async def get_price(self, token: str) -> Optional[Dict]:
        """
        Récupère le prix agrégé d'un token.
        
        Args:
            token: Adresse ou symbole du token
            
        Returns:
            Optional[Dict]: Prix agrégé avec métadonnées
        """
        # Vérifier le cache
        if token in self.price_cache:
            cache_age = datetime.now() - self.last_update[token]
            if cache_age < timedelta(seconds=self.config['cache_ttl']):
                return self.price_cache[token]
                
        # Récupérer les prix de toutes les sources
        prices = []
        
        # Prix DEX
        dex_price = await self.dex_feed.get_price(token)
        if dex_price:
            prices.append({
                'price': dex_price,
                'source': 'dex',
                'liquidity': await self.dex_feed.get_liquidity(token)
            })
            
        # Prix CEX
        cex_price = await self.cex_feed.get_price(token)
        if cex_price:
            prices.append({
                'price': cex_price,
                'source': 'cex',
                'liquidity': await self.cex_feed.get_liquidity(token)
            })
            
        if not prices:
            logger.warning(f"Aucun prix disponible pour {token}")
            return None
            
        # Normaliser le prix
        normalized_price = self.normalizer.normalize_price(token, prices)
        if not normalized_price:
            return None
            
        # Calculer les métriques
        volatility = self.normalizer.get_price_volatility(token)
        is_stable = self.normalizer.is_price_stable(token)
        
        # Créer le résultat
        result = {
            'price': normalized_price,
            'sources': [p['source'] for p in prices],
            'timestamp': datetime.now().timestamp(),
            'volatility': volatility,
            'is_stable': is_stable,
            'confidence': self._calculate_confidence(prices, normalized_price)
        }
        
        # Mettre en cache
        self.price_cache[token] = result
        self.last_update[token] = datetime.now()
        
        return result
        
    async def get_arbitrage_opportunities(self) -> List[Dict]:
        """
        Récupère les opportunités d'arbitrage actuelles.
        
        Returns:
            List[Dict]: Liste des opportunités d'arbitrage
        """
        try:
            # Récupérer les prix actuels
            prices = await self.price_manager.get_all_prices()
            
            # Trouver les opportunités d'arbitrage
            opportunities = self.find_arbitrage_opportunities(prices)
            
            # Filtrer les opportunités dont le profit estimé est supérieur au coût du gaz
            filtered_opportunities = []
            for opp in opportunities:
                estimated_profit_usd = opp.get('estimated_profit_usd', 0)
                if estimated_profit_usd > self.gas_cost_estimate:
                    filtered_opportunities.append(opp)
            
            return filtered_opportunities
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des opportunités d'arbitrage: {str(e)}")
            return []
    
    def find_arbitrage_opportunities(self, prices: Dict[str, Dict], amount_in: Optional[float] = None) -> List[Dict]:
        """
        Analyse les prix pour trouver des opportunités d'arbitrage.
        
        Args:
            prices: Dictionnaire des prix par paire
            amount_in: Montant à échanger (optionnel)
            
        Returns:
            List[Dict]: Liste des opportunités d'arbitrage
        """
        opportunities = []
        
        try:
            # Parcourir toutes les paires de trading
            for pair, pair_data in prices.items():
                # Vérifier si nous avons des prix pour différentes sources
                if 'sources' not in pair_data or len(pair_data['sources']) < 2:
                    continue
                
                # Extraire le symbole et organiser les sources par prix
                symbols = pair.split('/')
                if len(symbols) != 2:
                    continue
                
                token_in, token_out = symbols
                
                # Organiser les sources par prix d'achat (ordre croissant)
                buy_sources = sorted(
                    [(source, data) for source, data in pair_data['sources'].items()],
                    key=lambda x: Decimal(str(x[1]['price']))
                )
                
                # Organiser les sources par prix de vente (ordre décroissant)
                sell_sources = sorted(
                    [(source, data) for source, data in pair_data['sources'].items()],
                    key=lambda x: Decimal(str(x[1]['price'])),
                    reverse=True
                )
                
                # Comparer les meilleures sources d'achat et de vente
                if not buy_sources or not sell_sources:
                    continue
                
                cheapest_source, cheapest_data = buy_sources[0]
                most_expensive_source, most_expensive_data = sell_sources[0]
                
                # Si la meilleure source d'achat et de vente est la même, continuer
                if cheapest_source == most_expensive_source:
                    continue
                
                buy_price = Decimal(str(cheapest_data['price']))
                sell_price = Decimal(str(most_expensive_data['price']))
                
                # Calculer le spread
                if buy_price == 0:
                    continue
                    
                spread = (sell_price - buy_price) / buy_price
                
                # Vérifier si le spread est suffisant
                if spread > self.min_spread:
                    # Calculer le profit estimé
                    amount = Decimal(str(amount_in)) if amount_in else Decimal('100')  # Valeur par défaut
                    estimated_profit = amount * spread
                    
                    # Créer l'opportunité
                    opportunity = {
                        'id': str(uuid.uuid4()),
                        'pair': pair,
                        'token_in': token_in,
                        'token_out': token_out,
                        'buy_source': cheapest_source,
                        'buy_price': float(buy_price),
                        'sell_source': most_expensive_source,
                        'sell_price': float(sell_price),
                        'spread': float(spread),
                        'spread_percent': float(spread * 100),
                        'amount_in': float(amount),
                        'estimated_profit': float(estimated_profit),
                        'estimated_profit_usd': float(estimated_profit * sell_price),
                        'timestamp': datetime.now().isoformat(),
                        'confidence': self._calculate_confidence(pair_data)
                    }
                    
                    opportunities.append(opportunity)
            
            # Trier par profit estimé
            opportunities.sort(key=lambda x: x['estimated_profit_usd'], reverse=True)
            
            return opportunities
            
        except Exception as e:
            logger.error(f"Erreur lors de la recherche d'opportunités d'arbitrage: {str(e)}")
            return []
    
    def _calculate_confidence(self, pair_data: Dict) -> float:
        """
        Calcule un score de confiance pour une opportunité d'arbitrage.
        
        Args:
            pair_data: Données de prix pour la paire
            
        Returns:
            float: Score de confiance entre 0 et 1
        """
        try:
            # Facteurs de confiance
            factors = {
                'num_sources': 0.3,     # Nombre de sources contribuant au prix
                'price_age': 0.4,       # Âge des données de prix
                'volatility': 0.3       # Volatilité récente du prix
            }
            
            confidence = 0.0
            
            # Nombre de sources
            sources_count = len(pair_data.get('sources', {}))
            max_sources = 5  # Nombre maximum attendu de sources
            sources_score = min(sources_count / max_sources, 1.0)
            confidence += sources_score * factors['num_sources']
            
            # Âge des données
            now = datetime.now()
            timestamps = [
                datetime.fromisoformat(data.get('timestamp', now.isoformat()))
                for _, data in pair_data.get('sources', {}).items()
            ]
            
            if timestamps:
                newest_timestamp = max(timestamps)
                age_seconds = (now - newest_timestamp).total_seconds()
                age_score = max(1.0 - (age_seconds / 60), 0)  # Réduire la confiance après 1 minute
                confidence += age_score * factors['price_age']
            else:
                confidence += 0  # Pas de données de timestamp
            
            # Volatilité
            volatility = pair_data.get('volatility', 0.1)  # Valeur par défaut
            volatility_score = max(1.0 - volatility * 10, 0)  # Considérer une volatilité > 10% comme mauvaise
            confidence += volatility_score * factors['volatility']
            
            return min(confidence, 1.0)
            
        except Exception as e:
            logger.error(f"Erreur lors du calcul du score de confiance: {str(e)}")
            return 0.5  # Valeur par défaut
    
    async def _periodic_update(self) -> None:
        """Tâche périodique pour mettre à jour les prix et opportunités."""
        logger.info("Démarrage de la tâche de mise à jour périodique des opportunités")
        
        update_interval = self.config.get('price_feed', {}).get('opportunity_update_interval', 10)
        
        while self.is_running:
            try:
                start_time = time.time()
                
                # Mettre à jour les opportunités
                opportunities = await self.get_arbitrage_opportunities()
                
                if self.monitor:
                    # Mettre à jour les métriques
                    self.monitor.set_metric('arbitrage_opportunities_count', len(opportunities))
                    
                    if opportunities:
                        best_opportunity = opportunities[0]
                        self.monitor.set_metric('best_arbitrage_spread', best_opportunity['spread_percent'])
                        self.monitor.set_metric('best_arbitrage_profit_usd', best_opportunity['estimated_profit_usd'])
                
                # Calculer le temps écoulé et attendre
                elapsed = time.time() - start_time
                sleep_time = max(0, update_interval - elapsed)
                
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                    
            except asyncio.CancelledError:
                logger.info("Tâche de mise à jour des opportunités annulée")
                break
            except Exception as e:
                logger.error(f"Erreur lors de la mise à jour périodique des opportunités: {str(e)}")
                await asyncio.sleep(5)  # Attendre en cas d'erreur
    
    async def open_position(self, token_address: str, entry_price: Decimal, amount: Decimal, 
                       stop_loss: Optional[Decimal] = None, take_profit: Optional[Decimal] = None) -> str:
        """
        Ouvre une nouvelle position de trading.
        
        Args:
            token_address: Adresse du token
            entry_price: Prix d'entrée
            amount: Montant investi
            stop_loss: Prix du stop loss (optionnel)
            take_profit: Prix du take profit (optionnel)
            
        Returns:
            str: Identifiant de la position
        """
        position_id = str(uuid.uuid4())
        
        # Configurer le stop loss si non spécifié
        if stop_loss is None:
            stop_loss_percent = self.config.get('price_feed', {}).get('stop_loss', {}).get('default_percent', 0.05)
            stop_loss = entry_price * (Decimal('1') - Decimal(str(stop_loss_percent)))
        
        # Configurer le take profit si non spécifié
        if take_profit is None:
            take_profit_percent = self.config.get('price_feed', {}).get('take_profit', {}).get('default_percent', 0.1)
            take_profit = entry_price * (Decimal('1') + Decimal(str(take_profit_percent)))
        
        # Créer la position
        position = {
            'id': position_id,
            'token_address': token_address,
            'entry_price': entry_price,
            'current_price': entry_price,
            'amount': amount,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'status': 'open',
            'pnl': Decimal('0'),
            'pnl_percent': Decimal('0'),
            'entry_time': datetime.now(),
            'last_update_time': datetime.now(),
            'exit_time': None,
            'exit_price': None,
            'exit_reason': None
        }
        
        # Stocker la position
        self.positions[position_id] = position
        
        logger.info(f"Position ouverte: {position_id} pour {token_address} au prix {entry_price}")
        return position_id
    
    async def close_position(self, position_id: str, exit_price: Decimal, reason: str = "manual") -> Dict[str, Any]:
        """
        Ferme une position existante.
        
        Args:
            position_id: Identifiant de la position
            exit_price: Prix de sortie
            reason: Raison de la fermeture
            
        Returns:
            Dict: Position mise à jour
        """
        if position_id not in self.positions:
            logger.error(f"Position {position_id} non trouvée")
            return {}
            
        position = self.positions[position_id]
        
        if position['status'] != 'open':
            logger.warning(f"Position {position_id} déjà fermée")
            return position
        
        # Calculer le P&L
        entry_price = position['entry_price']
        amount = position['amount']
        
        if entry_price > 0:
            pnl = (exit_price - entry_price) * amount
            pnl_percent = (exit_price - entry_price) / entry_price * Decimal('100')
        else:
            pnl = Decimal('0')
            pnl_percent = Decimal('0')
        
        # Mettre à jour la position
        position.update({
            'status': 'closed',
            'exit_price': exit_price,
            'exit_time': datetime.now(),
            'exit_reason': reason,
            'pnl': pnl,
            'pnl_percent': pnl_percent,
            'last_update_time': datetime.now()
        })
        
        logger.info(f"Position fermée: {position_id}, P&L: {pnl} ({pnl_percent:.2f}%), Raison: {reason}")
        return position
    
    async def update_position(self, position_id: str, current_price: Decimal) -> Dict[str, Any]:
        """
        Met à jour l'état d'une position avec le prix actuel.
        
        Args:
            position_id: Identifiant de la position
            current_price: Prix actuel du token
            
        Returns:
            Dict: Position mise à jour
        """
        if position_id not in self.positions:
            logger.error(f"Position {position_id} non trouvée")
            return {}
            
        position = self.positions[position_id]
        
        if position['status'] != 'open':
            return position  # Ne pas mettre à jour les positions fermées
        
        # Calculer le P&L courant
        entry_price = position['entry_price']
        amount = position['amount']
        
        if entry_price > 0:
            pnl = (current_price - entry_price) * amount
            pnl_percent = (current_price - entry_price) / entry_price * Decimal('100')
        else:
            pnl = Decimal('0')
            pnl_percent = Decimal('0')
        
        # Mettre à jour la position
        position.update({
            'current_price': current_price,
            'pnl': pnl,
            'pnl_percent': pnl_percent,
            'last_update_time': datetime.now()
        })
        
        # Vérifier stop loss et take profit
        if current_price <= position['stop_loss']:
            # Déclencher le stop loss
            return await self.close_position(position_id, current_price, "stop_loss")
            
        if current_price >= position['take_profit']:
            # Déclencher le take profit
            return await self.close_position(position_id, current_price, "take_profit")
        
        return position
    
    async def get_position(self, position_id: str) -> Dict[str, Any]:
        """
        Récupère les détails d'une position.
        
        Args:
            position_id: Identifiant de la position
            
        Returns:
            Dict: Détails de la position
        """
        return self.positions.get(position_id, {})
    
    async def get_all_positions(self, status: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """
        Récupère toutes les positions, avec filtrage optionnel par statut.
        
        Args:
            status: Statut des positions à récupérer (optionnel)
            
        Returns:
            Dict: Positions filtrées
        """
        if status is None:
            return self.positions
            
        return {
            pos_id: pos
            for pos_id, pos in self.positions.items()
            if pos['status'] == status
        }
    
    async def get_token_positions(self, token_address: str, status: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """
        Récupère les positions pour un token spécifique, avec filtrage optionnel par statut.
        
        Args:
            token_address: Adresse du token
            status: Statut des positions à récupérer (optionnel)
            
        Returns:
            Dict: Positions filtrées
        """
        if status is None:
            return {
                pos_id: pos
                for pos_id, pos in self.positions.items()
                if pos['token_address'] == token_address
            }
            
        return {
            pos_id: pos
            for pos_id, pos in self.positions.items()
            if pos['token_address'] == token_address and pos['status'] == status
        } 