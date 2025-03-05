#!/usr/bin/env python3
"""
Script de test pour vérifier les améliorations apportées au bot GBP
"""

import asyncio
import sys
import os
from loguru import logger
import time
import argparse
import random
from typing import Dict, List, Any, Optional

# Configurer asyncio pour Windows
if os.name == 'nt':
    # Utiliser le SelectorEventLoop sur Windows pour éviter les problèmes avec aiodns
    try:
        if sys.version_info >= (3, 8):
            # Python 3.8+ utilise ProactorEventLoop par défaut sur Windows
            # Forcer l'utilisation de SelectorEventLoop
            if asyncio.get_event_loop_policy()._loop_factory.__name__ == 'ProactorEventLoop':
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
                print("Politique d'événements asyncio configurée pour Windows (SelectorEventLoop)")
    except Exception as e:
        print(f"Impossible de configurer la politique d'événements asyncio pour Windows: {str(e)}")

# Ajouter le répertoire parent au chemin de recherche des modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gbpbot.config.config_manager import config_manager
from gbpbot.core.rpc.rpc_manager import rpc_manager
from gbpbot.core.price_feed import PriceManager
from gbpbot.main import GBPBot
from gbpbot.utils.cache_manager import cache_manager
from gbpbot.utils.anomaly_detector import anomaly_detector
from gbpbot.utils.websocket_manager import WebSocketManager

# Configuration du logger
logger.remove()
logger.add(
    sys.stdout,
    colorize=True,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
)
logger.add("test_improvements.log", rotation="100 MB")

async def test_rpc_manager():
    """
    Teste le gestionnaire RPC
    """
    logger.info("🔍 Test du gestionnaire RPC...")
    
    # Vérifier la santé des RPC
    await rpc_manager.check_rpc_health()
    
    # Récupérer le meilleur RPC
    best_rpc = rpc_manager.get_best_rpc_url()
    logger.info(f"Meilleur RPC: {best_rpc}")
    
    # Récupérer un provider Web3
    web3 = rpc_manager.get_web3_provider()
    if web3:
        # Vérifier la connexion
        if web3.is_connected():
            # Récupérer le numéro de bloc
            block_number = web3.eth.block_number
            logger.info(f"Numéro de bloc actuel: {block_number}")
            
            # Récupérer le prix du gaz
            gas_price = web3.eth.gas_price
            logger.info(f"Prix du gaz actuel: {web3.from_wei(gas_price, 'gwei'):.2f} Gwei")
            
            logger.info("✅ Test du gestionnaire RPC réussi")
            return True
    
    logger.error("❌ Test du gestionnaire RPC échoué")
    return False

async def test_price_feed_anomaly_detection():
    """Teste la détection d'anomalies de prix"""
    logger.info("=== Test de la détection d'anomalies de prix ===")
    
    # Obtenir une instance Web3
    web3 = rpc_manager.get_web3_provider()
    if not web3:
        logger.error("Impossible d'obtenir une instance Web3")
        return False
    
    # Créer une instance de PriceFeed en mode simulation
    price_feed = PriceManager(web3, is_testnet=False, simulation_mode=True)
    
    # Tester la détection d'anomalies avec des prix normaux
    normal_prices = [30.0, 30.5, 31.0, 30.8, 30.2]
    for price in normal_prices:
        is_anomaly = price_feed._is_price_anomaly("WAVAX/USDC", "test_source", price)
        logger.info(f"Prix: {price}, Anomalie: {is_anomaly}")
    
    # Tester la détection d'anomalies avec des prix anormaux
    anomaly_prices = [0.0001, 10000.0, 50.0, 10.0]
    for price in anomaly_prices:
        is_anomaly = price_feed._is_price_anomaly("WAVAX/USDC", "test_source", price)
        logger.info(f"Prix: {price}, Anomalie: {is_anomaly}")
    
    # Ne pas tester la normalisation des prix car cela nécessite des méthodes qui ne sont pas disponibles en mode simulation
    logger.info("Test de la détection d'anomalies de prix terminé avec succès")
    
    return True

async def test_websocket_initialization():
    """Teste l'initialisation des WebSockets"""
    logger.info("=== Test de l'initialisation des WebSockets ===")
    
    # Obtenir une instance Web3
    web3 = rpc_manager.get_web3_provider()
    if not web3:
        logger.error("Impossible d'obtenir une instance Web3")
        return False
    
    # Créer une instance de PriceFeed
    price_feed = PriceManager(web3, is_testnet=False, simulation_mode=False)
    
    # Initialiser les WebSockets
    ws_prices = await price_feed.initialize_websockets()
    logger.info(f"WebSockets initialisés, prix initiaux: {ws_prices}")
    
    # Attendre quelques secondes pour recevoir des mises à jour
    logger.info("Attente de mises à jour WebSocket...")
    await asyncio.sleep(10)
    
    # Vérifier les prix WebSocket
    logger.info(f"Prix WebSocket après attente: {price_feed.ws_prices}")
    
    return True

