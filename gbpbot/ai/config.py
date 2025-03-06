#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gestionnaire de Configuration pour l'IA
=======================================

Ce module gère la configuration sécurisée des clés API et autres paramètres
sensibles pour les intégrations d'IA dans GBPBot.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union

# Configurer le logger
logger = logging.getLogger("gbpbot.ai.config")

class AIConfig:
    """
    Gestionnaire de configuration pour les intégrations d'IA.
    
    Cette classe gère le stockage sécurisé et l'accès aux clés API
    et autres paramètres de configuration pour les modèles d'IA.
    """
    
    # Chemin par défaut pour le fichier de configuration
    DEFAULT_CONFIG_PATH = os.path.join(
        os.path.expanduser("~"), 
        ".gbpbot", 
        "ai_config.json"
    )
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialise le gestionnaire de configuration.
        
        Args:
            config_path: Chemin vers le fichier de configuration (optionnel)
        """
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
        self.config = {}
        self._load_config()
    
    def _load_config(self) -> None:
        """
        Charge la configuration depuis le fichier.
        Si le fichier n'existe pas, crée une configuration vide.
        """
        try:
            config_file = Path(self.config_path)
            
            # Créer le répertoire parent si nécessaire
            if not config_file.parent.exists():
                config_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Charger la configuration si le fichier existe
            if config_file.exists():
                with open(self.config_path, "r") as f:
                    self.config = json.load(f)
                logger.info(f"Configuration chargée depuis {self.config_path}")
            else:
                # Créer un fichier de configuration vide
                self.config = {
                    "openai": {
                        "api_key": "",
                        "model": "gpt-3.5-turbo",
                        "max_tokens": 1000,
                        "temperature": 0.7
                    },
                    "llama": {
                        "model_path": "",
                        "quantization": "4bit",
                        "context_length": 2048,
                        "temperature": 0.7
                    }
                }
                self._save_config()
                logger.info(f"Nouveau fichier de configuration créé à {self.config_path}")
        
        except Exception as e:
            logger.error(f"Erreur lors du chargement de la configuration: {e}")
            # Créer une configuration par défaut en cas d'erreur
            self.config = {
                "openai": {
                    "api_key": "",
                    "model": "gpt-3.5-turbo"
                },
                "llama": {
                    "model_path": ""
                }
            }
    
    def _save_config(self) -> None:
        """
        Sauvegarde la configuration dans le fichier.
        """
        try:
            with open(self.config_path, "w") as f:
                json.dump(self.config, f, indent=4)
            
            # Restreindre les permissions du fichier (lecture/écriture uniquement pour l'utilisateur)
            os.chmod(self.config_path, 0o600)
            logger.info(f"Configuration sauvegardée dans {self.config_path}")
        
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde de la configuration: {e}")
    
    def get(self, provider: str, key: str, default: Any = None) -> Any:
        """
        Récupère une valeur de configuration.
        
        Args:
            provider: Le fournisseur d'IA (ex: 'openai', 'llama')
            key: La clé de configuration à récupérer
            default: Valeur par défaut si la clé n'existe pas
            
        Returns:
            La valeur de configuration ou la valeur par défaut
        """
        if provider in self.config and key in self.config[provider]:
            return self.config[provider][key]
        
        # Vérifier si la valeur est dans les variables d'environnement
        env_key = f"GBPBOT_{provider.upper()}_{key.upper()}"
        env_value = os.environ.get(env_key)
        if env_value:
            return env_value
        
        return default
    
    def set(self, provider: str, key: str, value: Any) -> None:
        """
        Définit une valeur de configuration.
        
        Args:
            provider: Le fournisseur d'IA (ex: 'openai', 'llama')
            key: La clé de configuration à définir
            value: La valeur à stocker
        """
        if provider not in self.config:
            self.config[provider] = {}
        
        self.config[provider][key] = value
        self._save_config()
    
    def set_openai_api_key(self, api_key: str) -> None:
        """
        Définit la clé API OpenAI.
        
        Args:
            api_key: La clé API OpenAI
        """
        self.set("openai", "api_key", api_key)
    
    def get_openai_api_key(self) -> Optional[str]:
        """
        Récupère la clé API OpenAI.
        
        Returns:
            La clé API OpenAI ou None si non définie
        """
        # Vérifier d'abord dans les variables d'environnement
        env_key = os.environ.get("OPENAI_API_KEY")
        if env_key:
            return env_key
        
        return self.get("openai", "api_key")
    
    def set_llama_model_path(self, model_path: str) -> None:
        """
        Définit le chemin vers le modèle LLaMA.
        
        Args:
            model_path: Le chemin vers le modèle LLaMA
        """
        self.set("llama", "model_path", model_path)
    
    def get_llama_model_path(self) -> Optional[str]:
        """
        Récupère le chemin vers le modèle LLaMA.
        
        Returns:
            Le chemin vers le modèle LLaMA ou None si non défini
        """
        return self.get("llama", "model_path")
    
    def get_provider_config(self, provider: str) -> Dict[str, Any]:
        """
        Récupère toute la configuration d'un fournisseur.
        
        Args:
            provider: Le fournisseur d'IA (ex: 'openai', 'llama')
            
        Returns:
            Un dictionnaire contenant la configuration du fournisseur
        """
        if provider in self.config:
            # Créer une copie pour éviter la modification directe
            config = dict(self.config[provider])
            
            # Vérifier les variables d'environnement pour chaque clé
            for key in config:
                env_key = f"GBPBOT_{provider.upper()}_{key.upper()}"
                env_value = os.environ.get(env_key)
                if env_value:
                    config[key] = env_value
            
            # Cas spécial pour OpenAI API key
            if provider == "openai" and "api_key" in config:
                env_key = os.environ.get("OPENAI_API_KEY")
                if env_key:
                    config["api_key"] = env_key
            
            return config
        
        return {}

# Instance globale du gestionnaire de configuration
_config_instance = None

def get_ai_config(config_path: Optional[str] = None) -> AIConfig:
    """
    Récupère l'instance globale du gestionnaire de configuration.
    
    Args:
        config_path: Chemin vers le fichier de configuration (optionnel)
        
    Returns:
        L'instance du gestionnaire de configuration
    """
    global _config_instance
    
    if _config_instance is None:
        _config_instance = AIConfig(config_path)
    
    return _config_instance 