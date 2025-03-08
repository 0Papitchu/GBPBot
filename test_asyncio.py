#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test pour la gestion correcte d'asyncio et des sessions aiohttp.
Ce script démontre les bonnes pratiques pour éviter les erreurs comme 
"RuntimeError: no running event loop" et "Unclosed client session".
"""

import asyncio
import aiohttp
import sys
import platform
import logging
from pathlib import Path

# Configuration du logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_asyncio")

async def fetch_with_session(session, url):
    """
    Effectue une requête HTTP en utilisant une session existante.
    
    Args:
        session: Session aiohttp à utiliser
        url: URL à appeler
        
    Returns:
        dict: Réponse JSON ou texte si non-JSON
    """
    try:
        async with session.get(url, timeout=10) as response:
            if response.content_type == 'application/json':
                return await response.json()
            else:
                return {"text": await response.text(), "status": response.status}
    except Exception as e:
        logger.error(f"Erreur lors de la requête à {url}: {e}")
        return {"error": str(e)}

async def fetch_multiple_urls(urls):
    """
    Appelle plusieurs URLs de manière concurrente.
    Utilise une seule session pour toutes les requêtes.
    
    Args:
        urls: Liste d'URLs à appeler
        
    Returns:
        list: Liste des résultats dans l'ordre des URLs
    """
    # Créer une session unique pour toutes les requêtes
    async with aiohttp.ClientSession() as session:
        # Créer les tâches pour chaque URL
        tasks = [fetch_with_session(session, url) for url in urls]
        
        # Attendre que toutes les tâches se terminent
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return results

async def main_async():
    """
    Fonction asynchrone principale.
    Démonstration des bonnes pratiques pour la gestion des sessions aiohttp.
    """
    # URLs de test (APIs publiques)
    test_urls = [
        "https://api.github.com/",
        "https://api.coingecko.com/api/v3/ping",
        "https://api.coindesk.com/v1/bpi/currentprice.json"
    ]
    
    logger.info("Début des requêtes HTTP asynchrones...")
    
    # Utilisation correcte des sessions aiohttp
    results = await fetch_multiple_urls(test_urls)
    
    # Afficher les résultats
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"URL {test_urls[i]}: Exception: {result}")
        else:
            logger.info(f"URL {test_urls[i]}: Succès, type de réponse: {type(result)}")
    
    logger.info("Test terminé avec succès!")
    return True

def configure_asyncio():
    """
    Configure asyncio selon le système d'exploitation.
    Sur Windows, utilise la politique SelectSelector.
    """
    if platform.system() == 'Windows':
        # Windows nécessite une configuration spéciale pour asyncio
        try:
            import asyncio
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            logger.info("Politique d'événement WindowsSelectorEventLoopPolicy configurée pour Windows")
        except ImportError:
            logger.warning("Impossible de configurer la politique d'événement pour Windows")
    else:
        # Vérifier si uvloop est disponible sur les systèmes Unix
        try:
            import uvloop
            uvloop.install()
            logger.info("uvloop installé pour de meilleures performances sur Unix")
        except ImportError:
            logger.info("uvloop non disponible, utilisation de la boucle asyncio standard")

def main():
    """
    Point d'entrée principal du script.
    Configure asyncio et lance la fonction principale asynchrone.
    """
    # Configurer asyncio selon le système d'exploitation
    configure_asyncio()
    
    # Lancer la fonction asynchrone principale avec asyncio.run()
    try:
        result = asyncio.run(main_async())
        return 0 if result else 1
    except Exception as e:
        logger.exception(f"Erreur non gérée dans la boucle principale: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 