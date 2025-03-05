import asyncio
from gbpbot.main import GBPBot
from loguru import logger
import sys
import os

# Configuration du logger
logger.remove()
logger.add(
    sys.stdout,
    colorize=True,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
)

async def test_bot():
    """Teste le démarrage du bot"""
    try:
        logger.info("Test de démarrage du bot")
        
        # Créer l'instance du bot
        bot = GBPBot(simulation_mode=True, is_testnet=False)
        
        # Définir le solde initial en mode simulation
        bot.blockchain.simulated_balances = {
            "WAVAX": 5.0,
            "USDT": 0.0,
            "USDC": 0.0,
            "WETH": 0.0
        }
        
        # Démarrer le bot avec un timeout
        try:
            # Exécuter le bot pendant 10 secondes maximum
            await asyncio.wait_for(bot.start(), timeout=10)
        except asyncio.TimeoutError:
            logger.info("Timeout atteint, arrêt du bot")
        
        logger.info("Test terminé avec succès")
    except Exception as e:
        logger.error(f"Erreur lors du test: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    # Configurer l'event loop pour Windows
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    # Exécuter le test
    asyncio.run(test_bot()) 