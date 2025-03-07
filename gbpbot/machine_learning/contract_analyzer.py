#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module d'analyse de contrats avec modèles légers pour GBPBot
===========================================================

Ce module utilise des modèles d'IA légers pour analyser les contrats de tokens
avec une latence minimale. Il fournit des évaluations rapides de la sécurité 
des contrats, détectant les risques potentiels comme les honeypots, les backdoors, 
et autres fonctions malveillantes.
"""

import os
import re
import time
import json
import logging
import hashlib
import asyncio
from typing import Dict, List, Any, Optional, Tuple, Union, Set
from dataclasses import dataclass, field

# Import du module de modèles légers
try:
    from gbpbot.machine_learning.lightweight_models import (
        LightweightModelManager,
        create_model_manager,
        ModelTask
    )
    ML_IMPORTS_OK = True
except ImportError:
    ML_IMPORTS_OK = False
    logging.warning("Les modules de machine learning ne sont pas disponibles.")

# Configuration du logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("contract_analyzer")

@dataclass
class ContractSecurityResult:
    """
    Résultat de l'analyse de sécurité d'un contrat de token.
    """
    contract_address: str
    is_safe: bool
    confidence: float  # 0-100%
    risk_scores: Dict[str, float]  # catégorie de risque -> score (0-1)
    execution_time_ms: float
    high_risk_features: List[str]
    medium_risk_features: List[str]
    low_risk_features: List[str]
    model_used: str
    recommendation: str
    analysis_timestamp: float = field(default_factory=time.time)
    
    @property
    def overall_risk_score(self) -> float:
        """Score de risque global (0-1, où 1 est le plus risqué)."""
        if not self.risk_scores:
            return 0.0
            
        # Exclure le score "secure" du calcul
        risk_only = {k: v for k, v in self.risk_scores.items() if k != "secure"}
        if not risk_only:
            return 0.0
            
        # Le score global est le maximum des scores de risque
        return max(risk_only.values())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit le résultat en dictionnaire."""
        return {
            "contract_address": self.contract_address,
            "is_safe": self.is_safe,
            "confidence": self.confidence,
            "risk_scores": self.risk_scores,
            "overall_risk_score": self.overall_risk_score,
            "execution_time_ms": self.execution_time_ms,
            "high_risk_features": self.high_risk_features,
            "medium_risk_features": self.medium_risk_features,
            "low_risk_features": self.low_risk_features,
            "model_used": self.model_used,
            "recommendation": self.recommendation,
            "analysis_timestamp": self.analysis_timestamp
        }

