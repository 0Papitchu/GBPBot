"""
Module d'adaptateurs pour les bibliothèques externes.

Ce module contient des adaptateurs permettant à GBPBot d'interagir avec différentes
bibliothèques et APIs externes, y compris des adaptateurs pour les blockchains.
"""

import logging

logger = logging.getLogger(__name__)

# Export des classes et fonctions d'adaptateur Solana
try:
    from gbpbot.adapters.solana_web3 import (
        # Classe principale d'adaptateur
        SolanaWeb3Adapter,
        
        # Classes de remplacement pour solana-py
        PublicKey,
        Keypair,
        Transaction,
        TransactionInstruction,
        AccountMeta,
        SystemProgram,
        SYS_PROGRAM_ID,
        
        # Clients Solana
        AsyncClient,
        Client,
        
        # Types et utilitaires
        Commitment,
        TxOpts,
        transfer,
    )

    logger.info("Les adaptateurs Solana Web3.js ont été chargés avec succès.")
    solana_adapter_available = True

except ImportError as e:
    logger.warning(f"Impossible de charger l'adaptateur Solana: {e}")
    solana_adapter_available = False

__all__ = [
    # Constantes de disponibilité
    "solana_adapter_available",
    
    # Classes d'adaptateur Solana (si disponibles)
    "SolanaWeb3Adapter",
    "PublicKey",
    "Keypair",
    "Transaction",
    "TransactionInstruction",
    "AccountMeta",
    "SystemProgram",
    "SYS_PROGRAM_ID",
    "AsyncClient",
    "Client",
    "Commitment",
    "TxOpts",
    "transfer",
] 