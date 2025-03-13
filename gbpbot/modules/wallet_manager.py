"""
Gestionnaire de Wallets pour GBPBot
==================================

Ce module fournit une gestion unifiée des wallets pour différentes blockchains,
permettant de stocker, récupérer et gérer les clés privées, adresses et soldes
de manière sécurisée et organisée.

Il prend en charge différentes blockchains comme Avalanche, Solana et Sonic.
"""

import os
import json
import time
import logging
import threading
from typing import Dict, List, Any, Optional, Union, Tuple
from pathlib import Path
import hmac
import hashlib
import base64
from datetime import datetime

# Configuration du logger
logger = logging.getLogger("gbpbot.modules.wallet_manager")

# Variables drapeau pour la disponibilité des modules
solana_available = False
web3_available = False

# Importations conditionnelles pour les blockchains spécifiques
try:
    import solana  # type: ignore
    from solana.keypair import Keypair as SolanaKeypair  # type: ignore
    from solana.publickey import PublicKey as SolanaPublicKey  # type: ignore
    solana_available = True
except ImportError:
    solana_available = False
    logger.warning("Module solana non disponible. Support Solana limité.")
    
    # Classes factices pour éviter les erreurs
    class SolanaKeypair:
        @staticmethod
        def generate():
            class FakeKeypair:
                seed = b'0' * 32
                @property
                def public_key(self):
                    return "FakeSolanaAddress"
            return FakeKeypair()
        
        @staticmethod
        def from_seed(seed):
            class FakeKeypair:
                seed = seed
                @property
                def public_key(self):
                    return "FakeSolanaAddress"
            return FakeKeypair()
    
    class SolanaPublicKey:
        def __init__(self, address):
            self.address = address
        
        def __str__(self):
            return self.address

try:
    from web3 import Web3  # type: ignore
    web3_available = True
except ImportError:
    web3_available = False
    logger.warning("Module web3 non disponible. Support Ethereum/Avalanche limité.")
    
    # Classe factice pour éviter les erreurs
    class Web3:
        class Eth:
            class Account:
                @staticmethod
                def create():
                    class FakeAccount:
                        key = b'0' * 32
                        address = "0xFakeEthereumAddress"
                        
                        def hex(self):
                            return "0x" + "0" * 64
                    return FakeAccount()
                
                @staticmethod
                def from_key(key):
                    class FakeAccount:
                        key = key
                        address = "0xFakeEthereumAddress"
                    return FakeAccount()
            
            account = Account()
        
        eth = Eth()


class WalletConfig:
    """Configuration pour un wallet unique"""
    
    def __init__(
        self,
        blockchain: str,
        address: str,
        private_key: Optional[str] = None,
        keystore_path: Optional[str] = None,
        keystore_password: Optional[str] = None,
        label: Optional[str] = None
    ):
        """
        Initialise une configuration de wallet.
        
        Args:
            blockchain: Type de blockchain (solana, avax, ethereum, sonic)
            address: Adresse du wallet
            private_key: Clé privée (chiffrée)
            keystore_path: Chemin vers le fichier keystore
            keystore_password: Mot de passe du keystore (chiffré)
            label: Libellé lisible pour ce wallet
        """
        self.blockchain = blockchain.lower()
        self.address = address
        self.private_key = private_key
        self.keystore_path = keystore_path
        self.keystore_password = keystore_password
        self.label = label or f"{blockchain}-{address[:6]}...{address[-4:]}"
        self.last_used = datetime.now().timestamp()
    
    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """
        Convertit la configuration en dictionnaire.
        
        Args:
            include_sensitive: Inclure les données sensibles (clés privées, mots de passe)
            
        Returns:
            Dict: Configuration du wallet
        """
        result = {
            "blockchain": self.blockchain,
            "address": self.address,
            "label": self.label,
            "last_used": self.last_used
        }
        
        if include_sensitive:
            result["private_key"] = self.private_key
            result["keystore_path"] = self.keystore_path
            result["keystore_password"] = self.keystore_password
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WalletConfig':
        """
        Crée une configuration à partir d'un dictionnaire.
        
        Args:
            data: Dictionnaire de configuration
            
        Returns:
            WalletConfig: Configuration de wallet
        """
        return cls(
            blockchain=data.get("blockchain", "unknown"),
            address=data.get("address", ""),
            private_key=data.get("private_key"),
            keystore_path=data.get("keystore_path"),
            keystore_password=data.get("keystore_password"),
            label=data.get("label")
        )


