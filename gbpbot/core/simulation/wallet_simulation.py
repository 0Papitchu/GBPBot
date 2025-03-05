#!/usr/bin/env python3
"""
Module de simulation de portefeuille pour GBPBot
Fournit des portefeuilles simulés avec des soldes pour le mode simulation
"""

import random
import json
import os
from typing import Dict, List, Optional, Union, Any
from decimal import Decimal
from loguru import logger
from web3 import Web3
from gbpbot.config.config_manager import config_manager
from gbpbot.core.simulation import is_simulation_mode

class SimulatedWallet:
    """Portefeuille simulé avec des soldes pour différents tokens"""
    
    def __init__(self, initial_balances: Optional[Dict[str, Union[float, Decimal]]] = None):
        """
        Initialise un portefeuille simulé
        
        Args:
            initial_balances: Soldes initiaux des tokens (clé: symbole, valeur: solde)
        """
        self.balances = initial_balances or {
            "AVAX": 10.0,
            "WAVAX": 5.0,
            "USDC": 1000.0,
            "USDT": 1000.0,
            "WETH.e": 0.5,
            "BTC.b": 0.02,
            "JOE": 100.0,
            "PNG": 100.0
        }
        
        self.token_addresses = {}
        self._load_token_addresses()
        
        # Journaliser l'initialisation
        logger.info(f"Portefeuille simulé initialisé avec {len(self.balances)} tokens")
        for token, balance in self.balances.items():
            logger.debug(f"  - {token}: {balance}")
    
    def _load_token_addresses(self):
        """Charge les adresses des tokens depuis la configuration"""
        try:
            # Charger depuis la configuration
            config = config_manager.get_config("tokens")
            if config and isinstance(config, dict):
                for token, details in config.items():
                    if "address" in details:
                        self.token_addresses[token] = details["address"]
            
            # Ajouter des adresses par défaut si nécessaire
            if not self.token_addresses:
                self.token_addresses = {
                    "WAVAX": "0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7",
                    "USDC": "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E",
                    "USDT": "0x9702230A8Ea53601f5cD2dc00fDBc13d4dF4A8c7",
                    "WETH.e": "0x49D5c2BdFfac6CE2BFdB6640F4F80f226bc10bAB",
                    "BTC.b": "0x152b9d0FdC40C096757F570A51E494bd4b943E50",
                    "JOE": "0x6e84a6216eA6dACC71eE8E6b0a5B7322EEbC0fDd",
                    "PNG": "0x60781C2586D68229fde47564546784ab3fACA982"
                }
        except Exception as e:
            logger.warning(f"Erreur lors du chargement des adresses de tokens: {str(e)}")
            # Utiliser des valeurs par défaut
            self.token_addresses = {
                "WAVAX": "0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7",
                "USDC": "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E",
                "USDT": "0x9702230A8Ea53601f5cD2dc00fDBc13d4dF4A8c7",
                "WETH.e": "0x49D5c2BdFfac6CE2BFdB6640F4F80f226bc10bAB",
                "BTC.b": "0x152b9d0FdC40C096757F570A51E494bd4b943E50"
            }
    
    def get_balance(self, token_symbol: str) -> float:
        """
        Récupère le solde d'un token
        
        Args:
            token_symbol: Symbole du token
            
        Returns:
            float: Solde du token
        """
        return self.balances.get(token_symbol, 0.0)
    
    def get_balance_by_address(self, token_address: str) -> float:
        """
        Récupère le solde d'un token par son adresse
        
        Args:
            token_address: Adresse du token
            
        Returns:
            float: Solde du token
        """
        # Convertir l'adresse en format checksum pour les comparaisons
        try:
            checksum_address = Web3.to_checksum_address(token_address)
        except:
            # Si l'adresse n'est pas valide, continuer avec l'originale
            checksum_address = token_address
        
        # Chercher le symbole correspondant à l'adresse
        symbol = None
        for token, address in self.token_addresses.items():
            if address.lower() == token_address.lower():
                symbol = token
                break
        
        if symbol:
            return self.get_balance(symbol)
        else:
            # Si le token n'est pas trouvé, retourner 0
            return 0.0
    
    def update_balance(self, token_symbol: str, new_balance: float) -> None:
        """
        Met à jour le solde d'un token
        
        Args:
            token_symbol: Symbole du token
            new_balance: Nouveau solde
        """
        self.balances[token_symbol] = new_balance
        logger.debug(f"Solde de {token_symbol} mis à jour: {new_balance}")
    
    def add_to_balance(self, token_symbol: str, amount: float) -> None:
        """
        Ajoute un montant au solde d'un token
        
        Args:
            token_symbol: Symbole du token
            amount: Montant à ajouter
        """
        current_balance = self.balances.get(token_symbol, 0.0)
        self.balances[token_symbol] = current_balance + amount
        logger.debug(f"Ajout de {amount} au solde de {token_symbol}: nouveau solde = {self.balances[token_symbol]}")
    
    def subtract_from_balance(self, token_symbol: str, amount: float) -> bool:
        """
        Soustrait un montant du solde d'un token
        
        Args:
            token_symbol: Symbole du token
            amount: Montant à soustraire
            
        Returns:
            bool: True si la soustraction a réussi, False si le solde est insuffisant
        """
        current_balance = self.balances.get(token_symbol, 0.0)
        if current_balance < amount:
            logger.warning(f"Solde insuffisant de {token_symbol}: {current_balance} < {amount}")
            return False
        
        self.balances[token_symbol] = current_balance - amount
        logger.debug(f"Soustraction de {amount} du solde de {token_symbol}: nouveau solde = {self.balances[token_symbol]}")
        return True
    
    def swap_tokens(self, from_token: str, to_token: str, amount_from: float, amount_to: float) -> bool:
        """
        Simule un échange de tokens
        
        Args:
            from_token: Symbole du token source
            to_token: Symbole du token destination
            amount_from: Montant à échanger
            amount_to: Montant à recevoir
            
        Returns:
            bool: True si l'échange a réussi, False sinon
        """
        # Vérifier le solde du token source
        if not self.subtract_from_balance(from_token, amount_from):
            return False
        
        # Ajouter le token destination
        self.add_to_balance(to_token, amount_to)
        
        logger.info(f"Échange simulé: {amount_from} {from_token} → {amount_to} {to_token}")
        return True
    
    def get_all_balances(self) -> Dict[str, float]:
        """
        Récupère tous les soldes
        
        Returns:
            Dict[str, float]: Tous les soldes (clé: symbole, valeur: solde)
        """
        return self.balances.copy()
    
    def get_token_address(self, token_symbol: str) -> Optional[str]:
        """
        Récupère l'adresse d'un token par son symbole
        
        Args:
            token_symbol: Symbole du token
            
        Returns:
            Optional[str]: Adresse du token, ou None si non trouvé
        """
        return self.token_addresses.get(token_symbol)

