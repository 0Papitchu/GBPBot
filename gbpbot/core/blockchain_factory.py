from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple, Union
from loguru import logger
from web3 import Web3
import asyncio
import time
import aiohttp
from datetime import datetime, timedelta
import uuid
import logging
import traceback
import os
from cryptography.fernet import Fernet
from solana.keypair import Keypair
from solana.publickey import PublicKey
from gbpbot.utils.solana_imports import Pubkey
from functools import wraps
from web3.exceptions import TransactionNotFound, TimeExhausted
from collections import defaultdict
import random

from gbpbot.core.exceptions import (
    BlockchainError, RPCConnectionError, RPCTimeoutError, RPCResponseError,
    ContractCallError, TransactionError, TransactionFailedError, 
    TransactionTimeoutError, InsufficientFundsError, GasEstimationError,
    SwapError, SwapExecutionError, SlippageExceededError, PriceImpactTooHighError,
    ArbitrageError, ArbitrageExecutionError
)

class BaseBlockchainClient(ABC):
    """Classe de base abstraite pour tous les clients blockchain"""
    
    @abstractmethod
    async def connect(self) -> bool:
        """
        Établit une connexion avec la blockchain
        
        Returns:
            bool: True si la connexion est établie, False sinon
        """
        pass
    
    @abstractmethod
    async def get_token_price(self, token_address: str, base_token: str) -> float:
        """
        Récupère le prix d'un token par rapport à un autre
        
        Args:
            token_address: Adresse du token dont on veut connaître le prix
            base_token: Adresse du token de base (ex: USDC, WETH, etc.)
            
        Returns:
            float: Prix du token en unités de base_token
        """
        pass
    
    @abstractmethod
    async def execute_swap(self, token_in: str, token_out: str, amount_in: float, 
                          slippage: float = 0.5, deadline_seconds: int = 300,
                          gas_priority: str = "normal") -> Dict:
        """
        Exécute un swap entre deux tokens
        
        Args:
            token_in: Adresse du token d'entrée
            token_out: Adresse du token de sortie
            amount_in: Montant du token d'entrée à échanger
            slippage: Slippage maximum accepté en pourcentage
            deadline_seconds: Délai d'expiration de la transaction en secondes
            gas_priority: Priorité de gas ("low", "normal", "high")
            
        Returns:
            Dict: Informations sur la transaction
        """
        pass
    
    @abstractmethod
    async def get_token_balance(self, token_address: str, wallet_address: Optional[str] = None) -> float:
        """
        Récupère le solde d'un token pour un wallet donné
        
        Args:
            token_address: Adresse du token
            wallet_address: Adresse du wallet (ou None pour utiliser le wallet par défaut)
            
        Returns:
            float: Solde du token
        """
        pass
    
    @abstractmethod
    async def check_token_approval(self, token_address: str, spender_address: str, 
                                 amount: Optional[float] = None) -> bool:
        """
        Vérifie si un token est approuvé pour un spender
        
        Args:
            token_address: Adresse du token
            spender_address: Adresse du spender (ex: router DEX)
            amount: Montant à approuver (None pour unlimited)
            
        Returns:
            bool: True si le token est approuvé pour le montant spécifié
        """
        pass
    
    @abstractmethod
    async def approve_token(self, token_address: str, spender_address: str, 
                          amount: Optional[float] = None, gas_priority: str = "normal") -> Dict:
        """
        Approuve un token pour un spender
        
        Args:
            token_address: Adresse du token
            spender_address: Adresse du spender (ex: router DEX)
            amount: Montant à approuver (None pour unlimited)
            gas_priority: Priorité de gas ("low", "normal", "high")
            
        Returns:
            Dict: Informations sur la transaction
        """
        pass
    
    @abstractmethod
    async def wait_for_transaction(self, tx_hash: str, timeout: int = 120) -> Dict:
        """
        Attend la confirmation d'une transaction
        
        Args:
            tx_hash: Hash de la transaction
            timeout: Timeout en secondes
            
        Returns:
            Dict: Récépissé de la transaction
        """
        pass
    
    @abstractmethod
    async def get_new_tokens(self, since_block: Optional[int] = None, 
                           dex_filter: Optional[List[str]] = None) -> List[Dict]:
        """
        Récupère les nouveaux tokens créés sur la blockchain
        
        Args:
            since_block: Block à partir duquel chercher (None pour utiliser le dernier block)
            dex_filter: Liste des DEX à filtrer (None pour tous)
            
        Returns:
            List[Dict]: Liste des nouveaux tokens avec leurs informations
        """
        pass
    
    @abstractmethod
    async def analyze_contract(self, token_address: str) -> Dict:
        """
        Analyse le contrat d'un token pour détecter les risques
        
        Args:
            token_address: Adresse du token à analyser
            
        Returns:
            Dict: Résultat de l'analyse
        """
        pass
    
    @abstractmethod
    async def estimate_gas(self, tx: Dict) -> int:
        """
        Estime le gas nécessaire pour une transaction
        
        Args:
            tx: Transaction à estimer
            
        Returns:
            int: Estimation du gas
        """
        pass

