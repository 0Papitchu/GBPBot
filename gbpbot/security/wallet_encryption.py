#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Module de chiffrement des wallets pour GBPBot
=============================================

Ce module gère le chiffrement/déchiffrement sécurisé des clés privées 
de wallets pour éviter le stockage en clair sur le disque.

Il utilise la cryptographie symétrique avec dérivation de clé basée 
sur mot de passe (PBKDF2) et stocke les données en format JSON.
"""

import os
import json
import base64
import getpass
import logging
import hashlib
from typing import Dict, List, Any, Optional, Union, Tuple
from pathlib import Path

# Importer le module de compatibilité qui gère toutes les dépendances optionnelles
try:
    from gbpbot.security.encryption_compat import (
        has_cryptography, has_secrets, has_prometheus, has_pandas,
        Fernet, hashes, PBKDF2HMAC, secrets, prometheus_client, pd
    )
except ImportError:
    # Fallback basique si le module de compatibilité n'est pas disponible
    has_cryptography = False
    has_secrets = False
    has_prometheus = False
    has_pandas = False
    
    # Tenter d'importer les modules essentiels directement
    try:
        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        has_cryptography = True
    except ImportError:
        # Définir des classes stub minimales si nécessaire
        class Fernet:
            def __init__(self, key):
                self.key = key
            def encrypt(self, data):
                raise NotImplementedError("Cryptography non disponible")
            def decrypt(self, data):
                raise NotImplementedError("Cryptography non disponible")
        
        class hashes:
            class SHA256:
                pass
        
        class PBKDF2HMAC:
            def __init__(self, algorithm, length, salt, iterations):
                self.algorithm = algorithm
                self.length = length
                self.salt = salt
                self.iterations = iterations
            def derive(self, data):
                # Fallback simple avec hashlib
                import hashlib
                return hashlib.pbkdf2_hmac('sha256', data, self.salt, self.iterations, self.length)
    
    # Fallback pour secrets
    try:
        import secrets
        has_secrets = True
    except ImportError:
        secrets = None
    
    # Stubs pour pandas et prometheus (non essentiels)
    pd = None
    prometheus_client = None
    
# Configuration du logger
logger = logging.getLogger("gbpbot.security.wallet_encryption")

class WalletEncryption:
    """
    Classe pour gérer le chiffrement et déchiffrement des données de wallets.
    Utilise une approche basée sur mot de passe pour protéger les clés privées.
    """
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialise le gestionnaire de chiffrement des wallets.
        
        Args:
            config_dir: Chemin vers le répertoire de configuration (optionnel)
        """
        # Chemin du répertoire de configuration
        if config_dir:
            self.config_dir = Path(config_dir)
        else:
            # Utiliser le répertoire par défaut
            script_dir = Path(__file__).parent.parent.parent
            self.config_dir = script_dir / "config"
        
        # Chemin du fichier de wallets
        self.wallets_path = self.config_dir / "wallets.json"
        
        # Chemin du fichier de wallets chiffré
        self.encrypted_wallets_path = self.config_dir / "wallets.encrypted.json"
        
        # Chemin du fichier de sel
        self.salt_path = self.config_dir / ".wallet_salt"
        
        # S'assurer que le répertoire existe
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Mot de passe en mémoire (optionnel)
        self._password = None
        
        # Indicateur de disponibilité du chiffrement
        self.encryption_available = has_cryptography
        
        logger.info(f"Module de chiffrement de wallets initialisé, cryptography {'disponible' if has_cryptography else 'non disponible'}")
    
    def set_master_password(self, password: Optional[str] = None) -> bool:
        """
        Définit le mot de passe maître utilisé pour le chiffrement/déchiffrement.
        
        Args:
            password: Mot de passe à utiliser (si None, demande interactivement)
            
        Returns:
            bool: True si le mot de passe a été défini, False sinon
        """
        if password is None:
            # Demander le mot de passe de manière interactive
            try:
                password = getpass.getpass("Mot de passe maître pour le chiffrement des wallets: ")
                password_confirm = getpass.getpass("Confirmer le mot de passe: ")
                
                if password != password_confirm:
                    logger.error("Les mots de passe ne correspondent pas")
                    return False
                
                if not password:
                    logger.error("Le mot de passe ne peut pas être vide")
                    return False
            except Exception as e:
                logger.error(f"Erreur lors de la saisie du mot de passe: {str(e)}")
                return False
        
        # Stocker le mot de passe en mémoire
        self._password = password
        
        return True
    
    def _get_password(self) -> Optional[str]:
        """
        Récupère le mot de passe stocké ou le demande à l'utilisateur.
        
        Returns:
            str: Mot de passe ou None si non disponible
        """
        if self._password:
            return self._password
        
        # Demander le mot de passe
        try:
            self._password = getpass.getpass("Mot de passe pour accéder aux wallets: ")
            if not self._password:
                logger.error("Mot de passe vide")
                return None
            return self._password
        except Exception as e:
            logger.error(f"Erreur lors de la saisie du mot de passe: {str(e)}")
            return None
    
    def _generate_key(self, password: str, salt: Optional[bytes] = None) -> Tuple[bytes, bytes]:
        """
        Génère une clé de chiffrement à partir d'un mot de passe en utilisant PBKDF2.
        
        Args:
            password: Mot de passe utilisateur
            salt: Sel pour la dérivation de clé (généré si None)
            
        Returns:
            Tuple[bytes, bytes]: (clé de chiffrement, sel utilisé)
        """
        if not has_cryptography:
            # Méthode alternative si cryptography n'est pas disponible
            if salt is None:
                if has_secrets:
                    salt = secrets.token_bytes(16)
                else:
                    # Fallback si secrets n'est pas disponible
                    salt = os.urandom(16)
            
            # Utiliser PBKDF2 via hashlib (moins sécurisé, mais disponible)
            derived_key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000, 32)
            return derived_key, salt
        
        # Méthode recommandée avec cryptography
        if salt is None:
            salt = os.urandom(16)
            
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key, salt
    
    def _save_salt(self, salt: bytes) -> bool:
        """
        Sauvegarde le sel sur le disque de manière sécurisée.
        
        Args:
            salt: Sel à sauvegarder
            
        Returns:
            bool: True si le sel a été sauvegardé avec succès, False sinon
        """
        try:
            # Encodage base64 pour le stockage
            salt_b64 = base64.b64encode(salt).decode('utf-8')
            
            # Sauvegarder avec des permissions restreintes
            with open(self.salt_path, 'w') as f:
                f.write(salt_b64)
            
            # Définir les permissions (600 - lecture/écriture uniquement pour le propriétaire)
            try:
                os.chmod(self.salt_path, 0o600)
            except Exception as e:
                logger.warning(f"Impossible de définir les permissions sur le fichier de sel: {str(e)}")
            
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde du sel: {str(e)}")
            return False
    
    def _load_salt(self) -> Optional[bytes]:
        """
        Charge le sel depuis le disque.
        
        Returns:
            bytes: Sel chargé ou None si non disponible
        """
        if not self.salt_path.exists():
            logger.warning("Fichier de sel non trouvé")
            return None
        
        try:
            with open(self.salt_path, 'r') as f:
                salt_b64 = f.read().strip()
            
            return base64.b64decode(salt_b64)
        except Exception as e:
            logger.error(f"Erreur lors du chargement du sel: {str(e)}")
            return None
    
    def encrypt_wallets(self, wallets: List[Dict[str, Any]], password: Optional[str] = None) -> bool:
        """
        Chiffre une liste de wallets avec le mot de passe spécifié.
        
        Args:
            wallets: Liste des wallets à chiffrer
            password: Mot de passe de chiffrement (si None, utilise celui en mémoire ou le demande)
            
        Returns:
            bool: True si les wallets ont été chiffrés et sauvegardés avec succès
        """
        if not has_cryptography:
            logger.warning("Le module cryptography n'est pas disponible, chiffrement limité")
        
        # Obtenir le mot de passe
        password_to_use = password or self._get_password()
        if not password_to_use:
            return False
        
        try:
            # Générer une clé à partir du mot de passe
            key, salt = self._generate_key(password_to_use)
            
            # Sauvegarder le sel
            self._save_salt(salt)
            
            # Préparer les wallets pour le chiffrement
            # Pour chaque wallet, chiffrer uniquement la clé privée
            encrypted_wallets = []
            
            for wallet in wallets:
                # Créer une copie du wallet
                wallet_copy = wallet.copy()
                
                # Chiffrer la clé privée si elle existe
                if "private_key" in wallet_copy and wallet_copy["private_key"]:
                    private_key = wallet_copy["private_key"]
                    
                    if has_cryptography:
                        # Chiffrement avec Fernet
                        f = Fernet(key)
                        encrypted_key = f.encrypt(private_key.encode()).decode()
                    else:
                        # Méthode alternative (moins sécurisée)
                        # XOR simple avec dérivation de clé (uniquement pour compatibilité)
                        derived_key = hashlib.sha256((password_to_use + wallet_copy.get("address", "")).encode()).digest()
                        xor_bytes = bytes(a ^ b for a, b in zip(private_key.encode(), derived_key * (len(private_key) // len(derived_key) + 1)))
                        encrypted_key = base64.b64encode(xor_bytes).decode()
                    
                    wallet_copy["private_key"] = encrypted_key
                    wallet_copy["encrypted"] = True
                
                encrypted_wallets.append(wallet_copy)
            
            # Sauvegarder les wallets chiffrés
            wallet_data = {
                "wallets": encrypted_wallets,
                "encrypted": True,
                "encryption_version": "1.0",
                "encryption_method": "fernet" if has_cryptography else "xor"
            }
            
            with open(self.encrypted_wallets_path, 'w') as f:
                json.dump(wallet_data, f, indent=4)
            
            # Définir les permissions (600 - lecture/écriture uniquement pour le propriétaire)
            try:
                os.chmod(self.encrypted_wallets_path, 0o600)
            except Exception as e:
                logger.warning(f"Impossible de définir les permissions sur le fichier de wallets chiffrés: {str(e)}")
            
            logger.info(f"Wallets chiffrés et sauvegardés dans {self.encrypted_wallets_path}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors du chiffrement des wallets: {str(e)}")
            return False
    
    def decrypt_wallets(self, password: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        """
        Déchiffre les wallets avec le mot de passe spécifié.
        
        Args:
            password: Mot de passe de déchiffrement (si None, utilise celui en mémoire ou le demande)
            
        Returns:
            List[Dict[str, Any]]: Liste des wallets déchiffrés ou None en cas d'erreur
        """
        if not self.encrypted_wallets_path.exists():
            logger.error("Fichier de wallets chiffrés non trouvé")
            return None
        
        # Obtenir le mot de passe
        password_to_use = password or self._get_password()
        if not password_to_use:
            return None
        
        # Charger le sel
        salt = self._load_salt()
        if not salt:
            logger.error("Impossible de charger le sel de chiffrement")
            return None
        
        try:
            # Charger les wallets chiffrés
            with open(self.encrypted_wallets_path, 'r') as f:
                wallet_data = json.load(f)
            
            # Vérifier si les wallets sont chiffrés
            if not wallet_data.get("encrypted", False):
                logger.warning("Les wallets ne semblent pas être chiffrés")
                return wallet_data.get("wallets", [])
            
            # Obtenir la méthode de chiffrement
            encryption_method = wallet_data.get("encryption_method", "fernet")
            encrypted_wallets = wallet_data.get("wallets", [])
            
            # Générer la clé à partir du mot de passe et du sel
            key, _ = self._generate_key(password_to_use, salt)
            
            # Déchiffrer les wallets
            decrypted_wallets = []
            
            for wallet in encrypted_wallets:
                # Créer une copie du wallet
                wallet_copy = wallet.copy()
                
                # Déchiffrer la clé privée si elle est chiffrée
                if "private_key" in wallet_copy and wallet_copy.get("encrypted", False):
                    encrypted_key = wallet_copy["private_key"]
                    
                    try:
                        if encryption_method == "fernet" and has_cryptography:
                            # Déchiffrement avec Fernet
                            f = Fernet(key)
                            decrypted_key = f.decrypt(encrypted_key.encode()).decode()
                        else:
                            # Méthode alternative (si fernet n'est pas disponible ou méthode XOR utilisée)
                            derived_key = hashlib.sha256((password_to_use + wallet_copy.get("address", "")).encode()).digest()
                            xor_bytes = base64.b64decode(encrypted_key)
                            decrypted_key_bytes = bytes(a ^ b for a, b in zip(xor_bytes, derived_key * (len(xor_bytes) // len(derived_key) + 1)))
                            decrypted_key = decrypted_key_bytes.decode()
                        
                        wallet_copy["private_key"] = decrypted_key
                        wallet_copy.pop("encrypted", None)
                    except Exception as e:
                        logger.error(f"Erreur lors du déchiffrement du wallet {wallet_copy.get('address')}: {str(e)}")
                        # Garder la clé chiffrée en cas d'erreur
                
                decrypted_wallets.append(wallet_copy)
            
            logger.info(f"{len(decrypted_wallets)} wallets déchiffrés avec succès")
            return decrypted_wallets
            
        except Exception as e:
            logger.error(f"Erreur lors du déchiffrement des wallets: {str(e)}")
            return None
    
    def encrypt_wallet_file(self, wallet_file: Optional[str] = None, password: Optional[str] = None) -> bool:
        """
        Chiffre un fichier de wallets existant.
        
        Args:
            wallet_file: Chemin du fichier de wallets (si None, utilise le chemin par défaut)
            password: Mot de passe de chiffrement (si None, utilise celui en mémoire ou le demande)
            
        Returns:
            bool: True si le fichier a été chiffré avec succès
        """
        # Définir le chemin du fichier de wallets
        wallet_path = Path(wallet_file) if wallet_file else self.wallets_path
        
        if not wallet_path.exists():
            logger.error(f"Fichier de wallets {wallet_path} non trouvé")
            return False
        
        try:
            # Charger les wallets
            with open(wallet_path, 'r') as f:
                wallets = json.load(f)
            
            # Vérifier le format
            if not isinstance(wallets, list):
                logger.error("Format de fichier de wallets invalide")
                return False
            
            # Chiffrer les wallets
            success = self.encrypt_wallets(wallets, password)
            
            if success:
                logger.info(f"Fichier {wallet_path} chiffré avec succès")
                
                # Créer une sauvegarde du fichier original
                backup_path = wallet_path.with_suffix(f"{wallet_path.suffix}.bak")
                try:
                    with open(wallet_path, 'r') as fsrc, open(backup_path, 'w') as fdst:
                        fdst.write(fsrc.read())
                    logger.info(f"Sauvegarde créée: {backup_path}")
                except Exception as e:
                    logger.warning(f"Impossible de créer une sauvegarde: {str(e)}")
            
            return success
            
        except Exception as e:
            logger.error(f"Erreur lors du chiffrement du fichier de wallets: {str(e)}")
            return False
    
    def decrypt_to_file(self, output_file: Optional[str] = None, password: Optional[str] = None) -> bool:
        """
        Déchiffre les wallets et les sauvegarde dans un fichier.
        ATTENTION: Cette fonction écrit les clés privées en clair sur le disque.
        
        Args:
            output_file: Chemin du fichier de sortie (si None, utilise le chemin par défaut)
            password: Mot de passe de déchiffrement (si None, utilise celui en mémoire ou le demande)
            
        Returns:
            bool: True si les wallets ont été déchiffrés et sauvegardés avec succès
        """
        # Avertissement de sécurité
        logger.warning("Déchiffrement des wallets vers un fichier - les clés privées seront en clair sur le disque!")
        
        # Définir le chemin du fichier de sortie
        output_path = Path(output_file) if output_file else self.wallets_path
        
        # Déchiffrer les wallets
        wallets = self.decrypt_wallets(password)
        if not wallets:
            return False
        
        try:
            # Sauvegarder les wallets déchiffrés
            with open(output_path, 'w') as f:
                json.dump(wallets, f, indent=4)
            
            # Définir les permissions (600 - lecture/écriture uniquement pour le propriétaire)
            try:
                os.chmod(output_path, 0o600)
            except Exception as e:
                logger.warning(f"Impossible de définir les permissions sur le fichier de wallets: {str(e)}")
            
            logger.info(f"Wallets déchiffrés et sauvegardés dans {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des wallets déchiffrés: {str(e)}")
            return False
    
    def test_password(self, password: str) -> bool:
        """
        Teste si un mot de passe peut déchiffrer les wallets.
        
        Args:
            password: Mot de passe à tester
            
        Returns:
            bool: True si le mot de passe est correct
        """
        if not self.encrypted_wallets_path.exists() or not self.salt_path.exists():
            logger.error("Fichiers de chiffrement non trouvés")
            return False
        
        # Sauvegarder le mot de passe actuel
        current_password = self._password
        
        try:
            # Définir le mot de passe à tester
            self._password = password
            
            # Essayer de déchiffrer les wallets
            wallets = self.decrypt_wallets(password)
            
            # Vérifier si le déchiffrement a réussi
            if wallets:
                return True
            
            return False
            
        except Exception:
            return False
            
        finally:
            # Restaurer le mot de passe
            self._password = current_password


def encrypt_wallet_file(wallet_file: str, password: Optional[str] = None, config_dir: Optional[str] = None) -> bool:
    """
    Fonction utilitaire pour chiffrer un fichier de wallets.
    
    Args:
        wallet_file: Chemin du fichier de wallets
        password: Mot de passe de chiffrement (si None, demande interactivement)
        config_dir: Répertoire de configuration (optionnel)
        
    Returns:
        bool: True si le fichier a été chiffré avec succès
    """
    encryption = WalletEncryption(config_dir)
    return encryption.encrypt_wallet_file(wallet_file, password)


def decrypt_wallet_file(encrypted_file: str, output_file: str, password: Optional[str] = None, config_dir: Optional[str] = None) -> bool:
    """
    Fonction utilitaire pour déchiffrer un fichier de wallets.
    
    Args:
        encrypted_file: Chemin du fichier de wallets chiffrés
        output_file: Chemin du fichier de sortie
        password: Mot de passe de déchiffrement (si None, demande interactivement)
        config_dir: Répertoire de configuration (optionnel)
        
    Returns:
        bool: True si le fichier a été déchiffré avec succès
    """
    encryption = WalletEncryption(config_dir)
    encryption.encrypted_wallets_path = Path(encrypted_file)
    return encryption.decrypt_to_file(output_file, password)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Utilitaire de chiffrement des wallets GBPBot")
    parser.add_argument("action", choices=["encrypt", "decrypt", "test"],
                        help="Action à effectuer (encrypt, decrypt ou test)")
    parser.add_argument("--file", "-f", 
                        help="Chemin du fichier de wallets (pour 'encrypt') ou du fichier chiffré (pour 'decrypt')")
    parser.add_argument("--output", "-o", 
                        help="Chemin du fichier de sortie (pour 'decrypt')")
    parser.add_argument("--config", "-c", 
                        help="Répertoire de configuration")
    parser.add_argument("--password", "-p", 
                        help="Mot de passe (non recommandé, préférez la saisie interactive)")
    
    args = parser.parse_args()
    
    encryption = WalletEncryption(args.config)
    
    if args.action == "encrypt":
        if not encryption.encrypt_wallet_file(args.file, args.password):
            exit(1)
    
    elif args.action == "decrypt":
        if not encryption.decrypt_to_file(args.output, args.password):
            exit(1)
    
    elif args.action == "test":
        password = args.password or getpass.getpass("Mot de passe à tester: ")
        if encryption.test_password(password):
            print("Mot de passe correct")
        else:
            print("Mot de passe incorrect")
            exit(1) 