from typing import Dict, List, Optional
from decimal import Decimal
import logging

from gbpbot.core.price_feed.price_normalizer import PriceNormalizer as EnhancedPriceNormalizer

logger = logging.getLogger(__name__)

class PriceNormalizer(EnhancedPriceNormalizer):
    """
    Version archivée du normalisateur de prix.
    Cette classe hérite de la version améliorée pour maintenir la compatibilité.
    
    À terme, il est recommandé de migrer vers EnhancedPriceNormalizer 
    directement et de supprimer cette classe.
    """
    
    def __init__(self, config: Dict = None):
        """
        Initialise le normalisateur de prix compatible.
        
        Args:
            config: Configuration du normalisateur
        """
        super().__init__(config or {})
        logger.warning("Utilisation de la classe PriceNormalizer dépréciée. "
                      "Veuillez migrer vers EnhancedPriceNormalizer.")

    def normalize_price(self, token: str, prices: List[Dict]) -> Optional[Decimal]:
        """
        Normalise les prix d'un token à partir de différentes sources.
        
        Args:
            token: Adresse ou symbole du token
            prices: Liste des prix avec leur source et timestamp
            
        Returns:
            Optional[Decimal]: Prix normalisé ou None si pas assez de données valides
        """
        if not prices or len(prices) < self.min_sources:
            logger.warning(f"Pas assez de sources de prix pour {token}")
            return None
            
        # Filtrer les prix invalides et les outliers
        valid_prices = self._filter_prices(prices)
        if len(valid_prices) < self.min_sources:
            logger.warning(f"Pas assez de prix valides après filtrage pour {token}")
            return None
            
        # Calculer le prix normalisé (moyenne pondérée par la liquidité)
        try:
            weighted_prices = []
            total_weight = Decimal(0)
            
            for price_info in valid_prices:
                price = Decimal(price_info['price'])
                weight = Decimal(price_info.get('liquidity', 1))
                weighted_prices.append(price * weight)
                total_weight += weight
                
            if total_weight == 0:
                return statistics.median([Decimal(p['price']) for p in valid_prices])
                
            normalized_price = sum(weighted_prices) / total_weight
            
            # Mettre à jour l'historique
            self._update_history(token, normalized_price)
            
            return normalized_price
            
        except Exception as e:
            logger.error(f"Erreur lors de la normalisation des prix pour {token}: {str(e)}")
            return None
            
    def _filter_prices(self, prices: List[Dict]) -> List[Dict]:
        """
        Filtre les prix invalides et les outliers.
        
        Args:
            prices: Liste des prix à filtrer
            
        Returns:
            List[Dict]: Prix filtrés
        """
        # Enlever les prix nuls ou négatifs
        valid_prices = [p for p in prices if Decimal(p['price']) > 0]
        
        if not valid_prices:
            return []
            
        # Calculer la médiane et l'écart-type
        price_values = [Decimal(p['price']) for p in valid_prices]
        median_price = statistics.median(price_values)
        
        try:
            std_dev = statistics.stdev(price_values)
        except statistics.StatisticsError:
            # Pas assez de données pour calculer l'écart-type
            return valid_prices
            
        # Filtrer les outliers
        filtered_prices = []
        for price_info in valid_prices:
            price = Decimal(price_info['price'])
            deviation = abs(price - median_price) / std_dev
            
            if deviation <= self.outlier_threshold:
                filtered_prices.append(price_info)
            else:
                logger.warning(f"Prix outlier détecté: {price} (déviation: {deviation:.2f})")
                
        return filtered_prices
        
    def _update_history(self, token: str, price: Decimal) -> None:
        """
        Met à jour l'historique des prix pour un token.
        
        Args:
            token: Adresse ou symbole du token
            price: Prix normalisé
        """
        if token not in self.price_history:
            self.price_history[token] = []
            
        history = self.price_history[token]
        history.append(price)
        
        # Garder uniquement les N derniers prix
        max_history = self.config.get('max_history_size', 100)
        if len(history) > max_history:
            self.price_history[token] = history[-max_history:]
            
    def get_price_volatility(self, token: str) -> Optional[Decimal]:
        """
        Calcule la volatilité des prix d'un token.
        
        Args:
            token: Adresse ou symbole du token
            
        Returns:
            Optional[Decimal]: Volatilité ou None si pas assez d'historique
        """
        if token not in self.price_history:
            return None
            
        history = self.price_history[token]
        if len(history) < 2:
            return None
            
        try:
            # Calculer l'écart-type relatif (coefficient de variation)
            mean_price = statistics.mean(history)
            std_dev = statistics.stdev(history)
            return Decimal(std_dev) / Decimal(mean_price)
            
        except statistics.StatisticsError:
            return None
            
    def is_price_stable(self, token: str) -> bool:
        """
        Vérifie si le prix d'un token est stable.
        
        Args:
            token: Adresse ou symbole du token
            
        Returns:
            bool: True si le prix est stable
        """
        volatility = self.get_price_volatility(token)
        if volatility is None:
            return False
            
        max_volatility = self.config.get('max_volatility', 0.02)  # 2% par défaut
        return volatility <= Decimal(max_volatility) 