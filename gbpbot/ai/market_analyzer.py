#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module d'analyse de marché basé sur l'IA pour GBPBot
===================================================

Ce module fournit des fonctionnalités d'analyse de marché utilisant l'IA
pour étudier les données du marché, détecter les patterns de prix,
prédire les mouvements de prix et scorer les tokens.
"""

import os
import json
import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime, timedelta

# Configurer le logging
logger = logging.getLogger("gbpbot.ai.market_analyzer")

from gbpbot.ai.llm_provider import LLMProvider
from gbpbot.ai.prompt_manager import get_prompt_manager

class MarketAnalyzer:
    """
    Classe d'analyse de marché utilisant l'IA pour étudier les données du marché,
    détecter les patterns de prix, prédire les mouvements de prix et scorer les tokens.
    
    Cette classe utilise des modèles de langage pour analyser les données de marché
    et fournir des insights sur les tendances, les opportunités et les risques.
    """
    
    def __init__(self, ai_client: LLMProvider, config: Optional[Dict[str, Any]] = None):
        """
        Initialise l'analyseur de marché
        
        Args:
            ai_client: Client IA à utiliser pour l'analyse
            config: Configuration spécifique pour l'analyseur
        """
        logger.info("Initialisation de l'analyseur de marché")
        self.ai_client = ai_client
        self.config = config or {}
        self.prompt_manager = get_prompt_manager()
        
        # Initialiser les caches pour optimiser les performances avec typing
        self.market_analysis_cache: Dict[str, Tuple[Dict[str, Any], datetime]] = {}
        self.token_analysis_cache: Dict[str, Tuple[Dict[str, Any], datetime]] = {}
        self.pattern_detection_cache: Dict[str, Tuple[List[Dict[str, Any]], datetime]] = {}
        self.contract_analysis_cache: Dict[str, Tuple[Dict[str, Any], datetime]] = {}
        
        # Charger les templates de prompts
        self._load_prompt_templates()
        
    def _load_prompt_templates(self) -> None:
        """Charge les templates de prompts depuis les fichiers"""
        try:
            # Tenter de charger depuis le prompt_manager
            market_template = self.prompt_manager.format_prompt("market_analysis")
            token_template = self.prompt_manager.format_prompt("token_analysis")
            contract_template = self.prompt_manager.format_prompt("contract_analysis")
            
            # Si les templates ne sont pas disponibles, utiliser les templates par défaut
            self.market_analysis_template = market_template or """
            Analyser les conditions actuelles du marché à partir des données suivantes:
            {market_data}
            
            Format de réponse:
            {{
                "market_sentiment": "bullish/bearish/neutral",
                "key_indicators": ["indicateur 1", "indicateur 2", ...],
                "opportunities": ["opportunité 1", "opportunité 2", ...],
                "risks": ["risque 1", "risque 2", ...],
                "recommendation": "description détaillée de la recommandation"
            }}
            """
            
            self.token_analysis_template = token_template or """
            Analyser le token suivant en examinant les données fournies:
            {token_data}
            
            Format de réponse:
            {{
                "token_name": "nom du token",
                "potential_score": nombre de 0 à 100,
                "risk_score": nombre de 0 à 100,
                "strengths": ["force 1", "force 2", ...],
                "weaknesses": ["faiblesse 1", "faiblesse 2", ...],
                "recommendation": "acheter/vendre/conserver",
                "explanation": "explication détaillée de l'analyse"
            }}
            """
            
            self.code_analysis_template = contract_template or """
            Analyser le contrat intelligent suivant pour détecter les risques potentiels:
            {contract_code}
            
            Format de réponse:
            {{
                "security_score": nombre de 0 à 100,
                "rug_pull_risk": nombre de 0 à 100,
                "honeypot_risk": nombre de 0 à 100,
                "issues": ["problème 1", "problème 2", ...],
                "high_risk_functions": ["fonction 1", "fonction 2", ...],
                "recommendation": "investir/éviter/prudence",
                "explanation": "explication détaillée des problèmes et risques"
            }}
            """
            
            logger.debug("Templates de prompts chargés avec succès")
        except Exception as e:
            logger.error(f"Erreur lors du chargement des templates: {e}")
            # Si erreur, utiliser des templates par défaut
            self.market_analysis_template = """Analyser le marché: {market_data}"""
            self.token_analysis_template = """Analyser le token: {token_data}"""
            self.code_analysis_template = """Analyser le contrat: {contract_code}"""
            
    async def analyze_market_conditions(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyse les conditions actuelles du marché en utilisant l'IA
        
        Args:
            market_data: Données du marché à analyser
            
        Returns:
            Résultat de l'analyse sous forme de dictionnaire
        """
        logger.info("Analyse des conditions du marché")
        
        # Vérifier le cache (max 15 minutes)
        cache_key = str(market_data.get("timestamp", ""))
        if cache_key in self.market_analysis_cache:
            cached_result, timestamp = self.market_analysis_cache[cache_key]
            if datetime.now() - timestamp < timedelta(minutes=15):
                logger.info("Utilisation du cache pour l'analyse du marché")
                return cached_result
        
        try:
            # Préparer le prompt
            prompt = self.market_analysis_template.format(
                market_data=json.dumps(market_data, indent=2)
            )
            
            # Analyser avec l'IA
            response = self.ai_client.generate_text(prompt)
            
            # Extraire et parser le JSON
            try:
                result = self._extract_json_from_response(response)
            except Exception as e:
                logger.error(f"Erreur lors du parsing du JSON: {e}")
                # Faire une analyse simplifiée en fallback
                result = self._fallback_market_analysis(market_data)
            
            # Mettre en cache
            self.market_analysis_cache[cache_key] = (result, datetime.now())
            
            return result
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse du marché: {e}")
            return self._fallback_market_analysis(market_data)
    
    async def analyze_token(self, token_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyse un token spécifique en utilisant l'IA
        
        Args:
            token_data: Données du token à analyser
            
        Returns:
            Résultat de l'analyse sous forme de dictionnaire
        """
        logger.info(f"Analyse du token {token_data.get('symbol', 'inconnu')}")
        
        # Vérifier le cache (max 30 minutes)
        cache_key = f"{token_data.get('symbol', '')}-{token_data.get('price', '')}"
        if cache_key in self.token_analysis_cache:
            cached_result, timestamp = self.token_analysis_cache[cache_key]
            if datetime.now() - timestamp < timedelta(minutes=30):
                logger.info("Utilisation du cache pour l'analyse du token")
                return cached_result
        
        try:
            # Préparer le prompt
            prompt = self.token_analysis_template.format(
                token_data=json.dumps(token_data, indent=2)
            )
            
            # Analyser avec l'IA
            response = await self.ai_client.generate_text(prompt)
            
            # Extraire et parser le JSON
            try:
                result = self._extract_json_from_response(response)
            except Exception as e:
                logger.error(f"Erreur lors du parsing du JSON: {e}")
                # Faire une analyse simplifiée en fallback
                result = self._fallback_token_analysis(token_data)
            
            # Mettre en cache
            self.token_analysis_cache[cache_key] = (result, datetime.now())
            
            return result
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse du token: {e}")
            return self._fallback_token_analysis(token_data)
    
    async def analyze_contract(self, contract_code: str, token_symbol: str = "") -> Dict[str, Any]:
        """
        Analyse un contrat intelligent en utilisant l'IA pour détecter les vulnérabilités
        
        Args:
            contract_code: Code du contrat à analyser
            token_symbol: Symbole du token (optionnel)
            
        Returns:
            Résultat de l'analyse sous forme de dictionnaire
        """
        logger.info(f"Analyse du contrat pour {token_symbol or 'token inconnu'}")
        
        # Vérifier le cache (max 1 heure)
        cache_key = f"{token_symbol}-{hash(contract_code)}"
        if cache_key in self.contract_analysis_cache:
            cached_result, timestamp = self.contract_analysis_cache[cache_key]
            if datetime.now() - timestamp < timedelta(hours=1):
                logger.info("Utilisation du cache pour l'analyse du contrat")
                return cached_result
        
        try:
            # Limiter la taille du contrat pour éviter de dépasser les limites de l'IA
            contract_code_limited = contract_code[:20000] if len(contract_code) > 20000 else contract_code
            
            # Préparer le prompt
            prompt = self.code_analysis_template.format(
                contract_code=contract_code_limited
            )
            
            # Analyser avec l'IA
            response = await self.ai_client.analyze_code(code=contract_code_limited)
            
            # Extraire et parser le JSON
            try:
                result = self._extract_json_from_response(response)
            except Exception as e:
                logger.error(f"Erreur lors du parsing du JSON: {e}")
                # Faire une analyse simplifiée en fallback
                result = self._fallback_contract_analysis(token_symbol)
            
            # Mettre en cache
            self.contract_analysis_cache[cache_key] = (result, datetime.now())
            
            return result
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse du contrat: {e}")
            return self._fallback_contract_analysis(token_symbol)
    
    async def predict_price_movement(self, token_data: Dict[str, Any], timeframe_hours: int = 24) -> Dict[str, Any]:
        """
        Prédit le mouvement de prix d'un token sur une période donnée
        
        Args:
            token_data: Données du token à analyser
            timeframe_hours: Horizon de prédiction en heures
            
        Returns:
            Prédiction sous forme de dictionnaire
        """
        logger.info(f"Prédiction du prix pour {token_data.get('symbol', 'inconnu')} sur {timeframe_hours}h")
        
        try:
            # Combiner avec l'analyse du token pour plus de contexte
            token_analysis = await self.analyze_token(token_data)
            
            # Créer un prompt spécifique pour la prédiction
            prompt = f"""
            En te basant sur les données du token suivant et ton analyse:
            
            Token: {token_data.get('name')} ({token_data.get('symbol')})
            Prix actuel: ${token_data.get('price'):,.6f}
            Variation 24h: {token_data.get('change_24h')}%
            Variation 7j: {token_data.get('change_7d')}%
            Volume 24h: ${token_data.get('volume_24h'):,.0f}
            
            Ton analyse précédente:
            Tendance: {token_analysis.get('trend')}
            Opportunité: {token_analysis.get('opportunity_rating')}/10
            Risque: {token_analysis.get('risk_rating')}/10
            
            Prédis le mouvement de prix pour les prochaines {timeframe_hours} heures.
            
            Format de réponse:
            {{
                "direction": "hausse/baisse/stable",
                "estimated_change_percent": 0-100,
                "confidence_level": 0-100,
                "key_factors": ["facteur 1", "facteur 2", ...],
                "risk_factors": ["risque 1", "risque 2", ...],
                "detailed_prediction": "description détaillée de la prédiction"
            }}
            """
            
            # Analyser avec l'IA
            response = await self.ai_client.generate_text(prompt)
            
            # Extraire et parser le JSON
            try:
                result = self._extract_json_from_response(response)
            except Exception as e:
                logger.error(f"Erreur lors du parsing du JSON: {e}")
                # Faire une prédiction simplifiée en fallback
                result = {
                    "direction": "stable",
                    "estimated_change_percent": 0,
                    "confidence_level": 30,
                    "key_factors": ["Données insuffisantes"],
                    "risk_factors": ["Prédiction non fiable"],
                    "detailed_prediction": "Impossible de générer une prédiction précise."
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Erreur lors de la prédiction de prix: {e}")
            return {
                "direction": "stable",
                "estimated_change_percent": 0,
                "confidence_level": 30,
                "key_factors": ["Erreur d'analyse"],
                "risk_factors": ["Prédiction non fiable"],
                "detailed_prediction": f"Erreur lors de l'analyse: {str(e)}"
            }
    
    async def generate_market_report(self) -> Dict[str, Any]:
        """
        Génère un rapport complet sur l'état du marché
        
        Returns:
            Rapport sous forme de dictionnaire
        """
        logger.info("Génération d'un rapport de marché")
        # À implémenter selon les besoins
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "en cours d'implémentation"
        }
    
    def _extract_json_from_response(self, response: str) -> Dict[str, Any]:
        """
        Extrait un objet JSON d'une réponse textuelle
        
        Args:
            response: Réponse textuelle contenant du JSON
            
        Returns:
            Objet JSON extrait
        """
        # Chercher le début et la fin du JSON
        start_idx = response.find('{')
        end_idx = response.rfind('}') + 1
        
        if start_idx >= 0 and end_idx > start_idx:
            json_str = response[start_idx:end_idx]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                # Essayer de nettoyer le JSON
                cleaned_json = self._clean_json_string(json_str)
                return json.loads(cleaned_json)
        
        raise ValueError("Aucun JSON valide trouvé dans la réponse")
    
    def _clean_json_string(self, json_str: str) -> str:
        """
        Nettoie une chaîne JSON potentiellement mal formée
        
        Args:
            json_str: Chaîne JSON à nettoyer
            
        Returns:
            Chaîne JSON nettoyée
        """
        # Remplacer les single quotes par des double quotes
        json_str = json_str.replace("'", '"')
        
        # Supprimer les commentaires éventuels
        lines = json_str.split('\n')
        cleaned_lines = []
        for line in lines:
            if '//' in line:
                line = line[:line.index('//')]
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def _fallback_market_analysis(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Génère une analyse de marché simplifiée en cas d'échec de l'IA
        
        Args:
            market_data: Données du marché
            
        Returns:
            Analyse simplifiée
        """
        logger.info("Utilisation de l'analyse de marché fallback")
        
        # Déterminer la tendance en fonction du fear & greed index
        fear_greed = market_data.get("fear_greed_index", 50)
        if fear_greed >= 70:
            trend = "haussier"
            risk_level = "élevé"
        elif fear_greed <= 30:
            trend = "baissier"
            risk_level = "moyen"
        else:
            trend = "neutre"
            risk_level = "moyen"
        
        # Examiner les tokens en tendance
        trending_tokens = market_data.get("trending_tokens", [])
        positive_trends = sum(1 for t in trending_tokens if t.get("change_24h", 0) > 0)
        negative_trends = len(trending_tokens) - positive_trends
        
        if positive_trends > negative_trends:
            # Tendance positive
            key_indicators = ["Majorité des tokens en hausse", "Sentiment de marché positif"]
            recommendations = ["Surveiller les opportunités d'achat", "Rester vigilant sur les signes de retournement"]
        else:
            # Tendance négative
            key_indicators = ["Majorité des tokens en baisse", "Sentiment de marché négatif"]
            recommendations = ["Prudence dans les achats", "Attendre des signaux de rebond"]
        
        return {
            "trend": trend,
            "confidence_level": 60,
            "key_indicators": key_indicators,
            "patterns": ["Analyse simplifiée en mode dégradé"],
            "short_term_prediction": "Analyse simplifiée disponible uniquement en mode dégradé.",
            "recommendations": recommendations,
            "risk_level": risk_level
        }
    
    def _fallback_token_analysis(self, token_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Génère une analyse de token simplifiée en cas d'échec de l'IA
        
        Args:
            token_data: Données du token
            
        Returns:
            Analyse simplifiée
        """
        logger.info("Utilisation de l'analyse de token fallback")
        
        # Calcul basique basé sur les changements de prix
        change_24h = token_data.get("change_24h", 0)
        change_7d = token_data.get("change_7d", 0)
        
        # Déterminer la tendance
        if change_24h > 5 and change_7d > 10:
            trend = "fortement haussier"
            opportunity_rating = 8
            strengths = ["Forte dynamique haussière", "Momentum positif"]
            weaknesses = ["Risque de correction après la hausse"]
            recommendation = "Ce token montre une forte dynamique positive. Considérer des prises de profit partielles pour sécuriser les gains."
        elif change_24h > 0 and change_7d > 0:
            trend = "haussier"
            opportunity_rating = 6
            strengths = ["Tendance positive", "Stabilité du prix"]
            weaknesses = ["Hausse modérée, potentiel limité à court terme"]
            recommendation = "Ce token montre une tendance positive stable. Surveiller pour des opportunités d'achat sur les dips."
        elif change_24h < -5 and change_7d < -10:
            trend = "fortement baissier"
            opportunity_rating = 3
            strengths = ["Possible opportunité d'achat si le marché se stabilise"]
            weaknesses = ["Forte tendance baissière", "Pourrait continuer à baisser"]
            recommendation = "Ce token est en forte baisse. Attendre des signes de stabilisation avant d'envisager un achat."
        elif change_24h < 0 and change_7d < 0:
            trend = "baissier"
            opportunity_rating = 4
            strengths = ["Possible opportunité d'achat si la tendance s'inverse"]
            weaknesses = ["Tendance négative actuelle"]
            recommendation = "Ce token montre une tendance négative. Surveiller les niveaux de support pour d'éventuelles opportunités d'achat."
        else:
            trend = "neutre"
            opportunity_rating = 5
            strengths = ["Relative stabilité du prix"]
            weaknesses = ["Manque de direction claire"]
            recommendation = "Ce token montre une tendance neutre. Surveiller les développements du projet et les catalyseurs potentiels."
        
        # Calculer le risque en fonction du contexte
        if "meme" in token_data.get("name", "").lower() or token_data.get("market_cap", 1e9) < 100e6:
            risk_rating = 8
            weaknesses.append("Risque élevé typique des memecoins ou petite capitalisation")
        else:
            risk_rating = 6
            
        return {
            "trend": trend,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "opportunity_rating": opportunity_rating,
            "risk_rating": risk_rating,
            "recommendation": recommendation
        }
    
    def _fallback_contract_analysis(self, token_symbol: str) -> Dict[str, Any]:
        """
        Génère une analyse de contrat simplifiée en cas d'échec de l'IA
        
        Args:
            token_symbol: Symbole du token
            
        Returns:
            Analyse simplifiée
        """
        logger.info("Utilisation de l'analyse de contrat fallback")
        
        return {
            "security_issues": [
                {"severity": "inconnue", "description": "Analyse automatique non disponible", "location": "N/A"}
            ],
            "risk_assessment": "Impossible d'évaluer les risques du contrat sans analyse complète",
            "recommendation": "prudence"
        }

def create_market_analyzer(ai_client: Optional[LLMProvider] = None, config: Optional[Dict[str, Any]] = None) -> MarketAnalyzer:
    """
    Crée une instance de MarketAnalyzer.
    
    Args:
        ai_client: Client IA à utiliser pour l'analyse
        config: Configuration optionnelle
        
    Returns:
        Une instance de MarketAnalyzer
    """
    if ai_client is None:
        logger.warning("Aucun client IA fourni, certaines fonctionnalités seront limitées")
    
    return MarketAnalyzer(ai_client, config) 