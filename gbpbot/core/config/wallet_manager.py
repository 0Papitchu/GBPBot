#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Module de gestion des wallets du GBPBot

Ce module gère les wallets et leurs clés privées de manière sécurisée.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from eth_account import Account
from solana.keypair import Keypair
from base58 import b58encode, b58decode

class WalletManager:
    """Gestionnaire de wallets du GBPBot"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialise le gestionnaire de wallets
        
        Args:
            config (Dict[str, Any]): Configuration du bot
        """
        self.config = config
        self.wallets = self._load_wallets()
        
        # Vérifier les wallets au démarrage
        for blockchain, wallet in self.wallets.items():
            if not self._validate_wallet(blockchain, wallet):
                raise ValueError(f"Wallet invalide pour {blockchain}")
    
    def _load_wallets(self) -> Dict[str, Dict[str, str]]:
        """
        Charge les wallets depuis le fichier de configuration
        
        Returns:
            Dict[str, Dict[str, str]]: Wallets chargés
        """
        wallets = self.config.get("wallets", {})
        
        # Vérifier que les wallets sont présents
        if not wallets:
            raise ValueError("Aucun wallet configuré")
            
        return wallets
    
    def _save_wallets(self) -> bool:
        """
        Sauvegarde les wallets dans le fichier de configuration
        
        Returns:
            bool: True si la sauvegarde a réussi, False sinon
        """
        try:
            # Mettre à jour la section wallets
            self.config["wallets"] = self.wallets
            
            # Sauvegarder dans le fichier
            wallets_file = self.config["security"]["wallets_file"]
            with open(wallets_file, "w") as f:
                json.dump(self.wallets, f, indent=4)
                
            return True
        except Exception as e:
            print(f"Erreur lors de la sauvegarde des wallets: {str(e)}")
            return False
    
    def _validate_wallet(self, blockchain: str, wallet: Dict[str, str]) -> bool:
        """
        Valide un wallet pour une blockchain donnée
        
        Args:
            blockchain (str): Nom de la blockchain
            wallet (Dict[str, str]): Données du wallet
            
        Returns:
            bool: True si le wallet est valide, False sinon
        """
        required_fields = ["address", "private_key"]
        
        # Vérifier les champs requis
        if not all(field in wallet for field in required_fields):
            print(f"Champs manquants dans le wallet {blockchain}")
            return False
        
        try:
            # Validation spécifique selon la blockchain
            if blockchain == "avalanche":
                # Vérifier le format de l'adresse Ethereum
                if not wallet["address"].startswith("0x"):
                    print(f"Format d'adresse invalide pour {blockchain}")
                    return False
                    
                # Vérifier la clé privée
                account = Account.from_key(wallet["private_key"])
                if account.address.lower() != wallet["address"].lower():
                    print(f"La clé privée ne correspond pas à l'adresse pour {blockchain}")
                    return False
                    
            elif blockchain == "solana":
                try:
                    # Vérifier le format de la clé privée Solana
                    private_key = b58decode(wallet["private_key"])
                    keypair = Keypair.from_secret_key(private_key)
                    
                    # Vérifier que l'adresse correspond
                    if str(keypair.public_key) != wallet["address"]:
                        print(f"La clé privée ne correspond pas à l'adresse pour {blockchain}")
                        return False
                except:
                    print(f"Clé privée invalide pour {blockchain}")
                    return False
            else:
                print(f"Blockchain non supportée: {blockchain}")
                return False
                
            return True
        except Exception as e:
            print(f"Erreur lors de la validation du wallet {blockchain}: {str(e)}")
            return False
    
    def get_wallet(self, blockchain: str) -> Optional[Dict[str, str]]:
        """
        Retourne un wallet pour une blockchain donnée
        
        Args:
            blockchain (str): Nom de la blockchain
            
        Returns:
            Optional[Dict[str, str]]: Wallet ou None si non trouvé
        """
        return self.wallets.get(blockchain)
    
    def add_wallet(self, blockchain: str, wallet: Dict[str, str]) -> bool:
        """
        Ajoute ou met à jour un wallet
        
        Args:
            blockchain (str): Nom de la blockchain
            wallet (Dict[str, str]): Données du wallet
            
        Returns:
            bool: True si l'ajout a réussi, False sinon
        """
        # Valider le wallet
        if not self._validate_wallet(blockchain, wallet):
            return False
        
        # Ajouter le wallet
        self.wallets[blockchain] = wallet
        
        # Sauvegarder les modifications
        return self._save_wallets()
    
    def remove_wallet(self, blockchain: str) -> bool:
        """
        Supprime un wallet
        
        Args:
            blockchain (str): Nom de la blockchain
            
        Returns:
            bool: True si la suppression a réussi, False sinon
        """
        if blockchain not in self.wallets:
            return False
            
        # Supprimer le wallet
        del self.wallets[blockchain]
        
        # Sauvegarder les modifications
        return self._save_wallets()
    
    def list_wallets(self) -> List[str]:
        """
        Liste les blockchains pour lesquelles des wallets sont configurés
        
        Returns:
            List[str]: Liste des blockchains
        """
        return list(self.wallets.keys())
    
    def get_balance(self, blockchain: str) -> Optional[float]:
        """
        Retourne le solde d'un wallet
        
        Args:
            blockchain (str): Nom de la blockchain
            
        Returns:
            Optional[float]: Solde en tokens natifs ou None si erreur
        """
        wallet = self.get_wallet(blockchain)
        if not wallet:
            return None
            
        try:
            if blockchain == "avalanche":
                # TODO: Implémenter la récupération du solde AVAX
                pass
            elif blockchain == "solana":
                # TODO: Implémenter la récupération du solde SOL
                pass
                
            return None
        except Exception as e:
            print(f"Erreur lors de la récupération du solde pour {blockchain}: {str(e)}")
            return None 