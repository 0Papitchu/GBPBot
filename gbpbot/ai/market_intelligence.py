"""
Module d'intelligence de marché pour GBPBot
Combine Claude 3.7 avec la recherche web pour des analyses avancées
"""

import json
import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

from gbpbot.ai import create_ai_client
from gbpbot.ai.web_search import create_web_search_provider
from gbpbot.utils.logger import setup_logger

logger = setup_logger("MarketIntelligence", logging.INFO)

class MarketIntelligence:
    """
    Système d'intelligence de marché qui combine:
    - Analyse IA avancée avec Claude 3.7
    - Recherche web en temps réel
    - Apprentissage continu à partir des résultats passés
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialise le système d'intelligence de marché
        
        Args:
            config: Configuration optionnelle
        """
        self.config = config or {}
        self.ai_client = None
        self.web_search = None
        self.initialized = False
        
        # Historique d'analyses pour apprentissage
        self.analysis_history = []
        # Limiter l'historique à 100 entrées maximum
        self.max_history_entries = self.config.get("max_history_entries", 100)
    
    async def initialize(self):
        """Initialise les clients IA et recherche web"""
        if not self.initialized:
            self.ai_client = await create_ai_client(
                provider=self.config.get("ai_provider", "claude"),
                config=self.config.get("ai_config")
            )
            
            self.web_search = await create_web_search_provider(
                config=self.config.get("web_search_config")
            )
            
            self.initialized = True
            logger.info("Système d'intelligence de marché initialisé")
    
    async def close(self):
        """Ferme proprement les clients"""
        if self.ai_client:
            await self.ai_client.close()
        if self.web_search:
            await self.web_search.close()
    
    async def analyze_token(
        self, 
        token_symbol: str, 
        chain: str = None,
        with_web_search: bool = True
    ) -> Dict[str, Any]:
        """
        Analyse complète d'un token avec recherche web et IA
        
        Args:
            token_symbol: Symbole du token
            chain: Blockchain du token
            with_web_search: Activer la recherche web
            
        Returns:
            Analyse complète du token
        """
        if not self.initialized:
            await self.initialize()
        
        # Collecter les données
        token_data = {"symbol": token_symbol, "chain": chain}
        
        # Ajouter des informations web si demandé
        if with_web_search and self.web_search:
            try:
                web_info = await self.web_search.get_token_info(token_symbol, chain)
                token_data["web_info"] = web_info
            except Exception as e:
                logger.warning(f"Erreur lors de la recherche web pour {token_symbol}: {str(e)}")
        
        # Analyse IA avec Claude 3.7
        try:
            # Enrichir le prompt avec les informations web
            enriched_prompt = self._create_token_analysis_prompt(token_data)
            
            # Générer l'analyse
            raw_analysis = await self.ai_client.generate_text(
                prompt=enriched_prompt,
                temperature=0.3,
                system_message="Vous êtes un expert en analyse de crypto-monnaies spécialisé dans la détection d'opportunités de trading. Fournissez une analyse complète basée sur les données fournies et votre connaissance des marchés. Répondez en format JSON structuré."
            )
            
            # Extraire et nettoyer l'analyse
            analysis = self._extract_json_from_text(raw_analysis)
            
            # Calculer le score du token
            score, score_details = await self.ai_client.get_token_score(token_data)
            analysis["score"] = score
            analysis["score_details"] = score_details
            
            # Ajouter à l'historique
            self._add_to_history("token_analysis", {
                "token": token_symbol,
                "chain": chain,
                "timestamp": datetime.now().isoformat(),
                "score": score,
                "analysis": analysis
            })
            
            return analysis
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse du token {token_symbol}: {str(e)}")
            return {
                "error": f"Analyse échouée: {str(e)}",
                "token": token_symbol,
                "timestamp": datetime.now().isoformat()
            }
    
    async def analyze_market(
        self,
        keywords: List[str] = None,
        with_web_search: bool = True
    ) -> Dict[str, Any]:
        """
        Analyse du marché global avec recherche web et IA
        
        Args:
            keywords: Mots-clés pour cibler l'analyse
            with_web_search: Activer la recherche web
            
        Returns:
            Analyse complète du marché
        """
        if not self.initialized:
            await self.initialize()
        
        # Collecter les données
        market_data = {"keywords": keywords or []}
        
        # Ajouter des informations web si demandé
        if with_web_search and self.web_search:
            try:
                market_news = await self.web_search.get_market_news(keywords)
                market_data["news"] = market_news
            except Exception as e:
                logger.warning(f"Erreur lors de la recherche d'actualités: {str(e)}")
        
        # Analyse IA avec Claude 3.7
        try:
            # Enrichir le prompt avec les informations web
            enriched_prompt = self._create_market_analysis_prompt(market_data)
            
            # Générer l'analyse
            raw_analysis = await self.ai_client.generate_text(
                prompt=enriched_prompt,
                temperature=0.4,
                system_message="Vous êtes un expert en analyse de marchés crypto. Fournissez une analyse profonde des conditions actuelles du marché et des opportunités potentielles. Répondez en format JSON structuré."
            )
            
            # Extraire et nettoyer l'analyse
            analysis = self._extract_json_from_text(raw_analysis)
            
            # Ajouter à l'historique
            self._add_to_history("market_analysis", {
                "keywords": keywords,
                "timestamp": datetime.now().isoformat(),
                "analysis": analysis
            })
            
            return analysis
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse du marché: {str(e)}")
            return {
                "error": f"Analyse échouée: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    async def generate_trading_strategy(
        self,
        token_symbol: str = None,
        chain: str = None,
        strategy_type: str = "auto",
        risk_profile: str = "balanced"
    ) -> Dict[str, Any]:
        """
        Génère une stratégie de trading adaptée pour un token ou le marché global
        
        Args:
            token_symbol: Symbole du token (optionnel)
            chain: Blockchain du token
            strategy_type: Type de stratégie ('sniping', 'arbitrage', 'auto')
            risk_profile: Profil de risque ('conservative', 'balanced', 'aggressive')
            
        Returns:
            Stratégie de trading détaillée
        """
        if not self.initialized:
            await self.initialize()
        
        # Analyse préalable du token ou du marché
        if token_symbol:
            analysis = await self.analyze_token(token_symbol, chain)
        else:
            analysis = await self.analyze_market()
        
        # Créer le prompt pour la génération de stratégie
        strategy_prompt = self._create_strategy_generation_prompt(
            analysis, 
            token_symbol=token_symbol,
            strategy_type=strategy_type,
            risk_profile=risk_profile
        )
        
        try:
            # Générer la stratégie
            raw_strategy = await self.ai_client.generate_text(
                prompt=strategy_prompt,
                temperature=0.5,
                system_message="Vous êtes un stratège de trading crypto expérimenté. Générez une stratégie de trading détaillée et actionnable, avec des paramètres précis et des critères d'entrée/sortie clairs. Répondez en format JSON structuré."
            )
            
            # Extraire et nettoyer la stratégie
            strategy = self._extract_json_from_text(raw_strategy)
            
            # Enrichir avec des métadonnées
            strategy["generated_at"] = datetime.now().isoformat()
            strategy["token"] = token_symbol
            strategy["chain"] = chain
            strategy["strategy_type"] = strategy_type
            strategy["risk_profile"] = risk_profile
            
            # Ajouter à l'historique
            self._add_to_history("strategy_generation", {
                "token": token_symbol,
                "strategy_type": strategy_type,
                "risk_profile": risk_profile,
                "timestamp": datetime.now().isoformat(),
                "strategy": strategy
            })
            
            return strategy
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération de stratégie: {str(e)}")
            return {
                "error": f"Génération de stratégie échouée: {str(e)}",
                "token": token_symbol,
                "timestamp": datetime.now().isoformat()
            }
    
    def _create_token_analysis_prompt(self, token_data: Dict[str, Any]) -> str:
        """
        Crée un prompt riche pour l'analyse d'un token
        
        Args:
            token_data: Données du token à analyser
            
        Returns:
            Prompt formaté
        """
        token_symbol = token_data.get("symbol", "")
        chain = token_data.get("chain", "")
        
        prompt = f"""
        Analysez en profondeur le token {token_symbol} sur {chain or 'toutes les blockchains'} 
        en vous basant sur les informations suivantes:
        
        ```json
        {json.dumps(token_data, indent=2)}
        ```
        
        Votre analyse doit inclure:
        1. Évaluation générale du token et son potentiel
        2. Risques potentiels (rug pull, honeypot, risques techniques)
        3. Opportunités à court et moyen terme
        4. Métriques clés (liquidité, volume, détenteurs)
        5. Recommandation de trading (acheter, vendre, attendre)
        6. Paramètres optimaux de trading (slippage, montant, timing)
        
        Fournissez un score global de 0 à 100 pour ce token et justifiez votre notation.
        Répondez avec un JSON structuré.
        """
        
        return prompt
    
    def _create_market_analysis_prompt(self, market_data: Dict[str, Any]) -> str:
        """
        Crée un prompt riche pour l'analyse du marché
        
        Args:
            market_data: Données du marché à analyser
            
        Returns:
            Prompt formaté
        """
        keywords = market_data.get("keywords", [])
        news = market_data.get("news", [])
        
        prompt = f"""
        Analysez les conditions actuelles du marché crypto
        """
        
        if keywords:
            prompt += f" en vous concentrant sur: {', '.join(keywords)}"
        
        prompt += """
        en vous basant sur les actualités et données récentes suivantes:
        
        Actualités récentes:
        """
        
        # Ajouter les actualités
        if news:
            for i, item in enumerate(news[:10], 1):
                prompt += f"""
                {i}. {item.get('title', '')}
                   Source: {item.get('url', '')}
                   Résumé: {item.get('summary', '')}
                """
        else:
            prompt += "Pas d'actualités spécifiques disponibles."
        
        prompt += """
        
        Votre analyse doit inclure:
        1. Tendance globale du marché (haussière, baissière, latérale)
        2. Mouvements significatifs récents et leur impact
        3. Opportunités d'arbitrage entre plateformes
        4. Zones potentielles pour le sniping de nouveaux tokens
        5. Recommandations générales de trading
        6. Prédiction à court terme (24-48h)
        
        Répondez avec un JSON structuré.
        """
        
        return prompt
    
    def _create_strategy_generation_prompt(
        self,
        analysis: Dict[str, Any],
        token_symbol: str = None,
        strategy_type: str = "auto",
        risk_profile: str = "balanced"
    ) -> str:
        """
        Crée un prompt pour la génération de stratégie
        
        Args:
            analysis: Analyse préalable
            token_symbol: Symbole du token
            strategy_type: Type de stratégie
            risk_profile: Profil de risque
            
        Returns:
            Prompt formaté
        """
        if token_symbol:
            prompt = f"""
            Générez une stratégie de trading optimale pour {token_symbol} 
            basée sur l'analyse suivante:
            
            ```json
            {json.dumps(analysis, indent=2)}
            ```
            """
        else:
            prompt = f"""
            Générez une stratégie de trading optimale pour le marché actuel
            basée sur l'analyse suivante:
            
            ```json
            {json.dumps(analysis, indent=2)}
            ```
            """
        
        # Ajouter des détails spécifiques au type de stratégie
        if strategy_type == "sniping":
            prompt += """
            Concentrez-vous sur une stratégie de sniping optimisée pour:
            - Détection rapide des nouveaux tokens à fort potentiel
            - Entrée optimale (timing, montant, slippage)
            - Critères de sortie clairs (take profit, stop loss)
            - Gestion de risque
            """
        elif strategy_type == "arbitrage":
            prompt += """
            Concentrez-vous sur une stratégie d'arbitrage optimisée pour:
            - Identification des écarts de prix entre plateformes
            - Calcul précis de la rentabilité (frais inclus)
            - Timing et exécution
            - Routes d'arbitrage optimales
            """
        else:  # auto
            prompt += """
            Déterminez le type de stratégie optimal (sniping, arbitrage, autre) 
            en fonction de l'analyse et fournissez des détails complets.
            """
        
        # Adapter selon le profil de risque
        if risk_profile == "conservative":
            prompt += """
            Adoptez un profil de risque conservateur avec:
            - Allocation de capital limitée (max 5% par trade)
            - Stop loss serré
            - Forte diversification
            - Critères de sélection stricts
            """
        elif risk_profile == "aggressive":
            prompt += """
            Adoptez un profil de risque agressif avec:
            - Allocation de capital plus importante (jusqu'à 20% par trade)
            - Stop loss plus large
            - Concentration sur les opportunités à fort potentiel
            - Utilisation de l'effet de levier si pertinent
            """
        else:  # balanced
            prompt += """
            Adoptez un profil de risque équilibré avec:
            - Allocation de capital modérée (8-12% par trade)
            - Stop loss raisonnable
            - Diversification ciblée
            - Combinaison d'opportunités à faible et fort risque
            """
        
        prompt += """
        Votre stratégie doit inclure:
        1. Paramètres précis d'entrée et sortie
        2. Allocation de capital recommandée
        3. Timing optimal d'exécution
        4. Gestion des risques
        5. Métriques à surveiller
        6. Conditions d'ajustement de la stratégie
        
        Répondez avec un JSON structuré contenant tous ces éléments.
        """
        
        return prompt
    
    def _extract_json_from_text(self, text: str) -> Dict[str, Any]:
        """
        Extrait et parse un JSON à partir d'une réponse textuelle
        
        Args:
            text: Texte contenant potentiellement du JSON
            
        Returns:
            Dictionnaire JSON extrait
        """
        try:
            # Essai 1: Chercher un bloc JSON entre ```json et ```
            import re
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', text)
            if json_match:
                return json.loads(json_match.group(1))
            
            # Essai 2: Chercher un bloc JSON entre ``` et ```
            json_match = re.search(r'```\s*([\s\S]*?)\s*```', text)
            if json_match:
                return json.loads(json_match.group(1))
            
            # Essai 3: Chercher des accolades pour extraire le JSON
            json_start = text.find('{')
            json_end = text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                return json.loads(text[json_start:json_end])
            
            # Si tout échoue, retourner le texte brut
            logger.warning(f"Impossible de parser un JSON valide de la réponse")
            return {"raw_text": text}
            
        except json.JSONDecodeError as e:
            logger.error(f"Erreur de décodage JSON: {str(e)}")
            return {"error": "JSON invalide", "raw_text": text}
    
    def _add_to_history(self, entry_type: str, entry_data: Dict[str, Any]):
        """
        Ajoute une entrée à l'historique d'analyses
        
        Args:
            entry_type: Type d'entrée (token_analysis, market_analysis, etc.)
            entry_data: Données de l'entrée
        """
        self.analysis_history.append({
            "type": entry_type,
            "timestamp": datetime.now().isoformat(),
            "data": entry_data
        })
        
        # Limiter la taille de l'historique
        if len(self.analysis_history) > self.max_history_entries:
            self.analysis_history = self.analysis_history[-self.max_history_entries:]

# Fonction utilitaire pour créer un système d'intelligence de marché
async def create_market_intelligence(config: Optional[Dict[str, Any]] = None) -> MarketIntelligence:
    """
    Crée et initialise un système d'intelligence de marché
    
    Args:
        config: Configuration optionnelle
        
    Returns:
        Système d'intelligence de marché initialisé
    """
    intelligence = MarketIntelligence(config)
    await intelligence.initialize()
    return intelligence 