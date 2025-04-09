#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module d'initialisation pour GBPBot
====================================

Ce module est responsable de la vérification et de l'initialisation des composants
critiques avant le démarrage du GBPBot. Il s'assure que toutes les dépendances,
configurations et connexions sont correctement établies.
"""

import os
import sys
import json
import logging
import importlib
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any, Union

# Ajouter le répertoire racine au chemin d'importation
ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

# Import des modules GBPBot
try:
    from gbpbot.core.config import ConfigManager
    from gbpbot.core.exceptions import InitializationError, ConfigurationError
except ImportError as e:
    print(f"Erreur critique lors de l'importation des modules de base: {str(e)}")
    print("Veuillez vérifier que vous exécutez ce script depuis le dossier racine du projet.")
    sys.exit(1)

# Configuration du logger
logger = logging.getLogger("gbpbot.initialization")

class BotInitializer:
    """
    Classe responsable de l'initialisation du GBPBot.
    
    Cette classe vérifie les configurations, les connexions et les dépendances
    avant de lancer le bot. Elle s'assure que tout est correctement configuré
    pour un fonctionnement optimal.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialise le vérificateur de configuration.
        
        Args:
            config_path: Chemin vers le fichier de configuration principal (optionnel)
        """
        self.root_dir = ROOT_DIR
        self.config_manager = ConfigManager(config_path)
        self.initialization_status = {
            "config": False,
            "blockchains": {},
            "wallets": {},
            "api_keys": {},
            "dependencies": {},
            "overall": False
        }
    
    def initialize(self) -> bool:
        """
        Exécute toutes les vérifications d'initialisation.
        
        Returns:
            bool: True si l'initialisation est réussie, False sinon
        """
        try:
            logger.info("Démarrage de l'initialisation du GBPBot...")
            
            # Vérification des configurations
            self._check_configuration()
            
            # Vérification des connexions blockchain
            self._check_blockchain_connections()
            
            # Vérification des wallets
            self._check_wallets()
            
            # Vérification des clés API
            self._check_api_keys()
            
            # Vérification des dépendances optionnelles
            self._check_optional_dependencies()
            
            # Finalisation
            self._finalize_initialization()
            
            return self.initialization_status["overall"]
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation: {str(e)}")
            self.initialization_status["overall"] = False
            return False
    
    def _check_configuration(self) -> None:
        """Vérifie la configuration du bot"""
        logger.info("Vérification de la configuration...")
        
        try:
            # Charger la configuration
            config = self.config_manager.get_config()
            
            # Vérifier les sections essentielles
            required_sections = ["general", "blockchains", "wallets", "modules"]
            missing_sections = [section for section in required_sections if section not in config]
            
            if missing_sections:
                raise ConfigurationError(f"Sections manquantes dans la configuration: {', '.join(missing_sections)}")
            
            # Vérifier les modes de fonctionnement
            if "general" in config and "mode" in config["general"]:
                valid_modes = ["production", "test", "simulation"]
                current_mode = config["general"]["mode"]
                
                if current_mode not in valid_modes:
                    logger.warning(f"Mode de fonctionnement non reconnu: {current_mode}. Utilisation du mode 'simulation'.")
            
            self.initialization_status["config"] = True
            logger.info("✅ Configuration vérifiée avec succès")
            
        except Exception as e:
            logger.error(f"Erreur lors de la vérification de la configuration: {str(e)}")
            self.initialization_status["config"] = False
            raise InitializationError(f"Échec de la vérification de la configuration: {str(e)}")
    
    def _check_blockchain_connections(self) -> None:
        """Vérifie les connexions aux blockchains configurées"""
        logger.info("Vérification des connexions blockchain...")
        
        try:
            config = self.config_manager.get_config()
            
            if "blockchains" not in config:
                logger.warning("Aucune blockchain configurée")
                return
            
            blockchains = config["blockchains"]
            
            for chain_name, chain_config in blockchains.items():
                if not chain_config.get("enabled", False):
                    logger.info(f"Blockchain {chain_name} désactivée, vérification ignorée")
                    self.initialization_status["blockchains"][chain_name] = "disabled"
                    continue
                
                rpc_url = chain_config.get("rpc_url")
                if not rpc_url:
                    logger.warning(f"URL RPC manquante pour {chain_name}")
                    self.initialization_status["blockchains"][chain_name] = "missing_rpc"
                    continue
                
                logger.info(f"Vérification de la connexion à {chain_name}...")
                
                # Vérifier la connexion (implementation spécifique à chaque blockchain)
                connection_status = self._test_blockchain_connection(chain_name, rpc_url)
                
                if connection_status:
                    logger.info(f"✅ Connexion à {chain_name} réussie")
                    self.initialization_status["blockchains"][chain_name] = "connected"
                else:
                    logger.warning(f"❌ Échec de connexion à {chain_name}")
                    self.initialization_status["blockchains"][chain_name] = "connection_failed"
            
            # Vérifier qu'au moins une blockchain est connectée
            connected_chains = [chain for chain, status in self.initialization_status["blockchains"].items() 
                              if status == "connected"]
            
            if not connected_chains:
                logger.error("Aucune blockchain connectée")
                raise InitializationError("Aucune blockchain connectée")
            
        except Exception as e:
            logger.error(f"Erreur lors de la vérification des connexions blockchain: {str(e)}")
            raise InitializationError(f"Échec de la vérification des connexions blockchain: {str(e)}")
    
    def _test_blockchain_connection(self, chain_name: str, rpc_url: str) -> bool:
        """
        Teste la connexion à une blockchain spécifique.
        
        Args:
            chain_name: Nom de la blockchain
            rpc_url: URL du point d'accès RPC
            
        Returns:
            bool: True si la connexion est réussie, False sinon
        """
        try:
            if chain_name.lower() in ["ethereum", "avalanche", "avax", "bsc", "polygon"]:
                # Test pour les chaînes compatibles EVM
                from web3 import Web3
                web3 = Web3(Web3.HTTPProvider(rpc_url))
                connected = web3.is_connected()
                if connected:
                    block_number = web3.eth.block_number
                    logger.info(f"Connecté à {chain_name} - Bloc actuel: {block_number}")
                return connected
                
            elif chain_name.lower() in ["solana", "sol"]:
                # Test pour Solana
                try:
                    import solana
                    from solana.rpc.api import Client
                    client = Client(rpc_url)
                    response = client.get_health()
                    if response["result"] == "ok":
                        logger.info(f"Connecté à {chain_name} - Statut: OK")
                        return True
                    else:
                        logger.warning(f"Problème de connexion à {chain_name} - Statut: {response.get('result', 'unknown')}")
                        return False
                except ImportError:
                    logger.warning("Module solana non disponible, impossible de vérifier la connexion")
                    return False
                    
            else:
                # Blockchain non supportée directement
                logger.warning(f"Méthode de vérification non disponible pour {chain_name}")
                # Tentative de connexion générique via HTTP
                import requests
                response = requests.post(
                    rpc_url, 
                    json={"jsonrpc":"2.0", "method":"web3_clientVersion", "params":[], "id":1},
                    timeout=5
                )
                return response.status_code == 200
                
        except Exception as e:
            logger.error(f"Erreur de connexion à {chain_name}: {str(e)}")
            return False
    
    def _check_wallets(self) -> None:
        """Vérifie les configurations de wallets"""
        logger.info("Vérification des wallets configurés...")
        
        try:
            config = self.config_manager.get_config()
            
            if "wallets" not in config:
                logger.warning("Aucun wallet configuré")
                return
            
            wallets = config["wallets"]
            
            for wallet_name, wallet_config in wallets.items():
                if not wallet_config.get("enabled", False):
                    logger.info(f"Wallet {wallet_name} désactivé, vérification ignorée")
                    self.initialization_status["wallets"][wallet_name] = "disabled"
                    continue
                
                # Vérifier les champs essentiels pour le wallet
                address = wallet_config.get("address")
                chain = wallet_config.get("blockchain")
                
                if not address:
                    logger.warning(f"Adresse manquante pour le wallet {wallet_name}")
                    self.initialization_status["wallets"][wallet_name] = "missing_address"
                    continue
                
                if not chain:
                    logger.warning(f"Blockchain non spécifiée pour le wallet {wallet_name}")
                    self.initialization_status["wallets"][wallet_name] = "missing_chain"
                    continue
                
                # Vérifier la validité de l'adresse
                if self._is_valid_wallet_address(address, chain):
                    logger.info(f"✅ Wallet {wallet_name} validé")
                    self.initialization_status["wallets"][wallet_name] = "valid"
                else:
                    logger.warning(f"❌ Format d'adresse invalide pour le wallet {wallet_name}")
                    self.initialization_status["wallets"][wallet_name] = "invalid_address"
            
            # Vérifier qu'au moins un wallet est valide
            valid_wallets = [wallet for wallet, status in self.initialization_status["wallets"].items() 
                           if status == "valid"]
            
            if not valid_wallets:
                logger.error("Aucun wallet valide configuré")
                raise InitializationError("Aucun wallet valide configuré")
            
        except Exception as e:
            logger.error(f"Erreur lors de la vérification des wallets: {str(e)}")
            raise InitializationError(f"Échec de la vérification des wallets: {str(e)}")
    
    def _is_valid_wallet_address(self, address: str, chain: str) -> bool:
        """
        Vérifie la validité d'une adresse de wallet pour une blockchain donnée.
        
        Args:
            address: Adresse du wallet
            chain: Nom de la blockchain
            
        Returns:
            bool: True si l'adresse est valide, False sinon
        """
        try:
            if chain.lower() in ["ethereum", "avalanche", "avax", "bsc", "polygon"]:
                # Validation pour les adresses EVM
                from web3 import Web3
                return Web3.is_address(address)
                
            elif chain.lower() in ["solana", "sol"]:
                # Validation pour Solana
                # Les adresses Solana font généralement 44 caractères et sont encodées en base58
                import base58
                try:
                    decoded = base58.b58decode(address)
                    return len(decoded) == 32  # Les clés publiques font 32 octets
                except:
                    return False
                    
            else:
                # Blockchain non supportée directement
                logger.warning(f"Méthode de validation d'adresse non disponible pour {chain}")
                return True  # Assume valid if we can't check
                
        except Exception as e:
            logger.error(f"Erreur lors de la validation de l'adresse: {str(e)}")
            return False
    
    def _check_api_keys(self) -> None:
        """Vérifie les clés API configurées"""
        logger.info("Vérification des clés API...")
        
        try:
            config = self.config_manager.get_config()
            
            # Vérifier les clés API pour les exchanges
            if "exchanges" in config:
                for exchange_name, exchange_config in config["exchanges"].items():
                    if not exchange_config.get("enabled", False):
                        logger.info(f"Exchange {exchange_name} désactivé, vérification ignorée")
                        self.initialization_status["api_keys"][exchange_name] = "disabled"
                        continue
                    
                    api_key = exchange_config.get("api_key")
                    api_secret = exchange_config.get("api_secret")
                    
                    if not api_key or not api_secret:
                        logger.warning(f"Clés API manquantes pour {exchange_name}")
                        self.initialization_status["api_keys"][exchange_name] = "missing_keys"
                        continue
                    
                    # Masquer partiellement les clés pour le logging
                    masked_key = api_key[:4] + '*' * (len(api_key) - 8) + api_key[-4:] if len(api_key) > 8 else "****"
                    masked_secret = api_secret[:4] + '*' * (len(api_secret) - 8) + api_secret[-4:] if len(api_secret) > 8 else "****"
                    
                    logger.info(f"Exchange {exchange_name} - API Key: {masked_key}, API Secret: {masked_secret}")
                    self.initialization_status["api_keys"][exchange_name] = "configured"
            
            # Vérifier d'autres services API (comme CoinGecko, etc.)
            if "services" in config:
                for service_name, service_config in config["services"].items():
                    if not service_config.get("enabled", False):
                        continue
                    
                    api_key = service_config.get("api_key")
                    
                    if not api_key:
                        logger.info(f"Service {service_name} configuré sans clé API (peut être normal pour certains services gratuits)")
                        self.initialization_status["api_keys"][service_name] = "no_key_required"
                    else:
                        masked_key = api_key[:4] + '*' * (len(api_key) - 8) + api_key[-4:] if len(api_key) > 8 else "****"
                        logger.info(f"Service {service_name} - API Key: {masked_key}")
                        self.initialization_status["api_keys"][service_name] = "configured"
            
            logger.info("✅ Vérification des clés API terminée")
            
        except Exception as e:
            logger.error(f"Erreur lors de la vérification des clés API: {str(e)}")
            # Ne pas lever d'exception, car les clés API peuvent ne pas être critiques
    
    def _check_optional_dependencies(self) -> None:
        """Vérifie les dépendances optionnelles qui améliorent les performances"""
        logger.info("Vérification des dépendances optionnelles...")
        
        # Liste des dépendances optionnelles à vérifier
        optional_deps = {
            "tensorflow": "Améliore les capacités d'IA/ML",
            "ccxt": "Permet l'intégration avec de nombreux exchanges",
            "numba": "Optimise les calculs intensifs",
            "ujson": "Améliore les performances de parsing JSON",
            "uvloop": "Optimise les performances asyncio",
            "aiohttp": "Améliore les performances HTTP asynchrones",
            "solana": "Support pour la blockchain Solana",
            "anchorpy": "Support pour les programmes Anchor sur Solana"
        }
        
        for package, description in optional_deps.items():
            try:
                # Tenter d'importer le module
                importlib.import_module(package)
                logger.info(f"✅ {package} est installé ({description})")
                self.initialization_status["dependencies"][package] = "installed"
            except ImportError:
                logger.info(f"⚠️ {package} n'est pas installé ({description})")
                self.initialization_status["dependencies"][package] = "missing"
    
    def _finalize_initialization(self) -> None:
        """Finalise l'initialisation et détermine le statut global"""
        logger.info("Finalisation de l'initialisation...")
        
        # Vérifier que les éléments critiques sont valides
        critical_elements = [
            self.initialization_status["config"],
            # Au moins une blockchain doit être connectée
            any(status == "connected" for status in self.initialization_status["blockchains"].values()),
            # Au moins un wallet doit être valide
            any(status == "valid" for status in self.initialization_status["wallets"].values())
        ]
        
        if all(critical_elements):
            logger.info("✅ Initialisation réussie! GBPBot est prêt à démarrer.")
            self.initialization_status["overall"] = True
        else:
            logger.error("❌ Initialisation échouée! Certains éléments critiques ne sont pas configurés correctement.")
            self.initialization_status["overall"] = False
    
    def get_status(self) -> Dict:
        """
        Retourne le statut complet de l'initialisation.
        
        Returns:
            Dict: Status d'initialisation complet
        """
        return self.initialization_status
    
    def print_status_report(self) -> None:
        """Affiche un rapport détaillé du statut d'initialisation"""
        print("\n" + "=" * 60)
        print("  RAPPORT D'INITIALISATION GBPBOT")
        print("=" * 60)
        
        # Statut global
        status_str = "✅ RÉUSSI" if self.initialization_status["overall"] else "❌ ÉCHOUÉ"
        print(f"\nStatut global: {status_str}")
        
        # Configuration
        config_status = "✅ Valide" if self.initialization_status["config"] else "❌ Invalide"
        print(f"\n📋 Configuration: {config_status}")
        
        # Blockchains
        print("\n⛓️ Connexions blockchain:")
        for chain, status in self.initialization_status["blockchains"].items():
            status_icon = "✅" if status == "connected" else "⚠️" if status == "disabled" else "❌"
            print(f"  - {chain}: {status_icon} {status}")
        
        # Wallets
        print("\n👛 Wallets:")
        for wallet, status in self.initialization_status["wallets"].items():
            status_icon = "✅" if status == "valid" else "⚠️" if status == "disabled" else "❌"
            print(f"  - {wallet}: {status_icon} {status}")
        
        # API Keys
        print("\n🔑 Clés API:")
        for service, status in self.initialization_status["api_keys"].items():
            status_icon = "✅" if status in ["configured", "no_key_required"] else "⚠️" if status == "disabled" else "❌"
            print(f"  - {service}: {status_icon} {status}")
        
        # Dépendances optionnelles
        print("\n📦 Dépendances optionnelles:")
        for package, status in self.initialization_status["dependencies"].items():
            status_icon = "✅" if status == "installed" else "⚠️"
            print(f"  - {package}: {status_icon} {status}")
        
        print("\n" + "=" * 60)
        
        # Recommandations si des problèmes sont détectés
        if not self.initialization_status["overall"]:
            print("\n⚠️ RECOMMANDATIONS:")
            
            if not self.initialization_status["config"]:
                print("  - Vérifiez le fichier de configuration pour vous assurer qu'il contient toutes les sections requises.")
            
            missing_connections = [chain for chain, status in self.initialization_status["blockchains"].items() 
                                if status == "connection_failed"]
            if missing_connections:
                print(f"  - Vérifiez les points d'accès RPC pour: {', '.join(missing_connections)}")
            
            invalid_wallets = [wallet for wallet, status in self.initialization_status["wallets"].items() 
                             if status in ["invalid_address", "missing_address", "missing_chain"]]
            if invalid_wallets:
                print(f"  - Vérifiez la configuration des wallets: {', '.join(invalid_wallets)}")
            
            print("\nConsultez les logs pour plus de détails.")
            print("=" * 60)


# Fonction d'initialisation principale
def initialize_bot(config_path: Optional[str] = None) -> Tuple[bool, Dict]:
    """
    Initialise le GBPBot avec vérification complète.
    
    Args:
        config_path: Chemin vers le fichier de configuration (optionnel)
        
    Returns:
        Tuple[bool, Dict]: Status d'initialisation (succès/échec) et détails du statut
    """
    initializer = BotInitializer(config_path)
    success = initializer.initialize()
    initializer.print_status_report()
    
    return success, initializer.get_status()


# Exécution directe du module
if __name__ == "__main__":
    # Configuration du logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialiser le bot
    success, status = initialize_bot()
    
    if not success:
        sys.exit(1) 