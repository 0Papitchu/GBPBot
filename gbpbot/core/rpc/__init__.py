"""
Module de gestion des connexions RPC pour GBPBot.
"""

from gbpbot.core.rpc.rpc_manager import RPCManager

# Singleton global
rpc_manager = RPCManager()

# Exporter le gestionnaire RPC simulé s'il existe
try:
    from gbpbot.core.rpc.rpc_simulation import simulated_rpc_manager
except ImportError:
    # En cas d'erreur d'importation, créer une variable simulée pour éviter les erreurs
    simulated_rpc_manager = None

__all__ = ['rpc_manager', 'simulated_rpc_manager'] 