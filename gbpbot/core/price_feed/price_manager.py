#!/usr/bin/env python3
"""
Gestionnaire principal des flux de prix.
Version optimisée avec réduction des duplications et amélioration
de la gestion des sources de prix.
"""

import asyncio
import time
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
from loguru import logger
from collections import OrderedDict
import uuid
from datetime import datetime, timedelta
import copy

from gbpbot.config.config_manager import ConfigManager
from gbpbot.core.monitoring.monitor import BotMonitor
from .dex_feed import DEXPriceFeed
from .cex_feed import CEXPriceFeed
from .price_normalizer import PriceNormalizer as EnhancedPriceNormalizer
try:
    from .sources.oracle import OraclePriceFeed
    has_oracle = True
except ImportError:
    has_oracle = False
    OraclePriceFeed = None

class PriceManager:
    """
    Gestionnaire central des flux de prix.
    Coordonne les différentes sources de prix et fournit une interface
    unifiée pour récupérer les prix normalisés.
    """

    def __init__(self, web3=None, is_testnet: bool = False, simulation_mode: bool = False, monitor: Optional[BotMonitor] = None):
        """
        Initialise le gestionnaire de prix.
        
        Args:
            web3: Instance Web3 pour les interactions blockchain
            is_testnet: Indique si on utilise le testnet
            simulation_mode: Indique si on est en mode simulation
            monitor: Instance du moniteur pour le tracking des métriques
        """
        logger.info("Initialisation du gestionnaire de prix")
        self.config = ConfigManager().get_config()
        self.monitor = monitor
        self.web3 = web3
        self.is_testnet = is_testnet
        self.simulation_mode = simulation_mode
        
        # Initialisation des feeds
        logger.debug("Initialisation des feeds de prix")
        self.dex_feed = DEXPriceFeed(self.config, self.monitor)
        self.cex_feed = CEXPriceFeed(self.config, self.monitor)
        
        # Ajouter le feed Oracle si configuré
        price_feed_config = self.config.get('price_feed', {})
        if price_feed_config.get('use_oracle', False):
            self.oracle_feed = OraclePriceFeed(self.config, self.monitor)
        else:
            self.oracle_feed = None
        
        # Normalisation des prix
        self.normalizer = EnhancedPriceNormalizer(price_feed_config)
        
        # Cache des prix
        self.price_cache = {}
        self.cached_prices = {}
        self.ws_prices = {}
        self.cache_timeout = price_feed_config.get('cache_timeout', 5)
        logger.debug(f"Timeout du cache configuré à {self.cache_timeout} secondes")
        
        # État du service
        self.is_running = False
        self.update_task = None
        self._last_price_anomalies = OrderedDict()
        
        logger.info("Gestionnaire de prix initialisé avec succès")

    async def start(self) -> None:
        """Démarre le service de prix."""
        try:
            if self.is_running:
                logger.warning("Le gestionnaire de prix est déjà en cours d'exécution")
                return
                
            logger.info("Démarrage du gestionnaire de prix")
            
            # Démarrer les feeds
            await self.dex_feed.start()
            await self.cex_feed.start()
            
            # Démarrer le feed oracle si disponible
            if self.oracle_feed:
                await self.oracle_feed.start()
            
            # Démarrer la tâche de mise à jour périodique
            self.is_running = True
            self.update_task = asyncio.create_task(self._periodic_update())
            
            # Initialiser les websockets si non en mode simulation
            if not self.simulation_mode:
                await self.initialize_websockets()
            
            logger.info("Gestionnaire de prix démarré avec succès")
        except Exception as e:
            logger.error(f"Erreur lors du démarrage du gestionnaire de prix: {str(e)}")
            self.is_running = False
            # Arrêter les feeds en cas d'erreur
            try:
                await self.dex_feed.stop()
                await self.cex_feed.stop()
                if self.oracle_feed:
                    await self.oracle_feed.stop()
            except Exception as stop_error:
                logger.error(f"Erreur lors de l'arrêt des feeds après échec de démarrage: {str(stop_error)}")
            raise

    async def stop(self) -> None:
        """Arrête le service de prix."""
        try:
            if not self.is_running:
                logger.warning("Le gestionnaire de prix n'est pas en cours d'exécution")
                return
                
            logger.info("Arrêt du gestionnaire de prix")
            
            # Arrêter la tâche de mise à jour
            self.is_running = False
            if self.update_task:
                self.update_task.cancel()
                try:
                    await self.update_task
                except asyncio.CancelledError:
                    pass
            
            # Arrêter les feeds
            await self.dex_feed.stop()
            await self.cex_feed.stop()
            if self.oracle_feed:
                await self.oracle_feed.stop()
            
            logger.info("Gestionnaire de prix arrêté avec succès")
        except Exception as e:
            logger.error(f"Erreur lors de l'arrêt du gestionnaire de prix: {str(e)}")
            raise
            
    async def get_price(self, token_symbol: str, source: Optional[str] = None) -> Optional[Decimal]:
        """
        Récupère le prix actuel d'un token depuis une source spécifique ou toutes les sources.
        
        Args:
            token_symbol: Symbole du token (ex: "WAVAX")
            source: Source spécifique (dex, cex, oracle) ou None pour le prix normalisé
            
        Returns:
            Optional[Decimal]: Prix du token ou None si non disponible
        """
        try:
            # Vérifier si le prix est dans le cache et toujours valide
            cache_key = f"{token_symbol.upper()}_{source or 'normalized'}"
            if cache_key in self.price_cache:
                cache_entry = self.price_cache[cache_key]
                if time.time() - cache_entry['timestamp'] < self.cache_timeout:
                    logger.debug(f"Prix trouvé dans le cache pour {token_symbol} (source: {source or 'normalized'}): {cache_entry['price']}")
                    return cache_entry['price']
            
            # Si une source spécifique est demandée, récupérer directement
            if source:
                if source.lower() == 'dex':
                    price = await self.dex_feed.get_price(token_symbol)
                elif source.lower() == 'cex':
                    price = await self.cex_feed.get_price(token_symbol, "binance")  # Utiliser Binance par défaut
                elif source.lower() == 'oracle' and self.oracle_feed:
                    price = await self.oracle_feed.get_price(token_symbol)
                else:
                    logger.warning(f"Source inconnue: {source}")
                    return None
                
                # Mettre en cache si valide
                if price:
                    self.price_cache[cache_key] = {
                        'price': price,
                        'timestamp': time.time()
                    }
                
                return price
            
            # Si pas de source spécifique, récupérer toutes les sources et normaliser
            prices = []
            
            # DEX
            dex_price = await self.dex_feed.get_price(token_symbol)
            if dex_price:
                prices.append({
                    'price': dex_price,
                    'source': 'dex',
                    'weight': 1.0
                })
            
            # CEX
            cex_price = await self.cex_feed.get_price(token_symbol, "binance")
            if cex_price:
                prices.append({
                    'price': cex_price,
                    'source': 'cex',
                    'weight': 1.5  # Donner plus de poids aux CEX car souvent plus fiables
                })
            
            # Oracle
            if self.oracle_feed:
                oracle_price = await self.oracle_feed.get_price(token_symbol)
                if oracle_price:
                    prices.append({
                        'price': oracle_price,
                        'source': 'oracle',
                        'weight': 2.0  # Donner encore plus de poids aux oracles car plus fiables
                    })
            
            # WebSocket (si disponible)
            if token_symbol.lower() in self.ws_prices:
                ws_price = self.ws_prices[token_symbol.lower()].get('price')
                if ws_price:
                    prices.append({
                        'price': Decimal(str(ws_price)),
                        'source': 'websocket',
                        'weight': 1.2  # Bon poids car temps réel mais pas toujours fiable
                    })
            
            # Si simulation, ajouter les prix simulés
            if self.simulation_mode and token_symbol.upper() in self.cached_prices:
                sim_price = self.cached_prices[token_symbol.upper()]
                prices.append({
                    'price': sim_price,
                    'source': 'simulation',
                    'weight': 3.0  # Priorité maximale en mode simulation
                })
            
            # Vérifier qu'on a au moins un prix
            if not prices:
                logger.warning(f"Aucun prix trouvé pour {token_symbol}")
                return None
            
            # Normaliser les prix
            normalized_price = self.normalizer.normalize_price(token_symbol, prices)
            
            # Mettre en cache
            if normalized_price:
                self.price_cache[cache_key] = {
                    'price': normalized_price,
                    'timestamp': time.time()
                }
            
            return normalized_price
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du prix pour {token_symbol}: {str(e)}")
            return None
    
    async def get_all_prices(self) -> Dict[str, Dict]:
        """
        Récupère tous les prix disponibles pour tous les tokens.
        
        Returns:
            Dict[str, Dict]: Prix par paire de trading
        """
        try:
            all_prices = {}
            
            # Liste des tokens configurés
            tokens = self.config.get('tokens', {})
            pairs = self.config.get('price_feed', {}).get('pairs', [])
            
            # Pour chaque paire, récupérer les prix de toutes les sources
            for pair in pairs:
                pair_data = {'sources': {}}
                
                # Récupérer les prix DEX
                try:
                    dex_price = await self.dex_feed.get_price(pair)
                    if dex_price:
                        pair_data['sources']['dex'] = {
                            'price': float(dex_price),
                            'timestamp': datetime.now().isoformat()
                        }
                except Exception as e:
                    logger.error(f"Erreur lors de la récupération du prix DEX pour {pair}: {str(e)}")
                
                # Récupérer les prix CEX
                try:
                    for cex in ['binance', 'coinbase', 'kucoin']:
                        try:
                            cex_price = await self.cex_feed.get_price(pair, cex)
                            if cex_price:
                                pair_data['sources'][f'cex_{cex}'] = {
                                    'price': float(cex_price),
                                    'timestamp': datetime.now().isoformat()
                                }
                        except:
                            pass
                except Exception as e:
                    logger.error(f"Erreur lors de la récupération des prix CEX pour {pair}: {str(e)}")
                
                # Récupérer le prix Oracle si disponible
                if self.oracle_feed:
                    try:
                        oracle_price = await self.oracle_feed.get_price(pair)
                        if oracle_price:
                            pair_data['sources']['oracle'] = {
                                'price': float(oracle_price),
                                'timestamp': datetime.now().isoformat()
                            }
                    except Exception as e:
                        logger.error(f"Erreur lors de la récupération du prix Oracle pour {pair}: {str(e)}")
                
                # Récupérer le prix WebSocket si disponible
                if pair.lower() in self.ws_prices:
                    ws_data = self.ws_prices[pair.lower()]
                    pair_data['sources']['websocket'] = {
                        'price': float(ws_data.get('price', 0)),
                        'timestamp': ws_data.get('timestamp', datetime.now().isoformat())
                    }
                
                # Normaliser le prix si on a au moins une source
                if pair_data['sources']:
                    # Convertir les données pour la normalisation
                    sources_for_normalization = [
                        {
                            'price': data['price'],
                            'source': source,
                            'weight': 1.0 if 'dex' in source else 1.5 if 'cex' in source else 2.0
                        }
                        for source, data in pair_data['sources'].items()
                    ]
                    
                    # Normaliser
                    normalized_price = self.normalizer.normalize_price(pair, sources_for_normalization)
                    
                    if normalized_price:
                        pair_data['price'] = float(normalized_price)
                        pair_data['timestamp'] = datetime.now().isoformat()
                        pair_data['volatility'] = float(self.normalizer.get_price_volatility(pair) or 0)
                        
                        # Ajouter à la liste des prix
                        all_prices[pair] = pair_data
            
            return all_prices
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de tous les prix: {str(e)}")
            return {}
    
    async def get_price_pair(self, token_in: str, token_out: str) -> Optional[Decimal]:
        """
        Récupère le prix d'une paire de tokens.
        
        Args:
            token_in: Symbole du token d'entrée
            token_out: Symbole du token de sortie
            
        Returns:
            Optional[Decimal]: Prix de la paire ou None si non disponible
        """
        pair_key = f"{token_in}/{token_out}"
        
        # Vérifier si la paire est dans le cache
        if pair_key in self.price_cache:
            cache_entry = self.price_cache[pair_key]
            if time.time() - cache_entry['timestamp'] < self.cache_timeout:
                return cache_entry['price']
        
        # Récupérer les prix des deux tokens en USD
        price_in = await self.get_price(token_in)
        price_out = await self.get_price(token_out)
        
        if not price_in or not price_out:
            return None
        
        # Calculer le taux de change
        if price_out == Decimal('0'):
            return None
            
        pair_price = price_in / price_out
        
        # Mettre en cache
        self.price_cache[pair_key] = {
            'price': pair_price,
            'timestamp': time.time()
        }
        
        return pair_price
    
    def _is_price_anomaly(self, symbol: str, source: str, price: Decimal) -> bool:
        """
        Détecte si un prix est anormal par rapport aux données historiques.
        
        Args:
            symbol: Symbole de la paire
            source: Source du prix
            price: Prix à vérifier
            
        Returns:
            bool: True si le prix est anormal, False sinon
        """
        return self.normalizer.is_price_anomaly(symbol, source, price)
    
    async def _periodic_update(self) -> None:
        """Tâche périodique pour mettre à jour les prix."""
        logger.info("Démarrage de la tâche de mise à jour périodique des prix")
        
        update_interval = self.config.get('price_feed', {}).get('update_interval', 5)
        
        while self.is_running:
            try:
                start_time = time.time()
                
                # Mettre à jour les prix
                prices = await self.get_all_prices()
                
                # Mettre à jour les métriques
                if self.monitor and prices:
                    for pair, data in prices.items():
                        if 'price' in data:
                            self.monitor.set_metric(f"price_{pair.replace('/', '_')}", data['price'])
                
                # Calculer le temps écoulé et attendre
                elapsed = time.time() - start_time
                sleep_time = max(0.1, update_interval - elapsed)
                
                await asyncio.sleep(sleep_time)
                
            except asyncio.CancelledError:
                logger.info("Tâche de mise à jour des prix annulée")
                break
            except Exception as e:
                logger.error(f"Erreur lors de la mise à jour périodique des prix: {str(e)}")
                await asyncio.sleep(1)  # Attendre un peu en cas d'erreur
    
    async def initialize_websockets(self) -> Dict[str, Dict]:
        """
        Initialise les connexions WebSocket pour les prix en temps réel.
        
        Returns:
            Dict[str, Dict]: État des WebSockets
        """
        if self.simulation_mode:
            logger.info("WebSockets non initialisés en mode simulation")
            return {}
        
        ws_pairs = []
        
        # Récupérer les paires configurées
        configured_pairs = self.config.get('price_feed', {}).get('websocket_pairs', [])
        
        # Convertir les paires en format compatible avec les exchanges
        for pair in configured_pairs:
            tokens = pair.split('/')
            if len(tokens) == 2:
                base, quote = tokens
                
                # Format Binance: btcusdt, ethusdc, etc.
                ws_pairs.append(f"{base.lower()}{quote.lower()}")
                logger.info(f"Tâche WebSocket créée pour {base.lower()}{quote.lower()}")
        
        logger.info(f"WebSockets initialisés pour {len(ws_pairs)} paires")
        
        return self.ws_prices
    
    async def find_arbitrage_opportunities(self) -> List[Dict]:
        """
        Trouve les opportunités d'arbitrage à partir des prix actuels.
        
        Returns:
            List[Dict]: Liste des opportunités d'arbitrage
        """
        try:
            # Récupérer tous les prix
            prices = await self.get_all_prices()
            
            opportunities = []
            min_spread = self.config.get('price_feed', {}).get('min_spread', 0.01)  # 1% minimum
            
            # Pour chaque paire
            for pair, pair_data in prices.items():
                sources = pair_data.get('sources', {})
                
                # Besoin d'au moins 2 sources pour comparer
                if len(sources) < 2:
                    continue
                
                # Organiser les sources par prix
                source_prices = [(source, data['price']) for source, data in sources.items()]
                
                # Trier par prix (du moins cher au plus cher)
                source_prices.sort(key=lambda x: x[1])
                
                # Comparer le prix le plus bas et le prix le plus élevé
                lowest_source, lowest_price = source_prices[0]
                highest_source, highest_price = source_prices[-1]
                
                # Calculer le spread
                if lowest_price == 0:
                    continue
                    
                spread = (highest_price - lowest_price) / lowest_price
                
                # Si le spread est suffisant, c'est une opportunité d'arbitrage
                if spread >= min_spread:
                    tokens = pair.split('/')
                    
                    if len(tokens) != 2:
                        continue
                        
                    base_token, quote_token = tokens
                    
                    opportunity = {
                        'id': str(uuid.uuid4()),
                        'pair': pair,
                        'buy_source': lowest_source,
                        'buy_price': lowest_price,
                        'sell_source': highest_source,
                        'sell_price': highest_price,
                        'spread': spread,
                        'spread_percent': spread * 100,
                        'timestamp': datetime.now().isoformat(),
                        'base_token': base_token,
                        'quote_token': quote_token
                    }
                    
                    opportunities.append(opportunity)
            
            # Trier par spread décroissant
            opportunities.sort(key=lambda x: x['spread'], reverse=True)
            
            return opportunities
            
        except Exception as e:
            logger.error(f"Erreur lors de la recherche d'opportunités d'arbitrage: {str(e)}")
            return [] 