"""
Module AgentManager - Système d'orchestration d'agents IA pour GBPBot

Ce module implémente un agent IA avancé capable d'orchestrer l'ensemble des modules
du GBPBot pour une prise de décision autonome ou semi-autonome.
"""

import os
import json
import logging
import asyncio
from typing import Dict, List, Any, Optional, Union, Callable
from enum import Enum
from dataclasses import dataclass, field

# Importations LangChain
try:
    from langchain.agents import AgentExecutor, initialize_agent, AgentType
    from langchain.chains.conversation.memory import ConversationBufferMemory
    from langchain.tools import Tool
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    # Classes de remplacement pour le typage
    class AgentExecutor:
        pass
    class Tool:
        pass

# Importations internes
from gbpbot.utils.logger import setup_logger
from gbpbot.config.settings import get_settings
from gbpbot.ai.langchain_adapter import GBPBotTool, create_langchain_llm
# Import conditionnel des modules qui peuvent ne pas exister
try:
    from gbpbot.modules.token_sniper import TokenSniper
    TOKEN_SNIPER_AVAILABLE = True
except ImportError:
    TOKEN_SNIPER_AVAILABLE = False

try:
    from gbpbot.modules.arbitrage_engine import ArbitrageEngine
    ARBITRAGE_ENGINE_AVAILABLE = True
except ImportError:
    ARBITRAGE_ENGINE_AVAILABLE = False

try:
    from gbpbot.modules.market_analyzer import MarketAnalyzer
    MARKET_ANALYZER_AVAILABLE = True
except ImportError:
    MARKET_ANALYZER_AVAILABLE = False

try:
    from gbpbot.security.stealth_manager import StealthManager
    STEALTH_MANAGER_AVAILABLE = True
except ImportError:
    STEALTH_MANAGER_AVAILABLE = False

try:
    from gbpbot.ai.profile_intelligence import ProfileIntelligence
    PROFILE_INTELLIGENCE_AVAILABLE = True
except ImportError:
    PROFILE_INTELLIGENCE_AVAILABLE = False

# Configuration du logger
logger = setup_logger("agent_manager", logging.INFO)

class AgentAutonomyLevel(str, Enum):
    """Niveau d'autonomie de l'agent IA."""
    SEMI_AUTONOME = "semi_autonomous"  # Requiert validation humaine pour actions critiques
    AUTONOME = "autonomous"            # Totalement autonome
    HYBRIDE = "hybrid"                 # Adaptatif selon contexte et risque

@dataclass
class AgentConfig:
    """Configuration de l'agent IA."""
    autonomy_level: AgentAutonomyLevel = AgentAutonomyLevel.HYBRIDE
    max_decision_amount: float = 0.1  # Montant max pour décisions sans validation
    enable_websearch: bool = True
    enable_human_feedback: bool = True
    max_consecutive_actions: int = 5
    ai_temperature: float = 0.2
    ai_max_tokens: int = 4000
    cache_timeout_minutes: int = 10
    approval_timeout_seconds: int = 300
    language: str = "fr"  # 'fr' ou 'en'