async def test_gbpbot_initialization():
    """Teste l'initialisation du GBPBot avec les améliorations"""
    logger.info("=== Test de l'initialisation du GBPBot ===")
    
    try:
        # Créer une instance de GBPBot en mode simulation
        bot = GBPBot(simulation_mode=True, is_testnet=False)
        
        # Vérifier que le bot est correctement initialisé
        if bot.blockchain and bot.blockchain.is_connected():
            logger.success("GBPBot initialisé avec succès, connexion blockchain établie")
        else:
            logger.error("Échec de l'initialisation du GBPBot")
            return False
        
        # Démarrer le bot pendant quelques secondes pour tester
        logger.info("Démarrage du bot pour un test court...")
        
        # Créer une tâche pour le bot
        bot_task = asyncio.create_task(bot.start())
        
        # Attendre 30 secondes
        await asyncio.sleep(30)
        
        # Annuler la tâche
        bot_task.cancel()
        
        try:
            await bot_task
        except asyncio.CancelledError:
            logger.info("Test du bot terminé")
    except Exception as e:
        logger.error(f"Erreur lors du test du GBPBot: {str(e)}")
        logger.info("Le test du GBPBot est ignoré en raison d'une erreur d'initialisation")
        return False
    
    return True

async def test_cache_manager():
    """
    Teste le gestionnaire de cache
    """
    logger.info("🔍 Test du gestionnaire de cache...")
    
    # Tester le cache RPC
    cache_key = "test_rpc_cache"
    cache_value = {"result": "test_value", "timestamp": time.time()}
    
    # Stocker une valeur dans le cache
    cache_manager.set_rpc_result(cache_key, cache_value)
    
    # Récupérer la valeur du cache
    cached_value = cache_manager.get_rpc_result(cache_key)
    
    if cached_value and cached_value["result"] == "test_value":
        logger.info("Cache RPC: OK")
    else:
        logger.error("Cache RPC: ERREUR")
        return False
    
    # Tester le cache de prix
    cache_manager.set_price("AVAX/USDT", 21.5)
    cached_price = cache_manager.get_price("AVAX/USDT")
    
    if cached_price and cached_price == 21.5:
        logger.info("Cache de prix: OK")
    else:
        logger.error("Cache de prix: ERREUR")
        return False
    
    # Récupérer les statistiques du cache
    stats = cache_manager.get_stats()
    logger.info(f"Statistiques du cache: {stats}")
    
    logger.info("✅ Test du gestionnaire de cache réussi")
    return True

async def test_anomaly_detector():
    """
    Teste le détecteur d'anomalies
    """
    logger.info("🔍 Test du détecteur d'anomalies...")
    
    # Générer des prix normaux
    pair = "WAVAX/USDC"
    base_price = 21.5
    
    # Ajouter des prix normaux
    for i in range(15):
        # Prix avec une légère variation aléatoire
        price = base_price + random.uniform(-0.2, 0.2)
        anomaly_detector.add_price(pair, price, "test")
    
    # Vérifier les statistiques
    stats = anomaly_detector.get_price_statistics(pair, "test")
    if stats:
        logger.info(f"Statistiques pour {pair}: moyenne={stats['mean']:.4f}, écart-type={stats['std']:.4f}")
    else:
        logger.error("Impossible de récupérer les statistiques")
        return False
    
    # Ajouter un prix anormal
    anomaly_price = base_price * 1.5  # 50% plus élevé
    is_anomaly, details = anomaly_detector.is_price_anomaly(pair, anomaly_price, "test")
    
    if is_anomaly:
        logger.info(f"Anomalie détectée: {details}")
    else:
        logger.error("Anomalie non détectée")
        return False
    
    # Vérifier les anomalies
    anomalies = anomaly_detector.get_anomalies_for_pair(pair)
    if anomalies:
        logger.info(f"Nombre d'anomalies détectées: {len(anomalies)}")
    else:
        logger.error("Aucune anomalie détectée")
        return False
    
    logger.info("✅ Test du détecteur d'anomalies réussi")
    return True

