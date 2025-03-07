"""
Module d'adaptateur pour les imports Solana.

Ce module centralise tous les imports liés à Solana et fournit des classes de remplacement
en cas d'absence des packages requis. Cela permet au reste du code de fonctionner
même si les dépendances Solana ne sont pas disponibles.

À partir de Python 3.11, nous utilisons @solana/web3.js via notre adaptateur plutôt que solana-py.
"""

import logging
from typing import Any, Dict, List, Optional, Union, Tuple, TypeVar

# Configuration du logger
logger = logging.getLogger(__name__)

# Drapeaux pour suivre la disponibilité des packages
SOLANA_AVAILABLE = False
SOLDERS_AVAILABLE = False
ANCHORPY_AVAILABLE = False

# Tentative d'import des adaptateurs Solana Web3.js
try:
    from gbpbot.adapters.solana_web3 import (
        # Classes d'adaptateur
        PublicKey,
        Keypair,
        Transaction,
        TransactionInstruction,
        AccountMeta,
        SystemProgram,
        SYS_PROGRAM_ID,
        AsyncClient,
        Client as SolanaClient,
        Commitment,
        TxOpts,
        transfer,
    )
    SOLANA_AVAILABLE = True
    logger.info("Adaptateur Solana Web3.js importé avec succès")
except ImportError as e:
    logger.warning(f"Impossible d'importer l'adaptateur Solana Web3.js: {e}")
    
    # Classes de remplacement pour les imports manquants
    class DummyKeypair:
        """Classe de remplacement pour solana.keypair.Keypair"""
        def __init__(self, *args, **kwargs):
            self.public_key = DummyPublicKey()
            self.secret_key = b''
            logger.warning("Utilisation de DummyKeypair - le package solana-py n'est pas installé")
        
        @classmethod
        def generate(cls):
            return cls()
        
        @classmethod
        def from_secret_key(cls, secret_key):
            return cls()
        
        def sign(self, *args, **kwargs):
            return b''

    class DummyPublicKey:
        """Classe de remplacement pour solana.publickey.PublicKey"""
        def __init__(self, value=None):
            self.value = value or "DummyPublicKey"
            logger.warning("Utilisation de DummyPublicKey - le package solana-py n'est pas installé")
        
        def __str__(self):
            return str(self.value)
        
        def __eq__(self, other):
            return False
        
        def to_base58(self):
            return "DummyBase58String"

    class DummyPubkey:
        """Classe de remplacement pour solders.pubkey.Pubkey"""
        def __init__(self, value=None):
            self.value = value or "DummyPubkey"
            logger.warning("Utilisation de DummyPubkey - le package solders n'est pas installé")
        
        def __str__(self):
            return str(self.value)
        
        def __eq__(self, other):
            return False
        
        @classmethod
        def from_string(cls, s):
            return cls(s)
        
        def to_string(self):
            return "DummyPubkeyString"
            
    # Utilisation des classes de remplacement
    Keypair = DummyKeypair
    PublicKey = DummyPublicKey
    
    class DummySolanaClient:
        def __init__(self, *args, **kwargs):
            logger.warning("Utilisation de DummySolanaClient - le package solana-py n'est pas installé")
        
        def get_balance(self, *args, **kwargs):
            return {"result": {"value": 0}}
        
        def get_token_accounts_by_owner(self, *args, **kwargs):
            return {"result": {"value": []}}
        
        def get_account_info(self, *args, **kwargs):
            return {"result": {"value": None}}
        
        def send_transaction(self, *args, **kwargs):
            return {"result": "DummyTxSignature"}
    
    SolanaClient = DummySolanaClient
    
    class DummyAsyncClient:
        def __init__(self, *args, **kwargs):
            logger.warning("Utilisation de DummyAsyncClient - le package solana-py n'est pas installé")
        
        async def get_balance(self, *args, **kwargs):
            return {"result": {"value": 0}}
        
        async def get_token_accounts_by_owner(self, *args, **kwargs):
            return {"result": {"value": []}}
        
        async def get_account_info(self, *args, **kwargs):
            return {"result": {"value": None}}
        
        async def send_transaction(self, *args, **kwargs):
            return {"result": "DummyTxSignature"}
        
        async def close(self):
            pass
    
    AsyncClient = DummyAsyncClient
    
    class DummyTransaction:
        def __init__(self, *args, **kwargs):
            self.instructions = []
            logger.warning("Utilisation de DummyTransaction - le package solana-py n'est pas installé")
        
        def add(self, *args, **kwargs):
            return self
        
        def sign(self, *args, **kwargs):
            return self
    
    Transaction = DummyTransaction
    
    class DummyTransactionInstruction:
        def __init__(self, *args, **kwargs):
            logger.warning("Utilisation de DummyTransactionInstruction - le package solana-py n'est pas installé")
    
    TransactionInstruction = DummyTransactionInstruction
    
    class DummyAccountMeta:
        def __init__(self, *args, **kwargs):
            logger.warning("Utilisation de DummyAccountMeta - le package solana-py n'est pas installé")
    
    AccountMeta = DummyAccountMeta
    
    class DummySystemProgram:
        def __init__(self, *args, **kwargs):
            logger.warning("Utilisation de DummySystemProgram - le package solana-py n'est pas installé")
        
        @staticmethod
        def transfer(*args, **kwargs):
            return DummyTransactionInstruction()
    
    SystemProgram = DummySystemProgram
    SYS_PROGRAM_ID = DummyPublicKey("11111111111111111111111111111111")
    
    class DummyCommitment:
        FINALIZED = "finalized"
        CONFIRMED = "confirmed"
        PROCESSED = "processed"
    
    Commitment = DummyCommitment
    
    class DummyTxOpts:
        def __init__(self, *args, **kwargs):
            logger.warning("Utilisation de DummyTxOpts - le package solana-py n'est pas installé")
    
    TxOpts = DummyTxOpts
    
    def transfer(*args, **kwargs):
        logger.warning("Utilisation de la fonction transfer factice - le package solana-py n'est pas installé")
        return DummyTransactionInstruction()

