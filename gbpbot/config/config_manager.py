"""
Module de configuration centralisé pour GBPBot
Ce module gère toutes les configurations du bot de manière centralisée
"""

import os
import json
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from loguru import logger
from datetime import timedelta
import yaml
from gbpbot.config.default_config import DEFAULT_CONFIG

class ConfigManager:
    """
    Gestionnaire de configuration pour charger et gérer les configurations
    """
    
    _instance = None
    
    def __new__(cls):
        """Implémentation du pattern Singleton"""
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """
        Initialise le gestionnaire de configuration
        """
        if not hasattr(self, 'initialized'):
            # Chemins de configuration
            self.config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config")
            self.config_file = os.path.join(self.config_dir, "config.yaml")
            
            # Configuration actuelle
            self.config = self._load_config()
            
            # Marquer comme initialisé
            self.initialized = True
            logger.info("Gestionnaire de configuration initialisé")
    
    def _load_config(self) -> Dict[str, Any]:
        """
        Charge la configuration depuis le fichier de configuration
        
        Returns:
            Dict: Configuration chargée
        """
        # Vérifier si le répertoire de configuration existe
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)
            logger.info(f"Répertoire de configuration créé: {self.config_dir}")
        
        # Vérifier si le fichier de configuration existe
        if not os.path.exists(self.config_file):
            # Créer le fichier de configuration avec les valeurs par défaut
            with open(self.config_file, "w") as f:
                yaml.dump(DEFAULT_CONFIG, f, default_flow_style=False)
            
            logger.info(f"Fichier de configuration créé: {self.config_file}")
            return DEFAULT_CONFIG
        
        try:
            # Charger la configuration depuis le fichier
            with open(self.config_file, "r") as f:
                config = yaml.safe_load(f)
            
            # Fusionner avec la configuration par défaut pour s'assurer que toutes les clés existent
            merged_config = self._merge_configs(DEFAULT_CONFIG, config)
            
            logger.info(f"Configuration chargée depuis {self.config_file}")
            return merged_config
            
        except Exception as e:
            logger.error(f"Erreur lors du chargement de la configuration: {str(e)}")
            logger.warning("Utilisation de la configuration par défaut")
            return DEFAULT_CONFIG
    
    def _merge_configs(self, default_config: Dict[str, Any], user_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fusionne la configuration par défaut avec la configuration utilisateur
        
        Args:
            default_config: Configuration par défaut
            user_config: Configuration utilisateur
            
        Returns:
            Dict: Configuration fusionnée
        """
        merged = default_config.copy()
        
        # Parcourir la configuration utilisateur
        for key, value in user_config.items():
            # Si la clé existe dans la configuration par défaut et que les deux valeurs sont des dictionnaires
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                # Fusion récursive
                merged[key] = self._merge_configs(merged[key], value)
            else:
                # Sinon, utiliser la valeur de la configuration utilisateur
                merged[key] = value
        
        return merged
    
    def get_config(self, section: Optional[str] = None) -> Any:
        """
        Récupère la configuration ou une section spécifique
        
        Args:
            section: Section de configuration à récupérer (None pour toute la configuration)
            
        Returns:
            Any: Configuration ou section de configuration
        """
        if section is None:
            return self.config
        
        if section in self.config:
            return self.config[section]
        
        logger.warning(f"Section de configuration non trouvée: {section}")
        return {}
    
    def set_config(self, section: str, key: str, value: Any) -> None:
        """
        Modifie une valeur de configuration
        
        Args:
            section: Section de configuration
            key: Clé de configuration
            value: Nouvelle valeur
        """
        if section not in self.config:
            self.config[section] = {}
        
        self.config[section][key] = value
        
        # Sauvegarder la configuration
        self.save_config()
        
        logger.info(f"Configuration mise à jour: {section}.{key} = {value}")
    
    def save_config(self) -> None:
        """
        Sauvegarde la configuration dans le fichier de configuration
        """
        try:
            # Sauvegarder la configuration
            with open(self.config_file, "w") as f:
                yaml.dump(self.config, f, default_flow_style=False)
            
            logger.info(f"Configuration sauvegardée dans {self.config_file}")
            
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde de la configuration: {str(e)}")
    
    def reset_config(self, section: Optional[str] = None) -> None:
        """
        Réinitialise la configuration ou une section spécifique
        
        Args:
            section: Section de configuration à réinitialiser (None pour toute la configuration)
        """
        if section is None:
            # Réinitialiser toute la configuration
            self.config = DEFAULT_CONFIG.copy()
        elif section in self.config and section in DEFAULT_CONFIG:
            # Réinitialiser une section spécifique
            self.config[section] = DEFAULT_CONFIG[section].copy()
        else:
            logger.warning(f"Section de configuration non trouvée: {section}")
            return
        
        # Sauvegarder la configuration
        self.save_config()
        
        logger.info(f"Configuration réinitialisée: {section if section else 'toute la configuration'}")
    
    def get_env_var(self, name: str, default: Any = None) -> Any:
        """
        Récupère une variable d'environnement
        
        Args:
            name: Nom de la variable d'environnement
            default: Valeur par défaut si la variable n'existe pas
            
        Returns:
            Any: Valeur de la variable d'environnement
        """
        return os.environ.get(name, default)
    
    def load_env_vars(self) -> None:
        """
        Charge les variables d'environnement dans la configuration
        """
        # Charger les clés API des échanges
        binance_api_key = self.get_env_var("BINANCE_API_KEY")
        binance_api_secret = self.get_env_var("BINANCE_API_SECRET")
        
        if binance_api_key and binance_api_secret:
            self.config["exchanges"]["binance"]["api_key"] = binance_api_key
            self.config["exchanges"]["binance"]["api_secret"] = binance_api_secret
            self.config["exchanges"]["binance"]["enabled"] = True
            logger.info("Clés API Binance chargées depuis les variables d'environnement")
        
        kucoin_api_key = self.get_env_var("KUCOIN_API_KEY")
        kucoin_api_secret = self.get_env_var("KUCOIN_API_SECRET")
        kucoin_passphrase = self.get_env_var("KUCOIN_PASSPHRASE")
        
        if kucoin_api_key and kucoin_api_secret and kucoin_passphrase:
            self.config["exchanges"]["kucoin"]["api_key"] = kucoin_api_key
            self.config["exchanges"]["kucoin"]["api_secret"] = kucoin_api_secret
            self.config["exchanges"]["kucoin"]["passphrase"] = kucoin_passphrase
            self.config["exchanges"]["kucoin"]["enabled"] = True
            logger.info("Clés API KuCoin chargées depuis les variables d'environnement")
        
        # Charger les clés API des RPC privés
        ankr_api_key = self.get_env_var("ANKR_API_KEY")
        if ankr_api_key:
            # Ajouter un nœud RPC privé Ankr
            ankr_node = {
                "url": f"https://rpc.ankr.com/avalanche/{ankr_api_key}",
                "priority": 0,  # Priorité la plus élevée
                "weight": 15,
                "active": True
            }
            
            # Vérifier si le nœud existe déjà
            exists = False
            for node in self.config["rpc"]["nodes"]:
                if node["url"].startswith("https://rpc.ankr.com/avalanche/"):
                    node.update(ankr_node)
                    exists = True
                    break
            
            if not exists:
                self.config["rpc"]["nodes"].insert(0, ankr_node)
            
            logger.info("Clé API Ankr chargée depuis les variables d'environnement")
        
        getblock_api_key = self.get_env_var("GETBLOCK_API_KEY")
        if getblock_api_key:
            # Ajouter un nœud RPC privé GetBlock
            getblock_node = {
                "url": f"https://avax.getblock.io/{getblock_api_key}/mainnet",
                "priority": 0,  # Priorité la plus élevée
                "weight": 15,
                "active": True
            }
            
            # Vérifier si le nœud existe déjà
            exists = False
            for node in self.config["rpc"]["nodes"]:
                if node["url"].startswith("https://avax.getblock.io/"):
                    node.update(getblock_node)
                    exists = True
                    break
            
            if not exists:
                self.config["rpc"]["nodes"].insert(0, getblock_node)
            
            logger.info("Clé API GetBlock chargée depuis les variables d'environnement")
        
        # Charger d'autres variables d'environnement
        log_level = self.get_env_var("LOG_LEVEL")
        if log_level:
            self.config["general"]["log_level"] = log_level
            logger.info(f"Niveau de log configuré depuis les variables d'environnement: {log_level}")
        
        simulation_mode = self.get_env_var("SIMULATION_MODE")
        if simulation_mode is not None:
            self.config["general"]["simulation_mode"] = simulation_mode.lower() in ("true", "1", "yes")
            logger.info(f"Mode simulation configuré depuis les variables d'environnement: {self.config['general']['simulation_mode']}")
        
        testnet = self.get_env_var("TESTNET")
        if testnet is not None:
            self.config["general"]["testnet"] = testnet.lower() in ("true", "1", "yes")
            logger.info(f"Mode testnet configuré depuis les variables d'environnement: {self.config['general']['testnet']}")

# Créer une instance singleton
config_manager = ConfigManager() 