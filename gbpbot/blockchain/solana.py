"""
Module d'interface avec la blockchain Solana pour GBPBot
=====================================================

Ce module fournit une interface de haut niveau pour interagir avec
la blockchain Solana, incluant la surveillance des blocs, la découverte
des tokens, et les interactions avec les programmes Solana.
"""

import os
import json
import time
import base64
import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple, Union, Callable, Set
from dataclasses import dataclass
from datetime import datetime

# Configurer le logging
logger = logging.getLogger(__name__)

# Importer les modules GBPBot
try:
    from gbpbot.core import config
    from gbpbot.core import rpc
    from gbpbot.core import wallet
except ImportError as e:
    logger.warning(f"ImportError: {e}")
    logger.warning("Certaines fonctionnalités peuvent être limitées")
    config = None
    rpc = None
    wallet = None


@dataclass
class TokenInfo:
    """Information sur un token Solana"""
    mint: str
    symbol: str = "Unknown"
    name: str = "Unknown Token"
    decimals: int = 9
    total_supply: Optional[int] = None
    logo_uri: Optional[str] = None
    price_usd: Optional[float] = None
    volume_24h: Optional[float] = None
    market_cap: Optional[float] = None
    is_verified: bool = False
    is_liquidity_token: bool = False
    creation_date: Optional[float] = None
    

@dataclass
class BlockInfo:
    """Information sur un bloc Solana"""
    slot: int
    blockhash: str
    parent_blockhash: str
    timestamp: float
    height: Optional[int] = None
    transaction_count: int = 0
    is_finalized: bool = False


@dataclass
class TransactionInfo:
    """Information sur une transaction Solana"""
    signature: str
    slot: int
    timestamp: Optional[float] = None
    fee: int = 0
    status: str = "Unknown"
    confirmations: Optional[int] = None
    recent_blockhash: Optional[str] = None
    program_ids: List[str] = None
    
    def __post_init__(self):
        if self.program_ids is None:
            self.program_ids = []


