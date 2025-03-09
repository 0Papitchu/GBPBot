"""
Module de chargement sécurisé des wallets pour GBPBot

Ce module permet de charger les wallets de manière sécurisée en remplaçant
les variables d'environnement dans le fichier de configuration wallets.json
"""

import os
import json
import re
import logging
from typing import Dict, List, Any
from pathlib import Path

# Configurer le logger
logger = logging.getLogger("WalletLoader")

class WalletLoader:
    """
    Chargeur sécurisé de wallets pour GBPBot.
    Gère le remplacement des variables d'environnement par leurs valeurs réelles.
    """
    
    def __init__(self, wallets_path: str = "config/wallets.json"):
        """
        Initialise le chargeur de wallets.
        
        Args:
            wallets_path: Chemin vers le fichier de configuration des wallets
        """
        self.wallets_path = Path(wallets_path)
        self.wallets_config = None
        self.env_pattern = re.compile(r"\${([A-Za-z0-9_]+)}")
    
    def load_wallets(self) -> List[Dict[str, Any]]:
        """
        Charge les configurations de wallets en remplaçant les variables d'environnement.
        
        Returns:
            Liste des configurations de wallets avec les valeurs réelles
        """
        try:
            if not self.wallets_path.exists():
                logger.error(f"Fichier de configuration des wallets introuvable: {self.wallets_path}")
                return []
            
            # Charger le contenu du fichier
            with open(self.wallets_path, "r") as f:
                content = f.read()
            
            # Remplacer les variables d'environnement
            processed_content = self._replace_env_vars(content)
            
            # Charger le JSON traité
            wallets = json.loads(processed_content)
            
            # Valider les wallets
            validated_wallets = self._validate_wallets(wallets)
            
            logger.info(f"Chargé {len(validated_wallets)} wallets valides")
            return validated_wallets
            
        except Exception as e:
            logger.error(f"Erreur lors du chargement des wallets: {str(e)}")
            return []
    
    def _replace_env_vars(self, content: str) -> str:
        """
        Remplace les variables d'environnement par leurs valeurs réelles.
        
        Args:
            content: Contenu du fichier JSON avec variables d'environnement
            
        Returns:
            Contenu avec les variables remplacées par leurs valeurs
        """
        def replace_match(match):
            env_var = match.group(1)
            value = os.environ.get(env_var)
            if value is None:
                logger.warning(f"Variable d'environnement non définie: {env_var}")
                return f"UNDEFINED_{env_var}"
            return value
        
        return self.env_pattern.sub(replace_match, content)
    
    def _validate_wallets(self, wallets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Valide les wallets chargés et filtre ceux qui sont invalides.
        
        Args:
            wallets: Liste des wallets à valider
            
        Returns:
            Liste des wallets valides
        """
        valid_wallets = []
        
        for wallet in wallets:
            # Vérifier les champs obligatoires
            if not all(k in wallet for k in ["address", "private_key", "chain"]):
                logger.warning(f"Wallet ignoré: champs obligatoires manquants")
                continue
                
            # Vérifier que les valeurs ne sont pas des variables non définies
            if any(str(v).startswith("UNDEFINED_") for v in wallet.values()):
                logger.warning(f"Wallet ignoré: variables d'environnement non définies")
                continue
                
            # Vérifier la chaîne blockchain
            if wallet["chain"] not in ["avax", "sol", "eth", "bsc", "ftm"]:
                logger.warning(f"Wallet ignoré: chaîne non supportée: {wallet['chain']}")
                continue
                
            valid_wallets.append(wallet)
        
        return valid_wallets

# Fonction utilitaire pour obtenir les wallets chargés
def get_wallets() -> List[Dict[str, Any]]:
    """
    Charge et retourne les wallets configurés.
    
    Returns:
        Liste des wallets configurés et valides
    """
    loader = WalletLoader()
    return loader.load_wallets()

# Fonction pour obtenir les wallets d'une chaîne spécifique
def get_chain_wallets(chain: str) -> List[Dict[str, Any]]:
    """
    Retourne les wallets pour une chaîne spécifique.
    
    Args:
        chain: Nom de la chaîne (avax, sol, etc.)
        
    Returns:
        Liste des wallets pour la chaîne spécifiée
    """
    wallets = get_wallets()
    return [w for w in wallets if w["chain"].lower() == chain.lower()] 