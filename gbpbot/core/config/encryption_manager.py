#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Module de gestion du chiffrement du GBPBot

Ce module gère le chiffrement et déchiffrement des données sensibles
comme les clés API et les wallets.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from base64 import b64encode, b64decode

class EncryptionManager:
    """Gestionnaire de chiffrement du GBPBot"""
    
    def __init__(self, security_config: Dict[str, Any]):
        """
        Initialise le gestionnaire de chiffrement
        
        Args:
            security_config (Dict[str, Any]): Configuration de sécurité
        """
        self.security_config = security_config
        self.encryption_key = self._load_encryption_key()
        self.fernet = Fernet(self.encryption_key)
    
    def _load_encryption_key(self) -> bytes:
        """
        Charge ou génère la clé de chiffrement
        
        Returns:
            bytes: Clé de chiffrement
        """
        key_file = self.security_config["encryption_key_file"]
        
        # Créer le dossier des clés si nécessaire
        os.makedirs(os.path.dirname(key_file), exist_ok=True)
        
        # Si le fichier de clé existe, le charger
        if os.path.exists(key_file):
            with open(key_file, "rb") as f:
                return b64decode(f.read())
        
        # Sinon, générer une nouvelle clé
        key = Fernet.generate_key()
        
        # Sauvegarder la clé
        with open(key_file, "wb") as f:
            f.write(b64encode(key))
        
        return key
    
    def _derive_key(self, password: str, salt: bytes = None) -> bytes:
        """
        Dérive une clé de chiffrement à partir d'un mot de passe
        
        Args:
            password (str): Mot de passe
            salt (bytes, optional): Sel pour le KDF. Defaults to None.
            
        Returns:
            bytes: Clé dérivée
        """
        if salt is None:
            salt = os.urandom(16)
            
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        
        key = b64encode(kdf.derive(password.encode()))
        return key
    
    def encrypt_data(self, data: str) -> str:
        """
        Chiffre des données
        
        Args:
            data (str): Données à chiffrer
            
        Returns:
            str: Données chiffrées en base64
        """
        if not self.security_config["encryption_enabled"]:
            return data
            
        encrypted = self.fernet.encrypt(data.encode())
        return b64encode(encrypted).decode()
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """
        Déchiffre des données
        
        Args:
            encrypted_data (str): Données chiffrées en base64
            
        Returns:
            str: Données déchiffrées
        """
        if not self.security_config["encryption_enabled"]:
            return encrypted_data
            
        decrypted = self.fernet.decrypt(b64decode(encrypted_data))
        return decrypted.decode()
    
    def encrypt_file(self, input_file: str, output_file: str) -> bool:
        """
        Chiffre un fichier
        
        Args:
            input_file (str): Chemin du fichier à chiffrer
            output_file (str): Chemin du fichier chiffré
            
        Returns:
            bool: True si le chiffrement a réussi, False sinon
        """
        try:
            with open(input_file, "r") as f:
                data = f.read()
            
            encrypted = self.encrypt_data(data)
            
            with open(output_file, "w") as f:
                f.write(encrypted)
                
            return True
        except Exception as e:
            print(f"Erreur lors du chiffrement du fichier: {str(e)}")
            return False
    
    def decrypt_file(self, input_file: str, output_file: str) -> bool:
        """
        Déchiffre un fichier
        
        Args:
            input_file (str): Chemin du fichier chiffré
            output_file (str): Chemin du fichier déchiffré
            
        Returns:
            bool: True si le déchiffrement a réussi, False sinon
        """
        try:
            with open(input_file, "r") as f:
                encrypted = f.read()
            
            decrypted = self.decrypt_data(encrypted)
            
            with open(output_file, "w") as f:
                f.write(decrypted)
                
            return True
        except Exception as e:
            print(f"Erreur lors du déchiffrement du fichier: {str(e)}")
            return False
    
    def change_encryption_key(self, new_password: str) -> bool:
        """
        Change la clé de chiffrement
        
        Args:
            new_password (str): Nouveau mot de passe pour la clé
            
        Returns:
            bool: True si le changement a réussi, False sinon
        """
        try:
            # Générer une nouvelle clé
            salt = os.urandom(16)
            new_key = self._derive_key(new_password, salt)
            
            # Sauvegarder la nouvelle clé
            key_file = self.security_config["encryption_key_file"]
            with open(key_file, "wb") as f:
                f.write(b64encode(new_key))
            
            # Mettre à jour la clé en mémoire
            self.encryption_key = new_key
            self.fernet = Fernet(self.encryption_key)
            
            return True
        except Exception as e:
            print(f"Erreur lors du changement de clé: {str(e)}")
            return False 