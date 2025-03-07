"""
Module de Sniping de Memecoins sur Solana pour GBPBot
====================================================

Ce module fournit des fonctionnalités spécialisées pour le sniping ultra-rapide
de nouveaux memecoins sur la blockchain Solana, avec une emphase sur la vitesse
d'exécution, la détection automatique et la sécurité contre les scams.
"""

import os
import json
import time
import asyncio
import logging
import random
from typing import Dict, List, Any, Optional, Tuple, Set, Union
from datetime import datetime, timedelta
import base58
import requests
import numpy as np

# Configurer le logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("solana_memecoin_sniper")

# Import de l'analyseur de marché basé sur l'IA
try:
    from gbpbot.ai import create_ai_client, get_prompt_manager
    from gbpbot.ai.market_analyzer import MarketAnalyzer
    from gbpbot.ai.token_contract_analyzer import create_token_contract_analyzer, SolanaTokenContractAnalyzer
    AI_IMPORTS_OK = True
    logger.info("Modules d'IA chargés avec succès")
except ImportError as e:
    logger.warning(f"Impossible d'importer les modules d'IA: {str(e)}")
    logger.warning("Les fonctionnalités d'analyse IA ne seront pas disponibles")
    AI_IMPORTS_OK = False

# Essayer d'importer les dépendances Solana
try:
    from solana.rpc.async_api import AsyncClient
    from solana.rpc.commitment import Commitment
    from solana.rpc.types import TokenAccountOpts
    from solana.publickey import PublicKey
    from solana.transaction import Transaction, TransactionInstruction, AccountMeta
    from solana.system_program import SYS_PROGRAM_ID
    from solders.instruction import Instruction
    from solders.signature import Signature
    from spl.token.instructions import create_associated_token_account, get_associated_token_address
    SOLANA_IMPORTS_OK = True
except ImportError as e:
    logger.warning(f"Impossible d'importer les modules Solana: {str(e)}")
    logger.warning("Installation via pip install solana-py solders anchorpy")
    SOLANA_IMPORTS_OK = False

# Essayer d'importer l'optimiseur MEV Jito
try:
    from gbpbot.core.optimization.jito_mev_optimizer import (
        create_jito_optimizer, 
        JitoMEVOptimizer, 
        JitoConfig
    )
    JITO_OPTIMIZER_AVAILABLE = True
    logger.info("Module d'optimisation MEV Jito chargé avec succès")
except ImportError:
    JITO_OPTIMIZER_AVAILABLE = False
    logger.warning("Module d'optimisation MEV Jito non disponible - les transactions ne seront pas optimisées pour MEV")

# Essayer d'importer l'analyseur de contrats léger
try:
    from gbpbot.machine_learning.contract_analyzer import (
        create_contract_analyzer,
        LightweightContractAnalyzer,
        ContractSecurityResult
    )
    LIGHTWEIGHT_ANALYZER_AVAILABLE = True
    logger.info("Analyseur de contrats léger chargé avec succès")
except ImportError:
    LIGHTWEIGHT_ANALYZER_AVAILABLE = False
    logger.warning("Analyseur de contrats léger non disponible - l'analyse rapide ne sera pas disponible")

# Ajout de l'importation du module d'analyse de microstructure
try:
    from gbpbot.machine_learning.market_microstructure_analyzer import MarketMicrostructureAnalyzer
    MARKET_MICROSTRUCTURE_ANALYZER_AVAILABLE = True
    logger.info("Analyseur de microstructure de marché chargé avec succès")
except ImportError:
    MARKET_MICROSTRUCTURE_ANALYZER_AVAILABLE = False
    logger.warning("Analyseur de microstructure de marché non disponible")

# Essayer d'importer le prédicteur de volatilité
try:
    from gbpbot.machine_learning.volatility_predictor import create_volatility_predictor, VolatilityPredictor
    VOLATILITY_PREDICTOR_AVAILABLE = True
    logger.info("Prédicteur de volatilité chargé avec succès")
except ImportError:
    VOLATILITY_PREDICTOR_AVAILABLE = False
    logger.warning("Prédicteur de volatilité non disponible - les prédictions de volatilité ne seront pas disponibles")