class SolanaMonitor:
    """Moniteur de blockchain Solana"""
    
    # Programmes SPL Token
    TOKEN_PROGRAM_ID = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
    ASSOCIATED_TOKEN_PROGRAM_ID = "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"
    
    # Programmes populaires
    SERUM_DEX_PROGRAM_ID = "9xQeWvG816bUx9EPjHmaT23yvVM2ZWbrrpZb9PusVFin"
    RAYDIUM_LIQUIDITY_PROGRAM_ID = "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"
    JUPITER_PROGRAM_ID = "JUP4Fb2cqiRUcaTHdrPC8h2gNsA2ETXiPDD33WcGuJB"
    
    def __init__(self):
        """Initialise le moniteur Solana"""
        # État
        self.is_running = False
        self.monitor_task = None
        
        # Configurations
        self.monitor_interval = 2.0  # secondes
        self.finalized_only = True
        self.confirmed_blocks: Dict[int, BlockInfo] = {}
        self.processed_signatures: Set[str] = set()
        self.latest_slot = 0
        
        # Dictionnaire des tokens connus
        self.known_tokens: Dict[str, TokenInfo] = {}
        
        # Callbacks
        self.new_block_callbacks: List[Callable[[BlockInfo], None]] = []
        self.new_transaction_callbacks: List[Callable[[TransactionInfo], None]] = []
        self.new_token_callbacks: List[Callable[[TokenInfo], None]] = []
        
        # Chargement de tokens connus depuis un fichier JSON si disponible
        self._load_known_tokens()
        
        # Configurer les paramètres de surveillance
        self._load_config()
        
    def _load_config(self) -> None:
        """Charge la configuration depuis le gestionnaire de configuration"""
        if not config:
            return
            
        try:
            # Charger les paramètres de surveillance
            monitor_config = config.get("blockchain.solana.monitor", {})
            
            self.monitor_interval = monitor_config.get("interval", self.monitor_interval)
            self.finalized_only = monitor_config.get("finalized_only", self.finalized_only)
            
            # Adapter les paramètres en fonction du mode de performance
            performance_mode = config.get("performance_mode", "balanced")
            
            if performance_mode == "high":
                self.monitor_interval = 1.0
            elif performance_mode == "economy":
                self.monitor_interval = 5.0
                
        except Exception as e:
            logger.error(f"Erreur lors du chargement de la configuration: {e}")
            
    def _load_known_tokens(self) -> None:
        """Charge les tokens connus depuis un fichier JSON"""
        try:
            # Chemin par défaut pour les tokens connus
            base_dir = os.path.dirname(os.path.abspath(__file__))
            tokens_file = os.path.join(base_dir, "known_tokens.json")
            
            if os.path.exists(tokens_file):
                with open(tokens_file, "r") as f:
                    tokens_data = json.load(f)
                    
                for mint, token_data in tokens_data.items():
                    self.known_tokens[mint] = TokenInfo(
                        mint=mint,
                        symbol=token_data.get("symbol", "Unknown"),
                        name=token_data.get("name", "Unknown Token"),
                        decimals=token_data.get("decimals", 9),
                        total_supply=token_data.get("total_supply"),
                        logo_uri=token_data.get("logo_uri"),
                        price_usd=token_data.get("price_usd"),
                        volume_24h=token_data.get("volume_24h"),
                        market_cap=token_data.get("market_cap"),
                        is_verified=token_data.get("is_verified", False),
                        is_liquidity_token=token_data.get("is_liquidity_token", False),
                        creation_date=token_data.get("creation_date")
                    )
                    
                logger.info(f"Chargement de {len(self.known_tokens)} tokens connus")
                
        except Exception as e:
            logger.error(f"Erreur lors du chargement des tokens connus: {e}")
            
    def _save_known_tokens(self) -> None:
        """Sauvegarde les tokens connus dans un fichier JSON"""
        try:
            # Chemin par défaut pour les tokens connus
            base_dir = os.path.dirname(os.path.abspath(__file__))
            tokens_file = os.path.join(base_dir, "known_tokens.json")
            
            tokens_data = {}
            for mint, token in self.known_tokens.items():
                tokens_data[mint] = {
                    "symbol": token.symbol,
                    "name": token.name,
                    "decimals": token.decimals,
                    "total_supply": token.total_supply,
                    "logo_uri": token.logo_uri,
                    "price_usd": token.price_usd,
                    "volume_24h": token.volume_24h,
                    "market_cap": token.market_cap,
                    "is_verified": token.is_verified,
                    "is_liquidity_token": token.is_liquidity_token,
                    "creation_date": token.creation_date
                }
                
            with open(tokens_file, "w") as f:
                json.dump(tokens_data, f, indent=2)
                
            logger.debug(f"Sauvegarde de {len(self.known_tokens)} tokens connus")
            
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des tokens connus: {e}")
            
    async def start_monitoring(self) -> None:
        """Démarre la surveillance de la blockchain"""
        if self.is_running:
            logger.warning("Le moniteur est déjà en cours d'exécution")
            return
            
        if rpc is None:
            logger.error("Module RPC non disponible")
            return
            
        # Démarrer le gestionnaire RPC s'il n'est pas déjà démarré
        if hasattr(rpc, 'start'):
            await rpc.start()
            
        # Démarrer la surveillance
        self.is_running = True
        self.monitor_task = asyncio.create_task(self._monitoring_loop())
        
        logger.info("Surveillance de la blockchain Solana démarrée")
        
    async def stop_monitoring(self) -> None:
        """Arrête la surveillance de la blockchain"""
        if not self.is_running:
            logger.warning("Le moniteur n'est pas en cours d'exécution")
            return
            
        # Arrêter la surveillance
        self.is_running = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
                
        # Sauvegarder les tokens connus
        self._save_known_tokens()
        
        logger.info("Surveillance de la blockchain Solana arrêtée")
        
    async def _monitoring_loop(self) -> None:
        """Boucle principale de surveillance"""
        while self.is_running:
            try:
                # Récupérer le dernier slot
                commitment = "finalized" if self.finalized_only else "confirmed"
                slot_info = await rpc.call("getSlot", [{"commitment": commitment}])
                
                current_slot = slot_info
                
                # Si c'est un nouveau slot
                if current_slot > self.latest_slot:
                    # Récupérer les informations sur le bloc
                    await self._process_new_slot(current_slot)
                    self.latest_slot = current_slot
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Erreur lors de la surveillance: {e}")
                
            # Attendre avant la prochaine vérification
            await asyncio.sleep(self.monitor_interval)
            
    async def _process_new_slot(self, slot: int) -> None:
        """
        Traite un nouveau slot
        
        Args:
            slot: Numéro du slot
        """
        try:
            # Récupérer les informations sur le bloc
            commitment = "finalized" if self.finalized_only else "confirmed"
            block_info = await rpc.call("getBlock", [
                slot,
                {
                    "encoding": "json",
                    "commitment": commitment,
                    "transactionDetails": "full",
                    "maxSupportedTransactionVersion": 0
                }
            ])
            
            if not block_info:
                return
                
            # Créer l'objet BlockInfo
            block = BlockInfo(
                slot=slot,
                blockhash=block_info.get("blockhash", ""),
                parent_blockhash=block_info.get("previousBlockhash", ""),
                timestamp=block_info.get("blockTime", time.time()),
                height=block_info.get("blockHeight"),
                transaction_count=len(block_info.get("transactions", [])),
                is_finalized=commitment == "finalized"
            )
            
            # Enregistrer le bloc
            self.confirmed_blocks[slot] = block
            
            # Notifier les abonnés
            for callback in self.new_block_callbacks:
                try:
                    callback(block)
                except Exception as e:
                    logger.error(f"Erreur lors de l'appel d'un callback de bloc: {e}")
                    
            # Traiter les transactions
            await self._process_block_transactions(block_info, block)
            
            # Limiter le nombre de blocs stockés (garder les 100 derniers)
            if len(self.confirmed_blocks) > 100:
                oldest_slot = min(self.confirmed_blocks.keys())
                del self.confirmed_blocks[oldest_slot]
                
        except Exception as e:
            logger.error(f"Erreur lors du traitement du slot {slot}: {e}")
            
    async def _process_block_transactions(self, block_info: Dict[str, Any], block: BlockInfo) -> None:
        """
        Traite les transactions d'un bloc
        
        Args:
            block_info: Informations sur le bloc
            block: Objet BlockInfo
        """
        transactions = block_info.get("transactions", [])
        
        for tx_data in transactions:
            try:
                # Extraire les informations de base de la transaction
                meta = tx_data.get("meta", {})
                transaction = tx_data.get("transaction", {})
                
                # Vérifier si la transaction a réussi
                if meta.get("err") is not None:
                    continue  # Ignorer les transactions qui ont échoué
                    
                # Extraire la signature
                signatures = transaction.get("signatures", [])
                if not signatures:
                    continue
                    
                signature = signatures[0]
                
                # Vérifier si cette transaction a déjà été traitée
                if signature in self.processed_signatures:
                    continue
                    
                self.processed_signatures.add(signature)
                
                # Limiter le nombre de signatures stockées
                if len(self.processed_signatures) > 10000:
                    self.processed_signatures = set(list(self.processed_signatures)[-5000:])
                    
                # Extraire les programmes utilisés
                program_ids = []
                for instruction in transaction.get("message", {}).get("instructions", []):
                    program_idx = instruction.get("programIdIndex")
                    if program_idx is not None:
                        account_keys = transaction.get("message", {}).get("accountKeys", [])
                        if 0 <= program_idx < len(account_keys):
                            program_id = account_keys[program_idx]
                            program_ids.append(program_id)
                            
                # Créer l'objet TransactionInfo
                tx_info = TransactionInfo(
                    signature=signature,
                    slot=block.slot,
                    timestamp=block.timestamp,
                    fee=meta.get("fee", 0),
                    status="Success",
                    confirmations=1,  # Nouveau bloc, donc 1 confirmation
                    recent_blockhash=transaction.get("message", {}).get("recentBlockhash"),
                    program_ids=program_ids
                )
                
                # Notifier les abonnés
                for callback in self.new_transaction_callbacks:
                    try:
                        callback(tx_info)
                    except Exception as e:
                        logger.error(f"Erreur lors de l'appel d'un callback de transaction: {e}")
                        
                # Vérifier si c'est une transaction de création de token
                if self.TOKEN_PROGRAM_ID in program_ids:
                    await self._check_for_new_token(tx_info, tx_data)
                    
            except Exception as e:
                logger.error(f"Erreur lors du traitement d'une transaction: {e}")
                
    async def _check_for_new_token(self, tx_info: TransactionInfo, tx_data: Dict[str, Any]) -> None:
        """
        Vérifie si une transaction contient la création d'un nouveau token
        
        Args:
            tx_info: Informations sur la transaction
            tx_data: Données brutes de la transaction
        """
        try:
            # Cette fonction est simplifiée pour l'exemple
            # Une implémentation complète nécessiterait de parser les instructions
            # pour détecter les appels à MintTo, InitializeMint, etc.
            
            # Exemple simplifié: vérifier si un compte de token a été créé
            # en regardant les changements de solde des comptes
            
            # Pour une implémentation complète, il faudrait utiliser le décodage des instructions
            # avec les layouts Solana pour identifier précisément les créations de tokens
            
            meta = tx_data.get("meta", {})
            post_token_balances = meta.get("postTokenBalances", [])
            
            for balance in post_token_balances:
                mint = balance.get("mint")
                
                # Si c'est un nouveau token non connu
                if mint and mint not in self.known_tokens:
                    logger.info(f"Potentiel nouveau token détecté: {mint}")
                    
                    # Essayer d'obtenir des informations sur le token
                    try:
                        token_info = await self.get_token_info(mint)
                        if token_info:
                            # Ajouter aux tokens connus
                            self.known_tokens[mint] = token_info
                            
                            # Notifier les abonnés
                            for callback in self.new_token_callbacks:
                                try:
                                    callback(token_info)
                                except Exception as e:
                                    logger.error(f"Erreur lors de l'appel d'un callback de token: {e}")
                                    
                    except Exception as e:
                        logger.error(f"Erreur lors de la récupération des infos du token {mint}: {e}")
                        
        except Exception as e:
            logger.error(f"Erreur lors de la vérification de nouveaux tokens: {e}")
            
    def register_new_block_callback(self, callback: Callable[[BlockInfo], None]) -> None:
        """
        Enregistre un callback pour les nouveaux blocs
        
        Args:
            callback: Fonction à appeler pour chaque nouveau bloc
        """
        if callback not in self.new_block_callbacks:
            self.new_block_callbacks.append(callback)
            
    def register_new_transaction_callback(self, callback: Callable[[TransactionInfo], None]) -> None:
        """
        Enregistre un callback pour les nouvelles transactions
        
        Args:
            callback: Fonction à appeler pour chaque nouvelle transaction
        """
        if callback not in self.new_transaction_callbacks:
            self.new_transaction_callbacks.append(callback)
            
    def register_new_token_callback(self, callback: Callable[[TokenInfo], None]) -> None:
        """
        Enregistre un callback pour les nouveaux tokens
        
        Args:
            callback: Fonction à appeler pour chaque nouveau token
        """
        if callback not in self.new_token_callbacks:
            self.new_token_callbacks.append(callback)
            
    def unregister_callback(self, callback: Callable) -> None:
        """
        Supprime un callback
        
        Args:
            callback: Callback à supprimer
        """
        if callback in self.new_block_callbacks:
            self.new_block_callbacks.remove(callback)
            
        if callback in self.new_transaction_callbacks:
            self.new_transaction_callbacks.remove(callback)
            
        if callback in self.new_token_callbacks:
            self.new_token_callbacks.remove(callback)
            
    async def get_token_info(self, mint: str) -> Optional[TokenInfo]:
        """
        Récupère les informations sur un token
        
        Args:
            mint: Adresse du token (pubkey du mint)
            
        Returns:
            Informations sur le token ou None si non trouvé
        """
        if not rpc:
            return None
            
        # Vérifier si le token est déjà connu
        if mint in self.known_tokens:
            return self.known_tokens[mint]
            
        try:
            # Récupérer les informations sur le mint
            account_info = await rpc.call("getAccountInfo", [
                mint,
                {"encoding": "jsonParsed"}
            ])
            
            if not account_info:
                return None
                
            # Vérifier si c'est bien un compte de mint
            data = account_info.get("data", {})
            if isinstance(data, dict) and data.get("program") == "spl-token":
                parsed_data = data.get("parsed", {})
                if parsed_data.get("type") == "mint":
                    mint_info = parsed_data.get("info", {})
                    
                    # Créer l'objet TokenInfo
                    decimals = mint_info.get("decimals", 9)
                    supply = mint_info.get("supply")
                    
                    token_info = TokenInfo(
                        mint=mint,
                        decimals=decimals,
                        total_supply=int(supply) if supply else None,
                        creation_date=time.time()  # Date actuelle comme approximation
                    )
                    
                    # Essayer de récupérer des informations supplémentaires
                    # via des services externes (simplifiable dans une implémentation réelle)
                    # Cette partie pourrait utiliser des API comme solscan, coingecko, etc.
                    
                    return token_info
                    
            return None
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des infos du token {mint}: {e}")
            return None
            
    async def get_token_accounts(self, owner: str) -> List[Dict[str, Any]]:
        """
        Récupère tous les comptes de tokens possédés par une adresse
        
        Args:
            owner: Adresse du propriétaire
            
        Returns:
            Liste des comptes de tokens
        """
        if not rpc:
            return []
            
        try:
            # Utiliser getTokenAccountsByOwner
            response = await rpc.call("getTokenAccountsByOwner", [
                owner,
                {"programId": self.TOKEN_PROGRAM_ID},
                {"encoding": "jsonParsed"}
            ])
            
            if not response or "value" not in response:
                return []
                
            token_accounts = []
            
            for item in response["value"]:
                try:
                    data = item.get("account", {}).get("data", {})
                    if isinstance(data, dict) and data.get("program") == "spl-token":
                        parsed_data = data.get("parsed", {})
                        if parsed_data.get("type") == "account":
                            info = parsed_data.get("info", {})
                            
                            # Extraire les informations du compte
                            mint = info.get("mint")
                            token_amount = info.get("tokenAmount", {})
                            
                            # Créer l'entrée pour ce compte
                            token_account = {
                                "pubkey": item.get("pubkey"),
                                "mint": mint,
                                "amount": int(token_amount.get("amount", 0)),
                                "decimals": token_amount.get("decimals", 9),
                                "ui_amount": token_amount.get("uiAmount", 0)
                            }
                            
                            # Ajouter des infos supplémentaires si le token est connu
                            if mint in self.known_tokens:
                                token = self.known_tokens[mint]
                                token_account["symbol"] = token.symbol
                                token_account["name"] = token.name
                                token_account["price_usd"] = token.price_usd
                                
                            token_accounts.append(token_account)
                            
                except Exception as e:
                    logger.error(f"Erreur lors du traitement d'un compte de token: {e}")
                    
            return token_accounts
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des comptes de tokens pour {owner}: {e}")
            return []
            
    async def get_recent_transactions(self, address: str, limit: int = 10) -> List[TransactionInfo]:
        """
        Récupère les transactions récentes pour une adresse
        
        Args:
            address: Adresse à surveiller
            limit: Nombre maximum de transactions à récupérer
            
        Returns:
            Liste des transactions récentes
        """
        if not rpc:
            return []
            
        try:
            # Récupérer les signatures récentes
            signatures = await rpc.call("getSignaturesForAddress", [
                address,
                {"limit": limit}
            ])
            
            if not signatures:
                return []
                
            transactions = []
            
            for sig_info in signatures:
                try:
                    signature = sig_info.get("signature")
                    
                    # Récupérer les détails de la transaction
                    tx_info = await rpc.call("getTransaction", [
                        signature,
                        {"encoding": "jsonParsed"}
                    ])
                    
                    if tx_info:
                        # Extraire les informations de la transaction
                        meta = tx_info.get("meta", {})
                        slot = tx_info.get("slot", 0)
                        block_time = tx_info.get("blockTime", time.time())
                        
                        # Extraire les programmes utilisés
                        program_ids = []
                        transaction = tx_info.get("transaction", {})
                        for instruction in transaction.get("message", {}).get("instructions", []):
                            program_idx = instruction.get("programIdIndex")
                            if program_idx is not None:
                                account_keys = transaction.get("message", {}).get("accountKeys", [])
                                if 0 <= program_idx < len(account_keys):
                                    program_id = account_keys[program_idx]
                                    program_ids.append(program_id)
                                    
                        # Créer l'objet TransactionInfo
                        tx = TransactionInfo(
                            signature=signature,
                            slot=slot,
                            timestamp=block_time,
                            fee=meta.get("fee", 0),
                            status="Success" if meta.get("err") is None else "Failed",
                            confirmations=tx_info.get("confirmations"),
                            recent_blockhash=transaction.get("message", {}).get("recentBlockhash"),
                            program_ids=program_ids
                        )
                        
                        transactions.append(tx)
                        
                except Exception as e:
                    logger.error(f"Erreur lors du traitement de la transaction {signature}: {e}")
                    
            return transactions
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des transactions pour {address}: {e}")
            return []
            
    async def get_latest_price(self, token_mint: str) -> Optional[float]:
        """
        Récupère le dernier prix d'un token (simplifiée)
        
        Args:
            token_mint: Adresse du token
            
        Returns:
            Prix en USD ou None si non disponible
        """
        # Cette fonction est simplifiée pour l'exemple
        # Une implémentation réelle nécessiterait de:
        # 1. Interroger les DEX comme Serum/Raydium pour obtenir les prix
        # 2. Utiliser des agrégateurs comme Jupiter pour obtenir des prix précis
        # 3. Potentiellement utiliser des API externes pour les tokens moins liquides
        
        # Vérifier si le token est déjà connu avec un prix
        if token_mint in self.known_tokens and self.known_tokens[token_mint].price_usd is not None:
            return self.known_tokens[token_mint].price_usd
            
        logger.info(f"Récupération du prix pour {token_mint} non implementée")
        return None
        
    async def estimate_transaction_fee(self, use_priority_fee: bool = False) -> int:
        """
        Estime les frais de transaction
        
        Args:
            use_priority_fee: Utiliser des frais prioritaires
            
        Returns:
            Frais estimés en lamports
        """
        if not rpc:
            return 5000  # Frais par défaut
            
        try:
            # Récupérer les frais récents
            fees = await rpc.call("getRecentPrioritizationFees")
            
            if not fees or len(fees) == 0:
                return 5000  # Frais par défaut
                
            # Calculer la moyenne des frais
            recent_fees = [fee.get("prioritizationFee", 0) for fee in fees]
            avg_priority_fee = sum(recent_fees) / len(recent_fees)
            
            # Récupérer le prix de base
            last_valid_block_height = fees[0].get("slot", 0)
            
            fee_info = await rpc.call("getFees", [{"commitment": "confirmed"}])
            if not fee_info:
                return 5000
                
            base_fee = fee_info.get("feeCalculator", {}).get("lamportsPerSignature", 5000)
            
            # Calculer les frais totaux
            if use_priority_fee:
                # Ajouter des frais prioritaires (estimation simplifiée)
                priority_multiplier = 1.5
                return int(base_fee + (avg_priority_fee * priority_multiplier))
            else:
                return base_fee
                
        except Exception as e:
            logger.error(f"Erreur lors de l'estimation des frais: {e}")
            return 5000  # Frais par défaut


