from gbpbot.core.blockchain import BlockchainClient
from loguru import logger

def main():
    """Affiche l'adresse du wallet"""
    try:
        client = BlockchainClient()
        logger.info(f"Adresse du wallet: {client.account.address}")
    except Exception as e:
        logger.error(f"Erreur: {str(e)}")

if __name__ == "__main__":
    main() 