#!/usr/bin/env python3
"""
Module de gestion des transactions blockchain.
"""

from gbpbot.core.transaction.transaction_manager import TransactionManager, get_transaction_manager
from gbpbot.core.transaction.transaction_service import TransactionService, get_transaction_service

__all__ = [
    'TransactionManager',
    'get_transaction_manager',
    'TransactionService',
    'get_transaction_service',
    'initialize_transaction_system',
    'shutdown_transaction_system'
]

async def initialize_transaction_system(monitor):
    """
    Initialise le système de transactions.
    
    Args:
        monitor: Moniteur du bot
        
    Returns:
        TransactionService: Service de transactions
    """
    service = get_transaction_service(monitor)
    await service.start()
    return service

async def shutdown_transaction_system():
    """
    Arrête le système de transactions.
    """
    from gbpbot.core.transaction.transaction_service import transaction_service
    if transaction_service:
        await transaction_service.stop() 