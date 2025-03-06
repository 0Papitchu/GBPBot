#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analyseur de Marché basé sur l'IA
================================

Ce module utilise l'intelligence artificielle pour analyser les données du marché,
détecter des tendances et faire des prédictions pour informer les stratégies de trading.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime, timedelta

from gbpbot.ai import LLMProvider, get_prompt_manager
from gbpbot.ai.prompt_manager import PromptManager

# Configuration du logger
logger = logging.getLogger("gbpbot.ai.market_analyzer")

class MarketAnalyzer:
    """
    Analyseur de marché basé sur l'IA pour détecter des tendances et faire des prédictions.
    
    Cette classe combine les données du marché avec l'analyse par IA pour informer
    les décisions de trading et optimiser les stratégies.
    """
    
    def __init__(self, ai_client: LLMProvider, prompt_manager: Optional[PromptManager] = None):
        """
        Initialise l'analyseur de marché.
        
        Args:
            ai_client: Un client d'IA implémentant l'interface LLMProvider
            prompt_manager: Un gestionnaire de prompts (optionnel)
        """
        self.ai_client = ai_client
        self.prompt_manager = prompt_manager or get_prompt_manager()
        
        # Historique des analyses pour établir des patterns
        self.analysis_history = []
        self.max_history_size = 50  # Limiter la taille de l'historique
    
    def analyze_market_data(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyse les données du marché pour détecter des tendances et faire des prédictions.
        
        Args:
            market_data: Données du marché à analyser (prix, volumes, etc.)
            
        Returns:
            Analyse du marché avec tendances, signaux et prédictions
        """
        try:
            # Préparer les données pour l'analyse
            formatted_data = self._format_market_data(market_data)
            
            # Obtenir le template de prompt d'analyse de marché
            prompt = self.prompt_manager.format_prompt(
                "market_analysis",
                market_data=formatted_data
            )
            
            if not prompt:
                logger.error("Impossible de formater le prompt d'analyse de marché")
                return self._get_fallback_analysis()
            
            # Utiliser l'IA pour analyser les données
            ai_response = self.ai_client.generate_text(prompt)
            
            if not ai_response:
                logger.error("Pas de réponse de l'IA pour l'analyse de marché")
                return self._get_fallback_analysis()
            
            # Tenter de parser la réponse JSON
            try:
                # Vérifier si la réponse est déjà un dictionnaire ou s'il faut la parser
                if isinstance(ai_response, dict):
                    analysis = ai_response
                else:
                    analysis = json.loads(ai_response)
                
                # Stocker l'analyse dans l'historique
                self._update_analysis_history(analysis)
                
                return analysis
            
            except json.JSONDecodeError:
                logger.error("Impossible de décoder la réponse de l'IA comme JSON")
                # Extraire manuellement les informations si possible
                return self._extract_analysis_from_text(ai_response)
        
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse du marché: {e}")
            return self._get_fallback_analysis()
    
    def detect_pattern(self, token_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Détecte des patterns spécifiques dans les données d'un token.
        
        Args:
            token_data: Données historiques du token à analyser
            
        Returns:
            Patterns détectés avec leur probabilité et signaux associés
        """
        try:
            # Formatter les données du token pour l'analyse
            formatted_data = json.dumps(token_data, indent=2)
            
            # Créer un prompt spécifique pour la détection de patterns
            prompt = f"""
            Analyser les données suivantes d'un token pour détecter des patterns de trading:
            
            {formatted_data}
            
            Identifier les patterns (pump and dump, accumulation, distribution, etc.)
            et donner une évaluation de la prochaine tendance probable.
            Répondre UNIQUEMENT en format JSON structuré.
            """
            
            # Utiliser l'IA pour détecter des patterns
            ai_response = self.ai_client.generate_text(prompt)
            
            if not ai_response:
                logger.error("Pas de réponse de l'IA pour la détection de patterns")
                return {"patterns": [], "trend_prediction": "neutral", "confidence": 0.5}
            
            try:
                # Vérifier si la réponse est déjà un dictionnaire ou s'il faut la parser
                if isinstance(ai_response, dict):
                    pattern_analysis = ai_response
                else:
                    pattern_analysis = json.loads(ai_response)
                return pattern_analysis
            
            except json.JSONDecodeError:
                logger.error("Impossible de décoder la réponse de pattern comme JSON")
                return {"patterns": [], "trend_prediction": "neutral", "confidence": 0.5}
        
        except Exception as e:
            logger.error(f"Erreur lors de la détection de patterns: {e}")
            return {"patterns": [], "trend_prediction": "neutral", "confidence": 0.5}
    
    def evaluate_token_score(self, token_data: Dict[str, Any], contract_code: Optional[str] = None) -> float:
        """
        Évalue un score de confiance pour un token en combinant analyse technique et analyse du contrat.
        
        Args:
            token_data: Données du token (prix, volume, social metrics, etc.)
            contract_code: Code du contrat pour analyse de sécurité (optionnel)
            
        Returns:
            Score de confiance entre 0 et 1.0
        """
        try:
            # Analyser les données du token
            market_analysis = self.analyze_market_data({"token": token_data})
            market_score = self._extract_score_from_analysis(market_analysis)
            
            # Si le code du contrat est fourni, analyser le contrat
            contract_score = 0.5  # Score neutre par défaut
            if contract_code:
                contract_analysis = self._analyze_contract(contract_code)
                contract_score = self._extract_score_from_contract_analysis(contract_analysis)
            
            # Combiner les scores (70% market data, 30% contract si disponible)
            if contract_code:
                final_score = (market_score * 0.7) + (contract_score * 0.3)
            else:
                final_score = market_score
            
            return min(max(final_score, 0.0), 1.0)  # Limiter entre 0 et 1
        
        except Exception as e:
            logger.error(f"Erreur lors de l'évaluation du score du token: {e}")
            return 0.5  # Score neutre en cas d'erreur
    
    def predict_price_movement(self, token_data: Dict[str, Any], timeframe_hours: int = 24) -> Dict[str, Any]:
        """
        Prédit le mouvement de prix d'un token sur une période donnée.
        
        Args:
            token_data: Données historiques du token
            timeframe_hours: Période de prédiction en heures
            
        Returns:
            Prédiction avec direction, amplitude et niveau de confiance
        """
        try:
            # Formatter les données pour la prédiction
            formatted_data = json.dumps({
                "token_data": token_data,
                "timeframe_hours": timeframe_hours
            }, indent=2)
            
            # Créer un prompt pour la prédiction de prix
            prompt = f"""
            En tant qu'expert en trading de crypto-monnaies, analyser les données suivantes:
            
            {formatted_data}
            
            Prédire le mouvement de prix pour les prochaines {timeframe_hours} heures.
            Inclure: direction (up/down/sideways), pourcentage de changement estimé,
            niveau de confiance, et justification.
            Répondre UNIQUEMENT en format JSON.
            """
            
            # Utiliser l'IA pour la prédiction
            ai_response = self.ai_client.generate_text(prompt)
            
            if not ai_response:
                logger.error("Pas de réponse de l'IA pour la prédiction de prix")
                return self._get_fallback_prediction(timeframe_hours)
            
            try:
                # Vérifier si la réponse est déjà un dictionnaire ou s'il faut la parser
                if isinstance(ai_response, dict):
                    prediction = ai_response
                else:
                    prediction = json.loads(ai_response)
                return prediction
            
            except json.JSONDecodeError:
                logger.error("Impossible de décoder la réponse de prédiction comme JSON")
                return self._get_fallback_prediction(timeframe_hours)
        
        except Exception as e:
            logger.error(f"Erreur lors de la prédiction de mouvement de prix: {e}")
            return self._get_fallback_prediction(timeframe_hours)
    
    def _format_market_data(self, market_data: Dict[str, Any]) -> str:
        """
        Formatte les données du marché pour l'analyse par IA.
        
        Args:
            market_data: Données brutes du marché
            
        Returns:
            Données formatées en JSON pour l'IA
        """
        try:
            # Ajouter un horodatage pour le contexte
            market_data["timestamp"] = datetime.now().isoformat()
            
            # Formater en JSON avec indentation pour la lisibilité
            return json.dumps(market_data, indent=2)
        
        except Exception as e:
            logger.error(f"Erreur lors du formatage des données: {e}")
            return json.dumps({"error": "Données non formatables", "timestamp": datetime.now().isoformat()})
    
    def _extract_analysis_from_text(self, text: str) -> Dict[str, Any]:
        """
        Extrait les informations d'analyse à partir d'une réponse texte non-JSON.
        
        Args:
            text: Réponse texte de l'IA
            
        Returns:
            Analyse structurée extraite du texte
        """
        # Structure de base pour l'analyse
        analysis = {
            "trend": "unknown",
            "confidence": 0.5,
            "key_indicators": [],
            "patterns": [],
            "short_term_prediction": "neutral",
            "recommendations": [],
            "risk_level": "medium"
        }
        
        # Extraire la tendance
        if "bullish" in text.lower():
            analysis["trend"] = "bullish"
        elif "bearish" in text.lower():
            analysis["trend"] = "bearish"
        elif "neutral" in text.lower() or "sideways" in text.lower():
            analysis["trend"] = "neutral"
        
        # Extraire la prédiction
        if "will increase" in text.lower() or "will rise" in text.lower():
            analysis["short_term_prediction"] = "up"
        elif "will decrease" in text.lower() or "will fall" in text.lower():
            analysis["short_term_prediction"] = "down"
        
        # Tenter d'extraire d'autres informations clés
        # (Cette partie pourrait être améliorée avec une analyse plus sophistiquée)
        
        return analysis
    
    def _update_analysis_history(self, analysis: Dict[str, Any]) -> None:
        """
        Met à jour l'historique des analyses.
        
        Args:
            analysis: Nouvelle analyse à ajouter à l'historique
        """
        # Ajouter un horodatage si non présent
        if "timestamp" not in analysis:
            analysis["timestamp"] = datetime.now().isoformat()
        
        # Ajouter à l'historique
        self.analysis_history.append(analysis)
        
        # Limiter la taille de l'historique
        if len(self.analysis_history) > self.max_history_size:
            self.analysis_history = self.analysis_history[-self.max_history_size:]
    
    def _get_fallback_analysis(self) -> Dict[str, Any]:
        """
        Fournit une analyse par défaut en cas d'erreur.
        
        Returns:
            Analyse par défaut
        """
        return {
            "trend": "neutral",
            "confidence": 0.5,
            "key_indicators": [],
            "patterns": [],
            "short_term_prediction": "neutral",
            "recommendations": [
                "Attendre plus de données pour une analyse plus précise"
            ],
            "risk_level": "medium",
            "timestamp": datetime.now().isoformat(),
            "note": "Analyse par défaut (erreur de l'analyseur)"
        }
    
    def _get_fallback_prediction(self, timeframe_hours: int) -> Dict[str, Any]:
        """
        Fournit une prédiction par défaut en cas d'erreur.
        
        Args:
            timeframe_hours: Période de prédiction en heures
            
        Returns:
            Prédiction par défaut
        """
        return {
            "direction": "sideways",
            "change_percent": 0.0,
            "confidence": 0.5,
            "justification": "Prédiction par défaut en raison d'une erreur d'analyse",
            "timeframe_hours": timeframe_hours,
            "timestamp": datetime.now().isoformat()
        }
    
    def _analyze_contract(self, contract_code: str) -> Dict[str, Any]:
        """
        Analyse le code d'un contrat de token pour détecter des problèmes de sécurité.
        
        Args:
            contract_code: Code du contrat à analyser
            
        Returns:
            Analyse du contrat avec problèmes de sécurité détectés
        """
        try:
            # Obtenir le template de prompt d'analyse de contrat
            prompt = self.prompt_manager.format_prompt(
                "token_contract_analysis",
                contract_code=contract_code
            )
            
            if not prompt:
                logger.error("Impossible de formater le prompt d'analyse de contrat")
                return {"security_issues": [], "risk_assessment": "unknown"}
            
            # Utiliser l'IA pour analyser le contrat
            ai_response = self.ai_client.analyze_token_contract(contract_code)
            
            if not ai_response:
                logger.error("Pas de réponse de l'IA pour l'analyse de contrat")
                return {"security_issues": [], "risk_assessment": "unknown"}
            
            try:
                # Vérifier si la réponse est déjà un dictionnaire ou s'il faut la parser
                if isinstance(ai_response, dict):
                    contract_analysis = ai_response
                else:
                    contract_analysis = json.loads(ai_response)
                return contract_analysis
            
            except json.JSONDecodeError:
                logger.error("Impossible de décoder la réponse d'analyse de contrat comme JSON")
                return {"security_issues": [], "risk_assessment": "unknown"}
        
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse du contrat: {e}")
            return {"security_issues": [], "risk_assessment": "unknown"}
    
    def _extract_score_from_analysis(self, analysis: Dict[str, Any]) -> float:
        """
        Extrait un score de confiance à partir d'une analyse de marché.
        
        Args:
            analysis: Analyse du marché
            
        Returns:
            Score de confiance entre 0 et 1.0
        """
        # Valeur de confiance de base (0.5 = neutre)
        score = 0.5
        
        # Utiliser la confiance si présente
        if "confidence" in analysis:
            try:
                score = float(analysis["confidence"])
            except (ValueError, TypeError):
                pass
        
        # Ajuster en fonction de la tendance
        if "trend" in analysis:
            trend = analysis.get("trend", "").lower()
            if trend == "bullish":
                score = min(score + 0.2, 1.0)
            elif trend == "bearish":
                score = max(score - 0.2, 0.0)
        
        # Ajuster en fonction du niveau de risque
        if "risk_level" in analysis:
            risk = analysis.get("risk_level", "").lower()
            if risk == "low":
                score = min(score + 0.1, 1.0)
            elif risk == "high":
                score = max(score - 0.1, 0.0)
        
        return score
    
    def _extract_score_from_contract_analysis(self, analysis: Dict[str, Any]) -> float:
        """
        Extrait un score de confiance à partir d'une analyse de contrat.
        
        Args:
            analysis: Analyse du contrat
            
        Returns:
            Score de confiance entre 0 et 1.0
        """
        # Valeur de confiance de base (0.5 = neutre)
        score = 0.7  # Légèrement optimiste par défaut
        
        # Réduire le score en fonction des problèmes de sécurité
        security_issues = analysis.get("security_issues", [])
        for issue in security_issues:
            severity = issue.get("severity", "").lower()
            if severity == "high":
                score -= 0.3
            elif severity == "medium":
                score -= 0.15
            elif severity == "low":
                score -= 0.05
        
        # Ajuster en fonction de l'évaluation globale des risques
        risk_assessment = analysis.get("risk_assessment", "").lower()
        if risk_assessment == "high":
            score = max(score * 0.7, 0.1)  # Réduire fortement
        elif risk_assessment == "medium":
            score = max(score * 0.9, 0.3)  # Réduire modérément
        elif risk_assessment == "low":
            score = min(score * 1.1, 1.0)  # Augmenter légèrement
        
        return min(max(score, 0.0), 1.0)  # Limiter entre 0 et 1 