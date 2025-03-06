"""
Module de gestion de la configuration pour GBPBot
================================================

Ce module gère la configuration de GBPBot, y compris le chargement
des paramètres depuis les fichiers de configuration et les variables d'environnement.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union, List

# Configurer le logging
logger = logging.getLogger(__name__)

# Chemins de configuration par défaut
DEFAULT_CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG_FILE = "optimized_config.json"
DEFAULT_CONFIG_PATH = os.path.join(DEFAULT_CONFIG_DIR, DEFAULT_CONFIG_FILE)

# Configuration par défaut
DEFAULT_CONFIG = {
    "version": "1.0.0",
    "system_specs": {},
    "blockchain": {
        "solana": {
            "rpc_endpoints": [
                {
                    "name": "mainnet",
                    "url": "https://api.mainnet-beta.solana.com",
                    "priority": 1
                }
            ]
        }
    },
    "dex": {
        "preferred_dex": [
            {
                "name": "jupiter",
                "priority": 1
            },
            {
                "name": "raydium",
                "priority": 2
            }
        ]
    },
    "resource_limits": {
        "max_threads": 4,
        "max_ram_usage_percent": 75,
        "cache_size_mb": 200,
        "log_level": "INFO"
    },
    "performance_mode": "balanced"
}


class ConfigManager:
    """Gestionnaire de configuration pour GBPBot"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialise le gestionnaire de configuration
        
        Args:
            config_path: Chemin vers le fichier de configuration (optionnel)
        """
        self.config_path = config_path or DEFAULT_CONFIG_PATH
        self.config = DEFAULT_CONFIG.copy()
        self.load_config()
        
    def load_config(self) -> bool:
        """
        Charge la configuration depuis le fichier
        
        Returns:
            bool: True si la configuration a été chargée avec succès, False sinon
        """
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    loaded_config = json.load(f)
                    
                # Mettre à jour la configuration avec les valeurs chargées
                self._update_nested_dict(self.config, loaded_config)
                logger.info(f"Configuration chargée depuis {self.config_path}")
                return True
            else:
                logger.warning(f"Fichier de configuration {self.config_path} introuvable, utilisation des valeurs par défaut")
                return False
        except Exception as e:
            logger.error(f"Erreur lors du chargement de la configuration: {str(e)}")
            return False
            
    def save_config(self, config_path: Optional[str] = None) -> bool:
        """
        Sauvegarde la configuration dans un fichier
        
        Args:
            config_path: Chemin où sauvegarder la configuration (optionnel)
            
        Returns:
            bool: True si la configuration a été sauvegardée avec succès, False sinon
        """
        path = config_path or self.config_path
        
        try:
            # Créer le répertoire parent s'il n'existe pas
            os.makedirs(os.path.dirname(path), exist_ok=True)
            
            with open(path, 'w') as f:
                json.dump(self.config, f, indent=4)
                
            logger.info(f"Configuration sauvegardée dans {path}")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde de la configuration: {str(e)}")
            return False
            
    def get(self, key: str, default: Any = None) -> Any:
        """
        Récupère une valeur de configuration
        
        Args:
            key: Chemin de la clé, séparé par des points (par exemple "blockchain.solana.rpc_endpoints")
            default: Valeur par défaut à retourner si la clé n'existe pas
            
        Returns:
            La valeur de configuration ou la valeur par défaut
        """
        keys = key.split('.')
        value = self.config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
            
    def set(self, key: str, value: Any) -> None:
        """
        Définit une valeur de configuration
        
        Args:
            key: Chemin de la clé, séparé par des points
            value: Valeur à définir
        """
        keys = key.split('.')
        config = self.config
        
        # Naviguer jusqu'au dernier niveau
        for k in keys[:-1]:
            if k not in config or not isinstance(config[k], dict):
                config[k] = {}
            config = config[k]
            
        # Définir la valeur
        config[keys[-1]] = value
        
    def get_rpc_endpoints(self, blockchain: str = "solana") -> List[Dict[str, Any]]:
        """
        Récupère les endpoints RPC pour une blockchain donnée
        
        Args:
            blockchain: Nom de la blockchain
            
        Returns:
            Liste des endpoints RPC
        """
        return self.get(f"blockchain.{blockchain}.rpc_endpoints", [])
        
    def get_preferred_dex(self) -> List[Dict[str, Any]]:
        """
        Récupère la liste des DEX préférés
        
        Returns:
            Liste des DEX préférés
        """
        return self.get("dex.preferred_dex", [])
        
    def get_performance_mode(self) -> str:
        """
        Récupère le mode de performance
        
        Returns:
            Mode de performance (high, balanced, economy, auto)
        """
        return self.get("performance_mode", "auto")
        
    def get_resource_limits(self) -> Dict[str, Any]:
        """
        Récupère les limites de ressources
        
        Returns:
            Limites de ressources
        """
        return self.get("resource_limits", {})
        
    def _update_nested_dict(self, d: Dict[str, Any], u: Dict[str, Any]) -> Dict[str, Any]:
        """
        Met à jour un dictionnaire imbriqué
        
        Args:
            d: Dictionnaire à mettre à jour
            u: Dictionnaire avec les nouvelles valeurs
            
        Returns:
            Dictionnaire mis à jour
        """
        for k, v in u.items():
            if isinstance(v, dict) and k in d and isinstance(d[k], dict):
                d[k] = self._update_nested_dict(d[k], v)
            else:
                d[k] = v
        return d


# Créer une instance globale du gestionnaire de configuration
config_manager = ConfigManager()

# Exporter des fonctions utilitaires pour faciliter l'accès
def get(key: str, default: Any = None) -> Any:
    """Récupère une valeur de configuration"""
    return config_manager.get(key, default)

def set(key: str, value: Any) -> None:
    """Définit une valeur de configuration"""
    config_manager.set(key, value)

def save(config_path: Optional[str] = None) -> bool:
    """Sauvegarde la configuration"""
    return config_manager.save_config(config_path)

def load(config_path: Optional[str] = None) -> bool:
    """Charge la configuration"""
    if config_path:
        config_manager.config_path = config_path
    return config_manager.load_config() 