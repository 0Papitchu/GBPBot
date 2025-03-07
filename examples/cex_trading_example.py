#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Exemple d'utilisation des clients CEX du GBPBot.

Ce script montre comment utiliser les clients d'échanges centralisés (CEX)
pour effectuer des opérations courantes comme récupérer des prix, consulter
des soldes et passer des ordres.
"""

import asyncio
import logging
import sys
import os
from decimal import Decimal
from typing import Dict, Any, cast

# Ajouter le répertoire racine au chemin pour pouvoir importer les modules GBPBot
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from gbpbot.clients.cex import CEXClientFactory, SUPPORTED_EXCHANGES
from gbpbot.config.config_manager import ConfigManager

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("cex_example")


async def show_ticker_info(exchange: str, symbol: str) -> None:
    """
    Affiche les informations de ticker pour un symbole donné.
    
    Args:
        exchange: Nom de l'échange
        symbol: Symbole du marché
    """
    client = CEXClientFactory.create_client(exchange)
    await client.initialize()
    
    try:
        logger.info(f"Récupération du ticker pour {symbol} sur {exchange}...")
        ticker = await client.get_ticker(symbol)
        
        logger.info(f"Ticker {symbol} sur {exchange}:")
        logger.info(f"  Prix actuel: {ticker['last']}")
        logger.info(f"  Meilleur bid: {ticker['bid']}")
        logger.info(f"  Meilleur ask: {ticker['ask']}")
        logger.info(f"  Volume 24h: {ticker['volume']}")
        logger.info(f"  Variation 24h: {ticker['percentage']}%")
    finally:
        await client.shutdown()


async def show_orderbook(exchange: str, symbol: str, depth: int = 5) -> None:
    """
    Affiche le carnet d'ordres pour un symbole donné.
    
    Args:
        exchange: Nom de l'échange
        symbol: Symbole du marché
        depth: Nombre de niveaux à afficher
    """
    client = CEXClientFactory.create_client(exchange)
    await client.initialize()
    
    try:
        logger.info(f"Récupération du carnet d'ordres pour {symbol} sur {exchange}...")
        orderbook = await client.get_orderbook(symbol, limit=depth)
        
        logger.info(f"Carnet d'ordres {symbol} sur {exchange}:")
        logger.info("  Asks (vendeurs):")
        for i, (price, amount) in enumerate(orderbook["asks"][:depth]):
            logger.info(f"    {i+1}. Prix: {price}, Quantité: {amount}")
        
        logger.info("  Bids (acheteurs):")
        for i, (price, amount) in enumerate(orderbook["bids"][:depth]):
            logger.info(f"    {i+1}. Prix: {price}, Quantité: {amount}")
    finally:
        await client.shutdown()


async def show_account_balance(exchange: str) -> None:
    """
    Affiche les soldes du compte.
    
    Args:
        exchange: Nom de l'échange
    """
    client = CEXClientFactory.create_client(exchange)
    await client.initialize()
    
    try:
        logger.info(f"Récupération des soldes sur {exchange}...")
        balances = await client.get_balance()
        
        if not balances:
            logger.info("Aucun solde trouvé ou clés API non configurées.")
            return
        
        logger.info(f"Soldes sur {exchange}:")
        # balances est un dictionnaire de currency->amount
        balances_dict = cast(Dict[str, Decimal], balances)
        for currency, amount in balances_dict.items():
            if amount > Decimal("0"):
                logger.info(f"  {currency}: {amount}")
    finally:
        await client.shutdown()


async def place_test_order(exchange: str, symbol: str, amount: Decimal, price: Decimal) -> None:
    """
    Place un ordre de test (limit buy).
    
    ATTENTION: Cette fonction place un ordre réel si les clés API sont configurées !
    En mode testnet, l'ordre sera placé sur le réseau de test.
    
    Args:
        exchange: Nom de l'échange
        symbol: Symbole du marché
        amount: Quantité à acheter
        price: Prix d'achat
    """
    client = CEXClientFactory.create_client(exchange, testnet=True)
    await client.initialize()
    
    try:
        logger.info(f"Placement d'un ordre limit buy sur {exchange} (testnet): {amount} {symbol} @ {price}")
        
        order = await client.create_order(
            symbol=symbol,
            order_type="limit",
            side="buy",
            amount=amount,
            price=price
        )
        
        logger.info(f"Ordre créé:")
        logger.info(f"  ID: {order['id']}")
        logger.info(f"  Type: {order['type']}")
        logger.info(f"  Côté: {order['side']}")
        logger.info(f"  Quantité: {order['amount']}")
        logger.info(f"  Prix: {order['price']}")
        logger.info(f"  Statut: {order['status']}")
        
        # Attendre un peu puis annuler l'ordre
        logger.info("Attente de 5 secondes avant annulation...")
        await asyncio.sleep(5)
        
        logger.info(f"Annulation de l'ordre {order['id']}...")
        cancel_result = await client.cancel_order(order['id'], symbol)
        logger.info(f"Ordre annulé avec succès: {cancel_result['status']}")
    except Exception as e:
        logger.error(f"Erreur lors du placement/annulation de l'ordre: {str(e)}")
    finally:
        await client.shutdown()


async def list_available_markets(exchange: str) -> None:
    """
    Liste les marchés disponibles sur l'échange.
    
    Args:
        exchange: Nom de l'échange
    """
    client = CEXClientFactory.create_client(exchange)
    await client.initialize()
    
    try:
        logger.info(f"Récupération des marchés disponibles sur {exchange}...")
        markets = await client.get_markets()
        
        logger.info(f"Marchés disponibles sur {exchange} ({len(markets)} total):")
        for i, market in enumerate(markets[:10]):  # Afficher seulement les 10 premiers
            logger.info(f"  {i+1}. {market['symbol']} ({market['base']}/{market['quote']})")
        
        if len(markets) > 10:
            logger.info(f"  ... et {len(markets) - 10} autres marchés")
    finally:
        await client.shutdown()


async def main() -> None:
    """Fonction principale exécutant les exemples."""
    logger.info(f"Échanges supportés: {', '.join(SUPPORTED_EXCHANGES)}")
    
    # Choisir l'échange à utiliser
    exchange = "binance"
    symbol = "BTC/USDT"
    
    # Exemples d'utilisation des clients CEX
    await show_ticker_info(exchange, symbol)
    print()
    
    await show_orderbook(exchange, symbol, depth=5)
    print()
    
    await list_available_markets(exchange)
    print()
    
    # Les fonctions suivantes nécessitent des clés API configurées
    config = ConfigManager().get_config()
    if config.get("exchanges", {}).get(exchange, {}).get("api_key"):
        await show_account_balance(exchange)
        print()
        
        # ATTENTION: Cette fonction place un ordre réel (en testnet)
        # Décommentez pour tester
        # await place_test_order(exchange, symbol, Decimal("0.001"), Decimal("20000.00"))
    else:
        logger.info(f"Clés API non configurées pour {exchange}, exemples d'ordres désactivés")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Programme interrompu")
    except Exception as e:
        logger.error(f"Erreur: {str(e)}")
        import traceback
        traceback.print_exc() 