# Instance globale du moniteur Solana
solana_monitor = SolanaMonitor()

# Fonctions d'accès simplifiées
async def start_monitoring() -> None:
    """Démarre la surveillance de la blockchain"""
    await solana_monitor.start_monitoring()

async def stop_monitoring() -> None:
    """Arrête la surveillance de la blockchain"""
    await solana_monitor.stop_monitoring()

def register_new_block_callback(callback: Callable[[BlockInfo], None]) -> None:
    """Enregistre un callback pour les nouveaux blocs"""
    solana_monitor.register_new_block_callback(callback)

def register_new_transaction_callback(callback: Callable[[TransactionInfo], None]) -> None:
    """Enregistre un callback pour les nouvelles transactions"""
    solana_monitor.register_new_transaction_callback(callback)

def register_new_token_callback(callback: Callable[[TokenInfo], None]) -> None:
    """Enregistre un callback pour les nouveaux tokens"""
    solana_monitor.register_new_token_callback(callback)

def unregister_callback(callback: Callable) -> None:
    """Supprime un callback"""
    solana_monitor.unregister_callback(callback)

async def get_token_info(mint: str) -> Optional[TokenInfo]:
    """Récupère les informations sur un token"""
    return await solana_monitor.get_token_info(mint)

async def get_token_accounts(owner: str) -> List[Dict[str, Any]]:
    """Récupère tous les comptes de tokens possédés par une adresse"""
    return await solana_monitor.get_token_accounts(owner)

async def get_recent_transactions(address: str, limit: int = 10) -> List[TransactionInfo]:
    """Récupère les transactions récentes pour une adresse"""
    return await solana_monitor.get_recent_transactions(address, limit)

async def get_latest_price(token_mint: str) -> Optional[float]:
    """Récupère le dernier prix d'un token"""
    return await solana_monitor.get_latest_price(token_mint)

async def estimate_transaction_fee(use_priority_fee: bool = False) -> int:
    """Estime les frais de transaction"""
    return await solana_monitor.estimate_transaction_fee(use_priority_fee) 