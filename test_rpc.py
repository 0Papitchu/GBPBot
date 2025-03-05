import asyncio
from gbpbot.core.rpc.rpc_manager import rpc_manager
from loguru import logger
import sys

# Configuration du logger
logger.remove()
logger.add(
    sys.stdout,
    colorize=True,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
)

async def test_rpc_manager():
    """Teste le gestionnaire RPC"""
    try:
        logger.info("Test du gestionnaire RPC")
        
        # Vérifier la santé des RPC
        logger.info("Vérification de la santé des RPC...")
        result = await rpc_manager.check_rpc_health()
        
        logger.info(f"Résultat: {result}")
        
        # Fermer la session
        await rpc_manager.close()
        
        logger.info("Test terminé avec succès")
    except Exception as e:
        logger.error(f"Erreur lors du test: {e}")

if __name__ == "__main__":
    asyncio.run(test_rpc_manager()) 