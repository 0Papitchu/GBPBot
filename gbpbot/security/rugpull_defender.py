from typing import Dict, List, Optional, Tuple
import asyncio
from loguru import logger
from web3 import Web3
import json
from pathlib import Path
import aiohttp
import re
from dataclasses import dataclass, field
import numpy as np

@dataclass
class SecurityCheck:
    """Résultat d'une vérification de sécurité"""
    is_safe: bool
    risk_level: str
    warnings: List[str]
    token_info: Dict = field(default_factory=dict)
    contract_analysis: Dict = field(default_factory=dict)
    liquidity_analysis: Dict = field(default_factory=dict)

class SmartContractAnalyzer:
    def __init__(self):
        self.dangerous_patterns = {
            'mint': r'function\s+mint',
            'burn': r'function\s+burn',
            'blacklist': r'mapping.*blacklist',
            'whitelist': r'mapping.*whitelist',
            'owner_only': r'onlyOwner',
            'max_tx': r'maxTransaction',
            'fee_change': r'changeFee|updateFee',
            'pause': r'pause|unpause'
        }
        
    async def deep_analyze(self, token_address: str) -> Dict:
        """Analyse approfondie d'un contrat intelligent"""
        try:
            # Récupération du code source
            contract_code = await self._get_contract_source(token_address)
            if not contract_code:
                return {
                    'is_safe': False,
                    'reason': 'unverified_contract'
                }
                
            # Analyse des patterns dangereux
            dangerous_functions = self._analyze_dangerous_patterns(contract_code)
            
            # Analyse des permissions
            permissions = await self._analyze_permissions(contract_code)
            
            # Vérification du code malicieux
            malicious_code = self._detect_malicious_code(contract_code)
            
            # Score de sécurité
            security_score = self._calculate_security_score(
                dangerous_functions,
                permissions,
                malicious_code
            )
            
            return {
                'is_safe': security_score > 0.7,
                'security_score': security_score,
                'dangerous_functions': dangerous_functions,
                'permissions': permissions,
                'malicious_code': malicious_code,
                'recommendations': self._generate_recommendations(
                    dangerous_functions,
                    permissions,
                    malicious_code
                )
            }
            
        except Exception as e:
            logger.error(f"Error analyzing contract: {str(e)}")
            return {'is_safe': False, 'reason': str(e)}

    async def _get_contract_source(self, token_address: str) -> Optional[str]:
        """Récupère le code source du contrat"""
        try:
            # TODO: Implémenter la récupération du code source
            return "contract code..."
        except Exception as e:
            logger.error(f"Error getting contract source: {str(e)}")
            return None

    def _analyze_dangerous_patterns(self, contract_code: str) -> Dict:
        """Analyse les patterns dangereux dans le code"""
        findings = {}
        
        for pattern_name, pattern in self.dangerous_patterns.items():
            matches = re.finditer(pattern, contract_code, re.IGNORECASE)
            if matches:
                findings[pattern_name] = [m.group() for m in matches]
                
        return findings

    async def _analyze_permissions(self, contract_code: str) -> Dict:
        """Analyse les permissions du contrat"""
        permissions = {
            'owner_functions': [],
            'restricted_functions': [],
            'public_functions': []
        }
        
        # Analyse des fonctions
        function_pattern = r'function\s+(\w+)'
        matches = re.finditer(function_pattern, contract_code)
        
        for match in matches:
            function_name = match.group(1)
            if 'onlyOwner' in contract_code[match.start():match.end() + 100]:
                permissions['owner_functions'].append(function_name)
            elif any(modifier in contract_code[match.start():match.end() + 100]
                    for modifier in ['private', 'internal']):
                permissions['restricted_functions'].append(function_name)
            else:
                permissions['public_functions'].append(function_name)
                
        return permissions

    def _detect_malicious_code(self, contract_code: str) -> List[Dict]:
        """Détecte le code potentiellement malicieux"""
        malicious_patterns = [
            {
                'pattern': r'selfdestruct|suicide',
                'severity': 'high',
                'description': 'Contract self-destruction capability'
            },
            {
                'pattern': r'delegatecall',
                'severity': 'high',
                'description': 'Delegatecall usage (potential proxy manipulation)'
            },
            {
                'pattern': r'assembly',
                'severity': 'medium',
                'description': 'Assembly code usage'
            }
        ]
        
        findings = []
        for pattern in malicious_patterns:
            matches = re.finditer(pattern['pattern'], contract_code, re.IGNORECASE)
            if matches:
                findings.append({
                    'type': pattern['pattern'],
                    'severity': pattern['severity'],
                    'description': pattern['description'],
                    'locations': [m.group() for m in matches]
                })
                
        return findings

    def _calculate_security_score(self, dangerous_functions: Dict,
                                permissions: Dict, malicious_code: List) -> float:
        """Calcule le score de sécurité du contrat"""
        base_score = 1.0
        
        # Pénalités pour les fonctions dangereuses
        for functions in dangerous_functions.values():
            base_score -= len(functions) * 0.1
            
        # Pénalités pour les permissions
        if len(permissions['owner_functions']) > 5:
            base_score -= 0.2
            
        # Pénalités pour le code malicieux
        for finding in malicious_code:
            if finding['severity'] == 'high':
                base_score -= 0.3
            elif finding['severity'] == 'medium':
                base_score -= 0.15
                
        return max(0, min(1, base_score))

