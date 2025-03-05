#!/usr/bin/env python
"""
Script pour vérifier l'existence des paires de trading sur différents exchanges
"""

import asyncio
import logging
import ccxt.async_support as ccxt
from typing import Dict, List, Set, Tuple

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("trading_pairs_results.log"),
        logging.StreamHandler()
    ]
)

# Exchanges à vérifier
EXCHANGES = [
    "binance", "kucoin", "gate", "okx", "huobi", "bybit"
]

# Paires à vérifier (format: base/quote)
PAIRS_TO_CHECK = [
    "AVAX/USDT", "AVAX/USDC", "AVAX/USD", 
    "WAVAX/USDT", "WAVAX/USDC", "WAVAX/USD",
    "ETH/AVAX", "BTC/AVAX",
    "ETH/USDT", "ETH/USDC", "BTC/USDT", "BTC/USDC"
]

async def check_exchange_pairs(exchange_id: str) -> Tuple[str, Dict[str, bool], Set[str]]:
    """Vérifie l'existence des paires sur un exchange spécifique"""
    exchange_class = getattr(ccxt, exchange_id)
    exchange = exchange_class()
    
    results = {}
    all_pairs = set()
    
    try:
        logging.info(f"Vérification des paires sur {exchange_id}...")
        markets = await exchange.load_markets()
        
        # Collecter toutes les paires disponibles
        all_pairs = set(markets.keys())
        
        # Vérifier les paires spécifiques
        for pair in PAIRS_TO_CHECK:
            results[pair] = pair in markets
            status = "✅" if pair in markets else "❌"
            logging.info(f"{status} {exchange_id}: {pair}")
            
        # Trouver des paires alternatives pour AVAX
        avax_pairs = [p for p in all_pairs if "AVAX" in p]
        if avax_pairs:
            logging.info(f"Paires AVAX disponibles sur {exchange_id}: {', '.join(avax_pairs[:5])}")
            if len(avax_pairs) > 5:
                logging.info(f"... et {len(avax_pairs) - 5} autres")
    
    except Exception as e:
        logging.error(f"Erreur lors de la vérification de {exchange_id}: {str(e)}")
    finally:
        await exchange.close()
    
    return exchange_id, results, all_pairs

async def check_all_exchanges():
    """Vérifie toutes les paires sur tous les exchanges"""
    tasks = [check_exchange_pairs(exchange_id) for exchange_id in EXCHANGES]
    results = await asyncio.gather(*tasks)
    
    # Analyser les résultats
    exchange_results = {exchange_id: pairs for exchange_id, pairs, _ in results}
    all_exchange_pairs = {exchange_id: all_pairs for exchange_id, _, all_pairs in results}
    
    # Trouver les paires communes à tous les exchanges
    common_pairs = set()
    for exchange_id, pairs in all_exchange_pairs.items():
        if not common_pairs:
            common_pairs = pairs
        else:
            common_pairs &= pairs
    
    # Générer des recommandations
    logging.info("\n===== RÉSULTATS DE LA VÉRIFICATION DES PAIRES =====")
    
    # Tableau récapitulatif
    logging.info("\nTableau récapitulatif des paires:")
    header = "Paire        | " + " | ".join(EXCHANGES)
    separator = "------------|" + "-|".join(["-" * len(ex) for ex in EXCHANGES])
    logging.info(header)
    logging.info(separator)
    
    for pair in PAIRS_TO_CHECK:
        row = f"{pair:<12} | "
        row += " | ".join(["✅" if exchange_results[ex].get(pair, False) else "❌" for ex in EXCHANGES])
        logging.info(row)
    
    # Recommandations
    logging.info("\nRecommandations pour les paires de trading:")
    
    # Paires les plus supportées
    pair_support = {}
    for pair in PAIRS_TO_CHECK:
        support_count = sum(1 for ex in EXCHANGES if exchange_results[ex].get(pair, False))
        pair_support[pair] = support_count
    
    best_pairs = sorted(pair_support.items(), key=lambda x: x[1], reverse=True)
    
    logging.info("\nPaires recommandées (par ordre de support):")
    for pair, count in best_pairs:
        if count > 0:
            exchanges_list = [ex for ex in EXCHANGES if exchange_results[ex].get(pair, False)]
            logging.info(f"- {pair}: Supporté par {count}/{len(EXCHANGES)} exchanges ({', '.join(exchanges_list)})")
    
    # Écrire les recommandations dans un fichier
    with open("trading_pairs_recommendations.txt", "w") as f:
        f.write("# Paires de trading recommandées\n\n")
        f.write("# Format: TOKEN_PAIRS=paire1,paire2,paire3\n")
        
        # Paires principales (supportées par au moins 3 exchanges)
        main_pairs = [pair for pair, count in best_pairs if count >= 3]
        if main_pairs:
            f.write(f"TOKEN_PAIRS={','.join(main_pairs)}\n")
        else:
            # Fallback sur les meilleures paires disponibles
            top_pairs = [pair for pair, _ in best_pairs[:3] if pair_support[pair] > 0]
            if top_pairs:
                f.write(f"TOKEN_PAIRS={','.join(top_pairs)}\n")
            else:
                f.write("# Aucune paire commune trouvée. Vérifiez manuellement les paires disponibles.\n")

if __name__ == "__main__":
    logging.info("Démarrage de la vérification des paires de trading...")
    asyncio.run(check_all_exchanges())
    logging.info("Vérification terminée. Consultez trading_pairs_results.log pour les détails.") 