class LightweightContractAnalyzer:
    """
    Analyseur de contrats utilisant des modèles légers pour une évaluation rapide.
    
    Cette classe utilise des modèles d'IA légers et optimisés pour analyser
    les contrats de tokens et détecter les risques de sécurité avec une
    latence minimale.
    """
    
    def __init__(
        self,
        models_dir: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialise l'analyseur de contrats léger.
        
        Args:
            models_dir: Répertoire contenant les modèles légers
            config: Configuration de l'analyseur
        """
        self.config = config or {}
        self.model_manager = None
        self.contract_security_model = None
        self.token_potential_model = None
        
        # Statistiques d'utilisation
        self.total_analyses = 0
        self.total_execution_time_ms = 0
        self.cache_hits = 0
        self.models_loaded = False
        
        # Cache des résultats d'analyse
        self._analysis_cache: Dict[str, ContractSecurityResult] = {}
        self._cache_ttl_seconds = self.config.get("cache_ttl_seconds", 3600)  # 1 heure par défaut
        self._max_cache_items = self.config.get("max_cache_items", 1000)
        
        # Initialiser le gestionnaire de modèles si les imports sont OK
        if ML_IMPORTS_OK:
            try:
                self.model_manager = create_model_manager(models_dir)
                self._load_models()
            except Exception as e:
                logger.error(f"Erreur lors de l'initialisation du gestionnaire de modèles: {e}")
        else:
            logger.warning("Les modèles légers ne sont pas disponibles. Installation requise.")
    
    def _load_models(self) -> bool:
        """
        Charge les modèles nécessaires pour l'analyse de contrats.
        
        Returns:
            bool: Succès du chargement
        """
        if not self.model_manager:
            return False
            
        try:
            # Charger les modèles par tâche
            contract_security_models = self.model_manager.get_models_by_task(
                ModelTask.CONTRACT_SECURITY, 
                load_if_needed=False
            )
            
            token_potential_models = self.model_manager.get_models_by_task(
                ModelTask.TOKEN_POTENTIAL,
                load_if_needed=False
            )
            
            # Si aucun modèle n'est trouvé, essayer de découvrir et charger les modèles
            if not contract_security_models:
                logger.info("Aucun modèle d'analyse de contrats trouvé, recherche en cours...")
                self.model_manager.load_discovered_models(tasks=["contract_security"])
                contract_security_models = self.model_manager.get_models_by_task(
                    ModelTask.CONTRACT_SECURITY, 
                    load_if_needed=False
                )
            
            # Charger le premier modèle de sécurité de contrat trouvé
            if contract_security_models:
                self.contract_security_model = contract_security_models[0]
                self.contract_security_model.load()
                logger.info(f"Modèle d'analyse de contrats chargé: {self.contract_security_model.name}")
            else:
                logger.warning("Aucun modèle d'analyse de contrats trouvé")
                
            # Charger le premier modèle d'évaluation de potentiel de token trouvé
            if token_potential_models:
                self.token_potential_model = token_potential_models[0]
                self.token_potential_model.load()
                logger.info(f"Modèle d'évaluation de potentiel chargé: {self.token_potential_model.name}")
            
            self.models_loaded = self.contract_security_model is not None
            return self.models_loaded
            
        except Exception as e:
            logger.error(f"Erreur lors du chargement des modèles: {e}")
            return False
    
    def analyze_contract(
        self, 
        contract_address: str, 
        contract_code: Optional[str] = None,
        bytecode: Optional[str] = None
    ) -> ContractSecurityResult:
        """
        Analyse un contrat de token pour détecter les risques de sécurité.
        
        Args:
            contract_address: Adresse du contrat à analyser
            contract_code: Code source du contrat (si disponible)
            bytecode: Bytecode du contrat (si disponible et pas de code source)
            
        Returns:
            ContractSecurityResult: Résultat de l'analyse de sécurité
        """
        # Vérifier si le résultat est dans le cache
        cache_key = self._get_cache_key(contract_address, contract_code, bytecode)
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            self.cache_hits += 1
            return cached_result
        
        # Vérifier si les modèles sont chargés
        if not self.models_loaded and not self._load_models():
            return self._create_fallback_result(
                contract_address,
                "Les modèles d'analyse ne sont pas disponibles"
            )
        
        start_time = time.time()
        
        try:
            # Préparer les données d'entrée pour le modèle
            input_data = self._prepare_contract_input(contract_address, contract_code, bytecode)
            
            # Effectuer l'analyse avec le modèle de sécurité de contrat
            if self.contract_security_model:
                prediction, execution_time_ms = self.contract_security_model.predict(
                    input_data, 
                    cache_key=cache_key
                )
                
                # Traiter les résultats de la prédiction
                result = self._process_contract_security_prediction(
                    contract_address, 
                    prediction, 
                    execution_time_ms
                )
                
                # Mettre en cache le résultat
                self._add_to_cache(cache_key, result)
                
                # Mettre à jour les statistiques
                self.total_analyses += 1
                self.total_execution_time_ms += execution_time_ms
                
                return result
            else:
                return self._create_fallback_result(
                    contract_address,
                    "Modèle d'analyse de contrats non disponible"
                )
                
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse du contrat {contract_address}: {e}")
            execution_time_ms = (time.time() - start_time) * 1000
            
            return self._create_fallback_result(
                contract_address,
                f"Erreur d'analyse: {str(e)}",
                execution_time_ms
            )
    
    def _prepare_contract_input(
        self, 
        contract_address: str, 
        contract_code: Optional[str] = None,
        bytecode: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Prépare les données d'entrée pour le modèle d'analyse de contrat.
        
        Args:
            contract_address: Adresse du contrat
            contract_code: Code source du contrat
            bytecode: Bytecode du contrat
            
        Returns:
            Dict[str, Any]: Données préparées pour le modèle
        """
        # Si le code source est disponible, l'utiliser
        if contract_code:
            # Extraire les fonctions et les caractéristiques importantes
            functions = self._extract_functions(contract_code)
            features = self._extract_security_features(contract_code)
            
            # Créer les entrées pour le modèle
            input_data = {
                "contract_address": contract_address,
                "has_source_code": True,
                "functions": functions,
                "features": features,
                "raw_code": contract_code[:4096]  # Limiter la taille pour les modèles
            }
        
        # Sinon, utiliser le bytecode s'il est disponible
        elif bytecode:
            # Extraire les signatures et patterns du bytecode
            signatures = self._extract_signatures_from_bytecode(bytecode)
            byte_patterns = self._extract_byte_patterns(bytecode)
            
            input_data = {
                "contract_address": contract_address,
                "has_source_code": False,
                "bytecode_signatures": signatures,
                "byte_patterns": byte_patterns,
                "raw_bytecode": bytecode[:1024]  # Limiter la taille
            }
        
        # Si aucune donnée n'est disponible, utiliser uniquement l'adresse
        else:
            input_data = {
                "contract_address": contract_address,
                "has_source_code": False,
                "fallback_analysis": True
            }
        
        return input_data
    
    def _extract_functions(self, code: str) -> List[Dict[str, Any]]:
        """
        Extrait les fonctions du code source du contrat.
        
        Args:
            code: Code source du contrat
            
        Returns:
            List[Dict[str, Any]]: Liste des fonctions extraites
        """
        functions = []
        
        # Extraction simple des déclarations de fonction
        # En production, cette fonction devrait utiliser un parser AST pour plus de précision
        function_pattern = r"function\s+(\w+)\s*\(([^)]*)\)(?:\s+(?:external|public|internal|private))?\s*(?:(?:pure|view|payable))?\s*(?:returns\s*\([^)]*\))?\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}"
        matches = re.finditer(function_pattern, code, re.DOTALL)
        
        for match in matches:
            function_name = match.group(1)
            function_params = match.group(2).strip()
            function_body = match.group(3)
            
            functions.append({
                "name": function_name,
                "params": function_params,
                "body_length": len(function_body),
                "has_owner_check": "owner" in function_body.lower(),
                "is_privileged": any(x in function_body.lower() for x in ["onlyowner", "require(msg.sender", "require(owner", "_owner"]),
                "modifies_state": any(x in function_body.lower() for x in ["=", ".transfer", ".send", "delete"]),
                "uses_low_level": any(x in function_body.lower() for x in ["assembly", "delegatecall", "callcode", "selfdestruct"])
            })
        
        return functions
    
    def _extract_security_features(self, code: str) -> Dict[str, Any]:
        """
        Extrait les caractéristiques de sécurité du code source.
        
        Args:
            code: Code source du contrat
            
        Returns:
            Dict[str, Any]: Caractéristiques de sécurité extraites
        """
        code_lower = code.lower()
        
        return {
            "has_transfer_function": "transfer" in code_lower,
            "has_transferfrom_function": "transferfrom" in code_lower,
            "has_approve_function": "approve(" in code_lower,
            "has_ownership_controls": any(x in code_lower for x in ["ownable", "onlyowner"]),
            "has_pausable": "pausable" in code_lower or "paused" in code_lower,
            "has_blacklist": any(x in code_lower for x in ["blacklist", "blocklist", "banned"]),
            "has_whitelist": "whitelist" in code_lower,
            "has_tax": any(x in code_lower for x in ["tax", "fee", "royalty"]),
            "has_mint": "mint" in code_lower,
            "has_burn": "burn" in code_lower,
            "has_timelock": "timelock" in code_lower,
            "has_selfdestruct": "selfdestruct" in code_lower or "suicide" in code_lower,
            "has_assembly": "assembly" in code_lower,
            "has_delegatecall": "delegatecall" in code_lower,
            "has_reentrancy_guard": "reentrancyguard" in code_lower or "nonreentrant" in code_lower,
            "has_admin_functions": any(x in code_lower for x in ["admin", "setowner", "transferownership"]),
            "has_withdraw_function": any(x in code_lower for x in ["withdraw(", "withdrawall", "withdrawfunds"])
        }
    
    def _extract_signatures_from_bytecode(self, bytecode: str) -> List[str]:
        """
        Extrait les signatures de fonction du bytecode.
        
        Args:
            bytecode: Bytecode du contrat
            
        Returns:
            List[str]: Signatures extraites
        """
        # Modèle simplifié pour extraire les 4 premiers octets des sélecteurs de fonction
        # En production, cette fonction devrait utiliser un décodeur spécifique
        signatures = []
        
        if bytecode.startswith("0x"):
            bytecode = bytecode[2:]
            
        # Chercher les sélecteurs potentiels (4 octets après PUSH4)
        push4_pattern = r"63([0-9a-fA-F]{8})"
        matches = re.finditer(push4_pattern, bytecode)
        
        for match in matches:
            signatures.append(match.group(1))
            
        return signatures[:20]  # Limiter le nombre de signatures
    
    def _extract_byte_patterns(self, bytecode: str) -> Dict[str, bool]:
        """
        Extrait des motifs connus du bytecode pour l'analyse de sécurité.
        
        Args:
            bytecode: Bytecode du contrat
            
        Returns:
            Dict[str, bool]: Motifs détectés
        """
        if bytecode.startswith("0x"):
            bytecode = bytecode[2:]
            
        return {
            # Patterns simplifiés - en production, utiliser des patterns plus précis
            "has_transfer_pattern": "a9059cbb" in bytecode.lower(),  # transfer(address,uint256)
            "has_approve_pattern": "095ea7b3" in bytecode.lower(),  # approve(address,uint256)
            "has_ownership_pattern": "8da5cb5b" in bytecode.lower(),  # owner()
            "has_mint_pattern": "40c10f19" in bytecode.lower(),  # mint(address,uint256)
            "has_pause_pattern": "8456cb59" in bytecode.lower(),  # pause()
            "has_blacklist_pattern": "0a8f1d550" in bytecode.lower(),  # blacklist(address)
            "has_tax_pattern": "a56812e7" in bytecode.lower(),  # setTaxFee(uint256)
            "has_selfdestruct_pattern": "f69be1c1" in bytecode.lower()  # selfdestruct()
        }
    
    def _process_contract_security_prediction(
        self, 
        contract_address: str, 
        prediction: Any, 
        execution_time_ms: float
    ) -> ContractSecurityResult:
        """
        Traite les résultats de la prédiction du modèle de sécurité.
        
        Args:
            contract_address: Adresse du contrat analysé
            prediction: Résultat brut de la prédiction du modèle
            execution_time_ms: Temps d'exécution en millisecondes
            
        Returns:
            ContractSecurityResult: Résultat structuré de l'analyse
        """
        # Obtenir les classes du modèle
        model_metadata = self.contract_security_model.get_metadata()
        classes = model_metadata["metadata"].get("classes", [])
        
        # Traiter la prédiction brute en fonction du format de sortie du modèle
        # (La logique exacte dépend du modèle utilisé)
        prediction_array = prediction
        if isinstance(prediction, dict) and "output" in prediction:
            prediction_array = prediction["output"]
        
        # Normaliser les scores (si nécessaire)
        scores = {}
        if len(classes) > 0 and len(prediction_array) == len(classes):
            for i, class_name in enumerate(classes):
                scores[class_name] = float(prediction_array[i])
        else:
            # Fallback si les classes ne correspondent pas
            scores = {"unknown": 1.0}
        
        # Déterminer si le contrat est sûr
        secure_score = scores.get("secure", 0.0)
        threshold = self.config.get("security_threshold", 0.65)
        is_safe = secure_score >= threshold
        
        # Calculer la confiance du résultat
        confidence = max(list(scores.values())) * 100
        
        # Déterminer les caractéristiques à risque
        high_risk = []
        medium_risk = []
        low_risk = []
        
        for risk_type, score in scores.items():
            if risk_type == "secure":
                continue
                
            risk_description = self._get_risk_description(risk_type)
            
            if score >= 0.7:
                high_risk.append(f"{risk_description} ({score:.2f})")
            elif score >= 0.4:
                medium_risk.append(f"{risk_description} ({score:.2f})")
            elif score >= 0.2:
                low_risk.append(f"{risk_description} ({score:.2f})")
        
        # Générer une recommandation
        recommendation = self._generate_recommendation(is_safe, scores)
        
        # Créer le résultat final
        return ContractSecurityResult(
            contract_address=contract_address,
            is_safe=is_safe,
            confidence=confidence,
            risk_scores=scores,
            execution_time_ms=execution_time_ms,
            high_risk_features=high_risk,
            medium_risk_features=medium_risk,
            low_risk_features=low_risk,
            model_used=self.contract_security_model.name,
            recommendation=recommendation
        )
    
    def _get_risk_description(self, risk_type: str) -> str:
        """
        Retourne une description lisible pour un type de risque.
        
        Args:
            risk_type: Type de risque identifié
            
        Returns:
            str: Description du risque
        """
        descriptions = {
            "honeypot_risk": "Risque de honeypot (impossible de vendre)",
            "rugpull_risk": "Risque de rug pull (retrait de liquidité)",
            "backdoor_risk": "Backdoor potentielle",
            "tax_manipulation_risk": "Manipulation possible des taxes",
            "privileged_functions_risk": "Fonctions privilégiées excessives",
            "transfer_blocking_risk": "Possibilité de bloquer les transferts"
        }
        
        return descriptions.get(risk_type, risk_type.replace("_", " ").title())
    
    def _generate_recommendation(self, is_safe: bool, scores: Dict[str, float]) -> str:
        """
        Génère une recommandation basée sur l'analyse de sécurité.
        
        Args:
            is_safe: Si le contrat est considéré comme sûr
            scores: Scores de risque par catégorie
            
        Returns:
            str: Recommandation
        """
        if is_safe:
            return "Le contrat semble sécurisé. Procéder avec une allocation standard."
        
        # Trouver le risque le plus élevé
        highest_risk = max((score, risk) for risk, score in scores.items() if risk != "secure")
        highest_score, highest_risk_type = highest_risk
        
        if highest_score >= 0.8:
            return f"Ne pas investir. Risque élevé détecté: {self._get_risk_description(highest_risk_type)}."
        elif highest_score >= 0.6:
            return f"Investir avec prudence extrême. Limiter à <10% de l'allocation standard. Risque: {self._get_risk_description(highest_risk_type)}."
        else:
            return "Investir avec prudence. Limiter à 50% de l'allocation standard."
    
    def _get_cache_key(
        self, 
        contract_address: str, 
        contract_code: Optional[str] = None,
        bytecode: Optional[str] = None
    ) -> str:
        """
        Génère une clé de cache pour un contrat.
        
        Args:
            contract_address: Adresse du contrat
            contract_code: Code source du contrat
            bytecode: Bytecode du contrat
            
        Returns:
            str: Clé de cache
        """
        # Si le code source est disponible, l'utiliser pour la clé
        if contract_code:
            code_hash = hashlib.md5(contract_code.encode('utf-8')).hexdigest()
            return f"{contract_address}_{code_hash}"
        
        # Sinon, utiliser le bytecode s'il est disponible
        elif bytecode:
            byte_hash = hashlib.md5(bytecode.encode('utf-8')).hexdigest()
            return f"{contract_address}_{byte_hash}"
        
        # En dernier recours, utiliser uniquement l'adresse
        return contract_address
    
    def _get_from_cache(self, cache_key: str) -> Optional[ContractSecurityResult]:
        """
        Récupère un résultat du cache s'il est valide.
        
        Args:
            cache_key: Clé de cache
            
        Returns:
            Optional[ContractSecurityResult]: Résultat en cache ou None
        """
        if cache_key in self._analysis_cache:
            result = self._analysis_cache[cache_key]
            
            # Vérifier si le résultat est toujours valide
            cache_age = time.time() - result.analysis_timestamp
            if cache_age < self._cache_ttl_seconds:
                return result
                
            # Supprimer le résultat expiré
            del self._analysis_cache[cache_key]
            
        return None
    
    def _add_to_cache(self, cache_key: str, result: ContractSecurityResult) -> None:
        """
        Ajoute un résultat au cache.
        
        Args:
            cache_key: Clé de cache
            result: Résultat à mettre en cache
        """
        # Si le cache est plein, supprimer l'entrée la plus ancienne
        if len(self._analysis_cache) >= self._max_cache_items:
            oldest_key = min(
                self._analysis_cache.keys(),
                key=lambda k: self._analysis_cache[k].analysis_timestamp
            )
            del self._analysis_cache[oldest_key]
            
        # Ajouter le nouveau résultat
        self._analysis_cache[cache_key] = result
    
    def _create_fallback_result(
        self, 
        contract_address: str, 
        reason: str,
        execution_time_ms: float = 0.0
    ) -> ContractSecurityResult:
        """
        Crée un résultat de fallback quand l'analyse normale échoue.
        
        Args:
            contract_address: Adresse du contrat
            reason: Raison de l'échec
            execution_time_ms: Temps d'exécution
            
        Returns:
            ContractSecurityResult: Résultat de fallback
        """
        return ContractSecurityResult(
            contract_address=contract_address,
            is_safe=False,
            confidence=0.0,
            risk_scores={"unknown": 1.0},
            execution_time_ms=execution_time_ms,
            high_risk_features=[],
            medium_risk_features=[f"Analyse incomplète: {reason}"],
            low_risk_features=[],
            model_used="fallback",
            recommendation="Impossible d'analyser ce contrat correctement. Procéder avec une extrême prudence."
        )
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Récupère les statistiques d'utilisation de l'analyseur.
        
        Returns:
            Dict[str, Any]: Statistiques d'utilisation
        """
        avg_execution_time = 0.0
        if self.total_analyses > 0:
            avg_execution_time = self.total_execution_time_ms / self.total_analyses
            
        return {
            "total_analyses": self.total_analyses,
            "avg_execution_time_ms": avg_execution_time,
            "cache_hits": self.cache_hits,
            "cache_size": len(self._analysis_cache),
            "models_loaded": self.models_loaded,
            "available_models": self.model_manager.get_loaded_models() if self.model_manager else []
        }

# Fonction utilitaire pour créer un analyseur avec configuration par défaut
def create_contract_analyzer(
    models_dir: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None
) -> LightweightContractAnalyzer:
    """
    Crée un analyseur de contrats léger avec configuration par défaut.
    
    Args:
        models_dir: Répertoire des modèles (si None, utilise le répertoire par défaut)
        config: Configuration de l'analyseur
        
    Returns:
        LightweightContractAnalyzer: Analyseur de contrats léger
    """
    analyzer = LightweightContractAnalyzer(models_dir, config)
    return analyzer 