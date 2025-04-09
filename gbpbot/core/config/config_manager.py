#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Module de gestion de la configuration du GBPBot

Ce module gère le chargement, la validation et la sauvegarde
des paramètres de configuration du GBPBot.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional

class ConfigManager:
    """Gestionnaire de configuration du GBPBot"""
    
    def __init__(self, config_file: str = "config.json"):
        """
        Initialise le gestionnaire de configuration
        
        Args:
            config_file (str): Chemin vers le fichier de configuration
        """
        self.config_file = config_file
        self.config = self._load_config_file()
        
        if not self._validate_config():
            raise ValueError("Configuration invalide")
    
    def _load_config_file(self) -> Dict[str, Any]:
        """
        Charge la configuration depuis le fichier
        
        Returns:
            Dict[str, Any]: Configuration chargée
        """
        if not os.path.exists(self.config_file):
            raise FileNotFoundError(f"Fichier de configuration non trouvé: {self.config_file}")
            
        with open(self.config_file, "r") as f:
            config = json.load(f)
            
        return config
    
    def _save_config_file(self) -> bool:
        """
        Sauvegarde la configuration dans le fichier
        
        Returns:
            bool: True si la sauvegarde a réussi, False sinon
        """
        try:
            with open(self.config_file, "w") as f:
                json.dump(self.config, f, indent=4)
            return True
        except Exception as e:
            print(f"Erreur lors de la sauvegarde de la configuration: {str(e)}")
            return False
    
    def _validate_config(self) -> bool:
        """
        Valide la configuration
        
        Returns:
            bool: True si la configuration est valide, False sinon
        """
        required_sections = ["general", "security", "blockchain", "api_keys", "wallets", "trading"]
        
        # Vérifier la présence des sections requises
        for section in required_sections:
            if section not in self.config:
                print(f"Section manquante dans la configuration: {section}")
                return False
        
        # Vérifier les paramètres de la section general
        general = self.config["general"]
        if not all(key in general for key in ["environment", "log_level", "data_dir"]):
            print("Paramètres manquants dans la section general")
            return False
        
        # Vérifier les paramètres de la section security
        security = self.config["security"]
        if not all(key in security for key in ["encryption_enabled", "encryption_key_file"]):
            print("Paramètres manquants dans la section security")
            return False
        
        # Vérifier les paramètres de la section blockchain
        blockchain = self.config["blockchain"]
        for chain in ["avalanche", "solana"]:
            if chain not in blockchain:
                print(f"Configuration manquante pour la blockchain {chain}")
                return False
            chain_config = blockchain[chain]
            if not all(key in chain_config for key in ["rpc_url", "websocket"]):
                print(f"Paramètres manquants pour la blockchain {chain}")
                return False
        
        # Vérifier les paramètres de trading
        trading = self.config["trading"]
        if not all(key in trading for key in ["max_slippage", "gas_multiplier"]):
            print("Paramètres manquants dans la section trading")
            return False
        
        return True
    
    def get_config(self) -> Dict[str, Any]:
        """
        Retourne la configuration complète
        
        Returns:
            Dict[str, Any]: Configuration complète
        """
        return self.config
    
    def get_section(self, section: str) -> Optional[Dict[str, Any]]:
        """
        Retourne une section spécifique de la configuration
        
        Args:
            section (str): Nom de la section
            
        Returns:
            Optional[Dict[str, Any]]: Section de configuration ou None si non trouvée
        """
        return self.config.get(section)
    
    def update_config(self, updates: Dict[str, Any]) -> bool:
        """
        Met à jour la configuration avec de nouvelles valeurs
        
        Args:
            updates (Dict[str, Any]): Nouvelles valeurs à mettre à jour
            
        Returns:
            bool: True si la mise à jour a réussi, False sinon
        """
        # Mettre à jour la configuration
        for section, values in updates.items():
            if section in self.config:
                if isinstance(values, dict):
                    self.config[section].update(values)
                else:
                    self.config[section] = values
        
        # Valider la nouvelle configuration
        if not self._validate_config():
            return False
        
        # Sauvegarder la configuration
        return self._save_config_file()
    
    def validate_config(self) -> bool:
        """
        Valide la configuration actuelle
        
        Returns:
            bool: True si la configuration est valide, False sinon
        """
        return self._validate_config() 