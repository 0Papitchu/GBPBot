#!/usr/bin/env python
"""
Script pour tester la fiabilité des endpoints RPC Avalanche
"""

import asyncio
import time
import aiohttp
import json
import logging
from typing import Dict, List, Tuple

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("rpc_test_results.log"),
        logging.StreamHandler()
    ]
)

# Liste des endpoints RPC Avalanche à tester
RPC_ENDPOINTS = [
    "https://api.avax.network/ext/bc/C/rpc",
    "https://avalanche-c-chain.publicnode.com",
    "https://rpc.ankr.com/avalanche",
    "https://avalanche.blockpi.network/v1/rpc/public",
    "https://avalanche-mainnet.infura.io/v3/9aa3d95b3bc440fa88ea12eaa4456161",  # Clé publique Infura
    "https://avalanche.drpc.org",
    "https://avalanche.rpc.thirdweb.com",
    "https://avax.meowrpc.com",
    "https://avalanche.api.onfinality.io/public",
    "https://1rpc.io/avax/c",
    "https://avax-mainnet.gateway.pokt.network/v1/lb/605238bf6b986eea7cf36d5e",
    "https://avalanche.public-rpc.com",
]

# Requête JSON-RPC standard pour tester la connexion
TEST_REQUEST = {
    "jsonrpc": "2.0",
    "method": "eth_blockNumber",
    "params": [],
    "id": 1
}

async def test_endpoint(session: aiohttp.ClientSession, endpoint: str) -> Tuple[str, bool, float, Dict]:
    """Teste un endpoint RPC et retourne les résultats"""
    start_time = time.time()
    success = False
    response_data = {}
    
    try:
        async with session.post(endpoint, json=TEST_REQUEST, timeout=5) as response:
            response_time = time.time() - start_time
            if response.status == 200:
                response_data = await response.json()
                if "result" in response_data:
                    success = True
                    logging.info(f"✅ {endpoint} - Réponse en {response_time:.2f}s")
                else:
                    logging.warning(f"⚠️ {endpoint} - Réponse sans 'result' en {response_time:.2f}s")
            else:
                logging.error(f"❌ {endpoint} - Statut HTTP {response.status} en {response_time:.2f}s")
    except Exception as e:
        response_time = time.time() - start_time
        logging.error(f"❌ {endpoint} - Erreur: {str(e)} en {response_time:.2f}s")
    
    return endpoint, success, response_time, response_data

async def test_all_endpoints():
    """Teste tous les endpoints RPC et affiche les résultats"""
    async with aiohttp.ClientSession() as session:
        tasks = [test_endpoint(session, endpoint) for endpoint in RPC_ENDPOINTS]
        results = await asyncio.gather(*tasks)
        
        # Trier les résultats par temps de réponse
        successful_endpoints = [r for r in results if r[1]]
        successful_endpoints.sort(key=lambda x: x[2])  # Trier par temps de réponse
        
        # Afficher les résultats
        logging.info("\n===== RÉSULTATS DES TESTS RPC =====")
        logging.info(f"Endpoints testés: {len(RPC_ENDPOINTS)}")
        logging.info(f"Endpoints fonctionnels: {len(successful_endpoints)}")
        
        if successful_endpoints:
            logging.info("\nEndpoints recommandés (du plus rapide au plus lent):")
            for i, (endpoint, _, response_time, _) in enumerate(successful_endpoints[:5], 1):
                logging.info(f"{i}. {endpoint} - {response_time:.2f}s")
            
            # Générer la configuration pour .env
            rpc_config = "\n# Configuration RPC optimisée\n"
            rpc_config += f"PRIMARY_RPC_URL={successful_endpoints[0][0]}\n"
            
            if len(successful_endpoints) > 1:
                backup_urls = [endpoint[0] for endpoint in successful_endpoints[1:4]]
                rpc_config += f"BACKUP_RPC_URLS={','.join(backup_urls)}\n"
            
            logging.info("\nConfiguration recommandée pour .env:")
            logging.info(rpc_config)
            
            # Écrire la configuration dans un fichier
            with open("rpc_config.txt", "w") as f:
                f.write(rpc_config)
        else:
            logging.error("Aucun endpoint fonctionnel trouvé!")

if __name__ == "__main__":
    logging.info("Démarrage des tests des endpoints RPC Avalanche...")
    asyncio.run(test_all_endpoints())
    logging.info("Tests terminés. Consultez rpc_test_results.log pour les détails.") 