class WalletManager:
    """
    Gestionnaire central pour les wallets sur différentes blockchains.
    
    Cette classe est responsable de:
    - Stocker les configurations de wallets de manière sécurisée
    - Fournir des informations sur les wallets (adresses, soldes)
    - Faciliter l'utilisation des wallets pour les transactions
    """
    
    _instance = None
    
    def __new__(cls):
        """Implémentation du pattern Singleton"""
        if cls._instance is None:
            cls._instance = super(WalletManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialise le gestionnaire de wallets"""
        # Éviter la réinitialisation du singleton
        if getattr(self, "_initialized", False):
            return
            
        self._initialized = True
        
        # Données de base
        self.wallets: Dict[str, WalletConfig] = {}  # wallet_id -> WalletConfig
        self.wallets_by_blockchain: Dict[str, List[str]] = {}  # blockchain -> [wallet_id]
        self.default_wallets: Dict[str, str] = {}  # blockchain -> wallet_id
        
        # Stockage des balances (mise en cache)
        self.balances: Dict[str, Dict[str, float]] = {}  # wallet_id -> {token -> amount}
        self.balances_timestamp: Dict[str, float] = {}  # wallet_id -> timestamp
        
        # Verrou pour l'accès concurrent
        self._lock = threading.RLock()
        
        # Chemin du fichier de configuration
        self.config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "wallets")
        self.wallets_file = os.path.join(self.config_dir, "wallets.json")
        self.balances_file = os.path.join(self.config_dir, "balances.json")
        
        # Créer le répertoire de configuration s'il n'existe pas
        os.makedirs(self.config_dir, exist_ok=True)
        
        # Charger les données existantes
        self._load_wallets()
        self._load_balances()
    
    def _load_wallets(self) -> None:
        """Charge les configurations de wallets depuis le fichier"""
        if not os.path.exists(self.wallets_file):
            logger.info("Fichier de configuration des wallets non trouvé. Création d'un nouveau fichier.")
            return
            
        try:
            with open(self.wallets_file, 'r') as f:
                data = json.load(f)
                
                # Charger les wallets
                wallets_data = data.get("wallets", {})
                for wallet_id, wallet_data in wallets_data.items():
                    self.wallets[wallet_id] = WalletConfig.from_dict(wallet_data)
                
                # Charger les wallets par blockchain
                self.wallets_by_blockchain = data.get("wallets_by_blockchain", {})
                
                # Charger les wallets par défaut
                self.default_wallets = data.get("default_wallets", {})
                
            logger.info(f"Chargé {len(self.wallets)} configurations de wallet depuis {self.wallets_file}")
        except Exception as e:
            logger.error(f"Erreur lors du chargement des configurations de wallet: {str(e)}")
    
    def _save_wallets(self) -> None:
        """Sauvegarde les configurations de wallets dans le fichier"""
        try:
            with self._lock:
                data = {
                    "wallets": {wallet_id: wallet.to_dict(include_sensitive=True) for wallet_id, wallet in self.wallets.items()},
                    "wallets_by_blockchain": self.wallets_by_blockchain,
                    "default_wallets": self.default_wallets
                }
                
                with open(self.wallets_file, 'w') as f:
                    json.dump(data, f, indent=2)
                    
            logger.debug(f"Configurations de wallet sauvegardées dans {self.wallets_file}")
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des configurations de wallet: {str(e)}")
    
    def _load_balances(self) -> None:
        """Charge les balances depuis le fichier"""
        if not os.path.exists(self.balances_file):
            logger.info("Fichier de balances non trouvé. Création d'un nouveau fichier.")
            return
            
        try:
            with open(self.balances_file, 'r') as f:
                data = json.load(f)
                self.balances = data.get("balances", {})
                self.balances_timestamp = data.get("timestamps", {})
                
            logger.info(f"Chargé les balances pour {len(self.balances)} wallets depuis {self.balances_file}")
        except Exception as e:
            logger.error(f"Erreur lors du chargement des balances: {str(e)}")
    
    def _save_balances(self) -> None:
        """Sauvegarde les balances dans le fichier"""
        try:
            with self._lock:
                data = {
                    "balances": self.balances,
                    "timestamps": self.balances_timestamp
                }
                
                with open(self.balances_file, 'w') as f:
                    json.dump(data, f, indent=2)
                    
            logger.debug(f"Balances sauvegardées dans {self.balances_file}")
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des balances: {str(e)}")
    
    def add_wallet(self, wallet_config: WalletConfig) -> str:
        """
        Ajoute une nouvelle configuration de wallet.
        
        Args:
            wallet_config: Configuration du wallet à ajouter
            
        Returns:
            str: Identifiant du wallet ajouté
        """
        with self._lock:
            # Générer un ID unique pour le wallet
            wallet_id = f"{wallet_config.blockchain}-{wallet_config.address}"
            
            # Ajouter le wallet
            self.wallets[wallet_id] = wallet_config
            
            # Mettre à jour les wallets par blockchain
            if wallet_config.blockchain not in self.wallets_by_blockchain:
                self.wallets_by_blockchain[wallet_config.blockchain] = []
            
            if wallet_id not in self.wallets_by_blockchain[wallet_config.blockchain]:
                self.wallets_by_blockchain[wallet_config.blockchain].append(wallet_id)
            
            # Définir comme wallet par défaut si c'est le premier pour cette blockchain
            if wallet_config.blockchain not in self.default_wallets:
                self.default_wallets[wallet_config.blockchain] = wallet_id
            
            # Sauvegarder les modifications
            self._save_wallets()
            
            logger.info(f"Wallet ajouté: {wallet_id}")
            return wallet_id
    
    def remove_wallet(self, wallet_id: str) -> bool:
        """
        Supprime une configuration de wallet.
        
        Args:
            wallet_id: Identifiant du wallet à supprimer
            
        Returns:
            bool: True si le wallet a été supprimé, False sinon
        """
        with self._lock:
            if wallet_id not in self.wallets:
                logger.warning(f"Wallet {wallet_id} non trouvé pour suppression")
                return False
            
            # Récupérer la blockchain
            blockchain = self.wallets[wallet_id].blockchain
            
            # Supprimer le wallet
            del self.wallets[wallet_id]
            
            # Mettre à jour les wallets par blockchain
            if blockchain in self.wallets_by_blockchain and wallet_id in self.wallets_by_blockchain[blockchain]:
                self.wallets_by_blockchain[blockchain].remove(wallet_id)
            
            # Mettre à jour le wallet par défaut si nécessaire
            if blockchain in self.default_wallets and self.default_wallets[blockchain] == wallet_id:
                if blockchain in self.wallets_by_blockchain and self.wallets_by_blockchain[blockchain]:
                    self.default_wallets[blockchain] = self.wallets_by_blockchain[blockchain][0]
                else:
                    del self.default_wallets[blockchain]
            
            # Supprimer les balances
            if wallet_id in self.balances:
                del self.balances[wallet_id]
            
            if wallet_id in self.balances_timestamp:
                del self.balances_timestamp[wallet_id]
            
            # Sauvegarder les modifications
            self._save_wallets()
            self._save_balances()
            
            logger.info(f"Wallet supprimé: {wallet_id}")
            return True
    
    def get_wallet(self, wallet_id: str) -> Optional[WalletConfig]:
        """
        Récupère une configuration de wallet par son identifiant.
        
        Args:
            wallet_id: Identifiant du wallet
            
        Returns:
            WalletConfig ou None si non trouvé
        """
        with self._lock:
            return self.wallets.get(wallet_id)
    
    def get_wallet_by_address(self, address: str, blockchain: Optional[str] = None) -> Optional[WalletConfig]:
        """
        Récupère une configuration de wallet par son adresse.
        
        Args:
            address: Adresse du wallet
            blockchain: Type de blockchain (optionnel)
            
        Returns:
            WalletConfig ou None si non trouvé
        """
        with self._lock:
            for wallet_id, wallet in self.wallets.items():
                if wallet.address == address and (blockchain is None or wallet.blockchain == blockchain):
                    return wallet
            return None
    
    def get_wallets_for_blockchain(self, blockchain: str) -> List[WalletConfig]:
        """
        Récupère toutes les configurations de wallet pour une blockchain.
        
        Args:
            blockchain: Type de blockchain
            
        Returns:
            Liste de configurations de wallet
        """
        with self._lock:
            blockchain = blockchain.lower()
            wallet_ids = self.wallets_by_blockchain.get(blockchain, [])
            return [self.wallets[wallet_id] for wallet_id in wallet_ids if wallet_id in self.wallets]
    
    def get_default_wallet(self, blockchain: str) -> Optional[WalletConfig]:
        """
        Récupère la configuration du wallet par défaut pour une blockchain.
        
        Args:
            blockchain: Type de blockchain
            
        Returns:
            WalletConfig ou None si non trouvé
        """
        with self._lock:
            blockchain = blockchain.lower()
            if blockchain in self.default_wallets:
                wallet_id = self.default_wallets[blockchain]
                return self.wallets.get(wallet_id)
            return None
    
    def set_default_wallet(self, wallet_id: str) -> bool:
        """
        Définit un wallet comme wallet par défaut pour sa blockchain.
        
        Args:
            wallet_id: Identifiant du wallet
            
        Returns:
            bool: True si le wallet a été défini comme défaut, False sinon
        """
        with self._lock:
            if wallet_id not in self.wallets:
                logger.warning(f"Wallet {wallet_id} non trouvé pour définition comme défaut")
                return False
            
            blockchain = self.wallets[wallet_id].blockchain
            self.default_wallets[blockchain] = wallet_id
            
            # Sauvegarder les modifications
            self._save_wallets()
            
            logger.info(f"Wallet {wallet_id} défini comme wallet par défaut pour {blockchain}")
            return True
    
    def update_balances(self, wallet_id: str, balances: Dict[str, float]) -> bool:
        """
        Met à jour les balances d'un wallet.
        
        Args:
            wallet_id: Identifiant du wallet
            balances: Dictionnaire de balances (token -> montant)
            
        Returns:
            bool: True si les balances ont été mises à jour, False sinon
        """
        with self._lock:
            if wallet_id not in self.wallets:
                logger.warning(f"Wallet {wallet_id} non trouvé pour mise à jour des balances")
                return False
            
            self.balances[wallet_id] = balances
            self.balances_timestamp[wallet_id] = time.time()
            
            # Sauvegarder les modifications
            self._save_balances()
            
            logger.debug(f"Balances mises à jour pour le wallet {wallet_id}")
            return True
    
    def get_balances(self, blockchain: Optional[str] = None) -> Dict[str, Dict[str, float]]:
        """
        Récupère les balances pour tous les wallets ou pour une blockchain spécifique.
        
        Args:
            blockchain: Type de blockchain (optionnel)
            
        Returns:
            Dict: Balances par wallet (wallet_label -> {token -> montant})
        """
        with self._lock:
            result = {}
            
            if blockchain:
                blockchain = blockchain.lower()
                wallet_ids = self.wallets_by_blockchain.get(blockchain, [])
            else:
                wallet_ids = list(self.wallets.keys())
            
            for wallet_id in wallet_ids:
                if wallet_id in self.wallets and wallet_id in self.balances:
                    wallet = self.wallets[wallet_id]
                    result[wallet.label] = self.balances[wallet_id]
            
            return result
    
    def get_balance(self, wallet_id: str, token: str) -> float:
        """
        Récupère la balance d'un token spécifique pour un wallet.
        
        Args:
            wallet_id: Identifiant du wallet
            token: Symbole du token
            
        Returns:
            float: Balance du token ou 0 si non trouvée
        """
        with self._lock:
            if wallet_id not in self.balances:
                return 0.0
            
            return self.balances[wallet_id].get(token, 0.0)
    
    def get_total_balance(self, token: str) -> float:
        """
        Récupère la balance totale d'un token spécifique sur tous les wallets.
        
        Args:
            token: Symbole du token
            
        Returns:
            float: Balance totale du token
        """
        with self._lock:
            total = 0.0
            
            for wallet_id, balances in self.balances.items():
                total += balances.get(token, 0.0)
            
            return total
    
    def create_solana_wallet(self, label: Optional[str] = None) -> Optional[str]:
        """
        Crée un nouveau wallet Solana.
        
        Args:
            label: Libellé du wallet (optionnel)
            
        Returns:
            str: Identifiant du wallet créé ou None en cas d'erreur
        """
        if not solana_available:
            logger.error("Impossible de créer un wallet Solana : module solana non disponible")
            return None
        
        try:
            # Créer une nouvelle paire de clés
            keypair = SolanaKeypair.generate()
            private_key = base64.b64encode(keypair.seed).decode('utf-8')
            address = str(keypair.public_key)
            
            # Créer la configuration du wallet
            wallet_config = WalletConfig(
                blockchain="solana",
                address=address,
                private_key=private_key,
                label=label or f"Solana-{address[:6]}...{address[-4:]}"
            )
            
            # Ajouter le wallet
            return self.add_wallet(wallet_config)
            
        except Exception as e:
            logger.error(f"Erreur lors de la création du wallet Solana: {str(e)}")
            return None
    
    def create_evm_wallet(self, blockchain: str, label: Optional[str] = None) -> Optional[str]:
        """
        Crée un nouveau wallet EVM (Ethereum, Avalanche, Sonic).
        
        Args:
            blockchain: Type de blockchain (ethereum, avax, sonic)
            label: Libellé du wallet (optionnel)
            
        Returns:
            str: Identifiant du wallet créé ou None en cas d'erreur
        """
        if not web3_available:
            logger.error(f"Impossible de créer un wallet {blockchain} : module web3 non disponible")
            return None
        
        # Valider la blockchain
        if blockchain.lower() not in ["ethereum", "avax", "sonic"]:
            logger.error(f"Blockchain non supportée: {blockchain}")
            return None
        
        try:
            # Créer un compte
            account = Web3().eth.account.create()
            private_key = account.key.hex()
            address = account.address
            
            # Créer la configuration du wallet
            wallet_config = WalletConfig(
                blockchain=blockchain.lower(),
                address=address,
                private_key=private_key,
                label=label or f"{blockchain.capitalize()}-{address[:6]}...{address[-4:]}"
            )
            
            # Ajouter le wallet
            return self.add_wallet(wallet_config)
            
        except Exception as e:
            logger.error(f"Erreur lors de la création du wallet {blockchain}: {str(e)}")
            return None
    
    def import_wallet_from_private_key(self, blockchain: str, private_key: str, label: Optional[str] = None) -> Optional[str]:
        """
        Importe un wallet à partir de sa clé privée.
        
        Args:
            blockchain: Type de blockchain (solana, ethereum, avax, sonic)
            private_key: Clé privée
            label: Libellé du wallet (optionnel)
            
        Returns:
            str: Identifiant du wallet importé ou None en cas d'erreur
        """
        blockchain = blockchain.lower()
        
        try:
            if blockchain == "solana":
                if not solana_available:
                    logger.error("Impossible d'importer un wallet Solana : module solana non disponible")
                    return None
                
                # Gérer différents formats de clé privée Solana
                if private_key.startswith("[") and private_key.endswith("]"):
                    # Format JSON
                    key_bytes = bytes(json.loads(private_key))
                elif len(private_key) == 88 and private_key[0] == "[" and private_key[-1] == "]":
                    # Format array string
                    key_bytes = bytes([int(x) for x in private_key[1:-1].split(",")])
                else:
                    # Essayer base64
                    try:
                        key_bytes = base64.b64decode(private_key)
                    except:
                        logger.error("Format de clé privée Solana non reconnu")
                        return None
                
                keypair = SolanaKeypair.from_seed(key_bytes[:32])
                address = str(keypair.public_key)
                enc_private_key = base64.b64encode(keypair.seed).decode('utf-8')
                
            elif blockchain in ["ethereum", "avax", "sonic"]:
                if not web3_available:
                    logger.error(f"Impossible d'importer un wallet {blockchain} : module web3 non disponible")
                    return None
                
                # Normaliser la clé privée
                if private_key.startswith("0x"):
                    private_key = private_key[2:]
                
                account = Web3().eth.account.from_key(f"0x{private_key}")
                address = account.address
                enc_private_key = private_key
                
            else:
                logger.error(f"Blockchain non supportée: {blockchain}")
                return None
            
            # Créer la configuration du wallet
            wallet_config = WalletConfig(
                blockchain=blockchain,
                address=address,
                private_key=enc_private_key,
                label=label or f"{blockchain.capitalize()}-{address[:6]}...{address[-4:]}"
            )
            
            # Ajouter le wallet
            return self.add_wallet(wallet_config)
            
        except Exception as e:
            logger.error(f"Erreur lors de l'importation du wallet {blockchain}: {str(e)}")
            return None
    
    def get_private_key(self, wallet_id: str) -> Optional[str]:
        """
        Récupère la clé privée d'un wallet.
        
        Args:
            wallet_id: Identifiant du wallet
            
        Returns:
            str: Clé privée ou None si non trouvée
        """
        with self._lock:
            wallet = self.wallets.get(wallet_id)
            if not wallet:
                logger.warning(f"Wallet {wallet_id} non trouvé pour récupération de la clé privée")
                return None
            
            return wallet.private_key
    
    def get_supported_chains(self) -> List[str]:
        """
        Récupère la liste des blockchains supportées qui ont des wallets configurés.
        
        Returns:
            List[str]: Liste des blockchains supportées
        """
        with self._lock:
            return list(self.wallets_by_blockchain.keys())
    
    def is_wallet_available(self, blockchain: str) -> bool:
        """
        Vérifie si un wallet est disponible pour une blockchain.
        
        Args:
            blockchain: Type de blockchain
            
        Returns:
            bool: True si un wallet est disponible, False sinon
        """
        with self._lock:
            blockchain = blockchain.lower()
            return blockchain in self.wallets_by_blockchain and len(self.wallets_by_blockchain[blockchain]) > 0
    
    def fetch_balances(self, wallet_id: str) -> Dict[str, float]:
        """
        Récupère les balances actuelles d'un wallet depuis la blockchain.
        Cette méthode est un placeholder et doit être implémentée en fonction des besoins spécifiques.
        
        Args:
            wallet_id: Identifiant du wallet
            
        Returns:
            Dict[str, float]: Balances (token -> montant)
        """
        logger.warning("fetch_balances() est un placeholder et doit être implémenté pour une utilisation réelle")
        return {}

    async def get_balances_async(self, blockchain: Optional[str] = None) -> Dict[str, Dict[str, float]]:
        """Version asynchrone de get_balances pour l'interface Telegram"""
        return self.get_balances(blockchain)

    async def get_supported_chains_async(self) -> List[str]:
        """Version asynchrone de get_supported_chains pour l'interface Telegram"""
        return self.get_supported_chains()


def get_wallet_manager() -> WalletManager:
    """
    Fonction utilitaire pour obtenir l'instance singleton du gestionnaire de wallets.
    
    Returns:
        Instance singleton de WalletManager
    """
    return WalletManager() 