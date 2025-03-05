from web3 import Web3
from eth_account import Account
import json


# Fonction pour créer un middleware personnalisé pour les chaînes PoA
# Fonction supprimée car non nécessaire avec web3.py v7.8.0

from typing import Optional, Tuple, List, Dict, Any, Callable
import os
from dotenv import load_dotenv
from loguru import logger
from web3.exceptions import ExtraDataLengthError
from .transaction_manager import TransactionManager
from .price_feed import PriceManager
import time
import random
from functools import wraps
import asyncio
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import ccxt.async_support as ccxt
# Import remplacé par notre propre middleware
from web3.providers import WebSocketProvider
from web3.exceptions import TransactionNotFound
from web3.types import TxParams, Wei
from eth_account.signers.local import LocalAccount
import aiohttp
from datetime import datetime, timedelta
import websockets
import hashlib
from .rpc.rpc_manager import rpc_manager  # Importer le gestionnaire RPC

# Charger les variables d'environnement
load_dotenv()

def retry_on_failure(max_retries=3, backoff_factor=1.5):
    """
    Décorateur pour réessayer les fonctions qui peuvent échouer en raison de problèmes RPC
    avec un délai exponentiel entre les tentatives.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            retries = 0
            last_exception = None
            
            while retries < max_retries:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    last_exception = e
                    
                    # Journaliser l'erreur
                    logger.warning(f"Tentative {retries}/{max_retries} échouée pour {func.__name__}: {str(e)}")
                    
                    # Si c'est la dernière tentative, lever l'erreur
                    if retries >= max_retries:
                        logger.error(f"Échec de toutes les tentatives pour {func.__name__}")
                        raise last_exception
                        
                    # Attendre avec backoff exponentiel
                    wait_time = backoff_factor ** retries
                    logger.debug(f"Attente de {wait_time:.2f} secondes avant la prochaine tentative")
                    await asyncio.sleep(wait_time)
                    
                    # Utiliser le RPCManager pour obtenir une nouvelle connexion RPC
                    if hasattr(args[0], 'web3') and args[0].web3:
                        logger.info("Obtention d'une nouvelle connexion RPC via RPCManager")
                        args[0].web3 = rpc_manager.get_web3_provider()
                        
            # Ne devrait jamais arriver ici
            raise last_exception
            
        return wrapper
    return decorator

class SecureKeyManager:
    """Gestionnaire sécurisé pour les clés privées"""
    
    def __init__(self, password_env_var="KEY_PASSWORD"):
        """
        Initialise le gestionnaire de clés sécurisé
        
        Args:
            password_env_var: Variable d'environnement contenant le mot de passe de déchiffrement
        """
        self.password_env_var = password_env_var
        self._key = None
    
    def _derive_key(self, password: str) -> bytes:
        """Dérive une clé de chiffrement à partir du mot de passe"""
        salt = b'GBPBot_salt_value'  # Idéalement, ce sel devrait être stocké de manière sécurisée
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))
    
    def get_private_key(self) -> str:
        """
        Récupère et déchiffre la clé privée
        
        Returns:
            La clé privée déchiffrée
        
        Raises:
            ValueError: Si la clé privée ou le mot de passe n'est pas défini
            Exception: Si le déchiffrement échoue
        """
        # Vérifier si nous sommes en mode simulation
        if os.getenv("SIMULATION_MODE", "false").lower() == "true":
            return "0x" + "0" * 64  # Clé factice pour la simulation
        
        # Récupérer la clé privée chiffrée
        encrypted_key = os.getenv("ENCRYPTED_PRIVATE_KEY")
        if not encrypted_key:
            # Fallback sur l'ancienne méthode si la clé chiffrée n'existe pas
            private_key = os.getenv("PRIVATE_KEY")
            if not private_key:
                raise ValueError("Aucune clé privée définie (ni ENCRYPTED_PRIVATE_KEY ni PRIVATE_KEY)")
            
            logger.warning("Utilisation de PRIVATE_KEY non chiffrée. Considérez utiliser ENCRYPTED_PRIVATE_KEY pour plus de sécurité.")
            return private_key if private_key.startswith("0x") else "0x" + private_key
        
        # Récupérer le mot de passe
        password = os.getenv(self.password_env_var)
        if not password:
            raise ValueError(f"Mot de passe de déchiffrement non défini ({self.password_env_var})")
        
        try:
            # Dériver la clé de chiffrement
            key = self._derive_key(password)
            
            # Déchiffrer la clé privée
            f = Fernet(key)
            decrypted_key = f.decrypt(encrypted_key.encode()).decode()
            
            # Vérifier le format de la clé
            if not decrypted_key.startswith("0x"):
                decrypted_key = "0x" + decrypted_key
                
            # Vérifier la longueur de la clé
            if len(decrypted_key) != 66:  # 0x + 64 caractères hexadécimaux
                raise ValueError("Format de clé privée invalide après déchiffrement")
                
            return decrypted_key
            
        except Exception as e:
            logger.error(f"Erreur lors du déchiffrement de la clé privée: {str(e)}")
            raise Exception("Impossible de déchiffrer la clé privée")
    
    @staticmethod
    def encrypt_key(private_key: str, password: str) -> str:
        """
        Chiffre une clé privée avec un mot de passe
        
        Args:
            private_key: La clé privée à chiffrer
            password: Le mot de passe pour le chiffrement
            
        Returns:
            La clé privée chiffrée en base64
        """
        # Nettoyer la clé privée
        if private_key.startswith("0x"):
            private_key = private_key[2:]
            
        # Dériver la clé de chiffrement
        salt = b'GBPBot_salt_value'
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        
        # Chiffrer la clé privée
        f = Fernet(key)
        encrypted_key = f.encrypt(private_key.encode())
        
        return encrypted_key.decode()

class BlockchainClient:
    """Client pour interagir avec la blockchain Avalanche"""
    
    def __init__(self, private_key: Optional[str] = None, is_testnet: bool = False, simulation_mode: bool = False):
        """
        Initialise le client blockchain
        
        Args:
            private_key: Clé privée pour signer les transactions
            is_testnet: Utiliser le testnet au lieu du mainnet
            simulation_mode: Mode simulation (pas de transactions réelles)
        """
        self.is_testnet = is_testnet
        self.simulation_mode = simulation_mode
        self.web3 = None
        self.account = None
        
        # Initialiser les balances simulées pour le mode simulation
        self.simulated_balances = {
            "WAVAX": 10.0,
            "USDT": 1000.0,
            "USDC": 1000.0,
            "WETH": 1.0
        }
        
        # Initialiser la connexion Web3
        self._initialize_web3()
        
        # Configurer le compte si une clé privée est fournie
        if private_key:
            self.account = Account.from_key(private_key)
            logger.info(f"Compte configuré: {self.account.address}")
        elif not simulation_mode:
            logger.warning("Aucune clé privée fournie, les transactions ne pourront pas être signées")
            
        # Initialiser le gestionnaire de transactions
        self.tx_manager = TransactionManager(self.web3, self.account if self.account else None, simulation_mode)
        
        # Initialiser le gestionnaire de prix
        self.price_feed = PriceManager(self.web3, is_testnet, simulation_mode)
        
        # Charger les adresses des contrats
        self._load_contract_addresses()
        
        # Initialiser les contrats
        self._initialize_contracts()
        
        # Vérifier la connexion
        self._check_connection()
        
    def _initialize_web3(self):
        """
        Initialise la connexion Web3 avec le gestionnaire RPC
        
        Returns:
            Web3: Instance Web3 connectée
        """
        try:
            # Utiliser le gestionnaire RPC pour obtenir une instance Web3
            self.web3 = rpc_manager.get_web3_provider()
            
            if not self.web3:
                logger.error("Impossible d'obtenir une instance Web3 du gestionnaire RPC")
                if self.simulation_mode:
                    # En mode simulation, on peut continuer avec une instance Web3 minimale
                    logger.warning("Mode simulation: création d'une instance Web3 minimale")
                    from web3 import Web3
                    self.web3 = Web3()
                    return self.web3
                else:
                    raise ConnectionError("Échec de la connexion Web3")
                
            if not self.web3.is_connected():
                logger.error("La connexion Web3 n'est pas établie")
                if self.simulation_mode:
                    # En mode simulation, on peut continuer avec une instance Web3 minimale
                    logger.warning("Mode simulation: création d'une instance Web3 minimale")
                    from web3 import Web3
                    self.web3 = Web3()
                    return self.web3
                else:
                    raise ConnectionError("Échec de la connexion Web3")
                
            logger.info("Connexion Web3 établie via le gestionnaire RPC")
            return self.web3
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de Web3: {str(e)}")
            if self.simulation_mode:
                # En mode simulation, on peut continuer avec une instance Web3 minimale
                logger.warning("Mode simulation: création d'une instance Web3 minimale après erreur")
                from web3 import Web3
                self.web3 = Web3()
                return self.web3
            else:
                raise ConnectionError(f"Échec de la connexion Web3: {str(e)}")

    def is_connected(self) -> bool:
        """Vérifie si la connexion à la blockchain est active"""
        try:
            if self.simulation_mode:
                return True
            return self.web3.is_connected() and self.web3.eth.chain_id == 43114
        except Exception as e:
            logger.error(f"Erreur lors de la vérification de la connexion: {str(e)}")
            return False
            
    async def wrap_avax(self, amount: float) -> Optional[str]:
        """Wrap des AVAX en WAVAX"""
        try:
            if self.simulation_mode:
                if self.simulated_balances["AVAX"] >= amount:
                    self.simulated_balances["AVAX"] -= amount
                    self.simulated_balances[self.tokens["WAVAX"]] += amount
                    tx_hash = "0x" + "0" * 64  # Hash simulé
                    logger.info(f"[SIMULATION] Transaction de wrapping simulée: {tx_hash}")
                    return tx_hash
                else:
                    logger.error("[SIMULATION] Solde AVAX insuffisant pour le wrapping")
                    return None
                    
            amount_wei = Web3.to_wei(amount, 'ether')
            
            # Préparer la transaction
            tx = {
                'from': self.account.address,
                'to': self.contracts['wavax'],
                'value': amount_wei,
                'nonce': self.web3.eth.get_transaction_count(self.account.address),
                'gas': 100000,  # Estimation pour le wrapping
                'maxFeePerGas': Web3.to_wei(50, 'gwei'),
                'maxPriorityFeePerGas': Web3.to_wei(2, 'gwei')
            }
            
            # Signer et envoyer la transaction
            signed_tx = self.account.sign_transaction(tx)
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            logger.info(f"Transaction de wrapping envoyée: {tx_hash.hex()}")
            return tx_hash.hex()
            
        except Exception as e:
            logger.error(f"Erreur lors du wrapping d'AVAX: {str(e)}")
            return None
            
    def get_token_balance(self, token_address: str) -> int:
        """Récupère le solde d'un token en wei"""
        try:
            if self.simulation_mode:
                try:
                    # Utiliser le gestionnaire de portefeuille simulé si disponible
                    from gbpbot.core.simulation.wallet_simulation import wallet_manager
                    
                    # Si l'adresse est un symbole, utiliser directement
                    if token_address in wallet_manager.default_wallet.balances:
                        balance = wallet_manager.get_balance(token_address)
                        return Web3.to_wei(balance, "ether")
                    
                    # Sinon, utiliser get_balance_by_address
                    balance = wallet_manager.get_balance_by_address(token_address)
                    return Web3.to_wei(balance, "ether")
                
                except ImportError:
                    # Fallback: utiliser les balances simulées internes
                    # Trouver le symbole correspondant à l'adresse
                    symbol = next((sym for sym, addr in self.token_addresses.items() if addr == token_address), None)
                    if symbol:
                        balance = self.simulated_balances.get(symbol, 0.0)
                        return Web3.to_wei(balance, "ether")
                    return 0
            else:
                # En mode réel, récupérer le vrai solde
                token_contract = self.web3.eth.contract(
                    address=Web3.to_checksum_address(token_address),
                    abi=self.token_abi
                )
                return token_contract.functions.balanceOf(self.account.address).call()
                
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du solde: {str(e)}")
            return 0
            
    def simulate_trade(self, token_in: str, token_out: str, amount: float, profit_percent: float) -> bool:
        """Simule un trade avec un profit donné"""
        # Vérifier que nous sommes en mode simulation
        if not self.simulation_mode:
            logger.warning("Tentative d'utiliser simulate_trade en mode réel")
            return False
        
        try:
            # Vérifier le solde
            if self.simulated_balances[token_in] < amount:
                logger.warning(f"[SIMULATION] Solde insuffisant en {token_in}. Requis: {amount}, Disponible: {self.simulated_balances[token_in]}")
                return False
            
            # Calculer le montant reçu avec le profit
            amount_out = amount * (1 + profit_percent / 100)
            
            # Mettre à jour les balances simulées
            self.simulated_balances[token_in] -= amount
            self.simulated_balances[token_out] += amount_out
            
            logger.success(f"[SIMULATION] Trade simulé: {amount} {token_in} → {amount_out:.4f} {token_out}")
            logger.info(f"[SIMULATION] Nouveaux soldes: {token_in}: {self.simulated_balances[token_in]:.4f}, {token_out}: {self.simulated_balances[token_out]:.4f}")
            
            # Calculer le profit en USD (approximatif)
            profit_usd = amount * (profit_percent / 100)
            if token_out in ["USDT", "USDC"]:
                profit_usd = amount_out - amount  # Si le token de sortie est un stablecoin
            
            logger.info(f"[SIMULATION] Profit estimé: {profit_usd:.4f} USD ({profit_percent:.2f}%)")
            return True
            
        except Exception as e:
            logger.error(f"[SIMULATION] Erreur lors de la simulation du trade: {str(e)}")
            return False
            
    def simulate_swap_stablecoins_to_wavax(self, amount_stablecoin: float, stablecoin: str = "USDC") -> bool:
        """Simule une reconversion de stablecoins en WAVAX en mode simulation
        
        Args:
            amount_stablecoin: Montant de stablecoin à reconvertir
            stablecoin: Le stablecoin à utiliser (USDC ou USDT)
            
        Returns:
            bool: True si la reconversion a réussi, False sinon
        """
        if not self.simulation_mode:
            logger.warning("Tentative d'utiliser simulate_swap_stablecoins_to_wavax en mode réel")
            return False
            
        try:
            # Vérifier que le stablecoin est valide
            if stablecoin not in ["USDC", "USDT"]:
                logger.error(f"[SIMULATION] Stablecoin invalide: {stablecoin}")
                return False
                
            # Vérifier le solde disponible
            if stablecoin not in self.simulated_balances or self.simulated_balances[stablecoin] < amount_stablecoin:
                logger.warning(f"[SIMULATION] Solde insuffisant en {stablecoin}. Requis: {amount_stablecoin}, Disponible: {self.simulated_balances.get(stablecoin, 0.0)}")
                return False
            
            # Utiliser un prix fixe pour WAVAX en mode simulation
            wavax_price = 20.0  # Prix par défaut de WAVAX en USD
                
            # On simule un échange avec des frais (0.3% comme sur TraderJoe + 0.5% de slippage)
            fee_percent = 0.3
            slippage_percent = 0.5
            total_fee_percent = fee_percent + slippage_percent
                
            # Calculer le montant de WAVAX à recevoir
            amount_wavax = amount_stablecoin * (1 - total_fee_percent / 100) / wavax_price
            
            # Simuler une légère volatilité du marché (±0.5%)
            price_volatility = random.uniform(-0.5, 0.5) / 100
            amount_wavax = amount_wavax * (1 + price_volatility)
            
            # Mettre à jour les balances simulées
            self.simulated_balances[stablecoin] -= amount_stablecoin
            
            # Créer WAVAX s'il n'existe pas
            if "WAVAX" not in self.simulated_balances:
                self.simulated_balances["WAVAX"] = 0
                
            self.simulated_balances["WAVAX"] += amount_wavax
            
            logger.success(f"[SIMULATION] Rééquilibrage simulé: {amount_stablecoin} {stablecoin} → {amount_wavax:.4f} WAVAX (prix WAVAX: ${wavax_price:.2f})")
            logger.info(f"[SIMULATION] Nouveaux soldes: {stablecoin}: {self.simulated_balances[stablecoin]:.4f}, WAVAX: {self.simulated_balances['WAVAX']:.4f}")
            
            # Si on utilise le gestionnaire de portefeuille simulé, mettre à jour les soldes
            try:
                from gbpbot.core.simulation.wallet_simulation import wallet_manager
                wallet_manager.update_balance(stablecoin, self.simulated_balances[stablecoin])
                wallet_manager.update_balance("WAVAX", self.simulated_balances["WAVAX"])
            except ImportError:
                pass  # Ignorer si le module n'est pas disponible
                
            return True
            
        except Exception as e:
            logger.error(f"[SIMULATION] Erreur lors de la simulation du rééquilibrage: {str(e)}")
            return False
            
    def _get_erc20_balance(self, token_address: str) -> int:
        """Récupère le solde d'un token ERC20"""
        try:
            if self.simulation_mode:
                return 0
                
            # ABI minimal pour balanceOf
            abi = [{"constant":True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"}]
            
            contract = self.web3.eth.contract(address=token_address, abi=abi)
            return contract.functions.balanceOf(self.account.address).call()
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du solde ERC20: {str(e)}")
            return 0
            
    @retry_on_failure(max_retries=5, backoff_factor=0.5)
    async def send_transaction(self, to: str, data: bytes, value: int = 0, priority: str = "normal") -> Optional[str]:
        """Envoie une transaction avec retry automatique en cas d'échec"""
        if self.simulation_mode:
            tx_hash = "0x" + "0" * 64  # Hash simulé
            logger.info(f"[SIMULATION] Transaction simulée: {tx_hash}")
            return tx_hash
            
        try:
            return await self.tx_manager.send_transaction(to, data, value, priority)
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de la transaction: {str(e)}")
            return None
            
    def estimate_gas_price(self) -> int:
        """Estime le prix du gas optimal"""
        return self.tx_manager.get_optimal_gas_price()

    def _prepare_dex_swap(self, dex: str, token_in: str, token_out: str, amount_in: Optional[int] = None, amount_out: Optional[int] = None) -> Dict:
        """Prépare les paramètres pour un swap sur un DEX"""
        try:
            if amount_in is None and amount_out is None:
                raise ValueError("Either amount_in or amount_out must be specified")
            if amount_in is not None and amount_out is not None:
                raise ValueError("Only one of amount_in or amount_out can be specified")

            # Récupérer le contrat du DEX
            dex_contract = self.contracts.get(dex)
            if not dex_contract:
                raise ValueError(f"DEX contract not found for {dex}")

            # Préparer les paramètres du swap
            path = [token_in, token_out]
            deadline = int(time.time()) + 300  # 5 minutes

            # Construire les paramètres en fonction du montant spécifié
            if amount_in is not None:
                params = {
                    'amountIn': amount_in,
                    'amountOutMin': 0,  # À ajuster avec le slippage
                    'path': path,
                    'to': self.account.address,
                    'deadline': deadline
                }
                method = 'swapExactTokensForTokens'
            else:
                params = {
                    'amountOut': amount_out,
                    'amountInMax': 2**256 - 1,  # Maximum uint256
                    'path': path,
                    'to': self.account.address,
                    'deadline': deadline
                }
                method = 'swapTokensForExactTokens'

            return {
                'contract': dex_contract,
                'method': method,
                'params': params
            }
        except Exception as e:
            logger.error(f"Erreur lors de la préparation du swap sur {dex}: {str(e)}")
            raise 

    def _load_abi(self, name: str) -> List[Dict[str, Any]]:
        """
        Charge un ABI depuis un fichier JSON
        
        Args:
            name: Nom du fichier ABI sans extension
            
        Returns:
            List[Dict[str, Any]]: ABI chargé
        """
        try:
            import os
            import json
            
            # Chemin vers le dossier des ABIs
            abi_path = os.path.join(os.path.dirname(__file__), "..", "abis", f"{name}.json")
            
            # Si le fichier n'existe pas, créer le dossier abis et le fichier avec l'ABI minimal
            if not os.path.exists(abi_path):
                os.makedirs(os.path.dirname(abi_path), exist_ok=True)
                
                # ABI minimal pour ERC20
                minimal_abi = [
                    {
                        "constant": True,
                        "inputs": [{"name": "_owner", "type": "address"}],
                        "name": "balanceOf",
                        "outputs": [{"name": "balance", "type": "uint256"}],
                        "type": "function"
                    },
                    {
                        "constant": False,
                        "inputs": [
                            {"name": "_to", "type": "address"},
                            {"name": "_value", "type": "uint256"}
                        ],
                        "name": "transfer",
                        "outputs": [{"name": "", "type": "bool"}],
                        "type": "function"
                    }
                ]
                
                with open(abi_path, "w") as f:
                    json.dump(minimal_abi, f, indent=2)
                
                return minimal_abi
            
            # Charger l'ABI depuis le fichier
            with open(abi_path, "r") as f:
                return json.load(f)
                
        except Exception as e:
            logger.error(f"Erreur lors du chargement de l'ABI {name}: {str(e)}")
            # Retourner un ABI minimal en cas d'erreur
            return [
                {
                    "constant": True,
                    "inputs": [{"name": "_owner", "type": "address"}],
                    "name": "balanceOf",
                    "outputs": [{"name": "balance", "type": "uint256"}],
                    "type": "function"
                }
            ] 

    def get_balance(self, token_symbol: str) -> float:
        """Récupère le solde d'un token en format décimal
        
        Args:
            token_symbol (str): Symbole du token (WAVAX, USDT, USDC, etc.)
            
        Returns:
            float: Solde du token en format décimal
        """
        try:
            # En mode simulation, retourner directement le solde simulé
            if self.simulation_mode:
                return self.simulated_balances.get(token_symbol, 0.0)
                
            # En mode réel, récupérer le solde depuis la blockchain
            if token_symbol == "AVAX":
                # Pour AVAX natif
                balance_wei = self.web3.eth.get_balance(self.account.address)
            else:
                # Pour les tokens ERC20
                token_address = self.token_addresses.get(token_symbol)
                if not token_address:
                    logger.warning(f"Adresse du token {token_symbol} non trouvée")
                    return 0.0
                    
                token_contract = self.web3.eth.contract(
                    address=Web3.to_checksum_address(token_address),
                    abi=self.token_abi
                )
                balance_wei = token_contract.functions.balanceOf(self.account.address).call()
                
            # Convertir de wei à la forme décimale
            return float(Web3.from_wei(balance_wei, 'ether'))
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du solde de {token_symbol}: {str(e)}")
            return 0.0
            
    def update_simulated_balance(self, token_symbol: str, amount: float, is_addition: bool = True) -> None:
        """Met à jour le solde simulé d'un token
        
        Args:
            token_symbol (str): Symbole du token
            amount (float): Montant à ajouter ou soustraire
            is_addition (bool): Si True, ajoute le montant, sinon le soustrait
        """
        if not self.simulation_mode:
            return
            
        if token_symbol not in self.simulated_balances:
            self.simulated_balances[token_symbol] = 0.0
            
        if is_addition:
            self.simulated_balances[token_symbol] += amount
            logger.debug(f"[SIMULATION] Ajout de {amount} {token_symbol}, nouveau solde: {self.simulated_balances[token_symbol]}")
        else:
            if self.simulated_balances[token_symbol] >= amount:
                self.simulated_balances[token_symbol] -= amount
                logger.debug(f"[SIMULATION] Retrait de {amount} {token_symbol}, nouveau solde: {self.simulated_balances[token_symbol]}")
            else:
                logger.warning(f"[SIMULATION] Solde insuffisant en {token_symbol} pour retirer {amount}")
                # En mode simulation, on permet quand même l'opération avec un solde négatif pour des tests
                self.simulated_balances[token_symbol] -= amount
                logger.debug(f"[SIMULATION] Solde négatif autorisé: {self.simulated_balances[token_symbol]} {token_symbol}") 

    def _load_contract_addresses(self):
        """Charge les adresses des contrats"""
        # Charger les adresses des contrats
        config_path = os.path.join(os.path.dirname(__file__), "../config/blockchain_config.json")
        with open(config_path, "r") as f:
            self.config = json.load(f)
            
        # Sélectionner la configuration en fonction du réseau
        network = "testnet" if self.is_testnet else "mainnet"
        self.config = self.config[network]
        
        # Charger les adresses des contrats
        self.contracts = {
            "trader_joe_router": self.config["dexes"]["trader_joe"]["router"],
            "pangolin_router": self.config["dexes"]["pangolin"]["router"],
            "wavax": self.config["tokens"]["WAVAX"]
        }
        
        # Adresses des tokens selon le réseau
        self.token_addresses = {
            "WAVAX": self.config["tokens"]["WAVAX"],
            "USDT": self.config["tokens"]["USDT"],
            "USDC": self.config["tokens"]["USDC"],
            "WETH": self.config["tokens"]["WETH"]
        }
        
        # Afficher un message si en mode simulation
        if self.simulation_mode:
            logger.info("🔬 Mode simulation activé - Utilisation de balances simulées")
            logger.info(f"Balances simulées initiales: {self.simulated_balances}")
        
        # Mapping des symboles aux adresses pour les requêtes
        self.token_mapping = {
            "WAVAX": self.token_addresses["WAVAX"],
            "USDT": self.token_addresses["USDT"],
            "USDC": self.token_addresses["USDC"],
            "WETH": self.token_addresses["WETH"]
        }
        
        # Définir les tokens pour tous les modes
        self.tokens = {
            "WAVAX": self.token_addresses["WAVAX"],
            "USDT": self.token_addresses["USDT"],
            "USDC": self.token_addresses["USDC"],
            "WETH": self.token_addresses["WETH"]
        }
        
        # Charger les ABIs
        self.token_abi = self._load_abi("erc20")
        
        # Créer les contrats pour chaque token
        self.token_contracts = {}
        for symbol, address in self.token_addresses.items():
            self.token_contracts[symbol] = self.web3.eth.contract(address=self.web3.to_checksum_address(address), abi=self.token_abi)
            
        # Charger la clé privée et l'adresse du portefeuille
        if not self.simulation_mode:
            self.private_key = os.getenv("PRIVATE_KEY")
            self.account = Account.from_key(self.private_key)
            self.address = self.account.address
            logger.info(f"Portefeuille initialisé: {self.address}")
        else:
            # En mode simulation, créer un compte factice
            self.private_key = "0x0000000000000000000000000000000000000000000000000000000000000001"
            self.account = Account.from_key(self.private_key)
            self.address = self.account.address
            logger.info(f"Portefeuille de simulation initialisé: {self.address}")
        
        # Configuration des RPC
        self.INFURA_KEY = os.getenv("INFURA_API_KEY", "dd3c56e2271645738e61f440e2b27e1f")
        self.rpc_urls = [
            f"https://avalanche-mainnet.infura.io/v3/{self.INFURA_KEY}",  # Infura comme principal
            "https://api.avax.network/ext/bc/C/rpc",  # Backup 1
            "https://avax-mainnet.public.blastapi.io/ext/bc/C/rpc"  # Backup 2
        ]
        
        # Adresses des contrats importants
        self.contracts = {
            "trader_joe_router": self.contracts["trader_joe_router"],
            "pangolin_router": self.contracts["pangolin_router"],
            "wavax": self.contracts["wavax"]
        }
        
        if self.simulation_mode:
            logger.info("🔬 Mode simulation activé - Utilisation de balances simulées")
        
    def _initialize_contracts(self):
        """Initialise les contrats"""
        # Créer les contrats pour chaque token
        self.token_contracts = {}
        for symbol, address in self.token_addresses.items():
            self.token_contracts[symbol] = self.web3.eth.contract(address=self.web3.to_checksum_address(address), abi=self.token_abi)
            
    def _check_connection(self):
        """Vérifie la connexion à la blockchain"""
        if not self.web3.is_connected():
            logger.error("La connexion à la blockchain est perdue")
            raise ConnectionError("Échec de la connexion à la blockchain")
            
        if self.web3.eth.chain_id != 43114:
            logger.error(f"La blockchain n'est pas Avalanche (chain_id: {self.web3.eth.chain_id})")
            raise ConnectionError("La blockchain n'est pas Avalanche")
            
        logger.success("Connexion à la blockchain établie")
        
    def _load_abi(self, name: str) -> List[Dict[str, Any]]:
        """
        Charge un ABI depuis un fichier JSON
        
        Args:
            name: Nom du fichier ABI sans extension
            
        Returns:
            List[Dict[str, Any]]: ABI chargé
        """
        try:
            import os
            import json
            
            # Chemin vers le dossier des ABIs
            abi_path = os.path.join(os.path.dirname(__file__), "..", "abis", f"{name}.json")
            
            # Si le fichier n'existe pas, créer le dossier abis et le fichier avec l'ABI minimal
            if not os.path.exists(abi_path):
                os.makedirs(os.path.dirname(abi_path), exist_ok=True)
                
                # ABI minimal pour ERC20
                minimal_abi = [
                    {
                        "constant": True,
                        "inputs": [{"name": "_owner", "type": "address"}],
                        "name": "balanceOf",
                        "outputs": [{"name": "balance", "type": "uint256"}],
                        "type": "function"
                    },
                    {
                        "constant": False,
                        "inputs": [
                            {"name": "_to", "type": "address"},
                            {"name": "_value", "type": "uint256"}
                        ],
                        "name": "transfer",
                        "outputs": [{"name": "", "type": "bool"}],
                        "type": "function"
                    }
                ]
                
                with open(abi_path, "w") as f:
                    json.dump(minimal_abi, f, indent=2)
                
                return minimal_abi
            
            # Charger l'ABI depuis le fichier
            with open(abi_path, "r") as f:
                return json.load(f)
                
        except Exception as e:
            logger.error(f"Erreur lors du chargement de l'ABI {name}: {str(e)}")
            # Retourner un ABI minimal en cas d'erreur
            return [
                {
                    "constant": True,
                    "inputs": [{"name": "_owner", "type": "address"}],
                    "name": "balanceOf",
                    "outputs": [{"name": "balance", "type": "uint256"}],
                    "type": "function"
                }
            ] 

    async def get_dex_price(self, dex_name: str, token_in_address: str, token_out_address: str, amount_in: int) -> Optional[float]:
        """
        Récupère le prix d'un token sur un DEX spécifique.
        
        Args:
            dex_name: Nom du DEX (trader_joe, pangolin, sushi, etc.)
            token_in_address: Adresse du token d'entrée
            token_out_address: Adresse du token de sortie
            amount_in: Montant d'entrée en wei
            
        Returns:
            Optional[float]: Prix du token ou None si non disponible
        """
        try:
            if self.simulation_mode:
                # En mode simulation, générer un prix avec une légère variation
                # pour simuler les différences entre DEX
                base_price = 0
                
                # Déterminer un prix de base selon les tokens - PRIX MIS À JOUR
                if token_in_address.lower() == self.token_addresses.get("WAVAX", "").lower():
                    if token_out_address.lower() == self.token_addresses.get("USDT", "").lower():
                        base_price = 19.91  # Prix AVAX/USDT mis à jour
                    elif token_out_address.lower() == self.token_addresses.get("USDC", "").lower():
                        base_price = 19.91  # Prix AVAX/USDC mis à jour
                    elif token_out_address.lower() == self.token_addresses.get("WETH", "").lower():
                        base_price = 0.009340  # Prix AVAX/ETH mis à jour (1 AVAX = 0.0195 ETH)
                elif token_in_address.lower() == self.token_addresses.get("USDT", "").lower():
                    if token_out_address.lower() == self.token_addresses.get("WAVAX", "").lower():
                        base_price = 1/19.91  # 1 USDT = 1/19.91 AVAX
                    elif token_out_address.lower() == self.token_addresses.get("USDC", "").lower():
                        base_price = 1.0  # 1 USDT = 1 USDC
                    elif token_out_address.lower() == self.token_addresses.get("WETH", "").lower():
                        base_price = 0.000469  # 1 USDT = 0.000469 ETH (basé sur ETH à ~1780 USDT)
                
                # Ajouter une variation cohérente selon le DEX
                variation = {
                    "trader_joe": 1.0,
                    "pangolin": 0.988,  # Légèrement plus bas que Trader Joe
                    "sushi": 1.015      # Légèrement plus haut que Trader Joe
                }.get(dex_name, 1.0)
                
                # Ajouter une légère variation aléatoire (±0.5% seulement pour plus de stabilité)
                random_variation = 1.0 + (random.random() * 0.01 - 0.005)
                
                # Calculer le prix final
                price = float(base_price) * float(variation) * float(random_variation)
                
                # Convertir le montant d'entrée en unités décimales
                amount_in_decimal = float(Web3.from_wei(amount_in, "ether"))
                
                # Calculer le montant de sortie
                amount_out = amount_in_decimal * price
                
                logger.debug(f"Prix simulé sur {dex_name}: {price} (montant de sortie: {amount_out})")
                return price
            else:
                # En mode réel, il faudrait interroger le DEX via un contrat
                # Cette partie nécessiterait une implémentation spécifique pour chaque DEX
                logger.warning(f"Récupération de prix réel sur {dex_name} non implémentée")
                return None
                
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du prix sur {dex_name}: {str(e)}")
            return None
            
    async def get_cex_price(self, cex_name: str, symbol: str) -> Optional[float]:
        """
        Récupère le prix d'une paire de trading sur un CEX spécifique.
        
        Args:
            cex_name: Nom du CEX (binance, kucoin, gate, etc.)
            symbol: Symbole de la paire (ex: "AVAX/USDT")
            
        Returns:
            Optional[float]: Prix de la paire ou None si non disponible
        """
        try:
            if self.simulation_mode:
                # En mode simulation, générer un prix avec une légère variation
                # pour simuler les différences entre CEX
                base_price = 0
                
                # Déterminer un prix de base selon la paire - PRIX MIS À JOUR
                if symbol == "AVAX/USDT":
                    base_price = 19.91  # Prix AVAX/USDT mis à jour
                elif symbol == "AVAX/USDC":
                    base_price = 19.91  # Prix AVAX/USDC mis à jour
                elif symbol == "ETH/USDT":
                    base_price = 2134.26  # Prix ETH/USDT mis à jour
                elif symbol == "ETH/USDC":
                    base_price = 2133.79  # Prix ETH/USDC mis à jour
                elif symbol == "AVAX/ETH":
                    base_price = 0.009340  # Prix AVAX/ETH mis à jour
                elif symbol == "USDT/USDC":
                    base_price = 1.0  # 1 USDT = 1 USDC reste constant
                # Ajouter les paires avec WAVAX (même prix que AVAX car WAVAX est AVAX enveloppé)
                elif symbol == "WAVAX/USDT":
                    base_price = 19.91  # Même prix que AVAX/USDT
                elif symbol == "WAVAX/USDC": 
                    base_price = 19.91  # Même prix que AVAX/USDC
                elif symbol == "USDC/WAVAX":
                    base_price = 1 / 19.91  # Inverse de WAVAX/USDC
                elif symbol == "USDT/WAVAX":
                    base_price = 1 / 19.91  # Inverse de WAVAX/USDT
                elif symbol == "WAVAX/ETH":
                    base_price = 0.009340  # Même prix que AVAX/ETH
                elif symbol == "ETH/WAVAX":
                    base_price = 1 / 0.009340  # Inverse de WAVAX/ETH
                
                # Ajouter une variation cohérente selon le CEX
                variation = {
                    "binance": 1.0,
                    "kucoin": 0.998,    # Légèrement plus bas que Binance
                    "gate": 1.003       # Légèrement plus haut que Binance
                }.get(cex_name, 1.0)
                
                # Ajouter une légère variation aléatoire (±0.3% seulement pour plus de stabilité)
                random_variation = 1.0 + (random.random() * 0.006 - 0.003)
                
                # Calculer le prix final
                price = base_price * variation * random_variation
                
                logger.debug(f"Prix simulé sur {cex_name} pour {symbol}: {price}")
                return price
            else:
                # En mode réel, il faudrait interroger le CEX via son API
                # Cette partie nécessiterait une implémentation spécifique pour chaque CEX
                logger.warning(f"Récupération de prix réel sur {cex_name} non implémentée")
                return None
                
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du prix sur {cex_name}: {str(e)}")
            return None 