#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Client OpenAI pour GBPBot
========================

Ce module fournit une implémentation de LLMProvider pour utiliser
les modèles d'OpenAI (GPT-4, GPT-3.5, etc.) dans le GBPBot.
"""

import os
import logging
import time
import json
from typing import Dict, Any, List, Optional, Union, Tuple, cast

# Configuration du logger
logger = logging.getLogger(__name__)

# Vérifier si OpenAI est disponible
try:
    import openai
    from openai import OpenAI
    from openai.types.chat import ChatCompletionMessageParam
    from openai.types.chat import ChatCompletionSystemMessageParam
    from openai.types.chat import ChatCompletionUserMessageParam
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False
    logger.warning("Package OpenAI non disponible. Installez-le avec 'pip install openai'.")

# Importer la classe de base
from gbpbot.ai.llm_provider import LLMProvider

class OpenAIClient(LLMProvider):
    """
    Client pour les modèles d'OpenAI
    
    Cette classe implémente l'interface LLMProvider pour utiliser
    les modèles d'OpenAI comme GPT-4, GPT-3.5, etc.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialise le client OpenAI
        
        Args:
            config: Configuration du client OpenAI
                - api_key: Clé API OpenAI
                - model_name: Nom du modèle à utiliser (default: "gpt-3.5-turbo")
                - max_tokens: Nombre maximum de tokens (default: 1024)
                - temperature: Température pour la génération (default: 0.7)
        """
        super().__init__(config)
        
        # Extraire la configuration
        api_key = self.config.get("api_key") or os.environ.get("OPENAI_API_KEY")
        self.model_name = self.config.get("model_name", "gpt-3.5-turbo")
        self.max_tokens = self.config.get("max_tokens", 1024)
        self.temperature = self.config.get("temperature", 0.7)
        
        # Vérifier si la clé API est disponible
        if not api_key:
            logger.error("Clé API OpenAI non fournie. Définissez-la dans la configuration ou via la variable d'environnement OPENAI_API_KEY.")
            self._client = None
            return
        
        # Initialiser le client OpenAI
        try:
            if HAS_OPENAI:
                self._client = OpenAI(api_key=api_key)
                logger.info(f"Client OpenAI initialisé avec le modèle {self.model_name}")
            else:
                logger.error("OpenAI n'est pas disponible. Installez le package 'openai'.")
                self._client = None
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du client OpenAI: {e}")
            self._client = None
    
    def generate_text(self, prompt: str, **kwargs) -> str:
        """
        Génère du texte à partir d'un prompt en utilisant le modèle OpenAI
        
        Args:
            prompt: Le prompt à utiliser
            **kwargs: Arguments supplémentaires
                - max_tokens: Nombre maximum de tokens
                - temperature: Température pour la génération
                - system_message: Message système pour contextualiser
                
        Returns:
            str: Le texte généré
            
        Raises:
            Exception: Si la génération échoue
        """
        if not self._client:
            logger.error("Client OpenAI non initialisé")
            return ""
        
        # Extraire les paramètres
        max_tokens = kwargs.get("max_tokens", self.max_tokens)
        temperature = kwargs.get("temperature", self.temperature)
        system_message = kwargs.get("system_message", "Tu es un assistant d'IA spécialisé en trading et cryptomonnaies.")
        
        # Créer les messages
        system_msg: ChatCompletionSystemMessageParam = {
            "role": "system",
            "content": system_message
        }
        
        user_msg: ChatCompletionUserMessageParam = {
            "role": "user",
            "content": prompt
        }
        
        messages: List[ChatCompletionMessageParam] = [system_msg, user_msg]
        
        # Appeler l'API avec gestion des erreurs et retries
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                response = self._client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
                
                # Extraire le texte généré
                if response.choices and len(response.choices) > 0:
                    generated_text = response.choices[0].message.content
                    if generated_text is None:
                        return ""
                    return generated_text
                else:
                    logger.warning("Réponse OpenAI vide")
                    return ""
                
            except Exception as e:
                logger.error(f"Erreur lors de la génération de texte (tentative {attempt+1}/{max_retries}): {e}")
                
                if attempt < max_retries - 1:
                    # Attendre avant de réessayer
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Backoff exponentiel
                else:
                    logger.error(f"Échec de la génération de texte après {max_retries} tentatives: {e}")
                    return ""
        
        return ""  # Ne devrait jamais arriver
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Génère un embedding vectoriel pour le texte donné
        
        Args:
            text: Le texte à encoder
            
        Returns:
            List[float]: L'embedding vectoriel
            
        Raises:
            Exception: Si la génération échoue
        """
        if not self._client:
            logger.error("Client OpenAI non initialisé")
            return []
        
        # Modèle d'embedding
        embedding_model = "text-embedding-ada-002"
        
        try:
            response = self._client.embeddings.create(
                model=embedding_model,
                input=text
            )
            
            if response.data and len(response.data) > 0:
                return response.data[0].embedding
            else:
                logger.warning("Réponse d'embedding OpenAI vide")
                return []
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération d'embedding: {e}")
            return []
    
    @property
    def provider_name(self) -> str:
        """Retourne le nom du fournisseur"""
        return "openai"
    
    @property
    def is_available(self) -> bool:
        """Vérifie si le fournisseur est disponible et fonctionnel"""
        return HAS_OPENAI and self._client is not None
    
    @property
    def capabilities(self) -> Dict[str, bool]:
        """Retourne les capacités du fournisseur"""
        return {
            "text_generation": True,
            "embeddings": True,
            "code_analysis": True,
            "market_analysis": True,
            "token_scoring": True
        }
    
    async def generate_text(
        self, 
        prompt: str,
        max_tokens: int = 500,
        temperature: float = 0.7,
        system_message: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Génère du texte à partir du prompt fourni.
        
        Args:
            prompt: Le texte d'entrée pour guider la génération
            max_tokens: Nombre maximum de tokens à générer
            temperature: Contrôle de la randomité (0.0-1.0)
            system_message: Message système optionnel pour contextualiser
            **kwargs: Arguments supplémentaires spécifiques au modèle
            
        Returns:
            Le texte généré
            
        Raises:
            Exception: Si la génération échoue
        """
        messages: List[ChatCompletionMessageParam] = []
        
        # Ajouter le message système si fourni
        if system_message:
            messages.append(cast(ChatCompletionSystemMessageParam, {"role": "system", "content": system_message}))
        else:
            # Message système par défaut
            messages.append(cast(ChatCompletionSystemMessageParam, {
                "role": "system", 
                "content": "Vous êtes un assistant spécialisé dans l'analyse de trading crypto."
            }))
        
        # Ajouter le prompt utilisateur
        messages.append(cast(ChatCompletionUserMessageParam, {"role": "user", "content": prompt}))
        
        # Appeler l'API avec gestion des erreurs et retries
        for attempt in range(3):
            try:
                response = self._client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    n=1,
                    **{k: v for k, v in kwargs.items() if k not in ["model"]}
                )
                
                # Extraire et retourner le texte généré
                return response.choices[0].message.content.strip()
            except Exception as e:
                logger.warning(f"Erreur lors de la génération (tentative {attempt+1}/3): {e}")
                if attempt < 2:
                    # Attendre avant de réessayer (backoff exponentiel)
                    wait_time = 2 ** attempt
                    logger.info(f"Attente de {wait_time}s avant de réessayer...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Échec de la génération après 3 tentatives")
                    raise
        
        # Cette ligne ne devrait jamais être atteinte en raison du raise dans la boucle,
        # mais elle est nécessaire pour satisfaire le type checker
        raise Exception("Échec inattendu de la génération de texte")
    
    def generate_chat_response(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 500,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """
        Génère une réponse basée sur une conversation.
        
        Args:
            messages: Liste de messages (format: [{"role": "user|assistant|system", "content": "texte"}])
            max_tokens: Nombre maximum de tokens à générer
            temperature: Contrôle de la randomité (0.0-1.0)
            **kwargs: Arguments supplémentaires spécifiques au modèle
            
        Returns:
            La réponse générée
            
        Raises:
            Exception: Si la génération échoue
        """
        # Vérifier que les messages sont au bon format
        for msg in messages:
            if "role" not in msg or "content" not in msg:
                raise ValueError("Chaque message doit contenir 'role' et 'content'")
            if msg["role"] not in ["user", "assistant", "system"]:
                raise ValueError("Le rôle doit être 'user', 'assistant' ou 'system'")
        
        # Appeler l'API avec gestion des erreurs et retries
        for attempt in range(3):
            try:
                response = self._client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    n=1,
                    **{k: v for k, v in kwargs.items() if k not in ["model"]}
                )
                
                # Extraire et retourner le texte généré
                return response.choices[0].message.content.strip()
                
            except Exception as e:
                if attempt < 2:
                    logger.warning(f"Tentative {attempt+1} échouée: {e}. Nouvelle tentative...")
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    logger.error(f"Échec de la génération de chat après 3 tentatives: {e}")
                    raise
    
    def analyze_code(
        self,
        code: str,
        task: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Analyse du code source pour détecter des problèmes ou des opportunités.
        
        Args:
            code: Le code source à analyser
            task: Description de l'analyse à effectuer
            **kwargs: Arguments supplémentaires spécifiques au modèle
            
        Returns:
            Dictionnaire contenant les résultats de l'analyse
            
        Raises:
            Exception: Si l'analyse échoue
        """
        # Construire le prompt pour l'analyse de code
        prompt = f"""
        Analyse le code suivant selon la tâche demandée: {task}
        
        ```
        {code}
        ```
        
        Réponds UNIQUEMENT au format JSON avec la structure suivante:
        {{
            "summary": "Résumé de l'analyse",
            "issues": [
                {{
                    "severity": "high|medium|low",
                    "description": "Description du problème",
                    "line": "Numéro de ligne concernée ou null",
                    "solution": "Solution proposée"
                }}
            ],
            "improvements": [
                {{
                    "description": "Description de l'amélioration possible",
                    "benefit": "Bénéfice attendu"
                }}
            ],
            "security_score": 0-10,
            "efficiency_score": 0-10
        }}
        """
        
        # Température plus basse pour une analyse plus déterministe
        system_message = """
        Tu es un expert en analyse de code et de sécurité, spécialisé dans les smart contracts 
        et les applications de trading crypto. Ton rôle est d'analyser le code fourni pour 
        détecter des problèmes, des vulnérabilités ou des améliorations possibles.
        Tu dois répondre UNIQUEMENT au format JSON demandé.
        """
        
        try:
            result = self.generate_text(
                prompt=prompt,
                system_message=system_message,
                temperature=0.2,  # Température plus basse pour cohérence
                max_tokens=kwargs.get("max_tokens", 2000),
                **kwargs
            )
            
            # Extraire le JSON de la réponse
            result = result.strip()
            if result.startswith("```json"):
                result = result[7:]
            if result.endswith("```"):
                result = result[:-3]
            
            # Parser le JSON
            return json.loads(result)
            
        except json.JSONDecodeError as e:
            logger.error(f"Échec du parsing JSON de l'analyse de code: {e}")
            logger.debug(f"Réponse non parsable: {result}")
            
            # Fallback: retourner un dictionnaire avec l'erreur et la réponse brute
            return {
                "error": "Échec du parsing de la réponse",
                "raw_response": result,
                "summary": "Analyse non disponible",
                "issues": [],
                "improvements": [],
                "security_score": 0,
                "efficiency_score": 0
            }
    
    def analyze_token_contract(
        self,
        contract_code: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Analyse un contrat de token pour détecter des problèmes de sécurité ou des fonctions malveillantes.
        
        Args:
            contract_code: Le code source du contrat
            **kwargs: Arguments supplémentaires
            
        Returns:
            Dictionnaire contenant le score de sécurité et les problèmes détectés
            
        Raises:
            Exception: Si l'analyse échoue
        """
        # Utiliser l'analyse de code avec un prompt spécifique
        return self.analyze_code(
            code=contract_code,
            task="Analyse ce smart contract pour détecter toute fonction malveillante, backdoor, " 
                 "rug pull, honeypot, ou autres vulnérabilités. Identifie également les patterns "
                 "suspects comme des taxes excessives, des restrictions sur la vente, des "
                 "fonctions d'exclusion de limitation, etc.",
            **kwargs
        )
    
    def analyze_market_trend(
        self,
        market_data: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """
        Analyse des données de marché pour identifier des tendances.
        
        Args:
            market_data: Données de marché à analyser
            **kwargs: Arguments supplémentaires
            
        Returns:
            Dictionnaire contenant les tendances identifiées et recommandations
            
        Raises:
            Exception: Si l'analyse échoue
        """
        # Convertir les données de marché en format texte
        market_data_str = json.dumps(market_data, indent=2)
        
        prompt = f"""
        Analyse les données de marché suivantes et identifie les tendances, patterns et signaux importants:
        
        {market_data_str}
        
        Réponds UNIQUEMENT au format JSON avec la structure suivante:
        {{
            "trend": "bullish|bearish|neutral",
            "confidence": 0-100,
            "key_indicators": ["indicateur1", "indicateur2", ...],
            "patterns": [
                {{
                    "name": "Nom du pattern",
                    "significance": "Description de l'importance",
                    "probability": 0-100
                }}
            ],
            "short_term_prediction": "Description prédiction court terme",
            "recommendations": [
                {{
                    "action": "Action recommandée",
                    "reasoning": "Justification"
                }}
            ],
            "risk_level": "high|medium|low"
        }}
        """
        
        system_message = """
        Tu es un analyste de marché crypto expérimenté, spécialisé dans l'analyse technique et fondamentale.
        Ton rôle est d'analyser les données de marché pour identifier les tendances, les patterns et les signaux.
        Tu dois être objectif et te baser uniquement sur les données fournies.
        Tu dois répondre UNIQUEMENT au format JSON demandé.
        """
        
        try:
            result = self.generate_text(
                prompt=prompt,
                system_message=system_message,
                temperature=0.3,
                max_tokens=kwargs.get("max_tokens", 1500),
                **kwargs
            )
            
            # Extraire le JSON de la réponse
            result = result.strip()
            if result.startswith("```json"):
                result = result[7:]
            if result.endswith("```"):
                result = result[:-3]
            
            # Parser le JSON
            return json.loads(result)
            
        except json.JSONDecodeError as e:
            logger.error(f"Échec du parsing JSON de l'analyse de marché: {e}")
            logger.debug(f"Réponse non parsable: {result}")
            
            # Fallback: retourner un dictionnaire avec l'erreur et la réponse brute
            return {
                "error": "Échec du parsing de la réponse",
                "raw_response": result,
                "trend": "neutral",
                "confidence": 0,
                "key_indicators": [],
                "patterns": [],
                "short_term_prediction": "Analyse non disponible",
                "recommendations": [],
                "risk_level": "high"
            }
    
    def get_token_score(
        self,
        token_data: Dict[str, Any],
        **kwargs
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Évalue un token et génère un score de potentiel ou de risque.
        
        Args:
            token_data: Données du token à évaluer
            **kwargs: Arguments supplémentaires
            
        Returns:
            Tuple contenant (score, détails)
            
        Raises:
            Exception: Si l'évaluation échoue
        """
        # Convertir les données du token en format texte
        token_data_str = json.dumps(token_data, indent=2)
        
        prompt = f"""
        Évalue ce token crypto et génère un score de potentiel et une analyse des risques:
        
        {token_data_str}
        
        Réponds UNIQUEMENT au format JSON avec la structure suivante:
        {{
            "potential_score": 0-100,
            "risk_score": 0-100,
            "overall_score": 0-100,
            "strengths": ["force1", "force2", ...],
            "weaknesses": ["faiblesse1", "faiblesse2", ...],
            "red_flags": ["problème1", "problème2", ...],
            "assessment": "Évaluation globale détaillée",
            "recommendation": "buy|sell|hold|avoid"
        }}
        """
        
        system_message = """
        Tu es un expert en évaluation de tokens crypto, spécialisé dans les memecoins et nouveaux projets.
        Ton rôle est d'évaluer objectivement le potentiel et les risques d'un token sur la base des données fournies.
        Sois particulièrement attentif aux signaux de scam, rug pull, ou autres problèmes de sécurité.
        Tu dois répondre UNIQUEMENT au format JSON demandé.
        """
        
        try:
            result = self.generate_text(
                prompt=prompt,
                system_message=system_message,
                temperature=0.2,
                max_tokens=kwargs.get("max_tokens", 1000),
                **kwargs
            )
            
            # Extraire le JSON de la réponse
            result = result.strip()
            if result.startswith("```json"):
                result = result[7:]
            if result.endswith("```"):
                result = result[:-3]
            
            # Parser le JSON
            parsed_result = json.loads(result)
            
            # Extraire le score global et les détails
            score = float(parsed_result.get("overall_score", 0))
            details = parsed_result
            
            return (score, details)
            
        except json.JSONDecodeError as e:
            logger.error(f"Échec du parsing JSON de l'évaluation de token: {e}")
            logger.debug(f"Réponse non parsable: {result}")
            
            # Fallback: retourner un score faible et des détails minimaux
            return (0.0, {
                "error": "Échec du parsing de la réponse",
                "raw_response": result,
                "potential_score": 0,
                "risk_score": 100,
                "overall_score": 0,
                "strengths": [],
                "weaknesses": ["Analyse échouée"],
                "red_flags": ["Impossible d'évaluer ce token"],
                "assessment": "Analyse non disponible",
                "recommendation": "avoid"
            }) 