class SolanaMemecoinSniper:
    """
    Sniping ultra-rapide de memecoins sur Solana avec détection automatique
    et sécurité intégrée.
    """
    
    def __init__(
        self,
        wallet_keypair_path: Optional[str] = None,
        rpc_url: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        auto_approve: bool = False,
        simulation_mode: bool = False,
        notification_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None
    ):
        """
        Initialize the Solana memecoin sniper.
        
        Args:
            wallet_keypair_path: Path to the wallet keypair file
            rpc_url: Solana RPC URL
            config: Sniper configuration parameters
            auto_approve: Whether to automatically approve transactions (use with caution)
            simulation_mode: Run in simulation mode without executing real transactions
            notification_callback: Optional callback function for notifications
        """
        self.config = config or {}
        
        # Initialiser l'analyseur de microstructure de marché
        if MARKET_MICROSTRUCTURE_ANALYZER_AVAILABLE:
            self.market_microstructure_analyzer = MarketMicrostructureAnalyzer(rpc_url)
            logger.info("Analyseur de microstructure de marché initialisé avec succès")
        else:
            self.market_microstructure_analyzer = None
            logger.warning("Analyseur de microstructure de marché non disponible")
        
        # Initialiser le prédicteur de volatilité
        if VOLATILITY_PREDICTOR_AVAILABLE:
            volatility_config = self.config.get("volatility", {})
            use_gpu = volatility_config.get("use_gpu", True)
            
            self.volatility_predictor = create_volatility_predictor(
                config=volatility_config,
                models_dir=volatility_config.get("models_dir", "data/volatility_models"),
                data_dir=volatility_config.get("data_dir", "data/volatility_data"),
                use_gpu=use_gpu
            )
            logger.info("Prédicteur de volatilité initialisé avec succès")
        else:
            self.volatility_predictor = None
            logger.warning("Prédicteur de volatilité non disponible")
        
        # Enhanced with AI if available
        if AI_IMPORTS_OK:
            try:
                # Initialize AI client
                ai_config = self.config.get("AI", {})
                self.ai_client = create_ai_client(
                    provider=ai_config.get("PROVIDER", "openai"),
                    model_name=ai_config.get("MODEL", "gpt-3.5-turbo"),
                    temperature=float(ai_config.get("TEMPERATURE", 0.3)),
                    openai_api_key=ai_config.get("OPENAI_API_KEY", None),
                    local_model_path=ai_config.get("LOCAL_MODEL_PATH", None)
                )
                
                if self.ai_client:
                    # Initialize market analyzer
                    self.market_analyzer = MarketAnalyzer(ai_client=self.ai_client, config=ai_config)
                    
                    # Initialize contract analyzer
                    risk_patterns_file = ai_config.get("RISK_PATTERNS_FILE", None)
                    self.contract_analyzer = create_token_contract_analyzer(
                        ai_client=self.ai_client, 
                        config=ai_config,
                        risk_patterns_file=risk_patterns_file
                    )
                    
                    logger.info("AI-enhanced sniping enabled (Market + Contract Analysis)")
                    self.ai_enabled = True
                else:
                    logger.warning("Failed to initialize AI client, falling back to traditional analysis")
                    self.ai_enabled = False
                    self.market_analyzer = None
                    self.contract_analyzer = None
            except Exception as e:
                logger.error(f"Failed to initialize AI components: {e}")
                self.ai_enabled = False
                self.market_analyzer = None
                self.contract_analyzer = None
        else:
            self.ai_enabled = False
            self.ai_client = None
            self.market_analyzer = None
            self.contract_analyzer = None
        
        # Configuration du RPC
        self.rpc_url = rpc_url or os.environ.get("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
        self.ws_url = os.environ.get("SOLANA_WEBSOCKET_URL", "wss://api.mainnet-beta.solana.com")
        
        # Vérifier si les imports Solana sont OK
        if not SOLANA_IMPORTS_OK:
            logger.error("Les modules Solana ne sont pas disponibles. Le sniping ne fonctionnera pas.")
            return
            
        # Initialiser le client RPC
        self.commitment = Commitment(os.environ.get("SOLANA_PREFLIGHT_COMMITMENT", "processed"))
        self.client = AsyncClient(self.rpc_url, self.commitment, timeout=30)
        
        # Charger la clé privée
        self._load_private_key(wallet_keypair_path)
        
        # Configuration des programmes Solana
        self.raydium_amm_program_id = PublicKey(os.environ.get(
            "RAYDIUM_AMM_PROGRAM", "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"))
        self.token_program_id = PublicKey("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
        
        # Tokens de base (USDC, SOL, etc.)
        self.base_tokens = {
            "USDC": PublicKey("EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"),
            "SOL": PublicKey("So11111111111111111111111111111111111111112"),
            "USDT": PublicKey("Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"),
        }
        
        # Configuration du sniping
        self.max_amount_per_snipe = float(os.environ.get("MAX_SNIPE_AMOUNT_USD", "100"))
        self.take_profit_percent = float(os.environ.get("DEFAULT_TAKE_PROFIT", "20.0"))
        self.stop_loss_percent = float(os.environ.get("DEFAULT_STOP_LOSS", "10.0"))
        self.use_trailing_stop = os.environ.get("TRAILING_TAKE_PROFIT", "true").lower() == "true"
        self.trailing_percent = float(os.environ.get("TRAILING_PERCENT", "5.0"))
        self.check_honeypot = os.environ.get("CHECK_HONEYPOT", "true").lower() == "true"
        self.min_liquidity_usd = float(os.environ.get("MIN_LIQUIDITY_USD", "10000"))
        
        # État interne
        self.active_snipes = {}
        self.watched_pairs = set()
        self.blacklisted_tokens = set(os.environ.get("BLACKLISTED_TOKENS", "").split(","))
        self.token_info_cache = {}
        self.max_token_cache_size = int(os.environ.get("MAX_TOKEN_CACHE_SIZE", "1000"))
        self.max_blacklist_size = int(os.environ.get("MAX_BLACKLIST_SIZE", "5000"))
        self.running = False
        self.mempool_listener_task = None
        self.price_update_task = None
        self.snipe_manager_task = None
        
        # Compteurs et statistiques
        self.stats = {
            "tokens_detected": 0,
            "tokens_analyzed": 0,
            "tokens_sniped": 0,
            "successful_snipes": 0,
            "failed_snipes": 0,
            "total_profit_usd": 0.0,
            "total_loss_usd": 0.0,
            "start_time": None,
            "manipulations_detected": 0,
            "volatility_predictions": 0,
            "high_volatility_detected": 0,
        }
        
        # Initialiser l'analyseur de marché basé sur l'IA si disponible
        self.ai_market_analyzer = None
        self.use_ai_analysis = self.config.get("use_ai_analysis", os.environ.get("USE_AI_ANALYSIS", "true").lower() == "true")
        
        if self.use_ai_analysis and AI_IMPORTS_OK:
            self._initialize_ai_analyzer()
        else:
            logger.warning("L'analyse de marché par IA est désactivée ou non disponible")
        
        # Configuration MEV
        self.use_mev_protection = self.config.get("use_mev_protection", True)
        self.mev_optimizer = None
        self.jito_tip_percentage = self.config.get("jito_tip_percentage", 0.5)  # % du profit attendu
        self.jito_tip_account = self.config.get("jito_tip_account")
        self.jito_auth_keypair_path = self.config.get("jito_auth_keypair_path")
        self.jito_endpoint = self.config.get("jito_endpoint", "http://localhost:8100")
        
        # Statistiques MEV
        self.mev_stats = {
            "transactions_sent_via_jito": 0,
            "transactions_sent_standard": 0,
            "estimated_mev_saved": 0.0,
            "total_jito_tips_paid": 0.0,
        }
        
        # Initialiser l'optimiseur MEV si disponible
        self._initialize_mev_optimizer()
        
        # Configuration de l'analyseur léger
        self.use_lightweight_analyzer = self.config.get("use_lightweight_analyzer", True)
        self.lightweight_analyzer = None
        self.lightweight_analyzer_models_dir = self.config.get("lightweight_models_dir")
        self.lightweight_analysis_enabled = self.use_lightweight_analyzer and LIGHTWEIGHT_ANALYZER_AVAILABLE
        self.lightweight_analysis_timeout_ms = self.config.get("lightweight_analysis_timeout_ms", 500)  # 500ms max
        
        # Statistiques d'analyse légère
        self.lightweight_stats = {
            "total_analyses": 0,
            "analyses_succeeded": 0,
            "analyses_failed": 0,
            "tokens_rejected": 0,
            "avg_analysis_time_ms": 0.0,
            "tokens_analyzed_ids": set()  # Pour éviter les doublons
        }
        
        logger.info(f"Solana Memecoin Sniper initialisé avec RPC: {self.rpc_url}")
    
    def _load_private_key(self, private_key: Optional[str] = None) -> None:
        """
        Charge la clé privée pour les transactions
        
        Args:
            private_key: Clé privée (base58) ou chemin vers un fichier de keystore
        """
        try:
            self.private_key = None
            self.public_key = None
            
            # Priorité 1: Argument direct
            if private_key:
                self.private_key = base58.b58decode(private_key)
                self.public_key = PublicKey(self._get_public_key_from_private(self.private_key))
                return
                
            # Priorité 2: Variable d'environnement
            env_key = os.environ.get("MAIN_PRIVATE_KEY")
            if env_key and env_key != "VOTRE_CLE_PRIVEE_ICI":
                self.private_key = base58.b58decode(env_key)
                self.public_key = PublicKey(self._get_public_key_from_private(self.private_key))
                return
                
            # Priorité 3: Fichier keystore
            keystore_path = os.environ.get("KEYSTORE_PATH", "data/solana_wallet.json")
            if os.path.exists(keystore_path):
                with open(keystore_path, "r") as f:
                    keystore = json.load(f)
                    # Il faudrait normalement décrypter le keystore avec un mot de passe
                    # C'est juste un exemple simplifié
                    if "privateKey" in keystore:
                        self.private_key = base58.b58decode(keystore["privateKey"])
                        self.public_key = PublicKey(self._get_public_key_from_private(self.private_key))
                        return
            
            logger.warning("Aucune clé privée Solana trouvée. Les transactions ne fonctionneront pas.")
            
        except Exception as e:
            logger.error(f"Erreur lors du chargement de la clé privée: {str(e)}")
            self.private_key = None
            self.public_key = None
    
    def _get_public_key_from_private(self, private_key: bytes) -> str:
        """
        Dérive la clé publique à partir de la clé privée
        Ceci est un placeholder - l'implémentation réelle dépend de la bibliothèque utilisée
        
        Args:
            private_key: La clé privée au format bytes
            
        Returns:
            str: La clé publique au format base58
        """
        # NOTE: Ceci est un placeholder - en pratique, il faudrait utiliser 
        # la cryptographie appropriée pour dériver la clé publique
        # Dans solana-py, la clé publique est généralement déjà connue ou dérivée par la bibliothèque
        
        # Si on a les imports solana corrects, on pourrait faire:
        # from solana.keypair import Keypair
        # keypair = Keypair.from_secret_key(private_key)
        # return str(keypair.public_key)
        
        return "DummyPublicKey"  # Placeholder
    
    async def start(self) -> bool:
        """
        Démarre le sniping de memecoins Solana
        
        Returns:
            bool: True si démarré avec succès, False sinon
        """
        if not SOLANA_IMPORTS_OK:
            logger.error("Impossible de démarrer: modules Solana manquants")
            return False
            
        if self.running:
            logger.warning("Le sniper est déjà en cours d'exécution")
            return True
            
        logger.info("Démarrage du Solana Memecoin Sniper...")
        
        try:
            # Vérifier la connexion au RPC
            resp = await self.client.get_health()
            if resp != "ok":
                logger.error(f"Le RPC Solana n'est pas disponible: {resp}")
                return False
                
            # Vérifier le solde du wallet
            if self.public_key:
                balance_resp = await self.client.get_balance(self.public_key)
                balance_sol = balance_resp["result"]["value"] / 1_000_000_000
                logger.info(f"Solde du wallet: {balance_sol} SOL")
                
                if balance_sol < 0.05:
                    logger.warning(f"Solde faible: {balance_sol} SOL. Certaines transactions pourraient échouer.")
            else:
                logger.warning("Pas de clé publique configurée. Mode lecture seule.")
            
            # Démarrer les tâches de surveillance
            self.running = True
            self.stats["start_time"] = time.time()
            
            # Tâche 1: Écoute du mempool pour les nouveaux tokens
            self.mempool_listener_task = asyncio.create_task(self._mempool_listener())
            
            # Tâche 2: Mise à jour des prix pour les snipes actifs
            self.price_update_task = asyncio.create_task(self._price_update_loop())
            
            # Tâche 3: Gestion des snipes actifs (stop-loss, take-profit)
            self.snipe_manager_task = asyncio.create_task(self._snipe_manager())
            
            # Initialiser l'analyseur léger si disponible
            self._initialize_lightweight_analyzer()
            
            logger.info("Solana Memecoin Sniper démarré avec succès")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors du démarrage du sniper: {str(e)}")
            self.running = False
            return False
    
    async def stop(self) -> None:
        """Arrête le sniping de memecoins"""
        if not self.running:
            logger.warning("Le sniper n'est pas en cours d'exécution")
            return
            
        logger.info("Arrêt du Solana Memecoin Sniper...")
        
        try:
            # Arrêter les tâches de surveillance
            self.running = False
            
            for task in [self.mempool_listener_task, self.price_update_task, self.snipe_manager_task]:
                if task and not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
            
            # Fermer la connexion client
            await self.client.close()
            
            # Fermer l'optimiseur MEV si actif
            if self.mev_optimizer:
                try:
                    await self.mev_optimizer.close()
                    logger.info("Optimiseur MEV fermé")
                except Exception as e:
                    logger.error(f"Erreur lors de la fermeture de l'optimiseur MEV: {e}")
            
            # Loguer les statistiques d'analyse légère si disponible
            if self.lightweight_analysis_enabled and self.lightweight_analyzer:
                analyzer_stats = self.lightweight_analyzer.get_statistics()
                logger.info(f"Statistiques d'analyse légère: {json.dumps(self.lightweight_stats, default=str)}")
                logger.info(f"Statistiques de l'analyseur: {json.dumps(analyzer_stats, default=str)}")
            
            logger.info("Solana Memecoin Sniper arrêté avec succès")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'arrêt du sniper: {str(e)}")
    
    async def _mempool_listener(self) -> None:
        """
        Écoute les transactions dans le mempool pour détecter les nouveaux tokens
        et les mouvements de liquidité
        """
        logger.info("Démarrage de l'écoute du mempool Solana...")
        
        try:
            while self.running:
                # Cette implémentation est simplifiée.
                # Dans un cas réel, il faudrait utiliser un websocket pour écouter les transactions
                # qui créent de nouveaux tokens ou ajoutent de la liquidité
                
                # Vérification périodique des nouveaux tokens (simulation de l'écoute du mempool)
                detected_tokens = await self._detect_new_tokens()
                
                for token_info in detected_tokens:
                    if await self._should_snipe_token(token_info):
                        await self._execute_snipe(token_info)
                
                # Attendre un court délai avant la prochaine vérification
                await asyncio.sleep(2)
                
        except asyncio.CancelledError:
            logger.info("Écoute du mempool arrêtée")
        except Exception as e:
            logger.error(f"Erreur dans l'écoute du mempool: {str(e)}")
            if self.running:
                # Redémarrer l'écoute en cas d'erreur
                asyncio.create_task(self._mempool_listener())
    
    async def _detect_new_tokens(self) -> List[Dict]:
        """
        Détecte les nouveaux tokens sur Solana
        
        Returns:
            List[Dict]: Liste d'informations sur les nouveaux tokens détectés
        """
        # Cette fonction est une simulation - dans un cas réel, 
        # elle devrait analyser les transactions en temps réel
        # Pour détecter les nouveaux tokens et les ajouts de liquidité
        
        # Simuler la détection d'un nouveau token (1% de chance)
        detected_tokens = []
        if random.random() < 0.01:
            token_address = f"RandomToken{int(time.time())}"
            
            # Simuler les infos d'un nouveau token
            token_info = {
                "address": token_address,
                "name": f"Meme Token {token_address[-4:]}",
                "symbol": f"MEME{token_address[-4:]}",
                "decimals": 9,
                "liquidity_usd": random.uniform(5000, 100000),
                "creation_time": time.time(),
                "base_token": "USDC",
                "pair_address": f"Pair{token_address}"
            }
            
            # Limiter la taille du cache de tokens
            if len(self.token_info_cache) >= self.max_token_cache_size:
                # Supprimer 20% des entrées les plus anciennes
                keys_to_remove = list(self.token_info_cache.keys())[:int(self.max_token_cache_size * 0.2)]
                for key in keys_to_remove:
                    del self.token_info_cache[key]
                logger.debug(f"Cache de tokens nettoyé, {len(keys_to_remove)} entrées supprimées")
            
            # Ajouter au cache
            self.token_info_cache[token_address] = token_info
            
            self.stats["tokens_detected"] += 1
            detected_tokens.append(token_info)
            logger.info(f"Nouveau token détecté: {token_info['symbol']} ({token_address})")
        
        return detected_tokens
    
    async def _should_snipe_token(self, token_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Détermine si un token doit être snipé basé sur différents critères,
        incluant l'analyse de microstructure du marché et la prédiction de volatilité.
        
        Args:
            token_data: Données du token
            
        Returns:
            Tuple[bool, str]: (Doit être snipé, Raison)
        """
        # Vérification initiale des critères de base
        if not self._pass_basic_security_checks(token_data):
            return False, "Échec des vérifications de sécurité de base"
        
        # Vérifier l'analyse de microstructure si disponible
        try:
            if MARKET_MICROSTRUCTURE_ANALYZER_AVAILABLE and hasattr(self, 'market_microstructure_analyzer') and self.market_microstructure_analyzer is not None:
                market_address = token_data.get("pair_address")
                if market_address:
                    start_time = time.time()
                    # Analyser le carnet d'ordres pour détecter les manipulations
                    manipulation_results = await self.market_microstructure_analyzer.analyze_order_book(market_address)
                    
                    # Vérifier également la détection de manipulation spécifique
                    manipulation_detection = await self.market_microstructure_analyzer.detect_market_manipulation(market_address)
                    
                    elapsed_ms = (time.time() - start_time) * 1000
                    logger.info(f"Analyse de microstructure pour {token_data.get('symbol', 'inconnu')} terminée en {elapsed_ms:.2f}ms")
                    
                    # Prendre une décision basée sur les résultats
                    if manipulation_results.get("manipulation_detected") or manipulation_detection.get("manipulation_detected"):
                        manipulation_type = (
                            manipulation_results.get("manipulation_type") or 
                            manipulation_detection.get("manipulation_type") or 
                            "unknown"
                        )
                        logger.warning(f"Manipulation de marché détectée pour {token_data.get('symbol', 'inconnu')}: {manipulation_type}")
                        self.stats["manipulations_detected"] += 1
                        return False, f"Manipulation de marché détectée: {manipulation_type}"
                    
                    # Des indicateurs positifs de microstructure peuvent renforcer la confiance
                    if manipulation_results.get("market_health", 0) > 80:
                        logger.info(f"Indicateurs de microstructure très positifs pour {token_data.get('symbol', 'inconnu')}")
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse de microstructure: {str(e)}")
            # Continuer malgré l'erreur, mais avec une note dans les logs
        
        # Vérifier la prédiction de volatilité si disponible
        try:
            if VOLATILITY_PREDICTOR_AVAILABLE and hasattr(self, 'volatility_predictor') and self.volatility_predictor is not None:
                # Préparer les données pour la prédiction de volatilité
                price_data = self._prepare_price_data_for_volatility(token_data)
                
                # Prédire la volatilité
                start_time = time.time()
                volatility_prediction = await self.volatility_predictor.predict_volatility(price_data, timeframe="15min")
                elapsed_ms = (time.time() - start_time) * 1000
                
                self.stats["volatility_predictions"] += 1
                
                if volatility_prediction.get("success", False):
                    logger.info(f"Prédiction de volatilité pour {token_data.get('symbol', 'inconnu')} terminée en {elapsed_ms:.2f}ms")
                    
                    # Enregistrer la prédiction pour référence future
                    token_data["volatility_prediction"] = volatility_prediction
                    
                    predicted_volatility = volatility_prediction.get("predicted_volatility", 0)
                    volatility_level = volatility_prediction.get("volatility_level", "moyenne")
                    confidence_score = volatility_prediction.get("confidence_score", 0.5)
                    
                    logger.info(f"Volatilité prédite pour {token_data.get('symbol', 'inconnu')}: {predicted_volatility:.4f} "
                               f"(niveau: {volatility_level}, confiance: {confidence_score:.2f})")
                    
                    # Prendre une décision basée sur la volatilité prédite
                    if volatility_level == "élevée":
                        self.stats["high_volatility_detected"] += 1
                        
                        # Si la confiance est élevée, adapter la stratégie
                        if confidence_score > 0.8:
                            # Dans certains cas, une volatilité très élevée peut indiquer un risque
                            # Si le ratio est très élevé, nous pourrions vouloir attendre
                            volatility_ratio = predicted_volatility / token_data.get("historical_volatility", 0.01)
                            if volatility_ratio > 3.0:
                                logger.warning(f"Volatilité prédite extrêmement élevée pour {token_data.get('symbol', 'inconnu')}")
                                return False, f"Volatilité prédite extrêmement élevée (ratio: {volatility_ratio:.2f}), trop risqué"
                            
                            # Adapter les paramètres de trading (sera utilisé lors du sniping)
                            recommendations = volatility_prediction.get("recommendations", {})
                            token_data["trading_recommendations"] = recommendations
                            
                            # Haute volatilité = opportunité potentielle + risque accru
                            logger.info(f"Haute volatilité détectée pour {token_data.get('symbol', 'inconnu')}, adaptation des paramètres de trading")
                
                else:
                    logger.warning(f"Échec de la prédiction de volatilité: {volatility_prediction.get('error', 'Erreur inconnue')}")
            
        except Exception as e:
            logger.error(f"Erreur lors de la prédiction de volatilité: {str(e)}")
            # Continuer malgré l'erreur, mais avec une note dans les logs
        
        # Continuer avec les autres vérifications existantes
        return self._legacy_should_snipe_token(token_data)
    
    async def _fetch_contract_code(self, contract_address: str) -> Optional[str]:
        """
        Attempt to fetch contract code for analysis.
        
        Args:
            contract_address: Token contract address
            
        Returns:
            Optional[str]: Contract code if available, None otherwise
        """
        # For now, return None as Solana doesn't easily expose contract code
        # Future implementation can integrate with explorers or other sources
        return None
    
    def _prepare_token_data_for_analysis(self, token_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert internal token data format to the format expected by the market analyzer.
        
        Args:
            token_data: Internal token data
            
        Returns:
            Dict[str, Any]: Formatted data for AI analysis
        """
        # Extract and normalize relevant fields
        return {
            "symbol": token_data.get("symbol", "Unknown"),
            "name": token_data.get("name", token_data.get("symbol", "Unknown")),
            "address": token_data.get("mint", ""),
            "price_usd": token_data.get("price", 0.0),
            "price_change_24h": token_data.get("price_change_24h", 0.0),
            "market_cap": token_data.get("market_cap", 0),
            "volume_24h": token_data.get("volume_24h", 0),
            "liquidity_usd": token_data.get("liquidity", 0),
            "holders": token_data.get("holders", 0),
            "transactions_24h": token_data.get("transactions_24h", 0),
            "launch_date": token_data.get("created_at", "Unknown"),
            "contract_verified": token_data.get("verified", False),
            "liquidity_locked": token_data.get("liquidity_locked", False),
            "tax_buy": token_data.get("buy_tax", 0),
            "tax_sell": token_data.get("sell_tax", 0)
        }
    
    def _pass_basic_security_checks(self, token_data: Dict[str, Any]) -> bool:
        """
        Perform quick security checks that don't require AI analysis.
        
        Args:
            token_data: Token data
            
        Returns:
            bool: True if passes basic checks, False otherwise
        """
        # Check if token has a name/symbol
        if not token_data.get("symbol") and not token_data.get("name"):
            logger.warning("Token without name or symbol - suspicious")
            return False
        
        # Check for minimum liquidity
        min_liquidity = self.config.get("MIN_LIQUIDITY_USD", 500)
        if token_data.get("liquidity", 0) < min_liquidity:
            logger.warning(f"Insufficient liquidity: ${token_data.get('liquidity', 0)} (min: ${min_liquidity})")
            return False
        
        # Check for suspiciously high taxes
        max_tax = self.config.get("MAX_TAX_PERCENTAGE", 10)
        if token_data.get("buy_tax", 0) > max_tax or token_data.get("sell_tax", 0) > max_tax:
            logger.warning(f"High tax detected: Buy {token_data.get('buy_tax', 0)}%, Sell {token_data.get('sell_tax', 0)}%")
            return False
        
        return True
    
    def _legacy_should_snipe_token(self, token_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Legacy method for token sniping decision without AI.
        
        Args:
            token_data: Token data
            
        Returns:
            Tuple[bool, str]: Decision and reason
        """
        # Existing implementation...
        # This should be the current implementation of _should_snipe_token
        # Keep the implementation intact
        
        # For example, check if it meets minimum criteria
        min_liquidity = self.config.get("MIN_LIQUIDITY_USD", 1000)
        if token_data.get("liquidity", 0) < min_liquidity:
            return False, f"Insufficient liquidity: ${token_data.get('liquidity', 0)} (min: ${min_liquidity})"
        
        # Check for maximum spread
        max_spread = self.config.get("MAX_SPREAD_PERCENTAGE", 15)
        current_spread = token_data.get("spread_percentage", 0)
        if current_spread > max_spread:
            return False, f"Spread too high: {current_spread}% (max: {max_spread}%)"
        
        # Check for creation time (we want new tokens)
        max_age_minutes = self.config.get("MAX_TOKEN_AGE_MINUTES", 60)
        creation_time = token_data.get("created_at")
        if creation_time:
            try:
                age_minutes = (datetime.now() - datetime.fromisoformat(creation_time)).total_seconds() / 60
                if age_minutes > max_age_minutes:
                    return False, f"Token too old: {age_minutes:.1f} minutes (max: {max_age_minutes})"
            except:
                pass
        
        return True, "Token passed basic criteria"
    
    async def _execute_snipe(self, token_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Exécute le sniping d'un token.
        
        Args:
            token_data: Données du token
            
        Returns:
            Tuple[bool, str]: (Succès, Message)
        """
        if self.simulation_mode:
            logger.info("Mode simulation - pas de transaction réelle")
            snipe_id = f"sim_{token_data['mint']}_{int(time.time())}"
            return True, snipe_id
            
        token_mint = token_data.get("mint")
        token_symbol = token_data.get("symbol", "Unknown")
        
        logger.info(f"Preparing to snipe {token_symbol} ({token_mint})")
        
        try:
            # Get base investment amount
            base_amount = self.config.get("BASE_INVESTMENT_AMOUNT", 0.05)
            
            # Determine AI-optimized parameters if available
            if self.ai_enabled and self.market_analyzer:
                try:
                    # Get AI score if available
                    market_data = self._prepare_token_data_for_analysis(token_data)
                    token_analysis = await self.market_analyzer.analyze_token(market_data)
                    
                    ai_score = token_analysis.get("potential_score", 60)
                    
                    # Adjust investment amount based on AI score
                    if ai_score >= 90:  # Extremely promising token
                        adjusted_amount = base_amount * 1.5
                        max_slippage = 15  # Accept higher slippage for exceptional opportunities
                    elif ai_score >= 80:
                        adjusted_amount = base_amount * 1.25
                        max_slippage = 10
                    elif ai_score >= 70:
                        adjusted_amount = base_amount * 1.1
                        max_slippage = 8
                    else:
                        adjusted_amount = base_amount
                        max_slippage = 5
                    
                    # Adjust take-profit thresholds based on AI
                    expected_growth = token_analysis.get("expected_growth", 2.0)
                    take_profit_target = max(1.5, min(5.0, expected_growth * 0.8))  # 80% of expected growth, bounded
                    
                    logger.info(f"AI-optimized parameters: Amount: {adjusted_amount} SOL, " +
                              f"Slippage: {max_slippage}%, Take-profit: {take_profit_target}x")
                    
                except Exception as e:
                    logger.error(f"Error getting AI-optimized parameters: {e}")
                    adjusted_amount = base_amount
                    max_slippage = self.config.get("MAX_SLIPPAGE_PERCENTAGE", 5)
                    take_profit_target = self.config.get("TAKE_PROFIT_MULTIPLIER", 2.0)
            else:
                # Use default parameters if AI is not available
                adjusted_amount = base_amount
                max_slippage = self.config.get("MAX_SLIPPAGE_PERCENTAGE", 5)
                take_profit_target = self.config.get("TAKE_PROFIT_MULTIPLIER", 2.0)
            
            # Calculer le profit attendu pour l'optimisation MEV (estimation simplifiée)
            # Cette logique peut être affinée avec des calculs plus précis
            expected_profit_sol = None
            if token_analysis:
                # Si nous avons une analyse du token, utiliser son potentiel estimé
                potential_multiple = token_analysis.get("potential_multiple", 2.0)
                investment_sol = adjusted_amount
                expected_profit_sol = investment_sol * (potential_multiple - 1.0) * 0.8  # 80% du profit potentiel
            
            # Préparation de la transaction de swap
            # Note: Cette partie dépend de votre implémentation spécifique
            # Nous supposons que vous avez un code existant qui construit cette transaction
            
            # Calcul du profit attendu pour l'optimisation MEV (estimation simplifiée)
            expected_profit_sol = None
            if token_analysis:
                # Si nous avons une analyse du token, utiliser son potentiel estimé
                potential_multiple = token_analysis.get("potential_multiple", 2.0)
                investment_sol = adjusted_amount
                expected_profit_sol = investment_sol * (potential_multiple - 1.0) * 0.8  # 80% du profit potentiel
            
            # Construction de la transaction - à adapter selon votre implémentation actuelle
            # Ceci est un exemple simplifié, à remplacer par votre code existant
            transaction = await self._build_swap_transaction(
                token_data, 
                adjusted_amount,
                max_slippage
            )
            
            # Optimisation MEV pour la transaction
            success, tx_result = await self._send_transaction_with_mev_optimization(
                transaction, 
                expected_profit_sol
            )
            
            # Setup auto take-profit and stop-loss
            if self.config.get("AUTO_TAKE_PROFIT", True):
                # ...existing implementation with adjusted take_profit_target...
                pass
                
            # Adapter les paramètres de trading en fonction de la prédiction de volatilité
            if "volatility_prediction" in token_data and token_data["volatility_prediction"].get("success", False):
                volatility_level = token_data["volatility_prediction"].get("volatility_level", "moyenne")
                recommendations = token_data.get("trading_recommendations", {})
                
                # Adapter le stop-loss en fonction des recommandations
                sniping_recommendations = recommendations.get("sniping", {})
                stop_loss_type = sniping_recommendations.get("stop_loss", "standard")
                
                if stop_loss_type == "serré":
                    stop_loss_percent = self.stop_loss_percent * 0.8  # Plus serré (20% plus proche)
                elif stop_loss_type == "large":
                    stop_loss_percent = self.stop_loss_percent * 1.5  # Plus large (50% plus éloigné)
                else:
                    stop_loss_percent = self.stop_loss_percent  # Standard
                
                # Adapter le take-profit en fonction des recommandations
                take_profit_type = sniping_recommendations.get("take_profit", "standard")
                
                if take_profit_type == "échelonné":
                    # Configuration pour prises de profit échelonnées
                    take_profit_levels = [
                        {"percent": self.take_profit_percent * 0.5, "allocation": 0.3},  # 30% à 50% du TP
                        {"percent": self.take_profit_percent, "allocation": 0.4},        # 40% au TP standard
                        {"percent": self.take_profit_percent * 2, "allocation": 0.3}     # 30% à 200% du TP
                    ]
                    token_data["take_profit_levels"] = take_profit_levels
                elif take_profit_type == "modéré":
                    take_profit_percent = self.take_profit_percent * 0.7  # Plus modéré (70% du TP standard)
                else:
                    take_profit_percent = self.take_profit_percent  # Standard
                
                # Journaliser les adaptations
                logger.info(f"Paramètres de trading adaptés pour {token_data.get('symbol', 'inconnu')} "
                          f"basés sur la prédiction de volatilité: SL={stop_loss_percent:.1f}%, "
                          f"TP={take_profit_type}")
            
            # Return success
            return success, tx_result
            
        except Exception as e:
            logger.error(f"Error executing snipe: {e}")
            return False, f"Failed to execute snipe: {str(e)}"
    
    async def _build_swap_transaction(
        self, 
        token_data: Dict[str, Any], 
        amount_sol: float,
        slippage: float
    ) -> Transaction:
        """
        Construit une transaction de swap pour le token spécifié.
        Note: Cette méthode est un exemple et doit être adaptée à votre implémentation.
        
        Args:
            token_data: Données du token
            amount_sol: Montant en SOL à utiliser
            slippage: Slippage à appliquer (en pourcentage)
            
        Returns:
            Transaction: Transaction de swap
        """
        # Note: Cette méthode est une implémentation fictive
        # Remplacez-la par votre implémentation réelle de construction de transaction
        
        # Exemple simplifié
        transaction = Transaction()
        
        # Obtenir un blockhash récent
        blockhash = (await self.client.get_recent_blockhash()).value.blockhash
        transaction.recent_blockhash = blockhash
        
        # Ajouter les instructions de swap ici selon votre logique
        # ...
        
        # Signer la transaction
        if self.wallet:
            transaction.sign(self.wallet)
            
        return transaction
    
    async def _send_transaction_with_mev_optimization(
        self, 
        transaction: Transaction, 
        expected_profit: Optional[float] = None
    ) -> Tuple[bool, str]:
        """
        Envoie une transaction avec optimisation MEV si disponible.
        
        Args:
            transaction: Transaction Solana à envoyer
            expected_profit: Profit attendu en SOL (pour calculer les tips Jito)
            
        Returns:
            Tuple[bool, str]: (Succès, ID de transaction ou message d'erreur)
        """
        # Si l'optimiseur MEV est disponible et activé, l'utiliser
        if self.mev_optimizer and self.use_mev_protection:
            try:
                logger.info("Envoi de transaction via optimiseur MEV Jito...")
                
                # Calculer le tip basé sur le profit attendu
                jito_tip = None
                if expected_profit:
                    jito_tip = expected_profit * (self.jito_tip_percentage / 100.0)
                    logger.info(f"Profit attendu: {expected_profit:.4f} SOL, tip Jito: {jito_tip:.4f} SOL")
                
                # Envoyer la transaction via Jito
                success, tx_id = await self.mev_optimizer.send_transaction_via_jito(
                    transaction, 
                    expected_profit, 
                    tip_override=jito_tip
                )
                
                # Mettre à jour les statistiques
                if success:
                    self.mev_stats["transactions_sent_via_jito"] += 1
                    
                    # Mettre à jour les statistiques depuis l'optimiseur
                    if hasattr(self.mev_optimizer, "get_statistics"):
                        optimizer_stats = self.mev_optimizer.get_statistics()
                        self.mev_stats["estimated_mev_saved"] = optimizer_stats.get("estimated_mev_saved_sol", 0.0)
                        self.mev_stats["total_jito_tips_paid"] = optimizer_stats.get("total_tips_paid_sol", 0.0)
                        
                    logger.info(f"Transaction optimisée pour MEV envoyée avec succès: {tx_id}")
                    return success, tx_id
                else:
                    logger.warning(f"Échec de l'optimisation MEV: {tx_id}, fallback vers envoi standard")
            except Exception as e:
                logger.error(f"Erreur lors de l'envoi via optimiseur MEV: {e}")
                logger.warning("Fallback vers envoi standard")
        
        # Méthode standard si l'optimiseur n'est pas disponible ou a échoué
        try:
            # Préparer la transaction si nécessaire
            if not transaction.recent_blockhash:
                blockhash = (await self.client.get_recent_blockhash()).value.blockhash
                transaction.recent_blockhash = blockhash
                
            # Envoyer la transaction
            signature = await self.client.send_transaction(transaction)
            tx_sig = signature.value
            
            self.mev_stats["transactions_sent_standard"] += 1
            logger.info(f"Transaction envoyée via méthode standard: {tx_sig}")
            
            return True, tx_sig
            
        except Exception as e:
            error_msg = f"Échec de l'envoi de transaction: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    async def _price_update_loop(self) -> None:
        """Boucle de mise à jour des prix pour les snipes actifs"""
        logger.info("Démarrage de la boucle de mise à jour des prix...")
        
        try:
            while self.running:
                for snipe_id, snipe_data in list(self.active_snipes.items()):
                    # Dans un cas réel, nous interrogerions le DEX pour obtenir le prix actuel
                    # Ici, nous simulons des mouvements de prix
                    
                    # Simuler un changement de prix (-5% à +10%)
                    price_change = random.uniform(-0.05, 0.1)
                    new_price = snipe_data["current_price"] * (1 + price_change)
                    
                    # Mettre à jour le prix actuel
                    snipe_data["current_price"] = new_price
                    
                    # Mettre à jour le prix le plus élevé si nécessaire
                    if new_price > snipe_data["highest_price"]:
                        snipe_data["highest_price"] = new_price
                        
                        # Ajuster le stop loss trailing si activé
                        if snipe_data["trailing_stop"]:
                            new_stop_loss = new_price * (1 - snipe_data["trailing_distance"] / 100)
                            # Ne déplacer le stop loss que vers le haut
                            if new_stop_loss > snipe_data["stop_loss_percent"] / 100:
                                snipe_data["stop_loss_percent"] = new_stop_loss * 100
                                logger.info(f"Stop loss ajusté pour {snipe_data['token']['symbol']}: {snipe_data['stop_loss_percent']:.2f}%")
                    
                # Attendre avant la prochaine mise à jour
                await asyncio.sleep(5)
                
        except asyncio.CancelledError:
            logger.info("Boucle de mise à jour des prix arrêtée")
        except Exception as e:
            logger.error(f"Erreur dans la boucle de mise à jour des prix: {str(e)}")
            if self.running:
                # Redémarrer la boucle en cas d'erreur
                asyncio.create_task(self._price_update_loop())
    
    async def _snipe_manager(self) -> None:
        """Gère les snipes actifs (take profit, stop loss)"""
        logger.info("Démarrage du gestionnaire de snipes...")
        
        try:
            while self.running:
                for snipe_id, snipe_data in list(self.active_snipes.items()):
                    current_price = snipe_data["current_price"]
                    entry_price = snipe_data["price_entry"]
                    take_profit_percent = snipe_data["take_profit_percent"]
                    stop_loss_percent = snipe_data["stop_loss_percent"]
                    token_symbol = snipe_data["token"]["symbol"]
                    
                    # Vérifier si le take profit est atteint
                    if current_price >= (1 + take_profit_percent / 100) * entry_price:
                        profit_percent = (current_price / entry_price - 1) * 100
                        profit_usd = snipe_data["amount_sol"] * (current_price / entry_price - 1)
                        
                        logger.info(f"Take profit atteint pour {token_symbol}: +{profit_percent:.2f}% (${profit_usd:.2f})")
                        
                        # Simuler la vente
                        await self._close_position(snipe_id, "take_profit")
                        continue
                    
                    # Vérifier si le stop loss est atteint
                    if current_price <= (1 - stop_loss_percent / 100) * entry_price:
                        loss_percent = (1 - current_price / entry_price) * 100
                        loss_usd = snipe_data["amount_sol"] * (1 - current_price / entry_price)
                        
                        logger.info(f"Stop loss atteint pour {token_symbol}: -{loss_percent:.2f}% (-${loss_usd:.2f})")
                        
                        # Simuler la vente
                        await self._close_position(snipe_id, "stop_loss")
                        continue
                    
                    # Vérifier si le temps maximum est dépassé (1 heure)
                    if time.time() - snipe_data["time_entry"] > 3600:
                        profit_percent = (current_price / entry_price - 1) * 100
                        
                        logger.info(f"Temps maximum dépassé pour {token_symbol}: {profit_percent:.2f}%")
                        
                        # Simuler la vente
                        await self._close_position(snipe_id, "time_limit")
                        continue
                
                # Attendre avant la prochaine vérification
                await asyncio.sleep(3)
                
        except asyncio.CancelledError:
            logger.info("Gestionnaire de snipes arrêté")
        except Exception as e:
            logger.error(f"Erreur dans le gestionnaire de snipes: {str(e)}")
            if self.running:
                # Redémarrer le gestionnaire en cas d'erreur
                asyncio.create_task(self._snipe_manager())
    
    async def _close_position(self, snipe_id: str, reason: str) -> None:
        """
        Ferme une position (vend un token)
        
        Args:
            snipe_id: Identifiant du snipe
            reason: Raison de la fermeture (take_profit, stop_loss, manual, time_limit)
        """
        if snipe_id not in self.active_snipes:
            logger.warning(f"Impossible de fermer la position {snipe_id}: non trouvée")
            return
            
        snipe_data = self.active_snipes[snipe_id]
        token_symbol = snipe_data["token"]["symbol"]
        entry_price = snipe_data["price_entry"]
        current_price = snipe_data["current_price"]
        
        # Calculer le profit/perte
        profit_percent = (current_price / entry_price - 1) * 100
        profit_usd = snipe_data["amount_sol"] * (current_price / entry_price - 1)
        
        logger.info(f"Fermeture de la position sur {token_symbol}: {profit_percent:.2f}% (${profit_usd:.2f}) - Raison: {reason}")
        
        try:
            # Dans un cas réel, nous construirions une transaction Solana
            # pour vendre le token
            
            # Simuler la vente
            # 95% de chance que la vente réussisse
            success = random.random() < 0.95
            
            if success:
                # Mettre à jour les statistiques
                if profit_usd > 0:
                    self.stats["successful_snipes"] += 1
                    self.stats["total_profit_usd"] += profit_usd
                else:
                    self.stats["total_loss_usd"] -= profit_usd  # Profit négatif = perte
                
                # Supprimer le snipe de la liste des actifs
                del self.active_snipes[snipe_id]
                
                logger.info(f"Position fermée avec succès sur {token_symbol}")
            else:
                logger.warning(f"Échec de la fermeture de position sur {token_symbol}")
                
        except Exception as e:
            logger.error(f"Erreur lors de la fermeture de position sur {token_symbol}: {str(e)}")
    
    def get_stats(self) -> Dict:
        """
        Récupère les statistiques du sniper.
        
        Returns:
            Dict: Statistiques du sniper
        """
        runtime = time.time() - (self.stats["start_time"] or time.time())
        runtime_str = str(timedelta(seconds=int(runtime)))
        
        net_profit = self.stats["total_profit_usd"] - self.stats["total_loss_usd"]
        
        stats = {
            "tokens_detected": self.stats["tokens_detected"],
            "tokens_analyzed": self.stats["tokens_analyzed"],
            "tokens_sniped": self.stats["tokens_sniped"],
            "successful_snipes": self.stats["successful_snipes"],
            "failed_snipes": self.stats["failed_snipes"],
            "total_profit_usd": self.stats["total_profit_usd"],
            "total_loss_usd": self.stats["total_loss_usd"],
            "net_profit_usd": net_profit,
            "active_snipes": len(self.active_snipes),
            "running_time": runtime_str,
            "hourly_profit": net_profit / (runtime / 3600) if runtime > 0 else 0,
            "mev_optimization": {
                "enabled": self.use_mev_protection,
                "available": JITO_OPTIMIZER_AVAILABLE,
                "transactions_sent_via_jito": self.mev_stats["transactions_sent_via_jito"],
                "transactions_sent_standard": self.mev_stats["transactions_sent_standard"],
                "estimated_mev_saved_sol": self.mev_stats["estimated_mev_saved"],
                "total_jito_tips_paid_sol": self.mev_stats["total_jito_tips_paid"],
                "net_benefit_sol": self.mev_stats["estimated_mev_saved"] - self.mev_stats["total_jito_tips_paid"]
            },
            "lightweight_analysis": {
                "enabled": self.lightweight_analysis_enabled,
                "available": LIGHTWEIGHT_ANALYZER_AVAILABLE,
                "total_analyses": self.lightweight_stats["total_analyses"],
                "analyses_succeeded": self.lightweight_stats["analyses_succeeded"],
                "analyses_failed": self.lightweight_stats["analyses_failed"],
                "tokens_rejected": self.lightweight_stats["tokens_rejected"],
                "avg_analysis_time_ms": self.lightweight_stats["avg_analysis_time_ms"],
                "analyzer_details": self.lightweight_analyzer.get_statistics() if self.lightweight_analyzer else {}
            }
        }
        
        return stats

    def _initialize_ai_analyzer(self) -> None:
        """Initialise l'analyseur de marché basé sur l'IA"""
        try:
            # Vérifier si l'IA est activée dans la configuration
            self.use_ai_analysis = self.config.get("use_ai_analysis", os.environ.get("USE_AI_ANALYSIS", "true").lower() == "true")
            
            if not self.use_ai_analysis:
                logger.info("Analyse IA désactivée dans la configuration")
                return
                
            if not AI_IMPORTS_OK:
                logger.warning("Modules d'IA non disponibles, impossible d'initialiser l'analyseur")
                self.use_ai_analysis = False
                return
                
            # Créer un client d'IA
            ai_provider = self.config.get("ai_provider", os.environ.get("AI_PROVIDER", "auto"))
            ai_client = create_ai_client(provider=ai_provider)
            
            if ai_client is None:
                logger.warning("Impossible de créer le client d'IA. L'analyse par IA sera désactivée.")
                self.use_ai_analysis = False
                return
                
            # Créer le gestionnaire de prompts
            prompt_manager = get_prompt_manager()
            
            # Créer l'analyseur de marché
            self.ai_market_analyzer = MarketAnalyzer(ai_client, prompt_manager)
            logger.info("Analyseur de marché IA initialisé avec succès")
            
            # Configurer les seuils spécifiques à l'IA
            self.config["min_ai_score"] = self.config.get("min_ai_score", 0.65)
            
            # Charger les patterns connus à haut risque (historique des analyses)
            self._load_ai_risk_patterns()
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de l'analyseur de marché IA: {str(e)}")
            self.ai_market_analyzer = None
            self.use_ai_analysis = False
    
    def _load_ai_risk_patterns(self) -> None:
        """Charge les patterns de risque identifiés par l'IA"""
        try:
            # Chemin vers le fichier de patterns risqués
            risk_patterns_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
                "data",
                "ai_risk_patterns.json"
            )
            
            # Vérifier si le fichier existe
            if not os.path.exists(risk_patterns_path):
                # Créer un fichier initial avec quelques patterns connus
                default_patterns = {
                    "high_risk_patterns": [
                        "pump_and_dump",
                        "rug_pull_preparation",
                        "distribution_phase",
                        "fakeout_pattern"
                    ],
                    "suspicious_metrics": {
                        "dev_wallet_percent": 30,  # % détenus par dev wallet
                        "liquidity_ratio": 0.05,   # ratio liquidité/mcap
                        "twitter_follower_ratio": 0.01  # followers Twitter / mcap
                    },
                    "version": "1.0"
                }
                
                # Créer le répertoire si nécessaire
                os.makedirs(os.path.dirname(risk_patterns_path), exist_ok=True)
                
                # Écrire le fichier initial
                with open(risk_patterns_path, 'w') as f:
                    json.dump(default_patterns, f, indent=4)
                    
                self.risk_patterns = default_patterns
                logger.info(f"Fichier de patterns de risque créé à {risk_patterns_path}")
                
            else:
                # Charger le fichier existant
                with open(risk_patterns_path, 'r') as f:
                    self.risk_patterns = json.load(f)
                logger.info(f"Patterns de risque chargés: {len(self.risk_patterns.get('high_risk_patterns', []))} patterns, {len(self.risk_patterns.get('suspicious_metrics', {}))} métriques")
            
        except Exception as e:
            logger.warning(f"Erreur lors du chargement des patterns de risque: {str(e)}")
            # Initialiser avec des valeurs par défaut
            self.risk_patterns = {
                "high_risk_patterns": ["pump_and_dump", "rug_pull_preparation"],
                "suspicious_metrics": {"dev_wallet_percent": 30}
            }

    def _initialize_mev_optimizer(self) -> None:
        """Initialise l'optimiseur MEV pour Solana si disponible."""
        if not self.use_mev_protection or not JITO_OPTIMIZER_AVAILABLE:
            logger.info("Protection MEV désactivée ou non disponible")
            return
            
        try:
            logger.info("Initialisation de l'optimiseur MEV Jito...")
            self.mev_optimizer = create_jito_optimizer(
                solana_rpc_url=self.rpc_url,
                wallet_keypair_path=self.wallet_keypair_path,
                jito_auth_keypair_path=self.jito_auth_keypair_path,
                jito_searcher_endpoint=self.jito_endpoint,
                jito_tip_account=self.jito_tip_account
            )
            logger.info("Optimiseur MEV Jito initialisé avec succès")
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de l'optimiseur MEV: {e}")
            self.mev_optimizer = None

    def _initialize_lightweight_analyzer(self) -> None:
        """Initialise l'analyseur de contrats léger."""
        if not self.lightweight_analysis_enabled:
            logger.info("Analyse légère désactivée ou non disponible")
            return
            
        try:
            logger.info("Initialisation de l'analyseur de contrats léger...")
            self.lightweight_analyzer = create_contract_analyzer(
                models_dir=self.lightweight_analyzer_models_dir,
                config={
                    "cache_ttl_seconds": 3600,  # 1 heure de cache
                    "max_cache_items": 1000,
                    "security_threshold": self.config.get("security_threshold", 0.65)
                }
            )
            logger.info("Analyseur de contrats léger initialisé avec succès")
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de l'analyseur léger: {e}")
            self.lightweight_analyzer = None
            self.lightweight_analysis_enabled = False
    
    def _update_lightweight_stats(self, result: ContractSecurityResult, elapsed_ms: float, token_id: str) -> None:
        """
        Met à jour les statistiques d'analyse légère.
        
        Args:
            result: Résultat de l'analyse
            elapsed_ms: Temps écoulé en ms
            token_id: Identifiant du token
        """
        # Éviter de compter plusieurs fois le même token
        if token_id in self.lightweight_stats["tokens_analyzed_ids"]:
            return
            
        self.lightweight_stats["tokens_analyzed_ids"].add(token_id)
        self.lightweight_stats["total_analyses"] += 1
        
        if result.model_used != "fallback":
            self.lightweight_stats["analyses_succeeded"] += 1
        else:
            self.lightweight_stats["analyses_failed"] += 1
            
        if not result.is_safe and result.overall_risk_score >= 0.8:
            self.lightweight_stats["tokens_rejected"] += 1
            
        # Mettre à jour le temps moyen d'analyse
        n = self.lightweight_stats["total_analyses"]
        old_avg = self.lightweight_stats["avg_analysis_time_ms"]
        new_avg = ((old_avg * (n-1)) + elapsed_ms) / n
        self.lightweight_stats["avg_analysis_time_ms"] = new_avg

    def _prepare_price_data_for_volatility(self, token_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prépare les données de prix pour la prédiction de volatilité.
        
        Args:
            token_data: Données du token
            
        Returns:
            Dict[str, Any]: Données formatées pour le prédicteur de volatilité
        """
        # Récupérer les données OHLCV si disponibles
        price_data = {
            "symbol": token_data.get("symbol", "Unknown"),
            "timestamp": int(time.time()),
            "open": token_data.get("price", 0),
            "high": token_data.get("price_high", token_data.get("price", 0) * 1.01),  # Estimation si non disponible
            "low": token_data.get("price_low", token_data.get("price", 0) * 0.99),    # Estimation si non disponible
            "close": token_data.get("price", 0),
            "volume": token_data.get("volume_24h", 0),
        }
        
        # Calculer les caractéristiques techniques si possible
        if "price_history" in token_data and len(token_data["price_history"]) > 1:
            price_history = token_data["price_history"]
            price_data["log_return"] = np.log(price_data["close"] / price_history[-1]["price"])
            
            # Calculer la volatilité historique (écart-type des rendements logarithmiques)
            returns = [np.log(price_history[i+1]["price"] / price_history[i]["price"]) 
                      for i in range(len(price_history)-1)]
            
            if returns:
                price_data["volatility"] = np.std(returns)
            
            # Moyennes mobiles
            recent_prices = [p["price"] for p in price_history[-15:]]
            if len(recent_prices) >= 15:
                ma_5 = np.mean(recent_prices[-5:])
                ma_15 = np.mean(recent_prices[-15:])
                price_data["ma_ratio"] = ma_5 / ma_15 if ma_15 > 0 else 1.0
            
            # Variations de volume si disponibles
            if "volume_history" in token_data and len(token_data["volume_history"]) > 1:
                volume_history = token_data["volume_history"]
                price_data["volume_change"] = (price_data["volume"] / volume_history[-1]["volume"]) - 1 if volume_history[-1]["volume"] > 0 else 0
                
                recent_volumes = [v["volume"] for v in volume_history[-5:]]
                if recent_volumes:
                    price_data["volume_ratio"] = price_data["volume"] / np.mean(recent_volumes) if np.mean(recent_volumes) > 0 else 1.0
        
        return price_data


# Exemple d'utilisation du module
async def main():
    """Fonction d'exemple pour démo du sniper"""
    # Initialiser le sniper
    sniper = SolanaMemecoinSniper()
    
    # Démarrer le sniper
    await sniper.start()
    
    try:
        # Laisser tourner pour la démo
        print("Sniper en cours d'exécution. Appuyez sur Ctrl+C pour arrêter.")
        while True:
            stats = sniper.get_stats()
            print(f"Statistiques: {json.dumps(stats, indent=2)}")
            await asyncio.sleep(10)
    except KeyboardInterrupt:
        print("Arrêt demandé...")
    finally:
        # Arrêter le sniper
        await sniper.stop()
        print("Sniper arrêté.")

if __name__ == "__main__":
    asyncio.run(main()) 