class AgentManager:
    """
    Gestionnaire d'agents IA pour GBPBot.
    
    Implémente un système avancé d'agents IA basés sur LangChain pour
    orchestrer les différents modules du GBPBot et prendre des décisions
    intelligentes de manière autonome ou semi-autonome.
    """
    
    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        require_approval_callback: Optional[Callable[[str, Dict[str, Any]], asyncio.Future]] = None
    ):
        """
        Initialise le gestionnaire d'agents IA.
        
        Args:
            config: Configuration de l'agent
            require_approval_callback: Fonction de callback pour validation humaine
        """
        self.config = config or AgentConfig()
        self.require_approval_callback = require_approval_callback
        
        # État interne
        self.initialized = False
        self.tools = []
        self.agent = None
        self.memory = None
        self.llm = None
        
        # Composants du bot
        self.token_sniper = None
        self.arbitrage_engine = None
        self.market_analyzer = None
        self.stealth_manager = None
        self.profile_intelligence = None
        
        # Statistiques et métriques
        self.total_decisions = 0
        self.approved_decisions = 0
        self.rejected_decisions = 0
        self.autonomous_decisions = 0
        self.decision_history = []
        
        # Vérifier si LangChain est disponible
        if not LANGCHAIN_AVAILABLE:
            logger.warning("LangChain n'est pas disponible. L'agent IA ne pourra pas être utilisé.")
        
        # Initialisation asynchrone
        asyncio.create_task(self._async_init())
    
    async def _async_init(self) -> None:
        """Initialisation asynchrone des composants."""
        try:
            if not LANGCHAIN_AVAILABLE:
                logger.error("LangChain n'est pas disponible. L'agent IA ne pourra pas être utilisé.")
                return
            
            # Initialiser le LLM
            self.llm = await create_langchain_llm(
                temperature=self.config.ai_temperature,
                max_tokens=self.config.ai_max_tokens
            )
            
            # Initialiser les composants du bot (uniquement ceux disponibles)
            await self._initialize_components()
            
            # Initialiser la mémoire LangChain
            self.memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
            
            # Définir les outils disponibles pour l'agent
            await self._define_tools()
            
            # Initialiser l'agent LangChain
            await self._initialize_langchain_agent()
            
            self.initialized = True
            logger.info(f"Agent IA initialisé avec niveau d'autonomie: {self.config.autonomy_level}")
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de l'agent IA: {str(e)}")
    
    async def _initialize_components(self) -> None:
        """Initialise les composants du bot."""
        # Initialiser uniquement les composants disponibles
        if TOKEN_SNIPER_AVAILABLE:
            try:
                self.token_sniper = TokenSniper(config={})
                logger.info("Module TokenSniper initialisé")
            except Exception as e:
                logger.error(f"Erreur lors de l'initialisation du TokenSniper: {str(e)}")
        
        if ARBITRAGE_ENGINE_AVAILABLE:
            try:
                self.arbitrage_engine = ArbitrageEngine(config={})
                logger.info("Module ArbitrageEngine initialisé")
            except Exception as e:
                logger.error(f"Erreur lors de l'initialisation de l'ArbitrageEngine: {str(e)}")
        
        if MARKET_ANALYZER_AVAILABLE:
            try:
                self.market_analyzer = MarketAnalyzer()
                logger.info("Module MarketAnalyzer initialisé")
            except Exception as e:
                logger.error(f"Erreur lors de l'initialisation du MarketAnalyzer: {str(e)}")
        
        if STEALTH_MANAGER_AVAILABLE:
            try:
                self.stealth_manager = StealthManager()
                logger.info("Module StealthManager initialisé")
            except Exception as e:
                logger.error(f"Erreur lors de l'initialisation du StealthManager: {str(e)}")
        
        if PROFILE_INTELLIGENCE_AVAILABLE:
            try:
                self.profile_intelligence = ProfileIntelligence()
                logger.info("Module ProfileIntelligence initialisé")
            except Exception as e:
                logger.error(f"Erreur lors de l'initialisation du ProfileIntelligence: {str(e)}")
    
    async def _define_tools(self) -> None:
        """Définit les outils disponibles pour l'agent."""
        self.tools = []
        
        # Ajouter les outils uniquement s'ils sont disponibles
        if self.market_analyzer:
            self.tools.append(
                GBPBotTool(
                    name="MarketAnalyzer",
                    description="Analyse les données du marché crypto et recommande des opportunités.",
                    func=self._analyze_market
                )
            )
        
        if self.token_sniper:
            self.tools.append(
                GBPBotTool(
                    name="TokenSniper",
                    description="Effectue un sniping rapide d'un token spécifique.",
                    func=self._snipe_token
                )
            )
        
        if self.arbitrage_engine:
            self.tools.append(
                GBPBotTool(
                    name="ArbitrageEngine",
                    description="Exécute des opérations d'arbitrage entre DEX.",
                    func=self._execute_arbitrage
                )
            )
        
        if self.profile_intelligence:
            self.tools.append(
                GBPBotTool(
                    name="ProfileManager",
                    description="Sélectionne le profil de trading optimal pour une opération spécifique.",
                    func=self._select_trading_profile
                )
            )
        
        # Outils génériques toujours disponibles
        self.tools.append(
            GBPBotTool(
                name="TransactionExecutor",
                description="Exécute une transaction blockchain avec les paramètres spécifiés.",
                func=self._execute_transaction
            )
        )
        
        # Ajouter la recherche web si activée
        if self.config.enable_websearch:
            self.tools.append(
                GBPBotTool(
                    name="WebSearch",
                    description="Recherche des informations sur le web pour enrichir l'analyse.",
                    func=self._search_web
                )
            )
    
    async def _initialize_langchain_agent(self) -> None:
        """Initialise l'agent LangChain avec les outils définis."""
        if not self.llm:
            logger.error("LLM non initialisé pour l'agent LangChain")
            return
        
        try:
            # Créer l'agent
            self.agent = initialize_agent(
                tools=self.tools,
                llm=self.llm,
                agent=AgentType.CONVERSATIONAL_REACT_DESCRIPTION,
                verbose=True,
                memory=self.memory,
                handle_parsing_errors=True
            )
            
            # Configurer l'agent
            if isinstance(self.agent, AgentExecutor):
                self.agent.max_iterations = self.config.max_consecutive_actions
                
            logger.info(f"Agent LangChain initialisé avec {len(self.tools)} outils")
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de l'agent LangChain: {str(e)}")
    
    async def run_agent(self, query: str) -> Dict[str, Any]:
        """
        Exécute l'agent IA avec une requête spécifique.
        
        Args:
            query: Requête ou instruction pour l'agent
            
        Returns:
            Résultat de l'exécution de l'agent
        """
        if not LANGCHAIN_AVAILABLE:
            return {
                "success": False,
                "error": "LangChain n'est pas disponible. Veuillez installer les dépendances requises.",
                "query": query
            }
        
        if not self.initialized or not self.agent:
            await self._async_init()
            if not self.initialized:
                return {"error": "Agent IA non initialisé", "query": query}
        
        try:
            # Exécuter l'agent de manière asynchrone pour ne pas bloquer
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, lambda: self.agent.run(query))
            
            # Mettre à jour les statistiques
            self.total_decisions += 1
            
            return {
                "success": True,
                "result": result,
                "query": query
            }
        except Exception as e:
            logger.error(f"Erreur lors de l'exécution de l'agent: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "query": query
            }
    
    # Implémentations des fonctions d'outil
    
    async def _analyze_market(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Analyse le marché et retourne des opportunités."""
        try:
            if not self.market_analyzer:
                return {"status": "error", "message": "MarketAnalyzer non disponible"}
            
            # Extraire les paramètres
            blockchain = params.get("blockchain", "solana")
            token_type = params.get("token_type", "memecoin")
            time_frame = params.get("time_frame", "short")
            
            # Simuler une analyse de marché (à remplacer par l'implémentation réelle)
            analysis_results = {
                "opportunities": [
                    {"token": "SOL/USDT", "type": "achat", "confiance": 0.85, "raison": "Support atteint"},
                    {"token": "AVAX/USDT", "type": "vente", "confiance": 0.72, "raison": "Résistance approchée"}
                ],
                "market_sentiment": "bullish",
                "volatility": "medium",
                "top_movers": ["SOL", "AVAX", "PEPE"],
                "blockchain": blockchain
            }
            
            # Log de l'action (pour statistiques)
            logger.info(f"Analyse de marché effectuée pour {blockchain} ({token_type})")
            
            return {
                "status": "success",
                "data": analysis_results
            }
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse de marché: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    async def _snipe_token(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Exécute une opération de sniping de token."""
        try:
            if not self.token_sniper:
                return {"status": "error", "message": "TokenSniper non disponible"}
            
            # Vérifier si l'approbation est nécessaire
            if self._requires_approval(params):
                approved = await self._request_approval("Sniping de token", params)
                if not approved:
                    return {"status": "rejected", "reason": "L'utilisateur a rejeté l'opération"}
            
            # Extraire les paramètres
            token_address = params.get("token_address")
            amount = params.get("amount", 0.1)
            blockchain = params.get("blockchain", "solana")
            slippage = params.get("slippage", 1.0)
            
            if not token_address:
                return {"status": "error", "message": "Adresse du token manquante"}
            
            # Simuler une opération de sniping (à remplacer par l'implémentation réelle)
            snipe_result = {
                "token_address": token_address,
                "blockchain": blockchain,
                "amount_spent": amount,
                "tokens_received": amount * 1000,  # Simulé
                "tx_hash": "0x" + "1" * 64,
                "status": "success"
            }
            
            # Log de l'action (pour statistiques)
            logger.info(f"Sniping effectué pour {token_address} sur {blockchain} (montant: {amount})")
            
            return {
                "status": "success",
                "data": snipe_result
            }
        except Exception as e:
            logger.error(f"Erreur lors du sniping: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    async def _execute_arbitrage(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Exécute une opération d'arbitrage."""
        try:
            if not self.arbitrage_engine:
                return {"status": "error", "message": "ArbitrageEngine non disponible"}
            
            # Vérifier si l'approbation est nécessaire
            if self._requires_approval(params):
                approved = await self._request_approval("Arbitrage", params)
                if not approved:
                    return {"status": "rejected", "reason": "L'utilisateur a rejeté l'opération"}
            
            # Extraire les paramètres
            token_pair = params.get("token_pair", "SOL/USDT")
            amount = params.get("amount", 0.1)
            source_dex = params.get("source_dex", "raydium")
            target_dex = params.get("target_dex", "orca")
            
            # Simuler une opération d'arbitrage (à remplacer par l'implémentation réelle)
            arbitrage_result = {
                "token_pair": token_pair,
                "amount": amount,
                "source_dex": source_dex,
                "target_dex": target_dex,
                "profit": amount * 0.02,  # 2% de profit simulé
                "profit_percentage": 2.0,
                "tx_hash": "0x" + "2" * 64,
                "status": "success"
            }
            
            # Log de l'action (pour statistiques)
            logger.info(f"Arbitrage effectué pour {token_pair} de {source_dex} à {target_dex} (montant: {amount})")
            
            return {
                "status": "success",
                "data": arbitrage_result
            }
        except Exception as e:
            logger.error(f"Erreur lors de l'arbitrage: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    async def _select_trading_profile(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Sélectionne le profil de trading optimal."""
        try:
            if not self.profile_intelligence:
                return {"status": "error", "message": "ProfileIntelligence non disponible"}
            
            # Extraire les paramètres
            blockchain = params.get("blockchain", "solana")
            operation_type = params.get("operation_type", "standard")
            token_symbol = params.get("token_symbol", "SOL")
            
            # Sélectionner le profil (utiliser l'implémentation réelle)
            profile = await self.profile_intelligence.select_optimal_profile(
                blockchain=blockchain,
                operation_type=operation_type,
                token_symbol=token_symbol,
                force_ai_selection=params.get("force_ai_selection", False)
            )
            
            # Log de l'action (pour statistiques)
            logger.info(f"Profil {profile} sélectionné pour {operation_type} sur {blockchain}")
            
            return {
                "status": "success",
                "data": {
                    "selected_profile": profile,
                    "blockchain": blockchain,
                    "operation_type": operation_type
                }
            }
        except Exception as e:
            logger.error(f"Erreur lors de la sélection du profil: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    async def _execute_transaction(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Exécute une transaction blockchain."""
        try:
            # Vérifier si l'approbation est nécessaire
            if self._requires_approval(params):
                approved = await self._request_approval("Transaction", params)
                if not approved:
                    return {"status": "rejected", "reason": "L'utilisateur a rejeté l'opération"}
            
            # Extraire les paramètres
            blockchain = params.get("blockchain", "solana")
            tx_type = params.get("tx_type", "swap")
            amount = params.get("amount", 0.1)
            
            # Simuler une transaction (à remplacer par l'implémentation réelle)
            tx_result = {
                "blockchain": blockchain,
                "tx_type": tx_type,
                "amount": amount,
                "tx_hash": "0x" + "3" * 64,
                "status": "success",
                "timestamp": datetime.now().isoformat()
            }
            
            # Log de l'action (pour statistiques)
            logger.info(f"Transaction {tx_type} exécutée sur {blockchain} (montant: {amount})")
            
            return {
                "status": "success",
                "data": tx_result
            }
        except Exception as e:
            logger.error(f"Erreur lors de l'exécution de la transaction: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    async def _search_web(self, query: str) -> Dict[str, Any]:
        """Recherche des informations sur le web."""
        try:
            # Vérifier si la recherche web est activée
            if not self.config.enable_websearch:
                return {"status": "error", "message": "Recherche web désactivée"}
            
            # Simuler une recherche web (à remplacer par l'implémentation réelle)
            search_results = [
                {
                    "title": "Example Search Result 1",
                    "url": "https://example.com/1",
                    "snippet": "This is a sample search result for " + query
                },
                {
                    "title": "Example Search Result 2",
                    "url": "https://example.com/2",
                    "snippet": "Another sample search result related to " + query
                }
            ]
            
            # Log de l'action (pour statistiques)
            logger.info(f"Recherche web effectuée pour: {query}")
            
            return {
                "status": "success",
                "data": search_results,
                "query": query
            }
        except Exception as e:
            logger.error(f"Erreur lors de la recherche web: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def _requires_approval(self, params: Dict[str, Any]) -> bool:
        """
        Détermine si une opération nécessite une approbation humaine.
        
        Args:
            params: Paramètres de l'opération
            
        Returns:
            True si l'approbation est nécessaire, False sinon
        """
        # Semi-autonome - toujours demander approbation
        if self.config.autonomy_level == AgentAutonomyLevel.SEMI_AUTONOME:
            return True
        
        # Autonome - jamais demander approbation
        if self.config.autonomy_level == AgentAutonomyLevel.AUTONOME:
            return False
        
        # Hybride - décider en fonction des paramètres
        # Par exemple, vérifier si le montant dépasse le seuil
        amount = float(params.get("amount", 0.0))
        if amount > self.config.max_decision_amount:
            return True
        
        # Vérifier si l'opération est à haut risque
        risk_level = params.get("risk_level", "low").lower()
        if risk_level in ["high", "très élevé", "extreme"]:
            return True
        
        return False
    
    async def _request_approval(self, operation: str, params: Dict[str, Any]) -> bool:
        """
        Demande l'approbation utilisateur pour une opération.
        
        Args:
            operation: Description de l'opération
            params: Paramètres de l'opération
            
        Returns:
            True si approuvé, False sinon
        """
        if not self.require_approval_callback:
            logger.warning("Callback d'approbation non configuré, refus automatique")
            return False
        
        try:
            # Créer un future pour attendre la réponse
            future = self.require_approval_callback(operation, params)
            
            # Attendre la réponse avec timeout
            approved = await asyncio.wait_for(future, timeout=self.config.approval_timeout_seconds)
            
            # Mettre à jour les statistiques
            if approved:
                self.approved_decisions += 1
            else:
                self.rejected_decisions += 1
            
            return approved
        except asyncio.TimeoutError:
            logger.warning(f"Timeout de l'approbation pour {operation}, refus automatique")
            self.rejected_decisions += 1
            return False
        except Exception as e:
            logger.error(f"Erreur lors de la demande d'approbation: {str(e)}")
            self.rejected_decisions += 1
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Retourne les statistiques de l'agent.
        
        Returns:
            Dictionnaire de statistiques
        """
        return {
            "total_decisions": self.total_decisions,
            "approved_decisions": self.approved_decisions,
            "rejected_decisions": self.rejected_decisions,
            "autonomous_decisions": self.autonomous_decisions,
            "approval_rate": self.approved_decisions / max(1, self.total_decisions),
            "autonomy_level": self.config.autonomy_level,
            "initialized": self.initialized,
            "available_tools": [tool.name for tool in self.tools] if self.tools else []
        }

def create_agent_manager(
    autonomy_level: str = "hybrid",
    max_decision_amount: float = 0.1,
    require_approval_callback: Optional[Callable] = None
) -> AgentManager:
    """
    Crée et retourne une instance d'AgentManager.
    
    Args:
        autonomy_level: Niveau d'autonomie ("semi_autonomous", "autonomous", "hybrid")
        max_decision_amount: Montant maximum pour décisions autonomes
        require_approval_callback: Fonction de callback pour validation humaine
        
    Returns:
        Instance d'AgentManager
    """
    # Convertir la chaîne en enum
    autonomy_enum = AgentAutonomyLevel.HYBRIDE
    if autonomy_level == "semi_autonomous":
        autonomy_enum = AgentAutonomyLevel.SEMI_AUTONOME
    elif autonomy_level == "autonomous":
        autonomy_enum = AgentAutonomyLevel.AUTONOME
    
    # Créer la configuration
    config = AgentConfig(
        autonomy_level=autonomy_enum,
        max_decision_amount=max_decision_amount
    )
    
    # Créer l'agent manager
    return AgentManager(
        config=config,
        require_approval_callback=require_approval_callback
    )
