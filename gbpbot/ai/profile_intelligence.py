#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module ProfileIntelligence - Système d'automatisation des profils de trading par IA

Ce module permet aux systèmes d'IA intégrés dans GBPBot (Claude, OpenAI, LLaMA) 
de gérer automatiquement les profils de trading utilisés par le système anti-détection.
L'objectif est d'optimiser la sélection des profils en fonction du contexte d'opération
tout en maintenant un équilibre entre discrétion et performance de trading.

Les systèmes d'IA sélectionnent le profil optimal en fonction de:
- La blockchain cible (Solana, AVAX, Sonic)
- Le type d'opération (arbitrage, sniping, trading standard)
- Le token concerné et ses caractéristiques
- Les conditions de marché actuelles
- L'historique de détection sur les différentes blockchains

Le module s'assure que le choix du profil n'interfère jamais avec la capacité
du bot à générer des profits importants.
"""

import os
import json
import random
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime, timedelta
import asyncio

# Importations internes
from gbpbot.utils.logger import setup_logger
from gbpbot.ai.llm_provider import get_ai_client, AiClientResponseFormat, AiClientResponse
from gbpbot.config.settings import get_settings

# Configuration du logger
logger = setup_logger("profile_intelligence", logging.INFO)

@dataclass
class BlockchainStatus:
    """Statut de détection et performances sur une blockchain spécifique."""
    chain_name: str
    detection_risk: float = 0.0  # 0.0-1.0 (1.0 = risque élevé)
    detection_events: int = 0  # Nombre d'événements de détection
    failed_transactions: int = 0  # Nombre de transactions échouées
    total_transactions: int = 0  # Nombre total de transactions
    last_reset: datetime = field(default_factory=datetime.now)  # Dernière remise à zéro des compteurs
    
    def update(self, detection_events: int = 0, failed_transactions: int = 0, total_transactions: int = 1) -> None:
        """Met à jour les statistiques de la blockchain."""
        self.detection_events += detection_events
        self.failed_transactions += failed_transactions
        self.total_transactions += total_transactions
        
        # Calcul du risque de détection (formule pondérée)
        if self.total_transactions > 0:
            detection_rate = self.detection_events / self.total_transactions
            failure_rate = self.failed_transactions / self.total_transactions
            
            # Pondération: détection compte double par rapport aux échecs
            self.detection_risk = min(1.0, (detection_rate * 0.7) + (failure_rate * 0.3))
        
        # Réinitialiser les compteurs si trop vieux (7 jours)
        if (datetime.now() - self.last_reset).days > 7:
            self._soft_reset()
    
    def _soft_reset(self) -> None:
        """Réinitialise partiellement les compteurs pour éviter l'accumulation."""
        # Conserver une partie de l'historique pour la continuité
        self.detection_events = int(self.detection_events * 0.3)
        self.failed_transactions = int(self.failed_transactions * 0.3)
        self.total_transactions = int(self.total_transactions * 0.3) or 1
        self.last_reset = datetime.now()

@dataclass
class ProfileIntelligenceConfig:
    """Configuration du système d'intelligence de profil."""
    enable_ai_profile_management: bool = True
    performance_priority: float = 0.7  # 0.0-1.0 (0 = discrétion max, 1 = performance max)
    default_profile: str = "intermediate_trader"
    ai_fallback_threshold: float = 0.75  # Seuil de confiance pour le fallback aux règles
    blockchain_risk_thresholds: Dict[str, float] = field(default_factory=lambda: {
        "solana": 0.6,  # Plus risqué par défaut 
        "avax": 0.4,
        "sonic": 0.5
    })
    # Périodes entre les consultations de l'IA (pour éviter les appels excessifs)
    min_ai_consultation_interval_secs: int = 60
    operation_specific_intervals: Dict[str, int] = field(default_factory=lambda: {
        "sniping": 30,     # Consulter plus souvent pour le sniping (30s)
        "arbitrage": 120,  # Moins souvent pour l'arbitrage (2min)
        "standard": 300    # Rarement pour les opérations standard (5min)
    })