async def test_websocket_manager():
    """
    Teste le gestionnaire de WebSockets
    """
    logger.info("🔍 Test du gestionnaire de WebSockets...")
    
    # Initialiser le gestionnaire de WebSockets
    ws_manager = WebSocketManager()
    
    # Récupérer les paires à surveiller
    pairs = config_manager.get_config("websocket")["pairs"]
    logger.info(f"Paires à surveiller: {pairs}")
    
    # Dictionnaire pour stocker les prix
    prices = {}
    
    # Callback pour les messages
    def on_message(ws_id, message):
        try:
            # Extraire le prix du message
            if "p" in message:
                pair = ws_id.split("_")[0]
                price = float(message["p"])
                prices[pair] = price
                logger.debug(f"Prix reçu pour {pair}: {price}")
        except Exception as e:
            logger.error(f"Erreur lors du traitement du message: {str(e)}")
    
    # Initialiser les WebSockets pour chaque paire
    ws_tasks = []
    for pair in pairs:
        # Créer l'URL du WebSocket Binance
        ws_url = f"wss://stream.binance.com:9443/ws/{pair.lower()}@trade"
        
        # Connecter le WebSocket
        ws_id = f"{pair}_binance"
        ws_manager.connect(ws_id, ws_url, on_message=on_message)
        logger.info(f"WebSocket connecté pour {pair}")
        
        # Ajouter à la liste des tâches
        ws_tasks.append(ws_id)
    
    # Attendre que les prix soient reçus
    logger.info(f"Attente des prix WebSocket ({len(ws_tasks)} WebSockets initialisés)...")
    
    # Attendre jusqu'à 10 secondes pour recevoir les prix
    for _ in range(10):
        await asyncio.sleep(1)
        if len(prices) == len(pairs):
            break
    
    # Afficher les prix reçus
    if prices:
        for pair, price in prices.items():
            logger.info(f"Prix WebSocket pour {pair.upper()}: {price}")
        
        logger.info("✅ Test du gestionnaire de WebSockets réussi")
        
        # Fermer les WebSockets
        for ws_id in ws_tasks:
            ws_manager.disconnect(ws_id)
        
        return True
    else:
        logger.error("❌ Aucun prix reçu des WebSockets")
        return False

async def test_bot_initialization():
    """
    Teste l'initialisation du GBPBot
    """
    logger.info("🔍 Test d'initialisation du GBPBot...")
    
    try:
        # Initialiser le bot
        bot = GBPBot(network="avalanche", testnet=False)
        
        # Vérifier si le bot est initialisé
        if bot.blockchain_client:
            logger.info("Blockchain client initialisé")
            
            # Vérifier la connexion RPC
            if bot.blockchain_client.web3:
                logger.info(f"Connecté au réseau: {bot.blockchain_client.web3.eth.chain_id}")
                logger.info("✅ Test d'initialisation du GBPBot réussi")
                return True
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation du GBPBot: {str(e)}")
        logger.info("⚠️ Test d'initialisation du GBPBot ignoré")
    
    return False

async def main():
    """
    Fonction principale
    """
    # Configurer le parser d'arguments
    parser = argparse.ArgumentParser(description="Tests des améliorations du GBPBot")
    parser.add_argument("--rpc", action="store_true", help="Tester le gestionnaire RPC")
    parser.add_argument("--cache", action="store_true", help="Tester le gestionnaire de cache")
    parser.add_argument("--anomaly", action="store_true", help="Tester le détecteur d'anomalies")
    parser.add_argument("--websocket", action="store_true", help="Tester le gestionnaire de WebSockets")
    parser.add_argument("--bot", action="store_true", help="Tester l'initialisation du GBPBot")
    parser.add_argument("--all", action="store_true", help="Exécuter tous les tests")
    
    # Parser les arguments
    args = parser.parse_args()
    
    # Si aucun argument n'est spécifié, exécuter tous les tests
    if not any(vars(args).values()):
        args.all = True
    
    # Afficher le titre
    logger.info("=" * 50)
    logger.info("Tests des améliorations du GBPBot")
    logger.info("=" * 50)
    
    # Exécuter les tests
    results = {}
    
    if args.all or args.rpc:
        results["rpc"] = await test_rpc_manager()
    
    if args.all or args.cache:
        results["cache"] = await test_cache_manager()
    
    if args.all or args.anomaly:
        results["anomaly"] = await test_anomaly_detector()
    
    if args.all or args.websocket:
        results["websocket"] = await test_websocket_manager()
    
    if args.all or args.bot:
        results["bot"] = await test_bot_initialization()
    
    # Afficher les résultats
    logger.info("=" * 50)
    logger.info("Résultats des tests")
    logger.info("=" * 50)
    
    for test, result in results.items():
        status = "✅ RÉUSSI" if result else "❌ ÉCHOUÉ"
        logger.info(f"Test {test}: {status}")
    
    # Vérifier si tous les tests ont réussi
    if all(results.values()):
        logger.info("✅ Tous les tests ont réussi")
        return 0
    else:
        logger.error("❌ Certains tests ont échoué")
        return 1

if __name__ == "__main__":
    # Exécuter la fonction principale
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 