class ContractCallError(Exception):
    """Exception raised when a contract call fails after retries"""
    pass

class AvaxBlockchainClient(BaseBlockchainClient):
    """Client blockchain pour Avalanche"""
    
    def __init__(self, config: Dict):
        """Initialise le client Avalanche"""
        self.config = config
        self.logger = logger.bind(blockchain="avalanche")
        self.web3 = None
        self.wallet_address = None
        self.private_key = None
        
        # Cache pour les prix des tokens
        self.price_cache = {}
        self.cache_expiry = 60  # 60 secondes par défaut
        
        # Métriques RPC
        self.rpc_metrics = defaultdict(lambda: {
            "success_count": 0,
            "error_count": 0,
            "timeout_count": 0,
            "total_time": 0,
            "last_latency": 0,
            "last_used": 0
        })
        
        # Pool de connexions RPC
        self.rpc_pool = {}
        
        # Initialiser le client
        self._initialize()
        
    def _initialize(self):
        """Initialise le client Web3 et charge la configuration"""
        try:
            # Initialiser le pool de connexions RPC
            self._init_rpc_pool()
            
            # Charger les adresses des tokens
            self._load_token_addresses()
            
            # Charger le wallet si configuré
            self._load_wallet()
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'initialisation du client Avalanche: {str(e)}")
            
    def _init_rpc_pool(self):
        """Initialise le pool de connexions RPC"""
        try:
            rpc_providers = self.config.get("rpc_providers", [])
            
            if not rpc_providers:
                self.logger.warning("Aucun fournisseur RPC configuré")
                return
                
            self.logger.info(f"Initialisation du pool RPC avec {len(rpc_providers)} fournisseurs")
            
            for provider in rpc_providers:
                url = provider.get("url")
                weight = provider.get("weight", 1)
                
                if not url:
                    continue
                    
                try:
                    # Créer l'instance Web3 avec timeout optimisé et gestion des sessions
                    web3_instance = Web3(Web3.HTTPProvider(
                        url,
                        request_kwargs={
                            "timeout": self.config.get("rpc", {}).get("timeout", 10),
                        }
                    ))
                    
                    # Vérifier la connexion
                    if web3_instance.is_connected():
                        self.rpc_pool[url] = {
                            "web3": web3_instance,
                            "weight": weight,
                            "url": url
                        }
                        self.logger.debug(f"Connexion RPC établie: {url}")
                    else:
                        self.logger.warning(f"Impossible de se connecter au RPC: {url}")
                        
                except Exception as e:
                    self.logger.error(f"Erreur lors de l'initialisation du RPC {url}: {str(e)}")
            
            # Sélectionner un fournisseur par défaut
            if self.rpc_pool:
                default_provider = self._select_weighted_provider()
                self.web3 = default_provider
                self.logger.info(f"Pool RPC initialisé avec {len(self.rpc_pool)} fournisseurs actifs")
            else:
                self.logger.error("Aucun fournisseur RPC disponible")
                
        except Exception as e:
            self.logger.error(f"Erreur lors de l'initialisation du pool RPC: {str(e)}")
            
    def _select_weighted_provider(self):
        """
        Sélectionne un fournisseur RPC en fonction de son poids et de ses performances
        
        Returns:
            Web3: Instance Web3 du fournisseur sélectionné
        """
        if not self.rpc_pool:
            self.logger.error("Aucun fournisseur RPC disponible")
            raise RPCConnectionError("Aucun fournisseur RPC disponible")
            
        # Calculer les poids ajustés en fonction des métriques
        adjusted_weights = {}
        
        for url, provider in self.rpc_pool.items():
            base_weight = provider["weight"]
            metrics = self.rpc_metrics[url]
            
            # Ajuster le poids en fonction des erreurs et de la latence
            success_rate = 1.0
            if metrics["success_count"] + metrics["error_count"] > 0:
                success_rate = metrics["success_count"] / (metrics["success_count"] + metrics["error_count"])
                
            latency_factor = 1.0
            if metrics["last_latency"] > 0:
                latency_factor = min(1.0, 1.0 / (metrics["last_latency"] / 1000))
                
            # Calculer le poids ajusté
            adjusted_weight = base_weight * success_rate * latency_factor
            
            # Ajouter un facteur aléatoire pour éviter de toujours choisir le même fournisseur
            adjusted_weight *= (0.9 + 0.2 * random.random())
            
            adjusted_weights[url] = max(0.1, adjusted_weight)  # Minimum weight of 0.1
            
        # Sélectionner un fournisseur en fonction des poids ajustés
        total_weight = sum(adjusted_weights.values())
        if total_weight <= 0:
            # Fallback to equal weights if all weights are 0
            urls = list(self.rpc_pool.keys())
            selected_url = random.choice(urls)
        else:
            # Weighted random selection
            r = random.uniform(0, total_weight)
            cumulative_weight = 0
            selected_url = list(self.rpc_pool.keys())[0]  # Default to first provider
            
            for url, weight in adjusted_weights.items():
                cumulative_weight += weight
                if r <= cumulative_weight:
                    selected_url = url
                    break
                    
        # Update last used timestamp
        self.rpc_metrics[selected_url]["last_used"] = time.time()
        
        return self.rpc_pool[selected_url]["web3"]
    
    async def connect(self) -> bool:
        """Établit une connexion avec la blockchain Avalanche"""
        try:
            # Récupérer la liste des providers depuis la config
            providers = self.config["rpc"]["providers"]["avalanche"]["mainnet"]
            
            if not providers:
                logger.error("❌ Aucun provider RPC disponible pour Avalanche")
                return False
            
            # Initialiser le pool de connexions RPC
            for _ in range(self.rpc_pool_size):
                # Sélectionner un provider selon les poids
                selected_provider = self._select_weighted_provider(providers)
                
                if not selected_provider:
                    logger.error("❌ Impossible de sélectionner un provider RPC")
                    return False
                
                # Créer l'instance Web3 avec timeout optimisé et gestion des sessions
                web3_instance = Web3(Web3.AsyncHTTPProvider(
                    selected_provider["url"],
                    request_kwargs={
                        "timeout": self.config["rpc"]["timeout"],
                        "headers": {"Content-Type": "application/json"},
                        "session": aiohttp.ClientSession(
                            connector=aiohttp.TCPConnector(limit=100, ttl_dns_cache=300)
                        )
                    }
                ))
                
                self.rpc_pool.append({
                    "web3": web3_instance,
                    "provider": selected_provider,
                    "health": 100,  # Score de santé initial
                    "last_used": 0  # Timestamp de dernière utilisation
                })
            
            # Définir l'instance Web3 principale
            if self.rpc_pool:
                self.web3 = self.rpc_pool[0]["web3"]
            else:
                logger.error("❌ Échec de l'initialisation du pool RPC")
                return False
            
            # Charger les adresses des tokens
            self._load_token_addresses()
            
            # Charger la configuration réseau
            self.network_config = {
                "chain_id": 43114,  # Avalanche C-Chain
                "native_token": "AVAX",
                "block_time": 2,    # En secondes
                "explorer_url": "https://snowtrace.io"
            }
            
            # Charger les informations du wallet
            self._load_wallet_info()
            
            logger.info(f"✅ Connecté à Avalanche avec un pool de {len(self.rpc_pool)} connexions RPC")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de la connexion à Avalanche: {str(e)}")
            return False
    
    def _load_token_addresses(self):
        """Charge les adresses des tokens depuis la configuration"""
        try:
            self.token_addresses = {}
            
            if "tokens" in self.config:
                # Charger les adresses de base (WAVAX, etc.)
                if "native_token_address" in self.config:
                    self.token_addresses["WAVAX"] = Web3.to_checksum_address(self.config["native_token_address"])
                    
                # Charger les tokens de base
                if "base_tokens" in self.config:
                    for token in self.config["base_tokens"]:
                        if "symbol" in token and "address" in token:
                            self.token_addresses[token["symbol"]] = Web3.to_checksum_address(token["address"])
                
                # Charger les tokens cibles
                if "target_tokens" in self.config:
                    for token in self.config["target_tokens"]:
                        if "symbol" in token and "address" in token:
                            self.token_addresses[token["symbol"]] = Web3.to_checksum_address(token["address"])
                
                self.logger.info(f"✅ {len(self.token_addresses)} adresses de tokens chargées")
            else:
                self.logger.warning("⚠️ Configuration des tokens non trouvée")
                
        except Exception as e:
            self.logger.error(f"❌ Erreur lors du chargement des adresses de tokens: {str(e)}")
            
    def _load_wallet(self):
        """Charge le wallet depuis la configuration"""
        try:
            # Vérifier si une clé privée est fournie dans la configuration
            private_key = self.config.get("private_key")
            
            if private_key:
                self.private_key = private_key
                account = self.web3.eth.account.from_key(private_key)
                self.wallet_address = account.address
                self.logger.info(f"✅ Wallet chargé: {self.wallet_address}")
            else:
                self.logger.warning("⚠️ Configuration du wallet non trouvée")
                
        except Exception as e:
            self.logger.error(f"❌ Erreur lors du chargement du wallet: {str(e)}")
            
    async def get_token_price(self, token_address: str, base_token: str) -> float:
        """Récupère le prix d'un token sur Avalanche"""
        try:
            # Vérifier le cache
            cache_key = f"{token_address.lower()}_{base_token.lower()}"
            current_time = time.time()
            
            if cache_key in self.price_cache and current_time - self.price_cache[cache_key]["timestamp"] < self.cache_expiry:
                # Utiliser la valeur en cache
                return self.price_cache[cache_key]["price"]
            
            # Convertir les adresses en format checksum
            token_address = self.web3.to_checksum_address(token_address)
            
            # Convertir le symbole en adresse si nécessaire
            if base_token in self.token_addresses:
                base_token = self.token_addresses[base_token]
            base_token = self.web3.to_checksum_address(base_token)
            
            # Récupérer les adresses des DEX depuis la config
            dex_config = self.config.get("dex", {}).get("avalanche", {})
            router_addresses = []
            
            # Ajouter les routers des différents DEX
            if "traderjoe" in dex_config:
                router_addresses.append(dex_config["traderjoe"]["router_address"])
            if "pangolin" in dex_config:
                router_addresses.append(dex_config["pangolin"]["router_address"])
            
            if not router_addresses:
                logger.error("❌ Aucune adresse de router DEX configurée")
                return 0
            
            # Charger l'ABI du router
            router_abi = self._load_router_abi()
            
            # Montant d'entrée pour la simulation (1 token)
            token_contract = self.web3.eth.contract(address=token_address, abi=self._load_erc20_abi())
            decimals = await self._safe_call_contract_function(token_contract.functions.decimals())
            amount_in = 10 ** decimals
            
            # Créer les tâches pour interroger tous les DEX en parallèle
            tasks = []
            for router_address in router_addresses:
                router_contract = self.web3.eth.contract(address=router_address, abi=router_abi)
                tasks.append(self._get_price_from_dex(router_contract, token_address, base_token, amount_in))
            
            # Exécuter toutes les requêtes en parallèle
            prices = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filtrer les erreurs et calculer le prix moyen
            valid_prices = [p for p in prices if isinstance(p, (int, float)) and p > 0]
            
            if not valid_prices:
                logger.warning(f"⚠️ Impossible d'obtenir un prix valide pour {token_address}")
                return 0
            
            # Utiliser le prix médian pour éviter les outliers
            valid_prices.sort()
            if len(valid_prices) % 2 == 0:
                price = (valid_prices[len(valid_prices)//2 - 1] + valid_prices[len(valid_prices)//2]) / 2
            else:
                price = valid_prices[len(valid_prices)//2]
            
            # Mettre en cache
            self.price_cache[cache_key] = {
                "price": price,
                "timestamp": current_time,
                "sources": len(valid_prices)
            }
            
            # Limiter la taille du cache (LRU simple)
            if len(self.price_cache) > 1000:
                # Supprimer les entrées les plus anciennes
                oldest_keys = sorted(
                    self.price_cache.keys(),
                    key=lambda k: self.price_cache[k]["timestamp"]
                )[:100]
                for key in oldest_keys:
                    del self.price_cache[key]
            
            return price
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de la récupération du prix pour {token_address}: {str(e)}")
            return 0
    
    async def _get_price_from_dex(self, router_contract, token_address, base_token, amount_in):
        """Récupère le prix d'un token sur un DEX spécifique"""
        try:
            # Récupérer les montants out pour 1 token
            amounts_out = await self._safe_call_contract_function(
                router_contract.functions.getAmountsOut(
                    amount_in,
                    [token_address, base_token]
                )
            )
            
            # Le prix est le ratio entre les deux montants
            if amounts_out and len(amounts_out) >= 2 and amounts_out[0] > 0:
                return amounts_out[1] / amounts_out[0]
            return 0
        except Exception as e:
            logger.debug(f"Échec de récupération du prix sur DEX: {str(e)}")
            return 0
    
    async def _safe_call_contract_function(self, function, *args, **kwargs):
        """
        Appelle une fonction de contrat de manière sécurisée avec gestion des erreurs
        
        Args:
            function: Fonction du contrat à appeler
            *args: Arguments positionnels pour la fonction
            **kwargs: Arguments nommés pour la fonction
            
        Returns:
            Le résultat de l'appel de la fonction
        """
        max_retries = 3
        retry_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                # Sélectionner un fournisseur RPC
                web3 = self._select_weighted_provider()
                
                # Mesurer le temps d'exécution
                start_time = time.time()
                
                # Exécuter la fonction
                if callable(function):
                    if args or kwargs:
                        result = await function(*args, **kwargs)
                    else:
                        result = await function.call()
                else:
                    raise ValueError("La fonction fournie n'est pas callable")
                
                # Calculer la latence
                latency = time.time() - start_time
                
                # Mettre à jour les métriques
                provider_url = next((url for url, provider in self.rpc_pool.items() 
                                   if provider["web3"] == web3), None)
                if provider_url:
                    self.rpc_metrics[provider_url]["success_count"] += 1
                    self.rpc_metrics[provider_url]["total_time"] += latency
                    self.rpc_metrics[provider_url]["last_latency"] = latency
                
                return result
                
            except Exception as e:
                self.logger.warning(f"Erreur lors de l'appel de la fonction (tentative {attempt+1}/{max_retries}): {str(e)}")
                
                # Mettre à jour les métriques
                if web3:
                    provider_url = next((url for url, provider in self.rpc_pool.items() 
                                       if provider["web3"] == web3), None)
                    if provider_url:
                        self.rpc_metrics[provider_url]["error_count"] += 1
                
                # Attendre avant de réessayer
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (attempt + 1))
        
        # Toutes les tentatives ont échoué
        self.logger.error(f"Échec de l'appel de la fonction après {max_retries} tentatives")
        raise ContractCallError(f"Échec de l'appel de la fonction après {max_retries} tentatives")
    
    def _load_erc20_abi(self) -> List:
        """Charge l'ABI d'un token ERC20"""
        return [
            {
                "constant": True,
                "inputs": [],
                "name": "decimals",
                "outputs": [{"name": "", "type": "uint8"}],
                "payable": False,
                "stateMutability": "view",
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [{"name": "_owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "balance", "type": "uint256"}],
                "payable": False,
                "stateMutability": "view",
                "type": "function"
            }
        ]
    
    def _load_router_abi(self) -> List:
        """Charge l'ABI du router DEX"""
        return [
            {
                "inputs": [
                    {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                    {"internalType": "address[]", "name": "path", "type": "address[]"}
                ],
                "name": "getAmountsOut",
                "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [
                    {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                    {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"},
                    {"internalType": "address[]", "name": "path", "type": "address[]"},
                    {"internalType": "address", "name": "to", "type": "address"},
                    {"internalType": "uint256", "name": "deadline", "type": "uint256"}
                ],
                "name": "swapExactTokensForTokens",
                "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [
                    {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                    {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"},
                    {"internalType": "address[]", "name": "path", "type": "address[]"},
                    {"internalType": "address", "name": "to", "type": "address"},
                    {"internalType": "uint256", "name": "deadline", "type": "uint256"}
                ],
                "name": "swapExactTokensForAVAX",
                "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [
                    {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"},
                    {"internalType": "address[]", "name": "path", "type": "address[]"},
                    {"internalType": "address", "name": "to", "type": "address"},
                    {"internalType": "uint256", "name": "deadline", "type": "uint256"}
                ],
                "name": "swapExactAVAXForTokens",
                "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}],
                "stateMutability": "payable",
                "type": "function"
            },
            {
                "inputs": [
                    {"internalType": "address", "name": "tokenA", "type": "address"},
                    {"internalType": "address", "name": "tokenB", "type": "address"}
                ],
                "name": "getReserves",
                "outputs": [
                    {"internalType": "uint256", "name": "reserveA", "type": "uint256"},
                    {"internalType": "uint256", "name": "reserveB", "type": "uint256"}
                ],
                "stateMutability": "view",
                "type": "function"
            }
        ]
    
    def _load_dex_routers(self):
        """
        Charge les adresses des routeurs DEX à partir de la configuration
        """
        try:
            if "dex" not in self.config or "routers" not in self.config["dex"]:
                self.logger.warning("Configuration DEX manquante, utilisation des routeurs par défaut")
                # Adresses par défaut pour Trader Joe et Pangolin
                self.dex_routers = {
                    "traderjoe": "0x60aE616a2155Ee3d9A68541Ba4544862310933d4",
                    "pangolin": "0xE54Ca86531e17Ef3616d22Ca28b0D458b6C89106"
                }
                return
            
            routers = self.config["dex"]["routers"]
            for router in routers:
                name = router["name"]
                address = router["address"]
                self.dex_routers[name] = address
            
            self.logger.info(f"Chargé {len(self.dex_routers)} routeurs DEX")
        
        except Exception as e:
            self.logger.error(f"Erreur lors du chargement des routeurs DEX: {str(e)}")
            # Utiliser des routeurs par défaut en cas d'erreur
            self.dex_routers = {
                "traderjoe": "0x60aE616a2155Ee3d9A68541Ba4544862310933d4",
                "pangolin": "0xE54Ca86531e17Ef3616d22Ca28b0D458b6C89106"
            }
    
    # Implémentations des autres méthodes abstraites
    # Ces méthodes seront implémentées progressivement dans les prochaines étapes
    
    async def execute_swap(self, 
                          from_token: str, 
                          to_token: str, 
                          amount: float, 
                          wallet_address: str, 
                          private_key: str, 
                          slippage: float = 0.5, 
                          deadline_minutes: int = 20,
                          gas_boost: float = 1.1,
                          dex_router: Optional[str] = None) -> Dict:
        """
        Exécute un swap entre deux tokens sur Avalanche
        
        Args:
            from_token: Adresse du token source
            to_token: Adresse du token destination
            amount: Montant à échanger
            wallet_address: Adresse du portefeuille
            private_key: Clé privée du portefeuille
            slippage: Pourcentage de slippage toléré (par défaut 0.5%)
            deadline_minutes: Délai d'expiration en minutes (par défaut 20 min)
            gas_boost: Multiplicateur pour le gas price (par défaut 1.1x)
            dex_router: Adresse du router DEX à utiliser (si None, utilise le router par défaut)
            
        Returns:
            Dict: Informations sur la transaction
        """
        try:
            self.logger.info(f"Préparation du swap: {amount} {from_token} -> {to_token}")
            
            # Convertir les adresses en format checksum
            from_token = Web3.to_checksum_address(from_token)
            to_token = Web3.to_checksum_address(to_token)
            wallet_address = Web3.to_checksum_address(wallet_address)
            
            # Sélectionner le meilleur RPC
            web3 = self._select_weighted_provider()
            
            # Déterminer si nous traitons avec AVAX natif
            is_avax_in = from_token.lower() == self.config.get("native_token_address").lower()
            is_avax_out = to_token.lower() == self.config.get("native_token_address").lower()
            
            # Obtenir le router à utiliser
            if not dex_router:
                # Utiliser le premier router par défaut
                dex_routers = self.config.get("dex_routers", {})
                if not dex_routers:
                    raise ValueError("Aucun router DEX configuré")
                dex_router = list(dex_routers.values())[0]
            
            dex_router = Web3.to_checksum_address(dex_router)
            router_contract = web3.eth.contract(address=dex_router, abi=self._load_router_abi())
            
            # Calculer le deadline
            deadline = int(time.time() + (deadline_minutes * 60))
            
            # Préparer le chemin de swap
            path = [from_token, to_token]
            
            # Gérer les tokens ERC20
            if not is_avax_in:
                # Obtenir les décimales du token source
                token_contract = web3.eth.contract(address=from_token, abi=self._load_erc20_abi())
                decimals = await self._safe_call_contract_function(token_contract.functions.decimals())
                
                # Convertir le montant en wei
                amount_in_wei = int(amount * (10 ** decimals))
                
                # Vérifier l'allowance et approuver si nécessaire
                allowance = await self._safe_call_contract_function(
                    token_contract.functions.allowance(wallet_address, dex_router)
                )
                
                if allowance < amount_in_wei:
                    self.logger.info(f"Approbation nécessaire pour {amount} {from_token}")
                    approve_tx = await self._build_and_send_transaction(
                        token_contract.functions.approve(dex_router, 2**256 - 1),
                        wallet_address,
                        private_key,
                        gas_boost=gas_boost
                    )
                    self.logger.info(f"Approbation effectuée: {approve_tx['transactionHash'].hex()}")
                    
                    # Attendre que l'approbation soit confirmée
                    await self._wait_for_transaction(web3, approve_tx['transactionHash'].hex())
            else:
                # Pour AVAX, utiliser 18 décimales
                amount_in_wei = web3.to_wei(amount, 'ether')
            
            # Obtenir le prix estimé
            if is_avax_in:
                amounts_out = await self._safe_call_contract_function(
                    router_contract.functions.getAmountsOut(amount_in_wei, path)
                )
            else:
                amounts_out = await self._safe_call_contract_function(
                    router_contract.functions.getAmountsOut(amount_in_wei, path)
                )
            
            # Calculer le montant minimum avec slippage
            amount_out = amounts_out[1]
            min_amount_out = int(amount_out * (1 - slippage / 100))
            
            self.logger.info(f"Prix estimé: {amount_out}, Min avec slippage: {min_amount_out}")
            
            # Construire la transaction de swap en fonction du type
            if is_avax_in:
                # AVAX -> Token
                swap_function = router_contract.functions.swapExactAVAXForTokens(
                    min_amount_out,
                    path,
                    wallet_address,
                    deadline
                )
                value = amount_in_wei
            elif is_avax_out:
                # Token -> AVAX
                swap_function = router_contract.functions.swapExactTokensForAVAX(
                    amount_in_wei,
                    min_amount_out,
                    path,
                    wallet_address,
                    deadline
                )
                value = 0
            else:
                # Token -> Token
                swap_function = router_contract.functions.swapExactTokensForTokens(
                    amount_in_wei,
                    min_amount_out,
                    path,
                    wallet_address,
                    deadline
                )
                value = 0
            
            # Envoyer la transaction
            tx_receipt = await self._build_and_send_transaction(
                swap_function,
                wallet_address,
                private_key,
                value=value,
                gas_boost=gas_boost
            )
            
            tx_hash = tx_receipt['transactionHash'].hex()
            self.logger.info(f"Swap exécuté: {tx_hash}")
            
            # Attendre la confirmation et récupérer les détails
            receipt = await self._wait_for_transaction(web3, tx_hash)
            
            # Analyser les logs pour obtenir les montants réels
            swap_info = {
                'transaction_hash': tx_hash,
                'from_token': from_token,
                'to_token': to_token,
                'amount_in': amount,
                'amount_out_min': min_amount_out,
                'gas_used': receipt['gasUsed'],
                'status': receipt['status']
            }
            
            return swap_info
            
        except Exception as e:
            self.logger.error(f"Erreur lors du swap: {str(e)}")
            raise SwapExecutionError(f"Échec du swap {from_token} -> {to_token}: {str(e)}")
    
    async def _build_and_send_transaction(self, 
                                         contract_function, 
                                         wallet_address: str, 
                                         private_key: str, 
                                         value: int = 0, 
                                         gas_boost: float = 1.1) -> Dict:
        """
        Construit et envoie une transaction avec optimisation de gas
        
        Args:
            contract_function: Fonction du contrat à appeler
            wallet_address: Adresse du portefeuille
            private_key: Clé privée du portefeuille
            value: Valeur en wei à envoyer (pour les transactions AVAX)
            gas_boost: Multiplicateur pour le gas price
            
        Returns:
            Dict: Reçu de transaction
        """
        web3 = self._select_weighted_provider()
        
        # Estimer le gas nécessaire avec une marge de sécurité
        try:
            gas_estimate = await self._safe_call_contract_function(
                contract_function.estimate_gas, {'from': wallet_address, 'value': value}
            )
            gas_limit = int(gas_estimate * 1.2)  # Ajouter 20% de marge
        except Exception as e:
            self.logger.warning(f"Erreur lors de l'estimation du gas: {str(e)}")
            gas_limit = 500000  # Valeur par défaut sécuritaire
        
        # Obtenir le nonce
        nonce = web3.eth.get_transaction_count(wallet_address)
        
        # Obtenir le gas price actuel et appliquer le boost
        gas_price = web3.eth.gas_price
        boosted_gas_price = int(gas_price * gas_boost)
        
        # Construire la transaction
        tx = {
            'from': wallet_address,
            'value': value,
            'gas': gas_limit,
            'gasPrice': boosted_gas_price,
            'nonce': nonce,
            'chainId': self.config.get("chain_id", 43114)  # Avalanche C-Chain par défaut
        }
        
        # Construire la transaction avec le contrat
        tx = contract_function.build_transaction(tx)
        
        # Signer la transaction
        signed_tx = web3.eth.account.sign_transaction(tx, private_key)
        
        # Envoyer la transaction
        tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        # Attendre la confirmation initiale
        tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
        
        return tx_receipt
    
    async def _wait_for_transaction(self, web3, tx_hash: str, max_confirmations: int = 2) -> Dict:
        """
        Attend qu'une transaction soit confirmée
        
        Args:
            web3: Instance Web3
            tx_hash: Hash de la transaction
            max_confirmations: Nombre de confirmations à attendre
            
        Returns:
            Dict: Reçu de transaction
        """
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
        
        if receipt['status'] != 1:
            self.logger.error(f"La transaction a échoué: {tx_hash}")
            raise TransactionFailedError(f"La transaction {tx_hash} a échoué")
        
        # Attendre des confirmations supplémentaires si nécessaire
        if max_confirmations > 1:
            current_block = web3.eth.block_number
            confirmation_block = receipt['blockNumber'] + max_confirmations - 1
            
            while web3.eth.block_number < confirmation_block:
                self.logger.info(f"En attente de confirmations: {web3.eth.block_number}/{confirmation_block}")
                await asyncio.sleep(2)
        
        return receipt
    
    async def find_arbitrage_opportunity(self, 
                                   from_token: str,
                                   amount_in: float,
                                   path_length: int = 2,
                                   min_profit_threshold: float = 0.01) -> Dict:
        """
        Recherche des opportunités d'arbitrage pour un token donné
        
        Args:
            from_token: Adresse du token de départ
            amount_in: Montant à utiliser pour l'arbitrage
            path_length: Longueur du chemin d'arbitrage (par défaut 2)
            min_profit_threshold: Seuil de profit minimum en pourcentage (par défaut 0.01 = 1%)
            
        Returns:
            Dict: Informations sur l'opportunité d'arbitrage trouvée ou None
        """
        # Vérifier que le token est valide
        if not Web3.is_address(from_token):
            raise ValueError(f"Adresse de token invalide: {from_token}")
        
        # Obtenir les tokens de base pour les paires
        base_tokens = self._get_base_tokens()
        
        # Construire les chemins potentiels
        paths = []
        for base_token in base_tokens:
            if base_token.lower() != from_token.lower():
                # Chemin simple: from_token -> base_token -> from_token
                paths.append([from_token, base_token, from_token])
        
        # Évaluer chaque chemin
        best_profit = 0
        best_path = None
        best_amounts = None
        best_dexes = None
        
        for path in paths:
            try:
                # Simuler l'exécution du chemin
                amounts, dexes = await self._simulate_arbitrage_path(path, amount_in)
                
                # Calculer le profit
                profit = amounts[-1] - amount_in
                profit_percentage = profit / amount_in
                
                if profit_percentage > best_profit and profit_percentage >= min_profit_threshold:
                    best_profit = profit_percentage
                    best_path = path
                    best_amounts = amounts
                    best_dexes = dexes
            
            except Exception as e:
                self.logger.warning(f"Erreur lors de la simulation du chemin {path}: {str(e)}")
                continue
        
        if best_path:
            # Construire le résultat
            token_symbols = []
            for token in best_path:
                symbol = await self._get_token_symbol(token)
                token_symbols.append(symbol)
            
            arbitrage_result = {
                "path": best_path,
                "symbols": token_symbols,
                "amounts": best_amounts,
                "dexes": best_dexes,
                "profit": best_amounts[-1] - amount_in,
                "profit_percentage": best_profit * 100,  # Convertir en pourcentage
                "amount_in": amount_in
            }
            
            return arbitrage_result
        
        return None

    async def monitor_mev_for_tokens(self, 
                                     token_addresses: List[str], 
                                     time_window_seconds: int = 300) -> Dict:
        """
        Surveille l'activité MEV pour un ensemble de tokens
        
        Args:
            token_addresses: Liste des adresses de tokens à surveiller
            time_window_seconds: Fenêtre de temps en secondes pour l'analyse
            
        Returns:
            Dict: Rapport d'activité MEV
        """
        # Importer le moniteur MEV
        from gbpbot.core.mev_monitor import MEVMonitor
        
        # Créer une instance du moniteur MEV
        mev_monitor = MEVMonitor(self, self.logger)
        
        # Exécuter l'analyse MEV
        return await mev_monitor.monitor_mev_activity(token_addresses, time_window_seconds)
    
    async def protect_transaction_from_mev(self, 
                                         tx_params: Dict, 
                                         protection_level: str = 'medium',
                                         private_mempool: bool = False) -> Dict:
        """
        Applique des protections anti-MEV à une transaction
        
        Args:
            tx_params: Paramètres de la transaction
            protection_level: Niveau de protection ('low', 'medium', 'high')
            private_mempool: Utiliser un mempool privé si disponible
            
        Returns:
            Dict: Paramètres de transaction modifiés
        """
        # Importer le moniteur MEV
        from gbpbot.core.mev_monitor import MEVMonitor
        
        # Créer une instance du moniteur MEV
        mev_monitor = MEVMonitor(self, self.logger)
        
        # Appliquer les protections
        return await mev_monitor.protect_transaction(tx_params, protection_level, private_mempool)

class SolanaBlockchainClient(BaseBlockchainClient):
    """Client blockchain pour Solana"""
    
    return False, {"error": str(e)}

# Exemple de décorateur pour le monitoring des performances
def monitor_performance(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        result = await func(*args, **kwargs)
        execution_time = time.time() - start_time
        
        # Enregistrer les métriques
        metrics.record_execution_time(func.__name__, execution_time)
        
        return result
    return wrapper

# Utilisation
@monitor_performance
async def execute_swap(self, *args, **kwargs):
    # ...

class BlockchainClientFactory:
    """Factory pour créer des clients blockchain"""
    
    @staticmethod
    def create_client(blockchain_type: str, config: dict):
        """
        Crée un client blockchain en fonction du type spécifié
        
        Args:
            blockchain_type: Type de blockchain ('avalanche', 'ethereum', 'solana', etc.)
            config: Configuration du client
            
        Returns:
            Un client blockchain
        """
        if blockchain_type.lower() == "avalanche":
            return AvaxBlockchainClient(config)
        elif blockchain_type.lower() == "solana":
            return SolanaBlockchainClient(config)
        else:
            raise ValueError(f"Type de blockchain non supporté: {blockchain_type}")