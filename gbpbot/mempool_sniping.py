#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module de sniping ultra-rapide via surveillance du mempool.
Ce module permet de détecter les nouvelles paires de trading dès leur apparition
dans le mempool et d'exécuter des transactions avant qu'elles ne soient confirmées.
"""

import os
import sys
import time
import json
import asyncio
import websockets
from web3 import Web3
from typing import Dict, List, Any, Callable, Optional
from loguru import logger
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Configurer le logger
logger.remove()
logger.add(sys.stderr, level="INFO")
logger.add("mempool_sniping.log", rotation="10 MB", level="DEBUG")

class MempoolSniping:
    """Classe pour le sniping ultra-rapide via surveillance du mempool."""
    
    def __init__(self, 
                 web3_provider: str = None, 
                 wallet_private_key: str = None,
                 min_liquidity: float = 1.0,
                 max_buy_amount: float = 0.1,
                 gas_boost_percentage: int = 10,
                 target_dexes: List[str] = None,
                 blacklisted_tokens: List[str] = None):
        """
        Initialiser le module de sniping mempool.
        
        Args:
            web3_provider: URL du fournisseur Web3 (ex: Infura, Alchemy)
            wallet_private_key: Clé privée du wallet pour les transactions
            min_liquidity: Liquidité minimale requise pour le sniping (en ETH/BNB)
            max_buy_amount: Montant maximum à dépenser par transaction (en ETH/BNB)
            gas_boost_percentage: Pourcentage d'augmentation du gas pour être prioritaire
            target_dexes: Liste des DEX à surveiller (adresses des routeurs)
            blacklisted_tokens: Liste des tokens à ignorer (adresses)
        """
        # Configuration Web3
        self.web3_provider = web3_provider or os.getenv("WEB3_PROVIDER_URL")
        self.wallet_private_key = wallet_private_key or os.getenv("WALLET_PRIVATE_KEY")
        
        if not self.web3_provider:
            raise ValueError("Web3 provider URL is required")
        
        self.web3 = Web3(Web3.HTTPProvider(self.web3_provider))
        self.ws_provider = os.getenv("WEB3_WS_PROVIDER_URL")
        
        # Vérifier la connexion
        if not self.web3.is_connected():
            raise ConnectionError("Failed to connect to Web3 provider")
        
        # Configuration du wallet
        if self.wallet_private_key:
            self.account = self.web3.eth.account.from_key(self.wallet_private_key)
            self.wallet_address = self.account.address
            logger.info(f"Wallet configured: {self.wallet_address}")
        else:
            self.account = None
            self.wallet_address = None
            logger.warning("No wallet private key provided, running in read-only mode")
        
        # Configuration du sniping
        self.min_liquidity = min_liquidity
        self.max_buy_amount = max_buy_amount
        self.gas_boost_percentage = gas_boost_percentage
        
        # DEX à surveiller (adresses des routeurs)
        self.target_dexes = target_dexes or [
            # Uniswap V2 Router
            "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D",
            # PancakeSwap Router
            "0x10ED43C718714eb63d5aA57B78B54704E256024E",
            # SushiSwap Router
            "0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F"
        ]
        self.target_dexes = [addr.lower() for addr in self.target_dexes]
        
        # Tokens blacklistés
        self.blacklisted_tokens = blacklisted_tokens or []
        self.blacklisted_tokens = [addr.lower() for addr in self.blacklisted_tokens]
        
        # État du sniping
        self.is_running = False
        self.pending_txs = {}
        self.detected_pairs = {}
        
        # Callbacks
        self.on_pair_detected = None
        self.on_transaction_executed = None
        
        logger.info("Mempool sniping module initialized")
    
    async def start_monitoring(self):
        """Démarrer la surveillance du mempool."""
        if not self.ws_provider:
            raise ValueError("WebSocket provider URL is required for mempool monitoring")
        
        self.is_running = True
        logger.info("Starting mempool monitoring...")
        
        async with websockets.connect(self.ws_provider) as websocket:
            # S'abonner aux transactions en attente
            await websocket.send(json.dumps({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "eth_subscribe",
                "params": ["newPendingTransactions"]
            }))
            
            subscription_response = await websocket.recv()
            logger.debug(f"Subscription response: {subscription_response}")
            
            # Boucle principale de surveillance
            while self.is_running:
                try:
                    message = await websocket.recv()
                    tx_hash = json.loads(message)["params"]["result"]
                    
                    # Récupérer les détails de la transaction
                    await self._process_pending_transaction(tx_hash)
                    
                except Exception as e:
                    logger.error(f"Error in mempool monitoring: {e}")
                    await asyncio.sleep(1)
    
    async def _process_pending_transaction(self, tx_hash: str):
        """
        Traiter une transaction en attente.
        
        Args:
            tx_hash: Hash de la transaction
        """
        try:
            # Récupérer les détails de la transaction
            tx = self.web3.eth.get_transaction(tx_hash)
            
            # Ignorer les transactions sans données ou vers des adresses non ciblées
            if not tx or not tx.to or not tx.input or tx.to.lower() not in self.target_dexes:
                return
            
            # Analyser les données de la transaction pour détecter les ajouts de liquidité
            if self._is_add_liquidity_tx(tx):
                token_address = self._extract_token_address(tx)
                
                if token_address and token_address.lower() not in self.blacklisted_tokens:
                    # Vérifier si le token est nouveau ou a une liquidité suffisante
                    if await self._check_token_eligibility(token_address):
                        pair_info = {
                            "token_address": token_address,
                            "router_address": tx.to,
                            "detected_at": time.time(),
                            "tx_hash": tx_hash
                        }
                        
                        # Stocker les informations de la paire détectée
                        self.detected_pairs[token_address.lower()] = pair_info
                        
                        logger.info(f"New trading pair detected: {token_address}")
                        
                        # Exécuter le callback si défini
                        if self.on_pair_detected:
                            self.on_pair_detected(pair_info)
                        
                        # Exécuter le sniping si en mode actif
                        if self.wallet_private_key:
                            await self._execute_sniping(pair_info)
        
        except Exception as e:
            logger.error(f"Error processing transaction {tx_hash}: {e}")
    
    def _is_add_liquidity_tx(self, tx) -> bool:
        """
        Vérifier si une transaction est un ajout de liquidité.
        
        Args:
            tx: Transaction à analyser
            
        Returns:
            bool: True si c'est un ajout de liquidité, False sinon
        """
        # Signatures des fonctions d'ajout de liquidité
        add_liquidity_signatures = [
            # Uniswap/PancakeSwap addLiquidityETH
            "0xf305d719",
            # Uniswap/PancakeSwap addLiquidity
            "0xe8e33700"
        ]
        
        if tx.input and len(tx.input) >= 10:
            function_signature = tx.input[:10]
            return function_signature in add_liquidity_signatures
        
        return False
    
    def _extract_token_address(self, tx) -> Optional[str]:
        """
        Extraire l'adresse du token d'une transaction d'ajout de liquidité.
        
        Args:
            tx: Transaction à analyser
            
        Returns:
            Optional[str]: Adresse du token ou None si non trouvée
        """
        try:
            # Pour addLiquidityETH, le token est le premier paramètre (32 bytes après la signature)
            if tx.input.startswith("0xf305d719"):
                token_address = "0x" + tx.input[34:74]
                return self.web3.to_checksum_address(token_address)
            
            # Pour addLiquidity, les tokens sont les deux premiers paramètres
            elif tx.input.startswith("0xe8e33700"):
                token_address = "0x" + tx.input[34:74]
                return self.web3.to_checksum_address(token_address)
            
        except Exception as e:
            logger.error(f"Error extracting token address: {e}")
        
        return None
    
    async def _check_token_eligibility(self, token_address: str) -> bool:
        """
        Vérifier si un token est éligible pour le sniping.
        
        Args:
            token_address: Adresse du token à vérifier
            
        Returns:
            bool: True si le token est éligible, False sinon
        """
        try:
            # Vérifier si le token est déjà connu
            if token_address.lower() in self.detected_pairs:
                return False
            
            # Vérifier si le token est blacklisté
            if token_address.lower() in self.blacklisted_tokens:
                return False
            
            # Vérifier si le token a un contrat valide
            token_code = self.web3.eth.get_code(token_address)
            if not token_code or token_code == "0x":
                return False
            
            # Vérifier la liquidité (à implémenter selon le DEX)
            # Cette vérification peut nécessiter des appels spécifiques au DEX
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking token eligibility: {e}")
            return False
    
    async def _execute_sniping(self, pair_info: Dict[str, Any]):
        """
        Exécuter une transaction de sniping.
        
        Args:
            pair_info: Informations sur la paire détectée
        """
        if not self.wallet_private_key:
            logger.warning("Cannot execute sniping: no wallet private key provided")
            return
        
        try:
            token_address = pair_info["token_address"]
            router_address = pair_info["router_address"]
            
            logger.info(f"Executing sniping for token: {token_address}")
            
            # Obtenir le prix du gas actuel
            gas_price = self.web3.eth.gas_price
            
            # Augmenter le prix du gas pour être prioritaire
            boosted_gas_price = int(gas_price * (100 + self.gas_boost_percentage) / 100)
            
            # Construire la transaction de swap (à adapter selon le DEX)
            # Cet exemple utilise la fonction swapExactETHForTokens d'Uniswap/PancakeSwap
            
            # Charger l'ABI du routeur (simplifié pour l'exemple)
            router_abi = [
                {
                    "inputs": [
                        {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"},
                        {"internalType": "address[]", "name": "path", "type": "address[]"},
                        {"internalType": "address", "name": "to", "type": "address"},
                        {"internalType": "uint256", "name": "deadline", "type": "uint256"}
                    ],
                    "name": "swapExactETHForTokens",
                    "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}],
                    "stateMutability": "payable",
                    "type": "function"
                }
            ]
            
            # Créer le contrat du routeur
            router_contract = self.web3.eth.contract(address=router_address, abi=router_abi)
            
            # Adresse du token natif (ETH, BNB, etc.)
            weth_address = self.web3.to_checksum_address("0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2")  # WETH
            
            # Chemin de swap
            path = [weth_address, token_address]
            
            # Deadline (30 minutes)
            deadline = int(time.time() + 1800)
            
            # Montant à acheter (en wei)
            amount_in_wei = self.web3.to_wei(self.max_buy_amount, "ether")
            
            # Montant minimum de tokens à recevoir (0 pour accepter n'importe quel montant)
            amount_out_min = 0
            
            # Construire la transaction
            tx = router_contract.functions.swapExactETHForTokens(
                amount_out_min,
                path,
                self.wallet_address,
                deadline
            ).build_transaction({
                "from": self.wallet_address,
                "value": amount_in_wei,
                "gas": 300000,  # Limite de gas
                "gasPrice": boosted_gas_price,
                "nonce": self.web3.eth.get_transaction_count(self.wallet_address)
            })
            
            # Signer la transaction
            signed_tx = self.web3.eth.account.sign_transaction(tx, self.wallet_private_key)
            
            # Envoyer la transaction
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            logger.info(f"Sniping transaction sent: {tx_hash.hex()}")
            
            # Stocker la transaction en attente
            self.pending_txs[tx_hash.hex()] = {
                "token_address": token_address,
                "amount": self.max_buy_amount,
                "gas_price": boosted_gas_price,
                "timestamp": time.time()
            }
            
            # Attendre la confirmation de la transaction
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
            
            if receipt.status == 1:
                logger.info(f"Sniping transaction confirmed: {tx_hash.hex()}")
                
                # Exécuter le callback si défini
                if self.on_transaction_executed:
                    self.on_transaction_executed({
                        "tx_hash": tx_hash.hex(),
                        "token_address": token_address,
                        "amount": self.max_buy_amount,
                        "status": "success"
                    })
            else:
                logger.error(f"Sniping transaction failed: {tx_hash.hex()}")
                
                # Exécuter le callback si défini
                if self.on_transaction_executed:
                    self.on_transaction_executed({
                        "tx_hash": tx_hash.hex(),
                        "token_address": token_address,
                        "amount": self.max_buy_amount,
                        "status": "failed"
                    })
            
        except Exception as e:
            logger.error(f"Error executing sniping: {e}")
    
    def stop_monitoring(self):
        """Arrêter la surveillance du mempool."""
        self.is_running = False
        logger.info("Stopping mempool monitoring...")
    
    def set_on_pair_detected_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """
        Définir le callback à exécuter lorsqu'une nouvelle paire est détectée.
        
        Args:
            callback: Fonction à appeler avec les informations de la paire
        """
        self.on_pair_detected = callback
    
    def set_on_transaction_executed_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """
        Définir le callback à exécuter lorsqu'une transaction est exécutée.
        
        Args:
            callback: Fonction à appeler avec les informations de la transaction
        """
        self.on_transaction_executed = callback
    
    def add_to_blacklist(self, token_address: str):
        """
        Ajouter un token à la liste noire.
        
        Args:
            token_address: Adresse du token à blacklister
        """
        token_address = token_address.lower()
        if token_address not in self.blacklisted_tokens:
            self.blacklisted_tokens.append(token_address)
            logger.info(f"Token added to blacklist: {token_address}")
    
    def remove_from_blacklist(self, token_address: str):
        """
        Retirer un token de la liste noire.
        
        Args:
            token_address: Adresse du token à retirer de la liste noire
        """
        token_address = token_address.lower()
        if token_address in self.blacklisted_tokens:
            self.blacklisted_tokens.remove(token_address)
            logger.info(f"Token removed from blacklist: {token_address}")
    
    def get_detected_pairs(self) -> Dict[str, Dict[str, Any]]:
        """
        Obtenir la liste des paires détectées.
        
        Returns:
            Dict[str, Dict[str, Any]]: Dictionnaire des paires détectées
        """
        return self.detected_pairs
    
    def get_pending_transactions(self) -> Dict[str, Dict[str, Any]]:
        """
        Obtenir la liste des transactions en attente.
        
        Returns:
            Dict[str, Dict[str, Any]]: Dictionnaire des transactions en attente
        """
        return self.pending_txs

# Exemple d'utilisation
async def main():
    """Fonction principale pour tester le module."""
    # Créer une instance du module de sniping
    sniping = MempoolSniping()
    
    # Définir les callbacks
    def on_pair_detected(pair_info):
        print(f"New pair detected: {pair_info['token_address']}")
    
    def on_transaction_executed(tx_info):
        print(f"Transaction executed: {tx_info['tx_hash']}, Status: {tx_info['status']}")
    
    sniping.set_on_pair_detected_callback(on_pair_detected)
    sniping.set_on_transaction_executed_callback(on_transaction_executed)
    
    # Démarrer la surveillance
    try:
        await sniping.start_monitoring()
    except KeyboardInterrupt:
        sniping.stop_monitoring()
        print("Monitoring stopped")

if __name__ == "__main__":
    asyncio.run(main()) 