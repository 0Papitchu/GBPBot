"""
Module de recherche web pour GBPBot
Permet d'obtenir des informations récentes sur le marché, les tokens et les tendances
"""

import aiohttp
import asyncio
import os
import json
import logging
import time
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import urllib.parse

# Créer le logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("WebSearch")

class WebSearchProvider:
    """
    Fournisseur de recherche web qui utilise des API publiques et anonymes
    pour obtenir des informations récentes
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialise le fournisseur de recherche web
        
        Args:
            config: Configuration optionnelle
        """
        self.config = config or {}
        # Les clés API sont optionnelles, le système peut utiliser des API sans clé
        # si nécessaire, avec un taux limité
        self.serper_api_key = self.config.get("serper_api_key") or os.environ.get("SERPER_API_KEY")
        self.session = None
        self.cache = {}
        self.cache_duration = timedelta(hours=1)  # Cache d'une heure par défaut
    
    async def _ensure_session(self):
        """Assure qu'une session HTTP est disponible"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
    
    async def close(self):
        """Ferme la session HTTP"""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
    
    async def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Effectue une recherche web avec la requête spécifiée
        
        Args:
            query: Requête de recherche
            max_results: Nombre maximum de résultats à retourner
            
        Returns:
            Liste de résultats de recherche
        """
        # Vérifier d'abord dans le cache
        cache_key = f"search:{query}:{max_results}"
        if cache_key in self.cache:
            cache_entry = self.cache[cache_key]
            if datetime.now() - cache_entry["timestamp"] < self.cache_duration:
                return cache_entry["results"]
        
        await self._ensure_session()
        
        results = []
        
        # Tenter d'abord avec Serper si une clé API est disponible
        if self.serper_api_key:
            try:
                headers = {
                    "X-API-KEY": self.serper_api_key,
                    "Content-Type": "application/json"
                }
                payload = {
                    "q": query,
                    "num": max_results
                }
                
                async with self.session.post(
                    "https://google.serper.dev/search", 
                    headers=headers, 
                    json=payload
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        organic_results = data.get("organic", [])
                        
                        for result in organic_results[:max_results]:
                            results.append({
                                "title": result.get("title", ""),
                                "link": result.get("link", ""),
                                "snippet": result.get("snippet", ""),
                                "source": "serper"
                            })
            except Exception as e:
                logger.warning(f"Erreur avec Serper API: {str(e)}")
        
        # Si pas de résultats avec Serper, essayer des alternatives
        if not results:
            try:
                # Utiliser une méthode alternative basique via Bing ou DuckDuckGo
                # Note: Ce n'est pas une utilisation réelle de ces API,
                # c'est une alternative de fallback basique
                fallback_urls = [
                    f"https://www.bing.com/search?q={urllib.parse.quote(query)}",
                    f"https://duckduckgo.com/?q={urllib.parse.quote(query)}"
                ]
                
                for url in fallback_urls:
                    try:
                        async with self.session.get(url, headers={"User-Agent": "Mozilla/5.0"}) as response:
                            if response.status == 200:
                                html = await response.text()
                                
                                # Extraction très basique des titres et URLs
                                # Dans un système de production, utilisez une bibliothèque comme BeautifulSoup
                                # pour parser correctement le HTML
                                import re
                                title_matches = re.findall(r'<h2.*?>(.*?)</h2>', html)
                                url_matches = re.findall(r'href="(https?://[^"]+)"', html)
                                
                                for i in range(min(len(title_matches), len(url_matches), max_results)):
                                    results.append({
                                        "title": title_matches[i].replace("<", "").replace(">", ""),
                                        "link": url_matches[i],
                                        "snippet": "Snippet non disponible via recherche basique",
                                        "source": "fallback"
                                    })
                                
                                if results:
                                    break
                    except Exception as e:
                        logger.warning(f"Erreur avec la source de fallback {url}: {str(e)}")
            except Exception as e:
                logger.warning(f"Erreur avec la recherche de fallback: {str(e)}")
        
        # Mettre en cache les résultats
        self.cache[cache_key] = {
            "timestamp": datetime.now(),
            "results": results
        }
        
        # Si toujours pas de résultats, retourner un résultat vide
        if not results:
            logger.warning(f"Aucun résultat trouvé pour la requête: {query}")
        
        return results
    
    async def get_token_info(self, token_symbol: str, chain: str = None) -> Dict[str, Any]:
        """
        Recherche des informations spécifiques sur un token crypto
        
        Args:
            token_symbol: Symbole du token (ex: SOL, BONK)
            chain: Blockchain optionnelle pour préciser la recherche
            
        Returns:
            Informations sur le token
        """
        # Construire une requête ciblée
        query = f"{token_symbol} token"
        if chain:
            query += f" {chain} blockchain price analysis"
        else:
            query += " cryptocurrency price analysis recent news"
        
        # Effectuer la recherche
        search_results = await self.search(query, max_results=7)
        
        # Extraire et structurer les informations
        return {
            "symbol": token_symbol,
            "chain": chain,
            "search_results": search_results,
            "timestamp": datetime.now().isoformat()
        }
    
    async def get_market_news(self, keywords: List[str] = None) -> List[Dict[str, Any]]:
        """
        Obtient les dernières nouvelles du marché crypto
        
        Args:
            keywords: Mots-clés optionnels pour cibler la recherche
            
        Returns:
            Liste d'articles d'actualité
        """
        # Construire la requête
        base_query = "cryptocurrency market news latest"
        
        if keywords and len(keywords) > 0:
            base_query += " " + " ".join(keywords)
        
        # Effectuer la recherche
        search_results = await self.search(base_query, max_results=10)
        
        # Filtrer et formater les résultats
        news = []
        for result in search_results:
            news.append({
                "title": result.get("title", ""),
                "url": result.get("link", ""),
                "summary": result.get("snippet", ""),
                "source": result.get("source", "web"),
                "retrieved_at": datetime.now().isoformat()
            })
        
        return news

# Fonction utilitaire pour créer un fournisseur de recherche web
async def create_web_search_provider(config: Optional[Dict[str, Any]] = None) -> WebSearchProvider:
    """
    Crée et initialise un fournisseur de recherche web
    
    Args:
        config: Configuration optionnelle
        
    Returns:
        Fournisseur de recherche web initialisé
    """
    provider = WebSearchProvider(config)
    return provider 