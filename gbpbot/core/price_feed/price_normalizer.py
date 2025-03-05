#!/usr/bin/env python3
"""
Module de normalisation des prix entre différentes sources.
Version améliorée avec gestion d'historique et détection des anomalies.
"""

from typing import Dict, List, Optional, Any
from decimal import Decimal
import statistics
from datetime import datetime, timedelta
from loguru import logger
import copy
from collections import deque

class PriceNormalizer:
    """Gestionnaire avancé de normalisation des prix entre différentes sources."""
    
    def __init__(self, config: Dict = None):
        """
        Initialise le normalisateur de prix.
        
        Args:
            config: Configuration optionnelle pour le normalisateur
        """
        self.config = config or {}
        
        # Configuration des paramètres
        self.outlier_threshold = self.config.get('price_feed', {}).get('outlier_threshold', 2.0)
        self.min_sources = self.config.get('price_feed', {}).get('min_sources', 2)
        self.max_deviation = self.config.get('price_feed', {}).get('max_deviation', 0.05)  # 5% d'écart maximum
        self.history_size = self.config.get('price_feed', {}).get('history_size', 50)
        self.volatility_threshold = self.config.get('price_feed', {}).get('volatility_threshold', 0.03)  # 3% de volatilité maximum
        
        # Historique des prix et statistiques
        self.price_history = {}  # Historique des prix par paire de trading
        self.last_prices = {}    # Dernier prix normalisé par paire
        self.volatility = {}     # Volatilité calculée par paire
        
        logger.debug(f"Normalisateur de prix initialisé avec seuil d'outlier: {self.outlier_threshold}, "
                    f"sources min: {self.min_sources}, taille historique: {self.history_size}")
    
    def normalize_price(self, token: str, prices: List[Dict]) -> Optional[Decimal]:
        """
        Normalise les prix d'un token à partir de différentes sources.
        
        Args:
            token: Adresse ou symbole du token
            prices: Liste des prix avec leur source, poids et autres métadonnées
            
        Returns:
            Optional[Decimal]: Prix normalisé ou None si pas assez de données valides
        """
        try:
            if not prices or len(prices) < 1:
                logger.warning(f"Pas assez de sources de prix pour {token}")
                return None
                
            # Si une seule source, retourner directement le prix
            if len(prices) == 1:
                normalized_price = Decimal(str(prices[0]['price']))
                self._update_history(token, normalized_price)
                return normalized_price
                
            # Filtrer les prix invalides et les outliers
            valid_prices = self._filter_prices(prices)
            if len(valid_prices) < 1:
                logger.warning(f"Pas assez de prix valides après filtrage pour {token}")
                return None
                
            # Si un seul prix valide, le retourner directement
            if len(valid_prices) == 1:
                normalized_price = Decimal(str(valid_prices[0]['price']))
                self._update_history(token, normalized_price)
                return normalized_price
                
            # Calculer le prix normalisé (moyenne pondérée par la liquidité/poids)
            weighted_prices = []
            total_weight = Decimal('0')
            
            for price_info in valid_prices:
                price = Decimal(str(price_info['price']))
                weight = Decimal(str(price_info.get('weight', price_info.get('liquidity', 1))))
                weighted_prices.append(price * weight)
                total_weight += weight
                
            if total_weight == Decimal('0'):
                # Si pas de poids, utiliser la médiane
                normalized_price = statistics.median([Decimal(str(p['price'])) for p in valid_prices])
            else:
                # Calculer la moyenne pondérée
                normalized_price = sum(weighted_prices) / total_weight
            
            # Mettre à jour l'historique des prix
            self._update_history(token, normalized_price)
            
            logger.debug(f"Prix normalisé pour {token}: {normalized_price} (à partir de {len(valid_prices)} sources)")
            return normalized_price
            
        except Exception as e:
            logger.error(f"Erreur lors de la normalisation des prix pour {token}: {str(e)}")
            # En cas d'erreur, essayer de retourner la médiane des prix bruts
            try:
                if prices:
                    normalized_price = statistics.median([Decimal(str(p['price'])) for p in prices])
                    self._update_history(token, normalized_price)
                    return normalized_price
            except:
                pass
            return None
    
    def _filter_prices(self, prices: List[Dict]) -> List[Dict]:
        """
        Filtre les prix pour éliminer les outliers.
        
        Args:
            prices: Liste des prix à filtrer
            
        Returns:
            List[Dict]: Liste des prix valides
        """
        try:
            # Enlever les prix nuls ou négatifs
            valid_prices = [p for p in prices if Decimal(str(p['price'])) > 0]
            
            if not valid_prices:
                return []
                
            # Convertir tous les prix en Decimal pour éviter les problèmes de précision
            decimal_prices = [Decimal(str(p['price'])) for p in valid_prices]
            
            # Calculer la médiane et l'écart-type
            median_price = statistics.median(decimal_prices)
            
            try:
                std_dev = statistics.stdev(decimal_prices)
            except statistics.StatisticsError:
                # Pas assez de valeurs pour calculer l'écart-type
                return valid_prices
                
            # Filtrer les outliers en fonction de l'écart-type
            filtered_prices = []
            for i, price_info in enumerate(valid_prices):
                price = decimal_prices[i]
                
                # Si l'écart-type est proche de zéro, éviter la division par zéro
                if std_dev < Decimal('0.000001'):
                    filtered_prices.append(price_info)
                    continue
                    
                # Calculer la déviation normalisée
                deviation = abs(price - median_price) / std_dev
                
                if deviation <= self.outlier_threshold:
                    filtered_prices.append(price_info)
                else:
                    logger.warning(f"Prix outlier filtré: {price} (déviation: {deviation:.2f} écarts-types de la médiane {median_price})")
            
            return filtered_prices
            
        except Exception as e:
            logger.error(f"Erreur lors du filtrage des prix: {str(e)}")
            return prices  # En cas d'erreur, retourner les prix d'origine
    
    def _update_history(self, token: str, price: Decimal) -> None:
        """
        Met à jour l'historique des prix pour un token.
        
        Args:
            token: Identifiant du token
            price: Prix normalisé
        """
        timestamp = datetime.now()
        
        if token not in self.price_history:
            self.price_history[token] = deque(maxlen=self.history_size)
            
        self.price_history[token].append({
            'price': price,
            'timestamp': timestamp
        })
        
        self.last_prices[token] = price
        
        # Mettre à jour la volatilité
        self._update_volatility(token)
    
    def _update_volatility(self, token: str) -> None:
        """
        Calcule et met à jour la volatilité des prix pour un token.
        
        Args:
            token: Identifiant du token
        """
        if token not in self.price_history or len(self.price_history[token]) < 2:
            self.volatility[token] = Decimal('0')
            return
            
        prices = [entry['price'] for entry in self.price_history[token]]
        
        if len(prices) >= 2:
            try:
                # Utiliser l'écart-type relatif à la moyenne comme mesure de volatilité
                mean_price = statistics.mean(prices)
                std_dev = statistics.stdev(prices)
                
                if mean_price > 0:
                    self.volatility[token] = Decimal(str(std_dev)) / Decimal(str(mean_price))
                else:
                    self.volatility[token] = Decimal('0')
                    
            except Exception as e:
                logger.error(f"Erreur lors du calcul de la volatilité pour {token}: {str(e)}")
                self.volatility[token] = Decimal('0')
        else:
            self.volatility[token] = Decimal('0')
    
    def is_price_stable(self, token: str) -> bool:
        """
        Vérifie si le prix d'un token est stable.
        
        Args:
            token: Identifiant du token
            
        Returns:
            bool: True si le prix est stable, False sinon
        """
        if token not in self.volatility:
            return True  # Si pas de données, considérer stable par défaut
            
        return self.volatility[token] <= Decimal(str(self.volatility_threshold))
    
    def get_price_volatility(self, token: str) -> Optional[Decimal]:
        """
        Récupère la volatilité calculée pour un token.
        
        Args:
            token: Identifiant du token
            
        Returns:
            Optional[Decimal]: Volatilité du prix ou None si non disponible
        """
        return self.volatility.get(token)
    
    def is_price_anomaly(self, token: str, source: str, price: Decimal) -> bool:
        """
        Détecte si un prix est anormal par rapport à l'historique récent.
        
        Args:
            token: Identifiant du token
            source: Source du prix
            price: Prix à vérifier
            
        Returns:
            bool: True si le prix est anormal, False sinon
        """
        if token not in self.last_prices:
            return False  # Pas d'historique pour comparer
            
        last_price = self.last_prices[token]
        
        if last_price == Decimal('0'):
            return False  # Éviter division par zéro
            
        # Calculer le pourcentage de changement
        price_change = abs(price - last_price) / last_price * Decimal('100')
        
        # Seuil d'anomalie basé sur la volatilité historique ou une valeur par défaut
        anomaly_threshold = Decimal('10')  # 10% par défaut
        if token in self.volatility:
            # Ajuster le seuil en fonction de la volatilité (min 5%, max 50%)
            volatility_factor = min(max(self.volatility[token] * Decimal('100') * Decimal('5'), Decimal('5')), Decimal('50'))
            anomaly_threshold = volatility_factor
            
        is_anomaly = price_change > anomaly_threshold
        
        if is_anomaly:
            logger.warning(f"Prix anormal détecté pour {token} sur {source}: {price} "
                          f"(changement de {price_change:.2f}% par rapport au dernier prix {last_price})")
                          
        return is_anomaly
        
    def normalize_prices(self, prices_by_pair: Dict[str, List[Dict]]) -> Dict[str, Dict]:
        """
        Normalise les prix pour plusieurs paires de trading.
        
        Args:
            prices_by_pair: Dictionnaire des prix par paire
            
        Returns:
            Dict[str, Dict]: Prix normalisés par paire
        """
        normalized = {}
        
        for pair, prices in prices_by_pair.items():
            normalized_price = self.normalize_price(pair, prices)
            if normalized_price is not None:
                normalized[pair] = {
                    'price': normalized_price,
                    'timestamp': datetime.now(),
                    'sources_count': len(prices),
                    'volatility': self.get_price_volatility(pair)
                }
                
        return normalized
    
    def detect_arbitrage_opportunities(self, normalized_prices: Dict[str, Dict], min_spread: float = 0.01) -> List[Dict]:
        """
        Détecte les opportunités d'arbitrage entre les différentes sources.
        
        Args:
            normalized_prices: Prix normalisés par token
            min_spread: Spread minimum pour considérer une opportunité (1% par défaut)
            
        Returns:
            List[Dict]: Liste des opportunités d'arbitrage
        """
        try:
            opportunities = []
            
            for token_address, price_info in normalized_prices.items():
                # Vérifier si on a des prix DEX et CEX
                if 'dex' in price_info and 'cex' in price_info:
                    dex_price = price_info['dex']['price']
                    cex_price = price_info['cex']['price']
                    
                    # Calculer le spread
                    if dex_price == Decimal('0') or cex_price == Decimal('0'):
                        continue
                        
                    spread = abs(dex_price - cex_price) / min(dex_price, cex_price)
                    
                    # Si le spread est suffisant, c'est une opportunité
                    if spread >= Decimal(str(min_spread)):
                        opportunities.append({
                            'token': token_address,
                            'dex_price': dex_price,
                            'cex_price': cex_price,
                            'spread': spread,
                            'dex_exchange': price_info['dex']['exchange'],
                            'cex_exchange': price_info['cex']['exchange'],
                            'liquidity': price_info['dex'].get('liquidity', Decimal('0')),
                            'timestamp': max(price_info['dex']['timestamp'], price_info['cex']['timestamp'])
                        })
            
            # Trier les opportunités par spread décroissant
            opportunities.sort(key=lambda x: x['spread'], reverse=True)
            
            return opportunities
            
        except Exception as e:
            logger.error(f"Erreur lors de la détection des opportunités d'arbitrage: {str(e)}")
            return [] 