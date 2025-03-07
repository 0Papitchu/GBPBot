#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Module de gestion des secrets pour GBPBot.

Ce module fournit une interface sécurisée pour stocker et récupérer des données sensibles
comme les clés privées, les tokens API, etc. Les données sont chiffrées au repos
à l'aide de la bibliothèque Fernet (chiffrement symétrique).

Exemple d'utilisation:
    secrets_manager = SecretsManager()
    secrets_manager.store_secret("PRIVATE_KEY", "0x123...")
    private_key = secrets_manager.get_secret("PRIVATE_KEY")
"""

import os
import json
import base64
import logging
import getpass
from typing import Dict, Any, Optional, Union
from pathlib import Path
from datetime import datetime

# Importer le module de cryptographie avec gestion des exceptions
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    CRYPTO_AVAILABLE = True
except ImportError:
    logging.warning("Module cryptography non disponible. Fonctionnalités de chiffrement désactivées.")
    CRYPTO_AVAILABLE = False

# Configuration du logger
logger = logging.getLogger("gbpbot.security")

class SecretsManager:
    """
    Gestionnaire de secrets pour stocker et récupérer des données sensibles de façon sécurisée.
    
    Utilise le chiffrement Fernet pour protéger les données au repos. La clé est dérivée
    d'un mot de passe maître ou générée aléatoirement et stockée localement.
    """
    
    def __init__(self, config_dir: Optional[Union[str, Path]] = None, 
                 master_password: Optional[str] = None,
                 auto_load: bool = True):
        """
        Initialise le gestionnaire de secrets.
        
        Args:
            config_dir: Répertoire de configuration (défaut: ~/.gbpbot)
            master_password: Mot de passe maître pour dériver la clé de chiffrement 
                             (défaut: générer/charger une clé aléatoire)
            auto_load: Charger automatiquement les secrets au démarrage
        """
        # Définir le répertoire de configuration
        if config_dir is None:
            self.config_dir = Path.home() / ".gbpbot" / "secure"
        else:
            self.config_dir = Path(config_dir)
        
        # Chemins des fichiers
        self.key_file = self.config_dir / "crypto.key"
        self.secrets_file = self.config_dir / "secrets.enc"
        self.salt_file = self.config_dir / "salt.bin"
        
        # Création du répertoire de configuration si nécessaire
        self._ensure_config_dir()
        
        # Initialisations
        self.cipher = None
        self.secrets_cache = {}
        self.master_password = master_password
        
        # Vérifier si la cryptographie est disponible
        if not CRYPTO_AVAILABLE:
            logger.warning("Fonctionnalités de chiffrement désactivées. Les secrets seront stockés en texte brut.")
            return
        
        # Initialiser le chiffrement
        self._initialize_encryption()
        
        # Charger les secrets existants
        if auto_load:
            self.load_secrets()
    
    def _ensure_config_dir(self) -> None:
        """Crée le répertoire de configuration s'il n'existe pas."""
        os.makedirs(self.config_dir, exist_ok=True)
        
        # Sécuriser le répertoire (uniquement sur UNIX)
        if os.name == "posix":
            try:
                os.chmod(self.config_dir, 0o700)  # Permissions: rwx------
            except Exception as e:
                logger.warning(f"Impossible de sécuriser le répertoire de configuration: {e}")
    
    def _initialize_encryption(self) -> None:
        """Initialise le chiffrement en chargeant ou générant une clé."""
        if not CRYPTO_AVAILABLE:
            return
            
        try:
            # Si un mot de passe maître est fourni, l'utiliser pour dériver la clé
            if self.master_password:
                self._derive_key_from_password()
            else:
                # Sinon, charger ou générer une clé aléatoire
                self._load_or_create_key()
                
            logger.debug("Chiffrement initialisé avec succès")
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du chiffrement: {e}")
            raise
    
    def _derive_key_from_password(self) -> None:
        """Dérive une clé de chiffrement à partir du mot de passe maître."""
        # Charger ou générer un sel
        if self.salt_file.exists():
            with open(self.salt_file, "rb") as f:
                salt = f.read()
        else:
            salt = os.urandom(16)
            with open(self.salt_file, "wb") as f:
                f.write(salt)
        
        # Dériver la clé à partir du mot de passe
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(self.master_password.encode()))
        self.cipher = Fernet(key)
    
    def _load_or_create_key(self) -> None:
        """Charge une clé existante ou en génère une nouvelle."""
        if self.key_file.exists():
            try:
                with open(self.key_file, "rb") as f:
                    key = f.read()
                self.cipher = Fernet(key)
                logger.debug(f"Clé de chiffrement chargée depuis: {self.key_file}")
            except Exception as e:
                logger.error(f"Erreur lors du chargement de la clé: {e}")
                # Si la clé est corrompue, en générer une nouvelle
                self._generate_new_key()
        else:
            self._generate_new_key()
    
    def _generate_new_key(self) -> None:
        """Génère une nouvelle clé de chiffrement."""
        try:
            key = Fernet.generate_key()
            with open(self.key_file, "wb") as f:
                f.write(key)
            
            # Sécuriser le fichier de clé (uniquement sur UNIX)
            if os.name == "posix":
                os.chmod(self.key_file, 0o600)  # Permissions: rw-------
                
            self.cipher = Fernet(key)
            logger.info(f"Nouvelle clé de chiffrement générée: {self.key_file}")
        except Exception as e:
            logger.error(f"Erreur lors de la génération de la clé: {e}")
            raise
    
    def load_secrets(self) -> Dict[str, Any]:
        """
        Charge les secrets depuis le fichier chiffré.
        
        Returns:
            Dictionnaire contenant les secrets
        """
        if not self.secrets_file.exists():
            logger.debug("Aucun fichier de secrets trouvé")
            self.secrets_cache = {}
            return {}
            
        try:
            with open(self.secrets_file, "rb") as f:
                encrypted_data = f.read()
                
            if not CRYPTO_AVAILABLE or not self.cipher:
                # Si le chiffrement n'est pas disponible, essayer de lire en JSON texte brut
                try:
                    self.secrets_cache = json.loads(encrypted_data.decode('utf-8'))
                    return self.secrets_cache
                except:
                    logger.error("Impossible de lire le fichier de secrets")
                    return {}
            
            # Déchiffrer les données
            decrypted_data = self.cipher.decrypt(encrypted_data).decode('utf-8')
            self.secrets_cache = json.loads(decrypted_data)
            logger.debug(f"Secrets chargés depuis: {self.secrets_file}")
            return self.secrets_cache
            
        except Exception as e:
            logger.error(f"Erreur lors du chargement des secrets: {e}")
            return {}
    
    def store_secrets(self, secrets_dict: Dict[str, Any]) -> bool:
        """
        Stocke un dictionnaire de secrets dans le fichier chiffré.
        
        Args:
            secrets_dict: Dictionnaire contenant les secrets à stocker
            
        Returns:
            True si l'opération a réussi, False sinon
        """
        try:
            # Mise à jour du cache
            self.secrets_cache = secrets_dict
            
            # Si le chiffrement n'est pas disponible, stocker en texte brut (dangereux)
            if not CRYPTO_AVAILABLE or not self.cipher:
                logger.warning("Stockage des secrets en texte brut (non sécurisé)")
                with open(self.secrets_file, "w") as f:
                    json.dump(secrets_dict, f, indent=2)
                return True
            
            # Chiffrer et stocker
            encrypted_data = self.cipher.encrypt(json.dumps(secrets_dict).encode('utf-8'))
            
            # Créer une sauvegarde du fichier existant s'il existe
            if self.secrets_file.exists():
                backup_file = self.config_dir / f"secrets.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}"
                try:
                    import shutil
                    shutil.copy2(self.secrets_file, backup_file)
                    logger.debug(f"Backup créé: {backup_file}")
                except Exception as e:
                    logger.warning(f"Impossible de créer une sauvegarde: {e}")
            
            # Écrire les données chiffrées
            with open(self.secrets_file, "wb") as f:
                f.write(encrypted_data)
                
            # Sécuriser le fichier (uniquement sur UNIX)
            if os.name == "posix":
                os.chmod(self.secrets_file, 0o600)  # Permissions: rw-------
                
            logger.info(f"Secrets stockés avec succès dans: {self.secrets_file}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors du stockage des secrets: {e}")
            return False
    
    def store_secret(self, key: str, value: Any) -> bool:
        """
        Stocke une valeur secrète individuelle.
        
        Args:
            key: Clé identifiant le secret
            value: Valeur à stocker
            
        Returns:
            True si l'opération a réussi, False sinon
        """
        # Charger les secrets existants si le cache est vide
        if not self.secrets_cache:
            self.load_secrets()
            
        # Mettre à jour la valeur
        self.secrets_cache[key] = value
        
        # Sauvegarder tous les secrets
        return self.store_secrets(self.secrets_cache)
    
    def get_secret(self, key: str, default: Any = None) -> Any:
        """
        Récupère un secret par sa clé.
        
        Args:
            key: Clé identifiant le secret
            default: Valeur par défaut si la clé n'existe pas
            
        Returns:
            La valeur du secret ou la valeur par défaut
        """
        # Charger les secrets si nécessaire
        if not self.secrets_cache:
            self.load_secrets()
            
        return self.secrets_cache.get(key, default)
    
    def delete_secret(self, key: str) -> bool:
        """
        Supprime un secret.
        
        Args:
            key: Clé identifiant le secret à supprimer
            
        Returns:
            True si l'opération a réussi, False sinon
        """
        # Charger les secrets si nécessaire
        if not self.secrets_cache:
            self.load_secrets()
            
        # Vérifier si la clé existe
        if key not in self.secrets_cache:
            logger.warning(f"Tentative de suppression d'un secret inexistant: {key}")
            return False
            
        # Supprimer la clé
        del self.secrets_cache[key]
        
        # Sauvegarder les changements
        return self.store_secrets(self.secrets_cache)
    
    def clear_all_secrets(self) -> bool:
        """
        Supprime tous les secrets.
        
        Returns:
            True si l'opération a réussi, False sinon
        """
        confirmation = input("⚠️ ATTENTION: Cette action va supprimer tous vos secrets. Tapez 'CONFIRMER' pour continuer: ")
        if confirmation != "CONFIRMER":
            logger.warning("Suppression des secrets annulée")
            return False
            
        self.secrets_cache = {}
        return self.store_secrets({})
    
    @staticmethod
    def ask_for_master_password() -> str:
        """
        Demande un mot de passe maître à l'utilisateur de façon sécurisée.
        
        Returns:
            Le mot de passe saisi
        """
        return getpass.getpass("Entrez le mot de passe maître: ")


# Test de fonctionnement si exécuté directement
if __name__ == "__main__":
    # Configuration du logging pour les tests
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    print("=== Test du gestionnaire de secrets GBPBot ===")
    
    # Utiliser un répertoire temporaire pour les tests
    import tempfile
    temp_dir = tempfile.mkdtemp()
    print(f"Utilisation du répertoire temporaire: {temp_dir}")
    
    # Créer un gestionnaire de secrets
    sm = SecretsManager(config_dir=temp_dir)
    
    # Tester le stockage de secrets
    print("\nTest de stockage de secrets...")
    secrets = {
        "PRIVATE_KEY": "0x123abc...",
        "API_KEY": "sk_test_1234567890",
        "TELEGRAM_TOKEN": "1234567890:ABCDEFGH...",
        "NUMBERS": [1, 2, 3, 4, 5],
        "CONFIG": {"max_gas": 100, "slippage": 0.5}
    }
    
    if sm.store_secrets(secrets):
        print("✅ Secrets stockés avec succès")
    else:
        print("❌ Échec du stockage des secrets")
    
    # Tester la récupération de secrets
    print("\nTest de récupération de secrets...")
    loaded_secrets = sm.load_secrets()
    
    if loaded_secrets == secrets:
        print("✅ Secrets récupérés avec succès")
    else:
        print("❌ Échec de la récupération des secrets")
        print(f"Attendu: {secrets}")
        print(f"Obtenu: {loaded_secrets}")
    
    # Tester la récupération individuelle
    print("\nTest de récupération individuelle...")
    api_key = sm.get_secret("API_KEY")
    if api_key == "sk_test_1234567890":
        print(f"✅ API_KEY récupérée avec succès: {api_key}")
    else:
        print(f"❌ Échec de la récupération de l'API_KEY: {api_key}")
    
    # Tester la mise à jour d'un secret
    print("\nTest de mise à jour d'un secret...")
    sm.store_secret("API_KEY", "sk_test_updated")
    updated_key = sm.get_secret("API_KEY")
    if updated_key == "sk_test_updated":
        print(f"✅ API_KEY mise à jour avec succès: {updated_key}")
    else:
        print(f"❌ Échec de la mise à jour de l'API_KEY: {updated_key}")
    
    # Tester la suppression d'un secret
    print("\nTest de suppression d'un secret...")
    if sm.delete_secret("NUMBERS"):
        print("✅ Secret supprimé avec succès")
        if "NUMBERS" not in sm.load_secrets():
            print("✅ Vérification réussie: le secret a bien été supprimé")
        else:
            print("❌ Le secret existe toujours après suppression")
    else:
        print("❌ Échec de la suppression du secret")
    
    # Nettoyage
    print("\nNettoyage du répertoire de test...")
    import shutil
    shutil.rmtree(temp_dir)
    print("✅ Test terminé") 