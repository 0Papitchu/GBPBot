"""
Module de compatibilité pour les middlewares web3.py.

Ce module fournit des implémentations factices pour les middlewares qui pourraient
ne pas être disponibles dans certaines versions de web3.py.
"""

import logging
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

# Implémentation factice du middleware geth_poa_middleware
def dummy_geth_poa_middleware(make_request: Callable, web3: Any) -> Callable:
    """
    Implémentation factice du middleware geth_poa_middleware.
    
    Cette fonction est utilisée lorsque le middleware geth_poa_middleware n'est pas
    disponible dans la version installée de web3.py.
    
    Args:
        make_request: La fonction de requête à utiliser
        web3: L'instance Web3
        
    Returns:
        Une fonction middleware
    """
    def middleware(method: str, params: Any) -> Dict:
        """Middleware qui ne fait rien de spécial"""
        return make_request(method, params)
    
    return middleware

def get_geth_poa_middleware() -> Callable:
    """
    Récupère le middleware geth_poa_middleware.
    
    Cette fonction tente d'importer le middleware geth_poa_middleware depuis
    différents emplacements connus. Si l'importation échoue, elle renvoie
    une implémentation factice.
    
    Returns:
        Le middleware geth_poa_middleware ou une implémentation factice
    """
    # Essayer d'importer depuis web3.middleware (versions récentes)
    try:
        from web3.middleware import geth_poa_middleware
        logger.info("Middleware geth_poa_middleware importé depuis web3.middleware")
        return geth_poa_middleware
    except ImportError:
        pass
    
    # Essayer d'importer depuis web3.middleware.geth (versions plus anciennes)
    try:
        from web3.middleware.geth import geth_poa_middleware
        logger.info("Middleware geth_poa_middleware importé depuis web3.middleware.geth")
        return geth_poa_middleware
    except ImportError:
        pass
    
    # Essayer d'importer depuis eth_middleware (certaines versions)
    try:
        from eth_middleware import geth_poa_middleware
        logger.info("Middleware geth_poa_middleware importé depuis eth_middleware")
        return geth_poa_middleware
    except ImportError:
        pass
    
    # Utiliser l'implémentation factice
    logger.error("Could not import geth_poa_middleware from any known location")
    logger.info("Using dummy geth_poa_middleware implementation")
    return dummy_geth_poa_middleware 