class SimulatedWalletManager:
    """Gestionnaire de portefeuilles simulés"""
    
    _instance = None
    
    def __new__(cls):
        """Implémentation du pattern Singleton"""
        if cls._instance is None:
            cls._instance = super(SimulatedWalletManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialise le gestionnaire de portefeuilles simulés"""
        if not hasattr(self, 'initialized'):
            # Charger la configuration
            config = config_manager.get_config("simulation")
            wallet_config = config.get("wallet", {})
            
            # Créer le portefeuille par défaut
            initial_balances = wallet_config.get("initial_balance", None)
            self.default_wallet = SimulatedWallet(initial_balances)
            
            # Liste des portefeuilles avec leurs adresses
            self.wallets = {}
            
            # Marquer comme initialisé
            self.initialized = True
            logger.info("Gestionnaire de portefeuilles simulés initialisé")
    
    def get_wallet(self, address: Optional[str] = None) -> SimulatedWallet:
        """
        Récupère un portefeuille simulé par son adresse
        
        Args:
            address: Adresse du portefeuille (None pour le portefeuille par défaut)
            
        Returns:
            SimulatedWallet: Portefeuille simulé
        """
        if address is None:
            return self.default_wallet
        
        # Créer un nouveau portefeuille si nécessaire
        if address not in self.wallets:
            self.wallets[address] = SimulatedWallet()
        
        return self.wallets[address]
    
    def get_balance(self, token_symbol: str, address: Optional[str] = None) -> float:
        """
        Récupère le solde d'un token pour un portefeuille
        
        Args:
            token_symbol: Symbole du token
            address: Adresse du portefeuille (None pour le portefeuille par défaut)
            
        Returns:
            float: Solde du token
        """
        wallet = self.get_wallet(address)
        return wallet.get_balance(token_symbol)
    
    def get_balance_by_address(self, token_address: str, wallet_address: Optional[str] = None) -> float:
        """
        Récupère le solde d'un token par son adresse
        
        Args:
            token_address: Adresse du token
            wallet_address: Adresse du portefeuille (None pour le portefeuille par défaut)
            
        Returns:
            float: Solde du token
        """
        wallet = self.get_wallet(wallet_address)
        return wallet.get_balance_by_address(token_address)
    
    def update_balance(self, token_symbol: str, new_balance: float, address: Optional[str] = None) -> None:
        """
        Met à jour le solde d'un token pour un portefeuille
        
        Args:
            token_symbol: Symbole du token
            new_balance: Nouveau solde
            address: Adresse du portefeuille (None pour le portefeuille par défaut)
        """
        wallet = self.get_wallet(address)
        wallet.update_balance(token_symbol, new_balance)
    
    def get_token_address(self, token_symbol: str) -> Optional[str]:
        """
        Récupère l'adresse d'un token par son symbole
        
        Args:
            token_symbol: Symbole du token
            
        Returns:
            Optional[str]: Adresse du token, ou None si non trouvé
        """
        return self.default_wallet.get_token_address(token_symbol)

# Instance singleton
wallet_manager = SimulatedWalletManager() 