# Tentative d'import des packages Solders
try:
    from solders.pubkey import Pubkey
    from solders.transaction import Transaction as SoldersTransaction
    from solders.instruction import Instruction as SoldersInstruction
    SOLDERS_AVAILABLE = True
    logger.info("Package solders importé avec succès")
except ImportError as e:
    logger.warning(f"Impossible d'importer le package solders: {e}")
    # Utilisation des classes de remplacement
    Pubkey = DummyPubkey
    
    class DummySoldersTransaction:
        def __init__(self, *args, **kwargs):
            logger.warning("Utilisation de DummySoldersTransaction - le package solders n'est pas installé")
        
        def sign(self, *args, **kwargs):
            return self
    
    SoldersTransaction = DummySoldersTransaction
    
    class DummySoldersInstruction:
        def __init__(self, *args, **kwargs):
            logger.warning("Utilisation de DummySoldersInstruction - le package solders n'est pas installé")
    
    SoldersInstruction = DummySoldersInstruction

# Tentative d'import des packages AnchorPy
try:
    import anchorpy
    ANCHORPY_AVAILABLE = True
    logger.info("Package anchorpy importé avec succès")
except ImportError as e:
    logger.warning(f"Impossible d'importer le package anchorpy: {e}")
    # AnchorPy est plus complexe, nous ne fournissons pas de remplacement complet

def check_solana_dependencies() -> Dict[str, bool]:
    """
    Vérifie la disponibilité des dépendances Solana.
    
    Returns:
        Dict[str, bool]: Dictionnaire indiquant la disponibilité de chaque package
    """
    return {
        "solana": SOLANA_AVAILABLE,
        "solders": SOLDERS_AVAILABLE,
        "anchorpy": ANCHORPY_AVAILABLE
    }

def get_dependency_status() -> str:
    """
    Retourne un message sur l'état des dépendances.
    
    Returns:
        str: Message décrivant l'état des dépendances
    """
    status = check_solana_dependencies()
    if all(status.values()):
        return "Toutes les dépendances Solana sont disponibles."
    
    missing = [pkg for pkg, available in status.items() if not available]
    if missing:
        return f"Dépendances Solana manquantes: {', '.join(missing)}. Certaines fonctionnalités seront limitées."
    
    return "État des dépendances Solana inconnu."

# Définir des types pour les annotations
PubkeyType = Union[str, 'PublicKey', 'Pubkey', 'DummyPublicKey', 'DummyPubkey']
PublicKeyType = Optional['PublicKey']
PubkeyResultType = Optional['Pubkey']

def convert_pubkey_types(pubkey: PubkeyType) -> Tuple[PublicKeyType, PubkeyResultType]:
    """
    Convertit entre différents types de clés publiques.
    
    Args:
        pubkey: Clé publique à convertir (peut être une chaîne, PublicKey ou Pubkey)
        
    Returns:
        Tuple[Optional[PublicKey], Optional[Pubkey]]: Tuple contenant les versions PublicKey et Pubkey
    """
    solana_pubkey = None
    solders_pubkey = None
    
    if isinstance(pubkey, str):
        try:
            if SOLANA_AVAILABLE:
                solana_pubkey = PublicKey(pubkey)
            if SOLDERS_AVAILABLE:
                solders_pubkey = Pubkey.from_string(pubkey)
        except Exception as e:
            logger.error(f"Erreur lors de la conversion de la clé publique: {e}")
    elif isinstance(pubkey, PublicKey) or isinstance(pubkey, DummyPublicKey):
        solana_pubkey = pubkey
        if SOLDERS_AVAILABLE and not isinstance(pubkey, DummyPublicKey):
            try:
                solders_pubkey = Pubkey.from_string(str(pubkey))
            except Exception as e:
                logger.error(f"Erreur lors de la conversion de PublicKey vers Pubkey: {e}")
    elif isinstance(pubkey, Pubkey) or isinstance(pubkey, DummyPubkey):
        solders_pubkey = pubkey
        if SOLANA_AVAILABLE and not isinstance(pubkey, DummyPubkey):
            try:
                solana_pubkey = PublicKey(str(pubkey))
            except Exception as e:
                logger.error(f"Erreur lors de la conversion de Pubkey vers PublicKey: {e}")
    
    return solana_pubkey, solders_pubkey 