class LiquidityMonitor:
    def __init__(self, web3_provider: str):
        self.web3 = Web3(Web3.HTTPProvider(web3_provider))
        self.min_liquidity = 10  # 10 AVAX minimum
        
    async def analyze_liquidity_security(self, token_address: str) -> Dict:
        """Analyse la sécurité de la liquidité"""
        try:
            # Vérification de la liquidité
            liquidity = await self._check_liquidity(token_address)
            
            # Vérification du verrouillage
            lock_info = await self._check_liquidity_lock(token_address)
            
            # Analyse des mouvements de liquidité
            liquidity_movements = await self._analyze_liquidity_movements(token_address)
            
            # Score de sécurité
            security_score = self._calculate_liquidity_score(
                liquidity,
                lock_info,
                liquidity_movements
            )
            
            return {
                'is_safe': security_score > 0.7,
                'security_score': security_score,
                'liquidity': liquidity,
                'lock_info': lock_info,
                'movements': liquidity_movements,
                'recommendations': self._generate_recommendations(
                    liquidity,
                    lock_info,
                    liquidity_movements
                )
            }
            
        except Exception as e:
            logger.error(f"Error analyzing liquidity: {str(e)}")
            return {'is_safe': False, 'reason': str(e)}

    async def _check_liquidity(self, token_address: str) -> Dict:
        """Vérifie la liquidité du token"""
        try:
            # TODO: Implémenter la vérification de liquidité
            return {
                'total_liquidity': 0,
                'liquidity_pairs': []
            }
        except Exception as e:
            logger.error(f"Error checking liquidity: {str(e)}")
            return {'total_liquidity': 0}

    async def _check_liquidity_lock(self, token_address: str) -> Dict:
        """Vérifie le verrouillage de la liquidité"""
        try:
            # TODO: Implémenter la vérification du lock
            return {
                'is_locked': False,
                'lock_duration': 0,
                'lock_contract': None
            }
        except Exception as e:
            logger.error(f"Error checking liquidity lock: {str(e)}")
            return {'is_locked': False}

    async def _analyze_liquidity_movements(self, token_address: str) -> List[Dict]:
        """Analyse les mouvements de liquidité"""
        try:
            # TODO: Implémenter l'analyse des mouvements
            return []
        except Exception as e:
            logger.error(f"Error analyzing liquidity movements: {str(e)}")
            return []

    def _calculate_liquidity_score(self, liquidity: Dict, lock_info: Dict,
                                 movements: List) -> float:
        """Calcule le score de sécurité de la liquidité"""
        base_score = 1.0
        
        # Vérification du montant minimum
        if liquidity['total_liquidity'] < self.min_liquidity:
            base_score -= 0.5
            
        # Bonus pour le verrouillage
        if lock_info['is_locked']:
            if lock_info['lock_duration'] > 180:  # 6 mois
                base_score += 0.2
            elif lock_info['lock_duration'] > 90:  # 3 mois
                base_score += 0.1
                
        # Pénalités pour les mouvements suspects
        for movement in movements:
            if movement.get('is_suspicious'):
                base_score -= 0.1
                
        return max(0, min(1, base_score))

