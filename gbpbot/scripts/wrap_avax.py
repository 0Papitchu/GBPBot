import asyncio
from loguru import logger
import sys
from web3 import Web3
from gbpbot.core.blockchain import BlockchainClient

async def main():
    """Script pour wrapper des AVAX en WAVAX"""
    try:
        # Initialiser le client blockchain en mode simulation
        client = BlockchainClient(simulation_mode=True)
        
        # Vérifier la connexion
        if not client.is_connected():
            logger.error("Impossible de se connecter à Avalanche")
            return
            
        # Vérifier le solde AVAX simulé
        avax_balance = client.simulated_balances["AVAX"]
        logger.info(f"Solde AVAX simulé: {avax_balance:.4f}")
        
        if avax_balance < 5.0:
            logger.error(f"Solde simulé insuffisant pour wrapper 5 AVAX: {avax_balance:.4f} AVAX")
            return
            
        # Wrapper 5 AVAX
        amount_to_wrap = 5.0
        logger.info(f"Wrapping simulé de {amount_to_wrap} AVAX en WAVAX...")
        
        tx_hash = await client.wrap_avax(amount_to_wrap)
        if not tx_hash:
            logger.error("Échec du wrapping simulé")
            return
            
        logger.info(f"Transaction simulée envoyée: {tx_hash}")
        logger.success(f"✅ {amount_to_wrap} AVAX wrappés avec succès en WAVAX (simulation)!")
        
        # Vérifier le nouveau solde
        wavax_balance = client.simulated_balances["WAVAX"]
        logger.info(f"Nouveau solde WAVAX simulé: {wavax_balance:.4f}")
        
    except Exception as e:
        logger.error(f"Erreur: {str(e)}")
        sys.exit(1)
        
if __name__ == "__main__":
    # Configurer le logging
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    
    # Exécuter le script
    asyncio.run(main()) 