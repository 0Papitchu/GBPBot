from abc import ABC, abstractmethod
from typing import Dict, Optional
from decimal import Decimal

class BasePriceFeed(ABC):
    """Classe abstraite de base pour les price feeds."""
    
    def __init__(self, config: Dict):
        self.config = config
        self.is_running = False
        
    @abstractmethod
    async def start(self) -> None:
        """Démarre le price feed."""
        pass
        
    @abstractmethod
    async def stop(self) -> None:
        """Arrête le price feed."""
        pass
        
    @abstractmethod
    async def get_price(self, token_address: str) -> Optional[Decimal]:
        """Récupère le prix d'un token."""
        pass
        
    @abstractmethod
    async def get_liquidity(self, token_address: str) -> Optional[Decimal]:
        """Récupère la liquidité d'un token."""
        pass
        
    @abstractmethod
    async def validate_price(self, token_address: str, price: Decimal) -> bool:
        """Valide si un prix est cohérent."""
        pass 