class TokenValidator:
    def __init__(self, web3_provider: str):
        self.web3 = Web3(Web3.HTTPProvider(web3_provider))
        
    async def simulate_sell(self, token_address: str, amount_percentage: str,
                          slippage: float) -> Dict:
        """Simule une vente de token"""
        try:
            # TODO: Implémenter la simulation de vente
            return {
                'success': True,
                'expected_output': 0,
                'price_impact': 0,
                'gas_estimate': 0
            }
        except Exception as e:
            logger.error(f"Error simulating sell: {str(e)}")
            return {'success': False, 'reason': str(e)}

class RugPullDefender:
    def __init__(self, web3_provider: str):
        """
        Initialise le défenseur contre les rug pulls
        
        Args:
            web3_provider: URL du provider Web3
        """
        self.web3 = Web3(Web3.HTTPProvider(web3_provider))
        
        # Configuration de sécurité améliorée
        self.config = {
            "min_liquidity": Web3.to_wei(5000, "ether"),  # Liquidité minimale
            "min_time_locked": 7 * 24 * 3600,  # 7 jours minimum de lock
            "max_owner_percentage": 10.0,  # Max 10% pour le owner
            "min_holders": 100,  # Minimum de holders
            "max_mint_percentage": 5.0,  # Max 5% de mint par transaction
            "max_burn_percentage": 5.0,  # Max 5% de burn par transaction
            "blacklist_threshold": 0.8,  # Seuil pour blacklist
            "max_tax_percentage": 10.0,  # Max 10% de taxe
            "min_code_similarity": 0.7,  # Similarité minimale avec contrats vérifiés
            "max_risk_score": 7.0  # Score de risque maximum (sur 10)
        }
        
        # Chargement des données de sécurité
        self.verified_contracts = self._load_verified_contracts()
        self.known_exploits = self._load_known_exploits()
        self.blacklisted_patterns = self._load_blacklist_patterns()
        
    async def analyze_security(self, token_address: str) -> SecurityCheck:
        """Analyse la sécurité d'un token"""
        try:
            # Vérifier le format de l'adresse
            if not self._is_valid_address(token_address):
                return SecurityCheck(
                    is_safe=False,
                    risk_level="HIGH",
                    warnings=["Invalid token address format"]
                )

            # Analyser le contrat
            contract_security = await self._analyze_contract_security(token_address)
            
            # Analyser les informations du token
            token_info = await self._analyze_token_info(token_address)
            
            # Analyser la liquidité
            liquidity_security = await self._analyze_liquidity_security(token_address)
            
            # Agréger les résultats
            warnings = []
            risk_level = "LOW"
            
            # Vérifier les résultats du contrat
            if contract_security.get("has_proxy", False):
                warnings.append("Contract uses a proxy pattern")
            if contract_security.get("has_mint_function", False):
                warnings.append("Contract can mint new tokens")
                risk_level = "MEDIUM"
            if contract_security.get("has_blacklist", False):
                warnings.append("Contract has blacklist functionality")
                risk_level = "MEDIUM"
                
            # Vérifier la distribution des tokens
            if token_info["owner_percentage"] > 50:
                warnings.append(f"Owner holds {token_info['owner_percentage']:.1f}% of supply")
                risk_level = "HIGH"
            if token_info["distribution"].get("top_10_percentage", 0) > 80:
                warnings.append("Top 10 holders control >80% of supply")
                risk_level = "MEDIUM"
                
            # Vérifier la liquidité
            if liquidity_security["total_liquidity_usd"] < 10000:
                warnings.append("Low liquidity (<$10k)")
                risk_level = "HIGH"
            if liquidity_security["locked_liquidity_percentage"] < 50:
                warnings.append("Less than 50% of liquidity is locked")
                risk_level = "MEDIUM"
                
            return SecurityCheck(
                is_safe=risk_level != "HIGH",
                risk_level=risk_level,
                warnings=warnings
            )
            
        except Exception as e:
            logger.error(f"Error in security analysis: {str(e)}")
            return SecurityCheck(
                is_safe=False,
                risk_level="HIGH",
                warnings=["Error during security analysis"]
            )
            
    async def _analyze_contract_security(self, token_address: str) -> Dict:
        """Analyse la sécurité du contrat"""
        try:
            # Récupérer le code du contrat
            contract_code = await self.web3.eth.get_code(token_address)
            if len(contract_code) == 0:
                return {
                    "has_proxy": False,
                    "has_mint_function": False,
                    "has_blacklist": False,
                    "vulnerabilities": ["Contract has no code"]
                }
                
            # Analyser les fonctions du contrat
            contract_analysis = {
                "has_proxy": False,
                "has_mint_function": False,
                "has_blacklist": False,
                "vulnerabilities": []
            }
            
            # Pour le testnet, on simule l'analyse
            # En production, il faudrait faire une analyse statique du bytecode
            contract_analysis.update({
                "has_proxy": False,
                "has_mint_function": True,
                "has_blacklist": False,
                "vulnerabilities": []
            })
            
            return contract_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing contract security: {str(e)}")
            return {
                "has_proxy": False,
                "has_mint_function": False,
                "has_blacklist": False,
                "vulnerabilities": ["Error analyzing contract"]
            }

    def _calculate_risk_score(self, token_info: Dict, contract_analysis: Dict,
                              liquidity_analysis: Dict) -> float:
        """Calcule le score de risque final"""
        # Poids des différents facteurs
        weights = {
            'token_info': 0.2,
            'contract_analysis': 0.4,
            'liquidity_analysis': 0.4
        }
        
        # Score du token info
        token_score = self._calculate_token_score(token_info)
        
        # Score du contrat
        contract_score = self._calculate_contract_score(contract_analysis)
        
        # Score de la liquidité
        liquidity_score = self._calculate_liquidity_score(liquidity_analysis)
        
        # Score final pondéré
        final_score = (
            weights['token_info'] * token_score +
            weights['contract_analysis'] * contract_score +
            weights['liquidity_analysis'] * liquidity_score
        )
        
        return max(0, min(10, final_score))

    def _calculate_token_score(self, token_info: Dict) -> float:
        """Calcule le score basé sur les informations du token"""
        # Implémentation du calcul du score basé sur les informations du token
        return 0.0  # Placeholder, actual implementation needed

    def _calculate_contract_score(self, contract_analysis: Dict) -> float:
        """Calcule le score basé sur l'analyse du contrat"""
        # Implémentation du calcul du score basé sur l'analyse du contrat
        return 0.0  # Placeholder, actual implementation needed

    def _calculate_liquidity_score(self, liquidity_analysis: Dict) -> float:
        """Calcule le score basé sur l'analyse de la liquidité"""
        # Implémentation du calcul du score basé sur l'analyse de la liquidité
        return 0.0  # Placeholder, actual implementation needed

    def _load_verified_contracts(self) -> List[Dict]:
        """Charge les données des contrats vérifiés"""
        # Implémentation de la charge des données des contrats vérifiés
        return []  # Placeholder, actual implementation needed

    def _load_known_exploits(self) -> List[Dict]:
        """Charge les données des exploits connus"""
        # Implémentation de la charge des données des exploits connus
        return []  # Placeholder, actual implementation needed

    def _load_blacklist_patterns(self) -> List[Dict]:
        """Charge les données des patterns malveillants"""
        # Implémentation de la charge des données des patterns malveillants
        return []  # Placeholder, actual implementation needed

    def _check_code_similarity(self, bytecode: bytes) -> float:
        """Vérifie la similarité du code avec des contrats vérifiés"""
        # Implémentation de la vérification de la similarité du code
        return 0.0  # Placeholder, actual implementation needed

    def _check_proxy_pattern(self, bytecode: bytes) -> bool:
        """Vérifie la présence d'un pattern de proxy"""
        # Implémentation de la vérification de la présence d'un pattern de proxy
        return False  # Placeholder, actual implementation needed

    def _is_contract_verified(self, token_address: str) -> bool:
        """Vérifie si le contrat est vérifié"""
        # Implémentation de la vérification si le contrat est vérifié
        return False  # Placeholder, actual implementation needed

    def _analyze_risk_patterns(self, bytecode: bytes) -> List[str]:
        """Analyse les patterns risqués dans le bytecode"""
        # Implémentation de l'analyse des patterns risqués dans le bytecode
        return []  # Placeholder, actual implementation needed

    def _generate_recommendations(self, contract_analysis: Dict,
                                liquidity_analysis: Dict,
                                sell_simulations: List[Dict]) -> List[str]:
        """Génère des recommandations basées sur l'analyse"""
        recommendations = []
        
        # Recommandations basées sur le contrat
        if contract_analysis['dangerous_functions']:
            recommendations.append(
                "⚠️ Contract contains potentially dangerous functions"
            )
            
        # Recommandations basées sur la liquidité
        if not liquidity_analysis['lock_info']['is_locked']:
            recommendations.append(
                "⚠️ Liquidity is not locked"
            )
            
        # Recommandations basées sur les simulations
        failed_sells = [
            sim for sim in sell_simulations
            if not sim['result']['success']
        ]
        if failed_sells:
            recommendations.append(
                "⚠️ Some sell simulations failed"
            )
            
        return recommendations

    async def _analyze_token_info(self, token_address: str) -> Dict:
        """Analyse les informations de base du token"""
        try:
            # Récupérer les informations du token
            token_contract = self.web3.eth.contract(
                address=token_address,
                abi=self._get_token_abi()
            )
            
            # Informations de base
            token_info = {
                "name": await token_contract.functions.name().call(),
                "symbol": await token_contract.functions.symbol().call(),
                "decimals": await token_contract.functions.decimals().call(),
                "total_supply": await token_contract.functions.totalSupply().call()
            }
            
            # Analyse de la distribution
            holders = await self._get_token_holders(token_address)
            owner = await self._get_token_owner(token_contract)
            
            # Calcul des pourcentages
            if token_info["total_supply"] > 0:
                owner_balance = await token_contract.functions.balanceOf(owner).call()
                owner_percentage = (owner_balance / token_info["total_supply"]) * 100
            else:
                owner_percentage = 0
                
            token_info.update({
                "holders_count": len(holders),
                "owner": owner,
                "owner_percentage": owner_percentage,
                "distribution": await self._analyze_token_distribution(token_address, holders)
            })
            
            return token_info
            
        except Exception as e:
            logger.error(f"Error analyzing token info: {str(e)}")
            return {
                "name": "Unknown",
                "symbol": "???",
                "decimals": 18,
                "total_supply": 0,
                "holders_count": 0,
                "owner": "0x0000000000000000000000000000000000000000",
                "owner_percentage": 0,
                "distribution": {}
            }
            
    def _get_token_abi(self) -> List:
        """Retourne l'ABI standard ERC20"""
        return [
            {
                "constant": True,
                "inputs": [],
                "name": "name",
                "outputs": [{"name": "", "type": "string"}],
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [],
                "name": "symbol",
                "outputs": [{"name": "", "type": "string"}],
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [],
                "name": "decimals",
                "outputs": [{"name": "", "type": "uint8"}],
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [],
                "name": "totalSupply",
                "outputs": [{"name": "", "type": "uint256"}],
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [{"name": "_owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "balance", "type": "uint256"}],
                "type": "function"
            }
        ]
        
    async def _get_token_holders(self, token_address: str) -> List[Dict]:
        """Récupère la liste des holders du token"""
        try:
            # Cette fonction devrait faire appel à une API comme Covalent ou Etherscan
            # Pour le testnet, on retourne des données simulées
            return [
                {"address": "0x1111...", "balance": 1000000},
                {"address": "0x2222...", "balance": 500000},
                {"address": "0x3333...", "balance": 250000}
            ]
        except Exception as e:
            logger.error(f"Error getting token holders: {str(e)}")
            return []
            
    async def _get_token_owner(self, token_contract) -> str:
        """Récupère l'adresse du propriétaire du token"""
        try:
            # Essayer différentes méthodes pour trouver le owner
            methods = ["owner", "getOwner", "admin"]
            
            for method in methods:
                try:
                    if hasattr(token_contract.functions, method):
                        return await getattr(token_contract.functions, method)().call()
                except:
                    continue
                    
            return "0x0000000000000000000000000000000000000000"
            
        except Exception as e:
            logger.error(f"Error getting token owner: {str(e)}")
            return "0x0000000000000000000000000000000000000000"
            
    async def _analyze_token_distribution(self, token_address: str, holders: List[Dict]) -> Dict:
        """Analyse la distribution du token"""
        try:
            total_supply = sum(h["balance"] for h in holders)
            if total_supply == 0:
                return {}
                
            # Calculer les métriques de distribution
            distribution = {
                "top_10_percentage": sum(
                    h["balance"] for h in sorted(
                        holders,
                        key=lambda x: x["balance"],
                        reverse=True
                    )[:10]
                ) / total_supply * 100,
                "holder_count": len(holders),
                "gini_coefficient": self._calculate_gini_coefficient(holders)
            }
            
            return distribution
            
        except Exception as e:
            logger.error(f"Error analyzing token distribution: {str(e)}")
            return {}
            
    def _calculate_gini_coefficient(self, holders: List[Dict]) -> float:
        """Calcule le coefficient de Gini pour mesurer l'inégalité de distribution"""
        try:
            if not holders:
                return 0
                
            balances = sorted(h["balance"] for h in holders)
            n = len(balances)
            if n == 0 or sum(balances) == 0:
                return 0
                
            index = np.arange(1, n + 1)
            return (np.sum((2 * index - n - 1) * balances)) / (n * sum(balances))
            
        except Exception as e:
            logger.error(f"Error calculating Gini coefficient: {str(e)}")
            return 0

    async def _analyze_liquidity_security(self, token_address: str) -> Dict:
        """Analyse la sécurité de la liquidité d'un token"""
        try:
            # Récupérer les informations de liquidité
            liquidity_info = {
                "total_liquidity_usd": 0,
                "locked_liquidity_percentage": 0,
                "lock_duration_days": 0,
                "pair_addresses": []
            }
            
            # Pour le testnet, on simule des données
            # En production, il faudrait interroger les DEX et les services de lock
            liquidity_info.update({
                "total_liquidity_usd": 50000,  # $50k de liquidité
                "locked_liquidity_percentage": 75,  # 75% de la liquidité est lockée
                "lock_duration_days": 180,  # Lock de 6 mois
                "pair_addresses": ["0x4444..."]  # Adresse de la paire sur le DEX
            })
            
            return liquidity_info
            
        except Exception as e:
            logger.error(f"Error analyzing liquidity security: {str(e)}")
            return {
                "total_liquidity_usd": 0,
                "locked_liquidity_percentage": 0,
                "lock_duration_days": 0,
                "pair_addresses": []
            }
            
    def _is_valid_address(self, address: str) -> bool:
        """Vérifie si une adresse est au format valide"""
        try:
            # Vérifier le format de l'adresse
            if not re.match(r"^0x[a-fA-F0-9]{40}$", address):
                return False
                
            # Vérifier que ce n'est pas l'adresse nulle
            if address == "0x0000000000000000000000000000000000000000":
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Error validating address: {str(e)}")
            return False 