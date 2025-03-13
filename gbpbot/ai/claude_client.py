"""
Client Claude 3.7 pour GBPBot - Fournit une interface avec l'API Anthropic Claude 3.7
pour l'analyse avancée des opportunités de trading et la recherche web.
"""

import os
import json
import logging
import asyncio
from typing import Dict, List, Optional, Any, Tuple
import aiohttp
from datetime import datetime

from gbpbot.ai.base import LLMProvider
from gbpbot.utils.logger import setup_logger

# Configurer le logger
logger = setup_logger("ClaudeClient", logging.INFO)

class ClaudeClient(LLMProvider):
    """
    Client pour l'API Claude 3.7 d'Anthropic, optimisé pour les analyses de trading crypto
    et les décisions automatisées pour GBPBot.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialise le client Claude avec la configuration spécifiée.
        
        Args:
            config: Configuration du client Claude (clé API, modèle, etc.)
        """
        self.config = config or {}
        self.api_key = self.config.get("api_key") or os.environ.get("CLAUDE_API_KEY")
        self.model = self.config.get("model") or os.environ.get("CLAUDE_MODEL", "claude-3-7-sonnet-20240229")
        
        if not self.api_key:
            logger.warning("Aucune clé API Claude trouvée. Définissez CLAUDE_API_KEY ou fournissez-la via config.")
        
        self.base_url = "https://api.anthropic.com/v1"
        self.max_tokens = self.config.get("max_tokens", 4096)
        self.temperature = self.config.get("temperature", 0.7)
        
        # Cache pour les embeddings et les réponses
        self.cache = {}
        self.session = None
    
    async def _ensure_session(self):
        """Assure qu'une session aiohttp est disponible"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            })
    
    async def close(self):
        """Ferme proprement la session"""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
    
    async def generate_text(
        self, 
        prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        system_message: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Génère une réponse de texte à partir d'un prompt donné en utilisant Claude 3.7.
        
        Args:
            prompt: Le prompt à envoyer à Claude
            max_tokens: Nombre maximum de tokens dans la réponse
            temperature: Contrôle de la randomisation (0-1)
            system_message: Message système optionnel pour guider Claude
            
        Returns:
            Texte généré par Claude
        """
        await self._ensure_session()
        
        if not self.api_key:
            raise ValueError("Clé API Claude manquante")
        
        # Préparer la requête
        system = system_message or "You are an AI assistant specialized in cryptocurrency trading, blockchain analysis, and market predictions. Provide concise, actionable insights."
        
        payload = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system,
            "messages": [{"role": "user", "content": prompt}]
        }
        
        # Effectuer la requête
        try:
            start_time = datetime.now()
            async with self.session.post(f"{self.base_url}/messages", json=payload) as response:
                response_data = await response.json()
                
            # Calculer le temps de réponse
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.debug(f"Réponse Claude reçue en {elapsed:.2f}s")
            
            if "content" in response_data and len(response_data["content"]) > 0:
                return response_data["content"][0]["text"]
            else:
                logger.error(f"Format de réponse Claude inattendu: {response_data}")
                return ""
                
        except Exception as e:
            logger.error(f"Erreur lors de la génération de texte avec Claude: {str(e)}")
            return f"Erreur: {str(e)}"
    
    async def analyze_code(
        self,
        code: str,
        task: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Analyse un morceau de code pour une tâche spécifique en utilisant Claude
        
        Args:
            code: Code à analyser
            task: Description de la tâche d'analyse
            kwargs: Paramètres supplémentaires
            
        Returns:
            Résultats de l'analyse
        """
        prompt = f"""
        Analysez le code suivant selon la tâche demandée : {task}
        
        ```
        {code}
        ```
        
        Fournissez une analyse détaillée qui inclut :
        1. Un résumé de ce que fait le code
        2. Les problèmes potentiels, bugs ou vulnérabilités
        3. Des suggestions d'amélioration spécifiques
        4. Une évaluation globale
        
        Répondez en JSON structuré avec les clés suivantes :
        - "summary": résumé du code
        - "issues": liste des problèmes détectés
        - "improvements": liste des améliorations proposées
        - "rating": note globale sur 10
        """
        
        system_message = "Vous êtes un expert en revue de code spécialisé dans les applications blockchain et de trading. Analysez le code avec précision et fournissez des conseils pratiques."
        
        try:
            response = await self.generate_text(
                prompt=prompt,
                system_message=system_message,
                temperature=0.3,
                **kwargs
            )
            
            # Extraire le JSON de la réponse
            import re
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response)
            if json_match:
                analysis = json.loads(json_match.group(1))
            else:
                # Chercher une structure JSON directement
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    analysis = json.loads(response[json_start:json_end])
                else:
                    logger.warning(f"Impossible de parser un JSON valide de la réponse: {response[:200]}...")
                    analysis = {
                        "summary": "Erreur de parsing de la réponse",
                        "issues": ["Format de réponse non reconnu"],
                        "improvements": [],
                        "rating": 0
                    }
            
            return analysis
            
        except json.JSONDecodeError as e:
            logger.error(f"Erreur de décodage JSON: {str(e)}")
            return {
                "error": "Erreur de décodage JSON",
                "raw_response": response if 'response' in locals() else "Aucune réponse"
            }
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse du code: {str(e)}")
            return {"error": str(e)}
    
    async def get_token_score(
        self,
        token_data: Dict[str, Any],
        **kwargs
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Évalue un token crypto et lui attribue un score basé sur son potentiel et ses risques
        
        Args:
            token_data: Données du token à évaluer
            kwargs: Paramètres supplémentaires
            
        Returns:
            Tuple (score, détails) où score est entre 0 et 100
        """
        # Prompt pour l'évaluation du token
        token_symbol = token_data.get("symbol", "")
        chain = token_data.get("chain", "")
        
        prompt = f"""
        Évaluez le token {token_symbol} sur {chain or 'blockchain inconnue'} pour déterminer son potentiel de profit et ses risques.
        
        Voici les données disponibles sur ce token :
        ```json
        {json.dumps(token_data, indent=2)}
        ```
        
        Veuillez fournir :
        1. Un score global entre 0 et 100 (où 100 est le meilleur)
        2. Une analyse détaillée des forces et faiblesses
        3. Une évaluation des risques (rug pull, honeypot, etc.)
        4. Une recommandation de trading (achat, vente, attente)
        
        Votre réponse doit être en JSON structuré avec les clés suivantes :
        - "score": le score numérique (0-100)
        - "analysis": analyse textuelle détaillée
        - "strengths": liste des points forts
        - "weaknesses": liste des points faibles
        - "risks": évaluation des risques
        - "recommendation": recommandation de trading
        - "confidence": niveau de confiance dans cette évaluation (0-100)
        """
        
        system_message = "Vous êtes un analyste crypto expert, spécialisé dans l'évaluation des tokens et la détection des arnaques. Votre objectif est de fournir une analyse objective et précise pour guider les décisions de trading."
        
        try:
            # Générer l'évaluation
            response = await self.generate_text(
                prompt=prompt,
                system_message=system_message,
                temperature=0.2,  # Basse température pour plus de précision
                **kwargs
            )
            
            # Extraire le JSON
            import re
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response)
            if json_match:
                analysis = json.loads(json_match.group(1))
            else:
                # Chercher une structure JSON directement
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    analysis = json.loads(response[json_start:json_end])
                else:
                    logger.warning(f"Format de réponse inattendu: {response[:200]}...")
                    analysis = {"score": 0, "error": "Format invalide", "raw_response": response}
            
            # Extraire le score et s'assurer qu'il est dans la plage 0-100
            score = float(analysis.get("score", 0))
            score = max(0, min(100, score))  # Limiter entre 0 et 100
            
            return score, analysis
            
        except json.JSONDecodeError as e:
            logger.error(f"Erreur de décodage JSON: {str(e)}")
            return 0, {"error": "Erreur de décodage JSON", "raw_response": response if 'response' in locals() else ""}
        except Exception as e:
            logger.error(f"Erreur lors de l'évaluation du token: {str(e)}")
            return 0, {"error": str(e)}
    
    async def analyze_market_trend(
        self,
        market_data: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """
        Analyse les tendances du marché crypto à partir des données fournies
        
        Args:
            market_data: Données du marché à analyser
            kwargs: Paramètres supplémentaires
            
        Returns:
            Analyse des tendances du marché
        """
        # Construire un prompt adapté pour l'analyse du marché
        prompt = f"""
        Analysez les données de marché crypto suivantes pour déterminer les tendances actuelles :
        
        ```json
        {json.dumps(market_data, indent=2)}
        ```
        
        Votre analyse doit inclure :
        1. Tendance générale du marché (haussière, baissière, neutre)
        2. Mouvements significatifs récents et leur impact
        3. Opportunités d'arbitrage entre plateformes
        4. Tokens et secteurs à surveiller
        5. Prédiction à court terme (24-48h)
        6. Indicateurs techniques pertinents
        
        Répondez en JSON structuré avec les clés suivantes :
        - "trend": tendance générale ("bullish", "bearish", "neutral")
        - "market_analysis": analyse textuelle détaillée
        - "opportunities": liste des opportunités identifiées
        - "tokens_to_watch": liste des tokens à surveiller
        - "short_term_prediction": prédiction à court terme
        - "confidence": niveau de confiance (0-100)
        """
        
        system_message = "Vous êtes un analyste de marché crypto expérimenté. Fournissez une analyse objective basée uniquement sur les données fournies. Évitez les spéculations infondées et concentrez-vous sur les faits et indicateurs concrets."
        
        try:
            # Générer l'analyse
            response = await self.generate_text(
                prompt=prompt,
                system_message=system_message,
                temperature=0.4,
                **kwargs
            )
            
            # Extraire le JSON de la réponse
            import re
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response)
            if json_match:
                analysis = json.loads(json_match.group(1))
            else:
                # Chercher une structure JSON directement
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    analysis = json.loads(response[json_start:json_end])
                else:
                    logger.warning(f"Impossible de parser un JSON valide de la réponse: {response[:200]}...")
                    analysis = {
                        "trend": "neutral",
                        "market_analysis": "Erreur d'analyse",
                        "error": "Format de réponse non reconnu",
                        "raw_response": response
                    }
            
            return analysis
            
        except json.JSONDecodeError as e:
            logger.error(f"Erreur de décodage JSON: {str(e)}")
            return {"error": "Erreur de décodage JSON", "raw_response": response if 'response' in locals() else ""}
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse du marché: {str(e)}")
            return {"error": str(e)}
    
    @property
    def provider_name(self) -> str:
        """Nom du fournisseur d'IA"""
        return "claude"
    
    @property
    def is_available(self) -> bool:
        """Vérifie si le client Claude est disponible"""
        return bool(self.api_key)
    
    @property
    def capabilities(self) -> Dict[str, bool]:
        """Capacités du modèle Claude"""
        return {
            "text_generation": True,
            "market_analysis": True,
            "token_scoring": True,
            "web_search": False,  # Nécessite une intégration séparée
            "code_analysis": True,
            "embeddings": False  # Claude n'a pas d'API d'embeddings native
        }

# Fonction utilitaire pour créer un client Claude
async def create_claude_client(config: Optional[Dict[str, Any]] = None) -> ClaudeClient:
    """
    Crée et initialise un client Claude.
    
    Args:
        config: Configuration optionnelle
        
    Returns:
        Client Claude initialisé
    """
    client = ClaudeClient(config)
    return client 