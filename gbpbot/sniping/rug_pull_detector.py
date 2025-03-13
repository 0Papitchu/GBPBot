"""
Détecteur avancé de rug pulls pour GBPBot
=========================================

Ce module permet d'analyser les tokens pour détecter les signes potentiels
de rug pulls, en utilisant des techniques avancées d'analyse de contrats,
de liquidité et de comportement des développeurs.
"""

import logging
import asyncio
import time
from typing import Dict, List, Tuple, Any, Optional
import re

from gbpbot.utils.logging_utils import setup_logger
from gbpbot.config.trading_config import TradingConfig

logger = logging.getLogger(__name__)

class RugPullDetector:
    """
    Détecteur avancé de rug pulls utilisant plusieurs techniques
    pour identifier les signes de scams potentiels.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialise le détecteur de rug pulls.
        
        Args:
            config: Configuration optionnelle
        """
        self.config = config or {}
        self.risk_thresholds = self.config.get("risk_thresholds", {
            "dev_wallet_percentage": 20.0,  # % max de tokens détenus par le dev wallet
            "liquidity_percentage": 3.0,    # % min de liquidité par rapport au market cap
            "min_liquidity_lock_days": 30,  # Nombre minimum de jours de verrouillage de liquidité
            "max_buy_tax": 10.0,            # Taxe maximum à l'achat en %
            "max_sell_tax": 15.0,           # Taxe maximum à la vente en %
            "max_total_tax": 20.0,          # Taxe totale maximum en %
            "max_holder_concentration": 60.0, # % max pour les 10 premiers wallets
            "malicious_function_score": 80,  # Score à partir duquel les fonctions sont considérées malveillantes
        })
        
        # Patterns pour les fonctions malveillantes dans les contrats
        self.malicious_function_patterns = [
            r"blacklist|disable|block|ban|exclude",  # Fonctions de blacklist
            r"setTax(?!esExempt)|updateFee|changeFee",  # Changement dynamique de taxes
            r"setMax(?:Tx|Transaction|Wallet|Hold)",  # Limitations dynamiques
            r"pause(?:Trading|Transaction|Swap)",  # Pause des transactions
            r"owner(?:Transfer|Only|WithdrawToken)",  # Privilèges spéciaux des propriétaires
            r"migrat|upgrade|newOwner",  # Migrations et changements de propriétaire
            r"steal|drain|extract(?!Eth)",  # Fonctions de drainage explicites
            r"setWhale|setBot|setBuyLimit",  # Contrôles spécifiques de limites
            r"emergencyWithdraw|rescueToken",  # Fonctions de "secours" suspectes
            r"setRouter|changeDex|setLpPair"  # Changement de routeur/DEX
        ]
        
        # Initialiser le logger
        self.logger = setup_logger("RugPullDetector", level=logging.INFO)
        self.logger.info("RugPullDetector initialized with risk thresholds: %s", self.risk_thresholds)
    
    async def analyze_token(self, token_address: str, blockchain_client, pair_address: str = None) -> Dict[str, Any]:
        """
        Analyse complète d'un token pour détecter les signes de rug pull.
        
        Args:
            token_address: Adresse du contrat du token
            blockchain_client: Client blockchain pour les requêtes
            pair_address: Adresse de la paire de liquidité (optionnel)
            
        Returns:
            Dictionnaire contenant le score de risque et les problèmes détectés
        """
        self.logger.info(f"Analyzing token {token_address} for rug pull signals")
        
        # Résultats
        results = {
            "token_address": token_address,
            "is_potential_rug": False,
            "risk_score": 0,  # 0-100, 100 étant le plus risqué
            "issues": [],
            "warnings": [],
            "safe_signals": [],
            "contract_analysis": {},
            "ownership_analysis": {},
            "liquidity_analysis": {},
            "historical_analysis": {}
        }
        
        try:
            # 1. Analyse du contrat
            contract_analysis = await self._analyze_contract(token_address, blockchain_client)
            results["contract_analysis"] = contract_analysis
            
            # 2. Analyse de la distribution des tokens
            ownership_analysis = await self._analyze_token_distribution(token_address, blockchain_client)
            results["ownership_analysis"] = ownership_analysis
            
            # 3. Analyse de la liquidité
            liquidity_analysis = await self._analyze_liquidity(token_address, blockchain_client, pair_address)
            results["liquidity_analysis"] = liquidity_analysis
            
            # 4. Analyse historique (si disponible)
            historical_analysis = await self._analyze_historical_data(token_address, blockchain_client)
            results["historical_analysis"] = historical_analysis
            
            # Calculer le score de risque global
            risk_score = self._calculate_risk_score(
                contract_analysis, 
                ownership_analysis, 
                liquidity_analysis,
                historical_analysis
            )
            
            # Déterminer si c'est un rug pull potentiel
            is_potential_rug = risk_score > 65
            critical_issues = sum(1 for issue in results["issues"] if issue.get("severity") == "critical")
            
            # Un token avec 2+ problèmes critiques est considéré comme un rug pull potentiel
            if critical_issues >= 2:
                is_potential_rug = True
            
            results["risk_score"] = risk_score
            results["is_potential_rug"] = is_potential_rug
            
            self.logger.info(f"Analysis complete for {token_address}. Risk score: {risk_score}/100, Potential rug: {is_potential_rug}")
            
        except Exception as e:
            self.logger.error(f"Error analyzing token {token_address}: {str(e)}")
            results["issues"].append({
                "type": "analysis_error",
                "message": f"Error during analysis: {str(e)}",
                "severity": "high"
            })
            results["risk_score"] = 75  # Score élevé par défaut en cas d'erreur
            results["is_potential_rug"] = True  # Considéré comme risqué si l'analyse échoue
            
        return results
    
    async def _analyze_contract(self, token_address: str, blockchain_client) -> Dict[str, Any]:
        """
        Analyse le code du contrat pour détecter des fonctions malveillantes.
        
        Args:
            token_address: Adresse du contrat du token
            blockchain_client: Client blockchain pour les requêtes
            
        Returns:
            Résultats de l'analyse du contrat
        """
        results = {
            "is_verified": False,
            "has_malicious_functions": False,
            "malicious_functions": [],
            "has_honeypot_signs": False,
            "honeypot_signs": [],
            "has_proxy": False,
            "has_mint_function": False,
            "has_blacklist_function": False,
            "tax_functions": [],
            "buy_tax": 0.0,
            "sell_tax": 0.0,
            "issues": []
        }
        
        try:
            # Vérifier si le contrat est vérifié
            contract_info = await blockchain_client.get_contract_info(token_address)
            results["is_verified"] = contract_info.get("is_verified", False)
            
            if not results["is_verified"]:
                results["issues"].append({
                    "type": "unverified_contract",
                    "message": "Le contrat n'est pas vérifié, impossible d'analyser le code source",
                    "severity": "critical"
                })
                return results
            
            # Récupérer le code source
            source_code = await blockchain_client.get_contract_source(token_address)
            
            if not source_code:
                results["issues"].append({
                    "type": "source_code_unavailable",
                    "message": "Code source indisponible malgré la vérification",
                    "severity": "high"
                })
                return results
            
            # Vérifier les fonctions malveillantes
            malicious_functions = self._check_malicious_functions(source_code)
            results["malicious_functions"] = malicious_functions
            results["has_malicious_functions"] = len(malicious_functions) > 0
            
            # Vérifier les signes de honeypot
            honeypot_signs = self._check_honeypot_signs(source_code)
            results["honeypot_signs"] = honeypot_signs
            results["has_honeypot_signs"] = len(honeypot_signs) > 0
            
            # Vérifier la présence de fonctions proxy ou de délégation
            results["has_proxy"] = "delegatecall" in source_code or "proxy" in source_code.lower()
            
            # Vérifier la présence de fonctions de mint
            results["has_mint_function"] = "mint" in source_code.lower() and "function" in source_code.lower()
            
            # Vérifier la présence de fonctions de blacklist
            results["has_blacklist_function"] = any(
                re.search(r"function\s+.*blacklist", source_code, re.IGNORECASE) 
                for pattern in ["blacklist", "blocklist", "ban", "exclude"]
            )
            
            # Extraire les informations sur les taxes
            tax_info = self._extract_tax_info(source_code)
            results.update(tax_info)
            
            # Ajouter les problèmes critiques
            if results["has_malicious_functions"]:
                results["issues"].append({
                    "type": "malicious_functions",
                    "message": f"Le contrat contient {len(malicious_functions)} fonctions potentiellement malveillantes",
                    "severity": "critical",
                    "details": malicious_functions
                })
                
            if results["has_honeypot_signs"]:
                results["issues"].append({
                    "type": "honeypot_signs",
                    "message": f"Le contrat présente {len(honeypot_signs)} signes de honeypot",
                    "severity": "critical",
                    "details": honeypot_signs
                })
                
            if results["has_proxy"]:
                results["issues"].append({
                    "type": "proxy_contract",
                    "message": "Le contrat utilise un mécanisme de proxy/délégation qui peut cacher des fonctions malveillantes",
                    "severity": "high"
                })
                
            if results["has_mint_function"]:
                results["issues"].append({
                    "type": "mint_function",
                    "message": "Le contrat possède une fonction de mint qui peut être utilisée pour créer de nouveaux tokens",
                    "severity": "medium"
                })
                
            if results["has_blacklist_function"]:
                results["issues"].append({
                    "type": "blacklist_function",
                    "message": "Le contrat possède une fonction de blacklist qui peut empêcher certains wallets de vendre",
                    "severity": "high"
                })
                
            # Vérifier les taxes excessives
            if results["buy_tax"] > self.risk_thresholds["max_buy_tax"]:
                results["issues"].append({
                    "type": "high_buy_tax",
                    "message": f"Taxe d'achat excessive: {results['buy_tax']}% (max recommandé: {self.risk_thresholds['max_buy_tax']}%)",
                    "severity": "medium"
                })
                
            if results["sell_tax"] > self.risk_thresholds["max_sell_tax"]:
                results["issues"].append({
                    "type": "high_sell_tax",
                    "message": f"Taxe de vente excessive: {results['sell_tax']}% (max recommandé: {self.risk_thresholds['max_sell_tax']}%)",
                    "severity": "high"
                })
                
            total_tax = results["buy_tax"] + results["sell_tax"]
            if total_tax > self.risk_thresholds["max_total_tax"]:
                results["issues"].append({
                    "type": "high_total_tax",
                    "message": f"Taxes totales excessives: {total_tax}% (max recommandé: {self.risk_thresholds['max_total_tax']}%)",
                    "severity": "high"
                })
            
        except Exception as e:
            self.logger.error(f"Error in contract analysis for {token_address}: {str(e)}")
            results["issues"].append({
                "type": "contract_analysis_error",
                "message": f"Erreur d'analyse du contrat: {str(e)}",
                "severity": "medium"
            })
            
        return results
    
    async def _analyze_token_distribution(self, token_address: str, blockchain_client) -> Dict[str, Any]:
        """
        Analyse la distribution des tokens pour détecter des concentrations suspectes.
        
        Args:
            token_address: Adresse du contrat du token
            blockchain_client: Client blockchain pour les requêtes
            
        Returns:
            Résultats de l'analyse de distribution
        """
        results = {
            "top_holders": [],
            "dev_wallet_percentage": 0.0,
            "top10_percentage": 0.0,
            "liquidity_percentage": 0.0,
            "token_total_supply": 0,
            "issues": []
        }
        
        try:
            # Récupérer la distribution des tokens
            holders = await blockchain_client.get_token_holders(token_address)
            
            if not holders:
                results["issues"].append({
                    "type": "distribution_data_unavailable",
                    "message": "Données de distribution indisponibles",
                    "severity": "medium"
                })
                return results
                
            results["top_holders"] = holders[:10]  # Top 10 détenteurs
            
            # Calculer le pourcentage total détenu par les 10 premiers wallets
            total_supply = await blockchain_client.get_token_total_supply(token_address)
            results["token_total_supply"] = total_supply
            
            if total_supply > 0:
                top10_tokens = sum(holder["balance"] for holder in holders[:10])
                results["top10_percentage"] = (top10_tokens / total_supply) * 100
                
                # Identifier le wallet du développeur (généralement le top 1)
                if holders:
                    results["dev_wallet_percentage"] = (holders[0]["balance"] / total_supply) * 100
                    
                # Identifier le wallet de liquidité (généralement un contract)
                liquidity_wallets = [h for h in holders if h.get("is_contract", False)]
                if liquidity_wallets:
                    liquidity_tokens = sum(w["balance"] for w in liquidity_wallets)
                    results["liquidity_percentage"] = (liquidity_tokens / total_supply) * 100
                
            # Ajouter les problèmes potentiels
            if results["dev_wallet_percentage"] > self.risk_thresholds["dev_wallet_percentage"]:
                results["issues"].append({
                    "type": "high_dev_concentration",
                    "message": f"Wallet développeur détient {results['dev_wallet_percentage']:.2f}% des tokens (max recommandé: {self.risk_thresholds['dev_wallet_percentage']}%)",
                    "severity": "critical"
                })
                
            if results["top10_percentage"] > self.risk_thresholds["max_holder_concentration"]:
                results["issues"].append({
                    "type": "high_holder_concentration",
                    "message": f"Top 10 wallets détiennent {results['top10_percentage']:.2f}% des tokens (max recommandé: {self.risk_thresholds['max_holder_concentration']}%)",
                    "severity": "high"
                })
                
            if results["liquidity_percentage"] < self.risk_thresholds["liquidity_percentage"]:
                results["issues"].append({
                    "type": "low_liquidity_percentage",
                    "message": f"Faible pourcentage en liquidité: {results['liquidity_percentage']:.2f}% (min recommandé: {self.risk_thresholds['liquidity_percentage']}%)",
                    "severity": "high"
                })
                
        except Exception as e:
            self.logger.error(f"Error in token distribution analysis for {token_address}: {str(e)}")
            results["issues"].append({
                "type": "distribution_analysis_error",
                "message": f"Erreur d'analyse de distribution: {str(e)}",
                "severity": "medium"
            })
            
        return results
    
    async def _analyze_liquidity(self, token_address: str, blockchain_client, pair_address: str = None) -> Dict[str, Any]:
        """
        Analyse la liquidité du token et son verrouillage.
        
        Args:
            token_address: Adresse du contrat du token
            blockchain_client: Client blockchain pour les requêtes
            pair_address: Adresse de la paire de liquidité (optionnel)
            
        Returns:
            Résultats de l'analyse de liquidité
        """
        results = {
            "liquidity_locked": False,
            "liquidity_lock_duration_days": 0,
            "liquidity_usd": 0.0,
            "market_cap_usd": 0.0,
            "liquidity_to_mcap_ratio": 0.0,
            "issues": []
        }
        
        try:
            # Récupérer les infos de liquidité
            if not pair_address:
                pair_info = await blockchain_client.get_token_pair_info(token_address)
                pair_address = pair_info.get("pair_address") if pair_info else None
                
            if not pair_address:
                results["issues"].append({
                    "type": "liquidity_data_unavailable",
                    "message": "Adresse de paire de liquidité indisponible",
                    "severity": "medium"
                })
                return results
                
            # Vérifier la liquidité totale
            liquidity_info = await blockchain_client.get_pair_liquidity(pair_address)
            results["liquidity_usd"] = liquidity_info.get("liquidity_usd", 0)
            
            # Vérifier le market cap
            token_price = liquidity_info.get("token_price_usd", 0)
            total_supply = await blockchain_client.get_token_total_supply(token_address)
            results["market_cap_usd"] = token_price * total_supply
            
            # Calculer le ratio liquidité/market cap
            if results["market_cap_usd"] > 0:
                results["liquidity_to_mcap_ratio"] = (results["liquidity_usd"] / results["market_cap_usd"]) * 100
            
            # Vérifier si la liquidité est verrouillée
            lock_info = await blockchain_client.get_liquidity_lock_info(pair_address)
            results["liquidity_locked"] = lock_info.get("is_locked", False)
            results["liquidity_lock_duration_days"] = lock_info.get("lock_days", 0)
            
            # Ajouter les problèmes potentiels
            if not results["liquidity_locked"]:
                results["issues"].append({
                    "type": "liquidity_not_locked",
                    "message": "La liquidité n'est pas verrouillée, ce qui représente un risque important de rug pull",
                    "severity": "critical"
                })
            elif results["liquidity_lock_duration_days"] < self.risk_thresholds["min_liquidity_lock_days"]:
                results["issues"].append({
                    "type": "short_liquidity_lock",
                    "message": f"Verrouillage de liquidité court: {results['liquidity_lock_duration_days']} jours (min recommandé: {self.risk_thresholds['min_liquidity_lock_days']} jours)",
                    "severity": "high"
                })
                
            if results["liquidity_to_mcap_ratio"] < self.risk_thresholds["liquidity_percentage"]:
                results["issues"].append({
                    "type": "low_liquidity_ratio",
                    "message": f"Faible ratio liquidité/market cap: {results['liquidity_to_mcap_ratio']:.2f}% (min recommandé: {self.risk_thresholds['liquidity_percentage']}%)",
                    "severity": "high"
                })
                
            if results["liquidity_usd"] < 5000:
                results["issues"].append({
                    "type": "very_low_liquidity",
                    "message": f"Liquidité très faible: ${results['liquidity_usd']:.2f} (risque de manipulation de prix élevé)",
                    "severity": "high" if results["liquidity_usd"] < 1000 else "medium"
                })
            
        except Exception as e:
            self.logger.error(f"Error in liquidity analysis for {token_address}: {str(e)}")
            results["issues"].append({
                "type": "liquidity_analysis_error",
                "message": f"Erreur d'analyse de liquidité: {str(e)}",
                "severity": "medium"
            })
            
        return results
    
    async def _analyze_historical_data(self, token_address: str, blockchain_client) -> Dict[str, Any]:
        """
        Analyse les données historiques du token pour détecter des comportements suspects.
        
        Args:
            token_address: Adresse du contrat du token
            blockchain_client: Client blockchain pour les requêtes
            
        Returns:
            Résultats de l'analyse historique
        """
        results = {
            "creation_time": None,
            "age_days": 0,
            "recent_large_transfers": [],
            "recent_sells_by_team": [],
            "issues": []
        }
        
        try:
            # Récupérer la date de création du token
            creation_info = await blockchain_client.get_token_creation_info(token_address)
            results["creation_time"] = creation_info.get("creation_time")
            
            if results["creation_time"]:
                # Calculer l'âge du token en jours
                current_time = time.time()
                results["age_days"] = (current_time - results["creation_time"]) / (24 * 3600)
                
                # Tokens récents (moins de 24h) sont plus risqués
                if results["age_days"] < 1:
                    results["issues"].append({
                        "type": "very_new_token",
                        "message": f"Token très récent ({results['age_days']:.2f} jours), risque élevé",
                        "severity": "high"
                    })
                elif results["age_days"] < 3:
                    results["issues"].append({
                        "type": "new_token",
                        "message": f"Token récent ({results['age_days']:.2f} jours), risque modéré",
                        "severity": "medium"
                    })
            
            # Récupérer les gros transferts récents
            recent_transfers = await blockchain_client.get_recent_token_transfers(
                token_address,
                limit=20,
                min_value_usd=5000  # Transfers > $5000
            )
            results["recent_large_transfers"] = recent_transfers
            
            # Identifier les wallets de l'équipe (dev, marketing, etc.)
            team_wallets = await blockchain_client.get_token_team_wallets(token_address)
            
            # Vérifier les ventes récentes par l'équipe
            recent_sells = await blockchain_client.get_recent_token_sells(
                token_address,
                wallets=team_wallets,
                limit=10
            )
            results["recent_sells_by_team"] = recent_sells
            
            # Évaluer les risques liés à l'historique
            if recent_sells and len(recent_sells) > 0:
                total_sold_usd = sum(sell.get("value_usd", 0) for sell in recent_sells)
                
                if total_sold_usd > 10000:
                    results["issues"].append({
                        "type": "team_selling",
                        "message": f"L'équipe a vendu récemment pour ${total_sold_usd:.2f}, signe potentiel de rug pull",
                        "severity": "critical"
                    })
                elif total_sold_usd > 1000:
                    results["issues"].append({
                        "type": "team_small_selling",
                        "message": f"L'équipe a vendu récemment pour ${total_sold_usd:.2f}, risque modéré",
                        "severity": "medium"
                    })
            
        except Exception as e:
            self.logger.error(f"Error in historical analysis for {token_address}: {str(e)}")
            results["issues"].append({
                "type": "historical_analysis_error",
                "message": f"Erreur d'analyse historique: {str(e)}",
                "severity": "low"
            })
            
        return results
    
    def _calculate_risk_score(self, contract_analysis, ownership_analysis, 
                             liquidity_analysis, historical_analysis) -> int:
        """
        Calcule un score de risque global basé sur toutes les analyses.
        
        Returns:
            Score de risque entre 0 et 100
        """
        score = 0
        max_score = 100
        
        # Analyse du contrat (40% du score total)
        if contract_analysis.get("has_malicious_functions"):
            score += 25
        if contract_analysis.get("has_honeypot_signs"):
            score += 35
        if contract_analysis.get("has_proxy"):
            score += 15
        if contract_analysis.get("has_mint_function"):
            score += 10
        if contract_analysis.get("has_blacklist_function"):
            score += 20
            
        # Taxes (10% du score total)
        buy_tax = contract_analysis.get("buy_tax", 0)
        sell_tax = contract_analysis.get("sell_tax", 0)
        total_tax = buy_tax + sell_tax
        
        if total_tax > self.risk_thresholds["max_total_tax"]:
            score += 10
        elif total_tax > self.risk_thresholds["max_total_tax"] / 2:
            score += 5
            
        # Distribution des tokens (20% du score total)
        dev_wallet_percentage = ownership_analysis.get("dev_wallet_percentage", 0)
        top10_percentage = ownership_analysis.get("top10_percentage", 0)
        
        if dev_wallet_percentage > self.risk_thresholds["dev_wallet_percentage"]:
            score += min(20, dev_wallet_percentage / 2)
        
        if top10_percentage > self.risk_thresholds["max_holder_concentration"]:
            score += min(15, (top10_percentage - self.risk_thresholds["max_holder_concentration"]) / 2)
            
        # Liquidité (20% du score total)
        if not liquidity_analysis.get("liquidity_locked", False):
            score += 20
        elif liquidity_analysis.get("liquidity_lock_duration_days", 0) < self.risk_thresholds["min_liquidity_lock_days"]:
            score += 10
            
        liquidity_ratio = liquidity_analysis.get("liquidity_to_mcap_ratio", 0)
        if liquidity_ratio < self.risk_thresholds["liquidity_percentage"]:
            score += min(15, (self.risk_thresholds["liquidity_percentage"] - liquidity_ratio) * 2)
            
        # Historique (10% du score total)
        age_days = historical_analysis.get("age_days", 0)
        if age_days < 1:
            score += 10
        elif age_days < 3:
            score += 5
            
        recent_sells = historical_analysis.get("recent_sells_by_team", [])
        if recent_sells:
            total_sold_usd = sum(sell.get("value_usd", 0) for sell in recent_sells)
            if total_sold_usd > 10000:
                score += 10
            elif total_sold_usd > 1000:
                score += 5
                
        # Limiter le score à 100
        return min(max_score, int(score))
    
    def _check_malicious_functions(self, source_code: str) -> List[Dict[str, Any]]:
        """
        Vérifie la présence de fonctions malveillantes dans le code source.
        
        Args:
            source_code: Code source du contrat
            
        Returns:
            Liste des fonctions malveillantes détectées
        """
        malicious_functions = []
        
        for pattern in self.malicious_function_patterns:
            matches = re.finditer(f"function\\s+(\\w+)\\s*\\(.*\\).*{pattern}", source_code, re.IGNORECASE)
            for match in matches:
                function_name = match.group(1)
                function_context = source_code[max(0, match.start() - 50):min(len(source_code), match.end() + 150)]
                malicious_functions.append({
                    "name": function_name,
                    "pattern": pattern,
                    "context": function_context,
                    "risk": "high"
                })
                
        return malicious_functions
    
    def _check_honeypot_signs(self, source_code: str) -> List[Dict[str, Any]]:
        """
        Vérifie la présence de signes de honeypot dans le code source.
        
        Args:
            source_code: Code source du contrat
            
        Returns:
            Liste des signes de honeypot détectés
        """
        honeypot_signs = []
        
        # Patterns typiques des honeypots
        honeypot_patterns = [
            (r"require\s*\(\s*!?\s*isBot\s*\[\s*(\w+)\s*\]\s*", "isBot check"),
            (r"require\s*\(\s*canSell\s*", "canSell restriction"),
            (r"require\s*\(\s*balanceOf\s*\[\s*msg\.sender\s*\]\s*[<>=]=\s*", "balance check for selling"),
            (r"require\s*\(\s*sellLimit\s*[<>=]=\s*", "sell limit restriction"),
            (r"if\s*\(\s*to\s*==\s*(\w+)\s*\)\s*{\s*return\s*false\s*;\s*}", "blocked sell to specific address"),
            (r"if\s*\(\s*from\s*==\s*(\w+)\s*&&\s*to\s*==\s*(\w+)\s*\)\s*{\s*return\s*false\s*;\s*}", "blocked specific transfer path"),
            (r"onlyOwner\s*\(\s*\)\s*{\s*_basicTransfer", "owner-only transfer bypass"),
            (r"if\s*\(\s*.*sellEnabled\s*==\s*false", "sell enabled flag"),
            (r"require\s*\(\s*tradingEnabled", "trading enabled flag"),
            (r"if\s*\(\s*block\.timestamp\s*[<>]\s*(\w+)\s*\)\s*{\s*require\s*\(\s*", "time-based sell restriction")
        ]
        
        for pattern, description in honeypot_patterns:
            if re.search(pattern, source_code, re.IGNORECASE):
                honeypot_signs.append({
                    "pattern": pattern,
                    "description": description,
                    "risk": "critical"
                })
                
        return honeypot_signs
    
    def _extract_tax_info(self, source_code: str) -> Dict[str, Any]:
        """
        Extrait les informations sur les taxes depuis le code source.
        
        Args:
            source_code: Code source du contrat
            
        Returns:
            Informations sur les taxes
        """
        results = {
            "buy_tax": 0.0,
            "sell_tax": 0.0,
            "tax_functions": []
        }
        
        # Recherche des variables de taxe
        buy_tax_vars = [
            r"(?:buy|purchase)(?:Fee|Tax)\s*=\s*(\d+)",
            r"_(?:buy|purchase)(?:Fee|Tax)\s*=\s*(\d+)",
            r"(?:buy|purchase)(?:Fee|Tax)\s*:\s*(\d+)"
        ]
        
        sell_tax_vars = [
            r"(?:sell|transfer)(?:Fee|Tax)\s*=\s*(\d+)",
            r"_(?:sell|transfer)(?:Fee|Tax)\s*=\s*(\d+)",
            r"(?:sell|transfer)(?:Fee|Tax)\s*:\s*(\d+)"
        ]
        
        # Extraire les taxes d'achat
        for pattern in buy_tax_vars:
            matches = re.finditer(pattern, source_code)
            for match in matches:
                tax_value = int(match.group(1))
                # Les taxes sont souvent exprimées en points de base (1% = 100 bps)
                if tax_value > 100:
                    tax_value = tax_value / 100
                results["buy_tax"] = max(results["buy_tax"], tax_value)
                results["tax_functions"].append({
                    "type": "buy_tax",
                    "value": tax_value,
                    "match": match.group(0)
                })
                
        # Extraire les taxes de vente
        for pattern in sell_tax_vars:
            matches = re.finditer(pattern, source_code)
            for match in matches:
                tax_value = int(match.group(1))
                # Les taxes sont souvent exprimées en points de base (1% = 100 bps)
                if tax_value > 100:
                    tax_value = tax_value / 100
                results["sell_tax"] = max(results["sell_tax"], tax_value)
                results["tax_functions"].append({
                    "type": "sell_tax",
                    "value": tax_value,
                    "match": match.group(0)
                })
                
        return results 