class ProfileIntelligence:
    """
    Système d'intelligence pour la gestion automatisée des profils de trader par IA.
    
    Ce système permet aux différentes IA intégrées (Claude, OpenAI, LLaMA) de choisir
    automatiquement le profil de trading le plus approprié en fonction du contexte
    d'opération, tout en équilibrant discrétion et performance.
    """
    
    def __init__(self, config: Optional[Union[Dict[str, Any], ProfileIntelligenceConfig]] = None):
        """
        Initialise le système d'intelligence de profil.
        
        Args:
            config: Configuration du système sous forme de dictionnaire ou de ProfileIntelligenceConfig
        """
        if config is None:
            self.config = ProfileIntelligenceConfig()
        elif isinstance(config, dict):
            # Créer la configuration à partir du dictionnaire
            config_dict = {
                "enable_ai_profile_management": config.get("enable_ai_profile_management", True),
                "performance_priority": config.get("performance_priority", 0.7),
                "default_profile": config.get("default_profile", "intermediate_trader"),
                "ai_fallback_threshold": config.get("ai_fallback_threshold", 0.75),
                "blockchain_risk_thresholds": config.get("blockchain_risk_thresholds", {
                    "solana": 0.6,
                    "avax": 0.4,
                    "sonic": 0.5
                }),
                "min_ai_consultation_interval_secs": config.get("min_ai_consultation_interval_secs", 60),
                "operation_specific_intervals": config.get("operation_specific_intervals", {
                    "sniping": 30,
                    "arbitrage": 120,
                    "standard": 300
                })
            }
            self.config = ProfileIntelligenceConfig(**config_dict)
        else:
            self.config = config
        
        # État interne
        self.blockchain_statuses: Dict[str, BlockchainStatus] = {
            "solana": BlockchainStatus(chain_name="solana"),
            "avax": BlockchainStatus(chain_name="avax"),
            "sonic": BlockchainStatus(chain_name="sonic")
        }
        
        # Historique des sélections de profil
        self.profile_selections: Dict[str, Dict[str, int]] = {
            "solana": {},
            "avax": {},
            "sonic": {}
        }
        
        # Cache des décisions récentes pour limiter les appels API
        self.decision_cache: Dict[str, Dict[str, Any]] = {}
        self.last_ai_consultation: Dict[str, datetime] = {}
        
        # Statistiques
        self.total_ai_selections: int = 0
        self.total_rule_based_selections: int = 0
        self.total_profile_switches: int = 0
        self.last_selected_profile: str = self.config.default_profile
        
        # Traçabilité des changements de profil
        self.profile_change_history: List[Dict[str, Any]] = []
        
        logger.info(f"Système ProfileIntelligence initialisé avec priorité performance: {self.config.performance_priority}")
    
    async def select_optimal_profile(
        self,
        blockchain: str,
        operation_type: str,
        token_symbol: str,
        force_ai_selection: bool = False
    ) -> str:
        """
        Sélectionne le profil de trading optimal en fonction du contexte.
        
        Args:
            blockchain: Blockchain cible ("solana", "avax", "sonic")
            operation_type: Type d'opération ("sniping", "arbitrage", "standard")
            token_symbol: Symbole du token
            force_ai_selection: Force l'utilisation de l'IA même si le cache est valide
            
        Returns:
            Nom du profil à utiliser
        """
        # Normaliser les entrées
        blockchain = blockchain.lower()
        operation_type = operation_type.lower()
        
        # Vérifier si la blockchain est supportée
        if blockchain not in self.blockchain_statuses:
            logger.warning(f"Blockchain non supportée: {blockchain}, utilisation de solana")
            blockchain = "solana"
        
        # Clé de cache pour cette opération
        cache_key = f"{blockchain}:{operation_type}:{token_symbol}"
        
        # Vérifier si une décision récente est disponible dans le cache
        if not force_ai_selection and cache_key in self.decision_cache:
            cached_decision = self.decision_cache[cache_key]
            last_decision_time = cached_decision.get("timestamp", datetime.min)
            
            # Déterminer l'intervalle de rafraîchissement en fonction du type d'opération
            refresh_interval = self.config.operation_specific_intervals.get(
                operation_type, 
                self.config.min_ai_consultation_interval_secs
            )
            
            # Utiliser la décision en cache si assez récente
            if datetime.now() - last_decision_time < timedelta(seconds=refresh_interval):
                profile = cached_decision.get("profile", self.config.default_profile)
                logger.debug(f"Utilisation du profil en cache pour {operation_type} sur {blockchain}: {profile}")
                return profile
        
        # Si l'IA est désactivée, utiliser la sélection basée sur des règles
        if not self.config.enable_ai_profile_management:
            profile = self._rule_based_profile_selection(blockchain, operation_type, token_symbol)
            self.total_rule_based_selections += 1
            return profile
        
        # Vérifier si l'IA a été consultée récemment pour limiter les appels
        now = datetime.now()
        last_consultation = self.last_ai_consultation.get(blockchain, datetime.min)
        min_interval = timedelta(seconds=self.config.min_ai_consultation_interval_secs)
        
        if not force_ai_selection and now - last_consultation < min_interval:
            # Utiliser la sélection basée sur des règles si l'IA a été consultée récemment
            profile = self._rule_based_profile_selection(blockchain, operation_type, token_symbol)
            self.total_rule_based_selections += 1
            return profile
        
        # Mettre à jour le timestamp de la dernière consultation
        self.last_ai_consultation[blockchain] = now
        
        # Tenter la sélection basée sur l'IA
        try:
            # Préparer le contexte pour l'IA
            context = self._prepare_ai_context(blockchain, operation_type, token_symbol)
            
            # Obtenir un client IA
            ai_client = get_ai_client()
            
            # Si pas de client IA disponible, fallback aux règles
            if not ai_client:
                logger.warning("Aucun client IA disponible, utilisation des règles prédéfinies")
                profile = self._rule_based_profile_selection(blockchain, operation_type, token_symbol)
                self.total_rule_based_selections += 1
                return profile
            
            # Déterminer le prompt optimal en fonction du provider
            provider = ai_client.provider
            
            # Construire le prompt adapté au provider
            if provider == "claude":
                prompt = self._build_claude_prompt(context)
            elif provider == "openai":
                prompt = self._build_openai_prompt(context)
            else:  # llama ou autre
                prompt = self._build_generic_prompt(context)
            
            # Appeler l'IA pour décision
            response = await ai_client.generate(
                prompt=prompt,
                response_format=AiClientResponseFormat.JSON,
                temperature=0.2,  # Basse température pour des réponses cohérentes
                max_tokens=500
            )
            
            # Traiter la réponse
            profile, confidence = self._parse_ai_response(response, blockchain, operation_type)
            
            # Si la confiance est faible, fallback aux règles
            if confidence < self.config.ai_fallback_threshold:
                logger.info(f"Confiance IA faible ({confidence:.2f}), fallback aux règles")
                profile = self._rule_based_profile_selection(blockchain, operation_type, token_symbol)
                self.total_rule_based_selections += 1
            else:
                # Utiliser la sélection de l'IA
                self.total_ai_selections += 1
                
                # Mettre à jour les statistiques
                if profile != self.last_selected_profile:
                    self.total_profile_switches += 1
                    
                    # Enregistrer le changement dans l'historique
                    self.profile_change_history.append({
                        "timestamp": datetime.now().isoformat(),
                        "previous_profile": self.last_selected_profile,
                        "new_profile": profile,
                        "blockchain": blockchain,
                        "operation_type": operation_type,
                        "token": token_symbol,
                        "confidence": confidence,
                        "reason": response.content if hasattr(response, "content") else "Unknown"
                    })
                
                # Mettre à jour les sélections par blockchain
                if profile not in self.profile_selections[blockchain]:
                    self.profile_selections[blockchain][profile] = 0
                self.profile_selections[blockchain][profile] += 1
            
            # Mettre à jour le cache
            self.decision_cache[cache_key] = {
                "profile": profile,
                "confidence": confidence,
                "timestamp": datetime.now()
            }
            
            # Mettre à jour le dernier profil sélectionné
            self.last_selected_profile = profile
            
            return profile
            
        except Exception as e:
            logger.error(f"Erreur lors de la sélection IA du profil: {str(e)}")
            # Fallback aux règles en cas d'erreur
            profile = self._rule_based_profile_selection(blockchain, operation_type, token_symbol)
            self.total_rule_based_selections += 1
            return profile
    
    def _rule_based_profile_selection(self, blockchain: str, operation_type: str, token_symbol: str) -> str:
        """
        Sélectionne un profil basé sur des règles prédéfinies (fallback pour l'IA).
        
        Args:
            blockchain: Blockchain cible
            operation_type: Type d'opération
            token_symbol: Symbole du token
            
        Returns:
            Nom du profil à utiliser
        """
        blockchain_status = self.blockchain_statuses.get(blockchain)
        
        # Si pas de statut ou blockchain non suivie, utiliser le statut solana par défaut
        if not blockchain_status:
            blockchain_status = self.blockchain_statuses.get("solana", BlockchainStatus(chain_name="solana"))
        
        # Vérifier le risque de détection pour cette blockchain
        detection_risk = blockchain_status.detection_risk
        risk_threshold = self.config.blockchain_risk_thresholds.get(blockchain, 0.5)
        
        # Profils adaptés à différentes situations
        high_risk_profiles = ["beginner_trader", "whale_tracker"]
        standard_profiles = ["intermediate_trader", "avax_arbitrageur"]
        performance_profiles = ["expert_trader", "solana_meme_sniper"]
        
        # Si risque élevé sur la blockchain, privilégier un profil discret
        if detection_risk > risk_threshold:
            profile_pool = high_risk_profiles
        else:
            # Sinon, base la sélection sur la priorité performance
            perf_priority = self.config.performance_priority
            
            if operation_type == "sniping":
                # Pour le sniping, ajuster la priorité performance
                if perf_priority > 0.6:
                    profile_pool = performance_profiles
                else:
                    profile_pool = standard_profiles
            elif operation_type == "arbitrage":
                # Pour l'arbitrage, profil plus agressif
                if perf_priority > 0.4:
                    profile_pool = performance_profiles
                else:
                    profile_pool = standard_profiles
            else:
                # Pour les opérations standard
                if perf_priority > 0.8:
                    profile_pool = performance_profiles
                elif perf_priority > 0.4:
                    profile_pool = standard_profiles
                else:
                    profile_pool = high_risk_profiles
        
        # Sélectionner aléatoirement parmi le pool de profils adaptés
        return random.choice(profile_pool)
    
    def _prepare_ai_context(self, blockchain: str, operation_type: str, token_symbol: str) -> Dict[str, Any]:
        """
        Prépare le contexte pour la prise de décision par l'IA.
        
        Args:
            blockchain: Blockchain cible
            operation_type: Type d'opération
            token_symbol: Symbole du token
            
        Returns:
            Dictionnaire de contexte pour l'IA
        """
        # Obtenir le statut de la blockchain
        blockchain_status = self.blockchain_statuses.get(blockchain, BlockchainStatus(chain_name=blockchain))
        
        # Récupérer des informations sur les profils disponibles
        profiles = self._load_available_profiles()
        
        # Historique des sélections pour cette blockchain
        chain_selections = self.profile_selections.get(blockchain, {})
        
        return {
            "request": {
                "blockchain": blockchain,
                "operation_type": operation_type,
                "token_symbol": token_symbol,
                "timestamp": datetime.now().isoformat()
            },
            "blockchain_status": {
                "chain_name": blockchain_status.chain_name,
                "detection_risk": blockchain_status.detection_risk,
                "detection_events": blockchain_status.detection_events,
                "failed_transactions": blockchain_status.failed_transactions,
                "total_transactions": blockchain_status.total_transactions
            },
            "trader_profiles": profiles,
            "past_selections": chain_selections,
            "performance_priority": self.config.performance_priority,
            "last_selected_profile": self.last_selected_profile,
            "system_config": {
                "risk_thresholds": self.config.blockchain_risk_thresholds,
                "default_profile": self.config.default_profile
            }
        }
    
    def _load_available_profiles(self) -> Dict[str, Dict[str, Any]]:
        """
        Charge les profils de trading disponibles.
        
        Returns:
            Dictionnaire des profils disponibles
        """
        # Emplacement des profils prédéfinis
        profiles_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "security",
            "data",
            "trader_profiles.json"
        )
        
        profiles = {}
        
        # Essayer de charger les profils existants
        if os.path.exists(profiles_path):
            try:
                with open(profiles_path, 'r') as f:
                    profiles = json.load(f)
            except Exception as e:
                logger.error(f"Erreur lors du chargement des profils: {str(e)}")
        
        return profiles
    
    def _build_claude_prompt(self, context: Dict[str, Any]) -> str:
        """
        Construit un prompt optimisé pour Claude.
        
        Args:
            context: Contexte d'opération
            
        Returns:
            Prompt formaté pour Claude
        """
        blockchain = context["request"]["blockchain"]
        operation = context["request"]["operation_type"]
        token = context["request"]["token_symbol"]
        risk = context["blockchain_status"]["detection_risk"]
        perf_priority = context["performance_priority"]
        
        prompt = f"""
        <context>
        Vous êtes le système d'intelligence de profil de GBPBot, un bot de trading avancé.
        Votre tâche est de sélectionner le profil de trading optimal pour une opération spécifique
        afin d'équilibrer la discrétion (éviter la détection) et la performance (maximiser les profits).

        Blockchain cible: {blockchain}
        Type d'opération: {operation}
        Token concerné: {token}
        Risque de détection actuel: {risk:.2f}/1.0
        Priorité performance: {perf_priority:.2f}/1.0 (plus élevé = privilégie la performance)
        
        Statut de la blockchain {blockchain}:
        - Événements de détection: {context["blockchain_status"]["detection_events"]}
        - Transactions échouées: {context["blockchain_status"]["failed_transactions"]}
        - Transactions totales: {context["blockchain_status"]["total_transactions"]}
        
        Profils de trading disponibles:
        {json.dumps(context["trader_profiles"], indent=2)}
        
        Sélections passées sur {blockchain}:
        {json.dumps(context["past_selections"], indent=2)}
        
        Dernier profil sélectionné: {context["last_selected_profile"]}
        </context>

        <instructions>
        Analysez le contexte et sélectionnez le profil de trading optimal pour cette opération.
        Vous devez équilibrer deux objectifs contradictoires:
        1. Discrétion: éviter la détection par les DEX et autres acteurs de la blockchain
        2. Performance: maximiser les profits et l'efficacité des transactions
        
        En fonction de la priorité performance configurée ({perf_priority:.2f}/1.0), vous devez
        pencher plus vers la performance ou la discrétion.
        
        Si le risque de détection est élevé (>{context["system_config"]["risk_thresholds"].get(blockchain, 0.5)}), privilégiez la discrétion.
        Pour les opérations de type "sniping", la vitesse est cruciale.
        Pour les opérations de type "arbitrage", l'efficacité des transactions est primordiale.
        
        Répondez UNIQUEMENT au format JSON comme suit:
        {{
            "selected_profile": "nom_du_profil",
            "confidence": 0.XX,
            "reasoning": "Explication brève de votre choix"
        }}
        </instructions>
        """
        return prompt
    
    def _build_openai_prompt(self, context: Dict[str, Any]) -> str:
        """
        Construit un prompt optimisé pour OpenAI.
        
        Args:
            context: Contexte d'opération
            
        Returns:
            Prompt formaté pour OpenAI
        """
        # Version simplifiée pour OpenAI
        blockchain = context["request"]["blockchain"]
        operation = context["request"]["operation_type"]
        token = context["request"]["token_symbol"]
        risk = context["blockchain_status"]["detection_risk"]
        perf_priority = context["performance_priority"]
        
        prompt = f"""
        You are the profile intelligence system for GBPBot, an advanced trading bot.
        Your task is to select the optimal trading profile for a specific operation
        to balance stealth (avoiding detection) and performance (maximizing profits).

        Target blockchain: {blockchain}
        Operation type: {operation}
        Token: {token}
        Current detection risk: {risk:.2f}/1.0
        Performance priority: {perf_priority:.2f}/1.0 (higher = prioritize performance)
        
        Available trading profiles:
        {json.dumps(context["trader_profiles"], indent=2)}
        
        Please analyze the context and select the optimal trading profile.
        If detection risk is high (>{context["system_config"]["risk_thresholds"].get(blockchain, 0.5)}), prioritize stealth.
        For "sniping" operations, speed is crucial.
        For "arbitrage" operations, transaction efficiency is paramount.
        
        Respond ONLY in JSON format as follows:
        {{
            "selected_profile": "profile_name",
            "confidence": 0.XX,
            "reasoning": "Brief explanation of your choice"
        }}
        """
        return prompt
    
    def _build_generic_prompt(self, context: Dict[str, Any]) -> str:
        """
        Construit un prompt générique pour les autres modèles.
        
        Args:
            context: Contexte d'opération
            
        Returns:
            Prompt formaté
        """
        # Version ultra simplifiée pour les autres modèles (LLaMA, etc.)
        blockchain = context["request"]["blockchain"]
        operation = context["request"]["operation_type"]
        
        prompt = f"""
        Select the best trading profile for {operation} on {blockchain}.
        Available profiles: {', '.join(context["trader_profiles"].keys())}
        Performance priority: {context["performance_priority"]:.2f}
        Detection risk: {context["blockchain_status"]["detection_risk"]:.2f}
        
        Return JSON only: {{"selected_profile": "profile_name", "confidence": 0.XX}}
        """
        return prompt
    
    def _parse_ai_response(self, response: AiClientResponse, blockchain: str, operation_type: str) -> Tuple[str, float]:
        """
        Parse la réponse de l'IA pour extraire le profil sélectionné.
        
        Args:
            response: Réponse de l'IA
            blockchain: Blockchain cible (pour fallback)
            operation_type: Type d'opération (pour fallback)
            
        Returns:
            Tuple (nom_profil, niveau_confiance)
        """
        try:
            # Récupérer le contenu de la réponse
            content = response.content if hasattr(response, "content") else str(response)
            
            # Tenter de parser le JSON
            if isinstance(content, str):
                # Nettoyer et extraire la partie JSON
                json_str = content.strip()
                
                # Heuristique pour extraire la partie JSON
                start_idx = json_str.find("{")
                end_idx = json_str.rfind("}")
                
                if start_idx >= 0 and end_idx > start_idx:
                    json_str = json_str[start_idx:end_idx+1]
                
                decision = json.loads(json_str)
            else:
                decision = content
            
            # Extraire les informations
            profile = decision.get("selected_profile", self.config.default_profile)
            confidence = float(decision.get("confidence", 0.5))
            
            # Valider le profil
            profiles = self._load_available_profiles()
            if profile not in profiles:
                logger.warning(f"Profil sélectionné par l'IA non disponible: {profile}, utilisation du profil par défaut")
                profile = self.config.default_profile
                confidence = 0.5
            
            return profile, confidence
            
        except Exception as e:
            logger.error(f"Erreur lors du parsing de la réponse IA: {str(e)}")
            # En cas d'erreur, fallback au profil par défaut
            return self.config.default_profile, 0.0
    
    async def update_blockchain_status(
        self,
        blockchain: str,
        detection_events: int = 0,
        failed_transactions: int = 0,
        total_transactions: int = 1
    ) -> None:
        """
        Met à jour le statut d'une blockchain.
        
        Args:
            blockchain: Nom de la blockchain
            detection_events: Nombre d'événements de détection
            failed_transactions: Nombre de transactions échouées
            total_transactions: Nombre total de transactions
        """
        blockchain = blockchain.lower()
        
        # Créer le statut s'il n'existe pas
        if blockchain not in self.blockchain_statuses:
            self.blockchain_statuses[blockchain] = BlockchainStatus(chain_name=blockchain)
        
        # Mettre à jour le statut
        self.blockchain_statuses[blockchain].update(
            detection_events=detection_events,
            failed_transactions=failed_transactions,
            total_transactions=total_transactions
        )
        
        # Log si le risque est élevé
        risk = self.blockchain_statuses[blockchain].detection_risk
        threshold = self.config.blockchain_risk_thresholds.get(blockchain, 0.5)
        
        if risk > threshold:
            logger.warning(
                f"Risque de détection élevé sur {blockchain}: {risk:.2f} "
                f"(seuil: {threshold}). Adaptation recommandée."
            )
            
            # Effacer le cache pour forcer une nouvelle sélection
            for key in list(self.decision_cache.keys()):
                if key.startswith(f"{blockchain}:"):
                    del self.decision_cache[key]
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Retourne des statistiques sur le système d'intelligence de profil.
        
        Returns:
            Dictionnaire de statistiques
        """
        return {
            "total_ai_selections": self.total_ai_selections,
            "total_rule_based_selections": self.total_rule_based_selections,
            "total_profile_switches": self.total_profile_switches,
            "last_selected_profile": self.last_selected_profile,
            "blockchain_risks": {
                chain: status.detection_risk
                for chain, status in self.blockchain_statuses.items()
            },
            "profile_selections_by_chain": self.profile_selections,
            "cache_size": len(self.decision_cache)
        }

def create_profile_intelligence(config: Optional[Union[Dict[str, Any], ProfileIntelligenceConfig]] = None) -> ProfileIntelligence:
    """
    Crée et retourne une instance de ProfileIntelligence.
    
    Args:
        config: Configuration du système d'intelligence de profil
        
    Returns:
        Instance de ProfileIntelligence
    """
    return ProfileIntelligence(config=config) 