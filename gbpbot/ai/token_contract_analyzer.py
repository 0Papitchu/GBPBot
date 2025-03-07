#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module d'analyse rapide des contrats de tokens Solana pour GBPBot
=================================================================

Ce module fournit une analyse optimisée des contrats de tokens Solana
en utilisant des techniques d'IA légères et rapides pour détecter les
potentiels risques (honeypots, rug pulls, etc.) en temps réel.
"""

import os
import json
import logging
import asyncio
import time
from typing import Dict, List, Any, Optional, Set, Tuple, Union
from dataclasses import dataclass

# Configuration du logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("token_contract_analyzer")

# Import de l'analyseur de marché basé sur l'IA et des modules Solana
try:
    from gbpbot.ai import create_ai_client, get_prompt_manager
    from gbpbot.ai.market_analyzer import MarketAnalyzer
    from gbpbot.ai.llm_provider import LLMProvider
    AI_IMPORTS_OK = True
except ImportError as e:
    logger.warning(f"Impossible d'importer les modules d'IA: {str(e)}")
    logger.warning("Les fonctionnalités d'analyse IA ne seront pas disponibles")
    AI_IMPORTS_OK = False

# Essai d'importation des outils d'analyse de contrats Solana
try:
    import base58
    from solana.publickey import PublicKey
    SOLANA_IMPORTS_OK = True
except ImportError as e:
    logger.warning(f"Impossible d'importer les modules Solana: {str(e)}")
    logger.warning("Installation via pip install solana-py")
    SOLANA_IMPORTS_OK = False

# Patterns de risques connus pour les tokens Solana
KNOWN_RISK_PATTERNS = {
    "honeypot": [
        "transfer_hook", 
        "disable_transfer",
        "block_transfer",
        "pause_trading",
        "owner_only",
        "only_whitelist"
    ],
    "rug_pull": [
        "mint_to_owner",
        "unlimited_mint",
        "owner_withdraw",
        "drain_liquidity",
        "hidden_fee",
        "change_fee"
    ],
    "backdoor": [
        "admin_control",
        "emergency_withdraw",
        "rescue_tokens",
        "owner_set_fee"
    ]
}

@dataclass
class ContractAnalysisResult:
    """Résultat de l'analyse d'un contrat de token."""
    is_safe: bool
    risk_score: float  # 0-100, où 0 est le plus risqué et 100 le plus sûr
    risk_factors: List[Dict[str, Any]]
    confidence: float  # 0-100
    execution_time_ms: float
    potential_honeypot: bool
    potential_rug_pull: bool
    unknown_risks: bool
    recommendation: str

class SolanaTokenContractAnalyzer:
    """
    Analyseur de contrats de tokens Solana utilisant des techniques d'IA
    légères pour détecter rapidement les risques potentiels.
    """
    
    def __init__(
        self, 
        ai_client: Optional[LLMProvider] = None,
        config: Optional[Dict[str, Any]] = None,
        risk_patterns_file: Optional[str] = None
    ):
        """
        Initialise l'analyseur de contrats.
        
        Args:
            ai_client: Client IA optionnel pour l'analyse approfondie.
            config: Configuration pour l'analyseur.
            risk_patterns_file: Chemin vers un fichier JSON contenant des patterns à risque additionnels.
        """
        self.config = config or {}
        self.ai_client = ai_client
        self.has_ai = ai_client is not None and AI_IMPORTS_OK
        
        # Paramètres de configuration
        self.min_analysis_confidence = self.config.get("MIN_ANALYSIS_CONFIDENCE", 70)
        self.max_analysis_time_ms = self.config.get("MAX_ANALYSIS_TIME_MS", 300)
        self.strict_mode = self.config.get("STRICT_CONTRACT_ANALYSIS", True)
        
        # Chargement des patterns de risques
        self.risk_patterns = KNOWN_RISK_PATTERNS.copy()
        if risk_patterns_file and os.path.exists(risk_patterns_file):
            try:
                with open(risk_patterns_file, 'r') as f:
                    custom_patterns = json.load(f)
                    for category, patterns in custom_patterns.items():
                        if category in self.risk_patterns:
                            self.risk_patterns[category].extend(patterns)
                        else:
                            self.risk_patterns[category] = patterns
                logger.info(f"Patterns de risques additionnels chargés depuis {risk_patterns_file}")
            except Exception as e:
                logger.error(f"Erreur lors du chargement des patterns de risques: {e}")
        
        if self.has_ai:
            # Si disponible, charger le prompt pour l'analyse de contrats
            try:
                self.prompt_manager = get_prompt_manager()
                self.contract_analysis_prompt = self.prompt_manager.get_prompt_template("token_contract_analysis_prompt")
                logger.info("Template d'analyse de contrats chargé avec succès")
            except Exception as e:
                logger.warning(f"Impossible de charger le template d'analyse de contrats: {e}")
                self.contract_analysis_prompt = None
        
        # Statistiques d'analyse
        self.total_analyzed = 0
        self.honeypots_detected = 0
        self.rugpulls_detected = 0
        self.average_analysis_time_ms = 0
    
    async def quick_analyze_contract(
        self, 
        contract_address: str, 
        contract_code: Optional[str] = None
    ) -> ContractAnalysisResult:
        """
        Analyse rapide d'un contrat de token Solana pour détecter les risques potentiels.
        Si le code du contrat n'est pas fourni, tente de le récupérer via l'API Solana.
        
        Args:
            contract_address: Adresse du contrat à analyser
            contract_code: Code du contrat si disponible
            
        Returns:
            ContractAnalysisResult: Résultat de l'analyse
        """
        start_time = time.time()
        
        if not SOLANA_IMPORTS_OK:
            logger.warning("L'analyse de contrats Solana nécessite les modules Solana")
            return self._create_fallback_result("modules_missing")
        
        # Validation de l'adresse
        try:
            if not contract_address.startswith("So"):
                # Tentative de conversion en PublicKey pour vérifier la validité
                pubkey = PublicKey(contract_address)
                contract_address = str(pubkey)
            
            # Normaliser l'adresse
            if len(contract_address) < 32:
                logger.warning(f"Adresse de contrat Solana potentiellement invalide: {contract_address}")
        except Exception as e:
            logger.error(f"Adresse de contrat invalide: {contract_address} - {str(e)}")
            return self._create_fallback_result("invalid_address") 
        
        # Si le code du contrat n'est pas fourni, on procède à une analyse basique
        if not contract_code:
            logger.info(f"Code du contrat non fourni pour {contract_address}, analyse basique seulement")
            # TODO: Implémentation future pour récupérer le code via l'API Solana
            preliminary_result = self._perform_basic_analysis(contract_address)
            
            # Si l'IA est disponible et que l'analyse basique n'est pas concluante,
            # on peut faire une analyse plus poussée
            if self.has_ai and self.ai_client and preliminary_result.risk_score < 80:
                try:
                    return await self._enhance_with_ai_analysis(preliminary_result, contract_address)
                except Exception as e:
                    logger.error(f"Erreur lors de l'analyse IA: {e}")
                    return preliminary_result
            return preliminary_result
        
        # Analyse détaillée si le code est disponible
        risk_factors = []
        found_patterns = []
        
        # Recherche des patterns à risque dans le code
        for category, patterns in self.risk_patterns.items():
            for pattern in patterns:
                if pattern.lower() in contract_code.lower():
                    found_patterns.append(pattern)
                    risk_factors.append({
                        "category": category,
                        "pattern": pattern,
                        "severity": "high" if category in ["honeypot", "rug_pull"] else "medium"
                    })
        
        # Détermination du niveau de risque global
        is_potential_honeypot = any(factor["category"] == "honeypot" for factor in risk_factors)
        is_potential_rugpull = any(factor["category"] == "rug_pull" for factor in risk_factors)
        
        # Calcul du score de risque (0-100, où 100 est le plus sûr)
        num_high_severity = sum(1 for factor in risk_factors if factor["severity"] == "high")
        num_medium_severity = sum(1 for factor in risk_factors if factor["severity"] == "medium")
        
        base_risk_score = 100
        if num_high_severity > 0:
            base_risk_score -= min(80, num_high_severity * 20)  # Jusqu'à -80 points pour risques élevés
        if num_medium_severity > 0:
            base_risk_score -= min(20, num_medium_severity * 5)  # Jusqu'à -20 points pour risques moyens
        
        risk_score = max(0, min(100, base_risk_score))
        
        # Détermination de la recommandation
        if is_potential_honeypot:
            recommendation = "ÉVITER - Potentiel honeypot détecté"
            self.honeypots_detected += 1
        elif is_potential_rugpull:
            recommendation = "RISQUÉ - Potentiel rug pull détecté"
            self.rugpulls_detected += 1
        elif risk_score < 50:
            recommendation = "PRUDENCE - Risques significatifs détectés"
        elif risk_score < 80:
            recommendation = "ACCEPTABLE - Quelques points d'attention"
        else:
            recommendation = "OK - Aucun risque majeur détecté"
        
        # Si l'IA est disponible, on peut améliorer l'analyse
        basic_result = ContractAnalysisResult(
            is_safe=risk_score >= 70,
            risk_score=risk_score,
            risk_factors=risk_factors,
            confidence=75.0,  # Confiance modérée pour l'analyse basique
            execution_time_ms=(time.time() - start_time) * 1000,
            potential_honeypot=is_potential_honeypot,
            potential_rug_pull=is_potential_rugpull,
            unknown_risks=False,
            recommendation=recommendation
        )
        
        if self.has_ai and self.ai_client:
            try:
                return await self._enhance_with_ai_analysis(basic_result, contract_address, contract_code)
            except Exception as e:
                logger.error(f"Erreur lors de l'analyse IA: {e}")
                return basic_result
        
        self.total_analyzed += 1
        self._update_statistics(basic_result.execution_time_ms)
        
        return basic_result
    
    def _perform_basic_analysis(self, contract_address: str) -> ContractAnalysisResult:
        """
        Effectue une analyse basique du contrat basée sur des heuristiques simples.
        
        Args:
            contract_address: Adresse du contrat
            
        Returns:
            ContractAnalysisResult: Résultat de l'analyse basique
        """
        # Analyse minimale basée sur l'adresse du contrat
        # Par exemple, vérifier si l'adresse suit les conventions Solana
        start_time = time.time()
        
        is_valid_format = True
        try:
            # Vérification basique du format d'adresse Solana
            if not contract_address.startswith("So") or len(contract_address) < 32:
                is_valid_format = False
            
            # Tentative de décoder l'adresse en base58
            _ = base58.b58decode(contract_address)
        except Exception:
            is_valid_format = False
        
        # Sans le code, on peut seulement fournir une estimation très basique
        if not is_valid_format:
            return self._create_fallback_result("invalid_format")
        
        # Dans le doute, on recommande la prudence
        result = ContractAnalysisResult(
            is_safe=False,  # Sans code à analyser, on ne peut pas garantir la sécurité
            risk_score=50.0,  # Score neutre
            risk_factors=[{
                "category": "unknown",
                "pattern": "code_unavailable",
                "severity": "medium",
                "description": "Le code du contrat n'est pas disponible pour analyse"
            }],
            confidence=30.0,  # Faible confiance
            execution_time_ms=(time.time() - start_time) * 1000,
            potential_honeypot=False,
            potential_rug_pull=False,
            unknown_risks=True,
            recommendation="PRUDENCE - Analyse limitée sans accès au code source"
        )
        
        self.total_analyzed += 1
        self._update_statistics(result.execution_time_ms)
        
        return result
    
    async def _enhance_with_ai_analysis(
        self, 
        base_result: ContractAnalysisResult, 
        contract_address: str,
        contract_code: Optional[str] = None
    ) -> ContractAnalysisResult:
        """
        Améliore l'analyse de base avec des insights IA si possible.
        
        Args:
            base_result: Résultat de l'analyse basique
            contract_address: Adresse du contrat
            contract_code: Code du contrat si disponible
            
        Returns:
            ContractAnalysisResult: Résultat amélioré
        """
        if not self.has_ai or not self.ai_client or not self.contract_analysis_prompt:
            return base_result
        
        start_time = time.time()
        ai_timeout_seconds = self.max_analysis_time_ms / 1000
        
        try:
            # Préparation des données pour l'analyse IA
            contract_info = {
                "address": contract_address,
                "risk_factors": base_result.risk_factors,
                "code_snippet": contract_code[:5000] if contract_code else "Non disponible"
            }
            
            # Formatage du prompt avec les informations du contrat
            prompt = self.prompt_manager.format_prompt(
                "token_contract_analysis_prompt", 
                contract_info=json.dumps(contract_info, indent=2)
            )
            
            # Obtention de l'analyse IA avec timeout
            ai_analysis_task = self.ai_client.generate(prompt, max_tokens=1000)
            ai_analysis = await asyncio.wait_for(ai_analysis_task, timeout=ai_timeout_seconds)
            
            # Traitement de la réponse IA
            ai_result = self._extract_ai_analysis(ai_analysis)
            
            if ai_result:
                # Fusion des résultats de base et de l'IA
                enhanced_result = ContractAnalysisResult(
                    is_safe=ai_result.get("is_safe", base_result.is_safe),
                    risk_score=ai_result.get("risk_score", base_result.risk_score),
                    risk_factors=ai_result.get("risk_factors", base_result.risk_factors),
                    confidence=ai_result.get("confidence", base_result.confidence),
                    execution_time_ms=(time.time() - start_time) * 1000 + base_result.execution_time_ms,
                    potential_honeypot=ai_result.get("potential_honeypot", base_result.potential_honeypot),
                    potential_rug_pull=ai_result.get("potential_rug_pull", base_result.potential_rug_pull),
                    unknown_risks=ai_result.get("unknown_risks", base_result.unknown_risks),
                    recommendation=ai_result.get("recommendation", base_result.recommendation)
                )
                
                return enhanced_result
            
        except asyncio.TimeoutError:
            logger.warning(f"Timeout lors de l'analyse IA du contrat {contract_address}")
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse IA du contrat {contract_address}: {e}")
        
        return base_result
    
    def _extract_ai_analysis(self, ai_response: str) -> Optional[Dict[str, Any]]:
        """
        Extrait les informations structurées de la réponse IA.
        
        Args:
            ai_response: Réponse brute de l'IA
            
        Returns:
            Optional[Dict[str, Any]]: Informations structurées ou None en cas d'échec
        """
        try:
            # Recherche de contenu JSON dans la réponse
            import re
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', ai_response)
            
            if json_match:
                json_str = json_match.group(1)
                return json.loads(json_str)
            
            # Deuxième tentative sans les backticks
            json_match = re.search(r'\{[\s\S]*\}', ai_response)
            if json_match:
                json_str = json_match.group(0)
                return json.loads(json_str)
            
            logger.warning("Impossible d'extraire JSON de la réponse IA")
            return None
            
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction des données IA: {e}")
            return None
    
    def _create_fallback_result(self, reason: str) -> ContractAnalysisResult:
        """
        Crée un résultat par défaut en cas d'échec d'analyse.
        
        Args:
            reason: Raison de l'échec
            
        Returns:
            ContractAnalysisResult: Résultat par défaut
        """
        if reason == "modules_missing":
            return ContractAnalysisResult(
                is_safe=False,
                risk_score=0.0,
                risk_factors=[{
                    "category": "error",
                    "pattern": "modules_missing",
                    "severity": "high",
                    "description": "Modules Solana requis manquants"
                }],
                confidence=100.0,
                execution_time_ms=0.0,
                potential_honeypot=False,
                potential_rug_pull=False,
                unknown_risks=True,
                recommendation="IMPOSSIBLE - Modules requis manquants"
            )
        elif reason == "invalid_address":
            return ContractAnalysisResult(
                is_safe=False,
                risk_score=0.0,
                risk_factors=[{
                    "category": "error",
                    "pattern": "invalid_address",
                    "severity": "high",
                    "description": "Adresse de contrat invalide"
                }],
                confidence=100.0,
                execution_time_ms=0.0,
                potential_honeypot=False,
                potential_rug_pull=False,
                unknown_risks=True,
                recommendation="IMPOSSIBLE - Adresse de contrat invalide"
            )
        elif reason == "invalid_format":
            return ContractAnalysisResult(
                is_safe=False,
                risk_score=20.0,
                risk_factors=[{
                    "category": "warning",
                    "pattern": "invalid_format",
                    "severity": "medium",
                    "description": "Format d'adresse inhabituel"
                }],
                confidence=70.0,
                execution_time_ms=0.0,
                potential_honeypot=False,
                potential_rug_pull=False,
                unknown_risks=True,
                recommendation="PRUDENCE - Format d'adresse inhabituel"
            )
        else:
            return ContractAnalysisResult(
                is_safe=False,
                risk_score=0.0,
                risk_factors=[{
                    "category": "error",
                    "pattern": "unknown_error",
                    "severity": "high",
                    "description": f"Erreur inconnue: {reason}"
                }],
                confidence=100.0,
                execution_time_ms=0.0,
                potential_honeypot=False,
                potential_rug_pull=False,
                unknown_risks=True,
                recommendation="IMPOSSIBLE - Erreur inconnue"
            )
    
    def _update_statistics(self, execution_time_ms: float) -> None:
        """
        Met à jour les statistiques d'analyse.
        
        Args:
            execution_time_ms: Temps d'exécution de l'analyse en ms
        """
        # Mise à jour du temps moyen d'analyse
        if self.total_analyzed == 1:
            self.average_analysis_time_ms = execution_time_ms
        else:
            self.average_analysis_time_ms = (
                ((self.total_analyzed - 1) * self.average_analysis_time_ms + execution_time_ms) / 
                self.total_analyzed
            )
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Retourne les statistiques d'analyse.
        
        Returns:
            Dict[str, Any]: Statistiques d'analyse
        """
        return {
            "total_analyzed": self.total_analyzed,
            "honeypots_detected": self.honeypots_detected,
            "rugpulls_detected": self.rugpulls_detected,
            "average_analysis_time_ms": self.average_analysis_time_ms,
            "has_ai": self.has_ai
        }

# Fonction d'aide pour créer un analyseur avec configuration par défaut
def create_token_contract_analyzer(
    ai_client: Optional[LLMProvider] = None,
    config: Optional[Dict[str, Any]] = None,
    risk_patterns_file: Optional[str] = None
) -> SolanaTokenContractAnalyzer:
    """
    Crée un analyseur de contrats Solana avec configuration par défaut.
    
    Args:
        ai_client: Client IA optionnel
        config: Configuration personnalisée
        risk_patterns_file: Fichier de patterns de risques
        
    Returns:
        SolanaTokenContractAnalyzer: Instance de l'analyseur
    """
    if ai_client is None and AI_IMPORTS_OK:
        try:
            # Tentative de création d'un client IA par défaut
            from gbpbot.ai import create_ai_client
            ai_client = create_ai_client()
            if ai_client:
                logger.info("Client IA créé automatiquement pour l'analyseur de contrats")
        except Exception as e:
            logger.warning(f"Impossible de créer un client IA par défaut: {e}")
    
    return SolanaTokenContractAnalyzer(
        ai_client=ai_client,
        config=config,
        risk_patterns_file=risk_patterns_file
    ) 