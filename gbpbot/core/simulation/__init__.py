"""
Module de simulation pour GBPBot
Ce module fournit des fonctionnalités pour simuler différents aspects du trading
"""

import os
from gbpbot.config.config_manager import config_manager
from loguru import logger

# Variable globale indiquant si le mode simulation est activé
simulation_mode = False

def is_simulation_mode() -> bool:
    """
    Détermine si le bot fonctionne en mode simulation
    
    Returns:
        bool: True si le mode simulation est activé, False sinon
    """
    return simulation_mode

def setup_simulation_mode(enabled: bool = True) -> None:
    """
    Active ou désactive le mode simulation
    
    Args:
        enabled: True pour activer, False pour désactiver
    """
    global simulation_mode
    simulation_mode = enabled
    
    # Mettre à jour la configuration
    config = config_manager.get_config()
    if "simulation" not in config:
        config["simulation"] = {}
    
    config["simulation"]["enabled"] = enabled
    
    # Enregistrer dans les logs
    if enabled:
        logger.info("Mode simulation activé")
    else:
        logger.info("Mode simulation désactivé")

# Initialiser le mode simulation à partir de la configuration ou des variables d'environnement
def init_simulation():
    """
    Initialise le mode simulation en fonction de la configuration
    """
    # Vérifier la configuration
    config = config_manager.get_config()
    sim_enabled = config.get("simulation", {}).get("enabled", False)
    
    # Vérifier les variables d'environnement (prioritaires)
    env_sim_mode = os.environ.get("GBPBOT_SIMULATION_MODE", "").lower()
    if env_sim_mode in ("true", "1", "yes", "y", "on"):
        sim_enabled = True
    elif env_sim_mode in ("false", "0", "no", "n", "off"):
        sim_enabled = False
    
    # Configurer le mode simulation
    setup_simulation_mode(sim_enabled)
    
    return sim_enabled

# Initialiser les modules de simulation
def init_simulation_modules():
    """
    Initialise tous les modules de simulation nécessaires
    """
    if is_simulation_mode():
        logger.info("Initialisation des modules de simulation")
        
        # Importer et initialiser les modules de simulation
        try:
            # RPC simulé
            from gbpbot.core.rpc.rpc_simulation import simulated_rpc_manager
            logger.info("Module RPC simulé initialisé")
        except ImportError:
            logger.warning("Module RPC simulé non disponible")
        
        try:
            # Portefeuille simulé
            from gbpbot.core.simulation.wallet_simulation import wallet_manager
            logger.info("Module de portefeuille simulé initialisé")
        except ImportError:
            logger.warning("Module de portefeuille simulé non disponible")

# Initialiser automatiquement
init_simulation()

# Exporter les fonctions
__all__ = ["is_simulation_mode", "setup_simulation_mode", "init_simulation", "init_simulation_modules"] 