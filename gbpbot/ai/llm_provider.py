#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Classe abstraite pour les fournisseurs de modèles de langage (LLM)
=================================================================

Ce module définit l'interface commune que tous les fournisseurs
de modèles de langage doivent implémenter pour être utilisés
dans le GBPBot.
"""

import abc
from typing import Dict, Any, List, Optional, Union, Tuple

class LLMProvider(abc.ABC):
    """
    Classe abstraite définissant l'interface pour les fournisseurs de LLM
    
    Tous les fournisseurs de modèles de langage (OpenAI, LLaMA, etc.)
    doivent implémenter cette interface pour être utilisés dans le GBPBot.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialise le fournisseur de LLM
        
        Args:
            config: Configuration du fournisseur
        """
        self.config = config or {}
        self.model_name = self.config.get("model_name", "default")
        self.max_tokens = self.config.get("max_tokens", 1024)
        self.temperature = self.config.get("temperature", 0.7)
    
    @abc.abstractmethod
    def generate_text(self, prompt: str, **kwargs) -> str:
        """
        Génère du texte à partir d'un prompt
        
        Args:
            prompt: Le prompt à utiliser
            **kwargs: Arguments supplémentaires spécifiques au fournisseur
            
        Returns:
            str: Le texte généré
        """
        pass
    
    @abc.abstractmethod
    def generate_embedding(self, text: str) -> List[float]:
        """
        Génère un embedding vectoriel pour le texte donné
        
        Args:
            text: Le texte à encoder
            
        Returns:
            List[float]: L'embedding vectoriel
        """
        pass
    
    def analyze_contract(self, contract_code: str) -> Dict[str, Any]:
        """
        Analyse un contrat intelligent pour détecter les risques
        
        Args:
            contract_code: Le code du contrat à analyser
            
        Returns:
            Dict[str, Any]: Résultats de l'analyse avec scores de risque
        """
        prompt = f"""
        Analyse le contrat suivant et identifie les risques potentiels:
        
        ```solidity
        {contract_code}
        ```
        
        Réponds au format JSON avec les champs suivants:
        - risk_score: note de 0 à 100 (100 = très risqué)
        - rug_pull_risk: note de 0 à 100
        - honeypot_risk: note de 0 à 100
        - backdoor_risk: note de 0 à 100
        - issues: liste des problèmes identifiés
        - explanation: explication détaillée
        """
        
        try:
            result = self.generate_text(prompt)
            # Extraire le JSON de la réponse
            import json
            import re
            
            # Chercher un bloc JSON dans la réponse
            json_match = re.search(r'```json\s*(.*?)\s*```', result, re.DOTALL)
            if json_match:
                result = json_match.group(1)
            
            # Nettoyer et parser le JSON
            result = result.strip()
            if result.startswith('{') and result.endswith('}'):
                return json.loads(result)
            else:
                # Essayer de trouver un JSON valide dans la chaîne
                start = result.find('{')
                end = result.rfind('}')
                if start != -1 and end != -1 and end > start:
                    return json.loads(result[start:end+1])
            
            return {
                "error": "Impossible de parser la réponse JSON",
                "raw_response": result,
                "risk_score": 100  # Par défaut, considérer comme risqué en cas d'erreur
            }
        except Exception as e:
            return {
                "error": f"Erreur lors de l'analyse du contrat: {str(e)}",
                "risk_score": 100  # Par défaut, considérer comme risqué en cas d'erreur
            }
    
    def analyze_token(self, token_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyse les données d'un token pour évaluer son potentiel
        
        Args:
            token_data: Données du token (prix, volume, liquidité, etc.)
            
        Returns:
            Dict[str, Any]: Résultats de l'analyse avec scores et recommandations
        """
        # Convertir les données du token en texte pour le prompt
        token_info = "\n".join([f"{k}: {v}" for k, v in token_data.items()])
        
        prompt = f"""
        Analyse les données suivantes d'un token et évalue son potentiel:
        
        {token_info}
        
        Réponds au format JSON avec les champs suivants:
        - potential_score: note de 0 à 100 (100 = très prometteur)
        - pump_probability: probabilité de 0 à 100
        - risk_level: "low", "medium", "high" ou "extreme"
        - recommendation: "buy", "hold", "sell" ou "avoid"
        - reasoning: explication détaillée
        """
        
        try:
            result = self.generate_text(prompt)
            # Extraire le JSON de la réponse
            import json
            import re
            
            # Chercher un bloc JSON dans la réponse
            json_match = re.search(r'```json\s*(.*?)\s*```', result, re.DOTALL)
            if json_match:
                result = json_match.group(1)
            
            # Nettoyer et parser le JSON
            result = result.strip()
            if result.startswith('{') and result.endswith('}'):
                return json.loads(result)
            else:
                # Essayer de trouver un JSON valide dans la chaîne
                start = result.find('{')
                end = result.rfind('}')
                if start != -1 and end != -1 and end > start:
                    return json.loads(result[start:end+1])
            
            return {
                "error": "Impossible de parser la réponse JSON",
                "raw_response": result,
                "potential_score": 0  # Par défaut, considérer comme peu prometteur en cas d'erreur
            }
        except Exception as e:
            return {
                "error": f"Erreur lors de l'analyse du token: {str(e)}",
                "potential_score": 0  # Par défaut, considérer comme peu prometteur en cas d'erreur
            }
    
    def get_market_sentiment(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyse le sentiment du marché à partir des données fournies
        
        Args:
            market_data: Données du marché (tendances, volumes, etc.)
            
        Returns:
            Dict[str, Any]: Analyse du sentiment avec recommandations
        """
        # Convertir les données du marché en texte pour le prompt
        market_info = "\n".join([f"{k}: {v}" for k, v in market_data.items()])
        
        prompt = f"""
        Analyse les données suivantes du marché et détermine le sentiment général:
        
        {market_info}
        
        Réponds au format JSON avec les champs suivants:
        - sentiment: "bullish", "neutral" ou "bearish"
        - confidence: niveau de confiance de 0 à 100
        - market_phase: "accumulation", "markup", "distribution" ou "markdown"
        - recommendation: recommandation générale
        - reasoning: explication détaillée
        """
        
        try:
            result = self.generate_text(prompt)
            # Extraire le JSON de la réponse
            import json
            import re
            
            # Chercher un bloc JSON dans la réponse
            json_match = re.search(r'```json\s*(.*?)\s*```', result, re.DOTALL)
            if json_match:
                result = json_match.group(1)
            
            # Nettoyer et parser le JSON
            result = result.strip()
            if result.startswith('{') and result.endswith('}'):
                return json.loads(result)
            else:
                # Essayer de trouver un JSON valide dans la chaîne
                start = result.find('{')
                end = result.rfind('}')
                if start != -1 and end != -1 and end > start:
                    return json.loads(result[start:end+1])
            
            return {
                "error": "Impossible de parser la réponse JSON",
                "raw_response": result,
                "sentiment": "neutral",  # Par défaut, sentiment neutre en cas d'erreur
                "confidence": 0
            }
        except Exception as e:
            return {
                "error": f"Erreur lors de l'analyse du sentiment: {str(e)}",
                "sentiment": "neutral",  # Par défaut, sentiment neutre en cas d'erreur
                "confidence": 0
            }
    
    @property
    @abc.abstractmethod
    def provider_name(self) -> str:
        """Retourne le nom du fournisseur (openai, llama, etc.)"""
        pass
    
    @property
    @abc.abstractmethod
    def is_available(self) -> bool:
        """Vérifie si le fournisseur est disponible et fonctionnel"""
        pass
    
    @property
    @abc.abstractmethod
    def capabilities(self) -> Dict[str, bool]:
        """
        Retourne un dictionnaire des capacités supportées par ce fournisseur.
        
        Par exemple:
        {
            "chat": True,
            "code_analysis": True,
            "token_contract_analysis": False,
            "market_analysis": True,
            "embeddings": False
        }
        """
        pass 